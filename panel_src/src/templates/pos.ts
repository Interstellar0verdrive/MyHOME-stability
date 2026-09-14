// `pos` - a positioning run: the shutter is moving to a place the step chose, and there is
// nothing for anybody to do but wait.
//
// It is the one template with no operative column, so the host lays it out as a single
// centred column at every width. No button: the step advances by itself when the movement
// ends, which is why the only controls here are a bar and a number of seconds. Both come
// from the model; 0.6.0 never produces one, because 0.6.0 never moves a shutter.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderPos = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const progress = model.progress;
  if (!progress) {
    return html`<div class="stub">${context.i18n.t("panel.screen.not_in_this_version")}</div>`;
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
