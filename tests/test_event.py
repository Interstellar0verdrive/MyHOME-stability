"""Tests for the CEN / CEN+ scenario-control event entities (0.4.0).

The entities are fed the way the gateway feeds them in production: a raw OpenWebNet
frame goes through ``MyHOMEGatewayHandler._dispatch_message``, which fires the bus
event *and* pushes the press into the entity.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import ATTR_EVENT_TYPE, ATTR_EVENT_TYPES, DOMAIN as EVENT
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from OWNd.message import OWNEvent

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import (
    CONF_ENTITY,
    CONF_PLATFORMS,
    DOMAIN,
    EVENT_CEN,
    EVENT_CENPLUS,
    SCENARIO_CONTROL_EVENT_TYPES,
)

from .helpers_core import MAC
from .helpers_platforms import GATEWAY_DIAG_UNIQUE_IDS, device_config, entity_object, setup_myhome

SCENARIO_YAML = f"""
gateway:
  mac: {MAC}
  scenario_control:
    keypad_soggiorno:
      object: 25
      name: Keypad Soggiorno
      buttons: [1, 2, 3, 4]
    keypad_ingresso:
      protocol: cen
      where: '51'
      name: Keypad Ingresso
      buttons: [0, 1]
  light:
    light_test:
      where: '11'
      name: Light Test
"""


def _capture(hass: HomeAssistant, event_type: str) -> list[dict[str, Any]]:
    """Record the payloads of a bus event for the duration of the test."""
    seen: list[dict[str, Any]] = []
    hass.bus.async_listen(event_type, lambda event: seen.append(dict(event.data)))
    return seen


async def feed_frame(hass: HomeAssistant, frame: str) -> None:
    """Push a raw frame through the gateway dispatcher, as the monitor session does."""
    handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
    message = OWNEvent.parse(frame)
    assert message is not None, frame
    await handler._dispatch_message(message, from_monitor=True)  # noqa: SLF001
    await hass.async_block_till_done()


# --------------------------------------------------------------------------- creation
async def test_entities_and_devices_are_created(hass: HomeAssistant, tmp_path) -> None:
    """One device and one event entity per declared control, with our unique ids."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        entity_registry = er.async_get(hass)
        events = [
            item
            for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            if item.domain == EVENT
        ]
        assert {item.unique_id for item in events} == {
            f"{MAC}-cenplus-25-event",
            f"{MAC}-cen-51-event",
        }
        assert {item.translation_key for item in events} == {"scenario_control"}

        # __init__.expected_unique_ids must agree, or a restart would prune them.
        platforms = hass.data[DOMAIN][MAC][CONF_PLATFORMS]
        assert {item.unique_id for item in events} == expected_unique_ids(
            MAC, {EVENT: platforms[EVENT]}
        ) - GATEWAY_DIAG_UNIQUE_IDS

        device_registry = dr.async_get(hass)
        gateway_device = device_registry.async_get_device_by_identifier((DOMAIN, MAC), entry.entry_id)
        for key, model in (("cenplus-25", "CEN+ scenario control"), ("cen-51", "CEN scenario control")):
            device = device_registry.async_get_device_by_identifier((DOMAIN, f"{MAC}-{key}"), entry.entry_id)
            assert device is not None, key
            assert device.model == model
            # Contract C: the control hangs off the gateway device.
            assert device.via_device_id == gateway_device.id


async def test_no_event_platform_without_scenario_controls(hass: HomeAssistant, tmp_path) -> None:
    yaml_text = f"""
gateway:
  mac: {MAC}
  light:
    light_test:
      where: '11'
      name: Light Test
"""
    async with setup_myhome(hass, tmp_path, yaml_text) as (entry, _commands):
        entity_registry = er.async_get(hass)
        assert not [
            item
            for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            if item.domain == EVENT
        ]
        assert EVENT not in hass.data[DOMAIN][MAC][CONF_PLATFORMS]


async def test_event_types_and_static_attributes(hass: HomeAssistant, tmp_path) -> None:
    """Each protocol advertises exactly the event names gateway.py can produce."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        cenplus = hass.states.get("event.keypad_soggiorno_scenario_control")
        cen = hass.states.get("event.keypad_ingresso_scenario_control")
        assert cenplus is not None and cen is not None
        assert cenplus.state == STATE_UNKNOWN
        assert cenplus.attributes[ATTR_EVENT_TYPES] == list(SCENARIO_CONTROL_EVENT_TYPES["cen_plus"])
        assert cen.attributes[ATTR_EVENT_TYPES] == list(SCENARIO_CONTROL_EVENT_TYPES["cen"])
        # CEN+ controls are addressed by object, CEN controls by WHERE.
        assert cenplus.attributes["protocol"] == "cen_plus"
        assert cenplus.attributes["object"] == 25
        assert "where" not in cenplus.attributes
        assert cenplus.attributes["buttons"] == [1, 2, 3, 4]
        assert cen.attributes["protocol"] == "cen"
        assert cen.attributes["where"] == "51"
        assert "object" not in cen.attributes


# --------------------------------------------------------------------------- events
async def test_cenplus_frames_fire_the_entity(hass: HomeAssistant, tmp_path) -> None:
    """*25*<what>#<button>*2<object>## (OWNd puts the object in WHERE[1:]) drives the CEN+ entity and the bus event."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        payloads = _capture(hass, EVENT_CENPLUS)

        await feed_frame(hass, "*25*21#3*225##")
        state = hass.states.get("event.keypad_soggiorno_scenario_control")
        assert state.attributes[ATTR_EVENT_TYPE] == "pushbutton_short_press"
        assert state.attributes["pushbutton"] == 3
        first = state.state

        await feed_frame(hass, "*25*22#3*225##")
        state = hass.states.get("event.keypad_soggiorno_scenario_control")
        assert state.attributes[ATTR_EVENT_TYPE] == "pushbutton_long_press"
        assert state.state != first  # the state is the timestamp of the last press

        await feed_frame(hass, "*25*25#2*225##")
        state = hass.states.get("event.keypad_soggiorno_scenario_control")
        assert state.attributes[ATTR_EVENT_TYPE] == "rotate_cw_slow"
        assert state.attributes["pushbutton"] == 2

        assert [p["event"] for p in payloads] == [
            "pushbutton_short_press",
            "pushbutton_long_press",
            "rotate_cw_slow",
        ]


async def test_cen_frames_fire_the_entity(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        payloads = _capture(hass, EVENT_CEN)

        await feed_frame(hass, "*15*1*51##")
        state = hass.states.get("event.keypad_ingresso_scenario_control")
        assert state.attributes[ATTR_EVENT_TYPE] == "pushbutton_short_press"
        assert state.attributes["pushbutton"] == 1

        await feed_frame(hass, "*15*1#2*51##")
        state = hass.states.get("event.keypad_ingresso_scenario_control")
        assert state.attributes[ATTR_EVENT_TYPE] == "pushbutton_long_release"

        assert [p["object"] for p in payloads] == [51, 51]
        # The CEN+ entity is untouched by CEN traffic.
        assert hass.states.get("event.keypad_soggiorno_scenario_control").state == STATE_UNKNOWN


async def test_mac_is_in_both_bus_payloads(hass: HomeAssistant, tmp_path) -> None:
    """0.4.0: `mac` disambiguates multi-gateway setups (additive, documented)."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        cenplus = _capture(hass, EVENT_CENPLUS)
        cen = _capture(hass, EVENT_CEN)
        await feed_frame(hass, "*25*21#1*225##")
        await feed_frame(hass, "*15*1*51##")
        assert cenplus == [{"object": 25, "pushbutton": 1, "event": "pushbutton_short_press", "mac": MAC}]
        assert cen == [{"object": 51, "pushbutton": 1, "event": "pushbutton_short_press", "mac": MAC}]


async def test_undeclared_control_fires_the_bus_event_only(hass: HomeAssistant, tmp_path) -> None:
    """0.3.x behaviour is preserved for controls that are not in myhome.yaml."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        payloads = _capture(hass, EVENT_CENPLUS)
        await feed_frame(hass, "*25*21#1*299##")
        assert payloads == [{"object": 99, "pushbutton": 1, "event": "pushbutton_short_press", "mac": MAC}]
        # No entity was created for object 99, and the declared one did not move.
        assert hass.states.get("event.keypad_soggiorno_scenario_control").state == STATE_UNKNOWN


async def test_button_outside_the_declared_list_still_reported(hass: HomeAssistant, tmp_path) -> None:
    """`buttons` drives the trigger picker, it is not a filter on the bus."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        await feed_frame(hass, "*25*21#9*225##")
        state = hass.states.get("event.keypad_soggiorno_scenario_control")
        assert state.attributes["pushbutton"] == 9


async def test_unknown_event_name_is_ignored(hass: HomeAssistant, tmp_path) -> None:
    """A defensive guard: an event name the protocol does not declare never raises."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        entity = entity_object(hass, EVENT, "cen-51")
        entity.handle_scenario_event("pushbutton_long_press_repeat", 1)  # CEN+ only
        await hass.async_block_till_done()
        assert hass.states.get("event.keypad_ingresso_scenario_control").state == STATE_UNKNOWN


async def test_entity_registers_in_the_device_entities_slot(hass: HomeAssistant, tmp_path) -> None:
    """Contract C: the dispatcher finds the entity through hass.data."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        assert set(device_config(hass, EVENT, "cenplus-25")["entities"]) == {EVENT}
        assert entity_object(hass, EVENT, "cenplus-25").unique_id == f"{MAC}-cenplus-25-event"
