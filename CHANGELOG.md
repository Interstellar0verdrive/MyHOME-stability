# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- Covers, found by the 2026-09-07 code review (all reproduced with tests):
  - an advanced actuator's real position could be overwritten by the time-based
    estimate after a plain "opening"/"closing" frame; advanced covers now only track
    the direction from those frames, and they finally report `opening` / `closing`
    from their own status frames (states 11-14);
  - after a short timed run (a tilt target below ~17 %), the gateway's late copy of
    the movement command could start a phantom run to the end stop; the echo window
    now also covers our own stop commands, and only one contradicting frame per
    command is ignored, so a real keypad stop right after it is still honoured;
  - `set_cover_position` to the value a moving cover was passing through did nothing
    and the cover ran on; it now stops there;
  - a full `open_cover` / `close_cover` did not re-calibrate: the actuator's end-stop
    frame froze the stale estimate instead of snapping it to `0` / `100`. It snaps
    now, once three quarters of the expected run have elapsed; earlier stops are
    still honoured as real stops;
  - the last position is restored *before* the first status request instead of
    racing it;
  - `inverted` now also mirrors the level of an advanced actuator, so direction
    flags and position agree.
- Timing keys (`shutter_run`, `slat_time`, `opening_time`, `closing_time`) written
  on an `advanced` cover are now reported as ignored with a warning instead of
  silently dropped.
- Covers, second review round:
  - a keypad press within 1.5 s of a stop sent by Home Assistant is no longer
    discarded. Only a frame that can actually be the gateway echoing our own command
    is ignored: a `stopped` frame after a movement we commanded, or a copy of the
    movement our own stop interrupted. A movement in any other direction is honoured
    immediately, a press in the same direction is recovered by a status re-read about
    two seconds later, and a stop the gateway refused no longer arms the window at
    all. Without this a shutter driven from the wall could run fully open while Home
    Assistant reported it closed, until the next command from Home Assistant;
  - an advanced actuator no longer stays *Opening* / *Closing* for ever when its
    `stopped` frame is lost: the direction is dropped after the longest configured
    travel time plus 30 s and the actuator's status is re-read; the reported position
    is never estimated.
- Sensors, binary sensors and climate, found by the same review:
  - a platform section written as a YAML list or a scalar (`light: [...]`) is
    reported as a normal validation error with its key path instead of crashing the
    setup with a traceback;
  - `icon_on` given without `icon` now works on lights, switches and binary sensors
    (the entity's default icon is used while off);
  - `icon` was documented as a common key but ignored by sensors, binary sensors,
    climate zones and the scenario-control event entity, and `icon_on` by binary
    sensors; they now work (the Lock/Unlock buttons keep their fixed icons, and the
    validator knows `icon_on` on a binary sensor, so it no longer reports it as an
    unknown key);
  - `entity_name` on a `class: power` meter now renames the Power entity;
  - in a plant with a central unit, every nameless zone was called "Central unit";
    only the bare `#0` is, `#0#5` is "Zone 5" again;
  - a `climate` zone paired with a temperature `sensor` on the same zone lost the
    zone's name to the probe: the shared device keeps the climate name and the probe
    name becomes the sensor's `entity_name`;
  - an explicit `keepalive_minutes` equal to the built-in default (125) was overridden
    by the *Default instant-power keep-alive* option; the file value now always wins;
  - a WHO 1 illuminance sensor behind an F422 interface never received its interface
    and matched no reply;
  - a dimmer switched on with `transition:` kept a stale brightness;
  - the sensor refresh tasks are cancelled when the entity is removed, so a pending
    one cannot outlive a config entry reload;
  - the energy throttle resolves a sensor key whichever way its bus interface is
    spelled (`31#4#3` / `31#4#03`), like the frame dispatcher;
  - an unquoted 3- or 5-digit `where` (the shape sensor addresses take) is no longer
    blamed on lost leading zeros and octal; the message quotes the user's own value;
  - a WHO 9 auxiliary binary sensor claimed to be `off` from the moment it was
    created. The bus never answers a status request for an auxiliary channel, so
    there was nothing behind that `off`: the entity now starts `unknown` and
    restores its last known state across a restart or a reload.
- Device triggers, blueprints, flows and diagnostics:
  - a device trigger on a device that is not a scenario control (a light, a cover,
    the gateway) is now refused with a readable error; it used to be accepted and the
    automation showed as *on* without ever firing. The shipped blueprints' device
    picker now only offers scenario controls;
  - the per-device diagnostics download no longer contains the device's `name` /
    `entity_name`, the HMAC password frame is redacted like the other negotiation
    frames, and the configuration file is reported by name only, never with its
    directory;
  - the options flow no longer turns a gateway configured *without* a password into
    one with an empty password (which OWNd reports as "invalid password" instead of
    asking for one);
  - a gateway that never set the **Configuration file path** option showed no file
    name at all in the diagnostics download, and `config_file_is_default_location:
    false` — the opposite of the truth. Both now report the default: `myhome.yaml`,
    in the default location;
  - discovery: a thermoregulation zone is suggested as `climate` and a temperature
    probe of its own (WHERE above 99) as a `class: temperature` sensor. Before, the
    classifier tested an attribute OWNd does not have, so every probe became a zone;
    the first correction of this round then turned every zone into a probe. A probe
    wired as a zone's main sensor is indistinguishable from the zone on the bus and
    is reported as a zone; the first WHO 4 frame decides and is never revised;
  - discovery: the WHO 25 "scan" entry never left the machine (OWNd cannot build a
    general dry-contact status request, and there is none on the bus); the entry is
    gone and the docs now say that dry contacts and keypads are seen only when they
    emit a frame during the run;
  - discovery: scenario controls report `platform: event`, not `button`, in
    `myhome_device_discovered`, and a device family with no `myhome.yaml` section
    (alarm devices) reports `platform: null` instead of `binary_sensor`, which the
    schema rejects.
- Gateway, sessions and setup, found by the same review:
  - one unexpected exception inside the command sending loop used to kill the
    command path for the life of the process: the loop now survives it, the command
    is dropped and counted, and the worker backs off;
  - a command session whose `open()` was cancelled while the worker was being shut
    down leaked the socket instead of closing it — gateways only hold a handful of
    concurrent sessions;
  - a crash inside `OWNd`'s session negotiation escaped as an unhandled exception;
    it is now a reconnectable session error like every other connection failure;
  - a command lost to an authentication failure was not counted: it now shows up in
    the **Commands dropped** diagnostic entity like the other lost commands;
  - the rate-limited log keys are bounded, and a NACK line is keyed by WHO/WHERE
    instead of by the whole frame, so a busy plant could no longer grow that table
    one entry per distinct frame;
  - an area lighting frame (`*1*0*3##`) re-requested the status of the *decoded*
    area number instead of the WHERE the frame carried, so `*#1*10##` asked actuator
    A=1 PL=0 rather than area 10, and the lights of areas `00` and `100` did not
    follow a physical area button;
  - the idle watchdog no longer arms itself when its probe could not even be queued
    (a full or closed command queue): reconnecting the monitor cannot help, so it
    simply retries on the next poll;
  - a platform that refuses to unload is now logged as an error instead of passing
    unnoticed; the sockets are already closed at that point, so the entry has to be
    reloaded.
- Tests: service-call refusals are pinned to their own translation key (a wrong
  message could pass before), and the suite covers the gateway failure surface
  (refused commands, general/area/group WHO 2 frames, the complete CEN/CEN+ press
  table, the idle-probe window, the listening loop's catch-all, the reconnect
  backoff cap), the session error paths and discovery.

### Added

- CI runs `ruff` and `pytest` on every push and pull request
  (`.github/workflows/tests.yml`), with the rule set pinned in `ruff.toml`; the
  suite used to run only on a developer's machine.
- `strings.json` as the source of the translations.
- `requirements_test.txt` (the one dependency list CI and the development docs
  install), `scripts/release_notes.py` (the CHANGELOG section of a version,
  unwrapped for the GitHub release page) and a `.gitattributes` pinning LF line
  endings, so the CRLF-to-LF rewrite of `__init__.py` / `config_flow.py` cannot
  happen again file by file.

### Changed

- The *Probe window* option description now says what the watchdog does: the
  connection is rebuilt only when *neither* session answers the probe.
- **Binary sensors are named after their device** ("Window Contact", not "Window
  Contact Window"): they are now the main entity of their device like every other
  platform. Entity ids and history are unaffected; only the displayed name changes.
- Four configurations that used to load are now rejected with the key path of the
  offending device, because they could never work: `interface:` on a WHO 4/9/18/25
  sensor (their frames never carry it), a WHO 1 `binary_sensor` with a class other
  than `motion`, a `climate` zone with `heat: false` and `cool: false`, and a CEN
  `scenario_control` whose `where` is outside 1-2047.
- A CEN scenario control used to accept trigger types only CEN+ can fire
  (`rotate_cw_slow`, `pushbutton_long_press_repeat`); such a trigger now fails
  validation. It never fired; it used to fail quietly.
- A device trigger whose **button number** is outside the protocol's range (CEN+
  buttons are 1-32, CEN buttons are 0-31) is now refused when the automation loads,
  like a wrong event type. It used to validate and never fire.
- **The idle watchdog no longer reconnects a gateway that answered the probe.** It
  used to close and rebuild the event session whenever the probe produced nothing on
  the monitor within *Probe window* seconds. Some gateways answer on the command
  session without mirroring the reply onto the monitor, and those were reconnected
  every `idle watchdog + probe window` seconds for no reason: an acknowledged probe
  now re-arms the watchdog instead, and only a probe answered on *neither* session
  reconnects. The monitor socket itself is still guarded by TCP keepalive.
- **The Number of concurrent command sessions option is capped at 4** (gateways hold
  only a handful of concurrent sessions), and the options form now offers 1-4 rather
  than 1-10. An entry saved with more than 4 opens 4; a non-numeric value left by a
  hand-edited entry falls back to 1 with a warning instead of failing the setup.
- Discovery suggests a **WHO 9 auxiliary channel as a `binary_sensor`** with
  `who: "9"`, not as a `switch`. The switch platform only accepts `who: "1"`, so
  copying the old suggestion into `myhome.yaml` blocked the whole setup.
- The dead `invalid_port` and `gateway_vanished` translation keys were removed (no
  code path could set them), and so was an unload helper that could never cancel
  anything (the session close already does).

## [0.4.0] - 2026-09-07

Three additions: a two-phase travel model for covers, CEN/CEN+ scenario controls as
Home Assistant devices with UI-selectable triggers, and a bus event for wall
pushbuttons in dimmer mode. Nothing is renamed and no `entity_id` or `unique_id`
changes; the event-contract changes are additive (a new `mac` key on the CEN/CEN+ bus
events, one new event). A `myhome.yaml` written for 0.3.x keeps behaving exactly as it
did: the cover model and the scenario controls are opt-in through new keys.

### Fixed

- Timed cover targets (`set_cover_position`, tilt) were cancelled by the gateway:
  MyHOMEServer1 answers a movement command with a "stopped" frame immediately
  followed by the "opening"/"closing" one, and that stop was taken as the end of
  the run, so the shutter ran to the end stop. The stop echo arriving within 1.5 s
  of our own command is now ignored (one frame per command: a second stop inside the
  window, i.e. a keypad press, is honoured; keypad-started runs are unaffected).
  Found live on the first calibrated shutter.
- `myhome.send_message` crashed with an internal error on frames that OWNd's typed
  parser does not model, such as a CEN+ virtual press (`*25*21#1*#2##`, WHERE starting
  with `#`). Well-formed frames are now sent as generic commands; malformed ones
  raise a proper validation error. Found while testing the scenario controls.

### Added

- **Wall pushbutton events.** The gateway echoes what a physical light pushbutton
  sent (`*1*1000#WHAT*WHERE##`) right before the actuator answers; those frames were
  dropped. They are now republished as `myhome_light_pushbutton_event`
  (`mac`, `where`, `what`, `event`, `message`). The point is dimmer-mode pushbuttons
  wired to relays: a hold sends `dim_up`/`dim_down` about twice a second and nothing
  else on the bus reflects it, so this is the only way to turn such a button into a
  dimming remote for, say, a Zigbee bulb. Short presses give `on`/`off` next to the
  status the entity already follows. Found on a bedside pushbutton.
- **CEN / CEN+ scenario controls as devices, with device triggers and an event
  entity.** A wall keypad has no state, so until now its presses existed only as
  `myhome_cenplus_event` / `myhome_cen_event` bus events, usable from YAML and
  invisible everywhere else. Declaring the control under the new `scenario_control:`
  block in `myhome.yaml` now creates a **device** on the gateway carrying one
  **event entity** (`event.<name>_scenario_control`, state = timestamp of the last
  press, attributes `event_type`, `pushbutton`, `protocol`, `object`/`where` and
  `buttons`) and a set of **device triggers**, so "Button 2 held down on Living Room
  Keypad" can be picked in the automation editor instead of hand-written event
  triggers. Both CEN+ (`object`, buttons 1-32, including the long-press repeat and
  the four rotary events) and CEN (`where`, buttons 0-31) are supported; `buttons`
  decides which combinations the picker offers, never what reaches the bus. Controls
  that are *not* declared keep firing the bus events and create nothing, exactly as
  in 0.3.x.

  *The device-trigger module is ported from [fedem95/MyHOME](https://github.com/fedem95/MyHOME) by fedem95 (AGPL-3.0): the base-schema extension, the type/subtype split and the delegation to Home Assistant's own event trigger are theirs; the concept was also explored by [mantovanellimatteo/MyHOME](https://github.com/mantovanellimatteo/MyHOME). The event-entity model is ported from [adrael/MyHOME](https://github.com/adrael/MyHOME) by raphael (AGPL-3.0), whose `event.py` implements the same shape for a doorbell.*

  See [Configuration → Scenario control](docs/configuration.md#scenario-control-cen--cen)
  and [Recipes → Device triggers and blueprints](docs/recipes.md#device-triggers-and-blueprints).
- **`mac` in the `myhome_cenplus_event` / `myhome_cen_event` payloads.** Additive: the
  existing `object`, `pushbutton` and `event` keys are untouched, so automations
  written before 0.4.0 keep matching. It carries the normalised MAC of the gateway
  that saw the frame, so a multi-gateway plant can tell two controls with the same
  object number apart — which is what the device triggers filter on.
  *Suggested by fedem95, whose fork adds the same key.*
- **Two automation blueprints**, in `blueprints/automation/myhome/`:
  `cenplus_button_light.yaml` (short press toggles a light, long press turns it off)
  and `cenplus_button_cover.yaml` (hold up/down to open/close a cover, short press to
  stop). HACS does not install blueprints, so they are imported by URL — see
  [Recipes → Importing the blueprints](docs/recipes.md#importing-the-blueprints).

- **Two-phase travel model for basic covers (`slat_time`).** On most roller shutters
  the motor run is not all lift: from fully closed the first seconds only tilt the
  slats ("lamelle") open while the curtain stays on the floor, and when closing the
  motor keeps running for the same few seconds *after* the curtain has touched the
  floor, to close them again. The linear 0-100 estimate therefore reported "5 %" with
  the curtain still on the floor, and *set position 50 %* from closed ended around
  55-60 %. Declaring `slat_time` (seconds, default `0` = previous behaviour) splits
  every run into a **slat phase** and a **curtain phase**:
  - `current_position` now describes the curtain only — `0` = curtain on the floor
    whatever the slats do, `100` = fully open;
  - `current_tilt_position` describes the slats — `0` = closed, `100` = open — and the
    cover is `closed` only when both are `0`;
  - the tilt services (`cover.open_cover_tilt`, `cover.close_cover_tilt`,
    `cover.set_cover_tilt_position`, `cover.stop_cover_tilt`) appear on covers with a
    `slat_time`, which makes "closed with the slats open" a single service call; above
    the floor the slats are always open, so tilt commands are ignored there;
  - `cover.set_cover_position` computes the run through both phases (from closed,
    5 % costs `slat_time + 0.05 × (opening_time - slat_time)` seconds), and movements
    started from a physical keypad are tracked through the same model.

  See
  [Configuration → The two-phase travel model](docs/configuration.md#the-two-phase-travel-model-slat_time)
  and [Recipes → Covers](docs/recipes.md#covers).
- **Separate `opening_time` and `closing_time` for basic covers.** Both default to
  `shutter_run`, which stays the one value most installations need; set them when the
  motor is measurably slower in one direction. *The idea of separate up/down travel
  times comes from [andrea-parisi/MyHOME](https://github.com/andrea-parisi/MyHOME).*
- Basic covers expose `Slat time`, `Opening time` and `Closing time` as extra state
  attributes when those keys are in use, next to the existing `Shutter run`.

### Changed

- `cover.set_cover_position` with a target of `0` or `100` now runs the cover into its
  end stop instead of stopping it with a timer at the computed moment. The end stop is
  what re-calibrates a time-based estimate, and the stop command was redundant there.
- The estimated **tilt** is persisted next to the position, so "closed with the slats
  open" survives a restart or a reload.

## [0.3.1] - 2026-09-05

Hotfix release. Four bugs, no new features, no configuration change required. No
`entity_id`, `unique_id` or event contract is touched — entities behind an F422 bus
interface keep the exact ids they had in 0.3.0.

### Fixed

- **Devices behind an F422 local bus interface never received state updates.** The
  `OWNd` version we shipped (0.7.48) compared an integer WHO against a list of
  strings in `OWNMessage.interface`, so the property always returned `None` and the
  `#4#<interface>` part never reached the entity address: a frame such as
  `*1*1*11#4#3##` was reported as plain `1-11` and applied to the main-bus device
  with the same WHERE, if one existed. The dependency is now pinned to
  **`OWNd==0.7.49`**, which fixes this upstream (it also stops a `TypeError` on
  thermostat local-offset values 6/7/8 and makes session shutdown robust against a
  connection that was never opened). *Upstream `OWNd` fix; independently found by
  GreenGrassBlueOcean and pinned by Dav41K9 and rdr-66.*
- **Bus interface numbers were zero padded on the wire.** Every command the
  integration sent carried `11#4#03` while the bus writes `11#4#3`, so the address in
  our commands did not match the address in the gateway's replies — a mismatch that
  became visible the moment the `OWNd` fix above started reporting interfaces at all.
  `interface` is now accepted as an integer or as a 1- or 2-digit string (`3`, `"3"`,
  `"03"`) and always normalised to the unpadded bus form. **Entity ids are
  preserved:** the internal device key, and with it every `unique_id`, keeps the
  padded spelling (`1-11#4#03`), and incoming frames are matched against both
  spellings. See
  [Configuration → Local bus interfaces](docs/configuration.md#local-bus-interfaces-interface).
  *Problem identified by carferrer.*
- **The central heating unit de-synchronised zone 1.** `OWNd` rewrites a heating
  `zone 0` frame to the zone in the first WHERE parameter, so `*#4*0#1*20*1##` — the
  central unit's actuator — was reported as entity `4-1` and drove zone 1's climate
  entity with the central unit's state. Such frames are now routed to the
  central-unit entity (`4-#0`). *Fix contributed by jacopo-j, via
  [michnovka's fork](https://github.com/michnovka/HomeAssistant-MyHOME).*
- **`myhome.sync_time` blocked the event loop.** Building the command calls
  `pytz.timezone()`, which reads the timezone database from disk; it now runs in an
  executor, so Home Assistant no longer logs a blocking-call warning when the service
  is called. *Found by sxpert.*

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

[Unreleased]: https://github.com/Interstellar0verdrive/MyHOME-stability/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/Interstellar0verdrive/MyHOME-stability/releases/tag/v0.4.0
[0.3.1]: https://github.com/Interstellar0verdrive/MyHOME-stability/releases/tag/v0.3.1
[0.3.0]: https://github.com/Interstellar0verdrive/MyHOME-stability/releases/tag/v0.3.0
[0.2.1]: https://github.com/Interstellar0verdrive/MyHOME-stability/releases/tag/v0.2.1
[0.2.0]: https://github.com/Interstellar0verdrive/MyHOME-stability/releases/tag/v0.2.0
[0.1.1]: https://github.com/Interstellar0verdrive/MyHOME-stability/releases/tag/v0.1.1
[0.1.0]: https://github.com/Interstellar0verdrive/MyHOME-stability/releases/tag/v0.1.0
