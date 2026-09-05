"""Validator for the MyHome configuration file (``myhome.yaml``).

Contract A (see ``.audit-2026-09/CONTRACTS.md``): ``config_schema(yaml_dict)`` returns

    {mac: {CONF_PLATFORMS: {platform: {device_key: device_cfg}}, <gateway-level keys>}}

for one or more gateways.  Accepted roots are a ``gateway:`` block and/or MAC-address
root keys (legacy and multi-gateway styles).  Device keys are ``"{who}-{where}"`` or
``"{who}-{where}#4#{interface}"`` (climate: ``"{who}-{zone}"``).

Every device config is post-processed so that the platform modules can index the keys
listed in Contract A directly (``name``, ``entity_name``, ``icon``, ``icon_on``,
``manufacturer``, ``model``, ``entities`` and the platform specific ones).

Engine note: Home Assistant Core 2026.9 replaced voluptuous with probatio.  Probatio's
compatibility layer compiles nested ``Schema`` instances directly and never invokes the
``__call__`` of a *subclass* nested inside another schema, so the device schemas are
wrapped in plain lambdas in ``gateway_schema``.  The top-level ``MyHomeConfigSchema``
instance is always called directly by ``__init__.py`` so its ``__call__`` runs on both
engines.  Nothing else in this module is engine sensitive (verified with both engines
by ``tests/test_validate.py``).
"""
from __future__ import annotations

import difflib
import re
from collections.abc import Iterable, Mapping, MutableMapping, Sequence

from voluptuous import (
    ALLOW_EXTRA,
    PREVENT_EXTRA,
    Schema,
    Optional,
    Required,
    Coerce,
    Boolean,
    Any,
    All,
    In,
    Invalid,
    Range,
)
from homeassistant.helpers.device_registry import format_mac as ha_format_mac
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.switch import (
    SwitchDeviceClass,
    DOMAIN as SWITCH,
)
from homeassistant.components.button import DOMAIN as BUTTON
from homeassistant.components.cover import (
    CoverDeviceClass,
    DOMAIN as COVER,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    DOMAIN as BINARY_SENSOR,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    DOMAIN as SENSOR,
)
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.const import CONF_NAME, CONF_MAC

from .const import (
    LOGGER,
    CONF_PLATFORMS,
    CONF_WHO,
    CONF_WHERE,
    CONF_BUS_INTERFACE,
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_ICON,
    CONF_ICON_ON,
    CONF_ZONE,
    CONF_FAN_SUPPORT,
    CONF_MANUFACTURER,
    CONF_DEVICE_MODEL,
    CONF_DEVICE_CLASS,
    CONF_DIMMABLE,
    CONF_ADVANCED_SHUTTER,
    CONF_INVERTED,
    CONF_HEATING_SUPPORT,
    CONF_COOLING_SUPPORT,
    CONF_STANDALONE,
    CONF_CENTRAL,
    CONF_GATEWAY as CONF_GATEWAY_BLOCK,
    # Contract A keys (added to const.py by F2; platform modules import them from there).
    CONF_LOCK_BUTTONS,
    CONF_SHUTTER_RUN,
    CONF_SOURCE_PLATFORM,
    CONF_MIN_DELTA_W,
    CONF_MIN_INTERVAL_SEC,
    CONF_SUPPRESS_LOG_INTERVAL_SEC,
    CONF_INFO_LOG_INTERVAL_SEC,
    CONF_KEEPALIVE_MINUTES,
    CONF_SENSOR_DEFAULTS,
    DEFAULT_KEEPALIVE_MINUTES,
    DEFAULT_MANUFACTURER,
    DEFAULT_SHUTTER_RUN,
)

# --------------------------------------------------------------------------------------
# YAML keys that only the validator needs to know about (not in const.py).
# --------------------------------------------------------------------------------------
CONF_ENERGY_DEFAULTS = "energy"  # legacy alias of sensor_defaults
DEVICE_CLASS_ALIAS = "device_class"  # YAML alias of CONF_DEVICE_CLASS ("class")

# Built-in defaults for the power/energy reporting filter and keep-alive.  Gateway level
# ``sensor_defaults`` (alias ``energy``) override these, per-sensor keys override both.
SENSOR_FILTER_DEFAULTS: dict[str, int | float] = {
    CONF_MIN_DELTA_W: 5,
    CONF_MIN_INTERVAL_SEC: 1.0,
    CONF_SUPPRESS_LOG_INTERVAL_SEC: 60.0,
    CONF_KEEPALIVE_MINUTES: DEFAULT_KEEPALIVE_MINUTES,
}

# Legacy / alias spellings of the filter keys (first match wins when the canonical key
# is absent).  ``refresh_period`` is the upstream (artmakh) name for min_interval_sec.
_FILTER_ALIASES: dict[str, tuple[str, ...]] = {
    CONF_MIN_DELTA_W: ("energy_min_delta_w",),
    CONF_MIN_INTERVAL_SEC: ("energy_min_interval_sec", "refresh_period", "refresh_period_sec"),
    CONF_SUPPRESS_LOG_INTERVAL_SEC: ("energy_suppress_log_interval_sec",),
    CONF_INFO_LOG_INTERVAL_SEC: ("energy_info_log_interval_sec",),
    CONF_KEEPALIVE_MINUTES: (),
}

DEVICE_PLATFORMS: tuple[str, ...] = (LIGHT, SWITCH, COVER, BINARY_SENSOR, SENSOR, CLIMATE)
LOCK_BUTTON_PLATFORMS: tuple[str, ...] = (LIGHT, SWITCH, COVER)


# --------------------------------------------------------------------------------------
# Unknown-key warnings (val-07)
# --------------------------------------------------------------------------------------
_WARNED_UNKNOWN_KEYS: set[tuple[str, ...]] = set()


def warn_unknown_keys(path: Sequence[object], data: Mapping, known_keys: Iterable[object]) -> None:
    """Log (once per key path, WARNING) every key of ``data`` that is not in ``known_keys``.

    Unknown keys are kept in the configuration for backward compatibility; this only
    tells the user that the key is ignored and suggests the closest known key.  Never
    raises.
    """
    known = sorted({str(k) for k in known_keys})
    known_set = set(known)
    for key in data:
        key_text = str(key)
        if key_text in known_set:
            continue
        marker = (*(str(p) for p in path), key_text)
        if marker in _WARNED_UNKNOWN_KEYS:
            continue
        _WARNED_UNKNOWN_KEYS.add(marker)
        hint = difflib.get_close_matches(key_text, known, n=1, cutoff=0.6)
        LOGGER.warning(
            "myhome.yaml: unknown key '%s' in %s is ignored%s",
            key_text,
            ".".join(str(p) for p in path) or "<root>",
            f" (did you mean '{hint[0]}'?)" if hint else "",
        )


def reset_unknown_key_warnings() -> None:
    """Forget which unknown keys were already reported (used by tests)."""
    _WARNED_UNKNOWN_KEYS.clear()


def _key_name(key: object) -> str | None:
    """Return the literal key name behind a schema key or Marker (``Optional``/``Required``)."""
    literal = getattr(key, "schema", key)
    return literal if isinstance(literal, str) else None


def _known_keys(fields: Mapping) -> set[str]:
    return {name for name in (_key_name(k) for k in fields) if name is not None}


# --------------------------------------------------------------------------------------
# MAC address
# --------------------------------------------------------------------------------------
def format_mac(address: object) -> str | None:
    """Normalise a MAC address to Home Assistant's ``aa:bb:cc:dd:ee:ff`` form, or ``None``."""
    if not isinstance(address, str):
        return None
    mac = "".join(re.sub("[.:-]", "", address).split()).upper()
    if len(mac) != 12 or re.fullmatch("[0-9A-F]{12}", mac) is None:
        return None
    return ha_format_mac(mac)


class MacAddress:
    """Validator: MAC address in any common notation, normalised via ``format_mac``."""

    def __init__(self, msg: str | None = None) -> None:
        self.msg = msg

    def __call__(self, v: object) -> str:
        if not isinstance(v, str):
            raise Invalid(self.msg or f"MAC address must be a string like '00:03:50:xx:xx:xx', got {v!r}")
        mac = format_mac(v)
        if mac is None:
            raise Invalid(self.msg or f"Invalid MAC address {v!r}, expected 12 hex digits like '00:03:50:xx:xx:xx'")
        return mac

    def __repr__(self) -> str:
        return f"MacAddress(msg={self.msg!r})"


# --------------------------------------------------------------------------------------
# WHERE validators
# --------------------------------------------------------------------------------------
def _where_text(v: object) -> str:
    """Turn the raw YAML value of a WHERE into a string.

    YAML parses unquoted ``where: 01`` as the integer 1 (leading zero lost) and
    ``where: 010`` as octal 8, so integers are accepted only when they cannot be
    ambiguous: 0 (General) and 2- or 4-digit numbers without a leading zero.
    """
    if isinstance(v, bool) or v is None:
        raise Invalid("WHERE is missing or not a string, quote it (e.g. where: '15')")
    if isinstance(v, int):
        if v == 0:
            return "0"
        if 10 <= v <= 99 or 1000 <= v <= 9999:
            return str(v)
        if 1 <= v <= 9:
            raise Invalid(
                f"WHERE {v} was read by YAML as a number and is ambiguous: quote it as "
                f"'0{v}' for A=0 PL={v} or as '{v}' for area {v}"
            )
        raise Invalid(
            f"WHERE {v} was read by YAML as a number (leading zeros are lost, '0…' is octal): quote it, e.g. where: '0115'"
        )
    if isinstance(v, str):
        text = v.strip()
        if text == "":
            raise Invalid("WHERE must not be empty")
        return text
    raise Invalid(f"WHERE must be a string, got {type(v).__name__}")


class General:
    """WHERE ``0`` (all devices of the WHO)."""

    def __init__(self, msg: str | None = None) -> None:
        self.msg = msg

    def __call__(self, v: object) -> str:
        if isinstance(v, str) and v == "0":
            return v
        raise Invalid(self.msg or f"Invalid General WHERE {v!r}, it must be '0'.")

    def __repr__(self) -> str:
        return f"General(msg={self.msg!r})"


class Area:
    """WHERE of a whole area: ``00``, ``1``..``9``, ``10``.

    Note: ``00`` is also a valid Point-to-Point address (A=0 PL=0); the ``Any`` order in
    the device schemas makes it an Area, which is what the OpenWebNet spec says.
    """

    _VALUES = ("00", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10")

    def __init__(self, msg: str | None = None) -> None:
        self.msg = msg

    def __call__(self, v: object) -> str:
        if isinstance(v, str) and v in self._VALUES:
            return v
        raise Invalid(self.msg or f"Invalid Area WHERE {v!r}, it must be a string in [00, 1-9, 10].")

    def __repr__(self) -> str:
        return f"Area(msg={self.msg!r})"


class Group:
    """WHERE of a group: ``#1``..``#255`` (normalised: ``#01`` -> ``#1``)."""

    def __init__(self, msg: str | None = None) -> None:
        self.msg = msg

    def __call__(self, v: object) -> str:
        if isinstance(v, str) and v.startswith("#") and v[1:].isdigit() and 1 <= int(v[1:]) <= 255:
            return f"#{int(v[1:])}"
        raise Invalid(self.msg or f"Invalid Group WHERE {v!r}, it must be a string like '#[1-255]'.")

    def __repr__(self) -> str:
        return f"Group(msg={self.msg!r})"


class PointToPoint:
    """WHERE of a single device: ``A`` + ``PL`` as 2 digits (A 0-9, PL 0-9) or 4 digits (A 00-10, PL 00-15)."""

    def __init__(self, msg: str | None = None) -> None:
        self.msg = msg

    def __call__(self, v: object) -> str:
        if not (isinstance(v, str) and v.isdigit()):
            raise Invalid(self.msg or f"Invalid WHERE {v!r}, it must be a string of 2 or 4 digits.")
        length = len(v)
        if length not in (2, 4):
            raise Invalid(self.msg or f"Invalid WHERE {v!r} length, it must be a string of 2 or 4 digits.")
        a, pl = v[: length // 2], v[length // 2 :]
        if 0 <= int(a) <= 10 and 0 <= int(pl) <= 15:
            return f"{a}{pl}"
        raise Invalid(self.msg or f"Invalid WHERE {v!r}, A must be [0-10] and PL must be [0-15].")

    def __repr__(self) -> str:
        return f"PointToPoint(msg={self.msg!r})"


class SpecialWhere:
    """WHERE of sensors (energy meters, thermo probes, dry contacts): any string of digits."""

    def __init__(self, msg: str | None = None) -> None:
        self.msg = msg

    def __call__(self, v: object) -> str:
        if isinstance(v, str) and v.isdigit():
            return v
        raise Invalid(self.msg or f"Invalid WHERE {v!r}, it must be a string of digits.")

    def __repr__(self) -> str:
        return f"SpecialWhere(msg={self.msg!r})"


class BusInterface:
    """Local bus interface number ``00``..``15`` (int 0-15 accepted and zero padded)."""

    def __init__(self, msg: str | None = None) -> None:
        self.msg = msg

    def __call__(self, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 15:
            return f"{v:02d}"
        if isinstance(v, str) and v.isdigit() and len(v) == 2:
            if int(v) > 15:
                raise Invalid(self.msg or f"Invalid Bus Interface number {v}, it must be between 00 and 15.")
            return v
        raise Invalid(self.msg or f"Invalid Bus Interface number {v!r}, it must be a string of 2 digits (00-15).")

    def __repr__(self) -> str:
        return f"BusInterface(msg={self.msg!r})"


class Zone:
    """Thermoregulation zone: ``#0`` (central unit), ``1``..``99`` or ``#0#<zone>``."""

    def __init__(self, msg: str | None = None) -> None:
        self.msg = msg

    def __call__(self, v: object) -> str:
        if isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= 99:
            return str(v)
        if isinstance(v, str):
            text = v.strip()
            if text == "#0" or re.fullmatch(r"#0#[1-9][0-9]?", text):
                return text
            if text.isdigit() and 1 <= int(text) <= 99:
                return text
        raise Invalid(self.msg or f"Invalid zone {v!r}, expected '#0' (central unit), '1'-'99' or '#0#<zone>'.")

    def __repr__(self) -> str:
        return f"Zone(msg={self.msg!r})"


ACTUATOR_WHERE = All(
    _where_text,
    Any(
        General(),
        Area(),
        Group(),
        PointToPoint(),
        msg=(
            "Invalid <WHERE>, expecting a valid General ('0'), Area ('00', '1'-'9', '10'), "
            "Group ('#1'-'#255') or Point-to-Point (2 or 4 digits, A 0-10, PL 0-15) <WHERE>"
        ),
    ),
)
SENSOR_WHERE = All(_where_text, SpecialWhere())


def is_point_to_point(where: object) -> bool:
    """True for a Point-to-Point WHERE (2 or 4 digits) that is neither General, Area nor Group."""
    return (
        isinstance(where, str)
        and where.isdigit()
        and len(where) in (2, 4)
        and where not in Area._VALUES
    )


# --------------------------------------------------------------------------------------
# Field helpers
# --------------------------------------------------------------------------------------
def _who(*allowed: str):
    """WHO field: accepts the (string or unquoted int) values in ``allowed``."""
    return All(Coerce(str), In(list(allowed)))


def _device_class(enum, allowed: Sequence):
    """Device class field: validated against ``allowed`` and normalised to the enum member."""
    return All(Coerce(str), In(list(allowed)), Coerce(enum))


_NON_NEGATIVE_INT = All(Coerce(int), Range(min=0))
_NON_NEGATIVE_FLOAT = All(Coerce(float), Range(min=0))
_KEEPALIVE_MINUTES = All(Coerce(int), Range(min=0, max=255))

_COMMON_FIELDS: dict = {
    Required(CONF_NAME): str,
    Optional(CONF_ENTITY_NAME): str,
    Optional(CONF_ICON): str,
    Optional(CONF_MANUFACTURER, default=DEFAULT_MANUFACTURER): str,
    Optional(CONF_DEVICE_MODEL): Coerce(str),
}

# Power/energy reporting filter + keep-alive keys, valid both at gateway level
# (``sensor_defaults`` / ``energy``) and per sensor.
_SENSOR_FILTER_FIELDS: dict = {
    Optional(CONF_MIN_DELTA_W): _NON_NEGATIVE_INT,
    Optional(CONF_MIN_INTERVAL_SEC): _NON_NEGATIVE_FLOAT,
    Optional(CONF_SUPPRESS_LOG_INTERVAL_SEC): _NON_NEGATIVE_FLOAT,
    Optional(CONF_INFO_LOG_INTERVAL_SEC): _NON_NEGATIVE_FLOAT,
    Optional(CONF_KEEPALIVE_MINUTES): _KEEPALIVE_MINUTES,
    # Aliases (legacy energy_* names and the upstream refresh_period)
    Optional("energy_min_delta_w"): _NON_NEGATIVE_INT,
    Optional("energy_min_interval_sec"): _NON_NEGATIVE_FLOAT,
    Optional("energy_suppress_log_interval_sec"): _NON_NEGATIVE_FLOAT,
    Optional("energy_info_log_interval_sec"): _NON_NEGATIVE_FLOAT,
    Optional("refresh_period"): _NON_NEGATIVE_FLOAT,
    Optional("refresh_period_sec"): _NON_NEGATIVE_FLOAT,
}

_SWITCH_CLASSES = [SwitchDeviceClass.OUTLET, SwitchDeviceClass.SWITCH]
_COVER_CLASSES = list(CoverDeviceClass)
_BINARY_SENSOR_CLASSES = list(BinarySensorDeviceClass)
_SENSOR_CLASSES = [
    SensorDeviceClass.TEMPERATURE,
    SensorDeviceClass.POWER,
    SensorDeviceClass.ENERGY,
    SensorDeviceClass.ILLUMINANCE,
]

# Default binary_sensor class by WHO when neither ``class`` nor ``device_class`` is given.
_BINARY_SENSOR_DEFAULT_CLASS: dict[str, BinarySensorDeviceClass | None] = {
    "25": BinarySensorDeviceClass.OPENING,
    "1": BinarySensorDeviceClass.MOTION,
    "9": None,
}

# Default WHO by sensor class (and the only WHO each class is valid for).
_SENSOR_WHO_BY_CLASS: dict[str, str] = {
    SensorDeviceClass.POWER: "18",
    SensorDeviceClass.ENERGY: "18",
    SensorDeviceClass.TEMPERATURE: "4",
    SensorDeviceClass.ILLUMINANCE: "1",
}

LIGHT_FIELDS: dict = {
    **_COMMON_FIELDS,
    Optional(CONF_WHO, default="1"): _who("1"),
    Required(CONF_WHERE): ACTUATOR_WHERE,
    Optional(CONF_BUS_INTERFACE): BusInterface(),
    Optional(CONF_ICON_ON): str,
    Optional(CONF_DIMMABLE, default=False): Boolean(),
    Optional(CONF_LOCK_BUTTONS, default=False): Boolean(),
    # Lights have no device class in HA; accepted (and normalised to ``class``) so that
    # the alias rule holds on every platform, but nothing reads it.
    Optional(CONF_DEVICE_CLASS): str,
    Optional(DEVICE_CLASS_ALIAS): str,
}

SWITCH_FIELDS: dict = {
    **_COMMON_FIELDS,
    Optional(CONF_WHO, default="1"): _who("1"),
    Required(CONF_WHERE): ACTUATOR_WHERE,
    Optional(CONF_BUS_INTERFACE): BusInterface(),
    Optional(CONF_ICON_ON): str,
    # No schema default: it would collide with the ``device_class`` alias before the
    # alias is folded.  The default (switch) is applied by _finalize_switch.
    Optional(CONF_DEVICE_CLASS): _device_class(SwitchDeviceClass, _SWITCH_CLASSES),
    Optional(DEVICE_CLASS_ALIAS): _device_class(SwitchDeviceClass, _SWITCH_CLASSES),
    Optional(CONF_LOCK_BUTTONS, default=False): Boolean(),
}

COVER_FIELDS: dict = {
    **_COMMON_FIELDS,
    Optional(CONF_WHO, default="2"): _who("2"),
    Required(CONF_WHERE): ACTUATOR_WHERE,
    Optional(CONF_BUS_INTERFACE): BusInterface(),
    Optional(CONF_ADVANCED_SHUTTER, default=False): Boolean(),
    Optional(CONF_SHUTTER_RUN, default=DEFAULT_SHUTTER_RUN): All(Coerce(float), Range(min=1)),
    Optional(CONF_INVERTED, default=False): Boolean(),
    # Default (shutter) applied by _finalize_cover, after the ``device_class`` alias is folded.
    Optional(CONF_DEVICE_CLASS): _device_class(CoverDeviceClass, _COVER_CLASSES),
    Optional(DEVICE_CLASS_ALIAS): _device_class(CoverDeviceClass, _COVER_CLASSES),
    Optional(CONF_LOCK_BUTTONS, default=False): Boolean(),
}

BINARY_SENSOR_FIELDS: dict = {
    **_COMMON_FIELDS,
    Optional(CONF_WHO, default="25"): _who("1", "9", "25"),
    Required(CONF_WHERE): SENSOR_WHERE,
    Optional(CONF_BUS_INTERFACE): BusInterface(),
    Optional(CONF_INVERTED, default=False): Boolean(),
    Optional(CONF_DEVICE_CLASS): _device_class(BinarySensorDeviceClass, _BINARY_SENSOR_CLASSES),
    Optional(DEVICE_CLASS_ALIAS): _device_class(BinarySensorDeviceClass, _BINARY_SENSOR_CLASSES),
}

SENSOR_FIELDS: dict = {
    **_COMMON_FIELDS,
    **_SENSOR_FILTER_FIELDS,
    Optional(CONF_WHO): _who("1", "4", "18"),
    Required(CONF_WHERE): SENSOR_WHERE,
    Optional(CONF_BUS_INTERFACE): BusInterface(),
    Optional(CONF_DEVICE_CLASS): _device_class(SensorDeviceClass, _SENSOR_CLASSES),
    Optional(DEVICE_CLASS_ALIAS): _device_class(SensorDeviceClass, _SENSOR_CLASSES),
}

CLIMATE_FIELDS: dict = {
    # ``name`` is optional for climate devices (defaults to "Zone N" / "Central unit"),
    # so the common Required(name) is replaced below.
    **{k: v for k, v in _COMMON_FIELDS.items() if _key_name(k) != CONF_NAME},
    Optional(CONF_NAME): str,
    Optional(CONF_WHO, default="4"): _who("4"),
    Optional(CONF_ZONE): Zone(),
    Optional(CONF_WHERE): Zone(),  # discovery writes ``where`` for thermo zones: alias of ``zone``
    Optional(CONF_HEATING_SUPPORT, default=True): Boolean(),
    Optional(CONF_COOLING_SUPPORT, default=False): Boolean(),
    Optional(CONF_FAN_SUPPORT, default=False): Boolean(),
    Optional(CONF_STANDALONE, default=False): Boolean(),
    Optional(CONF_CENTRAL, default=False): Boolean(),
}

ENERGY_DEFAULTS_FIELDS: dict = dict(_SENSOR_FILTER_FIELDS)

PLATFORM_FIELDS: dict[str, dict] = {
    LIGHT: LIGHT_FIELDS,
    SWITCH: SWITCH_FIELDS,
    COVER: COVER_FIELDS,
    BINARY_SENSOR: BINARY_SENSOR_FIELDS,
    SENSOR: SENSOR_FIELDS,
    CLIMATE: CLIMATE_FIELDS,
}


# --------------------------------------------------------------------------------------
# Per-device post-processing
# --------------------------------------------------------------------------------------
def _resolve_class_alias(device: MutableMapping, yaml_key: str) -> None:
    """Fold the ``device_class`` alias into ``class``; both with different values -> Invalid."""
    if DEVICE_CLASS_ALIAS not in device:
        return
    alias_value = device.pop(DEVICE_CLASS_ALIAS)
    if CONF_DEVICE_CLASS in device and device[CONF_DEVICE_CLASS] != alias_value:
        raise Invalid(
            f"device '{yaml_key}' has both class={device[CONF_DEVICE_CLASS]!r} and "
            f"device_class={alias_value!r}; use only one of them",
            path=[yaml_key, DEVICE_CLASS_ALIAS],
        )
    device[CONF_DEVICE_CLASS] = alias_value


def _inject_common_defaults(device: MutableMapping) -> None:
    """Guarantee the keys every platform indexes directly (Contract A)."""
    device[CONF_ENTITIES] = {}
    for key in (CONF_DEVICE_MODEL, CONF_ICON, CONF_ICON_ON, CONF_ENTITY_NAME):
        device.setdefault(key, None)


def _finalize_switch(device: MutableMapping, yaml_key: str) -> None:
    device.setdefault(CONF_DEVICE_CLASS, SwitchDeviceClass.SWITCH)


def _finalize_cover(device: MutableMapping, yaml_key: str) -> None:
    device.setdefault(CONF_DEVICE_CLASS, CoverDeviceClass.SHUTTER)


def _finalize_binary_sensor(device: MutableMapping, yaml_key: str) -> None:
    if CONF_DEVICE_CLASS not in device:
        device[CONF_DEVICE_CLASS] = _BINARY_SENSOR_DEFAULT_CLASS.get(device[CONF_WHO])


def _finalize_climate(device: MutableMapping, yaml_key: str) -> None:
    """Accept ``where`` as ``zone``, apply the central-unit form and default the name."""
    where = device.pop(CONF_WHERE, None)
    if where is not None:
        if CONF_ZONE in device and device[CONF_ZONE] != where:
            raise Invalid(
                f"climate '{yaml_key}' has both zone={device[CONF_ZONE]!r} and where={where!r}; use only 'zone'",
                path=[yaml_key, CONF_WHERE],
            )
        device[CONF_ZONE] = where
    device.setdefault(CONF_ZONE, "#0")
    if device[CONF_CENTRAL] and not device[CONF_ZONE].startswith("#0"):
        device[CONF_ZONE] = f"#0#{device[CONF_ZONE]}"
    if CONF_NAME not in device:
        device[CONF_NAME] = "Central unit" if device[CONF_ZONE].startswith("#0") else f"Zone {device[CONF_ZONE]}"


def _finalize_sensor(device: MutableMapping, yaml_key: str) -> None:
    """Require a class, derive/validate WHO from it and create the sub-entity slots."""
    if CONF_DEVICE_CLASS not in device:
        raise Invalid(
            f"sensor '{yaml_key}' is missing the required sensor class (use 'class' or 'device_class': "
            f"{', '.join(str(c) for c in _SENSOR_CLASSES)})",
            path=[yaml_key, CONF_DEVICE_CLASS],
        )
    sensor_class = device[CONF_DEVICE_CLASS]
    expected_who = _SENSOR_WHO_BY_CLASS[sensor_class]
    if CONF_WHO not in device:
        device[CONF_WHO] = expected_who
    elif device[CONF_WHO] != expected_who:
        raise Invalid(
            f"sensor '{yaml_key}': class {sensor_class} requires who {expected_who}, got who {device[CONF_WHO]}",
            path=[yaml_key, CONF_WHO],
        )
    if sensor_class in (SensorDeviceClass.POWER, SensorDeviceClass.ENERGY):
        device[CONF_ENTITIES][f"daily-{SensorDeviceClass.ENERGY}"] = {}
        device[CONF_ENTITIES][f"monthly-{SensorDeviceClass.ENERGY}"] = {}
        device[CONF_ENTITIES][f"total-{SensorDeviceClass.ENERGY}"] = {}
        if sensor_class == SensorDeviceClass.POWER:
            device[CONF_ENTITIES][f"{SensorDeviceClass.POWER}"] = {}
    # Fold legacy/alias spellings into the canonical filter keys (canonical key wins).
    for canonical, aliases in _FILTER_ALIASES.items():
        if canonical in device:
            continue
        for alias in aliases:
            if alias in device:
                device[canonical] = device[alias]
                break


_PLATFORM_FINALIZERS = {
    SWITCH: _finalize_switch,
    COVER: _finalize_cover,
    BINARY_SENSOR: _finalize_binary_sensor,
    CLIMATE: _finalize_climate,
    SENSOR: _finalize_sensor,
}


class MyHomeDeviceSchema(Schema):
    """Schema of one platform section: ``{yaml_key: {device fields}}``.

    Validates every device, warns about unknown keys, folds aliases and injects the
    defaults required by Contract A.  The result is still keyed by the YAML key; the
    rekeying to ``who-where`` (with duplicate detection) is done by ``MyHomeConfigSchema``
    because it needs the whole gateway.
    """

    def __init__(self, platform: str, fields: Mapping) -> None:
        self.platform = platform
        self.known_keys = _known_keys(fields)
        # Outer mapping: keys must be strings (PREVENT_EXTRA rejects e.g. an unquoted int
        # device key); inner mapping: unknown keys are kept and reported by
        # warn_unknown_keys (ALLOW_EXTRA) for backward compatibility.
        super().__init__({Optional(str): Schema(dict(fields), extra=ALLOW_EXTRA)}, extra=PREVENT_EXTRA)

    def __call__(self, data):
        data = super().__call__(data)
        finalize = _PLATFORM_FINALIZERS.get(self.platform)
        for yaml_key, device in data.items():
            warn_unknown_keys((self.platform, yaml_key), device, self.known_keys)
            _resolve_class_alias(device, yaml_key)
            _inject_common_defaults(device)
            if finalize is not None:
                finalize(device, yaml_key)
        return data


light_schema = MyHomeDeviceSchema(LIGHT, LIGHT_FIELDS)
switch_schema = MyHomeDeviceSchema(SWITCH, SWITCH_FIELDS)
cover_schema = MyHomeDeviceSchema(COVER, COVER_FIELDS)
binary_sensor_schema = MyHomeDeviceSchema(BINARY_SENSOR, BINARY_SENSOR_FIELDS)
sensor_schema = MyHomeDeviceSchema(SENSOR, SENSOR_FIELDS)
climate_schema = MyHomeDeviceSchema(CLIMATE, CLIMATE_FIELDS)

PLATFORM_SCHEMAS: dict[str, MyHomeDeviceSchema] = {
    LIGHT: light_schema,
    SWITCH: switch_schema,
    COVER: cover_schema,
    BINARY_SENSOR: binary_sensor_schema,
    SENSOR: sensor_schema,
    CLIMATE: climate_schema,
}

# Gateway-level defaults for the power/energy filter (``sensor_defaults``, alias ``energy``).
energy_defaults_schema = Schema(ENERGY_DEFAULTS_FIELDS, extra=ALLOW_EXTRA)
sensor_defaults_schema = energy_defaults_schema

def _section(schema):
    """Wrap a section schema in a plain callable that treats a ``null`` section as empty.

    The device schemas are Schema subclasses whose overridden __call__ performs
    post-processing.  Probatio's compatibility layer compiles nested Schema instances
    directly and never invokes the subclass __call__, so they must be reached through a
    plain callable (the lambda pattern); this forces __call__ to run on both engines.
    A section left empty in YAML (``light:`` with nothing under it) parses as ``None``
    and is accepted as an empty mapping.
    """
    return lambda v: schema({} if v is None else v)


gateway_schema = Schema(
    {
        Optional(CONF_MAC): MacAddress(),
        Optional(LIGHT): _section(light_schema),
        Optional(SWITCH): _section(switch_schema),
        Optional(COVER): _section(cover_schema),
        Optional(BINARY_SENSOR): _section(binary_sensor_schema),
        Optional(SENSOR): _section(sensor_schema),
        Optional(CLIMATE): _section(climate_schema),
        Optional(CONF_ENERGY_DEFAULTS): _section(energy_defaults_schema),
        Optional(CONF_SENSOR_DEFAULTS): _section(sensor_defaults_schema),
    },
    extra=ALLOW_EXTRA,  # unknown gateway-level keys are kept and reported, never fatal
)
_GATEWAY_KNOWN_KEYS = {CONF_MAC, *DEVICE_PLATFORMS, CONF_ENERGY_DEFAULTS, CONF_SENSOR_DEFAULTS}


# --------------------------------------------------------------------------------------
# Gateway-level post-processing
# --------------------------------------------------------------------------------------
def device_key(device: Mapping) -> str:
    """Key of a validated device inside ``hass.data[DOMAIN][mac][CONF_PLATFORMS][platform]``.

    ``"{who}-{where}"``, ``"{who}-{where}#4#{interface}"`` for devices behind a bus
    interface, ``"{who}-{zone}"`` for climate (the central form ``#0#N`` keys as ``N``).
    """
    who = device[CONF_WHO]
    if CONF_ZONE in device and CONF_WHERE not in device:
        zone = device[CONF_ZONE]
        return f"{who}-{zone[3:] if zone.startswith('#0#') else zone}"
    where = device[CONF_WHERE]
    interface = device.get(CONF_BUS_INTERFACE)
    return f"{who}-{where}#4#{interface}" if interface else f"{who}-{where}"


def _resolve_filter_block(block: Mapping) -> dict:
    """Canonical filter keys of a gateway-level ``sensor_defaults``/``energy`` block."""
    resolved: dict = {}
    for canonical, aliases in _FILTER_ALIASES.items():
        for key in (canonical, *aliases):
            if key in block:
                resolved[canonical] = block[key]
                break
    return resolved


def _merge_sensor_defaults(gateway: Mapping, root_key: str) -> dict:
    """Built-in defaults <- ``energy`` <- ``sensor_defaults`` (per key)."""
    merged = dict(SENSOR_FILTER_DEFAULTS)
    for block_key in (CONF_ENERGY_DEFAULTS, CONF_SENSOR_DEFAULTS):
        block = gateway.get(block_key)
        if isinstance(block, Mapping):
            warn_unknown_keys((root_key, block_key), block, _known_keys(ENERGY_DEFAULTS_FIELDS))
            merged.update(_resolve_filter_block(block))
    return merged


def _apply_sensor_defaults(device: MutableMapping, defaults: Mapping) -> None:
    """Per-sensor keys win, then the merged gateway defaults, then the built-in ones."""
    for key, value in defaults.items():
        device.setdefault(key, value)


def _resolve_gateway_mac(root_key: str, gateway: Mapping) -> str:
    """MAC of a root entry: from its ``mac`` key and/or from the root key itself."""
    inner_mac = gateway.get(CONF_MAC)
    root_mac = None if root_key == CONF_GATEWAY_BLOCK else format_mac(root_key)
    if inner_mac and root_mac and inner_mac != root_mac:
        raise Invalid(
            f"root key '{root_key}' is a MAC address but its 'mac' entry says {inner_mac!r}; they must match",
            path=[root_key, CONF_MAC],
        )
    mac = inner_mac or root_mac
    if not mac:
        raise Invalid(
            f"gateway '{root_key}' needs a 'mac: 00:03:50:xx:xx:xx' entry (or use the MAC address as the root key)",
            path=[root_key, CONF_MAC],
        )
    return mac


class MyHomeConfigSchema(Schema):
    """Top-level ``myhome.yaml`` schema producing the Contract A structure keyed by MAC."""

    def __call__(self, data):
        data = super().__call__(data)
        result: dict = {}
        origin_of_mac: dict[str, str] = {}

        for root_key, gateway in data.items():
            mac = _resolve_gateway_mac(root_key, gateway)
            if mac in origin_of_mac:
                raise Invalid(
                    f"gateway MAC {mac} is configured twice: root entries '{origin_of_mac[mac]}' and '{root_key}'",
                    path=[root_key, CONF_MAC],
                )
            origin_of_mac[mac] = root_key
            warn_unknown_keys((root_key,), gateway, _GATEWAY_KNOWN_KEYS)

            platforms: dict[str, dict] = {}
            entry: dict = {CONF_PLATFORMS: platforms}
            sensor_defaults = _merge_sensor_defaults(gateway, root_key)
            # Merged canonical defaults, published once under ``sensor_defaults``
            # (``energy`` is folded into it; gateway.py falls back to sensor_defaults).
            entry[CONF_SENSOR_DEFAULTS] = sensor_defaults

            # Rekey every device to who-where and refuse duplicates across ALL platforms
            # (val-01): a duplicate silently replaced the first device before.  The one
            # tolerated cross-platform pair is a climate zone plus a WHO 4 temperature
            # sensor on the same zone (both legitimately address zone N; they live in
            # different platform dicts so nothing collides at run time).
            origins_of_key: dict[str, list[tuple[str, str]]] = {}
            for platform in DEVICE_PLATFORMS:
                section = gateway.get(platform)
                if section is None:
                    continue
                rekeyed: dict = {}
                for yaml_key, device in section.items():
                    key = device_key(device)
                    for other_platform, other_key in origins_of_key.get(key, ()):
                        if {other_platform, platform} == {CLIMATE, SENSOR}:
                            continue
                        address = device.get(CONF_WHERE, device.get(CONF_ZONE))
                        raise Invalid(
                            f"Duplicate WHERE '{address}' (who {device[CONF_WHO]}): {platform} '{yaml_key}' "
                            f"collides with {other_platform} '{other_key}' (both map to device '{key}'). "
                            f"Each WHO/WHERE (+interface) may appear only once per gateway; "
                            f"fix the WHERE or remove one of the two devices.",
                            path=[root_key, platform, yaml_key, CONF_WHERE if CONF_WHERE in device else CONF_ZONE],
                        )
                    origins_of_key.setdefault(key, []).append((platform, yaml_key))
                    if platform == SENSOR:
                        _apply_sensor_defaults(device, sensor_defaults)
                    rekeyed[key] = device
                platforms[platform] = rekeyed

            # Lock/Unlock buttons (val-10 / plat-08 / plat-09): only on request
            # (``lock_buttons: true``) and only for Point-to-Point WHEREs, because
            # ``*14*0*0##`` on a General/Area WHERE disables every actuator of the plant.
            buttons: dict = {}
            for platform in LOCK_BUTTON_PLATFORMS:
                for key, device in platforms.get(platform, {}).items():
                    if device.get(CONF_LOCK_BUTTONS) and is_point_to_point(device[CONF_WHERE]):
                        button = dict(device)  # shallow copy: the button must not share ``entities``
                        button[CONF_ENTITIES] = {}
                        button[CONF_SOURCE_PLATFORM] = platform
                        buttons[key] = button
            if buttons:
                platforms[BUTTON] = buttons

            # Keep the remaining (non-platform) gateway-level keys for backward
            # compatibility; __init__.py merges them into hass.data[DOMAIN][mac].
            for key, value in gateway.items():
                if key in (CONF_MAC, CONF_ENERGY_DEFAULTS, CONF_SENSOR_DEFAULTS) or key in DEVICE_PLATFORMS:
                    continue
                entry[key] = value

            result[mac] = entry

        return result


config_schema = MyHomeConfigSchema(
    {
        Optional(CONF_GATEWAY_BLOCK): gateway_schema,
        # Legacy / multi-gateway style: the MAC address (or any name, with an inner
        # ``mac``) as root key.
        Optional(str): gateway_schema,
    },
    extra=PREVENT_EXTRA,  # root keys are gateways only; non-string keys are rejected
)
