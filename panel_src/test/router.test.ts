// Which screen an address asks for, and what an address for a screen looks like.
//
// The panel writes its own hash and reads Home Assistant's `route.path` when there is
// none, so a deep link has to land on the right screen on the first paint - and a
// half-typed one must not blank the page.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { Router, buildPath, parsePath } from "../src/engine/router";

describe("reading an address", () => {
  it("reads the overview out of every spelling of nothing", () => {
    for (const raw of ["", "/", "//", "#/", "#"]) {
      assert.deepEqual(parsePath(raw), { view: "overview", params: {}, path: "/" });
    }
  });

  it("reads a shutter and a profile", () => {
    assert.deepEqual(parsePath("/cover/aa:bb-2-81"), {
      view: "cover",
      params: { id: "aa:bb-2-81" },
      path: "/cover/aa:bb-2-81",
    });
    assert.equal(parsePath("/profile/tall").view, "profile");
    assert.equal(parsePath("/profile/tall").params.name, "tall");
  });

  it("reads the wizard out of the address, and nothing else out of it", () => {
    // The one rule this route has (SPEC §5.1, decision 24): **reloading `#/calibrate`
    // can never start a session**, because the address says nothing about which shutter
    // or which path. What the user asked for is in the store. A link written against an
    // older spelling still opens the wizard, and what it names is dropped.
    for (const raw of ["/calibrate", "#/calibrate", "/calibrate/", "/calibrate/42",
                       "/calibrate/00:03:50:aa:bb:cc-2-81", "/calibrate/path_a/tall"]) {
      assert.deepEqual(
        parsePath(raw),
        { view: "calibrate", params: {}, path: "/calibrate" },
        raw,
      );
    }
  });

  it("unescapes the identifier, because a profile may be called 'Tall shutters'", () => {
    assert.equal(parsePath("/profile/Tall%20shutters").params.name, "Tall shutters");
    assert.equal(parsePath("#/cover/aa%3Abb-2-81").params.id, "aa:bb-2-81");
  });

  it("keeps the raw text when the escape is half typed, rather than throwing", () => {
    const route = parsePath("/cover/aa%");
    assert.equal(route.view, "cover");
    assert.equal(route.params.id, "aa%");
  });

  it("calls a path it does not know unknown, and a known one with nothing after it too", () => {
    assert.equal(parsePath("/nonsense").view, "unknown");
    assert.equal(parsePath("/cover").view, "unknown");
    assert.equal(parsePath("/cover/").view, "unknown");
  });

  it("tolerates the slashes a person leaves behind", () => {
    assert.equal(parsePath("///profile/tall//").params.name, "tall");
  });
});

describe("writing an address", () => {
  it("escapes what a name may contain", () => {
    assert.equal(buildPath("profile", "Tall shutters"), "/profile/Tall%20shutters");
    assert.equal(buildPath("cover", "aa:bb-2-81"), "/cover/aa%3Abb-2-81");
  });

  it("is the overview for the overview, and for a screen with nothing to name", () => {
    assert.equal(buildPath("overview"), "/");
    assert.equal(buildPath("cover", ""), "/");
  });

  it("writes the wizard's address with nothing after it, whatever it is handed", () => {
    assert.equal(buildPath("calibrate"), "/calibrate");
    assert.equal(buildPath("calibrate", "00:03:50:aa:bb:cc-2-81"), "/calibrate");
  });

  it("writes the list for a view with no address of its own", () => {
    // Never another screen's address: a wrong one that leads somewhere real is worse than
    // a wrong one that leads nowhere.
    assert.equal(buildPath("unknown", "tall"), "/");
    assert.equal(buildPath("unknown"), "/");
  });

  it("survives a round trip", () => {
    const name = "Tall shutters / west";
    assert.equal(parsePath(buildPath("profile", name)).params.name, name);
  });
});

describe("the two places an address can come from", () => {
  // `Router` binds `hashchange` on the window; Node has an `EventTarget` and no window,
  // and the two halves of this class are worth testing apart from a browser.
  const fake = globalThis as unknown as {
    window: EventTarget;
    location: { hash: string };
  };
  fake.window = new EventTarget();

  it("prefers its own hash to the property the host set", () => {
    const router = new Router();
    fake.location = { hash: "#/profile/tall" };
    router.setHostPath("/cover/aa");
    assert.equal(router.current.view, "profile");
    fake.location = { hash: "" };
    assert.equal(router.current.view, "cover");
  });

  it("tells its listener only when the effective address really changed", () => {
    const router = new Router();
    fake.location = { hash: "" };
    const seen: string[] = [];
    router.start((route) => seen.push(route.path));
    router.setHostPath("/cover/aa");
    router.setHostPath("/cover/aa");
    assert.deepEqual(seen, ["/cover/aa"]);
    router.stop();
  });

  it("says nothing when a hash is already answering for the address", () => {
    const router = new Router();
    fake.location = { hash: "#/profile/tall" };
    const seen: string[] = [];
    router.start((route) => seen.push(route.path));
    router.setHostPath("/cover/aa");
    assert.deepEqual(seen, []);
    router.stop();
  });
});
