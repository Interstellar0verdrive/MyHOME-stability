# Configuration reference

How to add a gateway from the UI, and the full `myhome.yaml` schema: file
location, root formats, every parameter per platform, Lock/Unlock buttons,
multiple gateways, custom icons/device classes, and what the validator's error
messages mean.

See the [main README](../README.md) for installation and a minimal example, and
[Recipes](recipes.md) for copy-paste automations and configuration built on top
of this schema.

## Contents

- [Gateway setup](#gateway-setup)
  - [Automatic discovery](#automatic-discovery-recommended)
  - [Manual gateway configuration](#manual-gateway-configuration)
  - [Reauthentication](#reauthentication)
  - [Options](#options)
  - [Repairs](#repairs)
- [The `myhome.yaml` file](#the-myhomeyaml-file)
- [Common parameters (all platforms)](#common-parameters-all-platforms)
  - [Local bus interfaces (`interface`)](#local-bus-interfaces-interface)
- [Light](#light)
- [Switch](#switch)
- [Cover](#cover)
  - [The two-phase travel model (`slat_time`)](#the-two-phase-travel-model-slat_time)
  - [Calibrating a cover](#calibrating-a-cover)
- [Binary sensor](#binary-sensor)
- [Climate](#climate)
- [Sensor](#sensor)
- [Scenario control (CEN / CEN+)](#scenario-control-cen--cen)
- [Lock/Unlock buttons](#lockunlock-buttons)
- [Multiple gateways](#multiple-gateways)
- [Custom icons and device classes](#custom-icons-and-device-classes)
- [Validation errors](#validation-errors)

## Gateway setup

### Automatic discovery (recommended)

Most MyHOME gateways support automatic discovery via SSDP:

1. Go to **Settings → Devices & services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"MyHOME"**
4. Select your discovered gateway
5. Enter the gateway password if required
6. Click **"Submit"**

### Manual gateway configuration

If your gateway isn't auto-discovered:

1. Go to **Settings → Devices & services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"MyHOME"**
4. Select **"Configure manually"**
5. Enter gateway details:
   - **Host**: Gateway IP address
   - **Port**: Gateway port (default: 20000)
   - **Password**: Gateway password (if required)
   - **Name**: Friendly name for the gateway

### Reauthentication

If the gateway rejects the stored password (for example after it was changed on
the device), Home Assistant raises a reauth flow: open it from the integration
card and enter the current OpenWebNet password.

### Options

From **Settings → Devices & services → MyHOME → Configure** you can change,
without removing the integration:

- IP address/hostname, port, password
- **Configuration file path** — where `myhome.yaml` (and `myhome_discovered.yaml`)
  live, if not the default Home Assistant config directory
- **Number of concurrent command sessions**
- **Generate events in Home Assistant for each message received** — toggles
  `myhome_message_event` (see [Services and events](services-and-events.md))

Saving options reloads the integration.

#### Session tunables

Since 0.3.0 the timings that used to be hard-coded are editable in the same form.
**The defaults are exactly the values 0.2.x used internally, so leaving them alone
changes nothing** — only touch them if you are working around a specific gateway
misbehaviour, and change one at a time.

| Option | Default | Range | What it does |
| --- | --- | --- | --- |
| Idle watchdog | 300 s | 60–3600 | No frame received on the monitor session for this long: a harmless status request is sent through the command session to check the gateway is still alive. Lower it on a gateway that dies silently; raise it on a very quiet plant that produces false probes. |
| Probe window | 30 s | 5–300 | The probe was sent and *still* nothing arrived on the monitor session: the event session is closed and reconnected (backoff 1, 2, 4 … 60 s). |
| Command timeout | 10 s | 2–60 | How long a single command may take to be written and acknowledged. On timeout it is retried once on a fresh session, then dropped with a warning. Raise it on a slow gateway that NACKs under load. |
| Command queue TTL | 60 s | 10–600 | Commands still queued after this long are dropped instead of being sent late (a light that switches on two minutes after the button press is worse than one that does not). |
| Default instant-power keep-alive | 125 min | 0–255 | The keep-alive asked of the energy meters for power sensors that do not set `keepalive_minutes` themselves in `myhome.yaml`. `0` disables it. A per-sensor value in the file always wins. See [Energy monitoring](energy.md). |

A [diagnostics download](troubleshooting.md#diagnostics-download) always reports the
values actually in effect, under `effective_options`.

### Repairs

The integration reports configuration problems as Home Assistant **repair issues**
(*Settings → System → Repairs*) instead of leaving them in the log:

| Issue | Severity | Meaning |
| --- | --- | --- |
| MyHOME configuration file is invalid | Error | `myhome.yaml` could not be read, parsed or validated. The issue carries the file path and the exact validator message; no device is created until it is fixed. |
| Unknown keys in the MyHOME configuration file | Warning | The file contains keys the integration does not know. They are ignored (never fatal, for backward compatibility) and listed with a "did you mean" hint. Dismissable if the keys are intentional. |
| No devices configured for this MyHOME gateway | Warning | The gateway's MAC address has no section in the file — usually a typo in the MAC, or the section of a different gateway. |

Each issue is cleared automatically as soon as a later load no longer hits its cause
(fix the file, then reload the integration).

## The `myhome.yaml` file

Devices are declared in `myhome.yaml` (in your Home Assistant config folder, or
the path set in the integration options). The file is validated when the
integration loads; a validation error is shown in **Settings → Devices &
services** with the offending key path, and the integration does not start until
it is fixed.

Two root styles are accepted, and they can be mixed (one entry per gateway):

- **`gateway:` block** (the style written by auto-discovery, recommended):
  ```yaml
  gateway:
    mac: "00:03:50:AA:BB:CC"
    light:
      kitchen_light:
        where: "15"
        name: "Kitchen Light"
  ```
- **MAC address as root key** (legacy, and the way to configure several gateways):
  ```yaml
  "00:03:50:AA:BB:CC":
    light:
      kitchen_light:
        where: "15"
        name: "Kitchen Light"
  ```
  An inner `mac:` is optional here; if present it must match the root key. Any MAC notation is accepted (`00:03:50:aa:bb:cc`, `00-03-50-AA-BB-CC`, `000350AABBCC`).

Under the gateway, each platform section (`light`, `switch`, `cover`, `binary_sensor`, `sensor`, `climate`, `scenario_control`) maps a **YAML key of your choice** (used only in error messages) to a device. Sections may be left empty.

Rules worth knowing:

- **Quote every `where`** (`where: "01"`, not `where: 01`). YAML reads unquoted numbers with leading zeros as decimal/octal integers and the address is lost; the validator rejects ambiguous values with a message telling you to quote them.
- **Each WHO/WHERE may appear only once per gateway**, across all platforms (a duplicate `where` used to silently drop one of the two devices). The error names both YAML keys. The only tolerated overlap is a `climate` zone plus a `sensor` of class `temperature` on the same zone.
- **Unknown keys do not break the configuration**: they are kept and reported once at WARNING level with a "did you mean" hint (e.g. `dimable` → `dimmable`). Check the log after editing the file.
- `device_class` is accepted as an alias of `class` on every platform (they must not both be given with different values).

## Common parameters (all platforms)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `where` | string | Yes | – | OpenWebNet WHERE address (see the platform notes for the accepted forms). Climate uses `zone` instead. |
| `name` | string | Yes | – | Device name in Home Assistant (optional for climate). |
| `entity_name` | string | No | device name | Name of the main entity when it must differ from the device name. On a `class: power` meter it renames the **Power** entity; the daily/monthly/total energy entities of a `power` or `energy` meter keep their own translated names ("Energy today", "Energy this month", "Energy"). |
| `icon` | string | No | – | Icon of the main entity (`mdi:...` or any registered icon set). |
| `icon_on` | string | No | – | Icon used while the entity is on (light, switch). |
| `manufacturer` | string | No | `BTicino S.p.A.` | Cosmetic, shown in the device page. |
| `model` | string | No | – | Cosmetic, shown in the device page. |
| `who` | string | No | per platform | OpenWebNet WHO; only needed for sensors/binary sensors that support several. |
| `interface` | string or int | No | – | Local bus interface (F422) of a device behind a bus interface (light, switch, cover, binary sensor, sensor; not climate, which is addressed by zone, and not `scenario_control`). Accepted as an integer or as a 1-2 digit string: `3`, `"3"` and `"03"` all mean the same interface. |
| `class` / `device_class` | string | No | per platform | Home Assistant device class (see the platform tables). |

Accepted actuator WHERE forms (light, switch, cover): General `"0"`, Area `"00"`, `"1"`..`"10"`, Group `"#1"`..`"#255"`, Point-to-Point 2 digits (`"15"`, A=1 PL=5) or 4 digits (`"0115"`, A=01 PL=15). Sensors and binary sensors accept any string of digits (energy meters are usually `"51"`..`"5N"`). Climate is different: its `zone` (and its `where` alias) accepts only `"#0"` for the central unit, `"1"`..`"99"` for a zone, or `"#0#<zone>"` for a zone driven through the central unit.

### Local bus interfaces (`interface`)

A device behind an F422 bus interface is addressed on the bus as
`<where>#4#<interface>` — for example WHERE `11` on interface 3 is `11#4#3`.

- **Accepted forms**: an integer `0`..`15` or a string of 1 or 2 digits
  (`3`, `"3"`, `"03"`). Anything else is a configuration error.
- **Stored unpadded**: whatever you write, the value is normalised to the form the
  bus uses (`"3"`), which is also the form every command the integration sends
  carries. This changed in **0.3.1**: before it, commands went out zero padded
  (`11#4#03`) while the bus answers unpadded.
- **Entity identity is unchanged**: the internal device key, and therefore the
  `unique_id` of every entity behind a bus interface, keeps the interface zero
  padded (`1-11#4#03`). Upgrading to 0.3.1 does **not** rename your entities or
  lose their history.
- Incoming frames are matched against both spellings, so a gateway that reports
  `11#4#3` and a configuration written `interface: "03"` resolve to the same
  entity.

> Devices behind a bus interface received **no state updates at all** before
> 0.3.1: the `OWNd` version we shipped never extracted the interface from the
> frame, so their updates were applied to a main-bus device with the same WHERE,
> if one existed. Fixed by `OWNd` 0.7.49 plus the normalisation above.

## Light

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dimmable` | boolean | `false` | Enable brightness control. |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

## Switch

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class` | `switch` \| `outlet` | `switch` | Device class. |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

## Cover

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `advanced` | boolean | `false` | Advanced actuator reporting its real position (position control from the device). |
| `shutter_run` | number (s) | `20` | Full travel time in seconds, at least `1`. Basic actuators use it to estimate the position (`0` = curtain down, `100` = fully open; with `slat_time`, `0` means the curtain rests on the floor, see the two-phase model below), derive open/closed and support *set position* by timed stop. Ignored on `advanced` actuators. |
| `slat_time` | number (s) | `0` | Seconds of the run that only open/close the slats ("lamelle"), without moving the curtain. `0` disables the two-phase model. |
| `opening_time` | number (s) | = `shutter_run` | Full **upward** run, when it differs from the downward one. At least `1`. |
| `closing_time` | number (s) | = `shutter_run` | Full **downward** run, when it differs from the upward one. At least `1`. |
| `inverted` | boolean | `false` | The actuator is wired the other way round: `open_cover` sends *lower*, a bus "raising" frame is read as closing and an advanced actuator's reported level is mirrored. Home Assistant's own convention is unchanged: position `0` is still closed, `100` still open. |
| `class` | cover device class | `shutter` | Any Home Assistant cover class (`shutter`, `blind`, `awning`, `garage`, ...). |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

`slat_time` must leave at least one second of curtain travel in both directions
(`slat_time < min(opening_time, closing_time) - 1`), otherwise the configuration is
rejected with the name of the offending cover.

### The two-phase travel model (`slat_time`)

On most roller shutters the motor run is not all lift. Starting from fully closed,
the first seconds only tilt the slats open while the curtain stays on the floor; and
when closing, the motor keeps running for the same few seconds *after* the curtain
has touched the floor, to close them again. A single linear 0-100 model therefore
reports "5 %" while the curtain is still on the floor, and *set position 50 %* from
closed ends up around 55-60 %.

With `slat_time` set, the integration splits every run in two phases:

| Phase | Duration | Reported as |
|-------|----------|-------------|
| Slats ("lamelle") | `slat_time` | `current_tilt_position` — 0 = slats closed, 100 = slats open |
| Curtain | `opening_time - slat_time` (up) / `closing_time - slat_time` (down) | `current_position` — 0 = curtain on the floor, 100 = fully open |

Consequences, all of them deliberate:

- `current_position: 0` means **the curtain rests on the floor**, whatever the slats
  are doing. The entity is `closed` only when the curtain is down **and** the slats
  are closed (`current_tilt_position: 0`); with the curtain down and the slats open
  it is `open`.
- Above the floor the slats are necessarily open, so `current_tilt_position` is
  pinned to `100` and the tilt services are ignored (with a DEBUG log line).
- The tilt services (`cover.open_cover_tilt`, `cover.close_cover_tilt`,
  `cover.set_cover_tilt_position`, `cover.stop_cover_tilt`) are only offered when
  `slat_time` is greater than `0`.
- `cover.set_cover_position` computes the run through **both** phases: from fully
  closed, position 5 % costs `slat_time + 0.05 × (opening_time - slat_time)` seconds.
- `cover.open_cover` and `cover.close_cover` still run into the end stop, which is
  what re-calibrates the estimate: a "stopped" frame that arrives during a full run
  commanded from Home Assistant, once at least three quarters of the expected run
  have elapsed, is read as the physical end stop and the estimate snaps to `0` /
  `100`. Earlier stops are taken for what they most likely are, somebody pressing
  *stop*, and freeze the estimate where it is. `set_cover_position` with `0` or
  `100` uses the same full run instead of stopping by timer.
- Movements started from a physical keypad (or by a scenario) are tracked through the
  very same model, from the `opening` / `closing` / `stopped` frames on the bus.
- `slat_time: 0` (the default) is exactly the 0.3.x linear behaviour, tilt included:
  no tilt feature, no extra attribute.

### Calibrating a cover

1. Close the cover completely (`cover.close_cover`) and let it stop by itself.
2. Start a stopwatch, command `cover.open_cover` and note two moments:
   - the instant the **bottom edge leaves the floor** → that is `slat_time`
     (typically 2-4 s);
   - the instant the cover **stops at the top** → that is `shutter_run` (the full
     upward run).
3. Time the way back down (`cover.close_cover`, until the motor stops by itself). If
   it differs from the upward run by more than a second or so, set `opening_time` and
   `closing_time` instead of a single `shutter_run`; otherwise `shutter_run` alone is
   enough.
4. Reload the integration and check `set_cover_position: 50`: consistent overshoot
   means the times are too large, stopping short means too small.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      shutter_run: 30      # full run, both directions
      slat_time: 3         # the first/last 3 s only move the slats
    bedroom_shutter:
      where: "82"
      name: "Bedroom Shutter"
      slat_time: 3
      opening_time: 32     # this motor is slower going up
      closing_time: 28
```

The loaded values are exposed on basic covers as the `Shutter run` attribute, plus
`Slat time`, `Opening time` and `Closing time` when they are actually in use.

See [Recipes → Covers](recipes.md#covers) for tuning the travel times,
`set_cover_position` behaviour, "closed with the slats open" and `inverted` wiring.

## Binary sensor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `who` | `"25"` \| `"1"` \| `"9"` | `"25"` | `25` dry contact / alarm zone, `1` motion sensor (lighting bus), `9` auxiliary. |
| `class` | binary sensor device class | by WHO | Default `opening` for WHO 25, `motion` for WHO 1, none for WHO 9. |
| `inverted` | boolean | `false` | Invert the reported state. |

Notes:

- A binary sensor is the **main entity** of its device, like a light or a cover:
  its friendly name is the device `name` (or `entity_name` when set), with no
  device-class word appended. Entity ids are unchanged — only the friendly name is.
- **WHO 1 supports `class: motion` only.** A WHO 1 binary sensor declared with any
  other class is a configuration error: the load stops with the key path of the
  offending device and a repair issue in *Settings → System → Repairs*. Motion
  sensors live on the lighting bus and are the only WHO 1 input this platform
  models; for a dry contact use WHO 25.

## Climate

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `zone` | string | `"#0"` | Thermo zone `"1"`..`"99"`, or `"#0"` for the central unit. `where` is accepted as an alias. |
| `name` | string | `Zone N` / `Central unit` | Optional. |
| `heat` | boolean | `true` | Heating support. |
| `cool` | boolean | `false` | Cooling support. |
| `fan` | boolean | `false` | Fan support. |
| `standalone` | boolean | `false` | Standalone thermostat (no central unit). |
| `central` | boolean | `false` | Zone driven through the central unit (`#0#N` addressing). |

## Sensor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class` | `power` \| `energy` \| `temperature` \| `illuminance` | **required** | Sensor type. `power` and `energy` are both WHO 18 meters: `power` creates the Power entity plus the three energy totalisers; `energy` creates the three totalisers only (Energy today / this month are disabled by default) and never arms the instant-power stream, so the `keepalive_minutes` and filter keys have no effect on it. `temperature` is WHO 4 (WHERE = zone), `illuminance` WHO 1. |
| `who` | string | from `class` | Only needed to override the WHO implied by the class (must match). |
| `keepalive_minutes` | integer 0-255 | `125` | Power meters only: the integration asks the meter to push instant power for this many minutes and renews the request by itself. `0` disables the automatic keep-alive. |
| `min_delta_w`, `min_interval_sec`, `suppress_log_interval_sec`, `info_log_interval_sec` | number | see [Energy monitoring](energy.md) | Per-sensor overrides of the power filtering defaults. |
| aliases | – | – | `refresh_period` and `refresh_period_sec` are accepted for `min_interval_sec`, and `energy_min_delta_w` / `energy_min_interval_sec` / `energy_suppress_log_interval_sec` / `energy_info_log_interval_sec` for their canonical counterparts. The canonical key wins if both are given. See [Energy monitoring](energy.md#sensor_defaults). |

Units are fixed by the class (W, Wh, °C, lx). Energy filtering, totals and
`keepalive_minutes` are covered in full in [Energy monitoring](energy.md).

## Scenario control (CEN / CEN+)

A CEN or CEN+ scenario control is a wall keypad: it commands the bus directly and
never reports a state, so Home Assistant only ever learns that a button *was*
pressed. Its presses have always been on the Home Assistant event bus as
`myhome_cenplus_event` / `myhome_cen_event` (see
[Services and events](services-and-events.md#cen-keypad-events)) and nothing about
that changed. Declaring the control under `scenario_control:` adds two things on
top, since **0.4.0**:

- a **device** with one **event entity**, so the last press is visible in the state
  machine and in history (`event.<name>_scenario_control`);
- **device triggers**, so "Button 2 held down on Living Room Keypad" can be picked
  from the automation editor instead of hand-written event triggers.

Controls you do not declare keep working exactly as before, firing the bus events
and creating no entity.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  scenario_control:
    keypad_living_room:
      object: 25              # CEN+ object number
      name: "Living Room Keypad"
      buttons: [1, 2, 3, 4]

    keypad_hall:
      protocol: cen
      where: "51"             # CEN address
      name: "Hall Keypad"
      buttons: [1, 2]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | – | Device name in Home Assistant. |
| `protocol` | `cen_plus` \| `cen` | No | `cen_plus` | Which of the two protocols the control speaks. |
| `object` | integer 1-2047 | Yes for `cen_plus` | – | CEN+ object number: the frame's WHERE without its leading `#` (WHERE `#25` → `object: 25`), i.e. the number the bus event reports as `object`. Not allowed for `cen`. |
| `where` | string of digits | Yes for `cen` | – | CEN address, as it appears in the `*15*…*<where>##` frame. Not allowed for `cen_plus`. |
| `buttons` | list of integers | No | `[1, 2, 3, 4]` | Which pushbuttons the automation editor should offer. CEN+ buttons are `1`-`32`, CEN buttons are `0`-`31`. |
| `entity_name`, `icon`, `manufacturer`, `model` | string | No | see below | The common cosmetic keys; `model` defaults to `CEN+ scenario control` / `CEN scenario control`. |

Notes:

- `buttons` is **not a filter**: a press on a button you did not list still fires
  the bus event and still updates the event entity. It only decides which
  combinations the trigger picker shows, so a 4-button keypad does not produce a
  32-entry dropdown.
- The device key is `cenplus-<object>` / `cen-<where>`, so a CEN control and a CEN+
  control may carry the same number without colliding. Declaring the same address
  twice is a validation error, as for any other platform.
- A CEN address is normalised to its unpadded form (`"051"` and `"51"` are the same
  control), because that is how the bus writes it.
- The event entity's `event_types` are exactly the event names of the protocol —
  see the [event tables](services-and-events.md#cen-keypad-events). CEN+ adds the
  long-press repeat and the four rotary events; CEN has the release after a short
  press instead. Beware that the four CEN names describe different gestures from
  the CEN+ ones: on CEN, `pushbutton_short_press` fires at the start of *every*
  press, long ones included, and `pushbutton_long_press` repeats while the button
  is held. Use `pushbutton_short_release` for "the user tapped the button" — see
  [CEN keypad events](services-and-events.md#cen-keypad-events-1).
- `interface:` is **not supported** for scenario controls. A CEN control is
  identified by its WHERE alone, so a CEN keypad on an F422 local bus and one on
  the main bus with the same WHERE are indistinguishable; declare only one of them.

See [Recipes → CEN+ keypads](recipes.md#cen-keypads) for automations, blueprints
and the device-trigger UI.

## Lock/Unlock buttons

Lights, switches and covers with `lock_buttons: true` get two configuration buttons (**Lock** / **Unlock**) that disable/enable the actuator on the bus (`*14*...`). They are only generated for Point-to-Point WHEREs: locking a General or Area WHERE would disable every actuator of the plant. Buttons are off by default; existing installations that relied on the automatically generated buttons must opt in per device.

See [Recipes → Lock/Unlock buttons](recipes.md#lockunlock-buttons) for a full example and an automation built on it.

## Multiple gateways

Use the MAC address of each gateway as the root key (a `gateway:` block may coexist with MAC root keys; every MAC must be unique):

```yaml
# First gateway
"00:03:50:AA:BB:CC":
  light:
    kitchen_light:
      where: "15"
      name: "Kitchen Light"

# Second gateway
"00:03:50:DD:EE:FF":
  cover:
    garage_door:
      where: "25"
      name: "Garage Door"
      class: garage
```

Each gateway also needs its own config entry (discovered or manual) with the same MAC. See [Recipes → Several gateways](recipes.md#several-gateways) for the service-call syntax once more than one gateway is loaded.

## Custom icons and device classes

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  light:
    accent_lighting:
      where: "45"
      name: "Accent Lighting"
      dimmable: true
      icon: "mdi:led-strip-variant"
      icon_on: "mdi:led-strip-variant"

  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      class: shutter
      shutter_run: 30
      icon: "mdi:window-shutter"
      lock_buttons: true

  binary_sensor:
    window_sensor:
      where: "301"
      name: "Living Room Window"
      class: window          # `device_class: window` is accepted too
      icon: "mdi:window-open"
```

## Validation errors

`myhome.yaml` is validated on every (re)load. Errors block the setup and are shown in the integration card with the key path (`gateway.cover.<key>.where`); warnings only appear in the log. Typical messages:

- **`required key not provided`**: `where` and `name` are mandatory (climate: `zone`/`name` optional).
- **`Invalid <WHERE>`** / **`quote it`**: the address is not a valid OpenWebNet WHERE, or an unquoted number lost its leading zero.
- **`Duplicate WHERE 'x' (who N): cover 'a' collides with cover 'b'`**: the same device is declared twice; fix the address or remove one of the two entries (both YAML keys are named).
- **`sensor 'x' is missing the required sensor class`**: add `class: power|energy|temperature|illuminance`.
- **a WHO 1 `binary_sensor` with a `class` other than `motion`**: WHO 1 inputs are modelled as motion sensors only. Drop the class, or move the device to `who: "25"` if it is a dry contact.
- **`scenario_control 'x' is missing the required 'object'`** / **`a CEN control is addressed by 'where', not by 'object'`**: a CEN+ control needs `object`, a CEN control needs `where`; never both.
- **`scenario_control 'x': pushbutton N is out of range for protocol …`**: CEN+ buttons are 1-32, CEN buttons are 0-31.
- **`gateway 'x' needs a 'mac'`** / **`configured twice`**: every root entry needs a MAC (as `mac:` or as the root key) and each MAC may appear once.
- **`unknown key 'dimable' in light.x is ignored (did you mean 'dimmable'?)`** (WARNING): a typo or an unsupported key; the device is still created without it.

See [Troubleshooting → Configuration issues](troubleshooting.md#configuration-issues) if the integration will not load after an edit.
