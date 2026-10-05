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

const matches = (query) => typeof matchMedia === "function" && matchMedia(query).matches;
const still = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

export const layout = {
  phone: () => matches(PHONE),
  fullScreen: () => matches(FULL_SCREEN),
  sheets: () => matches(SHEETS),
  /** The full-screen views and the sheets slide in and out, unless motion is reduced. */
  slides: (query = FULL_SCREEN) => matches(query) && !still(),
};
