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
// * **assertive**, for the guided calibration and for nothing else. It was deliberately
//   absent while the panel only assigned profiles - nothing there is an emergency, and
//   `alert` interrupts whatever the user was reading. A shutter that has just started
//   moving is the exception the rule was waiting for: the whole step is a press timed to
//   an instant a second or two away, and a reader who is told about it politely, after the
//   step's prose, is told after the moment has gone (SPEC §5.7).

import { html, type TemplateResult } from "lit";

/** The polite live region. Rendered once, near the top of the panel, and never moved. */
export const liveRegion = (message: string): TemplateResult =>
  html`<div class="sr-only" role="status" aria-live="polite" aria-atomic="true">${message}</div>`;

/**
 * The assertive one: the motor starting, and a step that was abandoned.
 *
 * Two sentences on the whole panel may use it, and both are about a shutter that is moving
 * in the room the reader is standing in. Everything else goes through `liveRegion`.
 */
export const alertRegion = (message: string): TemplateResult =>
  html`<div class="sr-only" role="alert" aria-live="assertive" aria-atomic="true">${message}</div>`;

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
    const active = deepActiveElement(this._root.getRootNode() as unknown as DocumentOrShadowRoot);
    if (event.shiftKey && (active === first || active === this._root)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  };

  /**
   * Start trapping inside `root`.
   *
   * `focusFirst` is true for a panel whose first control is where a user should start -
   * the review sheet, "Quale profilo?" - and false for one whose contents move focus
   * themselves: the routed cards each take their own heading on the paint that first
   * draws it, and two things calling `focus()` in the same frame is a race whose winner
   * depends on which element updated first.
   */
  hold(root: HTMLElement, focusFirst = true): void {
    this.release();
    this._root = root;
    root.addEventListener("keydown", this._onKey);
    if (focusFirst) {
      focusWhenPainted(() => focusable(root)[0] ?? root);
    }
  }

  release(): void {
    this._root?.removeEventListener("keydown", this._onKey);
    this._root = null;
  }
}

/** What a Tab can land on: the rule the trap uses, and the one `npm run keyboard` walks. */
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]),' +
  ' textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Everything inside `root` a Tab can reach, in document order - **shadow roots included**.
 *
 * The panel's first two traps held plain markup, so `querySelectorAll` was the whole of
 * it. The drawer of the routed cards is not: its contents are `<myhome-cover-detail>` and
 * `<myhome-profile-card>`, each with a shadow root of its own, and a trap that could not
 * see into one would have found exactly one stop - the drawer's own close - and held the
 * keyboard on it while the card behind the glass stayed unreachable.
 *
 * The walk enters a host's shadow root at the host, which puts that content before any
 * light children of the same host. Nothing in this panel has both; a component that grew
 * a slot would want a real flattened-tree walk here.
 */
const focusable = (root: HTMLElement | ShadowRoot): HTMLElement[] => {
  const found: HTMLElement[] = [];
  const walk = (node: ParentNode): void => {
    for (const element of node.querySelectorAll<HTMLElement>("*")) {
      if (element.matches(FOCUSABLE)) {
        found.push(element);
      }
      if (element.shadowRoot) {
        walk(element.shadowRoot);
      }
    }
  };
  walk(root);
  return found.filter((element) => element.offsetParent !== null);
};

/**
 * The element that really has focus, however many shadow roots down it is.
 *
 * `activeElement` answers with the *host* of the root the focused element is in, so a
 * comparison against the last stop of a trap whose contents are a custom element would
 * always be false - and the keyboard would walk out of the panel at the end of it.
 */
export const deepActiveElement = (root: DocumentOrShadowRoot): Element | null => {
  let active = root.activeElement;
  while (active?.shadowRoot?.activeElement) {
    active = active.shadowRoot.activeElement;
  }
  return active;
};
