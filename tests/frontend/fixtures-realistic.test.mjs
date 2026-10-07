/** The realistic house used by the browser checks: the Calibration tab reads it as Home Assistant would send it. */
import assert from "node:assert/strict";
import { after, afterEach, test } from "node:test";

import { mount, reset, tick, dom } from "./wizard-harness.mjs";
import { realisticFixture } from "./fixtures-realistic.mjs";

afterEach(reset);
after(() => dom.window.close());

const rows = (tab) => [...tab().querySelectorAll(".cal-row")];
const badge = (tab, entity) => rows(tab).find((row) => row.dataset.entity === entity).querySelector(".cal-badge").dataset.status;

test("the realistic house lists every timed cover with its state, never the awning with a position sensor", async () => {
  const { tab } = await mount(realisticFixture());
  await tick(8);
  assert.equal(rows(tab).length, 10);
  assert.equal(rows(tab).some((row) => row.dataset.entity === "cover.tenda_terrazza"), false);
  assert.deepEqual(["cover.soggiorno_1", "cover.camera_giardino", "cover.cucina", "cover.ospiti", "cover.studio", "cover.bagno"].map((entity) => badge(tab, entity)),
    ["rolls", "rolls", "times", "times", "to_measure", "to_measure"]);
  assert.match(rows(tab).find((row) => row.dataset.entity === "cover.camera_giardino").textContent, /Tapparella Camera Matrimoniale Lato Giardino/);
});

test("a session open in another tab puts its cover on top, in progress, and holds every new measurement", async () => {
  const { tab } = await mount(realisticFixture({ session: "running" }));
  await tick(8);
  const first = rows(tab)[0];
  assert.equal(first.dataset.entity, "cover.bagno");
  assert.equal(first.querySelector(".cal-badge").dataset.status, "running");
  assert.ok(first.querySelector('[data-action="cal-tab-session"]'));
  assert.equal(tab().querySelector('[data-action="cal-tab-measure"]').disabled, true);
});

test("a paused automatic cycle shows as paused on its cover", async () => {
  const { tab } = await mount(realisticFixture({ session: "paused" }));
  await tick(8);
  const first = rows(tab)[0];
  assert.equal(first.dataset.entity, "cover.corridoio");
  assert.match(first.querySelector(".cal-badge").textContent, /pausa|paused/i);
});
