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
- [Device triggers and blueprints](#device-triggers-and-blueprints)
- [Wall pushbuttons in dimmer mode](#wall-pushbuttons-in-dimmer-mode)
- [Raw OpenWebNet commands](#raw-openwebnet-commands)
- [Covers](#covers)
- [Energy](#energy)
- [Lock/Unlock buttons](#lockunlock-buttons)
- [Several gateways](#several-gateways)
- [Debugging with raw bus events](#debugging-with-raw-bus-events)

## CEN+ keypads

CEN+ scenario controls fire `myhome_cenplus_event`. See
[Services and events → CEN+ keypad events](services-and-events.md#cen-keypad-events)
for the full event data contract (`object`, `pushbutton`, `event`, `mac`, and every
`event` value with its OpenWebNet WHAT).

The event triggers below always work, whether or not the control is declared in
`myhome.yaml`. If you would rather build these automations from the UI, declare the
control under `scenario_control:` and use the
[device triggers](#device-triggers-and-blueprints) instead — same events, two
dropdowns.

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

Classic (non-plus) CEN controls fire `myhome_cen_event`, whose `object` key carries
the CEN WHERE. See
[Services and events → CEN keypad events](services-and-events.md#cen-keypad-events-1)
for the event data contract; CEN controls support the same
[device triggers](#device-triggers-and-blueprints) with `protocol: cen`.

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

## Device triggers and blueprints

Declaring a keypad under `scenario_control:` (see
[Configuration → Scenario control](configuration.md#scenario-control-cen--cen))
turns it into a device, and its buttons then appear in **Settings → Automations →
Create automation → Add trigger → Device**.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  scenario_control:
    keypad_living_room:
      object: 25
      name: "Living Room Keypad"
      buttons: [1, 2, 3, 4]
```

The trigger the UI writes looks like this — `device_id` is the registry id of the
keypad, which you normally never type by hand:

```yaml
automation:
  - alias: "Living room keypad, button 2 held"
    triggers:
      - trigger: device
        domain: myhome
        device_id: 0123456789abcdef0123456789abcdef
        type: pushbutton_long_press
        subtype: button_2
    actions:
      - action: light.turn_off
        target:
          entity_id: light.living_room
```

`type` is any event name of the control's protocol and `subtype` is `button_<n>`
for any button in the device's `buttons` list; both are the same values the bus
event carries, so a device trigger and an event trigger are interchangeable.

The same control also gets an event entity, useful in templates and history:

```yaml
automation:
  - alias: "Any press on the living room keypad"
    triggers:
      - trigger: state
        entity_id: event.living_room_keypad_scenario_control
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.event_type == 'pushbutton_short_press' }}"
    actions:
      - action: notify.persistent_notification
        data:
          message: "Button {{ trigger.to_state.attributes.pushbutton }} pressed"
```

### Importing the blueprints

Two ready-made blueprints ship in the repository. HACS does not install
blueprints, so import them by URL: **Settings → Automations & scenes →
Blueprints → Import blueprint**, and paste

```
https://github.com/Interstellar0verdrive/MyHOME-stability/blob/master/blueprints/automation/myhome/cenplus_button_light.yaml
https://github.com/Interstellar0verdrive/MyHOME-stability/blob/master/blueprints/automation/myhome/cenplus_button_cover.yaml
```

| Blueprint | What it does |
|---|---|
| `cenplus_button_light.yaml` | One CEN+ button drives one light: short press toggles, holding turns it off. |
| `cenplus_button_cover.yaml` | Two CEN+ buttons drive one cover: hold up/down to open/close, short press on either to stop. |

Both ask for the scenario-control device, the button(s) and the target entity;
the control must be declared in `myhome.yaml` first, otherwise there is no device
to pick.

## Wall pushbuttons in dimmer mode

A BTicino light pushbutton can be configured (installer app) in **dimmer mode**: a
short press still sends on/off, but while it is held it keeps sending "one step up" /
"one step down" frames (WHAT 30/31, about two per second), alternating the direction
at every hold. Two very different situations follow from that.

### A real dimmer: nothing to do

If the actuator behind the button is a dimmer (`dimmable: true` in `myhome.yaml`),
the hold dims the light on the bus and the actuator broadcasts its level: the
`light` entity follows on its own, brightness included. Home Assistant and the
BTicino side stay in sync without any automation, exactly as for on/off.

### A relay behind a dimmer-mode button: the hold becomes a free gesture

If the actuator is a relay, the "step" frames do nothing physically, but the
integration republishes them as
[`myhome_light_pushbutton_event`](services-and-events.md#wall-pushbutton-events-myhome_light_pushbutton_event)
(`where`, `event: dim_up` / `dim_down`). A plain wall button gets a second gesture
that Home Assistant can attach to anything. Two things to know first:

- the hold **always turns the button's own light on** (the pushbutton sends "on"
  before the first step; the relay obeys). Automations should treat that as a given;
- the button, not the light, decides the up/down direction, and it alternates at
  every hold. Unless you drive a real dimmer, ignore `dim_up` vs `dim_down` and
  decide in the automation.

#### Example 1: hold to dim a Zigbee bulb

A bedside pushbutton whose WHERE has no useful relay drives a Zigbee bulb: short
press on/off is kept in sync by two state automations (see the CEN+ recipes for the
shape), the hold dims. Each frame moves the bulb by 10 %, so a three-second hold
spans most of the range.

```yaml
automation:
  - alias: "Bedside pushbutton: hold to dim the Zigbee bulb"
    mode: queued
    max: 5
    triggers:
      - trigger: event
        event_type: myhome_light_pushbutton_event
        event_data:
          where: "42"
          event: dim_up
        id: up
      - trigger: event
        event_type: myhome_light_pushbutton_event
        event_data:
          where: "42"
          event: dim_down
        id: down
    conditions:
      - condition: state
        entity_id: light.bedside_bulb
        state: "on"
    actions:
      - action: light.turn_on
        target:
          entity_id: light.bedside_bulb
        data:
          brightness_step_pct: "{{ 10 if trigger.id == 'up' else -10 }}"
```

#### Example 2: hold on any light = the whole room

With every wall button in dimmer mode, each light gets a "room" gesture. The rule
that turned out to be the least surprising in daily use is a two-stage hold:

- room **completely on** → the hold switches it all off;
- **anything off** → the hold switches it all on; keep holding and it all goes off.

The pressed light counts as it is at decision time, i.e. on (the hold itself
switched it on), so if it was the only light off the room is "complete" and the hold
switches everything off: to switch on just that light, a short press is enough.

The frames keep coming every 0.5 s while the button is held, so the automation
counts the frames of one hold (same WHERE, frames less than 1 s apart) and acts only
at the threshold frame (five frames ≈ 2.5 s) and, for the second stage, at twice
that. One automation with a `WHERE → group` table covers the house.

```yaml
input_number:
  hold_seconds:
    min: 0.5
    max: 6
    step: 0.5
    initial: 2.5
  hold_frames:
    min: 0
    max: 1000
    step: 1
    mode: box
  hold_last_frame:
    min: 0
    max: 4102444800
    step: 0.001
    mode: box
input_text:
  hold_last_where:
    max: 10
  hold_stage:
    max: 10

automation:
  - alias: "Hold on a wall button drives its room"
    mode: queued
    max: 10
    triggers:
      - trigger: event
        event_type: myhome_light_pushbutton_event
        event_data:
          event: dim_up
      - trigger: event
        event_type: myhome_light_pushbutton_event
        event_data:
          event: dim_down
    variables:
      where: "{{ trigger.event.data.where }}"
      # WHERE -> [pressed light, light group to command, group to read the room state]
      rooms:
        "11": [light.hall, light.living_room, group.living_room]
        "12": [light.sofa, light.living_room, group.living_room]
        "13": [light.kitchen_ceiling, light.kitchen, group.kitchen]
        "41": [light.kitchen_strip, light.kitchen, group.kitchen]
    conditions:
      # HA turns "11" into a number when rendering: compare as a string
      - condition: template
        value_template: "{{ (where | string) in rooms }}"
    actions:
      - variables:
          light: "{{ rooms[where | string][0] }}"
          room: "{{ rooms[where | string][1] }}"
          room_state: "{{ rooms[where | string][2] }}"
          now_ts: "{{ as_timestamp(now()) }}"
          new_hold: >-
            {{ (now_ts - states('input_number.hold_last_frame') | float(0)) > 1.0
               or states('input_text.hold_last_where') != (where | string) }}
          others_all_on: >-
            {{ expand(room_state) | rejectattr('entity_id', 'eq', light)
               | rejectattr('state', 'eq', 'on') | list | count == 0 }}
          count: "{{ 1 if new_hold else (states('input_number.hold_frames') | int(0)) + 1 }}"
          threshold: "{{ [((states('input_number.hold_seconds') | float(2.5)) / 0.5) | round(0) | int, 1] | max }}"
          stage: "{{ '' if new_hold else states('input_text.hold_stage') }}"
      - action: input_number.set_value
        target:
          entity_id: input_number.hold_last_frame
        data:
          value: "{{ now_ts }}"
      - action: input_text.set_value
        target:
          entity_id: input_text.hold_last_where
        data:
          value: "{{ where }}"
      - action: input_number.set_value
        target:
          entity_id: input_number.hold_frames
        data:
          value: "{{ count }}"
      - if:
          - condition: template
            value_template: "{{ new_hold }}"
        then:
          - action: input_text.set_value
            target:
              entity_id: input_text.hold_stage
            data:
              value: ""
      - choose:
          - conditions: "{{ count == threshold }}"
            sequence:
              - if:
                  - condition: template
                    value_template: "{{ others_all_on }}"
                then:
                  - action: light.turn_off
                    target:
                      entity_id: "{{ room }}"
                  - action: input_text.set_value
                    target:
                      entity_id: input_text.hold_stage
                    data:
                      value: "off"
                else:
                  - action: light.turn_on
                    target:
                      entity_id: "{{ room }}"
                  - action: input_text.set_value
                    target:
                      entity_id: input_text.hold_stage
                    data:
                      value: "on"
          - conditions: "{{ count == threshold * 2 and stage == 'on' }}"
            sequence:
              - action: light.turn_off
                target:
                  entity_id: "{{ room }}"
              - action: input_text.set_value
                target:
                  entity_id: input_text.hold_stage
                data:
                  value: "off"
```

Map a button to a scene instead of a group if you prefer. The LEDs on every keypad
follow the actuators, so whatever Home Assistant switches on the bus is reflected on
the wall without extra work.

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
and must be at least `1`; `slat_time` defaults to `0` (two-phase model off) and
must leave at least one second of curtain travel in both directions;
`opening_time` and `closing_time` default to `shutter_run`; `advanced` and
`inverted` default to `false`; `class` defaults to `shutter`.

Such covers are marked `assumed_state`, which is why the dashboard card shows
separate up/stop/down buttons rather than a toggle. While the cover moves, the
estimated position is pushed to Home Assistant once per second.

### Slats and curtain: `slat_time`

On a real roller shutter the first seconds of an upward run only tilt the slats
("lamelle") open, without lifting anything, and a downward run keeps going for the
same few seconds after the curtain has touched the floor. Declare those seconds as
`slat_time` and the position stops lying:

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      shutter_run: 30
      slat_time: 3         # 3 s of slats + 27 s of curtain, each way
```

`current_position` then counts the **curtain** only (0 = on the floor, 100 = up) and
`current_tilt_position` the **slats** (0 = closed, 100 = open); the entity is
`closed` only when both are 0. The full model, and how to measure the two numbers,
is in
[Configuration → The two-phase travel model](configuration.md#the-two-phase-travel-model-slat_time).

If the motor is measurably slower in one direction, replace `shutter_run` with
`opening_time` and `closing_time` (`shutter_run` stays the fallback for both):

```yaml
      bedroom_shutter:
        where: "82"
        name: "Bedroom Shutter"
        slat_time: 3
        opening_time: 32
        closing_time: 28
```

### Closed, with the slats open

The classic night position: curtain all the way down, slats open for a bit of air
and light. It needs `slat_time` (the tilt services only exist with it) and is a
single service call — the cover runs up for `slat_time` seconds and stops.

```yaml
script:
  shutters_night_ventilation:
    sequence:
      # From any position: down to the end stop first (slats closed) …
      - action: cover.close_cover
        target:
          entity_id: cover.living_room_shutter
      - wait_template: "{{ is_state('cover.living_room_shutter', 'closed') }}"
        timeout: "00:01:00"
      # … then open just the slats.
      - action: cover.open_cover_tilt
        target:
          entity_id: cover.living_room_shutter
```

The entity ends up `open` with `current_position: 0` and
`current_tilt_position: 100` — that is the point: the curtain is down, the slats
are not. `cover.close_cover_tilt` puts it back to fully closed, and
`cover.set_cover_tilt_position` picks anything in between (`50` = half of
`slat_time`).

### Ventilation gap

A few centimetres of actual gap, with the slats open, is a curtain position rather
than a tilt:

```yaml
script:
  shutters_ventilation_gap:
    sequence:
      - action: cover.set_cover_position
        target:
          entity_id: cover.living_room_shutter
        data:
          position: 5
```

With `shutter_run: 30` and `slat_time: 3` that runs the motor for
`3 + 0.05 × 27 = 4.35` seconds: three to open the slats, then a little over one to
lift the curtain. Without `slat_time` the same call would run 1.5 s and leave the
curtain on the floor.

### `set_cover_position`

`set_cover_position` works on both kinds of actuator:

- **advanced**: the position is sent to the actuator directly.
- **basic**: the cover is started in the right direction and stopped by a timer
  after the run computed through both phases of the model. Without `slat_time` that
  is the plain `|target − current| / 100 × shutter_run` seconds; with it, the slat
  phase is added whenever the curtain leaves (or reaches) the floor.
- **basic, target `0` or `100`**: the cover is run into its end stop instead of being
  stopped by a timer, which re-calibrates the estimate for free.

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
4. On the same upward run, note when the **bottom edge leaves the floor**: those
   seconds are `slat_time`.
5. Check `set_cover_position` at 50 %: if the cover consistently overshoots,
   `shutter_run` is too large; if it stops short, too small.

The values are exposed on the entity as the `Shutter run` attribute for basic
covers (plus `Slat time`, `Opening time` and `Closing time` when in use), so you
can confirm what is actually loaded.

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
