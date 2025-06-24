"""Constants for the MyHome component."""
import logging
from typing import Dict, Set

LOGGER = logging.getLogger(__package__)
DOMAIN = "myhome"

# Request timeout constants
THING_STATE_REQ_TIMEOUT_SEC = 5

# Event attributes
ATTR_GATEWAY = "gateway"
ATTR_MESSAGE = "message"

# Configuration constants
CONF = "config"
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
CONF_PARENT_ID = "parent_id"
CONF_WHO = "who"
CONF_WHERE = "where"
CONF_BUS_INTERFACE = "interface"
CONF_ZONE = "zone"
CONF_DIMMABLE = "dimmable"
CONF_GATEWAY = "gateway"
CONF_DEVICE_CLASS = "class"
CONF_INVERTED = "inverted"
CONF_ADVANCED_SHUTTER = "advanced"
CONF_HEATING_SUPPORT = "heat"
CONF_COOLING_SUPPORT = "cool"
CONF_FAN_SUPPORT = "fan"
CONF_STANDALONE = "standalone"
CONF_CENTRAL = "central"
CONF_SHORT_PRESS = "pushbutton_short_press"
CONF_SHORT_RELEASE = "pushbutton_short_release"
CONF_LONG_PRESS = "pushbutton_long_press"
CONF_LONG_RELEASE = "pushbutton_long_release"

# Device type constants (following OpenHAB pattern)
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

# Supported device type sets (following OpenHAB pattern)
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

# Channel constants (following OpenHAB pattern)
CHANNEL_SWITCH = "switch"
CHANNEL_SWITCH_01 = "switch_01"
CHANNEL_SWITCH_02 = "switch_02"
CHANNEL_BRIGHTNESS = "brightness"
CHANNEL_SHUTTER = "shutter"
CHANNEL_TEMPERATURE = "temperature"
CHANNEL_FUNCTION = "function"
CHANNEL_TEMP_SETPOINT = "setpointTemperature"
CHANNEL_TEMP_TARGET = "targetTemperature"
CHANNEL_MODE = "mode"
CHANNEL_FAN_SPEED = "speedFanCoil"
CHANNEL_POWER = "power"
CHANNEL_ENERGY_TOTALIZER_DAY = "energyToday"
CHANNEL_ENERGY_TOTALIZER_MONTH = "energyThisMonth"
CHANNEL_SCENARIO_BUTTON = "button#"
CHANNEL_DRY_CONTACT_IR = "sensor"
CHANNEL_SCENARIO = "scenario"
CHANNEL_AUX = "aux"
CHANNEL_ALARM_SYSTEM_STATE = "state"
CHANNEL_ALARM_SYSTEM_ARMED = "armed"
CHANNEL_ALARM_ZONE_STATE = "state"
CHANNEL_ALARM_ZONE_ALARM = "alarm"

# Config properties (following OpenHAB pattern)
CONFIG_PROPERTY_WHERE = "where"
CONFIG_PROPERTY_SHUTTER_RUN = "shutterRun"
CONFIG_PROPERTY_SCENARIO_BUTTONS = "buttons"
CONFIG_PROPERTY_STANDALONE = "standAlone"
CONFIG_PROPERTY_REFRESH_PERIOD = "energyRefreshPeriod"

# Properties
PROPERTY_OWNID = "ownId"
PROPERTY_FIRMWARE_VERSION = "firmwareVersion"
PROPERTY_MODEL = "model"
PROPERTY_SERIAL_NO = "serialNumber"
