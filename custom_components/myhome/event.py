"""Event entities for CEN / CEN+ scenario controls (0.4.0).

A wall keypad is stateless: nothing on the bus ever reports "button 3 is currently
pressed", only that it *was* pressed.  Home Assistant models exactly that with the
``event`` platform, so every control declared under ``scenario_control:`` in
``myhome.yaml`` becomes one device carrying one ``EventEntity`` whose state is the
timestamp of the last press and whose attributes say which button and which kind of
press it was.

Two things come out of that entity:

- the **device** exists in the registry even though no actuator answers for it, which
  is what ``device_trigger.py`` needs to offer "button 2 long press" in the automation
  editor (a stateless trigger-only device owning no entity would be pruned at every
  restart);
- the last press is visible in the state machine and in history, which a bus event
  alone never is.

Controls that are *not* declared in ``myhome.yaml`` are unaffected: their frames keep
firing ``myhome_cenplus_event`` / ``myhome_cen_event`` on the Home Assistant bus and
create no entity, exactly as in 0.3.x.

*The event-entity model is ported from ``adrael/MyHOME`` (`event.py`, doorbell), by
raphael, AGPL-3.0, adapted here to CEN/CEN+ and to our base
entity and dispatcher conventions.*
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .gateway import MyHOMEGatewayHandler

from homeassistant.components.event import (
    DOMAIN as PLATFORM,
    EventDeviceClass,
    EventEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BUTTONS,
    CONF_DEVICE_MODEL,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
    CONF_MANUFACTURER,
    CONF_OBJECT,
    CONF_PLATFORMS,
    CONF_PROTOCOL,
    CONF_SCENARIO_CONTROL,
    CONF_WHERE,
    CONF_WHO,
    DOMAIN,
    LOGGER,
    PROTOCOL_CEN_PLUS,
    SCENARIO_CONTROL_EVENT_TYPES,
)
from .myhome_device import MyHOMEEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one event entity per declared CEN/CEN+ scenario control."""
    configured = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS].get(PLATFORM, {})
    if not configured:
        return

    gateway_handler = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_ENTITY]
    async_add_entities(
        MyHOMEScenarioControl(
            hass=hass,
            device_id=device_id,
            who=cfg[CONF_WHO],
            where=cfg[CONF_WHERE],
            protocol=cfg[CONF_PROTOCOL],
            object_id=cfg[CONF_OBJECT],
            buttons=cfg[CONF_BUTTONS],
            name=cfg[CONF_NAME],
            entity_name=cfg[CONF_ENTITY_NAME],
            manufacturer=cfg[CONF_MANUFACTURER],
            model=cfg[CONF_DEVICE_MODEL],
            gateway=gateway_handler,
        )
        for device_id, cfg in configured.items()
    )


class MyHOMEScenarioControl(MyHOMEEntity, EventEntity):
    """The single event entity of one CEN / CEN+ scenario control.

    ``event_types`` are the protocol's event names, i.e. exactly the strings the
    gateway puts in the ``event`` key of ``myhome_cenplus_event`` /
    ``myhome_cen_event`` (``SCENARIO_CONTROL_EVENT_TYPES``), so an automation written
    against the bus event and one written against this entity speak the same language.
    """

    _attr_device_class = EventDeviceClass.BUTTON
    # Kept on purpose, although ``MyHOMEEntity`` reserves translation keys for
    # *secondary* entities and a scenario control owns exactly one entity: the key is
    # what makes the entity_id ``event.<name>_scenario_control``, which the docs, the
    # recipes and every existing user automation already name.  Dropping it (and
    # setting ``_attr_name = None``) would rename every user's entity and lose its
    # history, so it must never be "cleaned up" without a migration step.
    _attr_translation_key = CONF_SCENARIO_CONTROL

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        entity_name: str | None,
        device_id: str,
        who: str,
        where: str,
        protocol: str,
        object_id: int,
        buttons: list[int],
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
        # Unique ids must stay exactly as ``__init__.expected_unique_ids()`` builds them.
        self._attr_unique_id = f"{gateway.mac}-{self._device_id}-event"
        self._protocol = protocol
        self._object = object_id
        self._buttons = list(buttons)
        self._attr_event_types = list(SCENARIO_CONTROL_EVENT_TYPES[protocol])

        # Static attributes describing the control itself.  CEN+ controls are addressed
        # by object number, CEN controls by WHERE, so each protocol advertises the key
        # its users already know from the bus event / from the OpenWebNet frame.
        address_key = CONF_OBJECT if protocol == PROTOCOL_CEN_PLUS else CONF_WHERE
        self._attr_extra_state_attributes: dict[str, Any] = {
            CONF_PROTOCOL: protocol,
            address_key: object_id if address_key == CONF_OBJECT else where,
            CONF_BUTTONS: self._buttons,
        }

    def handle_scenario_event(self, event_type: str, pushbutton: int) -> None:
        """A CEN/CEN+ frame for this control arrived: publish it as an entity event.

        Called by the gateway dispatcher right after the matching bus event is fired.
        Buttons that are not in the configured ``buttons`` list are still reported —
        the list only drives which triggers the automation UI offers, it is not a
        filter on the bus.
        """
        if event_type not in self._attr_event_types:
            LOGGER.debug(
                "%s Ignoring %s event '%s' for %s", self._gateway_handler.log_id, self._protocol, event_type, self.unique_id
            )
            return
        self._trigger_event(event_type, {"pushbutton": int(pushbutton)})
        self.async_write_ha_state()
