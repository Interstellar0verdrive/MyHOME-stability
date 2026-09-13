// `esito` - how it ended, and what that means now.
//
// Four outcomes, each with its own pastel and its own face: saved, cancelled, expired,
// problem. The template itself is almost nothing - the icon is the host's, beside the
// title - and that is right: an outcome screen is a sentence and a way onward, and the
// sentence belongs to the texts. What it must never do is imply that something is still
// happening, which is why there is no live region and no spinner here.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderEsito = (
  model: ScreenModel,
  _context: ScreenContext,
): TemplateResult | typeof nothing => {
  if (!model.summary?.rows?.length) {
    return nothing;
  }
  // An outcome sometimes carries what was written, so that "saved" is checkable rather
  // than a claim.
  return html`<div class="summary">
    ${model.summary.rows.map(
      (row) => html`<div class="summary-row">
        <span class="label">${row.label}</span>
        <span class="after">${row.after}</span>
      </div>`,
    )}
    ${model.summary.note ? html`<p class="note-line">${model.summary.note}</p>` : nothing}
  </div>`;
};
