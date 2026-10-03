/**
 * A stand-in for Home Assistant in the panel tests: inventory, profile overview and read, and a
 * calibration session whose `geometry` and `guided` transitions follow the backend modules
 * (`cover_calibration_geometry.py`, `cover_calibration.py`) closely enough to drive every screen.
 * Bus events are explicit calls (`started()`, `stopped()`, `autoStop()`), so tests decide when the
 * cover "moves". Every message the panel sends is recorded in `calls` / `subscriptions`.
 */
export function coverInventory(covers) {
  return {
    version: "2.0.0b13", panel_version: "0.41.0",
    gateways: [{ entry_id: "one", title: "Home", mac: "00:03:50:00:00:01", model: "F454", host: "192.0.2.1", state: "loaded", connected: true, monitor_available: true }],
    devices: [],
    entities: covers.map(([entity_id, name, area_id]) => ({ entity_id, entry_id: "one", domain: "cover", who: "2", name: null, original_name: name,
      device_id: null, area_id, unique_id: `uid-${entity_id}`, address: { raw: "91", a: "9", pl: "1", interface: null } })),
    areas: [{ id: "living", name: "Living room" }, { id: "kitchen", name: "Kitchen" }],
  };
}

const evidence = (source, recorded_at = null, extra = {}) => ({ source, recorded_at, origin_entity_id: null, origin_name: null, inherited: false, ...extra });
const value = (number, provenance, origin = "override") => ({ value: number, origin, provenance, scaled: false });

export function sampleOverview() {
  const measured = evidence("guided", "2026-09-29T10:00:00+00:00");
  return {
    entry_id: "one", revision: 7, capabilities: { profile_management: true, profile_assignment: true },
    profiles: [{ id: "tall", name: "tall_two_leaf", opening_time: 22.4, closing_time: 21.9, reference_travel_cm: 198,
      geometry: { slat_time_s: 4.4, opening_roll: 1.83, closing_roll: 1.91 }, assigned_to: ["cover.kitchen_two", "cover.living_three"],
      provenance: { opening: evidence("guided", "2026-09-29T10:00:00+00:00", { origin_name: "Living room shutter 1" }), closing: measured } }],
    covers: [
      { entity_id: "cover.living_one", name: "Living room shutter 1", profile_id: null, travel_cm: 195, available: true, advanced: false, overrides: {},
        effective: { opening: value(22.0, evidence("unknown"), "native_fallback"), closing: value(21.7, evidence("unknown"), "native_fallback") } },
      { entity_id: "cover.kitchen_two", name: "Kitchen shutter 2", profile_id: "tall", travel_cm: 110, available: true, advanced: false, overrides: {},
        effective: { opening: value(12.3, measured, "profile"), closing: value(12.1, measured, "profile"), slat_time_s: value(2.4, measured, "profile"),
          opening_roll: value(1.83, measured, "profile"), closing_roll: value(1.91, measured, "profile") } },
      { entity_id: "cover.living_three", name: "Living room shutter 3", profile_id: "tall", travel_cm: 196, available: true, advanced: false, overrides: {},
        effective: { opening: value(22.2, measured, "profile"), closing: value(21.8, measured, "profile") } },
    ],
  };
}

export function createFakeBackend({ language = "en", inventory = coverInventory([["cover.living_one", "Living room shutter 1", "living"],
  ["cover.kitchen_two", "Kitchen shutter 2", "kitchen"], ["cover.living_three", "Living room shutter 3", "living"]]), overview = sampleOverview(),
  session: initial = null, owner = true } = {}) {
  const calls = [], subscriptions = [];
  let session = initial, listener = null, clock = 0;
  const backend = {
    calls, subscriptions, overview,
    get session() { return session; },
    tick(seconds) { clock += seconds; },
    view(extra = {}) {
      const { _after_stop, _after_position, _started, ...public_ } = session;
      void _after_stop; void _after_position;
      return { ...public_, elapsed: _started == null ? null : Math.round((clock - _started) * 100) / 100,
        owner, read_only: !owner, attachment: "attachment-1", attached: true, owner_present: true, recoverable: !["saved", "cancelled", "interrupted"].includes(session.phase), ...extra };
    },
    emit() { if (session.mode === "geometry") refresh(); session.sequence += 1; listener?.(backend.view()); },
    /** The bus confirms the movement asked by `next`, `open` or `close`. */
    started() {
      session.phase = session.phase === "starting_open" ? "opening" : "closing";
      session._started = clock;
      backend.emit();
    },
    /** The actuator confirms Stop after a press, an endpoint or a timed half run. */
    stopped() {
      if (session.phase !== "geometry_wait_stop") throw new Error(`stopped() in ${session.phase}`);
      session._started = null;
      session.phase = session._after_stop;
      if (session.phase === "briefing") session.step = ["home", "reset", "top"].includes(session.step) ? session._after_position : "half_open";
      backend.emit();
    },
    /** The scheduled Stop of an intermediate run. */
    autoStop() {
      session.samples[session.step] = clock - session._started;
      session.phase = "geometry_wait_stop"; session._after_stop = "reading";
      backend.emit();
    },
    interrupt(reason) { session.phase = "interrupted"; session.reason = reason; session._started = null; backend.emit(); },
  };

  const startGeometry = (message) => ({
    entry_id: message.entry_id, entity_id: message.entity_id, session_id: "session-1", sequence: 1, revision: message.revision,
    mode: "geometry", phase: "briefing", step: "home", reason: null, values: {}, samples: {}, readings: {}, geometry: {}, travel_cm: null,
    stop_requested: false, slats: message.slats !== false, lift_attempts: 1, still_resting: false, gap_warning: false, touching_cm: 1, max_gap_cm: 20,
    gap_warn_cm: 10, lift_repeat: true, saved_travel_cm: 195, expected_cm: null, can_repeat: false, save_modes: ["new"], reading_kind: "home",
    _after_stop: "briefing", _after_position: message.slats === false ? "opening" : "lift", _started: null });
  const startGuided = (message) => ({
    entry_id: message.entry_id, entity_id: message.entity_id, session_id: "session-1", sequence: 1, revision: message.revision, mode: "guided",
    phase: "confirm_closed", reason: null, values: {}, stop_requested: false, save_modes: ["new", "cover", "shared"], _started: null });

  const repeatable = () => session.phase === "reading" || session.phase === "review" || (session.phase === "briefing" && session.step === "half_open") || session.gap_warning;
  const refresh = () => {
    session.can_repeat = repeatable();
    session.reading_kind = session.step === "opening" ? "travel" : session.step;
    session.expected_cm = session.travel_cm && session.step?.startsWith("half_") ? session.travel_cm / 2 : null;
    // As cover_calibration_geometry.py publishes it: the heights a roll from 1 to 5 accepts at this stop.
    session.reading_range = session.phase === "reading" && session.step?.startsWith("half_") && session.travel_cm
      ? { min_cm: session.travel_cm * 0.3712345, max_cm: session.travel_cm * 0.5512345 } : null;
  };

  function geometryAction(message) {
    const { action } = message;
    if (action === "next" && session.phase === "briefing") {
      session.gap_warning = session.still_resting = false;
      session.phase = ["home", "reset", "closing", "half_close"].includes(session.step) ? "starting_close" : "starting_open";
    } else if (action === "lift" && session.step === "lift" && session.phase === "opening") {
      session.samples.lift = clock - session._started;
      session.phase = "geometry_wait_stop"; session._after_stop = "reading";
    } else if (action === "endpoint" && ["opening", "closing"].includes(session.phase) && ["home", "reset", "opening", "closing", "top"].includes(session.step)) {
      if (["opening", "closing"].includes(session.step)) session.values[`${session.step}_time`] = clock - session._started;
      session._after_stop = session.step === "opening" ? "reading" : "briefing";
      session.phase = "geometry_wait_stop";
    } else if (action === "reading" && session.phase === "reading") {
      const number = message.reading_cm;
      if (session.step === "lift") {
        if (number > session.max_gap_cm) throw Object.assign(new Error("gap"), { code: "invalid_gap" });
        session.still_resting = number < session.touching_cm;
        if (session.still_resting) { delete session.samples.lift; session.lift_attempts += 1; } else session.readings.gap = number;
        session.gap_warning = number >= session.gap_warn_cm;
        session.step = "reset"; session._after_position = session.still_resting ? "lift" : "opening";
      } else if (session.step === "opening") {
        session.travel_cm = number; session.step = "closing";
      } else if (session.reading_range && (number < session.reading_range.min_cm || number > session.reading_range.max_cm)) {
        throw Object.assign(new Error("range"), { code: "reading_out_of_range" });
      } else if (session.step === "half_open") {
        session.geometry = { slat_time_s: session.slats ? 4.4 : 0, opening_roll: 1.83 };
        session.readings.half_open = number; session.step = "top"; session._after_position = "half_close";
      } else {
        session.geometry.closing_roll = 1.91; session.readings.half_close = number; session.phase = "review"; refresh(); return;
      }
      session.phase = "briefing";
    } else if (action === "repeat" && repeatable()) {
      const target = session.gap_warning ? "lift" : session.phase === "briefing" && session.step === "half_open" ? "closing" : session.step;
      session.step = ["half_close", "closing"].includes(target) ? "top" : session.slats ? "reset" : "home";
      session._after_position = target;
      if (target === "lift") { session.lift_attempts += 1; delete session.samples.lift; delete session.readings.gap; }
      session.still_resting = session.gap_warning = false;
      session.phase = "briefing";
    } else throw Object.assign(new Error("step"), { code: "calibration_step" });
  }

  function guidedAction(message) {
    const { action } = message;
    if (action === "open" && session.phase === "confirm_closed") session.phase = "starting_open";
    else if (action === "close" && session.phase === "confirm_open") session.phase = "starting_close";
    else if (action === "endpoint" && ["opening", "closing"].includes(session.phase)) {
      session.values[`${session.phase}_time`] = clock - session._started;
      session._started = null;
      session.phase = session.phase === "opening" ? "confirm_open" : "review";
    } else throw Object.assign(new Error("step"), { code: "calibration_step" });
  }

  const hass = {
    language, states: {},
    connection: {
      subscribeEvents: async () => () => {},
      subscribeMessage: async (callback, message) => {
        subscriptions.push(message);
        if (message.type === "myhome/cover_profiles/subscribe") return () => {};
        if (message.type === "myhome/cover_calibration/start") {
          // As in Home Assistant, a start without `mode` is the guided measurement.
          session = message.mode === "geometry" ? startGeometry(message) : startGuided(message);
          refresh();
        } else if (message.type === "myhome/cover_calibration/resume") {
          if (!session || session.session_id !== message.session_id) throw Object.assign(new Error("expired"), { code: "calibration_expired" });
          if (message.claim) owner = true;
        } else throw new Error(`Unexpected subscription ${message.type}`);
        listener = callback;
        callback(backend.view());
        return () => { if (listener === callback) listener = null; };
      },
    },
    callWS: async (message) => {
      calls.push(message);
      if (message.type === "myhome/panel/inventory") return structuredClone(inventory);
      if (message.type === "myhome/cover_profiles/overview") return structuredClone(overview);
      if (message.type === "myhome/cover_profiles/read") {
        const live = session && !["saved", "cancelled"].includes(session.phase) ? { ...backend.view(), owner: false, read_only: true } : null;
        if (live) delete live.attachment;
        return { revision: overview.revision, calibration: live };
      }
      if (message.type === "myhome/cover_calibration/action") {
        const { action } = message;
        if (action === "heartbeat") return backend.view();
        if (action === "stop") { if (session.phase !== "review") { session.phase = "interrupted"; session.reason = "stopped"; } session.sequence += 1; return backend.view(); }
        if (action === "cancel") { session.phase = "cancelled"; session.reason = "cancelled"; session.sequence += 1; return backend.view(); }
        if (action === "detach") return backend.view();
        if (action === "save") {
          if (session.phase !== "review") throw Object.assign(new Error("step"), { code: "calibration_step" });
          if (!session.save_modes.includes(message.save_mode || "new")) throw Object.assign(new Error("mode"), { code: "invalid_profile" });
          session.phase = "saved"; session.saved = { save_mode: message.save_mode, name: message.name }; session.sequence += 1;
          return backend.view();
        }
        if (message.sequence !== session.sequence) throw Object.assign(new Error("sequence"), { code: "calibration_sequence" });
        if (session.mode === "guided") guidedAction(message); else geometryAction(message);
        refresh();
        session.sequence += 1;
        const result = backend.view();
        // The answer reaches the caller first; other subscribers get the same view.
        return result;
      }
      if (message.type === "myhome/cover_calibration/targets") return { revision: 7, max_batch: 4, targets: [] };
      throw new Error(`Unexpected command ${message.type}`);
    },
  };
  backend.hass = hass;
  return backend;
}
