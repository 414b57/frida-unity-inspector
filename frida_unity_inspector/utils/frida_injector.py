from __future__ import annotations
from typing import Any, Awaitable, Callable, Optional, Union

import asyncio
import hashlib
import logging
import pathlib

import frida

from .adb_device import AdbDevice

logger = logging.getLogger(f"fui.utils.{__name__}")

MessageCallback = Callable[[dict, Optional[bytes]], Union[None, Awaitable[None]]]
LogCallback = Callable[[str, str], Union[None, Awaitable[None]]]


class FridaInjector:
    """
    Uploads/starts a frida-server on a device and injects an agent script into a
    target process, exposing an RPC interface and message/log callbacks.

    Two modes:
        - spawn:  spawn the package suspended, inject, then (optionally) resume.
        - attach: wait for the package's process to appear, then attach + inject.

    Usage:
        adb = AdbDevice("33021FDH30013K")
        injector = FridaInjector(
            adb,
            server_file="frida-server",
            agent_script="/path/to/_agent.js",
        )
        await injector.ensure_server()
        await injector.spawn_and_inject("com.example.app")
        result = await injector.call("someExport", 1, 2)
        ...
        injector.detach()

    :param adb: An Adb instance bound to the target device.
    :param server_file: Local path to the frida-server binary to upload.
    :param agent_script: Path to the agent .js to inject.
    :param spawn: Whether the default inject flow spawns (True) or attaches (False).
    :param resume_after_load: In spawn mode, resume the process after the agent loads.
    :param kill_on_stop: Kill the target process on detach().
    :param load_timeout: Seconds to wait for a process to appear when attaching.
    :param remote_name: On-device filename under /data/local/tmp. Defaults to the basename of `server_file`.
    """

    def __init__(
        self,
        adb: AdbDevice,
        server_file: str,
        agent_script: str,
        spawn: bool = False,
        resume_after_load: bool = True,
        kill_on_stop: bool = True,
        load_timeout: float = 30.0,
        remote_name: Optional[str] = None,
    ) -> None:
        if not server_file:
            raise ValueError("server_file must be a non-empty path")
        if not agent_script:
            raise ValueError("agent_script must be a non-empty path")
        if load_timeout <= 0:
            raise ValueError("load_timeout must be positive")

        self._adb = adb
        self._server_file = server_file
        self._agent_script = agent_script
        self._spawn = spawn
        self._resume_after_load = resume_after_load
        self._kill_on_stop = kill_on_stop
        self._load_timeout = load_timeout
        self._remote_name = remote_name or pathlib.Path(server_file).name

        # runtime
        self._loop: asyncio.AbstractEventLoop | None = None
        self._frida_device: frida.core.Device | None = None
        self._session: frida.core.Session | None = None
        self._script: frida.core.Script | None = None
        self._pid: int | None = None
        self._attached: bool = False

        self._on_message_callbacks: list[MessageCallback] = []
        self._on_log_callbacks: list[LogCallback] = []

    @property
    def _remote_server_path(self) -> str:
        """Absolute path the frida server binary lives at on-device."""
        return f"/data/local/tmp/{self._remote_name}"

    @property
    def attached(self) -> bool:
        return self._attached

    @property
    def pid(self) -> Optional[int]:
        return self._pid

    # Agent script
    def _get_agent_script(self) -> str:
        agent_script_path = pathlib.Path(self._agent_script).resolve()
        logger.debug("Loading agent script from: %s", agent_script_path)
        if not agent_script_path.exists():
            raise FileNotFoundError(f"Agent script not found at {agent_script_path}")
        with open(agent_script_path, "r") as f:
            return f.read()

    def _load_script(self, session: frida.core.Session) -> frida.core.Script:
        script = session.create_script(self._get_agent_script())
        script.on("message", self._on_frida_message)
        script.on("destroyed", self._on_frida_script_destroyed)
        script.set_log_handler(self._on_frida_log)
        script.load()
        logger.debug("Frida script loaded for session %s.", session)
        return script

    # Frida device
    async def _get_frida_device(self) -> Optional[frida.core.Device]:
        try:
            frida_device = frida.get_device(self._adb.serial)
            logger.debug("Frida device obtained for device %s.", self._adb.serial)
            return frida_device
        except Exception as e:
            logger.error("Failed to get frida device for device %s. Error: %s", self._adb.serial, e)
            return None

    def _find_specific_process(self, package_name: str, startswith_valid: bool = False) -> Optional[frida.core.Process]:
        try:
            apps = self._frida_device.enumerate_applications()
            for app in apps:
                if app.identifier == package_name or (startswith_valid and app.identifier.startswith(package_name)):
                    logger.spam("Found matching application: %s (PID: %s) for package '%s'", app.identifier, app.pid, package_name)
                    return app
            return None
        except Exception as e:
            logger.error("Error while enumerating processes: %s", e)
            return None

    async def _get_process_pid(self, package_name: str) -> Optional[int]:
        deadline = asyncio.get_event_loop().time() + self._load_timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                process = self._find_specific_process(package_name)
                if process is not None:
                    return process.pid
            except Exception as e:
                logger.error("Error while enumerating processes: %s", e)
            await asyncio.sleep(0.5)
        logger.error("Timeout reached while trying to find process '%s'.", package_name)
        return None

    # Ensure that frida server is uploaded and running
    async def _ensure_frida_server_uploaded(self) -> bool:
        try:
            # Check `/data/local/tmp` for the server. If not, push it.
            local_server_path = pathlib.Path(self._server_file)
            files = await self._adb.shell_ok("ls", "/data/local/tmp")
            if self._remote_name not in files.text.split():
                logger.info("Frida server not found on device %s. Uploading as '%s'...", self._adb.serial, self._remote_name)
                await self._adb.push(str(local_server_path), self._remote_server_path)
                logger.info("Frida server uploaded to device %s.", self._adb.serial)
                return True
            logger.spam("Frida server already present on device %s. Checking hash...", self._adb.serial)
            # Then check if hash matches. If not, delete from device and push it again.
            local_server_hash = hashlib.sha256(local_server_path.read_bytes()).hexdigest()
            remote_server_hash = await self._adb.shell_ok("sha256sum", self._remote_server_path)
            logger.spam("Local frida server hash: %s | Remote frida server hash: %s", local_server_hash, remote_server_hash.text.split()[0])
            if local_server_hash != remote_server_hash.text.split()[0]:
                logger.info("Frida server hash mismatch on device %s. Re-uploading...", self._adb.serial)
                await self._adb.shell_ok("rm", self._remote_server_path)
                await self._adb.push(str(local_server_path), self._remote_server_path)
                logger.info("Frida server re-uploaded to device %s.", self._adb.serial)
                return True
            logger.spam("Frida server hash matches on device %s.", self._adb.serial)

            # All good - frida server is present and matches hash.
            return True
        except Exception as e:
            logger.error("Failed to ensure frida server on device %s. Error: %s", self._adb.serial, e)
            return False

    async def _ensure_frida_server_permissions(self) -> bool:
        try:
            await self._adb.shell_ok("chmod", "755", self._remote_server_path)
            logger.spam("Frida server permissions set to 755 on device %s.", self._adb.serial)
            return True
        except Exception as e:
            logger.error("Failed to set frida server permissions on device %s. Error: %s", self._adb.serial, e)
            return False

    async def _ensure_frida_server_running(self) -> bool:
        try:
            # Check if frida server is running by checking for its process (by its on-device name).
            ps_output = await self._adb.shell("ps", "-a", "|", "grep", self._remote_name)
            if self._remote_name in ps_output.text:
                logger.spam("Frida server already running on device %s. (1)", self._adb.serial)
                return True
            ps_output = await self._adb.shell("ps", "-A", "|", "grep", self._remote_name)
            if self._remote_name in ps_output.text:
                logger.spam("Frida server already running on device %s. (2)", self._adb.serial)
                return True
            # Start the frida server in the background.
            await self._adb.shell_ok(f"su -c 'nohup {self._remote_server_path} >/dev/null 2>&1 &'")
            # Above ensures that frida server is started in the background and does not block the shell.
            logger.info("Frida server started on device %s.", self._adb.serial)
            return True
        except Exception as e:
            logger.error("Failed to start frida server on device %s. Error: %s", self._adb.serial, e)
            return False

    async def ensure_server(self) -> bool:
        """Upload (if needed), chmod, and start the frida server. Returns True on success."""
        return (
            await self._ensure_frida_server_uploaded()
            and await self._ensure_frida_server_permissions()
            and await self._ensure_frida_server_running()
        )

    # Inject
    async def spawn_and_inject(self, package_name: str) -> bool:
        """Spawn the package suspended, inject the agent, then optionally resume."""
        if self._frida_device is None:
            self._frida_device = await self._get_frida_device()
        if self._frida_device is None:
            logger.error("Frida device unavailable. Cannot spawn '%s'.", package_name)
            return False
        self._loop = asyncio.get_running_loop()

        self._pid = self._frida_device.spawn([package_name])
        logger.debug("Spawned process '%s' with PID %s.", package_name, self._pid)
        self._session = self._frida_device.attach(self._pid)
        logger.debug("Attached to spawned process '%s' with PID %s.", package_name, self._pid)
        self._script = self._load_script(self._session)
        if self._resume_after_load:
            self._frida_device.resume(self._pid)
            logger.debug("Resumed spawned process '%s' with PID %s.", package_name, self._pid)

        self._attached = True
        return True

    async def attach_and_inject(self, package_name: str) -> bool:
        """Wait for the package's process to appear, then attach and inject the agent."""
        if self._frida_device is None:
            self._frida_device = await self._get_frida_device()
        if self._frida_device is None:
            logger.error("Frida device unavailable. Cannot attach to '%s'.", package_name)
            return False
        self._loop = asyncio.get_running_loop()

        self._pid = await self._get_process_pid(package_name)
        if self._pid is None:
            logger.error("Failed to find process '%s' to attach.", package_name)
            return False
        self._session = self._frida_device.attach(self._pid)
        logger.debug("Attached to running process '%s' with PID %s.", package_name, self._pid)
        self._script = self._load_script(self._session)

        self._attached = True
        return True

    async def inject(self, package_name: str) -> bool:
        """Inject using the configured mode (spawn vs attach)."""
        if self._spawn:
            return await self.spawn_and_inject(package_name)
        return await self.attach_and_inject(package_name)

    def detach(self) -> None:
        """Unload the script, detach the session, and (if configured) kill the process."""
        try:
            if self._script is not None:
                self._script.unload()
                logger.trace("Frida script unloaded for session %s.", self._session)
            else:
                logger.warning("Frida script is None. Cannot unload script.")
        except Exception as e:
            logger.error("Failed to unload frida script. Error: %s", e)
        try:
            if self._session is not None:
                self._session.detach()
                logger.trace("Frida session detached for PID %s.", self._pid)
            else:
                logger.warning("Frida session is None. Cannot detach session.")
        except Exception as e:
            logger.error("Failed to detach frida session. Error: %s", e)

        if self._kill_on_stop:
            try:
                if self._pid is not None and self._frida_device is not None:
                    self._frida_device.kill(self._pid)
                    logger.trace("Frida process with PID %s killed.", self._pid)
                else:
                    logger.warning("Frida process PID or device is None. Cannot kill process.")
            except Exception as e:
                logger.error("Failed to kill frida process with PID %s. Error: %s", self._pid, e)

        self._frida_device = None
        self._session = None
        self._script = None
        self._pid = None
        self._attached = False

    async def wait_until_exit(self, package_name: str, poll_interval: float = 1.0) -> None:
        """Block until the target process disappears or the agent is destroyed."""
        while self._attached:
            try:
                process = self._find_specific_process(package_name)
                if process is None:
                    logger.info("Process '%s' has exited.", package_name)
                    break
            except Exception as e:
                logger.error("Error while checking process '%s': %s", package_name, e)
                break
            await asyncio.sleep(poll_interval)

    # Frida RPC
    async def call(self, method: str, *args: Any) -> Any:
        if self._script is None:
            logger.verbose("Frida script is not loaded. Cannot call method.")
            return None
        try:
            fn = getattr(self._script.exports_async, method, None)
            if fn is None:
                raise AttributeError(f"Method '{method}' not found in frida script exports.")
            result = await fn(*args)
            logger.spam("Called method '%s' on frida script with args %s. Result: %s", method, args, result)
            return result
        except Exception as e:
            logger.error("Failed to call method '%s' on frida script. Error: %s", method, e)
            return None

    async def post(self, message: dict, data: Optional[bytes] = None) -> None:
        if self._script is None:
            logger.verbose("Frida script is not loaded. Cannot post message.")
            return
        try:
            self._script.post(message, data)
            logger.spam("Posted message to frida script: %s | Data: %s", message, data)
        except Exception as e:
            logger.error("Failed to post message to frida script. Error: %s", e)

    # Frida thread callbacks
    def register_on_message_callback(self, callback: MessageCallback) -> None:
        if callback not in self._on_message_callbacks:
            self._on_message_callbacks.append(callback)
            logger.debug("Registered on_message callback: %s", callback)
        else:
            logger.warning("Callback %s is already registered.", callback)

    def unregister_on_message_callback(self, callback: MessageCallback) -> None:
        if callback in self._on_message_callbacks:
            self._on_message_callbacks.remove(callback)
            logger.debug("Unregistered on_message callback: %s", callback)
        else:
            logger.warning("Callback %s is not registered.", callback)

    def register_on_log_callback(self, callback: LogCallback) -> None:
        if callback not in self._on_log_callbacks:
            self._on_log_callbacks.append(callback)
            logger.debug("Registered on_log callback: %s", callback)
        else:
            logger.warning("Callback %s is already registered.", callback)

    def unregister_on_log_callback(self, callback: LogCallback) -> None:
        if callback in self._on_log_callbacks:
            self._on_log_callbacks.remove(callback)
            logger.debug("Unregistered on_log callback: %s", callback)
        else:
            logger.warning("Callback %s is not registered.", callback)

    def _on_frida_message(self, message: dict, data: Optional[bytes]) -> None:
        logger.god_save_you("Frida message received: %s | Data: %s", message, data)
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._handle_frida_message(message, data), self._loop)
        else:
            logger.error("Event loop is not set. Cannot handle frida message.")

    async def _handle_frida_message(self, message: dict, data: Optional[bytes]) -> None:
        logger.god_save_you("Calling %d callbacks for frida message.", len(self._on_message_callbacks))
        for callback in self._on_message_callbacks:
            try:
                self.logger.trace(f"Invoking callback {callback} for message")
                result = callback(message, data)
                if asyncio.iscoroutine(result):
                    await result
                self.logger.spam(f"Callback {callback} completed for message")
            except Exception as e:
                logger.error("Error in frida message callback: %s", e)

    def _on_frida_log(self, level: str, text: str) -> None:
        if not self._on_log_callbacks:
            # No consumers registered - fall back to our own logger.
            log_fn = {
                "info": logger.info,
                "warning": logger.warning,
                "error": logger.error,
            }.get(level, logger.info)
            log_fn("[agent] %s", text)
            return
        if self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._handle_frida_log(level, text), self._loop)
        else:
            logger.error("Event loop is not set. Cannot handle frida log.")

    async def _handle_frida_log(self, level: str, text: str) -> None:
        for callback in self._on_log_callbacks:
            try:
                result = callback(level, text)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error("Error in frida log callback: %s", e)

    def _on_frida_script_destroyed(self) -> None:
        logger.trace("Frida script destroyed.")
        self._attached = False