// "Rivedi e conferma" - the one screen between a gesture and a write.
//
// A side panel from the right at 600 px and up, a bottom sheet below it, and the same
// contents either way: the missing travels **first**, then one card per shutter with a
// before and an after, then one button that says how many assignments it is about to make.
//
// **Why the travels come first.** A profile is the measurement of one window with a certain
// travel, brought to the others in proportion, so a window whose travel nobody knows cannot
// be given one. The drop still succeeded - the design is explicit that it always does - and
// this form is where the consequence is collected, in one place, rather than as twelve
// separate refusals after the fact. Until every one of them is filled in, the confirm
// button says how many are missing instead of how many would be written.
//
// **Where the numbers come from.** `myhome/calibration/preview` (contract §11), which runs
// `resolve_cover` on the server with the hypothetical assignment. Not from arithmetic here:
// the prototype's `rescale` is a JavaScript re-implementation of `derive_cover_from_profile`
// and the two would drift, and a review screen that disagreed with the shutter about what
// it is going to do would be worse than no review screen at all.
//
// The rows a table can show are the three times; "mostra tutto" adds the two roll
// coefficients. The note under each card says what the change really means for that
// shutter - all its values are its own and nothing will change, some are and those stay,
// the profile is being brought to this travel, or the values are going back to the file or
// to the defaults - and which of those it is comes from the preview's own `origin`.

// The box itself - the backdrop, the panel from the right, the sheet from the bottom,
// the head and the scrolling body - is `components/sheet.ts`, which the routed cards'
// drawer is drawn in too. What is below is what goes *inside* this one, **and the frame
// travels with it**: `reviewPanelStyles` carries `sheetStyles`, because the rules only
// reach the shadow root that adopts them. When the frame moved to its own file, only the
// shell (`main.ts`) adopted it, while this panel is drawn inside `myhome-overview`'s root:
// the panel lost its backdrop, its fixed position and its round ✕, and landed at the
// bottom of the page as a plain block. A component whose markup needs a frame now
// brings it, whoever draws it.

import { css, html, nothing, type CSSResultGroup, type TemplateResult } from "lit";

import {
  DECIMALS,
  MEASURABLE_KEYS,
  ROLL_KEYS,
  TABLE_KEYS,
  travelProblem,
} from "../engine/assign";
import { UNIT_KEY, bareLabel, withUnit } from "../engine/fields";
import { type I18n } from "../engine/i18n";
import { type PendingChange } from "../engine/store";
import { type CoverRow, type PreviewItem, type ProfileRow } from "../engine/ws";
import { sheetStyles } from "./sheet";

export const reviewPanelStyles: CSSResultGroup = [sheetStyles, css`
  .sheet .body[aria-busy="true"] table,
  .sheet .body[aria-busy="true"] .note {
    opacity: 0.55;
    transition: opacity 120ms ease;
  }

  .sheet .intro {
    margin: 0 0 16px;
    font-size: 13.5px;
    color: var(--myhome-text-soft);
    line-height: 1.5;
  }

  .sheet .travel-note {
    background: var(--myhome-info-pastel);
    border-radius: 8px;
    padding: 12px;
    margin: 0 0 16px;
    font-size: 13.5px;
    line-height: 1.5;
  }

  .sheet .travel-note strong {
    font-weight: 500;
    display: block;
    margin-bottom: 4px;
  }

  .sheet .item {
    border: 1px solid var(--myhome-divider);
    border-radius: 8px;
    padding: 12px;
    margin: 0 0 12px;
  }

  .sheet .item .line {
    display: flex;
    align-items: baseline;
    gap: 8px;
    flex-wrap: wrap;
  }

  .sheet .item .name {
    font-weight: 500;
    flex: 1 1 auto;
    min-width: 0;
  }

  /*
   * Plain grey text, as the design draws it. It is not called "route": that is the
   * pending chip of the rows (cover-row.ts), whose dashed border and tinted ground are
   * adopted by the same shadow root and used to be drawn here too.
   */
  .sheet .item .item-route {
    font-size: 13px;
    color: var(--myhome-text-soft);
  }

  .sheet label.travel {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 10px 0 2px;
    font-size: 13.5px;
  }

  .sheet label.travel .what {
    flex: 1;
  }

  .sheet label.travel input {
    width: 96px;
    height: 44px;
    border-radius: 8px;
    border: 1px solid var(--myhome-field-border);
    background: var(--myhome-card);
    color: inherit;
    padding: 0 10px;
    font: inherit;
    font-size: 14px;
    text-align: right;
  }

  .sheet label.travel input[aria-invalid="true"] {
    border-color: var(--myhome-error-ink);
  }

  .sheet .field-error {
    margin: 2px 0 0;
    font-size: 12.5px;
    color: var(--myhome-error-ink);
    text-align: right;
  }

  .sheet table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 0;
    font-size: 13.5px;
  }

  .sheet th {
    font-weight: 400;
    color: var(--myhome-text-soft);
    padding: 4px 0;
    border-bottom: 1px solid var(--myhome-divider);
    text-align: right;
  }

  .sheet th.what {
    text-align: left;
  }

  .sheet th.after {
    font-weight: 500;
    color: var(--myhome-text);
  }

  .sheet td {
    padding: 5px 0;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .sheet td.what {
    text-align: left;
    color: var(--myhome-text-soft);
  }

  .sheet td.after {
    font-weight: 500;
  }

  .sheet .note {
    margin: 10px 0 0;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    line-height: 1.5;
  }

  .sheet .problem {
    margin: 10px 0 0;
    font-size: 12.5px;
    color: var(--myhome-error-ink);
    line-height: 1.5;
  }

  .sheet .show-all {
    border: none;
    background: transparent;
    color: var(--myhome-primary-ink);
    font: inherit;
    font-size: 13.5px;
    cursor: pointer;
    padding: 4px 0;
    min-height: 44px;
  }

  .sheet .refusal {
    background: var(--myhome-error-pastel);
    border-radius: 8px;
    padding: 12px;
    margin: 0 0 12px;
    font-size: 13.5px;
    line-height: 1.5;
  }

  .sheet .foot {
    padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px));
    border-top: 1px solid var(--myhome-divider);
    display: flex;
    gap: 12px;
    justify-content: flex-end;
  }

  .sheet .foot button {
    min-height: 44px;
    border: none;
    font: inherit;
    font-size: 14px;
    cursor: pointer;
  }

  .sheet .foot .back {
    padding: 0 16px;
    background: transparent;
    color: var(--myhome-text-soft);
  }

  .sheet .foot .confirm {
    padding: 0 24px;
    border-radius: 22px;
    background: var(--myhome-primary);
    color: var(--myhome-text-on-primary);
    font-weight: 500;
  }

  .sheet .foot .confirm[disabled] {
    background: var(--myhome-background-soft);
    color: var(--myhome-text-off);
    cursor: default;
  }
`];

export interface ReviewContext {
  i18n: I18n;
  pending: readonly PendingChange[];
  covers: ReadonlyMap<string, CoverRow>;
  profiles: ReadonlyMap<string, ProfileRow>;
  /** The server's answer to "what would this batch come to", or `null` while it has not. */
  preview: readonly PreviewItem[] | null;
  heights: Readonly<Record<string, string>>;
  /** Errors under the fields appear once the user has tried to confirm. */
  forced: boolean;
  showAll: boolean;
  /** A write is in flight: every control is inert and the button says so. */
  applying: boolean;
  /** A refused write, kept above the list with the pending changes still there. */
  refusal: string;
  /**
   * True while `preview` is in the air.
   *
   * It is drawn as `aria-busy` and half a step of opacity and **nothing else**: the answer
   * on the screen is still the answer to a question with one number changed in it, and
   * replacing it with a spinner would take the table away every time somebody typed a
   * digit. A reader is told the panel is still asking; a looker sees the numbers fade.
   */
  previewing: boolean;
  route: (cover: CoverRow) => string;
  onHeight: (cover: string, value: string) => void;
  onToggleShowAll: () => void;
  onConfirm: () => void;
  onClose: () => void;
}

/** The sentence under one card: what this change really means for this shutter. */
const noteFor = (
  i18n: I18n,
  cover: CoverRow,
  change: PendingChange,
  item: PreviewItem | undefined,
  profiles: ReadonlyMap<string, ProfileRow>,
): string => {
  if (MEASURABLE_KEYS.every((key) => cover.has_own.includes(key))) {
    return i18n.t("panel.review.note.all_own");
  }
  if (cover.has_own.length > 0) {
    return i18n.t("panel.review.note.some_own");
  }
  if (change.to === null) {
    // Which of the two it falls back to is the server's answer, not a guess from here.
    return item?.origin === "from_the_file"
      ? i18n.t("panel.review.note.back_to_file")
      : i18n.t("panel.review.note.back_to_defaults");
  }
  const profile = profiles.get(change.to);
  if (!item || item.height === null || !profile || profile.reference_height === null) {
    return "";
  }
  return i18n.t("panel.review.note.scaled", {
    profile: change.to,
    reference: i18n.number(profile.reference_height, 0),
    travel: i18n.number(item.height, 0),
  });
};

/** The refusal sentence for one row's own problem, in the words the API would use. */
const problemFor = (
  i18n: I18n,
  cover: CoverRow,
  problem: string,
  change: PendingChange,
): string =>
  i18n.refusal(problem, {
    cover: cover.name,
    covers: cover.name,
    count: 1,
    profile: change.to ?? "",
    key: i18n.t("panel.review.travel.label"),
    min: 20,
    max: 500,
  });

export const reviewPanel = (context: ReviewContext): TemplateResult => {
  const { i18n } = context;
  const byId = new Map((context.preview ?? []).map((item) => [item.cover_unique_id, item]));
  const items = context.pending
    .map((change) => ({ change, cover: context.covers.get(change.cover) }))
    .filter((row): row is { change: PendingChange; cover: CoverRow } => row.cover !== undefined);

  const missing = items.filter(
    ({ change, cover }) => change.to !== null && cover.height === null &&
      travelProblem(context.heights[change.cover]) !== null,
  ).length;

  const keys = context.showAll ? [...TABLE_KEYS, ...ROLL_KEYS] : TABLE_KEYS;

  // The form's label without its "(s)", and the unit with the number instead: "Tempo di
  // salita … 21,8 s", as the cover's card and the profile's say it (engine/fields.ts).
  const label = (key: string): string =>
    bareLabel(i18n.t(`options.step.calibration_edit.data.${key}`));
  const value = (key: string, number: number): string => {
    const unit = UNIT_KEY[key];
    return withUnit(i18n.number(number, DECIMALS[key] ?? 1), unit ? i18n.t(unit) : "");
  };

  return html`
    <!--
      While the batch is in the air every way out is inert, the backdrop and the ✕
      included: Escape is already guarded, and a panel that could be dismissed by a stray
      click on the dark half would take the refusal - and the pending changes it is about
      to show again - off the screen with it.
    -->
    <div
      class="sheet-backdrop"
      aria-hidden="true"
      @click=${() => {
        if (!context.applying) {
          context.onClose();
        }
      }}
    ></div>
    <!--
      A div and not an aside: an aside is a complementary landmark, and a landmark that
      also carries role="dialog" is an element claiming to be two things at once. The
      geometry is the sheet class either way.
    -->
    <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="review-title" data-focus-root>
      <div class="head">
        <h2 id="review-title">${i18n.t("panel.review.title")}</h2>
        <button
          type="button"
          aria-label=${i18n.t("panel.common.action.close")}
          ?disabled=${context.applying}
          @click=${context.onClose}
        >
          ✕
        </button>
      </div>
      <div class="body" aria-busy=${context.previewing ? "true" : "false"}>
        <p class="intro">${i18n.t("panel.review.intro")}</p>
        ${context.refusal
          ? html`<div class="refusal" role="alert">${context.refusal}</div>`
          : nothing}
        ${missing > 0
          ? html`<div class="travel-note">
              <strong>${i18n.t("panel.review.travel.title")}</strong>
              ${i18n.t("panel.review.travel.hint")}
            </div>`
          : nothing}
        ${items.map(({ change, cover }) => {
          const item = byId.get(change.cover);
          const typed = context.heights[change.cover];
          const needs = change.to !== null && cover.height === null;
          const problem = needs ? travelProblem(typed) : null;
          const showError = problem !== null && (context.forced || (typed ?? "") !== "");
          // The table is only drawn once there is an answer to draw: a preview that could
          // not be computed is a row waiting for its travel, not a row of blanks.
          const rows =
            item && item.problem === null
              ? keys.filter((key) => item.values[key] !== undefined && cover.values[key] !== undefined)
              : [];
          return html`<section class="item">
            <div class="line">
              <span class="name">${cover.name}</span>
              <span class="item-route">${context.route(cover)}</span>
            </div>
            ${needs
              ? html`<label class="travel">
                    <span class="what">${i18n.t("panel.review.travel.label")}</span>
                    <input
                      type="text"
                      inputmode="decimal"
                      .value=${typed ?? ""}
                      ?disabled=${context.applying}
                      aria-label=${i18n.t("panel.review.travel.aria")}
                      aria-invalid=${showError ? "true" : "false"}
                      placeholder=${i18n.t("panel.review.travel.placeholder")}
                      @input=${(event: Event) =>
                        context.onHeight(change.cover, (event.target as HTMLInputElement).value)}
                    />
                    <span>${i18n.t("panel.common.unit.centimetres")}</span>
                  </label>
                  ${showError
                    ? html`<p class="field-error">
                        ${problem === "missing_travel"
                          ? i18n.t("panel.review.travel.required")
                          : problemFor(i18n, cover, problem as string, change)}
                      </p>`
                    : nothing}`
              : nothing}
            ${item && item.problem !== null && item.problem !== "missing_travel"
              ? html`<p class="problem">
                  ${problemFor(i18n, cover, item.problem, change)}
                </p>`
              : nothing}
            ${rows.length > 0
              ? html`<table>
                  <thead>
                    <tr>
                      <th class="what"></th>
                      <th>${i18n.t("panel.review.before")}</th>
                      <th class="after">${i18n.t("panel.review.after")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${rows.map(
                      (key) => html`<tr>
                        <td class="what">${label(key)}</td>
                        <td>${value(key, cover.values[key])}</td>
                        <td class="after">${value(key, (item as PreviewItem).values[key])}</td>
                      </tr>`,
                    )}
                  </tbody>
                </table>`
              : nothing}
            ${(() => {
              const note = noteFor(i18n, cover, change, item, context.profiles);
              return note ? html`<p class="note">${note}</p>` : nothing;
            })()}
          </section>`;
        })}
        <button class="show-all" type="button" @click=${context.onToggleShowAll}>
          ${context.showAll
            ? i18n.t("panel.common.action.hide_all")
            : i18n.t("panel.common.action.show_all")}
        </button>
      </div>
      <div class="foot">
        <button class="back" type="button" ?disabled=${context.applying} @click=${context.onClose}>
          ${i18n.t("panel.review.action.back")}
        </button>
        <button
          class="confirm"
          type="button"
          ?disabled=${context.applying || (context.forced && missing > 0)}
          @click=${context.onConfirm}
        >
          ${context.applying
            ? i18n.t("panel.banner.applying.title")
            : missing > 0
              ? missing === 1
                ? i18n.t("panel.review.action.missing_travel_one")
                : i18n.t("panel.review.action.missing_travel", { count: missing })
              : items.length === 1
                ? i18n.t("panel.review.action.confirm_one")
                : i18n.t("panel.review.action.confirm", { count: items.length })}
        </button>
      </div>
    </div>
  `;
};
