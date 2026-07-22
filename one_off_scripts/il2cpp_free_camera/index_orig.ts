import "frida-il2cpp-bridge";

const WAIT_FRAMES = 10;   // frames to wait for the GPU readback before giving up
let frameCount = -2; // frames since last readback request
const SWAP_RB     = false;   // set true if red/blue come out swapped

function perform(): void {
    Il2Cpp.perform(() => {
        console.log("perform entered");          // if this misses, it's perform/domain
        const t = Il2Cpp.mainThread;
        console.log("mainThread:", t.id);        // if this misses, it's the thread lookup
        t.schedule(() => console.log("scheduled"));
    });

    Il2Cpp.perform(() => {
        console.log("[+] IL2CPP attached, thread:", Il2Cpp.currentThread?.id);

        Il2Cpp.mainThread.schedule(() => {
            console.log("[+] IL2CPP main thread scheduled, thread:", Il2Cpp.currentThread?.id);
            const Core = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
            // For obj
            const GameObject = Core.class("UnityEngine.GameObject");
            const Camera = Core.class("UnityEngine.Camera");
            const Transform = Core.class("UnityEngine.Transform");
            const Vector3 = Core.class("UnityEngine.Vector3");
            const Quaternion = Core.class("UnityEngine.Quaternion");

            // For rendering / getting the image
            const RenderTexture = Core.class("UnityEngine.RenderTexture");
            const CommandBuffer = Core.class("UnityEngine.Rendering.CommandBuffer");
            const Graphics = Core.class("UnityEngine.Graphics");
            const RPM = Core.class("UnityEngine.Rendering.RenderPipelineManager");
            const GF = Core.class("UnityEngine.Experimental.Rendering.GraphicsFormat");

            const DST_FORMAT = GF.field(SWAP_RB ? "B8G8R8A8_UNorm" : "R8G8B8A8_UNorm").value as any;

            const inj = CommandBuffer.method("Internal_RequestAsyncReadback_5_Injected", 6);

            // Setup Freecam
            const spawnPos = Vector3.alloc()
            spawnPos.method(".ctor", 3).invoke(5, 1, -10);
            spawnPos.ref(true)

            const freecamGO = GameObject.alloc();
            freecamGO.method(".ctor", 1).invoke(Il2Cpp.string("Freecam_Injected"));
            freecamGO.ref(true)

            const freecamCamera = freecamGO.method<Il2Cpp.Object>("AddComponent", 1).invoke(Camera.type.object);
            console.log("[+] Freecam camera created: " + freecamCamera);
            freecamCamera.ref(true)

            const freecamTransform = freecamGO.method<Il2Cpp.Object>("get_transform", 0).invoke();
            // Log: [info] Method: System.Void set_position(UnityEngine.Vector3 value); // 0x03007988
            freecamTransform.method("set_position", 1).invoke(spawnPos.unbox());
            freecamTransform.ref(true)

            console.log("[+] Freecam created at " + spawnPos.method("ToString", 0).invoke().toString());

            // Setup rendering pipeline
            const W = freecamCamera.method<number>("get_pixelWidth").invoke();
            const H = freecamCamera.method<number>("get_pixelHeight").invoke();
            const BYTE_LEN = W * H * 4;
            console.log("[+] Freecam resolution: " + W + "x" + H + " (" + BYTE_LEN + " bytes)");

            const rt = RenderTexture.alloc();
            rt.method(".ctor", 3).invoke(W, H, 24);
            rt.ref(true)

            const dataBuf = Memory.alloc(BYTE_LEN)
            const structPtr = Memory.alloc(16);
            structPtr.writePointer(dataBuf); // nativeArrayBuffer @0
            structPtr.add(8).writeS64(BYTE_LEN); // lengthInBytes @8
            const cmd = CommandBuffer.new();
            cmd.ref(true)

            console.log("[+] Rendering setup done");

            // Connect camera to render pipeline
            freecamCamera.method("set_targetTexture", 1).invoke(rt);

            console.log("[+] Freecam connected to render pipeline");

            // Hook into the end-of-frame callback to poll for the readback result
            const hooked = RPM.method("EndCameraRendering", 2);

            hooked.implementation = function (ctx, cam: Il2Cpp.Object) {
                const ret = this.method("EndCameraRendering", 2).invoke(ctx, cam);

                if (!cam.handle.equals(freecamCamera.handle)) return ret; // Only poll for the freecam

                // console.log("[+] EndCameraRendering called for camera: " + cam);
                // console.log("[+] EndCameraRendering called with context: " + ctx);

                try {
                    frameCount++;
                    const readbackReady = new Uint8Array(dataBuf.readByteArray(BYTE_LEN)!).some(v => v !== 0);
                    if (readbackReady) {
                        console.log("[+] Readback ready, sending image data (" + BYTE_LEN + " bytes)");
                        const imageData = dataBuf.readByteArray(BYTE_LEN);
                        send({type: "frame", width: W, height: H, format: SWAP_RB ? "BGRA" : "RGBA"}, imageData);
                        dataBuf.writeByteArray(new Uint8Array(BYTE_LEN));
                        // Reset frame cont, so can query another readback next frame
                        frameCount = -2;
                    } else if (frameCount > WAIT_FRAMES || frameCount < 0) {
                        console.log("[+] " + frameCount + " / " + WAIT_FRAMES + " frames passed, requesting readback");
                        cmd.method("Clear", 0).invoke();
                        const selfPtr = cmd.field("m_Ptr").value as NativePointer; // CommandBuffer native ptr
                        const srcPtr = rt.field("m_CachedPtr").value as NativePointer; // UnityEngine.Object native ptr
                        inj.invoke(
                            selfPtr,      // _unity_self  : IntPtr
                            srcPtr,       // src          : IntPtr
                            0,            // mipIndex
                            DST_FORMAT,   // dstFormat
                            ptr(0),       // callback     : null Action
                            structPtr,    // nativeArrayData*
                        );

                        Graphics.method("ExecuteCommandBuffer", 1).invoke(cmd);
                        console.log("[+] Readback requested");
                        frameCount = 0;
                    }
                } catch (e) {
                    console.error("[!] Error in EndCameraRendering hook: " + e);
                }

                return ret;
            };

            console.log("[+] Hooked into EndCameraRendering");

            // Setup controls
            function setCameraInputLoop() {
                recv("set_camera", (message) => {
                    setCameraInputLoop()
                    console.log(message.payload.key);
                    console.log(message.payload.value);

                    // Pos
                    if (message.payload.key === "x") {
                        const pos = freecamTransform.method<Il2Cpp.Object>("get_position", 0).invoke();
                        pos.field("x").value = message.payload.value;
                        freecamTransform.method("set_position", 1).invoke(pos);
                    } else if (message.payload.key === "y") {
                        const pos = freecamTransform.method<Il2Cpp.Object>("get_position", 0).invoke();
                        pos.field("y").value = message.payload.value;
                        freecamTransform.method("set_position", 1).invoke(pos);
                    } else if (message.payload.key === "z") {
                        const pos = freecamTransform.method<Il2Cpp.Object>("get_position", 0).invoke();
                        pos.field("z").value = message.payload.value;
                        freecamTransform.method("set_position", 1).invoke(pos);
                    }
                    // Rot
                    // TODO

                    // FOV
                    // TODO
                });
            }
            setCameraInputLoop();
            console.log("[+] Camera input loop set up");
        });
    });
}

setTimeout(() => {
    perform();
    send({ type: "event", event: "agent_ready" });
}, 4000);

send({ type: "event", event: "agent_loaded" });