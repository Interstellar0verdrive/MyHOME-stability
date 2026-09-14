// Reading a Lit template without a browser.
//
// The Markdown renderer's whole security claim is a claim about *where* a string ends up:
// a hostile name has to arrive as a value Lit substitutes - which it escapes, and which
// can never be an attribute name, a tag or a URL - and never as part of the static text of
// the template. A `TemplateResult` says exactly that and says it structurally: `strings`
// is the part the program wrote and `values` is the part it was given.
//
// So this walks one and produces two things: the static skeleton, with every substitution
// marked, and the list of substituted values. An assertion on the skeleton is an assertion
// about what the program wrote; an assertion on the values is one about what it passed. No
// DOM, no `innerHTML`, and nothing that could make a test pass by rendering a thing the
// browser would have refused.

interface LitLike {
  strings: readonly string[];
  values: readonly unknown[];
}

const isTemplate = (value: unknown): value is LitLike =>
  typeof value === "object" &&
  value !== null &&
  Array.isArray((value as LitLike).strings) &&
  Array.isArray((value as LitLike).values);

export interface ReadTemplate {
  /** The markup the program wrote, with every substitution shown as `{{…}}`. */
  skeleton: string;
  /** The same, with the substitutions taken out: *only* what the program wrote. */
  statics: string;
  /** Every string that was substituted into it, in order, however deeply nested. */
  values: string[];
}

const walk = (node: unknown, out: ReadTemplate): void => {
  if (isTemplate(node)) {
    node.strings.forEach((text, index) => {
      out.skeleton += text;
      out.statics += text;
      if (index < node.values.length) {
        walk(node.values[index], out);
      }
    });
    return;
  }
  if (Array.isArray(node)) {
    for (const item of node) {
      walk(item, out);
    }
    return;
  }
  if (node === undefined || node === null || typeof node === "object") {
    // `nothing`, `noChange` and the directives render nothing a test can read.
    return;
  }
  const text = String(node);
  out.values.push(text);
  out.skeleton += `{{${text}}}`;
};

export const read = (template: unknown): ReadTemplate => {
  const out: ReadTemplate = { skeleton: "", statics: "", values: [] };
  walk(template, out);
  return out;
};
