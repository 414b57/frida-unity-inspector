console.log("Hello from Frida script!");
rpc.exports = {
    hello: function() {
        return "Hello";
    },
    copy: function(msg) {
        return "I am copying your message: " + msg;
    }
};

send({ type: "agent_ready", agent: "default" });

setInterval(() => {
    send({ type: "ping" });
}, 1000);