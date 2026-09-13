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
          # mac: "00:03:50:aa:bb:cc"   # only needed with more than one gateway
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
for the event data contract. CEN controls support
[device triggers](#device-triggers-and-blueprints) too, over their own shorter list
of event names: `pushbutton_short_press`, `pushbutton_short_release`,
`pushbutton_long_press` and `pushbutton_long_release`. The two lists are not nested
either way — `pushbutton_short_release` is CEN-only, and the long-press repeat and
the four rotary events are CEN+-only — and a trigger asking a CEN control for a
CEN+-only event is refused when the automation loads.

Match a tap on **`pushbutton_short_release`**, not on `pushbutton_short_press`:
on CEN the "press" frame is sent at the start of every press, long ones included,
so a short-press trigger also fires when the user starts holding the button.
`pushbutton_long_press` repeats while the button is held, so give a long-press
automation `mode: queued` (or `max_exceeded: silent`) rather than the default
`mode: single`.

```yaml
automation:
  - alias: "CEN 5/3 tapped"
    triggers:
      - trigger: event
        event_type: myhome_cen_event
        event_data:
          object: 5
          pushbutton: 3
          event: pushbutton_short_release
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

`type` is any event name of the control's protocol and `subtype` is `button_<n>`;
both are the same values the bus event carries, so a device trigger and an event
trigger are all but interchangeable — except that the device trigger **also** matches
the gateway `mac`, which the event trigger only does if you add it, so it is the
narrower of the two.

`buttons:` only decides which combinations the picker offers. A device trigger
written by hand for a button you did not declare still works, as long as the number
is inside the protocol's range (CEN+ `1`-`32`, CEN `0`-`31`); outside that range it
is refused when the automation loads.

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
to pick — the picker lists the declared scenario controls of this integration and
nothing else. Both offer **buttons 1-8** only — for a higher button number on a
large keypad, use a device trigger or a plain `myhome_cenplus_event` trigger as
shown above.

**They are CEN+ blueprints.** The picker cannot filter by protocol, so a declared
**CEN** control appears in it as well, and the blueprints do run on one — but on CEN
the short press fires at the *start of every press*, long ones included (see
[CEN keypads](#cen-keypads-1)), so holding a button in the light blueprint toggles
the light first and then turns it off. On a CEN control, build the automation on a
plain `myhome_cen_event` trigger matching `pushbutton_short_release` instead.

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

If the pushbutton sits behind an F422 local bus interface, the event's `where`
carries the full bus form (`"42#4#3"`), not `"42"` — check a live event in
**Developer tools → Events** before writing the match.

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

One limit of the example above: it keeps a single "last frame / last WHERE" pair,
so two buttons held at the same time defeat it. Their frames arrive interleaved
(WHERE `11`, then `13`, then `11`, then `13`…), each one looks to the automation
like "a different WHERE from last time", `new_hold` is true every time, and the
counter resets before either hold reaches the threshold. If that matters to you,
keep the per-button counters in one `input_text` as JSON keyed by WHERE, and add
a short per-room lock so two holds on the same room do not undo each other.

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
fires `myhome_general_light_event` (or `myhome_area_light_event` /
`myhome_group_light_event`) with `message` and `event: on|off`, plus `area` or
`group` where applicable. For a **general** or **area** lighting frame it also
re-requests the affected states, so your `light` entities follow along on their own;
a **group** frame fires the event only, because a group has no WHERE to poll. The
three WHO 2 automation events fire the event only as well — covers report their own
movement as it happens.

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
"stopped" — never a position. The integration estimates the position from the run
times — `opening_time` and `closing_time`, the seconds a full travel takes in each
direction — and from `roll`, which says how the curtain speeds up as it winds onto
the tube.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      class: shutter
      opening_time: 30       # seconds for a full closed→open travel
```

Defaults and limits, from the validator: `opening_time` defaults to `20` seconds
and must be at least `1`, and `closing_time` defaults to `opening_time`;
`shutter_run` is the legacy alias of `opening_time` and still works; `slat_time`
defaults to `0` (two-phase model off) and must leave at least one second of curtain
travel in both directions; `roll` defaults to `1.6` on `class: shutter` and to `1.0`
on every other class, and must be between `1.0` and `5.0`; `opening_roll` and
`closing_roll` both default to `roll` and take the same range; `tilt`, `advanced` and
`inverted` default to `false`; `class` defaults to `shutter`.

`roll: 1.0` is the plain linear estimate of 0.4.1 and earlier — set it explicitly on
a cover whose behaviour you do not want to change. `opening_roll` and `closing_roll`
override it one direction at a time, exactly as `opening_time` and `closing_time` do
for the run times, for a shutter that does not behave the same way up and down. See
[Configuration → Why the position is not linear](configuration.md#why-the-position-is-not-linear-roll),
and [Calibrating a shutter in centimetres](#calibrating-a-shutter-in-centimetres)
below for measuring your own.

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
      opening_time: 30
      slat_time: 3         # 3 s of slats + 27 s of curtain, each way
      tilt: true           # offer the tilt controls as well
```

`current_position` then counts the **curtain** only (0 = on the floor, 100 = up) and
`current_tilt_position` the **slats** (0 = closed, 100 = open); the entity is
`closed` only when both are 0. The full model, and how to measure the two numbers,
is in
[Configuration → The two-phase travel model](configuration.md#the-two-phase-travel-model-slat_time).

**Since 0.4.2 `tilt: true` is what creates the tilt controls.** `slat_time` on its
own still splits the run in two phases — the timing, the meaning of position `0` and
the run computed by `set_cover_position` are unchanged — but the entity offers no
`current_tilt_position` and no `cover.*_tilt` services without it. Add the key to
every cover you actually tilt from Home Assistant.

If the motor is measurably slower in one direction, add `closing_time` next to
`opening_time`:

```yaml
      bedroom_shutter:
        where: "82"
        name: "Bedroom Shutter"
        slat_time: 3
        tilt: true
        opening_time: 32
        closing_time: 28
```

### Closed, with the slats open

The classic night position: curtain all the way down, slats open for a bit of air
and light. It needs a **basic** actuator with `slat_time` set **and `tilt: true`** —
the tilt services only exist there, and an `advanced:` cover gets no tilt control at
all — and is a single service call: the cover runs up for `slat_time` seconds and stops.

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

With `opening_time: 30` and `slat_time: 3` that runs the motor for about `4.7`
seconds: three to open the slats, then a little under two to lift the curtain — the
curtain is at its slowest down there, which is why it is not the `0.05 × 27 = 1.35`
seconds a linear model would use (that is what `roll: 1.0` gives, and the shutter
then stops short of the 5 %). Without `slat_time` at all the same call would run
1.5 s and leave the curtain on the floor.

### `set_cover_position`

`set_cover_position` works on both kinds of actuator:

- **advanced**: the position is sent to the actuator directly.
- **basic**: the cover is started in the right direction and stopped by a timer
  after the run computed through both phases of the model and through the `roll`.
  With `roll: 1.0` and no `slat_time` that is the plain
  `|target − current| / 100 × opening_time` seconds; the roll bends it (a run near
  the floor takes longer than the same percentage near the top), and `slat_time`
  adds the slat phase whenever the curtain leaves (or reaches) the floor.
- **basic, target `0` or `100`**: the cover is run into its end stop instead of being
  stopped by a timer, which re-calibrates the estimate for free (the end-stop frame
  snaps the estimate to `0` / `100`; see the two-phase model notes in the
  configuration reference for the one caveat).
- **basic, target equal to the position the cover is passing through**: the cover is
  stopped right there.

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
runs to whichever end is closer to the requested position instead — fully open for
a target ≥ 50, fully closed below — so that the estimate gets a reference point. Run one full open and one
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
        opening_time: 18
```

### Calibrating a shutter in centimetres

> **There is a dialog that does all of this for you.** Since 0.5.0,
> **Settings → Devices & services → MyHOME → Configure → "Calibrate a cover"**
> drives the shutter, times the runs from the actuator's own status frames, asks
> for the same centimetres and stores the model itself — no stopwatch, no action
> calls, no pasting. It is the recommended way for a basic cover: see
> [Guided calibration](guided-calibration.md). The recipe below is the manual
> alternative, and stays supported: it is what to use when you would rather write
> the keys yourself, when the actuator does not report its own movement status (the
> dialog needs that to time a run), or from a script.

The run times and the slat time are a stopwatch job. The roll — how much faster the
curtain travels when it is up than when it is down, see
[Configuration → Why the position is not linear](configuration.md#why-the-position-is-not-linear-roll)
— is not: you cannot see it, you can only measure where the shutter *ends up*. That
is what the two calibration actions do. You measure one shutter with a tape measure,
and every similar shutter in the house then gets the same model scaled by its own
height.

Two measurements, two independent answers: the descent gives `closing_roll` and the
ascent gives `opening_roll`. Neither of them is a cross-check on the other, and
neither solves the `slat_time` — that value is always the one you configured, or the
one you hand the action.

> **The cover runs to a full end stop and back, twice.** Nothing may be in the way:
> no open window, no plant on the sill, nobody underneath. Do this while you are
> standing in front of it — you have to measure it anyway.

#### Prerequisites

Write `opening_time`, `closing_time` and, if the shutter has one, `slat_time`
**first**, all three with a stopwatch: the run times from the moment the motor
starts to the moment it stops by itself at the end stop, in each direction
(`cover.open_cover` and `cover.close_cover`, both all the way), and the slat time as
the seconds between the start of an upward run and the instant the bottom edge
leaves the floor. Everything below is built on them: each run drives the motor for
exactly the time a plain *set position 50 %* would use with the current
configuration and a linear model (downwards half of the curtain run, upwards the
configured `slat_time` plus half of the curtain run), and the computation reads the
same numbers back. Do not edit these keys between the runs and the computation.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      opening_time: 22.3     # measured, full upward run
      closing_time: 21.7     # measured, full downward run
      slat_time: 4.7         # measured, bottom edge leaves the floor here
```

Reload the integration and check the `Opening time` / `Closing time` / `Slat time`
attributes of the entity: they are what the calibration will use. The slat time is
never solved for — a stopwatch reads it directly, and it is the one part of the run
you can actually watch happen.

> **Measure every centimetre from the same point: where the bottom edge rests with
> the shutter fully closed.** Not the floor, a sill or a threshold — on some windows
> those coincide with it, on others they sit a few centimetres above or below it.
> Use that one reference for the height below, for both calibration readings, and
> for every check afterwards. A different reference shows up as a constant offset of
> a few centimetres at every position and in both directions, which looks like the
> model got something wrong but is not: a constant offset like that is the sign of a
> reference mismatch, while an error that grows with the length of the run points at
> the times or the roll coefficient instead.

Measure the **height** as well — from that reference point to the bottom edge with
the shutter fully open, in centimetres. It is 195 cm in this example.

#### Step 1 — the half descent

From **Developer tools → Actions**, in YAML mode:

```yaml
action: myhome.cover_calibration_run
target:
  entity_id: cover.living_room_shutter
data:
  direction: close
```

The cover opens fully, waits until it is certainly against the top end stop, then
closes for the seconds a linear *set position 50 %* would use — here
`(21.7 − 4.7) / 2` = 8.5 s — and stops. **Measure the centimetres from the same
reference point to the bottom edge** and write the number down (85 cm here). The action reports the
seconds it used as `motor_seconds` — the *measured* motor time, from the actuator's
own "moving" status to its own "stopped" when it sends them, which can differ from
the planned 8.5 s by a tenth of a second or two; note it down too if you like, though
step 3 recomputes the same number from the configuration.

#### Step 2 — the half ascent

The same action, the other way:

```yaml
action: myhome.cover_calibration_run
target:
  entity_id: cover.living_room_shutter
data:
  direction: open
```

The cover closes fully, then opens for the mirror-image time — the slat phase plus
half the curtain run, here `4.7 + (22.3 − 4.7) / 2` = 13.5 s — and stops. Measure
again (80 cm here).

This second measurement is optional, and it is not a check on the first one: it is
the measurement of the *other* direction. Give it and step 3 returns an
`opening_roll` beside the `closing_roll`; leave it out and only the descent is
described, and the same coefficient is used both ways.

#### Step 3 — compute the model

```yaml
action: myhome.cover_calibration_compute
target:
  entity_id: cover.living_room_shutter
data:
  height: 195
  closed_half_cm: 85
  opened_half_cm: 80
```

The action moves nothing and writes nothing: it solves the model and answers. In
*Developer tools → Actions* the response is shown under the call; in a script use
`response_variable:`. Its shape (**your numbers will be different**):

```yaml
closing_roll: 1.69
opening_roll: 2.12
roll: 1.9
slat_time: 4.7
opening_time: 22.3
closing_time: 21.7
height: 195
closed_run_seconds: 8.5
opened_run_seconds: 13.5
yaml: |
  cover_profiles:
    living_room_shutter:
      reference_height: 195
      opening_time: 22.3
      closing_time: 21.7
      slat_time: 4.7
      closing_roll: 1.69
      opening_roll: 2.12
  # on the cover itself:
  #   profile: living_room_shutter
  #   height: 195
```

Each measurement is solved on its own, by bisection, and lands on it exactly: the
descent gives `closing_roll`, the ascent `opening_roll`, and `roll` is simply their
mean, reported for the covers and the templates that want one number. `slat_time` is
the value the action used — the one you configured, or the one you passed in the
call. `opening_roll` is missing altogether when you did not measure the ascent.

**Why the two are not the same number.** In pure geometry they would be: the roll
has the same radius at the same height whichever way the curtain is going. A real
shutter is less tidy going up — the motor is lifting the whole hanging curtain, the
slats have to unstick from each other and leave the floor, the tube is loaded
differently — and all of that slows the first part of the ascent and shifts where
half a run ends up. Rather than model it, the integration lets the coefficient
differ per direction and each measurement sets its own. The shutter in this example
ended half a run at 85 cm coming down and 80 cm going up, which is about 1.7 and
2.1 — a real difference, not a measurement error, and one that a single averaged
coefficient would split down the middle and miss by a few centimetres each way. A
shutter whose two numbers come out within about 0.1 of each other is symmetrical
enough, and the snippet then writes a single `roll:` instead of the two keys.

Paste the snippet into `myhome.yaml` — the `cover_profiles:` block at gateway level,
beside the platform sections, and the two commented lines onto the cover itself.
Rename the profile to something you will recognise (`tall`, `bedrooms`, `2m_shutter`)
if it is going to describe more than the one cover it was measured on.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"

  cover_profiles:
    tall:
      reference_height: 195
      opening_time: 22.3
      closing_time: 21.7
      slat_time: 4.7
      closing_roll: 1.69
      opening_roll: 2.12

  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      profile: tall
      height: 195
```

The `opening_time` / `closing_time` / `slat_time` keys can come off the cover now:
the profile carries them, and at the reference height nothing is scaled.

> **If the same cover also has a stored calibration**, what you paste here will not
> reach it: the values the [guided calibration](guided-calibration.md) kept for a
> cover beat the file, key by key. Delete them under **Configure → Calibrations**
> and the file's keys apply again.

If instead the action refuses the call, it is because the centimetres you gave it
cannot be produced by any roll coefficient in the accepted range (`1.0` to `5.0`)
with those run times: the message names the measurement it could not use and the
band of centimetres that direction can actually reach. That usually means the cover
did not start from its end stop, or the run times are not the ones the run used —
re-run step 1 or 2 and measure again.

#### Step 4 — reload and check

Reload the integration (**Settings → Devices & services → MyHOME → ⋮ → Reload**; a
full restart is not needed) and confirm the `Opening roll` / `Closing roll`
attributes of the entity (a single `Roll` when the two are equal). Then run the
cover fully open once, so the estimate has a reference, and ask for the middle:

```yaml
action: cover.set_cover_position
target:
  entity_id: cover.living_room_shutter
data:
  position: 50
```

Measure. On a 195 cm shutter the bottom edge should now sit within a couple of
centimetres of 97 cm. Before the calibration it would have stopped noticeably low.

#### Step 5 — every other shutter in the house

Give the others the same profile and **their own height**, and nothing else:

```yaml
  cover:
    kitchen_shutter:
      where: "82"
      name: "Kitchen Shutter"
      profile: tall
      height: 120
    hall_shutter:
      where: "83"
      name: "Hall Shutter"
      profile: tall
      height: 160
```

The times and the roll are scaled per cover — the arithmetic is in
[Configuration → How a height scales a profile](configuration.md#how-a-height-scales-a-profile).
Reload, run them all to 50 % and walk round with the tape measure. Correct only the
ones that miss: a written key beats the profile key by key, so a shutter with a
slower motor keeps the profile and overrides one number.

```yaml
    hall_shutter:
      where: "83"
      name: "Hall Shutter"
      profile: tall
      height: 160
      closing_time: 19.4    # this one is measurably slower coming down
```

A cover that misses by a lot has no business in that profile: measure it with steps
1-3 and give it a profile of its own.

#### What accuracy to expect

After calibration, runs from the end stops land within 1–2 cm and chained runs
between intermediate positions within about 2 cm, with the occasional shutter at
4 cm; no drift accumulates across runs, because every full open or close
re-synchronises the estimate.

- **On the calibrated cover**: 2-3 cm at mid-travel on a 2 m shutter, which is as
  good as the measurements you fed it. Each solved coefficient reproduces its own
  measurement exactly; the error you are left with is what the model does *between*
  the point you measured and the end stops.
- **With only the descent measured**: the same coefficient is used going up, and the
  ascent is the direction where shutters misbehave. Measuring both is ten more
  minutes and it is what step 2 is for.
- **On the derived covers**: a little more. The derivation assumes the same product —
  same motor, same slat profile, same tube — and scales it by height alone. A
  different motor is a different profile.
- **The end stops are exact either way**: `0` and `100` are reached by running into
  the physical stop, not by a timer, and that is also what re-synchronises the
  estimate. A basic actuator never reports its position; everything in between the
  stops remains an estimate, only now a much better one.
- Re-measure after mechanical work on the shutter. Nothing else drifts.

### Tuning the travel times

1. Set `opening_time` to your best guess and reload the integration.
2. Close the cover fully (`cover.close_cover`), wait for it to stop moving on its
   own, then open it fully with a stopwatch running.
3. Set `opening_time` to the measured seconds, save, reload. Time the way down too,
   and add `closing_time` if it differs by more than a second.
4. On the same upward run, note when the **bottom edge leaves the floor**: those
   seconds are `slat_time`.
5. Check `set_cover_position` at 50 %: if the cover consistently overshoots the
   times are too large, if it stops short they are too small — but a *systematic*
   miss at mid-travel with the end stops right is the roll, not the times, and the
   [guided calibration](guided-calibration.md) — or
   [Calibrating a shutter in centimetres](#calibrating-a-shutter-in-centimetres),
   by hand — solves it properly. A miss in one direction only is a roll that differs per
   direction, and the same recipe gives you `opening_roll` and `closing_roll`.

The values are exposed on basic covers as the `Opening time` and `Closing time`
attributes and either `Roll` or `Opening roll` / `Closing roll` (plus `Slat time`,
`Height` and `Profile` when in use), so you can confirm what is actually loaded.

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
three energy entities (today / this month / total) — but *Energy today* and *Energy
this month* are **disabled by default**, so on a fresh install you see two entities,
not four. Enable them from the entity settings if your gateway answers totaliser
requests; see
[Energy → Daily/monthly/total energy](energy.md#dailymonthlytotal-energy-and-gateways-without-totals).

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

**Events need the same care.** The CEN, CEN+ and wall-pushbutton events all carry a
`mac` key, normalised the same way. Two gateways can produce the same
`object`/`pushbutton` pair, or the same pushbutton WHERE, so on a multi-gateway plant
add `mac:` to the `event_data` of every such trigger or the automation fires twice:

```yaml
      - trigger: event
        event_type: myhome_cenplus_event
        event_data:
          mac: "00:03:50:aa:bb:cc"
          object: 1
          pushbutton: 1
          event: pushbutton_short_press
```

Device triggers need no such addition: they always match on `mac`.

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
