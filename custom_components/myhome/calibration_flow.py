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
  automatic runs of the tape steps do start on their own: there is nothing to be ready
  for while they run.
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
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
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
from homeassistant.util import dt as dt_util

from .calibration import (
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
    timing_from_presses,
)
from .calibration_store import (
    PROFILE_NAME_PATTERN,
    CalibrationStore,
    async_get_store,
    cover_calibration_data,
    cover_profile_data,
    describe_profile,
    loaded_store,
    merged_profiles,
    profile_overrides,
    stored_calibration,
)
from .const import (
    CALIBRATION_SOURCE_GUIDED,
    CALIBRATION_SOURCE_MANUAL,
    CALIBRATION_SOURCE_PROFILE,
    CONF_ADVANCED_SHUTTER,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_PROFILES,
    CONF_ENTITIES,
    CONF_HEIGHT,
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
PLAN_FULL: tuple[str, ...] = (
    "home_closed",
    "open_timed",
    "height",
    "close_timed",
    "half_down",
    "half_up",
    "profile_name",
    "summary",
)
PLAN_PRECISE: tuple[str, ...] = (
    "quarter_down",
    "three_quarter_down",
    "quarter_up",
    "three_quarter_up",
    "verify",
    "summary",
)
# Path B opens with a homing too: the height is measured from the rest of the bottom
# edge to where it is *now*, which only means the whole travel when "now" is the top.
PLAN_PROFILE: tuple[str, ...] = ("home_open", "height", "verify_offer", "summary")
# Paths B and C open the way path A does: the shutter is brought to an end stop and the
# user is asked whether it really got there (the question is the homing stage's
# `done_step`, not a stage of its own). Every homing's wait is bounded by the *modelled*
# run of a model that is, in path C, wrong by hypothesis - that is why the user is in
# path C - so without the confirmation the first measured run can start from a shutter
# that is still travelling.
PLAN_TIMES: tuple[str, ...] = ("home_closed", "open_timed", "close_timed", "summary")
PLAN_TIMES_AND_ROLLS: tuple[str, ...] = (
    "home_closed",
    "open_timed",
    "height",
    "close_timed",
    "half_down",
    "half_up",
    "summary",
)
# What path B's optional check is preceded by: its run goes *down* from the top, so the
# end stop it needs confirming is the open one.
PLAN_VERIFY_B: tuple[str, ...] = ("home_open", "verify_b")

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

PATH_FIRST = "path_a"
PATH_PROFILE = "path_b"
PATH_REFINE = "path_c"

FIELD_COVER = "cover"
FIELD_MEASURED_CM = "measured_cm"
FIELD_PROFILE = "profile"
# "Nessun profilo" in the assignment form. Not the empty string: a select whose option
# is "" renders as a blank line the user cannot tell from an unset field.
NO_PROFILE = "__none__"

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
    # (motor seconds of the run, centimetres read off the tape), in the order measured.
    descent: list[tuple[float, float]] = field(default_factory=list)
    ascent: list[tuple[float, float]] = field(default_factory=list)
    deviation: float | None = None
    precise: bool = False

    @property
    def slat_time(self) -> float:
        """The slat phase, from the one press that measures it (0 until then)."""
        return (self.opening.slat_time if self.opening else None) or 0.0


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
        names = sorted(self._all_profiles())
        if user_input is not None:
            assignments: dict[str, tuple[str | None, float | None]] = {}
            for label, unique_id in fields.items():
                chosen = user_input.get(label, NO_PROFILE)
                profile = None if chosen == NO_PROFILE else str(chosen)
                if profile == self._assigned_profile(unique_id):
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
                    # Only `__none__` is translated; a profile name has no text of its
                    # own and Home Assistant falls back to showing the value itself,
                    # which is the name the user gave it.
                    translation_key="profile_choice",
                )
            )
        return self.async_show_form(
            step_id="assign_covers",
            data_schema=vol.Schema(schema),
            description_placeholders={"covers": ", ".join(fields)},
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
        followers = [self._cover_name(unique_id) for unique_id in self._store.covers_following(name)]
        stored = self._store.profile(name)
        return {
            "profile": name,
            "covers": ", ".join(followers) if followers else "",
            "values": describe_profile(name, stored or dict(self._all_profiles().get(name) or {})),
            "count": str(len(followers)),
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
        orphans = await store.async_remove_profile(name)
        if orphans or had_it:
            self._mark_changed()
        LOGGER.info(
            "Cover profile '%s' deleted; %s shutter(s) went back to the configuration file",
            name,
            len(orphans),
        )
        self._deleted = name
        self._deleted_covers = [self._cover_name(unique_id) for unique_id in orphans]
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
            },
        )

    # ------------------------------------------------------------ one calibration
    async def async_step_calibrations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Which shutter's own measurements the next screens are about."""
        stored = {
            unique_id: self._cover_name(unique_id)
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
        self._shown_at: datetime | None = None
        self._report: RunReport | None = None
        self._pending: tuple[str, float] | None = None
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
        """One screen for both reasons: the shutter is not ours to move right now."""
        return self.async_show_menu(
            step_id=f"refused_{self._claim_refused}",
            menu_options=["calibrate", "init"],
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
        """How far to go: its own times, or its own roll coefficients as well."""
        return self.async_show_menu(
            step_id="refine_scope",
            menu_options=["times_only", "times_and_rolls", "cancel_flow"],
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
        """Leave the conversation, having written nothing (true at every screen)."""
        self._disarm()
        self._release()
        self._reset_calibration()
        return await self.async_step_cancelled()

    async def async_step_cancelled(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Say so, and offer the menu rather than closing the dialog."""
        return self.async_show_menu(step_id="cancelled", menu_options=["calibrate", "init"])

    # ------------------------------------------------------------------ movements
    async def _async_job(self, job: Callable[[], Awaitable[None]]) -> None:
        """Run one step's movements, turning every failure into a reason to show."""
        self._error = None
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

    async def _job_start(self, direction: str) -> None:
        """Let it run free while we watch (it is already at the far end stop)."""
        self._motor_start = await self._cover_to_drive().async_calib_start(direction)

    async def _job_fraction(self, direction: str, fraction: float) -> None:
        cover = self._cover_to_drive()
        await cover.async_calib_home(_other_end(direction))
        self._report = await cover.async_calib_run_fraction(direction, fraction)

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

    # ------------------------------------------------------------------ stage: open
    async def async_step_home_open(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Send the shutter all the way up: the end a downward check starts from."""
        return await self._async_movement(
            step_id="home_open",
            action=HOMING_ACTION[DIRECTION_OPEN],
            job=lambda: self._job_home(DIRECTION_OPEN),
            done_step="home_open_done",
        )

    async def async_step_home_open_done(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The same question path A asks at the bottom, asked at the top."""
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="home_open_done",
            menu_options=["confirm_open", "repeat_step", "not_right"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_confirm_open(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """It is fully open: the check can start from a place we both agree on."""
        return await self._async_advance()

    # ------------------------------------------------------------- stage: the ascent
    async def async_step_open_timed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Bring it to the bottom, then explain the two presses before anything runs.

        Nothing starts here. The first live walk-through had the shutter already
        climbing while the user was still reading what they were supposed to watch for,
        and the measurement it produced was the reaction time of somebody who had not
        been told there was anything to react to.
        """
        return await self._async_movement(
            step_id="open_timed",
            action=HOMING_ACTION[DIRECTION_CLOSE],
            job=lambda: self._job_home(DIRECTION_CLOSE),
            done_step="open_brief",
        )

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
        """The first press: the bottom edge leaves the floor, the slats are open."""
        return self._press_menu("open_lift", "lifted_off")

    async def async_step_lifted_off(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Remember when that press reached us, and wait for the end of the run."""
        if self._timed_out():
            return await self.async_step_problem_timeout()
        self._lift_off = dt_util.utcnow()
        return await self.async_step_open_top()

    async def async_step_open_top(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The second press: the shutter has reached the top and stopped by itself."""
        return self._press_menu("open_top", "stopped_open")

    async def async_step_stopped_open(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Turn the two presses into a slat time and an opening run time."""
        if self._timed_out():
            return await self.async_step_problem_timeout()
        try:
            self._measured.opening = timing_from_presses(
                self._motor_start, self._lift_off, dt_util.utcnow()
            )
        except CalibrationError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_label, err)
            return await self.async_step_problem_bad_point()
        return await self.async_step_open_result()

    async def async_step_open_result(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The two numbers the presses produced, before anything is built on them."""
        opening = self._measured.opening
        self._idle_timeout = MOVED_IDLE_TIMEOUT_SEC
        return self.async_show_menu(
            step_id="open_result",
            menu_options=["accept_step", "repeat_step"],
            description_placeholders=self._placeholders(
                slat=f"{(opening.slat_time or 0.0):.1f}" if opening else "-",
                run=f"{opening.run_time:.1f}" if opening else "-",
            ),
        )

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
        """The travel that was just written down, with a way to write it again."""
        return self.async_show_menu(
            step_id="height_result",
            menu_options=["accept_step", "repeat_measure"],
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
        self._measured.height = None
        self._measured.height_measured = False
        return await self.async_step_height()

    # --------------------------------------------------------- stages: the measured runs
    async def _async_fraction_stage(
        self, *, step_id: str, direction: str, fraction: float, done_step: str
    ) -> ConfigFlowResult:
        self._pending = (direction, fraction)
        return await self._async_movement(
            step_id=step_id,
            action=RUNNING_ACTION[direction],
            job=lambda: self._job_fraction(direction, fraction),
            done_step=done_step,
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
            menu_options=["accept_step", "repeat_tape"],
            description_placeholders=self._placeholders(
                percent=round(fraction * 100),
                measured=f"{points[-1][1]:.1f}" if points else "-",
            ),
        )

    async def async_step_repeat_tape(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Throw the reading away and run the stage's own movements again."""
        # The verification fits nothing, so it has nothing to take back; the two
        # measuring stages do, and the reading has to go before the run is repeated or
        # the fit would be given the same fraction twice.
        if self._tape_target == "descent" and self._measured.descent:
            self._measured.descent.pop()
        elif self._tape_target == "ascent" and self._measured.ascent:
            self._measured.ascent.pop()
        return await self._async_enter()

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
            CONF_SLAT_TIME: self._measured.slat_time,
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
    def _fits(self) -> tuple[DirectionFit, DirectionFit] | None:
        """Fit both directions, or None when this path measured no centimetres."""
        measured = self._measured
        if (
            measured.opening is None
            or measured.closing is None
            or not measured.height
            or not measured.descent
            or not measured.ascent
        ):
            return None
        slat = measured.slat_time
        down = fit_from_run(
            DIRECTION_CLOSE,
            run_time=measured.closing.run_time,
            slat_time=slat,
            measurements=measured.descent,
            height=measured.height,
        )
        up = fit_from_run(
            DIRECTION_OPEN,
            run_time=measured.opening.run_time,
            slat_time=slat,
            measurements=measured.ascent,
            height=measured.height,
        )
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
                CONF_SLAT_TIME: round(measured.slat_time, 1),
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
            return _Result(
                yaml=overrides_yaml(key, values, measured.height),
                overrides=values,
                accuracy_cm=accuracy,
            )
        # Path C, times only: two presses and nothing to fit.
        values = {
            CONF_OPENING_TIME: round(measured.opening.run_time, 1) if measured.opening else 0.0,
            CONF_CLOSING_TIME: round(measured.closing.run_time, 1) if measured.closing else 0.0,
            CONF_SLAT_TIME: round(measured.slat_time, 1),
        }
        return _Result(yaml=overrides_yaml(key, values, None), overrides=values)

    def _summary_placeholders(self, result: _Result) -> dict[str, str]:
        # The unit travels with the value, so a path that did not measure something
        # reads "-" rather than "- cm".
        height = f"{self._measured.height:.0f} cm" if self._measured.height else "\u2013"
        accuracy = "\u2013" if result.accuracy_cm is None else f"{result.accuracy_cm:.1f} cm"
        replaced, kept = self._replaced_and_kept(result)
        return self._placeholders(
            yaml=f"```yaml\n{result.yaml}```",
            height=height,
            accuracy=accuracy,
            percent=round(VERIFY_RUN * 100),
            profile=self._measured_name or self._profile or "",
            replacing=", ".join(replaced) or "\u2013",
            keeping=", ".join(kept) or "\u2013",
        )

    async def async_step_summary(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Two summaries, because the two levels have different things to say.

        The basic one has no accuracy to report - one reading per direction reproduces
        itself - and offers the four extra readings that would give it one. The precise
        one has a number that was measured at a position nothing was fitted to, and
        nothing left to offer but Save.
        """
        if self._measured.precise:
            return await self.async_step_summary_precise()
        if self._path == PATH_FIRST:
            return await self.async_step_summary_basic()
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
        """The same summary for paths B and C, with nothing left to offer but Save."""
        return self.async_show_menu(
            step_id="summary_short",
            menu_options=["save", "cancel_flow"],
            description_placeholders=self._summary_placeholders(self._result()),
        )

    async def async_step_summary_precise(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The same, plus the one number in the whole flow that was verified."""
        result = self._result()
        return self.async_show_menu(
            step_id="summary_precise",
            menu_options=["save", "cancel_flow"],
            description_placeholders=self._summary_placeholders(result),
        )

    async def async_step_refine(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """"Migliora la precisione": four more tape readings, and then a check.

        The presses are not repeated. With three points per direction the fit solves
        the roll *and* a scale factor on the run time, which is the reaction time of
        those presses being measured on the shutter instead of guessed at.
        """
        self._measured.precise = True
        self._plan = self._plan[: self._index] + list(PLAN_PRECISE)
        return await self._async_enter()

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
                profile_wins=result.follows_profile,
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
        self._disarm()
        self._release()
        # ...and the conversation is over: without this, rendering the `saved` screen
        # re-arms the watchdog through `_touch`, and half an hour later the log carries
        # a WARNING saying nothing was saved about a calibration that was (0.5.0 v2
        # review, RISK-2).
        self._cover = None
        return await self.async_step_saved()

    async def async_step_saved(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """What was saved, where it lives, and how to undo it."""
        return self.async_show_menu(
            step_id="saved",
            menu_options=["calibrate", "init"],
            description_placeholders={
                "cover": self._saved_cover,
                "profile": self._saved_profile,
            },
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
