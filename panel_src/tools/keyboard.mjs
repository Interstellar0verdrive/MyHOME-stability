// `npm run keyboard` - the flows, walked without a pointer.
//
// The handoff (§5) asks that every assignment be reachable from the keyboard and that
// Escape give back whatever is held. Those are behaviours, not markup, so axe cannot see
// them: what it can say is that a control has a name, not that focus comes back to it. So
// this walks them, in the same jsdom host, and asserts the four things that a keyboard-only
// user actually needs.
//
// **Tab is computed and not pressed.** jsdom implements `focus()` and `activeElement` but
// not sequential navigation, so the tab order here is the panel's own `focusable()` rule
// applied to the rendered tree - which is also what the focus trap uses, and therefore the
// thing worth checking. What *is* dispatched for real is every key the panel handles:
// Enter on the handle, Escape, Enter on an option.
//
// Dev-only, like its two neighbours: it loads the committed bundle and nothing imports it.

import {
  COVER,
  deep,
  deepAll,
  makePending,
  mount,
  openDialog,
  refuseAStaleBundle,
} from "./panel-host.mjs";

await refuseAStaleBundle();

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]),' +
  ' textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const tabOrder = (root) => deepAll(root, FOCUSABLE);

/**
 * The element that really has focus, wherever in the nest of shadow roots it is.
 *
 * Not `panel.shadowRoot.activeElement` and a walk down from it: a browser retargets that
 * to the host of the inner root, jsdom does not always, and a check that passed or failed
 * on which of the two was in front of it would be a check of jsdom. Every root is asked
 * instead, and the deepest answer that is not itself a host is the one that is focused.
 */
const active = (panel) => {
  const roots = [];
  const collect = (root) => {
    roots.push(root);
    for (const element of root.querySelectorAll("*")) {
      if (element.shadowRoot) {
        collect(element.shadowRoot);
      }
    }
  };
  collect(panel.shadowRoot);
  let found = null;
  for (const root of roots) {
    const one = root.activeElement;
    if (one && !one.shadowRoot) {
      found = one;
    }
  }
  return found;
};

const describe = (node) =>
  node
    ? `${node.tagName.toLowerCase()}${node.className ? "." + String(node.className).trim().split(/\s+/).join(".") : ""}` +
      (node.getAttribute?.("aria-label") ? ` [${node.getAttribute("aria-label")}]` : "")
    : "nothing";

const press = (window, node, key) =>
  node?.dispatchEvent(new window.KeyboardEvent("keydown", { key, bubbles: true, composed: true }));

/**
 * The CSS that really reaches an element: the rules of the shadow root it is drawn in.
 *
 * jsdom lays nothing out, so a panel with no frame at all - no backdrop, no fixed
 * position, the confirm button at the bottom of the page - passes every check of markup
 * and focus above. What can be asked without a layout engine is whether the rules that
 * make the frame are in the root the element lives in: a rule adopted by another root
 * does not reach it. Both routes Lit can take are read - adopted sheets, and the
 * `<style>` elements it falls back to, whose text is read directly because jsdom does
 * not parse a stylesheet inside a shadow root - and the whitespace is folded so that one
 * pattern fits both the source and the minified bundle.
 */
const rulesReaching = (element) => {
  const root = element?.getRootNode?.();
  if (!root) {
    return "";
  }
  const text = [];
  const walk = (rules) => {
    for (const rule of rules) {
      text.push(rule.cssText);
      if (rule.cssRules) {
        walk(rule.cssRules);
      }
    }
  };
  for (const sheet of root.adoptedStyleSheets ?? []) {
    walk(sheet.cssRules);
  }
  for (const style of root.querySelectorAll?.("style") ?? []) {
    text.push(style.textContent ?? "");
  }
  return text.join("\n").replace(/\/\*[\s\S]*?\*\//g, "").replace(/\s+/g, " ");
};

/** True when the sheet's frame - backdrop and fixed box - is styled where it is drawn. */
const framed = (sheet) => {
  const rules = rulesReaching(sheet);
  return /(^|[\s}])\.sheet-backdrop ?\{[^}]*position: ?fixed/.test(rules) &&
    /(^|[\s}])\.sheet ?\{[^}]*position: ?fixed/.test(rules) &&
    /(^|[\s}])\.sheet \.head button ?\{[^}]*border-radius: ?24px/.test(rules);
};

const checks = [];
const check = (what, ok, detail = "") => {
  checks.push({ what, ok, detail });
  console.log(`  ${ok ? "ok  " : "✖   "}${what}${detail ? ` - ${detail}` : ""}`);
};

// --- the assignment, from the handle to the undo strip ---------------------------------
{
  console.log("\noverview → assign by keyboard → review → confirm");
  const { window, panel, dom, settle } = await mount({ name: "overview", state: "ready" });
  const context = { window, panel, deep, deepAll, settle };

  const stops = tabOrder(panel.shadowRoot);
  console.log(`  tab order (${stops.length}): ${stops.slice(0, 8).map(describe).join(" → ")} …`);
  check("every control on the overview is reachable", stops.length > 0);
  check(
    "the search box comes before the rows",
    stops.findIndex((one) => one.classList?.contains("search")) <
      stops.findIndex((one) => one.classList?.contains("handle")),
  );
  check(
    "nothing that does nothing is in the tab order",
    stops.every((one) => !one.hasAttribute("disabled")),
  );

  const handle = deep(panel.shadowRoot, "button.handle");
  await openDialog(context);
  check("Enter on the handle opens the choice", deep(panel.shadowRoot, ".dialog") !== null);
  check("focus moves into it", deep(panel.shadowRoot, ".dialog")?.contains(active(panel)) === true,
    describe(active(panel)));

  press(window, active(panel) ?? handle, "Escape");
  await settle();
  check("Escape closes it", deep(panel.shadowRoot, ".dialog") === null);
  check(
    "and focus comes back to the handle it was opened from",
    active(panel)?.classList?.contains("handle") === true,
    describe(active(panel)),
  );

  await makePending(context);
  check("a choice made by keyboard is one pending change",
    deep(panel.shadowRoot, ".route .withdraw") !== null);
  check(
    "focus comes back to the row the shutter moved to",
    active(panel)?.classList?.contains("handle") === true,
    describe(active(panel)),
  );

  const withdraw = deep(panel.shadowRoot, ".route .withdraw");
  check("the withdraw cross is a button and is in the tab order",
    withdraw?.tagName === "BUTTON" && tabOrder(panel.shadowRoot).includes(withdraw));

  deep(panel.shadowRoot, "button.review").click();
  await settle();
  const sheet = deep(panel.shadowRoot, ".sheet");
  check("the review sheet opens", sheet !== null);
  check("and it is drawn in its frame: backdrop, fixed panel, round ✕", framed(sheet));
  check("focus is inside it", sheet?.contains(active(panel)) === true, describe(active(panel)));
  check(
    "the sheet holds the keyboard",
    tabOrder(sheet ?? panel.shadowRoot).length > 0 && sheet?.getAttribute("aria-modal") === "true",
  );
  press(window, active(panel) ?? panel, "Escape");
  await settle();
  check("Escape closes the sheet", deep(panel.shadowRoot, ".sheet") === null);
  check("the pending change survives it", deep(panel.shadowRoot, ".route .withdraw") !== null);
  dom.window.close();
}

// --- the two cards, which are drawers over the list --------------------------------------
//
// A deep link opens both: the list on the page and the card in a panel over it. So what is
// asserted here is the pair - that the list really is behind, that the keyboard cannot
// walk into it, and that Escape gives the whole thing back and lands on the list.
for (const [name, hash] of [["cover detail", COVER], ["profile card", "#/profile/tall"]]) {
  console.log(`\n${name} → edit`);
  const { window, panel, dom, settle } = await mount({ name, state: "ready", hash });
  const sheet = deep(panel.shadowRoot, "[data-drawer]");
  check("the deep link opened the list and a drawer over it", sheet !== null &&
    deep(panel.shadowRoot, "myhome-overview") !== null);
  check("the drawer holds the keyboard", sheet?.getAttribute("aria-modal") === "true");
  check("and it is drawn in its frame: backdrop, fixed panel, round ✕", framed(sheet));
  const stops = tabOrder(sheet ?? panel.shadowRoot);
  console.log(`  tab order (${stops.length}): ${stops.slice(0, 6).map(describe).join(" → ")} …`);
  check("its own control is the first stop inside it", describe(stops[0]).includes("button"));
  check(
    "the card's heading took focus on the paint that drew it",
    active(panel)?.hasAttribute?.("data-heading") === true,
    describe(active(panel)),
  );
  // The list behind is still rendered, and its controls are still in the document: what
  // keeps them out of reach is the trap, and what the trap is given is this element.
  check(
    "the list's own controls are outside the drawer",
    deep(panel.shadowRoot, "input.field.search") !== null &&
      sheet?.contains(deep(panel.shadowRoot, "input.field.search")) === false,
  );
  const wide = deepAll(sheet ?? panel.shadowRoot, "button.wide:not([disabled])")[0];
  wide?.click();
  await settle();
  const fields = deepAll(deep(panel.shadowRoot, "[data-drawer]") ?? panel.shadowRoot, "input.field");
  check("the form it opens has fields with names",
    fields.length > 0 && fields.every((one) => one.getAttribute("aria-label")));
  check("every field says whether it is refused",
    fields.every((one) => one.hasAttribute("aria-invalid")));
  press(window, active(panel) ?? panel, "Escape");
  await settle();
  check("Escape steps out of the form and leaves the drawer open",
    deep(panel.shadowRoot, "[data-drawer]") !== null);
  press(window, active(panel) ?? panel, "Escape");
  await settle();
  check("Escape again closes the drawer", deep(panel.shadowRoot, "[data-drawer]") === null);
  check("and the list is what is left", deep(panel.shadowRoot, "button.handle") !== null);
  dom.window.close();
}

// --- the drawer's one level of back stack ------------------------------------------------
{
  console.log("\ndetail → profile → back");
  const { window, panel, dom, settle } = await mount({
    name: "back stack",
    state: "ready",
    hash: COVER,
    expect: "[data-drawer]",
  });
  const head = () => deep(panel.shadowRoot, "[data-drawer] .head button");
  check("a drawer opened from the list closes, and does not go back",
    head()?.getAttribute("aria-label") === "Close", describe(head()));
  // The detail's link to the profile it follows: the drawer's contents are replaced.
  // Asked of the drawer element rather than of a descendant selector: the card inside it
  // is a custom element, and `[data-drawer] button` cannot cross a shadow boundary.
  const toProfile = deepAll(deep(panel.shadowRoot, "[data-drawer]"), "button.wide").find(
    (button) => (button.textContent ?? "").includes("Open the profile card"),
  );
  toProfile?.click();
  await settle();
  check("the profile is in the same drawer", window.location.hash.startsWith("#/profile/"));
  check("and its control is now a way back", head()?.getAttribute("aria-label") === "Back",
    describe(head()));
  head()?.click();
  await settle();
  check("which lands on the cover it came from", window.location.hash === COVER);
  check("and is a close again, because the stack is one level deep",
    head()?.getAttribute("aria-label") === "Close", describe(head()));
  head()?.click();
  await settle();
  check("the list is what is behind it", deep(panel.shadowRoot, "[data-drawer]") === null &&
    deep(panel.shadowRoot, "button.handle") !== null);
  dom.window.close();
}

// --- ...and the dark half, which is not the arrow -----------------------------------------
{
  console.log("\ndetail → profile → a click outside");
  // Live finding 27: a click outside answered like the arrow, so from a profile card
  // opened out of a shutter's card it went back to the shutter and a second click outside
  // was needed to leave. A click outside is "I am done with this", from however deep.
  const { window, panel, dom, settle } = await mount({
    name: "the drawer, dismissed from two levels down",
    state: "ready",
    hash: COVER,
    expect: "[data-drawer]",
  });
  const toProfile = deepAll(deep(panel.shadowRoot, "[data-drawer]"), "button.wide").find(
    (button) => (button.textContent ?? "").includes("Open the profile card"),
  );
  toProfile?.click();
  await settle();
  check("the profile is in the drawer, two screens deep",
    window.location.hash.startsWith("#/profile/"));
  deep(panel.shadowRoot, ".sheet-backdrop")?.click();
  await settle();
  check("one click outside lands on the list, not on the shutter it came from",
    window.location.hash === "#/" || window.location.hash === "" || window.location.hash === "#",
    window.location.hash);
  check("and the drawer is gone", deep(panel.shadowRoot, "[data-drawer]") === null &&
    deep(panel.shadowRoot, "button.handle") !== null);
  dom.window.close();
}

// --- the measuring lock ------------------------------------------------------------------
{
  console.log("\na measurement is running");
  const { window, panel, dom, settle } = await mount({ name: "measuring", state: "measuring" });
  await settle();
  const handles = deepAll(panel.shadowRoot, "button.handle");
  check("no handle is reachable", handles.every((one) => one.hasAttribute("disabled")));
  press(window, deep(panel.shadowRoot, "button.handle"), "Enter");
  await settle();
  check("Enter on one opens nothing", deep(panel.shadowRoot, ".dialog") === null);
  check("and the banner says why", deep(panel.shadowRoot, ".banner") !== null ||
    (panel.shadowRoot.textContent ?? "").includes("guided calibration"));
  dom.window.close();
}

// --- the guided calibration --------------------------------------------------------------
//
// From lot F2 this is where a measurement is driven from, and the keyboard rules SPEC §5.7
// fixes are behaviours rather than markup: where focus lands when a step arrives, that the
// press really is a button, and that Escape asks the question instead of throwing three
// minutes of measurements away.
//
// It is also where the guard in `tools/panel-host.mjs` bites: the accessors that throw
// "Method not implemented" on the form APIs Home Assistant's scoped registry does not
// implement only fire on a screen a check actually mounts, and the wizard's steps are the
// screens with the fields on them.
{
  console.log("\nthe guided calibration, a brief before a timed run");
  const { window, panel, dom, settle, calls } = await mount({
    name: "the wizard",
    state: "session:briefing_open_brief",
    hash: "#/calibrate",
    expect: "[data-wizard]",
  });
  await settle();
  const stops = tabOrder(panel.shadowRoot);
  console.log(`  tab order (${stops.length}): ${stops.map(describe).join(" → ")}`);
  const big = deep(panel.shadowRoot, "button.big");
  check("the big button is in the tab order", stops.includes(big), describe(big));
  // Enter and Space are a `<button>`'s own, and jsdom does not synthesise the click a
  // browser makes from them - so what is asserted is that the control really is one, and
  // that pressing it is what sends the step on.
  check("and it is a button, so Enter and Space press it", big?.tagName === "BUTTON");
  check("focus is on the heading, because this step is words and not a press",
    active(panel)?.tagName === "H1", describe(active(panel)));
  big?.click();
  await settle();
  check("pressing it sends one act and nothing else",
    calls.filter((one) => one === "act").length === 1 && !calls.includes("stop"),
    calls.join(", "));

  console.log("\n…and Escape on it");
  press(window, active(panel) ?? big, "Escape");
  await settle();
  const dialog = deep(panel.shadowRoot, "[data-exit-dialog]");
  check("Escape asks whether to leave", dialog !== null);
  check("and nothing was cancelled by asking", !calls.includes("cancel"), calls.join(", "));
  check("the keyboard is inside the question", dialog?.contains(active(panel)) === true,
    describe(active(panel)));
  press(window, active(panel), "Escape");
  await settle();
  check("Escape again goes back to measuring", deep(panel.shadowRoot, "[data-exit-dialog]") === null);
  check("and still nothing was cancelled", !calls.includes("cancel"), calls.join(", "));
  dom.window.close();
}

{
  console.log("\nthe guided calibration, a press to be made");
  const { panel, dom, settle, calls } = await mount({
    name: "the wizard, pressing",
    state: "session:running_open_lift",
    hash: "#/calibrate",
    expect: "[data-wizard]",
  });
  await settle();
  const big = deep(panel.shadowRoot, "button.big");
  // The one step where focus does not go to the heading: the button *is* the step, and a
  // user who had to Tab to it would have missed the instant it is about.
  check("focus is on the big button", active(panel) === big, describe(active(panel)));
  check("and it carries the dialog's own numbered label",
    (big?.textContent ?? "").trim().startsWith("1)"), (big?.textContent ?? "").trim());
  check("nothing has been sent by arriving on it", !calls.includes("act"), calls.join(", "));
  big?.click();
  await settle();
  check("and the press sends exactly one act", calls.filter((one) => one === "act").length === 1);
  dom.window.close();
}

{
  console.log("\nthe guided calibration, driven by somebody else");
  const { panel, dom, settle, calls } = await mount({
    name: "the wizard, read-only",
    state: "session:owned_by_other",
    hash: "#/calibrate",
    expect: "[data-take-control]",
  });
  await settle();
  const stops = tabOrder(panel.shadowRoot);
  const take = deep(panel.shadowRoot, "[data-take-control]");
  check("the one thing to press is the offer to take control", stops.includes(take),
    stops.map(describe).join(" → "));
  check("and none of the step's own answers is reachable",
    deepAll(panel.shadowRoot, "button.option").length === 0);
  check("attaching to it took nothing from anybody",
    !calls.includes("act") && !calls.includes("stop"), calls.join(", "));
  dom.window.close();
}

// --- the choice of shutter (lot F3) -----------------------------------------------------
{
  console.log("\nthe guided calibration, the choice of shutter");
  const { panel, dom, settle, calls } = await mount({
    name: "the wizard, choosing a shutter",
    state: "ready",
    hash: "#/calibrate",
    expect: "[data-wizard-pick]",
  });
  await settle();
  const stops = tabOrder(panel.shadowRoot);
  const options = deepAll(panel.shadowRoot, ".options button.option");
  console.log(`  tab order (${stops.length}): ${stops.map(describe).join(" → ")}`);
  check("every shutter on it is reachable", options.length > 0 && options.every((one) => stops.includes(one)),
    `${options.length} shutters`);
  check("and each of them is a button, so Enter and Space choose it",
    options.every((one) => one.tagName === "BUTTON"));
  check("arriving on the choice starts nothing", !calls.includes("start") && !calls.includes("attach"),
    calls.join(", ") || "nothing sent");
  // The choice is a screen of the wizard like any other (SPEC §5.7): the keyboard lands on
  // its heading, and a reader is told which screen arrived. Without both, pressing "Misura
  // una tapparella" leaves focus on a button that is no longer in the document.
  check("focus is on the heading of the choice", active(panel)?.tagName === "H1",
    describe(active(panel)));
  const spoken = deepAll(panel.shadowRoot, "[data-wizard-pick] [aria-live='polite']")
    .map((one) => (one.textContent ?? "").trim())
    .filter(Boolean);
  check("and the screen says out loud which one it is", spoken.length === 1, spoken.join(" | "));
  options[0]?.click();
  await settle();
  // A row selects; "Continue" is what opens a session (live finding 3, and the design's
  // own `Continua`). Both are buttons, so Enter and Space reach the whole gesture.
  check("pressing a row still starts nothing", !calls.includes("start"), calls.join(", ") || "nothing sent");
  const going_on = deepAll(panel.shadowRoot, "button.big")[0];
  check("and the way on is a button of the footer", going_on?.tagName === "BUTTON",
    describe(going_on));
  going_on?.click();
  await settle();
  check("choosing one opens exactly one session", calls.filter((one) => one === "start").length === 1,
    calls.join(", "));
  // The intention travels in the store, so the address stays the wizard's own and carries
  // nothing that could reopen a session on a reload (SPEC §5.1).
  check("and the address still says nothing about which shutter",
    dom.window.location.hash === "#/calibrate", dom.window.location.hash);
  dom.window.close();
}

// --- the measuring banner, in its three shapes (lot F3) ---------------------------------
{
  console.log("\nthe banner over a calibration of this panel's own");
  const { panel, dom, settle, calls } = await mount({
    name: "the banner, a session of the panel's",
    state: "measuring-panel",
    expect: '[data-banner="resume"]',
  });
  const stops = tabOrder(panel.shadowRoot);
  const resume = deep(panel.shadowRoot, '[data-banner="resume"]');
  const end = deep(panel.shadowRoot, '[data-banner="end-panel"]');
  check("both offers are in the tab order", stops.includes(resume) && stops.includes(end));
  check("and they are buttons, not links that go to the integration page",
    resume?.tagName === "BUTTON" && end?.tagName === "BUTTON");
  end?.click();
  await settle();
  check("ending it asks first", deep(panel.shadowRoot, "[data-banner-question]") !== null);
  check("and nothing was sent by asking", !calls.includes("cancel"), calls.join(", ") || "nothing");
  // The question replaces the offers, so the button that was pressed leaves the document:
  // left alone the keyboard falls to the top of the page, and the strip is read out but
  // cannot be answered.
  check("the keyboard is on the answer, not back at the top of the page",
    active(panel) === deep(panel.shadowRoot, '[data-banner="confirm"]'), describe(active(panel)));
  deep(panel.shadowRoot, '[data-banner="keep"]')?.click();
  await settle();
  check("saying no puts the offers back", deep(panel.shadowRoot, '[data-banner="resume"]') !== null);
  check("and the keyboard comes back to the offer that asked",
    active(panel) === deep(panel.shadowRoot, '[data-banner="end-panel"]'), describe(active(panel)));
  check("and still nothing was sent", !calls.includes("cancel"), calls.join(", ") || "nothing");
  end?.click();
  await settle();
  deep(panel.shadowRoot, '[data-banner="confirm"]')?.click();
  await settle();
  // `force`, because the session may be held by another device: a "Termina" that could be
  // refused for ownership would be a button that does nothing on the one screen that has
  // no other way of freeing the shutter.
  check("saying yes ends it, whoever owns it",
    calls.filter((one) => one === "cancel").length === 1, calls.join(", "));
  dom.window.close();
}

{
  console.log("\nthe banner over a calibration of the Configure dialog's");
  const { panel, dom, settle, calls } = await mount({
    name: "the banner, the dialog",
    state: "measuring",
    expect: '[data-banner="end-other"]',
  });
  const stops = tabOrder(panel.shadowRoot);
  const close = deep(panel.shadowRoot, '[data-banner="end-other"]');
  check("closing the dialog is offered and reachable", stops.includes(close));
  check("and so is opening it", stops.includes(deep(panel.shadowRoot, '[data-banner="configure"]')));
  check("resuming is not, because this panel is not driving it",
    deep(panel.shadowRoot, '[data-banner="resume"]') === null);
  close?.click();
  await settle();
  check("closing it asks first", deep(panel.shadowRoot, "[data-banner-question]") !== null);
  check("and nothing was sent by asking", !calls.includes("end_other"), calls.join(", ") || "nothing");
  deep(panel.shadowRoot, '[data-banner="confirm"]')?.click();
  await settle();
  check("saying yes closes the dialogs of this gateway",
    calls.filter((one) => one === "end_other").length === 1, calls.join(", "));
  dom.window.close();
}

{
  console.log("\nthe banner over a run an action of 0.4.2 started");
  const { panel, dom, settle } = await mount({
    name: "the banner, the service",
    state: "measuring-service",
    drive: async (context) => {
      context.deep(context.panel.shadowRoot, '[data-banner="end-other"]')?.click();
      await context.settle();
      context.deep(context.panel.shadowRoot, '[data-banner="confirm"]')?.click();
      await context.settle();
    },
    expect: "[data-banner-service]",
  });
  await settle();
  // Every dialog of the gateway was closed and the shutter is still held: there is nothing
  // left to close, so the banner stops offering and says to wait.
  check("nothing is offered any more",
    deepAll(panel.shadowRoot, "[data-banner-measuring] button.offer").length === 0);
  check("and the strip says the run finishes by itself",
    (deep(panel.shadowRoot, "[data-banner-measuring]")?.textContent ?? "").includes("wait for it"));
  dom.window.close();
}

{
  console.log("\nthe wizard, a start refused because the dialog is holding the shutter");
  const { panel, dom, settle, calls } = await mount({
    name: "the wizard, busy",
    state: "busy:other",
    hash: "#/calibrate",
    drive: async (context) => {
      context.deep(context.panel.shadowRoot, ".options button.option")?.click();
      await context.settle();
      context.deepAll(context.panel.shadowRoot, "button.big")[0]?.click();
      await context.settle();
    },
    expect: "[data-session-busy]",
  });
  await settle();
  const stops = tabOrder(panel.shadowRoot);
  check("the refusal is a screen with something to do on it",
    stops.includes(deep(panel.shadowRoot, '[data-busy="end-other"]')) &&
      stops.includes(deep(panel.shadowRoot, '[data-busy="configure"]')),
    stops.map(describe).join(" → "));
  check("nothing was started", calls.filter((one) => one === "start").length === 1 &&
    !calls.includes("attach"), calls.join(", "));
  deep(panel.shadowRoot, '[data-busy="end-other"]')?.click();
  await settle();
  check("closing the dialog asks first", deep(panel.shadowRoot, "[data-busy-question]") !== null);
  check("with the keyboard on the answer", 
    active(panel) === deep(panel.shadowRoot, '[data-busy="confirm"]'), describe(active(panel)));
  check("and nothing was sent by asking", !calls.includes("end_other"), calls.join(", "));
  deep(panel.shadowRoot, '[data-busy="confirm"]')?.click();
  await settle();
  check("saying yes closes it, and the screen goes back to the choice of shutter",
    calls.filter((one) => one === "end_other").length === 1 &&
      deep(panel.shadowRoot, "[data-wizard-pick]") !== null,
    calls.join(", "));
  dom.window.close();
}

// --- where the calibration has got to (live finding 29, lot W2) -------------------------
//
// The stepper's own rule is that it is orientation and not a road back, and that rule is a
// keyboard rule before it is anything else: a rail of nine rows that all took focus would
// put nine stops between the heading and the field a reading is typed into. So what is
// walked here is exactly that - how many of its rows are in the tab order, which one, and
// what pressing it sends.
{
  console.log("\nthe guided calibration, the stepper on an ordinary step");
  const { panel, dom, settle, calls } = await mount({
    name: "the wizard, the stepper",
    state: "session:awaiting_reading_measure_descent",
    hash: "#/calibrate",
    expect: "[data-stepper]",
  });
  await settle();
  const stops = tabOrder(panel.shadowRoot);
  const rows = deepAll(panel.shadowRoot, "[data-stepper] li.step");
  const toggle = deep(panel.shadowRoot, "[data-stepper-toggle]");
  console.log(`  tab order (${stops.length}): ${stops.map(describe).join(" → ")}`);
  check(`the stepper draws ${rows.length} rows`, rows.length >= 6, String(rows.length));
  check("and not one of them is in the tab order",
    stops.every((one) => !deep(panel.shadowRoot, "[data-stepper]")?.contains(one) ||
      one.classList?.contains("stepper-toggle")));
  check("the collapsible row is a button, so Enter and Space open it",
    toggle?.tagName === "BUTTON", describe(toggle));
  check("it is in the tab order", stops.includes(toggle));
  check("and it says whether the list is open", toggle?.getAttribute("aria-expanded") === "false");
  check("the list it opens is the one it names",
    toggle?.getAttribute("aria-controls") === deep(panel.shadowRoot, "[data-stepper] ol")?.id);
  check("the one row in hand is the one marked as the step",
    deepAll(panel.shadowRoot, '[data-stepper] [aria-current="step"]').length === 1);
  check("the stepper comes before the step it is about",
    (deep(panel.shadowRoot, "[data-stepper]")?.compareDocumentPosition(
      deep(panel.shadowRoot, "h1.screen-title"),
    ) ?? 0) & 4,
    "the nav precedes the heading");
  toggle?.click();
  await settle();
  check("opening it says so", 
    deep(panel.shadowRoot, "[data-stepper-toggle]")?.getAttribute("aria-expanded") === "true");
  check("and sends nothing at all to the session",
    !calls.includes("act") && !calls.includes("stop"), calls.join(", "));
  dom.window.close();
}

{
  console.log("\n…and on a reading that has to be done again, where a verb is being offered");
  const { window, panel, dom, settle, calls } = await mount({
    name: "the wizard, the stepper with nothing to press",
    state: "session:awaiting_reading_measure_descent_stale",
    hash: "#/calibrate",
    expect: "[data-stepper]",
  });
  await settle();
  const rows = deepAll(panel.shadowRoot, "[data-stepper] .step-still");
  const before = active(panel);
  check(`the rail draws ${rows.length} rows`, rows.length >= 6, String(rows.length));
  check("and not one of them is a control",
    deepAll(panel.shadowRoot, "[data-stepper] button:not(.stepper-toggle)").length === 0);
  check("nor has a tabindex that would put it in the way",
    rows.every((row) => row.getAttribute("tabindex") === null));
  // Pressed one by one, which is what a finger does to a row that looks like a link.
  for (const row of rows) {
    row.click();
  }
  await settle();
  check(`pressing all ${rows.length} of them sends nothing`,
    !calls.includes("act") && !calls.includes("stop"), calls.join(", "));
  check("and moves the keyboard nowhere", active(panel) === before, describe(active(panel)));
  // …and the verb the rail used to duplicate is still offered, once, where it belongs.
  const secondary = deepAll(panel.shadowRoot, "button.cta.secondary");
  check("while the step itself still offers the way to repeat the reading",
    secondary.length >= 1, secondary.map((one) => (one.textContent ?? "").trim()).join(" / "));
  secondary[0]?.click();
  await settle();
  check("and pressing that sends exactly one act",
    calls.filter((one) => one === "act").length === 1, calls.join(", "));
  void window;
  dom.window.close();
}

const failed = checks.filter((one) => !one.ok);
console.log(`\n${checks.length} checks, ${failed.length} failed`);
process.exit(failed.length === 0 ? 0 : 1);
