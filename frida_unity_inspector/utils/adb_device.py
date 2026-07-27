from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(f"fui.utils.{__name__}")


@dataclass
class AdbResult:
    """Result of an adb invocation."""
    returncode: int
    stdout: bytes
    stderr: bytes

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def text(self) -> str:
        return self.stdout.decode(errors="replace").strip()

    @property
    def error_text(self) -> str:
        return self.stderr.decode(errors="replace").strip()


class AdbError(RuntimeError):
    """Raised when an adb command fails and the caller asked for a checked call."""

    def __init__(self, args: tuple[str, ...], result: AdbResult) -> None:
        self.args_used = args
        self.result = result
        super().__init__(
            f"adb {' '.join(args)} failed (rc={result.returncode}): {result.error_text or result.text}"
        )


class AdbDevice:
    """
    Async ADB wrapper bound to a single device serial.

    Usage:
        adb = AdbDevice("33021FDH30013K")
        result = await adb.shell_ok("ls", "/sdcard")

    :param serial: The device serial (as shown by `adb devices`).
    :param adb_path: Path to the adb binary. Defaults to "adb" (on PATH).
    :param command_timeout: Default per-command timeout in seconds.
    """

    def __init__(
        self,
        serial: str,
        adb_path: str = "adb",
        command_timeout: float = 10.0,
    ) -> None:
        if not serial:
            raise ValueError("serial must be a non-empty device id")
        if not adb_path:
            raise ValueError("adb_path must be a non-empty string")
        if not command_timeout or command_timeout <= 0:
            raise ValueError("command_timeout must be a positive number")
        self._serial = serial
        self._adb_path = adb_path
        self._command_timeout = command_timeout

    @property
    def serial(self) -> str:
        return self._serial

    # Low-level execution
    async def run(self, *args: str, timeout: Optional[float] = None) -> AdbResult:
        """
        Run `adb -s <serial> <args...>` and return the full result.
        Never raises on non-zero exit; check `result.ok`.

        :raises FileNotFoundError: If the adb binary does not exist.
        :raises asyncio.TimeoutError: If the command exceeds the timeout.
        """
        full_args = ("-s", self._serial, *args)
        proc = await asyncio.create_subprocess_exec(
            self._adb_path, *full_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout or self._command_timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            logger.error("adb %s timed out after %.1fs", " ".join(args), timeout or self._command_timeout)
            raise
        result = AdbResult(returncode=proc.returncode, stdout=stdout, stderr=stderr)
        logger.spam("adb %s -> rc=%d", " ".join(args), result.returncode)
        return result

    async def run_ok(self, *args: str, timeout: Optional[float] = None) -> AdbResult:
        """Like run(), but raises AdbError on non-zero exit."""
        result = await self.run(*args, timeout=timeout)
        if not result.ok:
            raise AdbError(args, result)
        return result

    async def shell(self, *args: str, timeout: Optional[float] = None) -> AdbResult:
        """Run `adb shell <args...>`."""
        return await self.run("shell", *args, timeout=timeout)

    async def shell_ok(self, *args: str, timeout: Optional[float] = None) -> AdbResult:
        """Run `adb shell <args...>`, raising AdbError on failure."""
        return await self.run_ok("shell", *args, timeout=timeout)

    # Device readiness
    async def is_device_available(self) -> bool:
        """
        Check if the device is available (unlocked) via adb.

        Only checks whether the device is locked, not whether the screen is
        off: if the device is unlocked the screen is on, which is the only
        state we can use.
        """
        result = await self.shell("dumpsys", "window")
        # Need `mDreamingLockscreen=false` and `isKeyguardShowing=false`.
        if not result.ok or not result.text:
            return False
        dreaming_lock = re.search(r"mDreamingLockscreen=(true|false)", result.text)
        keyguard_showing = re.search(r"isKeyguardShowing=(true|false)", result.text)
        if not dreaming_lock or not keyguard_showing:
            logger.trace("Failed to parse dumpsys window output for device %s: dreaming_lock=%s, keyguard_showing=%s",self._serial, dreaming_lock, keyguard_showing,)
            return False
        dreaming_value = dreaming_lock.group(1) == "true"
        keyguard_value = keyguard_showing.group(1) == "true"
        logger.trace("Device %s availability check: dreaming_lock=%s, keyguard_showing=%s",self._serial, dreaming_value, keyguard_value,)
        return not dreaming_value and not keyguard_value

    # Input / Control
    async def tap(self, x: int, y: int) -> None:
        await self.shell_ok("input", "tap", str(int(x)), str(int(y)))

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        await self.shell_ok(
            "input", "swipe",
            str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(duration_ms)),
        )

    async def keyevent(self, keycode: int | str) -> None:
        await self.shell_ok("input", "keyevent", str(keycode))

    async def input_text(self, text: str) -> None:
        # `adb shell input text` treats space specially; %s is its escape for it.
        await self.shell_ok("input", "text", text.replace(" ", "%s"))

    # Screen
    async def screencap(self, timeout: Optional[float] = None) -> bytes:
        """Take a screenshot and return raw PNG bytes."""
        result = await self.run_ok("exec-out", "screencap", "-p", timeout=timeout or max(self._command_timeout, 15.0))
        return result.stdout

    async def wm_size(self) -> Optional[tuple[int, int]]:
        """Return the (width, height) of the screen, or None if it can't be parsed."""
        result = await self.shell("wm", "size")
        # "Physical size: 1080x2400" (possibly with an "Override size:" line)
        match = None
        for line in result.text.splitlines():
            match = re.search(r"(\d+)x(\d+)", line) or match
        if not match:
            return None
        return int(match.group(1)), int(match.group(2))

    # App / process management
    async def start_activity(self, package: str, activity: Optional[str] = None) -> AdbResult:
        """
        Launch an app. With an explicit activity uses `am start`; otherwise
        resolves the launcher intent via monkey (works without knowing the
        activity name).

        Uses the LAUNCHER category and MAIN action so the app is launched as if
        from the home screen (avoids anti-tamper detection of illegal launches).
        """
        if activity:
            component = f"{package}/{activity}"
            return await self.shell_ok("am", "start", "-c", "android.intent.category.LAUNCHER", "-a", "android.intent.action.MAIN", "-n", component)
        return await self.shell_ok(
            "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"
        )

    async def soft_stop(self, package: str) -> None:
        """
        Stop an app by sending it to the background and then killing it.
        A more "legit" way to stop an app than force-stop, which can be
        detected by anti-tamper measures.
        """
        await self.shell_ok("am", "broadcast", "-a", "android.intent.action.CLOSE_SYSTEM_DIALOGS")
        await self.shell_ok("input", "keyevent", "KEYCODE_HOME")
        await asyncio.sleep(0.5)
        await self.shell_ok("am", "kill", package)

    async def hard_stop(self, package: str) -> None:
        """Stop an app by force-stopping it (brute force; more detectable)."""
        await self.shell_ok("am", "force-stop", package)

    async def pidof(self, package: str) -> Optional[int]:
        """Return the PID of the package's main process, or None if not running."""
        result = await self.shell("pidof", package)
        if result.ok and result.text:
            try:
                return int(result.text.split()[0])
            except ValueError:
                return None
        return None

    async def is_running(self, package: str) -> bool:
        return await self.pidof(package) is not None

    async def current_focus(self) -> Optional[str]:
        """
        Return the package name of the currently focused app, or None.
        Parses `dumpsys window` mCurrentFocus / mFocusedApp.
        """
        result = await self.shell("dumpsys", "window", "displays")
        text = result.text
        if not result.ok or not text:
            # Older/newer android versions differ; fall back to full dumpsys window
            result = await self.shell("dumpsys", "window")
            text = result.text
            if not result.ok:
                return None
        for pattern in (r"mCurrentFocus=Window\{[^ ]+ [^ ]+ ([^/ }]+)", r"mFocusedApp=.*?\s([a-zA-Z0-9_.]+)/"):
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    async def is_foreground(self, package: str) -> bool:
        return (await self.current_focus()) == package

    async def getprop(self, prop: str) -> Optional[str]:
        result = await self.shell("getprop", prop)
        return result.text if result.ok else None

    # File management
    async def push(self, local_path: str, remote_path: str) -> None:
        await self.run_ok("push", local_path, remote_path)

    async def delete(self, remote_path: str) -> None:
        await self.shell_ok("rm", "-f", remote_path)