// `scelta` - a list of options, one of which is the current one.
//
// The wizard uses it for "which of the three paths?" and "which shutter?"; the panel uses
// it for "Quale profilo?", the confirmation step that the tap and the keyboard paths share
// with a drop. Every option is a button, so the keyboard reaches them in order with no
// roving tabindex, and the chosen one is announced by `aria-pressed` rather than by colour
// alone.

import { html, nothing, type TemplateResult } from "lit";

import type { ScreenContext, ScreenModel } from "../engine/screen";

export const renderScelta = (
  model: ScreenModel,
  context: ScreenContext,
): TemplateResult | typeof nothing => {
  const options = model.options ?? [];
  if (options.length === 0) {
    return nothing;
  }
  return html`<div class="options" role="group" aria-label=${model.title}>
    ${options.map(
      (option) => html`<button
        class="option"
        type="button"
        aria-pressed=${option.current ? "true" : "false"}
        @click=${() => context.fire(option.action)}
      >
        <span class="option-head">
          <strong class="option-title">${option.title}</strong>
          ${option.chip
            ? html`<span class="chip ${option.chipTone ?? "neutral"}"
                >${option.chipTone === "adjusted"
                  ? html`<span class="dot" aria-hidden="true"></span>`
                  : nothing}${option.chip}</span
              >`
            : nothing}
        </span>
        ${option.meta ? html`<span class="option-meta">${option.meta}</span>` : nothing}
      </button>`,
    )}
  </div>`;
};
