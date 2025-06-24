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
    OWNLightingCommand,
    OWNAutomationEvent,
    OWNAutomationCommand,
    OWNEnergyEvent,
    OWNHeatingEvent,
    OWNHeatingCommand,
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
            "OWNLightingCommand": self._determine_lighting_device_type,
            "OWNAutomationEvent": lambda msg: DEVICE_TYPE_BUS_AUTOMATION,
            "OWNAutomationCommand": lambda msg: DEVICE_TYPE_BUS_AUTOMATION,
            "OWNEnergyEvent": lambda msg: DEVICE_TYPE_BUS_ENERGY_METER,
            "OWNHeatingEvent": self._determine_thermo_device_type,
            "OWNHeatingCommand": self._determine_thermo_device_type,
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
        
        # Log discovery status
        self.logger.info("Discovery activated: %s", self._discovery_active)
        self.logger.info("Discovery timeout: %s seconds", self._discovery_timeout)
        
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
        self.logger.debug("Discovery message received: %s (type: %s, discovery_active: %s)", 
                         message, type(message).__name__, self._discovery_active)
        
        if not self._discovery_active:
            self.logger.debug("Discovery not active, ignoring message")
            return
        
        try:
            # Handle both event messages and status response messages
            device_info = self._extract_device_info(message)
            self.logger.debug("Extracted device info: %s", device_info)
            if device_info:
                device_id = device_info["unique_id"]
                if device_id not in self._discovered_devices:
                    self.logger.info("Discovered new device: %s (%s) at WHERE=%s", 
                                    device_info["name"], device_info["device_type"], device_info["where"])
                    self._discovered_devices[device_id] = device_info
                    
                    # Immediately create discovery result following OpenHAB pattern
                    self._create_discovery_result(device_info)
                else:
                    self.logger.debug("Device %s already discovered, skipping", device_id)
            else:
                # If we can't extract device info, log the message for debugging
                self.logger.debug("Could not extract device info from message: %s", message)
                # Try to handle as raw response string for discovery commands
                if hasattr(message, '__str__'):
                    message_str = str(message)
                    if message_str.startswith('*') and message_str.endswith('##'):
                        self.logger.debug("Processing message as potential command response: %s", message_str)
                        self.handle_command_response(message_str)
        
        except Exception as e:
            self.logger.error("Error handling discovery message %s: %s", message, e)
    
    def handle_command_response(self, response_string: str) -> None:
        """Handle command response strings for discovery."""
        if not self._discovery_active:
            return
            
        try:
            self.logger.debug("Processing command response for discovery: %s", response_string)
            
            # Parse the response string manually
            # Format: *WHO*WHAT*WHERE##
            if response_string.startswith('*') and response_string.endswith('##'):
                parts = response_string[1:-2].split('*')
                if len(parts) >= 3:
                    who, what, where = parts[0], parts[1], parts[2]
                    
                    # Create a synthetic device info based on the response
                    device_info = self._create_device_info_from_response(who, what, where)
                    if device_info:
                        device_id = device_info["unique_id"]
                        if device_id not in self._discovered_devices:
                            self.logger.debug("Discovered device from command response: %s", device_info["name"])
                            self._discovered_devices[device_id] = device_info
                            self._create_discovery_result(device_info)
                            
        except Exception as e:
            self.logger.error("Error processing command response %s: %s", response_string, e)
    
    def _create_device_info_from_response(self, who: str, what: str, where: str) -> Optional[Dict[str, Any]]:
        """Create device info from command response parts."""
        try:
            # Map WHO to device type and platform
            # For lighting (WHO=1), be conservative about dimmer detection
            # WHAT values for lighting:
            # 0 = OFF
            # 1 = ON
            # 2-10 = Potentially dimming levels (20%-100%)
            # 8 = Often indicates "temporized ON" or special state, not a dimming level
            # Note: Just because a device responds with a dimming WHAT value doesn't mean it's actually a dimmer
            # Some on/off switches may respond with these values. Default to on/off switch to be safe.
            is_dimmer = False  # Default to on/off switch for safer device identification
            
            who_to_device_type = {
                "1": ("bus_dimmer" if is_dimmer else "bus_on_off_switch", "light"),
                "2": ("bus_automation", "cover"),
                "4": ("bus_thermo_zone", "climate"),
                "18": ("bus_energy_meter", "sensor"),
                "9": ("bus_aux", "switch"),
                "25": ("bus_cen_scenario_control", "button"),
            }
            
            self.logger.debug("Device type detection for WHO=%s WHAT=%s WHERE=%s: is_dimmer=%s", 
                            who, what, where, is_dimmer)
            
            if who not in who_to_device_type:
                return None
                
            device_type, platform = who_to_device_type[who]
            
            # Create device info
            device_info = {
                "unique_id": f"{self.config_entry.data['mac']}-{where}",
                "name": f"MyHOME {device_type.replace('_', ' ').title()} {where}",
                "device_type": device_type,
                "where": where,
                "platform": platform,
                "category": self.device_factory.get_device_category(device_type),
                "properties": {
                    "ownId": f"{who}*{where}",
                    "where": where,
                    "discovered_at": datetime.now().isoformat(),
                    "response_who": who,
                    "response_what": what,
                }
            }
            
            return device_info
            
        except Exception as e:
            self.logger.error("Error creating device info from response WHO=%s WHAT=%s WHERE=%s: %s", who, what, where, e)
            return None
    
    def _extract_device_info(self, message: OWNMessage) -> Optional[Dict[str, Any]]:
        """Extract device information from message following OpenHAB patterns."""
        message_type = type(message).__name__
        self.logger.debug("Extracting device info from message type: %s", message_type)
        
        if message_type not in self._message_to_device_type:
            self.logger.debug("Message type %s not in supported types: %s", 
                            message_type, list(self._message_to_device_type.keys()))
            return None
        
        # Get device WHERE address - try multiple attributes
        where = None
        for attr in ['where', 'entity', 'object', 'address']:
            if hasattr(message, attr):
                where = getattr(message, attr, None)
                if where:
                    break
        
        self.logger.debug("Found WHERE address: %s from message: %s", where, message)
        if not where:
            self.logger.debug("No WHERE address found in message")
            return None
        
        # Convert WHERE to string and clean it up
        where = str(where)
        if where.startswith('#'):
            # Skip group addresses during discovery for now
            self.logger.debug("Skipping group address: %s", where)
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
                "message_str": str(message),
            }
        }
        
        # Add device-specific properties
        self._add_device_specific_properties(device_info, message)
        
        return device_info
    
    def _determine_lighting_device_type(self, message) -> str:
        """Determine lighting device type following OpenHAB patterns."""
        # Be conservative about dimmer detection - require explicit brightness information
        # Check if it's a dimmer based on actual brightness capabilities
        if hasattr(message, 'brightness') and message.brightness is not None and message.brightness > 0:
            # Only consider it a dimmer if it has actual brightness level (not just 0/1)
            return DEVICE_TYPE_BUS_DIMMER
        elif hasattr(message, 'brightness_preset') and message.brightness_preset:
            # Has brightness preset capability
            return DEVICE_TYPE_BUS_DIMMER
        else:
            # Default to on/off switch - user can manually configure as dimmer if needed
            return DEVICE_TYPE_BUS_ON_OFF_SWITCH
    
    def _determine_thermo_device_type(self, message) -> str:
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
            if hasattr(message, 'brightness') and message.brightness is not None and message.brightness > 0:
                properties["brightness"] = message.brightness
                properties["dimmable"] = True
                properties["detection_confidence"] = "high"
            elif hasattr(message, 'brightness_preset') and message.brightness_preset:
                properties["dimmable"] = True
                properties["detection_confidence"] = "medium"
            else:
                properties["dimmable"] = False
                properties["detection_confidence"] = "high"
                properties["note"] = "Detected as on/off switch. If this device supports dimming, manually configure dimmable: true"
                
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
            "*#18*0##",  # Request all energy management device status (WHO=18) - May not be supported by all gateways
            "*#25*0##",  # Request all CEN/dry contact device status (WHO=25)
            "*#9*0##",   # Request all auxiliary device status (WHO=9) - May not be supported by all gateways
        ]
        
        from OWNd.message import OWNCommand
        
        self.logger.info("Sending %d discovery commands...", len(discovery_commands))
        
        successful_commands = 0
        failed_commands = []
        
        for i, command in enumerate(discovery_commands, 1):
            try:
                if self._discovery_active:
                    self.logger.info("Sending discovery command %d/%d: %s", i, len(discovery_commands), command)
                    # Send command through gateway
                    own_command = OWNCommand.parse(command)
                    if own_command and own_command.is_valid:
                        await self.gateway_handler.send_status_request(own_command)
                        self.logger.debug("Command %s queued successfully", command)
                        successful_commands += 1
                    else:
                        self.logger.warning("Failed to parse command: %s", command)
                        failed_commands.append((command, "Invalid command format"))
                    # Small delay between commands
                    await asyncio.sleep(0.5)
                else:
                    self.logger.warning("Discovery deactivated during command sending")
                    break
            except Exception as e:
                self.logger.error("Error sending discovery command %s: %s", command, e)
                failed_commands.append((command, str(e)))
        
        self.logger.info("Discovery commands sent. Successful: %d, Failed: %d", 
                        successful_commands, len(failed_commands))
        
        if failed_commands:
            self.logger.warning("Failed commands (this is normal if gateway doesn't support these subsystems):")
            for cmd, error in failed_commands:
                who = cmd.split('*')[1] if '*' in cmd else '?'
                subsystem_name = {
                    "18": "Energy Management (WHO=18)",
                    "9": "Auxiliary (WHO=9)",
                    "25": "CEN/Dry Contact (WHO=25)"
                }.get(who, f"WHO={who}")
                self.logger.warning("  %s - %s (Command: %s)", subsystem_name, error, cmd)
        
        self.logger.info("Waiting for device responses...")
    
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