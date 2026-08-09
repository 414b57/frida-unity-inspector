import "frida-il2cpp-bridge"

import { defineCapability, getCapability } from "../helpers/capability"
import type { Component, HierarchyNode, IconName } from "../helpers/models"
import { pruneComponents, rememberComponent } from "../helpers/properties"
import { Capabilities } from "../helpers/protocol"
import { klass, method } from "../helpers/resolve"

/*
 * Lightweight walk of the hierarchy, returning a tree of HierarchyNode objects.
 * Each node contains the GameObject's name, icon, and a list of its components as specified by the models.
 * However the properties field of each component is left empty, as this function does not fetch property values.
 * The properties can be fetched later in batches using the getComponentProperties capability.
 */

function parseComponentsOfGameObject(gameObject: Il2Cpp.Object, name: string, seenComponentIds: Set<string>): Component[] {
    const componentClass = klass("UnityEngine.CoreModule", "UnityEngine.Component")

    const behaviourClass = klass("UnityEngine.CoreModule", "UnityEngine.Behaviour")
    const colliderClass = klass("UnityEngine.PhysicsModule", "UnityEngine.Collider")
    const rendererClass = klass("UnityEngine.CoreModule", "UnityEngine.Renderer")

    const components: Component[] = []

    const getComponentsMethod = gameObject.tryMethod<Il2Cpp.Array<Il2Cpp.Object>>("GetComponents", 0)
    if (!(componentClass && getComponentsMethod)) {
        console.warn(`GameObject ${name} has no GetComponents method or Component class, cannot get components.`)
        return components
    }
    const componentArray = getComponentsMethod.inflate(componentClass).invoke()
    if (!componentArray) {
        console.warn(`GameObject ${name} states has componenets, but getcomponents returned null. This is unexpected.`)
        return components
    }

    for (const component of componentArray) {
        const componentKlass = component.class
        const componentId = component.handle.toString()
        const componentType = `${componentKlass.namespace ? componentKlass.namespace + "." : ""}${componentKlass.name}`
        const componentIcon: IconName = "unknown" // TODO: Determine icon for the component

        // determine if can change enabled state - unityengine.Behaviour + unityengine.Collider + unityenginer.Renderer
        let enabled: boolean | null = null // Null = cant change, true/false can change/current state
        if (behaviourClass && componentKlass.isSubclassOf(behaviourClass, true)) {
            enabled = component.tryMethod<boolean>("get_enabled")?.invoke() ?? null
        } else if (colliderClass && componentKlass.isSubclassOf(colliderClass, true)) {
            enabled = component.tryMethod<boolean>("get_enabled")?.invoke() ?? null
        } else if (rendererClass && componentKlass.isSubclassOf(rendererClass, true)) {
            // TODO - Look into this. Can be turnt on/off. But in `Renderer` it has no `get_enabled` only `set_enabled`?
            enabled = component.tryMethod<boolean>("get_enabled")?.invoke() ?? null
        }

        rememberComponent(componentId, component)
        seenComponentIds.add(componentId)

        components.push({
            id: componentId,
            name: componentKlass.name,
            type: componentType,
            icon: componentIcon,

            enabled: enabled,
            expanded: true, // No way to determine if expanded or not, so default to true
            properties: [], // Filled in by getComponentProperties, not here.
        })
    }

    return components
}

function parseGameObjectToStructureNode(gameObject: Il2Cpp.Object, seenComponentIds: Set<string>): HierarchyNode {
    // Hierarchy Node
    const id = gameObject.handle.toString()
    const name = gameObject.tryMethod<Il2Cpp.String>("get_name")?.invoke().toString() ?? "Unknown-GameObject"
    const icon: IconName = "unknown" // TODO: Determine, either here, or in python side. idk yet.

    // Data for the GameObject
    const active = gameObject.tryMethod<boolean>("get_activeSelf")?.invoke() ?? false
    const tag = gameObject.tryMethod<Il2Cpp.String>("get_tag")?.invoke().toString() ?? "Unknown-Tag"
    const layer = gameObject.tryMethod<number>("get_layer")?.invoke() ?? -1
    const transform = gameObject.tryMethod<Il2Cpp.Object>("get_transform")?.invoke() ?? null

    const components = parseComponentsOfGameObject(gameObject, name, seenComponentIds)

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

            children.push(parseGameObjectToStructureNode(childGameObject, seenComponentIds))
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
    name: Capabilities.GET_HIERARCHY_STRUCTURE,

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
            const seenComponentIds = new Set<string>()
            const structure: HierarchyNode[] = []
            for (const rootGameObject of rootGameObjects) {
                structure.push(parseGameObjectToStructureNode(rootGameObject, seenComponentIds))
            }
            pruneComponents(seenComponentIds)
            return structure
        }),
})
