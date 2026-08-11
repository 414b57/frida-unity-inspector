/* AUTO-GENERATED from ../../protocol_spec.py + ../../../models.py - do not edit by hand. */
import type { HierarchyNode, Property } from "./models"

export const MessageTypes = {
    EVENT: "event",
} as const
export type MessageType = (typeof MessageTypes)[keyof typeof MessageTypes]

export const Events = {
    AGENT_LOADED: "agent_loaded",
    AGENT_READY: "agent_ready",
} as const
export type EventName = (typeof Events)[keyof typeof Events]

export const Builtins = {
    CAPABILITIES: "capabilities",
    VERSION: "version",
    UNITY_VERSION: "unityVersion",
    PING: "ping",
} as const
export type BuiltinName = (typeof Builtins)[keyof typeof Builtins]

export const Capabilities = {
    GET_CURRENT_RENDER_PIPELINE: "getCurrentRenderPipeline",
    GET_SCENE_MANAGER: "getSceneManager",
    GET_CURRENT_SCENE: "getCurrentScene",
    GET_HIERARCHY_STRUCTURE: "getHierarchyStructure",
    GET_COMPONENT_PROPERTIES: "getComponentProperties",
    SET_GAMEOBJECT_ACTIVE: "setGameObjectActive",
    SET_COMPONENT_ENABLED: "setComponentEnabled",
    SET_PROPERTY_VALUE: "setPropertyValue",
} as const
export type CapabilityName = (typeof Capabilities)[keyof typeof Capabilities]

/** Capabilities each capability depends on */
export const CapabilityRequires: Record<CapabilityName, readonly CapabilityName[]> = {
    "getCurrentRenderPipeline": [],
    "getSceneManager": [],
    "getCurrentScene": ["getSceneManager"],
    "getHierarchyStructure": ["getCurrentScene"],
    "getComponentProperties": ["getHierarchyStructure"],
    "setGameObjectActive": [],
    "setComponentEnabled": [],
    "setPropertyValue": [],
}

/** Payload shape each event carries. */
export interface EventPayloads {
    "agent_loaded": null
    "agent_ready": Record<string, boolean>
}

/** Signature each capability's implementation must have. */
export interface CapabilitySignatures {
    "getCurrentRenderPipeline": () => string | null | Promise<string | null>
    "getSceneManager": () => any | Promise<any>
    "getCurrentScene": () => any | Promise<any>
    "getHierarchyStructure": () => HierarchyNode[] | null | Promise<HierarchyNode[] | null>
    "getComponentProperties": (component_ids: string[]) => Record<string, Property[] | null> | Promise<Record<string, Property[] | null>>
    "setGameObjectActive": (gameobject_handle_ptr: string, active: boolean) => boolean | Promise<boolean>
    "setComponentEnabled": (component_handle_ptr: string, active: boolean) => boolean | Promise<boolean>
    "setPropertyValue": (component_handle_ptr: string, property: Property) => Property | Promise<Property>
}

export interface BuiltinSignatures {
    "capabilities": () => Record<string, boolean> | Promise<Record<string, boolean>>
    "version": () => string | Promise<string>
    "unityVersion": () => string | Promise<string>
    "ping": (unix_epoch_seconds: number) => [number, number] | Promise<[number, number]>
}

/** Helper for sending an event to the Python side with a payload matching the protocol. */
export function sendEvent<E extends EventName>(event: E, data: EventPayloads[E]): void {
    send({ type: MessageTypes.EVENT, event, data })
}
