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
    MESSAGE_TYPE_MAIN_TEMPERATURE,
    MESSAGE_TYPE_SECONDARY_TEMPERATURE,
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
    CONF_BUS_INTERFACE,
    CONF_WHERE,
    CONF_WHO,
    DEVICE_TYPE_BUS_ALARM_ZONE,
    DEVICE_TYPE_BUS_AUTOMATION,
    DEVICE_TYPE_BUS_AUX,
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_DIMMER,
    DEVICE_TYPE_BUS_DRY_CONTACT_IR,
    DEVICE_TYPE_BUS_ENERGY_METER,
    DEVICE_TYPE_BUS_ON_OFF_SWITCH,
    DEVICE_TYPE_BUS_THERMO_CU,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DEVICE_TYPE_GENERIC,
    DEVICE_TYPE_TO_PLATFORM,
    DOMAIN,
    LOGGER,
    bus_full_where,
    is_bus_scope_address,
    normalise_bus_interface,
)
from .validate import device_key

if TYPE_CHECKING:
    from .gateway import MyHOMEGatewayHandler

DISCOVERY_TIMEOUT_SEC = 60

# How the thermoregulation central unit is addressed everywhere else in the
# integration: ``gateway.py._message_entity_key`` keys its frames as ``4-#0``,
# ``validate.Zone`` accepts ``#0`` (and refuses a bare ``0``) and ``climate.py``
# builds a real entity for it.  Discovery uses the same spelling so the suggestion
# it writes is YAML the schema loads.
CENTRAL_UNIT_ZONE = "#0"

# Cosmetic grouping of device types (was device_factory.get_device_category)
_DEVICE_CATEGORY: dict[str, str] = {
    DEVICE_TYPE_BUS_ON_OFF_SWITCH: "lighting",
    DEVICE_TYPE_BUS_DIMMER: "lighting",
    DEVICE_TYPE_BUS_AUTOMATION: "automation",
    DEVICE_TYPE_BUS_ENERGY_METER: "energy",
    DEVICE_TYPE_BUS_THERMO_ZONE: "thermoregulation",
    DEVICE_TYPE_BUS_THERMO_SENSOR: "thermoregulation",
    DEVICE_TYPE_BUS_THERMO_CU: "thermoregulation",
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
    "*#9*0##",  # auxiliary (not every gateway answers)
    # No WHO 25 entry on purpose. There is no general status request for dry
    # contacts (OWNd refuses to build `*#25*0##`, and the bus has no such frame), and
    # CEN / CEN+ keypads never answer a status request at all: both kinds of device
    # are discovered only from the frames they emit during the run.
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
        # A run reports what *this* run saw: the suggestion collector outlives the run
        # (it is created once per config entry), so it is cleared alongside.
        self.suggestions.reset()

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
            try:  # noqa: SIM105 - awaiting a cancelled task reads better than suppress()
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
            # The address as the bus writes it: without the interface, the main-bus
            # actuator 11 and the one on the riser produce the same line twice.
            bus_full_where(device_info["where"], device_info["interface"]),
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

        if is_bus_scope_address(message):
            # A general (``0``), area (``00``, ``1``-``9``, ``100``) or group
            # (``#N``) WHERE on WHO 1 / WHO 2.  The gateway intercepts these frames a
            # few lines further down its own dispatcher and never gives them to an
            # entity, so announcing them here would offer the user a block that
            # commands the whole plant (or a whole area) and can never show a state
            # -- and ``where: '100'`` is not even YAML the schema loads, because the
            # bus spells area 10 with three digits and the schema with two.  One
            # predicate for both decisions: see ``const.is_bus_scope_address``.
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
            # What is left of the ``#`` addresses once ``is_bus_scope_address`` above
            # has taken the WHO 1 / WHO 2 groups: the ``*5*<what>*#<zone>##`` frames
            # of a burglar alarm, where ``#N`` is zone N and not a group -- dropped
            # deliberately, because an alarm zone has no entity and no
            # ``myhome.yaml`` section, so announcing it would only grow the
            # "must be declared by hand" count with something that cannot be declared
            # at all.  A real alarm *sensor* frame (``*5*<what>*<zone><sensor>##``,
            # e.g. ``*5*11*12##`` = sensor 2 of zone 1) carries a plain WHERE, gets
            # through, and is what makes ``platform: null`` a value the public
            # discovery event really publishes.
            return None

        device_type = self._message_to_device_type[message_type](message)
        if not device_type or device_type not in ALL_DEVICE_SUPPORTED_TYPES:
            device_type = DEVICE_TYPE_GENERIC

        # The F422 local bus interface lives in ``message.interface``, never in
        # ``message.where``: OWNd 0.7.49 parses ``*1*1*11#4#3##`` as ``where == '11'``
        # with ``interface == '3'`` (and keeps the pair in ``entity``, ``1-11#4#3``).
        # Reading ``where`` alone made a lamp on a private riser look like the
        # main-bus lamp with the same address, which is a different physical device:
        # the pasted block drove the wrong actuator, the entity never updated (the
        # gateway dispatches these frames by ``1-11#4#03``, never by ``1-11``), and
        # the two shared one unique id, so whichever answered second was silently
        # never announced at all.  ``normalise_bus_interface`` unpads it, because the
        # bus sends ``#4#3`` and ``#4#03`` for the same interface.
        raw_interface = getattr(message, "interface", None)
        interface = normalise_bus_interface(raw_interface)
        if raw_interface and interface is None:
            # The frame carries an interface this integration cannot use (an F422 local
            # bus is a 0-15 field, so ``#4#16`` should not exist on real hardware).
            # ``None`` here would mean "on the main bus", and the device would be
            # announced and suggested as the main-bus device of the same address --
            # which is the very defect reading the interface was added to fix.
            # ``validate.BusInterface`` refuses such a value outright, so discovery
            # refuses the frame rather than inventing an identity for it.
            LOGGER.debug(
                "%s Discovery ignoring `%s`: bus interface %r is not usable (expected 0-15)",
                self.gateway_handler.log_id,
                message,
                raw_interface,
            )
            return None

        if device_type == DEVICE_TYPE_BUS_THERMO_CU:
            # The central unit is addressed ``#0``, never ``0`` (see
            # _determine_thermo_device_type): re-spell the WHERE before it reaches the
            # unique id, the properties and the YAML suggestion, so the key matches the
            # ``4-#0`` key gateway.py and validate.py use for the same device.
            where = CENTRAL_UNIT_ZONE
            # The generic formula would produce "MyHOME Bus Thermo Cu #0", and this
            # name is copied verbatim into the user's myhome.yaml.
            name = "MyHOME Thermoregulation Central Unit"
        else:
            # ``11#4#3`` in the name, so the two devices are told apart in the file
            # the user reads and in the "Discovered ..." log line.
            name = f"MyHOME {device_type.replace('_', ' ').title()} {bus_full_where(where, interface)}"

        who = str(getattr(message, "who", "") or "")
        # ``validate.device_key`` is the one definition of a device's identity, and
        # this id is ``{mac}-{device_key}`` -- the same string as the device registry
        # identifier and the tail of every entity ``unique_id``, interface zero
        # padded and all.  Building it here by hand is how the spellings drift.
        key = device_key({CONF_WHO: who, CONF_WHERE: where, CONF_BUS_INTERFACE: interface})
        device_info: dict[str, Any] = {
            # unique per gateway AND WHO (a light and a shutter may share a WHERE)
            "unique_id": f"{self._mac}-{key}",
            "name": name,
            "device_type": device_type,
            "who": who,
            "where": where,
            # Unpadded, as ``myhome.yaml`` spells it; ``None`` for a device on the
            # main bus.  Published in ``myhome_device_discovered`` too.
            "interface": interface,
            # Published verbatim (``None`` included): the table is exhaustive over
            # ALL_DEVICE_SUPPORTED_TYPES, and inventing a fallback section here is
            # exactly what made an alarm device look like a ``binary_sensor``.
            "platform": DEVICE_TYPE_TO_PLATFORM.get(device_type),
            "category": _DEVICE_CATEGORY.get(device_type, "generic"),
            "properties": {
                # The address as it appears on the bus, interface included.
                "ownId": f"{who}*{bus_full_where(where, interface)}" if who else where,
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
        """Tell the central unit, a standalone temperature probe and a zone apart.

        A WHO 4 frame whose WHERE is ``0`` is the **central unit**, not zone 0: a
        plant-wide mode change (``*4*1*0##``), the plant temperature
        (``*#4*0*0*0235##``) and the CU's own actuator status (``*#4*0#1*20*1##``)
        all report ``where == '0'`` on OWNd 0.7.49, and ``gateway.py``'s
        ``_message_entity_key`` already keys them as ``4-#0``.  Calling that a zone
        produced a ``climate: {zone: '0'}`` suggestion, and ``validate.Zone`` accepts
        ``#0``, ``1``-``99`` and ``#0#<zone>`` but never ``0`` -- so pasting it did
        not break one device, it made the whole ``myhome.yaml`` fail to load and every
        other device of that gateway disappear.  ``#0`` is a device the integration
        really builds (``climate.py`` models the central unit, AUTO included), so it
        is classified and suggested rather than dropped.

        OWNd 0.7.49 also makes the probe/zone distinction, in the WHERE and not in the
        payload (``OWNd/message.py``, ``OWNHeatingEvent.__init__``): a WHERE of 99 or
        less is a plain zone number, the reading lands in ``main_temperature`` and the
        message type is ``MESSAGE_TYPE_MAIN_TEMPERATURE``; a WHERE above 99 is
        ``<sensor digit><zone>``, the reading lands in ``secondary_temperature`` and
        the type is ``MESSAGE_TYPE_SECONDARY_TEMPERATURE``.  So *only* the secondary
        type identifies a probe that is not the zone itself: a main-temperature frame
        is **the zone** reporting its own sensor and must keep its ``climate:``
        suggestion, or the user is told to write a read-only ``sensor:`` block and
        loses the thermostat for that room.

        Two things this classifier deliberately does not attempt:

        - it never looks at ``mode``.  ``OWNMessage`` fills ``_what`` *or*
          ``_dimension``, never both, so a temperature frame cannot carry a mode; and
          since ``handle_discovery_message`` keeps the first classification for a
          given unique id -- a zone's mode frame and its temperature frame share one,
          and a zone broadcasts its temperature far more often than it changes mode --
          the answer has to be right from a single frame anyway.
        - a probe wired as the *main* sensor of a zone is indistinguishable from that
          zone on the bus.  Such a device is reported as a zone, which is the safer
          default: a ``climate:`` block nobody needs is one line to delete, a missing
          one costs a thermostat.  ``validate.py`` also tolerates a climate zone and a
          WHO 4 temperature sensor on the same zone, so both can be kept.
        """
        if str(getattr(message, "where", "") or "") == "0":
            return DEVICE_TYPE_BUS_THERMO_CU
        # ``OWNHeatingCommand`` has no ``message_type`` at all, hence the getattr.
        if getattr(message, "message_type", None) == MESSAGE_TYPE_SECONDARY_TEMPERATURE:
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
            # Same OWNd 0.7.49 API as sensor.py: the reading is in main_temperature or
            # in secondary_temperature[1], never in a ``temperature`` attribute.
            if message.message_type == MESSAGE_TYPE_MAIN_TEMPERATURE:
                properties["temperature"] = message.main_temperature
            elif message.message_type == MESSAGE_TYPE_SECONDARY_TEMPERATURE:
                properties["temperature"] = message.secondary_temperature[1]

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

