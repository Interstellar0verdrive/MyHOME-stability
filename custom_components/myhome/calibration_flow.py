"""The guided cover calibration as config subentry flows (0.5.0, phase 2).

Phase 1 built the two halves this module sits between: the maths (`calibration.py`),
which turns button presses and tape readings into a travel model, and the runner
(`cover.py`, the four `async_calib_*` primitives), which drives one shutter and reports
what the bus really did. What was missing was the conversation - and a calibration is a
conversation, because half of the measurements only a person standing in the room can
make.

The shape of that conversation is the whole point of the file, so it is worth stating
before the code:

* **No stopwatch.** The integration already knows when the motor starts (the actuator
  answers our frame with its own status), so the user is never asked to time anything.
  They press a button when something *happens* - the bottom edge lifts off the floor,
  the shutter stops - and the time is the instant that press reaches Home Assistant
  minus the instant the motor really began to turn.
* **Nothing is written before Save.** Every screen up to the summary only moves the
  shutter, which is an ordinary command the estimate follows as it follows any other.
  Closing the dialog at any point leaves the configuration, the storage and the shutter
  exactly as they were.
* **Every measuring step is self-contained.** It first brings the shutter to the end
  stop it needs and then does its one thing, so "Repeat this step" is always safe and
  never asks the user to remember where they were. Every measuring screen carries that
  button, and next to it "It did not do what it should", which sends a stop, re-homes
  and starts the step again.
* **Verbose, plain language.** Each screen says what is about to happen and what the
  user has to do. The texts live in `strings.json` (Italian first in the FLOW
  document, then en/fr/nl); this module only decides which screen comes next.

The three paths, chosen on the second screen:

A. *the first shutter of its kind* - the full measurement, which produces a **profile**
   (a `cover_profile` subentry) plus this window's own height (a `cover_calibration`);
B. *the same as one already calibrated* - pick the profile, measure the height with a
   tape, optionally check it at half travel;
C. *refine this one* - it follows a profile but gets it wrong: measure its own times,
   and if needed its own roll coefficients, and store them as overrides.

The steps of a path are a **plan**: a list of stage names walked in order
(`_async_advance`), which is what makes "Repeat this step" a one-liner (re-enter the
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
from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
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
    timing_from_presses,
)
from .calibration_store import (
    PROFILE_NAME_PATTERN,
    async_set_cover_calibration,
    async_set_cover_profile,
    cover_calibration_data,
    cover_profile_data,
    merged_profiles,
    stored_calibrations,
    stored_profiles,
)
from .const import (
    CONF_ADVANCED_SHUTTER,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_PROFILES,
    CONF_COVER_UNIQUE_ID,
    CONF_ENTITIES,
    CONF_HEIGHT,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PLATFORMS,
    CONF_PROFILE,
    CONF_RAW,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
    DIRECTION_CLOSE,
    DIRECTION_OPEN,
    DOMAIN,
    LOGGER,
    SUBENTRY_COVER_CALIBRATION,
    SUBENTRY_COVER_PROFILE,
)
from .cover import calibration_yaml
from .validate import derive_cover_from_profile

# How long a measuring screen waits for the press it is about. The user is watching a
# shutter that takes twenty seconds to run: a minute and a half is generous for the
# press itself and short enough that a screen left open over lunch does not come back
# with a "measurement" of four thousand seconds. A flow cannot push a new screen at a
# browser, so the window is checked when the press finally arrives (see `_timed_out`).
PRESS_TIMEOUT_SEC = 90.0

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

# The tape is read to the nearest centimetre; a window is at most a few metres of
# curtain. The bounds are the selector's, so a mistyped 1950 is refused by the form
# rather than by the fit three screens later.
MIN_HEIGHT_CM = 20.0
MAX_HEIGHT_CM = 500.0

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
# and "Repeat this step" re-enters the stage it is on.
PLAN_FULL: tuple[str, ...] = (
    "home_closed",
    "open_timed",
    "height",
    "close_timed",
    "half_down",
    "half_up",
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
PLAN_PROFILE: tuple[str, ...] = ("height", "verify_offer", "summary")
PLAN_TIMES: tuple[str, ...] = ("open_timed", "close_timed", "summary")
PLAN_TIMES_AND_ROLLS: tuple[str, ...] = (
    "open_timed",
    "height",
    "close_timed",
    "half_down",
    "half_up",
    "summary",
)

# The progress text of an automatic run, by the direction it runs in. A mapping rather
# than a conditional expression so that every progress action of the flow can be found
# (and checked against the translations) without reading the code that uses it.
RUNNING_ACTION = {DIRECTION_CLOSE: "running_down", DIRECTION_OPEN: "running_up"}

PATH_FIRST = "path_a"
PATH_PROFILE = "path_b"
PATH_REFINE = "path_c"

FIELD_COVER = "cover"
FIELD_MEASURED_CM = "measured_cm"

_NAME_RE = re.compile(PROFILE_NAME_PATTERN)
_NOT_A_NAME = re.compile(r"[^A-Za-z0-9_]+")


def _height_selector() -> NumberSelector:
    """Centimetres of curtain travel, as a box with a unit."""
    return NumberSelector(
        NumberSelectorConfig(
            min=MIN_HEIGHT_CM, max=MAX_HEIGHT_CM, step=0.5, mode=NumberSelectorMode.BOX, unit_of_measurement="cm"
        )
    )


def _measurement_selector() -> NumberSelector:
    """A tape reading: zero is legitimate (the bar is on its rest)."""
    return NumberSelector(
        NumberSelectorConfig(
            min=0, max=MAX_HEIGHT_CM, step=0.5, mode=NumberSelectorMode.BOX, unit_of_measurement="cm"
        )
    )


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


def profile_reference_yaml(cover_key: str, profile: str, height: float) -> str:
    """The two lines path B is really about: follow that profile, at this height."""
    return f"cover:\n  {cover_key}:\n    {CONF_PROFILE}: {profile}\n    {CONF_HEIGHT}: {round(height, 1)}\n"


@dataclass(slots=True)
class _Measured:
    """Everything the conversation has collected, and nothing that was saved.

    It lives for as long as the dialog does and is thrown away with it - which is the
    "nothing is written before Save" of the UX, stated as a data structure.
    """

    height: float | None = None
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
    shutter); `overrides` by path C; path B fills in neither and carries the height.
    """

    yaml: str
    profile: dict[str, float] | None = None
    overrides: dict[str, float] = field(default_factory=dict)
    accuracy_cm: float | None = None


class CoverCalibrationFlow(ConfigSubentryFlow):
    """The guided calibration of one basic cover, screen by screen."""

    def __init__(self) -> None:
        """Start with nothing measured and no shutter claimed."""
        self._cover: Any = None
        self._cover_unique_id: str | None = None
        self._cover_name: str = ""
        self._cover_key: str = ""
        self._path: str = PATH_FIRST
        self._plan: list[str] = []
        self._index: int = 0
        self._measured = _Measured()
        self._profile: str | None = None
        self._profile_name: str | None = None
        self._task: Any = None
        self._error: str | None = None
        self._stop_first: bool = False
        self._motor_start: datetime | None = None
        self._lift_off: datetime | None = None
        self._shown_at: datetime | None = None
        self._report: RunReport | None = None
        self._pending: tuple[str, float] | None = None
        self._session: contextlib.ExitStack | None = None

    # ------------------------------------------------------------------ housekeeping
    @callback
    def async_remove(self) -> None:
        """Let the shutter go when the dialog closes, however it closed.

        The whole conversation holds one calibration session on the cover (so the
        `Calibrating` attribute does not blink off between two screens while the user
        reads one), and a flow that is abandoned - the X, a browser closed, a timeout -
        gets no other chance to give it back.
        """
        if self._session is not None:
            self._session.close()
            self._session = None

    @property
    def _mac(self) -> str:
        return str(self._get_entry().data[CONF_MAC])

    def _covers(self) -> dict[str, dict[str, Any]]:
        """The basic covers of this gateway, by device key, or {} when it is not loaded.

        Advanced covers are left out on purpose and not merely disabled: they report
        their own position, so there is no travel model to calibrate and every runner
        primitive refuses them (`REASON_ADVANCED`).
        """
        gateway = self.hass.data.get(DOMAIN, {}).get(self._mac) or {}
        covers = (gateway.get(CONF_PLATFORMS) or {}).get(COVER) or {}
        return {key: cfg for key, cfg in covers.items() if not cfg.get(CONF_ADVANCED_SHUTTER)}

    def _yaml_profiles(self) -> Mapping[str, Mapping[str, Any]]:
        gateway = self.hass.data.get(DOMAIN, {}).get(self._mac) or {}
        return gateway.get(CONF_COVER_PROFILES) or {}

    def _all_profiles(self) -> dict[str, Mapping[str, Any]]:
        """Both namespaces at once, exactly as a cover resolves them."""
        return merged_profiles(self._yaml_profiles(), stored_profiles(self._get_entry()))

    def _placeholders(self, **extra: Any) -> dict[str, str]:
        """Every screen names the shutter it is about; the rest is per step."""
        return {"cover": self._cover_name, **{key: str(value) for key, value in extra.items()}}

    @callback
    def _claim(self, unique_id: str) -> bool:
        """Take hold of one cover for the rest of the conversation."""
        for key, cfg in self._covers().items():
            if f"{self._mac}-{key}" != unique_id:
                continue
            entity = (cfg.get(CONF_ENTITIES) or {}).get(COVER)
            if entity is None:
                return False
            self._cover = entity
            self._cover_unique_id = unique_id
            self._cover_key = key
            self._cover_name = str(cfg.get(CONF_NAME) or entity.entity_id)
            self._session = contextlib.ExitStack()
            self._session.enter_context(entity.calibration_session())
            return True
        return False

    # ------------------------------------------------------------------ the entrances
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """What the tool is for, and what to expect from it, before any choice.

        The addendum of 12 September: a user who arrives here from "Add" deserves to
        know that the percentage of a basic cover is an estimate, that the calibration
        makes it a good one rather than a perfect one, and that the covers which report
        their own position are missing from the list because they do not need this.
        """
        if not self._covers():
            return self.async_abort(reason="no_basic_covers")
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
        return await self.async_step_cover()

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Re-running the calibration of a cover that already has one.

        There is nothing in a stored calibration that can be meaningfully edited in a
        form - it is a set of measurements - so "Reconfigure" is the measurement again,
        on the cover the subentry names, and Save replaces what is there.
        """
        subentry = self._get_reconfigure_subentry()
        unique_id = str(subentry.data.get(CONF_COVER_UNIQUE_ID, ""))
        if not self._claim(unique_id):
            return self.async_abort(reason="unknown_cover")
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure", data_schema=vol.Schema({}), description_placeholders=self._placeholders()
            )
        return await self.async_step_path()

    async def async_step_cover(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Pick the shutter. Only the basic ones are listed (see `_covers`)."""
        covers = {
            f"{self._mac}-{key}": str(cfg.get(CONF_NAME) or key) for key, cfg in self._covers().items()
        }
        if user_input is not None:
            if not self._claim(user_input[FIELD_COVER]):
                return self.async_abort(reason="unknown_cover")
            return await self.async_step_path()
        return self.async_show_form(
            step_id="cover",
            data_schema=vol.Schema({vol.Required(FIELD_COVER): vol.In(covers)}),
        )

    async def async_step_path(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The three paths - the last two only once there is a profile to follow."""
        options = [PATH_FIRST]
        if self._all_profiles():
            options += [PATH_PROFILE, PATH_REFINE]
        return self.async_show_menu(
            step_id="path", menu_options=options, description_placeholders=self._placeholders()
        )

    # ------------------------------------------------------------------ path A
    async def async_step_path_a(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The warning before the first movement: the shutter is about to run, twice over."""
        if user_input is None:
            return self.async_show_form(
                step_id="path_a", data_schema=vol.Schema({}), description_placeholders=self._placeholders()
            )
        self._path = PATH_FIRST
        self._measured = _Measured()
        return await self._async_start_plan(PLAN_FULL)

    # ------------------------------------------------------------------ path B
    async def async_step_path_b(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """This window is one of a kind already measured: name the kind."""
        profiles = sorted(self._all_profiles())
        if not profiles:
            return self.async_abort(reason="no_profiles")
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
    async def async_step_path_c(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """This window follows a profile and gets it wrong: measure what it needs."""
        profiles = sorted(self._all_profiles())
        if not profiles:
            return self.async_abort(reason="no_profiles")
        if user_input is not None:
            self._path = PATH_REFINE
            self._profile = user_input[CONF_PROFILE]
            # A height already measured (path B's check sent us here) is kept: it is
            # the same window and the same tape.
            self._measured = _Measured(height=self._measured.height)
            return await self.async_step_refine_scope()
        current = self._profile or self._current_profile() or profiles[0]
        return self.async_show_form(
            step_id="path_c",
            data_schema=vol.Schema(
                {vol.Required(CONF_PROFILE, default=current if current in profiles else profiles[0]): vol.In(profiles)}
            ),
            description_placeholders=self._placeholders(),
        )

    def _current_profile(self) -> str | None:
        """The profile this cover follows today, stored one first, then the file's."""
        stored = stored_calibrations(self._get_entry()).get(self._cover_unique_id or "")
        if stored is not None and stored.profile:
            return stored.profile
        cfg = self._covers().get(self._cover_key) or {}
        return cfg.get(CONF_PROFILE)

    async def async_step_refine_scope(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """How far to go: its own times, or its own roll coefficients as well."""
        return self.async_show_menu(
            step_id="refine_scope",
            menu_options=["times_only", "times_and_rolls", "cancel_flow"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_times_only(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Two presses: this motor is slower (or faster) than the profile's."""
        return await self._async_start_plan(PLAN_TIMES)

    async def async_step_times_and_rolls(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Two presses and two tape readings: this curtain winds differently too."""
        return await self._async_start_plan(PLAN_TIMES_AND_ROLLS)

    # ------------------------------------------------------------------ the plan
    async def _async_start_plan(self, plan: tuple[str, ...]) -> SubentryFlowResult:
        self._plan = list(plan)
        self._index = 0
        return await self._async_enter()

    async def _async_enter(self) -> SubentryFlowResult:
        """(Re-)enter the stage the pointer is on, with its own state cleared."""
        self._task = None
        self._error = None
        self._report = None
        return await getattr(self, f"async_step_{self._plan[self._index]}")()

    async def _async_advance(self) -> SubentryFlowResult:
        self._index += 1
        return await self._async_enter()

    async def async_step_repeat_step(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """"Repeat this step": only this one, and only its own movements."""
        return await self._async_enter()

    async def async_step_not_right(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """"It did not do what it should": stop it, then run the step again.

        The stop is what makes this different from "Repeat": something is moving that
        should not be, or is moving the wrong way, and the step's own homing would
        otherwise queue behind it.
        """
        self._stop_first = True
        return await self._async_enter()

    async def async_step_cancel_flow(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Leave, having written nothing (which is true at every screen)."""
        return self.async_abort(reason="cancelled")

    # ------------------------------------------------------------------ movements
    async def _async_job(self, job: Callable[[], Awaitable[None]]) -> None:
        """Run one step's movements, turning every failure into a reason to show."""
        self._error = None
        try:
            if self._stop_first:
                self._stop_first = False
                with contextlib.suppress(CalibrationError):
                    await self._cover.async_calib_stop()
            await job()
        except CalibrationError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_name, err)
            self._error = err.reason if err.reason in PROBLEM_REASONS else REASON_UNKNOWN
        except HomeAssistantError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_name, err)
            self._error = REASON_UNKNOWN
        except Exception:  # noqa: BLE001 - a flow must not leave a dialog spinning
            LOGGER.exception("Guided calibration of %s failed unexpectedly", self._cover_name)
            self._error = REASON_UNKNOWN

    async def _async_movement(
        self, *, step_id: str, action: str, job: Callable[[], Awaitable[None]], done_step: str, **extra: Any
    ) -> SubentryFlowResult:
        """The progress screen of one stage: start the movements, then move on.

        Home Assistant re-enters this step when the task finishes, which is why the
        task is the step's only state: no task means "start it", a task that is not
        done means "keep showing the bar".
        """
        if self._task is None:
            self._task = self.hass.async_create_task(
                self._async_job(job), f"myhome guided calibration {step_id}", eager_start=False
            )
        if not self._task.done():
            return self.async_show_progress(
                step_id=step_id,
                progress_action=action,
                progress_task=self._task,
                description_placeholders=self._placeholders(**extra),
            )
        self._task = None
        if self._error is not None:
            return self.async_show_progress_done(next_step_id=f"problem_{self._error}")
        return self.async_show_progress_done(next_step_id=done_step)

    async def _job_home(self, direction: str) -> None:
        await self._cover.async_calib_home(direction)

    async def _job_timed(self, direction: str) -> None:
        """Bring the shutter to the far end, then let it run free while we watch."""
        await self._cover.async_calib_home(_other_end(direction))
        self._motor_start = await self._cover.async_calib_start(direction)

    async def _job_fraction(self, direction: str, fraction: float) -> None:
        await self._cover.async_calib_home(_other_end(direction))
        self._report = await self._cover.async_calib_run_fraction(direction, fraction)

    # ------------------------------------------------------------------ the presses
    def _timed_out(self) -> bool:
        """True when the press we were waiting for took longer than a user would."""
        if self._shown_at is None:  # pragma: no cover - every press step sets it first
            return False
        return (dt_util.utcnow() - self._shown_at).total_seconds() > PRESS_TIMEOUT_SEC

    @callback
    def _press_menu(self, step_id: str, action: str) -> SubentryFlowResult:
        """A screen with one thing to press when something happens, and two ways out."""
        self._shown_at = dt_util.utcnow()
        return self.async_show_menu(
            step_id=step_id,
            menu_options=[action, "repeat_step", "not_right"],
            description_placeholders=self._placeholders(),
        )

    @callback
    def _problem(self, reason: str) -> SubentryFlowResult:
        """The screen for one kind of failure, with "Repeat this step" next to it."""
        return self.async_show_menu(
            step_id=f"problem_{reason}",
            menu_options=["repeat_step", "cancel_flow"],
            description_placeholders=self._placeholders(),
        )

    # Each reason has a screen of its own rather than a sentence in a placeholder: a
    # shutter that did not answer and a gateway that dropped the frame need different
    # things done about them, and a translated text can say so.
    async def async_step_problem_no_echo(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The shutter never reported that it had started moving."""
        return self._problem(REASON_NO_ECHO)

    async def async_step_problem_not_delivered(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The gateway never wrote our command to the bus."""
        return self._problem(REASON_NOT_DELIVERED)

    async def async_step_problem_not_stopped(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Our stop was refused or dropped: the shutter ran on to its end stop."""
        return self._problem(REASON_NOT_STOPPED)

    async def async_step_problem_busy(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Something else is already moving this shutter."""
        return self._problem(REASON_BUSY)

    async def async_step_problem_bad_point(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The presses cannot both be right (the second came before the first)."""
        return self._problem(REASON_BAD_POINT)

    async def async_step_problem_timeout(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Nobody pressed anything for a minute and a half."""
        return self._problem(REASON_TIMEOUT)

    async def async_step_problem_unknown(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Anything else at all; the log has the detail."""
        return self._problem(REASON_UNKNOWN)

    # ------------------------------------------------------------------ stage: close
    async def async_step_home_closed(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Send the shutter all the way down, so every later measurement has an origin."""
        return await self._async_movement(
            step_id="home_closed",
            action="homing_closed",
            job=lambda: self._job_home(DIRECTION_CLOSE),
            done_step="home_closed_done",
        )

    async def async_step_home_closed_done(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Ask the user to confirm what the estimate believes: it is really closed."""
        self._shown_at = dt_util.utcnow()
        return self.async_show_menu(
            step_id="home_closed_done",
            menu_options=["confirm_closed", "repeat_step", "not_right"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_confirm_closed(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """It is closed: on to the measured opening."""
        return await self._async_advance()

    # ------------------------------------------------------------------ stage: open run
    async def async_step_open_timed(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Close it (it may already be), then start it upwards and hand over the watch."""
        return await self._async_movement(
            step_id="open_timed",
            action="starting_open",
            job=lambda: self._job_timed(DIRECTION_OPEN),
            done_step="open_lift",
        )

    async def async_step_open_lift(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The first press: the bottom edge leaves the floor, the slats are open."""
        return self._press_menu("open_lift", "lifted_off")

    async def async_step_lifted_off(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Remember when that press reached us, and wait for the end of the run."""
        if self._timed_out():
            return await self.async_step_problem_timeout()
        self._lift_off = dt_util.utcnow()
        return await self.async_step_open_top()

    async def async_step_open_top(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The second press: the shutter has reached the top and stopped by itself."""
        return self._press_menu("open_top", "stopped_open")

    async def async_step_stopped_open(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Turn the two presses into a slat time and an opening run time."""
        if self._timed_out():
            return await self.async_step_problem_timeout()
        try:
            self._measured.opening = timing_from_presses(self._motor_start, self._lift_off, dt_util.utcnow())
        except CalibrationError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_name, err)
            return await self.async_step_problem_bad_point()
        return await self._async_advance()

    # ------------------------------------------------------------------ stage: close run
    async def async_step_close_timed(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Open it fully, then start it downwards; one press ends this one."""
        return await self._async_movement(
            step_id="close_timed",
            action="starting_close",
            job=lambda: self._job_timed(DIRECTION_CLOSE),
            done_step="close_bottom",
        )

    async def async_step_close_bottom(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The press that ends the descent: it is down and the slats have closed."""
        return self._press_menu("close_bottom", "stopped_closed")

    async def async_step_stopped_closed(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The closing run time. Its slat phase is the opening one (phase 2 decision)."""
        if self._timed_out():
            return await self.async_step_problem_timeout()
        try:
            self._measured.closing = timing_from_presses(self._motor_start, None, dt_util.utcnow())
        except CalibrationError as err:
            LOGGER.warning("Guided calibration of %s: %s", self._cover_name, err)
            return await self.async_step_problem_bad_point()
        return await self._async_advance()

    # ------------------------------------------------------------------ stage: height
    async def async_step_height(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The one measurement everything else is scaled by: the curtain travel."""
        if user_input is not None:
            self._measured.height = float(user_input[CONF_HEIGHT])
            return await self._async_advance()
        default = self._measured.height or (self._covers().get(self._cover_key) or {}).get(CONF_HEIGHT)
        schema = {
            vol.Required(CONF_HEIGHT, description={"suggested_value": default}): _height_selector()
        }
        return self.async_show_form(
            step_id="height", data_schema=vol.Schema(schema), description_placeholders=self._placeholders()
        )

    # --------------------------------------------------------- stages: the measured runs
    async def _async_fraction_stage(
        self, *, step_id: str, direction: str, fraction: float, done_step: str
    ) -> SubentryFlowResult:
        self._pending = (direction, fraction)
        return await self._async_movement(
            step_id=step_id,
            action=RUNNING_ACTION[direction],
            job=lambda: self._job_fraction(direction, fraction),
            done_step=done_step,
            percent=round(fraction * 100),
        )

    async def async_step_half_down(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Open fully, run half the curtain down: the descent's own coefficient."""
        return await self._async_fraction_stage(
            step_id="half_down", direction=DIRECTION_CLOSE, fraction=HALF_RUN, done_step="measure_descent"
        )

    async def async_step_quarter_down(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """A quarter of the way down: the second point of the descent."""
        return await self._async_fraction_stage(
            step_id="quarter_down", direction=DIRECTION_CLOSE, fraction=QUARTER_RUN, done_step="measure_descent"
        )

    async def async_step_three_quarter_down(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Three quarters of the way down: the third."""
        return await self._async_fraction_stage(
            step_id="three_quarter_down",
            direction=DIRECTION_CLOSE,
            fraction=THREE_QUARTER_RUN,
            done_step="measure_descent",
        )

    async def async_step_half_up(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Close fully, run the slats plus half the curtain up."""
        return await self._async_fraction_stage(
            step_id="half_up", direction=DIRECTION_OPEN, fraction=HALF_RUN, done_step="measure_ascent"
        )

    async def async_step_quarter_up(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """A quarter of the way up."""
        return await self._async_fraction_stage(
            step_id="quarter_up", direction=DIRECTION_OPEN, fraction=QUARTER_RUN, done_step="measure_ascent"
        )

    async def async_step_three_quarter_up(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Three quarters of the way up."""
        return await self._async_fraction_stage(
            step_id="three_quarter_up",
            direction=DIRECTION_OPEN,
            fraction=THREE_QUARTER_RUN,
            done_step="measure_ascent",
        )

    # ------------------------------------------------------------------ the tape
    def _measurement_form(self, step_id: str, errors: dict[str, str] | None = None) -> SubentryFlowResult:
        direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required(FIELD_MEASURED_CM): _measurement_selector()}),
            errors=errors,
            description_placeholders=self._placeholders(
                percent=round(fraction * 100), direction=direction
            ),
        )

    def _accept_measurement(self, user_input: Mapping[str, Any]) -> float | None:
        """A tape reading that fits inside the travel this window was said to have.

        A bar measured above the whole curtain travel is a tape read from the wrong
        reference (the floor rather than where the bottom edge rests when closed), and
        the fit would refuse it three screens later with nothing to correct.
        """
        value = float(user_input[FIELD_MEASURED_CM])
        height = self._measured.height
        if height is not None and value > height:
            return None
        return value

    async def async_step_measure_descent(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """How far the bar came down: one point of the descent."""
        if user_input is None:
            return self._measurement_form("measure_descent")
        value = self._accept_measurement(user_input)
        if value is None or self._report is None:
            return self._measurement_form("measure_descent", errors={FIELD_MEASURED_CM: "above_the_travel"})
        self._measured.descent.append((self._report.motor_seconds, value))
        return await self._async_advance()

    async def async_step_measure_ascent(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """How far the bar came up: one point of the ascent."""
        if user_input is None:
            return self._measurement_form("measure_ascent")
        value = self._accept_measurement(user_input)
        if value is None or self._report is None:
            return self._measurement_form("measure_ascent", errors={FIELD_MEASURED_CM: "above_the_travel"})
        self._measured.ascent.append((self._report.motor_seconds, value))
        return await self._async_advance()

    # ------------------------------------------------------------------ verification
    async def async_step_verify(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The precise level's last run, to a place no measurement taught the model."""
        return await self._async_fraction_stage(
            step_id="verify", direction=DIRECTION_CLOSE, fraction=VERIFY_RUN, done_step="measure_verify"
        )

    async def async_step_verify_offer(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Path B: measuring the height is enough, but the shutter can be asked."""
        return self.async_show_menu(
            step_id="verify_offer",
            menu_options=["verify_now", "skip_verify"],
            description_placeholders=self._placeholders(),
        )

    async def async_step_verify_now(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Graft the check onto the plan, right here."""
        self._plan.insert(self._index + 1, "verify_b")
        return await self._async_advance()

    async def async_step_skip_verify(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Take the profile at its word."""
        return await self._async_advance()

    async def async_step_verify_b(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Path B's check: half way down from the top, then a tape."""
        return await self._async_fraction_stage(
            step_id="verify_b", direction=DIRECTION_CLOSE, fraction=VERIFY_RUN_PROFILE, done_step="measure_verify"
        )

    async def async_step_measure_verify(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The reading the model is compared against, rather than fitted to."""
        if user_input is None:
            return self._measurement_form("measure_verify")
        value = self._accept_measurement(user_input)
        if value is None:
            return self._measurement_form("measure_verify", errors={FIELD_MEASURED_CM: "above_the_travel"})
        self._measured.deviation = self._deviation(value)
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
        if fits is None:  # pragma: no cover - the precise level fits before it verifies
            return None
        down, up = fits
        return {
            CONF_CLOSING_TIME: down.corrected_run_time,
            CONF_OPENING_TIME: up.corrected_run_time,
            CONF_SLAT_TIME: self._measured.slat_time,
            CONF_CLOSING_ROLL: down.fit.roll,
            CONF_OPENING_ROLL: up.fit.roll,
        }

    async def async_step_verify_result(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Show the deviation in centimetres, and what can be done about it."""
        deviation = self._measured.deviation
        off_by = abs(deviation) if deviation is not None else 0.0
        options = ["continue_step", "repeat_step"]
        if self._path == PATH_PROFILE and off_by > REFINE_THRESHOLD_CM:
            options = ["path_c", "continue_step", "repeat_step"]
        return self.async_show_menu(
            step_id="verify_result",
            menu_options=options,
            description_placeholders=self._placeholders(deviation=f"{off_by:.0f}"),
        )

    async def async_step_continue_step(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Carry on with the plan from wherever the current stage left off."""
        return await self._async_advance()

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
        name = self._profile_name or _suggested_name(getattr(self._cover, "entity_id", ""))
        key = _suggested_name(getattr(self._cover, "entity_id", ""))
        if self._path == PATH_PROFILE:
            height = measured.height or 0.0
            return _Result(yaml=profile_reference_yaml(key, self._profile or "", height))
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
            accuracy = max(down.fit.max_residual_cm, up.fit.max_residual_cm)
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

    async def async_step_summary(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """The numbers in plain sight, and the same numbers as YAML for the file-minded."""
        result = self._result()
        options = ["save"]
        if self._path == PATH_FIRST and not self._measured.precise:
            options.append("refine")
        options.append("cancel_flow")
        accuracy = "-" if result.accuracy_cm is None else f"{result.accuracy_cm:.1f}"
        return self.async_show_menu(
            step_id="summary",
            menu_options=options,
            description_placeholders=self._placeholders(
                yaml=f"```yaml\n{result.yaml}```",
                accuracy=accuracy,
                height=f"{self._measured.height:.0f}" if self._measured.height else "-",
            ),
        )

    async def async_step_refine(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """"Improve the accuracy": four more tape readings, and then a check.

        The presses are not repeated. With three points per direction the fit solves
        the roll *and* a scale factor on the run time, which is the reaction time of
        those presses being measured on the shutter instead of guessed at.
        """
        self._measured.precise = True
        self._plan = self._plan[: self._index] + list(PLAN_PRECISE)
        return await self._async_enter()

    # ------------------------------------------------------------------ saving
    async def async_step_save(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Path A names the kind of shutter first; the other two have nothing to name."""
        if self._path == PATH_FIRST:
            return await self.async_step_profile_name()
        return self._async_store()

    async def async_step_profile_name(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Name the profile: a YAML key, because that is what it may become."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = str(user_input[CONF_NAME]).strip()
            if not _NAME_RE.match(name):
                errors[CONF_NAME] = "invalid_name"
            elif name in self._all_profiles():
                errors[CONF_NAME] = "name_in_use"
            else:
                self._profile_name = name
                return self._async_store()
        suggested = (user_input or {}).get(CONF_NAME) or _suggested_name(
            getattr(self._cover, "entity_id", "")
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
            description_placeholders=self._placeholders(),
        )

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

    @callback
    def _async_store(self) -> SubentryFlowResult:
        """Write the subentries - the first and only thing this flow writes.

        Through the phase 1 helpers rather than through `async_create_entry`, because
        they *replace*: a shutter has one calibration and a kind of shutter one
        profile, and `async_add_subentry` would refuse the second run outright. The
        flow therefore ends on an abort with a reason that says it worked, which is
        Home Assistant's way of closing a dialog that has nothing left to create.
        """
        entry = self._get_entry()
        result = self._result()
        assert self._cover_unique_id is not None
        if result.profile is not None and self._profile_name:
            async_set_cover_profile(
                self.hass,
                entry,
                self._profile_name,
                cover_profile_data(
                    self._profile_name,
                    reference_height=result.profile[CONF_REFERENCE_HEIGHT],
                    opening_time=result.profile[CONF_OPENING_TIME],
                    closing_time=result.profile[CONF_CLOSING_TIME],
                    slat_time=result.profile[CONF_SLAT_TIME],
                    opening_roll=result.profile[CONF_OPENING_ROLL],
                    closing_roll=result.profile[CONF_CLOSING_ROLL],
                    raw=self._raw(),
                ),
                reload=False,
            )
        async_set_cover_calibration(
            self.hass,
            entry,
            self._cover_unique_id,
            cover_calibration_data(
                self._cover_unique_id,
                profile=self._profile_name or self._profile,
                height=self._measured.height,
                overrides=result.overrides or None,
                raw=self._raw(),
            ),
            title=self._cover_name,
        )
        LOGGER.info(
            "Guided calibration of %s saved (%s)",
            self._cover_name,
            self._profile_name or self._profile or "overrides",
        )
        return self.async_abort(
            reason="calibration_saved", description_placeholders=self._placeholders()
        )


class CoverProfileFlow(ConfigSubentryFlow):
    """A stored profile: something to look at and to delete, not to type.

    A profile is a set of measurements of one model of shutter, and there is nothing in
    it a form could sensibly ask for - every number came off a tape or a press. So this
    flow shows what is stored and says where it came from; Home Assistant's own delete
    button removes it, and running the guided calibration again under the same name is
    what replaces it.
    """

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """There is no way to add a profile by hand, and that is the point."""
        return self.async_abort(reason="add_profile_via_calibration")

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Show the stored numbers, and how to change them."""
        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_abort(reason="profile_unchanged")
        data = subentry.data
        lines = [
            f"{key}: {value}"
            for key, value in data.items()
            if key not in (CONF_RAW, CONF_NAME) and not isinstance(value, dict)
        ]
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({}),
            description_placeholders={
                "profile": str(data.get(CONF_NAME) or subentry.title),
                "values": "```yaml\n" + "\n".join(lines) + "\n```",
            },
        )


@callback
def async_get_subentry_types() -> dict[str, type[ConfigSubentryFlow]]:
    """The two subentry types of a MyHOME gateway (`config_flow` hands this to HA)."""
    return {
        SUBENTRY_COVER_CALIBRATION: CoverCalibrationFlow,
        SUBENTRY_COVER_PROFILE: CoverProfileFlow,
    }


__all__ = [
    "PRESS_TIMEOUT_SEC",
    "PROBLEM_REASONS",
    "REFINE_THRESHOLD_CM",
    "RUNNING_ACTION",
    "CoverCalibrationFlow",
    "CoverProfileFlow",
    "async_get_subentry_types",
    "overrides_yaml",
    "profile_reference_yaml",
]
