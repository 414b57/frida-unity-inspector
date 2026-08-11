import "frida-il2cpp-bridge"

import { defineCapability, getCapability } from "../helpers/capability"
import { Capabilities } from "../helpers/protocol"
import { method } from "../helpers/resolve"

defineCapability({
    name: Capabilities.GET_CURRENT_SCENE,

    detect: () => method("UnityEngine.CoreModule", "UnityEngine.SceneManagement.SceneManager", "GetActiveScene") !== null,

    implementation: () =>
        Il2Cpp.perform(async () => {
            const sceneManager: Il2Cpp.Class | null = await getCapability(Capabilities.GET_SCENE_MANAGER)() // Should never be null, but just in case
            if (sceneManager === null) return null

            const getActiveScene = sceneManager.tryMethod<Il2Cpp.ValueType>("GetActiveScene")
            if (getActiveScene === null) return null

            return getActiveScene.invoke()
        }, "main"),
})
