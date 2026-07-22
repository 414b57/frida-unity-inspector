from __future__ import annotations

import os
import frida
from PIL import Image
import numpy as np
import cv2

import threading, collections, re, sys

latest = collections.deque(maxlen=1)   # drop stale frames

# package_name = "com.PlapPlap.FridaTestingEnv"
package_name = 'com.master.triple3d.find'

def process_frame(meta, data):
    w, h = meta["width"], meta["height"]
    if len(data) != w * h * 4:
        return None
    arr = np.frombuffer(data, np.uint8).reshape(h, w, 4)
    return arr[::-1]  # flip vertically, zero-copy view

_window_initialized = False

def render_frame(arr, fmt):
    global _window_initialized

    code = cv2.COLOR_RGBA2BGR if fmt == "RGBA" else cv2.COLOR_BGRA2BGR

    if not _window_initialized:
        cv2.namedWindow("Frame", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(
            "Frame",
            cv2.WND_PROP_TOPMOST,
            1
        )
        _window_initialized = True

    cv2.imshow("Frame", cv2.cvtColor(arr, code))
    cv2.waitKey(1)

import time
_n, _t = 0, time.time()

def on_message(message, data):
    global _n, _t
    if message["type"] != "send":
        print("Log:", message); return
    p = message["payload"]
    if p.get("type") == "frame":
        _n += 1
        if _n % 30 == 0:
            print(f"[recv] {30/(time.time()-_t):.1f} fps")
            _t = time.time()
        latest.append((p, data))
        script.post({"type": "frame_ack"})


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
PAT = re.compile(r"^(x|y|z|rx|ry|rz|fov)\s*=\s*(-?\d+(?:\.\d+)?)$")

def input_loop():
    while True:
        cmd = input("> ").strip()
        if cmd == "exit":
            break
        m = PAT.match(cmd)
        if not m:
            print("Invalid command. Use `x/y/z`=`value`, `rx/ry/rz`=`value`, or `fov`=`value`.")
            continue
        script.post({"type": "set_camera", "payload": {m.group(1): float(m.group(2))}})

t = threading.Thread(target=input_loop, daemon=True)
t.start()

while True:
    try:
        meta, data = latest.pop()
    except IndexError:
        cv2.waitKey(1)          # keep the window pumping when idle
        continue
    arr = process_frame(meta, data)
    if arr is not None:
        render_frame(arr, meta["format"])