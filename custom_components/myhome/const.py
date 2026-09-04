"""Constants for the MyHome component."""
import logging
from typing import Dict, Set

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
THING_STATE_REQ_TIMEOUT_SEC = 5
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
# Energy sensor tuning keys (Contract A / E)
CONF_MIN_DELTA_W = "min_delta_w"
CONF_MIN_INTERVAL_SEC = "min_interval_sec"
CONF_SUPPRESS_LOG_INTERVAL_SEC = "suppress_log_interval_sec"
CONF_KEEPALIVE_MINUTES = "keepalive_minutes"

# Default manufacturer for BTicino/Legrand gateways and devices
DEFAULT_MANUFACTURER = "BTicino S.p.A."

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

# Supported device type sets.
# NOTE: only device_factory.py / device_handler.py (F3, slated for removal) still
# reference these sets; drop them together with those modules.
GENERIC_SUPPORTED_DEVICE_TYPES: Set[str] = {DEVICE_TYPE_GENERIC}

LIGHTING_SUPPORTED_DEVICE_TYPES: Set[str] = {
    DEVICE_TYPE_BUS_ON_OFF_SWITCH,
    DEVICE_TYPE_BUS_DIMMER
}

LIGHTING_GROUP_SUPPORTED_DEVICE_TYPES: Set[str] = {DEVICE_TYPE_BUS_LIGHT_GROUP}

AUTOMATION_SUPPORTED_DEVICE_TYPES: Set[str] = {DEVICE_TYPE_BUS_AUTOMATION}

THERMOREGULATION_SUPPORTED_DEVICE_TYPES: Set[str] = {
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_CU
}

ENERGY_MANAGEMENT_SUPPORTED_DEVICE_TYPES: Set[str] = {DEVICE_TYPE_BUS_ENERGY_METER}

SCENARIO_SUPPORTED_DEVICE_TYPES: Set[str] = {
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_DRY_CONTACT_IR
}

SCENARIO_BASIC_SUPPORTED_DEVICE_TYPES: Set[str] = {DEVICE_TYPE_BUS_SCENARIO}

AUX_SUPPORTED_DEVICE_TYPES: Set[str] = {DEVICE_TYPE_BUS_AUX}

ALARM_SUPPORTED_DEVICE_TYPES: Set[str] = {
    DEVICE_TYPE_BUS_ALARM_SYSTEM,
    DEVICE_TYPE_BUS_ALARM_ZONE
}

# Combined device type sets
ALL_DEVICE_SUPPORTED_TYPES: Set[str] = (
    GENERIC_SUPPORTED_DEVICE_TYPES |
    LIGHTING_SUPPORTED_DEVICE_TYPES |
    LIGHTING_GROUP_SUPPORTED_DEVICE_TYPES |
    AUTOMATION_SUPPORTED_DEVICE_TYPES |
    THERMOREGULATION_SUPPORTED_DEVICE_TYPES |
    ENERGY_MANAGEMENT_SUPPORTED_DEVICE_TYPES |
    SCENARIO_SUPPORTED_DEVICE_TYPES |
    SCENARIO_BASIC_SUPPORTED_DEVICE_TYPES |
    AUX_SUPPORTED_DEVICE_TYPES |
    ALARM_SUPPORTED_DEVICE_TYPES
)

# Device type to platform mapping
DEVICE_TYPE_TO_PLATFORM: Dict[str, str] = {
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

# Legacy OpenHAB-port property names, still imported by device_handler.py (F3).
CONFIG_PROPERTY_WHERE = "where"
PROPERTY_OWNID = "ownId"
PROPERTY_FIRMWARE_VERSION = "firmwareVersion"
PROPERTY_MODEL = "model"
PROPERTY_SERIAL_NO = "serialNumber"
