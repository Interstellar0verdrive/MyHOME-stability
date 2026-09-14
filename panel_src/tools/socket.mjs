// `npm run socket` - the panel against a socket that drops, comes back, and flaps.
//
// The one state the other three checks cannot reach. `tools/a11y.mjs` and
// `tools/keyboard.mjs` mount the panel against a stub gateway whose `addEventListener` is
// a no-op, so nothing there ever sees Home Assistant restart; and `npm test` is the half
// of the panel that has no DOM in it, which the subscription is not.
//
// What it asserts is one number: **how many live subscriptions the panel is holding.** A
// second one is invisible from the screen - the model it pushes is the same model - and
// permanent: the handle of every subscription but the last is dropped on the floor, so
// each one goes on asking the gateway for a whole overview at every write for the life of
// the tab. It was reachable two ways, both of them ordinary: "Try again" pressed twice on
// the refusal card, and a socket that drops and comes back twice while the panel is
// polling. Both are here.
//
// Dev-only, no browser: the committed bundle in jsdom, like the other two.

import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const bundle = join(root, "custom_components", "myhome", "frontend", "myhome-panel.js");

const fixture = JSON.parse(
  await readFile(join(root, "tests", "fixtures", "panel_overview_example.json"), "utf8"),
);
const strings = JSON.parse(
  await readFile(join(root, "custom_components", "myhome", "strings.json"), "utf8"),
);

/**
 * A gateway that counts, and a socket that can be taken down and brought back.
 *
 * `subscribeMessage` is deliberately slow when asked to be: a race that only shows itself
 * when two callers overlap is a race a fast fake hides.
 */
const gateway = ({ refuseSubscribe = false, subscribeMs = 0 } = {}) => {
  const stats = { subscribes: 0, unsubscribes: 0, overviews: 0 };
  const listeners = new Map();
  const connection = {
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
        stats.overviews += 1;
        return connection.refuseOverview
          ? Promise.reject({
              code: "not_found",
              message: "Config entry not loaded",
              translation_key: "entry_not_loaded",
            })
          : Promise.resolve(structuredClone(fixture));
      }
      if (message.type === "myhome/calibration/preview") {
        return Promise.resolve({ entry_id: fixture.entry_id, items: [] });
      }
      return Promise.reject({ code: "unknown_command", message: "unknown command" });
    },
    async subscribeMessage(callback, message) {
      if (message.type !== "myhome/calibration/subscribe" || connection.refuseSubscribe) {
        throw { code: "unknown_command", message: "unknown command" };
      }
      if (subscribeMs) {
        await new Promise((resolve) => setTimeout(resolve, subscribeMs));
      }
      stats.subscribes += 1;
      callback({ type: "overview", overview: structuredClone(fixture) });
      return async () => {
        stats.unsubscribes += 1;
      };
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
    refuseSubscribe,
    refuseOverview: false,
  };
  const fire = (name) => {
    for (const handler of [...(listeners.get(name) ?? [])]) {
      handler();
    }
  };
  return { connection, stats, fire, live: () => stats.subscribes - stats.unsubscribes };
};

const mount = async (connection) => {
  const dom = new JSDOM(
    '<!doctype html><html lang="en"><head><title>Home Assistant</title></head><body></body></html>',
    {
      runScripts: "outside-only",
      pretendToBeVisual: true,
      url: "http://localhost/myhome-calibration",
    },
  );
  const { window } = dom;
  // As in `tools/panel-host.mjs`: the bundle is an ES module and jsdom will not load one
  // out of a string, so the single `export {…}` esbuild ends it with is taken off.
  window.eval((await readFile(bundle, "utf8")).replace(/\bexport\s*\{[^}]*\};?/g, ""));
  const panel = window.document.createElement("myhome-calibration-panel");
  panel.hass = {
    states: {},
    connection,
    language: "en",
    locale: { language: "en" },
  };
  panel.narrow = false;
  panel.route = { prefix: "/myhome-calibration", path: "/" };
  panel.panel = {
    title: "Profili e tapparelle",
    icon: null,
    url_path: "myhome-calibration",
    config: { version: "0.6.0.dev" },
  };
  window.document.body.appendChild(panel);
  const settle = (ms = 150) => new Promise((resolve) => window.setTimeout(resolve, ms));
  await settle(200);
  return { window, panel, settle };
};

let failures = 0;
const check = (what, got, want) => {
  const ok = got === want;
  if (!ok) {
    failures += 1;
  }
  console.log(`  ${ok ? "ok " : "✖  "} ${what}${ok ? "" : ` - got ${got}, wanted ${want}`}`);
};

console.log("a socket that drops and comes back");
{
  const { connection, stats, fire, live } = gateway();
  const { settle } = await mount(connection);
  check("one subscription on the way up", stats.subscribes, 1);
  const readAtStart = stats.overviews;
  for (let round = 0; round < 5; round += 1) {
    fire("disconnected");
    await settle(30);
    fire("ready");
    await settle(140);
  }
  check("still one subscription after five restarts", live(), 1);
  check("and it was never opened twice", stats.subscribes, 1);
  check("the gateway was read again on each of them", stats.overviews - readAtStart, 5);
}

console.log("\na socket that flaps while the panel is polling");
{
  // The backend did not know the command when the panel started, so it is polling - and
  // then the socket comes back three times in a row, faster than a round trip.
  const { connection, stats, fire, live } = gateway({ subscribeMs: 60 });
  connection.refuseSubscribe = true;
  const { settle } = await mount(connection);
  check("no subscription while the command is refused", stats.subscribes, 0);
  connection.refuseSubscribe = false;
  fire("disconnected");
  await settle(20);
  fire("ready");
  fire("ready");
  fire("ready");
  await settle(600);
  check("exactly one subscription is live", live(), 1);
  check("nothing was left holding a subscription nobody can give back", stats.unsubscribes, 0);
}

console.log("\n'Try again' pressed twice, faster than a round trip");
{
  // The gateway was reloading when the panel opened, so the screen is the refusal card
  // and its one button - the button whose whole job is to try the other half again.
  const { connection, stats, live } = gateway({ subscribeMs: 60 });
  connection.refuseSubscribe = true;
  connection.refuseOverview = true;
  const { panel, settle } = await mount(connection);
  connection.refuseSubscribe = false;
  connection.refuseOverview = false;
  const retry = panel.shadowRoot.querySelector("button.cta.text");
  if (!retry) {
    console.log("  ✖   the retry button was not on the screen");
    failures += 1;
  } else {
    retry.click();
    retry.click();
    retry.click();
    await settle(600);
    // Three presses are three attempts, and that is right: each one is somebody asking
    // again. What must not happen is two of them being live at once, so every attempt but
    // the last gives its own subscription back.
    check("exactly one subscription is live", live(), 1);
    check("every earlier attempt was given back", stats.unsubscribes, stats.subscribes - 1);
  }
}

console.log(`\n${failures} check${failures === 1 ? "" : "s"} failed`);
process.exit(failures === 0 ? 0 : 1);
