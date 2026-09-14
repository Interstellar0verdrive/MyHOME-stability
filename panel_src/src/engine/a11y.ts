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

/**
 * Keep the keyboard inside one panel while it is open.
 *
 * The handoff (§5) asks for it on the review sheet and the "Quale profilo?" dialog, and
 * both are modal in the sense that matters: the screen behind them is still there, still
 * has focusable rows in it, and tabbing into it would leave the user editing a list they
 * cannot see the top of. There is no `inert` here on purpose - it is not in every browser
 * this integration supports, and a trap that works everywhere is worth more than a
 * property that works in most places.
 *
 * `Tab` is caught on the way down and wrapped at either end; everything else is left
 * alone, Escape included, which the view handles as a cancel like every other cancel.
 * A container with nothing focusable in it keeps focus on itself rather than throwing.
 */
export class FocusTrap {
  private _root: HTMLElement | null = null;
  private _onKey = (event: KeyboardEvent): void => {
    if (event.key !== "Tab" || !this._root) {
      return;
    }
    const stops = focusable(this._root);
    if (stops.length === 0) {
      event.preventDefault();
      this._root.focus();
      return;
    }
    const first = stops[0];
    const last = stops[stops.length - 1];
    // `activeElement` inside a shadow root is the host, so the root's own is what to ask.
    const active = (this._root.getRootNode() as unknown as DocumentOrShadowRoot).activeElement;
    if (event.shiftKey && (active === first || active === this._root)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  };

  /** Start trapping inside `root` and put focus on its first stop. */
  hold(root: HTMLElement): void {
    this.release();
    this._root = root;
    root.addEventListener("keydown", this._onKey);
    focusWhenPainted(() => focusable(root)[0] ?? root);
  }

  release(): void {
    this._root?.removeEventListener("keydown", this._onKey);
    this._root = null;
  }
}

/** Everything inside `root` a Tab can reach, in document order. */
const focusable = (root: HTMLElement): HTMLElement[] =>
  Array.from(
    root.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => element.offsetParent !== null || element === root);
