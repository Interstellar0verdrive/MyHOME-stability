// The numbers of the session, written the way the user's language writes them.
//
// The snapshot carries raw values and nothing else (contract §12): `86.25`, never
// "86,3 cm". That is deliberate - a backend that formatted them would have to know the
// language of every client watching the same session - and it makes this file the one
// place where a number becomes a word.
//
// Two jobs, and they are separate on purpose:
//
// * **`placeholders`** - the dialog's own `{…}` names, filled with the decimals SPEC §5.3
//   fixes for each of them. The sentences these go into are translated into seven
//   languages and none of them may be edited, so the panel has to put in exactly what the
//   dialog would have put in;
// * **`valueLine`** - the review's rows, which are the panel's own screen and therefore
//   carry their unit beside them.
//
// `Intl.NumberFormat` through `engine/i18n.ts`, in the language the user was served, so a
// German reading a French installation still reads "86,3" the way they write it.

import { bareLabel, withUnit } from "../engine/fields";
import { type I18n } from "../engine/i18n";
import { type SessionValueKey } from "../engine/session-contract";

/**
 * How many decimals each of the dialog's placeholders is written with (SPEC §5.3).
 *
 * The seconds and the centimetres of a measurement get one, because that is the precision
 * the measurement has; an expected value and its tolerance get none, because they are
 * being used to point at a place on a wall; and `readings` is a count.
 */
export const PLACEHOLDER_DECIMALS: Readonly<Record<string, number>> = {
  run: 1,
  slat: 1,
  gap: 1,
  height: 1,
  measured: 1,
  accuracy: 1,
  deviation: 1,
  expected: 0,
  tolerance: 0,
  percent: 0,
  readings: 0,
};

/** …and the same for the six values of the model, plus the two bus costs. */
export const VALUE_DECIMALS: Readonly<Record<SessionValueKey, number>> = {
  travel_cm: 0,
  opening_time_s: 1,
  closing_time_s: 1,
  slat_time_s: 1,
  opening_roll: 2,
  closing_roll: 2,
  stop_latency_s: 2,
  start_delay_s: 2,
};

/** Which of the two units a value of the model is measured in; a roll has none. */
const VALUE_UNIT: Readonly<Record<SessionValueKey, "cm" | "s" | "">> = {
  travel_cm: "cm",
  opening_time_s: "s",
  closing_time_s: "s",
  slat_time_s: "s",
  opening_roll: "",
  closing_roll: "",
  stop_latency_s: "s",
  start_delay_s: "s",
};

/**
 * The value labels, which are **not** the panel's own: five of the six already exist as
 * `options.step.calibration_edit.data.*` in all eight languages, and the panel is
 * forbidden from keeping a second copy of a sentence the guided flow already says. The two
 * bus costs have no label there, because the dialog never edits them, so those two are the
 * panel's (SPEC §5.5).
 */
const EDIT_LABEL: Readonly<Partial<Record<SessionValueKey, string>>> = {
  travel_cm: "height",
  opening_time_s: "opening_time",
  closing_time_s: "closing_time",
  slat_time_s: "slat_time",
  opening_roll: "opening_roll",
  closing_roll: "closing_roll",
};

export const valueLabel = (key: SessionValueKey, i18n: I18n): string => {
  const borrowed = EDIT_LABEL[key];
  if (borrowed) {
    // Without the bracket: the form's labels end in the unit because a form field has
    // nowhere else to say it, and `valueLine` puts the unit beside the number. The review
    // of the wizard printed both - "Corsa del telo (cm) ... 110 cm" - which is the drift
    // the cards were corrected for on 18 September and the same functions correct here
    // (live finding 24).
    return bareLabel(i18n.t(`options.step.calibration_edit.data.${borrowed}`));
  }
  // Written out rather than built, because `tests/test_translations.py` reads the keys
  // this bundle asks for out of its double-quoted literals: a key assembled at run time
  // is a key with no stand-in beside it and no test behind it.
  return key === "stop_latency_s"
    ? i18n.t("panel.wizard.review.key.stop_latency")
    : i18n.t("panel.wizard.review.key.start_delay");
};

/** One number of the model, with its unit: "195 cm", "22,6 s", "2,02". */
export const valueLine = (key: SessionValueKey, value: number | null, i18n: I18n): string => {
  if (value === null) {
    // An em dash and not an empty cell: "this value does not exist today" is something
    // the row is saying, and a blank says nothing at all.
    return "—";
  }
  const written = i18n.number(value, VALUE_DECIMALS[key] ?? 1);
  const unit = VALUE_UNIT[key] ?? "";
  if (unit === "") {
    return written;
  }
  const written_unit =
    unit === "cm" ? i18n.t("panel.common.unit.centimetres") : i18n.t("panel.common.unit.seconds");
  return withUnit(written, written_unit);
};

/**
 * The snapshot's placeholders, written out.
 *
 * Anything that is not a number goes through as it is (`cover` is a name), and a `null`
 * becomes an empty string rather than the word "null" - a sentence with a hole in it is
 * better than a sentence with a lie in it.
 */
export const placeholders = (
  raw: Record<string, string | number | null>,
  i18n: I18n,
  extra?: Record<string, string | number | null>,
): Record<string, string> => {
  const out: Record<string, string> = {};
  for (const [name, value] of Object.entries({ ...raw, ...(extra ?? {}) })) {
    if (value === null || value === undefined) {
      out[name] = "";
    } else if (typeof value === "number") {
      out[name] = i18n.number(value, PLACEHOLDER_DECIMALS[name] ?? 1);
    } else {
      out[name] = value;
    }
  }
  return out;
};

/** A count of seconds with one decimal, for the motor line and the press note. */
export const seconds = (value: number, i18n: I18n): string => i18n.number(value, 1);

/**
 * How long a movement has been running, in seconds, read off the **server's** clock.
 *
 * The browser's clock is never the measure of anything (SPEC §5.4, decision 15): what is
 * shown is `now` corrected by the difference this tab last measured between its own clock
 * and `server_time`. A negative answer - the snapshot arrived before its own anchor, which
 * a slow network really does produce - is shown as zero rather than as a count backwards.
 */
export const elapsedSince = (startedAt: string, skewMs: number, now: number): number => {
  const started = Date.parse(startedAt);
  if (Number.isNaN(started)) {
    return 0;
  }
  return Math.max(0, (now - skewMs - started) / 1000);
};

/** What is left of a planned movement, never below zero and never above what was planned. */
export const remaining = (plannedS: number | null, elapsedS: number): number => {
  if (plannedS === null) {
    return 0;
  }
  return Math.max(0, plannedS - elapsedS);
};

/** How far along a planned movement is, as a fraction between 0 and 1. */
export const fraction = (plannedS: number | null, elapsedS: number): number => {
  if (plannedS === null || plannedS <= 0) {
    return 0;
  }
  return Math.max(0, Math.min(1, elapsedS / plannedS));
};
