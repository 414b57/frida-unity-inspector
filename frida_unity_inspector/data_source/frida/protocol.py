"""AUTO-GENERATED from protocol.json - do not edit by hand."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Awaitable, Callable, TypeAlias

from pydantic import TypeAdapter


class MessageTypes(StrEnum):
    EVENT = "event"


class Events(StrEnum):
    AGENT_LOADED = "agent_loaded"
    AGENT_READY = "agent_ready"


class Builtins(StrEnum):
    CAPABILITIES = "capabilities"
    VERSION = "version"
    UNITY_VERSION = "unityVersion"
    PING = "ping"


class Capabilities(StrEnum):
    GET_CURRENT_RENDER_PIPELINE = "getCurrentRenderPipeline"
    GET_SCENE_MANAGER = "getSceneManager"
    GET_CURRENT_SCENE = "getCurrentScene"


# Capabilities each capability depends on
CAPABILITY_REQUIRES: dict[Capabilities, tuple[Capabilities, ...]] = {
    Capabilities.GET_CURRENT_RENDER_PIPELINE: (),
    Capabilities.GET_SCENE_MANAGER: (),
    Capabilities.GET_CURRENT_SCENE: (Capabilities.GET_SCENE_MANAGER,),
}


# Event payloads, and their TypeAdapters for validation
AgentLoadedData: TypeAlias = None
AgentReadyData: TypeAlias = dict[str, bool]

EVENT_DATA_ADAPTERS: dict[Events, TypeAdapter[Any]] = {
    Events.AGENT_LOADED: TypeAdapter(AgentLoadedData),
    Events.AGENT_READY: TypeAdapter(AgentReadyData),
}


# TypeAdapters for validating RPC return values
_CAPABILITIES_RETURN: TypeAdapter[Any] = TypeAdapter(dict[str, bool])
_VERSION_RETURN: TypeAdapter[Any] = TypeAdapter(str)
_UNITY_VERSION_RETURN: TypeAdapter[Any] = TypeAdapter(str)
_PING_RETURN: TypeAdapter[Any] = TypeAdapter(tuple[float, float])
_GET_CURRENT_RENDER_PIPELINE_RETURN: TypeAdapter[Any] = TypeAdapter(str | None)
_GET_SCENE_MANAGER_RETURN: TypeAdapter[Any] = TypeAdapter(Any)
_GET_CURRENT_SCENE_RETURN: TypeAdapter[Any] = TypeAdapter(Any | None)


RpcCall: TypeAlias = Callable[..., Awaitable[Any]]


class AgentRpc:
    """Typed wrappers around the agent's RPC exports.

    Each method corresponds to an RPC call, and returns the validated result via pydantic. Raises ValidationError if the result is invalid.
    """

    def __init__(self, call: RpcCall) -> None:
            self._call = call
            self._dispatch: dict[StrEnum, RpcCall] = {
                Builtins.CAPABILITIES: self.capabilities,
                Builtins.VERSION: self.version,
                Builtins.UNITY_VERSION: self.unity_version,
                Builtins.PING: self.ping,
                Capabilities.GET_CURRENT_RENDER_PIPELINE: self.get_current_render_pipeline,
                Capabilities.GET_SCENE_MANAGER: self.get_scene_manager,
                Capabilities.GET_CURRENT_SCENE: self.get_current_scene,
            }

    def dispatch(self, key: StrEnum, *args, **kwargs) -> Awaitable[Any]:
        """Dispatches an RPC call based on the key, and returns the validated result."""
        if key not in self._dispatch:
            raise ValueError(f"Unknown RPC key: {key}")
        return self._dispatch[key](*args, **kwargs)

    async def capabilities(self) -> dict[str, bool]:
        result = await self._call(Builtins.CAPABILITIES)
        return _CAPABILITIES_RETURN.validate_python(result)

    async def version(self) -> str:
        result = await self._call(Builtins.VERSION)
        return _VERSION_RETURN.validate_python(result)

    async def unity_version(self) -> str:
        result = await self._call(Builtins.UNITY_VERSION)
        return _UNITY_VERSION_RETURN.validate_python(result)

    async def ping(self, unix_epoch_seconds: float) -> tuple[float, float]:
        result = await self._call(Builtins.PING, unix_epoch_seconds)
        return _PING_RETURN.validate_python(result)

    async def get_current_render_pipeline(self) -> str | None:
        result = await self._call(Capabilities.GET_CURRENT_RENDER_PIPELINE)
        return _GET_CURRENT_RENDER_PIPELINE_RETURN.validate_python(result)

    async def get_scene_manager(self) -> Any:
        result = await self._call(Capabilities.GET_SCENE_MANAGER)
        return _GET_SCENE_MANAGER_RETURN.validate_python(result)

    async def get_current_scene(self) -> Any | None:
        result = await self._call(Capabilities.GET_CURRENT_SCENE)
        return _GET_CURRENT_SCENE_RETURN.validate_python(result)
