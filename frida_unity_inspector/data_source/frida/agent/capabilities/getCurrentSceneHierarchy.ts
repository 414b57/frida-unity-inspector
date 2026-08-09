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
    const components: Component[] = [] // TODO: Implement component parsing

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

                const componentProperties: Property[] = [] // TODO - Below has basic field reading, look into custom handlers for stuff. i.e. transform doesnt have fields but still has `get_position`/`get_localEulerAngles`/`get_localScale` etc. so can custom parse it
                for (const field of componentClass.fields) {
                    const fieldStatic = field.isStatic
                    if (fieldStatic) {
                        continue // TODO - Implement support for static. rn does `04:36:43.983  WARNING   fui.utils.frida_injector   [agent] Failed to read field kMinAperture of component "Main Camera" (Camera): Il2CppError: couldn't find non-static field kMinAperture in hierarchy of class UnityEngine.Camera`
                    }
                    const fieldName = field.name
                    const fieldType = field.type.name

                    try {
                        const raw = component.field(field.name).value
                        switch (fieldType) {
                            case "System.Single":
                            case "System.Double": {
                                const value = toNumber(raw)
                                componentProperties.push({ label: fieldName, kind: "float", is_static: fieldStatic, read_only: false, value: value ?? 0 })
                                break
                            }
                            case "System.Int32":
                            case "System.Int64":
                            case "System.UInt32":
                            case "System.UInt64":
                            case "System.Int16":
                            case "System.UInt16":
                            case "System.Byte":
                            case "System.SByte": {
                                const value = toNumber(raw)
                                componentProperties.push({ label: fieldName, kind: "int", is_static: fieldStatic, read_only: false, value: value ?? 0 })
                                break
                            }
                            case "System.Boolean":
                                componentProperties.push({ label: fieldName, kind: "bool", is_static: fieldStatic, read_only: false, value: Boolean(raw) })
                                break
                            case "System.String":
                                componentProperties.push({ label: fieldName, kind: "string", is_static: fieldStatic, read_only: false, value: (raw as Il2Cpp.String).toString() })
                                break
                            case "UnityEngine.Vector3":
                                const rawVT: Il2Cpp.ValueType = raw as Il2Cpp.ValueType
                                const value: Vector3 = {
                                    x: rawVT.field<number>("x").value,
                                    y: rawVT.field<number>("y").value,
                                    z: rawVT.field<number>("z").value
                                }
                                componentProperties.push({ label: fieldName, kind: "vector3", is_static: fieldStatic, read_only: false, value: value })
                                break
                            default: {
                                // console.log(`Skipping field ${fieldName} of component ${componentName} (${componentType}) with unsupported type ${fieldType}`)
                            }
                        }
                    } catch (e) {
                        console.warn(`Failed to read field ${fieldName} of component ${componentName} (${componentType}): ${e}`)
                        continue
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
        }
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
