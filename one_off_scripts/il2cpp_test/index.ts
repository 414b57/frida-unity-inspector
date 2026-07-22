import "frida-il2cpp-bridge"

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
    console.log("[+] Found Assembly-CSharp, class count: " +  asmCsharp.image.classes.length);

    asmCsharp.image.classes.forEach(cls => {
        console.log("  class: " + cls.name);
    });

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

send({ type: "event", event: "agent_ready" });