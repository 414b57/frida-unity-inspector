from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional, Union, Annotated

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
    """List of unity serialized property types."""

    # Basic / Primitive Types
    INT = "int"
    FLOAT = "float"
    DOUBLE = "double"
    BOOL = "bool"
    STRING = "string"
    CHAR = "char"
    LONG = "long"
    ENUM = "enum"

    # Vector / Math Types
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"
    VECTOR4 = "vector4"
    VECTOR2INT = "vector2int"
    VECTOR3INT = "vector3int"
    QUATERNION = "quaternion"
    MATRIX4X4 = "matrix4x4"
    RECT = "rect"
    RECTINT = "rectint"
    BOUNDS = "bounds"
    BOUNDSINT = "boundsint"

    # Colour Types
    COLOR = "color" # fuck american spelling
    COLOR32 = "color32" # TODO - Not sure if needed?
    GRADIENT = "gradient"

    # Array / Collection Types
    ARRAY = "array"
    DICTIONARY = "dictionary" # TODO - Not sure if this possible? As unity doesnt serialize dictionaires. but probs can get this data from frida. So left in for now.

    # Object / Reference Types
    OBJECT = "object"

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


# class Property(BaseModel):
#     """One property of a component (e.g. Transform.position, Rigidbody.mass, ...)."""
#     label: str # The display name of the property, e.g. "Position" or "Move Speed".
#     read_only: bool = False # Whether the property is read-only. If true, the user cannot edit it. (I.e. Instance ID)
#     kind: PropertyKind # The type of property, which determines how it is displayed and edited.
#     value: Any = None # The current value of the property. Type depends on `kind
#     # TODO - Look into make classes for each kind of property, e.g. FloatProperty, IntProperty, etc. to make it more type safe.

# - Properties -
class BaseProperty(BaseModel):
    label: str
    read_only: bool = False

# Basic / Primitive Types
class IntProperty(BaseProperty):
    kind: Literal[PropertyKind.INT] = PropertyKind.INT
    value: int

class FloatProperty(BaseProperty):
    kind: Literal[PropertyKind.FLOAT] = PropertyKind.FLOAT
    value: float

class DoubleProperty(BaseProperty):
    kind: Literal[PropertyKind.DOUBLE] = PropertyKind.DOUBLE
    value: float

class BoolProperty(BaseProperty):
    kind: Literal[PropertyKind.BOOL] = PropertyKind.BOOL
    value: bool

class StringProperty(BaseProperty):
    kind: Literal[PropertyKind.STRING] = PropertyKind.STRING
    value: str

class CharProperty(BaseProperty):
    kind: Literal[PropertyKind.CHAR] = PropertyKind.CHAR
    value: str = Field(..., min_length=1, max_length=1) # single character string

class LongProperty(BaseProperty):
    kind: Literal[PropertyKind.LONG] = PropertyKind.LONG
    value: int

class EnumProperty(BaseProperty):
    kind: Literal[PropertyKind.ENUM] = PropertyKind.ENUM
    options: list[str] = Field(default_factory=list) # list of possible enum values
    value: str # current enum value

# Vector / Math Types
class Vector2(BaseModel):
    x: float
    y: float

class Vector2Property(BaseProperty):
    kind: Literal[PropertyKind.VECTOR2] = PropertyKind.VECTOR2
    value: Vector2

class Vector3(BaseModel):
    x: float
    y: float
    z: float

class Vector3Property(BaseProperty):
    kind: Literal[PropertyKind.VECTOR3] = PropertyKind.VECTOR3
    value: Vector3

class Vector4(BaseModel):
    x: float
    y: float
    z: float
    w: float

class Vector4Property(BaseProperty):
    kind: Literal[PropertyKind.VECTOR4] = PropertyKind.VECTOR4
    value: Vector4

class Vector2Int(BaseModel):
    x: int
    y: int

class Vector2IntProperty(BaseProperty):
    kind: Literal[PropertyKind.VECTOR2INT] = PropertyKind.VECTOR2INT
    value: Vector2Int

class Vector3Int(BaseModel):
    x: int
    y: int
    z: int

class Vector3IntProperty(BaseProperty):
    kind: Literal[PropertyKind.VECTOR3INT] = PropertyKind.VECTOR3INT
    value: Vector3Int

class Quaternion(BaseModel):
    x: float
    y: float
    z: float
    w: float

class QuaternionProperty(BaseProperty):
    kind: Literal[PropertyKind.QUATERNION] = PropertyKind.QUATERNION
    value: Quaternion

class Matrix4x4(BaseModel):
    m00: float; m01: float; m02: float; m03: float
    m10: float; m11: float; m12: float; m13: float
    m20: float; m21: float; m22: float; m23: float
    m30: float; m31: float; m32: float; m33: float

class Matrix4x4Property(BaseProperty):
    kind: Literal[PropertyKind.MATRIX4X4] = PropertyKind.MATRIX4X4
    value: Matrix4x4

class Rect(BaseModel):
    x: float
    y: float
    width: float
    height: float

class RectProperty(BaseProperty):
    kind: Literal[PropertyKind.RECT] = PropertyKind.RECT
    value: Rect

class RectInt(BaseModel):
    x: int
    y: int
    width: int
    height: int

class RectIntProperty(BaseProperty):
    kind: Literal[PropertyKind.RECTINT] = PropertyKind.RECTINT
    value: RectInt

class Bounds(BaseModel):
    center: Vector3
    size: Vector3

class BoundsProperty(BaseProperty):
    kind: Literal[PropertyKind.BOUNDS] = PropertyKind.BOUNDS
    value: Bounds

class BoundsInt(BaseModel):
    position: Vector3Int
    size: Vector3Int

class BoundsIntProperty(BaseProperty):
    kind: Literal[PropertyKind.BOUNDSINT] = PropertyKind.BOUNDSINT
    value: BoundsInt

# Colour Types
class Color(BaseModel):
    r: float
    g: float
    b: float
    a: float

class ColorProperty(BaseProperty):
    kind: Literal[PropertyKind.COLOR] = PropertyKind.COLOR
    value: Color

class Color32(BaseModel):
    r: int
    g: int
    b: int
    a: int

class Color32Property(BaseProperty):
    kind: Literal[PropertyKind.COLOR32] = PropertyKind.COLOR32
    value: Color32

class GradientProperty(BaseProperty):
    kind: Literal[PropertyKind.GRADIENT] = PropertyKind.GRADIENT
    value: Any # TODO - Not sure how to represent this better.

# Array / Collection Types
class ArrayProperty(BaseProperty):
    kind: Literal[PropertyKind.ARRAY] = PropertyKind.ARRAY
    value: list[Any] = Field(default_factory=list) # TODO - Not sure how to represent this better.

class DictionaryProperty(BaseProperty):
    kind: Literal[PropertyKind.DICTIONARY] = PropertyKind.DICTIONARY
    value: dict[Any, Any] = Field(default_factory=dict) # TODO - Not sure how to represent this better.

# Object / Reference Types
class ObjectProperty(BaseProperty):
    kind: Literal[PropertyKind.OBJECT] = PropertyKind.OBJECT
    value: Any # TODO - Not sure how to represent this better.

Property = Annotated[
    Union[
        # Basic / Primitive Types
        IntProperty,
        FloatProperty,
        DoubleProperty,
        BoolProperty,
        StringProperty,
        CharProperty,
        LongProperty,
        EnumProperty,

        # Vector / Math Types
        Vector2Property,
        Vector3Property,
        Vector4Property,
        Vector2IntProperty,
        Vector3IntProperty,
        QuaternionProperty,
        Matrix4x4Property,
        RectProperty,
        RectIntProperty,
        BoundsProperty,
        BoundsIntProperty,

        # Colour Types
        ColorProperty,
        Color32Property,
        GradientProperty,

        # Array / Collection Types
        ArrayProperty,
        DictionaryProperty,

        # Object / Reference Types
        ObjectProperty,
    ],
    Field(discriminator="kind")
]

