// The choice of shutter, without a browser and without a gateway.
//
// `coverPickerModel` is the screen `#/calibrate` shows when there is no session, and it is
// a pure function of the overview - which is the whole reason it is testable here. Three
// things are worth holding:
//
// * **the list is the overview's, in the overview's order** - this screen neither filters
//   nor re-sorts a list the server has already narrowed and the user has already arranged;
// * **every row says the same second line the overview says** - one wording for "Cucina ·
//   corsa 195 cm", out of sentences that already exist in seven languages;
// * **an option carries an identifier and never an instruction** - the action is
//   `cover:<unique_id>`, which is what keeps the choice of a shutter a thing the user
//   pressed rather than a thing an address said.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { COVER, coverOf, coverPickerModel } from "../src/components/cover-picker";
import { I18n } from "../src/engine/i18n";
import { type CoverRow } from "../src/engine/ws";
import { type HaConnection } from "../src/types/ha";

import overview from "../../tests/fixtures/panel_overview_example.json";
import english from "../../custom_components/myhome/translations/en.json";
import italian from "../../custom_components/myhome/translations/it.json";

type Files = typeof english;

const speaking = async (language: string, files: Files): Promise<I18n> => {
  const i18n = new I18n();
  await i18n.load(
    {
      sendMessagePromise: async () =>
        ({
          language,
          requested: language,
          fallback: false,
          texts: {
            options: files.options,
            selector: files.selector,
            exceptions: files.exceptions,
            panel: files.config_panel,
          },
        }) as never,
      subscribeMessage: async () => async () => undefined,
    } as unknown as HaConnection,
    language,
  );
  return i18n;
};

const en_gb = await speaking("en", english);
const it_it = await speaking("it", italian as unknown as Files);

const covers = overview.covers as unknown as CoverRow[];

describe("the choice of shutter", () => {
  it("offers every shutter the overview carries, in the overview's own order", () => {
    const model = coverPickerModel(en_gb, covers);
    assert.equal(model.model, "scelta");
    assert.deepEqual(
      (model.options ?? []).map((option) => option.title),
      covers.map((cover) => cover.name),
    );
  });

  it("names a shutter by its identifier and never by anything else", () => {
    const model = coverPickerModel(en_gb, covers);
    for (const [index, option] of (model.options ?? []).entries()) {
      assert.equal(option.action, `${COVER}${covers[index].unique_id}`);
      assert.equal(coverOf(option.action), covers[index].unique_id);
    }
    // Every other token of the wizard has to be left alone by this one: an `act:` read as
    // a shutter would open a session on a name that is a verb.
    assert.equal(coverOf("act:path_a"), null);
    assert.equal(coverOf("submit"), null);
  });

  it("says the room and the travel the way the overview says them", () => {
    const model = coverPickerModel(it_it, covers);
    const first = covers[0];
    const meta = (model.options ?? [])[0].meta ?? "";
    assert.ok(meta.includes(first.area ?? ""), meta);
    assert.ok(
      first.height === null
        ? meta.includes("non indicata")
        : meta.includes(it_it.number(first.height, 0)),
      meta,
    );
  });

  it("carries the origin as a chip, in the short form the rows use", () => {
    const inherited = { ...covers[0], origin: "inherited", profile: "tall" };
    const measured = { ...covers[0], origin: "measured", profile: null };
    const model = coverPickerModel(en_gb, [inherited, measured]);
    assert.equal((model.options ?? [])[0].chip, en_gb.t("panel.overview.cover.origin_inherited"));
    assert.equal((model.options ?? [])[1].chip, en_gb.origin("measured", null));
  });

  it("leaves no placeholder unfilled in either language", () => {
    for (const i18n of [en_gb, it_it]) {
      const model = coverPickerModel(i18n, covers);
      const said = [
        model.title,
        model.body ?? "",
        ...(model.options ?? []).flatMap((option) => [option.title, option.meta ?? "", option.chip ?? ""]),
        ...(model.secondary ?? []).map((action) => action.label),
      ].join(" ");
      assert.equal(/\{[a-z_]+\}/.test(said), false, said);
    }
  });

  it("has a way out on it, because nobody has to be on this screen", () => {
    const model = coverPickerModel(en_gb, covers);
    assert.equal((model.secondary ?? []).length, 1);
    assert.equal((model.secondary ?? [])[0].action, "close");
  });

  it("is a screen even when the gateway has nothing on it", () => {
    const model = coverPickerModel(en_gb, []);
    assert.deepEqual(model.options, []);
    assert.notEqual(model.title, "");
  });
});
