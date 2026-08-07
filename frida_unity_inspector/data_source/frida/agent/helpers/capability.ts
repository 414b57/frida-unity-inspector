import { CapabilityName, CapabilityRequires, CapabilitySignatures } from "./protocol";

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
const registered = new Map<CapabilityName, RegisteredCapability>();

export function defineCapability<N extends CapabilityName>(capability: Capability<N>): void {
    registry.push(capability as RegisteredCapability);
    registered.set(capability.name, capability as RegisteredCapability);
}

export function capabilities(): readonly RegisteredCapability[] {
    return registry;
}

export function getCapability<N extends CapabilityName>(name: N): CapabilitySignatures[N] {
    const capability = registered.get(name);
    if (capability === undefined) {
        throw new Error(`capability '${name}' is not registered - is its module imported in index.ts?`);
    }
    return capability.implementation as CapabilitySignatures[N];
}

function isAvailable(name: CapabilityName, resolved: Map<CapabilityName, boolean>): boolean {
    const cached = resolved.get(name);
    if (cached !== undefined) return cached;
    resolved.set(name, false);

    // Fail fast if any required capability is unavailable. Should hopefully speed up detection by skipping detect calls for capabilities that are known to be unavailable.
    for (const required of CapabilityRequires[name] ?? []) {
        if (isAvailable(required, resolved)) continue;
        console.warn(`[!] capability '${name}' unavailable - requires '${required}'`);
        return false;
    }

    const capability = registered.get(name);
    const result = capability !== undefined && capability.detect();
    resolved.set(name, result);
    return result;
}

export function resolveAvailability(): Record<CapabilityName, boolean> {
    const resolved = new Map<CapabilityName, boolean>();
    const snapshot = {} as Record<CapabilityName, boolean>;
    for (const name of Object.keys(CapabilityRequires) as CapabilityName[]) snapshot[name] = isAvailable(name, resolved);
    return snapshot;
}
