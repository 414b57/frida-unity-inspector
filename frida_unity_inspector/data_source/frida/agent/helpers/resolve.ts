import "frida-il2cpp-bridge"

export function assembly(name: string): Il2Cpp.Assembly | null {
    return Il2Cpp.domain.tryAssembly(name);
}

export function klass(assemblyName: string, fullyQualifiedName: string): Il2Cpp.Class | null {
    return assembly(assemblyName)?.image.tryClass(fullyQualifiedName) ?? null;
}

export function method<T extends Il2Cpp.Method.ReturnType = Il2Cpp.Method.ReturnType>(
    assemblyName: string,
    fullyQualifiedName: string,
    methodName: string,
    parameterCount?: number,
): Il2Cpp.Method<T> | null {
    return klass(assemblyName, fullyQualifiedName)?.tryMethod<T>(methodName, parameterCount) ?? null;
}
