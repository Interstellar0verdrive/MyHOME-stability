// Build the panel: one ES module, minified, into the directory the integration ships.
//
// One command and one dependency on purpose. The maintainer of this repository is not
// a professional front-end developer, and a build that needs a dev server, a plugin
// chain and a watch mode is a build that stops being run. `node build.mjs` is the whole
// of it, and `.github/workflows/panel.yml` runs the same line and then asks git whether
// the committed bundle still matches - which is what makes a file nobody reads
// trustworthy.
//
// **No version is stamped into the bundle, and that is deliberate.** `release.yml`
// rewrites `manifest.json`'s version and commits it just before it tags; a bundle that
// carried the version would be stale from that commit onwards, and every release would
// have to remember to rebuild it or watch CI go red. The panel learns its version at
// runtime instead, out of the `config` the registration hands it, and the URL it is
// fetched from carries `?v=<version>` so a browser still cannot serve an old one.

import { build } from "esbuild";
import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const outfile = join(here, "..", "custom_components", "myhome", "frontend", "myhome-panel.js");

// `tests/test_panel_build.py` asserts this exact first line, so a bundle built by
// something else - or edited by hand - is a failing test and not a mystery.
const BANNER = "/* MyHOME calibration panel */";

await mkdir(dirname(outfile), { recursive: true });

await build({
  entryPoints: [join(here, "src", "main.ts")],
  outfile,
  bundle: true,
  format: "esm",
  target: "es2022",
  minify: true,
  // Off: a source map would double what HACS ships, and the bundle is read by nobody -
  // the source next to it is the thing to read.
  sourcemap: false,
  legalComments: "none",
  banner: { js: BANNER },
  charset: "utf8",
  logLevel: "info",
});
