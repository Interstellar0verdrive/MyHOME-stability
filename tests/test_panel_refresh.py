"""A calibration written now reaches the shutters now, without reloading the entry.

Up to 0.5.0 there was one way for a stored calibration to reach a cover: reload the
config entry. The entity reads its travel model in its constructor, so the gateway was
taken down and built again for every saved measurement - acceptable once, at the end of
a guided conversation, and absurd on a panel where the user assigns a profile to twelve
windows in a row and each assignment would take every light, sensor and shutter of the
house away for a second or two.

0.6.0 (plan decision 4) sends `SIGNAL_CALIBRATION_CHANGED` instead. Every cover of that
gateway re-runs the *same* resolution its constructor ran - against the cover block as
`myhome.yaml` wrote it (`CONF_COVERS_FROM_FILE`) plus the store as it now is - and swaps
its numbers in place. What this file holds is that the swap is complete (the numbers, the
derived phases, the tilt controls, the published attributes, the merged configuration in
`hass.data`), that it agrees with the panel's own read path key for key, that nothing
reloads, and the one thing a swap must never do: change the arithmetic under a shutter
that is running.
"""

from __future__ import annotations

import random
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER,
    CoverEntityFeature,
    CoverState,
)
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import async_fire_time_changed, mock_restore_cache

from custom_components.myhome import panel_write
from custom_components.myhome.calibration_store import (
    cover_calibration_data,
    cover_profile_data,
    loaded_store,
)
from custom_components.myhome.const import (
    ATTR_CALIBRATION_SOURCE,
    CONF_COVERS_FROM_FILE,
    CONF_HEIGHT,
    CONF_OPENING_TIME,
    CONF_PROFILE,
    CONF_SLAT_TIME,
    DOMAIN,
    SIGNAL_CALIBRATION_CHANGED,
)
from custom_components.myhome.panel_data import async_cover_detail, async_overview
from custom_components.myhome.panel_schemas import (
    ERROR_BUSY_CALIBRATING,
    ERROR_UNKNOWN_PROFILE,
    MEASURABLE_KEYS,
)

from .helpers_core import MAC
from .helpers_platforms import device_config, entity_object, setup_myhome
from .test_panel_parity import assert_they_agree

FIRST = "2-81"
SECOND = "2-82"
FIRST_ID = f"{MAC}-{FIRST}"
SECOND_ID = f"{MAC}-{SECOND}"
FIRST_ENTITY = "cover.hallway_shutter"
SECOND_ENTITY = "cover.landing_shutter"

HEIGHT = 195.0

# A third gateway configuration, for the two tests about a slat phase that is taken
# away while the motor is turning the slats: the file has to state one for there to be
# one to take away.
SLAT = "2-85"
SLAT_ID = f"{MAC}-{SLAT}"
SLAT_ENTITY = "cover.blind"
SLAT_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    blind:
      where: '85'
      name: Blind
      opening_time: 30
      closing_time: 29
      slat_time: 6
      tilt: true
      height: {HEIGHT}
"""

# The first shutter writes its own run times and its own travel, which is what makes
# "what the file says" and "what the profile says" two different answers for it - and
# therefore the cover that can tell a refresh resolved against the file from one that
# resolved against its own previous answer. The second says nothing at all and runs on
# the defaults until something is stored for it.
YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      opening_time: 30
      closing_time: 29
      roll: 1.2
      height: {HEIGHT}
    landing_shutter:
      where: '82'
      name: Landing Shutter
    skylight:
      where: '83'
      name: Skylight
      advanced: true
"""

# A profile with a slat phase, measured on a window of exactly the first one's height:
# assigned to it, every number arrives unscaled, which keeps the assertions about *which*
# number arrived free of arithmetic about how it was scaled.
TALL = cover_profile_data(
    "tall",
    reference_height=HEIGHT,
    opening_time=22.0,
    closing_time=21.0,
    slat_time=4.0,
    opening_roll=2.0,
    closing_roll=1.5,
)


async def refresh(hass: HomeAssistant, entry: Any) -> None:
    """Say what a panel write says when it has finished writing."""
    async_dispatcher_send(hass, SIGNAL_CALIBRATION_CHANGED.format(mac=MAC), entry.entry_id)
    await hass.async_block_till_done()


async def assign(hass: HomeAssistant, entry: Any, unique_id: str, profile: str | None) -> None:
    """Store an assignment the way the panel's `assign` command will, and publish it."""
    store = loaded_store(hass, entry)
    assert store is not None
    if profile is not None and store.profile(profile) is None:
        await store.async_set_profile(profile, TALL)
    await store.async_set_assignments({unique_id: (profile, None)})
    await refresh(hass, entry)


# ------------------------------------------------------------------ the swap itself
async def test_an_assignment_reaches_the_shutter_without_reloading_the_entry(
    hass: HomeAssistant, tmp_path
) -> None:
    """The whole of decision 4: new numbers, same entity, no reload.

    Mutation caught: dispatching nothing after a write (the shutter goes on running on
    the file until something else reloads the entry); reloading the entry anyway.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, FIRST)
        before = hass.states.get(FIRST_ENTITY)
        assert before.attributes["Opening time"] == 30.0
        assert before.attributes[ATTR_CALIBRATION_SOURCE] == "yaml"

        with patch.object(
            hass.config_entries, "async_reload", autospec=True
        ) as reload, patch.object(
            hass.config_entries, "async_schedule_reload", autospec=True
        ) as scheduled:
            await assign(hass, entry, FIRST_ID, "tall")

        assert reload.call_count == 0
        assert scheduled.call_count == 0
        # The same object, still: no entity was destroyed and rebuilt.
        assert entity_object(hass, COVER, FIRST) is entity

        state = hass.states.get(FIRST_ENTITY)
        assert state.attributes["Opening time"] == 22.0
        assert state.attributes["Closing time"] == 21.0
        assert state.attributes["Slat time"] == 4.0
        assert state.attributes["Opening roll"] == 2.0
        assert state.attributes["Closing roll"] == 1.5
        assert state.attributes["Profile"] == "tall"
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "profile tall"
        # ...and the numbers the *movement* is planned with, not only the published ones.
        assert entity._opening_time == 22.0  # noqa: SLF001
        assert entity._closing_time == 21.0  # noqa: SLF001
        assert entity._curtain_up == 18.0  # noqa: SLF001


async def test_the_shutter_and_the_panel_say_the_same_thing_after_a_refresh(
    hass: HomeAssistant, tmp_path
) -> None:
    """The parity invariant, one write later.

    `test_panel_parity.py` holds it at setup; this holds it after an in-place swap,
    which is the moment a second resolution could start disagreeing with the first.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        await assign(hass, entry, FIRST_ID, "tall")

        row = next(
            item for item in async_overview(hass, entry)["covers"] if item["unique_id"] == FIRST_ID
        )
        state = hass.states.get(FIRST_ENTITY)
        assert row["source"] == state.attributes[ATTR_CALIBRATION_SOURCE]
        assert row["origin"] == "inherited"
        assert row["values"][CONF_OPENING_TIME] == state.attributes["Opening time"]
        assert row["values"][CONF_SLAT_TIME] == state.attributes["Slat time"]
        assert row["profile"] == state.attributes["Profile"]


async def test_the_merged_configuration_follows_the_shutter(hass: HomeAssistant, tmp_path) -> None:
    """`hass.data` carries the numbers the shutter really runs on, as it does at setup.

    Everything else that reads a cover's numbers - the diagnostics, the guided flow's
    own screens - reads that dict, so a refresh that updated only the entity would leave
    two answers in the house.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        await assign(hass, entry, FIRST_ID, "tall")
        cfg = device_config(hass, COVER, FIRST)
        assert cfg[CONF_OPENING_TIME] == 22.0
        assert cfg["shutter_run"] == 22.0
        assert cfg[CONF_PROFILE] == "tall"


async def test_taking_an_assignment_away_puts_the_shutter_back_on_its_file(
    hass: HomeAssistant, tmp_path
) -> None:
    """The keys a resolution stops stating are removed, not left behind.

    Mutation caught: merging the new answer over the old one without laying the file's
    own block down again - `Profile` would go on naming a profile nobody follows any
    more, in the attributes and in `hass.data` alike.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        # Nothing is written about this one, so it runs on the numbers this integration
        # gives any shutter - which is what it has to go back to.
        defaults = hass.states.get(SECOND_ENTITY).attributes["Opening time"]
        await assign(hass, entry, SECOND_ID, "tall")
        assert hass.states.get(SECOND_ENTITY).attributes["Profile"] == "tall"
        # Assigned with no travel of its own and none in the file: the profile arrives
        # unscaled, which is what `reference_height` means when nothing else is known.
        assert hass.states.get(SECOND_ENTITY).attributes["Opening time"] == 22.0

        await assign(hass, entry, SECOND_ID, None)
        state = hass.states.get(SECOND_ENTITY)
        assert "Profile" not in state.attributes
        assert "Slat time" not in state.attributes
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "yaml"
        assert state.attributes["Opening time"] == defaults
        assert CONF_PROFILE not in device_config(hass, COVER, SECOND)


async def test_a_refresh_resolves_against_the_file_and_not_against_its_own_last_answer(
    hass: HomeAssistant, tmp_path
) -> None:
    """The copy taken at setup stays the file's, however many times it is resolved.

    The trap the lot 1-2 handoff names: `cover.async_setup_entry` writes the resolved
    model back into the validated configuration, so resolving *that* a second time would
    hand the previous answer to the precedence as though the user had typed it into
    their own file. This shutter writes 30 s in `myhome.yaml`; after a profile has been
    assigned and taken away again it must be running on 30 s, and the detail view must
    still be able to say that 30 s is what the file writes.

    Mutation caught: `async_refresh_cover_config` resolving `CONF_PLATFORMS` instead of
    `CONF_COVERS_FROM_FILE`.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        written = dict(hass.data[DOMAIN][MAC][CONF_COVERS_FROM_FILE][FIRST])
        await assign(hass, entry, FIRST_ID, "tall")
        await assign(hass, entry, FIRST_ID, None)

        assert hass.data[DOMAIN][MAC][CONF_COVERS_FROM_FILE][FIRST] == written
        assert hass.states.get(FIRST_ENTITY).attributes["Opening time"] == 30.0

        detail = async_cover_detail(hass, entry, FIRST_ID)
        opening = next(item for item in detail["keys"] if item["key"] == CONF_OPENING_TIME)
        assert opening["origin"] == "file"
        assert opening["file_value"] == 30.0
        assert opening["default_value"] is None


async def test_a_slat_phase_that_appears_brings_the_tilt_controls_with_it(
    hass: HomeAssistant, tmp_path
) -> None:
    """`slat_time` is a number a calibration can change, and three things hang off it.

    The two-phase timing, the tilt controls a cover with `tilt: true` exposes, and the
    `Slat time` attribute. A reload would have rebuilt all three; so does the swap.
    """
    yaml_text = YAML.replace(
        "      height: 195.0\n", "      height: 195.0\n      tilt: true\n"
    )
    async with setup_myhome(hass, tmp_path, yaml_text) as (entry, _commands):
        plain = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        assert hass.states.get(FIRST_ENTITY).attributes[ATTR_SUPPORTED_FEATURES] == plain

        await assign(hass, entry, FIRST_ID, "tall")
        state = hass.states.get(FIRST_ENTITY)
        assert state.attributes["Slat time"] == 4.0
        assert state.attributes[ATTR_SUPPORTED_FEATURES] == (
            plain
            | CoverEntityFeature.OPEN_TILT
            | CoverEntityFeature.CLOSE_TILT
            | CoverEntityFeature.SET_TILT_POSITION
            | CoverEntityFeature.STOP_TILT
        )

        await assign(hass, entry, FIRST_ID, None)
        state = hass.states.get(FIRST_ENTITY)
        assert "Slat time" not in state.attributes
        assert state.attributes[ATTR_SUPPORTED_FEATURES] == plain


async def test_an_advanced_shutter_publishes_no_travel_model_before_or_after(
    hass: HomeAssistant, tmp_path
) -> None:
    """An advanced cover reports its own position: there is nothing here to swap."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        await refresh(hass, entry)
        state = hass.states.get("cover.skylight")
        assert ATTR_CALIBRATION_SOURCE not in state.attributes
        assert "Opening time" not in state.attributes


# --------------------------------------------------- a shutter that is already running
async def test_a_shutter_in_motion_keeps_the_clock_and_the_plan_it_started_with(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one thing a swap must never do (0.6.0 scope, §3).

    `_travel` and `_travel_time` are each other's inverse *within one run*; that is what
    makes a stop land where the estimate says it will. A model swapped half way through
    plans the first half with one roll and finishes it with another, and the shutter ends
    up somewhere neither model ever described. So the numbers change at once - the
    attributes say so, and the next movement will use them - while the run in flight
    keeps the snapshot it started with, its clock, and the deadline armed from them.

    Mutation caught: applying the new model to `_run` while a movement is in flight;
    re-arming the deadline on the new duration.
    """
    # A known starting position: a `set_cover_position` from an unknown one is a free
    # run to the end stop, and a free run has no timed stop to be disturbed.
    mock_restore_cache(hass, (State(FIRST_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, YAML) as (entry, commands):
        entity = entity_object(hass, COVER, FIRST)
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: FIRST_ENTITY, ATTR_POSITION: 40}, blocking=True
        )
        assert commands.sent_frames == ["*2*2*81##"]
        started_at = entity._move_started_at  # noqa: SLF001
        duration = entity._move_duration  # noqa: SLF001
        running = entity._run  # noqa: SLF001
        assert duration is not None

        freezer.tick(timedelta(seconds=5))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        half_way = hass.states.get(FIRST_ENTITY).attributes[ATTR_CURRENT_POSITION]

        await assign(hass, entry, FIRST_ID, "tall")

        # The model is the new one, and says so...
        assert entity._opening_time == 22.0  # noqa: SLF001
        assert hass.states.get(FIRST_ENTITY).attributes["Closing time"] == 21.0
        # ...and the run is still the old one, term for term.
        assert entity._run is running  # noqa: SLF001
        assert entity._run.closing_roll == 1.2  # noqa: SLF001
        assert entity._move_started_at == started_at  # noqa: SLF001
        assert entity._move_duration == duration  # noqa: SLF001
        assert hass.states.get(FIRST_ENTITY).attributes[ATTR_CURRENT_POSITION] == half_way

        # ...and it lands on the position it was commanded to, on its own clock.
        freezer.tick(timedelta(seconds=duration))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert commands.sent_frames == ["*2*2*81##", "*2*0*81##"]
        assert hass.states.get(FIRST_ENTITY).attributes[ATTR_CURRENT_POSITION] == 40


async def test_the_new_model_takes_over_as_soon_as_the_run_is_over(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The deferral is one run long and not a run longer.

    Mutation caught: leaving `_run` frozen after `_finish_movement`, which would time
    every later movement by a model the shutter stopped having.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, FIRST)
        await hass.services.async_call(
            COVER, "close_cover", {ATTR_ENTITY_ID: FIRST_ENTITY}, blocking=True
        )
        await assign(hass, entry, FIRST_ID, "tall")
        assert entity._run.slat_time == 0.0  # noqa: SLF001

        await hass.services.async_call(
            COVER, "stop_cover", {ATTR_ENTITY_ID: FIRST_ENTITY}, blocking=True
        )
        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        assert entity._moving is None  # noqa: SLF001
        assert entity._run.slat_time == 4.0  # noqa: SLF001
        assert entity._run.closing_roll == 1.5  # noqa: SLF001


async def test_a_height_measured_on_one_window_rescales_only_that_window(
    hass: HomeAssistant, tmp_path
) -> None:
    """Two shutters on one profile, at two travels: the swap scales each to its own.

    The scaling is `derive_cover_from_profile`'s and is not re-done here; what this holds
    is that the refresh hands it each window's own travel, which is the one input a
    per-cover swap could get wrong by reading the profile's reference height instead.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        store = loaded_store(hass, entry)
        await store.async_set_profile("tall", TALL)
        await store.async_set_assignments(
            {FIRST_ID: ("tall", None), SECOND_ID: ("tall", HEIGHT / 2)}
        )
        await refresh(hass, entry)

        first = hass.states.get(FIRST_ENTITY)
        second = hass.states.get(SECOND_ENTITY)
        assert first.attributes["Opening time"] == 22.0
        assert second.attributes["Opening time"] < first.attributes["Opening time"]
        assert second.attributes["Height"] == HEIGHT / 2
        assert device_config(hass, COVER, SECOND)[CONF_HEIGHT] == HEIGHT / 2


async def test_a_slat_phase_taken_away_leaves_the_run_in_flight_its_slat_leg(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The last line of both travel functions is part of the frozen model too.

    `_normalise` decides whether a shutter resting on the floor still has slats to
    account for, and it is what `_travel` and `_travel_time` both end on. Reading the
    live flag there while the seconds stay frozen is the worst of both: a calibration
    that takes the slat phase away mid-run erases the whole slat leg of a run that is
    still turning the slats, so the shutter reads "slats closed" while the motor has
    three seconds of them left and the next command pays for them again.

    Mutation caught: `_normalise` reading `self._two_phase` instead of
    `self._run.two_phase`.
    """
    mock_restore_cache(
        hass,
        (
            State(
                SLAT_ENTITY,
                CoverState.OPEN,
                {ATTR_CURRENT_POSITION: 0, ATTR_CURRENT_TILT_POSITION: 100},
            ),
        ),
    )
    async with setup_myhome(hass, tmp_path, SLAT_YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, SLAT)
        assert entity._run.two_phase is True  # noqa: SLF001
        # Closing from the floor with the slats open: the whole run is the slat leg.
        await hass.services.async_call(
            COVER, "close_cover", {ATTR_ENTITY_ID: SLAT_ENTITY}, blocking=True
        )
        freezer.tick(timedelta(seconds=3))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        half_way = hass.states.get(SLAT_ENTITY).attributes[ATTR_CURRENT_TILT_POSITION]
        assert 0 < half_way < 100

        store = loaded_store(hass, entry)
        await store.async_set_calibration(
            SLAT_ID, cover_calibration_data(SLAT_ID, overrides={CONF_SLAT_TIME: 0.0})
        )
        await refresh(hass, entry)

        # The model says the shutter has no slat phase any more...
        assert entity._slat_time == 0.0  # noqa: SLF001
        assert entity._two_phase is False  # noqa: SLF001
        assert "Slat time" not in hass.states.get(SLAT_ENTITY).attributes
        # ...and the run in flight is still half way through the one it started with.
        assert entity._run.slat_time == 6.0  # noqa: SLF001
        assert entity._estimate() == (0, half_way)  # noqa: SLF001


async def test_a_reversal_after_a_refresh_is_planned_with_the_new_model(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A run that ends by being reversed, not by being stopped, still ends the deferral.

    `_finish_movement` puts the snapshot back, and every movement that follows a
    completed one therefore has the current model. A movement that follows a movement
    does not go through it: the direction is turned round under the motor and
    `_start_movement` is the only place that could take the fresh snapshot.

    Mutation caught: dropping `self._run = self._current_movement_model()` from
    `_start_movement`, after which a shutter reversed while a calibration was landing
    goes on being timed by the model it stopped having.
    """
    mock_restore_cache(hass, (State(FIRST_ENTITY, CoverState.OPEN, {ATTR_CURRENT_POSITION: 100}),))
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, FIRST)
        await hass.services.async_call(
            COVER, "close_cover", {ATTR_ENTITY_ID: FIRST_ENTITY}, blocking=True
        )
        await assign(hass, entry, FIRST_ID, "tall")
        assert entity._moving is not None  # noqa: SLF001
        assert entity._run.slat_time == 0.0  # noqa: SLF001

        freezer.tick(timedelta(seconds=2))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        # Turned round under the motor: no stop, no `_finish_movement`.
        await hass.services.async_call(
            COVER, "open_cover", {ATTR_ENTITY_ID: FIRST_ENTITY}, blocking=True
        )
        assert entity._run.slat_time == 4.0  # noqa: SLF001
        assert entity._run.opening_roll == 2.0  # noqa: SLF001
        assert entity._run.two_phase is True  # noqa: SLF001


# --------------------------------------------------------------------------------------
# The same thing again, without a script
# --------------------------------------------------------------------------------------
# Every test above is a story somebody thought of: assign, then move; move, then assign;
# take the slat phase away at exactly the wrong moment. The failure this mechanism can
# really have is the one nobody thought of - the eleventh write landing on the third
# shutter while the second is two seconds into a run and the first is being measured -
# and a story-shaped test cannot reach it.
#
# So: bounded random sequences over a fixed set of seeds, deterministic and replayable,
# asserting the four things that must hold whatever the order was.
#
#   1. A movement's frozen model never changes while that movement is in flight. Not
#      "has the same numbers": the same object, because `_travel` and `_travel_time` are
#      each other's inverse within one run and a swap half way through lands the shutter
#      somewhere neither model ever described.
#   2. Once everything has settled, every shutter's own numbers are what a fresh
#      resolution says - which is the same assertion `test_panel_parity` makes, run here
#      against an entity that has been refreshed in place a dozen times instead of built.
#   3. Nothing raises. A refusal is an answer (`busy_calibrating` while a measurement is
#      running, `write_in_progress` under the lock); anything else is a bug.
#   4. A shutter being measured is left alone: `Calibrating` survives every swap, because
#      it is not one of the attributes a swap rewrites.

STEPS = 28
SEEDS = [1, 2, 3, 5, 8, 13]

MOVES = ("open_cover", "close_cover", "set_cover_position")


def a_profile(name: str) -> dict[str, Any]:
    """A profile with numbers of its own, so a swap to it is visible in an attribute."""
    return cover_profile_data(
        name,
        reference_height=HEIGHT,
        opening_time=18.0 + len(name),
        closing_time=17.0 + len(name),
        slat_time=float(len(name) % 5),
        opening_roll=1.5 + len(name) / 10,
        closing_roll=1.4 + len(name) / 10,
    )


async def _a_write(
    hass: HomeAssistant, entry: Any, store: Any, rng: random.Random, unique_id: str
) -> tuple[str, Any]:
    """One of the panel's writes, chosen at random, as the command layer makes it."""
    what = rng.choice(
        ("assign", "unassign", "set_travel", "cover_edit", "cover_forget", "profile_edit")
    )
    if what == "assign":
        name = rng.choice(["tall", "short"])
        return what, lambda e, s: panel_write.async_assign(
            hass,
            e,
            s,
            assignments=[
                {"cover_unique_id": unique_id, "profile": name, "height": rng.choice([150, 195])}
            ],
            order=None,
        )
    if what == "unassign":
        return what, lambda e, s: panel_write.async_assign(
            hass, e, s, assignments=[{"cover_unique_id": unique_id, "profile": None}], order=None
        )
    if what == "set_travel":
        return what, lambda e, s: panel_write.async_set_travel(
            hass, e, s, cover_unique_id=unique_id, height=rng.choice([120, 195, None])
        )
    if what == "cover_edit":
        key = rng.choice([CONF_OPENING_TIME, CONF_SLAT_TIME])
        value = rng.choice([None, 12.0, 3.0])
        return what, lambda e, s: panel_write.async_cover_edit(
            hass,
            e,
            s,
            cover_unique_id=unique_id,
            overrides={key: value},
            height=None,
            height_given=False,
        )
    if what == "cover_forget":
        return what, lambda e, s: panel_write.async_cover_forget(
            hass, e, s, cover_unique_id=unique_id
        )
    name = rng.choice(["tall", "short"])
    numbers = a_profile(name)
    return what, lambda e, s: panel_write.async_profile_edit(
        hass,
        e,
        s,
        name=name,
        values={key: numbers[key] for key in MEASURABLE_KEYS},
        reference_height=rng.choice([150.0, HEIGHT]),
    )


@pytest.mark.parametrize("seed", SEEDS)
async def test_any_order_of_writes_and_movements_leaves_a_shutter_we_can_describe(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, seed: int
) -> None:
    """Twenty-eight steps in an order nobody chose, six times over, and four invariants.

    The steps are writes (the real commands, through `panel_write.async_write`, so the
    lock and the signal are the real ones), movements, stops, ticks of the clock and
    guided-calibration sessions opening and closing. The seeds are fixed, so a failure is
    a failure somebody can replay rather than a flake to be re-run until it goes away.

    Mutation caught: `_start_movement` not taking its snapshot - two of the six seeds
    fail, which is the point of running six. (The two neighbouring mutations are each
    caught by a story-shaped test rather than by this one, and are named here so the
    division of labour is on the page: `_finish_movement` not restoring the snapshot
    fails `test_a_reversal_after_a_refresh_is_planned_with_the_new_model`, and
    `_publish_travel_attributes` taking `Calibrating` away with the travel block fails
    `test_websocket_api.py::test_a_measurement_that_opens_while_a_write_is_being_applied`
    - the only state in which a swap and a session overlap, because every write is
    refused while a measurement is running.)
    """
    rng = random.Random(seed)
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        store = loaded_store(hass, entry)
        for name in ("tall", "short"):
            await store.async_set_profile(name, a_profile(name))

        entities = {
            FIRST_ENTITY: entity_object(hass, COVER, FIRST),
            SECOND_ENTITY: entity_object(hass, COVER, SECOND),
        }
        ids = {FIRST_ENTITY: FIRST_ID, SECOND_ENTITY: SECOND_ID}
        # The plan each run is being flown under. Re-taken after every *movement*
        # command, because a command may legitimately plan a new run (a reversal under
        # the motor ends one movement and starts another); held across everything else,
        # which is where the invariant lives - a write, a tick of the clock or a
        # measurement starting must not touch a plan already in flight.
        frozen: dict[str, Any] = {}
        sessions: dict[str, Any] = {}

        def remember_the_plans() -> None:
            """Whatever is moving now, keep the model it is moving under."""
            for entity_id, entity in entities.items():
                if entity._moving is None:  # noqa: SLF001
                    frozen.pop(entity_id, None)
                else:
                    frozen[entity_id] = entity._run  # noqa: SLF001

        def the_plans_have_not_moved() -> None:
            for entity_id, plan in frozen.items():
                entity = entities[entity_id]
                if entity._moving is not None:  # noqa: SLF001
                    # 1. The same object, not merely the same numbers.
                    assert entity._run is plan, (seed, entity_id)  # noqa: SLF001
            # 4. ...and a shutter under the tape is left alone by every swap.
            for entity_id in sessions:
                assert entities[entity_id].calibrating is True, (seed, entity_id)
                assert hass.states.get(entity_id).attributes["Calibrating"] is True

        for step in range(STEPS):
            entity_id = rng.choice(list(entities))
            entity = entities[entity_id]
            what = rng.choice(("write", "write", "move", "tick", "stop", "session"))

            if what == "write":
                name, work = await _a_write(hass, entry, store, rng, ids[entity_id])
                try:
                    # 3. A refusal is an answer; anything else is a bug.
                    await panel_write.async_write(hass, entry, name, work)
                except panel_write.PanelError as refusal:
                    assert refusal.translation_key in (
                        ERROR_BUSY_CALIBRATING,
                        ERROR_UNKNOWN_PROFILE,
                    ), (seed, step, refusal.translation_key)
                await hass.async_block_till_done()
            elif what in ("move", "stop"):
                move = "stop_cover" if what == "stop" else rng.choice(MOVES)
                data: dict[str, Any] = {ATTR_ENTITY_ID: entity_id}
                if move == "set_cover_position":
                    data[ATTR_POSITION] = rng.randrange(0, 101, 10)
                try:
                    await hass.services.async_call(COVER, move, data, blocking=True)
                except ServiceValidationError:
                    # A shutter under the tape refuses to be driven, which is the
                    # guided calibration's own rule and not this mechanism's.
                    assert entity_id in sessions, (seed, step)
                # A movement command may plan a new run; everything else may not.
                remember_the_plans()
            elif what == "session":
                if entity_id in sessions:
                    sessions.pop(entity_id).__exit__(None, None, None)
                else:
                    held = entity.calibration_session()
                    held.__enter__()
                    sessions[entity_id] = held
                await hass.async_block_till_done()
            else:
                freezer.tick(timedelta(seconds=rng.randint(1, 9)))
                async_fire_time_changed(hass)
                await hass.async_block_till_done()

            the_plans_have_not_moved()
            remember_the_plans()


        # Everything settles: the sessions end and the clock runs past any movement.
        for held in list(sessions.values()):
            held.__exit__(None, None, None)
        sessions.clear()
        for _ in range(4):
            freezer.tick(timedelta(seconds=60))
            async_fire_time_changed(hass)
            await hass.async_block_till_done()

        assert all(entity._moving is None for entity in entities.values())  # noqa: SLF001
        # 2. ...and every shutter is running on exactly what a fresh resolution says.
        overview = async_overview(hass, entry)
        for entity_id, unique_id in ids.items():
            row = next(item for item in overview["covers"] if item["unique_id"] == unique_id)
            assert_they_agree(hass, row, entity_id, case=f"seed {seed} / {entity_id}")
            # The frozen model is the current one again, which is what makes the
            # deferral one run long and not a run longer.
            entity = entities[entity_id]
            assert entity._run == entity._current_movement_model()  # noqa: SLF001
