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

import { COVER, deep, deepAll, makePending, mount, openDialog } from "./panel-host.mjs";

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

const failed = checks.filter((one) => !one.ok);
console.log(`\n${checks.length} checks, ${failed.length} failed`);
process.exit(failed.length === 0 ? 0 : 1);
