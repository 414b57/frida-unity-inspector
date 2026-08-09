import "frida-il2cpp-bridge"

import type { Property, Vector3 } from "./models"

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

// Value parsing / type wrangling helpers. These are used to convert raw Il2Cpp values into a more structured format for the inspector.
function toNumber(raw: unknown): number | null {
    if (typeof raw === "number") return Number.isFinite(raw) ? raw : null
    if (typeof raw === "bigint") return Number(raw)
    // Enums come back as a ValueType wrapping the underlying `value__` field.
    try {
        const underlying = (raw as Il2Cpp.ValueType).field("value__").value
        const n = Number(underlying)
        return Number.isFinite(n) ? n : null
    } catch {
        return null
    }
}

type ParsedValue =
    | { kind: "float" | "int"; value: number }
    | { kind: "bool"; value: boolean }
    | { kind: "string"; value: string }
    | { kind: "vector3"; value: Vector3 }

const VALUE_PARSERS: Record<string, (raw: unknown) => ParsedValue> = { // Returns in the property format, as specified within models.ts
    "System.Single": (raw) => ({ kind: "float", value: toNumber(raw) ?? 0 }),
    "System.Double": (raw) => ({ kind: "float", value: toNumber(raw) ?? 0 }),
    "System.Int32": (raw) => ({ kind: "int", value: toNumber(raw) ?? 0 }),
    "System.Int64": (raw) => ({ kind: "int", value: toNumber(raw) ?? 0 }),
    "System.UInt32": (raw) => ({ kind: "int", value: toNumber(raw) ?? 0 }),
    "System.UInt64": (raw) => ({ kind: "int", value: toNumber(raw) ?? 0 }),
    "System.Int16": (raw) => ({ kind: "int", value: toNumber(raw) ?? 0 }),
    "System.UInt16": (raw) => ({ kind: "int", value: toNumber(raw) ?? 0 }),
    "System.Byte": (raw) => ({ kind: "int", value: toNumber(raw) ?? 0 }),
    "System.SByte": (raw) => ({ kind: "int", value: toNumber(raw) ?? 0 }),
    "System.Boolean": (raw) => ({ kind: "bool", value: Boolean(raw) }),
    "System.String": (raw) => ({ kind: "string", value: (raw as Il2Cpp.String).toString() }),
    "UnityEngine.Vector3": (raw) => {
        const rawVT = raw as Il2Cpp.ValueType
        return {
            kind: "vector3",
            value: {
                x: rawVT.field<number>("x").value,
                y: rawVT.field<number>("y").value,
                z: rawVT.field<number>("z").value,
            },
        }
    },
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
    const componentClass = component.class
    const componentName = componentClass.name
    const componentType = `${componentClass.namespace ? componentClass.namespace + "." : ""}${componentClass.name}`

    const properties: Property[] = []

    // Field-backed properties.
    for (const field of componentClass.fields) {
        if (field.isStatic) {
            continue // TODO - Implement support for static. rn does `04:36:43.983  WARNING   fui.utils.frida_injector   [agent] Failed to read field kMinAperture of component "Main Camera" (Camera): Il2CppError: couldn't find non-static field kMinAperture in hierarchy of class UnityEngine.Camera`
        }
        const parse = VALUE_PARSERS[field.type.name]
        if (!parse) continue

        try {
            properties.push({
                label: field.name,
                is_static: false,
                read_only: false,
                source: "field",
                member: field.name,
                ...parse(component.field(field.name).value),
            })
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
        const parse = VALUE_PARSERS[getter.returnType.name]
        if (!parse) continue // Only invoke getters whose result we can actually render.

        try {
            const setterName = `set_${accessorName}`
            const hasSetter = componentClass.tryMethod(setterName, 1) !== null
            properties.push({
                label: accessorName,
                is_static: false,
                read_only: !hasSetter,
                source: "accessor",
                getter: getter.name,
                setter: hasSetter ? setterName : null,
                ...parse(component.method(getter.name, 0).invoke()),
            })
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
