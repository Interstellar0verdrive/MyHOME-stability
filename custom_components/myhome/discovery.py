"""Device discovery service for the MyHOME integration.

The service listens to the traffic the gateway handler already receives, sends a
few general status requests and records every (WHO, WHERE) it sees. Devices that
are not in the validated configuration are turned into YAML suggestions written
to `myhome_discovered.yaml` (see config_flow_discovery.py). Public events
`myhome_device_discovered` / `myhome_discovery_completed` are kept for user
automations.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from OWNd.message import (
    OWNAutomationEvent,
    OWNCommand,
    OWNEnergyEvent,
    OWNHeatingEvent,
    OWNLightingEvent,
    OWNMessage,
)

from .config_flow_discovery import MyHOMEDiscoverySuggestions
from .const import (
    ALL_DEVICE_SUPPORTED_TYPES,
    DEVICE_TYPE_BUS_ALARM_ZONE,
    DEVICE_TYPE_BUS_AUTOMATION,
    DEVICE_TYPE_BUS_AUX,
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_DIMMER,
    DEVICE_TYPE_BUS_DRY_CONTACT_IR,
    DEVICE_TYPE_BUS_ENERGY_METER,
    DEVICE_TYPE_BUS_ON_OFF_SWITCH,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DEVICE_TYPE_GENERIC,
    DEVICE_TYPE_TO_PLATFORM,
    DOMAIN,
    LOGGER,
)

if TYPE_CHECKING:
    from .gateway import MyHOMEGatewayHandler

DISCOVERY_TIMEOUT_SEC = 60

# Cosmetic grouping of device types (was device_factory.get_device_category)
_DEVICE_CATEGORY: dict[str, str] = {
    DEVICE_TYPE_BUS_ON_OFF_SWITCH: "lighting",
    DEVICE_TYPE_BUS_DIMMER: "lighting",
    DEVICE_TYPE_BUS_AUTOMATION: "automation",
    DEVICE_TYPE_BUS_ENERGY_METER: "energy",
    DEVICE_TYPE_BUS_THERMO_ZONE: "thermoregulation",
    DEVICE_TYPE_BUS_THERMO_SENSOR: "thermoregulation",
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL: "scenario",
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL: "scenario",
    DEVICE_TYPE_BUS_DRY_CONTACT_IR: "scenario",
    DEVICE_TYPE_BUS_AUX: "auxiliary",
    DEVICE_TYPE_BUS_ALARM_ZONE: "alarm",
}

# General status requests sent when discovery starts.
_DISCOVERY_COMMANDS = (
    "*#1*0##",  # lighting
    "*#2*0##",  # automation
    "*#4*0##",  # thermoregulation
    "*#18*0##",  # energy management (not every gateway answers)
    "*#25*0##",  # CEN / dry contacts
    "*#9*0##",  # auxiliary (not every gateway answers)
)


class MyHOMEDeviceDiscoveryService:
    """Discovery service for one gateway (created by the gateway handler)."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, gateway_handler: MyHOMEGatewayHandler) -> None:
        self.hass = hass
        self.config_entry = config_entry
        self.gateway_handler = gateway_handler
        self.suggestions = MyHOMEDiscoverySuggestions(hass, config_entry)

        self._discovered_devices: dict[str, dict[str, Any]] = {}
        self._discovery_active = False
        self._discovery_timeout = DISCOVERY_TIMEOUT_SEC
        self._discovery_task: asyncio.Task | None = None
        self._timer_handle: asyncio.TimerHandle | None = None
        self._completion_task: asyncio.Task | None = None
        # Set by stop_discovery(); the worker waits on it instead of polling.
        self._stopped = asyncio.Event()

        self._message_to_device_type: dict[str, Callable[[OWNMessage], str]] = {
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

    @property
    def _mac(self) -> str:
        return self.config_entry.data["mac"]

    # ------------------------------------------------------------------ lifecycle
    async def start_discovery(self) -> None:
        """Start a discovery run (no-op when one is already active)."""
        if self._discovery_active:
            LOGGER.warning("%s Discovery already active", self.gateway_handler.log_id)
            return

        LOGGER.info("%s Starting device discovery (%ss)", self.gateway_handler.log_id, self._discovery_timeout)
        self._discovery_active = True
        self._stopped.clear()
        self._discovered_devices.clear()

        # Tracked task + tracked timer: both are cancelled by stop_discovery(),
        # which __init__.async_unload_entry awaits before closing the gateway.
        self._discovery_task = self.config_entry.async_create_background_task(
            self.hass, self._discovery_worker(), name="myhome_discovery_worker"
        )
        self._timer_handle = self.hass.loop.call_later(self._discovery_timeout, self._on_timeout)

    async def stop_discovery(self, reason: str = "stopped") -> None:
        """Stop discovery, cancel the worker/timer and flush the suggestions."""
        if not self._discovery_active:
            return
        LOGGER.info("%s Stopping device discovery (%s)", self.gateway_handler.log_id, reason)
        self._discovery_active = False
        self._stopped.set()

        if self._timer_handle is not None:
            self._timer_handle.cancel()
            self._timer_handle = None

        task, self._discovery_task = self._discovery_task, None
        if task is not None and not task.done() and task is not asyncio.current_task():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self.hass.bus.async_fire(
            f"{DOMAIN}_discovery_completed",
            {
                "gateway_mac": self._mac,
                "reason": reason,
                "discovered_count": len(self._discovered_devices),
                "discovered_devices": list(self._discovered_devices.keys()),
            },
        )
        LOGGER.info(
            "%s Discovery completed: %d device(s) seen", self.gateway_handler.log_id, len(self._discovered_devices)
        )
        await self.suggestions.async_flush()

    @callback
    def _on_timeout(self) -> None:
        """Timer callback: finish the run on the event loop."""
        self._timer_handle = None
        if not self._discovery_active:
            return
        self._completion_task = self.config_entry.async_create_task(
            self.hass, self.stop_discovery("timeout"), name="myhome_discovery_complete"
        )

    def is_discovery_active(self) -> bool:
        return self._discovery_active

    def get_discovered_devices(self) -> dict[str, dict[str, Any]]:
        return dict(self._discovered_devices)

    # ------------------------------------------------------------------ traffic hook
    def handle_discovery_message(self, message: OWNMessage) -> None:
        """Called by the gateway listening loop for every inbound message."""
        if not self._discovery_active:
            return
        try:
            device_info = self._extract_device_info(message)
        except Exception as err:  # noqa: BLE001 - never disturb the listening loop
            LOGGER.debug("%s Discovery could not classify `%s`: %s", self.gateway_handler.log_id, message, err)
            return
        if not device_info:
            return
        unique_id = device_info["unique_id"]
        if unique_id in self._discovered_devices:
            return
        self._discovered_devices[unique_id] = device_info
        LOGGER.info(
            "%s Discovered %s at WHO=%s WHERE=%s",
            self.gateway_handler.log_id,
            device_info["device_type"],
            device_info["who"],
            device_info["where"],
        )
        self._create_discovery_result(device_info)

    def _create_discovery_result(self, device_info: dict[str, Any]) -> None:
        """Queue the YAML suggestion and fire the public event."""
        self.suggestions.add(device_info)
        self.hass.bus.async_fire(
            f"{DOMAIN}_device_discovered",
            {
                "platform": device_info["platform"],
                "discovered_device": device_info,
                "config_entry_id": self.config_entry.entry_id,
                "gateway_mac": self._mac,
            },
        )

    # ------------------------------------------------------------------ classification
    def _extract_device_info(self, message: OWNMessage) -> dict[str, Any] | None:
        message_type = type(message).__name__
        if message_type not in self._message_to_device_type:
            return None

        where = None
        for attr in ("where", "entity", "object", "address"):
            value = getattr(message, attr, None)
            if value:
                where = value
                break
        if not where:
            return None
        where = str(where)
        if where.startswith("#"):
            # groups / general addresses are not devices
            return None

        device_type = self._message_to_device_type[message_type](message)
        if not device_type or device_type not in ALL_DEVICE_SUPPORTED_TYPES:
            device_type = DEVICE_TYPE_GENERIC

        who = str(getattr(message, "who", "") or "")
        device_info: dict[str, Any] = {
            # unique per gateway AND WHO (a light and a shutter may share a WHERE)
            "unique_id": f"{self._mac}-{who}-{where}",
            "name": f"MyHOME {device_type.replace('_', ' ').title()} {where}",
            "device_type": device_type,
            "who": who,
            "where": where,
            "platform": DEVICE_TYPE_TO_PLATFORM.get(device_type, "sensor"),
            "category": _DEVICE_CATEGORY.get(device_type, "generic"),
            "properties": {
                "ownId": f"{who}*{where}" if who else where,
                "where": where,
                "discovered_at": dt_util.utcnow().isoformat(),
                "message_type": message_type,
                "message_str": str(message),
            },
        }
        self._add_device_specific_properties(device_info, message)
        return device_info

    @staticmethod
    def _determine_lighting_device_type(message: OWNMessage) -> str:
        brightness = getattr(message, "brightness", None)
        if brightness is not None and brightness > 0:
            return DEVICE_TYPE_BUS_DIMMER
        if getattr(message, "brightness_preset", None):
            return DEVICE_TYPE_BUS_DIMMER
        return DEVICE_TYPE_BUS_ON_OFF_SWITCH

    @staticmethod
    def _determine_thermo_device_type(message: OWNMessage) -> str:
        if getattr(message, "temperature", None) is not None:
            return DEVICE_TYPE_BUS_THERMO_SENSOR
        return DEVICE_TYPE_BUS_THERMO_ZONE

    @staticmethod
    def _add_device_specific_properties(device_info: dict[str, Any], message: OWNMessage) -> None:
        properties = device_info["properties"]
        if isinstance(message, OWNLightingEvent):
            brightness = getattr(message, "brightness", None)
            if brightness is not None and brightness > 0:
                properties["brightness"] = brightness
                properties["dimmable"] = True
            elif getattr(message, "brightness_preset", None):
                properties["dimmable"] = True
            else:
                properties["dimmable"] = False
                properties["note"] = "Detected as on/off switch; set `dimmable: true` manually for dimmers"
        elif isinstance(message, OWNAutomationEvent):
            properties["shutter_type"] = "standard"
        elif isinstance(message, OWNEnergyEvent):
            properties["meter_type"] = "energy"
            if hasattr(message, "active_power"):
                properties["power"] = message.active_power
        elif isinstance(message, OWNHeatingEvent):
            properties["thermo_type"] = device_info["device_type"]
            if getattr(message, "temperature", None) is not None:
                properties["temperature"] = message.temperature

    # ------------------------------------------------------------------ worker
    async def _discovery_worker(self) -> None:
        try:
            await self._send_discovery_commands()
            if self._discovery_active:
                # Keep the task alive until stop_discovery() (timer or service).
                await self._stopped.wait()
        except asyncio.CancelledError:
            LOGGER.debug("%s Discovery worker cancelled", self.gateway_handler.log_id)
            raise
        except Exception as err:  # noqa: BLE001
            LOGGER.error("%s Discovery worker error: %s", self.gateway_handler.log_id, err)

    async def _send_discovery_commands(self) -> None:
        for command in _DISCOVERY_COMMANDS:
            if not self._discovery_active:
                return
            own_command = OWNCommand.parse(command)
            if own_command is None or not own_command.is_valid:
                LOGGER.debug("%s Discovery command `%s` not parsable", self.gateway_handler.log_id, command)
                continue
            LOGGER.debug("%s Discovery status request `%s`", self.gateway_handler.log_id, command)
            await self.gateway_handler.send_status_request(own_command)
            await asyncio.sleep(0.5)

    async def discover_device_by_address(self, where: str) -> dict[str, Any] | None:
        """Probe a single WHERE on the common subsystems and return what answered."""
        for who in (1, 2, 4, 18, 25, 9):
            own_command = OWNCommand.parse(f"*#{who}*{where}##")
            if own_command is not None and own_command.is_valid:
                await self.gateway_handler.send_status_request(own_command)
                await asyncio.sleep(0.2)
        for who in (1, 2, 4, 18, 25, 9):
            found = self._discovered_devices.get(f"{self._mac}-{who}-{where}")
            if found:
                return found
        return None
