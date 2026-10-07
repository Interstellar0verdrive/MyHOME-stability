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
  // Q-27: in the table layouts the bar has no order control: only the chips count.
  const order = compact.getBoundingClientRect().width;
  const need = chips.getBoundingClientRect().width + (order > 0 ? BAR_GAP + order : 0);
  bar.classList.remove("is-measuring");
  bar.classList.toggle("is-chips", need <= room);
  bar.dataset.width = String(room);
}

export function fitBars(root) {
  for (const bar of root?.querySelectorAll?.(".cal-filterbar") || []) {
    fitBar(bar);
    if (typeof ResizeObserver !== "function" || watched.has(bar)) continue;
    // D-37: measured in the next frame, so a bar changing its own state never re-enters the observer's delivery
    // («ResizeObserver loop completed with undelivered notifications»).
    observer ||= new ResizeObserver((entries) => {
      const targets = entries.map((entry) => entry.target);
      (globalThis.requestAnimationFrame || ((callback) => setTimeout(callback, 16)))(() => {
        for (const target of targets) if (target.isConnected && String(target.clientWidth) !== target.dataset.width) fitBar(target);
      });
    });
    observer.observe(bar);
    watched.add(bar);
  }
}

/** D-40: the room the name of a wizard list's row keeps before its chips leave the side for under it. */
export const ROW_NAME_MIN = 200;

/**
 * D-40 (decided 8 Oct): A-01's and the sequence's rows follow the page cards' measured rule (Q-15) instead of a fixed
 * list width: the chips beside the name, side by side while the name keeps ROW_NAME_MIN px (`is-beside`), one under
 * the other while it still does (`is-beside is-stacked`), under the name otherwise. Measured again when a list's
 * width changes.
 */
export function fitRows(root) {
  for (const list of root?.querySelectorAll?.(".cal-batch-rows") || []) {
    for (const row of list.querySelectorAll(":scope > .cal-batch-row")) fitRow(row);
    if (typeof ResizeObserver !== "function" || rowsWatched.has(list)) continue;
    rowsObserver ||= new ResizeObserver((entries) => {
      const lists = entries.map((entry) => entry.target);
      (globalThis.requestAnimationFrame || ((callback) => setTimeout(callback, 16)))(() => {
        for (const target of lists) if (target.isConnected) for (const row of target.querySelectorAll(":scope > .cal-batch-row")) fitRow(row);
      });
    });
    rowsObserver.observe(list);
    rowsWatched.add(list);
  }
}
const rowsWatched = new WeakSet();
let rowsObserver = null;

function fitRow(row) {
  row.classList.remove("is-beside", "is-stacked");
  const lead = row.querySelector(".cal-batch-lead"), chips = [...row.querySelectorAll(".cal-batch-chips .badge, .cal-batch-chips .chip, .cal-batch-chips .muted")]
    .filter((chip) => chip.getClientRects().length);
  const view = row.ownerDocument.defaultView, style = view.getComputedStyle(row);
  const inner = row.clientWidth - (parseFloat(style.paddingLeft) || 0) - (parseFloat(style.paddingRight) || 0);
  if (!inner || !lead || !chips.length) return;
  const gap = parseFloat(style.columnGap) || 12, chipGap = 8;
  const widths = chips.map((chip) => chip.getBoundingClientRect().width);
  const room = inner - lead.getBoundingClientRect().width - 2 * gap;
  const together = widths.reduce((sum, width) => sum + width, 0) + chipGap * (widths.length - 1);
  if (room - together >= ROW_NAME_MIN) row.classList.add("is-beside");
  else if (room - Math.max(...widths) >= ROW_NAME_MIN) row.classList.add("is-beside", "is-stacked");
}

/**
 * U-1: in the one-column wizard (content under 700 px, a window of 720 px or more) the actions are a bar held at the
 * bottom of the window. Home Assistant scrolls the page on <html> while the panel grows with its content, so a sticky
 * bar never sticks: the bar is docked instead, `position: fixed` over the wizard's own width, whenever the wizard runs
 * past the window's bottom, and back in its place at the end of the wizard when that end is in view. The wizard keeps
 * the bar's height as padding meanwhile, so nothing moves. The stylesheet marks the layout with `--wiz-single: 1`.
 * D-02: with columns, the sequence's status and Start (`.cal-batch-sticky`, sticky at 76 px) are held the same way: moved
 * down their column by a transform so their top stays 16 px under the panel's bar (or the window's top), never past
 * the column's end. Where the sticky rule works the block is already there and nothing is added.
 * Returns the function that stops it.
 */
export function dockBar(wiz) {
  if (!wiz || typeof window === "undefined" || typeof window.addEventListener !== "function") return () => {};
  const view = wiz.ownerDocument.defaultView;
  let frame = 0;
  const update = () => {
    frame = 0;
    if (!wiz.isConnected) return;
    const bar = wiz.querySelector(":scope > .wiz-frame > .wiz-columns > .wiz-actions, :scope .wiz-columns > .wiz-actions");
    const single = view.getComputedStyle(wiz).getPropertyValue("--wiz-single").trim() === "1";
    const box = wiz.getBoundingClientRect(), height = view.innerHeight;
    const docked = wiz.classList.contains("is-docked");
    const barHeight = bar ? (docked ? bar.getBoundingClientRect().height : bar.offsetHeight) : 0;
    const dock = !!bar && single && box.height > 0 && box.bottom > height + 1 && box.top + barHeight + 80 < height;
    wiz.classList.toggle("is-docked", dock);
    if (dock) {
      wiz.style.setProperty("--dock-left", `${Math.round(box.left)}px`);
      wiz.style.setProperty("--dock-width", `${Math.round(box.width)}px`);
      wiz.style.setProperty("--dock-height", `${Math.round(barHeight)}px`);
    }
    hold(single);
  };
  const hold = (single) => {
    const block = wiz.querySelector(".cal-batch-sticky");
    if (!block) return;
    block.style.transform = "";
    if (single || view.getComputedStyle(block).position !== "sticky") return;
    const column = block.parentElement.getBoundingClientRect(), own = block.getBoundingClientRect();
    const topbar = wiz.getRootNode().querySelector?.(".topbar")?.getBoundingClientRect();
    const top = (topbar && topbar.bottom > 0 ? topbar.bottom : 0) + 16;
    const room = column.bottom - parseFloat(view.getComputedStyle(block.parentElement).paddingBottom || "0") - own.bottom;
    const shift = Math.min(top - own.top, room);
    if (shift > 0.5) block.style.transform = `translateY(${Math.round(shift)}px)`;
  };
  const schedule = () => { if (!frame) frame = (view.requestAnimationFrame || ((callback) => setTimeout(callback, 16)))(update); };
  view.addEventListener("scroll", schedule, { capture: true, passive: true });
  view.addEventListener("resize", schedule, { passive: true });
  const observer = typeof ResizeObserver === "function" ? new ResizeObserver(schedule) : null;
  observer?.observe(wiz);
  update();
  return () => {
    view.removeEventListener("scroll", schedule, { capture: true });
    view.removeEventListener("resize", schedule);
    observer?.disconnect();
    wiz.classList.remove("is-docked");
    const block = wiz.querySelector(".cal-batch-sticky");
    if (block) block.style.transform = "";
  };
}

