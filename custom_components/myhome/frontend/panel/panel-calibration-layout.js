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

/**
 * Q-22: the content width from which a card's header could lie on the blocks' three columns: its third column must
 * hold the widest profile chip (180 px, cut beyond), the widest action («Apri sessione», ~120 px at 14 px semibold with
 * its 14 px padding), ⋮ (40 px) and two 8 px gaps = 356 px; three such columns, two 32 px gaps and the card's 2 × 14 px
 * padding = 1160 px. That is past the cards' band (they end at 1015 px, `LIST_BANDS.tableFull`): the cards keep the
 * header [icon + texts][chips][action ⋮] at every width, and the table takes over from 1016 px.
 */
export const CARD_HEADER = { chip: 180, action: 120, menu: 40, gap: 8, columnGap: 32, padding: 14 };
export const CARD_HEADER_COLUMNS = 3 * (CARD_HEADER.chip + CARD_HEADER.action + CARD_HEADER.menu + 2 * CARD_HEADER.gap)
  + 2 * CARD_HEADER.columnGap + 2 * CARD_HEADER.padding;

/**
 * R-1: the wizard and the sequence by the tab's content width (`@container caltab`): three columns (stepper 240 · centre ·
 * actions clamp(240px, 30 %, 320px)) from 1000 px, the steps strip with centre and actions column from 700 px, one
 * column with the actions in a sticky bottom bar below. Window rules stay media queries: the phone (`PHONE`, under
 * 720 px, full screen, fixed bar whose actions keep 480 px centred from a 560 px bar) and the landscape phone (`SHORT`).
 */
export const WIZARD_BANDS = { threeColumns: 1000, intermediate: 700, wideBar: 560 };

/** The wizard's layout for a content width, given the window rules. */
export function wizardBand(width, { phone = false, short = false } = {}) {
  return short ? "landscape" : phone ? "phone" : width >= WIZARD_BANDS.threeColumns ? "three-columns" : width >= WIZARD_BANDS.intermediate ? "intermediate" : "single-column";
}

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
 * Q-24: the filter and order bar shows its chips (and «Ordina per» on the right) only when the chips on one line, the
 * order control and at least `BAR_GAP` px between them fit the bar's width; otherwise its two drop-downs. Measured, not
 * a container query: the chips' width depends on their labels and counts. Each bar is measured again when its width
 * changes (a ResizeObserver per bar).
 */
export const BAR_GAP = 16;
const watched = new WeakSet();
let observer = null;

function fitBar(bar) {
  const chips = bar.querySelector(".cal-tab-chips"), compact = bar.querySelector(".cal-tab-compact");
  const room = bar.clientWidth;
  if (!chips || !compact || !room) return;
  bar.classList.add("is-chips", "is-measuring");
  const need = chips.getBoundingClientRect().width + BAR_GAP + compact.getBoundingClientRect().width;
  bar.classList.remove("is-measuring");
  bar.classList.toggle("is-chips", need <= room);
  bar.dataset.width = String(room);
}

export function fitBars(root) {
  for (const bar of root?.querySelectorAll?.(".cal-filterbar") || []) {
    fitBar(bar);
    if (typeof ResizeObserver !== "function" || watched.has(bar)) continue;
    observer ||= new ResizeObserver((entries) => {
      for (const { target } of entries) if (target.isConnected && String(target.clientWidth) !== target.dataset.width) fitBar(target);
    });
    observer.observe(bar);
    watched.add(bar);
  }
}

