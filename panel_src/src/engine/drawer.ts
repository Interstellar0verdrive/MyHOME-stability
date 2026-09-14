// Which screen is a drawer over the overview, and what is behind it.
//
// `#/cover/<id>` and `#/profile/<name>` are **not** screens of their own any more. The
// design draws them as panels from the right (Consegna 0.6.0, §3: "pannelli da destra
// (480 px)", "pannelli come fogli dal basso" below 600 px), the review panel was already
// built that way, and the first live pass asked for the other two to match: the list stays
// on the screen behind them, which is where the shutter that was tapped is.
//
// The route did not change with them. A deep link to `#/cover/aa:bb-2-81` still opens that
// shutter, on first paint, from a cold browser - it opens the overview *and* the drawer,
// which is what the plan asks for (§3.3) and what a modal over a list nobody has loaded
// could never do.
//
// **One level of back stack, and no more.** The only way to move between two drawers is a
// link inside one: a cover's card links to its profile, and a profile's card links to each
// of its followers. So the question the leading control has to answer is "one screen back,
// or out", and the whole of the answer is below. It is a pure function of the two routes
// because a stack that lived in the DOM would be a stack that survived a reload of the
// page and pointed at a shutter nobody is looking at.

import { type Route } from "./router";

/** True for a route drawn as a drawer over the overview. */
export const isDrawerRoute = (route: Route): boolean =>
  route.view === "cover" || route.view === "profile";

/**
 * The one remembered screen, after a move from `before` to `next`.
 *
 * * out to the overview, or in from it: nothing is remembered;
 * * the same screen repainted: whatever was remembered stays;
 * * **back onto the remembered screen**: the stack is spent, which is what keeps it one
 *   level deep and what makes the leading control turn back into a close;
 * * anything else: the screen being left is what one step back means.
 */
export const nextBack = (back: Route | null, before: Route, next: Route): Route | null => {
  if (!isDrawerRoute(next) || !isDrawerRoute(before)) {
    return null;
  }
  if (before.path === next.path) {
    return back;
  }
  if (back && back.path === next.path) {
    return null;
  }
  return before;
};

/** Where the drawer's leading control goes: one screen back, or out to the overview. */
export const backPath = (back: Route | null): string => back?.path ?? "/";
