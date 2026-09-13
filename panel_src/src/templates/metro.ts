// `metro` - a tape reading: one number, large, with its unit outside the field.
//
// A 64 px field at 32 px type, `inputmode="decimal"` so a phone offers the right keyboard,
// and the expected value with its tolerance as a caption underneath. Errors go under the
// field, never in a dialog, and they are the flow's own reasons - `not_a_number`,
// `out_of_range`, `above_the_travel` - so one sentence serves both clients.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderMetro = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const field = model.field;
  if (!field) {
    return html`<div class="stub">${context.i18n.t("panel.screen.not_in_this_version")}</div>`;
  }
  return html`<div class="reading ${field.big === false ? "" : "big"}">
    <label for="reading">${field.label}</label>
    <div class="row">
      <input
        id="reading"
        inputmode="decimal"
        .value=${field.value}
        placeholder=${field.placeholder ?? ""}
        aria-describedby=${field.error ? "reading-error" : field.hint ? "reading-hint" : nothing}
        aria-invalid=${field.error ? "true" : "false"}
        @input=${(event: Event) => context.fire("field", (event.target as HTMLInputElement).value)}
      />
      ${field.unit ? html`<span class="unit">${field.unit}</span>` : nothing}
    </div>
    ${field.hint ? html`<p class="hint" id="reading-hint">${field.hint}</p>` : nothing}
    ${field.error
      ? html`<p class="error" id="reading-error" role="alert">${field.error}</p>`
      : nothing}
  </div>`;
};
