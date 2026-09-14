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

import { build, transform } from "esbuild";
import { mkdir, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const outfile = join(here, "..", "custom_components", "myhome", "frontend", "myhome-panel.js");

// `tests/test_panel_build.py` asserts this exact first line, so a bundle built by
// something else - or edited by hand - is a failing test and not a mystery.
const BANNER = "/* MyHOME calibration panel */";

// The stylesheets are minified, and they have to be minified here.
//
// A Lit stylesheet is a tagged template literal, and a template literal's contents are
// part of the program's meaning: `--minify` will not touch a character inside one, so
// every rule of every component ships with the indentation it was written with. Across the
// panel that is more than ten kilobytes of spaces in a file with a budget.
//
// So each `css`...`` block is handed to **esbuild's own CSS minifier** on the way in.
// Nothing here parses CSS: the extraction is the only home-made part of it, and it is
// safe because no `css` block in this source interpolates (`${`) or escapes anything - a
// grep over `src/` holds that, and a block that did would throw here rather than be
// mangled, because the closing backtick would be the wrong one.
//
// The source stays readable and the bundle stays small, which is the whole trade.
const CSS_BLOCK = /(^|[\s=(,[:])css`([^`]*)`/g;

const minifyStylesheets = {
  name: "minify-lit-css",
  setup(pluginBuild) {
    pluginBuild.onLoad({ filter: /\.ts$/ }, async (args) => {
      const source = await readFile(args.path, "utf8");
      if (!source.includes("css`")) {
        return null;
      }
      const blocks = [...source.matchAll(CSS_BLOCK)];
      if (blocks.length === 0) {
        return null;
      }
      const minified = await Promise.all(
        blocks.map((match) => transform(match[2], { loader: "css", minify: true })),
      );
      let index = 0;
      const contents = source.replace(CSS_BLOCK, (_whole, before) => {
        const done = minified[index++].code.trim();
        return `${before}css\`${done}\``;
      });
      return { contents, loader: "ts" };
    });
  },
};

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
  // Lit is BSD-3-Clause, and clause 2 asks a *binary* redistribution to reproduce the
  // copyright notice. The bundle is exactly that: HACS copies it to every installation
  // and `release.yml` puts it in the zip. `"eof"` collects the `@license` headers esbuild
  // would otherwise drop and prints them once at the end of the file, which costs half a
  // kilobyte and is the only attribution that travels with the thing being distributed.
  // The full licence text is beside the bundle in THIRD_PARTY_NOTICES.md.
  legalComments: "eof",
  banner: { js: BANNER },
  plugins: [minifyStylesheets],
  charset: "utf8",
  logLevel: "info",
});
