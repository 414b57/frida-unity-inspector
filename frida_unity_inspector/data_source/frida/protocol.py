"""AUTO-GENERATED from protocol_spec.py + models.py - do not edit by hand."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Awaitable, Callable, TypeAlias

from pydantic import TypeAdapter
from ..models import HierarchyNode, Property


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
    GET_HIERARCHY_STRUCTURE = "getHierarchyStructure"
    GET_COMPONENT_PROPERTIES = "getComponentProperties"
    SET_GAMEOBJECT_ACTIVE = "setGameObjectActive"
    SET_COMPONENT_ENABLED = "setComponentEnabled"
    SET_PROPERTY_VALUE = "setPropertyValue"


# Capabilities each capability depends on
CAPABILITY_REQUIRES: dict[Capabilities, tuple[Capabilities, ...]] = {
    Capabilities.GET_CURRENT_RENDER_PIPELINE: (),
    Capabilities.GET_SCENE_MANAGER: (),
    Capabilities.GET_CURRENT_SCENE: (Capabilities.GET_SCENE_MANAGER,),
    Capabilities.GET_HIERARCHY_STRUCTURE: (Capabilities.GET_CURRENT_SCENE,),
    Capabilities.GET_COMPONENT_PROPERTIES: (Capabilities.GET_HIERARCHY_STRUCTURE,),
    Capabilities.SET_GAMEOBJECT_ACTIVE: (),
    Capabilities.SET_COMPONENT_ENABLED: (),
    Capabilities.SET_PROPERTY_VALUE: (),
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
_GET_CURRENT_SCENE_RETURN: TypeAdapter[Any] = TypeAdapter(Any)
_GET_HIERARCHY_STRUCTURE_RETURN: TypeAdapter[Any] = TypeAdapter(list[HierarchyNode] | None)
_GET_COMPONENT_PROPERTIES_RETURN: TypeAdapter[Any] = TypeAdapter(dict[str, list[Property] | None])
_SET_GAMEOBJECT_ACTIVE_RETURN: TypeAdapter[Any] = TypeAdapter(bool)
_SET_COMPONENT_ENABLED_RETURN: TypeAdapter[Any] = TypeAdapter(bool)
_SET_PROPERTY_VALUE_RETURN: TypeAdapter[Any] = TypeAdapter(Property | None)


# TypeAdapters for serializing RPC arguments (frida json.dumps can't handle pydantic models)
_PING_ARG_UNIX_EPOCH_SECONDS: TypeAdapter[Any] = TypeAdapter(float)
_GET_COMPONENT_PROPERTIES_ARG_COMPONENT_IDS: TypeAdapter[Any] = TypeAdapter(list[str])
_SET_GAMEOBJECT_ACTIVE_ARG_GAMEOBJECT_HANDLE_PTR: TypeAdapter[Any] = TypeAdapter(str)
_SET_GAMEOBJECT_ACTIVE_ARG_ACTIVE: TypeAdapter[Any] = TypeAdapter(bool)
_SET_COMPONENT_ENABLED_ARG_COMPONENT_HANDLE_PTR: TypeAdapter[Any] = TypeAdapter(str)
_SET_COMPONENT_ENABLED_ARG_ACTIVE: TypeAdapter[Any] = TypeAdapter(bool)
_SET_PROPERTY_VALUE_ARG_COMPONENT_HANDLE_PTR: TypeAdapter[Any] = TypeAdapter(str)
_SET_PROPERTY_VALUE_ARG_PROPERTY: TypeAdapter[Any] = TypeAdapter(Property)


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
                Capabilities.GET_HIERARCHY_STRUCTURE: self.get_hierarchy_structure,
                Capabilities.GET_COMPONENT_PROPERTIES: self.get_component_properties,
                Capabilities.SET_GAMEOBJECT_ACTIVE: self.set_gameobject_active,
                Capabilities.SET_COMPONENT_ENABLED: self.set_component_enabled,
                Capabilities.SET_PROPERTY_VALUE: self.set_property_value,
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
        result = await self._call(Builtins.PING, _PING_ARG_UNIX_EPOCH_SECONDS.dump_python(unix_epoch_seconds, mode="json"))
        return _PING_RETURN.validate_python(result)

    async def get_current_render_pipeline(self) -> str | None:
        result = await self._call(Capabilities.GET_CURRENT_RENDER_PIPELINE)
        return _GET_CURRENT_RENDER_PIPELINE_RETURN.validate_python(result)

    async def get_scene_manager(self) -> Any:
        result = await self._call(Capabilities.GET_SCENE_MANAGER)
        return _GET_SCENE_MANAGER_RETURN.validate_python(result)

    async def get_current_scene(self) -> Any:
        result = await self._call(Capabilities.GET_CURRENT_SCENE)
        return _GET_CURRENT_SCENE_RETURN.validate_python(result)

    async def get_hierarchy_structure(self) -> list[HierarchyNode] | None:
        result = await self._call(Capabilities.GET_HIERARCHY_STRUCTURE)
        return _GET_HIERARCHY_STRUCTURE_RETURN.validate_python(result)

    async def get_component_properties(self, component_ids: list[str]) -> dict[str, list[Property] | None]:
        result = await self._call(Capabilities.GET_COMPONENT_PROPERTIES, _GET_COMPONENT_PROPERTIES_ARG_COMPONENT_IDS.dump_python(component_ids, mode="json"))
        return _GET_COMPONENT_PROPERTIES_RETURN.validate_python(result)

    async def set_gameobject_active(self, gameobject_handle_ptr: str, active: bool) -> bool:
        result = await self._call(Capabilities.SET_GAMEOBJECT_ACTIVE, _SET_GAMEOBJECT_ACTIVE_ARG_GAMEOBJECT_HANDLE_PTR.dump_python(gameobject_handle_ptr, mode="json"), _SET_GAMEOBJECT_ACTIVE_ARG_ACTIVE.dump_python(active, mode="json"))
        return _SET_GAMEOBJECT_ACTIVE_RETURN.validate_python(result)

    async def set_component_enabled(self, component_handle_ptr: str, active: bool) -> bool:
        result = await self._call(Capabilities.SET_COMPONENT_ENABLED, _SET_COMPONENT_ENABLED_ARG_COMPONENT_HANDLE_PTR.dump_python(component_handle_ptr, mode="json"), _SET_COMPONENT_ENABLED_ARG_ACTIVE.dump_python(active, mode="json"))
        return _SET_COMPONENT_ENABLED_RETURN.validate_python(result)

    async def set_property_value(self, component_handle_ptr: str, property: Property) -> Property | None:
        result = await self._call(Capabilities.SET_PROPERTY_VALUE, _SET_PROPERTY_VALUE_ARG_COMPONENT_HANDLE_PTR.dump_python(component_handle_ptr, mode="json"), _SET_PROPERTY_VALUE_ARG_PROPERTY.dump_python(property, mode="json"))
        return _SET_PROPERTY_VALUE_RETURN.validate_python(result)
