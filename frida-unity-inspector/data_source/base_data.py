from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Callable

from .models import LogType, IconName, PropertyKind, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, Property

LogCallback = Callable[[LogEntry], None]

class BaseDataSource(ABC):
    """Abstract base class for data sources."""

    def __init__(self) -> None:
        self._log_history: list[LogEntry] = []
        self._log_subscribers: list[LogCallback] = []

    # -- lifecycle --
    @abstractmethod
    def start(self) -> None:
        """Connect / attach. Safe to call once before serving requests."""

    @abstractmethod
    def stop(self) -> None:
        """Detach and release resources."""

    @abstractmethod
    def status(self) -> Status:
        """Current attach/connection status."""

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger(f"fui.base_data")

    def get_logger(self, subname: str | None = None) -> logging.Logger:
        return logging.getLogger(f"fui.base_data.{subname}" if subname else "fui.base_data")

    # -- reading data --
    @abstractmethod
    def get_game_context(self) -> GameContext:
        """Get static metadata about the inspected Unity game."""

    @abstractmethod
    def get_scenes(self) -> list[SceneDeclaration]:
        """Get the list of scenes known to the game."""

    @abstractmethod
    def get_current_scene(self) -> Scene:
        """Get the currently loaded scene and its hierarchy."""

    # TODO - Extra methods? I.e. search. etc

    # -- writing data --
    @abstractmethod
    def set_active(self, object_id: str, active: bool) -> None:
        """Toggle a GameObject's active state."""

    # TODO - Set property method

    # -- log streaming --
    def get_log_history(self) -> list[LogEntry]:
        """Get the history of log entries."""
        return self._log_history

    def _get_log_subscribers(self) -> list[LogCallback]:
        """Get the list of log subscribers."""
        return self._log_subscribers

    def subscribe(self, callback: LogCallback) -> None:
        """Register ``callback`` for future log entries."""
        if callback in self._log_subscribers:
            self.logger.warning("Attempted to subscribe a callback that was already subscribed.")
        else:
            self._log_subscribers.append(callback)

    def unsubscribe(self, callback: LogCallback) -> None:
        """Unregister ``callback`` from future log entries."""
        if callback not in self._log_subscribers:
            self.logger.warning("Attempted to unsubscribe a callback that was not subscribed.")
        else:
            self._log_subscribers.remove(callback)

    def emit(self, event: LogEntry) -> None:
        """Emit a log entry to all subscribers."""
        self._log_history.append(event)
        for callback in self._log_subscribers:
            try:
                callback(event)
            except Exception as e:
                self.logger.exception("Error in log subscriber callback: %s", e)