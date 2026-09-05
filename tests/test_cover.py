"""Tests for the MyHOME cover platform (Contract F: time-based position)."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache,
)

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER,
    CoverDeviceClass,
    CoverEntityFeature,
    CoverState,
)
from homeassistant.const import (
    ATTR_ASSUMED_STATE,
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import CONF_PLATFORMS, DOMAIN

from .helpers_core import MAC
from .helpers_platforms import (
    device_config,
    entity_object,
    feed_event,
    real_config_yaml,
    set_connected,
    setup_myhome,
)

BASIC_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    tapparella_test:
      where: '81'
      name: Tapparella Test
      shutter_run: 30
      icon: mdi:window-shutter
"""

INVERTED_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    tapparella_inv:
      where: '82'
      name: Tapparella Inv
      shutter_run: 20
      inverted: true
"""

ADVANCED_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    tapparella_adv:
      where: '83'
      name: Tapparella Adv
      advanced: true
"""

ENTITY = "cover.tapparella_test"


async def _advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    """Move the (frozen) clock forward and let the scheduled callbacks run."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_real_config_creates_every_cover(hass: HomeAssistant, tmp_path) -> None:
    """The user's covers, with `class`, `icon` and `shutter_run` honoured (val-08)."""
    async with setup_myhome(hass, tmp_path, real_config_yaml()) as (entry, _commands):
        entity_registry = er.async_get(hass)
        entries = [
            item
            for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            if item.domain == COVER
        ]
        platforms = hass.data[DOMAIN][MAC][CONF_PLATFORMS]
        # One entity per configured cover, no duplicate WHERE swallowed silently.
        assert len(entries) == len(platforms[COVER])
        assert len(entries) >= 12
        assert {item.unique_id for item in entries} == expected_unique_ids(MAC, {COVER: platforms[COVER]})

        state = hass.states.get("cover.tapparella_cucina_1")
        assert state.attributes[ATTR_DEVICE_CLASS] == CoverDeviceClass.SHUTTER
        assert state.attributes["icon"] == "mdi:window-shutter"
        assert state.attributes[ATTR_ASSUMED_STATE] is True
        assert state.attributes["Shutter run"] == 30.0
        assert state.attributes[ATTR_SUPPORTED_FEATURES] == (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION
        )
        assert device_config(hass, COVER, "2-91")["shutter_run"] == 30.0


async def test_position_estimate_while_opening(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """plat-07: a basic cover estimates its position from `shutter_run`."""
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        await hass.services.async_call(COVER, "open_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*1*81##"]
        assert hass.states.get(ENTITY).state == CoverState.OPENING

        await _advance(hass, freezer, 15)
        # Unknown start position is assumed closed, so half a run is 50 %.
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 50

        # The actuator reports it stopped: freeze the estimate there.
        await feed_event(hass, entity_object(hass, COVER, "2-81"), "*2*0*81##")
        state = hass.states.get(ENTITY)
        assert state.state == CoverState.OPEN
        assert state.attributes[ATTR_CURRENT_POSITION] == 50

        await _advance(hass, freezer, 10)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 50


async def test_full_close_reaches_closed(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """After a full run the cover settles on closed, not on `unknown` (plat-07)."""
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*2*81##"]
        assert hass.states.get(ENTITY).state == CoverState.CLOSING

        await _advance(hass, freezer, 31)
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.state == CoverState.CLOSED
        # The actuator stops by itself: no stop command from us.
        assert commands.sent_frames == ["*2*2*81##"]


async def test_set_position_stops_on_time(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """Contract F: `set_cover_position` runs the cover and stops it with a timer."""
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100

        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
        )
        assert commands.sent_frames == ["*2*2*81##"]

        await _advance(hass, freezer, 10)
        assert commands.sent_frames == ["*2*2*81##"]
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 67

        # 60 % of a 30 s run = 18 s.
        await _advance(hass, freezer, 9)
        assert commands.sent_frames == ["*2*2*81##", "*2*0*81##"]
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 40
        assert state.state == CoverState.OPEN


async def test_stop_cancels_the_timer(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """A manual stop freezes the position and cancels the pending auto-stop."""
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 0}, blocking=True
        )
        await _advance(hass, freezer, 6)
        await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*2*81##", "*2*0*81##"]
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 80

        # The auto-stop must not fire afterwards.
        await _advance(hass, freezer, 60)
        assert commands.sent_frames == ["*2*2*81##", "*2*0*81##"]
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 80


async def test_inverted_flips_commands_and_events(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """`inverted: true` swaps the raise/lower semantics in both directions."""
    async with setup_myhome(hass, tmp_path, INVERTED_YAML) as (_entry, commands):
        entity_id = "cover.tapparella_inv"
        await hass.services.async_call(COVER, "open_cover", {ATTR_ENTITY_ID: entity_id}, blocking=True)
        assert commands.sent_frames == ["*2*2*82##"]
        assert hass.states.get(entity_id).state == CoverState.OPENING

        await _advance(hass, freezer, 21)
        assert hass.states.get(entity_id).attributes[ATTR_CURRENT_POSITION] == 100

        # The bus says "raising", which on an inverted actuator means closing.
        cover = entity_object(hass, COVER, "2-82")
        await feed_event(hass, cover, "*2*1*82##")
        assert hass.states.get(entity_id).state == CoverState.CLOSING
        await _advance(hass, freezer, 21)
        assert hass.states.get(entity_id).state == CoverState.CLOSED


async def test_position_restored_after_restart(hass: HomeAssistant, tmp_path) -> None:
    """The estimated position survives a restart (Contract F)."""
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 42}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 42
        assert state.state == CoverState.OPEN


async def test_position_survives_entry_reload(hass: HomeAssistant, tmp_path) -> None:
    """Reloading the config entry keeps the estimated position.

    On unload the gateway connection is closed before the entities are removed, so
    HA snapshots them as ``unavailable`` without attributes; the position must
    therefore travel through ``extra_restore_state_data``.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 42}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (entry, _commands):
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 42
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)
        state = hass.states.get(ENTITY)
        assert state.attributes.get(ATTR_CURRENT_POSITION) == 42
        assert state.state == CoverState.OPEN


async def test_advanced_cover_uses_real_positions(hass: HomeAssistant, tmp_path) -> None:
    """Advanced actuators report a real position (dimension 10, 0 = closed)."""
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        entity_id = "cover.tapparella_adv"
        assert hass.states.get(entity_id).attributes.get(ATTR_ASSUMED_STATE) is None

        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*10*42*0*0##")
        state = hass.states.get(entity_id)
        assert state.attributes[ATTR_CURRENT_POSITION] == 42
        assert state.state == CoverState.OPEN

        await feed_event(hass, cover, "*#2*83*10*10*0*0*0##")
        assert hass.states.get(entity_id).state == CoverState.CLOSED

        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: entity_id, ATTR_POSITION: 70}, blocking=True
        )
        assert commands.sent_frames == ["*#2*83*#11#001*70##"]


async def test_handle_event_never_raises(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")

        class _Broken:
            human_readable_log = "broken"
            is_opening = True
            is_closing = False
            is_closed = None

            @property
            def current_position(self):
                raise ValueError("boom")

        cover.handle_event(_Broken())
        await hass.async_block_till_done()
        assert hass.states.get(ENTITY) is not None


async def test_availability_follows_connection_signal(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        await set_connected(hass, False)
        assert hass.states.get(ENTITY).state == "unavailable"
        await set_connected(hass, True)
        assert hass.states.get(ENTITY).state != "unavailable"
