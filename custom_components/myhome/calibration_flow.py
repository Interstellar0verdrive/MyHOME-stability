"""The guided cover calibration, and everything else under "Configura" (0.5.0 v2).

Phase 1 built the two halves this module sits between: the maths (`calibration.py`),
which turns button presses and tape readings into a travel model, and the runner
(`cover.py`, the four `async_calib_*` primitives), which drives one shutter and reports
what the bus really did. What was missing was the conversation - and a calibration is a
conversation, because half of the measurements only a person standing in the room can
make.

The first draft put that conversation behind "Aggiungi" on the integration page, as two
config subentry types. The conversation was right and the place was wrong: subentries
put stray rows under the devices, made Home Assistant group every device under "devices
not belonging to a subentry", offered a "rename" that renamed a row rather than a
profile, and gave the user nowhere to look at a stored number, let alone correct one.
So everything now lives under **Configura** - one options flow with a menu at the top
of it - and the data lives in the integration's own store (`calibration_store.py`).

This module is the two mixins that options flow is made of:

* `CalibrationManagementMixin` - the screens that show, assign, edit and delete what is
  stored, without moving a shutter;
* `GuidedCalibrationMixin` - the guided measurement itself.

The shape of the guided conversation is the whole point, so it is worth stating before
the code:

* **No stopwatch.** The integration already knows when the motor starts (the actuator
  answers our frame with its own status), so the user is never asked to time anything.
  They press a button when something *happens* - the bottom edge lifts off the floor,
  the shutter stops - and the time is the instant that press reaches Home Assistant
  minus the instant the motor really began to turn.
* **Nothing moves by itself on a screen with a press to make.** The instructions come
  first, then an explicit "1) Avvia la tapparella", and only then the two presses. The
  runs of the tape steps do start on their own: there is nothing to be ready for while
  they run, and the whole phase is announced once, on `tape_brief`, rather than a
  button at a time.
* **The tape readings are dealt from where the shutter already is.** Each one runs to
  its percentage from one end stop or the other, so the one whose end stop the shutter
  is standing at is taken first and the homing it would have cost never happens
  (`order_the_readings`).
* **Every measurement is confirmed.** After the presses, after the tape, after the
  height: a screen showing what was just measured, with "Ripeti la misura" next to
  "Va bene, avanti".
* **Nothing is written before Save.** Every screen up to the summary only moves the
  shutter, which is an ordinary command the estimate follows as it follows any other.
  Closing the dialog at any point leaves the configuration, the storage and the shutter
  exactly as they were.
* **Every measuring step is self-contained.** It first brings the shutter to the end
  stop it needs and then does its one thing, so "Ripeti questo passo" is always safe and
  never asks the user to remember where they were.

The three paths, chosen after the intro:

A. *the first shutter of its kind* - the full measurement, which produces a **profile**
   plus this window's own numbers;
B. *the same as one already calibrated* - pick the profile, measure the height with a
   tape, optionally check it at half travel;
C. *refine this one* - it follows a profile but gets it wrong: measure its own times,
   and if needed its own roll coefficients, and store them as overrides.

The steps of a path are a **plan**: a list of stage names walked in order
(`_async_advance`), which is what makes "Ripeti questo passo" a one-liner (re-enter the
stage the pointer is on) and what lets the precise level graft four more measurements
onto the end of path A without a second copy of the state machine.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
from homeassistant.helpers.translation import async_get_translations
from homeassistant.util import dt as dt_util

from .calibration import (
    FIXED_SCALE_BOUNDS,
    REASON_BAD_POINT,
    REASON_BUSY,
    REASON_NO_ECHO,
    REASON_NOT_DELIVERED,
    REASON_NOT_STOPPED,
    CalibrationError,
    DirectionFit,
    PressTiming,
    RunReport,
    deviation_cm,
    fit_from_run,
    predict_cm,
    slat_time_from_gap,
    slat_time_from_press,
    timing_from_presses,
    timing_with_slat,
)
from .calibration_store import (
    PROFILE_NAME_PATTERN,
    CalibrationStore,
    StoredCalibration,
    async_get_store,
    cover_calibration_data,
    cover_profile_data,
    describe_profile,
    loaded_store,
    merged_profiles,
    profile_overrides,
    resolve_cover,
    stored_calibration,
)
from .const import (
    CALIBRATION_ORIGIN_PROFILE_SLOT,
    CALIBRATION_ORIGIN_SELECTOR,
    CALIBRATION_SOURCE_GUIDED,
    CALIBRATION_SOURCE_MANUAL,
    CALIBRATION_SOURCE_PROFILE,
    CONF_ADVANCED_SHUTTER,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_PROFILES,
    CONF_ENTITIES,
    CONF_HEIGHT,
    CONF_MEASURED_ON,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PLATFORMS,
    CONF_PROFILE,
    CONF_PROFILE_WINS,
    CONF_RAW,
    CONF_REFERENCE_COVER,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
    CONF_SOURCE,
    CONF_YAML_KEY,
    DEFAULT_ROLL_SHUTTER,
    DIRECTION_CLOSE,
    DIRECTION_OPEN,
    DOMAIN,
    LOGGER,
    MAX_ROLL,
    MIN_ROLL,
)
from .cover import calibration_yaml
from .validate import derive_cover_from_profile

# How long a measuring screen waits for the press it is about. The user is watching a
# shutter that takes twenty seconds to run: a minute and a half is generous for the
# press itself and short enough that a screen left open over lunch does not come back
# with a "measurement" of four thousand seconds. A flow cannot push a new screen at a
# browser, so the window is checked when the press finally arrives (see `_timed_out`).
PRESS_TIMEOUT_SEC = 90.0

# How long a conversation may sit on one screen before the shutter is given back.
#
# Home Assistant never expires a flow of its own accord, and a browser tab that is
# simply closed - a laptop that sleeps, a phone that kills the tab - tells nobody. The
# flow object would then live for the rest of the Home Assistant run holding a
# calibration session, so `Calibrating` would stay true and `set_cover_position` on that
# shutter would keep raising until the entry was reloaded.
#
# Two lengths, because the two kinds of screen are waiting for different things. A
# screen with nothing moving is waiting for somebody to read it, and half an hour of
# reading (or of being interrupted by the doorbell) is a perfectly ordinary thing to do:
# the first live walk-through lost its session to a ten-minute timer while the user was
# still on the introduction. A screen that follows a movement is waiting for a person
# who is standing in front of a shutter with a tape in their hand, and ten minutes of
# that means they walked away.
IDLE_TIMEOUT_SEC = 1800.0
MOVED_IDLE_TIMEOUT_SEC = 600.0

# Where the automatic runs stop. The three fractions of the precise level bracket the
# travel (a quarter, a half, three quarters); the verification deliberately lands
# *between* them, at two fifths, so it asks the model about a place no measurement
# taught it. Path B's optional check runs to the half, which is where a shutter that
# follows the wrong profile is most obviously wrong.
HALF_RUN = 0.5
QUARTER_RUN = 0.25
THREE_QUARTER_RUN = 0.75
VERIFY_RUN = 0.40
VERIFY_RUN_PROFILE = 0.50

# Above this the profile is not describing this window (FLOW, "soglia affinamento":
# 3 cm), and path B offers path C instead of pretending the check passed.
REFINE_THRESHOLD_CM = 3.0

# What the tape form promises next to the expected value. The precise level knows the
# model it is checking, so it can afford to be strict; the basic level's expectation is
# drawn from the default roll of an ordinary shutter and deserves a wider margin - the
# live walk-through read fifteen centimetres off the default geometry on a shutter that
# turned out to be perfectly ordinary, and a band of ten made that look like a fault.
EXPECTED_TOLERANCE_CM = 3.0
ROUGH_TOLERANCE_CM = 15.0

# The tape is read to the nearest centimetre; a window is at most a few metres of
# curtain. The bounds are checked in the flow rather than by a number selector, because
# the fields are text - a comma is a decimal separator in most of the languages this
# integration is translated into, and a `<input type="number">` refuses it.
MIN_HEIGHT_CM = 20.0
MAX_HEIGHT_CM = 500.0
# The lift-off run of the ascent, and what the screen after it is allowed to say.
#
# The press that ends that run carries a fifth of a second of human reaction, an HTTP
# request, whatever the command queue costs and the motor's own eighth of a second of
# braking - all of it at the slowest the curtain ever moves (the closed end, four to
# seven centimetres a second on an ordinary window). So a *good* press leaves the bottom
# edge standing a few centimetres above its rest, and the three cases the check screen
# offers are exactly the three things the user can see:
#
# * still touching  - the press came *before* the edge left, so the slat phase measured
#   is too short and no arithmetic can put back a distance that was never travelled:
#   the run has to be made again;
# * a few centimetres - what a press that went well looks like;
# * a hand's breadth or more - a late press, and the one case a tape can repair
#   (`calibration.slat_time_from_gap`).
TOUCHING_CM = 1.0
MAX_GAP_CM = 50.0
# Past this much between the press and the stop frame reaching the bus, the gap is the
# command queue's doing and not the user's, and the check screen says so rather than
# leaving them to conclude they were slow. A second is already several centimetres of
# bar; an idle gateway answers in tens of milliseconds.
LATE_STOP_SEC = 1.0

# What a height defaults to when nothing at all is known about this window. Deliberately
# a round number and not the one in the file: a pre-filled 198 looks like a measurement
# somebody already made, and the whole point of the screen is that it has not been made.
FALLBACK_HEIGHT_CM = 200.0

# The ranges of the hand-editing forms. They are the schema's own (`validate.py`), so a
# number typed here is one the file could have carried.
MIN_RUN_SEC = 1.0
MAX_RUN_SEC = 600.0
MAX_SLAT_SEC = 60.0

# Two reasons of the flow's own, next to the runner's (`calibration.REASON_*`): the
# press that never came, and anything else at all.
REASON_TIMEOUT = "timeout"
REASON_UNKNOWN = "unknown"

# Every reason that has a screen of its own. A reason outside this tuple is shown as
# `unknown` rather than as a step id nobody wrote a text for.
PROBLEM_REASONS: tuple[str, ...] = (
    REASON_NO_ECHO,
    REASON_NOT_DELIVERED,
    REASON_NOT_STOPPED,
    REASON_BUSY,
    REASON_BAD_POINT,
    REASON_TIMEOUT,
    REASON_UNKNOWN,
)

# The plans. A stage is the name of an `async_step_` method; the pointer walks the list
# and "Ripeti questo passo" re-enters the stage it is on.
#
# The order of the tape phase is *not* the order written here: `tape_brief` reorders the
# readings that follow it so that the first one starts from the end stop the shutter is
# already standing at (`order_the_readings`).
PLAN_FULL: tuple[str, ...] = (
    "home_closed",
    "open_timed",
    "height_read",
    "close_timed",
    "tape_brief",
    "half_down",
    "half_up",
    "profile_name",
    "summary",
)
# The thorough calibration (lexicon of 13 Sep: "calibrazione approfondita", which the
# texts used to call "the precise level"). Four readings that fit the two roll
# coefficients *and* a scale on the run times, and then the check. It is reached three
# ways and is the same plan every time: from the summary of path A, from the summary of
# a correction, and chosen up front as the third scope of a correction - which is the
# one way in that has timed nothing of its own, and takes the times the cover already
# moves on as the model the readings correct (`_adopt_the_model_in_use`).
PLAN_PRECISE: tuple[str, ...] = (
    "tape_brief",
    "quarter_down",
    "three_quarter_down",
    "quarter_up",
    "three_quarter_up",
    "verify",
    "summary",
)
# ...and the same with the curtain travel in front of it, for a cover nobody has ever
# measured one for. Every reading of the phase is a number of centimetres out of that
# travel, so a thorough calibration cannot start without it; a travel already known -
# stored for this cover, or written in the configuration file - is *not* asked for
# again, because the user is standing in front of the shutter to read a tape and this
# is the one reading that does not change.
PLAN_PRECISE_TRAVEL: tuple[str, ...] = ("tape_brief", "height_read", *PLAN_PRECISE[1:])
# Path B is a tape phase and nothing else: the warning screen, one homing, one reading.
# The height is measured from the rest of the bottom edge to where it is *now*, which
# only means the whole travel when "now" is the top, so `height_read` brings the shutter
# there first (in path A it is already there, and the runner answers a homing that has
# nothing to run with the settle alone).
PLAN_PROFILE: tuple[str, ...] = ("tape_brief", "height_read", "verify_offer", "summary")
# Paths A and C open with a homing the user is asked to confirm, because what follows it
# is a *timed press*: somebody has to be standing in front of the shutter, watching, when
# the run starts. Every homing's wait is bounded by the modelled run of a model that is,
# in path C, wrong by hypothesis - that is why the user is in path C - so without the
# confirmation the first measured run could start from a shutter still travelling. The
# tape phase has no such confirmation: nothing there has to be caught by a human eye, so
# it leans on `async_calib_home` (the full run time plus a margin) and says what it is
# doing in the progress text instead (maintainer, 13 Sep).
PLAN_TIMES: tuple[str, ...] = ("home_closed", "open_timed", "close_timed", "summary")
PLAN_TIMES_AND_ROLLS: tuple[str, ...] = (
    "home_closed",
    "open_timed",
    "height_read",
    "close_timed",
    "tape_brief",
    "half_down",
    "half_up",
    "summary",
)
# Path B's optional check, grafted onto the plan when it is accepted. Its own briefing is
# `verify_offer`, the screen that offered it, and the run homes itself.
PLAN_VERIFY_B: tuple[str, ...] = ("verify_b",)

# The readings of the tape phase, and the end stop the run of each one starts from.
#
# A stage here is "bring the shutter to an end stop, run to a percentage, read the tape":
# there is nothing to press and nothing to be quick about, which is what lets them chain
# without a confirmation between them. It is also what lets them be *reordered*: a
# reading whose run starts where the shutter already stands costs one movement instead of
# two, so the plan is walked in the order that homes the shutter least (maintainer,
# 13 Sep: after the descent the shutter is at the bottom, so the ascent's reading comes
# first and the full opening happens once, between the two).
TAPE_RUN_FROM: dict[str, str] = {
    "half_down": DIRECTION_OPEN,
    "half_up": DIRECTION_CLOSE,
    "quarter_down": DIRECTION_OPEN,
    "three_quarter_down": DIRECTION_OPEN,
    "quarter_up": DIRECTION_CLOSE,
    "three_quarter_up": DIRECTION_CLOSE,
}
# The readings of the tape phase that stay where the plan puts them: the travel, which is
# read with the shutter standing still and is what every other reading is scaled by, and
# the two verifications, which put a question to a model that is only finished once every
# other reading is in.
TAPE_FIXED: tuple[str, ...] = ("height_read", "verify", "verify_b")
TAPE_STAGES: frozenset[str] = frozenset(TAPE_RUN_FROM) | frozenset(TAPE_FIXED)


def order_the_readings(stages: Sequence[str], at: str | None) -> list[str]:
    """The readings of one tape phase, in the order that homes the shutter least.

    `at` is the end stop the shutter is standing at, or `None` when it is somewhere in
    between. The first reading whose run starts from there needs no homing at all; after
    any run to a percentage the shutter is between the two end stops again, so every
    later reading costs a homing whichever one is picked and the plan's own order - which
    is written so that each homing is the *short* way round - is kept.

    The readings of `TAPE_FIXED` are not moved: they are answered where the plan puts
    them, and only the movable ones are dealt round them.
    """
    movable = [stage for stage in stages if stage in TAPE_RUN_FROM]
    ordered: list[str] = []
    here = at
    while movable:
        pick = next((stage for stage in movable if TAPE_RUN_FROM[stage] == here), movable[0])
        movable.remove(pick)
        ordered.append(pick)
        here = None
    dealt = iter(ordered)
    return [next(dealt) if stage in TAPE_RUN_FROM else stage for stage in stages]


# The progress text of an automatic run, by the direction it runs in. A mapping rather
# than a conditional expression so that every progress action of the flow can be found
# (and checked against the translations) without reading the code that uses it.
RUNNING_ACTION = {DIRECTION_CLOSE: "running_down", DIRECTION_OPEN: "running_up"}
# ...and of a homing, by the end stop it is heading for.
HOMING_ACTION = {DIRECTION_CLOSE: "homing_closed", DIRECTION_OPEN: "homing_open"}

# Why a conversation may not start on the cover it was pointed at. They are the reasons
# `_claim` answers with; each has a screen that offers a way back to the menu rather
# than closing the dialog on the user.
REASON_UNKNOWN_COVER = "unknown_cover"
REASON_ALREADY_CALIBRATING = "already_calibrating"
CLAIM_REASONS: tuple[str, ...] = (REASON_UNKNOWN_COVER, REASON_ALREADY_CALIBRATING)

# The exits of the lift-off check screen, in the order the user's eye runs down the
# shutter: still on its base, a few centimetres up, a hand's breadth up.
LIFT_CHECK_OPTIONS = ["lift_too_early", "lift_accept", "lift_gap", "not_right"]

PATH_FIRST = "path_a"
PATH_PROFILE = "path_b"
PATH_REFINE = "path_c"

FIELD_COVER = "cover"
FIELD_GAP_CM = "gap_cm"
FIELD_MEASURED_CM = "measured_cm"
FIELD_PROFILE = "profile"
# "Nessun profilo" in the assignment form. Not the empty string: a select whose option
# is "" renders as a blank line the user cannot tell from an unset field. It is also a
# translation key under `selector.profile_choice.options`, so it has to be a slug
# (`[a-z0-9-_]+`, no leading or trailing separator) or hassfest refuses `strings.json`.
NO_PROFILE = "no_profile"

_NAME_RE = re.compile(PROFILE_NAME_PATTERN)
_NOT_A_NAME = re.compile(r"[^A-Za-z0-9_]+")

# The five numbers a profile is made of, in the order the hand-editing form shows them,
# with the bounds each one is refused outside of.
PROFILE_FIELDS: tuple[tuple[str, float, float], ...] = (
    (CONF_REFERENCE_HEIGHT, MIN_HEIGHT_CM, MAX_HEIGHT_CM),
    (CONF_OPENING_TIME, MIN_RUN_SEC, MAX_RUN_SEC),
    (CONF_CLOSING_TIME, MIN_RUN_SEC, MAX_RUN_SEC),
    (CONF_SLAT_TIME, 0.0, MAX_SLAT_SEC),
    (CONF_OPENING_ROLL, MIN_ROLL, MAX_ROLL),
    (CONF_CLOSING_ROLL, MIN_ROLL, MAX_ROLL),
)
# ...and the same for one cover's own numbers. `height` first, then whichever of the
# travel keys were measured: they are optional, and a field left empty removes the
# override rather than storing a zero.
CALIBRATION_FIELDS: tuple[tuple[str, float, float], ...] = (
    (CONF_OPENING_TIME, MIN_RUN_SEC, MAX_RUN_SEC),
    (CONF_CLOSING_TIME, MIN_RUN_SEC, MAX_RUN_SEC),
    (CONF_SLAT_TIME, 0.0, MAX_SLAT_SEC),
    (CONF_OPENING_ROLL, MIN_ROLL, MAX_ROLL),
    (CONF_CLOSING_ROLL, MIN_ROLL, MAX_ROLL),
)

ERROR_NOT_A_NUMBER = "not_a_number"
ERROR_OUT_OF_RANGE = "out_of_range"
ERROR_ABOVE_THE_TRAVEL = "above_the_travel"
ERROR_INVALID_NAME = "invalid_name"


def _text_field() -> TextSelector:
    """A number typed by a person, which is to say a piece of text.

    Every numeric field of these screens is a text box and not a `NumberSelector`.
    `NumberSelector` renders `<input type="number">`, whose decimal separator is the
    browser's and not the user's: a shutter measured as `85,5` in Italian is refused
    outright by a browser running in English, with no message that says why. The
    parsing below accepts both separators and every screen says so.
    """
    return TextSelector(TextSelectorConfig())


def parse_number(value: Any) -> float | None:
    """A number written the way a person writes it, or None.

    A comma or a point, and nothing else: a thousands separator is not accepted,
    because "1.234" is a thousand in one country and one-and-a-bit in another and a
    tape reading is never a thousand of anything.
    """
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number


def _other_end(direction: str) -> str:
    """The end stop a run of `direction` has to start from."""
    return DIRECTION_OPEN if direction == DIRECTION_CLOSE else DIRECTION_CLOSE


def _suggested_name(entity_id: str) -> str:
    """A profile name the user can accept as it stands, from the cover's entity id."""
    object_id = entity_id.split(".", 1)[-1] if entity_id else ""
    cleaned = _NOT_A_NAME.sub("_", object_id).strip("_")
    return cleaned or "shutter"


def overrides_yaml(cover_key: str, overrides: Mapping[str, float], height: float | None) -> str:
    """The `myhome.yaml` equivalent of a set of per-cover overrides.

    The counterpart of `cover.calibration_yaml` for the paths that measure one window
    rather than a model of window: the same numbers, written where the user would have
    written them by hand, so that "the integration is keeping this for me" is never the
    only way to have them.
    """
    lines = ["cover:", f"  {cover_key}:"]
    if height is not None:
        lines.append(f"    {CONF_HEIGHT}: {round(height, 1)}")
    for key, value in overrides.items():
        lines.append(f"    {key}: {round(value, 2)}")
    return "\n".join(lines) + "\n"


def profile_reference_yaml(
    cover_key: str, profile: str, height: float, values: Mapping[str, float] | None = None
) -> str:
    """The two lines path B is really about - and the numbers they come to.

    The two lines say what was decided: this window is one of those, and it is this
    tall. The numbers under them are what those two lines *mean* for this window, and
    they are there for the same reason the flow stores them: a `profile:` does not beat
    a run time written for the cover itself (spec 1.3), so on a file that carries its
    own times the two lines alone would change nothing at all (0.5.0 v2 review, BUG-1).
    """
    lines = [
        "cover:",
        f"  {cover_key}:",
        f"    {CONF_PROFILE}: {profile}",
        f"    {CONF_HEIGHT}: {round(height, 1)}",
    ]
    lines += [f"    {key}: {round(value, 2)}" for key, value in (values or {}).items()]
    return "\n".join(lines) + "\n"


@dataclass(slots=True)
class _Measured:
    """Everything the conversation has collected, and nothing that was saved.

    It lives for as long as the dialog does and is thrown away with it - which is the
    "nothing is written before Save" of the UX, stated as a data structure.
    """

    height: float | None = None
    # True when the height above was read off a tape *in this conversation*. A height
    # that was merely carried in - the record's, or the file's, so that the summary and
    # the fits have something to scale by - is not this conversation's to write: a copy
    # of the file's `height:` stored here would shadow the file for ever (0.5.0 v2
    # review, BUG-2, and the same staleness RISK-A is about).
    height_measured: bool = False
    opening: PressTiming | None = None
    closing: PressTiming | None = None
    # The lift-off run of the ascent, which since 0.5.0 is a run of its own: the slat
    # phase the press measured, the motor seconds from the start of that run to the
    # motor coming to rest after the stop it triggered, the gap the user optionally
    # taped afterwards, and whether that stop left late enough for the gap to be the
    # gateway's doing. The first is what `opening` is built from; the second and third
    # are what `calibration.slat_time_from_gap` replaces the first with at fit time.
    slat_seconds: float | None = None
    lift_run_sec: float | None = None
    lift_gap_cm: float | None = None
    lift_late: bool = False
    # (motor seconds of the run, centimetres read off the tape), in the order measured.
    descent: list[tuple[float, float]] = field(default_factory=list)
    ascent: list[tuple[float, float]] = field(default_factory=list)
    deviation: float | None = None
    # The fraction of the travel the verification really ran to, remembered because the
    # summary names it in percent and the two verifications do not run to the same
    # place: `VERIFY_RUN` at the precise level of path A, `VERIFY_RUN_PROFILE` for the
    # check path B offers. A constant here would put "40 %" under a run that went half
    # way (0.5.0 v5 review).
    verify_fraction: float | None = None
    precise: bool = False
    # True when `opening` and `closing` above were not timed in this conversation but
    # taken off the model the cover already moves on ("solo la calibrazione
    # approfondita"). The fit still corrects them - that is what the time scale of
    # `fit_direction` is - but the record's `raw` says they were not pressed for, so
    # that a reader six months later does not take them for a measurement.
    times_adopted: bool = False

    @property
    def slat_time(self) -> float:
        """The slat phase, from the one press that measures it (0 until then).

        `opening` carries it once the full ascent has been measured too, because that
        is what the model wants; before then - between the two runs of the ascent - it
        is only on `slat_seconds`, and the check screen is showing it.
        """
        if self.opening is not None and self.opening.slat_time is not None:
            return self.opening.slat_time
        return self.slat_seconds or 0.0


@dataclass(slots=True)
class _Result:
    """What Save is about to write, and what the summary screen shows.

    `profile` is filled in by path A alone (it is the path that discovers a kind of
    shutter); `overrides` by the two paths that measure this window, A and C. Path B
    measures nothing but the height and writes no overrides at all - what it stores is
    the intent, `follows_profile` below, and the numbers are derived from the profile
    on every read (`calibration_store.resolve_cover`).
    """

    yaml: str
    profile: dict[str, float] | None = None
    overrides: dict[str, float] = field(default_factory=dict)
    accuracy_cm: float | None = None
    # True for path B: "this window is one of those, and I mean it more than the file
    # does". Stored as `profile_wins`, which is what puts the profile above the run
    # times the file writes for this cover and makes `Calibration source` name it.
    follows_profile: bool = False


class CalibrationContextMixin:
    """What both halves of the dialog need: the gateway, its covers, its profiles.

    Mixed into `MyHomeOptionsFlowHandler`, which supplies `hass`, `config_entry` and
    the loaded store.
    """

    hass: Any
    config_entry: Any
    _store_ref: CalibrationStore | None
    _changed: bool
    # The five origin phrases in the installation's language, read once per dialog by
    # `_async_load_origin_words`; `None` until then.
    _origin_words: dict[str, str] | None

    @property
    def _store(self) -> CalibrationStore:
        """The store this gateway is running on *now*, for reading.

        Never the object this dialog was handed when it opened. The entry is reloaded
        by plenty of things the dialog knows nothing about - the "Ricarica" button
        after an edit of `myhome.yaml`, a re-auth finishing, a *second* "Configura"
        dialog closing after a Save, which this release reloads on purpose - and each
        setup builds a new `CalibrationStore` from disk. A write through the old one
        serialises a snapshot from before the reload over everything written since
        (0.5.0 v2 review, BUG-3). The fall-back is for the moment of the reload
        itself, when the entry is unloaded and there is no live store to be had; every
        *write* re-fetches with `_async_store` instead, which reads the file rather
        than trusting anything held here.
        """
        return loaded_store(self.hass, self.config_entry) or self._store_ref  # type: ignore[return-value]

    async def _async_store(self) -> CalibrationStore:
        """The live store, fetched again before every write (see `_store`)."""
        self._store_ref = await async_get_store(self.hass, self.config_entry)
        return self._store_ref

    @property
    def _mac(self) -> str:
        return str(self.config_entry.data[CONF_MAC])

    def _covers(self) -> dict[str, dict[str, Any]]:
        """The basic covers of this gateway, by device key, or {} when it is not loaded.

        Advanced covers are left out on purpose and not merely disabled: they report
        their own position, so there is no travel model to calibrate and every runner
        primitive refuses them (`REASON_ADVANCED`).
        """
        gateway = self.hass.data.get(DOMAIN, {}).get(self._mac) or {}
        covers = (gateway.get(CONF_PLATFORMS) or {}).get(COVER) or {}
        return {key: cfg for key, cfg in covers.items() if not cfg.get(CONF_ADVANCED_SHUTTER)}

    def _cover_names(self) -> dict[str, str]:
        """Every basic cover of this gateway, as {unique id: the name it is known by}."""
        return {
            f"{self._mac}-{key}": str(cfg.get(CONF_NAME) or key)
            for key, cfg in self._covers().items()
        }

    def _cover_name(self, unique_id: str) -> str:
        """The name of one cover, or its unique id when it is not configured any more."""
        return self._cover_names().get(unique_id, unique_id)

    def _cover_config(self, unique_id: str) -> dict[str, Any]:
        for key, cfg in self._covers().items():
            if f"{self._mac}-{key}" == unique_id:
                return cfg
        return {}

    def _yaml_profiles(self) -> Mapping[str, Mapping[str, Any]]:
        gateway = self.hass.data.get(DOMAIN, {}).get(self._mac) or {}
        return gateway.get(CONF_COVER_PROFILES) or {}

    def _all_profiles(self) -> dict[str, Mapping[str, Any]]:
        """Both namespaces at once, exactly as a cover resolves them."""
        return merged_profiles(self._yaml_profiles(), self._store.profiles)

    def _assigned_profile(self, unique_id: str) -> str | None:
        """The profile this window follows today, from wherever it is said.

        The stored assignment first, then the `profile:` written in the file - which is
        what the assignment form has to preselect, because a form that opens on
        "Nessun profilo" for a cover the file assigns is telling the user something
        untrue about their own installation (0.5.0 v2 review, RISK-1).
        """
        stored = self._store.calibration(unique_id)
        if stored is not None and stored.profile:
            return str(stored.profile)
        name = self._cover_config(unique_id).get(CONF_PROFILE)
        return str(name) if name else None

    def _covers_following(self, name: str) -> tuple[list[str], list[str]]:
        """The shutters that follow a profile, split by where they were told to.

        Two sources, and the dialog used to count only the first: the assignment stored
        here (`calibration_store.covers_following`), and the `profile:` key written
        against the cover in the configuration file, which `validate.py` accepts and
        `cover.py` reads on every load. A profile three shutters follow through
        `myhome.yaml` and nobody assigned from this dialog read "0 covers" on the very
        screen that was about to delete it.

        A stored assignment outranks the file's key (`resolve_cover`), so a cover that
        has both is counted once, on the side that really decides. The two lists are
        kept apart because deleting the profile does different things to them: the
        assignment is stripped from the record, while the `profile:` line stays in the
        file and starts naming nothing - or names a `cover_profiles:` entry that was
        shadowed until now.
        """
        assigned = [self._cover_name(unique_id) for unique_id in self._store.covers_following(name)]
        from_file: list[str] = []
        for key, cfg in self._covers().items():
            if cfg.get(CONF_PROFILE) != name:
                continue
            stored = self._store.calibration(f"{self._mac}-{key}")
            if stored is not None and stored.profile:
                continue
            from_file.append(str(cfg.get(CONF_NAME) or key))
        return assigned, sorted(from_file)

    def _followers_with_origin(self, name: str) -> list[str]:
        """The shutters that follow one profile, each with where its numbers come from.

        "Covers following it" is a list of names on `profile_view`, and a name does not
        say whether that shutter is running on the profile whole or on the profile plus
        three numbers of its own - which is the question somebody looking at a profile's
        values is usually asking. The origin comes from `resolve_cover` through
        `_origin_in_words`, so it is the same answer the attribute gives.
        """
        assigned = list(self._store.covers_following(name))
        from_file = [
            f"{self._mac}-{key}"
            for key, cfg in self._covers().items()
            if cfg.get(CONF_PROFILE) == name
            and not (
                (stored := self._store.calibration(f"{self._mac}-{key}")) is not None
                and stored.profile
            )
        ]
        labelled = [
            f"{self._cover_name(unique_id)} ({origin})"
            if (origin := self._origin_in_words(unique_id))
            else self._cover_name(unique_id)
            for unique_id in assigned
        ]
        return labelled + sorted(
            f"{self._cover_name(unique_id)} ({origin})"
            if (origin := self._origin_in_words(unique_id))
            else self._cover_name(unique_id)
            for unique_id in from_file
        )

    def _own_height(self, unique_id: str) -> float | None:
        """The travel *this* window is known to have: its record's, else the file's.

        Never a profile's `reference_height`, which is another window's travel and
        would silently scale a newly assigned profile by the old one's reference.
        """
        stored = self._store.calibration(unique_id)
        if stored is not None and stored.height:
            return float(stored.height)
        cfg = self._cover_config(unique_id)
        if cfg.get(CONF_HEIGHT):
            return float(cfg[CONF_HEIGHT])
        return None

    def _known_height(self, unique_id: str) -> float | None:
        """The travel this window is already said to have, from wherever it is said.

        In the order the resolution uses it: what was measured on this window, then
        what the file says about it, then the reference height of the profile it
        follows. `None` when nobody has ever said - which is the one case the height
        screen falls back to a round 200.

        Only the guided height form uses the last of those three, and only as the
        number the field opens on, with the user standing in front of the window with
        a tape. Nothing is ever *stored* from it: see `_own_height`, which is what the
        assignment form asks.
        """
        own = self._own_height(unique_id)
        if own is not None:
            return own
        name = self._assigned_profile(unique_id)
        profile = self._all_profiles().get(name or "")
        if profile and profile.get(CONF_REFERENCE_HEIGHT):
            return float(profile[CONF_REFERENCE_HEIGHT])
        return None

    @callback
    def _mark_changed(self) -> None:
        """Something stored changed: the entry has to be rebuilt before we are done."""
        self._changed = True

    # ------------------------------------------------------- the origin, in words
    async def _async_load_origin_words(self) -> None:
        """Read the five origin phrases out of the translations, once per dialog.

        `description_placeholders` are substituted by the frontend into a text Home
        Assistant has already translated, so a phrase *this* side of the wire has to
        pick its own language: `hass.config.language`, which is the installation's,
        because the backend is never told which one the browser is showing. The
        alternative is a screen that says the same five things in English to everybody.

        A dialog asks for them once and keeps them: they cannot change while it is
        open, and every screen that prints an origin would otherwise ask again.
        """
        if self._origin_words is not None:
            return
        prefix = f"component.{DOMAIN}.selector.{CALIBRATION_ORIGIN_SELECTOR}.options."
        found = await async_get_translations(
            self.hass, self.hass.config.language, "selector", {DOMAIN}
        )
        self._origin_words = {
            key.removeprefix(prefix): text
            for key, text in found.items()
            if key.startswith(prefix)
        }

    @callback
    def _origin_in_words(self, unique_id: str) -> str:
        """Where this cover's numbers come from today, as a screen says it.

        The same question `Calibration source` answers and the same answer:
        `resolve_cover` decides which of the five it is, here and for the attribute, so
        a screen cannot call a shutter measured while its attribute calls it adjusted.
        The token itself is the fall-back - a dialog that never loaded the phrases
        (nothing in this release opens one without `async_step_init`) says `guided`
        rather than nothing at all.
        """
        device = self._cover_config(unique_id)
        if not device:
            return ""
        resolved = resolve_cover(
            device,
            profiles=self._all_profiles(),
            calibration=self._store.calibration(unique_id),
        )
        words = self._origin_words or {}
        # `replace` and not `format`: a profile name is matched against
        # `PROFILE_NAME_PATTERN` before it is stored, but a name out of `myhome.yaml`
        # reaches this screen unfiltered, and a stray brace in it must not be able to
        # turn a label into a `KeyError` three screens deep.
        return words.get(resolved.origin, resolved.source).replace(
            CALIBRATION_ORIGIN_PROFILE_SLOT, resolved.profile or ""
        )


# ------------------------------------------------------------------ management
class CalibrationManagementMixin(CalibrationContextMixin):
    """Everything under "Configura" that does not move a shutter.

    Three sections, each of which ends by coming back to the menu it came from, so the
    dialog is never a dead end: the profiles and who follows them, the calibrations of
    individual shutters, and (in `config_flow.py`, because it is not about covers at
    all) the gateway's own settings.
    """

    _profile_name: str | None
    _cover_unique_id: str | None

    # ------------------------------------------------------------ profiles & covers
    async def async_step_profiles_covers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The section menu: who follows what, and what the profiles say."""
        options = ["assign_covers"]
        if self._all_profiles():
            options.append("pick_profile")
        options.append("init")
        return self.async_show_menu(
            step_id="profiles_covers",
            menu_options=options,
            description_placeholders={
                "profiles": str(len(self._all_profiles())),
                "covers": str(len(self._covers())),
            },
        )

    async def async_step_assign_covers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """One select per shutter: which kind of shutter it is, or none.

        Assigning is not measuring. A shutter given a profile runs on that profile's
        numbers scaled to its own height, which is exactly what the second window of a
        kind needs and no help at all to a window nothing has been measured on - hence
        the follow-up form for the heights nobody knows yet.
        """
        fields = self._cover_fields()
        if not fields:
            return await self.async_step_no_basic_covers()
        # A profile the *file* calls `no_profile` would otherwise put the sentinel in
        # the list twice; `async_step_profile_name` refuses the name, so the file is the
        # only door it can come through.
        names = sorted(name for name in self._all_profiles() if name != NO_PROFILE)
        if user_input is not None:
            assignments: dict[str, tuple[str | None, float | None]] = {}
            for label, unique_id in fields.items():
                chosen = user_input.get(label, NO_PROFILE)
                profile = None if chosen == NO_PROFILE else str(chosen)
                current = self._assigned_profile(unique_id)
                # The second half is the window that follows a profile the select
                # cannot offer, because the *file* called that profile like the
                # sentinel: the row opens on "Nessun profilo" for want of anything else
                # to show, so submitting the form untouched must not be read as an
                # instruction to take the assignment away. Such a profile can only be
                # given from path B, and only ever taken back from "Calibrazioni".
                if profile == current or (profile is None and current == NO_PROFILE):
                    # This row was left as it was. Collecting it anyway wrote a record
                    # for every shutter the form had ever shown - stamped `guided`,
                    # listed under "Calibrazioni" as something measured, and (with a
                    # height copied out of the file) shadowing that very file for ever
                    # - after a screen on which the user changed nothing, and it
                    # reloaded the gateway to do it (0.5.0 v2 review, BUG-2).
                    continue
                # Never a height: what this window's own is, the resolution already
                # knows (the record's, else the file's). A height *invented* here from
                # the reference height of the profile being assigned would scale the
                # new profile by another window's travel.
                assignments[unique_id] = (profile, None)
            self._pending_assignments = assignments
            missing = [
                unique_id
                for unique_id, (profile, _height) in assignments.items()
                if profile is not None and self._own_height(unique_id) is None
            ]
            if missing:
                self._missing_heights = missing
                return await self.async_step_assign_heights()
            return await self._async_write_assignments()
        schema = {}
        for label, unique_id in fields.items():
            current = self._assigned_profile(unique_id) or NO_PROFILE
            if current not in (*names, NO_PROFILE):
                current = NO_PROFILE
            schema[vol.Required(label, description={"suggested_value": current})] = SelectSelector(
                SelectSelectorConfig(
                    options=[NO_PROFILE, *names],
                    mode=SelectSelectorMode.DROPDOWN,
                    custom_value=False,
                    # Only `no_profile` is translated; a profile name has no text of its
                    # own and Home Assistant falls back to showing the value itself,
                    # which is the name the user gave it.
                    translation_key="profile_choice",
                )
            )
        return self.async_show_form(
            step_id="assign_covers",
            data_schema=vol.Schema(schema),
            # Not the bare list of names: this is the screen that *changes* where a
            # cover's numbers come from, so it says where each one's come from now.
            description_placeholders={
                "covers": ", ".join(
                    f"{label} ({origin})" if (origin := self._origin_in_words(unique_id)) else label
                    for label, unique_id in fields.items()
                )
            },
        )

    def _cover_fields(self) -> dict[str, str]:
        """{the label of a form field: the cover it is about}.

        The fields of these two forms are one per shutter, so their names cannot live
        in `strings.json` - there is no way to translate a key that only exists on one
        installation. Home Assistant shows the key itself when it finds no text for it,
        so the key *is* the shutter's name; a name two shutters share is told apart by
        the address on the bus, because a form with the same label twice is a form
        whose answers cannot be attributed.
        """
        fields: dict[str, str] = {}
        for key, cfg in self._covers().items():
            name = str(cfg.get(CONF_NAME) or key)
            label = name if name not in fields else f"{name} ({key})"
            fields[label] = f"{self._mac}-{key}"
        return fields

    async def async_step_assign_heights(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The heights of the shutters that were just given a profile and have none.

        A profile is a shutter of a certain height; it is scaled to every other window
        by the ratio of the two. Without this window's own height there is nothing to
        scale by, and the profile would be applied as if every window were the one it
        was measured on.
        """
        missing = self._missing_heights
        fields = {
            label: unique_id
            for label, unique_id in self._cover_fields().items()
            if unique_id in missing
        }
        errors: dict[str, str] = {}
        if user_input is not None:
            heights: dict[str, float] = {}
            for label, unique_id in fields.items():
                value = parse_number(user_input.get(label))
                if value is None:
                    errors[label] = ERROR_NOT_A_NUMBER
                elif not MIN_HEIGHT_CM <= value <= MAX_HEIGHT_CM:
                    errors[label] = ERROR_OUT_OF_RANGE
                else:
                    heights[unique_id] = value
            if not errors:
                for unique_id, height in heights.items():
                    profile, _ = self._pending_assignments[unique_id]
                    self._pending_assignments[unique_id] = (profile, height)
                return await self._async_write_assignments()
        schema = {
            vol.Required(
                label, description={"suggested_value": (user_input or {}).get(label, "")}
            ): _text_field()
            for label in fields
        }
        return self.async_show_form(
            step_id="assign_heights",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={"covers": ", ".join(fields)},
        )

    async def _async_write_assignments(self) -> ConfigFlowResult:
        store = await self._async_store()
        if self._pending_assignments and await store.async_set_assignments(self._pending_assignments):
            self._mark_changed()
        self._pending_assignments = {}
        self._missing_heights = []
        return await self.async_step_profiles_covers()

    # ------------------------------------------------------------ one profile
    async def async_step_pick_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Which profile the next three screens are about."""
        names = sorted(self._all_profiles())
        if not names:
            return await self.async_step_profiles_covers()
        if user_input is not None:
            self._profile_name = str(user_input[FIELD_PROFILE])
            return await self.async_step_profile_actions()
        return self.async_show_form(
            step_id="pick_profile",
            data_schema=vol.Schema(
                {vol.Required(FIELD_PROFILE, default=names[0]): vol.In(names)}
            ),
        )

    def _profile_placeholders(self) -> dict[str, str]:
        name = self._profile_name or ""
        assigned, from_file = self._covers_following(name)
        followers = assigned + from_file
        stored = self._store.profile(name)
        return {
            "profile": name,
            "covers": ", ".join(followers) if followers else "",
            "values": describe_profile(name, stored or dict(self._all_profiles().get(name) or {})),
            "count": str(len(followers)),
            "assigned": str(len(assigned)),
            "from_file": str(len(from_file)),
            # The same list again, with each shutter's origin after its name. Only
            # "Vedi i valori" prints it: the screens that are about to *delete* the
            # profile name the shutters plainly, because there the question is which
            # ones lose it and not what each of them is running on today.
            "followers": ", ".join(self._followers_with_origin(name)),
        }

    async def async_step_profile_actions(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """What can be done with one profile, once it is chosen."""
        options = ["profile_view"]
        # A profile written in `myhome.yaml` is the file's, and the file is the user's:
        # the dialog shows it and leaves it alone.
        if self._store.profile(self._profile_name or "") is not None:
            options += ["profile_edit", "profile_delete"]
        options.append("profiles_covers")
        return self.async_show_menu(
            step_id="profile_actions",
            menu_options=options,
            description_placeholders=self._profile_placeholders(),
        )

    async def async_step_profile_view(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The stored numbers, and the shutters that follow them."""
        if user_input is not None:
            return await self.async_step_profile_actions()
        return self.async_show_form(
            step_id="profile_view",
            data_schema=vol.Schema({}),
            description_placeholders=self._profile_placeholders(),
        )

    async def async_step_profile_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The six numbers of a profile, by hand.

        Editing rather than re-measuring is for the user who knows what their shutter
        does - who has the manufacturer's run times, or who watched the guided
        calibration land half a second out and wants to say so. Every field is
        validated against the range the configuration schema would have applied.
        """
        name = self._profile_name or ""
        stored = self._store.profile(name) or {}
        errors: dict[str, str] = {}
        if user_input is not None:
            values: dict[str, float] = {}
            for key, low, high in PROFILE_FIELDS:
                value = parse_number(user_input.get(key))
                if value is None:
                    errors[key] = ERROR_NOT_A_NUMBER
                elif not low <= value <= high:
                    errors[key] = ERROR_OUT_OF_RANGE
                else:
                    values[key] = value
            if not errors:
                store = await self._async_store()
                await store.async_set_profile(
                    name,
                    cover_profile_data(
                        name,
                        reference_height=values[CONF_REFERENCE_HEIGHT],
                        opening_time=values[CONF_OPENING_TIME],
                        closing_time=values[CONF_CLOSING_TIME],
                        slat_time=values[CONF_SLAT_TIME],
                        opening_roll=values[CONF_OPENING_ROLL],
                        closing_roll=values[CONF_CLOSING_ROLL],
                        reference_cover=stored.get(CONF_REFERENCE_COVER),
                        # A hand edit re-stamps `measured_at` - it is the date the
                        # numbers were last stated, and they have just been stated -
                        # and clears nothing else: the window they were measured on is
                        # still the window they were measured on.
                        measured_on=stored.get(CONF_MEASURED_ON),
                        source=stored.get(CONF_SOURCE) or CALIBRATION_SOURCE_MANUAL,
                        raw=stored.get(CONF_RAW),
                    ),
                )
                self._mark_changed()
                return await self.async_step_profile_actions()
        current = user_input or stored
        schema = {
            vol.Required(
                key, description={"suggested_value": _as_text(current.get(key))}
            ): _text_field()
            for key, _low, _high in PROFILE_FIELDS
        }
        return self.async_show_form(
            step_id="profile_edit",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders=self._profile_placeholders(),
        )

    async def async_step_profile_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask first, and name the shutters that are about to lose the profile."""
        return self.async_show_menu(
            step_id="profile_delete",
            menu_options=["profile_delete_confirm", "profile_actions"],
            description_placeholders=self._profile_placeholders(),
        )

    async def async_step_profile_delete_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete it, and say which shutters went back to the file."""
        name = self._profile_name or ""
        store = await self._async_store()
        had_it = store.profile(name) is not None
        # Read before the deletion: `async_remove_profile` strips the assignment, so
        # afterwards there is nothing left to count on that side, and the shutters that
        # follow through the file's own `profile:` key are never in `orphans` at all.
        _assigned, from_file = self._covers_following(name)
        orphans = await store.async_remove_profile(name)
        if orphans or had_it:
            self._mark_changed()
        LOGGER.info(
            "Cover profile '%s' deleted; %s shutter(s) lost the assignment and %s "
            "follow(ed) it through the configuration file",
            name,
            len(orphans),
            len(from_file),
        )
        self._deleted = name
        self._deleted_assigned = [self._cover_name(unique_id) for unique_id in orphans]
        self._deleted_from_file = from_file
        self._deleted_covers = self._deleted_assigned + from_file
        return await self.async_step_profile_deleted()

    async def async_step_profile_deleted(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """What just happened, before going back to the list."""
        if user_input is not None:
            self._profile_name = None
            return await self.async_step_profiles_covers()
        return self.async_show_form(
            step_id="profile_deleted",
            data_schema=vol.Schema({}),
            description_placeholders={
                "profile": self._deleted,
                "covers": ", ".join(self._deleted_covers) if self._deleted_covers else "",
                "count": str(len(self._deleted_covers)),
                "assigned": str(len(self._deleted_assigned)),
                "from_file": str(len(self._deleted_from_file)),
            },
        )

    # ------------------------------------------------------------ one calibration
    async def async_step_calibrations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Which shutter's own measurements the next screens are about."""
        # The entry is the shutter's name and, after it, where the model it runs on
        # comes from: the list is read to find the shutter whose numbers are wrong, and
        # "measured" against "adjusted from profile tall" is most of that answer before
        # the user has opened anything.
        stored = {
            unique_id: f"{self._cover_name(unique_id)} - {origin}"
            if (origin := self._origin_in_words(unique_id))
            else self._cover_name(unique_id)
            for unique_id, record in self._store.calibrations.items()
            if record.says_anything
        }
        if not stored:
            return await self.async_step_no_calibrations()
        if user_input is not None:
            self._cover_unique_id = str(user_input[FIELD_COVER])
            return await self.async_step_calibration_actions()
        return self.async_show_form(
            step_id="calibrations",
            data_schema=vol.Schema({vol.Required(FIELD_COVER): vol.In(stored)}),
            description_placeholders={"count": str(len(stored))},
        )

    async def async_step_no_calibrations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Nothing has been measured yet, said in one screen rather than an empty list."""
        return self.async_show_menu(step_id="no_calibrations", menu_options=["init"])

    async def async_step_no_basic_covers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Every cover of this gateway reports its own position: nothing to calibrate."""
        return self.async_show_menu(step_id="no_basic_covers", menu_options=["init"])

    def _calibration_placeholders(self) -> dict[str, str]:
        unique_id = self._cover_unique_id or ""
        record = self._store.calibration(unique_id)
        lines: list[str] = []
        if record is not None:
            if record.profile:
                lines.append(f"{CONF_PROFILE}: {record.profile}")
            if record.follows_a_profile:
                # Shown because it is a precedence and not a detail: this is the line
                # that says the profile beats what the file writes for this cover.
                lines.append(f"{CONF_PROFILE_WINS}: true")
            if record.height is not None:
                lines.append(f"{CONF_HEIGHT}: {round(record.height, 1)}")
            lines += [f"{key}: {round(value, 2)}" for key, value in record.overrides.items()]
        return {
            "cover": self._cover_name(unique_id),
            "values": "```yaml\n" + "\n".join(lines or ["-"]) + "\n```",
            "profile": (record.profile if record and record.profile else ""),
            "measured_at": (record.measured_at if record and record.measured_at else ""),
            # What the block above *amounts to*: the keys are what is stored, and this
            # is what the shutter runs on once the profile and the file have had their
            # say. The two screens that show the keys say it; the edit and the delete
            # are given it and do not.
            "origin": self._origin_in_words(unique_id),
        }

    async def async_step_calibration_actions(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """What can be done with one shutter's measurements."""
        return self.async_show_menu(
            step_id="calibration_actions",
            menu_options=[
                "calibration_view",
                "calibration_edit",
                "calibration_remeasure",
                "calibration_delete",
                "calibrations",
            ],
            description_placeholders=self._calibration_placeholders(),
        )

    async def async_step_calibration_view(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """What is stored for this shutter, as it is stored."""
        if user_input is not None:
            return await self.async_step_calibration_actions()
        return self.async_show_form(
            step_id="calibration_view",
            data_schema=vol.Schema({}),
            description_placeholders=self._calibration_placeholders(),
        )

    async def async_step_calibration_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The height and the overrides of one shutter, by hand.

        Every travel field is optional and an empty one means "no override": that is
        how a number measured by mistake is taken back out without deleting the whole
        record and the profile assignment with it.
        """
        unique_id = self._cover_unique_id or ""
        record = self._store.calibration(unique_id)
        # The measurements the guided conversation kept for a human to argue with six
        # months later. Correcting one number by hand is not a reason to forget how the
        # other five were arrived at - and since 0.6.0 it is also where the panel reads
        # how thorough that calibration was and what the tape check came to, so dropping
        # the block emptied two columns of a screen that never asked for a correction.
        # Carried over exactly as the panel's own hand edit carries it.
        measurements = (self._store.raw_covers.get(unique_id) or {}).get(CONF_RAW)
        errors: dict[str, str] = {}
        if user_input is not None:
            height = parse_number(user_input.get(CONF_HEIGHT))
            if user_input.get(CONF_HEIGHT) and height is None:
                errors[CONF_HEIGHT] = ERROR_NOT_A_NUMBER
            elif height is not None and not MIN_HEIGHT_CM <= height <= MAX_HEIGHT_CM:
                errors[CONF_HEIGHT] = ERROR_OUT_OF_RANGE
            overrides: dict[str, float] = {}
            for key, low, high in CALIBRATION_FIELDS:
                raw = user_input.get(key)
                if not str(raw or "").strip():
                    continue
                value = parse_number(raw)
                if value is None:
                    errors[key] = ERROR_NOT_A_NUMBER
                elif not low <= value <= high:
                    errors[key] = ERROR_OUT_OF_RANGE
                else:
                    overrides[key] = value
            if not errors:
                data = cover_calibration_data(
                    unique_id,
                    profile=record.profile if record else None,
                    # Correcting a number by hand says nothing about which kind of
                    # shutter this is: a window that was told to follow a profile goes
                    # on following it, and the keys typed here sit above it exactly as
                    # measured ones would.
                    profile_wins=bool(record and record.profile_wins),
                    height=height,
                    overrides=overrides or None,
                    source=CALIBRATION_SOURCE_MANUAL,
                    raw=measurements,
                )
                store = await self._async_store()
                if stored_calibration(data).says_anything:
                    await store.async_set_calibration(unique_id, data)
                else:
                    # Every field cleared: that is "forget what you know about this
                    # shutter", not "remember nothing about it". A record holding only
                    # a `source` and a timestamp is invisible on the "Calibrazioni"
                    # screen (which lists what `says_anything`) and immortal in
                    # `.storage` (0.5.0 v2 review, RISK-3) - the assignment writer has
                    # deleted such a record all along.
                    await store.async_remove_calibration(unique_id)
                self._mark_changed()
                return await self.async_step_calibration_actions()
        current: Mapping[str, Any] = user_input or {
            CONF_HEIGHT: record.height if record else None,
            **(dict(record.overrides) if record else {}),
        }
        schema = {
            vol.Optional(
                CONF_HEIGHT, description={"suggested_value": _as_text(current.get(CONF_HEIGHT))}
            ): _text_field()
        }
        for key, _low, _high in CALIBRATION_FIELDS:
            schema[
                vol.Optional(key, description={"suggested_value": _as_text(current.get(key))})
            ] = _text_field()
        return self.async_show_form(
            step_id="calibration_edit",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders=self._calibration_placeholders(),
        )

    async def async_step_calibration_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask before throwing a measurement away; it cannot be got back by thinking."""
        return self.async_show_menu(
            step_id="calibration_delete",
            menu_options=["calibration_delete_confirm", "calibration_actions"],
            description_placeholders=self._calibration_placeholders(),
        )

    async def async_step_calibration_delete_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete it: this shutter goes back to the configuration file."""
        unique_id = self._cover_unique_id or ""
        self._deleted_covers = [self._cover_name(unique_id)]
        store = await self._async_store()
        if await store.async_remove_calibration(unique_id):
            self._mark_changed()
        LOGGER.info("The stored calibration of %s was deleted", self._deleted_covers[0])
        return await self.async_step_calibration_deleted()

    async def async_step_calibration_deleted(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """What just happened, before going back to the list."""
        if user_input is not None:
            self._cover_unique_id = None
            return await self.async_step_calibrations()
        return self.async_show_form(
            step_id="calibration_deleted",
            data_schema=vol.Schema({}),
            description_placeholders={"cover": self._deleted_covers[0] if self._deleted_covers else ""},
        )

    async def async_step_calibration_remeasure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Measure this shutter again: the guided conversation, on the cover named here."""
        unique_id = self._cover_unique_id or ""
        self._release()
        self._reset_calibration()
        if (reason := self._claim(unique_id)) is not None:
            return await self._async_claim_refused(reason)
        # The travel this window is already known to have is seeded in one place, by
        # the one path that does not measure it (`async_step_path_c`): a refinement
        # reached from here starts from it exactly as one reached from the menu does,
        # and paths A and B measure it themselves.
        return await self.async_step_path()


def _as_text(value: Any) -> str:
    """A stored number as a field is pre-filled with it (and an absent one as "")."""
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


# ------------------------------------------------------------------ the guided flow
class GuidedCalibrationMixin(CalibrationContextMixin):
    """The guided calibration of one basic cover, screen by screen."""

    # ------------------------------------------------------------------ state
    @callback
    def _reset_calibration(self) -> None:
        """Forget one conversation, so the next one starts where the first did."""
        self._cover: Any = None
        self._cover_unique_id = None
        self._cover_key: str = ""
        self._cover_label: str = ""
        self._path: str = PATH_FIRST
        self._plan: list[str] = []
        self._index: int = 0
        self._measured = _Measured()
        self._profile: str | None = None
        self._measured_name: str | None = None
        self._task: Any = None
        self._error: str | None = None
        self._stop_first: bool = False
        self._motor_start: datetime | None = None
        self._lift_off: datetime | None = None
        self._stop_delivered: datetime | None = None
        self._motor_stopped: datetime | None = None
        self._shown_at: datetime | None = None
        self._report: RunReport | None = None
        self._pending: tuple[str, float] | None = None
        # The step a run to a percentage hands over to, remembered because the run is a
        # screen of its own and no longer the stage's.
        self._after_the_run: str = "measure_descent"
        # The end stop the shutter is standing at, `None` when it is between the two.
        # What the order of a tape phase is drawn from (`order_the_readings`).
        self._at: str | None = None
        self._yaml_key: str = ""
        self._expired: bool = False
        self._claim_refused: str | None = None
        self._tape_target: str | None = None

    # ---------------------------------------------------------------- the watchdog
    # Every screen restarts the clock. Overriding the three `async_show_*` is what
    # makes that exhaustive: a step added later cannot forget to do it, because there
    # is no other way for this flow to put anything in front of a user.
    @callback
    def async_show_form(self, *args: Any, **kwargs: Any) -> ConfigFlowResult:
        """A form, and one more stretch of patience."""
        self._touch()
        return super().async_show_form(*args, **kwargs)

    @callback
    def async_show_menu(self, *args: Any, **kwargs: Any) -> ConfigFlowResult:
        """A menu, and one more stretch of patience."""
        self._touch()
        return super().async_show_menu(*args, **kwargs)

    @callback
    def async_show_progress(self, *args: Any, **kwargs: Any) -> ConfigFlowResult:
        """A progress bar: a movement is activity too, and a short-lived kind."""
        self._touch()
        return super().async_show_progress(*args, **kwargs)

    @callback
    def _touch(self) -> None:
        """Restart the watchdog: somebody is still having this conversation."""
        if self._cover is None:
            # Nothing has been claimed yet, so there is nothing to give back.
            return
        timeout, self._idle_timeout = self._idle_timeout, IDLE_TIMEOUT_SEC
        self._disarm()
        self._watchdog = async_call_later(self.hass, timeout, self._async_session_expired)

    # -------------------------------------------------------------- the live cover
    def _live_cover(self) -> Any:
        """The entity of the cover being calibrated, looked up again right now.

        Not the object `_claim` took hold of. A config entry that is reloaded while a
        conversation is open - the "Ricarica" button, a re-auth, a second "Configura"
        dialog closing after a Save - tears every cover entity down and builds new
        ones, and Home Assistant cancels no flow when it does (0.5.0 v2 review,
        BUG-4). The old object then drives frames into a gateway handler whose sessions
        are closed, leaves the *live* shutter unmarked (so `set_cover_position` is free
        to run the same motor), and restarts a 1 Hz position tick nothing will cancel.
        """
        unique_id = self._cover_unique_id or ""
        for key, cfg in self._covers().items():
            if f"{self._mac}-{key}" == unique_id:
                return (cfg.get(CONF_ENTITIES) or {}).get(COVER)
        return None

    def _cover_to_drive(self) -> Any:
        """The live cover, or a refusal that has a screen of its own."""
        cover = self._live_cover()
        if cover is None:
            raise CalibrationError(
                REASON_UNKNOWN_COVER,
                f"{self._cover_label} is not configured on this gateway any more",
            )
        self._cover = cover
        return cover

    @callback
    def _disarm(self) -> None:
        if self._watchdog is not None:
            self._watchdog()
            self._watchdog = None

    @callback
    def async_remove(self) -> None:
        """Let the shutter go when the dialog closes, however it closed.

        The whole conversation holds one calibration session on the cover (so the
        `Calibrating` attribute does not blink off between two screens while the user
        reads one), and a flow that is abandoned - the X, a browser closed, a timeout -
        gets no other chance to give it back.
        """
        self._disarm()
        self._release()

    @callback
    def _release(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    async def _async_session_expired(self, _now: datetime) -> None:
        """Give the shutter back: nobody has touched this dialog for a long time.

        The flow itself is **not** aborted. Home Assistant answers a request against a
        flow it has forgotten with "Invalid flow specified", which is what the first
        live walk-through got - in the middle of reading the second screen, because the
        timer of a screen with nothing moving used to be ten minutes. So the session is
        released and the shutter stopped, the conversation is marked expired, and the
        next thing the user does lands on a screen that says so and offers to start
        again (`_guarded`, below).
        """
        self._watchdog = None
        self._expired = True
        cover = self._cover
        LOGGER.warning(
            "Guided calibration of %s: nothing happened for a long time, so the shutter "
            "is being given back. Nothing was saved; start again to measure it",
            self._cover_label,
        )
        self._release()
        self._cover = None
        await self._async_stop_if_moving(self._live_cover() or cover)

    async def _async_stop_if_moving(self, cover: Any) -> None:
        """Stop a shutter that is still running as the conversation ends under it.

        Both ways a conversation can end without the user - the watchdog and an unload
        of the entry - go through this, because the two used to differ silently: one
        stopped the shutter and the other only let go of it, while `cancelled` and
        `expired` both say "la tapparella è dove l'ha lasciata l'ultimo movimento"
        (final review, RISK-C).
        """
        if cover is None or not (cover.is_opening or cover.is_closing):
            return
        with contextlib.suppress(HomeAssistantError):
            await cover.async_calib_stop()

    async def async_step_expired(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """What the user finds when they come back to a dialog that timed out."""
        return self.async_show_menu(
            step_id="expired",
            menu_options=["calibrate", "init"],
            description_placeholders={"cover": self._cover_label},
        )

    # ------------------------------------------------------------------ claiming
    @callback
    def _claim(self, unique_id: str) -> str | None:
        """Take hold of one cover for the rest of the conversation.

        Answers with the reason it could not, or None when the shutter is ours. A cover
        that is already being calibrated - a second browser tab on the same shutter, or
        the 0.4.2 service in the middle of a run - is refused here rather than half way
        through the first movement, because that is the only moment at which the user
        has not yet been asked to do anything.
        """
        for key, cfg in self._covers().items():
            if f"{self._mac}-{key}" != unique_id:
                continue
            entity = (cfg.get(CONF_ENTITIES) or {}).get(COVER)
            if entity is None:
                return REASON_UNKNOWN_COVER
            if entity.calibrating:
                return REASON_ALREADY_CALIBRATING
            self._cover = entity
            self._cover_unique_id = unique_id
            self._cover_key = key
            self._yaml_key = str(cfg.get(CONF_YAML_KEY) or "")
            self._cover_label = str(cfg.get(CONF_NAME) or entity.entity_id)
            self._session = contextlib.ExitStack()
            self._session.enter_context(entity.calibration_session())
            self._watch_for_unload()
            return None
        return REASON_UNKNOWN_COVER

    @callback
    def _watch_for_unload(self) -> None:
        """Expire this conversation if the entry is unloaded (or reloaded) under it.

        Home Assistant never cancels a flow when a config entry is reloaded, and this
        release reloads on purpose whenever a dialog that stored something is closed -
        including a *second* dialog, opened on another shutter while this conversation
        was half way through. The expiry screen is exactly the right thing to find
        afterwards: it says nothing was saved and offers to start again.

        `ConfigEntry.async_on_unload` hands back no way to unregister, so the callback
        outlives the conversation - but the list it goes on is drained by the very
        unload that runs it, and the callback's first question is whether there is a
        conversation left to expire.
        """
        if self._unload_watched:
            return
        self._unload_watched = True
        self.config_entry.async_on_unload(self._async_entry_unloaded)

    @callback
    def _async_entry_unloaded(self) -> None:
        """The gateway went away: give the shutter back and stop the clock."""
        self._unload_watched = False
        if self._cover is None:
            return
        LOGGER.info(
            "Guided calibration of %s: the gateway was reloaded, so this conversation "
            "was ended. Nothing was saved; start again to measure it",
            self._cover_label,
        )
        self._expired = True
        self._disarm()
        cover = self._live_cover() or self._cover
        self._release()
        self._cover = None
        # A free run is heading for an end stop anyway and the gateway is being torn
        # down, so this may well not reach the bus - but a conversation that ends with
        # the shutter moving must have *tried* to stop it, exactly as the watchdog
        # does (final review, RISK-C). Scheduled rather than awaited: `async_on_unload`
        # callbacks are synchronous.
        if cover is not None and (cover.is_opening or cover.is_closing):
            self.hass.async_create_task(
                self._async_stop_if_moving(cover),
                "myhome calibration stop on unload",
                eager_start=False,
            )

    async def _async_claim_refused(self, reason: str) -> ConfigFlowResult:
        """Say why the shutter could not be taken, with a way back to the menu."""
        self._claim_refused = reason
        return await self.async_step_claim_refused()

    async def async_step_claim_refused(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """One screen for both reasons: the shutter is not ours to move right now.

        Given `_placeholders()` like every other screen of the conversation. Neither
        text names the shutter today, but a translation that did would be rendered by
        formatjs as "[formatjs Error: MISSING_VALUE]" instead - a whole screen lost to
        one brace (final review).
        """
        return self.async_show_menu(
            step_id=f"refused_{self._claim_refused}",
            menu_options=["calibrate", "init"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_refused_unknown_cover(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The cover named by a stored calibration is not configured any more."""
        self._claim_refused = REASON_UNKNOWN_COVER
        return await self.async_step_claim_refused()

    async def async_step_refused_already_calibrating(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Something else is already calibrating this shutter."""
        self._claim_refused = REASON_ALREADY_CALIBRATING
        return await self.async_step_claim_refused()

    # ------------------------------------------------------------------ the entrance
    async def async_step_calibrate(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """What the tool is for, and what to expect from it, before any choice.

        A user who arrives here deserves to know that the percentage of a basic cover
        is an estimate, that the calibration makes it a good one rather than a perfect
        one, and that the covers which report their own position are missing from the
        list because they do not need this.
        """
        self._disarm()
        self._release()
        self._reset_calibration()
        if not self._covers():
            return await self.async_step_no_basic_covers()
        return self.async_show_menu(step_id="calibrate", menu_options=["cover", "init"])

    async def async_step_cover(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pick the shutter. Only the basic ones are listed (see `_covers`)."""
        covers = self._cover_names()
        if user_input is not None:
            if (reason := self._claim(user_input[FIELD_COVER])) is not None:
                return await self._async_claim_refused(reason)
            return await self.async_step_path()
        return self.async_show_form(
            step_id="cover",
            data_schema=vol.Schema({vol.Required(FIELD_COVER): vol.In(covers)}),
        )

    def _placeholders(self, **extra: Any) -> dict[str, str]:
        """Every screen names the shutter it is about; the rest is per step."""
        return {"cover": self._cover_label, **{key: str(value) for key, value in extra.items()}}

    async def async_step_path(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The three paths - the last two only once there is a profile to follow."""
        options = [PATH_FIRST]
        if self._all_profiles():
            options += [PATH_PROFILE, PATH_REFINE]
        options.append("cancel_flow")
        return self.async_show_menu(
            step_id="path", menu_options=options, description_placeholders=self._placeholders()
        )

    # ------------------------------------------------------------------ path A
    async def async_step_path_a(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The warning before the first movement: the shutter is about to run, twice over."""
        if user_input is not None:
            self._path = PATH_FIRST
            self._measured = _Measured()
            return await self._async_start_plan(PLAN_FULL)
        return self.async_show_menu(
            step_id="path_a",
            menu_options=["begin", "cancel_flow"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_begin(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """"Ho capito, cominciamo": the one menu option of the warning screen."""
        return await self.async_step_path_a({})

    # ------------------------------------------------------------------ path B
    async def async_step_path_b(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """This window is one of a kind already measured: name the kind."""
        profiles = sorted(self._all_profiles())
        if not profiles:
            return await self.async_step_path()
        if user_input is not None:
            self._path = PATH_PROFILE
            self._profile = user_input[CONF_PROFILE]
            self._measured = _Measured()
            return await self._async_start_plan(PLAN_PROFILE)
        return self.async_show_form(
            step_id="path_b",
            data_schema=vol.Schema({vol.Required(CONF_PROFILE, default=profiles[0]): vol.In(profiles)}),
            description_placeholders=self._placeholders(),
        )

    # ------------------------------------------------------------------ path C
    async def async_step_path_c(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """This window follows a profile and gets it wrong: measure what it needs."""
        profiles = sorted(self._all_profiles())
        if not profiles:
            return await self.async_step_path()
        if user_input is not None:
            self._path = PATH_REFINE
            self._profile = user_input[CONF_PROFILE]
            # A height already measured (path B's check sent us here) is kept: it is
            # the same window and the same tape. Entered from the menu instead, the
            # travel this window is already *known* to have is what the conversation
            # starts from - the summary would otherwise show "-" for it and the Save
            # would write a record that has forgotten it (final review, BUG-A).
            measured_here = self._measured.height is not None and self._measured.height_measured
            self._measured = _Measured(
                height=self._measured.height or self._own_height(self._cover_unique_id or ""),
                height_measured=measured_here,
            )
            return await self.async_step_refine_scope()
        current = self._profile or self._current_profile() or profiles[0]
        return self.async_show_form(
            step_id="path_c",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PROFILE, default=current if current in profiles else profiles[0]
                    ): vol.In(profiles)
                }
            ),
            description_placeholders=self._placeholders(),
        )

    def _current_profile(self) -> str | None:
        """The profile this cover follows today, stored one first, then the file's."""
        return self._assigned_profile(self._cover_unique_id or "")

    async def async_step_refine_scope(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """How far to go: its own times, its own roll coefficients, or the readings alone.

        The third scope is the one the live installation asked for. A cover that has
        already been corrected - its own times and its own coefficients stored - had no
        way at all to the thorough calibration: that level hung off the summary of path
        A and nowhere else, so the only way to the four extra readings was to time the
        three runs again. `points_only` keeps every time the cover already moves on and
        runs the tape phase over them.
        """
        return self.async_show_menu(
            step_id="refine_scope",
            menu_options=["times_only", "times_and_rolls", "points_only", "cancel_flow"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_times_only(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Two presses: this motor is slower (or faster) than the profile's."""
        return await self._async_start_plan(PLAN_TIMES)

    async def async_step_times_and_rolls(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Two presses and two tape readings: this curtain winds differently too."""
        return await self._async_start_plan(PLAN_TIMES_AND_ROLLS)

    async def async_step_points_only(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The thorough calibration alone: no timed run, four readings and the check.

        Nothing is pressed for here, so there is nothing for the conversation to time:
        the run times and the slat phase it starts from are the ones the cover moves on
        today, and the four readings refit the two roll coefficients and the scale of
        those times over them. The one way the model cannot be put together is a cover
        that is not in this gateway's configuration any more - the entry was reloaded
        off an edited `myhome.yaml` while the dialog stood open - and that is the screen
        the conversation already has for it.
        """
        if not self._adopt_the_model_in_use():
            return await self._async_claim_refused(REASON_UNKNOWN_COVER)
        return await self._async_start_thorough(from_here=False)

    @callback
    def _values_in_use(self) -> dict[str, float] | None:
        """The travel model this cover really moves on, as the readings start from it.

        Read through `resolve_cover`, which is the precedence the cover platform itself
        applies - this cover's stored overrides, the profile it was *told* to follow,
        the keys the configuration file writes for it, the profile the file names, the
        defaults - rather than a second copy of that order written here. The profile is
        the one chosen on `path_c`, which the user may have just changed, and the travel
        is whatever this conversation knows of it.
        """
        unique_id = self._cover_unique_id or ""
        device = self._cover_config(unique_id)
        if not device:
            return None
        record = self._store.calibration(unique_id)
        chosen = self._profile or (record.profile if record is not None else None)
        height = self._measured.height or (record.height if record is not None else None)
        if record is not None:
            record = replace(record, profile=chosen, height=height)
        elif chosen is not None:
            record = StoredCalibration(cover_unique_id=unique_id, profile=chosen, height=height)
        values = resolve_cover(device, profiles=self._all_profiles(), calibration=record).values
        wanted = (
            CONF_OPENING_TIME,
            CONF_CLOSING_TIME,
            CONF_SLAT_TIME,
            CONF_OPENING_ROLL,
            CONF_CLOSING_ROLL,
        )
        if any(values.get(key) is None for key in wanted):
            return None
        return {key: float(values[key]) for key in wanted}

    @callback
    def _adopt_the_model_in_use(self) -> bool:
        """Take the times the cover moves on today as the ones the readings correct.

        `PressTiming` is what the fit is fed, and it is built here out of numbers
        nobody pressed for - which is the whole point of the scope: three timed runs
        are three chances to be half a second late, and a cover that has already been
        timed has no reason to spend them again.
        """
        values = self._values_in_use()
        if values is None:
            return False
        slat = values[CONF_SLAT_TIME]
        self._measured.opening = PressTiming(slat, values[CONF_OPENING_TIME])
        self._measured.closing = PressTiming(None, values[CONF_CLOSING_TIME])
        self._measured.times_adopted = True
        return True

    @callback
    def _thorough_plan(self) -> tuple[str, ...]:
        """The thorough calibration, with the curtain travel first when nobody knows it."""
        return PLAN_PRECISE if self._measured.height else PLAN_PRECISE_TRAVEL

    async def _async_start_thorough(self, *, from_here: bool) -> ConfigFlowResult:
        """Install the thorough plan, either after what has been walked or instead of it.

        `from_here` is what tells the two ways in apart: pressed on a summary, the plan
        replaces the tail of the one that got there (the pointer is on `summary`, and
        everything before it has already happened); chosen on `refine_scope`, it is the
        whole plan and the conversation starts on its first stage.
        """
        self._measured.precise = True
        plan = list(self._thorough_plan())
        if from_here:
            self._plan = self._plan[: self._index] + plan
            return await self._async_enter()
        return await self._async_start_plan(tuple(plan))

    # ------------------------------------------------------------------ the plan
    async def _async_start_plan(self, plan: tuple[str, ...]) -> ConfigFlowResult:
        self._plan = list(plan)
        self._index = 0
        return await self._async_enter()

    async def _async_enter(self) -> ConfigFlowResult:
        """(Re-)enter the stage the pointer is on, with its own state cleared."""
        self._task = None
        self._error = None
        self._report = None
        return await getattr(self, f"async_step_{self._plan[self._index]}")()

    async def _async_advance(self) -> ConfigFlowResult:
        self._index += 1
        return await self._async_enter()

    async def async_step_repeat_step(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """"Ripeti questo passo": only this one, and only its own movements."""
        return await self._async_enter()

    async def async_step_not_right(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """"Non ha fatto quello che doveva": stop it, then run the step again.

        The stop is what makes this different from "Ripeti": something is moving that
        should not be, or is moving the wrong way, and the step's own homing would
        otherwise queue behind it.
        """
        self._stop_first = True
        return await self._async_enter()

    async def async_step_cancel_flow(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Leave the conversation, having written nothing (true at every screen).

        The shutter is *not* stopped. A run of the calibration is free - only an end
        stop or a stop of ours ends it - and by the time this screen can be reached the
        conversation has already given up on measuring that run; interrupting it would
        leave the curtain at an arbitrary point instead of a known one. The screen says
        as much, which is why it is given the shutter's name.
        """
        self._cancelled_cover = self._cover_label
        self._disarm()
        self._release()
        self._reset_calibration()
        return await self.async_step_cancelled()

    async def async_step_cancelled(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Say so, and offer the menu rather than closing the dialog.

        The shutter's name is carried on `_cancelled_cover` rather than read off
        `_cover_label`: `async_step_cancel_flow` throws the conversation away before
        showing this screen, and `_reset_calibration` empties the label with it.
        """
        return self.async_show_menu(
            step_id="cancelled",
            menu_options=["calibrate", "init"],
            description_placeholders={"cover": self._cancelled_cover},
        )

    # ------------------------------------------------------------------ movements
    async def _async_job(self, job: Callable[[], Awaitable[None]]) -> None:
        """Run one step's movements, turning every failure into a reason to show."""
        self._error = None
        # Nothing is known about where the shutter is while it is moving, and nothing is
        # known about where it ended up if the movement failed: what put it at an end
        # stop says so itself, once it is there.
        self._at = None
        try:
            if self._stop_first:
                self._stop_first = False
                with contextlib.suppress(CalibrationError):
                    await self._cover_to_drive().async_calib_stop()
            await job()
        except CalibrationError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_label, err)
            self._error = (
                err.reason
                if err.reason in PROBLEM_REASONS or err.reason == REASON_UNKNOWN_COVER
                else REASON_UNKNOWN
            )
        except HomeAssistantError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_label, err)
            self._error = REASON_UNKNOWN
        except Exception:  # noqa: BLE001 - a flow must not leave a dialog spinning
            LOGGER.exception("Guided calibration of %s failed unexpectedly", self._cover_label)
            self._error = REASON_UNKNOWN

    async def _async_movement(
        self,
        *,
        step_id: str,
        action: str,
        job: Callable[[], Awaitable[None]],
        done_step: str,
        **extra: Any,
    ) -> ConfigFlowResult:
        """The progress screen of one stage: start the movements, then move on.

        Home Assistant re-enters this step when the task finishes, which is why the
        task is the step's only state: no task means "start it", a task that is not
        done means "keep showing the bar".
        """
        if self._task is None:
            self._task = self.hass.async_create_task(
                self._async_job(job), f"myhome guided calibration {step_id}", eager_start=False
            )
        # A shutter is moving, or has just stopped: the shorter of the two patiences.
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        if not self._task.done():
            return self.async_show_progress(
                step_id=step_id,
                progress_action=action,
                progress_task=self._task,
                description_placeholders=self._placeholders(**extra),
            )
        self._task = None
        if self._error == REASON_UNKNOWN_COVER:
            # The cover went away under the conversation; the screen that says so is
            # already written in seven languages.
            return self.async_show_progress_done(next_step_id="refused_unknown_cover")
        if self._error is not None:
            return self.async_show_progress_done(next_step_id=f"problem_{self._error}")
        return self.async_show_progress_done(next_step_id=done_step)

    async def _job_home(self, direction: str) -> None:
        await self._cover_to_drive().async_calib_home(direction)
        self._at = direction

    async def _job_start(self, direction: str) -> None:
        """Let it run free while we watch (it is already at the far end stop)."""
        self._motor_start = await self._cover_to_drive().async_calib_start(direction)

    async def _job_fraction(self, direction: str, fraction: float) -> None:
        """The run to the percentage alone: the homing is the stage's first movement."""
        self._report = await self._cover_to_drive().async_calib_run_fraction(direction, fraction)

    # ------------------------------------------------------------------ the presses
    def _timed_out(self) -> bool:
        """True when the press we were waiting for took longer than a user would."""
        if self._shown_at is None:  # pragma: no cover - every press step sets it first
            return False
        return (dt_util.utcnow() - self._shown_at).total_seconds() > PRESS_TIMEOUT_SEC

    @callback
    def _press_menu(self, step_id: str, action: str) -> ConfigFlowResult:
        """A screen with one thing to press when something happens, and two ways out."""
        self._shown_at = dt_util.utcnow()
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id=step_id,
            menu_options=[action, "repeat_step", "not_right"],
            description_placeholders=self._placeholders(),
        )

    @callback
    def _problem(self, reason: str) -> ConfigFlowResult:
        """The screen for one kind of failure, with "Ripeti questo passo" next to it."""
        return self.async_show_menu(
            step_id=f"problem_{reason}",
            menu_options=["repeat_step", "cancel_flow"],
            description_placeholders=self._placeholders(),
        )

    # Each reason has a screen of its own rather than a sentence in a placeholder: a
    # shutter that did not answer and a gateway that dropped the frame need different
    # things done about them, and a translated text can say so.
    async def async_step_problem_no_echo(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The shutter never reported that it had started moving."""
        return self._problem(REASON_NO_ECHO)

    async def async_step_problem_not_delivered(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The gateway never wrote our command to the bus."""
        return self._problem(REASON_NOT_DELIVERED)

    async def async_step_problem_not_stopped(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Our stop was refused or dropped: the shutter ran on to its end stop."""
        return self._problem(REASON_NOT_STOPPED)

    async def async_step_problem_busy(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Something else is already moving this shutter."""
        return self._problem(REASON_BUSY)

    async def async_step_problem_bad_point(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The presses cannot both be right (the second came before the first)."""
        return self._problem(REASON_BAD_POINT)

    async def async_step_problem_timeout(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Nobody pressed anything for a minute and a half."""
        return self._problem(REASON_TIMEOUT)

    async def async_step_problem_unknown(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Anything else at all; the log has the detail."""
        return self._problem(REASON_UNKNOWN)

    # ------------------------------------------------------------------ stage: close
    async def async_step_home_closed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Send the shutter all the way down, so every later measurement has an origin."""
        return await self._async_movement(
            step_id="home_closed",
            action=HOMING_ACTION[DIRECTION_CLOSE],
            job=lambda: self._job_home(DIRECTION_CLOSE),
            done_step="home_closed_done",
        )

    async def async_step_home_closed_done(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask the user to confirm what the estimate believes: it is really closed."""
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="home_closed_done",
            menu_options=["confirm_closed", "repeat_step", "not_right"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_confirm_closed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """It is closed: on to the measured opening."""
        return await self._async_advance()

    # ------------------------------------------------------------ the tape phase
    # Where the shutter stops being something the user has to be ready for. Every reading
    # from here on is "go to an end stop, run to a percentage, stop by yourself", so the
    # conversation asks once - on `tape_brief` - and then chains the runs, with the
    # progress texts saying what is moving and the reading forms as the only stops
    # (maintainer, 13 Sep). The confirmation the homings used to end on ("is it
    # completely open?") is gone with them: it protected a *press*, and there is none
    # here.
    async def async_step_tape_brief(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The one warning of the tape phase, and the order its readings are taken in."""
        self._order_the_tape_phase()
        return self.async_show_menu(
            step_id="tape_brief",
            menu_options=["tape_start", "cancel_flow"],
            description_placeholders=self._placeholders(readings=len(self._tape_phase())),
        )

    async def async_step_tape_start(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """"Ho capito, cominciamo": the readings run from here without asking again."""
        return await self._async_advance()

    @callback
    def _tape_phase(self) -> list[str]:
        """The readings that follow the briefing: every stage up to the first that is not.

        The phase is read off the plan rather than stored, so a plan that grafts stages
        onto itself (the precise level, path B's check) needs nothing of its own.
        """
        phase: list[str] = []
        for stage in self._plan[self._index + 1 :]:
            if stage not in TAPE_STAGES:
                break
            phase.append(stage)
        return phase

    @callback
    def _order_the_tape_phase(self) -> None:
        """Deal the readings out again, starting from the end stop the shutter is at."""
        phase = self._tape_phase()
        start = self._index + 1
        self._plan[start : start + len(phase)] = order_the_readings(phase, self._at)

    # ------------------------------------------------------------- stage: the ascent
    # One stage, three movements, two presses - and the two presses are on two separate
    # runs (0.5.0, "path A ascent"). Before, one run carried both: the user pressed as
    # the bottom edge left its rest and pressed again twenty seconds later at the top,
    # and the first press was worth whatever their attention was worth after having been
    # told to watch for two different things at once. Now the first press *ends* its run
    # - the flow stops the shutter on it - so the measurement can be checked with a tape
    # (the bottom edge should be standing a few centimetres up) and, where the press was
    # late, repaired by it. The shutter is then closed again and the whole ascent is run
    # for the second press.
    #
    # "Ripeti questo passo" anywhere in here re-enters `async_step_open_timed`, which is
    # to say it repeats *both* runs: the two are one measurement and a slat phase from
    # one attempt does not belong with a full ascent from another.
    async def async_step_open_timed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Bring it to the bottom, then explain the first press before anything runs.

        Nothing starts here. The first live walk-through had the shutter already
        climbing while the user was still reading what they were supposed to watch for,
        and the measurement it produced was the reaction time of somebody who had not
        been told there was anything to react to.
        """
        if self._task is None:
            # Entering the stage (or repeating it): everything the two runs collect goes
            # back to nothing, so a repeat cannot pair a slat phase with the wrong
            # ascent. Guarded by the task, because Home Assistant re-enters this step
            # for every frame of the progress bar.
            self._forget_the_ascent()
        return await self._async_movement(
            step_id="open_timed",
            action=HOMING_ACTION[DIRECTION_CLOSE],
            job=lambda: self._job_home(DIRECTION_CLOSE),
            done_step="open_brief",
        )

    @callback
    def _forget_the_ascent(self) -> None:
        """Throw away both runs of the ascent, before the first one is started again."""
        self._lift_off = None
        self._stop_delivered = None
        self._motor_stopped = None
        self._measured.slat_seconds = None
        self._measured.lift_run_sec = None
        self._measured.lift_gap_cm = None
        self._measured.lift_late = False

    async def async_step_open_brief(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The instructions, and the button that starts the run when they are read."""
        return self.async_show_menu(
            step_id="open_brief",
            menu_options=["open_start", "repeat_step", "cancel_flow"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_open_start(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """"1) Avvia la tapparella": the frame goes out now and not before."""
        return await self._async_movement(
            step_id="open_start",
            action="starting_open",
            job=lambda: self._job_start(DIRECTION_OPEN),
            done_step="open_lift",
        )

    async def async_step_open_lift(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The one press of the first run: the bottom edge leaves its rest."""
        return self._press_menu("open_lift", "lifted_off")

    async def async_step_lifted_off(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Remember when that press reached us, and stop the shutter on it at once.

        The stop is what turns a press into something a tape can check: the shutter
        comes to rest a few centimetres up, and where it rests says how late the press
        was. It goes out on its own progress screen so that a gateway which will not
        take it lands on `problem_not_stopped` like every other refused frame.
        """
        if self._timed_out():
            return await self.async_step_problem_timeout()
        if self._lift_off is None:
            self._lift_off = dt_util.utcnow()
        return await self.async_step_lift_stop()

    async def async_step_lift_stop(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The stop the press asked for, and the two instants it is measured by."""
        return await self._async_movement(
            step_id="lift_stop",
            action="stopping_lift",
            job=self._job_stop_lift,
            done_step="lift_measured",
        )

    async def _job_stop_lift(self) -> None:
        """Stop the lift-off run, and note when the frame went out and the motor stopped.

        Two different instants, and both are needed. The delivery is what says whether
        the command queue held the stop back - the user is told, so that a large gap
        does not read as their own slowness - and the motor stop is the far end of the
        distance the tape is about to measure.
        """
        cover = self._cover_to_drive()
        self._stop_delivered = await cover.async_calib_stop()
        self._motor_stopped = await cover.async_calib_motor_stop()

    async def async_step_lift_measured(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Turn the press into a slat phase, and go and look at where it stopped."""
        measured = self._measured
        try:
            measured.slat_seconds = slat_time_from_press(self._motor_start, self._lift_off)
        except CalibrationError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_label, err)
            return await self.async_step_problem_bad_point()
        if self._motor_start is not None and self._motor_stopped is not None:
            measured.lift_run_sec = (self._motor_stopped - self._motor_start).total_seconds()
        measured.lift_late = (
            self._stop_delivered is not None
            and self._lift_off is not None
            and (self._stop_delivered - self._lift_off).total_seconds() > LATE_STOP_SEC
        )
        return await self.async_step_lift_check()

    async def async_step_lift_check(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Where the bottom edge is standing now, which is how good that press was.

        Three exits, one per thing the user can see, plus the usual "it did not do what
        it should". "Ripeti questo passo" is not offered a fourth time: on this screen it
        would be the same button as "it is still touching the base" with a vaguer label.

        The same three whichever level the conversation is heading for. Asking for the
        gap by default at the precise level was considered and dropped: the level is
        chosen *after* the measurements (`summary_basic` -> "Migliora la precisione",
        and `PLAN_PRECISE` does not re-measure the ascent), so a branch on it would
        never be taken in a real walk. What the text does instead is recommend the
        reading, in one sentence, as the most precise of the three.
        """
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        if self._measured.lift_late:
            return self.async_show_menu(
                step_id="lift_check_late",
                menu_options=LIFT_CHECK_OPTIONS,
                description_placeholders=self._placeholders(),
            )
        return self.async_show_menu(
            step_id="lift_check",
            menu_options=LIFT_CHECK_OPTIONS,
            description_placeholders=self._placeholders(),
        )

    async def async_step_lift_check_late(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The same screen with the busy-gateway paragraph; the router picks between them."""
        return await self.async_step_lift_check()

    async def async_step_lift_too_early(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """"It is still touching the base": the press came before the edge left it.

        Nothing can be done with that measurement. A gap of zero says the curtain
        travelled no distance at all before the motor stopped, so the lift-off is
        somewhere *after* the stop and the slat phase the press produced is short by an
        unknown amount. The only honest answer is the run again, which is exactly what
        "Ripeti questo passo" does - the label is what differs, and the label is what
        the user recognises.
        """
        return await self.async_step_repeat_step()

    async def async_step_lift_accept(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """"It stands a few centimetres up": the press is taken at its word."""
        return await self.async_step_open_home_again()

    async def async_step_lift_gap(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The tape reading that replaces the press: how far the bar rose after it.

        The field may be left empty, which is the way out for somebody who opened the
        form and then thought better of it: the press stands as it was made. A reading
        under a centimetre is not a small gap, it is a shutter still resting on its
        base, and it goes to a screen of its own instead of being taken as a very good
        press.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            written = str(user_input.get(FIELD_GAP_CM, "")).strip()
            if not written:
                return await self.async_step_open_home_again()
            value = parse_number(written)
            if value is None:
                errors[FIELD_GAP_CM] = ERROR_NOT_A_NUMBER
            elif not 0.0 <= value <= MAX_GAP_CM:
                errors[FIELD_GAP_CM] = ERROR_OUT_OF_RANGE
            elif value < TOUCHING_CM:
                return await self.async_step_lift_early()
            else:
                self._measured.lift_gap_cm = value
                return await self.async_step_open_home_again()
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_form(
            step_id="lift_gap",
            data_schema=vol.Schema({vol.Optional(FIELD_GAP_CM, default=""): _text_field()}),
            errors=errors,
            description_placeholders=self._placeholders(),
        )

    async def async_step_lift_early(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """A gap of nothing: the press was early, and the run has to be made again."""
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="lift_early",
            menu_options=["repeat_step", "lift_gap", "not_right"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_open_home_again(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Back down to the base: the full ascent starts from the end stop as well."""
        return await self._async_movement(
            step_id="open_home_again",
            action=HOMING_ACTION[DIRECTION_CLOSE],
            job=lambda: self._job_home(DIRECTION_CLOSE),
            done_step="closed_again",
        )

    async def async_step_closed_again(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The same question as at the start of the stage, asked before the second run."""
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="closed_again",
            menu_options=["confirm_closed_again", "repeat_step", "not_right"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_confirm_closed_again(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """It is closed again: on to the briefing of the full ascent.

        Deliberately not `confirm_closed`, which advances the *plan*: this confirmation
        is inside a stage and has to come back to it.
        """
        return await self.async_step_open_full_brief()

    async def async_step_open_full_brief(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The second run's instructions, and the button that starts it."""
        return self.async_show_menu(
            step_id="open_full_brief",
            menu_options=["open_full_start", "repeat_step", "cancel_flow"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_open_full_start(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """"2) Avvia la tapparella": the whole ascent this time, end stop to end stop."""
        return await self._async_movement(
            step_id="open_full_start",
            action="starting_open_full",
            job=lambda: self._job_start(DIRECTION_OPEN),
            done_step="open_top",
        )

    async def async_step_open_top(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The one press of the second run: the shutter has stopped by itself at the top."""
        return self._press_menu("open_top", "stopped_open")

    async def async_step_stopped_open(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Put the two runs together: the slat phase of the first, the ascent of the second."""
        if self._timed_out():
            return await self.async_step_problem_timeout()
        try:
            run = timing_from_presses(self._motor_start, None, dt_util.utcnow())
            self._measured.opening = timing_with_slat(run, self._measured.slat_seconds or 0.0)
            # The run was free: whatever the press measured, the shutter is at the top.
            self._at = DIRECTION_OPEN
        except CalibrationError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_label, err)
            return await self.async_step_problem_bad_point()
        return await self.async_step_open_result()

    async def async_step_open_result(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The two numbers the two runs produced, before anything is built on them.

        Two screens, because a gap that was taped changes what the slat time on this one
        *means*: it is still the press's, and the tape will replace it when the values
        are computed, so a screen that showed the press's number alone would be showing
        a number that never reaches the profile.
        """
        opening = self._measured.opening
        gap = self._measured.lift_gap_cm
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        placeholders = self._placeholders(
            slat=f"{(opening.slat_time or 0.0):.1f}" if opening else "-",
            run=f"{opening.run_time:.1f}" if opening else "-",
            gap=f"{gap:.1f}" if gap is not None else "-",
        )
        if gap is not None:
            return self.async_show_menu(
                step_id="open_result_gap",
                menu_options=["accept_step", "repeat_step"],
                description_placeholders=placeholders,
            )
        return self.async_show_menu(
            step_id="open_result",
            menu_options=["accept_step", "repeat_step"],
            description_placeholders=placeholders,
        )

    async def async_step_open_result_gap(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """The result screen of an ascent whose gap was taped; the router picks it."""
        return await self.async_step_open_result()

    # ------------------------------------------------------------ stage: the descent
    async def async_step_close_timed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Bring it to the top, then explain the press before anything runs."""
        return await self._async_movement(
            step_id="close_timed",
            action=HOMING_ACTION[DIRECTION_OPEN],
            job=lambda: self._job_home(DIRECTION_OPEN),
            done_step="close_brief",
        )

    async def async_step_close_brief(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The instructions of the descent, and the button that starts it."""
        return self.async_show_menu(
            step_id="close_brief",
            menu_options=["close_start", "repeat_step", "cancel_flow"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_close_start(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """"1) Avvia la tapparella", downwards."""
        return await self._async_movement(
            step_id="close_start",
            action="starting_close",
            job=lambda: self._job_start(DIRECTION_CLOSE),
            done_step="close_bottom",
        )

    async def async_step_close_bottom(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The press that ends the descent: it is down and the slats have closed."""
        return self._press_menu("close_bottom", "stopped_closed")

    async def async_step_stopped_closed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The closing run time. Its slat phase is the opening one (phase 2 decision)."""
        if self._timed_out():
            return await self.async_step_problem_timeout()
        try:
            self._measured.closing = timing_from_presses(self._motor_start, None, dt_util.utcnow())
            # ...and at the bottom, which is what the first reading of the tape phase is
            # dealt from.
            self._at = DIRECTION_CLOSE
        except CalibrationError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_label, err)
            return await self.async_step_problem_bad_point()
        return await self.async_step_close_result()

    async def async_step_close_result(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The number the press produced, before anything is built on it."""
        closing = self._measured.closing
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="close_result",
            menu_options=["accept_step", "repeat_step"],
            description_placeholders=self._placeholders(
                run=f"{closing.run_time:.1f}" if closing else "-"
            ),
        )

    async def async_step_accept_step(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """"Va bene, avanti": the measurement stands, on to the next stage."""
        return await self._async_advance()

    # ------------------------------------------------------------------ stage: height
    async def async_step_height_read(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bring it to the top, then ask for the travel.

        The travel is the distance between the two end stops, so it can only be read off
        a shutter standing at one of them. In path A the ascent has just left it there
        and the runner answers a homing with nothing to run with the settle alone
        (`cover._async_calib_home`); in path B this is the only movement of the path.
        Homing here rather than in a stage of its own is what makes "Ripeti questo passo"
        put the shutter back where the reading needs it.

        A travel already written down is thrown away when this stage is re-entered by
        "Non ha fatto quello che doveva" - which is what `_stop_first` marks, and the
        only way back in here. The screen that offers it says the shutter never reached
        the top, so the number read off it is worth no more than the reading
        `repeat_measure` doubts, and that one is thrown away too; leaving it behind
        would open the form again on the very number the user has just disowned. A
        travel carried in from somewhere else - path C keeps the one path B's check
        measured - is not touched, because this stage is then entered with nothing to
        stop first.
        """
        if self._stop_first:
            self._forget_the_travel()
        return await self._async_movement(
            step_id="height_read",
            action=HOMING_ACTION[DIRECTION_OPEN],
            job=lambda: self._job_home(DIRECTION_OPEN),
            done_step="height",
        )

    async def async_step_height(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The one measurement everything else is scaled by: the curtain travel."""
        errors: dict[str, str] = {}
        if user_input is not None:
            value = parse_number(user_input.get(CONF_HEIGHT))
            if value is None:
                errors[CONF_HEIGHT] = ERROR_NOT_A_NUMBER
            elif not MIN_HEIGHT_CM <= value <= MAX_HEIGHT_CM:
                errors[CONF_HEIGHT] = ERROR_OUT_OF_RANGE
            else:
                self._measured.height = value
                self._measured.height_measured = True
                return await self.async_step_height_result()
        default = (
            self._measured.height
            if self._measured.height is not None
            else self._known_height(self._cover_unique_id or "")
        )
        suggested = _as_text(default if default is not None else FALLBACK_HEIGHT_CM)
        return self.async_show_form(
            step_id="height",
            data_schema=vol.Schema(
                {vol.Required(CONF_HEIGHT, description={"suggested_value": suggested}): _text_field()}
            ),
            errors=errors,
            description_placeholders=self._placeholders(),
        )

    async def async_step_height_result(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The travel that was just written down, with a way to write it again.

        "Non ha fatto quello che doveva" is here because the homing that opens this stage
        no longer ends on a confirmation of its own: this screen is the first thing the
        user sees after it, and a travel read off a shutter that never reached the top is
        the one reading that would put every other measurement out.
        """
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="height_result",
            menu_options=["accept_step", "repeat_measure", "not_right"],
            description_placeholders=self._placeholders(
                height=f"{self._measured.height:.1f}" if self._measured.height else "-"
            ),
        )

    async def async_step_repeat_measure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """"Ripeti la misura": ask for the reading again without moving anything.

        The height is read with the shutter standing where the previous stage left it,
        so there is nothing to re-run; the tape readings have their own step to repeat
        (`repeat_step`), which does re-run the movements.
        """
        self._forget_the_travel()
        return await self.async_step_height()

    @callback
    def _forget_the_travel(self) -> None:
        """Take back a travel that is not one: the form opens on nothing again."""
        self._measured.height = None
        self._measured.height_measured = False

    # --------------------------------------------------------- stages: the measured runs
    async def _async_fraction_stage(
        self, *, step_id: str, direction: str, fraction: float, done_step: str
    ) -> ConfigFlowResult:
        """One reading's two movements, each with a progress screen that names it.

        Two screens rather than one because they are two different things to watch: the
        shutter travelling the whole way to an end stop, and the run to the percentage
        that is about to be measured. One text covering both said "it is being opened
        completely and then run down to 50 %" over a bar that was doing the first of
        those, which is exactly the moment the user is deciding whether to stand clear.
        """
        self._pending = (direction, fraction)
        self._after_the_run = done_step
        start = _other_end(direction)
        return await self._async_movement(
            step_id=step_id,
            action=HOMING_ACTION[start],
            job=lambda: self._job_home(start),
            done_step="tape_run",
        )

    async def async_step_tape_run(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The run to the percentage, from the end stop the homing has just reached."""
        direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
        return await self._async_movement(
            step_id="tape_run",
            action=RUNNING_ACTION[direction],
            job=lambda: self._job_fraction(direction, fraction),
            done_step=self._after_the_run,
            percent=round(fraction * 100),
        )

    async def async_step_half_down(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Open fully, run half the curtain down: the descent's own coefficient."""
        return await self._async_fraction_stage(
            step_id="half_down", direction=DIRECTION_CLOSE, fraction=HALF_RUN, done_step="measure_descent"
        )

    async def async_step_quarter_down(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A quarter of the way down: the second point of the descent."""
        return await self._async_fraction_stage(
            step_id="quarter_down", direction=DIRECTION_CLOSE, fraction=QUARTER_RUN, done_step="measure_descent"
        )

    async def async_step_three_quarter_down(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Three quarters of the way down: the third."""
        return await self._async_fraction_stage(
            step_id="three_quarter_down",
            direction=DIRECTION_CLOSE,
            fraction=THREE_QUARTER_RUN,
            done_step="measure_descent",
        )

    async def async_step_half_up(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Close fully, run the slats plus half the curtain up."""
        return await self._async_fraction_stage(
            step_id="half_up", direction=DIRECTION_OPEN, fraction=HALF_RUN, done_step="measure_ascent"
        )

    async def async_step_quarter_up(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """A quarter of the way up."""
        return await self._async_fraction_stage(
            step_id="quarter_up", direction=DIRECTION_OPEN, fraction=QUARTER_RUN, done_step="measure_ascent"
        )

    async def async_step_three_quarter_up(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Three quarters of the way up."""
        return await self._async_fraction_stage(
            step_id="three_quarter_up",
            direction=DIRECTION_OPEN,
            fraction=THREE_QUARTER_RUN,
            done_step="measure_ascent",
        )

    # ------------------------------------------------------------------ the tape
    def _expected_cm(self) -> tuple[str, str]:
        """Where the model thinks the bar is, and how far out is still normal.

        The precise level has a fitted model of *this* window, so its expectation is
        worth being strict about. The basic level has only the ordinary geometry of a
        roller shutter, so it says the same thing with a wider margin: the point of the
        line is to catch a tape read from the floor rather than from the rest, which is
        wrong by tens of centimetres, not by three.
        """
        direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
        height = self._measured.height
        if not height:
            return ("-", f"{ROUGH_TOLERANCE_CM:.0f}")
        values = self._model_values()
        if values is not None:
            roll = values[CONF_CLOSING_ROLL if direction == DIRECTION_CLOSE else CONF_OPENING_ROLL]
            tolerance = EXPECTED_TOLERANCE_CM
        else:
            roll = DEFAULT_ROLL_SHUTTER
            tolerance = ROUGH_TOLERANCE_CM
        expected = predict_cm(direction, roll, 1.0, fraction, height)
        return (f"{expected:.0f}", f"{tolerance:.0f}")

    def _measurement_form(self, step_id: str, errors: dict[str, str] | None = None) -> ConfigFlowResult:
        direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
        expected, tolerance = self._expected_cm()
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required(FIELD_MEASURED_CM): _text_field()}),
            errors=errors,
            description_placeholders=self._placeholders(
                percent=round(fraction * 100),
                direction=direction,
                expected=expected,
                tolerance=tolerance,
            ),
        )

    def _accept_measurement(self, user_input: Mapping[str, Any]) -> tuple[float | None, str | None]:
        """A tape reading that is a number and fits inside this window's travel.

        A bar measured above the whole curtain travel is a tape read from the wrong
        reference (the floor rather than where the bottom edge rests when closed), and
        the fit would refuse it three screens later with nothing to correct.
        """
        value = parse_number(user_input.get(FIELD_MEASURED_CM))
        if value is None:
            return None, ERROR_NOT_A_NUMBER
        if value < 0:
            return None, ERROR_OUT_OF_RANGE
        height = self._measured.height
        if height is not None and value > height:
            return None, ERROR_ABOVE_THE_TRAVEL
        return value, None

    async def async_step_measure_descent(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """How far the bar came down: one point of the descent."""
        if user_input is None:
            return self._measurement_form("measure_descent")
        value, error = self._accept_measurement(user_input)
        if value is None or self._report is None:
            return self._measurement_form(
                "measure_descent", errors={FIELD_MEASURED_CM: error or ERROR_ABOVE_THE_TRAVEL}
            )
        self._measured.descent.append((self._report.motor_seconds, value))
        self._tape_target = "descent"
        return await self.async_step_tape_result()

    async def async_step_measure_ascent(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """How far the bar came up: one point of the ascent."""
        if user_input is None:
            return self._measurement_form("measure_ascent")
        value, error = self._accept_measurement(user_input)
        if value is None or self._report is None:
            return self._measurement_form(
                "measure_ascent", errors={FIELD_MEASURED_CM: error or ERROR_ABOVE_THE_TRAVEL}
            )
        self._measured.ascent.append((self._report.motor_seconds, value))
        self._tape_target = "ascent"
        return await self.async_step_tape_result()

    async def async_step_tape_result(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The reading that was just taken, with "Ripeti la misura" next to it.

        "Ripeti" here is the step's own movements again, and the reading is thrown
        away: the shutter has to be back at its end stop for the same fraction to mean
        the same thing.
        """
        _direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
        points = self._measured.descent if self._tape_target == "descent" else self._measured.ascent
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="tape_result",
            menu_options=["accept_step", "repeat_tape", "tape_not_right"],
            description_placeholders=self._placeholders(
                percent=round(fraction * 100),
                measured=f"{points[-1][1]:.1f}" if points else "-",
            ),
        )

    async def async_step_repeat_tape(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Throw the reading away and run the stage's own movements again."""
        self._forget_the_reading()
        return await self._async_enter()

    async def async_step_tape_not_right(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """"Non ha fatto quello che doveva", said of the run behind a reading.

        The tape phase asks nothing before its movements, so this is where a shutter that
        went the wrong way or never moved is reported: it stops whatever is moving and
        makes the stage's movements again, and the reading that was typed over the top of
        the mishap goes with them.
        """
        self._forget_the_reading()
        return await self.async_step_not_right()

    @callback
    def _forget_the_reading(self) -> None:
        """Take the last reading back off the direction it was appended to."""
        # The verification fits nothing, so it has nothing to take back; the two
        # measuring stages do, and the reading has to go before the run is repeated or
        # the fit would be given the same fraction twice.
        if self._tape_target == "descent" and self._measured.descent:
            self._measured.descent.pop()
        elif self._tape_target == "ascent" and self._measured.ascent:
            self._measured.ascent.pop()

    # ------------------------------------------------------------------ verification
    async def async_step_verify(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The precise level's last run, to a place no measurement taught the model."""
        return await self._async_fraction_stage(
            step_id="verify", direction=DIRECTION_CLOSE, fraction=VERIFY_RUN, done_step="measure_verify"
        )

    async def async_step_verify_offer(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Path B: measuring the height is enough, but the shutter can be asked."""
        return self.async_show_menu(
            step_id="verify_offer",
            menu_options=["verify_now", "skip_verify"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_verify_now(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Graft the check - and the homing it has to start from - onto the plan here."""
        self._plan[self._index + 1 : self._index + 1] = list(PLAN_VERIFY_B)
        return await self._async_advance()

    async def async_step_skip_verify(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Take the profile at its word."""
        return await self._async_advance()

    async def async_step_verify_b(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Path B's check: half way down from the top, then a tape."""
        return await self._async_fraction_stage(
            step_id="verify_b", direction=DIRECTION_CLOSE, fraction=VERIFY_RUN_PROFILE, done_step="measure_verify"
        )

    async def async_step_measure_verify(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The reading the model is compared against, rather than fitted to."""
        if user_input is None:
            return self._measurement_form("measure_verify")
        value, error = self._accept_measurement(user_input)
        if value is None:
            return self._measurement_form(
                "measure_verify", errors={FIELD_MEASURED_CM: error or ERROR_ABOVE_THE_TRAVEL}
            )
        self._measured.deviation = self._deviation(value)
        # Where that reading was taken, for the summary: the stage set `_pending` when
        # it started the run, and the two verifications run to different fractions.
        _direction, fraction = self._pending or (DIRECTION_CLOSE, VERIFY_RUN)
        self._measured.verify_fraction = fraction
        self._tape_target = None
        return await self.async_step_verify_result()

    def _deviation(self, measured: float) -> float | None:
        """How far the shutter really stopped from where the model said it would."""
        report = self._report
        height = self._measured.height
        values = self._model_values()
        if report is None or not height or values is None:
            # The profile this window follows was deleted while the dialog was open,
            # which is the one way a verification can end up with nothing to verify
            # against. The screen then reports no gap rather than inventing one.
            return None
        return deviation_cm(
            DIRECTION_CLOSE,
            roll=values[CONF_CLOSING_ROLL],
            height=height,
            run_time=values[CONF_CLOSING_TIME],
            slat_time=values[CONF_SLAT_TIME],
            motor_seconds=report.motor_seconds,
            measured_cm=measured,
        )

    def _model_values(self) -> dict[str, float] | None:
        """The travel model the verification is asking about.

        Path B has not measured a thing beyond the height, so the model is the profile
        scaled to this window; the precise level of path A has just fitted one, so it
        is the fit. Either way the run itself is real and its seconds are the bus's.
        """
        if self._path == PATH_PROFILE:
            profile = self._all_profiles().get(self._profile or "")
            if profile is None:
                return None
            return derive_cover_from_profile(profile, self._measured.height)
        fits = self._fits()
        if fits is None:
            return None
        down, up = fits
        return {
            CONF_CLOSING_TIME: down.corrected_run_time,
            CONF_OPENING_TIME: up.corrected_run_time,
            CONF_SLAT_TIME: up.slat_time,
            CONF_CLOSING_ROLL: down.fit.roll,
            CONF_OPENING_ROLL: up.fit.roll,
        }

    async def async_step_verify_result(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show the deviation in centimetres, and what can be done about it."""
        deviation = self._measured.deviation
        # Rounded *before* the threshold is applied, so that the number on the screen is
        # the number that decided: comparing the unrounded value showed "3 cm" both
        # with and without the refinement on offer, on a digit the user cannot see.
        off_by = round(abs(deviation), 1) if deviation is not None else 0.0
        options = ["accept_step", "repeat_tape"]
        if self._path == PATH_PROFILE and off_by > REFINE_THRESHOLD_CM:
            options = ["path_c", "accept_step", "repeat_tape"]
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="verify_result",
            menu_options=options,
            description_placeholders=self._placeholders(deviation=f"{off_by:.1f}"),
        )

    # ------------------------------------------------------------------ the name
    async def async_step_profile_name(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Name the kind of shutter, before the summary rather than after it.

        The summary shows the `myhome.yaml` equivalent of what was measured, and a
        profile's name is the key of that block: asking for it afterwards meant the
        snippet on the screen carried a name the user had not chosen yet.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_NAME]).strip()
            # `NO_PROFILE` is a valid YAML key and the sentinel the assignment select
            # uses for "Nessun profilo": a profile really called that would be
            # unassignable from that form for ever.
            if not _NAME_RE.match(name) or name == NO_PROFILE:
                errors[CONF_NAME] = ERROR_INVALID_NAME
            else:
                # A name already in use *replaces* that profile. The commonest reason to
                # walk path A again is that the first measurement was poor; refusing the
                # name sent the user back to this form with three minutes of
                # measurements about to be thrown away. A `cover_profiles:` entry of the
                # same name in the file is not touched and goes on being shadowed.
                self._measured_name = name
                return await self._async_advance()
        suggested = (
            (user_input or {}).get(CONF_NAME)
            or self._measured_name
            or _suggested_name(getattr(self._cover, "entity_id", ""))
        )
        return self.async_show_form(
            step_id="profile_name",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, description={"suggested_value": suggested}): TextSelector(
                        TextSelectorConfig()
                    )
                }
            ),
            errors=errors,
            description_placeholders=self._placeholders(
                replaced=("yes" if self._measured_name in self._all_profiles() else "")
            ),
        )

    # ------------------------------------------------------------------ the summary
    def _fit_both(self, slat: float) -> tuple[DirectionFit, DirectionFit]:
        """One fit per direction, both told the same slat phase.

        The time scale is fitted with the roll wherever the run times were *pressed*
        for: it is the reaction time of those presses, measured on the shutter instead
        of guessed at. "Solo la calibrazione approfondita" pressed for nothing - its
        times are the ones the cover already moves on - so there is no finger in them
        to correct and the scale is pinned at 1. That is also what makes the two
        readings per direction fit one unknown rather than two, which leaves a residual
        worth reading, and what makes the model that is stored the same model the check
        at 40 % was asked about.
        """
        measured = self._measured
        height = measured.height or 0.0
        scale_bounds = (
            {"scale_bounds": FIXED_SCALE_BOUNDS} if measured.times_adopted else {}
        )
        down = fit_from_run(
            DIRECTION_CLOSE,
            run_time=measured.closing.run_time if measured.closing else 0.0,
            slat_time=slat,
            measurements=measured.descent,
            height=height,
            **scale_bounds,
        )
        up = fit_from_run(
            DIRECTION_OPEN,
            run_time=measured.opening.run_time if measured.opening else 0.0,
            slat_time=slat,
            measurements=measured.ascent,
            height=height,
            **scale_bounds,
        )
        return down, up

    def _slat_from_gap(self, raw: float, *, roll: float, height: float | None, curtain: float) -> float:
        """The slat phase the taped gap implies, or the press's own when none was taped.

        The whole of the gap refinement's plumbing: the pure arithmetic is
        `calibration.slat_time_from_gap`, and this is the guard in front of it. A
        conversation with no gap, no measured lift-off run, no height or no curtain time
        has nothing to correct with and keeps the press.
        """
        measured = self._measured
        if measured.lift_gap_cm is None or measured.lift_run_sec is None:
            return raw
        if not height or curtain <= 0:
            return raw
        return slat_time_from_gap(
            stop_seconds=measured.lift_run_sec,
            gap_cm=measured.lift_gap_cm,
            roll=roll,
            height=height,
            curtain_time=curtain,
        )

    def _fits(self) -> tuple[DirectionFit, DirectionFit] | None:
        """Fit both directions, or None when this path measured no centimetres.

        Fitted twice where the user taped the gap the lift-off run left, because the
        two things are defined in terms of each other: the correction needs the ascent's
        roll and curtain time, and the fit that produces them needs the slat phase the
        correction is about. The circle is broken by fitting once with the press's own
        slat phase - which is right to within the fraction of a second the gap is there
        to remove - and fitting again with the corrected one. A third round would move
        the roll by less than the tape can read.
        """
        measured = self._measured
        if (
            measured.opening is None
            or measured.closing is None
            or not measured.height
            or not measured.descent
            or not measured.ascent
        ):
            return None
        down, up = self._fit_both(measured.slat_time)
        refined = self._slat_from_gap(
            up.slat_time, roll=up.fit.roll, height=measured.height, curtain=up.curtain_time
        )
        if refined != up.slat_time:
            down, up = self._fit_both(refined)
        return down, up

    def _result(self) -> _Result:
        """What Save would write, computed from what has been measured so far."""
        measured = self._measured
        name = self._measured_name or _suggested_name(getattr(self._cover, "entity_id", ""))
        # The key the *file* knows this cover by, not the entity's object id: the
        # snippet is offered as something to paste into the configuration file, and an
        # entity the user has since renamed would make it paste into nothing.
        key = self._yaml_key or _suggested_name(getattr(self._cover, "entity_id", ""))
        if self._path == PATH_PROFILE:
            height = measured.height or 0.0
            # Nothing of the profile is copied into the record: what is stored is
            # "this window follows that profile", and the resolution scales it on
            # every read. The numbers below are for the *screen* - the snippet is
            # offered as an alternative to saving, and `profile:` + `height:` pasted
            # into a file that carries its own run times would not change them
            # (0.5.0 v2 review, BUG-1; final review, RISK-A).
            profile = self._all_profiles().get(self._profile or "")
            derived = profile_overrides(profile, height) if profile is not None else {}
            return _Result(
                yaml=profile_reference_yaml(key, self._profile or "", height, derived),
                follows_profile=True,
            )
        fits = self._fits()
        if fits is not None:
            down, up = fits
            values = {
                CONF_OPENING_TIME: round(up.corrected_run_time, 1),
                CONF_CLOSING_TIME: round(down.corrected_run_time, 1),
                # The fit's, not the press's: `_fits` replaces the press with the taped
                # gap where there is one, and `DirectionFit` carries what it was told.
                CONF_SLAT_TIME: round(up.slat_time, 1),
                CONF_OPENING_ROLL: round(up.fit.roll, 2),
                CONF_CLOSING_ROLL: round(down.fit.roll, 2),
            }
            # A direction fitted through a single point is reproduced exactly by
            # construction, so its residual is 0.0 and means nothing at all. It takes
            # two points per direction before there is anything left over to be a
            # residual of, which is why the basic summary has no accuracy line at all.
            accuracy = (
                max(down.fit.max_residual_cm, up.fit.max_residual_cm)
                if min(down.fit.points, up.fit.points) > 1
                else None
            )
            if self._path == PATH_FIRST:
                return _Result(
                    yaml=calibration_yaml(
                        name,
                        measured.height or 0.0,
                        values[CONF_OPENING_TIME],
                        values[CONF_CLOSING_TIME],
                        values[CONF_SLAT_TIME],
                        values[CONF_CLOSING_ROLL],
                        values[CONF_OPENING_ROLL],
                    ),
                    profile={CONF_REFERENCE_HEIGHT: measured.height or 0.0, **values},
                    # The same numbers again, as this window's own overrides. The
                    # profile is what the *next* shutter of this kind inherits; the
                    # overrides are what makes this one run on what was just measured,
                    # because a profile does not beat a key written in the configuration
                    # file (spec 1.3) and the file is where a basic cover's run times
                    # usually live.
                    overrides=dict(values),
                    accuracy_cm=accuracy,
                )
            if measured.times_adopted:
                # The scope that timed nothing measured the two roll coefficients and
                # nothing else. Writing the run times it *started from* as this cover's
                # own would be a measurement nobody made - `raw` already says
                # `times_measured: false` - and worse than idle: an override freezes
                # the profile's times into this cover, so correcting the profile would
                # afterwards reach every window that follows it except the one that was
                # measured most carefully.
                rolls = {
                    CONF_OPENING_ROLL: values[CONF_OPENING_ROLL],
                    CONF_CLOSING_ROLL: values[CONF_CLOSING_ROLL],
                }
                return _Result(
                    yaml=overrides_yaml(key, rolls, measured.height),
                    overrides=rolls,
                    accuracy_cm=accuracy,
                )
            return _Result(
                yaml=overrides_yaml(key, values, measured.height),
                overrides=values,
                accuracy_cm=accuracy,
            )
        # Path C, times only: three presses and nothing to fit. The gap can still be
        # corrected for - this path always follows a profile, so the roll and the
        # curtain time it needs are the profile's, scaled to whatever this window's
        # height is known to be.
        slat = measured.slat_time
        profile = self._all_profiles().get(self._profile or "")
        height = measured.height or self._known_height(self._cover_unique_id or "")
        if profile is not None and measured.opening is not None:
            model = derive_cover_from_profile(profile, height)
            slat = self._slat_from_gap(
                slat,
                roll=model[CONF_OPENING_ROLL],
                height=height,
                curtain=measured.opening.run_time - slat,
            )
        values = {
            CONF_OPENING_TIME: round(measured.opening.run_time, 1) if measured.opening else 0.0,
            CONF_CLOSING_TIME: round(measured.closing.run_time, 1) if measured.closing else 0.0,
            CONF_SLAT_TIME: round(slat, 1),
        }
        return _Result(yaml=overrides_yaml(key, values, None), overrides=values)

    def _summary_placeholders(self, result: _Result) -> dict[str, str]:
        """The numbers the three summaries share, and the one only the precise one shows.

        `{accuracy}` is the verification's own answer whenever there is one: how far the
        shutter really stopped from where the model said it would, at the one position
        no reading was fitted to. That is the number `summary_precise` names, and it is
        the only place the flow says "accuracy" out loud. The worst residual over the
        fitted readings is the fallback - it is what a summary reached without a
        verification would have to fall back on, and it is what the basic summary's "-"
        comes from, because one reading per direction reproduces itself and leaves no
        residual at all.
        """
        measured = self._measured
        # The unit travels with the value, so a path that did not measure something
        # reads "-" rather than "- cm".
        height = f"{measured.height:.0f} cm" if measured.height else "\u2013"
        if measured.deviation is not None:
            accuracy = f"{abs(measured.deviation):.1f} cm"
        elif result.accuracy_cm is not None:
            accuracy = f"{result.accuracy_cm:.1f} cm"
        else:
            accuracy = "\u2013"
        replaced, kept = self._replaced_and_kept(result)
        return self._placeholders(
            yaml=f"```yaml\n{result.yaml}```",
            height=height,
            accuracy=accuracy,
            percent=round((measured.verify_fraction or VERIFY_RUN) * 100),
            profile=self._measured_name or self._profile or "",
            replacing=", ".join(replaced) or "\u2013",
            keeping=", ".join(kept) or "\u2013",
        )

    async def async_step_summary(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Two summaries, because the two levels have different things to say.

        The basic one has no accuracy to report - one reading per direction reproduces
        itself - and offers the four extra readings and the check that would give it
        one. The precise one reports that check: how far the shutter stopped from where
        the model said it would, at a position nothing was fitted to. Nothing left to
        offer there but Save.
        """
        if self._measured.precise:
            return await self.async_step_summary_precise()
        if self._path == PATH_FIRST:
            return await self.async_step_summary_basic()
        if self._path == PATH_REFINE:
            return await self.async_step_summary_correction()
        return await self.async_step_summary_short()

    async def async_step_summary_basic(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Path A at the basic level: what was measured, and the offer to do better.

        Reached from path A alone, because its text ends on "Migliora la precisione" -
        four more readings and a gap in centimetres - and paths B and C have nothing of
        their own to improve: their numbers are the profile's. A screen that described a
        button two of the three paths did not have was the one thing the live
        walk-through asked for by name (0.5.0 v2 review, BUG-5).
        """
        return self.async_show_menu(
            step_id="summary_basic",
            menu_options=["save", "refine", "cancel_flow"],
            description_placeholders=self._summary_placeholders(self._result()),
        )

    async def async_step_summary_short(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Path B's summary, with nothing left to offer but Save.

        Path B measures no time of its own: its numbers are the profile's, scaled to a
        travel read with a tape, and that is the whole of what it claims. The thorough
        calibration is not offered here because fitting four readings would give this
        cover roll coefficients of its own and make it something other than "one of
        those" - which is the statement path B exists to make. The screen that doubts
        the profile is `verify_result`, and what it offers is the correction.
        """
        return self.async_show_menu(
            step_id="summary_short",
            menu_options=["save", "cancel_flow"],
            description_placeholders=self._summary_placeholders(self._result()),
        )

    async def async_step_summary_correction(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Path C's summary: what was corrected, and the offer to go on to the readings.

        The same offer as `summary_basic`, and for the same reason: the accuracy of
        what has just been measured has not been checked, and four more readings plus
        the check are what would check it. It is a screen of its own rather than a
        second text for `summary_short` because path B reaches that one and has no such
        button - a summary that describes a button the user cannot see is the one thing
        the live walk-through asked for by name (0.5.0 v2 review, BUG-5).
        """
        return self.async_show_menu(
            step_id="summary_correction",
            menu_options=["save", "refine", "cancel_flow"],
            description_placeholders=self._summary_placeholders(self._result()),
        )

    async def async_step_summary_precise(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The same, plus the one number in the whole flow that was verified.

        There is only one text for this screen because there is only one way to reach
        it: `PLAN_PRECISE` ends `verify` -> `summary`, and `precise` is set nowhere but
        `async_step_refine`, which installs that plan. So the verification has always
        happened by the time this is shown, and `{accuracy}` is always its answer - the
        gap at `{percent}` % of the descent, the one position no reading was fitted to.
        A second text for a precise summary with no verification behind it would be a
        screen nobody could open (`test_the_precise_summary_always_has_a_verification`
        is what says so).
        """
        result = self._result()
        return self.async_show_menu(
            step_id="summary_precise",
            menu_options=["save", "cancel_flow"],
            description_placeholders=self._summary_placeholders(result),
        )

    async def async_step_refine(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """"Continua con la calibrazione approfondita": four readings, and then a check.

        The presses are not repeated. With three points per direction the fit solves
        the roll *and* a scale factor on the run time, which is the reaction time of
        those presses being measured on the shutter instead of guessed at.

        Offered by two summaries - path A's and a correction's - and the same plan for
        both: whatever the conversation has timed so far is what the readings correct.
        """
        return await self._async_start_thorough(from_here=True)

    # ------------------------------------------------------------------ saving
    @callback
    def _raw(self) -> dict[str, Any]:
        """The measurements themselves, kept beside the conclusions drawn from them."""
        measured = self._measured
        return {
            "path": self._path,
            "precise": measured.precise,
            "height": measured.height,
            "opening_run": measured.opening.run_time if measured.opening else None,
            "closing_run": measured.closing.run_time if measured.closing else None,
            "slat": measured.slat_time,
            # False for the one scope that times nothing: the two run times above were
            # the ones the cover already moved on, not a pair of presses.
            "times_measured": not measured.times_adopted,
            "descent": [list(point) for point in measured.descent],
            "ascent": [list(point) for point in measured.ascent],
            "deviation_cm": measured.deviation,
        }

    def _merged_with(
        self, record: Any, result: _Result
    ) -> tuple[dict[str, float], float | None]:
        """What Save really writes: this measurement *over* what was already stored.

        A record is not a form. "Affina la calibrazione" measures the two run times and
        has no opinion whatever about the roll coefficients; "Misura di nuovo" on a
        window whose height was measured once and whose `myhome.yaml` does not carry a
        `height:` re-measures nothing of it unless the path asks for it. Writing the
        record whole threw both of those away - silently, on the one screen whose whole
        promise is to make the model *better* (final review, BUG-A). So the keys this
        conversation measured are written over the keys it did not, and a height nobody
        measured here is the one that was already known.

        Path B is the exception: it is not a measurement of this window but a statement
        about which kind of shutter it is, and the numbers measured on it before are
        exactly what it supersedes. Its summary says so.
        """
        if result.follows_profile:
            # Path B measures the height itself, on the screen before the summary.
            return dict(result.overrides), self._measured.height
        kept = dict(record.overrides) if record is not None else {}
        merged = {**kept, **result.overrides}
        height = (
            self._measured.height
            if self._measured.height_measured
            else (record.height if record is not None else None)
        )
        return merged, height

    def _replaced_and_kept(self, result: _Result) -> tuple[list[str], list[str]]:
        """The keys this Save overwrites, and the ones it leaves exactly as they are.

        Written out by key rather than in prose: these are the names the stored record
        is shown under two screens away ("Vedi i valori"), the names of the snippet on
        this very screen, and the same words in all seven languages.
        """
        record = self._store.calibration(self._cover_unique_id or "")
        merged, height = self._merged_with(record, result)
        before = dict(record.overrides) if record is not None else {}
        moving = {key for key in set(before) | set(merged) if before.get(key) != merged.get(key)}
        replaced = sorted(moving)
        kept = sorted(key for key in merged if key not in moving)
        if self._measured.height_measured:
            replaced.append(CONF_HEIGHT)
        elif self._measured.height or height is not None:
            # Known, and not by this conversation: it stays exactly where it is said,
            # which is the record when there is one and the file when there is not.
            kept.append(CONF_HEIGHT)
        return replaced, kept

    @callback
    def _profile_still_wins(self, record: Any, result: _Result) -> bool:
        """Whether the cover goes on following its profile *above* what the file writes.

        `profile_wins` is the flag that puts a profile over the keys the configuration
        file writes for this cover: it means "somebody said, on this installation and
        after that file was written, that this shutter is one of those". A correction
        was taking it away, because the flag was read off `follows_profile` and only
        path B sets that. The cover then fell back under its own file for every key the
        correction did not measure - three run times measured, and both roll
        coefficients silently moved from the profile's to the file's - and
        `Calibration source` reported `guided`, because after the flip the profile
        answered for nothing at all. That is the opposite of what `path_c` promises
        ("everything you do not measure goes on coming from the profile"), on the one
        screen whose whole purpose is to make the model better.

        So a correction keeps it: the profile confirmed on `path_c` is that statement
        being made, and a record that already carried the flag keeps carrying it. The
        same reasoning as `async_step_calibration_edit`, which has never let a hand edit
        of one number change which kind of shutter this is.
        """
        if result.follows_profile:  # path B, which is the statement itself
            return True
        if self._path != PATH_REFINE:
            return False
        return self._profile is not None or bool(record is not None and record.profile_wins)

    async def async_step_save(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Write the store - the first and only thing this conversation writes."""
        result = self._result()
        assert self._cover_unique_id is not None
        if result.profile is not None and self._measured_name:
            await (await self._async_store()).async_set_profile(
                self._measured_name,
                cover_profile_data(
                    self._measured_name,
                    reference_height=result.profile[CONF_REFERENCE_HEIGHT],
                    opening_time=result.profile[CONF_OPENING_TIME],
                    closing_time=result.profile[CONF_CLOSING_TIME],
                    slat_time=result.profile[CONF_SLAT_TIME],
                    opening_roll=result.profile[CONF_OPENING_ROLL],
                    closing_roll=result.profile[CONF_CLOSING_ROLL],
                    reference_cover=self._cover_label,
                    # ...and the same window as an id, which survives a rename and is
                    # what the panel follows back to the cover that is there now. This
                    # is the only place a profile's provenance is ever written: it is
                    # a fact about *this* conversation, which has just held a tape
                    # against that shutter.
                    measured_on=self._cover_unique_id,
                    raw=self._raw(),
                ),
            )
        store = await self._async_store()
        record = store.calibration(self._cover_unique_id)
        merged, height = self._merged_with(record, result)
        await store.async_set_calibration(
            self._cover_unique_id,
            cover_calibration_data(
                self._cover_unique_id,
                profile=self._measured_name or self._profile,
                profile_wins=self._profile_still_wins(record, result),
                height=height,
                overrides=merged or None,
                source=(
                    CALIBRATION_SOURCE_PROFILE
                    if result.follows_profile
                    else CALIBRATION_SOURCE_GUIDED
                ),
                raw=self._raw(),
            ),
        )
        self._mark_changed()
        LOGGER.info(
            "Guided calibration of %s saved (%s)",
            self._cover_label,
            self._measured_name or self._profile or "overrides",
        )
        self._saved_cover = self._cover_label
        self._saved_profile = self._measured_name or self._profile or ""
        self._saved_path = self._path
        # Read off the record that was just written rather than guessed at from the
        # path: a correction leaves `guided` or `profile <name>, adjusted` depending on
        # whether the profile still answers for anything, and the screen quotes the
        # attribute the user is about to go and look at.
        self._saved_source = self._source_now()
        # ...and the same answer in words, for the sentence that tells the user what
        # this shutter is running on now rather than what the attribute spells.
        self._saved_origin = self._origin_in_words(self._cover_unique_id)
        self._disarm()
        self._release()
        # ...and the conversation is over: without this, rendering the `saved` screen
        # re-arms the watchdog through `_touch`, and half an hour later the log carries
        # a WARNING saying nothing was saved about a calibration that was (0.5.0 v2
        # review, RISK-2).
        self._cover = None
        return await self.async_step_saved()

    @callback
    def _source_now(self) -> str:
        """What `Calibration source` says about this cover with the record as it stands."""
        unique_id = self._cover_unique_id or ""
        device = self._cover_config(unique_id)
        if not device:  # pragma: no cover - the cover went away between Save and here
            return CALIBRATION_SOURCE_GUIDED
        return resolve_cover(
            device,
            profiles=self._all_profiles(),
            calibration=self._store.calibration(unique_id),
        ).source

    def _saved_placeholders(self) -> dict[str, str]:
        """The shutter, the profile and the origin, read off what Save actually wrote."""
        return {
            "cover": self._saved_cover,
            "profile": self._saved_profile,
            "source": self._saved_source,
            "origin": self._saved_origin,
        }

    async def async_step_saved(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """What was saved, where it lives, and how to undo it - path A's version.

        Also the router, because what Save really wrote is a different sentence on each
        path: path A measured this shutter and named a profile after it, path B measured
        nothing but its height and gave it somebody else's profile, path C measured a
        few of its numbers over a profile it goes on following. One screen for all three
        told two of them that the shutter "moves on the values just measured", which is
        a sentence the user cannot check against the attributes (final review). Three
        step ids, as the three summaries already are.
        """
        if self._saved_path == PATH_PROFILE:
            return await self.async_step_saved_profile()
        if self._saved_path == PATH_REFINE:
            return await self.async_step_saved_refined()
        return self.async_show_menu(
            step_id="saved",
            menu_options=["calibrate", "init"],
            description_placeholders=self._saved_placeholders(),
        )

    async def async_step_saved_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Path B: the shutter follows a profile, and only its height was measured."""
        return self.async_show_menu(
            step_id="saved_profile",
            menu_options=["calibrate", "init"],
            description_placeholders=self._saved_placeholders(),
        )

    async def async_step_saved_refined(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Path C: its own numbers over a profile it goes on following."""
        return self.async_show_menu(
            step_id="saved_refined",
            menu_options=["calibrate", "init"],
            description_placeholders=self._saved_placeholders(),
        )


# Every guided step is answered with the expiry screen once the watchdog has given the
# shutter back. Wrapping them here rather than writing the check into each one is the
# same argument as the watchdog's own `async_show_*` overrides: a step added later
# cannot forget, because there is no way to add one that is not wrapped. The three
# exceptions are the ways *out* of the expiry screen.
_NEVER_EXPIRES = frozenset({"async_step_expired", "async_step_calibrate", "async_step_cancelled"})


def _guarded(method: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    async def _wrapper(self: Any, user_input: Any = None) -> Any:
        if getattr(self, "_expired", False):
            return await self.async_step_expired()
        return await method(self, user_input)

    _wrapper.__name__ = method.__name__
    _wrapper.__doc__ = method.__doc__
    return _wrapper


for _name, _method in list(vars(GuidedCalibrationMixin).items()):
    if _name.startswith("async_step_") and _name not in _NEVER_EXPIRES:
        setattr(GuidedCalibrationMixin, _name, _guarded(_method))


__all__ = [
    "CLAIM_REASONS",
    "HOMING_ACTION",
    "IDLE_TIMEOUT_SEC",
    "MOVED_IDLE_TIMEOUT_SEC",
    "PRESS_TIMEOUT_SEC",
    "PROBLEM_REASONS",
    "REFINE_THRESHOLD_CM",
    "RUNNING_ACTION",
    "CalibrationContextMixin",
    "CalibrationManagementMixin",
    "GuidedCalibrationMixin",
    "overrides_yaml",
    "parse_number",
    "profile_reference_yaml",
]
