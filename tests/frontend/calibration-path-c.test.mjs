import assert from "node:assert/strict";
import { after, afterEach, test } from "node:test";

import { translations } from "../../custom_components/myhome/frontend/panel/panel-translations.js";
import { dom, mount, move, reset, settle, tick } from "./wizard-harness.mjs";

afterEach(reset);
after(() => dom.window.close());

async function toCase(context, scope) {
  const { wiz, press, startFor, code, backend } = context;
  // L-38: a times-only measurement starts at once only from a cover Home Assistant reports closed at a known 0.
  if (scope === "times_only") backend.hass.states["cover.kitchen_two"] = { state: "closed", attributes: { current_position: 0 } };
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
  assert.match(options[0].closest("label").innerHTML, /^<input[^>]*><span class="wiz-radio-text"><span class="wiz-radio-label"><strong>When sent halfway, it stops too high or too low; at the end stop it works correctly<\/strong> <span class="badge wiz-recommended">Recommended<\/span><\/span><span class="wiz-radio-explain">We will remeasure only/, "title and explanation apart, 4 px between them (G4-3); L-34: recommended");
  assert.match(wiz().querySelector(".wiz-body").textContent, /This cover has only its base calibration: fine-tuning adds the readings/, "L-34: why");
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
  // L-30: the hint gives a range; the expected height is the preview's own.
  const expected = Math.round(document.querySelector("myhome-panel")._calibrationTab._wizard._gateway.view.expected_cm);
  await type(String(expected));
  assert.equal(code(), "C-32");
  assert.match(wiz().querySelector(".wiz-body").textContent, /Gap of about 0 cm after 4\.8 s of descent/);
  await press("accept");
  assert.equal(code(), "C-38");
  const before = [...wiz().querySelectorAll(".wiz-main > .wiz-table tbody td:nth-of-type(1)")];
  assert.ok(before.length === 6 && before.every((cell) => cell.classList.contains("muted")), "Before in grey");
  // D-35: the rolls, the only values that change here, are in the table; a gap under 1 cm is said so.
  assert.deepEqual([...wiz().querySelectorAll(".wiz-main > .wiz-table tbody th")].slice(-2).map((cell) => cell.textContent), [translations.en.wiz_T105, translations.en.wiz_T106]);
  assert.equal(wiz().querySelector(".wiz-save-info"), null, "L-46: a preview saves nothing");
  assert.equal(wiz().querySelector(".wiz-technical .muted").textContent, translations.en.wiz_T239);
  assert.match(wiz().querySelector(".wiz-precision").textContent, /a gap under 1 cm after 4\.8 s of descent/);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((button) => button.dataset.wiz), ["close", "another"]);
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
  await type("110"); await press("ack:ascent");
  await press("next"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  await type("54"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await move(backend, { auto: true, stop: true }); await type("56"); await press("check-start");
  assert.equal(code(), "C-21");
  assert.match(wiz().querySelector(".wiz-body").textContent, /quelli del profilo «tall_two_leaf» adattati alla corsa del telo di Kitchen shutter 2/);
  assert.equal(wiz().querySelector('[name="save_profile"]').checked, false);
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, true);
  assert.equal(wiz().querySelector(".wiz-result-notices .wiz-notice").textContent,
    "Salvare solo su questa tapparella non è ancora disponibile in questa versione: accendi «Salva anche come profilo riusabile, o aggiorna quello esistente» per salvare i valori misurati come profilo nuovo.",
    "D-16: at the top; N-11: it names the way of saving and the switch to turn on");
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

test("L-4: a «solo tempi» session the wizard started opens in the wizard's reader view from a second tab; one from Devices keeps the maintainer's dialog", async () => {
  // The wizard marks its own start.
  const first = await mount();
  await toCase(first, "times_only");
  await first.press("begin");
  assert.equal(first.backend.subscriptions.find((message) => message.type === "myhome/cover_calibration/start").origin, "wizard");
  reset();
  const guided = (extra) => ({ entry_id: "one", entity_id: "cover.living_one", session_id: "session-1", sequence: 5, revision: 7, mode: "guided",
    phase: "opening", reason: null, values: {}, stop_requested: false, save_modes: ["new", "cover", "shared"], _started: 0, ...extra });
  const second = await mount({ session: guided({ origin: "wizard" }), owner: false });
  second.backend.tick(8);
  second.tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(8);
  assert.equal(second.root.querySelector("#dialog-host dialog.cal-dialog"), null, "not the maintainer's dialog");
  assert.equal(second.code(), "C-11");
  assert.ok(second.wiz().querySelector(".wiz-readonly"), "the reader view");
  assert.deepEqual([...second.wiz().querySelectorAll(".wiz-actions .wiz-action")].map((button) => button.dataset.wiz).at(-1), "stop", "with its Stop (L-23: after the step's own buttons, off)");
  assert.deepEqual(second.wiz().querySelector(".wiz-steps") && [...second.wiz().querySelectorAll(".wiz-steps > ol > li")].length, 5, "the «solo tempi» steps");
  reset();
  const devices = await mount({ session: guided({}), owner: false });
  devices.tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(8);
  assert.ok(devices.root.querySelector("#dialog-host dialog.cal-dialog"), "started from Devices: the maintainer's dialog");
  assert.equal(devices.wiz(), null);
});

test("L-38: times only first closes an open cover, as path A does, then starts on «check that it is fully closed»", async () => {
  const context = await mount();
  const { backend, wiz, code, press, panel } = context;
  await toCase(context, "times_only");
  backend.hass.states["cover.kitchen_two"] = { state: "open", attributes: { current_position: 100 } };
  await press("begin");
  assert.equal(code(), "C-04", "the positioning first");
  assert.equal(wiz().querySelector(".wiz-title").textContent, "Positioning cover");
  assert.deepEqual(backend.hass.services.at(-1), { domain: "cover", service: "close_cover", data: { entity_id: "cover.kitchen_two" } });
  assert.equal(backend.subscriptions.some((message) => message.type === "myhome/cover_calibration/start"), false, "no session yet");
  assert.ok(wiz().querySelector('[data-wiz="stop"]'), "Stop while it closes");
  // Home Assistant reports it closed: the session starts on its confirmation.
  backend.hass.states["cover.kitchen_two"] = { state: "closed", attributes: { current_position: 0 } };
  panel._calibrationTab._wizard.updateHass(backend.hass); await tick(6);
  assert.equal(backend.subscriptions.filter((message) => message.type === "myhome/cover_calibration/start").at(-1).mode, undefined, "the guided session");
  assert.equal(code(), "C-11");
  // Stop during the positioning: Home Assistant stops the cover, nothing has started.
  reset();
  const again = await mount();
  await toCase(again, "times_only");
  // After a restart Home Assistant knows no position for a modelled cover: positioned first too.
  again.backend.hass.states["cover.kitchen_two"] = { state: "open", attributes: { current_position: null } };
  await again.press("begin");
  again.wiz().querySelector('[data-wiz="stop"]').click(); await tick(4);
  assert.deepEqual(again.backend.hass.services.at(-1), { domain: "cover", service: "stop_cover", data: { entity_id: "cover.kitchen_two" } });
  assert.equal(again.backend.subscriptions.some((message) => message.type === "myhome/cover_calibration/start"), false);
  // From «Perfeziona» (start: refine): C-01 → C-02 → times only, a cover reported closed but at no known position.
  reset();
  const third = await mount();
  const tabView = third.panel._calibrationTab, item = tabView._covers().find((entry) => entry.cover.entity_id === "cover.kitchen_two");
  third.backend.hass.states["cover.kitchen_two"] = { state: "closed", attributes: { current_position: null } };
  tabView._openWizard({ start: "refine", item }); await tick();
  assert.equal(third.code(), "C-01");
  await third.press("current");
  const radio = third.wiz().querySelector('input[name="case"][value="times_only"]'); radio.checked = true; radio.dispatchEvent(new Event("change", { bubbles: true }));
  await third.press("case"); await third.press("begin");
  assert.equal(third.code(), "C-04", "an unknown position is positioned first, whatever the state says");
  assert.equal(third.backend.hass.services.at(-1).service, "close_cover");
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

test("D-21: before a case or path is confirmed the stepper follows the one chosen so far", async () => {
  const { buildScreen } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-screens.js");
  const { translations } = await import("../../custom_components/myhome/frontend/panel/panel-translations.js");
  const t = (key) => translations.en[key] || key;
  const cover = { name: "Studio", profile: { name: "standard_3ante" }, travel_cm: 150, effective: { opening: { value: 20 }, closing: { value: 19 } } };
  const at = (stage, scope = null, local = {}) => buildScreen({ t, stage, path: "C", scope, cover, local });
  const keys = (screen) => screen.stepper.phases.map((phase) => phase.key);
  // L-11: C-01 shows the steps of the case preselected on C-02 (the tape readings only) at once.
  assert.deepEqual(keys(at("current")), ["intro", "prep", "readings", "summary"], "C-01: the preselected case's steps, not path A's seven");
  assert.match(at("current").stepper.line, / of 4/);
  assert.deepEqual(keys(at("case")), ["intro", "prep", "readings", "summary"]);
  assert.equal(at("case").stepper.phases[0].substeps[0].value, t("wiz_T236"), "its caption too");
  assert.deepEqual(keys(at("case", "times_only")), ["intro", "prep", "ascent", "descent", "summary"], "the case just ticked");
});

test("N-14: C-01's «Currently in use» box stands out from the page in both themes", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-box \{ display: grid; gap: 4px; padding: 12px 14px; border-radius: 10px; border: 1px solid var\(--panel-border\);\s*background: color-mix\(in srgb, var\(--primary-text-color, #182b37\) 6%, var\(--panel-surface\)\); \}/);
});
