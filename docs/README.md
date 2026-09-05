# Documentation

Supplementary documentation for the MyHOME (Stability) integration. The
[main README](../README.md) covers the elevator pitch, installation and a
minimal configuration example; the pages here go deeper.

- **[Configuration reference](configuration.md)** — gateway setup from the UI,
  the full `myhome.yaml` schema (file location, root formats, every parameter per
  platform), Lock/Unlock buttons, multiple gateways, custom icons/device
  classes, and validation errors.
- **[Services and events](services-and-events.md)** — the five services and
  their fields, and the event contracts (CEN/CEN+, general/area/group,
  discovery, raw bus traffic).
- **[Energy monitoring](energy.md)** — the instant-power keep-alive, the push
  filter, `sensor_defaults`, daily/monthly/total energy, and deriving kWh with
  `integration`/`utility_meter` when the gateway returns no totals.
- **[Discovery](discovery.md)** — what a discovery run writes to
  `myhome_discovered.yaml` and does not touch in `myhome.yaml`.
- **[Troubleshooting](troubleshooting.md)** — common issues, debug logging, and
  upgrading from the pre-`myhome.yaml` (v0.8 and earlier) versions.
- **[Gateway compatibility](gateway-compatibility.md)** — what is verified, only
  expected, or unknown per gateway model; the hard-coded watchdog, keep-alive and
  queue values; how to report your own gateway.
- **[Recipes](recipes.md)** — copy-paste examples for CEN/CEN+ keypads, raw
  OpenWebNet commands, covers, energy, Lock/Unlock buttons, several gateways and
  raw-bus debugging.
- **[Migrating from the original](migrating-from-original.md)** — coming from
  `anotherjulien/MyHOME` or the `artmakh` fork: what stays compatible, what
  changed, a step-by-step upgrade, and the known limitations.
- **[Architecture](architecture.md)** — how it works inside: module map, config
  entry lifecycle, the two OpenWebNet sessions, the command queue, the dispatcher,
  the validator contract and the test strategy.
- **[Development](development.md)** — setting up a virtual environment, running
  the test suite, and linting.
