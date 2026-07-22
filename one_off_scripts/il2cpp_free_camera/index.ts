import "frida-il2cpp-bridge";

const SWAP_RB     = false;  // set true if red/blue come out swapped
const NBUF        = 3;      // readback slots in flight
const SCALE       = 4;      // render at 1/SCALE resolution (1 = full)
const WAIT_FRAMES = 30;     // frames before a stuck slot is recycled
const MAX_INFLIGHT = 2;     // unacked frames allowed on the wire

const now = () => Date.now();

class Stat {
    private n = 0; private sum = 0; private max = 0;
    constructor(private label: string, private every = 60) {}
    add(ms: number) {
        this.n++; this.sum += ms; if (ms > this.max) this.max = ms;
        if (this.n >= this.every) {
            console.log(`[T] ${this.label}: avg ${(this.sum / this.n).toFixed(2)} ms, max ${this.max} ms over ${this.n}`);
            this.n = 0; this.sum = 0; this.max = 0;
        }
    }
}

const statHook  = new Stat("hook total");
const statDrain = new Stat("drain+send");
const statFps   = new Stat("freecam frame interval");
const statLat   = new Stat("input -> applied");

type Pose = { x?: number; y?: number; z?: number; rx?: number; ry?: number; rz?: number; fov?: number };
const POSE_KEYS = ["x", "y", "z", "rx", "ry", "rz", "fov"] as const;

let pendingPose: Pose | null = null;
let pendingPoseTs = 0;
let inFlight = 0;

// ---- message loops: re-arm FIRST, always -----------------------------------
function cameraLoop() {
    recv("set_camera", (message) => {
        cameraLoop();
        const p = message.payload as Pose & { key?: string; value?: number };
        const merged: Pose = pendingPose ?? {};
        if (p.key !== undefined && p.value !== undefined) {
            (merged as any)[p.key] = p.value;          // legacy single-key form
        } else {
            for (const k of POSE_KEYS) if (p[k] !== undefined) merged[k] = p[k];
        }
        if (!pendingPose) pendingPoseTs = now();
        pendingPose = merged;
    });
}

function ackLoop() {
    recv("frame_ack", () => {
        ackLoop();
        if (inFlight > 0) inFlight--;
    });
}

function perform(): void {
    Il2Cpp.perform(() => {
        console.log("[+] IL2CPP attached, thread:", Il2Cpp.currentThread?.id, " | version:", Il2Cpp.unityVersion);

        const Core = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
        const RPM  = Core.class("UnityEngine.Rendering.RenderPipelineManager");

        RPM.methods.forEach(m =>
            console.log((m.isStatic ? "static " : "") + m.returnType.name + " " + m.name + " /" + m.parameters.length));

        // null => built-in pipeline; non-null => URP/HDRP/SRP
        console.log("currentPipeline:", RPM.method("get_currentPipeline").invoke());

        const Camera = Core.class("UnityEngine.Camera");
        // debug log all methods:
        Camera.methods.forEach((m) => {
            console.log(m)
        });


        const tSched = now();
        Il2Cpp.mainThread.schedule(() => {
            console.log(`[T] schedule -> main thread: ${now() - tSched} ms`);
            const tSetup = now();

            const Core = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
            const GameObject    = Core.class("UnityEngine.GameObject");
            const Camera        = Core.class("UnityEngine.Camera");
            const Vector3       = Core.class("UnityEngine.Vector3");
            const RenderTexture = Core.class("UnityEngine.RenderTexture");
            const CommandBuffer = Core.class("UnityEngine.Rendering.CommandBuffer");
            const Graphics      = Core.class("UnityEngine.Graphics");
            const RPM           = Core.class("UnityEngine.Rendering.RenderPipelineManager");
            const GF            = Core.class("UnityEngine.Experimental.Rendering.GraphicsFormat");

            const DST_FORMAT = GF.field(SWAP_RB ? "B8G8R8A8_UNorm" : "R8G8B8A8_UNorm").value as any;
            const inj = CommandBuffer.method("Internal_RequestAsyncReadback_5_Injected", 6);

            // ---- freecam ---------------------------------------------------
            const spawnPos = Vector3.alloc();
            // spawnPos.method(".ctor", 3).invoke(0, 1, -10);
            spawnPos.method(".ctor", 3).invoke(0, 10, -5);
            spawnPos.ref(true);

            const go = GameObject.alloc();
            go.method(".ctor", 1).invoke(Il2Cpp.string("Freecam_Injected"));
            go.ref(true);

            const freecamCamera = go.method<Il2Cpp.Object>("AddComponent", 1).invoke(Camera.type.object);
            freecamCamera.ref(true);

            const freecamTransform = go.method<Il2Cpp.Object>("get_transform", 0).invoke();
            freecamTransform.method("set_position", 1).invoke(spawnPos.unbox());
            freecamTransform.ref(true);

            // ---- render target ---------------------------------------------
            const W = Math.max(1, (freecamCamera.method<number>("get_pixelWidth").invoke()  / SCALE) | 0);
            const H = Math.max(1, (freecamCamera.method<number>("get_pixelHeight").invoke() / SCALE) | 0);
            const BYTE_LEN = W * H * 4;
            console.log(`[+] Freecam target: ${W}x${H} (${BYTE_LEN} bytes) x${NBUF} slots`);

            const rt = RenderTexture.alloc();
            rt.method(".ctor", 3).invoke(W, H, 24);
            rt.ref(true);

            interface Slot {
                data: NativePointer; struct: NativePointer; flag: NativePointer;
                pending: boolean; age: number;
            }
            const slots: Slot[] = [];
            for (let i = 0; i < NBUF; i++) {
                const data = Memory.alloc(BYTE_LEN);
                const struct = Memory.alloc(16);
                struct.writePointer(data);
                struct.add(8).writeS64(BYTE_LEN);
                slots.push({ data, struct, flag: data.add(BYTE_LEN - 4), pending: false, age: 0 });
            }
            let nextSlot = 0;

            const cmd = CommandBuffer.new();
            cmd.ref(true);

            freecamCamera.method("set_targetTexture", 1).invoke(rt);

            // ---- cached handles --------------------------------------------
            const mCmdClear = cmd.method("Clear", 0);
            const mExecCB   = Graphics.method("ExecuteCommandBuffer", 1);
            const mGetPos   = freecamTransform.method<Il2Cpp.Object>("get_position", 0);
            const mSetPos   = freecamTransform.method("set_position", 1);
            // const mGetEuler = freecamTransform.method<Il2Cpp.Object>("get_eulerAngles", 0);
            // const mSetEuler = freecamTransform.method("set_eulerAngles", 1);
            // const mSetFov   = freecamCamera.method("set_fieldOfView", 1);
            const camHandle = freecamCamera.handle;
            const FMT = SWAP_RB ? "BGRA" : "RGBA";

            function applyPose(p: Pose) {
                if (p.x !== undefined || p.y !== undefined || p.z !== undefined) {
                    const pos = mGetPos.invoke();
                    if (p.x !== undefined) pos.field("x").value = p.x;
                    if (p.y !== undefined) pos.field("y").value = p.y;
                    if (p.z !== undefined) pos.field("z").value = p.z;
                    mSetPos.invoke(pos);
                }
                // if (p.rx !== undefined || p.ry !== undefined || p.rz !== undefined) {
                //     const rot = mGetEuler.invoke();
                //     if (p.rx !== undefined) rot.field("x").value = p.rx;
                //     if (p.ry !== undefined) rot.field("y").value = p.ry;
                //     if (p.rz !== undefined) rot.field("z").value = p.rz;
                //     mSetEuler.invoke(rot);
                // }
                // if (p.fov !== undefined) mSetFov.invoke(p.fov);
            }

            function requestInto(slot: Slot) {
                mCmdClear.invoke();
                inj.invoke(
                    cmd.field("m_Ptr").value as NativePointer,
                    rt.field("m_CachedPtr").value as NativePointer,
                    0, DST_FORMAT, ptr(0), slot.struct,
                );
                mExecCB.invoke(cmd);
                slot.pending = true;
                slot.age = 0;
            }

            // ---- hook -------------------------------------------------------
            const hooked = RPM.method("EndCameraRendering", 2);
            let lastFrameTs = 0;

            hooked.implementation = function (ctx, cam: Il2Cpp.Object) {
                if (!cam.handle.equals(camHandle)) return hooked.invoke(ctx, cam);

                const tHook = now();

                // Newest input applied before the render pass we're about to capture.
                if (pendingPose) {
                    try {
                        applyPose(pendingPose);
                        statLat.add(now() - pendingPoseTs);
                    } catch (e) { console.error("[!] applyPose: " + e); }
                    pendingPose = null;
                }

                const ret = hooked.invoke(ctx, cam);

                if (lastFrameTs) statFps.add(now() - lastFrameTs);
                lastFrameTs = now();

                try {
                    const tDrain = now();
                    for (const s of slots) {
                        if (!s.pending) continue;
                        s.age++;
                        if (s.flag.readU32() !== 0) {
                            if (inFlight < MAX_INFLIGHT) {
                                send({ type: "frame", width: W, height: H, format: FMT },
                                     s.data.readByteArray(BYTE_LEN));
                                inFlight++;
                            }
                            // Drop the frame if the consumer is behind; slot is freed either way.
                            s.flag.writeU32(0);
                            s.pending = false;
                        } else if (s.age > WAIT_FRAMES) {
                            s.flag.writeU32(0);
                            s.pending = false;
                        }
                    }
                    statDrain.add(now() - tDrain);

                    const s = slots[nextSlot];
                    if (!s.pending) {
                        requestInto(s);
                        nextSlot = (nextSlot + 1) % NBUF;
                    }
                } catch (e) {
                    console.error("[!] Error in EndCameraRendering hook: " + e);
                }

                statHook.add(now() - tHook);
                return ret;
            };

            console.log("[+] Hooked into EndCameraRendering");
            console.log(`[T] TOTAL main-thread setup: ${now() - tSetup} ms`);
        });
    });
}

cameraLoop();
ackLoop();

setTimeout(() => {
    perform();
    send({ type: "event", event: "agent_ready" });
}, 4000);

send({ type: "event", event: "agent_loaded" });