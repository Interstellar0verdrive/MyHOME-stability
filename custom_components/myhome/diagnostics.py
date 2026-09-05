"""Diagnostics support for MyHOME (0.3.0, G1-A).

Home Assistant discovers this platform automatically; **Settings -> Devices &
services -> MyHOME -> ... -> Download diagnostics** produces a JSON file that can be
attached to a bug report.

What goes in:

- the config entry data/options with the password removed and the identifying
  fields (MAC, entry id, host, UDN, SSDP location) partially masked -- enough to
  correlate frames, not enough to identify the installation;
- the effective tunables (options merged with the 0.2.x defaults);
- a *summary* of the validated ``myhome.yaml``: per platform the device count and
  the device keys (``who-where``), never the user's device names;
- the gateway handler statistics (Contract: ``handler.stats``, a ``GatewayStats``
  dataclass) and its session parameters;
- the last frames of the ring buffer (``handler.recent_frames``).  OpenWebNet frames
  carry no personal data, but session-negotiation frames are replaced by a marker so
  a password hash can never leak into a public issue.

Everything is read defensively (``getattr`` with a fallback): diagnostics must never
be the reason a bug report cannot be produced.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

from OWNd import __version__ as OWND_VERSION

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_ID,
    CONF_MAC,
    CONF_PASSWORD,
    __version__ as HA_VERSION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.loader import async_get_integration

from .const import (
    CONF_COMMAND_TIMEOUT_SEC,
    CONF_DEFAULT_KEEPALIVE_MINUTES,
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_FILE_PATH,
    CONF_GENERATE_EVENTS,
    CONF_IDLE_WATCHDOG_SEC,
    CONF_OWN_PASSWORD,
    CONF_PLATFORMS,
    CONF_PROBE_WINDOW_SEC,
    CONF_QUEUE_TTL_SEC,
    CONF_SSDP_LOCATION,
    CONF_UDN,
    CONF_WORKER_COUNT,
    DEFAULT_COMMAND_TIMEOUT_SEC,
    DEFAULT_IDLE_WATCHDOG_SEC,
    DEFAULT_KEEPALIVE_MINUTES,
    DEFAULT_PROBE_WINDOW_SEC,
    DEFAULT_QUEUE_TTL_SEC,
    DOMAIN,
    LOGGER,
)

# Never shown, in any form.
TO_REDACT: set[str] = {CONF_PASSWORD, CONF_OWN_PASSWORD}
# Shown truncated: they identify the installation but are needed to read the frames.
PARTIALLY_REDACTED: set[str] = {CONF_MAC, CONF_ID, CONF_UDN, CONF_HOST, CONF_SSDP_LOCATION}

REDACTED = "**REDACTED**"
REDACTED_FRAME = "**REDACTED (session negotiation)**"
MAX_FRAMES = 50

# Session/authentication frames: ``*99*<session>##`` (+ its ``*#99*`` variants) and the
# nonce / password-hash exchange ``*#<digits>##``.  ACK/NACK (``*#*1##`` / ``*#*0##``)
# do not match: the character after ``*#`` is a ``*``, not a digit.
_NEGOTIATION_RE = re.compile(r"^\*#?99\*")
_AUTH_HASH_RE = re.compile(r"^\*#\d+##$")
_IPV4_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}$")

# Handler attributes that describe the live session behaviour (Contract B knobs).
_SESSION_PARAMETERS = (
    "command_timeout",
    "connect_timeout",
    "command_ttl",
    "command_session_idle",
    "idle_timeout",
    "probe_window",
    "read_poll_interval",
    "initial_backoff",
    "max_backoff",
)


# --------------------------------------------------------------------------- redaction
def _redact_tail(value: Any, keep: int = 8) -> Any:
    """Keep the first ``keep`` characters of a string, mask the rest."""
    if not isinstance(value, str) or not value:
        return value
    if len(value) <= keep:
        return REDACTED
    return f"{value[:keep]}{REDACTED}"


def _redact_host(value: Any) -> Any:
    """Mask the host part of an IPv4 address, truncate anything else."""
    if not isinstance(value, str) or not value:
        return value
    if (match := _IPV4_RE.match(value)) is not None:
        # Keep the network class (useful when reading routing problems), drop the rest.
        return f"{match.group(1)}.{match.group(2)}.x.x"
    return _redact_tail(value)


def _redact_identity(data: Mapping[str, Any]) -> dict[str, Any]:
    """Remove the password and partially mask the identifying fields."""
    redacted = async_redact_data(dict(data), TO_REDACT)
    for key in PARTIALLY_REDACTED:
        if key not in redacted or redacted[key] is None:
            continue
        redacted[key] = _redact_host(redacted[key]) if key == CONF_HOST else _redact_tail(redacted[key])
    return redacted


def redact_frame(frame: str) -> str:
    """Replace a session-negotiation frame with a marker, pass anything else through."""
    if _NEGOTIATION_RE.match(frame) or _AUTH_HASH_RE.match(frame):
        return REDACTED_FRAME
    return frame


def _jsonable(value: Any) -> Any:
    """Convert a ring-buffer item to JSON-friendly data, redacting session frames."""
    if isinstance(value, str):
        # str() also flattens the StrEnum device classes stored in the device config.
        return redact_frame(str(value))
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    return repr(value)


# --------------------------------------------------------------------------- sections
def effective_options(entry: ConfigEntry) -> dict[str, Any]:
    """The tunables actually in effect (options merged with the 0.2.x hard-coded values)."""
    options = entry.options
    return {
        CONF_FILE_PATH: options.get(CONF_FILE_PATH) or None,
        CONF_WORKER_COUNT: options.get(CONF_WORKER_COUNT, 1),
        CONF_GENERATE_EVENTS: bool(options.get(CONF_GENERATE_EVENTS, False)),
        CONF_IDLE_WATCHDOG_SEC: options.get(CONF_IDLE_WATCHDOG_SEC, DEFAULT_IDLE_WATCHDOG_SEC),
        CONF_PROBE_WINDOW_SEC: options.get(CONF_PROBE_WINDOW_SEC, DEFAULT_PROBE_WINDOW_SEC),
        CONF_COMMAND_TIMEOUT_SEC: options.get(CONF_COMMAND_TIMEOUT_SEC, DEFAULT_COMMAND_TIMEOUT_SEC),
        CONF_QUEUE_TTL_SEC: options.get(CONF_QUEUE_TTL_SEC, DEFAULT_QUEUE_TTL_SEC),
        CONF_DEFAULT_KEEPALIVE_MINUTES: options.get(CONF_DEFAULT_KEEPALIVE_MINUTES, DEFAULT_KEEPALIVE_MINUTES),
    }


def _device_summary(device: Mapping[str, Any]) -> dict[str, Any]:
    """A single device's validated config without the live entity objects."""
    return {key: _jsonable(value) for key, value in device.items() if key != CONF_ENTITIES}


def config_summary(gateway_data: Mapping[str, Any]) -> dict[str, Any]:
    """Per-platform device count and device keys - never the user's device names."""
    platforms: Mapping[str, Mapping[str, Any]] = gateway_data.get(CONF_PLATFORMS, {})
    return {
        "gateway_keys": sorted(str(key) for key in gateway_data if key not in (CONF_PLATFORMS, CONF_ENTITY)),
        "device_count": sum(len(devices) for devices in platforms.values()),
        "platforms": {
            platform: {"count": len(devices), "device_keys": sorted(devices)}
            for platform, devices in sorted(platforms.items())
        },
    }


def handler_summary(handler: Any) -> dict[str, Any]:
    """Live handler state: Contract stats plus the session parameters in effect."""
    if handler is None:
        return {"loaded": False}
    stats = getattr(handler, "stats", None)
    if is_dataclass(stats) and not isinstance(stats, type):
        stats_data: Any = _jsonable(asdict(stats))
    elif isinstance(stats, Mapping):
        stats_data = _jsonable(stats)
    else:
        # A1 adds handler.stats in the same wave; until then report what is there.
        stats_data = None

    # Contract: the handler publishes the knobs in effect; fall back to the attributes.
    parameters = getattr(handler, "session_parameters", None)
    if not isinstance(parameters, Mapping):
        parameters = {name: getattr(handler, name, None) for name in _SESSION_PARAMETERS}

    buffer = getattr(handler, "send_buffer", None)
    return {
        "loaded": True,
        "is_connected": bool(getattr(handler, "is_connected", False)),
        "auth_failed": bool(getattr(handler, "auth_failed", False)),
        "generate_events": bool(getattr(handler, "generate_events", False)),
        "queue_size": buffer.qsize() if buffer is not None else None,
        "listening_worker": getattr(handler, "listening_worker", None) is not None,
        "sending_workers": len(getattr(handler, "sending_workers", []) or []),
        "stats": stats_data,
        "session_parameters": _jsonable(parameters),
    }


def recent_frames(handler: Any, limit: int = MAX_FRAMES) -> list[Any]:
    """The last ``limit`` frames of the handler ring buffer, session frames redacted."""
    frames = getattr(handler, "recent_frames", None)
    if not frames:
        return []
    try:
        tail = list(frames)[-limit:]
    except TypeError:  # pragma: no cover - a non-iterable ring buffer would be a bug
        LOGGER.debug("recent_frames is not iterable (%s)", type(frames).__name__)
        return []
    return [_jsonable(frame) for frame in tail]


# --------------------------------------------------------------------------- platform
async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Diagnostics for a MyHOME config entry."""
    mac: str = entry.data[CONF_MAC]
    gateway_data: Mapping[str, Any] = hass.data.get(DOMAIN, {}).get(mac, {})
    handler = gateway_data.get(CONF_ENTITY)

    try:
        integration_version = str((await async_get_integration(hass, DOMAIN)).version)
    except Exception:  # noqa: BLE001 - diagnostics must never fail on a version lookup
        integration_version = "unknown"
    return {
        "versions": {
            "myhome": integration_version,
            "ownd": OWND_VERSION,
            "home_assistant": HA_VERSION,
        },
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "minor_version": entry.minor_version,
            "source": entry.source,
            "state": str(entry.state),
            "unique_id": _redact_tail(entry.unique_id),
            "data": _redact_identity(entry.data),
            "options": _redact_identity(entry.options),
        },
        "effective_options": effective_options(entry),
        "config": config_summary(gateway_data),
        "handler": handler_summary(handler),
        "recent_frames": recent_frames(handler),
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Diagnostics for one device: the entry diagnostics plus that device's config."""
    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    mac: str = entry.data[CONF_MAC]
    gateway_data: Mapping[str, Any] = hass.data.get(DOMAIN, {}).get(mac, {})
    platforms: Mapping[str, Mapping[str, Any]] = gateway_data.get(CONF_PLATFORMS, {})
    identifiers = {identifier for domain, identifier in device.identifiers if domain == DOMAIN}

    device_info: dict[str, Any] = {
        "is_gateway": mac in identifiers,
        "device_keys": sorted(
            identifier.removeprefix(f"{mac}-") for identifier in identifiers if identifier != mac
        ),
        "disabled_by": str(device.disabled_by) if device.disabled_by else None,
        "config": {},
    }
    for platform, devices in platforms.items():
        for device_key in device_info["device_keys"]:
            if device_key in devices:
                device_info["config"][f"{platform}.{device_key}"] = _device_summary(devices[device_key])

    diagnostics["device"] = device_info
    return diagnostics
