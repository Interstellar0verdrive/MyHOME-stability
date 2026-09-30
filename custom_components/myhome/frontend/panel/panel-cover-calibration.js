/** Backend-owned measurement: one owner per browser tab, read-only readers, explicit recovery. */
const url = new URL("panel-dom.js", import.meta.url);
url.search = new URL(import.meta.url).search;
const { escapeHtml: esc } = await import(url.href);
const visualUrl = new URL("panel-calibration-visual.js", import.meta.url);
visualUrl.search = new URL(import.meta.url).search;
const { visualMarkup, renderCalibrationVisual } = await import(visualUrl.href);

// Presence on the backend lapses after three missed heartbeats (45 s).
const HEARTBEAT_MS = 15000;
const CLIENT_KEY = "myhome-calibration-client";
let memoryClient = null;

/** One identity per browser tab, kept across reopenings so the backend recognises its owner. */
export function calibrationClient() {
  const fresh = () => globalThis.crypto.getRandomValues(new Uint32Array(4)).join("-");
  try {
    const storage = globalThis.sessionStorage;
    const stored = storage.getItem(CLIENT_KEY);
    if (/^\d+-\d+-\d+-\d+$/.test(stored || "")) return stored;
    const created = fresh();
    storage.setItem(CLIENT_KEY, created);
    return created;
  } catch {
    memoryClient ||= fresh();
    return memoryClient;
  }
}

export class CoverCalibration {
  constructor() { this._generation = 0; }

  close({ cancel = false, leave = true } = {}) {
    this._generation++;
    this._pin?.();
    this._pin = null;
    clearInterval(this._heartbeat);
    this._heartbeat = null;
    const state = this._state;
    // A read-only tab never cancels the owner's session: it only stops reading it.
    const action = !state?.recoverable || (cancel && !state.read_only) ? "cancel" : "detach";
    const operation = state && !["saved", "cancelled"].includes(state.phase) && (leave || action === "cancel")
      ? this._context.hass.callWS({ type: "myhome/cover_calibration/action", entry_id: state.entry_id,
        session_id: state.session_id, ...(state.attachment ? { attachment: state.attachment } : {}),
        action }).catch(() => {}) : Promise.resolve();
    const unsubscribe = this._unsubscribe;
    const done = operation.then(() => unsubscribe?.()).catch(() => {});
    this._unsubscribe = null;
    this._state = null;
    return done;
  }

  async open(context) {
    // Reopening the same session swaps the subscription without leaving it.
    this.close({ leave: !context.resume || context.resume.session_id !== this._state?.session_id });
    if (context.resume) context = { ...context, mode: context.resume.mode, direction: context.resume.direction,
      entity_ids: context.resume.batch ? context.resume.targets.map((item) => item.entity_id) : undefined };
    this._context = context;
    this._lost = false;
    this._busy = false;
    this._claiming = !!context.claim;
    this._savePreview = null;
    this._renderedPreview = null;
    const generation = this._generation;
    const { host, hass, entity, revision, t } = context;
    const client_id = calibrationClient();
    const automatic = context.mode === "automatic";
    const quick = context.direction;
    const geometry = context.mode === "geometry";
    host.innerHTML = `<div class="cal-panel" data-phase="loading">
      <h3 class="cal-title"><ha-icon icon="mdi:timer-outline" aria-hidden="true"></ha-icon>${esc(t(geometry ? "calGeometry" : automatic ? "calAutomatic" : "calGuided"))}</h3>
      <ol class="cal-steps" aria-hidden="true" ${automatic || quick || geometry ? "hidden" : ""}>
        <li data-step="opening"><span class="cal-step-index">1</span><span>${esc(t("calStepOpening"))}</span></li>
        <li data-step="closing"><span class="cal-step-index">2</span><span>${esc(t("calStepClosing"))}</span></li>
        <li data-step="review"><span class="cal-step-index">3</span><span>${esc(t("calStepReview"))}</span></li>
      </ol>
      <details class="profile-meta cal-guide"><summary>${esc(t("calVisualGuide"))}</summary>
        <p class="muted cal-help">${esc(t(geometry ? "calGeometryHelp" : quick ? (quick === "opening" ? "calQuickOpeningHelp" : "calQuickClosingHelp") : automatic ? "calAutomaticHelp" : "calHelp"))}</p>
        <p class="muted">${esc(t("calRecoveryHelp"))}</p>
      </details>
      ${context.resume ? `<p>${esc(context.resume.entity_id)}</p>` : ""}
      ${context.entity_ids ? `<p class="notice">${esc(t("calBatchHelp"))}</p><ol id="cal-targets"></ol>` : ""}
      <div class="cal-status">
        ${visualMarkup()}
        <p id="cal-phase" role="status">${esc(t("loading"))}</p>
        <p id="cal-elapsed" class="cal-elapsed"></p>
      </div>
      <p id="cal-stop-status" class="notice" hidden>${esc(t("calStopRequested"))}</p>
      <p id="cal-lift-repeat" class="notice" role="status" hidden></p>
      <p id="cal-reason" class="error" role="alert" hidden></p>
      <button type="button" id="cal-reconnect" hidden>${esc(t("calResume"))}</button>
      <p id="cal-read-only" class="notice" hidden>${esc(t("calReadOnly"))}</p>
      <button type="button" id="cal-take-control" hidden>${esc(t("calTakeControl"))}</button>
      <div class="actions cal-actions">
        <button type="button" class="primary" data-cal-action="run" hidden>${esc(t("calAutomaticStart"))}</button>
        <button type="button" class="primary" data-cal-action="open" hidden><ha-icon icon="mdi:arrow-up-bold" aria-hidden="true"></ha-icon><span>${esc(t("calOpen"))}</span></button>
        <button type="button" class="primary" data-cal-action="close" hidden><ha-icon icon="mdi:arrow-down-bold" aria-hidden="true"></ha-icon><span>${esc(t("calClose"))}</span></button>
        <button type="button" class="primary" data-cal-action="endpoint" hidden></button>
        <button type="button" class="primary" data-cal-action="next" hidden>${esc(t("calGeometryStart"))}</button>
        <button type="button" class="primary" data-cal-action="lift" hidden>${esc(t("calLift"))}</button>
      </div>
      <form id="cal-reading" hidden>
        <label><span id="cal-reading-label"></span><input name="reading_cm" type="text" inputmode="decimal" autocomplete="off" required></label>
        <p id="cal-reading-range" class="error" hidden></p>
        <p id="cal-expected" class="muted"></p>
        <button type="submit" class="primary">${esc(t("calReadingAccept"))}</button>
      </form>
      <button type="button" id="cal-repeat" hidden>${esc(t("calRepeat"))}</button>
      <form id="cal-save" class="profile-section cal-save" hidden><p id="cal-values" class="cal-values"></p>
        <label ${context.entity_ids ? "hidden" : ""}>${esc(t("calSaveDestination"))}<select id="cal-save-mode">
          <option value="new">${esc(t("calSaveNew"))}</option><option value="cover">${esc(t("calSaveCover"))}</option><option value="shared">${esc(t("calSaveShared"))}</option>
        </select></label>
        <label id="cal-name-label" ${context.entity_ids ? "hidden" : ""}>${esc(t("profileName"))}<input name="profile_name" required maxlength="64" ${context.entity_ids ? "disabled" : ""}></label>
        <div id="cal-batch-review"></div>
        <p id="cal-save-help" class="muted">${esc(t("calSaveOverrides"))}</p>
        <div id="cal-save-impact" class="notice" hidden></div>
        <button type="submit" class="primary">${esc(t(context.entity_ids ? "calBatchSave" : "calSave"))}</button>
      </form>
      <div class="actions calibration-safety-actions"><button type="button" id="cal-stop" disabled><ha-icon icon="mdi:stop-circle-outline" aria-hidden="true"></ha-icon><span>${esc(t("calStop"))}</span></button>
        <button type="button" id="cal-cancel" disabled>${esc(t("calCancel"))}</button></div>
    </div>`;
    for (const button of host.querySelectorAll("[data-cal-action]")) {
      button.onclick = () => this._perform(button.dataset.calAction);
    }
    host.querySelector("#cal-repeat").onclick = () => this._perform("repeat");
    host.querySelector("#cal-reading").onsubmit = (event) => {
      event.preventDefault();
      this._submitReading(event.currentTarget.elements.reading_cm);
    };
    host.querySelector("#cal-reading").oninput = (event) => this._checkRange(event.currentTarget);
    host.querySelector("#cal-stop").onclick = () => this._perform("stop");
    host.querySelector("#cal-cancel").onclick = async () => {
      await this.close({ cancel: true });
      if (this._generation === generation + 1 && host.isConnected) context.onCancel();
    };
    host.querySelector("#cal-reconnect").onclick = () => this.open({ ...context, claim: false, resume: this._state });
    host.querySelector("#cal-take-control").onclick = () => this.open({ ...context, claim: true, resume: this._state });
    host.querySelector("#cal-save-mode").onchange = () => {
      this._savePreview = null;
      if (this._state) this._render();
    };
    host.querySelector("#cal-save").onsubmit = (event) => {
      event.preventDefault();
      const form = event.currentTarget;
      if (!form.reportValidity()) return;
      if (context.entity_ids) {
        this._perform("save", { names: [...form.querySelectorAll("[data-batch-name]")].map((input) => input.value.trim()) });
        return;
      }
      const save_mode = host.querySelector("#cal-save-mode").value;
      if (save_mode === "shared" && !this._savePreview) this._perform("preview_save", { save_mode });
      else this._perform("save", { save_mode,
        ...(save_mode === "new" ? { name: form.elements.profile_name.value.trim() } : {}),
        ...(save_mode === "shared" ? { confirmation: this._savePreview.confirmation } : {}) });
    };
    const message = context.resume
      ? { type: "myhome/cover_calibration/resume", entry_id: entity.entry_id, session_id: context.resume.session_id, client_id,
        ...(context.claim ? { claim: true, sequence: context.resume.sequence } : {}) }
      : context.entity_ids
        ? { type: "myhome/cover_calibration/batch_start", entry_id: entity.entry_id, entity_ids: context.entity_ids, revision, client_id }
        : { type: "myhome/cover_calibration/start", entry_id: entity.entry_id, entity_id: entity.entity_id, revision, client_id, ...(automatic || geometry ? { mode: context.mode } : {}), ...(quick ? { direction: quick } : {}), ...(geometry && context.slats === false ? { slats: false } : {}) };
    if (!context.resume) {
      // Home Assistant replays this same message object after a reconnection. Once the
      // connection drops, or this view closes, it names the session on screen: the replay
      // then reads that session and never starts another one if it has ended meanwhile.
      const pin = () => { if (this._state?.session_id) message.session_id ??= this._state.session_id; };
      hass.connection.addEventListener?.("disconnected", pin);
      this._pin = () => { pin(); hass.connection.removeEventListener?.("disconnected", pin); };
    }
    try {
      const unsubscribe = await hass.connection.subscribeMessage((state) => {
        if (!this._current(generation)) return;
        this._accept(state);
      }, message);
      if (!this._current(generation)) { Promise.resolve(unsubscribe()).catch(() => {}); return; }
      this._unsubscribe = unsubscribe;
      this._heartbeat = setInterval(() => this._perform("heartbeat"), HEARTBEAT_MS);
    } catch (error) {
      if (this._current(generation)) {
        this._error(error);
        host.querySelector("#cal-cancel").disabled = false;
      }
    }
  }

  _current(generation) { return generation === this._generation && this._context.host.isConnected; }

  /** Movement, readings and Save wait for a response, a connection and ownership; Stop never does. */
  _locked() { return this._busy || this._lost || !!this._state?.read_only; }

  _accept(state) {
    // Sequences are ordered within one session only.
    if (this._state && state.session_id === this._state.session_id && state.sequence < this._state.sequence) return;
    if (state.session_id !== this._state?.session_id || (state.recoverable && state.attachment !== this._state?.attachment)) {
      this._busy = false;
      this._savePreview = null;
      this._context.host.querySelector("#cal-reason").hidden = true;
    }
    this._state = state;
    if (state.recoverable) this._lost = !state.attached;
    if (state.phase !== "review") this._savePreview = null;
    else if (state.save_preview && this._context.host.querySelector("#cal-save-mode").value === "shared") this._savePreview = state.save_preview;
    this._render();
    if (this._claiming) {
      // A claim against a sequence that has moved on only reads: say so instead of doing nothing.
      this._claiming = false;
      if (state.read_only) {
        const box = this._context.host.querySelector("#cal-reason");
        box.textContent = this._context.t("calClaimStale");
        box.hidden = false;
      }
    }
    if (state.phase === "saved") {
      this.close();
      this._context.onSaved();
    }
  }

  _render() {
    const { host, t } = this._context;
    const state = this._state;
    host.querySelector("#cal-reconnect").hidden = !this._lost || !state.recoverable;
    const readOnly = !!state.read_only, ended = ["saved", "cancelled"].includes(state.phase);
    const notice = host.querySelector("#cal-read-only");
    notice.hidden = !readOnly || ended;
    // Presence of the owner comes from the backend; this tab's own link is `attached`.
    const ownerAway = state.owner_present === false;
    notice.textContent = t(ownerAway ? "calReadOnlyAway" : "calReadOnly");
    const take = host.querySelector("#cal-take-control");
    take.hidden = !readOnly || ended || this._lost;
    take.disabled = this._busy;
    take.classList.toggle("primary", ownerAway);
    const cancel = host.querySelector("#cal-cancel");
    cancel.disabled = false;
    cancel.textContent = t(readOnly ? "close" : "calCancel");
    host.querySelector(".cal-panel").dataset.phase = state.phase;
    const automatic = state.mode === "automatic";
    const geometry = state.mode === "geometry";
    host.querySelector("#cal-phase").textContent = automatic && ["starting_open", "starting_close", "opening", "closing", "settling"].includes(state.phase)
      ? `${t("calAutomaticRun")} ${state.run_index + 1}/3 · ${t(`calAutoPhase_${state.phase}`)}`
      : t(state.direction && state.phase === "review" ? "calQuickReview" : `calPhase_${state.phase}`);
    host.querySelector("#cal-elapsed").textContent = state.elapsed == null ? "" : `${t("calElapsed")}: ${state.elapsed} s`;
    host.querySelector("#cal-stop-status").hidden = !state.stop_requested;
    const reason = host.querySelector("#cal-reason");
    if (state.reason) {
      reason.hidden = false;
      reason.textContent = t(`calReason_${state.reason}`);
    }
    for (const action of ["run", "open", "close", "endpoint"]) {
      const button = host.querySelector(`[data-cal-action="${action}"]`);
      button.hidden = geometry ? action !== "endpoint" || !["opening", "closing"].includes(state.phase) || !["home", "reset", "opening", "closing", "top"].includes(state.step) : action === "run" ? !automatic || state.phase !== "confirm_automatic" : automatic || (action === "open" ? state.phase !== "confirm_closed" : action === "close"
        ? state.phase !== "confirm_open" : !["opening", "closing"].includes(state.phase));
      button.disabled = this._locked();
    }
    host.querySelector('[data-cal-action="endpoint"]').textContent = t(state.phase === "opening" ? "calEndpointOpen" : "calEndpointClose");
    host.querySelector("#cal-stop").disabled = ["saved", "cancelled"].includes(state.phase);
    host.querySelector("#cal-save").hidden = state.phase !== "review";
    this._renderSave();
    host.querySelector("#cal-values").textContent = `${t("profileOpeningTime")}: ${shown(state.values.opening_time, "s")} · ${t("profileClosingTime")}: ${shown(state.values.closing_time, "s")}`;
    if (state.direction) {
      host.querySelector("#cal-values").textContent = ["opening", "closing"].map((direction) =>
        `${t(direction === "opening" ? "profileOpeningTime" : "profileClosingTime")}: ${shown(state.values[`${direction}_time`], "s")} s · ${t(direction === state.direction ? "calQuickMeasured" : "calQuickRetained")}`).join(" · ");
    }
    this._renderGeometry(geometry);
    renderCalibrationVisual(host, state, t, this._lost);
    host.querySelector("#cal-values").hidden = !!state.batch;
    if (state.batch) {
      host.querySelector("#cal-targets").innerHTML = state.targets.map((item, index) => {
        const result = state.results.find((row) => row.index === index);
        const status = ["interrupted", "cancelled"].includes(state.phase) ? t("calBatchDiscarded") : result ? `${shown(result.values.opening_time, "s")} / ${shown(result.values.closing_time, "s")} s` : t(index === state.cover_index ? "calBatchCurrent" : "calBatchWaiting");
        return `<li>${esc(item.name)} · ${esc(status)}</li>`;
      }).join("");
      const review = host.querySelector("#cal-batch-review");
      if (state.phase === "review" && !review.children.length) {
        review.innerHTML = state.results.map((result) => `<label>${esc(state.targets[result.index].name)} · ${esc(shown(result.values.opening_time, "s"))} / ${esc(shown(result.values.closing_time, "s"))} s
          ${state.targets[result.index].travel_cm != null ? `<span class="muted">${esc(t("profileReferenceTravel"))}: ${esc(shown(state.targets[result.index].travel_cm, "cm"))} cm</span>` : ""}
          <span class="muted">${esc(t("profileName"))}</span><input data-batch-name="${result.index}" required maxlength="64" value="${esc(state.targets[result.index].name.slice(0, 64))}"></label>`).join("");
      }
    }
  }

  _renderGeometry(enabled) {
    const { host, t } = this._context, state = this._state;
    const disabled = this._locked();
    for (const [action, visible] of [["next", state.phase === "briefing"], ["lift", state.step === "lift" && state.phase === "opening"]]) {
      const button = host.querySelector(`[data-cal-action="${action}"]`);
      button.hidden = !enabled || !visible;
      button.disabled = disabled;
    }
    const form = host.querySelector("#cal-reading");
    form.hidden = !enabled || state.phase !== "reading";
    // HA's scoped registry exposes named form controls but its iterator throws.
    for (const input of form.querySelectorAll("input, button")) input.disabled = disabled;
    const repeat = host.querySelector("#cal-repeat");
    repeat.hidden = !enabled || !state.can_repeat;
    repeat.disabled = disabled;
    if (!enabled) return;
    const noSlats = state.slats === false;
    // Runs that only bring the cover to an end stop measure nothing: no elapsed time, only what to confirm.
    const positioning = ["opening", "closing"].includes(state.phase) && ["home", "reset", "top"].includes(state.step);
    host.querySelector("#cal-elapsed").hidden = positioning;
    const notice = host.querySelector("#cal-lift-repeat");
    // Assigned only when it changes, so heartbeats do not repeat the announcement.
    const lift = state.still_resting ? fill(t("calLiftRepeated"), state) : state.gap_warning ? fill(t("calGapWarning"), state) : "";
    notice.hidden = !lift;
    if (notice.textContent !== lift) notice.textContent = lift;
    if (["briefing", "opening", "closing", "reading", "geometry_wait_stop"].includes(state.phase)) {
      const key = state.phase === "briefing" ? `calBrief_${state.step}${noSlats && ["home", "closing"].includes(state.step) ? "_no_slats" : ""}`
        : state.phase === "geometry_wait_stop" ? "calGeometryWaitStop"
          : state.phase === "reading" ? `calReading_${state.reading_kind}${state.reading_kind === "lift" && state.lift_repeat === false ? "_refused" : ""}`
            : state.step === "lift" ? "calLiftRunning" : state.step.startsWith("half_") ? "calHalfRunning"
              : !positioning ? "calEndpointRunning" : state.step === "top" ? "calPositionOpen" : `calPositionClose${noSlats ? "_no_slats" : ""}`;
      host.querySelector("#cal-phase").textContent = fill(t(key), state);
    }
    // The travel already saved for the cover is offered, never sent without confirmation.
    if (form.dataset.step !== state.step) {
      form.elements.reading_cm.value = state.step === "opening" && state.saved_travel_cm != null ? `${state.saved_travel_cm}` : "";
      form.dataset.step = state.step;
    }
    this._checkRange(form);
    form.elements.reading_cm.min = state.step === "lift" ? "0" : "0.1";
    host.querySelector("#cal-reading-label").textContent = t(state.step === "opening" ? "profileCoverTravel" : "calHeightCm");
    host.querySelector("#cal-expected").textContent = state.expected_cm == null ? "" : `${t("calExpectedRough")}: ${shown(state.expected_cm, "cm")} cm. ${t("calExpectedHelp")}`;
    if (state.phase === "review") {
      // Without slats the summary says so instead of showing a zero slat time.
      const keys = noSlats ? ["opening_roll", "closing_roll"] : ["slat_time_s", "opening_roll", "closing_roll"];
      host.querySelector("#cal-values").textContent += ` · ${t("profileCoverTravel")}: ${shown(state.travel_cm, "cm")} cm · ` +
        [...(noSlats ? [t("calGeometryNoSlats")] : []), ...keys.map((key) => `${t(`calGeometry_${key}`)}: ${shown(state.geometry[key], key === "slat_time_s" ? "s" : "roll")}`)].join(" · ");
      host.querySelector("#cal-save-help").textContent = t(noSlats ? "calGeometryReviewNoSlats" : "calGeometryReview");
    }
  }

  _renderSave() {
    const { host, t } = this._context;
    const state = this._state, form = host.querySelector("#cal-save");
    const selector = host.querySelector("#cal-save-mode");
    const modes = state.save_modes || ["new"];
    for (const option of selector.options) option.disabled = !modes.includes(option.value);
    if (!modes.includes(selector.value)) { selector.value = "new"; this._savePreview = null; }
    selector.disabled = this._locked();
    const mode = selector.value;
    host.querySelector("#cal-name-label").hidden = !!state.batch || mode !== "new";
    form.elements.profile_name.disabled = !!state.batch || mode !== "new";
    form.elements.profile_name.required = !state.batch && mode === "new";
    host.querySelector("#cal-save-help").textContent = t(mode === "new" ? "calSaveOverrides" : mode === "cover" ? "calSaveCoverHelp" : "calSaveSharedHelp");
    if (!state.batch && mode === "new" && state.travel_cm != null) host.querySelector("#cal-save-help").textContent += ` ${t("profileReferenceTravel")}: ${shown(state.travel_cm, "cm")} cm.`;
    if (mode === "shared" && state.reference_travel_cm != null) host.querySelector("#cal-save-help").textContent += ` ${t("profileReferenceTravel")}: ${shown(state.reference_travel_cm, "cm")} cm. ${t("calReferenceNormalization")}`;
    const button = form.querySelector('button[type="submit"]');
    button.disabled = this._locked();
    button.textContent = t(state.batch ? "calBatchSave" : mode === "new" ? "calSave" : mode === "cover" ? "calSaveCover" : this._savePreview ? "calConfirmShared" : "calPreviewShared");
    const box = host.querySelector("#cal-save-impact");
    box.hidden = !this._savePreview;
    if (this._savePreview && this._renderedPreview !== this._savePreview) {
      const preview = this._savePreview;
      box.innerHTML = `<p><strong>${esc(preview.after.name)}</strong> · ${esc(t("calSharedImpact"))}</p><ul>${preview.followers.map((item) =>
        `<li><strong>${esc(item.name || item.entity_id || t("profileMissingCover"))}</strong>${item.available ? "" : ` · ${esc(t("profileUnavailableFollower"))}`}<br>${["opening", "closing"].map((direction) => {
          const change = item.changes[direction];
          return `${esc(t(direction === "opening" ? "profileOpeningTime" : "profileClosingTime"))}: ${esc(shown(change.before, "s"))} → ${esc(shown(change.after, "s"))} s${change.overridden ? ` · ${esc(t("calPersonalRetained"))}` : change.override_removed ? ` · ${esc(t("calPersonalRemoved"))}` : ""}`;
        }).join("<br>")}</li>`).join("")}</ul>`;
    }
    this._renderedPreview = this._savePreview;
  }

  /** A lift-off gap outside its range keeps the button disabled; Home Assistant still validates it. */
  _checkRange(form) {
    const state = this._state, reading = parseReading(form.elements.reading_cm.value);
    const outside = state.step === "lift" && state.max_gap_cm != null && Number.isFinite(reading) && (reading < 0 || reading > state.max_gap_cm);
    const range = form.querySelector("#cal-reading-range"), text = outside ? fill(this._context.t("profileError_invalid_gap"), state) : "";
    range.hidden = !outside;
    if (range.textContent !== text) range.textContent = text;
    form.querySelector('button[type="submit"]').disabled = form.elements.reading_cm.disabled || outside;
  }

  /** A tape reading with a comma or a point; an empty or partial number is never sent as 0. */
  _submitReading(input) {
    const reading_cm = parseReading(input.value);
    input.setAttribute("aria-invalid", String(!Number.isFinite(reading_cm)));
    if (Number.isFinite(reading_cm)) {
      this._perform("reading", { reading_cm });
      return;
    }
    const box = this._context.host.querySelector("#cal-reason");
    box.textContent = this._context.t("calReadingNumber");
    box.hidden = false;
    input.focus();
  }

  _error(error) {
    const { host, t } = this._context;
    const key = `profileError_${error.code}`;
    const box = host.querySelector("#cal-reason");
    box.textContent = t(key) === key ? t("calConnectionError") : fill(t(key), this._state);
    box.hidden = false;
  }

  async _perform(action, extra = {}) {
    if (!this._state || (this._busy && !["stop", "heartbeat"].includes(action))) return;
    const generation = this._generation;
    const { hass } = this._context;
    const state = this._state;
    const ownsBusy = !["heartbeat", "stop"].includes(action);
    const current = () => this._current(generation) && this._state?.attachment === state.attachment;
    if (ownsBusy) {
      this._busy = true;
      this._context.host.querySelector("#cal-reason").hidden = true;
    }
    this._render();
    try {
      const result = await hass.callWS({ type: "myhome/cover_calibration/action", entry_id: state.entry_id,
        session_id: state.session_id, sequence: state.sequence,
        ...(state.attachment ? { attachment: state.attachment } : {}), action, ...extra });
      if (current()) this._accept(result);
    } catch (error) {
      if (!current()) return;
      if (action === "heartbeat") this._lost = true;
      if (action === "save" || action === "preview_save") this._savePreview = null;
      this._error(error);
    } finally {
      if (current()) { if (ownsBusy) this._busy = false; this._render(); }
    }
  }
}

/** Display only, stored values keep full precision: tenths of a second or centimetre, rolls to two decimals. */
export function shown(value, unit) {
  return value == null ? "—" : `${Number(Number(value).toFixed(unit === "roll" ? 2 : 1))}`;
}

/** A comma or a point before the decimals; anything else, empty included, is not a number. */
function parseReading(value) {
  const text = value.trim().replace(",", ".");
  return /^-?(\d+\.?\d*|\.\d+)$/.test(text) ? Number(text) : NaN;
}

/** Limits such as {touching_cm} come from the session view, never from the text. */
function fill(text, state) {
  return text.replace(/\{(\w+)\}/g, (match, key) => state?.[key] == null ? match : `${Number(state[key])}`);
}
