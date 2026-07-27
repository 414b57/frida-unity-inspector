from __future__ import annotations

from typing import Any

from ..models import LogType, IconName, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, Property
from ..models import Vector2, Vector3, Color, Vector2Property, Vector3Property, FloatProperty, BoolProperty, StringProperty, EnumProperty, ColorProperty

from ..base_data import BaseDataSource, LogCallback

class FridaDataSource(BaseDataSource):
    """
    TODO


    """
    def __init__(self) -> None:
        super().__init__()

    # -- lifecycle --
    def start(self) -> None:
        """TODO"""

    def stop(self) -> None:
        """TODO"""

    def status(self) -> Status:
        """TODO"""

    # -- reading data --
    def get_game_context(self) -> GameContext:
        """TODO"""

    def get_scenes(self) -> list[SceneDeclaration]:
        """TODO"""

    def get_current_scene(self) -> Scene:
        """TODO"""

    # -- writing data --
    def set_active(self, object_id: str, active: bool) -> None:
        """TODO"""

    def set_component_enabled(self, object_id: str, component_id: str, enabled: bool) -> None:
        """TODO"""

    def set_property(self, object_id: str, component_id: str, label: str, value: Any) -> Property:
        """TODO"""
