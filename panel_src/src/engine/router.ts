// Which screen the address bar is asking for.
//
// The panel is one element for four screens, so something has to turn a location into a
// view, and back. Home Assistant gives a custom panel a `route` property whose `path` is
// whatever follows `/myhome-calibration`, and it navigates by `history.pushState` plus a
// `location-changed` event on the document. That works, but it is frontend behaviour this
// repository cannot verify (lot 4, open point 2), and a panel that cannot move between
// its own screens is a panel with one screen.
//
// So the router reads **both**, and prefers the one that cannot be taken away:
//
// * `#/cover/<id>` - the panel's own hash, which it writes itself and which no host
//   behaviour can reinterpret. `hashchange` is a platform event, not a private contract.
// * `route.path` - Home Assistant's, honoured when there is no hash, so a deep link of
//   the form `/myhome-calibration/cover/<id>` opens the right screen on the first paint.
//
// One consequence worth stating: a link *out* of the panel is an ordinary `<a href>` and
// is left to the browser and to Home Assistant's own router. Only movement **inside** the
// panel goes through here.

/** The views the panel can show. `calibrate` is reserved: 0.7.0 routes it, 0.6.0 does not. */
export type ViewId = "overview" | "cover" | "profile" | "calibrate" | "unknown";

export interface Route {
  view: ViewId;
  /** `id` for `/cover/:id`, `name` for `/profile/:name`, `session` for `/calibrate/:session`. */
  params: Record<string, string>;
  /** The normalised path this route was read from, leading slash included. */
  path: string;
}

const OVERVIEW: Route = { view: "overview", params: {}, path: "/" };

/** `/cover/aa%3Abb-2-81` -> `{view: "cover", params: {id: "aa:bb-2-81"}}`. */
export const parsePath = (raw: string): Route => {
  const path = "/" + (raw || "").replace(/^#/, "").replace(/^\/+/, "").replace(/\/+$/, "");
  if (path === "/") {
    return OVERVIEW;
  }
  const parts = path.slice(1).split("/");
  const rest = parts.slice(1).join("/");
  let value = rest;
  try {
    value = decodeURIComponent(rest);
  } catch {
    // A half-typed escape in the address bar is not worth a blank screen; the raw text
    // simply will not match any shutter, and the view says so.
  }
  if (parts[0] === "cover" && rest) {
    return { view: "cover", params: { id: value }, path };
  }
  if (parts[0] === "profile" && rest) {
    return { view: "profile", params: { name: value }, path };
  }
  if (parts[0] === "calibrate" && rest) {
    return { view: "calibrate", params: { session: value }, path };
  }
  return { view: "unknown", params: {}, path };
};

/** `/profile/Tall shutters` -> `#/profile/Tall%20shutters`. */
export const buildPath = (view: ViewId, value?: string): string => {
  if (view === "overview" || !value) {
    return "/";
  }
  const segment = view === "cover" ? "cover" : view === "profile" ? "profile" : "calibrate";
  return `/${segment}/${encodeURIComponent(value)}`;
};

export class Router {
  private _onChange: (route: Route) => void = () => undefined;
  private _fromHost = "/";
  private _listener = (): void => this._emit();

  start(onChange: (route: Route) => void): void {
    this._onChange = onChange;
    window.addEventListener("hashchange", this._listener);
  }

  stop(): void {
    window.removeEventListener("hashchange", this._listener);
    this._onChange = () => undefined;
  }

  /**
   * The path Home Assistant put in the `route` property. It only decides anything while
   * the panel has written no hash of its own, which is exactly the first paint after a
   * deep link.
   */
  setHostPath(path: string | undefined): void {
    const next = path || "/";
    if (next === this._fromHost) {
      return;
    }
    const before = this.current.path;
    this._fromHost = next;
    if (this.current.path !== before) {
      this._emit();
    }
  }

  get current(): Route {
    const hash = typeof location !== "undefined" ? location.hash : "";
    if (hash && hash.length > 1) {
      return parsePath(hash.slice(1));
    }
    return parsePath(this._fromHost);
  }

  /** Move to another screen of this panel. */
  navigate(path: string): void {
    const target = "#" + (path.startsWith("/") ? path : "/" + path);
    if (location.hash === target) {
      return;
    }
    location.hash = target;
  }

  private _emit(): void {
    this._onChange(this.current);
  }
}
