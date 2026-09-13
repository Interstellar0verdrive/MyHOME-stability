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

import { css, html, nothing, type TemplateResult } from "lit";

import {
  DECIMALS,
  MEASURABLE_KEYS,
  ROLL_KEYS,
  TABLE_KEYS,
  travelProblem,
} from "../engine/assign";
import { type I18n } from "../engine/i18n";
import { type PendingChange } from "../engine/store";
import { type CoverRow, type PreviewItem, type ProfileRow } from "../engine/ws";

export const reviewPanelStyles = css`
  .sheet-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    z-index: 50;
  }

  /* The phone: a sheet from the bottom, never taller than 86 vh. */
  .sheet {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    max-height: 86vh;
    background: var(--myhome-card);
    color: var(--myhome-text);
    z-index: 51;
    border-radius: 16px 16px 0 0;
    box-shadow: var(--myhome-shadow);
    display: flex;
    flex-direction: column;
  }

  /* From 600 px, a panel from the right instead. */
  @media (min-width: 600px) {
    .sheet {
      top: 0;
      left: auto;
      right: 0;
      bottom: 0;
      width: min(480px, 100vw);
      max-height: none;
      border-radius: 0;
    }
  }

  .sheet .head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--myhome-divider);
  }

  .sheet .head h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 500;
    flex: 1;
  }

  .sheet .head button {
    width: 48px;
    height: 48px;
    flex: 0 0 48px;
    border: none;
    background: transparent;
    color: var(--myhome-text-soft);
    font-size: 20px;
    cursor: pointer;
    border-radius: 24px;
  }

  .sheet .body {
    flex: 1;
    overflow: auto;
    padding: 16px;
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

  .sheet .item .route {
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
    border: 1px solid var(--myhome-divider);
    background: var(--myhome-card);
    color: inherit;
    padding: 0 10px;
    font: inherit;
    font-size: 14px;
    text-align: right;
  }

  .sheet label.travel input[aria-invalid="true"] {
    border-color: var(--myhome-error);
  }

  .sheet .field-error {
    margin: 2px 0 0;
    font-size: 12.5px;
    color: var(--myhome-error);
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
    color: var(--myhome-error);
    line-height: 1.5;
  }

  .sheet .show-all {
    border: none;
    background: transparent;
    color: var(--myhome-primary);
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
`;

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

  const label = (key: string): string =>
    i18n.t(`options.step.calibration_edit.data.${key}`);

  return html`
    <div class="sheet-backdrop" aria-hidden="true" @click=${context.onClose}></div>
    <aside
      class="sheet"
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-title"
      data-focus-root
    >
      <div class="head">
        <h2 id="review-title">${i18n.t("panel.review.title")}</h2>
        <button
          type="button"
          aria-label=${i18n.t("panel.common.action.close")}
          @click=${context.onClose}
        >
          ✕
        </button>
      </div>
      <div class="body">
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
              <span class="route">${context.route(cover)}</span>
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
                        <td>${i18n.number(cover.values[key], DECIMALS[key] ?? 1)}</td>
                        <td class="after">
                          ${i18n.number((item as PreviewItem).values[key], DECIMALS[key] ?? 1)}
                        </td>
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
    </aside>
  `;
};
