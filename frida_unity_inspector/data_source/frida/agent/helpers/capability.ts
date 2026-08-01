export interface Capability {
    /** Stable identifier reported to the Python side, e.g. "hierarchy". */
    name: string;
    /** Fresh probe of the target. Return true when the capability is usable. */
    detect(): boolean;
    /** Wire RPC exports for this capability. Called only when detect() returned true. */
    register?(exports: Record<string, unknown>): void;
}

const registry: Capability[] = [];

/** Register a capability. Call at module top level; index.ts imports each module for the side effect. */
export function defineCapability(capability: Capability): void {
    registry.push(capability);
}

export function capabilities(): readonly Capability[] {
    return registry;
}
