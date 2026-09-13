// The bits of Home Assistant's frontend this panel actually touches.
//
// Hand-written rather than imported: `home-assistant-frontend` publishes no types for
// custom panels, and depending on a package that big to describe four properties would
// be a dependency nobody could update. Everything here is narrowed to what is used, so
// a rename upstream shows up as a compile error in one file instead of as `any`.

/** The connection `hass` carries: `home-assistant-js-websocket`, which reconnects itself. */
export interface HaConnection {
  sendMessagePromise<T>(message: Record<string, unknown>): Promise<T>;
  subscribeMessage<T>(
    callback: (message: T) => void,
    subscribeMessage: Record<string, unknown>,
  ): Promise<() => Promise<void>>;
}

export interface HaLocale {
  language: string;
}

export interface HaUser {
  id: string;
  name: string;
  is_admin: boolean;
}

export interface HomeAssistant {
  states: Record<string, { state: string; attributes: Record<string, unknown> }>;
  connection: HaConnection;
  language: string;
  locale: HaLocale;
  themes?: unknown;
  user?: HaUser;
}

/** `route.path` is the part after `/myhome-calibration`, leading slash included. */
export interface HaRoute {
  prefix: string;
  path: string;
}

/**
 * The registered panel, as `frontend.Panel.to_response` sends it. `config` is what the
 * integration put there: the `_panel_custom` block Home Assistant reads, and the
 * integration's own `version`, which is the panel's only way of knowing which release
 * it belongs to (the bundle itself carries no stamp - see `build.mjs`).
 */
export interface HaPanelInfo {
  title: string | null;
  icon: string | null;
  url_path: string;
  config: {
    version?: string;
    _panel_custom?: { name: string; module_url?: string };
  } | null;
}
