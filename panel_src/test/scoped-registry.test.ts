// No form APIs anywhere under `src/` - the scoped element registry forbids them.
//
// Home Assistant's frontend loads custom elements through a **scoped registry** polyfill,
// and that polyfill does not implement the form-related parts of the DOM: in the v2 panel
// a perfectly ordinary read of a form's elements collection threw "Method not
// implemented" and took a whole screen down with it, in production, on a browser nobody
// could reproduce it on because the polyfill only loads inside Home Assistant.
//
// The rule that came out of it (SPEC §5.9) is blunt on purpose: **the panel never uses a
// form.** Values are read from the event (`event.target.value`) or with `querySelector`
// on the shadow root, which is what every screen in the panel already does.
//
// Two checks hold it, and they fail for different reasons:
//
// * this one, a scan of the sources, which names the file and the line - it fails on the
//   line somebody wrote, before a bundle exists;
// * `tools/panel-host.mjs`, which installs getters that throw "Method not implemented" on
//   exactly these properties before it loads the bundle, so `npm run a11y`,
//   `npm run keyboard` and `npm run session` fail if the shipped code really reaches for
//   one. That one fails on the screen, the way the user met it.
//
// **Comments and strings are stripped first.** A rule that could not be written down in
// the file it governs would be a rule nobody could explain, and this very file talks
// about `form.elements` for three paragraphs.

import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, it } from "node:test";

/**
 * The sources, found from the working directory.
 *
 * `import.meta.url` is no use: `test/run.mjs` compiles each test into a temporary
 * directory, so a path relative to this module points at the bundle and not at the tree.
 * npm runs a script with the package directory as the working directory, and that is
 * `panel_src`.
 */
const SRC = join(process.cwd(), "src");

const sources = (directory: string): string[] => {
  const found: string[] = [];
  for (const name of readdirSync(directory).sort()) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) {
      found.push(...sources(path));
    } else if (name.endsWith(".ts")) {
      found.push(path);
    }
  }
  return found;
};

/**
 * The code, with every comment and every literal blanked out and the lines kept.
 *
 * A scanner over the raw text would fail on the sentence explaining the rule, and one
 * that stripped comments by regular expression would fail on a `//` inside a URL. This is
 * the small state machine that does it properly: code, line comment, block comment,
 * the two quotes and a template literal, with escapes. What comes out has the same length
 * and the same line breaks as what went in, so a match still reports the real line.
 */
export const strip = (text: string): string => {
  const out: string[] = [];
  let mode: "code" | "line" | "block" | "'" | '"' | "`" = "code";
  for (let index = 0; index < text.length; index += 1) {
    const here = text[index];
    const next = text[index + 1];
    const keep = (character: string): void => {
      out.push(character === "\n" ? "\n" : character);
    };
    if (mode === "code") {
      if (here === "/" && next === "/") {
        mode = "line";
        keep(" ");
        continue;
      }
      if (here === "/" && next === "*") {
        mode = "block";
        keep(" ");
        continue;
      }
      if (here === "'" || here === '"' || here === "`") {
        mode = here;
        keep(" ");
        continue;
      }
      keep(here);
      continue;
    }
    if (mode === "line") {
      if (here === "\n") {
        mode = "code";
        keep("\n");
        continue;
      }
      keep(" ");
      continue;
    }
    if (mode === "block") {
      if (here === "*" && next === "/") {
        mode = "code";
        keep(" ");
        out.push(" ");
        index += 1;
        continue;
      }
      keep(here === "\n" ? "\n" : " ");
      continue;
    }
    // Inside a literal: an escape swallows the character after it, so that `"\""` ends
    // where it really ends.
    if (here === "\\") {
      keep(" ");
      out.push(next === "\n" ? "\n" : " ");
      index += 1;
      continue;
    }
    if (here === mode) {
      mode = "code";
      keep(" ");
      continue;
    }
    keep(here === "\n" ? "\n" : " ");
  }
  return out.join("");
};

/** Every API SPEC §5.9 strikes out, and what to do instead. */
const FORBIDDEN: { what: string; instead: string; pattern: RegExp }[] = [
  {
    what: "a <form> element",
    instead: "a plain container: a form holds state, and state lives in the store",
    pattern: /<\s*form[\s>/]/g,
  },
  {
    what: "the elements collection of a form or a fieldset",
    instead: "read the value off the event, or querySelector the shadow root",
    pattern: /\.elements\b/g,
  },
  {
    what: "document.forms",
    instead: "querySelector on the shadow root the field lives in",
    pattern: /\bdocument\s*\.\s*forms\b|\.forms\b/g,
  },
  {
    what: "FormData",
    instead: "collect the fields the screen knows it has, by name",
    pattern: /\bFormData\b/g,
  },
  {
    what: "requestSubmit()",
    instead: "call the action the button would have called",
    pattern: /\brequestSubmit\b/g,
  },
  {
    what: "form.reset()",
    instead: "set the fields back from the store, which is what they are drawn from",
    pattern: /\.reset\s*\(/g,
  },
  {
    what: "namedItem()",
    instead: "querySelector with the id or the data attribute",
    pattern: /\bnamedItem\b/g,
  },
  {
    what: "attachInternals() / formAssociated",
    instead: "nothing in this panel is a form-associated element",
    pattern: /\battachInternals\b|\bformAssociated\b/g,
  },
];

describe("the DOM APIs the scoped registry does not implement", () => {
  it("finds the sources where npm runs it from", () => {
    assert.ok(statSync(SRC).isDirectory(), `no sources at ${SRC}`);
    const files = sources(SRC);
    assert.ok(files.length > 20, `only ${files.length} sources found under ${SRC}`);
  });

  it("is never used anywhere under src/", () => {
    const offences: string[] = [];
    for (const path of sources(SRC)) {
      const code = strip(readFileSync(path, "utf8"));
      const lines = code.split("\n");
      for (const { what, instead, pattern } of FORBIDDEN) {
        lines.forEach((line, index) => {
          pattern.lastIndex = 0;
          if (pattern.test(line)) {
            offences.push(
              `${relative(process.cwd(), path)}:${index + 1}: ${what} - ${instead}`,
            );
          }
        });
      }
    }
    assert.deepEqual(
      offences,
      [],
      `the scoped registry throws "Method not implemented" on these:\n${offences.join("\n")}`,
    );
  });

  it("would say where, if one were written", () => {
    // The scan is only worth having if it really fires, and if what it says is enough to
    // find the line. This is that assertion, on a source that does not exist.
    const code = strip('const sinner = () => {\n  return document.forms;\n};\n');
    const line = code.split("\n").findIndex((one) => /\.forms\b/.test(one));
    assert.equal(line, 1);
  });

  it("does not fire on the prose that explains it, or on a URL in a comment", () => {
    const innocent = [
      "// form.elements throws inside Home Assistant; see the note about FormData.",
      "/* document.forms, requestSubmit(), namedItem() - none of them. */",
      'const doc = "https://example.invalid/a//b"; // and namedItem in a sentence',
      "const kept = `a template with document.forms in it`;",
    ].join("\n");
    const code = strip(innocent);
    for (const { pattern } of FORBIDDEN) {
      pattern.lastIndex = 0;
      assert.equal(pattern.test(code), false, `fired on prose: ${pattern}`);
    }
    // …and the line count survives, which is what makes the report usable.
    assert.equal(code.split("\n").length, innocent.split("\n").length);
  });
});
