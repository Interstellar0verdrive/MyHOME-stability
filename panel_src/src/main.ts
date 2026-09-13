// <myhome-calibration-panel> - the element Home Assistant instantiates at
// /myhome-calibration.
//
// 0.6.0 lot 4 is the toolchain and the way in, not the application: this is a real
// element that really talks to the real backend, and it renders one screen - the header
// and a line of proof that the WebSocket contract works end to end. The router, the
// screen engine, the views and the assignment gestures are lots 5 to 8, and they hang
// off this file without changing it.
//
// **The element contract.** Home Assistant sets four *properties* (never attributes) on
// the element: `hass`, `narrow`, `route` and `panel`. That is frontend-repo behaviour
// (`src/panels/custom/ha-panel-custom.ts`); the Python side only proves what is *sent*
// (`frontend.Panel.to_response`). All four are declared `attribute: false` accordingly.
//
// **`hass` changes identity on every state update in the whole installation** - a light
// switched on at the other end of the house replaces it. `shouldUpdate` therefore asks
// what actually changed before repainting, which is the difference between a panel that
// renders when something happened and one that renders at the rate the house generates
// events.

import { LitElement, css, html, nothing, type PropertyValues, type TemplateResult } from "lit";

import { I18n } from "./engine/i18n";
import { defined, toggleSidebar } from "./engine/ha";
import { themeStyles } from "./engine/theme";
import { asWsError, overview, type Overview, type WsError } from "./engine/ws";
import { type HaPanelInfo, type HaRoute, type HomeAssistant } from "./types/ha";

/**
 * The English words the skeleton needs before the texts lot writes the `panel.*` block.
 *
 * Every one of these is a `t(key, fallback)` call the texts lot deletes; until then a
 * panel with no keys still renders something a person can read, rather than a screen of
 * dotted identifiers.
 */
const FALLBACK = {
  title: "Profiles and shutters",
  menu: "Open the sidebar",
  loading: "Loading…",
  summary: "{profiles} profiles, {covers} shutters",
  problem: "The panel could not read this gateway.",
  configure: "Open Configure instead",
};

export class MyHomeCalibrationPanel extends LitElement {
  static override properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    route: { attribute: false },
    panel: { attribute: false },
    _overview: { state: true },
    _error: { state: true },
    _ready: { state: true },
  };

  declare hass: HomeAssistant;
  declare narrow: boolean;
  declare route: HaRoute;
  declare panel: HaPanelInfo | null;

  private _i18n = new I18n();
  private _overview: Overview | null = null;
  private _error: WsError | null = null;
  private _ready = false;
  private _language = "";

  constructor() {
    super();
    this.narrow = false;
    this.panel = null;
  }

  static override styles = [
    themeStyles,
    css`
      .toolbar {
        display: flex;
        align-items: center;
        gap: 8px;
        height: 56px;
        padding: 0 8px;
        box-sizing: border-box;
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

      /* The fallback for ha-menu-button: 48x48, like every target in the handoff. */
      button.menu {
        width: 48px;
        height: 48px;
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

      .card {
        background: var(--myhome-card);
        border-radius: var(--myhome-radius);
        box-shadow: var(--ha-card-box-shadow, 0 2px 2px rgba(0, 0, 0, 0.12));
        padding: 16px;
        font-size: 14px;
      }

      .card.problem {
        background: color-mix(in srgb, var(--myhome-error) 12%, var(--myhome-card));
        color: var(--myhome-text);
      }

      .soft {
        color: var(--myhome-text-soft);
        font-size: 13px;
        margin-top: 8px;
      }

      a {
        color: var(--myhome-primary);
      }
    `,
  ];

  /**
   * Repaint when something changed, not when the house did.
   *
   * `hass` alone is not news: it is a new object on every state update anywhere in the
   * installation. The panel's own model arrives over the WebSocket, so the only things
   * it watches on `hass` are the user's language - which decides the sentences - and,
   * from lot 7 on, the `Calibrating` attribute of its own covers.
   */
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
    if (changed.has("hass") && this._ready && this._languageOf(this.hass) !== this._language) {
      void this._loadTexts();
    }
  }

  private _languageOf(hass: HomeAssistant | undefined): string {
    return hass?.locale?.language || hass?.language || "en";
  }

  /**
   * Read the sentences and the gateway, once, and survive either failing.
   *
   * A panel that throws on load shows a blank page and no server-side error, which is
   * the worst failure mode this feature has (plan, R3). So the bootstrap catches its own
   * errors and renders them, naming the version it is and pointing at "Configura" - which
   * remains a complete path to everything the panel does.
   */
  private async _bootstrap(): Promise<void> {
    await this._loadTexts();
    try {
      this._overview = await overview(this.hass.connection);
      this._error = null;
    } catch (error) {
      this._error = asWsError(error);
    }
    this._ready = true;
  }

  private async _loadTexts(): Promise<void> {
    const language = this._languageOf(this.hass);
    try {
      await this._i18n.load(this.hass.connection, language);
    } catch {
      // The texts are a convenience; a panel with no sentences still counts shutters.
      // `t()` falls back to the key, or to the English word the skeleton passes it.
    }
    this._language = language;
    this.requestUpdate();
  }

  private get _version(): string {
    return this.panel?.config?.version ?? "";
  }

  private _renderMenuButton(): TemplateResult | typeof nothing {
    if (!this.narrow) {
      return nothing;
    }
    // Home Assistant's own hamburger when it is there - and it is, in every version of
    // the frontend this integration supports - and a button that fires the same event
    // when the name changes under us. The sidebar is the only way off a phone screen.
    if (defined("ha-menu-button")) {
      return html`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`;
    }
    return html`<button
      class="menu"
      type="button"
      aria-label=${this._i18n.t("panel.common.action.menu", FALLBACK.menu)}
      @click=${() => toggleSidebar(this)}
    >
      ☰
    </button>`;
  }

  private _renderBody(): TemplateResult {
    if (!this._ready) {
      return html`<div class="card">${this._i18n.t("panel.common.loading", FALLBACK.loading)}</div>`;
    }
    if (this._error || !this._overview) {
      const error = this._error;
      return html`<div class="card problem">
        <div>${this._i18n.t("panel.error.not_found", FALLBACK.problem)}</div>
        <div class="soft">${error ? `${error.code}: ${error.message}` : ""}</div>
        <div class="soft">
          <a href="/config/integrations/integration/myhome"
            >${this._i18n.t("panel.common.action.configure", FALLBACK.configure)}</a
          >
          ${this._version ? html` · ${this._version}` : nothing}
        </div>
      </div>`;
    }
    // The proof that the contract works end to end: two numbers that could only have
    // come from `resolve_cover` on the server. Lots 7 and 8 replace this with the
    // groups, the rows and the chips; until they do, this is what says the plumbing is
    // sound on a real gateway.
    const summary = this._i18n
      .t("panel.overview.summary", FALLBACK.summary)
      .replace("{profiles}", String(this._overview.profiles.length))
      .replace("{covers}", String(this._overview.covers.length));
    return html`<div class="card">
      <div>${summary}</div>
      <div class="soft">
        ${this._overview.entries.map((entry) => entry.title).join(" · ")}
        ${this._version ? html` · ${this._version}` : nothing}
      </div>
    </div>`;
  }

  protected override render(): TemplateResult {
    const title = this._i18n.t("panel.overview.title", this.panel?.title ?? FALLBACK.title);
    return html`
      <div class="toolbar">
        ${this._renderMenuButton()}
        <div class="title">${title}</div>
      </div>
      <div class="content">${this._renderBody()}</div>
    `;
  }
}

// Defined once, and only once: Home Assistant keeps a panel's module in the document
// after a navigation, so a second visit re-imports nothing - but a development reload
// would otherwise throw on the name.
if (!customElements.get("myhome-calibration-panel")) {
  customElements.define("myhome-calibration-panel", MyHomeCalibrationPanel);
}
