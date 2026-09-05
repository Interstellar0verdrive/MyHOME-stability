"""Base entity shared by every MyHOME platform (Contract C)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .gateway import MyHOMEGatewayHandler

from homeassistant.const import EntityCategory
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
    SIGNAL_GATEWAY_STATS,
)
from .validate import is_point_to_point


def address_attributes(where: str, interface: str | None) -> dict[str, str]:
    """Extra state attributes describing the bus address of an entity.

    `A`/`PL` only make sense for a point-to-point WHERE; General, Area and Group
    WHEREs are reported verbatim instead of being cut in half (plat-10).  The bus
    interface, when configured, is exposed as `Int`.
    """
    if is_point_to_point(where):
        attributes = {"A": where[: len(where) // 2], "PL": where[len(where) // 2 :]}
    else:
        attributes = {"Where": where}
    if interface is not None:
        attributes["Int"] = interface
    return attributes


class MyHOMEEntity(Entity):
    """Common behaviour for all MyHOME entities.

    - never polled, `has_entity_name` on;
    - device info links the actuator to the gateway device with `via_device_id`
      (`gateway.device_id` is set by `__init__.async_setup_entry` before the
      platforms are forwarded);
    - `available` mirrors the gateway event session (`gateway.is_connected`) and
      is refreshed through the SIGNAL_GATEWAY_CONNECTION dispatcher signal;
    - the entity registers itself in `hass.data[DOMAIN][mac][CONF_PLATFORMS]`
      under its `entity_slot` so the gateway dispatcher can find it, and
      unregisters on removal;
    - naming: `_attr_name` is the YAML `entity_name` when given; otherwise an
      entity that declares `_attr_translation_key` (secondary entities: Power,
      Energy today, Lock...) is named by its translation and the attribute is
      left unset, while the main entity of a device gets `_attr_name = None`
      (= the device name; the explicit None stops HA from falling back to the
      device-class name such as "Temperature").  Set `_attr_translation_key`
      before calling `super().__init__()` when it is an instance attribute.

    Platforms must not override `available`, `device_info`, `should_poll` or
    `has_entity_name`.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True

    # Key under which the entity registers itself in the device's `entities` dict.
    # None -> the platform name (one entity per device).  Devices hosting several
    # entities (energy meters, lock/unlock buttons) override it per entity so that
    # the gateway dispatcher (`_entities_for`, `_refresh_light`) finds all of them.
    _entity_slot: str | None = None

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
        entity_name: str | None = None,
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
        if entity_name:
            self._attr_name = entity_name
        elif not getattr(self, "_attr_translation_key", None):
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
        """Gateway connection state changed: push the new availability to HA.

        Subclasses that must re-issue a bus request on reconnection override this
        (keeping the `@callback` decorator) and call `super()`.
        """
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
    @property
    def entity_slot(self) -> str:
        """Registry slot of this entity in the device's `entities` dict."""
        return self._entity_slot or self._platform

    def _entities_registry(self) -> dict | None:
        """Return the `entities` dict of this device in hass.data, if present."""
        try:
            return self._hass.data[DOMAIN][self._gateway_handler.mac][CONF_PLATFORMS][
                self._platform
            ][self._device_id][CONF_ENTITIES]
        except KeyError:
            return None

    async def async_added_to_hass(self) -> None:
        """Subscribe, register in hass.data and send the first status request.

        `async_update` is optional: platforms whose devices cannot be queried
        (buttons, WHO 9 auxiliary channels) simply do not define it.
        """
        self._async_subscribe_connection_signal()
        entities = self._entities_registry()
        if entities is not None:
            entities[self.entity_slot] = self
        if hasattr(self, "async_update"):
            await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        """When entity is removed from hass."""
        entities = self._entities_registry()
        if entities is not None and entities.get(self.entity_slot) is self:
            del entities[self.entity_slot]


class MyHOMEGatewayDiagnosticEntity(Entity):
    """Base class of the diagnostic entities of the *gateway* device (0.3.0, G1-B).

    These entities describe the health of the connection itself, so they differ from
    every other entity of the integration and do NOT derive from `MyHOMEEntity`:

    - they belong to the gateway device (`identifiers={(DOMAIN, mac)}`), not to a bus
      device, and carry no WHO/WHERE;
    - they are not registered in `hass.data[...][CONF_ENTITIES]`: no bus frame is ever
      dispatched to them, they are fed by the `SIGNAL_GATEWAY_STATS` snapshots;
    - they stay **available while the gateway is down**, which is exactly when the user
      needs to read them (an "unavailable" connectivity sensor would be useless).

    Subclasses implement `_apply_stats()` and are created by the sensor and
    binary_sensor platforms even when no device of that platform is configured.
    """

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        gateway: MyHOMEGatewayHandler,
        unique_id_suffix: str,
        translation_key: str,
    ) -> None:
        self._gateway_handler = gateway
        self._attr_unique_id = f"{gateway.mac}-{unique_id_suffix}"
        self._attr_translation_key = translation_key
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, gateway.mac)})

    @property
    def available(self) -> bool:
        """Diagnostic entities never go unavailable (see the class docstring)."""
        return True

    async def async_added_to_hass(self) -> None:
        """Subscribe to the stats signal and take the current snapshot."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_GATEWAY_STATS.format(mac=self._gateway_handler.mac),
                self._async_stats_updated,
            )
        )
        # Contract: `handler.stats` always holds the latest snapshot; `getattr` keeps
        # the platforms working against a gateway build without it.
        stats = getattr(self._gateway_handler, "stats", None)
        if stats is not None:
            self._apply_stats(stats)

    @callback
    def _async_stats_updated(self, stats: Any) -> None:
        """A fresh GatewayStats snapshot was published."""
        self._apply_stats(stats)
        self.async_write_ha_state()

    @callback
    def _apply_stats(self, stats: Any) -> None:
        """Copy the fields this entity exposes out of the snapshot."""
        raise NotImplementedError
