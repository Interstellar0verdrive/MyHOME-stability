"""Tests for the MyHOME switch platform."""

from __future__ import annotations

from homeassistant.components.switch import DOMAIN as SWITCH, SwitchDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import CONF_PLATFORMS, DOMAIN

from .helpers_core import MAC
from .helpers_platforms import GATEWAY_DIAG_UNIQUE_IDS, entity_object, feed_event, set_connected, setup_myhome

SWITCH_YAML = f"""
gateway:
  mac: {MAC}
  switch:
    presa_bus:
      where: '23'
      interface: '01'
      name: Presa Bus
      device_class: outlet
    rele_test:
      where: '31'
      name: Rele Test
"""


async def test_switches_created(hass: HomeAssistant, tmp_path) -> None:
    """Entities, device classes, address attributes and unique ids."""
    async with setup_myhome(hass, tmp_path, SWITCH_YAML) as (entry, _commands):
        entity_registry = er.async_get(hass)
        entries = [
            item
            for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            if item.domain == SWITCH
        ]
        assert len(entries) == 2
        platforms = hass.data[DOMAIN][MAC][CONF_PLATFORMS]
        assert {item.unique_id for item in entries} == expected_unique_ids(
            MAC, {SWITCH: platforms[SWITCH]}
        ) - GATEWAY_DIAG_UNIQUE_IDS
        assert {item.unique_id for item in entries} == {f"{MAC}-1-23#4#01", f"{MAC}-1-31"}

        outlet = hass.states.get("switch.presa_bus")
        assert outlet.attributes[ATTR_DEVICE_CLASS] == SwitchDeviceClass.OUTLET
        assert outlet.attributes["Int"] == "01"
        assert hass.states.get("switch.rele_test").attributes[ATTR_DEVICE_CLASS] == SwitchDeviceClass.SWITCH


async def test_status_request_uses_bus_interface(hass: HomeAssistant, tmp_path) -> None:
    """plat-05: the status request must carry `#4#<interface>`."""
    async with setup_myhome(hass, tmp_path, SWITCH_YAML, clear_commands=False) as (_entry, commands):
        assert "*#1*23#4#01##" in commands.status_frames
        assert "*#1*31##" in commands.status_frames


async def test_turn_on_off(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, SWITCH_YAML) as (_entry, commands):
        await hass.services.async_call(SWITCH, "turn_on", {ATTR_ENTITY_ID: "switch.presa_bus"}, blocking=True)
        assert commands.sent_frames == ["*1*1*23#4#01##"]
        commands.clear()
        await hass.services.async_call(SWITCH, "turn_off", {ATTR_ENTITY_ID: "switch.presa_bus"}, blocking=True)
        assert commands.sent_frames == ["*1*0*23#4#01##"]


async def test_handle_event_and_is_on_guard(hass: HomeAssistant, tmp_path) -> None:
    """plat-03: stateless dimension replies must not raise nor change the state."""
    async with setup_myhome(hass, tmp_path, SWITCH_YAML):
        switch = entity_object(hass, SWITCH, "1-31")
        await feed_event(hass, switch, "*1*1*31##")
        assert hass.states.get("switch.rele_test").state == STATE_ON

        await feed_event(hass, switch, "*#1*31*2*0*1*0##")
        assert hass.states.get("switch.rele_test").state == STATE_ON

        await feed_event(hass, switch, "*1*0*31##")
        assert hass.states.get("switch.rele_test").state == STATE_OFF


async def test_availability_follows_connection_signal(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, SWITCH_YAML):
        assert hass.states.get("switch.rele_test").state != STATE_UNAVAILABLE
        await set_connected(hass, False)
        assert hass.states.get("switch.rele_test").state == STATE_UNAVAILABLE
