// The Markdown renderer, and the one thing it exists to make impossible.
//
// Every sentence on this panel comes out of a translation file, and a translation file is
// edited by hand, by several people, in seven languages. So the renderer's contract is not
// "render Markdown well": it is that **nothing in a string it is given can become anything
// but text** - no tag, no attribute, no URL, no request to a host nobody chose. There is no
// `unsafeHTML` anywhere in the panel, and these assertions are what says so structurally:
// a hostile string has to arrive as a substituted *value* of the Lit template and never as
// part of the markup the program wrote. `test/lit-text.ts` explains how that is read.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { renderMarkdown, splitLeadingImage } from "../src/engine/markdown";
import { read } from "./lit-text";

describe("what it renders", () => {
  it("makes a paragraph of a paragraph", () => {
    const out = read(renderMarkdown("one\n\ntwo"));
    assert.deepEqual(out.values, ["one", "two"]);
    assert.equal((out.skeleton.match(/<p>/g) ?? []).length, 2);
  });

  it("makes a line break of a single newline, because that is how a cell is typed", () => {
    const out = read(renderMarkdown("one\ntwo"));
    assert.deepEqual(out.values, ["one", "two"]);
    assert.match(out.skeleton, /<br/);
  });

  it("makes a list of a list", () => {
    const out = read(renderMarkdown("- one\n- two"));
    assert.deepEqual(out.values, ["one", "two"]);
    assert.match(out.skeleton, /<ul>/);
    assert.equal((out.skeleton.match(/<li>/g) ?? []).length, 2);
  });

  it("emphasises what is between a pair of markers and leaves an unmatched one alone", () => {
    assert.match(read(renderMarkdown("a **b** c")).skeleton, /<strong>/);
    const odd = read(renderMarkdown("a **b c"));
    assert.doesNotMatch(odd.skeleton, /<strong>/);
    assert.deepEqual(odd.values, ["a ", "b c"]);
  });

  it("draws an image the integration itself serves", () => {
    const out = read(renderMarkdown("![the tape](/myhome_static/metro.webp)"));
    assert.match(out.skeleton, /<img class="md-image"/);
    assert.deepEqual(out.values, ["/myhome_static/metro.webp", "the tape"]);
  });
});

describe("what it refuses", () => {
  it("renders a script tag as the characters somebody typed", () => {
    const out = read(renderMarkdown("<script>alert(1)</script>"));
    assert.deepEqual(out.values, ["<script>alert(1)</script>"]);
    assert.doesNotMatch(out.statics, /<script/);
  });

  it("renders an onerror image as text and never as an element", () => {
    const hostile = '<img src=x onerror="alert(1)">';
    const out = read(renderMarkdown(hostile));
    assert.deepEqual(out.values, [hostile]);
    assert.doesNotMatch(out.statics, /onerror/);
    assert.doesNotMatch(out.statics, /<img/);
  });

  it("has no link syntax at all, so a javascript: URL is a sentence", () => {
    const out = read(renderMarkdown("[click](javascript:alert(1))"));
    assert.deepEqual(out.values, ["[click](javascript:alert(1))"]);
    assert.doesNotMatch(out.statics, /href/);
    assert.doesNotMatch(out.statics, /<a[ >]/);
  });

  it("never builds an href out of a translated string, whatever the string is", () => {
    for (const text of [
      "[x](https://evil.example)",
      "<a href='https://evil.example'>x</a>",
      "**[x](/config)**",
    ]) {
      // `statics` and not `skeleton`: what matters is that the program never *wrote*
      // an href, not that the sentence does not contain the six letters.
      assert.doesNotMatch(read(renderMarkdown(text)).statics, /href/, text);
    }
  });

  it("shows an off-site image as its alt text and fetches nothing", () => {
    const out = read(renderMarkdown("![evil](https://evil.example/x.png)"));
    assert.deepEqual(out.values, ["evil"]);
    assert.doesNotMatch(out.skeleton, /<img/);
  });

  it("refuses an image that climbs out of the served directory", () => {
    for (const src of [
      "/myhome_static/../../secret.png",
      "//evil.example/x.png",
      "data:image/svg+xml;base64,AAAA",
    ]) {
      const out = read(renderMarkdown(`![alt](${src})`));
      assert.doesNotMatch(out.skeleton, /<img/, src);
    }
  });
});

describe("the illustration at the head of a step", () => {
  it("lifts one the integration serves out of the body", () => {
    const { image, body } = splitLeadingImage(
      "![the tape](/myhome_static/metro.webp)\n\nRead the tape.",
    );
    assert.deepEqual(image, { alt: "the tape", src: "/myhome_static/metro.webp" });
    assert.equal(body, "Read the tape.");
  });

  it("leaves an off-site one in the body, where the renderer will refuse it too", () => {
    const { image, body } = splitLeadingImage("![evil](https://evil.example/x.png)\n\nBody.");
    assert.equal(image, null);
    assert.match(body, /evil\.example/);
    assert.doesNotMatch(read(renderMarkdown(body)).skeleton, /<img/);
  });

  it("leaves a body that does not open with an image exactly as it is", () => {
    const text = "Just words.\n\nAnd more.";
    assert.deepEqual(splitLeadingImage(text), { image: null, body: text });
    assert.deepEqual(splitLeadingImage(""), { image: null, body: "" });
  });
});
