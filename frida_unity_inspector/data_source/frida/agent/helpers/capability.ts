import { CapabilityName, CapabilitySignatures } from "./protocol";

export interface Capability<N extends CapabilityName = CapabilityName> {
    /** Stable identifier from protocol.json, also the name of the RPC export. */
    name: N;
    /** Returns true if the capability is available in the current target/required functions not stripped. */
    detect(): boolean;
    /**
     * The capability itself. Its signature is pinned by protocol.json, so args and return type stay in step with the Python bindings.
     */
    implementation: CapabilitySignatures[N];
}

type RegisteredCapability = {
    name: CapabilityName;
    detect(): boolean;
    implementation: (...args: any[]) => unknown;
};

const registry: RegisteredCapability[] = [];

export function defineCapability<N extends CapabilityName>(capability: Capability<N>): void {
    registry.push(capability as RegisteredCapability);
}

export function capabilities(): readonly RegisteredCapability[] {
    return registry;
}
