# Gateway compatibility

This page records what is **known** to work per gateway model, what is only
**expected** from the OpenWebNet protocol and the `OWNd` library, and what nobody
has reported yet.

The integration has one author with one gateway. Everything marked "verified"
below was observed on real hardware; everything else is an honest "we think so".
If you run a gateway that is not verified here, the
[reporting section](#how-to-report-your-gateway) tells you what to send.

## Legend

| Mark | Meaning |
|---|---|
| **verified** | Observed working (or observed *not* working) on real hardware. |
| *expected* | Follows from the OpenWebNet protocol and the code paths in `OWNd` / this integration, but nobody has confirmed it on this model. |
| **please report** | Unknown. No data at all. |

The only hardware behind the "verified" marks is a **MyHOMEServer1** with
**F520/F521** energy meters, SCS lighting actuators (ON/OFF, no dimmers), basic
WHO 2 shutter actuators and CEN+ scenario controls.

## Connection, discovery and control

| Gateway | Connection / auth | SSDP discovery | Lights (ON/OFF) | Dimmers | Covers (basic) | Covers (advanced position) | Climate |
|---|---|---|---|---|---|---|---|
| MyHOMEServer1 | **verified** | **please report** (see note 1) | **verified** | **please report** | **verified** | **please report** | **please report** |
| F454 | *expected* | *expected* (matcher present) | *expected* | *expected* | *expected* | *expected* | *expected* |
| F455 | *expected* | *expected* (matcher present) | *expected* | *expected* | *expected* | *expected* | *expected* |
| F453AV | *expected* | *expected* (matcher present) | *expected* | *expected* | *expected* | *expected* | *expected* |
| MH200N | *expected* | *expected* (matcher present) | *expected* | *expected* | *expected* | *expected* | *expected* |
| MH202 | *expected* | *expected* (matcher present) | *expected* | *expected* | *expected* | *expected* | *expected* |
| MH201 | *expected* | *expected* (matcher present) | *expected* | *expected* | *expected* | *expected* | *expected* |
| Other (F452, MH200, HL4684, AM4890, …) | *expected* | *expected* (matcher present) | *expected* | *expected* | *expected* | *expected* | *expected* |

## Energy, events and sessions

| Gateway | Instant power (`*#18*<where>*#1200#1*<minutes>##`) | Energy totals (`*#18*<where>*51/53/54##`) | CEN+ events | CEN events | Concurrent session limit |
|---|---|---|---|---|---|
| MyHOMEServer1 | **verified** (F520/F521) | **verified not to work**: the requests are ACKed with no data frame, so the daily/monthly/total sensors stay `unknown` | **verified** | **please report** | **please report** (see note 3) |
| F454 | *expected* | **please report** | *expected* | *expected* | **please report** |
| F455 | *expected* | **please report** | *expected* | *expected* | **please report** |
| F453AV | *expected* | **please report** | *expected* | *expected* | **please report** |
| MH200N | *expected* | **please report** | *expected* | *expected* | **please report** |
| MH202 | *expected* | **please report** | *expected* | *expected* | **please report** |
| MH201 | *expected* | **please report** | *expected* | *expected* | **please report** |
| Other | *expected* | **please report** | *expected* | *expected* | **please report** |

### Note 1 — the two discovery paths

There are two independent discovery mechanisms, and they can disagree.

1. **Home Assistant's SSDP component** produces the "discovered integration" card.
   It matches on the entries in `custom_components/myhome/manifest.json`: ST
   `upnp:rootdevice`, manufacturer `BTicino S.p.A.`, and one of these exact
   `modelName` values — `HL4684`, `AM4890`, `MyHomeServer1`, `F455`, `F454`,
   `F453AV`, `F452`, `MH200N`, `MH200`, `MH202`, `MH201`. Home Assistant compares
   the *value* exactly (only header keys are case-insensitive), so a device
   announcing `MyHOMEServer1` (capital HO) would **not** match the
   `MyHomeServer1` entry. This has not been confirmed either way on real
   hardware — hence "please report" for MyHOMEServer1. `F453` without the `AV`
   suffix has no matcher at all.
2. **The gateway picker inside the config flow** (`Add integration → MyHOME`)
   does its own SSDP `M-SEARCH` through `OWNd.discovery.find_gateways()`, which
   selects on the `USN` prefix instead: `uuid:pnp-webserver-`,
   `uuid:pnp-scheduler-`, `uuid:pnp-scheduler201-`, `uuid:pnp-touchscreen-`,
   `uuid:pnp-myhomeserver1-`, `uuid:upnp-Basic gateway-`,
   `uuid:upnp-IPscenariomodule-`, `uuid:upnp-IPscenarioModule-`.

If your gateway never shows up in either, use **Custom** in the picker and enter
address, port, MAC and model by hand. The OpenWebNet port is normally 20000; when
a gateway is discovered, the port is read over UPnP/SOAP
(`urn:schemas-bticino-it:service:openserver:1#getopenserverPort`) and falls back
to 20000.

### Note 2 — authentication

Authentication is entirely `OWNd`'s (`OWNd/connection.py`, `_negotiate()`), and it
covers three cases automatically. The integration does not choose a method; it
reacts to what the gateway offers.

| Gateway answer to `*99*<0\|1>##` | What happens |
|---|---|
| `ACK` | No password. Session open. |
| A **nonce** frame | Legacy "OPEN" algorithm. The password is treated as an integer (`int(password)`), so **this path requires a numeric password**. A non-numeric password raises `ValueError`, which the config flow turns into the `password_numeric` error on the password form. |
| A **SHA challenge** (`*98*1##` / `*98*2##`) | HMAC handshake, SHA-1 or SHA-256 depending on the challenge. Any password string works. The gateway's own HMAC response is verified too, so a wrong password fails on either side. |

Password failures surface as the OWNd messages `password_required`,
`password_error` and `password_retry`; at runtime the integration turns any of
them into a Home Assistant **reauth** flow instead of retrying forever.
`password_retry` means the gateway reset the negotiation — wait ~60 s before
retrying.

### Note 3 — session limits

The integration opens **one event (monitor) session** per gateway, plus **one
command session per command worker** (default 1, configurable 1–10 in the
integration options). A command session that has had nothing to send for 60 s is
closed and reopened on demand, specifically so an idle integration does not hold a
slot on gateways with a small concurrent-session budget.

No exact limit is documented for any model here. If you see `IncompleteReadError`
or immediate disconnects after a reload, that is the symptom to report.

## Watchdog, keep-alive and queue parameters

Since 0.3.0 the first four are configurable from the integration's **Configure** dialog (see [Configuration reference](configuration.md)); the defaults below are the values used when nothing is set. They live in `custom_components/myhome/gateway.py` and
`custom_components/myhome/own_session.py`. They are not exposed in the UI or in
`myhome.yaml`. Tests override them on the handler instance; nothing else does.

| Parameter | Value | Where | What it does |
|---|---|---|---|
| `IDLE_TIMEOUT_SEC` | `300.0` s | `gateway.py` | No frame on the monitor session for this long → send a probe status request. |
| `PROBE_WINDOW_SEC` | `30.0` s | `gateway.py` | Probe sent and still nothing on the monitor → treat the session as dead and reconnect. |
| `READ_POLL_SEC` | `30.0` s | `gateway.py` | Wake-up cadence of the listening loop; the granularity of the idle watchdog. |
| `INITIAL_BACKOFF_SEC` | `1.0` s | `gateway.py` | First reconnect delay. |
| `MAX_BACKOFF_SEC` | `60.0` s | `gateway.py` | Backoff ceiling; it doubles on each consecutive failure and resets once the session proves alive. |
| `CONNECT_TIMEOUT_SEC` | `10.0` s | `gateway.py` | TCP connect + negotiation, one attempt. |
| `COMMAND_TIMEOUT_SEC` | `10.0` s | `gateway.py` | Write a command and wait for the gateway's ACK/NACK. |
| `COMMAND_QUEUE_MAXSIZE` | `200` | `gateway.py` | Bounded command queue. When full, new commands are refused (the service call raises; entity commands log a rate-limited warning). |
| `COMMAND_TTL_SEC` | `60.0` s | `gateway.py` | A command dequeued more than this long after being queued is dropped, not sent. |
| `COMMAND_SESSION_IDLE_SEC` | `60.0` s | `gateway.py` | Idle command session is closed and given back to the gateway. |
| `LOG_RATE_LIMIT_SEC` | `60.0` s | `gateway.py` | Default rate limit for repeated warnings (queue full, dropped command, NACK…). |
| `RECONNECT_LOG_RATE_LIMIT_SEC` | `300.0` s | `gateway.py` | Rate limit for the "event session lost, reconnecting" warning. |
| TCP keepalive idle / interval / count | `30` s / `10` s / `3` | `own_session.py` | Applied to both session sockets where the platform supports it (`TCP_KEEPIDLE` on Linux, `TCP_KEEPALIVE` on macOS). A dead peer is detected in about 60 s instead of the kernel default of ~2 hours. |

The probe used by the idle watchdog is picked from your own configuration, in this
order: a point-to-point light, switch or cover status request; otherwise a WHO 18
total-consumption request; otherwise a climate zone temperature request; otherwise
the general lighting status `*#1*0##`.

## How to report your gateway

Open an issue at
<https://github.com/Interstellar0verdrive/MyHOME-stability/issues> with the
information below.

### 1. Turn on debug logging

Add this to `configuration.yaml` and restart (or use **Developer tools → Actions →
`logger.set_level`** for a temporary change):

```yaml
logger:
  default: warning
  logs:
    custom_components.myhome: debug
    OWNd: debug
```

### 2. Collect

- Gateway **model** and **firmware** as shown on the device page in Home
  Assistant (Settings → Devices & services → MyHOME → the gateway device).
- Whether the gateway appeared as a **discovered integration card**, in the
  **picker list**, or only through **Custom**.
- The log lines from startup through the first minute of traffic. The interesting
  ones look like:
  - `Event session established` / `Gateway is connected`
  - `Negotiating event session.` and `Received SHA challenge` or `Received nonce`
  - `Queued \`*#18*51*51##\`` followed by `` `*#18*51*51##` acknowledged (N reply frame(s)) ``
  - `Event: \`*1*1*11##\`` (monitor traffic)
- For energy: the reply-frame count for the totaliser requests
  (`*#18*<where>*51##`, `*53##`, `*54##`). **`acknowledged (0 reply frame(s))` is
  the signature of a gateway that ACKs the request but returns no data** — that is
  the MyHOMEServer1 + F520/F521 case.
- The relevant part of your `myhome.yaml`.

### 3. Redact before pasting

- **The gateway password.** It never appears in the logs, but it is often written
  in a comment in `myhome.yaml`.
- **The MAC address**, if you would rather not publish it. It appears in
  `myhome.yaml`, in entity unique ids and in device identifiers. Replace it
  consistently, e.g. `00:03:50:AA:BB:CC`.
- Local IP addresses if your setup makes them sensitive.

Nonces and HMAC hashes in the OWNd debug log are single-use challenge values, not
your password, but redacting them costs nothing.
