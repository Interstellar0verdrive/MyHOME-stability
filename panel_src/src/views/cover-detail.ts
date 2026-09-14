// One shutter, and where every number it runs on comes from.
//
// `#/cover/<unique_id>`. The prototype draws this as a panel over the overview
// (`Prototipo Assegnazione.dc.html`, `detailOpen`); here it is a **screen of its own**,
// because the plan gives it a route and requires a deep link to it to work on first paint
// (§3.3: "opening /myhome-calibration/cover/aa:bb:…-3-2 renders the detail view"). A modal
// over a list nobody has loaded yet is not a thing a URL can produce. Everything else is
// the prototype's - the same rows, the same four modes, the same sentences, the same
// order of the buttons.
//
// **The panel works nothing out.** Each row's number, its origin, what it would inherit
// and what removing the measurement would leave all arrive from
// `myhome/calibration/cover_detail`. The one screen here that shows a number nobody has
// stated yet is the travel editor, and that number comes from
// `myhome/calibration/preview`: changing a window's travel rescales its profile, which is
// arithmetic, and the arithmetic is the server's on every screen of this panel.
//
// The hand edit is the exception that proves it: an edited value is either exactly the
// number typed - it beats the profile and the file, which is what "valore proprio" means -
// or, for an emptied field, the key's own `inherited_value`, which `cover_detail` has
// already answered. So the resulting values are a lookup and not a second travel model,
// and no round trip is made for them.
//
// **Five keys, not eight.** `values` carries `roll`, `stop_latency` and `start_delay` too.
// `roll` is the fallback of the two directional coefficients and is never what a
// calibrated shutter runs on (`panel_data.PROFILE_VALUE_KEYS` says so and leaves it out
// for the same reason); the other two are timings no measurement sets and no form offers.
// Printing them would be offering the user three more numbers to correct that correct
// nothing, and none of the three has a label in any of the eight translation files.

import { LitElement, html, nothing, type TemplateResult } from "lit";

import { focusWhenPainted } from "../engine/a11y";
import { DECIMALS, ROLL_KEYS, TABLE_KEYS } from "../engine/assign";
import { FIELDS, UNIT_KEY, isEmpty, valueProblem } from "../engine/fields";
import { I18n } from "../engine/i18n";
import { initialState, type PanelState } from "../engine/store";
import { buttonStyles, cardStyles, fieldStyles, themeStyles } from "../engine/theme";
import { type CoverKeyRow, type CoverRow, type PreviewItem } from "../engine/ws";
import {
  cardFoot,
  cardPageStyles,
  numberField,
  valueRow,
  wideButton,
} from "../components/card-page";
import { originChip, originChipStyles } from "../components/origin-chip";

/** The five the card shows and the form edits, in the order the guided dialog asks them. */
export const DETAIL_KEYS: readonly string[] = [...TABLE_KEYS, ...ROLL_KEYS];

/**
 * Everything this screen can ask for. Implemented once, in `main.ts`, beside the socket -
 * the same arrangement `AssignActions` has, and for the same reason: a view that could
 * reach a shutter on its own would be a second place to look for what this panel writes.
 */
export interface DetailActions {
  back: () => void;
  retry: () => void;
  openProfile: (name: string) => void;
  /** "Assegna a un profilo…": the overview, with "Quale profilo?" already open. */
  assign: () => void;
  mode: (mode: PanelState["detail"]["mode"]) => void;
  field: (key: string, value: string) => void;
  saveValues: () => void;
  saveTravel: () => void;
  remove: () => void;
  /** "Misura di nuovo", "Correggi… → …", "Calibrazione approfondita": all end in the flow. */
  openFlow: (source: HTMLElement) => void;
}

export class MyHomeCoverDetail extends LitElement {
  static override properties = {
    i18n: { attribute: false },
    state: { attribute: false },
    actions: { attribute: false },
  };

  declare i18n: I18n;
  declare state: PanelState;
  declare actions: DetailActions;

  constructor() {
    super();
    this.i18n = new I18n();
    this.state = initialState({ view: "cover", params: {}, path: "/" });
    this.actions = {} as DetailActions;
  }

  static override styles = [
    themeStyles,
    cardStyles,
    buttonStyles,
    fieldStyles,
    originChipStyles,
    cardPageStyles,
  ];

  override connectedCallback(): void {
    super.connectedCallback();
    window.addEventListener("keydown", this._onKey);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    window.removeEventListener("keydown", this._onKey);
  }

  /**
   * Escape steps back once: out of a form into the card, and out of the card to the list.
   *
   * The same rule the overview's Escape follows, and the same guard: nothing is given back
   * while a write is in the air, because the screen the user would land on has no idea
   * what the gateway is doing.
   */
  private _onKey = (event: KeyboardEvent): void => {
    if (event.key !== "Escape" || this.state.applying) {
      return;
    }
    if (this.state.detail.mode !== "view") {
      this.actions.mode("view");
      return;
    }
    this.actions.back();
  };

  /**
   * Focus lands on the heading of whatever is now on screen.
   *
   * A screen that changes under a keyboard user without moving focus leaves them at the
   * top of the document with no idea that anything happened; a heading is where a screen
   * reader would start reading anyway, and `tabindex="-1"` makes it a target without
   * putting it in the tab order.
   */
  protected override updated(): void {
    // Which screen this is, as far as focus is concerned: a different shutter or a
    // different mode is a different screen, and the same one repainted is not.
    //
    // It is compared against what was *focused*, not against the previous state, because
    // the heading does not exist yet at the moment the route changes: the card is still
    // waiting for `cover_detail` and there is nothing to focus. Remembering the pair
    // means the move happens on the paint that first draws a heading, whenever that is.
    const detail = this.state.detail;
    const screen = `${detail.for ?? ""}|${detail.mode}`;
    if (screen === this._focused) {
      return;
    }
    const heading = this.renderRoot.querySelector<HTMLElement>("[data-heading]");
    if (!heading) {
      return;
    }
    this._focused = screen;
    focusWhenPainted(() => heading);
  }

  /** The screen whose heading already has focus, so it is not taken again on a repaint. */
  private _focused = "";

  private get _locked(): boolean {
    return this.state.overview?.measuring != null || this.state.applying;
  }

  private _label(key: string): string {
    return this.i18n.t(`options.step.calibration_edit.data.${key}`);
  }

  private _unit(key: string): string {
    const unit = UNIT_KEY[key];
    return unit ? this.i18n.t(unit) : "";
  }

  private _number(key: string, value: number): string {
    return this.i18n.number(value, DECIMALS[key] ?? FIELDS[key]?.decimals ?? 1);
  }

  /** The refusal sentence for one field, in the words the API itself would use. */
  private _problem(key: string, problem: string): string {
    return this.i18n.refusal(problem, {
      key: this._label(key),
      min: FIELDS[key]?.min ?? 0,
      max: FIELDS[key]?.max ?? 0,
      cover: this.state.detail.answer?.cover.name ?? "",
    });
  }

  /** Where this cover's values will come from once its own measurements are gone. */
  private _destination(): string {
    const forget = this.state.detail.answer?.forget;
    if (!forget) {
      return "";
    }
    if (forget.falls_back_to === "profile") {
      return this.i18n.t("panel.detail.destination.profile", {
        profile: forget.profile ?? "",
      });
    }
    return forget.falls_back_to === "file"
      ? this.i18n.t("panel.detail.destination.file")
      : this.i18n.t("panel.detail.destination.defaults");
  }

  protected override render(): TemplateResult {
    const detail = this.state.detail;
    if (detail.loading) {
      return html`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`;
    }
    if (!detail.answer) {
      return html`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.unknown")}</h2>
        <p class="sub">
          ${detail.error
            ? this.i18n.refusal(
                detail.error.translation_key,
                detail.error.translation_placeholders ?? {},
              )
            : ""}
        </p>
        ${cardFoot(
          this.i18n.t("panel.common.action.retry"),
          this.actions.retry,
          html`<button class="cta secondary compact" type="button" @click=${this.actions.back}>
            ${this.i18n.t("panel.common.action.back")}
          </button>`,
        )}
      </div>`;
    }
    return html`${this._head(detail.answer.cover)}
    ${this.state.writeError
      ? html`<div class="card refusal" role="alert">
          ${this.i18n.refusal(
            this.state.writeError.translation_key,
            this.state.writeError.translation_placeholders ?? {},
          )}
        </div>`
      : nothing}
    ${detail.mode === "view" ? this._view(detail.answer.cover, detail.answer.keys) : nothing}
    ${detail.mode === "edit" ? this._edit(detail.answer.keys) : nothing}
    ${detail.mode === "travel" ? this._travel(detail.answer.cover) : nothing}
    ${detail.mode === "correct" ? this._correct() : nothing}
    ${detail.mode === "remove" ? this._remove(detail.answer.cover) : nothing}`;
  }

  /** Who this window is, what it runs on and how thoroughly it was measured. */
  private _head(cover: CoverRow): TemplateResult {
    const parts = [
      cover.area,
      cover.height === null
        ? this.i18n.t("panel.overview.cover.travel_unknown")
        : this.i18n.t("panel.overview.cover.travel", {
            travel: this.i18n.number(cover.height, 0),
          }),
      cover.profile ? this.i18n.t("panel.overview.cover.follows", { profile: cover.profile }) : null,
    ].filter((part): part is string => Boolean(part));
    const level =
      cover.level === "precise"
        ? this.i18n.t("panel.detail.level_thorough")
        : cover.level === "basic"
          ? this.i18n.t("panel.detail.level_basic")
          : null;
    return html`<section class="card">
      <p class="sub">${parts.join(" · ")}</p>
      <div class="chips">
        ${originChip(this.i18n, cover.origin, cover.profile, false)}
        ${cover.measured_at
          ? html`<span class="chip"
              >${this.i18n.t("panel.detail.measured_at", {
                date: this.i18n.date(cover.measured_at),
              })}${level ? ` · ${level}` : ""}</span
            >`
          : nothing}
        ${cover.verify_note !== null
          ? html`<span class="chip"
              >${this.i18n.t("panel.detail.verify_note", {
                deviation: this.i18n.number(cover.verify_note, 1),
              })}</span
            >`
          : nothing}
      </div>
      ${cover.profile_missing
        ? html`<p class="warn" style="margin-top:12px;margin-bottom:0">
            ${this.i18n.t("panel.overview.cover.profile_missing", {
              profile: cover.profile ?? "",
            })}
          </p>`
        : nothing}
      ${cover.profile_from_file
        ? html`<p class="sub" style="margin-top:8px">
            ${this.i18n.t("panel.overview.cover.from_file")}
          </p>`
        : nothing}
    </section>`;
  }

  // ------------------------------------------------------------------ the card itself
  private _view(cover: CoverRow, keys: readonly CoverKeyRow[]): TemplateResult {
    const rows = DETAIL_KEYS.map((key) => keys.find((row) => row.key === key)).filter(
      (row): row is CoverKeyRow => row !== undefined,
    );
    const hasOwn = cover.has_own.length > 0;
    const offersThorough = hasOwn && cover.level !== "precise";
    return html`<section class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.values.title")}</h2>
        <p class="intro">${this.i18n.t("panel.detail.values.intro")}</p>
        <div class="rows">
          ${rows.map((row) => this._valueRow(cover, row))}
        </div>
      </section>
      <section class="card actions">
        ${wideButton({
          label: this.i18n.t("panel.detail.action.edit"),
          disabled: this._locked,
          onClick: () => this.actions.mode("edit"),
        })}
        ${wideButton({
          label: this.i18n.t("panel.detail.action.travel"),
          note: this.i18n.t("options.step.calibration_edit.data_description.height"),
          disabled: this._locked,
          onClick: () => this.actions.mode("travel"),
        })}
        ${wideButton({
          label: this.i18n.t("panel.detail.action.assign"),
          disabled: this._locked,
          onClick: this.actions.assign,
        })}
        ${cover.profile
          ? wideButton({
              label: this.i18n.t("panel.overview.group.open"),
              note: this.i18n.t("panel.overview.group.profile", { profile: cover.profile }),
              onClick: () => this.actions.openProfile(cover.profile as string),
            })
          : nothing}
        ${this._flowButton(
          "panel.detail.action.measure_again",
          "panel.detail.action.measure_again_note",
        )}
        ${hasOwn
          ? wideButton({
              label: this.i18n.t("panel.detail.action.correct"),
              note: this.i18n.t("panel.detail.action.correct_note"),
              onClick: () => this.actions.mode("correct"),
            })
          : nothing}
        ${offersThorough
          ? this._flowButton("panel.detail.action.thorough", "panel.detail.action.thorough_note")
          : nothing}
        ${hasOwn
          ? wideButton({
              label: this.i18n.t("panel.detail.action.remove"),
              destructive: true,
              disabled: this._locked,
              onClick: () => this.actions.mode("remove"),
            })
          : nothing}
      </section>`;
  }

  /**
   * One key: the number, and the sentence that says who said it.
   *
   * A window that measured this key for itself also shows what it would go back to,
   * because that is the whole question the user is asking when they look at an adjusted
   * shutter - which of these numbers are mine, and what is underneath them.
   */
  private _valueRow(cover: CoverRow, row: CoverKeyRow): TemplateResult {
    const from =
      row.origin === "own"
        ? this.i18n.t("panel.detail.source.own")
        : row.origin === "profile"
          ? this.i18n.t("panel.detail.source.profile", { profile: cover.profile ?? "" })
          : row.origin === "file"
            ? this.i18n.t("panel.detail.source.file")
            : this.i18n.t("panel.detail.source.default");
    return valueRow(
      this._label(row.key),
      this._number(row.key, row.value),
      this._unit(row.key),
      from,
      row.own && row.inherited_value !== null
        ? this.i18n.t("panel.detail.edit.inherits", {
            value: this._number(row.key, row.inherited_value),
          })
        : null,
    );
  }

  /** A button that ends in the options flow, with the one line that says it will. */
  private _flowButton(labelKey: string, noteKey: string): TemplateResult {
    return wideButton({
      label: `${this.i18n.t(labelKey)} ↗`,
      note: this.i18n.t(noteKey),
      title: this.i18n.t("panel.common.opens_configure"),
      onClick: (event: Event) => this.actions.openFlow(event.currentTarget as HTMLElement),
    });
  }

  // ------------------------------------------------------------------ the hand edit
  private _edit(keys: readonly CoverKeyRow[]): TemplateResult {
    const form = this.state.detail.form;
    const rows = DETAIL_KEYS.map((key) => keys.find((row) => row.key === key)).filter(
      (row): row is CoverKeyRow => row !== undefined,
    );
    const broken = rows.some((row) => valueProblem(row.key, form[row.key]) !== null);
    return html`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.edit.title")}</h2>
      <div class="warn">${this.i18n.t("panel.detail.edit.intro")}</div>
      <div class="fields">
        ${rows.map((row) => this._field(row))}
      </div>
      ${cardFoot(
        this.i18n.t("panel.common.action.cancel"),
        () => this.actions.mode("view"),
        html`<button class="cta compact" type="button" ?disabled=${this._locked || broken}
          @click=${this.actions.saveValues}>
          ${this.i18n.t("panel.detail.edit.action.save")}
        </button>`,
        this.state.applying,
      )}
    </section>`;
  }

  /**
   * One editable value.
   *
   * The placeholder is the whole contract of this form: an empty field is not a zero, it
   * is "nothing to say about this one", and what the window would then use is the number
   * the placeholder shows - `inherited_value`, answered by the server. A key with nothing
   * underneath it says so in words instead of showing a number nobody has.
   */
  private _field(row: CoverKeyRow): TemplateResult {
    const typed = this.state.detail.form[row.key];
    const problem = valueProblem(row.key, typed);
    const placeholder =
      row.inherited_value === null
        ? this.i18n.t("panel.detail.edit.empty")
        : this.i18n.t("panel.detail.edit.inherits", {
            value: this._number(row.key, row.inherited_value),
          });
    return numberField({
      label: this._label(row.key),
      value: typed ?? "",
      unit: this._unit(row.key),
      placeholder,
      error: problem ? this._problem(row.key, problem) : null,
      disabled: this.state.applying,
      onInput: (value) => this.actions.field(row.key, value),
    });
  }

  // --------------------------------------------------------------------- the travel
  /**
   * The one number on this screen whose consequences the panel may not work out.
   *
   * A travel is what a profile is scaled by, so changing it changes every value the
   * window inherits - and that is `derive_cover_from_profile`, which lives on the server
   * and is asked through `preview` with the typed travel in the item. The table is drawn
   * only when there is an answer to draw.
   */
  private _travel(cover: CoverRow): TemplateResult {
    const typed = this.state.detail.form.height;
    const problem = valueProblem("height", typed);
    const item = this.state.detail.preview;
    const rows =
      item && item.problem === null
        ? DETAIL_KEYS.filter(
            (key) => item.values[key] !== undefined && cover.values[key] !== undefined,
          )
        : [];
    return html`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this.i18n.t("options.step.calibration_edit.data.height")}
      </h2>
      <p class="intro">
        ${this.i18n.t("options.step.calibration_edit.data_description.height")}
      </p>
      ${numberField({
        label: this.i18n.t("panel.review.travel.label"),
        ariaLabel: this.i18n.t("panel.review.travel.aria"),
        value: typed ?? "",
        unit: this.i18n.t("panel.common.unit.centimetres"),
        placeholder: this.i18n.t("panel.review.travel.placeholder"),
        error: problem ? this._problem("height", problem) : null,
        disabled: this.state.applying,
        onInput: (value) => this.actions.field("height", value),
      })}
      ${item && item.problem !== null
        ? html`<p class="field-error">${this._problem("height", item.problem)}</p>`
        : nothing}
      ${rows.length > 0
        ? html`<table aria-busy=${this.state.detail.previewing ? "true" : "false"}>
            <thead>
              <tr>
                <th class="what"></th>
                <th>${this.i18n.t("panel.review.before")}</th>
                <th class="after">${this.i18n.t("panel.review.after")}</th>
              </tr>
            </thead>
            <tbody>
              ${rows.map(
                (key) => html`<tr>
                  <td class="what">${this._label(key)}</td>
                  <td>${this._number(key, cover.values[key])}</td>
                  <td class="after">
                    ${this._number(key, (item as PreviewItem).values[key])}
                  </td>
                </tr>`,
              )}
            </tbody>
          </table>`
        : nothing}
      ${cardFoot(
        this.i18n.t("panel.common.action.cancel"),
        () => this.actions.mode("view"),
        html`<button class="cta compact" type="button"
          ?disabled=${this._locked || problem !== null || isEmpty(typed)}
          @click=${this.actions.saveTravel}>
          ${this.i18n.t("panel.common.action.save")}
        </button>`,
        this.state.applying,
      )}
    </section>`;
  }

  // -------------------------------------------------------------------- "Correggi…"
  /**
   * The three scopes of the lexicon, each of which ends in the options flow.
   *
   * None of them can be preselected: the flow's `init` step is a menu and takes no
   * argument, so all three land the user in the same place. The intro says the dialog
   * opens; naming the path in the button is what tells them which of the three menu
   * entries to pick. Giving the flow an entry point that carries a scope is a 0.7.0 item.
   */
  private _correct(): TemplateResult {
    return html`<section class="card actions">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.action.correct")}</h2>
      <p class="intro">${this.i18n.t("panel.detail.correct.intro")}</p>
      ${this._flowButton("panel.detail.correct.times", "panel.detail.correct.times_note")}
      ${this._flowButton(
        "panel.detail.correct.times_rolls",
        "panel.detail.correct.times_rolls_note",
      )}
      ${this._flowButton("panel.detail.correct.thorough", "panel.detail.correct.thorough_note")}
      <div class="foot">
        <button class="cta text" type="button" @click=${() => this.actions.mode("view")}>
          ${this.i18n.t("panel.common.action.back")}
        </button>
      </div>
    </section>`;
  }

  // ------------------------------------------------------------- "Rimuovi la misura"
  /**
   * The confirmation, which names what the window will use afterwards.
   *
   * The destination is `cover_detail`'s `forget` block and not the keys' own
   * `inherited_origin`: the removal takes the whole record, so the assignment goes with
   * it and so does a travel nobody else states - and a window with no travel cannot be
   * brought a profile at all. The line about the travel is drawn only when the file
   * states it, because otherwise it is a promise about a number this write removes.
   */
  private _remove(cover: CoverRow): TemplateResult {
    const forget = this.state.detail.answer?.forget;
    return html`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.detail.remove.title")}</h2>
      <div class="danger">
        <p style="margin:0">
          ${this.i18n.t("panel.detail.remove.body", {
            cover: cover.name,
            destination: this._destination(),
          })}
        </p>
        ${forget?.travel_stays
          ? html`<p class="soft">${this.i18n.t("panel.detail.remove.travel_stays")}</p>`
          : nothing}
      </div>
      ${cardFoot(
        this.i18n.t("panel.common.action.cancel"),
        () => this.actions.mode("view"),
        html`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.detail.remove.action")}
        </button>`,
        this.state.applying,
      )}
    </section>`;
  }
}

if (!customElements.get("myhome-cover-detail")) {
  customElements.define("myhome-cover-detail", MyHomeCoverDetail);
}
