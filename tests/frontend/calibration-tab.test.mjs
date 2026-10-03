import assert from "node:assert/strict";
import { after, afterEach, test } from "node:test";
import { JSDOM } from "jsdom";

import { translations } from "../../custom_components/myhome/frontend/panel/panel-translations.js";

const dom = new JSDOM("<!doctype html><html><body></body></html>", { url: "http://localhost/", pretendToBeVisual: true });
for (const key of ["window", "document", "HTMLElement", "customElements", "CustomEvent", "Event", "KeyboardEvent", "history"]) {
  globalThis[key] = key === "window" ? dom.window : dom.window[key];
}
dom.window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
dom.window.HTMLDialogElement.prototype.close = function () { this.open = false; };
await import("../../custom_components/myhome/frontend/panel/myhome-panel.js");
const { coverStatus, timedCovers } = await import("../../custom_components/myhome/frontend/panel/panel-calibration-tab.js");

const tick = async (count = 3) => { for (let i = 0; i < count; i++) await new Promise((resolve) => setImmediate(resolve)); };
afterEach(() => { document.body.replaceChildren(); window.localStorage.clear(); window.history.replaceState(null, "", "/"); });
after(() => dom.window.close());

const guided = (date, extra = {}) => ({ source: "guided", recorded_at: date, origin_entity_id: null, origin_name: null, inherited: false, ...extra });
const unknown = { source: "unknown", recorded_at: null, origin_entity_id: null, origin_name: null, inherited: false };
const timing = (value, provenance, origin = "override") => ({ value, origin, provenance, scaled: false });

function overview() {
  return { entry_id: "one", revision: 7, capabilities: { profile_management: true, profile_assignment: true },
    profiles: [{ id: "tall", name: "tall_two_leaf", opening_time: 22.4, closing_time: 21.9, assigned_to: ["cover.living_two", "cover.kitchen_two"],
      provenance: { opening: guided("2026-09-29T10:00:00+00:00"), closing: guided("2026-09-29T10:00:00+00:00") } }],
    covers: [
      { entity_id: "cover.living_one", name: "Living room shutter 1", profile_id: null, travel_cm: 198, available: true, advanced: false, overrides: {},
        effective: { opening: timing(22.24, guided("2026-10-01T09:00:00+00:00")), closing: timing(21.71, guided("2026-10-01T09:00:00+00:00")) } },
      { entity_id: "cover.living_two", name: "Living room shutter 2", profile_id: "tall", travel_cm: 196, available: true, advanced: false, overrides: {},
        effective: { opening: timing(22.4, guided("2026-09-29T10:00:00+00:00", { inherited: true, origin_name: "Living room shutter 1" }), "profile"),
          closing: timing(21.9, guided("2026-09-29T10:00:00+00:00", { inherited: true, origin_name: "Living room shutter 1" }), "profile"),
          slat_time_s: timing(4.4, guided("2026-09-29T10:00:00+00:00"), "profile"), opening_roll: timing(1.8312, guided("2026-09-29T10:00:00+00:00"), "profile"),
          closing_roll: timing(1.9071, guided("2026-09-29T10:00:00+00:00"), "profile") } },
      { entity_id: "cover.kitchen_two", name: "Kitchen shutter 2", profile_id: "tall", travel_cm: null, available: true, advanced: false, overrides: {},
        effective: { opening: timing(22.4, guided("2026-09-29T10:00:00+00:00", { inherited: true }), "profile"), closing: timing(21.9, guided("2026-09-29T10:00:00+00:00", { inherited: true }), "profile") } },
      { entity_id: "cover.bedroom", name: "Bedroom", profile_id: null, travel_cm: null, available: true, advanced: false, overrides: {},
        effective: { opening: timing(30, unknown, "native_fallback"), closing: timing(30, unknown, "native_fallback") } },
      { entity_id: "cover.sensor", name: "Skylight", profile_id: null, available: true, advanced: true, overrides: {}, effective: null },
    ] };
}

function inventory() {
  const cover = (entity_id, name, area_id = "living") => ({ entity_id, entry_id: "one", domain: "cover", who: "2", name: null, original_name: name,
    device_id: null, area_id, unique_id: `uid-${entity_id}`, address: { raw: "91", a: "9", pl: "1", interface: null } });
  return { version: "2.0.0b13", panel_version: "0.41.0",
    gateways: [{ entry_id: "one", title: "Casa", mac: "00:03:50:00:00:01", model: "F454", host: "192.0.2.1", state: "loaded", connected: true, monitor_available: true }],
    devices: [],
    entities: [cover("cover.living_one", "Living room shutter 1"), cover("cover.living_two", "Living room shutter 2"),
      cover("cover.kitchen_two", "Kitchen shutter 2", "kitchen"), cover("cover.bedroom", "Bedroom", "bedroom"), cover("cover.sensor", "Skylight", "attic")],
    areas: [{ id: "living", name: "Living room" }, { id: "kitchen", name: "Kitchen" }, { id: "bedroom", name: "Bedroom" }] };
}

async function mount({ data = overview(), session = null, language = "en", callWS } = {}) {
  const calls = [], subscriptions = [];
  const hass = {
    language, states: {},
    connection: {
      subscribeMessage: async (callback, request) => { subscriptions.push({ callback, request }); return () => {}; },
      subscribeEvents: async () => () => {},
    },
    callWS: async (message) => {
      calls.push(message);
      if (callWS) { const result = await callWS(message); if (result !== undefined) return result; }
      if (message.type === "myhome/panel/inventory") return inventory();
      if (message.type === "myhome/cover_profiles/overview") return structuredClone(data);
      if (message.type === "myhome/cover_profiles/read") return { revision: 7, calibration: session };
      throw new Error(`Unexpected command: ${message.type}`);
    },
  };
  const panel = document.createElement("myhome-panel");
  panel.hass = hass;
  document.body.append(panel);
  await tick();
  const root = panel.shadowRoot;
  root.querySelector('[data-action="cover-view"][data-id="calibration"]').click();
  await tick(6);
  return { panel, root, calls, subscriptions, hass, tab: root.getElementById("cover-calibration-tab") };
}

const rows = (tab) => [...tab.querySelectorAll(".cal-row")];
const row = (tab, id) => tab.querySelector(`.cal-row[data-entity="${id}"]`);
const commands = (calls) => calls.filter((message) => message.type.startsWith("myhome/cover_calibration/"));

test("status comes from the saved evidence: to measure, times measured, times and roll", () => {
  const data = overview();
  const [one, two, kitchen, bedroom] = data.covers;
  assert.deepEqual(coverStatus(one), { status: "times", rolls: false, last: "2026-10-01T09:00:00+00:00", method: "guided", origin: null });
  assert.equal(coverStatus(two).status, "rolls");
  assert.equal(coverStatus(two).method, "inherited");
  assert.equal(coverStatus(two).origin, "Living room shutter 1");
  assert.equal(coverStatus(kitchen).status, "times");
  assert.equal(coverStatus(bedroom).status, "to_measure");
  assert.equal(coverStatus(bedroom).last, null);
  assert.deepEqual(timedCovers(data).map((cover) => cover.entity_id), ["cover.living_one", "cover.living_two", "cover.kitchen_two", "cover.bedroom"]);
});

test("the Calibration sub-tab sits next to Devices and Profiles and lists timed covers only, without commands", async () => {
  const { root, tab, calls } = await mount();
  const views = [...root.querySelectorAll('[data-action="cover-view"]')].map((button) => [button.dataset.id, button.textContent.trim()]);
  assert.deepEqual(views, [["devices", "Devices"], ["profiles", "Profiles"], ["calibration", "Calibration"]]);
  assert.equal(root.querySelector('[data-action="cover-view"][data-id="calibration"]').getAttribute("aria-pressed"), "true");
  assert.equal(tab.querySelector("h3").textContent, "Calibration");
  assert.deepEqual(rows(tab).map((item) => item.dataset.entity), ["cover.bedroom", "cover.kitchen_two", "cover.living_one", "cover.living_two"]);
  assert.equal(row(tab, "cover.sensor"), null, "covers with a position sensor need no calibration");
  const badge = (id) => row(tab, id).querySelector(".cal-badge");
  assert.deepEqual(["cover.bedroom", "cover.living_one", "cover.living_two"].map((id) => [badge(id).dataset.status, badge(id).textContent]),
    [["to_measure", "To measure"], ["times", "Times measured"], ["rolls", "Times and roll"]]);
  assert.equal(row(tab, "cover.living_two").querySelector(".cal-profile-chip").textContent, "tall_two_leaf");
  assert.equal(row(tab, "cover.living_one").querySelector(".cal-row-profile").textContent.trim(), "—");
  assert.match(row(tab, "cover.living_one").querySelector(".cal-row-last").textContent, /^Measured on Oct 1, 2026$/);
  assert.equal(row(tab, "cover.bedroom").querySelector(".cal-row-last").textContent, "—");
  assert.equal(tab.querySelector(".cal-tab-summary").textContent, "4 roller shutters · 3 calibrated · 1 to measure");
  assert.equal(commands(calls).length, 0, "rendering the list never starts a measurement");
  assert.deepEqual(calls.filter((message) => message.type.startsWith("myhome/cover_profiles/")).map((message) => [message.type, message.entity_id]),
    [["myhome/cover_profiles/overview", undefined], ["myhome/cover_profiles/read", "cover.living_one"]]);
});

test("filters keep their counts, explain covers to measure and follow the panel search", async () => {
  const { root, tab } = await mount();
  const chips = () => Object.fromEntries([...tab.querySelectorAll('[data-action="cal-tab-filter"]')].map((chip) => [chip.dataset.id, chip.querySelector(".count").textContent]));
  assert.deepEqual(chips(), { all: "4", to_measure: "1", calibrated: "3", profile: "2" });
  tab.querySelector('[data-action="cal-tab-filter"][data-id="to_measure"]').click();
  assert.deepEqual(rows(tab).map((item) => item.dataset.entity), ["cover.bedroom"]);
  assert.match(tab.querySelector(".cal-tab-help").textContent, /default travel times/);
  assert.equal(tab.querySelector('[data-action="cal-tab-filter"][data-id="to_measure"]').getAttribute("aria-pressed"), "true");
  tab.querySelector('[data-action="cal-tab-filter"][data-id="profile"]').click();
  assert.deepEqual(rows(tab).map((item) => item.dataset.entity), ["cover.kitchen_two", "cover.living_two"]);
  assert.equal(tab.querySelector(".cal-tab-help"), null);
  tab.querySelector('[data-action="cal-tab-filter"][data-id="all"]').click();
  const search = root.getElementById("search");
  search.value = "tall_two"; search.dispatchEvent(new Event("input", { bubbles: true }));
  await tick();
  assert.deepEqual(rows(root.getElementById("cover-calibration-tab")).map((item) => item.dataset.entity), ["cover.kitchen_two", "cover.living_two"]);
});

test("the chevron expands a row in place with the values in use, the last measurement and the profile", async () => {
  const { tab } = await mount();
  const toggle = row(tab, "cover.living_two").querySelector('[data-action="cal-tab-toggle"]');
  assert.equal(toggle.getAttribute("aria-expanded"), "false");
  assert.equal(row(tab, "cover.living_two").querySelector(".cal-row-details").hidden, true);
  toggle.click();
  const expanded = row(tab, "cover.living_two");
  assert.equal(expanded.querySelector('[data-action="cal-tab-toggle"]').getAttribute("aria-expanded"), "true");
  const details = expanded.querySelector(".cal-row-details");
  assert.equal(details.hidden, false);
  const facts = Object.fromEntries([...details.querySelectorAll(".cal-facts div")].map((item) => [item.querySelector("dt").textContent, item.querySelector("dd").textContent]));
  assert.deepEqual(facts, { "Opening time": "22.4 s", "Closing time": "21.9 s", Slats: "Yes · 4.4 s", "Curtain travel": "196 cm",
    "Roll on ascent": "1.83", "Roll on descent": "1.91", Date: "Sep 29, 2026", Method: "From the profile" });
  assert.match(details.textContent, /Also followed by Kitchen shutter 2\./);
  assert.match(details.textContent, /adapted to the curtain travel of this roller shutter/);
  assert.ok(details.querySelector('[data-action="cover-profile"][data-id="cover.living_two"]'));
  expanded.querySelector('[data-action="cal-tab-toggle"]').click();
  assert.equal(row(tab, "cover.living_two").querySelector(".cal-row-details").hidden, true);
});

test("every text key the calibration screens use exists in English and Italian", async () => {
  const { readFileSync } = await import("node:fs");
  const base = new URL("../../custom_components/myhome/frontend/panel/", import.meta.url);
  const keys = new Set();
  for (const file of ["panel-calibration-tab.js", "panel-calibration-wizard.js", "panel-calibration-screens.js"]) {
    const source = readFileSync(new URL(file, base), "utf8");
    for (const match of source.matchAll(/\b(?:t|tx)\("([A-Za-z0-9_]+)"/g)) keys.add(match[1]);
  }
  // Keys built from a value: every value the views can carry.
  for (const value of ["all", "to_measure", "calibrated", "profile"]) keys.add(`calTabFilter_${value}`);
  for (const value of ["to_measure", "times", "rolls"]) keys.add(`calTabStatus_${value}`);
  for (const value of ["guided", "automatic", "inherited", "none"]) keys.add(`calTabMethod_${value}`);
  for (const value of ["unexpected_movement", "external_command", "unexpected_stop", "stopped", "not_delivered", "start_timeout",
    "not_stopped", "stop_queue_full", "invalid_measurement", "travel_timeout", "cover_unavailable"]) keys.add(`calReason_${value}`);
  assert.ok(keys.size > 150, `${keys.size} keys found`);
  for (const key of keys) {
    assert.ok(translations.en[key], `en ${key}`);
    assert.ok(translations.it[key], `it ${key}`);
  }
});

test("row menu items move with the arrow keys", async () => {
  const { root, tab } = await mount();
  row(tab, "cover.bedroom").querySelector('[data-action="cal-tab-menu"]').click();
  const items = [...row(tab, "cover.bedroom").querySelectorAll('[role="menuitem"]')];
  assert.equal(root.activeElement, items[0]);
  items[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
  assert.equal(root.activeElement, items[1]);
  items[1].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
  assert.equal(root.activeElement, items[0], "the arrows wrap");
  items[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
  assert.equal(root.activeElement, items[1]);
});

test("the row menu assigns a profile in the existing dialog and closes with Escape back on its button", async () => {
  const { root, tab, hass } = await mount();
  hass.callWS = ((original) => async (message) => message.type === "myhome/cover_profiles/read" && message.entity_id === "cover.bedroom"
    ? { revision: 7, profiles: [], assigned_profile_id: null, writable: true, effective_opening_time: 30, effective_closing_time: 30, calibration: null }
    : original(message))(hass.callWS);
  const menuButton = row(tab, "cover.bedroom").querySelector('[data-action="cal-tab-menu"]');
  menuButton.click();
  const menu = row(tab, "cover.bedroom").querySelector(".cal-menu");
  assert.equal(menu.hidden, false);
  assert.equal(root.activeElement, menu.querySelector('[role="menuitem"]'));
  menu.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  assert.equal(row(tab, "cover.bedroom").querySelector(".cal-menu").hidden, true);
  assert.equal(root.activeElement, row(tab, "cover.bedroom").querySelector('[data-action="cal-tab-menu"]'));
  row(tab, "cover.bedroom").querySelector('[data-action="cal-tab-menu"]').click();
  row(tab, "cover.bedroom").querySelector('.cal-menu [data-action="cover-profile"]').click();
  await tick();
  assert.ok(root.querySelector(".cover-profile-dialog"), "Assign profile opens the maintainer's dialog");
});

test("a session in progress marks its cover, blocks new measurements and opens an automatic group in the existing view", async () => {
  const session = { entry_id: "one", entity_id: "cover.bedroom", session_id: "group", mode: "automatic", batch: true, phase: "paused",
    reason: "owner_absent", sequence: 4, values: {}, recoverable: true, attached: false, owner_present: false, cover_index: 0, results: [],
    targets: [{ entity_id: "cover.bedroom", name: "Bedroom" }, { entity_id: "cover.living_one", name: "Living room shutter 1" }],
    next_step: { step: "next_cover", cover_index: 1, entity_id: "cover.living_one" } };
  const { tab, subscriptions, calls } = await mount({ session });
  assert.match(tab.querySelector(".cal-tab-busy").textContent, /finish or cancel it/);
  assert.equal(tab.querySelector('[data-action="cal-tab-batch"]').disabled, true);
  for (const id of ["cover.bedroom", "cover.living_one"]) {
    assert.equal(row(tab, id).querySelector(".cal-badge").dataset.status, "running");
    assert.equal(row(tab, id).querySelector(".cal-badge").textContent, "In progress · paused");
  }
  assert.equal(row(tab, "cover.living_two").querySelector(".cal-badge").dataset.status, "rolls");
  const open = row(tab, "cover.bedroom").querySelector('[data-action="cal-tab-session"]');
  assert.equal(open.textContent, "Open session");
  open.click(); await tick();
  const resume = subscriptions.find((item) => item.request.type === "myhome/cover_calibration/resume");
  assert.equal(resume.request.session_id, "group");
  assert.equal("claim" in resume.request, false, "opening never takes control");
  resume.callback({ ...session, attachment: "reader", owner: false, read_only: true });
  assert.equal(tab.querySelector("#cal-paused").hidden, false);
  assert.equal(commands(calls).length, 0);
  tab.querySelector(".cal-tab-back").click(); await tick();
  assert.ok(tab.querySelector(".cal-list"));
});

test("an empty gateway explains which covers need calibration", async () => {
  const data = overview();
  data.covers = data.covers.filter((cover) => cover.advanced);
  const { tab } = await mount({ data, language: "it" });
  assert.equal(tab.querySelector(".cal-tab-empty h2").textContent, translations.it.calTabEmptyTitle);
  assert.match(tab.querySelector(".cal-tab-empty").textContent, /sensore di posizione/);
  assert.equal(tab.querySelector(".cal-list"), null);
});

test("a group uses the existing selection and starts only after an explicit choice", async () => {
  const { tab, subscriptions, calls } = await mount({ callWS: (message) => message.type === "myhome/cover_calibration/targets"
    ? { revision: 7, max_batch: 4, targets: [{ entity_id: "cover.bedroom", name: "Bedroom", reason: null }, { entity_id: "cover.living_one", name: "Living room shutter 1", reason: "cover_unavailable" }] }
    : undefined });
  tab.querySelector('[data-action="cal-tab-batch"]').click(); await tick();
  assert.equal(tab.querySelector('input[value="cover.living_one"]').disabled, true);
  assert.equal(tab.querySelector("#batch-continue").disabled, true);
  tab.querySelector('input[value="cover.bedroom"]').checked = true;
  tab.querySelector("#batch-selection").dispatchEvent(new Event("change"));
  tab.querySelector("#batch-continue").click(); await tick();
  const start = subscriptions.find((item) => item.request.type === "myhome/cover_calibration/batch_start");
  assert.deepEqual(start.request.entity_ids, ["cover.bedroom"]);
  assert.equal(start.request.revision, 7);
  assert.equal(commands(calls).filter((message) => message.type === "myhome/cover_calibration/action").length, 0);
});

test("Italian texts of the tab carry no placeholder", async () => {
  const { tab } = await mount({ language: "it" });
  row(tab, "cover.living_two").querySelector('[data-action="cal-tab-toggle"]').click();
  assert.doesNotMatch(tab.textContent, /\{\w+\}|calTab|wiz_T/);
  assert.match(tab.textContent, /Tempi e rullo/);
  assert.match(tab.querySelector(".cal-tab-summary").textContent, /^4 tapparelle · 3 calibrate · 1 da misurare$/);
});

test("a gateway whose session cannot be read but is reserved keeps new measurements off; a failed read tries the next cover", async () => {
  const data = overview();
  for (const cover of data.covers) cover.assignment_reason = "calibration_busy";
  let reads = 0;
  const { tab, calls } = await mount({ data, callWS: (message) => {
    if (message.type === "myhome/cover_profiles/read") { reads++; throw Object.assign(new Error("x"), { code: "storage_error" }); }
    return undefined;
  } });
  assert.equal(reads, 3, "three covers are tried before giving up for this refresh");
  assert.match(tab.querySelector(".cal-tab-busy").textContent, /finish or cancel it/);
  assert.equal(tab.querySelector('[data-action="cal-tab-measure"]').disabled, true);
  assert.equal(tab.querySelector('[data-action="cal-tab-batch"]').disabled, true);
  assert.ok([...tab.querySelectorAll('[data-action="cal-tab-measure-cover"]')].every((button) => button.disabled));
  assert.equal(calls.filter((message) => message.type.startsWith("myhome/cover_calibration/")).length, 0);
});

test("the second read finds the session when the first one fails", async () => {
  let reads = 0;
  const session = { entry_id: "one", entity_id: "cover.bedroom", session_id: "s", mode: "geometry", phase: "briefing", step: "home", sequence: 2,
    values: {}, recoverable: true, attached: true, owner_present: true };
  const { tab } = await mount({ callWS: (message) => {
    if (message.type === "myhome/cover_profiles/read") { reads++; if (reads === 1) throw new Error("lost"); return { revision: 7, calibration: session }; }
    return undefined;
  } });
  assert.equal(row(tab, "cover.bedroom").querySelector(".cal-badge").dataset.status, "running");
  assert.ok(tab.querySelector(".cal-tab-busy"));
});

test("the summary uses singular forms for one cover", async () => {
  const data = overview();
  data.covers = [data.covers[0], data.covers[4]];
  const { tab } = await mount({ data, language: "it" });
  assert.equal(tab.querySelector(".cal-tab-summary").textContent, "1 tapparella · 1 calibrata · 0 da misurare");
});
