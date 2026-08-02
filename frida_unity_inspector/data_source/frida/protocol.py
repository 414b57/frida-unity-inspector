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


class Capabilities(StrEnum):
    GET_CURRENT_RENDER_PIPELINE = "getCurrentRenderPipeline"


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
_GET_CURRENT_RENDER_PIPELINE_RETURN: TypeAdapter[Any] = TypeAdapter(str | None)


RpcCall: TypeAlias = Callable[..., Awaitable[Any]]


class AgentRpc:
    """Typed wrappers around the agent's RPC exports.

    Each method corresponds to an RPC call, and returns the validated result via pydantic. Raises ValidationError if the result is invalid.
    """

    def __init__(self, call: RpcCall) -> None:
        self._call = call

    async def capabilities(self) -> dict[str, bool]:
        result = await self._call(Builtins.CAPABILITIES)
        return _CAPABILITIES_RETURN.validate_python(result)

    async def version(self) -> str:
        result = await self._call(Builtins.VERSION)
        return _VERSION_RETURN.validate_python(result)

    async def get_current_render_pipeline(self) -> str | None:
        result = await self._call(Capabilities.GET_CURRENT_RENDER_PIPELINE)
        return _GET_CURRENT_RENDER_PIPELINE_RETURN.validate_python(result)
