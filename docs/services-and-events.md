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
  - [General/area/group bus events](#generalareagroup-bus-events)
  - [Raw bus traffic (`myhome_message_event`)](#raw-bus-traffic-myhome_message_event)

## Services

### `myhome.start_discovery`

Start automatic device discovery on a gateway. See [Discovery](discovery.md).

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
reconnection and every `keepalive_minutes - 5` minutes (see
[Configuration → Sensor](configuration.md#sensor)); use this service to force it,
or for a one-off/different duration.

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

Send raw OpenWebNet commands to the gateway. The frame is parsed by `OWNd` before
being sent; if it does not parse, or parses as invalid, the call fails with *"…
is not a valid OpenWebNet command"* and nothing is sent. If the queue is closed or
full, the call fails with *"The gateway did not accept the command …"*.

```yaml
service: myhome.send_message
data:
  gateway: "00:03:50:XX:XX:XX"  # Optional
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
  `discovered_device`, `config_entry_id`, `gateway_mac`.
- `myhome_discovery_completed`: fired when a discovery run finishes (`myhome.stop_discovery`
  or the 60-second timeout).

See [Discovery](discovery.md) for what triggers these and what they write.

### CEN+ keypad events

`myhome_cenplus_event` fires on CEN+ scenario control activity. The event data has
exactly three keys:

| Key | Type | Value |
|---|---|---|
| `object` | integer | The CEN+ object address (the WHERE without its leading `#`). |
| `pushbutton` | integer | The button number on that object. |
| `event` | string | One of the values in the table below. |

There is **no** `gateway` key on this event. If you run more than one gateway and
two of them can produce the same `object`/`pushbutton` pair, you cannot tell them
apart from the event alone.

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

Classic (non-plus) CEN controls fire `myhome_cen_event` with the same three keys
(`object`, `pushbutton`, `event`) and a shorter list of values:
`pushbutton_short_press`, `pushbutton_short_release`, `pushbutton_long_press`,
`pushbutton_long_release`. See [Recipes → CEN keypads](recipes.md#cen-keypads-1)
for an example.

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
| `where`, `interface`, `where parameters`, `what`, `what parameters`, `dimension`, `dimension parameters`, `dimension values` | no | Present only when the frame carries them. |

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
