// `npm test` - the pure half of the panel, run under `node --test`.
//
// **Why a runner at all.** The sources are TypeScript with extensionless imports, which is
// what the bundler wants and what Node's own loader refuses; and the plan rules out a
// browser-driven suite (SPEC §9.2), so there is no Playwright to hide the compilation
// inside. The cheapest honest thing is the build the panel already has: esbuild compiles
// each test to one ES module in a temporary directory, and `node --test` runs those. No
// new runtime dependency, no test framework, no configuration file - `node:test` and
// `node:assert` are in Node.
//
// **What is tested is what has no DOM in it**: the pending model, the sentences, the
// router, the Markdown renderer, the illustration check and the options-flow opener. The
// views are Lit elements and are walked in the development harness by a person, as they
// have been since lot 5; that boundary is the handoff's open point, not an oversight.

import { spawn } from "node:child_process";
import { mkdtemp, readdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { build } from "esbuild";

const here = dirname(fileURLToPath(import.meta.url));

const entryPoints = (await readdir(here))
  .filter((name) => name.endsWith(".test.ts"))
  .sort()
  .map((name) => join(here, name));

if (entryPoints.length === 0) {
  console.error("no tests found in", here);
  process.exit(1);
}

const outdir = await mkdtemp(join(tmpdir(), "myhome-panel-test-"));

await build({
  entryPoints,
  outdir,
  bundle: true,
  format: "esm",
  platform: "node",
  target: "node22",
  // Bundled, so the sources may go on importing each other the way the panel does. Node's
  // own modules stay external: a test that spied on `node:assert` would be a test of the
  // bundler.
  packages: undefined,
  external: ["node:*"],
  outExtension: { ".js": ".mjs" },
  sourcemap: "inline",
  logLevel: "warning",
});

const compiled = (await readdir(outdir))
  .filter((name) => name.endsWith(".mjs"))
  .sort()
  .map((name) => join(outdir, name));

const child = spawn(process.execPath, ["--test", ...compiled], { stdio: "inherit" });
child.on("exit", async (code) => {
  await rm(outdir, { recursive: true, force: true });
  process.exit(code ?? 1);
});
