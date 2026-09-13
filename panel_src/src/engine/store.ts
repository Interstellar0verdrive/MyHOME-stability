// The client state, in one place, with one rule.
//
// The rule, from the contract: **the server model is replaced whole and the client model
// is never merged into it.** `overview` arrives complete on every read and on every push,
// and anything the user is in the middle of - a search string, a filter, a pending
// assignment in lot 7 - lives beside it and never inside it. A client that merges pushes
// into a model it also edits eventually shows a shutter following a profile the server
// deleted, and the way to make that impossible is to keep the two in different fields.
//
// No Redux, no signals library, no reactive controller. A panel with one writer and a
// handful of readers needs a field, a `subscribe` and a `set`; anything more is a
// dependency somebody has to keep in step with Lit.

import { type Route } from "./router";
import { type Overview, type WsError } from "./ws";

/** Where the model is coming from, which the panel says out loud when it is not live. */
export type Connection = "starting" | "live" | "polling" | "offline";

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
});

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

  /** A fresh server answer: the model, and nothing the user was typing. */
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
