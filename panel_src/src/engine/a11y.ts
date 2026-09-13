// Saying out loud what the screen shows.
//
// The handoff (section 5) asks for `aria-live` announcements for drop outcomes, pending
// changes, applying and results, and for focus that moves to a panel when it opens and
// back to the control that opened it when it closes. The prototype kept an `announce`
// string in its state and rendered it into a polite region; that is what this file makes
// reusable, so lots 7 and 8 announce through one region instead of three.
//
// Two regions, not one, and the difference matters:
//
// * **polite** for everything the user caused and can see - a change withdrawn, an order
//   remembered. It waits for a pause in the screen reader's speech.
// * **status**, rendered visibly, for the measuring banner: it is not an announcement of
//   something that just happened but a standing condition of the whole page, and a user
//   arriving mid-session has to meet it rather than be told about it once.
//
// An assertive region is deliberately absent. Nothing this panel does is an emergency, and
// `alert` interrupts whatever the user was reading.

import { html, type TemplateResult } from "lit";

/** The polite live region. Rendered once, near the top of the panel, and never moved. */
export const liveRegion = (message: string): TemplateResult =>
  html`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${message}</div>`;

/**
 * Move focus somewhere, after Lit has painted it.
 *
 * `requestAnimationFrame` rather than `updateComplete`, because the caller usually wants
 * focus on an element it has just asked to exist and the two promises resolve in that
 * order anyway. A missing element is not an error: the screen changed under the request.
 */
export const focusWhenPainted = (find: () => HTMLElement | null | undefined): void => {
  requestAnimationFrame(() => {
    const element = find();
    if (element) {
      element.focus();
    }
  });
};

/**
 * Remember which control opened a panel, so it can be given focus back when the panel
 * closes. Losing focus to the top of the document is how a keyboard user loses their place.
 */
export class FocusReturn {
  private _source: HTMLElement | null = null;

  remember(source: EventTarget | null): void {
    this._source = source instanceof HTMLElement ? source : null;
  }

  restore(): void {
    const source = this._source;
    this._source = null;
    if (source && source.isConnected) {
      focusWhenPainted(() => source);
    }
  }
}
