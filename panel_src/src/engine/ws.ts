// Typed wrappers over the three read commands of `custom_components/myhome/websocket_api.py`.
//
// The shapes below are `custom_components/myhome/panel_schemas.py` restated in
// TypeScript, and that file says so in its own words: it is the frozen contract, and a
// change to either is a change to both. Nothing here re-derives anything the server
// already answered - not a cover's origin, not a rescaled profile value. That is the
// parity invariant: the panel and the `Calibration source` attribute must never disagree,
// and the only way to guarantee it is that one function computes it, on the server.

import { type HaConnection } from "../types/ha";

export interface EntrySummary {
  entry_id: string;
  title: string;
  mac: string;
  loaded: boolean;
}

export interface ProfileRow {
  name: string;
  source: "store" | "yaml" | null;
  editable: boolean;
  values: Record<string, number>;
  reference_height: number | null;
  measured_on: string | null;
  measured_on_name: string | null;
  measured_at: string | null;
  followers: string[];
  followers_from_file: string[];
  missing: boolean;
}

export interface CoverRow {
  unique_id: string;
  entity_id: string | null;
  name: string;
  area_id: string | null;
  area: string | null;
  height: number | null;
  profile: string | null;
  profile_from_file: boolean;
  profile_missing: boolean;
  origin: string;
  source: string;
  values: Record<string, number>;
  has_own: string[];
  level: string | null;
  verify_note: number | null;
  measured_at: string | null;
  calibrating: boolean;
  order_index: number;
}

export interface Overview {
  entries: EntrySummary[];
  entry_id: string;
  measuring: { cover_unique_id: string; name: string } | null;
  profiles: ProfileRow[];
  covers: CoverRow[];
  order: string[];
  no_basic_covers: boolean;
}

export interface Texts {
  language: string;
  requested: string;
  fallback: boolean;
  texts: Record<string, unknown>;
}

/**
 * A refusal from the backend, kept whole.
 *
 * `translation_key` is the interesting half: the backend never sends a sentence a user
 * should read, it sends the key of one, and the panel renders it out of the same seven
 * files the guided dialog reads. `message` is the English fallback that travels beside
 * it so that a key the texts lot has not written yet still says something.
 */
export interface WsError {
  code: string;
  message: string;
  translation_key?: string;
  translation_placeholders?: Record<string, string>;
}

export const asWsError = (error: unknown): WsError => {
  if (error && typeof error === "object" && "code" in error) {
    return error as WsError;
  }
  return { code: "unknown_error", message: String(error) };
};

export const overview = (connection: HaConnection, entryId?: string): Promise<Overview> =>
  connection.sendMessagePromise<Overview>({
    type: "myhome/calibration/overview",
    ...(entryId ? { entry_id: entryId } : {}),
  });

export const texts = (connection: HaConnection, language: string): Promise<Texts> =>
  connection.sendMessagePromise<Texts>({
    type: "myhome/calibration/texts",
    language,
  });

export const coverDetail = (
  connection: HaConnection,
  entryId: string,
  coverUniqueId: string,
): Promise<CoverDetail> =>
  connection.sendMessagePromise<CoverDetail>({
    type: "myhome/calibration/cover_detail",
    entry_id: entryId,
    cover_unique_id: coverUniqueId,
  });

/** One key of a cover's model, and which of the four sources said it (contract §3). */
export interface CoverKeyRow {
  key: string;
  value: number;
  origin: "own" | "profile" | "file" | "default";
  own: boolean;
  inherited_value: number | null;
  inherited_origin: string | null;
  profile_value: number | null;
  file_value: number | null;
  default_value: number | null;
}

export interface CoverDetail {
  entry_id: string;
  cover: CoverRow;
  keys: CoverKeyRow[];
}

// --- the subscription -----------------------------------------------------------------
//
// `myhome/calibration/subscribe` pushes the whole `overview` on subscribing and after
// every write, and a `measuring` object whenever a guided calibration takes one of this
// gateway's shutters or gives it back. The payload is always complete and never a patch,
// which is what lets the panel replace its model rather than merge into it - and what
// stops two browser tabs on the same twelve shutters from each seeing half of it.

export interface OverviewEvent {
  type: "overview";
  overview: Overview;
}

export interface MeasuringEvent {
  type: "measuring";
  cover_unique_id: string | null;
  name: string | null;
}

export type CalibrationEvent = OverviewEvent | MeasuringEvent;

export const subscribe = (
  connection: HaConnection,
  entryId: string | null,
  onEvent: (event: CalibrationEvent) => void,
): Promise<() => Promise<void>> =>
  connection.subscribeMessage<CalibrationEvent>(onEvent, {
    type: "myhome/calibration/subscribe",
    ...(entryId ? { entry_id: entryId } : {}),
  });

/**
 * True when the backend does not know this command at all.
 *
 * The subscription lands with the write half of the contract, which is a branch behind the
 * one this panel is built on. A panel that assumed it was there would show a stale model
 * for as long as the tab stayed open and never say so; a panel that feature-detects it
 * falls back to asking again every half minute and says *that*. `unknown_command` is Home
 * Assistant's own code for a message type nothing has registered.
 */
export const isUnknownCommand = (error: unknown): boolean => asWsError(error).code === "unknown_command";

// --- the write half (contract §8-§10) --------------------------------------------------
//
// Declared here, against the frozen document, so that lots 7 and 8 have one place to call
// and one shape to expect. **Nothing in 0.6.0 lot 5 calls them**: the overview is read-only
// in this lot and the commands themselves are still on a branch under review. Every write
// answers with a fresh whole `overview` and an `undo_token` - or `null` when the write
// changed nothing at all.

export interface WriteResult {
  overview: Overview;
  undo_token: string | null;
}

export interface AssignItem {
  cover_unique_id: string;
  profile: string | null;
  height?: number | null;
}

export interface AssignResult extends WriteResult {
  applied: number;
}

export const assign = (
  connection: HaConnection,
  entryId: string,
  assignments: AssignItem[],
  order?: string[],
): Promise<AssignResult> =>
  connection.sendMessagePromise<AssignResult>({
    type: "myhome/calibration/assign",
    entry_id: entryId,
    assignments,
    ...(order ? { order } : {}),
  });

export const reorder = (
  connection: HaConnection,
  entryId: string,
  order: string[],
  profile?: string | null,
): Promise<WriteResult> =>
  connection.sendMessagePromise<WriteResult>({
    type: "myhome/calibration/reorder",
    entry_id: entryId,
    order,
    ...(profile !== undefined ? { profile } : {}),
  });

export const setTravel = (
  connection: HaConnection,
  entryId: string,
  coverUniqueId: string,
  height: number | null,
): Promise<WriteResult> =>
  connection.sendMessagePromise<WriteResult>({
    type: "myhome/calibration/set_travel",
    entry_id: entryId,
    cover_unique_id: coverUniqueId,
    height,
  });

export const coverEdit = (
  connection: HaConnection,
  entryId: string,
  coverUniqueId: string,
  overrides: Record<string, number | null>,
  height?: number | null,
): Promise<WriteResult> =>
  connection.sendMessagePromise<WriteResult>({
    type: "myhome/calibration/cover_edit",
    entry_id: entryId,
    cover_unique_id: coverUniqueId,
    overrides,
    ...(height !== undefined ? { height } : {}),
  });

export interface CoverForgetResult extends WriteResult {
  falls_back_to: "profile" | "file" | "defaults";
  profile: string | null;
}

export const coverForget = (
  connection: HaConnection,
  entryId: string,
  coverUniqueId: string,
): Promise<CoverForgetResult> =>
  connection.sendMessagePromise<CoverForgetResult>({
    type: "myhome/calibration/cover_forget",
    entry_id: entryId,
    cover_unique_id: coverUniqueId,
  });

export interface ProfileEditResult extends WriteResult {
  affected: string[];
}

export const profileEdit = (
  connection: HaConnection,
  entryId: string,
  name: string,
  values: Record<string, number>,
  referenceHeight: number | null,
): Promise<ProfileEditResult> =>
  connection.sendMessagePromise<ProfileEditResult>({
    type: "myhome/calibration/profile_edit",
    entry_id: entryId,
    name,
    values,
    reference_height: referenceHeight,
  });

export interface ProfileRenameResult extends WriteResult {
  moved: number;
  from_file: string[];
}

export const profileRename = (
  connection: HaConnection,
  entryId: string,
  name: string,
  newName: string,
): Promise<ProfileRenameResult> =>
  connection.sendMessagePromise<ProfileRenameResult>({
    type: "myhome/calibration/profile_rename",
    entry_id: entryId,
    name,
    new_name: newName,
  });

export interface ProfileDeleteResult extends WriteResult {
  covers_affected: string[];
  from_file: string[];
}

export const profileDelete = (
  connection: HaConnection,
  entryId: string,
  name: string,
): Promise<ProfileDeleteResult> =>
  connection.sendMessagePromise<ProfileDeleteResult>({
    type: "myhome/calibration/profile_delete",
    entry_id: entryId,
    name,
  });

export interface UndoResult extends WriteResult {
  undone: string;
}

export const undo = (
  connection: HaConnection,
  entryId: string,
  undoToken: string,
): Promise<UndoResult> =>
  connection.sendMessagePromise<UndoResult>({
    type: "myhome/calibration/undo",
    entry_id: entryId,
    undo_token: undoToken,
  });
