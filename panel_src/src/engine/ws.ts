// Typed wrappers over the three read commands of `custom_components/myhome/websocket_api.py`.
//
// The shapes below are `custom_components/myhome/panel_schemas.py` restated in
// TypeScript, and that file says so in its own words: it is the frozen contract, and a
// change to either is a change to both. Nothing here re-derives anything the server
// already answered - not a cover's origin, not a rescaled profile value. That is the
// parity invariant: the panel and the `Calibration source` attribute must never disagree,
// and the only way to guarantee it is that one function computes it, on the server.

import { type HaConnection } from "../types/ha";
import {
  type SessionAction,
  type SessionAnswer,
  type SessionCancelAnswer,
  type SessionEndOtherAnswer,
  type SessionEvent,
  type SessionGetAnswer,
  type SessionHeartbeatAnswer,
  type OverviewSession,
  type SessionPath,
  type SessionSaveAnswer,
  type SessionSaveTarget,
  type SessionScope,
  type SessionSubmit,
} from "./session-contract";

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
  /**
   * Which client is holding a shutter of this gateway, or `null` for none (contract §4.5).
   *
   * `measuring` beside it says *that* one is being measured; this says *who*. A
   * `measuring` with no `session` is the *Configure* dialog or the 0.4.2 action - the two
   * holders this panel did not open and cannot drive - and that is the whole distinction
   * the banner is built on (SPEC §6).
   */
  session: OverviewSession | null;
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

/**
 * What "Rimuovi la misura" would leave, read before it removes anything (contract §3).
 *
 * The same three facts `cover_forget` answers with afterwards, computed the same way -
 * this window resolved once more with the record gone. `keys[].inherited_*` is **not**
 * the answer to this question: it takes the overrides away and leaves the record, which
 * is right for an emptied field and wrong for a removal that takes the assignment and
 * the travel with it.
 */
export interface CoverForgetOutcome {
  falls_back_to: "profile" | "file" | "defaults";
  profile: string | null;
  /** `myhome.yaml`'s own `height:` survives; a travel typed into this panel does not. */
  travel_stays: boolean;
}

export interface CoverDetail {
  entry_id: string;
  cover: CoverRow;
  keys: CoverKeyRow[];
  forget: CoverForgetOutcome;
}

/**
 * What a batch of assignments would come to, with none of them made (contract §11).
 *
 * The review panel's before/after table. The "after" is the profile brought to the
 * window's own travel with whatever it measured for itself still on top, and it comes
 * from the server for the same reason every other number on this screen does: the panel
 * would otherwise need a second copy of `derive_cover_from_profile`, and two copies of a
 * travel model are two answers. `items` are exactly `assign`'s `assignments`, so what is
 * previewed is the batch itself and not a translation of it.
 */
export interface PreviewKeyRow {
  key: string;
  value: number;
  origin: "own" | "profile" | "file" | "default";
}

export interface PreviewItem {
  cover_unique_id: string;
  profile: string | null;
  height: number | null;
  /**
   * The one thing that stops this item, or `null`. Always a `translation_key` `assign`
   * refuses with - `missing_travel`, `unknown_profile`, `out_of_range`, ... - so the row
   * shows the same sentence whether the problem was found before the write or by it.
   */
  problem: string | null;
  origin: string | null;
  source: string | null;
  values: Record<string, number>;
  keys: PreviewKeyRow[];
  has_own: string[];
}

export interface PreviewResult {
  entry_id: string;
  items: PreviewItem[];
}

/**
 * The numbers to pretend a profile has while the question is answered (contract §11).
 *
 * Exactly what `profile_edit` would write - the five values and the travel they were
 * measured at - because the profile card's impact preview asks what those numbers would
 * mean for each follower, and the panel may no more scale a profile for that screen than
 * for the review panel. The override replaces the numbers of a profile the gateway
 * already has; it never defines a new name.
 */
export type ProfileValues = Record<string, Record<string, number>>;

export const preview = (
  connection: HaConnection,
  entryId: string,
  items: AssignItem[],
  profileValues?: ProfileValues,
): Promise<PreviewResult> =>
  connection.sendMessagePromise<PreviewResult>({
    type: "myhome/calibration/preview",
    entry_id: entryId,
    items,
    ...(profileValues ? { profile_values: profileValues } : {}),
  });

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

/**
 * The third event (contract §11.4), pushed on subscribing and at every transition of the
 * gateway's calibration session. The type is the frozen contract's own: nothing about the
 * session is restated here.
 */
export type { SessionEvent };

export type CalibrationEvent = OverviewEvent | MeasuringEvent | SessionEvent;

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

// --- the calibration session (contract §11) --------------------------------------------
//
// Ten commands, one per line of `docs/panel-websocket-api.md` §11.2 and of
// `WS_SESSION_COMMANDS` in `panel_schemas.py`. The shapes come from
// `engine/session-contract.ts`, which is frozen: nothing is restated here, and a wrapper
// that invented a key would fail to compile against the request interfaces there.
//
// `entry_id` is required on every one of them, reads included: a session is always one
// gateway's. Only `engine/session.ts` calls these - the screens talk to the client, and
// the client talks to the socket - so that there is one place that knows what a verb
// means and one place that knows what it is called.

export const sessionGet = (
  connection: HaConnection,
  entryId: string,
): Promise<SessionGetAnswer> =>
  connection.sendMessagePromise<SessionGetAnswer>({
    type: "myhome/calibration/session/get",
    entry_id: entryId,
  });

export interface SessionStartFields {
  cover_unique_id: string;
  client_id: string;
  path?: SessionPath;
  /** Only with `path_b` or `path_c`; anything else is `invalid_format`. */
  profile?: string;
  /** Only with `path_c`. */
  scope?: SessionScope;
}

export const sessionStart = (
  connection: HaConnection,
  entryId: string,
  fields: SessionStartFields,
): Promise<SessionAnswer> =>
  connection.sendMessagePromise<SessionAnswer>({
    type: "myhome/calibration/session/start",
    entry_id: entryId,
    cover_unique_id: fields.cover_unique_id,
    client_id: fields.client_id,
    // Left out rather than sent as `undefined`: the schema refuses a key it does not
    // expect, and a `path` nobody chose is a key nobody sent.
    ...(fields.path ? { path: fields.path } : {}),
    ...(fields.profile ? { profile: fields.profile } : {}),
    ...(fields.scope ? { scope: fields.scope } : {}),
  });

export interface SessionAttachFields {
  session_id: string;
  client_id: string;
  claim?: boolean;
}

export const sessionAttach = (
  connection: HaConnection,
  entryId: string,
  fields: SessionAttachFields,
): Promise<SessionAnswer> =>
  connection.sendMessagePromise<SessionAnswer>({
    type: "myhome/calibration/session/attach",
    entry_id: entryId,
    session_id: fields.session_id,
    client_id: fields.client_id,
    ...(fields.claim ? { claim: true } : {}),
  });

export interface SessionClientFields {
  session_id: string;
  client_id: string;
}

export const sessionHeartbeat = (
  connection: HaConnection,
  entryId: string,
  fields: SessionClientFields,
): Promise<SessionHeartbeatAnswer> =>
  connection.sendMessagePromise<SessionHeartbeatAnswer>({
    type: "myhome/calibration/session/heartbeat",
    entry_id: entryId,
    session_id: fields.session_id,
    client_id: fields.client_id,
  });

export interface SessionActFields extends SessionClientFields {
  revision: number;
  action: SessionAction | SessionSubmit;
  /** A number goes as the text that was typed, so a decimal comma survives. */
  value?: string | number | null;
}

export const sessionAct = (
  connection: HaConnection,
  entryId: string,
  fields: SessionActFields,
): Promise<SessionAnswer> =>
  connection.sendMessagePromise<SessionAnswer>({
    type: "myhome/calibration/session/act",
    entry_id: entryId,
    session_id: fields.session_id,
    client_id: fields.client_id,
    revision: fields.revision,
    action: fields.action,
    ...(fields.value === undefined ? {} : { value: fields.value }),
  });

export const sessionStop = (
  connection: HaConnection,
  entryId: string,
  fields: SessionClientFields,
): Promise<SessionAnswer> =>
  connection.sendMessagePromise<SessionAnswer>({
    type: "myhome/calibration/session/stop",
    entry_id: entryId,
    session_id: fields.session_id,
    client_id: fields.client_id,
  });

export const sessionLeave = (
  connection: HaConnection,
  entryId: string,
  fields: SessionClientFields,
): Promise<SessionAnswer> =>
  connection.sendMessagePromise<SessionAnswer>({
    type: "myhome/calibration/session/leave",
    entry_id: entryId,
    session_id: fields.session_id,
    client_id: fields.client_id,
  });

export interface SessionCancelFields {
  client_id: string;
  /** Left out: the gateway's session, whichever it is. */
  session_id?: string;
  /** Ends it whoever owns it - the way out that always works. */
  force?: boolean;
}

export const sessionCancel = (
  connection: HaConnection,
  entryId: string,
  fields: SessionCancelFields,
): Promise<SessionCancelAnswer> =>
  connection.sendMessagePromise<SessionCancelAnswer>({
    type: "myhome/calibration/session/cancel",
    entry_id: entryId,
    client_id: fields.client_id,
    ...(fields.session_id ? { session_id: fields.session_id } : {}),
    ...(fields.force ? { force: true } : {}),
  });

export interface SessionSaveFields extends SessionClientFields {
  revision: number;
  target: SessionSaveTarget;
}

export const sessionSave = (
  connection: HaConnection,
  entryId: string,
  fields: SessionSaveFields,
): Promise<SessionSaveAnswer> =>
  connection.sendMessagePromise<SessionSaveAnswer>({
    type: "myhome/calibration/session/save",
    entry_id: entryId,
    session_id: fields.session_id,
    client_id: fields.client_id,
    revision: fields.revision,
    target: fields.target,
  });

export const sessionEndOther = (
  connection: HaConnection,
  entryId: string,
): Promise<SessionEndOtherAnswer> =>
  connection.sendMessagePromise<SessionEndOtherAnswer>({
    type: "myhome/calibration/session/end_other",
    entry_id: entryId,
  });
