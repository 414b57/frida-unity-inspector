/*
 * Generates the typed protocol bindings for both sides from ../protocol.json:
 *   ../protocol.py        - StrEnums, event payload aliases, typed RPC client
 *   ./helpers/protocol.ts - name consts, capability signatures, typed sendEvent
 * Runs automatically as part of `npm run build`.
 *
 */
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const protocolPath = path.join(here, "..", "protocol.json");
const pythonOut = path.join(here, "..", "protocol.py");
const typescriptOut = path.join(here, "helpers", "protocol.ts");

const protocol = JSON.parse(readFileSync(protocolPath, "utf-8"));

const BANNER_PY = `"""AUTO-GENERATED from protocol.json - do not edit by hand."""`;
const BANNER_TS = `/* AUTO-GENERATED from ../../protocol.json - do not edit by hand. */`;

const KEY_PATTERN = /^[A-Z][A-Z0-9_]*$/;

// Map protocol type spec -> Python / TypeScript annotation
// TODO - Look into better way, so dont have to manually define each mapping.
const PRIMITIVES = {
    string: { py: "str",   ts: "string" },
    int:    { py: "int",   ts: "number" },
    float:  { py: "float", ts: "number" },
    bool:   { py: "bool",  ts: "boolean" },
    null:   { py: "None",  ts: "null" },
    any:    { py: "Any",   ts: "unknown" },
};

// Split a type spec's generic arguments, e.g. "map<string, list<int>>" -> ["string", "list<int>"].
function splitTypeArgs(spec) {
    const parts = [];
    let depth = 0;
    let current = "";
    for (const char of spec) {
        if (char === "<") depth++;
        else if (char === ">") depth--;
        if (char === "," && depth === 0) {
            parts.push(current);
            current = "";
        } else {
            current += char;
        }
    }
    parts.push(current);
    return parts.map((part) => part.trim());
}

// Translate a protocol type spec into Python and TypeScript annotations, e.g. "list<string>" -> { py: "list[str]", ts: "string[]" }.
function parseType(spec) {
    const text = String(spec).trim();

    if (text.endsWith("?")) {
        const inner = parseType(text.slice(0, -1));
        return { py: `${inner.py} | None`, ts: `${inner.ts} | null` };
    }

    const generic = /^(list|map)<(.*)>$/.exec(text); // Match list<T> or map<K, V> | TODO Look into a better way so dont have to manually define each mapping.
    if (generic !== null) {
        // If found - Ensure the correct number of type arguments are provided, and recursively parse them.
        const [, kind, rawArgs] = generic;
        const args = splitTypeArgs(rawArgs).map(parseType);
        if (kind === "list") {
            if (args.length !== 1) throw new Error(`list<> takes exactly 1 type argument - '${spec}'`);
            return { py: `list[${args[0].py}]`, ts: `${args[0].ts}[]` };
        }
        if (args.length !== 2) throw new Error(`map<> takes exactly 2 type arguments - '${spec}'`);
        return { py: `dict[${args[0].py}, ${args[1].py}]`, ts: `Record<${args[0].ts}, ${args[1].ts}>` };
    }

    const primitive = PRIMITIVES[text];
    if (primitive === undefined) {
        throw new Error(`Unknown type specified - '${spec}' (known: ${Object.keys(PRIMITIVES).join(", ")}, T?, list<T>, map<K, V>)`);
    }
    return primitive;
}

// Read a section of protocol.json, validating that all keys are in the correct format.
function section(name) {
    const entries = protocol[name];
    if (entries === undefined) throw new Error(`protocol.json is missing section '${name}'`);
    for (const key of Object.keys(entries)) {
        if (!KEY_PATTERN.test(key)) throw new Error(`'${name}.${key}' is not a valid SCREAMING_SNAKE_CASE key`);
    }
    return entries;
}

// Ensure a call entry is in the correct format, and parse its argument and return types.
function readCall(sectionName, key, entry) {
    const where = `${sectionName}.${key}`;
    if (typeof entry?.name !== "string") throw new Error(`'${where}' needs a string 'name'`);
    if (typeof entry.returns !== "string") throw new Error(`'${where}' needs a string 'returns'`);
    const args = (entry.args ?? []).map((arg, index) => {
        if (typeof arg?.name !== "string" || typeof arg?.type !== "string") {
            throw new Error(`'${where}.args[${index}]' needs string 'name' and 'type'`);
        }
        return { name: arg.name, type: parseType(arg.type) };
    });
    return { key, name: entry.name, args, returns: parseType(entry.returns) };
}

function readCallSection(name) {
    return Object.entries(section(name)).map(([key, entry]) => readCall(name, key, entry));
}

const messageTypes = section("message_types");
const events = Object.entries(section("events")).map(([key, entry]) => {
    // Ensure in correct format, and parse the event's data type.
    if (typeof entry?.name !== "string") throw new Error(`'events.${key}' needs a string 'name'`);
    if (typeof entry.data !== "string") throw new Error(`'events.${key}' needs a string 'data'`);
    return { key, name: entry.name, data: parseType(entry.data) };
});
const builtins = readCallSection("builtins");
const capabilities = readCallSection("capabilities");

// Helper functions for converting between python and typescript naming conventions, and for generating event payload type aliases.
const pascalCase = (key) => key.toLowerCase().replace(/(^|_)([a-z0-9])/g, (_, __, char) => char.toUpperCase());
const snakeCase = (key) => key.toLowerCase();
const eventDataAlias = (event) => `${pascalCase(event.key)}Data`;

// ---- Python ----------------------------------------------------------------
/*
 * Generates the protocol file for PYTHON side;
 * - StrEnum classes for message types, events, builtins, and capabilities
 * - Type aliases for event payloads
 * - TypeAdapter instances for validating event payloads and RPC return values
 * - AgentRpc class with typed methods for calling builtins and capabilities
 */
function renderPython() {
    let out = `${BANNER_PY}\nfrom __future__ import annotations\n\nfrom enum import StrEnum\nfrom typing import Any, Awaitable, Callable, TypeAlias\n\nfrom pydantic import TypeAdapter\n`;

    const enums = [
        ["MessageTypes", Object.entries(messageTypes).map(([key, name]) => [key, name])],
        ["Events", events.map((event) => [event.key, event.name])],
        ["Builtins", builtins.map((call) => [call.key, call.name])],
        ["Capabilities", capabilities.map((call) => [call.key, call.name])],
    ];
    for (const [className, members] of enums) {
        out += `\n\nclass ${className}(StrEnum):\n`;
        if (members.length === 0) out += "    pass\n";
        for (const [key, value] of members) out += `    ${key} = ${JSON.stringify(value)}\n`;
    }

    out += "\n\n# Event payloads, and their TypeAdapters for validation\n";
    for (const event of events) out += `${eventDataAlias(event)}: TypeAlias = ${event.data.py}\n`;
    out += "\nEVENT_DATA_ADAPTERS: dict[Events, TypeAdapter[Any]] = {\n";
    for (const event of events) out += `    Events.${event.key}: TypeAdapter(${eventDataAlias(event)}),\n`;
    out += "}\n";

    const allCalls = [...builtins.map((call) => ({ ...call, enum: "Builtins" })), ...capabilities.map((call) => ({ ...call, enum: "Capabilities" }))];

    out += "\n\n# TypeAdapters for validating RPC return values\n";
    for (const call of allCalls) out += `_${call.key}_RETURN: TypeAdapter[Any] = TypeAdapter(${call.returns.py})\n`;

    out += `\n\nRpcCall: TypeAlias = Callable[..., Awaitable[Any]]\n\n\nclass AgentRpc:\n`;
    out += `    """Typed wrappers around the agent's RPC exports.\n\n`;
    out += `    Each method corresponds to an RPC call, and returns the validated result via pydantic. Raises ValidationError if the result is invalid.\n`;
    out += `    """\n\n`;
    out += `    def __init__(self, call: RpcCall) -> None:\n`;
    out += `            self._call = call\n`;
    out += `            self._dispatch: dict[StrEnum, RpcCall] = {\n`;
    for (const call of allCalls) out += `                ${call.enum}.${call.key}: self.${snakeCase(call.key)},\n`;
    out += `            }\n\n`;
    out += `    def dispatch(self, key: StrEnum, *args, **kwargs) -> Awaitable[Any]:\n`;
    out += `        """Dispatches an RPC call based on the key, and returns the validated result."""\n`;
    out += `        if key not in self._dispatch:\n`;
    out += `            raise ValueError(f"Unknown RPC key: {key}")\n`;
    out += `        return self._dispatch[key](*args, **kwargs)\n`;
    for (const call of allCalls) {
        const params = call.args.map((arg) => `, ${arg.name}: ${arg.type.py}`).join("");
        const passed = call.args.map((arg) => `, ${arg.name}`).join("");
        out += `\n    async def ${snakeCase(call.key)}(self${params}) -> ${call.returns.py}:\n`;
        out += `        result = await self._call(${call.enum}.${call.key}${passed})\n`;
        out += `        return _${call.key}_RETURN.validate_python(result)\n`;
    }
    return out;
}

// ---- TypeScript ------------------------------------------------------------
/*
 * Generates the protocol file for TypeScript side;
 * - Const objects for message types, events, builtins, and capabilities
 * - Type aliases for event names, builtin names, and capability names
 * - Interfaces for event payloads, builtin signatures, and capability signatures
 * - sendEvent function for sending events to the Python side with typed payloads
 */
function renderTypeScript() {
    let out = `${BANNER_TS}\n`;

    const consts = [
        ["MessageTypes", "MessageType", Object.entries(messageTypes)],
        ["Events", "EventName", events.map((event) => [event.key, event.name])],
        ["Builtins", "BuiltinName", builtins.map((call) => [call.key, call.name])],
        ["Capabilities", "CapabilityName", capabilities.map((call) => [call.key, call.name])],
    ];
    for (const [constName, typeName, members] of consts) {
        out += `\n\nexport const ${constName} = {\n`;
        for (const [key, value] of members) out += `    ${key}: ${JSON.stringify(value)},\n`;
        out += `} as const\n`;
        out += `export type ${typeName} = (typeof ${constName})[keyof typeof ${constName}]\n`;
    }

    // Implementations start Il2Cpp.perform themselves, so they may return a Promise; frida resolves it before replying.
    const signature = (call) => `(${call.args.map((arg) => `${arg.name}: ${arg.type.ts}`).join(", ")}) => ${call.returns.ts} | Promise<${call.returns.ts}>`;

    out += `\n/** Payload shape each event carries. */`;
    out += `\nexport interface EventPayloads {\n`;
    for (const event of events) out += `    ${JSON.stringify(event.name)}: ${event.data.ts}\n`;
    out += `}\n`;

    out += `\n/** Signature each capability's implementation must have. */`;
    out += `\nexport interface CapabilitySignatures {\n`;
    for (const call of capabilities) out += `    ${JSON.stringify(call.name)}: ${signature(call)}\n`;
    out += `}\n`;

    out += `\nexport interface BuiltinSignatures {\n`;
    for (const call of builtins) out += `    ${JSON.stringify(call.name)}: ${signature(call)}\n`;
    out += `}\n`;

    out += `\n/** Helper for sending an event to the Python side with a payload matching the protocol. */\n`;
    out += `export function sendEvent<E extends EventName>(event: E, data: EventPayloads[E]): void {\n`;
    out += `    send({ type: MessageTypes.EVENT, event, data })\n}\n`;

    return out;
}

function writeIfChanged(filePath, content) {
    let existing = null;
    try {
        existing = readFileSync(filePath, "utf-8");
    } catch {}
    if (existing === content) return false;
    writeFileSync(filePath, content);
    return true;
}

const wrotePython = writeIfChanged(pythonOut, renderPython());
const wroteTypescript = writeIfChanged(typescriptOut, renderTypeScript());
const status = wrotePython || wroteTypescript ? "generated" : "up to date";
console.log(`[+] protocol: ${status} - ${path.relative(process.cwd(), pythonOut)} and ${path.relative(process.cwd(), typescriptOut)}`);
