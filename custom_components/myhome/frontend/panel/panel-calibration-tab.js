/**
 * Hold the page still: `overflow: hidden` on `html`, `body` and every scrolling ancestor of `host` (through shadow roots);
 * the returned function puts their own values and scroll back (iOS may move the scroll when overflow changes).
 */
function holdScroll(host) {
  const held = [];
  const hold = (element) => { if (element?.style) { held.push([element, element.style.overflow, element.scrollTop]); element.style.overflow = "hidden"; } };
  hold(document.documentElement); hold(document.body);
  for (let node = host; node; node = node.parentElement || node.getRootNode?.().host) {
    if (node === document.documentElement || node === document.body) continue;
    if (/(auto|scroll)/.test(node.ownerDocument.defaultView.getComputedStyle(node).overflowY)) hold(node);
  }
  return () => { for (const [element, value, top] of held.reverse()) { element.style.overflow = value; if (element.scrollTop !== top) element.scrollTop = top; } };
}


/** WHO 2 "Calibration" view: what each timed cover uses, its measurement state and the ways to measure it. */
const asset = (name) => { const url = new URL(name, import.meta.url); url.search = new URL(import.meta.url).search; return url.href; };
const [{ escapeHtml: esc }, model, text, { CoverCalibration }, { CalibrationWizard }, { ProfileCatalogueEditor }, { morph }, { layout, SHEETS, fitLines, listBand, contentWidth }] = await Promise.all([
  import(asset("panel-dom.js")), import(asset("panel-model.js")), import(asset("panel-calibration-text.js")),
  import(asset("panel-cover-calibration.js")), import(asset("panel-calibration-wizard.js")), import(asset("panel-profile-catalogue-editor.js")),
  import(asset("panel-calibration-morph.js")), import(asset("panel-calibration-layout.js")),
]);
const { fill, rich, number, dateText, names, followedBy } = text;

const MEASURED = ["guided", "automatic"];
export const FILTERS = ["all", "to_measure", "calibrated", "profile"];
// Covers read in turn to find the gateway's session when a read fails.
const SESSION_PROBES = 3;
export const SORT_KEYS = ["cover", "status", "profile"];
/** The Assign profile dialog's "No profile" entry (a profile id is never this). */
const NO_PROFILE = "__no_profile__";
export const DEFAULT_SORT = Object.freeze({ key: "cover", dir: "asc" });
export const SORT_STORAGE_KEY = "myhome-panel-calibration-sort-v1";
// Status from what needs attention first; a running cover is always on top, whatever the order.
const STATUS_RANK = { to_measure: 0, times: 1, rolls: 2, verified: 3 };

function savedSort() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(SORT_STORAGE_KEY));
    if (SORT_KEYS.includes(saved?.key) && ["asc", "desc"].includes(saved?.dir)) return { key: saved.key, dir: saved.dir };
  } catch { /* The default order applies when browser storage is blocked. */ }
  return { ...DEFAULT_SORT };
}

/** What a cover uses, read from the backend view; nothing is estimated in the browser. */
export function coverStatus(cover) {
  const effective = cover.effective || {};
  const evidence = ["opening", "closing"].map((direction) => effective[direction]?.provenance).filter(Boolean);
  const measured = evidence.filter((item) => MEASURED.includes(item.source));
  const rolls = effective.opening_roll?.value != null && effective.closing_roll?.value != null;
  const dates = [...measured, ...["slat_time_s", "opening_roll", "closing_roll"].map((key) => effective[key]?.provenance)]
    .map((item) => item?.recorded_at).filter((value) => value && !Number.isNaN(Date.parse(value))).sort();
  const latest = [...measured].sort((a, b) => String(b.recorded_at).localeCompare(String(a.recorded_at)))[0] || null;
  return {
    status: rolls ? "rolls" : measured.length ? "times" : "to_measure",
    rolls, last: dates.at(-1) || null, method: latest ? (latest.inherited ? "inherited" : latest.source) : null,
    origin: latest?.inherited ? latest.origin_name || latest.origin_entity_id : null,
  };
}

/** Covers this view can measure: timed covers, never those with a position sensor (no resolved timings). */
export function timedCovers(data) {
  return (data?.covers || []).filter((cover) => cover.effective && !cover.advanced);
}

export class CalibrationTab {
  constructor() {
    this._generation = 0; this._rows = new Map(); this._unsubs = []; this._expanded = new Set(); this._page = null;
    this._filter = "all"; this._sort = savedSort(); this._menu = null; this._mode = { kind: "list" }; this._hosts = new WeakSet();
    this._calibration = new CoverCalibration();
    this._wizard = new CalibrationWizard();
  }

  /**
   * While the wizard or the sequence view is shown, the page does not bounce or pull to refresh at its top (Safari's
   * pull-to-refresh reloads Home Assistant and drops the wizard without asking: iOS never shows `beforeunload`). The
   * previous values come back as soon as the list is shown again.
   */
  get _mode() { return this.__mode; }
  set _mode(mode) {
    this.__mode = mode;
    // The phone's details page belongs to the list: a wizard, a sequence or a session closes it.
    // The details page it closed comes back when the list does (`_backToList`).
    if (mode?.kind !== "list") { if (this._page) this._pageReturn = this._page; this._page = null; }
    this._syncHold();
  }

  /**
   * The views over the page hold it: the wizard and the sequence (always no pull-to-refresh; held still when full
   * screen, M4-4) and the phone's details page (P-5: held still too, only its body scrolls).
   */
  _syncHold() {
    const mode = this.__mode;
    const full = mode?.kind === "wizard" || mode?.kind === "batch", page = mode?.kind === "list" && !!this._page;
    const hold = full || page, roots = [document.documentElement, document.body].filter(Boolean);
    if (hold && !this._overscroll) {
      this._overscroll = roots.map((element) => [element, element.style.overscrollBehaviorY]);
      for (const element of roots) element.style.overscrollBehaviorY = "none";
    } else if (!hold && this._overscroll) {
      for (const [element, value] of this._overscroll) element.style.overscrollBehaviorY = value;
      this._overscroll = null;
    }
    // M4-4: the full-screen wizard (a phone, or a landscape phone: the stylesheet's rule) holds the page under it still;
    // only its content area scrolls. Elsewhere the wizard sits in the page. The details page exists only on the phone.
    const still = (full && layout.fullScreen()) || page;
    if (still && this._context?.host && !this._fullHold) this._fullHold = holdScroll(this._context.host);
    else if (!still && this._fullHold) { this._fullHold(); this._fullHold = null; }
  }

  /** Replace the wizard (tests use a faster preview); `null` leaves only sessions and groups. */
  useWizard(wizard) { this._wizard?.close(); this._wizard = wizard; }

  clear() {
    this._context?.setBeforeLeave?.(null);
    this._catalogue?.close();
    this._generation++;
    this._closeDialog();
    for (const unsubscribe of this._unsubs.splice(0)) Promise.resolve(unsubscribe()).catch(() => {});
    this._calibration.close();
    this._wizard?.close();
    this._rows.clear();
    this._page = null;
    this._pageReturn = null;
    this._mode = { kind: "list" };
    this._batch = null;
    this._menu = null;
    this._context = null;
    this._key = null;
  }

  show(context) {
    const key = JSON.stringify(context.gateways.map((entry) => entry.entry_id).sort());
    const changed = key !== this._key || context.hass.connection !== this._context?.hass.connection;
    if (changed) this.clear();
    if (!changed && this._context && this._context.host !== context.host) {
      // A rebuilt shell gives a new element: whatever the old one showed is closed, as on any exit.
      this._calibration.close();
      this._wizard?.close();
      this._mode = { kind: "list" };
    }
    this._context = context;
    this._key = key;
    // The tab's notes follow Home Assistant's dark mode like the wizard does; without theme data, the system's preference.
    const darkMode = context.hass?.themes?.darkMode;
    context.host.dataset.theme = (typeof darkMode === "boolean" ? darkMode : !!globalThis.matchMedia?.("(prefers-color-scheme: dark)")?.matches) ? "dark" : "light";
    // Leaving the tab with a live calibration open asks first (the wizard's "Calibration in progress").
    context.setBeforeLeave?.(() => (this._mode.kind === "wizard" ? this._wizard?.beforeLeave?.() : null) || null);
    if (!this._hosts.has(context.host)) {
      this._hosts.add(context.host);
      context.host.addEventListener("click", (event) => this._click(event));
      context.host.addEventListener("keydown", (event) => this._keydown(event));
      context.host.addEventListener("change", (event) => this._change(event));
      // P-4: a new width measures the lines under the names again (whole address when it fits).
      if (typeof ResizeObserver === "function") {
        const host = context.host;
        let width = 0;
        new ResizeObserver(([entry]) => {
          const now = Math.round(entry.contentRect.width);
          if (now !== width) { width = now; this._band(); fitLines(host); }
        }).observe(host);
      }
    }
    if (changed) {
      const generation = this._generation;
      for (const entry of context.gateways) this._rows.set(entry.entry_id, { loading: false, data: null, session: null, error: false, again: false });
      for (const entry of context.gateways) {
        this._subscribe(entry.entry_id, generation);
        this._read(entry.entry_id, generation);
      }
    }
    this._render();
  }

  updateHass(hass) {
    if (!this._context) return;
    this._context.hass = hass;
    this._wizard?.updateHass?.(hass);
  }

  /** Session state is transient (no revision): the panel's periodic refresh reads it again. */
  refresh() {
    if (!this._context || document.hidden) return;
    for (const entryId of this._rows.keys()) this._read(entryId, this._generation);
  }

  _current(generation) { return generation === this._generation && this._context?.host.isConnected; }

  async _subscribe(entryId, generation) {
    try {
      const unsubscribe = await this._context.hass.connection.subscribeMessage((event) => {
        if (!this._current(generation) || event.entry_id !== entryId) return;
        const row = this._rows.get(entryId);
        if (event.kind === "removed") { row.removed = true; row.data = null; this._render(); return; }
        if (Number.isInteger(event.revision) && event.revision > (row.data?.revision ?? -1)) this._read(entryId, generation);
      }, { type: "myhome/cover_profiles/subscribe", entry_id: entryId });
      if (!this._current(generation)) { await unsubscribe(); return; }
      this._unsubs.push(unsubscribe);
    } catch { /* The panel's periodic refresh reconciles missed notifications. */ }
  }

  async _read(entryId, generation) {
    if (!this._current(generation) || document.hidden) return;
    const row = this._rows.get(entryId);
    if (!row || row.removed) return;
    if (row.loading) { row.again = true; return; }
    row.loading = true;
    const { hass } = this._context;
    try {
      const data = await hass.callWS({ type: "myhome/cover_profiles/overview", entry_id: entryId });
      if (!this._current(generation) || row.removed) return;
      if (data.entry_id !== entryId) throw new Error("Wrong gateway");
      if (!row.data || data.revision >= row.data.revision) row.data = data;
      row.error = false;
      // The overview carries no session: a cover read gives the gateway's session (one at a time). If a read
      // fails the next cover is tried; the overview still says when the gateway is reserved (calibration_busy).
      row.reserved = row.data.covers.some((cover) => cover.assignment_reason === "calibration_busy");
      row.session = null;
      row.sessionKnown = false;
      for (const probe of timedCovers(row.data).slice(0, SESSION_PROBES)) {
        try {
          const snapshot = await hass.callWS({ type: "myhome/cover_profiles/read", entry_id: entryId, entity_id: probe.entity_id });
          if (!this._current(generation)) return;
          row.session = snapshot.calibration && !["saved", "cancelled"].includes(snapshot.calibration.phase) ? snapshot.calibration : null;
          row.sessionKnown = true;
          break;
        } catch { /* Try the next cover; the session is read again at the next refresh. */ }
      }
      if (!timedCovers(row.data).length) row.sessionKnown = true;
    } catch {
      if (this._current(generation)) row.error = true;
    } finally {
      if (this._current(generation)) {
        row.loading = false;
        this._render();
        if (row.again) { row.again = false; this._read(entryId, generation); }
      }
    }
  }

  /** Every timed cover of the scope, with its gateway and inventory entity. */
  _covers() {
    const { gateways, inventory, hass } = this._context;
    return gateways.flatMap((entry) => {
      const row = this._rows.get(entry.entry_id);
      if (!row?.data) return [];
      return timedCovers(row.data).map((cover) => {
        const entity = inventory.entities.find((item) => item.entity_id === cover.entity_id && item.entry_id === entry.entry_id);
        const profile = row.data.profiles.find((item) => item.id === cover.profile_id) || null;
        const areaId = entity ? model.effectiveArea(entity, inventory.devices) : "";
        return { entry, cover, entity, profile, revision: row.data.revision, session: row.session,
          name: entity ? model.entityName(entity, hass) : cover.name, area: inventory.areas.find((area) => area.id === areaId)?.name || "",
          ...coverStatus(cover) };
      });
    }).sort((a, b) => a.name.localeCompare(b.name));
  }

  /** The rows in the chosen order: running covers first, then by the column; ties by name, then room. */
  _sorted(items, language) {
    const collator = new Intl.Collator(language, { sensitivity: "base", numeric: true });
    const { key, dir } = this._sort, sign = dir === "desc" ? -1 : 1;
    const byName = (a, b) => collator.compare(a.name, b.name) || collator.compare(a.area, b.area);
    const compare = (a, b) => {
      const running = Number(this._running(b)) - Number(this._running(a));
      if (running) return running;
      if (key === "status") return sign * ((STATUS_RANK[a.status] ?? 0) - (STATUS_RANK[b.status] ?? 0)) || byName(a, b);
      if (key === "profile") {
        // Covers without a profile stay at the bottom in both orders.
        if (!a.profile !== !b.profile) return a.profile ? -1 : 1;
        return (a.profile ? sign * collator.compare(a.profile.name, b.profile.name) : 0) || byName(a, b);
      }
      return sign * byName(a, b);
    };
    return [...items].sort(compare);
  }

  /** Same column: ascending, then descending, then back to the default order; another column starts ascending. */
  _setSort(key, dir) {
    if (!SORT_KEYS.includes(key)) return;
    if (dir) this._sort = { key, dir };
    else if (this._sort.key !== key) this._sort = { key, dir: "asc" };
    else if (this._sort.dir === "asc") this._sort = { key, dir: "desc" };
    else this._sort = { ...DEFAULT_SORT };
    try { window.localStorage.setItem(SORT_STORAGE_KEY, JSON.stringify(this._sort)); } catch { /* Kept for this visit only. */ }
    this._render();
  }

  _change(event) {
    if (this._mode.kind === "batch") {
      const input = event.target.closest?.(".cal-batch-row input[type=checkbox]");
      if (input) { this._batchToggle(input.value, input.checked); return; }
      if (event.target.matches?.('select[data-batch="gateway"]')) { this._loadBatch(event.target.value); return; }
      // M4-2: «Select ⌄» is a native menu of actions: the choice is applied, then the placeholder comes back.
      if (event.target.matches?.("select[data-batch-pick]")) {
        const pick = event.target.value;
        event.target.value = "";
        event.target.blur();
        if (pick) this._batchPick(pick);
        return;
      }
    }
    // M4-3: on a touch screen a native drop-down keeps the focus (and its ring) after the choice: let it go.
    const touch = typeof matchMedia === "function" && matchMedia("(hover: none)").matches;
    if (touch && event.target.matches?.("select[data-filter], select[data-sort]")) event.target.blur();
    if (event.target.matches?.("select[data-filter]") && this._mode.kind === "list") { this._filter = event.target.value; this._render(); return; }
    const select = event.target.closest?.("select[data-sort]");
    if (!select || !["list", "batch"].includes(this._mode.kind)) return;
    const [key, dir] = select.value.split(":");
    this._setSort(key, dir === "desc" ? "desc" : "asc");
  }

  /**
   * P-3: the one filter and order bar of the Calibration list, A-01 and the sequence. Two states, chosen by the bar's own
   * width (`@container calbar`, 640 px: a 680 px column less its padding): wide, the chips on the left (filters, or the
   * sequence's selection shortcuts) and «Ordina per» as a compact drop-down on the right; narrow, two native drop-downs at 50 % (the chips' drop-down and
   * the order). The order is the same `<select>` in both states.
   */
  _filterBar({ chips, chipsClass = "", label = "", select, compactClass = "", sortAttribute = "data-sort", extra = "" }) {
    const { t } = this._context;
    return `<div class="cal-filterbar${extra}"><div class="cal-filterbar-row">
          <div class="cal-tab-chips${chipsClass}" role="group" aria-label="${esc(t("calTabFilterLabel"))}">${label ? `<span class="cal-filterbar-label">${esc(label)}</span>` : ""}${chips}</div>
          <div class="cal-tab-compact${compactClass}">${select}${this._compactSort(sortAttribute)}</div></div></div>`;
  }

  /** The filter drop-down of the narrow bar (T-01c M): the four filters with their counts. */
  _filterSelect(counts, current, attribute = "data-filter") {
    const { t } = this._context;
    return `<label class="cal-compact-sort cal-compact-filter"><span>${esc(t("wiz_T474"))}</span><select ${attribute} aria-label="${esc(t("calTabFilterLabel"))}">${FILTERS.map((filter) =>
      `<option value="${filter}" ${current === filter ? "selected" : ""}>${esc(t(`calTabFilter_${filter}`))} (${counts[filter]})</option>`).join("")}</select></label>`;
  }

  /** «Ordina: Tapparella ↑ ⌄» (narrow) or «Ordina per: Tapparella ↑ ⌄» (wide): the order control of every list. */
  _compactSort(attribute = "data-sort") {
    const { t } = this._context;
    const column = (key) => t({ cover: "calTabColCover", status: "calTabColStatus", profile: "calTabColProfile" }[key]);
    const options = SORT_KEYS.flatMap((key) => ["asc", "desc"].map((dir) =>
      `<option value="${key}:${dir}" ${this._sort.key === key && this._sort.dir === dir ? "selected" : ""}>${esc(column(key))} ${dir === "asc" ? "↑" : "↓"}</option>`)).join("");
    return `<label class="cal-compact-sort cal-filterbar-sort"><span class="cal-sort-short">${esc(t("wiz_T450"))}</span><span class="cal-sort-long">${esc(t("wiz_T379"))}:</span><select ${attribute}="order" aria-label="${esc(t("wiz_T379"))}">${options}</select></label>`;
  }

  /** The header row of the Calibration table: Cover, Status and Profile sort it (the wizard's lists are cards). */
  _sortHeads(lead = "") {
    const { t } = this._context, trigger = (key) => `data-action="cal-tab-sort" data-id="${key}"`;
    return `<div class="cal-list-head" role="group" aria-label="${esc(t("wiz_T379"))}"><span class="cal-head-lead">${lead}</span>${this._sortHead("cover", t("calTabColCover"), trigger)}${this._sortHead("status", t("calTabColStatus"), trigger)}${this._sortHead("profile", t("calTabColProfile"), trigger)}<span></span></div>`;
  }

  /** A column header: a button that sorts by it, with the arrow of the current order. */
  _sortHead(key, label, trigger) {
    const { t } = this._context;
    const active = this._sort.key === key, dir = this._sort.dir;
    return `<span class="cal-sort-cell"><button type="button" class="cal-sort" ${trigger(key)} aria-pressed="${active}">${esc(label)}${active
      ? `<ha-icon icon="mdi:arrow-${dir === "asc" ? "up" : "down"}" aria-hidden="true"></ha-icon><span class="visually-hidden">, ${esc(t(dir === "asc" ? "wiz_T381" : "wiz_T382"))}</span>` : ""}</button></span>`;
  }

  /**
   * A-01's list: the sequence view's rows (name, room, bus address, status, profile) with one radio each, the list's
   * filter chips and its shared order. The wizard draws it and owns the choice; its controls carry `data-wiz`.
   * The chosen row opens and shows `notes` (the "already calibrated" note, the profile it follows).
   */
  _pickerMarkup({ selected = "", filter = "all", notes = [] } = {}) {
    const { t, hass, gateways } = this._context, language = hass.language || "en";
    const all = this._covers();
    const counts = { all: all.length, to_measure: all.filter((item) => item.status === "to_measure").length,
      calibrated: all.filter((item) => item.status !== "to_measure").length, profile: all.filter((item) => item.profile).length };
    const visible = this._sorted(all, language).filter((item) => filter === "all" || (filter === "to_measure" ? item.status === "to_measure"
      : filter === "calibrated" ? item.status !== "to_measure" : !!item.profile));
    const profile = (item) => item.profile ? `<span class="chip cal-profile-chip"><ha-icon icon="mdi:circle" aria-hidden="true"></ha-icon>${esc(item.profile.name)}</span>`
      : `<span class="muted" aria-label="${esc(t("calTabProfileNone"))}">—</span>`;
    const rows = visible.map((item) => {
      const key = JSON.stringify([item.entry.entry_id, item.cover.entity_id]), chosen = key === selected;
      return `<label class="cal-batch-row wiz-pick-row${chosen ? " is-selected" : ""}" data-entity="${esc(item.cover.entity_id)}">
        <span class="cal-batch-lead"><input type="radio" name="cover" value="${esc(key)}" ${chosen ? "checked" : ""}>
          <span class="cal-row-icon" aria-hidden="true"><ha-icon icon="mdi:window-shutter"></ha-icon></span></span>
        <span class="cal-row-name"><strong>${esc(item.name)}</strong><span class="muted">${this._subline([item.area, gateways.length > 1 ? item.entry.title : ""], item.entity)}</span></span>
        <span class="cal-batch-chips"><span class="cal-batch-status"><span class="badge cal-badge" data-status="${item.status}">${esc(t(`calTabStatus_${item.status}`))}</span></span>
        <span class="cal-batch-profile">${profile(item)}</span></span>
        ${chosen && notes.length ? `<span class="wiz-pick-notes">${notes.map((note) => `<span class="cal-note${note.tone === "warning" ? " is-warning" : ""}">${esc(note.text)}</span>`).join("")}</span>` : ""}</label>`;
    }).join("");
    return `${this._filterBar({ chipsClass: " wiz-pick-chips", sortAttribute: "data-pick-sort", extra: " wiz-pick-bar",
        chips: FILTERS.map((id) => `<button type="button" class="cal-chip" data-wiz="pick-filter:${id}" aria-pressed="${filter === id}">${esc(t(`calTabFilter_${id}`))} <span class="count">${counts[id]}</span></button>`).join(""),
        select: this._filterSelect(counts, filter, "data-pick-filter") })}
      <div class="cal-list cal-batch-list wiz-pick-list">
        <div class="cal-batch-rows" role="radiogroup" aria-label="${esc(t("wiz_T005"))}">${rows || `<p class="muted wiz-pick-empty">${esc(t("noResults"))}</p>`}</div></div>`;
  }

  /** In the chevron column: close every visible row when any is open, otherwise open them all (the filter applies). */
  _expandAll(visible) {
    const { t } = this._context;
    const keys = visible.map((item) => JSON.stringify([item.entry.entry_id, item.cover.entity_id]));
    const all = keys.some((key) => this._expanded.has(key));
    const label = t(all ? "wiz_T425" : "wiz_T424");
    return `<button type="button" class="icon-button cal-expand-all" data-action="cal-tab-expand-all" data-id="${all ? "collapse" : "expand"}" aria-label="${esc(label)}" title="${esc(label)}"><ha-icon icon="mdi:unfold-${all ? "less" : "more"}-horizontal" aria-hidden="true"></ha-icon></button>`;
  }

  _running(item) {
    const session = item.session;
    return !!session && (session.entity_id === item.cover.entity_id || (session.targets || []).some((target) => target.entity_id === item.cover.entity_id));
  }

  _matches(item) {
    const { filters, inventory } = this._context;
    if (filters.category && filters.category !== "cover") return false;
    if (filters.area) {
      const area = item.entity ? model.effectiveArea(item.entity, inventory.devices) : "";
      if (filters.area === "__none__" ? !!area : area !== filters.area) return false;
    }
    const terms = filters.query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const words = [item.name, item.cover.entity_id, item.profile?.name, item.entity?.address?.raw].filter(Boolean).join(" ").toLocaleLowerCase();
    return terms.every((term) => words.includes(term));
  }

  _render() {
    if (this._context?.host.isConnected && this._mode.kind === "batch") { this._renderBatch(); return; }
    if (!this._context?.host.isConnected || this._mode.kind !== "list") return;
    if (this._openPendingWizard()) return;
    const { host, t, hass, gateways } = this._context;
    const language = hass.language || "en";
    const loading = gateways.some((entry) => !this._rows.get(entry.entry_id)?.data && !this._rows.get(entry.entry_id)?.error && !this._rows.get(entry.entry_id)?.removed);
    const failed = gateways.filter((entry) => this._rows.get(entry.entry_id)?.error);
    const all = this._covers().filter((item) => this._matches(item));
    const counts = { all: all.length, to_measure: all.filter((item) => item.status === "to_measure").length,
      calibrated: all.filter((item) => item.status !== "to_measure").length, profile: all.filter((item) => item.profile).length };
    const visible = this._sorted(all, language).filter((item) => this._filter === "all" || (this._filter === "to_measure" ? item.status === "to_measure"
      : this._filter === "calibrated" ? item.status !== "to_measure" : !!item.profile));
    // A live session, or a gateway the overview reports reserved while its session could not be read: no new measurement.
    const rows = gateways.map((entry) => this._rows.get(entry.entry_id)).filter(Boolean);
    const busy = rows.map((row) => row.session).find(Boolean) || (rows.some((row) => row.data && row.reserved && !row.sessionKnown) ? { unknown: true } : null);
    let html;
    if (!loading && !failed.length && !this._covers().length) {
      // T-04: no cover estimated from its travel times on the gateway(s); the tab's title stays above.
      html = `<h3 class="cal-tab-title">${esc(t("calTabTitle"))}</h3>${this._emptyCard(t(gateways.length > 1 ? "wiz_T495" : "wiz_T492"), t("calTabEmptyBody"),
        `<details class="cal-empty-how"><summary>${esc(t("calTabHowItWorks"))}</summary><p class="muted">${esc(t("calTabHowItWorksBody"))}</p></details>`, "cal-tab-empty")}`;
    } else {
      // The buttons line up with the introduction, not with the title above it.
      html = `<h3 class="cal-tab-title">${esc(t("calTabTitle"))}</h3><div class="cal-tab-head"><p class="muted cal-tab-intro">${esc(t("calTabIntro"))}</p>
        <div class="actions cal-tab-actions">
          <button type="button" data-action="cal-tab-batch" ${busy || loading ? "disabled" : ""}><ha-icon icon="mdi:format-list-numbered" aria-hidden="true"></ha-icon><span>${esc(t("wiz_T363"))}</span></button>
          ${this._wizard ? `<button type="button" class="primary" data-action="cal-tab-measure" ${busy || loading || !counts.all ? "disabled" : ""}><ha-icon icon="mdi:ruler" aria-hidden="true"></ha-icon><span>${esc(t("calTabMeasureOne"))}</span></button>` : ""}
        </div></div>
        <p class="muted cal-tab-summary" role="status">${esc([["calTabCountCovers", counts.all], ["calTabCountCalibrated", counts.calibrated], ["calTabCountToMeasure", counts.to_measure]]
          .map(([key, count]) => fill(t(count === 1 ? `${key}_one` : key), { n: count })).join(" · "))}</p>
        ${this._filterBar({ extra: " cal-tab-filters", select: this._filterSelect(counts, this._filter),
          chips: FILTERS.map((filter) => `<button type="button" class="cal-chip" data-action="cal-tab-filter" data-id="${filter}" aria-pressed="${this._filter === filter}">${esc(t(`calTabFilter_${filter}`))} <span class="count">${counts[filter]}</span></button>`).join("") })}
        ${this._done ? `<p class="notice cal-tab-done" role="status"><ha-icon icon="mdi:check-circle-outline" aria-hidden="true"></ha-icon><span>${esc(this._done)}</span></p>` : ""}
        ${busy ? `<p class="notice cal-tab-busy" role="status"><ha-icon icon="mdi:information-outline" aria-hidden="true"></ha-icon><span>${esc(t("calTabBusy"))}</span></p>` : ""}
        ${this._filter === "to_measure" ? `<p class="cal-note cal-tab-help">${esc(t("calTabToMeasureHelp"))}</p>` : ""}
        ${failed.map((entry) => `<p class="notice error" role="alert">${esc(gateways.length > 1 ? `${entry.title}: ` : "")}${esc(t("calTabError"))}</p>`).join("")}
        ${failed.length ? `<button type="button" data-action="cal-tab-refresh">${esc(t("refresh"))}</button>` : ""}
        ${loading ? `<p class="muted" role="status">${esc(t("loading"))}</p>` : ""}
        ${visible.length || loading ? "" : this._emptyCard(t("wiz_T493"), t("wiz_T494"), "", "cal-tab-no-match")}
        ${visible.length ? `<div class="cal-list">
          ${this._sortHeads(this._expandAll(visible))}
          <div class="cal-list-rows" role="list">${visible.map((item) => this._row(item, busy, language)).join("")}</div></div>` : ""}
        ${this._pageMarkup(busy, language)}`;
    }
    // Patched in place (M3): the list, the details page and their scroll stay where they are.
    morph(host, html);
    this._band();
    fitLines(host);
    this._syncHold();
  }

  /** Q-3: the list's band for the tab's content width, as the stylesheet's container rules choose it (`data-band`). */
  _band() {
    const host = this._context?.host, width = contentWidth(host);
    if (!host || !width) return;
    const band = listBand(width);
    if (host.dataset.band !== band) host.dataset.band = band;
  }

  /** T-04 / T-04b: an empty state as a card: the shutter icon, a title, its explanation and an optional extra. */
  _emptyCard(title, body, extra = "", kind = "") {
    return `<div class="cal-empty ${kind}" role="status"><span class="cal-empty-icon" aria-hidden="true"><ha-icon icon="mdi:window-shutter"></ha-icon></span>
        <h4>${esc(title)}</h4><p class="muted">${esc(body)}</p>${extra}</div>`;
  }

  _row(item, busy, language) {
    const { t, gateways, addressDetails } = this._context;
    const key = JSON.stringify([item.entry.entry_id, item.cover.entity_id]);
    const id = `cal-row-${encodeURIComponent(key).replace(/%/g, "")}`;
    const expanded = this._expanded.has(key);
    const running = this._running(item);
    const session = running ? item.session : null;
    const badge = session ? `<span class="badge cal-badge" data-status="running">${esc(t(session.waiting_for_stop ? "calTabRunning_waiting"
      : session.phase === "paused" ? "calTabRunning_paused" : session.owner_present ?? session.attached ? "calTabRunning_present" : "calTabRunning_absent"))}</span>`
      : `<span class="badge cal-badge" data-status="${item.status}">${esc(t(`calTabStatus_${item.status}`))}</span>`;
    const profile = item.profile ? `<span class="chip cal-profile-chip"><ha-icon icon="mdi:circle" aria-hidden="true"></ha-icon>${esc(item.profile.name)}</span>` : `<span class="muted" aria-label="${esc(t("calTabProfileNone"))}">—</span>`;
    const last = item.last ? fill(t("calTabMeasuredOn"), { date: dateText(item.last, language) }) : "";
    const action = session
      ? (session.waiting_for_stop || session.recoverable === false ? "" : `<button type="button" class="cal-row-action" data-action="cal-tab-session" data-id="${esc(item.entry.entry_id)}">${esc(t("calOpenSession"))}</button>`)
      : this._wizard ? `<button type="button" class="cal-row-action" data-action="cal-tab-${item.rolls ? "refine" : "measure-cover"}" data-id="${esc(key)}" ${busy ? "disabled" : ""}>${esc(t(item.rolls ? "calTabActionRefine" : "calTabActionMeasure"))}</button>` : "";
    const menuOpen = this._menu === key;
    return `<div class="cal-row${session ? " is-running" : ""}${expanded ? " is-expanded" : ""}" role="listitem" data-entity="${esc(item.cover.entity_id)}" data-entry="${esc(item.entry.entry_id)}">
      <div class="cal-row-main">
        <button type="button" class="cal-row-toggle" data-action="cal-tab-toggle" data-id="${esc(key)}" aria-expanded="${expanded}" aria-controls="${esc(id)}">
          <span class="cal-row-lead" aria-hidden="true"><ha-icon class="cal-row-chevron" icon="mdi:chevron-right"></ha-icon><span class="cal-row-icon"><ha-icon icon="mdi:window-shutter"></ha-icon></span></span>
          <span class="cal-row-name"><strong>${esc(item.name)}</strong><span class="muted">${this._subline([this._area(item), gateways.length > 1 ? item.entry.title : ""], item.entity)}</span><span class="cal-row-last-inline">${esc(last || t("wiz_T418"))}</span></span></button>
        <span class="cal-row-chips"><span class="cal-row-status">${badge}</span>
        <span class="cal-row-profile">${profile}</span></span>
        <span class="cal-row-actions">${action}
          <span class="cal-menu-wrap"><button type="button" class="icon-button" data-action="cal-tab-menu" data-id="${esc(key)}" aria-haspopup="menu" aria-expanded="${menuOpen}" aria-label="${esc(t("calTabMore"))}: ${esc(item.name)}" title="${esc(t("calTabMore"))}"><ha-icon icon="mdi:dots-vertical" aria-hidden="true"></ha-icon></button>
          <span class="cal-menu" role="menu" ${menuOpen ? "" : "hidden"}>
            ${!session && this._wizard && item.rolls ? `<button type="button" role="menuitem" data-action="cal-tab-refine" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="mdi:target" aria-hidden="true"></ha-icon>${esc(t("calTabActionRefine"))}</button>` : ""}
            ${!session && this._wizard ? `<button type="button" role="menuitem" data-action="cal-tab-measure-cover" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="${item.status === "to_measure" ? "mdi:ruler" : "mdi:reload"}" aria-hidden="true"></ha-icon>${esc(t(item.status === "to_measure" ? "calTabActionMeasure" : "calTabActionRemeasure"))}</button>` : ""}
            <button type="button" role="menuitem" data-action="cal-tab-assign" data-id="${esc(key)}"><ha-icon icon="mdi:link-variant" aria-hidden="true"></ha-icon>${esc(t(item.profile ? "wiz_T427" : "calTabAssign"))}</button>
            <button type="button" role="menuitem" data-action="cal-tab-toggle" data-id="${esc(key)}"><ha-icon icon="mdi:information-outline" aria-hidden="true"></ha-icon>${esc(t("calTabDetails"))}</button>
          </span></span></span>
      </div>
      <div class="cal-row-details" id="${esc(id)}" ${expanded ? "" : "hidden"}>${expanded ? this._details(item, busy, language, addressDetails) : ""}</div>
    </div>`;
  }

  /** "Address: 86 · A: 8 · PL: 6" with the device cards' style: grey labels, dark values. */
  _address(item) {
    const address = item.entity?.address, { t } = this._context;
    if (!address?.raw) return "";
    const fields = [[t("address"), address.raw], ...(address.a != null && address.pl != null ? [["A", address.a], ["PL", address.pl]] : [])];
    // On the cards only «Address: 86»; A and PL in their own span.
    const part = ([label, value]) => `<span><span class="cal-row-address-label">${esc(label)}:</span> <span class="cal-row-address-value">${esc(value)}</span></span>`;
    const [first, ...rest] = fields;
    return `${part(first)}${rest.length ? `<span class="cal-row-address-ap"> · ${rest.map(part).join(" · ")}</span>` : ""}`;
  }

  /**
   * The line under a cover's name (responsive map §3.3): room, gateway, bus address as units. It wraps only between
   * units (the «·» stays with the unit before it) and the address never breaks: two lines rather than «…».
   */
  _subline(before, entity, after = []) {
    const address = this._address({ entity });
    const pieces = [...before.filter(Boolean).map((unit) => ["cal-row-unit", esc(unit)]), ...(address ? [["cal-row-address", address]] : []),
      ...after.filter(Boolean).map((unit) => ["cal-row-unit", esc(unit)])];
    return pieces.map(([kind, html], index) => `<span class="${kind}">${html}${index < pieces.length - 1 ? " ·" : ""}</span>`).join(" ");
  }

  _area(item) { return item.area; }

  /**
   * T-05 M: on phones a cover's details are a page over the list (the list stays below it, so closing it lands at the
   * same place): name, address and ✕ at the top, then the title, the status and the three blocks one under the other.
   */
  _pageMarkup(busy, language) {
    const item = this._page ? this._item(this._page) : null;
    if (!item) { this._page = null; return ""; }
    const { t, gateways, addressDetails } = this._context;
    const session = this._running(item) ? item.session : null;
    const badge = session ? `<span class="badge cal-badge" data-status="running">${esc(t(session.waiting_for_stop ? "calTabRunning_waiting"
      : session.phase === "paused" ? "calTabRunning_paused" : session.owner_present ?? session.attached ? "calTabRunning_present" : "calTabRunning_absent"))}</span>`
      : `<span class="badge cal-badge" data-status="${item.status}">${esc(t(`calTabStatus_${item.status}`))}</span>`;
    return `<div class="cal-page${session ? " is-running" : ""}" role="dialog" aria-modal="true" aria-labelledby="cal-page-name" data-entity="${esc(item.cover.entity_id)}">
        <div class="cal-page-head"><div class="cal-page-head-text"><h2 id="cal-page-name">${esc(item.name)}</h2>
          <p class="muted">${this._subline([this._area(item), gateways.length > 1 ? item.entry.title : ""], item.entity)}</p></div>
          <button type="button" class="icon-button cal-page-close" data-action="cal-tab-page-close" aria-label="${esc(t("wiz_T448"))}" title="${esc(t("wiz_T448"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button></div>
        <div class="cal-page-body"><div class="cal-page-title"><h3>${esc(t("wiz_T447"))}</h3>${badge}</div>
          ${this._details(item, busy, language, addressDetails)}</div></div>`;
  }

  /**
   * Only the phone layout (window under 720 px, not a landscape phone) opens a cover's details as a page; elsewhere the
   * row or the card opens in place, so the page never covers Home Assistant's sidebar (responsive map, D3).
   */
  _phone() { return layout.phone(); }

  _closePage() {
    const page = this._context.host.querySelector(".cal-page");
    if (page && layout.slides() && !page.classList.contains("is-leaving")) {
      page.classList.add("is-leaving");
      setTimeout(() => { if (this._page) this._closePage(); }, 220);
      return;
    }
    const key = this._page;
    this._page = null;
    this._render();
    [...this._context.host.querySelectorAll('.cal-row [data-action="cal-tab-toggle"].cal-row-toggle')].find((button) => button.dataset.id === key)?.focus({ preventScroll: true });
  }

  _details(item, busy, language) {
    const { t, inventory, hass } = this._context;
    const effective = item.cover.effective;
    const value = (key, digits = 1) => number(effective[key]?.value, language, digits);
    const slat = effective.slat_time_s?.value;
    const rows = [
      [t("wiz_T093"), `${value("opening")} s`], [t("wiz_T094"), `${value("closing")} s`],
      [t("calTabSlats"), slat == null ? "—" : slat === 0 ? t("calTabSlatsNo") : fill(t("calTabSlatsYes"), { seconds: number(slat, language) })],
      [t("wiz_T041"), item.cover.travel_cm == null ? "—" : `${number(item.cover.travel_cm, language)} cm`],
      [t("wiz_T105"), item.rolls ? value("opening_roll", 2) : "—"], [t("wiz_T106"), item.rolls ? value("closing_roll", 2) : "—"],
    ];
    const followers = item.profile ? item.profile.assigned_to.filter((id) => id && id !== item.cover.entity_id).map((id) => {
      const entity = inventory.entities.find((entry) => entry.entity_id === id);
      return entity ? model.entityName(entity, hass) : id;
    }) : [];
    const scaled = ["opening", "closing"].some((direction) => effective[direction]?.origin === "profile");
    const list = (items) => `<dl class="cal-facts">${items.map(([label, shown]) => `<div><dt>${esc(label)}</dt><dd>${esc(shown)}</dd></div>`).join("")}</dl>`;
    const key = JSON.stringify([item.entry.entry_id, item.cover.entity_id]);
    // Each block ends with its own action, left-aligned under its content.
    const action = (button) => button ? `<div class="cal-block-action">${button}</div>` : "";
    const refine = this._wizard && item.rolls ? `<button type="button" class="primary" data-action="cal-tab-refine" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="mdi:target" aria-hidden="true"></ha-icon>${esc(t("calTabActionRefine"))}</button>` : "";
    const measure = this._wizard ? `<button type="button" class="${item.rolls ? "" : "primary"}" data-action="cal-tab-measure-cover" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="${item.status === "to_measure" ? "mdi:ruler" : "mdi:reload"}" aria-hidden="true"></ha-icon>${esc(t(item.status === "to_measure" ? "calTabActionMeasure" : "calTabActionRemeasure"))}</button>` : "";
    // A cover that follows a profile changes it (or unlinks it); one that follows none is assigned one.
    const assign = `<button type="button" data-action="cal-tab-assign" data-id="${esc(key)}"><ha-icon icon="mdi:link-variant" aria-hidden="true"></ha-icon>${esc(t(item.profile ? "wiz_T427" : "calTabAssign"))}</button>`;
    // A cover in progress is yellow throughout: its notes take the warning variant (icon and primary stay accent).
    const note = this._running(item) ? "cal-note is-warning" : "cal-note";
    return `<div class="cal-details-grid">
        <section><h4>${esc(t("calTabValues"))}</h4>${list(rows)}${this._originNote(item, language)}${action(refine)}</section>
        <section><h4>${esc(t("calTabColLast"))}</h4>${list([[t("calTabDate"), item.last ? dateText(item.last, language) : "—"],
          [t("calTabMethod"), t(`calTabMethod_${item.method || "none"}`)]])}
          ${item.profile && scaled ? `<p class="${note}">${esc(fill(t("calTabInheritedNote"), { profile: item.profile.name }))}</p>` : ""}${action(measure)}</section>
        <section><h4>${esc(t("calTabColProfile"))}</h4>${item.profile ? `<p><span class="chip cal-profile-chip"><ha-icon icon="mdi:circle" aria-hidden="true"></ha-icon>${esc(item.profile.name)}</span></p>
          <p>${esc(followers.length ? fill(t("calTabFollowers"), { names: names(followers, language) }) : t("calTabFollowersNone"))}</p>
          <p class="${note}">${esc(t("calTabProfileNote"))}</p>` : `<p class="muted">${esc(t("calTabProfileNone"))}</p>`}${action(assign)}</section>
      </div>`;
  }

  /** Where the times of a never measured cover come from: the integration's default or the YAML configuration. */
  _originNote(item, language) {
    const effective = item.cover.effective, origin = effective.opening?.origin;
    if (item.status !== "to_measure" || !["default", "yaml"].includes(origin) || effective.closing?.origin !== origin) return "";
    const [opening, closing] = [effective.opening.value, effective.closing.value].map((value) => number(value, language));
    return `<p class="cal-note${this._running(item) ? " is-warning" : ""} cal-origin-note">${esc(fill(this._context.t(origin === "yaml" ? "wiz_T378" : "wiz_T377"),
      { seconds: opening === closing ? opening : `${opening} / ${closing}` }))}</p>`;
  }

  _item(key) {
    const [entryId, entityId] = JSON.parse(key);
    return this._covers().find((item) => item.entry.entry_id === entryId && item.cover.entity_id === entityId);
  }

  _keydown(event) {
    if (this._page && this._menu === null && this._mode.kind === "list" && event.key === "Escape") { event.preventDefault(); this._closePage(); return; }
    if (this._menu === null || this._mode.kind !== "list") return;
    if (["ArrowDown", "ArrowUp"].includes(event.key)) {
      // Menu items move with the arrows and wrap, as in Home Assistant's own menus.
      const items = [...this._context.host.querySelectorAll('.cal-menu:not([hidden]) [role="menuitem"]')];
      const index = items.indexOf(this._context.host.getRootNode().activeElement);
      if (!items.length) return;
      event.preventDefault();
      items[(index + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length].focus();
      return;
    }
    if (event.key !== "Escape") return;
    const key = this._menu;
    this._menu = null;
    this._render();
    [...this._context.host.querySelectorAll('[data-action="cal-tab-menu"]')].find((button) => button.dataset.id === key)?.focus();
  }

  _click(event) {
    if (this._mode.kind === "batch") {
      // M6-1 (R7-7): a tap on the Steps sheet's backdrop closes it.
      if (event.target.classList?.contains("wiz-sheet")) {
        this._batchStepsOpen = false;
        event.target.hidden = true;
        return;
      }
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const { action, id } = button.dataset;
      if (action === "cal-tab-batch-back") this._batchBack();
      else if (action === "cal-tab-batch-steps" || action === "cal-tab-batch-steps-close") {
        this._batchStepsOpen = action === "cal-tab-batch-steps";
        this._context.host.querySelector(".cal-batch .wiz-sheet")?.toggleAttribute("hidden", !this._batchStepsOpen);
      }
      else if (action === "cal-tab-batch-pick") this._batchPick(id);
      else if (action === "cal-tab-batch-start") this._batchStart();
      else if (action === "cal-tab-sort") this._setSort(id);
      return;
    }
    if (this._mode.kind !== "list") return;
    const target = event.target.closest("button");
    // The whole row opens and closes its details, as the maintainer's device cards do; its buttons keep their own action.
    const row = !target && !event.target.closest(".cal-menu, a, input, select") && event.target.closest(".cal-row-main");
    if (row) { row.querySelector('[data-action="cal-tab-toggle"]')?.click(); return; }
    if (!target) return;
    const { action, id } = target.dataset;
    if (action !== "cal-tab-menu" && this._menu !== null) { this._menu = null; if (!action?.startsWith("cal-tab-")) this._render(); }
    if (action === "cal-tab-filter") { this._filter = id; this._render(); }
    else if (action === "cal-tab-sort") this._setSort(id);
    else if (action === "cal-tab-expand-all") {
      const language = this._context.hass.language || "en";
      const visible = this._sorted(this._covers().filter((item) => this._matches(item)), language).filter((item) => this._filter === "all"
        || (this._filter === "to_measure" ? item.status === "to_measure" : this._filter === "calibrated" ? item.status !== "to_measure" : !!item.profile));
      for (const item of visible) {
        const key = JSON.stringify([item.entry.entry_id, item.cover.entity_id]);
        if (id === "collapse") this._expanded.delete(key); else this._expanded.add(key);
      }
      this._render();
    } else if (action === "cal-tab-toggle") {
      if (this._phone()) {
        this._page = id;
        this._render();
        this._context.host.querySelector(".cal-page-close")?.focus();
        return;
      }
      if (this._expanded.has(id)) this._expanded.delete(id); else this._expanded.add(id);
      this._render();
    } else if (action === "cal-tab-page-close") {
      this._closePage();
    } else if (action === "cal-tab-menu") {
      this._menu = this._menu === id ? null : id;
      this._render();
      if (this._menu) this._context.host.querySelector('.cal-menu:not([hidden]) [role="menuitem"]')?.focus();
    } else if (action === "cal-tab-refresh") this.refresh();
    else if (action === "cal-tab-batch") this._selectBatch();
    else if (action === "cal-tab-session") this._openSession(id);
    else if (action === "cal-tab-measure") this._openWizard({ start: "choose" });
    else if (action === "cal-tab-measure-cover") { const item = this._item(id); if (item) this._openWizard({ start: "path", item }); }
    else if (action === "cal-tab-refine") { const item = this._item(id); if (item) this._openWizard({ start: "refine", item }); }
    else if (action === "cal-tab-assign") { const item = this._item(id); if (item) this._assignProfile(item); }
    else if (action?.startsWith("cal-tab-")) this._render();
  }

  /** Open the wizard on a cover as soon as the list knows it (the tab may still be loading). */
  requestWizard(entryId, entityId) {
    // Never queued behind an open wizard, group or session: it would open by surprise when that closes.
    if (this._mode.kind !== "list") return;
    this._pendingWizard = { entryId, entityId };
    if (this._context) this._render();
  }

  _openPendingWizard() {
    const pending = this._pendingWizard;
    if (!pending || !this._wizard || this._mode.kind !== "list") return false;
    const row = this._rows.get(pending.entryId);
    if (!row || (!row.data && !row.error)) return false;
    this._pendingWizard = null;
    const item = this._covers().find((entry) => entry.entry.entry_id === pending.entryId && entry.cover.entity_id === pending.entityId);
    if (!item || row.session || (row.reserved && !row.sessionKnown)) return false;
    this._openWizard({ start: "path", item });
    return true;
  }

  /** Back to the list after a wizard, a group or an opened session; the backend is read again. */
  _backToList() {
    // M5-4: on a phone the full-screen view slides down before the list comes back (at once with reduced motion).
    const view = this._context?.host.querySelector(":scope > .wiz");
    if (view && layout.slides() && !view.classList.contains("is-leaving")) {
      view.classList.add("is-leaving");
      setTimeout(() => { if (view.isConnected) this._backToList(); }, 220);
      return;
    }
    this._mode = { kind: "list" };
    if (!this._context) return;
    // Back from the wizard opened on a cover's details page: the same page again (a row opened in place stays open).
    if (this._pageReturn && layout.phone()) this._page = this._pageReturn;
    this._pageReturn = null;
    this._context.host.innerHTML = "";
    this._render();
    this.refresh();
  }

  _openWizard(options) {
    if (!this._wizard || !this._context) return;
    this._done = "";
    this._mode = { kind: "wizard" };
    const { host, hass, t, onOpenCover } = this._context;
    // The covers as they are at each step: after a save, fine-tuning (C-01) shows the values just written.
    this._wizard.open({ host, hass, t, covers: () => this._covers(), data: (entryId) => this._rows.get(entryId)?.data, ...options,
      // A-01's list, drawn as the tab's lists are, in the list's shared order.
      picker: { markup: (state) => this._pickerMarkup(state), sort: (key, dir) => this._setSort(key, dir), order: () => ({ ...this._sort }) },
      onOpenCover: (entityId) => onOpenCover?.(entityId),
      onAssignProfile: (profile) => this._assignToCovers(profile),
      onClose: () => this._backToList() });
  }

  /** The gateway's open session: the wizard for its own modes, the existing view, in its own dialog, for the others. */
  _openSession(entryId) {
    const row = this._rows.get(entryId), session = row?.session;
    if (!session || !this._context) return;
    const item = this._covers().find((entry) => entry.entry.entry_id === entryId && entry.cover.entity_id === session.entity_id);
    // The wizard needs the cover in the list (name, gateway); otherwise the existing view opens it.
    if (item && this._wizard?.handles?.(session)) { this._openWizard({ start: "resume", session, item }); return; }
    const { hass, t } = this._context;
    const body = this._openDialog({ title: t(session.batch ? "wiz_T364" : "calTitle"), subtitle: session.batch ? "" : item?.name || session.entity_id,
      icon: session.batch ? "mdi:format-list-numbered" : "mdi:timer-outline" });
    this._calibration.open({ host: body, hass, t, entity: { entry_id: entryId, entity_id: session.entity_id }, resume: session,
      revision: row.data?.revision, onCancel: () => this._dialogDone(), onSaved: () => this._dialogDone() });
  }

  /**
   * A dialog with the look of the maintainer's profile dialog, in the panel's dialog host. Closing it leaves an open
   * session as closing the profile dialog does: the session keeps running in Home Assistant.
   */
  _openDialog({ title, subtitle = "", icon }) {
    this._closeDialog();
    this._done = "";
    const { dialogHost, t } = this._context;
    dialogHost.innerHTML = `<dialog class="cover-profile-dialog cal-dialog" aria-labelledby="cal-dialog-title">
      <header class="dialog-head"><div class="dialog-icon" aria-hidden="true"><ha-icon icon="${esc(icon)}"></ha-icon></div>
        <div class="dialog-head-text"><h2 id="cal-dialog-title">${esc(title)}</h2>${subtitle ? `<p class="muted">${esc(subtitle)}</p>` : ""}</div></header>
      <div class="cal-dialog-body"></div>
      <footer class="dialog-foot"><button type="button" class="cal-dialog-close">${esc(t("close"))}</button></footer></dialog>`;
    const dialog = dialogHost.querySelector("dialog");
    dialog.querySelector(".cal-dialog-close").onclick = () => this._dialogDone();
    dialog.oncancel = (event) => { event.preventDefault(); this._dialogDone(); };
    // A click on the backdrop (outside the dialog's box) closes it as Escape does, applying nothing.
    dialog.addEventListener("click", (event) => {
      if (event.target !== dialog) return;
      const box = dialog.getBoundingClientRect();
      const inside = event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top && event.clientY <= box.bottom;
      if (!inside || (!box.width && !box.height)) this._dialogDone();
    });
    dialog.showModal();
    this._dialog = dialog;
    this._holdPage(dialog);
    return dialog.querySelector(".cal-dialog-body");
  }

  _closeDialog() {
    this._calibration.close();
    this._dialog?.close();
    this._dialog?.remove();
    this._dialog = null;
    this._releasePage();
  }

  /**
   * M2-6: while a sheet is open on a phone the page under it does not scroll (iOS scrolls the page behind a modal
   * dialog, and the sheet moves with it): every scrolling ancestor of the panel, `html` and `body` get
   * `overflow: hidden` until the sheet closes. Only the sheet's body scrolls; its footer stays at the bottom, with the
   * fade above it while there is more to read (as M-5).
   */
  _holdPage(dialog) {
    this._releasePage();
    const body = dialog.querySelector(".cal-dialog-body"), foot = dialog.querySelector(".dialog-foot");
    if (body && foot) {
      const more = () => foot.classList.toggle("has-more", body.scrollHeight - body.scrollTop - body.clientHeight > 1);
      body.addEventListener("scroll", more, { passive: true });
      if (typeof ResizeObserver === "function") { this._sheetObserver = new ResizeObserver(more); this._sheetObserver.observe(body); }
      more();
    }
    if (!layout.sheets()) return;
    this._held = holdScroll(this._context.host);
  }

  _releasePage() {
    this._sheetObserver?.disconnect();
    this._sheetObserver = null;
    this._held?.();
    this._held = null;
  }

  /**
   * The cover a measurement was taken on, as the list names it: Home Assistant's provenance carries the registry name,
   * which for a cover named by its device is only the entity id.
   */
  _originName(origin) {
    const id = origin?.origin_entity_id, { hass } = this._context;
    return (id && (this._covers().find((item) => item.cover.entity_id === id)?.name || hass.states?.[id]?.attributes?.friendly_name))
      || origin?.origin_name || id || "";
  }

  /** A cover by the name the list gives it (then its friendly name, then its entity id). */
  _coverName(id) {
    return this._covers().find((item) => item.cover.entity_id === id)?.name || this._context.hass.states?.[id]?.attributes?.friendly_name || id;
  }

  _dialogDone() {
    // As a sheet (window under 720 × 500 px) the dialog slides down before it closes (at once with reduced motion or centred).
    const dialog = this._dialog;
    if (dialog && layout.slides(SHEETS) && !dialog.classList.contains("is-leaving")) {
      dialog.classList.add("is-leaving");
      setTimeout(() => { if (this._dialog === dialog) { this._closeDialog(); this.refresh(); } }, 220);
      return;
    }
    if (dialog?.classList.contains("is-leaving")) return;
    this._closeDialog();
    this.refresh();
  }

  /**
   * "Assign profile": the gateway's saved profiles as on B-01 (type, where and when measured, reference travel, who
   * follows it), one to choose, then the existing `assign` write. Nothing moves; the profile dialog stays the
   * maintainer's.
   */
  _assignProfile(item) {
    const { hass, t } = this._context, language = hass.language || "en";
    const data = this._rows.get(item.entry.entry_id)?.data;
    if (!data) return;
    const body = this._openDialog({ title: t(item.profile ? "wiz_T427" : "calTabAssign"), subtitle: item.name, icon: "mdi:link-variant" });
    const dialog = this._dialog, generation = this._generation;
    const profiles = [...data.profiles].sort((a, b) => a.name.localeCompare(b.name));
    // Who follows each profile, by name, to recognise a similar cover.
    const followers = (profile) => followedBy(t, profile.assigned_to.filter(Boolean).map((id) => this._coverName(id)), language);
    const describe = (profile) => {
      const slat = profile.geometry?.slat_time_s;
      const origin = profile.provenance?.opening;
      return [
        [t(slat == null ? "wiz_T370" : slat > 0 ? "wiz_T368" : "wiz_T369"),
          profile.reference_travel_cm != null ? fill(t("wiz_T372"), { cm: number(profile.reference_travel_cm, language) }) : ""].filter(Boolean).join(" · "),
        origin?.recorded_at && (origin.origin_entity_id || origin.origin_name)
          ? fill(t("wiz_T371"), { cover: this._originName(origin), date: dateText(origin.recorded_at, language) }) : "",
        followers(profile),
      ];
    };
    // "No profile" unlinks the profile the cover follows. On the cover the profile was measured on it is shown disabled:
    // its values live only in the profile until Home Assistant copies them on unlinking (backend lot to plan).
    const followed = data.profiles.find((profile) => profile.id === item.cover.profile_id);
    const source = followed?.provenance?.opening?.origin_entity_id === item.cover.entity_id;
    const none = followed ? `<label class="wiz-radio cal-assign-none${source ? " is-disabled" : ""}"><input type="radio" name="assign_profile" value="${NO_PROFILE}"${source ? " disabled" : ""}>
        <span><strong><ha-icon icon="mdi:link-variant-off" aria-hidden="true"></ha-icon>${esc(t("wiz_T404"))}</strong><small class="muted">${esc(fill(t(source ? "wiz_T430" : "wiz_T405"), { profile: followed.name }))}</small></span></label>` : "";
    body.innerHTML = profiles.length ? `<fieldset class="wiz-radios cal-assign-list"><legend>${esc(t("wiz_T163"))}</legend>${none}${profiles.map((profile) => {
      const [type, measured, followers] = describe(profile);
      return `<label class="wiz-radio"><input type="radio" name="assign_profile" value="${esc(profile.id)}" ${profile.id === item.cover.profile_id ? "checked" : ""}>
        <span><strong>${esc(profile.name)}</strong><small class="muted">${esc(type)}</small>${measured ? `<small class="muted">${esc(measured)}</small>` : ""}<small class="muted cal-assign-followers">${esc(followers)}</small></span></label>`;
    }).join("")}</fieldset>
      <p class="error" role="alert" hidden></p>`
      : `<p class="muted">${esc(t("profileListEmpty"))}</p>`;
    // A calibration open on the gateway reserves it: Home Assistant would refuse, so the dialog says so and waits.
    const row = this._rows.get(item.entry.entry_id), reserved = !!(row?.session || row?.reserved);
    if (reserved) body.insertAdjacentHTML("afterbegin", `<p class="cal-note cal-assign-busy" role="status">${esc(t("wiz_T412"))}</p>`);
    if (!profiles.length) return;
    // As in the design (T-09): Cancel, outlined, then Assign on the footer's row.
    const cancel = dialog.querySelector(".cal-dialog-close");
    cancel.textContent = t("wiz_T025");
    cancel.classList.add("cal-dialog-cancel");
    dialog.querySelector(".dialog-foot").insertAdjacentHTML("beforeend", `<button type="button" class="primary" data-assign disabled>${esc(t("wiz_T373"))}</button>`);
    const button = dialog.querySelector("[data-assign]");
    const chosen = () => body.querySelector('input[name="assign_profile"]:checked')?.value;
    // Assign stays off while the gateway is reserved, and after Home Assistant has refused once.
    let refused = false;
    body.onchange = () => {
      button.disabled = reserved || refused || !chosen() || chosen() === item.cover.profile_id;
      // Unlinking is said as such on the button, with the broken link.
      button.innerHTML = chosen() === NO_PROFILE ? `<ha-icon icon="mdi:link-variant-off" aria-hidden="true"></ha-icon><span>${esc(t("wiz_T406"))}</span>` : esc(t("wiz_T373"));
    };
    button.onclick = async () => {
      const choice = chosen();
      if (!choice || button.disabled || reserved || refused) return;
      const profileId = choice === NO_PROFILE ? null : choice;
      button.disabled = true;
      const box = body.querySelector(".error");
      box.hidden = true;
      try {
        await hass.callWS({ type: "myhome/cover_profiles/write", entry_id: item.entry.entry_id, entity_id: item.cover.entity_id,
          revision: data.revision, action: "assign", profile_id: profileId });
        if (generation === this._generation && this._dialog === dialog) {
          if (profileId === null) this._done = fill(t("wiz_T407"), { cover: item.name });
          this._dialogDone();
        }
      } catch (error) {
        if (generation !== this._generation || this._dialog !== dialog) return;
        const key = `profileError_${error?.code}`;
        box.textContent = t(key) === key ? t("profileError") : t(key);
        box.hidden = false;
        refused = true;
      }
    };
  }

  /**
   * A-34's "Assign this profile to other covers": the maintainer's own Assign dialog (the one the Profiles tab opens,
   * ProfileCatalogueEditor with action "assign"), on the profile just written. A profile just created is found by
   * name once the overview carries it.
   */
  async _assignToCovers({ entryId, profileId, name }) {
    if (!this._context) return;
    const find = () => this._rows.get(entryId)?.data?.profiles.find((profile) => (profileId && profile.id === profileId) || (!profileId && profile.name === name));
    if (!find()) await this._read(entryId, this._generation);
    const profile = find();
    if (!profile || !this._context) return;
    const { hass, t, dialogHost, inventory, addressDetails } = this._context;
    this._catalogue ??= new ProfileCatalogueEditor();
    this._catalogue.open({ host: dialogHost, hass, entryId, profileId: profile.id, action: "assign", entities: inventory.entities,
      addressDetails, t, onSaved: () => this.refresh() });
  }

  /** Several covers in sequence: the existing selection and automatic batch, in a dialog, with readable names. */
  /** Sequence selection (T-06): a view in the tab, in place of the list, with our own rows. */
  async _selectBatch() {
    const { gateways } = this._context;
    this._menu = null;
    this._mode = { kind: "batch" };
    this._batch = { entryId: gateways[0].entry_id, data: null, order: [], error: "", loading: true };
    this._context.host.innerHTML = "";
    await this._loadBatch(this._batch.entryId);
  }

  async _loadBatch(entryId) {
    const { hass } = this._context, generation = this._generation;
    const batch = this._batch = { entryId, data: null, order: [], error: "", loading: true };
    this._render();
    try {
      batch.data = await hass.callWS({ type: "myhome/cover_calibration/targets", entry_id: entryId });
    } catch (error) {
      const key = `profileError_${error?.code}`, { t } = this._context;
      batch.error = t(key) === key ? t("profileError") : t(key);
    }
    if (!this._current(generation) || this._batch !== batch) return;
    batch.loading = false;
    this._render();
  }

  /** The gateway's targets with the names, rooms, addresses, status and profile the list shows, in the list's order. */
  _batchTargets() {
    const batch = this._batch, { inventory, hass } = this._context;
    const covers = new Map(this._covers().filter((item) => item.entry.entry_id === batch.entryId).map((item) => [item.cover.entity_id, item]));
    return this._sorted((batch.data?.targets || []).map((target) => {
      const item = covers.get(target.entity_id);
      const entity = item?.entity || inventory.entities.find((entry) => entry.entity_id === target.entity_id && entry.entry_id === batch.entryId);
      const area = item?.area ?? (entity ? inventory.areas.find((entry) => entry.id === model.effectiveArea(entity, inventory.devices))?.name || "" : "");
      return { ...target, item, entity, area, status: item?.status, profile: item?.profile || null,
        name: item?.name || (entity ? model.entityName(entity, hass) : target.name) };
    }), hass.language || "en");
  }

  _renderBatch() {
    const { host, t, gateways } = this._context;
    const batch = this._batch, max = batch.data?.max_batch ?? 0, count = batch.order.length;
    // The same order as the list (shared choice); the place in the sequence stays the order of the ticks.
    const targets = this._batchTargets();
    const statusBadge = (item) => item ? `<span class="badge cal-badge" data-status="${item.status}">${esc(t(`calTabStatus_${item.status}`))}</span>` : "";
    const profile = (item) => item?.profile ? `<span class="chip cal-profile-chip"><ha-icon icon="mdi:circle" aria-hidden="true"></ha-icon>${esc(item.profile.name)}</span>`
      : `<span class="muted" aria-label="${esc(t("calTabProfileNone"))}">—</span>`;
    const rows = targets.map((target) => {
      const place = batch.order.indexOf(target.entity_id);
      return `<label class="cal-batch-row${place >= 0 ? " is-selected" : ""}" data-entity="${esc(target.entity_id)}">
        <span class="cal-batch-lead"><input type="checkbox" value="${esc(target.entity_id)}" ${place >= 0 ? "checked" : ""} ${target.reason ? "disabled" : ""}>
          <span class="cal-batch-order" aria-hidden="true">${place >= 0 ? place + 1 : ""}</span>
          <span class="cal-row-icon" aria-hidden="true"><ha-icon icon="mdi:window-shutter"></ha-icon></span></span>
        <span class="cal-row-name"><strong>${esc(target.name)}</strong><span class="muted">${this._subline([target.area], target.entity, target.reason ? [t(`profileError_${target.reason}`)] : [])}</span></span>
        <span class="cal-batch-chips"><span class="cal-batch-status">${statusBadge(target.item)}</span>
        <span class="cal-batch-profile">${profile(target.item)}</span></span></label>`;
    }).join("");
    const summary = count === 0 ? t("wiz_T386") : count === 1 ? t("wiz_T385") : fill(t("wiz_T384"), { count });
    const select = t("wiz_T383").replace(/\s*:\s*$/, "");
    const picks = [["all", t("calTabFilter_all")], ["to_measure", t("calTabFilter_to_measure")], ["none", t("wiz_T391")]];
    // M4-5 (T-06w): the selection is a view with the wizard's chrome: header (back, title, capacity, «Cancel the
    // sequence» / ✕), the steps Selection · Run · Results (the last two still run in the maintainer's dialog), the
    // content in the middle and the status with Start in the actions column (the bottom bar on phones).
    const line = fill(t("wizPhaseLine"), { phase: t("wiz_T482"), n: 1, total: 3 });
    const html = `<div class="wiz cal-batch cal-batch-wiz">
      <div class="wiz-frame">
        <header class="wiz-head">
          <button type="button" class="icon-button wiz-back" data-action="cal-tab-batch-back" aria-label="${esc(t("wiz_T403"))}" title="${esc(t("wiz_T403"))}"><ha-icon icon="mdi:arrow-left" aria-hidden="true"></ha-icon></button>
          <div class="wiz-head-text"><h3 class="wiz-cover">${esc(t("wiz_T364"))}</h3><p class="muted wiz-head-sub">${esc(fill(t("wiz_T488"), { max }))}</p></div>
          <button type="button" class="wiz-discard" data-action="cal-tab-batch-back">${esc(t("wiz_T366"))}</button>
          <button type="button" class="icon-button wiz-x" data-action="cal-tab-batch-back" aria-label="${esc(t("wiz_T366"))}" title="${esc(t("wiz_T366"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button>
        </header>
        <div class="wiz-compact"><span class="wiz-dot" aria-hidden="true"></span><span class="wiz-compact-line">${esc(line)}</span>
          <button type="button" class="wiz-steps-button" data-action="cal-tab-batch-steps" aria-haspopup="dialog">${esc(t("wiz_T274"))}</button></div>
        <div class="wiz-columns">
          <nav class="wiz-steps" aria-label="${esc(t("wiz_T274"))}">${this._batchSteps(count)}</nav>
          <div class="wiz-main">
            <h4 class="wiz-title">${esc(t("wiz_T481"))}</h4>
            <div class="wiz-body"><p>${esc(t("wiz_T387"))}</p></div>
            <div class="cal-note is-warning cal-batch-note">${rich(t("wiz_T388"))}</div>
            ${gateways.length > 1 ? `<label class="cal-batch-gateway">${esc(t("gateway"))}<select data-batch="gateway">${gateways.map((entry) => `<option value="${esc(entry.entry_id)}" ${entry.entry_id === batch.entryId ? "selected" : ""}>${esc(entry.title)}</option>`).join("")}</select></label>` : ""}
            ${batch.error ? `<p class="notice error" role="alert">${esc(batch.error)}</p>` : ""}
            ${batch.loading ? `<p class="muted" role="status">${esc(t("loading"))}</p>` : ""}
            ${!batch.loading && !batch.error && !targets.length ? `<p class="muted">${esc(t("calBatchEmpty"))}</p>` : ""}
            ${targets.length ? `${this._filterBar({ extra: " cal-batch-filterbar", compactClass: " cal-batch-compact", label: t("wiz_T383"),
              chips: picks.map(([id, label]) => `<button type="button" class="cal-chip" data-action="cal-tab-batch-pick" data-id="${id}">${esc(label)}</button>`).join(""),
              select: `<label class="cal-compact-sort cal-compact-filter cal-compact-select"><select data-batch-pick aria-label="${esc(select)}">
                <option value="" selected>${esc(select)}</option>${picks.map(([id, label]) => `<option value="${id}">${esc(label)}</option>`).join("")}</select></label>` })}
            <div class="cal-list cal-batch-list">
              <div class="cal-batch-rows" role="group" aria-label="${esc(t("wiz_T364"))}">${rows}</div></div>
            <p class="error cal-batch-limit" role="alert">${count > max ? esc(`${t("calBatchLimit")}: ${max}`) : ""}</p>` : ""}
          </div>
          <div class="wiz-actions cal-batch-actions"><div class="cal-batch-sticky">
            <p class="cal-batch-summary" role="status">${esc(summary)}</p>
            <button type="button" class="wiz-action primary" data-action="cal-tab-batch-start" ${count === 0 || count > max || batch.loading ? "disabled" : ""}>${esc(t("wiz_T365"))}</button>
          </div></div>
        </div>
        <div class="wiz-sheet" role="dialog" aria-modal="true" aria-label="${esc(t("wiz_T274"))}" ${this._batchStepsOpen ? "" : "hidden"}><div class="wiz-sheet-card">
          <button type="button" class="icon-button wiz-sheet-close" data-action="cal-tab-batch-steps-close" aria-label="${esc(t("close"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button>
          <div class="wiz-sheet-steps">${this._batchSteps(count)}</div></div></div>
      </div>
    </div>`;
    // A new selection only patches the rows, the summary and Start: the view is not rebuilt, so the list never moves
    // under the pointer (rebuilding recreated the spacer and the browser shifted the scroll by a pixel or two).
    const structure = JSON.stringify([targets.map((target) => [target.entity_id, target.name, target.area, target.status, target.profile?.name, target.reason]),
      batch.loading, batch.error, batch.entryId, max, gateways.length, this._sort, t("wiz_T364")]);
    if (host.querySelector(".cal-batch") && this._batchStructure === structure) this._patchBatch(summary, count, max);
    else { this._batchStructure = structure; morph(host, html); }
    fitLines(host.querySelector(".cal-batch"));
    // The fade above the actions while the list goes on under them (phones, as M-5).
    const main = host.querySelector(".cal-batch .wiz-main"), actions = host.querySelector(".cal-batch .wiz-actions");
    if (main && actions && !main.dataset.watched) {
      main.dataset.watched = "1";
      const more = () => actions.classList.toggle("has-more", main.scrollHeight - main.scrollTop - main.clientHeight > 1);
      main.addEventListener("scroll", more, { passive: true });
      if (typeof ResizeObserver === "function") new ResizeObserver(more).observe(main);
      more();
    }
  }

  /** The sequence's steps, as the wizard's stepper: Selection (with how many are chosen), Run, Results. */
  _batchSteps(count) {
    const { t } = this._context;
    const chosen = count === 0 ? t("wiz_T487") : count === 1 ? t("wiz_T486") : fill(t("wiz_T485"), { count });
    const step = (label, state, sub = "") => `<li data-step-state="${state}"${state === "current" ? ' aria-current="step"' : ""}><span class="wiz-step-mark" aria-hidden="true"></span><span class="wiz-step-label">${esc(label)}</span>${sub ? `<ul><li>${esc(sub)}</li></ul>` : ""}</li>`;
    return `<p class="wiz-steps-line">${esc(fill(t("wizPhaseLine"), { phase: t("wiz_T482"), n: 1, total: 3 }))}</p>
      <ol>${step(t("wiz_T482"), "current", chosen)}${step(t("wiz_T483"), "future")}${step(t("wiz_T484"), "future")}</ol>`;
  }

  _patchBatch(summary, count, max) {
    const { host, t } = this._context, batch = this._batch;
    for (const row of host.querySelectorAll(".cal-batch-row")) {
      const place = batch.order.indexOf(row.dataset.entity), input = row.querySelector("input");
      row.classList.toggle("is-selected", place >= 0);
      if (input.checked !== place >= 0) input.checked = place >= 0;
      row.querySelector(".cal-batch-order").textContent = place >= 0 ? String(place + 1) : "";
    }
    host.querySelector(".cal-batch-summary").textContent = summary;
    const steps = this._batchSteps(count);
    for (const target of host.querySelectorAll(".cal-batch .wiz-steps, .cal-batch .wiz-sheet-steps")) if (target.innerHTML !== steps) morph(target, steps);
    const limit = host.querySelector(".cal-batch-limit");
    if (limit) limit.textContent = count > max ? `${t("calBatchLimit")}: ${max}` : "";
    host.querySelector('[data-action="cal-tab-batch-start"]').disabled = count === 0 || count > max || batch.loading;
  }

  _batchToggle(entityId, checked) {
    const batch = this._batch;
    batch.order = batch.order.filter((id) => id !== entityId);
    if (checked) batch.order.push(entityId);
    this._render();
  }

  /** Shortcuts: all available covers or those to measure, in the list's order; None clears the sequence. */
  _batchPick(kind) {
    this._batch.order = kind === "none" ? [] : this._batchTargets().filter((target) => !target.reason && (kind === "all" || target.item?.status === "to_measure"))
      .map((target) => target.entity_id);
    this._render();
  }

  /** Start: `batch_start` with the chosen order, once; the existing view runs it in a dialog for now. */
  _batchStart() {
    const batch = this._batch, ids = [...batch.order];
    if (batch.starting || !ids.length || ids.length > (batch.data?.max_batch ?? 0)) return;
    batch.starting = true;
    const { hass, t } = this._context;
    this._mode = { kind: "list" };
    this._batch = null;
    this._context.host.innerHTML = "";
    this._render();
    const body = this._openDialog({ title: t("wiz_T364"), icon: "mdi:format-list-numbered" });
    this._calibration.open({ host: body, hass, t, entity: { entry_id: batch.entryId }, mode: "automatic", entity_ids: ids, revision: batch.data.revision,
      onCancel: () => this._dialogDone(), onSaved: () => this._dialogDone() });
  }

  _batchBack() {
    this._batch = null;
    this._backToList();
  }
}
