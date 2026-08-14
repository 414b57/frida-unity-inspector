from __future__ import annotations

from typing import Any

from pydantic import TypeAdapter

from ..models import GameContext, SceneDeclaration, Status, Scene, Property, HierarchyNode

from ..base_data import BaseDataSource, StatusUpdate, StructureUpdate, PropertiesUpdate
from .agent_session import AgentSession
from .device_resolver import resolve_frida_device
from .protocol import Capabilities, Builtins
from frida_unity_inspector.utils import AdbDevice, FridaInjector

import logging
import time
import asyncio
import frida
import pathlib

CWD = pathlib.Path(__file__).resolve().parent
AGENT_FILE_PATH = CWD / "agent" / "_agent.js"
SERVER_FILE = "frida-server-17.8.2-android-arm64"
SERVER_FILE_PATH = CWD / SERVER_FILE

# Delay between ticks of the run loop. Each tick polls for a light hierarchy structure, then polls for a chunk of property values.
TICK_INTERVAL_SECONDS = 0.25
# Whether should account for time spent in tick when sleeping between ticks. If True, then the sleep time is reduced by the time spent in tick, so that the total time between ticks is approximately TICK_INTERVAL_SECONDS. If False, then the sleep time is always TICK_INTERVAL_SECONDS, so that the total time between ticks is TICK_INTERVAL_SECONDS + time spent in tick.
ACCOUNT_FOR_TICK_TIME = True
# How many properties to poll per tick. Polling too many properties at once can hitch the game thread, so we do it in chunks.
PROPS_PER_TICK = 3

_STRUCTURE_ADAPTER: TypeAdapter[list[Scene]] = TypeAdapter(list[Scene])
_PROPS_ADAPTER: TypeAdapter[list[Property]] = TypeAdapter(list[Property])

class FridaDataSource(BaseDataSource):
    """
    TODO
    """
    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(f"fui.data_source.frida")

    def __init__(self, device: str, package: str, spawn: bool, kill_on_stop: bool, unity_version: str | None = None) -> None:
        super().__init__()
        # args
        self.device = device
        self.package = package
        self.spawn = spawn
        self.kill_on_stop = kill_on_stop
        self.unity_version = unity_version

        # runtime - internal state
        self.frida_device: frida.core.Device | None = None
        self.adb_device: AdbDevice | None = None
        self.frida_injector: FridaInjector | None = None
        self.session: AgentSession | None = None
        self._run_loop_task: asyncio.Task | None = None
        self._running = False
        self._last_tick_time: float | None = None

        # runtime - external state (From agent/unity)
        self.current_status: Status | None = None
        self.game_context: GameContext | None = None
        self.scenes: list[SceneDeclaration] | None = None

        self._structure: list[Scene] | None = None # Cache of loaded scenes (light hierarchy), for change detection and property merging
        self._structure_dump: bytes | None = None  # last serialized structure, if match no changes has occured
        self._component_props: dict[str, list[Property]] = {} # per-component cached property values, keyed by component id
        self._component_prop_dumps: dict[str, bytes] = {}  # per-component serialized props, if match no changes has occured
        self._prop_cycle: list[str] = []  # all component ids in tree order
        self._prop_cursor = 0  # position within the in-scope components
        self._polled_this_cycle = 0  # components polled since last full sweep
        self._poll_percent = 0.0  # percent of in-scope components polled since last full sweep

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

        self.frida_injector._script.post({"type": "set_unity_version", "unity_version": self.unity_version})
        if self.unity_version is not None:
            self.logger.trace(f"Unity version set to {self.unity_version} in agent")

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
        return self.current_status

    # Run
    async def _run(self) -> None:
        """TODO"""
        self.logger.info("FridaDataSource run loop started. Waiting for agent to become ready...")
        await self.session.ready.wait()
        self.logger.info("FridaDataSource agent is ready. Starting main loop...")

        try:
            self.game_context = GameContext(
                version=await self.session.call_capability(Builtins.VERSION),
                unity_version=await self.session.call_capability(Builtins.UNITY_VERSION),
                render_pipeline=await self.session.call_capability(Capabilities.GET_CURRENT_RENDER_PIPELINE)
            )
        except Exception as e:
            self.logger.error(f"Failed to fetch game context: {e}", exc_info=e)

        while self._running:
            try:
                await self._tick()
            except Exception as e:
                self.logger.error(f"Error in FridaDataSource run loop: {e}\n", exc_info=e)
            finally:
                sleep_time = TICK_INTERVAL_SECONDS
                if ACCOUNT_FOR_TICK_TIME and self._last_tick_time is not None:
                    sleep_time = max(0.0, TICK_INTERVAL_SECONDS - self._last_tick_time)
                await asyncio.sleep(sleep_time)

    async def _tick(self) -> None:
        """One poll cycle: refresh the light structure, then one chunk of property values."""
        start = time.time()
        python_to_ts_delay, ts_time = await self.session.call_capability(Builtins.PING, unix_epoch_seconds=start)
        stop = time.time()
        round_trip_time = stop - start

        await self._poll_structure() # Qucik poll of the light hierarchy structure, if changed re-key the property and notify subscribers
        structure_poll_time = time.time()
        await self._poll_property_chunk() # Then do heavy reflection work on the game thread to fetch property values for the next chunk of in-scope components and notify subscribers of changes

        finish = time.time()
        self.current_status = Status(
            running=self._running,
            message=f"FridaDataSource running - {self._poll_percent:.0f}% polled - tick took {finish - start:.6f}s (structure: {structure_poll_time - start:.6f}s, properties: {finish - structure_poll_time:.6f}s)"
        )
        self.logger.trace(f"Ping round-trip time: {round_trip_time:.6f}s, python-to-ts delay: {python_to_ts_delay:.6f}s, ts-to-python delay: {stop-ts_time:.6f}s")
        self.logger.debug(f"Total time: {finish-start:.6f}s, structure poll: {structure_poll_time-start:.6f}s, property poll: {finish-structure_poll_time:.6f}s")
        self._emit_update(StatusUpdate(status=self.current_status))
        self._last_tick_time = time.time()-start

    async def _poll_structure(self) -> None:
        """Refresh the light hierarchy tree; on change, re-key the property and notify subscribers."""
        if not self.session.has_capability(Capabilities.GET_HIERARCHY_STRUCTURE): # If cant get hierarchy structure, then no point in polling for it
            return
        scenes: list[Scene] | None = await self.session.call_capability(Capabilities.GET_HIERARCHY_STRUCTURE)
        if scenes is None:
            return

        dump = _STRUCTURE_ADAPTER.dump_json(scenes)
        if dump == self._structure_dump: # If nothing has changed, then no need to re-key the property or notify subscribers
            return

        self._structure = scenes
        self._structure_dump = dump

        # Re-key the property to the components that exist now, across every loaded scene.
        live_ids: list[str] = []
        def collect(nodes: list[HierarchyNode]) -> None:
            for node in nodes:
                for component in node.data.components:
                    live_ids.append(component.id)
                collect(node.children)
        for scene in scenes:
            collect(scene.roots)
        self._prop_cycle = live_ids
        live_set = set(live_ids)

        for dead_id in [cid for cid in self._component_props if cid not in live_set]: # Remove any cached properties for components that no longer exist in the hierarchy
            self._component_props.pop(dead_id, None)
            self._component_prop_dumps.pop(dead_id, None)

        self._emit_update(StructureUpdate(scenes=scenes))

    async def _poll_property_chunk(self) -> None:
        """Fetch properties of in-scope components in chunks, to avoid hitching the game thread. Notify subscribers of any changes."""
        if not self.session.has_capability(Capabilities.GET_COMPONENT_PROPERTIES): # If cant get component properties, then no point in polling for them
            return
        scope = self._property_scope
        targets = [cid for cid in self._prop_cycle if scope is None or cid in scope] # Only poll for properties of components that are in scope (if any). If no scope is set, then poll for all components.
        if not targets: # If no components are in scope, then no need to poll for properties
            return

        if self._prop_cursor >= len(targets):
            self._prop_cursor = 0
        chunk = [targets[(self._prop_cursor + i) % len(targets)] for i in range(min(PROPS_PER_TICK, len(targets)))]
        self._prop_cursor = (self._prop_cursor + len(chunk)) % len(targets)
        self._poll_percent = 100.0 * self._prop_cursor / len(targets) if targets else 0.0

        result: dict[str, list[Property] | None] = await self.session.call_capability(Capabilities.GET_COMPONENT_PROPERTIES, component_ids=chunk)

        self._polled_this_cycle += len(chunk)
        if self._polled_this_cycle >= len(targets):
            self._poll_percent = 100.0
            self._polled_this_cycle = 0  # reset for next sweep
        else:
            self._poll_percent = 100.0 * self._polled_this_cycle / len(targets)

        changed: dict[str, list[Property]] = {}
        for component_id, props in result.items():
            if props is None:
                # Stale id - the component vanished between the structure walk and now.
                self._component_props.pop(component_id, None)
                self._component_prop_dumps.pop(component_id, None)
                continue
            dump = _PROPS_ADAPTER.dump_json(props)
            if dump == self._component_prop_dumps.get(component_id): # If nothing has changed, then no need to notify subscribers
                continue
            self._component_props[component_id] = props
            self._component_prop_dumps[component_id] = dump
            changed[component_id] = props

        if changed:
            self._emit_update(PropertiesUpdate(components=changed))

    # -- reading data --
    async def get_game_context(self) -> GameContext:
        """TODO"""
        return self.game_context

    async def get_scenes(self) -> list[SceneDeclaration]:
        """TODO"""
        return self.scenes

    async def get_loaded_scenes(self) -> list[Scene]:
        """Every loaded scene: light structure with all property values cached so far merged in. Used during initial load of web app."""
        if self._structure is None:
            return []

        def fill(node: HierarchyNode) -> None:
            for component in node.data.components:
                component.properties = list(self._component_props.get(component.id, []))
            for child in node.children:
                fill(child)

        scenes = [scene.model_copy(deep=True) for scene in self._structure]
        for scene in scenes:
            for root in scene.roots:
                fill(root)
        return scenes

    # -- writing data --
    async def set_active(self, object_id: str, active: bool) -> None:
        """TODO"""
        self.logger.debug(f"Setting active state of object {object_id} to {active}")
        result = await self.session.call_capability(Capabilities.SET_GAMEOBJECT_ACTIVE, object_id, active)
        if not result:
            self.logger.error(f"Failed to set active state of object {object_id} to {active}")
            return result
        self.logger.debug(f"Successfully set active state of object {object_id} to {active}")

    async def set_component_enabled(self, object_id: str, component_id: str, enabled: bool) -> None:
        """TODO"""
        self.logger.debug(f"Setting enabled state of component {component_id} on object {object_id} to {enabled}")
        result = await self.session.call_capability(Capabilities.SET_COMPONENT_ENABLED, component_id, enabled)
        if not result:
            self.logger.error(f"Failed to set enabled state of component {component_id} on object {object_id} to {enabled}")
            return
        self.logger.debug(f"Successfully set enabled state of component {component_id} on object {object_id} to {enabled}")

    async def set_property(self, object_id: str, component_id: str, property: Property) -> Property:
        """TODO"""
        self.logger.debug(f"Setting property {property.label} of component {component_id} on object {object_id} to {property.value}")
        result = await self.session.call_capability(Capabilities.SET_PROPERTY_VALUE, component_id, property)
        if result is None:
            self.logger.error(f"Failed to set property {property.label} of component {component_id} on object {object_id} to {property.value}")
            return result
        self.logger.debug(f"Successfully set property {property.label} of component {component_id} on object {object_id} to {property.value} (result: {result.value})")
        return result
