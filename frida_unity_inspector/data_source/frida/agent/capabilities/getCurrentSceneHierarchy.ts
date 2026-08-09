import "frida-il2cpp-bridge"

import { defineCapability, getCapability } from "../helpers/capability"
import type { Component, GameObjectData, HierarchyNode, IconName } from "../helpers/models"
import { Capabilities } from "../helpers/protocol"
import { method } from "../helpers/resolve"

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

    // Recursively get and parse children
    const children: HierarchyNode[] = []
    if (transform) {
        const childCount = transform.tryMethod<number>("get_childCount")?.invoke() ?? 0
        for (let i = 0; i < childCount; i++) {
            const childTransform = transform.tryMethod<Il2Cpp.Object>("GetChild", 1)?.invoke(i) ?? null
            if (childTransform) {
                const childGameObject = childTransform.tryMethod<Il2Cpp.Object>("get_gameObject")?.invoke() ?? null
                if (childGameObject) {
                    const childNode = parseGameObjectToHierarchyNode(childGameObject)
                    children.push(childNode)
                }
            }
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
