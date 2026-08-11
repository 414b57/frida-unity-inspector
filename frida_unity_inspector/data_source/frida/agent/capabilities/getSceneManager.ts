import "frida-il2cpp-bridge"

import { defineCapability } from "../helpers/capability"
import { Capabilities } from "../helpers/protocol"
import { klass } from "../helpers/resolve"

function sceneManagerClass(): Il2Cpp.Class | null {
    return klass("UnityEngine.CoreModule", "UnityEngine.SceneManagement.SceneManager")
}

defineCapability({
    name: Capabilities.GET_SCENE_MANAGER,
    detect: () => sceneManagerClass() !== null,

    implementation: () => Il2Cpp.perform(() => sceneManagerClass(), "main"),
})
