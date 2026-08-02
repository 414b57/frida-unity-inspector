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
                // Ugly way - but cba to mess around with backend rn. Just want to begin implementing features. TODO - Improve.
                snapshot[Builtins.CAPABILITIES] = true
                snapshot[Builtins.VERSION] = true
                snapshot[Builtins.UNITY_VERSION] = true
                snapshot[Builtins.PING] = true
                return snapshot
            })
        detected[Builtins.CAPABILITIES] = true

        // Returns current version of agent
        exports[Builtins.VERSION] = () => {
            return "0.1.0"
        }
        detected[Builtins.VERSION] = true

        // Returns current unity version of the target process
        exports[Builtins.UNITY_VERSION] = () => {
            return Il2Cpp.unityVersion
        }
        detected[Builtins.UNITY_VERSION] = true

        // Ping
        exports[Builtins.PING] = (unix_epoch_seconds: number) => {
            const now = Date.now() / 1000
            return [now-unix_epoch_seconds, now]
        }
        detected[Builtins.PING] = true

        console.log("[+] RPC exports:", Object.keys(exports))

        console.log("[+] Capabilities detected:", JSON.stringify(detected))
        sendEvent(Events.AGENT_READY, detected)
    })
}

setTimeout(bootstrap, 3000)

sendEvent(Events.AGENT_LOADED, null)
