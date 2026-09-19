// The illustration slot: the one place a value the panel did not write reaches the DOM.
//
// A step's drawing used to be a background image built by joining strings - which meant a
// `src` carrying `");` could add declarations of its own and turn the slot into a
// full-screen overlay fetching from a host nobody chose. REVIEW lot 5 found it and fixed
// it; this is the assertion that was missing underneath. The drawing is an `<img>` now
// (live findings 10, 14 and 19: a box with a background crops whatever does not match its
// shape), so no string is joined into CSS any more - but the address is still the
// translation files' and is still checked here before anything asks for it.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { drawingSrc } from "../src/engine/safe-style";

describe("a drawing the integration serves", () => {
  it("is the address itself, and nothing about its shape", () => {
    assert.equal(drawingSrc({ src: "/myhome_static/metro.webp", alt: "" }), "/myhome_static/metro.webp");
  });

  it("does not care what the step called it", () => {
    assert.equal(
      drawingSrc({ src: "/myhome_static/a/b_c-1.webp", alt: "the bottom edge" }),
      "/myhome_static/a/b_c-1.webp",
    );
  });
});

describe("a drawing from anywhere else is not drawn", () => {
  it("refuses a scheme, a host and a path outside the served directory", () => {
    for (const src of [
      "https://evil.example/x.png",
      "//evil.example/x.png",
      "/local/x.png",
      "data:image/svg+xml;base64,AAAA",
      "/myhome_static/../secret.png",
      "/myhome_static/a/../../secret.png",
    ]) {
      assert.equal(drawingSrc({ src, alt: "" }), null, src);
    }
  });

  it("refuses every other spelling of climbing out, and of not being a path at all", () => {
    for (const src of [
      // The browser decodes before it resolves, so an encoded dot segment is a dot
      // segment - and a prefix check would have let all six of these through.
      "/myhome_static/%2e%2e/secret.png",
      "/myhome_static/..%2fsecret.png",
      "/myhome_static/a.png?x=/../secret",
      "/myhome_static/a.png#/../secret",
      "/myhome_static/./a.png",
      "/myhome_static/..",
      // ...and a path that is not one: no scheme, no host, no backslash, no newline.
      "/myhome_static/\\..\\secret.png",
      "HTTPS://evil.example/myhome_static/a.png",
      "/myhome_static/a.png\n/x",
      // The prefix alone, with no file after it, is not a drawing either.
      "/myhome_static/",
    ]) {
      assert.equal(drawingSrc({ src, alt: "" }), null, src);
    }
  });

  it("refuses a src that tries to close the url and open a declaration", () => {
    assert.equal(
      drawingSrc({
        src: '/myhome_static/a.png");background-color:red;--x:url("',
        alt: "",
      }),
      null,
    );
  });
});
