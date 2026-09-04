"""Base entity shared by every MyHOME platform (Contract C)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gateway import MyHOMEGatewayHandler

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    CONF_ENTITIES,
    CONF_PLATFORMS,
    DEFAULT_MANUFACTURER,
    DOMAIN,
    SIGNAL_GATEWAY_CONNECTION,
)


class MyHOMEEntity(Entity):
    """Common behaviour for all MyHOME entities.

    - never polled, `has_entity_name` on;
    - device info links the actuator to the gateway device with `via_device_id`
      (`gateway.device_id` is set by `__init__.async_setup_entry` before the
      platforms are forwarded);
    - `available` mirrors the gateway event session (`gateway.is_connected`) and
      is refreshed through the SIGNAL_GATEWAY_CONNECTION dispatcher signal;
    - the entity registers itself in `hass.data[DOMAIN][mac][CONF_PLATFORMS]`
      so the gateway dispatcher can find it, and unregisters on removal.

    Platforms must not override `available`, `device_info`, `should_poll` or
    `has_entity_name`.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        platform: str,
        device_id: str,
        who: str,
        where: str,
        manufacturer: str | None,
        model: str | None,
        gateway: MyHOMEGatewayHandler,
    ) -> None:
        self._hass = hass
        self._platform = platform
        self._who = who
        self._where = where
        self._device_id = device_id
        self._attr_unique_id = f"{gateway.mac}-{self._device_id}"
        self._manufacturer = manufacturer or DEFAULT_MANUFACTURER
        self._model = model
        self._gateway_handler = gateway
        # Main entity of a device takes the device name; platforms set
        # `_attr_name = entity_name` when the YAML provides one.
        self._attr_name = None
        self._connection_unsub_registered = False

        device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{gateway.mac}-{self._device_id}")},
            name=name,
            manufacturer=self._manufacturer,
            model=self._model,
        )
        # Contract B/C: the gateway handler exposes the registry id of the gateway
        # device; fall back gracefully if it is not set (e.g. in unit tests).
        via_device_id = getattr(gateway, "device_id", None)
        if via_device_id:
            device_info["via_device_id"] = via_device_id
        self._attr_device_info = device_info

    # ------------------------------------------------------------------ availability
    @property
    def available(self) -> bool:
        """Entity is available only while the gateway event session is alive."""
        return bool(getattr(self._gateway_handler, "is_connected", False))

    @callback
    def _async_on_connection_change(self, connected: bool) -> None:
        """Gateway connection state changed: push the new availability to HA."""
        self.async_write_ha_state()

    @callback
    def _async_subscribe_connection_signal(self) -> None:
        """Subscribe (once) to the gateway connection signal."""
        if self._connection_unsub_registered:
            return
        self._connection_unsub_registered = True
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_GATEWAY_CONNECTION.format(mac=self._gateway_handler.mac),
                self._async_on_connection_change,
            )
        )

    async def async_internal_added_to_hass(self) -> None:
        """Framework hook: guarantees the connection subscription even when a
        platform overrides `async_added_to_hass` without calling super()."""
        await super().async_internal_added_to_hass()
        self._async_subscribe_connection_signal()

    # ------------------------------------------------------------------ registration
    def _entities_registry(self) -> dict | None:
        """Return the `entities` dict of this device in hass.data, if present."""
        try:
            return self._hass.data[DOMAIN][self._gateway_handler.mac][CONF_PLATFORMS][
                self._platform
            ][self._device_id][CONF_ENTITIES]
        except KeyError:
            return None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        self._async_subscribe_connection_signal()
        entities = self._entities_registry()
        if entities is not None:
            entities[self._platform] = self
        await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        """When entity is removed from hass."""
        entities = self._entities_registry()
        if entities is not None and entities.get(self._platform) is self:
            del entities[self._platform]
