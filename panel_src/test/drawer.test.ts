// Which address is a drawer, and what "back" means inside one.
//
// The whole of the back stack is three rules and one level, and every one of them is a
// thing a user can walk into with a browser's own back button: a deep link that opens the
// list and a panel over it, a link from one panel to the other, and the step back that has
// to end at the list rather than ping-pong between two cards. They are asserted here, on
// the pure functions, because the alternative is a jsdom that has to be driven through
// four navigations to say the same thing - which `npm run keyboard` does do, once, over
// the real markup.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { backPath, isDrawerRoute, nextBack } from "../src/engine/drawer";
import { parsePath, type Route } from "../src/engine/router";

const at = (path: string): Route => parsePath(path);

const OVERVIEW = at("/");
const COVER_A = at("/cover/aa:bb-2-81");
const COVER_B = at("/cover/aa:bb-2-82");
const PROFILE = at("/profile/tall");

describe("which screens are drawn over the list", () => {
  it("is the two routed cards, and nothing else", () => {
    assert.equal(isDrawerRoute(COVER_A), true);
    assert.equal(isDrawerRoute(PROFILE), true);
    assert.equal(isDrawerRoute(OVERVIEW), false);
    assert.equal(isDrawerRoute(at("/calibrate/session-1")), false);
    assert.equal(isDrawerRoute(at("/nonsense")), false);
  });
});

describe("the one level of back stack", () => {
  it("remembers nothing when a drawer is opened from the list", () => {
    assert.equal(nextBack(null, OVERVIEW, COVER_A), null);
    assert.equal(backPath(nextBack(null, OVERVIEW, COVER_A)), "/");
  });

  it("remembers the card being left when one drawer opens another", () => {
    const back = nextBack(null, COVER_A, PROFILE);
    assert.equal(back?.path, COVER_A.path);
    assert.equal(backPath(back), COVER_A.path);
  });

  it("spends the stack on the way back, so one level is all there ever is", () => {
    // detail → profile → the same detail: the arrow becomes a close again.
    const back = nextBack(null, COVER_A, PROFILE);
    assert.equal(nextBack(back, PROFILE, COVER_A), null);
  });

  it("keeps one level when the third screen is a new one", () => {
    // detail A → profile → detail B: what is behind B is the profile, not A.
    const back = nextBack(null, COVER_A, PROFILE);
    assert.equal(nextBack(back, PROFILE, COVER_B)?.path, PROFILE.path);
  });

  it("forgets everything on the way out to the list", () => {
    const back = nextBack(null, COVER_A, PROFILE);
    assert.equal(nextBack(back, PROFILE, OVERVIEW), null);
  });

  it("survives a repaint of the same screen", () => {
    const back = nextBack(null, COVER_A, PROFILE);
    assert.equal(nextBack(back, PROFILE, at("/profile/tall"))?.path, COVER_A.path);
  });
});
