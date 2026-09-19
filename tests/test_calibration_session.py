"""The calibration session: the core, path A at the basic level, and the save.

The shutter here is the **fake runner** of `helpers_calibration.py` - the same 195 cm
reference window the dialog's tests use - so the numbers the session stores can be
checked against the ones it was meant to rediscover rather than against themselves. The
`myhome.yaml` under it deliberately carries numbers that are *not* the shutter's, so
that "the calibration reached the store" can be told from "the file never moved".

Three things this file is really about, beyond the walk:

* **A read never moves anything.** `get`, `attach` and `snapshot` answer and stop
  there, and a session picked up again shows where it stands instead of re-entering
  its step (lesson 5 of the panel v2, SPEC §3.5).
* **The clocks are the backend's.** The press timeout fires by itself, the lease is the
  dialog's own watchdog, and a heartbeat renews the presence and *not* the lease.
* **Nothing is written before Save**, whatever the conversation is interrupted by.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.const import CONF_NAME, STATE_CLOSING, STATE_OPEN, STATE_OPENING
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.myhome import calibration_session
from custom_components.myhome.calibration import REASON_NO_ECHO, CalibrationError
from custom_components.myhome.calibration_flow import (
    IDLE_TIMEOUT_SEC,
    MOVED_IDLE_TIMEOUT_SEC,
    PRESS_TIMEOUT_SEC,
)
from custom_components.myhome.calibration_measure import expected_cm
from custom_components.myhome.calibration_session import (
    PRESENCE_SEC,
    CalibrationSession,
    async_start,
    current,
)
from custom_components.myhome.calibration_store import (
    loaded_store,
    merged_profiles,
    resolve_cover,
)
from custom_components.myhome.const import (
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_HEIGHT,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PROFILE,
    CONF_PROFILE_WINS,
    CONF_RAW,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
    DIRECTION_CLOSE,
    DIRECTION_OPEN,
)
from custom_components.myhome.panel_data import async_overview, basic_covers, yaml_profiles
from custom_components.myhome.panel_write import PanelError

from .helpers_calibration import (
    CLOSING,
    CURTAIN_DOWN,
    CURTAIN_UP,
    HEIGHT,
    OPENING,
    ROLL_DOWN,
    ROLL_UP,
    SLAT,
    FakeRunner,
    ascent_cm,
    descent_cm,
)
from .helpers_core import MAC
from .helpers_platforms import entity_object, setup_myhome

DEVICE_KEY = "2-81"
UNIQUE_ID = f"{MAC}-{DEVICE_KEY}"
SECOND_UNIQUE_ID = f"{MAC}-2-82"
ENTITY = "cover.hallway_shutter"
COVER_NAME = "Hallway Shutter"
YAML_KEY = "front_hall_roller"
CLIENT = "3b0c7e1a-5d2f-4a8e-9c61-0e7f4b2d9a10"
OTHER_CLIENT = "8d41f6b2-7c3e-4f95-a0d8-2b6e9c1f7e33"

# The file's own numbers, which are *not* the shutter's: a fixture whose numbers are
# the fake shutter's own cannot tell "the calibration reached the store" from "nothing
# moved at all" (0.5.0 review, BUG-1).
FILE_OPENING = 30.0
FILE_CLOSING = 29.0
FILE_SLAT = 6.0
FILE_ROLL = 1.2

YAML = f"""
gateway:
  mac: {MAC}
  cover:
    {YAML_KEY}:
      where: '81'
      name: {COVER_NAME}
      opening_time: {FILE_OPENING}
      closing_time: {FILE_CLOSING}
      slat_time: {FILE_SLAT}
      roll: {FILE_ROLL}
      height: {HEIGHT}
"""

# The same, with a second basic shutter that already follows a profile: what
# `review.affected` is about, and what a profile of the same name is written over.
FOLLOWER_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    {YAML_KEY}:
      where: '81'
      name: {COVER_NAME}
      opening_time: {FILE_OPENING}
      closing_time: {FILE_CLOSING}
      slat_time: {FILE_SLAT}
      roll: {FILE_ROLL}
      height: {HEIGHT}
    landing_shutter:
      where: '82'
      name: Landing Shutter
      height: 150
      profile: tall
  cover_profiles:
    tall:
      reference_height: {HEIGHT}
      opening_time: {FILE_OPENING}
      closing_time: {FILE_CLOSING}
      slat_time: {FILE_SLAT}
      roll: {FILE_ROLL}
"""

# The same window with a `stop_latency:` written for it in the file, which is the one
# state in which following a profile changes a key nobody measured (SPEC §3.9, R4).
BUS_COST_YAML = YAML.replace(
    f"      height: {HEIGHT}\n", f"      height: {HEIGHT}\n      stop_latency: 0.35\n"
)

# A shutter whose modelled run outlasts every patience, so that a movement started
# before the clock jumps is still in flight when a timer fires.
SLOW_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    {YAML_KEY}:
      where: '81'
      name: {COVER_NAME}
      opening_time: 3000
      closing_time: 3000
      height: {HEIGHT}
"""


# --------------------------------------------------------------------------------------
# Driving a session
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Act:
    """One thing the user does, and how long they took to do it."""

    action: str
    value: Any = None
    tick: float = 0.0


async def open_session(hass: HomeAssistant, entry, **kwargs) -> CalibrationSession:
    """Start the gateway's session and let its first screen settle."""
    session = await async_start(
        hass, entry, cover_unique_id=UNIQUE_ID, client_id=CLIENT, **kwargs
    )
    await hass.async_block_till_done()
    return session


async def act(
    hass: HomeAssistant,
    session: CalibrationSession,
    one: Act,
    *,
    freezer: FrozenDateTimeFactory | None = None,
    client: str = CLIENT,
) -> dict[str, Any]:
    """One action, then everything it set in motion, then the screen it ended on.

    The snapshot is read *after* `async_block_till_done` and not out of the answer:
    what the panel sees next is the event the movement publishes when it is over, and
    a test that only looked at the answer would never see a single homing finish.
    """
    if one.tick and freezer is not None:
        freezer.tick(timedelta(seconds=one.tick))
    await session.async_act(client, session.revision, one.action, one.value)
    await hass.async_block_till_done()
    return session.snapshot()


async def walk(
    hass: HomeAssistant,
    session: CalibrationSession,
    acts,
    *,
    freezer: FrozenDateTimeFactory | None = None,
) -> dict[str, Any]:
    """Play a list of actions against the session."""
    snapshot = session.snapshot()
    for one in acts:
        snapshot = await act(hass, session, one, freezer=freezer)
    return snapshot


# The whole of path A at the basic level, as a list of what the user does. A list
# rather than a function so that any prefix of it can be replayed - which is how
# "abandoning it at any screen writes nothing" is tested.
PATH_A_BASIC: tuple[Act, ...] = (
    Act("path_a"),
    Act("begin"),
    Act("confirm_closed"),
    # The ascent, in two runs of one press each.
    Act("open_start"),
    Act("lifted_off", tick=SLAT),
    Act("lift_accept"),
    Act("confirm_closed_again"),
    Act("open_full_start"),
    Act("stopped_open", tick=OPENING),
    Act("accept_step"),
    # The travel, read with the shutter standing at the top.
    Act("submit", str(HEIGHT)),
    Act("accept_step"),
    # The descent.
    Act("close_start"),
    Act("stopped_closed", tick=CLOSING),
    Act("accept_step"),
    # The tape phase. The shutter is at the bottom, so the ascent's reading is the one
    # that needs no homing and is therefore dealt first.
    Act("tape_start"),
    Act("submit", str(ascent_cm(0.5))),
    Act("accept_step"),
    Act("submit", str(descent_cm(0.5))),
    Act("accept_step"),
    Act("submit", "tall"),
)

# How far into the walk each screen is, for the tests that stop at one.
AFTER_THE_ASCENT = 9
AFTER_THE_TRAVEL = 12


def the_store(hass: HomeAssistant, entry):
    store = loaded_store(hass, entry)
    assert store is not None
    return store


def the_profile(hass: HomeAssistant, entry, name: str = "tall") -> dict[str, Any]:
    profile = the_store(hass, entry).raw_profiles.get(name)
    assert profile is not None, the_store(hass, entry).raw_profiles
    return profile


def the_record(hass: HomeAssistant, entry, unique_id: str = UNIQUE_ID) -> dict[str, Any]:
    record = the_store(hass, entry).raw_covers.get(unique_id)
    assert record is not None, the_store(hass, entry).raw_covers
    return record


def running(entity, direction: str = DIRECTION_OPEN):
    """Make the entity report that its motor is turning, whatever the fake runner did.

    The fake runner answers the four primitives and never drives the real state
    machine, so the two questions the ending asks - "is it still moving?" and "does the
    gateway stay reserved?" - have to be posed here.
    """
    opening = direction == DIRECTION_OPEN
    return patch.multiple(
        type(entity),
        is_opening=property(lambda _self: opening),
        is_closing=property(lambda _self: not opening),
    )


# --------------------------------------------------------------------------------------
# Starting, and the refusals that come before any movement
# --------------------------------------------------------------------------------------
async def test_a_session_starts_on_the_screen_that_precedes_every_movement(
    hass: HomeAssistant, tmp_path
) -> None:
    """`start` opens a session and moves nothing, whatever it is told about the path.

    The three entrances of the panel all land on a screen the user has to press
    something on: `start` never skips a briefing, because the briefing is what tells
    somebody to go and stand in front of a window.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        snapshot = session.snapshot()
        assert snapshot["state"] == "armed"
        assert snapshot["step"] == "path"
        assert snapshot["revision"] == 1
        assert snapshot["actions"] == ["path_a"]
        assert snapshot["movement"] is None
        assert snapshot["owner"]["client_id"] == CLIENT
        assert snapshot["cover"] == {
            "unique_id": UNIQUE_ID,
            "entity_id": ENTITY,
            "name": COVER_NAME,
        }
        assert runner.log == []
        await session.async_cancel(CLIENT)


async def test_a_start_that_names_path_a_opens_on_its_warning(
    hass: HomeAssistant, tmp_path
) -> None:
    """The detail screen's "Misura di nuovo" arrives with the path already chosen."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry, path="path_a")

        assert session.snapshot()["step"] == "path_a"
        assert session.snapshot()["path"] == "path_a"
        assert session.snapshot()["actions"] == ["begin"]
        assert runner.log == []
        await session.async_cancel(CLIENT)


async def test_a_second_session_on_the_same_gateway_is_refused(
    hass: HomeAssistant, tmp_path
) -> None:
    """One session per gateway, refused and never queued (contract §2.1)."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        with pytest.raises(PanelError) as refused:
            await async_start(
                hass, entry, cover_unique_id=UNIQUE_ID, client_id=OTHER_CLIENT
            )
        assert refused.value.translation_key == "already_calibrating"
        assert refused.value.placeholders["by"] == "panel"
        await session.async_cancel(CLIENT)


async def test_a_start_is_refused_while_the_dialog_holds_a_shutter(
    hass: HomeAssistant, tmp_path
) -> None:
    """The *Configura* dialog is measuring: the panel says so rather than fighting it.

    Driven through the real options flow, because what the refusal reads is the
    `calibrating` flag the dialog's own `_claim` sets - not a flag this test invents.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        manager = hass.config_entries.options
        result = await manager.async_init(entry.entry_id)
        result = await manager.async_configure(result["flow_id"], {"next_step_id": "calibrate"})
        result = await manager.async_configure(result["flow_id"], {"next_step_id": "cover"})
        result = await manager.async_configure(result["flow_id"], {"cover": UNIQUE_ID})
        assert result["step_id"] == "path"

        with pytest.raises(PanelError) as refused:
            await async_start(hass, entry, cover_unique_id=UNIQUE_ID, client_id=CLIENT)
        assert refused.value.translation_key == "already_calibrating"
        assert refused.value.placeholders["by"] == "other"
        for flow in list(manager.async_progress()):
            manager.async_abort(flow["flow_id"])


async def test_a_start_on_a_cover_that_is_not_there_says_which_kind_of_nothing(
    hass: HomeAssistant, tmp_path
) -> None:
    """"No such shutter" and "not something this panel does" stay two answers."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        with pytest.raises(PanelError) as refused:
            await async_start(
                hass, entry, cover_unique_id=f"{MAC}-9-99", client_id=CLIENT
            )
        assert refused.value.translation_key == "unknown_cover"
        assert current(hass, entry) is None


async def test_a_start_naming_a_profile_nobody_defines_is_refused(
    hass: HomeAssistant, tmp_path
) -> None:
    """A profile that is not there cannot be the one this window is like."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        with pytest.raises(PanelError) as refused:
            await async_start(
                hass,
                entry,
                cover_unique_id=UNIQUE_ID,
                client_id=CLIENT,
                path="path_b",
                profile="nobody",
            )
        assert refused.value.translation_key == "unknown_profile"
        # ...and nothing was left in the registry to refuse the next start.
        assert current(hass, entry) is None


async def test_the_session_holds_the_shutter_for_as_long_as_it_lasts(
    hass: HomeAssistant, tmp_path
) -> None:
    """`Calibrating` is on from the first screen to the last, as in the dialog."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(entity)
        assert entity.calibrating is False

        session = await open_session(hass, entry)
        assert entity.calibrating is True
        assert async_overview(hass, entry)["measuring"]["cover_unique_id"] == UNIQUE_ID

        await session.async_cancel(CLIENT)
        assert entity.calibrating is False


# --------------------------------------------------------------------------------------
# A read never moves anything (lesson 5)
# --------------------------------------------------------------------------------------
async def test_reading_a_session_never_touches_the_shutter(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`snapshot`, `attach`, `current` and a heartbeat drive no primitive at all.

    The bug this is about killed a session in the v2 panel: a redraw that re-entered
    the step restarted its movements, so a phone waking up sent a shutter off again.
    Read it as many times as you like; the fake runner's log has to stay where the
    walk left it.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:2], freezer=freezer)
        assert session.snapshot()["step"] == "home_closed_done"
        so_far = list(runner.log)

        for _ in range(3):
            session.snapshot()
            session.attach(CLIENT)
            session.attach(OTHER_CLIENT)
            session.heartbeat(CLIENT)
            assert current(hass, entry) is session
            await hass.async_block_till_done()

        assert runner.log == so_far
        assert session.snapshot()["step"] == "home_closed_done"
        await session.async_cancel(CLIENT)


async def test_a_session_picked_up_again_does_not_re_enter_its_step(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A page reloaded in the middle of a positioning starts nothing (SPEC §3.5)."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:2], freezer=freezer)
        so_far = list(runner.log)

        freezer.tick(timedelta(seconds=PRESENCE_SEC + 5))
        snapshot = session.attach(OTHER_CLIENT)

        assert snapshot["owner"]["client_id"] == OTHER_CLIENT
        assert snapshot["step"] == "home_closed_done"
        await hass.async_block_till_done()
        assert runner.log == so_far
        await session.async_cancel(OTHER_CLIENT)


# --------------------------------------------------------------------------------------
# The ownership and the presence
# --------------------------------------------------------------------------------------
async def test_another_client_is_read_only_while_the_owner_is_present(
    hass: HomeAssistant, tmp_path
) -> None:
    """Two hands on the same buttons is the one thing ownership exists to prevent."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        assert session.attach(OTHER_CLIENT)["owner"]["client_id"] == CLIENT
        with pytest.raises(PanelError) as refused:
            await session.async_act(OTHER_CLIENT, session.revision, "path_a")
        assert refused.value.translation_key == "session_owned"

        # ...and "Prendi il controllo" is the way through, after the screen has asked.
        assert session.attach(OTHER_CLIENT, claim=True)["owner"]["client_id"] == OTHER_CLIENT
        await session.async_act(OTHER_CLIENT, session.revision, "path_a")
        assert session.snapshot()["step"] == "path_a"
        await session.async_cancel(OTHER_CLIENT)


async def test_a_heartbeat_never_takes_the_session_over(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A beat is not an act (SPEC §4.2, amended 19 Sep).

    A second tab left open on the wizard must not become the owner by doing nothing,
    forty-five seconds after the phone in the user's hand went to sleep - the phone
    would come back read-only in the middle of a tape reading, which is the very
    failure presence was added to prevent.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        revision = session.revision

        freezer.tick(timedelta(seconds=PRESENCE_SEC + 5))
        assert session.present is False
        for _ in range(3):
            assert session.heartbeat(OTHER_CLIENT) == {"owner": False, "present_until": None}

        assert session.owner == CLIENT
        assert session.revision == revision
        # ...and the owner's own beat says so and moves nothing either.
        beat = session.heartbeat(CLIENT)
        assert beat["owner"] is True and beat["present_until"] is not None
        assert session.revision == revision
        await session.async_cancel(CLIENT)


async def test_presence_lapsing_stops_nothing_and_lets_anyone_carry_on(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A locked phone loses the buttons, not the measurements (lesson 1)."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        runner = FakeRunner(entity)
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:AFTER_THE_ASCENT], freezer=freezer)
        measured = session.snapshot()["measured"]
        so_far = list(runner.log)

        freezer.tick(timedelta(seconds=PRESENCE_SEC + 5))
        await hass.async_block_till_done()

        assert session.ended is False
        assert entity.calibrating is True
        assert runner.log == so_far
        assert session.snapshot()["measured"] == measured

        # ...and the next client that *acts* simply carries on.
        await session.async_act(OTHER_CLIENT, session.revision, "accept_step")
        await hass.async_block_till_done()
        assert session.owner == OTHER_CLIENT
        assert session.snapshot()["step"] == "height"
        await session.async_cancel(OTHER_CLIENT)


# --------------------------------------------------------------------------------------
# Path A, screen by screen
# --------------------------------------------------------------------------------------
async def test_path_a_walks_the_screens_the_dialog_walks(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Every transition of SPEC §3.4 that path A goes through, in order.

    The table is derived from the dialog line by line, and this is what says the
    controller kept to it: the step, the contract's state, and - where it matters - the
    substate and what is moving.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        seen: list[tuple[str, str, str | None]] = []
        snapshot = session.snapshot()
        seen.append((snapshot["step"], snapshot["state"], snapshot["substate"]))
        for one in PATH_A_BASIC:
            snapshot = await act(hass, session, one, freezer=freezer)
            seen.append((snapshot["step"], snapshot["state"], snapshot["substate"]))

        assert seen == [
            ("path", "armed", None),
            ("path_a", "armed", None),
            ("home_closed_done", "briefing", None),
            ("open_brief", "briefing", None),
            ("open_lift", "running", "awaiting_endpoint"),
            ("lift_check", "briefing", None),
            ("closed_again", "briefing", None),
            ("open_full_brief", "briefing", None),
            ("open_top", "running", "awaiting_endpoint"),
            ("open_result", "briefing", None),
            ("height", "awaiting_reading", None),
            ("height_result", "briefing", None),
            ("close_brief", "briefing", None),
            ("close_bottom", "running", "awaiting_endpoint"),
            ("close_result", "briefing", None),
            ("tape_brief", "briefing", None),
            ("measure_ascent", "awaiting_reading", None),
            ("tape_result", "briefing", None),
            ("measure_descent", "awaiting_reading", None),
            ("tape_result", "briefing", None),
            ("profile_name", "briefing", None),
            ("summary_basic", "review", None),
        ]
        await session.async_cancel(CLIENT)


async def test_the_tape_phase_is_dealt_from_the_end_stop_the_shutter_is_at(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The ascent's reading comes first, because the descent left the shutter down.

    `order_the_readings` is the dialog's and is imported rather than copied; what this
    checks is that the session hands it the end stop it really is at.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC[:15], freezer=freezer)

        assert snapshot["step"] == "tape_brief"
        assert snapshot["position_known"] == DIRECTION_CLOSE
        assert snapshot["plan"] == [
            "home_closed",
            "open_timed",
            "height_read",
            "close_timed",
            "tape_brief",
            "half_up",
            "half_down",
            "profile_name",
            "summary",
        ]
        assert snapshot["placeholders"]["readings"] == 2
        await session.async_cancel(CLIENT)


async def test_the_measurements_are_the_reference_window_s_own(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The fake shutter *is* the 195 cm window, so the review has to rediscover it.

    Anything else means a step lost a measurement, mixed up a direction, or fed the fit
    a run time that was never spent.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC, freezer=freezer)

        measured = snapshot["measured"]
        assert measured["travel_cm"] == HEIGHT
        assert measured["travel_measured"] is True
        assert measured["opening_time_s"] == pytest.approx(OPENING, abs=0.05)
        assert measured["closing_time_s"] == pytest.approx(CLOSING, abs=0.05)
        assert measured["slat_time_s"] == pytest.approx(SLAT, abs=0.05)
        assert measured["times_adopted"] is False
        assert measured["lift"]["pressed_at"] is not None
        assert measured["lift"]["stop_written_at"] is not None
        assert measured["lift"]["late"] is False
        assert measured["ascent"] == [
            [pytest.approx(SLAT + CURTAIN_UP / 2), pytest.approx(ascent_cm(0.5))]
        ]
        assert measured["descent"] == [
            [pytest.approx(CURTAIN_DOWN / 2), pytest.approx(descent_cm(0.5))]
        ]

        fit = snapshot["fit"]
        assert fit["opening"]["roll"] == pytest.approx(ROLL_UP, abs=0.01)
        assert fit["closing"]["roll"] == pytest.approx(ROLL_DOWN, abs=0.01)
        # One reading per direction reproduces itself exactly, so there is nothing
        # left over to be a residual of.
        assert fit["opening"]["points"] == [
            {
                "motor_s": pytest.approx(SLAT + CURTAIN_UP / 2),
                "measured_cm": pytest.approx(ascent_cm(0.5)),
                "residual_cm": None,
            }
        ]
        await session.async_cancel(CLIENT)


async def test_the_review_shows_what_the_shutter_will_use_before_anything_is_written(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Before is the file's numbers, after is the profile's, and nothing is stored yet."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC, freezer=freezer)

        review = snapshot["review"]
        assert review["variant"] == "basic"
        assert review["targets"] == ["profile", "cover_only"]
        assert review["profile_name"] == "tall"
        assert review["profile_exists"] is False
        assert review["name_clash"] is None
        assert [row["key"] for row in review["rows"]] == [
            "travel_cm",
            "opening_time_s",
            "closing_time_s",
            "slat_time_s",
            "opening_roll",
            "closing_roll",
        ]
        rows = {row["key"]: row for row in review["rows"]}
        assert rows["opening_time_s"]["before"] == FILE_OPENING
        assert rows["opening_time_s"]["after"] == pytest.approx(OPENING, abs=0.05)
        assert rows["closing_roll"]["before"] == FILE_ROLL
        assert rows["closing_roll"]["after"] == pytest.approx(ROLL_DOWN, abs=0.01)
        assert review["side_effects"] == []
        assert review["affected"] == []
        assert review["accuracy_cm"] is None
        assert review["replacing"] == [
            "travel_cm",
            "opening_time_s",
            "closing_time_s",
            "slat_time_s",
            "opening_roll",
            "closing_roll",
        ]
        assert review["yaml"].startswith("cover_profiles:\n  tall:\n")

        # Nothing at all has been written by the walk that got here.
        assert the_store(hass, entry).raw_profiles == {}
        assert the_store(hass, entry).raw_covers == {}
        await session.async_cancel(CLIENT)


async def test_the_review_names_every_other_shutter_the_profile_reaches(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A name already in use is an *update*, and the screen shows who else it moves.

    That is what makes the contract's first exit acceptable (docs §12.5): the list is
    not truncated, because the point of it is seeing every window before writing.
    """
    async with setup_myhome(hass, tmp_path, FOLLOWER_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC, freezer=freezer)

        review = snapshot["review"]
        assert review["profile_exists"] is True
        assert review["name_clash"] == "file"
        assert [follower["cover_unique_id"] for follower in review["affected"]] == [
            SECOND_UNIQUE_ID
        ]
        follower = review["affected"][0]
        assert follower["name"] == "Landing Shutter"
        rows = {row["key"]: row for row in follower["rows"]}
        # A 150 cm window following a 195 cm profile: scaled, and moved by the write.
        assert rows["opening_time_s"]["before"] != rows["opening_time_s"]["after"]
        assert rows["travel_cm"]["before"] == 150.0
        await session.async_cancel(CLIENT)


async def test_the_review_says_when_the_write_moves_a_key_nobody_measured(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Following a profile brings the profile's bus costs. Nothing changes silently.

    The file writes `stop_latency:` for this window; the profile carries the
    installation's default, and a profile that wins puts its own above the file's. The
    screen says so before the user presses Save (SPEC §3.9, risk R4).
    """
    async with setup_myhome(hass, tmp_path, BUS_COST_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC, freezer=freezer)

        assert snapshot["review"]["side_effects"] == [
            {"key": "stop_latency_s", "before": 0.35, "after": pytest.approx(0.1)}
        ]
        await session.async_cancel(CLIENT)


# --------------------------------------------------------------------------------------
# Saving
# --------------------------------------------------------------------------------------
async def test_saving_path_a_writes_the_profile_and_the_assignment_and_no_own_values(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The contract's first exit, and the numbers the shutter really runs on after it.

    The panel writes the profile and assigns it, with **no** values of the cover's own:
    values of its own would hide the very profile that was measured on it (contract
    §2.7). What the shutter then moves on has to be exactly what the dialog would have
    written as overrides - the same fit, reached by the other road.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC, freezer=freezer)
        answer = await session.async_save(CLIENT, snapshot["revision"], "profile")

        profile = the_profile(hass, entry)
        assert profile[CONF_NAME] == "tall"
        assert profile[CONF_REFERENCE_HEIGHT] == HEIGHT
        assert profile[CONF_OPENING_TIME] == pytest.approx(OPENING, abs=0.05)
        assert profile[CONF_CLOSING_TIME] == pytest.approx(CLOSING, abs=0.05)
        assert profile[CONF_SLAT_TIME] == pytest.approx(SLAT, abs=0.05)
        assert profile[CONF_OPENING_ROLL] == pytest.approx(ROLL_UP, abs=0.01)
        assert profile[CONF_CLOSING_ROLL] == pytest.approx(ROLL_DOWN, abs=0.01)
        assert profile["reference_cover"] == COVER_NAME
        assert profile["measured_on"] == UNIQUE_ID
        assert profile[CONF_RAW]["client"] == "panel"
        assert profile[CONF_RAW]["save_target"] == "profile"

        record = the_record(hass, entry)
        assert record[CONF_PROFILE] == "tall"
        assert record[CONF_PROFILE_WINS] is True
        assert record[CONF_HEIGHT] == HEIGHT
        assert "overrides" not in record

        # ...and this is the point of the exit: what it runs on is the fit.
        resolved = resolve_cover(
            basic_covers(hass, entry)[UNIQUE_ID],
            profiles=merged_profiles(
                yaml_profiles(hass, entry), the_store(hass, entry).profiles
            ),
            calibration=the_store(hass, entry).calibration(UNIQUE_ID),
        )
        assert resolved.values[CONF_OPENING_TIME] == pytest.approx(OPENING, abs=0.05)
        assert resolved.values[CONF_CLOSING_TIME] == pytest.approx(CLOSING, abs=0.05)
        assert resolved.values[CONF_SLAT_TIME] == pytest.approx(SLAT, abs=0.05)
        assert resolved.values[CONF_OPENING_ROLL] == pytest.approx(ROLL_UP, abs=0.01)
        assert resolved.values[CONF_CLOSING_ROLL] == pytest.approx(ROLL_DOWN, abs=0.01)

        saved = session.snapshot()
        assert saved["state"] == "saved"
        assert saved["step"] is None
        assert saved["outcome"]["reason"] == "saved"
        assert saved["outcome"]["profile"] == "tall"
        assert saved["outcome"]["source"] == "profile tall"
        assert saved["review"] is not None
        assert answer["overview"]["covers"][0]["profile"] == "tall"
        # The shutter is given back the moment it is saved.
        assert entity_object(hass, COVER, DEVICE_KEY).calibrating is False


async def test_saving_for_this_shutter_alone_writes_its_own_values_and_no_profile(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Salva solo per questa tapparella": five numbers, and no kind of shutter named."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC, freezer=freezer)
        await session.async_save(CLIENT, snapshot["revision"], "cover_only")

        assert the_store(hass, entry).raw_profiles == {}
        record = the_record(hass, entry)
        assert CONF_PROFILE not in record
        assert record[CONF_HEIGHT] == HEIGHT
        assert record["overrides"] == {
            CONF_OPENING_TIME: pytest.approx(OPENING, abs=0.05),
            CONF_CLOSING_TIME: pytest.approx(CLOSING, abs=0.05),
            CONF_SLAT_TIME: pytest.approx(SLAT, abs=0.05),
            CONF_OPENING_ROLL: pytest.approx(ROLL_UP, abs=0.01),
            CONF_CLOSING_ROLL: pytest.approx(ROLL_DOWN, abs=0.01),
        }
        assert record[CONF_RAW]["save_target"] == "cover_only"
        assert session.snapshot()["outcome"]["source"] == "guided"


async def test_saving_for_this_shutter_alone_leaves_its_assignment_exactly_as_it_was(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Path A measured a window; it said nothing about which kind of shutter it is.

    So "Salva solo per questa tapparella" writes the five numbers and does not touch
    the profile this cover was following, nor whether that profile wins over the file.
    Clearing it would be a decision nobody made, on the one screen whose whole promise
    is that it is about this window alone.
    """
    async with setup_myhome(
        hass,
        tmp_path,
        FOLLOWER_YAML,
        calibration={
            "profiles": {},
            "covers": {
                UNIQUE_ID: {
                    "cover_unique_id": UNIQUE_ID,
                    "profile": "tall",
                    "profile_wins": True,
                    "height": HEIGHT,
                }
            },
        },
    ) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC, freezer=freezer)
        await session.async_save(CLIENT, snapshot["revision"], "cover_only")

        record = the_record(hass, entry)
        assert record[CONF_PROFILE] == "tall"
        assert record[CONF_PROFILE_WINS] is True
        assert set(record["overrides"]) == {
            CONF_OPENING_TIME,
            CONF_CLOSING_TIME,
            CONF_SLAT_TIME,
            CONF_OPENING_ROLL,
            CONF_CLOSING_ROLL,
        }
        # ...and no profile of the measured name was written on the way.
        assert the_store(hass, entry).raw_profiles == {}


async def test_a_save_leaves_no_undo_and_does_not_reload_the_entry(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Three minutes of measurements are not a gesture to take back by accident.

    The write goes through the panel's own door - so the covers pick the numbers up in
    place and every subscriber gets the overview - but it hands back no token, and it
    never reloads the entry (plan decision 4).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC, freezer=freezer)
        with patch.object(hass.config_entries, "async_schedule_reload") as reload:
            answer = await session.async_save(CLIENT, snapshot["revision"], "profile")
        assert reload.call_count == 0
        assert answer.keys() == {"session", "overview"}
        assert "undo_token" not in answer


async def test_a_save_is_refused_outside_the_review_and_on_an_old_revision(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Nothing is written by a refused save, whichever rule refused it."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:3], freezer=freezer)

        with pytest.raises(PanelError) as refused:
            await session.async_save(CLIENT, session.revision, "profile")
        assert refused.value.translation_key == "not_in_review"

        snapshot = await walk(hass, session, PATH_A_BASIC[3:], freezer=freezer)
        with pytest.raises(PanelError) as refused:
            await session.async_save(CLIENT, snapshot["revision"] - 1, "profile")
        assert refused.value.translation_key == "revision_conflict"
        with pytest.raises(PanelError) as refused:
            await session.async_save(CLIENT, session.revision, "nowhere")
        assert refused.value.translation_key == "action_not_offered"
        assert the_store(hass, entry).raw_covers == {}
        await session.async_cancel(CLIENT)


@pytest.mark.parametrize("upto", range(len(PATH_A_BASIC) + 1))
async def test_abandoning_the_conversation_at_any_screen_writes_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, upto: int
) -> None:
    """The promise the whole conversation rests on, checked at every step of it."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:upto], freezer=freezer)
        await session.async_cancel(CLIENT)
        assert the_store(hass, entry).raw_profiles == {}
        assert the_store(hass, entry).raw_covers == {}


# --------------------------------------------------------------------------------------
# Repeating, and the ways a step can be made again
# --------------------------------------------------------------------------------------
async def test_repeat_step_makes_the_stage_s_own_movements_again(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Ripeti questo passo" re-enters the stage the plan stands on, and nothing else."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)
        assert session.snapshot()["step"] == "open_lift"

        snapshot = await act(hass, session, Act("repeat_step"), freezer=freezer)

        # Back at the start of the ascent, with its homing made again...
        assert snapshot["step"] == "open_brief"
        assert runner.homed == [DIRECTION_CLOSE, DIRECTION_CLOSE, DIRECTION_CLOSE]
        # ...and everything the two runs had collected thrown away, so that a repeat
        # cannot pair a slat phase with the wrong ascent.
        assert snapshot["measured"]["slat_time_s"] is None
        assert snapshot["measured"]["lift"] is None
        await session.async_cancel(CLIENT)


async def test_not_right_writes_a_stop_before_making_the_step_again(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Something is moving that should not be: stop it, then run the step again."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:2], freezer=freezer)
        stops = runner.stops

        snapshot = await act(hass, session, Act("not_right"), freezer=freezer)

        assert runner.stops == stops + 1
        assert runner.log[-2:] == [("stop", ""), ("home", DIRECTION_CLOSE)]
        assert snapshot["step"] == "home_closed_done"
        await session.async_cancel(CLIENT)


async def test_repeat_measure_asks_for_the_travel_again_without_moving_anything(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The travel is read with the shutter standing still, so there is nothing to re-run."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:AFTER_THE_TRAVEL - 1], freezer=freezer)
        assert session.snapshot()["step"] == "height_result"
        so_far = list(runner.log)

        snapshot = await act(hass, session, Act("repeat_measure"), freezer=freezer)

        assert snapshot["step"] == "height"
        assert runner.log == so_far
        # ...and the form opens on nothing again rather than on the number just disowned.
        assert snapshot["measured"]["travel_cm"] is None
        assert snapshot["form"]["suggested"] == HEIGHT  # the file's, which is not a measurement
        await session.async_cancel(CLIENT)


async def test_repeat_tape_throws_the_reading_away_and_runs_the_stage_again(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The same fraction has to mean the same thing, so the run is made again too."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC[:17], freezer=freezer)
        assert snapshot["step"] == "tape_result"
        assert len(snapshot["measured"]["ascent"]) == 1
        runs = len(runner.runs)

        snapshot = await act(hass, session, Act("repeat_tape"), freezer=freezer)

        assert snapshot["step"] == "measure_ascent"
        assert snapshot["measured"]["ascent"] == []
        assert len(runner.runs) == runs + 1
        await session.async_cancel(CLIENT)


async def test_a_reading_that_cannot_be_one_is_a_field_error_and_not_a_refusal(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """It is the user's mistake, not the protocol's, so the screen says so and stays.

    Including the two numbers `float()` accepts and no tape ever produced: "nan" and
    "inf" are stopped here, before they reach a fit that would raise three screens
    later (B1 handoff, R1).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:16], freezer=freezer)
        assert session.snapshot()["step"] == "measure_ascent"

        for value, error in (
            ("not a number", "not_a_number"),
            ("nan", "not_a_number"),
            ("inf", "not_a_number"),
            ("-3", "out_of_range"),
            (str(HEIGHT + 1), "above_the_travel"),
        ):
            snapshot = await act(hass, session, Act("submit", value), freezer=freezer)
            assert snapshot["step"] == "measure_ascent", value
            assert snapshot["form"]["error"] == error, value
            assert snapshot["measured"]["ascent"] == [], value

        # ...and a decimal comma survives, because the panel sends what was typed.
        snapshot = await act(
            hass, session, Act("submit", f"{ascent_cm(0.5):.1f}".replace(".", ",")),
            freezer=freezer,
        )
        assert snapshot["step"] == "tape_result"
        await session.async_cancel(CLIENT)


async def test_a_travel_outside_the_bounds_and_a_name_that_is_not_one(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The two other forms of path A, refused in the dialog's own words."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:10], freezer=freezer)

        snapshot = await act(hass, session, Act("submit", "3"), freezer=freezer)
        assert snapshot["form"]["error"] == "out_of_range"
        snapshot = await act(hass, session, Act("submit", str(HEIGHT)), freezer=freezer)
        assert snapshot["step"] == "height_result"

        snapshot = await walk(hass, session, PATH_A_BASIC[11:20], freezer=freezer)
        assert snapshot["step"] == "profile_name"
        snapshot = await act(hass, session, Act("submit", "no profile!"), freezer=freezer)
        assert snapshot["form"]["error"] == "invalid_name"
        # `no_profile` is the sentinel the assignment form uses for "Nessun profilo": a
        # profile really called that would be unassignable from that form for ever.
        snapshot = await act(hass, session, Act("submit", "no_profile"), freezer=freezer)
        assert snapshot["form"]["error"] == "invalid_name"
        await session.async_cancel(CLIENT)


async def test_the_lift_off_check_and_the_gap_a_tape_can_repair(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The three things the user can see at the bottom of the shutter, and the fourth.

    A gap under a centimetre is not a small gap: it is a shutter still resting on its
    base, so the run has to be made again rather than taken for a very good press.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)
        snapshot = await act(hass, session, Act("lifted_off", tick=SLAT), freezer=freezer)
        assert snapshot["step"] == "lift_check"
        assert snapshot["actions"] == ["lift_too_early", "lift_accept", "lift_gap", "not_right"]

        snapshot = await act(hass, session, Act("lift_gap"), freezer=freezer)
        assert snapshot["step"] == "lift_gap"
        assert snapshot["form"] == {
            "field": "gap_cm",
            "kind": "number",
            "optional": True,
            "unit": "cm",
            "suggested": None,
            "min": 0.0,
            "max": 50.0,
            "choices": None,
            "error": None,
        }

        snapshot = await act(hass, session, Act("submit", "0.4"), freezer=freezer)
        assert snapshot["step"] == "lift_early"

        snapshot = await act(hass, session, Act("lift_gap"), freezer=freezer)
        snapshot = await act(hass, session, Act("submit", "4,5"), freezer=freezer)
        assert snapshot["step"] == "closed_again"
        assert snapshot["measured"]["lift"]["gap_cm"] == 4.5

        # ...and an empty field is the way out for somebody who thought better of it.
        snapshot = await act(hass, session, Act("confirm_closed_again"), freezer=freezer)
        assert snapshot["step"] == "open_full_brief"
        await session.async_cancel(CLIENT)


async def test_a_late_press_gets_the_screen_that_says_the_gateway_was_busy(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A stop the command queue held back is not the user being slow, and says so."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        runner.stop_queue = 2.0
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)
        snapshot = await act(hass, session, Act("lifted_off", tick=SLAT), freezer=freezer)

        assert snapshot["step"] == "lift_check_late"
        assert snapshot["measured"]["lift"]["late"] is True
        await session.async_cancel(CLIENT)


# --------------------------------------------------------------------------------------
# The clocks
# --------------------------------------------------------------------------------------
async def test_the_press_timeout_pushes_a_screen_instead_of_waiting_for_the_press(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The panel can be told; the dialog could only notice (SPEC §3.6).

    A screen left open on a press for a minute and a half stops being a measurement -
    and the session says so of its own accord, rather than waiting for a press that
    would then be timed from the wrong instant.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)
        assert snapshot["press"]["kind"] == "lift_off"
        expires = dt_util.parse_datetime(snapshot["press"]["expires_at"])
        assert expires is not None

        freezer.tick(timedelta(seconds=PRESS_TIMEOUT_SEC + 1))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()

        snapshot = session.snapshot()
        assert snapshot["step"] == "problem_timeout"
        assert snapshot["problem"] == {"code": "timeout"}
        assert snapshot["actions"] == ["repeat_step"]
        assert snapshot["press"] is None
        assert session.ended is False

        # ...and the step can simply be made again.
        snapshot = await act(hass, session, Act("repeat_step"), freezer=freezer)
        assert snapshot["step"] == "open_brief"
        await session.async_cancel(CLIENT)


async def test_a_press_that_arrives_after_the_window_is_still_refused(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The lazy check the dialog relies on is kept, for the press that overtakes the timer."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)

        freezer.tick(timedelta(seconds=PRESS_TIMEOUT_SEC + 1))
        snapshot = await act(hass, session, Act("lifted_off"), freezer=freezer)

        assert snapshot["step"] == "problem_timeout"
        await session.async_cancel(CLIENT)


async def test_the_lease_is_the_dialog_s_watchdog_and_gives_the_shutter_back(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Half an hour on a screen with nothing moving, ten minutes after a movement."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(entity)
        session = await open_session(hass, entry)

        # A screen with nothing moving is waiting for somebody to read it.
        expires = dt_util.parse_datetime(session.snapshot()["idle_expires_at"])
        assert expires == dt_util.utcnow() + timedelta(seconds=IDLE_TIMEOUT_SEC)

        # ...and a screen that follows a movement is waiting for somebody with a tape.
        await walk(hass, session, PATH_A_BASIC[:2], freezer=freezer)
        expires = dt_util.parse_datetime(session.snapshot()["idle_expires_at"])
        assert expires == dt_util.utcnow() + timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC)

        freezer.tick(timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC + 1))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()

        snapshot = session.snapshot()
        assert snapshot["state"] == "ended"
        assert snapshot["outcome"]["reason"] == "expired"
        assert snapshot["idle_expires_at"] is None
        assert snapshot["owner"] is None
        assert entity.calibrating is False
        assert the_store(hass, entry).raw_covers == {}


async def test_the_lease_stops_a_shutter_that_is_still_running_when_it_runs_out(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Nobody is watching it any more, so it does not get to reach its end stop alone."""
    async with setup_myhome(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        runner = FakeRunner(entity)
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:2], freezer=freezer)
        assert session.snapshot()["step"] == "home_closed_done"
        stops = runner.stops

        with running(entity, DIRECTION_OPEN):
            freezer.tick(timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC + 1))
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()

        assert runner.stops == stops + 1
        assert session.snapshot()["outcome"]["reason"] == "expired"


async def test_a_heartbeat_does_not_renew_the_lease(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A tab forgotten open must not hold a shutter in calibration for ever.

    Which is the whole difference between the lease and the presence: the first is
    about the conversation being alive, the second only about who may drive it.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        expires = session.snapshot()["idle_expires_at"]

        for _ in range(20):
            freezer.tick(timedelta(seconds=IDLE_TIMEOUT_SEC / 20))
            session.heartbeat(CLIENT)
            async_fire_time_changed(hass, dt_util.utcnow())
            await hass.async_block_till_done()
            if session.ended:
                break

        assert session.snapshot()["outcome"]["reason"] == "expired"
        # ...and the beats never moved the date it was going to run out on.
        assert expires == expires


async def test_every_transition_moves_the_revision_and_restarts_the_lease(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The invariant the whole snapshot rests on: one door, and it does both things.

    `_publish` is the only thing that increments `revision`, and it is the only thing
    that rearms the lease - the same exhaustiveness the dialog gets by overriding its
    three `async_show_*` methods.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        seen = session.snapshot()["revision"]

        for one in PATH_A_BASIC:
            before = session.snapshot()
            snapshot = await act(hass, session, one, freezer=freezer)
            assert snapshot["revision"] > before["revision"], one
            assert snapshot["idle_expires_at"] is not None, one
            expires = dt_util.parse_datetime(snapshot["idle_expires_at"])
            assert expires is not None and expires > dt_util.utcnow(), one
            seen = snapshot["revision"]

        # ...and a read moves neither.
        session.snapshot()
        session.heartbeat(CLIENT)
        session.attach(CLIENT)
        assert session.snapshot()["revision"] == seen
        await session.async_cancel(CLIENT)


async def test_a_stale_revision_is_refused_with_nothing_done(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """What makes a double tap on a press, or a retry after a reconnection, harmless."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:2], freezer=freezer)
        so_far = list(runner.log)
        step = session.snapshot()["step"]

        with pytest.raises(PanelError) as refused:
            await session.async_act(CLIENT, session.revision - 1, "confirm_closed")
        assert refused.value.translation_key == "revision_conflict"
        await hass.async_block_till_done()
        assert runner.log == so_far
        assert session.snapshot()["step"] == step
        await session.async_cancel(CLIENT)


async def test_an_action_the_step_does_not_offer_is_refused(
    hass: HomeAssistant, tmp_path
) -> None:
    """Including the two ways out of the dialog, which are commands and not actions."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        for action in ("cancel_flow", "save", "accept_step", "submit"):
            with pytest.raises(PanelError) as refused:
                await session.async_act(CLIENT, session.revision, action)
            assert refused.value.translation_key == "action_not_offered", action
            assert refused.value.placeholders["action"] == action
        await session.async_cancel(CLIENT)


# --------------------------------------------------------------------------------------
# The three verbs
# --------------------------------------------------------------------------------------
async def test_cancel_discards_everything_and_does_not_stop_the_shutter(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A run already under way finishes at its end stop, as the dialog's Cancel does.

    Interrupting it would leave the curtain at an arbitrary point instead of a known
    one, and the screen says as much.
    """
    async with setup_myhome(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        runner = FakeRunner(entity)
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)
        stops = runner.stops

        with running(entity, DIRECTION_OPEN):
            answer = await session.async_cancel(CLIENT)

        assert runner.stops == stops
        assert answer["already_ended"] is False
        snapshot = answer["session"]
        assert snapshot["state"] == "ended"
        assert snapshot["outcome"]["reason"] == "cancelled"
        assert snapshot["measured"]["travel_cm"] is None  # the provisional values are gone
        assert snapshot["plan"] == []
        assert entity.calibrating is False


async def test_cancel_is_idempotent_and_never_refused_for_concurrency(
    hass: HomeAssistant, tmp_path
) -> None:
    """Annulla must never fail silently, and must never say "somebody moved on".

    It carries no revision precisely so that a transition the user did not cause - a
    press timing out, a shutter brought back to its end stop - cannot refuse it
    (lesson 2, contract amendment of 19 Sep).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        first = await session.async_cancel(CLIENT)
        assert first["already_ended"] is False
        for _ in range(3):
            again = await session.async_cancel(CLIENT)
            assert again["already_ended"] is True
            assert again["session"]["outcome"]["reason"] == "cancelled"
            assert again["session"]["revision"] == first["session"]["revision"]


async def test_cancel_by_another_client_needs_force(hass: HomeAssistant, tmp_path) -> None:
    """The banner's "Termina" is the way out that always works."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        with pytest.raises(PanelError) as refused:
            await session.async_cancel(OTHER_CLIENT)
        assert refused.value.translation_key == "session_owned"
        assert session.ended is False

        answer = await session.async_cancel(OTHER_CLIENT, force=True)
        assert answer["session"]["outcome"]["reason"] == "cancelled"


async def test_leave_ends_a_session_that_has_measured_nothing(
    hass: HomeAssistant, tmp_path
) -> None:
    """Closing the window on the first screen gives the shutter straight back."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(entity)
        session = await open_session(hass, entry)

        snapshot = session.leave(CLIENT)

        assert session.ended is True
        # The answer is the terminal snapshot and not nothing: the screen that follows
        # says the calibration was closed before the first measurement, and it reads
        # that off the outcome.
        assert snapshot["state"] == "ended"
        assert snapshot["outcome"]["reason"] == "left"
        assert entity.calibrating is False


async def test_leave_keeps_a_session_that_has_something_to_protect(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A tape reading is not thrown away because a page was closed (contract §2.1)."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        runner = FakeRunner(entity)
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:AFTER_THE_ASCENT], freezer=freezer)
        so_far = list(runner.log)

        snapshot = session.leave(CLIENT)

        assert session.ended is False
        assert snapshot is not None and snapshot["owner"] is None
        assert entity.calibrating is True
        assert runner.log == so_far
        assert snapshot["measured"]["opening_time_s"] is not None

        # ...and whoever acts next simply picks it up.
        await session.async_act(OTHER_CLIENT, session.revision, "accept_step")
        await hass.async_block_till_done()
        assert session.owner == OTHER_CLIENT
        await session.async_cancel(OTHER_CLIENT)


async def test_leave_from_a_client_that_is_not_the_owner_does_nothing(
    hass: HomeAssistant, tmp_path
) -> None:
    """It is sent as a page goes away: a read-only tab has nothing to leave."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        snapshot = session.leave(OTHER_CLIENT)

        assert snapshot is not None
        assert session.ended is False
        assert session.owner == CLIENT
        await session.async_cancel(CLIENT)


async def test_stop_writes_a_stop_and_makes_the_step_it_interrupted_void(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The only verb that touches the shutter, and what it costs the step it lands on."""
    async with setup_myhome(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)
        assert session.snapshot()["step"] == "open_lift"
        stops = runner.stops

        snapshot = await session.async_stop(CLIENT)

        assert runner.stops == stops + 1
        assert snapshot["step"] == "problem_interrupted"
        assert snapshot["problem"] == {"code": "interrupted"}
        assert snapshot["actions"] == ["repeat_step"]
        assert snapshot["movement"] is None
        assert snapshot["press"] is None
        assert session.ended is False
        await session.async_cancel(CLIENT)


async def test_stop_outside_a_movement_is_a_plain_stop(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """With nothing of the session's moving, the state does not change."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:2], freezer=freezer)
        stops = runner.stops

        snapshot = await session.async_stop(CLIENT)

        assert runner.stops == stops + 1
        assert snapshot["step"] == "home_closed_done"
        await session.async_cancel(CLIENT)


# --------------------------------------------------------------------------------------
# What the shutter does when nobody asked it to (SPEC §3.7)
# --------------------------------------------------------------------------------------
async def test_a_movement_outside_a_measurement_is_not_an_interruption(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The shutter taken down with the wall switch while the instructions are read.

    The natural gesture, accepted: what the session forgets is where the shutter is,
    and it says so. Nothing is ended, nothing is void and nothing is repeated.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:2], freezer=freezer)
        assert session.snapshot()["position_known"] == DIRECTION_CLOSE

        hass.states.async_set(ENTITY, STATE_OPENING)
        await hass.async_block_till_done()

        snapshot = session.snapshot()
        assert snapshot["step"] == "home_closed_done"
        assert snapshot["external_move"] is True
        assert snapshot["position_known"] is None
        assert snapshot["problem"] is None
        await session.async_cancel(CLIENT)


async def test_a_timed_run_never_starts_from_a_point_nobody_knows(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The session takes the shutter back to the end stop itself, and says it did.

    Refusing and asking the user to put it back by hand is the v2 defect this replaces.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:3], freezer=freezer)
        hass.states.async_set(ENTITY, STATE_OPENING)
        await hass.async_block_till_done()
        homings = len(runner.homed)

        snapshot = await act(hass, session, Act("open_start"), freezer=freezer)

        assert snapshot["step"] == "open_brief"
        assert snapshot["notice"] == "rehomed"
        assert snapshot["position_known"] == DIRECTION_CLOSE
        assert snapshot["external_move"] is False
        assert len(runner.homed) == homings + 1
        assert runner.started == []

        # ...and pressing it again now simply starts the run.
        snapshot = await act(hass, session, Act("open_start"), freezer=freezer)
        assert snapshot["step"] == "open_lift"
        assert runner.started == [DIRECTION_OPEN]
        await session.async_cancel(CLIENT)


async def test_a_reading_taken_where_the_shutter_no_longer_is_says_so(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The field stays: the user may have measured first, and they are the one who knows."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:16], freezer=freezer)
        assert session.snapshot()["step"] == "measure_ascent"

        hass.states.async_set(ENTITY, STATE_CLOSING)
        await hass.async_block_till_done()

        snapshot = session.snapshot()
        assert snapshot["step"] == "measure_ascent"
        assert snapshot["notice"] == "reading_stale"
        assert snapshot["actions"] == ["repeat_tape"]
        assert snapshot["form"] is not None
        assert snapshot["external_move"] is True
        await session.async_cancel(CLIENT)


async def test_a_movement_the_other_way_during_a_measurement_voids_the_step(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A shutter driven downwards in the middle of a timed ascent measures nothing."""
    async with setup_myhome(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)
        assert session.snapshot()["step"] == "open_lift"

        hass.states.async_set(ENTITY, STATE_CLOSING)
        await hass.async_block_till_done()

        snapshot = session.snapshot()
        assert snapshot["step"] == "problem_interrupted"
        assert snapshot["problem"] == {"code": "interrupted"}
        assert session.ended is False
        await session.async_cancel(CLIENT)


async def test_a_shutter_stopped_before_the_lift_off_press_voids_the_step(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one stop that is not the end stop the step is measuring."""
    async with setup_myhome(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)

        hass.states.async_set(ENTITY, STATE_OPENING)
        await hass.async_block_till_done()
        hass.states.async_set(ENTITY, STATE_OPEN)
        await hass.async_block_till_done()

        assert session.snapshot()["step"] == "problem_interrupted"
        await session.async_cancel(CLIENT)


async def test_the_shutter_reaching_its_end_stop_is_not_an_interruption(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """It is the very thing `open_top` and `close_bottom` are waiting to be told about."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:8], freezer=freezer)
        assert session.snapshot()["press"]["kind"] == "end_stop"

        hass.states.async_set(ENTITY, STATE_OPENING)
        await hass.async_block_till_done()
        hass.states.async_set(ENTITY, STATE_OPEN)
        await hass.async_block_till_done()

        snapshot = session.snapshot()
        assert snapshot["step"] == "open_top"
        assert snapshot["problem"] is None
        snapshot = await act(hass, session, Act("stopped_open", tick=OPENING), freezer=freezer)
        assert snapshot["step"] == "open_result"
        await session.async_cancel(CLIENT)


# --------------------------------------------------------------------------------------
# Problems, endings and the gateway's reservation
# --------------------------------------------------------------------------------------
async def test_a_movement_that_fails_lands_on_a_screen_and_not_on_the_end(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A shutter that did not answer is a problem to repeat, not a session to lose."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:3], freezer=freezer)
        runner.fail = CalibrationError(REASON_NO_ECHO, "no echo")

        snapshot = await act(hass, session, Act("open_start"), freezer=freezer)

        assert snapshot["step"] == "problem_no_echo"
        assert snapshot["problem"] == {"code": "no_echo"}
        assert snapshot["movement"] is None
        assert session.ended is False
        snapshot = await act(hass, session, Act("repeat_step"), freezer=freezer)
        assert snapshot["step"] == "open_brief"
        await session.async_cancel(CLIENT)


async def test_the_entry_being_unloaded_ends_the_session_and_stops_the_shutter(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`async_unload_entry` closes it first, while the entities are still there."""
    async with setup_myhome(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        runner = FakeRunner(entity)
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)
        stops = runner.stops

        with running(entity, DIRECTION_OPEN):
            await calibration_session.async_end_all(hass, entry, "unloaded")

        assert runner.stops == stops + 1
        snapshot = session.snapshot()
        assert snapshot["state"] == "ended"
        assert snapshot["outcome"]["reason"] == "unloaded"
        assert entity.calibrating is False


async def test_unloading_the_config_entry_ends_the_session(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The whole way round, through Home Assistant's own unload."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:3], freezer=freezer)

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert session.ended is True
        assert session.snapshot()["outcome"]["reason"] == "unloaded"


async def test_the_gateway_stays_reserved_while_a_cancelled_run_finishes(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The shutter is given back at once; the gateway is not (contract §2.1).

    It is what the user meets pressing "Calibra un'altra tapparella" straight after
    cancelling one: there is nothing to resume and nothing to close, only a run
    finishing by itself, and the screen says to wait.
    """
    async with setup_myhome(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        entity = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(entity)
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:4], freezer=freezer)

        with running(entity, DIRECTION_OPEN):
            await session.async_cancel(CLIENT)
            assert entity.calibrating is False

            with pytest.raises(PanelError) as refused:
                await async_start(
                    hass, entry, cover_unique_id=UNIQUE_ID, client_id=OTHER_CLIENT
                )
            assert refused.value.translation_key == "already_calibrating"
            assert refused.value.placeholders["by"] == "reserved"

        # Once the shutter has stopped, the gateway is free again.
        again = await open_session(hass, entry)
        assert again.snapshot()["state"] == "armed"
        await again.async_cancel(CLIENT)


async def test_a_finished_session_stays_readable_for_ten_minutes(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A page that comes back reads *how* it ended, not "no such session"."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await session.async_cancel(CLIENT)

        assert current(hass, entry) is session
        freezer.tick(timedelta(minutes=9))
        assert current(hass, entry) is session
        assert current(hass, entry).snapshot()["outcome"]["reason"] == "cancelled"

        freezer.tick(timedelta(minutes=2))
        assert current(hass, entry) is None


async def test_a_new_start_replaces_the_session_that_ended(
    hass: HomeAssistant, tmp_path
) -> None:
    """The terminal snapshot is an answer, not a lock."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await session.async_cancel(CLIENT)

        again = await open_session(hass, entry)
        assert again is not session
        assert again.session_id != session.session_id
        assert current(hass, entry) is again
        await again.async_cancel(CLIENT)


async def test_a_verb_on_a_session_that_has_ended_says_how_it_ended(
    hass: HomeAssistant, tmp_path
) -> None:
    """Every verb but `cancel`, `get` and `attach`, which are how a client finds out."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await session.async_cancel(CLIENT)

        with pytest.raises(PanelError) as refused:
            await session.async_act(CLIENT, session.revision, "path_a")
        assert refused.value.translation_key == "session_ended"
        assert refused.value.placeholders["reason"] == "cancelled"
        with pytest.raises(PanelError):
            await session.async_stop(CLIENT)
        with pytest.raises(PanelError):
            await session.async_save(CLIENT, session.revision, "profile")
        # ...while the three reads answer.
        assert session.attach(CLIENT)["outcome"]["reason"] == "cancelled"
        assert session.heartbeat(CLIENT) == {"owner": False, "present_until": None}
        assert session.leave(CLIENT) is not None


# --------------------------------------------------------------------------------------
# The subscription, and the one arithmetic
# --------------------------------------------------------------------------------------
async def test_every_transition_is_published_once_in_revision_order(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """What the socket forwards, and what a second screen follows along with."""
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        seen: list[dict[str, Any]] = []
        drop = session.subscribe(seen.append)

        await walk(hass, session, PATH_A_BASIC[:6], freezer=freezer)
        revisions = [snapshot["revision"] for snapshot in seen]
        assert revisions == sorted(revisions)
        assert len(revisions) == len(set(revisions))
        assert seen[-1]["step"] == session.snapshot()["step"]

        drop()
        await act(hass, session, Act("confirm_closed_again"), freezer=freezer)
        assert seen[-1]["step"] != session.snapshot()["step"]
        await session.async_cancel(CLIENT)


async def test_the_expected_reading_is_the_dialog_s_own(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """One arithmetic for the dialog and the panel, down to the number on the screen.

    The ported function answers the two *strings* the dialog's sentence substitutes;
    the panel is given values and formats them itself, so the rule is applied in the
    session and this is what keeps the two answers the same number.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, PATH_A_BASIC[:16], freezer=freezer)

        reading = snapshot["reading"]
        assert reading["direction"] == DIRECTION_OPEN
        assert reading["fraction"] == 0.5
        assert reading["from_end_stop"] == DIRECTION_CLOSE
        expected, tolerance = expected_cm(
            pending=(DIRECTION_OPEN, 0.5), height=HEIGHT, model=None
        )
        assert f"{reading['expected_cm']:.0f}" == expected
        assert f"{reading['tolerance_cm']:.0f}" == tolerance
        assert snapshot["placeholders"]["expected"] == reading["expected_cm"]
        assert snapshot["placeholders"]["percent"] == 50
        await session.async_cancel(CLIENT)


async def test_the_snapshot_always_carries_every_key_of_the_contract(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Every key is always there; what does not apply is null (docs §12).

    Checked at every screen of the walk, because a key that appears only on some of
    them is a key the panel has to guard against instead of drawing.
    """
    from custom_components.myhome.panel_schemas import SESSION_KEYS

    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshots = [session.snapshot()]
        for one in PATH_A_BASIC:
            snapshots.append(await act(hass, session, one, freezer=freezer))
        await session.async_save(CLIENT, session.revision, "profile")
        snapshots.append(session.snapshot())

        for snapshot in snapshots:
            assert tuple(snapshot) == SESSION_KEYS, snapshot["step"]
            assert snapshot["placeholders"]["cover"] == snapshot["cover"]["name"]
            if snapshot["substate"] is not None:
                assert snapshot["state"] == "running"
            if snapshot["press"] is not None:
                assert snapshot["substate"] == "awaiting_endpoint"
            if snapshot["problem"] is not None:
                assert snapshot["step"] == f"problem_{snapshot['problem']['code']}"
