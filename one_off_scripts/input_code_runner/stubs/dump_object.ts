/*
 * dump_object.ts
 *
 * Finds a GameObject by name across all loaded scenes (including inactive ones) and
 * dumps it in the exact same tree format as dump_scene.ts - object, its components,
 * and its child hierarchy - but rooted at that single object instead of a whole scene.
 *
 * Usage (from input_code_runner):
 *     r stubs/dump_object.ts <gameObjectName>
 *
 * The name is read from SCRIPT_ARGS (joined with spaces, so multi-word names work).
 * If several objects share the name, every match is dumped. Runs inside Il2Cpp.perform().
 */

const args: string[] = (globalThis as any).SCRIPT_ARGS ?? []
const targetName = args.join(" ").trim()

function indent(depth: number): string {
    return "  ".repeat(depth)
}

function componentTypeName(component: Il2Cpp.Object): string {
    const k = component.class
    return `${k.namespace ? k.namespace + "." : ""}${k.name}`
}

const componentClass = Il2Cpp.domain
    .tryAssembly("UnityEngine.CoreModule")
    ?.image.tryClass("UnityEngine.Component")

function gameObjectName(gameObject: Il2Cpp.Object): string {
    return gameObject.tryMethod<Il2Cpp.String>("get_name")?.invoke()?.toString() ?? "<unnamed>"
}

// Identical renderer to dump_scene.ts so the output format matches exactly.
function dumpGameObject(gameObject: Il2Cpp.Object, depth: number): void {
    const name = gameObjectName(gameObject)
    const active = gameObject.tryMethod<boolean>("get_activeSelf")?.invoke() ?? false
    const tag = gameObject.tryMethod<Il2Cpp.String>("get_tag")?.invoke()?.toString() ?? "Untagged"
    const layer = gameObject.tryMethod<number>("get_layer")?.invoke() ?? -1

    console.log(`${indent(depth)}● ${name}  (active=${active}, tag=${tag}, layer=${layer})`)

    const getComponents = gameObject.tryMethod<Il2Cpp.Array<Il2Cpp.Object>>("GetComponents", 0)
    if (componentClass && getComponents) {
        const comps = getComponents.inflate(componentClass).invoke()
        if (comps) {
            for (const c of comps) {
                console.log(`${indent(depth)}  · ${componentTypeName(c)}`)
            }
        }
    }

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

// Walk one object's subtree collecting every GameObject whose name matches.
function collectMatches(gameObject: Il2Cpp.Object, name: string, out: Il2Cpp.Object[]): void {
    if (gameObjectName(gameObject) === name) out.push(gameObject)

    const transform = gameObject.tryMethod<Il2Cpp.Object>("get_transform")?.invoke() ?? null
    if (!transform) return
    const childCount = transform.tryMethod<number>("get_childCount")?.invoke() ?? 0
    for (let i = 0; i < childCount; i++) {
        const childTransform = transform.tryMethod<Il2Cpp.Object>("GetChild", 1)?.invoke(i) ?? null
        if (!childTransform) continue
        const childGO = childTransform.tryMethod<Il2Cpp.Object>("get_gameObject")?.invoke() ?? null
        if (!childGO) continue
        collectMatches(childGO, name, out)
    }
}

if (!targetName) {
    console.error("[dump_object] no object name given. Usage: r stubs/dump_object.ts <name>")
} else {
    const sceneManager = Il2Cpp.domain
        .tryAssembly("UnityEngine.CoreModule")
        ?.image.tryClass("UnityEngine.SceneManagement.SceneManager")

    if (!sceneManager) {
        console.error("[dump_object] SceneManager class not found")
    } else {
        const sceneCount = sceneManager.tryMethod<number>("get_sceneCount")?.invoke() ?? 0
        const getSceneAt = sceneManager.tryMethod<Il2Cpp.ValueType>("GetSceneAt")

        const matches: Il2Cpp.Object[] = []
        if (getSceneAt) {
            for (let s = 0; s < sceneCount; s++) {
                const scene = getSceneAt.invoke(s)
                const getRoots = scene.tryMethod<Il2Cpp.Array<Il2Cpp.Object>>("GetRootGameObjects")
                if (!getRoots) continue
                for (const root of getRoots.invoke()) {
                    collectMatches(root, targetName, matches)
                }
            }
        }

        if (matches.length === 0) {
            console.error(`[dump_object] no GameObject named "${targetName}" found in any loaded scene`)
        } else {
            console.log(`[dump_object] found ${matches.length} GameObject(s) named "${targetName}"`)
            matches.forEach((go, i) => {
                console.log(`[dump_object] match ${i}:`)
                dumpGameObject(go, 0)
            })
        }
    }
}
