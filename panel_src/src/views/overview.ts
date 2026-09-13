// The overview: every shutter of one gateway, grouped by the profile it follows.
//
// This is the prototype (`Prototipo Assegnazione.dc.html`, `vista: panoramica`) translated
// into Lit, and the prototype is the specification: its measurements, its colours and its
// states are transcribed rather than redesigned. What is **not** transcribed is its
// arithmetic - `rescale`, `effKeys`, `originLabel` are a second implementation of
// `resolve_cover_config`, and two implementations of a travel model are two answers. Every
// number and every origin on this screen arrives from the server.
//
// **Read-only in this lot.** The handles are drawn and inert, there is no pending bar and
// no review panel; assignment is lot 7. The one thing that leaves this screen is a link
// into the options flow, which is where a measurement happens and will keep happening.
//
// The search box and the room select are client-side, over `overview.covers`, and the room
// comes from `area` - resolved server-side out of the entity and device registries, and
// `null` for a shutter nobody filed anywhere. Nothing groups, sorts or filters on an area
// being present: a house with no areas at all shows one select with one option and every
// shutter in its group.

import { LitElement, css, html, type TemplateResult } from "lit";

import { I18n } from "../engine/i18n";
import { renderMarkdown } from "../engine/markdown";
import { buttonStyles, cardStyles, fieldStyles, themeStyles } from "../engine/theme";
import { type CoverRow, type Overview, type ProfileRow } from "../engine/ws";
import { coverRowStyles } from "../components/cover-row";
import { groupCard, groupCardStyles, type PanelGroup } from "../components/group-card";
import { originChipStyles } from "../components/origin-chip";

/** The integration page, which is the way to "Configura" and therefore to every measurement. */
export const FLOW_URL = "/config/integrations/integration/myhome";

export class MyHomeOverview extends LitElement {
  static override properties = {
    i18n: { attribute: false },
    overview: { attribute: false },
    search: { type: String },
    room: { type: String },
  };

  declare i18n: I18n;
  declare overview: Overview | null;
  declare search: string;
  declare room: string;

  constructor() {
    super();
    this.i18n = new I18n();
    this.overview = null;
    this.search = "";
    this.room = "";
  }

  static override styles = [
    themeStyles,
    cardStyles,
    buttonStyles,
    fieldStyles,
    originChipStyles,
    coverRowStyles,
    groupCardStyles,
    css`
      :host {
        display: block;
        background: transparent;
      }

      .intro {
        margin: 8px 0 4px;
        max-width: 72ch;
      }

      .intro p {
        margin: 0 0 8px;
        line-height: 1.55;
      }

      .counts {
        margin: 0 0 16px;
        color: var(--myhome-text-soft);
      }

      .controls {
        display: flex;
        gap: 12px;
        align-items: center;
        flex-wrap: wrap;
        margin: 0 0 16px;
      }

      .controls .search {
        flex: 1 1 220px;
        max-width: 340px;
      }

      .controls .spacer {
        flex: 1 1 auto;
      }

      /*
       * The select draws its own arrow: only with appearance stripped does it take the
       * theme's own background and text colours, and the native arrow goes with it.
       *
       * The prototype drew the replacement as an SVG data URI with a fixed grey painted
       * into it. A data URI cannot read a CSS variable, so that grey would be the one
       * literal colour in the panel and the same grey in both themes - which is the thing
       * the handoff's first rule forbids. The chevron here is two borders on a wrapper's
       * pseudo-element instead, in the theme's own secondary text colour.
       */
      .select-wrap {
        position: relative;
        display: inline-flex;
      }

      .select-wrap::after {
        content: "";
        position: absolute;
        right: 13px;
        top: 50%;
        width: 7px;
        height: 7px;
        border-right: 1.6px solid var(--myhome-text-soft);
        border-bottom: 1.6px solid var(--myhome-text-soft);
        border-radius: 1px;
        transform: translateY(-70%) rotate(45deg);
        pointer-events: none;
      }

      select.field {
        appearance: none;
        padding-right: 36px;
      }

      a.cta {
        display: inline-flex;
        align-items: center;
        text-decoration: none;
      }

      .welcome {
        max-width: 640px;
        margin: 48px auto;
        padding: 32px;
      }

      .welcome h2 {
        margin: 0 0 12px;
        font-size: 22px;
        font-weight: 500;
      }

      .welcome p {
        margin: 0 0 8px;
        line-height: 1.55;
      }

      .welcome .soft {
        color: var(--myhome-text-soft);
        margin-bottom: 24px;
      }

      .welcome .after {
        margin: 12px 0 0;
        font-size: 13px;
        color: var(--myhome-text-soft);
      }

      .notice {
        padding: 16px;
        margin: 16px 0;
        font-size: 14px;
        line-height: 1.55;
      }

      .notice .actions {
        margin-top: 12px;
      }
    `,
  ];

  private _fire(name: string, detail?: unknown): void {
    this.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }

  /** The rooms the select offers: every area a shutter of this gateway really has. */
  private get _rooms(): string[] {
    const seen = new Set<string>();
    for (const cover of this.overview?.covers ?? []) {
      if (cover.area) {
        seen.add(cover.area);
      }
    }
    return Array.from(seen).sort((a, b) => a.localeCompare(b, this.i18n.language));
  }

  private _matches(cover: CoverRow): boolean {
    const needle = this.search.trim().toLowerCase();
    if (needle && !cover.name.toLowerCase().includes(needle)) {
      return false;
    }
    return !this.room || cover.area === this.room;
  }

  /**
   * The values line of a profile's header. Four numbers, in the reader's own language, and
   * the words around them from the texts - never a template assembled here out of units.
   */
  private _valuesLine(profile: ProfileRow): string {
    if (profile.missing || !profile.values || profile.values.opening_time === undefined) {
      return this.i18n.t("panel.overview.group.values_unknown");
    }
    return this.i18n.t("panel.overview.group.values", {
      travel: profile.reference_height === null ? "?" : this.i18n.number(profile.reference_height, 0),
      opening: this.i18n.number(profile.values.opening_time, 1),
      closing: this.i18n.number(profile.values.closing_time, 1),
      slat: this.i18n.number(profile.values.slat_time, 1),
    });
  }

  /**
   * Where the profile came from: the shutter it was measured on and when - and, when that
   * shutter has since been told to follow something else, that too. A profile measured on a
   * window that now follows another profile is not wrong, but it is surprising, and a
   * surprise the screen does not mention is a surprise the user finds out later.
   */
  private _provenanceLine(profile: ProfileRow): string {
    if (profile.source === "yaml") {
      return this.i18n.t("panel.overview.group.from_file");
    }
    if (!profile.measured_on) {
      return this.i18n.t("panel.overview.group.provenance_missing");
    }
    const date = profile.measured_at ? this.i18n.date(profile.measured_at) : "";
    if (!profile.measured_on_name) {
      return this.i18n.t("panel.overview.group.measured_on_gone", { date });
    }
    let line = this.i18n.t("panel.overview.group.measured_on", {
      cover: profile.measured_on_name,
      date,
    });
    const reference = (this.overview?.covers ?? []).find(
      (cover) => cover.unique_id === profile.measured_on,
    );
    if (reference && reference.profile !== profile.name) {
      const now = reference.profile ?? this.i18n.t("panel.overview.group.no_profile");
      line += ` · ${this.i18n.t("panel.profile.provenance_now_profile", { profile: now })}`;
    }
    return line;
  }

  /** The groups, in the server's profile order, with "Senza profilo" last. */
  private get _groups(): PanelGroup[] {
    const overview = this.overview;
    if (!overview) {
      return [];
    }
    const covers = [...overview.covers].sort((a, b) => a.order_index - b.order_index);
    const inGroup = (name: string | null): CoverRow[] =>
      covers.filter((cover) => (cover.profile ?? null) === name && this._matches(cover));
    const groups: PanelGroup[] = overview.profiles.map((profile, index) => ({
      key: profile.name,
      id: `group-${index}`,
      title: this.i18n.t("panel.overview.group.profile", { profile: profile.name }),
      values: this._valuesLine(profile),
      provenance: this._provenanceLine(profile),
      warning: profile.missing ? this.i18n.t("panel.overview.group.missing") : "",
      covers: inGroup(profile.name),
    }));
    groups.push({
      key: null,
      id: "group-none",
      title: this.i18n.t("panel.overview.group.no_profile"),
      values: this.i18n.t("panel.overview.group.no_profile_note"),
      provenance: "",
      warning: "",
      covers: inGroup(null),
    });
    return groups;
  }

  private _renderControls(): TemplateResult {
    return html`<div class="controls">
      <input
        class="field search"
        type="search"
        .value=${this.search}
        placeholder=${this.i18n.t("panel.common.search")}
        aria-label=${this.i18n.t("panel.common.search")}
        @input=${(event: Event) =>
          this._fire("myhome-search", (event.target as HTMLInputElement).value)}
      />
      <span class="select-wrap">
        <select
          class="field"
          aria-label=${this.i18n.t("panel.common.room_filter")}
          .value=${this.room}
          @change=${(event: Event) =>
            this._fire("myhome-room", (event.target as HTMLSelectElement).value)}
        >
          <option value="">${this.i18n.t("panel.common.all_rooms")}</option>
          ${this._rooms.map((room) => html`<option value=${room}>${room}</option>`)}
        </select>
      </span>
      <span class="spacer"></span>
      <a class="cta secondary compact" href=${FLOW_URL} title=${this.i18n.t("panel.firstrun.note")}
        >${this.i18n.t("panel.firstrun.action.measure")}</a
      >
    </div>`;
  }

  /**
   * The first run: no profile has ever been measured. The handoff is explicit that this is
   * a welcome and not an empty list - a list with nothing in it teaches nobody what a
   * profile is, and this is the one moment the panel has the user's attention for it.
   */
  private _renderFirstRun(): TemplateResult {
    return html`<section class="card welcome">
      <h2>${this.i18n.t("panel.firstrun.title")}</h2>
      <div>${this.i18n.md("panel.firstrun.body")}</div>
      <div class="soft">${this.i18n.md("panel.firstrun.how")}</div>
      <a class="cta" href=${FLOW_URL}>${this.i18n.t("panel.firstrun.action.measure")}</a>
      <p class="after">${this.i18n.t("panel.firstrun.note")}</p>
    </section>`;
  }

  protected override render(): TemplateResult {
    const overview = this.overview;
    if (!overview) {
      return html`<p>${this.i18n.t("panel.common.loading")}</p>`;
    }
    if (overview.no_basic_covers) {
      return html`<div class="card notice">
        ${renderMarkdown(this.i18n.t("panel.overview.no_basic_covers"))}
      </div>`;
    }
    // `profiles` carries every name defined *or* followed, so an empty list really is an
    // installation where nothing has ever been measured.
    if (overview.profiles.length === 0) {
      return this._renderFirstRun();
    }
    const groups = this._groups;
    const shown = groups.reduce((total, group) => total + group.covers.length, 0);
    const filtering = this.search.trim() !== "" || this.room !== "";
    return html`
      <div class="intro">${this.i18n.md("panel.overview.explanation")}</div>
      <p class="counts">
        ${this.i18n.t("panel.overview.summary", {
          profiles: overview.profiles.length,
          covers: overview.covers.length,
        })}
      </p>
      ${this._renderControls()}
      ${shown === 0 && filtering
        ? html`<div class="card notice">
            <div>${this.i18n.t("panel.overview.no_results")}</div>
            <div class="actions">
              <button class="cta text" type="button" @click=${() => this._fire("myhome-clear-filters")}>
                ${this.i18n.t("panel.overview.action.clear_filters")}
              </button>
            </div>
          </div>`
        : html`<div class="groups">
            ${groups.map((group) =>
              groupCard(group, {
                i18n: this.i18n,
                onOpenProfile: (name) => this._fire("myhome-open-profile", name),
                onOpenCover: (cover) => this._fire("myhome-open-cover", cover.unique_id),
              }),
            )}
          </div>`}
    `;
  }
}

if (!customElements.get("myhome-overview")) {
  customElements.define("myhome-overview", MyHomeOverview);
}
