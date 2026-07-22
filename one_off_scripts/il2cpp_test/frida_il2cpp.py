from __future__ import annotations

import os
import frida

package_name = 'com.PlapPlap.FridaTestingEnv'
# package_name = 'com.master.triple3d.find'

def on_message(message: any, data: bytes | None) -> None:
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

if not os.path.exists("./_agent.js"):
    raise FileNotFoundError("The _agent.js file was not found in the current directory, run `npm run build` first to generate it.")

raw = open("./_agent.js", "r").read()
print(f"Loaded script from _agent.js, length: {len(raw)} characters")

script = session.create_script(raw)
script.on('message', on_message)
script.on('destroyed', on_destroyed)
script.set_log_handler(on_log)
script.load()

device.resume(pid)

input("Press Enter to exit...\n")