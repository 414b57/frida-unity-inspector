import "frida-il2cpp-bridge"

import type {BaseProperty, Property, Vector3Property} from "./models"
import {klass} from "./resolve";

// A miniature component registry to avoid dereferencing freed memory.
// getHierarchyStructure registers every component it walks past here, keyed by handle which are stable across the lifetime of the component.
// getComponentProperties resolves ids through this map instead of casting raw pointers,
// so a stale/unknown id degrades to null instead of dereferencing freed memory.
const knownComponents = new Map<string, Il2Cpp.Object>()

export function rememberComponent(id: string, component: Il2Cpp.Object): void {
    knownComponents.set(id, component)
}

export function getKnownComponent(id: string): Il2Cpp.Object | null {
    return knownComponents.get(id) ?? null
}

// Remove any components from the registry that are not in the provided set of live ids.
export function pruneComponents(liveIds: Set<string>): void {
    for (const id of knownComponents.keys()) {
        if (!liveIds.has(id)) knownComponents.delete(id)
    }
}

// Value parsing / type wrangling helpers.
function toNumber(raw: unknown): number | null {
    if (typeof raw === "number") return Number.isFinite(raw) ? raw : null
    if (typeof raw === "bigint") return Number(raw)
    if (raw instanceof Int64 || raw instanceof UInt64) return raw.toNumber()
    try {
        const underlying = (raw as Il2Cpp.ValueType).field("value__").value
        const n = Number(underlying)
        return Number.isFinite(n) ? n : null
    } catch {
        return null
    }
}

/// Parsers
// Used to convert raw Il2Cpp values into a more structured format for the inspector. Each parser is keyed by the type name of the value it can parse.
const VALUE_PARSERS: Record<string, (raw: unknown, base: BaseProperty) => Property> = {
    /// Basic / primitive types.
    // int
    "System.Byte": (raw, base) => ({ ...base, kind: "int", value: toNumber(raw) ?? 0 }),
    "System.SByte": (raw, base) => ({ ...base, kind: "int", value: toNumber(raw) ?? 0 }),
    "System.Int16": (raw, base) => ({ ...base, kind: "int", value: toNumber(raw) ?? 0 }),
    "System.Int32": (raw, base) => ({ ...base, kind: "int", value: toNumber(raw) ?? 0 }),
    "System.Int64": (raw, base) => ({ ...base, kind: "int", value: toNumber(raw) ?? 0 }),
    "System.UInt16": (raw, base) => ({ ...base, kind: "int", value: toNumber(raw) ?? 0 }),
    "System.UInt32": (raw, base) => ({ ...base, kind: "int", value: toNumber(raw) ?? 0 }),
    "System.UInt64": (raw, base) => ({ ...base, kind: "int", value: toNumber(raw) ?? 0 }),
    // float
    "System.Single": (raw, base) => ({ ...base, kind: "float", value: toNumber(raw) ?? 0 }),
    // double
    "System.Double": (raw, base) => ({ ...base, kind: "double", value: toNumber(raw) ?? 0 }),
    // bool
    "System.Boolean": (raw, base) => ({ ...base, kind: "bool", value: Boolean(raw) }),
    // string
    "System.String": (raw, base) => ({ ...base, kind: "string", value: (raw as Il2Cpp.String).toString() }),
    // char
    "System.Char": (raw, base) => ({ ...base, kind: "string", value: String.fromCharCode(toNumber(raw) ?? 0) }),
    // Enum
    "System.Enum": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        const value = toNumber(rawVT.field("value__").value) ?? 0
        const enumType = rawVT.box().class
        const options: Record<string, number> = {}
        for (const field of enumType.fields) {
            if (field.isStatic && field.type.name.endsWith(enumType.name)) {
                options[field.name] = toNumber(field.value) ?? 0
            }
        }
        return {
            ...base,
            kind: "enum",
            options: options,
            value: value,
        }
    },

    /// Vector / Math Types
    // Vec2/3/4
    "UnityEngine.Vector2": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "vector2",
            value: {
                x: rawVT.field<number>("x").value,
                y: rawVT.field<number>("y").value,
            },
        }
    },
    "UnityEngine.Vector3": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "vector3",
            value: {
                x: rawVT.field<number>("x").value,
                y: rawVT.field<number>("y").value,
                z: rawVT.field<number>("z").value,
            },
        }
    },
    "UnityEngine.Vector4": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "vector4",
            value: {
                x: rawVT.field<number>("x").value,
                y: rawVT.field<number>("y").value,
                z: rawVT.field<number>("z").value,
                w: rawVT.field<number>("w").value,
            },
        }
    },
    // VecInt2/3
    "UnityEngine.Vector2Int": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "vector2int",
            value: {
                x: rawVT.field<number>("m_X").value,
                y: rawVT.field<number>("m_Y").value,
            },
        }
    },
    "UnityEngine.Vector3Int": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "vector3int",
            value: {
                x: rawVT.field<number>("m_X").value,
                y: rawVT.field<number>("m_Y").value,
                z: rawVT.field<number>("m_Z").value,
            },
        }
    },
    // Quaternion
    "UnityEngine.Quaternion": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "quaternion",
            value: {
                x: rawVT.field<number>("x").value,
                y: rawVT.field<number>("y").value,
                z: rawVT.field<number>("z").value,
                w: rawVT.field<number>("w").value,
            },
        }
    },
    // Matrix4x4
    "UnityEngine.Matrix4x4": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "matrix4x4",
            value: {
                m00: rawVT.field<number>("m00").value,
                m01: rawVT.field<number>("m01").value,
                m02: rawVT.field<number>("m02").value,
                m03: rawVT.field<number>("m03").value,

                m10: rawVT.field<number>("m10").value,
                m11: rawVT.field<number>("m11").value,
                m12: rawVT.field<number>("m12").value,
                m13: rawVT.field<number>("m13").value,

                m20: rawVT.field<number>("m20").value,
                m21: rawVT.field<number>("m21").value,
                m22: rawVT.field<number>("m22").value,
                m23: rawVT.field<number>("m23").value,

                m30: rawVT.field<number>("m30").value,
                m31: rawVT.field<number>("m31").value,
                m32: rawVT.field<number>("m32").value,
                m33: rawVT.field<number>("m33").value,
            },
        }
    },
    // Rect/RectInt
    "UnityEngine.Rect": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "rect",
            value: {
                x: rawVT.field<number>("m_XMin").value,
                y: rawVT.field<number>("m_YMin").value,
                width: rawVT.field<number>("m_Width").value,
                height: rawVT.field<number>("m_Height").value,
            },
        }
    },
    "UnityEngine.RectInt": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "rectint",
            value: {
                x: rawVT.field<number>("m_XMin").value,
                y: rawVT.field<number>("m_YMin").value,
                width: rawVT.field<number>("m_Width").value,
                height: rawVT.field<number>("m_Height").value,
            },
        }
    },
    // Bounds/BoundsInt
    "UnityEngine.Bounds": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        const center = rawVT.field<Il2Cpp.ValueType>("m_Center").value
        const extents = rawVT.field<Il2Cpp.ValueType>("m_Extents").value
        return {
            ...base,
            kind: "bounds",
            value: {
                center: {
                    x: center.field<number>("x").value,
                    y: center.field<number>("y").value,
                    z: center.field<number>("z").value,
                },
                extent: {
                    x: extents.field<number>("x").value,
                    y: extents.field<number>("y").value,
                    z: extents.field<number>("z").value,
                },
            }
        }
    },
    "UnityEngine.BoundsInt": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        const position = rawVT.field<Il2Cpp.ValueType>("m_Position").value
        const size = rawVT.field<Il2Cpp.ValueType>("m_Size").value
        return {
            ...base,
            kind: "boundsint",
            value: {
                position: {
                    x: position.field<number>("m_X").value,
                    y: position.field<number>("m_Y").value,
                    z: position.field<number>("m_Z").value,
                },
                size: {
                    x: size.field<number>("m_X").value,
                    y: size.field<number>("m_Y").value,
                    z: size.field<number>("m_Z").value,
                },
            }
        }
    },

    /// Colour types
    // Color/Color32
    "UnityEngine.Color": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "color",
            value: {
                r: rawVT.field<number>("r").value,
                g: rawVT.field<number>("g").value,
                b: rawVT.field<number>("b").value,
                a: rawVT.field<number>("a").value,
            },
        }
    },
    "UnityEngine.Color32": (raw, base) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            ...base,
            kind: "color32",
            value: {
                r: rawVT.field<number>("r").value,
                g: rawVT.field<number>("g").value,
                b: rawVT.field<number>("b").value,
                a: rawVT.field<number>("a").value,
            },
        }
    },
    // Gradient
    // TODO - Implement Gradient parsing
    "UnityEngine.Gradient": (raw, base) => {
        return {
            ...base,
            kind: "gradient",
            value: "TODO - Implement Gradient parsing",
            read_only: true,
        }
    },

    /// Array / Collection types
    // TODO - Implement array/collection parsing

    /// Object / Reference types
    "UnityEngine.Object": (raw, base) => {
        const obj = raw as Il2Cpp.Object
        return {
            ...base,
            kind: "object",
            value: obj,
            // Special case - Override the read_only flag to always be true. Dont allow editing.
            read_only: true,
        }
    },
    "UnityEngine.Component": (raw, base) => {
        const obj = raw as Il2Cpp.Object
        return {
            ...base,
            kind: "component",
            value: obj,
            // Special case - Override the read_only flag to always be true. Dont allow editing.
            read_only: true,
        }
    }
}

function resolveParser(type: Il2Cpp.Type, baseComponentClass: Il2Cpp.Class): ((raw: unknown, base: BaseProperty) => Property) | undefined {
    const direct = VALUE_PARSERS[type.name]
    if (direct) return direct
    // field.type.name returns the name of enum (DataTestScript.ExampleEnum), which wont match via direct `System.Enum` lookup. So we need to check if the type is an enum and return the enum parser if so.
    if (type.class.isEnum) return VALUE_PARSERS["System.Enum"]
    // Check if obj is a componenet, if so call the component parser. This is a bit of a hack, but it works for now. TODO - Improve this to be more robust.
    if (type.class.isSubclassOf(baseComponentClass, true)) return VALUE_PARSERS["UnityEngine.Component"]
    return undefined
}

// TODO - IMPROVE - Make it so we can do subclasses i.e. `UnityEngine.Renderer`/`UnityEngine.Collider` so dont have to write a custom parser for every single subclass of those. (e.g. MeshRenderer, BoxCollider, etc.)
const CUSTOM_COMPONENT_PARSERS: Record<string, (component: Il2Cpp.Object) => Property[]> = {
    // "UnityEngine.Transform": (component) => [...],
    "UnityEngine.MeshRenderer": component => {
        const properties: Property[] = []

        /// UnityEngine.Renderer properties
        // SortingLayerID
        const sortingLayerID = component.tryMethod<number>("get_sortingLayerID")?.invoke() ?? null
        if (sortingLayerID !== null) {
            properties.push({
                label: "Sorting Layer ID",
                is_static: false,
                read_only: true,
                source: "accessor",
                getter: "get_sortingLayerID",
                setter: null,
                kind: "int",
                value: sortingLayerID,
            })
        }

        // SortingOrder
        const sortingOrder = component.tryMethod<number>("get_sortingOrder")?.invoke() ?? null
        if (sortingOrder !== null) {
            properties.push({
                label: "Sorting Order",
                is_static: false,
                read_only: true,
                source: "accessor",
                getter: "get_sortingOrder",
                setter: null,
                kind: "int",
                value: sortingOrder,
            })
        }

        // SortingGroupID
        const sortingGroupID = component.tryMethod<number>("get_sortingGroupID")?.invoke() ?? null
        if (sortingGroupID !== null) {
            properties.push({
                label: "Sorting Group ID",
                is_static: false,
                read_only: true,
                source: "accessor",
                getter: "get_sortingGroupID",
                setter: null,
                kind: "int",
                value: sortingGroupID,
            })
        }

        // SortingGroupOrder
        const sortingGroupOrder = component.tryMethod<number>("get_sortingGroupOrder")?.invoke() ?? null
        if (sortingGroupOrder !== null) {
            properties.push({
                label: "Sorting Group Order",
                is_static: false,
                read_only: true,
                source: "accessor",
                getter: "get_sortingGroupOrder",
                setter: null,
                kind: "int",
                value: sortingGroupOrder,
            })
        }

        /// UnityEngine.MeshRenderer specific properties
        // This has no specific props. Only default.

        return properties
    }
}

/** Full reflection scan of one component: field-backed, accessor-backed, then custom per-type extras. */
export function parseComponentProperties(component: Il2Cpp.Object): Property[] {
    const baseComponentClass = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image.class("UnityEngine.Component")

    const componentClass = component.class
    const componentName = componentClass.name
    const componentType = `${componentClass.namespace ? componentClass.namespace + "." : ""}${componentClass.name}`

    const properties: Property[] = []

    // Field-backed properties.
    for (const field of componentClass.fields) {
        if (field.isStatic) {
            continue // TODO - Implement support for static. rn does `04:36:43.983  WARNING   fui.utils.frida_injector   [agent] Failed to read field kMinAperture of component "Main Camera" (Camera): Il2CppError: couldn't find non-static field kMinAperture in hierarchy of class UnityEngine.Camera`
        }
        const parse = resolveParser(field.type, baseComponentClass)
        if (!parse) { // Only read fields whose type we can actually render.
            // console.warn(`No parser for field ${field.name} of component ${componentName} (${componentType}) with type ${field.type.name}`)
            continue
        }

        try {
            properties.push(parse(component.field(field.name).value, {
                label: field.name,
                is_static: false,
                read_only: false,
                source: "field",
                member: field.name,
            }))
        } catch (e) {
            console.warn(`Failed to read field ${field.name} of component ${componentName} (${componentType}): ${e}`)
        }
    }

    // Accessor-backed properties (get_X/set_X method pairs).
    // (e.g. Transform only exposes position/rotation/scale through accessors).
    const seenLabels = new Set(properties.map((p) => p.label))
    for (const getter of componentClass.methods) {
        if (getter.isStatic || getter.parameterCount !== 0 || !getter.name.startsWith("get_")) continue
        const accessorName = getter.name.substring(4)
        if (accessorName.length === 0 || seenLabels.has(accessorName)) continue
        const parse = resolveParser(getter.returnType, baseComponentClass)
        if (!parse) { // Only invoke getters whose result we can actually render.
            // console.warn(`No parser for getter ${getter.name} of component ${componentName} (${componentType}) with return type ${getter.returnType.name}`)
            continue
        }

        try {
            const setterName = `set_${accessorName}`
            const hasSetter = componentClass.tryMethod(setterName, 1) !== null
            properties.push(parse(component.method(getter.name, 0).invoke(), {
                label: accessorName,
                is_static: false,
                read_only: !hasSetter,
                source: "accessor",
                getter: getter.name,
                setter: hasSetter ? setterName : null,
            }))
            seenLabels.add(accessorName)
        } catch (e) {
            console.warn(`Failed to invoke getter ${getter.name} of component ${componentName} (${componentType}): ${e}`)
        }
    }

    // Component-specific custom properties (synthetic values, oddly-named members, multi-call reads)
    const customParser = CUSTOM_COMPONENT_PARSERS[componentType]
    if (customParser) {
        try {
            properties.push(...customParser(component))
        } catch (e) {
            console.warn(`Custom property parser for component ${componentName} (${componentType}) failed: ${e}`)
        }
    }

    return properties
}

/// Writers
// Used to convert structured Property values back into raw Il2Cpp values for writing back to the game. Each writer is keyed by the type name of the value it can write.
const VALUE_WRITERS: Record<string, (property: Property, writeType: Il2Cpp.Type) => any> = {
    /// Basic / primitive types.
    "System.Byte": (property) => property.value,
    "System.SByte": (property) => property.value,
    "System.Int16": (property) => property.value,
    "System.Int32": (property) => property.value,
    "System.Int64": (property) => property.value,
    "System.UInt16": (property) => property.value,
    "System.UInt32": (property) => property.value,
    "System.UInt64": (property) => property.value,
    // float
    "System.Single": (property) => property.value,
    // double
    "System.Double": (property) => property.value,
    // bool
    "System.Boolean": (property) => property.value,
    // string
    "System.String": (property) => Il2Cpp.string(property.value),
    // char
    "System.Char": (property) => property.value.charCodeAt(0),
    // Enum
    "System.Enum": (property, writeType) => {
        const size = writeType.class.valueTypeSize
        const handle = Memory.alloc(size)
        const v = property.value as number
        switch (size) {
            case 1: handle.writeS8(v); break
            case 2: handle.writeS16(v); break
            case 8: handle.writeS64(v); break
            default: handle.writeS32(v); break // 4-byte int is the common case
        }
        return new Il2Cpp.ValueType(handle, writeType)
    },

    /// Vector / Math Types
    "UnityEngine.Vector3": (property) => {
        const casted = property as Vector3Property;
        const Vector3Class = klass("UnityEngine.CoreModule", "UnityEngine.Vector3")
        if (!Vector3Class) throw new Error("Vector3 class not found")
        const v = Vector3Class.alloc()
        v.method(".ctor", 3).invoke(casted.value.x, casted.value.y, casted.value.z)
        return v.unbox()
    }
    // TODO - Rest

    /// Colour types
    // TODO

    /// Array / Collection types
    // TODO

    /// Object / Reference types
    // TODO
}

function resolveWriter(type: Il2Cpp.Type, baseComponentClass: Il2Cpp.Class): ((property: Property, writeType: Il2Cpp.Type) => any) | undefined {
    const direct = VALUE_WRITERS[type.name]
    if (direct) return direct
    // field.type.name returns the name of enum (DataTestScript.ExampleEnum), which wont match via direct `System.Enum` lookup. So we need to check if the type is an enum and return the enum writer if so.
    if (type.class.isEnum) return VALUE_WRITERS["System.Enum"]
    // Check if obj is a componenet, if so call the component writer. This is a bit of a hack, but it works for now. TODO - Improve this to be more robust.
    if (type.class.isSubclassOf(baseComponentClass, true)) return VALUE_WRITERS["UnityEngine.Component"]
    return undefined
}
// TODO - Merge resolve writer and parser. as seems to work same? idk. Look into future.

const CUSTOM_COMPONENT_WRITERS: Record<string, (component: Il2Cpp.Object, property: Property) => Property | null> = {
    // TODO - idk if needed. But match for now.
}

export function writeComponentProperty(componentHandleId: string, property: Property): Property | null {
    const component = getKnownComponent(componentHandleId)
    if (component === null) {
        console.warn(`writeComponentProperty: Unknown component id ${componentHandleId}`)
        return null
    }
    const componentClass = component.class

    // NOTE: Myb rename - as not custom comp anymore. just synthetic handlers.
    const componentType = `${componentClass.namespace ? componentClass.namespace + "." : ""}${componentClass.name}`
    const customWriter = CUSTOM_COMPONENT_WRITERS[componentType]
    if (customWriter) {
        try {
            return customWriter(component, property)
        } catch (e) {
            console.warn(`Custom property writer for component ${component.class.name} (${componentType}) failed: ${e}`)
            return null
        }
    }


    // Determine write type - also cache field/setter for later use when getting type. So dont have to re-resolve.
    let field: Il2Cpp.BoundField | Il2Cpp.Field | null | undefined = null
    let getter: Il2Cpp.BoundMethod | Il2Cpp.Method | null | undefined = null
    let setter: Il2Cpp.BoundMethod | Il2Cpp.Method | null | undefined = null
    let getType: Il2Cpp.Type | null = null
    let writeType: Il2Cpp.Type | null = null
    // Field handle
    if (property.source === "field" && property.is_static && property.member) {
        field = component.class.tryField(property.member)
        if (!field) {
            console.warn(`writeComponentProperty: Unknown field ${property.member} on component ${component.class.name}`)
            return null
        }
        writeType = field.type
        getType = field.type
    } else if (property.source === "field" && !property.is_static && property.member) {
        field = component.tryField(property.member)
        if (!field) {
            console.warn(`writeComponentProperty: Unknown field ${property.member} on component ${component.class.name}`)
            return null
        }
        writeType = field.type
        getType = field.type
    }
    // Accessor handle
    else if (property.source === "accessor" && property.is_static && property.setter && property.getter) {
        setter = component.class.tryMethod(property.setter, 1)
        if (!setter) {
            console.warn(`writeComponentProperty: Unknown static setter ${property.setter} on component ${component.class.name}`)
            return null
        }
        writeType = setter.parameters[0].type

        getter = component.class.tryMethod(property.getter, 0)
        if (!getter) {
            console.warn(`writeComponentProperty: Unknown static getter ${property.getter} on component ${component.class.name}`)
            return null
        }
        getType = getter.returnType
    } else if (property.source === "accessor" && !property.is_static && property.setter && property.getter) {
        setter = component.tryMethod(property.setter, 1)
        if (!setter) {
            console.warn(`writeComponentProperty: Unknown setter ${property.setter} on component ${component.class.name}`)
            return null
        }
        writeType = setter.parameters[0].type

        getter = component.tryMethod(property.getter, 0)
        if (!getter) {
            console.warn(`writeComponentProperty: Unknown getter ${property.getter} on component ${component.class.name}`)
            return null
        }
        getType = getter.returnType
    } else {
        console.warn(`writeComponentProperty: Unknown property source ${property.source} or missing member/setter/getter on component ${component.class.name}`)
        return null
    }

    const baseComponentClass = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image.class("UnityEngine.Component")
    const writer = resolveWriter(writeType, baseComponentClass)
    const parser = resolveParser(getType, baseComponentClass)
    if (!writer) {
        console.warn(`writeComponentProperty: No writer for type ${writeType.name} on component ${component.class.name}`)
        return null
    }
    if (!parser) {
        console.warn(`writeComponentProperty: No parser for type ${writeType.name} on component ${component.class.name}`)
        return null
    }

    if (field) {
        try {
            field.value = writer(property, writeType)
            return parser(field.value, property)
        } catch (e) {
            console.warn(`writeComponentProperty: Failed to write field ${field.name} on component ${component.class.name}: ${e}`)
            return null
        }
    } else if (setter) {
        try {
            setter.invoke(writer(property, writeType))
            return parser(getter!.invoke(), property)
        } catch (e) {
            console.warn(`writeComponentProperty: Failed to invoke setter ${setter.name} on component ${component.class.name}: ${e}`)
            return null
        }
    } else {
        console.warn(`writeComponentProperty: No field or setter found for property ${property.label} on component ${component.class.name}`)
        return null
    }
}