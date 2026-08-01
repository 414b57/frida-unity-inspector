import "frida-il2cpp-bridge"

function perform() {
    Il2Cpp.perform(() => {
        console.log("[+] IL2CPP attached");

        rpc.exports.test = (arg) => {
            console.log("[+] Test called with arg:", arg);
            return "Hello from Frida!";
        }
    });
}

setTimeout(() => {
    perform();
    send({ type: "event", event: "agent_ready" });
}, 3000);

send({ type: "event", event: "agent_loaded" });