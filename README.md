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
- [Quick start](#quick-start)
  - [Installation](#installation)
  - [Gateway setup](#gateway-setup)
  - [Device configuration (`myhome.yaml`)](#device-configuration-myhomeyaml)
- [What's new in 0.2.x / Upgrading](#whats-new-in-02x--upgrading)
- [Features](#features)
- [Supported devices](#supported-devices)
- [Documentation](#documentation)
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

## Quick start

### Installation

#### HACS (recommended)

This repository is not in the default HACS store: add it as a custom repository.

1. In HACS open the menu (⋮) → **Custom repositories**
2. Repository: `https://github.com/Interstellar0verdrive/MyHOME-stability-next`, type **Integration**, then **Add**
3. Search for **MyHome** in HACS, open it and **Download**
4. Restart Home Assistant
5. Add the gateway from **Settings → Devices & services → Add integration → MyHOME**
6. Describe your devices in `/config/myhome.yaml` (see below) and reload the integration

#### Manual installation

1. Download `myhome.zip` from the [latest release](https://github.com/Interstellar0verdrive/MyHOME-stability-next/releases/latest)
2. Extract it to `custom_components/myhome/` in your Home Assistant configuration directory
3. Restart Home Assistant and add the gateway from **Settings → Devices & services**

### Gateway setup

Add the gateway from **Settings → Devices & services → Add integration → MyHOME**.
Most gateways are found via SSDP; otherwise choose **"Configure manually"** and
enter host, port and password. A later password rejection raises a reauth flow,
and **Configure** on the integration card changes the address, the `myhome.yaml`
path, session count and raw-event generation without removing the integration.

Full walkthrough and every option: [Configuration reference](docs/configuration.md).

### Device configuration (`myhome.yaml`)

Devices are declared in `myhome.yaml`, in your Home Assistant config folder. Here
is a minimal example — one light, one cover and one power sensor on a single
gateway:

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  light:
    kitchen_light:
      where: "15"
      name: "Kitchen Light"
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
  sensor:
    house_main_power:
      where: "51"
      name: "House Main Power"
      class: power
```

Save the file, then reload the integration (**Settings → Devices & services →
MyHOME → ⋮ → Reload**). The file is validated on every (re)load; a validation
error is shown in the integration card with the offending key path.

This covers the basics — see [Configuration reference](docs/configuration.md)
for the full parameter tables (every platform, energy filtering, Lock/Unlock
buttons, multiple gateways, custom icons) and [Recipes](docs/recipes.md) for
copy-paste automations.

## What's new in 0.2.x / Upgrading

Release 0.2.0 is a stability-focused rewrite of the gateway session handling, the
YAML validator and every platform. Full details in [CHANGELOG.md](CHANGELOG.md)
and a step-by-step guide in [Migrating from the original](docs/migrating-from-original.md);
the highlights:

- **Minimum Home Assistant version is now 2026.8.0.**
- **Breaking: Lock/Unlock buttons are now opt-in.** They used to be generated for
  every actuator; on upgrade the existing Lock/Unlock button entities are
  **removed**. Add `lock_buttons: true` under a device to keep them.
- **Energy totals are no longer discarded**, but not every gateway provides them:
  a MyHOMEServer1 with F520/F521 meters, for instance, acknowledges the requests
  without returning data, so those sensors stay `unknown` on that hardware. See
  [Energy monitoring](docs/energy.md).
- **You can probably remove your workaround automations** after a few days of
  watching the log: the integration now detects a dead session and reconnects
  itself, and arms/renews the instant-power keep-alive on its own.
- **A duplicate `where` across two devices is now a clear setup error** naming
  both YAML keys, instead of silently dropping one of the devices.

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

## Documentation

The [`docs/`](docs/README.md) folder goes deeper than this README:

- [Configuration reference](docs/configuration.md) — gateway setup from the UI,
  the full `myhome.yaml` schema, Lock/Unlock buttons, multiple gateways, custom
  icons, and validation errors
- [Services and events](docs/services-and-events.md) — every service's fields
  and every event's data contract
- [Energy monitoring](docs/energy.md) — the instant-power keep-alive, the push
  filter, daily/monthly/total energy, and deriving kWh without gateway totals
- [Discovery](docs/discovery.md) — what a discovery run writes and does not touch
- [Troubleshooting](docs/troubleshooting.md) — common issues, debug logging, and
  upgrading from the pre-`myhome.yaml` versions
- [Gateway compatibility](docs/gateway-compatibility.md) — what is verified per
  gateway model, what is only expected, and how to report yours
- [Recipes](docs/recipes.md) — copy-paste automations and configuration for
  CEN/CEN+, raw commands, covers, energy, buttons and multiple gateways
- [Migrating from the original](docs/migrating-from-original.md) — upgrading from
  `anotherjulien/MyHOME` (or the `artmakh` fork), and the known limitations
- [Architecture](docs/architecture.md) — how it works inside, for contributors
- [Development](docs/development.md) — setting up a dev environment, tests, linting

## Support & contributing

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/Interstellar0verdrive/MyHOME-stability-next/issues)
- **Wiki**: [Detailed documentation and examples](https://github.com/anotherjulien/MyHOME/wiki)
- **Community Forum**: [Home Assistant Community](https://community.home-assistant.io/)

Contributions are welcome! Please fork the repository, create a feature branch,
make your changes, add tests if applicable, and submit a pull request. See
[Development](docs/development.md) to set up the test suite and linter first.

## Acknowledgments

- **[anotherjulien/MyHOME](https://github.com/anotherjulien/MyHOME)** and **[OWNd](https://github.com/anotherjulien/OWNd)**: the original integration and the OpenWebNet library it runs on — the foundation of everything in this repository. Thank you.
- **[artmakh/MyHOME](https://github.com/artmakh/MyHOME)**: the intermediate fork this repository started from
- **OpenHAB OpenWebNet binding**: reference for the discovery device-type mapping
- **Home Assistant Community**: Continuous feedback and support
- **BTicino/Legrand**: MyHOME protocol and documentation

## License

This project is licensed under the GNU Affero General Public License v3.0 — see the [LICENSE](LICENSE) file for details.
