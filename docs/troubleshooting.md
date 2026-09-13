# Troubleshooting

Common issues, debug logging, and upgrading from the pre-`myhome.yaml` versions.

## Contents

- [Gateway connection issues](#gateway-connection-issues)
- [Device discovery issues](#device-discovery-issues)
- [Configuration issues](#configuration-issues)
- [Cover position issues](#cover-position-issues)
- [Repairs](#repairs)
- [Diagnostics download](#diagnostics-download)
- [Debug logging](#debug-logging)
- [Migration from the original integration v0.8 and earlier](#migration-from-the-original-integration-v08-and-earlier)

## Gateway connection issues

1. **Check network connectivity**: Ensure Home Assistant can reach the gateway IP
2. **Verify gateway password**: Ensure the password is correct
3. **Check firewall settings**: Ensure port 20000 is accessible
4. **Review logs**: Check Home Assistant logs for connection errors

## Device discovery issues

**"Discovery not active" in logs:**
- Ensure you are calling the action correctly: `action: myhome.start_discovery`
  with `gateway: "00:03:50:AA:BB:CC"` (the `gateway` field is only needed with
  more than one gateway loaded)
- Do not put action calls in `configuration.yaml` — run them from
  **Developer tools → Actions**, or from an automation or script
- Check that the gateway MAC address is correct
- Confirm the run actually started: the log shows `Starting device discovery (60s)` at INFO

**No devices found during discovery:**
1. **Enable debug logging** to see discovery messages:
   ```yaml
   logger:
     logs:
       custom_components.myhome.discovery: debug
       custom_components.myhome.gateway: debug
       custom_components.myhome.config_flow_discovery: debug
   ```
2. **Check discovery status** — with `custom_components.myhome.discovery: debug`,
   a healthy run logs, in order:
   - `Starting device discovery (60s)` (INFO)
   - ``Discovery status request `*#1*0##` `` — then the same for `*#2*0##`,
     `*#4*0##`, `*#18*0##` and `*#9*0##`, half a second apart. There is no WHO 25
     request: dry contacts and CEN/CEN+ keypads are only seen when they emit a frame
     during the run (see [Discovery](discovery.md))
   - `Discovered bus_dimmer at WHO=1 WHERE=11` (INFO), once per new device
   - `Discovery completed: N device(s) seen` (INFO)
   - `Discovery finished: N suggestion(s) (M new) written to <path>` (INFO). When
     the run saw something it could not suggest, the same line ends with
     `N device(s) must be declared by hand under scenario_control: (...)` and/or
     `N device(s) belong to a family this integration has no support for (...)`;
     a run that suggested nothing at all logs those clauses on their own

   The suggestions are then flushed to `myhome_discovered.yaml`. Nothing is ever
   written to `myhome.yaml`.
3. **Verify device responses** - Look for incoming messages after discovery commands
4. **Check gateway communication** - Ensure devices are responding to status requests
5. **Manual device test** - Try controlling devices through other MyHOME apps first

**Incorrect device type detection:**
- **Dimmer vs switch**: discovery classifies on what the actuator answered.
  - A frame carrying a brightness, or a preset level (WHAT 2–10, 8 included),
    is classified as a **dimmer** and the suggestion carries `dimmable: true`.
  - A frame carrying only ON/OFF (WHAT 0 or 1) is classified as an on/off
    **switch**, and the discovered device carries the note *"Detected as on/off
    switch; set `dimmable: true` manually for dimmers"*.
  - Because the classification depends on the state the device happened to be
    in, a dimmer that was fully on (WHAT 1) when discovery ran is reported as a
    switch. Set `dimmable: true` by hand — it is the expected correction, not a
    bug.

**Devices discovered but suggestions missing:**

See [Discovery](discovery.md) — since 0.2.0, suggestions go to `myhome_discovered.yaml`, not `myhome.yaml`.

1. **Check `myhome_discovered.yaml`** exists and has grown after a discovery run.
   If a `myhome_discovered.yaml.new` sits next to it, your `myhome_discovered.yaml`
   is not valid YAML and the suggestions went to the sibling instead — the
   *"Discovery finished"* line in the log names the file that was written.
2. **Verify file permissions** - ensure Home Assistant can write to that folder.
3. Discovery only runs for the duration of `myhome.start_discovery` (default
   60 s) or until `myhome.stop_discovery` is called; both flush whatever was
   collected so far to the file.
4. A device already present in `myhome.yaml` (matched on WHO, WHERE and bus
   interface) is not suggested again — a device behind an F422 interface and the
   main-bus device with the same WHERE are two different devices. A CEN / CEN+
   scenario control already declared under `scenario_control:` is matched instead on
   the key the integration really stores it under (`cenplus-<object>` for CEN+,
   `cen-<where>` for CEN), and is left out of the closing report. That key carries no
   F422 bus interface, so declaring the main-bus keypad covers the riser keypad at the
   same address as well.

## Configuration issues

1. **Validate YAML syntax**: Ensure `myhome.yaml` has correct formatting
2. **Check device addresses**: Verify WHERE addresses match physical devices
3. **Review device types**: Ensure correct platform assignments
4. **Reload the integration** after every `myhome.yaml` change: *Settings →
   Devices & services → MyHOME → ⋮ → Reload*. A full Home Assistant restart is
   not needed — the file is re-read and re-validated on every reload.

See [Configuration → Validation errors](configuration.md#validation-errors) for
the exact error messages the integration produces.

## Cover position issues

**The 50 % position lands too low / too high:**

If the two end stops are right — `cover.open_cover` and `cover.close_cover` reach
them, and the entity reads `100` and `0` there — but the middle of the travel is
consistently off in the same direction, the run times are not the problem: the
`roll` is. A rolling shutter travels faster with the curtain up (fat roll on the
tube) than with it down, so a linear estimate stops a basic actuator too low on the
way down and too high on the way up. See
[Configuration → Why the position is not linear](configuration.md#why-the-position-is-not-linear-roll).

1. Check the `Roll` attribute of the cover in **Developer tools → States** — or
   `Opening roll` and `Closing roll`, which is what you get instead when the two
   directions carry different coefficients. Covers of `class: shutter` default to
   `1.6` in both directions since 0.4.2; anything else defaults to `1.0`, the old
   linear estimate.
2. Measure the real values once with the
   [guided calibration](guided-calibration.md) — *Configure → "Calibrate a
   shutter"*, which measures and stores them for you — or by hand with
   [Recipes → Calibrating a shutter in centimetres](recipes.md#calibrating-a-shutter-in-centimetres),
   and apply them on that cover or as a profile shared by every shutter of the same
   kind.
3. **If it misses going up but not coming down** (or the other way round), one
   coefficient cannot describe both directions — which is common, since a shutter is
   not symmetrical under load. Measure both directions in that recipe and write the
   `opening_roll` / `closing_roll` pair it gives you rather than a single `roll`.
4. If instead the cover misses *everything*, end stops included — it stops short of
   the top, or keeps running after the position reads `100` — the run times are
   wrong; re-measure `opening_time` and `closing_time` with a stopwatch first, then
   calibrate.
5. If it is the first few centimetres off the floor that are wrong, and the position
   sits at `0` while the slats are still moving, that is `slat_time`, not the roll:
   stopwatch it (the calibration never solves it for you) — see
   [the two-phase travel model](configuration.md#the-two-phase-travel-model-slat_time).

**The guided calibration will not measure a shutter:**

The dialog under *Configure → "Calibrate a cover"* times a run from the
actuator's own "moving" status, so it needs the shutter to report that it has
started. When it does not, the step stops with *"the cover did not answer"*; when
the gateway never wrote the frame at all, with *"the command never reached the
bus"*. Check that nothing else is driving the shutter — a wall pushbutton, an
automation, another dialog — and repeat the step. If it fails every time, that
actuator does not relay its own status and only the manual
[recipe](recipes.md#calibrating-a-shutter-in-centimetres) can measure it.

A shutter missing from the list is declared `advanced: true` (it reports its own
position and has nothing to calibrate), and a whole gateway of those hides the menu
item altogether. A dialog left open too long releases the shutter — 30 minutes on a
screen with nothing moving, 10 after a movement — and the next click lands on
*"session expired"*: nothing was saved, and the measurements have to be taken
again. The rest is in [Guided calibration →
Troubleshooting](guided-calibration.md#troubleshooting).

**Several covers moved together stop at different heights than one at a time:**

Fixed in **0.4.3**. Until then a cover timed its run from the moment the command was
queued, while the frame itself left for the bus about a tenth of a second later per
command already waiting; a scene moving twelve shutters at once stopped them 5 to 14 cm
too high on a 195 cm window, the last one of the scene worst, while the same covers
driven one at a time were exact. The run is now timed from the instant the frame is
written, and a stop frame is written before anything still waiting for the *other*
covers — never before a frame of its own cover, which would end a run that had not
started.

If a scene still lands differently from a single command after 0.4.3:

1. Download the [diagnostics](#diagnostics-download) right after running the scene and
   look at `handler`: a `queue_size` (and `stats.queue_length`) that stays high, or a
   `stats.commands_dropped` that grows, means the frames are not merely late but
   backing up or being lost, which no timing model can repair. `recent_frames` shows
   what actually went out, and when.
2. Check `command_worker_count` in `effective_options` (**Configure** on the
   integration page). One worker is the default and one is enough for the timing; more
   of them shorten a long queue, at the cost of one command session per worker on a
   gateway that holds only a handful — see [Gateway compatibility → Note 3 — session
   limits](gateway-compatibility.md#note-3--session-limits).
3. If the covers land consistently off in the *same* direction whether they run alone
   or together, it is the model and not the queue: go back to the `roll` above.

A basic actuator never reports its position, so this is always an estimate. Running
the cover fully open or fully closed re-synchronises it.

**Runs that start from an intermediate position stop short, but full runs land fine:**

Fixed in **0.4.4**. Until then a run was timed from the moment its frame reached the
bus, but the motor only starts turning a fixed while later and keeps turning a fixed
while after the stop frame; a run that started and ended at an end stop absorbed both
costs into the calibration, while a run that started or ended in the middle of the
travel did not — on a 195 cm shutter that meant 3-4 cm too high on a descent, 5-9 cm
too low on an ascent. The run is now timed from the actuator's own "moving" status
(`start_delay`, default `0.5` s, as a fallback when nothing relays it), and the stop
is written `stop_latency` (default `0.1` s) before the modelled end so the motor
coasts onto the target.

If a shutter still stops short of an intermediate target after 0.4.4, check the
`Start delay` / `Stop latency` attributes (published only when they differ from the
defaults) and, if your gateway starts or stops noticeably slower or faster than that,
tune `stop_latency` and `start_delay` on the cover or its profile — see
[Configuration → Cover](configuration.md#cover). If you
had added a bus allowance to `opening_time` / `closing_time` before 0.4.4 to work
around this, take it back off: the delay is now modelled at each end, and a padded
time is counted twice.

## Repairs

Configuration problems are reported in **Settings → System → Repairs**, not only in
the log. Three issues can come from this integration:

- **MyHOME configuration file is invalid** (error). `myhome.yaml` could not be read,
  parsed or validated; the issue shows the file path and the exact validator message
  (the same text as on the integration card). Nothing is created until it is fixed.
  Correct the file, then reload the integration (⋮ → Reload) — the issue disappears
  on its own.
- **Unknown keys in the MyHOME configuration file** (warning). The file has keys the
  integration does not know. They are *ignored*, never fatal — the issue lists them
  with a "did you mean" suggestion, which usually points straight at a typo
  (`dimable` → `dimmable`). If the keys are there on purpose (comments, your own
  bookkeeping), dismiss the issue.
- **No devices configured for this MyHOME gateway** (warning). The MAC address of the
  configured gateway has no section in the file, so it got no devices. Check the MAC
  in the file against the one on the integration card; the issue lists the gateways
  it *did* find in the file.

Each issue is re-evaluated on every load: fix the cause and reload, and it clears.

## Diagnostics download

For a bug report, attach a diagnostics file rather than a screenshot of the log:

1. **Settings → Devices & services → MyHOME**.
2. On the integration card, **⋮ → Download diagnostics** (for a single device, open
   the device page and use its own **⋮ → Download diagnostics** — it adds that
   device's validated configuration).
3. Attach the JSON file to the
   [issue](https://github.com/Interstellar0verdrive/MyHOME-stability/issues).

What is inside:

| Section | Content |
| --- | --- |
| `versions` | Integration, OWNd and Home Assistant versions. |
| `entry` | The config entry, **without the password**, with its **title redacted** (you may have renamed it, and a renamed gateway commonly carries a household or family name), with MAC, host, UDN, SSDP location and the entry's own `unique_id` partially masked; the configuration file is reported by its file name only, never with its directory. |
| `effective_options` | The tunables actually in effect (see [Configuration → Options](configuration.md#options)), including `config_file_name` and `config_file_is_default_location` — whether `myhome.yaml` sits where the integration would look for it by default. An entry that never set the option reports the default file name and `config_file_is_default_location: true`, which is what that entry actually uses. `command_worker_count` is the number of command sessions really opened: the setup clamps a stored value above the maximum, and this is the clamped one. |
| `config` | A *summary* of the validated `myhome.yaml`: `gateway_keys` (the sorted list of gateway-level keys present in the file, such as `mac` or `sensor_defaults`), then per platform the device count and the `who-where` device keys. Your device names are not included — in the per-device download either, where the device's own `name` and `entity_name` are replaced by `**REDACTED**`. That is true of the file's **contents**. The **file name** Home Assistant proposes for a per-device download is built by Home Assistant out of the device name (`myhome-<entry id>-<device name>-<device id>.json`) and no integration can change it, so rename the file before attaching it to a public issue — or attach the entry-level download instead, whose file name carries no name at all. |
| `handler` | Gateway statistics (connected, frames received, last frame, reconnects, commands sent/dropped, queue length, session state), whether the listening and sending loops are running and how many there are, whether authentication failed, whether raw events are generated, and the session timings in effect. |
| `recent_frames` | The last 50 bus frames with their timestamps and direction — usually the fastest way to see what the gateway is actually saying. |

Session-negotiation frames (`*99*…##` and the nonce/password-hash exchange) are
replaced by a `**REDACTED (session negotiation)**` marker, so the file is safe to
attach to a public issue. It is still worth a look before you upload it.

For a *live* view of the same numbers, the gateway device carries diagnostic
entities: the connectivity binary sensor and the "last frame" timestamp are enabled
by default; the reconnect, dropped-command and queue-length counters are disabled by
default and can be enabled from the entity settings.

## Debug logging

Enable debug logging to troubleshoot issues:

```yaml
logger:
  default: warning
  logs:
    custom_components.myhome: debug
    OWNd: debug
```

> **Note:** For day-to-day use, keep `custom_components.myhome` at `info` (or leave the `logger:` block out entirely) — per-frame bus traffic is only logged at `debug`. Occasional "reconnecting" INFO lines after a gateway hiccup are expected; the integration retries and recovers on its own. Use `debug` only when troubleshooting.

## Migration from the original integration v0.8 and earlier

If you are upgrading from `anotherjulien/MyHOME` **v0.8 or earlier** — the
releases that were configured in `configuration.yaml`, before `myhome.yaml`
existed:

1. **Create myhome.yaml**: Move device configurations from `configuration.yaml`
2. **Update device structure**: Follow the new YAML format below
3. **Remove old configuration**: Delete MyHOME entries from `configuration.yaml`
4. **Restart Home Assistant**: Required for new configuration to take effect
5. **Use auto-discovery**: Consider using the new discovery features

**Old format (configuration.yaml):**
```yaml
myhome:
  gateways:
    - host: 192.168.1.10
      devices:
        light:
          - where: "15"
            name: "Living Room"
            dimmable: true
```

**New format (myhome.yaml):**
```yaml
"00:03:50:AA:BB:CC":
  light:
    living_room:
      where: "15"
      name: "Living Room"
      dimmable: true
```

If you are instead upgrading from a more recent `anotherjulien/MyHOME` or
`artmakh` release (already using `myhome.yaml`), see
[Migrating from the original](migrating-from-original.md) instead.
