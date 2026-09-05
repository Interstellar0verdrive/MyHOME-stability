# Migrating from anotherjulien/MyHOME

This page is for people coming from
[anotherjulien/MyHOME](https://github.com/anotherjulien/MyHOME) or from the
[artmakh](https://github.com/artmakh/MyHOME) fork it was continued in.

The authoritative list of what changed is
[CHANGELOG.md](../CHANGELOG.md); this page reorganises it as a migration
checklist.

The domain is still `myhome`, the configuration file is still `myhome.yaml`, and
the OpenWebNet library is still `OWNd` (pinned to 0.7.49 since 0.3.1). This fork is a
continuation, not a rewrite of the configuration surface.

## Before you start

- **Minimum Home Assistant version is 2026.8.0.** Earlier versions will not run
  this integration. Check **Settings → About** first.
- Config entries are migrated from **version 1 to version 2** on the first load.
  The migration is automatic and needs no input, but it is one-way: you cannot
  downgrade to 0.1.x afterwards without removing and re-adding the gateway.

## What stays compatible

| Thing | Status |
|---|---|
| `myhome.yaml` file name and location | Unchanged (config directory, or the path set in the integration options). |
| The `gateway:` root block | Accepted. |
| A MAC address as the root key | Accepted. Any notation: `00:03:50:aa:bb:cc`, `00-03-50-AA-BB-CC`, `000350AABBCC`. |
| Several gateways in one file | Accepted, one root entry per gateway (a `gateway:` block may coexist with MAC root keys). |
| Platform sections `light`, `switch`, `cover`, `binary_sensor`, `sensor`, `climate` | Unchanged. |
| Free-choice YAML keys per device | Unchanged; they are used only in error messages. |
| Device options (`where`, `name`, `dimmable`, `advanced`, `shutter_run`, `inverted`, `class`, `icon`, `icon_on`, `manufacturer`, `model`, `interface`, `zone`, `heat`, `cool`, `standalone`, `central`, …) | Accepted. |
| `energy:` gateway block | Accepted as an alias of `sensor_defaults:`. |
| `refresh_period` / `refresh_period_sec` | Accepted as aliases of `min_interval_sec`. |
| `energy_min_delta_w`, `energy_min_interval_sec`, `energy_suppress_log_interval_sec`, `energy_info_log_interval_sec` | Accepted as legacy aliases. |
| CEN / CEN+ event names and data keys | `myhome_cen_event` and `myhome_cenplus_event` keep `object`, `pushbutton`, `event`, and the four original `pushbutton_*` values. |
| `myhome_message_event`, `myhome_general_*` / `myhome_area_*` / `myhome_group_*` events | Unchanged names. |
| Services `myhome.send_message`, `myhome.sync_time`, `myhome.start_discovery`, `myhome.stop_discovery` | Unchanged names and `gateway` field. |
| Entity unique ids | Unchanged patterns (see below), so `entity_id`s survive the upgrade. |

The unique id patterns the integration builds are, for gateway MAC `M` and a
device key `{who}-{where}` (or `{who}-{where}#4#{interface}`, or `{who}-{zone}`
for climate):

| Platform | Unique id |
|---|---|
| `light`, `switch`, `cover`, `climate` | `M-{who}-{where}` |
| `binary_sensor` | `M-{who}-{where}-{class}` |
| `sensor` (temperature, illuminance) | `M-{who}-{where}-{class}` |
| `sensor` (power meter) | `M-{who}-{where}-power`, `-daily-energy`, `-monthly-energy`, `-total-energy` |
| `button` (opt-in) | `M-{who}-{where}-disable` and `M-{who}-{where}-enable` |

If you want to be certain nothing moved, note down a few `entity_id`s from
**Developer tools → States** before upgrading and compare afterwards.

## What changed

### Validation is now strict, and errors block the setup

`myhome.yaml` is validated on every (re)load. A validation error shows on the
integration card with the offending key path, and the integration does not start
until it is fixed. Previously some of these were silent.

- **Duplicate WHERE is an error.** Two devices with the same WHO/WHERE
  (+ `interface`) used to have the second silently overwrite the first — one of
  your entities simply never existed. The message now names both YAML keys:

  ```
  Duplicate WHERE '81' (who 2): cover 'tapparella_camera_bambino' collides with
  cover 'tapparella_camera_aleksander_2' (both map to device '2-81').
  ```

  The one tolerated overlap is a `climate` zone plus a `sensor` of class
  `temperature` on the same zone.

- **`device_class` is a documented alias of `class`** on every platform. Both keys
  are accepted; giving both with *different* values is an error.

- **Unknown keys produce a WARNING with a "did you mean" hint** and are otherwise
  ignored, e.g. `unknown key 'dimable' in light.kitchen is ignored (did you mean
  'dimmable'?)`. Each key path is reported once. **Read your log after the first
  load**: typos that used to be silently swallowed now tell you they are being
  swallowed.

- **Quote every `where`.** Unquoted YAML numbers lose leading zeros (`where: 01`
  becomes `1`) and `0…` is read as octal. Ambiguous values are rejected with a
  message telling you exactly how to quote them.

- **A `sensor` must declare its class** (`power`, `energy`, `temperature` or
  `illuminance`); if `who` is also given it must match the class.

### Lock/Unlock buttons are opt-in — this one removes entities

They used to be generated for **every** light, switch and cover, including
General and Area addresses where a single press would disable the whole plant. On
upgrade, those button entities **disappear**.

To keep them for a specific device, add `lock_buttons: true` under it. They are
only created for Point-to-Point WHEREs.

```yaml
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      lock_buttons: true
```

Check your automations and dashboards for `button.*_lock` / `button.*_unlock`
entities before upgrading.

### Sensor friendly names no longer repeat the device name

A power sensor used to be called "Kitchen Oven Kitchen Oven Power"; it is now
"Kitchen Oven Power" (device name + entity name from the translation). The
`entity_id` is unchanged. Automations or dashboard cards that match on the old
**friendly name text** need updating; anything keyed on `entity_id` does not.

The affected names are `Power`, `Energy today`, `Energy this month`, `Energy`,
`Lock` and `Unlock`.

### Discovery no longer rewrites `myhome.yaml`

`myhome.start_discovery` used to edit your configuration file. It now writes
suggestions to **`myhome_discovered.yaml`**, in the same folder as your
`myhome.yaml`, for you to review and copy in by hand. A run stops itself after
60 seconds, or when you call `myhome.stop_discovery`; both flush what was
collected. Devices already present in `myhome.yaml` (matched on WHO/WHERE) are not
suggested again.

### There is an options flow

**Settings → Devices & services → MyHOME → Configure** now lets you change,
without removing the integration: address, port, password, the path of
`myhome.yaml`, the number of concurrent command sessions (1–10, default 1), and
*"Generate events in Home Assistant for each message received"* (the
`myhome_message_event` switch). Saving the options reloads the integration.

There is also a proper **reauth** flow: when the gateway rejects the stored
password at runtime, Home Assistant asks for the new one instead of failing
silently.

### `iot_class` is now `local_push`

The manifest declares `local_push` (it was wrong before) and lists `OWNd` under
`loggers`, so `logger:` blocks targeting `OWNd` behave as expected. This is
cosmetic for you, but it is what makes Home Assistant stop showing the
integration as a polling one.

### New CEN+ event value: `pushbutton_long_press_repeat`

"Still held" (WHAT 23) used to be mapped onto the same event as the initial long
press (WHAT 22), so holding a button produced a stream of `pushbutton_long_press`
events. Now:

- `pushbutton_long_press` fires **once**, when the hold starts;
- `pushbutton_long_press_repeat` fires repeatedly while the button stays held.

**If an automation of yours relied on the repeated `pushbutton_long_press`** (a
hold-to-dim, for instance), change its trigger to
`pushbutton_long_press_repeat`. See
[Recipes → Hold to dim](recipes.md#hold-to-dim-long-press-repeat).

Four rotation values were also added and no longer fire with `event: null`:
`rotate_cw_slow`, `rotate_cw_fast`, `rotate_ccw_slow`, `rotate_ccw_fast`.

### Other behaviour changes worth knowing

- **Entity `available` now means something.** It follows the real state of the
  gateway's event session. Expect entities to go `unavailable` during a gateway
  reboot and come back on their own, where they previously kept showing a stale
  state.
- **Instant power keep-alive is built in** (`keepalive_minutes`, default 125). A
  "re-send `start_sending_instant_power` every 2 hours" automation is no longer
  needed.
- **`myhome.start_sending_instant_power` now targets entities** with `target:`
  instead of taking a MAC + WHERE pair. Old calls need rewriting.
- **Per-frame logging moved from INFO to DEBUG.** If your log looked busy at INFO
  before, it will be quiet now; set `custom_components.myhome: debug` when you
  actually need the traffic.
- **Basic covers now track position.** `shutter_run`, `inverted`, `class` and
  `icon` were accepted by the old schema but never read by `cover.py`; they now
  do what they say, and `set_cover_position` works on basic actuators.
- **`fan: true` on a climate zone is accepted but ignored**, with a warning: the
  protocol layer has no fan-speed command.

## Step-by-step

1. **Back up.** Settings → System → Backups → *Create backup*. At minimum, copy
   `myhome.yaml` and note the entity ids you care about.
2. **Read your `myhome.yaml` for duplicates.** Any two devices with the same
   `where` (and the same `who`/`interface`) will now block the setup. Grep for
   repeated `where:` values before you upgrade; you may find, as the author did,
   that one of the two entities never existed in Home Assistant.
3. **Decide about Lock/Unlock buttons.** If you use them, add
   `lock_buttons: true` to the relevant devices now, so they come back on the
   first load instead of disappearing.
4. **Add this repository to HACS as a custom repository.** HACS → menu (⋮) →
   *Custom repositories* → `https://github.com/Interstellar0verdrive/MyHOME-stability`,
   type *Integration* → *Add*. Then search for **MyHome**, open it and
   *Download*.
5. **Remove the old folder if you installed it manually.** Delete
   `custom_components/myhome/` from the previous installation before extracting
   the new one. Do not merge the two — old modules left behind
   (`device_handler.py`, `device_factory.py`) were removed in this fork.
6. **Restart Home Assistant.**
7. **Check the config entry.** Settings → Devices & services → MyHOME. It should
   be *Loaded*. If it shows an error, the message names the key path in
   `myhome.yaml` that needs fixing; fix it and reload the entry.
8. **Read the log for warnings.** Filter on `myhome.yaml:` — every unknown key is
   reported once, with a suggestion:

   ```yaml
   logger:
     logs:
       custom_components.myhome: info
   ```

   Look for `unknown key '…' is ignored`, `Gateway … has no section in …`,
   `Ignoring unknown platform keys in …` and `Removing … : no longer in the
   configuration`.
9. **Check your entities.** Anything the pruning removed is listed at INFO
   (`Removing <entity_id> (<unique_id>): no longer in the configuration`).
   Entities you disabled in the UI are kept.
10. **Retire your workaround automations** — after a few days of watching, not on
    day one. The daily reload, the "command watchdog" that reloads when a state
    does not change, and the 2-hour `start_sending_instant_power` loop are all
    covered by the integration now. They are harmless to keep running in the
    meantime.

## Known limitations

These are real, current limitations. They are listed here so you find them before
they surprise you.

### Legacy preset-only dimmers are not supported

`OWNd` does not translate the old preset levels (WHAT 2–10) into a brightness
value: it reports them as a "preset" and leaves brightness unset. When the
integration sees such a frame it re-requests the real level with
`*#1*<where>*1##` (dimension 1). A dimmer that only speaks the preset WHATs and
does not answer dimension 1 will therefore show as on/off without a brightness.
Outgoing brightness is likewise sent as `*#1*<where>*#1*<level+100>*<speed>##`,
not as a preset WHAT.

### The `binary_sensor` unique id embeds the device class

A binary sensor's unique id is `{mac}-{who}-{where}-{class}`. Changing `class:` in
`myhome.yaml` therefore orphans the old registry entry, the pruning removes it,
and a **new entity with a new `entity_id`** appears. This is kept for backward
compatibility with existing installations. If you change the class of a binary
sensor, expect to fix up references to it. (A device class of `None`, which is the
default for WHO 9, renders as the literal `-None`.)

### Energy totals depend on the gateway

The daily/monthly/total energy entities carry whatever the gateway answers to
`*#18*<where>*54##`, `*#18*<where>*53##` and `*#18*<where>*51##`. Some gateways
acknowledge those requests and return no data — a MyHOMEServer1 with F520/F521
meters is the confirmed case — and the sensors then stay `unknown` forever. This
is why **Energy today** and **Energy this month** are created disabled by default.

If your gateway does not answer, derive energy from the power sensor with the
`integration` and `utility_meter` helpers instead — see
[Energy monitoring → Computing kWh when the gateway returns no totals](energy.md#computing-kwh-when-the-gateway-returns-no-totals).
See also [Gateway compatibility](gateway-compatibility.md) for what is verified
per model, and how to report yours.
