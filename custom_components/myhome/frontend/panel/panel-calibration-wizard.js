/**
 * The calibration wizard of the Calibration tab: stepper · instruction · actions on desktop, a
 * full screen on a phone. It draws what `panel-calibration-screens.js` decides and talks to a
 * `CalibrationGateway` (live session or local preview); it never builds a WebSocket message itself.
 */
const asset = (name) => { const url = new URL(name, import.meta.url); url.search = new URL(import.meta.url).search; return url.href; };
const [{ escapeHtml: esc }, text, screens, gateways, visual] = await Promise.all([
  import(asset("panel-dom.js")), import(asset("panel-calibration-text.js")), import(asset("panel-calibration-screens.js")),
  import(asset("panel-calibration-gateway.js")), import(asset("panel-calibration-visual.js")),
]);
const { rich, inline, names } = text;
const { buildScreen, slug } = screens;
const { LiveCalibrationGateway, PreviewCalibrationGateway } = gateways;
const { visualMarkup, renderCalibrationVisual } = visual;

/** A tape reading with a comma or a point; anything else, empty included, is not a number. */
export function parseReading(value) {
  const textValue = String(value ?? "").trim().replace(",", ".");
  return /^-?(\d+\.?\d*|\.\d+)$/.test(textValue) ? Number(textValue) : NaN;
}

const STAGES_BEFORE_SESSION = ["choose", "path", "profile", "current", "case", "before"];

export class CalibrationWizard {
  constructor({ stageMs } = {}) { this._stageMs = stageMs; this._generation = 0; }

  /** Sessions the wizard draws itself: slat and roll measurement, and guided times in both directions. */
  handles(session) { return session?.mode === "geometry" || (session?.mode === "guided" && !session.direction && !session.batch); }

  updateHass(hass) { if (this._context) this._context.hass = hass; }

  close() {
    this._generation++;
    clearInterval(this._ticker);
    this._gateway?.close();
    this._gateway = null;
    this._root?.remove();
    this._root = null;
    this._frame = null;
    this._engine = null;
    this._context = null;
  }

  open({ host, hass, t, covers, data, start = "choose", item = null, session = null, onOpenCover, onClose }) {
    this.close();
    this._context = { host, hass, t, covers, data, onOpenCover, onClose };
    this._local = { stage: "choose", path: "A", scope: null, coverKey: item ? key(item) : covers[0] ? key(covers[0]) : "" };
    host.innerHTML = "";
    this._root = document.createElement("section");
    this._root.className = "wiz";
    this._root.setAttribute("aria-labelledby", "wiz-cover");
    // The drawn screen is replaced at every step; the session engine keeps its own element.
    this._frame = document.createElement("div");
    this._frame.className = "wiz-frame";
    this._engine = document.createElement("div");
    this._engine.className = "wiz-engine";
    this._engine.hidden = true;
    this._root.append(this._frame, this._engine);
    host.append(this._root);
    this._root.addEventListener("click", (event) => this._click(event));
    this._root.addEventListener("keydown", (event) => this._keydown(event));
    this._root.addEventListener("input", (event) => this._input(event));
    this._root.addEventListener("change", (event) => this._change(event));
    this._root.addEventListener("submit", (event) => { event.preventDefault(); this._reading(); });
    this._signature = null;
    if (start === "path" && item) this._local.stage = "path";
    this._render();
    if (start === "refine" && item) this._startRefine(this._baseFromCover(item));
    else if (start === "resume" && session) this._resume(session, item);
    this._render();
  }

  // ---------- context for the screens ----------

  _item() { return this._context.covers.find((item) => key(item) === this._local.coverKey) || null; }

  _gatewayData(item = this._item()) { return item ? this._context.data?.(item.entry.entry_id) : null; }

  _cover() {
    const item = this._item();
    if (!item) return null;
    const data = this._gatewayData(item), { hass } = this._context;
    const followers = item.profile ? item.profile.assigned_to.filter((id) => id && id !== item.cover.entity_id)
      .map((id) => this._context.covers.find((entry) => entry.cover.entity_id === id)?.name || hass.states?.[id]?.attributes?.friendly_name || id) : [];
    const followed = this._local.path === "B" ? data?.profiles.find((profile) => profile.id === this._local.profileId) : null;
    const address = item.entity?.address;
    return { name: item.name, entity_id: item.cover.entity_id, effective: item.cover.effective || {}, travel_cm: item.cover.travel_cm ?? null,
      profile: item.profile, followers, followProfile: followed?.name ?? null,
      address: address ? [`${this._context.t("address")}: ${address.raw ?? this._context.t("addressUnknown")}`,
        ...(address.a != null && address.pl != null ? [`A: ${address.a}`, `PL: ${address.pl}`] : []), "WHO 2"].join(" · ") : "" };
  }

  _profiles() {
    const data = this._gatewayData();
    return (data?.profiles || []).map((profile) => ({ id: profile.id, name: profile.name, followers: profile.assigned_to.length,
      measuredOn: profile.provenance?.opening?.origin_name || profile.provenance?.opening?.origin_entity_id || null }));
  }

  _screen() {
    const { t, hass } = this._context, local = this._local, gateway = this._gateway;
    const cover = this._cover(), language = hass.language || "en";
    const followed = local.path === "B" ? this._gatewayData()?.profiles.find((profile) => profile.id === local.profileId) : null;
    return buildScreen({ t, language, path: local.path, scope: local.scope, stage: local.stage, local, cover,
      covers: this._context.covers.map((item) => ({ key: key(item), label: item.name + (new Set(this._context.covers.map((entry) => entry.entry.entry_id)).size > 1 ? ` · ${item.entry.title}` : "") })),
      profiles: this._profiles(), followed, followerNames: cover ? names(cover.followers, language) : "",
      view: gateway?.view || null, status: gateway?.status || {}, elapsed: gateway?.elapsed() ?? null,
      preview: !!gateway?.preview, supports: (target) => gateway ? gateway.supports(target) : false });
  }

  // ---------- drawing ----------

  _render() {
    if (!this._root) return;
    const screen = this._screen();
    this._current = screen;
    const { t } = this._context;
    const signature = JSON.stringify([screen.code, screen.title, screen.body, screen.header, screen.choice && { ...screen.choice, value: undefined },
      screen.field && { ...screen.field, disabled: undefined }, screen.box, screen.table, screen.technical, screen.precision,
      screen.profileBlock && { ...screen.profileBlock, name: screen.profileBlock.name && { label: screen.profileBlock.name.label, hint: screen.profileBlock.name.hint } },
      screen.saveInfo, screen.preview, !!screen.visual, screen.wait && screen.wait.text, screen.discard]);
    if (signature !== this._signature) {
      const codeChanged = this._renderedCode !== screen.code;
      this._signature = signature;
      this._renderedCode = screen.code;
      this._root.dataset.code = screen.code;
      this._root.toggleAttribute("data-preview", screen.preview);
      this._frame.innerHTML = `
        <header class="wiz-head">
          <div class="wiz-head-text"><h3 id="wiz-cover" class="wiz-cover">${esc(screen.header.title)}</h3>${screen.header.subtitle ? `<p class="muted">${esc(screen.header.subtitle)}</p>` : ""}</div>
          ${screen.discard ? `<button type="button" class="wiz-discard" data-wiz="exit">${esc(t("wizDiscard"))}</button>` : ""}
          <button type="button" class="icon-button wiz-x" data-wiz="${screen.discard ? "exit" : "close"}" aria-label="${esc(screen.discard ? t("wizDiscard") : t("wiz_T158"))}" title="${esc(screen.discard ? t("wizDiscard") : t("wiz_T158"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button>
        </header>
        <div class="wiz-compact"><span class="wiz-dot" aria-hidden="true"></span><span class="wiz-compact-line"></span>
          <button type="button" class="wiz-steps-button" data-wiz="steps" aria-haspopup="dialog">${esc(t("wiz_T274"))}</button></div>
        <div class="wiz-columns">
          <nav class="wiz-steps" aria-label="${esc(t("wiz_T274"))}"></nav>
          <div class="wiz-main">
            ${screen.preview ? `<p class="wiz-preview" role="note"><ha-icon icon="mdi:eye-outline" aria-hidden="true"></ha-icon><span>${esc(t("wizPreview"))}</span></p>` : ""}
            <h4 class="wiz-title" tabindex="-1">${esc(screen.title)}</h4>
            <div class="wiz-stopwatch" hidden><span class="wiz-stopwatch-label"></span><span class="wiz-stopwatch-value"></span></div>
            ${screen.wait ? this._waitMarkup(screen.wait) : ""}
            ${screen.visual ? visualMarkup() : ""}
            ${screen.body ? `<div class="wiz-body">${rich(screen.body)}</div>` : ""}
            ${screen.box ? `<div class="wiz-box"><span class="muted">${esc(screen.box.label)}</span><p>${esc(screen.box.text)}</p></div>` : ""}
            ${screen.choice ? this._choiceMarkup(screen.choice) : ""}
            ${screen.field ? this._fieldMarkup(screen.field) : ""}
            ${screen.precision ? `<p class="wiz-precision">${inline(screen.precision)}</p>` : ""}
            ${screen.table ? this._tableMarkup(screen.table) : ""}
            ${screen.technical ? this._technicalMarkup(screen.technical) : ""}
            ${screen.profileBlock ? this._profileMarkup(screen.profileBlock) : ""}
            ${screen.saveInfo ? `<details class="wiz-accordion"><summary>${esc(screen.saveInfo.title)}<ha-icon icon="mdi:chevron-down" aria-hidden="true"></ha-icon></summary>${rich(screen.saveInfo.body)}</details>` : ""}
            <div class="wiz-notices" aria-live="polite"></div>
          </div>
          <div class="wiz-actions"></div>
        </div>
        <div class="wiz-sheet" role="dialog" aria-modal="true" aria-label="${esc(t("wiz_T274"))}" hidden><div class="wiz-sheet-card">
          <button type="button" class="icon-button wiz-sheet-close" data-wiz="steps-close" aria-label="${esc(t("close"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button>
          <div class="wiz-sheet-steps"></div></div></div>
        <div class="wiz-dialog" role="alertdialog" aria-modal="true" aria-labelledby="wiz-dialog-title" aria-describedby="wiz-dialog-body" hidden><div class="wiz-dialog-card">
          <h4 id="wiz-dialog-title">${esc(t("wiz_T267"))}</h4><p id="wiz-dialog-body"></p>
          <div class="actions"><button type="button" class="primary" data-wiz="stay">${esc(t("wiz_T269"))}</button>
            <button type="button" class="wiz-leave" data-wiz="leave">${esc(t("wiz_T270"))}</button>
            <button type="button" class="wiz-dialog-stop" data-wiz="stop" hidden>${esc(t("wiz_T028"))}</button></div></div></div>`;
      this._actionsSignature = null;
      if (codeChanged) queueMicrotask(() => this._frame?.querySelector(".wiz-title")?.focus({ preventScroll: false }));
    }
    this._patch(screen);
  }

  _engineHost() { return this._engine; }

  /** Whatever changes within one screen: stepper, stopwatch, progress, notices, buttons, read-only. */
  _patch(screen) {
    const root = this._frame, { t } = this._context;
    const stepper = this._stepperMarkup(screen);
    for (const target of [root.querySelector(".wiz-steps"), root.querySelector(".wiz-sheet-steps")]) if (target.innerHTML !== stepper) target.innerHTML = stepper;
    root.querySelector(".wiz-compact-line").textContent = screen.stepper.line;
    const watch = root.querySelector(".wiz-stopwatch");
    watch.hidden = !screen.stopwatch;
    if (screen.stopwatch) {
      root.querySelector(".wiz-stopwatch-label").textContent = screen.stopwatch.label;
      root.querySelector(".wiz-stopwatch-value").textContent = screen.stopwatch.value;
    }
    const wait = root.querySelector(".wiz-wait");
    if (wait && screen.wait) {
      const stages = screen.wait.stages.map((stage) => `<li data-state="${stage.state}">${esc(stage.text)}</li>`).join("");
      const list = wait.querySelector(".wiz-wait-stages");
      if (list.innerHTML !== stages) list.innerHTML = stages;
      list.hidden = !screen.wait.stages.length;
      const bar = wait.querySelector(".wiz-progress");
      bar.hidden = screen.wait.progress == null;
      if (screen.wait.progress != null) bar.querySelector("span").style.width = `${Math.round(screen.wait.progress * 100)}%`;
    }
    if (screen.visual) renderCalibrationVisual(root.querySelector(".wiz-main"), screen.visual, t, !!this._gateway?.status.lost);
    const notices = screen.notices.map((notice) => `<p class="notice wiz-notice" data-tone="${notice.tone}" ${notice.tone === "error" ? 'role="alert"' : ""}>${esc(notice.text)}</p>`).join("");
    const box = root.querySelector(".wiz-notices");
    if (box.innerHTML !== notices) box.innerHTML = notices;
    const field = root.querySelector(".wiz-field input");
    if (field) field.disabled = !!screen.field?.disabled;
    const block = screen.profileBlock?.name;
    const line = root.querySelector(".wiz-name-line");
    if (line && block && line.textContent !== block.line) line.textContent = block.line;
    root.querySelector(".wiz-name-input")?.setAttribute("aria-invalid", String(block ? !block.valid : false));
    const actions = JSON.stringify([screen.actions.map((action) => [action.id, action.label, action.kind]), screen.readOnly]);
    const column = root.querySelector(".wiz-actions");
    if (actions !== this._actionsSignature) {
      const focused = column.contains(root.getRootNode().activeElement) ? root.getRootNode().activeElement.dataset.wiz : null;
      this._actionsSignature = actions;
      column.innerHTML = `${screen.readOnly ? `<div class="wiz-readonly"><p class="notice">${esc(screen.readOnly.text)}</p>
          <button type="button" class="${screen.readOnly.primary || screen.readOnly.consequence ? "primary" : ""}" data-wiz="take">${esc(screen.readOnly.take)}</button>
          ${screen.readOnly.consequence ? `<p class="muted">${esc(screen.readOnly.consequence)}</p>` : ""}</div>` : ""}
        ${screen.actions.map((action) => `<button type="button" class="wiz-action ${action.kind}" data-wiz="${esc(action.id)}">${esc(action.label)}</button>`).join("")}`;
      if (focused) column.querySelector(`[data-wiz="${focused}"]`)?.focus();
    }
    for (const action of screen.actions) {
      const button = column.querySelector(`[data-wiz="${action.id}"]`);
      if (button) button.disabled = !!action.disabled;
    }
    const take = column.querySelector('[data-wiz="take"]');
    if (take) take.disabled = !!this._gateway?.status.busy;
  }

  _stepperMarkup(screen) {
    return `<p class="wiz-steps-line">${esc(screen.stepper.line)}</p>${screen.caption ? `<p class="wiz-steps-caption muted">${esc(screen.caption)}</p>` : ""}
      <ol>${screen.stepper.phases.map((phase) => `<li data-state="${phase.state}"${phase.state === "current" ? ' aria-current="step"' : ""}><span class="wiz-step-mark" aria-hidden="true"></span><span class="wiz-step-label">${esc(phase.label)}</span>
        ${phase.substeps.length ? `<ul>${phase.substeps.map((item) => `<li>${esc(item.label)}: ${esc(item.value)}</li>`).join("")}</ul>` : ""}</li>`).join("")}</ol>`;
  }

  _waitMarkup(wait) {
    return `<div class="wiz-wait" role="status"><p>${esc(wait.text)}</p><ol class="wiz-wait-stages"></ol>
      <div class="wiz-progress" hidden><span></span></div></div>`;
  }

  _choiceMarkup(choice) {
    if (choice.kind === "select") {
      return `<label class="wiz-choice">${esc(choice.label)}<select name="${esc(choice.name)}">${choice.options.map((option) =>
        `<option value="${esc(option.value)}" ${option.value === choice.value ? "selected" : ""}>${esc(option.label)}</option>`).join("")}</select>
        ${choice.hint ? `<span class="muted wiz-choice-hint">${esc(choice.hint)}</span>` : ""}</label>`;
    }
    return `<fieldset class="wiz-choice wiz-radios"><legend>${esc(choice.label)}</legend>${choice.options.map((option) =>
      `<label class="wiz-radio"><input type="radio" name="${esc(choice.name)}" value="${esc(option.value)}" ${option.value === choice.value ? "checked" : ""}><span>${inline(option.label)}</span></label>`).join("")}</fieldset>`;
  }

  _fieldMarkup(field) {
    const value = field.value == null ? "" : `${field.value}`;
    return `<form class="wiz-field" novalidate><label>${esc(field.label)}<span class="input-suffix"><input name="reading_cm" type="text" inputmode="decimal" autocomplete="off" value="${esc(value)}" aria-describedby="wiz-field-hint" data-kind="${esc(field.kind)}" data-min="${field.min}" data-max="${field.max}"><span>cm</span></span></label>
      <p id="wiz-field-hint" class="muted">${esc(field.hint)}</p></form>`;
  }

  _tableMarkup(table) {
    return `<table class="wiz-table"><thead><tr>${table.headers.map((header) => `<th scope="col">${esc(header)}</th>`).join("")}</tr></thead>
      <tbody>${table.rows.map((row) => `<tr><th scope="row">${esc(row.label)}</th><td>${row.changed ? `<s>${esc(row.before)}</s>` : esc(row.before)}</td><td>${esc(row.after)}</td></tr>`).join("")}</tbody></table>`;
  }

  _technicalMarkup(technical) {
    return `<details class="wiz-accordion wiz-technical"><summary>${esc(technical.title)}<ha-icon icon="mdi:chevron-down" aria-hidden="true"></ha-icon></summary>
      <p class="muted">${esc(technical.caption)}</p>${this._tableMarkup({ headers: [this._context.t("wizTableValue"), this._context.t("wizTableBefore"), this._context.t("wizTableAfter")], rows: technical.rows })}
      ${technical.code ? `<pre class="wiz-code">${esc(technical.code)}</pre>` : ""}</details>`;
  }

  _profileMarkup(block) {
    return `<div class="wiz-profile-block">
      <label class="wiz-switch"><input type="checkbox" role="switch" name="save_profile" ${block.on ? "checked" : ""}><span>${esc(block.switchLabel)}</span></label>
      <p class="muted">${esc(block.explanation)}</p>
      ${block.choice ? `<fieldset class="wiz-radios">${block.choice.options.map((option) => `<label class="wiz-radio"><input type="radio" name="save_choice" value="${esc(option.value)}" ${option.value === block.choice.value ? "checked" : ""}>
        <span>${esc(option.label)}${option.description ? `<small class="muted">${esc(option.description)}</small>` : ""}</span></label>`).join("")}</fieldset>` : ""}
      ${block.name ? `<label>${esc(block.name.label)}<input class="wiz-name-input" name="profile_name" maxlength="64" autocomplete="off" value="${esc(block.name.value)}" aria-describedby="wiz-name-hint"></label>
        <p id="wiz-name-hint" class="muted">${esc(block.name.hint)}</p><p class="wiz-name-line">${esc(block.name.line)}</p>` : ""}</div>`;
  }

  // ---------- events ----------

  _keydown(event) {
    if (event.key !== "Escape") return;
    const dialog = this._frame.querySelector(".wiz-dialog"), sheet = this._frame.querySelector(".wiz-sheet");
    if (!dialog.hidden) { event.preventDefault(); this._closeDialog(); }
    else if (!sheet.hidden) { event.preventDefault(); sheet.hidden = true; this._frame.querySelector('[data-wiz="steps"]').focus(); }
  }

  _input(event) {
    if (event.target.name === "profile_name") { this._local.profileName = event.target.value.trim(); this._patch(this._screen()); }
    if (event.target.name === "reading_cm") event.target.removeAttribute("aria-invalid");
  }

  _change(event) {
    const { name, value, checked } = event.target;
    if (name === "save_profile") { this._local.saveProfile = checked; this._render(); }
    else if (name === "save_choice") { this._local.saveChoice = value; this._render(); }
    else if (name === "slats") this._local.slats = value !== "no";
    else if (name === "case") this._local.scope = value;
    else if (name === "cover") this._local.coverKey = value;
    else if (name === "profile") { this._local.profileId = value; this._render(); }
  }

  _click(event) {
    const button = event.target.closest("button[data-wiz]");
    if (!button || button.disabled) return;
    event.preventDefault();
    this._act(button.dataset.wiz);
  }

  _value(name) { return this._frame.querySelector(`[name="${name}"]:checked, select[name="${name}"]`)?.value; }

  async _act(id) {
    const local = this._local, gateway = this._gateway;
    if (id === "steps") { const sheet = this._frame.querySelector(".wiz-sheet"); sheet.hidden = false; sheet.querySelector("button").focus(); return; }
    if (id === "steps-close") { this._frame.querySelector(".wiz-sheet").hidden = true; this._frame.querySelector('[data-wiz="steps"]').focus(); return; }
    if (id === "exit") { this._exit(); return; }
    if (id === "stay") { this._closeDialog(); return; }
    if (id === "leave") { this._leave(); return; }
    if (id === "close") { this._finish(); return; }
    if (id === "choose") { local.coverKey = this._value("cover") || local.coverKey; local.stage = "path"; return this._render(); }
    if (id.startsWith("path:")) {
      local.path = id.slice(5);
      local.stage = local.path === "A" ? "before" : local.path === "B" ? "profile" : "current";
      if (local.path === "B") local.profileId = this._profiles()[0]?.id;
      return this._render();
    }
    if (id === "profile") { local.profileId = this._value("profile") || local.profileId; local.stage = "before"; return this._render(); }
    if (id === "current") { local.stage = "case"; return this._render(); }
    if (id === "case") { local.scope = this._value("case") || local.scope || "times_and_rolls"; local.stage = "before"; return this._render(); }
    if (id === "begin") { if (local.stage === "before") local.slats = (this._value("slats") ?? (local.slats === false ? "no" : "yes")) !== "no"; return this._begin(); }
    if (id.startsWith("ack:")) {
      local[{ lift: "ackLift", ascent: "ackAscent", descent: "ackDescent", readings: "ackReadings" }[id.slice(4)]] = true;
      if (id === "ack:readings") return this._send("next");
      return this._render();
    }
    if (id === "reading") return this._reading();
    if (["next", "lift", "endpoint", "open", "close", "repeat", "repeat_step", "accept", "repeat_check", "redo_readings", "continue_anyway", "continue"].includes(id)) return this._send(id);
    if (id === "stop") { this._closeDialog(false); return gateway?.stop(); }
    if (id === "take") return gateway?.claim();
    if (id === "reconnect") return gateway?.reconnect();
    if (id === "save" || id === "refine") return this._save(id === "refine");
    if (id === "start-over") { this._dropGateway(); Object.assign(local, freshFlags(), { stage: "before" }); return this._render(); }
    if (id === "another") { this._dropGateway(); Object.assign(local, freshFlags(), { stage: "choose", path: "A", scope: null, saved: null, refining: false, base: null }); return this._render(); }
    if (id === "open-cover") { const entityId = this._item()?.cover.entity_id; const { onOpenCover } = this._context; this._finish(); onOpenCover?.(entityId); return; }
    if (id === "correct") {
      // B → C: the cover is measured on its own; nothing of the preview was written.
      this._dropGateway();
      Object.assign(local, freshFlags(), { path: "C", scope: "times_and_rolls", stage: "current" });
      return this._render();
    }
  }

  _send(action, extra = {}) {
    if (!this._gateway) return;
    this._local.armed = true;
    return this._gateway.act(action, extra);
  }

  _reading() {
    const input = this._frame.querySelector('[name="reading_cm"]');
    if (!input) return;
    const value = parseReading(input.value), min = Number(input.dataset.min), max = Number(input.dataset.max);
    if (!Number.isFinite(value) || value < min || value > max) {
      input.setAttribute("aria-invalid", "true");
      input.focus();
      return;
    }
    return this._send("reading", { reading_cm: value });
  }

  _save(thenRefine) {
    const screen = this._current, local = this._local;
    const action = screen.actions.find((item) => item.id === (thenRefine ? "refine" : "save"));
    if (!action || action.disabled || !this._gateway) return;
    local.thenRefine = thenRefine;
    const name = screen.profileBlock?.name?.value;
    // Path B saves no measured value: the cover follows the chosen profile (L5b).
    local.pendingSave = local.path === "B" ? { target: "follow_profile", name: null } : { target: action.target || "profile_new", name };
    local.armed = true;
    return this._gateway.save(local.pendingSave);
  }

  // ---------- sessions ----------

  _newGateway(kind, plan, values) {
    const generation = this._generation;
    const onChange = (change) => {
      if (generation !== this._generation || !this._root) return;
      if (change === "tick") { this._patch(this._screen()); return; }
      this._viewChanged();
    };
    this._gateway = kind === "live" ? new LiveCalibrationGateway({ onChange })
      : new PreviewCalibrationGateway({ onChange, plan, values, ...(this._stageMs != null ? { stageMs: this._stageMs } : {}) });
    return this._gateway;
  }

  _dropGateway() { this._gateway?.close(); this._gateway = null; }

  _liveContext() {
    const item = this._item(), { hass, t } = this._context, generation = this._generation;
    return { host: this._engineHost(), hass, t, entity: { entry_id: item.entry.entry_id, entity_id: item.cover.entity_id }, revision: item.revision,
      onSaved: () => { if (generation === this._generation) this._saved(); },
      onCancel: () => { if (generation === this._generation) this._finish(); } };
  }

  _begin() {
    const local = this._local, item = this._item();
    if (!item) return;
    this._dropGateway();
    Object.assign(local, freshFlags(), { stage: "session", begun: true, armed: true });
    if (local.path === "B" || (local.path === "C" && local.scope === "points_only")) {
      this._newGateway("preview", local.path === "B" ? "profile" : "rolls", this._baseValues(item)).start();
    } else {
      this._newGateway("live").start({ ...this._liveContext(), mode: local.path === "C" && local.scope === "times_only" ? "guided" : "geometry", slats: local.slats !== false });
    }
    this._render();
  }

  _resume(session, item) {
    const local = this._local;
    if (item) local.coverKey = key(item);
    local.path = "A";
    if (session.mode === "guided") { local.path = "C"; local.scope = "times_only"; }
    Object.assign(local, freshFlags(), { stage: "session" });
    this._newGateway("live").resume({ ...this._liveContext(), session });
  }

  _baseValues(item) {
    const effective = item.cover.effective || {};
    return { opening_time: effective.opening?.value, closing_time: effective.closing?.value, slat_time_s: effective.slat_time_s?.value ?? 0,
      opening_roll: effective.opening_roll?.value ?? null, closing_roll: effective.closing_roll?.value ?? null, travel_cm: item.cover.travel_cm ?? null };
  }

  _baseFromCover(item) {
    const values = this._baseValues(item);
    return { opening: values.opening_time, closing: values.closing_time, slat: values.slat_time_s, travel: values.travel_cm,
      opening_roll: values.opening_roll, closing_roll: values.closing_roll };
  }

  /** Fine-tuning after a calibration (A-22…A-34): simulated until the backend offers it (L5c). */
  _startRefine(base) {
    const local = this._local;
    this._dropGateway();
    Object.assign(local, freshFlags(), { stage: "session", refining: true, base, armed: true });
    this._newGateway("preview", "refine", { opening_time: base.opening, closing_time: base.closing, slat_time_s: base.slat ?? 0,
      opening_roll: base.opening_roll, closing_roll: base.closing_roll, travel_cm: base.travel }).start();
  }

  _viewChanged() {
    const view = this._gateway?.view, local = this._local;
    if (view?.phase === "review" && !view.preview) {
      local.review = { opening: view.values?.opening_time, closing: view.values?.closing_time, slat: view.geometry?.slat_time_s ?? null,
        travel: view.mode === "geometry" ? view.travel_cm : null, opening_roll: view.geometry?.opening_roll ?? null, closing_roll: view.geometry?.closing_roll ?? null,
        lift: view.samples?.lift ?? null, gap: view.readings?.gap ?? null };
      local.baseReadings = { ...view.readings };
    }
    if (view?.preview && view.phase === "saved") { this._saved(view.saved); return; }
    if (view?.preview && view.phase === "cancelled") { this._finish(); return; }
    this._autoNext(view);
    this._render();
  }

  /**
   * Movements the mockups show as automatic after a press: the return to a known end stop and the
   * runs of the tape readings. Only after an action of this tab, once per view, never in a read-only
   * or resumed view: the press that led here is the user's.
   */
  _autoNext(view) {
    const local = this._local;
    if (!view || view.preview || view.mode !== "geometry" || view.phase !== "briefing" || !view.owner || view.read_only || !local.armed) return;
    if (this._gateway.status.busy || local.autoSequence === view.sequence) return;
    const due = (view.step === "home" && local.begun) || (view.step === "reset" && !view.gap_warning) || view.step === "top"
      || (["half_open", "half_close"].includes(view.step) && local.ackReadings);
    if (!due) return;
    local.autoSequence = view.sequence;
    queueMicrotask(() => { if (this._gateway?.view === view) this._gateway.act("next"); });
  }

  _saved(previewSaved) {
    const local = this._local;
    const target = previewSaved?.target ?? local.pendingSave?.target;
    // The saved screen still shows what the steps measured, and whether the last part was a preview.
    if (this._gateway?.preview) local.fineReadings = { ...(this._gateway.view?.readings || {}), check: this._gateway.view?.check ?? null };
    local.saved = { target, name: previewSaved?.name ?? local.pendingSave?.name ?? null, travel_cm: this._gateway?.view?.travel_cm ?? local.review?.travel ?? null,
      preview: !!this._gateway?.preview };
    if (local.path === "B") local.saved.target = "follow_profile";
    if (local.thenRefine && local.review && !this._gateway?.preview) {
      const base = { ...local.review };
      this._startRefine(base);
      local.thenRefine = false;
      this._render();
      return;
    }
    local.stage = "saved";
    this._dropGateway();
    this._render();
  }

  // ---------- leaving ----------

  _sessionOpen() {
    const view = this._gateway?.view;
    return !!view && !["interrupted", "cancelled", "saved"].includes(view.phase) && !(view.read_only && !view.preview);
  }

  _exit() {
    if (STAGES_BEFORE_SESSION.includes(this._local.stage) || !this._sessionOpen()) { this._finish(); return; }
    const dialog = this._frame.querySelector(".wiz-dialog"), { t } = this._context;
    dialog.querySelector("#wiz-dialog-body").textContent = t(this._gateway.preview ? "wiz_T268" : "wizExitBodyLive");
    dialog.querySelector(".wiz-dialog-stop").hidden = !screens.MOVING(this._gateway.view);
    dialog.hidden = false;
    this._root.classList.add("has-dialog");
    dialog.querySelector('[data-wiz="stay"]').focus();
  }

  _closeDialog(focus = true) {
    const dialog = this._frame?.querySelector(".wiz-dialog");
    if (!dialog || dialog.hidden) return;
    dialog.hidden = true;
    this._root.classList.remove("has-dialog");
    if (focus) this._frame.querySelector('[data-wiz="exit"]')?.focus();
  }

  /** "Exit without saving": Cancel must reach Home Assistant; the view closes only once it has. */
  async _leave() {
    this._closeDialog(false);
    const gateway = this._gateway;
    if (!gateway) { this._finish(); return; }
    if (gateway.preview) { this._finish(); return; }
    await gateway.cancel();
    if (this._gateway === gateway && gateway.status.cancelPending) this._render();
  }

  _finish() {
    const { onClose } = this._context || {};
    this.close();
    onClose?.();
  }
}

function key(item) { return JSON.stringify([item.entry.entry_id, item.cover.entity_id]); }

function freshFlags() {
  return { ackLift: false, ackAscent: false, ackDescent: false, ackReadings: false, armed: false, begun: false, autoSequence: null,
    review: null, thenRefine: false, pendingSave: null, saveProfile: undefined, saveChoice: undefined, profileName: undefined, refining: false };
}

export { slug };
