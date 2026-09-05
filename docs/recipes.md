# Recipes

Copy-paste examples for things the integration can do. Every event name, event
data key, service field and YAML key below is taken from the code, not from
memory.

Automations use the current Home Assistant syntax (`triggers:` / `conditions:` /
`actions:`), which this integration's minimum version (2026.8.0) supports. The
older `trigger:` / `action:` spelling still works if you prefer it.

## Contents

- [CEN+ keypads](#cen-keypads)
- [CEN keypads](#cen-keypads-1)
- [Raw OpenWebNet commands](#raw-openwebnet-commands)
- [Covers](#covers)
- [Energy](#energy)
- [Lock/Unlock buttons](#lockunlock-buttons)
- [Several gateways](#several-gateways)
- [Debugging with raw bus events](#debugging-with-raw-bus-events)

## CEN+ keypads

CEN+ scenario controls fire `myhome_cenplus_event`. See
[Services and events → CEN+ keypad events](services-and-events.md#cen-keypad-events)
for the full event data contract (`object`, `pushbutton`, `event`, and every
`event` value with its OpenWebNet WHAT).

### Short press → run a scene

```yaml
automation:
  - alias: "CEN+ 1/1 short press: evening scene"
    triggers:
      - trigger: event
        event_type: myhome_cenplus_event
        event_data:
          object: 1
          pushbutton: 1
          event: pushbutton_short_press
    actions:
      - action: scene.turn_on
        target:
          entity_id: scene.evening_lights
```

### Long press → a different action from the short press

`pushbutton_long_press` fires once, at the moment the button starts being held, so
it is safe to use for a one-shot action.

```yaml
automation:
  - alias: "CEN+ 1/1 long press: everything off"
    triggers:
      - trigger: event
        event_type: myhome_cenplus_event
        event_data:
          object: 1
          pushbutton: 1
          event: pushbutton_long_press
    actions:
      - action: light.turn_off
        target:
          entity_id: all
```

### Hold to dim (long press repeat)

`pushbutton_long_press_repeat` fires again and again while the button is held. Use
`mode: queued` with a small `max` so a long hold does not pile up hundreds of
pending runs.

```yaml
automation:
  - alias: "CEN+ 1/2 hold: dim up"
    mode: queued
    max: 5
    triggers:
      - trigger: event
        event_type: myhome_cenplus_event
        event_data:
          object: 1
          pushbutton: 2
          event: pushbutton_long_press_repeat
    actions:
      - action: light.turn_on
        target:
          entity_id: light.accent_lighting
        data:
          brightness_step_pct: 10
```

### Release → stop what the hold was doing

```yaml
automation:
  - alias: "CEN+ 1/2 release: stop the cover"
    triggers:
      - trigger: event
        event_type: myhome_cenplus_event
        event_data:
          object: 1
          pushbutton: 2
          event: pushbutton_long_release
    actions:
      - action: cover.stop_cover
        target:
          entity_id: cover.living_room_shutter
```

### Rotation → volume, brightness, temperature

One automation for all four rotation values, using a template to pick the step.

```yaml
automation:
  - alias: "CEN+ rotary 3: brightness"
    triggers:
      - trigger: event
        event_type: myhome_cenplus_event
        event_data:
          object: 3
          pushbutton: 1
    conditions:
      - condition: template
        value_template: >
          {{ trigger.event.data.event.startswith('rotate_') }}
    actions:
      - action: light.turn_on
        target:
          entity_id: light.kitchen_light
        data:
          brightness_step_pct: >
            {% set e = trigger.event.data.event %}
            {% if e == 'rotate_cw_fast' %}20
            {% elif e == 'rotate_cw_slow' %}5
            {% elif e == 'rotate_ccw_fast' %}-20
            {% else %}-5
            {% endif %}
```

## CEN keypads

Classic (non-plus) CEN controls fire `myhome_cen_event`. See
[Services and events → CEN keypad events](services-and-events.md#cen-keypad-events-1)
for the event data contract.

```yaml
automation:
  - alias: "CEN 5/3 pressed"
    triggers:
      - trigger: event
        event_type: myhome_cen_event
        event_data:
          object: 5
          pushbutton: 3
          event: pushbutton_short_press
    actions:
      - action: script.turn_on
        target:
          entity_id: script.leaving_home
```

## Raw OpenWebNet commands

`myhome.send_message` queues an arbitrary frame. See
[Services and events → myhome.send_message](services-and-events.md#myhomesend_message)
for the field reference and error messages.

### Activate a scenario (WHO 0)

```yaml
script:
  evening_scenario:
    sequence:
      - action: myhome.send_message
        data:
          message: "*0*1*01##"   # scenario 1 on scenario module 01
```

### General OFF for all lights (WHO 1, WHERE 0)

```yaml
script:
  all_lights_off_on_the_bus:
    sequence:
      - action: myhome.send_message
        data:
          message: "*1*0*0##"
```

The integration recognises general/area/group frames coming back on the bus and
re-requests the affected states, so your `light` entities follow along. It also
fires `myhome_general_light_event` (and `myhome_area_light_event` /
`myhome_group_light_event`) with `message` and `event: on|off`, plus `area` or
`group` where applicable.

### Sync the gateway clock

```yaml
automation:
  - alias: "MyHOME: sync gateway clock nightly"
    triggers:
      - trigger: time
        at: "03:30:00"
    actions:
      - action: myhome.sync_time
```

## Covers

### Time-based position on a basic actuator

Basic (non-`advanced`) WHO 2 actuators report only "opening", "closing" and
"stopped" — never a position. The integration estimates the position from
`shutter_run`, the number of seconds a full travel takes.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      class: shutter
      shutter_run: 30        # seconds for a full open→closed travel
```

Defaults and limits, from the validator: `shutter_run` defaults to `20` seconds
and must be at least `1`; `advanced` and `inverted` default to `false`; `class`
defaults to `shutter`.

Such covers are marked `assumed_state`, which is why the dashboard card shows
separate up/stop/down buttons rather than a toggle. While the cover moves, the
estimated position is pushed to Home Assistant once per second.

### `set_cover_position`

`set_cover_position` works on both kinds of actuator:

- **advanced**: the position is sent to the actuator directly.
- **basic**: the cover is started in the right direction and stopped by a timer
  after `|target − current| / 100 × shutter_run` seconds.

```yaml
script:
  shutters_half_open:
    sequence:
      - action: cover.set_cover_position
        target:
          entity_id: cover.living_room_shutter
        data:
          position: 50
```

If the position is not known yet (fresh install, nothing restored), a basic cover
runs to the nearest end instead — fully open for a target ≥ 50, fully closed
below — so that the estimate gets a reference point. Run one full open and one
full close after setting up a cover; from then on the estimate has a baseline and
is restored across restarts and reloads.

### `inverted`

Set `inverted: true` when the actuator is wired the other way round: it swaps
`raise`/`lower` on outgoing commands **and** swaps `is_opening`/`is_closing` on
incoming frames, so both directions stay consistent.

```yaml
      garage_blind:
        where: "84"
        name: "Garage Blind"
        inverted: true
        shutter_run: 18
```

### Tuning `shutter_run`

1. Set `shutter_run` to your best guess and reload the integration.
2. Close the cover fully (`cover.close_cover`), wait for it to stop moving on its
   own, then open it fully with a stopwatch running.
3. Set `shutter_run` to the measured seconds, save, reload.
4. Check `set_cover_position` at 50 %: if the cover consistently overshoots,
   `shutter_run` is too large; if it stops short, too small.

The value is exposed on the entity as the `Shutter run` attribute for basic
covers, so you can confirm what is actually loaded.

### "Movement started / movement finished" automation

Home Assistant's cover states are `opening`, `closing`, `open` and `closed`. The
integration sets `opening`/`closing` from the bus frames (for both basic and
advanced actuators), so a plain state trigger is enough.

```yaml
automation:
  - alias: "Shutter: movement started"
    triggers:
      - trigger: state
        entity_id: cover.living_room_shutter
        to:
          - opening
          - closing
    actions:
      - action: notify.persistent_notification
        data:
          message: >
            {{ state_attr('cover.living_room_shutter','friendly_name') }}
            started {{ trigger.to_state.state }}.

  - alias: "Shutter: movement finished"
    triggers:
      - trigger: state
        entity_id: cover.living_room_shutter
        from:
          - opening
          - closing
        to:
          - open
          - closed
    actions:
      - action: notify.persistent_notification
        data:
          message: >
            Shutter stopped at
            {{ state_attr('cover.living_room_shutter','current_position') }} %.
```

Note that `unavailable` is also a possible `to:` state when the gateway
connection drops; the `to:` lists above exclude it deliberately.

## Energy

Declare the meter with `class: power`. This creates the **Power** entity plus
three energy entities (today / this month / total):

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  sensor:
    house_main:
      where: "51"
      name: "House Main"
      class: power
```

The power entity is `sensor.house_main_power` (device class `power`, unit W, state
class `measurement`). For the full reference — the instant-power keep-alive
(`keepalive_minutes`), the push filter (`sensor_defaults`), why the
daily/monthly/total entities may stay `unknown` on some gateways, and how to
derive kWh with the `integration`/`utility_meter` helpers when they do — see
[Energy monitoring](energy.md).

## Lock/Unlock buttons

Since 0.2.0 the WHO 14 Lock/Unlock buttons are **opt-in per device**. Add
`lock_buttons: true` to a `light`, `switch` or `cover` entry:

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      lock_buttons: true
```

See [Configuration → Lock/Unlock buttons](configuration.md#lockunlock-buttons)
for the validator rules (which devices and WHERE forms are eligible).

The two entities are created with entity category *config*, so they appear under
**Configuration** on the device page rather than in the main controls. Pressing
**Lock** sends `*14*0*<where>##` (the actuator stops obeying bus commands);
**Unlock** sends `*14*1*<where>##`.

```yaml
automation:
  - alias: "Lock the shutter while the window is open"
    triggers:
      - trigger: state
        entity_id: binary_sensor.living_room_window
        to: "on"
    actions:
      - action: button.press
        target:
          entity_id: button.living_room_shutter_lock
```

## Several gateways

Every gateway needs its **own config entry** (discovered or added manually) and
its own root entry in `myhome.yaml`. Use the MAC address as the root key; a
`gateway:` block may coexist with MAC root keys as long as every MAC is unique.

```yaml
"00:03:50:AA:BB:CC":
  light:
    kitchen_light:
      where: "15"
      name: "Kitchen Light"

"00:03:50:DD:EE:FF":
  cover:
    garage_door:
      where: "25"
      name: "Garage Door"
      class: garage
```

With more than one gateway loaded, the gateway-level services require the
`gateway:` field — omitting it fails with *"Specify the gateway: N gateways are
loaded."*:

```yaml
      - action: myhome.send_message
        data:
          gateway: "00:03:50:DD:EE:FF"
          message: "*2*1*25##"
```

Any MAC notation is accepted (`00:03:50:aa:bb:cc`, `00-03-50-AA-BB-CC`,
`000350AABBCC`); it is normalised before being matched. This applies to
`myhome.send_message`, `myhome.sync_time`, `myhome.start_discovery` and
`myhome.stop_discovery`. `myhome.start_sending_instant_power` targets entities
instead, so it needs no `gateway`.

## Debugging with raw bus events

`myhome_message_event` re-publishes every frame the **monitor session** receives
onto the Home Assistant event bus. It is **off by default**. See
[Services and events → Raw bus traffic](services-and-events.md#raw-bus-traffic-myhome_message_event)
for the full event data contract.

Enable it in **Settings → Devices & services → MyHOME → Configure**, tick
*"Generate events in Home Assistant for each message received"* and save. Saving
the options reloads the integration.

### Watch the bus live

**Developer tools → Events → Listen to events**, type `myhome_message_event`,
press *Start listening*, then operate a physical switch. The WHERE in the frame is
what you put in `myhome.yaml`.

### Log the WHERE of everything unknown

```yaml
automation:
  - alias: "MyHOME: log unmapped WHO 1 addresses"
    mode: queued
    max: 50
    triggers:
      - trigger: event
        event_type: myhome_message_event
    conditions:
      - condition: template
        value_template: "{{ trigger.event.data.get('who') == 1 }}"
    actions:
      - action: logbook.log
        data:
          name: MyHOME bus
          message: >
            who={{ trigger.event.data.who }}
            where={{ trigger.event.data.get('where') }}
            what={{ trigger.event.data.get('what') }}
            raw={{ trigger.event.data.message }}
```

Turn the option back off when you are done: on a busy plant this fires a lot of
events, and every one of them is written to the recorder unless you exclude it.

An alternative that costs nothing at runtime is the built-in discovery:
`myhome.start_discovery` listens for 60 seconds and writes YAML suggestions for
everything it saw but you have not configured, into `myhome_discovered.yaml` next
to your `myhome.yaml`.
