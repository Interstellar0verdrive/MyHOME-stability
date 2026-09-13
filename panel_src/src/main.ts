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
import { assignItems, needsTravel, travelProblem, withPending } from "./engine/assign";
import { Router, type Route } from "./engine/router";
import { NOTHING_PENDING, Store } from "./engine/store";
import { buttonStyles, cardStyles, srOnly, themeStyles } from "./engine/theme";
import { liveRegion } from "./engine/a11y";
import {
  asWsError,
  assign as sendAssign,
  isUnknownCommand,
  overview as fetchOverview,
  preview as fetchPreview,
  reorder as sendReorder,
  subscribe,
  undo as sendUndo,
  type CalibrationEvent,
  type CoverRow,
} from "./engine/ws";
import { type HaPanelInfo, type HaRoute, type HomeAssistant } from "./types/ha";
import { measuringBanner, measuringBannerStyles } from "./components/measuring-banner";
import { FLOW_URL, MyHomeOverview, type AssignActions } from "./views/overview";
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

      .toolbar .gateway {
        font-size: 13px;
        opacity: 0.8;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 40%;
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
    this._router.start((route: Route) => this._store.set({ route }));
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
      this._store.set({ route: this._router.current });
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
    const count = items.length;
    this._store.announce(this._i18n.t("panel.assign.announce.applying"));
    await this._write(
      () => sendAssign(this.hass.connection, entryId, items, order),
      (result) => {
        this._store.set({ ...NOTHING_PENDING });
        this._store.setOverview(result.overview);
        this._snack(
          count === 1
            ? this._i18n.t("panel.toast.assigned_one")
            : this._i18n.t("panel.toast.assigned", { count }),
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
  ): Promise<void> {
    this._store.set({ applying: true, writeError: null });
    try {
      const result = await send();
      this._store.set({ applying: false });
      onDone(result);
    } catch (error) {
      const refusal = asWsError(error);
      this._store.set({ applying: false, writeError: refusal });
      this._store.announce(
        this._i18n.refusal(refusal.translation_key, refusal.translation_placeholders ?? {}),
      );
    }
  }

  private _snack(message: string, undoToken: string | null): void {
    this._clearSnack();
    this._store.set({ snack: { message, undoToken } });
    this._store.announce(message);
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
      const cover = state.overview.covers.find(
        (candidate: CoverRow) => candidate.unique_id === route.params.id,
      );
      return this._renderPlaceholder(
        cover
          ? this._i18n.t("panel.detail.named", { cover: cover.name })
          : this._i18n.t("panel.detail.unknown"),
        this._i18n.t("panel.common.not_yet"),
      );
    }
    if (route.view === "profile") {
      const name = route.params.name;
      const known = state.overview.profiles.some((profile) => profile.name === name);
      return this._renderPlaceholder(
        known
          ? this._i18n.t("panel.profile.name", { profile: name })
          : this._i18n.t("panel.profile.unknown"),
        this._i18n.t("panel.common.not_yet"),
      );
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
    const title = this._i18n.t("panel.overview.title");
    const gateway = state.overview?.entries.find((entry) => entry.entry_id === state.entryId);
    const measuring = state.overview?.measuring ?? null;
    return html`
      <div class="toolbar">
        ${this._renderMenuButton()} ${this._renderBackButton()}
        <h1 class="title">${title}</h1>
        ${gateway && (state.overview?.entries.length ?? 0) > 1
          ? html`<div class="gateway">
              ${this._i18n.t("panel.common.gateway", { gateway: gateway.title })}
            </div>`
          : nothing}
      </div>
      ${measuring ? measuringBanner(this._i18n, measuring.name, FLOW_URL) : nothing}
      <div class="content">
        ${liveRegion(state.announce)} ${this._renderView()}
        ${state.connection === "polling" && state.status === "ready"
          ? html`<p class="connection">${this._i18n.t("panel.common.polling")}</p>`
          : nothing}
      </div>
    `;
  }
}

// The two elements the shell renders. Referenced rather than merely imported, so that a
// bundler with aggressive side-effect pruning cannot decide the registrations are dead.
void MyHomeOverview;
void MyHomeScreen;

// Defined once, and only once: Home Assistant keeps a panel's module in the document after
// a navigation, so a second visit re-imports nothing - but a development reload would
// otherwise throw on the name.
if (!customElements.get("myhome-calibration-panel")) {
  customElements.define("myhome-calibration-panel", MyHomeCalibrationPanel);
}
