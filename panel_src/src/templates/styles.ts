// The eight templates share one stylesheet because they share one shadow root.
//
// `<myhome-screen>` is the element; the templates are the functions it calls. That is a
// deliberate choice over eight custom elements: the responsive law is written once, in the
// host, and a template that needed its own element would have to be told the breakpoint
// again - which is how two columns become two answers. Everything here is sizes and colours
// transcribed from `Wizard Calibrazione.dc.html`, which is the specification.

import { css } from "lit";

export const templateStyles = css`
  .text-column {
    min-width: 0;
  }

  .phase {
    margin: 0 0 8px;
    font-size: 12px;
    color: var(--myhome-text-soft);
  }

  .new-text {
    display: inline-block;
    margin: 0 0 12px;
    background: var(--myhome-info-pastel);
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 12px;
    color: var(--myhome-text-soft);
  }

  .screen-title {
    margin: 0 0 12px;
    font-size: 20px;
    font-weight: 500;
    line-height: 1.3;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  /* The outcome screens carry one of four faces, in the pastel of what happened. */
  .outcome-icon {
    width: 32px;
    height: 32px;
    flex: 0 0 32px;
    border-radius: 16px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 600;
  }

  .outcome-icon.saved {
    background: var(--myhome-success-pastel);
    color: var(--myhome-success-ink);
  }

  .outcome-icon.saved::before {
    content: "✓";
  }

  .outcome-icon.cancelled {
    background: var(--myhome-error-pastel);
    color: var(--myhome-error-ink);
  }

  .outcome-icon.cancelled::before {
    content: "✕";
  }

  .outcome-icon.expired {
    background: var(--myhome-warning-pastel);
    color: var(--myhome-warning-ink);
  }

  .outcome-icon.expired::before {
    content: "⧗";
  }

  .outcome-icon.problem {
    background: var(--myhome-error-pastel);
    color: var(--myhome-error-ink);
  }

  .outcome-icon.problem::before {
    content: "!";
  }

  /*
   * The drawing is shown whole, at its own proportions, whatever the width of the column.
   *
   * It used to be a 230 px box with the picture as its background, which is a box that
   * decides the shape of what is inside it: every drawing taller than 230 px at the
   * column's width lost its top and its bottom, and three of them are (live findings 10,
   * 14 and 19 - the full ascent, the curtain travel and the reading at half way). An
   * image element with height auto takes its height from the picture instead of the other
   * way round, so there is nothing left to crop; max-height is a guard against a drawing
   * nobody has drawn yet filling the screen, and object-fit contain means that even then
   * the whole picture is inside the box. "npm run session" checks the five drawings that
   * exist against both widths: none of them reaches the guard, so each is drawn at
   * exactly its own proportions.
   */
  .drawing {
    display: block;
    width: 100%;
    height: auto;
    max-height: 520px;
    object-fit: contain;
    object-position: center;
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    margin: 0 0 16px;
    background-color: var(--myhome-drawing-paper);
  }

  .prose p {
    margin: 0 0 12px;
    font-size: 14.5px;
    line-height: 1.6;
    text-wrap: pretty;
  }

  .prose ul {
    margin: 0 0 12px;
    padding-left: 20px;
    font-size: 14.5px;
    line-height: 1.6;
  }

  .prose .md-image {
    display: block;
    max-width: 100%;
    border-radius: var(--myhome-radius);
    margin: 0 0 12px;
  }

  /*
   * The one big button, 64 px, in the same place on every step.
   *
   * **button.big and not .big.** The tape reading's card is class="reading big" -
   * "big" there means "the 64 px field of a measurement", a different thing with the same
   * word - and a bare .big reached it at equal specificity. .reading is declared after
   * and won back the background, the radius and the padding, but not the colour, so the
   * label, the number and the caret were painted --myhome-text-on-primary: white on a
   * white card, on every tape reading of every route. Naming the element is what keeps the
   * two meanings of the word apart.
   */
  button.big {
    width: 100%;
    min-height: 64px;
    border: none;
    border-radius: 16px;
    font: inherit;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    background: var(--myhome-primary);
    color: var(--myhome-text-on-primary);
    box-shadow: var(--myhome-shadow);
  }

  button.big.moving {
    background: var(--myhome-accent);
    color: var(--myhome-text-on-accent);
  }

  button.big[disabled] {
    background: var(--myhome-background-soft);
    color: var(--myhome-text-off);
    cursor: default;
    box-shadow: none;
  }

  .options {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 4px 0 0;
  }

  /*
   * A chosen option gains a border *and* an inset ring rather than a thicker border, so
   * that choosing one does not move the other two (handoff, section 2).
   */
  .option {
    text-align: left;
    border-radius: 10px;
    font: inherit;
    padding: 14px;
    min-height: 56px;
    cursor: pointer;
    color: inherit;
    border: 1px solid var(--myhome-field-border);
    background: var(--myhome-card);
  }

  .option[aria-pressed="true"] {
    border-color: var(--myhome-primary-ink);
    box-shadow: inset 0 0 0 1px var(--myhome-primary);
    background: var(--myhome-primary-faint);
  }

  .option .option-head {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .option .option-title {
    font-weight: 500;
    flex: 1;
    font-size: 14.5px;
    line-height: 1.4;
  }

  .option .option-meta {
    display: block;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    margin-top: 3px;
  }

  .live {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    font-size: 14px;
  }

  .live-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }

  .live-row .name {
    color: var(--myhome-text-soft);
  }

  .live-row .value {
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }

  /* A motor that is running says so in the warning colour, and keeps saying it. */
  .live-row .value.moving {
    color: var(--myhome-warning-ink);
    animation: myhome-pulse 1.2s ease-in-out infinite;
  }

  @keyframes myhome-pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.55;
    }
  }

  /* The small neutral chip an option can carry, beside its title. */
  .chip {
    font-size: 12px;
    border-radius: 10px;
    padding: 3px 9px;
    white-space: nowrap;
    background: var(--myhome-background-soft);
    color: var(--myhome-text-soft);
  }

  /*
   * …and the two the origin of a shutter's values is drawn in, which is the same
   * vocabulary components/origin-chip.ts uses on every row of the overview, for the
   * reason stated there: twenty per cent of a desaturated primary is grey by arithmetic,
   * so the fill carries a ring of the colour itself, and the accent pastel carries a dot
   * because two pastels of similar weight are not a distinction everybody can see.
   */
  .chip.measured {
    background: var(--myhome-primary-pastel);
    color: var(--myhome-text);
    box-shadow: inset 0 0 0 1px var(--myhome-primary);
  }

  .chip.adjusted {
    background: var(--myhome-accent-pastel);
    color: var(--myhome-text);
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .chip .dot {
    width: 6px;
    height: 6px;
    border-radius: 3px;
    background: var(--myhome-accent);
    display: inline-block;
  }

  .instruction {
    margin: 0 0 16px;
    font-size: 16.5px;
    line-height: 1.5;
    font-weight: 500;
  }

  .note {
    margin: 14px 0 0;
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 14px;
    line-height: 1.55;
  }

  .note.success {
    background: var(--myhome-success-pastel);
  }

  .note.error {
    background: var(--myhome-error-pastel);
  }

  .note.info {
    background: var(--myhome-info-pastel);
  }

  .progress-card {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 16px;
  }

  .progress-track {
    height: 8px;
    border-radius: 4px;
    background: var(--myhome-background-soft);
    overflow: hidden;
  }

  .progress-bar {
    height: 100%;
    background: var(--myhome-primary);
    border-radius: 4px;
    transition: width 0.1s linear;
  }

  .progress-eta {
    margin: 10px 0 0;
    font-size: 13px;
    color: var(--myhome-text-soft);
    font-variant-numeric: tabular-nums;
  }

  .reading {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 16px;
    margin: 4px 0 0;
  }

  .reading label {
    display: block;
    font-size: 13.5px;
    margin: 0 0 8px;
  }

  .reading .row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .reading input {
    flex: 1;
    min-width: 0;
    height: 56px;
    border-radius: 10px;
    border: 1px solid var(--myhome-field-border);
    background: var(--myhome-card);
    color: inherit;
    padding: 0 14px;
    font: inherit;
    font-size: 26px;
    font-variant-numeric: tabular-nums;
  }

  .reading.big input {
    height: 64px;
    font-size: 32px;
  }

  .reading .unit {
    font-size: 16px;
    color: var(--myhome-text-soft);
  }

  .reading.big .unit {
    font-size: 18px;
  }

  .reading .hint {
    margin: 8px 0 0;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
    line-height: 1.5;
  }

  .reading .error {
    margin: 8px 0 0;
    font-size: 12.5px;
    color: var(--myhome-error-ink);
    line-height: 1.5;
  }

  .summary {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 8px 16px;
    margin: 4px 0 14px;
  }

  .summary-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 9px 0;
    border-bottom: 1px solid var(--myhome-divider);
    font-size: 13.5px;
    flex-wrap: wrap;
  }

  .summary-row:last-of-type {
    border-bottom: none;
  }

  .summary-row .label {
    flex: 1 1 130px;
    color: var(--myhome-text-soft);
  }

  .summary-row .before {
    color: var(--myhome-text-soft);
    font-variant-numeric: tabular-nums;
    text-decoration: line-through;
    opacity: 0.7;
  }

  .summary-row .after {
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }

  .summary .note-line {
    margin: 10px 0;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
  }

  .code {
    background: var(--myhome-background-soft);
    border-radius: 8px;
    padding: 12px 14px;
    font-family: ui-monospace, Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-x: auto;
  }

  .stub {
    margin: 4px 0 0;
    background: var(--myhome-info-pastel);
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 13.5px;
    line-height: 1.55;
  }

  /* What the panel adds under a step's own prose: the numbers a check was made of. */
  .aside {
    margin: 0 0 12px;
    font-size: 13.5px;
    line-height: 1.55;
    color: var(--myhome-text-soft);
  }

  /*
   * The strip a screen wears while somebody else is driving. Above everything, because it
   * is the answer to "why is nothing here pressable" and a reader who meets it after the
   * step's prose has already tried.
   */
  .read-only {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin: 12px 16px 0;
    padding: 12px 14px;
    border-radius: 8px;
    background: var(--myhome-warning-pastel);
    font-size: 13.5px;
    line-height: 1.5;
  }

  /* The switch for the signal at the start, 44 px tall so a thumb can find it. */
  .cue {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 14px 2px 0;
    min-height: 44px;
    font-size: 13.5px;
    color: var(--myhome-text-soft);
    cursor: pointer;
  }

  .cue input {
    width: 20px;
    height: 20px;
    flex: 0 0 20px;
    accent-color: var(--myhome-primary);
  }

  /* The review's blocks: the side effects, and every shutter that follows the profile. */
  .summary-group {
    margin: 12px 0 0;
  }

  .summary-group > .group-title {
    margin: 0 0 4px;
    font-size: 13px;
    font-weight: 500;
  }

  .summary .line {
    margin: 10px 0 0;
    font-size: 12.5px;
    line-height: 1.55;
    color: var(--myhome-text-soft);
  }

  .disclose {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin: 12px 0 0;
  }

  .code-label {
    margin: 14px 0 6px;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
  }

  @media (min-width: 900px) {
    /* The strip spans the two columns, so it lines up with them and not with the page. */
    .read-only {
      margin: 0 auto;
      max-width: 1080px;
      width: calc(100% - 64px);
    }
  }
`;
