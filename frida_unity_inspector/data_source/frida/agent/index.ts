import "frida-il2cpp-bridge"

import {capabilities} from "./helpers/capability"
import {Builtins, BuiltinSignatures, Events, sendEvent} from "./helpers/protocol"

// Import each capability module for its registration side effect.
import "./capabilities/getCurrentRenderPipeline"

/*
Design idea:
- protocol.json is the single source of truth for names and signatures; helpers/protocol.ts and ../protocol.py are generated from it, so both sides of the boundary agree by construction.
- Each capability (capabilities/*.ts) detects the assemblies/classes/methods it needs and, if present, gets its implementation exported over RPC. Adding a feature = one protocol.json entry + one file + one import above.
- Registration happens here; each implementation starts Il2Cpp.perform itself and returns its promise. (Done this way, as some funcs may not need Il2Cpp.perform, so implementations can choose to do it themselves.)
*/

function bootstrap() {
    Il2Cpp.perform(() => {
        console.log("[+] IL2CPP attached")

        const exports = rpc.exports as Record<string, unknown>
        const detected: Record<string, boolean> = {}

        for (const capability of capabilities()) {
            const available = capability.detect()
            detected[capability.name] = available
            if (available) {
                exports[capability.name] = capability.implementation
            } else {
                console.warn(`[!] capability '${capability.name}' unavailable`)
            }
        }

        // Returns all capabilities and whether they are available.
        exports[Builtins.CAPABILITIES] = () =>
            Il2Cpp.perform(() => {
                const snapshot: Record<string, boolean> = {}
                for (const capability of capabilities()) {
                    snapshot[capability.name] = capability.detect()
                }
                return snapshot
            })

        console.log("[+] RPC exports:", Object.keys(exports))

        console.log("[+] Capabilities detected:", JSON.stringify(detected))
        sendEvent(Events.AGENT_READY, detected)
    })
}

setTimeout(bootstrap, 3000)

sendEvent(Events.AGENT_LOADED, null)
