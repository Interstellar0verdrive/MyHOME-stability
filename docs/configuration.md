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
- [The `myhome.yaml` file](#the-myhomeyaml-file)
- [Common parameters (all platforms)](#common-parameters-all-platforms)
- [Light](#light)
- [Switch](#switch)
- [Cover](#cover)
- [Binary sensor](#binary-sensor)
- [Climate](#climate)
- [Sensor](#sensor)
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

Under the gateway, each platform section (`light`, `switch`, `cover`, `binary_sensor`, `sensor`, `climate`) maps a **YAML key of your choice** (used only in error messages) to a device. Sections may be left empty.

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
| `entity_name` | string | No | device name | Name of the main entity when it must differ from the device name. |
| `icon` | string | No | – | Icon of the main entity (`mdi:...` or any registered icon set). |
| `icon_on` | string | No | – | Icon used while the entity is on (light, switch). |
| `manufacturer` | string | No | `BTicino S.p.A.` | Cosmetic, shown in the device page. |
| `model` | string | No | – | Cosmetic, shown in the device page. |
| `who` | string | No | per platform | OpenWebNet WHO; only needed for sensors/binary sensors that support several. |
| `interface` | string | No | – | Local bus interface (`"01"`..`"15"`) for devices behind a bus interface (light, switch, cover, sensors). |
| `class` / `device_class` | string | No | per platform | Home Assistant device class (see the platform tables). |

Accepted actuator WHERE forms (light, switch, cover): General `"0"`, Area `"00"`, `"1"`..`"10"`, Group `"#1"`..`"#255"`, Point-to-Point 2 digits (`"15"`, A=1 PL=5) or 4 digits (`"0115"`, A=01 PL=15). Sensors, binary sensors and climate accept any string of digits (energy meters are usually `"51"`..`"5N"`, thermo zones `"1"`..`"99"`).

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
| `shutter_run` | number (s) | `20` | Full travel time in seconds. Basic actuators use it to estimate the position (0 = closed, 100 = open), derive open/closed and support *set position* by timed stop. |
| `inverted` | boolean | `false` | Swap the up/down semantics (position 0 becomes open). |
| `class` | cover device class | `shutter` | Any Home Assistant cover class (`shutter`, `blind`, `awning`, `garage`, ...). |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

See [Recipes → Covers](recipes.md#covers) for tuning `shutter_run`, `set_cover_position` behaviour and `inverted` wiring.

## Binary sensor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `who` | `"25"` \| `"1"` \| `"9"` | `"25"` | `25` dry contact / alarm zone, `1` motion sensor (lighting bus), `9` auxiliary. |
| `class` | binary sensor device class | by WHO | Default `opening` for WHO 25, `motion` for WHO 1, none for WHO 9. |
| `inverted` | boolean | `false` | Invert the reported state. |

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
| `class` | `power` \| `energy` \| `temperature` \| `illuminance` | **required** | Sensor type. `power`/`energy` are WHO 18 meters (`power` also creates the daily/monthly/total energy entities), `temperature` WHO 4 (WHERE = zone), `illuminance` WHO 1. |
| `who` | string | from `class` | Only needed to override the WHO implied by the class (must match). |
| `keepalive_minutes` | integer 0-255 | `125` | Power meters only: the integration asks the meter to push instant power for this many minutes and renews the request by itself. `0` disables the automatic keep-alive. |
| `min_delta_w`, `min_interval_sec`, `suppress_log_interval_sec`, `info_log_interval_sec` | number | see [Energy monitoring](energy.md) | Per-sensor overrides of the power filtering defaults. |
| `refresh_period` | number | – | Alias of `min_interval_sec` (upstream name). |

Units are fixed by the class (W, Wh, °C, lx). Energy filtering, totals and
`keepalive_minutes` are covered in full in [Energy monitoring](energy.md).

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
- **`gateway 'x' needs a 'mac'`** / **`configured twice`**: every root entry needs a MAC (as `mac:` or as the root key) and each MAC may appear once.
- **`unknown key 'dimable' in light.x is ignored (did you mean 'dimmable'?)`** (WARNING): a typo or an unsupported key; the device is still created without it.

See [Troubleshooting → Configuration issues](troubleshooting.md#configuration-issues) if the integration will not load after an edit.
