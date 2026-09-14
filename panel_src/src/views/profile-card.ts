// One profile: what it says, where it was measured, who follows it, and what changing it
// would do to them.
//
// `#/profile/<name>`. A screen of its own for the reason the cover detail is one - the
// plan routes it and a deep link has to render it - and the prototype's panel otherwise
// transcribed: the values, the followers with their state, the three things that can be
// done, and the live impact preview beside the fields.
//
// **Everything it draws comes out of `overview`**, which already carries every profile
// whole: the five numbers, the reference travel, the provenance and the two follower
// lists. There is no second read for this screen.
//
// **Except the impact preview**, which is the whole point of the editor and is the one
// thing on it the panel may not work out. "Everything changes for the windows that inherit
// and only the inherited values for the adjusted ones" is a claim about numbers, and the
// numbers are `derive_cover_from_profile`'s: asked through `myhome/calibration/preview`
// with `profile_values` - the typed numbers in the profile's place - and one item per
// follower carrying that follower's *current* assignment, so that nothing but the profile
// is hypothetical.
//
// **A profile of `cover_profiles:` is read-only here**, and says so rather than offering
// three buttons that would be refused: the file belongs to the user and this integration
// has never written it.

import { LitElement, html, nothing, type TemplateResult } from "lit";

import { focusWhenPainted } from "../engine/a11y";
import { DECIMALS, MEASURABLE_KEYS } from "../engine/assign";
import { FIELDS, UNIT_KEY, isEmpty, valueProblem } from "../engine/fields";
import { I18n } from "../engine/i18n";
import { initialState, type PanelState } from "../engine/store";
import { buttonStyles, cardStyles, fieldStyles, themeStyles } from "../engine/theme";
import { type CoverRow, type PreviewItem, type ProfileRow } from "../engine/ws";
import {
  cardFoot,
  cardPageStyles,
  numberField,
  valueRow,
  wideButton,
} from "../components/card-page";

/** The six a profile states: the travel it was measured at, then the five values. */
export const PROFILE_KEYS: readonly string[] = ["reference_height", ...MEASURABLE_KEYS];

/** The name a profile may have: it is also a key of the user's configuration file. */
const NAME_PATTERN = /^[A-Za-z0-9_]+$/;

export interface ProfileActions {
  back: () => void;
  openCover: (uniqueId: string) => void;
  mode: (mode: PanelState["profile"]["mode"]) => void;
  field: (key: string, value: string) => void;
  newName: (value: string) => void;
  saveValues: () => void;
  rename: () => void;
  remove: () => void;
}

export class MyHomeProfileCard extends LitElement {
  static override properties = {
    i18n: { attribute: false },
    state: { attribute: false },
    actions: { attribute: false },
  };

  declare i18n: I18n;
  declare state: PanelState;
  declare actions: ProfileActions;

  constructor() {
    super();
    this.i18n = new I18n();
    this.state = initialState({ view: "profile", params: {}, path: "/" });
    this.actions = {} as ProfileActions;
  }

  static override styles = [
    themeStyles,
    cardStyles,
    buttonStyles,
    fieldStyles,
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

  /** Escape steps back once: out of a form into the card, out of the card to the list. */
  private _onKey = (event: KeyboardEvent): void => {
    if (event.key !== "Escape" || this.state.applying) {
      return;
    }
    if (this.state.profile.mode !== "view") {
      this.actions.mode("view");
      return;
    }
    this.actions.back();
  };

  /**
   * Focus lands on the heading of whatever is now on the screen.
   *
   * Compared against what was *focused* rather than against the previous state: the card
   * paints before `overview` has arrived, and there is no heading to focus then. See the
   * same method in `cover-detail.ts`.
   */
  protected override updated(): void {
    const profile = this.state.profile;
    const screen = `${profile.for ?? ""}|${profile.mode}`;
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

  private get _profile(): ProfileRow | null {
    const name = this.state.profile.for;
    return this.state.overview?.profiles.find((row) => row.name === name) ?? null;
  }

  /** Every window that follows it, however it was told to, in the order the list has them. */
  private get _followers(): CoverRow[] {
    const profile = this._profile;
    const covers = this.state.overview?.covers ?? [];
    if (!profile) {
      return [];
    }
    const ids = new Set([...profile.followers, ...profile.followers_from_file]);
    return covers.filter((cover) => ids.has(cover.unique_id));
  }

  /**
   * The label of one field.
   *
   * The five values borrow the guided form's own words, which are already translated
   * everywhere and are the words the user met while measuring. The travel is the panel's
   * own, because the form's says "(cm)" and this screen prints the unit itself.
   */
  private _label(key: string): string {
    return key === "reference_height"
      ? this.i18n.t("panel.profile.reference_travel")
      : this.i18n.t(`options.step.profile_edit.data.${key}`);
  }

  private _unit(key: string): string {
    const unit = UNIT_KEY[key];
    return unit ? this.i18n.t(unit) : "";
  }

  private _number(key: string, value: number): string {
    return this.i18n.number(value, DECIMALS[key] ?? FIELDS[key]?.decimals ?? 1);
  }

  private _problem(key: string, problem: string): string {
    return this.i18n.refusal(problem, {
      key: this._label(key),
      min: FIELDS[key]?.min ?? 0,
      max: FIELDS[key]?.max ?? 0,
    });
  }

  /** The keys a window measured for itself, as a list of words a sentence can carry. */
  private _ownKeys(cover: CoverRow): string {
    return cover.has_own
      .map((key) => this.i18n.t(`options.step.calibration_edit.data.${key}`))
      .join(", ");
  }

  protected override render(): TemplateResult {
    const profile = this._profile;
    if (!this.state.overview) {
      return html`<div class="card" role="status">${this.i18n.t("panel.common.loading")}</div>`;
    }
    if (!profile) {
      return html`<div class="card">
        <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.unknown")}</h2>
        ${cardFoot(
          this.i18n.t("panel.common.action.back"),
          this.actions.back,
          nothing,
        )}
      </div>`;
    }
    const mode = this.state.profile.mode;
    return html`${this._head(profile)}
    ${this.state.writeError
      ? html`<div class="card refusal" role="alert">
          ${this.i18n.refusal(
            this.state.writeError.translation_key,
            this.state.writeError.translation_placeholders ?? {},
          )}
        </div>`
      : nothing}
    ${mode === "view" ? this._view(profile) : nothing}
    ${mode === "edit" ? this._edit() : nothing}
    ${mode === "rename" ? this._rename(profile) : nothing}
    ${mode === "delete" ? this._delete(profile) : nothing}`;
  }

  /**
   * Where this profile came from: the window it was measured on, the day, and - when that
   * window has since been moved - what it follows now.
   *
   * "Misurato su «X» · data · ora segue «Y»" is the sentence `measured_on` and
   * `measured_at` exist for, and the last clause is the one that matters: a profile whose
   * own reference window has been assigned somewhere else is a profile describing a kind
   * of shutter nothing in this house is measured against any more. Nothing is guessed: a
   * profile written before 0.6.0 or by hand says so.
   */
  private _head(profile: ProfileRow): TemplateResult {
    const covers = this.state.overview?.covers ?? [];
    const reference = covers.find((cover) => cover.unique_id === profile.measured_on);
    let provenance: string;
    if (profile.measured_on && profile.measured_on_name && profile.measured_at) {
      provenance = this.i18n.t("panel.profile.provenance", {
        cover: profile.measured_on_name,
        date: this.i18n.date(profile.measured_at),
      });
      if (reference && reference.profile !== profile.name) {
        provenance += ` · ${
          reference.profile
            ? this.i18n.t("panel.profile.provenance_now_profile", { profile: reference.profile })
            : this.i18n.t("panel.profile.provenance_now_none")
        }`;
      }
    } else if (profile.measured_on && profile.measured_at) {
      // The id names a window this gateway no longer has: the date is still true.
      provenance = this.i18n.t("panel.overview.group.measured_on_gone", {
        date: this.i18n.date(profile.measured_at),
      });
    } else {
      provenance = this.i18n.t("panel.profile.provenance_missing");
    }
    const kind = profile.editable
      ? this.i18n.t("panel.profile.stored")
      : this.i18n.t("panel.profile.from_file");
    return html`<section class="card">
      <p class="sub">${profile.missing ? provenance : `${kind} · ${provenance}`}</p>
      ${profile.missing
        ? html`<p class="warn" style="margin:12px 0 0">
            ${this.i18n.t("panel.overview.group.values_unknown")}
          </p>`
        : nothing}
    </section>`;
  }

  // -------------------------------------------------------------------------- the card
  private _view(profile: ProfileRow): TemplateResult {
    const followers = this._followers;
    return html`${profile.missing
        ? nothing
        : html`<section class="card">
            <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.values")}</h2>
            <div class="rows">
              ${PROFILE_KEYS.map((key) =>
                key === "reference_height"
                  ? profile.reference_height === null
                    ? nothing
                    : valueRow(
                        this._label(key),
                        this._number(key, profile.reference_height),
                        this._unit(key),
                        "",
                        null,
                      )
                  : profile.values[key] === undefined
                    ? nothing
                    : valueRow(
                        this._label(key),
                        this._number(key, profile.values[key]),
                        this._unit(key),
                        "",
                        null,
                      ),
              )}
            </div>
          </section>`}
      <section class="card">
        <h2 ?data-heading=${profile.missing} tabindex="-1">
          ${followers.length === 0
            ? this.i18n.t("panel.profile.followers.none")
            : followers.length === 1
              ? this.i18n.t("panel.profile.followers.count_one")
              : this.i18n.t("panel.profile.followers.count", { count: followers.length })}
        </h2>
        <p class="intro">${this.i18n.t("panel.profile.edit.intro")}</p>
        <div class="rows">
          ${followers.map((cover) => this._follower(cover))}
        </div>
      </section>
      ${profile.editable
        ? html`<section class="card actions">
            ${wideButton({
              label: this.i18n.t("panel.profile.action.edit"),
              disabled: this._locked,
              onClick: () => this.actions.mode("edit"),
            })}
            ${wideButton({
              label: this.i18n.t("panel.profile.action.rename"),
              disabled: this._locked,
              onClick: () => this.actions.mode("rename"),
            })}
            ${wideButton({
              label: this.i18n.t("panel.profile.action.delete"),
              destructive: true,
              disabled: this._locked,
              onClick: () => this.actions.mode("delete"),
            })}
          </section>`
        : nothing}`;
  }

  /** One follower: its name as a link to its own card, and what it inherits. */
  private _follower(cover: CoverRow): TemplateResult {
    const all = MEASURABLE_KEYS.every((key) => cover.has_own.includes(key));
    const note = all
      ? this.i18n.t("panel.profile.followers.measured")
      : cover.has_own.length > 0
        ? this.i18n.t("panel.profile.followers.adjusted", { keys: this._ownKeys(cover) })
        : this.i18n.t("panel.profile.followers.inherited");
    return html`<div class="row">
      <span class="what">
        <button
          class="cta text"
          type="button"
          style="padding:0;min-height:44px"
          @click=${() => this.actions.openCover(cover.unique_id)}
        >
          ${cover.name}
        </button>
      </span>
      <span class="instead">${note}</span>
      ${cover.profile_from_file
        ? html`<span class="from">${this.i18n.t("panel.overview.cover.from_file")}</span>`
        : nothing}
    </div>`;
  }

  // ------------------------------------------------------------------------- the editor
  private _edit(): TemplateResult {
    const followers = this._followers;
    const form = this.state.profile.form;
    const broken = PROFILE_KEYS.some(
      (key) => valueProblem(key, form[key]) !== null || isEmpty(form[key]),
    );
    const target =
      followers.length === 1
        ? this.i18n.t("panel.profile.edit.reach_one")
        : this.i18n.t("panel.profile.edit.reach_all", { count: followers.length });
    return html`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.action.edit")}</h2>
      <div class="warn">
        <strong>${this.i18n.t("panel.profile.edit.reach", { target })}</strong>
        ${this.i18n.t("panel.profile.edit.intro")}
      </div>
      <div class="fields">
        ${PROFILE_KEYS.map((key) =>
          numberField({
            label: this._label(key),
            value: form[key] ?? "",
            unit: this._unit(key),
            // An emptied field is a different sentence from a bad number, and it used
             // to be no sentence at all: Save went grey, the impact line said "correct
             // the fields", and nothing under the field said which one or why. On this
             // card every one of the six is required - a profile with a blank in it is
             // not a profile - unlike the detail card, where empty means "inherit".
            error: isEmpty(form[key])
              ? this.i18n.t("panel.common.required")
              : (() => {
                  const problem = valueProblem(key, form[key]);
                  return problem ? this._problem(key, problem) : null;
                })(),
            disabled: this.state.applying,
            onInput: (value) => this.actions.field(key, value),
          }),
        )}
      </div>
      <h3>${this.i18n.t("panel.profile.impact.title")}</h3>
      <div class="rows" aria-busy=${this.state.profile.impacting ? "true" : "false"}>
        ${followers.map((cover) => this._impact(cover, broken))}
      </div>
      ${cardFoot(
        this.i18n.t("panel.common.action.cancel"),
        () => this.actions.mode("view"),
        html`<button class="cta compact" type="button" ?disabled=${this._locked || broken}
          @click=${this.actions.saveValues}>
          ${followers.length === 1
            ? this.i18n.t("panel.profile.edit.action.save_one")
            : this.i18n.t("panel.profile.edit.action.save", { count: followers.length })}
        </button>`,
        this.state.applying,
      )}
    </section>`;
  }

  /**
   * What the typed numbers would mean for one follower.
   *
   * Before is what the window runs on now (`overview`); after is `preview`'s answer with
   * the typed numbers in the profile's place. Only the keys the window **inherits** are
   * listed, because those are the only ones that move - a value measured on the window
   * itself beats the profile, key by key, and the line says which of them stay.
   */
  private _impact(cover: CoverRow, broken: boolean): TemplateResult {
    const all = MEASURABLE_KEYS.every((key) => cover.has_own.includes(key));
    const state = all
      ? this.i18n.t("panel.profile.impact.state_measured")
      : cover.has_own.length > 0
        ? this.i18n.t("panel.profile.impact.state_adjusted")
        : this.i18n.t("panel.profile.impact.state_inherited");
    let line: string;
    if (all) {
      line = this.i18n.t("panel.profile.impact.no_change");
    } else if (cover.height === null) {
      line = this.i18n.t("panel.profile.impact.no_travel");
    } else if (broken) {
      line = this.i18n.t("panel.profile.impact.invalid");
    } else {
      const item = (this.state.profile.impact ?? []).find(
        (row: PreviewItem) => row.cover_unique_id === cover.unique_id,
      );
      if (!item || item.problem !== null) {
        line = this.i18n.t("panel.common.loading");
      } else {
        const moved = MEASURABLE_KEYS.filter(
          (key) =>
            !cover.has_own.includes(key) &&
            cover.values[key] !== undefined &&
            item.values[key] !== undefined,
        ).map(
          (key) =>
            `${this.i18n.t(`options.step.calibration_edit.data.${key}`)} ` +
            `${this._number(key, cover.values[key])} → ${this._number(key, item.values[key])}`,
        );
        line = moved.join(" · ");
        if (cover.has_own.length > 0) {
          const kept = this.i18n.t("panel.profile.impact.kept", { keys: this._ownKeys(cover) });
          line = line ? `${line} — ${kept}` : kept;
        }
      }
    }
    return html`<div class="row">
      <span class="what">${cover.name}</span>
      <span class="instead">${state}</span>
      <span class="from" style="text-align:left">${line}</span>
    </div>`;
  }

  // ------------------------------------------------------------------------- the rename
  /**
   * The rule comes first, because it is not the rule for a friendly name.
   *
   * A profile name is also a key of `myhome.yaml` - the user may move the profile into
   * their own file - so it is letters, digits and underscores and nothing else. The panel
   * checks that before it asks; the server checks it again, and it is the server that
   * knows whether the name is already taken.
   */
  private _rename(profile: ProfileRow): TemplateResult {
    const typed = this.state.profile.newName;
    const bad = typed.trim() !== "" && !NAME_PATTERN.test(typed.trim());
    const error = bad
      ? this.i18n.refusal("invalid_name", { profile: typed })
      : this.state.profile.nameError;
    return html`<section class="card">
      <h2 data-heading tabindex="-1">${this.i18n.t("panel.profile.rename.title")}</h2>
      <p class="intro">${this.i18n.t("panel.profile.rename.rule")}</p>
      <label class="field-row">
        <span class="what">${this.i18n.t("panel.profile.rename.field")}</span>
        <input
          class="field"
          type="text"
          style="width:220px;text-align:left"
          .value=${typed}
          ?disabled=${this.state.applying}
          aria-label=${this.i18n.t("panel.profile.rename.field")}
          aria-invalid=${error ? "true" : "false"}
          @input=${(event: Event) =>
            this.actions.newName((event.target as HTMLInputElement).value)}
        />
      </label>
      ${error ? html`<p class="field-error" style="text-align:left">${error}</p>` : nothing}
      ${cardFoot(
        this.i18n.t("panel.common.action.cancel"),
        () => this.actions.mode("view"),
        html`<button class="cta compact" type="button"
          ?disabled=${this._locked || bad || typed.trim() === "" || typed.trim() === profile.name}
          @click=${this.actions.rename}>
          ${this.i18n.t("panel.profile.rename.action")}
        </button>`,
        this.state.applying,
      )}
    </section>`;
  }

  // ------------------------------------------------------------------------- the delete
  /**
   * The confirmation names the windows, because that is the question being asked.
   *
   * They are read out of `overview` before the write, and where they land is the
   * profile's own answer: the values of the configuration file where those exist, and
   * otherwise the defaults. Their travels and their own values stay - the deletion takes
   * the profile and nothing that was measured on a window.
   */
  private _delete(profile: ProfileRow): TemplateResult {
    const followers = this._followers;
    return html`<section class="card">
      <h2 data-heading tabindex="-1">
        ${this.i18n.t("panel.profile.delete.title", { profile: profile.name })}
      </h2>
      <div class="danger">
        ${followers.length === 0
          ? html`<p style="margin:0">${this.i18n.t("panel.profile.followers.none")}</p>`
          : html`<p style="margin:0">${this.i18n.t("panel.profile.delete.affects")}</p>
              <ul>
                ${followers.map((cover) => html`<li>${cover.name}</li>`)}
              </ul>`}
        <p>${this.i18n.t("panel.profile.delete.body")}</p>
      </div>
      ${cardFoot(
        this.i18n.t("panel.common.action.cancel"),
        () => this.actions.mode("view"),
        html`<button class="cta compact destructive" type="button" ?disabled=${this._locked}
          @click=${this.actions.remove}>
          ${this.i18n.t("panel.profile.delete.action")}
        </button>`,
        this.state.applying,
      )}
    </section>`;
  }
}

if (!customElements.get("myhome-profile-card")) {
  customElements.define("myhome-profile-card", MyHomeProfileCard);
}
