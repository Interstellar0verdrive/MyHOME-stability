"""Device triggers for CEN / CEN+ scenario controls (0.4.0).

A scenario control is a wall keypad: it commands the bus directly and Home Assistant
only ever sees that a button *was* pressed.  Those presses reach the bus as
``myhome_cenplus_event`` / ``myhome_cen_event``, which have always been usable from
YAML; this module makes the same presses selectable from the automation **editor**,
as "Button 2 long press on Keypad Soggiorno", by attaching the core ``event`` trigger
under the hood.

The device the triggers hang off is created by ``event.py`` from the
``scenario_control:`` block of ``myhome.yaml``; ``async_get_triggers`` reads the
protocol and the object number back out of its registry identifier
(``{mac}-cenplus-{object}`` / ``{mac}-cen-{where}``, see ``const.scenario_control_key``)
and the configured button list out of ``hass.data``.

*Structure ported from ``fedem95/MyHOME`` (`device_trigger.py`), by fedem95
, AGPL-3.0: the base-schema extension, the type/subtype split and
the delegation to ``homeassistant.components.homeassistant.triggers.event`` with
``platform_type="device"`` are theirs.  Adapted here to our per-protocol event names
(including the long-press repeat and the four rotary events), to the YAML-declared
button list and to the ``mac`` key we added to the bus payloads.*
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.event import DOMAIN as EVENT
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_EVENT_DATA,
    CONF_PLATFORM,
    CONF_TYPE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_EVENT,
    ATTR_MAC,
    ATTR_PUSHBUTTON,
    CONF_BUTTONS,
    CONF_OBJECT,
    CONF_PLATFORMS,
    DEFAULT_SCENARIO_BUTTONS,
    DOMAIN,
    PROTOCOL_CEN,
    PROTOCOL_CEN_PLUS,
    SCENARIO_CONTROL_BUS_EVENT,
    SCENARIO_CONTROL_EVENT_TYPES,
    SCENARIO_SUBTYPE_PREFIX,
    scenario_control_key,
)

# Not a shared Home Assistant constant: every device-trigger platform defines its own.
CONF_SUBTYPE = "subtype"

# Every event name any protocol can produce; the schema accepts all of them and
# `async_get_triggers` only ever offers the ones the device's protocol supports.
ALL_TRIGGER_TYPES: set[str] = {
    event_type for types in SCENARIO_CONTROL_EVENT_TYPES.values() for event_type in types
}
# Subtypes must be a closed set for the schema: CEN+ buttons are 1-32, CEN 0-31.
ALL_SUBTYPES: list[str] = [f"{SCENARIO_SUBTYPE_PREFIX}{button}" for button in range(0, 33)]

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(ALL_TRIGGER_TYPES),
        vol.Required(CONF_SUBTYPE): vol.In(ALL_SUBTYPES),
    }
)


def _control_from_device(hass: HomeAssistant, device_id: str) -> tuple[str, str, int] | None:
    """Return ``(mac, protocol, object)`` when ``device_id`` is a scenario control.

    The registry identifier is ``{mac}-cenplus-{object}`` or ``{mac}-cen-{where}``; the
    MAC itself contains no dash in Home Assistant's canonical ``aa:bb:..`` form, but it
    is recovered with ``rpartition`` on the protocol marker anyway so an oddly
    normalised MAC cannot break the split.  ``cenplus`` is tested first: ``-cen-`` can
    never match ``-cenplus-``, but the order documents the intent.
    """
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    for domain, identifier in device.identifiers:
        if domain != DOMAIN:
            continue
        for protocol in (PROTOCOL_CEN_PLUS, PROTOCOL_CEN):
            marker = "-" + scenario_control_key(protocol, "")  # "-cenplus-" / "-cen-"
            mac, found, address = identifier.rpartition(marker)
            if found and address.isdigit():
                return mac, protocol, int(address)
    return None


def _buttons_for(hass: HomeAssistant, mac: str, protocol: str, object_id: int) -> list[int]:
    """Pushbuttons declared for this control, or the default list when it is not loaded.

    ``async_get_triggers`` is also called for a device whose config entry is unloaded
    (the automation editor lists triggers of disabled entries too), so a missing
    ``hass.data`` entry must degrade to the documented default, never raise.
    """
    try:
        device = hass.data[DOMAIN][mac][CONF_PLATFORMS][EVENT][scenario_control_key(protocol, object_id)]
        buttons = device[CONF_BUTTONS]
    except (KeyError, TypeError):
        return list(DEFAULT_SCENARIO_BUTTONS)
    return list(buttons) or list(DEFAULT_SCENARIO_BUTTONS)


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict[str, Any]]:
    """List the triggers a scenario control offers: one per (button, event type)."""
    control = _control_from_device(hass, device_id)
    if control is None:
        return []
    mac, protocol, object_id = control

    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: trigger_type,
            CONF_SUBTYPE: f"{SCENARIO_SUBTYPE_PREFIX}{button}",
        }
        for button in _buttons_for(hass, mac, protocol, object_id)
        for trigger_type in SCENARIO_CONTROL_EVENT_TYPES[protocol]
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE | None:
    """Attach the trigger to the CEN/CEN+ bus event it stands for.

    Delegating to the core ``event`` trigger with ``platform_type="device"`` keeps the
    automation traces attributed to the device trigger instead of to a raw event
    trigger, and means the matching logic itself is Home Assistant's, not ours.
    """
    control = _control_from_device(hass, config[CONF_DEVICE_ID])
    if control is None:
        return None
    mac, protocol, object_id = control
    pushbutton = int(config[CONF_SUBTYPE].removeprefix(SCENARIO_SUBTYPE_PREFIX))

    event_config = event_trigger.TRIGGER_SCHEMA(
        {
            event_trigger.CONF_PLATFORM: "event",
            event_trigger.CONF_EVENT_TYPE: SCENARIO_CONTROL_BUS_EVENT[protocol],
            CONF_EVENT_DATA: {
                # ``mac`` (added to the payload in 0.4.0) keeps two gateways that both
                # own object 25 apart; ``object`` carries the CEN WHERE for CEN too.
                ATTR_MAC: mac,
                CONF_OBJECT: object_id,
                ATTR_PUSHBUTTON: pushbutton,
                ATTR_EVENT: config[CONF_TYPE],
            },
        }
    )
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
