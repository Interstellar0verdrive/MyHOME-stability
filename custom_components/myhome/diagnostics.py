"""Diagnostics support for MyHOME (0.3.0, G1-A).

Home Assistant discovers this platform automatically; **Settings -> Devices &
services -> MyHOME -> ... -> Download diagnostics** produces a JSON file that can be
attached to a bug report.

What goes in:

- the config entry data/options with the password removed and the identifying
  fields (MAC, entry id, host, UDN, SSDP location) partially masked, and the
  ``config_file_path`` reduced to its file name -- enough to correlate frames, not
  enough to identify the installation or its operating-system user;
- the effective tunables (options merged with the 0.2.x defaults);
- a *summary* of the validated ``myhome.yaml``: per platform the device count and
  the device keys (``who-where``), never the user's device names.  The per-device
  download adds that device's own validated config, with ``name`` /
  ``entity_name`` redacted for the same reason;
- the gateway handler statistics (Contract: ``handler.stats``, a ``GatewayStats``
  dataclass) and its session parameters;
- the last frames of the ring buffer (``handler.recent_frames``).  OpenWebNet frames
  carry no personal data, but session-negotiation frames are replaced by a marker so
  a password hash can never leak into a public issue.

Everything is read defensively (``getattr`` with a fallback): diagnostics must never
be the reason a bug report cannot be produced.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_ID,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    __version__ as HA_VERSION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.loader import async_get_integration
from OWNd import __version__ as OWND_VERSION

from .const import (
    CONF_COMMAND_TIMEOUT_SEC,
    CONF_DEFAULT_KEEPALIVE_MINUTES,
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
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
    DEFAULT_CONFIG_FILE,
    DEFAULT_IDLE_WATCHDOG_SEC,
    DEFAULT_KEEPALIVE_MINUTES,
    DEFAULT_PROBE_WINDOW_SEC,
    DEFAULT_QUEUE_TTL_SEC,
    DOMAIN,
    LOGGER,
    clamp_worker_count,
)

# Never shown, in any form.
TO_REDACT: set[str] = {CONF_PASSWORD, CONF_OWN_PASSWORD}
# Shown truncated: they identify the installation but are needed to read the frames.
PARTIALLY_REDACTED: set[str] = {CONF_MAC, CONF_ID, CONF_UDN, CONF_HOST, CONF_SSDP_LOCATION}
# Free-form names the user wrote: never shown (see _device_summary).
_NAME_KEYS: set[str] = {CONF_NAME, CONF_ENTITY_NAME}

REDACTED = "**REDACTED**"
REDACTED_FRAME = "**REDACTED (session negotiation)**"
MAX_FRAMES = 50

# Session/authentication frames: ``*99*<session>##`` (+ its ``*#99*`` variants) and the
# nonce / password-hash exchange ``*#<digits>##``.  ACK/NACK (``*#*1##`` / ``*#*0##``)
# do not match: the character after ``*#`` is a ``*``, not a digit.
_NEGOTIATION_RE = re.compile(r"^\*#?99\*")
_AUTH_HASH_RE = re.compile(r"^\*#\d+##$")
# The HMAC (SHA-1/SHA-256) variant OWNd sends instead of the legacy nonce is
# ``*#<Rb>*<hmac>##`` (OWNd/connection.py), i.e. two numbers separated by a ``*``.
# Both halves are a hex digest written two decimal digits per hex character, so they
# are 80 (SHA-1) or 128 (SHA-256) digits long; requiring at least 16 digits is what
# keeps an ordinary dimension request such as ``*#1*11##`` out of this pattern.
_AUTH_HMAC_RE = re.compile(r"^\*#\d{16,}\*\d{16,}##$")
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


def _redact_path(value: Any) -> Any:
    """Keep the file name of a path, drop the directories it lives in.

    ``config_file_path`` is free-form: on a HAOS install it is ``/config/myhome.yaml``
    and harmless, but on a container or core install it is often ``/home/<user>/...``
    or ``/Users/<user>/...``, i.e. the operating-system user name -- more identifying
    than the MAC octets that *are* masked next to it.  The file name is what every
    diagnostic use of the value actually needs.
    """
    if not isinstance(value, str) or not value:
        return value
    return os.path.basename(value) or REDACTED


def _redact_identity(data: Mapping[str, Any]) -> dict[str, Any]:
    """Remove the password and partially mask the identifying fields."""
    redacted = async_redact_data(dict(data), TO_REDACT)
    for key in PARTIALLY_REDACTED:
        if key not in redacted or redacted[key] is None:
            continue
        redacted[key] = _redact_host(redacted[key]) if key == CONF_HOST else _redact_tail(redacted[key])
    if redacted.get(CONF_FILE_PATH):
        redacted[CONF_FILE_PATH] = _redact_path(redacted[CONF_FILE_PATH])
    return redacted


def redact_frame(frame: str) -> str:
    """Replace a session-negotiation frame with a marker, pass anything else through."""
    if _NEGOTIATION_RE.match(frame) or _AUTH_HASH_RE.match(frame) or _AUTH_HMAC_RE.match(frame):
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
def effective_options(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """The tunables actually in effect (options merged with the 0.2.x hard-coded values).

    ``config_file_path`` is reported as its file name plus "is this the default
    location?": that answers every question a bug report asks of it (which file, and
    whether the user moved it) without publishing the directory it sits in, which on a
    non-HAOS install carries the operating-system user name.

    The option is only written once the user has opened the options dialog, so the
    effective path is resolved exactly the way ``__init__.async_setup_entry`` resolves
    it -- unset means the default location, not "no configuration file".  Reporting
    the raw option instead used to answer ``null`` / ``false`` for the majority case,
    which reads as "this user moved their file somewhere we cannot see".

    ``command_worker_count`` is resolved the same way and for the same reason: it is
    the number of command sessions really opened, not the stored option.
    """
    options = entry.options
    default_path = hass.config.path(DEFAULT_CONFIG_FILE)
    configured_path = str(options.get(CONF_FILE_PATH) or "") or default_path
    return {
        "config_file_name": _redact_path(configured_path) or None,
        "config_file_is_default_location": configured_path == default_path,
        # The value in force, not the stored one: the setup clamps it to
        # MAX_COMMAND_WORKERS, and ``handler.sending_workers`` is a few lines below in
        # the same file -- an entry saved under the old 1-10 form used to report
        # ``command_worker_count: 8`` next to a handler running 4.
        CONF_WORKER_COUNT: clamp_worker_count(options.get(CONF_WORKER_COUNT, 1)),
        CONF_GENERATE_EVENTS: bool(options.get(CONF_GENERATE_EVENTS, False)),
        CONF_IDLE_WATCHDOG_SEC: options.get(CONF_IDLE_WATCHDOG_SEC, DEFAULT_IDLE_WATCHDOG_SEC),
        CONF_PROBE_WINDOW_SEC: options.get(CONF_PROBE_WINDOW_SEC, DEFAULT_PROBE_WINDOW_SEC),
        CONF_COMMAND_TIMEOUT_SEC: options.get(CONF_COMMAND_TIMEOUT_SEC, DEFAULT_COMMAND_TIMEOUT_SEC),
        CONF_QUEUE_TTL_SEC: options.get(CONF_QUEUE_TTL_SEC, DEFAULT_QUEUE_TTL_SEC),
        CONF_DEFAULT_KEEPALIVE_MINUTES: options.get(CONF_DEFAULT_KEEPALIVE_MINUTES, DEFAULT_KEEPALIVE_MINUTES),
    }


def _device_summary(device: Mapping[str, Any]) -> dict[str, Any]:
    """A single device's validated config, without the live entity objects or names.

    ``name`` / ``entity_name`` are free-form strings the user wrote, and they are
    usually room or family names -- exactly what nobody expects to publish by
    attaching a diagnostics file to a public issue.  The module docstring and
    ``docs/troubleshooting.md`` both promise they are never included, so redact them
    here too and not only in the entry-level ``config`` summary.
    """
    return {
        key: (REDACTED if key in _NAME_KEYS and value else _jsonable(value))
        for key, value in device.items()
        if key != CONF_ENTITIES
    }


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
        "effective_options": effective_options(hass, entry),
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
