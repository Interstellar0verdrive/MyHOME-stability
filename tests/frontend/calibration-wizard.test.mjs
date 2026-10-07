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

test("the summaries speak of leaving the calibration, never of a window", () => {
  for (const [language, phrase, stop] of [["it", "Se abbandoni la calibrazione senza salvare, i valori attualmente in uso resteranno invariati.", "Se preferisci fermarti qui, abbandona la calibrazione: **niente è ancora stato salvato**."],
    ["en", "If you leave the calibration without saving, the values currently in use will stay unchanged.", "If you prefer to stop here, discard the calibration: **nothing has been saved yet**."]]) {
    const texts = Object.entries(translations[language]).filter(([key]) => key.startsWith("wiz"));
    // The window of the house (the base the closed cover rests on, G2-8) is not a window of the interface.
    assert.deepEqual(texts.filter(([, value]) => /finestra|the window/.test(value.replace(/base della finestra|the window base/g, ""))).map(([key]) => key), [], `${language}: no window`);
    for (const key of ["wiz_T281", "wiz_T289", "wiz_T310", "wiz_T317", "wizSaveCoverOnly"]) assert.ok(translations[language][key].endsWith(phrase), `${language} ${key}`);
    assert.ok(translations[language].wiz_T176.endsWith(stop), `${language} T176`);
  }
});

test("A-01 to A-03 stay in the browser: choosing a cover and a path sends nothing", async () => {
  const { tab, wiz, code, press, title, backend, button, pickCover, choosePath } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.equal(code(), "A-01");
  assert.equal(title(), "Which cover do you want to calibrate?");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Calibrate a cover");
  assert.match(wiz().querySelector(".wiz-body").innerHTML, /<strong>from travel times<\/strong>/);
  // The covers as the sequence view's rows, one radio each: name, room and address, status, profile.
  assert.equal(wiz().querySelector('select[name="cover"]'), null, "no drop-down");
  const rows = () => [...wiz().querySelectorAll(".wiz-picker .wiz-pick-row")];
  assert.deepEqual(rows().map((row) => [row.querySelector(".cal-row-name strong").textContent, row.querySelector(".cal-row-name .muted").textContent,
    row.querySelector(".cal-badge").textContent, row.querySelector(".cal-batch-profile").textContent.trim()]), [
    ["Kitchen shutter 2", "Kitchen · Address: 91 · A: 9 · PL: 1", "Calibrated (times and roll)", "tall_two_leaf"],
    ["Living room shutter 1", "Living room · Address: 91 · A: 9 · PL: 1", "To calibrate", "—"],
    ["Living room shutter 3", "Living room · Address: 91 · A: 9 · PL: 1", "Calibrated (times)", "tall_two_leaf"]]);
  assert.equal(wiz().querySelector(".wiz-picker [role=radiogroup]").getAttribute("aria-label"), "Cover to calibrate");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-pick-chips .cal-chip")].map((chip) => chip.textContent.replace(/\s+/g, " ").trim()),
    ["All 3", "To calibrate 1", "Calibrated 2", "With profile 2"], "the list's filter chips");
  assert.equal(wiz().querySelectorAll('.wiz-picker input[name="cover"]:checked').length, 0, "opened from the tab's button, nothing is chosen");
  assert.equal(wiz().querySelector(".wiz-pick-notes"), null, "no note before a choice");
  const subtitle = () => wiz().querySelector(".wiz-head .muted");
  assert.equal(subtitle().textContent, "No cover selected yet", "a placeholder until a cover is picked");
  assert.ok(subtitle().classList.contains("wiz-head-placeholder"));
  assert.equal(button("choose").disabled, true, "Continue waits for a choice");
  await pickCover("cover.living_one");
  assert.equal(subtitle().textContent, "Living room · Address: 91 · A: 9 · PL: 1", "the picked cover's room and address, its name only in its row");
  assert.deepEqual([...subtitle().children].map((unit) => [unit.className, unit.textContent]), [["cal-row-unit", "Living room ·"], ["cal-row-address", "Address: 91 · A: 9 · PL: 1"]],
    "units that wrap only between them (responsive map §3.3)");
  assert.equal(subtitle().classList.contains("wiz-head-placeholder"), false);
  assert.equal(wiz().querySelector(".wiz-pick-row.is-selected").dataset.entity, "cover.living_one");
  assert.equal(wiz().querySelector(".wiz-pick-notes"), null, "a never measured cover without a profile has no note");
  assert.equal(wiz().querySelector('.wiz-picker input[name="cover"]:checked').value, JSON.stringify(["one", "cover.living_one"]), "the choice survives the redraw");
  assert.equal(button("choose").disabled, false);
  // Filters and order act on the list only; the choice stays.
  wiz().querySelector('[data-wiz="pick-filter:calibrated"]').click(); await tick();
  assert.deepEqual(rows().map((row) => row.dataset.entity), ["cover.kitchen_two", "cover.living_three"]);
  assert.equal(button("choose").disabled, false, "a chosen cover hidden by a filter stays chosen");
  wiz().querySelector('[data-wiz="pick-filter:all"]').click(); await tick();
  // Cards at every width (responsive map): no column headers; one Sort by control gives the list's orders.
  assert.equal(wiz().querySelector(".wiz-picker .cal-list-head"), null, "no table headers in the wizard");
  const sortBy = (value) => { const select = wiz().querySelector('.wiz-picker select[data-pick-sort="order"]'); select.value = value; select.dispatchEvent(new Event("change", { bubbles: true })); };
  sortBy("status:asc"); await tick();
  assert.deepEqual(rows().map((row) => row.dataset.entity), ["cover.living_one", "cover.living_three", "cover.kitchen_two"], "sorted by status, as the list");
  // P-3: the list's own bar; its narrow filter drop-down filters as the chips do.
  assert.deepEqual([...wiz().querySelectorAll(".wiz-picker .cal-filterbar-row > *")].map((part) => part.classList[0]), ["cal-tab-chips", "cal-tab-compact"]);
  const pickFilter = wiz().querySelector(".wiz-picker select[data-pick-filter]");
  pickFilter.value = "calibrated"; pickFilter.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  assert.deepEqual(rows().map((row) => row.dataset.entity), ["cover.living_three", "cover.kitchen_two"]);
  assert.equal(wiz().querySelector('.wiz-pick-chips [data-wiz="pick-filter:calibrated"]').getAttribute("aria-pressed"), "true", "the chips follow");
  const back = wiz().querySelector(".wiz-picker select[data-pick-filter]");
  back.value = "all"; back.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  const phoneSort = wiz().querySelector('.wiz-picker select[data-pick-sort="order"]');
  phoneSort.value = "status:desc"; phoneSort.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  assert.deepEqual(rows().map((row) => row.dataset.entity), ["cover.kitchen_two", "cover.living_three", "cover.living_one"], "status, descending");
  assert.equal(wiz().querySelector('.wiz-picker select[data-pick-sort="order"]').value, "status:desc");
  const again = wiz().querySelector('.wiz-picker select[data-pick-sort="order"]');
  again.value = "status:asc"; again.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  await pickCover("cover.kitchen_two");
  // The chosen row opens with what choosing it means, in the row itself.
  const notes = [...wiz().querySelectorAll(".wiz-pick-row.is-selected .wiz-pick-notes .cal-note")];
  assert.deepEqual(notes.map((note) => [note.textContent, note.classList.contains("is-warning")]), [[
    'This cover is already calibrated (times and roll, Sep 29, 2026) and follows the profile "tall_two_leaf". A new calibration, if you choose it in the next step, will replace the values in use; to adjust them, choose fine-tuning.', true]],
    "one yellow note with the profile");
  sortBy("status:desc"); await tick(); sortBy("status:asc"); await tick();
  await press("choose");
  assert.equal(code(), "A-02");
  assert.equal(title(), 'How to calibrate "Kitchen shutter 2"?');
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Kitchen shutter 2");
  assert.equal(wiz().querySelector(".wiz-head .muted").textContent, "Kitchen · Address: 91 · A: 9 · PL: 1", "room first, no WHO (G4-1)");
  assert.equal(wiz().querySelector(".wiz-subline").textContent, 'Follows the profile "tall_two_leaf"');
  const radios = [...wiz().querySelectorAll('.wiz-radios input[name="path"]')];
  assert.deepEqual(radios.map((input) => input.closest(".wiz-radio").querySelector(".wiz-radio-label").firstChild.textContent.trim()),
    ["First cover of its type", "Like a cover already measured", "Fine-tuning"], "a radio list, not three buttons");
  assert.equal(wiz().querySelectorAll('.wiz-actions [data-wiz^="path:"]').length, 0);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-recommended")].map((badge) => [badge.closest(".wiz-radio").querySelector("input").value, badge.textContent]),
    [["C", "Recommended"]], "a calibrated cover: C is advised");
  assert.deepEqual(radios.filter((input) => input.checked).map((input) => input.value), ["C"], "the advised path is preselected");
  assert.equal(button("path").disabled, false, "Continue is ready on the advised path");
  assert.match(wiz().querySelector(".wiz-body").textContent, /"Fine-tuning" is the recommended option because this cover is already calibrated[^.]*\. If in doubt, choose this option\.$/, "the reason names the advised option");
  assert.ok(wiz().querySelector(".wiz-subline").classList.contains("cal-note"), "the cover's context is an information box");
  const sent = () => backend.calls.length + backend.subscriptions.length;
  const before = sent();
  const a = radios.find((input) => input.value === "A");
  a.checked = true; a.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  assert.equal(code(), "A-02", "ticking a radio only changes the choice");
  assert.equal(wiz().querySelector('input[name="path"][value="A"]').checked, true, "the choice survives the redraw");
  assert.match(wiz().querySelector(".wiz-body").textContent, /"Fine-tuning" is the recommended option.*If in doubt, choose this option\.$/, "the advice does not follow the choice");
  assert.equal(wiz().querySelector('input[name="path"][value="A"]').closest(".wiz-radio").querySelector(".wiz-radio-warning.is-warning").textContent,
    "A full new calibration will replace this cover's values in use. To adjust them without starting over, choose \"Fine-tuning\".", "a warning under the chosen path");
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

test("the header's back arrow goes one choice back before any session, keeping what was chosen", async () => {
  const { tab, wiz, code, press, pickCover, choosePath, backend } = await mount();
  const back = () => wiz().querySelector('.wiz-head [data-wiz="back"]');
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.equal(code(), "A-01");
  assert.equal(back().getAttribute("aria-label"), "Back");
  assert.equal(back().nextElementSibling.className, "wiz-head-text", "left of the cover's name");
  await pickCover("cover.kitchen_two"); await press("choose");
  await choosePath("C");
  assert.equal(code(), "C-01");
  await press("current");
  const radio = wiz().querySelector('input[name="case"][value="times_only"]'); radio.checked = true; radio.dispatchEvent(new Event("change", { bubbles: true }));
  await press("case");
  assert.equal(code(), "C-35");
  back().click(); await tick();
  assert.deepEqual([code(), wiz().querySelector('input[name="case"]:checked').value], ["C-02", "times_only"], "the case stays chosen");
  back().click(); await tick();
  assert.equal(code(), "C-01");
  back().click(); await tick();
  assert.deepEqual([code(), wiz().querySelector('input[name="path"]:checked').value], ["A-02", "C"], "the path stays chosen");
  await choosePath("A");
  const no = wiz().querySelector('input[name="slats"][value="no"]'); no.checked = true; no.dispatchEvent(new Event("change", { bubbles: true }));
  back().click(); await tick();
  assert.equal(code(), "A-02");
  await press("path");
  assert.deepEqual([code(), wiz().querySelector('input[name="slats"]:checked').value], ["A-03", "no"], "the slat choice too");
  back().click(); await tick(); back().click(); await tick();
  assert.equal(code(), "A-01");
  assert.equal(wiz().querySelector('.wiz-picker input[name="cover"]:checked').value, JSON.stringify(["one", "cover.kitchen_two"]), "the cover stays chosen");
  back().click(); await tick();
  assert.equal(wiz(), null, "from the first screen, back to the list");
  assert.ok(tab().querySelector(".cal-list"));
  assert.equal(backend.subscriptions.filter((message) => message.type === "myhome/cover_calibration/start").length, 0, "nothing was started");
  // During a session there is no way back, only Abandon.
  const second = await mount();
  await second.startFor("cover.living_one");
  await second.press("begin");
  assert.equal(second.code(), "A-04");
  assert.equal(second.wiz().querySelector('[data-wiz="back"]'), null);
});

test("after Calibrate another cover, the way back from A-02 is A-01 again", async () => {
  const context = await mount();
  const { wiz, code, press, pickCover } = context;
  await runToSaved(context, { fromRow: true });
  await press("another");
  assert.equal(code(), "A-01");
  await pickCover("cover.kitchen_two"); await press("choose");
  wiz().querySelector('[data-wiz="back"]').click(); await tick();
  assert.equal(code(), "A-01", "the restart begins at A-01, so back goes there");
});

test("from a cover's own Measure the way back from A-02 is the list", async () => {
  const { tab, wiz, code } = await mount();
  const row = [...tab().querySelectorAll(".cal-row")].find((item) => item.dataset.entity === "cover.living_one");
  row.querySelector('[data-action="cal-tab-measure-cover"]').click(); await tick();
  assert.equal(code(), "A-02");
  wiz().querySelector('[data-wiz="back"]').click(); await tick();
  assert.equal(wiz(), null);
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
  // "Ⓐ first of its type" is the introduction's sub-line, not a caption under the phase line.
  const intro = wiz().querySelector(".wiz-steps ol > li");
  assert.deepEqual([intro.querySelector(".wiz-step-label").textContent, intro.querySelector("ul > li").textContent], ["Introduction", "First of its type"]);
  assert.equal(wiz().querySelector(".wiz-steps-caption"), null);
  await press("ack:lift");
  assert.equal(code(), "A-07");
  assert.equal(wiz().querySelector(".wiz-stopwatch").hidden, true, "no stopwatch before the run");
  assert.equal(wiz().querySelector('[data-wiz="lift"]').disabled, true);
  await press("next");
  await move(backend, { seconds: 4 });
  assert.equal(wiz().querySelector(".wiz-stopwatch").hidden, false);
  assert.equal(wiz().querySelector(".wiz-stopwatch-label").textContent, "Motor");
  assert.equal(wiz().querySelector(".wiz-stopwatch").getAttribute("style"), "--wiz-stopwatch-width: 560px", "as wide as the drawing under it");
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
  // What was measured sits in tiles above the text: a small label, a big value; the text no longer repeats it.
  const tiles = () => [...wiz().querySelectorAll(".wiz-results .wiz-result")].map((tile) => [tile.querySelector(".wiz-result-label").textContent,
    tile.querySelector(".wiz-result-value").textContent.replace(/\s+/g, " ").trim()]);
  assert.equal(tiles().length, 2);
  assert.equal(tiles()[0][0], "Lift-off");
  assert.match(tiles()[0][1], /^\d+(\.\d)? s · 3 cm$/, "lift-off time and gap in one tile");
  assert.deepEqual(tiles()[1], ["Full ascent", "22.2 s"]);
  assert.deepEqual([wiz().querySelector(".wiz-results").nextElementSibling.className, wiz().querySelector(".wiz-results").nextElementSibling.nextElementSibling.className],
    ["wiz-result-notices", "wiz-body"], "above the text, with the notices about the result between them (G2-11)");
  assert.match(wiz().querySelector(".wiz-body").textContent, /^If both presses came at the right moment, continue\./);
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
  assert.deepEqual(tiles(), [["Full descent", "21.7 s"], ["Curtain travel", "198 cm"]]);
  assert.doesNotMatch(wiz().querySelector(".wiz-body").textContent, /21\.7/);
  await press("repeat");
  assert.equal(actions().at(-1), "next", "the return to the top starts by itself");
  await move(backend);
  assert.equal(wiz().querySelector('[data-wiz="endpoint"]').textContent, "It reached the top, continue");
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
  // Before the automatic confirmation (measured time + margin), the button is the shortcut.
  await move(backend, { seconds: 24 });
  assert.equal(wiz().querySelector('[data-wiz="endpoint"]').textContent, "It reached the top, continue");
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
  const { backend, code, press, type, startFor, wiz } = await mount();
  await startFor("cover.living_one");
  const no = wiz().querySelector('input[name="slats"][value="no"]');
  no.checked = true; no.dispatchEvent(new Event("change", { bubbles: true }));
  await press("begin");
  assert.equal(backend.subscriptions.find((message) => message.type === "myhome/cover_calibration/start").slats, false);
  await move(backend);
  const body = () => wiz().querySelector(".wiz-body").textContent;
  assert.equal(code(), "A-05");
  assert.doesNotMatch(body(), /slat/i, "D-10: no slats in the starting closure");
  await press("endpoint");
  backend.stopped(); await tick();
  assert.equal(code(), "A-11");
  assert.equal(wiz().querySelector(".wiz-title").textContent, "Full ascent");
  assert.equal([...wiz().querySelectorAll(".wiz-steps li li")].some((item) => item.textContent.startsWith("Lift-off")), false);
  assert.doesNotMatch(body(), /second run/i, "D-10: the ascent is the first run here");
  assert.match(body(), /To start the ascent, press button ①/);
  await press("next"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  assert.equal(code(), "A-13");
  await type("198");
  assert.equal(code(), "A-14");
  assert.doesNotMatch(body(), /slat|NOT press when the edge/i, "D-10: no slats in the descent, nor the late press they need");
  assert.match(body(), /To start the descent, press button ①/);
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
  assert.match(wiz().querySelector(".wiz-result-notices").textContent, /10 cm or more/, "under the result, before the text (G2-11)");
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
  // S-07: plain text at the top of the actions column, then the explanation and an outlined Take control.
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-readonly > p")].map((line) => line.textContent),
    ["Control: another device", "Another device is guiding this calibration."]);
  assert.equal(wiz().querySelector(".wiz-readonly .notice"), null);
  assert.equal(wiz().querySelector('[data-wiz="take"]').className, "wiz-take secondary");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-action")].map((button) => button.dataset.wiz), [], "nothing moves: no Stop to offer");
  assert.equal(wiz().querySelector('.wiz-frame [name="reading_cm"]'), null, "a reader has no reading field (S-07)");
  assert.equal(wiz().querySelector(".wiz-stopwatch").hidden, true, "who guides it is no longer in the stopwatch box");
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
  assert.equal(dialog.querySelector('[data-wiz="stop"]'), null, "no Stop of its own: Exit without saving sends it, and Stop stays on the page");
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

test("U-10: after Exit without saving the list is free at once, even with a read begun before the cancel", async () => {
  const { backend, panel, wiz, startFor, tab } = await mount();
  await startFor("cover.living_one");
  wiz().querySelector('[data-wiz="begin"]').click(); await tick(); await move(backend);
  // The list has read the live session; the next periodic read answers only after the cancel.
  panel._calibrationTab.refresh(); await tick(8);
  const callWS = backend.hass.callWS, held = [];
  backend.hass.callWS = async (message) => {
    const result = await callWS(message);
    if (message.type !== "myhome/cover_profiles/overview") return result;
    return new Promise((resolve) => held.push(() => resolve(result)));
  };
  panel._calibrationTab.refresh(); await tick();
  assert.ok(held.length, "a read is in flight");
  backend.hass.callWS = callWS;
  wiz().querySelector('.wiz-head [data-wiz="exit"]').click(); await tick();
  wiz().querySelector('[data-wiz="leave"]').click(); await tick(6);
  assert.equal(wiz(), null);
  const free = () => !tab().querySelector(".cal-tab-busy") && !tab().querySelector('[data-action="cal-tab-measure"]').disabled;
  assert.ok(free(), "no «In corso» row, notice or disabled header right after the cancel");
  held.splice(0).forEach((release) => release()); await tick(8);
  assert.ok(free(), "the read begun before the cancel does not bring the session back");
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
  // D-16: a Save not available yet is said at the top, and no help says what it would do.
  assert.match(wiz().querySelector(".wiz-result-notices").textContent, /not available yet/);
  assert.equal(wiz().querySelector(".wiz-save-info"), null);
  const toggle = wiz().querySelector('[name="save_profile"]');
  toggle.checked = true; toggle.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  assert.equal(code(), "A-21d");
  assert.equal(wiz().querySelector(".wiz-save-info").open, true, "What happens when I save? starts open");
  wiz().querySelector(".wiz-save-info").open = false;
  assert.deepEqual([...wiz().querySelectorAll('[name="save_choice"]')].map((input) => input.value), ["update", "new"], "listed as in A-21d");
  assert.equal(wiz().querySelector('[name="save_choice"][value="new"]').checked, true);
  assert.match(wiz().querySelector(".wiz-profile-block").textContent, /Will also change 1 cover: Living room shutter\u00a03\./);
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, false);
  const name = wiz().querySelector('[name="profile_name"]');
  const error = () => wiz().querySelector(".wiz-name-error");
  assert.equal(error().hidden, true);
  assert.equal(wiz().querySelector("#wiz-name-hint").textContent, "Up to 64 characters, different from the saved profiles.");
  // Home Assistant accepts any name of 1–64 characters, spaces included: only an empty or an existing name is refused.
  name.value = "test K1"; name.dispatchEvent(new Event("input", { bubbles: true })); await tick();
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, false, "a space is fine");
  name.value = "  Tall_Two_Leaf "; name.dispatchEvent(new Event("input", { bubbles: true })); await tick();
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, true, "an existing name");
  assert.deepEqual([error().hidden, error().textContent, name.getAttribute("aria-invalid")], [false, "A profile with this name already exists.", "true"]);
  assert.match(name.getAttribute("aria-describedby"), /wiz-name-error/);
  name.value = "   "; name.dispatchEvent(new Event("input", { bubbles: true })); await tick();
  assert.equal(error().textContent, "Enter a name for the profile.");
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, true);
  assert.equal(wiz().querySelector('[name="profile_name"]'), name, "typing never redraws the field");
  assert.equal(wiz().querySelector(".wiz-save-info").open, false, "closed by the user, it stays closed while the summary changes");
  name.value = "kitchen_two"; name.dispatchEvent(new Event("input", { bubbles: true })); await tick();
  assert.equal(error().hidden, true, "the error goes with the problem");
  assert.equal(wiz().querySelector(".wiz-name-line").textContent, 'This cover will follow the new profile. "tall_two_leaf" stays with the other cover.');
  const update = wiz().querySelector('[name="save_choice"][value="update"]');
  update.checked = true; update.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  assert.equal(wiz().querySelector('[data-wiz="save"]').disabled, true, "updating a shared profile waits for the unified Save");
  assert.equal(backend.calls.some((message) => message.action === "save"), false);
});

/** Path A on Living room shutter 1 from the first close to its saved screen (A-34). */
async function runToSaved({ backend, press, type, startFor, code, tab, choosePath }, { fromRow = false } = {}) {
  if (!fromRow) await startFor("cover.living_one");
  else {
    // From the cover's own Measure: A-01 is skipped.
    [...tab().querySelectorAll(".cal-row")].find((item) => item.dataset.entity === "cover.living_one").querySelector('[data-action="cal-tab-measure-cover"]').click(); await tick();
    await choosePath("A");
  }
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend, { seconds: 4.4 }); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend, { seconds: 22.2 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("198");
  await press("next"); await move(backend, { seconds: 21.7 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  await type("97"); await move(backend, { seconds: 24 }); await press("endpoint"); backend.stopped(); await tick();
  await move(backend, { auto: true, stop: true }); await type("101");
  assert.equal(code(), "A-21");
  await press("save");
  assert.equal(code(), "A-34");
}

test("A-34 offers fine-tuning once the calibration is saved: path C on the same cover, from the values just written", async () => {
  const { backend, wiz, code, press, type, actions, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend, { seconds: 4.4 }); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend, { seconds: 22.2 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("198");
  await press("next"); await move(backend, { seconds: 21.7 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  await type("97"); await move(backend, { seconds: 24 }); await press("endpoint"); backend.stopped(); await tick();
  await move(backend, { auto: true, stop: true }); await type("101");
  assert.equal(code(), "A-21");
  assert.equal(wiz().querySelector('[data-wiz="refine"]'), null, "the summary only saves");
  await press("save");
  assert.equal(code(), "A-34");
  const kinds = [...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => [item.dataset.wiz, item.className.replace("wiz-action ", "")]);
  assert.deepEqual(kinds, [["refine", "primary"], ["assign-profile", "secondary"], ["another", "secondary"], ["open-cover", "secondary"], ["close", "link"]],
    "fine-tuning is the next step; the new profile can go to other covers");
  assert.equal(wiz().querySelector('[data-wiz="refine"]').textContent, "Continue with fine-tuning");
  assert.equal(wiz().querySelector("#wiz-note-refine"), null, "no note under the button");
  assert.equal(wiz().querySelector('[data-wiz="refine"]').hasAttribute("aria-describedby"), false);
  const paragraphs = [...wiz().querySelectorAll(".wiz-body p")].map((item) => item.textContent);
  assert.equal(paragraphs.length, 2, "the saved text, then what fine-tuning does");
  assert.equal(wiz().querySelectorAll(".wiz-body p")[1].querySelector("strong").textContent, "Want to fine-tune the calibration?", "a bold lead-in");
  assert.equal(paragraphs[1],
    "Want to fine-tune the calibration? Four tape readings at a quarter and three quarters of the travel, plus a final check, will make the position estimate more precise along the whole travel. About 4 minutes; the cover will move.");
  const finetune = wiz().querySelector('.wiz-steps li[data-step-state]:last-of-type');
  assert.deepEqual([finetune.querySelector(".wiz-step-label").textContent, finetune.dataset.stepState], ["Fine-tuning (optional)", "future"], "still ahead, not ticked");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-steps ol > li")].slice(0, -1).map((item) => item.dataset.stepState), Array(6).fill("done"));
  const sent = actions().length, saves = backend.calls.filter((message) => message.action === "save").length;
  await press("refine");
  // Straight to the quarter readings (A-22…), in the same wizard: no C-01/C-02 in between.
  assert.match(code(), /^A-2[23]$/, "fine-tuning starts at once (its first positioning may already be over)");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Living room shutter 1", "on the same cover");
  assert.equal(wiz().querySelector(".wiz-steps-line").textContent, "Fine-tuning · 7 of 8", "the stepper goes on at Fine-tuning");
  await settle();
  assert.equal(code(), "A-23");
  for (const reading of ["52", "141", "146", "48"]) { await type(reading); await settle(); }
  assert.equal(code(), "A-31");
  const expected = Number(wiz().querySelector("#wiz-field-hint").textContent.match(/About (\d+) cm/)[1]);
  await type(String(expected + 6));
  assert.equal(code(), "A-32b");
  assert.equal(wiz().querySelector('[data-wiz="continue_anyway"]').classList.contains("link"), true);
  await press("repeat_check"); await settle();
  await type(String(expected + 1));
  assert.equal(code(), "A-32");
  await press("accept");
  assert.equal(code(), "A-33");
  await press("save");
  assert.equal(code(), "A-34");
  assert.equal(wiz().querySelector(".wiz-body").textContent, translations.en.wiz_T322, "the calibration before it was saved; the preview changed nothing");
  assert.equal(wiz().querySelector('[data-wiz="refine"]'), null, "the end of a preview offers no further fine-tuning");
  assert.equal(actions().length, sent, "the fine-tuning preview sent nothing");
  assert.equal(backend.calls.filter((message) => message.action === "save").length, saves, "and saved nothing more");
});

test("A-34's Assign this profile to other covers opens the maintainer's Assign dialog on the profile just created", async () => {
  const context = await mount();
  const { backend, root, wiz, code } = context;
  await runToSaved(context);
  const button = wiz().querySelector('[data-wiz="assign-profile"]');
  assert.equal(button.textContent, "Assign this profile to other covers");
  // Home Assistant has written the new profile: the tab finds it by name in the overview.
  backend.overview.profiles.push({ id: "fresh", name: "living_room_shutter_1", opening_time: 22.2, closing_time: 21.7, reference_travel_cm: 198,
    geometry: { slat_time_s: 4.4, opening_roll: 1.83, closing_roll: 1.91 }, assigned_to: ["cover.living_one"], provenance: {} });
  button.click(); await settle();
  const dialog = root.querySelector("#dialog-host dialog");
  assert.ok(dialog?.open, "the dialog is open");
  assert.equal(dialog.querySelector("#catalogue-title").textContent, "Assign profile to covers");
  assert.ok(backend.calls.some((message) => message.type === "myhome/cover_profiles/overview"));
  assert.equal(code(), "A-34", "the wizard stays under it");
  dialog.querySelector("#catalogue-close").click(); await tick();
  assert.equal(root.querySelector("#dialog-host dialog"), null);
});

test("the tab's Fine-tune asks first what is wrong (C-01, C-02), and the way back from C-01 is the list", async () => {
  const { tab, wiz, code, press } = await mount();
  const refine = () => [...tab().querySelectorAll('[data-action="cal-tab-refine"]')].find((button) => button.dataset.id.includes("cover.kitchen_two"));
  refine().click(); await tick();
  assert.equal(code(), "C-01");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Kitchen shutter 2");
  await press("current");
  assert.equal(code(), "C-02");
  wiz().querySelector('[data-wiz="back"]').click(); await tick();
  assert.equal(code(), "C-01");
  wiz().querySelector('[data-wiz="back"]').click(); await tick();
  assert.equal(wiz(), null);
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
  assert.equal(reading.title, "Check the cover");
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
  assert.deepEqual(drawn({ step: "reset", phase: "starting_close" }), ["A-09", null], "A-09's frame shows only the wait box");
  assert.deepEqual(drawn({ step: "reset", phase: "closing" }), ["A-10", "window-closed before-body"], "the closed window, as on A-05");
  assert.deepEqual(drawn({ step: "reset", phase: "closing" }, {}, "C"), ["C-10", "window-closed before-body"]);
  assert.deepEqual(drawn({ step: "opening", phase: "opening" }), ["A-11", "ascent-sequence before-body"]);
  assert.deepEqual(drawn({ step: "opening", phase: "reading" }), ["A-12", null]);
  assert.deepEqual(drawn({ step: "opening", phase: "reading" }, { ackAscent: true }), ["A-13", "curtain-open-tape after-body"]);
  assert.deepEqual(drawn({ step: "closing", phase: "closing" }), ["A-14", "descent-sequence before-body"]);
  assert.deepEqual(drawn({ step: "half_open", phase: "briefing" }), ["A-15", null]);
  assert.deepEqual(drawn({ step: "half_open", phase: "briefing" }, { ackDescent: true }), ["A-16", "curtain-partial-tape before-body"]);
  assert.deepEqual(drawn({ step: "half_open", phase: "opening" }, { ackDescent: true, ackReadings: true }), ["A-17", null]);
  assert.deepEqual(drawn({ step: "half_open", phase: "reading" }, { ackDescent: true, ackReadings: true }), ["A-18", "curtain-partial-tape after-body"]);
  assert.deepEqual(drawn({ step: "top", phase: "opening" }, { ackReadings: true }), ["A-19", null]);
  assert.deepEqual(drawn({ step: "top", phase: "opening" }), ["A-09", null], "the return to the top reuses A-09: no drawing either");
  assert.deepEqual(drawn({ step: "half_close", phase: "reading" }, { ackReadings: true }), ["A-20", "curtain-partial-tape after-body"]);
  assert.deepEqual(drawn({ step: "closing", phase: "closing" }, {}, "C"), ["C-14", "descent-sequence before-body"], "clones follow their A screen");
  assert.deepEqual(drawn({ phase: "review" }), ["A-21", null]);
});

test("every drawing a screen can pick is a themed inline SVG, and A-09 has none", async () => {
  const { readFileSync, statSync } = await import("node:fs");
  const { ILLUSTRATIONS, SVG, illustrationMarkup } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-illustration.js");
  const panel = new URL("../../custom_components/myhome/frontend/panel/", import.meta.url);
  const source = readFileSync(new URL("panel-calibration-screens.js", panel), "utf8");
  const table = source.slice(source.indexOf("const ILLUSTRATION_OF = {"), source.indexOf("ILLUSTRATION_OF.C ="));
  const used = new Set([...table.matchAll(/\["([a-z-]+)", (?:BEFORE|AFTER)\]/g)].map((match) => match[1]));
  assert.ok(used.size >= 9, `${used.size} ids in the table`);
  assert.deepEqual(Object.keys(SVG).sort(), Object.keys(ILLUSTRATIONS).sort(), "one drawing per id, no drawing without an id");
  const ids = new Set();
  for (const id of used) {
    assert.ok(ILLUSTRATIONS[id] && SVG[id], `${id} has a size and a drawing`);
    const host = document.createElement("div");
    host.innerHTML = illustrationMarkup(id, "Step diagram", (value) => value);
    const svg = host.firstElementChild;
    assert.equal(svg.tagName.toLowerCase(), "svg", id);
    assert.match(svg.getAttribute("viewBox"), /^0 0 \d+ \d+$/, `${id} keeps its viewBox`);
    assert.deepEqual([svg.getAttribute("width"), svg.getAttribute("height")], [String(ILLUSTRATIONS[id].width), String(ILLUSTRATIONS[id].height)]);
    assert.deepEqual([svg.getAttribute("role"), svg.getAttribute("aria-label"), svg.dataset.illustration], ["img", "Step diagram", id]);
    // Outside masks and clip paths every colour is a palette property (its light colour only as the fallback).
    const painted = SVG[id].replace(/<(mask|clipPath)\b[\s\S]*?<\/\1>/g, "").replace(/var\(--wiz-ill-[a-z0-9-]+,#[0-9A-Fa-f]{3,6}\)/g, "");
    assert.doesNotMatch(painted, /#[0-9A-Fa-f]{3,6}\b|"white"|"black"/, `${id} has no raw colour outside its masks`);
    for (const match of SVG[id].matchAll(/\bid="([^"]+)"/g)) {
      assert.ok(match[1].startsWith(`wiz-${id}-`), `${match[1]} carries its drawing's prefix`);
      assert.equal(ids.has(match[1]), false, `${match[1]} is unique on the page`);
      ids.add(match[1]);
    }
  }
  const bytes = statSync(new URL("panel-calibration-illustrations-svg.js", panel)).size;
  assert.ok(bytes <= 60 * 1024, `${bytes} bytes of drawings`);
  assert.match(table, /"05": \["window-closed"/);
  assert.doesNotMatch(table, /"09":/, "A-09 has no drawing");
  const t = (key) => translations.en[key] || key;
  const a09 = buildScreen({ t, stage: "session", path: "A", cover: { name: "Kitchen shutter 2" },
    view: { mode: "geometry", step: "reset", phase: "starting_close", values: {}, samples: { lift: 4 }, readings: { gap: 3 }, slats: true, owner: true, sequence: 4 } });
  assert.deepEqual([a09.code, a09.illustration], ["A-09", null]);
});

test("the profile switch is a 36×20 track with a 16 px thumb 2 px from every edge, in both states", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  const track = css.match(/\.wiz-switch input \{([^}]*)\}/)[1], thumb = css.match(/\.wiz-switch input::after \{([^}]*)\}/)[1];
  for (const rule of ["box-sizing: border-box", "width: 36px", "height: 20px", "border: 0", "margin: 0", "padding: 0"]) assert.ok(track.includes(rule), rule);
  for (const rule of ["top: 2px", "left: 2px", "width: 16px", "height: 16px"]) assert.ok(thumb.includes(rule), rule);
  assert.match(css, /\.wiz-switch input:checked::after \{ transform: translateX\(16px\); \}/);
});

test("on the phone the confirmations are sheets that slide down before they hide", async () => {
  const { wiz, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  const original = globalThis.matchMedia;
  try {
    globalThis.matchMedia = (query) => ({ matches: query.includes("max-width") });
    wiz().querySelector(".wiz-head .wiz-x").click(); await tick();
    const exit = wiz().querySelector(".wiz-dialog:not(.wiz-nav-dialog)");
    exit.querySelector('[data-wiz="stay"]').click(); await tick();
    assert.deepEqual([exit.hidden, exit.classList.contains("is-leaving")], [false, true], "sliding down");
    await new Promise((resolve) => setTimeout(resolve, 260));
    assert.equal(exit.hidden, true);
  } finally { globalThis.matchMedia = original; }
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-dialog, \.wiz-sheet \{ background: rgb\(0 0 0 \/ 55%\); -webkit-backdrop-filter: blur\(8px\); backdrop-filter: blur\(8px\); \}/);
  assert.match(css, /\.wiz-dialog \.actions \{ flex-direction: column-reverse; align-items: stretch;/, "stacked, primary first");
  assert.match(css, /dialog\.cal-dialog \{ width: 100%; max-width: none; max-height: 90vh; margin: auto 0 0; border-radius: 18px 18px 0 0;/, "the tab's dialogs too");
});

test("the Steps sheet slides down before it hides, at once with reduced motion", async () => {
  const { wiz, tab } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  const sheet = wiz().querySelector(".wiz-sheet");
  const original = globalThis.matchMedia;
  try {
    globalThis.matchMedia = () => ({ matches: false });
    wiz().querySelector('[data-wiz="steps"]').click(); await tick();
    assert.equal(sheet.hidden, false);
    wiz().querySelector('[data-wiz="steps-close"]').click(); await tick();
    assert.deepEqual([sheet.hidden, sheet.classList.contains("is-leaving")], [false, true], "sliding down");
    await new Promise((resolve) => setTimeout(resolve, 260));
    assert.deepEqual([sheet.hidden, sheet.classList.contains("is-leaving")], [true, false], "then hidden");
    globalThis.matchMedia = (query) => ({ matches: query.includes("reduce") });
    wiz().querySelector('[data-wiz="steps"]').click(); await tick();
    wiz().querySelector('[data-wiz="steps-close"]').click(); await tick();
    assert.equal(sheet.hidden, true, "reduced motion: at once");
  } finally { globalThis.matchMedia = original; }
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-sheet:not\(\[hidden\]\) \.wiz-sheet-card \{ animation: wiz-sheet-in 220ms/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\) \{ \.wiz-sheet, \.wiz-sheet \.wiz-sheet-card \{ animation: none !important; \} \}/);
});

test("the fade over the phone's action bar shows only while content is hidden below", async () => {
  const { wiz, tab } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  const main = wiz().querySelector(".wiz-main"), actions = wiz().querySelector(".wiz-actions");
  // jsdom has no layout: give the content a scroll box by hand.
  Object.defineProperties(main, { scrollHeight: { value: 900, configurable: true }, clientHeight: { value: 400, configurable: true } });
  main.scrollTop = 0; main.dispatchEvent(new Event("scroll"));
  assert.equal(actions.classList.contains("has-more"), true, "more below");
  main.scrollTop = 500; main.dispatchEvent(new Event("scroll"));
  assert.equal(actions.classList.contains("has-more"), false, "at the end of the scroll it goes");
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-actions\.has-more::before \{ opacity: 1; \}/);
});

test("on the phone the run's ① and ② stack, never side by side", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.doesNotMatch(css, /\.wiz-actions:has\(\.wiz-action:nth-of-type\(2\)\.primary\)/, "no two-column rule for two primaries");
  assert.match(css, /\.wiz-actions \{ display: grid; grid-template-columns: minmax\(0, 1fr\);/, "one column");
  assert.match(css, /@media \(hover: hover\) \{ \.wiz-action\.stop:hover \{/, "a tap leaves no tint on Stop");
  assert.match(css, /\.wiz-main \{ flex: 1; min-height: 0; overflow-y: auto;[^}]*display: flex; flex-direction: column; \}/, "the phone's content scrolls between the strip and the bar");
  assert.match(css, /\.wiz-main > \* \{ flex-shrink: 0; min-width: 0; \}/, "blocks keep their height: a drawing never covers the text");
  assert.match(css, /\.wiz-action\.stop, \.wiz-action\.link \{ min-height: 44px; background: transparent; \}/, "plain red text, the bar's height");
});

test("1 px dividers separate the side columns from the centre on the wide layout only", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  const wide = css.slice(css.indexOf("@container caltab (min-width: 1000px) {\n  .wiz-columns"));
  assert.match(wide.slice(0, wide.indexOf("\n}")), /\.wiz-steps \{ border-inline-end: 1px solid var\(--panel-border\); \}[\s\S]*\.wiz-actions \{ border-inline-start: 1px solid var\(--panel-border\); \}/);
});

test("the wizard's side columns take the page colour, slightly shaded", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz \{ --wiz-side: color-mix\(in srgb, var\(--primary-text-color, #182b37\) 4%, var\(--primary-background-color, #fafafa\)\);/);
});

test("the drawings' palette follows Home Assistant's dark mode", async () => {
  const { backend, panel, wiz, startFor } = await mount();
  await startFor("cover.living_one");
  assert.equal(wiz().dataset.theme, "light", "no theme data and no dark preference: light");
  panel.hass = { ...backend.hass, themes: { darkMode: true } }; await tick();
  assert.equal(wiz().dataset.theme, "dark");
  panel.hass = { ...backend.hass, themes: { darkMode: false } }; await tick();
  assert.equal(wiz().dataset.theme, "light");
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz\[data-theme="dark"\] \{[^}]*--wiz-ill-cover-border: #606060/);
});

test("the drawing is one inline SVG at its Figma size, placed by its position, and gone where the mockup has none", async () => {
  const { ILLUSTRATIONS } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-illustration.js");
  assert.deepEqual(Object.keys(ILLUSTRATIONS).sort(), ["ascent-sequence", "check", "curtain-open-tape", "curtain-partial-tape", "descent-sequence",
    "lift-sequence", "lift-sequence-mobile", "lift-zoom", "two-runs", "window-closed"]);
  assert.ok(Object.values(ILLUSTRATIONS).every((size) => size.width <= 564), "never wider than the instruction column");
  const { backend, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  await move(backend);
  assert.equal(code(), "A-05");
  const figure = wiz().querySelector(".wiz-main .wiz-illustration");
  assert.equal(figure.tagName.toLowerCase(), "svg");
  assert.equal(figure.dataset.illustration, "window-closed");
  assert.equal(figure.getAttribute("aria-label"), "Step diagram");
  assert.deepEqual([figure.getAttribute("width"), figure.getAttribute("height"), figure.getAttribute("viewBox")], ["259", "250", "0 0 260 250"]);
  assert.equal(figure.getAttribute("style"), "width: min(100%, 259px); aspect-ratio: 259 / 250", "the ratio is kept when the column is narrower");
  assert.equal(figure.nextElementSibling.className, "wiz-body", "a step shows its drawing above the text");
  assert.equal(wiz().querySelector(".wiz-frame .cal-visual"), null, "the maintainer's small scene is not used by the wizard");
});

test("every wait has its bar: the time left when the duration is known, moving back and forth when it is not", async () => {
  const t = (key) => translations.it[key] || key;
  const view = { mode: "geometry", step: "home", phase: "starting_close", values: {}, samples: {}, readings: {}, slats: true, owner: true, sequence: 1 };
  const wait = (cover, extra = {}, elapsed = null, local = {}) => buildScreen({ t, language: "it", stage: "session", path: "A", view: { ...view, ...extra },
    elapsed, local, cover: { name: "Cucina 2", ...cover } }).wait;
  // A positioning lasts the full time in use, the integration's default too (R3-11); without any time it is indeterminate.
  const fallback = wait({ effective: { closing: { value: 30, origin: "default" } } });
  assert.deepEqual(fallback.progress, { value: 0, remaining: 30 }, "the default time counts for a positioning");
  const never = wait({ effective: {} });
  assert.deepEqual(never.progress, { value: null, remaining: null }, "no time at all: indeterminate");
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

test("Stop alone in a wait is the red filled button; beside a step's buttons it stays a red link", async () => {
  const t = (key) => translations.en[key] || key;
  const view = { mode: "geometry", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 }, readings: {}, slats: true, owner: true, sequence: 2 };
  const kinds = (extra, local = {}) => buildScreen({ t, stage: "session", path: "A", view: { ...view, ...extra }, local, elapsed: 1, cover: { name: "Kitchen shutter 2" } })
    .actions.map((action) => `${action.id}:${action.kind}`);
  // Positionings to an end stop offer the end stop at once: Stop is then the red link beside it (R6-6).
  assert.deepEqual(kinds({ step: "home", phase: "starting_close" }), ["endpoint:primary", "stop:stop"], "A-04");
  assert.deepEqual(kinds({ step: "reset", phase: "closing" }), ["endpoint:primary", "stop:stop"], "A-09 (no time known: A-10 at once)");
  assert.deepEqual(kinds({ step: "half_open", phase: "opening" }, { ackDescent: true, ackReadings: true }), ["stop:danger"], "A-17: Home Assistant stops the half run, Stop alone");
  assert.deepEqual(kinds({ step: "lift", phase: "opening" }, { ackLift: true }), ["next:primary", "lift:primary", "stop:stop"], "A-07 keeps the link");
  assert.deepEqual(kinds({ step: "top", phase: "opening" }, { ackReadings: true }), ["endpoint:primary", "stop:stop"], "A-19 while it positions");
  const starting = buildScreen({ t, stage: "session", path: "A", view: { ...view, step: "home", phase: "starting_close" }, elapsed: null, cover: { name: "K" } });
  assert.equal(starting.actions[0].disabled, true, "until the motor runs Home Assistant would refuse the end stop");
  const { backend, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  assert.equal(code(), "A-04");
  assert.equal(wiz().querySelector('.wiz-actions [data-wiz="stop"]').className, "wiz-action stop");
  backend.started(); await tick();
  assert.equal(wiz().querySelector('.wiz-actions [data-wiz="endpoint"]').textContent, "It is fully closed, continue");
  await press("endpoint");
  assert.equal(backend.calls.filter((message) => message.action === "endpoint").length, 1, "the same end stop the automatic advance sends");
  await press("stop");
  assert.equal(backend.calls.filter((message) => message.action === "stop").length, 1, "the red button stops as before");
});

test("radios are plain rows, the advice badge is accent blue, links and Exit without saving are red text", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  const rule = (selector) => css.match(new RegExp(`^${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")} \\{([^}]*)\\}`, "m"))?.[1] ?? "";
  assert.doesNotMatch(rule(".wiz-radio"), /border|background/, "no card around a radio");
  assert.doesNotMatch(css, /\.wiz-radio:has\(input:checked\)/, "no tint on the chosen radio");
  assert.match(rule(".wiz-recommended"), /color: var\(--panel-accent\)/);
  assert.match(rule(".wiz-action.link"), /color: var\(--panel-error\)/);
  assert.match(rule(".wiz-action.danger"), /background: var\(--panel-error\)/);
  assert.match(rule(".wiz-leave"), /color: var\(--panel-error\); border: 0/);
});

test("a step's problem says the motor's state as plain lines under the text, S-05 with the stopwatch, and keeps Stop", () => {
  const t = (key) => translations.it[key] || key;
  const view = { mode: "geometry", phase: "opening", step: "opening", values: {}, samples: {}, readings: {}, slats: true, owner: true, sequence: 5 };
  const problem = (reason, extra = {}) => buildScreen({ t, language: "it", stage: "session", path: "A", view: { ...view, problem: { reason, ...extra } },
    cover: { name: "Cucina 2" } });
  const s05 = problem("travel_timeout", { elapsed_s: 92 });
  assert.equal(s05.code, "S-05");
  assert.equal(s05.stopwatch, null, "no light-blue box");
  assert.deepEqual(s05.status, [translations.it.wiz_T256, "Cronometro: fermo a 92 s"]);
  assert.deepEqual(problem("travel_timeout").status, [translations.it.wiz_T256], "without the time the second line is left out");
  const s01 = problem("unexpected_stop");
  assert.deepEqual([s01.code, s01.status], ["S-01", [translations.it.wiz_T242]]);
  assert.deepEqual(s01.actions.map((action) => action.id), ["repeat_step", "stop"], "Stop stays until the owner decides otherwise");
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
  // S-08: "Exit without saving" as red text on the left, the primary on the right; focus starts on the primary.
  assert.deepEqual(buttons.map((button) => button.dataset.wiz), ["leave", "stay"], "two buttons only");
  assert.equal(root.activeElement, dialog.querySelector('[data-wiz="stay"]'));
  buttons.at(-1).focus();
  dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
  assert.equal(root.activeElement, buttons[0], "Tab wraps to the first button");
  dialog.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", shiftKey: true, bubbles: true }));
  assert.equal(root.activeElement, buttons.at(-1), "Shift+Tab wraps to the last one");
  dialog.querySelector('[data-wiz="stay"]').click(); await tick();
  assert.equal(dialog.hidden, true, "Continue the calibration closes it and keeps the wizard");
});

test("a half run that did not start by itself can be started from its screen, and fine-tuning starts over as a preview", async () => {
  const t = (key) => translations.en[key] || key;
  const view = { mode: "geometry", phase: "briefing", step: "half_open", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 },
    readings: { gap: 3 }, geometry: {}, travel_cm: 198, slats: true, owner: true, sequence: 4 };
  const screen = buildScreen({ t, stage: "session", path: "A", view, local: { ackDescent: true, ackReadings: true }, cover: { name: "Living room shutter 1" } });
  assert.equal(screen.code, "A-17");
  assert.deepEqual(screen.actions.map((action) => action.id), ["next", "stop"]);
  const context = await mount({ stageMs: 30 });
  const { wiz, code, press, backend } = context;
  await runToSaved(context);
  await press("refine");
  assert.equal(code(), "A-22");
  await press("stop");
  assert.equal(code(), "S-01");
  await press("start-over");
  assert.equal(code(), "A-22", "fine-tuning starts over from the saved values, still as a preview");
  assert.ok(wiz().querySelector(".wiz-preview"));
  assert.equal(backend.calls.filter((message) => message.action === "save").length, 1, "only the base calibration was saved");
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

test("Close keeps each mockup's style: B-09 red filled, A-34 red text, C-34 and S-06 red outlined", () => {
  const t = (key) => translations.it[key] || key;
  const close = (screen) => [screen.code, screen.actions.find((action) => action.id === "close").kind];
  const saved = (path, preview = false) => buildScreen({ t, language: "it", stage: "saved", path, scope: path === "C" ? "times_only" : null,
    cover: { name: "Cucina 2", followProfile: "alta" }, local: { saved: { target: path === "B" ? "follow_profile" : "cover_only", preview } } });
  assert.deepEqual(close(saved("B")), ["B-09", "danger"]);
  assert.deepEqual(close(saved("A")), ["A-34", "link"]);
  assert.deepEqual(close(saved("C")), ["C-34", "danger-outline"]);
  assert.deepEqual([close(saved("B", true)), close(saved("A", true)), close(saved("C", true))],
    [["B-09", "primary"], ["A-34", "link"], ["C-34", "primary"]], "U-8: at the end of a preview Close is the primary on B-09 and C-34");
  const expired = buildScreen({ t, language: "it", stage: "session", path: "A", cover: { name: "Cucina 2" }, status: { expired: true },
    view: { mode: "geometry", phase: "briefing", step: "lift", values: {}, samples: {}, readings: {}, owner: true, sequence: 3 } });
  assert.deepEqual(close(expired), ["S-06", "danger-outline"]);
});

test("full runs and the return to the top: once the motor stopped by itself the stopwatch freezes, Stop goes, the bar is full", async () => {
  const t = (key) => translations.en[key] || key;
  const base = { mode: "geometry", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 }, readings: { gap: 3 },
    geometry: { slat_time_s: 4 }, travel_cm: 110, slats: true, owner: true, sequence: 7 };
  const screen = (view, local = {}, elapsed = 12.3, mode) => buildScreen({ t, stage: "session", path: mode === "guided" ? "C" : "A",
    scope: mode === "guided" ? "times_only" : null, view: { ...base, ...(mode ? { mode } : {}), ...view }, local, elapsed, cover: { name: "Kitchen shutter 2" } });
  const ids = (item) => item.actions.map((action) => action.id);
  for (const [view, code, local] of [[{ step: "opening", phase: "opening" }, "A-11"], [{ step: "closing", phase: "closing" }, "A-14"]]) {
    const running = screen({ ...view, motor_stopped: false, stopped_elapsed: null }, local);
    assert.equal(running.code, code);
    assert.deepEqual(ids(running), ["next", "endpoint", "stop"], `${code} running: Stop`);
    assert.deepEqual(running.stopwatch, { label: "Motor", value: "moving for 12.3 s" });
    assert.equal(screen({ ...view }, local, 12).stopwatch.value, "moving for 12.0 s", "one decimal always: the value keeps its length");
    const stopped = screen({ ...view, motor_stopped: true, stopped_elapsed: 21.37 }, local, 25.8);
    assert.deepEqual(ids(stopped), ["next", "endpoint"], `${code} stopped: no Stop`);
    assert.equal(stopped.actions.find((action) => action.id === "endpoint").kind, "primary");
    assert.equal(stopped.actions.find((action) => action.id === "endpoint").disabled, false, "the end stop is confirmed as before");
    assert.deepEqual(stopped.stopwatch, { label: "Stopwatch", value: "stopped at 21.4 s" }, `${code} freezes at the stop frame`);
    assert.equal(screen({ ...view, motor_stopped: true, stopped_elapsed: 21 }, local).stopwatch.value, "stopped at 21.0 s");
  }
  // The return to the top (A-19 first leg): the bar is complete once the motor stopped, before the expected time.
  const top = screen({ step: "top", phase: "opening", motor_stopped: false, stopped_elapsed: null }, { ackReadings: true }, 5);
  assert.deepEqual([top.code, ids(top), Math.round(top.wait.progress.value * 100)], ["A-19", ["endpoint", "stop"], 23], "still positioning: the end stop at once");
  assert.deepEqual(ids(screen({ step: "top", phase: "opening", motor_stopped: false }, { ackReadings: true }, 23)), ["endpoint", "stop"],
    "past its measured time the end stop is asked, Stop stays while the motor runs");
  const topStopped = screen({ step: "top", phase: "opening", motor_stopped: true, stopped_elapsed: 9.1 }, { ackReadings: true }, 9.5);
  assert.deepEqual([ids(topStopped), topStopped.wait.progress, topStopped.wait.remaining], [["endpoint"], { value: 1, remaining: null }, ""]);
  assert.deepEqual(ids(screen({ step: "top", phase: "opening", motor_stopped: true, stopped_elapsed: 9.1 })), ["endpoint", "stopped"],
    "the return before a repeated descent too, with the stopped state in place of its wait (D-12)");
  // The lift-off run is unchanged: a stop there still ends the session, so it keeps Stop.
  assert.deepEqual(ids(screen({ step: "lift", phase: "opening" }, { ackLift: true })), ["next", "lift", "stop"]);
  // The guided runs of path C (times only).
  const guided = screen({ phase: "closing", values: { opening_time: 12.6 }, motor_stopped: true, stopped_elapsed: 12.24 }, {}, 14, "guided");
  assert.deepEqual([guided.code, ids(guided), guided.stopwatch.value], ["C-14", ["run:close", "endpoint"], "stopped at 12.2 s"]);
  assert.deepEqual(ids(screen({ phase: "opening", motor_stopped: false }, {}, 3, "guided")), ["run:open", "endpoint", "stop"]);

  // On screen: the stopwatch stops counting and the Stop link leaves.
  const { backend, wiz, code, press, type, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend, { seconds: 4.4 }); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend, { seconds: 22.2 });
  assert.equal(code(), "A-11");
  assert.ok(wiz().querySelector('.wiz-actions [data-wiz="stop"]'));
  Object.assign(backend.session, { motor_stopped: true, stopped_elapsed: 22.24 }); backend.session.sequence += 1; backend.emit(); await settle();
  assert.equal(wiz().querySelector(".wiz-stopwatch-value").textContent, "stopped at 22.2 s");
  assert.equal(wiz().querySelector(".wiz-stopwatch-label").textContent, "Stopwatch");
  assert.equal(wiz().querySelector('.wiz-actions [data-wiz="stop"]'), null, "no Stop once the motor stopped");
  assert.equal(wiz().querySelector('[data-wiz="endpoint"]').classList.contains("primary"), true);
  await settle();
  assert.equal(wiz().querySelector(".wiz-stopwatch-value").textContent, "stopped at 22.2 s", "it does not count on");
});

test("a full run ended by the bus: valid with a press before or within 2 s of the frame, otherwise its result asks to repeat", async () => {
  const toAscent = async (context) => {
    const { backend, press, type, startFor, code } = context;
    await startFor("cover.living_one");
    await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
    await press("ack:lift"); await press("next"); await move(backend, { seconds: 4.4 }); await press("lift"); backend.stopped(); await tick();
    await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
    assert.equal(code(), "A-11");
    await press("next"); backend.started(); await tick();
  };
  const frame = (backend, seconds) => {
    backend.tick(seconds);
    Object.assign(backend.session, { motor_stopped: true, stopped_elapsed: backend.view().elapsed });
    backend.emit();
  };
  const endpoints = (backend) => backend.calls.filter((message) => message.action === "endpoint").length;
  const notice = (wiz) => wiz().querySelector(".wiz-result-notices").textContent;
  // (a) ② before the frame: the press time, valid.
  const a = await mount();
  await toAscent(a);
  a.backend.tick(22); a.backend.emit(); await tick();
  await a.press("endpoint"); a.backend.stopped(); await tick();
  assert.deepEqual([a.code(), !!a.wiz().querySelector('[data-wiz="ack:ascent"]'), notice(a.wiz)], ["A-12", true, ""]);
  // (b) ② within 2 s after the frame: the frame's time, valid.
  const b = await mount();
  await toAscent(b);
  frame(b.backend, 22); await tick();
  b.backend.tick(1); b.backend.emit(); await tick();
  await b.press("endpoint"); b.backend.stopped(); await tick();
  assert.deepEqual([b.code(), !!b.wiz().querySelector('[data-wiz="ack:ascent"]'), notice(b.wiz)], ["A-12", true, ""]);
  // (c) no ② within 2 s: the run goes on by itself to its result, not valid, with only Repeat.
  const c = await mount();
  await toAscent(c);
  frame(c.backend, 22); await tick();
  const before = endpoints(c.backend);
  c.backend.tick(1.5); c.backend.emit(); await tick();
  assert.equal(endpoints(c.backend), before, "1.5 s after the frame: still waiting for ②");
  c.backend.tick(1); c.backend.emit(); await tick(6);
  assert.equal(endpoints(c.backend), before + 1, "2.5 s: the panel confirms the end stop itself");
  c.backend.stopped(); await tick();
  assert.equal(c.code(), "A-12");
  assert.equal(notice(c.wiz), "The cover stopped before you pressed ②: the time may not be the real one. Repeat the run and press ② as soon as the motor really stops.");
  assert.deepEqual([...c.wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => [item.dataset.wiz, item.className.replace("wiz-action ", ""), item.disabled]),
    [["repeat", "primary", false], ["invalid-next", "secondary", true]], "no OK, continue: Continue shown, disabled (D-11)");
  assert.equal(c.title(), "Ascent not valid", "D-11: the title says so");
  assert.equal(c.wiz().querySelector(".wiz-result-notices .wiz-notice").dataset.tone, "error");
  const tiles = [...c.wiz().querySelectorAll(".wiz-result")];
  assert.deepEqual(tiles.map((tile) => tile.classList.contains("is-invalid")), [false, true], "the lift-off stays valid, the ascent is struck through");
  const ascent = () => [...c.wiz().querySelectorAll(".wiz-steps li li")].find((item) => item.textContent.startsWith("Full ascent"))?.textContent;
  assert.match(ascent(), /—/, "D-11: the stepper does not show the time judged not valid");
  await c.press("repeat");
  assert.ok(c.actions().slice(-2).includes("repeat"), "Repeat sends repeat (the return to the bottom then starts by itself)");
  assert.match(ascent(), /—/, "D-11: nor while the repeat returns to the bottom (A-09)");
  // (d) a frame at the actuator's timer (59-65 s), even with ② within 2 s: not valid.
  const d = await mount();
  await toAscent(d);
  frame(d.backend, 60.2); await tick();
  await d.press("endpoint"); d.backend.stopped(); await tick();
  assert.equal(d.code(), "A-12");
  assert.equal(notice(d.wiz), "The cover stopped when the actuator's timer ran out (about 60 s): the time is not valid. Repeat the run and press ② as soon as the motor really stops.");
  assert.equal(d.wiz().querySelector('[data-wiz="ack:ascent"]'), null);
});

test("the full descent follows the same rule, and the lift-off run is not affected", async () => {
  const { backend, press, type, startFor, code, wiz } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); backend.started(); await tick();
  assert.equal(code(), "A-07");
  // The lift-off run: a stop frame is not a full run's end (the backend interrupts it), the panel sends nothing.
  const before = backend.calls.filter((message) => message.action === "endpoint").length;
  backend.tick(5); Object.assign(backend.session, { motor_stopped: true, stopped_elapsed: 2 }); backend.emit(); await tick(6);
  assert.equal(backend.calls.filter((message) => message.action === "endpoint").length, before, "nothing automatic on A-07");
  delete backend.session.motor_stopped; delete backend.session.stopped_elapsed;
  await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend, { seconds: 22.2 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("198");
  assert.equal(code(), "A-14");
  await press("next"); backend.started(); backend.tick(21); Object.assign(backend.session, { motor_stopped: true, stopped_elapsed: backend.view().elapsed }); backend.emit(); await tick();
  backend.tick(3); backend.emit(); await tick(6);
  backend.stopped(); await tick();
  assert.equal(code(), "A-15");
  assert.match(wiz().querySelector(".wiz-result-notices").textContent, /stopped before you pressed ②/);
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => item.dataset.wiz), ["repeat", "invalid-next"]);
  assert.equal(wiz().querySelector(".wiz-title").textContent, "Descent not valid");
});

test("A-03 and A-16 have no Cancel of their own: the header's Abandon the calibration does the same", () => {
  const t = (key) => translations.it[key] || key;
  const a03 = buildScreen({ t, language: "it", stage: "before", path: "A", cover: { name: "Cucina 2" } });
  const a16 = buildScreen({ t, language: "it", stage: "session", path: "A", cover: { name: "Cucina 2" },
    view: { mode: "geometry", step: "half_open", phase: "briefing", values: { closing_time: 21 }, samples: {}, readings: {}, slats: true, owner: true, sequence: 9 },
    local: { ackDescent: true } });
  for (const screen of [a03, a16]) {
    assert.deepEqual(screen.actions.map((action) => action.id), [screen.code === "A-03" ? "begin" : "ack:readings"], screen.code);
    assert.equal(screen.discard, true, `${screen.code} keeps the header's Abandon`);
  }
  assert.deepEqual([a03.code, a16.code], ["A-03", "A-16"]);
});

test("A-04 lasts the whole positioning; A-05 then offers the end stop and T033 at once, Stop while the motor runs; A-10 never has T033", async () => {
  const { backend, wiz, code, press, actions, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  backend.started(); backend.tick(5); backend.emit(); await tick();
  assert.equal(code(), "A-04", "5 s into a 21.7 s closing: still positioning");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => item.dataset.wiz), ["endpoint", "stop"]);
  assert.match(wiz().querySelector(".wiz-wait-remaining").textContent, /17 s/, "the time left counts down over the closing time");
  backend.tick(16); backend.emit(); await tick();
  assert.equal(code(), "A-04", "21 s in: still positioning");
  // No new view: the screen's own clock ends the positioning (the time runs on between two views).
  const now = performance.now.bind(performance);
  performance.now = () => now() + 2000;
  try { await new Promise((resolve) => setTimeout(resolve, 250)); } finally { performance.now = now; }
  assert.equal(code(), "A-05", "past the closing time, drawn whole by the clock's tick");
  const kinds = () => [...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => [item.dataset.wiz, item.className.replace("wiz-action ", "")]);
  const misbehaved = () => wiz().querySelector('[data-wiz="misbehaved"]');
  assert.deepEqual(kinds(), [["endpoint", "primary"], ["misbehaved", "secondary"], ["stop", "stop"]], "outlined, with the red Stop link while moving");
  assert.equal(misbehaved().textContent, "It did not do what it should");
  assert.equal(misbehaved().disabled, false, "active at once");
  assert.equal(misbehaved().hasAttribute("aria-disabled"), false);
  assert.equal(wiz().querySelector('[data-wiz="endpoint"]').disabled, false);
  // Home Assistant says the motor stopped (a stop frame, real or the actuator's timer): Stop leaves.
  backend.session.motor_stopped = true; backend.emit(); await tick();
  assert.equal(code(), "A-05");
  assert.deepEqual(kinds(), [["endpoint", "primary"], ["misbehaved", "secondary"], ["stopped", "status is-still"]], "no Stop once the motor stopped: its state (U-9)");
  await press("misbehaved");
  assert.equal(actions().at(-1), "stop", "today it ends the session: nothing measured yet is lost");
  await tick();
  assert.equal(code(), "S-01");

  const t = (key) => translations.it[key] || key;
  const closing = { effective: { closing: { value: 21.7, origin: "native_fallback" } } };
  const run = (step, path, extra = {}, elapsed = 25) => buildScreen({ t, language: "it", stage: "session", path, scope: path === "C" ? "times_and_rolls" : null,
    cover: { name: "Cucina 2", ...closing }, elapsed,
    view: { mode: "geometry", step, phase: "closing", values: {}, samples: { lift: 4 }, readings: { gap: 3 }, slats: true, owner: true, sequence: 5, ...extra } });
  // The motor stopping ends the positioning before its time.
  assert.equal(run("home", "A", { motor_stopped: true }, 3).code, "A-05");
  assert.deepEqual([run("reset", "A", {}, 3).code, run("reset", "A", {}, 3).actions.map((action) => action.id)], ["A-09", ["endpoint", "stop"]], "A-09 lasts the positioning too, with the end stop at once");
  // U-9: once the estimated run and a margin are over (21.7 s + 15 %), the cover has stopped: its state in place of Stop.
  assert.deepEqual(run("reset", "A", {}, 30).actions.map((action) => action.id), ["endpoint", "stopped"], "the run is over");
  assert.deepEqual(run("home", "A", {}, 30).actions.map((action) => action.id), ["endpoint", "misbehaved", "stopped"]);
  assert.deepEqual([run("reset", "A", {}, 22.5).code, run("reset", "A", {}, 22.5).actions.map((action) => action.id)], ["A-10", ["endpoint", "stop"]],
    "a stop on A-10 would discard the lift-off: no T033 until repeat_step");
  assert.deepEqual(run("reset", "A", { motor_stopped: true }, 3).actions.map((action) => action.id), ["endpoint", "stopped"], "Stop only while moving");
  assert.deepEqual([run("home", "C", {}, 22.5).code, run("home", "C", {}, 22.5).actions.map((action) => [action.id, !!action.disabled])],
    ["C-05", [["endpoint", false], ["misbehaved", false], ["stop", false]]], "the C clone too");
  // A reader sees Stop only while it moves.
  assert.deepEqual(run("home", "C", { read_only: true, owner: false, owner_present: true, motor_stopped: true }).actions, []);
});

test("a positioning lasts the share of the travel still ahead, from the cover's estimated position", async () => {
  const t = (key) => translations.en[key] || key;
  const cover = { name: "Kitchen shutter 2", effective: { closing: { value: 20, origin: "native_fallback" } } };
  const wait = (view, runPosition, elapsed = 0, local = {}) => buildScreen({ t, stage: "session", path: "A", cover, runPosition, elapsed, local,
    view: { mode: "geometry", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 }, readings: { gap: 3 }, slats: true, owner: true, sequence: 3, ...view } });
  const home = { step: "home", phase: "closing" };
  assert.deepEqual([wait(home, 50, 1).code, wait(home, 50, 1).wait.progress.remaining], ["A-04", 9], "half open: half the closing time");
  assert.equal(wait(home, 50, 10.5).code, "A-05", "past that half");
  assert.deepEqual([wait(home, null, 1).wait.progress.remaining, wait(home, null, 15).code], [19, "A-04"], "position unknown: the full time");
  assert.deepEqual([wait(home, 0, 0.5).code, wait(home, 0, 0.5).wait.progress.remaining, wait(home, 0, 2.5).code], ["A-04", 2, "A-05"],
    "already closed: a short run until the bus confirms");
  assert.equal(wait({ ...home, motor_stopped: true }, 100, 1).code, "A-05", "the motor's own stop still ends it early");
  assert.deepEqual([wait({ step: "reset", phase: "closing" }, 20, 3).code, wait({ step: "reset", phase: "closing" }, 20, 5).code], ["A-09", "A-10"]);
  const top = { step: "top", phase: "opening" };
  assert.equal(wait(top, 30, 1, { ackReadings: true }).wait.progress.remaining, Math.ceil(22 * 0.7 - 1), "the return to the top runs 70 % of the opening time");
  // On screen: the position is read once, when the run starts.
  const { backend, code, press, startFor, wiz } = await mount();
  backend.hass.states = { "cover.living_one": { state: "open", attributes: { current_position: 50 } } };
  await startFor("cover.living_one");
  await press("begin");
  backend.started(); backend.tick(5); backend.emit(); await tick();
  assert.equal(code(), "A-04");
  assert.match(wiz().querySelector(".wiz-wait-remaining").textContent, /\b6 s/, "21.7 s × 50 % − 5 s");
  backend.hass.states["cover.living_one"].attributes.current_position = 100;
  backend.tick(6); backend.emit(); await tick();
  assert.equal(code(), "A-05", "a later position does not stretch the run");
});

test("the returns of the tape readings confirm themselves: on the motor's own stop, or after the measured time and a margin", async () => {
  const toTop = async (context) => {
    const { backend, press, type, startFor, code } = context;
    await startFor("cover.living_one");
    await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
    await press("ack:lift"); await press("next"); await move(backend, { seconds: 4.4 }); await press("lift"); backend.stopped(); await tick();
    await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
    await press("next"); await move(backend, { seconds: 22.2 }); await press("endpoint"); backend.stopped(); await tick();
    await press("ack:ascent"); await type("198");
    await press("next"); await move(backend, { seconds: 21.7 }); await press("endpoint"); backend.stopped(); await tick();
    await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
    await type("97");
    assert.equal(code(), "A-19");
    backend.started(); await tick();
  };
  const endpoints = (backend) => backend.calls.filter((message) => message.action === "endpoint").length;
  // 1. The motor stops by itself: the end stop is confirmed at once, and the half descent follows by itself.
  const first = await mount();
  await toTop(first);
  const before = endpoints(first.backend);
  first.backend.tick(10); first.backend.session.motor_stopped = true; first.backend.emit(); await tick(6);
  assert.equal(endpoints(first.backend), before + 1, "confirmed on the stop frame");
  first.backend.stopped(); await tick(6);
  assert.equal(first.actions().at(-1), "next", "the half descent starts as after a press");
  // 2. No stop frame: confirmed once the measured opening time (22.2 s) and the margin (3 s) have passed.
  const second = await mount();
  await toTop(second);
  const base = endpoints(second.backend);
  second.backend.tick(24); second.backend.emit(); await tick(6);
  assert.equal(endpoints(second.backend), base, "24 s: not yet, the button is the shortcut");
  assert.ok(second.wiz().querySelector('[data-wiz="endpoint"]'));
  second.backend.tick(2); second.backend.emit(); await tick(6);
  assert.equal(endpoints(second.backend), base + 1, "26 s: confirmed by itself");
  second.backend.emit(); await tick(6);
  assert.equal(endpoints(second.backend), base + 1, "once per run");
  // 3. A press first: one confirmation only.
  const third = await mount();
  await toTop(third);
  const start = endpoints(third.backend);
  third.backend.tick(23); third.backend.emit(); await tick();
  await third.press("endpoint");
  third.backend.tick(10); await tick(6);
  assert.equal(endpoints(third.backend), start + 1, "the press, then nothing more");
  // 4. A replayed subscription (Home Assistant reconnected) never confirms by itself.
  const fourth = await mount();
  const callbacks = [];
  const subscribe = fourth.backend.hass.connection.subscribeMessage;
  fourth.backend.hass.connection.subscribeMessage = async (callback, message) => { callbacks.push(callback); return subscribe(callback, message); };
  await toTop(fourth);
  const counted = endpoints(fourth.backend);
  fourth.backend.tick(10);
  callbacks.at(-1)(fourth.backend.view({ attachment: "attachment-2", motor_stopped: true }));
  await tick(6);
  assert.equal(endpoints(fourth.backend), counted, "no confirmation after a replay");
});

test("the return to the bottom before a repeated half-ascent reading confirms itself too", async () => {
  const { backend, press, type, startFor, code } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend, { seconds: 4.4 }); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("next"); await move(backend, { seconds: 22.2 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:ascent"); await type("198");
  await press("next"); await move(backend, { seconds: 21.7 }); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:descent"); await press("ack:readings"); await move(backend, { auto: true, stop: true });
  assert.equal(code(), "A-18");
  await press("repeat"); await tick();
  const step = backend.session.step;
  assert.ok(["reset", "home"].includes(step), `back to the bottom (${step})`);
  const before = backend.calls.filter((message) => message.action === "endpoint").length;
  backend.started(); backend.tick(8); backend.session.motor_stopped = true; backend.emit(); await tick(6);
  assert.equal(backend.calls.filter((message) => message.action === "endpoint").length, before + 1, "confirmed on the motor's own stop");
});

test("Abandon and the X always ask first while a session is open, on every step, preview included", async () => {
  const { backend, wiz, code, press, type, startFor } = await mount();
  const asks = async (label) => {
    for (const selector of ['.wiz-head [data-wiz="exit"].wiz-discard', '.wiz-head .wiz-x']) {
      const button = wiz().querySelector(selector);
      assert.ok(button, `${selector} on ${label}`);
      button.click(); await tick();
      const dialog = wiz().querySelector(".wiz-dialog:not(.wiz-nav-dialog)");
      assert.equal(dialog.hidden, false, `${selector} asks on ${label}`);
      dialog.querySelector('[data-wiz="stay"]').click(); await tick();
      assert.ok(wiz(), `still open on ${label}`);
    }
  };
  await startFor("cover.living_one");
  await press("begin");
  await asks("A-04 before the first view arrives");
  await tick();
  await asks(code());
  backend.started(); backend.tick(30); backend.emit(); await tick();
  await asks(code());
  await press("endpoint"); await asks("the stop after A-05"); backend.stopped(); await tick();
  await asks(code());
  await press("ack:lift"); await asks(code());
  await press("next"); await move(backend, { seconds: 4 }); await asks(code());
  await press("lift"); backend.stopped(); await tick(); await asks(code());
  await type("3"); await asks(code());
  // A problem Home Assistant reports as a step (L2) keeps the session open: Abandon still asks.
  backend.session.problem = { reason: "unexpected_stop" }; backend.emit(); await tick();
  assert.equal(code(), "S-01");
  await asks("S-01 as a step");
  delete backend.session.problem; backend.emit(); await tick();
  // A preview (path B) asks too.
  const preview = await mount({ stageMs: 30 });
  await preview.startFor("cover.living_one", "B");
  await preview.press("profile"); await preview.press("begin"); await settle();
  for (const selector of ['.wiz-head [data-wiz="exit"].wiz-discard', '.wiz-head .wiz-x']) {
    preview.wiz().querySelector(selector).click(); await tick();
    assert.equal(preview.wiz().querySelector(".wiz-dialog:not(.wiz-nav-dialog)").hidden, false, `${selector} asks in the preview (${preview.code()})`);
    preview.wiz().querySelector('[data-wiz="stay"]').click(); await tick();
  }
});

test("a reopened session asks before leaving once this tab owns it again", async () => {
  const session = { entry_id: "one", entity_id: "cover.living_one", session_id: "session-1", sequence: 9, revision: 7, mode: "geometry",
    phase: "briefing", step: "lift", reason: null, values: {}, samples: {}, readings: {}, geometry: {}, travel_cm: null, stop_requested: false,
    slats: true, lift_attempts: 1, still_resting: false, gap_warning: false, touching_cm: 1, max_gap_cm: 20, gap_warn_cm: 10,
    saved_travel_cm: 195, expected_cm: null, can_repeat: false, save_modes: ["new"], reading_kind: "lift" };
  const { tab, wiz, code } = await mount({ session, owner: false });
  tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(6);
  assert.ok(wiz().querySelector(".wiz-readonly"), "a reader first");
  wiz().querySelector(".wiz-head .wiz-x").click(); await tick();
  assert.equal(wiz(), null, "a reader leaves nothing behind: no question");
  tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(6);
  wiz().querySelector('[data-wiz="take"]').click(); await tick(6);
  if (wiz().querySelector('[data-wiz="take"]')) { wiz().querySelector('[data-wiz="take"]').click(); await tick(6); }
  assert.equal(wiz().querySelector(".wiz-readonly"), null, `the owner again on ${code()}`);
  wiz().querySelector(".wiz-head .wiz-x").click(); await tick();
  assert.equal(wiz().querySelector(".wiz-dialog:not(.wiz-nav-dialog)").hidden, false, "the owner is asked");
});

test("leaving the tab with a live session open asks: continue, leave and resume later, or leave without saving", async () => {
  const { panel, root, backend, tab, wiz, code, press, startFor } = await mount();
  const view = (id) => root.querySelector(`[data-action="cover-view"][data-id="${id}"]`);
  const nav = () => wiz()?.querySelector(".wiz-nav-dialog");
  // Before any session nothing is asked.
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.equal(panel._beforeLeave?.(), null, "A-01: nothing to ask");
  view("devices").click(); await tick();
  assert.equal(panel._coverView, "devices");
  view("calibration").click(); await tick(6);
  await startFor("cover.living_one");
  const unloads = [];
  const add = window.addEventListener.bind(window), remove = window.removeEventListener.bind(window);
  window.addEventListener = (type, handler, ...rest) => { if (type === "beforeunload") unloads.push(handler); return add(type, handler, ...rest); };
  window.removeEventListener = (type, handler, ...rest) => { if (type === "beforeunload") unloads.splice(unloads.indexOf(handler), 1); return remove(type, handler, ...rest); };
  try {
    await press("begin"); await tick();
    assert.equal(code(), "A-04");
    assert.equal(unloads.length, 1, "the browser warns before the page closes while the session is open");
    const event = new window.Event("beforeunload", { cancelable: true });
    unloads[0](event);
    assert.equal(event.defaultPrevented, true);
    // Another cover view: asked first, and nothing moves until the answer.
    view("devices").click(); await tick();
    assert.equal(panel._coverView, "calibration");
    assert.equal(nav().hidden, false);
    assert.equal(nav().querySelector("h4").textContent, "Calibration in progress");
    assert.equal(nav().querySelector("#wiz-nav-body").textContent,
      "If you leave now, the calibration will stay open for 30 minutes and you will be able to resume it from the Calibration tab. If you cancel it, the measurements taken so far will be lost.");
    assert.equal(nav().querySelector(".wiz-dialog-x").hidden, true, "centred: no ✕ (R-5)");
    assert.deepEqual([...nav().querySelectorAll(".actions button")].map((button) => [button.dataset.wiz, button.textContent, button.className]),
      [["nav-discard", "Leave without saving", "wiz-leave"], ["nav-later", "Leave and resume later", ""], ["nav-stay", "Continue calibration", "primary"]]);
    assert.equal(root.activeElement, nav().querySelector('[data-wiz="nav-stay"]'));
    nav().querySelector('[data-wiz="nav-stay"]').click(); await tick();
    assert.equal(panel._coverView, "calibration", "Continue keeps the wizard");
    assert.equal(nav().hidden, true);
    assert.equal(code(), "A-04");
    // The Bus monitor tab, then Escape: stays too.
    root.querySelector('[data-view="bus"]').click(); await tick();
    nav().dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true })); await tick();
    assert.equal(panel._view, "entities");
    // Leave and resume later: the panel moves on, the session stays open in Home Assistant.
    view("devices").click(); await tick();
    nav().querySelector('[data-wiz="nav-later"]').click(); await tick(4);
    assert.equal(panel._coverView, "devices");
    assert.equal(backend.calls.some((message) => message.action === "cancel"), false, "nothing cancelled");
    assert.equal(unloads.length, 0, "the browser's warning leaves with the wizard");
    assert.notEqual(backend.session.phase, "cancelled");
    // Back in the tab: the cover in progress is first, with Open session as its action.
    view("calibration").click(); await tick(8);
    const first = tab().querySelector(".cal-row");
    assert.equal(first.dataset.entity, "cover.living_one", "the cover in progress sits on top");
    assert.equal(first.querySelector(".cal-badge").dataset.status, "running");
    assert.equal(first.querySelector('[data-action="cal-tab-session"]').textContent, "Open session");
    // Reopened, taken back, and left without saving: Cancel reaches Home Assistant first.
    first.querySelector('[data-action="cal-tab-session"]').click(); await tick(6);
    for (let i = 0; i < 2 && wiz().querySelector('[data-wiz="take"]'); i++) { wiz().querySelector('[data-wiz="take"]').click(); await tick(6); }
    view("profiles").click(); await tick();
    assert.equal(nav().hidden, false);
    nav().querySelector('[data-wiz="nav-discard"]').click(); await tick(8);
    assert.equal(backend.calls.filter((message) => message.action === "cancel").length, 1);
    assert.equal(panel._coverView, "profiles");
  } finally {
    window.addEventListener = add; window.removeEventListener = remove;
  }
});

test("a landscape phone has the wizard full screen in two columns, Stop at the top of the actions (responsive map §3.2, D11, D12)", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  const short = css.slice(css.lastIndexOf("@media (max-height: 499px) and (orientation: landscape) {"));
  assert.match(short, /\.wiz \{ position: fixed; inset: 0;/, "full screen at any width");
  assert.match(short, /\.wiz-head \{ box-sizing: border-box; min-height: 44px;/, "a 44 px header");
  assert.match(short, /\.wiz-steps \{ display: none; \}/, "no stepper, the strip instead");
  assert.match(short, /\.wiz-columns \{[^}]*grid-template-columns: minmax\(0, 1fr\) calc\(clamp\(240px, 35%, 280px\) \+ var\(--cal-safe-right\)\);/);
  assert.match(short, /\.wiz-main \{ min-height: 0; overflow-y: auto;/, "the content scrolls");
  assert.match(short, /\.wiz-actions \{ position: static; min-height: 0; overflow-y: auto;/, "the actions scroll by themselves");
  assert.match(short, /\.wiz-actions > \[data-wiz="stop"\] \{ order: -1; \}/, "Stop always in view, at the top");
});

test("the Calibration in progress dialog is 592 px wide when centred, its three buttons on one row", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-nav-dialog \.wiz-dialog-card \{ width: min\(100%, 592px\);/);
  assert.match(css, /@media \(min-width: 720px\) and \(min-height: 500px\) \{ \.wiz-nav-dialog \.wiz-dialog-card \.actions \{ flex-wrap: nowrap; \} \}/, "wherever it is centred");
});

test("a click on a confirmation's backdrop is Continue the calibration", async () => {
  const { backend, wiz, press, startFor, panel } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  wiz().querySelector(".wiz-head .wiz-discard").click(); await tick();
  const exit = wiz().querySelector(".wiz-dialog:not(.wiz-nav-dialog)");
  assert.equal(exit.hidden, false);
  exit.querySelector(".wiz-dialog-card").click(); await tick();
  assert.equal(exit.hidden, false, "a click on the card keeps it");
  exit.click(); await tick();
  assert.equal(wiz().querySelector(".wiz-dialog:not(.wiz-nav-dialog)").hidden, true, "the backdrop continues");
  assert.equal(backend.calls.some((message) => message.action === "cancel"), false);
  const answer = panel._beforeLeave();
  wiz().querySelector(".wiz-nav-dialog").click();
  assert.equal(await answer, false, "Calibration in progress: the backdrop stays");
});

test("the time it stays open comes from Home Assistant's lease: 10 minutes after a movement", async () => {
  const { backend, wiz, press, startFor, panel } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await tick();
  Object.assign(backend.session, { recovery_seconds: 600 }); backend.emit(); await tick();
  const answer = panel._beforeLeave();
  assert.match(wiz().querySelector("#wiz-nav-body").textContent, /will stay open for 10 minutes/);
  wiz().querySelector('[data-wiz="nav-stay"]').click();
  assert.equal(await answer, false);
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
  await move(backend, { seconds: 24 });
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
  const radio = wiz().querySelector(`.wiz-picker input[value='${JSON.stringify(["one", "cover.living_one"])}']`);
  radio.checked = true; radio.dispatchEvent(new Event("change", { bubbles: true }));
  await tap("choose");
  const a = wiz().querySelector('input[name="path"][value="A"]'); a.checked = true; a.dispatchEvent(new Event("change", { bubbles: true })); await tick();
  await tap("path"); await tap("begin");
  await move(backend, { seconds: 22.5 }); // past the opening, within the closing time + margin: Stop is still offered
  assert.equal(code(), "A-05");
  assert.equal(button("endpoint").disabled, true, "an end stop is never confirmed by the tap that started the run");
  assert.equal(button("stop").disabled, false, "Stop is always available");
  await tap("endpoint");
  assert.equal(backend.calls.filter((message) => message.action === "endpoint").length, 1);
});

test("a stop frame well before the estimated run asks to check the end stop; the confirmation stays active", () => {
  const t = (key) => translations.en[key] || key;
  const cover = { name: "Kitchen 2", effective: { closing: { value: 20, origin: "native_fallback" } } };
  const at = (view, local = {}) => buildScreen({ t, stage: "session", path: "A", cover, elapsed: 8, local,
    view: { mode: "geometry", values: { opening_time: 22, closing_time: 21 }, samples: { lift: 4 }, readings: { gap: 3 }, slats: true, owner: true, sequence: 4, ...view } });
  const early = at({ step: "home", phase: "closing", motor_stopped: true, stopped_elapsed: 8 });
  assert.equal(early.code, "A-05");
  assert.deepEqual(early.notices, [{ tone: "warning", result: true, text: "The cover stopped earlier than expected (8.0 s of about 20 s): check that it is really fully closed before continuing." }]);
  assert.equal(early.actions[0].disabled, undefined, "the end stop stays pressable");
  assert.deepEqual(at({ step: "home", phase: "closing", motor_stopped: true, stopped_elapsed: 13 }).notices, [], "past 60 %: no warning");
  assert.equal(at({ step: "reset", phase: "closing", motor_stopped: true, stopped_elapsed: 5 }).notices.length, 1, "A-10 too");
  assert.equal(at({ step: "reset", phase: "closing", motor_stopped: true, stopped_elapsed: 5 }, { ackReadings: true }).notices.length, 0,
    "not on a return that confirms itself on the stop frame (§9.53)");
  const top = at({ step: "top", phase: "opening", motor_stopped: true, stopped_elapsed: 5 });
  assert.match(top.notices[0].text, /really fully open/, "the manual return to the top");
  // D-12: stopped is not «positioning»: no wait block telling to wait for the stop, the state instead of Stop.
  assert.deepEqual([top.code, top.title, top.wait ?? null], ["A-09", "The cover has stopped", null]);
  assert.deepEqual(top.actions.map((action) => [action.id, action.kind]), [["endpoint", "primary"], ["stopped", "state"]]);
  assert.equal(at({ step: "top", phase: "opening" }).title, "Positioning cover", "while it runs it is still a positioning");
});

test("S-01 says what happened when the panel knows more: It did not do what it should", async () => {
  const t = (key) => translations.en[key] || key;
  const view = { mode: "geometry", phase: "interrupted", reason: "stopped", step: "home", values: {}, samples: {}, readings: {}, owner: true, sequence: 9 };
  assert.equal(buildScreen({ t, stage: "session", path: "A", view, local: { misbehaved: true }, cover: { name: "K" } }).body, "The cover did not do what it should. Restart the calibration.");
  assert.equal(buildScreen({ t, stage: "session", path: "A", view, local: {}, cover: { name: "K" } }).body, translations.en.calReason_stopped, "a plain Stop keeps its text");
  const { backend, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend);
  await press("misbehaved"); await tick();
  assert.equal(code(), "S-01");
  assert.equal(wiz().querySelector(".wiz-body").textContent, "The cover did not do what it should. Restart the calibration.");
});

test("S-01 after the lift-off run stopped before ② says how to redo it; other steps keep the generic text", () => {
  const t = (key) => translations.en[key] || key;
  const body = (step) => buildScreen({ t, stage: "session", path: "A", cover: { name: "K" }, local: {},
    view: { mode: "geometry", phase: "interrupted", reason: "unexpected_stop", step, values: {}, samples: {}, readings: {}, owner: true, sequence: 9 } }).body;
  assert.equal(body("lift"), "The cover stopped before you pressed ②. Restart the calibration and press ② as soon as the bottom edge lifts off the rest.");
  assert.equal(body("half_open"), translations.en.calReason_unexpected_stop);
});

test("when the motor stops by itself on A-05 the end stop does not flicker disabled", async () => {
  const { backend, tab, wiz, code, press } = await mount({ guardMs: 700 });
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  const radio = wiz().querySelector(`.wiz-picker input[value='${JSON.stringify(["one", "cover.living_one"])}']`);
  radio.checked = true; radio.dispatchEvent(new Event("change", { bubbles: true })); await wait(720);
  wiz().querySelector('[data-wiz="choose"]').click(); await tick();
  const a = wiz().querySelector('input[name="path"][value="A"]'); a.checked = true; a.dispatchEvent(new Event("change", { bubbles: true })); await wait(720);
  wiz().querySelector('[data-wiz="path"]').click(); await tick(); await wait(720);
  wiz().querySelector('[data-wiz="begin"]').click(); await tick();
  backend.started(); backend.tick(30); backend.emit(); await tick();
  assert.equal(code(), "A-05");
  await wait(720);
  const endpoint = () => wiz().querySelector('[data-wiz="endpoint"]');
  assert.equal(endpoint().disabled, false);
  // The timer's stop frame: Stop goes away, nothing new appears under the finger.
  backend.session.motor_stopped = true; backend.emit(); await tick();
  assert.equal(wiz().querySelector('.wiz-actions [data-wiz="stop"]'), null);
  assert.equal(endpoint().disabled, false, "no hold for a button that only went away");
  void press;
});

test("a reopened slat and roll session of a cover that follows a profile is shown as path C", async () => {
  const session = { entry_id: "one", entity_id: "cover.kitchen_two", session_id: "session-1", sequence: 9, revision: 7, mode: "geometry",
    phase: "briefing", step: "lift", reason: null, values: {}, samples: {}, readings: {}, geometry: {}, travel_cm: null, stop_requested: false,
    slats: true, lift_attempts: 1, still_resting: false, gap_warning: false, touching_cm: 1, max_gap_cm: 20, gap_warn_cm: 10,
    saved_travel_cm: 110, expected_cm: null, can_repeat: false, save_modes: ["new"], reading_kind: "lift" };
  const { backend, tab, wiz, code, actions } = await mount({ session });
  tab().querySelector('[data-action="cal-tab-session"]').click(); await tick(6);
  assert.equal(code(), "C-06");
  assert.equal(wiz().querySelector(".wiz-steps li[data-step-state] > ul > li").textContent, "Remeasure all");
  assert.deepEqual(actions(), [], "reopening moves nothing");
  void backend;
});

test("the preview is announced before it starts and its end never says that something was saved", async () => {
  const t = (key) => translations.it[key] || key;
  // Under Ⓑ on A-02 the note now counts the profiles (R4-8); the preview is said where Ⓑ starts (B-02).
  assert.equal(buildScreen({ t, stage: "before", path: "B", cover: { name: "Cucina 2" } }).actions[0].note, translations.it.wiz_T318);
  assert.equal(buildScreen({ t, stage: "before", path: "C", scope: "points_only", cover: { name: "Cucina 2" } }).actions[0].note, translations.it.wiz_T318);
  assert.equal(buildScreen({ t, stage: "before", path: "C", scope: "times_only", cover: { name: "Cucina 2" } }).actions[0].note, undefined, "times only is live");
  const review = buildScreen({ t, language: "it", stage: "session", path: "A", cover: { name: "Cucina 2" },
    view: { mode: "geometry", phase: "review", values: { opening_time: 22, closing_time: 21 }, geometry: {}, travel_cm: 198, owner: true, sequence: 2 } });
  assert.deepEqual(review.actions.map((action) => action.id), ["save"], "the summary only saves");
  const real = buildScreen({ t, language: "it", stage: "saved", path: "A", cover: { name: "Cucina 2" }, local: { saved: { target: "profile_new", name: "cucina_2" } } });
  assert.equal(real.actions.find((action) => action.id === "refine").note, undefined, "no note under the button");
  assert.equal(real.body, `${translations.it.wiz_T155.replace("{name}", "cucina_2")}\n\n**Vuoi perfezionare la calibrazione?** Quattro letture col metro a un quarto e a tre quarti della corsa, più una verifica finale, renderanno la stima della posizione più precisa lungo tutta la corsa. Circa 4 minuti; la tapparella si muoverà.`,
    "T319 is the body's second paragraph");
  assert.deepEqual(real.actions.map((action) => [action.id, action.kind]), [["refine", "primary"], ["assign-profile", "secondary"], ["another", "secondary"], ["open-cover", "secondary"], ["close", "link"]]);
  const coverOnly = buildScreen({ t, language: "it", stage: "saved", path: "A", cover: { name: "Cucina 2" }, local: { saved: { target: "cover_only" } } });
  assert.equal(coverOnly.actions.some((action) => action.id === "assign-profile"), false, "no profile written, nothing to assign");
  assert.deepEqual(real.stepper.phases.map((phase) => [phase.key, phase.state]).slice(-2), [["summary", "done"], ["finetune", "future"]]);
  assert.equal(real.stepper.phases.at(-1).label, "Perfezionamento (facoltativo)");
  assert.equal(buildScreen({ t, language: "it", stage: "saved", path: "C", cover: { name: "Cucina 2" }, local: { saved: { target: "cover_only" } } })
    .actions.some((action) => action.id === "refine"), false, "not on C-34");
  const saved = buildScreen({ t, language: "it", stage: "saved", path: "C", cover: { name: "Cucina 2" }, local: { saved: { preview: true }, baseSaved: true } });
  assert.equal(saved.title, "Anteprima del riepilogo");
  assert.equal(saved.body, translations.it.wiz_T322);
  assert.equal(saved.preview, true);
  // On screen the note sits under its path, inside the radio's label.
  const { tab, wiz, press, pickCover } = await mount({ language: "it" });
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  await pickCover();
  await press("choose");
  const b = wiz().querySelector('input[name="path"][value="B"]').closest(".wiz-radio");
  assert.deepEqual([...b.querySelectorAll("small")].map((line) => line.textContent), ["Basta misurare la corsa del telo.", "1 profilo disponibile"],
    "under B, its explanation then the profiles available");
});

test("A-02 advises a path from the cover and the gateway's profiles, and preselects it", () => {
  const t = (key) => translations.en[key] || key;
  const advice = (screen) => screen.choice.options.filter((option) => option.badge).map((option) => [option.value, option.badge]);
  const note = (screen) => screen.choice.options.find((option) => option.value === "B").note;
  const tall = { id: "tall", name: "tall_two_leaf", slat: 4.4, referenceTravel: 198 }, low = { id: "low", name: "low_one_leaf", slat: 0, referenceTravel: 112 };
  // Never calibrated, no profile on the gateway: Ⓐ advised and preselected, Ⓑ cannot be chosen and says why.
  const none = buildScreen({ t, stage: "path", profiles: [], cover: { name: "Kitchen 2", status: "to_measure" } });
  assert.deepEqual(advice(none), [["A", "Recommended"]]);
  assert.equal(none.choice.options.find((option) => option.value === "B").disabled, true);
  assert.deepEqual(note(none), [translations.en.wiz_T453, translations.en.wiz_T401]);
  assert.equal(none.choice.value, "A");
  assert.equal(none.actions[0].disabled, false);
  assert.equal(none.subline, "Never calibrated", "the context says only that");
  assert.match(none.body, /If in doubt, choose this option\.$/);
  const c = none.choice.options.find((option) => option.value === "C");
  assert.deepEqual([c.disabled, c.note], [true, ["Only what is off gets corrected: tape readings, times, or everything.", "Calibrate the cover first."]], "no fine-tuning on a cover never measured");
  // G2-2: the introduction is one line and the advice; each option explains itself in its note.
  assert.equal(none.body, 'There are **three measurement paths**.\n\n"First cover of its type" is the recommended option because the cover has never been measured and there are no saved profiles. If in doubt, choose this option.');
  assert.deepEqual(none.choice.options.map((option) => option.note[0]), [translations.en.wiz_T452, translations.en.wiz_T453, translations.en.wiz_T454]);
  // Never calibrated, profiles available, no saved travel: no badge, nothing preselected, Ⓑ lists the profiles to compare.
  const some = buildScreen({ t, stage: "path", profiles: [tall, low], cover: { name: "Kitchen 2", status: "to_measure" } });
  assert.deepEqual(advice(some), [["A", "Recommended"]], "always one advised option (G4-2)");
  assert.equal(some.choice.value, "A");
  assert.equal(some.actions[0].disabled, false);
  assert.deepEqual(note(some), [translations.en.wiz_T453, "2 profiles available", "tall_two_leaf · With slats · Reference travel 198 cm", "low_one_leaf · Without slats · Reference travel 112 cm"]);
  assert.match(some.body, /^There are \*\*three measurement paths\*\*\.\n\n"First cover of its type" is the recommended option because the cover has never been measured and, without the length of its curtain, there is no telling whether a saved profile fits it\. If in doubt, choose this option\.$/);
  assert.deepEqual(note(buildScreen({ t, stage: "path", profiles: [tall], cover: { name: "Kitchen 2", status: "to_measure" } }))[1], "1 profile available");
  // A saved travel within 5 % of a profile's reference: Ⓑ advised, preselected and explained (closest first).
  const close = { id: "close", name: "near", slat: 0, referenceTravel: 109 };
  const similar = buildScreen({ t, stage: "path", profiles: [tall, low, close], cover: { name: "Kitchen 2", status: "to_measure", travel_cm: 110 } });
  assert.deepEqual([advice(similar), similar.choice.value], [[["B", "Recommended"]], "B"]);
  assert.deepEqual(note(similar), [translations.en.wiz_T453, "3 profiles available", 'Travel similar to the profile "near" (110 cm vs 109 cm)', 'Travel similar to the profile "low_one_leaf" (110 cm vs 112 cm)']);
  assert.match(similar.body, /"Like a cover already measured" is the recommended option because .* If in doubt, choose this option\.$/);
  assert.deepEqual(advice(buildScreen({ t, stage: "path", profiles: [tall], cover: { name: "Kitchen 2", status: "to_measure", travel_cm: 110 } })), [["A", "Recommended"]], "198 cm is not similar: the first of its type");
  // Already calibrated: Ⓒ; another choice gets its warning under it (Ⓑ: "a different profile" only when one is followed).
  const calibrated = (local, profile) => buildScreen({ t, stage: "path", local, profiles: [tall], cover: { name: "Kitchen 2", status: "rolls", last: "2026-10-01T09:00:00+00:00", profile } });
  assert.deepEqual([advice(calibrated({})), calibrated({}).choice.value, calibrated({}).subline], [[["C", "Recommended"]], "C", "Already calibrated (times and roll, Oct 1, 2026)"]);
  assert.deepEqual(note(calibrated({})), [translations.en.wiz_T453, "1 profile available"]);
  assert.equal(calibrated({}).choice.options.some((option) => option.warning), false);
  assert.equal(calibrated({ pathChoice: "B" }, { name: "tall_two_leaf" }).choice.options.find((option) => option.value === "B").warning, translations.en.wiz_T416);
  assert.equal(calibrated({ pathChoice: "B" }).choice.options.find((option) => option.value === "B").warning, translations.en.wiz_T417);
  assert.equal(calibrated({ pathChoice: "B" }, { name: "tall_two_leaf" }).subline,
    'Follows the profile "tall_two_leaf": the values are the profile\'s, without travel scaling, since the travel has not been measured.', "no measured travel (G2-1)");
});

test("A-21d defaults to updating the profile on the cover it was measured on, and A-34 says when a profile is left alone", () => {
  const t = (key) => translations.en[key] || key;
  const view = { mode: "geometry", phase: "review", values: { opening_time: 22, closing_time: 21 }, geometry: {}, travel_cm: 110, owner: true, sequence: 2 };
  const cover = (origin) => ({ name: "Kitchen 2", entity_id: "cover.kitchen_two", profile: { name: "tall", provenance: { opening: { origin_entity_id: origin } } }, followers: [], effective: {} });
  const choice = (origin, supports) => buildScreen({ t, stage: "session", path: "A", cover: cover(origin), view, local: { saveProfile: true }, supports })
    .profileBlock.choice.value;
  assert.equal(choice("cover.kitchen_two", () => true), "update", "the source cover updates its own profile by default, once that can be saved");
  assert.equal(choice("cover.kitchen_two", (target) => target !== "profile_update"), "new", "until then (no L5a) the default stays a new profile");
  assert.equal(choice("cover.hall", () => true), "new", "a follower creates a new one by default");
  const saved = (orphan) => buildScreen({ t, stage: "saved", path: "A", cover: { name: "Kitchen 2" }, local: { saved: { target: "profile_new", name: "kitchen_2", orphan } } });
  assert.deepEqual(saved("tall").note, { tone: "info", text: 'The profile "tall" is no longer followed by any cover: you can delete it from the Profiles tab.' });
  assert.equal(saved(null).note, null);
});

test("counts of zero and one use their own forms", () => {
  const t = (key) => translations.it[key] || key;
  const view = { mode: "geometry", phase: "review", values: { opening_time: 22, closing_time: 21 }, geometry: {}, travel_cm: 110, owner: true, sequence: 2 };
  const cover = (followers) => ({ name: "Cucina 2", profile: { name: "alte" }, followers, effective: {} });
  const review = (followers, local = {}) => buildScreen({ t, language: "it", stage: "session", path: "C", scope: "times_only", cover: cover(followers),
    view: { ...view, mode: "guided" }, local: { ackDescent: true, ...local } });
  assert.match(review([]).saveInfo.body, /Il profilo «alte» non cambierà\.\n/);
  assert.match(review(["Sala 3"]).saveInfo.body, /e l’altra tapparella che lo segue resterà com’è\./);
  assert.match(review(["Sala 2", "Sala 3"]).saveInfo.body, /e le altre 2 tapparelle che lo seguono resteranno come sono\./);
  const a21d = (followers) => buildScreen({ t, language: "it", stage: "session", path: "A", cover: cover(followers), view, local: { saveProfile: true },
    followerNames: followers.join(" e ") }).profileBlock;
  assert.equal(a21d([]).choice.options.find((option) => option.value === "update").description, "Nessun’altra tapparella lo segue.");
  assert.equal(a21d([]).name.line, "Questa tapparella seguirà il nuovo profilo. «alte» resterà senza tapparelle: potrai eliminarlo dalla scheda Profili.");
  assert.equal(a21d(["Sala 3"]).name.line, "Questa tapparella seguirà il nuovo profilo. «alte» resterà all'altra tapparella.");
  assert.equal(a21d(["Sala 2", "Sala 3"]).name.line, "Questa tapparella seguirà il nuovo profilo. «alte» resterà alle altre 2 tapparelle.");
  const update = buildScreen({ t, language: "it", stage: "session", path: "A", cover: cover(["Sala 3"]), view, local: { saveProfile: true, saveChoice: "update" } }).profileBlock;
  assert.equal(update.name, null, "updating the profile: no name and no sentence");
  assert.equal(update.switchLabel, "Salva anche come profilo riusabile, o aggiorna quello esistente", "the switch says it can also update");
  assert.equal(buildScreen({ t, language: "it", stage: "session", path: "A", cover: { name: "Cucina 2", followers: [], effective: {} }, view, local: {} }).profileBlock.switchLabel,
    "Salva anche come profilo riusabile", "without a profile the short label");
  assert.equal(a21d(["Sala 3"]).choice.options.find((option) => option.value === "update").description, "Cambierà anche l’altra tapparella che lo segue: Sala 3.");
  const b01 = (followerNames) => buildScreen({ t, language: "it", stage: "profile", path: "B", cover: cover([]), local: {},
    profiles: [{ id: "p", name: "alte", followers: followerNames.length, followerNames, measuredOn: "Sala 1" }] }).choice.options[0];
  assert.equal(b01([]).label, "alte · misurato su Sala 1");
  assert.deepEqual(b01([]).note, ["Nessuna tapparella lo segue"]);
  assert.deepEqual(b01(["Tapparella Cucina"]).note, ["Seguito da Tapparella Cucina"]);
  assert.deepEqual(b01(["Tapparella Cucina", "Portafinestra Terrazza"]).note, ["Seguito da Tapparella Cucina e Portafinestra Terrazza"]);
  assert.deepEqual(b01(["Tapparella Bagno", "Tapparella Studio", "Tapparella Corridoio"]).note, ["Seguito da Tapparella Bagno, Tapparella Studio e Tapparella Corridoio"]);
  assert.deepEqual(b01(["Tapparella Bagno", "Tapparella Studio", "Tapparella Corridoio", "Tapparella Cucina", "Portafinestra Terrazza"]).note,
    ["Seguito da Tapparella Bagno, Tapparella Studio, Tapparella Corridoio e altre 2"]);
  const en = (key) => translations.en[key] || key;
  assert.deepEqual(buildScreen({ t: en, language: "en", stage: "profile", path: "B", cover: cover([]), local: {},
    profiles: [{ id: "p", name: "tall", followerNames: ["X", "Y", "Z", "W"], measuredOn: "Hall" }] }).choice.options[0].note, ["Followed by X, Y, Z and 1 more"]);
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

test("A-01's list names the bus address and its notes in Italian too", async () => {
  const { tab, wiz, pickCover } = await mount({ language: "it" });
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.equal(wiz().querySelector(".wiz-pick-row .cal-row-name .muted").textContent, "Kitchen · Indirizzo: 91 · A: 9 · PL: 1");
  await pickCover("cover.kitchen_two");
  assert.equal(wiz().querySelector(".wiz-pick-notes .cal-note").textContent,
    "Questa tapparella è già calibrata (tempi e rullo, 29 set 2026) e segue il profilo «tall_two_leaf». Una nuova calibrazione, se la scegli al passo successivo, sostituirà i valori in uso; per correggerli, scegli il perfezionamento.");
  // Without a profile the clause about it falls.
  const t = (key) => translations.it[key] || key;
  const alone = buildScreen({ t, language: "it", stage: "choose", local: { coverKey: "k", coverPicked: true },
    covers: [{ key: "k", label: "Cucina 2", status: "times", last: "2026-10-01T09:00:00+00:00" }], cover: { name: "Cucina 2", profile: null } });
  assert.deepEqual(alone.picker.notes, [{ tone: "warning",
    text: "Questa tapparella è già calibrata (tempi misurati, 1 ott 2026). Una nuova calibrazione, se la scegli al passo successivo, sostituirà i valori in uso; per correggerli, scegli il perfezionamento." }]);
});

test("opened on a given cover, the wizard already has it chosen; from the tab's button it starts empty", async () => {
  const { panel, tab, wiz, code, button } = await mount();
  // From a row: Measure goes straight to the path choice on that cover.
  tab().querySelector('.cal-row[data-entity="cover.living_one"] [data-action="cal-tab-measure-cover"]').click(); await tick();
  assert.equal(code(), "A-02");
  assert.equal(wiz().querySelector(".wiz-cover").textContent, "Living room shutter 1");
  button("exit").click(); await tick();
  // Back on A-01 with a given cover (as after a cover-specific entry), its radio is ticked and the subtitle names it.
  const tabView = panel._calibrationTab;
  tabView._openWizard({ start: "choose", item: tabView._covers().find((item) => item.cover.entity_id === "cover.living_three") }); await tick();
  assert.equal(code(), "A-01");
  assert.equal(wiz().querySelector('.wiz-picker input[name="cover"]:checked').value, JSON.stringify(["one", "cover.living_three"]));
  assert.equal(wiz().querySelector(".wiz-head .muted").textContent, "Living room · Address: 91 · A: 9 · PL: 1");
  assert.equal(button("choose").disabled, false);
});

test("a missed heartbeat is a calm status, and the panel reconnects when the page is visible again", async () => {
  const { backend, panel, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await settle();
  const screenCode = code();
  const gateway = panel._calibrationTab._wizard._gateway;
  const notices = () => wiz().querySelector(".wiz-notices");
  // Safari puts the page aside: the heartbeat fails, as a closed connection would.
  const callWS = backend.hass.callWS;
  backend.hass.callWS = async (message) => {
    if (message.action === "heartbeat") throw Object.assign(new Error("Connection lost"), { code: 3 });
    return callWS(message);
  };
  await gateway._engine._perform("heartbeat"); await tick();
  assert.equal(notices().textContent, translations.en.wiz_T446);
  assert.ok(notices().querySelector(".notice.info, [data-tone='info'], .info"), "the interruption is told as information");
  assert.doesNotMatch(notices().textContent, /Connection or command failed/);
  // The page comes back: the panel resumes the session on its own and the status goes away.
  backend.hass.callWS = callWS;
  const resumes = () => backend.subscriptions.filter((message) => message.type === "myhome/cover_calibration/resume").length;
  const before = resumes();
  document.dispatchEvent(new window.Event("visibilitychange")); await settle();
  assert.equal(resumes(), before + 1);
  assert.equal(notices().textContent, "");
  assert.equal(code(), screenCode);
  // A command that really fails still says so.
  backend.hass.callWS = async (message) => { if (message.type === "myhome/cover_calibration/action" && message.action !== "heartbeat") throw new Error("boom"); return callWS(message); };
  await gateway._engine._perform("stop", {}); await tick();
  assert.match(notices().textContent, /Connection or command failed/);
});

test("A-07 carries its phone drawing beside the wide one; the stylesheet shows one per width", async () => {
  const { illustrationMarkup, PHONE_VERSION, SVG } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-illustration.js");
  assert.deepEqual(PHONE_VERSION, { "lift-sequence": "lift-sequence-mobile" });
  const host = document.createElement("div");
  host.innerHTML = illustrationMarkup("lift-sequence", "Step diagram", (value) => value);
  const drawings = [...host.querySelectorAll("svg")];
  assert.deepEqual(drawings.map((svg) => [svg.dataset.illustration, svg.getAttribute("class")]),
    [["lift-sequence", "wiz-illustration wiz-ill-wide"], ["lift-sequence-mobile", "wiz-illustration wiz-ill-phone"]]);
  assert.equal(drawings[1].getAttribute("viewBox"), "0 0 358 228");
  // The "②" stays live text in the panel's font, its colour themed like the rest.
  const label = drawings[1].querySelector("text");
  assert.equal(label.textContent, "②");
  assert.deepEqual([label.getAttribute("font-family"), label.getAttribute("font-weight"), label.getAttribute("fill")], ["inherit", "600", "var(--wiz-ill-surface,#fff)"]);
  assert.doesNotMatch(SVG["lift-sequence-mobile"], /#(?:009AC7|BDBDBD|2E2E2E)"/i, "no raw paint colour left");
  host.innerHTML = illustrationMarkup("lift-zoom", "Step diagram", (value) => value);
  assert.equal(host.querySelectorAll("svg").length, 1, "other drawings are one SVG");
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /@media \(max-width: 719px\) and \(min-height: 500px\), \(max-width: 719px\) and \(orientation: portrait\) \{\s*\.wiz-illustration\.wiz-ill-wide \{ display: none; \}/,
    "the phone's drawing in portrait only; a landscape phone keeps the wide one");
});

test("our texts name the shell's tabs with the shell's own labels, and never call a window a dialog in Italian", async () => {
  const fillIn = (text, values) => text.replace(/\{(\w+)\}/g, (_, key) => values[key]);
  assert.match(fillIn(translations.it.wiz_T409, { minutes: 30, tab: translations.it.calTabTab }), /dalla scheda Calibrazione\./);
  assert.match(fillIn(translations.en.wiz_T409, { minutes: 30, tab: translations.en.calTabTab }), /from the Calibration tab\./);
  assert.match(fillIn(translations.it.wiz_T431, { old: "x", tab: translations.it.profileListTitle }), /dalla scheda Profili\.$/);
  const italian = Object.entries(translations.it).filter(([key]) => key.startsWith("wiz_") || key.startsWith("calTab"));
  assert.deepEqual(italian.filter(([, text]) => /\bdialog|scheda (Calibration|Devices|Profiles)\b/.test(text)).map(([key]) => key), []);
});

test("a cover that follows a profile without a measured travel says the values are not scaled (A-02, C-01)", () => {
  const t = (key) => translations.it[key] || key;
  const cover = (travel_cm) => ({ name: "Cucina 2", status: "rolls", last: "2026-10-01T09:00:00+00:00", travel_cm, profile: { name: "alte" }, effective: {} });
  assert.equal(buildScreen({ t, language: "it", stage: "path", profiles: [], cover: cover(null) }).subline,
    "Segue il profilo «alte»: i valori sono quelli del profilo, senza adattamento alla corsa, che non è stata misurata.");
  assert.equal(buildScreen({ t, language: "it", stage: "path", profiles: [], cover: cover(110) }).subline, "Segue il profilo «alte»");
  const unscaled = buildScreen({ t, language: "it", stage: "current", path: "C", cover: cover(null) }).body.split("\n\n");
  assert.equal(unscaled[0], "Segue il profilo «alte»: i valori sono quelli del profilo, senza adattamento alla corsa, che non è stata misurata.");
  assert.match(unscaled[1], /^Nel passo successivo/);
  assert.doesNotMatch(unscaled.join(" "), /cm/);
  assert.match(buildScreen({ t, language: "it", stage: "current", path: "C", cover: cover(110) }).body, /^Cucina 2 segue il profilo «alte», adattato alla sua corsa del telo di 110 cm/);
});

test("how to tell the slats is a closed toggle right after the question (A-03); times only (C-35) says nothing about slats", async () => {
  const { wiz, code, startFor } = await mount();
  await startFor("cover.living_one");
  assert.equal(code(), "A-03");
  const fieldset = wiz().querySelector("fieldset.wiz-radios");
  const help = fieldset.querySelector("legend + details.wiz-help");
  assert.ok(help, "the toggle follows the question");
  assert.equal(help.open, false, "closed by default");
  assert.equal(help.querySelector("summary").textContent, "How to tell if it has slats");
  assert.match(help.textContent, /Slats are the horizontal strips/);
  assert.doesNotMatch(wiz().querySelector(".wiz-body").textContent, /horizontal strips/, "no longer in the body");
  help.open = true;
  const t = (key) => translations.en[key] || key;
  const timesOnly = buildScreen({ t, stage: "before", path: "C", scope: "times_only", cover: { name: "Kitchen 2", travel_cm: 110 } });
  assert.equal(timesOnly.choice, null);
  assert.equal(timesOnly.help, null, "times only: no slats help (M5-5)");
  assert.doesNotMatch(timesOnly.body, /slats|horizontal strips/, "nor any word about slats");
});

test("a lift-off gap under 1 cm repeats the run and the repeat says which value and why (G2-9)", async () => {
  const { backend, code, press, type, startFor, wiz } = await mount({ language: "it" });
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  assert.equal(code(), "A-08");
  assert.equal(wiz().querySelector("#wiz-field-hint").textContent, "Di solito 1–4 cm.");
  // 0,5 is sent as it is (no rounding): under the backend's 1 cm the edge still rests.
  await type("0,5");
  assert.equal(backend.calls.filter((message) => message.action === "reading").at(-1).reading_cm, 0.5);
  assert.equal(backend.session.lift_attempts, 2, "the backend repeats the lift-off");
  assert.equal(wiz().querySelector(".wiz-result-notices").textContent,
    "Hai indicato 0,5 cm: sotto 1 cm il bordo conta come ancora appoggiato, quindi la corsa viene ripetuta.");
  // Back at the bottom, the lift-off screen repeats it.
  await move(backend); await press("endpoint"); backend.stopped(); await tick();
  assert.equal(code(), "A-07");
  assert.match(wiz().querySelector(".wiz-result-notices").textContent, /^Hai indicato 0,5 cm/);
});

test("while the backend waits for the actuator's stop the screen says «Stopping…» with the stopwatch at the press (G2-10)", async () => {
  const { backend, code, press, startFor, wiz } = await mount({ language: "it" });
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend);
  await press("lift");
  assert.equal(backend.session.phase, "geometry_wait_stop");
  assert.equal(code(), "A-07");
  const bar = wiz().querySelector(".wiz-actions");
  assert.deepEqual([...bar.children].map((item) => [item.tagName, item.textContent.trim()]), [["P", "Arresto in corso…"]], "no disabled ①/②");
  assert.equal(bar.querySelector('[data-wiz="stopping"]').getAttribute("role"), "status");
  const watch = wiz().querySelector(".wiz-stopwatch");
  assert.equal(watch.hidden, false);
  assert.match(watch.textContent, /^Cronometro\s*fermo a \d+,\d s$/);
  const shown = watch.textContent;
  await new Promise((resolve) => setTimeout(resolve, 120)); backend.tick?.(1); await tick();
  assert.equal(wiz().querySelector(".wiz-stopwatch").textContent, shown, "frozen");
  backend.stopped(); await tick();
  assert.equal(code(), "A-08");
  // The actuator never confirmed: S-01, said plainly.
  const t = (key) => translations.it[key] || key;
  const screen = buildScreen({ t, language: "it", stage: "session", path: "A", cover: { name: "Cucina 2" }, local: {},
    view: { mode: "geometry", phase: "interrupted", reason: "not_stopped", step: "lift", values: {}, samples: {}, readings: {}, owner: true, sequence: 9 } });
  assert.deepEqual([screen.code, screen.body], ["S-01", "La tapparella non ha confermato l'arresto: ricomincia la calibrazione."]);
});

test("a heartbeat refused as expired after a reconnection resumes the same session; only a session Home Assistant ended shows S-06 (M3-1)", async () => {
  const { backend, panel, wiz, code, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await settle();
  const before = code();
  const gateway = panel._calibrationTab._wizard._gateway;
  const callWS = backend.hass.callWS;
  // The page came back on a new socket: the old token is refused as "expired", but the session is still there.
  backend.hass.callWS = async (message) => {
    if (message.action === "heartbeat") throw Object.assign(new Error("not owned by this connection"), { code: "calibration_expired" });
    return callWS(message);
  };
  const resumes = () => backend.subscriptions.filter((message) => message.type === "myhome/cover_calibration/resume").length;
  const count = resumes();
  await gateway._engine._perform("heartbeat"); await settle();
  backend.hass.callWS = callWS;
  assert.equal(gateway.status.expired, false);
  assert.notEqual(code(), "S-06", "no terminal screen while Home Assistant still has the session");
  assert.equal(resumes(), count + 2, "one read to check, one to resume the same session");
  assert.equal(backend.session.session_id, gateway.view.session_id);
  await settle();
  assert.equal(code(), before);
  // Home Assistant ended it for real: the check is refused, and only then the wizard says so.
  backend.hass.callWS = async (message) => {
    if (message.action === "heartbeat") throw Object.assign(new Error("expired"), { code: "calibration_expired" });
    return callWS(message);
  };
  backend.session.session_id = "gone";
  await gateway._engine._perform("heartbeat"); await settle();
  assert.equal(gateway.status.expired, true);
  assert.equal(code(), "S-06");
  backend.hass.callWS = callWS;
});

test("coming back to the page asks Home Assistant at once (M3-1)", async () => {
  const { backend, startFor, press } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await settle();
  const beats = () => backend.calls.filter((message) => message.action === "heartbeat").length;
  const count = beats();
  document.dispatchEvent(new window.Event("visibilitychange")); await settle();
  assert.equal(beats(), count + 1);
});

test("«Start over» after an ended session carries nothing of the old measurement (M3-2)", async () => {
  const { backend, panel, wiz, code, press, type, startFor } = await mount({ language: "it" });
  const toLiftReading = async () => {
    await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
    await press("ack:lift"); await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  };
  await startFor("cover.living_one");
  await toLiftReading();
  await type("2");
  assert.equal(panel._calibrationTab._wizard._local.lastGap, 2);
  // Home Assistant ends the session.
  const gateway = panel._calibrationTab._wizard._gateway, callWS = backend.hass.callWS;
  backend.hass.callWS = async (message) => { if (message.action === "heartbeat") throw Object.assign(new Error("expired"), { code: "calibration_expired" }); return callWS(message); };
  backend.session.session_id = "gone";
  await gateway._engine._perform("heartbeat"); await settle();
  backend.hass.callWS = callWS;
  assert.equal(code(), "S-06");
  await press("start-over");
  assert.equal(code(), "A-03");
  const local = panel._calibrationTab._wizard._local;
  assert.deepEqual([local.lastGap, local.baseReadings, local.fineReadings, local.review, local.reachedPhase], [null, null, null, null, null]);
  await toLiftReading();
  assert.equal(code(), "A-08");
  assert.equal(wiz().querySelector('[name="reading_cm"]').value, "", "the gap field starts empty");
  assert.equal(wiz().querySelector(".wiz-field").getAttribute("autocomplete"), "off");
  const lift = [...wiz().querySelectorAll(".wiz-steps li li")].find((item) => item.textContent.startsWith("Stacco"));
  assert.match(lift.textContent, /s · —$/, "no gap in the stepper before this session's reading");
});

test("two minutes before the idle expiry a waiting screen warns, counting the minutes down (M3)", () => {
  const t = (key) => translations.it[key] || key;
  const now = Date.parse("2026-10-05T13:00:00Z");
  const at = (seconds, extra = {}) => buildScreen({ t, language: "it", stage: "session", path: "A", local: { ackLift: true, ackAscent: true }, now, cover: { name: "Cucina 2" },
    view: { mode: "geometry", step: "opening", phase: "briefing", values: {}, samples: {}, readings: {}, slats: true, owner: true, sequence: 9, recoverable: true, attached: true,
      idle_expires_at: new Date(now + seconds * 1000).toISOString(), ...extra } });
  const warning = (screen) => screen.notices.find((notice) => /scade fra/.test(notice.text));
  assert.equal(warning(at(300)), undefined, "five minutes left: nothing yet");
  assert.deepEqual(warning(at(110)), { tone: "warning", result: true,
    text: "La sessione scade fra 2 min se non prosegui: la tapparella verrà liberata e le misure andranno perse." });
  assert.match(warning(at(50)).text, /fra 1 min/);
  assert.equal(warning(at(-5)), undefined, "past the deadline the backend's own end decides");
  assert.equal(warning(at(60, { phase: "opening" })), undefined, "not while the cover moves");
});

test("an ended session keeps the step it reached, greyed, in the stepper and the phone's strip (M3-3)", async () => {
  const { backend, panel, wiz, code, press, type, startFor } = await mount({ language: "it" });
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  await type("3"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  assert.equal(wiz().querySelector(".wiz-compact-line").textContent, "Salita · 3 di 7");
  const gateway = panel._calibrationTab._wizard._gateway, callWS = backend.hass.callWS;
  backend.hass.callWS = async (message) => { if (message.action === "heartbeat") throw Object.assign(new Error("expired"), { code: "calibration_expired" }); return callWS(message); };
  backend.session.session_id = "gone";
  await gateway._engine._perform("heartbeat"); await settle();
  backend.hass.callWS = callWS;
  assert.equal(code(), "S-06");
  assert.equal(wiz().querySelector(".wiz-compact-line").textContent, "Interrotta · Salita 3 di 7");
  assert.ok(wiz().querySelector(".wiz-compact").hasAttribute("data-interrupted"));
  const steps = wiz().querySelector(".wiz-steps");
  assert.ok(steps.hasAttribute("data-interrupted"));
  assert.equal(steps.querySelector('li[data-step-state="current"] > .wiz-step-label').textContent, "Salita");
  assert.match(steps.querySelector(".wiz-steps-line").textContent, /^Interrotta · Salita 3 di 7$/);
  // Starting over clears it.
  await press("start-over");
  assert.equal(wiz().querySelector(".wiz-steps").hasAttribute("data-interrupted"), false);
  assert.equal(wiz().querySelector(".wiz-compact-line").textContent, "Preparazione · 2 di 7");
});

test("choosing a cover on A-01 patches the list in place: same content area, same rows (M3-4)", async () => {
  const { tab, wiz, pickCover } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  const main = wiz().querySelector(".wiz-main"), rowOf = (id) => wiz().querySelector(`.wiz-pick-row[data-entity="${id}"]`);
  const kept = rowOf("cover.living_three");
  await pickCover("cover.kitchen_two");
  assert.equal(wiz().querySelector(".wiz-main"), main, "the frame is not rebuilt");
  assert.equal(rowOf("cover.living_three"), kept);
  assert.match(wiz().querySelector(".wiz-head .muted").textContent, /Kitchen/, "the header is patched");
  await pickCover("cover.living_three");
  assert.equal(rowOf("cover.living_three"), kept);
  assert.ok(kept.classList.contains("is-selected"));
});

test("A-02 says why the advised option is advised, impersonally, and says nothing when nothing is advised (G3-1)", () => {
  const t = (key) => translations.it[key] || key;
  const tall = { id: "tall", name: "alte", slat: 4.4, referenceTravel: 109 };
  const reason = (cover, profiles) => buildScreen({ t, language: "it", stage: "path", profiles, cover: { name: "Cucina 2", ...cover } }).body.split("\n\n")[1].replace(/ Nel dubbio, scegli questa opzione\.$/, "");
  assert.equal(reason({ status: "rolls", last: "2026-10-01T09:00:00+00:00" }, [tall]), "«Perfezionamento» è l'opzione consigliata perché questa tapparella è già calibrata.");
  assert.equal(reason({ status: "rolls", last: "2026-10-01T09:00:00+00:00", profile: { name: "alte" } }, [tall]),
    "«Perfezionamento» è l'opzione consigliata perché questa tapparella è già calibrata e segue il profilo «alte».");
  assert.equal(reason({ status: "to_measure" }, [tall]),
    "«Prima tapparella del suo tipo» è l'opzione consigliata perché la tapparella non è mai stata misurata e, senza la lunghezza del telo, non si può dire se un profilo salvato le si adatti.");
  assert.equal(reason({ status: "to_measure" }, []), "«Prima tapparella del suo tipo» è l'opzione consigliata perché la tapparella non è mai stata misurata e non ci sono profili salvati.");
  assert.equal(reason({ status: "to_measure", travel_cm: 110 }, [tall]),
    "«Come una tapparella già misurata» è l'opzione consigliata perché la corsa del telo (110 cm) è vicina a quella del profilo «alte» (109 cm).");
  const none = buildScreen({ t, language: "it", stage: "path", profiles: [{ ...tall, referenceTravel: 198 }], cover: { name: "Cucina 2", status: "to_measure", travel_cm: 110 } });
  assert.equal(none.body, "Ci sono **tre percorsi di misurazione**.\n\n«Prima tapparella del suo tipo» è l'opzione consigliata perché la corsa del telo (110 cm) non è vicina a quella di nessun profilo salvato. Nel dubbio, scegli questa opzione.",
    "travel known, no similar profile: still one advice (G4-2)");
  assert.deepEqual(none.choice.options.filter((option) => option.badge).map((option) => option.value), ["A"]);
});

test("«The edge is still resting» repeats the lift-off without a value, and the repeat warns by origin (G3-2, G3-3)", async () => {
  const { backend, code, press, startFor, wiz, button } = await mount({ language: "it" });
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  assert.equal(code(), "A-08");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => [item.dataset.wiz, item.textContent, item.className.replace("wiz-action ", "")]),
    [["reading", "Fatto, avanti", "primary"], ["resting", "Il bordo è ancora appoggiato", "secondary"]]);
  await press("resting");
  assert.equal(backend.calls.filter((message) => message.action === "reading").at(-1).reading_cm, 0, "the backend's path of a value under 1 cm");
  assert.equal(backend.session.lift_attempts, 2);
  const notice = wiz().querySelector(".wiz-result-notices .wiz-notice");
  assert.equal(notice.dataset.tone, "warning");
  assert.equal(notice.textContent, "Il bordo era ancora appoggiato: la corsa di stacco viene ripetuta.");
});

test("a value the field refuses says why under it, never a silent red (G3-4)", async () => {
  const { backend, code, press, type, startFor, wiz, actions } = await mount({ language: "it" });
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  assert.equal(code(), "A-08");
  const error = () => wiz().querySelector("#wiz-field-error");
  assert.equal(error().hidden, true);
  await type("25");
  assert.equal(error().hidden, false);
  assert.equal(error().textContent, "Valore oltre il massimo (20 cm): controlla la misura.");
  assert.equal(wiz().querySelector('[name="reading_cm"]').getAttribute("aria-invalid"), "true");
  assert.match(wiz().querySelector('[name="reading_cm"]').getAttribute("aria-describedby"), /wiz-field-error/);
  assert.equal(actions().includes("reading"), false, "nothing sent");
  await type("due");
  assert.equal(error().textContent, "Scrivi un numero di centimetri, con la virgola o il punto per i decimali.");
  const input = wiz().querySelector('[name="reading_cm"]');
  input.value = "2"; input.dispatchEvent(new Event("input", { bubbles: true })); await tick();
  assert.equal(error().hidden, true, "typing again clears it");
});

test("A-08b advises repeating: «Repeat the measurement» is the primary, «Ignore and continue» the outlined secondary; its warning is amber on dark themes (G3-5)", async () => {
  const { backend, code, press, type, startFor, wiz } = await mount();
  await startFor("cover.living_one");
  await press("begin"); await move(backend); await press("endpoint"); backend.stopped(); await tick();
  await press("ack:lift"); await press("next"); await move(backend); await press("lift"); backend.stopped(); await tick();
  await type("12");
  assert.equal(code(), "A-08");
  assert.deepEqual([...wiz().querySelectorAll(".wiz-actions .wiz-action")].map((item) => [item.dataset.wiz, item.textContent, item.className.replace("wiz-action ", "")]),
    [["repeat", "Repeat the measurement", "primary"], ["next", "Ignore and continue", "secondary"]]);
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\[data-theme="dark"\] \.wiz-notice\[data-tone="warning"\][^{]*\{ color: color-mix\(in srgb, var\(--panel-warning\) 70%/);
});

test("C-03 asks about the slats with the answer of the last calibration preselected (G4-5)", () => {
  const t = (key) => translations.it[key] || key;
  const before = (slat, local = {}) => buildScreen({ t, language: "it", stage: "before", path: "C", scope: "times_and_rolls", local,
    cover: { name: "Cucina 2", effective: slat === undefined ? {} : { slat_time_s: { value: slat } } } });
  const c03 = before(0);
  assert.equal(c03.code, "C-03");
  assert.equal(c03.choice.label, "Ha le lamelle?");
  assert.ok(c03.choice.help, "with its help");
  assert.equal(c03.choice.value, "no", "known: without slats");
  assert.equal(before(2.4).choice.value, "yes");
  assert.equal(before(undefined).choice.value, "yes", "unknown: with slats");
  assert.equal(before(0, { slats: true }).choice.value, "yes", "the user's own answer wins");
});

test("no «—» inside a sentence: without the datum the variant that does not name it (M5-6)", () => {
  const t = (key) => translations.it[key] || key;
  const before = (scope, travel_cm) => buildScreen({ t, language: "it", stage: "before", path: "C", scope, cover: { name: "Cucina 2", travel_cm } }).body;
  assert.match(before("times_only", null), /I due coefficienti di rullo e la corsa del telo resteranno quelli in uso/);
  assert.match(before("times_only", 110), /la corsa del telo, 110 cm, resteranno/);
  assert.match(before("points_only", null), /La corsa del telo non verrà rimisurata\./);
  for (const scope of ["times_only", "points_only"]) assert.doesNotMatch(before(scope, null), /—/);
  const all = Object.entries(translations.it).filter(([key]) => /^wiz_T(230|235|489|490|491)$/.test(key));
  assert.equal(all.length, 5);
});

test("a tap on the Steps sheet's backdrop closes it, as every sheet and dialog (M6-1, R7-7)", async () => {
  const { wiz, startFor } = await mount();
  await startFor("cover.living_one");
  wiz().querySelector('[data-wiz="steps"]').click(); await tick();
  const sheet = wiz().querySelector(".wiz-sheet");
  assert.equal(sheet.hidden, false);
  sheet.querySelector(".wiz-sheet-card").click(); await tick();
  assert.equal(sheet.hidden, false, "a tap inside the card keeps it");
  sheet.click(); await tick(); await new Promise((resolve) => setTimeout(resolve, 260));
  assert.equal(sheet.hidden, true, "a tap on the backdrop closes it");
});

test("the wizard's actions, Take control and PASSI take the shell's 8 px radius (Q-18); the compact order is round (Q-26)", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /--cal-btn-radius: 8px; \}/);
  for (const rule of [/\.wiz-action \{[^}]*border-radius: var\(--cal-btn-radius\);/, /\.wiz-take \{[^}]*border-radius: var\(--cal-btn-radius\);/]) assert.match(css, rule);
  assert.match(css, /\.cal-filterbar\.is-chips \.cal-filterbar-sort \{[^}]*border-radius: 999px;/, "Q-26: the compact order is drawn as a chip, round");
  assert.equal(css.match(/\.wiz-steps-button \{[^}]*border-radius: var\(--cal-btn-radius\);/g)?.length, 2, "PASSI in both layouts");
});

test("the wizard's layouts follow the content width as the layout module says, buttons 44 px (R-1)", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  const { WIZARD_BANDS, wizardBand, SHORT } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-layout.js");
  assert.match(css, new RegExp(`@container caltab \\(min-width: ${WIZARD_BANDS.threeColumns}px\\) \\{\\s*\\.wiz-columns \\{ grid-template-columns: 240px minmax\\(0, 1fr\\) clamp\\(240px, 30%, 320px\\);`));
  assert.match(css, new RegExp(`@container caltab \\(min-width: ${WIZARD_BANDS.intermediate}px\\) and \\(max-width: ${WIZARD_BANDS.threeColumns - 1}px\\) \\{\\s*\\.wiz-columns \\{ grid-template-columns: minmax\\(0, 1fr\\) clamp\\(240px, 30%, 320px\\);`));
  assert.match(css, new RegExp(`@container caltab \\(max-width: ${WIZARD_BANDS.intermediate - 1}px\\) \\{\\s*/\\*[^*]*\\*/\\s*\\.wiz, \\.wiz\\.cal-batch-wiz \\{ overflow: clip; --wiz-single: 1; \\}`));
  assert.match(css, new RegExp(`@container wizbar \\(min-width: ${WIZARD_BANDS.wideBar}px\\)`));
  assert.ok(css.includes(`@media ${SHORT} {`));
  assert.deepEqual([1200, 1000, 999, 700, 699].map((width) => wizardBand(width)), ["three-columns", "three-columns", "intermediate", "intermediate", "single-column"]);
  assert.equal(wizardBand(390, { phone: true }), "phone");
  assert.equal(wizardBand(844, { short: true }), "landscape");
  assert.match(css, /\.wiz-action \{ width: 100%; min-height: 44px;/);
  assert.match(css, /\.wiz-actions \{ display: grid; grid-template-columns: minmax\(0, 1fr\); gap: 12px; align-content: start; padding: 24px;/);
});

test("a 40 px fade of the surface under every fixed or sticky action bar and at the landscape centre's edge (R-2)", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  const fades = css.match(/\.wiz-actions::before \{ content: ""; position: absolute; inset-inline: 0; bottom: calc\(100% \+ 1px\); height: 40px;/g) || [];
  assert.equal(fades.length, 2, "the phone's fixed bar and the single column's sticky bar");
  assert.match(css, /\.wiz-main::after \{ content: ""; flex: none; position: sticky;[^}]*height: 40px;/);
  assert.match(css, /\.wiz-columns:has\(> \.wiz-actions\.has-more\) > \.wiz-main::after \{ opacity: 1; \}/);
});

test("«Passi» has its title and ✕: a centred card, a sheet from the bottom, a square side panel in landscape (R-3)", async () => {
  const { wiz, tab } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  const head = wiz().querySelector(".wiz-sheet .wiz-sheet-head");
  assert.equal(head.querySelector(".wiz-sheet-title").textContent, "Steps");
  assert.ok(head.querySelector('.wiz-sheet-close[data-wiz="steps-close"]'));
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-sheet-card \{[^}]*width: min\(100%, 360px\);/);
  const short = css.slice(css.lastIndexOf("@media (max-height: 499px) and (orientation: landscape) {"));
  assert.match(short, /\.wiz-sheet \.wiz-sheet-card \{ width: calc\(320px \+ var\(--cal-safe-right\)\); height: 100%; max-height: none; border-radius: 0;/);
  assert.match(short, /animation: wiz-panel-in/);
});

test("every wizard, block and dialog button centres its label and takes the shell's radius (R-4)", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-action, \.wiz-take, \.wiz-dialog-card \.actions button, dialog\.cal-dialog \.dialog-foot button, \.cal-block-action > button \{\s*justify-content: center; text-align: center; border-radius: var\(--cal-btn-radius\); \}/);
});

test("dialogs are 560 px centred cards, and sheets with a handle, a ✕ that keeps the calibration and stacked buttons (R-5)", async () => {
  const { wiz, press, startFor } = await mount();
  await startFor("cover.living_one");
  await press("begin");
  const original = globalThis.matchMedia;
  try {
    globalThis.matchMedia = (query) => ({ matches: query.includes("max-width") });
    wiz().querySelector(".wiz-head .wiz-x").click(); await tick();
    const exit = wiz().querySelector(".wiz-dialog:not(.wiz-nav-dialog)");
    assert.equal(exit.querySelector(".wiz-dialog-x").hidden, false, "a sheet has its ✕");
    exit.querySelector(".wiz-dialog-x").click(); await tick();
    await new Promise((resolve) => setTimeout(resolve, 260));
    assert.equal(exit.hidden, true, "✕ keeps the calibration");
  } finally { globalThis.matchMedia = original; }
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-dialog-card \{ box-sizing: border-box; width: min\(100%, 560px\); padding: 24px;/);
  assert.match(css, /dialog\.cal-dialog::before, \.wiz-dialog \.wiz-dialog-card::before \{ content: ""; display: block; flex: none; width: 40px; height: 4px;/, "the sheets' handle");
  assert.match(css, /dialog\.cal-dialog \{ width: min\(100%, 560px\); margin: auto auto 0; \}/, "landscape: a 560 px sheet, centred");
});

test("a gated primary stays a primary, disabled: A-01's Continue before a choice, the sequence's Start with nothing ticked (Q-29)", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  const rule = css.match(/\.wiz-action\.primary:disabled, \.wiz-action\.primary:disabled:hover \{([^}]*)\}/)?.[1] || "";
  assert.match(rule, /background: color-mix\(in srgb, var\(--panel-accent\) 38%, var\(--panel-surface\)\)/);
  assert.match(rule, /box-shadow: none/);
  assert.doesNotMatch(rule, /background: transparent/, "not an outlined button");
  const { wiz, tab, button } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  assert.ok(button("choose").classList.contains("primary"));
  assert.equal(button("choose").disabled, true);
});

test("in the one-column layout the action bar is docked to the window's bottom (Home Assistant scrolls <html>) (U-1)", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz\.is-docked > \.wiz-frame > \.wiz-columns > \.wiz-actions \{ position: fixed; z-index: 7; inset-inline-start: var\(--dock-left\); bottom: 0;/);
  assert.match(css, /\.wiz\.is-docked > \.wiz-frame > \.wiz-columns \{ padding-bottom: var\(--dock-height\); \}/, "the wizard keeps the bar's room");
  const { dockBar } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-layout.js");
  const { wiz, tab } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  const stop = dockBar(wiz());
  assert.equal(wiz().classList.contains("is-docked"), false, "without a layout nothing is docked");
  stop();
});


test("D-02: with columns the sequence's status and Start are held 16 px under the top while an outer box scrolls", async () => {
  const { dockBar } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-layout.js");
  const wiz = document.createElement("div"), column = document.createElement("div"), block = document.createElement("div");
  block.className = "cal-batch-sticky"; column.append(block); wiz.append(column); document.body.append(wiz);
  const rect = (top, height) => ({ top, bottom: top + height, height, left: 0, right: 600, width: 600 });
  let scrolled = 0;
  wiz.getBoundingClientRect = () => rect(100 - scrolled, 2000);
  column.getBoundingClientRect = () => rect(100 - scrolled, 2000);
  // Where it sits in the flow (the transform is cleared before each measure): the column's top + its 24 px padding.
  block.getBoundingClientRect = () => rect(124 - scrolled, 90);
  const original = window.getComputedStyle, frame = window.requestAnimationFrame;
  window.getComputedStyle = (element) => ({ position: element === block ? "sticky" : "static", paddingBottom: "24px", getPropertyValue: () => "" });
  window.requestAnimationFrame = (callback) => setTimeout(callback, 0);
  try {
    const stop = dockBar(wiz);
    assert.equal(block.style.transform, "", "in place while the column's top is in view");
    scrolled = 600; window.dispatchEvent(new window.Event("scroll")); await new Promise((resolve) => setTimeout(resolve, 5));
    assert.equal(block.style.transform, "translateY(492px)", "16 px under the window's top: 16 − (124 − 600)");
    scrolled = 1990; window.dispatchEvent(new window.Event("scroll")); await new Promise((resolve) => setTimeout(resolve, 5));
    assert.equal(block.style.transform, "translateY(1862px)", "never past the column's end: 2100 − 24 − 214 = 1862");
    stop();
    assert.equal(block.style.transform, "");
  } finally { window.getComputedStyle = original; window.requestAnimationFrame = frame; wiz.remove(); }
});

test("D-21: on A-02 the stepper shows the steps of the path ticked so far", async () => {
  const { wiz, code, press, pickCover, tab } = await mount();
  tab().querySelector('[data-action="cal-tab-measure"]').click(); await tick();
  await pickCover("cover.living_one"); await press("choose");
  assert.equal(code(), "A-02");
  const phases = () => wiz().querySelectorAll(".wiz-steps > ol > li").length;
  const tick_ = async (value) => { const radio = wiz().querySelector(`input[name="path"][value="${value}"]`); radio.checked = true; radio.dispatchEvent(new Event("change", { bubbles: true })); await tick(); };
  await tick_("B");
  assert.equal(phases(), 3, "path B: introduction, readings, summary");
  await tick_("A");
  assert.equal(phases(), 7);
});

test("D-22: from a 560 px bar every action is centred at 480, a red Stop alone included", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /@container wizbar \(min-width: 560px\) \{ \.wiz-actions > \*, \.wiz-actions > button\.danger \{ box-sizing: border-box; width: 100%; max-width: 480px; justify-self: center; \} \}/);
  assert.match(css, /button\.danger \{ color: var\(--panel-error\); justify-self: start; \}/, "the shell's rule it outweighs");
});

test("D-23/D-36: a number and its unit are held on one line in bodies, notices, waits and hints, the text unchanged", async () => {
  const { units, inline } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-text.js");
  assert.equal(units("fra 73,6 e 109,1 cm."), 'fra 73,6 e <span class="cal-nb">109,1 cm</span>.');
  assert.equal(units("circa 30 s) · 600 secondi · 12 %"), 'circa <span class="cal-nb">30 s</span>) · <span class="cal-nb">600 secondi</span> · <span class="cal-nb">12 %</span>');
  assert.equal(units("3 scatti, 2 sere"), "3 scatti, 2 sere", "only units");
  assert.match(inline("**21 s** o 20 s"), /<strong><span class="cal-nb">21 s<\/span><\/strong> o <span class="cal-nb">20 s<\/span>/);
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.cal-nb \{ white-space: nowrap; \}/);
});

test("D-24: the progress track is seen at 0 % on light and dark boxes", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /\.wiz-progress \{ height: 6px; border-radius: 999px; background: color-mix\(in srgb, var\(--primary-text-color, #182b37\) 14%, transparent\); overflow: hidden; \}/);
});

test("D-25/D-26: sheets have a centred handle (the Steps sheet too) and the side Steps panel reaches the right edge", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /dialog\.cal-dialog::before \{ align-self: center; margin: 10px auto 0; \}/);
  assert.match(css, /\.wiz-dialog \.wiz-dialog-card::before \{ margin: -12px auto 12px; \}/);
  assert.match(css, /\.wiz-sheet \.wiz-sheet-head::before \{ content: ""; position: absolute; top: 6px; left: 50%;/);
  assert.match(css, /\.wiz-sheet \.wiz-sheet-card \{ width: calc\(320px \+ var\(--cal-safe-right\)\); height: 100%; max-height: none; border-radius: 0; padding: 0; \}/);
  assert.match(css, /\.wiz-sheet \.wiz-sheet-head \{ padding-top: 4px; padding-inline-end: calc\(8px \+ var\(--cal-safe-right\)\); \}/);
});

test("D-30: in a landscape sheet the buttons sit side by side only while their labels fit on one line", async () => {
  const css = (await import("node:fs")).readFileSync(new URL("../../custom_components/myhome/frontend/panel/myhome-panel.css", import.meta.url), "utf8");
  assert.match(css, /dialog\.cal-dialog \.dialog-foot, \.wiz-dialog \.actions \{ flex-direction: row; flex-wrap: wrap; justify-content: end; \}/);
  assert.match(css, /dialog\.cal-dialog \.dialog-foot button, \.wiz-dialog \.actions button \{ flex: 1 1 auto; width: auto; min-width: 0; white-space: nowrap; \}/);
});

test("D-31: an ended session with a measurement out of range is titled as such, not as two presses", async () => {
  const t = (key) => translations.it[key] || key;
  const view = { mode: "geometry", phase: "interrupted", reason: "invalid_measurement", step: "opening", values: {}, samples: {}, readings: {}, owner: true, sequence: 9 };
  const screen = buildScreen({ t, language: "it", stage: "session", path: "A", view, local: {}, cover: { name: "K" } });
  assert.deepEqual([screen.code, screen.title, screen.body], ["S-04", "La misura non è valida", "Il tempo misurato deve essere compreso tra 1 e 600 secondi."]);
});

test("D-32: in the summary a cover without slats reads «No» for the slat time, not «0 s»", async () => {
  const t = (key) => translations.it[key] || key;
  const view = { mode: "geometry", phase: "review", step: "check", values: { opening_time: 22, closing_time: 21 }, samples: {}, readings: { half_open: 99, half_close: 98 },
    geometry: { slat_time_s: 0, opening_roll: 1.8, closing_roll: 1.9 }, slats: false, travel_cm: 198, owner: true, sequence: 9 };
  const screen = buildScreen({ t, language: "it", stage: "session", path: "A", view, local: {}, cover: { name: "K", effective: {} } });
  const slat = screen.table.rows.find((row) => row.label === t("wiz_T095"));
  assert.deepEqual([slat.before, slat.after], ["—", "No"]);
});

test("D-33: the stepper's times always carry one decimal", async () => {
  const t = (key) => translations.en[key] || key;
  const view = { mode: "geometry", phase: "briefing", step: "opening", values: { opening_time: 22 }, samples: { lift: 5 }, readings: { gap: 3 }, slats: true, owner: true, sequence: 4 };
  const screen = buildScreen({ t, stage: "session", path: "A", view, local: {}, cover: { name: "K" } });
  const ascent = screen.stepper.phases.find((phase) => phase.key === "ascent").substeps.map((item) => item.value);
  assert.deepEqual(ascent.slice(0, 2), ["5.0 s · 3 cm", "22.0 s"]);
});

test("D-37: the filter bars are fitted in the next frame, never inside the resize observer's delivery", async () => {
  const original = globalThis.ResizeObserver, frame = globalThis.requestAnimationFrame;
  let deliver = null; const frames = [];
  globalThis.ResizeObserver = class { constructor(callback) { deliver = callback; } observe() {} disconnect() {} };
  globalThis.requestAnimationFrame = (callback) => { frames.push(callback); return frames.length; };
  try {
    const { fitBars } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-layout.js?d37");
    const root = document.createElement("div"); root.innerHTML = '<div class="cal-filterbar"><div class="cal-filterbar-row"></div></div>';
    document.body.append(root);
    fitBars(root);
    assert.equal(typeof deliver, "function");
    const before = frames.length;
    deliver([{ target: root.firstElementChild }]);
    assert.equal(frames.length, before + 1, "the fit waits for the next frame");
    root.remove();
  } finally { globalThis.ResizeObserver = original; globalThis.requestAnimationFrame = frame; }
});
