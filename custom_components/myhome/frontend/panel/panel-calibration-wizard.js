/**
 * The calibration wizard of the Calibration tab: stepper · instruction · actions on desktop, a
 * full screen on a phone. It draws what `panel-calibration-screens.js` decides and talks to a
 * `CalibrationGateway` (live session or local preview); it never builds a WebSocket message itself.
 */
const asset = (name) => { const url = new URL(name, import.meta.url); url.search = new URL(import.meta.url).search; return url.href; };
const [{ escapeHtml: esc }, text, screens, gateways, illustration, { morph }, { layout, fitBars, fitRows, dockBar, focusOnOpen, revealHead }] = await Promise.all([
  import(asset("panel-dom.js")), import(asset("panel-calibration-text.js")), import(asset("panel-calibration-screens.js")),
  import(asset("panel-calibration-gateway.js")), import(asset("panel-calibration-illustration.js")), import(asset("panel-calibration-morph.js")), import(asset("panel-calibration-layout.js")),
]);
const { rich, inline, names } = text;
const { buildScreen, slug, stopVerdict } = screens;
const { LiveCalibrationGateway, PreviewCalibrationGateway } = gateways;
const { illustrationMarkup, ILLUSTRATIONS } = illustration;

/** "Label: value" as the tab's blocks show facts: the label regular, the value bold. */
/** A cover's room, gateway and bus address: one string, and its units for the header (responsive map §3.3). */
const subline = (lead, bus) => {
  const units = lead.filter(Boolean);
  return { address: [...units, bus].filter(Boolean).join(" · "), units: { lead: units, bus } };
};

function factMarkup(line) {
  const index = line.indexOf(": ");
  return index < 0 ? esc(line) : `${esc(line.slice(0, index))}: <strong>${esc(line.slice(index + 2))}</strong>`;
}

/** A tape reading with a comma or a point; anything else, empty included, is not a number. */
export function parseReading(value) {
  const textValue = String(value ?? "").trim().replace(",", ".");
  return /^-?(\d+\.?\d*|\.\d+)$/.test(textValue) ? Number(textValue) : NaN;
}

const STAGE_ICON = { done: "mdi:check-circle", current: "mdi:circle-half-full", future: "mdi:circle-outline" };
const STAGES_BEFORE_SESSION = ["choose", "path", "profile", "current", "case", "before"];
/**
 * After every change of screen (or of its buttons) the confirming buttons stay disabled this long, so that a slow
 * double tap never confirms an end stop the cover has not reached, nor skips the second tap of "Take control".
 * Stop is never held back.
 */
export const CONFIRM_GUARD_MS = 700;
/** How long a sheet takes to slide in or out (the CSS animations use the same). */
const SHEET_MS = 220;
/** Home Assistant keeps a session open this long for its owner at rest (IDLE_LEASE_SECONDS) when the view does not say. */
const IDLE_LEASE_SECONDS = 1800;
/** A return of the tape readings confirms itself this long after the measured time of its direction (~2 s + settling). */
export const AUTO_ENDPOINT_MARGIN_SECONDS = 3;
/** A stop frame between these times is an actuator's timer (about 60 s), never the real end of the run. */
export const TIMER_STOP_SECONDS = screens.TIMER_STOP_SECONDS;
// Phases a press goes through before the cover stops again: the press that started them still counts.
const TRANSIT = ["starting_open", "starting_close", "opening", "closing", "geometry_wait_stop"];

export class CalibrationWizard {
  constructor({ stageMs, guardMs = CONFIRM_GUARD_MS } = {}) { this._stageMs = stageMs; this._guardMs = guardMs; this._generation = 0; }

  /**
   * Sessions the wizard draws itself when opened from the list: slat and roll measurement. A guided
   * session (times only) opens in the existing view, which offers every save mode it was started with.
   */
  /** L-4: its own sessions, geometry and guided («solo tempi», marked `origin: "wizard"`); the rest is the maintainer's. */
  handles(session) { return !!session && !session.batch && (session.mode === "geometry" || (session.mode === "guided" && session.origin === "wizard" && !session.direction)); }

  updateHass(hass) { if (this._context) { this._context.hass = hass; this._theme(); } }

  /** The drawings follow Home Assistant's dark mode; without theme data, the system's preference. */
  _theme() {
    if (!this._root) return;
    const mode = this._context?.hass?.themes?.darkMode;
    const dark = typeof mode === "boolean" ? mode : !!globalThis.matchMedia?.("(prefers-color-scheme: dark)")?.matches;
    this._root.dataset.theme = dark ? "dark" : "light";
  }

  close() {
    clearInterval(this._leaseTimer); this._leaseTimer = null;
    if (this._onVisible) document.removeEventListener("visibilitychange", this._onVisible);
    this._onVisible = null;
    this._moreObserver?.disconnect();
    this._moreObserver = null;
    this._moreUpdate = null;
    this._navResolve?.(true);
    this._navResolve = null;
    this._unloadGuard(false);
    this._generation++;
    clearInterval(this._ticker);
    clearTimeout(this._guardTimer);
    this._gateway?.close();
    this._gateway = null;
    this._undock?.();
    this._undock = null;
    this._root?.remove();
    this._root = null;
    this._frame = null;
    this._engine = null;
    this._context = null;
  }

  open({ host, hass, t, covers, data, picker = null, start = "choose", item = null, session = null, onOpenCover, onAssignProfile, onDiscarded, onClose }) {
    this.close();
    this._context = { host, hass, t, covers, data, picker, onOpenCover, onAssignProfile, onDiscarded, onClose };
    // Opened on a given cover, the choice is made; from the tab's generic button it starts empty.
    this._local = { stage: "choose", path: "A", scope: null, coverKey: item ? key(item) : "", coverPicked: !!item };
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
    this._revealOnOpen = true;
    // U-1: the one-column layout docks its action bar to the window's bottom.
    this._undock = dockBar(this._root);
    this._theme();
    this._root.addEventListener("click", (event) => this._click(event));
    this._root.addEventListener("keydown", (event) => this._keydown(event));
    this._root.addEventListener("input", (event) => this._input(event));
    this._root.addEventListener("change", (event) => this._change(event));
    this._root.addEventListener("submit", (event) => { event.preventDefault(); this._reading(); });
    // Back on the page (Safari suspends a tab in the background): reconnect at once, without asking.
    this._onVisible = () => {
      const gateway = this._gateway, status = gateway?.status || {};
      if (document.hidden || !gateway || gateway.preview || status.expired || !gateway.view?.recoverable) return;
      // Lost: resume the same session. Otherwise ask at once: a subscription that died in the background shows now.
      if (status.lost) gateway.reconnect(); else gateway.ping?.();
    };
    document.addEventListener("visibilitychange", this._onVisible);
    this._signature = null;
    if (start === "path" && item) this._local.stage = "path";
    // Where the way back ends: A-01 from the tab's generic button, A-02 from a cover's own Measure.
    this._local.entry = this._local.stage;
    this._render();
    // The tab's Fine-tune asks first what is wrong (C-01, C-02); A-34's "Continue with fine-tuning" goes straight to A-22.
    if (start === "refine" && item) { Object.assign(this._local, { stage: "current", path: "C", entry: "current" }); this._render(); }
    else if (start === "resume" && session) this._resume(session, item);
    this._render();
  }

  // ---------- context for the screens ----------

  /** The tab's covers as they are now (a function from the tab, read again after a save), or a fixed list. */
  _covers() { const { covers } = this._context; return (typeof covers === "function" ? covers() : covers) || []; }

  _item() { return this._covers().find((item) => key(item) === this._local.coverKey) || null; }

  _gatewayData(item = this._item()) { return item ? this._context.data?.(item.entry.entry_id) : null; }

  _cover() {
    const item = this._item();
    if (!item) return null;
    const data = this._gatewayData(item), { hass } = this._context;
    const followers = item.profile ? item.profile.assigned_to.filter((id) => id && id !== item.cover.entity_id)
      .map((id) => this._covers().find((entry) => entry.cover.entity_id === id)?.name || hass.states?.[id]?.attributes?.friendly_name || id) : [];
    const followed = this._local.path === "B" ? data?.profiles.find((profile) => profile.id === this._local.profileId) : null;
    const address = item.entity?.address;
    return { name: item.name, entity_id: item.cover.entity_id, effective: item.cover.effective || {}, travel_cm: item.cover.travel_cm ?? null,
      status: item.status, last: item.last,
      profile: item.profile, followers, followProfile: followed?.name ?? null,
      // G4-1: as the list rows: room first (and the gateway when there are several), then the bus address; no WHO.
      // The units apart too (responsive map §3.3): the header wraps between them, never inside the address.
      ...subline([item.area, new Set(this._covers().map((entry) => entry.entry.entry_id)).size > 1 ? item.entry.title : ""],
        address ? [`${this._context.t("address")}: ${address.raw ?? this._context.t("addressUnknown")}`,
          ...(address.a != null && address.pl != null ? [`A: ${address.a}`, `PL: ${address.pl}`] : [])].join(" · ") : "") };
  }

  /** A drop-down entry: "Name · Room · Address: 86 · A: 8 · PL: 6", and the gateway when there are several. */
  _coverLabel(item) {
    const { t } = this._context, covers = this._covers(), address = item.entity?.address;
    const bus = address?.raw ? [`${t("address")}: ${address.raw}`, ...(address.a != null && address.pl != null ? [`A: ${address.a}`, `PL: ${address.pl}`] : [])].join(" · ") : "";
    const gateway = new Set(covers.map((entry) => entry.entry.entry_id)).size > 1 ? item.entry.title : "";
    return [item.name, item.area, bus, gateway].filter(Boolean).join(" · ");
  }

  _profiles() {
    const data = this._gatewayData();
    return (data?.profiles || []).map((profile) => ({ id: profile.id, name: profile.name, followers: profile.assigned_to.length,
      measuredOn: this._originName(profile.provenance?.opening), slat: profile.geometry ? profile.geometry.slat_time_s ?? null : null,
      followerNames: profile.assigned_to.filter(Boolean).map((id) => this._covers().find((item) => item.cover.entity_id === id)?.name
        || this._context.hass.states?.[id]?.attributes?.friendly_name || id),
      referenceTravel: profile.reference_travel_cm ?? null }));
  }

  /** Where a profile was measured, by the cover's name in the list (the provenance's name may be its entity id). */
  _originName(origin) {
    const id = origin?.origin_entity_id, { hass } = this._context;
    return (id && (this._covers().find((item) => item.cover.entity_id === id)?.name || hass.states?.[id]?.attributes?.friendly_name))
      || origin?.origin_name || id || null;
  }

  _screen() {
    const { t, hass } = this._context, local = this._local, gateway = this._gateway;
    const cover = this._cover(), language = hass.language || "en";
    const followed = local.path === "B" ? this._gatewayData()?.profiles.find((profile) => profile.id === local.profileId) : null;
    const screen = buildScreen({ t, language, path: local.path, scope: local.scope, stage: local.stage, local, cover,
      covers: this._covers().map((item) => ({ key: key(item), label: this._coverLabel(item), status: item.status, last: item.last })),
      profiles: this._profiles(), followed, followerNames: cover ? names(cover.followers, language) : "",
      view: gateway?.view || null, status: gateway?.status || {}, elapsed: gateway?.elapsed() ?? null, runPosition: local.run?.position ?? null, now: Date.now(),
      preview: !!gateway?.preview, supports: (target) => gateway ? gateway.supports(target) : false });
    // M3-3: the step reached by a live session, so that its end shows where it stopped.
    if (local.stage === "session" && gateway?.view && !screen.interrupted && !/^(S-|loading|paused|unknown)/.test(screen.code)) local.reachedPhase = screen.phase;
    return screen;
  }

  // ---------- drawing ----------

  _render() {
    if (!this._root) return;
    // While "Close without saving?" is open the screen behind it is not rebuilt: a tap meant for the
    // dialog never lands on a button that appeared under it. It is redrawn when the dialog closes.
    if (this._frame.querySelector(".wiz-dialog:not([hidden])")) { this._patch(this._screen()); return; }
    const screen = this._screen();
    this._current = screen;
    const { t } = this._context;
    const drawing = (position) => screen.illustration?.position === position ? illustrationMarkup(screen.illustration.id, t("wizIllustration"), esc) : "";
    // G2-11: a notice that comments a result sits right under the result box (or the stopwatch), before text and drawing.
    const resultNotices = '<div class="wiz-result-notices" aria-live="polite"></div>';
    // The header (cover name and address) is patched, not part of the frame: choosing a cover on A-01 keeps the list
    // and its scroll (M3-4).
    const signature = JSON.stringify([screen.code, screen.title, screen.body, screen.choice && { ...screen.choice, value: undefined },
      screen.field && { ...screen.field, disabled: undefined, error: undefined }, screen.box, screen.table, screen.technical, screen.precision,
      screen.profileBlock && { ...screen.profileBlock, name: screen.profileBlock.name && { label: screen.profileBlock.name.label, hint: screen.profileBlock.name.hint } },
      screen.saveInfo, screen.status, screen.preview, screen.illustration, screen.wait && screen.wait.text, screen.discard, screen.back, !!screen.picker, screen.results, screen.note, screen.help]);
    if (signature !== this._signature) {
      const codeChanged = this._renderedCode !== screen.code;
      // "What happens when I save?" opens with the summary; a reader's choice is kept while it stays on screen.
      const info = this._frame.querySelector(".wiz-save-info");
      this._local.saveInfoOpen = info ? info.open : true;
      // The slats explanation (G2-3) starts closed on every screen and keeps the reader's choice while it stays.
      const help = this._frame.querySelector(".wiz-help");
      this._local.helpOpen = !codeChanged && !!help?.open;
      // A choice that redraws the screen (a note under the chosen option) keeps the keyboard on that choice.
      const active = this._root.getRootNode().activeElement;
      const radio = !codeChanged && active?.type === "radio" && this._frame.contains(active) ? active.name : null;
      this._signature = signature;
      this._renderedCode = screen.code;
      this._root.dataset.code = screen.code;
      this._root.toggleAttribute("data-preview", screen.preview);
      this._frame.innerHTML = `
        <header class="wiz-head">
          ${screen.back ? `<button type="button" class="icon-button wiz-back" data-wiz="back" aria-label="${esc(t("wiz_T403"))}" title="${esc(t("wiz_T403"))}"><ha-icon icon="mdi:arrow-left" aria-hidden="true"></ha-icon></button>` : ""}
          <div class="wiz-head-text"><h3 id="wiz-cover" class="wiz-cover">${esc(screen.header.title)}</h3><p class="muted wiz-head-sub" hidden></p></div>
          ${screen.discard ? `<button type="button" class="wiz-discard" data-wiz="exit">${esc(t("wizDiscard"))}</button>` : ""}
          <button type="button" class="icon-button wiz-x" data-wiz="${screen.discard ? "exit" : "close"}" aria-label="${esc(screen.discard ? t("wizDiscard") : t("wiz_T158"))}" title="${esc(screen.discard ? t("wizDiscard") : t("wiz_T158"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button>
        </header>
        <div class="wiz-compact"><span class="wiz-dot" aria-hidden="true"></span><span class="wiz-compact-line"></span>
          <button type="button" class="wiz-steps-button" data-wiz="steps" aria-haspopup="dialog">${esc(t("wiz_T274"))}</button></div>
        <div class="wiz-columns">
          <nav class="wiz-steps" aria-label="${esc(t("wiz_T274"))}"></nav>
          <div class="wiz-main">
            ${screen.preview ? `<p class="wiz-preview" role="note"><ha-icon icon="mdi:eye-outline" aria-hidden="true"></ha-icon><span>${esc(t("wizPreview"))}</span></p>` : ""}
            <h4 class="wiz-title" tabindex="-1">${esc(screen.title)}</h4>${screen.subline ? `<p class="cal-note wiz-subline">${esc(screen.subline)}</p>` : ""}
            <div class="wiz-stopwatch" hidden${ILLUSTRATIONS[screen.illustration?.id] ? ` style="--wiz-stopwatch-width: ${ILLUSTRATIONS[screen.illustration.id].width}px"` : ""}><span class="wiz-stopwatch-label"></span><span class="wiz-stopwatch-value"></span></div>
            ${screen.results?.length ? "" : resultNotices}
            ${drawing("before-body")}
            ${screen.wait ? this._waitMarkup(screen.wait) : ""}
            ${screen.results?.length ? `<div class="wiz-results">${screen.results.map((tile) => `<div class="wiz-result${tile.invalid ? " is-invalid" : ""}"><span class="wiz-result-label">${esc(tile.label)}</span>
              <span class="wiz-result-value"><span class="wiz-result-number">${esc(tile.value)}</span><small> ${esc(tile.unit)}</small>${tile.extra ? `<span class="wiz-result-extra"> · ${esc(tile.extra)}</span>` : ""}</span></div>`).join("")}</div>${resultNotices}` : ""}
            ${screen.body ? `<div class="wiz-body">${rich(screen.body)}</div>` : ""}
            ${screen.help && !screen.choice ? this._helpMarkup(screen.help) : ""}
            ${screen.note ? `<p class="cal-note${screen.note.tone === "warning" ? " is-warning" : ""} wiz-note">${esc(screen.note.text)}</p>` : ""}
            ${screen.status.length ? `<div class="wiz-status">${screen.status.map((line) => `<p>${esc(line)}</p>`).join("")}</div>` : ""}
            ${drawing("after-body")}
            ${screen.box ? `<div class="wiz-box"><strong>${esc(screen.box.label)}</strong>${screen.box.lines.map((line) => `<p>${factMarkup(line)}</p>`).join("")}</div>` : ""}
            ${screen.choice ? this._choiceMarkup(screen.choice) : ""}
            ${screen.picker ? '<div class="wiz-picker"></div>' : ""}
            ${screen.field ? this._fieldMarkup(screen.field) : ""}
            ${screen.precision ? `<p class="wiz-precision">${inline(screen.precision)}</p>` : ""}
            ${screen.table ? this._tableMarkup(screen.table) : ""}
            ${screen.technical ? this._technicalMarkup(screen.technical) : ""}
            ${screen.profileBlock ? this._profileMarkup(screen.profileBlock) : ""}
            ${screen.saveInfo ? `<details class="wiz-accordion wiz-save-info"${this._local.saveInfoOpen ? " open" : ""}><summary>${esc(screen.saveInfo.title)}<ha-icon icon="mdi:chevron-down" aria-hidden="true"></ha-icon></summary>${rich(screen.saveInfo.body)}</details>` : ""}
            <div class="wiz-notices" aria-live="polite"></div>
          </div>
          <div class="wiz-actions"></div>
        </div>
        <div class="wiz-sheet" role="dialog" aria-modal="true" aria-label="${esc(t("wiz_T274"))}" hidden><div class="wiz-sheet-card" tabindex="-1">
          <div class="wiz-sheet-head"><h4 class="wiz-sheet-title">${esc(t("wiz_T274"))}</h4><button type="button" class="icon-button wiz-sheet-close" data-wiz="steps-close" aria-label="${esc(t("close"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button></div>
          <div class="wiz-sheet-steps"></div></div></div>
        <div class="wiz-dialog" role="alertdialog" aria-modal="true" aria-labelledby="wiz-dialog-title" aria-describedby="wiz-dialog-body" hidden><div class="wiz-dialog-card" tabindex="-1">
          <div class="wiz-dialog-head"><h4 id="wiz-dialog-title">${esc(t("wiz_T267"))}</h4><button type="button" class="icon-button wiz-dialog-x" data-wiz="dialog-x" hidden aria-label="${esc(t("close"))}" title="${esc(t("close"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button></div><p id="wiz-dialog-body"></p>
          <div class="actions"><button type="button" class="wiz-leave" data-wiz="leave">${esc(t("wiz_T270"))}</button>
            <button type="button" class="primary" data-wiz="stay">${esc(t("wiz_T269"))}</button></div></div></div>
        <div class="wiz-dialog wiz-nav-dialog" role="alertdialog" aria-modal="true" aria-labelledby="wiz-nav-title" aria-describedby="wiz-nav-body" hidden><div class="wiz-dialog-card" tabindex="-1">
          <div class="wiz-dialog-head"><h4 id="wiz-nav-title">${esc(t("wiz_T408"))}</h4><button type="button" class="icon-button wiz-dialog-x" data-wiz="dialog-x" hidden aria-label="${esc(t("close"))}" title="${esc(t("close"))}"><ha-icon icon="mdi:close" aria-hidden="true"></ha-icon></button></div><p id="wiz-nav-body"></p>
          <div class="actions"><button type="button" class="wiz-leave" data-wiz="nav-discard">${esc(t("wiz_T411"))}</button>
            <button type="button" data-wiz="nav-later">${esc(t("wiz_T410"))}</button>
            <button type="button" class="primary" data-wiz="nav-stay">${esc(t("wiz_T269"))}</button></div></div></div>`;
      this._actionsSignature = null;
      this._actionIds = null;
      this._pickerHtml = null;
      this._watchMore();
      if (radio) this._frame.querySelector(`.wiz-radios input[name="${radio}"]:checked`)?.focus({ preventScroll: true });
      // L-8: in the page's inline layouts the page is scrolled by `revealHead` (the head at the top on opening, kept in
      // view at every step), never by the focus; full screen, the focus scrolls the wizard's own content.
      if (codeChanged) queueMicrotask(() => {
        const inline = !layout.fullScreen();
        this._frame?.querySelector(".wiz-title")?.focus({ preventScroll: inline });
        if (inline) this._reveal();
      });
    }
    this._patch(screen);
  }

  /**
   * L-8b: after the step has been painted (two frames), the head is placed: at the top of the window on opening (once a
   * screen with its head is there), kept in view at every other step, never sent to the top of the page.
   */
  _reveal() {
    const root = this._root, frame = globalThis.requestAnimationFrame || ((callback) => setTimeout(callback, 16));
    frame(() => frame(() => {
      if (root !== this._root || !root?.isConnected) return;
      const always = this._revealOnOpen;
      this._revealOnOpen = false;
      revealHead(root, { always });
    }));
  }

  _engineHost() { return this._engine; }

  /**
   * A sheet from the bottom slides down before it hides (it slides up when shown, by CSS). Without motion (reduced
   * motion, or no media queries) it hides at once.
   */
  /** A confirmation hides at once while centred; as a sheet (window under 720 × 500 px) it slides down first. */
  _hideDialog(dialog, done) {
    if (layout.sheets()) { this._slideAway(dialog, done); return; }
    dialog.hidden = true;
    done?.();
  }

  _slideAway(element, done) {
    const finish = () => { element.classList.remove("is-leaving"); element.hidden = true; done?.(); };
    const motion = typeof matchMedia === "function" && !matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!motion || element.hidden) { finish(); return; }
    element.classList.add("is-leaving");
    setTimeout(finish, SHEET_MS);
  }

  /**
   * On the phone the content scrolls above a fixed action bar: a fade over the bar says there is more below, only
   * while there really is (it goes at the end of the scroll; on the wide layout nothing scrolls, so it never shows).
   */
  _watchMore() {
    const main = this._frame?.querySelector(".wiz-main"), actions = this._frame?.querySelector(".wiz-actions");
    if (!main || !actions) return;
    const update = () => actions.classList.toggle("has-more", main.scrollHeight - main.scrollTop - main.clientHeight > 1);
    main.addEventListener("scroll", update, { passive: true });
    this._moreObserver?.disconnect();
    if (typeof ResizeObserver === "function") {
      this._moreObserver = new ResizeObserver(update);
      this._moreObserver.observe(main);
      for (const child of main.children) this._moreObserver.observe(child);
    }
    this._moreUpdate = update;
    queueMicrotask(update);
  }

  /** Whatever changes within one screen: stepper, stopwatch, progress, notices, buttons, read-only, A-01's list. */
  _patch(screen) {
    const root = this._frame, { t } = this._context;
    queueMicrotask(() => this._moreUpdate?.());
    const picker = root.querySelector(".wiz-picker");
    if (picker && screen.picker) {
      const html = this._context.picker?.markup(screen.picker) ?? "";
      if (html !== this._pickerHtml) {
        // The list is redrawn in place: the control that had the focus (a radio, a chip, a header) gets it back.
        const active = root.getRootNode().activeElement;
        const focus = active && picker.contains(active) ? (active.dataset.wiz ? ["wiz", active.dataset.wiz] : active.name === "cover" ? ["cover", active.value]
          : active.dataset.pickSort ? ["pickSort", active.dataset.pickSort] : active.matches("[data-pick-filter]") ? ["pickFilter", ""] : null) : null;
        this._pickerHtml = html;
        // Patched in place: the rows, the scroll and the focus stay (M3-4).
        morph(picker, html);
        fitBars(picker);
        fitRows(picker);
        // X-3: a new choice only shows as selected (its notes open under it): nothing scrolls, the row stays where the
        // finger left it.
        if (focus) {
          const [kind, value] = focus;
          [...picker.querySelectorAll("button, input, select")].find((element) => (kind === "cover" ? element.name === "cover" && element.value : element.dataset[kind]) === value)
            ?.focus({ preventScroll: true });
        }
      }
    } else this._pickerHtml = null;
    const head = root.querySelector(".wiz-cover"), sub = root.querySelector(".wiz-head-sub");
    if (head && head.textContent !== screen.header.title) head.textContent = screen.header.title;
    if (sub) {
      // A cover's line as units (room, gateway, the address that never breaks); any other subtitle as plain text.
      const units = screen.header.units;
      const html = units ? [...units.lead.map((unit) => ["cal-row-unit", esc(unit)]), ...(units.bus ? [["cal-row-address", esc(units.bus)]] : [])]
        .map(([kind, part], index, all) => `<span class="${kind}">${part}${index < all.length - 1 ? " ·" : ""}</span>`).join(" ") : esc(screen.header.subtitle || "");
      if (sub._html !== html) { sub.innerHTML = html; sub._html = html; }
      sub.hidden = !screen.header.subtitle;
      sub.classList.toggle("wiz-head-placeholder", !!screen.header.placeholder);
    }
    const stepper = this._stepperMarkup(screen);
    for (const target of [root.querySelector(".wiz-steps"), root.querySelector(".wiz-sheet-steps")]) if (target.innerHTML !== stepper) target.innerHTML = stepper;
    root.querySelector(".wiz-compact-line").textContent = screen.stepper.line;
    // An ended session keeps the step it reached, greyed (M3-3).
    for (const target of [root.querySelector(".wiz-steps"), root.querySelector(".wiz-sheet-steps"), root.querySelector(".wiz-compact")]) target.toggleAttribute("data-interrupted", !!screen.stepper.interrupted);
    const watch = root.querySelector(".wiz-stopwatch");
    watch.hidden = !screen.stopwatch;
    if (screen.stopwatch) {
      root.querySelector(".wiz-stopwatch-label").textContent = screen.stopwatch.label;
      root.querySelector(".wiz-stopwatch-value").textContent = screen.stopwatch.value;
    }
    const wait = root.querySelector(".wiz-wait");
    if (wait && screen.wait) {
      // Stages done carry ✓, the current one ◐, the next ones an empty circle.
      // The bar and the time left sit under the stage in progress (after the text when there are no stages).
      const current = screen.wait.stages.findIndex((stage) => stage.state === "current");
      const stages = screen.wait.stages.map((stage, index) => `<li data-step-state="${stage.state}"><ha-icon icon="${STAGE_ICON[stage.state]}" aria-hidden="true"></ha-icon><span>${text.units(esc(stage.text))}</span>${index === current ? '<div class="wiz-wait-slot"></div>' : ""}</li>`).join("");
      const list = wait.querySelector(".wiz-wait-stages"), meter = wait.querySelector(".wiz-wait-meter");
      if (list.dataset.stages !== stages) {
        wait.append(meter);
        list.innerHTML = stages;
        list.dataset.stages = stages;
        list.querySelector(".wiz-wait-slot")?.replaceWith(meter);
      }
      list.hidden = !screen.wait.stages.length;
      // The bar is there for every run: the share already run, or moving back and forth while the duration is unknown;
      // not where nothing runs (`progress: false`, path B's preview, D-46).
      meter.hidden = screen.wait.progress === false;
      const bar = wait.querySelector(".wiz-progress"), share = screen.wait.progress?.value ?? null;
      bar.classList.toggle("is-indeterminate", share == null);
      if (share == null) bar.removeAttribute("aria-valuenow");
      else bar.setAttribute("aria-valuenow", String(Math.round(share * 100)));
      bar.querySelector("span").style.width = share == null ? "" : `${Math.round(share * 100)}%`;
      const remaining = wait.querySelector(".wiz-wait-remaining");
      remaining.textContent = screen.wait.remaining || "";
      remaining.hidden = !screen.wait.remaining;
    }
    const markup = (list) => list.map((notice) => `<p class="notice wiz-notice" data-tone="${notice.tone}" ${notice.tone === "error" ? 'role="alert"' : ""}>${text.units(esc(notice.text))}</p>`).join("");
    const top = root.querySelector(".wiz-result-notices");
    const notices = markup(screen.notices.filter((notice) => !(top && notice.result)));
    const box = root.querySelector(".wiz-notices");
    if (box.innerHTML !== notices) box.innerHTML = notices;
    if (top) { const first = markup(screen.notices.filter((notice) => notice.result)); if (top.innerHTML !== first) top.innerHTML = first; }
    const field = root.querySelector(".wiz-field input");
    if (field) field.disabled = !!screen.field?.disabled;
    // G3-4: a refused value says why, under the field; never a silent red.
    const fieldError = root.querySelector("#wiz-field-error");
    if (fieldError) {
      const message = screen.field?.error || "";
      if (fieldError.textContent !== message) fieldError.textContent = message;
      fieldError.hidden = !message;
      if (message) field?.setAttribute("aria-invalid", "true");
    }
    // L-9: a reading the field accepts but far from the model: a yellow warning under it, never a refusal.
    const warning = root.querySelector("#wiz-field-warning");
    if (warning) {
      const band = screen.field?.band, input = root.querySelector('[name="reading_cm"]'), value = input ? parseReading(input.value) : NaN;
      const far = !!band && Number.isFinite(value) && accepted(input) && (value < band.min || value > band.max) && !fieldError?.textContent;
      const message = far ? band.warning : "";
      if (warning.textContent !== message) warning.textContent = message;
      warning.hidden = !far;
    }
    const block = screen.profileBlock?.name;
    const line = root.querySelector(".wiz-name-line");
    if (line && block && line.textContent !== block.line) line.textContent = block.line;
    root.querySelector(".wiz-name-input")?.setAttribute("aria-invalid", String(block ? !block.valid : false));
    // Why the name cannot be saved, under the field (Save stays disabled meanwhile).
    const nameError = root.querySelector(".wiz-name-error");
    if (nameError) { nameError.textContent = block?.error || ""; nameError.hidden = !block?.error; }
    const actions = JSON.stringify([screen.actions.map((action) => [action.id, action.label, action.kind, action.note]), screen.readOnly, screen.links]);
    const column = root.querySelector(".wiz-actions");
    if (actions !== this._actionsSignature) {
      // The hold protects a tap from landing on a button that just appeared or changed. A button that only goes away
      // (Stop when the motor stops by itself) holds nothing back: the end stop never flickers disabled.
      const ids = screen.actions.map((action) => `${action.id}|${action.label}|${action.kind}`);
      const readOnly = JSON.stringify(screen.readOnly);
      if (!this._actionIds || readOnly !== this._readOnlySignature || ids.some((id) => !this._actionIds.includes(id))) this._guard();
      this._actionIds = ids;
      this._readOnlySignature = readOnly;
      const focused = column.contains(root.getRootNode().activeElement) ? root.getRootNode().activeElement.dataset.wiz : null;
      this._actionsSignature = actions;
      column.innerHTML = `${screen.readOnly ? `<div class="wiz-readonly"><p class="wiz-readonly-status">${esc(screen.readOnly.status)}</p><p>${esc(screen.readOnly.text)}</p>
          <button type="button" class="wiz-take ${screen.readOnly.primary || screen.readOnly.consequence ? "primary" : "secondary"}" data-wiz="take">${esc(screen.readOnly.take)}</button>
          ${screen.readOnly.consequence ? `<p class="muted">${esc(screen.readOnly.consequence)}</p>` : ""}</div>` : ""}
        ${screen.actions.map((action) => action.kind === "status" || action.kind === "state"
          ? `<p class="wiz-action status${action.kind === "state" ? " is-still" : ""}" data-wiz="${esc(action.id)}" role="status">${action.kind === "status" ? '<span class="wiz-spinner" aria-hidden="true"></span>' : ""}${esc(action.label)}</p>`
          : `<button type="button" class="wiz-action ${action.kind}" data-wiz="${esc(action.id)}"${action.note ? ` aria-describedby="wiz-note-${esc(action.id.replace(/\W/g, "-"))}"` : ""}>${esc(action.label)}</button>${action.note
          ? `<p class="wiz-action-note muted" id="wiz-note-${esc(action.id.replace(/\W/g, "-"))}">${esc(action.note)}</p>` : ""}`).join("")}
        ${screen.links?.length ? `<div class="wiz-more"><button type="button" class="wiz-more-toggle" data-wiz="more" aria-expanded="false" aria-controls="wiz-more-list">${esc(t("wiz_T529"))}<ha-icon icon="mdi:chevron-down" aria-hidden="true"></ha-icon></button>
          <div class="wiz-more-list" id="wiz-more-list">${screen.links.map((link) => `<button type="button" class="wiz-link" data-wiz="${esc(link.id)}">${esc(link.label)}</button>`).join("")}</div></div>` : ""}`;
      if (focused) column.querySelector(`[data-wiz="${focused}"]`)?.focus({ preventScroll: true });
    }
    // L-1: the other ways on stack under the actions; in the phone's bar they wait behind «Altre opzioni».
    const more = column.querySelector(".wiz-more");
    if (more) { more.classList.toggle("is-open", !!this._local.moreOpen); more.querySelector(".wiz-more-toggle").setAttribute("aria-expanded", String(!!this._local.moreOpen)); }
    const guarded = this._guarded();
    for (const action of screen.actions) {
      const button = column.querySelector(`[data-wiz="${action.id}"]`);
      if (!button || action.kind === "status" || action.kind === "state") continue;
      // N-06/Z-13: a reading's «Fatto, avanti» waits for a value in the field: off until the user types one. Z-2: after a
      // refused value it stays off until the value typed is one the field accepts.
      const input = action.id === "reading" ? root.querySelector('[name="reading_cm"]') : null;
      const empty = !!input && (!input.value.trim() || (this._local.fieldError != null && !accepted(input)));
      button.disabled = !!action.disabled || empty || (guarded && action.id !== "stop");
      // D-13 (decided 8 Oct): off only for a moment, enabling by itself (the hold after a change, a request or the motor
      // settling) keeps the light primary look; off until the user acts is the neutral grey.
      button.classList.toggle("is-settling", button.disabled && !empty && (!action.disabled || !!action.settling));
      // Disabled by the step itself (not by the short hold after a change): said to assistive technology too.
      if (action.disabled) button.setAttribute("aria-disabled", "true"); else button.removeAttribute("aria-disabled");
    }
    const take = column.querySelector('[data-wiz="take"]');
    if (take) { take.disabled = !!this._gateway?.status.busy || guarded; take.classList.toggle("is-settling", take.disabled); }
  }

  /** Hold the confirming buttons for CONFIRM_GUARD_MS, then draw them enabled again. */
  _guard() {
    if (!this._guardMs) return;
    this._guardUntil = performance.now() + this._guardMs;
    clearTimeout(this._guardTimer);
    const generation = this._generation;
    this._guardTimer = setTimeout(() => { if (generation === this._generation && this._frame) this._patch(this._screen()); }, this._guardMs + 10);
  }

  _guarded() { return !!this._guardMs && performance.now() < (this._guardUntil || 0); }

  _stepperMarkup(screen) {
    return `<p class="wiz-steps-line">${esc(screen.stepper.line)}</p>
      <ol>${screen.stepper.phases.map((phase) => `<li data-step-state="${phase.state}"${phase.state === "current" ? ' aria-current="step"' : ""}><span class="wiz-step-mark" aria-hidden="true"></span><span class="wiz-step-label">${esc(phase.label)}</span>
        ${phase.substeps.length ? `<ul>${phase.substeps.map((item) => `<li>${item.label ? `${esc(item.label)}: <strong>${esc(item.value)}</strong>` : esc(item.value)}</li>`).join("")}</ul>` : ""}</li>`).join("")}</ol>`;
  }

  _waitMarkup(wait) {
    return `<div class="wiz-wait" role="status">${wait.text ? `<p>${text.units(esc(wait.text))}</p>` : ""}<ol class="wiz-wait-stages"></ol>
      <div class="wiz-wait-meter"><div class="wiz-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-label="${esc(this._context.t("wiz_T027"))}"><span></span></div>
      <p class="wiz-wait-remaining muted" aria-live="off" hidden></p></div></div>`;
  }

  /** A closed-by-default explanation (G2-3): a native <details>, so it opens from the keyboard and reads as a toggle. */
  _helpMarkup(help) {
    // Q-32: the panel's one disclosure (`cal-disclosure`): a blue text link with a chevron, over a short paragraph.
    return `<details class="cal-disclosure wiz-help"${this._local.helpOpen ? " open" : ""}><summary><span class="cal-disclosure-label">${esc(help.summary)}</span><ha-icon icon="mdi:chevron-down" aria-hidden="true"></ha-icon></summary>${rich(help.text)}</details>`;
  }

  _choiceMarkup(choice) {
    // G4-3: a label written as «**title**\nexplanation» (C-02) is a title and its explanation, not one flex line with a
    // break in it (the break took a whole row: 24 px between them).
    const parts = (option) => {
      if (option.plain) return [esc(option.label), ""];
      const [first, ...rest] = option.label.split("\n");
      // The bold run closes on the next line in the sheet («**title\n**explanation»): close it on the title.
      const head = /^\*\*/.test(first) && !/^\*\*.*\*\*/.test(first) ? `${first.trim()}**` : first;
      const tail = rest.join(" ").trim().replace(/^\*\*\s*/, "");
      return tail ? [inline(head), `<span class="wiz-radio-explain">${inline(tail)}</span>`] : [inline(option.label), ""];
    };
    return `<fieldset class="wiz-choice wiz-radios"><legend${choice.legendHidden ? ' class="visually-hidden"' : ""}>${esc(choice.label)}</legend>${choice.help ? this._helpMarkup(choice.help) : ""}${choice.options.map((option) =>
      `<label class="wiz-radio${option.disabled ? " is-disabled" : ""}"><input type="radio" name="${esc(choice.name)}" value="${esc(option.value)}" ${option.value === choice.value ? "checked" : ""} ${option.disabled ? "disabled" : ""}><span class="wiz-radio-text"><span class="wiz-radio-label">${parts(option)[0]}${option.badge
        ? ` <span class="badge wiz-recommended">${esc(option.badge)}</span>` : ""}</span>${parts(option)[1]}${[].concat(option.note || []).map((line) => `<small class="muted">${text.units(esc(line))}</small>`).join("")}${option.warning
        ? `<span class="cal-note is-warning wiz-radio-warning">${text.units(esc(option.warning))}</span>` : ""}</span></label>`).join("")}</fieldset>`;
  }

  _fieldMarkup(field) {
    const value = field.value == null ? "" : `${field.value}`;
    return `<form class="wiz-field" novalidate autocomplete="off"><label>${esc(field.label)}<span class="input-suffix"><input name="reading_cm" type="text" inputmode="decimal" autocomplete="off" value="${esc(value)}" aria-describedby="wiz-field-hint wiz-field-error" data-kind="${esc(field.kind)}" data-min="${field.min}" data-max="${field.max}"><span>cm</span></span></label>
      <p id="wiz-field-hint" class="muted">${text.units(esc(field.hint))}</p><p id="wiz-field-error" class="wiz-field-error" role="alert" hidden></p>
      <p id="wiz-field-warning" class="cal-note is-warning wiz-field-warning" role="status" hidden></p></form>`;
  }

  _tableMarkup(table) {
    return `<table class="wiz-table"><thead><tr>${table.headers.map((header) => `<th scope="col">${esc(header)}</th>`).join("")}</tr></thead>
      <tbody>${table.rows.map((row) => `<tr><th scope="row">${esc(row.label)}</th><td${table.mutedBefore ? ' class="muted"' : ""}>${row.changed ? `<s>${esc(row.before)}</s>` : esc(row.before)}</td><td>${esc(row.after)}</td></tr>`).join("")}</tbody></table>`;
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
      ${block.name ? `<label>${esc(block.name.label)}<input class="wiz-name-input" name="profile_name" maxlength="64" autocomplete="off" value="${esc(block.name.value)}" aria-describedby="wiz-name-error wiz-name-hint"></label>
        <p id="wiz-name-error" class="wiz-name-error" role="alert" hidden></p>
        <p id="wiz-name-hint" class="muted">${esc(block.name.hint)}</p><p class="wiz-name-line">${esc(block.name.line)}</p>` : ""}</div>`;
  }

  // ---------- events ----------

  _keydown(event) {
    const dialog = this._frame.querySelector(".wiz-dialog:not([hidden])"), sheet = this._frame.querySelector(".wiz-sheet");
    const open = dialog || (!sheet.hidden ? sheet : null);
    if (!open) return;
    if (event.key === "Escape") {
      event.preventDefault();
      if (open === dialog && dialog.classList.contains("wiz-nav-dialog")) this._navAnswer(false);
      else if (open === dialog) this._closeDialog();
      else { this._slideAway(sheet); this._frame.querySelector('[data-wiz="steps"]').focus(); }
    } else if (event.key === "Tab") {
      // A modal keeps the keyboard inside it, as the native dialog would.
      const focusable = [...open.querySelectorAll("button:not([hidden]):not(:disabled)")];
      const active = this._root.getRootNode().activeElement, first = focusable[0], last = focusable.at(-1);
      if (!focusable.includes(active)) { event.preventDefault(); first?.focus(); }
      else if (event.shiftKey && active === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && active === last) { event.preventDefault(); first.focus(); }
    }
  }

  _input(event) {
    if (event.target.name === "profile_name") { this._local.profileName = event.target.value.trim(); this._patch(this._screen()); }
    if (event.target.name === "reading_cm") {
      // Z-2: a refused value stays marked until what is typed is accepted; then the message goes and the button comes on.
      if (this._local.fieldError != null && accepted(event.target)) { this._local.fieldError = null; event.target.removeAttribute("aria-invalid"); }
      // N-06: the button follows the field (typing never redraws the field itself).
      this._patch(this._screen());
    }
  }

  _change(event) {
    const { name, value, checked } = event.target;
    if (name === "save_profile") { this._local.saveProfile = checked; this._render(); }
    else if (name === "save_choice") { this._local.saveChoice = value; this._render(); }
    else if (name === "slats") this._local.slats = value !== "no";
    else if (name === "case") { this._local.scope = value; this._render(); }
    else if (name === "cover") { this._local.coverKey = value; this._local.coverPicked = true; this._render(); }
    else if (event.target.matches?.("select[data-pick-filter]")) { this._local.pickFilter = value; this._render(); }
    else if (event.target.dataset?.pickSort) {
      // The phone's "Sort by" bar of A-01: the list's shared order, as in the tab.
      const [key, dir] = value.split(":");
      this._context.picker?.sort(key, dir === "desc" ? "desc" : "asc");
      this._render();
    }
    else if (name === "profile") { this._local.profileId = value; this._render(); }
    else if (name === "path") { this._local.pathChoice = value; this._render(); }
  }

  _click(event) {
    // A click on a confirmation's backdrop (outside its card) is "Continue the calibration".
    if (event.target.classList?.contains("wiz-dialog")) {
      if (event.target.classList.contains("wiz-nav-dialog")) this._navAnswer(false); else this._closeDialog();
      return;
    }
    // M6-1 (R7-7 for every sheet): a tap on the Steps sheet's backdrop closes it, as its ✕ does.
    if (event.target.classList?.contains("wiz-sheet")) { this._act("steps-close"); return; }
    const button = event.target.closest("button[data-wiz]");
    if (!button || button.disabled) return;
    event.preventDefault();
    this._act(button.dataset.wiz);
  }

  _value(name) { return this._frame.querySelector(`[name="${name}"]:checked, select[name="${name}"]`)?.value; }

  async _act(id) {
    const local = this._local, gateway = this._gateway;
    if (id === "steps") { const sheet = this._frame.querySelector(".wiz-sheet"); sheet.hidden = false; focusOnOpen(sheet.querySelector(".wiz-sheet-card"), sheet.querySelector("button")); return; }
    if (id === "more") { local.moreOpen = !local.moreOpen; return this._render(); }
    if (id === "steps-close") { this._slideAway(this._frame.querySelector(".wiz-sheet")); this._frame.querySelector('[data-wiz="steps"]').focus(); return; }
    if (id === "exit") { this._exit(); return; }
    if (id === "back") { this._back(); return; }
    if (id.startsWith("pick-filter:")) { local.pickFilter = id.slice(12); return this._render(); }
    // R-5: the ✕ of a confirmation shown as a sheet keeps the calibration, as «Continua la calibrazione».
    if (id === "dialog-x") { this._act(this._frame.querySelector(".wiz-nav-dialog")?.hidden === false ? "nav-stay" : "stay"); return; }
    if (id === "stay") { this._closeDialog(); return; }
    if (id === "nav-stay") { this._navAnswer(false); return; }
    if (id === "nav-later") { this._navAnswer(true); return; }
    if (id === "nav-discard") { this._navDiscard(); return; }
    if (id === "leave") { this._leave(); return; }
    if (id === "close") { this._finish(); return; }
    if (id === "choose") { if (!local.coverPicked) return; local.pathChoice = null; local.stage = "path"; return this._render(); }
    if (id === "path" || id.startsWith("path:")) {
      const path = id === "path" ? this._value("path") || local.pathChoice : id.slice(5);
      if (!["A", "B", "C"].includes(path)) return;
      local.path = path;
      local.stage = local.path === "A" ? "before" : local.path === "B" ? "profile" : "current";
      if (local.path === "B") local.profileId = this._profiles()[0]?.id;
      return this._render();
    }
    if (id === "profile") { local.profileId = this._value("profile") || local.profileId; local.stage = "before"; return this._render(); }
    if (id === "current") { local.stage = "case"; return this._render(); }
    if (id === "case") { local.scope = this._value("case") || local.scope || "points_only"; local.stage = "before"; return this._render(); }
    if (id === "begin") { if (local.stage === "before") local.slats = (this._value("slats") ?? (local.slats === false ? "no" : "yes")) !== "no"; return this._begin(); }
    if (id.startsWith("ack:")) {
      local[{ lift: "ackLift", ascent: "ackAscent", descent: "ackDescent", readings: "ackReadings" }[id.slice(4)]] = true;
      if (id === "ack:readings") return this._send("next");
      return this._render();
    }
    if (id === "reading") return this._reading();
    // G3-2: «The edge is still resting» repeats the lift-off run without a value: the backend's path of a reading under
    // 1 cm (0 cm), remembered as coming from the button for the notice of the repeat (G3-3).
    if (id === "resting") { this._local.lastGap = 0; this._local.liftOrigin = "button"; this._local.fieldError = null; return this._send("reading", { reading_cm: 0 }); }
    // The guided protocol's own movements ("open", "close") are named apart from closing the wizard.
    if (id.startsWith("run:")) return this._send(id.slice(4));
    if (id === "endpoint" && local.fullRun) {
      // L-3: ② exists only while the motor runs. A click that races the stop's view is not a confirmation: the run is
      // not valid, as if ② had never been there; otherwise the press decides the run, even across a stop in flight.
      if (gateway?.view?.motor_stopped === true && !local.fullRun.pressed) { this._closeFullRun(gateway.view); return this._render(); }
      const run = local.fullRun;
      run.pressed = true;
      // A refused ② confirmed nothing: the run is judged again as if it had not been pressed.
      return Promise.resolve(this._send("endpoint")).then(() => {
        if (local.fullRun !== run || !this._gateway?.status.error) return;
        Object.assign(run, { pressed: false, decided: false });
        this._closeFullRun(this._gateway.view);
        this._render();
      });
    }
    const open = gateway?.view;
    if (id === "repeat" && local.invalidRun && open && !open.preview && open.mode === "geometry" && ["opening", "closing"].includes(open.step)
      && ["opening", "closing", "geometry_wait_stop"].includes(open.phase)) {
      // L-3: the backend is still in the stopped run or confirming its end: the end is confirmed first (nothing moves),
      // the repeat follows on the result it reaches.
      local.repeatQueued = true;
      if (local.fullRun) this._closeFullRun(open);
      return this._render();
    }
    // D-11: the time of a run judged not valid stays out of the stepper until a new run replaces it.
    if (id === "repeat" && local.invalidRun) {
      const key = local.invalidRun.step === "opening" ? "opening_time" : "closing_time";
      local.discarded = { step: local.invalidRun.step, value: gateway?.view?.values?.[key] ?? null };
    }
    if (id === "repeat") local.invalidRun = null;
    if (["next", "lift", "endpoint", "repeat", "repeat_step", "accept", "repeat_check", "redo_readings", "continue_anyway", "continue", "skip"].includes(id)) return this._send(id);
    // "It did not do what it should" (A-05): today the run is stopped and S-01 offers to start over (L2 will repeat the step).
    if (id === "stop" || id === "misbehaved") { local.misbehaved = id === "misbehaved"; local.stopSent = true; this._closeDialog(false); return gateway?.stop(); }
    // Ownership gained by a claim or a reconnection moves nothing until this tab presses something.
    if (id === "take") { local.arm = null; return gateway?.claim(); }
    if (id === "reconnect") { local.arm = null; return gateway?.reconnect(); }
    if (id === "save") return this._save();
    if (id === "refine") return this._fineTune();
    if (id === "assign-profile") {
      // The profile just written: by its id when it was updated, by its name when it was created (the id comes with the
      // overview Home Assistant publishes after the save).
      const item = this._item(), saved = local.saved || {};
      if (!item) return;
      this._context.onAssignProfile?.({ entryId: item.entry.entry_id, profileId: saved.target === "profile_update" ? item.profile?.id ?? null : null,
        name: saved.name ?? item.profile?.name ?? null });
      return;
    }
    if (id === "restart") {
      // G4-6: the guided session has no repeat verb: this attempt is cancelled (nothing was saved) and the times start
      // again from the briefing, with the cover to be closed.
      const gateway = this._gateway;
      Promise.resolve(gateway?.act("cancel")).catch(() => {}).finally(() => {
        if (this._gateway !== gateway) return;
        this._dropGateway(); Object.assign(local, freshFlags(), { stage: "before" }); this._render();
      });
      return;
    }
    if (id === "start-over") {
      // Fine-tuning starts again from the values just saved; everything else from "Before you begin".
      if (local.refining && local.base) { this._startRefine(local.base); return this._render(); }
      this._dropGateway(); Object.assign(local, freshFlags(), { stage: "before" }); return this._render();
    }
    if (id === "another") { this._dropGateway(); Object.assign(local, freshFlags(), { stage: "choose", entry: "choose", path: "A", scope: null, saved: null, refining: false, base: null, baseSaved: false, coverKey: "", coverPicked: false }); return this._render(); }
    if (id === "open-cover") { const entityId = this._item()?.cover.entity_id; const { onOpenCover } = this._context; this._finish(); onOpenCover?.(entityId); return; }
    if (id === "correct") {
      // B → C: the cover is measured on its own; nothing of the preview was written.
      this._dropGateway();
      Object.assign(local, freshFlags(), { path: "C", scope: "times_and_rolls", stage: "current" });
      return this._render();
    }
  }

  /** One choice back, before any session: what was chosen stays chosen; from the first screen, back to the list. */
  _back() {
    const local = this._local;
    const to = { choose: null, path: local.entry === "path" ? null : "choose", profile: "path", current: local.entry === "current" ? null : "path", case: "current",
      before: local.path === "A" ? "path" : local.path === "B" ? "profile" : "case" }[local.stage];
    if (to === undefined) return;
    if (to === null) { this._finish(); return; }
    if (to === "path") local.pathChoice = local.path;
    local.stage = to;
    this._render();
  }

  _send(action, extra = {}) {
    if (!this._gateway) return;
    this._arm(this._gateway.view);
    // A repeated run is confirmed again on its own screen (A-12, A-15) once measured.
    if (action === "repeat" && this._current?.code.endsWith("-12")) this._local.ackAscent = false;
    if (action === "repeat" && this._current?.code.endsWith("-15")) this._local.ackDescent = false;
    return this._gateway.act(action, extra);
  }

  _reading() {
    const input = this._frame.querySelector('[name="reading_cm"]');
    if (!input) return;
    const value = parseReading(input.value), min = Number(input.dataset.min), max = Number(input.dataset.max);
    if (!Number.isFinite(value) || value < min || value > max) {
      // Outside the accepted range of an intermediate reading the screen names the range; nothing is sent.
      this._local.fieldError = Number.isFinite(value) ? value : "nan";
      this._patch(this._screen());
      const field = this._frame.querySelector('[name="reading_cm"]');
      field.setAttribute("aria-invalid", "true");
      field.focus();
      // The reason under the field stays in view above the phone's action bar.
      this._frame.querySelector("#wiz-field-error:not([hidden])")?.scrollIntoView?.({ block: "nearest" });
      return;
    }
    this._local.fieldError = null;
    // The lift-off gap as typed (G2-9): a value under the backend's 1 cm counts as still resting, and the screen of the
    // repeated run names it. The backend uses the number as sent, without rounding (0.5 is under 1).
    if (input.dataset.kind === "gap") { this._local.lastGap = value; this._local.liftOrigin = "typed"; }
    return this._send("reading", { reading_cm: value });
  }

  _save() {
    const screen = this._current, local = this._local;
    const action = screen.actions.find((item) => item.id === "save");
    if (!action || action.disabled || !this._gateway) return;
    const name = screen.profileBlock?.name?.value;
    // Path B saves no measured value: the cover follows the chosen profile (L5b).
    local.pendingSave = local.path === "B" ? { target: "follow_profile", name: null } : { target: action.target || "profile_new", name };
    // A new profile for a cover that followed another, which no other cover follows: that profile will be left alone.
    const previous = this._item()?.profile;
    if (local.pendingSave.target === "profile_new" && previous && !previous.assigned_to.some((id) => id && id !== this._item().cover.entity_id)) {
      local.pendingSave.orphan = previous.name;
    }
    this._arm(this._gateway.view);
    return this._gateway.save(local.pendingSave);
  }

  // ---------- sessions ----------

  _newGateway(kind, plan, values) {
    const generation = this._generation;
    const onChange = (change) => {
      if (generation !== this._generation || !this._root) return;
      // A tick may end a positioning (A-04 → A-05): a new screen is drawn whole, the same one only patched.
      if (change === "tick") {
        this._autoEndpoint(this._gateway?.view);
        this._closeFullRun(this._gateway?.view);
        const screen = this._screen(); if (screen.code !== this._renderedCode) this._render(); else this._patch(screen); return;
      }
      this._viewChanged();
    };
    this._gateway = kind === "live" ? new LiveCalibrationGateway({ onChange })
      : new PreviewCalibrationGateway({ onChange, plan, values, ...(this._stageMs != null ? { stageMs: this._stageMs } : {}) });
    if (kind === "live") this._watchLease();
    return this._gateway;
  }

  _dropGateway() { clearInterval(this._leaseTimer); this._leaseTimer = null; this._gateway?.close(); this._gateway = null; }

  /** The idle expiry warning counts down without any message from Home Assistant: redraw it every 15 s. */
  _watchLease() {
    clearInterval(this._leaseTimer);
    this._leaseTimer = setInterval(() => {
      if (!this._root || !this._gateway?.view?.idle_expires_at) return;
      const screen = this._screen(); if (screen.code !== this._renderedCode) this._render(); else this._patch(screen);
    }, 15000);
  }

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
    Object.assign(local, freshFlags(), { stage: "session" });
    this._arm(null, true);
    if (local.path === "B" || (local.path === "C" && local.scope === "points_only")) {
      // Path B skips the travel measurement when the cover's travel is already saved (only the check remains).
      this._newGateway("preview", local.path === "B" ? "profile" : "rolls", { ...this._baseValues(item), skip_travel: local.path === "B" && item.cover.travel_cm > 0 }).start();
    } else {
      this._newGateway("live").start({ ...this._liveContext(), mode: local.path === "C" && local.scope === "times_only" ? "guided" : "geometry", slats: local.slats !== false });
    }
    this._render();
  }

  _resume(session, item) {
    const local = this._local;
    if (item) local.coverKey = key(item);
    // The view has no path: a slat and roll measurement of a cover that already follows a profile is the
    // correction "remeasure everything" (C), of any other cover the first of its type (A).
    const correction = session.mode === "geometry" && !!item?.profile, timesOnly = session.mode === "guided";
    Object.assign(local, freshFlags(), { stage: "session", path: correction || timesOnly ? "C" : "A",
      scope: timesOnly ? "times_only" : correction ? "times_and_rolls" : null, slats: session.slats !== false });
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

  /**
   * "Continue with fine-tuning" on A-34: the base calibration is saved, so fine-tuning (A-22…A-34, quarter readings and
   * the check) starts at once on the values just saved, in the same wizard, the stepper at Fine-tuning. Its end says
   * that the calibration before it was saved (T322).
   */
  _fineTune() {
    const local = this._local, base = local.base;
    if (!base || !this._item()) return;
    local.saved = null;
    local.baseSaved = true;
    this._startRefine(base);
    this._render();
  }

  /** Fine-tuning A-22…A-34 on `base`: simulated until the backend offers it (L5c). */
  _startRefine(base) {
    const local = this._local;
    this._dropGateway();
    // The readings of the calibration it refines stay for the stepper.
    Object.assign(local, freshFlags(), { stage: "session", refining: true, base, baseReadings: local.baseReadings });
    this._newGateway("preview", "refine", { opening_time: base.opening, closing_time: base.closing, slat_time_s: base.slat ?? 0,
      opening_roll: base.opening_roll, closing_roll: base.closing_roll, travel_cm: base.travel }).start();
  }

  _viewChanged() {
    const view = this._gateway?.view, local = this._local;
    // A refused value belongs to the step it was typed for; a refusal from Home Assistant to the phase it came in.
    if (view?.sequence !== local.fieldSequence) { local.fieldError = null; local.fieldSequence = view?.sequence; }
    if (view && view.phase !== local.errorPhase) { if (local.errorPhase !== undefined) this._gateway.clearError?.(); local.errorPhase = view.phase; }
    if (view?.phase === "review" && !view.preview) {
      local.review = { opening: view.values?.opening_time, closing: view.values?.closing_time, slat: view.geometry?.slat_time_s ?? null,
        travel: view.mode === "geometry" ? view.travel_cm : null, opening_roll: view.geometry?.opening_roll ?? null, closing_roll: view.geometry?.closing_roll ?? null,
        lift: view.samples?.lift ?? null, gap: view.readings?.gap ?? null };
      local.baseReadings = { ...view.readings };
    }
    if (view?.preview && view.phase === "saved") { this._saved(view.saved); return; }
    if (view?.preview && view.phase === "cancelled") { this._finish(); return; }
    this._trackRun(view);
    this._trackFullRun(view);
    this._autoEndpoint(view);
    this._closeFullRun(view);
    this._queuedRepeat(view);
    this._autoNext(view);
    this._unloadGuard(this._liveOpen());
    this._render();
  }

  /**
   * A positioning run to an end stop (`home`, `reset`, `top`) lasts the share of the travel still ahead: the cover's
   * estimated position (Home Assistant's `current_position`) is read once, when the run starts.
   */
  _trackRun(view) {
    const local = this._local;
    const run = !!view && !view.preview && ["home", "reset", "top"].includes(view.step)
      && ["starting_close", "starting_open", "closing", "opening"].includes(view.phase);
    if (!run) { local.run = null; return; }
    if (local.run?.step === view.step) return;
    const position = this._context.hass.states?.[this._item()?.cover.entity_id]?.attributes?.current_position;
    // Who owned the run when it started, and on which subscription: an automatic end stop needs both unchanged.
    local.run = { step: view.step, position: Number.isFinite(position) ? position : null, attachment: view.attachment ?? null,
      owned: !!view.owner && !view.read_only, sent: false };
  }

  /** The full ascent and descent (A-11, A-14 and their C clones): who owned the run when it started, on which subscription. */
  _trackFullRun(view) {
    const local = this._local;
    // The guided times-only runs (G4-6) are full runs too: their direction is their step.
    const step = view?.mode === "guided" ? (["starting_open", "opening"].includes(view.phase) ? "opening" : ["starting_close", "closing"].includes(view.phase) ? "closing" : null)
      : view?.step;
    const full = !!view && !view.preview && ["geometry", "guided"].includes(view.mode)
      && ((step === "opening" && ["starting_open", "opening"].includes(view.phase)) || (step === "closing" && ["starting_close", "closing"].includes(view.phase)));
    if (!full) { local.fullRun = null; return; }
    if (local.fullRun?.step === step) return;
    // `pressed`: ② was pressed in this tab while the motor ran; `sent`: the end of a run not valid was confirmed.
    local.fullRun = { step, pressed: false, decided: false, sent: false };
    local.invalidRun = null;
  }

  /**
   * How a full run ended by the bus is judged (R8-7, L-3): ② exists only while the motor runs. A press before the stop
   * reached this tab gives the run's time (the backend takes the frame's time for a press that crossed it); a stop
   * before any press (a wall switch, any stop) or at an actuator's timer (59-65 s) makes the result not valid at once.
   * Only the view decides, so a tab that opened, resumed or claimed the session after the stop judges it the same way.
   */
  _judgeFullRun(view) {
    const run = this._local.fullRun;
    if (!run || run.decided || view?.motor_stopped !== true || view.stopped_elapsed == null) return null;
    const verdict = stopVerdict(view.stopped_elapsed);
    return verdict === "timer" ? "timer" : run.pressed ? "valid" : verdict;
  }

  /**
   * A run judged not valid is shown as such by every tab, a reader's too. Its end stop is then confirmed by whichever
   * tab owns the session now (Home Assistant records the frame's time; nothing moves, the motor has already stopped),
   * so the result screen can offer only «Ripeti la corsa». Never after a lost connection, an error or with a request
   * pending; once per run.
   */
  _closeFullRun(view) {
    const local = this._local, run = local.fullRun, status = this._gateway?.status || {};
    if (!run) return;
    const verdict = this._judgeFullRun(view);
    if (verdict) { run.decided = true; local.invalidRun = verdict === "valid" ? null : { step: run.step, reason: verdict }; }
    if (!local.invalidRun || run.pressed || run.sent || view?.motor_stopped !== true) return;
    if (!view.owner || view.read_only || status.lost || status.error || status.busy) return;
    run.sent = true;
    queueMicrotask(() => {
      if (this._gateway?.view === view && !this._gateway.status.busy) this._send("endpoint"); else run.sent = false;
    });
  }

  /** «Ripeti la corsa» pressed while the stopped run was still open: sent on the result its confirmed end reaches. */
  _queuedRepeat(view) {
    const local = this._local, status = this._gateway?.status || {};
    if (!local.repeatQueued || !view) return;
    const result = view.mode === "geometry" && ((view.step === "opening" && view.phase === "reading") || (view.step === "half_open" && view.phase === "briefing"));
    const guided = view.mode === "guided" && ["confirm_open", "review"].includes(view.phase);
    if (!result && !guided) {
      if (!["opening", "closing", "geometry_wait_stop"].includes(view.phase)) local.repeatQueued = false;
      return;
    }
    local.repeatQueued = false;
    if (!view.owner || view.read_only || status.lost || status.error) return;
    queueMicrotask(() => { if (this._gateway?.view === view && !this._gateway.status.busy) this._act(guided ? "restart" : "repeat"); });
  }

  /**
   * The returns of the tape readings continue by themselves: the return to the top before the half-descent reading
   * and the return to the bottom before a repeated half-ascent reading confirm their end stop when the motor stops by
   * itself, or once the measured time of that direction plus a margin has passed. The button stays as a shortcut and
   * Stop is always there. As `_autoNext`: only for the owner, on the subscription the run started on, never after a
   * lost connection, an error or a claim, once per run; the press it makes arms the next automatic step as a press would.
   */
  _autoEndpoint(view) {
    const local = this._local, run = local.run, status = this._gateway?.status || {};
    if (!run || run.sent || !view || view.preview || view.mode !== "geometry" || !local.ackReadings) return;
    const returning = (view.step === "top" && view.phase === "opening") || (["reset", "home"].includes(view.step) && view.phase === "closing");
    if (!returning || run.step !== view.step) return;
    if (!run.owned || !view.owner || view.read_only || status.lost || status.error || status.busy || (view.attachment ?? null) !== run.attachment) {
      run.sent = true;
      return;
    }
    const full = view.step === "top" ? view.values?.opening_time : view.values?.closing_time;
    const elapsed = this._gateway.elapsed() ?? 0;
    if (view.motor_stopped !== true && !(full > 0 && elapsed >= full + AUTO_ENDPOINT_MARGIN_SECONDS)) return;
    run.sent = true;
    queueMicrotask(() => { if (this._gateway?.view === view && !this._gateway.status.busy) this._send("endpoint"); });
  }

  /** A press of this tab arms one automatic `next`: it remembers the view it was made on and its subscription. */
  _arm(view, start = false) {
    this._local.arm = { sequence: view?.sequence ?? -1, attachment: view?.attachment ?? null, start };
  }

  /**
   * Movements the mockups show as automatic after a press: the return to a known end stop and the runs of the tape
   * readings. THE RULE: an automatic verb is sent only on the view that immediately follows a press of the user in
   * this tab (through the movement and the stop that press started, never past a stop that waits for the user),
   * once per `sequence`, and never after a replayed subscription (a new `attachment`: Home Assistant reconnected),
   * a reconnection, a claim, a lost connection, a refused verb, or a view this tab does not own.
   */
  _autoNext(view) {
    const local = this._local, arm = local.arm, status = this._gateway?.status || {};
    if (!arm || !view || view.preview) return;
    // A start has no view yet: the first one it receives names its subscription.
    if (arm.start && arm.attachment === null && view.attachment) arm.attachment = view.attachment;
    const stale = view.mode !== "geometry" || !view.owner || view.read_only || status.lost || status.error
      || (arm.attachment !== null && view.attachment !== arm.attachment);
    if (stale) { local.arm = null; return; }
    if (view.sequence <= arm.sequence) return;
    if (view.phase !== "briefing") {
      // Still moving or stopping because of that press; anything else is a stop that waits for the user.
      if (!TRANSIT.includes(view.phase)) local.arm = null;
      return;
    }
    // The answer to the press arrives while it is still pending: decide once it has settled.
    if (status.busy) return;
    local.arm = null;
    const due = (view.step === "home" && arm.start) || (view.step === "reset" && !view.gap_warning) || view.step === "top"
      || (["half_open", "half_close"].includes(view.step) && local.ackReadings);
    if (!due) return;
    queueMicrotask(() => { if (this._gateway?.view === view) this._gateway.act("next"); });
  }

  _saved(previewSaved) {
    const local = this._local;
    const target = previewSaved?.target ?? local.pendingSave?.target;
    // The saved screen still shows what the steps measured, and whether the last part was a preview.
    // D-47: path B's stepper keeps the travel typed in B-04 too.
    if (this._gateway?.preview) local.fineReadings = { ...(this._gateway.view?.readings || {}), check: this._gateway.view?.check ?? null, travel: this._gateway.view?.travel_cm ?? null };
    local.saved = { target, name: previewSaved?.name ?? local.pendingSave?.name ?? null, travel_cm: this._gateway?.view?.travel_cm ?? local.review?.travel ?? null,
      preview: !!this._gateway?.preview, orphan: this._gateway?.preview ? null : local.pendingSave?.orphan ?? null };
    if (local.path === "B") local.saved.target = "follow_profile";
    local.stage = "saved";
    if (!local.refining && local.review) local.base = { ...local.review };
    this._dropGateway();
    this._render();
  }

  // ---------- leaving ----------

  /** A live session this tab owns and that is still open: leaving the tab leaves it open in Home Assistant. */
  _liveOpen() {
    return !!this._gateway && !this._gateway.preview && this._sessionOpen() && !!this._gateway.view?.owner;
  }

  /**
   * The panel asks before it moves away from the tab (another tab, gateway, category, filter): with a live session
   * open, "Calibration in progress" offers to stay, to leave it open and resume it later, or to cancel it. Returns
   * null when there is nothing to ask, otherwise a promise of whether the panel may leave.
   */
  beforeLeave() {
    if (!this._root || !this._liveOpen()) return null;
    if (this._navResolve) return this._navPromise;
    const dialog = this._frame.querySelector(".wiz-nav-dialog"), { t } = this._context;
    // How long Home Assistant keeps it open for its owner (30 minutes at rest, 10 after a movement).
    const seconds = this._gateway.view?.recovery_seconds;
    const minutes = Math.max(1, Math.round((Number.isFinite(seconds) ? seconds : IDLE_LEASE_SECONDS) / 60));
    dialog.querySelector("#wiz-nav-body").textContent = text.fill(t("wiz_T409"), { minutes, tab: t("calTabTab") });
    this._closeDialog(false);
    dialog.querySelector(".wiz-dialog-x").hidden = !layout.sheets();
    dialog.hidden = false;
    this._root.classList.add("has-dialog");
    focusOnOpen(dialog.querySelector(".wiz-dialog-card"), dialog.querySelector('[data-wiz="nav-stay"]'));
    this._navPromise = new Promise((resolve) => { this._navResolve = resolve; });
    return this._navPromise;
  }

  _navAnswer(leave) {
    const resolve = this._navResolve;
    this._navResolve = null;
    const dialog = this._frame?.querySelector(".wiz-nav-dialog");
    if (dialog && !dialog.hidden) {
      this._root.classList.remove("has-dialog");
      if (leave) dialog.hidden = true;
      else this._hideDialog(dialog, () => { this._render(); this._frame?.querySelector(".wiz-actions .wiz-action.primary:not(:disabled)")?.focus(); });
    }
    resolve?.(leave);
  }

  /** "Leave without saving": Cancel must reach Home Assistant before the panel moves on. */
  async _navDiscard() {
    const gateway = this._gateway;
    if (!gateway) { this._navAnswer(true); return; }
    const discarded = this._discarded(gateway);
    await gateway.cancel();
    if (this._gateway === gateway && gateway.status.cancelPending) { this._navAnswer(false); this._render(); return; }
    discarded();
    this._navAnswer(true);
  }

  /** The browser's own warning before the page closes or reloads while this tab owns an open session. */
  _unloadGuard(on) {
    if (on && !this._unload) {
      this._unload = (event) => { event.preventDefault(); event.returnValue = ""; };
      window.addEventListener("beforeunload", this._unload);
    } else if (!on && this._unload) {
      window.removeEventListener("beforeunload", this._unload);
      this._unload = null;
    }
  }

  _sessionOpen() {
    const view = this._gateway?.view;
    // A live start still waiting for its first view may already have created the session: leaving it asks too.
    if (this._gateway && !this._gateway.preview && !view && this._local.stage === "session" && !this._gateway.status.error) return true;
    return !!view && !["interrupted", "cancelled", "saved"].includes(view.phase) && !(view.read_only && !view.preview);
  }

  _exit() {
    if (STAGES_BEFORE_SESSION.includes(this._local.stage) || !this._sessionOpen()) { this._finish(); return; }
    const dialog = this._frame.querySelector(".wiz-dialog"), { t } = this._context;
    dialog.querySelector("#wiz-dialog-body").textContent = t(this._gateway.preview ? "wiz_T497" : "wizExitBodyLive");
    // R-5: a sheet (window under 720 × 500 px) has its ✕ in the title row.
    dialog.querySelector(".wiz-dialog-x").hidden = !layout.sheets();
    dialog.hidden = false;
    this._root.classList.add("has-dialog");
    focusOnOpen(dialog.querySelector(".wiz-dialog-card"), dialog.querySelector('[data-wiz="stay"]'));
  }

  _closeDialog(focus = true) {
    const dialog = this._frame?.querySelector(".wiz-dialog:not([hidden])");
    if (!dialog || dialog.classList.contains("is-leaving")) return;
    this._root.classList.remove("has-dialog");
    this._hideDialog(dialog, () => {
      if (!this._frame) return;
      this._render();
      // Back to something visible on every width: the screen's first enabled confirming button, or its title.
      if (focus) (this._frame.querySelector(".wiz-actions .wiz-action.primary:not(:disabled)") || this._frame.querySelector(".wiz-title"))?.focus();
    });
  }

  /** "Exit without saving": Cancel must reach Home Assistant; the view closes only once it has. */
  async _leave() {
    this._closeDialog(false);
    const gateway = this._gateway;
    if (!gateway) { this._finish(); return; }
    if (gateway.preview) { this._finish(); return; }
    const discarded = this._discarded(gateway);
    await gateway.cancel();
    if (gateway.status.cancelPending) { if (this._gateway === gateway) this._render(); return; }
    discarded();
  }

  /** U-10: once the cancel is confirmed the list shows the gateway free at once (taken before the view closes). */
  _discarded(gateway) {
    const entryId = this._item()?.entry.entry_id, { onDiscarded } = this._context || {};
    return () => { if (entryId && !gateway.preview) onDiscarded?.(entryId); };
  }

  _finish() {
    const { onClose } = this._context || {};
    this.close();
    onClose?.();
  }
}

function key(item) { return JSON.stringify([item.entry.entry_id, item.cover.entity_id]); }

/** Z-2: a value the reading field accepts (a number within its own limits). */
function accepted(input) {
  const value = parseReading(input.value), min = Number(input.dataset.min), max = Number(input.dataset.max);
  return Number.isFinite(value) && value >= min && value <= max;
}

/**
 * Everything a measurement leaves behind, cleared for a new session or «Start over»: acknowledgements, runs, the
 * lift-off value sent (G2-9), readings kept for the stepper, fine-tuning readings, the review and the step reached.
 * Fine-tuning keeps its base on purpose (`_startRefine` passes it again).
 */
function freshFlags() {
  return { ackLift: false, ackAscent: false, ackDescent: false, ackReadings: false, arm: null, run: null, fullRun: null, invalidRun: null, repeatQueued: false, moreOpen: false, discarded: null, misbehaved: false, stopSent: false,
    review: null, pendingSave: null, fieldError: null, fieldSequence: undefined, errorPhase: undefined, saveProfile: undefined, saveChoice: undefined,
    profileName: undefined, refining: false, lastGap: null, liftOrigin: null, baseReadings: null, fineReadings: null, pathChoice: null, reachedPhase: null };
}

export { slug };
