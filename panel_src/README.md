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

It also **minifies the stylesheets**, and it has to do that itself. A Lit stylesheet is a
tagged template literal, and `--minify` will not touch a character inside one: without the
plugin in `build.mjs` every component's CSS ships with the indentation it was written with,
which across the panel is more than fourteen kilobytes of spaces. Each ``css`…` `` block is
handed to esbuild's own CSS minifier on the way in; nothing here parses CSS, and the only
home-made part is finding the blocks. That is safe because no `css` block in `src/`
interpolates (`${`) or escapes anything - one that did would make the build throw rather
than be mangled, because the closing backtick would be the wrong one. Keep it that way.

**Commit the rebuilt bundle with the source change that caused it.** A pull request that
changes `src/` and not `custom_components/myhome/frontend/` fails CI, and so does the
reverse.

## Looking at it without a Home Assistant

`dev/harness.html` loads the committed bundle, hands the element the four properties Home
Assistant hands it, and stands in for the backend: the reads answer the real fixture
(`tests/fixtures/panel_overview_example.json`, which the Python suite regenerates from the
real server) and the real `strings.json`, and the writes — `preview`, `assign`, `reorder`,
`undo` and the subscription — work against a mutable copy of it with one undo slot, so the
whole assignment loop can be walked offline. Lot 8 added `cover_detail` and the six writes
the two routed cards make, and `profile_values` on a preview, so those can be walked offline
too - by clicking a row or a group heading, or straight at `#/cover/<unique id>` and
`#/profile/<name>`. Serve the repository root and open it:

```sh
python3 -m http.server 8765     # from the repository root
open http://localhost:8765/panel_src/dev/harness.html
```

The checkboxes across the top switch the states that are otherwise hard to reach: dark
theme, narrow, a measurement in progress, an installation with no profile yet, a gateway
whose shutters are all advanced, an `overview` that refuses and a write that does, a second
gateway so the header's picker has something to pick, and whether `myhome.yaml` states a
cover's travel - which is the one fact "Rimuovi la misura" cannot work out for itself. The
measuring and live-updates ones are **pushed down the subscription** rather than rebuilding
the element, because a measurement that starts while changes are already pending is a state
with a sentence of its own.

The scaling the stubbed `preview` does is the stub's own and is deliberately approximate.
It stands in for the server, which is the only thing allowed to do it: see the last rule
under *Dependencies*. It is not shipped and it is not a test — it is somewhere to look.

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
`ha-markdown` cover the last two, and the bundle has a 250 kB ceiling asserted by
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
src/engine/a11y.ts      the live region, focus return and the focus trap
src/engine/ha.ts        customElements.get() guards for every ha-* element used
src/engine/ws.ts        typed wrappers over every command; mirrors panel_schemas.py
src/engine/session-contract.ts  the calibration session on the wire: types, frozen
src/engine/session.ts   the session as this tab holds it: heartbeat, verbs, cancelling
src/engine/assign.ts    the pending-change model: pure functions, and no arithmetic
src/engine/fields.ts    the numeric fields of the two cards, and the bounds they obey
src/engine/flow.ts      opening the options flow: the probe, the watchdog, the page
src/engine/dnd.ts       FLIP, the pointer drag and the long press
src/i18n/keys.ts        every panel.* key the bundle asks for, and its English stand-in
src/i18n/fallback.json  the stand-ins themselves, held equal to en.json by the suite
src/templates/*.ts      the eight wizard step templates
src/components/*.ts     origin chip, cover row, group card, measuring banner,
                        the five bottom strips, "Quale profilo?", the review panel,
                        and card-page.ts: the shape both routed cards are cut from
src/views/overview.ts   <myhome-overview>, the management screen
src/views/cover-detail.ts   <myhome-cover-detail>, one shutter key by key
src/views/profile-card.ts   <myhome-profile-card>, one profile and its followers
src/views/wizard.ts     <myhome-wizard>, the guided calibration (a stub until lot F2)
src/types/ha.ts         the four properties Home Assistant sets, and the connection
```

## Assignment: three gestures, one pending state

A pointer drag from a row's handle (600 px and up), a long press and a tap on a collapsed
group title (below it), and Enter or Space on the handle at any width all produce the same
`PendingChange` in the store, drawn on the same row and confirmed in the same panel.
**Nothing is written until the confirm**: one `assign` carries every change, the positions
they imply and the travels the review panel collected, because a write reaches every cover
of the gateway at once.

Three rules the code follows and a reviewer should hold it to:

* **Pointer events, never HTML5 drag and drop.** `dragstart` is not fired by touch on iOS
  Safari, and its drag image cannot be styled. The handle carries `touch-action: none` and
  `pointerdown` is `preventDefault`ed; the drop target is found by hit-testing the shadow
  root, which is why every group and every row lives in one.
* **The pending changes live beside the server's model, never inside it.** A push replaces
  `overview` whole and the changes survive it, which is the contract's own rule.
* **The before/after numbers come from `myhome/calibration/preview`.** The panel never
  scales a profile.

## The two routed cards

`#/cover/<unique id>` and `#/profile/<name>` are **screens**, not panels over the list: the
plan routes both and asks a deep link to render on the first paint, and a modal over a list
nobody has loaded is not a thing a URL can produce. The prototype draws them as panels and
everything else about them is transcribed from it - the rows, the modes, the sentences, the
order of the buttons - and `components/card-page.ts` is the one stylesheet and the four
pieces they share.

What they ask the server, and what they do not:

* **the cover detail** reads `cover_detail`: on arrival, after each of its three writes and
  on each push while it is open. Every number, every origin, what an emptied field would
  inherit and what removing the measurement would leave is in that answer. The one thing
  that is not is what the shutter would run on at a **different** travel - a travel is what
  a profile is scaled by - so that field's before/after is `preview`'s, asked with the
  shutter's own assignment carried unchanged;
* **the profile card** reads nothing of its own: `overview` already carries every profile
  whole. Its editor asks `preview` with **`profile_values`** - the typed numbers in the
  profile's place - and one item per follower carrying that follower's current assignment,
  so that nothing but the profile is hypothetical. That is what the live impact preview is,
  and it is the third place the same rule applies: the panel does not scale a profile.

Both honour the measuring lock, keep a refused write where the user was working, and offer
the same seven-second undo strip as the rest of the panel. Escape steps back once - out of
a form into the card, out of the card to the list - and focus lands on the heading of
whatever has arrived.

## Getting to "Configura"

Five controls end in the guided calibration, which stays in the options flow for 0.6.0.
`engine/flow.ts` is the whole of it, and the order matters (plan section 3.7):

1. **probe** `customElements.get("dialog-data-entry-flow")`. Undefined - which is what a
   fresh page load is expected to give, since the frontend loads its dialogs lazily - and
   the panel navigates at once, with no event fired and no half-open state;
2. **fire and watch.** Defined, and `show-dialog` goes out; 400 ms later the document is
   asked whether a dialog really attached;
3. **the page.** It did not, so the panel says one line and navigates to
   `/config/integrations/integration/myhome`, where the user's next click is "Configura".

**The page is the contract and the dialog is the optimisation.** The parameters that dialog
wants carry a `flowConfig` of some twenty callbacks - how to create a flow, how to fetch
it, how to render each kind of step - which is the flow dialog's own configuration and not
something a panel bundled on its own can construct. HACS can fire the event because it is
built against the frontend source; we are not. So nothing in 0.6.0 becomes unreachable if
the event never works, and the acceptance criteria ask for the fallback rather than for it.

Neither path can preselect the shutter or the scope: the flow's `init` step is a menu that
takes no argument. The buttons name the path so the user knows which entry to pick, and an
entry point that carries one is a 0.7.0 item.

## The guided calibration

The measuring itself is moving into the panel in 0.6.0. The session it runs in lives
**on the server**, one per gateway: closing the tab, locking the phone or losing the
socket does not end it, and the panel's side of it is `src/engine/session.ts` - a class
with no Lit and no DOM in it, which `src/main.ts` makes when the first answer names a
gateway and which the screens talk to instead of talking to the socket. The ten commands
are wrapped in `engine/ws.ts` against the frozen contract
(`src/engine/session-contract.ts`, `docs/panel-websocket-api.md` §11-§14), and
`tests/fixtures/panel_session_examples.json` is where every snapshot in the checks and in
the harness comes from.

Five rules, each one a failure the v2 panel shipped on 18 September 2026. They are the
reason this part of the panel is built the way it is, and a reviewer should hold it to
them:

1. **The presence signal does not depend on the drawing.** The heartbeat is a
   `setInterval` of the client's own, started by `start` or `attach` and stopped only by
   the end of the session, by `leave` or by `dispose`. Nothing in `render()`, `updated()`
   or any other paint-time callback is on that path, and a listener that throws is caught.
   In v2 the heartbeat was sent from the render path: the first drawing error stopped it,
   and forty-five seconds later the server took the session away from somebody standing at
   the window with a tape measure.
2. **Cancelling never fails in silence.** `cancel()` answers on four branches - it worked
   or had already ended; another client owns it, so the screen offers "take control and
   end it" and "end it anyway"; the session is gone, which is what was asked for; or the
   gateway did not answer, and the offer is "try again" and "end it anyway", and when that
   is what failed, the time at which the lease frees the shutter by itself. No branch
   answers nothing, and no card ever comes out with a refusal on it and nothing underneath:
   the one recovery token that is not a button (`wait`) is always drawn as the sentence
   saying what happens anyway, with the hour when there is one to give.
   **"Take control" and "take control and end it" are two different offers**, with two
   tokens and two labels: only a refused "Cancel" ever offers the second, because only
   there is ending the thing that was asked for. A step refused because a second tab owns
   the session offers the first, and throws nothing away.
3. **No form APIs, anywhere.** Home Assistant loads custom elements through a scoped
   registry polyfill that does not implement them: `form.elements` threw "Method not
   implemented" in production. `test/scoped-registry.test.ts` scans `src/` for the eight
   of them and names the line; `tools/panel-host.mjs` makes those properties throw before
   it loads the bundle, so `a11y`, `keyboard` and `session` fail if the shipped code uses
   one. A guard like that only bites on a screen a check actually mounts, which is why each
   of the three opens `#/calibrate` in at least one of its states.
4. **Reloading `#/calibrate` never starts a session.** The address carries nothing -
   `/calibrate/<anything>` is the same route with what it names dropped - and the shutter,
   the path, the profile and the scope travel in the store as an *intention*. Arriving
   reads (`get`, then `attach`, both of which the contract defines as reads); only a
   button opens a session.
5. **Ownership is per browser tab, and taking it is deliberate.** The `client_id` lives in
   `sessionStorage`, so reloading the page is the same owner and a second tab is a second
   client. A heartbeat never takes ownership, however long the owner has been away, and the
   `attach` that arriving on the address sends goes **without `claim`**: opening a page can
   never take a measurement away from somebody who is in the middle of one. Taking control
   is a press, and both checks assert that the frame carried no claim.

```sh
npm run session   # the committed bundle in jsdom, against a session that misbehaves
```

It walks the ten states none of the other checks can reach: a snapshot the wizard cannot
draw (the error card appears, the panel goes on repainting when Home Assistant hands it a
new state, **and** the heartbeats go on arriving - the console line it prints is the panel
reporting that drawing error once, and is part of what is being checked), a "Cancel"
refused twice over and again with no hour to give, the address opened with no session and
opened on one somebody else is driving, a `start` refused while the gateway is busy with
another shutter, a session picked up again in the middle of a positioning run, and presence
lost and taken back. Two more are about the screens rather than the session: **every one
of the thirty-four examples of the frozen fixture pushed at the panel in turn**, each of
which has to draw a screen and not the card of a screen that could not be drawn, with
nothing said on the console on the way; and **every stylesheet the bundle ships**, which
has to have text in it. That last one exists because one of them did not: the CSS minifier
wrote a tick as `\2713`, which is not a valid escape inside the JavaScript template literal
the text goes back into, so the tagged template's cooked value was `undefined` and every
rule of `templates/styles.ts` was silently absent in a real browser. jsdom resolves no CSS
and no check here could see it; it was found by photographing the wizard beside the design.

The one thing it fakes beyond the gateway is the length of fifteen
seconds, so that it takes a second rather than a minute - and it counts the intervals it
compressed and fails if that count is zero, because a period that stopped matching would
otherwise leave half the scenarios passing while exercising no heartbeat at all.

`dev/harness.html` has the same thing to click at: the *a calibration session* checkbox
opens one on the fixture's snapshots and `#/calibrate` walks it.

**The screens themselves are a pure function.** `src/wizard/steps.ts` is one row per step
the conversation can stand on - which of the eight templates draws it, which of the six
phases the header names, which action is the big button, and whose words to show when the
step has none of its own - and `src/wizard/model.ts` turns a snapshot and that row into the
`ScreenModel` `<myhome-screen>` draws. Nothing else reads the snapshot: `views/wizard.ts`
holds the clock the motor line counts on, what the one field contains and where the
keyboard lands, and hands the rest over. That is what lets `test/wizard-model.test.ts` walk
every screen of the calibration without a browser, and it is what makes the error card of
SPEC §5.8 possible - a function that throws is a screen that can be replaced, where a view
that threw halfway through painting is a blank panel. The step table is held to the
contract's own list of sixty steps by that test, so a step the backend gains is a failure
that names it rather than a screen that quietly falls back to something.

One thing the screens add to the dialog's words: a **verification** carries the numbers it
was made of - where the shutter was sent, what the tape read, what the model had predicted -
under the dialog's own sentence about the deviation, and on path B the threshold the offer
to correct this shutter rests on. A check whose `gap_cm` is `null` had nothing to compare
against (the profile went out from under the session) and says so in the panel's own words:
the snapshot still carries `deviation: 0` because the dialog's sentence has to substitute
something, and a screen that printed "0.0 cm" there would be telling somebody their shutter
is perfect.

**The words of a measuring step are the dialog's.** `options.step.<step>` is already
translated into seven languages and the panel shows it as it is, illustration and all
(`splitLeadingImage` lifts the leading image into the drawing slot). What is the panel's
own, in English and Italian, is the four reviews, the outcomes, the positioning screens and
the one problem the dialog cannot produce - the steps whose dialog texts speak of the
dialog, of "Configure → Calibrations" or of "closing the dialog".

## The screen engine

Four pieces, and each is the thing 0.7.0 reuses without changing it.

**The router** (`engine/router.ts`) turns a location into `{view, params}` over four
patterns: `/`, `/cover/:id`, `/profile/:name` and `/calibrate`, which carries nothing after
it (see rule 4 above). (The plan's fifth, `/gateway/:entry_id`, is
not routed: the gateway is chosen by a select in the header, and a house with
one gateway - which is nearly all of them - never sees it.) It reads the panel's **own hash** first (`#/cover/…`, written by the
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
   reads. A missing key renders as the key, so that it looks like the bug it is. The one
   exception is the offline stand-in: `src/i18n/fallback.json` carries the English
   sentence for every `panel.*` key the bundle uses, because the panel paints before that
   call has answered and paints again when it fails, and four screens of dotted
   identifiers is not a better answer than four screens of English. The server's answer
   always wins where it has one, and `tests/test_translations.py` holds the stand-ins word
   for word to `strings.json` — and fails on a key the bundle asks for and the files do
   not have, and on a stand-in nobody asks for.
   The five origin phrases, the six value labels and the fourteen refusals are **not**
   among them: they are read from `selector.*`, `options.*` and `exceptions.*` in the same
   answer, because the panel is forbidden from keeping its own copy of a sentence the
   guided flow already says, and a fallback is a copy.
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
