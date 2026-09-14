// The five things that hover over the assignment screen, and never two of them at once.
//
// Each is anchored to the bottom of the viewport above `env(safe-area-inset-bottom)`, and
// each replaces the one below it in this order, which is the order of the gesture:
//
// 1. **the drop zone** - only while a row is in flight, because "Togli dal profilo" is a
//    destination and a destination that is always on screen is a button nobody reads;
// 2. **the armed strip** - only on the phone, while a shutter is waiting for a destination
//    to be tapped, with the way out beside it;
// 3. **the pending bar** - the count, "niente è ancora scritto", and the two ways on. It is
//    hidden during a flight and while the review panel is open, so it is never the thing
//    the user is dropping onto;
// 4. **the applying strip** - a write is in the air and the controls are disabled;
// 5. **the snack** - what was written, and "Annulla" for as long as the undo slot lasts.
//
// The two dark strips (armed, applying, snack) invert the theme's own colours rather than
// painting a grey: `--primary-text-color` on `--primary-background-color` is a pair the
// theme already guarantees the contrast of, in light and in dark alike, and the action word
// uses `--snack-action-color`, which is the one variable this project introduces for it.

import { css, html, nothing, type TemplateResult } from "lit";

import { type I18n } from "../engine/i18n";

export const stripStyles = css`
  .strip {
    position: fixed;
    left: 50%;
    bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    transform: translateX(-50%);
    max-width: 92vw;
    box-sizing: border-box;
    box-shadow: var(--myhome-shadow);
  }

  .drop-zone {
    z-index: 45;
    padding: 14px 28px;
    min-height: 48px;
    display: flex;
    align-items: center;
    border-radius: 24px;
    font-size: 14px;
    font-weight: 500;
    border: 2px dashed var(--myhome-divider);
    background: var(--myhome-card);
    color: var(--myhome-text-soft);
  }

  .drop-zone.over {
    border: 2px solid var(--myhome-primary-ink);
    color: var(--myhome-primary-ink);
  }

  .dark {
    background: var(--myhome-text);
    color: var(--myhome-background);
    border-radius: 8px;
    font-size: 14px;
  }

  /*
   * The armed strip used to sit 84 px up, where the pending bar would have been. Only one
   * strip is ever drawn at a time (the view returns the first that applies), so
   * that gap bought nothing - and on a short page, with every group collapsed to a 48 px
   * title, it landed on top of one of the targets the user is being asked to tap. It sits
   * where every other strip sits now, inside the 96 px the list already keeps clear.
   */
  .armed {
    z-index: 40;
    padding: 10px 16px;
    display: flex;
    gap: 16px;
    align-items: center;
  }

  .applying {
    z-index: 70;
    padding: 12px 20px;
  }

  .applying .under {
    display: block;
    font-size: 12px;
    opacity: 0.75;
    margin-top: 2px;
  }

  .snack {
    z-index: 70;
    padding: 8px 8px 8px 20px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .dark button {
    min-height: 44px;
    padding: 0 12px;
    border: none;
    background: transparent;
    color: var(--myhome-snack-action);
    font: inherit;
    font-weight: 500;
    cursor: pointer;
  }

  .pending-bar {
    z-index: 30;
    background: var(--myhome-card);
    border: 1px solid var(--myhome-divider);
    border-radius: 28px;
    padding: 8px 8px 8px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .pending-bar .count {
    font-size: 14px;
  }

  .pending-bar .locked {
    font-size: 13px;
    color: var(--myhome-warning-ink);
    flex-basis: 100%;
  }

  .pending-bar button {
    min-height: 44px;
    border: none;
    font: inherit;
    font-size: 14px;
    cursor: pointer;
  }

  .pending-bar .discard {
    padding: 0 12px;
    background: transparent;
    color: var(--myhome-text-soft);
  }

  .pending-bar .review {
    padding: 0 20px;
    border-radius: 22px;
    background: var(--myhome-primary);
    color: var(--myhome-text-on-primary);
    font-weight: 500;
  }

  .pending-bar button[disabled] {
    color: var(--myhome-text-off);
    background: var(--myhome-background-soft);
    cursor: default;
  }

  /*
   * On a phone the pill is the width of the screen instead of the width of its longest
   * line: centred and shrink-to-fit, the count wraps onto three short lines and the two
   * buttons end up under each other in a column narrower than the cards behind it.
   */
  @media (max-width: 599px) {
    .strip.pending-bar {
      left: 8px;
      right: 8px;
      transform: none;
      max-width: none;
      justify-content: space-between;
    }

    .strip.pending-bar .count {
      flex-basis: 100%;
    }
  }
`;

/** "Togli dal profilo — rilascia qui", which exists only while something is in flight. */
export const dropZone = (i18n: I18n, over: boolean): TemplateResult =>
  html`<div class="strip drop-zone ${over ? "over" : ""}" data-group="none">
    ${i18n.t("panel.assign.drop_zone")}
  </div>`;

export const armedStrip = (
  i18n: I18n,
  cover: string,
  onCancel: () => void,
): TemplateResult =>
  html`<div class="strip dark armed" role="status">
    <span>${i18n.t("panel.assign.armed", { cover })}</span>
    <button type="button" @click=${onCancel}>${i18n.t("panel.common.action.cancel")}</button>
  </div>`;

export interface PendingBarContext {
  i18n: I18n;
  count: number;
  /**
   * True while a measurement is running. The bar stays - the changes are still there and
   * throwing them away because somebody started measuring would be worse - but it says why
   * it cannot be confirmed, which is the rule "announced before, never an error after".
   */
  locked: boolean;
  lockedCover: string;
  onDiscard: () => void;
  onReview: () => void;
}

export const pendingBar = (context: PendingBarContext): TemplateResult => {
  const { i18n } = context;
  return html`<div class="strip pending-bar">
    <span class="count"
      >${context.count === 1
        ? i18n.t("panel.assign.pending.count_one")
        : i18n.t("panel.assign.pending.count", { count: context.count })}</span
    >
    <button class="discard" type="button" @click=${context.onDiscard}>
      ${i18n.t("panel.assign.action.discard_all")}
    </button>
    <button
      class="review"
      type="button"
      ?disabled=${context.locked}
      title=${i18n.t("panel.assign.action.review_hint")}
      @click=${context.onReview}
    >
      ${i18n.t("panel.assign.action.review")}
    </button>
    ${context.locked
      ? html`<span class="locked"
          >${i18n.t("panel.banner.measuring.body", { cover: context.lockedCover })}</span
        >`
      : nothing}
  </div>`;
};

export const applyingStrip = (i18n: I18n): TemplateResult =>
  html`<div class="strip dark applying" role="status">
    ${i18n.t("panel.banner.applying.title")}
    <span class="under">${i18n.t("panel.banner.applying.body")}</span>
  </div>`;

export const snackStrip = (
  i18n: I18n,
  message: string,
  onUndo: (() => void) | null,
): TemplateResult =>
  html`<div class="strip dark snack" role="status">
    <span>${message}</span>
    ${onUndo
      ? html`<button type="button" @click=${onUndo}>
          ${i18n.t("panel.toast.action.undo")}
        </button>`
      : nothing}
  </div>`;
