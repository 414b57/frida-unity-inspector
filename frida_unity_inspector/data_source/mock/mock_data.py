from __future__ import annotations

import datetime

from ..models import LogType, IconName, PropertyKind, GameContext, SceneDeclaration, LogEntry, Status, Scene, HierarchyNode, GameObjectData, Component, Property

from ..base_data import BaseDataSource, LogCallback

class MockDataSource(BaseDataSource):
    """Mock implementation of BaseData for testing and development."""
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
                                        Property(label="Position", kind=PropertyKind.VECTOR3, value="(0, 1, -10)"),
                                        Property(label="Rotation", kind=PropertyKind.VECTOR3, value="(0, 0, 0)"),
                                        Property(label="Scale", kind=PropertyKind.VECTOR3, value="(1, 1, 1)"),
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
                                        Property(label="Field of View", kind=PropertyKind.FLOAT, value=60.0),
                                        Property(label="Clipping Planes", kind=PropertyKind.VECTOR2, value="(0.3, 1000)"),
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
                                        Property(label="Position", kind=PropertyKind.VECTOR3, value="(0, 3, 0)"),
                                        Property(label="Rotation", kind=PropertyKind.VECTOR3, value="(50, -30, 0)"),
                                        Property(label="Scale", kind=PropertyKind.VECTOR3, value="(1, 1, 1)"),
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
                                        Property(label="Type", kind=PropertyKind.STRING, value="Directional"),
                                        Property(label="Color", kind=PropertyKind.COLOR, value="#FFFFFF"),
                                        Property(label="Intensity", kind=PropertyKind.FLOAT, value=1.0),
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
                                        Property(label="Position", kind=PropertyKind.VECTOR3, value="(0, 0, 0)"),
                                        Property(label="Rotation", kind=PropertyKind.VECTOR3, value="(0, 0, 0)"),
                                        Property(label="Scale", kind=PropertyKind.VECTOR3, value="(1, 1, 1)"),
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
                                                Property(label="Position", kind=PropertyKind.VECTOR3, value="(0, 0.5, 0)"),
                                                Property(label="Rotation", kind=PropertyKind.VECTOR3, value="(0, 0, 0)"),
                                                Property(label="Scale", kind=PropertyKind.VECTOR3, value="(1, 1, 1)"),
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
                                                Property(label="Material", kind=PropertyKind.STRING, value="Default-Material"),
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
                                                Property(label="Is Trigger", kind=PropertyKind.BOOL, value=False),
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
                                                Property(label="Move Speed", kind=PropertyKind.FLOAT, value=5.0),
                                                Property(label="Jump Height", kind=PropertyKind.FLOAT, value=2.0),
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
            name="Mock Game",
            version="1.0.0",
            unity_version="6000.0f1",

            tags=[
                "Respawn",
                "Finish",
                "EditorOnly",
                "MainCamera",
                "Player",
                "GameController"
            ],

            sorting_layers=["Default"],
            layers={
                0: "Default",
                1: "TransparentFX",
                2: "Ignore Raycast",
                4: "Water",
                5: "UI"
                # Layer 3, and 6-31 are user-defined and not included in this mock data
            },
            rendering_layers=[
                "Default",
                "Light Layer 1",
                "Light Layer 2",
                "Light Layer 3",
                "Light Layer 4",
                "Light Layer 5",
                "Light Layer 6",
                "Light Layer 7",
            ],

            # scenes=[
            #     SceneDeclaration(name="SampleScene")
            # ]
            scenes=[SceneDeclaration(name=scene.name) for scene in self._scenes]
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
    def set_active(self, object_id: str, active: bool) -> None:
        """Simulate toggling a GameObject's active state."""
        self.logger.info(f"Set active state of {object_id} to {active}.")
