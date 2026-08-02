from __future__ import annotations

from typing import Any

from ..models import LogType, IconName, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, Property
from ..models import Vector2, Vector3, Color, Vector2Property, Vector3Property, FloatProperty, BoolProperty, StringProperty, EnumProperty, ColorProperty

from ..base_data import BaseDataSource, LogCallback
from frida_unity_inspector.utils import DiscoveredDevice, device_discovery, AdbDevice, FridaInjector

import asyncio
import frida
import os
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

        # runtime - handlers
        self.adb_device: AdbDevice | None = None
        self.frida_device: frida.Device | None = None
        self.frida_injector: FridaInjector | None = None

        # runtime - state
        self._running = False
        self._agent_loaded = False
        self._agent_ready = False
        self._detected_capabilities: dict[str, Any] = {}

    # -- lifecycle --
    async def start(self) -> None:
        """
        TODO
        """
        self.logger.info("Starting FridaDataSource...")
        self._running = True
        if self.device == "local":
            self.logger.info("Using local device")
            self.frida_device = frida.get_local_device()
        elif self.device == "adb":
            self.logger.info("Using ADB device discovery")
            devices = await device_discovery.discover_devices()
            if not devices:
                raise RuntimeError("No devices found via ADB. Please ensure ADB is installed and the device is connected.")
            if len(devices) == 1:
                self.frida_device = frida.get_device(devices[0].device_id)
                self.logger.info(f"Selected 1st due to only 1 device found: {self.frida_device} (ADB state: {devices[0].adb_state})")
            else:
                while True:
                    self.logger.info(f"Multiple devices found. Please specify a device. Available devices: ")
                    for i, d in enumerate(devices):
                        self.logger.info(f"{i + 1}. {d.device_id} (ADB state: {d.adb_state})")
                    choice = input(f">> ")  # TODO - Look into better way than getting input here. But works for now.
                    try:
                        choice_index = int(choice) - 1
                        if 0 <= choice_index < len(devices):
                            self.frida_device = frida.get_device(devices[choice_index].device_id)
                            self.logger.info(f"Using device: {self.frida_device} (ADB state: {devices[choice_index].adb_state})")
                            break
                        else:
                            self.logger.warning(f"Invalid selection. Please choose a number between 1 and {len(devices)}.")
                    except ValueError:
                        self.logger.warning("Invalid input. Please enter a number.")
        else:
            self.logger.info(f"Using device: {self.device}")
            self.frida_device = frida.get_device(self.device)

        if self.frida_device is None:
            raise RuntimeError(f"Failed to get Frida device for {self.device}") # Shouldn't happen, but just in case

        is_local = self.device == "local"

        self.adb_device = None if is_local else AdbDevice(self.frida_device.id)
        self.frida_injector = FridaInjector(
            adb=self.adb_device,
            frida_device=self.frida_device,
            local=is_local,
            server_file=str(SERVER_FILE_PATH),
            # agent_script="agent/_agent.js",
            agent_script=str(AGENT_FILE_PATH),
            spawn=self.spawn,
            resume_after_load=True,
            kill_on_stop=self.kill_on_stop
        )
        self.logger.trace(f"Frida injector initialized for device {self.frida_device.id} and package {self.package} (spawn={self.spawn})")

        self.frida_injector.register_on_message_callback(self.on_message)

        if not is_local:
            await self.frida_injector.ensure_server()
            self.logger.trace(f"Frida server ensured on device {self.frida_device.id}")
        await self.frida_injector.inject(self.package)
        self.logger.trace(f"Frida agent injected/spawned into package {self.package} on device {self.frida_device.id}")

        # Start the run loop
        asyncio.create_task(self._run())

    async def stop(self) -> None:
        """TODO"""
        self.logger.info("Stopping FridaDataSource...")
        self._running = False
        if self.frida_injector:
            self.frida_injector.detach()
            self.logger.info("Frida injector stopped.")
        self.frida_injector = None

    async def status(self) -> Status:
        """TODO"""

    # Run
    async def _run(self) -> None:
        """TODO"""
        self.logger.info("FridaDataSource run loop started.")
        while self._running:
            await asyncio.sleep(1)
            if not self._agent_ready:
                continue  # Wait until the agent is ready before processing messages

            if self._detected_capabilities.get("getCurrentRenderPipeline", False):
                response = await self.frida_injector.call("getCurrentRenderPipeline")
                self.logger.debug(f"getCurrentRenderPipeline response: {response}")

    # Message Handling
    def on_message(self, message: dict[str, Any], data: bytes | None) -> None:
        """Handle messages from the Frida agent."""
        self.logger.trace(f"Received message from Frida agent: {message}, data length: {len(data) if data else 0}")
        # TODO - Handle messages and update internal state as needed
        msg_type = message.get("type", None)
        if msg_type is None:
            self.logger.warning("Received message without 'type' field from Frida agent.")
            self.logger.debug(f"Message: {message} ||| Data: {data}")
            return
        elif msg_type == "send":
            self._handle_message_sent(message, data)
        else:
            self.logger.warning(f"Received message with unrecognized type '{msg_type}' from Frida agent.")
            self.logger.debug(f"Message: {message} ||| Data: {data}")

    def _handle_message_sent(self, message: dict[str, Any], data: bytes | None) -> None:
        """Handle 'send' messages from the Frida agent."""
        payload = message.get("payload", None)
        if payload is None:
            self.logger.warning("Received 'send' message without 'payload' field from Frida agent.")
            self.logger.debug(f"Message: {message} ||| Data: {data}")
            return
        message_type = payload.get("type", None)
        if message_type is None:
            self.logger.warning("Received 'send' message without 'type' field from Frida agent.")
            self.logger.debug(f"Message: {message} ||| Data: {data}")
            return
        if message_type == "event":
            event = payload.get("event", None)
            event_data = payload.get("data", None)
            if event is None:
                self.logger.warning("Received 'send' message of type 'event' without 'event' field from Frida agent.")
                self.logger.debug(f"Message: {message} ||| Data: {data}")
                return
            self._handle_event(event, event_data, data)
        else:
            self.logger.warning(f"Received 'send' message with unrecognized type '{message_type}' from Frida agent.")
            self.logger.debug(f"Message: {message} ||| Data: {data}")

    def _handle_event(self, event: str, event_data: Any, data: bytes | None) -> None:
        """Handle events sent from the Frida agent."""
        self.logger.trace(f"Handling event '{event}' with data: {event_data}")
        events = {
            "agent_loaded": self._handle_agent_loaded,
            "agent_ready": self._handle_agent_ready,
        }
        if event in events:
            events[event](event, event_data, data)
        else:
            self._handle_unknown_event(event, event_data, data)

    # Event Handlers
    def _handle_unknown_event(self, event: str, event_data: Any, data: bytes | None) -> None:
        """Handle unknown events sent from the Frida agent."""
        self.logger.warning(f"Received unknown event '{event}' from Frida agent.")
        self.logger.debug(f"Event data: {event_data} ||| Data: {data}")

    def _handle_agent_loaded(self, event: str, event_data: Any, data: bytes | None) -> None:
        """Handle the event when the Frida agent has been loaded."""
        self._agent_loaded = True
        self.logger.info("Frida agent loaded successfully.")

    def _handle_agent_ready(self, event: str, event_data: Any, data: bytes | None) -> None:
        """Handle the event when the Frida agent is ready to receive commands."""
        self._agent_ready = True
        self.logger.info(f"Frida agent is ready. Detected capabilities: {event_data}")
        self._detected_capabilities = event_data if isinstance(event_data, dict) else {}

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
