"""Support for MyHOME binary sensors (dry contacts, auxiliary channels, motion sensors).

The platform also creates the ``connected`` diagnostic entity of the gateway device
(0.3.0, plan G1-B): it is fed by the ``SIGNAL_GATEWAY_STATS`` snapshots, stays
available while the gateway is down and exists even when no binary sensor at all is
configured.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import (
    DOMAIN as PLATFORM,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.restore_state import (
    ExtraStoredData,
    RestoredExtraData,
    RestoreEntity,
)
from homeassistant.util import dt as dt_util

from OWNd.message import (
    MESSAGE_TYPE_MOTION,
    MESSAGE_TYPE_MOTION_TIMEOUT,
    MESSAGE_TYPE_PIR_SENSITIVITY,
    OWNAuxEvent,
    OWNDryContactCommand,
    OWNDryContactEvent,
    OWNLightingCommand,
    OWNLightingEvent,
)

from .const import (
    CONF_BUS_INTERFACE,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_MODEL,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
    CONF_INVERTED,
    CONF_MANUFACTURER,
    CONF_PLATFORMS,
    CONF_WHERE,
    CONF_WHO,
    DOMAIN,
    GATEWAY_DIAG_CONNECTED,
    LOGGER,
)
from .gateway import MyHOMEGatewayHandler
from .myhome_device import (
    MyHOMEEntity,
    MyHOMEGatewayDiagnosticEntity,
    address_attributes,
)

PIR_SENSITIVITY = ["low", "medium", "high", "very high"]

# Motion sensors report their own timeout; until then assume the BTicino default
# (5 minutes) plus a margin, so a missed "no more motion" frame still clears.
DEFAULT_MOTION_TIMEOUT = timedelta(seconds=315)
MOTION_TIMEOUT_MARGIN = timedelta(seconds=15)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the binary sensor entities of this gateway.

    The gateway ``connected`` diagnostic entity (0.3.0, plan G1-B) is created for
    every gateway, including one without a single configured binary sensor.
    """
    gateway_data = hass.data[DOMAIN][config_entry.data[CONF_MAC]]
    gateway_handler = gateway_data[CONF_ENTITY]
    binary_sensors: list[Entity] = [MyHOMEGatewayConnectedSensor(gateway_handler)]

    configured_binary_sensors = gateway_data[CONF_PLATFORMS].get(PLATFORM, {})

    for device_id, cfg in configured_binary_sensors.items():
        who = int(cfg[CONF_WHO])
        # Contract A: `class` is always present but may legitimately be None (WHO 9).
        device_class = cfg[CONF_DEVICE_CLASS]
        entity_class: type[MyHOMEEntity] | None = None
        if who == 25:
            entity_class = MyHOMEDryContact
        elif who == 9:
            entity_class = MyHOMEAuxiliary
        elif who == 1 and device_class == BinarySensorDeviceClass.MOTION:
            entity_class = MyHOMEMotionSensor
        if entity_class is None:
            LOGGER.warning(
                "Ignoring binary sensor %s: WHO %s with class %s is not supported",
                device_id,
                who,
                device_class,
            )
            continue

        binary_sensors.append(
            entity_class(
                hass=hass,
                device_id=device_id,
                who=cfg[CONF_WHO],
                where=cfg[CONF_WHERE],
                interface=cfg.get(CONF_BUS_INTERFACE),
                name=cfg[CONF_NAME],
                entity_name=cfg[CONF_ENTITY_NAME],
                inverted=cfg[CONF_INVERTED],
                device_class=device_class,
                manufacturer=cfg[CONF_MANUFACTURER],
                model=cfg[CONF_DEVICE_MODEL],
                gateway=gateway_handler,
            )
        )

    async_add_entities(binary_sensors)


def entity_name_for(entity_name: str | None, device_class: BinarySensorDeviceClass | None) -> str:
    """Name of the sensor entity inside its device.

    `class` may be None (WHO 9 auxiliary channels have no HA device class), so the
    device class can never be dereferenced blindly (plat-01).
    """
    if entity_name:
        return entity_name
    if device_class is None:
        return "Sensor"
    return str(device_class).replace("_", " ").capitalize()


class MyHOMEBinarySensor(MyHOMEEntity, BinarySensorEntity):
    """Shared behaviour of the three binary sensor flavours."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        entity_name: str | None,
        device_id: str,
        who: str,
        where: str,
        interface: str | None,
        inverted: bool,
        device_class: BinarySensorDeviceClass | None,
        manufacturer: str | None,
        model: str | None,
        gateway: MyHOMEGatewayHandler,
    ) -> None:
        super().__init__(
            hass=hass,
            name=name,
            platform=PLATFORM,
            device_id=device_id,
            who=who,
            where=where,
            manufacturer=manufacturer,
            model=model,
            gateway=gateway,
        )

        self._inverted = bool(inverted)
        self._interface = interface
        self._full_where = f"{self._where}#4#{self._interface}" if self._interface is not None else self._where

        self._attr_device_class = device_class
        self._attr_name = entity_name_for(entity_name, device_class)

        # KNOWN LIMITATION (plat-12): the device class is part of the unique id, so
        # changing `class:` in the YAML orphans the registry entry (and the pruning in
        # __init__.expected_unique_ids() then removes it).  Kept for backward
        # compatibility with existing installations; `None` renders as "-None".
        self._attr_unique_id = f"{gateway.mac}-{self._device_id}-{device_class}"

        self._attr_is_on = False

    def _apply_state(self, is_on: bool) -> None:
        """Apply the `inverted` option to a raw contact state."""
        self._attr_is_on = is_on != self._inverted


class MyHOMEDryContact(MyHOMEBinarySensor):
    """A WHO 25 dry contact / IR detector."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._attr_extra_state_attributes = {"Sensor": f"({self._where[0]}){self._where[1:]}"}

    async def async_update(self) -> None:
        """Ask the gateway for the current state (also called on entity add)."""
        await self._gateway_handler.send_status_request(OWNDryContactCommand.status(self._full_where))

    def handle_event(self, message: OWNDryContactEvent) -> None:
        """Handle an event message (must never raise: it runs in the event loop)."""
        try:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            self._apply_state(bool(message.is_on))
        except Exception:  # pragma: no cover - defensive, keeps the session alive
            LOGGER.exception("%s Error handling dry contact event %s", self._gateway_handler.log_id, message)
            return
        self.async_schedule_update_ha_state()


class MyHOMEAuxiliary(MyHOMEBinarySensor):
    """A WHO 9 auxiliary channel (read only, no device class by default)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._attr_extra_state_attributes = {"Auxiliary channel": self._where}

    # AUX channels cannot be queried: no `async_update` (the base class skips it).

    def handle_event(self, message: OWNAuxEvent) -> None:
        """Handle an event message (must never raise: it runs in the event loop)."""
        try:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            self._apply_state(bool(message.is_on))
        except Exception:  # pragma: no cover - defensive, keeps the session alive
            LOGGER.exception("%s Error handling auxiliary event %s", self._gateway_handler.log_id, message)
            return
        self.async_schedule_update_ha_state()


class MyHOMEMotionSensor(MyHOMEBinarySensor, RestoreEntity):
    """A WHO 1 motion sensor.

    The bus only announces *detected motion*; the "no more motion" transition is
    derived from the sensor's own timeout (queried at startup).  The expiry runs on a
    timer instead of polling the entity (Contract C: `should_poll` stays False).
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._timeout = DEFAULT_MOTION_TIMEOUT
        self._timeout_timer = None
        # When the pending "no more motion" timer fires (UTC); persisted so a reload
        # does not restart a full timeout from scratch.
        self._expires_at: datetime | None = None
        self._attr_is_on = None
        self._attr_extra_state_attributes = {
            **address_attributes(self._where, self._interface),
            "Timeout": self._timeout.total_seconds(),
            "Sensitivity": PIR_SENSITIVITY[1],
        }

    @property
    def _motion_detected(self) -> bool:
        """`is_on` value that means "motion detected" for this sensor."""
        return not self._inverted

    async def async_update(self) -> None:
        """Ask the sensor for its configuration (also called on entity add)."""
        await self._gateway_handler.send_status_request(OWNLightingCommand.get_pir_sensitivity(self._full_where))
        await self._gateway_handler.send_status_request(OWNLightingCommand.get_motion_timeout(self._full_where))

    @property
    def extra_restore_state_data(self) -> ExtraStoredData | None:
        """Persist the state and the expiry independently of the entity state.

        On a config entry reload the gateway connection is closed before the entities
        are removed, so Home Assistant snapshots them as ``unavailable``: the last
        state is then useless and only the extra data survives (same pattern as
        ``cover.py``).  ``expires_at`` is stored as an ISO timestamp so the remaining
        motion timeout is restored exactly instead of restarting from zero.
        """
        return RestoredExtraData(
            {
                "is_on": self._attr_is_on,
                "expires_at": self._expires_at.isoformat() if self._expires_at else None,
            }
        )

    async def async_added_to_hass(self) -> None:
        """Register, query the sensor and restore the previous state."""
        await super().async_added_to_hass()
        if await self._async_restore_from_extra_data():
            return
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state not in (STATE_ON, STATE_OFF):
            return
        was_on = last_state.state == STATE_ON
        self._attr_is_on = was_on
        if was_on == self._motion_detected:
            # Motion was active: restart the timeout for whatever is left of it.
            remaining = (last_state.last_updated + self._timeout - dt_util.utcnow()).total_seconds()
            if remaining > 0:
                self._schedule_timeout(remaining)
            else:
                self._attr_is_on = not self._motion_detected
        self.async_write_ha_state()

    async def _async_restore_from_extra_data(self) -> bool:
        """Restore `is_on` / the pending timeout from the extra data, if any."""
        extra_data = await self.async_get_last_extra_data()
        if extra_data is None:
            return False
        stored = extra_data.as_dict()
        is_on = stored.get("is_on")
        if is_on is None:
            return False
        self._attr_is_on = bool(is_on)
        if self._attr_is_on == self._motion_detected:
            expires_at = dt_util.parse_datetime(stored.get("expires_at") or "")
            remaining = (
                (expires_at - dt_util.utcnow()).total_seconds()
                if expires_at is not None
                else self._timeout.total_seconds()
            )
            if remaining > 0:
                self._schedule_timeout(remaining)
            else:
                self._attr_is_on = not self._motion_detected
        self.async_write_ha_state()
        return True

    async def async_will_remove_from_hass(self) -> None:
        """Cancel the pending timeout."""
        self._cancel_timeout()
        await super().async_will_remove_from_hass()

    @callback
    def _cancel_timeout(self) -> None:
        if self._timeout_timer is not None:
            self._timeout_timer()
            self._timeout_timer = None
        self._expires_at = None

    @callback
    def _schedule_timeout(self, seconds: float | None = None) -> None:
        """(Re)arm the "no more motion" timer."""
        self._cancel_timeout()
        delay = self._timeout.total_seconds() if seconds is None else seconds
        self._expires_at = dt_util.utcnow() + timedelta(seconds=delay)
        self._timeout_timer = async_call_later(self.hass, delay, self._async_motion_expired)

    @callback
    def _async_motion_expired(self, now: datetime) -> None:
        """No motion frame for a whole timeout: clear the sensor (plat-11).

        The cleared state honours `inverted` symmetrically, so an inverted motion
        sensor toggles between the two states instead of being stuck.
        """
        self._timeout_timer = None
        self._expires_at = None
        self._attr_is_on = not self._motion_detected
        self.async_write_ha_state()

    def handle_event(self, message: OWNLightingEvent) -> None:
        """Handle an event message (must never raise: it runs in the event loop)."""
        if message.message_type not in (
            MESSAGE_TYPE_MOTION,
            MESSAGE_TYPE_MOTION_TIMEOUT,
            MESSAGE_TYPE_PIR_SENSITIVITY,
        ):
            return

        try:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            if message.message_type == MESSAGE_TYPE_MOTION and message.motion:
                self._attr_is_on = self._motion_detected
                self._schedule_timeout()
            elif message.message_type == MESSAGE_TYPE_MOTION_TIMEOUT:
                self._timeout = message.motion_timeout + MOTION_TIMEOUT_MARGIN
                self._attr_extra_state_attributes["Timeout"] = self._timeout.total_seconds()
                if self._attr_is_on == self._motion_detected:
                    self._schedule_timeout()
            elif message.message_type == MESSAGE_TYPE_PIR_SENSITIVITY:
                sensitivity = message.pir_sensitivity
                if isinstance(sensitivity, int) and 0 <= sensitivity < len(PIR_SENSITIVITY):
                    self._attr_extra_state_attributes["Sensitivity"] = PIR_SENSITIVITY[sensitivity]
        except Exception:  # pragma: no cover - defensive, keeps the session alive
            LOGGER.exception("%s Error handling motion event %s", self._gateway_handler.log_id, message)
            return

        self.async_write_ha_state()


# --------------------------------------------------------------------------- gateway
class MyHOMEGatewayConnectedSensor(MyHOMEGatewayDiagnosticEntity, BinarySensorEntity):
    """Whether the gateway event session is alive (0.3.0, plan G1-B).

    Unlike every other entity of the integration this one keeps reporting a state
    while the gateway is down (that is its whole point), see
    ``MyHOMEGatewayDiagnosticEntity``.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, gateway: MyHOMEGatewayHandler) -> None:
        super().__init__(gateway, GATEWAY_DIAG_CONNECTED, "gateway_connected")
        # Until the first snapshot arrives, report what the handler knows.
        self._attr_is_on = bool(getattr(gateway, "is_connected", False))

    @callback
    def _apply_stats(self, stats: Any) -> None:
        self._attr_is_on = bool(stats.connected)
