/** WHO 2 "Calibration" view: what each timed cover uses, its measurement state and the ways to measure it. */
const asset = (name) => { const url = new URL(name, import.meta.url); url.search = new URL(import.meta.url).search; return url.href; };
const [{ escapeHtml: esc, replacePreservingFocus }, model, text, { CoverCalibration }, { CalibrationWizard }] = await Promise.all([
  import(asset("panel-dom.js")), import(asset("panel-model.js")), import(asset("panel-calibration-text.js")),
  import(asset("panel-cover-calibration.js")), import(asset("panel-calibration-wizard.js")),
]);
const { fill, rich, number, dateText, names } = text;

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
    this._generation = 0; this._rows = new Map(); this._unsubs = []; this._expanded = new Set();
    this._filter = "all"; this._sort = savedSort(); this._menu = null; this._mode = { kind: "list" }; this._hosts = new WeakSet();
    this._calibration = new CoverCalibration();
    this._wizard = new CalibrationWizard();
  }

  /** Replace the wizard (tests use a faster preview); `null` leaves only sessions and groups. */
  useWizard(wizard) { this._wizard?.close(); this._wizard = wizard; }

  clear() {
    this._generation++;
    this._closeDialog();
    for (const unsubscribe of this._unsubs.splice(0)) Promise.resolve(unsubscribe()).catch(() => {});
    this._calibration.close();
    this._wizard?.close();
    this._rows.clear();
    this._mode = { kind: "list" };
    this._batch = null;
    this._unwatchBar();
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
    if (!this._hosts.has(context.host)) {
      this._hosts.add(context.host);
      context.host.addEventListener("click", (event) => this._click(event));
      context.host.addEventListener("keydown", (event) => this._keydown(event));
      context.host.addEventListener("change", (event) => this._change(event));
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
    }
    const select = event.target.closest?.("select[data-sort]");
    if (!select || !["list", "batch"].includes(this._mode.kind)) return;
    const field = select.dataset.sort;
    if (field === "key") this._setSort(select.value, this._sort.key === select.value ? this._sort.dir : "asc");
    else this._setSort(this._sort.key, select.value === "desc" ? "desc" : "asc");
  }

  /** The phone's "Sort by" bar: column and order, the same choices as the headers. */
  _sortBar() {
    const { t } = this._context;
    return `<div class="cal-sort-bar">
          <label>${esc(t("wiz_T379"))} <select data-sort="key">${SORT_KEYS.map((key) => `<option value="${key}" ${this._sort.key === key ? "selected" : ""}>${esc(t({ cover: "calTabColCover", status: "calTabColStatus", profile: "calTabColProfile" }[key]))}</option>`).join("")}</select></label>
          <label><span class="visually-hidden">${esc(t("wiz_T380"))}</span><select data-sort="dir">${["asc", "desc"].map((dir) => `<option value="${dir}" ${this._sort.dir === dir ? "selected" : ""}>${esc(t(dir === "asc" ? "wiz_T381" : "wiz_T382"))}</option>`).join("")}</select></label></div>`;
  }

  /** The header row of a list: Roller shutter, Status and Profile sort it. */
  _sortHeads(extra = "") {
    const { t } = this._context;
    return `<div class="cal-list-head${extra}" role="group" aria-label="${esc(t("wiz_T379"))}"><span></span>${this._sortHead("cover", t("calTabColCover"))}${this._sortHead("status", t("calTabColStatus"))}${this._sortHead("profile", t("calTabColProfile"))}<span></span></div>`;
  }

  /** A column header: a button that sorts by it, with the arrow of the current order. */
  _sortHead(key, label) {
    const { t } = this._context;
    const active = this._sort.key === key, dir = this._sort.dir;
    return `<span class="cal-sort-cell"><button type="button" class="cal-sort" data-action="cal-tab-sort" data-id="${key}" aria-pressed="${active}">${esc(label)}${active
      ? `<ha-icon icon="mdi:arrow-${dir === "asc" ? "up" : "down"}" aria-hidden="true"></ha-icon><span class="visually-hidden">, ${esc(t(dir === "asc" ? "wiz_T381" : "wiz_T382"))}</span>` : ""}</button></span>`;
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
      html = `<div class="empty cal-tab-empty"><h2>${esc(t("calTabEmptyTitle"))}</h2><p class="muted">${esc(t("calTabEmptyBody"))}</p>
        <details class="profile-meta"><summary>${esc(t("calTabHowItWorks"))}</summary><p class="muted">${esc(t("calTabHowItWorksBody"))}</p></details></div>`;
    } else {
      // The buttons line up with the introduction, not with the title above it.
      html = `<h3 class="cal-tab-title">${esc(t("calTabTitle"))}</h3><div class="cal-tab-head"><p class="muted cal-tab-intro">${esc(t("calTabIntro"))}</p>
        <div class="actions cal-tab-actions">
          <button type="button" data-action="cal-tab-batch" ${busy || loading ? "disabled" : ""}><ha-icon icon="mdi:format-list-numbered" aria-hidden="true"></ha-icon><span>${esc(t("wiz_T363"))}</span></button>
          ${this._wizard ? `<button type="button" class="primary" data-action="cal-tab-measure" ${busy || loading || !counts.all ? "disabled" : ""}><ha-icon icon="mdi:window-shutter-settings" aria-hidden="true"></ha-icon><span>${esc(t("calTabMeasureOne"))}</span></button>` : ""}
        </div></div>
        <div class="cal-tab-filters"><div class="cal-tab-chips" role="group" aria-label="${esc(t("calTabFilterLabel"))}">${FILTERS.map((filter) =>
          `<button type="button" class="cal-chip" data-action="cal-tab-filter" data-id="${filter}" aria-pressed="${this._filter === filter}">${esc(t(`calTabFilter_${filter}`))} <span class="count">${counts[filter]}</span></button>`).join("")}</div>
          <p class="muted cal-tab-summary" role="status">${esc([["calTabCountCovers", counts.all], ["calTabCountCalibrated", counts.calibrated], ["calTabCountToMeasure", counts.to_measure]]
            .map(([key, count]) => fill(t(count === 1 ? `${key}_one` : key), { n: count })).join(" · "))}</p></div>
        ${this._done ? `<p class="notice cal-tab-done" role="status"><ha-icon icon="mdi:check-circle-outline" aria-hidden="true"></ha-icon><span>${esc(this._done)}</span></p>` : ""}
        ${busy ? `<p class="notice cal-tab-busy" role="status"><ha-icon icon="mdi:information-outline" aria-hidden="true"></ha-icon><span>${esc(t("calTabBusy"))}</span></p>` : ""}
        ${this._filter === "to_measure" ? `<p class="cal-note cal-tab-help">${esc(t("calTabToMeasureHelp"))}</p>` : ""}
        ${failed.map((entry) => `<p class="notice error" role="alert">${esc(gateways.length > 1 ? `${entry.title}: ` : "")}${esc(t("calTabError"))}</p>`).join("")}
        ${failed.length ? `<button type="button" data-action="cal-tab-refresh">${esc(t("refresh"))}</button>` : ""}
        ${loading ? `<p class="muted" role="status">${esc(t("loading"))}</p>` : ""}
        ${visible.length || loading ? "" : `<p class="muted">${esc(t("noResults"))}</p>`}
        ${visible.length ? `${this._sortBar()}
        <div class="cal-list">
          ${this._sortHeads()}
          <div class="cal-list-rows" role="list">${visible.map((item) => this._row(item, busy, language)).join("")}</div></div>` : ""}`;
    }
    if (host.innerHTML !== html) replacePreservingFocus(host, html);
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
          <span class="cal-row-name"><strong>${esc(item.name)}</strong><span class="muted">${esc([this._area(item), gateways.length > 1 ? item.entry.title : ""].filter(Boolean).join(" · "))}${this._address(item)}<span class="cal-row-last-inline"> · ${esc(last || t("calTabNeverMeasured"))}</span></span></span></button>
        <span class="cal-row-status">${badge}</span>
        <span class="cal-row-profile">${profile}</span>
        <span class="cal-row-actions">${action}
          <span class="cal-menu-wrap"><button type="button" class="icon-button" data-action="cal-tab-menu" data-id="${esc(key)}" aria-haspopup="menu" aria-expanded="${menuOpen}" aria-label="${esc(t("calTabMore"))}: ${esc(item.name)}" title="${esc(t("calTabMore"))}"><ha-icon icon="mdi:dots-vertical" aria-hidden="true"></ha-icon></button>
          <span class="cal-menu" role="menu" ${menuOpen ? "" : "hidden"}>
            ${!session && this._wizard && item.rolls ? `<button type="button" role="menuitem" data-action="cal-tab-refine" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="mdi:target" aria-hidden="true"></ha-icon>${esc(t("calTabActionRefine"))}</button>` : ""}
            ${!session && this._wizard ? `<button type="button" role="menuitem" data-action="cal-tab-measure-cover" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="${item.status === "to_measure" ? "mdi:tape-measure" : "mdi:reload"}" aria-hidden="true"></ha-icon>${esc(t(item.status === "to_measure" ? "calTabActionMeasure" : "calTabActionRemeasure"))}</button>` : ""}
            <button type="button" role="menuitem" data-action="cal-tab-assign" data-id="${esc(key)}"><ha-icon icon="mdi:link-variant" aria-hidden="true"></ha-icon>${esc(t("calTabAssign"))}</button>
            <button type="button" role="menuitem" data-action="cal-tab-toggle" data-id="${esc(key)}"><ha-icon icon="mdi:information-outline" aria-hidden="true"></ha-icon>${esc(t("calTabDetails"))}</button>
          </span></span></span>
      </div>
      <div class="cal-row-details" id="${esc(id)}" ${expanded ? "" : "hidden"}>${expanded ? this._details(item, busy, language, addressDetails) : ""}</div>
    </div>`;
  }

  /** "· Address: 86 · A: 8 · PL: 6" with the device cards' style: grey labels, dark values. */
  _address(item) {
    const address = item.entity?.address, { t } = this._context;
    if (!address?.raw) return "";
    const fields = [[t("address"), address.raw], ...(address.a != null && address.pl != null ? [["A", address.a], ["PL", address.pl]] : [])];
    return `<span class="cal-row-address"> · ${fields.map(([label, value]) => `<span><span class="cal-row-address-label">${esc(label)}:</span> <span class="cal-row-address-value">${esc(value)}</span></span>`).join(" · ")}</span>`;
  }

  _area(item) { return item.area; }

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
    const measure = this._wizard ? `<button type="button" class="${item.rolls ? "" : "primary"}" data-action="cal-tab-measure-cover" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="${item.status === "to_measure" ? "mdi:tape-measure" : "mdi:reload"}" aria-hidden="true"></ha-icon>${esc(t(item.status === "to_measure" ? "calTabActionMeasure" : "calTabActionRemeasure"))}</button>` : "";
    const assign = `<button type="button" data-action="cal-tab-assign" data-id="${esc(key)}"><ha-icon icon="mdi:link-variant" aria-hidden="true"></ha-icon>${esc(t("calTabAssign"))}</button>`;
    return `<div class="cal-details-grid">
        <section><h4>${esc(t("calTabValues"))}</h4>${list(rows)}${this._originNote(item, language)}${action(refine)}</section>
        <section><h4>${esc(t("calTabColLast"))}</h4>${list([[t("calTabDate"), item.last ? dateText(item.last, language) : "—"],
          [t("calTabMethod"), t(`calTabMethod_${item.method || "none"}`)]])}
          ${item.profile && scaled ? `<p class="cal-note">${esc(fill(t("calTabInheritedNote"), { profile: item.profile.name }))}</p>` : ""}${action(measure)}</section>
        <section><h4>${esc(t("calTabColProfile"))}</h4>${item.profile ? `<p><span class="chip cal-profile-chip"><ha-icon icon="mdi:circle" aria-hidden="true"></ha-icon>${esc(item.profile.name)}</span></p>
          <p>${esc(followers.length ? fill(t("calTabFollowers"), { names: names(followers, language) }) : t("calTabFollowersNone"))}</p>
          <p class="cal-note">${esc(t("calTabProfileNote"))}</p>` : `<p class="muted">${esc(t("calTabProfileNone"))}</p>`}${action(assign)}</section>
      </div>`;
  }

  /** Where the times of a never measured cover come from: the integration's default or the YAML configuration. */
  _originNote(item, language) {
    const effective = item.cover.effective, origin = effective.opening?.origin;
    if (item.status !== "to_measure" || !["default", "yaml"].includes(origin) || effective.closing?.origin !== origin) return "";
    const [opening, closing] = [effective.opening.value, effective.closing.value].map((value) => number(value, language));
    return `<p class="cal-note cal-origin-note">${esc(fill(this._context.t(origin === "yaml" ? "wiz_T378" : "wiz_T377"),
      { seconds: opening === closing ? opening : `${opening} / ${closing}` }))}</p>`;
  }

  _item(key) {
    const [entryId, entityId] = JSON.parse(key);
    return this._covers().find((item) => item.entry.entry_id === entryId && item.cover.entity_id === entityId);
  }

  _keydown(event) {
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
      const button = event.target.closest("button[data-action]");
      if (!button) return;
      const { action, id } = button.dataset;
      if (action === "cal-tab-batch-back") this._batchBack();
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
    else if (action === "cal-tab-toggle") {
      if (this._expanded.has(id)) this._expanded.delete(id); else this._expanded.add(id);
      this._render();
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
    this._mode = { kind: "list" };
    if (!this._context) return;
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
      onOpenCover: (entityId) => onOpenCover?.(entityId),
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
    dialog.showModal();
    this._dialog = dialog;
    return dialog.querySelector(".cal-dialog-body");
  }

  _closeDialog() {
    this._calibration.close();
    this._dialog?.close();
    this._dialog?.remove();
    this._dialog = null;
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

  _dialogDone() {
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
    const body = this._openDialog({ title: t("calTabAssign"), subtitle: item.name, icon: "mdi:link-variant" });
    const dialog = this._dialog, generation = this._generation;
    const profiles = [...data.profiles].sort((a, b) => a.name.localeCompare(b.name));
    const followers = (count) => fill(t(count === 0 ? "wiz_T374" : count === 1 ? "wiz_T375" : "wiz_T376"), { count });
    const describe = (profile) => {
      const slat = profile.geometry?.slat_time_s;
      const origin = profile.provenance?.opening;
      return [
        [t(slat == null ? "wiz_T370" : slat > 0 ? "wiz_T368" : "wiz_T369"),
          profile.reference_travel_cm != null ? fill(t("wiz_T372"), { cm: number(profile.reference_travel_cm, language) }) : ""].filter(Boolean).join(" · "),
        [origin?.recorded_at && (origin.origin_entity_id || origin.origin_name)
          ? fill(t("wiz_T371"), { cover: this._originName(origin), date: dateText(origin.recorded_at, language) }) : "",
          followers(profile.assigned_to.filter(Boolean).length)].filter(Boolean).join(" · "),
      ];
    };
    // "No profile" unlinks the profile the cover follows; never on the cover the profile was measured on, whose values
    // live only in the profile until Home Assistant copies them on unlinking (backend lot to plan).
    const followed = data.profiles.find((profile) => profile.id === item.cover.profile_id);
    const source = followed?.provenance?.opening?.origin_entity_id === item.cover.entity_id;
    const none = followed && !source ? `<label class="wiz-radio cal-assign-none"><input type="radio" name="assign_profile" value="${NO_PROFILE}">
        <span><strong><ha-icon icon="mdi:link-variant-off" aria-hidden="true"></ha-icon>${esc(t("wiz_T404"))}</strong><small class="muted">${esc(fill(t("wiz_T405"), { profile: followed.name }))}</small></span></label>` : "";
    body.innerHTML = profiles.length ? `<fieldset class="wiz-radios cal-assign-list"><legend>${esc(t("wiz_T163"))}</legend>${none}${profiles.map((profile) => {
      const [type, measured] = describe(profile);
      return `<label class="wiz-radio"><input type="radio" name="assign_profile" value="${esc(profile.id)}" ${profile.id === item.cover.profile_id ? "checked" : ""}>
        <span><strong>${esc(profile.name)}</strong><small class="muted">${esc(type)}</small><small class="muted">${esc(measured)}</small></span></label>`;
    }).join("")}</fieldset>
      <p class="error" role="alert" hidden></p>`
      : `<p class="muted">${esc(t("profileListEmpty"))}</p>`;
    if (!profiles.length) return;
    // In the footer, on one row with Close, as in the other dialogs.
    dialog.querySelector(".dialog-foot").insertAdjacentHTML("beforeend", `<button type="button" class="primary" data-assign disabled>${esc(t("wiz_T373"))}</button>`);
    const button = dialog.querySelector("[data-assign]");
    const chosen = () => body.querySelector('input[name="assign_profile"]:checked')?.value;
    body.onchange = () => {
      button.disabled = !chosen() || chosen() === item.cover.profile_id;
      // Unlinking is said as such on the button, with the broken link.
      button.innerHTML = chosen() === NO_PROFILE ? `<ha-icon icon="mdi:link-variant-off" aria-hidden="true"></ha-icon><span>${esc(t("wiz_T406"))}</span>` : esc(t("wiz_T373"));
    };
    button.onclick = async () => {
      const choice = chosen();
      if (!choice || button.disabled) return;
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
        button.disabled = false;
      }
    };
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
        <span class="cal-row-name"><strong>${esc(target.name)}</strong><span class="muted">${esc(target.area)}${this._address({ entity: target.entity })}${target.reason ? ` · ${esc(t(`profileError_${target.reason}`))}` : ""}</span></span>
        <span class="cal-batch-status">${statusBadge(target.item)}</span>
        <span class="cal-batch-profile">${profile(target.item)}</span></label>`;
    }).join("");
    const summary = count === 0 ? t("wiz_T386") : count === 1 ? t("wiz_T385") : fill(t("wiz_T384"), { count });
    const html = `<div class="cal-batch">
      <button type="button" class="link cal-batch-back" data-action="cal-tab-batch-back"><ha-icon icon="mdi:arrow-left" aria-hidden="true"></ha-icon>${esc(t("wiz_T390"))}</button>
      <h3 class="cal-tab-title">${esc(t("wiz_T364"))}</h3>
      <p class="muted cal-tab-intro">${esc(t("wiz_T387"))}</p>
      <div class="cal-note is-warning cal-batch-note">${rich(t("wiz_T388"))}</div>
      ${gateways.length > 1 ? `<label class="cal-batch-gateway">${esc(t("gateway"))}<select data-batch="gateway">${gateways.map((entry) => `<option value="${esc(entry.entry_id)}" ${entry.entry_id === batch.entryId ? "selected" : ""}>${esc(entry.title)}</option>`).join("")}</select></label>` : ""}
      ${batch.error ? `<p class="notice error" role="alert">${esc(batch.error)}</p>` : ""}
      ${batch.loading ? `<p class="muted" role="status">${esc(t("loading"))}</p>` : ""}
      ${!batch.loading && !batch.error && !targets.length ? `<p class="muted">${esc(t("calBatchEmpty"))}</p>` : ""}
      ${targets.length ? `<div class="cal-batch-tools"><p class="cal-batch-shortcuts"><span class="muted">${esc(t("wiz_T383"))}</span>
          <button type="button" class="cal-chip" data-action="cal-tab-batch-pick" data-id="all">${esc(t("calTabFilter_all"))}</button>
          <button type="button" class="cal-chip" data-action="cal-tab-batch-pick" data-id="to_measure">${esc(t("calTabFilter_to_measure"))}</button>
          <button type="button" class="cal-chip" data-action="cal-tab-batch-pick" data-id="none">${esc(t("wiz_T391"))}</button></p>
          <p class="muted cal-batch-capacity">${esc(fill(t("wiz_T389"), { count: targets.length, max }))}</p></div>
        ${this._sortBar()}
        <div class="cal-list cal-batch-list">
          ${this._sortHeads(" cal-batch-head")}
          <div class="cal-batch-rows" role="group" aria-label="${esc(t("wiz_T364"))}">${rows}</div></div>
        <p class="error cal-batch-limit" role="alert">${count > max ? esc(`${t("calBatchLimit")}: ${max}`) : ""}</p>` : ""}
      <span class="cal-batch-sentinel" aria-hidden="true"></span>
      <span class="cal-batch-spacer" aria-hidden="true"${this._spacer != null ? ` style="height: ${this._spacer}px"` : ""}></span>
      <div class="cal-batch-bar"><p class="cal-batch-summary" role="status">${esc(summary)}</p>
        <div class="cal-batch-actions"><button type="button" class="cal-batch-cancel" data-action="cal-tab-batch-back">${esc(t("cancel"))}</button>
        <button type="button" class="primary" data-action="cal-tab-batch-start" ${count === 0 || count > max || batch.loading ? "disabled" : ""}><ha-icon icon="mdi:format-list-numbered" aria-hidden="true"></ha-icon>${esc(t("wiz_T365"))}</button></div></div>
    </div>`;
    // A new selection only patches the rows, the summary and Start: the view is not rebuilt, so the list never moves
    // under the pointer (rebuilding recreated the spacer and the browser shifted the scroll by a pixel or two).
    const structure = JSON.stringify([targets.map((target) => [target.entity_id, target.name, target.area, target.status, target.profile?.name, target.reason]),
      batch.loading, batch.error, batch.entryId, max, gateways.length, this._sort, t("wiz_T364")]);
    if (host.querySelector(".cal-batch") && this._batchStructure === structure) this._patchBatch(summary, count, max);
    else { this._batchStructure = structure; replacePreservingFocus(host, html); }
    this._watchBar();
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
    const limit = host.querySelector(".cal-batch-limit");
    if (limit) limit.textContent = count > max ? `${t("calBatchLimit")}: ${max}` : "";
    host.querySelector('[data-action="cal-tab-batch-start"]').disabled = count === 0 || count > max || batch.loading;
  }

  /**
   * The action bar is fixed to the bottom of the window, over the width of the view: a sticky bar would follow the
   * panel's own scroll box, which inside Home Assistant is not the box that scrolls. A spacer of its height ends the
   * view so the last row is never hidden; the fade shows while the end of the list is below the window's edge.
   */
  _watchBar() {
    const { host } = this._context;
    const view = host.querySelector(".cal-batch"), sentinel = host.querySelector(".cal-batch-sentinel");
    if (!view || !host.querySelector(".cal-batch-bar")) return;
    if (this._barView !== view) {
      this._unwatchBar();
      this._barView = view;
      const place = () => {
        const box = view.getBoundingClientRect(), bar = host.querySelector(".cal-batch-bar"), spacer = host.querySelector(".cal-batch-spacer");
        if (!bar) return;
        bar.style.left = `${Math.round(box.left)}px`;
        bar.style.width = `${Math.round(box.width)}px`;
        if (!spacer) return;
        // The end of the list stops just above the bar: the spacer covers the bar's height, less what the page already
        // has under the view (the panel's bottom padding, its empty status line).
        const end = host.closest("main") || host.parentElement;
        const below = end ? Math.max(0, end.getBoundingClientRect().bottom - box.bottom) : 0;
        const height = Math.max(0, Math.ceil(bar.getBoundingClientRect().height - below));
        if (this._spacer !== height) { this._spacer = height; spacer.style.height = `${height}px`; }
      };
      this._barPlace = place;
      window.addEventListener("resize", place);
      if (typeof ResizeObserver === "function") {
        this._barResize = new ResizeObserver(place);
        this._barResize.observe(view);
        this._barResize.observe(host.querySelector(".cal-batch-bar"));
      }
    }
    this._barPlace();
    this._barObserver?.disconnect();
    if (!sentinel || typeof IntersectionObserver !== "function") return;
    this._barObserver = new IntersectionObserver(([entry]) => host.querySelector(".cal-batch-bar")?.classList.toggle("has-more", !entry.isIntersecting),
      { threshold: 0 });
    this._barObserver.observe(sentinel);
  }

  _unwatchBar() {
    this._barObserver?.disconnect();
    this._barResize?.disconnect();
    if (this._barPlace) window.removeEventListener("resize", this._barPlace);
    this._barObserver = this._barResize = this._barPlace = this._barView = null;
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
    this._unwatchBar();
    this._context.host.innerHTML = "";
    this._render();
    const body = this._openDialog({ title: t("wiz_T364"), icon: "mdi:format-list-numbered" });
    this._calibration.open({ host: body, hass, t, entity: { entry_id: batch.entryId }, mode: "automatic", entity_ids: ids, revision: batch.data.revision,
      onCancel: () => this._dialogDone(), onSaved: () => this._dialogDone() });
  }

  _batchBack() {
    this._batch = null;
    this._unwatchBar();
    this._backToList();
  }
}
