/*
 * Helper script to watch and rebuild the agent bundle when any code files/associated files change. (protocol.json)
 * Mainly implemented, so protocol.json changes trigger a rebuild of the agent bundle.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import * as esbuild from "esbuild";

const here = path.dirname(fileURLToPath(import.meta.url));
const generatorPath = path.join(here, "generate_protocol.mjs");
const protocolPath = path.join(here, "..", "protocol.json");

const protocolCodegen = {
    name: "protocol-codegen",
    setup(build) {
        build.onStart(() => {
            try {
                execFileSync(process.execPath, [generatorPath], { stdio: "inherit" });
            } catch {
                return { errors: [{ text: "protocol generation failed - see output above" }] };
            }
        });
        // Attach protocol.json to the generated module so the watcher rebuilds when it changes.
        build.onLoad({ filter: /[\\/]helpers[\\/]protocol\.ts$/ }, (args) => ({
            contents: readFileSync(args.path, "utf-8"),
            loader: "ts",
            watchFiles: [protocolPath],
        }));
    },
};

const context = await esbuild.context({
    entryPoints: [path.join(here, "index.ts")],
    bundle: true,
    outfile: path.join(here, "_agent.js"),
    format: "iife",
    platform: "neutral",
    logLevel: "info",
    plugins: [protocolCodegen],
});

await context.watch();
