"""Device handler factory for MyHOME integration following OpenHAB patterns."""

from typing import Optional, Dict, Any
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DEVICE_TYPE_TO_PLATFORM,
    ALL_DEVICE_SUPPORTED_TYPES,
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

class MyHOMEDeviceFactory:
    """Factory for creating MyHOME device handlers following OpenHAB patterns."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the device factory."""
        self.hass = hass
        self.config_entry = config_entry
        self.logger = logging.getLogger(__name__)
    
    def supports_device_type(self, device_type: str) -> bool:
        """Check if device type is supported."""
        return device_type in ALL_DEVICE_SUPPORTED_TYPES
    
    def get_platform_for_device_type(self, device_type: str) -> Optional[str]:
        """Get the Home Assistant platform for a device type."""
        return DEVICE_TYPE_TO_PLATFORM.get(device_type)
    
    def get_device_category(self, device_type: str) -> str:
        """Get device category based on device type (following OpenHAB pattern)."""
        if device_type in LIGHTING_SUPPORTED_DEVICE_TYPES:
            return "lighting"
        elif device_type in LIGHTING_GROUP_SUPPORTED_DEVICE_TYPES:
            return "lighting_group"
        elif device_type in AUTOMATION_SUPPORTED_DEVICE_TYPES:
            return "automation"
        elif device_type in THERMOREGULATION_SUPPORTED_DEVICE_TYPES:
            return "thermoregulation"
        elif device_type in ENERGY_MANAGEMENT_SUPPORTED_DEVICE_TYPES:
            return "energy_management"
        elif device_type in SCENARIO_SUPPORTED_DEVICE_TYPES:
            return "scenario"
        elif device_type in SCENARIO_BASIC_SUPPORTED_DEVICE_TYPES:
            return "scenario_basic"
        elif device_type in AUX_SUPPORTED_DEVICE_TYPES:
            return "auxiliary"
        elif device_type in ALARM_SUPPORTED_DEVICE_TYPES:
            return "alarm"
        elif device_type in GENERIC_SUPPORTED_DEVICE_TYPES:
            return "generic"
        else:
            return "unknown"
    
    def create_device_config(self, device_type: str, device_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized device configuration following OpenHAB patterns."""
        category = self.get_device_category(device_type)
        platform = self.get_platform_for_device_type(device_type)
        
        standardized_config = {
            "device_type": device_type,
            "category": category,
            "platform": platform,
            **device_config
        }
        
        self.logger.debug(
            "Created device config for type %s: category=%s, platform=%s", 
            device_type, category, platform
        )
        
        return standardized_config
    
    def organize_devices_by_category(
        self, devices_config: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Organize devices by category following OpenHAB patterns."""
        organized = {}
        
        for device_id, device_config in devices_config.items():
            device_type = device_config.get("device_type", "generic_device")
            category = self.get_device_category(device_type)
            
            if category not in organized:
                organized[category] = {}
            
            organized[category][device_id] = device_config
        
        return organized
    
    def validate_device_config(
        self, device_type: str, device_config: Dict[str, Any]
    ) -> bool:
        """Validate device configuration."""
        if not self.supports_device_type(device_type):
            self.logger.error("Unsupported device type: %s", device_type)
            return False
        
        # Basic validation - ensure required fields are present
        required_fields = ["where", "name"]
        for field in required_fields:
            if field not in device_config:
                self.logger.error(
                    "Missing required field '%s' for device type %s", 
                    field, device_type
                )
                return False
        
        return True
    
    def get_supported_device_types(self) -> set:
        """Get all supported device types."""
        return ALL_DEVICE_SUPPORTED_TYPES.copy()
    
    def get_device_types_for_platform(self, platform: str) -> set:
        """Get device types that belong to a specific platform."""
        return {
            device_type for device_type, device_platform in DEVICE_TYPE_TO_PLATFORM.items()
            if device_platform == platform
        }
    
    def create_device_handler(self, device_type: str, device_config: Dict[str, Any]):
        """Create appropriate device handler following OpenHAB factory pattern."""
        from .device_handler import (
            MyHOMELightingHandler,
            MyHOMEAutomationHandler,
            MyHOMEThermoregulationHandler,
            MyHOMEEnergyHandler,
            MyHOMEScenarioHandler,
            MyHOMEAlarmHandler,
            MyHOMEAuxiliaryHandler,
            MyHOMEGenericHandler,
        )
        
        # Map device types to handlers following OpenHAB pattern
        if device_type in LIGHTING_SUPPORTED_DEVICE_TYPES | LIGHTING_GROUP_SUPPORTED_DEVICE_TYPES:
            self.logger.debug("Creating LIGHTING Handler for device type %s", device_type)
            return MyHOMELightingHandler(self.hass, self.config_entry, device_config)
        elif device_type in AUTOMATION_SUPPORTED_DEVICE_TYPES:
            self.logger.debug("Creating AUTOMATION Handler for device type %s", device_type)
            return MyHOMEAutomationHandler(self.hass, self.config_entry, device_config)
        elif device_type in THERMOREGULATION_SUPPORTED_DEVICE_TYPES:
            self.logger.debug("Creating THERMOREGULATION Handler for device type %s", device_type)
            return MyHOMEThermoregulationHandler(self.hass, self.config_entry, device_config)
        elif device_type in ENERGY_MANAGEMENT_SUPPORTED_DEVICE_TYPES:
            self.logger.debug("Creating ENERGY Handler for device type %s", device_type)
            return MyHOMEEnergyHandler(self.hass, self.config_entry, device_config)
        elif device_type in SCENARIO_SUPPORTED_DEVICE_TYPES | SCENARIO_BASIC_SUPPORTED_DEVICE_TYPES:
            self.logger.debug("Creating SCENARIO Handler for device type %s", device_type)
            return MyHOMEScenarioHandler(self.hass, self.config_entry, device_config)
        elif device_type in ALARM_SUPPORTED_DEVICE_TYPES:
            self.logger.debug("Creating ALARM Handler for device type %s", device_type)
            return MyHOMEAlarmHandler(self.hass, self.config_entry, device_config)
        elif device_type in AUX_SUPPORTED_DEVICE_TYPES:
            self.logger.debug("Creating AUXILIARY Handler for device type %s", device_type)
            return MyHOMEAuxiliaryHandler(self.hass, self.config_entry, device_config)
        elif device_type in GENERIC_SUPPORTED_DEVICE_TYPES:
            self.logger.debug("Creating GENERIC Handler for device type %s", device_type)
            return MyHOMEGenericHandler(self.hass, self.config_entry, device_config)
        else:
            self.logger.warning("Device type %s is not supported by this factory", device_type)
            return None