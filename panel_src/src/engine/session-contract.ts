// The guided calibration's session, as the panel sees it on the wire: types and nothing
// else.
//
// This file is `custom_components/myhome/panel_schemas.py`'s session block restated in
// TypeScript (0.6.0 wizard, lot L0). The two are frozen together with
// `docs/panel-websocket-api.md` §11-§14 and `tests/fixtures/panel_session_examples.json`,
// and `tests/test_session_contract.py` reads this file back to hold every union and every
// interface below to the Python tuple it restates: a change to one is a change to all
// four, in one commit that says it is a contract amendment.
//
// There is deliberately no executable code here. The client (`session.ts`, lot F1) and
// the screens (`wizard/*`, lot F2) import these shapes; nothing imports a value, so
// nothing here can drift from the server by being "helpful".
//
// Two vocabularies meet in a snapshot, on purpose. `state`, the verbs and the names of
// measured values are the published contract's (`docs/calibration-contract-proposal.md`
// Part 2): `awaiting_endpoint`, `travel_cm`, `opening_time_s`. `step`, `actions`,
// `form.field`, `placeholders` and `movement.progress_action` are the guided dialog's own
// ids, because they are the keys of sentences already translated into seven languages
// (`options.step.<step>`, `options.progress.<action>`) that the panel shows as they are.

/** An instant, ISO-8601 in UTC, from the backend's clock - the only clock a measurement reads. */
export type IsoTime = string;

// ------------------------------------------------------------------ the vocabularies

/** The contract's states (§2.2) plus the terminal `ended`. No session is `session: null`. */
export type SessionState =
  | "armed"
  | "briefing"
  | "running"
  | "positioning"
  | "awaiting_reading"
  | "checking"
  | "review"
  | "saved"
  | "ended";

/** Only in `running`, once the motor has echoed; `null` while it is starting. */
export type SessionSubstate = "awaiting_endpoint" | "awaiting_stop";

/** `outcome.reason`: `saved` goes with `state: "saved"`, the rest with `"ended"`. */
export type SessionOutcomeReason =
  | "saved"
  | "cancelled"
  | "expired"
  | "unloaded"
  | "left"
  | "cover_gone";

/** `problem.code`: the dialog's reasons, plus `interrupted`. The step is `problem_<code>`. */
export type SessionProblemCode =
  | "no_echo"
  | "not_delivered"
  | "not_stopped"
  | "busy"
  | "bad_point"
  | "timeout"
  | "unknown"
  | "interrupted";

export type SessionPath = "path_a" | "path_b" | "path_c";

export type SessionScope = "times_only" | "times_and_rolls" | "points_only";

/** The contract's levels; the dialog's texts say "precise" for the second. */
export type SessionLevel = "basic" | "thorough";

export type SessionSaveTarget = "profile" | "cover_only";

/** `review.variant`: the `summary_<variant>` step the review stands on. */
export type SessionReviewVariant = "basic" | "short" | "correction" | "precise";

/** The end stop the session last saw the shutter reach. */
export type SessionPosition = "closed" | "open";

export type SessionDirection = "open" | "close";

export type SessionMovementKind = "homing" | "free" | "fraction";

/** `movement.progress_action`: the key of `options.progress.<action>` for that movement. */
export type SessionProgressAction =
  | "homing_closed"
  | "homing_open"
  | "starting_open"
  | "starting_close"
  | "running_down"
  | "running_up"
  | "stopping_lift"
  | "starting_open_full";

export type SessionPressKind = "lift_off" | "end_stop";

export type SessionFormField = "profile" | "height" | "measured_cm" | "gap_cm" | "name";

export type SessionFormKind = "number" | "choice" | "text";

/** The one unit a field of this conversation carries; a name has none. */
export type SessionFormUnit = "cm";

/** The dialog's `options.error.*` keys: the contract's `bad_reading`, in detail. */
export type SessionFormError =
  | "not_a_number"
  | "out_of_range"
  | "above_the_travel"
  | "invalid_name";

/**
 * Something to say about what happened around the step, which is not a problem.
 * `rehomed`: the shutter had been moved from outside and was brought back to its end stop
 * before anything was timed. `reading_stale`: it was moved after it was positioned, so
 * the reading on the screen is no longer the reading of this step.
 */
export type SessionNotice = "rehomed" | "reading_stale";

/**
 * `already_calibrating`'s `{by}`: a live session of the panel's, something else holding
 * the shutter (the dialog, the 0.4.2 action), or the gateway still reserved by a session
 * that has ended while its shutter ran on — which is nothing to go back to, so the screen
 * says to wait rather than offering to resume it.
 */
export type SessionHolder = "panel" | "other" | "reserved";

/** Every step a snapshot can stand on, under the dialog's own ids. */
export type SessionStep =
  | "path"
  | "path_a"
  | "path_b"
  | "path_c"
  | "refine_scope"
  | "home_closed"
  | "home_closed_done"
  | "open_timed"
  | "open_brief"
  | "open_start"
  | "open_lift"
  | "lift_stop"
  | "lift_check"
  | "lift_check_late"
  | "lift_gap"
  | "lift_early"
  | "open_home_again"
  | "closed_again"
  | "open_full_brief"
  | "open_full_start"
  | "open_top"
  | "open_result"
  | "open_result_gap"
  | "height_read"
  | "height"
  | "height_result"
  | "close_timed"
  | "close_brief"
  | "close_start"
  | "close_bottom"
  | "close_result"
  | "tape_brief"
  | "half_down"
  | "half_up"
  | "quarter_down"
  | "three_quarter_down"
  | "quarter_up"
  | "three_quarter_up"
  | "verify"
  | "verify_b"
  | "tape_run"
  | "measure_descent"
  | "measure_ascent"
  | "tape_result"
  | "measure_verify"
  | "verify_result"
  | "verify_offer"
  | "profile_name"
  | "summary_basic"
  | "summary_short"
  | "summary_correction"
  | "summary_precise"
  | "problem_no_echo"
  | "problem_not_delivered"
  | "problem_not_stopped"
  | "problem_busy"
  | "problem_bad_point"
  | "problem_timeout"
  | "problem_unknown"
  | "problem_interrupted";

/**
 * The steps whose dialog texts (`options.step.<step>`) the panel shows as they are: every
 * step with texts of its own except the four summaries, which speak of the dialog.
 */
export type SessionReusedStep =
  | "path"
  | "path_a"
  | "path_b"
  | "path_c"
  | "refine_scope"
  | "home_closed_done"
  | "open_brief"
  | "open_lift"
  | "lift_check"
  | "lift_check_late"
  | "lift_gap"
  | "lift_early"
  | "closed_again"
  | "open_full_brief"
  | "open_top"
  | "open_result"
  | "open_result_gap"
  | "height"
  | "height_result"
  | "close_brief"
  | "close_bottom"
  | "close_result"
  | "tape_brief"
  | "measure_descent"
  | "measure_ascent"
  | "tape_result"
  | "measure_verify"
  | "verify_result"
  | "verify_offer"
  | "profile_name"
  | "problem_no_echo"
  | "problem_not_delivered"
  | "problem_not_stopped"
  | "problem_busy"
  | "problem_bad_point"
  | "problem_timeout"
  | "problem_unknown";

/** What `plan` may contain: the dialog's plan stages, `summary` included. */
export type SessionPlanStage =
  | "home_closed"
  | "open_timed"
  | "height_read"
  | "close_timed"
  | "tape_brief"
  | "half_down"
  | "half_up"
  | "quarter_down"
  | "three_quarter_down"
  | "quarter_up"
  | "three_quarter_up"
  | "verify"
  | "verify_b"
  | "verify_offer"
  | "profile_name"
  | "summary";

/**
 * Every value `actions` can carry: the dialog's `menu_options` ids, whose labels are
 * `options.step.<step>.menu_options.<action>`. Ways forward only — the dialog's two ways
 * out are commands of their own: `save` is the `save` command (its exits are
 * `review.targets`), and `cancel_flow` is the `cancel` verb, which carries no revision
 * and can never be refused for concurrency.
 */
export type SessionAction =
  | "path_a"
  | "path_b"
  | "path_c"
  | "begin"
  | "times_only"
  | "times_and_rolls"
  | "points_only"
  | "confirm_closed"
  | "open_start"
  | "lifted_off"
  | "lift_too_early"
  | "lift_accept"
  | "lift_gap"
  | "confirm_closed_again"
  | "open_full_start"
  | "stopped_open"
  | "accept_step"
  | "repeat_measure"
  | "close_start"
  | "stopped_closed"
  | "tape_start"
  | "repeat_tape"
  | "tape_not_right"
  | "verify_now"
  | "skip_verify"
  | "refine"
  | "repeat_step"
  | "not_right";

/** The one `act` value that is not a menu option: send `form`'s value. */
export type SessionSubmit = "submit";

/** `review.rows[].key`, in the order the review lists them. */
export type SessionReviewRowKey =
  | "travel_cm"
  | "opening_time_s"
  | "closing_time_s"
  | "slat_time_s"
  | "opening_roll"
  | "closing_roll";

/** `review.side_effects[].key`: any of the rows' keys, or one of the two bus costs. */
export type SessionValueKey = SessionReviewRowKey | "stop_latency_s" | "start_delay_s";

/** The refusals the session adds (`translation_key`), beside the ones that already exist. */
export type SessionErrorKey =
  | "already_calibrating"
  | "cover_unavailable"
  | "unknown_session"
  | "session_ended"
  | "session_owned"
  | "revision_conflict"
  | "action_not_offered"
  | "not_in_review";

export type SessionCommandType =
  | "myhome/calibration/session/get"
  | "myhome/calibration/session/start"
  | "myhome/calibration/session/attach"
  | "myhome/calibration/session/heartbeat"
  | "myhome/calibration/session/act"
  | "myhome/calibration/session/stop"
  | "myhome/calibration/session/leave"
  | "myhome/calibration/session/cancel"
  | "myhome/calibration/session/save"
  | "myhome/calibration/session/end_other";

// ---------------------------------------------------------------------- the snapshot

export interface SessionCover {
  unique_id: string;
  entity_id: string | null;
  name: string;
}

/** Present only when `start` named a scope: the one `refine_scope` highlights. */
export interface SessionIntent {
  scope: SessionScope;
}

export interface SessionForm {
  field: SessionFormField;
  kind: SessionFormKind;
  optional: boolean;
  unit: SessionFormUnit | null;
  /** What the field opens on: a number, a name, or the profile preselected. */
  suggested: number | string | null;
  min: number | null;
  max: number | null;
  /** The profiles to choose from, sorted, for `kind: "choice"`. */
  choices: string[] | null;
  error: SessionFormError | null;
}

export interface SessionMovement {
  kind: SessionMovementKind;
  direction: SessionDirection;
  /** The dialog's text for this movement: `options.progress.<progress_action>`. */
  progress_action: SessionProgressAction;
  /** The motion anchor; `null` while the motor is starting. */
  started_at: IsoTime | null;
  /** The modelled duration, for a progress bar only: no measurement reads it. */
  planned_s: number | null;
}

export interface SessionPress {
  kind: SessionPressKind;
  expires_at: IsoTime;
}

export interface SessionReading {
  direction: SessionDirection;
  fraction: number;
  from_end_stop: SessionPosition;
  expected_cm: number | null;
  tolerance_cm: number;
}

export interface SessionLift {
  pressed_at: IsoTime;
  stop_written_at: IsoTime | null;
  gap_cm: number | null;
  late: boolean;
}

/** `[motor seconds of the run, centimetres the tape read]`. */
export type SessionReadingPoint = [number, number];

export interface SessionMeasured {
  travel_cm: number | null;
  travel_measured: boolean;
  opening_time_s: number | null;
  closing_time_s: number | null;
  slat_time_s: number | null;
  lift: SessionLift | null;
  descent: SessionReadingPoint[];
  ascent: SessionReadingPoint[];
  times_adopted: boolean;
}

export interface SessionFitPoint {
  motor_s: number;
  measured_cm: number;
  /** Model minus tape; `null` for a direction fitted through a single point. */
  residual_cm: number | null;
}

export interface SessionFitDirection {
  run_time_s: number;
  slat_time_s: number;
  roll: number;
  time_scale: number;
  points: SessionFitPoint[];
}

export interface SessionFit {
  opening: SessionFitDirection;
  closing: SessionFitDirection;
}

export interface SessionCheck {
  fraction: number;
  predicted_cm: number;
  measured_cm: number;
  gap_cm: number;
  /** The threshold above which path B offers the correction; `null` outside path B. */
  threshold_cm: number | null;
  profile_level: SessionLevel | null;
  profile_check_cm: number | null;
}

/** A row of `rows`: always the six measured keys, in the order of `SessionReviewRowKey`. */
export interface SessionReviewMeasuredRow {
  key: SessionReviewRowKey;
  before: number | null;
  after: number | null;
}

/** A row of `side_effects`, which may name a key this calibration never measured. */
export interface SessionReviewRow {
  key: SessionValueKey;
  before: number | null;
  after: number | null;
}

export interface SessionReviewAffected {
  cover_unique_id: string;
  name: string;
  rows: SessionReviewMeasuredRow[];
}

export interface SessionReview {
  variant: SessionReviewVariant;
  /** The exits offered, the first being the main one. */
  targets: SessionSaveTarget[];
  profile_name: string | null;
  profile_exists: boolean;
  name_clash: "file" | null;
  rows: SessionReviewMeasuredRow[];
  side_effects: SessionReviewRow[];
  affected: SessionReviewAffected[];
  accuracy_cm: number | null;
  check_fraction: number | null;
  replacing: SessionReviewRowKey[];
  keeping: SessionReviewRowKey[];
  yaml: string;
}

export interface SessionProblem {
  code: SessionProblemCode;
}

export interface SessionOwner {
  client_id: string;
  present_until: IsoTime;
}

export interface SessionOutcome {
  reason: SessionOutcomeReason;
  profile: string | null;
  /** `overview`'s `origin` token for the shutter afterwards, when it was saved. */
  origin: string | null;
  /** …and the exact `Calibration source` string. */
  source: string | null;
}

/** The whole session, at one revision. Every key is always present. */
export interface SessionSnapshot {
  session_id: string;
  entry_id: string;
  revision: number;
  server_time: IsoTime;
  cover: SessionCover;
  state: SessionState;
  substate: SessionSubstate | null;
  step: SessionStep | null;
  path: SessionPath | null;
  scope: SessionScope | null;
  profile: string | null;
  level: SessionLevel;
  plan: SessionPlanStage[];
  plan_index: number | null;
  intent: SessionIntent | null;
  actions: SessionAction[];
  form: SessionForm | null;
  /** Raw values under the dialog's placeholder names; the panel formats them. */
  placeholders: Record<string, string | number | null>;
  movement: SessionMovement | null;
  press: SessionPress | null;
  reading: SessionReading | null;
  measured: SessionMeasured;
  fit: SessionFit | null;
  check: SessionCheck | null;
  review: SessionReview | null;
  problem: SessionProblem | null;
  notice: SessionNotice | null;
  position_known: SessionPosition | null;
  external_move: boolean;
  owner: SessionOwner | null;
  idle_expires_at: IsoTime | null;
  outcome: SessionOutcome | null;
}

export interface SessionCapabilities {
  model: "roll_nonlinear";
  paths: SessionPath[];
  levels: SessionLevel[];
  scopes: SessionScope[];
  check: boolean;
  fit_residuals: boolean;
  repeat_step: boolean;
  save_targets: SessionSaveTarget[];
  bulk: boolean;
}

// ----------------------------------------------------------------------- the commands

export interface SessionGetRequest {
  type: "myhome/calibration/session/get";
  entry_id: string;
}

export interface SessionStartRequest {
  type: "myhome/calibration/session/start";
  entry_id: string;
  cover_unique_id: string;
  client_id: string;
  path?: SessionPath;
  /** Only with `path_b` or `path_c`. */
  profile?: string;
  /** Only with `path_c`: highlighted on `refine_scope`, never chosen for the user. */
  scope?: SessionScope;
}

export interface SessionAttachRequest {
  type: "myhome/calibration/session/attach";
  entry_id: string;
  session_id: string;
  client_id: string;
  claim?: boolean;
}

export interface SessionHeartbeatRequest {
  type: "myhome/calibration/session/heartbeat";
  entry_id: string;
  session_id: string;
  client_id: string;
}

export interface SessionActRequest {
  type: "myhome/calibration/session/act";
  entry_id: string;
  session_id: string;
  client_id: string;
  revision: number;
  action: SessionAction | SessionSubmit;
  /** The text typed (a number stays a string), the profile chosen, or nothing. */
  value?: string | number | null;
}

export interface SessionStopRequest {
  type: "myhome/calibration/session/stop";
  entry_id: string;
  session_id: string;
  client_id: string;
}

export interface SessionLeaveRequest {
  type: "myhome/calibration/session/leave";
  entry_id: string;
  session_id: string;
  client_id: string;
}

export interface SessionCancelRequest {
  type: "myhome/calibration/session/cancel";
  entry_id: string;
  /** Left out: the gateway's session, whichever it is. */
  session_id?: string;
  client_id: string;
  /** Ends it whoever owns it. */
  force?: boolean;
}

export interface SessionSaveRequest {
  type: "myhome/calibration/session/save";
  entry_id: string;
  session_id: string;
  client_id: string;
  revision: number;
  target: SessionSaveTarget;
}

export interface SessionEndOtherRequest {
  type: "myhome/calibration/session/end_other";
  entry_id: string;
}

export type SessionRequest =
  | SessionGetRequest
  | SessionStartRequest
  | SessionAttachRequest
  | SessionHeartbeatRequest
  | SessionActRequest
  | SessionStopRequest
  | SessionLeaveRequest
  | SessionCancelRequest
  | SessionSaveRequest
  | SessionEndOtherRequest;

// ------------------------------------------------------------------------ the answers

export interface SessionGetAnswer {
  session: SessionSnapshot | null;
  capabilities: SessionCapabilities;
}

/** `start`, `attach`, `act`, `stop`; `leave` too, where `null` means nothing to leave. */
export interface SessionAnswer {
  session: SessionSnapshot | null;
}

export interface SessionHeartbeatAnswer {
  owner: boolean;
  present_until: IsoTime | null;
}

export interface SessionCancelAnswer {
  session: SessionSnapshot | null;
  already_ended: boolean;
}

/**
 * `overview` is the whole `myhome/calibration/overview` answer (`ws.ts`), rebuilt after
 * the write. Typed loosely here so that this file depends on nothing.
 */
export interface SessionSaveAnswer {
  session: SessionSnapshot;
  overview: Record<string, unknown>;
}

export interface SessionEndOtherAnswer {
  flows_aborted: number;
  still_calibrating: boolean;
  overview: Record<string, unknown>;
}

/**
 * `overview.session`: the one line the banner and the first-run screen need.
 *
 * The server sends it from the lot that builds the session; the shape is here so that
 * both halves write against it rather than inventing it. `measuring` in the same
 * overview says *that* a shutter is being measured; this says *who*, and a `measuring`
 * with no `session` beside it is the dialog or the 0.4.2 action.
 */
export interface OverviewSession {
  session_id: string;
  cover_unique_id: string;
  name: string;
  state: SessionState;
  /** The owner's `client_id`, or `null` when the session has no owner. */
  owner: string | null;
}

/** The third event of `myhome/calibration/subscribe`. */
export interface SessionEvent {
  type: "session";
  session: SessionSnapshot | null;
}
