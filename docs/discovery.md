# Discovery

How the integration finds devices on the bus that are not yet in `myhome.yaml`,
and what it does (and does not) do with them.

Since 0.2.0, discovery **never writes to `myhome.yaml`**. Suggestions for devices
seen on the bus but not yet configured are written to `myhome_discovered.yaml`,
next to your `myhome.yaml` (same folder, i.e. the path from the **Configuration
file path** option, or your Home Assistant config directory). Review that file
and copy the entries you want into `myhome.yaml` yourself, then reload the
integration.

> **If you ran discovery before this version and your plant has an F422 local bus
> interface,** delete `myhome_discovered.yaml` before your next run. The old file may
> hold two blocks for the same physical device: one without an `interface:` key,
> written by the earlier version, which is wrong and drives the main-bus device of the
> same address, and one with it, which is right. The file is only ever added to, never
> cleaned up, so both survive and both are accepted by the schema. Nothing is lost by
> deleting it — a run rewrites it.

- Start with `myhome.start_discovery`, stop early with `myhome.stop_discovery`
  (see [Services](services-and-events.md#services)); a run otherwise stops itself
  after 60 seconds. Both flush whatever was collected so far to the file.
- A run opens with one general status request per subsystem that has one
  (lighting, automation, thermoregulation, energy, auxiliary), then listens. Dry
  contacts (WHO 25) have no general status request and CEN / CEN+ keypads never
  answer one, so those devices are seen only when they emit a frame during the
  window: open the contact, press a button.
- A device already present in `myhome.yaml` (matched on WHO, WHERE and bus
  interface) is not suggested again. A CEN / CEN+ scenario control already declared
  under `scenario_control:` is likewise left out of the run's closing report — it is
  matched on its protocol and object number, which is how the integration keys it, and
  not on WHO/WHERE.
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
| Thermoregulation central unit | `climate` (WHO 4, `zone: "#0"`) |
| Temperature probe | `sensor` (WHO 4, `class: temperature`) |
| Dry contact / IR detector | `binary_sensor` (WHO 25, `class: motion`) |
| Auxiliary channel | `binary_sensor` (`who: "9"`, no class) |

A device behind an F422 local bus interface is suggested with its `interface:` key
(`where: "11"` plus `interface: "3"` for the actuator addressed `11#4#3` on the bus),
so it is a different suggestion from the main-bus device with the same WHERE. See
[Configuration → Local bus interfaces](configuration.md#local-bus-interfaces-interface).

A zone and a probe are told apart by the WHERE alone: a plain zone number is the
zone reporting its own sensor (`climate`), a WHERE above 99 is a probe of its own
(`sensor`). A probe wired as the *main* sensor of a zone therefore looks like the
zone and is suggested as `climate`; delete that line if you only want the reading,
or keep both, since a `climate` zone and a `temperature` sensor on the same zone are
allowed together. The first WHO 4 frame seen for a WHERE decides, and the run never
revises it. A WHO 4 frame whose WHERE is `0` is the central unit rather than a zone,
and is suggested as `zone: "#0"` — the only spelling the schema accepts for it.

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
[`scenario_control:`](configuration.md#scenario-control-cen--cen). If the keypad is
already declared there, the run does not mention it at all.

A lighting or automation frame addressed to the whole plant (WHERE `0`), to an area
(`00`, `1`–`9`, `100` — the bus spells area 10 with three digits) or to a group
(`#1`–`#255`) is not a device and is not discovered: the integration reports it on the
event bus as a general/area/group event instead. Such a block can still be written by
hand if you want an entity that commands a whole area — see
[Configuration → Common parameters](configuration.md#common-parameters-all-platforms) —
but it is a choice, not something a run will offer you, and the schema spells area 10
`10`, never `100`.

A frame whose F422 interface is outside `0`-`15` is ignored as well: the address
could not be declared anyway (the configuration schema refuses the same value), so a
run does not offer it rather than announcing the main-bus device with the same WHERE.

Of the burglar-alarm traffic, the per-sensor frames are reported (their WHERE is
`<zone><sensor>`); the zone-level frames, addressed `#<zone>`, are not, because an
alarm zone has no entity and no `myhome.yaml` section to declare it under.

What a run could not suggest is reported in its closing log line, in two clauses that
say different things: *"N device(s) must be declared by hand under `scenario_control:`"*
names the section to write them under, while *"N device(s) belong to a family this
integration has no support for"* is the alarm case, which has no section anywhere.
Each device is named `<device type>@<address>`, with the address exactly as the bus
writes it, F422 interface included (`bus_cen_scenario_control@11#4#3`). At most ten
names are listed; when there are more, the list ends with `, ... and N more`. Keypads
you have already declared are not counted.

For debug-log examples of a discovery run, and what to check when no devices are
found or suggestions are missing, see
[Troubleshooting → Device discovery issues](troubleshooting.md#device-discovery-issues).
