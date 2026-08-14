"""Single source of truth for everything crossing the Python <-> agent boundary.

This is used by `codegen.py` which turns this (plus `models.py`) into:
    - ./protocol.py - StrEnums, event payload aliases, typed RPC client
    - ./agent/helpers/models.ts - TS mirror of the pydantic models
    - ./agent/helpers/protocol.ts - name consts, capability signatures, typed sendEvent
This is done to ensure the protocol is fully typed and consistent in both domains.


To add a function/capability/event, add an entry below. Then specify its return type, argument types, and event data type using ordinary python type annotations.
You may also reference pydantic models from ``models.py`` directly (e.g. ``list[HierarchyNode]``) for further control, this is supported by the codegen and both sides will stay typed by construction.

Type vocabulary is just Python typing: ``str | int | float | bool | None``, ``Any``, ``list[T]``, ``dict[K, V]``, ``tuple[T, ...]``, ``Optional[T]``, ``Literal[...]``,
and any model / enum / alias defined in ``models.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# Load models.py without importing the wider package. Stores result in sys.modules["fui_models"] so that other code can import it normally and makes it act like a singleton.
def _load_models():
    if "fui_models" in sys.modules:
        return sys.modules["fui_models"]
    path = Path(__file__).resolve().parent.parent / "models.py"
    spec = importlib.util.spec_from_file_location("fui_models", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["fui_models"] = module
    spec.loader.exec_module(module)
    return module


models = _load_models()

HierarchyNode = models.HierarchyNode
Scene = models.Scene
Property = models.Property


# Spec vocabulary
@dataclass(frozen=True)
class Arg:
    name: str
    type: Any  # a Python type annotation


@dataclass(frozen=True)
class Call:
    """A builtin or capability RPC entry.

    ``key`` is the SCREAMING_SNAKE_CASE enum member; ``name`` is the JS export /
    wire name. ``requires`` names other capability keys (capabilities only).
    """

    key: str
    name: str
    returns: Any
    args: tuple[Arg, ...] = ()
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class Event:
    key: str
    name: str
    data: Any


# Protocol
# Message types - used to determine how to parse a message from agent. I.e. event is something that happened. Frame is a picture frame from camera, etc.
# NOTE: If add new message type, add in a `typeS: list[Type]` below as seen for agent loaded/ready events.
#       Then modify codegen.py to generate the new type in `render_protocol_ts` and `render_protocol_py` functions.
MESSAGE_TYPES: dict[str, str] = {
    "EVENT": "event",
}

EVENTS: list[Event] = [
    Event("AGENT_LOADED", "agent_loaded", None),
    Event("AGENT_READY", "agent_ready", dict[str, bool]),
]

# Built in functions that are always available over RPC regardless of capabilities. These are used to query the agent for its capabilities, version, etc.
BUILTINS: list[Call] = [
    Call("CAPABILITIES", "capabilities", dict[str, bool]),
    Call("VERSION", "version", str),
    Call("UNITY_VERSION", "unityVersion", str),
    Call("PING", "ping", tuple[float, float], args=(Arg("unix_epoch_seconds", float),)),
]

# Capabilities are functions that may or may not be available depending on the agent's capabilities (i.e. unity version, if functions have have been stripped or not, etc.)
CAPABILITIES: list[Call] = [
    ## Information Getting
    # Context / scene management
    Call("GET_CURRENT_RENDER_PIPELINE", "getCurrentRenderPipeline", Optional[str]),
    Call("GET_SCENE_MANAGER", "getSceneManager", Any),
    Call("GET_CURRENT_SCENE", "getCurrentScene", Any, requires=("GET_SCENE_MANAGER",)),
    # All currently-loaded scenes (Unity can have several loaded at once, e.g. additive loading).
    Call("GET_LOADED_SCENES", "getLoadedScenes", Any, requires=("GET_SCENE_MANAGER",)),

    # Hierarchy
    # Lightweight tree walk: ids/names/active/tag/layer + component list (id/type/enabled), NO property values.
    # Cheap to compute. Fetch property values separately per component as needed.
    # Returns one Scene per loaded scene, each carrying its own roots (property values omitted).
    Call(
        "GET_HIERARCHY_STRUCTURE",
        "getHierarchyStructure",
        Optional[list[Scene]],
        requires=("GET_LOADED_SCENES",),
    ),
    # Reflection-heavy property scan for a batch of components (ids from the structure walk).
    # A component id that is unknown/stale maps to None so callers can drop it.
    Call(
        "GET_COMPONENT_PROPERTIES",
        "getComponentProperties",
        dict[str, Optional[list[Property]]],
        args=(Arg("component_ids", list[str]),),
        requires=("GET_HIERARCHY_STRUCTURE",),
    ),

    ## Data writing
    Call(
        "SET_GAMEOBJECT_ACTIVE",
        "setGameObjectActive",
        bool,
        args=(Arg("gameobject_handle_ptr", str), Arg("active", bool)),
    ),
    Call(
        "SET_COMPONENT_ENABLED",
        "setComponentEnabled",
        bool,
        args=(Arg("component_handle_ptr", str), Arg("active", bool))
    ),
    Call(
        "SET_PROPERTY_VALUE",
        "setPropertyValue",
        Optional[Property],
        args=(Arg("component_handle_ptr", str), Arg("property", Property))
    )
]
