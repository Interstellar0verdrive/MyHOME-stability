"""Tests for the MyHOME cover platform (Contract F: time-based position)."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any
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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util
from OWNd.message import OWNAutomationCommand, OWNEvent
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    async_fire_time_changed_exact,
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

# `roll: 1` on every fixture below: these tests were written against the linear model
# and still pin it exactly (0.4.2 keeps `roll: 1` term-for-term identical to 0.3.x).
# The roll model itself is exercised by the ROLL_YAML fixture and the helper tests.
BASIC_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_test:
      where: '81'
      name: Cover Test
      shutter_run: 30
      roll: 1
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
      roll: 1
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
      tilt: true
      roll: 1
"""

# Same slat phase, but the motor is slower going up than coming down.
ASYMMETRIC_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_asymmetric:
      where: '86'
      name: Cover Asymmetric
      slat_time: 3
      tilt: true
      roll: 1
      opening_time: 32
      closing_time: 28
"""

# The roll model itself: 30 s of curtain, no slats, k = 1.7 (spec 0.4.2 section 1).
ROLL_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_roll:
      where: '87'
      name: Cover Roll
      shutter_run: 30
      roll: 1.7
"""

# A shutter that is not equally loaded in the two directions (0.4.2 amendment): the
# curtain phase is 30 s each way, but the tube behaves differently up and down.
DIRECTIONAL_ROLL_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_directional:
      where: '90'
      name: Cover Directional
      shutter_run: 30
      closing_roll: 1.7
      opening_roll: 1.0
"""

# A slat phase that is *timed* but not exposed: `tilt` is left at its default (false).
NO_TILT_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_hidden_slats:
      where: '88'
      name: Cover Hidden Slats
      shutter_run: 30
      slat_time: 3
      roll: 1
"""

# A cover whose whole model comes from a gateway profile, scaled to its own window.
PROFILE_YAML = f"""
gateway:
  mac: {MAC}
  cover_profiles:
    tall:
      reference_height: 195
      opening_time: 22.3
      closing_time: 21.7
      slat_time: 5.1
      roll: 1.6
  cover:
    cover_profiled:
      where: '89'
      name: Cover Profiled
      profile: tall
      height: 150
"""

ENTITY = "cover.cover_test"
SLAT_ENTITY = "cover.cover_slats"
ASYM_ENTITY = "cover.cover_asymmetric"
ROLL_ENTITY = "cover.cover_roll"
NO_TILT_ENTITY = "cover.cover_hidden_slats"
PROFILE_ENTITY = "cover.cover_profiled"
DIRECTIONAL_ENTITY = "cover.cover_directional"


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
        assert state.attributes["Opening time"] == 30.0
        assert state.attributes["Closing time"] == 30.0
        assert "Shutter run" not in state.attributes
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
        # Unknown start position is assumed closed, so half a run is 50 % - less the
        # half second the motor spends not turning yet (0.4.4): 14.5 s of a 30 s run.
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 48

        # The actuator reports it stopped: freeze the estimate there.
        await feed_event(hass, entity_object(hass, COVER, "2-81"), "*2*0*81##")
        state = hass.states.get(ENTITY)
        assert state.state == CoverState.OPEN
        assert state.attributes[ATTR_CURRENT_POSITION] == 48

        await _advance(hass, freezer, 10)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 48


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
        # 9.5 s of motor: the first half second of the call is the bus (0.4.4).
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 68

        # 60 % of a 30 s run = 18 s of motor, so the stop frame leaves at
        # 0.5 + 18 - 0.1 = 18.4 s and the shutter coasts onto the target.
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
        # 5.5 s of motor before the frame, plus the tenth of a second the motor takes
        # to obey it: 5.6 s of a 30 s run (0.4.4).
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 81

        # The auto-stop must not fire afterwards.
        await _advance(hass, freezer, 60)
        assert commands.sent_frames == ["*2*2*81##", "*2*0*81##"]
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 81


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
        assert state.attributes["Opening time"] == 30.0
        assert state.attributes["Closing time"] == 30.0
        assert state.attributes["Slat time"] == 3.0
        assert state.attributes["Roll"] == 1.0
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
        # 1.5 s of motor, since the first half second is the bus (0.4.4).
        await _advance(hass, freezer, 2)
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 50
        assert state.state == CoverState.OPENING

        await _advance(hass, freezer, 2.1)  # 4.1 s: not there yet
        assert commands.sent_frames == ["*2*1*85##"]

        # 4.8 s > 0.5 + 4.35 - 0.1: the frame leaves a tenth of a second early and
        # the motor coasts onto the target.
        await _advance(hass, freezer, 0.7)
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
        await _advance(hass, freezer, 16.3)
        assert commands.sent_frames == ["*2*1*85##"]

        await _advance(hass, freezer, 0.9)  # 17.2 s > 0.5 + 16.5 - 0.1 = 16.9 s
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

        # 15.5 s: 15 s of motor, so the curtain is down (13.5 s) and the slats are
        # half way through their three seconds.
        await _advance(hass, freezer, 15.5)
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 50
        assert state.state == CoverState.CLOSING

        await _advance(hass, freezer, 1.5)  # 17 s > 0.5 + 13.5 + 3
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
        # 1.9 s of motor into the three-second slat phase.
        assert hass.states.get(SLAT_ENTITY).attributes[ATTR_CURRENT_TILT_POSITION] == 63

        await _advance(hass, freezer, 0.7)  # 3.1 s > 0.5 + 3 - 0.1
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
        await _advance(hass, freezer, 17.3)  # 17.9 = 0.5 + 17.5 - 0.1: not yet
        assert commands.sent_frames == ["*2*1*86##"]
        await _advance(hass, freezer, 0.7)
        assert commands.sent_frames == ["*2*1*86##", "*2*0*86##"]
        assert hass.states.get(ASYM_ENTITY).attributes[ATTR_CURRENT_POSITION] == 50

        # Down: 50 % of (28 - 3) = 12.5 s of curtain, then 3 s of slats.
        commands.clear()
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ASYM_ENTITY}, blocking=True)
        await _advance(hass, freezer, 12)  # 11.5 s of motor
        assert hass.states.get(ASYM_ENTITY).attributes[ATTR_CURRENT_POSITION] == 4
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


# --------------------------------------------------------------------------------------
# The roll model (0.4.2)
# --------------------------------------------------------------------------------------
class _Model:
    """Just enough of a cover to call the travel model, without Home Assistant.

    `_travel` / `_travel_time` / `_normalise` read six attributes and nothing else, so
    the model can be exercised on its own - which is the only way to compare it against
    the pre-0.4.2 formulas over a grid.
    """

    def __init__(
        self,
        opening: float,
        closing: float,
        slat: float,
        roll: float,
        opening_roll: float | None = None,
        closing_roll: float | None = None,
    ) -> None:
        self._opening_time = opening
        self._closing_time = closing
        self._slat_time = slat
        self._roll = roll
        self._opening_roll = roll if opening_roll is None else opening_roll
        self._closing_roll = roll if closing_roll is None else closing_roll
        self._curtain_up = max(cover_module.MIN_CURTAIN_TIME, opening - slat)
        self._curtain_down = max(cover_module.MIN_CURTAIN_TIME, closing - slat)
        self._two_phase = slat > 0
        self._has_tilt = slat > 0

    _normalise = cover_module.MyHOMECover._normalise
    _curtain_tau = cover_module.MyHOMECover._curtain_tau
    _curtain_position = cover_module.MyHOMECover._curtain_position
    _travel = cover_module.MyHOMECover._travel
    _travel_time = cover_module.MyHOMECover._travel_time


def _linear_travel(model: _Model, direction: str, position: int, tilt: int, elapsed: float):
    """The 0.4.1 `_travel`, verbatim: the reference the roll model must degenerate to."""
    slat = model._slat_time
    if direction == cover_module.OPENING:
        if position <= 0 and slat > 0 and tilt < 100:
            slat_left = (100 - tilt) / 100 * slat
            if elapsed <= slat_left:
                return model._normalise(0, tilt + elapsed / slat * 100)
            elapsed -= slat_left
        return model._normalise(position + elapsed / model._curtain_up * 100, 100)
    curtain_left = position / 100 * model._curtain_down
    if elapsed < curtain_left:
        return model._normalise(position - elapsed / model._curtain_down * 100, 100)
    elapsed -= curtain_left
    if slat <= 0:
        return model._normalise(0, 0)
    start_tilt = 100 if position > 0 else tilt
    return model._normalise(0, start_tilt - elapsed / slat * 100)


def _linear_travel_time(model: _Model, direction: str, position: int, tilt: int, target: int, target_tilt: int):
    """The 0.4.1 `_travel_time`, verbatim."""
    slat = model._slat_time
    if direction == cover_module.OPENING:
        seconds = 0.0
        if position <= 0 and slat > 0:
            slat_target = 100 if target > 0 else target_tilt
            seconds += max(0.0, slat_target - tilt) / 100 * slat
        return seconds + max(0.0, target - position) / 100 * model._curtain_up
    seconds = max(0.0, position - target) / 100 * model._curtain_down
    if target <= 0 and slat > 0:
        start_tilt = 100 if position > 0 else tilt
        seconds += max(0.0, start_tilt - target_tilt) / 100 * slat
    return seconds


@pytest.mark.parametrize("roll", [1.0, 1.0000000001, 1.3, 1.7, 2.5, 5.0])
def test_roll_helpers_are_inverse_and_monotonic(roll: float) -> None:
    """`_roll_tau` and `_roll_x` are each other's inverse on [0, 1], and increasing.

    Everything else in the model is built on those two properties: if they held only
    approximately, a position would drift a little every time it was converted to a
    time and back, which is exactly what `set_cover_position` does.
    """
    grid = [i / 20 for i in range(21)]
    for x in grid:
        assert cover_module._roll_x(roll, cover_module._roll_tau(roll, x)) == pytest.approx(x, abs=1e-9)
        assert cover_module._roll_tau(roll, cover_module._roll_x(roll, x)) == pytest.approx(x, abs=1e-9)
    # Endpoints are exact: the curtain leaves the top at 0 and reaches the floor at 1.
    assert cover_module._roll_tau(roll, 0.0) == 0.0
    assert cover_module._roll_tau(roll, 1.0) == pytest.approx(1.0)
    assert cover_module._roll_x(roll, 0.0) == 0.0
    assert cover_module._roll_x(roll, 1.0) == pytest.approx(1.0)
    taus = [cover_module._roll_tau(roll, x) for x in grid]
    assert taus == sorted(taus)
    # The curtain is never *ahead* of the linear model: it starts fast and slows down,
    # so it has always covered at least its share of the distance.
    assert all(cover_module._roll_x(roll, tau) >= tau - 1e-12 for tau in grid)


def test_roll_one_is_exactly_the_linear_model() -> None:
    """`roll: 1` must be the 0.3.x/0.4.0 model term for term, not merely close to it.

    Every timing test in this file (and every installation upgrading from 0.4.1) is
    written against the linear formulas, so the degenerate case is a compatibility
    promise rather than a limit.

    Mutation caught: dropping the `k - 1 <= tolerance` branch of the helpers, which
    turns the exact answer into a 0/0.
    """
    for slat in (0.0, 3.0):
        model = _Model(opening=32, closing=28, slat=slat, roll=1.0)
        for direction in (cover_module.OPENING, cover_module.CLOSING):
            for position in (0, 1, 17, 50, 99, 100):
                for tilt in (0, 40, 100):
                    for elapsed in (0.0, 0.5, 3.0, 7.5, 19.0, 40.0):
                        assert model._travel(direction, position, tilt, elapsed) == _linear_travel(
                            model, direction, position, tilt, elapsed
                        )
                    for target in (0, 5, 50, 100):
                        for target_tilt in (0, 60, 100):
                            assert model._travel_time(
                                direction, position, tilt, target, target_tilt
                            ) == pytest.approx(
                                _linear_travel_time(model, direction, position, tilt, target, target_tilt),
                                abs=1e-9,
                            )


def test_roll_1_7_matches_the_measured_shutter() -> None:
    """The numbers of the 0.4.2 specification, section 1 (H = 195 cm, k = 1.7).

    Half the curtain time downwards from fully open leaves the curtain at 44 % - 85 cm
    off the floor on a 195 cm window, not the 97 cm the linear model predicts. The
    quarter and three-quarter points are the same curve read twice more.
    """
    model = _Model(opening=20, closing=20, slat=0.0, roll=1.7)
    assert model._travel(cover_module.CLOSING, 100, 100, 10.0)[0] == 44
    assert model._travel(cover_module.CLOSING, 100, 100, 5.0)[0] == 70
    assert model._travel(cover_module.CLOSING, 100, 100, 15.0)[0] == 20
    # An ascent is the time reversal of the descent: the same half run from the floor
    # ends at the same height.
    assert model._travel(cover_module.OPENING, 0, 100, 10.0)[0] == 44
    # ... and the trip back costs exactly what the trip out did.
    assert model._travel_time(cover_module.CLOSING, 100, 100, 44, 100) == pytest.approx(10.0, abs=0.1)
    assert model._travel_time(cover_module.OPENING, 44, 100, 100, 100) == pytest.approx(10.0, abs=0.1)


def test_a_roll_that_never_came_from_the_validator_is_still_usable() -> None:
    """`_clamped_roll` is the entity's own guard, not a second copy of the schema.

    Contract A keeps the three roll keys inside [1, 5], but `MyHOMECover` is also built
    by hand, and a roll below 1 does not merely shift a position - it makes `_roll_x`
    answer outside [0, 100] and every estimate meaningless.

    Mutation caught: dropping the fallback, which turns an unwritten directional key
    into a roll of 0.
    """
    assert cover_module._clamped_roll(None, 1.7) == 1.7
    assert cover_module._clamped_roll(0, 1.7) == 1.7
    assert cover_module._clamped_roll(0.2, 1.7) == cover_module.MIN_ROLL
    assert cover_module._clamped_roll(9.0, 1.7) == cover_module.MAX_ROLL
    assert cover_module._clamped_roll(2.5, 1.7) == 2.5


def test_a_directional_roll_moves_the_two_ways_differently() -> None:
    """One tube, two rolls: the descent uses `closing_roll`, the ascent `opening_roll`.

    The reference shutter really does behave like this (1.69 down against 2.12 up):
    the motor fights gravity one way and is helped by it the other, and a single
    coefficient cannot describe both runs. With a curved descent (k = 1.7) and a linear
    ascent (k = 1), a third of the run down leaves the curtain at 61 % and a third of
    the run up at 33 % - the plain linear answer.

    Mutation caught: using one roll for both directions, which makes the two numbers
    equal again.
    """
    model = _Model(opening=30, closing=30, slat=0.0, roll=1.7, opening_roll=1.0, closing_roll=1.7)
    assert model._travel(cover_module.CLOSING, 100, 100, 10.0)[0] == 61
    assert model._travel(cover_module.OPENING, 0, 100, 10.0)[0] == 33
    # `_travel_time` is the inverse of the same two curves, each on its own axis.
    assert model._travel_time(cover_module.CLOSING, 100, 100, 61, 100) == pytest.approx(10.0, abs=0.1)
    assert model._travel_time(cover_module.OPENING, 0, 0, 33, 100) == pytest.approx(10.0, abs=0.1)
    # The way back is NOT the way out any more: that is the whole point of two rolls.
    # The 39 % the curtain fell in 10 s costs 11.7 s to climb back on a linear ascent.
    assert model._travel_time(cover_module.OPENING, 61, 100, 100, 100) == pytest.approx(11.7, abs=0.1)


async def test_a_directional_roll_cover_publishes_and_uses_both(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Two rolls, two attributes, and an ascent timed with the upward one.

    Half way up on this cover is the linear 15 s (`opening_roll: 1`), not the 13.1 s
    the downward roll of 1.7 would have given. `Roll` is not published at all: a single
    number would have to be one of the two, and reading it as "the" roll of the shutter
    is exactly the mistake the amendment exists to prevent.

    Mutation caught: `set_cover_position` taking `closing_roll` whatever the direction.
    """
    mock_restore_cache(
        hass, (State(DIRECTIONAL_ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),)
    )
    async with setup_myhome(hass, tmp_path, DIRECTIONAL_ROLL_YAML) as (_entry, commands):
        state = hass.states.get(DIRECTIONAL_ENTITY)
        assert state.attributes["Opening roll"] == 1.0
        assert state.attributes["Closing roll"] == 1.7
        assert "Roll" not in state.attributes

        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: DIRECTIONAL_ENTITY, ATTR_POSITION: 50}, blocking=True
        )
        await _advance(hass, freezer, 14.0)
        assert commands.sent_frames == ["*2*1*90##"]
        await _advance(hass, freezer, 1.5)  # 15.5 s > 15 s
        assert commands.sent_frames == ["*2*1*90##", "*2*0*90##"]
        assert hass.states.get(DIRECTIONAL_ENTITY).attributes[ATTR_CURRENT_POSITION] == 50


async def test_set_position_on_a_roll_cover_stops_on_the_roll_time(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Half *way* is not half the *time*: 50 % on a k = 1.7 shutter costs 13.1 s of 30.

    tau(0.5) = (1.7 - sqrt(2.89 - 1.89 * 0.5)) / 0.7 = 0.436238, so the motor runs
    0.436238 * 30 = 13.09 s - against the 15 s the linear model would have used.

    Mutation caught: leaving `set_cover_position` on the linear formula while only
    `_travel` learned about the roll, which would stop the shutter two seconds late.
    """
    mock_restore_cache(hass, (State(ROLL_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, ROLL_YAML) as (_entry, commands):
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ROLL_ENTITY, ATTR_POSITION: 50}, blocking=True
        )
        await _advance(hass, freezer, 12.4)
        assert commands.sent_frames == ["*2*2*87##"]

        await _advance(hass, freezer, 1.0)  # 13.4 s > 13.09 s
        assert commands.sent_frames == ["*2*2*87##", "*2*0*87##"]
        state = hass.states.get(ROLL_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 50
        assert state.attributes["Roll"] == 1.7


async def test_tilt_is_hidden_by_default_but_still_timed(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`tilt` defaults to false: no tilt feature, no tilt attribute - but the same run.

    The slat phase is a property of the shutter, not of the user interface: opening
    from fully closed really does spend `slat_time` turning the slats before the
    curtain leaves the floor, and a model that skipped it would put every position
    afterwards out by that much. What `tilt: false` removes is only the controls.

    Mutation caught: `_has_tilt` and `_two_phase` collapsed back into one flag, which
    makes this run 13.5 s instead of 16.5 s.
    """
    mock_restore_cache(hass, (_closed(NO_TILT_ENTITY),))
    async with setup_myhome(hass, tmp_path, NO_TILT_YAML) as (_entry, commands):
        state = hass.states.get(NO_TILT_ENTITY)
        assert state.state == CoverState.CLOSED
        assert ATTR_CURRENT_TILT_POSITION not in state.attributes
        assert state.attributes[ATTR_SUPPORTED_FEATURES] == (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        # The slat phase is still configured, and still advertised as a number.
        assert state.attributes["Slat time"] == 3.0

        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: NO_TILT_ENTITY, ATTR_POSITION: 50}, blocking=True
        )
        await _advance(hass, freezer, 15.9)
        assert commands.sent_frames == ["*2*1*88##"]
        await _advance(hass, freezer, 0.7)  # 16.6 s > 3 + 13.5 = 16.5 s
        assert commands.sent_frames == ["*2*1*88##", "*2*0*88##"]
        assert hass.states.get(NO_TILT_ENTITY).attributes[ATTR_CURRENT_POSITION] == 50


async def test_tilt_commands_are_refused_when_tilt_is_off(hass: HomeAssistant, tmp_path) -> None:
    """Without the feature Home Assistant refuses the service before it reaches us."""
    mock_restore_cache(hass, (_closed(NO_TILT_ENTITY),))
    async with setup_myhome(hass, tmp_path, NO_TILT_YAML) as (_entry, commands):
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                COVER, "open_cover_tilt", {ATTR_ENTITY_ID: NO_TILT_ENTITY}, blocking=True
            )
        assert commands.sent_frames == []


async def test_a_profiled_cover_publishes_where_its_numbers_came_from(
    hass: HomeAssistant, tmp_path
) -> None:
    """`Height` and `Profile` are the audit trail of a derived cover.

    The times themselves say nothing about where they came from, and a cover whose
    model was scaled from a gateway profile is exactly the one whose attributes will be
    read when the estimate looks wrong.

    Mutation caught: dropping either attribute, or publishing them on a cover that has
    neither key (the other tests in this file assert they are absent there).
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML):
        state = hass.states.get(PROFILE_ENTITY)
        assert state.attributes["Profile"] == "tall"
        assert state.attributes["Height"] == 150.0
        # sqrt(1 + (1.6**2 - 1) * 150/195) = 1.4832397, rounded only for display.
        assert state.attributes["Roll"] == pytest.approx(1.4832397, abs=1e-6)
        assert state.attributes["Slat time"] == pytest.approx(3.9230769, abs=1e-6)

    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        plain = hass.states.get(ENTITY)
        assert "Profile" not in plain.attributes and "Height" not in plain.attributes


async def test_a_hidden_slat_state_survives_a_reload(hass: HomeAssistant, tmp_path) -> None:
    """A cover with `tilt: false` still remembers where its slats were.

    The tilt is not published on such a cover, so restoring it from the *state* is
    impossible; the extra restore data carries the model's own value instead. Without
    it the first open after a restart would spend a whole `slat_time` turning slats
    that were already open, and every position afterwards would be out by that much.

    Mutation caught: storing `current_cover_tilt_position` (None here) instead of the
    estimate.
    """
    async with setup_myhome(hass, tmp_path, NO_TILT_YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, "2-88")
        cover._finish_movement(0, 40)  # noqa: SLF001 - the slats half open, curtain down
        assert cover.extra_restore_state_data.as_dict() == {"position": 0, "tilt": 40}

        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        restored = entity_object(hass, COVER, "2-88")
        assert restored._move_start_tilt is None  # noqa: SLF001 - not moving
        assert restored._attr_current_cover_tilt_position == 40  # noqa: SLF001


async def test_the_calibration_sleep_really_sleeps() -> None:
    """The one line every calibration test patches out (`_async_sleep`).

    It exists so a test can replace the waiting without touching `asyncio.sleep` for
    the whole process; a zero-second call is enough to prove it is a real await.
    """
    await cover_module._async_sleep(0)


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
        (1.6, CoverState.OPEN, 96),  # outside it: a real keypad stop wins
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

        async def _refuse(self, message, **kwargs) -> bool:
            return False

        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)

        # The shutter never stopped: the estimate must keep running to the floor.
        assert hass.states.get(ENTITY).state == CoverState.CLOSING
        await _advance(hass, freezer, 0.5)
        # The shutter is still going, so a frame in that direction changes nothing here.
        await feed_event(hass, cover, "*2*2*81##")
        assert hass.states.get(ENTITY).state == CoverState.CLOSING
        await _advance(hass, freezer, 30)
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.state == CoverState.CLOSED


async def test_a_timed_stop_the_gateway_refused_runs_on_to_the_end_stop(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The refused-stop rule on the stop that ends a `set_cover_position`.

    Review 3 / C3-3 made that stop look at its `send()` result, but only to decide
    whether to arm the echo window: the estimate was still settled on the target
    first, unconditionally. Review 4 / C4-2: a stop that never reached the bus does
    not stop anything, so the shutter runs on to its end stop while Home Assistant
    reported it parked at a position it never reached - and the actuator's own
    `stopped` frame at the end of the physical run then re-froze that same stale
    value, for good.

    The timed run is now converted into a free run instead: the estimate keeps
    running, and the frame at the end of it re-calibrates the position exactly as it
    does for an `open_cover` / `close_cover` we sent ourselves.

    Mutations caught: settling the estimate before the send (the round-3 shape),
    after which the cover reads *open* at 50 % for ever; and dropping
    `self._own_free_run = True` from `_continue_to_end_stop`, after which the frame
    at the floor freezes the estimate wherever it happened to be instead of snapping
    it to closed.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 50}, blocking=True
        )

        async def _refuse(self, message, **kwargs) -> bool:
            return False

        # 100 -> 50 on a 30 s run: the auto-stop is due after 15 s, and refused.
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await _advance(hass, freezer, 16)

        # The shutter never got the stop: it is still going down, already past the
        # target, and the estimate goes down with it.
        state = hass.states.get(ENTITY)
        assert state.state == CoverState.CLOSING
        assert state.attributes[ATTR_CURRENT_POSITION] < 50

        # The shutter is still going, so a frame in that direction changes nothing here.
        await feed_event(hass, cover, "*2*2*81##")
        assert hass.states.get(ENTITY).state == CoverState.CLOSING

        # 12 s into the ~14 s of travel that were left: the actuator's own frame is
        # the end stop, and re-calibrates the estimate on the floor.
        await _advance(hass, freezer, 12)
        await feed_event(hass, cover, "*2*0*81##")
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.state == CoverState.CLOSED


async def test_a_refused_stop_cover_arms_no_echo_window(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The same rule on the explicit `stop_cover`, whose refusal returns even earlier.

    `async_stop_cover` says it too - "a stop the gateway never took cannot be echoed
    back, so arming the echo window on it would only swallow somebody else's frame" -
    and the `not sent` arm returns before `_mark_own_stop`. Nothing pinned that
    either, for the same reason as the test above: the "still honoured" line in
    `test_a_stop_the_gateway_refused_changes_nothing` feeds a `closing` frame while
    the entity is still `CLOSING`, so `_is_echo` is never reached.

    Mutation caught: calling `_mark_own_stop(self._moving)` in the `not sent` arm of
    `async_stop_cover` before it returns.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        await _advance(hass, freezer, 5)

        async def _refuse(self, message, **kwargs) -> bool:
            return False

        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        assert hass.states.get(ENTITY).state == CoverState.CLOSING

        # Somebody stops it at the wall instead, then presses "down" again straight
        # away. Both frames are real events; neither is an echo of anything we sent.
        await feed_event(hass, cover, "*2*0*81##")
        assert hass.states.get(ENTITY).state == CoverState.OPEN
        await feed_event(hass, cover, "*2*2*81##")
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
    direction goes - but only after the status grace (the gateway's command timeout
    plus a margin, see `ADVANCED_PROBE_GRACE_MARGIN_SEC`), never at the moment the
    status request goes out.
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

        # The grace is the command path's whole worst case for one request plus a
        # margin: two attempts of (connect + write/ACK), i.e. 40 + 2 s by default.
        await _advance(hass, freezer, 43)  # the grace runs out unanswered
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
        await _advance(hass, freezer, 43)  # nothing answers within the grace
        assert hass.states.get(entity_id).state == CoverState.OPEN


# Two slow awnings, each slower in one direction: 120 s one way, 40 s the other.
# `max` bounds both at 150 s; `min`, `opening_time` alone and `closing_time` alone
# each get one of the two wrong.
ADVANCED_ASYMMETRIC_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_adv_slow_open:
      where: '88'
      name: Cover Adv Slow Open
      advanced: true
      opening_time: 120
      closing_time: 40
    cover_adv_slow_close:
      where: '89'
      name: Cover Adv Slow Close
      advanced: true
      opening_time: 40
      closing_time: 120
"""


@pytest.mark.parametrize(
    ("where", "entity_id"),
    [("88", "cover.cover_adv_slow_open"), ("89", "cover.cover_adv_slow_close")],
    ids=["slower-opening", "slower-closing"],
)
async def test_the_safety_bound_of_an_advanced_cover_takes_the_longer_direction(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, where: str, entity_id: str
) -> None:
    """One bound for both directions, so it has to be the *longer* of the two.

    `opening_time` and `closing_time` are per-direction everywhere else
    (`test_asymmetric_opening_and_closing_times`), but an advanced cover has a single
    `_advanced_move_timeout`. Sizing it from the shorter direction cuts every long run
    short: an awning that takes 120 s to open, bounded at 40 + 30, has its status
    re-read fired mid-run and leaves *Opening* if the actuator does not answer inside
    the grace. Every other advanced fixture declares `shutter_run` alone, where the two
    times are equal and `max`, `min`, `opening_time` and `closing_time` all agree.

    Both orderings are exercised, so reading either key on its own fails on one of
    them. Mutation caught: `max(self._opening_time, self._closing_time)` ->
    `min(...)`, `self._opening_time`, or `self._closing_time`.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_ASYMMETRIC_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, f"2-{where}")
        await feed_event(hass, cover, f"*#2*{where}*10*10*42*0*0##")
        await feed_event(hass, cover, f"*2*1*{where}##")
        assert hass.states.get(entity_id).state == CoverState.OPENING

        # 100 s: past every wrong bound (40 + 30), well inside the right one (150 s).
        await _advance(hass, freezer, 100)
        assert commands.status_frames == []
        assert hass.states.get(entity_id).state == CoverState.OPENING

        await _advance(hass, freezer, 55)  # 155 s: past 120 + 30
        assert commands.status_frames == [f"*#2*{where}##"]


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


async def test_a_stop_on_an_advanced_cover_leaves_the_model_to_the_actuator(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Review 4 / C4-5: `stop_cover` on an advanced cover only sends the command.

    An advanced actuator's position *and* direction come from its own frames, so
    there is nothing to end here: the entity stays *Opening* until the actuator says
    it stopped, and the safety timer that bounds that direction stays armed. This is
    the arm of `async_stop_cover` that used to share one comment with the
    refused-command one - a reader who took that comment at face value would have
    read this as a refusal path and "fixed" it by freezing the estimate.

    Mutation caught: dropping the `if self._advanced: return`, after which the cover
    is published as *open* at 42 % the moment the stop is sent, before the actuator
    has stopped at all.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        await feed_event(hass, cover, "*#2*83*10*10*42*0*0##")
        await feed_event(hass, cover, "*2*1*83##")
        assert hass.states.get(entity_id).state == CoverState.OPENING
        commands.clear()

        await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: entity_id}, blocking=True)
        assert commands.sent_frames == ["*2*0*83##"]
        # The command is on its way: only the actuator's own frame ends the movement.
        assert hass.states.get(entity_id).state == CoverState.OPENING
        assert hass.states.get(entity_id).attributes[ATTR_CURRENT_POSITION] == 42

        await feed_event(hass, cover, "*#2*83*10*10*55*0*0##")  # "stopped at 55 %"
        state = hass.states.get(entity_id)
        assert state.state == CoverState.OPEN
        assert state.attributes[ATTR_CURRENT_POSITION] == 55
        # ... and that frame took the safety timer with it: no stray status request.
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

        # Well inside the 1.5 s echo window, and far enough in for the motor to have
        # moved at all: before 0.5 s of bus delay (0.4.4) the shutter is still at 100 %
        # and an UP press would have nowhere to go.
        await _advance(hass, freezer, 1.0)
        await feed_event(hass, cover, "*2*1*81##")  # somebody presses UP on the keypad

        assert hass.states.get(ENTITY).state == CoverState.OPENING
        await _advance(hass, freezer, 40)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100
        assert hass.states.get(ENTITY).state == CoverState.OPEN


async def test_the_status_grace_outlives_a_bus_round_trip(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The status grace has to outlast the command path it is waiting on.

    The safety timer asks the actuator what it is doing and only then concludes; the
    whole value of that (C3-2) is that a *slow* actuator answers in time. The answer
    travels the ordinary command queue - one sending worker by default, a scene's
    worth of commands possibly ahead of it, an idle command session that has to be
    re-opened first - and how long that costs is not one option but the handler's
    whole worst case for a single command: a connect, a write-and-ACK, and one retry
    of both (`MyHOMEGatewayHandler.command_budget`, 40 s with the defaults).

    Review 4 / C4-1: the round-3 grace was a fixed 2 s, which expires well inside
    that budget. On a merely busy bus (the "close everything at sunset" scene is the
    common one) the answer landed after the grace and the entity published `closed`
    in the middle of the run again - an advanced cover is not `assumed_state` and
    reads *closed* at position 0 - which is the symptom C3-2 was about.

    Review 5 / C5-3: sizing it on `command_timeout` alone left out the reconnect the
    comment itself named, and the reconnect is the likely case here - this entity has
    sent nothing for at least the whole safety bound, and an unused command session is
    closed after a minute. 13 s of silence, less than a single connect plus write,
    still flipped the entity to *closed*.

    The other advanced tests feed the answer without moving the clock at all, so they
    pass for any grace whatsoever, and `test_a_slow_advanced_actuator_never_leaves_opening`
    advances in one jump that straddles the whole sequence. Mutations caught: any
    fixed grace shorter than the command budget (`2.0`, the round-3 value, or `0.5`),
    a hard-coded `42.0` that would stop following the option, and the round-4 sizing
    on `command_timeout` alone, which the 13 s wait below defeats.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        entity_id = "cover.cover_advanced"
        cover = entity_object(hass, COVER, "2-83")
        handler = cover._gateway_handler  # noqa: SLF001 - the real handler, default options
        # The grace is the command path's own worst case plus a margin, never a
        # constant - and that worst case counts the reconnect and the retry, not just
        # the write (C5-3).
        assert handler.command_budget == 2 * (handler.connect_timeout + handler.command_timeout)
        assert handler.command_budget == 40.0  # the defaults, spelled out
        assert cover._advanced_probe_grace == (  # noqa: SLF001
            handler.command_budget + cover_module.ADVANCED_PROBE_GRACE_MARGIN_SEC
        )
        assert cover._advanced_probe_grace == 42.0  # noqa: SLF001

        await feed_event(hass, cover, "*#2*83*10*10*0*0*0##")  # closed, on the floor

        seen: list[str] = []

        @callback
        def _record(event) -> None:
            seen.append(event.data["new_state"].state)

        unsub = async_track_state_change_event(hass, [entity_id], _record)
        await feed_event(hass, cover, "*2*1*83##")  # it starts opening
        commands.clear()

        await _advance(hass, freezer, 55)  # past the 50 s bound: the actuator is asked
        assert commands.status_frames == ["*#2*83##"]

        # A round trip on a busy command queue is not instantaneous. Thirteen seconds
        # is not even one connect plus one write-and-ACK, so the request is still
        # perfectly in time; the entity must still say `opening` while it waits, not
        # flip to `closed` at position 0. (It is also more than the round-4 grace of
        # `command_timeout` + 2 s, so this is the wait that pins C5-3.)
        await _advance(hass, freezer, 13.0)
        assert hass.states.get(entity_id).state == CoverState.OPENING

        await feed_event(hass, cover, "*#2*83*10*11*60*0*0##")  # "still opening"
        assert hass.states.get(entity_id).state == CoverState.OPENING
        unsub()
        assert CoverState.CLOSED not in seen

        # And the grace follows the option: a gateway given 30 s per write gets
        # 2 * (10 + 30) + 2.
        handler.command_timeout = 30.0
        assert cover._advanced_probe_grace == 82.0  # noqa: SLF001


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


async def test_a_short_refused_timed_run_survives_the_gateway_echo(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """C5-2: the continued run keeps the echo protection of the command that began it.

    `_continue_to_end_stop` restarts the estimate through `_start_movement`, which
    clears the "we just sent this" bookkeeping. For a run longer than the echo window
    (1.5 s) that is harmless - the window had expired anyway. For a *short* run it is
    not: the gateway's own late "stopped" copy of the movement command we sent when
    the run began is then taken at face value and ends the continued run, which is
    precisely the failure C4-2 set out to remove.

    Short timed runs are ordinary: this one is a 40 % tilt on a 3 s slat time, i.e.
    1.2 s; a slider nudge from 50 % to 52 % on a 30 s run is 0.54 s.

    Mutation caught: dropping the save/restore of `_own_command_at` / `_own_command`
    around the `_start_movement` call in `_continue_to_end_stop`, after which the
    cover freezes at the tilt it had reached and never sees the end stop.
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-85")
        await hass.services.async_call(
            COVER, "set_cover_tilt_position", {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 40}, blocking=True
        )
        assert commands.sent_frames == ["*2*1*85##"]

        async def _refuse(self, message, **kwargs) -> bool:
            return False

        # The 1.2 s tilt run is over and its stop is refused: the slats keep going.
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await _advance(hass, freezer, 1.25)
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING

        # Still inside the 1.5 s window of `*2*1*85##`: this "stopped" frame is the
        # gateway repeating our own movement command, not the actuator stopping.
        await feed_event(hass, cover, "*2*0*85##")
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING

        # So the run carries on to the end stop, as `_continue_to_end_stop` promises.
        await _advance(hass, freezer, 40)
        state = hass.states.get(SLAT_ENTITY)
        assert state.state == CoverState.OPEN
        assert state.attributes[ATTR_CURRENT_POSITION] == 100
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 100


async def test_a_real_stop_inside_the_inherited_echo_window_is_re_read(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """C6-1: the window the continued run inherits may hide a real stop, so we ask.

    The window C5-2 restores across `_continue_to_end_stop` protects the run from the
    gateway's late "stopped" copy of the movement command that began it (the test
    above). The same window also swallows a *genuine* stop - somebody at the keypad,
    or an obstacle - for whatever is left of the 1.5 s, and nothing in the frame tells
    the two apart. Swallowed with no follow-up, the estimate then runs on to the end
    stop while the shutter stands still, and the entity settles on *Open* at 100 % for
    a cover parked at tilt 42: wrong until the next command or the next bus frame.

    So the frame is still ignored - it usually *is* the echo - but the actuator is
    asked what it is really doing, exactly as for the ambiguous keypad press in the
    same direction (`ECHO_RECHECK_DELAY_SEC`). Its answer costs two seconds of error
    instead of a position that stays wrong.

    Mutation caught: `_echo_after_restart` never set in `_continue_to_end_stop` (no
    status request goes out at all), or the flag not honoured in `_async_echo_recheck`
    (the re-check returns early because `_moving` is set during a continued run). With
    either, the cover ends this test fully open at 100 / 100.
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-85")
        await hass.services.async_call(
            COVER, "set_cover_tilt_position", {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 40}, blocking=True
        )
        assert commands.sent_frames == ["*2*1*85##"]
        commands.clear()

        async def _refuse(self, message, **kwargs) -> bool:
            return False

        # Same setup as the test above: the 1.2 s tilt run is over, its stop is refused,
        # and the slats keep going with the echo window of `*2*1*85##` still open.
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await _advance(hass, freezer, 1.25)
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING

        # This time the "stopped" frame is real: the shutter is parked at tilt ~42. It
        # is indistinguishable from the echo, so it is ignored just the same...
        await feed_event(hass, cover, "*2*0*85##")
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING
        assert commands.status_frames == []

        # ...but two seconds later the actuator is asked what it is doing.
        await _advance(hass, freezer, cover_module.ECHO_RECHECK_DELAY_SEC)
        assert commands.status_frames == ["*#2*85##"]

        # Its answer ends the run where the estimate has got to - a couple of seconds
        # of overshoot - instead of letting it free-run to the upper end stop.
        await feed_event(hass, cover, "*2*0*85##")
        state = hass.states.get(SLAT_ENTITY)
        assert state.state != CoverState.OPENING
        position = state.attributes[ATTR_CURRENT_POSITION]
        tilt = state.attributes[ATTR_CURRENT_TILT_POSITION]
        assert position < 10

        # And it stays there: no timer is left running towards the end stop.
        await _advance(hass, freezer, 40)
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == position
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == tilt

async def test_a_position_frame_on_a_cover_declared_basic_is_ignored(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """C6-2: a dimension-10 frame must not switch a basic cover into the advanced model.

    `advanced:` defaults to `false` and is the one key a user cannot guess from the
    device label, so "an advanced actuator configured as basic" is an ordinary
    misconfiguration. The dimension-10 branch used to be the only one in
    `handle_event` with no `self._advanced` guard, so such a frame took the entity
    apart: `_finish_movement` stopped the time-based estimate, `_set_advanced_direction`
    then set the direction again *without* restarting it, and the entity read *Opening*
    at a frozen percentage for the advanced safety bound plus its grace - here 60 + 42
    seconds - with nothing in the log to connect it to the missing key. A later plain
    `*2*1*81##` could not repair it either (the model is already "opening").

    Mutation caught: dropping the `and not self._advanced` guard from the branch, after
    which the position below jumps to 60 and a status re-read goes out at 60 s.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-81")
        assert hass.states.get(ENTITY).attributes[ATTR_ASSUMED_STATE] is True
        commands.clear()

        with caplog.at_level("DEBUG"):
            await feed_event(hass, cover, "*#2*81*10*11*60*0*0##")  # "opening, from 60 %"
        # The user is told which key would make the frame meaningful.
        assert "configured as basic" in caplog.text
        assert "advanced: true" in caplog.text

        # Nothing moved: no direction, no position taken from the frame.
        state = hass.states.get(ENTITY)
        assert state.state == CoverState.CLOSED
        assert state.attributes[ATTR_CURRENT_POSITION] == 0

        # And no advanced timer was armed behind it: past the 30 s run + 30 s bound
        # and the 42 s grace, the entity has still asked the actuator nothing.
        await _advance(hass, freezer, 100)
        assert commands.status_frames == []
        assert hass.states.get(ENTITY).state == CoverState.CLOSED


async def test_a_position_frame_does_not_interrupt_a_basic_cover_estimate(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """C6-2, the other half: the running estimate must survive the ignored frame.

    Ignoring the frame is only useful if the model it protects keeps running. The
    cover is opening on a 30 s run when the stray dimension-10 frame arrives; the
    estimate has to carry on from where it was, not freeze at the position the frame
    carried.

    Mutation caught: the same missing guard - the estimate stops and the position
    sticks at 60 for the rest of the run.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        await feed_event(hass, cover, "*2*1*81##")  # somebody pressed "up" on the keypad
        await _advance(hass, freezer, 6)  # a fifth of the 30 s run
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 20

        await feed_event(hass, cover, "*#2*81*10*11*60*0*0##")
        state = hass.states.get(ENTITY)
        assert state.state == CoverState.OPENING
        assert state.attributes[ATTR_CURRENT_POSITION] == 20  # not 60

        await _advance(hass, freezer, 6)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 40


async def test_a_fresh_command_after_a_continued_run_re_reads_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The inherited-window flag must not outlive the run that set it.

    `_echo_after_restart` marks one specific window as ambiguous: the residual slice a
    continued free run inherits from the command that began it (C6-1). An ordinary
    command that lands while that run is still going arms a *fresh* window a fraction
    of a second before the gateway echoes it back, which is the case `_is_echo`
    documents as having "nothing to re-read". If the flag survived into it, every such
    command would put a status request on the bus two seconds later for no reason, and
    the actuator's answer could end a run the user had only just started.

    Mutation caught: deleting `self._echo_after_restart = False` from `_start_movement`
    - the flag then leaks out of `_continue_to_end_stop` into the next command and a
    `*#2*85##` goes out at `ECHO_RECHECK_DELAY_SEC`. The run below is deliberately a
    long one: a short run would end first and `_finish_movement` would cancel the
    re-check timer before it could fire, hiding the leak.
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-85")
        await hass.services.async_call(
            COVER, "set_cover_tilt_position", {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 40}, blocking=True
        )

        async def _refuse(self, message, **kwargs) -> bool:
            return False

        # The 1.2 s tilt run ends, its stop is refused: the run continues to the end
        # stop and inherits the echo window of the command that began it.
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await _advance(hass, freezer, 1.25)
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING

        # An ordinary command lands while that run is still going: it arms its own echo
        # window from scratch, so the "stopped" frame that follows is the gateway's copy
        # of it and there is nothing ambiguous left to ask about.
        commands.clear()
        await hass.services.async_call(COVER, "open_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*1*85##"]
        await feed_event(hass, cover, "*2*0*85##")
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING

        await _advance(hass, freezer, cover_module.ECHO_RECHECK_DELAY_SEC)
        assert commands.status_frames == []
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING


async def test_a_new_command_drops_the_pending_echo_re_read(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A re-read that a later command made pointless must not reach the bus.

    `_is_echo` schedules a status request two seconds out whenever the frame it
    ignored might have been real. If another command arrives first the question is
    already answered - that command restarted the model - so `_cancel_timers` drops
    the pending re-read. Nothing exercised `_cancel_echo_recheck`'s body at all
    (`cover.py:494-495` was unreached by the whole suite), so the unsubscribe could be
    dropped and a stale `*#2*85##` would land on the bus after every such sequence.

    Mutation caught: removing the `self._echo_recheck()` call from
    `_cancel_echo_recheck`, or replacing its body with `return`.
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-85")
        await hass.services.async_call(COVER, "open_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        await _advance(hass, freezer, 1.0)
        await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)

        # The gateway's late copy of the movement our stop interrupted: ignored, but
        # ambiguous enough that a re-read is armed for `ECHO_RECHECK_DELAY_SEC`.
        await feed_event(hass, cover, "*2*1*85##")
        assert hass.states.get(SLAT_ENTITY).state != CoverState.OPENING

        # The user does not wait for it: they close the slats again straight away.
        commands.clear()
        await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*2*85##"]

        # That command answered the question, so the armed re-read is dropped.
        await _advance(hass, freezer, cover_module.ECHO_RECHECK_DELAY_SEC)
        assert commands.status_frames == []


async def test_stop_cover_tilt_stops_the_slats(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`stop_cover_tilt` is a real button in the UI, and it is the same bus stop.

    The tilt controls are the only ones a slat cover shows while the slats are moving,
    so this is the button a user reaches for to park the slats half open.
    `async_stop_cover_tilt` delegates to `async_stop_cover`; nothing exercised it, so
    the delegation could be removed and the button would silently do nothing.

    Mutation caught: replacing the body of `async_stop_cover_tilt` with `return`.
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (_entry, commands):
        await hass.services.async_call(COVER, "open_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        await _advance(hass, freezer, 1.0)
        assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING
        commands.clear()

        await hass.services.async_call(COVER, "stop_cover_tilt", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        assert commands.sent_frames == ["*2*0*85##"]

        state = hass.states.get(SLAT_ENTITY)
        assert state.state != CoverState.OPENING
        frozen = state.attributes[ATTR_CURRENT_TILT_POSITION]
        assert 0 < frozen < 100  # parked mid-phase, which is the point of the button

        # And the estimate really stopped: the slats do not drift on.
        await _advance(hass, freezer, 30)
        assert hass.states.get(SLAT_ENTITY).attributes[ATTR_CURRENT_TILT_POSITION] == frozen


@pytest.mark.parametrize(
    ("target", "expected_frame", "expected_end"),
    [(100, "*2*1*81##", 100), (0, "*2*2*81##", 0)],
)
async def test_the_two_ends_of_the_position_slider_run_to_the_end_stop(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, target, expected_frame, expected_end
) -> None:
    """Dragging the slider all the way is an open/close, not a timed run.

    Both ends are special-cased in `async_set_cover_position`: a timed run computed
    from an estimate would stop the shutter a few percent short of the end stop and
    leave the estimate uncalibrated, while running into the end stop re-calibrates it
    for free. Only the `position <= 0` half was exercised, so the `>= 100` half could
    have sent the opposite command - the shutter would go down when the user asked for
    fully open - with the suite green.

    Mutation caught: `await self.async_open_cover()` -> `await self.async_close_cover()`
    in the `position >= 100` arm.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 42}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        commands.clear()
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: target}, blocking=True
        )
        assert commands.sent_frames == [expected_frame]

        # A free run to the end stop: no stop command is ever sent, and the estimate
        # lands exactly on the end rather than a few percent short of it.
        await _advance(hass, freezer, 31)
        assert commands.sent_frames == [expected_frame]
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == expected_end


@pytest.mark.parametrize(
    ("restored_state", "expected_position"),
    [(CoverState.CLOSED, 0), (CoverState.OPEN, 100)],
)
async def test_a_restored_state_without_a_position_is_read_from_the_state_itself(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, restored_state, expected_position
) -> None:
    """The upgrade path: a cover restored from before positions existed.

    `myhome` covers stored no `current_position` until the two-phase model landed, and
    a restored state is whatever the *previous* version wrote. Without this fallback
    the entity comes back with no position at all, which makes the first
    `set_cover_position` take the "unknown position" branch and run the shutter to an
    end stop instead of to the position asked for - one wrong full travel per cover,
    once, on the release that upgrades them.

    The slats follow the curtain (`tilt = 100 if position > 0 else 0`): a cover resting
    on the floor has its slats closed, a raised one has them open.

    Mutation caught: swapping the two `position =` assignments in
    `async_added_to_hass`.
    """
    mock_restore_cache(hass, (State(SLAT_ENTITY, restored_state),))  # no attributes at all
    async with setup_myhome(hass, tmp_path, SLAT_YAML):
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == expected_position
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == expected_position

        # And the estimate starts from there: a run in the direction it can still go
        # moves away from the restored end, it does not jump to the other one.
        service = "close_cover" if expected_position == 100 else "open_cover"
        await hass.services.async_call(COVER, service, {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
        await _advance(hass, freezer, 6)
        moved = hass.states.get(SLAT_ENTITY).attributes[ATTR_CURRENT_POSITION]
        assert moved != expected_position
        assert abs(moved - expected_position) < 50  # from the restored end, not the other one


# ------------------------------------------------------- delivery-timed runs (0.4.3)
# `MyHOMEGatewayHandler.send` only queues a frame; one worker writes the queue
# serially, about a tenth of a second per frame. The covers below drive that worker by
# hand on the frozen clock, so a frame reaches the bus exactly when the test says it
# does - which is the whole subject of 0.4.3.
TWELVE_WHERES = tuple(str(where) for where in range(81, 93))
TWELVE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
""" + "".join(
    f"""    cover_{where}:
      where: '{where}'
      name: Cover {where}
      shutter_run: 30
      roll: 1
"""
    for where in TWELVE_WHERES
)
TWELVE_ENTITIES = [f"cover.cover_{where}" for where in TWELVE_WHERES]
# 100 -> 40 on a 30 s linear run.
TWELVE_RUN_SEC = 18.0
# What one frame costs the single command worker (measured on a MyHOMEServer1).
FRAME_GAP_SEC = 0.1
# The queue delay that broke a cover on the real bus (addendum 9): eleven frames
# ahead of the twelfth, plus the gateway's own pace.
QUEUE_WAIT_SEC = 1.6
# 0 -> 40 on a 30 s linear run.
RUN_TO_40_SEC = 12.0
# One frame of queue in the echo replay below, chosen so that the covers written last
# are written more than STOP_ECHO_WINDOW_SEC (1.5 s) after the service call.
ECHO_FRAME_GAP_SEC = 0.15
# The two bus costs the model carries from 0.4.4, read off the entity's own defaults so
# that a test never pins a number the integration has stopped using. The motor starts
# `START_DELAY_SEC` after the frame unless the actuator says otherwise, and stops
# `STOP_LATENCY_SEC` after the stop frame - so a run of `d` seconds of motor spans
# `START_DELAY_SEC + d - STOP_LATENCY_SEC` between the two writes.
START_DELAY_SEC = cover_module.DEFAULT_START_DELAY
STOP_LATENCY_SEC = cover_module.DEFAULT_STOP_LATENCY
# How long the actuator takes to answer a direction command with its own "moving"
# status, on the installation 0.4.4 comes from.
MOTOR_ECHO_SEC = 0.55
# The same answer, from a slower actuator: long enough that a whole scene of twelve
# frames is written before the first of them comes back, which is what makes the
# twelve-cover replay below readable (still well inside the window in which an answer
# can be ours: `start_delay` + 1.5 s).
SLOW_MOTOR_ECHO_SEC = 1.2


def _motor_seconds(slow: SlowCommandPath, where: str, direction: str, started: datetime | None = None) -> float:
    """Motor time between two written frames, as the bus really spends it.

    The frame that starts the run is written `START_DELAY_SEC` before the motor turns,
    and the stop frame `STOP_LATENCY_SEC` before it comes to rest. `started` replaces
    the first term when the actuator itself said when it started moving.
    """
    stopped = slow.instant(f"*2*0*{where}##") + timedelta(seconds=STOP_LATENCY_SEC)
    if started is None:
        started = slow.instant(f"*2*{direction}*{where}##") + timedelta(seconds=START_DELAY_SEC)
    return (stopped - started).total_seconds()


def _server1_answer(where: str, what: str) -> tuple[str, ...]:
    """What a MyHOMEServer1 sends on the MONITOR session when it writes a command.

    Measured on the installation this addendum comes from: the command translation
    "stop", the status "stopped", and the translation of the direction, all three
    within about a tenth of a second of the write - and only about half a second
    later, when the motor has really started, the direction status itself, which is
    the caller's job to feed. The two `1000#` translations parse to neither a
    direction nor a position and the cover ignores them; the "stopped" in the middle
    is the one that ended a run it had no business ending.
    """
    return (f"*2*1000#0*{where}##", f"*2*0*{where}##", f"*2*1000#{what}*{where}##")


def _frame_where(frame: str) -> tuple[Any, str, Any]:
    """The device an OWN frame addresses, keyed exactly as `gateway._CommandQueue`.

    `(WHO, bare WHERE, bus interface)` straight off the parsed message, so the double
    is no *less* conservative than the queue it models: reading the last field before
    the terminator instead gives `81#4#3` for `*2*1*81#4#3##` (which would let a stop
    for one bus interface overtake a direction frame for another) and `50` for an
    advanced cover's `*#2*81*#11#001*50##`.
    """
    message = OWNAutomationCommand(frame)
    return (message.who, message.where, message.interface)


class SlowCommandPath:
    """A command path whose frames are written one at a time, by the test.

    `send` only queues, exactly as the real handler does; `write_next` performs the
    write and reports it through the delivery callback, so the test decides on the
    frozen clock when each frame reaches the bus. Stop frames jump the queue exactly
    as `gateway._CommandQueue` makes them - which means they jump *other* covers'
    frames and never a frame for their own WHERE.
    """

    def __init__(self) -> None:
        self.stops: list[tuple[str, Any, Any]] = []
        self.queued: list[tuple[str, Any, Any]] = []
        self.written: list[tuple[str, datetime]] = []
        self.unreported: list[tuple[str, Any, datetime]] = []

    async def send(
        self,
        message: Any,
        *,
        on_delivered: Any = None,
        on_dropped: Any = None,
    ) -> bool:
        item = (str(message), on_delivered, on_dropped)
        where = _frame_where(item[0])
        if item[0].startswith("*2*0*") and not any(_frame_where(frame) == where for frame, _, _ in self.queued):
            self.stops.append(item)
        else:
            self.queued.append(item)
        return True

    @property
    def queue(self) -> list[tuple[str, Any, Any]]:
        """Everything still waiting, in the order it will be written."""
        return [*self.stops, *self.queued]

    def _take(self) -> tuple[str, Any, Any]:
        return (self.stops or self.queued).pop(0)

    def write_next(self, report: bool = True) -> str:
        """Write the next frame *now*, and tell its caller so.

        `report=False` writes the frame and says nothing yet: that is the race the
        addendum to 0.4.3 is about - the gateway answers a command on the *monitor*
        session as soon as it has it, and those frames can reach the entity before
        the write is reported back to it. `report_next` then does the telling.
        """
        frame, on_delivered, _ = self._take()
        written_at = dt_util.utcnow()
        self.written.append((frame, written_at))
        if on_delivered is None:
            return frame
        if report:
            on_delivered(time.monotonic())
        else:
            self.unreported.append((frame, on_delivered, written_at))
        return frame

    def report_next(self) -> str:
        """Report a write performed earlier, carrying the instant it happened.

        The report is monotonic and the cover converts it against the wall clock at
        callback time, so on a frozen clock the frozen seconds that passed in between
        have to be taken back off by hand - otherwise a report made "later" would
        claim the frame left later than it did.
        """
        frame, on_delivered, written_at = self.unreported.pop(0)
        on_delivered(time.monotonic() - (dt_util.utcnow() - written_at).total_seconds())
        return frame

    def drop_next(self) -> str:
        """Give up on the next frame: it never reaches the bus."""
        frame, _, on_dropped = self._take()
        if on_dropped is not None:
            on_dropped()
        return frame

    @property
    def frames(self) -> list[str]:
        return [frame for frame, _ in self.written]

    def instant(self, frame: str) -> datetime:
        """When `frame` was written."""
        return next(at for written, at in self.written if written == frame)


async def _advance_exact(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    """Move the frozen clock forward and fire only what is due at that instant.

    `_advance` fires everything within the next half second, which is exactly the
    slack these tests must not have: they assert *instants* to the millisecond. The
    millisecond of margin below is not slack, it is rounding - the helper compares a
    `datetime.timestamp()` against a `time.time()`, and at 1.8e9 seconds those two
    floats do not always agree on the last digit, so a timer due at exactly this
    instant would otherwise fire or not depending on the wall clock the test started
    at. It does not move the frozen clock, so every instant recorded below is still
    the exact one the test asked for.
    """
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed_exact(hass, dt_util.utcnow() + timedelta(milliseconds=1))
    await hass.async_block_till_done()


@pytest.mark.slow
async def test_twelve_covers_at_once_each_run_their_modelled_time(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The bug 0.4.3 exists for: a scene that moves twelve covers at once.

    The command worker writes one frame every 100 ms, so the twelfth "down" leaves
    the socket 1.1 s after Home Assistant asked for it - while its stop, queued a
    whole run later, finds the queue empty and goes out at once. Timing the run from
    the *enqueue* therefore made every motor stop early, by up to a second on the
    last cover: 5-14 cm too high on a 195 cm window, which is what the installation
    measured.

    What must hold is the same thing for all twelve: the motor interval each one
    really got - the instant its stop was written minus the instant its movement was
    written - is the run the model asked for. Before the fix the twelfth cover ran
    1.1 s short of it.
    """
    mock_restore_cache(
        hass,
        tuple(State(entity, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}) for entity in TWELVE_ENTITIES),
    )
    async with setup_myhome(hass, tmp_path, TWELVE_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER,
                "set_cover_position",
                {ATTR_ENTITY_ID: TWELVE_ENTITIES, ATTR_POSITION: 40},
                blocking=True,
            )
            assert len(slow.queue) == 12

            # The worker drains the queue, one frame every 100 ms.
            for index in range(12):
                if index:
                    await _advance_exact(hass, freezer, FRAME_GAP_SEC)
                slow.write_next()
                await hass.async_block_till_done()
            # (Home Assistant fans a multi-entity service call out in its own order.)
            assert sorted(slow.frames) == sorted(f"*2*2*{where}##" for where in TWELVE_WHERES)

            # Each stop now falls due 18 s of *motor* after its own frame was written
            # - half a second of bus first, a tenth of a second of coasting deducted at
            # the end - so the twelve of them arrive 100 ms apart at an idle worker.
            await _advance_exact(
                hass,
                freezer,
                TWELVE_RUN_SEC + START_DELAY_SEC - STOP_LATENCY_SEC - 11 * FRAME_GAP_SEC,
            )
            for index in range(12):
                if index:
                    await _advance_exact(hass, freezer, FRAME_GAP_SEC)
                assert len(slow.queue) == 1, f"cover {index} did not stop when it was due"
                slow.write_next()
                await hass.async_block_till_done()

        for where in TWELVE_WHERES:
            ran = _motor_seconds(slow, where, "2")
            assert abs(ran - TWELVE_RUN_SEC) < 0.001, f"cover {where} ran {ran}s"
        for entity in TWELVE_ENTITIES:
            state = hass.states.get(entity)
            assert state.attributes[ATTR_CURRENT_POSITION] == 40
            assert state.state == CoverState.OPEN


async def test_a_late_start_carries_the_timed_stop_with_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The stop is due `duration` after the frame reached the bus, not after the call.

    Mutation caught: dropping the re-scheduling of `_stop_timer` from
    `_apply_movement_delivery` (the stop then goes out at 18 s, 1.2 s of motor early),
    or re-basing only the clock and not the timer.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            # The entity reacts to the service call at once, as it always did.
            assert hass.states.get(ENTITY).state == CoverState.CLOSING

            # Eleven other covers were ahead of it in the queue.
            await _advance_exact(hass, freezer, 1.2)
            slow.write_next()
            await hass.async_block_till_done()
            # The estimate is re-based: 1.2 s of the run had not happened yet.
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100

            # 18 s after the *call* the shutter is still going: it started 1.2 s late,
            # and half a second later again (0.4.4) because no echo ever came.
            await _advance_exact(hass, freezer, 16.8)
            assert slow.queue == []
            assert hass.states.get(ENTITY).state == CoverState.CLOSING
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 46

            # 1.2 + 0.5 + 18 - 0.1: the stop frame leaves here.
            await _advance_exact(hass, freezer, 1.6)
            assert len(slow.queue) == 1
            slow.write_next()
            await hass.async_block_till_done()

        assert slow.frames == ["*2*2*81##", "*2*0*81##"]
        assert abs(_motor_seconds(slow, "81", "2") - 18.0) < 0.001
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 40
        assert state.state == CoverState.OPEN


async def test_a_stop_written_late_freezes_where_the_shutter_really_got_to(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The motor runs until the stop frame leaves, so the estimate must too.

    Two seconds of queue on a 30 s run is 6.7 % of the window - 13 cm on the 195 cm
    shutter the model was measured on. Freezing on the target would lose exactly that,
    and lose it in the direction the installation measured: too high.

    Mutation caught: settling on `(end_position, end_tilt)` when the stop is queued
    (the 0.4.2 shape), after which the cover reads 40 % while the shutter is at 33 %;
    and arming the echo window at the queueing instead of at the delivery, after which
    the gateway's own repeat of our stop is taken for a keypad press.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            slow.write_next()
            await hass.async_block_till_done()

            await _advance_exact(hass, freezer, 18.0 + START_DELAY_SEC - STOP_LATENCY_SEC)
            assert len(slow.queue) == 1  # the stop is queued, but nothing stopped yet
            assert hass.states.get(ENTITY).state == CoverState.CLOSING
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 40

            # The worker was busy with somebody else's frames for two seconds.
            await _advance_exact(hass, freezer, 2.0)
            assert hass.states.get(ENTITY).state == CoverState.CLOSING
            slow.write_next()
            await hass.async_block_till_done()

            state = hass.states.get(ENTITY)
            # 20 s of a 30 s run from the top, not the 18 s the model asked for.
            assert state.attributes[ATTR_CURRENT_POSITION] == 33
            assert state.state == CoverState.OPEN

            # The echo window opened when the frame left, so the gateway's late copy
            # of the movement it interrupted is still recognised as an echo.
            await feed_event(hass, cover, "*2*2*81##")
            assert hass.states.get(ENTITY).state == CoverState.OPEN


async def test_a_direction_frame_that_never_left_cancels_the_movement(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A queued movement the gateway never wrote moved nothing at all.

    `send()` answers as soon as the frame is queued, so the estimate starts
    optimistically; when the command path later gives up on it (the TTL expires, both
    attempts failed) the shutter never moved, and the estimate has to go back where
    the movement started from rather than run on to an end stop nothing is
    travelling towards.

    Mutation caught: ignoring `on_dropped` on a movement frame, after which the cover
    reads *closed* a run later while it never left the top.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
            assert hass.states.get(ENTITY).state == CoverState.CLOSING
            await _advance_exact(hass, freezer, 5)
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] < 100

            assert slow.drop_next() == "*2*2*81##"
            await hass.async_block_till_done()

            state = hass.states.get(ENTITY)
            assert state.attributes[ATTR_CURRENT_POSITION] == 100
            assert state.state == CoverState.OPEN
            # And no echo is expected either: the gateway cannot repeat a frame it
            # never had, so the window a command arms must be disarmed with it.
            cover = entity_object(hass, COVER, "2-81")
            assert cover._own_command_at is None  # noqa: SLF001
            assert cover._own_command is None  # noqa: SLF001
            # And nothing is running any more: no end stop is reached later.
            await _advance_exact(hass, freezer, 40)
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100
        assert slow.written == []


async def test_a_stop_that_never_left_runs_on_to_the_end_stop(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A queued stop that is dropped stopped nothing, exactly like a refused one.

    The difference with `test_a_timed_stop_the_gateway_refused_runs_on_to_the_end_stop`
    is only *when* the command path gives up: there before queueing, here after. The
    shutter is still running either way, so the run becomes a free one and the
    actuator's own frame at the end of it re-calibrates the estimate.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 50}, blocking=True
            )
            slow.write_next()
            await hass.async_block_till_done()

            await _advance_exact(hass, freezer, 15.0 + START_DELAY_SEC - STOP_LATENCY_SEC)
            assert slow.drop_next() == "*2*0*81##"
            await hass.async_block_till_done()
            assert hass.states.get(ENTITY).state == CoverState.CLOSING

            await _advance_exact(hass, freezer, 12.0)
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] < 50
            # The actuator hits the floor and says so: that is the end stop.
            await feed_event(hass, cover, "*2*0*81##")

        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.state == CoverState.CLOSED


async def test_an_explicit_stop_written_late_keeps_the_estimate_running(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`cover.stop_cover` freezes the position at the delivery, not at the call.

    Mutation caught: freezing on `self._estimate()` at the call (the 0.4.2 shape),
    after which the cover reads 85 % while the shutter stood at 71 %.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
            slow.write_next()
            await hass.async_block_till_done()

            await _advance_exact(hass, freezer, 5.0)
            await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
            # Queued, not written: the motor is still turning and so is the estimate.
            assert hass.states.get(ENTITY).state == CoverState.CLOSING

            await _advance_exact(hass, freezer, 4.0)
            slow.write_next()
            await hass.async_block_till_done()

        state = hass.states.get(ENTITY)
        # 8.6 s of a 30 s run - the motor started half a second after the command and
        # stopped a tenth of a second after the frame - not the 4.5 s it had run when
        # the button was pressed.
        assert state.attributes[ATTR_CURRENT_POSITION] == 71
        assert state.state == CoverState.OPEN


async def test_a_movement_the_command_path_refused_starts_no_estimate(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A direction frame that was never even queued moved nothing.

    The rule the refused *stop* has always followed, on the other side of the
    movement: `send()` said no, so there is no run to time and no echo to expect.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):

        async def _refuse(self, message, **kwargs) -> bool:
            return False

        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _refuse):
            await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        assert commands.sent_frames == []
        assert hass.states.get(ENTITY).state == CoverState.OPEN
        await _advance(hass, freezer, 40)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100


async def test_a_write_reported_after_a_bus_frame_ended_the_run_changes_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Both delivery reports name the run they belong to, and only touch that one.

    A keypad press can land between the queueing of a frame and its write; the run it
    ended is over, and a report that arrives afterwards must not restart its clock or
    re-freeze its position.

    Mutation caught: dropping either identity check, after which the movement report
    re-bases an estimate that is no longer running and the stop report freezes the
    cover a second time, at a position the shutter had already left.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            # A movement whose frame is still in the queue when the keypad sends the
            # cover the other way. It has to be the other way: a "stopped" frame
            # arriving while our own direction frame is queued is the gateway echoing
            # that very frame, and is ignored (addendum 9), while a direction the
            # gateway cannot possibly be echoing is somebody at the keypad and is
            # obeyed at once - which ends the run our frame belonged to just as well.
            await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
            await _advance_exact(hass, freezer, 5.0)
            await feed_event(hass, cover, "*2*1*81##")
            # 4.5 s of motor: the clock of our own frame starts half a second in.
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 85
            assert hass.states.get(ENTITY).state == CoverState.OPENING
            await _advance_exact(hass, freezer, 2.0)
            slow.write_next()
            await hass.async_block_till_done()
            await _advance_exact(hass, freezer, 2.0)
            # Four seconds of keypad run on a 30 s shutter, from the 85 % the closing
            # estimate had reached - and a keypad run starts the moment the frame says
            # so, with no bus delay of its own. A report that re-based the clock of a
            # run it does not belong to would leave it two seconds behind, at 92 %.
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 98
            # 85 % to the top is 4.5 s of motor, and the run started at 5 s.
            await _advance_exact(hass, freezer, 1.1)  # and it reaches the top
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100
            assert hass.states.get(ENTITY).state == CoverState.OPEN

            # And a timed stop whose frame is still in the queue when the actuator
            # reports that it stopped by itself.
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            slow.write_next()
            await hass.async_block_till_done()
            await _advance_exact(hass, freezer, 18.0 + START_DELAY_SEC - STOP_LATENCY_SEC)
            assert len(slow.queue) == 1  # the stop is queued and not written
            await feed_event(hass, cover, "*2*0*81##")
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 40

            await _advance_exact(hass, freezer, 5.0)
            slow.write_next()
            await hass.async_block_till_done()
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 40
        assert state.state == CoverState.OPEN


async def test_a_stop_never_leaves_before_the_movement_it_must_end(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A run shorter than the queue: the stop falls due before its own frame is written.

    A 40 % tilt is 1.2 s of motor, and the direction frame can easily spend longer
    than that in the queue - a scene, or a busy gateway. The stop that ends the run
    must not be queued while the frame that starts it is still waiting: stops overtake
    other covers' frames, so it would be written *first*, the actuator would be told
    to stop while standing still and then told to move, and nothing would ever stop it
    again. The slats would open fully and the curtain would run to the end stop while
    the entity reported tilt 40.

    Mutation caught: queueing the stop from `_async_movement_deadline` while
    `_move_delivery` is still pending (the frames then reach the bus in the order
    stop, movement, and the cover ends at 100 / 100).
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER,
                "set_cover_tilt_position",
                {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 40},
                blocking=True,
            )
            # The 1.2 s run falls due (at 0.5 + 1.2 - 0.1) while its own frame is
            # still in the queue.
            await _advance_exact(hass, freezer, 1.7)
            assert [frame for frame, _, _ in slow.queue] == ["*2*1*85##"]

            # The motor starts half a second from now: the whole run is ahead of it.
            slow.write_next()
            await hass.async_block_till_done()
            assert hass.states.get(SLAT_ENTITY).state == CoverState.OPENING

            await _advance_exact(hass, freezer, 1.6)
            assert [frame for frame, _, _ in slow.queue] == ["*2*0*85##"]
            slow.write_next()
            await hass.async_block_till_done()

        assert slow.frames == ["*2*1*85##", "*2*0*85##"]
        assert abs(_motor_seconds(slow, "85", "1") - 1.2) < 0.001
        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 40
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.state == CoverState.OPEN


async def test_a_stop_asked_for_while_the_movement_is_still_queued_leaves_after_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`cover.stop_cover` on a cover whose own direction frame has not been written.

    A scene moves twelve covers and the user stops one of them a second later, before
    the queue has reached it. The stop must not overtake the movement of the same
    cover - the actuator would take the stop while standing still and then start
    moving with nothing left to end the run - and the position frozen must be the
    travel the motor really did: from the instant the direction frame was written to
    the instant the stop was, 1.6 s of a 30 s run - half a second after the direction
    frame to a tenth of a second after the stop - not the 3.5 s that had passed since
    the service call.

    Mutation caught: routing the stop into the priority deque (the frames reach the
    bus the wrong way round), and measuring the run from the optimistic start after
    the movement was re-based onto its delivery (the cover then reads 90 %).
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
            await _advance_exact(hass, freezer, 1.0)
            await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
            # Queued behind its own movement, not in front of it.
            assert [frame for frame, _, _ in slow.queue] == ["*2*2*81##", "*2*0*81##"]
            assert hass.states.get(ENTITY).state == CoverState.CLOSING

            await _advance_exact(hass, freezer, 0.5)
            assert slow.write_next() == "*2*2*81##"
            await hass.async_block_till_done()
            assert hass.states.get(ENTITY).state == CoverState.CLOSING
            # Nothing has moved yet: the motor starts half a second from here.
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100

            await _advance_exact(hass, freezer, 2.0)
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

            state = hass.states.get(ENTITY)
            # 1.6 s of a 30 s run, which is what the shutter really did.
            assert state.attributes[ATTR_CURRENT_POSITION] == 95
            assert state.state == CoverState.OPEN

            # And it stays there: nothing is running any more.
            await _advance_exact(hass, freezer, 40)
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 95
        assert slow.frames == ["*2*2*81##", "*2*0*81##"]


async def test_the_answer_to_a_frame_that_waited_is_not_a_keypad_press(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The real-bus failure of addendum 9, replayed frame by frame.

    Twelve `set_cover_position` at once; this cover's "up" frame waits 1.6 s in the
    command queue. The gateway answers it on the monitor session the moment it is
    written - the translation "stop", the status "stopped", the translation "raise" -
    and those three reach the entity *before* the write is reported back to it; the
    status "raising" follows half a second later, after the report.

    Measured from the enqueue the echo window (1.5 s) was already over when they
    arrived, so the "stopped" ended the run and the "raising" behind it was taken for
    somebody at the keypad: the cover started a free run and went to the top, and the
    stop that should have ended the run belonged to a movement that no longer
    existed. The window now covers the whole wait, so the movement survives its own
    echo, one stop leaves 12 s after the frame reached the bus, and the shutter ends
    on its target.

    Mutation caught: measuring the window from `_own_command_at` alone (the run ends
    at the "stopped" and the cover reads 100 %).
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            # Eleven frames ahead of it: the write happens a second and a half later.
            await _advance_exact(hass, freezer, QUEUE_WAIT_SEC)
            assert slow.write_next(report=False) == "*2*1*81##"
            for answer in _server1_answer("81", "1"):
                await feed_event(hass, cover, answer)
            assert hass.states.get(ENTITY).state == CoverState.OPENING

            slow.report_next()
            await hass.async_block_till_done()
            # The motor really started here, so the estimate starts here too.
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 0

            # And says so half a second later, after the report: still not a keypad
            # press, and still nothing that could turn the run into a free one - it is
            # the motor starting, and from 0.4.4 the run is timed from this instant.
            await _advance_exact(hass, freezer, MOTOR_ECHO_SEC)
            started = dt_util.utcnow()
            await feed_event(hass, cover, "*2*1*81##")
            assert hass.states.get(ENTITY).state == CoverState.OPENING
            assert len(slow.queue) == 0

            # The stop falls due 12 s of motor after *that*, less the tenth of a
            # second the actuator takes to obey it.
            await _advance_exact(hass, freezer, RUN_TO_40_SEC - STOP_LATENCY_SEC)
            assert len(slow.queue) == 1
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()
            for answer in ("*2*1000#0*81##", "*2*0*81##"):
                await feed_event(hass, cover, answer)

        # Exactly one stop, and the motor ran the modelled time - counted from the
        # actuator's own word, not from the frame that asked it to start.
        assert slow.frames == ["*2*1*81##", "*2*0*81##"]
        assert abs(_motor_seconds(slow, "81", "1", started=started) - RUN_TO_40_SEC) < 0.001
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 40
        assert state.state == CoverState.OPEN


async def test_the_same_answer_reported_before_it_arrives_is_still_an_echo(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The same four frames, with the write reported before any of them arrives.

    This is the ordering 0.4.3 already handled - the window is re-based onto the
    delivery instant and the "stopped" lands well inside it - and it must keep
    behaving exactly as the race above: same estimate, same single stop, same target.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            await _advance_exact(hass, freezer, QUEUE_WAIT_SEC)
            assert slow.write_next() == "*2*1*81##"  # written and reported at once
            await hass.async_block_till_done()
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 0
            for answer in _server1_answer("81", "1"):
                await feed_event(hass, cover, answer)
            assert hass.states.get(ENTITY).state == CoverState.OPENING

            await _advance_exact(hass, freezer, MOTOR_ECHO_SEC)
            started = dt_util.utcnow()
            await feed_event(hass, cover, "*2*1*81##")
            assert hass.states.get(ENTITY).state == CoverState.OPENING

            await _advance_exact(hass, freezer, RUN_TO_40_SEC - STOP_LATENCY_SEC)
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

        assert slow.frames == ["*2*1*81##", "*2*0*81##"]
        assert abs(_motor_seconds(slow, "81", "1", started=started) - RUN_TO_40_SEC) < 0.001
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 40
        assert state.state == CoverState.OPEN


async def test_a_keypad_stop_while_our_own_frame_is_still_queued(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Somebody presses stop while our direction frame is still waiting its turn.

    Review 3 / risk 1: the extended window swallows that stop as if it were the echo
    of our own frame - nothing in the frame tells the two apart - and the rule "each
    shape is ignored once" then closed the window on it. The *real* echo, which
    arrives a millisecond after the write and before the delivery report, was
    therefore read as a keypad press: the run was ended by the "stopped", the target
    died with it, and the "raising" behind it started a free run to the end stop.
    Exactly the addendum-9 failure, re-entered through a stop that landed in the wait.

    The window now stays armed while the frame it belongs to is queued, so the real
    echo is still recognised and the run survives. What the cover guarantees here is
    the full outcome, not a fallback: one stop, written 12 s of motor after the
    actuator said it had started, and the shutter on its 40 % target. Swallowing that keypad
    press costs nothing, because our frame had not been written yet - the motor only
    starts when it is, and it is written *after* the stop, so there was no run of
    ours for that stop to end.

    The re-read armed by the swallow finds the movement running and stays off the
    bus (`_async_echo_recheck`); it is there for the case where our frame is dropped
    and never starts anything.

    Mutation caught: closing the window (`_own_command_at = None`) on a frame that
    only the `pending` term kept inside it - no stop is ever sent and the cover ends
    at 100 %.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            commands.clear()

            # Half way through the wait: a real stop from the keypad, for a motor
            # that is not running yet.
            await _advance_exact(hass, freezer, 0.8)
            await feed_event(hass, cover, "*2*0*81##")
            assert hass.states.get(ENTITY).state == CoverState.OPENING

            # The gateway writes our frame and answers it on the monitor session,
            # before the write is reported back to us.
            await _advance_exact(hass, freezer, QUEUE_WAIT_SEC - 0.8)
            assert slow.write_next(report=False) == "*2*1*81##"
            for answer in _server1_answer("81", "1"):
                await feed_event(hass, cover, answer)
            assert hass.states.get(ENTITY).state == CoverState.OPENING

            slow.report_next()
            await hass.async_block_till_done()
            # The motor really started here, so the estimate starts here too.
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 0

            await _advance_exact(hass, freezer, MOTOR_ECHO_SEC)
            started = dt_util.utcnow()
            await feed_event(hass, cover, "*2*1*81##")
            assert hass.states.get(ENTITY).state == CoverState.OPENING

            # The stop falls due 12 s of motor after the actuator said it had started,
            # and the re-read armed in the queue asked it nothing in between.
            await _advance_exact(hass, freezer, RUN_TO_40_SEC - STOP_LATENCY_SEC)
            assert commands.status_frames == []
            assert len(slow.queue) == 1
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()
            for answer in ("*2*1000#0*81##", "*2*0*81##"):
                await feed_event(hass, cover, answer)

        assert slow.frames == ["*2*1*81##", "*2*0*81##"]
        assert abs(_motor_seconds(slow, "81", "1", started=started) - RUN_TO_40_SEC) < 0.001
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 40
        assert state.state == CoverState.OPEN


@pytest.mark.slow
async def test_twelve_covers_answered_by_the_gateway_all_stop_on_their_target(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The whole scene, with the gateway answering every frame it writes.

    One frame every 150 ms, so the covers written last are written more than the
    1.5 s echo window after Home Assistant asked for them - and every one of them is
    answered on the monitor session before its write is reported back. Not one of the
    twelve may take that answer for a keypad press: every motor runs the modelled
    time and every shutter ends on 40 %.

    The burst the gateway relays at the write is *not* the motor (it is too soon to
    be one, `MOTOR_MIRROR_WINDOW_SEC`); each actuator says so itself a good while
    later, and the run is timed from there.

    Mutation caught: the same one as the single-cover replay, on the covers whose
    frame waited longest (the first ones are still inside the old window).
    """
    mock_restore_cache(
        hass,
        tuple(State(entity, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}) for entity in TWELVE_ENTITIES),
    )
    async with setup_myhome(hass, tmp_path, TWELVE_YAML):
        covers = {where: entity_object(hass, COVER, f"2-{where}") for where in TWELVE_WHERES}
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER,
                "set_cover_position",
                {ATTR_ENTITY_ID: TWELVE_ENTITIES, ATTR_POSITION: 40},
                blocking=True,
            )
            assert len(slow.queue) == 12

            written: list[str] = []
            for index in range(12):
                if index:
                    await _advance_exact(hass, freezer, ECHO_FRAME_GAP_SEC)
                where = _frame_where(slow.write_next(report=False))[1]
                written.append(where)
                for answer in _server1_answer(where, "2"):
                    await feed_event(hass, covers[where], answer)
                slow.report_next()
                await hass.async_block_till_done()
                assert hass.states.get(f"cover.cover_{where}").state == CoverState.CLOSING

            # Twelve frames later - 1.65 s after its own write for every one of them,
            # well past the mirror floor and still inside the window in which an answer
            # can be ours - each actuator says its motor is running. *That* is what
            # re-bases the clock, so every stop falls due `TWELVE_RUN_SEC -
            # STOP_LATENCY_SEC` after its own answer.
            echoes: dict[str, datetime] = {}
            for index, where in enumerate(written):
                if index:
                    await _advance_exact(hass, freezer, ECHO_FRAME_GAP_SEC)
                echoes[where] = dt_util.utcnow()
                await feed_event(hass, covers[where], f"*2*2*{where}##")
                await hass.async_block_till_done()
                assert hass.states.get(f"cover.cover_{where}").state == CoverState.CLOSING

            await _advance_exact(
                hass, freezer, TWELVE_RUN_SEC - STOP_LATENCY_SEC - 11 * ECHO_FRAME_GAP_SEC
            )
            for index in range(12):
                if index:
                    await _advance_exact(hass, freezer, ECHO_FRAME_GAP_SEC)
                assert len(slow.queue) == 1, f"cover {index} did not stop when it was due"
                where = _frame_where(slow.write_next())[1]
                await hass.async_block_till_done()
                for answer in (f"*2*1000#0*{where}##", f"*2*0*{where}##"):
                    await feed_event(hass, covers[where], answer)

        for where in TWELVE_WHERES:
            # Timed from the actuator's own "moving", not from the write it followed.
            ran = _motor_seconds(slow, where, "2", started=echoes[where])
            assert abs(ran - TWELVE_RUN_SEC) < 0.001, f"cover {where} ran {ran}s"
            state = hass.states.get(f"cover.cover_{where}")
            assert state.attributes[ATTR_CURRENT_POSITION] == 40
            assert state.state == CoverState.OPEN


# ------------------------------------------------- the motor's own clock (0.4.4)
# The bus costs a fixed amount per movement: the actuator answers our direction frame
# with its own "moving" status about half a second later, and keeps turning about a
# tenth of a second past our stop. The configured times are motor times, so the run has
# to be measured between those two instants - which is what the tests below pin.
TUNED_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_tuned:
      where: '84'
      name: Cover Tuned
      shutter_run: 30
      roll: 1
      start_delay: 1.2
      stop_latency: 0.4
"""
TUNED_ENTITY = "cover.cover_tuned"


async def test_the_run_is_timed_from_the_actuators_own_moving_status(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The finding of 0.4.4, on an idle queue: the motor starts when the actuator says.

    The frame is written at once, so 0.4.3 timed the run from that instant and stopped
    it 0.57 s of motor early - about 0.45 s in the measurements, 3-9 cm on a 195 cm
    window, and only on runs that did not end at an end stop (those hid it, which is
    why the calibration never caught it).

    This actuator answers in 1.2 s rather than the 0.55 s of the replays above, which
    is what makes the assertions below tell the answer apart from the half-second
    fallback: the run is 0.7 s longer than 0.4.3 would have made it, and the estimate
    stands still for all of it.

    Mutation caught: dropping the re-base in `_apply_motor_start` (the stop is queued
    0.7 s early and the estimate reads 22 % half way), re-basing the clock without
    re-arming the timed stop (the stop is queued 0.7 s early alone), and re-basing on
    every "moving" frame instead of the first (the second one, 0.3 s later, would move
    the whole run with it).
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            assert slow.write_next() == "*2*1*81##"  # an empty queue: written at once
            await hass.async_block_till_done()

            # A second and a bit in, the estimate believes the model's half second and
            # has 0.7 s of travel on the clock ...
            await _advance_exact(hass, freezer, SLOW_MOTOR_ECHO_SEC)
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 2
            started = dt_util.utcnow()

            # ... and then the actuator says it is only starting now, and is believed:
            # the whole run is still ahead of it. (On the measured gateway the answer
            # comes 0.57 s after the frame and this correction is 2 cm.)
            await feed_event(hass, cover, "*2*1*81##")
            assert hass.states.get(ENTITY).state == CoverState.OPENING
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 0

            # A second copy of the same status is not a second start: the motor starts
            # once, and a gateway that repeats itself must not restart the run - the
            # shutter would then overshoot its target by everything it had travelled.
            await _advance_exact(hass, freezer, 0.3)
            await feed_event(hass, cover, "*2*1*81##")

            # Six seconds of motor is half the run to 40 %.
            await _advance_exact(hass, freezer, 5.7)
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 20
            assert len(slow.queue) == 0

            # The stop is not queued a moment before it is due ...
            await _advance_exact(hass, freezer, RUN_TO_40_SEC - STOP_LATENCY_SEC - 6.1)
            assert slow.queue == []
            await _advance_exact(hass, freezer, 0.1)
            assert len(slow.queue) == 1
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

        assert abs(_motor_seconds(slow, "81", "1", started=started) - RUN_TO_40_SEC) < 0.001
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 40
        assert state.state == CoverState.OPEN


async def test_without_a_moving_status_the_run_starts_after_the_start_delay(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A gateway that never relays the status: the run is timed from the frame + 0.5 s.

    That is what `start_delay` is for, and it is the only thing it is for - an actuator
    that answers is believed instead. Half a second of a 30 s run is 1 % of the window,
    which is the error 0.4.3 had on every run.

    Mutation caught: `start_delay` unused (the stop leaves half a second early again).
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            written = dt_util.utcnow()
            assert slow.write_next() == "*2*1*81##"
            await hass.async_block_till_done()

            # Nothing says the motor started, so the model's own half second stands.
            await _advance_exact(hass, freezer, RUN_TO_40_SEC - STOP_LATENCY_SEC)
            assert slow.queue == [], "the half second of `start_delay` was not counted"
            await _advance_exact(hass, freezer, START_DELAY_SEC)
            assert len(slow.queue) == 1
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

        assert slow.instant("*2*1*81##") == written
        assert abs(_motor_seconds(slow, "81", "1") - RUN_TO_40_SEC) < 0.001
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 40


async def test_a_moving_status_long_after_our_command_leaves_the_clock_alone(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Only the actuator's *answer* re-bases the run, not any later frame.

    Some gateways repeat the direction while the shutter runs, and a keypad press in
    the direction a run is already going produces the same frame. Two seconds past the
    delivery neither can be the answer to our command any more, and moving the clock
    then would restart a run that is half over - the shutter would sail past its
    target by everything it had already travelled.

    Mutation caught: dropping the `start_delay + MOTOR_START_WINDOW_SEC` test (the stop
    then leaves 12 s after the late frame, four seconds of motor too late).
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            assert slow.write_next() == "*2*1*81##"
            await hass.async_block_till_done()

            # Well past `start_delay` + the echo window (0.5 + 1.5 s).
            await _advance_exact(hass, freezer, 4.0)
            await feed_event(hass, cover, "*2*1*81##")
            assert hass.states.get(ENTITY).state == CoverState.OPENING
            # 3.5 s of motor, unchanged by the frame that just arrived.
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 12

            await _advance_exact(
                hass, freezer, START_DELAY_SEC + RUN_TO_40_SEC - STOP_LATENCY_SEC - 4.0
            )
            assert len(slow.queue) == 1
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

        assert abs(_motor_seconds(slow, "81", "1") - RUN_TO_40_SEC) < 0.001
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 40


async def test_a_moving_status_that_arrives_after_the_stop_was_due_changes_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A run so short that the stop is queued before the actuator answers.

    A 40 % tilt is 1.2 s of motor and the actuator can take longer than that to say it
    has started. The stop is queued by then - it fell due on the clock the delivery
    armed - and the motor time it will freeze is measured from that same clock;
    re-basing the run onto an answer that arrives afterwards would freeze the estimate
    on a motor time the shutter never spent, and the slats would sit wherever the
    arithmetic landed.

    Mutation caught: dropping the `_pending_stop` guard from `_apply_motor_start`
    (the cover then reads tilt 3 instead of 47).
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML):
        cover = entity_object(hass, COVER, "2-85")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER,
                "set_cover_tilt_position",
                {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 40},
                blocking=True,
            )
            assert slow.write_next() == "*2*1*85##"
            await hass.async_block_till_done()

            # 0.5 + 1.2 - 0.1: the run is over, and the stop is queued behind a busy
            # worker, before the actuator has said anything at all.
            await _advance_exact(hass, freezer, START_DELAY_SEC + 1.2 - STOP_LATENCY_SEC)
            assert [frame for frame, _, _ in slow.queue] == ["*2*0*85##"]

            # It answers here, still inside the window in which an answer could be
            # ours, and with our stop already queued.
            await _advance_exact(hass, freezer, 0.2)
            await feed_event(hass, cover, "*2*1*85##")
            assert slow.write_next() == "*2*0*85##"
            await hass.async_block_till_done()

        state = hass.states.get(SLAT_ENTITY)
        # The stop frame left 0.2 s after it was queued, so the motor ran 1.4 s of the
        # three-second slat phase instead of the 1.2 s asked for: 47 %, not 40 %.
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 47
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert slow.frames == ["*2*1*85##", "*2*0*85##"]


async def test_a_stop_on_a_run_that_was_re_based_still_counts_the_coasting(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The motor coasts past our stop whatever the clock it is measured against.

    Both frames of a short tilt run can be queued together - the user changes their
    mind while a scene is still being written - and the movement is then re-based onto
    its own delivery *after* the stop has been queued. The motor time to freeze is the
    one that really existed, from the delivery of the direction frame to a tenth of a
    second past the delivery of the stop; on a three-second slat phase that tenth is
    three points of tilt, which is the whole difference between the two arms of
    `_apply_stop_delivery`.

    Mutation caught: dropping `stop_latency` from the re-based arm (tilt 17, not 20).
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER,
                "set_cover_tilt_position",
                {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 100},
                blocking=True,
            )
            await _advance_exact(hass, freezer, 0.5)
            await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True)
            # Behind its own movement, as ever: the queue never inverts a device.
            assert [frame for frame, _, _ in slow.queue] == ["*2*1*85##", "*2*0*85##"]

            # The direction frame reaches the bus here, so the motor starts half a
            # second later - after the stop was queued, which is what re-bases the run.
            await _advance_exact(hass, freezer, 0.5)
            assert slow.write_next() == "*2*1*85##"
            await hass.async_block_till_done()

            await _advance_exact(hass, freezer, 1.0)
            assert slow.write_next() == "*2*0*85##"
            await hass.async_block_till_done()

        state = hass.states.get(SLAT_ENTITY)
        # The motor ran from 1.5 s (the delivery plus the start delay) to 2.1 s (the
        # stop plus the coasting): 0.6 s of the three-second slat phase.
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 20
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert state.state == CoverState.OPEN


# A direction status the gateway relays at the instant it writes our own frame: too
# soon to be a motor (`MOTOR_MIRROR_WINDOW_SEC`), and the one shape that would give
# back the whole `start_delay` on every run if it were believed.
MIRRORED_ECHO_SEC = 0.02


class YieldingCommandPath(SlowCommandPath):
    """A command path whose `send` suspends before it takes a stop frame.

    `MyHOMEGatewayHandler.send` happens not to await anything today - `_enqueue` is
    synchronous - but nothing in its contract promises that, and a semaphore, a lock
    or a backpressure wait would all put an `await` there. While it is suspended the
    event loop keeps running the monitor session, so `answer` is the bus frame that
    arrives in exactly that gap: dispatched once, on the first stop frame, after the
    caller has computed the position to freeze and before the stop is on record.
    """

    def __init__(self, entity: Any, answer: str) -> None:
        super().__init__()
        self._entity = entity
        self._answer: str | None = answer

    async def send(
        self,
        message: Any,
        *,
        on_delivered: Any = None,
        on_dropped: Any = None,
    ) -> bool:
        if self._answer is not None and str(message).startswith("*2*0*"):
            answer, self._answer = self._answer, None
            await asyncio.sleep(0)
            self._entity.handle_event(OWNEvent.parse(answer))
        return await super().send(message, on_delivered=on_delivered, on_dropped=on_dropped)


async def test_a_stop_inside_the_start_delay_freezes_where_the_motor_really_got_to(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The user changes their mind before the motor has even started.

    `close_cover` at t = 0, `stop_cover` a tenth of a second later, and the stop frame
    written at t = 0.5 because another cover's frame was in front of it. The motor
    started at t = 0.5 (`start_delay`) and stopped at t = 0.6 (`stop_latency`): it ran
    a tenth of a second, and the shutter has not left the top.

    The whole point is that the elapsed time is *signed* while the clock is still in
    the future: the queue delay has to be added to -0.4 s, not to a zero somebody
    clamped it to on the way in. Clamping it early adds the delay to a motor that had
    not started, which freezes the entity up to `start_delay` of travel past where the
    shutter is - half a second of a 30 s run, ~3 cm on a 195 cm window, in the very
    direction 0.4.4 exists to remove.

    Mutation caught: clamping `elapsed` in `async_stop_cover` instead of letting
    `_apply_stop_delivery` clamp the sum once, at the end (the cover reads 98 %).
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
            assert slow.write_next() == "*2*2*81##"  # an idle queue: written at once
            await hass.async_block_till_done()

            # A tenth of a second in, the motor has not started and the estimate says so.
            await _advance_exact(hass, freezer, 0.1)
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 100
            await hass.services.async_call(COVER, "stop_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
            assert [frame for frame, _, _ in slow.queue] == ["*2*0*81##"]

            # The queue was busy: the stop only reaches the bus at t = 0.5, the very
            # instant the motor starts. It runs for the `stop_latency` of coasting and
            # nothing more.
            await _advance_exact(hass, freezer, 0.4)
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 100
        assert state.state == CoverState.OPEN
        assert slow.frames == ["*2*2*81##", "*2*0*81##"]


async def test_a_moving_status_while_our_stop_is_being_sent_changes_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The guard against a re-base must not depend on `send` never suspending.

    `_async_send_stop` reads the position to freeze and the motor time it belongs to,
    hands the frame over, and only then records the stop. Everything in between is one
    `await`: today it never yields, but the moment it does - a semaphore, a lock, a
    backpressure wait - a "moving" status dispatched inside it would find no stop on
    record, re-base the run onto its own end, and freeze the slats at the tenth of a
    second of coasting instead of the 40 % they were sent to.

    Mutation caught: recording the pending stop *after* the await without raising the
    flag before it (the cover reads tilt 3 instead of 40).
    """
    mock_restore_cache(hass, (_closed(),))
    async with setup_myhome(hass, tmp_path, SLAT_YAML):
        cover = entity_object(hass, COVER, "2-85")
        slow = YieldingCommandPath(cover, "*2*1*85##")
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER,
                "set_cover_tilt_position",
                {ATTR_ENTITY_ID: SLAT_ENTITY, ATTR_TILT_POSITION: 40},
                blocking=True,
            )
            assert slow.write_next() == "*2*1*85##"
            await hass.async_block_till_done()

            # 40 % of a three-second slat phase is 1.2 s of motor, so the stop falls
            # due at 0.5 + 1.2 - 0.1 - and the actuator's status reaches the entity
            # while that stop is still inside `send`, 1.6 s after our own frame, well
            # within the window in which an answer can be ours.
            await _advance_exact(hass, freezer, START_DELAY_SEC + 1.2 - STOP_LATENCY_SEC)
            assert [frame for frame, _, _ in slow.queue] == ["*2*0*85##"]
            assert slow.write_next() == "*2*0*85##"
            await hass.async_block_till_done()

        state = hass.states.get(SLAT_ENTITY)
        assert state.attributes[ATTR_CURRENT_TILT_POSITION] == 40
        assert state.attributes[ATTR_CURRENT_POSITION] == 0
        assert slow.frames == ["*2*1*85##", "*2*0*85##"]


async def test_a_direction_frame_relayed_at_the_write_is_not_the_motor_starting(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A gateway that mirrors the command it writes must not disable `start_delay`.

    Nothing in `*2*1*81##` says whether it is the gateway relaying the frame it has
    just been given or the actuator answering it half a second later; only its timing
    does. A mirror taken for the motor re-bases the clock onto the write and hands back
    the whole `start_delay` on every single run - 0.4.3's error, silently, with the key
    configured and never used. So a direction status younger than
    `MOTOR_MIRROR_WINDOW_SEC` leaves the clock alone, and - just as important - does
    not consume the "once per movement" either: the real answer at 0.57 s is still
    taken.

    Mutation caught: dropping the lower bound on the acceptance window (the stop leaves
    0.53 s early, which is the shortfall the release is about).
    """
    assert MIRRORED_ECHO_SEC < cover_module.MOTOR_MIRROR_WINDOW_SEC < MOTOR_ECHO_SEC
    mock_restore_cache(hass, (State(ENTITY, CoverState.CLOSED, {ATTR_CURRENT_POSITION: 0}),))
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            assert slow.write_next() == "*2*1*81##"
            await hass.async_block_till_done()

            # The gateway relays our own frame on the monitor session, 20 ms after
            # writing it. No motor starts that fast, and the estimate does not move.
            await _advance_exact(hass, freezer, MIRRORED_ECHO_SEC)
            await feed_event(hass, cover, "*2*1*81##")
            assert hass.states.get(ENTITY).state == CoverState.OPENING
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 0

            # The actuator itself answers at the measured 0.57 s, and *is* believed.
            await _advance_exact(hass, freezer, MOTOR_ECHO_SEC - MIRRORED_ECHO_SEC)
            started = dt_util.utcnow()
            await feed_event(hass, cover, "*2*1*81##")
            assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 0

            # Had the mirror been taken for the motor, the stop would be queued here.
            await _advance_exact(
                hass, freezer, RUN_TO_40_SEC - STOP_LATENCY_SEC - (MOTOR_ECHO_SEC - MIRRORED_ECHO_SEC)
            )
            assert slow.queue == [], "the frame the gateway mirrored was taken for the motor"

            await _advance_exact(hass, freezer, MOTOR_ECHO_SEC - MIRRORED_ECHO_SEC)
            assert len(slow.queue) == 1
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

        assert abs(_motor_seconds(slow, "81", "1", started=started) - RUN_TO_40_SEC) < 0.001
        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 40
        assert state.state == CoverState.OPEN


async def test_a_keypad_run_is_not_re_timed_by_the_frames_that_follow_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, caplog: pytest.LogCaptureFixture
) -> None:
    """Contract F, unchanged by 0.4.4: a keypad run starts when its frame says it does.

    There is no command of ours to answer, so there is no bus delay to model and
    nothing to re-base: the actuator is already moving when the frame arrives. A
    repeat of the same direction while it runs must not restart the estimate.

    Mutation caught: re-basing on `_own_command` being None (the second frame then
    rewinds the estimate by ten seconds), and reaching for the delivery instant of a
    frame there never was - which `handle_event`'s catch-all would swallow, leaving
    the frame unhandled and one exception per keypad press in the log.
    """
    async with setup_myhome(hass, tmp_path, BASIC_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, "2-81")
        await feed_event(hass, cover, "*2*1*81##")  # somebody presses UP on the keypad
        assert hass.states.get(ENTITY).state == CoverState.OPENING

        # A keypad run is timed from the frame, with no half second of bus in front.
        await _advance(hass, freezer, 10)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 33

        await feed_event(hass, cover, "*2*1*81##")  # the gateway repeats it
        await _advance(hass, freezer, 5)
        assert hass.states.get(ENTITY).attributes[ATTR_CURRENT_POSITION] == 50
        assert commands.sent_frames == []
        assert "Error handling cover event" not in caplog.text


async def test_the_two_bus_costs_can_be_measured_per_cover(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`start_delay` and `stop_latency` are read off the cover, and published when set.

    A slow actuator on a long bus: 1.2 s before the motor turns and 0.4 s of coasting
    after the stop, so the 18 s run spans 18.8 s between the two frames.

    Mutation caught: hard-coding either default in the entity instead of reading the
    configured value.
    """
    mock_restore_cache(hass, (State(TUNED_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, TUNED_YAML):
        state = hass.states.get(TUNED_ENTITY)
        assert state.attributes["Start delay"] == 1.2
        assert state.attributes["Stop latency"] == 0.4

        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: TUNED_ENTITY, ATTR_POSITION: 40}, blocking=True
            )
            assert slow.write_next() == "*2*2*84##"
            await hass.async_block_till_done()

            # 100 -> 40 on a 30 s run is 18 s of motor: 1.2 + 18 - 0.4 between the
            # two frames, and not a millisecond before it.
            await _advance_exact(hass, freezer, 1.2 + 18.0 - 0.4 - 0.1)
            assert slow.queue == []
            await _advance_exact(hass, freezer, 0.1)
            assert len(slow.queue) == 1
            assert slow.write_next() == "*2*0*84##"
            await hass.async_block_till_done()

        ran = slow.instant("*2*0*84##") - slow.instant("*2*2*84##")
        assert abs(ran.total_seconds() - (1.2 + 18.0 - 0.4)) < 0.001
        assert hass.states.get(TUNED_ENTITY).attributes[ATTR_CURRENT_POSITION] == 40

        # A *free* run anticipates nothing: no stop frame ends it, the actuator's own
        # end stop does, and the estimate settles a full 12 s of motor after the start.
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(COVER, "close_cover", {ATTR_ENTITY_ID: TUNED_ENTITY}, blocking=True)
            assert slow.write_next() == "*2*2*84##"
            await hass.async_block_till_done()

            await _advance_exact(hass, freezer, 1.2 + 12.0 - 0.2)
            assert hass.states.get(TUNED_ENTITY).state == CoverState.CLOSING
            await _advance_exact(hass, freezer, 0.2)
            assert hass.states.get(TUNED_ENTITY).state == CoverState.CLOSED
        assert slow.queue == []


async def test_the_default_bus_costs_are_not_published(hass: HomeAssistant, tmp_path) -> None:
    """Every cover has them; only a cover that was measured says so."""
    async with setup_myhome(hass, tmp_path, BASIC_YAML):
        attributes = hass.states.get(ENTITY).attributes
        assert "Start delay" not in attributes
        assert "Stop latency" not in attributes


@pytest.mark.slow
async def test_twelve_covers_from_intermediate_positions_all_reach_their_targets(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The measurement that opened 0.4.4: twelve shutters, none of them at an end stop.

    Every run that started from an end stop landed within a centimetre or two, and
    every run that started half way stopped short by the same constant - the bus
    latency, which the timed model had nowhere to put. Here each cover starts from its
    own intermediate position and is sent to its own target, the queue staggers the
    twelve frames and the actuators answer each of them in their own time, and what
    must hold for all twelve is that the motor ran the seconds the model asked for, to
    a millisecond. That is 0.006 % of the window; the 1 % the specification asks for
    would be 0.18 s, which is less than the bus latency this release is about.
    """
    starts = {where: 30 + 5 * index for index, where in enumerate(TWELVE_WHERES)}
    targets = {where: 90 - 4 * index for index, where in enumerate(TWELVE_WHERES)}
    mock_restore_cache(
        hass,
        tuple(
            State(f"cover.cover_{where}", CoverState.OPEN, {ATTR_CURRENT_POSITION: starts[where]})
            for where in TWELVE_WHERES
        ),
    )
    async with setup_myhome(hass, tmp_path, TWELVE_YAML):
        covers = {where: entity_object(hass, COVER, f"2-{where}") for where in TWELVE_WHERES}
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            for where in TWELVE_WHERES:
                await hass.services.async_call(
                    COVER,
                    "set_cover_position",
                    {ATTR_ENTITY_ID: f"cover.cover_{where}", ATTR_POSITION: targets[where]},
                    blocking=True,
                )
            assert len(slow.queue) == 12
            # Nothing has started yet - and nothing may drift *backwards* either: the
            # clock of each of these runs is half a second in the future, and an
            # estimate that took that at face value would report every shutter moving
            # the wrong way until its motor caught up.
            for where in TWELVE_WHERES:
                assert (
                    hass.states.get(f"cover.cover_{where}").attributes[ATTR_CURRENT_POSITION]
                    == starts[where]
                )

            # The worker writes one frame every 100 ms.
            written: list[str] = []
            for index in range(12):
                if index:
                    await _advance_exact(hass, freezer, FRAME_GAP_SEC)
                written.append(slow.write_next())
                await hass.async_block_till_done()

            # Each actuator answers its own frame `SLOW_MOTOR_ECHO_SEC` later, in the
            # order the frames were written, and the run is timed from that answer.
            echoes: dict[str, datetime] = {}
            for index, frame in enumerate(written):
                await _advance_exact(
                    hass, freezer, SLOW_MOTOR_ECHO_SEC - 11 * FRAME_GAP_SEC if not index else FRAME_GAP_SEC
                )
                where = _frame_where(frame)[1]
                echoes[where] = dt_util.utcnow()
                await feed_event(hass, covers[where], frame)
                assert hass.states.get(f"cover.cover_{where}").state in (
                    CoverState.OPENING,
                    CoverState.CLOSING,
                )

            # Every stop falls due `modelled - stop_latency` after its own answer.
            modelled = {
                where: covers[where]._travel_time(  # noqa: SLF001
                    cover_module.OPENING if targets[where] > starts[where] else cover_module.CLOSING,
                    starts[where],
                    100,
                    targets[where],
                    100,
                )
                for where in TWELVE_WHERES
            }
            due = sorted(
                (echoes[where] + timedelta(seconds=modelled[where] - STOP_LATENCY_SEC), where)
                for where in TWELVE_WHERES
            )
            for instant, where in due:
                delta = (instant - dt_util.utcnow()).total_seconds()
                if delta > 0:
                    await _advance_exact(hass, freezer, delta)
                if f"*2*0*{where}##" in slow.frames:
                    # Two runs happened to end at the same instant; this one went out
                    # with the other, which is exactly what the assertion below asked.
                    continue
                assert f"*2*0*{where}##" in [frame for frame, _, _ in slow.queue], (
                    f"cover {where} did not stop when it was due"
                )
                while slow.queue:
                    slow.write_next()
                    await hass.async_block_till_done()

        for where in TWELVE_WHERES:
            direction = "1" if targets[where] > starts[where] else "2"
            ran = _motor_seconds(slow, where, direction, started=echoes[where])
            assert abs(ran - modelled[where]) < 0.001, f"cover {where} ran {ran}s, modelled {modelled[where]}s"
            state = hass.states.get(f"cover.cover_{where}")
            assert state.attributes[ATTR_CURRENT_POSITION] == targets[where]


# ------------------------------------------- a deadline that fires too early (0.4.4)
# The failure of 2026-09-08 18:47, on the installation this release was measured on:
# nine covers commanded at once, a command queue writing about one frame every 1.2 s,
# and one cover told to go from 100 % to 25 % - a run of 11.25 s. Its direction frame
# reached the bus 11.6 s after it was queued, which is the very instant its stop fell
# due on the clock the *enqueue* had set (0.5 + 11.25 - 0.1). The run was re-based onto
# the delivery as it must be, and the stop went out a tenth of a second behind the
# direction frame all the same: the motor had turned for a tenth of a second, the
# shutter stayed at the top and the entity froze on the 25 % it never reached.
#
# The rule these tests pin is the one thing that makes a late delivery harmless: a run
# ends when *its own* clock says it does, and a timer armed against a clock that has
# since moved ends nothing at all.
LATE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    cover_late:
      where: '81'
      name: Cover Late
      shutter_run: 15
      roll: 1
"""
LATE_ENTITY = "cover.cover_late"
# 100 % -> 25 % on a 15 s linear run.
LATE_RUN_SEC = 11.25
# What the queue cost that frame: eight covers ahead of it at the gateway's own pace.
LATE_QUEUE_SEC = 11.6


async def test_a_deadline_that_fired_before_the_re_base_stops_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The replay of the failure above: the delivery lands on the old deadline.

    Two things fire here that must both come to nothing - the timer that had already
    been handed to the loop when the delivery re-based the clock (nothing can take
    such a timer back, so it carries the arming it belongs to and is dropped by it),
    and a timer that goes off early for any other reason at all (the arithmetic of the
    run says how much of it is left, and that is the answer). Only then does the
    actuator's own "moving" status arrive, and the stop goes out a whole run after
    *that*.

    Mutation caught: sending the stop from a deadline whose run still has seconds to
    go - the shutter then stops a tenth of a second after it started, at the top of
    the window, with the entity reading the 25 % it never reached.
    """
    mock_restore_cache(hass, (State(LATE_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, LATE_YAML):
        cover = entity_object(hass, COVER, "2-81")
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: LATE_ENTITY, ATTR_POSITION: 25}, blocking=True
            )
            # Eight covers ahead of it: the frame reaches the bus a hair before the
            # stop was due on the clock the enqueue set.
            await _advance_exact(hass, freezer, LATE_QUEUE_SEC)
            delivered = dt_util.utcnow()
            assert slow.write_next() == "*2*2*81##"
            await hass.async_block_till_done()
            assert slow.queue == []

            # The deadline of that clock, running after the delivery has moved it: the
            # loop was holding it when the re-base happened. It belongs to an arming
            # that is over, and it must do nothing.
            await cover._async_movement_deadline(  # noqa: SLF001
                cover._stop_timer_generation - 1,  # noqa: SLF001
                dt_util.utcnow(),
            )
            assert slow.queue == []

            # And the same again through the loop itself, at the instant the old
            # deadline fell due, with every timer in the house fired early.
            await _advance_exact(hass, freezer, START_DELAY_SEC + LATE_RUN_SEC - STOP_LATENCY_SEC - LATE_QUEUE_SEC)
            async_fire_time_changed_exact(hass, dt_util.utcnow() + timedelta(milliseconds=1), fire_all=True)
            await hass.async_block_till_done()
            assert slow.queue == [], "the stop went out while the motor was still starting"
            assert hass.states.get(LATE_ENTITY).state == CoverState.CLOSING
            assert hass.states.get(LATE_ENTITY).attributes[ATTR_CURRENT_POSITION] == 100

            # The actuator answers 0.57 s after the write, and the run is timed from
            # there (0.4.4): the stop is due a whole run later, less the coasting.
            await _advance_exact(
                hass,
                freezer,
                (delivered + timedelta(seconds=MOTOR_ECHO_SEC) - dt_util.utcnow()).total_seconds(),
            )
            started = dt_util.utcnow()
            await feed_event(hass, cover, "*2*2*81##")
            assert slow.queue == []

            await _advance_exact(hass, freezer, LATE_RUN_SEC - STOP_LATENCY_SEC)
            assert len(slow.queue) == 1, "the stop did not go out at the end of the run"
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

        # The motor ran the seconds the model asked for, from the actuator's own word
        # that it had started to a tenth of a second past our stop.
        assert abs(_motor_seconds(slow, "81", "2", started=started) - LATE_RUN_SEC) < 0.001
        assert slow.instant("*2*0*81##") == started + timedelta(seconds=LATE_RUN_SEC - STOP_LATENCY_SEC)
        state = hass.states.get(LATE_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 25
        assert state.state == CoverState.OPEN


async def test_a_delivery_after_twice_the_run_still_gets_a_whole_run(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A frame that waits in the queue for longer than two runs.

    Nothing about the queue shortens the movement: the deadline that falls due while
    the frame is still waiting only holds a timer in place (it cannot stop a motor
    that has not started, and its stop would be *written before* the direction frame),
    and the real one is armed when the gateway says the frame has left.

    Mutation caught: sending the stop from the deadline that falls due during the wait
    (the shutter then never stops), and arming the real one from anything but the
    delivery.
    """
    mock_restore_cache(hass, (State(LATE_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, LATE_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            await hass.services.async_call(
                COVER, "set_cover_position", {ATTR_ENTITY_ID: LATE_ENTITY, ATTR_POSITION: 25}, blocking=True
            )
            # Twice the run and more, with the frame still in the queue.
            await _advance_exact(hass, freezer, 2 * LATE_RUN_SEC + 1.0)
            assert slow.queue and slow.queue[0][0] == "*2*2*81##"
            assert hass.states.get(LATE_ENTITY).state == CoverState.CLOSING
            # The estimate is optimistic while the frame waits - it was started at the
            # enqueue so that the entity reacts to the service call at once - and after
            # two runs of waiting it has walked past the target and down to the bottom.
            # The delivery puts it back where the shutter really is; nothing else does.
            assert hass.states.get(LATE_ENTITY).attributes[ATTR_CURRENT_POSITION] == 0

            delivered = dt_util.utcnow()
            slow.write_next()
            await hass.async_block_till_done()
            assert slow.queue == []
            assert hass.states.get(LATE_ENTITY).attributes[ATTR_CURRENT_POSITION] == 100

            # 0.5 + 11.25 - 0.1 after the write, and not a second earlier.
            await _advance_exact(hass, freezer, START_DELAY_SEC + LATE_RUN_SEC - STOP_LATENCY_SEC - 0.05)
            assert slow.queue == []
            await _advance_exact(hass, freezer, 0.05)
            assert slow.write_next() == "*2*0*81##"
            await hass.async_block_till_done()

        assert abs(_motor_seconds(slow, "81", "2") - LATE_RUN_SEC) < 0.001
        assert slow.instant("*2*0*81##") == delivered + timedelta(
            seconds=START_DELAY_SEC + LATE_RUN_SEC - STOP_LATENCY_SEC
        )
        state = hass.states.get(LATE_ENTITY)
        assert state.attributes[ATTR_CURRENT_POSITION] == 25
        assert state.state == CoverState.OPEN


# A queue that writes a frame every 1.2 s, the pace the nine-cover scene measured on
# the real bus - five times the run below, so every cover's stop falls due on the
# enqueue clock long before its own frame has left.
SLOW_FRAME_GAP_SEC = 1.2
# 8 % of a 30 s linear run.
SHORT_RUN_SEC = 2.4


@pytest.mark.slow
async def test_twelve_covers_on_a_queue_slower_than_their_runs_all_reach_their_targets(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Twelve short runs behind a queue that is slower than any of them.

    The condition of the 2026-09-08 failure, generalised: every cover but the first is
    handed its frame long after the stop of that run was due on the clock its enqueue
    set, and the twelfth waits more than five runs. What must hold for all twelve is
    the same as ever - the motor ran the seconds the model asked for, and the shutter
    is on its target.
    """
    starts = {where: 30 + 5 * index for index, where in enumerate(TWELVE_WHERES)}
    targets = {where: starts[where] + 8 for where in TWELVE_WHERES}
    mock_restore_cache(
        hass,
        tuple(
            State(f"cover.cover_{where}", CoverState.OPEN, {ATTR_CURRENT_POSITION: starts[where]})
            for where in TWELVE_WHERES
        ),
    )
    async with setup_myhome(hass, tmp_path, TWELVE_YAML):
        slow = SlowCommandPath()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", slow.send):
            for where in TWELVE_WHERES:
                await hass.services.async_call(
                    COVER,
                    "set_cover_position",
                    {ATTR_ENTITY_ID: f"cover.cover_{where}", ATTR_POSITION: targets[where]},
                    blocking=True,
                )
            assert len(slow.queue) == 12

            # The worker writes one frame every 1.2 s; each stop is written when it
            # falls due, `start_delay + run - stop_latency` after its own frame left,
            # and jumps the queue to get there (0.4.3). The two never collide.
            stop_delay = START_DELAY_SEC + SHORT_RUN_SEC - STOP_LATENCY_SEC
            schedule = sorted(
                [(SLOW_FRAME_GAP_SEC * index, False) for index in range(12)]
                + [(SLOW_FRAME_GAP_SEC * index + stop_delay, True) for index in range(12)]
            )
            previous = 0.0
            for instant, is_stop in schedule:
                await _advance_exact(hass, freezer, instant - previous)
                previous = instant
                frame = slow.write_next()
                assert frame.startswith("*2*0*") is is_stop, f"unexpected {frame} at {instant}s"
                await hass.async_block_till_done()
            assert slow.queue == []

        for where in TWELVE_WHERES:
            ran = _motor_seconds(slow, where, "1")
            assert abs(ran - SHORT_RUN_SEC) < 0.001, f"cover {where} ran {ran}s"
            state = hass.states.get(f"cover.cover_{where}")
            assert state.attributes[ATTR_CURRENT_POSITION] == targets[where]
            assert state.state == CoverState.OPEN
