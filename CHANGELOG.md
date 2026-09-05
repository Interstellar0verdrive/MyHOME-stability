# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-09-05

Robustness and observability. Everything in this release is **additive**: with the
default options nothing changes in how the integration talks to your gateway, and no
entity_id, unique_id or event contract is touched.

### Added

- **Diagnostics download.** *Settings → Devices & services → MyHOME → ⋮ → Download
  diagnostics* (also available per device) produces a JSON file for bug reports: the
  config entry with the password removed and the MAC/host/UDN partially masked, the
  tunables in effect, a summary of the validated `myhome.yaml` (per platform: device
  count and `who-where` keys, never your device names), the gateway statistics and
  the last 50 bus frames. Session-negotiation frames are replaced by a marker so a
  password hash can never end up in a public issue. See
  [Troubleshooting](docs/troubleshooting.md#diagnostics-download).
- **Gateway diagnostic entities** on the gateway device: a `connectivity` binary
  sensor and a "last frame" timestamp sensor (both enabled by default), plus
  reconnect, dropped-command and queue-length counters (disabled by default — enable
  them from the entity settings when you are chasing a problem).
- **Repairs.** The integration now raises a Home Assistant repair issue, in all four
  languages, when `myhome.yaml` cannot be loaded (with the file path and the exact
  validation message), when it contains keys the integration does not know (listed,
  with a "did you mean" hint, dismissable), and when the gateway's MAC address has no
  section in the file. Each issue disappears on its own as soon as a later load no
  longer hits it.
- **Tunable session options** in *Configure*, pre-filled with the values 0.2.x used
  internally, so leaving them alone changes nothing: idle watchdog (300 s), probe
  window (30 s), command timeout (10 s), command queue TTL (60 s) and the default
  instant-power keep-alive (125 min, used when a sensor does not set
  `keepalive_minutes` in `myhome.yaml`). See
  [Configuration → Options](docs/configuration.md#options).

### Changed

- Identical status requests that are already waiting in the command queue are
  coalesced instead of being sent twice, so a reconnect no longer floods the gateway
  with duplicate `*#…##` frames.
- Motion binary sensors keep their state across a reload or restart (the off-delay is
  restored with them), like covers already did in 0.2.1.
- Temperature and illuminance sensors ask for a fresh value when the gateway
  reconnects, instead of waiting for the next spontaneous frame.

## [0.2.1] - 2026-09-05

### Fixed

- Time-based cover position was lost on every config-entry reload (and on a
  restart while the gateway was down): the entity is already `unavailable` when
  Home Assistant snapshots it for restoration, so the position is now persisted
  through `extra_restore_state_data` instead of the state attributes.

## [0.2.0] - 2026-09-05

A stability-focused rewrite of the gateway session handling, the YAML validator and
every platform. See the [v0.2.0 release notes](https://github.com/Interstellar0verdrive/MyHOME-stability/releases/tag/v0.2.0)
for the upgrade story in plain language.

### Breaking changes

- **Lock/Unlock buttons are no longer generated automatically.** They used to be
  created for every light/switch/cover actuator (including General/Area addresses,
  where a single click could lock the whole plant). On upgrade these entities
  **disappear**. To keep them for a specific device, add `lock_buttons: true` under
  that device in `myhome.yaml` — they are only created for Point-to-Point WHEREs.
- Friendly names of power/energy sensors no longer repeat the device name (e.g.
  "Power" instead of "Kitchen Oven Kitchen Oven Power"). `entity_id`s are unchanged,
  but automations or dashboards matching on the old friendly name text need updating.
- Config entries are migrated to version 2 on first load after the update (unwraps
  `manufacturer`/`sw_version`/etc. that were stored as 1-element lists). This is
  automatic; no user action is required, but it cannot be rolled back to 0.1.x
  without reconfiguring the gateway.

### Fixed

- **Commands silently dropped after a failed reconnect.** The command session used
  to mark a command as sent even when OWNd gave up after repeated connection
  refusals, and a half-open socket had no send timeout, so the single command
  worker could block forever while the queue kept growing. Commands now have a
  10 s send timeout, are retried once on a fresh session, and are dropped (with a
  rate-limited warning) instead of being silently swallowed — this is the root
  cause of commands "not passing" that used to require a watchdog automation.
- **Dead event session never detected.** There was no TCP keepalive and no
  idle-connection watchdog on the event (monitor) session, so a silently dead
  socket kept reporting `is_connected = True` until the next full reload — the
  root cause of the daily reload workaround. The event session now has TCP
  keepalive, and after 300 s of silence it probes the gateway and reconnects
  (with exponential backoff) if nothing comes back. Entity `available` now
  actually reflects the gateway connection state.
- **Energy sensors stuck at `unknown`.** Two separate bugs: the instant-power
  noise filter was also applied to totaliser replies (which report 0 W and were
  therefore suppressed), and totals requested by the integration were read on the
  command socket, where they were discarded instead of reaching the entities.
  Both are fixed: the filter only ever applies to instant active-power frames,
  and command-session replies are dispatched to entities exactly like monitor
  events. Note: some gateways (e.g. MyHOMEServer1 with F520/F521 meters)
  acknowledge the totaliser requests without returning data; on such hardware
  the daily/monthly/total sensors still show `unknown`, which is why they stay
  disabled by default.
- **Duplicate WHERE silently dropped a device.** Two devices sharing the same
  WHO/WHERE (e.g. two covers both on `where: "81"`) used to have the second
  silently overwrite the first. This is now a setup error naming both YAML keys.
- `binary_sensor` crashed the whole platform when `class`/`device_class` was
  missing or used the alias key; `device_class` is now a documented alias of
  `class` on every platform.
- Options flow crashed (`AttributeError`) on Home Assistant ≥ 2025.12.
- Reauthentication was never triggered on a rejected password (missing
  `entry_id`); a stale password now starts a proper reauth flow.
- Gateway unreachable at startup raised a raw `TypeError` instead of a retryable
  `ConfigEntryNotReady`.
- Basic covers were always `unknown`/`unavailable`: `shutter_run`, `inverted`,
  `class` and `icon` were accepted by the schema but never read by `cover.py`.
- Light brightness of 1–2% turned the dimmer fully off instead of dimming.
- `switch` status requests ignored the configured bus `interface`.
- CEN+ "still held" was mapped onto the same event as the initial long press,
  producing repeated `pushbutton_long_press` events while a button was held; some
  rotation events fired with `event: null`.
- `manufacturer`/`sw_version` stored as 1-element lists produced a Home Assistant
  warning and would have failed setup entirely from HA 2026.12; fixed at the
  source and migrated for existing config entries (version 2).
- A dirty reload (stale flags instead of an ordered shutdown) could leave the
  platforms and command socket in an inconsistent state and leak sessions on the
  gateway across repeated reloads.
- Deprecated Home Assistant APIs closed before their removal: `via_device` →
  `via_device_id`, deprecated device-registry lookup helpers, missing
  `ClimateEntityFeature.TURN_ON`/`TURN_OFF` (climate `turn_on`/`turn_off`/`toggle`
  now work on HA ≥ 2025.1).
- The climate central unit could never be put in `auto` mode; an unusable
  `fan_mode` was advertised without any way to set it (`fan: true` is still
  accepted in YAML and only logs a warning).
- User-disabled entities could be silently re-enabled by the registry pruning
  logic after a couple of reloads; the gateway device and disabled entities are
  now always preserved.

### Changed

- **Availability**: every entity's `available` state now follows the real
  connection state of its gateway, published by the event session.
- **Instant-power keep-alive is now built in.** The integration arms and
  automatically renews the meter's instant-power reporting itself
  (`keepalive_minutes`, default 125 minutes, 5 minutes before expiry); a manual
  "resend `start_sending_instant_power` every 2 hours" automation is no longer
  necessary (harmless to keep running for a while as a safety net).
- **Discovery never rewrites `myhome.yaml` any more.** Suggestions for devices
  seen on the bus but not yet configured are written to `myhome_discovered.yaml`
  (next to your `myhome.yaml`) for you to review and copy in by hand.
- Logging: per-frame chatter (bus traffic, per-command acknowledgements) is now
  DEBUG instead of INFO; INFO is reserved for connection lifecycle events.
- `iot_class` corrected to `local_push`; `manifest.json` now declares the `OWNd`
  logger.
- Minimum supported Home Assistant version is now **2026.8.0** (needed for
  `via_device_id` and the device-registry lookup API used by the new pruning
  logic).
- Services are registered once (not once per config entry) and validate their
  input with proper schemas and translated error messages; a failed
  `send_message`/command now raises a visible error instead of failing silently.
- `start_sending_instant_power` now targets power sensor entities directly with
  `target:` (entity selector) instead of a MAC + WHERE pair.
- `energy:` as a top-level gateway key is folded into `sensor_defaults:` (both
  are still accepted; `sensor_defaults` wins on conflicting keys).

### Added

- `keepalive_minutes` (0-255, default 125, `0` disables it) — per-sensor or
  gateway-wide (`sensor_defaults:`) instant-power keep-alive interval.
- Time-based position tracking for basic (non-advanced) covers, using
  `shutter_run` (seconds) and `inverted`; `set_cover_position` is now supported
  on basic actuators, and position is restored across restarts.
- `lock_buttons: true` opt-in per light/switch/cover device (Point-to-Point
  WHERE only) to (re-)generate the Lock/Unlock configuration buttons.
- New CEN+ event value `pushbutton_long_press_repeat` (fired while a button
  stays held, distinct from the initial `pushbutton_long_press`) and rotation
  events `rotate_cw_slow`, `rotate_cw_fast`, `rotate_ccw_slow`, `rotate_ccw_fast`.
- Config entry migration (version 1 → 2).
- Full translation coverage (English, French, Italian, Dutch) for every new
  string, service and error message.
- Automated test suite (pytest + pytest-homeassistant-custom-component) and a
  `ruff` lint pass; see the README's Development section.

### Removed

- Automatic generation of Lock/Unlock buttons for every actuator (see Breaking
  changes above).
- Dead `device_handler.py` / `device_factory.py` modules and the unused
  OpenHAB-style device-type constants that only they imported.

## [0.1.1] - 2026-09-04

### Fixed

- Setup failure on Home Assistant Core 2026.9+: the new `probatio` schema engine
  compiles nested `Schema` instances directly and never called the overridden
  `__call__` of the device schemas, so every platform failed with `KeyError` and
  the config entry went to `setup_error`. Nested device schemas are now invoked
  through plain callables, which works on both `probatio` and `voluptuous`.

## [0.1.0] - 2026-02-22

Baseline release of this fork (branched from `anotherjulien/MyHOME` via
`artmakh/MyHOME`): configurable energy rate limiting (`min_delta_w`,
`min_interval_sec`, `suppress_log_interval_sec`) with global sensor defaults in
the YAML, quieter power-sensor logging, discovery refinements, and assorted Home Assistant
compatibility fixes.
