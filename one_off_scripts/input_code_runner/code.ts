console.log("running")
const sceneManager = Il2Cpp.domain.tryAssembly("UnityEngine.CoreModule")?.image.tryClass("UnityEngine.SceneManagement.SceneManager")

if (sceneManager) {
    console.log("[+] SceneManager class found:", sceneManager.name)
    // get_sceneCount
    const sceneCount = sceneManager.tryMethod<number>("get_sceneCount")
    let totalSceneCount = 0
    if (sceneCount) {
        console.log("[+] SceneManager.get_sceneCount method found:", sceneCount.name)
        totalSceneCount = sceneCount.invoke()
        console.log("[+] SceneManager.get_sceneCount result:", totalSceneCount)
    } else {
        console.warn("[!] SceneManager.get_sceneCount method NOT found")
    }

    // GetSceneAt
    const getSceneAt = sceneManager.tryMethod<Il2Cpp.ValueType>("GetSceneAt")
    if (getSceneAt) {
        console.log("[+] SceneManager.GetSceneAt method found:", getSceneAt.name)
        for (let i = 0; i < totalSceneCount; i++) {
            const scene = getSceneAt.invoke(i)
            console.log(`[+] SceneManager.GetSceneAt(${i}) result:`, scene)
            // get_handle
            const handleMethod = scene.tryMethod<number>("get_handle")
            if (handleMethod) {
                const handle = handleMethod.invoke()
                console.log(`[+] SceneManager.GetSceneAt(${i}).get_handle() result:`, handle)
            }
            // get_path
            const pathMethod = scene.tryMethod<Il2Cpp.String>("get_path")
            if (pathMethod) {
                const path = pathMethod.invoke()
                console.log(`[+] SceneManager.GetSceneAt(${i}).get_path() result:`, path)
            }
            // get_name
            const nameMethod = scene.tryMethod<Il2Cpp.String>("get_name")
            if (nameMethod) {
                const name = nameMethod.invoke()
                console.log(`[+] SceneManager.GetSceneAt(${i}).get_name() result:`, name)
            }
            // get_isLoaded
            const isLoadedMethod = scene.tryMethod<boolean>("get_isLoaded")
            if (isLoadedMethod) {
                const isLoaded = isLoadedMethod.invoke()
                console.log(`[+] SceneManager.GetSceneAt(${i}).get_isLoaded() result:`, isLoaded)
            }
            // get_buildIndex
            const buildIndexMethod = scene.tryMethod<number>("get_buildIndex")
            if (buildIndexMethod) {
                const buildIndex = buildIndexMethod.invoke()
                console.log(`[+] SceneManager.GetSceneAt(${i}).get_buildIndex() result:`, buildIndex)
            }
            // get_rootCount
            const rootCountMethod = scene.tryMethod<number>("get_rootCount")
            if (rootCountMethod) {
                const rootCount = rootCountMethod.invoke()
                console.log(`[+] SceneManager.GetSceneAt(${i}).get_rootCount() result:`, rootCount)
            }
            // getRootGameObjects
            const getRootGameObjectsMethod = scene.tryMethod<Il2Cpp.Array<Il2Cpp.Object>>("GetRootGameObjects")
            if (getRootGameObjectsMethod) {
                const rootGameObjects: Il2Cpp.Array<Il2Cpp.Object>  = getRootGameObjectsMethod.invoke()
                console.log(`[+] SceneManager.GetSceneAt(${i}).GetRootGameObjects() result:`, rootGameObjects)
                let j = -1
                for (const rootGameObject of rootGameObjects) {
                    j++;
                    console.log(`[+] SceneManager.GetSceneAt(${i}).GetRootGameObjects()[${j}] result:`, rootGameObject)
                    // get_name of rootGameObject
                    const rootGameObjectNameMethod = rootGameObject.tryMethod<Il2Cpp.String>("get_name")
                    if (rootGameObjectNameMethod) {
                        const rootGameObjectName = rootGameObjectNameMethod.invoke()
                        console.log(`[+] SceneManager.GetSceneAt(${i}).GetRootGameObjects()[${j}].get_name() result:`, rootGameObjectName)
                    }
                }
            }
        }
    } else {
        console.warn("[!] SceneManager.GetSceneAt method NOT found")
    }

}