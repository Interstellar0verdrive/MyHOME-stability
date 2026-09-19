// `controllo` - a check with two or three outcomes, one of which asks for a number.
//
// It is `scelta` plus a field: the user says what they saw, and one of the answers ("it
// stopped short of the base") needs the gap in centimetres before the step can go on. The
// options are the same buttons for the same reason, and the field appears under them
// rather than in a dialog, so that the answer and its measurement stay one thought.
//
// The field here is the smaller one - 56 px at 26 px, against `metro`'s 64 at 32 - and
// that difference is the design's, not an oversight: `metro` is the step, and this is a
// detail somebody chose to add to an answer.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

/** The caption and the refusal, both, and in that order (as in `metro`). */
const describedBy = (field: NonNullable<ScreenModel["field"]>): string | undefined => {
  const ids = [field.hint ? "gap-hint" : "", field.error ? "gap-error" : ""].filter(
    (id) => id !== "",
  );
  return ids.length > 0 ? ids.join(" ") : undefined;
};

export const renderControllo = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const options = model.options ?? [];
  const field = model.field;
  if (options.length === 0 && !field) {
    return nothing;
  }
  return html`
    ${options.length > 0
      ? html`<div class="options" role="group" aria-label=${model.title}>
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
        </div>`
      : nothing}
    ${field
      ? html`<div class="reading" style="margin-top:12px">
          <label for="gap">${field.label}</label>
          <div class="row">
            <input
              id="gap"
              inputmode=${field.inputMode ?? "decimal"}
              .value=${field.value}
              placeholder=${field.placeholder ?? ""}
              aria-describedby=${describedBy(field) ?? nothing}
              aria-invalid=${field.error ? "true" : "false"}
              @input=${(event: Event) =>
                context.fire("field", (event.target as HTMLInputElement).value)}
            />
            ${field.unit ? html`<span class="unit">${field.unit}</span>` : nothing}
          </div>
          ${field.hint ? html`<p class="hint" id="gap-hint">${field.hint}</p>` : nothing}
          ${field.error
            ? html`<p class="error" id="gap-error" role="alert">${field.error}</p>`
            : nothing}
        </div>`
      : nothing}
  `;
};
