// What the panel draws while it is waiting for an answer.
//
// The rule from the handoff is that a slow network must not make the page jump: a reader
// on a phone tethered to a bad signal watched a one-line "Caricamento…" card, and then the
// whole screen appeared underneath it and pushed nothing where it had been looking. So the
// waiting state is the shape of the screen that is coming - a header, a filter row, two
// cards with rows in them - in the theme's own secondary background, at the measurements
// the real thing uses.
//
// **It is scenery, not content.** Every bar is `aria-hidden`; the one thing a screen reader
// is given is the sentence in the live region beside them, and `aria-busy` on the whole
// block. A skeleton read out bar by bar would be worse than the card it replaces.
//
// The shimmer is one `background-position` animation, and `themeStyles` already turns
// every animation in the panel down to nothing under `prefers-reduced-motion: reduce`, so
// a reader who asked for stillness gets flat blocks.

import { css, html, type TemplateResult } from "lit";
import { styleMap } from "lit/directives/style-map.js";

import { type I18n } from "../engine/i18n";

export const skeletonStyles = css`
  .sk {
    --sk-base: var(--myhome-background-soft);
  }

  .sk-bar {
    height: 12px;
    border-radius: 6px;
    background: linear-gradient(
      90deg,
      var(--sk-base) 25%,
      var(--myhome-card) 50%,
      var(--sk-base) 75%
    );
    background-size: 400% 100%;
    animation: sk-slide 1400ms linear infinite;
  }

  @keyframes sk-slide {
    from {
      background-position: 100% 0;
    }
    to {
      background-position: 0 0;
    }
  }

  .sk-intro {
    max-width: 72ch;
    margin: 8px 0 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .sk-controls {
    display: flex;
    gap: 12px;
    margin: 0 0 16px;
  }

  .sk-controls .sk-bar {
    height: 44px;
    border-radius: 8px;
  }

  .sk-groups {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  @media (min-width: 600px) {
    .sk-groups {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(300px, 1fr);
      align-items: start;
    }
  }

  .sk-group {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
  }

  .sk-head {
    padding: 16px 16px 12px;
    border-bottom: 1px solid var(--myhome-divider);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .sk-body {
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .sk-row {
    min-height: 48px;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    justify-content: center;
  }

  .sk-card {
    background: var(--myhome-card);
    border-radius: var(--myhome-radius);
    box-shadow: var(--myhome-shadow);
    padding: 16px;
    margin: 0 0 16px;
    max-width: 720px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
`;

// `styleMap` rather than a joined string, for the reason `engine/screen.ts` gives: a
// style attribute built by concatenation is a style attribute somebody can add a second
// declaration to. Nothing here comes from a server, and the rule holds anyway.
const bar = (width: string, height?: string): TemplateResult =>
  html`<div
    class="sk-bar"
    aria-hidden="true"
    style=${styleMap(height ? { width, height } : { width })}
  ></div>`;

const skeletonRow = (): TemplateResult =>
  html`<div class="sk-row">${bar("62%")}${bar("40%", "10px")}${bar("28%", "18px")}</div>`;

const skeletonGroup = (): TemplateResult =>
  html`<div class="sk-group">
    <div class="sk-head">${bar("45%", "16px")}${bar("80%", "10px")}${bar("60%", "10px")}</div>
    <div class="sk-body">${skeletonRow()}${skeletonRow()}${skeletonRow()}</div>
  </div>`;

/** The overview, before it has arrived: the intro, the filter row and two group cards. */
export const overviewSkeleton = (i18n: I18n): TemplateResult =>
  html`<div class="sk" role="status" aria-busy="true" aria-label=${i18n.t("panel.common.loading")}>
    <div class="sk-intro">${bar("92%", "14px")}${bar("74%", "14px")}${bar("36%", "12px")}</div>
    <div class="sk-controls">${bar("300px")}${bar("160px")}</div>
    <div class="sk-groups">${skeletonGroup()}${skeletonGroup()}</div>
  </div>`;

/** A routed card, before its second payload has arrived. */
export const cardSkeleton = (i18n: I18n): TemplateResult =>
  html`<div class="sk" role="status" aria-busy="true" aria-label=${i18n.t("panel.common.loading")}>
    <div class="sk-card">
      ${bar("40%", "16px")}${bar("70%", "10px")}${bar("100%")}${bar("100%")}${bar("55%")}
    </div>
    <div class="sk-card">${bar("35%", "16px")}${bar("100%", "44px")}${bar("100%", "44px")}</div>
  </div>`;
