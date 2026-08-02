import "frida-il2cpp-bridge"

import { capabilities } from "./helpers/capability"

// Import each capability module for its registration side effect.
import "./capabilities/getCurrentRenderPipeline"

/*
Design idea:
- Each capability (capabilities/*.ts) detects the assemblies/classes/methods it needs and, if present, registers the RPC it unlocks.
- On startup we probe every capability, register RPC for the ones available, and report the results. Adding a feature = one new file + one import above.
- Lookups are fail-soft and never cached (see resolve.ts): every probe and every RPC call re-resolves, since the GC may relocate runtime metadata.
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
                capability.register?.(exports)
            } else {
                console.warn(`[!] capability '${capability.name}' unavailable`)
            }
        }

        // Live snapshot of what the target supports; re-probes on every call.
        exports.capabilities = () => {
            Il2Cpp.perform(() => {
                const snapshot: Record<string, boolean> = {}
                for (const capability of capabilities()) {
                    snapshot[capability.name] = capability.detect()
                }
                return snapshot
            })
        }

        console.log("[+] RPC exports:", Object.keys(exports))

        console.log("[+] Capabilities detected:", JSON.stringify(detected))
        send({ type: "event", event: "agent_ready", data: detected })
    })
}

setTimeout(bootstrap, 3000)

send({ type: "event", event: "agent_loaded" })
