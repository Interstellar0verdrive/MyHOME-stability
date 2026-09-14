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
import { Router, type Route } from "./engine/router";
import { NOTHING_PENDING, NO_DETAIL, NO_PROFILE_CARD, Store } from "./engine/store";
import { buttonStyles, cardStyles, srOnly, themeStyles } from "./engine/theme";
import { liveRegion } from "./engine/a11y";
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
import { measuringBanner, measuringBannerStyles } from "./components/measuring-banner";
import { applyingStrip, snackStrip, stripStyles } from "./components/strips";
import { FLOW_URL, MyHomeOverview, type AssignActions } from "./views/overview";
import { DETAIL_KEYS, MyHomeCoverDetail, type DetailActions } from "./views/cover-detail";
import { MyHomeProfileCard, PROFILE_KEYS, type ProfileActions } from "./views/profile-card";
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
    stripStyles,
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

      a {
        color: var(--myhome-primary);
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
    window.removeEventListener("location-changed", this._onReturn);
    document.removeEventListener("visibilitychange", this._onReturn);
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
    const unsubscribe = this._unsubscribeWs;
    this._unsubscribeWs = null;
    // The socket outlives the element, so a subscription that is not given back keeps a
    // gateway pushing overviews at nobody for the rest of the session.
    void unsubscribe?.().catch(() => undefined);
  }

  protected override shouldUpdate(changed: PropertyValues): boolean {
    if (changed.size > 1 || !changed.has("hass")) {
      return true;
    }
    return this._languageOf(this.hass) !== this._language;
  }

  protected override firstUpdated(): void {
    void this._bootstrap();
  }

  protected override updated(changed: PropertyValues): void {
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
    await this._loadTexts();
    await this._refresh();
    // A deep link is answered only now: `cover_detail` needs a gateway, and until the
    // overview has named one there is nothing to ask it about.
    await this._loadDetail();
    await this._listen();
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
  private async _listen(): Promise<void> {
    try {
      this._unsubscribeWs = await subscribe(
        this.hass.connection,
        this._store.state.entryId,
        (event: CalibrationEvent) => this._onEvent(event),
      );
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
      if (this._store.state.review) {
        this._schedulePreview();
      }
      // The card is a second payload and a push says nothing about it. Re-read it while
      // it is on the screen, so a measurement finished in the dialog - or a change made
      // in another tab - reaches the rows that are being looked at.
      if (this._store.state.detail.for) {
        void this._loadDetail();
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

  private _renderBackButton(): TemplateResult | typeof nothing {
    if (this._store.state.route.view === "overview") {
      return nothing;
    }
    return html`<button
      type="button"
      aria-label=${this._i18n.t("panel.common.action.back")}
      @click=${() => this._navigate("/")}
    >
      ←
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
    const items = assignItems(state.pending, state.heights);
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
        assignItems(state.pending, state.heights),
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
    back: () => this._navigate("/"),
    retry: () => {
      this._store.set({ detail: { ...this._store.state.detail, loading: true, error: null } });
      void this._loadDetail();
    },
    openProfile: (name) => this._navigate(`/profile/${encodeURIComponent(name)}`),

    /**
     * "Assegna a un profilo…" is the overview's own gesture, so it is the overview's own
     * dialog: the card hands the shutter over and steps out of the way, rather than
     * growing a second copy of "Quale profilo?" with a second idea of what a pending
     * change is.
     */
    assign: () => {
      const id = this._store.state.detail.for;
      this._store.set({ dialog: id });
      this._navigate("/");
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
  private _title(): string {
    const state = this._store.state;
    const route = state.route;
    if (route.view === "cover") {
      const cover = this._detailCover;
      return cover
        ? this._i18n.t("panel.detail.named", { cover: cover.name })
        : this._i18n.t("panel.detail.title");
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
    back: () => this._navigate("/"),
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

  private _renderView(): TemplateResult {
    const state = this._store.state;

    if (state.status === "loading") {
      return html`<div class="card waiting" role="status">
        ${this._i18n.t("panel.common.loading")}
      </div>`;
    }
    if (state.status === "error" || !state.overview) {
      const error = state.error;
      return html`<div class="card problem" role="alert">
        <div>
          ${this._i18n.refusal(error?.translation_key, error?.translation_placeholders ?? {})}
        </div>
        <div class="soft">${error ? `${error.code}: ${error.message}` : ""}</div>
        <div class="soft">
          <button class="cta text" type="button" @click=${() => void this._refresh()}>
            ${this._i18n.t("panel.common.action.retry")}
          </button>
          <a href=${FLOW_URL}>${this._i18n.t("panel.common.action.configure")}</a>
          ${this._version ? html` · ${this._version}` : nothing}
        </div>
      </div>`;
    }
    const route = state.route;
    if (route.view === "cover") {
      return html`<myhome-cover-detail
        .i18n=${this._i18n}
        .state=${state}
        .actions=${this._detailActions}
      ></myhome-cover-detail>`;
    }
    if (route.view === "profile") {
      return html`<myhome-profile-card
        .i18n=${this._i18n}
        .state=${state}
        .actions=${this._profileActions}
      ></myhome-profile-card>`;
    }
    if (route.view !== "overview") {
      // `/calibrate/…` is reserved for 0.7.0, and anything else is a typed URL.
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

  protected override render(): TemplateResult {
    const state = this._store.state;
    const title = this._title();
    const measuring = state.overview?.measuring ?? null;
    const routed = state.route.view !== "overview";
    return html`
      <div class="toolbar">
        ${this._renderMenuButton()} ${this._renderBackButton()}
        <h1 class="title">${title}</h1>
        ${this._renderGatewayPicker()}
      </div>
      ${measuring ? measuringBanner(this._i18n, measuring.name, FLOW_URL) : nothing}
      <div class="content">
        ${liveRegion(state.announce)} ${this._renderView()}
        ${state.connection === "polling" && state.status === "ready"
          ? html`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`
          : nothing}
      </div>
      <!--
        The overview draws its own five strips, because three of them are about a gesture
        it owns. The routed cards have no gestures and two of the five still apply to them:
        a write in the air, and what it came to with "Annulla" beside it.
      -->
      ${routed && state.applying ? applyingStrip(this._i18n) : nothing}
      ${routed && state.snack && !state.applying
        ? snackStrip(
            this._i18n,
            state.snack.message,
            state.snack.undoToken ? () => void this._undo() : null,
          )
        : nothing}
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
    this._store.set({
      ...NOTHING_PENDING,
      entryId,
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

// Defined once, and only once: Home Assistant keeps a panel's module in the document after
// a navigation, so a second visit re-imports nothing - but a development reload would
// otherwise throw on the name.
if (!customElements.get("myhome-calibration-panel")) {
  customElements.define("myhome-calibration-panel", MyHomeCalibrationPanel);
}
