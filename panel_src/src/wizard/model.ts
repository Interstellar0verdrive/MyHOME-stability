// One snapshot in, one screen out, and no DOM anywhere in between.
//
// `screenModel(session, context)` is the whole of the guided calibration's appearance: the
// view mounts a `<myhome-screen>` with what comes out of here and does nothing else with
// the snapshot. That is what makes the screens testable without a browser
// (`test/wizard-model.test.ts` walks every example of the frozen fixture through it), and
// it is what makes SPEC §5.8's error card possible - a function that throws is a screen
// that can be replaced, where a view that threw halfway through painting is a blank panel.
//
// **Where the words come from.** Every step of the measurement shows the *dialog's* own
// sentences (`options.step.<step>`), already translated into seven languages: the panel
// may not keep a second copy of a sentence the guided flow already says. The exceptions
// are the four summaries, `problem_interrupted`, the positioning screens and the outcomes,
// which either do not exist in the dialog or speak of the dialog ("Configura →
// Calibrazioni", "alla chiusura del dialogo") - those are the panel's own block, en and it
// (SPEC §5.5, decision 12).
//
// **Where the model is not.** The roll coefficients, the slat time and the fit are never
// on the way forward: they are behind "Show every value" on the review and nowhere else
// (SPEC §5.4, decision 22). The user meets a shutter, a tape measure and a button.

import { type I18n } from "../engine/i18n";
import { splitLeadingImage } from "../engine/markdown";
import {
  type ScreenAction,
  type ScreenModel,
  type ScreenOption,
  type ScreenSummaryRow,
} from "../engine/screen";
import {
  type SessionAction,
  type SessionReviewMeasuredRow,
  type SessionSnapshot,
  type SessionStep,
  type SessionValueKey,
} from "../engine/session-contract";
import { type ProfileRow } from "../engine/ws";
import { PHASES, PHASE_KEY, STEPS, type StepRow } from "./steps";
import {
  elapsedSince,
  fraction as barFraction,
  placeholders as fillPlaceholders,
  remaining,
  seconds as secondsOf,
  valueLabel,
  valueLine,
} from "./format";

/** What the view knows and the snapshot does not. */
export interface WizardContext {
  i18n: I18n;
  /** This tab's clock, read once per paint so that one screen shows one instant. */
  now: number;
  /** `now` minus the server's `server_time` when the last snapshot arrived, in ms. */
  skewMs: number;
  /** What the one field on the screen holds, as typed; `null` before it was touched. */
  typed: string | null;
  /** `current_position` of the shutter, as the shutter itself estimates it. */
  position: number | null;
  /** Another client is driving: the screen is the same, without its controls. */
  readOnly: boolean;
  /** The review's two disclosures, as this screen currently has them. */
  showAll: boolean;
  showAffected: boolean;
  /** The signal at the start, as this browser remembers it. */
  cue: boolean;
  /** The gateway's profiles, for the second line of a profile choice. */
  profiles: ProfileRow[];
}

/** The tokens the screen fires back; `model.ts` writes them, `views/wizard.ts` reads them. */
export const ACT = "act:";
export const SAVE = "save:";
export const PICK = "pick:";
export const SUBMIT = "submit";
export const STOP = "stop";
export const CLAIM = "claim";
export const CUE = "cue";
export const SHOW_ALL = "show:all";
export const SHOW_AFFECTED = "show:affected";
export const AGAIN = "again";
export const OPEN_COVER = "open_cover";
export const CLOSE = "close";

/** The three rows of the review that are on the way forward; the rest is behind a press. */
const HEADLINE_ROWS: readonly SessionValueKey[] = ["travel_cm", "opening_time_s", "closing_time_s"];

/**
 * Where an action borrows its label when the step it is offered on has none of its own.
 *
 * It happens for two reasons, both of them the dialog's: a step whose screen is a form has
 * no `menu_options` at all (so `repeat_tape` arrives on `measure_descent` after an outside
 * movement with nowhere to read its words - contract §11.5), and the steps the panel draws
 * with its own texts still offer the dialog's actions. The lender is always a step that
 * offers the same action, so the words are the ones the user would have read in the
 * dialog.
 */
const BORROWED: Readonly<Partial<Record<SessionAction, SessionStep>>> = {
  repeat_step: "home_closed_done",
  not_right: "home_closed_done",
  accept_step: "open_result",
  repeat_tape: "tape_result",
  tape_not_right: "tape_result",
  repeat_measure: "height_result",
  path_c: "verify_result",
  refine: "summary_basic",
};

/** A sentence out of the files, or `null` when nobody wrote one. `I18n.t` answers the key. */
const text = (i18n: I18n, key: string, ph?: Record<string, string>): string | null => {
  const answer = i18n.t(key, ph);
  return answer === key ? null : answer;
};

/** The words on one action's button, from the step that offers it or from its lender. */
export const actionLabel = (
  i18n: I18n,
  step: SessionStep,
  action: SessionAction,
  ph: Record<string, string>,
): string => {
  const own = text(i18n, `options.step.${step}.menu_options.${action}`, ph);
  if (own !== null) {
    return own;
  }
  const lender = BORROWED[action];
  const borrowed = lender ? text(i18n, `options.step.${lender}.menu_options.${action}`, ph) : null;
  // The token itself, if the files really have nothing: a word nobody wrote is better
  // shown as the identifier it is than hidden behind an invented sentence.
  return borrowed ?? action;
};

/**
 * The header's phase line: "Ascent · 3 of 6", or nothing.
 *
 * Read by `main.ts` for the panel's own toolbar, which is drawn **outside** the wizard's
 * `try`. So it answers `null` for anything it does not recognise instead of throwing: a
 * snapshot that surprises the panel costs the wizard its screen, never the panel its page.
 */
export const phaseLine = (session: SessionSnapshot | null, i18n: I18n): string | null => {
  const step = session?.step;
  const row = step ? STEPS[step] : undefined;
  if (!row?.phase) {
    return null;
  }
  return i18n.t("panel.screen.phase", {
    phase: i18n.t(PHASE_KEY[row.phase]),
    index: PHASES.indexOf(row.phase) + 1,
    count: PHASES.length,
  });
};

/** The one row of the review the screen shows for a key, or nothing when there is none. */
const summaryRow = (
  rows: readonly SessionReviewMeasuredRow[],
  key: SessionValueKey,
  i18n: I18n,
): ScreenSummaryRow | null => {
  const row = rows.find((one) => one.key === key);
  if (!row) {
    return null;
  }
  return {
    label: valueLabel(key, i18n),
    before: row.before === null ? undefined : valueLine(key, row.before, i18n),
    after: valueLine(key, row.after, i18n),
  };
};

/**
 * The screen, built from the snapshot.
 *
 * It throws on a step it has no row for and on a snapshot missing what the contract says
 * is always there. That is not an oversight: `views/wizard.ts` catches it and shows the
 * card of SPEC §5.8, which says the calibration is still running and offers a way on -
 * which is a truer screen than one drawn from half a snapshot.
 */
export const screenModel = (session: SessionSnapshot, context: WizardContext): ScreenModel => {
  const { i18n } = context;
  const ph = fillPlaceholders(session.placeholders, i18n);
  if (!session.cover || typeof session.cover.name !== "string") {
    throw new Error("the snapshot names no shutter");
  }
  if (session.state === "saved" || session.state === "ended") {
    return outcomeScreen(session, context, ph);
  }
  const step = session.step;
  if (!step) {
    throw new Error(`a running session with no step (state ${session.state})`);
  }
  const row = STEPS[step];
  if (!row) {
    throw new Error(`no screen is described for the step '${step}'`);
  }
  const model =
    row.template === "pos"
      ? positioningScreen(session, context, row, ph)
      : row.template === "riepilogo"
        ? reviewScreen(session, context, ph)
        : row.template === "esito"
          ? problemScreen(session, context, row, ph)
          : stepScreen(session, context, row, step, ph);
  decorate(model, session, context);
  return model;
};

// ---------------------------------------------------------------- the ordinary steps

const stepScreen = (
  session: SessionSnapshot,
  context: WizardContext,
  row: StepRow,
  step: SessionStep,
  ph: Record<string, string>,
): ScreenModel => {
  const { i18n } = context;
  const source = row.display ?? step;
  const title = text(i18n, `options.step.${source}.title`, ph) ?? "";
  const described = text(i18n, `options.step.${source}.description`, ph) ?? "";
  const { image, body } = splitLeadingImage(described);
  const model: ScreenModel = {
    id: step,
    model: row.template,
    title,
    body,
    image: image ? { src: image.src, alt: image.alt } : undefined,
  };
  if (row.template === "click") {
    clickParts(model, session, context, row, step, body, ph);
  } else if (row.template === "metro" || (row.template === "controllo" && session.form)) {
    fieldParts(model, session, context, step, ph);
  }
  if (row.template === "scelta" || row.template === "controllo") {
    model.options = optionsFor(session, context, step, ph);
  }
  if (session.check) {
    checkParts(model, session, context);
  }
  if (row.template === "metro" && session.actions.length > 0) {
    // A form step's big button is "go on" with what was typed; whatever else the step
    // offers goes under it. It happens when something moved the shutter while the reading
    // was being taken: `repeat_tape` arrives on a screen that has no words of its own for
    // it, and borrows them from `tape_result` (contract §11.5).
    model.secondary = session.actions.map((action) => ({
      label: actionLabel(i18n, step, action, ph),
      action: `${ACT}${action}`,
      kind: "secondary" as const,
    }));
  }
  if (!model.primary) {
    footerFor(model, session, context, step, ph);
  }
  if (row.cue) {
    model.toggle = {
      label: i18n.t("panel.wizard.cue.toggle"),
      checked: context.cue,
      action: CUE,
    };
  }
  return model;
};

/**
 * What the two columns of a `click` screen say: the instruction, the motor and the press.
 *
 * The motor line is **only** what the snapshot said plus the seconds since its own anchor;
 * nothing here works out where the shutter is or whether it is still going. The estimated
 * position beside it is the shutter's own estimate, out of `hass`, at about one hertz -
 * two different claims, from two different sources, and neither of them this panel's.
 */
const clickParts = (
  model: ScreenModel,
  session: SessionSnapshot,
  context: WizardContext,
  row: StepRow,
  step: SessionStep,
  body: string,
  ph: Record<string, string>,
): void => {
  const { i18n } = context;
  const movement = session.movement;
  const progress = movement ? text(i18n, `options.progress.${movement.progress_action}`, ph) : null;
  const started = movement?.started_at ?? null;
  const running = started ? elapsedSince(started, context.skewMs, context.now) : 0;
  // During the movement the prose goes: one or two lines and the button, because there is
  // no time to read while watching a shutter (the maintainer's rule of 18 September). The
  // last paragraph of the step's own description is that line.
  const lines = body.split(/\n{2,}/).map((one) => one.trim()).filter((one) => one !== "");
  const instruction = row.press === "moving" ? (lines[lines.length - 1] ?? "") : (progress ?? "");
  if (row.press === "moving" || row.press === "registered") {
    model.body = lines.slice(0, -1).join("\n\n");
  } else {
    model.body = "";
  }
  const position =
    context.position === null ? undefined : `${i18n.number(context.position, 0)} %`;
  if (row.press === "starting") {
    model.press = {
      state: "starting",
      label: "",
      instruction,
      motor: i18n.t("panel.wizard.motor.starting"),
      position,
    };
    model.primary = { label: "…", action: "", disabled: true, kind: "primary" };
    return;
  }
  if (row.press === "registered") {
    const lift = session.measured.lift;
    const pressedAt = lift?.pressed_at ?? null;
    const at =
      pressedAt && started
        ? Math.max(0, (Date.parse(pressedAt) - Date.parse(started)) / 1000)
        : null;
    model.press = {
      state: "registered",
      label: "",
      instruction,
      motor: i18n.t("panel.wizard.motor.stopped"),
      position,
      note:
        at === null
          ? undefined
          : i18n.t("panel.wizard.press.registered_note", { seconds: secondsOf(at, i18n) }),
    };
    model.primary = {
      label: i18n.t("panel.wizard.press.registered"),
      action: "",
      disabled: true,
      kind: "primary",
    };
    return;
  }
  const press = session.actions[0];
  model.press = {
    state: "moving",
    label: "",
    instruction,
    motor: i18n.t("panel.wizard.motor.moving", { seconds: secondsOf(running, i18n) }),
    position,
  };
  if (press) {
    model.primary = {
      label: actionLabel(i18n, step, press, ph),
      action: `${ACT}${press}`,
      kind: "primary",
    };
  }
  model.secondary = session.actions
    .slice(1)
    .map((action) => ({
      label: actionLabel(i18n, step, action, ph),
      action: `${ACT}${action}`,
      kind: "secondary" as const,
    }));
};

/**
 * The numbers a verification was made of, said out loud.
 *
 * The dialog's own sentence gives the deviation and stops there; where the shutter was
 * sent, what the tape read and what the model had predicted are the answer to "how do you
 * know that", and on path B the threshold and the profile's own accuracy are what the
 * offer to correct this shutter rests on.
 *
 * **A check with no `gap_cm` is not a check that came out at zero.** It means the profile
 * went out from under the session and there was nothing to measure against; the snapshot
 * still carries `placeholders.deviation = 0` because the dialog's sentence has to
 * substitute something, and printing "0,0 cm" there would tell the reader their shutter is
 * perfect. So that case replaces the words rather than decorating them (lot B4, §7).
 */
const checkParts = (
  model: ScreenModel,
  session: SessionSnapshot,
  context: WizardContext,
): void => {
  const { i18n } = context;
  const check = session.check;
  if (!check) {
    return;
  }
  const percent = i18n.number(check.fraction * 100, 0);
  if (check.gap_cm === null) {
    model.title = i18n.t("panel.wizard.check.no_reference.title");
    model.body = i18n.t("panel.wizard.check.no_reference.body", {
      cover: session.cover.name,
      measured: i18n.number(check.measured_cm, 1),
      percent,
    });
    model.image = undefined;
    return;
  }
  const lines = [
    i18n.t("panel.wizard.check.measured", {
      measured: i18n.number(check.measured_cm, 1),
      predicted: i18n.number(check.predicted_cm, 1),
      percent,
    }),
  ];
  if (check.threshold_cm !== null) {
    lines.push(
      check.profile_check_cm === null
        ? i18n.t("panel.wizard.check.threshold", {
            threshold: i18n.number(check.threshold_cm, 0),
          })
        : i18n.t("panel.wizard.check.threshold_profile", {
            threshold: i18n.number(check.threshold_cm, 0),
            profile: session.profile ?? "",
            accuracy: i18n.number(check.profile_check_cm, 1),
          }),
    );
  }
  model.lines = lines;
};

/** The one field a step can ask for, with the caption and the refusal under it. */
const fieldParts = (
  model: ScreenModel,
  session: SessionSnapshot,
  context: WizardContext,
  step: SessionStep,
  ph: Record<string, string>,
): void => {
  const { i18n } = context;
  const form = session.form;
  if (!form || form.kind === "choice") {
    return;
  }
  const name = form.field;
  const label = text(i18n, `options.step.${step}.data.${name}`, ph) ?? name;
  const hint = text(i18n, `options.step.${step}.data_description.${name}`, ph) ?? undefined;
  const suggestion = form.suggested;
  model.field = {
    label,
    hint,
    unit: form.unit ?? undefined,
    value: context.typed ?? "",
    placeholder:
      suggestion === null || suggestion === undefined
        ? undefined
        : typeof suggestion === "number"
          ? i18n.number(suggestion, 1)
          : suggestion,
    error: form.error === null ? undefined : (text(i18n, `options.error.${form.error}`) ?? undefined),
    // A name is typed on a text keyboard and is not a big number: the 64 px field is for
    // the one measurement of the step, and a profile name in it looks like a reading.
    big: form.kind === "number",
    inputMode: form.kind === "text" ? "text" : "decimal",
  };
  model.primary = {
    label: i18n.t("panel.wizard.action.submit"),
    action: SUBMIT,
    kind: "primary",
  };
};

/** The options of a choice: the step's actions, or the profiles the form offers. */
const optionsFor = (
  session: SessionSnapshot,
  context: WizardContext,
  step: SessionStep,
  ph: Record<string, string>,
): ScreenOption[] => {
  const { i18n } = context;
  const form = session.form;
  if (form?.kind === "choice") {
    return (form.choices ?? []).map((choice) => profileOption(choice, context, form.suggested));
  }
  return session.actions.map((action) => ({
    title: actionLabel(i18n, step, action, ph),
    action: `${ACT}${action}`,
    // What `start` was told to highlight, and nothing more: the scope arrives from the
    // panel's own "Correggi…" and the screen shows which one the button meant, without
    // choosing it (contract §11.2).
    current: session.intent?.scope !== undefined && session.intent.scope === action,
  }));
};

/** One profile in a choice, with the reference travel and the shutter it was measured on. */
const profileOption = (
  choice: string,
  context: WizardContext,
  suggested: number | string | null,
): ScreenOption => {
  const { i18n } = context;
  if (choice === "from_the_file") {
    return {
      // Not the panel's own words: the five origin phrases already exist in all eight
      // languages, and "Dal file" is one of them.
      title: i18n.origin("from_the_file", null),
      meta: i18n.t("panel.wizard.profile.from_file"),
      action: `${PICK}${choice}`,
      current: suggested === choice,
    };
  }
  const profile = context.profiles.find((one) => one.name === choice);
  const reference = profile?.reference_height ?? null;
  const measured = profile?.measured_on_name ?? null;
  const meta =
    reference === null
      ? i18n.t("panel.wizard.profile.meta_no_reference")
      : measured === null
        ? i18n.t("panel.wizard.profile.meta", { reference: i18n.number(reference, 0) })
        : i18n.t("panel.wizard.profile.meta_measured", {
            reference: i18n.number(reference, 0),
            cover: measured,
          });
  return {
    title: choice,
    meta,
    action: `${PICK}${choice}`,
    current: suggested === choice,
  };
};

/** The big button and the ones under it, for a step whose actions are the way forward. */
const footerFor = (
  model: ScreenModel,
  session: SessionSnapshot,
  context: WizardContext,
  step: SessionStep,
  ph: Record<string, string>,
): void => {
  const { i18n } = context;
  if (model.options && model.options.length > 0) {
    // A choice is made by pressing one of the choices; a second button saying "go on"
    // would be a control that does nothing until one of them has been pressed.
    return;
  }
  const buttons: ScreenAction[] = session.actions.map((action) => ({
    label: actionLabel(i18n, step, action, ph),
    action: `${ACT}${action}`,
  }));
  const first = buttons[0];
  if (first) {
    model.primary = { ...first, kind: "primary" };
    model.secondary = buttons.slice(1).map((one) => ({ ...one, kind: "secondary" as const }));
  }
};

// ------------------------------------------------------------------- the positioning

/**
 * A screen with nothing to do on it: the shutter is on its way somewhere the step chose.
 *
 * The bar is `planned_s`, which the contract calls a modelled duration and warns is read
 * by nothing that measures. So is the number of seconds under it: they are there so that
 * waiting feels like waiting and not like a hang, and the step advances when the movement
 * ends - never when the bar fills.
 */
const positioningScreen = (
  session: SessionSnapshot,
  context: WizardContext,
  row: StepRow,
  ph: Record<string, string>,
): ScreenModel => {
  const { i18n } = context;
  const movement = session.movement;
  const progress = movement ? text(i18n, `options.progress.${movement.progress_action}`, ph) : null;
  const started = movement?.started_at ?? null;
  const running = started ? elapsedSince(started, context.skewMs, context.now) : 0;
  const planned = movement?.planned_s ?? null;
  const left = remaining(planned, running);
  const model: ScreenModel = {
    id: session.step ?? "",
    model: "pos",
    title: i18n.t("panel.wizard.positioning.title"),
    progress: {
      text: progress ?? "",
      fraction: barFraction(planned, running),
      eta:
        planned === null
          ? undefined
          : i18n.t("panel.wizard.positioning.remaining", { seconds: i18n.number(left, 0) }),
      done: planned !== null && left <= 0,
    },
  };
  if (row.stoppable) {
    model.secondary = [
      { label: i18n.t("panel.wizard.action.stop"), action: STOP, kind: "text" },
    ];
  }
  return model;
};

// ------------------------------------------------------------------------ the review

/**
 * What was measured, against what the shutter uses today - and nothing written yet.
 *
 * Three rows on the way forward and everything else behind "Show every value": the
 * maintainer's principle is that the model stays behind the flow, so the roll
 * coefficients, the slat time, the values this calibration did not measure but will
 * change, and the configuration snippet are all one press away rather than in the reader's
 * path (SPEC §5.4, decision 22).
 */
const reviewScreen = (
  session: SessionSnapshot,
  context: WizardContext,
  ph: Record<string, string>,
): ScreenModel => {
  const { i18n } = context;
  const review = session.review;
  if (!review) {
    throw new Error("a session in review with no review in it");
  }
  const rows = HEADLINE_ROWS.map((key) => summaryRow(review.rows, key, i18n)).filter(
    (one): one is ScreenSummaryRow => one !== null,
  );
  const more = (["slat_time_s", "opening_roll", "closing_roll"] as const)
    .map((key) => summaryRow(review.rows, key, i18n))
    .filter((one): one is ScreenSummaryRow => one !== null);
  const lines: string[] = [];
  if (review.accuracy_cm !== null && review.check_fraction !== null) {
    lines.push(
      i18n.t("panel.wizard.review.accuracy_checked", {
        accuracy: i18n.number(review.accuracy_cm, 1),
        percent: i18n.number(review.check_fraction * 100, 0),
      }),
    );
  } else {
    lines.push(i18n.t("panel.wizard.review.accuracy_unchecked"));
  }
  if (review.profile_exists && review.profile_name) {
    lines.push(
      i18n.t("panel.wizard.review.profile_exists", {
        profile: review.profile_name,
        count: review.affected.length,
      }),
    );
  }
  if (review.name_clash === "file" && review.profile_name) {
    lines.push(i18n.t("panel.wizard.review.name_clash", { profile: review.profile_name }));
  }
  lines.push(i18n.t("panel.wizard.review.where", { cover: session.cover.name }));
  const model: ScreenModel = {
    id: session.step ?? "",
    model: "riepilogo",
    title: i18n.t("panel.wizard.review.title"),
    body: i18n.t("panel.wizard.review.intro", { cover: session.cover.name }),
    summary: {
      rows,
      more: context.showAll ? more : undefined,
      sideEffects:
        context.showAll && review.side_effects.length > 0
          ? {
              title: i18n.t("panel.wizard.review.side_effects"),
              rows: review.side_effects.map((one) => ({
                label: valueLabel(one.key, i18n),
                before: one.before === null ? undefined : valueLine(one.key, one.before, i18n),
                after: valueLine(one.key, one.after, i18n),
              })),
            }
          : undefined,
      affected:
        context.showAffected && review.affected.length > 0
          ? review.affected.map((one) => ({
              title: one.name,
              rows: HEADLINE_ROWS.map((key) => summaryRow(one.rows, key, i18n)).filter(
                (found): found is ScreenSummaryRow => found !== null,
              ),
            }))
          : undefined,
      code: context.showAll ? review.yaml : undefined,
      codeLabel: context.showAll ? i18n.t("panel.wizard.review.yaml") : undefined,
      lines,
      disclose: discloseButtons(review.affected.length > 0, context, i18n),
    },
  };
  const [first, ...rest] = review.targets;
  if (first) {
    model.primary = { ...saveAction(first, review.profile_name, i18n), kind: "primary" };
  }
  model.secondary = [
    ...rest.map((target) => ({
      ...saveAction(target, review.profile_name, i18n),
      kind: "secondary" as const,
    })),
    ...session.actions.map((action) => ({
      label: actionLabel(i18n, "summary_basic", action, ph),
      action: `${ACT}${action}`,
      kind: "text" as const,
    })),
  ];
  return model;
};

const saveAction = (
  target: "profile" | "cover_only",
  profile: string | null,
  i18n: I18n,
): ScreenAction =>
  target === "profile"
    ? {
        label: i18n.t("panel.wizard.review.save_profile", { profile: profile ?? "" }),
        action: `${SAVE}profile`,
      }
    : {
        label: i18n.t("panel.wizard.review.save_cover_only"),
        action: `${SAVE}cover_only`,
      };

const discloseButtons = (
  hasAffected: boolean,
  context: WizardContext,
  i18n: I18n,
): { label: string; action: string; open: boolean }[] => {
  const buttons = [
    {
      label: context.showAll
        ? i18n.t("panel.common.action.hide_all")
        : i18n.t("panel.common.action.show_all"),
      action: SHOW_ALL,
      open: context.showAll,
    },
  ];
  if (hasAffected) {
    buttons.push({
      label: context.showAffected
        ? i18n.t("panel.wizard.review.affected_hide")
        : i18n.t("panel.wizard.review.affected_show"),
      action: SHOW_AFFECTED,
      open: context.showAffected,
    });
  }
  return buttons;
};

// ------------------------------------------------------------ the problems and the ends

/** A step that was abandoned: what happened, that nothing was written, and the way back. */
const problemScreen = (
  session: SessionSnapshot,
  context: WizardContext,
  row: StepRow,
  ph: Record<string, string>,
): ScreenModel => {
  const { i18n } = context;
  const step = session.step as SessionStep;
  const title = row.own
    ? i18n.t("panel.wizard.problem.interrupted.title")
    : (text(i18n, `options.step.${step}.title`, ph) ?? "");
  const described = row.own
    ? i18n.t("panel.wizard.problem.interrupted.body")
    : (text(i18n, `options.step.${step}.description`, ph) ?? "");
  const { image, body } = splitLeadingImage(described);
  const model: ScreenModel = {
    id: step,
    model: "esito",
    outcome: "problem",
    title,
    body,
    image: image ? { src: image.src, alt: image.alt } : undefined,
    alert: title,
  };
  footerFor(model, session, context, step, ph);
  return model;
};

/** How it ended, and what that means now. The one screen that is always the last one. */
const outcomeScreen = (
  session: SessionSnapshot,
  context: WizardContext,
  ph: Record<string, string>,
): ScreenModel => {
  const { i18n } = context;
  const outcome = session.outcome;
  const reason = outcome?.reason ?? "cancelled";
  const cover = session.cover.name;
  const model: ScreenModel = {
    id: `outcome_${reason}`,
    model: "esito",
    title: "",
    outcome: "cancelled",
  };
  if (reason === "saved") {
    const origin = i18n.origin(outcome?.origin ?? "measured", outcome?.profile ?? null);
    model.outcome = "saved";
    model.title = i18n.t("panel.wizard.outcome.saved.title");
    model.body = outcome?.profile
      ? i18n.t("panel.wizard.outcome.saved.profile", {
          cover,
          profile: outcome.profile,
          origin,
        })
      : i18n.t("panel.wizard.outcome.saved.cover", { cover, origin });
    const review = session.review;
    if (review) {
      model.summary = {
        rows: HEADLINE_ROWS.map((key) => summaryRow(review.rows, key, i18n)).filter(
          (one): one is ScreenSummaryRow => one !== null,
        ),
      };
    }
    model.primary = {
      label: i18n.t("panel.wizard.outcome.action.again"),
      action: AGAIN,
      kind: "primary",
    };
    model.secondary = [
      {
        label: i18n.t("panel.wizard.outcome.action.open_cover"),
        action: OPEN_COVER,
        kind: "secondary",
      },
      { label: i18n.t("panel.wizard.outcome.action.close"), action: CLOSE, kind: "text" },
    ];
    return model;
  }
  if (reason === "cancelled") {
    model.title = i18n.t("panel.wizard.outcome.cancelled.title");
    model.body = i18n.t("panel.wizard.outcome.cancelled.body", { cover });
  } else if (reason === "expired") {
    model.outcome = "expired";
    model.title = i18n.t("panel.wizard.outcome.expired.title");
    model.body = i18n.t("panel.wizard.outcome.expired.body", { cover });
  } else if (reason === "unloaded") {
    model.outcome = "expired";
    model.title = i18n.t("panel.wizard.outcome.unloaded.title");
    model.body = i18n.t("panel.wizard.outcome.unloaded.body", { cover });
  } else if (reason === "left") {
    model.title = i18n.t("panel.wizard.outcome.left.title");
    model.body = i18n.t("panel.wizard.outcome.left.body");
  } else {
    model.outcome = "problem";
    model.title = i18n.t("panel.wizard.outcome.gone.title");
    model.body = i18n.t("panel.wizard.outcome.gone.body", { cover });
  }
  model.primary = {
    label: i18n.t("panel.wizard.outcome.action.again"),
    action: AGAIN,
    kind: "primary",
  };
  model.secondary = [
    { label: i18n.t("panel.wizard.outcome.action.close"), action: CLOSE, kind: "text" },
  ];
  // `ph` is read by the outcomes that name the shutter through the snapshot's own
  // placeholders rather than through `cover`; keeping the parameter makes every branch of
  // this file take the same two things.
  void ph;
  return model;
};

// ------------------------------------------------------------------ what every screen gets

/**
 * The three things that are true of a screen whoever is looking at it: an outside
 * movement, who is driving, and what to announce.
 */
const decorate = (
  model: ScreenModel,
  session: SessionSnapshot,
  context: WizardContext,
): void => {
  const { i18n } = context;
  if (session.notice === "rehomed") {
    model.note = { text: i18n.t("panel.wizard.external.rehomed"), tone: "info" };
  } else if (session.notice === "reading_stale") {
    model.note = { text: i18n.t("panel.wizard.external.reading"), tone: "error" };
  } else if (session.external_move) {
    model.note = { text: i18n.t("panel.wizard.external.moved"), tone: "info" };
  }
  if (session.substate === "awaiting_endpoint") {
    // The one thing on this screen that must interrupt whatever is being read: a shutter
    // that has started moving is the moment the press is about.
    model.alert = i18n.t("panel.wizard.announce.motor");
  }
  model.announce = model.title;
  if (!context.readOnly) {
    return;
  }
  // Read-only: the same screen, without anything that acts. Not a screen saying "wait" -
  // the user is standing in front of a shutter somebody else is measuring, and what they
  // need is to see where it has got to and one way to take it over.
  model.primary = undefined;
  model.secondary = undefined;
  model.options = undefined;
  model.field = undefined;
  model.toggle = undefined;
  if (model.summary) {
    model.summary = { ...model.summary, disclose: undefined };
  }
  model.readOnly = {
    text: i18n.t("panel.wizard.owner.other"),
    label: i18n.t("panel.wizard.owner.take"),
    action: CLAIM,
  };
};
