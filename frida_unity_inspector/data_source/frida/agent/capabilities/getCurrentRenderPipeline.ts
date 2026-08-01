import "frida-il2cpp-bridge"

import { defineCapability } from "../helpers/capability"
import { method } from "../helpers/resolve"

function currentPipelineGetter(): Il2Cpp.Method<Il2Cpp.Object> | null {
    return method<Il2Cpp.Object>("UnityEngine.CoreModule", "UnityEngine.Rendering.RenderPipelineManager", "get_currentPipeline")
}

defineCapability({
    name: "getCurrentRenderPipeline",
    detect: () => currentPipelineGetter() !== null,

    register(exports) {
        exports.getCurrentRenderPipeline = () =>
            Il2Cpp.perform(() => {
                const getter = currentPipelineGetter()
                if (getter === null) return null
                const pipeline = getter.invoke()
                // if null then it's the built-in pipeline
                if (pipeline.isNull()) return null
                // if not null then its URP/HDRP/SRP
                return pipeline.class.name
            })
    },
})
