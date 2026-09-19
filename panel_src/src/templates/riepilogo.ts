// `riepilogo` - what was measured, against what the shutter uses today.
//
// Before is struck through and after is not, because the screen's question is "is this an
// improvement?" and two columns of similar numbers do not answer it.
//
// **Three rows, and everything else behind a press.** The maintainer's principle is that
// the position model stays behind the flow: the roll coefficients, the slat time, the
// values this calibration never measured but the save would change, and the configuration
// snippet are all one button away and none of them is in the reader's path. The rows that
// are hidden are **absent** rather than styled away, so that a screen reader is not read a
// block the screen says is shut.
//
// The YAML block is the same values as the file would write them: it is there for the
// person who keeps their configuration by hand, and it is shown, never applied.

import { html, nothing, type TemplateResult } from "lit";

import type {
  ScreenContext,
  ScreenModel,
  ScreenSummaryGroup,
  ScreenSummaryRow,
} from "../engine/screen";

/**
 * One row: what the value is called, what it is today, and what it would become.
 *
 * "Before" and "after" are said in words, inside the cell, and hidden from the screen -
 * where they used to be an `aria-label` on a `<span>`, which is an attribute ARIA does not
 * allow on an element with no role and which a browser is free to ignore. A struck-through
 * number with nothing naming it is two numbers in a row to anybody who cannot see the line
 * through the first one.
 */
const row = (one: ScreenSummaryRow, context: ScreenContext): TemplateResult => html`
  <div class="summary-row">
    <span class="label">${one.label}</span>
    ${one.before
      ? html`<span class="before"
          ><span class="sr-only">${context.i18n.t("panel.review.before")} </span>${one.before}</span
        >`
      : nothing}
    <span class="after"
      ><span class="sr-only">${context.i18n.t("panel.review.after")} </span>${one.after}</span
    >
  </div>
`;

const group = (one: ScreenSummaryGroup, context: ScreenContext): TemplateResult => html`
  <div class="summary-group">
    <p class="group-title">${one.title}</p>
    <div class="summary">${one.rows.map((each) => row(each, context))}</div>
  </div>
`;

export const renderRiepilogo = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const summary = model.summary;
  if (!summary) {
    return nothing;
  }
  return html`
    <div class="summary">
      ${summary.rows.map((one) => row(one, context))}
      ${(summary.more ?? []).map((one) => row(one, context))}
      ${(summary.lines ?? []).map((line) => html`<p class="line">${line}</p>`)}
      ${summary.note ? html`<p class="note-line">${summary.note}</p>` : nothing}
    </div>
    ${summary.sideEffects ? group(summary.sideEffects, context) : nothing}
    ${(summary.affected ?? []).map((one) => group(one, context))}
    ${summary.code
      ? html`${summary.codeLabel
            ? html`<p class="code-label">${summary.codeLabel}</p>`
            : nothing}<pre class="code">${summary.code}</pre>`
      : nothing}
    ${(summary.disclose ?? []).length > 0
      ? html`<div class="disclose">
          ${(summary.disclose ?? []).map(
            (one) => html`<button
              class="cta text"
              type="button"
              aria-expanded=${one.open ? "true" : "false"}
              data-disclose=${one.action}
              @click=${() => context.fire(one.action)}
            >
              ${one.label}
            </button>`,
          )}
        </div>`
      : nothing}
  `;
};
