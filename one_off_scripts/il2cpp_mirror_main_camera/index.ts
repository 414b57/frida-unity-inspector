import "frida-il2cpp-bridge";

const WAIT_FRAMES = 10;   // frames to wait for the GPU readback before giving up
const MAX_FRAMES  = 30;   // hard cap on polling
const SWAP_RB     = false;   // set true if red/blue come out swapped

function perform(): void {
    Il2Cpp.perform(() => {
        Il2Cpp.mainThread.schedule(() => {
            console.log("[+] IL2CPP attached");

            const Core          = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
            const Camera        = Core.class("UnityEngine.Camera");
            const RenderTexture = Core.class("UnityEngine.RenderTexture");
            const CommandBuffer = Core.class("UnityEngine.Rendering.CommandBuffer");
            const Graphics      = Core.class("UnityEngine.Graphics");
            const RPM           = Core.class("UnityEngine.Rendering.RenderPipelineManager");
            const GF            = Core.class("UnityEngine.Experimental.Rendering.GraphicsFormat");

            const DST_FORMAT = GF.field(SWAP_RB ? "B8G8R8A8_UNorm" : "R8G8B8A8_UNorm").value as any;
            console.log("[+] dstFormat = " + DST_FORMAT);

            const inj = CommandBuffer.method("Internal_RequestAsyncReadback_5_Injected", 6);

            const camera = Camera.method<Il2Cpp.Object>("get_main").invoke();
            if (camera.isNull()) {
                console.log("[!] main camera not found; aborting");
                return;
            }

            // ---- One-time setup: RT, camera redirect, readback buffers ----
            const W       = camera.method<number>("get_pixelWidth").invoke();
            const H       = camera.method<number>("get_pixelHeight").invoke();
            const byteLen = W * H * 4;

            const rt = RenderTexture.alloc();
            rt.method(".ctor", 3).invoke(W, H, 24);
            camera.method("set_targetTexture", 1).invoke(rt);

            const dataBuf   = Memory.alloc(byteLen);
            const structPtr = Memory.alloc(16);
            structPtr.writePointer(dataBuf);        // nativeArrayBuffer @0
            structPtr.add(8).writeS64(byteLen);     // lengthInBytes    @8
            const cmd = CommandBuffer.new();

            console.log("[+] setup done, " + W + "x" + H + " (" + byteLen + " bytes)");

            // ---- Per-frame work ----
            const requestReadback = (): void => {
                cmd.method("Clear", 0).invoke();
                const selfPtr = cmd.field("m_Ptr").value as NativePointer;       // CommandBuffer native ptr
                const srcPtr  = rt.field("m_CachedPtr").value as NativePointer;   // UnityEngine.Object native ptr

                inj.invoke(
                    selfPtr,      // _unity_self  : IntPtr
                    srcPtr,       // src          : IntPtr
                    0,            // mipIndex
                    DST_FORMAT,   // dstFormat
                    ptr(0), // callback     : null Action
                    structPtr,    // nativeArrayData*
                );

                Graphics.method("ExecuteCommandBuffer", 1).invoke(cmd);
                console.log("[+] readback requested; waiting up to " + WAIT_FRAMES + " frames");
            };

            // True once the GPU has written something to dataBuf.
            const readbackReady = (): boolean =>
                new Uint8Array(dataBuf.readByteArray(64)!).some(v => v !== 0);

            const sendFrame = (): void => {
                const buf = dataBuf.readByteArray(byteLen)!;
                send({ type: "frame", width: W, height: H, format: SWAP_RB ? "BGRA" : "RGBA" }, buf);
                console.log("[+] sent raw frame (" + byteLen + " bytes)");
            };

            const restoreCamera = (): void => {
                camera.method("set_targetTexture", 1).invoke(ptr(0));
            };

            // ---- Hook: only orchestrates timing, holds no setup logic ----
            let frame = -1;
            let done  = false;
            const hooked = RPM.method("EndCameraRendering", 2);

            hooked.implementation = function (ctx, cam: Il2Cpp.Object) {
                const ret = this.method("EndCameraRendering", 2).invoke(ctx, cam);
                if (done || !cam.handle.equals(camera.handle)) return ret;

                try {
                    frame++;
                    if (frame === 0) {
                        requestReadback();
                    } else if (frame >= WAIT_FRAMES) {
                        if (readbackReady()) {
                            sendFrame();
                            restoreCamera();
                            done = true;
                        } else if (frame >= MAX_FRAMES) {
                            console.log("[!] readback never landed; giving up");
                            restoreCamera();
                            done = true;
                        }
                    }
                } catch (e: any) {
                    console.log("[!] " + e + "\n" + e.stack);
                }
                return ret;
            };

            console.log("[+] hook installed; capturing…");
        });
    }, "main");
}

setTimeout(() => {
    perform();
    send({ type: "event", event: "agent_ready" });
}, 4000);

send({ type: "event", event: "agent_loaded" });