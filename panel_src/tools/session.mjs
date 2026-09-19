// `npm run session` - the committed bundle against a calibration session that misbehaves.
//
// The states behind the failures the v2 panel shipped, each one unreachable from the other
// checks:
// `npm test` is the half of the panel with no DOM in it, `a11y` and `keyboard` mount it
// against a gateway that always answers, and `socket` is about subscriptions and not about
// sessions. What is asserted here is not what the screen looks like but what the panel
// **keeps doing** while things go wrong:
//
// 1. a snapshot the wizard cannot draw: the error card is on the screen **and** the
//    presence signal goes on arriving. In the v2 panel the presence signal was sent from
//    the render path, so a drawing error stopped it and the server handed the session to
//    somebody else forty-five seconds later, mid-measurement;
// 2. "Cancel" refused - by another client, and then by a socket that is down: there is
//    always a card on the screen, and always either a button on it or the sentence saying
//    when the gateway frees the shutter by itself;
// 3. the address opened with no session on the gateway: nothing is started, nothing is
//    attached to. What the user asked to measure travels in the store and never in the
//    address, so a reload or a pasted link cannot set a shutter moving;
// 4. a session picked up again in the middle of a positioning run: **no `act` is sent**.
//    A client that re-entered its step would send a shutter that is already moving on a
//    second journey;
// 5. the address opened on a session somebody else is driving: it attaches **without**
//    `claim`, so opening a page never takes a measurement away from whoever is holding the
//    tape. Taking control is a press, and only a press;
// 6. "Cancel" refused when the session has no hour to give: still something to press, or a
//    sentence saying what happens anyway;
// 7. a `start` refused while the gateway is busy: the refusal stays on the screen, and the
//    tab does not end up attached to the other shutter's session;
// 8. presence lost and taken back: still no `act`, and no `stop`. Losing ownership turns a
//    screen read-only; it moves nothing.
//
// The document is the one `tools/panel-host.mjs` builds for the other checks, with the
// same accessors throwing "Method not implemented" on the form APIs Home Assistant's
// scoped registry does not implement, so this check fails too if the bundle reaches for
// one.
//
// **The one thing that is faked beyond the gateway** is the length of fifteen seconds: the
// heartbeat's own interval is compressed so that this takes a second rather than a minute.
// Nothing else about it is touched - not who sends it, not what stops it, not what it is
// sent from.
//
// Dev-only, no browser: the committed bundle in jsdom, like the other three.

import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";

import { deep, deepAll, forbidFormApis } from "./panel-host.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const bundle = join(root, "custom_components", "myhome", "frontend", "myhome-panel.js");

const overviewFixture = JSON.parse(
  await readFile(join(root, "tests", "fixtures", "panel_overview_example.json"), "utf8"),
);
const strings = JSON.parse(
  await readFile(join(root, "custom_components", "myhome", "strings.json"), "utf8"),
);
const sessions = JSON.parse(
  await readFile(join(root, "tests", "fixtures", "panel_session_examples.json"), "utf8"),
);

/** The heartbeat's real period, and what it is compressed to here. */
const REAL_HEARTBEAT_MS = 15_000;
const FAST_HEARTBEAT_MS = 25;

/** A snapshot of the frozen fixture, on the gateway this stub serves. */
const scenario = (name, over = {}) => {
  const one = sessions.scenarios[name];
  if (!one) {
    throw new Error(`no scenario called '${name}' in panel_session_examples.json`);
  }
  return { ...structuredClone(one), entry_id: overviewFixture.entry_id, ...over };
};

/**
 * A gateway that counts every message and can be told to refuse.
 *
 * `session` is whatever the test wants the server to be holding; `refuse` is a function
 * that, given the command name, returns the refusal to throw or nothing.
 */
const gateway = ({
  session = null,
  refuse = () => null,
  owner = true,
  overview = null,
  endOther = null,
} = {}) => {
  const counts = new Map();
  const lastOf = new Map();
  const listeners = new Map();
  let subscriber = null;
  const state = {
    session,
    refuse,
    owner,
    overview: overview ?? structuredClone(overviewFixture),
    endOther: endOther ?? { flows_aborted: 1, still_calibrating: false },
  };

  const count = (type) => counts.get(type) ?? 0;

  const connection = {
    sendMessagePromise(message) {
      counts.set(message.type, count(message.type) + 1);
      lastOf.set(message.type, message);
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
        return Promise.resolve(structuredClone(state.overview));
      }
      if (message.type === "myhome/calibration/cover_detail") {
        // Enough of the card to press its buttons: what is being walked here is the road
        // from one of them into a session, not the card's own numbers.
        const cover = state.overview.covers.find(
          (one) => one.unique_id === message.cover_unique_id,
        );
        if (!cover) {
          return Promise.reject({ code: "not_found", message: "no such cover" });
        }
        return Promise.resolve({
          entry_id: state.overview.entry_id,
          cover,
          keys: Object.keys(cover.values).map((key) => ({
            key,
            value: cover.values[key],
            origin: cover.has_own.includes(key) ? "own" : "profile",
            own: cover.has_own.includes(key),
            inherited_value: cover.values[key],
            inherited_origin: "inherited",
            profile_value: cover.values[key],
            file_value: null,
            default_value: null,
          })),
          forget: { falls_back_to: "defaults", profile: null, travel_stays: false },
        });
      }
      if (message.type.startsWith("myhome/calibration/session/")) {
        const name = message.type.slice("myhome/calibration/session/".length);
        const refusal = state.refuse(name, message);
        if (refusal) {
          return Promise.reject(refusal);
        }
        if (name === "get") {
          return Promise.resolve({
            session: state.session,
            capabilities: sessions._contract.capabilities,
          });
        }
        if (name === "heartbeat") {
          return Promise.resolve({
            owner: state.owner,
            present_until: state.owner ? state.session?.idle_expires_at ?? null : null,
          });
        }
        if (name === "end_other") {
          // What the backend does: every options flow of this gateway is aborted, and the
          // gateway is answered afresh. A shutter still in calibration afterwards was the
          // 0.4.2 action's, which no dialog was holding.
          if (!state.endOther.still_calibrating) {
            state.overview = { ...state.overview, measuring: null, session: null };
            subscriber?.({ type: "overview", overview: structuredClone(state.overview) });
          }
          return Promise.resolve({
            ...state.endOther,
            overview: structuredClone(state.overview),
          });
        }
        if (name === "cancel") {
          state.session = state.session
            ? { ...state.session, state: "ended", step: null, actions: [] }
            : null;
          return Promise.resolve({ session: state.session, already_ended: false });
        }
        return Promise.resolve({ session: state.session });
      }
      return Promise.reject({ code: "unknown_command", message: "unknown command" });
    },
    subscribeMessage(callback, message) {
      if (message.type !== "myhome/calibration/subscribe") {
        return Promise.reject({ code: "unknown_command", message: "unknown command" });
      }
      subscriber = callback;
      callback({ type: "overview", overview: structuredClone(state.overview) });
      callback({ type: "session", session: state.session });
      return Promise.resolve(async () => {
        subscriber = null;
      });
    },
    addEventListener(name, handler) {
      if (!listeners.has(name)) {
        listeners.set(name, new Set());
      }
      listeners.get(name).add(handler);
    },
    removeEventListener(name, handler) {
      listeners.get(name)?.delete(handler);
    },
  };

  return {
    connection,
    state,
    count,
    /** How many of the session's commands of that name were sent. */
    sessions: (name) => count(`myhome/calibration/session/${name}`),
    /** The last frame of that command, so that a check can read what was really on it. */
    last: (name) => lastOf.get(`myhome/calibration/session/${name}`),
    /** The gateway as the panel sees it, replaced whole and pushed, as the server does. */
    pushOverview: (over) => {
      state.overview = { ...state.overview, ...over };
      subscriber?.({ type: "overview", overview: structuredClone(state.overview) });
    },
    push: (session) => {
      state.session = session;
      subscriber?.({ type: "session", session });
    },
    fire: (name) => {
      for (const handler of [...(listeners.get(name) ?? [])]) {
        handler(connection);
      }
    },
  };
};

/**
 * How many intervals this file has compressed.
 *
 * The period is repeated here rather than read out of the source, so that a check on the
 * bundle is not coupled to the text of a TypeScript file - but a repeated constant is a
 * constant that can silently stop matching. If `HEARTBEAT_MS` ever changes, the scenarios
 * that count beats would fail loudly and the three that do not would go on passing while
 * exercising no heartbeat at all. So the compression itself is counted, and asserted at the
 * end: zero means this file, not the panel, is what needs updating.
 */
let compressed = 0;

/**
 * Everything the bundle said out loud, so that "drawn without complaint" can be asserted.
 *
 * `runScripts: "outside-only"` evaluates the bundle against this window, so the `console`
 * it reaches is this window's. Wrapped before the bundle is loaded and left forwarding, so
 * a real failure is still printed where a person running this can read it.
 */
const recordConsole = (window, said) => {
  for (const level of ["error", "warn"]) {
    const original = window.console[level].bind(window.console);
    window.console[level] = (...args) => {
      said.push(`${level}: ${args.map((one) => String(one)).join(" ")}`);
      original(...args);
    };
  }
};

/**
 * Every custom element the bundle registers, collected as it registers them.
 *
 * Written down rather than listed: a list is right on the day it is written, and the
 * defect the stylesheet check exists to catch is silent, so a component added next month
 * would go unchecked without anybody noticing. The bundle registers itself, so the names
 * can be taken from it.
 */
const recordDefinitions = (window, into) => {
  const original = window.customElements.define.bind(window.customElements);
  window.customElements.define = (name, ...rest) => {
    into.push(name);
    return original(name, ...rest);
  };
};

const mount = async (connection, hash = "#/calibrate", said = null, defined = null) => {
  const dom = new JSDOM(
    '<!doctype html><html lang="en"><head><title>Home Assistant</title></head><body></body></html>',
    {
      runScripts: "outside-only",
      pretendToBeVisual: true,
      url: `http://localhost/myhome-calibration${hash}`,
    },
  );
  const { window } = dom;
  forbidFormApis(window);
  // The heartbeat's fifteen seconds, and only those, made short enough to watch. Every
  // other interval the panel keeps - the thirty-second poll - is left alone.
  const realSetInterval = window.setInterval.bind(window);
  window.setInterval = (handler, ms, ...rest) => {
    if (ms === REAL_HEARTBEAT_MS) {
      compressed += 1;
    }
    return realSetInterval(handler, ms === REAL_HEARTBEAT_MS ? FAST_HEARTBEAT_MS : ms, ...rest);
  };
  Object.defineProperty(window.HTMLElement.prototype, "offsetParent", {
    configurable: true,
    get() {
      return this.hidden || !this.isConnected ? null : (this.parentElement ?? null);
    },
  });
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
  if (said) {
    recordConsole(window, said);
  }
  if (defined) {
    recordDefinitions(window, defined);
  }
  window.eval((await readFile(bundle, "utf8")).replace(/\bexport\s*\{[^}]*\};?/g, ""));
  const panel = window.document.createElement("myhome-calibration-panel");
  panel.hass = {
    states: {},
    connection,
    language: "en",
    locale: { language: "en" },
  };
  panel.narrow = false;
  panel.route = { prefix: "/myhome-calibration", path: hash.slice(1) };
  panel.panel = {
    title: "Profili e tapparelle",
    icon: null,
    url_path: "myhome-calibration",
    config: { version: "0.6.0.dev" },
  };
  window.document.body.appendChild(panel);
  const settle = (ms = 120) => new Promise((resolve) => window.setTimeout(resolve, ms));
  await settle(200);
  return {
    window,
    panel,
    settle,
    find: (selector) => deep(panel.shadowRoot, selector),
    all: (selector) => deepAll(panel.shadowRoot, selector),
  };
};

let failures = 0;

/**
 * Anything that escapes a check is a failure with a name.
 *
 * Without this the tool simply dies and the shell reports an exit code, which is true but
 * says nothing - and the interesting case is exactly that: an exception thrown inside
 * `shouldUpdate`, from a snapshot the panel did not expect, leaves Lit unable to repaint and
 * reaches the process rather than any assertion here.
 */
for (const signal of ["uncaughtException", "unhandledRejection"]) {
  process.on(signal, (error) => {
    console.log(`  ✖   nothing may escape a check (${signal}) - ${error}`);
    console.log("\n1 check failed");
    process.exit(1);
  });
}

/**
 * The ✕ of the header, and then "Leave without saving".
 *
 * The one way out of the wizard, and it is two presses on purpose: the second is a
 * confirmation that says what leaving costs. Both controls are the panel's own - the cross
 * is in the toolbar (SPEC §5.1) and the question is drawn by the wizard under it.
 */
const leaveTheCalibration = async (find, settle) => {
  find("[data-wizard-exit]")?.click();
  await settle(120);
  find("[data-exit-leave]")?.click();
  await settle(160);
};

/**
 * A stylesheet's text, split into selectors and what they declare.
 *
 * Not a CSS parser: braces are balanced, comments are dropped and a conditional group is
 * walked into. It exists because jsdom leaves a shadow root's stylesheets unparsed, and
 * because the question being asked - *which rules reach this element* - needs selectors
 * and nothing else.
 */
const splitRules = (text) => {
  const found = [];
  const scan = (source) => {
    let at = 0;
    while (at < source.length) {
      const open = source.indexOf("{", at);
      if (open < 0) {
        return;
      }
      const selector = source.slice(at, open).trim();
      let depth = 1;
      let close = open + 1;
      while (close < source.length && depth > 0) {
        if (source[close] === "{") {
          depth += 1;
        } else if (source[close] === "}") {
          depth -= 1;
        }
        close += 1;
      }
      const body = source.slice(open + 1, close - 1);
      if (selector.startsWith("@")) {
        if (/^@(media|supports|layer|container)\b/.test(selector)) {
          scan(body);
        }
      } else if (selector !== "") {
        found.push({ selectorText: selector, cssText: `${selector}{${body}}` });
      }
      at = close;
    }
  };
  scan(text.replace(/\/\*[\s\S]*?\*\//g, ""));
  return found;
};

const check = (what, got, want) => {
  const ok = got === want;
  if (!ok) {
    failures += 1;
  }
  console.log(`  ${ok ? "ok " : "✖  "} ${what}${ok ? "" : ` - got ${got}, wanted ${want}`}`);
};
const checkThat = (what, ok) => check(what, Boolean(ok), true);

console.log("a snapshot the wizard cannot draw");
{
  // The shutter is gone from the snapshot. What it stands for is anything the screen's
  // model does not survive - and lot F2's model is a much larger thing than this stub, so
  // the guarantee has to be about what happens *around* the exception, not about which
  // exception it is.
  const bench = gateway({ session: scenario("running_open_lift") });
  const { panel, settle, find } = await mount(bench.connection);
  checkThat("the wizard is on the screen to begin with", find("[data-wizard]"));
  const before = bench.sessions("heartbeat");
  bench.push(scenario("running_open_lift", { cover: null }));
  await settle(200);
  checkThat("the drawing that threw shows a card", find("[data-render-error]"));
  checkThat("the panel itself is still there", panel.shadowRoot.querySelector(".toolbar"));
  // …and it is still a panel. Home Assistant replaces `hass` on every state change in the
  // whole house, so this happens constantly; `shouldUpdate` reads the session's shutter out
  // of it, and an exception there escapes asynchronously through Lit's update and stops the
  // panel repainting for good - which is the opposite of what this snapshot is here to show.
  panel.hass = { ...panel.hass, states: { "cover.hallway_shutter": { state: "open", attributes: {} } } };
  await settle(120);
  checkThat("and it goes on repainting when Home Assistant hands it a new state", find("[data-render-error]"));
  checkThat(
    "the presence signal went on arriving",
    bench.sessions("heartbeat") > before,
  );
  const after = bench.sessions("heartbeat");
  await settle(200);
  checkThat("and it is still arriving now", bench.sessions("heartbeat") > after);
}

console.log("\n'Cancel', refused");
{
  const bench = gateway({
    session: scenario("running_open_lift"),
    refuse: (name) =>
      name === "cancel"
        ? {
            code: "not_allowed",
            message: "another client owns this session",
            translation_key: "session_owned",
          }
        : null,
  });
  const { settle, find } = await mount(bench.connection);
  await leaveTheCalibration(find, settle);
  const card = find("[data-session-trouble]");
  checkThat("a refused cancel puts a card on the screen", card);
  // `claim_cancel`, not `claim`: this is the one place where taking control means ending the
  // calibration, and it has a token and a label of its own so that no other refusal can put
  // a button on the screen that promises to take control and throws the measurements away.
  checkThat(
    "with the way out on it",
    card && card.querySelector('[data-recovery="claim_cancel"]'),
  );
  checkThat(
    "and not the one that only takes control",
    card && !card.querySelector('[data-recovery="claim"]'),
  );

  // …and now the gateway stops answering at all, which is the other half of branch 4.
  bench.state.refuse = () => new Error("the connection is closed");
  find('[data-recovery="force"]')?.click();
  await settle(160);
  const second = find("[data-session-trouble]");
  checkThat("a cancel nobody answered still puts a card on the screen", second);
  checkThat(
    "and it says when the gateway frees the shutter by itself",
    second && (second.textContent ?? "").includes("releases the shutter"),
  );
}

console.log("\nthe wizard's address, opened with no session on the gateway");
{
  // Lesson 4, at the bundle: the address is all a reload has, and it says nothing. What
  // the user asked to measure travels in the store, so a page opened - or reopened, or
  // followed from a link somebody pasted - at this address finds a session or finds
  // nothing, and never an instruction to set a shutter moving.
  const bench = gateway({ session: null });
  const { settle, find, all } = await mount(bench.connection, "#/calibrate/00:03:50:aa:bb:cc-2-81");
  await settle(200);
  checkThat("the wizard is drawn", find("myhome-wizard"));
  check("the session was read", bench.sessions("get") > 0, true);
  check("and nothing was started", bench.sessions("start"), 0);
  check("nor attached to", bench.sessions("attach"), 0);
  check("nor acted", bench.sessions("act"), 0);
  // What the address alone produces is the *question* (lot F3), never an answer to it:
  // the shutter the identifier in the address names is one row of a list of them.
  checkThat("the screen asks which shutter to measure", find("[data-wizard-pick]"));
  checkThat(
    "and it offers every shutter of the gateway, not the one that was in the address",
    all(".options button.option").length === overviewFixture.covers.length,
  );
}

console.log("\na session picked up again in the middle of a run");
{
  // `positioning`: the shutter is on its way to a fraction of its travel, and the snapshot
  // says so. Everything a client does here is a read.
  const bench = gateway({ session: scenario("positioning_tape_run") });
  const { settle } = await mount(bench.connection);
  await settle(200);
  check("the session was read", bench.sessions("get") > 0, true);
  // Lesson 5, and the one guarantee a single character can undo: arriving on the address
  // attaches **without** `claim`, so opening a page never takes a measurement away from
  // whoever is holding the tape. `ws.ts` leaves the key out when it is false.
  check("it attached to it", bench.sessions("attach") > 0, true);
  check("and it did not take it from anybody", bench.last("attach")?.claim, undefined);
  check("nothing was acted", bench.sessions("act"), 0);
  check("nothing was stopped", bench.sessions("stop"), 0);
  check("nothing was started", bench.sessions("start"), 0);
  // The socket drops and comes back, which replays the subscription and pushes the same
  // snapshot again: the moment a client that "resumed its step" would move the shutter.
  bench.fire("disconnected");
  await settle(80);
  bench.fire("ready");
  await settle(240);
  check("still nothing acted after a reconnection", bench.sessions("act"), 0);
  check("still nothing stopped", bench.sessions("stop"), 0);
}

console.log("\nthe address opened on a session somebody else is driving");
{
  // The dangerous half of "attach on arrival": the owner is present and is not this tab.
  // The screen has to end up read-only, and the session has to stay where it is.
  const owned = scenario("owned_by_other");
  const bench = gateway({ session: owned, owner: false });
  const { settle, find } = await mount(bench.connection);
  await settle(200);
  checkThat("the wizard is drawn", find("[data-wizard]"));
  check("it attached", bench.sessions("attach") > 0, true);
  check("without claiming anything", bench.last("attach")?.claim, undefined);
  check("and it started nothing", bench.sessions("start"), 0);
  check("and acted nothing", bench.sessions("act"), 0);
}

console.log("\n'Cancel' refused with no hour to give");
{
  // `idle_expires_at` is nullable in the contract. The card must never come out with a
  // refusal on it and an empty row of buttons underneath.
  const bench = gateway({
    session: scenario("running_open_lift", { idle_expires_at: null }),
    refuse: (name) => (name === "cancel" ? new Error("the connection is closed") : null),
  });
  const { settle, find } = await mount(bench.connection);
  await leaveTheCalibration(find, settle);
  find('[data-recovery="force"]')?.click();
  await settle(160);
  const card = find("[data-session-trouble]");
  checkThat("there is a card", card);
  const pressable = card ? card.querySelectorAll("[data-recovery]").length : 0;
  const sentence = (card?.textContent ?? "").includes("releases the shutter");
  checkThat("with something to press, or a sentence saying what happens anyway", pressable > 0 || sentence);
}

console.log("\na start refused while the gateway is busy with another shutter");
{
  // BUG-4, from the independent review: `Router.navigate` sets `location.hash` and
  // `hashchange` is asynchronous, so the route the wizard's own entry point causes fires
  // while `start` is still in the air. Reading there would wipe the refusal off the screen
  // and - far worse - attach this tab to the *other* shutter's session, making it the owner
  // of a calibration nobody chose.
  const busy = scenario("running_open_lift", { owner: null });
  const bench = gateway({
    session: busy,
    refuse: (name) =>
      name === "start"
        ? {
            code: "not_allowed",
            message: "Hallway Shutter is already being calibrated",
            translation_key: "already_calibrating",
            translation_placeholders: { cover: "Hallway Shutter", by: "panel" },
          }
        : null,
  });
  const { panel, settle, find } = await mount(bench.connection, "#/");
  await settle(160);
  // The one road into the wizard, called the way lot F3 will call it.
  panel._assignActions.calibrate({ cover: "00:03:50:aa:bb:cc-2-84", name: "Attic Shutter" });
  await settle(300);
  check("the start was refused", bench.sessions("start"), 1);
  // Never a bare refusal: `already_calibrating` is the one the user meets by pressing a
  // button, so it is the waiting screen with the banner's own offers on it (SPEC §6).
  checkThat("and the refusal is on the screen", find("[data-session-busy]"));
  checkThat(
    "as a screen with a way on, not an error on its own",
    find("[data-session-busy]")?.querySelector("button") ?? null,
  );
  check("nothing attached to the other shutter's session", bench.sessions("attach"), 0);
  check("and nothing was acted on it", bench.sessions("act"), 0);
}

console.log("\npresence lost, and taken back");
{
  const bench = gateway({ session: scenario("positioning_tape_run"), owner: true });
  const { settle } = await mount(bench.connection);
  await settle(120);
  bench.state.owner = false;
  await settle(240);
  const away = bench.sessions("heartbeat");
  checkThat("the presence signal goes on while the tab is read-only", away > 0);
  check("losing ownership moved nothing", bench.sessions("act"), 0);
  bench.state.owner = true;
  await settle(240);
  checkThat("and it is still beating when ownership comes back", bench.sessions("heartbeat") > away);
  check("taking it back moved nothing either", bench.sessions("act"), 0);
  check("and stopped nothing", bench.sessions("stop"), 0);
}

console.log("\nevery state the contract can produce, drawn");
{
  // The thirty-four examples of the frozen fixture are one per screen the panel has to
  // draw (lot L0), so this is the whole conversation walked through `wizard/model.ts` on
  // the shipped bundle: every step of the sixty, every problem, every outcome, the form
  // errors, the outside movements, the read-only session and the four reviews.
  //
  // What is asserted is not what any of them looks like - that is `test/wizard-model.test.ts`
  // and the screenshots beside the design - but that **none of them is the error card** and
  // that nothing was said on the console on the way. A screen the model half-understands
  // draws something; a screen it throws on draws the card, and the card is a failure here.
  const said = [];
  const bench = gateway({ session: null });
  const { settle, find } = await mount(bench.connection, "#/calibrate", said);
  await settle(160);
  const names = Object.keys(sessions.scenarios);
  check("the fixture still carries every example", names.length, 39);
  let drawn = 0;
  let broken = [];
  for (const name of names) {
    bench.push(scenario(name));
    await settle(90);
    if (find("[data-render-error]")) {
      broken.push(name);
      continue;
    }
    if (find("[data-wizard]")) {
      drawn += 1;
    } else {
      broken.push(`${name} (nothing drawn)`);
    }
  }
  check("every one of them drew a screen", drawn, names.length);
  checkThat(
    broken.length === 0 ? "and none of them showed the card of a screen that could not be drawn"
      : `and none of them showed the card of a screen that could not be drawn (${broken.join(", ")})`,
    broken.length === 0,
  );
  const complaints = said.filter((one) => !one.includes("Lit is in dev mode"));
  checkThat(
    complaints.length === 0 ? "and nothing was said on the console" : `console: ${complaints[0]}`,
    complaints.length === 0,
  );
}

console.log("\nthe field a measurement is written into");
{
  // BUG-1 of the independent review, and the shape of it rather than one colour: the tape
  // reading's card is `class="reading big"`, where "big" means "the 64 px field of a
  // measurement" - and the 64 px *button* was `.big` too. Same specificity, so `.reading`
  // won back the background and not the colour, and the label, the number and the caret
  // were painted `--myhome-text-on-primary`: white on a white card, on every tape reading
  // of every route.
  //
  // What is asserted is that no rule written for a filled button reaches the field. It is
  // read off the stylesheets the shadow root really carries rather than off a colour,
  // because jsdom resolves no custom property - and because the next collision of two
  // meanings of one word will not be this one.
  const bench = gateway({ session: scenario("awaiting_reading_measure_descent") });
  const { settle, find } = await mount(bench.connection);
  await settle(160);
  const card = find(".reading");
  checkThat("the reading's card is on the screen", card);
  const label = card?.querySelector("label");
  const input = card?.querySelector("input");
  checkThat("with its label and its field in it", label && input);
  const root = card?.getRootNode();
  // jsdom parses no stylesheet inside a shadow root - `style.sheet` is null and
  // `adoptedStyleSheets` carries no rules - so the text is split here. Selectors and
  // declarations is all this needs, and `element.matches` is jsdom's own.
  const rules = splitRules(
    [...(root?.querySelectorAll?.("style") ?? [])].map((style) => style.textContent ?? "").join("\n"),
  );
  checkThat(`the screen's stylesheets were read (${rules.length} rules)`, rules.length > 0);
  const reaching = (element) =>
    rules.filter((rule) => {
      try {
        return element.matches(rule.selectorText);
      } catch {
        return false;
      }
    });
  const painted = [...reaching(card), ...(input ? reaching(input) : []), ...(label ? reaching(label) : [])]
    .filter((rule) => /--myhome-text-on-primary|--myhome-primary\)/.test(rule.cssText));
  checkThat(
    painted.length === 0
      ? "no rule written for a filled button reaches it"
      : `a button's rule reaches the field: ${painted.map((one) => one.selectorText).join(", ")}`,
    painted.length === 0,
  );
  // …and the rule that really is the button still reaches the button.
  const big = find("button.big");
  const onBig = big ? reaching(big).filter((rule) => /min-height: ?64px/.test(rule.cssText)) : [];
  checkThat("and the button still has the rule that makes it 64 px", onBig.length > 0);
}

console.log("\nstopping the shutter in the middle of a timed run");
{
  // BUG-2: `stop` is a verb of the contract and not one of the step's `menu_options`, so it
  // is never in `actions` and the screen has to offer it itself (SPEC §5.4, decision 10).
  // These are the three moments the shutter is really running towards an end stop.
  const bench = gateway({ session: scenario("running_open_lift") });
  const { settle, find, all } = await mount(bench.connection);
  await settle(160);
  const stop = all("button").find((button) => (button.textContent ?? "").includes("Stop the shutter"));
  checkThat("a run under way offers to stop the shutter", stop);
  check("and nothing has been stopped by arriving", bench.sessions("stop"), 0);
  stop?.click();
  await settle(160);
  check("pressing it sends the stop verb, once", bench.sessions("stop"), 1);
  check("and nothing else", bench.sessions("act"), 0);
  // The screen it advances to is the step made repeatable, which is the server's business;
  // what matters here is that the panel has a way to interrupt the one thing that moves.
  checkThat("the wizard is still on the screen", find("[data-wizard]"));
}

console.log("\nthe overview, 'Misura una tapparella', a shutter chosen, a session open");
{
  // SPEC §6, first two rows: the control that used to be a link to the integration page
  // now goes to the wizard, which asks *which* shutter - and only then is a session
  // opened. The whole road, on the shipped bundle, from the list to the first screen of a
  // calibration.
  const bench = gateway({ session: null });
  const { window, settle, find, all } = await mount(bench.connection, "#/");
  await settle(200);
  const measure = all("button.cta").find((one) =>
    (one.textContent ?? "").includes("Measure a cover"),
  );
  checkThat("the overview offers to measure a shutter", measure);
  checkThat("and it is a button, not a link out of the panel", measure?.tagName === "BUTTON");
  measure?.click();
  await settle(240);
  check("it goes to the wizard's own address", window.location.hash, "#/calibrate");
  checkThat("which asks which shutter", find("[data-wizard-pick]"));
  check("and nothing was started by getting there", bench.sessions("start"), 0);
  // The first snapshot the gateway hands back once a shutter is chosen.
  bench.state.session = scenario("armed_path");
  all(".options button.option")[0]?.click();
  await settle(240);
  check("choosing one opens one session", bench.sessions("start"), 1);
  check(
    "on the shutter that was pressed",
    bench.last("start")?.cover_unique_id,
    overviewFixture.covers[0].unique_id,
  );
  check("with no path decided for the user", bench.last("start")?.path, undefined);
  checkThat("and the wizard is drawing its first screen", find("[data-wizard]"));
}

console.log("\nthe shutter's card, 'Correggi… → Solo i tempi'");
{
  // SPEC §6, fourth row: the three scopes used to land in the dialog's opening menu, all
  // three of them in the same place. `start` carries the path, the profile and the scope
  // now, so the session is born on the screen the button named.
  // A shutter with values of its own: "Correggi…" is offered only where there is
  // something to correct.
  const cover = overviewFixture.covers.find(
    (one) => one.profile !== null && one.has_own.length > 0,
  );
  const bench = gateway({ session: null });
  const { window, settle, find } = await mount(
    bench.connection,
    `#/cover/${encodeURIComponent(cover.unique_id)}`,
  );
  await settle(240);
  find('button.wide[data-wide="correct"]')?.click();
  await settle(160);
  checkThat("the card offers the three scopes of a correction", find('[data-wide="times-only"]'));
  bench.state.session = scenario("armed_refine_scope_intent");
  find('[data-wide="times-only"]')?.click();
  await settle(280);
  check("one session is opened", bench.sessions("start"), 1);
  const asked = bench.last("start");
  check("on this shutter", asked?.cover_unique_id, cover.unique_id);
  check("on the correction's own route", asked?.path, "path_c");
  check("with the scope the button named", asked?.scope, "times_only");
  check("and the profile it follows, so the scope is what the screen asks about",
    asked?.profile, cover.profile);
  check("the address is the wizard's, and says nothing else", window.location.hash, "#/calibrate");
  checkThat("and the screen is the wizard's", find("[data-wizard]"));
}

console.log("\nthe banner over a session of this panel's, and 'Riprendi'");
{
  // `measuring` says a shutter of the gateway is held; `session` says by whom (contract
  // §4.5). With both of them the wizard is a screen of this panel, so the banner's way on
  // is the wizard's own address - and going there **reads**, it never starts anything.
  const running = scenario("running_open_lift");
  const bench = gateway({
    session: running,
    overview: {
      ...structuredClone(overviewFixture),
      measuring: { cover_unique_id: running.cover.unique_id, name: running.cover.name },
      session: {
        session_id: running.session_id,
        cover_unique_id: running.cover.unique_id,
        name: running.cover.name,
        state: running.state,
        owner: running.owner?.client_id ?? null,
      },
    },
  });
  const { window, settle, find } = await mount(bench.connection, "#/");
  await settle(200);
  checkThat("the banner names this panel's own calibration", find('[data-banner="resume"]'));
  checkThat("and offers to end it", find('[data-banner="end-panel"]'));
  find('[data-banner="resume"]')?.click();
  await settle(240);
  check("resuming goes to the wizard's own address", window.location.hash, "#/calibrate");
  checkThat("and the screen it lands on is the session's", find("[data-wizard]"));
  check("resuming started nothing", bench.sessions("start"), 0);
}

console.log("\nthe banner over the Configure dialog, and 'Termina'");
{
  // The same amber strip with **no** session beside `measuring`: the holder is the dialog
  // or the 0.4.2 action, neither of which this panel can drive. So the way out is
  // `end_other`, which closes every options flow of this gateway - after the question that
  // says what closing one costs.
  const first = overviewFixture.covers[0];
  const bench = gateway({
    session: null,
    overview: {
      ...structuredClone(overviewFixture),
      measuring: { cover_unique_id: first.unique_id, name: first.name },
      session: null,
    },
  });
  const { settle, find } = await mount(bench.connection, "#/");
  await settle(200);
  checkThat("the banner does not offer to resume a session nobody here opened",
    !find('[data-banner="resume"]'));
  checkThat("it offers to close the dialog", find('[data-banner="end-other"]'));
  find('[data-banner="end-other"]')?.click();
  await settle(120);
  checkThat("which asks first", find("[data-banner-question]"));
  check("and sends nothing by asking", bench.sessions("end_other"), 0);
  find('[data-banner="confirm"]')?.click();
  await settle(200);
  check("saying yes closes the dialogs of this gateway", bench.sessions("end_other"), 1);
  checkThat("and the shutter is free, so the strip is gone", !find("[data-banner-measuring]"));
  check("no session of this panel's was opened by any of it", bench.sessions("start"), 0);
}

console.log("\n…and the same strip when it was an action of 0.4.2 all along");
{
  const first = overviewFixture.covers[0];
  const bench = gateway({
    session: null,
    overview: {
      ...structuredClone(overviewFixture),
      measuring: { cover_unique_id: first.unique_id, name: first.name },
      session: null,
    },
    endOther: { flows_aborted: 0, still_calibrating: true },
  });
  const { settle, find } = await mount(bench.connection, "#/");
  await settle(200);
  find('[data-banner="end-other"]')?.click();
  await settle(120);
  find('[data-banner="confirm"]')?.click();
  await settle(200);
  check("every dialog was closed and the shutter is still held", bench.sessions("end_other"), 1);
  checkThat("so the strip stops offering", find("[data-banner-service]"));
  checkThat(
    "and says to wait instead",
    !find('[data-banner="end-other"]') && !find('[data-banner="configure"]'),
  );
}

console.log("\nthe stylesheets the bundle ships");
{
  // A Lit stylesheet that arrives with no text in it costs a screen its whole appearance
  // and nothing else: the markup is right, the checks that read markup pass, and the panel
  // ships looking like an unstyled document. It happened - the CSS minifier wrote a tick
  // as `\2713`, which is not a valid escape inside the JavaScript template literal the
  // text is put back into, so the tagged template's cooked value was `undefined` and every
  // rule of the eight step templates was dropped. jsdom resolves no CSS and could not see
  // it; this can, because `cssText` is a string either way.
  const bench = gateway({ session: scenario("briefing_open_brief") });
  const defined = [];
  const { window } = await mount(bench.connection, "#/calibrate", null, defined);
  const empty = [];
  checkThat(`the bundle registered ${defined.length} elements`, defined.length >= 6);
  for (const tag of defined) {
    const element = window.customElements.get(tag);
    // `styles` is a `CSSResultGroup`: a stylesheet, or a nest of arrays of them (several
    // components export `[sheetStyles, css`…`]`), so it is flattened before it is read.
    const sheets = [element?.styles ?? []].flat(Infinity);
    for (const [at, sheet] of sheets.entries()) {
      const text = sheet?.cssText;
      if (typeof text !== "string" || text.trim() === "") {
        empty.push(`${tag}[${at}]`);
      }
    }
  }
  checkThat(
    empty.length === 0
      ? "every stylesheet the bundle ships has text in it"
      : `a stylesheet shipped empty: ${empty.join(", ")}`,
    empty.length === 0,
  );
}

console.log("\nthe check's own footing");
check(
  "the heartbeat's period is the one this file compresses " +
    "(update REAL_HEARTBEAT_MS when HEARTBEAT_MS changes)",
  compressed > 0,
  true,
);

console.log(`\n${failures} check${failures === 1 ? "" : "s"} failed`);
process.exit(failures === 0 ? 0 : 1);
