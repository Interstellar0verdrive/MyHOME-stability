// The illustration slot: the one place a value the panel did not write reaches CSS.
//
// A step's drawing is a background image, and a background image used to be built by
// joining strings - which meant a `src` carrying `");` could add declarations of its own
// and turn the slot into a full-screen overlay fetching from a host nobody chose. REVIEW
// lot 5 found it and fixed it; this is the assertion that was missing underneath.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { drawingStyle } from "../src/engine/safe-style";

describe("a drawing the integration serves", () => {
  it("is three properties and the documented defaults", () => {
    assert.deepEqual(drawingStyle({ src: "/myhome_static/metro.webp", alt: "" }), {
      backgroundImage: 'url("/myhome_static/metro.webp")',
      backgroundSize: "100% auto",
      backgroundPosition: "50% 60%",
    });
  });

  it("keeps a size and a position that are lengths and keywords", () => {
    assert.deepEqual(
      drawingStyle({ src: "/myhome_static/a.webp", alt: "", size: "contain", pos: "50% 40%" }),
      {
        backgroundImage: 'url("/myhome_static/a.webp")',
        backgroundSize: "contain",
        backgroundPosition: "50% 40%",
      },
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
      assert.equal(drawingStyle({ src, alt: "" }), null, src);
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
      assert.equal(drawingStyle({ src, alt: "" }), null, src);
    }
  });

  it("refuses a src that tries to close the url and open a declaration", () => {
    assert.equal(
      drawingStyle({
        src: '/myhome_static/a.png");background-color:red;--x:url("',
        alt: "",
      }),
      null,
    );
  });

  it("falls back to the defaults for a size or a position carrying anything else", () => {
    const style = drawingStyle({
      src: "/myhome_static/a.webp",
      alt: "",
      size: "auto;position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:9999",
      pos: "50% 60%;background:url(https://evil.example/x.png)",
    });
    assert.deepEqual(style, {
      backgroundImage: 'url("/myhome_static/a.webp")',
      backgroundSize: "100% auto",
      backgroundPosition: "50% 60%",
    });
  });
});
