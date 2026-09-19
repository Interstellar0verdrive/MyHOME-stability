// `pos` - a positioning run: the shutter is moving to a place the step chose, and there is
// nothing for anybody to do but wait.
//
// It is the one template with no operative column, so the host lays it out as a single
// centred column at every width. No big button: the step advances by itself when the
// movement ends, which is why the only things here are a sentence, a bar and a number of
// seconds. All three come from the model, and the bar is `planned_s` - a modelled
// duration, which the contract warns is read by nothing that measures. The one control
// the footer carries on these screens is "Stop the shutter", which is the `stop` verb and
// makes the step a problem it can be repeated from.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderPos = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const progress = model.progress;
  if (!progress) {
    return nothing;
  }
  const percent = Math.max(0, Math.min(1, progress.fraction)) * 100;
  return html`<div class="progress-card">
    ${progress.text ? html`<p class="instruction">${progress.text}</p>` : nothing}
    <div
      class="progress-track"
      role="progressbar"
      aria-label=${progress.text || context.i18n.t("panel.screen.progress")}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow=${Math.round(percent)}
    >
      <div class="progress-bar" style=${`width:${percent}%`}></div>
    </div>
    <p class="progress-eta" role="status">
      ${progress.done ? context.i18n.t("panel.screen.completed") : (progress.eta ?? "")}
    </p>
  </div>`;
};
