"""Tests for the guided calibration flows (0.5.0, phase 2 - the conversation).

The shutter here is a **fake runner**: the four `async_calib_*` primitives of the real
cover entity are replaced by a stand-in that answers the way a shutter of known
dimensions would. That is deliberate and not a shortcut. The primitives themselves are
covered frame by frame in `test_calibration_runner.py`, against a gateway that writes
and an actuator that answers; what is under test *here* is the conversation - which
screen follows which, what is carried between them, what is written at the end and
(most of all) what is written before the end, which is nothing.

The stand-in behaves like the 195 cm reference window used everywhere in this suite,
and the flow is given exactly the measurements that window would produce, so the
numbers the flow stores can be checked against the ones it was meant to rediscover
rather than against themselves.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from custom_components.myhome import calibration_store
from custom_components.myhome.calibration import (
    REASON_BUSY,
    REASON_NO_ECHO,
    REASON_NOT_DELIVERED,
    REASON_NOT_STOPPED,
    CalibrationError,
    RunReport,
    predict_cm,
)
from custom_components.myhome.calibration_flow import (
    PRESS_TIMEOUT_SEC,
    CoverCalibrationFlow,
)
from custom_components.myhome.calibration_store import (
    async_set_cover_calibration,
    cover_calibration_data,
)
from custom_components.myhome.const import (
    ATTR_CALIBRATION_SOURCE,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_UNIQUE_ID,
    CONF_HEIGHT,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_OVERRIDES,
    CONF_PROFILE,
    CONF_RAW,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
    DIRECTION_CLOSE,
    DIRECTION_OPEN,
    SUBENTRY_COVER_CALIBRATION,
    SUBENTRY_COVER_PROFILE,
)

from .helpers_core import MAC
from .helpers_platforms import entity_object, set_connected, setup_myhome

# The reference window, once. The YAML configures exactly what the fake shutter really
# is, so a calibration that works has to hand back the numbers below: anything else is
# the flow inventing a shutter.
HEIGHT = 195.0
OPENING = 22.3
CLOSING = 21.7
SLAT = 4.7
ROLL_DOWN = 1.69
ROLL_UP = 2.12
CURTAIN_DOWN = CLOSING - SLAT  # 17.0 s
CURTAIN_UP = OPENING - SLAT  # 17.6 s

DEVICE_KEY = "2-81"
UNIQUE_ID = f"{MAC}-{DEVICE_KEY}"
ENTITY = "cover.hallway_shutter"
COVER_NAME = "Hallway Shutter"

YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: {COVER_NAME}
      opening_time: {OPENING}
      closing_time: {CLOSING}
      slat_time: {SLAT}
      roll: {ROLL_DOWN}
      height: {HEIGHT}
"""

# The same gateway with a second, advanced cover: it must never be offered.
MIXED_YAML = (
    YAML
    + """    skylight:
      where: '82'
      name: Skylight
      advanced: true
"""
)

ADVANCED_ONLY_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    skylight:
      where: '82'
      name: Skylight
      advanced: true
"""

PROFILE_YAML = (
    YAML
    + f"""  cover_profiles:
    tall:
      reference_height: {HEIGHT}
      opening_time: {OPENING}
      closing_time: {CLOSING}
      slat_time: {SLAT}
      roll: {ROLL_DOWN}
"""
)


def descent_cm(fraction: float) -> float:
    """Where the bottom edge of the real window is after `fraction` of a descent."""
    return predict_cm(DIRECTION_CLOSE, ROLL_DOWN, 1.0, fraction, HEIGHT)


def ascent_cm(fraction: float) -> float:
    """...and after the slats plus `fraction` of an ascent."""
    return predict_cm(DIRECTION_OPEN, ROLL_UP, 1.0, fraction, HEIGHT)


class FakeRunner:
    """The four primitives of `MyHOMECover`, answered by a shutter that behaves.

    Every call is recorded, every failure is injectable, and the seconds handed back
    are the ones the reference window would really have spent - which is what makes
    the values the flow stores checkable.
    """

    def __init__(self, cover: Any) -> None:
        self.cover = cover
        self.homed: list[str] = []
        self.started: list[str] = []
        self.runs: list[tuple[str, float]] = []
        self.stops = 0
        self.fail: CalibrationError | None = None
        self.fail_on: str | None = None
        cover.async_calib_home = self._home
        cover.async_calib_start = self._start
        cover.async_calib_stop = self._stop
        cover.async_calib_run_fraction = self._run_fraction

    def _maybe_fail(self, what: str) -> None:
        if self.fail is not None and self.fail_on in (None, what):
            error, self.fail = self.fail, None
            raise error

    async def _home(self, direction: str, timeout: float | None = None) -> None:
        self._maybe_fail("home")
        self.homed.append(direction)

    async def _start(self, direction: str):
        self._maybe_fail("start")
        self.started.append(direction)
        return dt_util.utcnow()

    async def _stop(self):
        self._maybe_fail("stop")
        self.stops += 1
        return dt_util.utcnow()

    async def _run_fraction(self, direction: str, fraction: float) -> RunReport:
        self._maybe_fail("run")
        self.runs.append((direction, fraction))
        seconds = (
            fraction * CURTAIN_DOWN
            if direction == DIRECTION_CLOSE
            else SLAT + fraction * CURTAIN_UP
        )
        now = dt_util.utcnow()
        return RunReport(
            motor_start=now,
            stop_written=now,
            motor_seconds=seconds,
            planned_seconds=seconds,
            fraction=fraction,
            direction=direction,
        )


@asynccontextmanager
async def calibrating(hass: HomeAssistant, tmp_path, yaml_text: str, **kwargs) -> AsyncIterator:
    """`setup_myhome`, plus closing whatever dialog the test left open.

    A flow holds a calibration session on the cover for as long as the conversation
    lasts, and gives it back in `async_remove` - which Home Assistant calls when the
    dialog is closed. A test that simply walks away leaves that to the garbage
    collector, which runs the release off the event loop and turns a perfectly good
    assertion into an unraisable-exception warning three tests later. Closing the
    dialogs here is what the browser's X does, and it does it while the entry is still
    loaded.
    """
    async with setup_myhome(hass, tmp_path, yaml_text, **kwargs) as (entry, commands):
        try:
            yield entry, commands
        finally:
            manager = hass.config_entries.subentries
            for flow in list(manager.async_progress()):
                manager.async_abort(flow["flow_id"])


# --------------------------------------------------------------------------------------
# Driving a subentry flow
# --------------------------------------------------------------------------------------
async def start_flow(hass: HomeAssistant, entry, subentry_type: str = SUBENTRY_COVER_CALIBRATION):
    """Open the flow the "Add" button on the integration page opens."""
    return await hass.config_entries.subentries.async_init(
        (entry.entry_id, subentry_type), context={"source": "user"}
    )


async def _resolve(hass: HomeAssistant, result: dict[str, Any]) -> dict[str, Any]:
    """Let a progress screen finish, and answer with the screen that follows it."""
    while result["type"] is FlowResultType.SHOW_PROGRESS:
        await hass.async_block_till_done()
        result = await hass.config_entries.subentries.async_configure(result["flow_id"])
    return result


async def submit(hass: HomeAssistant, result: dict[str, Any], user_input=None) -> dict[str, Any]:
    """Press Submit on a form (or hand it its fields) and wait out any movement.

    A form with no fields is submitted with an empty mapping and not with `None`,
    because that is what the frontend sends: `None` means "show me this form", which is
    exactly what the confirmation screens would do for ever.
    """
    if result["type"] is FlowResultType.FORM and user_input is None:
        user_input = {}
    result = await hass.config_entries.subentries.async_configure(result["flow_id"], user_input)
    return await _resolve(hass, result)


async def choose(hass: HomeAssistant, result: dict[str, Any], option: str) -> dict[str, Any]:
    """Click one option of a menu."""
    assert result["type"] is FlowResultType.MENU, result
    assert option in result["menu_options"], (option, result["menu_options"])
    return await submit(hass, result, {"next_step_id": option})


@dataclass(frozen=True)
class Act:
    """One thing the user does, and how long they took to do it."""

    payload: dict[str, Any] | None = None
    option: str | None = None
    tick: float = 0.0


async def drive(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, result: dict[str, Any], acts
) -> dict[str, Any]:
    """Play a list of user actions against a flow."""
    for act in acts:
        if act.tick:
            freezer.tick(timedelta(seconds=act.tick))
        if act.option is not None:
            result = await choose(hass, result, act.option)
        else:
            result = await submit(hass, result, act.payload)
    return result


# The full walk of path A at the basic level, as a list of what the user does. It is a
# list rather than a function so that the "abandoning it at any screen writes nothing"
# test can replay any prefix of it.
PATH_A_BASIC: tuple[Act, ...] = (
    Act(),  # the introduction
    Act(payload={"cover": UNIQUE_ID}),
    Act(option="path_a"),
    Act(),  # the warning before the first movement
    Act(option="confirm_closed"),
    Act(option="lifted_off", tick=SLAT),
    Act(option="stopped_open", tick=CURTAIN_UP),
    Act(payload={CONF_HEIGHT: HEIGHT}),
    Act(option="stopped_closed", tick=CLOSING),
    Act(payload={"measured_cm": descent_cm(0.5)}),
    Act(payload={"measured_cm": ascent_cm(0.5)}),
    Act(option="save"),
    Act(payload={CONF_NAME: "tall"}),
)

PATH_A_PRECISE: tuple[Act, ...] = (
    *PATH_A_BASIC[:-2],
    Act(option="refine"),
    Act(payload={"measured_cm": descent_cm(0.25)}),
    Act(payload={"measured_cm": descent_cm(0.75)}),
    Act(payload={"measured_cm": ascent_cm(0.25)}),
    Act(payload={"measured_cm": ascent_cm(0.75)}),
    Act(payload={"measured_cm": descent_cm(0.40)}),
    Act(option="continue_step"),
    Act(option="save"),
    Act(payload={CONF_NAME: "tall"}),
)


def subentries_of(entry, subentry_type: str) -> list[Any]:
    return [s for s in entry.subentries.values() if s.subentry_type == subentry_type]


def the_profile(entry) -> dict[str, Any]:
    profiles = subentries_of(entry, SUBENTRY_COVER_PROFILE)
    assert len(profiles) == 1
    return dict(profiles[0].data)


def the_calibration(entry) -> dict[str, Any]:
    calibrations = subentries_of(entry, SUBENTRY_COVER_CALIBRATION)
    assert len(calibrations) == 1
    return dict(calibrations[0].data)


@pytest.fixture(autouse=True)
def _forget_clash_warnings():
    calibration_store.reset_name_clash_warnings()
    yield


# --------------------------------------------------------------------------------------
# Path A - the first shutter of its kind
# --------------------------------------------------------------------------------------
async def test_path_a_measures_the_shutter_and_stores_a_profile_and_a_calibration(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The whole conversation, and the numbers it has to rediscover.

    The fake shutter *is* the 195 cm reference window, so the profile the flow writes
    has to be that window: 22.3 s up, 21.7 s down, 4.7 s of slats and the two rolls.
    Anything else means a step lost a measurement, mixed up a direction, or fed the fit
    a run time that was never spent.

    Mutation caught: taking the slat phase off the descent as well as the ascent (both
    run times come out ~5 s short), or fitting the ascent against the descent's seconds.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "calibration_saved"

    profile = the_profile(entry)
    assert profile[CONF_NAME] == "tall"
    assert profile[CONF_REFERENCE_HEIGHT] == HEIGHT
    assert profile[CONF_OPENING_TIME] == pytest.approx(OPENING, abs=0.05)
    assert profile[CONF_CLOSING_TIME] == pytest.approx(CLOSING, abs=0.05)
    assert profile[CONF_SLAT_TIME] == pytest.approx(SLAT, abs=0.05)
    assert profile[CONF_CLOSING_ROLL] == pytest.approx(ROLL_DOWN, abs=0.01)
    assert profile[CONF_OPENING_ROLL] == pytest.approx(ROLL_UP, abs=0.01)
    # The measurements themselves are kept beside the conclusions drawn from them.
    assert profile[CONF_RAW]["descent"] == [[pytest.approx(CURTAIN_DOWN / 2), pytest.approx(descent_cm(0.5))]]

    calibration = the_calibration(entry)
    assert calibration[CONF_COVER_UNIQUE_ID] == UNIQUE_ID
    assert calibration[CONF_PROFILE] == "tall"
    assert calibration[CONF_HEIGHT] == HEIGHT
    # Path A stores no overrides: the numbers live in the profile, which is what makes
    # the second shutter of the same kind a two-screen job.
    assert CONF_OVERRIDES not in calibration


async def test_path_a_walks_the_screens_in_the_order_the_flow_document_agreed(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Screen by screen, with the movements each one is responsible for.

    Every measuring step brings the shutter to the end stop it needs *itself*, which is
    what makes "Repeat this step" safe; this test is where that shows up, as the list
    of homings below.

    Mutation caught: a step that measures from wherever the previous one happened to
    leave the shutter.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await start_flow(hass, entry)
        assert result["step_id"] == "user"

        seen = []
        for act in PATH_A_BASIC:
            if act.tick:
                freezer.tick(timedelta(seconds=act.tick))
            result = (
                await choose(hass, result, act.option)
                if act.option is not None
                else await submit(hass, result, act.payload)
            )
            seen.append(result.get("step_id") or result.get("reason"))

    assert seen == [
        "cover",
        "path",
        "path_a",
        "home_closed_done",
        "open_lift",
        "open_top",
        "height",
        "close_bottom",
        "measure_descent",
        "measure_ascent",
        "summary",
        "profile_name",
        "calibration_saved",
    ]
    # Closed for the first press, open for the descent, and the far end stop before
    # each of the two timed runs.
    assert runner.homed == [
        DIRECTION_CLOSE,  # home_closed
        DIRECTION_CLOSE,  # open_timed starts from the bottom
        DIRECTION_OPEN,  # close_timed starts from the top
        DIRECTION_OPEN,  # half_down
        DIRECTION_CLOSE,  # half_up
    ]
    assert runner.started == [DIRECTION_OPEN, DIRECTION_CLOSE]
    assert runner.runs == [(DIRECTION_CLOSE, 0.5), (DIRECTION_OPEN, 0.5)]


async def test_the_summary_shows_the_values_and_the_yaml_that_would_say_the_same(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A user who prefers the file must be able to copy it out of the dialog.

    Mutation caught: dropping the snippet (or building it from the raw presses rather
    than from the corrected times, which is what the profile is actually given).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:-2])

    assert result["step_id"] == "summary"
    placeholders = result["description_placeholders"]
    assert placeholders["height"] == "195"
    # Noise-free measurements: the model reproduces them exactly.
    assert float(placeholders["accuracy"]) == pytest.approx(0.0, abs=0.05)
    snippet = placeholders["yaml"]
    assert "cover_profiles:" in snippet
    assert f"{CONF_OPENING_TIME}: {OPENING}" in snippet
    assert f"{CONF_CLOSING_TIME}: {CLOSING}" in snippet
    assert f"{CONF_REFERENCE_HEIGHT}: {HEIGHT}" in snippet
    # Two rolls that differ are written as two keys (`cover.calibration_yaml`).
    assert f"{CONF_OPENING_ROLL}: {ROLL_UP}" in snippet
    assert f"{CONF_CLOSING_ROLL}: {ROLL_DOWN}" in snippet
    assert "save" in result["menu_options"]
    assert "refine" in result["menu_options"]


async def test_the_precise_level_adds_four_readings_and_ends_on_a_check(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Improve the accuracy": three points per direction, then a position nothing taught.

    The presses are deliberately *not* repeated: with three points the fit solves the
    roll and a scale on the run time together, which is the reaction time of those
    presses being measured rather than assumed.

    Mutation caught: verifying at one of the fractions that were fitted (the deviation
    would then be zero by construction and say nothing).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_PRECISE)

    assert result["reason"] == "calibration_saved"
    assert runner.runs == [
        (DIRECTION_CLOSE, 0.5),
        (DIRECTION_OPEN, 0.5),
        (DIRECTION_CLOSE, 0.25),
        (DIRECTION_CLOSE, 0.75),
        (DIRECTION_OPEN, 0.25),
        (DIRECTION_OPEN, 0.75),
        (DIRECTION_CLOSE, 0.40),
    ]
    profile = the_profile(entry)
    assert profile[CONF_OPENING_TIME] == pytest.approx(OPENING, abs=0.05)
    assert profile[CONF_CLOSING_TIME] == pytest.approx(CLOSING, abs=0.05)
    assert profile[CONF_CLOSING_ROLL] == pytest.approx(ROLL_DOWN, abs=0.01)
    assert profile[CONF_OPENING_ROLL] == pytest.approx(ROLL_UP, abs=0.01)
    assert profile[CONF_RAW]["precise"] is True
    assert len(profile[CONF_RAW]["descent"]) == 3
    assert len(profile[CONF_RAW]["ascent"]) == 3
    # A shutter that really is the model it was measured against lands on it.
    assert profile[CONF_RAW]["deviation_cm"] == pytest.approx(0.0, abs=0.5)


async def test_the_verification_screen_reports_the_gap_in_centimetres(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one number of the precise level a user can check with their own eyes.

    Mutation caught: showing the signed deviation (a shutter 3 cm low would read
    "-3 cm" and the screen's text says "stopped X cm from the estimate").
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        acts = PATH_A_PRECISE[: PATH_A_PRECISE.index(Act(option="continue_step"))]
        # The tape says the bar is 6 cm lower than the model expects.
        acts = (*acts[:-1], Act(payload={"measured_cm": descent_cm(0.40) - 6.0}))
        result = await drive(hass, freezer, await start_flow(hass, entry), acts)

    assert result["step_id"] == "verify_result"
    assert result["description_placeholders"]["deviation"] == "6"
    # Path A is already measuring this shutter: refining it again is not on offer.
    assert "path_c" not in result["menu_options"]


# --------------------------------------------------------------------------------------
# Nothing is written before Save
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("screens", range(len(PATH_A_BASIC)))
async def test_abandoning_the_flow_at_any_screen_writes_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, screens: int
) -> None:
    """The promise the first screen makes, checked at every screen it makes it about.

    The parametrisation walks one screen further each time and then closes the dialog
    the way the X does, which is the case that matters: a flow that stored the profile
    as soon as it had the numbers would pass a happy-path test and break this one at
    exactly the screens where a user hesitates.

    Mutation caught: writing either subentry anywhere before the name form is answered.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:screens])
        hass.config_entries.subentries.async_abort(result["flow_id"])
        await hass.async_block_till_done()

        assert entry.subentries == {}
        # And the shutter is given back: the session the flow held is released.
        assert cover.calibrating is False


async def test_cancelling_from_the_summary_saves_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Even with every measurement in hand, "Cancel" is a screen that writes nothing."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:-2])
        result = await choose(hass, result, "cancel_flow")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "cancelled"
    assert entry.subentries == {}


# --------------------------------------------------------------------------------------
# Repeat, "it did not do what it should", and the failures
# --------------------------------------------------------------------------------------
async def test_repeating_a_step_runs_that_step_again_and_keeps_the_rest(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Repeat this step" re-does one step's movements, not the conversation.

    Mutation caught: restarting the plan from the beginning (the height and the first
    presses would be asked for twice).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:6])
        assert result["step_id"] == "open_top"

        result = await choose(hass, result, "repeat_step")
        # The step homed and started again, and no stop was sent: nothing misbehaved.
        assert result["step_id"] == "open_lift"
        assert runner.started == [DIRECTION_OPEN, DIRECTION_OPEN]
        assert runner.stops == 0

        # ...and the rest of the walk still ends where it should.
        result = await drive(hass, freezer, result, PATH_A_BASIC[5:])
    assert result["reason"] == "calibration_saved"
    assert the_profile(entry)[CONF_OPENING_TIME] == pytest.approx(OPENING, abs=0.05)


async def test_it_did_not_do_what_it_should_stops_the_shutter_first(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The difference between "Repeat" and "It did not do what it should" is the stop.

    Something is moving that should not be - the wrong way, or on somebody else's
    command - and the step's own homing would otherwise queue behind it.

    Mutation caught: treating the two options as the same thing.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:5])
        assert result["step_id"] == "open_lift"

        result = await choose(hass, result, "not_right")
        assert result["step_id"] == "open_lift"
        assert runner.stops == 1
        assert runner.started == [DIRECTION_OPEN, DIRECTION_OPEN]
        assert entry.subentries == {}


async def test_a_shutter_that_does_not_answer_gets_its_own_screen(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`no_echo`: the frame was written and the actuator said nothing.

    Each reason has a screen of its own because each one needs something different
    done about it, and the screen offers the step again rather than the beginning.

    Mutation caught: letting the `CalibrationError` escape the progress task (the
    dialog would show a traceback), or showing one text for every failure.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:4])
        assert result["step_id"] == "home_closed_done"

        runner.fail = CalibrationError(REASON_NO_ECHO, "it said nothing")
        runner.fail_on = "start"
        result = await choose(hass, result, "confirm_closed")
        assert result["type"] is FlowResultType.MENU
        assert result["step_id"] == "problem_no_echo"
        assert set(result["menu_options"]) == {"repeat_step", "cancel_flow"}

        # The step is offered again, and this time it works.
        result = await choose(hass, result, "repeat_step")
        assert result["step_id"] == "open_lift"
        assert entry.subentries == {}


@pytest.mark.parametrize(
    ("reason", "step"),
    [
        (REASON_NOT_DELIVERED, "problem_not_delivered"),
        (REASON_BUSY, "problem_busy"),
        ("something_new", "problem_unknown"),
    ],
)
async def test_every_failure_reason_reaches_a_screen_written_for_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, reason: str, step: str
) -> None:
    """A reason nobody wrote a text for must land on the generic screen, not on a 404.

    Mutation caught: building the step id straight from `err.reason` (a future engine
    reason would raise `UnknownStep` and leave the dialog broken).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:3])
        runner.fail = CalibrationError(reason, "no")
        result = await submit(hass, result, None)

    assert result["step_id"] == step


async def test_a_press_that_never_came_is_not_believed(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The 90 s window: past it the press measures nothing and the step is offered again.

    A flow cannot push a new screen at a browser, so the window is checked when the
    press finally arrives - which is the only moment there is anything to check.

    Mutation caught: taking the press at face value (a screen left open over lunch
    would produce an opening time of several thousand seconds and a shutter that never
    moves again).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:5])
        assert result["step_id"] == "open_lift"

        freezer.tick(timedelta(seconds=PRESS_TIMEOUT_SEC + 1))
        result = await choose(hass, result, "lifted_off")
        assert result["step_id"] == "problem_timeout"
        assert entry.subentries == {}


async def test_presses_in_an_impossible_order_are_refused(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A shutter cannot stop before it starts: that is a user, not a measurement.

    The clock is moved *backwards* between the two presses, which is the only way to
    produce from the outside what a mis-pressed button produces from the inside.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:5])
        freezer.tick(timedelta(seconds=-5))
        result = await choose(hass, result, "lifted_off")
        result = await choose(hass, result, "stopped_open")

    assert result["step_id"] == "problem_bad_point"
    assert entry.subentries == {}


async def test_a_tape_reading_above_the_travel_is_sent_back_to_the_form(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Measuring from the floor instead of from the rest: caught on the screen itself.

    Mutation caught: accepting it and letting `fit_direction` raise `bad_point` three
    screens later, where the user can no longer tell which reading was wrong.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:9])
        assert result["step_id"] == "measure_descent"

        result = await submit(hass, result, {"measured_cm": HEIGHT + 20})
        assert result["step_id"] == "measure_descent"
        assert result["errors"] == {"measured_cm": "above_the_travel"}

        result = await drive(hass, freezer, result, PATH_A_BASIC[9:])
    assert result["reason"] == "calibration_saved"


# --------------------------------------------------------------------------------------
# The profile name
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["with space", "accènted", "dash-ed", ""])
async def test_a_profile_name_has_to_be_a_yaml_key(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, name: str
) -> None:
    """`PROFILE_NAME_PATTERN` is enforced here, which is the only place it can be.

    A profile name is also a key of `cover_profiles:` - a user may move a guided
    profile into the file by hand - so it has to be one.

    Mutation caught: storing whatever was typed (a name with a space would be a profile
    nobody can reference from the file).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:-1])
        assert result["step_id"] == "profile_name"

        result = await submit(hass, result, {CONF_NAME: name})
        assert result["step_id"] == "profile_name"
        assert result["errors"] == {CONF_NAME: "invalid_name"}
        assert entry.subentries == {}


async def test_a_name_already_taken_by_the_file_is_refused(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """UI profiles and `cover_profiles:` share one namespace, so the clash is here.

    Mutation caught: checking only the stored profiles (a guided profile would shadow
    the file's silently, which is the failure the store warns about at every reload).
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:-1])

        result = await submit(hass, result, {CONF_NAME: "tall"})
        assert result["errors"] == {CONF_NAME: "name_in_use"}
        assert entry.subentries == {}

        result = await submit(hass, result, {CONF_NAME: "tall_hallway"})
    assert result["reason"] == "calibration_saved"
    assert the_profile(entry)[CONF_NAME] == "tall_hallway"


# --------------------------------------------------------------------------------------
# Path B - the other windows of the same kind
# --------------------------------------------------------------------------------------
async def test_path_b_stores_the_profile_and_the_height_and_nothing_else(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Two screens and one tape reading, which is the point of having profiles at all."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(
            hass,
            freezer,
            await start_flow(hass, entry),
            (
                Act(),
                Act(payload={"cover": UNIQUE_ID}),
                Act(option="path_b"),
                Act(payload={CONF_PROFILE: "tall"}),
                Act(payload={CONF_HEIGHT: 160.0}),
                Act(option="skip_verify"),
                Act(option="save"),
            ),
        )

    assert result["reason"] == "calibration_saved"
    assert subentries_of(entry, SUBENTRY_COVER_PROFILE) == []
    calibration = the_calibration(entry)
    assert calibration[CONF_PROFILE] == "tall"
    assert calibration[CONF_HEIGHT] == 160.0
    assert CONF_OVERRIDES not in calibration
    # Skipping the check means the shutter never moved at all.
    assert runner.runs == []


async def test_path_b_offers_the_refinement_when_the_check_is_far_out(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Over three centimetres the profile is not describing this window (FLOW, 3 cm).

    The check runs the shutter half way down from the top and compares the tape with
    the profile *scaled to this window's height*, which is the model the calibration
    would be saved with.

    Mutation caught: comparing against the profile at its own reference height (a
    shorter window would look wrong by tens of centimetres and every path B would end
    in path C).
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        start = (
            Act(),
            Act(payload={"cover": UNIQUE_ID}),
            Act(option="path_b"),
            Act(payload={CONF_PROFILE: "tall"}),
            Act(payload={CONF_HEIGHT: HEIGHT}),
            Act(option="verify_now"),
        )
        result = await drive(hass, freezer, await start_flow(hass, entry), start)
        assert result["step_id"] == "measure_verify"

        # This window stops eight centimetres below where the profile says it will.
        result = await submit(hass, result, {"measured_cm": descent_cm(0.5) - 8.0})
        assert result["step_id"] == "verify_result"
        assert result["description_placeholders"]["deviation"] == "8"
        assert "path_c" in result["menu_options"]

        # ...and taking that offer keeps the height that was just measured.
        result = await choose(hass, result, "path_c")
        assert result["step_id"] == "path_c"
        result = await submit(hass, result, {CONF_PROFILE: "tall"})
        assert result["step_id"] == "refine_scope"


async def test_a_check_that_lands_close_enough_just_carries_on(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Under the threshold there is nothing to refine, so nothing is offered."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(
            hass,
            freezer,
            await start_flow(hass, entry),
            (
                Act(),
                Act(payload={"cover": UNIQUE_ID}),
                Act(option="path_b"),
                Act(payload={CONF_PROFILE: "tall"}),
                Act(payload={CONF_HEIGHT: HEIGHT}),
                Act(option="verify_now"),
                Act(payload={"measured_cm": descent_cm(0.5) - 1.0}),
            ),
        )
        assert result["step_id"] == "verify_result"
        assert "path_c" not in result["menu_options"]

        result = await drive(hass, freezer, result, (Act(option="continue_step"), Act(option="save")))
    assert result["reason"] == "calibration_saved"
    assert the_calibration(entry)[CONF_PROFILE] == "tall"


async def test_the_paths_that_need_a_profile_are_not_offered_without_one(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A menu that offers something impossible is worse than a shorter menu."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:2])

    assert result["step_id"] == "path"
    assert list(result["menu_options"]) == ["path_a"]


# --------------------------------------------------------------------------------------
# Path C - this one window
# --------------------------------------------------------------------------------------
async def test_path_c_times_only_stores_the_two_run_times_as_overrides(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The narrow refinement: this motor is slower, everything else is the profile's.

    Mutation caught: storing the rolls as well (they were never measured on this
    shutter, and writing them would pin the window to the profile's geometry as if it
    had been).
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(
            hass,
            freezer,
            await start_flow(hass, entry),
            (
                Act(),
                Act(payload={"cover": UNIQUE_ID}),
                Act(option="path_c"),
                Act(payload={CONF_PROFILE: "tall"}),
                Act(option="times_only"),
                Act(option="lifted_off", tick=SLAT),
                Act(option="stopped_open", tick=CURTAIN_UP),
                Act(option="stopped_closed", tick=CLOSING),
                Act(option="save"),
            ),
        )

    assert result["reason"] == "calibration_saved"
    assert subentries_of(entry, SUBENTRY_COVER_PROFILE) == []
    calibration = the_calibration(entry)
    assert calibration[CONF_PROFILE] == "tall"
    assert calibration[CONF_OVERRIDES] == {
        CONF_OPENING_TIME: pytest.approx(OPENING, abs=0.05),
        CONF_CLOSING_TIME: pytest.approx(CLOSING, abs=0.05),
        CONF_SLAT_TIME: pytest.approx(SLAT, abs=0.05),
    }
    # No tape, so no automatic runs at all.
    assert runner.runs == []


async def test_path_c_with_the_coefficients_measures_and_overrides_them_too(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The wide refinement: this curtain winds differently as well as running slower."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(
            hass,
            freezer,
            await start_flow(hass, entry),
            (
                Act(),
                Act(payload={"cover": UNIQUE_ID}),
                Act(option="path_c"),
                Act(payload={CONF_PROFILE: "tall"}),
                Act(option="times_and_rolls"),
                Act(option="lifted_off", tick=SLAT),
                Act(option="stopped_open", tick=CURTAIN_UP),
                Act(payload={CONF_HEIGHT: HEIGHT}),
                Act(option="stopped_closed", tick=CLOSING),
                Act(payload={"measured_cm": descent_cm(0.5)}),
                Act(payload={"measured_cm": ascent_cm(0.5)}),
                Act(option="save"),
            ),
        )

    assert result["reason"] == "calibration_saved"
    calibration = the_calibration(entry)
    assert calibration[CONF_HEIGHT] == HEIGHT
    assert calibration[CONF_OVERRIDES][CONF_CLOSING_ROLL] == pytest.approx(ROLL_DOWN, abs=0.01)
    assert calibration[CONF_OVERRIDES][CONF_OPENING_ROLL] == pytest.approx(ROLL_UP, abs=0.01)
    assert runner.runs == [(DIRECTION_CLOSE, 0.5), (DIRECTION_OPEN, 0.5)]
    # The summary of a refinement is about this cover, not about a kind of cover.
    assert subentries_of(entry, SUBENTRY_COVER_PROFILE) == []


async def test_the_refinement_summary_shows_the_cover_s_own_yaml(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Path C's snippet is the cover's own keys, not a `cover_profiles:` block."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(
            hass,
            freezer,
            await start_flow(hass, entry),
            (
                Act(),
                Act(payload={"cover": UNIQUE_ID}),
                Act(option="path_c"),
                Act(payload={CONF_PROFILE: "tall"}),
                Act(option="times_only"),
                Act(option="lifted_off", tick=SLAT),
                Act(option="stopped_open", tick=CURTAIN_UP),
                Act(option="stopped_closed", tick=CLOSING),
            ),
        )

    assert result["step_id"] == "summary"
    snippet = result["description_placeholders"]["yaml"]
    assert "cover_profiles:" not in snippet
    assert "cover:" in snippet
    assert "hallway_shutter:" in snippet
    # Nothing to improve: the precise level belongs to path A.
    assert "refine" not in result["menu_options"]


# --------------------------------------------------------------------------------------
# The cover selector, and the entry that has nothing to calibrate
# --------------------------------------------------------------------------------------
async def test_only_the_basic_covers_are_offered(hass: HomeAssistant, tmp_path) -> None:
    """An advanced cover reports its own position and every primitive refuses it.

    Mutation caught: listing every cover of the gateway (the flow would then reach
    `REASON_ADVANCED` on the first movement, which is a screen nobody should ever see).
    """
    async with calibrating(hass, tmp_path, MIXED_YAML) as (entry, _commands):
        result = await start_flow(hass, entry)
        result = await submit(hass, result, None)

    assert result["step_id"] == "cover"
    choices = result["data_schema"].schema["cover"].container
    assert choices == {UNIQUE_ID: COVER_NAME}


async def test_an_entry_without_a_basic_cover_says_so_instead_of_showing_an_empty_list(
    hass: HomeAssistant, tmp_path
) -> None:
    """The addendum of 12 September: a clear reason, not a select with nothing in it."""
    async with calibrating(hass, tmp_path, ADVANCED_ONLY_YAML) as (entry, _commands):
        result = await start_flow(hass, entry)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_basic_covers"
    assert entry.subentries == {}


# --------------------------------------------------------------------------------------
# Re-running, and deleting
# --------------------------------------------------------------------------------------
async def test_reconfiguring_a_calibration_measures_the_same_cover_again(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """There is nothing in a set of measurements to edit, so "Reconfigure" re-measures.

    The cover comes from the subentry rather than from a second selector, and the
    second run replaces the first rather than adding to it.

    Mutation caught: creating a second calibration for the same shutter (which
    `stored_calibrations` can only resolve by dictionary order).
    """
    existing = ConfigSubentryData(
        data={CONF_COVER_UNIQUE_ID: UNIQUE_ID, CONF_OVERRIDES: {CONF_SLAT_TIME: 9.9}},
        subentry_type=SUBENTRY_COVER_CALIBRATION,
        title=COVER_NAME,
        unique_id=f"{SUBENTRY_COVER_CALIBRATION}-{UNIQUE_ID}",
    )
    async with calibrating(hass, tmp_path, YAML, subentries=[existing]) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        subentry_id = next(iter(entry.subentries))
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_COVER_CALIBRATION),
            context={"source": "reconfigure", "subentry_id": subentry_id},
        )
        assert result["step_id"] == "reconfigure"
        # The cover was taken from the subentry: no selector, straight to the paths.
        result = await drive(hass, freezer, result, (Act(), *PATH_A_BASIC[2:]))
        await hass.async_block_till_done()

    assert result["reason"] == "calibration_saved"
    calibration = the_calibration(entry)
    assert calibration[CONF_PROFILE] == "tall"
    assert CONF_OVERRIDES not in calibration


async def test_saving_reaches_the_shutter_without_a_restart(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A calibration the user does not see take effect is one they do not believe in."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        assert hass.states.get(ENTITY).attributes[ATTR_CALIBRATION_SOURCE] == "yaml"

        await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC)
        await hass.async_block_till_done()
        # The reload built a new gateway handler, which starts disconnected (and an
        # unavailable entity publishes no attributes at all).
        await set_connected(hass, True)

        state = hass.states.get(ENTITY)
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "guided"
        assert state.attributes["Opening time"] == pytest.approx(OPENING, abs=0.05)


async def test_deleting_a_calibration_from_the_integration_page_reloads_the_entry(
    hass: HomeAssistant, tmp_path
) -> None:
    """Home Assistant's own delete button reaches the integration through no other hook.

    `async_remove_subentry` neither reloads nor tells the integration anything; what it
    does do is fire the config entry's update listeners, which is the listener 0.5.0
    registers (`__init__._async_watch_cover_subentries`). Without it the shutter keeps
    the deleted calibration until the next restart - and the next restart is exactly
    when nobody is watching any more.

    Mutation caught: dropping the listener, or making it compare only the *set* of
    subentries.
    """
    existing = ConfigSubentryData(
        data={CONF_COVER_UNIQUE_ID: UNIQUE_ID, CONF_OVERRIDES: {CONF_OPENING_TIME: 30.0}},
        subentry_type=SUBENTRY_COVER_CALIBRATION,
        title=COVER_NAME,
        unique_id=f"{SUBENTRY_COVER_CALIBRATION}-{UNIQUE_ID}",
    )
    async with calibrating(hass, tmp_path, YAML, subentries=[existing]) as (entry, _commands):
        assert hass.states.get(ENTITY).attributes["Opening time"] == 30.0

        subentry_id = next(iter(entry.subentries))
        hass.config_entries.async_remove_subentry(entry, subentry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == OPENING
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "yaml"


async def test_an_ordinary_entry_update_does_not_reload_anything(
    hass: HomeAssistant, tmp_path
) -> None:
    """The listener fires on every change to the entry, and reloads for one of them.

    Mutation caught: reloading on any update at all, which would rebuild every entity
    of the gateway each time the options dialog is opened and saved.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        handler = hass.data["myhome"][MAC]["entity"]
        hass.config_entries.async_update_entry(entry, title="A different title")
        await hass.async_block_till_done()
        # The same gateway handler: nothing was torn down and built again.
        assert hass.data["myhome"][MAC]["entity"] is handler


# --------------------------------------------------------------------------------------
# The profile subentry type
# --------------------------------------------------------------------------------------
async def test_a_profile_cannot_be_added_by_hand(hass: HomeAssistant, tmp_path) -> None:
    """Every number in a profile came off a tape; a form would only invite fiction."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        result = await start_flow(hass, entry, SUBENTRY_COVER_PROFILE)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "add_profile_via_calibration"


async def test_a_stored_profile_can_be_looked_at(hass: HomeAssistant, tmp_path) -> None:
    """"Reconfigure" on a profile shows what it holds and how to replace it."""
    profile = ConfigSubentryData(
        data={
            CONF_NAME: "tall",
            CONF_REFERENCE_HEIGHT: HEIGHT,
            CONF_OPENING_TIME: OPENING,
            CONF_CLOSING_TIME: CLOSING,
            CONF_SLAT_TIME: SLAT,
            CONF_OPENING_ROLL: ROLL_UP,
            CONF_CLOSING_ROLL: ROLL_DOWN,
            CONF_RAW: {"descent": []},
        },
        subentry_type=SUBENTRY_COVER_PROFILE,
        title="tall",
        unique_id=f"{SUBENTRY_COVER_PROFILE}-tall",
    )
    async with calibrating(hass, tmp_path, YAML, subentries=[profile]) as (entry, _commands):
        subentry_id = next(iter(entry.subentries))
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_COVER_PROFILE),
            context={"source": "reconfigure", "subentry_id": subentry_id},
        )
        assert result["step_id"] == "reconfigure"
        placeholders = result["description_placeholders"]
        assert placeholders["profile"] == "tall"
        assert f"{CONF_OPENING_TIME}: {OPENING}" in placeholders["values"]
        # The raw measurements are not shown: they are for a log, not for a dialog.
        assert "descent" not in placeholders["values"]

        result = await submit(hass, result, None)
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "profile_unchanged"
        # Looking at something must not change it.
        assert len(entry.subentries) == 1


async def test_both_subentry_types_are_offered_by_the_config_flow(
    hass: HomeAssistant, tmp_path
) -> None:
    """What the "Add" menu of the integration page is built from."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        supported = entry.supported_subentry_types
    assert set(supported) == {SUBENTRY_COVER_CALIBRATION, SUBENTRY_COVER_PROFILE}
    # Both can be re-opened from the row they created.
    assert all(kind["supports_reconfigure"] for kind in supported.values())


def test_every_plan_names_a_step_the_flow_really_has() -> None:
    """The plans are lists of method names, and a typo in one is a broken dialog.

    Mutation caught: renaming a step method without renaming it in the plan (nothing
    else in the suite would notice until that particular path was walked).
    """
    from custom_components.myhome import calibration_flow

    plans = (
        calibration_flow.PLAN_FULL,
        calibration_flow.PLAN_PRECISE,
        calibration_flow.PLAN_PROFILE,
        calibration_flow.PLAN_TIMES,
        calibration_flow.PLAN_TIMES_AND_ROLLS,
    )
    for plan in plans:
        for stage in plan:
            assert hasattr(CoverCalibrationFlow, f"async_step_{stage}"), stage


# --------------------------------------------------------------------------------------
# The edges of the conversation
# --------------------------------------------------------------------------------------
async def test_the_press_that_ends_the_opening_is_timed_too(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Both presses of the opening run carry the window, not only the first."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:6])
        assert result["step_id"] == "open_top"

        freezer.tick(timedelta(seconds=PRESS_TIMEOUT_SEC + 1))
        result = await choose(hass, result, "stopped_open")
    assert result["step_id"] == "problem_timeout"
    assert entry.subentries == {}


async def test_the_closing_press_is_timed_and_checked_like_the_opening_ones(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The descent has one press, and it is held to the same two rules.

    Mutation caught: checking the window and the order of the presses on the ascent
    alone, which is the copy-paste this pair of steps invites.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:8])
        assert result["step_id"] == "close_bottom"

        freezer.tick(timedelta(seconds=PRESS_TIMEOUT_SEC + 1))
        timed_out = await choose(hass, result, "stopped_closed")
        assert timed_out["step_id"] == "problem_timeout"

        # ...and a press that claims the shutter stopped before it started.
        result = await choose(hass, timed_out, "repeat_step")
        assert result["step_id"] == "close_bottom"
        freezer.tick(timedelta(seconds=-5))
        result = await choose(hass, result, "stopped_closed")
    assert result["step_id"] == "problem_bad_point"
    assert entry.subentries == {}


@pytest.mark.parametrize("step", ["measure_ascent", "measure_verify"])
async def test_every_tape_form_refuses_a_reading_above_the_travel(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, step: str
) -> None:
    """The check belongs to all three measurement screens, not only to the first."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        if step == "measure_ascent":
            acts = PATH_A_BASIC[:10]
        else:
            acts = (
                Act(),
                Act(payload={"cover": UNIQUE_ID}),
                Act(option="path_b"),
                Act(payload={CONF_PROFILE: "tall"}),
                Act(payload={CONF_HEIGHT: HEIGHT}),
                Act(option="verify_now"),
            )
        result = await drive(hass, freezer, await start_flow(hass, entry), acts)
        assert result["step_id"] == step

        result = await submit(hass, result, {"measured_cm": HEIGHT + 5})
    assert result["step_id"] == step
    assert result["errors"] == {"measured_cm": "above_the_travel"}


@pytest.mark.parametrize("error", [HomeAssistantError("no"), RuntimeError("no")])
async def test_a_failure_the_engine_does_not_name_still_ends_on_a_screen(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, error: Exception
) -> None:
    """A dialog that spins for ever is worse than a dialog that says "try again".

    Mutation caught: catching `CalibrationError` alone - a `ServiceValidationError` from
    an entity method, or any bug at all, would leave the progress bar turning with no
    way out but the X.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:3])
        runner.fail = error
        result = await submit(hass, result, None)

    assert result["step_id"] == "problem_unknown"
    assert entry.subentries == {}


async def test_a_stop_that_is_refused_does_not_stop_the_flow(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"It did not do what it should" sends a stop that may itself be refused.

    The step is repeated anyway: the stop is an attempt to tidy up, not a measurement,
    and refusing to go on because the tidying failed would strand the user on a screen
    whose only other button is Cancel.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:5])
        runner.fail = CalibrationError(REASON_NOT_STOPPED, "the gateway would not take it")
        runner.fail_on = "stop"
        result = await choose(hass, result, "not_right")

    assert result["step_id"] == "open_lift"


async def test_a_run_that_cannot_be_stopped_says_so(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`not_stopped` during a measured run: the shutter ran on and there is no point."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:8])
        runner.fail = CalibrationError(REASON_NOT_STOPPED, "no")
        runner.fail_on = "run"
        freezer.tick(timedelta(seconds=CLOSING))
        result = await choose(hass, result, "stopped_closed")

    assert result["step_id"] == "problem_not_stopped"
    assert entry.subentries == {}


async def test_path_c_starts_from_the_profile_the_cover_already_follows(
    hass: HomeAssistant, tmp_path
) -> None:
    """The refinement's profile field is pre-filled with the one in force.

    Mutation caught: reading the profile from `myhome.yaml` only - a cover that was
    moved to another profile by a guided calibration would be offered the file's.
    """
    profile = ConfigSubentryData(
        data={
            CONF_NAME: "short",
            CONF_REFERENCE_HEIGHT: 120.0,
            CONF_OPENING_TIME: 14.0,
            CONF_CLOSING_TIME: 13.5,
            CONF_SLAT_TIME: 3.0,
            CONF_OPENING_ROLL: 1.4,
            CONF_CLOSING_ROLL: 1.3,
        },
        subentry_type=SUBENTRY_COVER_PROFILE,
        title="short",
        unique_id=f"{SUBENTRY_COVER_PROFILE}-short",
    )
    calibration = ConfigSubentryData(
        data={CONF_COVER_UNIQUE_ID: UNIQUE_ID, CONF_PROFILE: "short", CONF_HEIGHT: 120.0},
        subentry_type=SUBENTRY_COVER_CALIBRATION,
        title=COVER_NAME,
        unique_id=f"{SUBENTRY_COVER_CALIBRATION}-{UNIQUE_ID}",
    )
    async with calibrating(hass, tmp_path, PROFILE_YAML, subentries=[profile, calibration]) as (
        entry,
        _commands,
    ):
        result = await start_flow(hass, entry)
        result = await submit(hass, result, None)
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "path_c")

    assert result["step_id"] == "path_c"
    key = next(key for key in result["data_schema"].schema if key == CONF_PROFILE)
    assert key.default() == "short"


async def test_a_profile_deleted_while_the_dialog_was_open_is_said_so(
    hass: HomeAssistant, tmp_path
) -> None:
    """Two browser tabs, one profile: the menu was built before it went.

    Mutation caught: indexing the (now empty) list of profiles to build the default of
    the select, which raises inside the flow instead of telling the user.
    """
    profile = ConfigSubentryData(
        data={
            CONF_NAME: "short",
            CONF_REFERENCE_HEIGHT: 120.0,
            CONF_OPENING_TIME: 14.0,
            CONF_CLOSING_TIME: 13.5,
            CONF_SLAT_TIME: 3.0,
            CONF_OPENING_ROLL: 1.4,
            CONF_CLOSING_ROLL: 1.3,
        },
        subentry_type=SUBENTRY_COVER_PROFILE,
        title="short",
        unique_id=f"{SUBENTRY_COVER_PROFILE}-short",
    )
    async with calibrating(hass, tmp_path, YAML, subentries=[profile]) as (entry, _commands):
        for option in ("path_b", "path_c"):
            result = await start_flow(hass, entry)
            result = await submit(hass, result, None)
            result = await submit(hass, result, {"cover": UNIQUE_ID})
            assert option in result["menu_options"]

            subentry_id = next(iter(entry.subentries))
            hass.config_entries.async_remove_subentry(entry, subentry_id)
            result = await choose(hass, result, option)
            assert result["type"] is FlowResultType.ABORT
            assert result["reason"] == "no_profiles"

            # Put it back for the second half of the loop.
            hass.config_entries.async_add_subentry(
                entry,
                calibration_store.ConfigSubentry(
                    data=dict(profile["data"]),
                    subentry_type=SUBENTRY_COVER_PROFILE,
                    title="short",
                    unique_id=f"{SUBENTRY_COVER_PROFILE}-short",
                ),
            )
            await hass.async_block_till_done()
            await set_connected(hass, True)


async def test_a_calibration_whose_cover_is_gone_cannot_be_re_run(
    hass: HomeAssistant, tmp_path
) -> None:
    """A shutter removed from `myhome.yaml` leaves its subentry behind for a while.

    Mutation caught: carrying on with `self._cover = None` and raising on the first
    movement instead of saying which cover is missing.
    """
    orphan = ConfigSubentryData(
        data={CONF_COVER_UNIQUE_ID: f"{MAC}-2-99", CONF_OVERRIDES: {CONF_SLAT_TIME: 4.0}},
        subentry_type=SUBENTRY_COVER_CALIBRATION,
        title="Gone",
        unique_id=f"{SUBENTRY_COVER_CALIBRATION}-{MAC}-2-99",
    )
    async with calibrating(hass, tmp_path, YAML, subentries=[orphan]) as (entry, _commands):
        subentry_id = next(iter(entry.subentries))
        result = await hass.config_entries.subentries.async_init(
            (entry.entry_id, SUBENTRY_COVER_CALIBRATION),
            context={"source": "reconfigure", "subentry_id": subentry_id},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown_cover"


async def test_a_cover_without_an_entity_yet_is_refused_rather_than_driven(
    hass: HomeAssistant, tmp_path
) -> None:
    """Between a reload and the platform being set up there is no entity to drive."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        result = await start_flow(hass, entry)
        result = await submit(hass, result, None)
        # The entity registry of the device, emptied the way an unload empties it.
        hass.data["myhome"][MAC]["platforms"][COVER][DEVICE_KEY]["entities"].clear()
        result = await submit(hass, result, {"cover": UNIQUE_ID})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unknown_cover"


async def test_a_verification_whose_profile_vanished_reports_no_gap(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The check compares the tape against a profile; somebody may have just deleted it.

    Mutation caught: reaching into `derive_cover_from_profile(None, ...)` and raising
    inside the flow, which loses the reading the user has just taken.
    """
    profile = ConfigSubentryData(
        data={
            CONF_NAME: "short",
            CONF_REFERENCE_HEIGHT: HEIGHT,
            CONF_OPENING_TIME: OPENING,
            CONF_CLOSING_TIME: CLOSING,
            CONF_SLAT_TIME: SLAT,
            CONF_OPENING_ROLL: ROLL_UP,
            CONF_CLOSING_ROLL: ROLL_DOWN,
        },
        subentry_type=SUBENTRY_COVER_PROFILE,
        title="short",
        unique_id=f"{SUBENTRY_COVER_PROFILE}-short",
    )
    async with calibrating(hass, tmp_path, YAML, subentries=[profile]) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(
            hass,
            freezer,
            await start_flow(hass, entry),
            (
                Act(),
                Act(payload={"cover": UNIQUE_ID}),
                Act(option="path_b"),
                Act(payload={CONF_PROFILE: "short"}),
                Act(payload={CONF_HEIGHT: HEIGHT}),
                Act(option="verify_now"),
            ),
        )
        assert result["step_id"] == "measure_verify"

        subentry_id = next(
            key
            for key, sub in entry.subentries.items()
            if sub.subentry_type == SUBENTRY_COVER_PROFILE
        )
        hass.config_entries.async_remove_subentry(entry, subentry_id)
        result = await submit(hass, result, {"measured_cm": descent_cm(0.5)})

    assert result["step_id"] == "verify_result"
    assert result["description_placeholders"]["deviation"] == "0"


async def test_a_movement_that_ends_in_an_impossible_measurement_has_a_screen_too(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`bad_point` can also come out of the engine, not only out of two presses."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await start_flow(hass, entry), PATH_A_BASIC[:3])
        runner.fail = CalibrationError("bad_point", "that is not a point")
        result = await submit(hass, result, None)

    assert result["step_id"] == "problem_bad_point"


async def test_the_store_still_reloads_an_entry_that_nothing_is_watching(
    hass: HomeAssistant, tmp_path
) -> None:
    """The two halves of "a calibration takes effect at once" are independent.

    Since 0.5.0 the reload of a Save normally comes from the update listener, which
    is eager enough to have started unloading the entry by the time the store's own
    `async_schedule_reload` looks at it - so the helper's reload is skipped rather than
    doubled. That is the *interaction*, not the contract: the four helpers promise to
    reload on their own, and an entry without the listener (a caller outside a flow, a
    future refactor) must still see the numbers reach the shutter.

    Mutation caught: deleting the store's own reload on the grounds that the listener
    covers it.
    """
    # Removed before the setup registers it, rather than after: the entry also holds
    # the callback that *unregisters* it, and clearing the list behind its back breaks
    # the next unload.
    with patch("custom_components.myhome._async_watch_cover_subentries"):
        async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
            assert entry.update_listeners == []
            async_set_cover_calibration(
                hass,
                entry,
                UNIQUE_ID,
                cover_calibration_data(UNIQUE_ID, overrides={CONF_SLAT_TIME: 9.0}),
            )
            await hass.async_block_till_done()
            await set_connected(hass, True)

            assert hass.states.get(ENTITY).attributes["Slat time"] == 9.0
