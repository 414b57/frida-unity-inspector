from __future__ import annotations

import os
import frida
from PIL import Image

package_name = "com.PlapPlap.FridaTestingEnv"
OUTPUT_PATH  = "frame.png"

# NOTE: FUCK unity/compilers that strip out unusued functions.
# It would of been so nice and easy to do this, if could use `Camera.render()`, but could work around, just wait for normal frame to render.
# But not having access to `Texture2d.ReadPixels()` is a pain in the fucking ass. And didnt have access to any of its similar functions
# Took me a couple hours to find a function that would work, AND was not stripped out. That was `CommandBuffer.RequestAsyncReadbackIntoNativeArray`
# Ofc couldnt be that easy, had to find its specific injected one - `Internal_RequestAsyncReadback_5_Injected`
# That method moves the rendered image from the GPU renderTexture to a CPU readable native array. Then read said array, and send it to here.
# Then convert raw RGBA image data to a PNG and save it. Then open it in the default image viewer.
# Also works out nicey/faster (i think). As readpixels is a blocking call, while this is async. So if did freecam, should be more responsive.

def save_frame(meta: dict, data: bytes) -> None:
    w, h = meta["width"], meta["height"]
    fmt  = meta.get("format", "RGBA")

    expected = w * h * 4
    if len(data) != expected:
        print(f"[!] size mismatch: got {len(data)}, expected {expected} ({w}x{h})")
        return

    img = Image.frombytes("RGBA", (w, h), data, "raw", fmt)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)   # Unity readback is bottom-up
    img.save(OUTPUT_PATH)
    print(f"[+] saved {OUTPUT_PATH} ({w}x{h}, {fmt})")

    img.show()


def on_message(message: any, data: bytes | None) -> None:
    if message["type"] == "error":
        print(f"[error] {message.get('description', message)}")
        return

    payload = message.get("payload") or {}
    mtype = payload.get("type")

    if mtype == "frame":
        if not data:
            print("[!] frame message had no binary payload")
            return
        save_frame(payload, data)
    elif mtype == "event":
        print(f"[event] {payload.get('event')}")
    else:
        print(f"[message] {payload}")


def on_destroyed():
    print("Script destroyed")


def on_log(level: str, text: str) -> None:
    print(f"Log: [{level}] {text}")

device = frida.get_usb_device()
print(f"Connected to device: {device.name}")

pid = device.spawn([package_name])
print(f"Spawned process with PID: {pid}")

session = device.attach(pid)
print(f"Attached to process: {package_name}")

raw = open("./_agent.js", "r").read()
print(f"Loaded script from _agent.js, length: {len(raw)} characters")

script = session.create_script(raw)
script.on("message", on_message)
script.on("destroyed", on_destroyed)
script.set_log_handler(on_log)
script.load()

device.resume(pid)

input("Press Enter to exit...\n")
