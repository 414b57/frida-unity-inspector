/*
 * Watches and rebuilds the agent bundle when source files change.
 * Also regenerates the protocol/model bindings when the Python source of truth (../protocol_spec.py, ../../models.py) changes, so both sides stay in step.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import * as esbuild from "esbuild";

const here = path.dirname(fileURLToPath(import.meta.url));
const generatorPath = path.join(here, "..", "codegen.py");
const specPath = path.join(here, "..", "protocol_spec.py");
const modelsPath = path.join(here, "..", "..", "models.py");
const pythonBin = process.env.PYTHON ?? "python";

const protocolCodegen = {
    name: "protocol-codegen",
    setup(build) {
        build.onStart(() => {
            try {
                execFileSync(pythonBin, [generatorPath], { stdio: "inherit" });
            } catch {
                return { errors: [{ text: "protocol generation failed - see output above" }] };
            }
        });
        // Attach the Python sources to the generated module so edits trigger a rebuild.
        build.onLoad({ filter: /[\\/]helpers[\\/]protocol\.ts$/ }, (args) => ({
            contents: readFileSync(args.path, "utf-8"),
            loader: "ts",
            watchFiles: [specPath, modelsPath],
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
