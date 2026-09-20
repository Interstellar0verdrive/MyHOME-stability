// The wizard's screens, without a browser and without a gateway.
//
// `screenModel` is a pure function of a snapshot, so the whole of what the guided
// calibration looks like can be walked here: the thirty-four examples the contract froze
// in `tests/fixtures/panel_session_examples.json` (lot L0) are one per screen the panel
// has to draw, and every one of them goes through the same function the bundle uses.
//
// Three families of assertion, and they are the three ways this screen can be wrong:
//
// * **a step with no row** - the table in `wizard/steps.ts` is held to the contract's own
//   list of sixty steps, so a step the backend gains is a test failure and not a screen
//   that silently falls back to something;
// * **a sentence the panel wrote** - every step of the measurement has to show the
//   *dialog's* words, already translated into seven languages. A title that came from the
//   panel's own block would be a 275th sentence to translate;
// * **a hole in a sentence** - a `{placeholder}` that reached the screen. The dialog fills
//   them server-side; the panel fills them itself, with the decimals SPEC §5.3 fixes, and
//   one that is not filled is visible to the user and invisible to a type checker.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { I18n } from "../src/engine/i18n";
import {
  type SessionSnapshot,
  type SessionStep,
} from "../src/engine/session-contract";
import { type HaConnection } from "../src/types/ha";
import { PHASES, STEPS } from "../src/wizard/steps";
import { phaseLine, screenModel, type WizardContext } from "../src/wizard/model";
import { placeholders, valueLine } from "../src/wizard/format";

import fixture from "../../tests/fixtures/panel_session_examples.json";
import english from "../../custom_components/myhome/translations/en.json";
import italian from "../../custom_components/myhome/translations/it.json";

type Files = typeof english;

const served = (files: Files): Record<string, unknown> => ({
  options: files.options,
  selector: files.selector,
  exceptions: files.exceptions,
  panel: files.config_panel,
});

const speaking = async (language: string, files: Files): Promise<I18n> => {
  const i18n = new I18n();
  await i18n.load(
    {
      sendMessagePromise: async () =>
        ({ language, requested: language, fallback: false, texts: served(files) }) as never,
      subscribeMessage: async () => async () => undefined,
    } as unknown as HaConnection,
    language,
  );
  return i18n;
};

const it_it = await speaking("it", italian as unknown as Files);
const en_gb = await speaking("en", english);

const scenarios = fixture.scenarios as unknown as Record<string, SessionSnapshot>;
const contract = fixture._contract as unknown as {
  steps: SessionStep[];
  reused_steps: SessionStep[];
};

/**
 * A moment `seconds` after a snapshot's movement began, on this tab's clock.
 *
 * Never an instant written down here: the fixture is regenerated from the real controller
 * (lot B3) and every `started_at` in it moves. What a test about the motor line is about
 * is the *interval*, so the interval is what it says.
 */
const secondsInto = (snapshot: SessionSnapshot, seconds: number, skewMs = 0): number =>
  Date.parse(snapshot.movement?.started_at ?? snapshot.server_time) + seconds * 1000 + skewMs;

const context = (i18n: I18n, over: Partial<WizardContext> = {}): WizardContext => ({
  i18n,
  now: Date.parse("2026-09-18T10:01:16.000+00:00"),
  skewMs: 0,
  typed: null,
  position: null,
  readOnly: false,
  showAll: false,
  showAffected: false,
  cue: true,
  selected: null,
  profiles: [],
  stepperOpen: false,
  ...over,
});

/**
 * A snapshot standing on any step at all.
 *
 * Built by taking one example that carries a movement, a form, a press and a review and
 * changing only the step, so that every one of the sixty rows can be exercised even where
 * the fixture has no example of its own. It is not a claim that the backend would ever
 * send this combination - it is the smallest thing that lets the table be walked whole.
 */
const standingOn = (step: SessionStep): SessionSnapshot => {
  const base = structuredClone(scenarios.running_open_lift);
  const measuring = structuredClone(scenarios.awaiting_reading_measure_descent);
  const stopping = structuredClone(scenarios.running_lift_stop);
  const reviewing = structuredClone(scenarios.review_precise);
  return {
    ...base,
    step,
    actions: base.actions,
    form: measuring.form,
    reading: measuring.reading,
    measured: stopping.measured,
    review: reviewing.review,
    check: reviewing.check,
    placeholders: { ...base.placeholders, ...measuring.placeholders, ...reviewing.placeholders },
  };
};

/** A number already written out, made safe to look for with a regular expression. */
const escapeForMatch = (written: string): string => written.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * The thorough calibration's check, built from path B's scenario.
 *
 * The fixture has no walk that stops on `verify_result` at the thorough level - the
 * thorough scenarios are reviews - and since lot W3 the two checks are drawn by different
 * code: path B's is the panel's own screen, the thorough one is still the dialog's. This
 * is the second of the two, which is what `path` and the three null fields make it.
 */
const theThoroughCheck = (): SessionSnapshot => {
  const snapshot = structuredClone(scenarios.checking_verify_result_offers_c);
  return {
    ...snapshot,
    path: "path_c",
    check: { ...snapshot.check!, threshold_cm: null, profile_level: null, profile_check_cm: null },
  } as unknown as SessionSnapshot;
};

/** Every string a screen shows, however deep in the model it is. */
const sentences = (model: ReturnType<typeof screenModel>): string[] => {
  const out: string[] = [model.title, model.body ?? ""];
  out.push(model.primary?.label ?? "");
  for (const one of model.secondary ?? []) {
    out.push(one.label);
  }
  for (const one of model.options ?? []) {
    out.push(one.title, one.meta ?? "");
  }
  if (model.field) {
    out.push(model.field.label, model.field.hint ?? "", model.field.error ?? "");
  }
  if (model.press) {
    out.push(model.press.instruction ?? "", model.press.motor ?? "", model.press.note ?? "");
  }
  if (model.progress) {
    out.push(model.progress.text ?? "", model.progress.eta ?? "");
  }
  for (const one of model.summary?.rows ?? []) {
    out.push(one.label, one.after, one.before ?? "");
  }
  out.push(...(model.summary?.lines ?? []));
  out.push(model.note?.text ?? "", model.readOnly?.text ?? "", model.readOnly?.label ?? "");
  return out.filter((one) => one !== "");
};

describe("the table of steps", () => {
  it("has one row for every step the contract can produce", () => {
    assert.deepEqual(Object.keys(STEPS).sort(), [...contract.steps].sort());
    assert.equal(contract.steps.length, 60);
  });

  it("gives every row one of the eight templates and a phase, problems apart", () => {
    const eight = new Set([
      "lettura",
      "scelta",
      "pos",
      "click",
      "controllo",
      "metro",
      "riepilogo",
      "esito",
    ]);
    for (const [step, row] of Object.entries(STEPS)) {
      assert.ok(eight.has(row.template), `${step}: ${row.template}`);
      const named = row.phase === null || PHASES.includes(row.phase);
      assert.ok(named, `${step}: ${String(row.phase)}`);
      // A problem can interrupt any stage and the snapshot does not say which one, so a
      // header naming a phase there would be naming the wrong one.
      assert.equal(row.phase === null, step.startsWith("problem_"), step);
    }
  });

  it("takes the words of every reused step from the dialog, in both languages", () => {
    for (const step of contract.reused_steps) {
      const row = STEPS[step];
      assert.ok(row, step);
      assert.ok(!row.own, `${step} is drawn with the panel's own words`);
      for (const i18n of [it_it, en_gb]) {
        const model = screenModel(standingOn(step), context(i18n));
        const source = row.display ?? step;
        const ph = placeholders(standingOn(step).placeholders, i18n);
        assert.equal(model.title, i18n.t(`options.step.${source}.title`, ph), step);
        assert.notEqual(model.title, "", step);
      }
    }
  });

  it("gives the steps the dialog has no words for the panel's own", () => {
    // The four reviews, the one problem the dialog cannot produce, and the positioning
    // screens: everything else the dialog says already.
    const ours = Object.entries(STEPS)
      .filter(([, row]) => row.own)
      .map(([step]) => step)
      .sort();
    assert.deepEqual(ours, [
      "problem_interrupted",
      "summary_basic",
      "summary_correction",
      "summary_precise",
      "summary_short",
    ]);
    const model = screenModel(standingOn("problem_interrupted"), context(it_it));
    assert.equal(model.title, it_it.t("panel.wizard.problem.interrupted.title"));
  });
});

describe("every example the contract froze", () => {
  it("becomes a screen, in Italian and in English", () => {
    for (const [name, snapshot] of Object.entries(scenarios)) {
      for (const i18n of [it_it, en_gb]) {
        const model = screenModel(snapshot, context(i18n));
        assert.notEqual(model.title.trim(), "", name);
        assert.ok(model.model, name);
      }
    }
    assert.equal(Object.keys(scenarios).length, 39);
  });

  it("leaves no placeholder unfilled anywhere on it", () => {
    for (const [name, snapshot] of Object.entries(scenarios)) {
      for (const i18n of [it_it, en_gb]) {
        const model = screenModel(snapshot, context(i18n));
        for (const sentence of sentences(model)) {
          assert.doesNotMatch(sentence, /\{[A-Za-z0-9_]+\}/, `${name}: ${sentence}`);
        }
      }
    }
  });

  it("never asks for a key nobody wrote", () => {
    for (const [name, snapshot] of Object.entries(scenarios)) {
      for (const i18n of [it_it, en_gb]) {
        for (const sentence of sentences(screenModel(snapshot, context(i18n)))) {
          assert.doesNotMatch(sentence, /^(panel|options|selector)\./, `${name}: ${sentence}`);
        }
      }
    }
  });
});

describe("the words of every screen", () => {
  it("never says the shutter's name under a header that already says it", () => {
    // Live finding 4: the dialog opens nearly every screen with "**Tapparella**: <name>",
    // because it has nowhere else to say which shutter is being measured. The panel's
    // header says it above every screen, so the line is the name twice.
    for (const [name, snapshot] of Object.entries(scenarios)) {
      for (const i18n of [it_it, en_gb]) {
        const model = screenModel(snapshot, context(i18n));
        const cover = snapshot.cover?.name ?? "";
        const first = (model.body ?? "").split(/\n{2,}/)[0]?.trim() ?? "";
        assert.notEqual(first, `**Tapparella**: ${cover}`, name);
        assert.notEqual(first, `**Cover**: ${cover}`, name);
      }
    }
  });

  it("keeps the line where it says something the header does not", () => {
    // "**Tapparella**: {cover} - **scarto**: {deviation} cm" is not the name twice. The
    // thorough calibration's own check is where that screen is still the dialog's: path
    // B's has been the panel's own since lot W3.
    const model = screenModel(theThoroughCheck(), context(it_it));
    assert.match(model.body ?? "", /^\*\*Tapparella\*\*:/);
  });

  it("gives every step of the measurement something to read, not a title and buttons", () => {
    // Live finding 17: the descent's "the motor is starting" screen had no drawing and no
    // prose at all - the instruction was blanked on the way through and the descent is the
    // one run with no illustration. A step is a screen somebody has to act on: it always
    // says what to do.
    for (const [name, snapshot] of Object.entries(scenarios)) {
      const model = screenModel(snapshot, context(en_gb));
      const said = [
        model.body ?? "",
        model.press?.instruction ?? "",
        model.progress?.text ?? "",
        model.field?.label ?? "",
        ...(model.options ?? []).map((one) => one.title),
        ...(model.lines ?? []),
        ...(model.summary?.lines ?? []),
      ]
        .join(" ")
        .trim();
      assert.notEqual(said, "", `${name} is a title and some buttons`);
    }
  });

  it("says what the press is for while the motor is still starting", () => {
    const model = screenModel(scenarios.running_open_start, context(en_gb));
    assert.match(model.body ?? "", /bottom edge leaves the base/);
    // ...and the operative column says what the motor is doing, which is the other half.
    assert.match(model.press?.instruction ?? "", /starting upwards/);
  });
});

describe("the numbers", () => {
  it("writes each placeholder with the decimals SPEC §5.3 fixes for it", () => {
    const model = screenModel(scenarios.awaiting_reading_measure_descent, context(it_it));
    // Expected and tolerance point at a place on a wall: no decimals.
    assert.match(model.field?.hint ?? "", /86/);
    assert.doesNotMatch(model.field?.hint ?? "", /86,25|86\.25/);
    assert.match(model.field?.hint ?? "", /15/);
    // …and the percentage in the title is a whole number too.
    assert.match(model.title, /50/);
  });

  it("writes them in the reader's own language", () => {
    // The deviation is read out of the fixture rather than written in here, because the
    // fixture is regenerated from the real controller (lot B3) and the number moves. What
    // this is about is the separator: one decimal, and a comma where Italian writes one.
    const snapshot = scenarios.checking_verify_result_offers_c;
    const deviation = snapshot.check?.gap_cm ?? 0;
    const italian_ = screenModel(snapshot, context(it_it));
    const english_ = screenModel(snapshot, context(en_gb));
    // Built with the same formatter the panel uses: `toFixed` and `Intl` disagree on an
    // exact half (`(1.05).toFixed(1)` is "1.0" where `Intl` gives "1,1"), and a check on
    // the decimal separator must not fall over a rounding rule it is not about.
    assert.match(italian_.body ?? "", new RegExp(escapeForMatch(it_it.number(deviation, 1))));
    assert.match(english_.body ?? "", new RegExp(escapeForMatch(en_gb.number(deviation, 1))));
  });

  it("writes a value of the model with its unit, and a missing one as a dash", () => {
    assert.equal(valueLine("travel_cm", 195, en_gb), "195 cm");
    assert.equal(valueLine("opening_time_s", 22.6, en_gb), "22.6 s");
    assert.equal(valueLine("opening_roll", 2.02, en_gb), "2.02");
    assert.equal(valueLine("travel_cm", null, en_gb), "—");
  });
});

describe("the screen of a press", () => {
  it("says the motor is starting, and offers nothing to press yet", () => {
    const model = screenModel(scenarios.running_open_start, context(en_gb));
    assert.equal(model.model, "click");
    assert.equal(model.press?.state, "starting");
    assert.equal(model.primary?.disabled, true);
    // The words are the step that is coming, not the one the snapshot stands on.
    assert.equal(model.title, en_gb.t("options.step.open_lift.title"));
  });

  it("puts the dialog's own press label on the big button, numbering and all", () => {
    const model = screenModel(scenarios.running_open_lift, context(it_it));
    assert.equal(model.press?.state, "moving");
    assert.equal(
      model.primary?.label,
      it_it.t("options.step.open_lift.menu_options.lifted_off"),
    );
    assert.match(model.primary?.label ?? "", /^1\)/);
    // The step's own two, and the panel's way of stopping the shutter under them.
    assert.deepEqual(
      (model.secondary ?? []).map((one) => one.action),
      ["act:repeat_step", "act:not_right", "stop"],
    );
  });

  it("counts the seconds off the server's clock and not off this one", () => {
    const snapshot = scenarios.running_open_lift;
    // Five and a half seconds after `movement.started_at`, with this tab's clock two
    // minutes fast: the line has to read 5,5 and not 125,5.
    const skewMs = 120_000;
    const model = screenModel(
      snapshot,
      context(it_it, { now: secondsInto(snapshot, 5.5, skewMs), skewMs }),
    );
    assert.equal(
      model.press?.motor,
      it_it.t("panel.wizard.motor.moving", { seconds: it_it.number(5.5, 1) }),
    );
  });

  it("shows the press it registered, and the shutter's own estimate beside it", () => {
    const snapshot = scenarios.running_lift_stop;
    const model = screenModel(snapshot, context(it_it, { position: 3 }));
    assert.equal(model.press?.state, "registered");
    assert.equal(model.primary?.disabled, true);
    // The instant of the press against the instant the run began: both of them the
    // server's, both of them read out of this snapshot.
    const at =
      (Date.parse(snapshot.measured.lift?.pressed_at ?? "") -
        Date.parse(snapshot.movement?.started_at ?? "")) /
      1000;
    assert.equal(
      model.press?.note,
      it_it.t("panel.wizard.press.registered_note", { seconds: it_it.number(at, 1) }),
    );
    assert.equal(
      model.press?.position,
      it_it.t("panel.wizard.motor.position", { percent: it_it.number(3, 0) }),
    );
  });

  it("carries the switch for the signal on the brief that starts a run, and nowhere else", () => {
    assert.ok(screenModel(scenarios.briefing_open_brief, context(en_gb)).toggle);
    assert.equal(screenModel(scenarios.running_open_lift, context(en_gb)).toggle, undefined);
  });
});

describe("the screen of a positioning run", () => {
  it("is a bar, a sentence and a way to stop the shutter", () => {
    const snapshot = scenarios.positioning_home_closed;
    // Half way through whatever the movement was planned to take, so the bar is half full
    // however long the regenerated fixture says that is.
    const halfway = (snapshot.movement?.planned_s ?? 0) / 2;
    const model = screenModel(snapshot, context(it_it, { now: secondsInto(snapshot, halfway) }));
    assert.equal(model.model, "pos");
    assert.equal(
      model.progress?.text,
      it_it.t("options.progress.homing_closed", {
        cover: String(snapshot.placeholders.cover ?? ""),
      }),
    );
    assert.ok((model.progress?.fraction ?? 0) > 0.45 && (model.progress?.fraction ?? 0) < 0.55);
    assert.equal(model.secondary?.[0]?.label, it_it.t("panel.wizard.action.stop"));
    // Nothing to press: the step advances when the movement ends, never when the bar fills.
    assert.equal(model.primary, undefined);
  });
});

describe("the review", () => {
  it("shows three rows and keeps the model behind a press", () => {
    const shut = screenModel(scenarios.review_basic, context(en_gb));
    assert.equal(shut.summary?.rows.length, 3);
    assert.equal(shut.summary?.more, undefined);
    assert.equal(shut.summary?.code, undefined);
    const open = screenModel(scenarios.review_basic, context(en_gb, { showAll: true }));
    assert.equal(open.summary?.more?.length, 3);
    assert.match(open.summary?.code ?? "", /cover_profiles/);
  });

  it("offers the exits the session offers, the first one big", () => {
    const model = screenModel(scenarios.review_basic, context(en_gb));
    assert.match(model.primary?.action ?? "", /^save:profile$/);
    assert.ok((model.secondary ?? []).some((one) => one.action === "save:cover_only"));
    // …and the thorough calibration, which is an action of the session and not an exit.
    assert.ok((model.secondary ?? []).some((one) => one.action === "act:refine"));
  });

  it("says the profile exists and who else follows it, before anything is written", () => {
    const model = screenModel(scenarios.review_basic_profile_exists, context(en_gb));
    assert.ok((model.summary?.lines ?? []).some((line) => line.includes("already exists")));
    assert.equal(model.summary?.affected, undefined);
    const open = screenModel(
      scenarios.review_basic_profile_exists,
      context(en_gb, { showAffected: true }),
    );
    assert.equal(open.summary?.affected?.length, 1);
    assert.equal(open.summary?.affected?.[0]?.title, "Landing Shutter");
  });

  it("shows what changes although this calibration never measured it", () => {
    // The fixture has no example with a side effect in it and cannot have one while
    // staying consistent with the overview it shares numbers with (lot L0, R7), so the
    // state is built here - which is where that handoff asked for it.
    const snapshot = structuredClone(scenarios.review_basic);
    snapshot.review!.side_effects = [{ key: "stop_latency_s", before: 0.35, after: 0.1 }];
    const model = screenModel(snapshot, context(en_gb, { showAll: true }));
    assert.equal(model.summary?.sideEffects?.rows.length, 1);
    assert.equal(model.summary?.sideEffects?.rows[0]?.label, en_gb.t("panel.wizard.review.key.stop_latency"));
    assert.equal(model.summary?.sideEffects?.rows[0]?.after, "0.10 s");
    // …and it is behind the same press as the coefficients.
    assert.equal(screenModel(snapshot, context(en_gb)).summary?.sideEffects, undefined);
  });

  it("gives the offer to go on a border, because it is a way forward", () => {
    // Live finding 20: one primary and two secondaries. "Continue with the thorough
    // calibration" was drawn as a third kind of button, which reads as a way out.
    const model = screenModel(scenarios.review_basic, context(en_gb));
    assert.equal(model.primary?.kind, "primary");
    const going_on = (model.secondary ?? []).find((one) => one.action === "act:refine");
    assert.equal(going_on?.kind, "secondary");
    assert.ok((model.secondary ?? []).every((one) => one.kind === "secondary"));
  });

  it("says a value that did not move once, and strikes nothing through", () => {
    // Live finding 23: an ascent measured again at the same 14,3 s was printed twice with
    // a line through the first, which is a difference the reader goes looking for.
    // The fixture is the real thing: this calibration moved the ascent and left the travel
    // and the descent exactly where they were.
    const model = screenModel(scenarios.review_basic, context(en_gb));
    const rows = model.summary?.rows ?? [];
    const same = rows.filter((one) => one.unchanged === true);
    assert.equal(same.length, 2);
    assert.ok(same.every((one) => one.before === undefined));
    const moved = rows.filter((one) => one.unchanged !== true);
    assert.equal(moved.length, 1);
    assert.equal(moved[0]?.before, valueLine("opening_time_s", 25, en_gb));
  });

  it("says each unit once, beside the number", () => {
    // Live finding 24: "Curtain travel (cm) … 110 cm". The label's bracket is there for a
    // form field, which has nowhere else to say the unit; here the number does.
    const model = screenModel(scenarios.review_basic, context(en_gb));
    for (const row of model.summary?.rows ?? []) {
      assert.doesNotMatch(row.label, /\((cm|s)\)$/, row.label);
    }
    const travel = model.summary?.rows.find((one) => /cm$/.test(one.after));
    assert.ok(travel, "a row in centimetres");
  });

  it("opens and shuts the technical details with the same words", () => {
    // Live finding 25: "Show every value, roll coefficients included" became "Hide the
    // roll coefficients", which reads as two controls - and what it hides was never only
    // the coefficients, because the snippet for the file goes with them.
    const shut = screenModel(scenarios.review_basic, context(en_gb));
    const open = screenModel(scenarios.review_basic, context(en_gb, { showAll: true }));
    const one = shut.summary?.disclose?.[0];
    const other = open.summary?.disclose?.[0];
    assert.equal(one?.label, en_gb.t("panel.wizard.review.details_show"));
    assert.equal(other?.label, en_gb.t("panel.wizard.review.details_hide"));
    assert.equal(one?.label.replace(/^Show/, ""), other?.label.replace(/^Hide/, ""));
    assert.equal(one?.note, en_gb.t("panel.wizard.review.details_note"));
  });

  it("says whether the accuracy was checked, and where", () => {
    const checked = screenModel(scenarios.review_precise, context(en_gb));
    assert.ok((checked.summary?.lines ?? []).some((line) => line.includes("40%")));
    const not = screenModel(scenarios.review_basic, context(en_gb));
    assert.ok((not.summary?.lines ?? []).some((line) => line.includes("not been checked")));
  });
});

describe("the outcomes", () => {
  it("has a screen for each of the six reasons a session ends", () => {
    const reasons = [
      ["saved_profile", "saved"],
      ["ended_cancelled", "cancelled"],
      ["ended_expired", "expired"],
      ["ended_unloaded", "expired"],
      ["ended_left", "cancelled"],
      ["ended_cover_gone", "problem"],
    ] as const;
    for (const [name, face] of reasons) {
      const model = screenModel(scenarios[name], context(en_gb));
      assert.equal(model.model, "esito", name);
      assert.equal(model.outcome, face, name);
      assert.notEqual(model.title.trim(), "", name);
      assert.ok(model.primary, name);
    }
  });

  it("says what was saved, what was made of it, and that it is already in use", () => {
    // Live finding 26: the sentence used to be "«nome» is saved and already in use: it
    // follows the profile «nome» (Inherited from profile «nome»)", which names the profile
    // three times and answers nothing. Three things in the order somebody asks them, and
    // no origin phrase inside a sentence that is not about where values come from.
    const model = screenModel(scenarios.saved_profile, context(en_gb));
    assert.match(model.body ?? "", /hallway_shutter/);
    assert.doesNotMatch(model.body ?? "", /Inherited/);
    assert.match(model.body ?? "", /created/);
    assert.equal(model.summary?.rows.length, 3);
    // ...and how a shutter like it is calibrated, under the sentence rather than in it.
    assert.deepEqual(model.lines, [en_gb.t("panel.wizard.outcome.saved.reuse")]);
  });

  it("says the values are the shutter's own when they were saved for it alone", () => {
    // `outcome.profile` is the profile the shutter follows and not the profile that was
    // written: a save for this shutter only, made on a shutter that has a profile
    // assigned, carries one. What tells the two apart is the origin - "measured" is the
    // shutter having values of its own - which is what the sentence is chosen on.
    const model = screenModel(scenarios.saved_cover_only, context(en_gb));
    assert.match(model.body ?? "", /Hallway Shutter/);
    assert.doesNotMatch(model.body ?? "", /tall/);
    assert.equal(model.lines, undefined);
  });
});

describe("the outside world", () => {
  it("says the shutter was brought back before anything was timed", () => {
    const model = screenModel(scenarios.briefing_open_brief_rehomed, context(en_gb));
    assert.equal(model.note?.tone, "info");
    assert.equal(model.note?.text, en_gb.t("panel.wizard.external.rehomed"));
  });

  it("says a reading no longer matches, and says it loudly", () => {
    const model = screenModel(scenarios.awaiting_reading_measure_descent_stale, context(en_gb));
    assert.equal(model.note?.tone, "error");
    // The action the step borrows from `tape_result`, because a form step has no labels.
    assert.equal(
      model.secondary?.[0]?.label,
      en_gb.t("options.step.tape_result.menu_options.repeat_tape"),
    );
  });

  it("mentions a movement that cost the step nothing, without alarming anybody", () => {
    const model = screenModel(scenarios.briefing_lift_check_external, context(en_gb));
    assert.equal(model.note?.tone, "info");
    assert.equal(model.note?.text, en_gb.t("panel.wizard.external.moved"));
  });
});

describe("stopping the shutter", () => {
  it("offers it on every screen where something of this session is running", () => {
    // `stop` is a verb of the contract and not one of the step's `menu_options`, so it is
    // never in `actions`: the screen adds it (SPEC §5.4, decision 10). The three timed
    // runs are the moments the shutter is really going somewhere.
    for (const name of ["running_open_start", "running_open_lift", "positioning_home_closed"]) {
      const model = screenModel(scenarios[name], context(en_gb));
      const stop = (model.secondary ?? []).find((one) => one.action === "stop");
      assert.ok(stop, name);
      assert.equal(stop?.label, en_gb.t("panel.wizard.action.stop"), name);
      // Last, under whatever the step itself offers: it is the way out of the step.
      assert.equal(model.secondary?.[model.secondary.length - 1]?.action, "stop", name);
    }
  });

  it("does not offer it where nothing of this session is moving", () => {
    for (const name of ["briefing_open_brief", "briefing_lift_check", "review_basic"]) {
      const model = screenModel(scenarios[name], context(en_gb));
      assert.equal(
        (model.secondary ?? []).some((one) => one.action === "stop"),
        false,
        name,
      );
    }
  });

  it("marks every step that moves, and only those", () => {
    // The flag and the shutter have to say the same thing: a step with a movement of the
    // session's own is a step with a way to interrupt it.
    for (const [name, snapshot] of Object.entries(scenarios)) {
      const step = snapshot.step;
      if (!step || !STEPS[step]) {
        continue;
      }
      const moving = snapshot.movement !== null;
      const offered = (screenModel(snapshot, context(en_gb)).secondary ?? []).some(
        (one) => one.action === "stop",
      );
      assert.equal(offered, moving && Boolean(STEPS[step].stoppable), name);
    }
  });
});

describe("a session somebody else is driving", () => {
  it("shows the same screen with nothing on it that acts", () => {
    const driving = screenModel(scenarios.owned_by_other, context(en_gb));
    const watching = screenModel(scenarios.owned_by_other, context(en_gb, { readOnly: true }));
    assert.ok((driving.options ?? []).length > 0);
    assert.equal(watching.options, undefined);
    assert.equal(watching.primary, undefined);
    assert.equal(watching.field, undefined);
    assert.equal(watching.title, driving.title);
    assert.equal(watching.readOnly?.label, en_gb.t("panel.wizard.owner.take"));
  });

  it("takes the field away from a reading, and the switch from a brief", () => {
    // One state exercised one branch of `decorate`. These are the other three: the field
    // of a tape reading, the switch for the signal at the start, and the two disclosures
    // of the review - each of which is a control that would otherwise be pressable on a
    // calibration somebody else is holding the tape for.
    const reading = screenModel(
      scenarios.awaiting_reading_measure_descent,
      context(en_gb, { readOnly: true }),
    );
    assert.equal(reading.field, undefined);
    assert.equal(reading.primary, undefined);
    assert.ok(reading.readOnly);

    const brief = screenModel(scenarios.briefing_open_brief, context(en_gb, { readOnly: true }));
    assert.equal(brief.toggle, undefined);
    assert.equal(brief.secondary, undefined);
    assert.ok(brief.readOnly);

    const review = screenModel(
      scenarios.review_basic_profile_exists,
      context(en_gb, { readOnly: true, showAll: true }),
    );
    assert.equal(review.summary?.disclose, undefined);
    assert.equal(review.primary, undefined);
    assert.ok(review.readOnly);
    // …and what it says is still there to read: the rows and the lines are not controls.
    assert.equal(review.summary?.rows.length, 3);
    assert.ok((review.summary?.lines ?? []).length > 0);
  });

  it("leaves the running screens showing what they were showing", () => {
    const watching = screenModel(scenarios.running_open_lift, context(en_gb, { readOnly: true }));
    // The motor card stays: somebody standing in front of the shutter has to be able to
    // see where it has got to, whoever is driving.
    assert.equal(watching.press?.state, "moving");
    assert.equal(watching.secondary, undefined);
    assert.equal(watching.primary, undefined);
  });
});

describe("the errors of a form", () => {
  it("puts the flow's own reason under the field", () => {
    const model = screenModel(scenarios.awaiting_reading_measure_descent_error, context(it_it));
    assert.equal(model.field?.error, it_it.t("options.error.above_the_travel"));
    assert.equal(model.field?.inputMode, "decimal");
  });

  it("gives a profile name a letter keyboard and the smaller field", () => {
    const model = screenModel(scenarios.briefing_profile_name, context(en_gb));
    assert.equal(model.field?.inputMode, "text");
    assert.equal(model.field?.big, false);
    assert.equal(model.field?.unit, undefined);
  });

  it("makes a choice of profiles out of the names the form offers", () => {
    // Nothing of the fixture is written into this test: the profile it describes is
    // whichever name the form offers that is not the file, and the option that is marked
    // is whichever one the form suggests. It has to survive the regeneration of the
    // fixture from the real controller (lot B3), which moves both.
    const snapshot = scenarios.armed_path_b_profile_choice;
    const choices = snapshot.form?.choices ?? [];
    const named = choices.find((one) => one !== "from_the_file") ?? "";
    assert.notEqual(named, "");
    const model = screenModel(
      snapshot,
      context(en_gb, {
        profiles: [
          {
            name: named,
            source: "store",
            editable: true,
            values: {},
            reference_height: 195,
            measured_on: "00:03:50:aa:bb:cc-2-81",
            measured_on_name: "Hallway Shutter",
            measured_at: null,
            followers: [],
            followers_from_file: [],
            missing: false,
          },
        ],
      }),
    );
    // One option per choice, in the order the form gives them - each of them a selection
    // and not a verb, because a choice is made with "Continue" (live finding 3).
    assert.equal(model.options?.length, choices.length);
    assert.deepEqual(
      (model.options ?? []).map((one) => one.action),
      choices.map((one) => `choose:pick:${one}`),
    );
    const marked = (model.options ?? []).filter((one) => one.current);
    assert.equal(marked.length, 1);
    assert.equal(marked[0]?.action, `choose:pick:${String(snapshot.form?.suggested)}`);
    // ...and the big button is what would send it.
    assert.equal(model.primary?.action, `pick:${String(snapshot.form?.suggested)}`);
    assert.equal(model.primary?.label, en_gb.t("panel.common.action.continue"));
    // The file is named by one of the origin phrases, which exist in all eight languages;
    // a profile is named by itself and carries its reference travel beside it.
    const file = (model.options ?? []).find((one) => one.action === "choose:pick:from_the_file");
    assert.equal(file?.title, en_gb.origin("from_the_file", null));
    const profile = (model.options ?? []).find((one) => one.action === `choose:pick:${named}`);
    assert.equal(profile?.title, named);
    assert.match(profile?.meta ?? "", new RegExp(en_gb.number(195, 0)));
    assert.match(profile?.meta ?? "", /Hallway Shutter/);
  });

  it("highlights the scope the panel's own button meant, and waits to be told to go", () => {
    const model = screenModel(scenarios.armed_refine_scope_intent, context(en_gb));
    const chosen = (model.options ?? []).filter((one) => one.current);
    assert.equal(chosen.length, 1);
    assert.equal(chosen[0]?.action, "choose:act:points_only");
    // Selected, not chosen: it is the big button that sends it, and until it is pressed
    // nothing has been decided.
    assert.equal(model.primary?.action, "act:points_only");
  });

  it("starts the three routes on (A), which is the one the text says to take in doubt", () => {
    // The design pre-selects the first, and live finding 5 asks the text to say so: a
    // reader who does not know which route is theirs presses Continue and gets (A).
    const model = screenModel(scenarios.armed_path, context(en_gb));
    const chosen = (model.options ?? []).filter((one) => one.current);
    assert.equal(chosen.length, 1);
    assert.equal(chosen[0]?.action, "choose:act:path_a");
    assert.equal(model.primary?.action, "act:path_a");
    assert.equal(model.primary?.disabled, false);
  });

  it("makes a choice with two gestures and never with one", () => {
    // Every option of a `scelta` selects and nothing more. A `controllo` - "what does the
    // shutter look like?" - is the other thing, and answers at the tap.
    for (const [name, snapshot] of Object.entries(scenarios)) {
      const model = screenModel(snapshot, context(en_gb));
      const step = snapshot.step;
      const template = step ? STEPS[step]?.template : undefined;
      if (template !== "scelta") {
        continue;
      }
      assert.ok(
        (model.options ?? []).every((one) => one.action.startsWith("choose:")),
        `${name}: an option that acts`,
      );
      assert.equal(model.primary?.label, en_gb.t("panel.common.action.continue"), name);
    }
  });
});

describe("the check of a verification", () => {
  it("says what the tape read and what the model had predicted", () => {
    // The thorough calibration's check, which is still the dialog's: the model predicted
    // a place, the tape found another, and the two numbers are what the gap is made of.
    const snapshot = theThoroughCheck();
    const check = snapshot.check;
    assert.ok(check);
    const model = screenModel(snapshot, context(en_gb));
    const lines = model.lines ?? [];
    assert.equal(lines.length, 1);
    assert.match(lines[0] ?? "", new RegExp(escapeForMatch(en_gb.number(check.measured_cm, 1))));
    assert.match(lines[0] ?? "", new RegExp(escapeForMatch(en_gb.number(check.predicted_cm, 1))));
    // …and the review says it its own way, with the accuracy line, not with these.
    assert.equal(screenModel(scenarios.review_precise, context(en_gb)).lines, undefined);
  });

  it("gives the verdict before the offer, on path B", () => {
    // Live finding 32: the screen printed the two numbers and then "Above 4 cm it is
    // worth measuring this shutter on its own", which was read as "middling" by the one
    // person who had measured the shutter. What decided is a comparison the panel has, so
    // the panel makes it and puts it first - both ways round.
    const out = scenarios.checking_verify_result_offers_c;
    const gap = out.check?.gap_cm ?? 0;
    const threshold = out.check?.threshold_cm ?? 0;
    assert.ok(gap > threshold);
    const beyond = screenModel(out, context(en_gb));
    assert.equal(beyond.title, en_gb.t("panel.wizard.check.half.beyond.title"));
    // The gap opens the body, and the offer comes after it, in its own paragraph.
    assert.match(beyond.body ?? "", new RegExp(`^\\*\\*${escapeForMatch(en_gb.number(gap, 1))}`));
    assert.ok((beyond.body ?? "").indexOf("\n\n") > 0);
    // The two numbers are still said, and they are said once: the separate lines the
    // screen used to carry are gone, not repeated under the words.
    assert.match(beyond.body ?? "", new RegExp(escapeForMatch(en_gb.number(out.check!.predicted_cm, 1))));
    assert.match(beyond.body ?? "", new RegExp(escapeForMatch(en_gb.number(out.check!.measured_cm, 1))));
    assert.equal(beyond.lines, undefined);
    // ...and the three of them add up as printed. The verdict is a subtraction the reader
    // is invited to check, so a "76" rounded off beside a "79.8" and a gap of "4.3" would
    // be three numbers that argue with each other on one line.
    const printed = (beyond.body ?? "").match(/[0-9]+(?:\.[0-9])?/g) ?? [];
    const numbers = printed.map(Number);
    assert.ok(
      numbers.some((one, i) => numbers.some((other, j) =>
        i !== j && Math.abs(Math.abs(other - one) - gap) < 0.05)),
      `nothing in ${printed.join(", ")} differs by the gap of ${gap}`,
    );

    const within = scenarios.checking_verify_result_within;
    assert.ok((within.check?.gap_cm ?? 0) <= (within.check?.threshold_cm ?? 0));
    const passed = screenModel(within, context(en_gb));
    assert.equal(passed.title, en_gb.t("panel.wizard.check.half.within.title"));
    assert.notEqual(passed.title, beyond.title);
    assert.equal(passed.lines, undefined);
  });

  it("promises half the travel on the screens that lead up to it, on path B", () => {
    // What the tape should read is half the curtain travel, and it is the same number on
    // the offer, under the field and in the verdict - or the check would be asking the
    // user to trust three different promises about one movement.
    const half = en_gb.number((scenarios.briefing_verify_offer.measured?.travel_cm ?? 0) / 2, 0);
    assert.equal(half, "76");
    for (const name of ["briefing_verify_offer", "awaiting_reading_measure_verify"] as const) {
      const model = screenModel(scenarios[name], context(en_gb));
      assert.match(model.body ?? "", new RegExp(escapeForMatch(half)), name);
      assert.doesNotMatch(model.body ?? "", /Configur/, name);
    }
    // The drawing of the tape against the shutter is the dialog's and is kept.
    assert.ok(screenModel(scenarios.awaiting_reading_measure_verify, context(en_gb)).image);
  });

  it("tells the review how close it came without naming a percentage, on path B", () => {
    // The review's ordinary line is "within N cm at P% of the descent". Path B's check
    // was aimed at half the travel and got there in whatever fraction of the run the
    // model needed, which is not a number anybody wants read out.
    const base = structuredClone(scenarios.review_short);
    const checked: SessionSnapshot = {
      ...base,
      review: { ...base.review!, accuracy_cm: 1.2, check_fraction: 0.5820290651319239 },
    } as unknown as SessionSnapshot;
    const lines = screenModel(checked, context(en_gb)).summary?.lines ?? [];
    assert.equal(
      lines[0],
      en_gb.t("panel.wizard.check.half.reviewed", { accuracy: en_gb.number(1.2, 1) }),
    );
    assert.doesNotMatch(lines[0] ?? "", /58|%/);
    // The thorough calibration's own check keeps the sentence with the percentage in it.
    const thorough: SessionSnapshot = { ...checked, path: "path_c" } as unknown as SessionSnapshot;
    assert.match((screenModel(thorough, context(en_gb)).summary?.lines ?? [])[0] ?? "", /58%/);
  });

  it("offers a path among the ways forward without making it the big button", () => {
    const model = screenModel(scenarios.checking_verify_result_offers_c, context(en_gb));
    // `actions` on `verify_result` can begin with `path_c`, which is a *route* and not an
    // ordinary way on (lot B4, §7). The step is drawn as a set of equal answers, so
    // nothing is promoted by its position and the correction can never become the button
    // somebody presses meaning "that's right, go on".
    assert.equal(model.model, "controllo");
    assert.equal(model.primary, undefined);
    const actions = (model.options ?? []).map((one) => one.action);
    assert.deepEqual(actions, (scenarios.checking_verify_result_offers_c.actions ?? []).map(
      (one) => `act:${one}`,
    ));
  });

  it("says a check with nothing behind it instead of printing nought centimetres", () => {
    // `gap_cm: null` means the profile went out from under the session: there was nothing
    // to compare the reading with. The snapshot still carries `deviation: 0` because the
    // dialog's sentence has to substitute something, and a screen that printed "0.0 cm"
    // there would be telling somebody their shutter is perfect (lot B4, §7).
    const original = scenarios.checking_verify_result_offers_c;
    const snapshot: SessionSnapshot = {
      ...structuredClone(original),
      check: { ...structuredClone(original.check!), gap_cm: null, threshold_cm: null },
      placeholders: { ...original.placeholders, deviation: 0 },
    } as unknown as SessionSnapshot;
    const model = screenModel(snapshot, context(en_gb));
    assert.equal(model.title, en_gb.t("panel.wizard.check.no_reference.title"));
    assert.doesNotMatch(model.body ?? "", /0\.0/);
    assert.equal(model.lines, undefined);
    // …and the answers are still there, because the reading was not thrown away.
    assert.ok((model.options ?? []).length > 0);
  });
});

describe("the header's phase line", () => {
  it("names the phase and where it falls", () => {
    assert.equal(
      phaseLine(scenarios.running_open_lift, en_gb),
      en_gb.t("panel.screen.phase", { phase: en_gb.t("panel.wizard.phase.ascent"), index: 3, count: 6 }),
    );
  });

  it("says nothing for a session that is over, or for none at all", () => {
    assert.equal(phaseLine(scenarios.ended_cancelled, en_gb), null);
    assert.equal(phaseLine(null, en_gb), null);
    assert.equal(phaseLine(scenarios.problem_no_echo, en_gb), null);
  });
});

describe("what it refuses to draw", () => {
  it("throws on a snapshot with no shutter in it, so that the card can be shown", () => {
    const broken = { ...scenarios.running_open_lift, cover: null } as unknown as SessionSnapshot;
    assert.throws(() => screenModel(broken, context(en_gb)), /shutter/);
  });

  it("throws on a step it was never told about", () => {
    const strange = { ...scenarios.running_open_lift, step: "open_sesame" } as unknown as SessionSnapshot;
    assert.throws(() => screenModel(strange, context(en_gb)), /open_sesame/);
  });
});
