"""Generates the typed bindings for both sides of the Python <-> agent boundary.

Source of truth is Python:
    - models.py - pydantic models (the serialized data shapes)
    - protocol_spec.py - the RPC/event surface, referencing those models directly

From them this emits:
    - ./protocol.py - StrEnums, event aliases, TypeAdapters, typed AgentRpc
    - ./agent/helpers/models.ts - TS mirror of the pydantic models
    - ./agent/helpers/protocol.ts - name consts, signatures, typed sendEvent

This is done to ensure the protocol is fully typed and consistent in both domains.

Run directly (`python codegen.py`) or via the agent's `npm run generate` / watch.
Output paths are resolved relative to this file, so the working directory doesn't matter.
"""

from __future__ import annotations

import logging
import importlib.util
import json
import sys
import types
import typing
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "protocol_spec.py"
PYTHON_OUT = HERE / "protocol.py"
MODELS_TS_OUT = HERE / "agent" / "helpers" / "models.ts"
PROTOCOL_TS_OUT = HERE / "agent" / "helpers" / "protocol.ts"

BANNER_PY = '"""AUTO-GENERATED from protocol_spec.py + models.py - do not edit by hand."""'
BANNER_TS = "/* AUTO-GENERATED from ../../protocol_spec.py + ../../../models.py - do not edit by hand. */"

logger = logging.getLogger("fui.codegen")
# NOTE - This is not part of standard code, so doesnt have the custom `install_custom_log_levels` applied. As such .env log level WILL be ignored. and custom trace/spam/gsy isnt available.

# Loads a python module from a file path, without importing the wider package. Stores result in sys.modules[name] so that other code can import it normally and makes it act like a singleton.
def load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Registry of all models, enums, and aliases defined in models.py, keyed by object id so that a field annotation can be rendered as a reference to its declared name.
class Registry:
    def __init__(self, models: types.ModuleType) -> None:
        self.models = models
        self.name_by_id: dict[int, str] = {}
        # (kind, name, obj) in definition order, for emitting models.ts top-to-bottom.
        self.ordered: list[tuple[str, str, Any]] = []

        for name, obj in vars(models).items():
            if name.startswith("_"):
                continue
            kind = self._classify(name, obj)
            if kind is None:
                continue
            self.name_by_id[id(obj)] = name
            self.ordered.append((kind, name, obj))

        logger.debug("Registry: %s", [(kind, name) for kind, name, _ in self.ordered])

    def _classify(self, name: str, obj: Any) -> str | None:
        if isinstance(obj, type) and obj.__module__ == self.models.__name__: # only consider classes defined in models.py
            if issubclass(obj, BaseModel): # e.g. GameContext, SceneDeclaration, HierarchyNode
                return "model"
            if issubclass(obj, Enum): # e.g. LogType, IconName
                return "enum"
            logger.warning("Unknown class %s.%s, skipping", self.models.__name__, name)
            return None

        if get_origin(obj) is Literal:  # e.g. IconName, LogType
            return "literal"
        if hasattr(obj, "__metadata__"):  # Annotated discriminated union, e.g. Property
            return "union"

        logger.debug("Unknown object %s.%s, skipping", self.models.__name__, name)
        return None

    def name_of(self, obj: Any) -> str | None:
        return self.name_by_id.get(id(obj))

# Utility functions for rendering Python types to TypeScript and vice versa.
def _literal_value_ts(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Enum):
        return json.dumps(value.value)
    if value is None:
        return "null"
    if isinstance(value, str):
        return json.dumps(value)
    return json.dumps(value)


def _is_union(origin: Any) -> bool:
    return origin is Union or origin is types.UnionType


class TsRenderer:
    def __init__(self, registry: Registry) -> None:
        self.reg = registry

    def render(self, tp: Any, refs: set[str] | None = None) -> str:
        # Check if this type is a named model/enum/alias in models.py, and if so return its name and record it in the refs set. So it can be imported in the generated TS file.
        named = self.reg.name_of(tp)
        if named is not None:
            if refs is not None:
                refs.add(named)
            return named

        # Primitive types
        if tp is None or tp is type(None):
            return "null"
        if tp is Any:
            return "any"
        if tp is str:
            return "string"
        if tp is bool:
            return "boolean"
        if tp is int or tp is float:
            return "number"
        if tp is bytes:
            return "string"

        # Generic types
        origin = get_origin(tp)
        if origin is Literal: # e.g. Literal["foo", "bar"] -> "foo" | "bar" (means value must be one of those strings)
            return " | ".join(_literal_value_ts(a) for a in get_args(tp))
        if hasattr(tp, "__metadata__"): # e.g. Annotated[Union[...], discriminator] - use the underlying type
            return self.render(get_args(tp)[0], refs)
        if _is_union(origin): # e.g. Union[A, B] or A | B -> A | B (means value can be either type)
            return " | ".join(self.render(a, refs) for a in get_args(tp))
        if origin in (list, set, frozenset): # e.g. list[A] or set[A] -> A[] (means value is an array of that type)
            inner = self.render(get_args(tp)[0], refs)
            return f"({inner})[]" if " | " in inner else f"{inner}[]"
        if origin is dict: # e.g. dict[A, B] -> Record<A, B> (means value is an object with keys of type A and values of type B)
            key, value = get_args(tp)
            return f"Record<{self.render(key, refs)}, {self.render(value, refs)}>"
        if origin is tuple: # e.g. tuple[A, B, C] -> [A, B, C] (means value is a fixed-length array with those types)
            return f"[{', '.join(self.render(a, refs) for a in get_args(tp))}]"

        # Unknown type - fallback to any
        logger.warning("TS - Unknown type %s, falling back to 'any'", tp)
        logger.debug("TS - Type %s has origin %s and args %s", tp, origin, get_args(tp))
        return "unknown"


class PyRenderer:
    """Renders a Python annotation, recording any model.py names it references."""

    def __init__(self, registry: Registry) -> None:
        self.reg = registry
        self.imports: set[str] = set()
        self.needs_literal = False

    def render(self, tp: Any) -> str:
        # Check if this type is a named model/enum/alias in models.py, and if so return its name and record it in the imports set. So it can be imported in the generated Python file.
        named = self.reg.name_of(tp)
        if named is not None:
            self.imports.add(named)
            return named

        # Primitive types
        if tp is None or tp is type(None):
            return "None"
        if tp is Any:
            return "Any"
        if tp is str:
            return "str"
        if tp is bool:
            return "bool"
        if tp is int:
            return "int"
        if tp is float:
            return "float"
        if tp is bytes:
            return "bytes"

        # Generic types
        origin = get_origin(tp)
        if origin is Literal: # e.g. Literal["foo", "bar"] -> Literal["foo", "bar"] (means value must be one of those strings)
            self.needs_literal = True
            return f"Literal[{', '.join(self._literal_value(a) for a in get_args(tp))}]"
        if hasattr(tp, "__metadata__"): # e.g. Annotated[Union[...], discriminator] - use the underlying type
            return self.render(get_args(tp)[0])
        if _is_union(origin): # e.g. Union[A, B] or A | B -> Union[A, B] (means value can be either type)
            return " | ".join(self.render(a) for a in get_args(tp))
        if origin in (list, set, frozenset): # e.g. list[A] or set[A] -> list[A] (means value is a list of that type)
            return f"{origin.__name__}[{self.render(get_args(tp)[0])}]"
        if origin is dict: # e.g. dict[A, B] -> dict[A, B] (means value is a dict with keys of type A and values of type B)
            key, value = get_args(tp)
            return f"dict[{self.render(key)}, {self.render(value)}]"
        if origin is tuple: # e.g. tuple[A, B, C] -> tuple[A, B, C] (means value is a fixed-length tuple with those types)
            return f"tuple[{', '.join(self.render(a) for a in get_args(tp))}]"

        logger.warning("PY - Unknown type %s, falling back to 'Any'", tp)
        logger.debug("PY - Type %s has origin %s and args %s", tp, origin, get_args(tp))
        return "Any"

    # Helper to render a literal value for Python type annotations, including Enum members.
    def _literal_value(self, value: Any) -> str:
        if isinstance(value, Enum):
            self.imports.add(type(value).__name__)
            return f"{type(value).__name__}.{value.name}"
        return repr(value)

# TODO - Above basically same, with minor differences. Could unify with a base class and a few abstract methods, but not worth it right now.

# Naming helpers
def snake_case(key: str) -> str:
    return key.lower()


def pascal_case(key: str) -> str:
    return "".join(part.capitalize() for part in key.split("_"))


def event_data_alias(event: Any) -> str:
    return f"{pascal_case(event.key)}Data"


# Generate `models.ts` from the pydantic models in `models.py`.
def render_models_ts(reg: Registry) -> str:
    ts = TsRenderer(reg)
    hints_globals = vars(reg.models)
    out = [BANNER_TS, ""]

    for kind, name, obj in reg.ordered:
        if kind in ("literal", "enum"): # If it's a literal or enum, render it as a union of its values. If it's an enum, get the values from the enum members; if it's a literal, get the values from the Literal args.
            members = get_args(obj) if kind == "literal" else [member.value for member in obj]
            union = " | ".join(_literal_value_ts(member) for member in members)
            out.append(f"export type {name} = {union}")
        elif kind == "union":  # Annotated[Union[...], discriminator] - render the underlying union type as a TypeScript union of its members.
            union_type = get_args(obj)[0]
            members = " | ".join(ts.render(member) for member in get_args(union_type))
            out.append(f"export type {name} = {members}")
        elif kind == "model": # If it's a pydantic model, render it as a TypeScript interface with its fields and their types. Use get_type_hints to get the field types, including any forward references.
            hints = get_type_hints(obj, globalns=hints_globals, include_extras=True)
            out.append(f"export interface {name} {{")
            for field_name, field_info in obj.model_fields.items():
                optional = "" if field_info.is_required() else "?"
                out.append(f"    {field_name}{optional}: {ts.render(hints[field_name])}")
            out.append("}")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


# Helper function to render a TypeScript function signature for a given Call object, including its argument types and return type.
def ts_signature(ts: TsRenderer, call: Any, refs: set[str]) -> str:
    args = ", ".join(f"{arg.name}: {ts.render(arg.type, refs)}" for arg in call.args)
    returns = ts.render(call.returns, refs)
    return f"({args}) => {returns} | Promise<{returns}>"


# Generate `protocol.ts` from the protocol spec in `protocol_spec.py`. This includes the name consts, event payloads, and capability signatures.
def render_protocol_ts(reg: Registry, spec: types.ModuleType) -> str:
    ts = TsRenderer(reg)
    refs: set[str] = set()

    # Consts that need to be exported as both a const object and a type alias. Each entry is a tuple of (const_name, type_name, members), where members is a list of (key, value) pairs.
    # Similar to the enums in protocol.py, but here we generate const objects and type aliases instead of StrEnum classes.
    consts = [
        ("MessageTypes", "MessageType", list(spec.MESSAGE_TYPES.items())),
        ("Events", "EventName", [(event.key, event.name) for event in spec.EVENTS]),
        ("Builtins", "BuiltinName", [(call.key, call.name) for call in spec.BUILTINS]),
        ("Capabilities", "CapabilityName", [(call.key, call.name) for call in spec.CAPABILITIES]),
    ]
    body: list[str] = []
    for const_name, type_name, members in consts:
        body.append("")
        body.append(f"export const {const_name} = {{")
        for key, value in members:
            body.append(f"    {key}: {json.dumps(value)},")
        body.append("} as const")
        body.append(f"export type {type_name} = (typeof {const_name})[keyof typeof {const_name}]")

    # Define the CapabilityRequires mapping, which maps each capability name to a list of capability names it requires. This is used for dependency checking.
    body.append("")
    body.append("/** Capabilities each capability depends on */")
    body.append("export const CapabilityRequires: Record<" + "CapabilityName, readonly CapabilityName[]> = {")
    name_by_key = {call.key: call.name for call in spec.CAPABILITIES}
    for call in spec.CAPABILITIES:
        required = ", ".join(json.dumps(name_by_key[key]) for key in call.requires)
        body.append(f"    {json.dumps(call.name)}: [{required}],")
    body.append("}")

    # Define the EventPayloads interface, which maps each event name to its corresponding payload type. This is used for type checking when sending events.
    body.append("")
    body.append("/** Payload shape each event carries. */")
    body.append("export interface EventPayloads {")
    for event in spec.EVENTS:
        body.append(f"    {json.dumps(event.name)}: {ts.render(event.data, refs)}")
    body.append("}")

    # Define the CapabilitySignatures interface, which maps each capability name to its corresponding function signature. This is used for type checking when calling capabilities.
    body.append("")
    body.append("/** Signature each capability's implementation must have. */")
    body.append("export interface CapabilitySignatures {")
    for call in spec.CAPABILITIES:
        body.append(f"    {json.dumps(call.name)}: {ts_signature(ts, call, refs)}")
    body.append("}")

    # Same as above - but for builtins, which are always available regardless of capabilities.
    body.append("")
    body.append("export interface BuiltinSignatures {")
    for call in spec.BUILTINS:
        body.append(f"    {json.dumps(call.name)}: {ts_signature(ts, call, refs)}")
    body.append("}")

    # Send event helper function.
    body.append("")
    body.append("/** Helper for sending an event to the Python side with a payload matching the protocol. */")
    body.append("export function sendEvent<E extends EventName>(event: E, data: EventPayloads[E]): void {")
    body.append("    send({ type: MessageTypes.EVENT, event, data })")
    body.append("}")

    header = [BANNER_TS]
    # If any external refs/refs to models.ts were used, import them at the top of the file. This ensures that the generated protocol.ts file has access to the types defined in models.ts.
    if refs:
        header.append(f"import type {{ {', '.join(sorted(refs))} }} from \"./models\"")

    return "\n".join(header + body).rstrip() + "\n"


# Generate `protocol.py` from the protocol spec in `protocol_spec.py`. This includes the StrEnums, event payload aliases, TypeAdapters, and typed AgentRpc class.
def render_protocol_py(reg: Registry, spec: types.ModuleType) -> str:
    py = PyRenderer(reg)

    # Render all types first so import/Literal usage is known before the header.
    event_types = {event.key: py.render(event.data) for event in spec.EVENTS}
    all_calls = [(call, "Builtins") for call in spec.BUILTINS] + [(call, "Capabilities") for call in spec.CAPABILITIES]
    return_types = {call.key: py.render(call.returns) for call, _ in all_calls}
    arg_types = {call.key: [(arg.name, py.render(arg.type)) for arg in call.args] for call, _ in all_calls}

    typing_names = ["Any", "Awaitable", "Callable", "TypeAlias"]
    if py.needs_literal:
        typing_names.insert(1, "Literal")

    # Setup imports and header for the generated Python file. This includes the BANNER_PY, future annotations import, StrEnum import, typing imports, and pydantic TypeAdapter import. If any models from models.py were referenced, import them as well.
    out: list[str] = [BANNER_PY, "from __future__ import annotations", ""]
    out.append("from enum import StrEnum")
    out.append(f"from typing import {', '.join(typing_names)}")
    out.append("")
    out.append("from pydantic import TypeAdapter")
    if py.imports:
        out.append(f"from ..models import {', '.join(sorted(py.imports))}")

    # Enums that need to be generated for the protocol. Each entry is a tuple of (class_name, members), where members is a list of (key, value) pairs. These will be rendered as StrEnum classes in the generated Python file.
    # Similar to ts consts, but here we generate StrEnum classes instead of const objects and type aliases.
    enums = [
        ("MessageTypes", list(spec.MESSAGE_TYPES.items())),
        ("Events", [(event.key, event.name) for event in spec.EVENTS]),
        ("Builtins", [(call.key, call.name) for call in spec.BUILTINS]),
        ("Capabilities", [(call.key, call.name) for call in spec.CAPABILITIES]),
    ]
    for class_name, members in enums:
        out.append("")
        out.append("")
        out.append(f"class {class_name}(StrEnum):")
        if not members:
            out.append("    pass")
        for key, value in members:
            out.append(f"    {key} = {json.dumps(value)}")

    # Define the CAPABILITY_REQUIRES mapping, which maps each capability enum member to a tuple of capability enum members it requires. This is used for dependency checking.
    out.append("")
    out.append("")
    out.append("# Capabilities each capability depends on")
    out.append("CAPABILITY_REQUIRES: dict[Capabilities, tuple[Capabilities, ...]] = {")
    for call in spec.CAPABILITIES:
        required = ", ".join(f"Capabilities.{key}" for key in call.requires)
        trailing = "," if len(call.requires) == 1 else ""
        out.append(f"    Capabilities.{call.key}: ({required}{trailing}),")
    out.append("}")

    # Define the event payload type aliases and their corresponding TypeAdapters for validation. Each event payload type alias is named after the event key in PascalCase with a "Data" suffix.
    out.append("")
    out.append("")
    out.append("# Event payloads, and their TypeAdapters for validation")
    for event in spec.EVENTS:
        out.append(f"{event_data_alias(event)}: TypeAlias = {event_types[event.key]}")
    out.append("")
    # Define the EVENT_DATA_ADAPTERS mapping, which maps each event enum member to its corresponding TypeAdapter for validation. This is used for validating event payloads received from the agent.
    out.append("EVENT_DATA_ADAPTERS: dict[Events, TypeAdapter[Any]] = {")
    for event in spec.EVENTS:
        out.append(f"    Events.{event.key}: TypeAdapter({event_data_alias(event)}),")
    out.append("}")

    # Define the TypeAdapters for validating RPC return values. Each TypeAdapter is named after the call key in PascalCase with a "_RETURN" suffix.
    out.append("")
    out.append("")
    out.append("# TypeAdapters for validating RPC return values")
    for call, _ in all_calls:
        out.append(f"_{call.key}_RETURN: TypeAdapter[Any] = TypeAdapter({return_types[call.key]})")

    out.append("")
    out.append("")
    # Define the RpcCall type alias, which represents a callable that takes any arguments and returns an Awaitable of any type. This is used for typing the RPC call function passed to the AgentRpc class.
    out.append("RpcCall: TypeAlias = Callable[..., Awaitable[Any]]")
    out.append("")
    out.append("")
    # Helper class that wraps the agent's RPC exports with typed methods. Each method corresponds to an RPC call, and returns the validated result via pydantic. Raises ValidationError if the result is invalid.
    out.append("class AgentRpc:")
    out.append('    """Typed wrappers around the agent\'s RPC exports.')
    out.append("")
    out.append("    Each method corresponds to an RPC call, and returns the validated result via pydantic. Raises ValidationError if the result is invalid.")
    out.append('    """')
    out.append("")
    out.append("    def __init__(self, call: RpcCall) -> None:")
    out.append("            self._call = call")
    out.append("            self._dispatch: dict[StrEnum, RpcCall] = {")
    for call, enum in all_calls:
        out.append(f"                {enum}.{call.key}: self.{snake_case(call.key)},")
    out.append("            }")
    out.append("")
    out.append("    def dispatch(self, key: StrEnum, *args, **kwargs) -> Awaitable[Any]:")
    out.append('        """Dispatches an RPC call based on the key, and returns the validated result."""')
    out.append("        if key not in self._dispatch:")
    out.append('            raise ValueError(f"Unknown RPC key: {key}")')
    out.append("        return self._dispatch[key](*args, **kwargs)")
    for call, enum in all_calls:
        params = "".join(f", {name}: {annotation}" for name, annotation in arg_types[call.key])
        passed = "".join(f", {name}" for name, _ in arg_types[call.key])
        out.append("")
        out.append(f"    async def {snake_case(call.key)}(self{params}) -> {return_types[call.key]}:")
        out.append(f"        result = await self._call({enum}.{call.key}{passed})")
        out.append(f"        return _{call.key}_RETURN.validate_python(result)")

    return "\n".join(out) + "\n"


# Helper function to write content to a file only if it has changed. Returns True if the file was written, False if it was unchanged.
def write_if_changed(path: Path, content: str) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    spec = load_by_path("protocol_spec", SPEC_PATH)
    reg = Registry(spec.models)
    logger.debug("Loaded %d models from %s", len(reg.ordered), reg.models.__name__)

    outputs = {
        PYTHON_OUT: render_protocol_py(reg, spec),
        MODELS_TS_OUT: render_models_ts(reg),
        PROTOCOL_TS_OUT: render_protocol_ts(reg, spec),
    }
    changed = [path for path, content in outputs.items() if write_if_changed(path, content)]
    for path in changed:
        logger.debug("Wrote %s", path)

    status = "generated" if changed else "up to date"
    rendered = ", ".join(path.name for path in outputs)
    logger.info("protocol: %s - %s", status, rendered)


if __name__ == "__main__":
    main()
