import "frida-il2cpp-bridge"

import { writeComponentProperty } from "../helpers/properties"
import { defineCapability } from "../helpers/capability"
import { Capabilities } from "../helpers/protocol"
import { Property } from "../helpers/models"
import { klass } from "../helpers/resolve"

defineCapability({
    name: Capabilities.SET_PROPERTY_VALUE,

    detect: () => klass("UnityEngine.CoreModule", "UnityEngine.GameObject") !== null,

    implementation: (component_handle_ptr: string, property: Property) =>
        Il2Cpp.perform(() => {
            return writeComponentProperty(component_handle_ptr, property);
        }),
})
