from __future__ import annotations

from typing import Any

from ..models import GameContext, SceneDeclaration, Status, Scene, Property

from ..base_data import BaseDataSource
from .agent_session import AgentSession
from .device_resolver import resolve_frida_device
from .protocol import Capabilities, Builtins
from frida_unity_inspector.utils import AdbDevice, FridaInjector

import asyncio
import frida
import pathlib

CWD = pathlib.Path(__file__).resolve().parent
AGENT_FILE_PATH = CWD / "agent" / "_agent.js"
SERVER_FILE = "frida-server-17.8.2-android-arm64"
SERVER_FILE_PATH = CWD / SERVER_FILE

class FridaDataSource(BaseDataSource):
    """
    TODO
    """
    def __init__(self, device: str, package: str, spawn: bool, kill_on_stop: bool) -> None:
        super().__init__()
        # args
        self.device = device
        self.package = package
        self.spawn = spawn
        self.kill_on_stop = kill_on_stop

        # runtime - internal state
        self.frida_device: frida.core.Device | None = None
        self.adb_device: AdbDevice | None = None
        self.frida_injector: FridaInjector | None = None
        self.session: AgentSession | None = None
        self._run_loop_task: asyncio.Task | None = None
        self._running = False

        # runtime - external state (From agent/unity)

    # -- lifecycle --
    async def start(self) -> None:
        """Resolve the device, inject the agent, and start the run loop."""
        self.logger.info("Starting FridaDataSource...")
        self._running = True

        self.frida_device = await resolve_frida_device(self.device)
        is_local = self.device == "local"

        self.adb_device = None if is_local else AdbDevice(self.frida_device.id)
        self.frida_injector = FridaInjector(
            adb=self.adb_device,
            frida_device=self.frida_device,
            local=is_local,
            server_file=str(SERVER_FILE_PATH),
            agent_script=str(AGENT_FILE_PATH),
            spawn=self.spawn,
            resume_after_load=True,
            kill_on_stop=self.kill_on_stop
        )
        self.session = AgentSession(self.frida_injector)
        self.logger.trace(f"Frida injector initialized for device {self.frida_device.id} and package {self.package} (spawn={self.spawn})")

        if not is_local:
            await self.frida_injector.ensure_server()
            self.logger.trace(f"Frida server ensured on device {self.frida_device.id}")
        success = await self.frida_injector.inject(self.package)
        if not success:
            raise RuntimeError(f"Failed to inject Frida agent into package {self.package} on device {self.frida_device.id}")
        self.logger.trace(f"Frida agent injected/spawned into package {self.package} on device {self.frida_device.id}")

        self._run_loop_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Cancel the run loop and tear down the session/injector."""
        self.logger.info("Stopping FridaDataSource...")
        self._running = False
        if self._run_loop_task is not None:
            self._run_loop_task.cancel()
            self._run_loop_task = None
        if self.session is not None:
            self.session.close()
            self.session = None
        if self.frida_injector is not None:
            self.frida_injector.detach()
            self.logger.info("Frida injector stopped.")
            self.frida_injector = None

    async def status(self) -> Status:
        """TODO"""

    # Run
    async def _run(self) -> None:
        """TODO"""
        self.logger.info("FridaDataSource run loop started. Waiting for agent to become ready...")
        await self.session.ready.wait()
        self.logger.info("FridaDataSource agent is ready. Starting main loop...")

        while self._running:
            await asyncio.sleep(1)
            VERSION: str | None = await self.session.call_capability(Builtins.VERSION)
            self.logger.debug(f"Agent version: {VERSION}")
            UNITY_VERSION: str | None = await self.session.call_capability(Builtins.UNITY_VERSION)
            self.logger.debug(f"Unity version: {UNITY_VERSION}")
            PING: str | None = await self.session.call_capability(Builtins.PING, msg="test")
            self.logger.debug(f"Ping response: {PING}")
            render_pipeline: str | None = await self.session.call_capability(Capabilities.GET_CURRENT_RENDER_PIPELINE)
            self.logger.debug(f"getCurrentRenderPipeline response: {render_pipeline}")
            capabilities: dict[str, bool] = await self.session.call_capability(Builtins.CAPABILITIES)
            self.logger.debug(f"Agent capabilities: {capabilities}")
            # if self.session.has_capability(Capabilities.GET_CURRENT_RENDER_PIPELINE):
            #     # None here means the built-in render pipeline.
            #     render_pipeline: str | None = await self.session.rpc.get_current_render_pipeline()
            #     self.logger.debug(f"getCurrentRenderPipeline response: {render_pipeline}")

    # -- reading data --
    async def get_game_context(self) -> GameContext:
        """TODO"""

    async def get_scenes(self) -> list[SceneDeclaration]:
        """TODO"""

    async def get_current_scene(self) -> Scene:
        """TODO"""

    # -- writing data --
    async def set_active(self, object_id: str, active: bool) -> None:
        """TODO"""

    async def set_component_enabled(self, object_id: str, component_id: str, enabled: bool) -> None:
        """TODO"""

    async def set_property(self, object_id: str, component_id: str, label: str, value: Any) -> Property:
        """TODO"""
