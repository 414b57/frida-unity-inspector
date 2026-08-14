import "frida-il2cpp-bridge"

function perform() {
    Il2Cpp.$config.unityVersion = "6000.0.63f1"

    console.log("perform started")
    function executeHandle() {
        recv("execute", (message) => {
            console.log(JSON.stringify(message))
            const code = message.code;
            console.log("[+] Received input code to execute:\n" + code);
            try {
                Il2Cpp.perform(() => {
                    console.log("perform started for code execution")
                    const result = (0, eval)(code);
                    let repr;
                    try {
                        repr = result === undefined ? "undefined" : String(result);
                    } catch (e) {
                        repr = "coukld not convert result to string: " + e.message;
                    }
                    send({type: "event", event: "code_executed", result: repr});
                })
            } catch (error) {
                send({ type: "event", event: "code_execution_error", error: error.stack || error.message });
            } finally {
                executeHandle(); // Wait for the next message
            }
        })
    }
    executeHandle();
}

setTimeout(() => {
    perform();
    send({ type: "event", event: "agent_ready" });
}, 0);

send({ type: "event", event: "agent_loaded" });