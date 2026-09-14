// Standing the panel up outside a browser, for the two checks that need it.
//
// `tools/a11y.mjs` runs axe over it and `tools/keyboard.mjs` walks it with the keyboard.
// Both need the same thing: the committed bundle, in a document, answering the same stub
// gateway the development harness answers, in whichever of the panel's states is being
// looked at. That is here rather than twice.
//
// Dev-only. `jsdom` is a devDependency and nothing under `src/` imports it; what is loaded
// is the built bundle, so what is checked is what ships.

import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const bundle = join(root, "custom_components", "myhome", "frontend", "myhome-panel.js");
export const axeSource = join(here, "..", "node_modules", "axe-core", "axe.min.js");

const fixture = JSON.parse(
  await readFile(join(root, "tests", "fixtures", "panel_overview_example.json"), "utf8"),
);
const strings = JSON.parse(
  await readFile(join(root, "custom_components", "myhome", "strings.json"), "utf8"),
);

/** The rules jsdom cannot honestly answer: they need layout, and it has none. */
export const NEEDS_LAYOUT = [
  "color-contrast",
  "target-size",
  "scrollable-region-focusable",
  "meta-viewport",
];

/**
 * One gateway, in the state named. Everything is the real fixture; the states that need
 * more than one shutter to be interesting get the shutter the harness adds.
 */
const overviewFor = (state) => {
  const answer = structuredClone(fixture);
  const extra = structuredClone(answer.covers[0]);
  Object.assign(extra, {
    unique_id: "aa:bb:cc:dd:ee:ff-2-84",
    entity_id: "cover.attic_shutter",
    name: "Attic Shutter",
    area: null,
    area_id: null,
    height: null,
    profile: null,
    profile_from_file: false,
    profile_missing: false,
    origin: "defaults",
    has_own: [],
    order_index: answer.covers.length,
  });
  answer.covers = [...answer.covers, extra];
  answer.order = answer.covers.map((cover) => cover.unique_id);
  if (state === "measuring") {
    answer.measuring = {
      cover_unique_id: answer.covers[0].unique_id,
      name: answer.covers[0].name,
    };
  }
  if (state === "first-run") {
    answer.profiles = [];
    answer.covers = answer.covers.map((cover) => ({ ...cover, profile: null }));
  }
  if (state === "no-basic-covers") {
    answer.no_basic_covers = true;
    answer.covers = [];
    answer.profiles = [];
  }
  return answer;
};

const connection = (state) => ({
  sendMessagePromise(message) {
    if (message.type === "myhome/calibration/texts") {
      return Promise.resolve({
        language: "en",
        requested: "en",
        fallback: false,
        texts: {
          options: strings.options,
          selector: strings.selector,
          exceptions: strings.exceptions,
          panel: strings.config_panel,
        },
      });
    }
    if (message.type === "myhome/calibration/overview") {
      return state === "error"
        ? Promise.reject({
            code: "not_found",
            message: "Config entry not loaded",
            translation_key: "entry_not_loaded",
          })
        : Promise.resolve(overviewFor(state));
    }
    if (message.type === "myhome/calibration/cover_detail") {
      const answer = overviewFor(state);
      const cover = answer.covers.find((one) => one.unique_id === message.cover_unique_id);
      if (!cover) {
        return Promise.reject({ code: "not_found", message: "no such cover" });
      }
      return Promise.resolve({
        entry_id: answer.entry_id,
        cover,
        keys: ["opening_time", "closing_time", "slat_time", "opening_roll", "closing_roll"].map(
          (key) => ({
            key,
            value: cover.values[key],
            origin: cover.has_own.includes(key) ? "own" : "profile",
            own: cover.has_own.includes(key),
            inherited_value: cover.values[key],
            inherited_origin: "inherited",
            profile_value: cover.values[key],
            file_value: null,
            default_value: null,
          }),
        ),
        forget: { falls_back_to: "defaults", profile: null, travel_stays: false },
      });
    }
    if (message.type === "myhome/calibration/preview") {
      return Promise.resolve({ entry_id: "01ENTRY", items: [] });
    }
    return Promise.reject({ code: "unknown_command", message: "unknown command" });
  },
  subscribeMessage(callback, message) {
    if (message.type !== "myhome/calibration/subscribe") {
      return Promise.reject({ code: "unknown_command", message: "unknown command" });
    }
    callback({ type: "overview", overview: overviewFor(state) });
    return Promise.resolve(async () => undefined);
  },
  addEventListener() {},
  removeEventListener() {},
});

export const settle = (window, ms = 60) =>
  new Promise((resolve) => window.setTimeout(resolve, ms));

/** Everything in one shadow root, and in the shadow roots of the elements inside it. */
export const deep = (root, selector) => {
  const direct = root.querySelector(selector);
  if (direct) {
    return direct;
  }
  for (const element of root.querySelectorAll("*")) {
    if (element.shadowRoot) {
      const found = deep(element.shadowRoot, selector);
      if (found) {
        return found;
      }
    }
  }
  return null;
};

export const deepAll = (root, selector) => {
  const found = [...root.querySelectorAll(selector)];
  for (const element of root.querySelectorAll("*")) {
    if (element.shadowRoot) {
      found.push(...deepAll(element.shadowRoot, selector));
    }
  }
  return found;
};

/** The panel, mounted, in the state named, with whatever the drive did to it done. */
export const mount = async ({ name, state, hash, drive, expect }) => {
  // The host document is Home Assistant's, not the panel's: a custom panel cannot give the
  // page a `<title>` or a `lang`, and a harness that left them off would report two
  // violations the panel has no way to fix and bury the ones it does.
  const dom = new JSDOM(
    '<!doctype html><html lang="en"><head><title>Home Assistant</title></head><body></body></html>',
    {
      runScripts: "outside-only",
      pretendToBeVisual: true,
      url: `http://localhost/myhome-calibration${hash ?? ""}`,
    },
  );
  const { window } = dom;
  // jsdom has no `matchMedia`, and the panel already guards every use of it - which is
  // what makes it safe to leave absent rather than faked into one width.
  window.eval(await readFile(axeSource, "utf8"));
  // The bundle is an ES module and jsdom will not load one out of a string, so it runs as
  // a classic script. esbuild leaves no `import` in it (everything is bundled) and exactly
  // one `export {…}`, which a classic script may not carry: it names the element class,
  // which nothing here reads - the element registers itself. It is followed by Lit's
  // licence comments (`legalComments: "eof"`), so it is not the last thing in the file.
  const module = (await readFile(bundle, "utf8")).replace(/\bexport\s*\{[^}]*\};?/g, "");
  window.eval(module);

  // jsdom lays nothing out, so `HTMLElement.offsetParent` is always null - and the panel's
  // own `focusable()` uses it to skip controls that are not on the screen. Left alone, that
  // makes every focus trap in the panel find nothing to hold and every focus check here
  // pass or fail for a reason that has nothing to do with the panel. The shim gives it the
  // browser's answer for an element that is in the tree and not hidden, which is the case
  // this host ever builds.
  Object.defineProperty(window.HTMLElement.prototype, "offsetParent", {
    configurable: true,
    get() {
      return this.hidden || !this.isConnected ? null : (this.parentElement ?? null);
    },
  });

  const panel = window.document.createElement("myhome-calibration-panel");
  panel.hass = {
    states: {},
    connection: connection(state),
    language: "en",
    locale: { language: "en" },
  };
  panel.narrow = false;
  panel.route = { prefix: "/myhome-calibration", path: hash ? hash.slice(1) : "/" };
  panel.panel = {
    title: "Profili e tapparelle",
    icon: null,
    url_path: "myhome-calibration",
    config: { version: "0.6.0.dev" },
  };
  window.document.body.appendChild(panel);
  await settle(window, 150);

  if (drive) {
    await drive({ window, panel, deep, deepAll, settle: (ms) => settle(window, ms ?? 80) });
    await settle(window, 120);
  }

  // A state driven by clicking is a state that can quietly fail to happen, and an audit of
  // the screen before it would pass for the wrong reason. Each driven state says what it
  // expects to be able to see.
  if (expect && !deep(panel.shadowRoot, expect)) {
    throw new Error(`${name}: the state was never reached ('${expect}' is not on the screen)`);
  }

  return { name, dom, window, panel, settle: (ms) => settle(window, ms ?? 80) };
};

export const COVER = "#/cover/00:03:50:aa:bb:cc-2-81";

/** Enter on the first handle: the keyboard road into "Quale profilo?". */
export const openDialog = async ({ window, panel, deep, settle }) => {
  const handle = deep(panel.shadowRoot, "button.handle");
  // Focused first, because that is the only way a keyboard reaches it - and because where
  // focus goes when the dialog closes is read off where it was when the dialog opened.
  handle.focus();
  handle.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
  await settle();
};

/** ...and a profile picked in it, which is one pending change. */
export const makePending = async (context) => {
  await openDialog(context);
  // Any destination but the one the shutter is already on, so the change is a change and
  // not a withdrawal.
  const option = context
    .deepAll(context.panel.shadowRoot, ".options button.option")
    .find((button) => !button.classList.contains("current"));
  option?.click();
  await context.settle();
};

/** The mode a wide button opens, named by the button itself. */
export const pressWide = (index) => async ({ panel, deepAll, settle }) => {
  const buttons = deepAll(panel.shadowRoot, "button.wide:not([disabled])");
  buttons[index]?.click();
  await settle();
};


/** Every state worth checking, and how to get the panel into it. */
export const STATES = [
  { name: "overview", state: "ready" },
  { name: "overview, measuring", state: "measuring" },
  { name: "overview, first run", state: "first-run" },
  { name: "overview, no basic covers", state: "no-basic-covers" },
  { name: "the gateway refuses", state: "error" },
  { name: "overview, the profile dialog open", state: "ready", drive: openDialog, expect: ".dialog" },
  { name: "overview, one change pending", state: "ready", drive: makePending, expect: ".route .withdraw" },
  {
    name: "overview, the review sheet open",
    state: "ready",
    drive: async (context) => {
      await makePending(context);
      context.deep(context.panel.shadowRoot, "button.review")?.click();
      await context.settle();
    },
    expect: ".sheet",
  },
  { name: "cover detail", state: "ready", hash: COVER },
  { name: "cover detail, first action", state: "ready", hash: COVER, drive: pressWide(0) },
  { name: "cover detail, second action", state: "ready", hash: COVER, drive: pressWide(1) },
  { name: "cover detail, last action", state: "ready", hash: COVER, drive: pressWide(-1) },
  { name: "profile card", state: "ready", hash: "#/profile/tall" },
  { name: "profile card, first action", state: "ready", hash: "#/profile/tall", drive: pressWide(0) },
  { name: "profile card, second action", state: "ready", hash: "#/profile/tall", drive: pressWide(1) },
  { name: "profile card, last action", state: "ready", hash: "#/profile/tall", drive: pressWide(-1) },
];

