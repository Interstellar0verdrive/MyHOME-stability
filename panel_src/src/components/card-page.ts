// The shape both routed cards are cut from.
//
// `#/cover/<unique_id>` and `#/profile/<name>` are the same screen twice: a stack of cards
// on the page's own background, each with a heading, a paragraph of explanation, a column
// of label-and-number rows, a form of right-aligned decimal fields with their errors
// underneath, and a row of buttons at the foot. The prototype draws them as two panels and
// gives them identical measurements
// (`Prototipo Assegnazione.dc.html`, `detailOpen` / `profOpen`), so they are one
// stylesheet here rather than two that drift - and one stylesheet in the bundle rather
// than two copies of four kilobytes.
//
// Every colour is a theme variable through `engine/theme.ts`; there is not a literal one
// in this file, which is what makes the dark theme free.

import { css, html, nothing, type TemplateResult } from "lit";

export const cardPageStyles = css`

    :host {
      display: block;
    }

    .card {
      padding: 16px;
      margin: 0 0 16px;
      max-width: 720px;
    }

    h2 {
      margin: 0 0 4px;
      font-size: 16px;
      font-weight: 500;
    }

    h2:focus-visible {
      outline: 2px solid var(--myhome-primary-ink);
      outline-offset: 4px;
    }

    .sub {
      margin: 0;
      font-size: 13px;
      color: var(--myhome-text-soft);
    }

    .chips {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin: 12px 0 0;
    }

    .intro {
      margin: 0 0 12px;
      font-size: 13px;
      color: var(--myhome-text-soft);
      line-height: 1.5;
    }

    /*
     * A preview in the air: the numbers on the screen fade half a step and the region is
     * marked busy. Nothing is removed and nothing moves - the answer being replaced is
     * still the answer to almost the same question, and a table that vanished on every
     * keystroke would be worse than a slightly old one.
     */
    table[aria-busy="true"],
    .rows[aria-busy="true"] {
      opacity: 0.55;
      transition: opacity 120ms ease;
    }

    .rows {
      display: flex;
      flex-direction: column;
    }

    .row {
      display: flex;
      align-items: baseline;
      gap: 8px;
      padding: 8px 0;
      border-bottom: 1px solid var(--myhome-divider);
      font-size: 13.5px;
      flex-wrap: wrap;
    }

    .row .what {
      flex: 1 1 150px;
      color: var(--myhome-text-soft);
    }

    .row .value {
      font-variant-numeric: tabular-nums;
      font-weight: 500;
    }

    .row .from {
      flex-basis: 100%;
      font-size: 12px;
      color: var(--myhome-text-soft);
      text-align: right;
    }

    /* The inherited number beside an own one: what this key would go back to. */
    .row .instead {
      font-size: 12px;
      color: var(--myhome-text-soft);
      font-variant-numeric: tabular-nums;
    }

    h3 {
      margin: 16px 0 4px;
      font-size: 14px;
      font-weight: 500;
    }

    .actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    /* The wide, left-aligned buttons of the prototype: a label and a line under it. */
    .wide {
      min-height: 48px;
      border: none;
      border-radius: 8px;
      background: var(--myhome-primary-faint);
      color: var(--myhome-primary-ink);
      font: inherit;
      font-size: 14px;
      cursor: pointer;
      text-align: left;
      padding: 10px 14px;
      display: block;
      width: 100%;
    }

    .wide.destructive {
      background: var(--myhome-error-strong);
      color: var(--myhome-error-ink);
    }

    .wide[disabled] {
      background: var(--myhome-background-soft);
      color: var(--myhome-text-off);
      cursor: default;
    }

    .wide .note {
      display: block;
      color: var(--myhome-text-soft);
      font-size: 12.5px;
      margin-top: 2px;
    }

    .warn {
      background: var(--myhome-warning-pastel);
      border-radius: 8px;
      padding: 12px;
      margin: 0 0 16px;
      font-size: 13px;
      line-height: 1.5;
    }

    .warn strong {
      font-weight: 500;
      display: block;
      margin-bottom: 4px;
    }

    .danger {
      background: var(--myhome-error-pastel);
      border-radius: 8px;
      padding: 16px;
      font-size: 14px;
      line-height: 1.55;
    }

    .danger strong {
      font-weight: 500;
    }

    .danger p {
      margin: 8px 0 0;
    }

    .danger ul {
      margin: 4px 0 0;
      padding: 0 0 0 20px;
      line-height: 1.7;
    }

    .danger .soft {
      color: var(--myhome-text-soft);
      font-size: 13px;
    }

    .fields {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    label.field-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13.5px;
    }

    label.field-row .what {
      flex: 1;
    }

    label.field-row input {
      width: 110px;
      text-align: right;
    }

    label.field-row .unit {
      color: var(--myhome-text-soft);
      width: 24px;
    }

    .field[aria-invalid="true"] {
      border-color: var(--myhome-error-ink);
    }

    .field-error {
      margin: 2px 26px 0 0;
      font-size: 12.5px;
      color: var(--myhome-error-ink);
      text-align: right;
    }

    .foot {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      margin-top: 16px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0 0;
      font-size: 13.5px;
    }

    th {
      font-weight: 400;
      color: var(--myhome-text-soft);
      padding: 4px 0;
      border-bottom: 1px solid var(--myhome-divider);
      text-align: right;
    }

    th.what,
    td.what {
      text-align: left;
    }

    th.after {
      font-weight: 500;
      color: var(--myhome-text);
    }

    td {
      padding: 5px 0;
      text-align: right;
      font-variant-numeric: tabular-nums;
    }

    td.what {
      color: var(--myhome-text-soft);
    }

    td.after {
      font-weight: 500;
    }

    a {
      color: var(--myhome-primary-ink);
    }

    .refusal {
      background: var(--myhome-error-pastel);
      border-radius: 8px;
      padding: 12px;
      margin: 0 0 16px;
      font-size: 13.5px;
      line-height: 1.5;
    }
`;

// The four pieces both cards are built out of. Functions rather than elements: they are
// markup with no state, they live in the calling view's shadow root, and a custom element
// per row would be a second style boundary in the middle of a table.

/** A label, a number and where it came from - one line of "Valori in uso". */
export const valueRow = (
  label: string,
  value: string,
  unit: string,
  from: string,
  instead: string | null,
): TemplateResult => html`<div class="row">
  <span class="what">${label}</span>
  <span class="value">${value}${unit ? html` ${unit}` : nothing}</span>
  ${instead ? html`<span class="instead">${instead}</span>` : nothing}
  ${from ? html`<span class="from">${from}</span>` : nothing}
</div>`;

export interface NumberFieldOptions {
  label: string;
  value: string;
  unit: string;
  placeholder?: string;
  ariaLabel?: string;
  /** The rendered sentence for whatever is wrong, or `null`. The server's words. */
  error: string | null;
  disabled: boolean;
  onInput: (value: string) => void;
}

/**
 * One number typed by a person.
 *
 * A text box and not `<input type="number">`, for the reason the guided dialog gives in
 * `calibration_flow._text_field`: a number input's decimal separator is the browser's and
 * not the user's, so a shutter measured as `85,5` is refused outright by a browser running
 * in English with no message that says why. `inputmode="decimal"` still asks a phone for
 * the right keyboard.
 */
export const numberField = (options: NumberFieldOptions): TemplateResult => html`<div>
  <label class="field-row">
    <span class="what">${options.label}</span>
    <input
      class="field"
      type="text"
      inputmode="decimal"
      .value=${options.value}
      ?disabled=${options.disabled}
      placeholder=${options.placeholder ?? ""}
      aria-label=${options.ariaLabel ?? options.label}
      aria-invalid=${options.error ? "true" : "false"}
      @input=${(event: Event) => options.onInput((event.target as HTMLInputElement).value)}
    />
    <span class="unit">${options.unit}</span>
  </label>
  ${options.error ? html`<p class="field-error">${options.error}</p>` : nothing}
</div>`;

export interface WideButtonOptions {
  label: string;
  note?: string;
  title?: string;
  destructive?: boolean;
  disabled?: boolean;
  onClick: (event: Event) => void;
}

/** The prototype's wide, left-aligned button: a label and, under it, what it will do. */
export const wideButton = (options: WideButtonOptions): TemplateResult => html`<button
  class="wide ${options.destructive ? "destructive" : ""}"
  type="button"
  title=${options.title ?? ""}
  ?disabled=${options.disabled ?? false}
  @click=${options.onClick}
>
  ${options.label}
  ${options.note ? html`<span class="note">${options.note}</span>` : nothing}
</button>`;

/** Cancel on the left, the thing itself on the right - the shape of every foot here. */
export const cardFoot = (
  cancelLabel: string,
  onCancel: () => void,
  action: TemplateResult | typeof nothing,
  cancelDisabled = false,
): TemplateResult => html`<div class="foot">
  <button class="cta text" type="button" ?disabled=${cancelDisabled} @click=${onCancel}>
    ${cancelLabel}
  </button>
  ${action}
</div>`;
