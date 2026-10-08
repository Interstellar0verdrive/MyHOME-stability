/**
 * Which screen of the calibration mockups (A-xx, B-xx, C-xx, S-xx) a moment of the wizard is.
 *
 * Pure: from the wizard's local choices and the session view it returns plain data (texts already
 * filled, fields, buttons, stepper), and the wizard only draws it. Text keys are those of the
 * shared translation sheet (`wiz_T…`); a few screen-only keys are `wiz…`.
 */
const asset = (name) => { const url = new URL(name, import.meta.url); url.search = new URL(import.meta.url).search; return url.href; };
const { fill, number, fixed, readingRange, RANGE_SLACK_CM, dateText, shortDate, followedBy } = await import(asset("panel-calibration-text.js"));

const PHASES = {
  intro: "wiz_T007", prep: "wiz_T008", ascent: "wiz_T009", descent: "wiz_T010", readings: "wiz_T011", summary: "wiz_T012", finetune: "wiz_T013",
};

/** The phases each path shows, in order (C depends on what is remeasured). */
export function phasesFor(path, scope, refining) {
  if (path === "B") return ["intro", "readings", "summary"];
  if (path === "C" && scope === "times_only") return ["intro", "prep", "ascent", "descent", "summary"];
  if (path === "C" && scope === "points_only") return ["intro", "prep", "readings", "summary"];
  // N-10: fine-tuning's own summary is part of «Perfezionamento» (the last step): the count stays 7, «Riepilogo» once.
  return ["intro", "prep", "ascent", "descent", "readings", "summary", "finetune"];
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
/** How long before the session's idle expiry the wizard warns (M3). */
export const LEASE_WARNING_MS = 120000;

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

/** A-02's box on the chosen cover: the profile it follows, its calibration, or that it was never measured. */
function pathContext(t, cover, language) {
  if (!cover) return "";
  // G2-1: without a measured travel the profile's values are not scaled, and the line says so.
  if (cover.profile?.name) return fill(t(cover.travel_cm > 0 ? "wiz_T395" : "wiz_T455"), { profile: cover.profile.name });
  if (cover.status && cover.status !== "to_measure") {
    // Inside «already calibrated (…)» the detail of the status, not the badge (G3-7: the badge says «Calibrated (…)»).
    return fill(t("wiz_T399"), { status: t(`calTabStatusDetail_${cover.status}`), date: dateText(cover.last, language) || "—" });
  }
  return t("wiz_T418");
}

/** Profiles whose reference travel is within this share of the cover's saved travel count as "the same size". */
export const SIMILAR_TRAVEL = 0.05;

/**
 * A-02's advice. Already calibrated: Ⓒ. Never measured: Ⓑ when a profile's reference travel is within ±5 % of the
 * cover's saved travel (the closest first), otherwise Ⓐ, with a badge only when no profile exists (with profiles the
 * user judges the similarity from the list under Ⓑ). The "if unsure" line always names the advised path.
 */
export function pathAdvice(cover, profiles = []) {
  const measured = !!cover?.status && cover.status !== "to_measure";
  if (measured) return { badge: "C", hint: "C", similar: [] };
  const travel = cover?.travel_cm;
  const similar = travel > 0 ? profiles.filter((profile) => profile.referenceTravel > 0 && Math.abs(profile.referenceTravel - travel) <= travel * SIMILAR_TRAVEL)
    .sort((a, b) => Math.abs(a.referenceTravel - travel) - Math.abs(b.referenceTravel - travel)) : [];
  if (similar.length) return { badge: "B", hint: "B", similar };
  // G4-2 (replaces R4-9b): there is always exactly one advised option, badge and preselection included.
  return { badge: "A", hint: "A", similar: [] };
}

/** The wizard's whole state as one screen. */
export function buildScreen(ctx) {
  const { t, language = "en", path = "A", scope = null, stage, local = {}, cover, view, status = {}, preview = false } = ctx;
  const n = (value, digits = 1) => number(value, language, digits);
  n.fixed = (value, digits = 1) => fixed(value, language, digits);
  const tx = (key, values) => fill(t(key), values);
  const name = cover?.name || "";
  const values = { cover: name, profile: cover?.profile?.name ?? "" };
  // D-21: before the case is confirmed (C-01, C-02) the stepper and its caption follow the case chosen so far, the
  // preselected «tape readings only» at first.
  // D-21 (Y): on C-01 the case is not chosen yet: the stepper shows only the introduction under «Perfezionamento».
  const stepScope = scope ?? (path === "C" && stage === "case" ? "points_only" : null);
  const screen = {
    code: "", header: { title: name || t("wiz_T001"), subtitle: cover?.address || "", units: cover?.units || null }, discard: true, preview,
    title: "", subline: "", body: "", help: null, note: null, results: null, stopwatch: null, wait: null, illustration: null, choice: null, picker: null, field: null, box: null, table: null,
    technical: null, profileBlock: null, saveInfo: null, precision: null, status: [], notices: [], actions: [], links: [], readOnly: null, phase: "intro",
    caption: caption(t, path, stepScope, cover), stepScope,
    // Before any session the header offers a way back to the previous choice (kept as it was).
    back: ["choose", "path", "profile", "current", "case", "before"].includes(stage),
  };
  const stop = { id: "stop", label: t("wiz_T028"), kind: "stop" };
  const finish = () => finalize(screen, ctx);

  // ---- Before any session: choices that stay in the browser. ----
  if (stage === "choose") {
    // The covers as a list with one radio each (the sequence view's rows, the list's filters and order); Continue
    // waits for a choice. The chosen row opens and says what choosing it means.
    const picked = local.coverPicked ? (ctx.covers || []).find((item) => item.key === local.coverKey) : null;
    const notes = [];
    // A calibrated cover: one warning that a new measurement replaces its values (and the profile it follows);
    // fine-tuning is the way to adjust them. A cover that only follows a profile says which.
    if (picked?.status && picked.status !== "to_measure") {
      notes.push({ tone: "warning", text: fill(t(cover?.profile?.name ? "wiz_T413" : "wiz_T414"), { profile: cover?.profile?.name ?? "",
        status: t(`calTabStatusDetail_${picked.status}`), date: dateText(picked.last, language) || "—" }) });
    } else if (picked && cover?.profile?.name) notes.push({ tone: "info", text: fill(t("wiz_T395"), { profile: cover.profile.name }) });
    Object.assign(screen, { code: "A-01", phase: "intro", title: t("wiz_T003"), body: t("wiz_T004"),
      picker: { selected: picked ? local.coverKey : "", filter: local.pickFilter || "all", notes },
      actions: [{ id: "choose", label: t("wiz_T006"), kind: "primary", disabled: !ctx.covers?.length || !picked }] });
    // Until a cover is picked the subtitle says so; then its room and address (its name is in the chosen row, not
    // repeated here: responsive map §3.3).
    screen.header = picked ? { title: t("wiz_T001"), subtitle: cover?.address || "", units: cover?.units || null }
      : { title: t("wiz_T001"), subtitle: t("wiz_T392"), placeholder: true };
    return finish();
  }
  if (stage === "path") {
    // A radio list (A-02 Section A) with Continue in the actions; the advised path carries a badge.
    const list = ctx.profiles || [], profiles = list.length, measured = !!cover?.status && cover.status !== "to_measure";
    const advice = pathAdvice(cover, list);
    // G2-4: a path is named by its option's own label, never by a letter.
    const label = { A: t("wiz_T017"), B: t("wiz_T018"), C: t("wiz_T019") };
    // Under Ⓑ: how many profiles exist, then why it is advised (similar travel) or, on a never measured cover, each
    // profile with its slats and reference travel so the user can judge the similarity.
    const describe = (profile) => [profile.name, t(profile.slat == null ? "wiz_T370" : profile.slat > 0 ? "wiz_T368" : "wiz_T369"),
      ...(profile.referenceTravel > 0 ? [fill(t("wiz_T372"), { cm: n(profile.referenceTravel, 0) })] : [])].join(" · ");
    // G2-2: each option carries its explanation as the first line of its note, then what applies to this cover.
    const bNote = !profiles ? [t("wiz_T453"), t("wiz_T401")] : [t("wiz_T453"), profiles === 1 ? t("wiz_T419") : fill(t("wiz_T420"), { count: profiles }),
      ...(advice.similar.length ? advice.similar.map((profile) => fill(t("wiz_T422"), { profile: profile.name, travel: n(cover.travel_cm, 0), reference: n(profile.referenceTravel, 0) }))
        : measured ? [] : list.map(describe))];
    const options = [
      { value: "A", label: label.A, note: [t("wiz_T452")] },
      { value: "B", label: label.B, disabled: !profiles, note: bNote },
      // Fine-tuning corrects values a cover already has: never on a cover never measured.
      { value: "C", label: label.C, note: [t("wiz_T454"), ...(measured ? [] : [t("wiz_T423")])], ...(measured ? {} : { disabled: true }) },
    ].map((option) => ({ ...option, badge: option.value === advice.badge && !option.disabled ? t("wiz_T400") : "" }));
    // Preselected on the badge, Continue is ready; without a badge nothing is chosen and Continue waits.
    const enabled = (value) => options.some((option) => option.value === value && !option.disabled);
    const chosen = enabled(local.pathChoice) ? local.pathChoice : advice.badge && enabled(advice.badge) ? advice.badge : "";
    // On a calibrated cover another path than the advised one says what it replaces, under the chosen option.
    if (measured && chosen && chosen !== advice.badge) {
      const warning = chosen === "A" ? fill(t("wiz_T415"), { option: label.C }) : chosen === "B" ? t(cover?.profile ? "wiz_T416" : "wiz_T417") : "";
      const option = options.find((item) => item.value === chosen);
      if (warning) option.warning = warning;
    }
    // "There are three paths", then always "If unsure, choose «…»" with the advised option's label; the options follow.
    // G3-1: why the advised option is advised, in one impersonal sentence (none when nothing is advised).
    const closest = advice.similar[0];
    const reason = measured ? fill(t(cover?.profile?.name ? "wiz_T464" : "wiz_T463"), { option: label.C, profile: cover?.profile?.name ?? "" })
      : advice.badge === "B" && closest ? fill(t("wiz_T467"), { option: label.B, travel: n(cover.travel_cm, 0), reference: n(closest.referenceTravel, 0), profile: closest.name })
        : !profiles ? fill(t("wiz_T466"), { option: label.A })
          : !(cover?.travel_cm > 0) ? fill(t("wiz_T465"), { option: label.A }) : fill(t("wiz_T476"), { option: label.A, travel: n(cover.travel_cm, 0) });
    // G4-2: the reason ends with «If in doubt, choose this option.»; no separate «If unsure» line.
    const body = [t("wiz_T016"), `${reason} ${t("wiz_T475")}`].join("\n\n");
    Object.assign(screen, { code: "A-02", phase: "intro", title: tx("wiz_T015", { name }), subline: pathContext(t, cover, language), body,
      choice: { name: "path", kind: "radio", label: tx("wiz_T015", { name }), legendHidden: true, value: chosen, options },
      actions: [{ id: "path", label: t("wiz_T006"), kind: "primary", disabled: !chosen }],
      // D-21: the stepper shows the steps of the path chosen so far (the advised one at first).
      stepPath: chosen || path });
    return finish();
  }
  if (stage === "profile") {
    const chosen = ctx.profiles?.find((item) => item.id === local.profileId) || ctx.profiles?.[0];
    // One radio row per profile: "tall_two_leaf · measured on Living room shutter 1", then who follows it by name.
    const about = (item) => fill(t("wiz_T165").split(" · ")[0], { cover: item.measuredOn || "—" });
    // Y-c: path B runs only as a preview: B-01 says so under its button, as B-02 does.
    Object.assign(screen, { code: "B-01", phase: "intro", title: t("wiz_T161"), body: t("wiz_T162"),
      choice: { name: "profile", kind: "radio", label: t("wiz_T163"), value: chosen?.id ?? "",
        options: (ctx.profiles || []).map((item) => ({ value: item.id, label: `${item.name} · ${lowerFirst(about(item), language)}`, plain: true,
          note: [followedBy(t, item.followerNames || [], language)] })) },
      actions: [{ id: "profile", label: t("wiz_T006"), kind: "primary", disabled: !chosen, note: t("wiz_T318") }] });
    return finish();
  }
  if (stage === "current") {
    const effective = cover?.effective || {};
    Object.assign(screen, { code: "C-01", phase: "intro", title: t("wiz_T184"),
      // G2-1: with no measured travel the first paragraph says the values are the profile's, not scaled.
      body: !cover?.profile ? tx("wizNoProfileBody", values) : cover.travel_cm > 0 ? tx("wiz_T185", { ...values, travel: n(cover.travel_cm) })
        : [tx("wiz_T455", values), ...tx("wiz_T185", { ...values, travel: "" }).split(/\n\s*\n/).slice(1)].join("\n\n"),
      // A bold title and one line per value: the sheet's single line (T188) split at its separators.
      box: { label: t("wiz_T186"), lines: tx("wiz_T188", { profile: cover?.profile?.name ?? "—", travel: n(cover?.travel_cm),
        opening: n.fixed(effective.opening?.value), closing: n.fixed(effective.closing?.value), slat: n.fixed(effective.slat_time_s?.value) }).split(" · ")
        // D-20: a value not known is «—», without the unit.
        .map((line) => line.replace(/—\s*(s|cm)$/, "—")) },
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
      // M5-6: never «— cm» inside a sentence: without a known travel the variant that does not name it.
      body: pointsOnly ? tx(cover?.travel_cm > 0 ? "wiz_T235" : "wiz_T490", { ...values, travel: n(cover?.travel_cm) })
        : timesOnly ? tx(cover?.travel_cm > 0 ? "wiz_T230" : "wiz_T489", { ...values, travel: n(cover?.travel_cm) })
        : path === "C" ? tx("wiz_T197", values) : t("wiz_T022"),
      // Guided times only has no lift-off: the backend does not use the slat choice there.
      // G4-5: the answer known from the last calibration is preselected (0 s of slats: without), «with slats» otherwise.
      choice: pointsOnly || timesOnly ? null : { name: "slats", kind: "radio", label: t("wiz_T023"),
        value: (local.slats ?? cover?.effective?.slat_time_s?.value !== 0) === false ? "no" : "yes",
        // G2-3: how to tell, closed by default, right after the question.
        help: { summary: t("wiz_T456"), text: t("wiz_T457") },
        options: [{ value: "yes", label: t("wiz_T198") }, { value: "no", label: t("wiz_T199") }] },
      // M5-5: times only has no slats question and says nothing about slats.
      help: null,
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
  // M3-3: an ended session keeps the step it reached in the stepper, marked as interrupted.
  const ended = (reason) => { problemScreen(screen, ctx, reason); screen.interrupted = true; screen.phase = local.reachedPhase || screen.phase; return finish(); };
  if (status.expired || view.reason === "expired") return ended("expired");
  if (ENDED.includes(view.phase)) return ended(view.reason || "stopped");
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
  if (path === "C") return t(scope === "times_only" ? "wiz_T231" : scope === "points_only" ? "wiz_T236" : scope === "times_and_rolls" ? "wiz_T200" : "wiz_T114");
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
  // A positioning only runs the part of the travel still ahead: the full time of its direction × that share, from the
  // cover's estimated position when the run started (100 = open). Already there: a short run until the bus confirms.
  // Unknown position: the full time. The estimate is only as good as the times in use, not yet measured here.
  const toRun = (full, closing) => {
    if (!(full > 0)) return null;
    const position = ctx.runPosition;
    if (position == null) return full;
    const share = Math.min(100, Math.max(0, closing ? position : 100 - position)) / 100;
    return share === 0 ? ALREADY_THERE_SECONDS : full * share;
  };
  const closingTime = toRun(timeInUse(ctx.cover?.effective?.closing), true);
  // What was just measured, as tiles above the text: a small label, a big value, its unit smaller.
  // D-33: a time always carries one decimal, in the tiles too («23,0 s», «1,0 s»).
  const liftTile = () => view.samples?.lift == null ? null : { label: t("wiz_T039"), value: n.fixed(view.samples.lift), unit: "s",
    extra: view.readings?.gap == null ? "" : `${n(view.readings.gap)} cm` };
  const timeTile = (key, seconds) => seconds == null ? null : { label: t(key), value: n.fixed(seconds), unit: "s" };
  const topTime = toRun(view.values?.opening_time, false);
  // A run to an end stop stays a positioning until the motor stops by itself or its full time has passed; only then
  // does the screen ask to confirm the end stop.
  const positioningRun = (seconds) => !MOTOR_STOPPED(view) && seconds > 0 && (elapsed ?? 0) < seconds;
  // While a cover positions to an end stop, the user's eye may confirm it at once (the estimate comes from times not yet
  // measured): the end stop is the primary from the start (pressable once the motor runs), Stop the red link beside it.
  // The motor stopped by itself well before the estimated run (under 60 %): a wall switch or an obstacle gives the same
  // frame as the end stop, so the user is asked to look before confirming. The confirmation stays active.
  const stoppedEarly = (estimate, key) => {
    if (!MOTOR_STOPPED(view) || view.stopped_elapsed == null || !(estimate > 0) || view.stopped_elapsed >= estimate * EARLY_STOP_SHARE) return;
    screen.notices.push({ tone: "warning", result: true, text: fill(t(key), { seconds: n.fixed(view.stopped_elapsed), estimate: n(estimate, 0) }) });
  };
  // G2-9: a lift-off reading under 1 cm repeats the run. The backend clears `still_resting` as soon as the return to
  // the bottom starts, so the panel keeps the value it sent: the return (A-09) and the new lift-off briefing (A-07)
  // name it and say why; after a reload, without the value, the backend's notice stands while it lasts.
  const resting = local.lastGap != null && local.lastGap < (view.touching_cm ?? 1) && (view.lift_attempts ?? 1) > 1;
  // G3-3: a warning, worded by where the repeat came from (the value typed, or the button).
  const liftRepeated = () => ({ tone: "warning", result: true, text: !resting ? fill(t("calLiftRepeated"), view)
    : local.liftOrigin === "button" ? t("wiz_T469") : fill(t("wiz_T458"), { n: n(local.lastGap, 2) }) });
  // G2-10: after ② (or at the end of a half run) the backend waits for the actuator's stop: the screen says so, the
  // stopwatch stays at the press, and ①/② give way to the status instead of sitting there disabled.
  const stopping = (seconds) => {
    if (seconds != null) { const [label, value] = splitLabel(fill(t("wiz_T257"), { seconds: n.fixed(seconds) })); screen.stopwatch = { label, value }; }
    else screen.stopwatch = null;
    screen.actions = [{ id: "stopping", label: t("wiz_T459"), kind: "status" }];
  };
  // U-9: once the run to an end stop is over (the stop frame, or its full time and a margin gone by: a timed actuator
  // stops by itself without a frame) Stop gives way to the state, «La corsa è finita: la tapparella è ferma».
  const ranOut = (seconds) => MOTOR_STOPPED(view) || (seconds > 0 && (elapsed ?? 0) >= seconds + Math.max(2, seconds * 0.15));
  const stopOrState = (seconds) => ranOut(seconds) ? [{ id: "stopped", label: t("wiz_T498"), kind: "state" }] : [stop];
  const toEndStop = (label, running) => [{ id: "endpoint", label: t(label), kind: "primary", disabled: phase !== running }, ...whileRunning(view, stop)];
  if (phase === "review" || phase === "saving") return summaryScreen(screen, ctx, tx, n, values);
  if (step === "home") {
    screen.phase = "prep";
    if (phase === "briefing") return Object.assign(screen, { code: p("03"), title: t("wiz_T021"), body: path === "C" ? tx("wiz_T197", values) : t("wiz_T022"),
      actions: [{ id: "next", label: t("wiz_T024"), kind: "primary" }] });
    // A-05 once the positioning is over: the end stop and "It did not do what it should" can be pressed at once, the
    // red Stop stays while the motor runs. T033 opens S-01 (nothing measured yet is lost). Not on A-10: there a stop
    // discards the lift-off measurement (§8.9).
    if (phase === "closing" && !positioningRun(closingTime)) {
      Object.assign(screen, { code: p("05"), title: t("wiz_T030"), body: t(slats ? "wiz_T031" : "wiz_T501"),
        actions: [{ id: "endpoint", label: t("wiz_T032"), kind: "primary" }, { id: "misbehaved", label: t("wiz_T033"), kind: "secondary" }, ...stopOrState(closingTime)] });
      stoppedEarly(closingTime, "wiz_T440");
      return screen;
    }
    positioning("04", tx("wiz_T029", values), closingTime);
    if (["starting_close", "closing"].includes(phase)) screen.actions = toEndStop("wiz_T032", "closing");
    return screen;
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
        actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }, { id: "resting", label: t("wiz_T468"), kind: "secondary" }] });
      return screen;
    }
    const running = ["starting_open", "opening"].includes(phase);
    // N-12: while the motor runs the body says what to watch for, no longer how to start it.
    const moving = /^(starting_)?(open|clos)ing$/.test(phase);
    Object.assign(screen, { code: p("07"), title: t("wiz_T042"), body: moving ? t("wiz_T520") : path === "C" ? t("wiz_T202") : t("wiz_T043"),
      stopwatch: runWatch(t, n, view, elapsed),
      actions: [{ id: "next", label: t("wiz_T045"), kind: "primary", disabled: phase !== "briefing" },
        { id: "lift", label: t("wiz_T046"), kind: "primary", disabled: phase !== "opening" }, stop] });
    if ((resting || view.still_resting) && phase === "briefing") screen.notices.push(liftRepeated());
    if (phase === "geometry_wait_stop") stopping(view.samples?.lift);
    return screen;
  }
  if (step === "reset") {
    // Z-4: the reading is already in: the screen is about the choice (repeat the lift-off run or go on), not the reading.
    if (phase === "briefing" && view.gap_warning) return Object.assign(screen, { code: p("08"), title: t("wiz_T525"), body: t("wiz_T526"), illustration: false,
      results: [liftTile()].filter(Boolean),
      notices: [{ tone: "warning", result: true, text: fill(t("calGapWarning"), view) }],
      // G3-5: repeating is the advised way; going on with a wide gap is the outlined secondary.
      actions: [{ id: "repeat", label: t("wiz_T061"), kind: "primary" }, { id: "next", label: t("wiz_T473"), kind: "secondary" }] });
    // The same Stop rule as A-05 (only while the motor runs); no T033 here, a stop would discard the lift-off.
    if (phase === "closing" && !positioningRun(closingTime)) {
      Object.assign(screen, { code: p("10"), title: t("wiz_T053"), body: t("wiz_T054"),
        actions: [{ id: "endpoint", label: t("wiz_T032"), kind: "primary" }, ...stopOrState(closingTime)] });
      // Not on a return before a repeated reading: that one confirms itself on the stop frame (§9.53).
      if (!local.ackReadings) stoppedEarly(closingTime, "wiz_T440");
      return screen;
    }
    positioning("09", tx(path === "C" ? "wiz_T203" : "wiz_T052", values), closingTime);
    if (["starting_close", "closing"].includes(phase)) screen.actions = toEndStop("wiz_T032", "closing");
    if (phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }];
    if (resting || view.still_resting) screen.notices.push(liftRepeated());
    return screen;
  }
  // A full run the bus ended without a timely press of ②: its result is shown but not valid; only a repeat goes on.
  // D-11: not valid is drawn as such: its own title, the tiles struck through, the notice as an error, and Continue
  // shown but disabled beside Repeat.
  const invalid = (key) => local.invalidRun?.step === key ? { tone: "error", result: true, text: t(local.invalidRun.reason === "timer" ? "wiz_T445" : "wiz_T444") } : null;
  const repeatOnly = (code, title, results, note) => Object.assign(screen, { code, title, results: results.filter(Boolean),
    notices: [note], actions: [{ id: "repeat", label: t("wiz_T061"), kind: "primary" }, { id: "invalid-next", label: t("wiz_T060"), kind: "secondary", disabled: true }] });
  if (step === "opening") {
    if (phase === "reading") {
      const bad = invalid("opening");
      if (bad) return repeatOnly(p("12"), t("wiz_T502"), [slats ? liftTile() : null, { ...timeTile("wiz_T040", view.values?.opening_time), invalid: true }], bad);
      if (!local.ackAscent && slats) return Object.assign(screen, { code: p("12"), title: t("wiz_T058"), body: t("wiz_T059"),
        results: [liftTile(), timeTile("wiz_T040", view.values?.opening_time)].filter(Boolean),
        actions: [{ id: "ack:ascent", label: t("wiz_T060"), kind: "primary" }, { id: "repeat", label: t("wiz_T061"), kind: "secondary" }] });
      return Object.assign(screen, { code: p("13"), title: t("wiz_T062"), body: t("wiz_T063"),
        // Z-11: one pattern for every reading's hint: the expected value when known, the field's limits otherwise.
        field: { label: t("wiz_T064"), hint: view.saved_travel_cm != null ? tx("wiz_T527", { cm: n(view.saved_travel_cm, 0) }) : t("wiz_T066"), min: 20, max: 500, kind: "travel", value: view.saved_travel_cm ?? null },
        actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }] });
    }
    Object.assign(screen, { code: p("11"), title: slats ? t("wiz_T055") : t("wiz_T040"),
      body: t(/^(starting_)?opening$/.test(phase) ? "wiz_T521" : slats ? "wiz_T056" : "wiz_T499"),
      stopwatch: runWatch(t, n, view, elapsed),
      actions: [{ id: "next", label: t("wiz_T045"), kind: "primary", disabled: phase !== "briefing" },
        { id: "endpoint", label: t("wiz_T057"), kind: "primary", disabled: phase !== "opening" }, ...whileRunning(view, stop)] });
    if (phase === "geometry_wait_stop") stopping(view.values?.opening_time);
    return screen;
  }
  if (step === "closing") {
    Object.assign(screen, { code: p("14"), title: t("wiz_T068"),
      body: t(/^(starting_)?closing$/.test(phase) ? (slats ? "wiz_T522" : "wiz_T523") : slats ? "wiz_T069" : "wiz_T500"), stopwatch: runWatch(t, n, view, elapsed),
      actions: [{ id: "next", label: t("wiz_T045"), kind: "primary", disabled: phase !== "briefing" },
        { id: "endpoint", label: t("wiz_T070"), kind: "primary", disabled: phase !== "closing" }, ...whileRunning(view, stop)] });
    if (phase === "geometry_wait_stop") stopping(view.values?.closing_time);
    return screen;
  }
  if (step === "half_open") {
    const bad = phase === "briefing" ? invalid("closing") : null;
    if (bad) {
      repeatOnly(p("15"), t("wiz_T503"), [{ ...timeTile("wiz_T068", view.values?.closing_time), invalid: true }], bad);
      screen.phase = "descent";
      return screen;
    }
    if (phase === "briefing" && !local.ackDescent) return Object.assign(screen, { code: p("15"), phase: "descent", title: t("wiz_T071"), body: t("wiz_T072"),
      results: [timeTile("wiz_T068", view.values?.closing_time), view.travel_cm == null ? null : { label: t("wiz_T041"), value: n(view.travel_cm), unit: "cm" }].filter(Boolean),
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
      actions: phase === "briefing" ? [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop] : phase === "geometry_wait_stop"
        ? [{ id: "stopping", label: t("wiz_T459"), kind: "status" }] : [stop] });
  }
  if (step === "top" && !local.ackReadings) {
    // D-12: once the motor has stopped the run is no longer «positioning»: the stop is said in the title, with its
    // warning when it came early, and the end stop to confirm (the state instead of Stop, U-9).
    if (phase === "opening" && MOTOR_STOPPED(view)) {
      // Z-5: as A-05 after an early stop (T440), «Non ha fatto quello che doveva» is offered beside the end stop.
      Object.assign(screen, { code: p("09"), phase: "descent", title: t("wiz_T504"),
        actions: [{ id: "endpoint", label: t("wiz_T432"), kind: "primary" }, { id: "misbehaved", label: t("wiz_T033"), kind: "secondary" }, ...stopOrState(topTime)] });
      stoppedEarly(topTime, "wiz_T441");
      return screen;
    }
    // The return to the top before a repeated descent: a positioning run to confirm at the end stop.
    positioning("09", t("wiz_T086"), topTime);
    screen.phase = "descent";
    if (["starting_open", "opening"].includes(phase)) screen.actions = toEndStop("wiz_T432", "opening");
    if (phase === "opening") stoppedEarly(topTime, "wiz_T441");
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
        // V-1: each leg says the time its bar counts down from (the run to the top from where the cover is), whole
        // seconds rounded up as the time left is, so «circa 23 s» never shows «circa 24 s» left.
        { text: tx("wiz_T084", { seconds: n(Math.ceil((topTime ?? view.values?.opening_time ?? 0) - 0.001), 0) }), state: first ? "current" : "done" },
        { text: tx("wiz_T085", { seconds: n(Math.ceil(down - 0.001), 0) }), state: first ? "future" : "current" }],
      progress: waitBar(view, elapsed, first ? topTime : down) }, actions: phase === "geometry_wait_stop" ? [{ id: "stopping", label: t("wiz_T459"), kind: "status" }] : [stop] });
    // The return to the top is a positioning run: Home Assistant needs its end stop confirmed.
    if (first && ["starting_open", "opening"].includes(phase)) screen.actions = toEndStop("wiz_T432", "opening");
    if (first && phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop];
    if (!first && phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop];
    return screen;
  }
  if (step === "check") {
    // A check of the measured model (the wizard does not offer one yet): its run is stopped by Home Assistant like the
    // intermediate runs, so no elapsed time; then the tape reading, from 0.1 cm to the measured travel.
    screen.phase = "readings";
    if (phase === "reading") return Object.assign(screen, { code: p("31"), title: t("wiz_T138"), body: t("wiz_T139"),
      field: { label: t("wiz_T064"), hint: view.check?.target_cm != null ? tx("wiz_T527", { cm: n(view.check.target_cm, 0) }) : t("wiz_T491"), min: 0.1, max: view.travel_cm ?? 10000, kind: "height" },
      actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }, { id: "repeat", label: t("wiz_T033"), kind: "secondary" }] });
    positioning("30", t("wiz_T086"));
    if (phase === "briefing") screen.actions = [{ id: "next", label: t("wiz_T060"), kind: "primary" }, stop];
    return screen;
  }
  if (phase === "geometry_wait_stop") return positioning("04", "");
  return Object.assign(screen, { code: "unknown", title: t(`calPhase_${phase}`), actions: [stop] });
}

/**
 * Live `guided` session for path C, times only (G4-6): the backend's two-run protocol on our own screens and texts,
 * adapted from A-11/A-12/A-14/A-15 (never the maintainer's phase texts). The backend goes from the measured ascent
 * straight to «ready for the descent» and from the measured descent straight to the review: the result screens are
 * the panel's own (acknowledged locally). A repeat starts the times again from a closed cover (the guided session has
 * no repeat verb). The validity rule of the full runs (R8-7) applies as on A-11/A-14.
 */
function guidedScreen(screen, ctx, tx, n, values, stop) {
  const { t, view, elapsed, local = {} } = ctx;
  const phase = view.phase;
  const tile = (key, seconds) => seconds == null ? null : { label: t(key), value: n.fixed(seconds), unit: "s" };
  const bad = (key) => local.invalidRun?.step === key ? { tone: "error", result: true, text: t(local.invalidRun.reason === "timer" ? "wiz_T445" : "wiz_T444") } : null;
  const result = (code, title, body, time, key, ack) => {
    const notice = bad(key);
    // D-11: as on A-12/A-15, a result that is not valid looks it.
    return Object.assign(screen, { code, title: notice ? t(key === "opening" ? "wiz_T502" : "wiz_T503") : title, body: notice ? "" : t(body),
      results: [time].filter(Boolean).map((tile) => notice ? { ...tile, invalid: true } : tile), notices: notice ? [notice] : [],
      actions: notice ? [{ id: "restart", label: t("wiz_T061"), kind: "primary" }, { id: "invalid-next", label: t("wiz_T060"), kind: "secondary", disabled: true }]
        : [{ id: ack, label: t("wiz_T060"), kind: "primary" }, { id: "restart", label: t("wiz_T061"), kind: "secondary" }] });
  };
  if ((phase === "review" || phase === "saving") && !local.ackDescent) {
    screen.phase = "descent";
    return result("C-15", t("wiz_T071"), "wiz_T480", tile("wiz_T068", view.values?.closing_time), "closing", "ack:descent");
  }
  if (phase === "review" || phase === "saving") return summaryScreen(screen, ctx, tx, n, values);
  if (["confirm_closed", "starting_open", "opening"].includes(phase)) {
    return Object.assign(screen, { code: "C-11", phase: "ascent", title: t("wiz_T040"), body: t(phase === "confirm_closed" ? "wiz_T477" : "wiz_T521"),
      stopwatch: runWatch(t, n, view, elapsed),
      actions: [{ id: "run:open", label: t("wiz_T045"), kind: "primary", disabled: phase !== "confirm_closed" },
        { id: "endpoint", label: t("wiz_T057"), kind: "primary", disabled: phase !== "opening" }, ...whileRunning(view, stop)] });
  }
  if (phase === "confirm_open" && !local.ackAscent) {
    screen.phase = "ascent";
    return result("C-12", t("wiz_T058"), "wiz_T478", tile("wiz_T040", view.values?.opening_time), "opening", "ack:ascent");
  }
  if (["confirm_open", "starting_close", "closing"].includes(phase)) {
    return Object.assign(screen, { code: "C-14", phase: "descent", title: t("wiz_T068"), body: t(phase === "confirm_open" ? "wiz_T479" : "wiz_T522"),
      stopwatch: runWatch(t, n, view, elapsed),
      actions: [{ id: "run:close", label: t("wiz_T045"), kind: "primary", disabled: phase !== "confirm_open" },
        { id: "endpoint", label: t("wiz_T070"), kind: "primary", disabled: phase !== "closing" }, ...whileRunning(view, stop)] });
  }
  return Object.assign(screen, { code: "unknown", title: t("wiz_T027"), actions: [stop] });
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
  // D-46: a preview's box says nothing moves (path B, fine-tuning, tape readings only), so its positionings are not
  // drawn as such: what would happen live, the stages it would run, no countdown, and the state in place of Stop.
  // Y-b: the preview box already says nothing moves: no state line, but «Continua» to the reading at once.
  const still = [{ id: "skip", label: t("wiz_T006"), kind: "primary" }];
  if (view.phase === "positioning") {
    if (profile && view.step === "open_full") return Object.assign(screen, { code: "B-03", title: t("wiz_T505"),
      wait: { text: tx("wiz_T506", values), stages: [], progress: false }, actions: still });
    const stages = view.stages.map((stage, index) => ({ text: tx(stageText[stage.key], { seconds: n(stage.seconds, 0) }),
      state: index < view.stage_index ? "done" : index === view.stage_index ? "current" : "future" }));
    return Object.assign(screen, { code: profile ? "B-05" : p(readingCodes[view.step][0]), title: t("wiz_T505"),
      wait: { text: t("wiz_T507"), stages, progress: false }, actions: still });
  }
  if (view.phase === "reading") {
    if (view.step === "travel") return Object.assign(screen, { code: "B-04", title: t("wiz_T062"), body: t("wiz_T063"),
      field: { label: t("wiz_T064"), hint: t("wiz_T066"), min: 20, max: 500, kind: "travel" },
      actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }] });
    if (profile) return Object.assign(screen, { code: "B-06", title: t("wiz_T138"),
      body: tx("wiz_T509", { expected: n(view.expected_cm, 0), travel: n(view.travel_cm, 0) }),
      field: { label: t("wiz_T064"), hint: view.expected_cm != null ? tx("wiz_T527", { cm: n(view.expected_cm, 0) }) : t("wiz_T491"), min: 0, max: 10000, kind: "height" },
      actions: [{ id: "reading", label: t("wiz_T051"), kind: "primary" }, { id: "repeat", label: t("wiz_T033"), kind: "secondary" }] });
    const [, number, title] = readingCodes[view.step];
    return Object.assign(screen, { code: p(number), title: t(title), body: view.step === "check" ? t("wiz_T139") : t("wiz_T082"),
      field: { label: t("wiz_T064"), hint: view.expected_cm != null ? tx("wiz_T527", { cm: n(view.expected_cm, 0) }) : t("wiz_T491"), min: 0, max: 10000, kind: "height" },
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
  // D-32: a slat time of 0 is a cover without slats: «No», as in the list's details, not «0 s».
  // Z-1: times always with one decimal, as the stepper and the tiles.
  const format = (key, value, unit, digits) => value == null ? "—" : key === "slat" && value === 0 ? t("calTabSlatsNo")
    : `${unit === " s" ? n.fixed(value, 1) : n(value, digits)}${unit}`;
  const row = (label, key, unit, digits = 1) => {
    const before = format(key, base[key], unit, digits);
    const shown = format(key, after[key], unit, digits);
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
  // D-35: a gap under 1 cm is said so, not «about 0 cm».
  const precision = view.check ? tx(Number(view.check.gap_cm) < 1 ? "wiz_T513" : "wiz_T151", { gap: view.check.gap_cm, seconds: n(view.check.check_seconds) }) : null;
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
    // C-38 shows the values in use in grey: only the rolls change, so (D-35) they are in the table, not only under
    // «Dettagli tecnici».
    screen.table.mutedBefore = true;
    screen.table.rows = [...screen.table.rows, ...rolls];
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

/** Under a new profile's name, for a cover that followed another: what happens to that one (left alone, or kept by others). */
function followLine(t, cover) {
  const others = cover.followers?.length ?? 0, old = cover.profile.name;
  return fill(t(others === 0 ? "wiz_T436" : others === 1 ? "wiz_T438" : "wiz_T437"), { old, count: others, tab: t("profileListTitle") });
}

/** "Also save as reusable profile": on by default for a first cover, off when it already follows a profile. */
function profileBlock(ctx, tx, pathC) {
  const { t, cover, local = {} } = ctx;
  const follows = !!cover?.profile;
  const on = local.saveProfile ?? (!follows && !pathC);
  // On the cover the followed profile was measured on, updating that profile is the default, but only once the session
  // can save into an existing profile (L5a; the same condition as the "not available yet" notice): the default never
  // lands on a choice that cannot be saved. Elsewhere, and until then, a new profile.
  const source = follows && !!cover.entity_id && cover.profile.provenance?.opening?.origin_entity_id === cover.entity_id;
  const canUpdate = ctx.supports ? ctx.supports("profile_update") : true;
  const choice = on && follows ? { name: "save_choice", value: local.saveChoice || (source && canUpdate ? "update" : "new"),
    // Listed as in A-21d: update first, then a new profile (still the default choice, §9.10).
    options: [{ value: "update", label: tx("wiz_T109", { profile: cover.profile.name }),
      description: counted(t, "wiz_T110", cover.followers?.length ?? 0, { names: ctx.followerNames || "—" }) }, { value: "new", label: t("wiz_T111") }] } : null;
  const creating = on && (!follows || choice.value === "new");
  const nameValue = local.profileName ?? slug(cover?.name || "");
  // Home Assistant accepts any name of 1–64 characters; two profiles with the same name would be told apart by nothing.
  const wanted = nameValue.trim().toLocaleLowerCase();
  const nameError = !wanted ? t("wiz_T435") : (ctx.profiles || []).some((profile) => profile.name?.trim().toLocaleLowerCase() === wanted) ? t("wiz_T434") : "";
  const block = { switchLabel: t(follows ? "wiz_T439" : "wiz_T096"), on, explanation: follows ? tx("wiz_T108", { profile: cover.profile.name }) : t("wiz_T097"), choice,
    name: creating ? { label: t("wiz_T098"), value: nameValue, hint: t("wiz_T433"), error: nameError,
      line: follows ? followLine(t, cover) : tx("wiz_T101", { name: nameValue }),
      valid: !nameError } : null,
    target: !on ? "cover_only" : creating ? "profile_new" : "profile_update" };
  return block;
}

function withSupport(screen, ctx, target) {
  const supported = ctx.supports ? ctx.supports(target) : true;
  if (!supported) {
    // D-16: said at the top of the screen (seen on a phone too), and no help explaining what Save would do.
    // N-11: the notice names the way of saving that is not available and what to do instead.
    const text = target === "cover_only" ? fill(ctx.t("wiz_T518"), { switch: ctx.t(ctx.cover?.profile ? "wiz_T439" : "wiz_T096") })
      : target === "profile_update" ? fill(ctx.t("wiz_T519"), { profile: ctx.cover?.profile?.name ?? "", choice: ctx.t("wiz_T111") }) : ctx.t("wizSaveUnavailable");
    screen.notices.push({ tone: "warning", result: true, text });
    screen.saveInfo = null;
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
      // U-8: at the end of a preview nothing is lost: on B-09 and C-34 «Chiudi» is the primary, not red (A-34 keeps its
      // primary «another» and Close as red text).
      actions: path === "B" ? [{ ...close("B"), kind: "primary" }]
        : path === "C" ? [{ ...close("C"), kind: "primary" }, { id: "another", label: t("wiz_T156"), kind: "secondary" }, { id: "open-cover", label: t("wiz_T157"), kind: "secondary" }]
        : [{ id: "another", label: t("wiz_T156"), kind: "primary" }, { id: "open-cover", label: t("wiz_T157"), kind: "secondary" }, close(path)] });
  }
  if (path === "B") return Object.assign(screen, { code: "B-09", title: t("wiz_T154"),
    body: tx("wiz_T182", { ...values, profile: ctx.cover?.followProfile ?? "", travel: number(saved.travel_cm, ctx.language, 0) }),
    actions: [close("B")] });
  const body = saved.target === "profile_new" ? tx("wiz_T155", { name: saved.name ?? "" })
    : path === "C" && ctx.cover?.profile ? tx("wiz_T228", values) : tx("wizSavedCover", values);
  // A-34: the base calibration is saved; fine-tuning (path C on the same cover) is the primary next step, explained
  // by the body's second paragraph (T319).
  // A profile was created or updated: it can be given to similar covers at once (the maintainer's Assign dialog).
  const assign = ["profile_new", "profile_update"].includes(saved.target) ? [{ id: "assign-profile", label: t("wiz_T426"), kind: "secondary" }] : [];
  // A new profile left the previous one without covers: it can be deleted from the Profiles tab (never by itself).
  if (saved.target === "profile_new" && saved.orphan) screen.note = { tone: "info", text: fill(t("wiz_T431"), { old: saved.orphan, tab: t("profileListTitle") }) };
  // Z-8: the bar holds the primary and one secondary (assigning the profile just saved, or another cover); the other
  // ways on are text links under the text, so a docked bar never covers the screen.
  if (path !== "C") return Object.assign(screen, { code: "A-34", title: t("wiz_T154"), body: `${body}\n\n${t("wiz_T319")}`,
    actions: [{ id: "refine", label: t("wiz_T103"), kind: "primary" }, ...(assign.length ? assign : [{ id: "another", label: t("wiz_T156"), kind: "secondary" }])],
    links: [...(assign.length ? [{ id: "another", label: t("wiz_T156") }] : []), { id: "open-cover", label: t("wiz_T157") }, { id: "close", label: t("wiz_T158") }] });
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
    // Today's backend discards the session: say what it says, and offer to start over. Two cases say more, from what
    // the panel knows: the stop came from "It did not do what it should", or the lift-off run stopped before ②.
    const key = `calReason_${reason}`;
    // G2-10: the actuator never confirmed the stop: S-01 says it plainly and offers to start over.
    if (reason === "not_stopped") { screen.code = "S-01"; screen.title = t("wiz_T240"); }
    // D-31: the ended session's reason is about the measured value (an interval out of range…), not two presses: a
    // title that says only that it is not valid.
    if (code === "S-04") screen.title = t("wiz_T512");
    // N-15: a Stop this tab did not send came from another tab or device: said so (the maintainer's «Stop richiesto.»
    // does not say where it came from).
    screen.body = reason === "not_stopped" ? t("wiz_T460") : reason === "stopped" && ctx.local?.misbehaved ? t("wiz_T442")
      : reason === "stopped" && ctx.local && !ctx.local.stopSent ? t("wiz_T524")
      : reason === "unexpected_stop" && ctx.view?.step === "lift" ? t("wiz_T443")
        : t(key) === key ? t("calPhase_interrupted") : t(key);
    screen.actions = [{ id: "start-over", label: t("wiz_T261"), kind: "primary" }, { id: "close", label: t("wiz_T158"), kind: "secondary" }];
  }
  // A step's problem keeps the session open: Abandon stays (and asks); an ended session has nothing to abandon.
  screen.discard = step && code !== "S-06";
  return screen;
}

/**
 * A reading at half the opening or closing time: with the session's `reading_range` the hint gives the heights
 * the fit accepts (never a target) and the field refuses the others before sending; otherwise the mockup's rough
 * expectation (T083).
 */
function halfField(ctx, tx, n) {
  const { t, view, language = "en" } = ctx, span = view.reading_range;
  if (!span) return { label: t("wiz_T064"), hint: view.expected_cm != null ? tx("wiz_T527", { cm: n(view.expected_cm, 0) }) : t("wiz_T491"), min: 0.1, max: 10000, kind: "height" };
  return { label: t("wiz_T064"), hint: fill(t("wiz_T528"), readingRange(span, language)),
    min: span.min_cm - RANGE_SLACK_CM, max: span.max_cm + RANGE_SLACK_CM, kind: "height", range: true };
}

function runWatch(t, n, view, elapsed) {
  if (!MEASURED_RUN(view)) return null;
  // Stopped by itself: the stopwatch stays at the time of the stop frame ("Stopwatch: stopped at 22.2 s").
  const frozen = MOTOR_STOPPED(view) && view.stopped_elapsed != null;
  if (!frozen && elapsed == null) return null;
  // One decimal always: the value keeps its length while it counts (and when it freezes).
  const [label, value] = splitLabel(frozen ? fill(t("wiz_T257"), { seconds: n.fixed(view.stopped_elapsed) }) : fill(t("wiz_T044"), { seconds: n.fixed(elapsed) }));
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


/** Whole seconds left, never 0 while the bar is shown (sums of tenths are not exact: 11.000000001 is 11). */
function secondsLeft(seconds) { return Math.max(1, Math.ceil(seconds - 0.001)); }

/** A stop frame before this share of the estimated run is "earlier than expected" (R7-9). */
const EARLY_STOP_SHARE = 0.6;

/** A positioning to an end stop the cover already sits at: the bar runs this long, until the bus confirms the stop. */
const ALREADY_THERE_SECONDS = 2;

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
  A: { "05": ["window-closed", BEFORE], "10": ["window-closed", BEFORE], "06": ["two-runs", BEFORE], "07": ["lift-sequence", BEFORE], "08": ["lift-zoom", AFTER],
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
  // D-21: fine-tuning before its case is chosen (A-02 with it ticked, C-01): only the introduction, no count.
  const unknownCase = (screen.stepPath || path) === "C" && !(screen.stepScope ?? scope) && !refining && ["path", "current"].includes(ctx.stage);
  const phases = unknownCase ? ["intro"] : phasesFor(screen.stepPath || path, screen.stepScope ?? scope, refining);
  let current = phases.indexOf(screen.phase);
  if (refining && screen.phase === "summary") current = phases.length - 1;
  // Y-d: the end of a preview saved nothing: its summary step stays the current one, not ticked as done.
  const previewEnd = screen.phase === "done" && screen.preview;
  if (screen.phase === "done") current = previewEnd ? phases.indexOf("summary") : phases.length;
  const source = view && !view.preview ? view : null;
  const base = local.base || {};
  const values = source?.values || {}, samples = source?.samples || {}, readings = { ...(local.baseReadings || {}), ...(source?.readings || {}) };
  // D-33: times always with one decimal («5,0 s» beside «4,9 s», R6-7).
  const seconds = (value) => value == null ? "—" : `${fixed(value, language, 1)} s`, cm = (value) => value == null ? "—" : `${n(value)} cm`;
  // D-11: a time judged not valid, or discarded by its repeat and not yet measured again, is not shown as a result.
  const kept = (step, value) => local.invalidRun?.step === step || (local.discarded?.step === step && local.discarded.value === value) ? null : value;
  const slats = source ? source.slats !== false : local.slats !== false;
  const sub = {
    // The path chosen ("Ⓐ first of its type") is the introduction's sub-line, as the mockups' stepper shows it.
    intro: screen.caption ? [["", screen.caption]] : [],
    ascent: [...(slats && !(path === "C" && scope === "times_only") ? [[t("wiz_T039"), (samples.lift ?? base.lift) != null
      ? `${seconds(samples.lift ?? base.lift)} · ${(readings.gap ?? base.gap) != null ? cm(readings.gap ?? base.gap) : "—"}` : "—"]] : []),
      [t("wiz_T040"), seconds(kept("opening", values.opening_time ?? base.opening))],
      ...(path === "C" && scope === "times_only" ? [] : [[t("wiz_T041"), cm(source?.travel_cm ?? base.travel)]])],
    descent: [[t("wiz_T068"), seconds(kept("closing", values.closing_time ?? base.closing))]],
    readings: path === "B" ? [[t("wiz_T041"), cm(view?.travel_cm ?? local.fineReadings?.travel)],
      [t("wiz_T119"), (view?.check ?? local.fineReadings?.check) ? `${(view?.check ?? local.fineReadings.check).gap_cm} cm` : "—"]]
      : path === "C" && scope === "points_only" ? fineSub(t, view, cm, local.fineReadings)
        : [[t("wiz_T077"), cm(readings.half_open)], [t("wiz_T078"), cm(readings.half_close)]],
    finetune: refining ? fineSub(t, view, cm, local.fineReadings) : [],
  };
  const finetuneLabel = refining ? t("wiz_T114") : t("wiz_T013");
  screen.stepper = {
    interrupted: !!screen.interrupted,
    line: previewEnd ? t("wiz_T517") : screen.phase === "done" ? t("wiz_T153") : unknownCase ? t(PHASES.intro) : fill(t(screen.interrupted ? "wiz_T461" : "wizPhaseLine"), { phase: screen.phase === "finetune" ? t("wiz_T114") : t(PHASES[screen.phase] || "wiz_T007"),
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
    // N-15: the step's own text addresses whoever guides it («premi ②», «se hai premuto…»): a reader has the box below.
    screen.body = "";
    screen.readOnly = { status: t("wiz_T262"), text: t("wiz_T263"), take: t(status.confirmTake ? "calConfirmTakeControl" : "wiz_T264"),
      consequence: status.confirmTake ? t("wiz_T265") : null, primary: view.owner_present === false };
    // Stop stays available to every reader while something may move (L1: a safety control).
    screen.actions = MOVING(view) ? [{ id: "stop", label: t("wiz_T028"), kind: "stop" }] : [];
    screen.field = null;
  }
  // Alone in a wait, Stop is the red filled button of the mockups; beside a step's buttons it stays a red link.
  if (screen.wait && screen.actions.length === 1 && screen.actions[0].id === "stop") screen.actions[0] = { ...screen.actions[0], kind: "danger" };
  // The backend hands the cover back after a stretch without any step (600 s after a movement; heartbeats do not
  // extend it). Two minutes before, a screen that waits for the user says so, counting the minutes down.
  if (view && !view.preview && view.idle_expires_at && !status.expired && !ENDED.includes(view.phase) && !MOVING(view)) {
    const left = Date.parse(view.idle_expires_at) - (ctx.now ?? Date.now());
    if (left > 0 && left <= LEASE_WARNING_MS) screen.notices.unshift({ tone: "warning", result: true, text: fill(t("wiz_T462"), { minutes: Math.max(1, Math.ceil(left / 60000)) }) });
  }
  if (status.lost && !status.expired && view && !ENDED.includes(view.phase)) {
    // A missed heartbeat (the phone put the page aside, the connection dropped for a moment) is a calm status while the
    // panel reconnects; a lost presence for any other reason stays an error.
    screen.notices.push(status.connection === "interrupted" ? { tone: "info", text: t("wiz_T446") } : { tone: "error", text: t("calVisual_disconnected") });
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
  // G3-4: outside the field's own limits (or not a number) the field says so under itself.
  // (A reading outside the fit's range keeps its notice with the accepted range.)
  if (local.fieldError != null && screen.field && !(screen.field.range && typeof local.fieldError === "number")) {
    const value = local.fieldError, { min, max } = screen.field;
    screen.field.error = value === "nan" ? t("wiz_T472") : value > max ? fill(t("wiz_T470"), { max: n(max) })
      : value < min ? fill(t("wiz_T471"), { min: n(min) }) : null;
  }
  if (typeof local.fieldError === "number" && screen.field?.range) {
    screen.notices.push({ tone: "error", text: fill(t("profileError_reading_out_of_range"), readingRange(view.reading_range, language, local.fieldError)) });
  }
  // D-13 (decided 8 Oct): a button off while the motor starts or the backend settles after a run enables by itself.
  if (view && (/^starting_/.test(view.phase) || view.phase === "geometry_wait_stop")) for (const action of screen.actions) if (action.disabled) action.settling = true;
  // Movement, readings and Save wait for an answer, a connection and ownership; Stop never does (also a passing state).
  if (status.locked) for (const action of screen.actions) if (!["stop", "reconnect", "close", "start-over"].includes(action.id)) { if (!action.disabled) action.settling = true; action.disabled = true; }
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
