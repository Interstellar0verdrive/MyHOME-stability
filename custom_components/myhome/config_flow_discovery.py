"""Config flow discovery for MyHOME devices following OpenHAB patterns."""

import logging
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    DEVICE_TYPE_TO_PLATFORM,
    ALL_DEVICE_SUPPORTED_TYPES,
)
from .device_factory import MyHOMEDeviceFactory


class MyHOMEDiscoveryConfigFlow:
    """Handle discovered MyHOME devices following OpenHAB patterns."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the discovery config flow."""
        self.hass = hass
        self.logger = logging.getLogger(__name__)
        
        # Listen for discovery events
        self._setup_discovery_listeners()
    
    @callback
    def _setup_discovery_listeners(self) -> None:
        """Setup discovery event listeners."""
        self.hass.bus.async_listen(
            f"{DOMAIN}_device_discovered", 
            self._handle_device_discovered
        )
        
        self.hass.bus.async_listen(
            f"{DOMAIN}_discovery_completed",
            self._handle_discovery_completed
        )
    
    @callback
    async def _handle_device_discovered(self, event) -> None:
        """Handle device discovered event following OpenHAB patterns."""
        try:
            discovery_data = event.data
            device_info = discovery_data.get("discovered_device")
            
            if not device_info:
                return
            
            # Check if device is already configured
            if await self._is_device_configured(device_info):
                self.logger.debug("Device %s already configured, skipping", 
                                device_info["unique_id"])
                return
            
            # Create Home Assistant device registry entry
            await self._create_device_registry_entry(device_info, discovery_data)
            
            # Suggest device configuration to user
            await self._suggest_device_configuration(device_info, discovery_data)
            
        except Exception as e:
            self.logger.error("Error handling device discovered event: %s", e)
    
    @callback
    async def _handle_discovery_completed(self, event) -> None:
        """Handle discovery completion event."""
        try:
            data = event.data
            gateway_mac = data.get("gateway_mac")
            discovered_count = data.get("discovered_count", 0)
            
            self.logger.info(
                "Discovery completed for gateway %s: %d devices found",
                gateway_mac, discovered_count
            )
            
            # Fire notification about discovery completion
            self.hass.bus.async_fire(f"{DOMAIN}_notify", {
                "title": "MyHOME Discovery Complete",
                "message": f"Found {discovered_count} devices on gateway {gateway_mac}",
                "notification_id": f"myhome_discovery_{gateway_mac}"
            })
            
        except Exception as e:
            self.logger.error("Error handling discovery completed event: %s", e)
    
    async def _is_device_configured(self, device_info: Dict[str, Any]) -> bool:
        """Check if device is already configured."""
        device_registry = dr.async_get(self.hass)
        
        # Check by unique ID
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, device_info["unique_id"])}
        )
        
        return device_entry is not None
    
    async def _create_device_registry_entry(
        self, 
        device_info: Dict[str, Any], 
        discovery_data: Dict[str, Any]
    ) -> None:
        """Create device registry entry following OpenHAB patterns."""
        try:
            device_registry = dr.async_get(self.hass)
            config_entry_id = discovery_data.get("config_entry_id")
            gateway_mac = discovery_data.get("gateway_mac")
            
            # Create device entry
            device_entry = device_registry.async_get_or_create(
                config_entry_id=config_entry_id,
                identifiers={(DOMAIN, device_info["unique_id"])},
                manufacturer="BTicino/Legrand",
                name=device_info["name"],
                model=f"MyHOME {device_info['device_type'].replace('_', ' ').title()}",
                via_device=(DOMAIN, gateway_mac),
                sw_version=device_info["properties"].get("firmware_version"),
            )
            
            self.logger.debug("Created device registry entry for %s", device_info["name"])
            
        except Exception as e:
            self.logger.error("Error creating device registry entry: %s", e)
    
    async def _suggest_device_configuration(
        self, 
        device_info: Dict[str, Any],
        discovery_data: Dict[str, Any]
    ) -> None:
        """Suggest device configuration to user following OpenHAB patterns."""
        try:
            # Create a suggested configuration entry for the user to approve
            config_data = {
                "device_info": device_info,
                "discovery_data": discovery_data,
                "suggested_config": self._generate_suggested_config(device_info)
            }
            
            # Fire event for UI to handle
            self.hass.bus.async_fire(f"{DOMAIN}_device_suggestion", config_data)
            
            self.logger.debug("Suggested configuration for device %s", device_info["name"])
            
        except Exception as e:
            self.logger.error("Error suggesting device configuration: %s", e)
    
    def _generate_suggested_config(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate suggested configuration following OpenHAB patterns."""
        device_type = device_info["device_type"]
        platform = device_info["platform"]
        where = device_info["where"]
        name = device_info["name"]
        
        # Base configuration
        suggested_config = {
            "where": where,
            "name": name,
            "device_type": device_type,
            "platform": platform,
        }
        
        # Add device-specific configuration following OpenHAB patterns
        if device_type in ["bus_dimmer", "bus_on_off_switch"]:
            suggested_config.update({
                "dimmable": device_type == "bus_dimmer",
                "icon": "mdi:lightbulb" if device_type == "bus_dimmer" else "mdi:light-switch"
            })
        
        elif device_type == "bus_automation":
            suggested_config.update({
                "device_class": "shutter",
                "icon": "mdi:window-shutter",
                "shutter_run": 20  # Default run time in seconds
            })
        
        elif device_type == "bus_energy_meter":
            suggested_config.update({
                "device_class": "energy",
                "unit_of_measurement": "W",
                "icon": "mdi:flash",
                "refresh_period": 30
            })
        
        elif device_type in ["bus_thermo_zone", "bus_thermo_sensor"]:
            suggested_config.update({
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "icon": "mdi:thermometer",
                "standalone": device_type == "bus_thermo_sensor"
            })
        
        elif device_type in ["bus_cen_scenario_control", "bus_cenplus_scenario_control"]:
            suggested_config.update({
                "device_class": "button",
                "icon": "mdi:gesture-tap-button",
                "buttons": "1,2,3,4"  # Default button configuration
            })
        
        elif device_type == "bus_dry_contact_ir":
            suggested_config.update({
                "device_class": "motion",
                "icon": "mdi:motion-sensor"
            })
        
        elif device_type == "bus_aux":
            suggested_config.update({
                "device_class": "switch",
                "icon": "mdi:electric-switch"
            })
        
        elif device_type in ["bus_alarm_system", "bus_alarm_zone"]:
            suggested_config.update({
                "device_class": "safety",
                "icon": "mdi:shield-home"
            })
        
        return suggested_config


@callback
def async_setup_discovery(hass: HomeAssistant) -> None:
    """Setup discovery config flow following OpenHAB patterns."""
    discovery = MyHOMEDiscoveryConfigFlow(hass)
    
    # Store reference for cleanup
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["discovery"] = discovery