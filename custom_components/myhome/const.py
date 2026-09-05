"""Constants for the MyHome component."""
import logging

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

# Device type to platform mapping
DEVICE_TYPE_TO_PLATFORM: dict[str, str] = {
    DEVICE_TYPE_BUS_ON_OFF_SWITCH: "light",
    DEVICE_TYPE_BUS_DIMMER: "light",
    DEVICE_TYPE_BUS_LIGHT_GROUP: "light",
    DEVICE_TYPE_BUS_AUTOMATION: "cover",
    DEVICE_TYPE_BUS_ENERGY_METER: "sensor",
    DEVICE_TYPE_BUS_THERMO_SENSOR: "sensor",
    DEVICE_TYPE_BUS_THERMO_ZONE: "climate",
    DEVICE_TYPE_BUS_THERMO_CU: "climate",
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL: "button",
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL: "button",
    DEVICE_TYPE_BUS_DRY_CONTACT_IR: "binary_sensor",
    DEVICE_TYPE_BUS_SCENARIO: "button",
    DEVICE_TYPE_BUS_ALARM_SYSTEM: "alarm_control_panel",
    DEVICE_TYPE_BUS_ALARM_ZONE: "binary_sensor",
    DEVICE_TYPE_BUS_AUX: "switch",
    DEVICE_TYPE_GENERIC: "sensor"
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

# Repairs issue ids (issue_registry), all prefixed with the entry id by the caller.
ISSUE_YAML_INVALID = "yaml_invalid"
ISSUE_UNKNOWN_KEYS = "unknown_keys"
ISSUE_NO_DEVICES_FOR_GATEWAY = "no_devices_for_gateway"
