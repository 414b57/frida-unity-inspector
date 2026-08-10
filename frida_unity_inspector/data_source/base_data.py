from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Annotated, Any, Callable, Literal, Union

from pydantic import BaseModel, Field

from .models import LogType, IconName, PropertyKind, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, BaseProperty, Property

LogCallback = Callable[[LogEntry], None]

# Data being pushed by a data source to its subscribers (web apps) when game state changes.
class StatusUpdate(BaseModel):
    """The data source's connection/attach status has changed."""
    type: Literal["status"] = "status"
    status: Status


class StructureUpdate(BaseModel):
    """The (light) hierarchy changed - carries the full new tree, property values omitted."""
    type: Literal["structure"] = "structure"
    scene: Scene

class PropertiesUpdate(BaseModel):
    """Fresh property values for some components, keyed by component id."""
    type: Literal["properties"] = "properties"
    components: dict[str, list[Property]] = Field(default_factory=dict)

DataUpdate = Annotated[
    Union[
        StatusUpdate,
        StructureUpdate,
        PropertiesUpdate,
    ],
    Field(discriminator="type")
]

UpdateCallback = Callable[[DataUpdate], None]

class BaseDataSource(ABC):
    """Abstract base class for data sources."""

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(f"fui.base_data")

    def __init__(self) -> None:
        self._log_history: list[LogEntry] = []
        self._log_subscribers: list[LogCallback] = []
        self._update_subscribers: list[UpdateCallback] = []
        # Which components property values should be polled for. None = all of them | a set of component ids = only those
        # Currently `simple_list` web app wants to update everything. But if implement a unity editor style UI, only update properties for the currently selected obj.
        self._property_scope: set[str] | None = None

    # -- lifecycle --
    @abstractmethod
    async def start(self) -> None:
        """Connect / attach. Safe to call once before serving requests."""

    @abstractmethod
    async def stop(self) -> None:
        """Detach and release resources."""

    @abstractmethod
    async def status(self) -> Status:
        """Current attach/connection status."""

    # -- reading data --
    @abstractmethod
    async def get_game_context(self) -> GameContext:
        """Get static metadata about the inspected Unity game."""

    @abstractmethod
    async def get_scenes(self) -> list[SceneDeclaration]:
        """Get the list of scenes known to the game."""

    @abstractmethod
    async def get_current_scene(self) -> Scene:
        """Get the currently loaded scene and its hierarchy."""

    # TODO - Extra methods? I.e. search. etc

    # -- writing data --
    @abstractmethod
    async def set_active(self, object_id: str, active: bool) -> None:
        """Toggle a GameObject's active state."""

    @abstractmethod
    async def set_component_enabled(self, object_id: str, component_id: str, enabled: bool) -> None:
        """Toggle a component's enabled state."""

    @abstractmethod
    async def set_property(self, object_id: str, component_id: str, property: Property) -> Property:
        """Set a component property's value and return the updated property."""

    # -- update streaming --
    def set_property_scope(self, component_ids: set[str] | None) -> None:
        """Limit property polling to `component_ids`. None = poll all components."""
        self._property_scope = set(component_ids) if component_ids is not None else None

    def subscribe_updates(self, callback: UpdateCallback) -> Callable[[], None]:
        """Register ``callback`` for future data updates (structure/property changes)."""
        if callback in self._update_subscribers:
            self.logger.warning("Attempted to subscribe an update callback that was already subscribed.")
        else:
            self._update_subscribers.append(callback)

        return lambda: self.unsubscribe_updates(callback)

    def unsubscribe_updates(self, callback: UpdateCallback) -> None:
        """Unregister ``callback`` from future data updates."""
        if callback not in self._update_subscribers:
            self.logger.warning("Attempted to unsubscribe an update callback that was not subscribed.")
        else:
            self._update_subscribers.remove(callback)

    def _emit_update(self, update: DataUpdate) -> None:
        """Emit a data update to all subscribers."""
        for callback in self._update_subscribers:
            try:
                callback(update)
            except Exception as e:
                self.logger.exception("Error in update subscriber callback: %s", e)

    # -- log streaming --
    def get_log_history(self) -> list[LogEntry]:
        """Get the history of log entries."""
        return self._log_history

    def _get_log_subscribers(self) -> list[LogCallback]:
        """Get the list of log subscribers."""
        return self._log_subscribers

    def subscribe(self, callback: LogCallback) -> Callable[[], None]:
        """Register ``callback`` for future log entries."""
        if callback in self._log_subscribers:
            self.logger.warning("Attempted to subscribe a callback that was already subscribed.")
        else:
            self._log_subscribers.append(callback)

        return lambda: self.unsubscribe(callback)

    def unsubscribe(self, callback: LogCallback) -> None:
        """Unregister ``callback`` from future log entries."""
        if callback not in self._log_subscribers:
            self.logger.warning("Attempted to unsubscribe a callback that was not subscribed.")
        else:
            self._log_subscribers.remove(callback)

    async def emit(self, event: LogEntry) -> None:
        """Emit a log entry to all subscribers."""
        self._log_history.append(event)
        for callback in self._log_subscribers:
            try:
                callback(event)
            except Exception as e:
                self.logger.exception("Error in log subscriber callback: %s", e)