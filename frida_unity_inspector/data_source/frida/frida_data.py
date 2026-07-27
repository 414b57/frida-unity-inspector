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
    async def start(self) -> None:
        """TODO"""

    async def stop(self) -> None:
        """TODO"""

    async def status(self) -> Status:
        """TODO"""

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
