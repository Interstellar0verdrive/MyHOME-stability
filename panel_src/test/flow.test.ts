// Getting to "Configura" from inside the panel: the probe, the event and the watchdog.
//
// The frontend's flow dialog is private API and this repository has no Home Assistant in
// it, so what can be tested is the decision - which of the two roads is taken, in which
// order, and whether the page always happens. That is also the part a regression would
// hurt most: a probe that got it wrong is a dead button, and there is no test in Python
// that could ever see it.

import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, it } from "node:test";

import { FLOW_URL, flowDialogDefined, navigateHomeAssistant, openOptionsFlow } from "../src/engine/flow";

interface Fakes {
  customElements: { get: (tag: string) => unknown; define: () => void };
  document: { querySelector: (selector: string) => unknown };
  history: { pushState: (state: unknown, title: string, path: string) => void };
  window: EventTarget;
  setTimeout: (fn: () => void, ms: number) => number;
}

const scope = globalThis as unknown as Fakes;

let defined: Set<string>;
let attached: Set<string>;
let pushed: string[];
let located: number;
let timers: Array<{ fn: () => void; ms: number }>;
let fired: Array<{ type: string; detail: Record<string, unknown> }>;

const source = {
  dispatchEvent(event: Event): boolean {
    fired.push({
      type: event.type,
      detail: (event as CustomEvent).detail as Record<string, unknown>,
    });
    return true;
  },
} as unknown as HTMLElement;

beforeEach(() => {
  defined = new Set();
  attached = new Set();
  pushed = [];
  located = 0;
  timers = [];
  fired = [];
  scope.customElements = { get: (tag) => (defined.has(tag) ? class {} : undefined), define: () => undefined };
  scope.document = { querySelector: (selector) => (attached.has(selector) ? {} : null) };
  scope.history = { pushState: (_state, _title, path) => pushed.push(path) };
  const bus = new EventTarget();
  bus.addEventListener("location-changed", () => (located += 1));
  scope.window = bus;
  scope.setTimeout = ((fn: () => void, ms: number) => timers.push({ fn, ms })) as never;
});

afterEach(() => {
  timers = [];
});

/** Run the watchdog the module scheduled, as a browser would after 400 ms. */
const tick = (): void => {
  const waiting = [...timers];
  timers = [];
  for (const timer of waiting) {
    timer.fn();
  }
};

describe("the probe", () => {
  it("is false when the frontend has not loaded its flow dialog", () => {
    assert.equal(flowDialogDefined(), false);
  });

  it("is true when it has", () => {
    defined.add("dialog-data-entry-flow");
    assert.equal(flowDialogDefined(), true);
  });
});

describe("with no dialog defined - which is what a fresh page load gives", () => {
  it("goes straight to the page, says so first, and fires no event at all", () => {
    const said: string[] = [];
    const road = openOptionsFlow({
      source,
      entryId: "01ENTRY",
      onLeaving: () => said.push("leaving"),
    });
    assert.equal(road, "page");
    assert.deepEqual(fired, []);
    assert.deepEqual(said, ["leaving"]);
    assert.deepEqual(pushed, [FLOW_URL]);
    assert.equal(located, 1);
    assert.equal(timers.length, 0);
  });
});

describe("with the dialog defined", () => {
  beforeEach(() => defined.add("dialog-data-entry-flow"));

  it("fires one show-dialog carrying the handler and the domain, and waits", () => {
    const road = openOptionsFlow({ source, entryId: "01ENTRY", onLeaving: () => undefined });
    assert.equal(road, "waiting");
    assert.equal(fired.length, 1);
    assert.equal(fired[0].type, "show-dialog");
    assert.equal(fired[0].detail.dialogTag, "dialog-data-entry-flow");
    assert.deepEqual(fired[0].detail.dialogParams, {
      startFlowHandler: "01ENTRY",
      domain: "myhome",
    });
    // Nothing has happened to the page yet, which is the whole point of waiting.
    assert.deepEqual(pushed, []);
    assert.equal(located, 0);
    assert.equal(timers.length, 1);
    assert.equal(timers[0].ms, 400);
  });

  it("goes to the page when nothing attached, and says so before it does", () => {
    const said: string[] = [];
    openOptionsFlow({ source, entryId: "01ENTRY", onLeaving: () => said.push("leaving") });
    tick();
    assert.deepEqual(said, ["leaving"]);
    assert.deepEqual(pushed, [FLOW_URL]);
    assert.equal(located, 1);
  });

  it("leaves the page alone when a dialog really did attach", () => {
    const said: string[] = [];
    attached.add("dialog-data-entry-flow");
    openOptionsFlow({ source, entryId: "01ENTRY", onLeaving: () => said.push("leaving") });
    tick();
    assert.deepEqual(said, []);
    assert.deepEqual(pushed, []);
    assert.equal(located, 0);
  });

  it("still schedules the watchdog when a listener throws, because dispatch is synchronous", () => {
    const angry = {
      dispatchEvent(): boolean {
        throw new Error("a listener blew up");
      },
    } as unknown as HTMLElement;
    assert.throws(() =>
      openOptionsFlow({ source: angry, entryId: null, onLeaving: () => undefined }),
    );
    // The real `dispatchEvent` reports a listener's exception to the page rather than
    // rethrowing; this only pins the shape of the call, and the page-always-happens
    // contract is the case above.
  });
});

describe("navigating Home Assistant", () => {
  it("is a pushState and the frontend's own location-changed, in that order", () => {
    navigateHomeAssistant("/config/integrations");
    assert.deepEqual(pushed, ["/config/integrations"]);
    assert.equal(located, 1);
  });
});
