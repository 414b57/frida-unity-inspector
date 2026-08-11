import "frida-il2cpp-bridge"

import { defineCapability } from "../helpers/capability"
import { Capabilities } from "../helpers/protocol"
import { method } from "../helpers/resolve"
import {getKnownComponent} from "../helpers/properties";

defineCapability({
    name: Capabilities.SET_COMPONENT_ENABLED,

    detect: () => method("UnityEngine.CoreModule", "UnityEngine.Behaviour", "set_enabled", 1) !== null,

    implementation: (component_handle_ptr: string, active: boolean) =>
        Il2Cpp.perform(() => {
            const comp = getKnownComponent(component_handle_ptr);
            if (comp === null) {
                console.warn(`Failed to find Component with handle ${component_handle_ptr}`);
                return false
            }
            const method = comp.tryMethod<void>("set_enabled", 1);
            if (method === null) {
                console.warn(`Failed to find set_enabled method on Component with handle ${component_handle_ptr}`);
                return false
            }
            method?.invoke(active);
            return true;
        }),
})
