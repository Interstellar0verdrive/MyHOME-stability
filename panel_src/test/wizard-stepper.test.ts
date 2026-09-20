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
import {
  ACT,
  AGAIN,
  CHOOSE,
  CLAIM,
  CLOSE,
  CUE,
  OPEN_COVER,
  PICK,
  SAVE,
  SHOW_AFFECTED,
  SHOW_ALL,
  STOP,
  SUBMIT,
  screenModel,
  type WizardContext,
} from "../src/wizard/model";
import { STEPPER, currentPhase, readStepperOpen, writeStepperOpen } from "../src/wizard/stepper";
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

  it("names the only plan that is not straight, so a new one cannot slip past in silence", () => {
    // The check above excludes the plans whose phases are interleaved, by shape and not by
    // name. Without this, a route that gained two interleaved phases by accident would be
    // excluded in silence and nobody would learn about it.
    const crooked = Object.entries(scenarios)
      .filter(([, snapshot]) => snapshot.plan.length > 0 && !straight(snapshot))
      .map(([name]) => name)
      .sort();
    // The thorough calibration: the reader saw the review, pressed "Continue with the
    // thorough calibration", and the plan was rewritten around a stage already behind them.
    assert.deepEqual(crooked, ["review_precise"]);
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

  it("leaves the rest of the rail exactly as it was, meta included", () => {
    // `shapeOf` used to compare the states alone, and the design's rule for a phase with an
    // error is that the rest of the stepper does not change - which includes the counter
    // under the phase name, and did not (the review's AFF-2).
    const named = (one: string) =>
      (stepperOf(one)?.rows ?? []).map(
        (row) => `${row.sub ? "  " : ""}${row.id}:${row.state}:${row.meta ?? ""}`,
      );
    const right = named("awaiting_reading_measure_descent");
    const wrong = named("awaiting_reading_measure_descent_error");
    assert.equal(wrong.length, right.length);
    for (const [at, line] of wrong.entries()) {
      // The two rows that really are different - the phase and the stage in hand - and
      // nothing else on the rail.
      if (line.includes(":error:")) {
        assert.ok(right[at].includes(":current:"), right[at]);
        continue;
      }
      assert.equal(line, right[at]);
    }
    // …and the counter is one of the things that did not move.
    assert.equal(
      wrong.find((one) => one.startsWith("readings:")),
      `readings:error:${en_gb.t("panel.wizard.stepper.within", { index: 3, count: 3 })}`,
    );
  });
});

describe("what the stepper is not: a control", () => {
  // The design says it in three places - "nessuna azione dallo stepper: nessun passo è
  // cliccabile", "la correzione non passa dallo stepper", "i passi dello stepper non
  // ricevono il focus" - and the independent review of this lot showed why the one
  // exception could not work: a row can only offer a verb the session is already offering,
  // and `model.ts` draws every one of those as a button on the same screen. So the rail was
  // a second way to press a button 700 px to its right, and one more stop for the keyboard.
  it("gives no row an action, on any example of the fixture at any point of its plan", () => {
    for (const [name, snapshot] of Object.entries(scenarios)) {
      for (let at = 0; at < Math.max(1, snapshot.plan.length); at += 1) {
        const stepper = screenModel(
          { ...snapshot, plan_index: snapshot.plan.length === 0 ? snapshot.plan_index : at },
          context(en_gb),
        ).stepper;
        for (const row of stepper?.rows ?? []) {
          assert.deepEqual(
            Object.keys(row).filter((key) => key === "action" || key === "actionLabel"),
            [],
            `${name}@${at}: ${row.id} carries an action`,
          );
        }
      }
    }
  });

  it("gives no row an action even where a verb that repeats a stage is being offered", () => {
    // The four states the review found, where `repeat_tape` really is in `actions`.
    for (const name of [
      "awaiting_reading_measure_descent_stale",
      "checking_verify_result_within",
      "checking_verify_result_offers_c",
    ]) {
      assert.ok(
        scenarios[name].actions.includes("repeat_tape"),
        `${name} no longer offers the verb this test is about`,
      );
      const rows = stepperOf(name)?.rows ?? [];
      assert.ok(rows.length > 0, name);
      for (const row of rows) {
        assert.equal("action" in row, false, `${name}: ${row.id}`);
      }
    }
  });

  it("draws the same rows whoever is driving, because none of them acts", () => {
    const mine = stepperOf("awaiting_reading_measure_descent_stale");
    const theirs = stepperOf("awaiting_reading_measure_descent_stale", { readOnly: true });
    assert.deepEqual(theirs, mine);
  });
});

describe("a plan with no place in it", () => {
  // RIS-1 of the review. Not producible by today's controller, and not written down as an
  // invariant either: `plan_index` is `number | null` and the API document says nothing, so
  // the rail refuses to draw rather than losing the reader's place in silence.
  const lost = (over: Partial<SessionSnapshot>) =>
    screenModel({ ...scenarios.awaiting_reading_measure_descent, ...over } as SessionSnapshot,
      context(en_gb)).stepper;

  it("draws nothing when the plan has no index into it", () => {
    assert.equal(lost({ plan_index: null }), undefined);
  });

  it("draws nothing when the index is past the end of the plan", () => {
    const plan = scenarios.awaiting_reading_measure_descent.plan;
    assert.equal(lost({ plan_index: plan.length }), undefined);
    assert.equal(lost({ plan_index: plan.length + 4 }), undefined);
    assert.equal(lost({ plan_index: -1 }), undefined);
  });

  it("never draws a rail with nothing in hand", () => {
    // The rule the two above exist for, asserted over everything the fixture can produce.
    for (const [name, snapshot] of Object.entries(scenarios)) {
      for (const at of [null, -1, 0, snapshot.plan.length, snapshot.plan.length + 1]) {
        const stepper = screenModel({ ...snapshot, plan_index: at } as SessionSnapshot, context(en_gb))
          .stepper;
        if (!stepper) {
          continue;
        }
        assert.equal(
          stepper.rows.filter((row) => row.inHand).length,
          1,
          `${name}@${at}: the rail has no row in hand`,
        );
      }
    }
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

describe("the token the collapsible row fires", () => {
  it("is not one of the screen's other tokens", () => {
    // `STEPPER` is the one token declared outside the block in `wizard/model.ts`, because
    // `stepper.ts` may not import that file (`model.ts` imports this one). Nothing made the
    // set distinct; this does (the review's AFF-10).
    const tokens = [ACT, SAVE, PICK, SUBMIT, STOP, CLAIM, CUE, CHOOSE, SHOW_ALL, SHOW_AFFECTED,
      AGAIN, OPEN_COVER, CLOSE, STEPPER];
    assert.equal(new Set(tokens).size, tokens.length);
    // …and no token is a prefix of another, because `views/wizard.ts` dispatches some of
    // them with `startsWith`.
    for (const one of tokens) {
      for (const other of tokens) {
        if (one === other) {
          continue;
        }
        assert.equal(other.startsWith(one), false, `'${other}' starts with '${one}'`);
      }
    }
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
