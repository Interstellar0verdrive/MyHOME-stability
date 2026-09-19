// The guided calibration's session, as this browser tab holds it: one class, no Lit and
// no DOM.
//
// The session itself lives on the server (contract §11.1): closing a tab, locking a phone
// or losing the socket does not end it. What lives here is the little that has to live in
// the browser - who this tab is, what the last snapshot said, when to say "still here" -
// and the rules that keep the three failures of the v2 panel from happening again.
//
// **Lesson 1: the presence signal does not depend on the drawing.** The heartbeat is a
// `setInterval` of this class's own, started by `start()` or `attach()` and stopped only
// by the end of the session, by `leave()` or by `dispose()`. Nothing in `render()`,
// `updated()` or any other paint-time callback touches it, and a listener that throws
// cannot reach it: every notification goes out inside a `try`. In the v2 panel the
// heartbeat was sent from the render path, so the first drawing error quietly stopped it
// and the server took the session away from a user who was standing at the window with a
// tape measure in their hand.
//
// **Lesson 2: cancelling never fails in silence.** `cancel()` answers with one of four
// branches and each of them carries something the screen can offer - take control, try
// again, end it anyway, or the instant at which the gateway frees the shutter by itself.
// No branch answers `undefined`, and no error is swallowed.
//
// **Lesson 5: ownership is per browser tab, and taking it is deliberate.** The
// `client_id` is kept in `sessionStorage`, so reloading the page stays the same owner and
// a second tab is a second client. A heartbeat never takes ownership (contract §11.1,
// amended 19 September 2026): a tab left open on the wizard must not become the owner by
// doing nothing while the phone in the user's hand is asleep. Ownership moves on a verb
// that does something, or on an `attach` - implicitly while the owner is away, and with
// `claim` after the screen has asked.
//
// A session picked up again shows where it stands and re-enters nothing: no method here
// sends an `act` on its own, and `get()` and `attach()` are reads (contract §11.1).

import { type SessionAction, type SessionSaveTarget, type SessionSnapshot,
  type SessionCapabilities, type SessionPath, type SessionScope, type SessionSubmit,
  type IsoTime } from "./session-contract";
import {
  asWsError,
  sessionAct,
  sessionAttach,
  sessionCancel,
  sessionGet,
  sessionHeartbeat,
  sessionLeave,
  sessionSave,
  sessionStart,
  sessionStop,
  type Overview,
  type WsError,
} from "./ws";
import { type HaConnection } from "../types/ha";

/** Every fifteen seconds, as the contract fixes it; presence lapses at forty-five. */
export const HEARTBEAT_MS = 15_000;

/** Where the tab's identity is kept, so that a reload is the same owner. */
export const CLIENT_ID_KEY = "myhome-calibration-client";

/** The pattern the backend's schema accepts (`^[A-Za-z0-9-]{8,64}$`). */
const CLIENT_ID = /^[A-Za-z0-9-]{8,64}$/;

/** What the panel holds of `sessionStorage`, so that nothing here needs a window. */
export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

/**
 * What the user asked to calibrate, on its way to `start`.
 *
 * It travels in the store and **never in the address** (SPEC §5.1, decision 24): a route
 * that carried a cover would start a session every time somebody reloaded the page.
 */
export interface WizardIntent {
  cover: string;
  /** The shutter's name, for the screen to say while the first snapshot is in the air. */
  name?: string;
  path?: SessionPath;
  profile?: string;
  scope?: SessionScope;
}

/**
 * What a screen can offer after something went wrong. Never a sentence, never a function:
 * the wizard turns each token into one of its own buttons.
 *
 * * `retry` - send the same thing again;
 * * `claim` - take the session from the client that owns it, then repeat;
 * * `force` - end it whoever owns it (`cancel` with `force`), the way out that always works;
 * * `reload` - read the session again, because it has moved on;
 * * `wait` - nothing left to press: the gateway frees the shutter by itself at `freedAt`.
 */
export type SessionRecovery = "retry" | "claim" | "force" | "reload" | "wait";

/** A refusal, and what can be done about it. The recovery list is never empty. */
export interface SessionTrouble {
  error: WsError;
  recovery: SessionRecovery[];
  /** `idle_expires_at` of the session, when the only thing left is to let it lapse. */
  freedAt: IsoTime | null;
}

export interface SessionDone {
  ok: true;
  session: SessionSnapshot | null;
  /** `save` answers with the rebuilt gateway; every other verb with `null`. */
  overview: Overview | null;
}

export interface SessionFailed extends SessionTrouble {
  ok: false;
}

/** Every verb answers one of these two, and no verb answers `undefined`. */
export type SessionResult = SessionDone | SessionFailed;

/** Which of the four branches of §5.2 a `cancel()` ended on. */
export type CancelBranch = "cancelled" | "already_ended" | "gone" | "owned" | "unconfirmed";

/**
 * The outcome of "Cancel", which the screen always shows.
 *
 * `ok` is about the shutter, not about the round trip: `gone` is a success - the session
 * is not there any more - even though the command was refused.
 */
export interface CancelOutcome {
  ok: boolean;
  branch: CancelBranch;
  session: SessionSnapshot | null;
  error: WsError | null;
  recovery: SessionRecovery[];
  freedAt: IsoTime | null;
}

export interface SessionClientOptions {
  connection: HaConnection;
  entryId: string;
  /** Called with every snapshot this client learns of, however it learned of it. */
  onChange?: (session: SessionSnapshot | null) => void;
  /** Only the tests and the development harness pass these two. */
  clientId?: string;
  storage?: KeyValueStore | null;
}

/** The two states a session is over in. */
export const isOver = (session: SessionSnapshot | null): boolean =>
  session !== null && (session.state === "saved" || session.state === "ended");

const refusal = (error: WsError): string => error.translation_key ?? error.code;

/** The refusals that mean "there is no such session any more". */
const GONE = new Set(["unknown_session", "session_ended"]);

/** The refusals that are about the gateway rather than about the session. */
const UNREACHABLE = new Set(["unknown_entry", "entry_not_loaded"]);

const randomId = (): string => {
  try {
    const uuid = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto?.randomUUID?.();
    if (uuid && CLIENT_ID.test(uuid)) {
      return uuid;
    }
  } catch {
    // `crypto` is absent on an insecure origin and throws on some hosts; the fallback
    // below is not a security control - the id is a name, not a secret.
  }
  const noise = `${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
  return `c-${noise}`.replace(/[^A-Za-z0-9-]/g, "").slice(0, 64).padEnd(8, "0");
};

/** The default store, read once and in a `try`: Safari throws on the property itself. */
const defaultStorage = (): KeyValueStore | null => {
  try {
    return (globalThis as { sessionStorage?: KeyValueStore }).sessionStorage ?? null;
  } catch {
    return null;
  }
};

/**
 * This tab's name in the session: the one that was kept, or a new one.
 *
 * Every access is wrapped, because a browser in private mode answers the property and
 * then throws on the read - and a panel that could not calibrate in a private window
 * would be a panel broken by a fallback nobody wrote.
 */
export const readClientId = (storage: KeyValueStore | null): string => {
  try {
    const kept = storage?.getItem(CLIENT_ID_KEY);
    if (kept && CLIENT_ID.test(kept)) {
      return kept;
    }
  } catch {
    // Unreadable: a fresh id for the life of this element, which is the documented ripiego.
  }
  const made = randomId();
  try {
    storage?.setItem(CLIENT_ID_KEY, made);
  } catch {
    // Unwritable: the id still works, it just does not survive a reload of this tab.
  }
  return made;
};

export class SessionClient {
  readonly entryId: string;
  readonly clientId: string;

  private _connection: HaConnection;
  private _onChange: (session: SessionSnapshot | null) => void;
  private _session: SessionSnapshot | null = null;
  private _capabilities: SessionCapabilities | null = null;
  private _owner = false;
  /** True between an `attach`/`start` that worked and the end of the session. */
  private _attached = false;
  private _timer: ReturnType<typeof setInterval> | null = null;
  private _disposed = false;
  /** So that a listener that throws is reported once and not on every beat. */
  private _warned = false;

  constructor(options: SessionClientOptions) {
    this._connection = options.connection;
    this.entryId = options.entryId;
    this._onChange = options.onChange ?? (() => undefined);
    this.clientId =
      options.clientId ??
      readClientId(options.storage === undefined ? defaultStorage() : options.storage);
  }

  get session(): SessionSnapshot | null {
    return this._session;
  }

  get capabilities(): SessionCapabilities | null {
    return this._capabilities;
  }

  /** Whether this tab may act, as the last answer from the server said. */
  get owner(): boolean {
    return this._owner;
  }

  /** Whether the presence timer is running - read by the checks, not by a screen. */
  get beating(): boolean {
    return this._timer !== null;
  }

  // --- the verbs ------------------------------------------------------------------------
  //
  // Each of them answers `{ok: true, session, overview}` or `{ok: false, error, recovery,
  // freedAt}`. Nothing here throws, nothing answers `undefined`, and every refusal comes
  // out with at least one thing the screen can offer.

  /** Read the session. A read never moves anything (contract §11.1). */
  async get(): Promise<SessionResult> {
    try {
      const answer = await sessionGet(this._connection, this.entryId);
      this._capabilities = answer.capabilities ?? this._capabilities;
      this._adopt(answer.session);
      return this._done(answer.session);
    } catch (raw) {
      return this._failed(raw);
    }
  }

  /** Open a session on one shutter. `start` never moves anything either. */
  async start(intent: WizardIntent): Promise<SessionResult> {
    try {
      const answer = await sessionStart(this._connection, this.entryId, {
        cover_unique_id: intent.cover,
        client_id: this.clientId,
        path: intent.path,
        profile: intent.profile,
        scope: intent.scope,
      });
      this._attached = true;
      this._adopt(answer.session);
      this._startHeartbeat();
      return this._done(answer.session);
    } catch (raw) {
      return this._failed(raw);
    }
  }

  /**
   * Pick a session up. Without `claim` it is a read; with it, it takes the session from a
   * client that is still present - which the screen asks about first.
   */
  async attach(sessionId: string, claim = false): Promise<SessionResult> {
    try {
      const answer = await sessionAttach(this._connection, this.entryId, {
        session_id: sessionId,
        client_id: this.clientId,
        claim,
      });
      this._attached = true;
      this._adopt(answer.session);
      this._startHeartbeat();
      return this._done(answer.session);
    } catch (raw) {
      return this._failed(raw);
    }
  }

  /** One step of the conversation, guarded by the revision the screen last read. */
  async act(action: SessionAction | SessionSubmit, value?: string | number | null): Promise<SessionResult> {
    const session = this._session;
    if (!session) {
      return this._failed({ code: "not_found", message: "no session", translation_key: "unknown_session" });
    }
    try {
      const answer = await sessionAct(this._connection, this.entryId, {
        session_id: session.session_id,
        client_id: this.clientId,
        revision: session.revision,
        action,
        value,
      });
      this._adopt(answer.session);
      return this._done(answer.session);
    } catch (raw) {
      return this._failed(raw);
    }
  }

  /** The one verb that touches the shutter. */
  async stop(): Promise<SessionResult> {
    const session = this._session;
    if (!session) {
      return this._failed({ code: "not_found", message: "no session", translation_key: "unknown_session" });
    }
    try {
      const answer = await sessionStop(this._connection, this.entryId, {
        session_id: session.session_id,
        client_id: this.clientId,
      });
      this._adopt(answer.session);
      return this._done(answer.session);
    } catch (raw) {
      return this._failed(raw);
    }
  }

  /** Write the result, once, from the review. */
  async save(target: SessionSaveTarget): Promise<SessionResult> {
    const session = this._session;
    if (!session) {
      return this._failed({ code: "not_found", message: "no session", translation_key: "unknown_session" });
    }
    try {
      const answer = await sessionSave(this._connection, this.entryId, {
        session_id: session.session_id,
        client_id: this.clientId,
        revision: session.revision,
        target,
      });
      this._adopt(answer.session);
      // The contract types `overview` loosely so that `session-contract.ts` depends on
      // nothing; the client is where it becomes the answer the rest of the panel reads.
      return {
        ok: true,
        session: answer.session,
        overview: (answer.overview as unknown as Overview) ?? null,
      };
    } catch (raw) {
      return this._failed(raw);
    }
  }

  /**
   * Detach this client: nothing is written and a run under way finishes by itself.
   *
   * Sent as the page goes away, so it is best effort by nature - if it never leaves,
   * presence lapses in forty-five seconds and the session is simply available again.
   */
  async leave(): Promise<SessionResult> {
    const session = this._session;
    this._stopHeartbeat();
    this._attached = false;
    if (!session) {
      return this._done(null);
    }
    try {
      const answer = await sessionLeave(this._connection, this.entryId, {
        session_id: session.session_id,
        client_id: this.clientId,
      });
      this._adopt(answer.session);
      return this._done(answer.session);
    } catch (raw) {
      return this._failed(raw);
    }
  }

  /**
   * "Cancel", which always ends somewhere the screen can show (SPEC §5.2, lesson 2).
   *
   * The four branches:
   *
   * 1. it worked, or the session had already ended - the outcome is shown;
   * 2. another client owns it - the screen offers "Take control and cancel", which is
   *    `claimAndCancel()`, and "End it anyway", which is this with `force`;
   * 3. the session is not there any more - "already ended", with the reason if the last
   *    snapshot carried one;
   * 4. the gateway did not answer - "not confirmed", with "Try again" and "End anyway";
   *    and if `force` was what just failed, with the instant the shutter is freed at.
   *
   * `cancel` carries no revision and can never be refused for concurrency (contract
   * §11.1), which is why branch 4 is about the network and nothing else.
   */
  async cancel({ force = false }: { force?: boolean } = {}): Promise<CancelOutcome> {
    const session = this._session;
    try {
      const answer = await sessionCancel(this._connection, this.entryId, {
        client_id: this.clientId,
        session_id: session?.session_id,
        force,
      });
      this._stopHeartbeat();
      this._attached = false;
      this._adopt(answer.session);
      return {
        ok: true,
        branch: answer.already_ended ? "already_ended" : "cancelled",
        session: answer.session,
        error: null,
        recovery: [],
        freedAt: null,
      };
    } catch (raw) {
      const error = asWsError(raw);
      const key = refusal(error);
      if (key === "session_owned") {
        return {
          ok: false,
          branch: "owned",
          session: this._session,
          error,
          recovery: ["claim", "force"],
          freedAt: this._session?.idle_expires_at ?? null,
        };
      }
      if (GONE.has(key)) {
        // Refused, and yet the thing the user asked for is true: there is no session on
        // this gateway any more. The outcome carries whatever the last snapshot said.
        this._stopHeartbeat();
        this._attached = false;
        return {
          ok: true,
          branch: "gone",
          session: this._session,
          error,
          recovery: [],
          freedAt: null,
        };
      }
      return {
        ok: false,
        branch: "unconfirmed",
        session: this._session,
        error,
        // "End it anyway" is the offer until it is the thing that just failed; then the
        // only honest sentence left is the one about the lease, and the screen says it.
        recovery: force ? ["wait"] : ["retry", "force"],
        freedAt: this._session?.idle_expires_at ?? null,
      };
    }
  }

  /** Branch 2: take the session from the client that owns it, then cancel it. */
  async claimAndCancel(): Promise<CancelOutcome> {
    const session = this._session;
    if (!session) {
      return this.cancel({ force: true });
    }
    const taken = await this.attach(session.session_id, true);
    if (!taken.ok) {
      return {
        ok: false,
        branch: "unconfirmed",
        session: this._session,
        error: taken.error,
        recovery: ["force"],
        freedAt: this._session?.idle_expires_at ?? null,
      };
    }
    return this.cancel();
  }

  // --- presence -------------------------------------------------------------------------

  /**
   * A snapshot that arrived by itself, over the subscription.
   *
   * It is folded in exactly like an answer to a verb: the same adoption, the same
   * notification, and the heartbeat stopped when the session is over. Nothing here sends
   * anything, so an event can never restart a movement.
   */
  apply(session: SessionSnapshot | null): void {
    this._adopt(session);
  }

  /**
   * The tab came back to the front: say "still here" at once, and read the session.
   *
   * Both are needed. The heartbeat may have been throttled to a crawl by a background
   * tab, and the snapshot the screen is showing may be several transitions old.
   */
  async resume(): Promise<SessionResult> {
    if (this._attached) {
      void this._beat();
    }
    return this.get();
  }

  /** Everything this client is holding, given back. */
  dispose(): void {
    this._disposed = true;
    this._stopHeartbeat();
    this._attached = false;
    this._onChange = () => undefined;
  }

  private _startHeartbeat(): void {
    if (this._timer !== null || this._disposed) {
      return;
    }
    if (!this._session || isOver(this._session)) {
      return;
    }
    // Its own timer, created here and nowhere else. No paint, no reactive update and no
    // element lifecycle callback is on this path, which is the whole of lesson 1.
    this._timer = setInterval(() => {
      void this._beat();
    }, HEARTBEAT_MS);
  }

  private _stopHeartbeat(): void {
    if (this._timer !== null) {
      clearInterval(this._timer);
      this._timer = null;
    }
  }

  private async _beat(): Promise<void> {
    const session = this._session;
    if (!session || isOver(session)) {
      this._stopHeartbeat();
      return;
    }
    try {
      const answer = await sessionHeartbeat(this._connection, this.entryId, {
        session_id: session.session_id,
        client_id: this.clientId,
      });
      const owner = answer.owner === true;
      if (owner !== this._owner) {
        // Ownership was taken by another tab. The screen goes read-only and offers to take
        // it back; nothing stops and nothing moves.
        this._owner = owner;
        this._notify();
      }
    } catch (raw) {
      const key = refusal(asWsError(raw));
      if (GONE.has(key)) {
        // The session really is gone: there is nothing left to be present for.
        this._stopHeartbeat();
        this._attached = false;
        return;
      }
      // Anything else - the socket down, the gateway reloading - is a reason to beat
      // again in fifteen seconds, not a reason to stop. A session is not lost because a
      // lift went past a router.
    }
  }

  // --- the plumbing ---------------------------------------------------------------------

  private _adopt(session: SessionSnapshot | null): void {
    this._session = session;
    this._owner = session?.owner?.client_id === this.clientId;
    if (isOver(session) || session === null) {
      this._stopHeartbeat();
    } else if (this._attached) {
      this._startHeartbeat();
    }
    this._notify();
  }

  /**
   * Tell whoever is listening, and survive them.
   *
   * A listener here is a repaint, and a repaint is the thing lesson 1 is about: an
   * exception thrown by a drawing must not reach the timer that keeps the session alive.
   * It is reported once - a console full of the same stack trace every fifteen seconds
   * buries the first one.
   */
  private _notify(): void {
    try {
      this._onChange(this._session);
    } catch (error) {
      if (!this._warned) {
        this._warned = true;
        console.error("MyHOME panel: the calibration screen threw while it was being told", error);
      }
    }
  }

  private _done(session: SessionSnapshot | null): SessionDone {
    return { ok: true, session, overview: null };
  }

  private _failed(raw: unknown): SessionFailed {
    const error = asWsError(raw);
    const key = refusal(error);
    let recovery: SessionRecovery[] = ["retry"];
    if (key === "session_owned") {
      recovery = ["claim"];
    } else if (key === "revision_conflict" || GONE.has(key) || key === "already_calibrating") {
      // Somebody - or something the session did by itself - moved on. Reading again is
      // the whole of the recovery: the screen that comes back is the true one.
      recovery = ["reload"];
    } else if (UNREACHABLE.has(key)) {
      recovery = ["retry"];
    }
    return { ok: false, error, recovery, freedAt: this._session?.idle_expires_at ?? null };
  }
}
