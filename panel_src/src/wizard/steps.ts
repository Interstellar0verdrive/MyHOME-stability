// One row for every step the conversation can stand on, and nothing else in it.
//
// The table is the whole of "which screen is this?": `model.ts` reads a row and builds a
// `ScreenModel` from the snapshot, and no other file decides what a step looks like. It is
// a table and not a `switch` for one reason - `tests/fixtures/panel_session_examples.json`
// carries the list of steps the backend can produce (`_contract.steps`, sixty of them),
// and `test/wizard-model.test.ts` asserts that this file has a row for every one. A
// `switch` with a missing case falls through to a default and ships; a missing row here
// fails a test that names the step.
//
// The four columns are SPEC §5.3's:
//
// * **`template`** - one of the eight `engine/screen.ts` already implements;
// * **`phase`** - which of the six the header names. Fixed per step and not derived from
//   `plan_index`, because the same step appears at different points of different plans and
//   a phase that moved under the reader would say less than no phase at all;
// * **`primary`** - which action is the big button. Left out, it is the first of
//   `actions`, which is the dialog's own order (`menu_options`) and therefore the order
//   somebody chose;
// * **`display`** - the step whose title and prose to show when this one has none of its
//   own. `open_start` is the motor starting: the words are `open_lift`'s, because that is
//   what is about to be asked, and only the motor line says "starting".
//
// Two more flags, both about a movement rather than about words: `cue` marks the screens
// that start a run - they carry the switch for the signal at the start - and `stoppable`
// marks the ones where "Stop the shutter" is offered (SPEC decision 10: the design does
// not draw it, the contract defines it, and a shutter running under a step nobody can
// interrupt is the thing the wall switch exists for).

import { type ScreenTemplate } from "../engine/screen";
import { type SessionAction, type SessionStep } from "../engine/session-contract";

/** The six phases of the header, in the order they are numbered (SPEC decision 21). */
export const PHASES = ["route", "prepare", "ascent", "descent", "readings", "summary"] as const;

export type WizardPhase = (typeof PHASES)[number];

/**
 * The phase names, written out rather than assembled.
 *
 * `tests/test_translations.py` reads the keys this bundle asks for out of its
 * double-quoted string literals, so a key built with a template string is a key with no
 * stand-in beside it and no test behind it.
 */
export const PHASE_KEY: Readonly<Record<WizardPhase, string>> = {
  route: "panel.wizard.phase.route",
  prepare: "panel.wizard.phase.prepare",
  ascent: "panel.wizard.phase.ascent",
  descent: "panel.wizard.phase.descent",
  readings: "panel.wizard.phase.readings",
  summary: "panel.wizard.phase.summary",
};

export interface StepRow {
  template: ScreenTemplate;
  phase: WizardPhase | null;
  /** Which action is the big button; the first of `actions` when this is absent. */
  primary?: SessionAction;
  /** Whose title and prose to show, when this step has none of its own. */
  display?: SessionStep;
  /** The motor's state on a `click` screen: this step is one of the three moments. */
  press?: "starting" | "moving" | "registered";
  /** This screen starts a run, so it carries the switch for the signal at the start. */
  cue?: boolean;
  /** Something of this session's is moving: "Stop the shutter" is offered. */
  stoppable?: boolean;
  /** The texts are the panel's own, because the dialog's speak of the dialog. */
  own?: boolean;
}

/**
 * Every step of `_contract.steps`, in the order the contract lists them.
 *
 * The `problem_*` steps carry no phase: a problem can interrupt any stage, the snapshot
 * does not say which one it interrupted, and a header naming the wrong phase is worse
 * than a header naming none.
 */
export const STEPS: Readonly<Record<SessionStep, StepRow>> = {
  // --- the route ------------------------------------------------------------------------
  path: { template: "scelta", phase: "route" },
  path_a: { template: "lettura", phase: "prepare" },
  path_b: { template: "scelta", phase: "route" },
  path_c: { template: "scelta", phase: "route" },
  refine_scope: { template: "scelta", phase: "route" },

  // --- getting the shutter to a known place ----------------------------------------------
  home_closed: { template: "pos", phase: "prepare", stoppable: true },
  home_closed_done: { template: "controllo", phase: "prepare" },

  // --- the ascent, in two runs and two presses -------------------------------------------
  open_timed: { template: "pos", phase: "ascent", stoppable: true },
  open_brief: { template: "lettura", phase: "ascent", cue: true },
  open_start: { template: "click", phase: "ascent", display: "open_lift", press: "starting", stoppable: true },
  open_lift: { template: "click", phase: "ascent", press: "moving", stoppable: true },
  lift_stop: { template: "click", phase: "ascent", display: "open_lift", press: "registered" },
  lift_check: { template: "controllo", phase: "ascent" },
  lift_check_late: { template: "controllo", phase: "ascent", display: "lift_check" },
  lift_gap: { template: "controllo", phase: "ascent" },
  lift_early: { template: "controllo", phase: "ascent" },
  open_home_again: { template: "pos", phase: "ascent", stoppable: true },
  closed_again: { template: "controllo", phase: "ascent" },
  open_full_brief: { template: "lettura", phase: "ascent", cue: true },
  open_full_start: { template: "click", phase: "ascent", display: "open_top", press: "starting", stoppable: true },
  open_top: { template: "click", phase: "ascent", press: "moving", stoppable: true },
  open_result: { template: "lettura", phase: "ascent" },
  open_result_gap: { template: "lettura", phase: "ascent" },

  // --- the travel of the curtain, read with the tape --------------------------------------
  height_read: { template: "pos", phase: "readings", stoppable: true },
  height: { template: "metro", phase: "readings" },
  height_result: { template: "lettura", phase: "readings" },

  // --- the descent -------------------------------------------------------------------------
  close_timed: { template: "pos", phase: "descent", stoppable: true },
  close_brief: { template: "lettura", phase: "descent", cue: true },
  close_start: { template: "click", phase: "descent", display: "close_bottom", press: "starting", stoppable: true },
  close_bottom: { template: "click", phase: "descent", press: "moving", stoppable: true },
  close_result: { template: "lettura", phase: "descent" },

  // --- the readings at a fraction of the travel ---------------------------------------------
  tape_brief: { template: "lettura", phase: "readings" },
  half_down: { template: "pos", phase: "readings", stoppable: true },
  half_up: { template: "pos", phase: "readings", stoppable: true },
  quarter_down: { template: "pos", phase: "readings", stoppable: true },
  three_quarter_down: { template: "pos", phase: "readings", stoppable: true },
  quarter_up: { template: "pos", phase: "readings", stoppable: true },
  three_quarter_up: { template: "pos", phase: "readings", stoppable: true },
  verify: { template: "pos", phase: "readings", stoppable: true },
  verify_b: { template: "pos", phase: "readings", stoppable: true },
  tape_run: { template: "pos", phase: "readings", stoppable: true },
  measure_descent: { template: "metro", phase: "readings" },
  measure_ascent: { template: "metro", phase: "readings" },
  tape_result: { template: "lettura", phase: "readings" },
  measure_verify: { template: "metro", phase: "readings" },
  verify_result: { template: "controllo", phase: "readings" },
  verify_offer: { template: "controllo", phase: "readings" },

  // --- the name and the review ---------------------------------------------------------------
  profile_name: { template: "metro", phase: "summary" },
  summary_basic: { template: "riepilogo", phase: "summary", own: true },
  summary_short: { template: "riepilogo", phase: "summary", own: true },
  summary_correction: { template: "riepilogo", phase: "summary", own: true },
  summary_precise: { template: "riepilogo", phase: "summary", own: true },

  // --- and what went wrong -------------------------------------------------------------------
  problem_no_echo: { template: "esito", phase: null },
  problem_not_delivered: { template: "esito", phase: null },
  problem_not_stopped: { template: "esito", phase: null },
  problem_busy: { template: "esito", phase: null },
  problem_bad_point: { template: "esito", phase: null },
  problem_timeout: { template: "esito", phase: null },
  problem_unknown: { template: "esito", phase: null },
  // The one problem the dialog has no words for: it is the panel's `stop` verb arriving in
  // the middle of a step (SPEC §3.5), which the dialog cannot produce.
  problem_interrupted: { template: "esito", phase: null, own: true },
};
