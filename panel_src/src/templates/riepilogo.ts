// `riepilogo` - what was measured, against what was there before.
//
// Before is struck through and after is not, because the screen's question is "is this an
// improvement?" and two columns of similar numbers do not answer it. The YAML block below
// is the same values as the file would write them: it is there for the person who keeps
// their configuration by hand, and it is shown, never applied.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderRiepilogo = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const summary = model.summary;
  if (!summary) {
    return html`<div class="stub">${context.i18n.t("panel.screen.not_in_this_version")}</div>`;
  }
  return html`
    <div class="summary">
      ${summary.rows.map(
        (row) => html`<div class="summary-row">
          <span class="label">${row.label}</span>
          ${row.before
            ? html`<span class="before" aria-label=${context.i18n.t("panel.review.before")}
                >${row.before}</span
              >`
            : nothing}
          <span class="after" aria-label=${context.i18n.t("panel.review.after")}>${row.after}</span>
        </div>`,
      )}
      ${summary.note ? html`<p class="note-line">${summary.note}</p>` : nothing}
    </div>
    ${summary.code ? html`<pre class="code">${summary.code}</pre>` : nothing}
  `;
};
