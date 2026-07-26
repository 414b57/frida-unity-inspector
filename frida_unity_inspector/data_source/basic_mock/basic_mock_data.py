from __future__ import annotations

import datetime

from typing import Any

from pydantic import TypeAdapter

from ..models import LogType, IconName, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, Property
from ..models import Vector2, Vector3, Color, Vector2Property, Vector3Property, FloatProperty, BoolProperty, StringProperty, EnumProperty, ColorProperty

_PROPERTY_ADAPTER: TypeAdapter[Property] = TypeAdapter(Property)

from ..base_data import BaseDataSource, LogCallback

class BasicMockDataSource(BaseDataSource):
    """Basic Mock implementation of BaseData for testing and development."""
    def __init__(self) -> None:
        super().__init__()

        self._scenes: list[Scene] = [
            Scene(
                name="SampleScene",
                roots=[
                    HierarchyNode(
                        id="1",
                        name="Main Camera",
                        icon="camera",

                        data = GameObjectData(
                            active=True,
                            is_static=False,
                            tag="MainCamera",
                            layer=0,

                            components=[
                                Component(
                                    id="1-1",
                                    name="Transform",
                                    type="Transform",
                                    icon="move",
                                    enabled=None, # Transform cannot be toggled
                                    expanded=True,
                                    properties=[
                                        Vector3Property(label="Position", value=Vector3(x=0, y=1, z=-10)),
                                        Vector3Property(label="Rotation", value=Vector3(x=0, y=0, z=0)),
                                        Vector3Property(label="Scale", value=Vector3(x=1, y=1, z=1)),
                                    ]
                                ),
                                Component(
                                    id="1-2",
                                    name="Camera",
                                    type="Camera",
                                    icon="camera",
                                    enabled=True,
                                    expanded=True,
                                    properties=[
                                        FloatProperty(label="Field of View", value=60.0),
                                        Vector2Property(label="Clipping Planes", value=Vector2(x=0.3, y=1000)),
                                    ]
                                ),
                                Component(
                                    id="1-3",
                                    name="Audio Listener",
                                    type="Audio Listener",
                                    icon="headphones",
                                    enabled=True,
                                    expanded=True,
                                    properties=[]
                                ),
                                Component(
                                    id="1-4",
                                    name="Universal Additional Camera Data",
                                    type="MonoBehaviour",
                                    icon="script",
                                    enabled=True,
                                    expanded=True,
                                    properties=[]
                                )
                            ]
                        ),

                        children=[]
                    ),
                    HierarchyNode(
                        id="2",
                        name="Directional Light",
                        icon="light",
                        data = GameObjectData(
                            active=True,
                            is_static=False,
                            tag="Untagged",
                            layer=0,
                            components=[
                                Component(
                                    id="2-1",
                                    name="Transform",
                                    type="Transform",
                                    icon="move",
                                    enabled=None, # Transform cannot be toggled
                                    expanded=True,
                                    properties=[
                                        Vector3Property(label="Position", value=Vector3(x=0, y=3, z=0)),
                                        Vector3Property(label="Rotation", value=Vector3(x=50, y=-30, z=0)),
                                        Vector3Property(label="Scale", value=Vector3(x=1, y=1, z=1)),
                                    ]
                                ),
                                Component(
                                    id="2-2",
                                    name="Light",
                                    type="Light",
                                    icon="light",
                                    enabled=True,
                                    expanded=True,
                                    properties=[
                                        EnumProperty(label="Type", options=["Spot", "Directional", "Point", "Area"], value="Directional"),
                                        ColorProperty(label="Color", value=Color(r=1.0, g=1.0, b=1.0, a=1.0)),
                                        FloatProperty(label="Intensity", value=1.0),
                                    ]
                                ),
                                Component(
                                    id="2-3",
                                    name="Universal Additional Light Data",
                                    type="MonoBehaviour",
                                    icon="script",
                                    enabled=True,
                                    expanded=True,
                                    properties=[]
                                )
                            ]
                        ),
                        children=[]
                    ),
                    HierarchyNode(
                        id="3",
                        name="Content",
                        icon="cube",
                        data = GameObjectData(
                            active=True,
                            is_static=False,
                            tag="Untagged",
                            layer=0,
                            components=[
                                Component(
                                    id="3-1",
                                    name="Transform",
                                    type="Transform",
                                    icon="move",
                                    enabled=None, # Transform cannot be toggled
                                    expanded=True,
                                    properties=[
                                        Vector3Property(label="Position", value=Vector3(x=0, y=0, z=0)),
                                        Vector3Property(label="Rotation", value=Vector3(x=0, y=0, z=0)),
                                        Vector3Property(label="Scale", value=Vector3(x=1, y=1, z=1)),
                                    ]
                                )
                            ]
                        ),

                        children=[
                            HierarchyNode(
                                id="4",
                                name="Cube",
                                icon="cube",
                                data = GameObjectData(
                                    active=True,
                                    is_static=False,
                                    tag="Untagged",
                                    layer=0,
                                    components=[
                                        Component(
                                            id="4-1",
                                            name="Transform",
                                            type="Transform",
                                            icon="move",
                                            enabled=None, # Transform cannot be toggled
                                            expanded=True,
                                            properties=[
                                                Vector3Property(label="Position", value=Vector3(x=0, y=0.5, z=0)),
                                                Vector3Property(label="Rotation", value=Vector3(x=0, y=0, z=0)),
                                                Vector3Property(label="Scale", value=Vector3(x=1, y=1, z=1)),
                                            ]
                                        ),
                                        Component(
                                            id="4-2",
                                            name="Mesh Renderer",
                                            type="Mesh Renderer",
                                            icon="cube",
                                            enabled=True,
                                            expanded=True,
                                            properties=[
                                                StringProperty(label="Material", value="Default-Material"),
                                            ]
                                        ),
                                        Component(
                                            id="4-3",
                                            name="Box Collider",
                                            type="Box Collider",
                                            icon="cube",
                                            enabled=True,
                                            expanded=True,
                                            properties=[
                                                BoolProperty(label="Is Trigger", value=False),
                                            ]
                                        ),
                                        Component(
                                            id="4-4",
                                            name="Cube Script",
                                            type="MonoBehaviour",
                                            icon="script",
                                            enabled=True,
                                            expanded=True,
                                            properties=[
                                                FloatProperty(label="Move Speed", value=5.0),
                                                FloatProperty(label="Jump Height", value=2.0),
                                            ]
                                        )
                                    ]
                                )
                            )
                        ]
                    )
                ]
            )
        ]

        self._game_context: GameContext = GameContext(
            # name="Mock Game",
            version="1.0.0",
            unity_version="6000.0f1",

            # tags=[
            #     "Respawn",
            #     "Finish",
            #     "EditorOnly",
            #     "MainCamera",
            #     "Player",
            #     "GameController"
            # ],
            #
            # sorting_layers=["Default"],
            # layers={
            #     0: "Default",
            #     1: "TransparentFX",
            #     2: "Ignore Raycast",
            #     4: "Water",
            #     5: "UI"
            #     # Layer 3, and 6-31 are user-defined and not included in this mock data
            # },
            # rendering_layers=[
            #     "Default",
            #     "Light Layer 1",
            #     "Light Layer 2",
            #     "Light Layer 3",
            #     "Light Layer 4",
            #     "Light Layer 5",
            #     "Light Layer 6",
            #     "Light Layer 7",
            # ],

            # scenes=[
            #     SceneDeclaration(name="SampleScene")
            # ]
            # scenes=[SceneDeclaration(name=scene.name) for scene in self._scenes]
        )

        self._log_history = [
            LogEntry(
                id=1,
                kind="log",
                message="Example Log Message",
                source="Example Log Source",
                timestamp=datetime.datetime.now().timestamp(),
            ),
            LogEntry(
                id=1,
                kind="log",
                message="Example Log Message With no source",
                timestamp=datetime.datetime.now().timestamp() + 1,
            ),
            LogEntry(
                id=3,
                kind="warning",
                message="Example Warning Message",
                source="Example Warning Source",
                timestamp=datetime.datetime.now().timestamp() + 2,
            ),
            LogEntry(
                id=4,
                kind="error",
                message="Example Error Message",
                source="Example Error Source",
                timestamp=datetime.datetime.now().timestamp() + 3,
            ),
            LogEntry(
                id=5,
                kind="error",
                message="NullReferenceException: Object reference not set to an instance of an object",
                source="PlayerMovement.cs:61",
                stack_trace=(
                    "NullReferenceException: Object reference not set to an instance of an object\n"
                    "PlayerMovement.get_GroundCheck () (at Assets/Scripts/PlayerMovement.cs:61)\n"
                    "PlayerMovement.Update () (at Assets/Scripts/PlayerMovement.cs:98)"
                ),
                timestamp=datetime.datetime.now().timestamp()+4,
            )
        ]

        self.logger.info("MockData initialized.")

    # -- lifecycle --
    def start(self) -> None:
        """Simulate starting the data source."""
        self.logger.info("MockData started.")

    def stop(self) -> None:
        """Simulate stopping the data source."""
        self.logger.info("MockData stopped.")

    def status(self) -> Status:
        """Return a mock status."""
        return Status(
            running=True,
            message="Mock data source is running."
        )

    # -- reading data --
    def get_game_context(self) -> GameContext:
        """Return mock game context data."""
        return self._game_context

    def get_scenes(self) -> list[SceneDeclaration]:
        """Return a list of mock scene declarations."""
        return self._game_context.scenes

    def get_current_scene(self) -> Scene:
        """Return a mock current scene with hierarchy."""
        return self._scenes[0]

    # -- writing data --
    def _find_node(self, object_id: str) -> HierarchyNode:
        def walk(nodes: list[HierarchyNode]) -> HierarchyNode | None:
            for node in nodes:
                if node.id == object_id:
                    return node
                found = walk(node.children)
                if found is not None:
                    return found
            return None

        for scene in self._scenes:
            found = walk(scene.roots)
            if found is not None:
                return found
        raise KeyError(f"No GameObject with id '{object_id}'.")

    def _find_component(self, object_id: str, component_id: str) -> Component:
        node = self._find_node(object_id)
        for component in node.data.components:
            if component.id == component_id:
                return component
        raise KeyError(f"GameObject '{object_id}' has no component with id '{component_id}'.")

    def set_active(self, object_id: str, active: bool) -> None:
        """Toggle a GameObject's active state."""
        node = self._find_node(object_id)
        node.data.active = active
        self.logger.info(f"Set active state of {object_id} ({node.name}) to {active}.")

    def set_component_enabled(self, object_id: str, component_id: str, enabled: bool) -> None:
        """Toggle a component's enabled state."""
        component = self._find_component(object_id, component_id)
        if component.enabled is None:
            raise ValueError(f"Component '{component.name}' has no enable checkbox.")
        component.enabled = enabled
        self.logger.info(f"Set enabled state of {object_id}/{component_id} ({component.name}) to {enabled}.")

    def set_property(self, object_id: str, component_id: str, label: str, value: Any) -> Property:
        """Set a component property's value."""
        component = self._find_component(object_id, component_id)
        for index, prop in enumerate(component.properties):
            if prop.label != label:
                continue
            if prop.read_only:
                raise ValueError(f"Property '{label}' is read-only.")
            if isinstance(prop, EnumProperty) and value not in prop.options:
                raise ValueError(f"'{value}' is not one of {prop.options}.")

            data = prop.model_dump()
            data["value"] = value
            new_prop = _PROPERTY_ADAPTER.validate_python(data)
            component.properties[index] = new_prop
            self.logger.info(f"Set property '{label}' of {object_id}/{component_id} ({component.name}) to {value!r}.")
            return new_prop
        raise KeyError(f"Component '{component_id}' has no property labeled '{label}'.")
