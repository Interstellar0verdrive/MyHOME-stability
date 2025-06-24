"""Base device handler following OpenHAB patterns."""

from abc import abstractmethod
from typing import Dict, Any, Optional, Set
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import (
    PROPERTY_OWNID,
    PROPERTY_FIRMWARE_VERSION,
    PROPERTY_MODEL,
    PROPERTY_SERIAL_NO,
    CONFIG_PROPERTY_WHERE,
    LIGHTING_SUPPORTED_DEVICE_TYPES,
    LIGHTING_GROUP_SUPPORTED_DEVICE_TYPES,
    AUTOMATION_SUPPORTED_DEVICE_TYPES,
    THERMOREGULATION_SUPPORTED_DEVICE_TYPES,
    ENERGY_MANAGEMENT_SUPPORTED_DEVICE_TYPES,
    SCENARIO_SUPPORTED_DEVICE_TYPES,
    SCENARIO_BASIC_SUPPORTED_DEVICE_TYPES,
    AUX_SUPPORTED_DEVICE_TYPES,
    ALARM_SUPPORTED_DEVICE_TYPES,
    GENERIC_SUPPORTED_DEVICE_TYPES,
)


class MyHOMEDeviceHandler:
    """Base class for MyHOME device handlers following OpenHAB patterns."""
    
    # To be overridden by subclasses
    SUPPORTED_DEVICE_TYPES: Set[str] = set()
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_config: Dict[str, Any]):
        """Initialize the device handler."""
        self.hass = hass
        self.config_entry = config_entry
        self.device_config = device_config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Device properties
        self._device_where = device_config.get(CONFIG_PROPERTY_WHERE)
        self._device_name = device_config.get("name", f"MyHOME Device {self._device_where}")
        self._device_type = device_config.get("device_type", "generic_device")
        
        # Initialize properties following OpenHAB pattern
        self._properties = self._initialize_properties()
    
    @property
    def device_where(self) -> Optional[str]:
        """Get device WHERE address."""
        return self._device_where
    
    @property
    def device_name(self) -> str:
        """Get device name."""
        return self._device_name
    
    @property
    def device_type(self) -> str:
        """Get device type."""
        return self._device_type
    
    @property
    def unique_id(self) -> str:
        """Get unique ID for this device."""
        return f"{self.config_entry.data['mac']}-{self._device_where}"
    
    @property
    def properties(self) -> Dict[str, Any]:
        """Get device properties following OpenHAB pattern."""
        return self._properties.copy()
    
    def _initialize_properties(self) -> Dict[str, Any]:
        """Initialize device properties following OpenHAB pattern."""
        properties = {}
        
        if self._device_where:
            properties[PROPERTY_OWNID] = self._device_where
        
        # Add model and other properties from config
        if "model" in self.device_config:
            properties[PROPERTY_MODEL] = self.device_config["model"]
        
        if "firmware_version" in self.device_config:
            properties[PROPERTY_FIRMWARE_VERSION] = self.device_config["firmware_version"]
        
        if "serial_number" in self.device_config:
            properties[PROPERTY_SERIAL_NO] = self.device_config["serial_number"]
        
        return properties
    
    @classmethod
    def supports_device_type(cls, device_type: str) -> bool:
        """Check if this handler supports the given device type."""
        return device_type in cls.SUPPORTED_DEVICE_TYPES
    
    @abstractmethod
    async def async_initialize(self) -> bool:
        """Initialize the device handler. Returns True if successful."""
        pass
    
    @abstractmethod
    async def async_update_state(self) -> None:
        """Update device state."""
        pass
    
    @abstractmethod
    def handle_message(self, message: Any) -> None:
        """Handle incoming messages for this device."""
        pass
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get device info dictionary for Home Assistant."""
        return {
            "identifiers": {("myhome", self.unique_id)},
            "name": self.device_name,
            "manufacturer": "BTicino/Legrand",
            "model": self.properties.get(PROPERTY_MODEL, "MyHOME Device"),
            "sw_version": self.properties.get(PROPERTY_FIRMWARE_VERSION),
            "via_device": ("myhome", self.config_entry.data["mac"]),
        }
    
    def log_debug(self, message: str, *args) -> None:
        """Log debug message with device context."""
        self.logger.debug(f"[{self.device_name}@{self._device_where}] {message}", *args)
    
    def log_info(self, message: str, *args) -> None:
        """Log info message with device context."""
        self.logger.info(f"[{self.device_name}@{self._device_where}] {message}", *args)
    
    def log_warning(self, message: str, *args) -> None:
        """Log warning message with device context."""
        self.logger.warning(f"[{self.device_name}@{self._device_where}] {message}", *args)
    
    def log_error(self, message: str, *args) -> None:
        """Log error message with device context."""
        self.logger.error(f"[{self.device_name}@{self._device_where}] {message}", *args)


class MyHOMELightingHandler(MyHOMEDeviceHandler):
    """Handler for lighting devices following OpenHAB patterns."""
    
    SUPPORTED_DEVICE_TYPES = LIGHTING_SUPPORTED_DEVICE_TYPES | LIGHTING_GROUP_SUPPORTED_DEVICE_TYPES
    
    async def async_initialize(self) -> bool:
        """Initialize lighting device."""
        self.log_debug("Initializing lighting device")
        return True
    
    async def async_update_state(self) -> None:
        """Update lighting device state."""
        self.log_debug("Updating lighting device state")
    
    def handle_message(self, message: Any) -> None:
        """Handle lighting message."""
        self.log_debug("Handling lighting message: %s", message)


class MyHOMEAutomationHandler(MyHOMEDeviceHandler):
    """Handler for automation devices following OpenHAB patterns."""
    
    SUPPORTED_DEVICE_TYPES = AUTOMATION_SUPPORTED_DEVICE_TYPES
    
    async def async_initialize(self) -> bool:
        """Initialize automation device."""
        self.log_debug("Initializing automation device")
        return True
    
    async def async_update_state(self) -> None:
        """Update automation device state."""
        self.log_debug("Updating automation device state")
    
    def handle_message(self, message: Any) -> None:
        """Handle automation message."""
        self.log_debug("Handling automation message: %s", message)


class MyHOMEThermoregulationHandler(MyHOMEDeviceHandler):
    """Handler for thermoregulation devices following OpenHAB patterns."""
    
    SUPPORTED_DEVICE_TYPES = THERMOREGULATION_SUPPORTED_DEVICE_TYPES
    
    async def async_initialize(self) -> bool:
        """Initialize thermoregulation device."""
        self.log_debug("Initializing thermoregulation device")
        return True
    
    async def async_update_state(self) -> None:
        """Update thermoregulation device state."""
        self.log_debug("Updating thermoregulation device state")
    
    def handle_message(self, message: Any) -> None:
        """Handle thermoregulation message."""
        self.log_debug("Handling thermoregulation message: %s", message)


class MyHOMEEnergyHandler(MyHOMEDeviceHandler):
    """Handler for energy management devices following OpenHAB patterns."""
    
    SUPPORTED_DEVICE_TYPES = ENERGY_MANAGEMENT_SUPPORTED_DEVICE_TYPES
    
    async def async_initialize(self) -> bool:
        """Initialize energy device."""
        self.log_debug("Initializing energy device")
        return True
    
    async def async_update_state(self) -> None:
        """Update energy device state."""
        self.log_debug("Updating energy device state")
    
    def handle_message(self, message: Any) -> None:
        """Handle energy message."""
        self.log_debug("Handling energy message: %s", message)


class MyHOMEScenarioHandler(MyHOMEDeviceHandler):
    """Handler for scenario devices following OpenHAB patterns."""
    
    SUPPORTED_DEVICE_TYPES = SCENARIO_SUPPORTED_DEVICE_TYPES | SCENARIO_BASIC_SUPPORTED_DEVICE_TYPES
    
    async def async_initialize(self) -> bool:
        """Initialize scenario device."""
        self.log_debug("Initializing scenario device")
        return True
    
    async def async_update_state(self) -> None:
        """Update scenario device state."""
        self.log_debug("Updating scenario device state")
    
    def handle_message(self, message: Any) -> None:
        """Handle scenario message."""
        self.log_debug("Handling scenario message: %s", message)


class MyHOMEAlarmHandler(MyHOMEDeviceHandler):
    """Handler for alarm devices following OpenHAB patterns."""
    
    SUPPORTED_DEVICE_TYPES = ALARM_SUPPORTED_DEVICE_TYPES
    
    async def async_initialize(self) -> bool:
        """Initialize alarm device."""
        self.log_debug("Initializing alarm device")
        return True
    
    async def async_update_state(self) -> None:
        """Update alarm device state."""
        self.log_debug("Updating alarm device state")
    
    def handle_message(self, message: Any) -> None:
        """Handle alarm message."""
        self.log_debug("Handling alarm message: %s", message)


class MyHOMEAuxiliaryHandler(MyHOMEDeviceHandler):
    """Handler for auxiliary devices following OpenHAB patterns."""
    
    SUPPORTED_DEVICE_TYPES = AUX_SUPPORTED_DEVICE_TYPES
    
    async def async_initialize(self) -> bool:
        """Initialize auxiliary device."""
        self.log_debug("Initializing auxiliary device")
        return True
    
    async def async_update_state(self) -> None:
        """Update auxiliary device state."""
        self.log_debug("Updating auxiliary device state")
    
    def handle_message(self, message: Any) -> None:
        """Handle auxiliary message."""
        self.log_debug("Handling auxiliary message: %s", message)


class MyHOMEGenericHandler(MyHOMEDeviceHandler):
    """Handler for generic/unknown devices following OpenHAB patterns."""
    
    SUPPORTED_DEVICE_TYPES = GENERIC_SUPPORTED_DEVICE_TYPES
    
    async def async_initialize(self) -> bool:
        """Initialize generic device."""
        self.log_debug("Initializing generic device")
        return True
    
    async def async_update_state(self) -> None:
        """Update generic device state."""
        self.log_debug("Updating generic device state")
    
    def handle_message(self, message: Any) -> None:
        """Handle generic message."""
        self.log_debug("Handling generic message: %s", message)