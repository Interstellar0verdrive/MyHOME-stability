# MyHOME (Stability) — BTicino/Legrand MyHOME for Home Assistant

A custom integration for **BTicino / Legrand MyHOME** (OpenWebNet) installations,
talking to the gateway (MyHOMEServer1, F454/F455, MH200N/MH202, ...) through the
[`OWNd`](https://github.com/anotherjulien/OWNd) library.

It is a fork of [anotherjulien/MyHOME](https://github.com/anotherjulien/MyHOME)
(via the `artmakh` fork), the integration that made MyHOME usable in Home Assistant
in the first place and that this project owes everything to. The original is no
longer being updated, so this fork carries it forward on a best-effort basis with
one goal: **an integration that stays up and keeps working with current Home
Assistant releases** — sessions that detect a dead connection and reconnect on
their own, commands that are never silently dropped, strict configuration
validation, and closed deprecations.

- Current release: **0.2.1** — see [CHANGELOG.md](CHANGELOG.md)
- Requires **Home Assistant 2026.8.0 or newer**
- Devices are declared in a YAML file (`myhome.yaml`); the gateway is added from the UI

## Contents

- [About this project](#about-this-project)
- [What's new in 0.2.x / Upgrading](#whats-new-in-02x--upgrading)
- [Features](#features)
- [Supported devices](#supported-devices)
- [Installation](#installation)
- [Gateway setup](#gateway-setup)
- [Device configuration (`myhome.yaml`)](#device-configuration-myhomeyaml)
- [Services](#services)
- [Events](#events)
- [Energy monitoring](#energy-monitoring)
- [Discovery](#discovery)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Support & contributing](#support--contributing)
- [Acknowledgments](#acknowledgments)
- [License](#license)

## About this project

This is a personal project, and it is honest about how it was made.

I am not a professional developer. I run a MyHOME installation at home and for
years I have gratefully used anotherjulien's integration, which is the foundation
of everything here: without that work, and without the `OWNd` library by the same
author, this fork would not exist. When the original project stopped receiving
updates — perfectly understandable for volunteer work — I forked it to keep it
alive for my own use and to fix the things that, over time, had broken with newer
Home Assistant releases.

The code in this fork was written with AI assistance, with me in the lead. That
does not mean a ten-line prompt and a "done": it meant hundreds of hours of
reading the original code and the OpenWebNet protocol, running structured
multi-agent audits of every module, deciding what to fix and how, writing shared
contracts between modules before touching them, reviewing every diff, running the
automated test suite (163 tests, including an end-to-end test against a fake
OpenWebNet server), and then testing each release against my real gateway and my
real house — lights, shutters, power meters, reloads and restarts — before
publishing it. When something did not work in the real world (for example, a
cover position that was lost on reload), it was found by testing, fixed, tested
again and released as a patch.

If you know this domain and you are skeptical of AI-assisted code, you are right
to be, and you are welcome to read the code, the tests and the
[CHANGELOG](CHANGELOG.md): every change is documented with the reason behind it.
Bug reports and pull requests are welcome; I will answer on a best-effort basis.

## What's new in 0.2.x / Upgrading

Release 0.2.0 is a stability-focused rewrite of the gateway session handling, the
YAML validator and every platform. Full details in [CHANGELOG.md](CHANGELOG.md);
the short version:

- **Minimum Home Assistant version is now 2026.8.0.**
- **Breaking: Lock/Unlock buttons are now opt-in.** They used to be generated for
  every actuator; on upgrade the existing Lock/Unlock button entities are
  **removed**. To keep them for a device, add `lock_buttons: true` under it in
  `myhome.yaml` (Point-to-Point WHERE only — see [Lock/Unlock buttons](#lockunlock-buttons)).
- **Energy totals are no longer discarded.** Instant power keeps working as before;
  the daily/monthly/total energy sensors now receive the gateway's answers when
  the gateway provides them. `daily`/`monthly` entities stay disabled by default —
  enable them from the entity's settings (gear icon → **Enable**) if your gateway
  supports the totaliser requests. Some gateways do not: a MyHOMEServer1 with
  F520/F521 meters, for instance, acknowledges the requests without returning
  data, so on that hardware those sensors remain `unknown`. See
  [Energy monitoring](#energy-monitoring).
- **You can probably remove your workaround automations** after a few days of
  watching the log: a periodic integration reload, a "command watchdog" that
  re-sends commands that didn't take effect, and a 2-hour
  `start_sending_instant_power` automation are no longer necessary — the
  integration now detects a dead session and reconnects itself, and arms/renews
  the instant-power keep-alive on its own (`keepalive_minutes`, default 125 min).
- **Discovery no longer rewrites `myhome.yaml`.** Suggestions for devices seen on
  the bus but not yet configured are written to `myhome_discovered.yaml` (next to
  your `myhome.yaml`) for you to review and copy in by hand.
- **A duplicate `where` across two devices is now a clear setup error** naming
  both YAML keys, instead of silently dropping one of the devices.
- **Modern Home Assistant patterns**: `has_entity_name`, `DeviceInfo` with
  `via_device_id`, config entry migrations, `OptionsFlowWithReload`, and closed
  deprecations (see [CHANGELOG.md](CHANGELOG.md) for the full list).

Existing `myhome.yaml` files keep working unchanged — the only behaviour change on
upgrade is the opt-in Lock/Unlock buttons, above.

## Features

- **Lights**: ON/OFF and dimmable actuators, area/group/general addresses, bus interfaces
- **Covers**: shutters and blinds with a time-based position estimate (`shutter_run`),
  `set_cover_position`, `inverted` wiring, and real positions on advanced actuators
- **Switches**: WHO 1 actuators driving loads other than lights (outlets, generic relays)
- **Climate**: thermoregulation zones and central unit (heat/cool/auto/off, set point)
- **Sensors**: instant power with a built-in keep-alive, daily/monthly/total energy
  (when the gateway answers), temperature and illuminance
- **Binary sensors**: dry contacts, alarm zones, motion sensors (with timeout)
- **Buttons** (opt-in): Lock/Unlock of a single actuator (`lock_buttons: true`)
- **Events**: CEN/CEN+ keypad presses (`myhome_cenplus_event`) and raw bus frames
  (`myhome_message_event`) for automations
- **Services**: send raw OpenWebNet messages, sync the gateway clock, start/stop
  discovery, request instant power
- **Discovery**: devices seen on the bus but not yet configured are written as
  suggestions to `myhome_discovered.yaml` (your `myhome.yaml` is never modified)
- **Multiple gateways** in one `myhome.yaml`; English, French, Italian and Dutch translations
- **Resilient by design**: TCP keepalive and idle watchdog on the event session,
  timeout/retry/TTL on the command queue, entity availability that follows the
  real connection state, strict YAML validation with clear error messages

## Supported devices

| Home Assistant platform | OpenWebNet WHO | What it covers |
|---|---|---|
| `light` | 1 | ON/OFF and dimmer actuators |
| `switch` | 1 | Actuators used for non-light loads |
| `cover` | 2 | Shutters, blinds (basic and advanced actuators) |
| `climate` | 4 | Thermostat zones, central unit |
| `sensor` | 18, 4, 1 | Power/energy meters, temperature, illuminance |
| `binary_sensor` | 25, 9, 1 | Dry contacts and alarm zones, auxiliary inputs, motion sensors |
| `button` | 14 | Optional Lock/Unlock of an actuator |

## Installation

### HACS (recommended)

This repository is not in the default HACS store: add it as a custom repository.

1. In HACS open the menu (⋮) → **Custom repositories**
2. Repository: `https://github.com/Interstellar0verdrive/MyHOME-stability-next`, type **Integration**, then **Add**
3. Search for **MyHome** in HACS, open it and **Download**
4. Restart Home Assistant
5. Add the gateway from **Settings → Devices & services → Add integration → MyHOME**
6. Describe your devices in `/config/myhome.yaml` (see [Device configuration](#device-configuration-myhomeyaml)) and reload the integration

### Manual installation

1. Download `myhome.zip` from the [latest release](https://github.com/Interstellar0verdrive/MyHOME-stability-next/releases/latest)
2. Extract it to `custom_components/myhome/` in your Home Assistant configuration directory
3. Restart Home Assistant and add the gateway from **Settings → Devices & services**

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
  `myhome_message_event` (see [Events](#events))

Saving options reloads the integration.

## Device configuration (`myhome.yaml`)

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

Under the gateway, each platform section (`light`, `switch`, `cover`, `binary_sensor`, `sensor`, `climate`) maps a **YAML key of your choice** (used only in error messages) to a device. Sections may be left empty.

Rules worth knowing:

- **Quote every `where`** (`where: "01"`, not `where: 01`). YAML reads unquoted numbers with leading zeros as decimal/octal integers and the address is lost; the validator rejects ambiguous values with a message telling you to quote them.
- **Each WHO/WHERE may appear only once per gateway**, across all platforms (a duplicate `where` used to silently drop one of the two devices). The error names both YAML keys. The only tolerated overlap is a `climate` zone plus a `sensor` of class `temperature` on the same zone.
- **Unknown keys do not break the configuration**: they are kept and reported once at WARNING level with a "did you mean" hint (e.g. `dimable` → `dimmable`). Check the log after editing the file.
- `device_class` is accepted as an alias of `class` on every platform (they must not both be given with different values).

### Common parameters (all platforms)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `where` | string | Yes | – | OpenWebNet WHERE address (see the platform notes for the accepted forms). Climate uses `zone` instead. |
| `name` | string | Yes | – | Device name in Home Assistant (optional for climate). |
| `entity_name` | string | No | device name | Name of the main entity when it must differ from the device name. |
| `icon` | string | No | – | Icon of the main entity (`mdi:...` or any registered icon set). |
| `icon_on` | string | No | – | Icon used while the entity is on (light, switch). |
| `manufacturer` | string | No | `BTicino S.p.A.` | Cosmetic, shown in the device page. |
| `model` | string | No | – | Cosmetic, shown in the device page. |
| `who` | string | No | per platform | OpenWebNet WHO; only needed for sensors/binary sensors that support several. |
| `interface` | string | No | – | Local bus interface (`"01"`..`"15"`) for devices behind a bus interface (light, switch, cover, sensors). |
| `class` / `device_class` | string | No | per platform | Home Assistant device class (see the platform tables). |

Accepted actuator WHERE forms (light, switch, cover): General `"0"`, Area `"00"`, `"1"`..`"10"`, Group `"#1"`..`"#255"`, Point-to-Point 2 digits (`"15"`, A=1 PL=5) or 4 digits (`"0115"`, A=01 PL=15). Sensors, binary sensors and climate accept any string of digits (energy meters are usually `"51"`..`"5N"`, thermo zones `"1"`..`"99"`).

### Light

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dimmable` | boolean | `false` | Enable brightness control. |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

### Switch

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class` | `switch` \| `outlet` | `switch` | Device class. |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

### Cover

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `advanced` | boolean | `false` | Advanced actuator reporting its real position (position control from the device). |
| `shutter_run` | number (s) | `20` | Full travel time in seconds. Basic actuators use it to estimate the position (0 = closed, 100 = open), derive open/closed and support *set position* by timed stop. |
| `inverted` | boolean | `false` | Swap the up/down semantics (position 0 becomes open). |
| `class` | cover device class | `shutter` | Any Home Assistant cover class (`shutter`, `blind`, `awning`, `garage`, ...). |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

### Binary sensor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `who` | `"25"` \| `"1"` \| `"9"` | `"25"` | `25` dry contact / alarm zone, `1` motion sensor (lighting bus), `9` auxiliary. |
| `class` | binary sensor device class | by WHO | Default `opening` for WHO 25, `motion` for WHO 1, none for WHO 9. |
| `inverted` | boolean | `false` | Invert the reported state. |

### Climate

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `zone` | string | `"#0"` | Thermo zone `"1"`..`"99"`, or `"#0"` for the central unit. `where` is accepted as an alias. |
| `name` | string | `Zone N` / `Central unit` | Optional. |
| `heat` | boolean | `true` | Heating support. |
| `cool` | boolean | `false` | Cooling support. |
| `fan` | boolean | `false` | Fan support. |
| `standalone` | boolean | `false` | Standalone thermostat (no central unit). |
| `central` | boolean | `false` | Zone driven through the central unit (`#0#N` addressing). |

### Sensor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class` | `power` \| `energy` \| `temperature` \| `illuminance` | **required** | Sensor type. `power`/`energy` are WHO 18 meters (`power` also creates the daily/monthly/total energy entities), `temperature` WHO 4 (WHERE = zone), `illuminance` WHO 1. |
| `who` | string | from `class` | Only needed to override the WHO implied by the class (must match). |
| `keepalive_minutes` | integer 0-255 | `125` | Power meters only: the integration asks the meter to push instant power for this many minutes and renews the request by itself. `0` disables the automatic keep-alive. |
| `min_delta_w`, `min_interval_sec`, `suppress_log_interval_sec`, `info_log_interval_sec` | number | see [Energy monitoring](#energy-monitoring) | Per-sensor overrides of the power filtering defaults. |
| `refresh_period` | number | – | Alias of `min_interval_sec` (upstream name). |

Units are fixed by the class (W, Wh, °C, lx). Energy filtering, totals and
`keepalive_minutes` are covered in full in [Energy monitoring](#energy-monitoring).

### Lock/Unlock buttons

Lights, switches and covers with `lock_buttons: true` get two configuration buttons (**Lock** / **Unlock**) that disable/enable the actuator on the bus (`*14*...`). They are only generated for Point-to-Point WHEREs: locking a General or Area WHERE would disable every actuator of the plant. Buttons are off by default; existing installations that relied on the automatically generated buttons must opt in per device.

### Multiple gateways

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

Each gateway also needs its own config entry (discovered or manual) with the same MAC.

### Custom icons and device classes

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

### Validation errors

`myhome.yaml` is validated on every (re)load. Errors block the setup and are shown in the integration card with the key path (`gateway.cover.<key>.where`); warnings only appear in the log. Typical messages:

- **`required key not provided`**: `where` and `name` are mandatory (climate: `zone`/`name` optional).
- **`Invalid <WHERE>`** / **`quote it`**: the address is not a valid OpenWebNet WHERE, or an unquoted number lost its leading zero.
- **`Duplicate WHERE 'x' (who N): cover 'a' collides with cover 'b'`**: the same device is declared twice; fix the address or remove one of the two entries (both YAML keys are named).
- **`sensor 'x' is missing the required sensor class`**: add `class: power|energy|temperature|illuminance`.
- **`gateway 'x' needs a 'mac'`** / **`configured twice`**: every root entry needs a MAC (as `mac:` or as the root key) and each MAC may appear once.
- **`unknown key 'dimable' in light.x is ignored (did you mean 'dimmable'?)`** (WARNING): a typo or an unsupported key; the device is still created without it.

## Services

### `myhome.start_discovery`

Start automatic device discovery on a gateway.

```yaml
service: myhome.start_discovery
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
```

### `myhome.stop_discovery`

Stop active device discovery.

```yaml
service: myhome.stop_discovery
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
```

### `myhome.start_sending_instant_power`

Asks the energy meter of the targeted power sensor(s) to (re)start sending instant
power updates. The integration already does this automatically on startup, on
reconnection and every `keepalive_minutes - 5` minutes (see [Sensor](#sensor)); use
this service to force it, or for a one-off/different duration.

```yaml
service: myhome.start_sending_instant_power
target:
  entity_id: sensor.house_main_power
data:
  duration: 60  # minutes, 1-255. Optional: defaults to the sensor's keepalive_minutes
```

### `myhome.sync_time`

Synchronize gateway time with Home Assistant.

```yaml
service: myhome.sync_time
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
```

### `myhome.send_message`

Send raw OpenWebNet commands to the gateway.

```yaml
service: myhome.send_message
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
  message: "*1*1*15##"  # Turn on light at address 15
```

## Events

### Device discovery events

- `myhome_device_discovered`: fired when a new device is found. Data: `platform`,
  `discovered_device`, `config_entry_id`, `gateway_mac`.
- `myhome_discovery_completed`: fired when a discovery run finishes (`myhome.stop_discovery`
  or the 60-second timeout).

### CEN / CEN+ keypad events

- `myhome_cenplus_event`: CEN+ scenario control events. Data: `object` (int, the
  CEN+ device address), `pushbutton` (int), `event` — one of
  `pushbutton_short_press`, `pushbutton_long_press` (fired once when a button is
  first held), `pushbutton_long_press_repeat` (fired repeatedly while it stays
  held), `pushbutton_long_release`, `rotate_cw_slow`, `rotate_cw_fast`,
  `rotate_ccw_slow`, `rotate_ccw_fast` (rotary CEN+ devices only).
- `myhome_cen_event`: CEN button events. Data: `object`, `pushbutton`, `event` —
  one of `pushbutton_short_press`, `pushbutton_short_release`,
  `pushbutton_long_press`, `pushbutton_long_release`.

### General/area/group bus events

Fired when a General/Area/Group lighting or automation command is seen on the bus
(e.g. someone uses a physical "all lights off" button); data includes the raw
`message` and, where applicable, the `area`/`group` address.

- `myhome_general_light_event`, `myhome_area_light_event`, `myhome_group_light_event`
  (WHO 1, lighting)
- `myhome_general_automation_event`, `myhome_area_automation_event`, `myhome_group_automation_event`
  (WHO 2, automation/covers)

### Raw bus traffic

- `myhome_message_event`: every parsed OpenWebNet frame from the monitor session,
  as `{"gateway": <host>, ...frame fields}`. Off by default — enable it with the
  **"Generate events in Home Assistant for each message received"** integration
  option if you want to build automations directly on raw bus traffic; expect a
  lot of events on a busy plant.

### Example event automation

```yaml
automation:
  - alias: "Scene Button Pressed"
    trigger:
      platform: event
      event_type: myhome_cenplus_event
      event_data:
        object: 25
        pushbutton: 1
        event: pushbutton_short_press
    action:
      service: scene.turn_on
      target:
        entity_id: scene.evening_lights
```

## Energy monitoring

### Instant power keep-alive

Power meters (WHO 18, `class: power`) only push instant-power updates for a
limited time after being asked. The integration asks automatically on startup,
on reconnection, and renews the request every `keepalive_minutes - 5` minutes so
it never lapses (`keepalive_minutes`, default `125`, `0` disables the automatic
keep-alive). Call `myhome.start_sending_instant_power` to force a request or use
a one-off duration (see [Services](#services)).

### Filtering push updates

Power meters push a value at every fluctuation. An instant-power update is
**processed** if **either** the absolute change vs. the last processed value is
**>= `min_delta_w`** or the time since the last processed value is **>=
`min_interval_sec`**; otherwise it is dropped (totalisers and daily/monthly
energy values are never filtered). When debug logging is enabled, dropped
updates are aggregated and logged at most once per `suppress_log_interval_sec`.

Defaults apply per gateway under `sensor_defaults:` (alias `energy:`; if both are present they are merged key by key and `sensor_defaults` wins) and can be overridden per sensor:

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"

  sensor_defaults:
    min_delta_w: 25              # process if |delta| >= 25 W ...
    min_interval_sec: 5          # ... or if the last processed value is older than 5 s
    suppress_log_interval_sec: 60
    keepalive_minutes: 125       # 0 disables the automatic instant-power keep-alive

  sensor:
    house_main_power:
      where: "51"
      name: "House Main Power"
      class: power
      min_delta_w: 50            # per-sensor override
      # refresh_period: 10       # alias of min_interval_sec
```

Built-in defaults: `min_delta_w: 5`, `min_interval_sec: 1`, `suppress_log_interval_sec: 60`, `keepalive_minutes: 125`. Precedence: per-sensor key → `sensor_defaults`/`energy` → built-in. Legacy `energy_*` spellings of these keys are still accepted.

### Daily/monthly/total energy and gateways without totals

A `power` sensor also creates daily/monthly/total energy entities, fed by the
gateway's own totaliser replies. `daily`/`monthly` stay **disabled by default** —
enable them from the entity's settings (gear icon → **Enable**) if your gateway
answers totaliser requests.

Not every gateway does: a MyHOMEServer1 with F520/F521 meters, for instance,
acknowledges the requests without returning data, so on that hardware those
sensors remain `unknown`. If your gateway does not provide totals, use Home
Assistant's built-in [`integration`](https://www.home-assistant.io/integrations/integration/)
helper on the `power` sensor to derive energy instead.

### Example

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  sensor:
    total_power:
      where: "51"
      name: "Total Power Consumption"
      class: power           # creates Power + Energy today/month/total entities
      min_interval_sec: 10   # rate-limit push updates (no polling)
      keepalive_minutes: 125 # automatic instant-power keep-alive
      icon: "mdi:flash"
    zone_temperature:
      where: "1"             # thermo zone 1
      name: "Living Room Temperature"
      class: temperature
```

## Discovery

Since 0.2.0, discovery **never writes to `myhome.yaml`**. Suggestions for devices
seen on the bus but not yet configured are written to `myhome_discovered.yaml`,
next to your `myhome.yaml` (same folder, i.e. the path from `config_file_path` in
the integration options, or your Home Assistant config directory). Review that
file and copy the entries you want into `myhome.yaml` yourself, then reload the
integration.

- Start with `myhome.start_discovery`, stop early with `myhome.stop_discovery`
  (see [Services](#services)); a run otherwise stops itself after 60 seconds.
  Both flush whatever was collected so far to the file.
- A device already present in `myhome.yaml` (matched on WHO/WHERE) is not
  suggested again.
- Progress fires `myhome_device_discovered` per device and
  `myhome_discovery_completed` when the run ends (see [Events](#events)).

## Troubleshooting

### Gateway connection issues

1. **Check network connectivity**: Ensure Home Assistant can reach the gateway IP
2. **Verify gateway password**: Ensure the password is correct
3. **Check firewall settings**: Ensure port 20000 is accessible
4. **Review logs**: Check Home Assistant logs for connection errors

### Device discovery issues

**"Discovery not active" in logs:**
- Ensure you're calling the service correctly: `service: myhome.start_discovery` with `gateway: "MAC_ADDRESS"`
- Don't put service calls in the YAML config file - use Developer Tools → Services
- Check that the gateway MAC address is correct
- Verify the service call shows `discovery_active: True` in debug logs

**No devices found during discovery:**
1. **Enable debug logging** to see discovery messages:
   ```yaml
   logger:
     logs:
       custom_components.myhome.discovery: debug
       custom_components.myhome.gateway: debug
       custom_components.myhome.config_flow_discovery: debug
   ```
2. **Check discovery status** - Look for logs like:
   - `"Starting MyHOME device discovery on gateway..."`
   - `"Sending discovery command 1/6: *#1*0##"`
   - `"Discovery message received: *1*8*11##"`
   - `"Discovered new device: MyHOME Bus Dimmer 11 at WHERE=11"`
   - `"Starting device configuration suggestion for MyHOME Bus Dimmer 11"`
   - `"Starting config file write process for device MyHOME Bus Dimmer 11"`
   - `"Successfully added device MyHOME Bus Dimmer 11 to configuration file"`
3. **Verify device responses** - Look for incoming messages after discovery commands
4. **Check gateway communication** - Ensure devices are responding to status requests
5. **Manual device test** - Try controlling devices through other MyHOME apps first

**Incorrect device type detection:**
- **Dimmer vs Switch**: Discovery determines device type based on status responses
  - Devices reporting dimming levels (WHAT=2-10, excluding 8) are detected as dimmers
  - Devices reporting only ON/OFF states (WHAT=0,1,8) are detected as switches
  - If a dimmer is incorrectly detected as a switch, manually edit the config and set `dimmable: true`
- **Special states**: WHAT=8 often indicates "temporized ON" or other special states, not dimming capability

**Devices discovered but suggestions missing:**

See [Discovery](#discovery) — since 0.2.0, suggestions go to `myhome_discovered.yaml`, not `myhome.yaml`.

1. **Check `myhome_discovered.yaml`** exists and has grown after a discovery run.
2. **Verify file permissions** - ensure Home Assistant can write to that folder.
3. Discovery only runs for the duration of `myhome.start_discovery` (default
   60 s) or until `myhome.stop_discovery` is called; both flush whatever was
   collected so far to the file.
4. A device already present in `myhome.yaml` (matched on WHO/WHERE) is not
   suggested again.

### Configuration issues

1. **Validate YAML syntax**: Ensure `myhome.yaml` has correct formatting
2. **Check device addresses**: Verify WHERE addresses match physical devices
3. **Review device types**: Ensure correct platform assignments
4. **Restart Home Assistant**: Required after `myhome.yaml` changes

See [Validation errors](#validation-errors) for the exact error messages the
integration produces.

### Debug logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: warning
  logs:
    custom_components.myhome: debug
    OWNd: debug
```

> **Note:** For day-to-day use, keep `custom_components.myhome` at `info` (or leave the `logger:` block out entirely) — per-frame bus traffic is only logged at `debug`. Occasional "reconnecting" INFO lines after a gateway hiccup are expected; the integration retries and recovers on its own. Use `debug` only when troubleshooting.

### Migration from v0.8 and earlier

If upgrading from version 0.8 or earlier:

1. **Create myhome.yaml**: Move device configurations from `configuration.yaml`
2. **Update device structure**: Follow the new YAML format below
3. **Remove old configuration**: Delete MyHOME entries from `configuration.yaml`
4. **Restart Home Assistant**: Required for new configuration to take effect
5. **Use auto-discovery**: Consider using the new discovery features

**Old format (configuration.yaml):**
```yaml
myhome:
  gateways:
    - host: 192.168.1.35
      devices:
        light:
          - where: "15"
            name: "Living Room"
            dimmable: true
```

**New format (myhome.yaml):**
```yaml
"00:03:50:XX:XX:XX":
  light:
    living_room:
      where: "15"
      name: "Living Room"
      dimmable: true
```

## Development

```bash
# Set up a virtual environment with the same Home Assistant / OWNd versions this
# integration targets, plus the test tooling:
python3 -m venv .venv
source .venv/bin/activate
pip install homeassistant pytest pytest-homeassistant-custom-component ruff \
  "OWNd==0.7.48"

# Run the test suite (pytest.ini sets asyncio_mode = auto, required by the HA
# test plugin):
pytest tests

# Lint (matches what was run before this release):
ruff check custom_components tests --select F,E9,B,UP,ASYNC
```

The tests never talk to a real gateway: `tests/test_gateway.py` and
`tests/test_init.py` spin up a loopback fake OpenWebNet server instead. A test
fixture mirroring a real (redacted) `myhome.yaml` lives in `tests/fixtures/`.

## Support & contributing

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/Interstellar0verdrive/MyHOME-stability-next/issues)
- **Wiki**: [Detailed documentation and examples](https://github.com/anotherjulien/MyHOME/wiki)
- **Community Forum**: [Home Assistant Community](https://community.home-assistant.io/)

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Acknowledgments

- **[anotherjulien/MyHOME](https://github.com/anotherjulien/MyHOME)** and **[OWNd](https://github.com/anotherjulien/OWNd)**: the original integration and the OpenWebNet library it runs on — the foundation of everything in this repository. Thank you.
- **[artmakh/MyHOME](https://github.com/artmakh/MyHOME)**: the intermediate fork this repository started from
- **OpenHAB OpenWebNet binding**: reference for the discovery device-type mapping
- **Home Assistant Community**: Continuous feedback and support
- **BTicino/Legrand**: MyHOME protocol and documentation

## License

This project is licensed under the GNU Affero General Public License v3.0 — see the [LICENSE](LICENSE) file for details.
