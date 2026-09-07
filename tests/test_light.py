"""Tests for the MyHOME light platform."""

from __future__ import annotations

import pytest
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_FLASH,
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
      icon: 'mdi:lightbulb-outline'
      icon_on: 'mdi:lightbulb'
    porch:
      where: '24'
      name: Porch
      icon_on: 'mdi:lightbulb-on'
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
            for entry in er.async_entries_for_config_entry(
                entity_registry, next(iter(hass.config_entries.async_entries(DOMAIN))).entry_id
            )
            if entry.domain == LIGHT
        ]
        assert len(entries) == 20

        platforms = hass.data[DOMAIN][MAC][CONF_PLATFORMS]
        assert {entry.unique_id for entry in entries} == expected_unique_ids(
            MAC, {LIGHT: platforms[LIGHT]}
        ) - GATEWAY_DIAG_UNIQUE_IDS

        state = hass.states.get("light.kitchen_ceiling")
        assert state is not None
        assert state.attributes["friendly_name"] == "Kitchen Ceiling"
        assert state.attributes["icon"] == "mdi:ceiling-light"
        assert state.attributes["A"] == "1"
        assert state.attributes["PL"] == "3"
        assert state.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.ONOFF]


async def test_status_request_on_add_uses_full_where(hass: HomeAssistant, tmp_path) -> None:
    """Every light asks for its state on add; bus interfaces are part of the address."""
    async with setup_myhome(hass, tmp_path, DIMMER_YAML, clear_commands=False) as (_entry, commands):
        # A dimmer is asked for its brightness, a relay for its on/off state.
        assert "*#1*11*1##" in commands.status_frames
        # 0.3.1: the interface goes on the bus unpadded, as OWNd 0.7.49 parses it back.
        assert "*#1*23#4#1##" in commands.status_frames


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
        assert commands.sent_frames == ["*1*1*23#4#1##"]


@pytest.mark.parametrize(
    ("flash", "frame"),
    [("short", "*1*20*23#4#1##"), ("long", "*1*22*23#4#1##")],
)
async def test_flash_uses_the_blinking_whats(hass: HomeAssistant, tmp_path, flash, frame) -> None:
    """F8: only the FLASH *feature bit* was asserted, never a frame.

    The two frequencies (0.5 s / 1.5 s) map to the OpenWebNet blinking WHATs 20 and 22;
    swapping them - or dropping the whole dispatch, so that flash degrades to a plain
    on/off - used to leave the suite green.
    """
    async with setup_myhome(hass, tmp_path, DIMMER_YAML) as (_entry, commands):
        await hass.services.async_call(
            LIGHT, "turn_on", {ATTR_ENTITY_ID: "light.relay_bus", ATTR_FLASH: flash}, blocking=True
        )
        assert commands.sent_frames == [frame]

        # turn_off with a flash blinks too, it does not switch the light off.
        commands.clear()
        await hass.services.async_call(
            LIGHT, "turn_off", {ATTR_ENTITY_ID: "light.relay_bus", ATTR_FLASH: flash}, blocking=True
        )
        assert commands.sent_frames == [frame]


async def test_transition_and_brightness_zero(hass: HomeAssistant, tmp_path) -> None:
    """F8 / NIT-3: the transition paths of a dimmer, none of which had a test."""
    async with setup_myhome(hass, tmp_path, DIMMER_YAML) as (_entry, commands):
        # ON with a transition and no brightness: the level is not part of the reply,
        # so the dimmer must ask for it (NIT-3: this path used to return right away and
        # keep a stale brightness).
        await hass.services.async_call(
            LIGHT,
            "turn_on",
            {ATTR_ENTITY_ID: "light.dimmer_test", ATTR_TRANSITION: 4},
            blocking=True,
        )
        assert commands.sent_frames == ["*1*1#4*11##"]
        assert commands.status_frames == ["*#1*11*1##"]

        # A plain ON asks for the level as well (the only way HA learns a dimmer's
        # brightness); the non-dimmable relay does not.
        commands.clear()
        await hass.services.async_call(
            LIGHT, "turn_on", {ATTR_ENTITY_ID: "light.dimmer_test"}, blocking=True
        )
        assert commands.sent_frames == ["*1*1*11##"]
        assert commands.status_frames == ["*#1*11*1##"]

        commands.clear()
        await hass.services.async_call(
            LIGHT, "turn_on", {ATTR_ENTITY_ID: "light.relay_bus"}, blocking=True
        )
        assert commands.status_frames == []

        # OFF with a transition.
        commands.clear()
        await hass.services.async_call(
            LIGHT,
            "turn_off",
            {ATTR_ENTITY_ID: "light.dimmer_test", ATTR_TRANSITION: 2},
            blocking=True,
        )
        assert commands.sent_frames == ["*1*0#2*11##"]

        # brightness 0 means "off", not "dim to 0 %".
        commands.clear()
        await hass.services.async_call(
            LIGHT,
            "turn_on",
            {ATTR_ENTITY_ID: "light.dimmer_test", ATTR_BRIGHTNESS: 0},
            blocking=True,
        )
        assert commands.sent_frames == ["*1*0*11##"]


async def test_icon_on_is_swapped_with_the_state(hass: HomeAssistant, tmp_path) -> None:
    """F8: `icon_on` had no fixture anywhere in the test suite."""
    async with setup_myhome(hass, tmp_path, DIMMER_YAML):
        relay = entity_object(hass, LIGHT, "1-23#4#01")
        assert hass.states.get("light.relay_bus").attributes["icon"] == "mdi:lightbulb-outline"
        await feed_event(hass, relay, "*1*1*23#4#1##")
        assert hass.states.get("light.relay_bus").attributes["icon"] == "mdi:lightbulb"
        await feed_event(hass, relay, "*1*0*23#4#1##")
        assert hass.states.get("light.relay_bus").attributes["icon"] == "mdi:lightbulb-outline"


async def test_icon_on_without_icon_is_applied(hass: HomeAssistant, tmp_path) -> None:
    """P2-INCONSISTENCY-1: `icon_on` alone was silently ignored on every platform.

    docs/configuration.md lists it as an independent key, so the pair is now read as
    "`icon_on` while on, `icon` otherwise" - and an absent `icon` means the icon Home
    Assistant would pick by itself, not "no icon swap at all".
    """
    async with setup_myhome(hass, tmp_path, DIMMER_YAML):
        porch = entity_object(hass, LIGHT, "1-24")
        assert "icon" not in hass.states.get("light.porch").attributes
        await feed_event(hass, porch, "*1*1*24##")
        assert hass.states.get("light.porch").attributes["icon"] == "mdi:lightbulb-on"
        await feed_event(hass, porch, "*1*0*24##")
        assert "icon" not in hass.states.get("light.porch").attributes


async def test_supported_features(hass: HomeAssistant, tmp_path) -> None:
    """Dimmers advertise TRANSITION + brightness, relays advertise FLASH."""
    async with setup_myhome(hass, tmp_path, DIMMER_YAML):
        dimmer = hass.states.get("light.dimmer_test")
        assert dimmer.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.BRIGHTNESS]
        assert dimmer.attributes[ATTR_SUPPORTED_FEATURES] == LightEntityFeature.TRANSITION

        relay = hass.states.get("light.relay_bus")
        assert relay.attributes[ATTR_SUPPORTED_COLOR_MODES] == [ColorMode.ONOFF]
        assert relay.attributes[ATTR_SUPPORTED_FEATURES] == LightEntityFeature.FLASH
        assert relay.attributes["Int"] == "1"


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
