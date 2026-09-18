// The numeric fields of the two cards, and the rules they are typed under.
//
// Five numbers describe a shutter - two run times, the slat time and two roll
// coefficients - and a profile states the same five plus the travel it was measured at.
// The detail card edits the first set for one window; the profile card edits the second
// for a kind of window. Both are typed into by a person, so both read a comma as a
// decimal point, and both are **pre**-validated here and validated again on the server,
// whose sentence wins (`engine/assign.ts` says the same thing about the travel, and this
// is the same rule one level wider).
//
// The bounds are the guided dialog's own (`calibration_flow.CALIBRATION_FIELDS` and
// `PROFILE_FIELDS`), restated rather than invented: a number the panel accepts and the
// dialog refuses would be a refusal the user could not have seen coming.
//
// **Nothing here computes a travel model.** These functions read text and hand back a
// number or the name of a problem. What a shutter would run on afterwards is
// `myhome/calibration/preview`'s answer on every screen of this panel, without exception.

import { parseTravel } from "./assign";

/** One field: what it is called in a payload, and the two numbers it must lie between. */
export interface FieldBounds {
  min: number;
  max: number;
  /** How many decimals the value deserves when it is printed back into the field. */
  decimals: number;
}

/**
 * The five a window can have measured on it, plus the travel, plus the profile's
 * reference travel - which is the same number under the name the profile gives it.
 */
export const FIELDS: Readonly<Record<string, FieldBounds>> = {
  opening_time: { min: 1, max: 600, decimals: 1 },
  closing_time: { min: 1, max: 600, decimals: 1 },
  slat_time: { min: 0, max: 60, decimals: 1 },
  opening_roll: { min: 1, max: 5, decimals: 2 },
  closing_roll: { min: 1, max: 5, decimals: 2 },
  height: { min: 20, max: 500, decimals: 0 },
  reference_height: { min: 20, max: 500, decimals: 0 },
};

/** Seconds, a bare ratio, or centimetres: which unit belongs beside which field. */
export const UNIT_KEY: Readonly<Record<string, string | null>> = {
  opening_time: "panel.common.unit.seconds",
  closing_time: "panel.common.unit.seconds",
  slat_time: "panel.common.unit.seconds",
  opening_roll: null,
  closing_roll: null,
  height: "panel.common.unit.centimetres",
  reference_height: "panel.common.unit.centimetres",
};

/**
 * A field's name as the panel prints it beside a number that carries its own unit.
 *
 * The labels are the guided form's (`options.step.calibration_edit.data.*` and
 * `profile_edit.data.*`), which the panel may not copy, and the form puts the unit in
 * brackets at the end - "Tempo di salita (s)" - because a form field has nowhere else to
 * say it. Every place the panel prints one of these labels, the number beside it already
 * says "14,9 s" or has "s" after the field, so the bracket is the unit a second time. The
 * trailing bracket is dropped here and the unit is printed with the number
 * (`withUnit`); a label with no bracket is returned as it is.
 *
 * Where the label is **not** beside a number - the refusal "{key} accetta un numero fra
 * {min} e {max}" - the whole label is used, because there the bracket is the only thing
 * that says what the two bounds are measured in.
 */
export const bareLabel = (label: string): string => label.replace(/\s*\([^()]*\)\s*$/u, "");

/** A number already formatted for the user's language, followed by its field's unit. */
export const withUnit = (text: string, unit: string): string => (unit ? `${text} ${unit}` : text);

/** Which of the two `assign` refusals a typed value breaks, or `null` when it is usable. */
export type ValueProblem = "not_a_number" | "out_of_range";

/**
 * What is wrong with this field, if anything.
 *
 * An **empty** field is not a problem here and never a zero: in the detail card it means
 * "nothing to say about this one" and the value goes back to being inherited, which is
 * `cover_edit`'s `null`. A caller that cannot accept an empty field (the profile card,
 * where all five are required) asks for that separately - `required` - because the two
 * are different sentences and only one of them is about the number.
 */
export const valueProblem = (key: string, raw: string | undefined): ValueProblem | null => {
  const text = (raw ?? "").trim();
  if (text === "") {
    return null;
  }
  const value = parseTravel(text);
  if (value === null) {
    return "not_a_number";
  }
  const bounds = FIELDS[key];
  if (!bounds) {
    return null;
  }
  return value < bounds.min || value > bounds.max ? "out_of_range" : null;
};

/** True when the field has been left empty. */
export const isEmpty = (raw: string | undefined): boolean => (raw ?? "").trim() === "";

/**
 * The number a usable field holds, or `null` when it is empty.
 *
 * Only ever called after `valueProblem` has said the text is usable, so a `null` here
 * means an empty field and nothing else.
 */
export const valueOf = (raw: string | undefined): number | null =>
  isEmpty(raw) ? null : parseTravel(raw ?? "");
