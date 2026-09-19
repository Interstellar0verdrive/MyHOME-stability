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
/**
 * The frozen session examples (lot L0), which is where every snapshot in this file comes
 * from: a stub that made its own would be a stub agreeing with nothing.
 */
const sessions = JSON.parse(
  await readFile(join(root, "tests", "fixtures", "panel_session_examples.json"), "utf8"),
);

/** One scenario of the fixture, with the gateway of the overview this host serves. */
export const sessionFixture = (name, entryId) => {
  const scenario = sessions.scenarios[name];
  if (!scenario) {
    throw new Error(`no session scenario called '${name}' in the fixture`);
  }
  return { ...structuredClone(scenario), entry_id: entryId };
};

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
  if (state === "measuring" || state === "measuring-panel" || state === "measuring-service") {
    answer.measuring = {
      cover_unique_id: answer.covers[0].unique_id,
      name: answer.covers[0].name,
    };
  }
  if (state === "measuring-panel") {
    // `measuring` says a shutter is held; `session` says by whom. With both of them the
    // banner offers the wizard and the way of ending it; with `measuring` alone it is the
    // Configure dialog or the 0.4.2 action (SPEC §6).
    const snapshot = sessionFixture("running_open_lift", answer.entry_id);
    answer.session = {
      session_id: snapshot.session_id,
      cover_unique_id: answer.covers[0].unique_id,
      name: answer.covers[0].name,
      state: snapshot.state,
      owner: snapshot.owner?.client_id ?? null,
    };
  }
  if (state === "first-run" || state === "no-profiles") {
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

/**
 * Which example of the frozen fixture a state stands on.
 *
 * `session:<name>` names one directly, so that every screen of the wizard SPEC §7.2 asks
 * for is a state here without a second stub being written for each. `calibrating` is the
 * one lot F1 added and is kept, because two checks name it.
 */
const scenarioOf = (state) => {
  if (state === "calibrating") {
    return "running_open_lift";
  }
  if (state === "session:cannot-be-drawn") {
    return "running_open_lift";
  }
  return state.startsWith("session:") ? state.slice("session:".length) : null;
};

/**
 * The session commands, answered from the fixture.
 *
 * Enough for the screens this host audits and no more: a stub that ran the conversation
 * would be a second implementation of the server, and what is being audited is markup.
 * Every verb answers with the same snapshot the state stands on, so an audit of a screen
 * is an audit of that screen and not of wherever a press would have led. `heartbeat`
 * answers as the owner except on the state that exists to be somebody else's.
 */
const session = (state, message) => {
  const entryId = overviewFor(state).entry_id;
  const scenario = scenarioOf(state);
  const snapshot = scenario ? sessionFixture(scenario, entryId) : null;
  if (snapshot && state === "session:cannot-be-drawn") {
    // A snapshot the model cannot survive, so that the card of SPEC §5.8 is a state axe
    // looks at rather than one only `npm run session` walks past. The shutter is what the
    // contract says is always there, which is why its absence is the shape of "anything
    // the model does not survive".
    snapshot.cover = null;
  }
  if (message.type.endsWith("/get")) {
    return Promise.resolve({ session: snapshot, capabilities: sessions._contract.capabilities });
  }
  if (message.type.endsWith("/heartbeat")) {
    return Promise.resolve({ owner: scenario !== "owned_by_other", present_until: null });
  }
  if (message.type.endsWith("/cancel")) {
    return Promise.resolve({ session: null, already_ended: snapshot === null });
  }
  if (message.type.endsWith("/end_other")) {
    // The gateway that still reports a shutter in calibration after every dialog of it has
    // been closed is the one the 0.4.2 action is holding: it is the only way the panel can
    // tell the two apart, and `measuring-service` is the state that says so.
    const still = state === "measuring-service";
    return Promise.resolve({
      flows_aborted: still ? 0 : 1,
      still_calibrating: still,
      overview: overviewFor(state),
    });
  }
  return Promise.resolve({ session: snapshot });
};

/** A gateway that refuses `start` because somebody else is holding a shutter of it. */
const alreadyCalibrating = (by) => ({
  code: "not_allowed",
  message: "a shutter of this gateway is already in calibration",
  translation_key: "already_calibrating",
  translation_placeholders: { cover: "Hallway Shutter", by },
});

const connection = (state) => ({
  /** Every session command this mount sent, so a keyboard walk can say what it caused. */
  calls: [],
  sendMessagePromise(message) {
    if (message.type.startsWith("myhome/calibration/session/")) {
      this.calls.push(message.type.slice("myhome/calibration/session/".length));
    }
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
    if (message.type.startsWith("myhome/calibration/session/")) {
      if (message.type.endsWith("/start") && state.startsWith("busy:")) {
        return Promise.reject(alreadyCalibrating(state.slice("busy:".length)));
      }
      return session(state, message);
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

/**
 * The document, made as unhelpful as the one the panel really runs in.
 *
 * Home Assistant's frontend registers custom elements through a **scoped registry**
 * polyfill, and that polyfill does not implement the form parts of the DOM. In the v2
 * panel an ordinary read of a form's elements collection threw "Method not implemented"
 * and took a screen down, in production, on a document no check here had - jsdom
 * implements all of it, so the panel passed every check and failed in the one place it
 * mattered.
 *
 * So the properties SPEC §5.9 strikes out are replaced by accessors that throw the
 * frontend's own sentence, before the bundle is evaluated. `npm run a11y`,
 * `npm run keyboard` and `npm run session` therefore fail if the shipped code reaches for
 * one of them - on the screen, the way a user meets it - while
 * `test/scoped-registry.test.ts` fails earlier and says which line.
 *
 * It is deliberately narrow: only the five properties on the list, and nothing about how
 * an `<input>` or a shadow root behaves, which is what the panel actually uses.
 */
export const forbidFormApis = (window) => {
  const refuse = (name) => ({
    configurable: true,
    get() {
      throw new Error(`Method not implemented. (${name})`);
    },
  });
  Object.defineProperty(window.HTMLFormElement.prototype, "elements", refuse("form.elements"));
  Object.defineProperty(
    window.HTMLFieldSetElement.prototype,
    "elements",
    refuse("fieldset.elements"),
  );
  Object.defineProperty(window.Document.prototype, "forms", refuse("document.forms"));
  for (const name of ["requestSubmit", "reset", "namedItem"]) {
    Object.defineProperty(window.HTMLFormElement.prototype, name, refuse(`form.${name}`));
  }
};

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
  // This tab's name in the session, seeded before the bundle reads it.
  //
  // `SessionClient` keeps it in `sessionStorage` and every example of the fixture is owned
  // by `_example.this_client_id`. Without this the panel would make a random name, find
  // itself looking at somebody else's calibration, and every screen below would be audited
  // in its read-only form - which is a real screen, but not the one with the controls on
  // it (there is a state further down that is deliberately somebody else's).
  try {
    window.sessionStorage.setItem("myhome-calibration-client", sessions._example.this_client_id);
  } catch {
    // A jsdom without storage: the states go on being audited read-only, which the
    // `expect` of each of them then catches.
  }
  // …and, before the bundle is loaded, the document is made to behave the way Home
  // Assistant's really does. See `forbidFormApis`.
  forbidFormApis(window);
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
  const gateway = connection(state);
  panel.hass = {
    // One shutter's position, because the wizard's press screens show the shutter's own
    // estimate beside the motor line and a state with no entity in it would audit a
    // screen with one row where the panel draws two.
    states: {
      "cover.hallway_shutter": { state: "opening", attributes: { current_position: 12 } },
    },
    connection: gateway,
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

  return { name, dom, window, panel, calls: gateway.calls, settle: (ms) => settle(window, ms ?? 80) };
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

/** …and the same by name, for the buttons whose position depends on the shutter. */
const pressNamedWide = (mark) => async ({ panel, deep, settle }) => {
  deep(panel.shadowRoot, `button.wide[data-wide="${mark}"]`)?.click();
  await settle();
};

/** One of the banner's offers, named by the mark it carries. */
const pressBanner = (mark) => async ({ panel, deep, settle }) => {
  deep(panel.shadowRoot, `[data-banner="${mark}"]`)?.click();
  await settle();
};

/**
 * The first shutter of the choice, and then "Continue", which is how a session is asked
 * for (lot F3, and the two gestures of live finding 3).
 */
const pressPickedShutter = async ({ panel, deep, deepAll, settle }) => {
  deep(panel.shadowRoot, ".options button.option")?.click();
  await settle();
  deepAll(panel.shadowRoot, "button.big")[0]?.click();
  await settle();
};

/** The wizard's own address, whichever screen of it is being looked at. */
const wizard = (name, scenario, more = {}) => ({
  name: `the wizard, ${name}`,
  state: `session:${scenario}`,
  hash: "#/calibrate",
  expect: "[data-wizard]",
  ...more,
});

/** One press on a control the wizard's screen draws, named by the selector that finds it. */
const pressInWizard = (selector) => async ({ deep, panel, settle }) => {
  deep(panel.shadowRoot, selector)?.click();
  await settle();
};

/**
 * Every screen of the guided calibration SPEC §7.2 lists, one per template and per state.
 *
 * The choice of route, a reading step, a reading the flow refused, the two moments of a
 * press, a positioning run, a check, the check that carries a field, the review shut and
 * open, the two ends, a problem, a calibration somebody else is driving, and the question
 * the cross asks.
 */
export const WIZARD_SCREENS = [
  wizard("the choice of route", "armed_path"),
  wizard("a choice of profiles", "armed_path_b_profile_choice"),
  wizard("a brief before a timed run", "briefing_open_brief"),
  wizard("the motor starting", "running_open_start"),
  wizard("a press to be made", "running_open_lift"),
  wizard("a press registered", "running_lift_stop"),
  wizard("a positioning run", "positioning_home_closed"),
  wizard("a check with three answers", "briefing_lift_check"),
  wizard("a check that asks for a number", "awaiting_reading_lift_gap"),
  wizard("a tape reading", "awaiting_reading_measure_descent"),
  wizard("a tape reading the flow refused", "awaiting_reading_measure_descent_error"),
  wizard("a profile to name", "briefing_profile_name"),
  // The five the regenerated fixture added (lot B3): the second route's profile choice,
  // and the whole of a verification - the offer, the run that sets it up, the reading and
  // the two answers it can come to, inside the threshold and over it.
  wizard("a choice of profiles to correct", "armed_path_c_profile_choice"),
  wizard("the offer of a verification", "briefing_verify_offer"),
  wizard("a run on the way to a verification", "positioning_verify"),
  wizard("the reading of a verification", "awaiting_reading_measure_verify"),
  wizard("a verification that came out inside the threshold", "checking_verify_result_within"),
  wizard("the review", "review_basic_profile_exists"),
  wizard("the review, every value shown", "review_basic_profile_exists", {
    name: "the wizard, the review with every value shown",
    drive: pressInWizard('[data-disclose="show:all"]'),
    expect: "pre.code",
  }),
  wizard("a step that was abandoned", "problem_no_echo"),
  wizard("a calibration that was saved", "saved_profile"),
  wizard("a calibration that timed out", "ended_expired"),
  wizard("one somebody else is driving", "owned_by_other", { expect: "[data-take-control]" }),
  wizard("the question the cross asks", "running_open_lift", {
    name: "the wizard, the question the cross asks",
    drive: pressInWizard("[data-wizard-exit]"),
    expect: "[data-exit-dialog]",
  }),
  // The card of SPEC §5.8. `npm run session` asserts that it appears and that the presence
  // signal goes on arriving; this asks whether it is a card anybody can use - it is the
  // one screen whose whole job is to offer a way on.
  wizard("a screen that could not be drawn", "cannot-be-drawn", {
    name: "the wizard, a screen that could not be drawn",
    expect: "[data-render-error]",
  }),
];

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
  // The two routed cards are drawers over the list since the first live pass, so each of
  // these states is "the overview, and a panel over it" - and `expect` is the drawer
  // itself, because a hash that stopped opening one would otherwise audit the list twice
  // and pass.
  { name: "cover detail", state: "ready", hash: COVER, expect: "[data-drawer]" },
  // The first action of both cards is the hand edit, and the advanced note is what says
  // the form is really open (and gives axe the note to look at).
  { name: "cover detail, first action", state: "ready", hash: COVER, drive: pressWide(0), expect: "[data-advanced-note]" },
  { name: "cover detail, second action", state: "ready", hash: COVER, drive: pressWide(1), expect: "[data-drawer]" },
  { name: "cover detail, last action", state: "ready", hash: COVER, drive: pressWide(-1), expect: "[data-drawer]" },
  {
    name: "cover detail, the profile choice over it",
    state: "ready",
    hash: COVER,
    drive: async (context) => {
      const assign = context
        .deepAll(context.panel.shadowRoot, "button.wide:not([disabled])")
        .find((button) => (button.textContent ?? "").includes("profile"));
      assign?.click();
      await context.settle();
    },
    expect: ".dialog",
  },
  // "Correggi…" and its three scopes, which are three ways into the wizard since lot F3.
  {
    name: "cover detail, the three scopes of a correction",
    state: "ready",
    hash: COVER,
    drive: pressNamedWide("correct"),
    expect: 'button.wide[data-wide="times-only"]',
  },
  // A gateway where nothing has ever been measured into a profile: a correction has no
  // profile to start from, so the two buttons that can only mean `path_c` say why instead
  // of opening a screen with nothing on it (BUG-1 of the review).
  {
    name: "cover detail, a gateway with no profiles to correct against",
    state: "no-profiles",
    hash: COVER,
    expect: 'button.wide[data-wide="correct"][disabled]',
  },
  { name: "profile card", state: "ready", hash: "#/profile/tall", expect: "[data-drawer]" },
  { name: "profile card, first action", state: "ready", hash: "#/profile/tall", drive: pressWide(0), expect: "[data-advanced-note]" },
  { name: "profile card, second action", state: "ready", hash: "#/profile/tall", drive: pressWide(1), expect: "[data-drawer]" },
  { name: "profile card, last action", state: "ready", hash: "#/profile/tall", drive: pressWide(-1), expect: "[data-drawer]" },
  // The wizard's address, with a session of the gateway's and without one, and then one
  // state for every screen of SPEC §7.2 - each standing on the example of the frozen
  // fixture that produces it, so that what is audited is a screen the server can really
  // send rather than one this file invented.
  { name: "the wizard, a session running", state: "calibrating", hash: "#/calibrate", expect: "[data-wizard]" },
  // No session on the gateway is the choice of shutter (lot F3), not an empty card: the
  // `expect` names the picker so that a route that stopped drawing it would fail here
  // rather than audit a screen with nothing on it and pass.
  { name: "the wizard, no session", state: "ready", hash: "#/calibrate", expect: "[data-wizard-pick]" },
  // …and the gateway where there is nothing to calibrate, which is the same address with
  // an empty list behind it.
  { name: "the wizard, nothing to calibrate", state: "no-basic-covers", hash: "#/calibrate", expect: "[data-wizard-empty]" },
  // …and the same choice on a gateway that is already holding a shutter: the condition is
  // said before the list, not discovered by pressing one of it.
  { name: "the wizard, choosing while the gateway is busy", state: "measuring", hash: "#/calibrate", expect: "[data-session-busy]" },
  ...WIZARD_SCREENS,
  // The banner in each of the three shapes SPEC §6 gives it, and the two questions it
  // asks. `measuring` alone is the Configure dialog; `measuring` with a session beside it
  // is this panel's own; `measuring-service` is the gateway that answers `end_other` with
  // the shutter still held.
  { name: "the banner, a session of the panel's", state: "measuring-panel", expect: '[data-banner="resume"]' },
  {
    name: "the banner, the question about ending it",
    state: "measuring-panel",
    drive: pressBanner("end-panel"),
    expect: "[data-banner-question]",
  },
  {
    name: "the banner, the question about closing the dialog",
    state: "measuring",
    drive: pressBanner("end-other"),
    expect: "[data-banner-question]",
  },
  {
    name: "the banner, an action of 0.4.2 holding the shutter",
    state: "measuring-service",
    drive: async (context) => {
      await pressBanner("end-other")(context);
      await pressBanner("confirm")(context);
    },
    expect: "[data-banner-service]",
  },
  // The waiting screen a refused `start` leaves, in the two shapes that have something to
  // press and the one that has not.
  ...["panel", "other", "reserved"].map((by) => ({
    name: `the wizard, the gateway is busy (${by})`,
    state: `busy:${by}`,
    hash: "#/calibrate",
    drive: pressPickedShutter,
    expect: "[data-session-busy]",
  })),
  {
    name: "the wizard, the question about closing the dialog",
    state: "busy:other",
    hash: "#/calibrate",
    drive: async (context) => {
      await pressPickedShutter(context);
      context.deep(context.panel.shadowRoot, '[data-busy="end-other"]')?.click();
      await context.settle();
    },
    expect: "[data-busy-question]",
  },
];

