// Where the calibration has got to, built out of the plan the snapshot already carries.
//
// Live finding 29 asked for a view of the passages: the ones behind ticked, the one in hand
// picked out, the ones ahead waiting. The design (`PoC Stepper Lettura.dc.html`) draws it as
// a 250 px column on a wide screen and as one collapsible row on a phone, and names six
// phases for route (A): Route · Preparation · Ascent · Descent · Tape readings · Review.
//
// **It invents nothing.** Every row here is a stage of `session.plan` - the dialog's own
// list of what this route will do - and every value beside a row is one of `measured`.
// There is no second table of steps to keep in step with the backend: a route that gains a
// stage gains a row, and a route that has no ascent says so instead of pretending.
//
// **The six phases are fixed and always all shown** (SPEC decision 21's order, which is
// `steps.ts`'s `PHASES`). A phase with no stage of it in the plan is *skipped*, with the
// dashed circle the design gives that state: on a correction of the times only, "Tape
// readings · not part of this route" is the sentence that explains why the run is short,
// and a phase that vanished would leave the reader counting to six and finding four.
//
// **The travel of the curtain belongs to whatever brought the shutter to the end stop it is
// measured from.** `height_read` is a tape reading, and on route (A) it is taken at the top
// the moment the timed ascent ends - which is why the design writes "Ascent · curtain travel
// 110 cm" and not a second visit to the readings. On route (B) nothing is timed and the same
// stage follows the briefing of the readings, where it belongs. So its phase is the phase of
// the stage before it, and `readings` when it opens a plan. That one rule is also what makes
// the phase counter monotone: read off `steps.ts` alone, route (A) counted 2, 3, **5**, 4, 5,
// 6, because the table gives every step one fixed phase and the same step sits at different
// points of different plans.
//
// **Nothing here is a road back.** The contract has no verb that repeats an arbitrary past
// stage: `repeat_tape` repeats the tape reading the session is standing on, `repeat_measure`
// the curtain travel. So exactly one row can ever be pressed - the stage at `plan_index`,
// and only while the matching verb is in `actions` - and pressing it sends that verb and
// nothing else. Every other row is a label with no control in it (SPEC §5.7: a row that
// looks pressable and does nothing is worse than a row that does not look pressable).

import { type I18n } from "../engine/i18n";
import { type ScreenStepper, type ScreenStepState, type ScreenStepperStep } from "../engine/screen";
import {
  type SessionAction,
  type SessionPath,
  type SessionPlanStage,
  type SessionSnapshot,
} from "../engine/session-contract";
import { withUnit } from "../engine/fields";
import { valueLabel, valueLine } from "./format";
import { PHASES, PHASE_KEY, STEPS, type WizardPhase } from "./steps";

/** The token the collapsible row fires; `views/wizard.ts` turns it into a repaint. */
export const STEPPER = "stepper";

/** Where the collapsible row's state is remembered: this tab, this session, and no further. */
export const STEPPER_KEY = "myhome-calibration-stepper";

/** What the panel holds of `sessionStorage`, so nothing here needs a window. */
export interface StepperStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

const defaultStore = (): StepperStore | null => {
  try {
    return (globalThis as { sessionStorage?: StepperStore }).sessionStorage ?? null;
  } catch {
    // Safari in a private window throws on the property itself, not on the read.
    return null;
  }
};

/**
 * Shut unless this tab opened it.
 *
 * The design's rule: closed by default, because the row sits above the step and the step is
 * what the reader came for. It is remembered for the session and not for the browser - it is
 * a thing about *this* calibration, and a phone that opened it once should not open it for
 * every calibration for ever.
 */
export const readStepperOpen = (store: StepperStore | null = defaultStore()): boolean => {
  try {
    return store?.getItem(STEPPER_KEY) === "open";
  } catch {
    return false;
  }
};

export const writeStepperOpen = (
  open: boolean,
  store: StepperStore | null = defaultStore(),
): void => {
  try {
    store?.setItem(STEPPER_KEY, open ? "open" : "shut");
  } catch {
    // Unwritable: the row works for this page and is shut again on the next one, which is a
    // smaller loss than a screen that cannot be drawn.
  }
};

/**
 * Which phase each stage of a plan belongs to.
 *
 * Written out rather than derived from `STEPS`, because the two answer different questions:
 * `STEPS[step].phase` is "what does the header of this screen say", one fixed answer per
 * step, and this is "which block of the work is this stage part of", which is what an order
 * of six phases needs. They agree everywhere except `height_read`, which has no fixed answer
 * - see the note at the top and `phaseOfStage` below.
 */
const STAGE_PHASE: Readonly<Record<SessionPlanStage, WizardPhase>> = {
  home_closed: "prepare",
  open_timed: "ascent",
  // Resolved by `phaseOfStage`; this is the answer for a plan that opens with it.
  height_read: "readings",
  close_timed: "descent",
  tape_brief: "readings",
  half_down: "readings",
  half_up: "readings",
  quarter_down: "readings",
  three_quarter_down: "readings",
  quarter_up: "readings",
  three_quarter_up: "readings",
  verify: "readings",
  verify_b: "readings",
  verify_offer: "readings",
  profile_name: "summary",
  summary: "summary",
};

/**
 * The name of one stage, key by key.
 *
 * `tests/test_translations.py` reads the keys this bundle asks for out of its double-quoted
 * string literals, so every one of them is written here rather than assembled - the same
 * reason `steps.ts` writes out `PHASE_KEY`. The six readings at a fraction are the exception
 * and are not in the map at all: their name is the fraction and the direction, which are in
 * the identifier itself, so they take one key per direction and carry the per cent as a
 * number (`READING_KEY` below).
 */
const STAGE_KEY: Readonly<Partial<Record<SessionPlanStage, string>>> = {
  home_closed: "panel.wizard.stepper.stage.home_closed",
  open_timed: "panel.wizard.stepper.stage.open_timed",
  height_read: "panel.wizard.stepper.stage.height_read",
  close_timed: "panel.wizard.stepper.stage.close_timed",
  tape_brief: "panel.wizard.stepper.stage.tape_brief",
  verify: "panel.wizard.stepper.stage.verify",
  verify_b: "panel.wizard.stepper.stage.verify",
  verify_offer: "panel.wizard.stepper.stage.verify_offer",
  profile_name: "panel.wizard.stepper.stage.profile_name",
  summary: "panel.wizard.stepper.stage.summary",
};

/** The readings at a fraction: how far along, and which way the shutter was going. */
const READING: Readonly<Partial<Record<SessionPlanStage, { percent: number; way: "up" | "down" }>>> =
  {
    half_down: { percent: 50, way: "down" },
    half_up: { percent: 50, way: "up" },
    quarter_down: { percent: 25, way: "down" },
    three_quarter_down: { percent: 75, way: "down" },
    quarter_up: { percent: 25, way: "up" },
    three_quarter_up: { percent: 75, way: "up" },
  };

/**
 * Which route was taken, said as the lexicon says it: the letter, in brackets.
 *
 * Three keys and not one with the letter substituted in, because the letter is part of the
 * name of the route ("percorso (A)") and not a value the panel formats - and because
 * `tests/test_translations.py` keeps the panel\'s substitutions to a list of names that
 * mean something, which a bare letter is not one of.
 */
const ROUTE_KEY: Readonly<Record<SessionPath, string>> = {
  path_a: "panel.wizard.stepper.route.path_a",
  path_b: "panel.wizard.stepper.route.path_b",
  path_c: "panel.wizard.stepper.route.path_c",
};

const READING_KEY = {
  down: "panel.wizard.stepper.reading_down",
  up: "panel.wizard.stepper.reading_up",
} as const;

/** The word for a state, said in the row's own name so a reader hears it with the row. */
const STATE_KEY: Readonly<Record<ScreenStepState, string>> = {
  done: "panel.wizard.stepper.state.done",
  current: "panel.wizard.stepper.state.current",
  future: "panel.wizard.stepper.state.future",
  skipped: "panel.wizard.stepper.state.skipped",
  error: "panel.wizard.stepper.state.error",
};

/**
 * Which verb, if any, repeats a given stage.
 *
 * The two the contract has, and no third: a tape reading at a fraction and the verification
 * are repeated with `repeat_tape`, the curtain travel with `repeat_measure`. The timed runs
 * are deliberately absent - repeating one throws away the times already registered, and the
 * way to do it is "It did not do what it should" inside the step or "Correct…" after the
 * save (the design's own rule, and live finding 29's "le corse no").
 */
const REPEAT: Readonly<Partial<Record<SessionPlanStage, SessionAction>>> = {
  height_read: "repeat_measure",
  half_down: "repeat_tape",
  half_up: "repeat_tape",
  quarter_down: "repeat_tape",
  three_quarter_down: "repeat_tape",
  quarter_up: "repeat_tape",
  three_quarter_up: "repeat_tape",
  verify: "repeat_tape",
  verify_b: "repeat_tape",
};

/** The phase of one stage of a plan, with `height_read` resolved by what came before it. */
const phaseOfStage = (plan: readonly SessionPlanStage[], at: number): WizardPhase => {
  const stage = plan[at];
  if (stage === "height_read" && at > 0) {
    return phaseOfStage(plan, at - 1);
  }
  return STAGE_PHASE[stage] ?? "readings";
};

/**
 * Which phase the session is in, out of the plan - the header's line and the stepper's
 * highlight, from one place.
 *
 * `null` when there is no plan to read (the route is still being chosen) or when the step
 * itself refuses a phase: the `problem_*` steps carry none, because a problem can interrupt
 * any stage and a header naming the wrong one is worse than a header naming none.
 */
export const currentPhase = (session: SessionSnapshot | null): WizardPhase | null => {
  const step = session?.step;
  if (!session || !step) {
    return null;
  }
  const row = STEPS[step];
  if (!row?.phase) {
    return null;
  }
  const at = session.plan_index;
  if (at === null || at < 0 || at >= session.plan.length) {
    return row.phase;
  }
  return phaseOfStage(session.plan, at);
};

/** The name of one stage, and the per cent when the stage is a reading at a fraction. */
const stageLabel = (stage: SessionPlanStage, i18n: I18n): string => {
  const reading = READING[stage];
  if (reading) {
    return i18n.t(READING_KEY[reading.way], { percent: i18n.number(reading.percent, 0) });
  }
  const key = STAGE_KEY[stage];
  return key ? i18n.t(key) : stage;
};

/**
 * What a reading of a fraction read, when it has already been read.
 *
 * `measured.descent` and `measured.ascent` are the points in the order they were taken, and
 * the order they were taken in is the order the plan lists them: the *n*-th downward stage of
 * the plan is the *n*-th point of `descent`. A point that is not there yet - the stage is the
 * one being read, or was repeated and is waiting - simply has no number beside it, which is
 * the only safe answer: a number beside the wrong row is worse than no number at all.
 */
const readingValue = (
  session: SessionSnapshot,
  plan: readonly SessionPlanStage[],
  at: number,
  i18n: I18n,
): string | null => {
  const reading = READING[plan[at]];
  if (!reading) {
    return null;
  }
  let ordinal = 0;
  for (let before = 0; before < at; before += 1) {
    if (READING[plan[before]]?.way === reading.way) {
      ordinal += 1;
    }
  }
  const points = reading.way === "down" ? session.measured.descent : session.measured.ascent;
  const point = points[ordinal];
  return point === undefined ? null : centimetres(point[1], i18n);
};

/**
 * A tape reading, with the one decimal it was taken to.
 *
 * Not `valueLine("travel_cm", …)`: the travel of the curtain is written with no decimals,
 * because it is a length of wall, and a reading is written with one, because it is a
 * measurement the model is fitted through. They are the same unit and two different
 * precisions - `format.ts`'s own `PLACEHOLDER_DECIMALS` says so for `measured` too.
 */
const centimetres = (value: number, i18n: I18n): string =>
  withUnit(i18n.number(value, 1), i18n.t("panel.common.unit.centimetres"));

/** …and the same for the two stages that are not readings at a fraction. */
const stageValue = (
  session: SessionSnapshot,
  plan: readonly SessionPlanStage[],
  at: number,
  i18n: I18n,
): string | null => {
  const stage = plan[at];
  if (stage === "height_read") {
    return session.measured.travel_measured && session.measured.travel_cm !== null
      ? valueLine("travel_cm", session.measured.travel_cm, i18n)
      : null;
  }
  if (stage === "verify" || stage === "verify_b") {
    return session.check ? centimetres(session.check.measured_cm, i18n) : null;
  }
  return readingValue(session, plan, at, i18n);
};

/** A value with the name of what it is, the way the review writes one: "Travel · 110 cm". */
const named = (key: "travel_cm" | "opening_time_s" | "closing_time_s", value: number, i18n: I18n) =>
  i18n.t("panel.wizard.stepper.value", {
    key: valueLabel(key, i18n),
    value: valueLine(key, value, i18n),
  });

/** The one line a finished phase carries: what it produced, when it produced a number. */
const phaseValue = (
  session: SessionSnapshot,
  phase: WizardPhase,
  stages: readonly number[],
  i18n: I18n,
): string | null => {
  const measured = session.measured;
  if (phase === "route") {
    return session.path === null ? null : i18n.t(ROUTE_KEY[session.path]);
  }
  if (phase === "ascent") {
    const travels = stages.some((at) => session.plan[at] === "height_read");
    if (travels && measured.travel_measured && measured.travel_cm !== null) {
      return named("travel_cm", measured.travel_cm, i18n);
    }
    return measured.opening_time_s === null
      ? null
      : named("opening_time_s", measured.opening_time_s, i18n);
  }
  if (phase === "descent") {
    return measured.closing_time_s === null
      ? null
      : named("closing_time_s", measured.closing_time_s, i18n);
  }
  return null;
};

/**
 * Whether the stage being stood on came out wrong.
 *
 * Two things can be wrong with a reading and both of them are in the snapshot: the flow
 * refused the number (`form.error`) and the shutter moved under it, which makes what was
 * read no longer true (`notice: "reading_stale"`).
 *
 * **Whether, and not what.** The design writes the reason beside the row ("250 cm - out of
 * range"); the reasons this flow really has are the dialog's own sentences, two and three
 * lines of them ("It is more than the whole travel of this curtain. Measure from the point
 * where the bottom edge rests…"), and a 250 px rail is not where a paragraph goes. The row
 * says "to be done again" and turns red; the sentence is in the field's own error and in
 * the note, one column away on the same screen.
 */
const wrongHere = (session: SessionSnapshot): boolean =>
  session.notice === "reading_stale" || (session.form?.error ?? null) !== null;

const row = (
  id: string,
  label: string,
  state: ScreenStepState,
  meta: string | null,
  i18n: I18n,
  more: Partial<ScreenStepperStep> = {},
): ScreenStepperStep => ({
  id,
  label,
  state,
  stateLabel: i18n.t(STATE_KEY[state]),
  ...(meta === null ? {} : { meta }),
  ...more,
});

/** What the view knows and the snapshot does not, for the stepper alone. */
export interface StepperContext {
  i18n: I18n;
  /** The collapsible row, as this tab has it. */
  open: boolean;
  /** Another client is driving: the rows are the same, and none of them acts. */
  readOnly: boolean;
  /** The words of a verb, from the step that offers it or from its lender. */
  label: (action: SessionAction) => string;
  /**
   * The token a verb is fired as.
   *
   * Handed in rather than built here, so that this file never imports `model.ts` - which
   * imports this one. A cycle between the two would be a bundle whose evaluation order
   * decides whether a constant exists, which is a bug that appears on one build and not the
   * next.
   */
  token: (action: SessionAction) => string;
}

/**
 * The whole stepper, or nothing at all.
 *
 * Nothing when there is no plan to draw: the choice of route (the plan does not exist until
 * a route is chosen), a step that carries no phase (the problems), and the outcomes, which
 * are not a step of the work but the end of it.
 */
export const stepperModel = (
  session: SessionSnapshot,
  context: StepperContext,
): ScreenStepper | null => {
  const { i18n } = context;
  const plan = session.plan;
  const here = currentPhase(session);
  if (plan.length === 0 || here === null) {
    return null;
  }
  const at = session.plan_index;
  const wrong = wrongHere(session);
  // Which stages belong to each phase, once, so the states below are arithmetic on indices
  // and never a second walk of the plan.
  const stagesOf = new Map<WizardPhase, number[]>(PHASES.map((phase) => [phase, []]));
  plan.forEach((_stage, index) => {
    stagesOf.get(phaseOfStage(plan, index))?.push(index);
  });
  // The route is not a stage of any plan - the plan is what the route decided - so it is
  // done from the moment there is one.
  stagesOf.set("route", []);

  const rows: ScreenStepperStep[] = [];
  const dots: ScreenStepState[] = [];
  for (const phase of PHASES) {
    const stages = stagesOf.get(phase) ?? [];
    const state: ScreenStepState =
      phase === "route"
        ? "done"
        : stages.length === 0
          ? "skipped"
          : at === null
            ? "future"
            : stages.includes(at)
              ? (wrong ? "error" : "current")
              : Math.max(...stages) < at
                ? "done"
                : "future";
    dots.push(state);
    const meta =
      state === "done"
        ? phaseValue(session, phase, stages, i18n)
        : state === "skipped"
          ? i18n.t("panel.wizard.stepper.not_on_route")
          : state === "current" && stages.length > 1
            ? i18n.t("panel.wizard.stepper.within", {
                index: stages.indexOf(at as number) + 1,
                count: stages.length,
              })
            : null;
    rows.push(row(phase, i18n.t(PHASE_KEY[phase]), state, meta, i18n));
    if (state !== "current" && state !== "error") {
      // The sub-steps of a phase that is not the one in hand are never shown: they are the
      // detail of somewhere the reader is not, and six phases with every stage under them is
      // a list nobody reads (the design's first rule).
      continue;
    }
    if (stages.length < 2) {
      // …and a phase made of one stage has no detail to open: "Descent" with "Timed descent"
      // under it is the same row twice, and the reader learns nothing from the second.
      continue;
    }
    for (const index of stages) {
      const stage = plan[index];
      const own: ScreenStepState =
        at === null || index > at
          ? "future"
          : index < at
            ? "done"
            : wrong
              ? "error"
              : "current";
      const value = own === "done" || own === "error" ? stageValue(session, plan, index, i18n) : null;
      const verb = REPEAT[stage];
      // The one row that can be pressed: the stage the session is standing on, and only
      // while the verb that repeats *it* is being offered. `readOnly` takes it away with
      // every other control on the screen.
      const offered =
        verb !== undefined &&
        !context.readOnly &&
        index === at &&
        session.actions.includes(verb);
      rows.push(
        row(
          `${phase}/${index}`,
          stageLabel(stage, i18n),
          own,
          own === "error" ? i18n.t(STATE_KEY.error) : value,
          i18n,
          {
            sub: true,
            ...(offered && verb !== undefined
              ? { action: context.token(verb), actionLabel: context.label(verb) }
              : {}),
          },
        ),
      );
    }
  }
  // The one row a screen reader is told is the step: the innermost of the rows in hand, so
  // that a phase and the stage inside it are not both announced as where the reader is.
  for (let at = rows.length - 1; at >= 0; at -= 1) {
    if (rows[at].state === "current" || rows[at].state === "error") {
      rows[at].inHand = true;
      break;
    }
  }
  return {
    label: i18n.t("panel.wizard.stepper.label"),
    here: i18n.t("panel.screen.phase", {
      phase: i18n.t(PHASE_KEY[here]),
      index: PHASES.indexOf(here) + 1,
      count: PHASES.length,
    }),
    rows,
    dots,
    open: context.open,
    toggle: STEPPER,
  };
};
