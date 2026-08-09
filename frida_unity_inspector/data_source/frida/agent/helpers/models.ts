/* AUTO-GENERATED from ../../protocol_spec.py + ../../../models.py - do not edit by hand. */

export type LogType = "log" | "warning" | "error"

export type IconName = "cube" | "camera" | "light" | "canvas" | "script" | "gear" | "move" | "rotate" | "scale" | "rect" | "headphones" | "unknown" | "error" | "warning" | "check" | "cross"

export type PropertyKind = "int" | "single" | "float" | "double" | "bool" | "string" | "char" | "long" | "enum" | "vector2" | "vector3" | "vector4" | "vector2int" | "vector3int" | "quaternion" | "matrix4x4" | "rect" | "rectint" | "bounds" | "boundsint" | "color" | "color32" | "gradient" | "array" | "dictionary" | "object"

export type PropertySource = "field" | "accessor" | "synthetic"

export interface GameContext {
    version: string
    unity_version: string
    render_pipeline?: string | null
}

export interface SceneDeclaration {
    name: string
}

export interface LogEntry {
    id: number
    kind: LogType
    message: string
    source?: string | null
    stack_trace?: string | null
    count?: number
    timestamp: number
}

export interface Status {
    running?: boolean
    message?: string | null
}

export interface Scene {
    name: string
    roots?: HierarchyNode[]
}

export interface HierarchyNode {
    id: string
    name: string
    icon?: IconName
    icon_color?: string | null
    data?: GameObjectData
    children?: HierarchyNode[]
}

export interface GameObjectData {
    active?: boolean
    tag?: string
    layer?: number
    components?: Component[]
}

export interface Component {
    id: string
    name: string
    type: string
    icon?: IconName
    enabled?: boolean | null
    expanded?: boolean
    properties?: Property[]
}

export interface BaseProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
}

export interface IntProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "int"
    value: number
}

export interface SingleProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "single"
    value: number
}

export interface FloatProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "float"
    value: number
}

export interface DoubleProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "double"
    value: number
}

export interface BoolProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "bool"
    value: boolean
}

export interface StringProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "string"
    value: string
}

export interface CharProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "char"
    value: string
}

export interface LongProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "long"
    value: number
}

export interface EnumProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "enum"
    options?: string[]
    value: string
}

export interface Vector2 {
    x: number
    y: number
}

export interface Vector2Property {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "vector2"
    value: Vector2
}

export interface Vector3 {
    x: number
    y: number
    z: number
}

export interface Vector3Property {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "vector3"
    value: Vector3
}

export interface Vector4 {
    x: number
    y: number
    z: number
    w: number
}

export interface Vector4Property {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "vector4"
    value: Vector4
}

export interface Vector2Int {
    x: number
    y: number
}

export interface Vector2IntProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "vector2int"
    value: Vector2Int
}

export interface Vector3Int {
    x: number
    y: number
    z: number
}

export interface Vector3IntProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "vector3int"
    value: Vector3Int
}

export interface Quaternion {
    x: number
    y: number
    z: number
    w: number
}

export interface QuaternionProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "quaternion"
    value: Quaternion
}

export interface Matrix4x4 {
    m00: number
    m01: number
    m02: number
    m03: number
    m10: number
    m11: number
    m12: number
    m13: number
    m20: number
    m21: number
    m22: number
    m23: number
    m30: number
    m31: number
    m32: number
    m33: number
}

export interface Matrix4x4Property {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "matrix4x4"
    value: Matrix4x4
}

export interface Rect {
    x: number
    y: number
    width: number
    height: number
}

export interface RectProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "rect"
    value: Rect
}

export interface RectInt {
    x: number
    y: number
    width: number
    height: number
}

export interface RectIntProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "rectint"
    value: RectInt
}

export interface Bounds {
    center: Vector3
    size: Vector3
}

export interface BoundsProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "bounds"
    value: Bounds
}

export interface BoundsInt {
    position: Vector3Int
    size: Vector3Int
}

export interface BoundsIntProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "boundsint"
    value: BoundsInt
}

export interface Color {
    r: number
    g: number
    b: number
    a: number
}

export interface ColorProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "color"
    value: Color
}

export interface Color32 {
    r: number
    g: number
    b: number
    a: number
}

export interface Color32Property {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "color32"
    value: Color32
}

export interface GradientProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "gradient"
    value: any
}

export interface ArrayProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "array"
    value?: any[]
}

export interface DictionaryProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "dictionary"
    value?: Record<any, any>
}

export interface ObjectProperty {
    label: string
    is_static?: boolean
    read_only?: boolean
    source?: PropertySource
    member?: string | null
    getter?: string | null
    setter?: string | null
    kind?: "object"
    value: any
}

export type Property = IntProperty | SingleProperty | FloatProperty | DoubleProperty | BoolProperty | StringProperty | CharProperty | LongProperty | EnumProperty | Vector2Property | Vector3Property | Vector4Property | Vector2IntProperty | Vector3IntProperty | QuaternionProperty | Matrix4x4Property | RectProperty | RectIntProperty | BoundsProperty | BoundsIntProperty | ColorProperty | Color32Property | GradientProperty | ArrayProperty | DictionaryProperty | ObjectProperty
