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
const gateway = ({ session = null, refuse = () => null, owner = true } = {}) => {
  const counts = new Map();
  const lastOf = new Map();
  const listeners = new Map();
  let subscriber = null;
  const state = { session, refuse, owner };

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
        return Promise.resolve(structuredClone(overviewFixture));
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
      callback({ type: "overview", overview: structuredClone(overviewFixture) });
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

const mount = async (connection, hash = "#/calibrate") => {
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
  return { window, panel, settle, find: (selector) => deep(panel.shadowRoot, selector) };
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
  const end = deepAll(find("[data-wizard]").getRootNode(), "button")
    .find((button) => (button.textContent ?? "").includes("End the calibration"));
  end?.click();
  await settle(160);
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
  const { settle, find } = await mount(bench.connection, "#/calibrate/00:03:50:aa:bb:cc-2-81");
  await settle(200);
  checkThat("the wizard is drawn", find("myhome-wizard"));
  check("the session was read", bench.sessions("get") > 0, true);
  check("and nothing was started", bench.sessions("start"), 0);
  check("nor attached to", bench.sessions("attach"), 0);
  check("nor acted", bench.sessions("act"), 0);
  checkThat(
    "the screen says there is no calibration running",
    (find("myhome-wizard")?.shadowRoot?.textContent ?? "").includes("No calibration is running"),
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
  const end = deepAll(find("[data-wizard]").getRootNode(), "button")
    .find((button) => (button.textContent ?? "").includes("End the calibration"));
  end?.click();
  await settle(160);
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
  checkThat("and the refusal is on the screen", find("[data-session-trouble]"));
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

console.log("\nthe check's own footing");
check(
  "the heartbeat's period is the one this file compresses " +
    "(update REAL_HEARTBEAT_MS when HEARTBEAT_MS changes)",
  compressed > 0,
  true,
);

console.log(`\n${failures} check${failures === 1 ? "" : "s"} failed`);
process.exit(failures === 0 ? 0 : 1);
