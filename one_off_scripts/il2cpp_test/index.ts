import "frida-il2cpp-bridge"

function perform() {
    Il2Cpp.perform(() => {
        console.log("[+] IL2CPP attached");
        console.log("Unity version: " + Il2Cpp.unityVersion);
        console.log("Module: " + Il2Cpp.module.name + " @ " + Il2Cpp.module.base);

        Il2Cpp.domain.assemblies.forEach(asm => {
            console.log("  asm: " + asm.name);
        });

        const asmCsharp = Il2Cpp.domain.assembly("Assembly-CSharp");
        if (!asmCsharp) {
            console.log("[-] Assembly-CSharp not found");
        }
        console.log("[+] Found Assembly-CSharp, class count: " + asmCsharp.image.classes.length);

        asmCsharp.image.classes.forEach(cls => {
            console.log("  class: " + cls.name);
        });

        const Core = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
        const Camera = Core.class("UnityEngine.Camera");

        const camera = Camera.method<Il2Cpp.Object>("get_main").invoke();
        if (camera.isNull()) {
            console.log("[!] main camera not found; aborting");
            return;
        }

        // log its position
        const transform = camera.method<Il2Cpp.Object>("get_transform").invoke();
        const position = transform.method<Il2Cpp.Object>("get_position").invoke();
        const posX = position.field("x").value as number;
        const posY = position.field("y").value as number;
        const posZ = position.field("z").value as number;
        console.log("[+] Main camera position: " + posX + ", " + posY + ", " + posZ);


        const tapRaycastClass = asmCsharp.image.class("TapRaycast");
        if (!tapRaycastClass) {
            console.log("[-] TapRaycast class not found");
            return;
        }
        console.log("[+] Found TapRaycast class, method count: " + tapRaycastClass.methods.length);

        const handleClickMethod = tapRaycastClass.method("handleClick");
        if (!handleClickMethod) {
            console.log("[-] handleClick method not found");
            return;
        }
        console.log("[+] Found handleClick method, hooking...");
        handleClickMethod.implementation = function () {
            console.log("[+] handleClick called, returning 'PlapPlap'");
            return Il2Cpp.string("PlapPlap");
        }
        console.log("[+] handleClick method hooked.");
    });
}

setTimeout(() => {
    perform();
    send({ type: "event", event: "agent_ready" });
}, 30000);

send({ type: "event", event: "agent_loaded" });