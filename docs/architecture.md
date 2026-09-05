# Architecture

How the integration works inside. This page is for contributors, and for anyone
who wants to check the claims in the README against the code rather than take
them on trust.

Everything below is from `custom_components/myhome/*.py` at version 0.3.1 and
`OWNd` 0.7.49.

## Module map

| File | Responsibility |
|---|---|
| `__init__.py` | Config entry lifecycle (setup, unload, migration), YAML loading, registry pruning, service registration. |
| `const.py` | Domain, `hass.data` layout keys, the connection signal name, every `myhome.yaml` key constant, defaults, and the discovery device-type tables. |
| `validate.py` | The `myhome.yaml` schema: WHERE/zone/MAC validators, per-platform field sets, alias folding, defaults injection, rekeying to `who-where`, duplicate detection, lock-button generation. |
| `gateway.py` | One `MyHOMEGatewayHandler` per gateway: the event session loop, the command worker(s), the message dispatcher, the instant-power throttle, availability publication, shutdown. |
| `own_session.py` | Thin subclasses of `OWNd`'s `OWNSession` that raise instead of returning `None`, add TCP keepalive, and read a command's replies until its ACK/NACK. |
| `myhome_device.py` | `MyHOMEEntity`, the base class of every entity: availability, device info, registration in `hass.data`, naming rules; plus `address_attributes()`. |
| `config_flow.py` | Config flow (gateway picker, manual entry, SSDP, port, password), reauth flow, options flow. |
| `discovery.py` | The bus-listening discovery service: a 60 s run, message classification, the public `myhome_device_discovered` / `myhome_discovery_completed` events. |
| `config_flow_discovery.py` | Turns discovered devices into YAML suggestions and writes `myhome_discovered.yaml` atomically. Never touches `myhome.yaml`. |
| `light.py` | WHO 1 lights and dimmers (brightness, transition, flash). |
| `switch.py` | WHO 1 actuators driving non-light loads. |
| `cover.py` | WHO 2 shutters: real position on advanced actuators, time-based estimate on basic ones. |
| `climate.py` | WHO 4 thermoregulation zones and central unit. |
| `sensor.py` | Instant power (with the keep-alive), the three energy totalisers, temperature, illuminance; the `start_sending_instant_power` entity service. |
| `binary_sensor.py` | WHO 25 dry contacts, WHO 9 auxiliary channels, WHO 1 motion sensors (with timeout). |
| `button.py` | The opt-in WHO 14 Lock/Unlock buttons. |
| `services.yaml`, `manifest.json`, `translations/{en,fr,it,nl}.json` | Service schemas for the UI, integration metadata and SSDP matchers, translated strings. |

## `hass.data` layout

Only per-gateway dicts, keyed by MAC address, live under `hass.data["myhome"]`:

```python
hass.data["myhome"][mac] = {
    "platforms": {
        "light":  {"1-11": {..., "entities": {"light": <MyHOMELight>}}},
        "cover":  {"2-81": {..., "entities": {"cover": <MyHOMECover>}}},
        "sensor": {"18-51": {..., "entities": {
            "power": <MyHOMEPowerSensor>,
            "total-energy": <MyHOMEEnergySensor>,
            # daily-energy / monthly-energy when enabled
        }}},
        "button": {"2-81": {..., "source_platform": "cover", "entities": {...}}},
    },
    "sensor_defaults": {...},   # merged power filter + keep-alive defaults
    "entity": <MyHOMEGatewayHandler>,
    # plus any unrecognised gateway-level keys, kept verbatim
}
```

The device keys are `"{who}-{where}"`, `"{who}-{where}#4#{interface}"` behind a
bus interface, and `"{who}-{zone}"` for climate. Entities register themselves in
their device's `entities` dict on `async_added_to_hass` and remove themselves on
`async_will_remove_from_hass`.

The bus interface is **zero padded in the device key only** (`1-11#4#03`), because
that key is also the tail of every entity `unique_id`. The `interface` value in the
device config — and therefore every frame the integration sends — is the unpadded
bus form (`11#4#3`). The dispatcher normalises incoming keys
(`gateway._entity_key_candidates`) so both spellings resolve to the same entity.

## Config entry lifecycle

### Setup order

```mermaid
sequenceDiagram
    participant HA as Home Assistant
    participant Init as __init__.async_setup_entry
    participant Val as validate.config_schema
    participant GW as MyHOMEGatewayHandler
    participant Plat as Platforms

    HA->>Init: async_setup_entry(entry)
    Init->>Init: normalise entry.unique_id, read options
    Init->>Val: read + validate myhome.yaml (executor)
    Note over Val: vol.Invalid -> ConfigEntryError<br/>missing file -> created empty + WARNING
    Val-->>Init: {mac: {platforms, sensor_defaults, ...}}
    Init->>Init: hass.data[DOMAIN][mac] = config
    Init->>GW: MyHOMEGatewayHandler(hass, entry, generate_events)
    Init->>Init: hass.data[DOMAIN][mac]["entity"] = handler
    Init->>GW: test() under a 20 s timeout
    Note over GW: OSError/TimeoutError -> ConfigEntryNotReady<br/>None -> ConfigEntryNotReady<br/>password_* -> ConfigEntryAuthFailed
    GW-->>Init: {"Success": true}
    Init->>HA: device_registry.async_get_or_create(gateway device)
    Init->>GW: handler.device_id = <registry id>
    Init->>HA: entry.async_on_unload(handler.close_listener)
    Init->>Plat: async_forward_entry_setups(all 7 platforms)
    Note over Plat: each platform returns early<br/>when it has no devices
    Init->>GW: initialize_discovery_service()
    Init->>GW: start listening_loop() as background task
    Init->>GW: start N sending_loop(worker_id) background tasks
    Init->>HA: prune stale registry entities/devices
    Init->>HA: register services (once per HA instance)
```

Two ordering decisions matter:

- The **handler is created after** `hass.data[DOMAIN][mac]` is populated, because
  it reads its energy defaults from there.
- The **loops start after the platforms are forwarded**, so no bus frame is ever
  dispatched into a half-built entity map.

The whole per-gateway dict is replaced on every setup — never merged into
leftovers from a previous one.

### Unload order

```
stop_device_discovery()
  -> close_listener()          # stop the loops, close sessions, drop the queue,
                               # publish is_connected = False
  -> _async_cancel_workers()   # belt and braces
  -> async_unload_platforms(all 7)
  -> hass.data[DOMAIN].pop(mac)
  -> unregister services if this was the last loaded entry
```

`close_listener()` is idempotent and is also registered through
`entry.async_on_unload`, so a setup that fails half way still closes its sockets.
It is safe to call from inside one of the loop tasks (it skips
`asyncio.current_task()` when cancelling).

Because the connection is closed *before* the platforms are unloaded, every
entity is already `unavailable` when Home Assistant snapshots states for
restoration. That is why `cover.py` persists its position through
`extra_restore_state_data` rather than through the state attributes.

### Migration

`async_migrate_entry` moves entries from version 1 to version 2 by unwrapping the
1-element lists the pre-0.2.0 manual flow stored for `manufacturer`,
`manufacturerURL`, `firmware`, `ssdp_location`, `ssdp_st`, `deviceType`,
`friendly_name` and `UDN`. An entry with a *higher* version than the code returns
`False` rather than corrupting itself.

## The two OpenWebNet sessions

OpenWebNet gateways expose two session types, selected by the first frame after
the greeting:

| Frame | Session | Used for |
|---|---|---|
| `*99*1##` | **event** (monitor) | The gateway pushes every bus frame. One per gateway, permanently open. |
| `*99*0##` | **command** | Send a frame, read its replies, read the ACK/NACK. One per command worker, closed after 60 s idle. |

```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Opening: OWNEventChannel.open(10 s)
    Opening --> Closed: OSError / TimeoutError / SessionError<br/>(backoff 1 s -> 60 s, doubling)
    Opening --> AuthFailed: AuthenticationError
    Opening --> Connected: negotiation Success<br/>is_connected = True
    Connected --> Connected: frame received<br/>(reset _last_rx, reset backoff)
    Connected --> Idle: no frame for read_poll (30 s)
    Idle --> Connected: frame received
    Idle --> Probing: idle >= 300 s<br/>queue a status request
    Probing --> Connected: any frame arrives on the monitor
    Probing --> Closed: no frame within 30 s<br/>SessionError -> reconnect
    Connected --> Closed: transport error<br/>is_connected = False
    AuthFailed --> [*]: loops stopped,<br/>reauth flow started
    Connected --> [*]: close_listener()
```

### `own_session.py`: why `OWNd` is wrapped

`OWNd`'s own session methods never raise. `connect()` returns `None` after five
refused attempts (three for `test_connection()`) or
`{"Success": False, "Message": ...}` after a negotiation failure; `send()` and
`get_next()` swallow every exception and return `None`. The handler could not tell
"the gateway is rebooting" from "a frame arrived".

`OWNChannel` subclasses `OWNSession`, so the negotiation and password code is
still `OWNd`'s (the package is pinned and untouched), but:

- **`open(timeout)`** makes **one** connection attempt inside `asyncio.timeout`,
  enables TCP keepalive on the socket (idle 30 s, interval 10 s, 3 probes, applied
  only where the platform provides the option), runs `OWNd`'s `_negotiate()`, and
  then **verifies the result**. A `Message` of `password_error`,
  `password_required` or `password_retry` becomes `AuthenticationError`; any other
  failure becomes `SessionError`; connect failures propagate as `OSError` /
  `TimeoutError`. The socket is always closed on failure. Retry and backoff belong
  to the caller.
- **`read_frame()` / `get_next()`** raise `SessionError` on EOF
  (`IncompleteReadError`) and on over-long frames, and let `OSError` through. A
  frame `OWNd`'s parser cannot handle — including the frames on which
  `OWNMessage.parse` itself raises, such as a short WHO 13 frame or a CEN+ frame
  without `#n` — comes back as its raw text, never as an exception. Cancelling the
  read (which the listening loop does on every poll timeout) is safe: the stream
  buffer is preserved.
- **`close()`** never raises, and is safe before `open()` and when called twice.

### `send_command()`: reading replies until ACK

```mermaid
sequenceDiagram
    participant E as Entity / service
    participant Q as send_buffer (queue, max 200)
    participant W as sending_loop(worker)
    participant C as OWNCommandChannel
    participant G as Gateway

    E->>Q: send(msg) / send_status_request(msg)
    Note over Q: QueueFull -> False + rate-limited WARNING
    W->>Q: get() with a 60 s timeout
    Note over W: timeout -> close the idle command session
    W->>W: drop if age > 60 s TTL
    W->>C: open(10 s) if no session yet
    W->>C: send_command(msg, 10 s)
    C->>G: *1*1*11##
    G-->>C: *1*1*11## (status reply)
    G-->>C: *#18*51*51*99## (another reply)
    G-->>C: *#*1## (ACK)
    C-->>W: CommandResult(acknowledged=True, replies=[...])
    W->>W: dispatch every reply like a monitor event
```

`send_command` writes the frame, then reads frames until it sees an `OWNSignaling`
ACK or NACK. Every non-signaling `OWNMessage` in between is collected into
`CommandResult.replies`; unparsable text is logged and discarded. This is what
makes multi-frame status and energy replies reach the entities instead of
desynchronising the session — the reason the energy totalisers were dead before
0.2.0. On timeout or transport error the channel is marked not open, because an
unknown number of late frames may still be in flight: the caller must discard it.

## The command queue

| Property | Value | Behaviour |
|---|---|---|
| Bounded | `maxsize=200` | `put_nowait` raises `QueueFull`; `send()` returns `False` and logs a rate-limited WARNING. `myhome.send_message` turns that `False` into a visible `HomeAssistantError`. |
| TTL | `60 s` | Checked when the item is dequeued, not while it waits. An expired command is dropped with a WARNING, never sent. |
| Timeout | `10 s` | Per `send_command` call: write + drain + read until ACK/NACK. |
| Retry | **once**, in place | On a transport error the session is closed and one fresh session is opened for a second attempt. |
| Drop | after the second failure | A rate-limited WARNING names the command. It is **never re-queued**: ordering stays intact and a stale command is never replayed minutes later. |
| Auth failure | immediate stop | `AuthenticationError` on a command session stops both loops and starts the reauth flow. |
| Backoff | `1 s → 60 s` | Applied inside the sending loop after a failed delivery, reset on the first success. |

Queued items carry an `is_status_request` flag (set by `send_status_request`); it
is currently recorded but not read anywhere — both kinds are logged identically.

`close_listener()` drains whatever is left and logs the discarded commands (up to
the first ten by name).

## Availability

`is_connected` is `True` only while the **event** session is verified alive. Every
transition is published on the dispatcher signal

```python
SIGNAL_GATEWAY_CONNECTION = "myhome_gateway_connection_{mac}"
```

`MyHOMEEntity.available` returns `gateway.is_connected`, and every entity
subscribes to that signal in `async_internal_added_to_hass` — a framework hook, so
the subscription happens even if a platform overrides `async_added_to_hass`
without calling `super()`. `_async_on_connection_change` writes the new state;
sensors override it to also re-issue their bus request on reconnection (which is
how the instant-power keep-alive is re-armed after a gateway reboot).

Platforms must not override `available`, `device_info`, `should_poll` or
`has_entity_name`. No entity is polled: `should_poll` is `False` in the base class,
and anything periodic drives its own timer through the Home Assistant time helpers
and cancels it through `async_on_remove`.

## Statistics and diagnostics (0.3.0)

The handler keeps a `GatewayStats` snapshot (`connected`, `last_frame_at`,
`frames_rx`, `reconnects`, `commands_sent`, `commands_dropped`, `queue_length`,
`session_state`) in `handler.stats` and publishes it on
`SIGNAL_GATEWAY_STATS` (throttled to once per second, and immediately on
connect, disconnect, authentication failure and every dropped command). The
gateway diagnostic entities subscribe to that signal; `diagnostics.py` reads the
same snapshot, the `session_parameters` in effect and the `recent_frames` ring
buffer (last 50 monitor frames, command replies and commands) when you download
diagnostics from the integration page. Identical status requests already waiting
in the queue are coalesced by `send_status_request()`.

## The dispatcher

`_dispatch_message(message, from_monitor=...)` routes one parsed frame and **never
raises**. Its order is:

1. Fire `myhome_message_event` — only when the option is on **and** the frame came
   from the monitor session. Building the event content is itself wrapped, because
   `OWNd`'s `event_content` can choke on odd frames.
2. Feed the discovery service (wrapped).
3. `OWNEnergyEvent` → the instant-power throttle, then the entities.
4. Lighting / automation / dry contact / aux / heating events → skip command
   translations, handle general/area/group scope by firing the matching bus event
   and re-requesting the affected states, handle dimmer preset levels by asking the
   light for its real brightness, otherwise deliver to the entities.
5. A heating **command** with dimension 14 seen on the bus → request that zone's
   status.
6. `OWNCENPlusEvent` / `OWNCENEvent` → fire `myhome_cenplus_event` /
   `myhome_cen_event`.
7. Gateway events/commands → DEBUG.
8. Anything else → DEBUG.

Two isolation rules make a bug in one entity harmless to the session:

- **`.get()` lookups everywhere.** `_gw_cfg()`, `_platform_cfg()` and
  `_entities_for()` walk `hass.data` with `.get()` and type checks, so a frame that
  arrives while the entry is being torn down finds an empty dict instead of raising
  `KeyError`.
- **Per-entity `try`/`except`.** `_dispatch_to_entities` calls each
  `handle_event()` inside its own `try`, logging a rate-limited ERROR keyed on the
  entity's unique id. One broken entity cannot tear down the session for the other
  fifty.

`_entities_for()` deliberately skips the `button` platform: the Lock/Unlock buttons
share the device key of the actuator they belong to, and they have no state to
update.

### Two corrections applied to `OWNd`'s entity key

`OWNd` is pinned and never modified; both fixes live in
`gateway._message_entity_key()` / `_entity_key_candidates()` and never touch its
private attributes.

- **Central heating unit (0.3.1).** `OWNHeatingEvent.__init__` rewrites a `zone 0`
  frame to the zone found in the first WHERE parameter, so `*#4*0#1*20*1##` — the
  central unit's actuator 1 — reports entity `4-1` and used to drive **zone 1's**
  climate entity with the central unit's state. A frame whose `where` is `"0"` is
  routed to the central-unit key `4-#0` instead.
- **Bus interface padding (0.3.1).** Device keys pad the interface (`1-11#4#03`),
  the bus does not (`1-11#4#3`). Lookups try the key as received and both
  int-normalised spellings, so either side may be written either way.

## The instant-power throttle

Only **instant active power** (`MESSAGE_TYPE_ACTIVE_POWER`) is throttled. Every
other WHO 18 frame — totaliser, daily, monthly — is dispatched unfiltered. Getting
this wrong is what used to keep the energy sensors at `unknown`: the totaliser
replies report 0 W and were suppressed as "no change".

The rule is an **OR**:

```python
accept = (
    last_w is None                              # first sample always passes
    or last_ts is None
    or abs(watts - last_w) >= settings.min_delta_w
    or now - last_ts >= settings.min_interval_sec
)
```

Either threshold at `0` accepts everything. Settings are resolved per entity, most
specific first — the sensor's own keys (which `validate.py` has already merged with
the gateway defaults), then the gateway `sensor_defaults`, then the code defaults —
and cached once the configuration is actually present.

Suppressed frames are counted and summarised at DEBUG at most once per
`suppress_log_interval_sec`. `info_log_interval_sec > 0` additionally writes an
INFO heartbeat for accepted samples; it is `0` (off) by default so ordinary
operation stays quiet.

## The validator contract

`config_schema(yaml_dict)` returns `{mac: {"platforms": {...}, ...}}` and
guarantees that the platform modules can index certain keys **directly**, without
`.get()` and without `KeyError`.

Guaranteed on every device, on every platform:

| Key | Guarantee |
|---|---|
| `name` | Present. Required in YAML except for climate, where it defaults to `Central unit` or `Zone N`. |
| `who` | Present. Defaults per platform: light/switch `1`, cover `2`, climate `4`, binary_sensor `25`, sensor derived from the class. |
| `entities` | Present, an empty dict, pre-seeded with the sub-entity slots for power/energy meters. |
| `entity_name`, `icon`, `icon_on`, `model` | Present, possibly `None`. |
| `manufacturer` | Present, defaults to `BTicino S.p.A.`. |

Platform specific guarantees:

| Platform | Also guaranteed |
|---|---|
| `light` | `where`, `dimmable` (default `false`), `lock_buttons` (default `false`). |
| `switch` | `where`, `class` (default `switch`), `lock_buttons`. |
| `cover` | `where`, `class` (default `shutter`), `advanced` (`false`), `shutter_run` (`20.0`, minimum 1), `inverted` (`false`), `lock_buttons`. |
| `binary_sensor` | `where`, `inverted`, `class` — **which may legitimately be `None`** (the default for WHO 9). |
| `sensor` | `where`, `class` (**required**, one of power/energy/temperature/illuminance), the merged filter keys, and the `entities` slots. |
| `climate` | `zone` (default `#0`), `heat`, `cool`, `fan`, `standalone`, `central`. |

### Rekeying and duplicate detection

Devices are re-keyed from your free-choice YAML key to `"{who}-{where}"`
(`"{who}-{where}#4#{interface}"`, `"{who}-{zone}"` for climate). While rekeying,
the validator records every key it has already seen **across all platforms**. A
collision raises `Invalid` naming both YAML keys — this used to be a silent
overwrite. The single tolerated overlap is a `climate` zone plus a WHO 4
`temperature` sensor on the same zone: both legitimately address zone N, and they
live in different platform dicts.

### Button generation

After rekeying, the validator walks `light`, `switch` and `cover` and, for every
device with `lock_buttons: true` **and** a Point-to-Point WHERE, adds a shallow
copy into a synthetic `button` platform with its own empty `entities` dict and a
`source_platform` key. Non-point-to-point WHEREs are skipped, because `*14*0*0##`
would disable every actuator on the plant.

### Unknown keys

Unknown keys are **kept** in the configuration (for backward compatibility) and
reported once per key path at WARNING, with a `difflib` "did you mean" hint. Root
keys, in contrast, are strict: only strings are accepted as gateway roots.

## Test strategy

163 tests, run with `pytest tests` (`pytest.ini` sets `asyncio_mode = auto`, which
the Home Assistant test plugin requires).

| File | Covers |
|---|---|
| `test_validate.py` | The schema: WHERE forms, aliases, duplicates, defaults, unknown-key warnings — and that `probatio` and `voluptuous` agree, since Home Assistant Core 2026.9 swapped the engine. |
| `test_gateway.py` | The handler against fake channels *and* against a real loopback OpenWebNet server: queue bounds, TTL, retry-once, drop, idle watchdog, auth failure, dispatcher isolation, the energy throttle, idempotent shutdown. |
| `test_init.py` | Setup and unload, entry migration, `ConfigEntryNotReady` / `ConfigEntryAuthFailed` paths, registry pruning that preserves user-disabled entities, service validation, two-gateway resolution — and the end-to-end test. |
| `test_config_flow.py` | Picker, manual entry, SSDP, port, password, reauth, options. |
| `test_light.py`, `test_switch.py`, `test_cover.py`, `test_climate.py`, `test_sensor.py`, `test_binary_sensor.py`, `test_button.py` | Per-platform behaviour. |

### The fake OpenWebNet server

`tests/test_gateway.py` contains `FakeOWNServer`, a minimal gateway on a loopback
port: it sends the greeting, records which session type was negotiated
(`*99*0##` / `*99*1##`), can demand a nonce and accept or reject the password,
answers scripted replies per received frame, can push arbitrary frames on every
open monitor session, and can drop all monitor sessions to simulate a dead link.
`pytest-socket` blocks sockets by default, so these tests opt in with
`@pytest.mark.usefixtures("socket_enabled")` — loopback only.

### What the end-to-end test covers

`test_end_to_end_with_fake_gateway` runs a **real** config entry setup against
that server with **no `OWNd` mock at all**, using the author's own redacted
configuration from `tests/fixtures/myhome.yaml`. It asserts, in order:

1. the entry reaches `LOADED` and the entities exist with their expected unique
   ids (`…-1-11` light, `…-2-81` cover, `…-18-51-total-energy` meter);
2. the event session is negotiated as `*99*1##`, `is_connected` becomes `True` and
   the entities leave `unavailable`;
3. status requests sent on the command session are answered and applied (the light
   goes to `off`), and an **energy totaliser reply read on the command session**
   reaches its entity (`12345`) — the regression that used to make those sensors
   dead;
4. the instant-power keep-alive was armed, verbatim: `*#18*51*#1200#1*125##`;
5. monitor frames drive the entities — light on, cover `opening`, then a stop that
   leaves an integer `current_position`;
6. dropping the monitor session makes every entity `unavailable`, the handler
   reconnects **exactly once** after the 1 s initial backoff, states come back, and
   only one monitor session is ever live;
7. unloading the entry closes the monitor session on the gateway side.

Point 6 is the one that matters most: it is a direct, automated check that the
"reload the integration every morning" workaround is no longer necessary.

### Lint

```bash
ruff check custom_components tests --select F,E9,B,UP,ASYNC
```
