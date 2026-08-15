/*
 * dump_scene.ts
 *
 * Dumps a single loaded scene as an indented tree of GameObjects, printing each
 * object's components and then recursing into its children.
 *
 * Usage (from input_code_runner):
 *     r stubs/dump_scene.ts <sceneIndex>
 *
 * The scene index is read from SCRIPT_ARGS[0] (injected by the agent). Defaults to 0.
 * Runs inside Il2Cpp.perform(), so the Il2Cpp API is available with no imports.
 */

const args: string[] = (globalThis as any).SCRIPT_ARGS ?? []
const sceneIndex = args.length > 0 ? parseInt(args[0], 10) : 0

function indent(depth: number): string {
    return "  ".repeat(depth)
}

function componentTypeName(component: Il2Cpp.Object): string {
    const k = component.class
    return `${k.namespace ? k.namespace + "." : ""}${k.name}`
}

// Cache the Component class once; used to inflate the generic GetComponents<T>().
const componentClass = Il2Cpp.domain
    .tryAssembly("UnityEngine.CoreModule")
    ?.image.tryClass("UnityEngine.Component")

function dumpGameObject(gameObject: Il2Cpp.Object, depth: number): void {
    const name = gameObject.tryMethod<Il2Cpp.String>("get_name")?.invoke()?.toString() ?? "<unnamed>"
    const active = gameObject.tryMethod<boolean>("get_activeSelf")?.invoke() ?? false
    const tag = gameObject.tryMethod<Il2Cpp.String>("get_tag")?.invoke()?.toString() ?? "Untagged"
    const layer = gameObject.tryMethod<number>("get_layer")?.invoke() ?? -1

    console.log(`${indent(depth)}● ${name}  (active=${active}, tag=${tag}, layer=${layer})`)

    // Components: generic GetComponents<Component>() -> array of every component on the object.
    const getComponents = gameObject.tryMethod<Il2Cpp.Array<Il2Cpp.Object>>("GetComponents", 0)
    if (componentClass && getComponents) {
        const comps = getComponents.inflate(componentClass).invoke()
        if (comps) {
            for (const c of comps) {
                console.log(`${indent(depth)}  · ${componentTypeName(c)}`)
            }
        }
    }

    // Children via the transform hierarchy.
    const transform = gameObject.tryMethod<Il2Cpp.Object>("get_transform")?.invoke() ?? null
    if (transform) {
        const childCount = transform.tryMethod<number>("get_childCount")?.invoke() ?? 0
        for (let i = 0; i < childCount; i++) {
            const childTransform = transform.tryMethod<Il2Cpp.Object>("GetChild", 1)?.invoke(i) ?? null
            if (!childTransform) continue
            const childGO = childTransform.tryMethod<Il2Cpp.Object>("get_gameObject")?.invoke() ?? null
            if (!childGO) continue
            dumpGameObject(childGO, depth + 1)
        }
    }
}

const sceneManager = Il2Cpp.domain
    .tryAssembly("UnityEngine.CoreModule")
    ?.image.tryClass("UnityEngine.SceneManagement.SceneManager")

if (!sceneManager) {
    console.error("[dump_scene] SceneManager class not found")
} else if (Number.isNaN(sceneIndex)) {
    console.error(`[dump_scene] invalid scene index: ${JSON.stringify(args[0])}`)
} else {
    const sceneCount = sceneManager.tryMethod<number>("get_sceneCount")?.invoke() ?? 0
    const getSceneAt = sceneManager.tryMethod<Il2Cpp.ValueType>("GetSceneAt")

    if (!getSceneAt) {
        console.error("[dump_scene] SceneManager.GetSceneAt not found")
    } else if (sceneIndex < 0 || sceneIndex >= sceneCount) {
        console.error(`[dump_scene] scene index ${sceneIndex} out of range (0..${sceneCount - 1})`)
    } else {
        const scene = getSceneAt.invoke(sceneIndex)
        const name = scene.tryMethod<Il2Cpp.String>("get_name")?.invoke()?.toString() ?? "<unknown>"
        const isLoaded = scene.tryMethod<boolean>("get_isLoaded")?.invoke() ?? false
        const rootCount = scene.tryMethod<number>("get_rootCount")?.invoke() ?? 0

        console.log(`[Scene ${sceneIndex}] "${name}"  (isLoaded=${isLoaded}, rootCount=${rootCount})`)

        const getRoots = scene.tryMethod<Il2Cpp.Array<Il2Cpp.Object>>("GetRootGameObjects")
        if (!getRoots) {
            console.error("[dump_scene] Scene.GetRootGameObjects not found")
        } else {
            for (const root of getRoots.invoke()) {
                dumpGameObject(root, 0)
            }
        }
        console.log(`[dump_scene] done dumping scene ${sceneIndex} "${name}"`)
    }
}
