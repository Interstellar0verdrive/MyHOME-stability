# The panel's source

This directory is the source of **"Profili e tapparelle"**, the custom Home Assistant
panel the integration registers at `/myhome-calibration`. It is **not shipped**: nothing
under `panel_src/` is copied by HACS or included in the release zip. What ships is the
one file this directory builds:

```
custom_components/myhome/frontend/myhome-panel.js
```

That file **is committed to git**, on purpose. HACS copies `custom_components/myhome/`
as it exists at the tag and `release.yml` zips the same directory; there is no build step
at a user's end, so a missing bundle is a blank page. The price is a generated file in
the tree, and it is paid by `.github/workflows/panel.yml`, which rebuilds it on every
push and fails on any difference, and by `tests/test_panel_build.py`, which checks it
from the ordinary Python suite with no Node installed.

## Building

```sh
cd panel_src
npm ci        # exactly what package-lock.json pins; refuses to run without it
npm run check # tsc --noEmit, strict
npm run build # node build.mjs -> ../custom_components/myhome/frontend/myhome-panel.js
```

Built and verified with **Node 26.5** and npm 11. Any Node that can run esbuild will do;
the CI job pins the major so that "it built differently on my machine" is never the
explanation for a red diff.

`npm run build` is one command wrapping one esbuild call: one ES module, `es2022`,
minified, no source map. The bundle opens with the line `/* MyHOME calibration panel */`,
which is how the Python test recognises a file the build actually made.

**Commit the rebuilt bundle with the source change that caused it.** A pull request that
changes `src/` and not `custom_components/myhome/frontend/` fails CI, and so does the
reverse.

## The version

The bundle carries **no version number**, and must not start to. `release.yml` rewrites
`manifest.json`'s version and commits it immediately before tagging; a bundle with the
version baked in would be stale from that commit onwards and every release would have to
remember to rebuild it. Instead:

* the panel registration puts the integration's version in the panel's `config`, and the
  element reads it from there at runtime (`panel.config.version`);
* the URL the browser fetches carries `?v=<version>`, so `cache_headers=True` cannot hand
  anyone a bundle from the previous release.

## Dependencies

Three, pinned exactly: **lit** (runtime, bundled), **typescript** and **esbuild** (build
only). Nothing else goes in here. No framework, no router library, no CSS framework, no
Markdown library, no icon font, no date library — `Intl` and the frontend's own
`ha-markdown` cover the last two, and the bundle has a 150 kB ceiling asserted by
`tests/test_panel_build.py`.

Lit is bundled rather than borrowed from a frontend global: a global is not a contract.

Lit is BSD-3-Clause, and clause 2 asks a binary redistribution to reproduce its copyright
notice — which the shipped bundle is, since HACS copies it to every installation. So
`build.mjs` sets `legalComments: "eof"`: esbuild collects the `@license` headers it would
otherwise drop and prints them once at the end of the file (half a kilobyte), and the full
text of the conditions and the disclaimer ships beside the bundle in
`custom_components/myhome/frontend/THIRD_PARTY_NOTICES.md`. A new runtime dependency means
a new entry in that file; `tests/test_panel_build.py` asserts the notice is in the bundle.

## Layout

```
build.mjs             the whole build
src/main.ts           <myhome-calibration-panel>, the element Home Assistant creates
src/engine/ha.ts      customElements.get() guards for every ha-* element used
src/engine/i18n.ts    the texts, read from the backend, never compiled in
src/engine/theme.ts   Home Assistant's CSS variables, each with a fallback
src/engine/ws.ts      typed wrappers over the read commands; mirrors panel_schemas.py
src/types/ha.ts       the four properties Home Assistant sets, and the connection
```

## Rules that are not style

1. **The panel never re-derives what the backend resolved.** Not a cover's origin, not a
   profile rescaled onto a window. One function (`resolve_cover`) answers that question,
   on the server, for both the panel and the `Calibration source` attribute — which is
   the only reason the two can be trusted to agree.
2. **No sentence is compiled into the bundle.** Texts come from
   `myhome/calibration/texts`, out of the same seven translation files the guided dialog
   reads. A missing key renders as the key, so that it looks like the bug it is. (The
   handful of English fallbacks in `main.ts` exist only until the texts lot writes the
   `panel.*` block; each one is a call that lot deletes.)
3. **Every `ha-*` element goes through `defined()` with a rendered fallback.** They are
   private API and Home Assistant has renamed them before. A rename must cost chrome,
   never a screen.
4. **Colours come from Home Assistant's CSS variables, each with a `var()` fallback.**
   Never a literal. The panel is registered with `embed_iframe: false`, so light, dark and
   user themes work with no code of ours.
