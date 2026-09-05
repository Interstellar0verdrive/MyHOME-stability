"""Support for MyHOME lights (WHO 1 actuators and dimmers)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_FLASH,
    ATTR_TRANSITION,
    DOMAIN as PLATFORM,
    FLASH_LONG,
    FLASH_SHORT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from OWNd.message import (
    OWNLightingCommand,
    OWNLightingEvent,
)

from .const import (
    CONF_BUS_INTERFACE,
    CONF_DEVICE_MODEL,
    CONF_DIMMABLE,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
    CONF_ICON,
    CONF_ICON_ON,
    CONF_MANUFACTURER,
    CONF_PLATFORMS,
    CONF_WHERE,
    CONF_WHO,
    DOMAIN,
    LOGGER,
)
from .gateway import MyHOMEGatewayHandler
from .myhome_device import MyHOMEEntity, address_attributes


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the light entities of this gateway (none when unconfigured)."""
    configured_lights = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS].get(PLATFORM, {})
    if not configured_lights:
        return

    gateway_handler = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_ENTITY]
    lights = [
        MyHOMELight(
            hass=hass,
            device_id=device_id,
            who=cfg[CONF_WHO],
            where=cfg[CONF_WHERE],
            icon=cfg[CONF_ICON],
            icon_on=cfg[CONF_ICON_ON],
            interface=cfg.get(CONF_BUS_INTERFACE),
            name=cfg[CONF_NAME],
            entity_name=cfg[CONF_ENTITY_NAME],
            dimmable=cfg[CONF_DIMMABLE],
            manufacturer=cfg[CONF_MANUFACTURER],
            model=cfg[CONF_DEVICE_MODEL],
            gateway=gateway_handler,
        )
        for device_id, cfg in configured_lights.items()
    ]

    async_add_entities(lights)


def eight_bits_to_percent(value: int) -> int:
    """Convert an HA brightness (0-255) to an OpenWebNet level (0-100).

    Any strictly positive brightness maps to at least 1 %: HA sends brightness 1 for
    the lowest slider position and for `brightness_step` results, and rounding those
    down to 0 used to switch the light off instead of dimming it (plat-06).
    """
    if value <= 0:
        return 0
    return max(1, round(value * 100 / 255))


def percent_to_eight_bits(value: int) -> int:
    """Convert an OpenWebNet level (0-100) to an HA brightness (0-255)."""
    return int(round(255 / 100 * value, 0))


def transition_to_speed(seconds: float | None) -> int | None:
    """Map the HA `transition` (seconds) to an OpenWebNet dimming speed step.

    OpenWebNet encodes the fade as a 0-255 "speed" index whose unit is not
    specified by the protocol; seconds are used 1:1 and clamped, so that a large
    `transition:` is no longer silently dropped by OWNd (plat-13).
    """
    if seconds is None:
        return None
    return max(0, min(255, int(round(float(seconds)))))


def message_is_on(message: OWNLightingEvent) -> bool | None:
    """Return `message.is_on`, or None when the frame carries no state.

    `OWNLightingEvent.is_on` compares `None < 32` for dimension replies that do not
    set a state (timer, PIR sensitivity, illuminance, motion timeout) and raises
    TypeError; those frames must not reach (nor kill) the entity (plat-03).
    """
    try:
        return bool(message.is_on)
    except TypeError:
        return None


class MyHOMELight(MyHOMEEntity, LightEntity):
    """A light or dimmer on the OpenWebNet bus."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        entity_name: str | None,
        icon: str | None,
        icon_on: str | None,
        device_id: str,
        who: str,
        where: str,
        interface: str | None,
        dimmable: bool,
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
            entity_name=entity_name,
        )

        self._interface = interface
        self._full_where = f"{self._where}#4#{self._interface}" if self._interface is not None else self._where

        self._attr_supported_features = LightEntityFeature(0)
        self._attr_supported_color_modes: set[ColorMode] = set()

        if dimmable:
            self._attr_supported_color_modes.add(ColorMode.BRIGHTNESS)
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_features |= LightEntityFeature.TRANSITION
        else:
            self._attr_supported_color_modes.add(ColorMode.ONOFF)
            self._attr_color_mode = ColorMode.ONOFF
            # FLASH is implemented below through the OpenWebNet blinking WHATs
            # (*1*2x*where##); dimmers use the transition instead.
            self._attr_supported_features |= LightEntityFeature.FLASH

        self._attr_extra_state_attributes = address_attributes(where, self._interface)

        self._on_icon = icon_on
        self._off_icon = icon

        if self._off_icon is not None:
            self._attr_icon = self._off_icon

        self._attr_is_on = None
        self._attr_brightness = None

    async def async_update(self) -> None:
        """Ask the gateway for the current state (also called on entity add)."""
        if ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            await self._gateway_handler.send_status_request(OWNLightingCommand.get_brightness(self._full_where))
        else:
            await self._gateway_handler.send_status_request(OWNLightingCommand.status(self._full_where))

    async def _async_flash(self, flash: str) -> bool:
        """Blink the light (FLASH_SHORT -> 0.5 s, FLASH_LONG -> 1.5 s)."""
        frequency = 1.5 if flash == FLASH_LONG else 0.5
        return await self._gateway_handler.send(OWNLightingCommand.flash(self._full_where, frequency))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        if ATTR_FLASH in kwargs and self._attr_supported_features & LightEntityFeature.FLASH:
            if kwargs[ATTR_FLASH] in (FLASH_SHORT, FLASH_LONG):
                await self._async_flash(kwargs[ATTR_FLASH])
                return

        transition = (
            transition_to_speed(kwargs.get(ATTR_TRANSITION))
            if self._attr_supported_features & LightEntityFeature.TRANSITION
            else None
        )

        if ATTR_BRIGHTNESS in kwargs and ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            percent_brightness = eight_bits_to_percent(kwargs[ATTR_BRIGHTNESS])
            if percent_brightness == 0:
                # Only reachable when HA explicitly asks for brightness 0.
                await self.async_turn_off(**kwargs)
                return
            await self._gateway_handler.send(
                OWNLightingCommand.set_brightness(self._full_where, percent_brightness, transition or 0)
            )
            return

        if transition is not None:
            await self._gateway_handler.send(OWNLightingCommand.switch_on(self._full_where, transition))
            return

        await self._gateway_handler.send(OWNLightingCommand.switch_on(self._full_where))
        if ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            # Dimmers answer a plain ON with a state frame only; ask for the level.
            await self.async_update()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        if ATTR_FLASH in kwargs and self._attr_supported_features & LightEntityFeature.FLASH:
            if kwargs[ATTR_FLASH] in (FLASH_SHORT, FLASH_LONG):
                await self._async_flash(kwargs[ATTR_FLASH])
                return

        transition = (
            transition_to_speed(kwargs.get(ATTR_TRANSITION))
            if self._attr_supported_features & LightEntityFeature.TRANSITION
            else None
        )
        if transition is not None:
            await self._gateway_handler.send(OWNLightingCommand.switch_off(self._full_where, transition))
            return

        await self._gateway_handler.send(OWNLightingCommand.switch_off(self._full_where))

    def handle_event(self, message: OWNLightingEvent) -> None:
        """Handle an event message (must never raise: it runs in the event loop)."""
        try:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)

            is_on = message_is_on(message)
            if is_on is None:
                # Dimension reply without state (timer/PIR/illuminance/timeout).
                return
            self._attr_is_on = is_on

            if ColorMode.BRIGHTNESS in self._attr_supported_color_modes and message.brightness is not None:
                self._attr_brightness = percent_to_eight_bits(message.brightness)

            if self._off_icon is not None and self._on_icon is not None:
                self._attr_icon = self._on_icon if self._attr_is_on else self._off_icon
        except Exception:  # pragma: no cover - defensive, keeps the session alive
            LOGGER.exception("%s Error handling light event %s", self._gateway_handler.log_id, message)
            return

        self.async_schedule_update_ha_state()
