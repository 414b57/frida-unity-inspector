import "frida-il2cpp-bridge"

import { defineCapability, getCapability } from "../helpers/capability"
import type {Component, GameObjectData, HierarchyNode, IconName, Property, Vector3} from "../helpers/models"
import { Capabilities } from "../helpers/protocol"
import {klass, method} from "../helpers/resolve"

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

const VALUE_PARSERS: Record<string, (raw: unknown) => ParsedValue> = {
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

function parseGameObjectToHierarchyNode(gameObject: Il2Cpp.Object): HierarchyNode {
    // Hierarchy Node
    const id = gameObject.handle.toString()
    const name = gameObject.tryMethod<Il2Cpp.String>("get_name")?.invoke().toString() ?? "Unknown-GameObject"
    const icon: IconName = "unknown" // TODO: Determine, either here, or in python side. idk yet.

    // Data for the GameObject
    const active = gameObject.tryMethod<boolean>("get_activeSelf")?.invoke() ?? false
    const tag = gameObject.tryMethod<Il2Cpp.String>("get_tag")?.invoke().toString() ?? "Unknown-Tag"
    const layer = gameObject.tryMethod<number>("get_layer")?.invoke() ?? -1
    const transform = gameObject.tryMethod<Il2Cpp.Object>("get_transform")?.invoke() ?? null

    // TODO - Componennts
    const components: Component[] = [] // TODO: Implement better component parsing

    const componentClass = klass("UnityEngine.CoreModule", "UnityEngine.Component")

    const behaviourClass = klass("UnityEngine.CoreModule", "UnityEngine.Behaviour")
    const colliderClass = klass("UnityEngine.PhysicsModule", "UnityEngine.Collider")
    const rendererClass = klass("UnityEngine.CoreModule", "UnityEngine.Renderer")

    const getComponentsMethod = gameObject.tryMethod<Il2Cpp.Array<Il2Cpp.Object>>("GetComponents", 0)
    if (componentClass && getComponentsMethod) {
        const componentArray = getComponentsMethod.inflate(componentClass).invoke()
        if (componentArray) {
            for (const component of componentArray) {
                const componentClass = component.class
                const componentId = component.handle.toString()
                const componentName = component.class.name
                const componentType = `${component.class ?component.class.namespace + "." : ""}${component.class.name}`
                const componentIcon: IconName = "unknown" // TODO: Determine icon for the component
                const componentExpanded = true // No way to determine if expanded or not, so default to true

                // determine if can change enabled state - unityengine.Behaviour + unityengine.Collider + unityenginer.Renderer
                let enabled: boolean | null = null // Null = cant change, true/false can change/current state
                if (behaviourClass && componentClass.isSubclassOf(behaviourClass, true)) {
                    enabled = component.tryMethod<boolean>("get_enabled")?.invoke() ?? null
                } else if (colliderClass && componentClass.isSubclassOf(colliderClass, true)) {
                    enabled = component.tryMethod<boolean>("get_enabled")?.invoke() ?? null
                } else if (rendererClass && componentClass.isSubclassOf(rendererClass, true)) {
                    // TODO - Look into this. Can be turnt on/off. But in `Renderer` it has no `get_enabled` only `set_enabled`?
                    enabled = component.tryMethod<boolean>("get_enabled")?.invoke() ?? null
                }
                // console.log(`Component ${componentName} (${componentType}) enabled state: ${enabled} (subclass of Behaviour: ${behaviourClass && componentClass.isSubclassOf(behaviourClass, true)}, subclass of Collider: ${colliderClass && componentClass.isSubclassOf(colliderClass, true)}, subclass of Renderer: ${rendererClass && componentClass.isSubclassOf(rendererClass, true)})`)

                const componentProperties: Property[] = [] // TODO - IMPROVE - Sub functions, etc.

                // Field-backed properties.
                for (const field of componentClass.fields) {
                    if (field.isStatic) {
                        continue // TODO - Implement support for static. rn does `04:36:43.983  WARNING   fui.utils.frida_injector   [agent] Failed to read field kMinAperture of component "Main Camera" (Camera): Il2CppError: couldn't find non-static field kMinAperture in hierarchy of class UnityEngine.Camera`
                    }
                    const parse = VALUE_PARSERS[field.type.name]
                    if (!parse) continue

                    try {
                        componentProperties.push({
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
                const seenLabels = new Set(componentProperties.map((p) => p.label))
                for (const getter of componentClass.methods) {
                    if (getter.isStatic || getter.parameterCount !== 0 || !getter.name.startsWith("get_")) continue
                    const accessorName = getter.name.substring(4)
                    // console.log(`Component ${componentName} (${componentType}) has accessor: ${accessorName}`)
                    if (accessorName.length === 0 || seenLabels.has(accessorName)) continue
                    const parse = VALUE_PARSERS[getter.returnType.name]
                    if (!parse) continue // Only invoke getters whose result we can actually render.

                    try {
                        const setterName = `set_${accessorName}`
                        const hasSetter = componentClass.tryMethod(setterName, 1) !== null
                        componentProperties.push({
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
                        componentProperties.push(...customParser(component))
                    } catch (e) {
                        console.warn(`Custom property parser for component ${componentName} (${componentType}) failed: ${e}`)
                    }
                }

                components.push({
                    id: componentId,
                    name: componentName,
                    type: componentType,
                    icon: componentIcon,

                    enabled: enabled,
                    expanded: componentExpanded,
                    properties: componentProperties,
                })
            }
        } else {
            console.warn(`GameObject ${name} states has componenets, but getcomponents returned null. This is unexpected.`)
        }
    } else {
        console.warn(`GameObject ${name} has no GetComponents method or Component class, cannot get components.`)
    }

    // Recursively get and parse children
    const children: HierarchyNode[] = []
    if (transform) {
        const childCount = transform.tryMethod<number>("get_childCount")?.invoke() ?? 0
        for (let i = 0; i < childCount; i++) {
            const childTransform = transform.tryMethod<Il2Cpp.Object>("GetChild", 1)?.invoke(i) ?? null
            if (!childTransform) {
                console.warn(`GameObject ${name} has no child at index ${i} despite childCount being ${childCount}.`)
                continue;
            }

            const childGameObject = childTransform.tryMethod<Il2Cpp.Object>("get_gameObject")?.invoke() ?? null
            if (!childGameObject) {
                console.warn(`Child transform at index ${i} of GameObject ${name} has no gameObject. what?`)
                continue;
            }

            const childNode = parseGameObjectToHierarchyNode(childGameObject)
            children.push(childNode)
        }
    } else {
        console.warn(`GameObject ${name} has no transform, cannot get children.`)
    }

    return {
        id: id,
        name: name,
        icon: icon,
        data: {
            active: active,
            tag: tag,
            layer: layer,
            components: components,
        },
        children: children,
    }
}

defineCapability({
    name: Capabilities.GET_CURRENT_SCENE_HIERARCHY,

    detect: () => {
        return (
            method("UnityEngine.CoreModule", "UnityEngine.SceneManagement.Scene", "GetRootGameObjects") !== null &&
            method("UnityEngine.CoreModule", "UnityEngine.GameObject", "GetComponents", 1) !== null
        )
    },

    implementation: () =>
        Il2Cpp.perform(async () => {
            const scene: Il2Cpp.ValueType = await getCapability(Capabilities.GET_CURRENT_SCENE)()
            if (scene === null) return null

            const getRootGameObjects = scene.tryMethod<Il2Cpp.Array<Il2Cpp.Object>>("GetRootGameObjects")
            if (getRootGameObjects === undefined) return null

            const rootGameObjects: Il2Cpp.Array<Il2Cpp.Object> = getRootGameObjects.invoke()
            const hierarchyNodes: HierarchyNode[] = []
            for (const rootGameObject of rootGameObjects) {
                const hierarchyNode = parseGameObjectToHierarchyNode(rootGameObject)
                hierarchyNodes.push(hierarchyNode)
            }
            return hierarchyNodes
        }),
})
