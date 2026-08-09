import "frida-il2cpp-bridge"

import { defineCapability } from "../helpers/capability"
import type { Property } from "../helpers/models"
import { getKnownComponent, parseComponentProperties } from "../helpers/properties"
import { Capabilities } from "../helpers/protocol"
import { klass } from "../helpers/resolve"

/*
 * Heavy data gathering of component properties. This is a batch operation that takes a list of component ids and returns a map of component id to its properties.
 * Each component's properties are represented as an array of Property objects, which contain the name, type, and value of the property.
 * If a component id is unknown or stale (i.e., the component has been destroyed or is no longer valid), the corresponding value in the map will be null.
 */

defineCapability({
    name: Capabilities.GET_COMPONENT_PROPERTIES,

    detect: () => {
        return klass("UnityEngine.CoreModule", "UnityEngine.Component") !== null
    },

    implementation: (componentIds: string[]) =>
        Il2Cpp.perform(() => {
            const result: Record<string, Property[] | null> = {}
            for (const componentId of componentIds) {
                const component = getKnownComponent(componentId)
                if (component === null) {
                    result[componentId] = null
                    continue
                }
                try {
                    // Use helper functions to parse - handles all of type wrangling/custom handlers/etc.
                    result[componentId] = parseComponentProperties(component)
                } catch (e) {
                    console.warn(`Failed to read properties of component ${componentId}: ${e}`)
                    result[componentId] = null
                }
            }
            return result
        }),
})
