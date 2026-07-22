from __future__ import annotations

import os
import frida
from PIL import Image
import numpy as np
import cv2

package_name = "com.PlapPlap.FridaTestingEnv"

def process_frame(meta, data):
    w, h = meta["width"], meta["height"]
    if len(data) != w * h * 4:
        return None
    arr = np.frombuffer(data, np.uint8).reshape(h, w, 4)
    return arr[::-1]  # flip vertically, zero-copy view

def render_frame(arr, fmt):
    small = arr[::4, ::4]
    code = cv2.COLOR_RGBA2BGR if fmt == "RGBA" else cv2.COLOR_BGRA2BGR
    cv2.imshow("Frame", cv2.cvtColor(small, code))
    cv2.waitKey(1)

def on_message(message: any, data: bytes | None) -> None:
    payload = message.get("payload") or {}
    mtype = payload.get("type")

    if mtype == "frame":
        if not data:
            print("[!] frame message had no binary payload")
            return
        frame_img = process_frame(payload, data)
        if frame_img is None:
            print("[!] failed to process frame")
            return
        render_frame(frame_img, payload.get("format", "RGBA"))
    elif mtype == "event":
        print(f"[event] {payload.get('event')}, data: {data}")
    else:
        print(f"Received message: {message}, data: {data}")


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

# input("Press Enter to exit...\n")

print("Type `x/y/z`=`value` to set camera position, `rx/ry/rz`=`value` to set rotation, `fov`=`value` to set field of view, or `exit` to quit.")
while True:
    try:
        cmd = input("> ").strip()
        if cmd == "exit":
            break
        if "=" not in cmd:
            print("Invalid command. Use `x/y/z`=`value`, `rx/ry/rz`=`value`, or `fov`=`value`.")
            continue
        key, value = cmd.split("=", 1)
        key = key.strip()
        value = float(value.strip())
        script.post({"type": "set_camera", "payload": {"key": key, "value": value}})
    except Exception as e:
        print(f"Error: {e}")