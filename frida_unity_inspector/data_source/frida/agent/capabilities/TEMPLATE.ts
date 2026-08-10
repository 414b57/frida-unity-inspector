// import "frida-il2cpp-bridge"
//
// import { defineCapability } from "../helpers/capability"
// import { Capabilities } from "../helpers/protocol"
// import {assembly, klass, method} from "../helpers/resolve"

// // -- TEMPLATE FILE --
// /*
//   * USAGE:
//   * 0. Ctrl + A this file, then press ctrl + / to uncomment all lines. Then follow below
//   * 1. In `protocol_spec.py`, define a new capability;
//   * Call(
//         "TEMPLATE_CAPABILITY_KEY_NAME",
//         "rpcExportedFunctionName",
//         bool, # return type
//         args=(Arg("arg1", str), Arg("arg2", int)) # arguments
//         # OPTIONAL:
//         # requires=("GET_SCENE_MANAGER") # capabilities that this capability depends on
//     )
//   * 2. In this file, implement the capability using `defineCapability`.
//   *    2.1  - Make sure name matches the capability key name defined in `protocol_spec.py`.
//   *    2.2  - Implement the `detect` function to check if the capability is available in the current Unity version. In here put logic that is required to run i.e. method calls. So if a method is not available in the current Unity version, return false.
//   *    2.3  - Implement the `implementation` function to define what the capability does. This function will be called when the capability is invoked from the Python side.
//   *             You can use `Il2Cpp.perform` to run code in the Unity context. The arguments passed to this function will be the same as defined in the `protocol_spec.py` file.
//   *             The return value of this function will be sent back to the Python side as the result of the capability call.
//   * 3. In index.ts, import this file to register the capability.
//   * 4. In the Python side, you can now call this capability, 2 possible ways to do so.
//   *     2.1  - Using `self.session.call_capability(Capabilities.TEMPLATE_CAPABILITY_KEY_NAME, arg1="some_string", arg2=42)`
//   *             This has a limitation of the return not being typed to the expected return type, so you will need to cast it to the expected type.
//   *     2.2  - First checking if can call by doing `self.session.has_capability(Capabilities.TEMPLATE_CAPABILITY_KEY_NAME)`, true = can call | false = cant call.
//   *             If true then do `self.session.rpc.rpcExportedFunctionName(arg1="some_string", arg2=42)` which will return the expected type.
//   * 5. Profit?
//  */

// defineCapability({
//     name: Capabilities.TEMPLATE_CAPABILITY_KEY_NAME,
//
//     detect: () => {
//         return (
//             assembly("UnityEngine.CoreModule") !== null &&
//             klass("UnityEngine.CoreModule", "UnityEngine.Component") !== null &&
//             method("UnityEngine.CoreModule", "UnityEngine.Component", "get_transform") !== null
//         )
//     },
//
//     implementation: (arg1: string, arg2: number) =>
//         Il2Cpp.perform(() => {
//             // Put code here that will be executed when the capability is called.
//             return "Return Value"
//         }),
// })
