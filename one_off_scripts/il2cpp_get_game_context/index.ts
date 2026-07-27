import "frida-il2cpp-bridge"

function perform() {
    Il2Cpp.perform(() => {
        console.log("[+] IL2CPP attached");

        // Unity Version
        console.log("[+] Unity Version: " + Il2Cpp.unityVersion);

        const Core = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
        const RPM  = Core.class("UnityEngine.Rendering.RenderPipelineManager");

        // console.log("[+] RenderPipelineManager: " + RPM);
        console.log("currentPipeline:", RPM.method("get_currentPipeline").invoke());


        // Get current scene and root objs
        // const Core = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;

        const sceneManager = Core.class("UnityEngine.SceneManagement.SceneManager");
        const getActiveScene = sceneManager.method<Il2Cpp.ValueType>("GetActiveScene");
        const activeScene = getActiveScene.invoke();
        console.log("[+] Active Scene: " + activeScene);

        const rootGameObjects = activeScene.box() // Convert from ValueType to Object, so can call GetRootGameObjects
            .method<Il2Cpp.Array<Il2Cpp.Object>>("GetRootGameObjects", 0)
            .invoke();

        console.log("[+] Root GameObjects: " + rootGameObjects.length);

        // @ts-ignore
        for (const go of rootGameObjects) {
            // @ts-ignore
            console.log("    - " + go.method<Il2Cpp.String>("get_name").invoke());
        }
    });
}

setTimeout(() => {
    perform();
    send({ type: "event", event: "agent_ready" });
}, 3000);

send({ type: "event", event: "agent_loaded" });