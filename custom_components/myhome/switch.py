"""Support for MyHOME switches (WHO 1 modules driving outlets or relays)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    DOMAIN as PLATFORM,
    SwitchDeviceClass,
    SwitchEntity,
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
    CONF_DEVICE_CLASS,
    CONF_DEVICE_MODEL,
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
from .myhome_device import MyHOMEEntity
from .gateway import MyHOMEGatewayHandler
from .validate import is_point_to_point


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the switch entities of this gateway (none when unconfigured)."""
    configured_switches = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS].get(PLATFORM, {})
    if not configured_switches:
        return

    gateway_handler = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_ENTITY]
    switches = [
        MyHOMESwitch(
            hass=hass,
            device_id=device_id,
            who=cfg[CONF_WHO],
            where=cfg[CONF_WHERE],
            icon=cfg[CONF_ICON],
            icon_on=cfg[CONF_ICON_ON],
            interface=cfg.get(CONF_BUS_INTERFACE),
            name=cfg[CONF_NAME],
            entity_name=cfg[CONF_ENTITY_NAME],
            device_class=cfg[CONF_DEVICE_CLASS],
            manufacturer=cfg[CONF_MANUFACTURER],
            model=cfg[CONF_DEVICE_MODEL],
            gateway=gateway_handler,
        )
        for device_id, cfg in configured_switches.items()
    ]

    async_add_entities(switches)


def message_is_on(message: OWNLightingEvent) -> bool | None:
    """Return `message.is_on`, or None when the frame carries no state (plat-03)."""
    try:
        return bool(message.is_on)
    except TypeError:
        return None


def address_attributes(where: str, interface: str | None) -> dict[str, str]:
    """`A`/`PL` for point-to-point WHEREs, plain `Where` otherwise (plat-10)."""
    if is_point_to_point(where):
        attributes = {"A": where[: len(where) // 2], "PL": where[len(where) // 2 :]}
    else:
        attributes = {"Where": where}
    if interface is not None:
        attributes["Int"] = interface
    return attributes


class MyHOMESwitch(MyHOMEEntity, SwitchEntity):
    """A WHO 1 module exposed as a switch (outlet / relay)."""

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
        device_class: SwitchDeviceClass | str | None,
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

        self._attr_name = entity_name

        self._interface = interface
        self._full_where = f"{self._where}#4#{self._interface}" if self._interface is not None else self._where

        self._attr_extra_state_attributes = address_attributes(where, self._interface)

        # Contract A guarantees a SwitchDeviceClass member; be forgiving anyway.
        try:
            self._attr_device_class = SwitchDeviceClass(str(device_class).lower())
        except ValueError:
            self._attr_device_class = SwitchDeviceClass.SWITCH

        self._on_icon = icon_on
        self._off_icon = icon

        if self._off_icon is not None:
            self._attr_icon = self._off_icon

        self._attr_is_on = None

    async def async_update(self) -> None:
        """Ask the gateway for the current state (also called on entity add).

        The status request must carry the bus interface, otherwise the reply is
        addressed to another entity and the switch stays `unknown` (plat-05).
        """
        await self._gateway_handler.send_status_request(OWNLightingCommand.status(self._full_where))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        await self._gateway_handler.send(OWNLightingCommand.switch_on(self._full_where))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        await self._gateway_handler.send(OWNLightingCommand.switch_off(self._full_where))

    def handle_event(self, message: OWNLightingEvent) -> None:
        """Handle an event message (must never raise: it runs in the event loop)."""
        try:
            label = "Outlet" if self._attr_device_class == SwitchDeviceClass.OUTLET else "Switch"
            LOGGER.debug(
                "%s %s",
                self._gateway_handler.log_id,
                message.human_readable_log.replace("Light", label),
            )

            is_on = message_is_on(message)
            if is_on is None:
                # Dimension reply without state (timer/PIR/illuminance/timeout).
                return
            self._attr_is_on = is_on

            if self._off_icon is not None and self._on_icon is not None:
                self._attr_icon = self._on_icon if self._attr_is_on else self._off_icon
        except Exception:  # pragma: no cover - defensive, keeps the session alive
            LOGGER.exception("%s Error handling switch event %s", self._gateway_handler.log_id, message)
            return

        self.async_schedule_update_ha_state()
