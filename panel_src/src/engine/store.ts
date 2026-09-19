// The client state, in one place, with one rule.
//
// The rule, from the contract: **the server model is replaced whole and the client model
// is never merged into it.** `overview` arrives complete on every read and on every push,
// and anything the user is in the middle of - a search string, a filter, a pending
// assignment - lives beside it and never inside it. A client that merges pushes into a
// model it also edits eventually shows a shutter following a profile the server deleted,
// and the way to make that impossible is to keep the two in different fields.
//
// That is why the assignment screen is built the way it is. A drag does not move a row in
// `overview.covers`; it adds a `PendingChange` beside it, and the groups are drawn by
// laying the pending changes over the server's model at render time. So a push that
// arrives mid-gesture replaces the model underneath and the user's half-finished work
// survives it - or, where it cannot (the shutter was deleted), quietly stops applying to
// anything, which is the honest outcome.
//
// No Redux, no signals library, no reactive controller. A panel with one writer and a
// handful of readers needs a field, a `subscribe` and a `set`; anything more is a
// dependency somebody has to keep in step with Lit.

import { type Route } from "./router";
import { type SessionTrouble, type WizardIntent } from "./session";
import { type SessionSnapshot } from "./session-contract";
import { type CoverDetail, type Overview, type PreviewItem, type WsError } from "./ws";

/** Where the model is coming from, which the panel says out loud when it is not live. */
export type Connection = "starting" | "live" | "polling" | "offline";

/**
 * One shutter on its way to another group, and nothing written yet.
 *
 * `to` is the profile it is heading for, `null` being "Senza profilo". A change back to
 * where the shutter already is is not a change: `withPending` below withdraws it instead
 * of recording it, which is the prototype's own rule and the reason the count on the bar
 * can be trusted.
 */
export interface PendingChange {
  cover: string;
  to: string | null;
}

/** Where in a group a drop would land: before a row, after one, or at the end. */
export interface InsertPoint {
  group: string;
  beforeId: string | null;
  afterId: string | null;
  end: boolean;
}

/** A row in flight: which shutter, what it is called, and what is under the pointer. */
export interface DragState {
  cover: string;
  name: string;
  over: string | null;
  insert: InsertPoint | null;
}

/** The feedback strip: one sentence, and the token that takes the write back. */
export interface Snack {
  message: string;
  undoToken: string | null;
}

/**
 * The routed cover detail (`#/cover/<unique_id>`), which is a second server model.
 *
 * It is kept beside `overview` rather than inside it for the same reason the pending
 * changes are: `cover_detail` answers a different question - per key, where each number
 * comes from and what it would fall back to - and a push replaces the overview without
 * saying anything about the shutter whose card is open. `for` records which shutter the
 * answer is about, so a stale answer is never drawn under a new name.
 *
 * `mode` is the prototype's own four states, and the three that are not `view` are the
 * three that write.
 */
export interface DetailState {
  for: string | null;
  answer: CoverDetail | null;
  loading: boolean;
  error: WsError | null;
  mode: "view" | "edit" | "travel" | "correct" | "remove";
  /** The five value fields and `height`, as typed. An empty field means "inherit". */
  form: Record<string, string>;
  /** What the panel's own pre-validation found; the server checks again and wins. */
  errors: Record<string, string>;
  /**
   * What the typed travel would come to, from `preview`. Only the travel: a hand-edited
   * value is either the number typed or the key's own `inherited_value`, which
   * `cover_detail` already answers, and asking the server to repeat it would be a round
   * trip for a lookup. A travel, on the other hand, rescales the profile - which is
   * arithmetic, and therefore the server's.
   */
  preview: PreviewItem | null;
  previewing: boolean;
}

/**
 * The routed profile card (`#/profile/<name>`). Everything it draws except the impact
 * preview comes out of `overview`, which already carries every profile whole.
 */
export interface ProfileState {
  for: string | null;
  mode: "view" | "edit" | "rename" | "delete";
  /** The five values and `reference_height`, as typed. */
  form: Record<string, string>;
  errors: Record<string, string>;
  /** The rename field and what is wrong with it. */
  newName: string;
  nameError: string;
  /**
   * One `preview` item per follower, answered with the typed numbers in the profile's
   * place (`profile_values`, contract §11). The panel does not scale a profile on this
   * screen any more than on the review panel.
   */
  impact: PreviewItem[] | null;
  impacting: boolean;
}

export const NO_DETAIL: DetailState = {
  for: null,
  answer: null,
  loading: false,
  error: null,
  mode: "view",
  form: {},
  errors: {},
  preview: null,
  previewing: false,
};

export const NO_PROFILE_CARD: ProfileState = {
  for: null,
  mode: "view",
  form: {},
  errors: {},
  newName: "",
  nameError: "",
  impact: null,
  impacting: false,
};

export interface PanelState {
  /** The gateway this model is about; `null` until the first answer names one. */
  entryId: string | null;
  /** The server's whole answer, or `null` while there has not been one. */
  overview: Overview | null;
  status: "loading" | "ready" | "error";
  error: WsError | null;
  connection: Connection;
  route: Route;
  /** Client-side only: the search box and the room select of the overview. */
  search: string;
  room: string;
  /** The sentence the live region reads out next. */
  announce: string;

  // --- the assignment, none of which is on the server yet ----------------------------
  /** The changes the user has made and not confirmed. */
  pending: PendingChange[];
  /**
   * The whole gateway's order as the user has dragged it, or `null` while they have not.
   * It travels with the batch (`assign`'s `order`) when there are assignments to write,
   * and on its own through `reorder` when a drop only moved a row inside its group.
   */
  order: string[] | null;
  /** The row in flight, on a pointer drag. */
  drag: DragState | null;
  /** The phone's "grab and tap the destination": the shutter waiting for a target. */
  armed: string | null;
  /** "Quale profilo?" is open for this shutter - the tap and keyboard path. */
  dialog: string | null;
  /** The review panel / bottom sheet. */
  review: boolean;
  /** The travels typed into the review panel's form, as typed. */
  heights: Record<string, string>;
  /** True once "Conferma" has been pressed with a travel missing: errors show from then. */
  heightsForced: boolean;
  /** "Mostra tutto": the two roll coefficients in the before/after table. */
  showAll: boolean;
  /** What the server says the batch would come to, or `null` while it has not said. */
  preview: PreviewItem[] | null;
  previewing: boolean;
  /** A write is in flight: every control that could start a second one is disabled. */
  applying: boolean;
  /** The feedback strip, with its undo token while the slot lasts. */
  snack: Snack | null;
  /** A refused write, shown where the user was working and never as a whole-page error. */
  writeError: WsError | null;

  // --- the two routed cards (lot 8) --------------------------------------------------
  detail: DetailState;
  profile: ProfileState;

  // --- the guided calibration (0.6.0 wizard) -----------------------------------------
  //
  // A third server model, kept beside the other two under the same rule: the snapshot is
  // replaced whole at every transition and nothing of the panel's is merged into it.
  /** The gateway's session, as the server last described it, or `null` for none. */
  session: SessionSnapshot | null;
  /**
   * A refusal the wizard has to answer, with the ways out it offers.
   *
   * It carries the recovery tokens rather than the bare refusal because of lesson 2: a
   * screen that can show an error and nothing to press is the silent failure with an
   * error message on it.
   */
  sessionError: SessionTrouble | null;
  /**
   * What the user asked to calibrate, on its way to `start` - and **never in the URL**
   * (SPEC §5.1): reloading `#/calibrate` reads the session and can never open one.
   */
  wizardIntent: WizardIntent | null;
  /** This browser tab's name in the session, from `sessionStorage` where there is one. */
  clientId: string;
  /**
   * The wizard's "Leave the calibration?" question, open or shut.
   *
   * In the store and not in the element because the control that asks it is not in the
   * element: the ✕ is in the panel's own toolbar (SPEC §5.1), beside the shutter's name
   * and the phase, and the dialog it opens belongs to the screen underneath it.
   */
  wizardExit: boolean;
}

export const initialState = (route: Route): PanelState => ({
  entryId: null,
  overview: null,
  status: "loading",
  error: null,
  connection: "starting",
  route,
  search: "",
  room: "",
  announce: "",
  pending: [],
  order: null,
  drag: null,
  armed: null,
  dialog: null,
  review: false,
  heights: {},
  heightsForced: false,
  showAll: false,
  preview: null,
  previewing: false,
  applying: false,
  snack: null,
  writeError: null,
  detail: NO_DETAIL,
  profile: NO_PROFILE_CARD,
  session: null,
  sessionError: null,
  wizardIntent: null,
  clientId: "",
  wizardExit: false,
});

/** Everything the user was composing, dropped: what "Scarta tutto" and a confirm leave. */
export const NOTHING_PENDING = {
  pending: [] as PendingChange[],
  order: null,
  heights: {} as Record<string, string>,
  heightsForced: false,
  preview: null,
  previewing: false,
  review: false,
  writeError: null,
} satisfies Partial<PanelState>;

export class Store {
  private _state: PanelState;
  private _subscribers = new Set<(state: PanelState) => void>();

  constructor(route: Route) {
    this._state = initialState(route);
  }

  get state(): PanelState {
    return this._state;
  }

  subscribe(callback: (state: PanelState) => void): () => void {
    this._subscribers.add(callback);
    return () => this._subscribers.delete(callback);
  }

  /**
   * Write some fields and tell everybody. Nothing is diffed: Lit already decides what to
   * repaint, and a store that tried to be clever about it would be a second renderer.
   */
  set(patch: Partial<PanelState>): void {
    this._state = { ...this._state, ...patch };
    for (const callback of this._subscribers) {
      callback(this._state);
    }
  }

  /**
   * A fresh server answer: the model, and nothing the user was typing.
   *
   * The pending changes are **kept**, deliberately. A push arrives after every write of
   * every browser tab on this gateway, and one of those is not a reason to throw away the
   * six assignments somebody is halfway through composing here. What does clear them is
   * confirming them, or asking to (`NOTHING_PENDING`).
   */
  setOverview(overview: Overview): void {
    this.set({
      overview,
      entryId: overview.entry_id,
      status: "ready",
      error: null,
    });
  }

  setError(error: WsError): void {
    this.set({ status: "error", error });
  }

  /** Said once, and cleared, so the same sentence twice is read twice. */
  announce(message: string): void {
    this.set({ announce: "" });
    this.set({ announce: message });
  }
}
