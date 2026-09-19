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
  profiles: [],
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
    assert.equal(Object.keys(scenarios).length, 34);
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
    assert.match(italian_.body ?? "", new RegExp(deviation.toFixed(1).replace(".", ",")));
    assert.match(english_.body ?? "", new RegExp(deviation.toFixed(1).replace(".", "\\.")));
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
    assert.equal(model.secondary?.length, 2);
  });

  it("counts the seconds off the server's clock and not off this one", () => {
    const snapshot = scenarios.running_open_lift;
    // Five and a half seconds after `movement.started_at`, with this tab's clock two
    // minutes fast: the line has to read 5,5 and not 125,5.
    const fast = Date.parse("2026-09-18T10:01:16.100+00:00") + 120_000;
    const model = screenModel(
      snapshot,
      context(it_it, { now: fast, skewMs: 120_000 }),
    );
    assert.match(model.press?.motor ?? "", /5,5/);
  });

  it("shows the press it registered, and the shutter's own estimate beside it", () => {
    const model = screenModel(scenarios.running_lift_stop, context(it_it, { position: 3 }));
    assert.equal(model.press?.state, "registered");
    assert.equal(model.primary?.disabled, true);
    assert.match(model.press?.note ?? "", /4,8/);
    assert.equal(model.press?.position, "3 %");
  });

  it("carries the switch for the signal on the brief that starts a run, and nowhere else", () => {
    assert.ok(screenModel(scenarios.briefing_open_brief, context(en_gb)).toggle);
    assert.equal(screenModel(scenarios.running_open_lift, context(en_gb)).toggle, undefined);
  });
});

describe("the screen of a positioning run", () => {
  it("is a bar, a sentence and a way to stop the shutter", () => {
    const model = screenModel(
      scenarios.positioning_home_closed,
      context(it_it, { now: Date.parse("2026-09-18T10:00:31.850+00:00") }),
    );
    assert.equal(model.model, "pos");
    assert.equal(model.progress?.text, it_it.t("options.progress.homing_closed", { cover: "Hallway Shutter" }));
    assert.ok((model.progress?.fraction ?? 0) > 0.4 && (model.progress?.fraction ?? 0) < 0.6);
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

  it("names the profile and where the values came from, when it was saved", () => {
    const model = screenModel(scenarios.saved_profile, context(en_gb));
    assert.match(model.body ?? "", /hallway_shutter/);
    assert.match(model.body ?? "", /Inherited/);
    assert.equal(model.summary?.rows.length, 3);
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
    const model = screenModel(scenarios.armed_path_b_profile_choice, context(en_gb, {
      profiles: [
        {
          name: "tall",
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
    }));
    const snapshot = scenarios.armed_path_b_profile_choice;
    const choices = snapshot.form?.choices ?? [];
    assert.equal(model.options?.length, choices.length);
    // One option per choice, in the order the form gives them, and the one the form
    // suggests is the one marked - read off the snapshot, because the fixture is
    // regenerated from the real controller (lot B3) and the suggestion moves.
    const marked = (model.options ?? []).filter((one) => one.current);
    assert.equal(marked.length, 1);
    assert.equal(marked[0]?.action, `pick:${String(snapshot.form?.suggested)}`);
    const file = (model.options ?? []).find((one) => one.action === "pick:from_the_file");
    assert.equal(file?.title, en_gb.origin("from_the_file", null));
    const tall = (model.options ?? []).find((one) => one.action === "pick:tall");
    assert.equal(tall?.title, "tall");
    assert.match(tall?.meta ?? "", /195/);
    assert.match(tall?.meta ?? "", /Hallway Shutter/);
  });

  it("highlights the scope the panel's own button meant, without choosing it", () => {
    const model = screenModel(scenarios.armed_refine_scope_intent, context(en_gb));
    const chosen = (model.options ?? []).filter((one) => one.current);
    assert.equal(chosen.length, 1);
    assert.equal(chosen[0]?.action, "act:points_only");
  });
});

describe("the check of a verification", () => {
  it("says what the tape read and what the model had predicted", () => {
    const snapshot = scenarios.checking_verify_result_offers_c;
    const check = snapshot.check;
    assert.ok(check);
    const model = screenModel(snapshot, context(en_gb));
    const lines = model.lines ?? [];
    assert.ok(lines.length >= 1);
    assert.match(lines[0] ?? "", new RegExp(check.measured_cm.toFixed(1).replace(".", "\\.")));
    assert.match(lines[0] ?? "", new RegExp(check.predicted_cm.toFixed(1).replace(".", "\\.")));
  });

  it("says what the offer to correct this shutter rests on, on path B", () => {
    const snapshot = scenarios.checking_verify_result_offers_c;
    // Only path B carries a threshold; everywhere else the second line is absent.
    assert.notEqual(snapshot.check?.threshold_cm, null);
    const lines = screenModel(snapshot, context(en_gb)).lines ?? [];
    assert.equal(lines.length, 2);
    assert.match(lines[1] ?? "", /profile/);
    // Path A checks the same way and has no threshold to offer a correction against: the
    // second line is absent rather than empty.
    const alone: SessionSnapshot = {
      ...structuredClone(snapshot),
      check: { ...structuredClone(snapshot.check!), threshold_cm: null, profile_check_cm: null },
    } as unknown as SessionSnapshot;
    assert.equal((screenModel(alone, context(en_gb)).lines ?? []).length, 1);
    // …and the review says it its own way, with the accuracy line, not with these.
    assert.equal(screenModel(scenarios.review_precise, context(en_gb)).lines, undefined);
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
