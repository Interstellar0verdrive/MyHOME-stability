// `click` - a timed run: the shutter moves and the user presses when it reaches the place
// the step described.
//
// The big button never moves and never changes shape, only its words: start the shutter,
// "…" while the motor is starting, the press itself, "press registered". That is the whole
// point of a fixed footer, and it is why the button lives in the host and the state lives
// here. Everything below is what the step says about the motor - never what this panel
// worked out, because it is not the thing driving the motor.
//
// Two claims, from two sources, and they are deliberately not merged. "Motor" is the
// session's own: `movement.started_at` plus the seconds since, on the server's clock.
// "Estimated position" is the shutter's, out of `hass.states`, at about one hertz. A panel
// that averaged them would be inventing a third number nobody measured.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderClick = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const press = model.press;
  if (!press) {
    return nothing;
  }
  const moving = press.state === "moving";
  return html`
    ${press.instruction ? html`<p class="instruction">${press.instruction}</p>` : nothing}
    <div class="live">
      <div class="live-row">
        <span class="name">${context.i18n.t("panel.screen.motor")}</span>
        <span class="value ${moving ? "moving" : ""}">${press.motor ?? ""}</span>
      </div>
      ${press.position
        ? html`<div class="live-row">
            <span class="name">${context.i18n.t("panel.screen.position")}</span>
            <span class="value">${press.position}</span>
          </div>`
        : nothing}
    </div>
    ${press.note
      ? html`<div
          class="note ${press.state === "problem" ? "error" : "success"}"
          role=${press.state === "problem" ? "alert" : "status"}
        >
          ${press.note}
        </div>`
      : nothing}
  `;
};
