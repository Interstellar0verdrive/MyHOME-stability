// Where the calibration has got to, walked over the frozen fixture (live finding 29).
//
// The stepper is a pure function of a snapshot, like the screens it sits beside, so the
// whole of it can be asserted here: the thirty-nine examples the contract froze go through
// the same function the bundle uses, and every rule the design writes down is one test.
//
// Four families of assertion, and they are the four ways this can be wrong:
//
// * **a phase that moved backwards** - the six are shown in one order and the reader counts
//   to six, so a route whose current phase goes 3, 5, 4 is a rail that lies. The plan is
//   walked and the phase index is asserted never to go down;
// * **a row that was invented** - every row is a stage of `plan` and every number beside one
//   is a value of `measured`, so a reading's number is asserted against the very point of
//   `measured.descent` the flow took;
// * **a row that acts when it should not** - exactly one row can carry an action, and only
//   when the session is offering the verb that repeats *that* stage. Every other row is
//   asserted to have none, on every example of the fixture;
// * **a word the panel wrote** - the names are keys of the panel's own block, so a key that
//   does not exist would reach the screen as a dotted identifier.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { I18n } from "../src/engine/i18n";
import { type SessionSnapshot } from "../src/engine/session-contract";
import { type HaConnection } from "../src/types/ha";
import { PHASES } from "../src/wizard/steps";
import { screenModel, type WizardContext } from "../src/wizard/model";
import { currentPhase, readStepperOpen, writeStepperOpen } from "../src/wizard/stepper";
import { valueLabel, valueLine } from "../src/wizard/format";

import fixture from "../../tests/fixtures/panel_session_examples.json";
import english from "../../custom_components/myhome/translations/en.json";
import italian from "../../custom_components/myhome/translations/it.json";

type Files = typeof english;

const served = (files: Files): Record<string, unknown> => ({
  options: files.options,
  selector: files.selector,
  exceptions: files.exceptions,
  panel: files.config_panel,
});

const speaking = async (language: string, files: Files): Promise<I18n> => {
  const i18n = new I18n();
  await i18n.load(
    {
      sendMessagePromise: async () =>
        ({ language, requested: language, fallback: false, texts: served(files) }) as never,
      subscribeMessage: async () => async () => undefined,
    } as unknown as HaConnection,
    language,
  );
  return i18n;
};

const it_it = await speaking("it", italian as unknown as Files);
const en_gb = await speaking("en", english);

const scenarios = fixture.scenarios as unknown as Record<string, SessionSnapshot>;

const context = (i18n: I18n, over: Partial<WizardContext> = {}): WizardContext => ({
  i18n,
  now: Date.parse("2026-09-18T10:01:16.000+00:00"),
  skewMs: 0,
  typed: null,
  position: null,
  readOnly: false,
  showAll: false,
  showAffected: false,
  cue: true,
  selected: null,
  profiles: [],
  stepperOpen: false,
  ...over,
});

const stepperOf = (name: string, over: Partial<WizardContext> = {}, i18n: I18n = en_gb) =>
  screenModel(scenarios[name], context(i18n, over)).stepper;

/**
 * A plan that goes through its phases once each, which is what a route walked straight
 * through looks like: the thorough calibration is the one that does not, because the plan
 * is rewritten when the reader presses "Continue with the thorough calibration".
 */
const straight = (snapshot: SessionSnapshot): boolean => {
  const seen = new Map<string, number>();
  let last = "";
  for (let at = 0; at < snapshot.plan.length; at += 1) {
    const phase = currentPhase({ ...snapshot, plan_index: at } as SessionSnapshot) ?? "";
    if (phase !== last && seen.has(phase)) {
      return false;
    }
    seen.set(phase, at);
    last = phase;
  }
  return true;
};

/** Every row with a state, as one string, so a whole rail can be asserted in one line. */
const shapeOf = (name: string) =>
  (stepperOf(name)?.rows ?? []).map((row) => `${row.sub ? "  " : ""}${row.id}:${row.state}`);

describe("which screens carry the stepper at all", () => {
  it("draws it on every step the plan knows about", () => {
    for (const name of ["briefing_open_brief", "awaiting_reading_measure_descent", "review_basic"]) {
      assert.ok(stepperOf(name), `${name} has no stepper`);
    }
  });

  it("draws none before a route has been chosen, because there is no plan yet", () => {
    // `path`, `path_b`, `path_c` and `refine_scope` all arrive with `plan: []`: the plan is
    // what the route decides, so a stepper here would have to invent its own list of six.
    for (const name of [
      "armed_path",
      "armed_path_b_profile_choice",
      "armed_path_c_profile_choice",
      "armed_refine_scope_intent",
    ]) {
      assert.equal(stepperOf(name), undefined, `${name} drew a stepper with no plan behind it`);
    }
  });

  it("draws none on a problem, which interrupted a stage the snapshot does not name", () => {
    for (const name of ["problem_no_echo", "problem_interrupted"]) {
      assert.equal(stepperOf(name), undefined);
    }
  });

  it("draws none on an outcome, which is the end of the work and not a place in it", () => {
    for (const name of ["saved_profile", "saved_cover_only", "ended_cancelled", "ended_expired"]) {
      assert.equal(stepperOf(name), undefined);
    }
  });
});

describe("the six phases", () => {
  it("names all six, always, in the one order the header counts in", () => {
    for (const [name, snapshot] of Object.entries(scenarios)) {
      const stepper = stepperOf(name);
      if (!stepper) {
        continue;
      }
      const phases = stepper.rows.filter((row) => !row.sub).map((row) => row.id);
      assert.deepEqual(phases, [...PHASES], `${name} (plan of ${snapshot.plan.length})`);
      assert.equal(stepper.dots.length, PHASES.length);
    }
  });

  it("marks the phases a route does not do as skipped, and never hides one", () => {
    // Route (C), a correction of the times: no tape readings at all. The row stays, says so,
    // and is the reason a reader counting to six finds six.
    const rows = new Map((stepperOf("review_correction")?.rows ?? []).map((r) => [r.id, r]));
    assert.equal(rows.get("readings")?.state, "skipped");
    assert.equal(rows.get("readings")?.meta, en_gb.t("panel.wizard.stepper.not_on_route"));
    // …and route (B), which skips three of them.
    const b = new Map((stepperOf("briefing_verify_offer")?.rows ?? []).map((r) => [r.id, r]));
    for (const phase of ["prepare", "ascent", "descent"]) {
      assert.equal(b.get(phase)?.state, "skipped", phase);
    }
    assert.equal(b.get("readings")?.state, "current");
  });

  it("says which route was taken beside the first phase", () => {
    const rows = stepperOf("briefing_open_brief")?.rows ?? [];
    assert.equal(rows[0]?.id, "route");
    assert.equal(rows[0]?.state, "done");
    assert.equal(rows[0]?.meta, en_gb.t("panel.wizard.stepper.route.path_a"));
    assert.equal(
      (stepperOf("briefing_verify_offer")?.rows ?? [])[0]?.meta,
      en_gb.t("panel.wizard.stepper.route.path_b"),
    );
  });

  it("puts the value a finished phase produced beside it", () => {
    const rows = new Map((stepperOf("awaiting_reading_measure_descent")?.rows ?? []).map((r) => [r.id, r]));
    const snapshot = scenarios.awaiting_reading_measure_descent;
    // The ascent carries the curtain travel, which is what the design writes there: the
    // reading is taken at the top the moment the timed run ends.
    assert.equal(
      rows.get("ascent")?.meta,
      en_gb.t("panel.wizard.stepper.value", {
        key: valueLabel("travel_cm", en_gb),
        value: valueLine("travel_cm", snapshot.measured.travel_cm, en_gb),
      }),
    );
    assert.equal(
      rows.get("descent")?.meta,
      en_gb.t("panel.wizard.stepper.value", {
        key: valueLabel("closing_time_s", en_gb),
        value: valueLine("closing_time_s", snapshot.measured.closing_time_s, en_gb),
      }),
    );
    // …and the preparation produced no number, so it carries none rather than a restatement
    // of its own name.
    assert.equal(rows.get("prepare")?.meta, undefined);
  });
});

describe("the phase the session is in", () => {
  it("never goes backwards while a route is walked straight through", () => {
    // The defect this exists for: read off `steps.ts` alone, route (A) counted 2, 3, **5**,
    // 4, 5, 6, because the curtain travel is a tape reading taken in the middle of the
    // ascent. The stepper reads the plan instead, so the number only ever grows.
    //
    // A thorough calibration is the one plan that really does go back - the reader saw the
    // review, pressed "Continue with the thorough calibration", and is taking readings again
    // - so it is excluded by what it is rather than by name: a plan whose phases are
    // interleaved is one that was rewritten in the middle.
    for (const [name, snapshot] of Object.entries(scenarios)) {
      if (snapshot.plan.length === 0 || !straight(snapshot)) {
        continue;
      }
      let highest = -1;
      for (let at = 0; at < snapshot.plan.length; at += 1) {
        const phase = currentPhase({ ...snapshot, plan_index: at } as SessionSnapshot);
        if (phase === null) {
          continue;
        }
        const index = PHASES.indexOf(phase);
        assert.ok(
          index >= highest,
          `${name}: stage ${at} (${snapshot.plan[at]}) goes back to ${phase}`,
        );
        highest = index;
      }
    }
  });

  it("never draws a finished phase under the one in hand, on any plan at all", () => {
    // Including the thorough one: whatever the plan did, what the rail shows has to read
    // top to bottom - everything behind, then where the reader is, then everything ahead.
    for (const [name] of Object.entries(scenarios)) {
      const rows = (stepperOf(name)?.rows ?? []).filter((row) => !row.sub);
      const here = rows.findIndex((row) => row.state === "current" || row.state === "error");
      if (here < 0) {
        continue;
      }
      for (const [at, row] of rows.entries()) {
        if (row.state === "skipped") {
          continue;
        }
        assert.equal(
          row.state === "done",
          at < here,
          `${name}: ${row.id} is ${row.state} at ${at}, and the phase in hand is at ${here}`,
        );
      }
    }
  });

  it("gives the curtain travel to the ascent on route (A) and to the readings on (B)", () => {
    const a = scenarios.awaiting_reading_measure_descent;
    assert.equal(
      currentPhase({ ...a, plan_index: a.plan.indexOf("height_read") } as SessionSnapshot),
      "ascent",
    );
    const b = scenarios.briefing_verify_offer;
    assert.equal(
      currentPhase({ ...b, plan_index: b.plan.indexOf("height_read") } as SessionSnapshot),
      "readings",
    );
  });

  it("agrees with the one row that is marked current", () => {
    for (const [name] of Object.entries(scenarios)) {
      const stepper = stepperOf(name);
      if (!stepper) {
        continue;
      }
      const marked = stepper.rows.filter((row) => !row.sub && (row.state === "current" || row.state === "error"));
      assert.equal(marked.length, 1, `${name} marks ${marked.length} phases`);
      assert.ok(stepper.here.includes(en_gb.t(`panel.wizard.phase.${marked[0].id}`)), name);
    }
  });
});

describe("the sub-steps of the phase in hand", () => {
  it("opens only the phase in hand, and only when it has more than one stage", () => {
    for (const [name] of Object.entries(scenarios)) {
      const stepper = stepperOf(name);
      if (!stepper) {
        continue;
      }
      let under: string | null = null;
      for (const row of stepper.rows) {
        if (!row.sub) {
          under = row.state === "current" || row.state === "error" ? row.id : null;
          continue;
        }
        assert.ok(under !== null, `${name}: a sub-step under a phase that is not in hand`);
        assert.ok(row.id.startsWith(`${under}/`), `${name}: ${row.id} is not under ${under}`);
      }
    }
  });

  it("walks the stages of that phase, done behind and waiting ahead", () => {
    assert.deepEqual(shapeOf("awaiting_reading_measure_descent"), [
      "route:done",
      "prepare:done",
      "ascent:done",
      "descent:done",
      "readings:current",
      "  readings/4:done",
      "  readings/5:done",
      "  readings/6:current",
      "summary:future",
    ]);
  });

  it("puts the number a reading read beside it, out of the points the flow took", () => {
    const snapshot = scenarios.awaiting_reading_measure_descent;
    // `half_up` is stage 5 of that plan and the first upward reading in it, so its number is
    // the first point of `measured.ascent` - and nothing else could be.
    const row = (stepperOf("awaiting_reading_measure_descent")?.rows ?? []).find(
      (one) => one.id === "readings/5",
    );
    assert.equal(row?.meta, `${en_gb.number(snapshot.measured.ascent[0][1], 1)} cm`);
  });

  it("leaves a reading that has not been taken without a number", () => {
    const row = (stepperOf("positioning_tape_run")?.rows ?? []).find((one) => one.sub && one.state === "current");
    assert.equal(row?.meta, undefined);
  });
});

describe("a reading that came out wrong", () => {
  it("marks the stage and the phase, and says the row has to be done again", () => {
    for (const name of [
      "awaiting_reading_measure_descent_error",
      "awaiting_reading_measure_descent_stale",
    ]) {
      const rows = stepperOf(name)?.rows ?? [];
      const phase = rows.find((one) => one.id === "readings");
      assert.equal(phase?.state, "error", name);
      const stage = rows.find((one) => one.id === "readings/6");
      assert.equal(stage?.state, "error", name);
      assert.equal(stage?.meta, en_gb.t("panel.wizard.stepper.state.error"), name);
    }
  });

  it("leaves the rest of the rail exactly as it was", () => {
    const wrong = shapeOf("awaiting_reading_measure_descent_error").map((row) =>
      row.replace(":error", ":current"),
    );
    assert.deepEqual(wrong, shapeOf("awaiting_reading_measure_descent"));
  });
});

describe("what can be pressed, and what only looks like it", () => {
  it("offers nothing at all on a screen whose session offers no verb that repeats a stage", () => {
    for (const [name] of Object.entries(scenarios)) {
      const stepper = stepperOf(name);
      if (!stepper) {
        continue;
      }
      const pressable = stepper.rows.filter((row) => row.action !== undefined);
      const offered =
        scenarios[name].actions.includes("repeat_tape") ||
        scenarios[name].actions.includes("repeat_measure");
      assert.ok(
        pressable.length <= 1,
        `${name} made ${pressable.length} rows pressable`,
      );
      if (!offered) {
        assert.equal(pressable.length, 0, `${name} made a row pressable with no verb behind it`);
      }
    }
  });

  it("makes the stage the verb would act on pressable, and sends that verb", () => {
    const rows = stepperOf("awaiting_reading_measure_descent_stale")?.rows ?? [];
    const pressable = rows.filter((row) => row.action !== undefined);
    assert.equal(pressable.length, 1);
    // The stage the session is standing on, which is the one `repeat_tape` repeats.
    assert.equal(pressable[0].id, `readings/${scenarios.awaiting_reading_measure_descent_stale.plan_index}`);
    assert.equal(pressable[0].action, "act:repeat_tape");
    // …named with the words of the verb itself, so pressing the row and pressing the button
    // under the field are visibly the same act.
    assert.ok((pressable[0].actionLabel ?? "").length > 0);
  });

  it("never makes a phase pressable, whatever is offered", () => {
    for (const [name] of Object.entries(scenarios)) {
      for (const row of stepperOf(name)?.rows ?? []) {
        if (!row.sub) {
          assert.equal(row.action, undefined, `${name}: the phase ${row.id} can be pressed`);
        }
      }
    }
  });

  it("never makes a timed run pressable: repeating one throws the times away", () => {
    // The stages that are runs rather than readings, on every example of the fixture.
    const runs = new Set(["home_closed", "open_timed", "close_timed", "tape_brief", "verify_offer", "profile_name", "summary"]);
    for (const [name, snapshot] of Object.entries(scenarios)) {
      for (const row of stepperOf(name)?.rows ?? []) {
        if (!row.sub || row.action === undefined) {
          continue;
        }
        const at = Number.parseInt(row.id.split("/")[1] ?? "", 10);
        assert.ok(!runs.has(snapshot.plan[at]), `${name}: ${snapshot.plan[at]} can be repeated`);
      }
    }
  });

  it("takes every action away when somebody else is driving", () => {
    const rows = stepperOf("awaiting_reading_measure_descent_stale", { readOnly: true })?.rows ?? [];
    assert.equal(rows.filter((row) => row.action !== undefined).length, 0);
    // …and the rows themselves are still all there: the stepper is what a reader standing in
    // front of somebody else's shutter is looking at.
    assert.equal(rows.length, (stepperOf("awaiting_reading_measure_descent_stale")?.rows ?? []).length);
  });
});

describe("the collapsible row", () => {
  it("carries the same line the header does, and one dot per phase", () => {
    const stepper = stepperOf("awaiting_reading_measure_descent");
    assert.equal(
      stepper?.here,
      en_gb.t("panel.screen.phase", {
        phase: en_gb.t("panel.wizard.phase.readings"),
        index: 5,
        count: 6,
      }),
    );
    assert.deepEqual(
      stepper?.dots,
      (stepper?.rows ?? []).filter((row) => !row.sub).map((row) => row.state),
    );
  });

  it("is shut unless this tab opened it, and says which it is", () => {
    assert.equal(stepperOf("awaiting_reading_measure_descent")?.open, false);
    assert.equal(stepperOf("awaiting_reading_measure_descent", { stepperOpen: true })?.open, true);
  });

  it("remembers the answer for the session, and survives a storage that refuses", () => {
    const store = new Map<string, string>();
    const shelf = {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => void store.set(key, value),
    };
    assert.equal(readStepperOpen(shelf), false);
    writeStepperOpen(true, shelf);
    assert.equal(readStepperOpen(shelf), true);
    writeStepperOpen(false, shelf);
    assert.equal(readStepperOpen(shelf), false);
    const broken = {
      getItem: () => {
        throw new Error("no storage in a private window");
      },
      setItem: () => {
        throw new Error("no storage in a private window");
      },
    };
    assert.equal(readStepperOpen(broken), false);
    assert.doesNotThrow(() => writeStepperOpen(true, broken));
  });
});

describe("the words", () => {
  it("asks for no key the files do not have, in either language", () => {
    for (const i18n of [en_gb, it_it]) {
      for (const [name] of Object.entries(scenarios)) {
        const stepper = stepperOf(name, {}, i18n);
        if (!stepper) {
          continue;
        }
        for (const said of [
          stepper.label,
          stepper.here,
          ...stepper.rows.flatMap((row) => [row.label, row.stateLabel, row.meta ?? ""]),
        ]) {
          assert.ok(!/^panel\.[a-z_.]+$/u.test(said), `${name}: '${said}' is a key and not a word`);
          assert.ok(!/\{[a-z_]+\}/u.test(said), `${name}: '${said}' still has a hole in it`);
        }
      }
    }
  });

  it("gives every row a state in words, for a reader who cannot see the circle", () => {
    for (const row of stepperOf("briefing_verify_offer", {}, it_it)?.rows ?? []) {
      assert.ok(row.stateLabel.length > 0, row.id);
    }
  });
});
