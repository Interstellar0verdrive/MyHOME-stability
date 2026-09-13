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
import { Router, type Route } from "./engine/router";
import { Store } from "./engine/store";
import { buttonStyles, cardStyles, srOnly, themeStyles } from "./engine/theme";
import { liveRegion } from "./engine/a11y";
import {
  asWsError,
  isUnknownCommand,
  overview as fetchOverview,
  subscribe,
  type CalibrationEvent,
  type CoverRow,
} from "./engine/ws";
import { type HaPanelInfo, type HaRoute, type HomeAssistant } from "./types/ha";
import { measuringBanner, measuringBannerStyles } from "./components/measuring-banner";
import { FLOW_URL, MyHomeOverview } from "./views/overview";
import { MyHomeScreen, type ScreenModel } from "./engine/screen";

/** How often the panel asks again when the backend has no subscription to offer. */
const POLL_MS = 30_000;

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

      .toolbar .title {
        flex: 1;
        min-width: 0;
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
      this._store.setOverview(event.overview);
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
      this._store.announce(
        event.cover_unique_id
          ? this._i18n.t("panel.banner.measuring_body", { cover: event.name ?? "" })
          : "",
      );
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

  private _renderView(): TemplateResult {
    const state = this._store.state;
    if (state.status === "loading") {
      return html`<div class="card problem" role="status">
        ${this._i18n.t("panel.common.loading")}
      </div>`;
    }
    if (state.status === "error" || !state.overview) {
      const error = state.error;
      const key = error?.translation_key ? `panel.error.${error.translation_key}` : "panel.error.unreachable";
      return html`<div class="card problem" role="alert">
        <div>${this._i18n.t(key, error?.translation_placeholders ?? {})}</div>
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
          ? this._i18n.t("panel.cover.title", { cover: cover.name })
          : this._i18n.t("panel.cover.unknown"),
        this._i18n.t("panel.common.not_yet"),
      );
    }
    if (route.view === "profile") {
      const name = route.params.name;
      const known = state.overview.profiles.some((profile) => profile.name === name);
      return this._renderPlaceholder(
        known
          ? this._i18n.t("panel.profile.title", { profile: name })
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
      .overview=${state.overview}
      .search=${state.search}
      .room=${state.room}
      @myhome-search=${(event: CustomEvent<string>) => this._store.set({ search: event.detail })}
      @myhome-room=${(event: CustomEvent<string>) => this._store.set({ room: event.detail })}
      @myhome-clear-filters=${() => this._store.set({ search: "", room: "" })}
      @myhome-open-cover=${(event: CustomEvent<string>) =>
        this._navigate(`/cover/${encodeURIComponent(event.detail)}`)}
      @myhome-open-profile=${(event: CustomEvent<string>) =>
        this._navigate(`/profile/${encodeURIComponent(event.detail)}`)}
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
        <div class="title">${title}</div>
        ${gateway && (state.overview?.entries.length ?? 0) > 1
          ? html`<div class="gateway">
              ${this._i18n.t("panel.overview.gateway", { gateway: gateway.title })}
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
