// `controllo` - a check with three outcomes, one of which asks for a number.
//
// It is `scelta` plus a field: the user says what they saw, and one of the answers ("it
// stopped short") needs the gap in centimetres before the step can go on. The options are
// the same buttons for the same reason, and the field appears under them rather than in a
// dialog, so that the answer and its measurement stay one thought.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderControllo = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const options = model.options ?? [];
  if (options.length === 0 && !model.field) {
    return html`<div class="stub">${context.i18n.t("panel.screen.not_in_this_version")}</div>`;
  }
  const field = model.field;
  return html`
    <div class="options" role="group" aria-label=${model.title}>
      ${options.map(
        (option) => html`<button
          class="option"
          type="button"
          aria-pressed=${option.current ? "true" : "false"}
          @click=${() => context.fire(option.action)}
        >
          <strong class="option-title">${option.title}</strong>
          ${option.meta ? html`<span class="option-meta">${option.meta}</span>` : nothing}
        </button>`,
      )}
    </div>
    ${field
      ? html`<div class="reading" style="margin-top:12px">
          <label for="gap">${field.label}</label>
          <div class="row">
            <input
              id="gap"
              inputmode="decimal"
              .value=${field.value}
              placeholder=${field.placeholder ?? ""}
              aria-describedby=${field.error ? "gap-error" : nothing}
              aria-invalid=${field.error ? "true" : "false"}
              @input=${(event: Event) =>
                context.fire("field", (event.target as HTMLInputElement).value)}
            />
            ${field.unit ? html`<span class="unit">${field.unit}</span>` : nothing}
          </div>
          ${field.error
            ? html`<p class="error" id="gap-error" role="alert">${field.error}</p>`
            : nothing}
        </div>`
      : nothing}
  `;
};
