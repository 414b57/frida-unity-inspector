import "frida-il2cpp-bridge"

import { defineCapability, getCapability } from "../helpers/capability"
import { Capabilities } from "../helpers/protocol"
import { method } from "../helpers/resolve"

/*
 * Unity can have several scenes loaded at once (e.g. additive scene loading).
 * This walks SceneManager.sceneCount / GetSceneAt(i) and returns every scene
 * that reports itself as loaded. Each returned Scene is an Il2Cpp.ValueType
 * struct - callers (e.g. getHierarchyStructure) parse it further.
 */

defineCapability({
    name: Capabilities.GET_LOADED_SCENES,

    detect: () =>
        method("UnityEngine.CoreModule", "UnityEngine.SceneManagement.SceneManager", "GetSceneAt") !== null &&
        method("UnityEngine.CoreModule", "UnityEngine.SceneManagement.SceneManager", "get_sceneCount") !== null,

    implementation: () =>
        Il2Cpp.perform(async () => {
            const sceneManager: Il2Cpp.Class | null = await getCapability(Capabilities.GET_SCENE_MANAGER)() // Should never be null, but just in case
            if (sceneManager === null) return []

            const getSceneCount = sceneManager.tryMethod<number>("get_sceneCount")
            const getSceneAt = sceneManager.tryMethod<Il2Cpp.ValueType>("GetSceneAt")
            if (getSceneCount === null || getSceneAt === null) return []

            const count = getSceneCount.invoke()
            const scenes: Il2Cpp.ValueType[] = []
            for (let i = 0; i < count; i++) {
                const scene = getSceneAt.invoke(i)
                const isLoaded = scene.tryMethod<boolean>("get_isLoaded")?.invoke() ?? false
                if (isLoaded) scenes.push(scene)
            }
            return scenes
        }),
})
