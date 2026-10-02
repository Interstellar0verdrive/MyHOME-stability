import assert from "node:assert/strict";
import { after, afterEach, test } from "node:test";

import { translations } from "../../custom_components/myhome/frontend/panel/panel-translations.js";
import { dom, mount, move, reset, settle, tick } from "./wizard-harness.mjs";

afterEach(reset);
after(() => dom.window.close());

async function toCase(context, scope) {
  const { wiz, press, startFor, code } = context;
  await startFor("cover.kitchen_two", "C");
  assert.equal(code(), "C-01");
  await press("current");
  assert.equal(code(), "C-02");
  if (scope) {
    const radio = wiz().querySelector(`input[name="case"][value="${scope}"]`);
    radio.checked = true; radio.dispatchEvent(new Event("change", { bubbles: true }));
  }
  await press("case");
}

test("C-01 shows what the cover uses now and C-02 preselects the case that remeasures everything", async () => {
  const context = await mount();
  const { wiz, code, press, startFor, title } = context;
  await startFor("cover.kitchen_two", "C");
  assert.equal(code(), "C-01");
  assert.equal(title(), "What this roller shutter currently uses");
  assert.match(wiz().querySelector(".wiz-body").textContent, /^Kitchen shutter 2 follows profile "tall_two_leaf", adapted to its 110 cm curtain travel/);
  assert.equal(wiz().querySelector(".wiz-box p").textContent,
    "Profile: tall_two_leaf · Curtain travel: 110 cm · Opening time: 12.3 s · Closing time: 12.1 s · Slat time: 2.4 s");
  await press("current");
  const options = [...wiz().querySelectorAll('input[name="case"]')];
  assert.deepEqual(options.map((input) => [input.value, input.checked]), [["points_only", false], ["times_only", false], ["times_and_rolls", true]]);
  assert.match(options[0].closest("label").innerHTML, /^<input[^>]*><span><strong>When sent halfway, it stops too high or too low; at the end stop it works correctly<\/strong><br>We will redo only/);
});

test("times only runs the existing guided measurement and saves on this cover only", async () => {
  const context = await mount();
  const { backend, wiz, code, press, actions, title } = context;
  await toCase(context, "times_only");
  assert.equal(code(), "C-35");
  assert.equal(wiz().querySelector('input[name="slats"]'), null, "the guided protocol does not use the slat choice");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Preparation · 2 of 5");
  assert.equal(wiz().querySelector(".wiz-steps-caption").textContent, "Ⓒ times only");
  await press("begin");
  const start = backend.subscriptions.find((message) => message.type === "myhome/cover_calibration/start");
  assert.equal("mode" in start, false, "a start without mode is the guided measurement");
  assert.equal("direction" in start, false, "both directions");
  assert.equal("slats" in start, false);
  assert.deepEqual(actions(), [], "the guided protocol starts nothing by itself");
  assert.equal(code(), "C-05");
  await press("run:open");
  await move(backend, { seconds: 12.6 });
  assert.equal(code(), "C-11");
  assert.equal(wiz().querySelector(".wiz-stopwatch").hidden, false);
  await press("endpoint");
  assert.equal(code(), "C-12");
  await press("run:close");
  await move(backend, { seconds: 12.2 });
  assert.equal(code(), "C-14");
  await press("endpoint");
  assert.equal(code(), "C-36");
  assert.equal(title(), "The calibration is ready");
  const rows = [...wiz().querySelectorAll(".wiz-main > .wiz-table tbody tr")].map((row) => [...row.children].map((cell) => cell.textContent));
  assert.deepEqual(rows, [["Opening time", "12.3 s", "12.6 s"], ["Closing time", "12.1 s", "12.2 s"], ["Slat time", "2.4 s", "="], ["Curtain travel", "110 cm", "="]]);
  assert.equal(wiz().querySelector(".wiz-profile-block"), null);
  assert.equal(wiz().querySelector('[data-wiz="refine"]'), null);
  assert.match(wiz().querySelector(".wiz-main > .wiz-accordion:not(.wiz-technical)").textContent, /Profile "tall_two_leaf" will not change, nor will the other 1 shutters following it/);
  await press("save");
  const save = backend.calls.filter((message) => message.action === "save").at(-1);
  assert.equal(save.save_mode, "cover");
  assert.equal("name" in save, false);
  assert.equal(code(), "C-34");
  assert.equal(wiz().querySelector(".wiz-body").textContent, 'Kitchen shutter 2 now uses its own measured values; profile "tall_two_leaf" has not changed.');
  assert.deepEqual(actions(), ["open", "endpoint", "close", "endpoint", "save"]);
});

test("tape readings only run as a preview with four readings and the check, saved on this cover", async () => {
  const context = await mount();
  const { backend, wiz, code, press, type } = context;
  await toCase(context, "points_only");
  assert.equal(code(), "C-37");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Preparation · 2 of 4");
  assert.match(wiz().querySelector(".wiz-body").textContent, /The 110 cm curtain travel is already known/);
  await press("begin"); await settle();
  assert.equal(code(), "C-23");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Tape measure readings · 3 of 4");
  for (const [reading, next] of [["27", "C-25"], ["82", "C-27"], ["83", "C-29"], ["28", "C-31"]]) {
    await type(reading); await settle();
    assert.equal(code(), next);
  }
  const expected = Number(wiz().querySelector("#wiz-field-hint").textContent.match(/About (\d+) cm/)[1]);
  await type(String(expected));
  assert.equal(code(), "C-32");
  assert.match(wiz().querySelector(".wiz-body").textContent, /Gap of about 0 cm after 4\.8 s of descent/);
  await press("accept");
  assert.equal(code(), "C-38");
  assert.equal(wiz().querySelector(".wiz-technical .muted").textContent, translations.en.wiz_T239);
  assert.match(wiz().querySelector(".wiz-precision").textContent, /after 4\.8 s of descent/);
  await press("save");
  assert.equal(code(), "C-34");
  assert.equal([...backend.calls, ...backend.subscriptions].filter((message) => message.type.startsWith("myhome/cover_calibration/")).length, 0);
});

test("remeasuring everything runs the geometry session with the C texts and waits for the backend to save on the cover only", async () => {
  const context = await mount({ language: "it" });
  const { backend, wiz, code, press, type } = context;
  await toCase(context);
  assert.equal(code(), "C-03");
  assert.match(wiz().querySelector(".wiz-body").textContent, /Devi trovarti davanti a Kitchen shutter 2/);
  await press("begin");
  assert.equal(backend.subscriptions.find((message) => message.type === "myhome/cover_calibration/start").mode, "geometry");
  assert.equal(code(), "C-04");
  assert.equal(wiz().querySelector(".wiz-wait p").textContent, "Kitchen shutter 2 viene chiusa completamente: in questo modo le misure partono da un punto noto. Aspetta che si fermi.");
  await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift");
  assert.equal(code(), "C-07");
  await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  await type("2"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("110");
  await press("next"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  await type("54"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await move(backend, { auto: true, stop: true }); await type("56");
  assert.equal(code(), "C-21");
  assert.match(wiz().querySelector(".wiz-body").textContent, /quelli del profilo «tall_two_leaf» adattati alla corsa del telo di Kitchen shutter 2/);
  assert.equal(wiz().querySelector('[name="save_profile"]').checked, false);
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, true);
  assert.equal(wiz().querySelector(".wiz-notices").textContent, translations.it.wizSaveUnavailable);
  const toggle = wiz().querySelector('[name="save_profile"]');
  toggle.checked = true; toggle.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  await press("save");
  assert.equal(backend.calls.filter((message) => message.action === "save").at(-1).save_mode, "new");
  assert.equal(code(), "C-34");
});
