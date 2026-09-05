"""Support for MyHOME heating/cooling zones and central units (WHO=4).

Fixes from the sensor/climate audit: TURN_ON/TURN_OFF features (sc-06), no advertised
but unimplemented FAN_MODE (sc-07), AUTO also on the central unit (sc-08), HEAT/COOL
selectable before a target temperature is known (sc-10), a safe ``async_set_temperature``
(sc-16) and an ``hvac_action`` that is derived from the MODE frames instead of staying
unknown until a valve frame arrives (sc-19).
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import DOMAIN as PLATFORM
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_MAC, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from OWNd.message import (
    CLIMATE_MODE_AUTO,
    CLIMATE_MODE_COOL,
    CLIMATE_MODE_HEAT,
    CLIMATE_MODE_OFF,
    MESSAGE_TYPE_ACTION,
    MESSAGE_TYPE_LOCAL_OFFSET,
    MESSAGE_TYPE_LOCAL_TARGET_TEMPERATURE,
    MESSAGE_TYPE_MAIN_HUMIDITY,
    MESSAGE_TYPE_MAIN_TEMPERATURE,
    MESSAGE_TYPE_MODE,
    MESSAGE_TYPE_MODE_TARGET,
    MESSAGE_TYPE_TARGET_TEMPERATURE,
    OWNHeatingCommand,
    OWNHeatingEvent,
)

from .const import (
    CONF_CENTRAL,
    CONF_COOLING_SUPPORT,
    CONF_DEVICE_MODEL,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
    CONF_FAN_SUPPORT,
    CONF_HEATING_SUPPORT,
    CONF_MANUFACTURER,
    CONF_PLATFORMS,
    CONF_STANDALONE,
    CONF_WHO,
    CONF_ZONE,
    DOMAIN,
    LOGGER,
)
from .gateway import MyHOMEGatewayHandler
from .myhome_device import MyHOMEEntity

# Used when the user asks for HEAT/COOL before the zone has reported its set point
# (sc-10): the command needs a temperature, so send a sane one and ask for the status.
DEFAULT_TARGET_TEMPERATURE = 20.0

# OWNd climate mode -> HA HVAC mode.
_OWN_MODE_TO_HVAC: dict[str, HVACMode] = {
    CLIMATE_MODE_AUTO: HVACMode.AUTO,
    CLIMATE_MODE_HEAT: HVACMode.HEAT,
    CLIMATE_MODE_COOL: HVACMode.COOL,
    CLIMATE_MODE_OFF: HVACMode.OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the climate entities of one gateway."""
    gateway_data = hass.data[DOMAIN][config_entry.data[CONF_MAC]]
    configured_devices: dict[str, dict[str, Any]] = gateway_data[CONF_PLATFORMS].get(PLATFORM, {})
    if not configured_devices:
        return

    gateway: MyHOMEGatewayHandler = gateway_data[CONF_ENTITY]
    async_add_entities(
        MyHOMEClimate(
            hass=hass,
            device_id=device_id,
            who=device[CONF_WHO],
            # Contract A: climate devices carry ``zone``, never ``where``.
            zone=device[CONF_ZONE],
            name=device[CONF_NAME],
            entity_name=device.get(CONF_ENTITY_NAME),
            heating=device[CONF_HEATING_SUPPORT],
            cooling=device[CONF_COOLING_SUPPORT],
            fan=device[CONF_FAN_SUPPORT],
            standalone=device[CONF_STANDALONE],
            central=device[CONF_CENTRAL],
            manufacturer=device[CONF_MANUFACTURER],
            model=device[CONF_DEVICE_MODEL],
            gateway=gateway,
        )
        for device_id, device in configured_devices.items()
    )


class MyHOMEClimate(MyHOMEEntity, ClimateEntity):
    """A MyHOME thermoregulation zone or central unit."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = 0.1
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 5
    _attr_max_temp = 40

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        device_id: str,
        who: str,
        zone: str,
        heating: bool,
        cooling: bool,
        fan: bool,
        standalone: bool,
        central: bool,
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
            where=zone,
            manufacturer=manufacturer,
            model=model,
            gateway=gateway,
            entity_name=entity_name,
        )

        self._standalone = standalone
        self._central = True if self._where.startswith("#0") else central
        self._heating = heating
        self._cooling = cooling

        self._attr_supported_features = ClimateEntityFeature(0)
        self._attr_hvac_modes = [HVACMode.OFF]
        if heating or cooling:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            # sc-08: `*4*311*#0##` is a valid command, so the central unit gets AUTO
            # too - without it a central unit in weekly program stayed `unknown`.
            self._attr_hvac_modes.append(HVACMode.AUTO)
            if heating:
                self._attr_hvac_modes.append(HVACMode.HEAT)
            if cooling:
                self._attr_hvac_modes.append(HVACMode.COOL)

        # sc-06: without these HA >= 2025.1 refuses climate.turn_on/turn_off/toggle.
        self._attr_supported_features |= ClimateEntityFeature.TURN_OFF
        if len(self._attr_hvac_modes) > 1:
            self._attr_supported_features |= ClimateEntityFeature.TURN_ON

        # sc-07: FAN_MODE used to be advertised while async_set_fan_mode did not exist
        # (NotImplementedError) and no frame ever populated fan_mode.  OWNd has no
        # fan-speed command either, so the key is accepted but does nothing.
        if fan:
            LOGGER.warning(
                "Climate zone %s: 'fan: true' is accepted for backward compatibility but "
                "fan speed is not supported by the MyHOME protocol layer; the option is ignored",
                device_id,
            )

        self._attr_current_temperature = None
        self._attr_current_humidity = None
        self._target_temperature = None
        self._local_offset = 0
        self._local_target_temperature = None

        self._attr_hvac_mode = None
        self._attr_hvac_action = None
        # True once the zone reported a valve/actuator state: from then on the reported
        # action wins over the one derived from the mode (sc-19).
        self._action_reported = False

    async def async_update(self) -> None:
        """Request the full zone status."""
        await self._gateway_handler.send_status_request(
            OWNHeatingCommand.status(self._where)
        )

    @property
    def target_temperature(self) -> float | None:
        """Set point as displayed on the zone (local offset included when known)."""
        if self._local_target_temperature is not None:
            return self._local_target_temperature
        return self._target_temperature

    # ------------------------------------------------------------------ commands
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.OFF:
            await self._gateway_handler.send(
                OWNHeatingCommand.set_mode(
                    where=self._where,
                    mode=CLIMATE_MODE_OFF,
                    standalone=self._standalone,
                )
            )
            return

        if hvac_mode == HVACMode.AUTO:
            await self._gateway_handler.send(
                OWNHeatingCommand.set_mode(
                    where=self._where,
                    mode=CLIMATE_MODE_AUTO,
                    standalone=self._standalone,
                )
            )
            return

        if hvac_mode not in (HVACMode.HEAT, HVACMode.COOL):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="climate_unsupported_hvac_mode",
                translation_placeholders={"hvac_mode": str(hvac_mode), "entity_id": str(self.entity_id)},
            )

        # sc-10: MyHOME has no "mode only" command for HEAT/COOL, the set point goes with
        # it.  The old code silently did nothing while the set point was unknown.
        target_temperature = self._target_temperature
        if target_temperature is None:
            target_temperature = DEFAULT_TARGET_TEMPERATURE
            LOGGER.warning(
                "%s Zone %s has no known set point yet: switching to %s with %s C and "
                "requesting the zone status",
                self._gateway_handler.log_id,
                self._where,
                hvac_mode,
                target_temperature,
            )
            await self.async_update()

        await self._gateway_handler.send(
            OWNHeatingCommand.set_temperature(
                where=self._where,
                temperature=target_temperature,
                mode=CLIMATE_MODE_HEAT if hvac_mode == HVACMode.HEAT else CLIMATE_MODE_COOL,
                standalone=self._standalone,
            )
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new target temperature."""
        # sc-16: `temperature` is guaranteed by HA for TARGET_TEMPERATURE entities, but a
        # direct call without it used to raise TypeError on `None - offset`.
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            temperature = self._local_target_temperature
        if temperature is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="climate_no_target_temperature",
                translation_placeholders={"entity_id": str(self.entity_id)},
            )

        target_temperature = float(temperature) - self._local_offset
        if self._attr_hvac_mode == HVACMode.HEAT:
            mode = CLIMATE_MODE_HEAT
        elif self._attr_hvac_mode == HVACMode.COOL:
            mode = CLIMATE_MODE_COOL
        else:
            mode = CLIMATE_MODE_AUTO

        await self._gateway_handler.send(
            OWNHeatingCommand.set_temperature(
                where=self._where,
                temperature=target_temperature,
                mode=mode,
                standalone=self._standalone,
            )
        )

    # ------------------------------------------------------------------ events
    @callback
    def _async_apply_mode(self, message: OWNHeatingEvent) -> None:
        """Apply a MODE / MODE_TARGET frame to the entity state."""
        hvac_mode = _OWN_MODE_TO_HVAC.get(message.mode)
        if hvac_mode is None or (
            hvac_mode is not HVACMode.OFF and hvac_mode not in self._attr_hvac_modes
        ):
            # sc-08: an unsupported mode must not leave the entity stale forever.
            LOGGER.debug(
                "%s Zone %s reported unsupported mode %s",
                self._gateway_handler.log_id,
                self._where,
                message.mode,
            )
            return
        LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
        self._attr_hvac_mode = hvac_mode

    @callback
    def _async_derive_hvac_action(self) -> None:
        """Derive hvac_action when the zone has not reported its actuators yet (sc-19)."""
        if self._attr_hvac_mode is None:
            return
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_action = HVACAction.OFF
            return
        if self._action_reported:
            # A real valve/actuator frame is authoritative.
            if self._attr_hvac_action == HVACAction.OFF:
                self._attr_hvac_action = HVACAction.IDLE
            return

        current = self._attr_current_temperature
        target = self.target_temperature
        if current is None or target is None:
            self._attr_hvac_action = HVACAction.IDLE
            return
        heating = self._attr_hvac_mode == HVACMode.HEAT or (
            self._attr_hvac_mode == HVACMode.AUTO and self._heating and not self._cooling
        )
        cooling = self._attr_hvac_mode == HVACMode.COOL or (
            self._attr_hvac_mode == HVACMode.AUTO and self._cooling and not self._heating
        )
        if heating:
            self._attr_hvac_action = (
                HVACAction.HEATING if current < target else HVACAction.IDLE
            )
        elif cooling:
            self._attr_hvac_action = (
                HVACAction.COOLING if current > target else HVACAction.IDLE
            )
        else:
            self._attr_hvac_action = HVACAction.IDLE

    def handle_event(self, message: OWNHeatingEvent) -> None:
        """Handle an event message."""
        if message.message_type == MESSAGE_TYPE_MAIN_TEMPERATURE:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            self._attr_current_temperature = message.main_temperature
        elif message.message_type == MESSAGE_TYPE_MAIN_HUMIDITY:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            self._attr_current_humidity = message.main_humidity
        elif message.message_type == MESSAGE_TYPE_TARGET_TEMPERATURE:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            self._target_temperature = message.set_temperature
            self._local_target_temperature = self._target_temperature + self._local_offset
        elif message.message_type == MESSAGE_TYPE_LOCAL_OFFSET:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            self._local_offset = message.local_offset
            if self._target_temperature is not None:
                self._local_target_temperature = self._target_temperature + self._local_offset
        elif message.message_type == MESSAGE_TYPE_LOCAL_TARGET_TEMPERATURE:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            self._local_target_temperature = message.local_set_temperature
            self._target_temperature = self._local_target_temperature - self._local_offset
        elif message.message_type == MESSAGE_TYPE_MODE:
            self._async_apply_mode(message)
        elif message.message_type == MESSAGE_TYPE_MODE_TARGET:
            self._async_apply_mode(message)
            if message.set_temperature is not None:
                self._target_temperature = message.set_temperature
                self._local_target_temperature = self._target_temperature + self._local_offset
        elif message.message_type == MESSAGE_TYPE_ACTION:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)
            self._action_reported = True
            if message.is_active():
                if self._heating and self._cooling:
                    if message.is_heating():
                        self._attr_hvac_action = HVACAction.HEATING
                    elif message.is_cooling():
                        self._attr_hvac_action = HVACAction.COOLING
                elif self._heating:
                    self._attr_hvac_action = HVACAction.HEATING
                elif self._cooling:
                    self._attr_hvac_action = HVACAction.COOLING
            elif self._attr_hvac_mode == HVACMode.OFF:
                self._attr_hvac_action = HVACAction.OFF
            else:
                self._attr_hvac_action = HVACAction.IDLE
        else:
            return

        self._async_derive_hvac_action()
        self.async_write_ha_state()
