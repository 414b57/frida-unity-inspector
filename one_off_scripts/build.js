const esbuild = require("esbuild");
const path = require("path");

const dir = process.env.INIT_CWD || process.cwd();
const watch = process.argv.includes("--watch");

const options = {
    entryPoints: [path.join(dir, "index.ts")],
    outfile: path.join(dir, "_agent.js"),
    bundle: true,
    format: "iife",
    platform: "neutral",
    logLevel: "warning",
};

if (watch) {
    esbuild.context(options).then((ctx) => {
        ctx.watch();
        console.log(`watching ${path.join(dir, "index.ts")}`);
    }).catch(() => process.exit(1));
} else {
    esbuild.build(options).catch(() => process.exit(1));
}