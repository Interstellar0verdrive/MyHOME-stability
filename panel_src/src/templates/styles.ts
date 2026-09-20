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

  /*
   * A value the calibration did not move: the number once, and the word for it beside.
   * The word is what carries the meaning - a struck-through number repeated is not a
   * difference, it is two numbers in a row (live finding 23).
   */
  .summary-row .same {
    font-size: 12.5px;
    color: var(--myhome-text-soft);
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

  /* What is behind a disclosure, said under its button rather than inside its label. */
  .disclose-note {
    margin: 2px 0 0;
    font-size: 12.5px;
    line-height: 1.5;
    color: var(--myhome-text-soft);
  }

  .code-label {
    margin: 14px 0 6px;
    font-size: 12.5px;
    color: var(--myhome-text-soft);
  }

  /*
   * Where the calibration has got to (live finding 29, and PoC Stepper Lettura.dc.html).
   *
   * One nav with two appearances: below ~1150 px the list is shut behind the row that
   * says where the reader is, and above it the row is gone and the list is the left column.
   * The switch is the media query in engine/screen.ts; nothing here measures a width.
   *
   * **Every colour is a mixed ink, not the raw theme colour.** The states are told apart by
   * shape as well as by colour - a tick, a filled dot, an empty ring, a dashed ring, an
   * exclamation - because a state told only by colour is a state a reader with a colour
   * deficiency cannot read (WCAG 1.4.1). The inks are the ones tools/contrast.mjs
   * measures, which is why they are the inks and not --myhome-success itself.
   */
  .stepper {
    background: var(--myhome-card);
    border-bottom: 1px solid var(--myhome-divider);
    margin: -16px -16px 16px;
  }

  .stepper-toggle {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 48px;
    padding: 0 16px;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
    box-sizing: border-box;
  }

  .stepper-toggle .here {
    flex: 1;
    min-width: 0;
    font-size: 13.5px;
    font-weight: 500;
  }

  .dots {
    display: flex;
    align-items: center;
    gap: 5px;
    flex: 0 0 auto;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 4px;
    box-sizing: border-box;
    background: var(--myhome-success-ink);
  }

  .dot.current,
  .dot.error {
    width: 10px;
    height: 10px;
    border-radius: 5px;
  }

  .dot.current {
    background: var(--myhome-primary-ink);
  }

  .dot.error {
    background: var(--myhome-error-ink);
  }

  .dot.future {
    background: none;
    border: 2px solid var(--myhome-field-border);
  }

  .dot.skipped {
    background: none;
    border: 2px dashed var(--myhome-text-soft);
  }

  /* The chevron, drawn rather than written: a glyph here would be read out as a word. */
  .chevron {
    width: 24px;
    height: 24px;
    flex: 0 0 24px;
    position: relative;
  }

  .chevron::before {
    content: "";
    position: absolute;
    left: 6px;
    top: 8px;
    width: 9px;
    height: 9px;
    border-right: 2px solid var(--myhome-text);
    border-bottom: 2px solid var(--myhome-text);
    transform: rotate(45deg);
  }

  .chevron.open::before {
    top: 12px;
    transform: rotate(225deg);
  }

  .stepper-list {
    display: none;
    list-style: none;
    margin: 0;
    padding: 4px 16px 12px;
  }

  .stepper-list.open {
    display: block;
  }

  .step {
    margin: 0;
    padding: 0;
  }

  /*
   * The row itself, pressable or not, drawn the same way: the two differ in what they are,
   * never in what they look like, so a rail does not jump when a verb is offered.
   */
  .step-press,
  .step-still {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    width: 100%;
    box-sizing: border-box;
    padding: 5px 0;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
  }

  .step-press {
    min-height: 48px;
    align-items: center;
    cursor: pointer;
    border-radius: 8px;
    padding: 5px 8px;
    margin: 0 -8px;
  }

  .step-press:hover {
    background: var(--myhome-primary-faint);
  }

  /*
   * The mark: 24 px for a phase, 18 px for a stage inside it, both centred in a 24 px
   * column so the names line up whatever the row is. The connector the design draws between
   * marks is the left rule on the words, which costs no element per row.
   */
  .mark {
    width: 24px;
    height: 24px;
    flex: 0 0 24px;
    border-radius: 12px;
    box-sizing: border-box;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    font-weight: 700;
    line-height: 1;
    margin-top: 1px;
  }

  .step.sub .mark {
    width: 18px;
    height: 18px;
    flex: 0 0 18px;
    border-radius: 9px;
    margin-left: 3px;
    margin-right: 3px;
    font-size: 10px;
  }

  .mark.done {
    background: var(--myhome-success-pastel);
    color: var(--myhome-success-ink);
  }

  .mark.done::before {
    content: "✓";
  }

  .mark.current {
    background: var(--myhome-primary-ink);
  }

  .mark.future {
    border: 2px solid var(--myhome-field-border);
  }

  .mark.skipped {
    border: 2px dashed var(--myhome-text-soft);
    color: var(--myhome-text-soft);
  }

  .mark.skipped::before {
    content: "–";
  }

  .mark.error {
    background: var(--myhome-error-pastel);
    color: var(--myhome-error-ink);
  }

  .mark.error::before {
    content: "!";
  }

  .step .words {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0 6px;
  }

  .step .name {
    font-size: 13.5px;
    font-weight: 500;
    line-height: 1.35;
    color: var(--myhome-text);
  }

  .step.sub .name {
    font-size: 13px;
    font-weight: 400;
  }

  .step.current .name,
  .step.error .name {
    font-weight: 600;
  }

  .step.future .name,
  .step.skipped .name {
    color: var(--myhome-text-soft);
  }

  .step .meta {
    flex-basis: 100%;
    font-size: 12px;
    line-height: 1.4;
    color: var(--myhome-text-soft);
    font-variant-numeric: tabular-nums;
  }

  .step.error .meta {
    color: var(--myhome-error-ink);
  }

  /* The one mark that says "this can be done again", beside the name it belongs to. */
  .step .redo {
    color: var(--myhome-primary-ink);
    font-size: 14px;
    line-height: 1;
  }

  @media (min-width: 900px) {
    /* The strip spans the two columns, so it lines up with them and not with the page. */
    .read-only {
      margin: 0 auto;
      max-width: 1080px;
      width: calc(100% - 64px);
    }

    /* Inside the pane's own padding, so the row lines up with the columns under it. */
    .stepper {
      margin: -24px -32px 20px;
    }

    .stepper-toggle {
      padding: 0 32px;
    }

    .stepper-list {
      padding: 4px 32px 16px;
    }
  }

  @media (min-width: 1150px) {
    /* The column: no card, no rule under it, and the rows back to their own size. */
    .stepper-list {
      padding: 0;
    }

    .step-press {
      min-height: 44px;
    }

    /*
     * The strip takes the maximum the pane really has, once the rail has widened it.
     *
     * It says another device is driving, and it is drawn above the pane rather than inside
     * it: nothing lines the two up but this number. Lot W2 raised the pane from 1080 to
     * 1374 px wherever there is a rail beside the step, and for one commit the strip stayed
     * at 1080 - 68 px of overhang per side at 1280, 115 px at 1600. So it carries the same
     * marking the pane does and reads the same pair of numbers, and tools/session.mjs
     * measures the two against each other at both widths.
     */
    .read-only {
      max-width: 1374px;
    }

    .read-only.no-stepper {
      max-width: 1080px;
    }
  }
`;
