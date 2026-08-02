/* AUTO-GENERATED from ../../protocol.json - do not edit by hand. */


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
} as const
export type CapabilityName = (typeof Capabilities)[keyof typeof Capabilities]

/** Payload shape each event carries. */
export interface EventPayloads {
    "agent_loaded": null
    "agent_ready": Record<string, boolean>
}

/** Signature each capability's implementation must have. */
export interface CapabilitySignatures {
    "getCurrentRenderPipeline": () => string | null | Promise<string | null>
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
