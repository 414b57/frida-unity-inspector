import "frida-il2cpp-bridge"

import { defineCapability } from "../helpers/capability"
import { Capabilities } from "../helpers/protocol"
import { method } from "../helpers/resolve"

defineCapability({
    name: Capabilities.SET_COMPONENT_ENABLED,

    detect: () => method("UnityEngine.CoreModule", "UnityEngine.Behaviour", "set_enabled", 1) !== null,

    implementation: (component_handle_ptr: string, active: boolean) =>
        Il2Cpp.perform(() => {
            const comp = new Il2Cpp.Object(ptr(component_handle_ptr));
            const method = comp.tryMethod<void>("set_enabled", 1);
            if (method === null) {
                return false
            }
            method?.invoke(active);
            return true;
        }),
})
