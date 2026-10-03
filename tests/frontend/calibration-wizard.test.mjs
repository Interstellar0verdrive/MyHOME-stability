import assert from "node:assert/strict";
import { after, afterEach, test } from "node:test";

import { translations } from "../../custom_components/myhome/frontend/panel/panel-translations.js";
import { sampleOverview } from "./fake-calibration.mjs";
import { dom, mount, move, reset, settle, tick } from "./wizard-harness.mjs";

const { parseReading } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-wizard.js");
const { buildScreen, phasesFor, slug } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-screens.js");
const { inline, rich } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-text.js");

afterEach(reset);
after(() => dom.window.close());

test("bold spans, paragraphs and line breaks are rendered from escaped text only", () => {
  assert.equal(inline("**You will need a tape measure. **Stand here"), "<strong>You will need a tape measure.</strong> Stand here");
  assert.equal(rich("**Done.\n**Gap <b>1</b> cm\n\nNext"), "<p><strong>Done.</strong><br>Gap &lt;b&gt;1&lt;/b&gt; cm</p><p>Next</p>");
  assert.equal(parseReading("2,8"), 2.8);
  assert.ok(Number.isNaN(parseReading("")));
  assert.equal(slug("Tapparella Sala 1"), "tapparella_sala_1");
  assert.deepEqual(phasesFor("A", null, false), ["intro", "prep", "ascent", "descent", "readings", "summary", "finetune"]);
  assert.deepEqual(phasesFor("A", null, true).length, 8);
  assert.deepEqual(phasesFor("B"), ["intro", "readings", "summary"]);
});

test("every generated screen text is filled in English and Italian", () => {
  for (const language of ["en", "it"]) {
    for (const [key, value] of Object.entries(translations[language])) {
      if (!key.startsWith("wiz")) continue;
      assert.ok(value.trim(), `${language} ${key} is empty`);
      assert.equal((value.match(/\*\*/g) || []).length % 2, 0, `${language} ${key} has unbalanced bold markers`);
      assert.doesNotMatch(value, /<[a-z]/i, `${language} ${key} carries HTML`);
    }
  }
  const placeholders = (value) => [...value.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();
  for (const key of Object.keys(translations.en).filter((item) => item.startsWith("wiz"))) {
    assert.deepEqual(placeholders(translations.it[key]), placeholders(translations.en[key]), key);
  }
});

test("A-01 to A-03 stay in the browser: choosing a cover and a path sends nothing", async () => {
  const { tab, wiz, code, press, title, backend, button, pickCover, choosePath } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.equal(code(), "A-01");
  assert.equal(title(), "Which roller shutter do you want to measure?");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Measure a roller shutter");
  assert.match(wiz().querySelector(".wiz-body").innerHTML, /<strong>from travel times<\/strong>/);
  const options = [...wiz().querySelectorAll('select[name="cover"] option')].map((option) => option.textContent);
  assert.deepEqual(options, ["Choose a roller shutter…", "Kitchen shutter 2 · Kitchen · Address: 91 · A: 9 · PL: 1 · Times and roll, Sep 29",
    "Living room shutter 1 · Living room · Address: 91 · A: 9 · PL: 1 · To measure", "Living room shutter 3 · Living room · Address: 91 · A: 9 · PL: 1 · Times measured, Sep 29"],
    "each cover names its state after the address");
  assert.equal(wiz().querySelector(".wiz-choice-note"), null, "no note before a choice");
  const subtitle = () => wiz().querySelector(".wiz-head .muted");
  assert.equal(subtitle().textContent, "No roller shutter selected yet", "a placeholder until a cover is picked");
  assert.ok(subtitle().classList.contains("wiz-head-placeholder"));
  assert.equal(wiz().querySelector('select[name="cover"]').value, "", "opened from the tab's button, the drop-down starts empty");
  assert.equal(wiz().querySelector('select[name="cover"] option').disabled, true, "the placeholder cannot be chosen");
  assert.equal(button("choose").disabled, true, "Continue waits for a choice");
  await pickCover(1);
  assert.equal(subtitle().textContent, "Living room shutter 1 · Living room · Address: 91 · A: 9 · PL: 1", "the picked cover, as in the drop-down");
  assert.equal(subtitle().classList.contains("wiz-head-placeholder"), false);
  assert.equal(wiz().querySelector(".wiz-choice-note"), null, "a never measured cover has no note");
  assert.equal(wiz().querySelector('select[name="cover"]').value, JSON.stringify(["one", "cover.living_one"]), "the choice survives the redraw");
  assert.equal(wiz().querySelector('select[name="cover"] option').textContent.startsWith("Kitchen"), true, "the placeholder leaves once a cover is chosen");
  assert.equal(button("choose").disabled, false);
  await pickCover(0);
  assert.equal(wiz().querySelector(".wiz-choice-note.cal-note").textContent,
    "This roller shutter is already calibrated (times and roll, Sep 29, 2026). A new measurement replaces the values in use; to adjust them, use fine-tuning.");
  await press("choose");
  assert.equal(code(), "A-02");
  assert.equal(title(), 'How to measure "Kitchen shutter 2"?');
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Kitchen shutter 2");
  assert.match(wiz().querySelector(".wiz-head .muted").textContent, /Address: 91 · A: 9 · PL: 1 · WHO 2/);
  assert.equal(wiz().querySelector(".wiz-subline").textContent, 'Follows the profile "tall_two_leaf"');
  const radios = [...wiz().querySelectorAll('.wiz-radios input[name="path"]')];
  assert.deepEqual(radios.map((input) => input.closest(".wiz-radio").querySelector(".wiz-radio-label").firstChild.textContent.trim()),
    ["Ⓐ  First roller shutter of this type", "Ⓑ  Like one already measured", "Ⓒ  Has a profile, but stops at the wrong point"], "a radio list, not three buttons");
  assert.equal(wiz().querySelectorAll('.wiz-actions [data-wiz^="path:"]').length, 0);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-recommended")].map((badge) => [badge.closest(".wiz-radio").querySelector("input").value, badge.textContent]),
    [["C", "Recommended"]], "a calibrated cover: C is advised");
  assert.deepEqual(radios.filter((input) => input.checked).map((input) => input.value), ["C"], "the advised path is preselected");
  assert.equal(button("path").disabled, false, "Continue is ready on the advised path");
  assert.doesNotMatch(wiz().querySelector(".wiz-body").textContent, /If unsure/, "no fallback advice while the advised path is chosen");
  const sent = () => backend.calls.length + backend.subscriptions.length;
  const before = sent();
  const a = radios.find((input) => input.value === "A");
  a.checked = true; a.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  assert.equal(code(), "A-02", "ticking a radio only changes the choice");
  assert.equal(wiz().querySelector('input[name="path"][value="A"]').checked, true, "the choice survives the redraw");
  assert.match(wiz().querySelector(".wiz-body").textContent, /If unsure, choose Ⓐ/, "away from the advice, the fallback line is back");
  assert.equal(sent(), before, "choosing a path sends nothing");
  await choosePath("A");
  assert.equal(code(), "A-03");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Preparation · 2 of 7");
  assert.equal(wiz().querySelector('.wiz-steps li[data-step-state="current"] .wiz-step-label').textContent, "Preparation");
  assert.equal(wiz().querySelector('input[name="slats"][value="yes"]').checked, true);
  assert.equal(backend.calls.filter((message) => message.type.startsWith("myhome/cover_calibration/")).length, 0);
  assert.equal(backend.subscriptions.filter((message) => message.type.startsWith("myhome/cover_calibration/")).length, 0);
  // Cancel before any session simply closes the wizard.
  button("exit").click(); await tick();
  assert.equal(wiz(), null);
  assert.ok(tab().querySelector(".cal-list"));
});

test("path A runs the live geometry session from the first close to Save, one message per press", async () => {
  const { backend, wiz, code, press, type, actions, title, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  const start = backend.subscriptions.find((message) => message.type === "myhome/cover_calibration/start");
  assert.equal(start.mode, "geometry");
  assert.equal(start.entity_id, "cover.living_one");
  assert.equal(start.revision, 7);
  assert.ok(start.client_id);
  assert.equal("slats" in start, false, "a cover with slats keeps the default");
  await tick();
  assert.deepEqual(actions(), ["next"], "Understood, begin closes the cover once");
  assert.equal(code(), "A-04");
  await move(backend);
  assert.equal(code(), "A-05");
  assert.equal(title(), "Starting closure");
  await press("endpoint");
  backend.stopped(); await tick();
  assert.equal(code(), "A-06");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Ascent · 3 of 7");
  await press("ack:lift");
  assert.equal(code(), "A-07");
  assert.equal(wiz().querySelector(".wiz-stopwatch").hidden, true, "no stopwatch before the run");
  assert.equal(wiz().querySelector('[data-wiz="lift"]').disabled, true);
  await press("next");
  await move(backend, { seconds: 4 });
  assert.equal(wiz().querySelector(".wiz-stopwatch").hidden, false);
  assert.equal(wiz().querySelector(".wiz-stopwatch-label").textContent, "Motor");
  assert.match(wiz().querySelector(".wiz-stopwatch-value").textContent, /^moving for \d+(\.\d)? s$/);
  assert.equal(wiz().querySelector('[data-wiz="next"]').disabled, true);
  await press("lift");
  backend.stopped(); await tick();
  assert.equal(code(), "A-08");
  await type("3");
  assert.deepEqual(actions().slice(-2), ["reading", "next"], "the return to the rest follows the reading by itself");
  assert.equal(code(), "A-09");
  await move(backend);
  assert.equal(code(), "A-10");
  await press("endpoint");
  backend.stopped(); await tick();
  assert.equal(code(), "A-11");
  await press("next");
  await move(backend, { seconds: 22.2 });
  await press("endpoint");
  backend.stopped(); await tick();
  assert.equal(code(), "A-12");
  assert.match(wiz().querySelector(".wiz-body").textContent, /^Slats 4(\.\d)? s, full ascent 22\.2 s\./);
  await press("ack:ascent");
  assert.equal(code(), "A-13");
  assert.equal(wiz().querySelector('[name="reading_cm"]').value, "195", "the saved travel is offered, not sent");
  await type("198");
  assert.equal(code(), "A-14");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Descent · 4 of 7");
  await press("next");
  await move(backend, { seconds: 21.7 });
  await press("endpoint");
  backend.stopped(); await tick();
  assert.equal(code(), "A-15");
  await press("repeat");
  assert.equal(actions().at(-1), "next", "the return to the top starts by itself");
  await move(backend);
  assert.equal(wiz().querySelector('[data-wiz="endpoint"]').textContent, "It is fully open, continue");
  await press("endpoint"); backend.stopped(); await tick();
  assert.equal(code(), "A-14");
  await press("next"); await move(backend, { seconds: 21.7 }); await press("endpoint"); backend.stopped(); await tick();
  assert.equal(code(), "A-15", "a repeated descent is confirmed again");
  await press("ack:descent");
  assert.equal(code(), "A-16");
  await press("ack:readings");
  assert.equal(actions().at(-1), "next");
  assert.equal(code(), "A-17");
  await move(backend, { auto: true, stop: true });
  assert.equal(code(), "A-18");
  assert.equal(wiz().querySelector("#wiz-field-hint").textContent, "For this cover the reading should be between 73.6 and 109.1 cm. Enter what the tape says.");
  const sentBefore = actions().length;
  await type("120");
  assert.equal(actions().length, sentBefore, "a reading outside the accepted range is not sent");
  assert.equal(wiz().querySelector('[name="reading_cm"]').getAttribute("aria-invalid"), "true");
  assert.equal(wiz().querySelector(".wiz-notices").textContent,
    "The reading (120 cm) is outside the accepted range (73.6–109.1 cm). Check the measurement reference and repeat the step. If the timings measured earlier were wrong, cancel and restart the guided measurement.");
  await type("97");
  assert.equal(wiz().querySelector(".wiz-notices").textContent, "");
  assert.equal(actions().at(-1), "next", "the return to the top starts by itself");
  assert.equal(code(), "A-19");
  await move(backend);
  assert.equal(wiz().querySelector('[data-wiz="endpoint"]').textContent, "It is fully open, continue");
  await press("endpoint");
  backend.stopped(); await tick();
  assert.equal(actions().at(-1), "next", "the half descent starts by itself after the top");
  await move(backend, { auto: true, stop: true });
  assert.equal(code(), "A-20");
  await type("101");
  assert.equal(code(), "A-21");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Summary · 6 of 7");
  const rows = [...wiz().querySelectorAll(".wiz-table:not(.wiz-technical .wiz-table) tbody tr")].map((row) => [...row.children].map((cell) => cell.textContent));
  assert.deepEqual(rows[3], ["Curtain travel", "195 cm", "198 cm"]);
  assert.equal(wiz().querySelector('[name="save_profile"]').checked, true);
  assert.equal(wiz().querySelector('[name="profile_name"]').value, "living_room_shutter_1");
  assert.equal(wiz().querySelector(".wiz-name-line").textContent, 'You will create the profile "living_room_shutter_1".');
  await press("save");
  const save = backend.calls.filter((message) => message.action === "save").at(-1);
  assert.equal(save.save_mode, "new");
  assert.equal(save.name, "living_room_shutter_1");
  assert.equal(code(), "A-34");
  assert.match(wiz().querySelector(".wiz-body").textContent, /The profile "living_room_shutter_1" was created/);
  assert.deepEqual(actions(), ["next", "endpoint", "next", "lift", "reading", "next", "endpoint", "next", "endpoint", "reading", "next", "endpoint",
    "repeat", "next", "endpoint", "next", "endpoint", "next", "reading", "next", "endpoint", "next", "reading", "save"]);
});

test("without slats the lift-off is skipped and the slat choice is sent", async () => {
  const { backend, code, press, startFor, wiz } = await mount();
  await startFor("cover.living_one");
  const no = wiz().querySelector('input[name="slats"][value="no"]');
  no.checked = true; no.dispatchEvent(new Event("change", { bubbles: true }));
  await press("begin");
  assert.equal(backend.subscriptions.find((message) => message.type === "myhome/cover_calibration/start").slats, false);
  await move(backend);
  await press("endpoint");
  backend.stopped(); await tick();
  assert.equal(code(), "A-11");
  assert.equal(wiz().querySelector(".wiz-title").textContent, "Full ascent");
  assert.equal([...wiz().querySelectorAll(".wiz-steps li li")].some((item) => item.textContent.startsWith("Lift-off")), false);
});

test("a wide gap asks before moving on and a reading out of range stays in the field", async () => {
  const { backend, code, press, type, actions, startFor, wiz } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  await type("25");
  assert.equal(wiz().querySelector('[name="reading_cm"]').getAttribute("aria-invalid"), "true");
  assert.equal(actions().includes("reading"), false, "a gap above the limit is not sent");
  await type("12");
  assert.equal(code(), "A-08");
  assert.match(wiz().querySelector(".wiz-notices").textContent, /10 cm or more/);
  assert.equal(actions().at(-1), "reading", "no movement starts before the choice");
  await press("repeat");
  assert.equal(actions().at(-1), "next", "Repeat returns to the rest by itself");
  assert.equal(backend.session.lift_attempts, 2);
});

test("a reader sees the step read-only and takes control in two taps while the owner is present", async () => {
  const session = { entry_id: "one", entity_id: "cover.living_one", session_id: "session-1", sequence: 9, revision: 7, mode: "geometry",
    phase: "reading", step: "half_open", reason: null, values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 }, readings: { gap: 3 },
    geometry: {}, travel_cm: 198, stop_requested: false, slats: true, lift_attempts: 1, still_resting: false, gap_warning: false,
    touching_cm: 1, max_gap_cm: 20, gap_warn_cm: 10, saved_travel_cm: 195, expected_cm: 99, can_repeat: true, save_modes: ["new"], reading_kind: "half_open" };
  const { backend, tab, wiz, code, actions } = await mount({ session, owner: false });
  const open = tab().querySelector('[data-action="cal-tab-session"]');
  open.click(); await tick(6);
  const resume = backend.subscriptions.find((message) => message.type === "myhome/cover_calibration/resume");
  assert.equal("claim" in resume, false);
  assert.equal(code(), "A-18");
  assert.equal(wiz().querySelector(".wiz-readonly .notice").textContent, "Another device is guiding this calibration.");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-action")].map((button) => button.dataset.wiz), [], "nothing moves: no Stop to offer");
  assert.equal(wiz().querySelector('.wiz-frame [name="reading_cm"]'), null, "a reader has no reading field (S-07)");
  assert.equal(wiz().querySelector(".wiz-stopwatch-label").textContent, "Control");
  assert.equal(wiz().querySelector(".wiz-stopwatch-value").textContent, "another device");
  wiz().querySelector('[data-wiz="take"]').click(); await tick();
  assert.equal(wiz().querySelector('[data-wiz="take"]').textContent, "Confirm take control");
  assert.match(wiz().querySelector(".wiz-readonly").textContent, /this device will guide the calibration/);
  assert.equal(backend.subscriptions.filter((message) => message.claim).length, 0, "the first tap sends nothing");
  wiz().querySelector('[data-wiz="take"]').click(); await tick(6);
  const claim = backend.subscriptions.filter((message) => message.claim);
  assert.equal(claim.length, 1);
  assert.equal(claim[0].sequence, 9);
  assert.equal(wiz().querySelector(".wiz-readonly"), null);
  assert.equal(wiz().querySelector('[name="reading_cm"]').disabled, false);
  assert.deepEqual(actions(), [], "taking control moves nothing");
});

test("an interruption shows its reason and Start over returns to Before you begin", async () => {
  const { backend, code, press, startFor, wiz, title } = await mount({ language: "it" });
  await startFor("cover.living_one");
  await press("begin"); await move(backend);
  backend.interrupt("unexpected_movement"); await tick();
  assert.equal(code(), "S-01");
  assert.equal(title(), translations.it.wiz_T240);
  assert.equal(wiz().querySelector(".wiz-body").textContent, translations.it.calReason_unexpected_movement);
  assert.equal(wiz().querySelector('[data-wiz="exit"]'), null, "an ended session has nothing to discard");
  await press("start-over");
  assert.equal(code(), "A-03");
  backend.interrupt("expired"); await tick();
  assert.equal(code(), "A-03", "a previous session no longer reaches the wizard");
});

test("Discard asks first, closes with Escape, and leaves only once Cancel reaches Home Assistant", async () => {
  const { backend, root, wiz, press, startFor, tab, actions } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend);
  const discard = wiz().querySelector('.wiz-head [data-wiz="exit"]');
  discard.click(); await tick();
  const dialog = wiz().querySelector(".wiz-dialog");
  assert.equal(dialog.hidden, false);
  assert.equal(dialog.querySelector("h4").textContent, "Close without saving?");
  assert.match(dialog.textContent, /A stop command is sent/);
  assert.equal(dialog.querySelector('[data-wiz="stop"]').hidden, false, "Stop sits beside Discard while it moves");
  assert.equal(root.activeElement, dialog.querySelector('[data-wiz="stay"]'));
  dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); await tick();
  assert.equal(dialog.hidden, true);
  assert.equal(root.activeElement, wiz().querySelector('.wiz-actions [data-wiz="endpoint"]'), "focus returns to the screen's confirming button, visible at every width");
  wiz().querySelector('.wiz-head [data-wiz="exit"]').click(); await tick();
  wiz().querySelector('[data-wiz="leave"]').click(); await tick(6);
  assert.equal(actions().at(-1), "cancel");
  assert.equal(wiz(), null);
  assert.ok(tab().querySelector(".cal-list"));
});

test("a cover that follows a profile saves only on itself by default, which waits for the backend", async () => {
  const overview = sampleOverview();
  const { backend, wiz, code, press, type, startFor } = await mount({ overview });
  await startFor("cover.kitchen_two");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("110");
  await press("next"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  await type("54"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await move(backend, { auto: true, stop: true }); await type("56");
  assert.equal(code(), "A-21c");
  assert.equal(wiz().querySelector('[name="save_profile"]').checked, false);
  assert.match(wiz().querySelector(".wiz-profile-block").textContent, /follows the profile "tall_two_leaf"/);
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, true);
  assert.match(wiz().querySelector(".wiz-notices").textContent, /not available yet/);
  const toggle = wiz().querySelector('[name="save_profile"]');
  toggle.checked = true; toggle.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  assert.equal(code(), "A-21d");
  assert.equal(wiz().querySelector('[name="save_choice"][value="new"]').checked, true);
  assert.match(wiz().querySelector(".wiz-profile-block").textContent, /Also changes 1 shutter: Living room shutter 3\./);
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, false);
  const name = wiz().querySelector('[name="profile_name"]');
  name.value = "bad name"; name.dispatchEvent(new Event("input", { bubbles: true })); await tick();
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, true);
  assert.equal(wiz().querySelector('[name="profile_name"]'), name, "typing never redraws the field");
  name.value = "kitchen_two"; name.dispatchEvent(new Event("input", { bubbles: true })); await tick();
  assert.match(wiz().querySelector(".wiz-name-line").textContent, /"tall_two_leaf" stays with Living room shutter 3/);
  const update = wiz().querySelector('[name="save_choice"][value="update"]');
  update.checked = true; update.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, true, "updating a shared profile waits for the unified Save");
  assert.equal(backend.calls.some((message) => message.action === "save"), false);
});

test("fine-tuning saves the calibration first, then runs as a preview that sends nothing", async () => {
  const { backend, wiz, code, press, type, actions, startFor, title } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend, { seconds: 4.4 }); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend, { seconds: 22.2 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("198");
  await press("next"); await move(backend, { seconds: 21.7 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  await type("97"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await move(backend, { auto: true, stop: true }); await type("101");
  await press("refine");
  assert.equal(backend.calls.filter((message) => message.action === "save").length, 1, "the calibration is saved before fine-tuning");
  const sent = actions().length;
  await settle();
  assert.equal(wiz().querySelector(".wiz-preview").textContent, translations.en.wizPreview);
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Fine-tuning · 7 of 8");
  assert.equal(code(), "A-23");
  assert.equal(title(), "Measure at quarter opening time");
  for (const reading of ["52", "141", "146", "48"]) { await type(reading); await settle(); }
  assert.equal(code(), "A-31");
  const expected = Number(wiz().querySelector("#wiz-field-hint").textContent.match(/About (\d+) cm/)[1]);
  await type(String(expected + 6));
  assert.equal(code(), "A-32b");
  assert.match(wiz().querySelector(".wiz-body").textContent, /Gap of about 6 cm after 8\.7 s of descent/);
  assert.equal(wiz().querySelector('[data-wiz="continue_anyway"]').classList.contains("link"), true);
  await press("repeat_check"); await settle();
  await type(String(expected + 1));
  assert.equal(code(), "A-32");
  await press("accept");
  assert.equal(code(), "A-33");
  assert.match(wiz().querySelector(".wiz-precision").textContent, /Verified accuracy: gap of about 1 cm after 8\.7 s of descent\./);
  await press("save");
  assert.equal(code(), "A-34");
  assert.ok(wiz().querySelector(".wiz-preview"), "the saved screen still says the last part was a preview");
  assert.equal(actions().length, sent, "the preview sent nothing to Home Assistant");
});

test("the profile dialog offers the new wizard next to the existing measurement", async () => {
  const { root, backend, wiz, code } = await mount();
  backend.hass.callWS = ((original) => async (message) => message.type === "myhome/cover_profiles/read"
    ? { revision: 7, profiles: [], assigned_profile_id: null, writable: true, effective_opening_time: 22, effective_closing_time: 21.7, calibration: null }
    : original(message))(backend.hass.callWS);
  root.querySelector('[data-action="cover-view"][data-id="devices"]').click(); await tick();
  root.querySelector('[data-action="cover-profile"][data-id="cover.living_one"]').click(); await tick(6);
  assert.ok(root.querySelector("#profile-calibrate"), "the existing measurement stays");
  const entry = root.querySelector("#profile-wizard");
  assert.equal(entry.textContent, "New guided measurement");
  entry.click(); await tick(10);
  assert.equal(root.querySelector(".cover-profile-dialog"), null);
  assert.equal(root.querySelector('[data-action="cover-view"][data-id="calibration"]').getAttribute("aria-pressed"), "true");
  assert.equal(code(), "A-02");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Living room shutter 1");
});

test("a reader keeps Stop while the cover may move, and nothing else", () => {
  const t = (key) => translations.en[key] || key;
  const view = { mode: "geometry", phase: "opening", step: "opening", values: {}, samples: {}, readings: {}, slats: true, read_only: true, owner: false, owner_present: true };
  const screen = buildScreen({ t, stage: "session", path: "A", view, cover: { name: "Kitchen shutter 2" } });
  assert.equal(screen.code, "A-11");
  assert.deepEqual(screen.actions.map((action) => action.id), ["stop"]);
  assert.equal(screen.readOnly.take, "Take control");
  assert.equal(screen.readOnly.primary, false, "the owner is present: taking control is not the first choice");
});

test("a check run is shown like an intermediate run, without elapsed time, then asks for its tape reading", () => {
  const t = (key) => translations.en[key] || key;
  const view = { mode: "geometry", phase: "opening", step: "check", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 },
    readings: {}, travel_cm: 110, slats: true, owner: true, sequence: 9, check: { direction: "opening", target_cm: 82.5, check_seconds: null } };
  const screen = (extra) => buildScreen({ t, stage: "session", path: "A", view: { ...view, ...extra }, elapsed: 6.4, local: { ackReadings: true }, cover: { name: "Kitchen shutter 2" } });
  const running = screen({});
  assert.equal(running.code, "A-30");
  assert.equal(running.stopwatch, null, "Home Assistant stops the check run: no elapsed time");
  assert.equal(running.illustration, null, "a wait has no drawing");
  assert.deepEqual(running.actions.map((action) => action.id), ["stop"]);
  assert.deepEqual(screen({ phase: "briefing" }).actions.map((action) => action.id), ["next", "stop"]);
  assert.equal(screen({ phase: "geometry_wait_stop" }).stopwatch, null);
  const reading = screen({ phase: "reading", reading_kind: "check" });
  assert.equal(reading.code, "A-31");
  assert.equal(reading.title, "Check the roller shutter");
  assert.deepEqual([reading.field.min, reading.field.max], [0.1, 110]);
  assert.match(reading.field.hint, /^About 83 cm expected/);
  assert.deepEqual(reading.actions.map((action) => action.id), ["reading", "repeat"]);
});

test("an intermediate reading names its accepted range in Italian with a decimal comma, and a refusal names the reading", () => {
  const t = (key) => translations.it[key] || key;
  const view = { mode: "geometry", phase: "reading", step: "half_close", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 },
    readings: { gap: 3 }, geometry: { slat_time_s: 4 }, travel_cm: 110, slats: true, owner: true, sequence: 3, reading_range: { min_cm: 40.83, max_cm: 60.63 } };
  const screen = buildScreen({ t, language: "it", stage: "session", path: "A", view, cover: { name: "Cucina 2" },
    status: { error: { code: "reading_out_of_range", reading: 70.5 } } });
  assert.equal(screen.code, "A-20");
  assert.equal(screen.field.hint, "Per questa tapparella la lettura attesa è fra 40,9 e 60,6 cm. Scrivi quello che dice il metro.");
  assert.match(screen.notices[0].text, /^La lettura \(70,5 cm\) è fuori dall’intervallo ammesso \(40,9–60,6 cm\)/);
  assert.equal(screen.stopwatch, null, "no time is shown for a reading");
  const running = buildScreen({ t, language: "it", stage: "session", path: "A", view: { ...view, phase: "closing", reading_range: null }, elapsed: 3.2,
    local: { ackReadings: true }, cover: { name: "Cucina 2" } });
  assert.equal(running.code, "A-19");
  assert.equal(running.stopwatch, null, "an intermediate run shows no elapsed time: Home Assistant stops it");
});

test("each mockup gets its drawing by code: readings after the text, steps and briefings before it, none elsewhere", () => {
  const t = (key) => translations.en[key] || key;
  const base = { mode: "geometry", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 }, readings: { gap: 3 },
    geometry: { slat_time_s: 4 }, travel_cm: 110, slats: true, owner: true, sequence: 4 };
  const drawn = (view, local = {}, path = "A") => {
    const screen = buildScreen({ t, stage: "session", path, scope: path === "C" ? "times_and_rolls" : null, view: { ...base, ...view }, local,
      elapsed: 2, cover: { name: "Kitchen shutter 2" } });
    return [screen.code, screen.illustration && `${screen.illustration.id} ${screen.illustration.position}`];
  };
  assert.deepEqual(drawn({ step: "home", phase: "closing" }), ["A-05", "window-closed before-body"]);
  assert.deepEqual(drawn({ step: "lift", phase: "briefing" }), ["A-06", "two-runs before-body"]);
  assert.deepEqual(drawn({ step: "lift", phase: "briefing" }, { ackLift: true }), ["A-07", "lift-sequence before-body"]);
  assert.deepEqual(drawn({ step: "lift", phase: "reading", reading_kind: "lift" }), ["A-08", "lift-zoom after-body"]);
  assert.deepEqual(drawn({ step: "reset", phase: "starting_close" }), ["A-09", "descent-sequence before-body"]);
  assert.deepEqual(drawn({ step: "reset", phase: "closing" }), ["A-10", null]);
  assert.deepEqual(drawn({ step: "opening", phase: "opening" }), ["A-11", "ascent-sequence before-body"]);
  assert.deepEqual(drawn({ step: "opening", phase: "reading" }), ["A-12", null]);
  assert.deepEqual(drawn({ step: "opening", phase: "reading" }, { ackAscent: true }), ["A-13", "curtain-open-tape after-body"]);
  assert.deepEqual(drawn({ step: "closing", phase: "closing" }), ["A-14", "descent-sequence before-body"]);
  assert.deepEqual(drawn({ step: "half_open", phase: "briefing" }), ["A-15", null]);
  assert.deepEqual(drawn({ step: "half_open", phase: "briefing" }, { ackDescent: true }), ["A-16", "curtain-open-tape before-body"]);
  assert.deepEqual(drawn({ step: "half_open", phase: "opening" }, { ackDescent: true, ackReadings: true }), ["A-17", null]);
  assert.deepEqual(drawn({ step: "half_open", phase: "reading" }, { ackDescent: true, ackReadings: true }), ["A-18", "curtain-partial-tape after-body"]);
  assert.deepEqual(drawn({ step: "top", phase: "opening" }, { ackReadings: true }), ["A-19", null]);
  assert.deepEqual(drawn({ step: "top", phase: "opening" }), ["A-09", null], "the return to the top is not the descent drawing");
  assert.deepEqual(drawn({ step: "half_close", phase: "reading" }, { ackReadings: true }), ["A-20", "curtain-partial-tape after-body"]);
  assert.deepEqual(drawn({ step: "closing", phase: "closing" }, {}, "C"), ["C-14", "descent-sequence before-body"], "clones follow their A screen");
  assert.deepEqual(drawn({ phase: "review" }), ["A-21", null]);
});

test("the drawing is one figure sized as in Figma, placed by its position, and gone where the mockup has none", async () => {
  const { ILLUSTRATIONS } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-illustration.js");
  assert.deepEqual(Object.keys(ILLUSTRATIONS).sort(), ["ascent-sequence", "check", "curtain-open-tape", "curtain-partial-tape", "descent-sequence",
    "lift-sequence", "lift-zoom", "two-runs", "window-closed"]);
  assert.ok(Object.values(ILLUSTRATIONS).every((size) => size.width <= 564), "never wider than the instruction column");
  const { backend, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  await move(backend);
  assert.equal(code(), "A-05");
  const figure = wiz().querySelector(".wiz-main .wiz-illustration");
  assert.equal(figure.dataset.illustration, "window-closed");
  assert.equal(figure.getAttribute("role"), "img");
  assert.equal(figure.getAttribute("aria-label"), "Step diagram");
  assert.match(figure.getAttribute("style"), /--wiz-illustration-width: 260px/);
  assert.equal(figure.nextElementSibling.className, "wiz-body", "a step shows its drawing above the text");
  assert.equal(wiz().querySelector(".wiz-frame .cal-visual"), null, "the maintainer's small scene is not used by the wizard");
});

test("every wait has its bar: the time left when the duration is known, moving back and forth when it is not", async () => {
  const t = (key) => translations.it[key] || key;
  const view = { mode: "geometry", step: "home", phase: "starting_close", values: {}, samples: {}, readings: {}, slats: true, owner: true, sequence: 1 };
  const wait = (cover, extra = {}, elapsed = null, local = {}) => buildScreen({ t, language: "it", stage: "session", path: "A", view: { ...view, ...extra },
    elapsed, local, cover: { name: "Cucina 2", ...cover } }).wait;
  const never = wait({ effective: { closing: { value: 30, origin: "default" } } });
  assert.deepEqual(never.progress, { value: null, remaining: null }, "a default time is only a guess: indeterminate");
  assert.equal(never.remaining, "");
  const known = wait({ effective: { closing: { value: 21.7, origin: "native_fallback" } } });
  assert.deepEqual(known.progress, { value: 0, remaining: 22 });
  assert.equal(known.remaining, "Tempo residuo circa 22 s");
  // A-19, second leg: 3 s into a half descent of (21 - 4) / 2 s.
  const half = wait({}, { step: "half_close", phase: "closing", values: { opening_time: 22, closing_time: 21 }, geometry: { slat_time_s: 4 } }, 3, { ackReadings: true });
  assert.equal(half.stages[0].state, "done");
  assert.equal(Math.round(half.progress.value * 100), 35);
  assert.equal(half.remaining, "Tempo residuo circa 6 s");
  // A-19, first leg: the return to the top lasts the measured opening time.
  assert.equal(wait({}, { step: "top", phase: "briefing", values: { opening_time: 22, closing_time: 21 } }, null, { ackReadings: true }).remaining, "Tempo residuo circa 22 s");

  const { backend, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  assert.equal(code(), "A-04");
  assert.equal(wiz().querySelector(".wiz-progress").classList.contains("is-indeterminate"), false);
  assert.equal(wiz().querySelector(".wiz-wait-remaining").textContent, "About 22 s remaining");
  assert.equal(backend.calls.length > 0, true);
});

test("screens carry no placeholder or key in either language", () => {
  const view = { mode: "geometry", phase: "reading", step: "half_open", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 },
    readings: { gap: 3 }, geometry: {}, travel_cm: 198, expected_cm: 99, slats: true, owner: true, sequence: 1 };
  for (const language of ["en", "it"]) {
    const t = (key) => translations[language][key] || translations.en[key] || key;
    const cover = { name: "Kitchen shutter 2", address: "Address: 91", effective: { opening: { value: 12 }, closing: { value: 12 } }, travel_cm: 110,
      profile: { name: "tall_two_leaf", assigned_to: [] }, followers: ["Living room shutter 3"] };
    const contexts = [
      { stage: "choose", covers: [{ key: "k", label: "Kitchen shutter 2" }] }, { stage: "path", profiles: [{ id: "p" }] }, { stage: "before" },
      { stage: "profile", path: "B", profiles: [{ id: "tall", name: "tall_two_leaf", followers: 2, measuredOn: "Living room shutter 1" }] },
      { stage: "current", path: "C" }, { stage: "case", path: "C" }, { stage: "before", path: "C", scope: "times_only" },
      { stage: "before", path: "C", scope: "points_only" }, { stage: "session", view },
      { stage: "session", view: { ...view, phase: "review" }, followerNames: "Living room shutter 3", local: { saveProfile: true } },
      { stage: "saved", local: { saved: { target: "profile_new", name: "kitchen" } } },
    ];
    for (const extra of contexts) {
      const screen = buildScreen({ t, language, path: "A", cover, ...extra });
      const textOf = JSON.stringify(screen);
      assert.doesNotMatch(textOf, /\{(cover|profile|name|seconds|cm|gap|count|names|travel|run|slat|phase|n|total)\}/, `${language} ${screen.code}`);
      assert.doesNotMatch(textOf, /"wiz_?T?\w*"|calTab\w+/, `${language} ${screen.code} shows a key`);
    }
  }
});

test("the keyboard reaches every step: title focus, Steps sheet, and a dialog that keeps Tab inside", async () => {
  const { root, wiz, press, startFor, backend } = await mount();
  await startFor("cover.living_one");
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(root.activeElement, wiz().querySelector(".wiz-title"), "a new step moves focus to its title");
  wiz().querySelector('[data-wiz="steps"]').click(); await tick();
  const sheet = wiz().querySelector(".wiz-sheet");
  assert.equal(sheet.hidden, false);
  assert.equal(root.activeElement, sheet.querySelector('[data-wiz="steps-close"]'));
  assert.equal(sheet.querySelector('[aria-current="step"] .wiz-step-label').textContent, "Preparation");
  sheet.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.equal(sheet.hidden, true);
  assert.equal(root.activeElement, wiz().querySelector('[data-wiz="steps"]'));
  await press("begin"); await move(backend);
  wiz().querySelector('.wiz-head [data-wiz="exit"]').click(); await tick();
  const dialog = wiz().querySelector(".wiz-dialog");
  const buttons = [...dialog.querySelectorAll("button:not([hidden])")];
  assert.deepEqual(buttons.map((button) => button.dataset.wiz), ["stay", "leave", "stop"]);
  buttons.at(-1).focus();
  dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
  assert.equal(root.activeElement, buttons[0], "Tab wraps to the first button");
  dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true }));
  assert.equal(root.activeElement, buttons.at(-1), "Shift+Tab wraps to the last one");
  buttons.at(-1).click(); await tick();
  assert.equal(dialog.hidden, true, "Stop from the dialog closes it and keeps the wizard");
  assert.equal(backend.calls.filter((message) => message.action === "stop").length, 1);
});

test("a half run that did not start by itself can be started from its screen, and fine-tuning starts over as a preview", async () => {
  const t = (key) => translations.en[key] || key;
  const view = { mode: "geometry", phase: "briefing", step: "half_open", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 },
    readings: { gap: 3 }, geometry: {}, travel_cm: 198, slats: true, owner: true, sequence: 4 };
  const screen = buildScreen({ t, stage: "session", path: "A", view, local: { ackDescent: true, ackReadings: true }, cover: { name: "Living room shutter 1" } });
  assert.equal(screen.code, "A-17");
  assert.deepEqual(screen.actions.map((action) => action.id), ["next", "stop"]);
  const { wiz, code, press, startFor, backend, type } = await mount({ stageMs: 30 });
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend, { seconds: 4.4 }); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend, { seconds: 22.2 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("198");
  await press("next"); await move(backend, { seconds: 21.7 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  await type("97"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await move(backend, { auto: true, stop: true }); await type("101");
  await press("refine");
  assert.equal(code(), "A-22");
  await press("stop");
  assert.equal(code(), "S-01");
  await press("start-over");
  assert.equal(code(), "A-22", "fine-tuning starts over from the saved values, still as a preview");
  assert.ok(wiz().querySelector(".wiz-preview"));
  assert.equal(backend.calls.filter((message) => message.action === "save").length, 1);
});

const resumed = (extra) => ({ entry_id: "one", entity_id: "cover.living_one", session_id: "session-1", sequence: 9, revision: 7, mode: "geometry",
  reason: null, values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 }, readings: { gap: 3 },
  geometry: {}, travel_cm: 198, stop_requested: false, slats: true, lift_attempts: 1, still_resting: false, gap_warning: false,
  touching_cm: 1, max_gap_cm: 20, gap_warn_cm: 10, saved_travel_cm: 195, expected_cm: 99, can_repeat: true, save_modes: ["new"], ...extra });

test("a refused press is not sent again by itself and its error stays on screen", async () => {
  const { backend, tab, wiz, code, press, actions } = await mount({ session: resumed({ phase: "briefing", step: "half_open", reading_kind: "half_open" }) });
  tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(6);
  assert.equal(code(), "A-15");
  await press("ack:descent");
  const original = backend.hass.callWS;
  let refused = false;
  backend.hass.callWS = async (message) => {
    if (message.action === "next" && !refused) { refused = true; backend.calls.push(message); throw Object.assign(new Error("busy"), { code: "cover_unavailable" }); }
    return original(message);
  };
  await press("ack:readings"); await tick(6);
  assert.deepEqual(actions(), ["next"], "one press, one message");
  assert.equal(wiz().querySelector(".wiz-notices").textContent, translations.en.profileError_cover_unavailable);
  assert.equal(code(), "A-17");
  assert.equal(wiz().querySelector('[data-wiz="next"]').disabled, false, "the run can be started again by hand");
});

test("taking control moves nothing, even on a step the wizard would otherwise continue by itself", async () => {
  const { backend, tab, wiz, code, type, actions } = await mount({ session: resumed({ phase: "reading", step: "half_open", reading_kind: "half_open" }) });
  tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(6);
  await type("99"); await tick(6);
  assert.deepEqual(actions(), ["reading", "next"]);
  // Another device takes the session and leaves it before the return to the top.
  backend.session.phase = "briefing"; backend.session.step = "top";
  const view = backend.view;
  backend.view = (extra = {}) => view({ owner: false, read_only: true, ...extra });
  backend.emit(); await tick(6);
  assert.ok(wiz().querySelector(".wiz-readonly"));
  backend.view = view;
  wiz().querySelector('[data-wiz="take"]').click(); await tick();
  wiz().querySelector('[data-wiz="take"]').click(); await tick(8);
  assert.equal(wiz().querySelector(".wiz-readonly"), null);
  assert.deepEqual(actions(), ["reading", "next"], "nothing after the claim");
  assert.equal(code(), "A-09", "a reopened session shows the return to the top as a positioning to start by hand");
  assert.equal(wiz().querySelector('[data-wiz="next"]').disabled, false);
});

test("the screen behind an open Discard dialog is not rebuilt until the dialog closes", async () => {
  const { backend, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend);
  assert.equal(code(), "A-05");
  wiz().querySelector('.wiz-head [data-wiz="exit"]').click(); await tick();
  const stay = wiz().querySelector('[data-wiz="stay"]');
  backend.interrupt("unexpected_movement"); await tick();
  assert.equal(wiz().querySelector('[data-wiz="stay"]'), stay, "the dialog stays where the user is about to tap");
  stay.click(); await tick();
  assert.equal(code(), "S-01");
});

test("a subscription replayed after a reconnection never starts a movement, even on a step that would continue by itself", async () => {
  const { backend, wiz, code, press, type, actions, startFor } = await mount();
  const callbacks = [];
  const subscribe = backend.hass.connection.subscribeMessage;
  backend.hass.connection.subscribeMessage = async (callback, message) => { callbacks.push(callback); return subscribe(callback, message); };
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend, { seconds: 4 }); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend, { seconds: 22 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("198");
  await press("next"); await move(backend, { seconds: 21 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  await type("97");
  assert.equal(code(), "A-19");
  await move(backend);
  await press("endpoint");
  // The socket drops: the cover stops and the session moves on with nobody listening.
  const emit = backend.emit;
  backend.emit = () => { backend.session.sequence += 1; };
  backend.stopped();
  backend.emit = emit;
  assert.equal(backend.session.step, "half_close");
  const before = actions().length;
  // Home Assistant reconnects and replays the subscription: same sequence, a new attachment.
  callbacks.at(-1)(backend.view({ attachment: "attachment-2" }));
  await tick(8);
  assert.deepEqual(actions().slice(before), [], "no movement after a replay");
  assert.equal(code(), "A-19");
  assert.equal(wiz().querySelector('[data-wiz="next"]').disabled, false, "the run waits for a press");
});

test("after every change of screen the confirming buttons wait 700 ms, Stop never does", async () => {
  const { backend, tab, wiz, code } = await mount({ guardMs: 700 });
  const { CONFIRM_GUARD_MS } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-wizard.js");
  assert.equal(CONFIRM_GUARD_MS, 700);
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const button = (id) => wiz().querySelector(`.wiz-actions [data-wiz="${id}"]`);
  const tap = async (id) => { await wait(720); assert.equal(button(id).disabled, false, id); button(id).click(); await tick(); };
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.equal(button("choose").disabled, true, "a tap landing right after the change does nothing");
  button("choose").click(); await tick();
  assert.equal(code(), "A-01");
  const select = wiz().querySelector('select[name="cover"]');
  select.value = JSON.stringify(["one", "cover.living_one"]); select.dispatchEvent(new Event("change", { bubbles: true }));
  await tap("choose");
  const a = wiz().querySelector('input[name="path"][value="A"]'); a.checked = true; a.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  await tap("path"); await tap("begin");
  await move(backend);
  assert.equal(code(), "A-05");
  assert.equal(button("endpoint").disabled, true, "an end stop is never confirmed by the tap that started the run");
  assert.equal(button("stop").disabled, false, "Stop is always available");
  await tap("endpoint");
  assert.equal(backend.calls.filter((message) => message.action === "endpoint").length, 1);
});

test("a reopened slat and roll session of a cover that follows a profile is shown as path C", async () => {
  const session = { entry_id: "one", entity_id: "cover.kitchen_two", session_id: "session-1", sequence: 9, revision: 7, mode: "geometry",
    phase: "briefing", step: "lift", reason: null, values: {}, samples: {}, readings: {}, geometry: {}, travel_cm: null, stop_requested: false,
    slats: true, lift_attempts: 1, still_resting: false, gap_warning: false, touching_cm: 1, max_gap_cm: 20, gap_warn_cm: 10,
    saved_travel_cm: 110, expected_cm: null, can_repeat: false, save_modes: ["new"], reading_kind: "lift" };
  const { backend, tab, wiz, code, actions } = await mount({ session });
  tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(6);
  assert.equal(code(), "C-06");
  assert.equal(wiz().querySelector(".wiz-steps-caption").textContent, "Ⓒ remeasure all");
  assert.deepEqual(actions(), [], "reopening moves nothing");
  void backend;
});

test("the preview is announced before it starts and its end never says that something was saved", async () => {
  const t = (key) => translations.it[key] || key;
  const screen = buildScreen({ t, language: "it", stage: "path", path: "A", profiles: [{ id: "tall" }], cover: { name: "Cucina 2" } });
  assert.equal(screen.choice.options.find((option) => option.value === "B").note,
    "Anteprima: questo percorso non è ancora collegato al backend, nessun movimento e nessun salvataggio.");
  assert.equal(buildScreen({ t, stage: "before", path: "B", cover: { name: "Cucina 2" } }).actions[0].note, translations.it.wiz_T318);
  assert.equal(buildScreen({ t, stage: "before", path: "C", scope: "points_only", cover: { name: "Cucina 2" } }).actions[0].note, translations.it.wiz_T318);
  assert.equal(buildScreen({ t, stage: "before", path: "C", scope: "times_only", cover: { name: "Cucina 2" } }).actions[0].note, undefined, "times only is live");
  const review = buildScreen({ t, language: "it", stage: "session", path: "A", cover: { name: "Cucina 2" },
    view: { mode: "geometry", phase: "review", values: { opening_time: 22, closing_time: 21 }, geometry: {}, travel_cm: 198, owner: true, sequence: 2 } });
  assert.equal(review.actions.find((action) => action.id === "refine").note, translations.it.wiz_T319);
  const saved = buildScreen({ t, language: "it", stage: "saved", path: "A", cover: { name: "Cucina 2" }, local: { saved: { preview: true }, baseSaved: true, refining: true } });
  assert.equal(saved.title, "Anteprima del riepilogo");
  assert.equal(saved.body, translations.it.wiz_T322);
  assert.equal(saved.preview, true);
  // On screen the note sits under its path, inside the radio's label.
  const { tab, wiz, press, pickCover } = await mount({ language: "it" });
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  await pickCover();
  await press("choose");
  const b = wiz().querySelector('input[name="path"][value="B"]').closest(".wiz-radio");
  assert.equal(b.querySelector("small").textContent, translations.it.wiz_T318);
});

test("A-02 advises a path from the cover and the gateway's profiles, and preselects it", () => {
  const t = (key) => translations.en[key] || key;
  const advice = (screen) => screen.choice.options.filter((option) => option.badge).map((option) => [option.value, option.badge]);
  // Never measured, no profile on the gateway: A is advised, B cannot be chosen and says why.
  const none = buildScreen({ t, stage: "path", profiles: [], cover: { name: "Kitchen 2", status: "to_measure" } });
  assert.deepEqual(advice(none), [["A", "Recommended"]]);
  const b = none.choice.options.find((option) => option.value === "B");
  assert.equal(b.disabled, true);
  assert.equal(b.note, translations.en.wiz_T401);
  assert.equal(none.choice.value, "A");
  assert.equal(none.actions[0].id, "path");
  assert.equal(none.actions[0].label, "Continue");
  assert.equal(none.actions[0].disabled, false);
  assert.equal(none.subline, "Never measured · no profile available");
  assert.doesNotMatch(none.body, /If unsure/);
  // Never measured, profiles available: B is advised; a choice of A brings the fallback line back.
  const some = buildScreen({ t, stage: "path", profiles: [{ id: "tall" }, { id: "short" }], cover: { name: "Kitchen 2", status: "to_measure" } });
  assert.deepEqual(advice(some), [["B", "Recommended"]]);
  assert.equal(some.choice.value, "B");
  assert.equal(some.subline, "Never measured · 2 profiles available");
  const picked = buildScreen({ t, stage: "path", local: { pathChoice: "A" }, profiles: [{ id: "tall" }], cover: { name: "Kitchen 2", status: "to_measure" } });
  assert.equal(picked.choice.value, "A");
  assert.equal(picked.subline, "Never measured · 1 profile available");
  assert.match(picked.body, /If unsure, choose Ⓐ\.$/);
});

test("counts of zero and one use their own forms", () => {
  const t = (key) => translations.it[key] || key;
  const view = { mode: "geometry", phase: "review", values: { opening_time: 22, closing_time: 21 }, geometry: {}, travel_cm: 110, owner: true, sequence: 2 };
  const cover = (followers) => ({ name: "Cucina 2", profile: { name: "alte" }, followers, effective: {} });
  const review = (followers, local = {}) => buildScreen({ t, language: "it", stage: "session", path: "C", scope: "times_only", cover: cover(followers),
    view: { ...view, mode: "guided" }, local });
  assert.match(review([]).saveInfo.body, /Il profilo «alte» non cambierà\.\n/);
  assert.match(review(["Sala 3"]).saveInfo.body, /e l’altra tapparella che lo segue resterà com’è\./);
  assert.match(review(["Sala 2", "Sala 3"]).saveInfo.body, /e le altre 2 tapparelle che lo seguono resteranno come sono\./);
  const a21d = (followers) => buildScreen({ t, language: "it", stage: "session", path: "A", cover: cover(followers), view, local: { saveProfile: true },
    followerNames: followers.join(" e ") }).profileBlock;
  assert.equal(a21d([]).choice.options[1].description, "Nessun’altra tapparella lo segue.");
  assert.equal(a21d([]).name.line, "Questa tapparella passa a seguirlo; nessun’altra tapparella segue «alte».");
  assert.equal(a21d(["Sala 3"]).choice.options[1].description, "Cambia anche l’altra tapparella che lo segue: Sala 3.");
  const b01 = (followers) => buildScreen({ t, stage: "profile", path: "B", cover: cover([]), local: {}, profiles: [{ id: "p", name: "alte", followers, measuredOn: "Sala 1" }] }).choice.hint;
  assert.equal(b01(0), "Misurato su Sala 1 · nessuna tapparella lo segue");
  assert.equal(b01(1), "Misurato su Sala 1 · 1 tapparella lo segue");
  assert.equal(b01(3), "Misurato su Sala 1 · 3 tapparelle lo seguono");
});

test("a refusal is forgotten once the session moves to another phase", async () => {
  const { backend, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend);
  const original = backend.hass.callWS;
  backend.hass.callWS = async (message) => message.action === "endpoint"
    ? (backend.calls.push(message), Promise.reject(Object.assign(new Error("range"), { code: "reading_out_of_range" }))) : original(message);
  await press("endpoint"); await tick(4);
  backend.interrupt("unexpected_movement"); await tick(4);
  assert.equal(code(), "S-01");
  assert.doesNotMatch(wiz().textContent, /\{\w+\}/, "no empty placeholder after the phase changed");
  assert.equal(wiz().querySelector(".wiz-notices").textContent, "");
});

test("the second tap of Take control is held back too, so a double click cannot skip the confirmation", async () => {
  const session = resumed({ phase: "reading", step: "half_open", reading_kind: "half_open" });
  const { backend, tab, wiz } = await mount({ session, owner: false, guardMs: 700 });
  tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(6);
  await new Promise((resolve) => setTimeout(resolve, 720));
  const take = () => wiz().querySelector('[data-wiz="take"]');
  take().click(); await tick();
  assert.equal(take().textContent, "Confirm take control");
  assert.equal(take().disabled, true);
  take().click(); await tick();
  assert.equal(backend.subscriptions.filter((message) => message.claim).length, 0, "a double click does not claim");
  await new Promise((resolve) => setTimeout(resolve, 720));
  assert.equal(take().disabled, false);
});

test("the panel's entity states never overwrite the wizard's stepper", async () => {
  const { panel, wiz, startFor } = await mount();
  await startFor("cover.living_one");
  const labels = () => [...wiz().querySelectorAll(".wiz-steps .wiz-step-label")].map((item) => item.textContent);
  const before = labels();
  assert.deepEqual(before, ["Introduction", "Preparation", "Ascent", "Descent", "Tape measure readings", "Summary", "Fine-tuning (optional)"]);
  // Home Assistant pushes a state update: the panel refreshes every [data-state] element it owns.
  panel.hass = { ...panel.hass, states: { ...panel.hass.states } };
  assert.deepEqual(labels(), before);
  assert.equal(wiz().querySelector("[data-state]"), null, "no element of the wizard uses the panel's state attribute");
});

test("the drop-down names the bus address with the Italian label too", async () => {
  const { tab, wiz, pickCover } = await mount({ language: "it" });
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.equal(wiz().querySelector('select[name="cover"] option').textContent, "Scegli una tapparella…");
  assert.equal(wiz().querySelector('select[name="cover"] option:not([disabled])').textContent, "Kitchen shutter 2 · Kitchen · Indirizzo: 91 · A: 9 · PL: 1 · Tempi e rullo, 29 set");
  await pickCover(0);
  assert.equal(wiz().querySelector(".wiz-choice-note").textContent,
    "Questa tapparella è già calibrata (tempi e rullo, 29 set 2026). Una nuova misurazione sostituisce i valori in uso; per ritoccarli usa il perfezionamento.");
});

test("opened on a given cover, the wizard already has it chosen; from the tab's button it starts empty", async () => {
  const { panel, tab, wiz, code, button } = await mount();
  // From a row: Measure goes straight to the path choice on that cover.
  tab().querySelector('.cal-row[data-entity="cover.living_one"] [data-action="cal-tab-measure-cover"]').click(); await tick();
  assert.equal(code(), "A-02");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Living room shutter 1");
  button("exit").click(); await tick();
  // Back on A-01 with a given cover (as after a cover-specific entry), the drop-down sits on it and the subtitle names it.
  const tabView = panel._calibrationTab;
  tabView._openWizard({ start: "choose", item: tabView._covers().find((item) => item.cover.entity_id === "cover.living_three") }); await tick();
  assert.equal(code(), "A-01");
  assert.equal(wiz().querySelector('select[name="cover"]').value, JSON.stringify(["one", "cover.living_three"]));
  assert.equal(wiz().querySelector('select[name="cover"] option[disabled]'), null, "no placeholder entry");
  assert.equal(wiz().querySelector(".wiz-head .muted").textContent, "Living room shutter 3 · Living room · Address: 91 · A: 9 · PL: 1");
  assert.equal(button("choose").disabled, false);
});
