// The sentences: what the server said, what the file beside the bundle says, and the key.
//
// The order of those three is the whole of this module's behaviour, and getting it wrong
// is invisible until a translator changes a word: a stand-in that shadowed the served
// sentence would mean the panel spoke English on an Italian installation and nobody could
// tell why.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { I18n } from "../src/engine/i18n";
import { type HaConnection } from "../src/types/ha";

const served = (texts: Record<string, unknown>, language = "it"): HaConnection =>
  ({
    sendMessagePromise: async () =>
      ({ language, requested: language, fallback: false, texts }) as never,
    subscribeMessage: async () => async () => undefined,
  }) as HaConnection;

const load = async (texts: Record<string, unknown>, language = "it"): Promise<I18n> => {
  const i18n = new I18n();
  await i18n.load(served(texts, language), language);
  return i18n;
};

describe("looking a sentence up", () => {
  it("prefers the server's words to the offline stand-in", async () => {
    const i18n = await load({ panel: { overview: { title: "Profili e tapparelle" } } });
    assert.equal(i18n.t("panel.overview.title"), "Profili e tapparelle");
  });

  it("falls back to the English stand-in for a key the answer does not carry", async () => {
    const i18n = await load({ panel: {} });
    assert.equal(i18n.t("panel.overview.title"), "Profiles and covers");
  });

  it("renders a key nothing knows as itself, which is what makes it look like a bug", async () => {
    const i18n = await load({});
    assert.equal(i18n.t("panel.nothing.at.all"), "panel.nothing.at.all");
  });

  it("does not mistake a branch of the tree for a sentence", async () => {
    const i18n = await load({ panel: { overview: { group: {} } } });
    assert.equal(i18n.t("panel.overview.group"), "panel.overview.group");
  });

  it("has not answered until it has", async () => {
    const blank = new I18n();
    assert.equal(blank.loaded, false);
    assert.equal(blank.language, "en");
    const i18n = await load({}, "it");
    assert.equal(i18n.loaded, true);
    assert.equal(i18n.language, "it");
  });
});

describe("placeholders", () => {
  it("substitutes by name and not by position", async () => {
    const i18n = await load({ panel: { x: "{b} then {a}" } });
    assert.equal(i18n.t("panel.x", { a: "one", b: "two" }), "two then one");
  });

  it("substitutes every occurrence of the same name", async () => {
    const i18n = await load({ panel: { x: "{a} and {a}" } });
    assert.equal(i18n.t("panel.x", { a: "one" }), "one and one");
  });

  it("takes a number as well as a string", async () => {
    const i18n = await load({ panel: { x: "{count} covers" } });
    assert.equal(i18n.t("panel.x", { count: 12 }), "12 covers");
  });

  it("leaves a placeholder nobody passed exactly as it is", async () => {
    const i18n = await load({ panel: { x: "{a} and {b}" } });
    assert.equal(i18n.t("panel.x", { a: "one" }), "one and {b}");
  });

  it("does not let a substituted value start a second substitution", async () => {
    // A shutter really can be called "{profile}". The sentence is scanned once and what
    // each placeholder is replaced with is never looked at again, so what goes in is text
    // and stays text.
    const i18n = await load({ panel: { x: "{cover} follows {profile}" } });
    assert.equal(
      i18n.t("panel.x", { cover: "{profile}", profile: "tall" }),
      "{profile} follows tall",
    );
  });

  it("does not let a value spell a replacement pattern either", async () => {
    // The other half of the same promise, and the one a refactor would break without
    // noticing: `String.prototype.replace` reads `$&`, `$\`` and `$1` in a *string*
    // replacement, so a name containing them would come out as the sentence around it
    // rather than as itself. A function replacement does not, and that is why it is one.
    const i18n = await load({ panel: { x: "Moving {cover} now" } });
    for (const name of ["$&", "$'", "$`", "$1", "$$", "$&$&"]) {
      assert.equal(i18n.t("panel.x", { cover: name }), `Moving ${name} now`, name);
    }
  });

  it("is not fooled by a brace a translator typed round something else", async () => {
    const i18n = await load({ panel: { x: "{{cover}} and { cover } and {co-ver}" } });
    assert.equal(
      i18n.t("panel.x", { cover: "Camera" }),
      "{Camera} and { cover } and {co-ver}",
    );
  });

  it("takes nothing off the prototype, whatever a sentence asks for", async () => {
    const i18n = await load({ panel: { x: "{toString} {constructor} {__proto__}" } });
    assert.equal(i18n.t("panel.x", {}), "{toString} {constructor} {__proto__}");
  });
});

describe("the words the panel is forbidden to keep its own copy of", () => {
  it("reads a refusal out of Home Assistant's own exceptions block", async () => {
    const i18n = await load({
      exceptions: { busy_calibrating: { message: 'Una calibrazione sta usando "{cover}".' } },
    });
    assert.equal(
      i18n.refusal("busy_calibrating", { cover: "Camera" }),
      'Una calibrazione sta usando "Camera".',
    );
  });

  it("says it could not read the gateway when there is no key at all", async () => {
    const i18n = await load({ panel: { error: { not_found: "Non si legge." } } });
    assert.equal(i18n.refusal(null), "Non si legge.");
    assert.equal(i18n.refusal("no_such_key"), "Non si legge.");
  });

  it("reads an origin out of the selector block the guided flow already has", async () => {
    const i18n = await load({
      selector: { calibration_origin: { options: { inherited: 'Ereditata dal profilo "{profile}"' } } },
    });
    assert.equal(i18n.origin("inherited", "tall"), 'Ereditata dal profilo "tall"');
    // A profile that is not there is an empty name and never the word "null".
    assert.equal(i18n.origin("inherited", null), 'Ereditata dal profilo ""');
  });
});

describe("numbers and dates, in the language that was served", () => {
  it("formats a number with the decimals the value deserves", async () => {
    const i18n = await load({}, "it");
    assert.equal(i18n.number(21.74, 1), "21,7");
    assert.equal(i18n.number(150, 0), "150");
    const english = await load({}, "en");
    assert.equal(english.number(21.74, 1), "21.7");
  });

  it("hands back an unreadable instant unchanged rather than an Invalid Date", async () => {
    const i18n = await load({}, "en");
    assert.equal(i18n.date("not a date"), "not a date");
    assert.match(i18n.date("2026-09-04T10:00:00+00:00"), /2026/);
  });
});
