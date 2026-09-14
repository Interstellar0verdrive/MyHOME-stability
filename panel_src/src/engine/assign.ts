// The pending-change model: what the three gestures all end up doing.
//
// Drag, tap and keyboard are three ways into one state. Each of them calls `withPending`,
// each of them ends at the same review panel, and **nothing is written until the user
// confirms** - which is the design's first interaction rule and not an implementation
// detail: a write reaches every shutter of the gateway at once, so a screen that wrote on
// every drop would be a screen that moved twelve travel models while somebody was still
// making up their mind.
//
// Everything here is a pure function over the server's model plus the pending list. There
// is no second copy of the model to keep in step, which is what makes a server push
// mid-gesture harmless: the groups are recomputed from whatever `overview` now says, with
// the same pending changes laid over it.
//
// **No arithmetic lives here.** The numbers in the review table come from
// `myhome/calibration/preview`, which runs the resolution the shutter itself runs on. The
// prototype's `rescale` and `effKeys` are deliberately not ported: they are a JavaScript
// re-implementation of `derive_cover_from_profile`, and the two would drift.

import { type PendingChange } from "./store";
import { type AssignItem, type CoverRow, type Overview } from "./ws";

/** The group a shutter is drawn in: its pending destination, else the server's answer. */
export const effectiveProfile = (
  cover: CoverRow,
  pending: readonly PendingChange[],
): string | null => {
  const change = pendingFor(cover.unique_id, pending);
  return change ? change.to : (cover.profile ?? null);
};

export const pendingFor = (
  coverUniqueId: string,
  pending: readonly PendingChange[],
): PendingChange | undefined => pending.find((item) => item.cover === coverUniqueId);

/**
 * The pending list with one shutter sent somewhere - or with its change withdrawn.
 *
 * Assigning a shutter back to where it already is is not a change, and recording it as one
 * would make the bar say "1 modifica in sospeso" about a batch that would write nothing.
 * The prototype's rule, kept: the change is removed instead.
 */
export const withPending = (
  pending: readonly PendingChange[],
  cover: CoverRow,
  to: string | null,
): { pending: PendingChange[]; withdrawn: boolean } => {
  const rest = pending.filter((item) => item.cover !== cover.unique_id);
  if (to === (cover.profile ?? null)) {
    return { pending: rest, withdrawn: true };
  }
  return { pending: [...rest, { cover: cover.unique_id, to }], withdrawn: false };
};

/**
 * The order the panel draws, which is the server's unless a drag has changed it.
 *
 * `overview.covers` already arrives in the stored order (contract §2), so the fallback is
 * the list itself. A local order is filtered against the model on every read rather than
 * trusted: a shutter that disappeared between the drag and the paint must not leave a hole,
 * and one that appeared must not be invisible.
 */
export const orderedCovers = (
  overview: Overview,
  order: readonly string[] | null,
): CoverRow[] => {
  const byId = new Map(overview.covers.map((cover) => [cover.unique_id, cover]));
  if (!order) {
    return [...overview.covers].sort((a, b) => a.order_index - b.order_index);
  }
  const seen = new Set<string>();
  const out: CoverRow[] = [];
  for (const id of order) {
    const cover = byId.get(id);
    if (cover && !seen.has(id)) {
      seen.add(id);
      out.push(cover);
    }
  }
  for (const cover of overview.covers) {
    if (!seen.has(cover.unique_id)) {
      out.push(cover);
    }
  }
  return out;
};

/**
 * The whole gateway's order with one shutter moved to where it was dropped.
 *
 * One flat list for every group, because that is what the store holds: a group is a slice
 * of it, so moving a row inside a group and moving it to another one are the same
 * operation and only one of them has to be got right.
 */
export const movedTo = (
  order: readonly string[],
  cover: string,
  target: { beforeId: string | null; afterId: string | null },
): string[] => {
  const without = order.filter((id) => id !== cover);
  let index = without.length;
  if (target.beforeId) {
    const found = without.indexOf(target.beforeId);
    index = found < 0 ? without.length : found;
  } else if (target.afterId) {
    const found = without.indexOf(target.afterId);
    index = found < 0 ? without.length : found + 1;
  }
  return [...without.slice(0, index), cover, ...without.slice(index)];
};

/**
 * The order with one shutter put at the end of the group it has just been sent to.
 *
 * A tap and a keyboard assignment mean "append", which is what a batch with **no** `order`
 * already means to the server (contract §9.1). But a batch that carries an order - and it
 * does the moment anything has been dragged - carries the whole gateway's list, and the
 * shutter would keep the place it had in it. So the same meaning is written into the list
 * the batch is about to send: after the last member of the destination group, or at the
 * end of everything when that group is empty.
 */
export const appendedToGroup = (
  order: readonly string[],
  cover: string,
  membersInOrder: readonly string[],
): string[] => {
  const last = membersInOrder.filter((id) => id !== cover).at(-1) ?? null;
  return movedTo(order, cover, { beforeId: null, afterId: last });
};

/**
 * The batch, as `assign` wants it: one item per pending change, with the travel where the
 * review panel collected one.
 *
 * A travel is only sent where the user typed it. A window that already has one is left
 * alone - resending the number it already carries would be a write that changed nothing
 * and an `undo_token` for it.
 */
export const assignItems = (
  pending: readonly PendingChange[],
  heights: Readonly<Record<string, string>>,
): AssignItem[] =>
  pending.map((change) => {
    const typed = heights[change.cover];
    const height = typed === undefined ? undefined : parseTravel(typed);
    return {
      cover_unique_id: change.cover,
      profile: change.to,
      ...(height === null || height === undefined ? {} : { height }),
    };
  });

/**
 * A number as a person writes it: a comma or a point, and nothing else.
 *
 * The same rule as `calibration_flow.parse_number`, because the same person types into the
 * same kind of field on both screens. This is a *pre*-validation and never the decision:
 * the server parses the value again and its refusal is the sentence the user reads.
 */
export const parseTravel = (raw: string): number | null => {
  const text = raw.trim().replace(",", ".");
  if (!text) {
    return null;
  }
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
};

/** The bounds of `set_travel` (contract §9.3), which are the guided form's own. */
export const MIN_TRAVEL_CM = 20;
export const MAX_TRAVEL_CM = 500;

/** Which of the six the typed travel breaks, or `null` when it is usable. */
export type TravelProblem = "missing_travel" | "not_a_number" | "out_of_range";

export const travelProblem = (raw: string | undefined): TravelProblem | null => {
  if (raw === undefined || raw.trim() === "") {
    return "missing_travel";
  }
  const value = parseTravel(raw);
  if (value === null) {
    return "not_a_number";
  }
  return value < MIN_TRAVEL_CM || value > MAX_TRAVEL_CM ? "out_of_range" : null;
};

/**
 * The item that leaves a shutter's assignment exactly as it is.
 *
 * The profile card's impact preview asks `preview` about every follower with the profile's
 * numbers changed and *nothing else* changed, so each item has to rewrite the record into
 * what it already was. For a window the store assigned that is its own profile name; for
 * one whose `myhome.yaml` carries the `profile:` line it is `null` - popping an assignment
 * the record does not have leaves the record alone, and the file goes on answering, which
 * is what `profile_from_file` means. Sending the name instead would set `profile_wins` on
 * a window that does not have it, and the preview would promise the profile's numbers
 * where the file's own run times really win.
 */
export const currentAssignment = (cover: CoverRow): AssignItem => ({
  cover_unique_id: cover.unique_id,
  profile: cover.profile_from_file ? null : (cover.profile ?? null),
});

/** True when this shutter needs a travel typed before the batch can be written. */
export const needsTravel = (cover: CoverRow, change: PendingChange): boolean =>
  change.to !== null && cover.height === null;

/**
 * The five numbers a window can have measured on *itself*, which is what `has_own` lists
 * (`panel_schemas.MEASURABLE_KEYS`). They are key names in a payload and not words on a
 * screen: `values` carries three more that no measurement ever sets, so counting the two
 * lists against each other is how "all its own" and "some of its own" are told apart.
 */
export const MEASURABLE_KEYS: readonly string[] = [
  "opening_time",
  "closing_time",
  "slat_time",
  "opening_roll",
  "closing_roll",
];

/** The three the before/after table always shows, in the order the guided form asks them. */
export const TABLE_KEYS: readonly string[] = ["opening_time", "closing_time", "slat_time"];

/** ...and the two "mostra tutto" adds. */
export const ROLL_KEYS: readonly string[] = ["opening_roll", "closing_roll"];

/** How many decimals each key deserves: a tenth of a second, a hundredth of a ratio. */
export const DECIMALS: Readonly<Record<string, number>> = {
  opening_time: 1,
  closing_time: 1,
  slat_time: 1,
  opening_roll: 2,
  closing_roll: 2,
};
