# Services and events

The five services the integration registers, and the contract (event name and
data keys) of every event it fires. For copy-paste automations built on these,
see [Recipes](recipes.md).

## Contents

- [Services](#services)
  - [`myhome.start_discovery`](#myhomestart_discovery)
  - [`myhome.stop_discovery`](#myhomestop_discovery)
  - [`myhome.start_sending_instant_power`](#myhomestart_sending_instant_power)
  - [`myhome.sync_time`](#myhomesync_time)
  - [`myhome.send_message`](#myhomesend_message)
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

With more than one gateway loaded, every gateway-targeted service above requires
the `gateway` field — omitting it fails with *"Specify the gateway: N gateways are
loaded."* `myhome.start_sending_instant_power` targets entities instead, so it
needs no `gateway`. See [Recipes → Several gateways](recipes.md#several-gateways).

## Events

### Device discovery events

- `myhome_device_discovered`: fired when a new device is found. Data: `platform`,
  `discovered_device`, `config_entry_id`, `gateway_mac`. `platform` is the section the
  device would be declared under (`light`, `cover`, `switch`, `sensor`,
  `binary_sensor`, `climate`) or `event` for a CEN/CEN+ scenario control, which is
  reported but never suggested.
- `myhome_discovery_completed`: fired when a discovery run finishes (`myhome.stop_discovery`
  or the 60-second timeout).

See [Discovery](discovery.md) for what triggers these and what they write.

### CEN+ keypad events

`myhome_cenplus_event` fires on CEN+ scenario control activity. The event data has
exactly four keys:

| Key | Type | Value |
|---|---|---|
| `object` | integer | The CEN+ object address: the frame's WHERE without its leading `#` (WHERE `#25` → `object: 25`). |
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

Both are strictly additive: an undeclared control fires the bus events and nothing
else, as in 0.3.x. See
[Recipes → Device triggers and blueprints](recipes.md#device-triggers-and-blueprints).

### General/area/group bus events

Fired when a General/Area/Group lighting or automation command is seen on the bus
(e.g. someone uses a physical "all lights off" button); data includes the raw
`message` and, where applicable, the `area`/`group` address.

- `myhome_general_light_event`, `myhome_area_light_event`, `myhome_group_light_event`
  (WHO 1, lighting)
- `myhome_general_automation_event`, `myhome_area_automation_event`, `myhome_group_automation_event`
  (WHO 2, automation/covers)

The integration also re-requests the affected entity states when it sees these
frames, so `light`/`cover` entities follow along on their own. See
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
| `event`   | `on`, `off`, `dim_up` (WHAT 30), `dim_down` (31), `dim_to_<pct>` (2-10), otherwise `what_<n>` |
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
