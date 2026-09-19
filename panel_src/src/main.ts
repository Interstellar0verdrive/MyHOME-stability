// <myhome-calibration-panel> - the element Home Assistant instantiates at
// /myhome-calibration.
//
// This file is the shell: the toolbar, the states that outrank every screen (loading, a
// refusal, a measurement in progress), the router, the store and the one place that talks
// to the backend. The screens themselves are in `views/`, and the wizard's eight step
// templates are in `templates/` behind `<myhome-screen>`.
//
// **The element contract.** Home Assistant sets four *properties* on the element: `hass`,
// `narrow`, `route` and `panel`. That is frontend-repo behaviour
// (`src/panels/custom/ha-panel-custom.ts`); the Python side only proves what is *sent*
// (`frontend.Panel.to_response`), so none of it is verified from this repository. The three
// that can only be objects are declared `attribute: false`; `narrow` keeps its attribute as
// well, because a boolean is the one of the four a host could plausibly set either way and
// accepting both costs nothing.
//
// Because it is unverified, nothing here may *depend* on it: the bootstrap waits for `hass`
// rather than assuming it is already there, and the router prefers its own hash to the
// `route` property (see `engine/router.ts`).
//
// **`hass` changes identity on every state update in the whole installation** - a light
// switched on at the other end of the house replaces it. `shouldUpdate` therefore asks what
// actually changed before repainting. Note for later lots: the moment anything here renders
// a value read out of `hass.states`, that question needs a second half, or those updates are
// silently dropped. Nothing does today - the model arrives over the WebSocket, and the
// `Calibrating` flag with it.

import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";

import { I18n } from "./engine/i18n";
import { defined, toggleSidebar } from "./engine/ha";
import {
  assignItems,
  currentAssignment,
  needsTravel,
  parseTravel,
  travelProblem,
  withPending,
} from "./engine/assign";
import { DECIMALS } from "./engine/assign";
import { isEmpty, valueProblem } from "./engine/fields";
import { openOptionsFlow } from "./engine/flow";
import { backPath, isDrawerRoute, nextBack } from "./engine/drawer";
import { Router, type Route } from "./engine/router";
import { SessionClient, isOver, type WizardIntent } from "./engine/session";
import { type SessionSnapshot } from "./engine/session-contract";
import { NOTHING_PENDING, NO_DETAIL, NO_PROFILE_CARD, Store } from "./engine/store";
import { buttonStyles, cardStyles, srOnly, themeStyles } from "./engine/theme";
import { FocusTrap, deepActiveElement, focusWhenPainted, liveRegion } from "./engine/a11y";
import {
  asWsError,
  assign as sendAssign,
  coverDetail as fetchCoverDetail,
  coverEdit as sendCoverEdit,
  coverForget as sendCoverForget,
  isUnknownCommand,
  profileDelete as sendProfileDelete,
  profileEdit as sendProfileEdit,
  profileRename as sendProfileRename,
  overview as fetchOverview,
  preview as fetchPreview,
  reorder as sendReorder,
  setTravel as sendSetTravel,
  subscribe,
  undo as sendUndo,
  type CalibrationEvent,
  type CoverRow,
  type Overview,
  type ProfileRow,
} from "./engine/ws";
import { type HaPanelInfo, type HaRoute, type HomeAssistant } from "./types/ha";
import { drawer, drawerStyles } from "./components/drawer";
import { measuringBanner, measuringBannerStyles } from "./components/measuring-banner";
import { cardSkeleton, overviewSkeleton, skeletonStyles } from "./components/skeleton";
import { applyingStrip, snackStrip, stripStyles } from "./components/strips";
import { FLOW_URL, MyHomeOverview, type AssignActions } from "./views/overview";
import { DETAIL_KEYS, MyHomeCoverDetail, type DetailActions } from "./views/cover-detail";
import { MyHomeProfileCard, PROFILE_KEYS, type ProfileActions } from "./views/profile-card";
import { MyHomeWizard, type WizardActions } from "./views/wizard";
import { MyHomeScreen, type ScreenModel } from "./engine/screen";

/** How often the panel asks again when the backend has no subscription to offer. */
const POLL_MS = 30_000;

/**
 * How long the feedback strip stays, with "Annulla" on it. The design fixes seven seconds.
 *
 * The *server's* undo slot is five minutes (contract §9.9) and is withdrawn by the next
 * write of the same gateway, so the strip is the shorter of the two on purpose: an offer
 * that is still on the screen after the thing behind it has expired is worse than no offer.
 */
const SNACK_MS = 7_000;

/**
 * How long the review panel waits after a keystroke before asking the server what the
 * batch would come to. Long enough that typing "145" is one question and not three.
 */
const PREVIEW_DEBOUNCE_MS = 400;

/**
 * The shortest gap between two reads caused by a *server push*.
 *
 * A push arrives after every write of every browser looking at this gateway, and two
 * payloads have to be asked again when one does: the batch preview, while the review panel
 * is open, and the open card, which a push says nothing about. On a house where something
 * else writes often that was one round trip each per write, unthrottled. They are asked at
 * most this often now, and always at least once - the follow-up is delayed, never dropped.
 */
const PUSH_FOLLOW_MS = 2_000;

export class MyHomeCalibrationPanel extends LitElement {
  static override properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    route: { attribute: false },
    panel: { attribute: false },
  };

  declare hass: HomeAssistant;
  declare narrow: boolean;
  declare route: HaRoute;
  declare panel: HaPanelInfo | null;

  private _i18n = new I18n();
  private _router = new Router();
  private _store = new Store(this._router.current);
  private _unsubscribeStore: (() => void) | null = null;
  private _unsubscribeWs: (() => Promise<void>) | null = null;
  private _poll: ReturnType<typeof setInterval> | null = null;
  private _language = "";
  private _started = false;
  private _snackTimer: ReturnType<typeof setTimeout> | null = null;
  private _previewTimer: ReturnType<typeof setTimeout> | null = null;
  private _travelTimer: ReturnType<typeof setTimeout> | null = null;
  private _impactTimer: ReturnType<typeof setTimeout> | null = null;
  private _followTimer: ReturnType<typeof setTimeout> | null = null;
  private _followedAt = 0;
  /**
   * The gateway's calibration session, as this tab holds it (0.6.0 wizard, lot F1).
   *
   * Made when the first answer names a gateway and remade when the gateway changes. It
   * owns its own presence timer: nothing in this file starts it, stops it or delays it,
   * and that is deliberate - see the head of `engine/session.ts`.
   */
  private _sessionClient: SessionClient | null = null;
  /** What `hass.states` last said about the shutter being calibrated: see `shouldUpdate`. */
  private _coverState = "";
  /** The queue `_listen` runs on, so that two callers can never open two subscriptions. */
  /** The one screen remembered behind the drawer, and the control it draws. */
  private _drawerBack: Route | null = null;
  private _trap = new FocusTrap();
  private _returnTo: HTMLElement | null = null;

  private _listening: Promise<void> = Promise.resolve();
  /** How many attempts are on that queue, waiting or in the air. */
  private _subscribing = 0;
  /** Every preview answer but the last is thrown away: they arrive out of order. */
  private _previewSeq = 0;

  constructor() {
    super();
    this.narrow = false;
    this.panel = null;
  }

  static override styles = [
    themeStyles,
    cardStyles,
    buttonStyles,
    srOnly,
    measuringBannerStyles,
    skeletonStyles,
    stripStyles,
    drawerStyles,
    css`
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 0 8px;
        background: var(--myhome-header);
        color: var(--myhome-header-text);
        font-size: 20px;
        font-weight: 400;
        /* The panel handles its own safe area (handle_safe_area: true). */
        padding-top: env(safe-area-inset-top, 0px);
        height: calc(56px + env(safe-area-inset-top, 0px));
      }

      /* The page's one <h1>, styled as the toolbar's title and not as a heading. */
      .toolbar .title {
        flex: 1;
        min-width: 0;
        margin: 0;
        font-size: inherit;
        font-weight: inherit;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      /* The gateway select, drawn only in a house with two of them. */
      .toolbar select.gateway {
        font: inherit;
        font-size: 13px;
        max-width: 40%;
        min-height: 44px;
        border-radius: 8px;
        border: 1px solid currentColor;
        background: transparent;
        color: inherit;
        padding: 0 6px;
      }

      /* A native option list is painted by the platform, not by the header. */
      .toolbar select.gateway option {
        color: var(--myhome-text);
        background: var(--myhome-card);
      }

      /* 48x48, like every target in the handoff. */
      .toolbar button {
        width: 48px;
        height: 48px;
        flex: 0 0 48px;
        border: 0;
        border-radius: 24px;
        background: transparent;
        color: inherit;
        font-size: 20px;
        line-height: 1;
        cursor: pointer;
      }

      .content {
        padding: 16px;
        max-width: 1200px;
        margin: 0 auto;
        padding-bottom: calc(16px + env(safe-area-inset-bottom, 0px));
      }

      .card.problem {
        background: var(--myhome-error-pastel);
        color: var(--myhome-text);
        padding: 16px;
      }

      /* Waiting is not a refusal, and must not borrow the error colour to say so. */
      .card.waiting {
        color: var(--myhome-text-soft);
        padding: 16px;
      }

      .soft {
        color: var(--myhome-text-soft);
        font-size: 13px;
        margin-top: 8px;
      }

      .connection {
        margin: 24px 0 0;
        font-size: 12.5px;
        color: var(--myhome-text-soft);
      }

      /*
       * Home Assistant restarting, seen from here. The frontend draws its own bar for it,
       * eventually and at the top of the window; this is the panel saying the same thing
       * about the thing the user is looking at, in the place the measuring banner uses,
       * so that "live" at the foot of the page is never a claim nobody is checking.
       */
      .offline {
        display: block;
        padding: 12px 16px;
        background: var(--myhome-warning-pastel);
        color: var(--myhome-text);
        font-size: 14px;
      }

      a {
        color: var(--myhome-primary-ink);
      }
    `,
  ];

  override connectedCallback(): void {
    super.connectedCallback();
    this._unsubscribeStore = this._store.subscribe(() => this.requestUpdate());
    this._router.start((route: Route) => this._onRoute(route));
    window.addEventListener("location-changed", this._onReturn);
    document.addEventListener("visibilitychange", this._onReturn);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this._unsubscribeStore?.();
    this._unsubscribeStore = null;
    this._router.stop();
    this._trap.release();
    window.removeEventListener("location-changed", this._onReturn);
    document.removeEventListener("visibilitychange", this._onReturn);
    this._unwatchSocket();
    this._stopPolling();
    if (this._snackTimer) {
      clearTimeout(this._snackTimer);
      this._snackTimer = null;
    }
    if (this._previewTimer) {
      clearTimeout(this._previewTimer);
      this._previewTimer = null;
    }
    if (this._travelTimer) {
      clearTimeout(this._travelTimer);
      this._travelTimer = null;
    }
    if (this._impactTimer) {
      clearTimeout(this._impactTimer);
      this._impactTimer = null;
    }
    if (this._followTimer) {
      clearTimeout(this._followTimer);
      this._followTimer = null;
    }
    const unsubscribe = this._unsubscribeWs;
    this._unsubscribeWs = null;
    // The socket outlives the element, so a subscription that is not given back keeps a
    // gateway pushing overviews at nobody for the rest of the session.
    void unsubscribe?.().catch(() => undefined);
    // The calibration session outlives the element too, and on purpose: it is the server's
    // and closing a page does not end it. What is given back here is this tab's claim on
    // it, so the next device to act picks it up without waiting out the forty-five seconds
    // of presence. Best effort by nature - if the message never leaves, presence lapses.
    const session = this._sessionClient;
    this._sessionClient = null;
    if (session) {
      void session.leave().finally(() => session.dispose());
    }
  }

  protected override shouldUpdate(changed: PropertyValues): boolean {
    if (changed.size > 1 || !changed.has("hass")) {
      return true;
    }
    if (this._languageOf(this.hass) !== this._language) {
      return true;
    }
    // The second half the note at the top of this file asked for. `hass` is replaced on
    // every state change in the whole installation, so the question is not "did anything
    // change" but "did the one thing this panel draws out of `hass.states` change": the
    // position of the shutter being calibrated, which the wizard shows beside the motor's
    // own elapsed time. Everything else still arrives over the WebSocket.
    const cover = this._coverStateNow();
    if (cover !== this._coverState) {
      this._coverState = cover;
      return true;
    }
    return false;
  }

  /**
   * What the shutter under calibration is saying about itself, as one string.
   *
   * Its state and `current_position` and nothing else: the estimate the shutter keeps for
   * itself, at about 1 Hz, which is what the wizard draws as "Posizione stimata". With no
   * session, or a session whose shutter has no entity, there is nothing to follow and the
   * empty string never changes.
   */
  private _coverStateNow(): string {
    const entity = this._store.state.session?.cover.entity_id;
    if (!entity) {
      return "";
    }
    const state = this.hass?.states?.[entity];
    if (!state) {
      return "";
    }
    return `${state.state}|${String(state.attributes?.current_position ?? "")}`;
  }

  protected override firstUpdated(): void {
    void this._bootstrap();
  }

  protected override updated(changed: PropertyValues): void {
    this._manageDrawerFocus();
    if (changed.has("route")) {
      this._router.setHostPath(this.route?.path);
      this._onRoute(this._router.current);
    }
    if (!changed.has("hass") || !this.hass) {
      return;
    }
    // The first `hass` the element ever sees, if it did not have one when it first
    // rendered. `_bootstrap` is what makes that harmless rather than permanent.
    if (!this._started) {
      void this._bootstrap();
      return;
    }
    if (this._languageOf(this.hass) !== this._language) {
      void this._loadTexts();
    }
  }

  /** Whether a drawer was on the screen the last time focus was looked at. */
  private _drawerWasOpen = false;
  private _dialogWasOpen = false;

  /**
   * The keyboard, while the drawer is open - the review panel's arrangement, moved up one
   * element because this drawer is the shell's and not the list's.
   *
   * Three things happen, and each of them is one of the handoff's §5 rules:
   *
   * * **the trap holds the drawer**, so Tab cannot walk out of it into the list behind,
   *   which is still full of rows and handles. It holds without taking focus: the card
   *   inside takes its own heading on the paint that first draws it, and two `focus()`
   *   calls in one frame is a race;
   * * **focus comes back** to whatever opened it - the row's own button, the group's
   *   heading - and it is read *deep*, because the control that was clicked lives in the
   *   overview's shadow root and `activeElement` would answer with the host;
   * * **"Quale profilo?" borrows the keyboard** while it is over the drawer, and gives it
   *   back to the drawer's first stop when it closes, rather than to the document.
   */
  private _manageDrawerFocus(): void {
    const state = this._store.state;
    const open = isDrawerRoute(state.route) && state.status !== "error";
    const dialog = state.dialog !== null;
    const root = (): HTMLElement | null =>
      this.renderRoot.querySelector<HTMLElement>("[data-drawer]");
    if (open && !this._drawerWasOpen) {
      this._returnTo = deepActiveElement(this.renderRoot as unknown as DocumentOrShadowRoot) as
        | HTMLElement
        | null;
      requestAnimationFrame(() => {
        const element = root();
        if (element) {
          this._trap.hold(element, false);
        }
      });
    } else if (!open && this._drawerWasOpen) {
      this._trap.release();
      const back = this._returnTo;
      this._returnTo = null;
      focusWhenPainted(() => (back?.isConnected ? back : null));
    } else if (open && this._dialogWasOpen && !dialog) {
      // The dialog has just closed over an open drawer: the overview's own focus return
      // has nothing to give it back to, because what opened the dialog was not in the
      // overview. The drawer takes the keyboard again.
      requestAnimationFrame(() => {
        const element = root();
        if (element) {
          this._trap.hold(element);
        }
      });
    }
    this._drawerWasOpen = open;
    this._dialogWasOpen = dialog;
  }

  private _languageOf(hass: HomeAssistant | undefined): string {
    return hass?.locale?.language || hass?.language || "en";
  }

  /**
   * Read the sentences and the gateway, once, and survive either failing.
   *
   * A panel that throws on load shows a blank page and no server-side error, which is the
   * worst failure mode this feature has (plan, R3). So the bootstrap catches its own errors
   * and renders them, naming the version it is and pointing at "Configura" - which remains
   * a complete path to everything the panel does.
   */
  private async _bootstrap(): Promise<void> {
    if (this._started || !this.hass) {
      return;
    }
    this._started = true;
    this._watchSocket();
    await this._loadTexts();
    await this._refresh();
    // A deep link is answered only now: `cover_detail` needs a gateway, and until the
    // overview has named one there is nothing to ask it about.
    await this._loadDetail();
    await this._listen();
    // …and the same for the session: every one of its commands carries an `entry_id`.
    // A deep link straight to `#/calibrate` therefore reads the session here, and reads
    // it - nothing about arriving at that address opens one.
    this._ensureSession();
    if (this._store.state.route.view === "calibrate") {
      await this._readSession();
    }
  }

  /**
   * Home Assistant restarting, and coming back.
   *
   * The socket reconnects on its own and replays its subscriptions, so nothing here is
   * needed to keep the model arriving. What it is for is honesty and freshness: the foot
   * of the page said "live" throughout a restart, and a panel that had fallen back to
   * polling never tried the subscription again. On `ready` the gateway is read once - the
   * replayed subscription pushes an overview too, and one extra read is cheaper than a
   * screen that is right only if a private replay behaviour is.
   */
  private _watchSocket(): void {
    const connection = this.hass?.connection;
    connection?.addEventListener?.("disconnected", this._onSocketDown);
    connection?.addEventListener?.("ready", this._onSocketReady);
  }

  private _unwatchSocket(): void {
    const connection = this.hass?.connection;
    connection?.removeEventListener?.("disconnected", this._onSocketDown);
    connection?.removeEventListener?.("ready", this._onSocketReady);
  }

  private _onSocketDown = (): void => {
    if (this._store.state.connection === "offline") {
      return;
    }
    this._store.set({ connection: "offline" });
    this._store.announce(this._i18n.t("panel.error.no_connection"));
  };

  private _onSocketReady = (): void => void this._afterReconnect();

  private async _afterReconnect(): Promise<void> {
    if (!this._started) {
      return;
    }
    this._store.set({ connection: this._unsubscribeWs ? "live" : "polling" });
    await this._refresh();
    // `_listen` is queued and so is safe to call twice; this only keeps a socket that
    // flaps from buying a round trip for every flap.
    if (!this._unsubscribeWs && !this._subscribing) {
      await this._listen();
    }
    this._store.announce(this._i18n.t("panel.common.reconnected"));
  }

  private async _loadTexts(): Promise<void> {
    const language = this._languageOf(this.hass);
    try {
      await this._i18n.load(this.hass.connection, language);
    } catch {
      // The texts are a convenience; a panel with no sentences still shows its shutters,
      // and `t()` falls back to the English stand-in and then to the key itself.
    }
    this._language = language;
    this.requestUpdate();
  }

  private async _refresh(): Promise<void> {
    try {
      const answer = await fetchOverview(this.hass.connection, this._store.state.entryId ?? undefined);
      this._store.setOverview(answer);
    } catch (error) {
      this._store.setError(asWsError(error));
    }
  }

  /**
   * Live updates when the backend has them, and asking again when it has not.
   *
   * `myhome/calibration/subscribe` arrives with the write half of the contract, which is a
   * branch behind the one this panel is built on. Rather than assume it - a panel showing a
   * stale model with no way of knowing it is stale - the subscription is attempted and
   * `unknown_command` is caught: an installation without it falls back to asking every
   * thirty seconds, and says so at the foot of the page.
   */
  private _listen(): Promise<void> {
    // **One at a time, whoever asks.** Giving the old subscription back before opening a
    // new one is not enough on its own: `subscribe` is a round trip, and two callers that
    // reach it before either has stored its answer both get a live subscription, of which
    // only the last is ever unsubscribed. That is not a hypothetical - "Try again" pressed
    // twice, and a socket that drops and comes back twice while the panel is polling, both
    // do it - and the leak is permanent: a subscription nobody holds the handle of goes on
    // pushing a whole overview at every write for the life of the tab. So the attempts are
    // queued, and each one still gives back whatever the one before it left.
    this._subscribing += 1;
    const next = this._listening
      .then(() => this._subscribeOnce())
      .finally(() => {
        this._subscribing -= 1;
      });
    this._listening = next.catch(() => undefined);
    return next;
  }

  private async _subscribeOnce(): Promise<void> {
    const previous = this._unsubscribeWs;
    this._unsubscribeWs = null;
    await previous?.().catch(() => undefined);
    try {
      const unsubscribe = await subscribe(
        this.hass.connection,
        this._store.state.entryId,
        (event: CalibrationEvent) => this._onEvent(event),
      );
      if (!this.isConnected) {
        // The panel was navigated away from while this was in the air, and
        // `disconnectedCallback` has already given back the nothing there was to give.
        void unsubscribe().catch(() => undefined);
        return;
      }
      this._unsubscribeWs = unsubscribe;
      this._store.set({ connection: "live" });
      this._stopPolling();
    } catch (error) {
      if (!isUnknownCommand(error)) {
        // Any other refusal is worth one line in the console: the panel still works, and a
        // maintainer reading the console deserves to know which half failed.
        console.warn("MyHOME panel: live updates are not available", asWsError(error));
      }
      this._store.set({ connection: "polling" });
      this._startPolling();
    }
  }

  private _onEvent(event: CalibrationEvent): void {
    if (event.type === "overview") {
      // The model is replaced whole and the pending changes are kept beside it: a write
      // another browser tab made is not a reason to throw away six assignments somebody
      // is halfway through composing here. What the new model *can* change is what those
      // assignments would come to, so the preview is asked again.
      this._store.setOverview(event.overview);
      // The preview and the open card are second payloads a push says nothing about, so
      // both are asked again - through one throttle, because a gateway somebody else is
      // writing to can push faster than a round trip takes.
      this._followPush();
      return;
    }
    if (event.type === "session") {
      // The third event of the subscription (contract §11.4): the whole snapshot at every
      // transition of this gateway's session. It is folded into the client, which adopts
      // it exactly as it adopts the answer to a verb - and which sends nothing back, so an
      // event can never restart a movement.
      const client = this._ensureSession();
      if (client) {
        client.apply(event.session);
      } else {
        this._store.set({ session: event.session });
      }
      return;
    }
    if (event.type === "measuring") {
      // The measuring flag is the one thing that changes what the screens *allow*, so it
      // arrives on its own and is folded into the model the views already read.
      const current = this._store.state.overview;
      if (!current) {
        return;
      }
      this._store.set({
        overview: {
          ...current,
          measuring: event.cover_unique_id
            ? { cover_unique_id: event.cover_unique_id, name: event.name ?? "" }
            : null,
        },
      });
      if (event.cover_unique_id) {
        // The lock is announced *before* anything is attempted, which is the rule. A
        // gesture already in the air is given back: a drop that landed the moment a
        // measurement started would be a change the user could not then confirm.
        this._store.set({ armed: null, drag: null });
        this._store.announce(
          this._i18n.t("panel.banner.measuring.body", { cover: event.name ?? "" }),
        );
      }
    }
  }

  /**
   * The two reads a push implies, at most one burst every `PUSH_FOLLOW_MS`.
   *
   * Delayed and never dropped: while a follow-up is already waiting, a second push is
   * answered by the one that is coming, and it reads the state as it will be then rather
   * than as it is now.
   */
  private _followPush(): void {
    if (this._followTimer) {
      return;
    }
    const wait = Math.max(0, PUSH_FOLLOW_MS - (Date.now() - this._followedAt));
    this._followTimer = setTimeout(() => {
      this._followTimer = null;
      this._followedAt = Date.now();
      if (this._store.state.review) {
        this._schedulePreview();
      }
      if (this._store.state.detail.for) {
        void this._loadDetail();
      }
    }, wait);
  }

  private _startPolling(): void {
    if (this._poll) {
      return;
    }
    this._poll = setInterval(() => {
      // A hidden tab asks nothing: the refresh on `visibilitychange` brings it up to date
      // the instant somebody looks at it again.
      if (!document.hidden) {
        void this._refresh();
      }
    }, POLL_MS);
  }

  private _stopPolling(): void {
    if (this._poll) {
      clearInterval(this._poll);
      this._poll = null;
    }
  }

  /**
   * Coming back from somewhere else - the options flow in another tab of the same window,
   * or simply a tab that was in the background. A measurement made in the dialog then shows
   * up here without a manual reload.
   */
  private _onReturn = (): void => {
    if (!this._started || document.hidden) {
      return;
    }
    void this._refresh();
    // The tab has come back to the front. A background tab's timers are throttled to a
    // crawl by every browser, so the session is told "still here" at once and read again -
    // both of which are still reads: nothing here can restart a movement.
    void this._sessionClient?.resume();
  };

  /**
   * A new address, and whatever the screen behind it has to read.
   *
   * The two routed cards of lot 8 are a second server model each - `cover_detail` for the
   * shutter, and the profile's own row out of the overview - so arriving at one is a read
   * and leaving it throws the read away rather than leaving a stale card to be shown again
   * on the way back. Nothing here touches the pending changes: a user who opens a card in
   * the middle of composing a batch comes back to the batch.
   */
  private _onRoute(route: Route): void {
    const before = this._store.state.route;
    // One level, worked out from the two routes and nothing else: see `engine/drawer.ts`.
    this._drawerBack = nextBack(this._drawerBack, this._store.state.route, route);
    this._store.set({ route });
    if (route.view === "cover") {
      const id = route.params.id;
      if (this._store.state.detail.for !== id) {
        this._store.set({ detail: { ...NO_DETAIL, for: id, loading: true } });
        void this._loadDetail();
      }
    } else if (this._store.state.detail.for !== null) {
      this._store.set({ detail: NO_DETAIL });
    }
    if (route.view === "profile") {
      const name = route.params.name;
      if (this._store.state.profile.for !== name) {
        this._store.set({ profile: { ...NO_PROFILE_CARD, for: name } });
      }
    } else if (this._store.state.profile.for !== null) {
      this._store.set({ profile: NO_PROFILE_CARD });
    }
    if (route.view === "calibrate") {
      // **Arriving reads; it never starts.** The intention that opens a session is put in
      // the store by `_calibrate`, before the navigation, and a reload of this address
      // finds no intention and no session of its own - which is the whole reason the
      // address carries nothing (SPEC §5.1).
      this._store.set({ sessionError: null });
      if (this._started) {
        void this._readSession();
      }
    } else if (before.view === "calibrate") {
      this._leaveSession();
    }
    if (!this._started) {
      return;
    }
    this._store.set({ writeError: null });
  }

  private get _version(): string {
    return this.panel?.config?.version ?? "";
  }

  private _navigate(path: string): void {
    this._router.navigate(path);
  }

  /**
   * The drawer's one way out: one screen back where there is one, the list otherwise.
   *
   * Every road leads here - the head's control, Escape inside the card, a click on the
   * dark half - so there is one answer to "what does going back mean" and the address bar
   * is always told, which is what keeps the browser's own back button in step.
   */
  private _closeDrawer = (): void => {
    if (this._store.state.applying) {
      return;
    }
    this._navigate(backPath(this._drawerBack));
  };

  private _renderMenuButton(): TemplateResult | typeof nothing {
    if (!this.narrow) {
      return nothing;
    }
    // Home Assistant's own hamburger when it is there - and it is, in every version of the
    // frontend this integration supports - and a button that fires the same event when the
    // name changes under us. The sidebar is the only way off a phone screen.
    if (defined("ha-menu-button")) {
      return html`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`;
    }
    return html`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu")}
      @click=${() => toggleSidebar(this)}
    >
      ☰
    </button>`;
  }

  /**
   * A screen that is routed but not built in this version, told as a `lettura` step - which
   * is what that template is for, and what proves the engine hosts one.
   */
  private _renderPlaceholder(title: string, body: string): TemplateResult {
    const model: ScreenModel = {
      id: "panel.common.not_yet",
      model: "lettura",
      title,
      body,
      secondary: [
        { label: this._i18n.t("panel.common.action.back"), action: "back", kind: "text" },
      ],
    };
    return html`<myhome-screen
      .model=${model}
      .i18n=${this._i18n}
      @myhome-screen-action=${(event: CustomEvent) => {
        if (event.detail?.action === "back") {
          this._navigate("/");
        }
      }}
    ></myhome-screen>`;
  }

  // --- the assignment ------------------------------------------------------------------
  //
  // Every write the panel makes is here, in one object, beside the socket. The view does
  // the gestures and knows nothing about the API; this knows the API and nothing about
  // pointers. A reviewer asking "what can this screen change" reads the interface in
  // `views/overview.ts` and then these twenty methods, and there is nowhere else to look.

  /** True while nothing may be written: a measurement, or a write already in the air. */
  private get _locked(): boolean {
    const state = this._store.state;
    return state.overview?.measuring != null || state.applying;
  }

  private _assignActions: AssignActions = {
    search: (value) => this._store.set({ search: value }),
    room: (value) => this._store.set({ room: value }),
    clearFilters: () => this._store.set({ search: "", room: "" }),
    openCover: (uniqueId) => this._navigate(`/cover/${encodeURIComponent(uniqueId)}`),
    openProfile: (name) => this._navigate(`/profile/${encodeURIComponent(name)}`),

    /**
     * A gesture ended on a destination.
     *
     * Sending a shutter back where it already is withdraws its change rather than
     * recording one, which is what keeps the count on the bar equal to the number of
     * things the batch would really write.
     */
    assign: (cover, to) => {
      if (this._locked) {
        return;
      }
      const { pending, withdrawn } = withPending(this._store.state.pending, cover, to);
      this._store.set({ pending, dialog: null, armed: null, writeError: null });
      // Chosen from "Quale profilo?" over an open drawer - the detail card's "Assegna a
      // un profilo…". The change is a fact about the list: the row that now carries a
      // dashed outline, the bar that counts it and the panel that would write it are all
      // behind the drawer, so the drawer steps out of the way rather than leaving the
      // user looking at a card that cannot show what they just did.
      if (isDrawerRoute(this._store.state.route)) {
        this._drawerBack = null;
        this._navigate("/");
      }
      this._store.announce(
        withdrawn
          ? this._i18n.t("panel.assign.announce.withdrawn", { cover: cover.name })
          : this._i18n.t("panel.assign.announce.pending", {
              cover: cover.name,
              target:
                to === null
                  ? this._i18n.t("panel.assign.target_none")
                  : this._i18n.t("panel.assign.target_profile", { profile: to }),
            }),
      );
      this._schedulePreview();
    },

    withdraw: (cover) => {
      this._store.set({
        pending: this._store.state.pending.filter((item) => item.cover !== cover.unique_id),
      });
      this._store.announce(
        this._i18n.t("panel.assign.announce.withdrawn", { cover: cover.name }),
      );
      this._schedulePreview();
    },

    discardAll: () => {
      this._store.set({ ...NOTHING_PENDING });
      this._store.announce(this._i18n.t("panel.assign.announce.discarded"));
    },

    /**
     * A drop that only moved a row inside its group, with nothing pending to carry it.
     *
     * The order is *remembered*, not confirmed: the design says so ("l'ordine è ricordato
     * tra le sessioni") and it is the one thing on this screen that changes no travel
     * model, so making the user confirm it would be a dialog about a list.
     */
    reorder: (order) => {
      if (this._locked || !this._store.state.entryId) {
        return;
      }
      this._store.set({ order });
      void this._write(
        () => sendReorder(this.hass.connection, this._store.state.entryId as string, order),
        (result) => {
          this._store.set({ order: null });
          this._store.setOverview(result.overview);
          this._snack(this._i18n.t("panel.toast.order_saved"), result.undo_token);
          this._store.announce(this._i18n.t("panel.assign.announce.reordered"));
        },
        // This one write is made without a review panel in front of it, so a refusal has
        // nowhere to be read. The order goes back to the server's - a list the gateway
        // refused is not a list this screen may go on drawing, and it would outlive every
        // later push - and the sentence takes the strip the result would have had.
        (sentence) => {
          this._store.set({ order: null, writeError: null });
          this._snack(sentence, null, false);
        },
      );
    },

    setOrder: (order) => this._store.set({ order }),

    drag: (cover) =>
      this._store.set({
        drag: cover ? { cover: cover.unique_id, name: cover.name, over: null, insert: null } : null,
      }),

    over: (target) => {
      const drag = this._store.state.drag;
      if (!drag) {
        return;
      }
      this._store.set({
        drag: { ...drag, over: target?.group ?? null, insert: target ? { ...target } : null },
      });
    },

    arm: (cover) => {
      this._store.set({ armed: cover ? cover.unique_id : null });
      if (cover) {
        this._store.announce(this._i18n.t("panel.assign.announce.armed"));
      }
    },

    dialog: (cover) => this._store.set({ dialog: cover ? cover.unique_id : null }),

    review: (open) => {
      this._store.set({ review: open, writeError: null, heightsForced: false });
      if (open) {
        void this._refreshPreview();
      }
    },

    height: (cover, value) => {
      this._store.set({ heights: { ...this._store.state.heights, [cover]: value } });
      this._schedulePreview();
    },

    toggleShowAll: () => this._store.set({ showAll: !this._store.state.showAll }),

    confirm: () => void this._confirm(),

    undo: () => void this._undo(),

    announce: (message) => this._store.announce(message),

    calibrate: (intent) => void this._calibrate(intent),
  };

  /**
   * The batch, in one write.
   *
   * The travels are checked here first so that the user is told which fields are missing
   * rather than being handed one refusal about the whole batch; the server checks them
   * again, and where the two disagree the server's sentence is the one that is shown.
   */
  private async _confirm(): Promise<void> {
    const state = this._store.state;
    const entryId = state.entryId;
    if (this._locked || !entryId || state.pending.length === 0) {
      return;
    }
    const missing = state.pending.filter((change) => {
      const cover = state.overview?.covers.find((row) => row.unique_id === change.cover);
      return (
        cover !== undefined &&
        needsTravel(cover, change) &&
        travelProblem(state.heights[change.cover]) !== null
      );
    });
    if (missing.length > 0) {
      this._store.set({ heightsForced: true });
      this._store.announce(this._i18n.t("panel.assign.announce.missing_travel"));
      return;
    }
    const items = assignItems(state.pending, state.heights, state.overview?.covers ?? []);
    const order = state.order ?? undefined;
    this._store.announce(this._i18n.t("panel.assign.announce.applying"));
    await this._write(
      () => sendAssign(this.hass.connection, entryId, items, order),
      (result) => {
        this._store.set({ ...NOTHING_PENDING });
        this._store.setOverview(result.overview);
        // `applied` and not the length of the batch: the server counts the rows that
        // really changed something (contract §9.1), and they are not always the same
        // number. Taking a shutter out of a profile its *file* gives it writes nothing -
        // the record had no profile to remove - and the row goes back where it was, so
        // "1 assignment applied" beside a list that did not move is the screen saying
        // something the gateway did not.
        this._snack(
          result.applied === 1
            ? this._i18n.t("panel.toast.assigned_one")
            : this._i18n.t("panel.toast.assigned", { count: result.applied }),
          result.undo_token,
        );
      },
    );
  }

  private async _undo(): Promise<void> {
    const state = this._store.state;
    const token = state.snack?.undoToken;
    if (!token || !state.entryId) {
      return;
    }
    const entryId = state.entryId;
    this._clearSnack();
    await this._write(
      () => sendUndo(this.hass.connection, entryId, token),
      (result) => {
        this._store.setOverview(result.overview);
        this._snack(this._i18n.t("panel.toast.undone"), null);
      },
    );
  }

  /**
   * One write, its "applying" state and its refusal.
   *
   * A refusal is kept **where the user was working** - `writeError`, shown at the top of
   * the review panel - and never promoted to the whole-page error card: the pending
   * changes are still there, still correct, and a screen that threw them away because the
   * gateway was busy for a second would be a screen nobody trusts with twelve of them.
   */
  private async _write<T>(
    send: () => Promise<T>,
    onDone: (result: T) => void,
    onRefused?: (sentence: string) => void,
  ): Promise<void> {
    this._store.set({ applying: true, writeError: null });
    try {
      const result = await send();
      this._store.set({ applying: false });
      onDone(result);
    } catch (error) {
      const refusal = asWsError(error);
      this._store.set({ applying: false, writeError: refusal });
      const sentence = this._i18n.refusal(
        refusal.translation_key,
        refusal.translation_placeholders ?? {},
      );
      this._store.announce(sentence);
      // `writeError` is where the review panel shows a refusal, and a write made from
      // anywhere else has to say so somewhere the user is actually looking.
      onRefused?.(sentence);
    }
  }

  private _snack(message: string, undoToken: string | null, announce = true): void {
    this._clearSnack();
    this._store.set({ snack: { message, undoToken } });
    if (announce) {
      this._store.announce(message);
    }
    this._snackTimer = setTimeout(() => {
      this._snackTimer = null;
      this._store.set({ snack: null });
    }, SNACK_MS);
  }

  private _clearSnack(): void {
    if (this._snackTimer) {
      clearTimeout(this._snackTimer);
      this._snackTimer = null;
    }
    this._store.set({ snack: null });
  }

  /** Ask again in a moment, so that typing a travel is one question and not five. */
  private _schedulePreview(): void {
    if (!this._store.state.review) {
      return;
    }
    if (this._previewTimer) {
      clearTimeout(this._previewTimer);
    }
    this._previewTimer = setTimeout(() => {
      this._previewTimer = null;
      void this._refreshPreview();
    }, PREVIEW_DEBOUNCE_MS);
  }

  /**
   * What the batch would come to, from the server (contract §11).
   *
   * The panel does not scale a profile: that is `derive_cover_from_profile`'s job and a
   * second copy of it here would drift from the one the shutter runs on. A preview that
   * fails leaves the last answer on the screen rather than blanking the table - the rows
   * are still the right rows, and the alternative to a slightly stale number is no number.
   */
  private async _refreshPreview(): Promise<void> {
    const state = this._store.state;
    if (!state.entryId || state.pending.length === 0) {
      this._store.set({ preview: null });
      return;
    }
    const seq = ++this._previewSeq;
    this._store.set({ previewing: true });
    try {
      const answer = await fetchPreview(
        this.hass.connection,
        state.entryId,
        assignItems(state.pending, state.heights, state.overview?.covers ?? []),
      );
      if (seq === this._previewSeq) {
        this._store.set({ preview: answer.items, previewing: false });
      }
    } catch (error) {
      if (seq === this._previewSeq) {
        this._store.set({ previewing: false });
      }
      if (!isUnknownCommand(error)) {
        console.warn("MyHOME panel: the preview could not be read", asWsError(error));
      }
    }
  }

  // --- the cover detail (lot 8) ---------------------------------------------------------
  //
  // Same arrangement as the assignment above: the view does the screen, this does the API.
  // Three writes - `cover_edit`, `set_travel`, `cover_forget` - each with the undo strip
  // the rest of the panel has, each refused visibly, and each followed by a fresh read of
  // the card, because a write answers with an `overview` and the card is a second payload.

  /** The shutter the card is about, out of the model the overview already holds. */
  private get _detailCover(): CoverRow | null {
    const state = this._store.state;
    const id = state.detail.for;
    return (
      state.overview?.covers.find((cover: CoverRow) => cover.unique_id === id) ?? null
    );
  }

  private async _loadDetail(): Promise<void> {
    const state = this._store.state;
    const id = state.detail.for;
    if (!this._started || !this.hass || !id || !state.entryId) {
      return;
    }
    try {
      const answer = await fetchCoverDetail(this.hass.connection, state.entryId, id);
      // The address may have moved on while the answer was in the air; a card drawn from
      // the previous shutter's numbers under the current shutter's name is the one thing
      // this screen must never do.
      if (this._store.state.detail.for !== id) {
        return;
      }
      this._store.set({
        detail: { ...this._store.state.detail, answer, loading: false, error: null },
      });
    } catch (error) {
      if (this._store.state.detail.for !== id) {
        return;
      }
      this._store.set({
        detail: {
          ...this._store.state.detail,
          answer: null,
          loading: false,
          error: asWsError(error),
        },
      });
    }
  }

  /** The five fields as the form wants them: an own value written out, or empty. */
  private _detailForm(): Record<string, string> {
    const answer = this._store.state.detail.answer;
    const form: Record<string, string> = {};
    for (const key of DETAIL_KEYS) {
      const row = answer?.keys.find((item) => item.key === key);
      form[key] = row && row.own ? this._i18n.number(row.value, DECIMALS[key] ?? 1) : "";
    }
    return form;
  }

  private _detailActions: DetailActions = {
    back: this._closeDrawer,
    retry: () => {
      this._store.set({ detail: { ...this._store.state.detail, loading: true, error: null } });
      void this._loadDetail();
    },
    openProfile: (name) => this._navigate(`/profile/${encodeURIComponent(name)}`),

    /**
     * "Assegna a un profilo…" is the overview's own gesture, so it is the overview's own
     * dialog: the card hands the shutter over rather than growing a second copy of
     * "Quale profilo?" with a second idea of what a pending change is.
     *
     * It used to navigate to the list first, because the card *was* the screen and the
     * dialog could not be drawn over something that was no longer there. The card is a
     * drawer now, so the dialog opens on top of it (z-index 60 over the drawer's 51) and
     * the shutter the user is reading about stays on the screen while they choose. What
     * the choice does is in `_assignActions.assign`: a pending change belongs to the
     * list, so that is where it hands them back.
     */
    assign: () => {
      this._store.set({ dialog: this._store.state.detail.for });
    },

    mode: (mode) => {
      const detail = this._store.state.detail;
      const cover = this._detailCover;
      const form =
        mode === "edit"
          ? this._detailForm()
          : mode === "travel"
            ? { height: cover?.height != null ? this._i18n.number(cover.height, 0) : "" }
            : {};
      this._store.set({
        detail: { ...detail, mode, form, errors: {}, preview: null, previewing: false },
        writeError: null,
      });
      if (mode === "travel") {
        void this._refreshTravelPreview();
      }
    },

    field: (key, value) => {
      const detail = this._store.state.detail;
      // A travel that cannot be used takes its table with it *now* rather than in four
      // hundred milliseconds: a before/after worked out from the previous number, sitting
      // under a field that says the current one is out of range, reads as the answer.
      //
      // Clearing the table is only half of that. A preview asked for the *previous*
      // number may still be in the air, and it would land on an empty table and fill it
      // back in - under the sentence saying the number is out of range. So the sequence
      // moves on here too: the answer to a question the screen has stopped asking is
      // dropped when it arrives, exactly as one overtaken by a newer question is.
      const unusable = key === "height" && valueProblem("height", value) !== null;
      if (unusable) {
        this._previewSeq += 1;
      }
      this._store.set({
        detail: {
          ...detail,
          form: { ...detail.form, [key]: value },
          ...(unusable ? { preview: null } : {}),
        },
      });
      if (key === "height") {
        this._scheduleTravelPreview();
      }
    },

    saveValues: () => void this._saveValues(),
    saveTravel: () => void this._saveTravel(),
    remove: () => void this._removeMeasure(),
    openFlow: (source) => this._openFlow(source),
    calibrate: (intent) => void this._calibrate(intent),
  };

  /**
   * The hand edit, as the patch `cover_edit` wants (contract §9.4).
   *
   * A field with a number sets it; a field left **empty** clears it, which is what sends
   * the key back to being inherited - the whole meaning of "vuoto = niente da dire". Every
   * one of the five is sent on every save, because the form shows all five and a key left
   * out would be a value the user watched themselves delete and that stayed.
   */
  private async _saveValues(): Promise<void> {
    const state = this._store.state;
    const id = state.detail.for;
    if (this._locked || !id || !state.entryId) {
      return;
    }
    const overrides: Record<string, number | null> = {};
    for (const key of DETAIL_KEYS) {
      const typed = state.detail.form[key];
      if (valueProblem(key, typed) !== null) {
        return;
      }
      overrides[key] = isEmpty(typed) ? null : parseTravel(typed ?? "");
    }
    const cleared = Object.values(overrides).every((value) => value === null);
    const name = this._detailCover?.name ?? "";
    const entryId = state.entryId;
    await this._write(
      () => sendCoverEdit(this.hass.connection, entryId, id, overrides),
      (result) => {
        this._store.set({ detail: { ...this._store.state.detail, mode: "view", form: {} } });
        this._store.setOverview(result.overview);
        void this._loadDetail();
        // Emptying every field *is* removing the measurement, and the prototype says so
        // in those words rather than "saved". Where the window lands is read off the row
        // the write itself answered with, not predicted here.
        this._snack(
          cleared
            ? this._i18n.t("panel.toast.measure_removed", {
                cover: name,
                destination: this._destinationOf(result.overview, id),
              })
            : this._i18n.t("panel.toast.values_saved", { cover: name }),
          result.undo_token,
        );
      },
    );
  }

  private async _saveTravel(): Promise<void> {
    const state = this._store.state;
    const id = state.detail.for;
    const typed = state.detail.form.height;
    if (this._locked || !id || !state.entryId || isEmpty(typed) || valueProblem("height", typed)) {
      return;
    }
    const height = parseTravel(typed ?? "");
    const name = this._detailCover?.name ?? "";
    const entryId = state.entryId;
    await this._write(
      () => sendSetTravel(this.hass.connection, entryId, id, height),
      (result) => {
        this._store.set({
          detail: { ...this._store.state.detail, mode: "view", form: {}, preview: null },
        });
        this._store.setOverview(result.overview);
        void this._loadDetail();
        this._snack(this._i18n.t("panel.toast.travel_saved", { cover: name }), result.undo_token);
      },
    );
  }

  /**
   * "Rimuovi la misura": the whole record, and the sentence that says what is left.
   *
   * The destination comes from the command's own answer (`falls_back_to` / `profile`),
   * which is the window resolved again with the record gone - the same resolution the
   * confirmation read out of `cover_detail`'s `forget` block a moment earlier. So the
   * warning and the result cannot disagree.
   */
  private async _removeMeasure(): Promise<void> {
    const state = this._store.state;
    const id = state.detail.for;
    if (this._locked || !id || !state.entryId) {
      return;
    }
    const name = this._detailCover?.name ?? "";
    const entryId = state.entryId;
    await this._write(
      () => sendCoverForget(this.hass.connection, entryId, id),
      (result) => {
        this._store.set({ detail: { ...this._store.state.detail, mode: "view" } });
        this._store.setOverview(result.overview);
        void this._loadDetail();
        this._snack(
          this._i18n.t("panel.toast.measure_removed", {
            cover: name,
            destination:
              result.falls_back_to === "profile"
                ? this._i18n.t("panel.detail.destination.profile", {
                    profile: result.profile ?? "",
                  })
                : result.falls_back_to === "file"
                  ? this._i18n.t("panel.detail.destination.file")
                  : this._i18n.t("panel.detail.destination.defaults"),
          }),
          result.undo_token,
        );
      },
    );
  }

  /** Where a shutter's numbers come from now, said in the words of a destination. */
  private _destinationOf(overview: Overview, uniqueId: string): string {
    const row = overview.covers.find((cover: CoverRow) => cover.unique_id === uniqueId);
    if (row?.origin === "inherited" || row?.origin === "adjusted") {
      return this._i18n.t("panel.detail.destination.profile", { profile: row.profile ?? "" });
    }
    return row?.origin === "from_the_file"
      ? this._i18n.t("panel.detail.destination.file")
      : this._i18n.t("panel.detail.destination.defaults");
  }

  private _scheduleTravelPreview(): void {
    if (this._travelTimer) {
      clearTimeout(this._travelTimer);
    }
    this._travelTimer = setTimeout(() => {
      this._travelTimer = null;
      void this._refreshTravelPreview();
    }, PREVIEW_DEBOUNCE_MS);
  }

  /**
   * What this window would run on at the typed travel.
   *
   * The one number on the detail screen the panel may not work out: a travel is what a
   * profile is scaled by, and scaling one here would be the second copy of
   * `derive_cover_from_profile` the whole API exists to prevent. The item carries the
   * shutter's *current* assignment so that nothing but the travel is hypothetical.
   */
  private async _refreshTravelPreview(): Promise<void> {
    const state = this._store.state;
    const cover = this._detailCover;
    const typed = state.detail.form.height;
    if (!state.entryId || !cover || isEmpty(typed) || valueProblem("height", typed) !== null) {
      this._store.set({ detail: { ...this._store.state.detail, preview: null } });
      return;
    }
    const seq = ++this._previewSeq;
    this._store.set({ detail: { ...this._store.state.detail, previewing: true } });
    try {
      const answer = await fetchPreview(this.hass.connection, state.entryId, [
        { ...currentAssignment(cover), height: parseTravel(typed ?? "") },
      ]);
      if (seq !== this._previewSeq) {
        return;
      }
      this._store.set({
        detail: {
          ...this._store.state.detail,
          preview: answer.items[0] ?? null,
          previewing: false,
        },
      });
    } catch (error) {
      if (seq === this._previewSeq) {
        this._store.set({ detail: { ...this._store.state.detail, previewing: false } });
      }
      if (!isUnknownCommand(error)) {
        console.warn("MyHOME panel: the preview could not be read", asWsError(error));
      }
    }
  }

  /**
   * Everything that ends in "Configura", from wherever it was asked for.
   *
   * `engine/flow.ts` probes the frontend's private flow dialog and, when it is not there
   * or does not open, navigates to the integration page - which is the path the
   * acceptance criteria require and the only one that cannot be taken away. The panel says
   * a sentence first either way: a change of environment nobody announced is worse than a
   * slow one.
   */
  private _openFlow(source: HTMLElement): void {
    openOptionsFlow({
      source,
      entryId: this._store.state.entryId,
      onLeaving: () => this._store.announce(this._i18n.t("panel.common.opens_configure")),
    });
  }

  /**
   * The one `<h1>` of the page, which says which screen this is.
   *
   * A panel with four screens and one title is a panel whose browser tab, whose back
   * button and whose screen reader all say the same thing about four different places.
   */
  /**
   * The drawer's own heading: which shutter, or which profile, is inside it.
   *
   * A shutter's is its name and nothing else, as the design draws it. It used to be put
   * in a sentence - "Tapparella «{cover}»" - and a shutter's name nearly always starts
   * with the word already, so the heading read "Tapparella «Tapparella Soggiorno 2»". A
   * profile's keeps its sentence: a profile is called "Alte", and "Profilo «Alte»" is how
   * every group heading names it.
   */
  private _drawerTitle(): string {
    const state = this._store.state;
    const route = state.route;
    if (route.view === "cover") {
      const cover = this._detailCover;
      return cover ? cover.name : this._i18n.t("panel.detail.title");
    }
    if (route.view === "profile") {
      const known = state.overview?.profiles.some(
        (profile) => profile.name === route.params.name,
      );
      return known
        ? this._i18n.t("panel.profile.name", { profile: route.params.name })
        : this._i18n.t("panel.profile.title");
    }
    return this._i18n.t("panel.overview.title");
  }

  /**
   * The page's one h1, which is the list's title and stays it.
   *
   * It used to become the name of whatever card was open, because the card *was* the
   * page. The card is a drawer over the list now, so the name is the drawer's own
   * heading - the thing `aria-modal` points a reader at - and the h1 goes on naming the
   * region behind it.
   */
  private _title(): string {
    const state = this._store.state;
    if (state.route.view === "calibrate") {
      // The shutter's own name, which is what the wizard is about. The phase line and the
      // control that closes it, which the design puts beside it, arrive with lot F2.
      // `?.` on the cover as well, although the contract says it is always there: the
      // toolbar is drawn outside the wizard's own `try`, and a snapshot that surprises the
      // panel must cost the wizard its screen and never the panel its page.
      return (
        state.session?.cover?.name ??
        state.wizardIntent?.name ??
        this._i18n.t("panel.wizard.title")
      );
    }
    return this._i18n.t("panel.overview.title");
  }

  // --- the profile card (lot 8) ---------------------------------------------------------
  //
  // Everything this screen draws is already in `overview`, so there is no read of its own.
  // The one thing it asks the server is the impact preview, which is the editor's whole
  // reason for existing and the one number on it the panel may not work out.

  private get _profileRow(): ProfileRow | null {
    const state = this._store.state;
    return (
      state.overview?.profiles.find((row: ProfileRow) => row.name === state.profile.for) ?? null
    );
  }

  /** Every window that follows it, however it was told to. */
  private _followersOf(profile: ProfileRow | null): CoverRow[] {
    const covers = this._store.state.overview?.covers ?? [];
    if (!profile) {
      return [];
    }
    const ids = new Set([...profile.followers, ...profile.followers_from_file]);
    return covers.filter((cover: CoverRow) => ids.has(cover.unique_id));
  }

  /** The six fields as the form wants them: the profile's own numbers, written out. */
  private _profileForm(profile: ProfileRow | null): Record<string, string> {
    const form: Record<string, string> = {};
    for (const key of PROFILE_KEYS) {
      const value =
        key === "reference_height" ? profile?.reference_height : profile?.values[key];
      form[key] =
        value === null || value === undefined
          ? ""
          : this._i18n.number(value, DECIMALS[key] ?? 0);
    }
    return form;
  }

  /** The typed numbers, or `null` while one of them cannot be used. */
  private _typedProfile(): Record<string, number> | null {
    const form = this._store.state.profile.form;
    const values: Record<string, number> = {};
    for (const key of PROFILE_KEYS) {
      if (isEmpty(form[key]) || valueProblem(key, form[key]) !== null) {
        return null;
      }
      values[key] = parseTravel(form[key] ?? "") as number;
    }
    return values;
  }

  private _profileActions: ProfileActions = {
    back: this._closeDrawer,
    openCover: (uniqueId) => this._navigate(`/cover/${encodeURIComponent(uniqueId)}`),

    mode: (mode) => {
      const profile = this._store.state.profile;
      this._store.set({
        profile: {
          ...profile,
          mode,
          form: mode === "edit" ? this._profileForm(this._profileRow) : {},
          errors: {},
          newName: mode === "rename" ? (profile.for ?? "") : "",
          nameError: "",
          impact: null,
          impacting: false,
        },
        writeError: null,
      });
      if (mode === "edit") {
        void this._refreshImpact();
      }
    },

    field: (key, value) => {
      const profile = this._store.state.profile;
      this._store.set({ profile: { ...profile, form: { ...profile.form, [key]: value } } });
      this._scheduleImpact();
    },

    newName: (value) =>
      this._store.set({
        profile: { ...this._store.state.profile, newName: value, nameError: "" },
      }),

    saveValues: () => void this._saveProfile(),
    rename: () => void this._renameProfile(),
    remove: () => void this._deleteProfile(),
  };

  private async _saveProfile(): Promise<void> {
    const state = this._store.state;
    const name = state.profile.for;
    const values = this._typedProfile();
    if (this._locked || !name || !state.entryId || !values) {
      return;
    }
    const { reference_height: travel, ...rest } = values;
    const entryId = state.entryId;
    await this._write(
      () => sendProfileEdit(this.hass.connection, entryId, name, rest, travel),
      (result) => {
        this._store.set({
          profile: { ...this._store.state.profile, mode: "view", impact: null },
        });
        this._store.setOverview(result.overview);
        this._snack(
          result.affected.length === 1
            ? this._i18n.t("panel.toast.profile_saved_one", { profile: name })
            : this._i18n.t("panel.toast.profile_saved", {
                profile: name,
                count: result.affected.length,
              }),
          result.undo_token,
        );
      },
    );
  }

  /**
   * A rename is a write and a navigation: the address bar names the profile, so staying
   * where we were would leave the card asking about a name nothing defines any more.
   *
   * Its refusal goes under the field rather than to the top of the card, because the two
   * that can happen - the name is not usable, the name is taken - are both about the
   * eight characters the user just typed.
   */
  private async _renameProfile(): Promise<void> {
    const state = this._store.state;
    const name = state.profile.for;
    const next = state.profile.newName.trim();
    if (this._locked || !name || !state.entryId || !next || next === name) {
      return;
    }
    const entryId = state.entryId;
    await this._write(
      () => sendProfileRename(this.hass.connection, entryId, name, next),
      (result) => {
        this._store.setOverview(result.overview);
        this._navigate(`/profile/${encodeURIComponent(next)}`);
        this._snack(
          this._i18n.t("panel.toast.profile_renamed", { profile: next }),
          result.undo_token,
        );
      },
      (sentence) =>
        this._store.set({
          profile: { ...this._store.state.profile, nameError: sentence },
          writeError: null,
        }),
    );
  }

  private async _deleteProfile(): Promise<void> {
    const state = this._store.state;
    const name = state.profile.for;
    if (this._locked || !name || !state.entryId) {
      return;
    }
    const entryId = state.entryId;
    await this._write(
      () => sendProfileDelete(this.hass.connection, entryId, name),
      (result) => {
        this._store.setOverview(result.overview);
        // The screen this card was is gone with the profile; the list is where the
        // shutters it used to describe now are.
        this._navigate("/");
        this._snack(
          this._i18n.t("panel.toast.profile_deleted", { profile: name }),
          result.undo_token,
        );
      },
    );
  }

  private _scheduleImpact(): void {
    if (this._impactTimer) {
      clearTimeout(this._impactTimer);
    }
    this._impactTimer = setTimeout(() => {
      this._impactTimer = null;
      void this._refreshImpact();
    }, PREVIEW_DEBOUNCE_MS);
  }

  /**
   * What the typed numbers would mean for every follower (contract §11, `profile_values`).
   *
   * One item per follower carrying that follower's *current* assignment, so that nothing
   * but the profile is hypothetical - `currentAssignment` is what makes that exact for a
   * window whose `myhome.yaml` names the profile rather than this panel. The scaling is
   * the server's, here as everywhere: a profile scaled in the browser would be the second
   * travel model the whole API exists to prevent.
   */
  private async _refreshImpact(): Promise<void> {
    const state = this._store.state;
    const values = this._typedProfile();
    const name = state.profile.for;
    const followers = this._followersOf(this._profileRow);
    if (!state.entryId || !name || !values || followers.length === 0) {
      this._store.set({ profile: { ...this._store.state.profile, impact: null } });
      return;
    }
    const seq = ++this._previewSeq;
    this._store.set({ profile: { ...this._store.state.profile, impacting: true } });
    try {
      const answer = await fetchPreview(
        this.hass.connection,
        state.entryId,
        followers.map((cover) => currentAssignment(cover)),
        { [name]: values },
      );
      if (seq !== this._previewSeq) {
        return;
      }
      this._store.set({
        profile: { ...this._store.state.profile, impact: answer.items, impacting: false },
      });
    } catch (error) {
      if (seq === this._previewSeq) {
        this._store.set({ profile: { ...this._store.state.profile, impacting: false } });
      }
      if (!isUnknownCommand(error)) {
        console.warn("MyHOME panel: the impact preview could not be read", asWsError(error));
      }
    }
  }

  /**
   * "Try again", which re-reads the gateway **and** asks for live updates again.
   *
   * The subscription is attempted once, at boot. A panel that started while the backend
   * was reloading caught the refusal, fell back to the thirty-second poll, and stayed
   * there for the life of the tab - the one button on the screen that says "try again"
   * only ever retried the half that had nothing to do with it.
   */
  private async _retry(): Promise<void> {
    await this._refresh();
    if (this._store.state.connection !== "live") {
      await this._listen();
    }
  }

  // --- the guided calibration (0.6.0 wizard, lot F1) -------------------------------------
  //
  // The shell's half of the session: making the client, giving it what arrives over the
  // subscription, and turning the wizard's five actions into its verbs. The rules the
  // whole lot exists for are in `engine/session.ts` and are not restated here; what this
  // file must not do is the short list:
  //
  // * it never sends a heartbeat, and nothing here can stop one. The timer is the
  //   client's and this element is not on its path (lesson 1);
  // * it never starts a session from a route (lesson 4). `_readSession` reads;
  // * it never swallows the outcome of a cancel (lesson 2). Every branch ends either as a
  //   session that is over or as `sessionError`, which the screen draws with its ways out.

  /** The client for the gateway on the screen, made once and remade when it changes. */
  private _ensureSession(): SessionClient | null {
    const entryId = this._store.state.entryId;
    if (!entryId || !this.hass) {
      return null;
    }
    if (this._sessionClient && this._sessionClient.entryId === entryId) {
      return this._sessionClient;
    }
    this._sessionClient?.dispose();
    const client = new SessionClient({
      connection: this.hass.connection,
      entryId,
      onChange: (session: SessionSnapshot | null) => this._store.set({ session }),
    });
    this._sessionClient = client;
    this._store.set({ clientId: client.clientId, session: client.session });
    return client;
  }

  /**
   * Read the gateway's session, and take part in it. Both of them are reads.
   *
   * `get` says what there is; `attach` says that this tab is looking at it, and is what
   * starts the presence signal (SPEC §5.2). Neither moves anything - the contract is
   * explicit that a session picked up again shows where it stands and does not re-enter
   * its step (§11.1), and `tools/session.mjs` holds this to it with a snapshot taken in
   * the middle of a positioning run.
   *
   * Attaching while somebody else is present and owns it is read-only, and the server
   * says so; taking control from them is a button on the screen, never something that
   * happens by opening a page.
   */
  private async _readSession(): Promise<void> {
    const client = this._ensureSession();
    if (!client) {
      return;
    }
    const seen = await client.get();
    if (!seen.ok) {
      this._store.set({ sessionError: seen });
      return;
    }
    if (!seen.session || isOver(seen.session)) {
      this._store.set({ sessionError: null });
      return;
    }
    const joined = await client.attach(seen.session.session_id);
    this._store.set({ sessionError: joined.ok ? null : joined });
  }

  /**
   * Leaving the wizard's address: this tab's claim given back, best effort.
   *
   * Not the session - that is the server's, and a run under way finishes by itself. A
   * `leave` that never arrives costs forty-five seconds of presence and nothing else.
   */
  private _leaveSession(): void {
    const client = this._sessionClient;
    if (!client || !client.session) {
      return;
    }
    void client.leave();
  }

  /**
   * "Measure this shutter" - the one road into the wizard.
   *
   * The intention goes into the store **first** and the address is changed after it,
   * because the address says nothing about it: what a reload of `#/calibrate` finds is a
   * session or no session, never an instruction to open one.
   */
  private async _calibrate(intent: WizardIntent): Promise<void> {
    this._store.set({ wizardIntent: intent, sessionError: null });
    this._navigate("/calibrate");
    const client = this._ensureSession();
    if (!client) {
      return;
    }
    const result = await client.start(intent);
    this._store.set({ sessionError: result.ok ? null : result });
  }

  /**
   * "Cancel", from the wizard's own control or from its error card, through the robust
   * path of SPEC §5.2.
   *
   * The outcome is always shown: a branch that ended the session leaves the snapshot on
   * the screen with its outcome, and one that did not leaves `sessionError` with the ways
   * out the client worked out. Neither of them is silence.
   */
  private async _cancelSession(how: "plain" | "claim" | "force"): Promise<void> {
    const client = this._ensureSession();
    if (!client) {
      return;
    }
    const outcome =
      how === "claim"
        ? await client.claimAndCancel()
        : await client.cancel({ force: how === "force" });
    if (outcome.ok || !outcome.error) {
      this._store.set({ sessionError: null, wizardIntent: null });
      return;
    }
    this._store.set({
      sessionError: {
        error: outcome.error,
        recovery: outcome.recovery,
        freedAt: outcome.freedAt,
      },
    });
  }

  private _wizardActions: WizardActions = {
    refresh: () => void this._readSession(),
    cancel: () => void this._cancelSession("plain"),
    claim: () => void this._cancelSession("claim"),
    force: () => void this._cancelSession("force"),
    back: () => this._navigate("/"),
  };

  /**
   * What is on the page itself, which since the first live pass is always the list.
   *
   * The two routed cards are drawn over it by `_renderDrawer`, so this answers one
   * question - what is *behind* - and a deep link to a shutter renders the list first and
   * the drawer on top of it, on the same paint.
   */
  private _renderView(): TemplateResult {
    const state = this._store.state;

    if (state.status === "loading") {
      // The shape of the screen that is coming, not a sentence where it will be: a page
      // that grows its content under the reader is the thing a slow network must not do.
      return overviewSkeleton(this._i18n);
    }
    if (state.status === "error" || !state.overview) {
      const error = state.error;
      return html`<div class="card problem" role="alert">
        <div>
          ${this._i18n.refusal(error?.translation_key, error?.translation_placeholders ?? {})}
        </div>
        <div class="soft">${error ? `${error.code}: ${error.message}` : ""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${() => void this._retry()}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${FLOW_URL}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version ? html` · ${this._version}` : nothing}
        </div>
      </div>`;
    }
    const route = state.route;
    if (route.view === "calibrate") {
      return this._renderWizard();
    }
    if (route.view !== "overview" && !isDrawerRoute(route)) {
      // A typed URL, or a link to a screen this version does not have.
      return this._renderPlaceholder(
        this._i18n.t("panel.overview.title"),
        this._i18n.t("panel.common.not_yet"),
      );
    }
    return html`<myhome-overview
      .i18n=${this._i18n}
      .state=${state}
      .actions=${this._assignActions}
    ></myhome-overview>`;
  }

  /**
   * The wizard, and the guarantee that a wizard that throws does not empty the panel.
   *
   * The element catches its own exceptions and draws the error card (SPEC §5.8); this is
   * the second net, for anything that goes wrong on the way to it. Neither of them touches
   * the session: it is on the server, the presence signal is on its own timer, and what
   * the user sees is a screen with "Try again" and "End the calibration" on it rather than
   * a blank panel.
   */
  private _renderWizard(): TemplateResult {
    try {
      return html`<myhome-wizard
        .i18n=${this._i18n}
        .state=${this._store.state}
        .actions=${this._wizardActions}
      ></myhome-wizard>`;
    } catch (error) {
      console.error("MyHOME panel: the guided calibration could not be drawn", error);
      return html`<div class="card problem" role="alert">
        <div>${this._i18n.t("panel.wizard.render_error.title")}</div>
        <div class="soft">${this._i18n.t("panel.wizard.render_error.body")}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${() => void this._cancelSession("plain")}>
            ${this._i18n.t("panel.wizard.action.end")}
          </button>
          <a href=${FLOW_URL}>${this._i18n.t("panel.common.action.configure")}</a>
        </div>
      </div>`;
    }
  }

  /**
   * The cover's detail, or the profile's card, as a panel over the list.
   *
   * Nothing is drawn while the overview itself has refused to load: the drawer would be a
   * panel over a refusal, with a "try again" underneath it that the backdrop swallows.
   * While it is merely *late*, the drawer is there with the card's own skeleton in it -
   * which is what a deep link on a cold browser looks like, and it is the shape of the
   * card rather than a spinner for the same reason the list gets one.
   */
  private _renderDrawer(): TemplateResult | typeof nothing {
    const state = this._store.state;
    if (!isDrawerRoute(state.route) || state.status === "error") {
      return nothing;
    }
    const content =
      state.status === "loading"
        ? cardSkeleton(this._i18n)
        : state.route.view === "cover"
          ? html`<myhome-cover-detail
              .i18n=${this._i18n}
              .state=${state}
              .actions=${this._detailActions}
            ></myhome-cover-detail>`
          : html`<myhome-profile-card
              .i18n=${this._i18n}
              .state=${state}
              .actions=${this._profileActions}
            ></myhome-profile-card>`;
    return drawer({
      i18n: this._i18n,
      title: this._drawerTitle(),
      hasBack: this._drawerBack !== null,
      applying: state.applying,
      onClose: this._closeDrawer,
      content,
    });
  }

  protected override render(): TemplateResult {
    const state = this._store.state;
    const title = this._title();
    const measuring = state.overview?.measuring ?? null;
    const routed = state.route.view !== "overview";
    return html`
      <!--
        One named landmark for everything the panel draws, and deliberately not "main" or
        "banner": a custom panel is rendered inside Home Assistant's own document and the
        shell owns those. A region named by the page's own heading is a landmark a reader
        can jump to and one that cannot collide with the host's.
      -->
      <div class="page" role="region" aria-labelledby="panel-title">
        <div class="toolbar">
          ${this._renderMenuButton()}
          <h1 class="title" id="panel-title">${title}</h1>
          ${this._renderGatewayPicker()}
        </div>
      ${state.connection === "offline"
        ? html`<div class="offline" role="status">
            ${this._i18n.t("panel.error.no_connection")}
          </div>`
        : nothing}
      ${measuring ? measuringBanner(this._i18n, measuring.name, FLOW_URL) : nothing}
      <div class="content">
        ${liveRegion(state.announce)} ${this._renderView()}
        ${state.connection === "polling" && state.status === "ready"
          ? html`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`
          : nothing}
      </div>
      ${this._renderDrawer()}
      <!--
        The overview draws its own five strips, because three of them are about a gesture
        it owns, and it stops drawing them while a drawer is over it. The routed cards
        have no gestures and two of the five still apply to them: a write in the air, and
        what it came to with "Annulla" beside it. So exactly one of the two is drawing
        strips at any moment, and they are drawn over the drawer (z-index 70) because a
        refusal of a write made *inside* the drawer has to be readable from there.
      -->
      ${routed && state.applying ? applyingStrip(this._i18n) : nothing}
      ${routed && state.snack && !state.applying
        ? snackStrip(
            this._i18n,
            state.snack.message,
            state.snack.undoToken ? () => void this._undo() : null,
          )
        : nothing}
      </div>
    `;
  }

  /**
   * Which gateway this screen is about - shown only when there is a choice.
   *
   * The design's own decision, and the handoff's ("Header: hide the gateway select with a
   * single gateway"): nearly every installation has one, and a picker with one entry is a
   * control that teaches the user their house is more complicated than it is. A house with
   * two gets a real select, because `overview` is about one gateway at a time and merging
   * two orders into one list is not a screen anybody asked for.
   */
  private _renderGatewayPicker(): TemplateResult | typeof nothing {
    const state = this._store.state;
    const entries = state.overview?.entries ?? [];
    const current = entries.find((entry) => entry.entry_id === state.entryId);
    if (entries.length <= 1) {
      return nothing;
    }
    const label = this._i18n.t("panel.common.gateway", { gateway: current?.title ?? "" });
    return html`<select
      class="gateway"
      aria-label=${label}
      .value=${state.entryId ?? ""}
      ?disabled=${state.applying}
      @change=${(event: Event) =>
        void this._switchGateway((event.target as HTMLSelectElement).value)}
    >
      ${entries.map(
        (entry) => html`<option value=${entry.entry_id} ?selected=${entry.entry_id === state.entryId}>
          ${entry.title}
        </option>`,
      )}
    </select>`;
  }

  /**
   * Look at another gateway.
   *
   * Everything the screen was holding belongs to the one it is leaving - the pending
   * changes name shutters of that gateway, the card is about one of them - so all of it is
   * dropped rather than carried across, and the subscription is moved with the model: a
   * socket still pushing the old gateway's overviews would replace the new one's the next
   * time anybody wrote to it.
   */
  private async _switchGateway(entryId: string): Promise<void> {
    if (!entryId || entryId === this._store.state.entryId) {
      return;
    }
    const unsubscribe = this._unsubscribeWs;
    this._unsubscribeWs = null;
    await unsubscribe?.().catch(() => undefined);
    this._clearSnack();
    // The session is one gateway's, so the client for the old one is given back with the
    // subscription. The new gateway's is made by `_ensureSession` on the next read.
    const session = this._sessionClient;
    this._sessionClient = null;
    session?.dispose();
    this._store.set({
      ...NOTHING_PENDING,
      entryId,
      session: null,
      sessionError: null,
      wizardIntent: null,
      detail: NO_DETAIL,
      profile: NO_PROFILE_CARD,
      search: "",
      room: "",
      snack: null,
    });
    this._navigate("/");
    await this._refresh();
    await this._listen();
  }
}

// The two elements the shell renders. Referenced rather than merely imported, so that a
// bundler with aggressive side-effect pruning cannot decide the registrations are dead.
void MyHomeOverview;
void MyHomeCoverDetail;
void MyHomeProfileCard;
void MyHomeScreen;
void MyHomeWizard;

// Defined once, and only once: Home Assistant keeps a panel's module in the document after
// a navigation, so a second visit re-imports nothing - but a development reload would
// otherwise throw on the name.
if (!customElements.get("myhome-calibration-panel")) {
  customElements.define("myhome-calibration-panel", MyHomeCalibrationPanel);
}
