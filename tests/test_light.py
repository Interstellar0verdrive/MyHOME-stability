"""Tests for the MyHOME light platform."""

from __future__ import annotations

import pytest

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_SUPPORTED_COLOR_MODES,
    ATTR_TRANSITION,
    DOMAIN as LIGHT,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import CONF_PLATFORMS, DOMAIN
from custom_components.myhome.light import (
    eight_bits_to_percent,
    percent_to_eight_bits,
    transition_to_speed,
)

from .helpers_core import MAC
from .helpers_platforms import (
    GATEWAY_DIAG_UNIQUE_IDS,
    entity_object,
    feed_event,
    real_config_yaml,
    set_connected,
    setup_myhome,
)

DIMMER_YAML = f"""
gateway:
  mac: {MAC}
  light:
    dimmer_test:
      where: '11'
      name: Dimmer Test
      dimmable: true
    relay_bus:
      where: '23'
      interface: '01'
      name: Relay Bus
"""


def test_brightness_conversion() -> None:
    """plat-06: a strictly positive brightness never rounds down to 0."""
    assert eight_bits_to_percent(0) == 0
    assert eight_bits_to_percent(1) == 1
    assert eight_bits_to_percent(2) == 1
    assert eight_bits_to_percent(3) == 1
    assert eight_bits_to_percent(128) == 50
    assert eight_bits_to_percent(255) == 100
    assert percent_to_eight_bits(100) == 255
    assert percent_to_eight_bits(50) == 127


def test_transition_mapping() -> None:
    """plat-13: transitions are clamped into the OpenWebNet speed range."""
    assert transition_to_speed(None) is None
    assert transition_to_speed(0) == 0
    assert transition_to_speed(2.5) in (2, 3)
    assert transition_to_speed(300) == 255
    assert transition_to_speed(-5) == 0


async def test_real_config_creates_every_light(hass: HomeAssistant, tmp_path) -> None:
    """The user's 20 lights, with their icons, names and unique ids."""
    async with setup_myhome(hass, tmp_path, real_config_yaml()):
        entity_registry = er.async_get(hass)
        entries = [
            entry
            for entry in er.async_entries_for_config_entry(entity_registry, next(iter(hass.config_entries.async_entries(DOMAIN))).entry_id)
            if entry.domain == LIGHT
        ]
        assert len(entries) == 20

        platforms = hass.data[DOMAIN][MAC][CONF_PLATFORMS]
        assert {entry.unique_id for entry in entries} == expected_unique_ids(
            MAC, {LIGHT: platforms[LIGHT]}
        ) - GATEWAY_DIAG_UNIQUE_IDS

        state = hass.states.get("light.luce_cucina_centrale")
        assert state is not None
        assert state.attributes["friendly_name"] == "Luce Cucina Centrale"
        assert state.attributes["icon"] == "fapro:luce-cucina-centrale"
        assert state.attributes["A"] == "1"
        assert state.attributes["PL"] == "3"
        assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.ONOFF]


async def test_status_request_on_add_uses_full_where(hass: HomeAssistant, tmp_path) -> None:
    """Every light asks for its state on add; bus interfaces are part of the address."""
    async with setup_myhome(hass, tmp_path, DIMMER_YAML, clear_commands=False) as (_entry, commands):
        # A dimmer is asked for its brightness, a relay for its on/off state.
        assert "*#1*11*1##" in commands.status_frames
        assert "*#1*23#4#01##" in commands.status_frames


async def test_turn_on_off_and_brightness(hass: HomeAssistant, tmp_path) -> None:
    """plat-06: brightness 1 dims to 1 %, it does not switch the light off."""
    async with setup_myhome(hass, tmp_path, DIMMER_YAML) as (_entry, commands):
        await hass.services.async_call(
            LIGHT, "turn_on", {ATTR_ENTITY_ID: "light.dimmer_test", ATTR_BRIGHTNESS: 1}, blocking=True
        )
        assert commands.sent_frames == ["*#1*11*#1*101*0##"]

        commands.clear()
        await hass.services.async_call(
            LIGHT, "turn_on", {ATTR_ENTITY_ID: "light.dimmer_test", ATTR_BRIGHTNESS: 255}, blocking=True
        )
        assert commands.sent_frames == ["*#1*11*#1*200*0##"]

        commands.clear()
        await hass.services.async_call(
            LIGHT,
            "turn_on",
            {ATTR_ENTITY_ID: "light.dimmer_test", ATTR_BRIGHTNESS: 128, ATTR_TRANSITION: 4},
            blocking=True,
        )
        assert commands.sent_frames == ["*#1*11*#1*150*4##"]

        commands.clear()
        await hass.services.async_call(LIGHT, "turn_off", {ATTR_ENTITY_ID: "light.dimmer_test"}, blocking=True)
        assert commands.sent_frames == ["*1*0*11##"]

        commands.clear()
        await hass.services.async_call(LIGHT, "turn_on", {ATTR_ENTITY_ID: "light.relay_bus"}, blocking=True)
        assert commands.sent_frames == ["*1*1*23#4#01##"]


async def test_supported_features(hass: HomeAssistant, tmp_path) -> None:
    """Dimmers advertise TRANSITION + brightness, relays advertise FLASH."""
    async with setup_myhome(hass, tmp_path, DIMMER_YAML):
        dimmer = hass.states.get("light.dimmer_test")
        assert dimmer.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.BRIGHTNESS]
        assert dimmer.attributes[ATTR_SUPPORTED_FEATURES] == LightEntityFeature.TRANSITION

        relay = hass.states.get("light.relay_bus")
        assert relay.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.ONOFF]
        assert relay.attributes[ATTR_SUPPORTED_FEATURES] == LightEntityFeature.FLASH
        assert relay.attributes["Int"] == "01"


async def test_handle_event_updates_state(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, DIMMER_YAML):
        dimmer = entity_object(hass, LIGHT, "1-11")
        await feed_event(hass, dimmer, "*1*1*11##")
        assert hass.states.get("light.dimmer_test").state == STATE_ON

        await feed_event(hass, dimmer, "*#1*11*1*150*0##")
        state = hass.states.get("light.dimmer_test")
        assert state.state == STATE_ON
        assert state.attributes[ATTR_BRIGHTNESS] == 127

        await feed_event(hass, dimmer, "*1*0*11##")
        assert hass.states.get("light.dimmer_test").state == STATE_OFF


@pytest.mark.parametrize("frame", ["*#1*11*2*0*1*0##", "*#1*11*5*2##", "*#1*11*7*0*5*0##"])
async def test_dimension_replies_never_raise(hass: HomeAssistant, tmp_path, frame: str) -> None:
    """plat-03: `message.is_on` raises TypeError for stateless dimension replies."""
    async with setup_myhome(hass, tmp_path, DIMMER_YAML):
        dimmer = entity_object(hass, LIGHT, "1-11")
        await feed_event(hass, dimmer, "*1*1*11##")
        await feed_event(hass, dimmer, frame)
        # No exception, and the previous state survives.
        assert hass.states.get("light.dimmer_test").state == STATE_ON


async def test_availability_follows_connection_signal(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, DIMMER_YAML):
        assert hass.states.get("light.dimmer_test").state != STATE_UNAVAILABLE
        await set_connected(hass, False)
        assert hass.states.get("light.dimmer_test").state == STATE_UNAVAILABLE
        await set_connected(hass, True)
        assert hass.states.get("light.dimmer_test").state != STATE_UNAVAILABLE
