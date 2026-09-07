# Discovery

How the integration finds devices on the bus that are not yet in `myhome.yaml`,
and what it does (and does not) do with them.

Since 0.2.0, discovery **never writes to `myhome.yaml`**. Suggestions for devices
seen on the bus but not yet configured are written to `myhome_discovered.yaml`,
next to your `myhome.yaml` (same folder, i.e. the path from the **Configuration
file path** option, or your Home Assistant config directory). Review that file
and copy the entries you want into `myhome.yaml` yourself, then reload the
integration.

- Start with `myhome.start_discovery`, stop early with `myhome.stop_discovery`
  (see [Services](services-and-events.md#services)); a run otherwise stops itself
  after 60 seconds. Both flush whatever was collected so far to the file.
- A device already present in `myhome.yaml` (matched on WHO/WHERE) is not
  suggested again.
- Progress fires `myhome_device_discovered` per device and
  `myhome_discovery_completed` when the run ends (see
  [Events → Device discovery events](services-and-events.md#device-discovery-events)).

## What discovery can suggest

Discovery only writes the device types it knows how to turn into a `myhome.yaml`
entry:

| Seen on the bus | Suggested as |
|---|---|
| Lighting actuator, ON/OFF | `light` (WHO 1, `dimmable: false`) |
| Lighting actuator answering with a brightness or a preset level | `light` (WHO 1, `dimmable: true`) |
| Automation actuator | `cover` (WHO 2, `shutter_run: 20`) |
| Energy meter | `sensor` (WHO 18, `class: power`) |
| Thermoregulation zone | `climate` (WHO 4) |
| Temperature probe | `sensor` (WHO 4, `class: temperature`) |
| Dry contact / IR detector | `binary_sensor` (WHO 25, `class: motion`) |
| Auxiliary channel | `binary_sensor` (`who: "9"`, no class) |

An auxiliary channel is suggested as a `binary_sensor` with an explicit
`who: "9"`, never as a `switch`: WHO 9 is read-only on this integration (the bus
reports the channel, nothing commands it) and the `switch` platform only accepts
`who: "1"`. See [Configuration → Binary sensor](configuration.md#binary-sensor)
for what the entity does once declared.

Everything else is seen and reported on the event bus but **never** written to
`myhome_discovered.yaml`: CEN and CEN+ scenario controls, alarm devices, and any
frame the classifier cannot place. Pressing keypad buttons during a run therefore
fires `myhome_device_discovered` and adds nothing to the file — that is expected,
not a failure. Declare scenario controls by hand, under
[`scenario_control:`](configuration.md#scenario-control-cen--cen).

For debug-log examples of a discovery run, and what to check when no devices are
found or suggestions are missing, see
[Troubleshooting → Device discovery issues](troubleshooting.md#device-discovery-issues).
