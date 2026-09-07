"""Tests for the MyHOME cover platform (Contract F: time-based position)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
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
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache,
)

from custom_components.myhome import cover as cover_module, expected_unique_ids
from custom_components.myhome.const import CONF_PLATFORMS, DOMAIN

from .helpers_core import MAC
from .helpers_platforms import (
    GATEWAY_DIAG_UNIQUE_IDS,
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
    cover_test:
      where: '81'
      name: Cover Test
      shutter_run: 30
      icon: mdi:window-shutter
"""

INVERTED_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_inverted:
      where: '82'
      name: Cover Inverted
      shutter_run: 20
      inverted: true
"""

ADVANCED_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_advanced:
      where: '83'
      name: Cover Advanced
      advanced: true
"""

# Two-phase travel (0.4.0): 3 s of slats, 27 s of curtain, in both directions.
SLAT_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_slats:
      where: '85'
      name: Cover Slats
      shutter_run: 30
      slat_time: 3
"""

# Same slat phase, but the motor is slower going up than coming down.
ASYMMETRIC_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_asymmetric:
      where: '86'
      name: Cover Asymmetric
      shutter_run: 30
      slat_time: 3
      opening_time: 32
      closing_time: 28
"""

ENTITY = "cover.cover_test"
SLAT_ENTITY = "cover.cover_slats"
ASYM_ENTITY = "cover.cover_asymmetric"


def _closed(entity_id: str = SLAT_ENTITY) -> State:
    """Restored state of a fully closed shutter: curtain down, slats closed."""
    return State(entity_id, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0, ATTR_CURRENT_TILT_POSITION: 0})


async def _advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    """Move the (frozen) clock forward and let the scheduled callbacks run.

    ``async_fire_time_changed`` bumps the mocked time by up to 0.5 s (it has to, for
    ``async_track_time_interval``'s random offset), so a timer fires as soon as the
    frozen clock is within half a second of its deadline: every "not fired yet"
    assertion below keeps a margin larger than that.
    """
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
        assert {item.unique_id for item in entries} == expected_unique_ids(
            MAC, {COVER: platforms[COVER]}
        ) - GATEWAY_DIAG_UNIQUE_IDS

        state = hass.states.get("cover.kitchen_shutter_1")
        assert state.attributes[ATTR_DEVICE_CLASS] == CoverDeviceClass.SHUTTER
        assert state.attributes["icon"] == "mdi:window-shutter"
        assert state.attributes[ATTR_ASSUMED_STATE] is True
        assert state.attributes["Shutter run"] == 30.0
        assert state.attributes[ATTR_SUPPORTED_FEATURES] == (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
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


async def test_inverted_flips_commands_and_events(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`inverted: true` swaps the raise/lower semantics in both directions."""
    async with setup_myhome(hass, tmp_path, INVERTED_YAML) as (_entry, commands):
        entity_id = "cover.cover_inverted"
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
        entity_id = "cover.cover_advanced"
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


# --------------------------------------------------------------------------------------
# Two-phase travel model: slat_time / opening_time / closing_time (0.4.0)
# --------------------------------------------------------------------------------------
async def test_slat_cover_advertises_tilt(hass: HomeAssistant, tmp_path) -> None:
    """`slat_time` adds the tilt feature set and the extra attributes."""
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML):
        state = hass.states.get(SLAT_ENTITY)
        assert state.state == CoverState.CLOSED
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 0
        assert state.attributes["Shutter run"] == 30.0
        assert state.attributes["Slat time"] == 3.0
        # Symmetric run: the per-direction attributes stay out of the way.
        assert "Opening time" not in state.attributes
        assert "Closing time" not in state.attributes
        assert state.attributes[ATTR_SUPPORTED_FEATURES] == (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.OPEN_TILT
            | CoverEntityFeature.CLOSE_TILT
            | CoverEntityFeature.SET_TILT_POSITION
            | CoverEntityFeature.STOP_TILT
        )


async def test_without_slat_time_nothing_changes(hass: HomeAssistant, tmp_path) -> None:
    """`slat_time: 0` (the default) keeps the plain 0.3.x linear model."""
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        state = hass.states.get(ENTITY)
        assert state.state == CoverState.CLOSED
        assert ATTR_CURRENT_TILT_POSITION not in state.attributes
        assert "Slat time" not in state.attributes
        assert state.attributes[ATTR_SUPPORTED_FEATURES] == (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )


async def test_set_position_5_from_closed_runs_through_the_slat_phase(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The ventilation gap: 3 s of slats + 5 % of the 27 s curtain run = 4.35 s."""
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_POSITION: 5}, blocking=True
        )
        assert commands.sent_frames == ["*2*1*85##"]

        # 2 s in: still inside the slat phase, the curtain has not moved yet.
        await _advance(hass, freezer, 2)
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 67
        assert state.state == CoverState.OPENING

        await _advance(hass, freezer, 1.7)  # 3.7 s: not there yet
        assert commands.sent_frames == ["*2*1*85##"]

        await _advance(hass, freezer, 0.7)  # 4.4 s > 3 + 0.05 * 27 = 4.35 s
        assert commands.sent_frames == ["*2*1*85##", "*2*0*85##"]
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 5
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100
        assert state.state == CoverState.OPEN


async def test_set_position_50_from_closed(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """Half open costs 3 + 13.5 s, not 15 s: the slat phase does not lift the curtain."""
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_POSITION: 50}, blocking=True
        )
        await _advance(hass, freezer, 15.9)
        assert commands.sent_frames == ["*2*1*85##"]

        await _advance(hass, freezer, 0.7)  # 16.6 s > 3 + 13.5 = 16.5 s
        assert commands.sent_frames == ["*2*1*85##", "*2*0*85##"]
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 50
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100


async def test_close_from_half_open_ends_with_the_slats_closed(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`close_cover` runs to the end stop: 13.5 s of curtain, then 3 s of slats."""
    mock_restore_cache(
        hass,
        (State(SLAT_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 50, ATTR_CURRENT_TILT_POSITION: 100}),),
    )
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*2*85##"]

        # 15.5 s: the curtain is down (13.5 s) but the slats are still closing.
        await _advance(hass, freezer, 15.5)
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 33
        assert state.state == CoverState.CLOSING

        await _advance(hass, freezer, 1.5)  # 17 s > 13.5 + 3
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 0
        assert state.state == CoverState.CLOSED
        # The actuator reaches its own end stop: no stop command from us.
        assert commands.sent_frames == ["*2*2*85##"]


async def test_open_and_close_tilt_from_closed(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """"Closed with the slats open": run up for `slat_time`, then stop."""
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        await hass.services.async_call(COVER, "open_cover_tilt", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*1*85##"]

        await _advance(hass, freezer, 2.4)
        assert commands.sent_frames == ["*2*1*85##"]
        assert hass.states.get(SLAT_ENTITY).attributes[ATTR_CURRENT_TILT_POSITION] == 80

        await _advance(hass, freezer, 0.7)  # 3.1 s > slat_time
        assert commands.sent_frames == ["*2*1*85##", "*2*0*85##"]
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100
        # Curtain on the floor but slats open: not "closed".
        assert state.state == CoverState.OPEN

        commands.clear()
        await hass.services.async_call(COVER, "close_cover_tilt", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*2*85##"]
        await _advance(hass, freezer, 3.5)
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 0
        assert state.state == CoverState.CLOSED
        # Closing the slats runs into the end stop: still no stop command.
        assert commands.sent_frames == ["*2*2*85##"]


async def test_set_tilt_position_is_proportional(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """`set_cover_tilt_position` splits the slat phase proportionally."""
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        await hass.services.async_call(
            COVER, "set_cover_tilt_position", {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 40}, blocking=True
        )
        await _advance(hass, freezer, 0.6)  # 40 % of 3 s = 1.2 s
        assert commands.sent_frames == ["*2*1*85##"]
        await _advance(hass, freezer, 0.7)
        assert commands.sent_frames == ["*2*1*85##", "*2*0*85##"]
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 40


async def test_tilt_is_a_noop_while_the_curtain_is_up(hass: HomeAssistant, tmp_path) -> None:
    """Above the floor the slats are always open: tilt commands do nothing."""
    mock_restore_cache(
        hass,
        (State(SLAT_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 50, ATTR_CURRENT_TILT_POSITION: 100}),),
    )
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        assert hass.states.get(SLAT_ENTITY).attributes[ATTR_CURRENT_TILT_POSITION] == 100
        for service, data in (
            ("open_cover_tilt", {}),
            ("close_cover_tilt", {}),
            ("set_cover_tilt_position", {ATTR_TILT_POSITION: 20}),
        ):
            await hass.services.async_call(
                COVER, service, {ATTR_ENTITY_ID: SLAT_ENTITY, **data}, blocking=True
            )
        assert commands.sent_frames == []
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 50
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100


async def test_keypad_movement_uses_the_same_model(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A physical up press from closed only opens the slats for the first 3 s."""
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML):
        cover = entity_object(hass, COVER, "2-85")
        await feed_event(hass, cover, "*2*1*85##")
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING

        await _advance(hass, freezer, 2)
        await feed_event(hass, cover, "*2*0*85##")
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 67
        assert state.state == CoverState.OPEN


async def test_asymmetric_opening_and_closing_times(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`opening_time` / `closing_time` are used per direction (andrea-parisi/MyHOME)."""
    mock_restore_cache(hass, (_closed(ASYM_ENTITY),))
    async with setup_myhome(hass, tmp_path, ASYMMETRIC_YAML) as (_entry, commands):
        state = hass.states.get(ASYM_ENTITY)
        assert state.attributes["Opening time"] == 32.0
        assert state.attributes["Closing time"] == 28.0

        # Up: 3 s of slats + 50 % of (32 - 3) = 17.5 s.
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ASYM_ENTITY, ATTR_POSITION: 50}, blocking=True
        )
        await _advance(hass, freezer, 16.9)
        assert commands.sent_frames == ["*2*1*86##"]
        await _advance(hass, freezer, 0.7)
        assert commands.sent_frames == ["*2*1*86##", "*2*0*86##"]
        assert hass.states.get(ASYM_ENTITY).attributes[ATTR_CURRENT_POSITION] == 50

        # Down: 50 % of (28 - 3) = 12.5 s of curtain, then 3 s of slats.
        commands.clear()
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ASYM_ENTITY}, blocking=True)
        await _advance(hass, freezer, 12)
        assert hass.states.get(ASYM_ENTITY).attributes[ATTR_CURRENT_POSITION] == 2
        await _advance(hass, freezer, 4)  # 16 s > 12.5 + 3
        state = hass.states.get(ASYM_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 0
        assert state.state == CoverState.CLOSED


async def test_tilt_survives_entry_reload(hass: HomeAssistant, tmp_path) -> None:
    """"Closed with the slats open" is restored across a reload, tilt included."""
    mock_restore_cache(
        hass,
        (State(SLAT_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 0, ATTR_CURRENT_TILT_POSITION: 60}),),
    )
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (entry, _commands):
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 60
        assert state.state == CoverState.OPEN

        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes.get(ATTR_CURRENT_POSITION) == 0
        assert state.attributes.get(ATTR_CURRENT_TILT_POSITION) == 60
        assert state.state == CoverState.OPEN

async def test_set_position_survives_the_gateway_stop_echo(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """MyHOMEServer1 echoes "stopped" then "opening" right after our command.

    Seen live on 2026-09-05: the echo cancelled the timed target and the shutter
    ran fully open. The stop echo must be ignored, the opening echo must not
    restart the estimate, and the timed stop must still be sent.
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_POSITION: 5}, blocking=True
        )
        assert commands.sent_frames == ["*2*1*85##"]
        cover = entity_object(hass, COVER, "2-85")
        await _advance(hass, freezer, 0.1)
        await feed_event(hass, cover, "*2*0*85##")  # gateway stop echo
        await _advance(hass, freezer, 0.4)
        await feed_event(hass, cover, "*2*1*85##")  # gateway opening echo
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING

        await _advance(hass, freezer, 3.2)  # 3.7 s: not there yet
        assert commands.sent_frames == ["*2*1*85##"]
        await _advance(hass, freezer, 0.7)  # 4.4 s > 4.35 s
        assert commands.sent_frames == ["*2*1*85##", "*2*0*85##"]
        await feed_event(hass, cover, "*2*0*85##")  # echo of our own stop
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 5
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100
        assert state.state == CoverState.OPEN


async def test_keypad_stop_is_not_mistaken_for_an_echo(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A keypad press (bus event, not our command) followed by a real stop is honoured."""
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, _commands):
        cover = entity_object(hass, COVER, "2-85")
        await feed_event(hass, cover, "*2*1*85##")
        await _advance(hass, freezer, 1.0)
        await feed_event(hass, cover, "*2*0*85##")
        state = hass.states.get(SLAT_ENTITY)
        assert state.state == CoverState.OPEN
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert 0 < state.attributes[ATTR_CURRENT_TILT_POSITION] < 100


# ---------------------------------------------------------------- review 2026-09-07
INVERTED_ADVANCED_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_adv_inverted:
      where: '84'
      name: Cover Adv Inverted
      advanced: true
      inverted: true
"""


async def test_advanced_position_is_never_estimated(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A plain movement frame on an advanced actuator must not start the timer model."""
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*10*42*0*0##")
        await feed_event(hass, cover, "*2*1*83##")
        assert hass.states.get(entity_id).state == CoverState.OPENING
        await _advance(hass, freezer, 40)
        # No status frame arrived: the real position must survive untouched.
        assert hass.states.get(entity_id).attributes[ATTR_CURRENT_POSITION] == 42
        await feed_event(hass, cover, "*2*0*83##")
        assert hass.states.get(entity_id).state == CoverState.OPEN


async def test_advanced_status_keeps_the_direction(hass: HomeAssistant, tmp_path) -> None:
    """Status 11-14 carry a position and a direction: both must be visible."""
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*11*42*0*0##")
        state = hass.states.get(entity_id)
        assert state.state == CoverState.OPENING
        assert state.attributes[ATTR_CURRENT_POSITION] == 42
        await feed_event(hass, cover, "*#2*83*10*12*60*0*0##")
        assert hass.states.get(entity_id).state == CoverState.CLOSING
        await feed_event(hass, cover, "*#2*83*10*10*60*0*0##")
        assert hass.states.get(entity_id).state == CoverState.OPEN

        # Review 3 / C3-8: OWNd reads the number in a 11-14 frame as the position the
        # run *started* from, and the one in a state-10 frame as the current position.
        # Both are the actuator's own value and both are written, so a run that starts
        # at 20 reports 20 until the actuator says otherwise - it never reports a
        # position the actuator did not send.
        await feed_event(hass, cover, "*#2*83*10*10*80*0*0##")
        assert hass.states.get(entity_id).attributes[ATTR_CURRENT_POSITION] == 80
        await feed_event(hass, cover, "*#2*83*10*11*20*0*0##")
        state = hass.states.get(entity_id)
        assert state.state == CoverState.OPENING
        assert state.attributes[ATTR_CURRENT_POSITION] == 20


async def test_inverted_advanced_cover_inverts_the_position_too(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, INVERTED_ADVANCED_YAML) as (_entry, commands):
        entity_id = "cover.cover_adv_inverted"
        cover = entity_object(hass, COVER, "2-84")
        await feed_event(hass, cover, "*#2*84*10*10*30*0*0##")
        assert hass.states.get(entity_id).attributes[ATTR_CURRENT_POSITION] == 70
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: entity_id, ATTR_POSITION: 70}, blocking=True
        )
        assert commands.sent_frames == ["*#2*84*#11#001*30##"]


async def test_late_movement_echo_after_our_stop_is_ignored(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A 0.6 s tilt run finishes before the gateway echoes the raise command."""
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-85")
        await hass.services.async_call(
            COVER, "set_cover_tilt_position", {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 20}, blocking=True
        )
        await _advance(hass, freezer, 0.8)
        assert commands.sent_frames == ["*2*1*85##", "*2*0*85##"]
        await feed_event(hass, cover, "*2*1*85##")  # stale echo of the raise command
        await _advance(hass, freezer, 40)
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 20


async def test_set_position_to_the_current_value_stops_a_moving_cover(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-81")
        await feed_event(hass, cover, "*2*1*81##")  # keypad
        await _advance(hass, freezer, 12)
        current = hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION]
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: current}, blocking=True
        )
        assert commands.sent_frames == ["*2*0*81##"]
        await _advance(hass, freezer, 40)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == current


async def test_end_stop_frame_recalibrates_a_full_close(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The motor reaches the floor before our timer: the estimate must snap to closed."""
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 50}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 0.1)
        await feed_event(hass, cover, "*2*0*81##")  # gateway echo, ignored
        await _advance(hass, freezer, 12)  # 80 % of the expected 15 s run
        await feed_event(hass, cover, "*2*0*81##")  # physical end stop
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.state == CoverState.CLOSED


async def test_early_stop_during_our_full_run_is_a_real_stop(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A stop well before the end of our own run is somebody stopping it: freeze."""
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 50}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 6)  # 40 % of the expected 15 s run
        await feed_event(hass, cover, "*2*0*81##")
        state = hass.states.get(ENTITY)
        assert state.state == CoverState.OPEN
        assert 25 <= state.attributes[ATTR_CURRENT_POSITION] <= 32


async def test_second_stop_inside_the_echo_window_is_honoured(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML):
        cover = entity_object(hass, COVER, "2-85")
        await hass.services.async_call(COVER, "open_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        await _advance(hass, freezer, 0.2)
        await feed_event(hass, cover, "*2*0*85##")  # gateway echo, ignored
        await _advance(hass, freezer, 0.8)
        await feed_event(hass, cover, "*2*0*85##")  # real keypad stop, inside the window
        state = hass.states.get(SLAT_ENTITY)
        assert state.state == CoverState.OPEN
        assert 0 < state.attributes[ATTR_CURRENT_TILT_POSITION] < 100


async def test_restore_wins_over_the_first_status_reply(hass: HomeAssistant, tmp_path) -> None:
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 42}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await feed_event(hass, cover, "*2*0*81##")
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 42
@pytest.mark.parametrize(
    ("delay", "expected_state", "expected_position"),
    [
        (1.0, CoverState.CLOSING, 40),  # inside the window: the gateway echo is ignored
        (1.6, CoverState.OPEN, 95),  # outside it: a real keypad stop wins
    ],
)
async def test_stop_echo_window_boundary(
    hass: HomeAssistant,
    tmp_path,
    freezer: FrozenDateTimeFactory,
    delay: float,
    expected_state: str,
    expected_position: int,
) -> None:
    """`STOP_ECHO_WINDOW_SEC` is a boundary, not a "swallow every stop" rule.

    Inside the window the gateway's own echo must not cancel the timed target;
    just outside it, someone pressing STOP on the keypad must freeze the estimate
    where it got to and cancel the pending auto-stop.

    Mutations caught: `STOP_ECHO_WINDOW_SEC = 0.2` (the 1.0 s case stops honouring
    the echo, so the shutter runs on to the end stop - the bug seen live on
    2026-09-05) and `STOP_ECHO_WINDOW_SEC = 5.0` (the 1.6 s case swallows a real
    keypad STOP two seconds into a `set_cover_position` run and keeps going).
    Both values are accepted by every other test in this file, because the echo
    test feeds its echo at 0.1 s and nothing ever feeds a stop just outside the
    window.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
        )
        # 100 -> 40 on a 30 s run: closing, and the auto-stop is due after 18 s.
        assert commands.sent_frames == ["*2*2*81##"]
        cover = entity_object(hass, COVER, "2-81")

        await _advance(hass, freezer, delay)
        await feed_event(hass, cover, "*2*0*81##")
        assert hass.states.get(ENTITY).state == expected_state

        await _advance(hass, freezer, 20)
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == expected_position
        # Only a run that was never stopped reaches its timed auto-stop.
        assert commands.sent_frames == (
            ["*2*2*81##", "*2*0*81##"] if expected_state == CoverState.CLOSING else ["*2*2*81##"]
        )


# ---------------------------------------------------------------- review 2 (2026-09-07)
async def test_keypad_movement_after_our_stop_is_honoured(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The gateway can only echo the movement it was interrupting, never the other one.

    Review 2 / C1: "stop it - no, open it again" on the wall keypad used to be
    swallowed whole, leaving Home Assistant reporting `closed` / 0 % while the
    shutter ran fully open. Mutation caught: `_is_echo` ignoring *any* movement
    frame inside the window after our own stop.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 5)
        await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        stopped_at = hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION]
        assert 80 <= stopped_at <= 86

        await _advance(hass, freezer, 1.0)  # well inside the echo window
        await feed_event(hass, cover, "*2*1*81##")  # somebody presses UP
        assert hass.states.get(ENTITY).state == CoverState.OPENING
        await _advance(hass, freezer, 40)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100

        # Review 3 / C3-9: a stop on a cover that was *not* moving interrupts nothing,
        # so it can be echoed by nothing either - the next keypad press is honoured
        # whatever its direction. Mutation caught: `_stopped_direction = interrupted
        # or OPENING`, which swallows the press below.
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 5)
        await feed_event(hass, cover, "*2*0*81##")  # somebody stops it at the wall
        assert hass.states.get(ENTITY).state == CoverState.OPEN
        await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 0.5)
        await feed_event(hass, cover, "*2*1*81##")
        assert hass.states.get(ENTITY).state == CoverState.OPENING


async def test_same_direction_echo_after_our_stop_is_ignored_then_rechecked(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The ambiguous case: ignore the frame, then ask the actuator what it is doing.

    A copy of the movement we just stopped is exactly what the gateway echoes, so it
    must not restart the estimate (mutation caught: dropping `_mark_own_stop()` from
    `async_stop_cover`, review 2 / G6). But it could equally be a second keypad press
    in the same direction, and that must not be lost for ever (review 2 / C1): a
    status re-request follows, and its answer restarts the estimate.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 5)
        await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        stopped_at = hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION]
        commands.clear()

        await _advance(hass, freezer, 1.0)
        await feed_event(hass, cover, "*2*2*81##")  # the gateway's late copy - or a new press
        # `!= CLOSING` would also pass on `unknown` / `unavailable`: say what it is.
        assert hass.states.get(ENTITY).state == CoverState.OPEN
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == stopped_at

        # Bounded recovery: the actuator is asked what it is really doing.
        await _advance(hass, freezer, 2.5)
        assert commands.status_frames == ["*#2*81##"]
        await feed_event(hass, cover, "*2*2*81##")  # it answers "still closing"
        assert hass.states.get(ENTITY).state == CoverState.CLOSING
        await _advance(hass, freezer, 40)
        assert hass.states.get(ENTITY).state == CoverState.CLOSED


async def test_a_stop_the_gateway_refused_changes_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A stop that never reached the bus leaves the shutter running - and the estimate.

    Review 3 / C3-1: the round-2 fix used the `send()` result to skip arming the echo
    window, but still ended the estimate. On a refused stop (the command queue is
    full, or the handler is closing) the shutter goes on to its end stop while Home
    Assistant froze the position half way and stopped ticking - permanently, because
    the actuator's own `stopped` frame at the end of the run then re-freezes the same
    stale value. Mutation caught: calling `_finish_movement(*self._estimate())` before
    the `sent` check, after which the cover reads *open* at ~83 % for ever.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 5)

        async def _refuse(self, message) -> bool:
            return False

        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)

        # The shutter never stopped: the estimate must keep running to the floor.
        assert hass.states.get(ENTITY).state == CoverState.CLOSING
        await _advance(hass, freezer, 0.5)
        # And nothing was armed either, so a frame inside the window is still honoured.
        await feed_event(hass, cover, "*2*2*81##")
        assert hass.states.get(ENTITY).state == CoverState.CLOSING
        await _advance(hass, freezer, 30)
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.state == CoverState.CLOSED


async def test_a_timed_stop_the_gateway_refused_does_not_arm_the_echo_window(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Review 3 / C3-3: the same rule on the stop that ends a `set_cover_position`.

    That stop is sent by the movement deadline, and its `send()` result used to be
    discarded: a refused stop armed the echo window anyway, and the window then
    swallowed the first frame in the interrupted direction - which, the stop having
    never reached the bus, can only be a real one. Mutation caught: calling
    `_mark_own_stop(interrupted)` without looking at the result, after which the
    keypad frame below is ignored and the cover stays *open* at 50 %.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 50}, blocking=True
        )

        async def _refuse(self, message) -> bool:
            return False

        # 100 -> 50 on a 30 s run: the auto-stop is due after 15 s, and refused.
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await _advance(hass, freezer, 16)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 50

        await feed_event(hass, cover, "*2*2*81##")  # the shutter is still going down
        assert hass.states.get(ENTITY).state == CoverState.CLOSING


async def test_advanced_movement_is_bounded_by_a_safety_timer(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Review 2 / C2: one lost "stopped" frame must not pin the entity on `opening`.

    Nothing times an advanced actuator, so before the safety timer the direction was
    only ever cleared by another bus frame. Mutations caught: removing the timer from
    `_set_advanced_direction` (the entity then reads *Opening* for ever) and dropping
    the `self._moving = None` from the grace callback (same).

    Review 3 / C3-2: the bound asks before it concludes. Nothing answers here, so the
    direction goes - but only after `ADVANCED_PROBE_GRACE_SEC`, never at the moment
    the status request goes out.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*10*42*0*0##")
        await feed_event(hass, cover, "*2*1*83##")
        assert hass.states.get(entity_id).state == CoverState.OPENING
        await _advance(hass, freezer, 40)  # inside the 20 s run + 30 s margin
        assert hass.states.get(entity_id).state == CoverState.OPENING

        commands.clear()
        await _advance(hass, freezer, 15)  # 55 s: the "stopped" frame is never coming
        # The actuator is asked first, and is still reported as moving until it
        # answers - or fails to.
        assert commands.status_frames == ["*#2*83##"]
        assert hass.states.get(entity_id).state == CoverState.OPENING

        await _advance(hass, freezer, 3)  # the grace runs out unanswered
        state = hass.states.get(entity_id)
        assert state.state == CoverState.OPEN
        # The real position is still the actuator's own, never an estimate.
        assert state.attributes[ATTR_CURRENT_POSITION] == 42
        assert commands.status_frames == ["*#2*83##"]


async def test_a_slow_advanced_actuator_never_leaves_opening(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Review 3 / C3-2: the safety timer must not publish a false "stopped" mid-run.

    An advanced cover is not `assumed_state` and is *closed* at position 0, so a
    shutter opening from the floor whose real run is longer than the bound used to be
    published as **closed** for as long as the status re-read took - once per run,
    firing every automation watching for `closed` or for the end of `opening`.

    Mutation caught: clearing `self._moving` and writing the state in
    `_async_advanced_movement_timeout` before the re-read (the round-2 shape), after
    which `closed` shows up in the recorded states below.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*10*0*0*0##")  # closed, on the floor
        assert hass.states.get(entity_id).state == CoverState.CLOSED

        seen: list[str] = []

        @callback
        def _record(event) -> None:
            seen.append(event.data["new_state"].state)

        unsub = async_track_state_change_event(hass, [entity_id], _record)
        await feed_event(hass, cover, "*2*1*83##")  # it starts opening
        assert hass.states.get(entity_id).state == CoverState.OPENING

        commands.clear()
        await _advance(hass, freezer, 55)  # past the 50 s bound, still running
        assert commands.status_frames == ["*#2*83##"]
        # It answers "still opening, started from 60": the direction survives.
        await feed_event(hass, cover, "*#2*83*10*11*60*0*0##")
        assert hass.states.get(entity_id).state == CoverState.OPENING

        # The answer re-armed the full bound, so the run is not cut short either.
        await _advance(hass, freezer, 40)
        assert hass.states.get(entity_id).state == CoverState.OPENING
        unsub()
        assert CoverState.CLOSED not in seen
        assert set(seen) == {CoverState.OPENING}


# 90 s of travel: the bound becomes 120 s instead of the 50 s default.
ADVANCED_LONG_RUN_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_advanced_long:
      where: '87'
      name: Cover Advanced Long
      advanced: true
      shutter_run: 90
"""


async def test_the_timing_keys_of_an_advanced_cover_size_the_safety_timer(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Review 3 / C3-4: on an advanced cover the timing keys do exactly one thing.

    They never produce a position (that is always the actuator's own value), but they
    are the only way to move the safety bound of `_set_advanced_direction` - which a
    shutter, awning or garage door whose run is longer than 50 s needs. Mutation
    caught: reading a fixed constant instead of `max(opening_time, closing_time)`,
    after which this cover is dropped out of *Opening* at 52 s.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_LONG_RUN_YAML) as (_entry, commands):
        entity_id = "cover.cover_advanced_long"
        cover = entity_object(hass, COVER, "2-87")
        await feed_event(hass, cover, "*#2*87*10*10*42*0*0##")
        await feed_event(hass, cover, "*2*1*87##")
        assert hass.states.get(entity_id).state == CoverState.OPENING

        await _advance(hass, freezer, 60)  # long past the 50 s default bound
        assert hass.states.get(entity_id).state == CoverState.OPENING
        assert commands.status_frames == []

        await _advance(hass, freezer, 65)  # 125 s: past 90 + 30
        assert commands.status_frames == ["*#2*87##"]
        await _advance(hass, freezer, 3)
        assert hass.states.get(entity_id).state == CoverState.OPEN


async def test_an_unload_during_the_status_grace_leaves_no_timer(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The grace armed by the safety timer must die with the entity.

    It lives in the same slot as the bound itself, so `_cancel_timers()` (and with it
    `async_will_remove_from_hass`) takes both; the Home Assistant test harness raises
    a *lingering timer* error on unload if it does not. Mutation caught: forgetting
    the handle (`self._advanced_timer = None` right after arming the grace).
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*10*42*0*0##")
        await feed_event(hass, cover, "*2*1*83##")
        await _advance(hass, freezer, 55)  # the bound fires, the grace is armed
        assert commands.status_frames == ["*#2*83##"]
        assert hass.states.get("cover.cover_advanced").state == CoverState.OPENING
    # The context manager unloads the entry inside the grace.


async def test_an_advanced_stop_disarms_the_safety_timer(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The normal case must stay silent: no stray status request after a clean stop."""
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*2*1*83##")
        await feed_event(hass, cover, "*#2*83*10*10*80*0*0##")  # position + "stopped"
        assert hass.states.get(entity_id).state == CoverState.OPEN
        commands.clear()
        await _advance(hass, freezer, 90)
        assert commands.status_frames == []


async def test_a_keypad_reversal_during_our_own_movement_is_honoured(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A movement frame is never the echo of a movement *we* commanded.

    Review 2 / W6: `_is_echo`'s first arm ("we commanded a movement, so only a
    `stopped` frame can be its echo") was decided by nothing in the suite - 0 hits
    in a full run - and dropping it left every test green. It is reachable, and by
    the most ordinary route there is: our own `close_cover` is still running when
    somebody at the wall keypad presses UP, well inside `STOP_ECHO_WINDOW_SEC`.

    Mutation caught: removing `if frame_direction is not None: return False` from
    that arm, after which the reversal is swallowed as an echo - Home Assistant
    goes on reporting `closing` and estimating the shutter downwards while it is
    actually running up, and the estimate is wrong until the next status request.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        assert hass.states.get(ENTITY).state == CoverState.CLOSING

        await _advance(hass, freezer, 0.5)  # well inside the 1.5 s echo window
        await feed_event(hass, cover, "*2*1*81##")  # somebody presses UP on the keypad

        assert hass.states.get(ENTITY).state == CoverState.OPENING
        await _advance(hass, freezer, 40)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100
        assert hass.states.get(ENTITY).state == CoverState.OPEN


async def test_the_status_grace_outlives_a_bus_round_trip(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`ADVANCED_PROBE_GRACE_SEC` has to be long enough for the answer to come back.

    The safety timer asks the actuator what it is doing and only then concludes; the
    whole value of that (C3-2) is that a *slow* actuator answers in time. The answer
    travels the command queue, which is serialised across the gateway and may already
    hold other requests, so the grace is not free: too short and the entity publishes
    `closed` mid-run again - an advanced cover is not `assumed_state` and reads
    *closed* at position 0 - once per run longer than its bound.

    The other advanced tests feed the answer without moving the clock at all, so they
    pass for any grace whatsoever, and `test_a_slow_advanced_actuator_never_leaves_opening`
    advances in one jump that straddles the whole sequence. Mutations caught:
    `ADVANCED_PROBE_GRACE_SEC = 0.01` and `= 0.5`.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*10*0*0*0##")  # closed, on the floor
        await feed_event(hass, cover, "*2*1*83##")  # it starts opening
        commands.clear()

        await _advance(hass, freezer, 55)  # past the 50 s bound: the actuator is asked
        assert commands.status_frames == ["*#2*83##"]

        # A round trip on a busy command queue is not instantaneous. The entity must
        # still say `opening` while it waits, not flip to `closed` at position 0.
        await _advance(hass, freezer, 1.0)
        assert hass.states.get(entity_id).state == CoverState.OPENING

        await feed_event(hass, cover, "*#2*83*10*11*60*0*0##")  # "still opening"
        assert hass.states.get(entity_id).state == CoverState.OPENING


async def test_the_echo_recheck_waits_out_the_echo_window(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`ECHO_RECHECK_DELAY_SEC` must not fire while the gateway may still be echoing.

    The re-request is what recovers a keypad press the echo guard swallowed; sending
    it while our own command is still being echoed back asks the actuator a question
    in the middle of the noise the guard exists to filter, and costs one command-queue
    slot per swallowed frame.

    `test_same_direction_echo_after_our_stop_is_ignored_then_rechecked` advances 2.5 s
    in a single step, so it passes for any delay at all. Mutations caught:
    `ECHO_RECHECK_DELAY_SEC = 1.0` and `= 0.01` (both inside `STOP_ECHO_WINDOW_SEC`).
    """
    assert cover_module.ECHO_RECHECK_DELAY_SEC > cover_module.STOP_ECHO_WINDOW_SEC
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 5)
        await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        commands.clear()

        await feed_event(hass, cover, "*2*2*81##")  # the ambiguous same-direction frame
        # Still inside the echo window: the actuator must not be asked yet.
        await _advance(hass, freezer, 1.0)
        assert commands.status_frames == []
        # Past `ECHO_RECHECK_DELAY_SEC`: now it is.
        await _advance(hass, freezer, 1.5)
        assert commands.status_frames == ["*#2*81##"]


@pytest.mark.parametrize(
    ("position", "expected"),
    [(50, "*2*1*81##"), (49, "*2*2*81##")],  # 50 is the boundary and belongs to "open"
)
async def test_a_position_command_with_no_known_position_runs_to_the_nearer_end(
    hass: HomeAssistant, tmp_path, position: int, expected: str
) -> None:
    """First use after a restart: `set_cover_position` still has to do something sensible.

    A basic cover knows where it is only from its own estimate, and a fresh install -
    or a restart with no restored state - has no estimate at all. Ignoring the command
    would leave the user pressing a slider that does nothing; the honest approximation
    is to run to the nearer end stop, which also re-calibrates the estimate for every
    command after it. Nothing in the suite reached this branch: every position test
    restores a position first.

    Parametrised rather than sequential, because a second setup in the same test would
    restore the position the first one left behind and never reach the branch at all.

    Mutations caught: `if position >= 50` -> `> 50` (a target of exactly 50 then runs
    the cover the wrong way), and deleting the `current is None` branch, after which
    `position > current` raises a TypeError inside the service call and the slider
    fails with a traceback.
    """
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        assert ATTR_CURRENT_POSITION not in hass.states.get(ENTITY).attributes  # unknown

        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: position}, blocking=True
        )
        assert commands.sent_frames == [expected]
        assert hass.states.get(ENTITY).state == (
            CoverState.OPENING if expected.startswith("*2*1") else CoverState.CLOSING
        )


async def test_a_tilt_command_with_no_known_position_is_ignored(
    hass: HomeAssistant, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    """A tilt with no position must be dropped, not guessed.

    Tilt only means anything with the curtain on the floor, so the slat phase cannot
    be entered until the position is known. Guessing would send the shutter to an end
    stop the user did not ask for - the opposite of what a tilt slider is for - and
    the branch that prevents it (`position is None`) had no test, so deleting it left
    the suite green while `position > 0` raised a TypeError inside the service call.

    Mutation caught: deleting the `if position is None: return` guard of
    `_async_move_tilt`.
    """
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        assert ATTR_CURRENT_POSITION not in hass.states.get(SLAT_ENTITY).attributes  # unknown

        with caplog.at_level("DEBUG"):
            await hass.services.async_call(
                COVER,
                "set_cover_tilt_position",
                {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 40},
                blocking=True,
            )
        assert commands.sent_frames == []  # nothing was sent to the bus
        assert "the position is not known yet" in caplog.text
        # And the entity is left alone: still unknown, not guessed into a state.
        assert hass.states.get(SLAT_ENTITY).state == STATE_UNKNOWN


async def test_an_advanced_actuator_reports_closing_as_well_as_opening(
    hass: HomeAssistant, tmp_path
) -> None:
    """Both halves of the advanced direction pair, not just the one that had a test.

    An advanced actuator's plain WHAT frames (`*2*1*83##` / `*2*2*83##`) carry only the
    direction - the position comes from its own status frames - and only the `opening`
    half was ever fed to one. Its `closing` sibling three lines down was not: an
    asymmetry, not a design decision. A shutter coming down at the keypad would show
    as `open` for the whole run, so a dashboard shows no movement and an automation
    waiting for `closing` never fires.

    Mutation caught: deleting the `elif closing: self._set_advanced_direction(CLOSING)`
    arm of the plain-frame branch (the cover then sits at `open` while it travels).
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*10*60*0*0##")  # stopped, at 60
        assert hass.states.get(entity_id).state == CoverState.OPEN

        await feed_event(hass, cover, "*2*2*83##")  # somebody presses DOWN
        state = hass.states.get(entity_id)
        assert state.state == CoverState.CLOSING
        # The position stays the actuator's own: an advanced cover is never estimated.
        assert state.attributes[ATTR_CURRENT_POSITION] == 60

        await feed_event(hass, cover, "*2*1*83##")  # and UP again
        assert hass.states.get(entity_id).state == CoverState.OPENING
