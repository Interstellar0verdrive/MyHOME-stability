"""Code to handle a MyHome Gateway."""
import asyncio
from typing import Dict, List, Optional, Any

from homeassistant.const import (
    CONF_ENTITIES,
    CONF_HOST,
    CONF_PORT,
    CONF_PASSWORD,
    CONF_NAME,
    CONF_MAC,
    CONF_FRIENDLY_NAME,
)
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.switch import (
    SwitchDeviceClass,
    DOMAIN as SWITCH,
)
from homeassistant.components.button import DOMAIN as BUTTON
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    DOMAIN as BINARY_SENSOR,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    DOMAIN as SENSOR,
)
from homeassistant.components.climate import DOMAIN as CLIMATE

from OWNd.connection import OWNSession, OWNEventSession, OWNCommandSession, OWNGateway
from OWNd.message import (
    OWNMessage,
    OWNLightingEvent,
    OWNLightingCommand,
    OWNEnergyEvent,
    OWNAutomationEvent,
    OWNDryContactEvent,
    OWNAuxEvent,
    OWNHeatingEvent,
    OWNHeatingCommand,
    OWNCENPlusEvent,
    OWNCENEvent,
    OWNGatewayEvent,
    OWNGatewayCommand,
    OWNCommand,
)

from .const import (
    CONF_PLATFORMS,
    CONF_FIRMWARE,
    CONF_SSDP_LOCATION,
    CONF_SSDP_ST,
    CONF_DEVICE_TYPE,
    CONF_MANUFACTURER,
    CONF_MANUFACTURER_URL,
    CONF_UDN,
    CONF_SHORT_PRESS,
    CONF_SHORT_RELEASE,
    CONF_LONG_PRESS,
    CONF_LONG_RELEASE,
    DOMAIN,
    LOGGER,
    THING_STATE_REQ_TIMEOUT_SEC,
    ALL_DEVICE_SUPPORTED_TYPES,
    DEVICE_TYPE_TO_PLATFORM,
)
from .myhome_device import MyHOMEEntity
from .button import (
    DisableCommandButtonEntity,
    EnableCommandButtonEntity,
)
from .device_factory import MyHOMEDeviceFactory


class MyHOMEGatewayHandler:
    """Manages a single MyHOME Gateway."""

    def __init__(self, hass, config_entry, generate_events=False):
        build_info = {
            "address": config_entry.data[CONF_HOST],
            "port": config_entry.data[CONF_PORT],
            "password": config_entry.data[CONF_PASSWORD],
            "ssdp_location": config_entry.data[CONF_SSDP_LOCATION],
            "ssdp_st": config_entry.data[CONF_SSDP_ST],
            "deviceType": config_entry.data[CONF_DEVICE_TYPE],
            "friendlyName": config_entry.data[CONF_FRIENDLY_NAME],
            "manufacturer": config_entry.data[CONF_MANUFACTURER],
            "manufacturerURL": config_entry.data[CONF_MANUFACTURER_URL],
            "modelName": config_entry.data[CONF_NAME],
            "modelNumber": config_entry.data[CONF_FIRMWARE],
            "serialNumber": config_entry.data[CONF_MAC],
            "UDN": config_entry.data[CONF_UDN],
        }
        self.hass = hass
        self.config_entry = config_entry
        self.generate_events = generate_events
        self.gateway = OWNGateway(build_info)
        self._terminate_listener = False
        self._terminate_sender = False
        self.is_connected = False
        self.listening_worker: asyncio.tasks.Task = None
        self.sending_workers: List[asyncio.tasks.Task] = []
        self.send_buffer = asyncio.Queue()
        
        # Initialize device factory following OpenHAB pattern
        self.device_factory = MyHOMEDeviceFactory(hass, config_entry)
        
        # Initialize discovery service following OpenHAB pattern
        self.discovery_service = None

    @property
    def mac(self) -> str:
        return self.gateway.serial

    @property
    def unique_id(self) -> str:
        return self.mac

    @property
    def log_id(self) -> str:
        return self.gateway.log_id

    @property
    def manufacturer(self) -> str:
        return self.gateway.manufacturer

    @property
    def name(self) -> str:
        return f"{self.gateway.model_name} Gateway"

    @property
    def model(self) -> str:
        return self.gateway.model_name

    @property
    def firmware(self) -> str:
        return self.gateway.firmware

    async def test(self) -> Dict:
        return await OWNSession(gateway=self.gateway, logger=LOGGER).test_connection()
    
    def supports_device_type(self, device_type: str) -> bool:
        """Check if device type is supported by this gateway."""
        return self.device_factory.supports_device_type(device_type)
    
    def get_device_category(self, device_type: str) -> str:
        """Get device category following OpenHAB patterns."""
        return self.device_factory.get_device_category(device_type)
    
    def organize_devices_by_category(self, devices_config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Organize devices by category following OpenHAB patterns."""
        return self.device_factory.organize_devices_by_category(devices_config)
    
    def validate_device_config(self, device_type: str, device_config: Dict[str, Any]) -> bool:
        """Validate device configuration."""
        return self.device_factory.validate_device_config(device_type, device_config)
    
    def initialize_discovery_service(self):
        """Initialize the discovery service following OpenHAB patterns."""
        if self.discovery_service is None:
            from .discovery import MyHOMEDeviceDiscoveryService
            self.discovery_service = MyHOMEDeviceDiscoveryService(
                self.hass, self.config_entry, self
            )
            LOGGER.debug("%s Discovery service initialized", self.log_id)
    
    async def start_device_discovery(self) -> None:
        """Start device discovery following OpenHAB patterns."""
        if self.discovery_service:
            await self.discovery_service.start_discovery()
        else:
            LOGGER.warning("%s Discovery service not initialized", self.log_id)
    
    async def stop_device_discovery(self) -> None:
        """Stop device discovery following OpenHAB patterns."""
        if self.discovery_service:
            await self.discovery_service.stop_discovery()
    
    def handle_discovery_message(self, message) -> None:
        """Handle message for discovery following OpenHAB patterns."""
        if self.discovery_service:
            self.discovery_service.handle_discovery_message(message)

    async def listening_loop(self):
        """Listen for gateway events and dispatch them to entities.

        This loop is designed to be resilient: the gateway can half-open/reset sockets.
        We use a timeout to avoid hanging forever on awaits, and we reconnect with
        exponential backoff on errors.

        Note: `self.is_connected` reflects the *event session* connectivity.
        """
        self._terminate_listener = False

        LOGGER.debug("%s Creating listening worker.", self.log_id)
        LOGGER.info("%s Listening loop started.", self.log_id)

        backoff = 1
        max_backoff = 60
        _event_session: Optional[OWNEventSession] = None

        while not self._terminate_listener:
            try:
                if _event_session is None:
                    _event_session = OWNEventSession(gateway=self.gateway, logger=LOGGER)
                    await _event_session.connect()
                    self.is_connected = True
                    backoff = 1
                    LOGGER.info("%s Event session established successfully.", self.log_id)

                # Avoid an infinite await when the gateway resets / half-opens the socket.
                # We wake up periodically to check termination flags and to allow reconnect logic.
                try:
                    message = await asyncio.wait_for(_event_session.get_next(), timeout=30)
                except asyncio.TimeoutError:
                    LOGGER.debug(
                        "%s Listening loop timeout waiting for events (30s).",
                        self.log_id,
                    )
                    continue

                LOGGER.debug("%s Message received: `%s`", self.log_id, message)

                if self.generate_events:
                    if isinstance(message, OWNMessage):
                        _event_content = {"gateway": str(self.gateway.host)}
                        _event_content.update(message.event_content)
                        self.hass.bus.async_fire("myhome_message_event", _event_content)
                    else:
                        self.hass.bus.async_fire(
                            "myhome_message_event",
                            {"gateway": str(self.gateway.host), "message": str(message)},
                        )

                if not isinstance(message, OWNMessage):
                    LOGGER.warning(
                        "%s Data received is not a message: `%s`",
                        self.log_id,
                        message,
                    )
                    continue

                # Handle message for discovery following OpenHAB patterns
                self.handle_discovery_message(message)

                # Continue with existing message processing
                if isinstance(message, OWNEnergyEvent):
                    if (
                        SENSOR in self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS]
                        and message.entity
                        in self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][SENSOR]
                    ):
                        for _entity in self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][SENSOR][
                            message.entity
                        ][CONF_ENTITIES]:
                            if isinstance(
                                self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][SENSOR][
                                    message.entity
                                ][CONF_ENTITIES][_entity],
                                MyHOMEEntity,
                            ):
                                self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][SENSOR][
                                    message.entity
                                ][CONF_ENTITIES][_entity].handle_event(message)
                    continue

                if (
                    isinstance(message, OWNLightingEvent)
                    or isinstance(message, OWNAutomationEvent)
                    or isinstance(message, OWNDryContactEvent)
                    or isinstance(message, OWNAuxEvent)
                    or isinstance(message, OWNHeatingEvent)
                ):
                    if message.is_translation:
                        LOGGER.debug(
                            "%s Ignoring translation message `%s`",
                            self.log_id,
                            message,
                        )
                        continue

                    is_event = False

                    if isinstance(message, OWNLightingEvent):
                        if message.is_general:
                            is_event = True
                            event = "on" if message.is_on else "off"
                            self.hass.bus.async_fire(
                                "myhome_general_light_event",
                                {"message": str(message), "event": event},
                            )
                            await asyncio.sleep(0.1)
                            await self.send_status_request(OWNLightingCommand.status("0"))
                        elif message.is_area:
                            is_event = True
                            event = "on" if message.is_on else "off"
                            self.hass.bus.async_fire(
                                "myhome_area_light_event",
                                {"message": str(message), "area": message.area, "event": event},
                            )
                            await asyncio.sleep(0.1)
                            await self.send_status_request(
                                OWNLightingCommand.status(message.area)
                            )
                        elif message.is_group:
                            is_event = True
                            event = "on" if message.is_on else "off"
                            self.hass.bus.async_fire(
                                "myhome_group_light_event",
                                {"message": str(message), "group": message.group, "event": event},
                            )

                    elif isinstance(message, OWNAutomationEvent):
                        if message.is_general:
                            is_event = True
                            if message.is_opening and not message.is_closing:
                                event = "open"
                            elif message.is_closing and not message.is_opening:
                                event = "close"
                            else:
                                event = "stop"
                            self.hass.bus.async_fire(
                                "myhome_general_automation_event",
                                {"message": str(message), "event": event},
                            )
                        elif message.is_area:
                            is_event = True
                            if message.is_opening and not message.is_closing:
                                event = "open"
                            elif message.is_closing and not message.is_opening:
                                event = "close"
                            else:
                                event = "stop"
                            self.hass.bus.async_fire(
                                "myhome_area_automation_event",
                                {"message": str(message), "area": message.area, "event": event},
                            )
                        elif message.is_group:
                            is_event = True
                            if message.is_opening and not message.is_closing:
                                event = "open"
                            elif message.is_closing and not message.is_opening:
                                event = "close"
                            else:
                                event = "stop"
                            self.hass.bus.async_fire(
                                "myhome_group_automation_event",
                                {"message": str(message), "group": message.group, "event": event},
                            )

                    if not is_event:
                        if isinstance(message, OWNLightingEvent) and message.brightness_preset:
                            if isinstance(
                                self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][LIGHT][
                                    message.entity
                                ][CONF_ENTITIES][LIGHT],
                                MyHOMEEntity,
                            ):
                                await self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][LIGHT][
                                    message.entity
                                ][CONF_ENTITIES][LIGHT].async_update()
                        else:
                            for _platform in self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS]:
                                if (
                                    _platform != BUTTON
                                    and message.entity
                                    in self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][_platform]
                                ):
                                    for _entity in self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][
                                        _platform
                                    ][message.entity][CONF_ENTITIES]:
                                        _obj = self.hass.data[DOMAIN][self.mac][CONF_PLATFORMS][
                                            _platform
                                        ][message.entity][CONF_ENTITIES][_entity]
                                        if (
                                            isinstance(_obj, MyHOMEEntity)
                                            and not isinstance(_obj, DisableCommandButtonEntity)
                                            and not isinstance(_obj, EnableCommandButtonEntity)
                                        ):
                                            _obj.handle_event(message)
                    continue

                if (
                    isinstance(message, OWNHeatingCommand)
                    and message.dimension is not None
                    and message.dimension == 14
                ):
                    where = message.where[1:] if message.where.startswith("#") else message.where
                    LOGGER.debug(
                        "%s Received heating command, sending query to zone %s",
                        self.log_id,
                        where,
                    )
                    await self.send_status_request(OWNHeatingCommand.status(where))
                    continue

                if isinstance(message, OWNCENPlusEvent):
                    if message.is_short_pressed:
                        event = CONF_SHORT_PRESS
                    elif message.is_held or message.is_still_held:
                        event = CONF_LONG_PRESS
                    elif message.is_released:
                        event = CONF_LONG_RELEASE
                    else:
                        event = None
                    self.hass.bus.async_fire(
                        "myhome_cenplus_event",
                        {"object": int(message.object), "pushbutton": int(message.push_button), "event": event},
                    )
                    LOGGER.info("%s %s", self.log_id, message.human_readable_log)
                    continue

                if isinstance(message, OWNCENEvent):
                    if message.is_pressed:
                        event = CONF_SHORT_PRESS
                    elif message.is_released_after_short_press:
                        event = CONF_SHORT_RELEASE
                    elif message.is_held:
                        event = CONF_LONG_PRESS
                    elif message.is_released_after_long_press:
                        event = CONF_LONG_RELEASE
                    else:
                        event = None
                    self.hass.bus.async_fire(
                        "myhome_cen_event",
                        {"object": int(message.object), "pushbutton": int(message.push_button), "event": event},
                    )
                    LOGGER.info("%s %s", self.log_id, message.human_readable_log)
                    continue

                if isinstance(message, OWNGatewayEvent) or isinstance(message, OWNGatewayCommand):
                    LOGGER.info("%s %s", self.log_id, message.human_readable_log)
                    continue

                LOGGER.info("%s Unsupported message type: `%s`", self.log_id, message)

            except asyncio.CancelledError:
                break
            except Exception as err:
                LOGGER.warning(
                    "%s Event listener error (%s). Reconnecting in %ss",
                    self.log_id,
                    type(err).__name__,
                    backoff,
                    exc_info=True,
                )
                self.is_connected = False

                try:
                    if _event_session is not None:
                        await _event_session.close()
                except Exception:
                    pass

                _event_session = None

                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

        # Clean shutdown
        try:
            if _event_session is not None:
                await _event_session.close()
        except Exception:
            pass

        self.is_connected = False
        LOGGER.debug("%s Destroying listening worker.", self.log_id)

    async def sending_loop(self, worker_id: int):
        """Send commands to the gateway using the command session.

        The gateway may reset the command socket; we reconnect on errors.
        """
        self._terminate_sender = False

        LOGGER.debug("%s Creating sending worker %s", self.log_id, worker_id)

        backoff = 1
        max_backoff = 60
        _command_session: Optional[OWNCommandSession] = None

        while not self._terminate_sender:
            task = await self.send_buffer.get()
            try:
                if _command_session is None:
                    _command_session = OWNCommandSession(gateway=self.gateway, logger=LOGGER)
                    await _command_session.connect()
                    backoff = 1
                    LOGGER.debug("%s Command session established (worker %s)", self.log_id, worker_id)

                LOGGER.debug(
                    "%s Message `%s` was successfully unqueued by worker %s.",
                    self.log_id,
                    task["message"],
                    worker_id,
                )

                await _command_session.send(
                    message=task["message"],
                    is_status_request=task["is_status_request"],
                )

                self.send_buffer.task_done()

            except asyncio.CancelledError:
                # Put the task back if we are being cancelled mid-send.
                try:
                    await self.send_buffer.put(task)
                except Exception:
                    pass
                raise

            except Exception as err:
                # Re-queue the task to retry after reconnect.
                LOGGER.debug(
                    "%s Command session connection reset, retrying... (%s)",
                    self.log_id,
                    type(err).__name__,
                )

                try:
                    await self.send_buffer.put(task)
                except Exception:
                    pass

                try:
                    if _command_session is not None:
                        await _command_session.close()
                except Exception:
                    pass

                _command_session = None

                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

        try:
            if _command_session is not None:
                await _command_session.close()
        except Exception:
            pass

        LOGGER.debug("%s Destroying sending worker %s", self.log_id, worker_id)

    async def close_listener(self) -> bool:
        LOGGER.info("%s Closing gateway workers", self.log_id)
        self._terminate_sender = True
        self._terminate_listener = True
        return True

    async def send(self, message: OWNCommand):
        await self.send_buffer.put({"message": message, "is_status_request": False})
        LOGGER.debug(
            "%s Message `%s` was successfully queued.",
            self.log_id,
            message,
        )

    async def send_status_request(self, message: OWNCommand):
        await self.send_buffer.put({"message": message, "is_status_request": True})
        LOGGER.debug(
            "%s Message `%s` was successfully queued.",
            self.log_id,
            message,
        )
