"""Device discovery service for MyHOME integration following OpenHAB patterns."""

import asyncio
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr

from OWNd.message import (
    OWNMessage,
    OWNLightingEvent,
    OWNAutomationEvent,
    OWNEnergyEvent,
    OWNHeatingEvent,
    OWNDryContactEvent,
    OWNAuxEvent,
    OWNCENEvent,
    OWNCENPlusEvent,
    OWNAlarmEvent,
)

from .const import (
    DOMAIN,
    DEVICE_TYPE_BUS_ON_OFF_SWITCH,
    DEVICE_TYPE_BUS_DIMMER,
    DEVICE_TYPE_BUS_AUTOMATION,
    DEVICE_TYPE_BUS_ENERGY_METER,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_DRY_CONTACT_IR,
    DEVICE_TYPE_BUS_AUX,
    DEVICE_TYPE_BUS_ALARM_ZONE,
    DEVICE_TYPE_GENERIC,
    DEVICE_TYPE_TO_PLATFORM,
    ALL_DEVICE_SUPPORTED_TYPES,
)
from .device_factory import MyHOMEDeviceFactory


class MyHOMEDeviceDiscoveryService:
    """Discovery service for MyHOME devices following OpenHAB patterns."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, gateway_handler):
        """Initialize the discovery service."""
        self.hass = hass
        self.config_entry = config_entry
        self.gateway_handler = gateway_handler
        self.device_factory = MyHOMEDeviceFactory(hass, config_entry)
        self.logger = logging.getLogger(__name__)
        
        # Discovery state
        self._discovered_devices: Dict[str, Dict[str, Any]] = {}
        self._discovery_active = False
        self._discovery_timeout = 60  # seconds
        self._discovery_task: Optional[asyncio.Task] = None
        
        # Device type mapping from messages
        self._message_to_device_type = {
            # Map message types to device types following OpenHAB patterns
            "OWNLightingEvent": self._determine_lighting_device_type,
            "OWNAutomationEvent": lambda msg: DEVICE_TYPE_BUS_AUTOMATION,
            "OWNEnergyEvent": lambda msg: DEVICE_TYPE_BUS_ENERGY_METER,
            "OWNHeatingEvent": self._determine_thermo_device_type,
            "OWNDryContactEvent": lambda msg: DEVICE_TYPE_BUS_DRY_CONTACT_IR,
            "OWNAuxEvent": lambda msg: DEVICE_TYPE_BUS_AUX,
            "OWNCENEvent": lambda msg: DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
            "OWNCENPlusEvent": lambda msg: DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
            "OWNAlarmEvent": lambda msg: DEVICE_TYPE_BUS_ALARM_ZONE,
        }
    
    async def start_discovery(self) -> None:
        """Start device discovery process following OpenHAB patterns."""
        if self._discovery_active:
            self.logger.warning("Discovery already active")
            return
        
        self.logger.info("Starting MyHOME device discovery on gateway %s", 
                        self.gateway_handler.name)
        
        self._discovery_active = True
        self._discovered_devices.clear()
        
        # Start discovery task with timeout
        self._discovery_task = asyncio.create_task(self._discovery_worker())
        
        # Schedule discovery completion
        self.hass.loop.call_later(self._discovery_timeout, self._complete_discovery)
    
    async def stop_discovery(self) -> None:
        """Stop device discovery process."""
        if not self._discovery_active:
            return
        
        self.logger.info("Stopping MyHOME device discovery")
        self._discovery_active = False
        
        if self._discovery_task and not self._discovery_task.done():
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass
    
    def handle_discovery_message(self, message: OWNMessage) -> None:
        """Handle incoming messages for device discovery following OpenHAB patterns."""
        if not self._discovery_active:
            return
        
        try:
            device_info = self._extract_device_info(message)
            if device_info:
                device_id = device_info["unique_id"]
                if device_id not in self._discovered_devices:
                    self.logger.debug("Discovered new device: %s (%s)", 
                                    device_info["name"], device_info["device_type"])
                    self._discovered_devices[device_id] = device_info
                    
                    # Immediately create discovery result following OpenHAB pattern
                    self._create_discovery_result(device_info)
        
        except Exception as e:
            self.logger.error("Error handling discovery message %s: %s", message, e)
    
    def _extract_device_info(self, message: OWNMessage) -> Optional[Dict[str, Any]]:
        """Extract device information from message following OpenHAB patterns."""
        message_type = type(message).__name__
        
        if message_type not in self._message_to_device_type:
            return None
        
        # Get device WHERE address
        where = getattr(message, 'where', None) or getattr(message, 'entity', None)
        if not where:
            return None
        
        # Determine device type using OpenHAB-style mapping
        device_type_func = self._message_to_device_type[message_type]
        device_type = device_type_func(message)
        
        if not device_type or device_type not in ALL_DEVICE_SUPPORTED_TYPES:
            device_type = DEVICE_TYPE_GENERIC
        
        # Create device info following OpenHAB patterns
        device_info = {
            "unique_id": f"{self.config_entry.data['mac']}-{where}",
            "name": f"MyHOME {device_type.replace('_', ' ').title()} {where}",
            "device_type": device_type,
            "where": where,
            "platform": DEVICE_TYPE_TO_PLATFORM.get(device_type, "sensor"),
            "category": self.device_factory.get_device_category(device_type),
            "properties": {
                "ownId": f"{message.who}*{where}" if hasattr(message, 'who') else where,
                "where": where,
                "discovered_at": datetime.now().isoformat(),
                "message_type": message_type,
            }
        }
        
        # Add device-specific properties
        self._add_device_specific_properties(device_info, message)
        
        return device_info
    
    def _determine_lighting_device_type(self, message: OWNLightingEvent) -> str:
        """Determine lighting device type following OpenHAB patterns."""
        # Check if it's a dimmer based on brightness information
        if hasattr(message, 'brightness') and message.brightness is not None:
            return DEVICE_TYPE_BUS_DIMMER
        elif hasattr(message, 'brightness_preset') and message.brightness_preset:
            return DEVICE_TYPE_BUS_DIMMER
        else:
            return DEVICE_TYPE_BUS_ON_OFF_SWITCH
    
    def _determine_thermo_device_type(self, message: OWNHeatingEvent) -> str:
        """Determine thermoregulation device type following OpenHAB patterns."""
        # Check message properties to determine if it's a zone or sensor
        if hasattr(message, 'temperature') and message.temperature is not None:
            return DEVICE_TYPE_BUS_THERMO_SENSOR
        else:
            return DEVICE_TYPE_BUS_THERMO_ZONE
    
    def _add_device_specific_properties(self, device_info: Dict[str, Any], message: OWNMessage) -> None:
        """Add device-specific properties following OpenHAB patterns."""
        properties = device_info["properties"]
        
        # Add message-specific properties
        if isinstance(message, OWNLightingEvent):
            if hasattr(message, 'brightness') and message.brightness is not None:
                properties["brightness"] = message.brightness
                properties["dimmable"] = True
            else:
                properties["dimmable"] = False
                
        elif isinstance(message, OWNAutomationEvent):
            properties["shutter_type"] = "standard"
            if hasattr(message, 'run_time'):
                properties["run_time"] = message.run_time
                
        elif isinstance(message, OWNEnergyEvent):
            properties["meter_type"] = "energy"
            if hasattr(message, 'power'):
                properties["power"] = message.power
                
        elif isinstance(message, OWNHeatingEvent):
            properties["thermo_type"] = device_info["device_type"]
            if hasattr(message, 'temperature'):
                properties["temperature"] = message.temperature
    
    def _create_discovery_result(self, device_info: Dict[str, Any]) -> None:
        """Create Home Assistant discovery result following OpenHAB patterns."""
        try:
            # Fire discovery event for Home Assistant
            discovery_data = {
                "platform": device_info["platform"],
                "discovered_device": device_info,
                "config_entry_id": self.config_entry.entry_id,
                "gateway_mac": self.config_entry.data["mac"],
            }
            
            self.hass.bus.async_fire(
                f"{DOMAIN}_device_discovered",
                discovery_data
            )
            
            self.logger.info(
                "Created discovery result for %s device %s at WHERE=%s",
                device_info["device_type"],
                device_info["name"],
                device_info["where"]
            )
        
        except Exception as e:
            self.logger.error("Error creating discovery result for %s: %s", 
                            device_info["unique_id"], e)
    
    async def _discovery_worker(self) -> None:
        """Worker task for active device discovery following OpenHAB patterns."""
        try:
            self.logger.debug("Discovery worker started")
            
            # Send discovery commands following OpenHAB patterns
            await self._send_discovery_commands()
            
            # Wait for discovery completion
            while self._discovery_active:
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            self.logger.debug("Discovery worker cancelled")
        except Exception as e:
            self.logger.error("Error in discovery worker: %s", e)
    
    async def _send_discovery_commands(self) -> None:
        """Send discovery commands to detect devices following OpenHAB patterns."""
        # Send status requests for common device types
        discovery_commands = [
            "*#1*0##",   # Request all lighting device status (WHO=1)
            "*#2*0##",   # Request all automation device status (WHO=2)
            "*#4*0##",   # Request all thermoregulation device status (WHO=4)
            "*#18*0##",  # Request all energy management device status (WHO=18)
            "*#25*0##",  # Request all CEN/dry contact device status (WHO=25)
            "*#9*0##",   # Request all auxiliary device status (WHO=9)
        ]
        
        from OWNd.message import OWNCommand
        
        for command in discovery_commands:
            try:
                if self._discovery_active:
                    self.logger.debug("Sending discovery command: %s", command)
                    # Send command through gateway
                    own_command = OWNCommand.parse(command)
                    if own_command and own_command.is_valid:
                        await self.gateway_handler.send_status_request(own_command)
                    # Small delay between commands
                    await asyncio.sleep(0.5)
            except Exception as e:
                self.logger.error("Error sending discovery command %s: %s", command, e)
    
    @callback
    def _complete_discovery(self) -> None:
        """Complete the discovery process."""
        if not self._discovery_active:
            return
        
        self.logger.info(
            "Discovery completed. Found %d devices", 
            len(self._discovered_devices)
        )
        
        # Fire discovery completion event
        self.hass.bus.async_fire(f"{DOMAIN}_discovery_completed", {
            "gateway_mac": self.config_entry.data["mac"],
            "discovered_count": len(self._discovered_devices),
            "discovered_devices": list(self._discovered_devices.keys())
        })
        
        # Stop discovery
        asyncio.create_task(self.stop_discovery())
    
    def get_discovered_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get all discovered devices following OpenHAB patterns."""
        return self._discovered_devices.copy()
    
    def is_discovery_active(self) -> bool:
        """Check if discovery is currently active."""
        return self._discovery_active
    
    async def discover_device_by_address(
        self, where: str
    ) -> Optional[Dict[str, Any]]:
        """Discover a specific device by WHERE address following OpenHAB patterns."""
        try:
            from OWNd.message import OWNCommand
            
            # Try different WHO types for the address
            # lighting, automation, thermo, energy, CEN, aux
            who_types = [1, 2, 4, 18, 25, 9]
            
            for who in who_types:
                command = f"*#{who}*{where}##"
                self.logger.debug(
                    "Discovering device at WHERE=%s with WHO=%s", where, who
                )
                
                own_command = OWNCommand.parse(command)
                if own_command and own_command.is_valid:
                    await self.gateway_handler.send_status_request(own_command)
                    await asyncio.sleep(0.2)
            
            # Check if device was discovered
            device_id = f"{self.config_entry.data['mac']}-{where}"
            return self._discovered_devices.get(device_id)
            
        except Exception as e:
            self.logger.error("Error discovering device at WHERE=%s: %s", where, e)
            return None