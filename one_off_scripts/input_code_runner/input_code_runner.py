from __future__ import annotations

import os
import subprocess
import threading
import frida

"""
HOT-Reload Notes:
- Enter to run code.ts (or r <path> to run a specific file)
- q/exit to quit
- The agent stays loaded, so the il2cpp bridge is only injected once.
- TypeScript is supported via esbuild, which strips types and outputs plain JS.
- The agent runs the code inside an Il2Cpp.perform() via eval, so can use the Il2Cpp API and frida-gum globals directly.
"""

package_name = 'com.pocketchamps.game'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_FILE = os.path.join(SCRIPT_DIR, "code.ts")
AGENT_FILE = os.path.join(SCRIPT_DIR, "_agent.js")
ESBUILD = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "node_modules", "esbuild", "bin", "esbuild"))

response_event = threading.Event()

def on_message(message: any, data: bytes | None) -> None:
    if message.get("type") == "send":
        payload = message.get("payload", {})
        event = payload.get("event")
        if event == "code_executed":
            print(f"[result] {payload.get('result')!r}")
            response_event.set()
        elif event == "code_execution_error":
            print(f"[error] {payload.get('error')}")
            response_event.set()
        else:
            print(f"[agent] {payload}")
    elif message.get("type") == "error":
        print(f"[script error] {message.get('description')}")
        print(message.get("stack", ""))
        response_event.set()
    else:
        print(f"Received message: {message}, data: {data}")


def on_destroyed():
    print("Script destroyed")


def on_log(level: str, text: str) -> None:
    print(f"Log: [{level}] {text}")


def transpile_ts(path: str) -> str | None:
    """Strip TypeScript types via esbuild, returning plain JS suitable for eval."""
    if not os.path.exists(ESBUILD):
        print(f"[!] esbuild not found at {ESBUILD}")
        return None
    result = subprocess.run(
        ["node", ESBUILD, path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("[!] TypeScript transpile failed:")
        print(result.stderr.strip())
        return None
    return result.stdout


def load_code(path: str) -> str | None:
    if not os.path.exists(path):
        print(f"[!] Code file not found: {path}")
        return None
    if path.lower().endswith((".ts", ".tsx", ".mts", ".cts")):
        return transpile_ts(path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_code(script, path: str) -> None:
    code = load_code(path)
    if code is None or not code.strip():
        print("[!] Nothing to run (file empty).")
        return
    print(f"[>] Sending {os.path.relpath(path, SCRIPT_DIR)} ({len(code)} chars)...")
    response_event.clear()
    script.post({'type': 'execute', 'code': code})
    # Wait for the agent to acknowledge so results print before the next prompt.
    if not response_event.wait(timeout=15):
        print("[!] No response within 15s (still running or agent stuck).")


def main() -> None:
    device = frida.get_usb_device()
    print(f"Connected to device: {device.name}")

    pid = None
    for app in device.enumerate_applications():
        if app.identifier == package_name:
            pid = app.pid
            break

    if pid is None:
        raise RuntimeError(f"Could not find running process for package: {package_name}")
    print(f"Found process {package_name} with PID: {pid}")

    session = device.attach(pid)
    print(f"Attached to process: {package_name}")

    if not os.path.exists(AGENT_FILE):
        raise FileNotFoundError("The _agent.js file was not found in the current directory, run `npm run build` first to generate it.")

    raw = open(AGENT_FILE, "r", encoding="utf-8").read()
    print(f"Loaded agent from _agent.js, length: {len(raw)} characters")

    script = session.create_script(raw)
    script.on('message', on_message)
    script.on('destroyed', on_destroyed)
    script.set_log_handler(on_log)
    script.load()

    if not os.path.exists(CODE_FILE):
        raise FileNotFoundError(f"Code file {CODE_FILE} not found. Create it.")

    print("\n=== Hot reload ready ===")
    print(f"Edit {os.path.relpath(CODE_FILE, SCRIPT_DIR)} then press ENTER to run it.")
    print("Commands: <ENTER>=run code.ts | r <path>=run file | q/exit=quit\n")

    while True:
        try:
            user_input = input("run> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

        if user_input.lower() in ("q", "exit", "quit"):
            break

        if not user_input:
            # Bare ENTER -> run the default code.js
            run_code(script, CODE_FILE)
            continue

        # Otherwise treat input as a target file: `r <path>` or just `<path>`.
        parts = user_input.split(None, 1)
        target = parts[1] if parts[0].lower() == "r" and len(parts) == 2 else user_input
        target = target if os.path.isabs(target) else os.path.join(SCRIPT_DIR, target)
        if os.path.exists(target):
            run_code(script, target)
        else:
            print(f"[!] Not a file: {target} (press ENTER alone to run code.ts)")

    session.detach()


if __name__ == "__main__":
    main()
