# Energy monitoring

How instant power is kept alive and filtered, how the daily/monthly/total
entities work (and what to do when your gateway does not fill them in), and the
full `sensor_defaults` parameter reference. See
[Configuration → Sensor](configuration.md#sensor) for the base sensor schema.

## Contents

- [Instant power keep-alive](#instant-power-keep-alive)
- [Filtering push updates](#filtering-push-updates)
- [`sensor_defaults`](#sensor_defaults)
- [Daily/monthly/total energy and gateways without totals](#dailymonthlytotal-energy-and-gateways-without-totals)
- [Computing kWh when the gateway returns no totals](#computing-kwh-when-the-gateway-returns-no-totals)

## Instant power keep-alive

Power meters (WHO 18, `class: power`) only push instant-power updates for a
limited time after being asked. The integration sends
`*#18*<where>*#1200#1*<minutes>##` when the entity is added, again on every
gateway reconnection, and then on a timer set to `keepalive_minutes − 5` minutes
(never less than 1 minute), so the stream never lapses.

| `keepalive_minutes` | Effect |
|---|---|
| `125` (default) | Arm for 125 minutes, re-arm every 120 minutes. |
| `1`–`255` | Any other duration. Values are clamped to this range. |
| `0` | Disables the automatic keep-alive entirely — nothing is armed, and `async_update` on the power entity does nothing. |

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  sensor:
    house_main:
      where: "51"
      name: "House Main"
      class: power
      keepalive_minutes: 60
```

To force a request outside the schedule, or to use a one-off duration, call
`myhome.start_sending_instant_power` (see
[Services → myhome.start_sending_instant_power](services-and-events.md#myhomestart_sending_instant_power)):

```yaml
      - action: myhome.start_sending_instant_power
        target:
          entity_id: sensor.house_main_power
        data:
          duration: 30      # minutes, 1-255; omit to use keepalive_minutes
```

## Filtering push updates

Power meters push a value at every fluctuation. An instant-power update is
**processed** if **either** the absolute change vs. the last processed value is
**>= `min_delta_w`** or the time since the last processed value is **>=
`min_interval_sec`**; otherwise it is dropped (totalisers and daily/monthly
energy values are never filtered). The filter is an **OR**: a frame passes if the
delta is big enough **or** enough time has elapsed. Either threshold set to `0`
accepts everything, and the very first sample always passes. When debug logging
is enabled, dropped updates are aggregated and logged at most once per
`suppress_log_interval_sec`.

**The filter applies only to instant active power.** Totaliser, daily and monthly
frames are never filtered.

## `sensor_defaults`

Defaults apply per gateway under `sensor_defaults:` (alias `energy:`; if both are
present they are merged key by key and `sensor_defaults` wins) and can be
overridden per sensor:

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"

  sensor_defaults:
    min_delta_w: 25              # process if |delta| >= 25 W ...
    min_interval_sec: 5          # ... or if the last processed value is older than 5 s
    suppress_log_interval_sec: 60
    info_log_interval_sec: 0
    keepalive_minutes: 125       # 0 disables the automatic instant-power keep-alive

  sensor:
    house_main_power:
      where: "51"
      name: "House Main Power"
      class: power
      min_delta_w: 1          # this meter reports every watt (per-sensor override)
    oven:
      where: "53"
      name: "Oven"
      class: power
```

| Key | Built-in default | Meaning |
|---|---|---|
| `min_delta_w` | `5` | Process an instant-power frame if it differs from the last processed one by at least this many watts. |
| `min_interval_sec` | `1.0` | …**or** if the last processed value is at least this old. |
| `suppress_log_interval_sec` | `60.0` | How often (at most) a DEBUG summary of the suppressed frames is written. |
| `info_log_interval_sec` | `0.0` (off) | If greater than 0, write an INFO line with the accepted value at most this often. |
| `keepalive_minutes` | `125` | See [Instant power keep-alive](#instant-power-keep-alive) above. |

Precedence: per-sensor key → `sensor_defaults`/`energy` → built-in default. Legacy
spellings `energy_min_delta_w`, `energy_min_interval_sec`,
`energy_suppress_log_interval_sec`, `energy_info_log_interval_sec`,
`refresh_period` and `refresh_period_sec` are still accepted; the canonical key
wins when both are present.

## Daily/monthly/total energy and gateways without totals

A `power` sensor also creates daily/monthly/total energy entities, fed by the
gateway's own totaliser replies to `*#18*<where>*54##`, `*#18*<where>*53##` and
`*#18*<where>*51##`. `daily`/`monthly` stay **disabled by default** — enable them
from the entity's settings (gear icon → **Enable**) if your gateway answers
totaliser requests. **Energy** (total) is enabled by default.

Not every gateway does: a MyHOMEServer1 with F520/F521 meters, for instance,
acknowledges the requests without returning data, so on that hardware those
sensors remain `unknown`. See [Gateway compatibility](gateway-compatibility.md)
for what is verified per model, and how to report yours.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"
  sensor:
    total_power:
      where: "51"
      name: "Total Power Consumption"
      class: power           # creates Power + Energy today/month/total entities
      min_interval_sec: 10   # rate-limit push updates (no polling)
      keepalive_minutes: 125 # automatic instant-power keep-alive
      icon: "mdi:flash"
    zone_temperature:
      where: "1"             # thermo zone 1
      name: "Living Room Temperature"
      class: temperature
```

## Computing kWh when the gateway returns no totals

If your gateway does not provide totals, derive energy from the power sensor with
Home Assistant's own helpers instead.

**Step 1 — a Riemann sum integral** (Settings → Devices & services → Helpers →
Create helper → *Integral*), or in YAML:

```yaml
sensor:
  - platform: integration
    source: sensor.house_main_power
    name: House Main Energy
    unique_id: house_main_energy
    unit_prefix: k
    unit_time: h
    method: left
    max_sub_interval: "00:05:00"
```

`method: left` is the right choice for a meter that pushes a new value only when
the load changes: the last reported value is held until the next one arrives.
`max_sub_interval` makes the integral keep accumulating during long stretches with
no new frame — useful because the filter above deliberately suppresses unchanged
readings.

This gives you `sensor.house_main_energy` in kWh with state class
`total_increasing` — usable directly in the Energy dashboard.

**Step 2 — daily and monthly buckets** (Settings → Devices & services → Helpers →
Create helper → *Utility meter*), or in YAML:

```yaml
utility_meter:
  house_main_daily:
    source: sensor.house_main_energy
    name: House Main Daily Energy
    cycle: daily
  house_main_monthly:
    source: sensor.house_main_energy
    name: House Main Monthly Energy
    cycle: monthly
```

If you had already built this before 0.2.0, keep it. It is more robust than the
gateway totals in any case: it survives a gateway that stops answering.
