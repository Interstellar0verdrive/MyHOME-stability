/**
 * The calibration views' layout rules (responsive map), one source for the scripts; the stylesheet's media queries
 * spell the same conditions. The widths of the tab itself are container queries and need no script.
 */
/** A landscape phone: too short for the phone's stacked bars, whatever its width. */
export const SHORT = "(max-height: 499px) and (orientation: landscape)";
/** The phone layout: a window under 720 px that is not a landscape phone (details as a page, bottom action bar). */
export const PHONE = "(max-width: 719px) and (min-height: 500px), (max-width: 719px) and (orientation: portrait)";
/** The wizard and the sequence full screen: the phone, and the landscape phone with its own two-column layout. */
export const FULL_SCREEN = `(max-width: 719px), ${SHORT}`;
/** Dialogs as sheets from the bottom: a window under 720 px wide or under 500 px high; centred otherwise. */
export const SHEETS = "(max-width: 719px), (max-height: 499px)";

/**
 * Q-3: the Calibration list by the tab's content width (the stylesheet's `@container caltab` rules use the same
 * numbers): the table with its actions column, the table over three full-width columns, cards with the three detail
 * blocks in one row, cards with the blocks one under the other.
 */
export const LIST_BANDS = { table: 1200, tableFull: 1016, cardsRow: 700 };

/** The list's band for a content width (px). */
export function listBand(width) {
  return width >= LIST_BANDS.table ? "table" : width >= LIST_BANDS.tableFull ? "table-full" : width >= LIST_BANDS.cardsRow ? "cards-row" : "cards-stacked";
}

/** The content width of the tab (`caltab`'s inline size: the box without its padding), 0 when it is not laid out. */
export function contentWidth(host) {
  const width = host?.clientWidth || 0;
  if (!width) return 0;
  const style = host.ownerDocument.defaultView.getComputedStyle(host);
  return width - (parseFloat(style.paddingLeft) || 0) - (parseFloat(style.paddingRight) || 0);
}

const matches = (query) => typeof matchMedia === "function" && matchMedia(query).matches;
const still = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

export const layout = {
  phone: () => matches(PHONE),
  fullScreen: () => matches(FULL_SCREEN),
  sheets: () => matches(SHEETS),
  /** The full-screen views and the sheets slide in and out, unless motion is reduced. */
  slides: (query = FULL_SCREEN) => matches(query) && !still(),
};

/**
 * P-4: the line under a cover's name on a card shows the whole address («Stanza · Indirizzo: 86 · A: 8 · PL: 6») when
 * it fits on one line of the card's real width, the short «Indirizzo: 86» only when it does not. Measured on the line
 * itself (as wide as its column): A and PL shown, without wrapping, then compared with the room there is.
 */
export function fitLines(root) {
  for (const line of root?.querySelectorAll?.(".cal-row-name > .muted") || []) {
    if (!line.querySelector(".cal-row-address-ap")) continue;
    line.classList.add("is-full");
    const room = line.clientWidth;
    if (!room) continue;
    const wrap = line.style.whiteSpace;
    line.style.whiteSpace = "nowrap";
    const fits = line.scrollWidth <= room + 1;
    if (wrap) line.style.whiteSpace = wrap; else { line.style.removeProperty("white-space"); if (!line.getAttribute("style")) line.removeAttribute("style"); }
    if (!fits) line.classList.remove("is-full");
  }
}
