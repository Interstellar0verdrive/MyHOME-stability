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
  const { tab, wiz, code, press, title, backend, button } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.equal(code(), "A-01");
  assert.equal(title(), "Which roller shutter do you want to measure?");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Measure a roller shutter");
  assert.match(wiz().querySelector(".wiz-body").innerHTML, /<strong>from travel times<\/strong>/);
  const options = [...wiz().querySelectorAll('select[name="cover"] option')].map((option) => option.textContent);
  assert.deepEqual(options, ["Kitchen shutter 2", "Living room shutter 1", "Living room shutter 3"]);
  await press("choose");
  assert.equal(code(), "A-02");
  assert.equal(title(), 'How to measure "Kitchen shutter 2"?');
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Kitchen shutter 2");
  assert.match(wiz().querySelector(".wiz-head .muted").textContent, /Address: 91 · A: 9 · PL: 1 · WHO 2/);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-action")].map((item) => item.textContent), ["Ⓐ  First roller shutter of this type", "Ⓑ  Like one already measured", "Ⓒ  Has a profile, but stops at the wrong point"]);
  await press("path:A");
  assert.equal(code(), "A-03");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Preparation · 2 of 7");
  assert.equal(wiz().querySelector('.wiz-steps li[data-state="current"] .wiz-step-label').textContent, "Preparation");
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
  assert.match(wiz().querySelector("#wiz-field-hint").textContent, /^About 99 cm expected/);
  await type("97");
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
  assert.equal(wiz().querySelector('[name="reading_cm"]').disabled, true);
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
  assert.equal(root.activeElement, wiz().querySelector('.wiz-head [data-wiz="exit"]'));
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
  assert.match(wiz().querySelector(".wiz-profile-block").textContent, /Also changes 1 shutters: Living room shutter 3\./);
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
