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
            self.logger.debug("Starting device configuration suggestion for %s", device_info["name"])
            self.logger.debug("Device info for suggestion: %s", device_info)
            
            # Generate suggested configuration
            suggested_config = self._generate_suggested_config(device_info)
            self.logger.debug("Generated suggested config: %s", suggested_config)
            
            # Auto-add device to configuration for now (can be made optional later)
            try:
                self.logger.debug("Attempting to add device to config file...")
                await self._add_device_to_config(device_info, suggested_config, discovery_data)
                self.logger.info("Auto-added discovered device %s to configuration", device_info["name"])
            except Exception as config_error:
                self.logger.error("Failed to add device to config file: %s", config_error)
                self.logger.debug("Config error details - device: %s, config: %s", device_info["name"], suggested_config)
                # Continue with other processing even if config write fails
            
            # Also fire event for UI to handle if needed
            config_data = {
                "device_info": device_info,
                "discovery_data": discovery_data,
                "suggested_config": suggested_config
            }
            self.logger.debug("Firing device suggestion event with data: %s", config_data)
            self.hass.bus.async_fire(f"{DOMAIN}_device_suggestion", config_data)
            self.logger.debug("Device suggestion event fired successfully")
            
        except Exception as e:
            self.logger.error("Error suggesting device configuration for %s: %s", device_info.get("name", "unknown"), e)
            self.logger.debug("Full error context - device_info: %s, discovery_data: %s", device_info, discovery_data)
    
    async def _add_device_to_config(
        self, 
        device_info: Dict[str, Any], 
        suggested_config: Dict[str, Any],
        discovery_data: Dict[str, Any]
    ) -> None:
        """Add discovered device to YAML configuration."""
        try:
            import yaml
            import aiofiles
            import os
            
            gateway_mac = discovery_data["gateway_mac"]
            platform = device_info["platform"]
            where = device_info["where"]
            
            # Use device WHERE as config key, make it unique
            device_key = f"discovered_{where}"
            
            config_file_path = "/config/myhome.yaml"
            
            self.logger.debug("Starting config file write process for device %s", device_info["name"])
            self.logger.debug("Config file path: %s", config_file_path)
            self.logger.debug("Gateway MAC: %s, Platform: %s, WHERE: %s", gateway_mac, platform, where)
            self.logger.debug("Device key: %s", device_key)
            self.logger.debug("Suggested config: %s", suggested_config)
            
            # Read existing config
            try:
                self.logger.debug("Reading existing config file...")
                async with aiofiles.open(config_file_path, mode="r") as yaml_file:
                    content = await yaml_file.read()
                    self.logger.debug("Config file content length: %d chars", len(content))
                    config = yaml.safe_load(content) or {}
                    self.logger.debug("Parsed existing config: %s", config)
            except FileNotFoundError:
                self.logger.info("Config file not found, creating new config structure")
                config = {}
            except Exception as e:
                self.logger.error("Error reading config file: %s", e)
                raise
            
            # Initialize gateway config if needed (use "gateway" as key instead of MAC)
            if "gateway" not in config:
                self.logger.debug("Initializing gateway config structure")
                config["gateway"] = {"mac": gateway_mac}
            else:
                self.logger.debug("Gateway config exists: %s", config["gateway"])
            
            # Initialize platform if needed  
            if platform not in config["gateway"]:
                self.logger.debug("Initializing platform %s in gateway config", platform)
                config["gateway"][platform] = {}
            else:
                self.logger.debug("Platform %s exists with %d devices", platform, len(config["gateway"][platform]))
            
            # Check if device already exists
            if device_key in config["gateway"][platform]:
                self.logger.warning("Device %s already exists in config, overwriting", device_key)
            else:
                self.logger.debug("Adding new device %s to platform %s", device_key, platform)
            
            # Add device config
            config["gateway"][platform][device_key] = suggested_config
            
            self.logger.debug("Device added to config structure")
            self.logger.debug("Updated platform config: %s", config["gateway"][platform])
            self.logger.debug("Full config structure keys: %s", list(config.keys()))
            
            # Write back to file
            try:
                self.logger.debug("Writing updated config to file...")
                async with aiofiles.open(config_file_path, mode="w") as yaml_file:
                    yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
                    self.logger.debug("Generated YAML content length: %d chars", len(yaml_content))
                    await yaml_file.write(yaml_content)
                    self.logger.debug("Config file write completed successfully")
                
                self.logger.info("Successfully added device %s to configuration file at %s", device_info["name"], config_file_path)
                
                # Log file stats for verification
                try:
                    file_stat = os.stat(config_file_path)
                    self.logger.debug("Config file size after write: %d bytes", file_stat.st_size)
                except Exception as stat_error:
                    self.logger.debug("Could not get file stats: %s", stat_error)
                
            except Exception as write_error:
                self.logger.error("Error writing to config file: %s", write_error)
                raise
            
            # Trigger config reload by reloading the integration
            self.logger.info("Config file updated, integration will reload automatically on next restart")
            self.logger.debug("To reload immediately, restart the MyHOME integration or Home Assistant")
            # Note: Don't force reload here as it can cause race conditions during discovery
            # The integration will pick up changes on next restart or manual reload
            
        except Exception as e:
            self.logger.error("Error in config file write process for device %s: %s", device_info["name"], e)
            self.logger.debug("Device info: %s", device_info)
            self.logger.debug("Suggested config: %s", suggested_config)
            self.logger.debug("Discovery data: %s", discovery_data)
    
    def _generate_suggested_config(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate suggested configuration following OpenHAB patterns."""
        device_type = device_info["device_type"]
        platform = device_info["platform"]
        where = device_info["where"]
        name = device_info["name"]
        
        self.logger.debug("Generating config for device type: %s, platform: %s, where: %s, name: %s", 
                         device_type, platform, where, name)
        
        # Base configuration - only include valid schema fields
        suggested_config = {
            "where": where,
            "name": name,
        }
        
        self.logger.debug("Base suggested_config: %s", suggested_config)
        
        # Add device-specific configuration following OpenHAB patterns
        if device_type in ["bus_dimmer", "bus_on_off_switch"]:
            self.logger.debug("Configuring lighting device: %s", device_type)
            suggested_config.update({
                "dimmable": device_type == "bus_dimmer",
                "icon": "mdi:lightbulb" if device_type == "bus_dimmer" else "mdi:light-switch"
            })
        
        elif device_type == "bus_automation":
            self.logger.debug("Configuring automation device")
            suggested_config.update({
                "device_class": "shutter",
                "icon": "mdi:window-shutter",
                "shutter_run": 20  # Default run time in seconds
            })
        
        elif device_type == "bus_energy_meter":
            self.logger.debug("Configuring energy meter device")
            suggested_config.update({
                "device_class": "energy",
                "unit_of_measurement": "W",
                "icon": "mdi:flash",
                "refresh_period": 30
            })
        
        elif device_type in ["bus_thermo_zone", "bus_thermo_sensor"]:
            self.logger.debug("Configuring thermo device: %s", device_type)
            suggested_config.update({
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "icon": "mdi:thermometer",
                "standalone": device_type == "bus_thermo_sensor"
            })
        
        elif device_type in ["bus_cen_scenario_control", "bus_cenplus_scenario_control"]:
            self.logger.debug("Configuring scenario control device: %s", device_type)
            suggested_config.update({
                "device_class": "button",
                "icon": "mdi:gesture-tap-button",
                "buttons": "1,2,3,4"  # Default button configuration
            })
        
        elif device_type == "bus_dry_contact_ir":
            self.logger.debug("Configuring dry contact device")
            suggested_config.update({
                "device_class": "motion",
                "icon": "mdi:motion-sensor"
            })
        
        elif device_type == "bus_aux":
            self.logger.debug("Configuring auxiliary device")
            suggested_config.update({
                "device_class": "switch",
                "icon": "mdi:electric-switch"
            })
        
        elif device_type in ["bus_alarm_system", "bus_alarm_zone"]:
            self.logger.debug("Configuring alarm device: %s", device_type)
            suggested_config.update({
                "device_class": "safety",
                "icon": "mdi:shield-home"
            })
        
        else:
            self.logger.warning("Unknown device type %s, using basic configuration", device_type)
        
        self.logger.debug("Final suggested_config for %s: %s", device_type, suggested_config)
        return suggested_config


@callback
def async_setup_discovery(hass: HomeAssistant) -> None:
    """Setup discovery config flow following OpenHAB patterns."""
    discovery = MyHOMEDiscoveryConfigFlow(hass)
    
    # Store reference for cleanup
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["discovery"] = discovery