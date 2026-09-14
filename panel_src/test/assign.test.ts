// The pending model: what a drag, a tap and a keystroke all end up doing.
//
// Every function here is pure, and every one of them decides something the user then sees
// as a number on a shutter. The batch shape is the one the contract fixes (§9.1-§9.3), and
// the assertions below are written against that document rather than against the code.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  appendedToGroup,
  assignItems,
  currentAssignment,
  effectiveProfile,
  movedTo,
  needsTravel,
  orderedCovers,
  parseTravel,
  routeEnd,
  routeLabel,
  travelProblem,
  withPending,
} from "../src/engine/assign";
import { I18n } from "../src/engine/i18n";
import { type PendingChange } from "../src/engine/store";
import { type HaConnection } from "../src/types/ha";
import { type CoverRow, type Overview } from "../src/engine/ws";

const cover = (unique_id: string, extra: Partial<CoverRow> = {}): CoverRow => ({
  unique_id,
  entity_id: `cover.${unique_id}`,
  name: unique_id,
  area_id: null,
  area: null,
  height: 150,
  profile: null,
  profile_from_file: false,
  profile_missing: false,
  origin: "defaults",
  source: "yaml",
  values: {},
  has_own: [],
  level: null,
  verify_note: null,
  measured_at: null,
  calibrating: false,
  order_index: 0,
  ...extra,
});

const overview = (covers: CoverRow[]): Overview => ({
  entries: [],
  entry_id: "01ENTRY",
  measuring: null,
  profiles: [],
  covers,
  order: covers.map((row) => row.unique_id),
  no_basic_covers: false,
});

describe("the pending list", () => {
  it("records one change per shutter, however many times it is moved", () => {
    const row = cover("a", { profile: "tall" });
    const first = withPending([], row, "short");
    const second = withPending(first.pending, row, null);
    assert.equal(second.pending.length, 1);
    assert.deepEqual(second.pending[0], { cover: "a", to: null });
    assert.equal(second.withdrawn, false);
  });

  it("withdraws the change when the shutter is sent back where it already is", () => {
    const row = cover("a", { profile: "tall" });
    const there = withPending([], row, "short");
    const back = withPending(there.pending, row, "tall");
    assert.deepEqual(back.pending, []);
    assert.equal(back.withdrawn, true);
  });

  it("treats an unassigned shutter's home as 'no profile' and not as a change", () => {
    const row = cover("a");
    const back = withPending([{ cover: "a", to: "tall" }], row, null);
    assert.deepEqual(back.pending, []);
    assert.equal(back.withdrawn, true);
  });

  it("draws a shutter in the group it is heading for", () => {
    const row = cover("a", { profile: "tall" });
    assert.equal(effectiveProfile(row, []), "tall");
    assert.equal(effectiveProfile(row, [{ cover: "a", to: null }]), null);
    assert.equal(effectiveProfile(cover("b"), []), null);
  });

  it("knows which shutter still needs a travel typed", () => {
    const change: PendingChange = { cover: "a", to: "tall" };
    assert.equal(needsTravel(cover("a", { height: null }), change), true);
    assert.equal(needsTravel(cover("a", { height: 150 }), change), false);
    assert.equal(needsTravel(cover("a", { height: null }), { cover: "a", to: null }), false);
  });
});

describe("the order", () => {
  const order = ["a", "b", "c", "d"];

  it("puts a row before the one it was dropped on", () => {
    assert.deepEqual(movedTo(order, "d", { beforeId: "b", afterId: null }), ["a", "d", "b", "c"]);
  });

  it("puts a row after the one it was dropped past", () => {
    assert.deepEqual(movedTo(order, "a", { beforeId: null, afterId: "c" }), ["b", "c", "a", "d"]);
  });

  it("appends when the drop landed on nothing in particular", () => {
    assert.deepEqual(movedTo(order, "a", { beforeId: null, afterId: null }), ["b", "c", "d", "a"]);
  });

  it("appends when the row it was dropped against is not in the list any more", () => {
    assert.deepEqual(movedTo(order, "a", { beforeId: "gone", afterId: null }), ["b", "c", "d", "a"]);
  });

  it("appends a tapped shutter after the last member of the group it was sent to", () => {
    // The rule "a tap appends at the end" has to be written into the list once a drag has
    // made one, because a batch carrying an order carries the whole gateway's.
    assert.deepEqual(appendedToGroup(order, "a", ["b", "c"]), ["b", "c", "a", "d"]);
  });

  it("appends a tapped shutter to the end of everything when its new group is empty", () => {
    assert.deepEqual(appendedToGroup(order, "a", []), ["b", "c", "d", "a"]);
  });

  it("ignores the shutter itself when it is already the last of its new group", () => {
    assert.deepEqual(appendedToGroup(order, "c", ["b", "c"]), ["a", "b", "c", "d"]);
  });

  it("falls back to the server's order when the user has dragged nothing", () => {
    const model = overview([
      cover("a", { order_index: 2 }),
      cover("b", { order_index: 0 }),
      cover("c", { order_index: 1 }),
    ]);
    assert.deepEqual(
      orderedCovers(model, null).map((row) => row.unique_id),
      ["b", "c", "a"],
    );
  });

  it("drops a shutter the gateway no longer has and keeps one it has just gained", () => {
    const model = overview([cover("a"), cover("b"), cover("new")]);
    assert.deepEqual(
      orderedCovers(model, ["gone", "b", "a", "b"]).map((row) => row.unique_id),
      ["b", "a", "new"],
    );
  });
});

describe("the batch, as the contract wants it", () => {
  it("sends the profile and nothing else where no travel was typed", () => {
    assert.deepEqual(assignItems([{ cover: "a", to: "tall" }], {}, [cover("a")]), [
      { cover_unique_id: "a", profile: "tall" },
    ]);
  });

  it("sends a travel only where the user typed one, and reads a comma as a point", () => {
    assert.deepEqual(assignItems([{ cover: "a", to: "tall" }], { a: "145,5" }, [cover("a")]), [
      { cover_unique_id: "a", profile: "tall", height: 145.5 },
    ]);
  });

  it("omits an unusable travel rather than sending a null the server would refuse", () => {
    assert.deepEqual(assignItems([{ cover: "a", to: "tall" }], { a: "  " }, [cover("a")]), [
      { cover_unique_id: "a", profile: "tall" },
    ]);
  });

  it("sends null for a shutter taken out of every profile", () => {
    assert.deepEqual(assignItems([{ cover: "a", to: null }], {}, [cover("a")]), [
      { cover_unique_id: "a", profile: null },
    ]);
  });

  it("drops a pending change naming a shutter the model no longer has", () => {
    // The row is not on the screen - `orderedCovers` filters it out - so it must not be
    // in the batch either. One item the server cannot place refuses the whole batch
    // (`_refuse_the_batch`), and the sentence would name a shutter the user cannot see
    // and cannot withdraw.
    assert.deepEqual(
      assignItems(
        [
          { cover: "a", to: "tall" },
          { cover: "gone", to: "tall" },
        ],
        {},
        [cover("a")],
      ),
      [{ cover_unique_id: "a", profile: "tall" }],
    );
  });

  it("is an empty batch when every pending change has stopped naming anything", () => {
    // Sent as it is, rather than held back: the write still carries the order, the
    // server applies nothing, and the reply is what clears the pending.
    assert.deepEqual(assignItems([{ cover: "gone", to: "tall" }], {}, [cover("a")]), []);
  });

  it("leaves a shutter exactly as it is for an impact preview", () => {
    assert.deepEqual(currentAssignment(cover("a", { profile: "tall" })), {
      cover_unique_id: "a",
      profile: "tall",
    });
    // A window whose file names the profile: popping an assignment the record does not
    // have leaves the file answering, which is what `profile_from_file` means.
    assert.deepEqual(
      currentAssignment(cover("b", { profile: "tall", profile_from_file: true })),
      { cover_unique_id: "b", profile: null },
    );
  });
});

describe("a travel as somebody types it", () => {
  it("reads both decimal separators and nothing else", () => {
    assert.equal(parseTravel("145,5"), 145.5);
    assert.equal(parseTravel(" 145.5 "), 145.5);
    assert.equal(parseTravel(""), null);
    assert.equal(parseTravel("abc"), null);
    assert.equal(parseTravel("1e2"), 100);
  });

  it("names the refusal the server would name", () => {
    assert.equal(travelProblem(undefined), "missing_travel");
    assert.equal(travelProblem("   "), "missing_travel");
    assert.equal(travelProblem("abc"), "not_a_number");
    assert.equal(travelProblem("5"), "out_of_range");
    assert.equal(travelProblem("501"), "out_of_range");
    assert.equal(travelProblem("20"), null);
    assert.equal(travelProblem("500"), null);
  });
});

describe("the pending chip's label", () => {
  // The two sentences the chip is built out of, as the server serves them.
  const italian = async (): Promise<I18n> => {
    const i18n = new I18n();
    await i18n.load(
      {
        sendMessagePromise: async () =>
          ({
            language: "it",
            requested: "it",
            fallback: false,
            texts: {
              panel: {
                assign: {
                  pending: { route: "{from} → {to}", route_name: "«{profile}»" },
                  target_none: "«Senza profilo»",
                },
              },
            },
          }) as never,
        subscribeMessage: async () => async () => undefined,
      } as HaConnection,
      "it",
    );
    return i18n;
  };

  it("names the two ends without the word Profilo, in the lexicon's quotes", async () => {
    const i18n = await italian();
    assert.equal(routeLabel(i18n, "alte", "alte_nuovo_test"), "«alte» → «alte_nuovo_test»");
  });

  it("says where a shutter leaving every profile is going", async () => {
    const i18n = await italian();
    assert.equal(routeLabel(i18n, "alte", null), "«alte» → «Senza profilo»");
    assert.equal(routeLabel(i18n, null, "alte"), "«Senza profilo» → «alte»");
  });

  it("never abbreviates the destination: what it is given is what it says", async () => {
    const i18n = await italian();
    const long = "tapparelle_alte_del_soggiorno_sul_giardino_sul_retro";
    assert.equal(routeEnd(i18n, long), `«${long}»`);
    assert.ok(routeLabel(i18n, "alte", long).endsWith(`«${long}»`));
  });
});
