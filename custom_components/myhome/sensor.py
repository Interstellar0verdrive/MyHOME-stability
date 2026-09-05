"""Support for MyHOME sensors (instant power, energy totalisers, temperature, illuminance).

Contract C (entity base) and Contract E (instant-power keep-alive) apply here:

* no entity is polled by Home Assistant (``should_poll`` is False in the base class);
  everything that needs a periodic bus request drives its own timer with the HA time
  helpers and cancels it through ``async_on_remove``;
* the power sensor arms ``*#18*<where>*#1200#1*<minutes>##`` when it is added and again
  on every gateway (re)connection, and re-arms itself a few minutes before the meter
  would stop streaming (Contract E, finding sc-04);
* the energy totalisers request their value at add time, periodically and at the local
  day/month boundary, and survive a restart through ``RestoreSensor`` (sc-11, sc-18);
* names come from the entity translation keys, never from the device name (sc-05).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN as PLATFORM
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MAC,
    CONF_NAME,
    LIGHT_LUX,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_time_change,
    async_track_time_interval,
)

from OWNd.message import (
    MESSAGE_TYPE_ACTIVE_POWER,
    MESSAGE_TYPE_CURRENT_DAY_CONSUMPTION,
    MESSAGE_TYPE_CURRENT_MONTH_CONSUMPTION,
    MESSAGE_TYPE_ENERGY_TOTALIZER,
    MESSAGE_TYPE_ILLUMINANCE,
    MESSAGE_TYPE_MAIN_TEMPERATURE,
    MESSAGE_TYPE_SECONDARY_TEMPERATURE,
    OWNEnergyCommand,
    OWNEnergyEvent,
    OWNHeatingCommand,
    OWNHeatingEvent,
    OWNLightingCommand,
    OWNLightingEvent,
)

from .const import (
    ATTR_DURATION,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_MODEL,
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
    CONF_KEEPALIVE_MINUTES,
    CONF_MANUFACTURER,
    CONF_PLATFORMS,
    CONF_WHERE,
    CONF_WHO,
    DEFAULT_KEEPALIVE_MINUTES,
    DOMAIN,
    LOGGER,
    SERVICE_START_SENDING_INSTANT_POWER,
)
from .gateway import MyHOMEGatewayHandler
from .myhome_device import MyHOMEEntity, address_attributes

# Keys of the sub-entity slots pre-seeded by validate.py in ``device[CONF_ENTITIES]``.
POWER_SLOT = f"{SensorDeviceClass.POWER}"
DAILY_ENERGY_SLOT = f"daily-{SensorDeviceClass.ENERGY}"
MONTHLY_ENERGY_SLOT = f"monthly-{SensorDeviceClass.ENERGY}"
TOTAL_ENERGY_SLOT = f"total-{SensorDeviceClass.ENERGY}"

# How often the energy totalisers are re-requested (the gateway never pushes them
# spontaneously).  Daily/monthly are additionally refreshed right after midnight.
ENERGY_REFRESH_INTERVAL = timedelta(minutes=5)
# Temperature probes and illuminance sensors do get pushed values, but a slow poll
# keeps them from going stale forever (sc-15).
ENVIRONMENT_REFRESH_INTERVAL = timedelta(minutes=5)

# Instant power keep-alive (Contract E).  The meter accepts 1..255 minutes; we re-arm
# KEEPALIVE_MARGIN_MINUTES before expiry so the stream never has a hole.
KEEPALIVE_MARGIN_MINUTES = 5
MAX_KEEPALIVE_MINUTES = 255

SERVICE_SEND_INSTANT_POWER = SERVICE_START_SENDING_INSTANT_POWER

INSTANT_POWER_SERVICE_SCHEMA = {
    vol.Optional(ATTR_DURATION): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_KEEPALIVE_MINUTES)),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the sensor entities of one gateway."""
    gateway_data = hass.data[DOMAIN][config_entry.data[CONF_MAC]]
    configured_sensors: dict[str, dict[str, Any]] = gateway_data[CONF_PLATFORMS].get(PLATFORM, {})
    if not configured_sensors:
        return

    gateway: MyHOMEGatewayHandler = gateway_data[CONF_ENTITY]
    sensors: list[MyHOMEEntity] = []
    power_devices_configured = False

    for device_id, device in configured_sensors.items():
        sensor_class = device[CONF_DEVICE_CLASS]
        common = {
            "hass": hass,
            "device_id": device_id,
            "who": device[CONF_WHO],
            "where": device[CONF_WHERE],
            "name": device[CONF_NAME],
            "manufacturer": device[CONF_MANUFACTURER],
            "model": device[CONF_DEVICE_MODEL],
            "gateway": gateway,
        }

        if sensor_class in (SensorDeviceClass.POWER, SensorDeviceClass.ENERGY):
            slots = list(device[CONF_ENTITIES].keys())
            if sensor_class == SensorDeviceClass.POWER:
                power_devices_configured = True
                sensors.append(
                    MyHOMEPowerSensor(
                        keepalive_minutes=int(device.get(CONF_KEEPALIVE_MINUTES, DEFAULT_KEEPALIVE_MINUTES)),
                        **common,
                    )
                )
                if POWER_SLOT in slots:
                    slots.remove(POWER_SLOT)
            for slot in slots:
                sensors.append(MyHOMEEnergySensor(entity_specific_id=slot, **common))

        elif sensor_class == SensorDeviceClass.TEMPERATURE:
            sensors.append(
                MyHOMETemperatureSensor(entity_name=device.get(CONF_ENTITY_NAME), **common)
            )

        elif sensor_class == SensorDeviceClass.ILLUMINANCE:
            sensors.append(
                MyHOMEIlluminanceSensor(entity_name=device.get(CONF_ENTITY_NAME), **common)
            )

    if power_devices_configured:
        entity_platform.async_get_current_platform().async_register_entity_service(
            SERVICE_SEND_INSTANT_POWER,
            INSTANT_POWER_SERVICE_SCHEMA,
            "start_sending_instant_power",
        )

    async_add_entities(sensors)


class _MyHOMESensorEntity(MyHOMEEntity):
    """Shared plumbing for every MyHOME sensor entity.

    A single MyHOME device (an F520 meter, for instance) hosts several entities, so
    each of them registers under its own ``_entity_slot`` in
    ``hass.data[...][CONF_ENTITIES]`` (Contract C); the base class does the
    bookkeeping.  Secondary entities carry no ``entity_name`` so their
    ``_attr_translation_key`` names them (sc-05).
    """

    _entity_slot = PLATFORM

    @callback
    def _async_on_connection_change(self, connected: bool) -> None:
        """Availability changed; on reconnection re-issue our bus request."""
        super()._async_on_connection_change(connected)
        if connected:
            self.hass.async_create_task(self.async_update())

    @callback
    def _async_periodic_refresh(self, now: datetime) -> None:
        """Timer callback: re-issue the bus request."""
        self.hass.async_create_task(self.async_update())


class MyHOMEPowerSensor(_MyHOMESensorEntity, SensorEntity):
    """Instant power reported by a WHO=18 meter."""

    _attr_translation_key = "power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _entity_slot = POWER_SLOT

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        device_id: str,
        who: str,
        where: str,
        manufacturer: str,
        model: str | None,
        gateway: MyHOMEGatewayHandler,
        keepalive_minutes: int = DEFAULT_KEEPALIVE_MINUTES,
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
        self._attr_unique_id = f"{gateway.mac}-{self._device_id}-{POWER_SLOT}"
        self._attr_native_value = None
        self._keepalive_minutes = max(0, min(int(keepalive_minutes), MAX_KEEPALIVE_MINUTES))

    async def async_added_to_hass(self) -> None:
        """Arm the instant power stream and schedule the re-arm (Contract E)."""
        await super().async_added_to_hass()  # -> async_update() -> first arm
        if self._keepalive_minutes > 0:
            interval = timedelta(minutes=max(1, self._keepalive_minutes - KEEPALIVE_MARGIN_MINUTES))
            self.async_on_remove(
                async_track_time_interval(self.hass, self._async_periodic_refresh, interval)
            )

    async def async_update(self) -> None:
        """(Re)arm the instant power stream; also used by ``homeassistant.update_entity``."""
        if self._keepalive_minutes <= 0:
            return
        await self.start_sending_instant_power(self._keepalive_minutes)

    async def start_sending_instant_power(self, duration: int | None = None) -> None:
        """Ask the meter to stream instant power for ``duration`` minutes (1-255).

        ``duration`` defaults to the configured ``keepalive_minutes`` (sc-04: the
        service schema made it optional while the method required it).
        """
        minutes = duration or self._keepalive_minutes or DEFAULT_KEEPALIVE_MINUTES
        minutes = max(1, min(int(minutes), MAX_KEEPALIVE_MINUTES))
        LOGGER.debug(
            "%s Arming instant power on %s for %s minutes.",
            self._gateway_handler.log_id,
            self._where,
            minutes,
        )
        await self._gateway_handler.send(
            OWNEnergyCommand.start_sending_instant_power(self._where, minutes)
        )

    def handle_event(self, message: OWNEnergyEvent) -> None:
        """Handle an instant power frame."""
        if message.message_type != MESSAGE_TYPE_ACTIVE_POWER:
            return
        LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
        self._attr_native_value = message.active_power
        self.async_write_ha_state()


class MyHOMEEnergySensor(_MyHOMESensorEntity, RestoreSensor):
    """Daily / monthly / total energy totaliser of a WHO=18 meter.

    All three entities are functional since 0.2.0: the totals are requested at
    add time, on every reconnection, every 5 minutes and right after local
    midnight, and the replies read on the command session reach ``handle_event``
    (sc-01 / gw-13).  "Energy today" and "Energy this month" are still created
    **disabled by default** (unchanged behaviour, no surprise entities for
    existing installations): enable them from Settings > Devices & services >
    MyHOME > the meter device > "+N entities not shown" > enable, or from the
    entity settings dialog.  The total "Energy" entity is enabled by default.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    # slot -> (translation key, OWNd message type, enabled by default)
    _SLOTS: dict[str, tuple[str, str, bool]] = {
        DAILY_ENERGY_SLOT: ("energy_today", MESSAGE_TYPE_CURRENT_DAY_CONSUMPTION, False),
        MONTHLY_ENERGY_SLOT: ("energy_month", MESSAGE_TYPE_CURRENT_MONTH_CONSUMPTION, False),
        TOTAL_ENERGY_SLOT: ("energy_total", MESSAGE_TYPE_ENERGY_TOTALIZER, True),
    }

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        device_id: str,
        who: str,
        where: str,
        entity_specific_id: str,
        manufacturer: str,
        model: str | None,
        gateway: MyHOMEGatewayHandler,
    ) -> None:
        translation_key, message_type, enabled_default = self._SLOTS[entity_specific_id]
        # Before super().__init__(): the base class names the entity by the
        # translation key only when it is already set (Contract C).
        self._attr_translation_key = translation_key
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
        self._entity_slot = entity_specific_id
        self._entity_specific_id = entity_specific_id
        self._message_type = message_type
        self._attr_entity_registry_enabled_default = enabled_default
        self._attr_unique_id = f"{gateway.mac}-{self._device_id}-{entity_specific_id}"
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Restore the last value and schedule the periodic/boundary refreshes."""
        await super().async_added_to_hass()  # -> async_update() -> first request

        # sc-11: without RestoreSensor every restart left a hole (and, with
        # TOTAL_INCREASING, a spurious meter reset) until the first reply arrived.
        if self._attr_native_value is None:
            last_data = await self.async_get_last_sensor_data()
            if last_data is not None and last_data.native_value is not None:
                self._attr_native_value = last_data.native_value

        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_periodic_refresh, ENERGY_REFRESH_INTERVAL
            )
        )
        if self._entity_specific_id != TOTAL_ENERGY_SLOT:
            # Daily/monthly counters reset at local midnight: ask again right after it
            # so the new period starts from a fresh value (timezone aware helper).
            self.async_on_remove(
                async_track_time_change(
                    self.hass, self._async_periodic_refresh, hour=0, minute=0, second=10
                )
            )

    async def async_update(self) -> None:
        """Request our totaliser value from the meter."""
        if self._entity_specific_id == TOTAL_ENERGY_SLOT:
            command = OWNEnergyCommand.get_total_consumption(self._where)
        elif self._entity_specific_id == MONTHLY_ENERGY_SLOT:
            command = OWNEnergyCommand.get_partial_monthly_consumption(self._where)
        else:
            command = OWNEnergyCommand.get_partial_daily_consumption(self._where)
        await self._gateway_handler.send_status_request(command)

    def _value_of(self, message: OWNEnergyEvent) -> float | int | None:
        """Consumption carried by ``message`` for this entity."""
        if self._message_type == MESSAGE_TYPE_ENERGY_TOTALIZER:
            return message.total_consumption
        if self._message_type == MESSAGE_TYPE_CURRENT_MONTH_CONSUMPTION:
            return message.current_month_partial_consumption
        return message.current_day_partial_consumption

    def handle_event(self, message: OWNEnergyEvent) -> None:
        """Handle a totaliser frame addressed to this entity (sc-18)."""
        if message.message_type != self._message_type:
            # The frame belongs to a sibling entity of the same meter.
            return
        value = self._value_of(message)
        if value is None or value < 0:
            LOGGER.debug(
                "%s Ignoring implausible energy value %s for %s.",
                self._gateway_handler.log_id,
                value,
                self._attr_unique_id,
            )
            return
        LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
        self._attr_native_value = value
        self.async_write_ha_state()


class MyHOMETemperatureSensor(_MyHOMESensorEntity, SensorEntity):
    """WHO=4 temperature probe."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _entity_slot = f"{SensorDeviceClass.TEMPERATURE}"

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        device_id: str,
        who: str,
        where: str,
        manufacturer: str,
        model: str | None,
        gateway: MyHOMEGatewayHandler,
        entity_name: str | None = None,
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
            # Only entity of its device: it takes the device name (Contract C)
            # unless the configuration gives it an explicit entity name.
            entity_name=entity_name,
        )
        self._attr_unique_id = f"{gateway.mac}-{self._device_id}-{self.entity_slot}"
        self._attr_native_value = None

    async def async_added_to_hass(self) -> None:
        """Schedule the slow refresh (Contract C forbids should_poll)."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_periodic_refresh, ENVIRONMENT_REFRESH_INTERVAL
            )
        )

    async def async_update(self) -> None:
        """Request the probe temperature."""
        await self._gateway_handler.send_status_request(
            OWNHeatingCommand.get_temperature(self._where)
        )

    def handle_event(self, message: OWNHeatingEvent) -> None:
        """Handle a temperature frame."""
        if message.message_type == MESSAGE_TYPE_MAIN_TEMPERATURE:
            value = message.main_temperature
        elif message.message_type == MESSAGE_TYPE_SECONDARY_TEMPERATURE:
            value = message.secondary_temperature[1]
        else:
            return
        LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
        self._attr_native_value = value
        self.async_write_ha_state()


class MyHOMEIlluminanceSensor(_MyHOMESensorEntity, SensorEntity):
    """WHO=1 illuminance sensor."""

    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_state_class = SensorStateClass.MEASUREMENT
    _entity_slot = f"{SensorDeviceClass.ILLUMINANCE}"

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        device_id: str,
        who: str,
        where: str,
        manufacturer: str,
        model: str | None,
        gateway: MyHOMEGatewayHandler,
        entity_name: str | None = None,
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
            entity_name=entity_name,
        )
        self._attr_unique_id = f"{gateway.mac}-{self._device_id}-{self.entity_slot}"
        self._attr_native_value = None
        # A/PL is meaningful for a WHO=1 point-to-point WHERE (sc-17: the same split
        # was applied to WHO=18/WHO=4 wheres, where it means nothing).
        self._attr_extra_state_attributes = address_attributes(where, None)

    async def async_added_to_hass(self) -> None:
        """Schedule the slow refresh (sc-15: the sensor was requested only once)."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_periodic_refresh, ENVIRONMENT_REFRESH_INTERVAL
            )
        )

    async def async_update(self) -> None:
        """Request the illuminance value."""
        await self._gateway_handler.send_status_request(
            OWNLightingCommand.get_illuminance(self._where)
        )

    def handle_event(self, message: OWNLightingEvent) -> None:
        """Handle an illuminance frame."""
        if message.message_type != MESSAGE_TYPE_ILLUMINANCE:
            return
        LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
        self._attr_native_value = message.illuminance
        self.async_write_ha_state()
