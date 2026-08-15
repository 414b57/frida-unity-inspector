from __future__ import annotations

import os
import shlex
import subprocess
import threading
from datetime import datetime
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
LOG_FILE = os.path.join(SCRIPT_DIR, "input_code_runner.log")

response_event = threading.Event()

# All output is mirrored to LOG_FILE, flushed on every line. Large dumps (e.g.
# dump_scene) overflow the terminal scrollback and scroll off screen, so the log
# file is the durable copy you can open/tail while a run is in progress.
# on_message / on_log fire on Frida's own thread, so a lock keeps lines intact.
_log_fh = open(LOG_FILE, "w", encoding="utf-8", buffering=1)
_log_lock = threading.Lock()


def emit(text: str = "") -> None:
    """Print to the console and append to LOG_FILE in realtime (both flushed)."""
    print(text, flush=True)
    with _log_lock:
        _log_fh.write(f"[{datetime.now():%H:%M:%S.%f}] {text}\n")
        _log_fh.flush()

def on_message(message: any, data: bytes | None) -> None:
    if message.get("type") == "send":
        payload = message.get("payload", {})
        event = payload.get("event")
        if event == "code_executed":
            emit(f"[result] {payload.get('result')!r}")
            response_event.set()
        elif event == "code_execution_error":
            emit(f"[error] {payload.get('error')}")
            response_event.set()
        else:
            emit(f"[agent] {payload}")
    elif message.get("type") == "error":
        emit(f"[script error] {message.get('description')}")
        emit(message.get("stack", ""))
        response_event.set()
    else:
        emit(f"Received message: {message}, data: {data}")


def on_destroyed():
    emit("Script destroyed")


def on_log(level: str, text: str) -> None:
    emit(f"Log: [{level}] {text}")


def transpile_ts(path: str) -> str | None:
    """Strip TypeScript types via esbuild, returning plain JS suitable for eval."""
    if not os.path.exists(ESBUILD):
        emit(f"[!] esbuild not found at {ESBUILD}")
        return None
    result = subprocess.run(
        ["node", ESBUILD, path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        emit("[!] TypeScript transpile failed:")
        emit(result.stderr.strip())
        return None
    return result.stdout


def load_code(path: str) -> str | None:
    if not os.path.exists(path):
        emit(f"[!] Code file not found: {path}")
        return None
    if path.lower().endswith((".ts", ".tsx", ".mts", ".cts")):
        return transpile_ts(path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_code(script, path: str, args: list[str] | None = None) -> None:
    args = args or []
    code = load_code(path)
    if code is None or not code.strip():
        emit("[!] Nothing to run (file empty).")
        return
    suffix = f" args={args}" if args else ""
    emit(f"[>] Sending {os.path.relpath(path, SCRIPT_DIR)} ({len(code)} chars){suffix}...")
    response_event.clear()
    script.post({'type': 'execute', 'code': code, 'args': args})
    # Wait for the agent to acknowledge so results print before the next prompt.
    if not response_event.wait(timeout=15):
        emit("[!] No response within 15s (still running or agent stuck).")


def main() -> None:
    emit(f"[log] Mirroring all output to {LOG_FILE}")

    device = frida.get_usb_device()
    emit(f"Connected to device: {device.name}")

    pid = None
    for app in device.enumerate_applications():
        if app.identifier == package_name:
            pid = app.pid
            break

    if pid is None:
        raise RuntimeError(f"Could not find running process for package: {package_name}")
    emit(f"Found process {package_name} with PID: {pid}")

    session = device.attach(pid)
    emit(f"Attached to process: {package_name}")

    if not os.path.exists(AGENT_FILE):
        raise FileNotFoundError("The _agent.js file was not found in the current directory, run `npm run build` first to generate it.")

    raw = open(AGENT_FILE, "r", encoding="utf-8").read()
    emit(f"Loaded agent from _agent.js, length: {len(raw)} characters")

    script = session.create_script(raw)
    script.on('message', on_message)
    script.on('destroyed', on_destroyed)
    script.set_log_handler(on_log)
    script.load()

    if not os.path.exists(CODE_FILE):
        raise FileNotFoundError(f"Code file {CODE_FILE} not found. Create it.")

    emit("\n=== Hot reload ready ===")
    emit(f"Edit {os.path.relpath(CODE_FILE, SCRIPT_DIR)} then press ENTER to run it.")
    emit("Commands: <ENTER>=run code.ts | r <path> [args...]=run file | q/exit=quit")
    emit(f"Full output (incl. large dumps) is tailing into {os.path.basename(LOG_FILE)}")
    emit("Examples: r stubs/dump_scene.ts 0 | r stubs/dump_object.ts Player\n")

    LAST_CODE_RUN = None

    while True:
        try:
            user_input = input("run> ").strip()
        except (KeyboardInterrupt, EOFError):
            emit("\nExiting...")
            break

        if user_input.lower() in ("q", "exit", "quit"):
            break

        if not user_input:
            # Bare ENTER -> run the default code.js
            run_code(script, CODE_FILE)
            continue

        # if it is `r <path> [args...]`, parse the path and args and call it
        # if it is `<path> [args...]`, parse the path and args and call it
        # if it is JUST `r`, then run the last code run (if any)
        tokens = shlex.split(user_input, posix=False)
        if tokens and tokens[0].lower() == "r":
            tokens = tokens[1:]
            if not tokens:
                if LAST_CODE_RUN:
                    run_code(script, *LAST_CODE_RUN)
                else:
                    emit("[!] No previous code run to repeat.")
                continue

        target, args = tokens[0], [t.strip('"') for t in tokens[1:]]
        target = target if os.path.isabs(target) else os.path.join(SCRIPT_DIR, target)
        if os.path.exists(target):
            run_code(script, target, args)
            LAST_CODE_RUN = [target, args]
        else:
            emit(f"[!] Not a file: {target} (press ENTER alone to run code.ts)")


    session.detach()


if __name__ == "__main__":
    try:
        main()
    finally:
        with _log_lock:
            _log_fh.flush()
            _log_fh.close()
