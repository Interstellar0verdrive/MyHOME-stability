// The note in front of the advanced parameters of a hand edit.
//
// Both cards offer the slat time and the two roll coefficients for correction by hand, and
// both put a note in front of the first of them: not at the top of the form, where it
// would make the two run times (and a profile's reference travel) look as dangerous as the
// model's own parameters. What is asserted is exactly that placement, on the template the
// two views really render, in edit mode - and its absence from every other mode.
//
// **No DOM.** Lit's Node build brings a minimal `HTMLElement` and `customElements`, enough
// to construct the two elements; an element that is never connected never renders on its
// own, so `render()` is called by hand and its `TemplateResult` read with `lit-text.ts` -
// the markup the view wrote, with every substituted string in order. The labels come out
// as their translation keys, because no texts answer has been served, which is what makes
// them easy to find.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import overviewExample from "../../tests/fixtures/panel_overview_example.json";
import { FALLBACK_TEXTS } from "../src/i18n/keys";
import type { PanelState } from "../src/engine/store";
import type { CoverKeyRow, CoverRow, Overview } from "../src/engine/ws";
import { DETAIL_KEYS, MyHomeCoverDetail } from "../src/views/cover-detail";
import { MyHomeProfileCard } from "../src/views/profile-card";
import { read } from "./lit-text";

const OVERVIEW = overviewExample as unknown as Overview;
const TITLE = FALLBACK_TEXTS["panel.common.advanced.title"];
const BODY = FALLBACK_TEXTS["panel.common.advanced.body"];
const NOTE = "data-advanced-note";

/** What a view wrote, as one string: the markup, with every substitution as `{{…}}`. */
const rendered = (element: MyHomeCoverDetail | MyHomeProfileCard): string =>
  read((element as unknown as { render: () => unknown }).render()).skeleton;

/** Where a substituted string first appears in the markup - and it has to appear. */
const at = (markup: string, text: string): number => {
  const index = markup.indexOf(`{{${text}}}`);
  assert.notEqual(index, -1, `${text} is not on the screen`);
  return index;
};

const keysOf = (cover: CoverRow): CoverKeyRow[] =>
  DETAIL_KEYS.map((key) => ({
    key,
    value: cover.values[key],
    origin: cover.has_own.includes(key) ? "own" : "profile",
    own: cover.has_own.includes(key),
    inherited_value: cover.values[key],
    inherited_origin: "inherited",
    profile_value: cover.values[key],
    file_value: null,
    default_value: null,
  }));

const coverDetail = (mode: PanelState["detail"]["mode"]): MyHomeCoverDetail => {
  const element = new MyHomeCoverDetail();
  const cover = OVERVIEW.covers[0];
  element.state = {
    ...element.state,
    overview: OVERVIEW,
    detail: {
      ...element.state.detail,
      for: cover.unique_id,
      mode,
      answer: {
        entry_id: OVERVIEW.entry_id,
        cover,
        keys: keysOf(cover),
        forget: { falls_back_to: "defaults", profile: null, travel_stays: false },
      },
    },
  };
  return element;
};

const profileCard = (mode: PanelState["profile"]["mode"]): MyHomeProfileCard => {
  const element = new MyHomeProfileCard();
  const profile = OVERVIEW.profiles.find((row) => row.name === "tall");
  assert.ok(profile, "the example has no profile called tall");
  element.state = {
    ...element.state,
    overview: OVERVIEW,
    profile: {
      ...element.state.profile,
      for: profile.name,
      mode,
      form: Object.fromEntries(
        Object.entries({ reference_height: profile.reference_height, ...profile.values }).map(
          ([key, value]) => [key, String(value)],
        ),
      ),
    },
  };
  return element;
};

describe("the advanced note of the cover's hand edit", () => {
  const markup = rendered(coverDetail("edit"));

  it("is drawn once, with its title and its sentence", () => {
    assert.equal(markup.split(NOTE).length - 1, 1);
    assert.ok(TITLE && BODY, "the English stand-ins are missing");
    at(markup, TITLE);
    at(markup, BODY);
  });

  it("sits right in front of the slat time, after the two run times", () => {
    const note = markup.indexOf(NOTE);
    const slat = at(markup, "options.step.calibration_edit.data.slat_time");
    assert.ok(at(markup, "options.step.calibration_edit.data.opening_time") < note);
    assert.ok(at(markup, "options.step.calibration_edit.data.closing_time") < note);
    assert.ok(note < slat);
    // Nothing else is drawn between the note and the field it introduces.
    assert.doesNotMatch(markup.slice(note, slat), /<input/);
    assert.ok(slat < at(markup, "options.step.calibration_edit.data.opening_roll"));
    assert.ok(slat < at(markup, "options.step.calibration_edit.data.closing_roll"));
  });

  it("is a named note and not the form's own intro", () => {
    assert.match(markup, /class="caution"\s+role="note"\s+aria-labelledby="advanced-note-title"/);
    assert.match(markup, /<strong id="advanced-note-title">\{\{Advanced parameters\}\}<\/strong>/);
    // The intro is still the plain warning box, and still at the top.
    assert.ok(markup.indexOf('class="warn"') < markup.indexOf(NOTE));
  });

  for (const mode of ["view", "travel", "correct", "remove"] as const) {
    it(`is not drawn in the ${mode} mode`, () => {
      assert.doesNotMatch(rendered(coverDetail(mode)), new RegExp(NOTE));
    });
  }
});

describe("the advanced note of the profile's hand edit", () => {
  const markup = rendered(profileCard("edit"));

  it("is drawn once, with its title and its sentence", () => {
    assert.equal(markup.split(NOTE).length - 1, 1);
    at(markup, TITLE);
    at(markup, BODY);
  });

  it("sits right in front of the slat time, after the travel and the two run times", () => {
    const note = markup.indexOf(NOTE);
    const slat = at(markup, "options.step.profile_edit.data.slat_time");
    assert.ok(at(markup, FALLBACK_TEXTS["panel.profile.reference_travel"]) < note);
    assert.ok(at(markup, "options.step.profile_edit.data.opening_time") < note);
    assert.ok(at(markup, "options.step.profile_edit.data.closing_time") < note);
    assert.ok(note < slat);
    assert.doesNotMatch(markup.slice(note, slat), /<input/);
    assert.ok(slat < at(markup, "options.step.profile_edit.data.opening_roll"));
    assert.ok(slat < at(markup, "options.step.profile_edit.data.closing_roll"));
  });

  for (const mode of ["view", "rename", "delete"] as const) {
    it(`is not drawn in the ${mode} mode`, () => {
      assert.doesNotMatch(rendered(profileCard(mode)), new RegExp(NOTE));
    });
  }
});
