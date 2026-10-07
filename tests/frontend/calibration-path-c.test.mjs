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

test("C-01 shows what the cover uses now and C-02 preselects its first case, as in the mockup", async () => {
  const context = await mount();
  const { wiz, code, press, startFor, title } = context;
  await startFor("cover.kitchen_two", "C");
  assert.equal(code(), "C-01");
  assert.equal(title(), "What this cover currently uses");
  assert.match(wiz().querySelector(".wiz-body").textContent, /^Kitchen shutter 2 follows profile "tall_two_leaf", adapted to its 110 cm curtain travel/);
  assert.equal(wiz().querySelector(".wiz-box strong").textContent, "Currently in use");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-box p")].map((line) => line.textContent),
    ["Profile: tall_two_leaf", "Curtain travel: 110 cm", "Opening time: 12.3 s", "Closing time: 12.1 s", "Slat time: 2.4 s"]);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-box p strong")].map((value) => value.textContent), ["tall_two_leaf", "110 cm", "12.3 s", "12.1 s", "2.4 s"],
    "the values bold, the labels regular");
  await press("current");
  const options = [...wiz().querySelectorAll('input[name="case"]')];
  assert.deepEqual(options.map((input) => [input.value, input.checked]), [["points_only", true], ["times_only", false], ["times_and_rolls", false]]);
  assert.match(options[0].closest("label").innerHTML, /^<input[^>]*><span class="wiz-radio-text"><span class="wiz-radio-label"><strong>When sent halfway, it stops too high or too low; at the end stop it works correctly<\/strong><\/span><span class="wiz-radio-explain">We will redo only/, "title and explanation apart, 4 px between them (G4-3)");
});

test("times only runs the existing guided measurement and saves on this cover only", async () => {
  const context = await mount();
  const { backend, wiz, code, press, actions, title } = context;
  await toCase(context, "times_only");
  assert.equal(code(), "C-35");
  assert.equal(wiz().querySelector('input[name="slats"]'), null, "the guided protocol does not use the slat choice");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Preparation · 2 of 5");
  assert.equal(wiz().querySelector(".wiz-steps li[data-step-state] > ul > li").textContent, "Times only");
  await press("begin");
  const start = backend.subscriptions.find((message) => message.type === "myhome/cover_calibration/start");
  assert.equal("mode" in start, false, "a start without mode is the guided measurement");
  assert.equal("direction" in start, false, "both directions");
  assert.equal("slats" in start, false);
  assert.deepEqual(actions(), [], "the guided protocol starts nothing by itself");
  // G4-6: our own screens and texts, never the maintainer's phase texts.
  assert.equal(code(), "C-11");
  assert.equal(title(), "Full ascent");
  assert.match(wiz().querySelector(".wiz-body").textContent, /Get ready to press button ② when the motor stops by itself at the top: you can hear it\./);
  assert.doesNotMatch(wiz().textContent, /Confirm that the cover is fully closed and stopped before starting/);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => [item.dataset.wiz, item.disabled]), [["run:open", false], ["endpoint", true], ["stop", false]]);
  await press("run:open");
  await move(backend, { seconds: 12.6 });
  assert.equal(code(), "C-11");
  assert.equal(wiz().querySelector(".wiz-stopwatch").hidden, false);
  await press("endpoint");
  assert.equal(code(), "C-12");
  assert.equal(title(), "Ascent measured");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-results .wiz-result-label")].map((item) => item.textContent), ["Full ascent"]);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => item.dataset.wiz), ["ack:ascent", "restart"]);
  await press("ack:ascent");
  assert.equal(code(), "C-14");
  assert.equal(title(), "Full descent");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => item.textContent), ["①  Start movement", "②  Stopped at the bottom", "Stop the cover"]);
  await press("run:close");
  await move(backend, { seconds: 12.2 });
  assert.equal(code(), "C-14");
  await press("endpoint");
  assert.equal(code(), "C-15");
  assert.equal(title(), "Descent measured");
  await press("ack:descent");
  assert.equal(code(), "C-36");
  assert.equal(title(), "The calibration is ready");
  const rows = [...wiz().querySelectorAll(".wiz-main > .wiz-table tbody tr")].map((row) => [...row.children].map((cell) => cell.textContent));
  assert.deepEqual(rows, [["Opening time", "12.3 s", "12.6 s"], ["Closing time", "12.1 s", "12.2 s"], ["Slat time", "2.4 s", "="], ["Curtain travel", "110 cm", "="]]);
  assert.equal(wiz().querySelector(".wiz-profile-block"), null);
  assert.equal(wiz().querySelector('[data-wiz="refine"]'), null);
  assert.match(wiz().querySelector(".wiz-main > .wiz-accordion:not(.wiz-technical)").textContent, /Profile "tall_two_leaf" will not change, nor will the other cover following it\./);
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
  const before = [...wiz().querySelectorAll(".wiz-main > .wiz-table tbody td:nth-of-type(1)")];
  assert.ok(before.length === 4 && before.every((cell) => cell.classList.contains("muted")), "Before in grey");
  assert.equal(wiz().querySelector(".wiz-save-info").open, true);
  assert.equal(wiz().querySelector(".wiz-technical .muted").textContent, translations.en.wiz_T239);
  assert.match(wiz().querySelector(".wiz-precision").textContent, /after 4\.8 s of descent/);
  await press("save");
  assert.equal(code(), "C-34");
  assert.equal([...backend.calls, ...backend.subscriptions].filter((message) => message.type.startsWith("myhome/cover_calibration/")).length, 0);
});

test("remeasuring everything runs the geometry session with the C texts and waits for the backend to save on the cover only", async () => {
  const context = await mount({ language: "it" });
  const { backend, wiz, code, press, type } = context;
  await toCase(context, "times_and_rolls");
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
  assert.equal(wiz().querySelector(".wiz-result-notices").textContent, translations.it.wizSaveUnavailable, "D-16: at the top");
  const toggle = wiz().querySelector('[name="save_profile"]');
  toggle.checked = true; toggle.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  await press("save");
  assert.equal(backend.calls.filter((message) => message.action === "save").at(-1).save_mode, "new");
  assert.equal(code(), "C-34");
});

test("times only: a repeat starts the times again from the briefing, and a run the bus ended without ② is not valid (G4-6, R8-7)", async () => {
  const context = await mount();
  const { backend, wiz, code, press } = context;
  await toCase(context, "times_only");
  await press("begin");
  await press("run:open");
  await move(backend, { seconds: 12.6 });
  await press("endpoint");
  assert.equal(code(), "C-12");
  await press("restart"); await tick(8);
  assert.equal(backend.session.phase, "cancelled", "the attempt is cancelled, nothing saved");
  assert.equal(code(), "C-35");
  const panel = context.panel ?? document.querySelector("myhome-panel");
  const wizard = panel._calibrationTab._wizard;
  // A guided run is tracked as a full run, for the same validity rule.
  wizard._local.fullRun = null;
  wizard._trackFullRun({ mode: "guided", phase: "opening", owner: true, attachment: "a" });
  assert.equal(wizard._local.fullRun.step, "opening");
});

test("D-20: in C-01 a value not known is «—» without its unit", async () => {
  const { buildScreen } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-screens.js");
  const { translations } = await import("../../custom_components/myhome/frontend/panel/panel-translations.js");
  const t = (key) => translations.it[key] || key;
  const cover = { name: "Studio", profile: { name: "standard_3ante" }, travel_cm: 150, effective: { opening: { value: 20 }, closing: { value: 19 }, slat_time_s: { value: null } } };
  const screen = buildScreen({ t, language: "it", stage: "current", path: "C", cover });
  assert.equal(screen.code, "C-01");
  assert.equal(screen.box.lines.at(-1), "Tempo lamelle: —");
  assert.equal(screen.box.lines[1], "Corsa del telo: 150 cm", "known values keep their unit");
});
