# Services and events

The seven services the integration registers, and the contract (event name and
data keys) of every event it fires. For copy-paste automations built on these,
see [Recipes](recipes.md).

## Contents

- [Services](#services)
  - [`myhome.start_discovery`](#myhomestart_discovery)
  - [`myhome.stop_discovery`](#myhomestop_discovery)
  - [`myhome.start_sending_instant_power`](#myhomestart_sending_instant_power)
  - [`myhome.sync_time`](#myhomesync_time)
  - [`myhome.send_message`](#myhomesend_message)
  - [`myhome.cover_calibration_run`](#myhomecover_calibration_run)
  - [`myhome.cover_calibration_compute`](#myhomecover_calibration_compute)
- [Events](#events)
  - [Device discovery events](#device-discovery-events)
  - [CEN+ keypad events](#cen-keypad-events)
  - [CEN keypad events](#cen-keypad-events-1)
  - [Device triggers and event entities](#device-triggers-and-event-entities)
  - [General/area/group bus events](#generalareagroup-bus-events)
  - [Wall pushbutton events (`myhome_light_pushbutton_event`)](#wall-pushbutton-events-myhome_light_pushbutton_event)
  - [Raw bus traffic (`myhome_message_event`)](#raw-bus-traffic-myhome_message_event)
  - [Example event automation](#example-event-automation)

## Services

### `myhome.start_discovery`

Start automatic device discovery on a gateway. See [Discovery](discovery.md).

```yaml
action: myhome.start_discovery
data:
  gateway: "00:03:50:AA:BB:CC"  # Optional
```

### `myhome.stop_discovery`

Stop active device discovery.

```yaml
action: myhome.stop_discovery
data:
  gateway: "00:03:50:AA:BB:CC"  # Optional
```

### `myhome.start_sending_instant_power`

Asks the energy meter of the targeted power sensor(s) to (re)start sending instant
power updates. The integration already does this automatically on startup, on
reconnection and every `keepalive_minutes - 5` minutes (see
[Configuration → Sensor](configuration.md#sensor)); use this service to force it,
or for a one-off/different duration.

```yaml
action: myhome.start_sending_instant_power
target:
  entity_id: sensor.house_main_power
data:
  duration: 60  # minutes, 1-255. Optional: defaults to the sensor's keepalive_minutes
```

### `myhome.sync_time`

Synchronize gateway time with Home Assistant.

```yaml
action: myhome.sync_time
data:
  gateway: "00:03:50:AA:BB:CC"  # Optional
```

### `myhome.send_message`

Send raw OpenWebNet commands to the gateway. The frame must have the OpenWebNet
shape (`*…##`); it is then handed to `OWNd`'s typed parser, and — since 0.4.0 —
sent as a generic command when that parser has no type for it, so frames such as
a CEN+ virtual press (`*25*21#1*#2##`) go through. A frame that is not
well-formed fails with *"… is not a valid OpenWebNet command"* and nothing is
sent. If the queue is closed or full, the call fails with *"The gateway did not
accept the command …"*.

```yaml
action: myhome.send_message
data:
  gateway: "00:03:50:AA:BB:CC"  # Optional
  message: "*1*1*15##"  # Turn on light at address 15
```

| Field | Required | Notes |
|---|---|---|
| `message` | yes | A valid OpenWebNet frame, e.g. `*1*1*15##`. |
| `gateway` | only with more than one gateway loaded | MAC address in any notation. |

### `myhome.cover_calibration_run`

Moves a cover to one end stop, then runs it back for exactly the seconds a linear
*set position 50 %* would use and stops it there, so that you can measure where it
ended up. It is step 1
of [Recipes → Calibrating a shutter in
centimetres](recipes.md#calibrating-a-shutter-in-centimetres); on its own it changes
no configuration and stores nothing.

```yaml
action: myhome.cover_calibration_run
target:
  entity_id: cover.living_room_shutter
data:
  direction: close
```

| Field | Required | Notes |
|---|---|---|
| `direction` | yes | `close` or `open`. The direction of the run you are going to measure: `close` yields the `closing_roll`, `open` the `opening_roll`. |

**Target**: one or more **basic** covers (`integration: myhome`, `domain: cover`).
Several covers are done one after another, never in parallel — you have to be
standing in front of each one with a tape measure.

What it does to each cover, in order:

1. sends the **opposite** full command (`open_cover` for `direction: close`,
   `close_cover` for `direction: open`) and waits the configured run of that
   direction plus 3 seconds, so the cover is certainly against its end stop;
2. sends the requested direction and runs the motor for exactly the time a
   `set_cover_position: 50` would use with the current configuration and a linear
   model — `(closing_time - slat_time) / 2` for `close` (it starts from fully open,
   so no slat phase comes first), `slat_time + (opening_time - slat_time) / 2` for
   `open` (it starts from fully closed, so the slats open first), with `slat_time`
   at `0` when it is not set — counted from the moment the motor started, the
   actuator's own status when it sends one, `start_delay` after the frame otherwise —
   then sends `stop_cover`;
3. leaves the cover there and reports what it did.

The commands are the entity's own, so the position estimate, the echo filtering and
the safety timers see this run like any other movement.

Response data, keyed by entity id:

| Key | Value |
|---|---|
| `direction` | The direction that was run. |
| `motor_seconds` | The seconds the motor really ran: from the actuator's own "moving" status to its own "stopped", when it sends them, and otherwise from the write of the direction frame plus `start_delay` to the write of the stop plus `stop_latency`. With an idle command queue and an actuator that behaves as configured it is the figure from the formulas above; anything else — a busy queue, a motor slower to start than `start_delay` — makes it the figure the shutter really travelled, which is the one `cover_calibration_compute` must be given. |
| `opening_time`, `closing_time`, `slat_time` | The times the cover is configured with — the ones the maths of `cover_calibration_compute` will use. `slat_time` is reported, never solved for: it is the configured value. |

Refused with a `ServiceValidationError`, naming the entity:

- on an `advanced:` cover — it reports its own position, there is nothing to
  calibrate;
- on a cover that is already moving.

It fails with a `HomeAssistantError`, naming the entity, when one of its own frames
never reaches the bus (the command queue refused it, its time to live expired, the
gateway never answered): a run whose direction frame or whose stop was lost has no
interval to report, and reporting the seconds it *meant* to run would send you off to
measure a shutter that did not move, or did not stop. It waits for each of its frames
to be either written or dropped for as long as that can take — the **Command queue
TTL** plus the whole budget of one command, about 100 seconds with the defaults —
before giving up on it, so a busy queue in front of the run delays it rather than
failing it.

> The cover runs to a **full end stop and back**, twice the length of a normal
> command. Make sure nothing is in the way, above or below.

### `myhome.cover_calibration_compute`

Turns the centimetres you measured into roll coefficients — one per direction
measured — and hands back a ready-to-paste YAML snippet. It computes only: no cover
is moved and nothing is written to `myhome.yaml`.

```yaml
action: myhome.cover_calibration_compute
target:
  entity_id: cover.living_room_shutter
data:
  height: 195
  closed_half_cm: 85
  opened_half_cm: 80
```

| Field | Required | Notes |
|---|---|---|
| `height` | yes | Curtain travel height of that cover in centimetres, floor to fully open. |
| `closed_half_cm` | yes | Centimetres from the floor to the bottom edge after `cover_calibration_run` with `direction: close`. Between `0` and `height`. It is what yields the `closing_roll`. |
| `opened_half_cm` | no | The same measurement after `direction: open`, and what yields the `opening_roll`. Leave it out and only the descent is described; the resulting coefficient is then used in both directions. |
| `slat_time` | no | The slat time in seconds, when you have stopwatched a better value than the one on the cover. It is **always** a given quantity, never solved for: without this field the cover's configured `slat_time` is used. |
| `closed_run_seconds`, `opened_run_seconds` | no | The `motor_seconds` the two runs reported. Leave them out and the same formula the run uses is applied to the cover's *current* configuration — which is why the YAML must not change between the run and this action. |

**Target**: exactly **one** basic cover. The maths needs that cover's configured
`opening_time` and `closing_time` — the same numbers the run used — so a second
entity would have nothing to do with the measurements.

Each direction is one equation in one unknown, solved by bisection and independent
of the other: the descent measurement fixes the `closing_roll`, the ascent
measurement the `opening_roll`. Neither is a check on the other, and neither
determines the slat time.

Response data:

| Key | Value |
|---|---|
| `closing_roll` | The coefficient solved from `closed_half_cm`, rounded to 0.01. |
| `opening_roll` | The coefficient solved from `opened_half_cm`, rounded to 0.01. Absent when the ascent was not measured. |
| `roll` | The mean of the two, or the closing one alone when only the descent was measured. The single number to write when the directions agree. |
| `slat_time` | The slat time the maths used: the field you passed, or the cover's own. Seconds, rounded to 0.1. |
| `opening_time`, `closing_time` | The times the solution was computed against, unchanged. |
| `height` | The height you passed, echoed back. |
| `closed_run_seconds`, `opened_run_seconds` | The motor seconds each equation was built on — the fields you passed, or the values recomputed from the cover's configuration. |
| `yaml` | A `cover_profiles:` entry built from the result, plus the `profile:` / `height:` lines for the cover itself, ready to paste into `myhome.yaml`. It writes a single `roll:` when the two coefficients differ by at most `0.1`, and `opening_roll:` / `closing_roll:` (with no `roll:`) when they differ by more. |

Refused with a `ServiceValidationError` when a measurement lies outside what the
model can reach: no coefficient in the accepted range (`1.0` to `5.0`), with those
run times and that height, puts the bottom edge where you say it was. The message
names the measurement — the descent or the ascent — and gives the band of
centimetres that direction can actually produce, so you can see at once whether you
mistyped a number or the cover did not start from its end stop. Repeating
`cover_calibration_run` for that direction, after checking that nothing stopped the
cover early, is the usual fix.

With more than one gateway loaded, every gateway-targeted service above requires
the `gateway` field — omitting it fails with *"Specify the gateway: N gateways are
loaded."* `myhome.start_sending_instant_power` and the two cover calibration
services target entities instead, so they need no `gateway`. See
[Recipes → Several gateways](recipes.md#several-gateways).

Both calibration services **return data**: call them from *Developer tools →
Actions* to read the response there, or with `response_variable:` in a script.

## Events

### Device discovery events

- `myhome_device_discovered`: fired when a new device is found. Data: `platform`,
  `discovered_device`, `config_entry_id`, `gateway_mac`. `platform` is the section the
  device would be declared under (`light`, `cover`, `sensor`, `binary_sensor`,
  `climate`), `event` for a CEN/CEN+ scenario control, which is reported but never
  suggested, or `null` for a device family this integration has no section for
  (alarm devices). A lighting actuator is always reported as `light`, never as
  `switch`: nothing on the bus says which of the two you want. `discovered_device`
  carries an `interface` key as well — the F422 local bus interface of the device,
  unpadded, and `null` for a device on the main bus. It also carries a `category` — a
  coarse grouping of the device family, one of `lighting`, `automation`, `energy`,
  `thermoregulation`, `scenario`, `auxiliary` or `alarm`. (`generic` exists as a
  defensive fallback in the code; no frame a run can see produces it.)
  `discovered_device` also carries `unique_id`, `name`, `device_type`, `who`, `where`
  and a `properties` mapping. `properties` always holds `ownId` (the address as the
  bus writes it, `1*11#4#3`), `where`, `discovered_at`, `message_type` and
  `message_str`, and adds what the frame happened to say: `dimmable` (with
  `brightness`, or with a `note` naming `dimmable: true` when the actuator only
  answered ON/OFF) on a lighting frame, `shutter_type` on an automation frame,
  `meter_type` (with `power` when the frame carries one) on an energy frame, and
  `thermo_type` plus the `temperature` reading on a WHO 4 frame.
- `myhome_discovery_completed`: fired when a discovery run finishes (`myhome.stop_discovery`
  or the 60-second timeout). Data: `gateway_mac`, `reason` (`stopped` when the service
  ended the run, `timeout` when it ran out), `discovered_count` and
  `discovered_devices` — the list of `{mac}-{device key}` unique ids seen during the
  run, suggested or not (`00:03:50:11:22:33-1-11`, or
  `00:03:50:11:22:33-1-11#4#03` behind a bus interface, `…-4-#0` for a
  thermoregulation central unit). A CEN / CEN+ scenario control is the exception: it
  is listed as `{mac}-25-<where>` / `{mac}-15-<where>`, built from the frame's WHO and
  WHERE, while the device registry identifier of the same keypad once declared is
  `{mac}-cenplus-<object>` / `{mac}-cen-<where>` (and its entity `unique_id`
  `{mac}-cenplus-<object>-event`). For `*25*21#3*225##` on gateway
  `00:03:50:11:22:33` the run publishes `00:03:50:11:22:33-25-225`, while the same
  keypad declared as `object: 25` is `00:03:50:11:22:33-cenplus-25` in the registry —
  the same number, a different string. Looking a keypad up in the registry by the id
  discovery published therefore finds nothing, and an alarm device has no registry
  entry at all.

See [Discovery](discovery.md) for what triggers these and what they write.

### CEN+ keypad events

`myhome_cenplus_event` fires on CEN+ scenario control activity. The event data has
exactly four keys:

| Key | Type | Value |
|---|---|---|
| `object` | integer | The CEN+ object address: the frame's WHERE without its leading `2` (WHERE `225` → `object: 25`, WHERE `2100` → `object: 100`). A CEN+ *command* addresses the same control as `#25`, but an event never carries that form. |
| `pushbutton` | integer | The button number on that object. |
| `event` | string | One of the values in the table below. |
| `mac` | string | MAC address of the gateway that saw the frame, normalised (`00:03:50:aa:bb:cc`). **Added in 0.4.0.** |

`mac` is an **additive** change: the three original keys are untouched, so every
automation written before 0.4.0 keeps matching. It exists so that two gateways which
can both produce the same `object`/`pushbutton` pair can be told apart — a filter the
[device triggers](#device-triggers-and-event-entities) always apply.

| `event` value | OpenWebNet WHAT | Fired when |
|---|---|---|
| `pushbutton_short_press` | 21 | The button is pressed briefly. |
| `pushbutton_long_press` | 22 | The button starts being held. Fired **once**. |
| `pushbutton_long_press_repeat` | 23 | Fired repeatedly while the button stays held. |
| `pushbutton_long_release` | 24 | The button is released. |
| `rotate_cw_slow` | 25 | Rotary control turned slowly clockwise. |
| `rotate_cw_fast` | 26 | Rotary control turned quickly clockwise. |
| `rotate_ccw_slow` | 27 | Rotary control turned slowly counter-clockwise. |
| `rotate_ccw_fast` | 28 | Rotary control turned quickly counter-clockwise. |

Any CEN+ frame that maps to none of these is ignored and logged at DEBUG. Copy-paste
automations for each value: [Recipes → CEN+ keypads](recipes.md#cen-keypads).

### CEN keypad events

Classic (non-plus) CEN controls fire `myhome_cen_event` with the same four keys
(`object`, `pushbutton`, `event`, `mac`) and a shorter list of values. `object`
carries the CEN WHERE as an integer, and `pushbutton` the frame's WHAT, which on
CEN *is* the button number (`*15*<pushbutton>*<where>##`).

The four names are the same strings CEN+ uses, but a CEN keypad reports a
different gesture with each of them:

| CEN frame | `event` value | Fired when |
|---|---|---|
| `*15*N*<where>##` | `pushbutton_short_press` | Button N is **pressed** — sent at the start of a long press too, not only for a tap. |
| `*15*N#1*<where>##` | `pushbutton_short_release` | Button N is released after a short press. This is the frame that means "the user tapped the button". |
| `*15*N#3*<where>##` | `pushbutton_long_press` | Extended pressure. It repeats while the button stays held (there is no separate "repeat" event as on CEN+). |
| `*15*N#2*<where>##` | `pushbutton_long_release` | Button N is released after an extended press. |

So on CEN, use **`pushbutton_short_release`** for "the user tapped the button":
`pushbutton_short_press` also fires at the start of every long press, and an
automation triggered on `pushbutton_long_press` with the default `mode: single`
will log "already running" while the button is held — use `mode: queued` (or
`mode: single` with `max_exceeded: silent`) there.

See [Recipes → CEN keypads](recipes.md#cen-keypads-1) for an example.

### Device triggers and event entities

Since **0.4.0**, a CEN/CEN+ control declared under `scenario_control:` in
`myhome.yaml` (see
[Configuration → Scenario control](configuration.md#scenario-control-cen--cen))
also becomes a **device** with:

- one **event entity** (`event.<name>_scenario_control`) whose state is the timestamp
  of the last press, with attributes `event_type` (the same string as the bus event's
  `event`), `pushbutton`, `protocol`, `buttons` (the declared list) and `object`
  (CEN+) / `where` (CEN);
- **device triggers**, one per declared button and event name, usable from the
  automation editor ("Button 2 held down"). They are implemented on top of the bus
  events above and match on `mac`, `object`, `pushbutton` and `event`, so they are
  exactly as reliable as a hand-written event trigger, with the gateway filter added.

A device trigger is **validated when the automation is loaded**, and refused with a
message naming the device when it can never fire:

| Refused | Message | Previously |
|---|---|---|
| The device is not a declared scenario control (a light, a cover, the gateway) | *Device `<id>` is not a MyHOME CEN/CEN+ scenario control* | Accepted; the automation showed as *on* and never fired. |
| The event name is not one this control's protocol can fire — the four rotary events and `pushbutton_long_press_repeat` on a **CEN** control | *`<type>` is not an event a MyHOME `<protocol>` scenario control can fire (device `<id>`)* | Accepted silently. |
| The button number is outside the protocol's range — CEN+ buttons are `1`-`32`, CEN buttons are `0`-`31` | The same shape of message, naming the button and the protocol | Accepted silently. |

All three used to validate and stay quiet, so a hand-written trigger with the wrong
type or button number now turns the automation red on the next reload instead of
never running. The button is checked against the **protocol's** range, not against
the control's `buttons:` list: `buttons:` only decides what the picker offers, and a
press on an undeclared button is still delivered.

Both the event entity and the device triggers are strictly additive: an undeclared
control fires the bus events and nothing else, as in 0.3.x. See
[Recipes → Device triggers and blueprints](recipes.md#device-triggers-and-blueprints).

### General/area/group bus events

Fired when a General/Area/Group lighting or automation command is seen on the bus
(e.g. someone uses a physical "all lights off" button); data includes the raw
`message` and, where applicable, the `area`/`group` address.

- `myhome_general_light_event`, `myhome_area_light_event`, `myhome_group_light_event`
  (WHO 1, lighting)
- `myhome_general_automation_event`, `myhome_area_automation_event`, `myhome_group_automation_event`
  (WHO 2, automation/covers)

| Event | Keys |
|---|---|
| `myhome_general_light_event` | `message`, `event` (`on` / `off`) |
| `myhome_area_light_event` | `message`, `area`, `event` |
| `myhome_group_light_event` | `message`, `group`, `event` |
| `myhome_general_automation_event` | `message`, `event` (`open` / `close` / `stop`) |
| `myhome_area_automation_event` | `message`, `area`, `event` |
| `myhome_group_automation_event` | `message`, `group`, `event` |

The two `general` events carry no address key at all: a general frame addresses the
whole plant, so there is nothing to report beyond the raw `message`.

For **lighting** general and area frames the integration also re-requests the
affected states, so `light` entities follow along on their own. A **group** frame
fires the event only — a group has no WHERE to poll — and so do all three
**automation** events, because covers report their own movement as it happens. See
[Recipes → Raw OpenWebNet commands](recipes.md#raw-openwebnet-commands) for a
`myhome.send_message` example that triggers one of these.

### Wall pushbutton events (`myhome_light_pushbutton_event`)

When someone presses a physical light pushbutton, the gateway echoes the command the
button sent (`*1*1000#WHAT*WHERE##`, a "command translation") right before the
actuator answers with its status. The status drives the `light` entity; the
translation is republished as `myhome_light_pushbutton_event` so that the press itself
can be acted on. Data:

| key       | value                                                                 |
|-----------|-----------------------------------------------------------------------|
| `mac`     | gateway MAC (as in the CEN/CEN+ events)                               |
| `where`   | the WHERE the button is addressed to, exactly as it appears on the bus, as a string: `"42"` on the main bus, `"11#4#3"` behind a local bus interface, `"0"` / `"3"` for a general or area button. Compare with `startswith` if the interface does not matter to you. |
| `what`    | the original WHAT, as an integer                                      |
| `event`   | `on`, `off`, `dim_up` (WHAT 30), `dim_down` (31), `dim_to_<pct>` for WHAT 2-10, where `<pct>` is WHAT × 10 (`dim_to_20` … `dim_to_100`), otherwise `what_<n>` |
| `message` | the raw frame                                                         |

The event is fired whether or not "Generate events for every bus message" is
enabled (that option only concerns `myhome_message_event`).

The interesting case is a pushbutton configured in **dimmer mode** and wired to a
relay: a short press gives `on`/`off` (and the light entity follows on its own), a
**hold** gives one `dim_up` or `dim_down` every ~0.5 s for as long as the button is
held, alternating direction between holds. The relay ignores those frames, so this
event is their only trace: it turns a plain BTicino pushbutton into a dimming remote for
anything in Home Assistant. A WHERE with no actuator behind it (a "virtual" light
declared in `myhome.yaml` just to follow a button) works the same way. See
[Recipes → Wall pushbuttons in dimmer mode](recipes.md#wall-pushbuttons-in-dimmer-mode).

### Raw bus traffic (`myhome_message_event`)

`myhome_message_event` re-publishes every frame the **monitor session** receives
onto the Home Assistant event bus. It is **off by default** — enable it with the
**"Generate events in Home Assistant for each message received"** integration
option (see [Configuration → Options](configuration.md#options)) if you want to
build automations directly on raw bus traffic; expect a lot of events on a busy
plant.

Event data for a frame `OWNd` could parse:

| Key | Always present | Value |
|---|---|---|
| `gateway` | yes | The gateway host (address), as a string. |
| `message` | yes | The raw frame, e.g. `*1*1*11##`. |
| `family` | yes | Frame family, e.g. `Event`, `Request`, `Command translation`. |
| `type` | yes | Message type, e.g. `Status`, `Dimension request`. |
| `who` | yes | The WHO as an integer. |
| `where`, `interface`, `where parameters`, `what`, `what parameters`, `dimension`, `dimension parameters`, `dimension values` | no | Present only when the frame carries them **and the value is non-zero**: `OWNd` omits a key whose value is `0`, so a light switching off (`*1*0*11##`) arrives with no `what` at all. Read them with `trigger.event.data.get('what')`, never with `trigger.event.data.what`. |

For a frame `OWNd` could **not** parse, only `gateway` and `message` (the raw
text) are present.

Replies read on the **command** session are dispatched to entities but do **not**
produce `myhome_message_event`. Only monitor traffic does. See
[Recipes → Debugging with raw bus events](recipes.md#debugging-with-raw-bus-events)
for watching the bus live and logging unmapped addresses.

### Example event automation

```yaml
automation:
  - alias: "Scene Button Pressed"
    triggers:
      - trigger: event
        event_type: myhome_cenplus_event
        event_data:
          object: 25
          pushbutton: 1
          event: pushbutton_short_press
          # mac: "00:03:50:AA:BB:CC"   # optional, only useful with several gateways
    actions:
      - action: scene.turn_on
        target:
          entity_id: scene.evening_lights
```
