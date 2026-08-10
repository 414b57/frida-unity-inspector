import "frida-il2cpp-bridge"

import { defineCapability } from "../helpers/capability"
import { Capabilities } from "../helpers/protocol"
import { assembly, klass, method } from "../helpers/resolve"

defineCapability({
    name: Capabilities.SET_GAMEOBJECT_ACTIVE,

    detect: () => method("UnityEngine.CoreModule", "UnityEngine.GameObject", "SetActive", 1) !== null,

    implementation: (gameobject_handle_ptr: string, active: boolean) =>
        Il2Cpp.perform(() => {
            const go = new Il2Cpp.Object(ptr(gameobject_handle_ptr));
            const method = go.tryMethod<void>("SetActive", 1);
            if (method === null) {
                return false
            }
            method?.invoke(active);
            return true;
        }),
})
