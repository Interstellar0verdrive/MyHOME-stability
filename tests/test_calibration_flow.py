"""Tests for everything under "Configura" (0.5.0 v2): the dialog, screen by screen.

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

import json
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import ATTR_POSITION, DOMAIN as COVER
from homeassistant.const import ATTR_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

import custom_components.myhome
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
    IDLE_TIMEOUT_SEC,
    MOVED_IDLE_TIMEOUT_SEC,
    NO_PROFILE,
    PLAN_FULL,
    PLAN_PRECISE,
    PLAN_PROFILE,
    PLAN_TIMES,
    PLAN_TIMES_AND_ROLLS,
    PLAN_VERIFY_B,
    PRESS_TIMEOUT_SEC,
    parse_number,
)
from custom_components.myhome.calibration_store import loaded_store
from custom_components.myhome.config_flow import MyHomeOptionsFlowHandler
from custom_components.myhome.const import (
    ATTR_CALIBRATING,
    ATTR_CALIBRATION_SOURCE,
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

# The same window, but a `myhome.yaml` that carries its own run times for it - which
# is how every basic cover in the owner's file is configured - and carries numbers that
# are *not* the shutter's. A fixture whose numbers are the fake shutter's own cannot
# tell "the calibration reached the shutter" from "the file never moved" (0.5.0 review,
# BUG-1), and its cover is written under a key that is not the entity's object id, which
# is what the YAML snippet has to be built from.
FILE_OPENING = 30.0
FILE_CLOSING = 29.0
FILE_SLAT = 6.0
FILE_ROLL = 1.2
YAML_KEY = "front_hall_roller"
OWN_NUMBERS_YAML = f"""
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

PROFILE_AND_OWN_NUMBERS_YAML = (
    OWN_NUMBERS_YAML
    + f"""  cover_profiles:
    tall:
      reference_height: {HEIGHT}
      opening_time: {OPENING}
      closing_time: {CLOSING}
      slat_time: {SLAT}
      roll: {ROLL_DOWN}
"""
)

# A shutter whose modelled run outlasts the watchdog's patience, so that a movement
# started before the clock jumps is still in flight when the watchdog fires. On every
# other fixture the cover reaches its end stop - and stops itself - on the way.
SLOW_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: {COVER_NAME}
      opening_time: 3000
      closing_time: 3000
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

# The same, with no `height:` for the cover: nothing anywhere knows this window's own
# travel, which is the one case a summary may report "-" for it.
NO_HEIGHT_PROFILE_YAML = PROFILE_YAML.replace(f"      height: {HEIGHT}\n", "")

# Two basic covers, so the assignment form has more than one row and the second one has
# no height anywhere.
TWO_COVERS_YAML = f"""
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
    landing_shutter:
      where: '82'
      name: Landing Shutter
      opening_time: 18
"""

SECOND_UNIQUE_ID = f"{MAC}-2-82"


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

    A conversation holds a calibration session on the cover for as long as it lasts,
    and gives it back in `async_remove` - which Home Assistant calls when the dialog is
    closed. A test that simply walks away leaves that to the garbage collector, which
    runs the release off the event loop and turns a perfectly good assertion into an
    unraisable-exception warning three tests later. Closing the dialogs here is what
    the browser's X does, and it does it while the entry is still loaded.
    """
    async with setup_myhome(hass, tmp_path, yaml_text, **kwargs) as (entry, commands):
        try:
            yield entry, commands
        finally:
            manager = hass.config_entries.options
            for flow in list(manager.async_progress()):
                manager.async_abort(flow["flow_id"])


# --------------------------------------------------------------------------------------
# Driving the options flow
# --------------------------------------------------------------------------------------
async def open_dialog(hass: HomeAssistant, entry) -> dict[str, Any]:
    """Press "Configura": the menu every screen of this release hangs off."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU, result
    assert result["step_id"] == "init"
    check_the_screen_renders(result)
    return result


async def _resolve(hass: HomeAssistant, result: dict[str, Any]) -> dict[str, Any]:
    """Let a progress screen finish, and answer with the screen that follows it."""
    while result["type"] is FlowResultType.SHOW_PROGRESS:
        check_the_screen_renders(result)
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_configure(result["flow_id"])
    check_the_screen_renders(result)
    return result


# --------------------------------------------------------------------------------------
# The one invariant every screen has to satisfy
# --------------------------------------------------------------------------------------
STRINGS = json.loads(
    (Path(custom_components.myhome.__file__).parent / "strings.json").read_text(encoding="utf-8")
)
PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
# Every step id this check has actually looked at, so that a check which silently
# stopped finding anything can be told from one that passes.
RENDERED_STEPS: set[str] = set()


def check_the_screen_renders(result: dict[str, Any]) -> None:
    """Every `{placeholder}` in this screen's text is one the step really passed.

    Home Assistant renders a step's texts through formatjs, which answers a
    substitution it was not given by replacing **the whole string** with
    "Translation [formatjs Error: MISSING_VALUE] The intl string context variable ...".
    That is what the second live walk-through found on the very first screen of
    "Configura" - `init`, whose title said `{gateway}`.

    A menu's title is the case worth stating twice: the frontend renders a menu header
    with no placeholders at all (`renderMenuHeader` passes none, while
    `renderMenuDescription` passes them), so a menu title that carries one is broken
    however carefully the step fills it in. Hence the two different rules below.

    Called from `_resolve`, so every screen every test of this file walks through is
    checked, which is the only way to be sure the rule holds for screens nobody
    thought to write a test about.
    """
    step_id = result.get("step_id")
    if step_id is None:
        return
    if result["type"] is FlowResultType.SHOW_PROGRESS:
        text = STRINGS["options"]["progress"][result["progress_action"]]
        given = set(result.get("description_placeholders") or {})
        assert set(PLACEHOLDER.findall(text)) <= given, f"progress {result['progress_action']}"
        return
    step = STRINGS["options"]["step"].get(step_id)
    if step is None:  # a screen of the config flow, or one with no text of its own
        return
    RENDERED_STEPS.add(step_id)
    given = set(result.get("description_placeholders") or {})
    wanted = set(PLACEHOLDER.findall(step.get("description", "")))
    for description in (step.get("data_description") or {}).values():
        wanted |= set(PLACEHOLDER.findall(description))
    title = set(PLACEHOLDER.findall(step.get("title", "")))
    if result["type"] is FlowResultType.MENU:
        assert not title, f"{step_id}: a menu title cannot be given placeholders"
        check_the_ways_back_come_last(result)
    else:
        wanted |= title
    assert wanted <= given, f"{step_id}: {sorted(wanted - given)} never reaches the screen"


# Every menu option that goes *back* rather than on. Home Assistant draws the same
# chevron next to every entry of a menu and allows no other icon, so an arrow in the
# label would point the wrong way: what tells a way out from an action is that it comes
# last (FLOW, second live walk-through).
RETURN_OPTIONS = frozenset(
    {
        "init",
        "finish",
        "cancel_flow",
        "profiles_covers",
        "calibrations",
        "profile_actions",
        "calibration_actions",
    }
)


def check_the_ways_back_come_last(result: dict[str, Any]) -> None:
    """"Torna al menu", "Annulla" and "Chiudi" are the bottom of every menu.

    "Profili e tapparelle" and "Calibrazioni" are ways *forward* on the dialog's own
    first screen and ways back everywhere else, which is why the top menu is asked a
    narrower question.
    """
    options = list(result["menu_options"])
    ways_back = {"init", "finish", "cancel_flow"} if result["step_id"] == "init" else RETURN_OPTIONS
    back = [index for index, option in enumerate(options) if option in ways_back]
    if not back:
        return
    assert back == list(range(min(back), len(options))), (
        f"{result['step_id']}: {options} - the ways back are not last"
    )


async def submit(hass: HomeAssistant, result: dict[str, Any], user_input=None) -> dict[str, Any]:
    """Press Submit on a form (or hand it its fields) and wait out any movement.

    A form with no fields is submitted with an empty mapping and not with `None`,
    because that is what the frontend sends: `None` means "show me this form", which is
    exactly what the confirmation screens would do for ever.
    """
    if result["type"] is FlowResultType.FORM and user_input is None:
        user_input = {}
    result = await hass.config_entries.options.async_configure(result["flow_id"], user_input)
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
    """Play a list of user actions against the dialog."""
    for act in acts:
        if act.tick:
            freezer.tick(timedelta(seconds=act.tick))
        if act.option is not None:
            result = await choose(hass, result, act.option)
        else:
            result = await submit(hass, result, act.payload)
    return result


# Getting as far as the first screen of the guided conversation.
ENTER: tuple[Act, ...] = (Act(option="calibrate"), Act(option="cover"))

# The full walk of path A at the basic level, as a list of what the user does. It is a
# list rather than a function so that the "abandoning it at any screen writes nothing"
# test can replay any prefix of it.
PATH_A_BASIC: tuple[Act, ...] = (
    *ENTER,
    Act(payload={"cover": UNIQUE_ID}),
    Act(option="path_a"),
    Act(option="begin"),
    Act(option="confirm_closed"),
    Act(option="open_start"),
    Act(option="lifted_off", tick=SLAT),
    Act(option="stopped_open", tick=CURTAIN_UP),
    Act(option="accept_step"),
    Act(payload={CONF_HEIGHT: str(HEIGHT)}),
    Act(option="accept_step"),
    Act(option="close_start"),
    Act(option="stopped_closed", tick=CLOSING),
    Act(option="accept_step"),
    Act(payload={"measured_cm": str(descent_cm(0.5))}),
    Act(option="accept_step"),
    Act(payload={"measured_cm": str(ascent_cm(0.5))}),
    Act(option="accept_step"),
    Act(payload={CONF_NAME: "tall"}),
    Act(option="save"),
)

PATH_A_PRECISE: tuple[Act, ...] = (
    *PATH_A_BASIC[:-1],
    Act(option="refine"),
    Act(payload={"measured_cm": str(descent_cm(0.25))}),
    Act(option="accept_step"),
    Act(payload={"measured_cm": str(descent_cm(0.75))}),
    Act(option="accept_step"),
    Act(payload={"measured_cm": str(ascent_cm(0.25))}),
    Act(option="accept_step"),
    Act(payload={"measured_cm": str(ascent_cm(0.75))}),
    Act(option="accept_step"),
    Act(payload={"measured_cm": str(descent_cm(0.40))}),
    Act(option="accept_step"),
    Act(option="save"),
)


def the_store(hass: HomeAssistant, entry):
    return loaded_store(hass, entry)


def the_profile(hass: HomeAssistant, entry) -> dict[str, Any]:
    profiles = the_store(hass, entry).raw_profiles
    assert len(profiles) == 1
    return next(iter(profiles.values()))


def the_calibration(hass: HomeAssistant, entry) -> dict[str, Any]:
    covers = the_store(hass, entry).raw_covers
    assert len(covers) == 1
    return next(iter(covers.values()))


@pytest.fixture(autouse=True)
def _forget_clash_warnings():
    calibration_store.reset_name_clash_warnings()
    yield


# --------------------------------------------------------------------------------------
# The menu
# --------------------------------------------------------------------------------------
async def test_the_dialog_opens_on_a_menu_with_everything_behind_it(
    hass: HomeAssistant, tmp_path
) -> None:
    """One entry point, four things to do, and a way out.

    Mutation caught: putting the gateway form back at the top (the calibration would be
    reachable from nowhere), or dropping "Chiudi" (the dialog could only be left by the
    X, which never writes the options).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        result = await open_dialog(hass, entry)
        assert result["menu_options"] == [
            "calibrate",
            "profiles_covers",
            "calibrations",
            "gateway",
            "finish",
        ]


async def test_the_calibration_is_not_offered_without_a_basic_cover(
    hass: HomeAssistant, tmp_path
) -> None:
    """An entry whose covers all report their own position has nothing to calibrate.

    The menu item is hidden rather than offered and then refused: an entry point that
    only ever leads to "there is nothing here" is worse than no entry point.

    Mutation caught: listing the item unconditionally.
    """
    async with calibrating(hass, tmp_path, ADVANCED_ONLY_YAML) as (entry, _commands):
        result = await open_dialog(hass, entry)
        assert "calibrate" not in result["menu_options"]
        # ...and the rest of the dialog still works.
        assert "gateway" in result["menu_options"]


async def test_closing_the_dialog_without_touching_anything_reloads_nothing(
    hass: HomeAssistant, tmp_path
) -> None:
    """"Chiudi" on a dialog that changed nothing must not restart the gateway.

    Mutation caught: reloading unconditionally when the dialog closes (every look at
    the stored values would cost a disconnect and a reconnect).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        with patch.object(hass.config_entries, "async_schedule_reload") as reload:
            result = await choose(hass, await open_dialog(hass, entry), "finish")
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert reload.call_count == 0


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
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC)
        assert result["step_id"] == "saved"

        profile = the_profile(hass, entry)
        assert profile[CONF_NAME] == "tall"
        assert profile[CONF_REFERENCE_HEIGHT] == HEIGHT
        assert profile[CONF_OPENING_TIME] == pytest.approx(OPENING, abs=0.05)
        assert profile[CONF_CLOSING_TIME] == pytest.approx(CLOSING, abs=0.05)
        assert profile[CONF_SLAT_TIME] == pytest.approx(SLAT, abs=0.05)
        assert profile[CONF_CLOSING_ROLL] == pytest.approx(ROLL_DOWN, abs=0.01)
        assert profile[CONF_OPENING_ROLL] == pytest.approx(ROLL_UP, abs=0.01)
        # The window it was measured on, for the screen that shows it.
        assert profile["reference_cover"] == COVER_NAME
        # The measurements themselves are kept beside the conclusions drawn from them.
        assert profile[CONF_RAW]["descent"] == [
            [pytest.approx(CURTAIN_DOWN / 2), pytest.approx(descent_cm(0.5))]
        ]

        calibration = the_calibration(hass, entry)
        assert calibration[CONF_PROFILE] == "tall"
        assert calibration[CONF_HEIGHT] == HEIGHT
        # ...and the same numbers again as this window's own overrides. The profile is
        # what the *next* shutter of this kind inherits; the overrides are what make
        # *this* one run on what was just measured, because a profile does not beat a
        # key written in the file and a basic cover's run times usually live there.
        assert calibration["overrides"] == {
            CONF_OPENING_TIME: pytest.approx(OPENING, abs=0.05),
            CONF_CLOSING_TIME: pytest.approx(CLOSING, abs=0.05),
            CONF_SLAT_TIME: pytest.approx(SLAT, abs=0.05),
            CONF_OPENING_ROLL: pytest.approx(ROLL_UP, abs=0.01),
            CONF_CLOSING_ROLL: pytest.approx(ROLL_DOWN, abs=0.01),
        }


async def test_path_a_walks_the_screens_in_the_order_the_flow_document_agreed(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Screen by screen, with the movements each one is responsible for.

    Two things this pins that the live walk-through found missing: no movement starts
    on a screen the user has not read (the shutter is homed, then the instructions, then
    an explicit "Avvia"), and every measurement is confirmed before the next one starts.

    Mutation caught: starting the timed run inside the progress screen that homes the
    shutter, which is what put the bottom edge past the slats before the user had read
    what they were supposed to watch.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await open_dialog(hass, entry)

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
        "calibrate",
        "cover",
        "path",
        "path_a",
        "home_closed_done",
        "open_brief",
        "open_lift",
        "open_top",
        "open_result",
        "height",
        "height_result",
        "close_brief",
        "close_bottom",
        "close_result",
        "measure_descent",
        "tape_result",
        "measure_ascent",
        "tape_result",
        "profile_name",
        "summary_basic",
        "saved",
    ]
    # Closed for the first press, open for the descent, and the far end stop before
    # each of the two timed runs.
    assert runner.homed == [
        DIRECTION_CLOSE,  # home_closed
        DIRECTION_CLOSE,  # open_timed brings it back to the bottom
        DIRECTION_OPEN,  # close_timed takes it to the top
        DIRECTION_OPEN,  # half_down
        DIRECTION_CLOSE,  # half_up
    ]
    assert runner.started == [DIRECTION_OPEN, DIRECTION_CLOSE]
    assert runner.runs == [(DIRECTION_CLOSE, 0.5), (DIRECTION_OPEN, 0.5)]


async def test_nothing_moves_until_the_user_starts_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The rule the live walk-through produced: instructions first, then a button.

    The briefing screen is reached with the shutter standing at the end stop it needs,
    and the direction frame only goes out when the user presses "1) Avvia".

    Mutation caught: folding the start back into the homing stage.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:6])
        assert result["step_id"] == "open_brief"
        assert runner.started == []
        result = await choose(hass, result, "open_start")
        assert result["step_id"] == "open_lift"
        assert runner.started == [DIRECTION_OPEN]


async def test_every_measurement_is_confirmed_before_the_next_one(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The presses, the height and the tape all get a screen showing what was taken.

    Before this, a press half a second late could only be undone by cancelling the
    whole conversation.

    Mutation caught: advancing straight from the last press to the next stage.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:9])
        assert result["step_id"] == "open_result"
        assert result["description_placeholders"]["slat"] == f"{SLAT:.1f}"
        assert result["description_placeholders"]["run"] == f"{OPENING:.1f}"
        assert result["menu_options"] == ["accept_step", "repeat_step"]


async def test_repeating_a_measurement_throws_the_first_one_away(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Ripeti la misura" re-runs that stage's own movements and nothing else.

    Mutation caught: keeping the discarded reading (the fit would then be given the
    same fraction twice, once right and once wrong).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        # ... as far as the descent's confirmation screen.
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:16])
        assert result["step_id"] == "tape_result"
        runs_before = len(runner.runs)

        result = await choose(hass, result, "repeat_tape")
        assert result["step_id"] == "measure_descent"
        assert len(runner.runs) == runs_before + 1
        result = await submit(hass, result, {"measured_cm": str(descent_cm(0.5))})
        result = await choose(hass, result, "accept_step")
        result = await submit(hass, result, {"measured_cm": str(ascent_cm(0.5))})
        result = await choose(hass, result, "accept_step")
        result = await submit(hass, result, {CONF_NAME: "tall"})
        assert result["step_id"] == "summary_basic"
        result = await choose(hass, result, "save")

        # One reading per direction, not two: the discarded one is gone.
        assert the_profile(hass, entry)[CONF_RAW]["descent"] == [
            [pytest.approx(CURTAIN_DOWN / 2), pytest.approx(descent_cm(0.5))]
        ]


async def test_the_height_can_be_written_again_without_moving_anything(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The height is read where the previous stage left the shutter: nothing to re-run.

    Mutation caught: giving the height screen the tape steps' "repeat", which would
    re-run the ascent and leave the shutter somewhere else entirely.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:11])
        assert result["step_id"] == "height_result"
        homed_before = list(runner.homed)

        result = await choose(hass, result, "repeat_measure")
        assert result["step_id"] == "height"
        assert runner.homed == homed_before
        result = await submit(hass, result, {CONF_HEIGHT: "190"})
        assert result["description_placeholders"]["height"] == "190.0"


async def test_the_name_is_asked_before_the_summary_and_reaches_the_snippet(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The summary shows the YAML of the profile, so its key has to exist by then.

    Before this the snippet carried the cover's own key as the profile name, because
    the name was asked on the screen *after* the one showing it.

    Mutation caught: moving the name form back behind the summary.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:-2])
        assert result["step_id"] == "profile_name"
        result = await submit(hass, result, {CONF_NAME: "camere"})
        assert result["step_id"] == "summary_basic"
        assert "camere:" in result["description_placeholders"]["yaml"]
        assert result["description_placeholders"]["height"] == "195 cm"


async def test_the_basic_summary_has_no_accuracy_and_offers_the_precise_level(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """One reading per direction reproduces itself, so there is no residual to show.

    Showing "0.0 cm" read as "perfect" and put the precise level - the only thing that
    measures the reaction time of the presses - out of reach in practice.

    Mutation caught: showing the residual of a one-point fit.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:-1])
        assert result["step_id"] == "summary_basic"
        assert result["menu_options"] == ["save", "refine", "cancel_flow"]
        assert result["description_placeholders"]["accuracy"] == "\u2013"


async def test_the_precise_level_adds_four_readings_and_ends_on_its_own_summary(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Migliora la precisione": 25 % and 75 % in both directions, then a check at 40 %.

    Three points per direction let the fit solve the roll *and* a scale on the run
    time, which is the reaction time of the presses being measured rather than assumed.

    Mutation caught: repeating the presses instead (the scale would be fitted against
    the very error it exists to absorb).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_PRECISE)
        assert result["step_id"] == "saved"

        assert runner.runs[-5:] == [
            (DIRECTION_CLOSE, 0.25),
            (DIRECTION_CLOSE, 0.75),
            (DIRECTION_OPEN, 0.25),
            (DIRECTION_OPEN, 0.75),
            (DIRECTION_CLOSE, 0.40),
        ]
        assert runner.started == [DIRECTION_OPEN, DIRECTION_CLOSE]

        profile = the_profile(hass, entry)
        assert profile[CONF_CLOSING_ROLL] == pytest.approx(ROLL_DOWN, abs=0.05)
        assert profile[CONF_OPENING_ROLL] == pytest.approx(ROLL_UP, abs=0.05)
        assert len(profile[CONF_RAW]["descent"]) == 3
        assert profile[CONF_RAW]["precise"] is True


async def test_the_precise_summary_reports_an_accuracy_and_offers_only_save(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Two summaries, because the two levels have different things to say.

    Mutation caught: offering "Migliora la precisione" again on the precise summary,
    which is a promise of an option that is not there.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_PRECISE[:-1])
        assert result["step_id"] == "summary_precise"
        assert result["menu_options"] == ["save", "cancel_flow"]
        accuracy = result["description_placeholders"]["accuracy"]
        assert accuracy.endswith(" cm") and float(accuracy[:-3]) < 2.0
        assert result["description_placeholders"]["percent"] == "40"


async def test_the_precise_tape_screens_say_what_is_expected(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A tape read from the floor instead of the rest is out by tens of centimetres.

    The basic level has only the ordinary geometry of a roller shutter to go on, so it
    says the same thing with a wider margin; the precise level has a fitted model of
    *this* window and can afford to be strict.

    Mutation caught: dropping the expectation, or quoting the same tolerance at both
    levels.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:15])
        assert result["step_id"] == "measure_descent"
        rough = result["description_placeholders"]
        assert rough["tolerance"] == "15"
        assert float(rough["expected"]) > 0

        result = await drive(hass, freezer, result, (*PATH_A_BASIC[15:-1], Act(option="refine")))
        assert result["step_id"] == "measure_descent"
        precise = result["description_placeholders"]
        assert precise["tolerance"] == "3"
        assert float(precise["expected"]) == pytest.approx(descent_cm(0.25), abs=1.0)


async def test_the_verification_screen_reports_the_gap_in_centimetres(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one number in the whole flow a tape can check without arithmetic.

    Mutation caught: comparing the reading against the *measured* fraction rather than
    against the model at the fraction the shutter really ran.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_PRECISE[:-3])
        assert result["step_id"] == "measure_verify"
        # Two centimetres lower than the model expects.
        result = await submit(hass, result, {"measured_cm": str(descent_cm(0.40) - 2.0)})
        assert result["step_id"] == "verify_result"
        assert result["description_placeholders"]["deviation"] == "2.0"
        # Path A never offers the refinement: it *is* the measurement.
        assert result["menu_options"] == ["accept_step", "repeat_tape"]


@pytest.mark.parametrize("stop_at", range(1, len(PATH_A_BASIC)))
async def test_abandoning_the_conversation_at_any_screen_writes_nothing(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, stop_at: int
) -> None:
    """"Nothing is saved until the last screen" is the promise; this is the proof.

    Mutation caught: storing anything before Save - a height, a profile name, a partial
    set of overrides.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:stop_at])
        store = the_store(hass, entry)
        assert store.raw_profiles == {}
        assert store.raw_covers == {}


async def test_cancelling_from_the_summary_saves_nothing_and_says_so(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The last chance to walk away, and a screen that confirms nothing happened."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:-1])
        result = await choose(hass, result, "cancel_flow")
        assert result["step_id"] == "cancelled"
        assert the_store(hass, entry).raw_profiles == {}
        # ...and the dialog is still usable.
        assert result["menu_options"] == ["calibrate", "init"]


async def test_a_second_walk_under_the_same_name_replaces_the_profile(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The commonest reason to walk path A again is that the first measurement was poor.

    Refusing the name sent the user back to the name form with three minutes of
    measurements about to be thrown away.

    Mutation caught: bringing the `name_in_use` refusal back.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC)
        first = the_profile(hass, entry)[CONF_OPENING_TIME]

        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:-2])
        result = await submit(hass, result, {CONF_NAME: "tall"})
        result = await choose(hass, result, "save")
        assert result["step_id"] == "saved"
        assert list(the_store(hass, entry).raw_profiles) == ["tall"]
        assert the_profile(hass, entry)[CONF_OPENING_TIME] == pytest.approx(first, abs=0.2)


async def test_a_name_already_in_the_file_shadows_it_instead_of_being_refused(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A `cover_profiles:` block of the same name is untouched and goes on being shadowed."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:-2])
        result = await submit(hass, result, {CONF_NAME: "tall"})
        assert result["step_id"] == "summary_basic"
        result = await choose(hass, result, "save")
        assert result["step_id"] == "saved"
        assert the_profile(hass, entry)[CONF_NAME] == "tall"


async def test_a_profile_name_has_to_be_a_yaml_key(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """It may end up in `cover_profiles:`, so it is a key with a key's rules."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:-2])
        result = await submit(hass, result, {CONF_NAME: "le alte"})
        assert result["errors"] == {CONF_NAME: "invalid_name"}
        result = await submit(hass, result, {CONF_NAME: "alte"})
        assert result["step_id"] == "summary_basic"


# --------------------------------------------------------------------------------------
# Numbers as people write them
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("written", "expected"),
    [("198.5", 198.5), ("198,5", 198.5), (" 200 ", 200.0), ("0", 0.0), ("", None), ("x", None)],
)
def test_a_decimal_may_be_written_with_a_comma_or_a_point(written: str, expected) -> None:
    """A `<input type="number">` refuses the separator of most of these languages.

    Mutation caught: parsing with `float()` alone, which turns "198,5" into an error
    message the user cannot act on.
    """
    assert parse_number(written) == expected


async def test_a_tape_reading_written_with_a_comma_is_accepted(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """End to end, on the one field every path goes through."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:10])
        assert result["step_id"] == "height"
        result = await submit(hass, result, {CONF_HEIGHT: "195,5"})
        assert result["description_placeholders"]["height"] == "195.5"


async def test_something_that_is_not_a_number_is_sent_back_to_the_form(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Every numeric field is text, so every one of them has to say what it wants."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:10])
        result = await submit(hass, result, {CONF_HEIGHT: "about two metres"})
        assert result["errors"] == {CONF_HEIGHT: "not_a_number"}
        result = await submit(hass, result, {CONF_HEIGHT: "5"})
        assert result["errors"] == {CONF_HEIGHT: "out_of_range"}


async def test_a_tape_reading_above_the_travel_is_sent_back_to_the_form(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A bar above the whole travel is a tape read from the floor, not from the rest."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:15])
        result = await submit(hass, result, {"measured_cm": str(HEIGHT + 10)})
        assert result["step_id"] == "measure_descent"
        assert result["errors"] == {"measured_cm": "above_the_travel"}
        result = await submit(hass, result, {"measured_cm": str(descent_cm(0.5))})
        assert result["step_id"] == "tape_result"


async def test_the_height_defaults_to_what_is_known_and_otherwise_to_two_hundred(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A pre-filled 198 looks like a measurement somebody already made.

    So the field opens on the height this window is already said to have - and on a
    round 200 when nobody has ever said.

    Mutation caught: pre-filling the file's height on a cover that has none (there is
    nothing to pre-fill), or dropping the known height and always offering 200.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:10])
        assert _suggested(result, CONF_HEIGHT) == "195"

    async with calibrating(hass, tmp_path, TWO_COVERS_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, "2-82"))
        acts = (
            *ENTER,
            Act(payload={"cover": SECOND_UNIQUE_ID}),
            *PATH_A_BASIC[3:10],
        )
        result = await drive(hass, freezer, await open_dialog(hass, entry), acts)
        assert result["step_id"] == "height"
        assert _suggested(result, CONF_HEIGHT) == "200"


def _suggested(result: dict[str, Any], key: str) -> Any:
    for marker in result["data_schema"].schema:
        if marker == key:
            return marker.description["suggested_value"]
    raise AssertionError(f"{key} is not in this form")


# --------------------------------------------------------------------------------------
# When something goes wrong
# --------------------------------------------------------------------------------------
async def test_a_shutter_that_does_not_answer_gets_its_own_screen(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Each failure needs something different done about it, so each has a text."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:4])
        runner.fail = CalibrationError(REASON_NO_ECHO)
        result = await choose(hass, result, "begin")
        assert result["step_id"] == "problem_no_echo"
        assert result["menu_options"] == ["repeat_step", "cancel_flow"]
        # ...and "Ripeti questo passo" really does run the step again.
        result = await choose(hass, result, "repeat_step")
        assert result["step_id"] == "home_closed_done"


@pytest.mark.parametrize(
    "reason", [REASON_NO_ECHO, REASON_NOT_DELIVERED, REASON_NOT_STOPPED, REASON_BUSY]
)
async def test_every_failure_reason_reaches_a_screen_written_for_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, reason: str
) -> None:
    """A reason with no screen would raise `UnknownStep` just after a shutter misbehaved."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:4])
        runner.fail = CalibrationError(reason)
        result = await choose(hass, result, "begin")
        assert result["step_id"] == f"problem_{reason}"


async def test_a_failure_the_engine_does_not_name_still_ends_on_a_screen(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A reason a later release grows lands on `problem_unknown`, not on a broken dialog."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:4])
        runner.fail = CalibrationError("something_new")
        result = await choose(hass, result, "begin")
        assert result["step_id"] == "problem_unknown"


async def test_a_press_that_never_came_is_not_believed(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Past a minute and a half the press measures nothing, so it is discarded."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:7])
        assert result["step_id"] == "open_lift"
        freezer.tick(timedelta(seconds=PRESS_TIMEOUT_SEC + 1))
        result = await choose(hass, result, "lifted_off")
        assert result["step_id"] == "problem_timeout"


async def test_presses_in_an_impossible_order_are_refused(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A shutter cannot have stopped before it started."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:6])
        # The motor "started" a minute in the future.
        async def _late(direction: str):
            return dt_util.utcnow() + timedelta(seconds=60)

        cover.async_calib_start = _late
        result = await choose(hass, result, "open_start")
        result = await choose(hass, result, "lifted_off")
        result = await choose(hass, result, "stopped_open")
        assert result["step_id"] == "problem_bad_point"


async def test_it_did_not_do_what_it_should_stops_the_shutter_first(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Something is moving that should not be, and the step's homing would queue behind it."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:5])
        assert result["step_id"] == "home_closed_done"
        assert runner.stops == 0
        result = await choose(hass, result, "not_right")
        assert result["step_id"] == "home_closed_done"
        assert runner.stops == 1


async def test_a_stop_that_is_refused_does_not_stop_the_conversation(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The stop of "Non ha fatto quello che doveva" is best effort, and says so."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:5])
        runner.fail = CalibrationError(REASON_NOT_STOPPED)
        runner.fail_on = "stop"
        result = await choose(hass, result, "not_right")
        assert result["step_id"] == "home_closed_done"


# --------------------------------------------------------------------------------------
# Path B - another window of the same kind
# --------------------------------------------------------------------------------------
PATH_B: tuple[Act, ...] = (
    *ENTER,
    Act(payload={"cover": UNIQUE_ID}),
    Act(option="path_b"),
    Act(payload={CONF_PROFILE: "tall"}),
    Act(option="confirm_open"),
    Act(payload={CONF_HEIGHT: str(HEIGHT)}),
    Act(option="accept_step"),
    Act(option="skip_verify"),
    Act(option="save"),
)


async def test_path_b_reaches_a_shutter_whose_file_carries_its_own_run_times(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Two screens for the second window of a kind - and they have to *do* something.

    The file here says 30 / 29 / 6 s and a roll of 1.2, which is how every basic cover
    in the owner's own `myhome.yaml` is written, and a profile does not beat a key
    written in the file (spec 1.3). Storing the profile's name alone therefore left the
    shutter exactly where it was while the summary promised the opposite - the review's
    BUG-1, and the headline of the release. So the record says that *this window*
    follows that profile (`profile_wins`), which is the one thing that puts the
    profile's values above the run times the file writes for this cover.

    Mutation caught: writing a bare `{profile, height}` without the flag (the entity
    keeps the file's 30 / 29 / 6); baking the numbers into the record instead, which is
    what went stale; stamping the record `guided`, which would make `Calibration
    source` claim this window was measured when only its height was.
    """
    async with calibrating(hass, tmp_path, PROFILE_AND_OWN_NUMBERS_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_B)
        assert result["step_id"] == "saved"
        calibration = the_calibration(hass, entry)
        assert calibration[CONF_PROFILE] == "tall"
        assert calibration[CONF_PROFILE_WINS] is True
        assert calibration[CONF_HEIGHT] == HEIGHT
        # Nothing of the profile is copied: what it comes to is worked out on every
        # read, so a correction of the profile can never miss this window.
        assert "overrides" not in calibration
        # One homing, no timed run, no fractional run: the height is the measurement.
        assert runner.started == []
        assert runner.runs == []

        # ...and the shutter really runs on them once the dialog is closed.
        result = await choose(hass, result, "init")
        result = await choose(hass, result, "finish")
        await hass.async_block_till_done()
        await set_connected(hass, True)
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == pytest.approx(OPENING, abs=0.05)
        assert state.attributes["Closing time"] == pytest.approx(CLOSING, abs=0.05)
        assert state.attributes["Slat time"] == pytest.approx(SLAT, abs=0.05)
        # It was not measured here, it was inherited: the source goes on naming the
        # profile rather than claiming a guided calibration of this window.
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "profile tall"


async def test_the_snippet_of_path_b_carries_the_numbers_the_two_lines_come_to(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The snippet is offered as an alternative to saving, so it has to be one.

    `profile:` + `height:` alone would change nothing at all on a file that carries its
    own run times, which is the same BUG-1 written into the user's configuration.
    """
    async with calibrating(hass, tmp_path, PROFILE_AND_OWN_NUMBERS_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_B[:-1])
        snippet = result["description_placeholders"]["yaml"]
        assert f"    {CONF_PROFILE}: tall" in snippet
        assert f"    {CONF_HEIGHT}: {HEIGHT}" in snippet
        assert f"    {CONF_OPENING_TIME}: " in snippet
        assert f"    {CONF_CLOSING_ROLL}: " in snippet


async def test_path_b_offers_the_refinement_when_the_check_is_far_out(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Over three centimetres the profile is not describing this window."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_B[:-2])
        result = await choose(hass, result, "verify_now")
        assert result["step_id"] == "home_open_done"
        result = await choose(hass, result, "confirm_open")
        assert result["step_id"] == "measure_verify"
        result = await submit(hass, result, {"measured_cm": str(descent_cm(0.5) - 8.0)})
        assert result["step_id"] == "verify_result"
        assert "path_c" in result["menu_options"]
        # And taking the offer keeps the height that was just measured.
        result = await choose(hass, result, "path_c")
        assert result["step_id"] == "path_c"
        assert _suggested_default(result, CONF_PROFILE) == "tall"


def _choices(result: dict[str, Any], key: str) -> list[str]:
    """The options one `vol.In` field of a form really offers."""
    for marker, validator in result["data_schema"].schema.items():
        if marker == key:
            return list(getattr(validator, "container", ()))
    raise AssertionError(f"{key} is not in this form")


def _suggested_default(result: dict[str, Any], key: str) -> Any:
    for marker in result["data_schema"].schema:
        if marker == key:
            return marker.default()
    raise AssertionError(f"{key} is not in this form")


async def test_a_check_that_lands_close_enough_just_carries_on(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """One or two centimetres are normal and already a very good approximation."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_B[:-2])
        result = await choose(hass, result, "verify_now")
        result = await choose(hass, result, "confirm_open")
        result = await submit(hass, result, {"measured_cm": str(descent_cm(0.5) - 1.0)})
        assert result["menu_options"] == ["accept_step", "repeat_tape"]
        result = await choose(hass, result, "accept_step")
        # Path B has nothing of its own to improve: the numbers are the profile's, so
        # it gets the summary that does not describe the refinement (review BUG-5).
        assert result["step_id"] == "summary_short"
        assert result["menu_options"] == ["save", "cancel_flow"]


async def test_the_paths_that_need_a_profile_are_not_offered_without_one(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """B and C follow a profile, so they only exist once there is one."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:3])
        assert result["menu_options"] == ["path_a", "cancel_flow"]


# --------------------------------------------------------------------------------------
# Path C - this one window
# --------------------------------------------------------------------------------------
PATH_C_TIMES: tuple[Act, ...] = (
    *ENTER,
    Act(payload={"cover": UNIQUE_ID}),
    Act(option="path_c"),
    Act(payload={CONF_PROFILE: "tall"}),
    Act(option="times_only"),
    Act(option="confirm_closed"),
    Act(option="open_start"),
    Act(option="lifted_off", tick=SLAT),
    Act(option="stopped_open", tick=CURTAIN_UP),
    Act(option="accept_step"),
    Act(option="close_start"),
    Act(option="stopped_closed", tick=CLOSING),
    Act(option="accept_step"),
    Act(option="save"),
)


async def test_path_c_times_only_stores_the_two_run_times_as_overrides(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """This motor is slower than the profile's, and nothing else about it differs.

    Mutation caught: storing a profile as well (the kind of shutter was not measured
    here, one window of it was).
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES)
        assert result["step_id"] == "saved"
        assert the_store(hass, entry).raw_profiles == {}
        calibration = the_calibration(hass, entry)
        assert calibration[CONF_PROFILE] == "tall"
        assert calibration["overrides"] == {
            CONF_OPENING_TIME: pytest.approx(OPENING, abs=0.05),
            CONF_CLOSING_TIME: pytest.approx(CLOSING, abs=0.05),
            CONF_SLAT_TIME: pytest.approx(SLAT, abs=0.05),
        }


async def test_path_c_with_the_coefficients_measures_and_overrides_them_too(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The curtain winds differently as well, so the rolls are this window's own."""
    acts = (
        *PATH_C_TIMES[:5],
        Act(option="times_and_rolls"),
        *PATH_A_BASIC[5:-2],
        Act(option="save"),
    )
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), acts)
        assert result["step_id"] == "saved"
        overrides = the_calibration(hass, entry)["overrides"]
        assert overrides[CONF_CLOSING_ROLL] == pytest.approx(ROLL_DOWN, abs=0.01)
        assert overrides[CONF_OPENING_ROLL] == pytest.approx(ROLL_UP, abs=0.01)
        assert the_store(hass, entry).raw_profiles == {}


async def test_the_refinement_summary_shows_the_cover_s_own_yaml(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Path C writes keys on the cover, not a `cover_profiles:` block."""
    async with calibrating(hass, tmp_path, PROFILE_AND_OWN_NUMBERS_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES[:-1])
        assert result["step_id"] == "summary_short"
        snippet = result["description_placeholders"]["yaml"]
        assert "cover_profiles:" not in snippet
        assert f"  {YAML_KEY}:" in snippet


async def test_path_c_starts_from_the_profile_the_cover_already_follows(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The user came here because *this* profile is wrong for *this* window."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        store = the_store(hass, entry)
        await store.async_set_assignments({UNIQUE_ID: ("tall", HEIGHT)})
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES[:4])
        assert result["step_id"] == "path_c"
        assert _suggested_default(result, CONF_PROFILE) == "tall"


async def test_the_summary_of_a_times_only_refinement_says_nothing_it_did_not_measure(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """No tape was read, so there is no accuracy to report.

    The travel is a different matter: it is not measured here either, but it is already
    known - the file writes it - and the conversation starts from what is known rather
    than from nothing, so that Save does not write a record that has forgotten it
    (final review, BUG-A).
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES[:-1])
        placeholders = result["description_placeholders"]
        assert placeholders["accuracy"] == "\u2013"
        assert placeholders["height"] == f"{HEIGHT:.0f} cm"
        # ...and the same screen on a window nobody has ever measured says so.
        assert placeholders["keeping"].endswith(CONF_HEIGHT)


async def test_a_refinement_of_a_window_nobody_measured_reports_no_travel(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Nothing knows this window's travel, so the summary says so rather than inventing one."""
    async with calibrating(hass, tmp_path, NO_HEIGHT_PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES[:-1])
        assert result["description_placeholders"]["height"] == "\u2013"


async def test_paths_b_and_c_begin_at_an_end_stop_the_user_has_confirmed(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The homing's wait is bounded by a model that is, in path C, wrong by hypothesis.

    Mutation caught: dropping the homing stage from either plan, which lets the first
    measured run start from a shutter that is still travelling.
    """
    assert PLAN_PROFILE[0] == "home_open"
    assert PLAN_TIMES[0] == "home_closed"
    assert PLAN_TIMES_AND_ROLLS[0] == "home_closed"
    assert PLAN_VERIFY_B == ("home_open", "verify_b")
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES[:6])
        assert result["step_id"] == "home_closed_done"
        assert runner.homed == [DIRECTION_CLOSE]


# --------------------------------------------------------------------------------------
# What a second conversation on the same window is allowed to forget (final review BUG-A)
# --------------------------------------------------------------------------------------
async def test_refining_a_window_keeps_the_height_and_the_rolls_it_did_not_measure(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Affina la calibrazione" makes the model better, or it is not a refinement.

    A window measured once - whose travel the guided flow is the only thing that knows,
    because the file writes no `height:` for it - is refined on its two run times
    alone. Writing the record whole threw the travel and both roll coefficients away:
    the shutter fell back to the file's `roll: 1.2` and to no height at all, and the
    position model came out of the refinement *worse* than it went in, on the one
    screen whose whole promise is the opposite (final review, BUG-A).

    Mutation caught: building the record from this conversation alone (`overrides=` and
    `height=` straight off `_Measured`), which is what it used to do.
    """
    async with calibrating(hass, tmp_path, NO_HEIGHT_PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        store = the_store(hass, entry)
        await store.async_set_calibration(
            UNIQUE_ID,
            calibration_store.cover_calibration_data(
                UNIQUE_ID,
                height=HEIGHT,
                overrides={
                    CONF_OPENING_TIME: 27.0,
                    CONF_CLOSING_TIME: 26.0,
                    CONF_SLAT_TIME: 4.7,
                    CONF_OPENING_ROLL: ROLL_UP,
                    CONF_CLOSING_ROLL: ROLL_DOWN,
                },
            ),
        )

        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES)
        assert result["step_id"] == "saved"

        record = the_store(hass, entry).calibration(UNIQUE_ID)
        # The two run times and the slat phase are this conversation's...
        assert record.overrides[CONF_OPENING_TIME] == pytest.approx(OPENING, abs=0.05)
        assert record.overrides[CONF_CLOSING_TIME] == pytest.approx(CLOSING, abs=0.05)
        # ...and everything it had no opinion about is exactly as it was.
        assert record.overrides[CONF_OPENING_ROLL] == ROLL_UP
        assert record.overrides[CONF_CLOSING_ROLL] == ROLL_DOWN
        assert record.height == HEIGHT

        # ...which is what the shutter really runs on once the dialog is closed.
        result = await choose(hass, result, "init")
        await choose(hass, result, "finish")
        await hass.async_block_till_done()
        await set_connected(hass, True)
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening roll"] == ROLL_UP
        assert state.attributes["Closing roll"] == ROLL_DOWN
        assert state.attributes["Height"] == HEIGHT


async def test_the_short_summary_says_what_it_replaces_and_what_it_leaves_alone(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The screen before Save names both lists, by the keys the record is shown under.

    "Nothing is written before Save" is only worth something if the screen that asks
    says what Save will do. A dash under "Corsa del telo" is not a way of saying "the
    195 cm you measured last month is about to be deleted" (final review, BUG-A).

    Mutation caught: reporting the whole record as replaced, or the summary computing
    its two lists from something other than what Save writes.
    """
    async with calibrating(hass, tmp_path, NO_HEIGHT_PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        await the_store(hass, entry).async_set_calibration(
            UNIQUE_ID,
            calibration_store.cover_calibration_data(
                UNIQUE_ID,
                height=HEIGHT,
                overrides={CONF_OPENING_TIME: 27.0, CONF_CLOSING_ROLL: ROLL_DOWN},
            ),
        )
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES[:-1])
        assert result["step_id"] == "summary_short"
        placeholders = result["description_placeholders"]
        replacing = placeholders["replacing"].split(", ")
        keeping = placeholders["keeping"].split(", ")
        assert set(replacing) == {CONF_OPENING_TIME, CONF_CLOSING_TIME, CONF_SLAT_TIME}
        assert set(keeping) == {CONF_CLOSING_ROLL, CONF_HEIGHT}


async def test_measuring_a_window_again_starts_from_the_travel_it_is_known_to_have(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Misura di nuovo" is a way into the same three paths, not a way to forget.

    It reset the conversation and claimed the cover, and path C then measured two run
    times against a travel of `None` (final review, BUG-A).

    Mutation caught: not seeding the height on this entrance, after which the refinement
    of a re-measured window loses it.
    """
    async with calibrating(hass, tmp_path, NO_HEIGHT_PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        await the_store(hass, entry).async_set_calibration(
            UNIQUE_ID,
            calibration_store.cover_calibration_data(
                UNIQUE_ID, height=HEIGHT, overrides={CONF_OPENING_TIME: 27.0}
            ),
        )
        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "calibration_remeasure")
        assert result["step_id"] == "path"

        result = await drive(hass, freezer, result, PATH_C_TIMES[3:-1])
        assert result["step_id"] == "summary_short"
        # The screen before Save says what it is scaling by and what it will keep...
        assert result["description_placeholders"]["height"] == f"{HEIGHT:.0f} cm"
        assert CONF_HEIGHT in result["description_placeholders"]["keeping"]
        result = await choose(hass, result, "save")
        assert result["step_id"] == "saved"
        # ...and the record still has it.
        assert the_store(hass, entry).calibration(UNIQUE_ID).height == HEIGHT


async def test_a_refinement_never_copies_the_file_s_height_into_the_record(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The travel it starts from may be the file's, and the file's stays the file's.

    Seeding the conversation with what is known is not the same as claiming it: a copy
    of the file's `height:` stored here would shadow the very line it was read from,
    for ever and silently - which is the half of BUG-2 the assignment form was fixed
    for, and the staleness RISK-A is about.

    Mutation caught: writing `self._measured.height` whatever its provenance.
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_C_TIMES)
        assert result["step_id"] == "saved"
        record = the_store(hass, entry).calibration(UNIQUE_ID)
        assert record.height is None
        # ...and the cover still has one, because the file says so.
        result = await choose(hass, result, "init")
        await choose(hass, result, "finish")
        await hass.async_block_till_done()
        await set_connected(hass, True)
        assert hass.states.get(ENTITY).attributes["Height"] == HEIGHT



# --------------------------------------------------------------------------------------
# What the save is worth
# --------------------------------------------------------------------------------------
async def test_saving_reaches_the_shutter_when_the_dialog_closes(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A calibration the user does not see take effect is one they do not believe in.

    The file here says 30 / 29 / 6 s and a roll of 1.2 - which is how every basic cover
    in the owner's own `myhome.yaml` is configured, and which the fake shutter is not -
    so the numbers on the entity can only be the measured ones.

    Mutation caught: storing the profile alone (a profile does not beat the file, so
    three minutes of measuring would change nothing but an attribute: review BUG-1).
    """
    async with calibrating(hass, tmp_path, OWN_NUMBERS_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC)
        assert result["step_id"] == "saved"
        assert result["description_placeholders"]["profile"] == "tall"
        # The reload happens when the dialog closes, once.
        result = await choose(hass, result, "init")
        result = await choose(hass, result, "finish")
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        await set_connected(hass, True)

        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == pytest.approx(OPENING, abs=0.05)
        assert state.attributes["Closing time"] == pytest.approx(CLOSING, abs=0.05)
        assert state.attributes["Slat time"] == pytest.approx(SLAT, abs=0.05)
        assert state.attributes["Opening roll"] == pytest.approx(ROLL_UP, abs=0.01)
        assert state.attributes["Closing roll"] == pytest.approx(ROLL_DOWN, abs=0.01)
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "guided"


async def test_the_gateway_is_reloaded_once_and_only_when_something_changed(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Two writes, one Save, one reload - and none at all for a dialog that only looked.

    A reload on a real gateway is a disconnect and a reconnect, very likely while the
    shutter is still moving from the last measurement.

    Mutation caught: reloading inside the store's own writes (path A writes twice).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        with patch.object(hass.config_entries, "async_schedule_reload") as reload:
            result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC)
            assert reload.call_count == 0
            result = await choose(hass, result, "init")
            result = await choose(hass, result, "finish")
            # Not synchronously: the reload waits for the `finally` of a movement that
            # was cut short to write its stop (review RISK-4).
            assert reload.call_count == 0
            await hass.async_block_till_done()
        assert reload.call_count == 1


async def test_the_yaml_snippet_uses_the_key_the_file_knows_the_cover_by(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The snippet is offered to be pasted, so it has to paste into something."""
    async with calibrating(hass, tmp_path, OWN_NUMBERS_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:-1])
        snippet = result["description_placeholders"]["yaml"]
        assert f"    {CONF_PROFILE}: tall" in snippet
        assert "hallway_shutter" not in snippet


# --------------------------------------------------------------------------------------
# Choosing the cover
# --------------------------------------------------------------------------------------
async def test_only_the_basic_covers_are_offered(hass: HomeAssistant, tmp_path) -> None:
    """An advanced cover reports its own position and every primitive refuses it."""
    async with calibrating(hass, tmp_path, MIXED_YAML) as (entry, _commands):
        result = await choose(hass, await open_dialog(hass, entry), "calibrate")
        result = await choose(hass, result, "cover")
        assert result["step_id"] == "cover"
        assert result["data_schema"].schema["cover"].container == {UNIQUE_ID: COVER_NAME}


async def test_a_cover_without_an_entity_yet_is_refused_rather_than_driven(
    hass: HomeAssistant, tmp_path
) -> None:
    """A configured cover whose platform never built an entity has nothing to drive."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        from custom_components.myhome.const import CONF_ENTITIES, CONF_PLATFORMS, DOMAIN

        hass.data[DOMAIN][MAC][CONF_PLATFORMS][COVER][DEVICE_KEY][CONF_ENTITIES] = {}
        result = await choose(hass, await open_dialog(hass, entry), "calibrate")
        result = await choose(hass, result, "cover")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        assert result["step_id"] == "refused_unknown_cover"
        assert result["menu_options"] == ["calibrate", "init"]


async def test_a_second_dialog_on_the_same_shutter_is_refused(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Two browser tabs on one shutter would each measure a run the other one stopped."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:5])

        second = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:3])
        assert second["step_id"] == "refused_already_calibrating"


async def test_the_old_service_and_the_dialog_do_not_share_a_shutter(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The 0.4.2 service refuses a cover a dialog is holding, and the other way round."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:5])
        assert cover.calibrating is True
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                COVER,
                "set_cover_position",
                {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40},
                blocking=True,
            )


async def test_the_shutter_is_marked_calibrating_for_the_whole_conversation(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """One session, held from the claim to the close, so the attribute does not blink."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await open_dialog(hass, entry)
        for act in PATH_A_BASIC[:8]:
            if act.tick:
                freezer.tick(timedelta(seconds=act.tick))
            result = (
                await choose(hass, result, act.option)
                if act.option is not None
                else await submit(hass, result, act.payload)
            )
            if act is not PATH_A_BASIC[0] and act is not PATH_A_BASIC[1]:
                assert cover.calibrating is True

        manager = hass.config_entries.options
        for flow in list(manager.async_progress()):
            manager.async_abort(flow["flow_id"])
        assert cover.calibrating is False
        assert ATTR_CALIBRATING not in hass.states.get(ENTITY).attributes


# --------------------------------------------------------------------------------------
# The watchdog, and the screen it leads to
# --------------------------------------------------------------------------------------
async def test_a_dialog_nobody_closed_gives_the_shutter_back_by_itself(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A browser tab that is simply closed used to hold the cover until the next restart.

    Home Assistant never expires a flow of its own accord, and a closed tab, a sleeping
    laptop or a phone that kills the tab tell nobody. The flow object then lived on
    holding the calibration session, so `Calibrating` stayed true and every
    `set_cover_position` on that shutter was refused.

    Mutation caught: dropping the watchdog.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:7])
        assert result["step_id"] == "open_lift"
        assert cover.calibrating is True

        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC + 1)
        )
        await hass.async_block_till_done()

        assert cover.calibrating is False
        assert ATTR_CALIBRATING not in hass.states.get(ENTITY).attributes
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
        )


async def test_an_expired_session_shows_a_screen_instead_of_an_invalid_flow(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The live walk-through's bug: Home Assistant answered "Invalid flow specified".

    The flow is never aborted server-side any more. The session is released, and the
    next thing the user does lands on a screen that says what happened and offers to
    start again.

    Mutation caught: aborting the flow on expiry (the dialog dies under the user's
    hands), or letting the expired conversation carry on measuring.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:7])
        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC + 1)
        )
        await hass.async_block_till_done()
        # The flow is still there, and answers.
        assert hass.config_entries.options.async_progress() != []
        result = await choose(hass, result, "lifted_off")
        assert result["step_id"] == "expired"
        assert result["menu_options"] == ["calibrate", "init"]
        assert the_store(hass, entry).raw_covers == {}
        # "Ricomincia" is a clean start, not a resumption.
        result = await choose(hass, result, "calibrate")
        assert result["step_id"] == "calibrate"


async def test_a_screen_with_nothing_moving_is_given_half_an_hour(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The first live walk-through lost its session while the user read the intro.

    Ten minutes is right for somebody standing in front of a shutter with a tape; it is
    not right for somebody reading three paragraphs and thinking about them.

    Mutation caught: one timer for both kinds of screen.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:4])
        assert result["step_id"] == "path_a"

        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC + 60)
        )
        await hass.async_block_till_done()
        assert cover.calibrating is True

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=IDLE_TIMEOUT_SEC + 1))
        await hass.async_block_till_done()
        assert cover.calibrating is False


async def test_every_screen_puts_the_watchdog_off_again(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Inactivity, not conversation.

    Mutation caught: arming the watchdog once, at the claim, so that a careful user
    measuring a tall window loses the shutter half way through.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:5])

        for _ in range(3):
            async_fire_time_changed(
                hass, dt_util.utcnow() + timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC * 2 / 3)
            )
            await hass.async_block_till_done()
            result = await choose(hass, result, "repeat_step")
            assert result["step_id"] == "home_closed_done"

        assert cover.calibrating is True


async def test_the_watchdog_stops_a_shutter_it_finds_still_running(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Releasing the session is not enough if the motor is still turning."""
    async with calibrating(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        runner = FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:7])
        assert result["step_id"] == "open_lift"
        cover._moving = "opening"  # noqa: SLF001 - the shutter is still travelling
        assert cover.is_opening is True

        async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC + 1)
        )
        await hass.async_block_till_done()
        assert runner.stops >= 1


# --------------------------------------------------------------------------------------
# "Profili e tapparelle"
# --------------------------------------------------------------------------------------
async def measured_profile(hass: HomeAssistant, entry, freezer) -> None:
    """Walk path A once, so the management screens have something to manage."""
    FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
    result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC)
    result = await choose(hass, result, "init")
    await choose(hass, result, "finish")
    await hass.async_block_till_done()
    await set_connected(hass, True)


async def test_the_assignment_form_has_one_row_per_shutter(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A select per cover, named after the cover, offering "Nessun profilo" first.

    The field names are the shutters' own names because Home Assistant shows the key
    when it finds no translation for it, and a key that only exists on one installation
    cannot be translated.

    Mutation caught: keying the form by the unique id, which is a MAC address and a bus
    address and means nothing to anybody.
    """
    async with calibrating(hass, tmp_path, TWO_COVERS_YAML) as (entry, _commands):
        store = the_store(hass, entry)
        await store.async_set_profile(
            "tall",
            calibration_store.cover_profile_data(
                "tall",
                reference_height=HEIGHT,
                opening_time=OPENING,
                closing_time=CLOSING,
                slat_time=SLAT,
                opening_roll=ROLL_UP,
                closing_roll=ROLL_DOWN,
            ),
        )
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        assert result["menu_options"] == ["assign_covers", "pick_profile", "init"]
        result = await choose(hass, result, "assign_covers")
        assert result["step_id"] == "assign_covers"
        fields = [str(marker) for marker in result["data_schema"].schema]
        assert fields == [COVER_NAME, "Landing Shutter"]
        options = result["data_schema"].schema[COVER_NAME].config["options"]
        assert options == [NO_PROFILE, "tall"]


async def test_assigning_a_profile_asks_for_the_height_it_does_not_know(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A profile is scaled by the ratio of two heights, so one of them has to exist.

    Mutation caught: storing the assignment without the height, which applies the
    profile as if every window were the one it was measured on.
    """
    async with calibrating(hass, tmp_path, TWO_COVERS_YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "assign_covers")
        result = await submit(
            hass, result, {COVER_NAME: "tall", "Landing Shutter": "tall"}
        )
        assert result["step_id"] == "assign_heights"
        assert [str(marker) for marker in result["data_schema"].schema] == ["Landing Shutter"]
        # A number it cannot read is refused on the row it belongs to.
        result = await submit(hass, result, {"Landing Shutter": "?"})
        assert result["errors"] == {"Landing Shutter": "not_a_number"}
        result = await submit(hass, result, {"Landing Shutter": "150,5"})
        assert result["step_id"] == "profiles_covers"

        store = the_store(hass, entry)
        assert store.calibration(SECOND_UNIQUE_ID).profile == "tall"
        assert store.calibration(SECOND_UNIQUE_ID).height == 150.5
        assert store.covers_following("tall") == sorted([UNIQUE_ID, SECOND_UNIQUE_ID])


async def test_no_profile_gives_a_shutter_back_to_the_file(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The first option of every select, and what it undoes."""
    async with calibrating(hass, tmp_path, TWO_COVERS_YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "assign_covers")
        result = await submit(
            hass, result, {COVER_NAME: NO_PROFILE, "Landing Shutter": NO_PROFILE}
        )
        assert result["step_id"] == "profiles_covers"
        assert the_store(hass, entry).calibration(UNIQUE_ID).profile is None


async def test_a_profile_can_be_looked_at(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Vedi i valori": the numbers, and who follows them."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "pick_profile")
        assert result["step_id"] == "pick_profile"
        result = await submit(hass, result, {CONF_PROFILE: "tall"})
        assert result["step_id"] == "profile_actions"
        assert result["description_placeholders"]["count"] == "1"
        result = await choose(hass, result, "profile_view")
        assert result["step_id"] == "profile_view"
        assert "opening_time" in result["description_placeholders"]["values"]
        assert result["description_placeholders"]["covers"] == COVER_NAME
        # ...and it comes back to the menu it came from.
        assert (await submit(hass, result))["step_id"] == "profile_actions"


async def test_a_profile_can_be_edited_by_hand(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The user who has the manufacturer's run times, or who saw the fit land half a
    second out, can say so without measuring again.

    Mutation caught: writing the values without validating them, which puts a roll of
    0.1 into the travel model and a shutter that stops nowhere near where it should.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "pick_profile")
        result = await submit(hass, result, {CONF_PROFILE: "tall"})
        result = await choose(hass, result, "profile_edit")
        assert result["step_id"] == "profile_edit"

        good = {
            CONF_REFERENCE_HEIGHT: "195",
            CONF_OPENING_TIME: "22,5",
            CONF_CLOSING_TIME: "21.5",
            CONF_SLAT_TIME: "4.5",
            CONF_OPENING_ROLL: "2.1",
            CONF_CLOSING_ROLL: "1.7",
        }
        result = await submit(hass, result, {**good, CONF_OPENING_ROLL: "0.2"})
        assert result["errors"] == {CONF_OPENING_ROLL: "out_of_range"}
        result = await submit(hass, result, {**good, CONF_CLOSING_TIME: "soon"})
        assert result["errors"] == {CONF_CLOSING_TIME: "not_a_number"}
        result = await submit(hass, result, good)
        assert result["step_id"] == "profile_actions"

        profile = the_store(hass, entry).profiles["tall"]
        assert profile[CONF_OPENING_TIME] == 22.5
        assert profile[CONF_CLOSING_TIME] == 21.5
        assert profile[CONF_OPENING_ROLL] == 2.1


async def test_deleting_a_profile_names_the_shutters_it_will_affect(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The confirmation is the only place the user finds out before the shutters do.

    Mutation caught: deleting without asking, or asking without naming the covers.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "pick_profile")
        result = await submit(hass, result, {CONF_PROFILE: "tall"})
        result = await choose(hass, result, "profile_delete")
        assert result["step_id"] == "profile_delete"
        assert result["description_placeholders"]["covers"] == COVER_NAME
        assert result["description_placeholders"]["count"] == "1"

        # "No, torna indietro" really does leave it alone.
        result = await choose(hass, result, "profile_actions")
        assert "tall" in the_store(hass, entry).raw_profiles

        result = await choose(hass, result, "profile_delete")
        result = await choose(hass, result, "profile_delete_confirm")
        assert result["step_id"] == "profile_deleted"
        assert result["description_placeholders"]["covers"] == COVER_NAME
        assert the_store(hass, entry).raw_profiles == {}
        assert the_store(hass, entry).calibration(UNIQUE_ID).profile is None
        assert (await submit(hass, result))["step_id"] == "profiles_covers"


async def test_a_profile_written_in_the_file_is_shown_and_left_alone(
    hass: HomeAssistant, tmp_path
) -> None:
    """The file is the user's. The dialog shows what is in it and offers nothing else.

    Mutation caught: offering "Modifica" on a `cover_profiles:` entry, which would
    silently create a stored profile that shadows the file's from then on.
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "pick_profile")
        result = await submit(hass, result, {CONF_PROFILE: "tall"})
        assert result["menu_options"] == ["profile_view", "profiles_covers"]


# --------------------------------------------------------------------------------------
# "Calibrazioni"
# --------------------------------------------------------------------------------------
async def test_the_calibrations_screen_says_so_when_there_is_nothing(
    hass: HomeAssistant, tmp_path
) -> None:
    """An empty select is not an explanation."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        assert result["step_id"] == "no_calibrations"
        assert result["menu_options"] == ["init"]
        assert (await choose(hass, result, "init"))["step_id"] == "init"


async def test_a_stored_calibration_can_be_looked_at_and_deleted(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Vedi" and "Elimina", with the confirmation between the two.

    Mutation caught: deleting straight from the action menu (a measurement thrown away
    by a mis-click cannot be got back by thinking).
    """
    async with calibrating(hass, tmp_path, OWN_NUMBERS_YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        assert hass.states.get(ENTITY).attributes["Opening time"] != FILE_OPENING

        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        assert result["step_id"] == "calibrations"
        assert result["data_schema"].schema["cover"].container == {UNIQUE_ID: COVER_NAME}
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        assert result["step_id"] == "calibration_actions"
        assert result["menu_options"] == [
            "calibration_view",
            "calibration_edit",
            "calibration_remeasure",
            "calibration_delete",
            "calibrations",
        ]
        result = await choose(hass, result, "calibration_view")
        assert "opening_time" in result["description_placeholders"]["values"]
        result = await submit(hass, result)

        result = await choose(hass, result, "calibration_delete")
        result = await choose(hass, result, "calibration_actions")
        assert the_store(hass, entry).calibration(UNIQUE_ID) is not None
        result = await choose(hass, result, "calibration_delete")
        result = await choose(hass, result, "calibration_delete_confirm")
        assert result["step_id"] == "calibration_deleted"
        assert the_store(hass, entry).calibration(UNIQUE_ID) is None
        # Nothing else is stored, so the list has nothing left to show.
        result = await submit(hass, result)
        assert result["step_id"] == "no_calibrations"

        result = await choose(hass, result, "init")
        result = await choose(hass, result, "finish")
        await hass.async_block_till_done()
        await set_connected(hass, True)
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == FILE_OPENING
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "yaml"


async def test_a_calibration_can_be_edited_by_hand(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """An override typed in, and an override taken back out by emptying its field.

    Mutation caught: reading an empty field as a zero, which would give the shutter a
    run time of nothing at all.
    """
    async with calibrating(hass, tmp_path, OWN_NUMBERS_YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "calibration_edit")
        assert result["step_id"] == "calibration_edit"

        result = await submit(hass, result, {CONF_HEIGHT: "twelve"})
        assert result["errors"] == {CONF_HEIGHT: "not_a_number"}
        result = await submit(hass, result, {CONF_HEIGHT: "190", CONF_OPENING_TIME: "900"})
        assert result["errors"] == {CONF_OPENING_TIME: "out_of_range"}
        result = await submit(
            hass, result, {CONF_HEIGHT: "190", CONF_OPENING_TIME: "24,5", CONF_SLAT_TIME: ""}
        )
        assert result["step_id"] == "calibration_actions"

        record = the_store(hass, entry).calibration(UNIQUE_ID)
        assert record.height == 190.0
        assert record.overrides == {CONF_OPENING_TIME: 24.5}
        assert record.profile == "tall"
        # The hand-edited record still beats the file, and the entity says so. The
        # reload happens however the dialog is left, the browser's X included.
        hass.config_entries.options.async_abort(result["flow_id"])
        await hass.async_block_till_done()
        await set_connected(hass, True)
        assert hass.states.get(ENTITY).attributes["Opening time"] == 24.5


async def test_measure_it_again_walks_straight_into_the_paths(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The cover comes from the row, so there is no selector to answer twice.

    Mutation caught: claiming the cover without releasing the previous conversation's
    session (the shutter would be held twice and freed once).
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "calibration_remeasure")
        assert result["step_id"] == "path"
        assert cover.calibrating is True

        result = await drive(hass, freezer, result, PATH_A_BASIC[3:])
        assert result["step_id"] == "saved"
        assert len(the_store(hass, entry).raw_covers) == 1


async def test_a_calibration_whose_cover_is_gone_cannot_be_re_measured(
    hass: HomeAssistant, tmp_path
) -> None:
    """A record for a cover the file no longer carries: a screen, not a traceback."""
    async with calibrating(
        hass,
        tmp_path,
        YAML,
        calibration={
            "profiles": {},
            "covers": {f"{MAC}-2-99": {"overrides": {CONF_SLAT_TIME: 4.7}, "source": "guided"}},
        },
    ) as (entry, _commands):
        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        result = await submit(hass, result, {"cover": f"{MAC}-2-99"})
        result = await choose(hass, result, "calibration_remeasure")
        assert result["step_id"] == "refused_unknown_cover"


# --------------------------------------------------------------------------------------
# Odds and ends
# --------------------------------------------------------------------------------------
def test_every_plan_names_a_step_the_flow_really_has() -> None:
    """A plan is a list of method names walked by `getattr`; a typo is an AttributeError.

    Mutation caught: renaming a stage and leaving a plan behind.
    """
    for plan in (PLAN_FULL, PLAN_PRECISE, PLAN_PROFILE, PLAN_TIMES, PLAN_TIMES_AND_ROLLS, PLAN_VERIFY_B):
        for stage in plan:
            assert hasattr(MyHomeOptionsFlowHandler, f"async_step_{stage}"), stage


async def test_a_verification_whose_profile_vanished_reports_no_gap(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one way a check can end up with nothing to check against."""
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_B[:-2])
        result = await choose(hass, result, "verify_now")
        result = await choose(hass, result, "confirm_open")
        # The file is re-read on a reload; here the flow's own profile is simply gone.
        from custom_components.myhome.const import CONF_COVER_PROFILES, DOMAIN

        hass.data[DOMAIN][MAC][CONF_COVER_PROFILES] = {}
        result = await submit(hass, result, {"measured_cm": str(descent_cm(0.5))})
        assert result["step_id"] == "verify_result"
        assert result["description_placeholders"]["deviation"] == "0.0"


@pytest.mark.parametrize(("reading", "offered"), [(3.04, False), (3.1, True)])
async def test_the_deviation_shown_is_the_deviation_compared(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, reading: float, offered: bool
) -> None:
    """"3.0 cm" never offers the refinement and "3.1 cm" always does.

    Mutation caught: comparing the unrounded value, which showed "3 cm" both with and
    without the refinement on offer, on a digit the user cannot see.
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_B[:-2])
        result = await choose(hass, result, "verify_now")
        result = await choose(hass, result, "confirm_open")
        result = await submit(hass, result, {"measured_cm": str(descent_cm(0.5) - reading)})
        assert result["description_placeholders"]["deviation"] == ("3.1" if offered else "3.0")
        assert ("path_c" in result["menu_options"]) is offered


async def test_the_second_press_is_timed_too_and_can_be_impossible(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Both presses of the ascent are checked, not only the first.

    Mutation caught: checking the window on `lifted_off` alone, which lets a press made
    an hour later become the opening time.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:8])
        assert result["step_id"] == "open_top"
        freezer.tick(timedelta(seconds=PRESS_TIMEOUT_SEC + 1))
        result = await choose(hass, result, "stopped_open")
        assert result["step_id"] == "problem_timeout"


async def test_the_closing_press_is_timed_and_checked_like_the_opening_ones(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one press of the descent gets the same two guards."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:13])
        assert result["step_id"] == "close_bottom"
        freezer.tick(timedelta(seconds=PRESS_TIMEOUT_SEC + 1))
        result = await choose(hass, result, "stopped_closed")
        assert result["step_id"] == "problem_timeout"

        async def _late(direction: str):
            return dt_util.utcnow() + timedelta(seconds=60)

        cover.async_calib_start = _late
        result = await choose(hass, result, "repeat_step")
        result = await choose(hass, result, "close_start")
        result = await choose(hass, result, "stopped_closed")
        assert result["step_id"] == "problem_bad_point"


async def test_an_ordinary_home_assistant_error_still_ends_on_a_screen(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Anything the engine raises that is not a `CalibrationError` is still a screen."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:4])

        async def _boom(direction: str, timeout: float | None = None) -> None:
            raise HomeAssistantError("the bus is on fire")

        cover.async_calib_home = _boom
        result = await choose(hass, result, "begin")
        assert result["step_id"] == "problem_unknown"


async def test_a_tape_reading_that_is_not_a_number_is_refused_on_every_form(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The descent, the ascent and the check all read the same field the same way."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:15])
        result = await submit(hass, result, {"measured_cm": "a bit less than a metre"})
        assert result["errors"] == {"measured_cm": "not_a_number"}
        result = await submit(hass, result, {"measured_cm": "-3"})
        assert result["errors"] == {"measured_cm": "out_of_range"}
        result = await submit(hass, result, {"measured_cm": str(descent_cm(0.5))})
        result = await choose(hass, result, "accept_step")

        assert result["step_id"] == "measure_ascent"
        result = await submit(hass, result, {"measured_cm": str(HEIGHT + 5)})
        assert result["errors"] == {"measured_cm": "above_the_travel"}
        result = await submit(hass, result, {"measured_cm": str(ascent_cm(0.5))})
        # ...and the ascent's reading can be taken again too.
        result = await choose(hass, result, "repeat_tape")
        assert result["step_id"] == "measure_ascent"
        result = await submit(hass, result, {"measured_cm": str(ascent_cm(0.5))})
        result = await choose(hass, result, "accept_step")
        result = await submit(hass, result, {CONF_NAME: "tall"})
        result = await choose(hass, result, "save")
        assert len(the_profile(hass, entry)[CONF_RAW]["ascent"]) == 1


async def test_the_check_of_the_precise_level_refuses_a_bad_reading_too(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The verification reads the same field, so it says the same things about it."""
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_PRECISE[:-3])
        assert result["step_id"] == "measure_verify"
        result = await submit(hass, result, {"measured_cm": "?"})
        assert result["errors"] == {"measured_cm": "not_a_number"}


async def test_the_assignment_form_says_so_when_there_is_no_basic_cover(
    hass: HomeAssistant, tmp_path
) -> None:
    """The section is still offered - there may be profiles to look at - but the form is not."""
    async with calibrating(hass, tmp_path, ADVANCED_ONLY_YAML) as (entry, _commands):
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        assert result["menu_options"] == ["assign_covers", "init"]
        result = await choose(hass, result, "assign_covers")
        assert result["step_id"] == "no_basic_covers"
        assert (await choose(hass, result, "init"))["step_id"] == "init"


async def test_a_height_outside_the_range_is_refused_on_both_forms(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A window is at most a few metres of curtain, on the assignment form as anywhere."""
    async with calibrating(hass, tmp_path, TWO_COVERS_YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "assign_covers")
        result = await submit(hass, result, {COVER_NAME: "tall", "Landing Shutter": "tall"})
        result = await submit(hass, result, {"Landing Shutter": "9000"})
        assert result["errors"] == {"Landing Shutter": "out_of_range"}

        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "calibration_edit")
        result = await submit(hass, result, {CONF_HEIGHT: "9000"})
        assert result["errors"] == {CONF_HEIGHT: "out_of_range"}
        result = await submit(hass, result, {CONF_HEIGHT: "195", CONF_CLOSING_ROLL: "thick"})
        assert result["errors"] == {CONF_CLOSING_ROLL: "not_a_number"}


async def test_an_assigned_profile_supplies_the_height_the_guided_flow_offers(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"If a height is already known, propose that one": the profile's counts as known.

    Mutation caught: looking only at the file and the stored record, which leaves the
    second window of a kind opening on a round 200 it has no reason to.
    """
    async with calibrating(hass, tmp_path, TWO_COVERS_YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        store = the_store(hass, entry)
        await store.async_set_assignments({SECOND_UNIQUE_ID: ("tall", None)})

        FakeRunner(entity_object(hass, COVER, "2-82"))
        acts = (*ENTER, Act(payload={"cover": SECOND_UNIQUE_ID}), *PATH_A_BASIC[3:10])
        result = await drive(hass, freezer, await open_dialog(hass, entry), acts)
        assert result["step_id"] == "height"
        assert _suggested(result, CONF_HEIGHT) == "195"


async def test_the_screens_that_need_a_profile_go_back_when_there_is_none_left(
    hass: HomeAssistant, tmp_path
) -> None:
    """A profile deleted in another tab must not leave a form with nothing in it.

    Mutation caught: building the select from an empty mapping, which voluptuous
    renders as a field that refuses every answer.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        result = await open_dialog(hass, entry)
        flow = next(iter(hass.config_entries.options._progress.values()))  # noqa: SLF001
        assert (await flow.async_step_path_b())["step_id"] == "path"
        assert (await flow.async_step_path_c())["step_id"] == "path"
        assert (await flow.async_step_pick_profile())["step_id"] == "profiles_covers"
        # The two refusal screens are reachable as steps of their own, which is what
        # the translations are checked against.
        assert (await flow.async_step_refused_unknown_cover())["step_id"] == "refused_unknown_cover"
        assert (await flow.async_step_refused_already_calibrating())[
            "step_id"
        ] == "refused_already_calibrating"
        assert result["step_id"] == "init"


async def test_an_assignment_to_a_profile_that_is_gone_shows_as_no_profile(
    hass: HomeAssistant, tmp_path
) -> None:
    """A name that resolves to nothing must not be pre-selected in the form.

    A select whose current value is not among its options cannot be submitted at all -
    not even by a user who came to the form to correct exactly that.

    Mutation caught: pre-filling the stored name without checking it still exists.
    """
    async with calibrating(
        hass,
        tmp_path,
        PROFILE_YAML,
        calibration={
            "profiles": {},
            "covers": {UNIQUE_ID: {CONF_PROFILE: "gone", "source": "guided"}},
        },
    ) as (entry, _commands):
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "assign_covers")
        assert _suggested(result, COVER_NAME) == NO_PROFILE


async def test_a_movement_that_raises_something_nobody_expected_still_has_a_screen(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A flow must never leave a dialog spinning, whatever the runner does.

    Mutation caught: letting a bare exception out of the progress task, which leaves
    the user watching a bar for ever with the shutter marked as calibrating.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:4])

        async def _boom(direction: str, timeout: float | None = None) -> None:
            raise ZeroDivisionError("a bug, not a bus")

        cover.async_calib_home = _boom
        result = await choose(hass, result, "begin")
        assert result["step_id"] == "problem_unknown"


# --------------------------------------------------------------------------------------
# What the 0.5.0 v2 review found
# --------------------------------------------------------------------------------------
# A cover the *file* assigns to a profile, which is the case the assignment form used to
# show as "Nessun profilo" - and the case in which a height must never be borrowed from
# the profile's reference height.
FILE_PROFILE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: {COVER_NAME}
      profile: tall
      height: {HEIGHT}
  cover_profiles:
    tall:
      reference_height: {HEIGHT}
      opening_time: {OPENING}
      closing_time: {CLOSING}
      slat_time: {SLAT}
      roll: {ROLL_DOWN}
    short:
      reference_height: 120
      opening_time: 14
      closing_time: 13
      slat_time: 3
      roll: 1.4
"""

# ...and the same without a `height:`, so that the only travel anybody could name is the
# one the profile was measured on, which is another window's.
FILE_PROFILE_NO_HEIGHT_YAML = FILE_PROFILE_YAML.replace(f"      height: {HEIGHT}\n", "")


def _suggestion(result: dict[str, Any], key: str) -> Any:
    """What a form field opens on, as the frontend reads it off the schema."""
    for marker in result["data_schema"].schema:
        if marker == key:
            return (marker.description or {}).get("suggested_value")
    raise AssertionError(f"{key} is not in this form")


async def _assignment_form(hass: HomeAssistant, entry) -> dict[str, Any]:
    """Open "Profili e tapparelle" -> "Assegna un profilo a ogni tapparella"."""
    result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
    result = await choose(hass, result, "assign_covers")
    assert result["step_id"] == "assign_covers"
    return result


async def test_submitting_the_assignment_form_unchanged_writes_nothing(
    hass: HomeAssistant, tmp_path
) -> None:
    """Looking at the form and pressing Submit is not a calibration.

    Every row used to be collected on submit with a height attached, so a user who
    changed nothing came away with a record per shutter: stamped `guided`, listed under
    "Calibrazioni" as something measured, shadowing the file's own `height:` for ever -
    and the gateway was reloaded to do it (review BUG-2).

    Mutation caught: collecting the rows that did not move, or attaching a height the
    resolution can read out of the file by itself.
    """
    async with calibrating(hass, tmp_path, TWO_COVERS_YAML) as (entry, _commands):
        with patch.object(hass.config_entries, "async_schedule_reload") as reload:
            result = await _assignment_form(hass, entry)
            unchanged = {
                str(marker): _suggestion(result, str(marker))
                for marker in result["data_schema"].schema
            }
            assert set(unchanged.values()) == {NO_PROFILE}
            result = await submit(hass, result, unchanged)
            assert result["step_id"] == "profiles_covers"
            assert the_store(hass, entry).raw_covers == {}

            result = await choose(hass, result, "init")
            await choose(hass, result, "finish")
            await hass.async_block_till_done()
        assert reload.call_count == 0


async def test_the_assignment_form_opens_on_the_profile_the_file_gives_a_cover(
    hass: HomeAssistant, tmp_path
) -> None:
    """A cover whose `myhome.yaml` says `profile: tall` follows one, and must say so.

    Mutation caught: preselecting the stored assignment alone, which shows "Nessun
    profilo" for a cover that follows one and offers to remove something it cannot.
    """
    async with calibrating(hass, tmp_path, FILE_PROFILE_YAML) as (entry, _commands):
        result = await _assignment_form(hass, entry)
        assert _suggestion(result, COVER_NAME) == "tall"


async def test_assigning_another_profile_never_borrows_the_first_one_s_height(
    hass: HomeAssistant, tmp_path
) -> None:
    """A profile's `reference_height` is another window's travel, and is not this one's.

    Without a `height:` of its own, a cover moved from one profile to another used to be
    scaled by the height the *old* profile had been measured on - silently, with no
    screen asking for the real one (review BUG-2).

    Mutation caught: falling back to the profile's reference height when deciding which
    covers still have to be measured.
    """
    async with calibrating(hass, tmp_path, FILE_PROFILE_NO_HEIGHT_YAML) as (entry, _commands):
        result = await _assignment_form(hass, entry)
        result = await submit(hass, result, {COVER_NAME: "short"})
        assert result["step_id"] == "assign_heights"
        result = await submit(hass, result, {COVER_NAME: "150"})
        assert result["step_id"] == "profiles_covers"
        record = the_store(hass, entry).calibration(UNIQUE_ID)
        assert record.profile == "short"
        assert record.height == 150.0



async def test_submitting_the_assignment_form_unchanged_writes_nothing_for_a_file_profile(
    hass: HomeAssistant, tmp_path
) -> None:
    """The case the "only the rows that moved" guard is really for.

    On a cover nothing assigns, the *other* half of the BUG-2 fix (never passing a
    height) already makes an unchanged "Nessun profilo" row write nothing - so the
    guard could be removed and all 1117 tests stayed green (mutation M4). A cover the
    **file** gives a `profile:` is the case that needs it: the form opens on that
    profile, and collecting the row would write `{profile: tall, profile_wins: true}`
    for it, list it under "Calibrazioni" as something the user did, reverse the
    file's own precedence and reload the gateway - after a screen on which nothing
    was touched.

    Mutation caught: collecting the rows that did not move.
    """
    async with calibrating(hass, tmp_path, FILE_PROFILE_YAML) as (entry, _commands):
        with patch.object(hass.config_entries, "async_schedule_reload") as reload:
            result = await _assignment_form(hass, entry)
            unchanged = {
                str(marker): _suggestion(result, str(marker))
                for marker in result["data_schema"].schema
            }
            assert unchanged == {COVER_NAME: "tall"}
            result = await submit(hass, result, unchanged)
            assert result["step_id"] == "profiles_covers"
            assert the_store(hass, entry).raw_covers == {}

            result = await choose(hass, result, "init")
            await choose(hass, result, "finish")
            await hass.async_block_till_done()
        assert reload.call_count == 0


async def test_a_reload_stops_a_shutter_the_conversation_left_running(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The two ways a conversation ends without the user must not differ silently.

    The watchdog stops a shutter it finds still moving; an unload released the session
    and let go of it, while the screen the user then finds says "la tapparella è dove
    l'ha lasciata l'ultimo movimento" (final review, RISK-C).

    Mutation caught: releasing without stopping on the unload path.
    """
    async with calibrating(hass, tmp_path, SLOW_YAML) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        runner = FakeRunner(cover)
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:7])
        assert result["step_id"] == "open_lift"
        cover._moving = "opening"  # noqa: SLF001 - the shutter is still travelling
        assert runner.stops == 0

        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        assert runner.stops >= 1
        # ...and the conversation is over, as BUG-4 asks.
        result = await choose(hass, result, "repeat_step")
        assert result["step_id"] == "expired"


async def test_the_reload_waits_for_a_movement_that_was_cut_short(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Closing the dialog mid-movement must not tear the gateway down over the stop.

    Home Assistant cancels the progress task and *then* calls `async_remove`, so the
    `finally` that shields the stop of a run in flight has not run yet. Two turns of
    the event loop used to stand in for it: a guess about how many awaits the stop
    costs, which nothing pinned - removing both sleeps left all 1117 tests green
    (final review, RISK-D, mutation M11). What is awaited now is the run itself.

    Mutation caught: scheduling the reload without waiting for the cover to be settled.
    """
    async with calibrating(hass, tmp_path, TWO_COVERS_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        # One conversation saved something, so closing the dialog reloads...
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC)
        assert result["step_id"] == "saved"

        # ...and a second one is half way through a movement on the other shutter.
        second = entity_object(hass, COVER, "2-82")
        FakeRunner(second)
        result = await choose(hass, result, "calibrate")
        result = await choose(hass, result, "cover")
        result = await submit(hass, result, {"cover": SECOND_UNIQUE_ID})
        result = await choose(hass, result, "path_a")
        assert second.calibrating is True

        order: list[str] = []

        async def _settled(timeout: float | None = None) -> bool:
            order.append("settled")
            return True

        second.async_calib_settled = _settled
        with patch.object(
            hass.config_entries,
            "async_schedule_reload",
            side_effect=lambda entry_id: order.append("reload"),
        ):
            hass.config_entries.options.async_abort(result["flow_id"])
            await hass.async_block_till_done()

        assert order == ["settled", "reload"]


async def test_a_dialog_open_across_a_reload_writes_through_the_live_store(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A reload builds a new store; the dialog must not serialise the old one over it.

    Two dialogs are not a contrived case - the design supports them, and every Save
    reloads the entry - and the old object's next write used to put a snapshot from
    before the reload back on disk, deleting whatever had been written since with
    nothing in the log to say so (review BUG-3).

    Mutation caught: caching the store object on the dialog and writing through it.
    """
    async with calibrating(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        dialog = await open_dialog(hass, entry)  # opened before the reload

        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        # Something else writes through the store of the new setup.
        await the_store(hass, entry).async_set_profile(
            "written_after_reload",
            calibration_store.cover_profile_data(
                "written_after_reload",
                reference_height=HEIGHT,
                opening_time=OPENING,
                closing_time=CLOSING,
                slat_time=SLAT,
                opening_roll=ROLL_UP,
                closing_roll=ROLL_DOWN,
            ),
        )

        # The old dialog *reads* the live store too: a snapshot from before the reload
        # would list, prefill and confirm against profiles that are no longer what the
        # gateway is running on, and `calibration_edit` would write that snapshot back
        # through the live store (review BUG-3, mutation M5).
        result = await choose(hass, dialog, "profiles_covers")
        result = await choose(hass, result, "pick_profile")
        assert "written_after_reload" in _choices(result, "profile")
        result = await submit(hass, result, {"profile": "written_after_reload"})
        result = await choose(hass, result, "profiles_covers")

        # ...and only then does the old dialog write.
        result = await choose(hass, result, "assign_covers")
        result = await submit(hass, result, {COVER_NAME: "tall"})
        assert result["step_id"] == "profiles_covers"

        on_disk = calibration_store.CalibrationStore(hass, entry.entry_id)
        await on_disk.async_load()
        assert "written_after_reload" in on_disk.raw_profiles
        assert on_disk.calibration(UNIQUE_ID).profile == "tall"


async def test_a_reload_under_a_live_conversation_ends_it_on_the_expired_screen(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Home Assistant cancels no flow when an entry is reloaded, so the dialog must.

    The conversation used to go on driving the entity object of the *old* setup: its
    gateway sessions are closed, so the frames go nowhere while the screens say the
    shutter moved; the live entity carries no `Calibrating`, so `set_cover_position` is
    free to drive the same motor; and the dead entity's 1 Hz position tick is never
    cancelled (review BUG-4).

    Mutation caught: not marking the conversation expired on unload.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:4])
        assert result["step_id"] == "path_a"
        assert hass.states.get(ENTITY).attributes[ATTR_CALIBRATING] is True

        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        # The shutter of the new setup is nobody's.
        assert ATTR_CALIBRATING not in hass.states.get(ENTITY).attributes
        # ...and the next click lands on the screen that says what happened.
        result = await choose(hass, result, "begin")
        assert result["step_id"] == "expired"
        assert result["menu_options"] == ["calibrate", "init"]


async def test_a_movement_whose_cover_went_away_is_refused_rather_than_driven(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Every movement resolves the entity again, and one that is gone has a screen.

    Mutation caught: holding the entity object for the whole conversation.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        from custom_components.myhome.const import CONF_PLATFORMS, DOMAIN

        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:4])
        # The cover is taken out of the file and the entry rebuilt: the conversation is
        # pointing at something that is not configured any more.
        hass.data[DOMAIN][MAC][CONF_PLATFORMS][COVER].pop(DEVICE_KEY)
        result = await choose(hass, result, "begin")
        assert result["step_id"] == "refused_unknown_cover"


async def test_the_watchdog_is_not_armed_again_by_the_saved_screen(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, caplog
) -> None:
    """Half an hour after a Save, the log must not say that nothing was saved.

    The `saved` screen renders through the same overridden `async_show_menu` as every
    other, which re-armed the watchdog on a conversation that was over (review RISK-2).

    Mutation caught: leaving the cover held after Save.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC)
        assert result["step_id"] == "saved"

        caplog.clear()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=IDLE_TIMEOUT_SEC + 1))
        await hass.async_block_till_done()

        assert [record for record in caplog.records if record.levelname == "WARNING"] == []
        # ...and the two ways out of the screen still work, including the one that
        # starts a second conversation in the same dialog.
        result = await choose(hass, result, "calibrate")
        assert result["step_id"] == "calibrate"
        result = await choose(hass, result, "cover")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        assert result["step_id"] == "path"


async def test_clearing_every_field_by_hand_deletes_the_record(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Modifica i valori a mano", emptied, means "forget this shutter".

    A record left holding nothing but a `source` and a timestamp vanishes from the
    "Calibrazioni" screen, which lists what says something, and stays in `.storage` for
    ever (review RISK-3).

    Mutation caught: storing the empty record instead of deleting it.
    """
    async with calibrating(hass, tmp_path, OWN_NUMBERS_YAML) as (entry, _commands):
        store = the_store(hass, entry)
        await store.async_set_calibration(
            UNIQUE_ID,
            calibration_store.cover_calibration_data(
                UNIQUE_ID, height=HEIGHT, overrides={CONF_OPENING_TIME: 20.0}
            ),
        )
        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "calibration_edit")
        result = await submit(hass, result, {CONF_HEIGHT: "", CONF_OPENING_TIME: ""})
        assert result["step_id"] == "calibration_actions"
        assert the_store(hass, entry).raw_covers == {}


async def test_a_profile_may_not_be_named_like_the_no_profile_option(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`no_profile` is a valid YAML key and the assignment select's sentinel.

    Mutation caught: accepting it, after which that profile can never be unassigned
    from "Profili e tapparelle" again.
    """
    async with calibrating(hass, tmp_path, YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_BASIC[:-2])
        assert result["step_id"] == "profile_name"
        result = await submit(hass, result, {CONF_NAME: NO_PROFILE})
        assert result["errors"] == {CONF_NAME: "invalid_name"}


async def test_editing_a_profile_reaches_the_windows_that_follow_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Path B keeps the name and the height, and the numbers are worked out from them.

    That is the whole reason the record carries `{profile, height, profile_wins}` and
    no numbers at all: a copy of the profile would have stopped following it the moment
    it was corrected.

    Mutation caught: storing the profile's values in the record, after which the
    correction below reaches nothing.
    """
    # A *stored* profile, because a `cover_profiles:` block belongs to the file and the
    # dialog does not edit it. The file's own case is the test below.
    async with calibrating(hass, tmp_path, OWN_NUMBERS_YAML) as (entry, _commands):
        await the_store(hass, entry).async_set_profile(
            "tall",
            calibration_store.cover_profile_data(
                "tall",
                reference_height=HEIGHT,
                opening_time=OPENING,
                closing_time=CLOSING,
                slat_time=SLAT,
                opening_roll=ROLL_DOWN,
                closing_roll=ROLL_DOWN,
            ),
        )
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_B)
        assert result["step_id"] == "saved"
        result = await choose(hass, result, "init")
        await choose(hass, result, "finish")
        await hass.async_block_till_done()
        await set_connected(hass, True)
        # The file says 30 s for this cover; the profile it was told to follow says
        # 22.3, and that is what the shutter runs on.
        assert hass.states.get(ENTITY).attributes["Opening time"] == pytest.approx(
            OPENING, abs=0.05
        )

        # The profile is corrected by hand: this window is 195 cm, the profile's own
        # reference height, so the numbers reach it unscaled.
        result = await choose(hass, await open_dialog(hass, entry), "profiles_covers")
        result = await choose(hass, result, "pick_profile")
        result = await submit(hass, result, {"profile": "tall"})
        result = await choose(hass, result, "profile_edit")
        result = await submit(
            hass,
            result,
            {
                CONF_REFERENCE_HEIGHT: str(HEIGHT),
                CONF_OPENING_TIME: "40",
                CONF_CLOSING_TIME: "39",
                CONF_SLAT_TIME: "5",
                CONF_OPENING_ROLL: str(ROLL_UP),
                CONF_CLOSING_ROLL: str(ROLL_DOWN),
            },
        )
        assert result["step_id"] == "profile_actions"
        # The record still holds nothing but the name and the height...
        assert "overrides" not in the_calibration(hass, entry)
        result = await choose(hass, result, "profiles_covers")
        result = await choose(hass, result, "init")
        await choose(hass, result, "finish")
        await hass.async_block_till_done()
        await set_connected(hass, True)
        # ...and the shutter runs on the corrected profile.
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == pytest.approx(40.0, abs=0.05)
        assert state.attributes["Closing time"] == pytest.approx(39.0, abs=0.05)


async def test_a_profile_corrected_in_the_file_reaches_the_windows_that_follow_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A `cover_profiles:` profile is the user's, and correcting it has to be enough.

    The first fix of BUG-1 stored the profile's numbers in the follower's record and
    derived them again whenever a *stored* profile was written. A profile written by
    hand in `myhome.yaml` - which this integration has supported since 0.4.x and the
    release notes still recommend - has no such hook: the numbers were a frozen copy,
    and the attribute went on naming a profile the window no longer followed (final
    review, RISK-A).

    Mutation caught: storing what the profile comes to instead of the fact that this
    window follows it.
    """
    async with calibrating(hass, tmp_path, PROFILE_AND_OWN_NUMBERS_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_B)
        assert result["step_id"] == "saved"
        result = await choose(hass, result, "init")
        await choose(hass, result, "finish")
        await hass.async_block_till_done()
        await set_connected(hass, True)
        assert hass.states.get(ENTITY).attributes["Opening time"] == pytest.approx(
            OPENING, abs=0.05
        )

        # The user corrects the profile in their own file and reloads.
        (tmp_path / "myhome.yaml").write_text(
            PROFILE_AND_OWN_NUMBERS_YAML.replace(
                f"      opening_time: {OPENING}", "      opening_time: 40.0"
            ),
            encoding="utf-8",
        )
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == pytest.approx(40.0, abs=0.05)
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "profile tall"


async def test_assigning_a_profile_makes_the_cover_follow_it(
    hass: HomeAssistant, tmp_path
) -> None:
    """"Assegna un profilo" and path B now mean the same thing by the same sentence.

    The screen says "this cover is built like those ones" and used to change nothing at
    all on a file that writes its own run times - which is how the owner's is written -
    while path B, two menus away, changed everything (final review, RISK-B).

    Mutation caught: writing the assignment without `profile_wins`.
    """
    async with calibrating(hass, tmp_path, PROFILE_AND_OWN_NUMBERS_YAML) as (entry, _commands):
        before = hass.states.get(ENTITY)
        assert before.attributes["Opening time"] == pytest.approx(FILE_OPENING)

        result = await _assignment_form(hass, entry)
        result = await submit(hass, result, {COVER_NAME: "tall"})
        assert result["step_id"] == "profiles_covers"
        record = the_store(hass, entry).calibration(UNIQUE_ID)
        assert record.follows_a_profile is True

        result = await choose(hass, result, "init")
        await choose(hass, result, "finish")
        await hass.async_block_till_done()
        await set_connected(hass, True)
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == pytest.approx(OPENING, abs=0.05)
        assert state.attributes["Closing time"] == pytest.approx(CLOSING, abs=0.05)
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "profile tall"

        # ...and "Vedi i valori" says so: the flag is a precedence, not a detail.
        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "calibration_view")
        assert f"{CONF_PROFILE_WINS}: true" in result["description_placeholders"]["values"]


# --------------------------------------------------------------------------------------
# The check every screen above is run through
# --------------------------------------------------------------------------------------
async def test_every_screen_of_a_whole_conversation_renders_its_own_text(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`check_the_screen_renders` is called on every screen; this one says which.

    A check that silently stopped finding anything - a renamed key, a step id that no
    longer matches the strings - would leave every test in this file passing while the
    invariant it is there for went unchecked.
    """
    RENDERED_STEPS.clear()
    async with calibrating(hass, tmp_path, OWN_NUMBERS_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await drive(hass, freezer, await open_dialog(hass, entry), PATH_A_PRECISE)
        assert result["step_id"] == "saved"
        result = await choose(hass, result, "init")
        result = await choose(hass, result, "profiles_covers")
        result = await choose(hass, result, "pick_profile")
        result = await submit(hass, result, {"profile": "tall"})
        result = await choose(hass, result, "profile_view")
        result = await submit(hass, result)
        result = await choose(hass, result, "profile_edit")
        result = await submit(
            hass,
            result,
            {
                CONF_REFERENCE_HEIGHT: str(HEIGHT),
                CONF_OPENING_TIME: str(OPENING),
                CONF_CLOSING_TIME: str(CLOSING),
                CONF_SLAT_TIME: str(SLAT),
                CONF_OPENING_ROLL: str(ROLL_UP),
                CONF_CLOSING_ROLL: str(ROLL_DOWN),
            },
        )
        result = await choose(hass, result, "profile_delete")
        result = await choose(hass, result, "profile_actions")
        result = await choose(hass, result, "profiles_covers")
        result = await choose(hass, result, "assign_covers")
        result = await submit(hass, result, {COVER_NAME: "tall"})
        result = await choose(hass, result, "init")
        result = await choose(hass, result, "calibrations")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "calibration_view")
        result = await submit(hass, result)
        result = await choose(hass, result, "calibration_edit")
        result = await submit(hass, result, {})
        result = await choose(hass, result, "calibration_delete")
        await choose(hass, result, "calibration_actions")

    assert {
        "init",
        "calibrate",
        "cover",
        "path",
        "path_a",
        "home_closed_done",
        "open_brief",
        "open_lift",
        "open_top",
        "open_result",
        "height",
        "height_result",
        "close_brief",
        "close_bottom",
        "close_result",
        "measure_descent",
        "measure_ascent",
        "tape_result",
        "profile_name",
        "summary_basic",
        "measure_verify",
        "verify_result",
        "summary_precise",
        "saved",
        "profiles_covers",
        "assign_covers",
        "pick_profile",
        "profile_actions",
        "profile_view",
        "profile_edit",
        "profile_delete",
        "calibrations",
        "calibration_actions",
        "calibration_view",
        "calibration_edit",
        "calibration_delete",
    } <= RENDERED_STEPS


def test_the_screen_check_catches_what_the_live_walk_through_found(monkeypatch) -> None:
    """The checker itself, against the two ways a screen can fail to render.

    Mutation caught: a check that asserts nothing (the menu title rule is the one the
    second live walk-through paid for, and it has to stay expensive to break).
    """
    steps = dict(STRINGS["options"]["step"])
    steps["init"] = {
        "title": "Configuring {gateway}",
        "description": "no placeholders here",
        "menu_options": {"finish": "Close"},
    }
    steps["cover"] = {"title": "Pick a cover", "description": "one of {covers}"}
    monkeypatch.setitem(STRINGS["options"], "step", steps)

    with pytest.raises(AssertionError, match="menu title"):
        check_the_screen_renders(
            {
                "type": FlowResultType.MENU,
                "step_id": "init",
                "menu_options": ["finish"],
                "description_placeholders": {"gateway": "MyHOMEServer1"},
            }
        )
    with pytest.raises(AssertionError, match="never reaches"):
        check_the_screen_renders(
            {"type": FlowResultType.FORM, "step_id": "cover", "description_placeholders": {}}
        )
