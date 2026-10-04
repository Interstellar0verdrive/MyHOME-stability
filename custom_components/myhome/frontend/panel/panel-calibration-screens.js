/**
 * Which screen of the calibration mockups (A-xx, B-xx, C-xx, S-xx) a moment of the wizard is.
 *
 * Pure: from the wizard's local choices and the session view it returns plain data (texts already
 * filled, fields, buttons, stepper), and the wizard only draws it. Text keys are those of the
 * shared translation sheet (`wiz_T…`); a few screen-only keys are `wiz…`.
 */
const asset = (name) => { const url = new URL(name, import.meta.url); url.search = new URL(import.meta.url).search; return url.href; };
const { fill, number, readingRange, RANGE_SLACK_CM, dateText, shortDate } = await import(asset("panel-calibration-text.js"));

const PHASES = {
  intro: "wiz_T007", prep: "wiz_T008", ascent: "wiz_T009", descent: "wiz_T010", readings: "wiz_T011", summary: "wiz_T012", finetune: "wiz_T013",
};

/** The phases each path shows, in order (C depends on what is remeasured). */
export function phasesFor(path, scope, refining) {
  if (path === "B") return ["intro", "readings", "summary"];
  if (path === "C" && scope === "times_only") return ["intro", "prep", "ascent", "descent", "summary"];
  if (path === "C" && scope === "points_only") return ["intro", "prep", "readings", "summary"];
  return ["intro", "prep", "ascent", "descent", "readings", "summary", "finetune", ...(refining ? ["summary"] : [])];
}

const MEASURED_RUN = (view) => view && ((view.mode === "geometry" && ["opening", "closing"].includes(view.phase) && ["lift", "opening", "closing"].includes(view.step))
  || (view.mode === "guided" && ["opening", "closing"].includes(view.phase)));

/**
 * `motor_stopped` (from the backend lot v2-endpoint): in a run the user confirms (the closings to the base `home` and
 * `reset`, the full ascent and descent, the return to the top, the guided runs) the motor has stopped (a stop frame
 * from the bus, real or the actuator's own timer) and the session waits for the confirmation; `stopped_elapsed` is
 * the run's time at that frame. Without the field the run counts as moving.
 */
const MOTOR_STOPPED = (view) => view?.motor_stopped === true;
/** Stop is offered while the motor runs; once it has stopped by itself only the confirmation is left. */
const whileRunning = (view, stop) => MOTOR_STOPPED(view) ? [] : [stop];

/** Movements in progress or about to start: Stop is the action that matters. */
export const MOVING = (view) => !!view && !MOTOR_STOPPED(view)
  && (["opening", "closing", "geometry_wait_stop", "positioning"].includes(view.phase) || view.phase?.startsWith("starting_"));

const ENDED = ["interrupted", "cancelled", "expired"];

/** Texts with a count: the zero and one forms of the sheet's plural texts (PROVVISORIO rows T305–T317). */
const PLURALS = { wiz_T110: ["wiz_T305", "wiz_T306"], wiz_T112: ["wiz_T307", null], wiz_T165: ["wiz_T308", "wiz_T309"],
  wiz_T285: ["wiz_T310", "wiz_T311"], wiz_T286: ["wiz_T312", "wiz_T313"], wiz_T287: ["wiz_T314", "wiz_T315"], wiz_T288: ["wiz_T316", "wiz_T317"] };
export function counted(t, key, count, values = {}) {
  const [zero, one] = PLURALS[key] || [];
  return fill(t(count === 0 && zero ? zero : count === 1 && one ? one : key), { ...values, count });
}

/** "Measured on…" in the middle of a line: "measured on…" (the language's own lower case). */
function lowerFirst(text, language) {
  return text ? text[0].toLocaleLowerCase(language) + text.slice(1) : text;
}

/** A-02's line on the chosen cover: the profile it follows, its calibration, or how many profiles it could follow. */
function pathContext(t, cover, profiles, language) {
  if (!cover) return "";
  if (cover.profile?.name) return fill(t("wiz_T395"), { profile: cover.profile.name });
  if (cover.status && cover.status !== "to_measure") {
    return fill(t("wiz_T399"), { status: t(`calTabStatus_${cover.status}`).toLocaleLowerCase(language), date: dateText(cover.last, language) || "—" });
  }
  return profiles === 0 ? t("wiz_T396") : profiles === 1 ? t("wiz_T398") : fill(t("wiz_T397"), { count: profiles });
}

/** A cover's state in the A-01 drop-down: "To measure", or "Times measured, Sep 29". */
function coverState(t, item, language) {
  if (!item.status) return "";
  const text = t(`calTabStatus_${item.status}`), date = item.status === "to_measure" ? "" : shortDate(item.last, language);
  return date ? `${text}, ${date}` : text;
}

/** The wizard's whole state as one screen. */
export function buildScreen(ctx) {
  const { t, language = "en", path = "A", scope = null, stage, local = {}, cover, view, status = {}, preview = false } = ctx;
  const n = (value, digits = 1) => number(value, language, digits);
  const tx = (key, values) => fill(t(key), values);
  const name = cover?.name || "";
  const values = { cover: name, profile: cover?.profile?.name ?? "" };
  const screen = {
    code: "", header: { title: name || t("wiz_T001"), subtitle: cover?.address || "" }, discard: true, preview,
    title: "", subline: "", body: "", stopwatch: null, wait: null, illustration: null, choice: null, field: null, box: null, table: null,
    technical: null, profileBlock: null, saveInfo: null, precision: null, status: [], notices: [], actions: [], readOnly: null, phase: "intro",
    caption: caption(t, path, scope, cover),
  };
  const stop = { id: "stop", label: t("wiz_T028"), kind: "stop" };
  const finish = () => finalize(screen, ctx);

  // ---- Before any session: choices that stay in the browser. ----
  if (stage === "choose") {
    Object.assign(screen, { code: "A-01", phase: "intro", title: t("wiz_T003"), body: t("wiz_T004"),
      // Empty with a placeholder entry until a cover is chosen; Continue waits for it.
      choice: { name: "cover", kind: "select", label: t("wiz_T005"), value: local.coverKey || "",
        options: [...(local.coverKey ? [] : [{ value: "", label: t("wiz_T393"), disabled: true }]),
          ...(ctx.covers || []).map((item) => ({ value: item.key, label: [item.label, coverState(t, item, language)].filter(Boolean).join(" · ") }))] },
      actions: [{ id: "choose", label: t("wiz_T006"), kind: "primary", disabled: !ctx.covers?.length || !local.coverKey }] });
    // Until a cover is picked the subtitle says so; then it names the cover as the drop-down does.
    const picked = local.coverPicked ? (ctx.covers || []).find((item) => item.key === local.coverKey) : null;
    screen.header = { title: t("wiz_T001"), subtitle: picked ? picked.label : t("wiz_T392"), placeholder: !picked };
    // A calibrated cover: a new measurement replaces its values; fine-tuning is the way to adjust them.
    if (picked?.status && picked.status !== "to_measure") {
      screen.choice.note = fill(t("wiz_T394"), { status: t(`calTabStatus_${picked.status}`).toLocaleLowerCase(language), date: dateText(picked.last, language) || "—" });
    }
    return finish();
  }
  if (stage === "path") {
    // A radio list (A-02 Section A) with Continue in the actions; the advised path carries a badge.
    const profiles = ctx.profiles?.length || 0, measured = cover?.status && cover.status !== "to_measure";
    const advised = measured ? "C" : profiles ? "B" : "A";
    const options = [
      { value: "A", label: t("wiz_T017") },
      { value: "B", label: t("wiz_T018"), disabled: !profiles, note: profiles ? t("wiz_T318") : t("wiz_T401") },
      { value: "C", label: t("wiz_T019") },
    ].map((option) => ({ ...option, badge: option.value === advised && !option.disabled ? t("wiz_T400") : "" }));
    // Preselected on the advised path, Continue is ready; another choice is a tap away.
    const enabled = (value) => options.some((option) => option.value === value && !option.disabled);
    const chosen = enabled(local.pathChoice) ? local.pathChoice : enabled(advised) ? advised : "";
    // "If unsure, choose Ⓐ" (the text's last paragraph) is dropped while the advised path is the one chosen.
    const body = chosen && chosen === advised ? t("wiz_T016").split(/\n\s*\n/).slice(0, -1).join("\n\n") : t("wiz_T016");
    Object.assign(screen, { code: "A-02", phase: "intro", title: tx("wiz_T015", { name }), subline: pathContext(t, cover, profiles, language), body,
      choice: { name: "path", kind: "radio", label: tx("wiz_T015", { name }), legendHidden: true, value: chosen, options },
      actions: [{ id: "path", label: t("wiz_T006"), kind: "primary", disabled: !chosen }] });
    return finish();
  }
  if (stage === "profile") {
    const chosen = ctx.profiles?.find((item) => item.id === local.profileId) || ctx.profiles?.[0];
    // One radio row per profile: "tall_two_leaf · measured on Living room shutter 1 · 3 shutters follow it".
    const about = (item) => counted(t, "wiz_T165", item.followers, { cover: item.measuredOn || "—" });
    Object.assign(screen, { code: "B-01", phase: "intro", title: t("wiz_T161"), body: t("wiz_T162"),
      choice: { name: "profile", kind: "radio", label: t("wiz_T163"), value: chosen?.id ?? "",
        options: (ctx.profiles || []).map((item) => ({ value: item.id, label: `${item.name} · ${lowerFirst(about(item), language)}`, plain: true })) },
      actions: [{ id: "profile", label: t("wiz_T006"), kind: "primary", disabled: !chosen }] });
    return finish();
  }
  if (stage === "current") {
    const effective = cover?.effective || {};
    Object.assign(screen, { code: "C-01", phase: "intro", title: t("wiz_T184"),
      body: cover?.profile ? tx("wiz_T185", { ...values, travel: n(cover.travel_cm) }) : tx("wizNoProfileBody", values),
      // A bold title and one line per value: the sheet's single line (T188) split at its separators.
      box: { label: t("wiz_T186"), lines: tx("wiz_T188", { profile: cover?.profile?.name ?? "—", travel: n(cover?.travel_cm),
        opening: n(effective.opening?.value), closing: n(effective.closing?.value), slat: n(effective.slat_time_s?.value) }).split(" · ") },
      actions: [{ id: "current", label: t("wiz_T006"), kind: "primary" }] });
    return finish();
  }
  if (stage === "case") {
    // As in the mockup, the first case (tape readings only) is preselected.
    Object.assign(screen, { code: "C-02", phase: "intro", title: t("wiz_T189"), body: t("wiz_T190"),
      choice: { name: "case", kind: "radio", label: t("wiz_T191"), value: local.scope || "points_only",
        options: [{ value: "points_only", label: t("wiz_T193") }, { value: "times_only", label: t("wiz_T194") }, { value: "times_and_rolls", label: t("wiz_T196") }] },
      actions: [{ id: "case", label: t("wiz_T006"), kind: "primary" }] });
    return finish();
  }
  if (stage === "before") {
    const pointsOnly = path === "C" && scope === "points_only", timesOnly = path === "C" && scope === "times_only";
    const bModel = path === "B";
    if (bModel) {
      Object.assign(screen, { code: "B-02", phase: "readings", title: t("wiz_T167"), body: t("wiz_T168"),
        actions: [{ id: "begin", label: t("wiz_T076"), kind: "primary", note: t("wiz_T318") }] });
      return finish();
    }
    Object.assign(screen, {
      code: pointsOnly ? "C-37" : timesOnly ? "C-35" : path === "C" ? "C-03" : "A-03", phase: "prep", title: t("wiz_T021"),
      body: pointsOnly ? tx("wiz_T235", { ...values, travel: n(cover?.travel_cm) }) : timesOnly ? tx("wiz_T230", { ...values, travel: n(cover?.travel_cm) })
        : path === "C" ? tx("wiz_T197", values) : t("wiz_T022"),
      // Guided times only has no lift-off: the backend does not use the slat choice there.
      choice: pointsOnly || timesOnly ? null : { name: "slats", kind: "radio", label: t("wiz_T023"), value: local.slats === false ? "no" : "yes",
        options: [{ value: "yes", label: t("wiz_T198") }, { value: "no", label: t("wiz_T199") }] },
      // Readings only run as a preview: said before it starts.
      // No "Cancel" (T025) here or on A-16: it did what the header's "Abandon the calibration" does.
      actions: [{ id: "begin", label: t("wiz_T024"), kind: "primary", ...(pointsOnly ? { note: t("wiz_T318") } : {}) }] });
    return finish();
  }
  if (stage === "saved") return finish(savedScreen(screen, ctx, tx, values));

  // ---- A session (live or preview). ----
  if (!view) {
    Object.assign(screen, { code: "loading", title: t("loading"), actions: [] });
    return finish();
  }
  if (status.expired || view.reason === "expired") return finish(problemScreen(screen, ctx, "expired"));
  if (ENDED.includes(view.phase)) return finish(problemScreen(screen, ctx, view.reason || "stopped"));
  if (view.problem) return finish(problemScreen(screen, ctx, view.problem.reason || view.problem, true));
  if (view.phase === "paused") {
    Object.assign(screen, { code: "paused", phase: screen.phase, title: t("calPhase_paused"), body: t("calRecoveryHelp"),
      actions: [{ id: "continue", label: t("calContinue"), kind: "primary" }, stop] });
    return finish();
  }

  if (view.preview) return finish(previewScreen(screen, ctx, tx, n, values, stop));
  if (view.mode === "guided") return finish(guidedScreen(screen, ctx, tx, n, values, stop));
  return finish(geometryScreen(screen, ctx, tx, n, values, stop));
}

function caption(t, path, scope, cover) {
  if (path === "B") return fill(t("wiz_T169"), { profile: cover?.followProfile ?? cover?.profile?.name ?? "" });
  if (path === "C") return t(scope === "times_only" ? "wiz_T231" : scope === "points_only" ? "wiz_T236" : "wiz_T200");
  return t("wiz_T026");
}

/** Live `geometry` session: path A and path C (times and rolls). */
function geometryScreen(screen, ctx, tx, n, values, stop) {
  const { t, view, local = {}, path } = ctx;
  const p = (number) => `${path === "C" ? "C" : "A"}-${number}`;
  const slats = view.slats !== false;
  const elapsed = ctx.elapsed;
  const step = view.step, phase = view.phase;
  // A positioning run lasts about the full time of its direction (the time in use, the integration's default too).
  const positioning = (number, text, seconds = null) => Object.assign(screen, { code: p(number), title: t("wiz_T027"),
    wait: { text, stages: [], progress: waitBar(view, elapsed, seconds) }, actions: [stop] });
  const closingTime = timeInUse(ctx.cover?.effective?.closing);
  // A run to an end stop stays a positioning until the motor stops by itself or its full time has passed; only then
  // does the screen ask to confirm the end stop.
  const positioningRun = (seconds) => !MOTOR_STOPPED(view) && seconds > 0 && (elapsed ?? 0) < seconds;
  if (phase === "review" || phase === "saving") return summaryScreen(screen, ctx, tx, n, values);
  if (step === "home") {
    screen.phase = "prep";
    if (phase === "briefing") return Object.assign(screen, { code: p("03"), title: t("wiz_T021"), body: path === "C" ? tx("wiz_T197", values) : t("wiz_T022"),
      actions: [{ id: "next", label: t("wiz_T024"), kind: "primary" }] });
    // A-05 once the positioning is over: the end stop and "It did not do what it should" can be pressed at once, the
    // red Stop stays while the motor runs. T033 opens S-01 (nothing measured yet is lost). Not on A-10: there a stop
    // discards the lift-off measurement (§8.9).
    if (phase === "closing" && !positioningRun(closingTime)) return Object.assign(screen, { code: p("05"), title: t("wiz_T030"), body: t("wiz_T031"),
      actions: [{ id: "endpoint", label: t("wiz_T032"), kind: "primary" }, { id: "misbehaved", label: t("wiz_T033"), kind: "secondary" }, ...whileRunning(view, stop)] });
    return positioning("04", tx("wiz_T029", values), closingTime);
  }
  if (["lift", "reset", "opening"].includes(step)) screen.phase = "ascent";
  if (step === "closing") screen.phase = "descent";
  if (["half_open", "half_close", "top"].includes(step)) screen.phase = "readings";
  if (step === "lift") {
    if (phase === "briefing" && !local.ackLift && slats) return Object.assign(screen, { code: p("06"), title: t("wiz_T035"), body: t("wiz_T036"),
      actions: [{ id: "ack:lift", label: t("wiz_T037"), kind: "primary" }] });
    if (phase === "reading") {
      Object.assign(screen, { code: p("08"), title: t("wiz_T047"), body: t("wiz_T048"),
        field: { label: t("wiz_T049"), hint: t("wiz_T050"), min: 0, max: view.max_gap_cm ?? 20, kind: "gap" },
        actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }] });
      return screen;
    }
    const running = ["starting_open", "opening"].includes(phase);
    Object.assign(screen, { code: p("07"), title: t("wiz_T042"), body: path === "C" ? t("wiz_T202") : t("wiz_T043"),
      stopwatch: runWatch(t, n, view, elapsed),
      actions: [{ id: "next", label: t("wiz_T045"), kind: "primary", disabled: phase !== "briefing" },
        { id: "lift", label: t("wiz_T046"), kind: "primary", disabled: phase !== "opening" }, stop] });
    if (view.still_resting && phase === "briefing") screen.notices.push({ tone: "info", text: fill(t("calLiftRepeated"), view) });
    if (phase === "geometry_wait_stop") screen.stopwatch = null;
    return screen;
  }
  if (step === "reset") {
    if (phase === "briefing" && view.gap_warning) return Object.assign(screen, { code: p("08"), title: t("wiz_T047"), body: t("wiz_T048"),
      notices: [{ tone: "warning", text: fill(t("calGapWarning"), view) }],
      actions: [{ id: "next", label: t("wiz_T060"), kind: "primary" }, { id: "repeat", label: t("wiz_T061"), kind: "secondary" }] });
    // The same Stop rule as A-05 (only while the motor runs); no T033 here, a stop would discard the lift-off.
    if (phase === "closing" && !positioningRun(closingTime)) return Object.assign(screen, { code: p("10"), title: t("wiz_T053"), body: t("wiz_T054"),
      actions: [{ id: "endpoint", label: t("wiz_T032"), kind: "primary" }, ...whileRunning(view, stop)] });
    positioning("09", tx(path === "C" ? "wiz_T203" : "wiz_T052", values), closingTime);
    if (phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }];
    if (view.still_resting) screen.notices.push({ tone: "info", text: fill(t("calLiftRepeated"), view) });
    return screen;
  }
  if (step === "opening") {
    if (phase === "reading") {
      if (!local.ackAscent && slats) return Object.assign(screen, { code: p("12"), title: t("wiz_T058"),
        body: tx("wiz_T059", { slat: n(view.samples?.lift), run: n(view.values?.opening_time) }),
        actions: [{ id: "ack:ascent", label: t("wiz_T060"), kind: "primary" }, { id: "repeat", label: t("wiz_T061"), kind: "secondary" }] });
      return Object.assign(screen, { code: p("13"), title: t("wiz_T062"), body: t("wiz_T063"),
        field: { label: t("wiz_T064"), hint: t("wiz_T066"), min: 20, max: 500, kind: "travel", value: view.saved_travel_cm ?? null },
        actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }] });
    }
    Object.assign(screen, { code: p("11"), title: slats ? t("wiz_T055") : t("wiz_T040"), body: t("wiz_T056"),
      stopwatch: runWatch(t, n, view, elapsed),
      actions: [{ id: "next", label: t("wiz_T045"), kind: "primary", disabled: phase !== "briefing" },
        { id: "endpoint", label: t("wiz_T057"), kind: "primary", disabled: phase !== "opening" }, ...whileRunning(view, stop)] });
    if (phase === "geometry_wait_stop") screen.stopwatch = null;
    return screen;
  }
  if (step === "closing") {
    Object.assign(screen, { code: p("14"), title: t("wiz_T068"), body: t("wiz_T069"), stopwatch: runWatch(t, n, view, elapsed),
      actions: [{ id: "next", label: t("wiz_T045"), kind: "primary", disabled: phase !== "briefing" },
        { id: "endpoint", label: t("wiz_T070"), kind: "primary", disabled: phase !== "closing" }, ...whileRunning(view, stop)] });
    if (phase === "geometry_wait_stop") screen.stopwatch = null;
    return screen;
  }
  if (step === "half_open") {
    if (phase === "briefing" && !local.ackDescent) return Object.assign(screen, { code: p("15"), phase: "descent", title: t("wiz_T071"),
      body: tx("wiz_T072", { run: n(view.values?.closing_time) }),
      actions: [{ id: "ack:descent", label: t("wiz_T060"), kind: "primary" }, { id: "repeat", label: t("wiz_T061"), kind: "secondary" }] });
    if (phase === "briefing" && !local.ackReadings) return Object.assign(screen, { code: p("16"), title: t("wiz_T074"), body: t("wiz_T075"),
      actions: [{ id: "ack:readings", label: t("wiz_T076"), kind: "primary" }] });
    if (phase === "reading") return Object.assign(screen, { code: p("18"), title: t("wiz_T081"), body: t("wiz_T082"),
      field: halfField(ctx, tx, n), actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }, { id: "repeat", label: t("wiz_T033"), kind: "secondary" }] });
    const seconds = ((slats ? view.samples?.lift || 0 : 0) + (view.values?.opening_time || 0)) / 2;
    return Object.assign(screen, { code: p("17"), title: t("wiz_T027"),
      wait: { text: tx(path === "C" ? "wiz_T205" : "wiz_T080", values), stages: [{ text: tx("wiz_T079", { seconds: n(seconds, 0) }), state: "current" }],
        progress: waitBar(view, elapsed, seconds) },
      // Normally started by the wizard itself; if that did not happen the run can be started here.
      actions: phase === "briefing" ? [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop] : [stop] });
  }
  if (step === "top" && !local.ackReadings) {
    // The return to the top before a repeated descent: a positioning run to confirm at the end stop.
    positioning("09", t("wiz_T086"), view.values?.opening_time);
    screen.phase = "descent";
    // The end stop is confirmed once the positioning is over (motor stopped, or its measured time passed).
    if (phase === "opening" && !positioningRun(view.values?.opening_time)) screen.actions = [{ id: "endpoint", label: t("wizTopReached"), kind: "primary" }, ...whileRunning(view, stop)];
    if (phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop];
    return screen;
  }
  if (step === "top" || step === "half_close") {
    if (phase === "reading") return Object.assign(screen, { code: p("20"), title: t("wiz_T087"), body: t("wiz_T088"),
      field: halfField(ctx, tx, n), actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }, { id: "repeat", label: t("wiz_T033"), kind: "secondary" }] });
    const down = Math.max(((view.values?.closing_time || 0) - (view.geometry?.slat_time_s || 0)) / 2, 0);
    const first = step === "top";
    Object.assign(screen, { code: p("19"), title: t("wiz_T027"),
      wait: { text: t("wiz_T086"), stages: [
        { text: tx("wiz_T084", { seconds: n(view.values?.opening_time, 0) }), state: first ? "current" : "done" },
        { text: tx("wiz_T085", { seconds: n(down, 0) }), state: first ? "future" : "current" }],
      progress: waitBar(view, elapsed, first ? view.values?.opening_time : down) }, actions: [stop] });
    // The return to the top is a positioning run: Home Assistant needs its end stop confirmed.
    if (first && phase === "opening" && !positioningRun(view.values?.opening_time)) screen.actions = [{ id: "endpoint", label: t("wizTopReached"), kind: "primary" }, ...whileRunning(view, stop)];
    if (first && phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop];
    if (!first && phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop];
    return screen;
  }
  if (step === "check") {
    // A check of the measured model (the wizard does not offer one yet): its run is stopped by Home Assistant like the
    // intermediate runs, so no elapsed time; then the tape reading, from 0.1 cm to the measured travel.
    screen.phase = "readings";
    if (phase === "reading") return Object.assign(screen, { code: p("31"), title: t("wiz_T138"), body: t("wiz_T139"),
      field: { label: t("wiz_T064"), hint: tx("wiz_T123", { cm: n(view.check?.target_cm, 0) }), min: 0.1, max: view.travel_cm ?? 10000, kind: "height" },
      actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }, { id: "repeat", label: t("wiz_T033"), kind: "secondary" }] });
    positioning("30", t("wiz_T086"));
    if (phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop];
    return screen;
  }
  if (phase === "geometry_wait_stop") return positioning("04", "");
  return Object.assign(screen, { code: "unknown", title: t(`calPhase_${phase}`), actions: [stop] });
}

/** Live `guided` session for path C, times only: the existing two-run protocol. */
function guidedScreen(screen, ctx, tx, n, values, stop) {
  const { t, view, elapsed } = ctx;
  const phase = view.phase;
  if (phase === "review" || phase === "saving") return summaryScreen(screen, ctx, tx, n, values);
  if (["confirm_closed"].includes(phase)) return Object.assign(screen, { code: "C-05", phase: "prep", title: t("wiz_T030"), body: t("calPhase_confirm_closed"),
    actions: [{ id: "run:open", label: t("wiz_T045"), kind: "primary" }, stop] });
  if (["starting_open", "opening"].includes(phase)) return Object.assign(screen, { code: "C-11", phase: "ascent", title: t("wiz_T040"), body: t("calPhase_opening"),
    stopwatch: runWatch(t, n, view, elapsed),
    actions: [{ id: "run:open", label: t("wiz_T045"), kind: "primary", disabled: true },
      { id: "endpoint", label: t("wiz_T057"), kind: "primary", disabled: phase !== "opening" }, ...whileRunning(view, stop)] });
  if (phase === "confirm_open") return Object.assign(screen, { code: "C-12", phase: "descent", title: t("wiz_T058"), body: t("calPhase_confirm_open"),
    actions: [{ id: "run:close", label: t("wiz_T045"), kind: "primary" }, stop] });
  if (["starting_close", "closing"].includes(phase)) return Object.assign(screen, { code: "C-14", phase: "descent", title: t("wiz_T068"), body: t("calPhase_closing"),
    stopwatch: runWatch(t, n, view, elapsed),
    actions: [{ id: "run:close", label: t("wiz_T045"), kind: "primary", disabled: true },
      { id: "endpoint", label: t("wiz_T070"), kind: "primary", disabled: phase !== "closing" }, ...whileRunning(view, stop)] });
  return Object.assign(screen, { code: "unknown", title: t(`calPhase_${phase}`), actions: [stop] });
}

/** Simulated steps: fine-tuning (A, C), tape readings only (C) and path B. */
function previewScreen(screen, ctx, tx, n, values, stop) {
  const { t, view, path } = ctx;
  const points = view.path === "rolls", profile = view.path === "profile";
  const p = (number) => `${path === "B" ? "B" : path === "C" ? "C" : "A"}-${number}`;
  screen.phase = profile ? "readings" : points ? "readings" : "finetune";
  if (view.phase === "review") return summaryScreen(screen, ctx, tx, n, values);
  const readingCodes = { quarter_open: ["22", "23", "wiz_T122"], three_quarter_open: ["24", "25", "wiz_T126"],
    quarter_close: ["26", "27", "wiz_T130"], three_quarter_close: ["28", "29", "wiz_T134"], check: ["30", "31", "wiz_T138"] };
  const stageText = { back_down: "wiz_T120", back_up: "wiz_T084", quarter_open: "wiz_T121", three_quarter_open: "wiz_T125",
    quarter_close: "wiz_T129", three_quarter_close: "wiz_T133", check: "wiz_T137", bottom: "wiz_T171", half_travel: "wiz_T172" };
  if (view.phase === "positioning") {
    if (profile && view.step === "open_full") return Object.assign(screen, { code: "B-03", title: t("wiz_T027"),
      wait: { text: tx("wiz_T170", values), stages: [], progress: stagesBar(view) }, actions: [stop] });
    const stages = view.stages.map((stage, index) => ({ text: tx(stageText[stage.key], { seconds: n(stage.seconds, 0) }),
      state: index < view.stage_index ? "done" : index === view.stage_index ? "current" : "future" }));
    return Object.assign(screen, { code: profile ? "B-05" : p(readingCodes[view.step][0]), title: t("wiz_T027"),
      wait: { text: t("wiz_T086"), stages, progress: stagesBar(view) }, actions: [stop] });
  }
  if (view.phase === "reading") {
    if (view.step === "travel") return Object.assign(screen, { code: "B-04", title: t("wiz_T062"), body: t("wiz_T063"),
      field: { label: t("wiz_T064"), hint: t("wiz_T066"), min: 20, max: 500, kind: "travel" },
      actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }] });
    if (profile) return Object.assign(screen, { code: "B-06", title: t("wiz_T138"),
      body: tx("wiz_T173", { expected: n(view.expected_cm, 0), travel: n(view.travel_cm, 0) }),
      field: { label: t("wiz_T064"), hint: tx("wiz_T123", { cm: n(view.expected_cm, 0) }), min: 0, max: 10000, kind: "height" },
      actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }, { id: "repeat", label: t("wiz_T033"), kind: "secondary" }] });
    const [, number, title] = readingCodes[view.step];
    return Object.assign(screen, { code: p(number), title: t(title), body: view.step === "check" ? t("wiz_T139") : t("wiz_T082"),
      field: { label: t("wiz_T064"), hint: tx("wiz_T123", { cm: n(view.expected_cm, 0) }), min: 0, max: 10000, kind: "height" },
      actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }, { id: "repeat", label: t("wiz_T033"), kind: "secondary" }] });
  }
  if (view.phase === "check_result") {
    const check = view.check, passed = check.passed;
    if (profile) return Object.assign(screen, { code: passed ? "B-07" : "B-07b", title: t(passed ? "wiz_T141" : "wiz_T144"),
      body: tx(passed ? "wiz_T175" : "wiz_T176", { ...values, profile: ctx.cover?.followProfile ?? values.profile, gap: check.gap_cm,
        expected: n(check.predicted_cm, 0), measured: n(check.measured_cm, 0) }),
      actions: passed ? [{ id: "accept", label: t("wiz_T060"), kind: "primary" }, { id: "repeat_check", label: t("wiz_T143"), kind: "secondary" }]
        : [{ id: "correct", label: t("wiz_T177"), kind: "primary" }, { id: "repeat_check", label: t("wiz_T143"), kind: "secondary" }] });
    const verdict = { gap: check.gap_cm, seconds: n(check.check_seconds) };
    return Object.assign(screen, { code: p(passed ? "32" : "32b"), title: t(passed ? "wiz_T141" : "wiz_T144"),
      body: tx(passed ? "wiz_T142" : "wiz_T145", verdict),
      actions: passed ? [{ id: "accept", label: t("wiz_T060"), kind: "primary" }, { id: "repeat_check", label: t("wiz_T143"), kind: "secondary" }]
        : [{ id: "repeat_check", label: t("wiz_T143"), kind: "primary" }, { id: "redo_readings", label: t("wiz_T146"), kind: "secondary" },
          { id: "continue_anyway", label: t("wiz_T147"), kind: "link" }] });
  }
  return Object.assign(screen, { code: "unknown", title: t("loading"), actions: [stop] });
}

/** Before/after of every summary: A-21, A-33, B-08, C-21, C-33, C-36, C-38. */
function summaryScreen(screen, ctx, tx, n, values) {
  const { t, view, path, scope, cover, local = {} } = ctx;
  const effective = cover?.effective || {};
  const refine = view.preview && view.path === "refine", points = view.preview && view.path === "rolls", profileB = view.preview && view.path === "profile";
  const timesOnly = path === "C" && scope === "times_only";
  const follows = !!cover?.profile;
  screen.phase = "summary";
  // What would be applied: the session's values, a profile adapted to this travel (B), or the values in use (readings only).
  let after;
  if (profileB) {
    const chosen = ctx.followed || {};
    const scale = chosen.reference_travel_cm && view.travel_cm ? view.travel_cm / chosen.reference_travel_cm : 1;
    after = { opening: chosen.opening_time * scale, closing: chosen.closing_time * scale, slat: chosen.geometry?.slat_time_s ?? null,
      travel: view.travel_cm, opening_roll: chosen.geometry?.opening_roll ?? null, closing_roll: chosen.geometry?.closing_roll ?? null };
  } else if (view.preview) {
    after = { opening: view.values.opening_time, closing: view.values.closing_time, slat: view.values.slat_time_s ?? null, travel: view.travel_cm,
      opening_roll: view.values.opening_roll ?? null, closing_roll: view.values.closing_roll ?? null };
  } else {
    after = { opening: view.values?.opening_time ?? effective.opening?.value, closing: view.values?.closing_time ?? effective.closing?.value,
      slat: view.mode === "geometry" ? view.geometry?.slat_time_s ?? null : effective.slat_time_s?.value ?? null,
      travel: view.mode === "geometry" ? view.travel_cm : cover?.travel_cm ?? null,
      opening_roll: view.mode === "geometry" ? view.geometry?.opening_roll ?? null : effective.opening_roll?.value ?? null,
      closing_roll: view.mode === "geometry" ? view.geometry?.closing_roll ?? null : effective.closing_roll?.value ?? null };
  }
  // Fine-tuning compares with what the calibration just saved; everything else with the values in use.
  const base = refine && local.base ? local.base : { opening: effective.opening?.value, closing: effective.closing?.value,
    slat: effective.slat_time_s?.value ?? null, travel: cover?.travel_cm ?? null,
    opening_roll: effective.opening_roll?.value ?? null, closing_roll: effective.closing_roll?.value ?? null };
  const row = (label, key, unit, digits = 1) => {
    const before = base[key] == null ? "—" : `${n(base[key], digits)}${unit}`;
    const shown = after[key] == null ? "—" : `${n(after[key], digits)}${unit}`;
    return { label, before, after: shown === before ? "=" : shown, changed: shown !== before && base[key] != null };
  };
  screen.table = { headers: [t("wizTableValue"), t("wizTableBefore"), t("wizTableAfter")],
    rows: [row(t("wiz_T093"), "opening", " s"), row(t("wiz_T094"), "closing", " s"), row(t("wiz_T095"), "slat", " s"), row(t("wiz_T041"), "travel", " cm")] };
  const rolls = [row(t("wiz_T105"), "opening_roll", "", 2), row(t("wiz_T106"), "closing_roll", "", 2)];
  const rollText = { opening_roll: n(after.opening_roll, 2), closing_roll: n(after.closing_roll, 2) };
  screen.technical = { title: t("wizTechnical"), caption: profileB || (timesOnly && after.opening_roll != null) ? tx("wiz_T181", rollText)
    : points ? t("wiz_T239") : t("wiz_T104"), rows: rolls,
    code: profileB || timesOnly ? "" : ["slat_time_s", "opening_roll", "closing_roll"].map((key) => `${key}: ${after[key === "slat_time_s" ? "slat" : key] == null ? "—" : n(after[key === "slat_time_s" ? "slat" : key], key === "slat_time_s" ? 1 : 2)}`).join("\n") };
  if (timesOnly && after.opening_roll == null) screen.technical = null;
  const precision = view.check ? tx("wiz_T151", { gap: view.check.gap_cm, seconds: n(view.check.check_seconds) }) : null;
  const saveInfo = (key) => ({ title: t("wiz_T280"), body: counted(t, key, cover?.followers?.length ?? 0, values) });
  const save = { id: "save", label: t("wiz_T102"), kind: "primary" };
  if (profileB) {
    const followed = ctx.cover?.followProfile ?? "";
    Object.assign(screen, { code: "B-08", title: t("wiz_T179"), body: tx("wiz_T180", { ...values, profile: followed, travel: n(view.travel_cm, 0) }),
      saveInfo: { title: t("wiz_T280"), body: tx("wiz_T284", { profile: followed }) }, actions: [save] });
    return screen;
  }
  if (timesOnly) {
    Object.assign(screen, { code: "C-36", title: t("wiz_T179"), body: follows ? tx("wiz_T233", values) : t("wiz_T092"),
      saveInfo: follows ? saveInfo("wiz_T287") : saveInfo("wizSaveCoverOnly"), actions: [{ ...save, target: "cover_only" }] });
    return withSupport(screen, ctx, "cover_only");
  }
  if (points) {
    // C-38 shows the values in use in grey: only the rolls change.
    screen.table.mutedBefore = true;
    Object.assign(screen, { code: "C-38", title: t("wiz_T149"), body: t("wiz_T238"), precision,
      saveInfo: follows ? saveInfo("wiz_T288") : saveInfo("wizSaveCoverOnly"), actions: [{ ...save, target: "cover_only" }] });
    return screen;
  }
  // A and C (times and rolls): one Save, with the reusable-profile switch.
  const c = path === "C";
  const block = profileBlock(ctx, tx, c);
  const target = block.target;
  Object.assign(screen, { code: c ? (refine ? "C-33" : "C-21") : refine ? (follows ? "A-33c" : "A-33") : follows ? (block.choice ? "A-21d" : "A-21c") : "A-21",
    title: t(refine ? "wiz_T149" : "wiz_T091"),
    body: c ? (follows ? tx(refine ? "wiz_T226" : "wiz_T210", values) : t(refine ? "wiz_T150" : "wiz_T092"))
      : t(refine ? (follows ? "wiz_T152" : "wiz_T150") : (follows ? "wiz_T107" : "wiz_T092")),
    precision, profileBlock: block,
    saveInfo: c ? (follows ? saveInfo(refine ? "wiz_T286" : "wiz_T285") : saveInfo("wizSaveCoverOnly"))
      : saveInfo(refine ? (follows ? "wiz_T283" : "wiz_T282") : (follows ? "wiz_T281" : "wiz_T289")),
    // Fine-tuning is offered once this is saved (A-34), not here.
    actions: [{ ...save, target }] });
  return withSupport(screen, ctx, target);
}

/** "Also save as reusable profile": on by default for a first cover, off when it already follows a profile. */
function profileBlock(ctx, tx, pathC) {
  const { t, cover, local = {} } = ctx;
  const follows = !!cover?.profile;
  const on = local.saveProfile ?? (!follows && !pathC);
  const choice = on && follows ? { name: "save_choice", value: local.saveChoice || "new",
    // Listed as in A-21d: update first, then a new profile (still the default choice, §9.10).
    options: [{ value: "update", label: tx("wiz_T109", { profile: cover.profile.name }),
      description: counted(t, "wiz_T110", cover.followers?.length ?? 0, { names: ctx.followerNames || "—" }) }, { value: "new", label: t("wiz_T111") }] } : null;
  const creating = on && (!follows || choice.value === "new");
  const nameValue = local.profileName ?? slug(cover?.name || "");
  const block = { switchLabel: t("wiz_T096"), on, explanation: follows ? tx("wiz_T108", { profile: cover.profile.name }) : t("wiz_T097"), choice,
    name: creating ? { label: t("wiz_T098"), value: nameValue, hint: t("wiz_T100"),
      line: follows ? counted(t, "wiz_T112", cover.followers?.length ?? 0, { profile: cover.profile.name, names: ctx.followerNames || "—" }) : tx("wiz_T101", { name: nameValue }),
      valid: /^[A-Za-z0-9_]{1,64}$/.test(nameValue) } : null,
    target: !on ? "cover_only" : creating ? "profile_new" : "profile_update" };
  return block;
}

function withSupport(screen, ctx, target) {
  const supported = ctx.supports ? ctx.supports(target) : true;
  if (!supported) {
    screen.notices.push({ tone: "warning", text: ctx.t("wizSaveUnavailable") });
    for (const action of screen.actions) if (action.id === "save") action.disabled = true;
  }
  if (screen.profileBlock?.name && !screen.profileBlock.name.valid) {
    for (const action of screen.actions) if (action.id === "save") action.disabled = true;
  }
  return screen;
}

/** Profile names: letters, digits and underscores, from the cover name. */
export function slug(text) {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLocaleLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 64) || "profile";
}

function savedScreen(screen, ctx, tx, values) {
  const { t, path, local = {} } = ctx;
  const saved = local.saved || {};
  // "Close" keeps each mockup's own style: B-09 red filled, A-34 red text, C-34 red outlined.
  const close = (of) => ({ id: "close", label: t("wiz_T158"), kind: of === "B" ? "danger" : of === "C" ? "danger-outline" : "link" });
  screen.discard = false;
  screen.phase = "done";
  screen.preview = !!saved.preview;
  // The end of a preview never says that something was saved: what was saved for real is said as such.
  if (saved.preview) {
    // The check mark of A-34 says "saved": not drawn at the end of a preview.
    screen.illustration = false;
    return Object.assign(screen, { code: path === "B" ? "B-09" : path === "C" ? "C-34" : "A-34", title: t("wiz_T320"),
      body: local.baseSaved ? t("wiz_T322") : tx("wiz_T321", values),
      actions: path === "B" ? [close("B")]
        : [{ id: "another", label: t("wiz_T156"), kind: "primary" }, { id: "open-cover", label: t("wiz_T157"), kind: "secondary" }, close(path)] });
  }
  if (path === "B") return Object.assign(screen, { code: "B-09", title: t("wiz_T154"),
    body: tx("wiz_T182", { ...values, profile: ctx.cover?.followProfile ?? "", travel: number(saved.travel_cm, ctx.language, 0) }),
    actions: [close("B")] });
  const body = saved.target === "profile_new" ? tx("wiz_T155", { name: saved.name ?? "" })
    : path === "C" && ctx.cover?.profile ? tx("wiz_T228", values) : tx("wizSavedCover", values);
  // A-34: the base calibration is saved; fine-tuning (path C on the same cover) is the primary next step, explained
  // by the body's second paragraph (T319).
  if (path !== "C") return Object.assign(screen, { code: "A-34", title: t("wiz_T154"), body: `${body}\n\n${t("wiz_T319")}`,
    actions: [{ id: "refine", label: t("wiz_T103"), kind: "primary" }, { id: "another", label: t("wiz_T156"), kind: "secondary" },
      { id: "open-cover", label: t("wiz_T157"), kind: "secondary" }, close(path)] });
  return Object.assign(screen, { code: "C-34", title: t("wiz_T154"), body,
    actions: [{ id: "another", label: t("wiz_T156"), kind: "primary" }, { id: "open-cover", label: t("wiz_T157"), kind: "secondary" }, close(path)] });
}

/** S-01…S-06: a step that ended. Today's sessions end with their reason (repeating starts over);
 * a published `problem` (L2) keeps the earlier measurements and repeats only the step. */
function problemScreen(screen, ctx, reason, step = false) {
  const { t } = ctx;
  const family = { unexpected_movement: ["S-01", "wiz_T240", "wiz_T241", "wiz_T243"], external_command: ["S-01", "wiz_T240", "wiz_T241", "wiz_T243"],
    unexpected_stop: ["S-01", "wiz_T240", "wiz_T241", "wiz_T243"], stopped: ["S-01", "wiz_T240", "wiz_T241", "wiz_T243"],
    not_delivered: ["S-02", "wiz_T244", "wiz_T245", "wiz_T247"], start_timeout: ["S-02", "wiz_T244", "wiz_T245", "wiz_T247"], no_echo: ["S-02", "wiz_T244", "wiz_T245", "wiz_T247"],
    not_stopped: ["S-03", "wiz_T248", "wiz_T249", "wiz_T251"], stop_queue_full: ["S-03", "wiz_T248", "wiz_T249", "wiz_T251"],
    invalid_measurement: ["S-04", "wiz_T252", "wiz_T253", "wiz_T243"], bad_point: ["S-04", "wiz_T252", "wiz_T253", "wiz_T243"],
    travel_timeout: ["S-05", "wiz_T254", "wiz_T255", "wiz_T258"], timeout: ["S-05", "wiz_T254", "wiz_T255", "wiz_T258"],
    expired: ["S-06", "wiz_T259", "wiz_T260", "wiz_T261"] }[reason] || ["S-01", "wiz_T240", null, "wiz_T243"];
  const [code, title, body, retry] = family;
  screen.code = code;
  screen.title = t(title);
  if (code === "S-06") {
    screen.body = t(body);
    // As in its mockup, "Close" is outlined in red.
    screen.actions = [{ id: "start-over", label: t("wiz_T261"), kind: "primary" }, { id: "close", label: t("wiz_T158"), kind: "danger-outline" }];
  } else if (step) {
    // The step alone is repeated: the texts of the mockups describe exactly this.
    screen.body = t(body);
    // The state of the motor (and, for S-05, of the stopwatch) as plain lines under the text, as in the mockups.
    // `elapsed_s` is the name expected from L2 for the time the run had when it was cut off; without it the line is left out.
    const seconds = ctx.view?.problem?.elapsed_s;
    screen.status = [t(code === "S-02" ? "wiz_T246" : code === "S-03" ? "wiz_T250" : code === "S-05" ? "wiz_T256" : "wiz_T242"),
      ...(code === "S-05" && seconds != null ? [fill(t("wiz_T257"), { seconds: number(seconds, ctx.language || "en", 1) })] : [])];
    screen.actions = [{ id: "repeat_step", label: t(retry), kind: "primary" }, { id: "stop", label: t("wiz_T028"), kind: "stop" }];
  } else {
    // Today's backend discards the session: say what it says, and offer to start over.
    const key = `calReason_${reason}`;
    screen.body = t(key) === key ? t("calPhase_interrupted") : t(key);
    screen.actions = [{ id: "start-over", label: t("wiz_T261"), kind: "primary" }, { id: "close", label: t("wiz_T158"), kind: "secondary" }];
  }
  screen.discard = false;
  return screen;
}

/**
 * A reading at half the opening or closing time: with the session's `reading_range` the hint gives the heights
 * the fit accepts (never a target) and the field refuses the others before sending; otherwise the mockup's rough
 * expectation (T083).
 */
function halfField(ctx, tx, n) {
  const { t, view, language = "en" } = ctx, span = view.reading_range;
  if (!span) return { label: t("wiz_T064"), hint: tx("wiz_T083", { cm: n(view.expected_cm, 0) }), min: 0.1, max: 10000, kind: "height" };
  return { label: t("wiz_T064"), hint: fill(t("calReadingRange"), readingRange(span, language)),
    min: span.min_cm - RANGE_SLACK_CM, max: span.max_cm + RANGE_SLACK_CM, kind: "height", range: true };
}

function runWatch(t, n, view, elapsed) {
  if (!MEASURED_RUN(view)) return null;
  // Stopped by itself: the stopwatch stays at the time of the stop frame ("Stopwatch: stopped at 22.2 s").
  const frozen = MOTOR_STOPPED(view) && view.stopped_elapsed != null;
  if (!frozen && elapsed == null) return null;
  const [label, value] = splitLabel(frozen ? fill(t("wiz_T257"), { seconds: n(view.stopped_elapsed) }) : fill(t("wiz_T044"), { seconds: n(elapsed) }));
  return { label, value };
}

/** "Motor: moving for 4.0 s" → ["Motor", "moving for 4.0 s"], as the box shows them. */
export function splitLabel(text) {
  const index = text.indexOf(": ");
  return index < 0 ? ["", text] : [text.slice(0, index), text.slice(index + 2)];
}

/**
 * The bar of a wait: the share of `seconds` already run (0 until the movement is under way) and the seconds left.
 * Without a known duration (a never measured cover) `value` and `remaining` are null: the bar is indeterminate.
 */
function waitBar(view, elapsed, seconds) {
  // The motor stopped before the expected time: the run is over, the bar is complete and no time is left.
  if (MOTOR_STOPPED(view)) return { value: 1, remaining: null };
  if (!(seconds > 0)) return { value: null, remaining: null };
  const done = ["opening", "closing"].includes(view.phase) && elapsed != null ? Math.min(seconds, Math.max(0, elapsed)) : 0;
  return { value: done / seconds, remaining: secondsLeft(seconds - done) };
}

/** A simulated positioning advances by stages: the stages done over the whole, the stages left as the time left. */
function stagesBar(view) {
  const seconds = (view.stages || []).map((stage) => stage.seconds || 0), total = seconds.reduce((sum, value) => sum + value, 0);
  if (!(total > 0)) return { value: null, remaining: null };
  const done = seconds.slice(0, view.stage_index || 0).reduce((sum, value) => sum + value, 0);
  return { value: done / total, remaining: secondsLeft(total - done) };
}

/** Whole seconds left, never 0 while the bar is shown (sums of tenths are not exact: 11.000000001 is 11). */
function secondsLeft(seconds) { return Math.max(1, Math.ceil(seconds - 0.001)); }

/** The full time of a positioning run: the time in use, the integration's default included. */
function timeInUse(entry) {
  return entry && entry.value > 0 ? entry.value : null;
}

/** A time in use counts as known once measured or configured; the integration's default is only a guess. */
function knownTime(entry) {
  return entry && entry.value > 0 && entry.origin !== "default" ? entry.value : null;
}

/**
 * The drawing of each mockup, by the number of its code (C-05…C-34 are the clones of A): its illustration id and
 * where it sits. Readings with the tape show it between the text and the field; steps and briefings under the title
 * (and the motor bar), above the text. Every other screen has none (A-09 too: its frame shows only the wait box).
 */
const BEFORE = "before-body", AFTER = "after-body";
const ILLUSTRATION_OF = {
  A: { "05": ["window-closed", BEFORE], "06": ["two-runs", BEFORE], "07": ["lift-sequence", BEFORE], "08": ["lift-zoom", AFTER],
    "11": ["ascent-sequence", BEFORE], "13": ["curtain-open-tape", AFTER], "14": ["descent-sequence", BEFORE],
    "16": ["curtain-partial-tape", BEFORE], "18": ["curtain-partial-tape", AFTER], "20": ["curtain-partial-tape", AFTER],
    "23": ["curtain-partial-tape", AFTER], "25": ["curtain-partial-tape", AFTER], "27": ["curtain-partial-tape", AFTER],
    "29": ["curtain-partial-tape", AFTER], "31": ["curtain-partial-tape", AFTER], "34": ["check", BEFORE] },
  B: { "02": ["curtain-open-tape", BEFORE], "06": ["curtain-partial-tape", AFTER] },
};
ILLUSTRATION_OF.C = ILLUSTRATION_OF.A;

function illustrationFor(code) {
  const [, letter, number] = /^([ABC])-(\d+)$/.exec(code || "") || [];
  const entry = letter && ILLUSTRATION_OF[letter][number];
  return entry ? { id: entry[0], position: entry[1] } : null;
}

/** Header line, stepper, read-only and connection state: the same on every screen. */
function finalize(screen, ctx) {
  const { t, language = "en", path = "A", scope, view, status = {}, local = {} } = ctx;
  // A screen may opt out (false) where its code is shared with a run the drawing does not show.
  screen.illustration = screen.illustration === false ? null : screen.illustration || illustrationFor(screen.code);
  const n = (value, digits = 1) => number(value, language, digits);
  // Under a wait's bar, the time left when its duration is known.
  if (screen.wait) screen.wait.remaining = screen.wait.progress?.remaining != null ? fill(t("wiz_T402"), { seconds: n(screen.wait.progress.remaining, 0) }) : "";
  const refining = (view?.preview && view.path === "refine") || local.refining;
  if (["choose", "path"].includes(ctx.stage)) screen.caption = "";
  const phases = phasesFor(path, scope, refining);
  let current = phases.indexOf(screen.phase);
  if (refining && screen.phase === "summary") current = phases.length - 1;
  if (screen.phase === "done") current = phases.length;
  const source = view && !view.preview ? view : null;
  const base = local.base || {};
  const values = source?.values || {}, samples = source?.samples || {}, readings = { ...(local.baseReadings || {}), ...(source?.readings || {}) };
  const seconds = (value) => value == null ? "—" : `${n(value)} s`, cm = (value) => value == null ? "—" : `${n(value)} cm`;
  const slats = source ? source.slats !== false : local.slats !== false;
  const sub = {
    // The path chosen ("Ⓐ first of its type") is the introduction's sub-line, as the mockups' stepper shows it.
    intro: screen.caption ? [["", screen.caption]] : [],
    ascent: [...(slats && !(path === "C" && scope === "times_only") ? [[t("wiz_T039"), (samples.lift ?? base.lift) != null
      ? `${n(samples.lift ?? base.lift)} s · ${(readings.gap ?? base.gap) != null ? cm(readings.gap ?? base.gap) : "—"}` : "—"]] : []),
      [t("wiz_T040"), seconds(values.opening_time ?? base.opening)],
      ...(path === "C" && scope === "times_only" ? [] : [[t("wiz_T041"), cm(source?.travel_cm ?? base.travel)]])],
    descent: [[t("wiz_T068"), seconds(values.closing_time ?? base.closing)]],
    readings: path === "B" ? [[t("wiz_T041"), cm(view?.travel_cm ?? local.fineReadings?.travel)],
      [t("wiz_T119"), (view?.check ?? local.fineReadings?.check) ? `${(view?.check ?? local.fineReadings.check).gap_cm} cm` : "—"]]
      : path === "C" && scope === "points_only" ? fineSub(t, view, cm, local.fineReadings)
        : [[t("wiz_T077"), cm(readings.half_open)], [t("wiz_T078"), cm(readings.half_close)]],
    finetune: refining ? fineSub(t, view, cm, local.fineReadings) : [],
  };
  const finetuneLabel = refining ? t("wiz_T114") : t("wiz_T013");
  screen.stepper = {
    line: screen.phase === "done" ? t("wiz_T153") : fill(t("wizPhaseLine"), { phase: screen.phase === "finetune" ? t("wiz_T114") : t(PHASES[screen.phase] || "wiz_T007"),
      n: current + 1, total: phases.length }),
    phases: phases.map((key, index) => ({ key, label: key === "finetune" ? finetuneLabel : t(PHASES[key]),
      // A-34 after a real save: fine-tuning (optional) is still ahead, so it is not ticked.
      state: key === "finetune" && screen.code === "A-34" && !screen.preview && !refining ? "future"
        : index < current ? "done" : index === current ? "current" : "future",
      substeps: index <= current ? (sub[key] || []).map(([label, value]) => ({ label, value })) : [] })),
  };
  // A reader sees the step and Stop only; another tab or device guides it.
  if (view?.read_only && !ENDED.includes(view.phase)) {
    // As S-07: the actions column says who guides it (T262, plain text) above the explanation and Take control;
    // a reader has no reading field to fill.
    screen.readOnly = { status: t("wiz_T262"), text: t("wiz_T263"), take: t(status.confirmTake ? "calConfirmTakeControl" : "wiz_T264"),
      consequence: status.confirmTake ? t("wiz_T265") : null, primary: view.owner_present === false };
    // Stop stays available to every reader while something may move (L1: a safety control).
    screen.actions = MOVING(view) ? [{ id: "stop", label: t("wiz_T028"), kind: "stop" }] : [];
    screen.field = null;
  }
  // Alone in a wait, Stop is the red filled button of the mockups; beside a step's buttons it stays a red link.
  if (screen.wait && screen.actions.length === 1 && screen.actions[0].id === "stop") screen.actions[0] = { ...screen.actions[0], kind: "danger" };
  if (status.lost && !status.expired && view && !ENDED.includes(view.phase)) {
    screen.notices.push({ tone: "error", text: t("calVisual_disconnected") });
    if (view.recoverable) screen.actions.push({ id: "reconnect", label: t("calResume"), kind: "secondary" });
  }
  if (status.notice) screen.notices.push({ tone: "warning", text: t(status.notice) });
  if (status.cancelPending) screen.notices.push({ tone: "error", text: t("calCancelFailed") });
  if (status.error) {
    const key = `profileError_${status.error.code}`;
    const values = { ...(view || {}), ...(readingRange(view?.reading_range, language, status.error.reading) || {}) };
    const text = t(key) === key ? t(view?.preview ? "calReadingNumber" : "calConnectionError") : fill(t(key), values);
    // A refusal whose values are gone (the session moved on) is not shown with empty placeholders.
    if (!/\{\w+\}/.test(text)) screen.notices.push({ tone: "error", text });
  }
  // A reading refused in the field, before anything is sent.
  if (local.fieldError != null && screen.field?.range) {
    screen.notices.push({ tone: "error", text: fill(t("profileError_reading_out_of_range"), readingRange(view.reading_range, language, local.fieldError)) });
  }
  // Movement, readings and Save wait for an answer, a connection and ownership; Stop never does.
  if (status.locked) for (const action of screen.actions) if (!["stop", "reconnect", "close", "start-over"].includes(action.id)) action.disabled = true;
  if (status.locked && screen.field) screen.field = { ...screen.field, disabled: true };
  return screen;
}

function fineSub(t, view, cm, kept = {}) {
  const readings = view?.preview ? view.readings || {} : kept || {};
  const check = view?.preview ? view.check : kept?.check;
  return [[t("wiz_T115"), cm(readings.quarter_open)], [t("wiz_T116"), cm(readings.three_quarter_open)],
    [t("wiz_T117"), cm(readings.quarter_close)], [t("wiz_T118"), cm(readings.three_quarter_close)],
    [t("wiz_T119"), check ? `${check.gap_cm} cm` : "—"]];
}
