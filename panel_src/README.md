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

## Looking at it without a Home Assistant

`dev/harness.html` loads the committed bundle, hands the element the four properties Home
Assistant hands it, and answers the two read commands with the real fixture
(`tests/fixtures/panel_overview_example.json`, which the Python suite regenerates from the
real server) and the real `strings.json`. Serve the repository root and open it:

```sh
python3 -m http.server 8765     # from the repository root
open http://localhost:8765/panel_src/dev/harness.html
```

The checkboxes across the top switch the states that are otherwise hard to reach: dark
theme, narrow, a measurement in progress, an installation with no profile yet, a gateway
whose shutters are all advanced, and an `overview` that refuses. It is not shipped and it is
not a test - it is somewhere to look.

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
build.mjs               the whole build
dev/harness.html        a page for looking at the panel without a Home Assistant
src/main.ts             <myhome-calibration-panel>, the element Home Assistant creates
src/engine/router.ts    location -> view; the panel's own hash, then Home Assistant's route
src/engine/store.ts     the client state: the server model, and what the user is doing to it
src/engine/screen.ts    <myhome-screen>: the ScreenModel contract and the responsive law
src/engine/markdown.ts  the little Markdown the texts contain, without a library
src/engine/i18n.ts      the texts, read from the backend, with numbers and dates
src/engine/theme.ts     Home Assistant's CSS variables, each with a fallback
src/engine/a11y.ts      the live region and focus return
src/engine/ha.ts        customElements.get() guards for every ha-* element used
src/engine/ws.ts        typed wrappers over every command; mirrors panel_schemas.py
src/i18n/keys.ts        every panel.* key the bundle asks for, and its English stand-in
src/templates/*.ts      the eight wizard step templates
src/components/*.ts     origin chip, cover row, group card, measuring banner
src/views/overview.ts   <myhome-overview>, the management screen
src/types/ha.ts         the four properties Home Assistant sets, and the connection
```

## The screen engine

Four pieces, and each is the thing 0.7.0 reuses without changing it.

**The router** (`engine/router.ts`) turns a location into `{view, params}` over four
patterns: `/`, `/cover/:id`, `/profile/:name` and - reserved, and rendered as "not in this
version" until 0.7.0 - `/calibrate/:session`. (The plan's fifth, `/gateway/:entry_id`, is
not routed: the gateway is chosen in the header and the header is lot 8's, and a house with
one gateway - which is nearly all of them - never sees either.) It reads the panel's **own hash** first (`#/cover/…`, written by the
panel and moved by `hashchange`, both of them platform behaviour) and falls back to the
`route.path` property Home Assistant sets, so a deep link of the form
`/myhome-calibration/cover/<id>` still opens the right screen on the first paint. Links
*out* of the panel are ordinary `<a href>` and are left to the browser.

**The store** (`engine/store.ts`) holds the server's `overview` in one field and everything
the user is doing in others. The server model is replaced whole on every read and every
push; the client model is never merged into it. That separation is what makes a push
arriving mid-edit harmless, and it is the reason lot 7's pending changes can exist at all.

**`<myhome-screen>`** (`engine/screen.ts`) renders a `ScreenModel` - id, template, title,
Markdown body, drawing, actions, and the live slots a moving shutter needs - through one of
the eight templates the wizard prototype names: `lettura`, `scelta`, `pos`, `click`,
`controllo`, `metro`, `riepilogo`, `esito`. It applies the handoff's responsive law once,
in CSS: below 900 px one column of at most 480 px with the call to action in a fixed footer
behind a 36 px gradient and 230 px of bottom margin on the content; at 900 px and above two
columns (text and drawing beside a 400 px operative column, 44 px apart, 1080 px at most)
with the right column sticky. A screen never acts: it fires `myhome-screen-action` with the
token its model gave it.

The templates are functions rather than eight custom elements on purpose. One element means
one shadow root, so the breakpoint is written once and a FLIP animation in lot 7 can measure
every row with one query.

**The texts** (`engine/i18n.ts`, `i18n/keys.ts`) come from `myhome/calibration/texts` with
named placeholders, plus `Intl` for numbers and dates in the user's language. `keys.ts` is
the list of every `panel.*` key the bundle asks for, with the English sentence beside each -
the offline stand-in, kept equal to `en.json` by `tests/test_translations.py`, which also
fails if the bundle asks for a key the files do not have.

**Two languages, during development.** The panel's block is `config_panel` in the eight
files and `panel` in the payload, and it is written in **English and Italian only**
(decision of 14 September 2026): a sentence that has to be translated into seven languages
before it can be tried on a screen is a sentence nobody rewrites. `strings.json`, `en.json`
and `it.json` are held key-for-key over that block; `fr`, `nl`, `es`, `de` and `pt` may
carry a subset, whose placeholders must still match, and one translation lot before the
0.6.0 release fills them. Nothing in the frontend has to know: `panel_data.async_texts`
serves each language **over English, key by key**, so a key a language has not reached yet
arrives as the English sentence rather than as a dotted identifier. A new panel sentence is
therefore added in three files — `strings.json`, `translations/en.json`,
`translations/it.json` — and in `src/i18n/keys.ts` with the same English words.

## Rules that are not style

1. **The panel never re-derives what the backend resolved.** Not a cover's origin, not a
   profile rescaled onto a window. One function (`resolve_cover`) answers that question,
   on the server, for both the panel and the `Calibration source` attribute — which is
   the only reason the two can be trusted to agree.
2. **No sentence is compiled into the bundle.** Texts come from
   `myhome/calibration/texts`, out of the same eight translation files the guided dialog
   reads. A missing key renders as the key, so that it looks like the bug it is. (The
   English stand-ins in `src/i18n/keys.ts` suspend that rule for the `panel.*` block only,
   and only until the texts lot writes it; the server's answer always wins where it has
   one.)
3. **Every `ha-*` element goes through `defined()` with a rendered fallback.** They are
   private API and Home Assistant has renamed them before. A rename must cost chrome,
   never a screen.
4. **Colours come from Home Assistant's CSS variables, each with a `var()` fallback.**
   Never a literal. The panel is registered with `embed_iframe: false`, so light, dark and
   user themes work with no code of ours. The pastels are
   `color-mix(in srgb, var(--X) N%, var(--card-background-color))` at the percentages the
   handoff fixes, and they are backgrounds only.
5. **No string ever becomes HTML.** `engine/markdown.ts` parses the paragraphs, bold, lists
   and `/myhome_static/` images the texts contain straight into Lit templates; nothing goes
   through `unsafeHTML`, and `ha-markdown` is deliberately not used for content. A tag that
   somehow reached a translation file arrives on the screen as the characters somebody
   typed.
