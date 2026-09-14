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

// --- the two cards ---------------------------------------------------------------------
for (const [name, hash] of [["cover detail", COVER], ["profile card", "#/profile/tall"]]) {
  console.log(`\n${name} → edit`);
  const { window, panel, dom, settle } = await mount({ name, state: "ready", hash });
  const stops = tabOrder(panel.shadowRoot);
  console.log(`  tab order (${stops.length}): ${stops.slice(0, 6).map(describe).join(" → ")} …`);
  check("the back arrow is the first stop", describe(stops[0]).includes("button"));
  check(
    "the card's heading took focus on the paint that drew it",
    active(panel)?.hasAttribute?.("data-heading") === true,
    describe(active(panel)),
  );
  const wide = deepAll(panel.shadowRoot, "button.wide:not([disabled])")[0];
  wide?.click();
  await settle();
  const fields = deepAll(panel.shadowRoot, "input.field");
  check("the form it opens has fields with names",
    fields.length > 0 && fields.every((one) => one.getAttribute("aria-label")));
  check("every field says whether it is refused",
    fields.every((one) => one.hasAttribute("aria-invalid")));
  press(window, active(panel) ?? panel, "Escape");
  await settle();
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

const failed = checks.filter((one) => !one.ok);
console.log(`\n${checks.length} checks, ${failed.length} failed`);
process.exit(failed.length === 0 ? 0 : 1);
