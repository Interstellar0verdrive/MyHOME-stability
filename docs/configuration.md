# Configuration reference

How to add a gateway from the UI, and the full `myhome.yaml` schema: file
location, root formats, every parameter per platform, Lock/Unlock buttons,
multiple gateways, custom icons/device classes, and what the validator's error
messages mean.

See the [main README](../README.md) for installation and a minimal example, and
[Recipes](recipes.md) for copy-paste automations and configuration built on top
of this schema.

## Contents

- [Gateway setup](#gateway-setup)
  - [Automatic discovery (recommended)](#automatic-discovery-recommended)
  - [Manual gateway configuration](#manual-gateway-configuration)
  - [Reauthentication](#reauthentication)
  - [Options](#options)
  - [Repairs](#repairs)
- [The `myhome.yaml` file](#the-myhomeyaml-file)
- [Common parameters (all platforms)](#common-parameters-all-platforms)
  - [Local bus interfaces (`interface`)](#local-bus-interfaces-interface)
- [Light](#light)
- [Switch](#switch)
- [Cover](#cover)
  - [Keypad presses and gateway echoes](#keypad-presses-and-gateway-echoes)
  - [Why the position is not linear (`roll`)](#why-the-position-is-not-linear-roll)
  - [The two-phase travel model (`slat_time`)](#the-two-phase-travel-model-slat_time)
  - [Cover profiles](#cover-profiles)
    - [How a height scales a profile](#how-a-height-scales-a-profile)
  - [Calibrating a cover](#calibrating-a-cover)
- [Binary sensor](#binary-sensor)
- [Climate](#climate)
- [Sensor](#sensor)
- [Scenario control (CEN / CEN+)](#scenario-control-cen--cen)
- [Lock/Unlock buttons](#lockunlock-buttons)
- [Multiple gateways](#multiple-gateways)
- [Custom icons and device classes](#custom-icons-and-device-classes)
- [State attributes](#state-attributes)
- [Validation errors](#validation-errors)

## Gateway setup

### Automatic discovery (recommended)

Many MyHOME gateways announce themselves over SSDP, but no model has been
confirmed on real hardware yet (see
[Gateway compatibility → Note 1](gateway-compatibility.md#note-1--the-two-discovery-paths)):

1. Go to **Settings → Devices & services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"MyHOME"**
4. Select your discovered gateway
5. Enter the gateway password if required
6. Click **"Submit"**

### Manual gateway configuration

If your gateway isn't auto-discovered:

1. Go to **Settings → Devices & services**
2. Click **"+ ADD INTEGRATION"**
3. Search for **"MyHOME"**
4. Select **"Configure manually"**
5. Enter gateway details:
   - **Host**: Gateway IP address
   - **Port**: Gateway port (default: 20000)
   - **Password**: Gateway password (if required)
   - **Name**: Friendly name for the gateway

### Reauthentication

If the gateway rejects the stored password (for example after it was changed on
the device), Home Assistant raises a reauth flow: open it from the integration
card and enter the current OpenWebNet password.

### Options

From **Settings → Devices & services → MyHOME → Configure** you can change,
without removing the integration:

- IP address/hostname, port, password
- **Configuration file path** — where `myhome.yaml` (and `myhome_discovered.yaml`)
  live, if not the default Home Assistant config directory
- **Number of concurrent command sessions** — how many command sessions the
  integration may hold open at once (default `1`, range `1`-`4`). Gateways only
  serve a handful of concurrent sessions, so `4` is the ceiling: see
  [Gateway compatibility → Note 3](gateway-compatibility.md#note-3--session-limits).
  Per-device ordering, [stop priority included](architecture.md#the-command-queue), is
  a guarantee of the queue, not of the bus: with more than one command worker, two
  adjacent frames for the same device can be dequeued together and race each other
  over the wire, so the default of `1` is where the guarantee holds end to end.
- **Generate events in Home Assistant for each message received** — toggles
  `myhome_message_event` (see [Services and events](services-and-events.md))

Saving options reloads the integration.

#### Session tunables

Since 0.3.0 the timings that used to be hard-coded are editable in the same form.
**The defaults are exactly the values 0.2.x used internally, so leaving them alone
changes nothing** — only touch them if you are working around a specific gateway
misbehaviour, and change one at a time.

| Option | Default | Range | What it does |
| --- | --- | --- | --- |
| Idle watchdog | 300 s | 60–3600 | No frame received on the monitor session for this long: a harmless status request is sent through the command session to check the gateway is still alive. Lower it on a gateway that dies silently; raise it on a very quiet plant that produces false probes. |
| Probe window | 30 s | 5–300 | The probe was sent, nothing arrived on the monitor session and the gateway acknowledged no status request on the command session: the event session is closed and reconnected (backoff 1, 2, 4 … 60 s). A status request the gateway ACKed on the **command** session after the probe went out — the probe itself, or any other — proves it is alive and simply does not mirror replies onto the monitor, so the watchdog re-arms instead of reconnecting. |
| Command timeout | 10 s | 2–60 | How long a single command may take to be written and acknowledged. A command that could not be written is retried once on a fresh session; one that was written and then not acknowledged is not sent again (the actuator has it). Either way it is then dropped with a warning. Raise it on a slow gateway that NACKs under load. |
| Command queue TTL | 60 s | 10–600 | Commands still queued after this long are dropped instead of being sent late (a light that switches on two minutes after the button press is worse than one that does not). |
| Default instant-power keep-alive | 125 min | 0–255 | The keep-alive asked of the energy meters for power sensors whose `keepalive_minutes` comes from neither the sensor nor the gateway's `sensor_defaults:` (alias `energy:`) block. `0` disables it. Any value written in the file — per sensor or in either gateway-level block — always wins, even when it equals the built-in `125`. Precedence: per-sensor key → `sensor_defaults` / `energy` → this option → built-in default. See [Energy monitoring](energy.md). |

A [diagnostics download](troubleshooting.md#diagnostics-download) always reports the
values actually in effect, under `effective_options`.

### Repairs

The integration reports configuration problems as Home Assistant **repair issues**
(*Settings → System → Repairs*) instead of leaving them in the log:

| Issue | Severity | Meaning |
| --- | --- | --- |
| MyHOME configuration file is invalid | Error | `myhome.yaml` could not be read, parsed or validated. The issue carries the file path and the exact validator message; no device is created until it is fixed. |
| Unknown keys in the MyHOME configuration file | Warning | The file contains keys the integration does not know. They are ignored (never fatal, for backward compatibility) and listed with a "did you mean" hint. Dismissable if the keys are intentional. |
| No devices configured for this MyHOME gateway | Warning | The gateway's MAC address has no section in the file — usually a typo in the MAC, or the section of a different gateway. |

Each issue is cleared automatically as soon as a later load no longer hits its cause
(fix the file, then reload the integration).

## The `myhome.yaml` file

Devices are declared in `myhome.yaml` (in your Home Assistant config folder, or
the path set in the integration options). The file is validated when the
integration loads; a validation error is shown in **Settings → Devices &
services** with the offending key path, and the integration does not start until
it is fixed.

Two root styles are accepted, and they can be mixed (one entry per gateway):

- **`gateway:` block** (the style written by auto-discovery, recommended):
  ```yaml
  gateway:
    mac: "00:03:50:AA:BB:CC"
    light:
      kitchen_light:
        where: "15"
        name: "Kitchen Light"
  ```
- **MAC address as root key** (legacy, and the way to configure several gateways):
  ```yaml
  "00:03:50:AA:BB:CC":
    light:
      kitchen_light:
        where: "15"
        name: "Kitchen Light"
  ```
  An inner `mac:` is optional here; if present it must match the root key. Any MAC notation is accepted (`00:03:50:aa:bb:cc`, `00-03-50-AA-BB-CC`, `000350AABBCC`).

Under the gateway, each platform section (`light`, `switch`, `cover`, `binary_sensor`, `sensor`, `climate`, `scenario_control`) maps a **YAML key of your choice** (used only in error messages) to a device. Sections may be left empty.

Besides the platform sections a gateway may carry `sensor_defaults:` (see [Energy monitoring](energy.md#sensor_defaults)) and, since 0.4.2, `cover_profiles:` (see [Cover profiles](#cover-profiles)): settings shared by several devices rather than devices of their own.

Rules worth knowing:

- **Quote every `where`** (`where: "01"`, not `where: 01`). YAML reads an unquoted address as a number, and a leading zero is gone by the time the validator sees it: nothing downstream can tell `where: 01` from `where: 1`, and `where: 0115` has already become `77` (YAML reads it as octal). Those values **cannot be detected**, so the validator does not claim to catch them — it accepts unquoted integers only as `0`, a two-digit or a four-digit value and refuses every other number — a bare `1`-`9`, which is ambiguous, a negative value, which is no address at all, and the 3- and 5-digit forms sensor addresses take, above all — and asks you to quote the whole file. Unquoted two- and four-digit numbers still load, for the configurations that always relied on it, which is exactly why the habit matters: an address written with a leading zero loads too, as a different device — everywhere except a WHO 4 zone or temperature probe, whose address is a zone number and is normalised (`'01'` is `1`; see [Climate](#climate)).
- **Each WHO/WHERE may appear only once per gateway**, across all platforms (a duplicate `where` used to silently drop one of the two devices). The error names both YAML keys. The only tolerated overlap is a `climate` zone plus a `sensor` of class `temperature` on the same zone: the two share one device, which keeps the **climate** name, and the probe's own `name` becomes the sensor's `entity_name` (device "Living Zone", sensor "Living Zone Living Probe").
- **Unknown keys do not break the configuration**: they are kept and reported once at WARNING level with a "did you mean" hint (e.g. `dimable` → `dimmable`). Check the log after editing the file.
- `device_class` is accepted as an alias of `class` on every platform (they must not both be given with different values).

## Common parameters (all platforms)

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `where` | string | Yes | – | OpenWebNet WHERE address (see the platform notes for the accepted forms). Climate uses `zone` instead. |
| `name` | string | Yes | – | Device name in Home Assistant (optional for climate). |
| `entity_name` | string | No | device name | Name of the main entity when it must differ from the device name. On a `class: power` meter it renames the **Power** entity; the daily/monthly/total energy entities of a `power` or `energy` meter keep their own translated names ("Energy today", "Energy this month", "Energy"). On a `scenario_control` the main entity is named `<device name> Scenario control` by default, not after the device alone; setting `entity_name` there also changes its `entity_id`, which is otherwise `event.<device>_scenario_control`. |
| `icon` | string | No | – | Icon of the entity (`mdi:...` or any registered icon set). On a `power` or `energy` meter, which owns several entities, it is applied to **all** of them (Power and the three energy totalisers) — unlike `entity_name`, which only renames the main one. Not applied to the optional Lock/Unlock buttons, which keep their fixed padlock icons. |
| `icon_on` | string | No | – | Icon used while the entity is on (light, switch, binary sensor). |
| `manufacturer` | string | No | `BTicino S.p.A.` | Cosmetic, shown in the device page. |
| `model` | string | No | – | Cosmetic, shown in the device page. |
| `who` | string | No | per platform | OpenWebNet WHO; only needed for sensors/binary sensors that support several. |
| `interface` | string or int | No | – | Local bus interface (F422) of a device behind a bus interface: light, switch, cover, WHO 1 motion binary sensors and WHO 1 illuminance sensors. **Refused** on the other sensor WHOs (4 temperature, 9 auxiliary, 18 energy, 25 dry contact) because their frames never carry the interface, so such a device could never receive an update; on climate (addressed by zone) and on `scenario_control` the key is not part of the schema at all: it is reported as an unknown key (a WARNING and the *Unknown keys* repair issue) and has no effect. Accepted as an integer or as a 1-2 digit string: `3`, `"3"` and `"03"` all mean the same interface. |
| `class` / `device_class` | string | No | per platform | Home Assistant device class (see the platform tables). |

Accepted actuator WHERE forms (light, switch, cover): General `"0"`, Area `"00"`, `"1"`..`"10"`, Group `"#1"`..`"#255"`, Point-to-Point 2 digits (`"15"`, A=1 PL=5) or 4 digits (`"0115"`, A=01 PL=15). Sensors and binary sensors accept any string of digits (energy meters are usually `"51"`..`"5N"`). Climate is different: its `zone` (and its `where` alias) accepts only `"#0"` for the central unit, `"1"`..`"99"` for a zone, or `"#0#<zone>"` for a zone driven through the central unit.

### Local bus interfaces (`interface`)

A device behind an F422 bus interface is addressed on the bus as
`<where>#4#<interface>` — for example WHERE `11` on interface 3 is `11#4#3`.

- **Accepted forms**: an integer `0`..`15` or a string of 1 or 2 digits
  (`3`, `"3"`, `"03"`). Anything else is a configuration error.
- **Stored unpadded**: whatever you write, the value is normalised to the form the
  bus uses (`"3"`), which is also the form every command the integration sends
  carries. This changed in **0.3.1**: before it, commands went out zero padded
  (`11#4#03`) while the bus answers unpadded.
- **Entity identity is unchanged**: the internal device key, and therefore the
  `unique_id` of every entity behind a bus interface, keeps the interface zero
  padded (`1-11#4#03`). Upgrading to 0.3.1 does **not** rename your entities or
  lose their history.
- Incoming frames are matched against both spellings, so a gateway that reports
  `11#4#3` and a configuration written `interface: "03"` resolve to the same
  entity.
- **Only WHO 1, 2 and 15 frames carry the interface.** `interface:` is therefore
  accepted on lights, switches, covers, WHO 1 motion binary sensors and WHO 1
  illuminance sensors, and rejected with a validation error on WHO 4, 9, 18 and 25
  sensors: declared there, the device would be keyed `18-51#4#03` while its frames
  always arrive as `18-51`, and it would stay `unknown` forever.

> Devices behind a bus interface received **no state updates at all** before
> 0.3.1: the `OWNd` version we shipped never extracted the interface from the
> frame, so their updates were applied to a main-bus device with the same WHERE,
> if one existed. Fixed by `OWNd` 0.7.49 plus the normalisation above.

## Light

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dimmable` | boolean | `false` | Enable brightness control. |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

## Switch

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class` | `switch` \| `outlet` | `switch` | Device class. |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

## Cover

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `advanced` | boolean | `false` | Advanced actuator reporting its real position (position control from the device). Get this key wrong in the *other* direction — an actuator that does report its own position, left at `false` — and those position frames are ignored: the timed estimate is what the cover was configured for, and mixing the two would leave the entity reading *Opening* at a frozen percentage. The log says so once per frame, at debug level, and names `advanced: true`. |
| `opening_time` | number (s) | `20` | Full **upward** run in seconds, slats included, at least `1`, measured motor-on to motor-off — the bus delays before and after it are `start_delay` and `stop_latency`, not part of this number. The official name of the key since **0.4.2** (`shutter_run` is its alias). Basic actuators use it, with `closing_time` and `roll`, to estimate the position (`0` = curtain down, `100` = fully open; with `slat_time`, `0` means the curtain rests on the floor, see the two-phase model below), to derive open/closed and to support *set position* by timed stop. On `advanced` actuators it does not estimate anything — they report their real position — but it is not unused: the longer of `opening_time` / `closing_time` plus 30 seconds is the deadline after which the actuator is asked what it is doing and a movement whose "stopped" frame was lost is cleared (cleared only if the actuator does not answer within the whole time a single command may take — a connection to re-open, a command to acknowledge, and one retry of both — plus a two-second margin: about 42 seconds with the default options, see [Keypad presses and gateway echoes](#keypad-presses-and-gateway-echoes)). The validator warns when the timing keys are set on an `advanced` cover, naming each one and what it still does there, so the log line is expected and not a symptom. |
| `closing_time` | number (s) | = `opening_time` | Full **downward** run, when it differs from the upward one. At least `1`. On an `advanced` actuator it only bounds the direction safety timer. |
| `stop_latency` | number (s) | `0.1` | How long the motor keeps turning after the stop frame is written, in seconds. The stop that ends a *set position* or a tilt run is written that much before the modelled end of the run, and the position frozen by `cover.stop_cover` is where the shutter coasts to. A constant of the installation, not of the window: it is never scaled by `height`. |
| `start_delay` | number (s) | `0.5` | How long the motor takes to start after the frame is written, in seconds. Used **only** until the actuator says itself that it is moving — which it normally does, about half a second later, and the run is then timed from that instant instead. It is what a gateway that does not relay status frames falls back on. Also never scaled by `height`. A direction status that arrives within 0.15 s of the write is not believed to be the motor: some gateways mirror the command they have just written on the monitor session, and no actuator starts that fast. |
| `shutter_run` | number (s) | – | **Legacy alias of `opening_time`**, kept for good: every configuration written before 0.4.2 keeps working unchanged. Writing both keys is accepted only if they carry the same number; two different values are refused with a message naming both. It has no separate meaning any more — in particular it is no longer the fallback of `closing_time` under another name, since `closing_time` falls back to `opening_time`, which is the same value. |
| `slat_time` | number (s) | `0` | Seconds of the run that only open/close the slats ("lamelle"), without moving the curtain. `0` disables the two-phase model. Since 0.4.2 the tilt *controls* need `tilt: true` as well; without it the two-phase timing still runs (see below), it is only the tilt entity features that are not offered. Ignored on `advanced` actuators, which have no tilt controls — and, since it is ignored, no longer cross-checked against the run times there either. |
| `roll` | number, `1.0`-`5.0` | `1.6` on `class: shutter`, `1.0` on every other class | How much faster the curtain travels when it is up than when it is down, because the roll on the tube is fatter (see [Why the position is not linear](#why-the-position-is-not-linear-roll)). `1.0` is the plain linear model of 0.4.1 and earlier. Typical measured values are between `1.4` and `2.0`. Only used by basic actuators, and only for the curtain phase: the slat phase stays linear. It is the value used in **both** directions unless one of the two keys below overrides it. |
| `opening_roll` | number, `1.0`-`5.0` | = `roll` | The roll used for **upward** runs, when the shutter does not behave the same way going up. Mirrors `opening_time` exactly: write it only when you have measured it. |
| `closing_roll` | number, `1.0`-`5.0` | = `roll` | The roll used for **downward** runs. Mirrors `closing_time`. Writing both directional keys makes `roll` irrelevant for the estimate; it is still what the attributes fall back on when the two are equal. |
| `tilt` | boolean | `false` | Offer the tilt controls (`cover.open_cover_tilt` and friends, and the `current_tilt_position` attribute). **Default `false` since 0.4.2**, even with `slat_time` set: the two-phase timing model runs underneath either way, only the tilt entity features are opt-in. Has no effect on an `advanced` cover, which never has tilt controls. |
| `height` | number (cm) | – | Curtain travel height, floor to fully open, in centimetres. On its own it does nothing but show up as an attribute; with `profile` it is what scales the profile's times and roll to this cover (see [Cover profiles](#cover-profiles)). |
| `profile` | string | – | Name of an entry of the gateway-level [`cover_profiles:`](#cover-profiles) mapping. An unknown name is a validation error listing the names that are defined. |
| `inverted` | boolean | `false` | The actuator is wired the other way round: `open_cover` sends *lower*, a bus "raising" frame is read as closing and an advanced actuator's reported level is mirrored. Home Assistant's own convention is unchanged: position `0` is still closed, `100` still open. |
| `class` | cover device class | `shutter` | Any Home Assistant cover class (`shutter`, `blind`, `awning`, `garage`, ...). It also decides the default `roll`. |
| `lock_buttons` | boolean | `false` | Create Lock/Unlock configuration buttons for this actuator (Point-to-Point WHERE only). |

`slat_time` must leave at least one second of curtain travel in both directions
(`slat_time < min(opening_time, closing_time) - 1`), otherwise the configuration is
rejected with the name of the offending cover.

A key written on the cover always wins. Everything not written there is taken from
the cover's `profile` (scaled by its `height`, if both are given), and what is left
falls back to the defaults in the table above. `stop_latency` and `start_delay`
resolve the same way — cover, then profile, then default — but they are the two
keys a profile hands over **unscaled**: a shorter window has less curtain to wind,
not a faster gateway.

`roll`, `opening_roll`, `closing_roll`, `height`, `profile`, `tilt`, `stop_latency`
and `start_delay` join `opening_time`, `closing_time`, `slat_time` and `shutter_run`
in the list of keys the validator warns about on an `advanced:` cover: they do
nothing there, the warning names them, and the configuration still loads.

### Keypad presses and gateway echoes

Neither of the two rules below depends on `slat_time`: the first applies to every
basic (timed) cover, the second to every `advanced:` one.

The gateway repeats commands back to Home Assistant a moment after it accepts
them, and those repeats look exactly like a keypad press. A frame arriving
within 1.5 s of a command sent by Home Assistant is ignored as such a repeat
only when it can be one: a `stopped` frame right after a movement we asked for,
or a copy of the movement a stop of ours interrupted — a `cover.stop_cover`, or
the stop the integration sends by itself at the end of a *set position* or a
tilt run. Both the run and that second and a half are counted, since 0.4.3, from
the moment the gateway actually wrote the frame, not from the moment Home
Assistant asked for it: on a busy command queue the two are a good fraction of a
second apart. While the frame is still waiting its turn that second and a half has
not started at all — the gateway cannot repeat a command it has not been given yet —
so a repeat is recognised as a repeat however long the queue was. A movement in any other direction, such as pressing *up* on the
keypad right after stopping a shutter that was going down, is honoured straight
away. Pressing the **same** direction again within that second and a half cannot
be told apart from the repeat, so it is ignored; the integration then re-reads
the actuator's status, and the movement is picked up about two seconds late
rather than lost. A stop Home Assistant could not even send — the gateway's
command queue was full, or the connection was closing — changes nothing at all:
no repeat can follow a command that was never sent, and the shutter is still
running, so the estimate keeps running with it. A stop that was accepted and
then never reached the bus — it waited in the queue past its sixty seconds, or
the gateway stopped answering — comes to the same thing one step later: the
shutter runs on to its end stop and the estimate runs on with it, for a
`cover.stop_cover` exactly as for the stop the integration sends by itself at
the end of a *set position* or a tilt run. Either way the actuator's own frame
at the end of the run is what puts the estimate back in step. That holds however
short the run was: a two-percent nudge of the position slider takes well under
the second and a half in which the gateway may still be repeating the command
that started it, and the repeat is recognised as one rather than being read as
the shutter stopping. The price of recognising it is that a *real* stop in that
same second and a half — somebody at the keypad, or the shutter meeting an
obstacle — cannot be told apart from it either. So that one is handled the same
way as the ambiguous keypad press: the frame is ignored, the actuator is asked
what it is really doing, and its answer ends the run about two seconds late
instead of letting the estimate run on to the end stop and settle there.

An advanced actuator's *Opening* / *Closing* state comes from its own frames. If the
frame that says it stopped is lost, the state would otherwise stay that way for
ever, so the integration re-reads the actuator's status after the longest configured
travel time plus 30 seconds, and drops the direction only if nothing answers.
"Nothing answers" is measured against the command path itself, not against a fixed
delay: that answer has to travel the ordinary command queue, which may have to
re-open a connection to the gateway first (ten seconds), then write the request and
wait for the acknowledgement (the **Command timeout** option, ten seconds by default,
see [Session tunables](#session-tunables)), and which gives the whole attempt one
retry before giving up. So the wait is **twice the sum of those two, plus two
seconds — about 42 seconds with the defaults** — and it grows with the **Command
timeout** option: setting that to 30 seconds makes the wait 82. Is a re-opened
connection really the case to size that wait on? Not certainly, but plausibly enough.
Home Assistant keeps **one** command connection per gateway — shared by every entity,
service call and background check, not one per cover — and closes it after a minute
in which it sent nothing at all. In a quiet house at three in the morning, which is
exactly when a shutter runs on a schedule with nobody watching, that connection
usually is closed. And the wait is sized on the worst case on purpose: being wrong
the cheap way leaves *Opening* on screen a little longer, while being wrong the other
way publishes a moving shutter as *closed* and wakes every automation watching for
it.

An actuator that is still running answers well inside that, so it is not reported as
stopped in the middle of a long run; an ordinary scene is comfortably inside it too —
a dozen commands the gateway acknowledges in well under a second. What is *not*
covered is a queue whose own backlog outlasts the wait: queued commands are dropped
only after the **Command queue TTL** option, sixty seconds by default, and holding
*Opening* for a whole minute after a genuinely lost frame would be worse than the
problem the deadline exists for. The reported position is not affected either way: it
is always the actuator's own value, never an estimate.

This is also the one thing the timing keys still do on an `advanced:` cover — a
shutter, awning or garage door whose run is longer than the 50 seconds of the default
needs `shutter_run` (or `opening_time` / `closing_time`) so that the safety timer
stays out of its way.

The two models are never mixed. A cover left at `advanced: false` ignores any frame
carrying a position — an advanced actuator that was not declared as one — and keeps
its timed estimate running; a cover declared `advanced: true` never estimates a
position at all. If a shutter reads *Opening* at a percentage that does not move, the
debug log will have said which of the two you are missing.

### Why the position is not linear (`roll`)

A rolling shutter winds onto a tube. The motor turns at a constant speed; the
curtain does not. With the shutter up, most of the curtain is already wound on the
tube, the roll is fat, and one turn of the motor pulls a long piece of curtain past
the window. With the shutter down the tube is nearly bare, and the same turn pulls
much less. The curtain is therefore fastest near the top and slowest near the floor.

A stopwatch model that assumes one constant speed gets the two end stops right — a
full run is a full run — and everything in between wrong, always in the same
direction: the estimate says the shutter is higher than it is on the way down, and
*set position 50 %* stops it too low.

`roll` is the one number that describes this: the ratio between the radius of the
full roll (shutter open) and the radius of the bare tube (shutter closed), which is
also the ratio between the fastest and the slowest curtain speed.

| `roll` | Meaning |
|---|---|
| `1.0` | Constant speed — the plain linear model of 0.4.1 and earlier. Set it explicitly on a cover whose estimate you do not want to change. |
| `1.4` – `2.0` | The range ordinary domestic roller shutters measure in. |
| `1.6` | The default on `class: shutter`, chosen as the middle of that range. |
| other classes | `1.0`: a blind, an awning or a garage door has no roll to speak of, or none we can model. |

Only the **curtain** phase goes through this model. The slat phase (`slat_time`)
stays linear, because the slats are not winding on anything, and both end stops are
still reached by running into them.

What it changes, for the default `roll: 1.6`, on a cover coming down from fully
open (curtain phase only):

| Fraction of the curtain run spent descending | Estimated position, `roll: 1.0` | Estimated position, `roll: 1.6` |
|---|---|---|
| a quarter | 75 % | 71 % |
| half | 50 % | 44 % |
| three quarters | 25 % | 21 % |

On a 195 cm shutter, half the curtain run leaves the bottom edge about 86 cm from
the floor, not 98. The same numbers read the other way: to *reach* the middle of
the window the motor has to run for rather more than half the time.

**One roll per direction, when the shutter needs it.** The geometry alone would make
the ascent the descent played backwards — same radius at the same height, so the
same speed. Real shutters are not quite that symmetrical: going up the motor lifts
the whole hanging curtain, the slats have to leave the floor and unstick from each
other, and the tube is loaded differently from when the curtain is paying out under
its own weight. Rather than model any of that, the integration lets the coefficient
differ per direction: `closing_roll` for descents, `opening_roll` for ascents, both
defaulting to `roll`. On the shutter these numbers were measured on (195 cm), half
the run down ended 85 cm off the floor and half the run up ended 80 cm — roughly a
roll of 1.7 downwards and 2.1 upwards. One coefficient per direction absorbs that
difference; a single one splits it and is a few centimetres out both ways.

The default is a plausible average, not your shutter, and it is the same in both
directions. Measure yours once with
[Recipes → Calibrating a shutter in centimetres](recipes.md#calibrating-a-shutter-in-centimetres),
which returns the roll of that cover in each direction and a ready-to-paste profile.


### The two-phase travel model (`slat_time`)

On most roller shutters the motor run is not all lift. Starting from fully closed,
the first seconds only tilt the slats open while the curtain stays on the floor; and
when closing, the motor keeps running for the same few seconds *after* the curtain
has touched the floor, to close them again. A single linear 0-100 model therefore
reports "5 %" while the curtain is still on the floor, and *set position 50 %* from
closed ends up around 55-60 %.

With `slat_time` set, the integration splits every run in two phases:

| Phase | Duration | Reported as |
|-------|----------|-------------|
| Slats ("lamelle") | `slat_time` | `current_tilt_position` — 0 = slats closed, 100 = slats open |
| Curtain | `opening_time - slat_time` (up) / `closing_time - slat_time` (down) | `current_position` — 0 = curtain on the floor, 100 = fully open |

The slat phase is linear; the curtain phase goes through the
[`roll` model](#why-the-position-is-not-linear-roll).

**Since 0.4.2 the tilt controls are opt-in.** `slat_time` alone buys the *timing*:
the run to a position is computed through both phases, `current_position: 0` still
means the curtain is on the floor, and a run up from fully closed still spends
`slat_time` before anything lifts. What it no longer buys by itself is the tilt
*entity features* — `current_tilt_position` and the four `cover.*_tilt` services.
Add `tilt: true` next to `slat_time` to get them back; the rest of this section then
describes the cover exactly as 0.4.1 did. Nothing else changes with the default
`tilt: false`, and the two bullets about the slats below simply do not apply.

Consequences, all of them deliberate:

- `current_position: 0` means **the curtain rests on the floor**, whatever the slats
  are doing. The entity is `closed` only when the curtain is down **and** the slats
  are closed (`current_tilt_position: 0`); with the curtain down and the slats open
  it is `open`.
- Above the floor the slats are necessarily open, so `current_tilt_position` is
  pinned to `100` and the tilt services are ignored (with a DEBUG log line).
- The tilt services (`cover.open_cover_tilt`, `cover.close_cover_tilt`,
  `cover.set_cover_tilt_position`, `cover.stop_cover_tilt`) are only offered on a
  **basic** actuator with `slat_time` greater than `0` **and `tilt: true`**. On an `advanced:` cover
  there is no tilt control at all, and the timing keys never produce a position —
  the actuator reports its own. Two of them are not unused, though: the run times
  set the safety timer described under [Keypad presses and gateway
  echoes](#keypad-presses-and-gateway-echoes), which is why the integration logs a
  warning naming, key by key, which of the ones you wrote still bounds that timer and
  which does nothing there at all.
- `cover.set_cover_position` computes the run through **both** phases: from fully
  closed, position 5 % costs `slat_time + 0.05 × (opening_time - slat_time)` seconds.
- **The clock starts when the motor does**, not when the service call is made and not
  when the frame reaches the bus (since 0.4.4). One command session writes about ten
  frames a second, so commanding a dozen covers at once staggers their *starts* over
  more than a second — but not the length of their runs: each shutter still runs
  exactly the seconds its target costs. The bus adds two constant delays of its own,
  and both are now modelled: the actuator answers a movement command with its own
  "moving" status about half a second later, which is when the run is timed from, and
  it keeps turning about a tenth of a second after the stop frame, which is why the
  stop is written that much early. `start_delay` and `stop_latency` are those two
  numbers, and a gateway that relays no status frames uses `start_delay` for every
  run.
- `cover.open_cover` and `cover.close_cover` still run into the end stop, which is
  what re-calibrates the estimate: a "stopped" frame that arrives during a full run
  commanded from Home Assistant, once at least three quarters of the expected run
  have elapsed, is read as the physical end stop and the estimate snaps to `0` /
  `100`. Earlier stops are taken for what they most likely are, somebody pressing
  *stop*, and freeze the estimate where it is. `set_cover_position` with `0` or
  `100` uses the same full run instead of stopping by timer.
- `cover.set_cover_position` on a cover whose position is **unknown** (no run seen
  since the restart, and nothing restored) cannot time anything, so it first runs to
  the nearest end stop — open for a target of `50` or more, closed below it — and the
  estimate has a reference from then on.
- Movements started from a physical keypad (or by a scenario) are tracked through the
  very same model, from the `opening` / `closing` / `stopped` frames on the bus.
- Gateway echoes and the advanced actuator's direction safety timer apply to every
  cover, whatever `slat_time` is — see [Keypad presses and gateway
  echoes](#keypad-presses-and-gateway-echoes) above.
- `slat_time: 0` (the default) leaves one single phase, and with `roll: 1.0` as well
  that is exactly the 0.3.x behaviour, tilt included: no tilt feature, no extra
  attribute.

### Cover profiles

Most houses have one kind of shutter in several sizes: same motor, same slats,
different heights. `cover_profiles:` lets you measure **one** of them properly and
describe all the others by their height alone.

The mapping sits at gateway level, beside the platform sections:

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"

  cover_profiles:
    tall:                     # any name, any number of profiles
      reference_height: 195   # cm — the height of the cover this was measured on
      opening_time: 22.3      # s, full upward run, slats included
      closing_time: 21.7      # s, defaults to opening_time
      slat_time: 4.7          # s, defaults to 0
      roll: 1.6               # defaults to 1.6
      # opening_roll / closing_roll here too, when the two directions differ

  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      profile: tall
      height: 195             # the profile's own reference: nothing is scaled
    kitchen_shutter:
      where: "82"
      name: "Kitchen Shutter"
      profile: tall
      height: 120             # shorter: times and roll are scaled down
    hall_shutter:
      where: "83"
      name: "Hall Shutter"
      profile: tall           # no height: the profile's numbers, unscaled
      closing_time: 19.4      # measured on this one; overrides the profile
```

| Key | Type | Default | Description |
|-----------|------|---------|-------------|
| `reference_height` | number (cm) > 0 | **required** | Curtain travel height of the cover the profile was measured on. |
| `opening_time` | number (s) ≥ 1 | **required** | Full upward run of that cover, slats included. `shutter_run` is accepted here as an alias too. |
| `closing_time` | number (s) ≥ 1 | = `opening_time` | Full downward run of that cover. |
| `slat_time` | number (s) ≥ 0 | `0` | Slat phase of that cover. |
| `roll` | number, `1.0`-`5.0` | `1.6` | Roll coefficient of that cover, in both directions. |
| `opening_roll` | number, `1.0`-`5.0` | = `roll` | Roll coefficient of that cover going up, when it differs. Mirrors `opening_time`. |
| `closing_roll` | number, `1.0`-`5.0` | = `roll` | Roll coefficient of that cover going down, when it differs. Mirrors `closing_time`. |
| `stop_latency` | number (s) ≥ 0 | `0.1` | How long the motor keeps turning after the stop frame is written. Carried over **unchanged**, whatever the cover's `height` is. |
| `start_delay` | number (s) ≥ 0 | `0.5` | How long the motor takes to start after the frame is written. Carried over **unchanged** as well — these two are the only keys a profile hands over the same whatever the cover's `height` is. A direction status that arrives within 0.15 s of the write is not believed to be the motor: some gateways mirror the command they have just written on the monitor session, and no actuator starts that fast. |

A profile nobody uses is harmless. A `profile:` naming an entry that does not exist
is a validation error, and the message lists the names that are defined.

#### How a height scales a profile

Everything below happens once, when the file is loaded. Writing a key on the cover
itself always wins over the derived value, key by key — that is how the
`hall_shutter` above keeps its own `closing_time` and inherits the rest.

Call `H_ref` the profile's `reference_height`, `k_ref` one of its roll coefficients
and `H` the cover's `height`:

- **Roll.** A shorter curtain makes a thinner roll, so a shorter cover is *more*
  linear than the one the profile was measured on:
  `roll = √(1 + (k_ref² − 1) × H / H_ref)`. The formula is applied to **each**
  direction separately: `closing_roll` from the profile's closing roll,
  `opening_roll` from its opening roll. With a single `roll:` in the profile the two
  are the same number and come out the same.
- **Slat time.** The slat gap is proportional to the number of slats, and so to the
  height: `slat_time = slat_time_ref × H / H_ref`.
- **Curtain time.** The curtain time follows the roll growth rather than the height,
  and it is the **closing** roll that sets the scale — one scale for both run times,
  and the descent is the direction the model is anchored on:
  `scale = (closing_roll − 1) / (k_ref_close − 1)`, or plain `H / H_ref` when the
  profile is linear coming down (`k_ref_close = 1`).
- **Run times.** The slat phase is added back to the scaled curtain phase:
  `opening_time = slat_time + (opening_time_ref − slat_time_ref) × scale`, and the
  same for `closing_time`.

Worked example — the `tall` profile above (195 cm, 22.3 / 21.7 / 4.7 s, roll 1.6 in
both directions) applied to a cover declared `height: 120`:

| Step | Computation | Result |
|---|---|---|
| Height ratio | `120 / 195` | `0.615` |
| `roll` (both directions) | `√(1 + (1.6² − 1) × 0.615)` = `√1.96` | **`1.40`** |
| Curtain scale | `(1.40 − 1) / (1.6 − 1)` | `0.667` |
| `slat_time` | `4.7 × 0.615` | **`2.9 s`** |
| `opening_time` | `2.9 + (22.3 − 4.7) × 0.667` | **`14.6 s`** |
| `closing_time` | `2.9 + (21.7 − 4.7) × 0.667` | **`14.2 s`** |

Had that profile carried the measured pair `closing_roll: 1.69` /
`opening_roll: 2.12` instead of the single `roll: 1.6`, the same 120 cm cover would
get `closing_roll` `√(1 + (1.69² − 1) × 0.615)` = **`1.46`**, `opening_roll`
`√(1 + (2.12² − 1) × 0.615)` = **`1.77`**, and a curtain scale of
`(1.46 − 1) / (1.69 − 1)` = `0.672` — the run times barely move, the two estimates
in between do.

(The integration keeps full precision internally and rounds only for display: times
to 0.1 s, roll coefficients to 0.01.)

Two cases worth spelling out:

- a cover with a `profile` and **no** `height` gets the profile's numbers as they
  are, unscaled — right for a cover the same size as the reference one;
- a cover with a `height` and **no** `profile` scales nothing. The key is then only
  documentation, published as the `Height` attribute.

The derivation assumes the covers are the same product: same motor, same slat
profile, same tube. A cover with a visibly different motor should be measured on its
own — either with its own keys, or with a second profile.


### Calibrating a cover

With a stopwatch, for the two run times:

1. Close the cover completely (`cover.close_cover`) and let it stop by itself.
2. Command `cover.open_cover`, start the stopwatch **when the curtain starts to
   move** (about half a second later — that half second is `start_delay`, not part
   of the run) and note two moments:
   - the instant the **bottom edge leaves the floor** → that is `slat_time`
     (typically 2-4 s);
   - the instant the cover **stops at the top** → that is `opening_time` (the full
     upward run).
3. Time the way back down (`cover.close_cover`, until the motor stops by itself) →
   `closing_time`. If it is within a second of the upward run, `opening_time` alone
   is enough; `closing_time` falls back to it.
4. Reload the integration and check `set_cover_position: 50`: consistent overshoot
   means the times are too large, stopping short means too small. If you added an
   allowance for the bus to these times before 0.4.4 — a few tenths to stop the
   shutter falling short — take it back off: the integration now models the delay at
   each end, and a padded time is counted twice.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      opening_time: 30     # full run, both directions
      slat_time: 3         # the first/last 3 s only move the slats
    bedroom_shutter:
      where: "82"
      name: "Bedroom Shutter"
      slat_time: 3
      opening_time: 32     # this motor is slower going up
      closing_time: 28
```

A stopwatch cannot measure the roll, though, and it is what decides where 50 %
lands. For that the integration has two actions that drive the cover, take the
centimetres you measured on it and solve the model, one direction at a time:
`myhome.cover_calibration_run` and `myhome.cover_calibration_compute` (see
[Services and events](services-and-events.md#myhomecover_calibration_run)). The
step-by-step procedure, including how to reuse the result on the other covers of the
house, is
[Recipes → Calibrating a shutter in centimetres](recipes.md#calibrating-a-shutter-in-centimetres).

The loaded values are exposed on basic covers as the `Opening time` and
`Closing time` attributes and either `Roll` — when the two directions agree — or
`Opening roll` and `Closing roll`, plus `Slat time`, `Height` and `Profile` when
they are set.

See [Recipes → Covers](recipes.md#covers) for tuning the travel times,
`set_cover_position` behaviour, "closed with the slats open" and `inverted` wiring.

## Binary sensor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `who` | `"25"` \| `"1"` \| `"9"` | `"25"` | `25` dry contact / alarm zone, `1` motion sensor (lighting bus), `9` auxiliary. |
| `class` | binary sensor device class | by WHO | Default `opening` for WHO 25, `motion` for WHO 1, none for WHO 9. |
| `inverted` | boolean | `false` | Invert the reported state. |

Notes:

- A binary sensor is the **main entity** of its device, like a light or a cover:
  its friendly name is the device `name` (or `entity_name` when set), with no
  device-class word appended. Entity ids are unchanged — only the friendly name is.
- **WHO 1 supports `class: motion` only.** A WHO 1 binary sensor declared with any
  other class is a configuration error: the load stops with the key path of the
  offending device and a repair issue in *Settings → System → Repairs*. Motion
  sensors live on the lighting bus and are the only WHO 1 input this platform
  models; for a dry contact use WHO 25.
- **A WHO 9 auxiliary channel cannot be polled.** The bus never answers a status
  request for one, so the entity starts as `unknown` after a fresh install and only
  takes a value when the first auxiliary frame arrives. Across a restart or a reload
  it restores its last known state instead of going back to `unknown`, so an
  automation reading it does not have to wait for the next bus activity. WHO 25 dry
  contacts and WHO 1 motion sensors *are* queried at startup.

## Climate

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `zone` | string | `"#0"` | Thermo zone `"1"`..`"99"`, or `"#0"` for the central unit. `where` is accepted as an alias. A leading zero is accepted and normalised (`'01'` is zone `1`); `"#0"` and `"#0#N"` are written exactly as shown. Because the two spellings are the same device, a file that contains both is refused as a duplicate and the gateway does not load until one is removed. |
| `name` | string | `Zone N` / `Central unit` | Optional. |
| `heat` | boolean | `true` | Heating support. At least one of `heat` / `cool` must be `true`; a zone with both `false` is a configuration error (it could only be switched off). |
| `cool` | boolean | `false` | Cooling support. |
| `fan` | boolean | `false` | Accepted for backward compatibility and **ignored**, with a warning naming the zone: the protocol layer has no fan-speed command, so nothing would ever set or report a fan mode. |
| `standalone` | boolean | `false` | Standalone thermostat (no central unit). |
| `central` | boolean | `false` | Zone driven through the central unit (`#0#N` addressing). |

> **Entity identity.** An address written with a leading zero used to be keyed `4-01`
> while every frame for it arrives as `4-1`: the entity was created, was named, was
> available and stayed `unknown` for ever. Normalising it gives the device key,
> `unique_id`, device and `entity_id` of the unpadded spelling (`4-1`). Nothing that
> worked is renamed — the padded entity never received a frame — and the old, empty
> entity and device are pruned on the first load. The new entity is created before
> that prune, so it takes the same id with a `_2` suffix (`climate.my_zone` →
> `climate.my_zone_2`); the old id is freed by the prune and can be given back to it
> from *Settings → Devices & services → Entities*. Either way, an automation that
> referenced the old `entity_id` has to be pointed at the new one. Because the two
> spellings are the same device, a file that contains **both** is refused as a
> duplicate and the whole gateway does not load — every entity of that gateway, not
> only the two — until one of the two entries is removed.

**Zones with more than one actuator.** A central unit that reports *actuator* status
sends one frame per actuator (`*#4*<zone>#<n>*20*<state>##`). The protocol layer
parses the actuator number `n` but offers no public way to read it, and this
integration will not reach into its internals for a value a future release could
rename — so the frames of a zone's actuators are treated as one. A zone with a valve
and a pump, or one actuator per circuit, therefore reports *Idle* as soon as **any**
one of them switches off, even if another is still running. The value is not stuck.
On a heat-only or cool-only zone — the usual case, since `cool` defaults to `false` —
the actuator's next "on" frame is itself a direction, and the zone goes straight back
to *Heating* (or *Cooling*). On a `heat: true, cool: true` zone that frame carries no
direction, so it hands the mode/temperature derivation back its job and the
temperature readings drive `hvac_action` again. A central unit that also reports
*valve* status keeps the direction the valve named through an actuator
frame that only says *active* — that one no longer overrules it. An actuator **off** is
still taken as the zone's answer there too, so the *Idle*-on-any-off limitation above
applies to such a plant as well, until the next valve frame restores the direction.
Only two cases are exact: a zone with a single actuator — the usual one — and a
central unit that reports *valve* status and no per-actuator status at all.

## Sensor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `class` | `power` \| `energy` \| `temperature` \| `illuminance` | **required** | Sensor type. `power` and `energy` are both WHO 18 meters: `power` creates the Power entity plus the three energy totalisers; `energy` creates the three totalisers only (Energy today / this month are disabled by default) and never arms the instant-power stream, so the `keepalive_minutes` and filter keys have no effect on it. `temperature` is WHO 4 (WHERE = zone), `illuminance` WHO 1. The zone is `1`-`99`, or a secondary probe written `<sensor><zone>` (`'302'` is probe 3 of zone 2). An address whose zone part is `0` — `'0'`, `'00'`, `'100'`, `'200'`…`'900'`, `'1000'` — is **refused**: the bus reports every one of those frames as the central unit (`4-#0`), which is a `climate:` device with `zone: "#0"`, never a temperature sensor. A temperature probe is addressed by zone, so a leading zero in its `where` is accepted and normalised (`'01'` is `1`, `'0302'` is `302`) — see the note below. Because the two spellings are the same device, a file that contains both is refused as a duplicate and the gateway does not load until one is removed. |
| `who` | string | from `class` | Only needed to override the WHO implied by the class (must match). |
| `keepalive_minutes` | integer 0-255 | `125` | Power meters only: the integration asks the meter to push instant power for this many minutes and renews the request by itself. `0` disables the automatic keep-alive. |
| `min_delta_w`, `min_interval_sec`, `suppress_log_interval_sec`, `info_log_interval_sec` | number | see [Energy monitoring](energy.md) | Per-sensor overrides of the power filtering defaults. |
| aliases | – | – | `refresh_period` and `refresh_period_sec` are accepted for `min_interval_sec`, and `energy_min_delta_w` / `energy_min_interval_sec` / `energy_suppress_log_interval_sec` / `energy_info_log_interval_sec` for their canonical counterparts. The canonical key wins if both are given. See [Energy monitoring](energy.md#sensor_defaults). |

Units are fixed by the class (W, Wh, °C, lx). Energy filtering, totals and
`keepalive_minutes` are covered in full in [Energy monitoring](energy.md).

> **Entity identity.** An address written with a leading zero used to be keyed `4-01`
> while every frame for it arrives as `4-1`: the entity was created, was named, was
> available and stayed `unknown` for ever. Normalising it gives the device key,
> `unique_id`, device and `entity_id` of the unpadded spelling (`4-1`). Nothing that
> worked is renamed — the padded entity never received a frame — and the old, empty
> entity and device are pruned on the first load. The new entity is created before
> that prune, so it takes the same id with a `_2` suffix (`sensor.hall_probe` →
> `sensor.hall_probe_2`); the old id is freed by the prune and can be given back to
> it from *Settings → Devices & services → Entities*. Either way, an automation that
> referenced the old `entity_id` has to be pointed at the new one. Because the two
> spellings are the same device, a file that contains **both** is refused as a
> duplicate and the whole gateway does not load — every entity of that gateway, not
> only the two — until one of the two entries is removed. An address the bus can only
> read as the central unit is refused rather than normalised, because there is
> nothing to normalise it to.

Only WHO 4 addresses are normalised this way. A WHO 18, WHO 9, WHO 25 or WHO 1
sensor keeps whatever text the bus writes, so padding is self-consistent there.

## Scenario control (CEN / CEN+)

A CEN or CEN+ scenario control is a wall keypad: it commands the bus directly and
never reports a state, so Home Assistant only ever learns that a button *was*
pressed. Its presses have always been on the Home Assistant event bus as
`myhome_cenplus_event` / `myhome_cen_event` (see
[Services and events](services-and-events.md#cen-keypad-events)) and nothing about
that changed. Declaring the control under `scenario_control:` adds two things on
top, since **0.4.0**:

- a **device** with one **event entity**, so the last press is visible in the state
  machine and in history (`event.<name>_scenario_control`);
- **device triggers**, so "Button 2 held down on Living Room Keypad" can be picked
  from the automation editor instead of hand-written event triggers.

Controls you do not declare keep working exactly as before, firing the bus events
and creating no entity.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  scenario_control:
    keypad_living_room:
      object: 25              # CEN+ object number
      name: "Living Room Keypad"
      buttons: [1, 2, 3, 4]

    keypad_hall:
      protocol: cen
      where: "51"             # CEN address
      name: "Hall Keypad"
      buttons: [1, 2]
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | – | Device name in Home Assistant. |
| `protocol` | `cen_plus` \| `cen` | No | `cen_plus` | Which of the two protocols the control speaks. |
| `object` | integer 1-2047 | Yes for `cen_plus` | – | CEN+ object number: the event frame's WHERE without its leading `2` (WHERE `225` → `object: 25`, WHERE `2100` → `object: 100`), i.e. the number the bus event reports as `object`. A CEN+ *command* addresses the same control as `#25`, but no event ever carries that form. Not allowed for `cen`. |
| `where` | string of digits | Yes for `cen` | – | CEN address `1`-`2047`, as it appears in the `*15*…*<where>##` frame (`0` is the CEN general address and is refused). Not allowed for `cen_plus`. |
| `buttons` | list of integers | No | `[1, 2, 3, 4]` | Which pushbuttons the automation editor should offer. CEN+ buttons are `1`-`32`, CEN buttons are `0`-`31`; the default is the same for both protocols, so a CEN keypad whose first key is number `0` should declare its `buttons` explicitly. |
| `entity_name`, `icon`, `manufacturer`, `model` | string | No | see below | The common cosmetic keys; `model` defaults to `CEN+ scenario control` / `CEN scenario control`. |

Notes:

- `buttons` is **not a filter**: a press on a button you did not list still fires
  the bus event and still updates the event entity. It only decides which
  combinations the trigger picker shows, so a 4-button keypad does not produce a
  32-entry dropdown.
- The device key is `cenplus-<object>` / `cen-<where>`, so a CEN control and a CEN+
  control may carry the same number without colliding. Declaring the same address
  twice is a validation error, as for any other platform.
- A CEN address is normalised to its unpadded form (`"051"` and `"51"` are the same
  control), because that is how the bus writes it.
- The event entity's `event_types` are exactly the event names of the protocol —
  see the [event tables](services-and-events.md#cen-keypad-events). CEN+ adds the
  long-press repeat and the four rotary events; CEN has the release after a short
  press instead. Beware that the four CEN names describe different gestures from
  the CEN+ ones: on CEN, `pushbutton_short_press` fires at the start of *every*
  press, long ones included, and `pushbutton_long_press` repeats while the button
  is held. Use `pushbutton_short_release` for "the user tapped the button" — see
  [CEN keypad events](services-and-events.md#cen-keypad-events-1).
- `interface:` is **not supported** for scenario controls — writing it produces the
  "unknown key" warning and has no effect. A CEN control is identified by its WHERE
  alone, so a CEN keypad on an F422 local bus and one on
  the main bus with the same WHERE are indistinguishable; declare only one of them.

See [Recipes → CEN+ keypads](recipes.md#cen-keypads) for automations, blueprints
and the device-trigger UI.

## Lock/Unlock buttons

Lights, switches and covers with `lock_buttons: true` get two configuration buttons (**Lock** / **Unlock**) that disable/enable the actuator on the bus (`*14*...`). They are only generated for Point-to-Point WHEREs: locking a General or Area WHERE would disable every actuator of the plant. Buttons are off by default; existing installations that relied on the automatically generated buttons must opt in per device.

See [Recipes → Lock/Unlock buttons](recipes.md#lockunlock-buttons) for a full example and an automation built on it.

## Multiple gateways

Use the MAC address of each gateway as the root key (a `gateway:` block may coexist with MAC root keys; every MAC must be unique):

```yaml
# First gateway
"00:03:50:AA:BB:CC":
  light:
    kitchen_light:
      where: "15"
      name: "Kitchen Light"

# Second gateway
"00:03:50:DD:EE:FF":
  cover:
    garage_door:
      where: "25"
      name: "Garage Door"
      class: garage
```

Each gateway also needs its own config entry (discovered or manual) with the same MAC. See [Recipes → Several gateways](recipes.md#several-gateways) for the service-call syntax once more than one gateway is loaded.

## Custom icons and device classes

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  light:
    accent_lighting:
      where: "45"
      name: "Accent Lighting"
      dimmable: true
      icon: "mdi:led-strip-variant"
      icon_on: "mdi:led-strip-variant"

  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      class: shutter
      shutter_run: 30
      icon: "mdi:window-shutter"
      lock_buttons: true

  binary_sensor:
    window_sensor:
      where: "301"
      name: "Living Room Window"
      class: window          # `device_class: window` is accepted too
      icon: "mdi:window-open"
```

## State attributes

Every MyHOME entity carries a few read-only attributes describing where it lives on
the bus. They are set once, at startup, and are visible in **Developer tools →
States** and in `state_attr(...)` templates.

| Attribute | On | Value |
|---|---|---|
| `A` / `PL` | Lights, switches, covers, Lock/Unlock buttons, illuminance sensors and WHO 1 motion sensors with a Point-to-Point WHERE | The two halves of the WHERE: `A` is the ambient, `PL` the light point (`"15"` → `A: 1`, `PL: 5`; `"0115"` → `A: 01`, `PL: 15`). |
| `Where` | The same entities with a General, Area or Group WHERE | The WHERE verbatim: cutting `"0"` or `"#3"` in half would mean nothing. |
| `Int` | Any of the above with an `interface:` | The F422 bus interface, unpadded (`"3"`). |
| `Opening time`, `Closing time`, `Roll` / `Opening roll` + `Closing roll`, `Slat time`, `Height`, `Profile` | Basic covers | The cover model actually loaded: the two travel times in seconds and the roll are always there — as a single `Roll` when the two directions carry the same coefficient, as `Opening roll` and `Closing roll` when they differ. `Slat time` appears when it is greater than `0`, `Height` and `Profile` when the keys are written. Times are rounded to 0.1 s and roll coefficients to 0.01 for display. The `Shutter run` attribute of 0.4.1 and earlier is gone — it was `Opening time` under another name. |
| `Sensor` | WHO 25 dry contacts | The WHERE split as OpenWebNet writes it, `(<type>)<number>`: `301` renders as `(3)01`, i.e. dry contact number `01`. Type `3` is a dry contact, type `4` an IR detector. A WHERE of any other shape is reported verbatim. |
| `Auxiliary channel` | WHO 9 auxiliary binary sensors | The WHERE, verbatim. |
| `Timeout`, `Sensitivity` | WHO 1 motion sensors | How long the entity waits before going back to *off*: the sensor's own motion timeout plus a 15 s margin. Both are requested from the sensor when the entity is added and show a default (`315` s, `medium`) until it answers. `Sensitivity` is the PIR level as a word — `low`, `medium`, `high` or `very high`. |
| `event_type`, `pushbutton`, `protocol`, `buttons`, `object` / `where` | Scenario controls | The last press and the control's identity — see [Services and events](services-and-events.md#device-triggers-and-event-entities). |

Power, energy and temperature sensors and climate zones carry no address
attributes: a WHO 18 meter WHERE or a thermo zone number has no A/PL split to
report.

## Validation errors

`myhome.yaml` is validated on every (re)load. Errors block the setup and are shown in the integration card with the key path (`gateway.cover.<key>.where`); warnings only appear in the log. Typical messages:

- **`required key not provided`**: `where` and `name` are mandatory (climate: `zone`/`name` optional).
- **an invalid or ambiguous `where`**: either the address is not a valid OpenWebNet WHERE, or it was written unquoted in a shape that could mean two things. The message echoes the value you actually wrote and asks for quotes on every `where:` in the file: a leading zero is already gone by the time the validator runs, so this is advice, not a diagnosis of that one value. Quoting is necessary, not sufficient — a 3- or 5-digit address is a sensor address and is refused on a light, a switch or a cover whether it is quoted or not — and a negative value is refused outright, with its own message, since no platform has a negative address.
- **`Duplicate WHERE 'x' (who N): cover 'a' collides with cover 'b'`**: the same device is declared twice; fix the address or remove one of the two entries (both YAML keys are named). When the two entries spell the address differently — `'01'` and `'001'` are the same WHO 4 zone — the message quotes **both** spellings as the file writes them (`… collides with climate 'living_room', which writes it '01'`) and says that addresses are compared after they are normalised.
- **a cover with both `opening_time` and `shutter_run`, set to different values**: `shutter_run` is the legacy alias of `opening_time`, so the two cannot disagree. The message names both keys; drop one of them.
- **a cover whose `profile:` names no entry of `cover_profiles:`**: the message lists the profile names that are defined for that gateway. See [Cover profiles](#cover-profiles).
- **`sensor 'x' is missing the required sensor class`**: add `class: power|energy|temperature|illuminance`.
- **`sensor 'x': WHERE '0' is the central unit's address, not a probe's`**: a WHO 4 temperature probe is addressed by zone (`1`-`99`, or `<sensor><zone>`). The central unit is a `climate:` device with `zone: "#0"`.
- **a WHO 1 `binary_sensor` with a `class` other than `motion`**: WHO 1 inputs are modelled as motion sensors only. Drop the class, or move the device to `who: "25"` if it is a dry contact.
- **`scenario_control 'x' is missing the required 'object'`** / **`a CEN control is addressed by 'where', not by 'object'`**: a CEN+ control needs `object`, a CEN control needs `where`; never both.
- **`scenario_control 'x': pushbutton N is out of range for protocol …`**: CEN+ buttons are 1-32, CEN buttons are 0-31.
- **`scenario_control 'x': CEN address '0' is out of range (1-2047)`**: a CEN `where` must be 1-2047, like a CEN+ `object`.
- **`'interface' is only supported for WHO 1/2/15 devices`**: the F422 interface was written on a temperature, auxiliary, energy or dry-contact sensor, whose frames never carry it. Remove the key; see [Local bus interfaces](#local-bus-interfaces-interface).
- **`climate 'x': at least one of 'heat' / 'cool' must be true`**: a zone that can neither heat nor cool has nothing to control.
- **`gateway 'x' needs a 'mac'`** / **`configured twice`**: every root entry needs a MAC (as `mac:` or as the root key) and each MAC may appear once.
- **`unknown key 'dimable' in light.x is ignored (did you mean 'dimmable'?)`** (WARNING): a typo or an unsupported key; the device is still created without it.

See [Troubleshooting → Configuration issues](troubleshooting.md#configuration-issues) if the integration will not load after an edit.
