import assert from "node:assert/strict";
import { after, afterEach, test } from "node:test";

import { translations } from "../../custom_components/myhome/frontend/panel/panel-translations.js";
import { dom, reset } from "./wizard-harness.mjs";

const { buildScreen } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-screens.js");

afterEach(reset);
after(() => dom.window.close());

/*
 * L-119 «same step, same bar»: the set and order of the actions in the bar are decided when a step is entered and never
 * change while the user stays on that step. Automatic events (the motor starting or stopping, the clock, a new view
 * from Home Assistant, the settling hold) only turn existing actions on or off. The one substitution allowed is Stop
 * replaced in place by the state line «La corsa è finita: la tapparella è ferma» (and back, when a new leg moves).
 * Each family below walks the states one step goes through and compares the bar's ids in order, for the tab that
 * guides the calibration and for a reader.
 */
const t = (key) => translations.it[key] || key;
const cover = { name: "Hall shutter", effective: { closing: { value: 21.7, origin: "native_fallback" }, opening: { value: 22.4, origin: "native_fallback" } }, travel_cm: 198 };
const base = { mode: "geometry", owner: true, read_only: false, sequence: 3, values: {}, samples: {}, readings: {}, slats: true, travel_cm: null };
const timed = { samples: { lift: 4.4 }, readings: { gap: 3 }, values: { opening_time: 22.2, closing_time: 21.7 }, travel_cm: 198 };
const halfRead = { ...timed, readings: { gap: 3, half_open: 97 } };
const acks = { ackLift: true, ackAscent: true, ackDescent: true, ackReadings: true };

/** The bar as ids in order; the finished line counts as the Stop whose slot it takes. */
export const barOf = (screen) => screen.actions.map(({ id }) => (id === "stopped" ? "stop" : id));
const screenAt = ({ path = "A", scope = null, view, local = {}, elapsed = null, status = {} }) => buildScreen({ t, language: "it", stage: "session", path, scope, cover,
  view: view && { ...base, ...view }, local, elapsed, status, previews: false });
const asReader = (state) => ({ ...state, view: { ...state.view, owner: false, read_only: true } });

/** Every state of one step: [label, state]. */
export const FAMILIES = {
  "C-11 guided ascent": [
    ["ready", { path: "C", scope: "times_only", view: { mode: "guided", phase: "confirm_closed" } }],
    ["① sent", { path: "C", scope: "times_only", view: { mode: "guided", phase: "confirm_closed" }, status: { starting: true } }],
    ["starting", { path: "C", scope: "times_only", view: { mode: "guided", phase: "starting_open" }, elapsed: 0 }],
    ["moving", { path: "C", scope: "times_only", view: { mode: "guided", phase: "opening" }, elapsed: 5 }],
    ["locked", { path: "C", scope: "times_only", view: { mode: "guided", phase: "opening" }, elapsed: 6, status: { locked: true } }],
    ["② pressed, motor stopped", { path: "C", scope: "times_only", view: { mode: "guided", phase: "opening", motor_stopped: true, stopped_elapsed: 12 },
      local: { fullRun: { step: "opening", pressed: true } }, elapsed: 13 }],
  ],
  "C-14 guided descent": [
    ["ready", { path: "C", scope: "times_only", view: { mode: "guided", phase: "confirm_open" }, local: { ackAscent: true } }],
    ["starting", { path: "C", scope: "times_only", view: { mode: "guided", phase: "starting_close" }, local: { ackAscent: true }, elapsed: 0 }],
    ["moving", { path: "C", scope: "times_only", view: { mode: "guided", phase: "closing" }, local: { ackAscent: true }, elapsed: 4 }],
    ["② pressed, motor stopped", { path: "C", scope: "times_only", view: { mode: "guided", phase: "closing", motor_stopped: true, stopped_elapsed: 21 },
      local: { ackAscent: true, fullRun: { step: "closing", pressed: true } }, elapsed: 22 }],
  ],
};

/** The walk: one code family (the step), one bar. */
export function assertOneBar(name, states) {
  const screens = states.map(([label, state]) => [label, screenAt(state)]);
  const [firstLabel, first] = screens[0];
  for (const [label, screen] of screens.slice(1)) {
    assert.deepEqual(barOf(screen), barOf(first), `${name}: «${label}» (${screen.code}) changes the bar of «${firstLabel}» (${first.code})`);
  }
  return screens;
}

for (const [name, states] of Object.entries(FAMILIES)) {
  test(`L-119: ${name} keeps one bar for the guide and for a reader`, () => {
    assertOneBar(name, states);
    assertOneBar(`${name} (reader)`, states.map(([label, state]) => [label, asReader(state)]));
  });
}

test("L-119: the walk tells a bar that changes from one that only turns actions on or off", () => {
  const states = FAMILIES["C-11 guided ascent"];
  const screens = assertOneBar("C-11", states);
  assert.ok(screens.some(([, screen]) => screen.actions.some((action) => action.disabled)) && screens.some(([, screen]) => screen.actions.every((action) => action.id !== "run:open" || !action.disabled)),
    "the same ids, on and off");
  assert.throws(() => assertOneBar("broken", [["a", { view: { step: "lift", phase: "opening" }, local: { ackLift: true }, elapsed: 2 }],
    ["b", { view: { step: "lift", phase: "reading" }, local: { ackLift: true } }]]), /changes the bar/);
});
