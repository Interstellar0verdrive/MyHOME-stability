"""Constants for the MyHome component."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from OWNd.message import OWNMessage

LOGGER = logging.getLogger(__package__)
DOMAIN = "myhome"

# hass.data keys.
#   hass.data[DOMAIN][<mac>] keeps the per-gateway layout consumed by the platforms
#   (CONF_PLATFORMS -> platform -> device key -> device config, CONF_ENTITY -> handler).
#   Nothing else may live under hass.data[DOMAIN] (see core-03 / cf-05).

# Dispatcher signal fired by the gateway handler on every is_connected transition.
# Consumers subscribe with SIGNAL_GATEWAY_CONNECTION.format(mac=<mac>).
SIGNAL_GATEWAY_CONNECTION = "myhome_gateway_connection_{mac}"

# Default file names (relative to the HA configuration directory).
DEFAULT_CONFIG_FILE = "myhome.yaml"
DISCOVERED_CONFIG_FILE = "myhome_discovered.yaml"

# Config entry version (bumped when entry.data needs a migration).
CONFIG_ENTRY_VERSION = 2
CONFIG_ENTRY_MINOR_VERSION = 1

# Service names
SERVICE_SYNC_TIME = "sync_time"
SERVICE_SEND_MESSAGE = "send_message"
SERVICE_START_DISCOVERY = "start_discovery"
SERVICE_STOP_DISCOVERY = "stop_discovery"
SERVICE_START_SENDING_INSTANT_POWER = "start_sending_instant_power"

# Request timeout constants
GATEWAY_TEST_TIMEOUT_SEC = 20

# Event attributes
ATTR_GATEWAY = "gateway"
ATTR_MESSAGE = "message"
ATTR_DURATION = "duration"

# Configuration constants
CONF_ENTITY = "entity"
CONF_ENTITIES = "entities"
CONF_ENTITY_NAME = "entity_name"
CONF_ICON = "icon"
CONF_ICON_ON = "icon_on"
CONF_PLATFORMS = "platforms"
CONF_ADDRESS = "address"
CONF_OWN_PASSWORD = "password"
CONF_FIRMWARE = "firmware"
CONF_SSDP_LOCATION = "ssdp_location"
CONF_SSDP_ST = "ssdp_st"
CONF_DEVICE_TYPE = "deviceType"
CONF_DEVICE_MODEL = "model"
CONF_MANUFACTURER = "manufacturer"
CONF_MANUFACTURER_URL = "manufacturerURL"
CONF_UDN = "UDN"
CONF_WORKER_COUNT = "command_worker_count"
# Upper bound for the option: gateways hold only a handful of concurrent sessions.
MAX_COMMAND_WORKERS = 4
CONF_FILE_PATH = "config_file_path"
CONF_GENERATE_EVENTS = "generate_events"
CONF_WHO = "who"
CONF_WHERE = "where"
CONF_BUS_INTERFACE = "interface"
CONF_ZONE = "zone"
CONF_DIMMABLE = "dimmable"
CONF_GATEWAY = "gateway"
CONF_DEVICE_CLASS = "class"
CONF_INVERTED = "inverted"
CONF_ADVANCED_SHUTTER = "advanced"
CONF_SHUTTER_RUN = "shutter_run"
# Two-phase travel model (0.4.0): the first/last seconds of the run only open/close
# the slats ("lamelle"), the rest lifts the curtain.  ``opening_time``/``closing_time``
# allow an asymmetric run; both default to ``shutter_run``.
CONF_SLAT_TIME = "slat_time"
CONF_OPENING_TIME = "opening_time"
CONF_CLOSING_TIME = "closing_time"
CONF_LOCK_BUTTONS = "lock_buttons"
CONF_SOURCE_PLATFORM = "source_platform"
CONF_HEATING_SUPPORT = "heat"
CONF_COOLING_SUPPORT = "cool"
CONF_FAN_SUPPORT = "fan"
CONF_STANDALONE = "standalone"
CONF_CENTRAL = "central"
CONF_SHORT_PRESS = "pushbutton_short_press"
CONF_SHORT_RELEASE = "pushbutton_short_release"
CONF_LONG_PRESS = "pushbutton_long_press"
CONF_LONG_RELEASE = "pushbutton_long_release"
# CEN+ event values added by gw-14 (the four names above are unchanged).
EVENT_LONG_PRESS_REPEAT = "pushbutton_long_press_repeat"
EVENT_ROTATE_CW_SLOW = "rotate_cw_slow"
EVENT_ROTATE_CW_FAST = "rotate_cw_fast"
EVENT_ROTATE_CCW_SLOW = "rotate_ccw_slow"
EVENT_ROTATE_CCW_FAST = "rotate_ccw_fast"
# --------------------------------------------------------------------------------------
# CEN / CEN+ scenario controls (0.4.0)
#
# A wall keypad carries no state, so a scenario control is declared in ``myhome.yaml``
# under ``scenario_control:`` and becomes ONE device on the gateway carrying ONE
# ``event`` entity (HA platform ``event``).  The device exists so that its buttons can
# be picked from the automation UI through ``device_trigger.py``; the entity makes the
# last press visible in the state machine and in history.
#
# Controls that are NOT declared keep firing the bus events only (backward compatible).
# --------------------------------------------------------------------------------------
CONF_SCENARIO_CONTROL = "scenario_control"  # YAML block name and translation key
CONF_PROTOCOL = "protocol"
CONF_OBJECT = "object"
CONF_BUTTONS = "buttons"
ATTR_PUSHBUTTON = "pushbutton"
ATTR_MAC = "mac"
ATTR_EVENT = "event"

PROTOCOL_CEN_PLUS = "cen_plus"
PROTOCOL_CEN = "cen"
SCENARIO_PROTOCOLS: tuple[str, ...] = (PROTOCOL_CEN_PLUS, PROTOCOL_CEN)

# WHO of each protocol (OWNd: 15 -> OWNCENEvent, 25 -> OWNCENPlusEvent).
WHO_CEN = "15"
WHO_CEN_PLUS = "25"
SCENARIO_CONTROL_WHO: dict[str, str] = {PROTOCOL_CEN_PLUS: WHO_CEN_PLUS, PROTOCOL_CEN: WHO_CEN}

# Bus event fired for each protocol (unchanged contract, see docs/services-and-events.md).
EVENT_CENPLUS = "myhome_cenplus_event"
EVENT_CEN = "myhome_cen_event"
# WHO 1 "command translation" frames (*1*1000#WHAT*WHERE##): what a physical light
# pushbutton sent, before the actuator answered. The only trace a relay leaves of a
# dimmer-mode hold (WHAT 30/31), so it is republished as a bus event (0.4.0).
EVENT_LIGHT_PUSHBUTTON = "myhome_light_pushbutton_event"
LIGHT_PUSHBUTTON_EVENTS: dict[int, str] = {0: "off", 1: "on", 30: "dim_up", 31: "dim_down"}
SCENARIO_CONTROL_BUS_EVENT: dict[str, str] = {PROTOCOL_CEN_PLUS: EVENT_CENPLUS, PROTOCOL_CEN: EVENT_CEN}

# Event names each protocol can produce, in the order gateway.py maps them.  These are
# the ``event_types`` of the event entity AND the ``type`` of every device trigger, so
# adding one here means adding a ``device_automation.trigger_type`` translation.
SCENARIO_CONTROL_EVENT_TYPES: dict[str, tuple[str, ...]] = {
    PROTOCOL_CEN_PLUS: (
        CONF_SHORT_PRESS,
        CONF_LONG_PRESS,
        EVENT_LONG_PRESS_REPEAT,
        CONF_LONG_RELEASE,
        EVENT_ROTATE_CW_SLOW,
        EVENT_ROTATE_CW_FAST,
        EVENT_ROTATE_CCW_SLOW,
        EVENT_ROTATE_CCW_FAST,
    ),
    # CEN has no "still held" repeat and no rotary, but it does report the release
    # after a short press as its own frame.
    PROTOCOL_CEN: (
        CONF_SHORT_PRESS,
        CONF_SHORT_RELEASE,
        CONF_LONG_PRESS,
        CONF_LONG_RELEASE,
    ),
}

# Button numbering differs: CEN+ pushbuttons are 1-32, CEN pushbuttons are 0-31.
SCENARIO_CONTROL_BUTTON_RANGE: dict[str, tuple[int, int]] = {
    PROTOCOL_CEN_PLUS: (1, 32),
    PROTOCOL_CEN: (0, 31),
}
DEFAULT_SCENARIO_BUTTONS: tuple[int, ...] = (1, 2, 3, 4)
# CEN+ object numbers are 1-2047; the bus WHERE is "2" + object (e.g. object 25 -> WHERE 225).
SCENARIO_OBJECT_RANGE: tuple[int, int] = (1, 2047)

SCENARIO_CONTROL_MODELS: dict[str, str] = {
    PROTOCOL_CEN_PLUS: "CEN+ scenario control",
    PROTOCOL_CEN: "CEN scenario control",
}

# Device-trigger subtypes: one per button ("button_3"), so the automation UI shows two
# dropdowns (what happened / which button) instead of one flat list.
SCENARIO_SUBTYPE_PREFIX = "button_"


def scenario_control_key(protocol: str, address: object) -> str:
    """Device key of a scenario control: ``cenplus-<object>`` / ``cen-<where>``.

    Used as the key in ``hass.data[...][CONF_PLATFORMS]["event"]``, as the tail of the
    device registry identifier (``{mac}-{key}``) and of the entity ``unique_id``
    (``{mac}-{key}-event``); ``device_trigger.py`` parses it back out of the identifier.
    """
    prefix = "cenplus" if protocol == PROTOCOL_CEN_PLUS else "cen"
    return f"{prefix}-{address}"


# Energy sensor tuning keys (Contract A / E); ``sensor_defaults`` is the gateway-level
# block validate.py merges into every power/energy sensor.
CONF_SENSOR_DEFAULTS = "sensor_defaults"
CONF_MIN_DELTA_W = "min_delta_w"
CONF_MIN_INTERVAL_SEC = "min_interval_sec"
CONF_SUPPRESS_LOG_INTERVAL_SEC = "suppress_log_interval_sec"
CONF_INFO_LOG_INTERVAL_SEC = "info_log_interval_sec"
CONF_KEEPALIVE_MINUTES = "keepalive_minutes"

# Defaults shared by the validator and the platforms.
DEFAULT_MANUFACTURER = "BTicino S.p.A."
DEFAULT_SHUTTER_RUN = 20.0  # seconds, full travel of a basic cover (Contract F)
DEFAULT_SLAT_TIME = 0.0  # seconds of slat-only travel; 0 disables the two-phase model
DEFAULT_KEEPALIVE_MINUTES = 125  # instant power keep-alive (Contract E; 0 = disabled)

# Device type constants (used by discovery.py to classify bus traffic)
DEVICE_TYPE_GENERIC = "generic_device"
DEVICE_TYPE_BUS_ON_OFF_SWITCH = "bus_on_off_switch"
DEVICE_TYPE_BUS_DIMMER = "bus_dimmer"
DEVICE_TYPE_BUS_LIGHT_GROUP = "bus_light_group"
DEVICE_TYPE_BUS_AUTOMATION = "bus_automation"
DEVICE_TYPE_BUS_ENERGY_METER = "bus_energy_meter"
DEVICE_TYPE_BUS_THERMO_SENSOR = "bus_thermo_sensor"
DEVICE_TYPE_BUS_THERMO_ZONE = "bus_thermo_zone"
DEVICE_TYPE_BUS_THERMO_CU = "bus_thermo_cu"
DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL = "bus_cen_scenario_control"
DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL = "bus_cenplus_scenario_control"
DEVICE_TYPE_BUS_DRY_CONTACT_IR = "bus_dry_contact_ir"
DEVICE_TYPE_BUS_SCENARIO = "bus_scenario_control"
DEVICE_TYPE_BUS_ALARM_SYSTEM = "bus_alarm_system"
DEVICE_TYPE_BUS_ALARM_ZONE = "bus_alarm_zone"
DEVICE_TYPE_BUS_AUX = "bus_aux"

# Every device type discovery.py may report (anything else becomes DEVICE_TYPE_GENERIC).
ALL_DEVICE_SUPPORTED_TYPES: set[str] = {
    DEVICE_TYPE_GENERIC,
    DEVICE_TYPE_BUS_ON_OFF_SWITCH,
    DEVICE_TYPE_BUS_DIMMER,
    DEVICE_TYPE_BUS_LIGHT_GROUP,
    DEVICE_TYPE_BUS_AUTOMATION,
    DEVICE_TYPE_BUS_ENERGY_METER,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DEVICE_TYPE_BUS_THERMO_CU,
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_DRY_CONTACT_IR,
    DEVICE_TYPE_BUS_SCENARIO,
    DEVICE_TYPE_BUS_ALARM_SYSTEM,
    DEVICE_TYPE_BUS_ALARM_ZONE,
    DEVICE_TYPE_BUS_AUX,
}

# Device type -> the Home Assistant platform the device ends up on, which is also the
# ``myhome.yaml`` section it is declared under except for the two CEN / CEN+ rows:
# they become ``event`` entities but are written under ``scenario_control:``, because
# there is no ``event:`` section in the file schema.  (The central unit is a milder
# case: its section really is ``climate:``, it is only the key inside it that differs,
# ``zone:`` rather than ``where:``.)
# This is published verbatim as the ``platform`` key of ``myhome_device_discovered``
# (see docs/services-and-events.md), so every value here is a promise that the
# integration really builds that kind of entity for this WHO.  ``None`` means it
# builds none: the honest answer for a family the integration has no platform for, and
# the reason the round-1 "button" -> "event" fix was needed for scenario controls (a
# stale value sends users looking for a ``button.*`` entity that will never exist).
DEVICE_TYPE_TO_PLATFORM: dict[str, str | None] = {
    DEVICE_TYPE_BUS_ON_OFF_SWITCH: "light",
    DEVICE_TYPE_BUS_DIMMER: "light",
    DEVICE_TYPE_BUS_LIGHT_GROUP: "light",
    DEVICE_TYPE_BUS_AUTOMATION: "cover",
    DEVICE_TYPE_BUS_ENERGY_METER: "sensor",
    DEVICE_TYPE_BUS_THERMO_SENSOR: "sensor",
    DEVICE_TYPE_BUS_THERMO_ZONE: "climate",
    # WHO 4 with WHERE ``0``: the thermoregulation central unit, declared as
    # ``climate: {zone: '#0'}`` (discovery.py re-spells the WHERE; a bare ``0`` is
    # refused by validate.Zone).
    DEVICE_TYPE_BUS_THERMO_CU: "climate",
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL: "event",
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL: "event",
    DEVICE_TYPE_BUS_DRY_CONTACT_IR: "binary_sensor",
    # An auxiliary channel is WHO 9, and ``binary_sensor`` is the only section whose
    # schema accepts WHO 9 (validate.BINARY_SENSOR_FIELDS: _who("1", "9", "25"));
    # ``switch`` is WHO 1 only, so the old "switch" hint produced YAML that refused
    # to load.
    DEVICE_TYPE_BUS_AUX: "binary_sensor",
    # WHO 5.  There is no alarm platform in this integration, and a WHO 5 device is
    # rejected by every section that exists (``binary_sensor`` is WHO 1/9/25), so
    # naming one would be the same lie the scenario controls used to tell.  This row
    # is reached in practice: a burglar-alarm *sensor* frame
    # (``*5*<what>*<zone><sensor>##``) carries a plain WHERE and survives discovery's
    # group-address guard, so ``platform: null`` really is published.
    DEVICE_TYPE_BUS_ALARM_ZONE: None,
    # The rows below are never produced by ``discovery._message_to_device_type``
    # today; they exist so the table stays exhaustive over ALL_DEVICE_SUPPORTED_TYPES.
    # WHO 0 scenario modules have no section either (``button.py`` only builds the
    # Lock/Unlock entities of an actuator, never a scenario button).
    DEVICE_TYPE_BUS_SCENARIO: None,
    DEVICE_TYPE_BUS_ALARM_SYSTEM: None,
    DEVICE_TYPE_GENERIC: None,
}

# --- 0.3.0 shared contract (observability + tunables) --------------------------
# Handler statistics: gateway.py publishes a fresh GatewayStats snapshot with
# async_dispatcher_send(hass, SIGNAL_GATEWAY_STATS.format(mac=<mac>), stats)
# at most once per second and on every reconnect/drop event.
SIGNAL_GATEWAY_STATS = "myhome_gateway_stats_{mac}"

# Diagnostic entities attached to the gateway device (unique_id = f"{mac}-{suffix}").
GATEWAY_DIAG_CONNECTED = "gateway-connected"
GATEWAY_DIAG_LAST_FRAME = "gateway-last-frame"
GATEWAY_DIAG_RECONNECTS = "gateway-reconnects"
GATEWAY_DIAG_COMMANDS_DROPPED = "gateway-commands-dropped"
GATEWAY_DIAG_QUEUE_LENGTH = "gateway-queue-length"
GATEWAY_DIAG_SUFFIXES = (
    GATEWAY_DIAG_CONNECTED,
    GATEWAY_DIAG_LAST_FRAME,
    GATEWAY_DIAG_RECONNECTS,
    GATEWAY_DIAG_COMMANDS_DROPPED,
    GATEWAY_DIAG_QUEUE_LENGTH,
)

# Options (entry.options) with their defaults = the values hard-coded in 0.2.x.
CONF_IDLE_WATCHDOG_SEC = "idle_watchdog_sec"
CONF_PROBE_WINDOW_SEC = "probe_window_sec"
CONF_COMMAND_TIMEOUT_SEC = "command_timeout_sec"
CONF_QUEUE_TTL_SEC = "queue_ttl_sec"
CONF_DEFAULT_KEEPALIVE_MINUTES = "default_keepalive_minutes"
DEFAULT_IDLE_WATCHDOG_SEC = 300
DEFAULT_PROBE_WINDOW_SEC = 30
DEFAULT_COMMAND_TIMEOUT_SEC = 10
DEFAULT_QUEUE_TTL_SEC = 60


# --------------------------------------------------------------------------------------
# F422 local bus interface (`<where>#4#<interface>`)
#
# The canonical form is the UNPADDED decimal string, because that is what the bus puts
# in the frame and therefore what OWNd 0.7.49 returns from `OWNMessage.interface`
# (0.7.48 compared an int WHO against strings and always returned None, which hid the
# mismatch).  Zero padding survives in ONE place only: `validate.device_key`, which is
# also the tail of every entity `unique_id`.
# --------------------------------------------------------------------------------------
def normalise_bus_interface(value: object) -> str | None:
    """Return the canonical unpadded interface string, or ``None`` when unusable.

    ``3``, ``"3"`` and ``"03"`` all normalise to ``"3"``.  Out-of-range and malformed
    values give ``None``; callers that need an error raise it themselves
    (``validate.BusInterface``).
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value) if 0 <= value <= 15 else None
    if isinstance(value, str) and value.isdigit() and len(value) <= 2 and int(value) <= 15:
        return str(int(value))
    return None


def clamp_worker_count(value: object, default: int = 1) -> int:
    """How many command sessions an option value really opens.

    Three places need the same answer and used to compute it apart: the setup
    (``__init__.async_setup_entry``, which acts on it), the options form (which
    pre-fills it -- an entry saved under the old 1-10 form otherwise opened on a
    number its own schema then refused, so *every* save failed, including one that
    only meant to change the IP address), and the diagnostics "effective options"
    section (which reports it next to ``handler.sending_workers``, and used to
    contradict it).  A hand-edited entry may hold anything at all, hence the
    non-numeric fallback.
    """
    try:
        number = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default
    return min(max(1, number), MAX_COMMAND_WORKERS)


def bus_full_where(where: str, interface: object) -> str:
    """WHERE as it must appear on the bus: ``11`` or ``11#4#3`` (never ``11#4#03``)."""
    normalised = normalise_bus_interface(interface)
    return f"{where}#4#{normalised}" if normalised is not None else str(where)


# --------------------------------------------------------------------------------------
# Plant-wide addresses (WHO 1 / WHO 2)
# --------------------------------------------------------------------------------------
def is_bus_scope_address(message: OWNMessage) -> bool:
    """True when a lighting/automation frame addresses a *scope* and not one device.

    OpenWebNet spells three plant-wide scopes in the WHERE of a WHO 1 or WHO 2 frame,
    and OWNd 0.7.49 decodes all three (``OWNMessage.is_general`` / ``is_area`` /
    ``is_group``):

    - the **general** address ``0`` -- every lamp, or every shutter, of the plant;
    - an **area** ``00``, ``1``-``9`` or ``100`` (``100`` is area 10: the bus spells
      it with three digits, the configuration schema with two);
    - a **group** ``#1``-``#255``.

    None of them is a device, and this one predicate is what says so for the whole
    integration.  ``gateway._handle_lighting_scope`` / ``_handle_automation_scope``
    intercept such a frame, fire the matching ``myhome_*_light_event`` /
    ``myhome_*_automation_event`` and never dispatch it to an entity; discovery must
    refuse it for the same reason, because a device it announces is a block the user
    pastes into ``myhome.yaml``:

    - ``light: {where: '0'}`` builds an entity whose "turn on" sends ``*1*1*0##``,
      i.e. switches every light in the house, and which can never show a state
      (the dispatcher intercepts every frame that would update it);
    - ``light: {where: '100'}`` is refused by the schema outright -- which does not
      break one device, it makes the whole ``myhome.yaml`` fail to load, so every
      device of that gateway disappears.

    Two callers, one definition, so the dispatcher and the discovery service cannot
    drift apart again.  ``is_general`` returns ``None`` (not ``False``) for a WHO 1 /
    WHO 2 frame whose WHERE is not the general address -- every other WHO gets a plain
    ``False`` -- hence the ``bool()``.
    """
    return bool(message.is_general or message.is_area or message.is_group)


# Repairs issue ids (issue_registry), all prefixed with the entry id by the caller.
ISSUE_YAML_INVALID = "yaml_invalid"
ISSUE_UNKNOWN_KEYS = "unknown_keys"
ISSUE_NO_DEVICES_FOR_GATEWAY = "no_devices_for_gateway"
