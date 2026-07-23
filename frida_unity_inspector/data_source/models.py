from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# -- ??? -- (Used for info, like what icons exist. TODO - actual name)
LogType = Literal[
    "log",
    "warning",
    "error",
]

IconName = Literal[
    "cube", # Everything defaults to this if no icon is specified.
    "camera",
    "light",
    "canvas",
    "script",
    "gear",
    "move",
    "rotate",
    "scale",
    "rect",
    "headphones",

    "unknown", # Question mark / `?`
    "error", "warning", "check", "cross",
]

class PropertyKind(str, Enum):
    """How the UI should render a single inspector field."""

    FLOAT = "float"
    INT = "int"
    STRING = "string"
    BOOL = "bool"
    ENUM = "enum"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"
    VECTOR4 = "vector4"
    SLIDER = "slider"
    COLOR = "color"
    OBJECT = "object"  # a reference to another asset / GameObject

# -- Static --
class GameContext(BaseModel):
    """Static metadata about the inspected Unity game.

    These values are expected to remain constant for the duration of an
    inspection session and are not affected by normal gameplay or runtime
    state changes.
    """

    name: str
    version: str
    unity_version: str

    tags: list[str] = Field(default_factory=list)
    sorting_layers: list[str] = Field(default_factory=list)
    # layers: list[str] = Field(default_factory=list)
    layers: dict[int, str] = Field(default_factory=dict) # key = layer index (0-31), value = layer name
    rendering_layers: list[str] = Field(default_factory=list)

    scenes: list[SceneDeclaration] = Field(default_factory=list)

class SceneDeclaration(BaseModel):
    """A scene that is known to the game, but not necessarily loaded. This should not change."""

    name: str


# -- Runtime --
# - Log Data -
class LogEntry(BaseModel):

    id: int
    kind: LogType
    message: str
    source: Optional[str] = None # todo - idk if needed
    stack_trace: Optional[str] = None # todo - idk if needed
    count: int = 1 # how many times this log has been repeated (e.g. "3x" in the console) # todo - idk if needed
    timestamp: float # unix timestamp in seconds

# - Status Data -
class Status(BaseModel):
    """The current attach/connection status of the data source."""

    running: bool = False # whether the data source is currently running
    message: Optional[str] = None # optional human-readable message about the status
    # TODO - Others? Like internal state, error codes, etc.

# - Scene Data -
class Scene(SceneDeclaration):
    """If the scene is loaded, this contains its runtime state and hierarchy."""

    roots: list[HierarchyNode] = Field(default_factory=list)

class HierarchyNode(BaseModel):
    """A GameObject row in the Hierarchy tree."""

    id: str
    name: str
    icon: IconName = "cube"
    icon_color: Optional[str] = None # optional CSS color override

    # data: GameObjectData = Field(default_factory=GameObjectData)
    data: GameObjectData = Field(default_factory=lambda: GameObjectData())
    # make it a lambda to shut up `Unresolved reference 'GameObjectData'`

    children: list[HierarchyNode] = Field(default_factory=list)

class GameObjectData(BaseModel):
    """The runtime state of a GameObject, including its components."""

    active: bool = True
    is_static: bool = False
    tag: str = "Untagged"
    layer: int = 0
    # Note: Tag's are unlimited. So use str to match. Layers ar limited (0-31). So use int to match.
    # Layer has some built in's, but rest are game specific.
    # 0 = Default, 1 = TransparentFX, 2 = Ignore Raycast, 3 = User Defined, 4 = Water, 5 = UI, 6-31 = User Defined

    components: list[Component] = Field(default_factory=list)

class Component(BaseModel):
    """One component attached to a GameObject (Transform, a MonoBehaviour, ...)."""

    id: str
    name: str
    type: str
    icon: IconName = "cube"
    # None -> component has no enable checkbox (e.g. Transform).
    # True/False -> component has an enable checkbox (e.g. MonoBehaviour).
    enabled: Optional[bool] = None
    expanded: bool = True
    properties: list[Property] = Field(default_factory=list)

class Property(BaseModel):
    """One property of a component (e.g. Transform.position, Rigidbody.mass, ...)."""
    label: str # The display name of the property, e.g. "Position" or "Move Speed".
    read_only: bool = False # Whether the property is read-only. If true, the user cannot edit it. (I.e. Instance ID)
    kind: PropertyKind # The type of property, which determines how it is displayed and edited.
    value: Any = None # The current value of the property. Type depends on `kind
    # TODO - Look into make classes for each kind of property, e.g. FloatProperty, IntProperty, etc. to make it more type safe.


