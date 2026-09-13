// Using Home Assistant's own elements without depending on them.
//
// `ha-menu-button`, `ha-card`, `ha-textfield` and the rest are defined in the frontend's
// main document, which - because the panel is registered with `embed_iframe: false` -
// is the same document this element lives in. They are also **private API**: Home
// Assistant has renamed them before (`ha-app-layout` -> `ha-top-app-bar-fixed`,
// `paper-*` -> `ha-*`, mwc -> Material Web), and it will again.
//
// So the rule for this panel, from the plan: everything load-bearing is ours, and every
// `ha-*` goes through `defined()` with a rendered fallback beside it. A renamed element
// must cost chrome, never a screen.

import { type TemplateResult } from "lit";

/** True when the frontend has defined this element in the document the panel lives in. */
export const defined = (tag: string): boolean =>
  typeof customElements !== "undefined" && customElements.get(tag) !== undefined;

/**
 * `whenDefined(tag, theirs, ours)` - the Home Assistant element when it exists, our own
 * markup when it does not. Both branches are written at the call site, so the fallback
 * is visible to whoever reads the template rather than hidden in a helper.
 */
export const whenDefined = (
  tag: string,
  theirs: () => TemplateResult,
  ours: () => TemplateResult,
): TemplateResult => (defined(tag) ? theirs() : ours());

/**
 * Ask the frontend to open the sidebar. `ha-menu-button` fires this itself; our fallback
 * button has to, and it is the one gesture a phone user cannot do without.
 */
export const toggleSidebar = (source: HTMLElement): void => {
  source.dispatchEvent(
    new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }),
  );
};
