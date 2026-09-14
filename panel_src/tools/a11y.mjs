// `npm run a11y` - axe-core over the panel, with no browser and nothing shipped.
//
// **Why this and not a browser.** The plan rules out a browser-driven suite (SPEC §9.2),
// and a panel that needs Playwright to be checked is a panel nobody checks. jsdom gives
// custom elements, shadow roots and a real accessibility tree, which is enough for the
// rules that are about *markup*: names, roles, labels, heading order, landmarks, duplicate
// ids, nested interactive content - which is precisely the family the row restructure of
// this lot is about. It has teeth: putting the old nested cross back makes it fail.
//
// **What it cannot do, and says so.** jsdom does no layout and resolves no CSS variable, so
// `color-contrast` and every target-size rule are disabled here rather than passed
// silently. Contrast is measured instead by `tools/contrast.mjs`, from the documented
// default values of the theme variables.
//
// Dev-only: `axe-core` and `jsdom` are devDependencies and nothing in `src/` imports
// either. The bundle this loads is the committed one, so what is audited is what ships.

import { readFile } from "node:fs/promises";

import { NEEDS_LAYOUT, STATES, axeSource, mount } from "./panel-host.mjs";

const audit = async (one) => {
  const { name, dom, window } = await mount(one);
  window.eval(await readFile(axeSource, "utf8"));
  const results = await window.eval(`axe.run(document, {
    rules: ${JSON.stringify(Object.fromEntries(NEEDS_LAYOUT.map((id) => [id, { enabled: false }])))},
    resultTypes: ["violations", "incomplete"],
  })`);
  dom.window.close();
  return { name, results };
};

let failed = 0;
for (const one of STATES) {
  const { name, results } = await audit(one);
  const violations = results.violations ?? [];
  const incomplete = results.incomplete ?? [];
  console.log(
    `\n${name}: ${results.passes?.length ?? "?"} checks, ` +
      `${violations.length} violations, ${incomplete.length} incomplete`,
  );
  for (const violation of violations) {
    failed += 1;
    console.log(`  ✖ [${violation.impact}] ${violation.id} - ${violation.help}`);
    for (const node of violation.nodes.slice(0, 4)) {
      console.log(`      ${node.html.slice(0, 160)}`);
    }
  }
  for (const one of incomplete) {
    console.log(`  ? ${one.id} - ${one.help} (${one.nodes.length})`);
  }
}

console.log(`\nrules not run here (no layout in jsdom): ${NEEDS_LAYOUT.join(", ")}`);
process.exit(failed === 0 ? 0 : 1);
