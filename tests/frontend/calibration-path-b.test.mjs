import assert from "node:assert/strict";
import { after, afterEach, test } from "node:test";

import { translations } from "../../custom_components/myhome/frontend/panel/panel-translations.js";
import { sampleOverview } from "./fake-calibration.mjs";
import { dom, mount, reset, settle, tick, waitFor } from "./wizard-harness.mjs";

afterEach(reset);
after(() => dom.window.close());

const calibrationTraffic = (backend) => [...backend.calls, ...backend.subscriptions].filter((message) => message.type.startsWith("myhome/cover_calibration/"));

test("B-01 offers the gateway's profiles with where they were measured and who follows them", async () => {
  const { wiz, code, press, startFor, title } = await mount();
  await startFor("cover.living_one", "B");
  assert.equal(code(), "B-01");
  assert.equal(title(), "Which profile does this roller shutter follow?");
  assert.deepEqual([...wiz().querySelectorAll('select[name="profile"] option')].map((option) => option.textContent), ["tall_two_leaf"]);
  assert.equal(wiz().querySelector(".wiz-choice-hint").textContent, "Measured on Living room shutter 1 · 2 shutters follow it");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Introduction · 1 of 3");
  assert.equal(wiz().querySelector(".wiz-steps-caption").textContent, 'Ⓑ like "tall_two_leaf"');
  await press("profile");
  assert.equal(code(), "B-02");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Tape measure readings · 2 of 3");
  assert.match(wiz().querySelector(".wiz-body").innerHTML, /<strong>the curtain travel<\/strong>/);
});

test("path B runs as a preview from the travel to the check and the summary, without any calibration message", async () => {
  const { backend, wiz, code, press, type, startFor, title } = await mount({ stageMs: 40 });
  await startFor("cover.living_one", "B");
  await press("profile");
  await press("begin");
  assert.equal(wiz().querySelector(".wiz-preview").textContent, translations.en.wizPreview);
  assert.equal(code(), "B-03");
  assert.equal(wiz().querySelector(".wiz-wait p").textContent, "Living room shutter 1 will open fully: measure the curtain travel from there. Wait for it to stop.");
  await waitFor(() => code() === "B-04", "B-04");
  await type("196");
  assert.equal(code(), "B-05");
  const stages = () => [...wiz().querySelectorAll(".wiz-wait-stages li")].map((item) => [item.textContent, item.dataset.stepState]);
  assert.deepEqual(stages(), [["1/2 Descends to the bottom — about 22 s", "current"], ["2/2 Ascends halfway through its travel — about 11 s", "future"]]);
  await waitFor(() => stages()[1]?.[1] === "current", "second stage");
  assert.equal(stages()[0][1], "done");
  await waitFor(() => code() === "B-06", "B-06");
  assert.equal(title(), "Check the roller shutter");
  assert.match(wiz().querySelector(".wiz-body").textContent, /The expected height is 98 cm, half of its 196 cm travel/);
  await type("99");
  assert.equal(code(), "B-07");
  assert.match(wiz().querySelector(".wiz-body").textContent, /^Gap of about 1 cm at half travel: profile "tall_two_leaf" describes this roller shutter well\./);
  assert.match(wiz().querySelector(".wiz-body").innerHTML, /The edge should have stopped at 98 cm and stopped at 99 cm\./);
  await press("accept");
  assert.equal(code(), "B-08");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Summary · 3 of 3");
  const rows = [...wiz().querySelectorAll(".wiz-main > .wiz-table tbody tr")].map((row) => [...row.children].map((cell) => cell.textContent));
  assert.deepEqual(rows, [["Opening time", "22 s", "22.2 s"], ["Closing time", "21.7 s", "="], ["Slat time", "—", "4.4 s"], ["Curtain travel", "195 cm", "196 cm"]]);
  assert.equal(wiz().querySelector(".wiz-technical .muted").textContent, "The two roll coefficients, 1.83 and 1.91, come from the profile: they were not measured on this roller shutter.");
  assert.equal(wiz().querySelector(".wiz-profile-block"), null, "B creates and updates no profile");
  assert.equal(wiz().querySelector('[data-wiz="refine"]'), null, "B cannot continue to fine-tuning");
  assert.match(wiz().querySelector(".wiz-main > .wiz-accordion:not(.wiz-technical)").innerHTML, /<strong>this shutter will follow profile "tall_two_leaf"<\/strong>/);
  await press("save");
  assert.equal(code(), "B-09");
  assert.equal(wiz().querySelector(".wiz-title").textContent, "Preview of the summary", "a preview never says it saved");
  assert.equal(wiz().querySelector(".wiz-body").textContent, "End of the preview: nothing has been saved and Living room shutter 1 keeps the values it used before.");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-action")].map((button) => button.textContent), ["Close"]);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-steps ul li")].map((item) => item.textContent), ["Curtain travel: 196 cm", "Check: 1 cm"], "the steps keep what was read");
  assert.ok(wiz().querySelector(".wiz-preview"));
  assert.deepEqual(calibrationTraffic(backend), [], "the preview sends nothing to Home Assistant");
});

test("a failed check offers to correct the cover with its own measurements, which opens path C", async () => {
  const { wiz, code, press, type, startFor, title } = await mount({ language: "it" });
  await startFor("cover.living_one", "B");
  await press("profile"); await press("begin"); await settle();
  await type("196"); await settle();
  await type("105");
  assert.equal(code(), "B-07b");
  assert.equal(title(), translations.it.wiz_T144);
  assert.match(wiz().querySelector(".wiz-body").textContent, /^Scarto di circa 7 cm a metà della corsa: più di quanto atteso\./);
  assert.match(wiz().querySelector(".wiz-body").innerHTML, /<strong>niente è ancora stato salvato<\/strong>/);
  assert.equal(wiz().querySelector('[data-wiz="continue_anyway"]'), null, "B has no Continue anyway");
  await press("repeat_check"); await settle();
  assert.equal(code(), "B-06");
  await type("105");
  await press("correct");
  assert.equal(code(), "C-01");
  assert.equal(wiz().querySelector(".wiz-preview"), null, "path C starts from the cover, outside the preview");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Living room shutter 1");
});

test("without a profile on the gateway, B is disabled and the screen says why", async () => {
  const overview = sampleOverview();
  overview.profiles = [];
  for (const cover of overview.covers) cover.profile_id = null;
  const { tab, wiz, code, press, pickCover } = await mount({ overview });
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  await pickCover();
  await press("choose");
  assert.equal(code(), "A-02");
  assert.equal(wiz().querySelector('[data-wiz="path:B"]').disabled, true);
  assert.match(wiz().querySelector(".wiz-notices").textContent, /No profile is saved on this gateway yet/);
});
