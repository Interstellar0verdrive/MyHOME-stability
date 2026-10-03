/** WHO 2 "Calibration" view: what each timed cover uses, its measurement state and the ways to measure it. */
const asset = (name) => { const url = new URL(name, import.meta.url); url.search = new URL(import.meta.url).search; return url.href; };
const [{ escapeHtml: esc, replacePreservingFocus }, model, text, { CoverCalibration }, { CalibrationWizard }] = await Promise.all([
  import(asset("panel-dom.js")), import(asset("panel-model.js")), import(asset("panel-calibration-text.js")),
  import(asset("panel-cover-calibration.js")), import(asset("panel-calibration-wizard.js")),
]);
const { fill, number, dateText, names } = text;

const MEASURED = ["guided", "automatic"];
export const FILTERS = ["all", "to_measure", "calibrated", "profile"];
// Covers read in turn to find the gateway's session when a read fails.
const SESSION_PROBES = 3;

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
    this._filter = "all"; this._menu = null; this._mode = { kind: "list" }; this._hosts = new WeakSet();
    this._calibration = new CoverCalibration();
    this._wizard = new CalibrationWizard();
  }

  /** Replace the wizard (tests use a faster preview); `null` leaves only sessions and groups. */
  useWizard(wizard) { this._wizard?.close(); this._wizard = wizard; }

  clear() {
    this._generation++;
    for (const unsubscribe of this._unsubs.splice(0)) Promise.resolve(unsubscribe()).catch(() => {});
    this._calibration.close();
    this._wizard?.close();
    this._rows.clear();
    this._mode = { kind: "list" };
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
        return { entry, cover, entity, profile, revision: row.data.revision, session: row.session,
          name: entity ? model.entityName(entity, hass) : cover.name, ...coverStatus(cover) };
      });
    }).sort((a, b) => a.name.localeCompare(b.name));
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
    if (!this._context?.host.isConnected || this._mode.kind !== "list") return;
    if (this._openPendingWizard()) return;
    const { host, t, hass, gateways } = this._context;
    const language = hass.language || "en";
    const loading = gateways.some((entry) => !this._rows.get(entry.entry_id)?.data && !this._rows.get(entry.entry_id)?.error && !this._rows.get(entry.entry_id)?.removed);
    const failed = gateways.filter((entry) => this._rows.get(entry.entry_id)?.error);
    const all = this._covers().filter((item) => this._matches(item));
    const counts = { all: all.length, to_measure: all.filter((item) => item.status === "to_measure").length,
      calibrated: all.filter((item) => item.status !== "to_measure").length, profile: all.filter((item) => item.profile).length };
    const visible = all.filter((item) => this._filter === "all" || (this._filter === "to_measure" ? item.status === "to_measure"
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
          <button type="button" data-action="cal-tab-batch" ${busy || loading ? "disabled" : ""}><ha-icon icon="mdi:select-group" aria-hidden="true"></ha-icon><span>${esc(t("calTabMeasureGroup"))}</span></button>
          ${this._wizard ? `<button type="button" class="primary" data-action="cal-tab-measure" ${busy || loading || !counts.all ? "disabled" : ""}><ha-icon icon="mdi:window-shutter-settings" aria-hidden="true"></ha-icon><span>${esc(t("calTabMeasureOne"))}</span></button>` : ""}
        </div></div>
        <div class="cal-tab-filters"><div class="cal-tab-chips" role="group" aria-label="${esc(t("calTabFilterLabel"))}">${FILTERS.map((filter) =>
          `<button type="button" class="cal-chip" data-action="cal-tab-filter" data-id="${filter}" aria-pressed="${this._filter === filter}">${esc(t(`calTabFilter_${filter}`))} <span class="count">${counts[filter]}</span></button>`).join("")}</div>
          <p class="muted cal-tab-summary" role="status">${esc([["calTabCountCovers", counts.all], ["calTabCountCalibrated", counts.calibrated], ["calTabCountToMeasure", counts.to_measure]]
            .map(([key, count]) => fill(t(count === 1 ? `${key}_one` : key), { n: count })).join(" · "))}</p></div>
        ${busy ? `<p class="notice cal-tab-busy" role="status"><ha-icon icon="mdi:information-outline" aria-hidden="true"></ha-icon><span>${esc(t("calTabBusy"))}</span></p>` : ""}
        ${this._filter === "to_measure" ? `<p class="notice cal-tab-help"><ha-icon icon="mdi:information-outline" aria-hidden="true"></ha-icon><span>${esc(t("calTabToMeasureHelp"))}</span></p>` : ""}
        ${failed.map((entry) => `<p class="notice error" role="alert">${esc(gateways.length > 1 ? `${entry.title}: ` : "")}${esc(t("calTabError"))}</p>`).join("")}
        ${failed.length ? `<button type="button" data-action="cal-tab-refresh">${esc(t("refresh"))}</button>` : ""}
        ${loading ? `<p class="muted" role="status">${esc(t("loading"))}</p>` : ""}
        ${visible.length || loading ? "" : `<p class="muted">${esc(t("noResults"))}</p>`}
        ${visible.length ? `<div class="cal-list" role="list">
          <div class="cal-list-head" aria-hidden="true"><span>${esc(t("calTabColCover"))}</span><span>${esc(t("calTabColStatus"))}</span><span>${esc(t("calTabColProfile"))}</span><span>${esc(t("calTabColLast"))}</span><span></span></div>
          ${visible.map((item) => this._row(item, busy, language)).join("")}</div>` : ""}`;
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
      ? (session.waiting_for_stop || session.recoverable === false ? "" : `<button type="button" class="ghost cal-row-action" data-action="cal-tab-session" data-id="${esc(item.entry.entry_id)}">${esc(t("calOpenSession"))}</button>`)
      : this._wizard ? `<button type="button" class="ghost cal-row-action" data-action="cal-tab-${item.rolls ? "refine" : "measure-cover"}" data-id="${esc(key)}" ${busy ? "disabled" : ""}>${esc(t(item.rolls ? "calTabActionRefine" : "calTabActionMeasure"))}</button>` : "";
    const menuOpen = this._menu === key;
    return `<div class="cal-row${session ? " is-running" : ""}${expanded ? " is-expanded" : ""}" role="listitem" data-entity="${esc(item.cover.entity_id)}" data-entry="${esc(item.entry.entry_id)}">
      <div class="cal-row-main">
        <button type="button" class="cal-row-toggle" data-action="cal-tab-toggle" data-id="${esc(key)}" aria-expanded="${expanded}" aria-controls="${esc(id)}">
          <ha-icon class="cal-row-chevron" icon="mdi:chevron-right" aria-hidden="true"></ha-icon><span class="cal-row-icon" aria-hidden="true"><ha-icon icon="mdi:window-shutter"></ha-icon></span>
          <span class="cal-row-name"><strong>${esc(item.name)}</strong><span class="muted">${esc([this._area(item), gateways.length > 1 ? item.entry.title : ""].filter(Boolean).join(" · "))}${this._address(item)}<span class="cal-row-last-inline"> · ${esc(last || t("calTabNeverMeasured"))}</span></span></span></button>
        <span class="cal-row-status">${badge}</span>
        <span class="cal-row-profile">${profile}</span>
        <span class="cal-row-last muted">${esc(session ? "—" : last || "—")}</span>
        <span class="cal-row-actions">${action}
          <span class="cal-menu-wrap"><button type="button" class="icon-button" data-action="cal-tab-menu" data-id="${esc(key)}" aria-haspopup="menu" aria-expanded="${menuOpen}" aria-label="${esc(t("calTabMore"))}: ${esc(item.name)}" title="${esc(t("calTabMore"))}"><ha-icon icon="mdi:dots-vertical" aria-hidden="true"></ha-icon></button>
          <span class="cal-menu" role="menu" ${menuOpen ? "" : "hidden"}>
            <button type="button" role="menuitem" data-action="cover-profile" data-id="${esc(item.cover.entity_id)}"><ha-icon icon="mdi:pencil-outline" aria-hidden="true"></ha-icon>${esc(t("calTabAssign"))}</button>
            <button type="button" role="menuitem" data-action="cal-tab-toggle" data-id="${esc(key)}"><ha-icon icon="mdi:information-outline" aria-hidden="true"></ha-icon>${esc(t("calTabDetails"))}</button>
          </span></span></span>
      </div>
      <div class="cal-row-details" id="${esc(id)}" ${expanded ? "" : "hidden"}>${expanded ? this._details(item, busy, language, addressDetails) : ""}</div>
    </div>`;
  }

  /** "· Address: 86  A: 8  PL: 6" as the device cards show it: grey labels, dark values. */
  _address(item) {
    const address = item.entity?.address, { t } = this._context;
    if (!address?.raw) return "";
    const fields = [[t("address"), address.raw], ...(address.a != null && address.pl != null ? [["A", address.a], ["PL", address.pl]] : [])];
    return `<span class="cal-row-address"> · ${fields.map(([label, value]) => `<span><span class="cal-row-address-label">${esc(label)}:</span> <span class="cal-row-address-value">${esc(value)}</span></span>`).join(" ")}</span>`;
  }

  _area(item) {
    const { inventory } = this._context;
    const id = item.entity ? model.effectiveArea(item.entity, inventory.devices) : "";
    return inventory.areas.find((area) => area.id === id)?.name || "";
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
    return `<div class="cal-details-grid">
        <section><h4>${esc(t("calTabValues"))}</h4>${list(rows)}</section>
        <section><h4>${esc(t("calTabColLast"))}</h4>${list([[t("calTabDate"), item.last ? dateText(item.last, language) : "—"],
          [t("calTabMethod"), t(`calTabMethod_${item.method || "none"}`)]])}
          ${item.profile && scaled ? `<p class="muted">${esc(fill(t("calTabInheritedNote"), { profile: item.profile.name }))}</p>` : ""}</section>
        <section><h4>${esc(t("calTabColProfile"))}</h4>${item.profile ? `<p><span class="chip cal-profile-chip"><ha-icon icon="mdi:circle" aria-hidden="true"></ha-icon>${esc(item.profile.name)}</span></p>
          <p>${esc(followers.length ? fill(t("calTabFollowers"), { names: names(followers, language) }) : t("calTabFollowersNone"))}</p>
          <p class="muted">${esc(t("calTabProfileNote"))}</p>` : `<p class="muted">${esc(t("calTabProfileNone"))}</p>`}</section>
      </div>
      <div class="actions cal-details-actions">
        ${this._wizard && item.rolls ? `<button type="button" class="primary" data-action="cal-tab-refine" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="mdi:tune-variant" aria-hidden="true"></ha-icon>${esc(t("calTabActionRefine"))}</button>` : ""}
        ${this._wizard ? `<button type="button" class="${item.rolls ? "" : "primary"}" data-action="cal-tab-measure-cover" data-id="${esc(key)}" ${busy ? "disabled" : ""}><ha-icon icon="mdi:reload" aria-hidden="true"></ha-icon>${esc(t(item.status === "to_measure" ? "calTabActionMeasure" : "calTabActionRemeasure"))}</button>` : ""}
        <button type="button" data-action="cover-profile" data-id="${esc(item.cover.entity_id)}"><ha-icon icon="mdi:pencil-outline" aria-hidden="true"></ha-icon>${esc(t("calTabAssign"))}</button>
      </div>`;
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
    if (this._mode.kind !== "list") return;
    const target = event.target.closest("button");
    // The whole row opens and closes its details, as the maintainer's device cards do; its buttons keep their own action.
    const row = !target && !event.target.closest(".cal-menu, a, input, select") && event.target.closest(".cal-row-main");
    if (row) { row.querySelector('[data-action="cal-tab-toggle"]')?.click(); return; }
    if (!target) return;
    const { action, id } = target.dataset;
    if (action !== "cal-tab-menu" && this._menu !== null) { this._menu = null; if (!action?.startsWith("cal-tab-")) this._render(); }
    if (action === "cal-tab-filter") { this._filter = id; this._render(); }
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
    this._mode = { kind: "wizard" };
    const { host, hass, t, onOpenCover } = this._context;
    this._wizard.open({ host, hass, t, covers: this._covers(), data: (entryId) => this._rows.get(entryId)?.data, ...options,
      onOpenCover: (entityId) => onOpenCover?.(entityId),
      onClose: () => this._backToList() });
  }

  /** The gateway's open session: the wizard for its own modes, the existing view for the others. */
  _openSession(entryId) {
    const row = this._rows.get(entryId), session = row?.session;
    if (!session || !this._context) return;
    const item = this._covers().find((entry) => entry.entry.entry_id === entryId && entry.cover.entity_id === session.entity_id);
    // The wizard needs the cover in the list (name, gateway); otherwise the existing view opens it.
    if (item && this._wizard?.handles?.(session)) { this._openWizard({ start: "resume", session, item }); return; }
    this._mode = { kind: "session" };
    const { host, hass, t } = this._context;
    this._calibration.open({ host, hass, t, entity: { entry_id: entryId, entity_id: session.entity_id }, resume: session,
      revision: row.data?.revision, onCancel: () => this._backToList(), onSaved: () => this._backToList() });
    this._appendBack(host);
  }

  _appendBack(host) {
    const back = document.createElement("button");
    back.type = "button";
    back.className = "ghost cal-tab-back";
    back.textContent = `← ${this._context.t("calTabBack")}`;
    // Leaving the view detaches like closing the profile dialog: the session keeps running in Home Assistant.
    back.onclick = () => { this._calibration.close(); this._backToList(); };
    host.prepend(back);
  }

  /** A group: the existing selection and automatic batch, with the same messages as the profile dialog. */
  async _selectBatch() {
    const { host, hass, t, gateways } = this._context;
    const generation = this._generation;
    this._mode = { kind: "batch" };
    host.innerHTML = `<div class="cal-batch"><h3>${esc(t("calBatchTitle"))}</h3><p>${esc(t("calBatchSelectHelp"))}</p>
      ${gateways.length > 1 ? `<label>${esc(t("gateway"))}<select id="cal-batch-gateway">${gateways.map((entry) => `<option value="${esc(entry.entry_id)}">${esc(entry.title)}</option>`).join("")}</select></label>` : ""}
      <p id="batch-error" role="alert"></p><div id="batch-selection">${esc(t("loading"))}</div>
      <div class="actions"><button type="button" id="batch-continue" class="primary" disabled>${esc(t("calBatchContinue"))}</button>
      <button type="button" id="batch-back">${esc(t("cancel"))}</button></div></div>`;
    host.querySelector("#batch-back").onclick = () => this._backToList();
    const load = async (entryId) => {
      const list = host.querySelector("#batch-selection"), next = host.querySelector("#batch-continue");
      next.disabled = true;
      list.textContent = t("loading");
      try {
        const data = await hass.callWS({ type: "myhome/cover_calibration/targets", entry_id: entryId });
        if (!this._current(generation) || this._mode.kind !== "batch") return;
        list.innerHTML = data.targets.map((item) => `<label class="batch-target"><input type="checkbox" value="${esc(item.entity_id)}" ${item.reason ? "disabled" : ""}>
          <span>${esc(item.name)}<small class="muted">${esc(item.entity_id)}${item.reason ? ` · ${esc(t(`profileError_${item.reason}`))}` : ""}</small></span></label>`).join("") || esc(t("calBatchEmpty"));
        const selected = () => [...list.querySelectorAll("input:checked:not(:disabled)")].map((input) => input.value);
        list.onchange = () => {
          const count = selected().length;
          next.disabled = count === 0 || count > data.max_batch;
          host.querySelector("#batch-error").textContent = count > data.max_batch ? `${t("calBatchLimit")}: ${data.max_batch}` : "";
        };
        next.onclick = () => {
          const ids = selected();
          if (next.disabled || !ids.length || ids.length > data.max_batch) return;
          next.disabled = true;
          this._mode = { kind: "session" };
          this._calibration.open({ host, hass, t, entity: { entry_id: entryId }, mode: "automatic", entity_ids: ids, revision: data.revision,
            onCancel: () => this._backToList(), onSaved: () => this._backToList() });
          this._appendBack(host);
        };
      } catch (error) {
        if (!this._current(generation)) return;
        list.textContent = "";
        const key = `profileError_${error?.code}`;
        host.querySelector("#batch-error").textContent = t(key) === key ? t("profileError") : t(key);
      }
    };
    const select = host.querySelector("#cal-batch-gateway");
    if (select) select.onchange = () => load(select.value);
    await load(select?.value || gateways[0].entry_id);
  }
}
