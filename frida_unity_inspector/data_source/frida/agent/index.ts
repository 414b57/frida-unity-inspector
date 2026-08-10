import "frida-il2cpp-bridge"

import {capabilities, resolveAvailability} from "./helpers/capability"
import {Builtins, Events, sendEvent} from "./helpers/protocol"

// Import each capability module for its registration side effect.
/// Information Getting
// Context/Scene management
import "./capabilities/getCurrentRenderPipeline"
import "./capabilities/getSceneManager"
import "./capabilities/getCurrentScene"
// Hierarchy/Component getting
import "./capabilities/getHierarchyStructure"
// Component property getting
import "./capabilities/getComponentProperties"

/// Data Writing
// GameObject/component/property changing
import "./capabilities/setGameObjectActive"

/*
Design idea:
- The Python side is the single source of truth: models.py defines the data shapes, protocol_spec.py the RPC/event surface. From these files codegen.py generates ../protocol.py, helpers/protocol.ts, and helpers/models.ts, so both sides of the boundary agree by construction.
- Each capability (capabilities/*.ts) detects the assemblies/classes/methods it needs and, if present, gets its implementation exported over RPC. Adding a feature = one protocol_spec.py entry (+ any models.py shape) + one file + one import above.
- Registration happens here; each implementation starts Il2Cpp.perform itself and returns its promise. (Done this way, as some funcs may not need Il2Cpp.perform, so implementations can choose to do it themselves.)
*/

function bootstrap() {
    Il2Cpp.perform(() => {
        console.log("[+] IL2CPP perform started")

        const exports = rpc.exports as Record<string, unknown>

        function getCapabilities(): Record<string, boolean> {
            const builtins = Object.fromEntries(Object.values(Builtins).map((name) => [name, true]))
            const availabilitySnapshot = resolveAvailability()
            return {...availabilitySnapshot, ...builtins}
        }
        
        exports[Builtins.CAPABILITIES] = getCapabilities

        exports[Builtins.VERSION] = () => {
            return "0.1.0"
        }

        exports[Builtins.UNITY_VERSION] = () => {
            return Il2Cpp.unityVersion
        }

        exports[Builtins.PING] = (unix_epoch_seconds: number) => {
            const now = Date.now() / 1000
            return [now-unix_epoch_seconds, now]
        }

        const capabilitySnapshot = getCapabilities()
        for (const capability of capabilities()) {
            if (capabilitySnapshot[capability.name]) {
                exports[capability.name] = capability.implementation
            } else {
                console.warn(`[!] capability '${capability.name}' unavailable`)
            }
        }

        console.log("[+] RPC exports:", Object.keys(exports))

        console.log("[+] Capabilities detected:", JSON.stringify(capabilitySnapshot))
        sendEvent(Events.AGENT_READY, capabilitySnapshot)
    })
}

setTimeout(bootstrap, 3000)

sendEvent(Events.AGENT_LOADED, null)
