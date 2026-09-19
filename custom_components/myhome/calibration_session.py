"""The guided calibration as a session the panel drives (0.6.0 wizard, lot B2).

The same measurement as the *Configura* dialog, with the conversation turned inside
out. A dialog is pulled: Home Assistant asks the flow for a screen, the flow answers
one, and nothing can reach the user between two questions. The panel is pushed: the
session lives on the server, publishes a whole snapshot at every transition, and the
browser is one of possibly several windows watching it. That difference is the only
reason this module exists at all - the arithmetic is `calibration_measure.py`, ported
from the dialog and kept equal to it by a parity test, and the shutter is driven
through the four `async_calib_*` primitives of `cover.py`, which do not change.

What the session therefore owns, and what the dialog owned in passing:

* **One session per gateway**, in `hass.data`, with an identity (`session_id`), a
  revision that grows at every transition and an owner (`client_id`) that can lapse,
  be picked up and be taken over. A browser tab is not the session: locking a phone in
  the middle of a tape reading must not lose the reading (lesson 1 of the panel v2).
* **The clock.** A press counts when its message reaches the backend, exactly as the
  dialog counts it when the HTTP request arrives; no instant from a browser enters a
  measurement. Unlike the dialog, the backend can push a screen, so the press timeout
  fires on its own rather than being noticed when the press finally arrives.
* **The lease**: the dialog's inactivity watchdog (1800 s, 600 s after a movement),
  rearmed by every transition and every verb of the owner - and deliberately *not* by
  a heartbeat, or a forgotten tab would hold a shutter in calibration for ever.
* **What the shutter does when nobody asked it to.** The dialog could not see a wall
  switch; the session watches its cover's state and answers the four cases of
  SPEC §3.7 - which includes doing nothing at all, because lowering the shutter while
  reading the instructions is an ordinary gesture and not a failure.

And the rule that governs the whole file: **a read never moves anything**. `snapshot`,
`attach` and `current` answer and stop there; every movement starts from an `act` or
from the end of the movement before it in the same chain. A session picked up again
shows where it stands and does not re-enter its step, which is the one thing the
dialog does differently (it re-enters a step for every frame of a progress bar).

Nothing is written before `save`, and `save` goes through `panel_write.async_write`
like every other write of the panel - one write at a time, the covers pick the numbers
up in place, every subscriber gets the new overview - with the two differences the
session needs: it is not refused by the calibration it is itself holding, and it
leaves no undo token.

Lot B2 built the core and path A at the basic level; lot B4 added the other two
paths, the thorough calibration and the two verifications, so the conversation now
covers the whole of SPEC §3.4. `IMPLEMENTED_PATHS` / `IMPLEMENTED_LEVELS` remain the
knob for a backend that walks less than all of it: an action they leave out is never
put in `actions` and is refused by the ordinary rule (`action_not_offered`).
"""

from __future__ import annotations

import contextlib
import math
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.websocket_api import (
    ERR_NOT_ALLOWED,
    ERR_NOT_FOUND,
    ERR_NOT_SUPPORTED,
    ERR_SERVICE_VALIDATION_ERROR,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME, STATE_CLOSING, STATE_OPENING, STATE_UNAVAILABLE
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from . import calibration_measure as measure
from .calibration import (
    CalibrationError,
    DirectionFit,
    RunReport,
    predict_cm,
    slat_time_from_press,
    timing_from_presses,
    timing_with_slat,
)
from .calibration_flow import (
    ERROR_ABOVE_THE_TRAVEL,
    ERROR_INVALID_NAME,
    ERROR_NOT_A_NUMBER,
    ERROR_OUT_OF_RANGE,
    EXPECTED_TOLERANCE_CM,
    FALLBACK_HEIGHT_CM,
    HALF_RUN,
    HOMING_ACTION,
    IDLE_TIMEOUT_SEC,
    LATE_STOP_SEC,
    LIFT_CHECK_OPTIONS,
    MAX_GAP_CM,
    MAX_HEIGHT_CM,
    MIN_HEIGHT_CM,
    MOVED_IDLE_TIMEOUT_SEC,
    NO_PROFILE,
    PATH_FIRST,
    PATH_PROFILE,
    PATH_REFINE,
    PLAN_FULL,
    PLAN_PRECISE,
    PLAN_PRECISE_TRAVEL,
    PLAN_PROFILE,
    PLAN_TIMES,
    PLAN_TIMES_AND_ROLLS,
    PLAN_VERIFY_B,
    PRESS_TIMEOUT_SEC,
    PROBLEM_REASONS,
    QUARTER_RUN,
    REASON_TIMEOUT,
    REASON_UNKNOWN,
    REASON_UNKNOWN_COVER,
    REFINE_THRESHOLD_CM,
    ROUGH_TOLERANCE_CM,
    RUNNING_ACTION,
    THREE_QUARTER_RUN,
    TOUCHING_CM,
    VERIFY_RUN,
    VERIFY_RUN_PROFILE,
    order_the_readings,
    parse_number,
)
from .calibration_store import (
    PROFILE_NAME_PATTERN,
    CalibrationStore,
    StoredCalibration,
    cover_calibration_data,
    cover_profile_data,
    loaded_store,
    merged_profiles,
    profile_as_config,
    resolve_cover,
)
from .const import (
    CALIBRATION_SOURCE_GUIDED,
    CALIBRATION_SOURCE_PROFILE,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_ENTITIES,
    CONF_HEIGHT,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PLATFORMS,
    CONF_PROFILE,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
    CONF_YAML_KEY,
    DIRECTION_CLOSE,
    DIRECTION_OPEN,
    DOMAIN,
    LOGGER,
)
from .cover import CALIBRATION_SETTLE_SEC, calibration_run_seconds
from .panel_data import (
    CALIBRATION_LEVEL_PRECISE,
    async_overview,
    basic_covers,
    calibrating_now,
    is_advanced_cover,
    level_and_note,
    yaml_profiles,
)
from .panel_schemas import (
    ERROR_ACTION_NOT_OFFERED,
    ERROR_ADVANCED_COVER,
    ERROR_ALREADY_CALIBRATING,
    ERROR_COVER_UNAVAILABLE,
    ERROR_NOT_IN_REVIEW,
    ERROR_REVISION_CONFLICT,
    ERROR_SESSION_ENDED,
    ERROR_SESSION_OWNED,
    ERROR_UNKNOWN_COVER,
    ERROR_UNKNOWN_PROFILE,
    SESSION_BOUNDARY_NAMES,
    SESSION_REVIEW_ROW_KEYS,
    SESSION_SUBMIT,
    SESSION_VALUE_KEYS,
)
from .panel_write import PanelError, async_publish, async_write

# Where the sessions live: one slot per config entry, holding the live session or the
# terminal snapshot of the last one. In `hass.data` and not in a module global for the
# same reason as `panel_write.WRITING_DATA_KEY`: one test process runs several Home
# Assistants, and a session that outlived one of them would refuse a start nobody
# could see the cause of.
SESSIONS_DATA_KEY = f"{DOMAIN}_calibration_sessions"

# How long a finished session stays readable. A client that comes back - a page
# reloaded after "Salva", a phone unlocked after the watchdog fired - must read *how*
# it ended rather than "no such session"; ten minutes is long enough for that and
# short enough that the answer is still about something the user remembers doing.
TERMINAL_TTL = timedelta(minutes=10)

# How long the owner stays present after its last heartbeat or verb. The panel beats
# every 15 s, so three missed beats. It decides who may act and nothing else: when it
# lapses nothing stops, nothing is cancelled and nothing moves (SPEC §3.6, lesson 1).
PRESENCE_SEC = 45.0

# The reason of a step the dialog has no name for: something outside the session moved
# the shutter, or the user pressed "Ferma la tapparella", in the middle of a
# measurement. The measurement is void, nothing was written, and the step can be made
# again - which is what its screen says.
REASON_INTERRUPTED = "interrupted"

# What this backend can carry out, which is now the whole of SPEC §3.4. They are kept
# as tuples rather than folded away because they are the knob a backend that walks less
# than all of it turns: what is not in them is not put in `actions` and is refused
# before a shutter is taken hold of, rather than advertised and then failed on.
#
# They are **not** what `capabilities` answers. `panel_schemas.SESSION_CAPABILITIES` is
# a constant of the frozen contract and lists the frozen tuples; the two agree today
# because these two are complete, and making the published capabilities derive from
# these is a change to a frozen artefact and therefore not this module's to make
# (handoff §8, RISCHIO-1).
IMPLEMENTED_PATHS: tuple[str, ...] = (PATH_FIRST, PATH_PROFILE, PATH_REFINE)
IMPLEMENTED_LEVELS: tuple[str, ...] = ("basic", "thorough")

_NAME_RE = re.compile(PROFILE_NAME_PATTERN)


# ---------------------------------------------------------------------- the step table
@dataclass(frozen=True, slots=True)
class _Screen:
    """One step of the conversation, as the snapshot describes it.

    `state` and `substate` are the published contract's tokens; `actions` are the
    dialog's own `menu_options` ids in the dialog's order, minus its two ways out
    (`save` is the `save` command and `cancel_flow` is the `cancel` verb, so neither
    is ever an action here); `form` names the field the step asks for, if any.
    `after_a_movement` is which of the two patiences the lease uses on this screen -
    the dialog decides the same thing by setting `_idle_timeout` before each
    `async_show_*`.
    """

    state: str
    substate: str | None = None
    actions: tuple[str, ...] = ()
    form: str | None = None
    after_a_movement: bool = False


# Every screen of the guided conversation, derived line by line from
# `calibration_flow.GuidedCalibrationMixin` (SPEC §3.4). The problem screens are added
# below, because they are one shape repeated.
SCREENS: dict[str, _Screen] = {
    # choosing a path
    "path": _Screen("armed", actions=(PATH_FIRST, PATH_PROFILE, PATH_REFINE)),
    "path_a": _Screen("armed", actions=("begin",)),
    "path_b": _Screen("armed", form=CONF_PROFILE),
    "path_c": _Screen("armed", form=CONF_PROFILE),
    "refine_scope": _Screen("armed", actions=("times_only", "times_and_rolls", "points_only")),
    # the first homing
    "home_closed": _Screen("positioning", after_a_movement=True),
    "home_closed_done": _Screen(
        "briefing", actions=("confirm_closed", "repeat_step", "not_right"), after_a_movement=True
    ),
    # the ascent: two runs, two presses
    "open_timed": _Screen("positioning", after_a_movement=True),
    "open_brief": _Screen("briefing", actions=("open_start", "repeat_step")),
    "open_start": _Screen("running", after_a_movement=True),
    "open_lift": _Screen(
        "running",
        substate="awaiting_endpoint",
        actions=("lifted_off", "repeat_step", "not_right"),
        after_a_movement=True,
    ),
    "lift_stop": _Screen("running", substate="awaiting_stop", after_a_movement=True),
    "lift_check": _Screen("briefing", actions=tuple(LIFT_CHECK_OPTIONS), after_a_movement=True),
    "lift_check_late": _Screen(
        "briefing", actions=tuple(LIFT_CHECK_OPTIONS), after_a_movement=True
    ),
    "lift_gap": _Screen("awaiting_reading", form="gap_cm", after_a_movement=True),
    "lift_early": _Screen(
        "briefing", actions=("repeat_step", "lift_gap", "not_right"), after_a_movement=True
    ),
    "open_home_again": _Screen("positioning", after_a_movement=True),
    "closed_again": _Screen(
        "briefing",
        actions=("confirm_closed_again", "repeat_step", "not_right"),
        after_a_movement=True,
    ),
    "open_full_brief": _Screen("briefing", actions=("open_full_start", "repeat_step")),
    "open_full_start": _Screen("running", after_a_movement=True),
    "open_top": _Screen(
        "running",
        substate="awaiting_endpoint",
        actions=("stopped_open", "repeat_step", "not_right"),
        after_a_movement=True,
    ),
    "open_result": _Screen("briefing", actions=("accept_step", "repeat_step"), after_a_movement=True),
    "open_result_gap": _Screen(
        "briefing", actions=("accept_step", "repeat_step"), after_a_movement=True
    ),
    # the curtain travel
    "height_read": _Screen("positioning", after_a_movement=True),
    "height": _Screen("awaiting_reading", form=CONF_HEIGHT),
    "height_result": _Screen(
        "briefing", actions=("accept_step", "repeat_measure", "not_right"), after_a_movement=True
    ),
    # the descent
    "close_timed": _Screen("positioning", after_a_movement=True),
    "close_brief": _Screen("briefing", actions=("close_start", "repeat_step")),
    "close_start": _Screen("running", after_a_movement=True),
    "close_bottom": _Screen(
        "running",
        substate="awaiting_endpoint",
        actions=("stopped_closed", "repeat_step", "not_right"),
        after_a_movement=True,
    ),
    "close_result": _Screen(
        "briefing", actions=("accept_step", "repeat_step"), after_a_movement=True
    ),
    # the tape phase
    "tape_brief": _Screen("briefing", actions=("tape_start",)),
    "half_down": _Screen("positioning", after_a_movement=True),
    "half_up": _Screen("positioning", after_a_movement=True),
    "quarter_down": _Screen("positioning", after_a_movement=True),
    "three_quarter_down": _Screen("positioning", after_a_movement=True),
    "quarter_up": _Screen("positioning", after_a_movement=True),
    "three_quarter_up": _Screen("positioning", after_a_movement=True),
    "verify": _Screen("positioning", after_a_movement=True),
    "verify_b": _Screen("positioning", after_a_movement=True),
    "tape_run": _Screen("positioning", after_a_movement=True),
    "measure_descent": _Screen("awaiting_reading", form="measured_cm", after_a_movement=True),
    "measure_ascent": _Screen("awaiting_reading", form="measured_cm", after_a_movement=True),
    "tape_result": _Screen(
        "briefing", actions=("accept_step", "repeat_tape", "tape_not_right"), after_a_movement=True
    ),
    "measure_verify": _Screen("awaiting_reading", form="measured_cm", after_a_movement=True),
    "verify_result": _Screen("checking", actions=("accept_step", "repeat_tape"), after_a_movement=True),
    "verify_offer": _Screen("briefing", actions=("verify_now", "skip_verify")),
    # the end
    "profile_name": _Screen("briefing", form=CONF_NAME),
    "summary_basic": _Screen("review", actions=("refine",)),
    "summary_short": _Screen("review"),
    "summary_correction": _Screen("review", actions=("refine",)),
    "summary_precise": _Screen("review"),
}
for _reason in (*PROBLEM_REASONS, REASON_INTERRUPTED):
    SCREENS[f"problem_{_reason}"] = _Screen("briefing", actions=("repeat_step",))

# The stage every reading of the tape phase, and every timed run, belongs to - so that
# `repeat_step` on a brief repeats the whole stage and a movement started outside a
# stage knows which homing brings the shutter back (SPEC §3.7).
#
# A brief that precedes a timed run, the end stop that run has to start from, and the
# homing step of the stage that would bring the shutter there.
TIMED_RUN_BRIEFS: dict[str, tuple[str, str, str]] = {
    # brief step: (direction of the run, end stop it starts from, the stage's homing step)
    "open_brief": (DIRECTION_OPEN, DIRECTION_CLOSE, "open_timed"),
    "open_full_brief": (DIRECTION_OPEN, DIRECTION_CLOSE, "open_home_again"),
    "close_brief": (DIRECTION_CLOSE, DIRECTION_OPEN, "close_timed"),
}

# The three screens that wait for a press, and what the press is about. The run they
# belong to is **still going** while they are on the screen - it is the whole point:
# the user is watching a shutter travel and will press when something happens - so the
# movement is not cleared when the primitive that started it comes back.
PRESS_STEPS: dict[str, str] = {
    "open_lift": "lift_off",
    "open_top": "end_stop",
    "close_bottom": "end_stop",
}

# The readings of the tape phase, as (direction, fraction, the step that asks for the
# tape). `half_down` and `half_up` are path A's; the other four are the thorough
# calibration's and the two verifications ask a model rather than feed one.
FRACTION_STAGES: dict[str, tuple[str, float, str]] = {
    "half_down": (DIRECTION_CLOSE, HALF_RUN, "measure_descent"),
    "half_up": (DIRECTION_OPEN, HALF_RUN, "measure_ascent"),
    "quarter_down": (DIRECTION_CLOSE, QUARTER_RUN, "measure_descent"),
    "three_quarter_down": (DIRECTION_CLOSE, THREE_QUARTER_RUN, "measure_descent"),
    "quarter_up": (DIRECTION_OPEN, QUARTER_RUN, "measure_ascent"),
    "three_quarter_up": (DIRECTION_OPEN, THREE_QUARTER_RUN, "measure_ascent"),
    "verify": (DIRECTION_CLOSE, VERIFY_RUN, "measure_verify"),
    "verify_b": (DIRECTION_CLOSE, VERIFY_RUN_PROFILE, "measure_verify"),
}

# The plans, by the path (and scope) that installs them. Imported from the dialog and
# never rewritten: a stage added there is a stage here.
PLANS: dict[str, tuple[str, ...]] = {
    PATH_FIRST: PLAN_FULL,
    PATH_PROFILE: PLAN_PROFILE,
    "times_only": PLAN_TIMES,
    "times_and_rolls": PLAN_TIMES_AND_ROLLS,
}
# The thorough calibration is not in that table because it is not chosen by a name: it
# is `PLAN_PRECISE`, or the same with the curtain travel in front of it for a window
# nobody has ever measured one for, and which of the two it is depends on what the
# conversation knows by then (`_thorough_plan`). `PLAN_VERIFY_B` is path B's optional
# check, grafted onto the plan at the screen that offers it.


def _other_end(direction: str) -> str:
    """The end stop a run of `direction` has to start from."""
    return DIRECTION_OPEN if direction == DIRECTION_CLOSE else DIRECTION_CLOSE


def _as_position(direction: str | None) -> str | None:
    """An end stop as the contract names it: a *position*, not a direction.

    Inside the session an end stop is the direction that reaches it, because that is
    what the primitives are given and what `order_the_readings` deals on. At the
    boundary the contract asks for `SESSION_POSITIONS` - `closed` / `open` - so the two
    words that differ are translated here, with the other boundary names
    (`SESSION_BOUNDARY_NAMES`). `open` happens to coincide; `close` / `closed` does not,
    which is exactly why this is a function and not a habit.
    """
    if direction is None:
        return None
    return "closed" if direction == DIRECTION_CLOSE else "open"


def _finite(value: Any) -> float | None:
    """A number the maths can be handed, or None.

    The second net behind the schema of lot B3 (B1 handoff, R1): `parse_number` is
    `float()` underneath, so "nan" and "inf" parse, and a reading of `nan` makes every
    fit raise three screens later. Refused here, in the words the dialog refuses a
    non-number in, because that is what it is.
    """
    number = parse_number(value)
    if number is None or not math.isfinite(number):
        return None
    return number


def _at_second(value: datetime | None) -> str | None:
    """One instant as the snapshot carries it, or None."""
    return None if value is None else value.isoformat()


# ------------------------------------------------------------------- what is moving
@dataclass(slots=True)
class _Movement:
    """What the session is making the shutter do, for the progress screens.

    `started_at` is the motion anchor and is `null` until it is known: a free run
    learns it from `async_calib_start` (the actuator's echo), a homing and a run to a
    fraction are anchored when the frame goes out, because neither is measured.
    """

    kind: str
    direction: str
    progress_action: str
    started_at: datetime | None = None
    planned_s: float | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "direction": self.direction,
            "progress_action": self.progress_action,
            "started_at": _at_second(self.started_at),
            "planned_s": self.planned_s,
        }


@dataclass(slots=True)
class _Press:
    """The press a measuring screen is waiting for, and when it stops being worth it."""

    kind: str
    expires_at: datetime

    def as_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "expires_at": _at_second(self.expires_at)}


# --------------------------------------------------------------------- the refusals
def _refuse(
    code: str, key: str, message: str, placeholders: Mapping[str, Any] | None = None
) -> PanelError:
    """One refusal, in the shape `connection.send_error` wants."""
    return PanelError(code, key, message, placeholders)


# --------------------------------------------------------------------- the registry
@callback
def _registry(hass: HomeAssistant) -> dict[str, CalibrationSession]:
    return hass.data.setdefault(SESSIONS_DATA_KEY, {})


@callback
def current(hass: HomeAssistant, entry: ConfigEntry) -> CalibrationSession | None:
    """This gateway's session - live, or terminal while it is still worth reading.

    A read and nothing else: it never moves a shutter, never starts a timer and never
    resurrects a session whose ten minutes are up (it forgets that one instead).
    """
    registry = _registry(hass)
    session = registry.get(entry.entry_id)
    if session is None:
        return None
    if session.forgettable:
        registry.pop(entry.entry_id, None)
        return None
    return session


@callback
def _live_entity(hass: HomeAssistant, entry: ConfigEntry, unique_id: str) -> Any:
    """The cover entity behind one unique id, looked up again right now.

    Never an object held from before. A config entry reloaded under a session - the
    "Ricarica" button, a re-auth, a dialog closing after a save - tears every cover
    entity down and builds new ones, and the old object would drive frames into a
    closed gateway and leave the live shutter unmarked (0.5.0 BUG-4, and
    `calibration_flow._live_cover`, which is this function).
    """
    mac = str(entry.data.get(CONF_MAC) or "")
    gateway = (hass.data.get(DOMAIN) or {}).get(mac) or {}
    covers = (gateway.get(CONF_PLATFORMS) or {}).get(COVER) or {}
    for key, cfg in covers.items():
        if f"{mac}-{key}" == unique_id:
            return (cfg.get(CONF_ENTITIES) or {}).get(COVER)
    return None


async def async_start(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    cover_unique_id: str,
    client_id: str,
    path: str | None = None,
    profile: str | None = None,
    scope: str | None = None,
) -> CalibrationSession:
    """Open the gateway's session on one basic cover. It never moves anything.

    Every refusal that can be known before a shutter is asked to do something is made
    here, which is the dialog's own rule (`_claim`): the one moment at which the user
    has not yet been asked to stand in front of a window.
    """
    registry = _registry(hass)
    running = current(hass, entry)
    if running is not None and not running.ended:
        raise _refuse(
            ERR_NOT_ALLOWED,
            ERROR_ALREADY_CALIBRATING,
            f"A calibration session is already running on {running.cover_name}",
            {"cover": running.cover_name, "by": "panel"},
        )
    if running is not None and running.reserved:
        raise _refuse(
            ERR_NOT_ALLOWED,
            ERROR_ALREADY_CALIBRATING,
            f"{running.cover_name} is still finishing the run a cancelled session left it on",
            {"cover": running.cover_name, "by": "reserved"},
        )
    if path is not None and path not in IMPLEMENTED_PATHS:
        # What this backend cannot carry out is not offered and not opened: a session
        # born on a screen every one of whose buttons is refused would hold the shutter
        # and do nothing, the only way out being `cancel`.
        raise _refuse(
            ERR_NOT_ALLOWED,
            ERROR_ACTION_NOT_OFFERED,
            f"{path!r} is not a path this backend can walk yet",
            {"action": path},
        )
    covers = basic_covers(hass, entry)
    measuring = calibrating_now(hass, entry)
    if measuring:
        held = sorted(measuring)[0]
        name = str(covers.get(held, {}).get(CONF_NAME) or held)
        raise _refuse(
            ERR_NOT_ALLOWED,
            ERROR_ALREADY_CALIBRATING,
            f"{name} is already being calibrated by something that is not this panel",
            {"cover": name, "by": "other"},
        )
    device = covers.get(cover_unique_id)
    if device is None:
        if is_advanced_cover(hass, entry, cover_unique_id):
            raise _refuse(
                ERR_NOT_SUPPORTED,
                ERROR_ADVANCED_COVER,
                f"{cover_unique_id} is an advanced shutter and has no travel model",
                {"cover": cover_unique_id},
            )
        raise _refuse(
            ERR_NOT_FOUND,
            ERROR_UNKNOWN_COVER,
            f"No cover with the unique id {cover_unique_id} on {entry.title}",
            {"cover": cover_unique_id},
        )
    name = str(device.get(CONF_NAME) or cover_unique_id)
    entity = _live_entity(hass, entry, cover_unique_id)
    state = None if entity is None else hass.states.get(getattr(entity, "entity_id", "") or "")
    if entity is None or (state is not None and state.state == STATE_UNAVAILABLE):
        raise _refuse(
            ERR_NOT_FOUND,
            ERROR_COVER_UNAVAILABLE,
            f"{name} has no entity, or its entity is unavailable",
            {"cover": name},
        )
    session = CalibrationSession(hass, entry, cover_unique_id=cover_unique_id, client_id=client_id)
    if profile is not None and profile not in session.profiles:
        raise _refuse(
            ERR_NOT_FOUND,
            ERROR_UNKNOWN_PROFILE,
            f"No profile called {profile!r} on {entry.title}",
            {"profile": profile},
        )
    registry[entry.entry_id] = session
    try:
        session.begin(path=path, profile=profile, scope=scope)
    except Exception:
        # Nothing has been published and nothing was taken hold of: a session that
        # could not open must not be left in the registry refusing the next start.
        registry.pop(entry.entry_id, None)
        raise
    return session


# The entries whose unload is already being watched. `ConfigEntry.async_on_unload`
# hands back no way to unregister, so a callback registered per *session* would pile up
# one per calibration for the life of the entry (all of them inert after the first).
# One per entry instead, registered by the first session and taken off this set by the
# unload that runs it - which is also what drains the entry's own list.
WATCHED_DATA_KEY = f"{DOMAIN}_calibration_sessions_watched"


@callback
def _watch_for_unload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """End whatever session this gateway has if the entry is unloaded under it.

    `async_unload_entry` already calls `async_end_all` as its first instruction, which
    is the ordinary way round and the one that can still write a stop. This is for
    every other way an entry goes away; by the time it runs the session is usually
    already ended, and its first question is whether there is one left to end.
    """
    watched: set[str] = hass.data.setdefault(WATCHED_DATA_KEY, set())
    if entry.entry_id in watched:
        return
    watched.add(entry.entry_id)

    @callback
    def unloaded() -> None:
        hass.data.setdefault(WATCHED_DATA_KEY, set()).discard(entry.entry_id)
        session = current(hass, entry)
        if session is None or session.ended:
            return
        LOGGER.info(
            "Panel calibration of %s: the gateway was reloaded, so the session was "
            "ended. Nothing was saved; start again to measure it",
            session.cover_name,
        )
        # `async_on_unload` callbacks are synchronous, and a session that ends with the
        # shutter moving must have *tried* to stop it (0.5.0 final review, RISK-C).
        hass.async_create_task(
            session.async_end("unloaded", stop=True),
            "myhome calibration session unloaded",
            eager_start=False,
        )

    entry.async_on_unload(unloaded)


async def async_end_all(hass: HomeAssistant, entry: ConfigEntry, reason: str) -> None:
    """Close this gateway's session, stopping the shutter if it is running.

    Called by `async_unload_entry` *before* the platforms are unloaded, while the
    entities still exist and a stop can still be written; and by the `async_on_unload`
    callback the session registers, for every other way an entry goes away.
    """
    session = current(hass, entry)
    if session is None or session.ended:
        return
    await session.async_end(reason, stop=True)


# ------------------------------------------------------------------------ the session
class CalibrationSession:
    """One guided calibration of one shutter, as a thing on the server.

    Built by `async_start` and never by hand: a session that is not in the registry
    has nowhere to be found again, which is the whole point of it not living in a
    browser.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        cover_unique_id: str,
        client_id: str,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.session_id = uuid4().hex
        self.cover_unique_id = cover_unique_id
        self.revision = 0

        device = basic_covers(hass, entry).get(cover_unique_id) or {}
        self.cover_name = str(device.get(CONF_NAME) or cover_unique_id)
        self._yaml_key = str(device.get(CONF_YAML_KEY) or "")
        entity = _live_entity(hass, entry, cover_unique_id)
        self.entity_id = str(getattr(entity, "entity_id", "") or "")

        # the conversation
        self._path: str | None = None
        self._plan: list[str] = []
        self._index: int | None = None
        self._measured = measure.Measured()
        self._profile: str | None = None
        self._scope: str | None = None
        self._intent: dict[str, Any] | None = None
        self._measured_name: str | None = None
        self._step: str = "path"
        self._problem: str | None = None
        self._notice: str | None = None
        self._form_error: str | None = None
        self._stop_first = False
        self._at: str | None = None
        self._external_move = False
        self._tape_target: str | None = None
        self._pending: tuple[str, float] | None = None
        self._after_the_run = "measure_descent"
        self._report: RunReport | None = None
        self._motor_start: datetime | None = None
        self._lift_off: datetime | None = None
        self._stop_delivered: datetime | None = None
        self._motor_stopped: datetime | None = None
        self._shown_at: datetime | None = None
        self._error: str | None = None
        self._result: measure.Result | None = None
        self._review: dict[str, Any] | None = None
        self._check: dict[str, Any] | None = None

        # what is moving, and what the screen is waiting for
        self._movement: _Movement | None = None
        self._press: _Press | None = None
        self._queued: Callable[[], Awaitable[None]] | None = None
        self._pumping = False
        # Bumped by anything that makes the movement under way pointless (a stop, an
        # external movement, a cancellation): the job that finishes afterwards sees
        # that the session has moved on and publishes nothing.
        self._generation = 0

        # the owner, and the two clocks
        self._owner: str | None = client_id
        self._owner_seen: datetime = dt_util.utcnow()
        self._lease: Callable[[], None] | None = None
        self._lease_at: datetime | None = None
        self._press_timer: Callable[[], None] | None = None

        # the ending
        self.ended = False
        self._outcome: dict[str, Any] | None = None
        self._ended_at: datetime | None = None
        self._reserved_until: datetime | None = None

        self._subscribers: list[Callable[[dict[str, Any]], None]] = []
        self._claim: contextlib.ExitStack | None = None
        self._watching: Callable[[], None] | None = None

    # ------------------------------------------------------------------ the gateway
    @property
    def profiles(self) -> dict[str, Mapping[str, Any]]:
        """Both namespaces at once, exactly as a cover resolves them."""
        return merged_profiles(yaml_profiles(self.hass, self.entry), self._store_profiles())

    def _store(self) -> CalibrationStore | None:
        """The store this gateway is running on *now*, or None during a reload.

        Never an object held from before, for the reason `CalibrationContextMixin._store`
        gives: every setup builds a new store from disk, and a write through the old one
        serialises a snapshot from before the reload over everything written since.
        """
        return loaded_store(self.hass, self.entry)

    def _store_profiles(self) -> Mapping[str, Mapping[str, Any]]:
        store = self._store()
        return {} if store is None else store.profiles

    def _record(self) -> StoredCalibration | None:
        store = self._store()
        return None if store is None else store.calibration(self.cover_unique_id)

    def _device(self) -> dict[str, Any]:
        """This cover as `myhome.yaml` wrote it.

        The file's own copy and never the validated dict the entity reads: the cover
        platform merges the resolved travel model back into that one, so resolving
        against it would let the record win twice and would leave nobody able to answer
        "what does the file say" (B1 handoff, R3; `panel_data._covers_as_written`).
        """
        return basic_covers(self.hass, self.entry).get(self.cover_unique_id) or {}

    def _resolved(
        self,
        record: StoredCalibration | None = None,
        profiles: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> Any:
        """This cover's travel model, through the one function the cover itself uses."""
        return resolve_cover(
            self._device(),
            profiles=dict(self.profiles) if profiles is None else dict(profiles),
            calibration=self._record() if record is None else record,
        )

    def _model_now(self) -> dict[str, float]:
        """The run times the shutter moves on today, for the progress bars.

        Only ever read to say how long a movement should take: no measurement is
        computed from it (the run times a measurement uses are the presses').
        """
        values = self._resolved().values
        return {
            key: float(values.get(key) or 0.0)
            for key in (CONF_OPENING_TIME, CONF_CLOSING_TIME, CONF_SLAT_TIME)
        }

    def _full_run(self, direction: str) -> float:
        model = self._model_now()
        return model[CONF_OPENING_TIME if direction == DIRECTION_OPEN else CONF_CLOSING_TIME]

    def _cover(self) -> Any:
        """The live entity, looked up again, or the refusal that has a screen of its own."""
        entity = _live_entity(self.hass, self.entry, self.cover_unique_id)
        if entity is None:
            raise CalibrationError(
                REASON_UNKNOWN_COVER,
                f"{self.cover_name} is not configured on this gateway any more",
            )
        return entity

    # ------------------------------------------------------------------ starting up
    @callback
    def begin(self, *, path: str | None, profile: str | None, scope: str | None) -> None:
        """Take hold of the shutter and publish the first screen. Nothing moves.

        `start` never skips a screen that comes before a movement: with `path_a` the
        session is born on the warning, not on the first homing.
        """
        entity = self._cover()
        self._claim = contextlib.ExitStack()
        self._claim.enter_context(entity.calibration_session())
        _watch_for_unload(self.hass, self.entry)
        self._watch_the_cover()
        if scope is not None:
            self._intent = {"scope": scope}
        if path == PATH_PROFILE:
            self._path = PATH_PROFILE
            self._profile = profile
            self._step = "path_b"
        elif path == PATH_REFINE:
            self._path = PATH_REFINE
            self._profile = profile
            if profile is None:
                self._step = "path_c"
            else:
                # Named up front, the profile is *chosen*, and the screen after the
                # choice is `refine_scope` - so the conversation has to start from
                # where choosing it leaves it, travel and all, and not merely display
                # a later screen (`async_step_path_c`, :1811-1828).
                self._correct_this_profile(profile)
                self._step = "refine_scope"
        elif path == PATH_FIRST:
            self._path = PATH_FIRST
            self._step = "path_a"
        else:
            self._step = "path"
        self._publish()
        self._publish_the_overview()

    @callback
    def _publish_the_overview(self) -> dict[str, Any]:
        """Push a fresh overview to every open panel of this gateway, and answer with it.

        A session is not a write: it takes hold of a shutter and gives it back without
        touching the store, so nothing in `panel_write` publishes an overview for it.
        But `overview.session` **is** part of the overview, and a panel that was already
        subscribed when this session began would otherwise read `null` there for the
        whole of it - which the document says means "the guided dialog or the 0.4.2
        action", so the second screen in the house would offer to close a dialog that
        does not exist rather than to join the calibration that does.

        Called at the two moments the answer changes: when the session appears
        (`begin`) and when it goes (`_finish`, whatever ended it). `measuring` moves
        with it, and the two are built from the same read, so no panel ever sees one
        without the other.
        """
        overview = async_overview(self.hass, self.entry)
        async_publish(self.hass, self.entry, overview)
        return overview

    @callback
    def _watch_the_cover(self) -> None:
        """Watch the shutter's state, for the movements the session did not ask for."""
        if not self.entity_id:
            return
        self._watching = async_track_state_change_event(
            self.hass, [self.entity_id], self._state_changed
        )

    # ------------------------------------------------------------------ subscriptions
    @callback
    def subscribe(self, send: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        """Follow this session's transitions; the answer unsubscribes."""
        self._subscribers.append(send)

        @callback
        def drop() -> None:
            with contextlib.suppress(ValueError):
                self._subscribers.remove(send)

        return drop

    # ----------------------------------------------------------------- the ownership
    @property
    def owner(self) -> str | None:
        return self._owner

    @property
    def present(self) -> bool:
        """True while the owner's last heartbeat or verb is less than 45 s old."""
        if self._owner is None:
            return False
        return (dt_util.utcnow() - self._owner_seen).total_seconds() < PRESENCE_SEC

    @property
    def present_until(self) -> datetime | None:
        return None if self._owner is None else self._owner_seen + timedelta(seconds=PRESENCE_SEC)

    @property
    def forgettable(self) -> bool:
        """True for a session that ended long enough ago to stop being an answer."""
        if not self.ended or self._ended_at is None:
            return False
        if self.reserved:
            return False
        return dt_util.utcnow() - self._ended_at > TERMINAL_TTL

    @property
    def reserved(self) -> bool:
        """True while the gateway is still held by a run this session left going.

        The shutter itself was given back the moment the session ended - its other
        commands work again - but a *new* session cannot start a measurement into a
        curtain that is still travelling (contract §2.1). It lasts until the cover
        stops moving or until a full run plus the settle margin has gone by, whichever
        comes first.
        """
        if self._reserved_until is None or dt_util.utcnow() >= self._reserved_until:
            return False
        entity = _live_entity(self.hass, self.entry, self.cover_unique_id)
        return bool(entity is not None and (entity.is_opening or entity.is_closing))

    @callback
    def _check_owner(self, client_id: str, *, force: bool = False) -> None:
        """Refuse a client that may not act, without changing anything at all.

        Split from `_take` so that the guards can be asked in the right order: the
        session is live, the client may act, the revision is the current one, the step
        offers the action - and only *then* the session changes hands. Taking it and
        then refusing the verb would mean a tab replaying an `act` after a reconnection
        carries the session off a phone that is using it, on a message the revision
        exists to throw away (SPEC §4.1: "niente eseguito").
        """
        if self._owner is not None and self._owner != client_id and self.present and not force:
            raise _refuse(
                ERR_NOT_ALLOWED,
                ERROR_SESSION_OWNED,
                "Another device is guiding this calibration",
            )

    @callback
    def _take(self, client_id: str, *, force: bool = False, publish: bool = False) -> None:
        """Make this client the owner, or refuse because somebody else is here.

        A verb that *does* something takes the session when its owner has gone quiet;
        a heartbeat never does (SPEC §4.2, amended 19 Sep), because a second tab left
        open would otherwise take a session away from a phone that went to sleep in the
        middle of a tape reading.
        """
        self._check_owner(client_id, force=force)
        changed = self._owner != client_id
        self._owner = client_id
        self._owner_seen = dt_util.utcnow()
        if changed and publish:
            self._publish()

    @callback
    def _guard_live(self) -> None:
        if self.ended:
            reason = str((self._outcome or {}).get("reason") or "")
            raise _refuse(
                ERR_NOT_ALLOWED,
                ERROR_SESSION_ENDED,
                f"This calibration has ended ({reason})",
                {"reason": reason},
            )

    @callback
    def _guard_revision(self, revision: int) -> None:
        if revision != self.revision:
            raise _refuse(
                ERR_NOT_ALLOWED,
                ERROR_REVISION_CONFLICT,
                f"This calibration has moved on (revision {self.revision}, not {revision})",
            )

    # ---------------------------------------------------------------------- the verbs
    @callback
    def attach(self, client_id: str, claim: bool = False) -> dict[str, Any]:
        """Read the session as this client, becoming its owner where that is allowed.

        A read: it starts nothing and moves nothing. The only thing it may change is
        who is holding the session, and that only when the owner has gone away or the
        user has said "take control" on the screen.
        """
        if not self.ended and (claim or not self.present or self._owner == client_id):
            self._take(client_id, force=claim, publish=True)
        return self.snapshot()

    @callback
    def heartbeat(self, client_id: str) -> dict[str, Any]:
        """Keep the owner present. Never an error, never a transition, never a claim."""
        if self.ended or self._owner != client_id:
            return {"owner": False, "present_until": None}
        self._owner_seen = dt_util.utcnow()
        return {"owner": True, "present_until": _at_second(self.present_until)}

    async def async_act(
        self, client_id: str, revision: int, action: str, value: Any = None
    ) -> dict[str, Any]:
        """One step of the conversation: a menu option, or a form being sent."""
        self._guard_live()
        self._check_owner(client_id)
        self._guard_revision(revision)
        if action == SESSION_SUBMIT:
            if self._form() is None:
                raise self._not_offered(action)
        elif action not in self._actions():
            raise self._not_offered(action)
        self._take(client_id)
        self._touch()
        await self._async_dispatch(action, value)
        self._pump()
        return self.snapshot()

    async def async_stop(self, client_id: str) -> dict[str, Any]:
        """Write a stop frame now: the one verb that touches the shutter.

        With a movement of the session under way the step is void - what it was
        measuring did not happen - so the screen becomes `problem_interrupted` at once
        and the job that is still awaiting a primitive is left to finish into nothing
        (see `_generation`). Cancelling the task instead would abandon a primitive
        half way through its own `finally`.
        """
        self._guard_live()
        self._check_owner(client_id)
        self._take(client_id)
        self._touch()
        interrupting = self._movement is not None
        if interrupting:
            self._overtake()
        refused: str | None = None
        try:
            await self._cover().async_calib_stop()
        except CalibrationError as err:
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            refused = err.reason if err.reason in PROBLEM_REASONS else REASON_UNKNOWN
        except HomeAssistantError as err:
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            refused = REASON_UNKNOWN
        if interrupting:
            self._movement = None
            self._press = None
            self._disarm_press()
            self._at = None
            # A stop the gateway would not take is not the same news as a step
            # interrupted: the shutter is still running on to its end stop, and the
            # dialog has a sentence for that in seven languages (`problem_not_stopped`).
            self._show_problem(refused or REASON_INTERRUPTED)
        return self.snapshot()

    @callback
    def leave(self, client_id: str) -> dict[str, Any]:
        """Detach this client. Nothing is written and nothing is stopped.

        A session with nothing measured ends with it - there is nothing to protect and
        a shutter should not be held by a window somebody closed. The answer is then the
        terminal snapshot and not nothing: the screen that follows says the calibration
        was closed before the first measurement, and it needs the outcome to say it.
        One that *has* measured something stays, without an owner, until somebody picks
        it up or the lease runs out.

        A `leave` from a client that is **not** the owner is a no-op, whether the owner
        is there or not (contract amendment, lot B3, after the independent review). It
        is sent as a page goes away: a read-only tab being closed has nothing to leave,
        and a departure is the one gesture that must never *acquire* anything. The rule
        the amendment of 19 September wrote for the heartbeat - ownership is taken by a
        verb that does something, or explicitly with `attach` and `claim` - reached this
        one through a second door: a phone locked for forty-five seconds on the first
        screen, a second tab closed, and the session ended as `left` under a user who
        was about to come back to it.
        """
        if self.ended or self._owner != client_id:
            return self.snapshot()
        if not self._anything_measured():
            self._end("left")
            return self.snapshot()
        self._owner = None
        self._publish()
        return self.snapshot()

    async def async_cancel(self, client_id: str, force: bool = False) -> dict[str, Any]:
        """Throw the provisional values away and end. The shutter is not stopped.

        Idempotent and never refused for concurrency: it carries no revision, because
        a transition the user did not cause - a press timing out, a shutter brought
        back to its end stop - must not turn "Annulla" into "somebody moved on, try
        again". That is the silent failure the panel exists to avoid (lesson 2).
        """
        if self.ended:
            return {"session": self.snapshot(), "already_ended": True}
        self._take(client_id, force=force)
        await self.async_end("cancelled")
        return {"session": self.snapshot(), "already_ended": False}

    async def async_save(self, client_id: str, revision: int, target: str) -> dict[str, Any]:
        """Write the result, once, and only from the review."""
        self._guard_live()
        self._check_owner(client_id)
        if self._screen().state != "review" or self._review is None or self._result is None:
            raise _refuse(
                ERR_NOT_ALLOWED,
                ERROR_NOT_IN_REVIEW,
                "There is nothing to save until the calibration reaches its summary",
            )
        self._guard_revision(revision)
        if target not in self._review["targets"]:
            raise self._not_offered(target)
        name = self._measured_name or self._profile
        if target == "profile" and self._path == PATH_FIRST and not _a_name(name):
            raise _refuse(
                ERR_SERVICE_VALIDATION_ERROR,
                ERROR_INVALID_NAME,
                f"{name!r} cannot be used as a profile name",
                {"profile": str(name or "")},
            )
        self._take(client_id)
        self._touch()
        written = await async_write(
            self.hass,
            self.entry,
            "calibration session",
            lambda entry, store: self._async_store_the_result(store, target),
            holder=self.cover_unique_id,
        )
        if self.ended:
            # A `cancel` arrived while the store was being written. The write happened
            # and is not taken back - it is the measurement the user asked to keep -
            # but the session has already ended and its outcome is not rewritten.
            LOGGER.warning(
                "Panel calibration of %s: the save completed after the session had "
                "ended (%s); what was written stands",
                self.cover_name,
                self._outcome_reason(),
            )
            return {"session": self.snapshot(), "overview": written["overview"]}
        resolved = self._resolved()
        # The overview `async_write` built is the gateway as it was **while this session
        # still held the shutter**: the store is written inside the write and the session
        # only ends when it comes back. So the answer carries the one `_finish` publishes
        # instead, or it would say `review` beside a snapshot that says `saved`.
        self._finish(
            "saved",
            extra={
                "profile": resolved.profile,
                "origin": resolved.origin,
                "source": resolved.source,
            },
        )
        LOGGER.info(
            "Guided calibration of %s saved from the panel (%s)",
            self.cover_name,
            self._measured_name or self._profile or "overrides",
        )
        return {"session": self.snapshot(), "overview": async_overview(self.hass, self.entry)}

    # ---------------------------------------------------------------- the conversation
    @callback
    def _screen(self, step: str | None = None) -> _Screen:
        return SCREENS[step or self._step]

    @callback
    def _actions(self) -> list[str]:
        """The step's menu options, narrowed to what this backend can carry out."""
        actions = list(self._screen().actions)
        if self._step == "path":
            if not self.profiles:
                actions = [action for action in actions if action == PATH_FIRST]
            actions = [action for action in actions if action in IMPLEMENTED_PATHS]
        if "refine" in actions and "thorough" not in IMPLEMENTED_LEVELS:
            actions.remove("refine")
        if self._step == "verify_result" and self._offers_the_correction():
            # The one screen that can put a *path* in front of the two ordinary ways
            # on: the profile this window was given does not describe it, and the
            # correction is the answer to that rather than another reading.
            actions = [PATH_REFINE, *actions]
        if self._notice == "reading_stale":
            # The reading no longer corresponds to where the shutter is; the field
            # stays on the screen (the user may have measured before it was touched)
            # but the way forward is the step again.
            return ["repeat_tape"]
        return actions

    @callback
    def _deviation_shown(self) -> float:
        """How far out the verification was, as the screen says it: rounded, unsigned."""
        deviation = self._measured.deviation
        return 0.0 if deviation is None else round(abs(deviation), 1)

    @callback
    def _offers_the_correction(self) -> bool:
        """Path B's verification, far enough out to be worth correcting the window.

        Rounded *before* the threshold is applied, as the dialog rounds it
        (`async_step_verify_result`, :3014): the number on the screen is the number
        that decided, and a gap of 3.04 cm that read "3,0 cm" and offered a correction
        was a screen arguing with itself over a digit nobody can see. The threshold is
        the dialog's fixed 3 cm (SPEC decision 20); how well the profile itself was
        measured is shown beside it (`check.profile_level`) rather than folded into it.
        """
        if self._path != PATH_PROFILE or PATH_REFINE not in IMPLEMENTED_PATHS:
            return False
        return self._deviation_shown() > REFINE_THRESHOLD_CM

    @callback
    def _not_offered(self, action: str) -> PanelError:
        return _refuse(
            ERR_NOT_ALLOWED,
            ERROR_ACTION_NOT_OFFERED,
            f"{action!r} is not something this step offers",
            {"action": action},
        )

    async def _async_dispatch(self, action: str, value: Any) -> None:
        """Carry out one action, up to the first movement it starts."""
        if action == SESSION_SUBMIT:
            await self._async_submit(value)
            return
        handler = getattr(self, f"_async_do_{action}", None)
        if handler is None:  # pragma: no cover - `_actions` never offers one without
            raise self._not_offered(action)
        await handler()

    # ---- choosing a path
    async def _async_do_path_a(self) -> None:
        self._path = PATH_FIRST
        self._show("path_a")

    async def _async_do_begin(self) -> None:
        self._path = PATH_FIRST
        self._measured = measure.Measured()
        await self._async_start_plan(PLANS[PATH_FIRST])

    async def _async_do_path_b(self) -> None:
        """"Ne ho gia' misurata una uguale": the profile form, and nothing else yet."""
        self._path = PATH_PROFILE
        self._show("path_b")

    async def _async_do_path_c(self) -> None:
        """"Segue un profilo ma sbaglia": the profile form again, from two screens.

        From the menu of paths, and from the verification of path B when the shutter
        stopped further from where the profile said than the threshold allows. In the
        second case the travel this conversation has just read with a tape is kept,
        which is what makes the jump worth offering at all: it is the same window and
        the same tape (`async_step_path_c`, :1823-1828, and `_correct_this_profile`).
        """
        self._path = PATH_REFINE
        # The verification that sent the user here was an answer about the profile
        # this window is about to stop being described by. It goes with the path: a
        # screen of a *correction* publishing a check with path B's threshold on it
        # would be describing a conversation that no longer exists.
        self._check = None
        self._show("path_c")

    # ---- the three scopes of a correction
    async def _async_do_times_only(self) -> None:
        self._scope = "times_only"
        await self._async_start_plan(PLANS["times_only"])

    async def _async_do_times_and_rolls(self) -> None:
        self._scope = "times_and_rolls"
        await self._async_start_plan(PLANS["times_and_rolls"])

    async def _async_do_points_only(self) -> None:
        """The thorough calibration alone: nothing is pressed for, so nothing is timed.

        The run times and the slat phase the readings correct are the ones the cover
        moves on **today**, taken as if they had been measured
        (`_adopt_the_model_in_use`, :1929). The one way they cannot be put together is
        a window the gateway's configuration no longer has - the entry was reloaded off
        an edited `myhome.yaml` under the session - and that is not a step that can be
        repeated, so the session ends the way it ends when the shutter goes away.
        """
        self._scope = "points_only"
        adopted = measure.adopted_timings(
            self._measured,
            measure.values_in_use(
                unique_id=self.cover_unique_id,
                device=self._device(),
                profiles=self.profiles,
                record=self._record(),
                profile=self._profile,
                height=self._measured.height,
            ),
        )
        if adopted is None:
            LOGGER.warning(
                "Panel calibration of %s: the model this shutter moves on cannot be "
                "read any more, so the thorough calibration has nothing to correct",
                self.cover_name,
            )
            await self.async_end("cover_gone", stop=True)
            return
        # Replaced, not merged: `adopted_timings` answers a copy, and the copy is the
        # measurement from here on (B1 handoff, R2).
        self._measured = adopted
        await self._async_start_thorough(from_here=False)

    # ---- the thorough calibration, and path B's check
    async def _async_do_refine(self) -> None:
        """"Continua con la calibrazione approfondita", from a summary (:3386)."""
        await self._async_start_thorough(from_here=True)

    async def _async_do_verify_now(self) -> None:
        """Graft the check - and the homing it starts from - onto the plan here."""
        index = (self._index or 0) + 1
        self._plan[index:index] = list(PLAN_VERIFY_B)
        await self._async_advance()

    async def _async_do_skip_verify(self) -> None:
        """Take the profile at its word."""
        await self._async_advance()

    # ---- the confirmations and the briefs
    async def _async_do_confirm_closed(self) -> None:
        await self._async_advance()

    async def _async_do_confirm_closed_again(self) -> None:
        self._show("open_full_brief")

    async def _async_do_accept_step(self) -> None:
        await self._async_advance()

    async def _async_do_repeat_step(self) -> None:
        await self._async_enter()

    async def _async_do_not_right(self) -> None:
        self._stop_first = True
        await self._async_enter()

    async def _async_do_tape_start(self) -> None:
        await self._async_advance()

    # ---- the ascent
    async def _async_do_open_start(self) -> None:
        await self._async_timed_run("open_brief", "open_start", "starting_open", "open_lift")

    async def _async_do_open_full_start(self) -> None:
        await self._async_timed_run(
            "open_full_brief", "open_full_start", "starting_open_full", "open_top"
        )

    async def _async_do_close_start(self) -> None:
        await self._async_timed_run("close_brief", "close_start", "starting_close", "close_bottom")

    async def _async_do_lifted_off(self) -> None:
        if self._timed_out():
            self._show_problem(REASON_TIMEOUT)
            return
        if self._lift_off is None:
            self._lift_off = dt_util.utcnow()
        self._disarm_press()
        self._press = None
        self._begin_movement(
            step="lift_stop",
            kind="free",
            direction=DIRECTION_OPEN,
            progress_action="stopping_lift",
            job=self._job_stop_lift,
            settle=self._settle_stop_lift,
            done="lift_measured",
            anchor=self._motor_start,
            planned_s=self._full_run(DIRECTION_OPEN),
        )

    async def _async_do_lift_too_early(self) -> None:
        await self._async_enter()

    async def _async_do_lift_accept(self) -> None:
        await self._async_goto("open_home_again")

    async def _async_do_lift_gap(self) -> None:
        self._show("lift_gap")

    async def _async_do_stopped_open(self) -> None:
        if self._timed_out():
            self._show_problem(REASON_TIMEOUT)
            return
        self._disarm_press()
        self._press = None
        try:
            run = timing_from_presses(self._motor_start, None, dt_util.utcnow())
            self._measured.opening = timing_with_slat(run, self._measured.slat_seconds or 0.0)
        except CalibrationError as err:
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            self._show_problem("bad_point")
            return
        # The run was free: whatever the press measured, the shutter is at the top.
        self._at = DIRECTION_OPEN
        self._movement = None
        self._show("open_result_gap" if self._measured.lift_gap_cm is not None else "open_result")

    async def _async_do_stopped_closed(self) -> None:
        if self._timed_out():
            self._show_problem(REASON_TIMEOUT)
            return
        self._disarm_press()
        self._press = None
        try:
            self._measured.closing = timing_from_presses(self._motor_start, None, dt_util.utcnow())
        except CalibrationError as err:
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            self._show_problem("bad_point")
            return
        self._at = DIRECTION_CLOSE
        self._movement = None
        self._show("close_result")

    # ---- the travel
    async def _async_do_repeat_measure(self) -> None:
        self._forget_the_travel()
        self._show("height")

    # ---- the tape
    async def _async_do_repeat_tape(self) -> None:
        self._forget_the_reading()
        await self._async_enter()

    async def _async_do_tape_not_right(self) -> None:
        self._forget_the_reading()
        self._stop_first = True
        await self._async_enter()

    # ---- the forms
    async def _async_submit(self, value: Any) -> None:
        field = self._screen().form
        if field == CONF_HEIGHT:
            await self._async_submit_height(value)
        elif field == "gap_cm":
            await self._async_submit_gap(value)
        elif field == "measured_cm":
            await self._async_submit_reading(value)
        elif field == CONF_NAME:
            await self._async_submit_name(value)
        elif field == CONF_PROFILE:
            await self._async_submit_profile(value)
        else:  # pragma: no cover - every field of `SCREENS` is named above
            # A field added to a screen and to nothing else: refused rather than sent
            # to whichever handler happened to be last.
            raise self._not_offered(SESSION_SUBMIT)

    async def _async_submit_height(self, value: Any) -> None:
        number = _finite(value)
        if number is None:
            self._show("height", error=ERROR_NOT_A_NUMBER)
            return
        if not MIN_HEIGHT_CM <= number <= MAX_HEIGHT_CM:
            self._show("height", error=ERROR_OUT_OF_RANGE)
            return
        self._measured.height = number
        self._measured.height_measured = True
        self._show("height_result")

    async def _async_submit_gap(self, value: Any) -> None:
        written = "" if value is None else str(value).strip()
        if not written:
            await self._async_goto("open_home_again")
            return
        number = _finite(written)
        if number is None:
            self._show("lift_gap", error=ERROR_NOT_A_NUMBER)
            return
        if not 0.0 <= number <= MAX_GAP_CM:
            self._show("lift_gap", error=ERROR_OUT_OF_RANGE)
            return
        if number < TOUCHING_CM:
            self._show("lift_early")
            return
        self._measured.lift_gap_cm = number
        await self._async_goto("open_home_again")

    async def _async_submit_reading(self, value: Any) -> None:
        step = self._step
        if _finite(value) is None:
            self._show(step, error=ERROR_NOT_A_NUMBER)
            return
        number, error = measure.accept_measurement(value, height=self._measured.height)
        if number is None:
            self._show(step, error=error or ERROR_ABOVE_THE_TRAVEL)
            return
        if step == "measure_verify":
            await self._async_verified(number)
            return
        if self._report is None:
            self._show(step, error=ERROR_ABOVE_THE_TRAVEL)
            return
        if step == "measure_descent":
            self._measured.descent.append((self._report.motor_seconds, number))
            self._tape_target = "descent"
        else:
            self._measured.ascent.append((self._report.motor_seconds, number))
            self._tape_target = "ascent"
        self._show("tape_result")

    async def _async_submit_profile(self, value: Any) -> None:
        """The kind of shutter this window is one of, chosen on `path_b` or `path_c`.

        A name nobody defines is `unknown_profile` and not a `form.error`: the field is
        a choice out of a list the snapshot carries, so a value outside it is a client
        sending something it was not offered, which is the protocol's business and not
        the user's. Every field where the user *types* answers with `form.error`.
        """
        name = str(value or "").strip()
        if name not in self.profiles:
            raise _refuse(
                ERR_NOT_FOUND,
                ERROR_UNKNOWN_PROFILE,
                f"No profile called {name!r} on {self.entry.title}",
                {"profile": name},
            )
        if self._path == PATH_REFINE:
            self._correct_this_profile(name)
            self._show("refine_scope")
            return
        self._profile = name
        self._measured = measure.Measured()
        await self._async_start_plan(PLANS[PATH_PROFILE])

    @callback
    def _correct_this_profile(self, name: str) -> None:
        """Start a correction of one profile, from what this window is known to be.

        The dialog's `async_step_path_c` on submit (:1811-1828). A travel this
        conversation measured is kept - path B's check sends the user here with the
        tape reading already done, and it is the same window and the same tape - and
        otherwise the conversation starts from the travel this window is *known* to
        have, so that the summary does not show "-" for it and Save does not write a
        record that has forgotten it. Never a profile's reference height: that is
        another window's travel (`own_height`).
        """
        measured_here = self._measured.height is not None and self._measured.height_measured
        self._profile = name
        self._measured = measure.Measured(
            height=self._measured.height
            or measure.own_height(record=self._record(), device=self._device()),
            height_measured=measured_here,
        )
        self._scope = None
        self._check = None
        self._result = None
        self._review = None

    async def _async_submit_name(self, value: Any) -> None:
        name = str(value or "").strip()
        if not _a_name(name):
            self._show("profile_name", error=ERROR_INVALID_NAME)
            return
        self._measured_name = name
        await self._async_advance()

    async def _async_verified(self, measured_cm: float) -> None:
        """The reading the model is asked about, rather than fitted to.

        One question put to the model as it stands, at a fraction nothing was fitted
        to: path B asks it of the profile scaled to this window, the thorough
        calibration of the fit it has just made (`_deviation` and `_model_values`,
        :2965-3013). The answer is a distance in centimetres, and the screen that
        follows is where it is read.
        """
        try:
            model = measure.model_values(
                path=self._path or PATH_FIRST,
                measured=self._measured,
                profiles=self.profiles,
                profile=self._profile,
            )
        except CalibrationError as err:
            # The same guard as everywhere the ported arithmetic is called (B1 handoff,
            # R1(b)): a reading the model cannot place is `bad_point`, which is the
            # dialog's own screen for it and offers the step again.
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            self._show_problem("bad_point")
            return
        gap = measure.deviation(
            measured_cm, report=self._report, height=self._measured.height, model=model
        )
        _direction, fraction = self._pending or (DIRECTION_CLOSE, VERIFY_RUN)
        self._measured.deviation = gap
        self._measured.verify_fraction = fraction
        self._tape_target = None
        self._check = self._the_check(measured_cm, fraction, gap)
        self._show("verify_result")

    @callback
    def _the_check(
        self, measured_cm: float, fraction: float, gap: float | None
    ) -> dict[str, Any]:
        """The verification as the contract publishes it (§12, `check`).

        Where the model said the bar would be, where it really was, how far apart the
        two are - and, when it is a profile that is being questioned, the threshold
        above which the correction is offered together with how well that profile was
        itself measured. The last two are what makes 3 cm readable: the same gap means
        nothing on a profile measured at the basic level and something on one that went
        through its own check (contract §2.5, SPEC decision 20).
        """
        level: str | None = None
        checked: float | None = None
        threshold: float | None = None
        if self._path == PATH_PROFILE:
            threshold = REFINE_THRESHOLD_CM
            level, checked = self._how_the_profile_was_measured()
        return {
            "fraction": fraction,
            "predicted_cm": None if gap is None else measured_cm - gap,
            "measured_cm": measured_cm,
            "gap_cm": None if gap is None else round(abs(gap), 1),
            "threshold_cm": threshold,
            "profile_level": level,
            "profile_check_cm": checked,
        }

    @callback
    def _how_the_profile_was_measured(self) -> tuple[str | None, float | None]:
        """The level of the profile being checked, and the gap its own check reported.

        Off the `raw` block the guided calibration keeps beside its conclusions, read
        with the panel's own `level_and_note` so that the overview row and this screen
        cannot disagree about what "thorough" means. A profile written by hand, or one
        that lives in `cover_profiles:` and was never measured here, has no `raw`: both
        are then `null` and the screen leaves the comparison out rather than inventing
        a level for it.
        """
        store = self._store()
        stored = None if store is None else store.profile(self._profile or "")
        level, gap = level_and_note(stored)
        if level is not None:
            # `precise` is what the store and the overview have called the level since
            # 0.5.0; `thorough` is what the contract calls it (SPEC §3.11).
            level = "thorough" if level == CALIBRATION_LEVEL_PRECISE else "basic"
        return level, None if gap is None else round(abs(gap), 1)

    # -------------------------------------------------------------------- the plan
    @callback
    def _thorough_plan(self) -> tuple[str, ...]:
        """The thorough calibration, with the curtain travel first when nobody knows it.

        The dialog's `_thorough_plan` (:1946). Every reading of the phase is a number
        of centimetres out of the travel, so the plan cannot start without one; a
        travel already known is not asked for again, because the user is standing in
        front of the shutter with a tape and that is the one reading that does not
        change.
        """
        return PLAN_PRECISE if self._measured.height else PLAN_PRECISE_TRAVEL

    async def _async_start_thorough(self, *, from_here: bool) -> None:
        """Install the thorough plan, after what has been walked or instead of it.

        The dialog's `_async_start_thorough` (:1951). `from_here` tells the two ways in
        apart: pressed on a summary, the plan replaces the tail of the one that got
        there - the pointer is on `summary` and everything before it has already
        happened, so the presses are **not** repeated and the readings are fitted over
        the times already measured; chosen as the third scope of a correction, it is
        the whole plan and the conversation starts on its first stage.
        """
        self._measured.precise = True
        plan = list(self._thorough_plan())
        if not from_here:
            await self._async_start_plan(plan)
            return
        self._plan = self._plan[: self._index or 0] + plan
        await self._async_enter()

    async def _async_start_plan(self, plan: Sequence[str]) -> None:
        self._plan = list(plan)
        self._index = 0
        await self._async_enter()

    async def _async_advance(self) -> None:
        self._index = (self._index or 0) + 1
        await self._async_enter()

    async def _async_enter(self) -> None:
        """(Re-)enter the stage the pointer is on, with its own state cleared."""
        self._error = None
        self._report = None
        # A summary describes a conversation that has finished; entering a stage means
        # this one has not. Without this, "Continua con la calibrazione approfondita"
        # would leave the review of the *basic* result in the snapshot for the whole of
        # the four readings that are about to replace it, and `save` reads the same two
        # fields the screen does.
        self._result = None
        self._review = None
        stage = self._plan[self._index or 0]
        if stage in FRACTION_STAGES:
            await self._async_fraction_stage(stage)
            return
        handler = getattr(self, f"_async_stage_{stage}", None)
        if handler is None:  # pragma: no cover - every stage of every plan has one
            # A stage of a plan imported from the dialog that this module knows no
            # screen for: it would be a stage added there and not here.
            raise self._not_offered(stage)
        await handler()

    # ---- stages
    async def _async_stage_home_closed(self) -> None:
        self._begin_homing(step="home_closed", direction=DIRECTION_CLOSE, done="home_closed_done")

    async def _async_stage_open_timed(self) -> None:
        self._forget_the_ascent()
        self._begin_homing(step="open_timed", direction=DIRECTION_CLOSE, done="open_brief")

    async def _async_stage_open_home_again(self) -> None:  # pragma: no cover - not a plan stage
        self._begin_homing(step="open_home_again", direction=DIRECTION_CLOSE, done="closed_again")

    async def _async_stage_height_read(self) -> None:
        if self._stop_first:
            self._forget_the_travel()
        self._begin_homing(step="height_read", direction=DIRECTION_OPEN, done="height")

    async def _async_stage_close_timed(self) -> None:
        self._begin_homing(step="close_timed", direction=DIRECTION_OPEN, done="close_brief")

    async def _async_stage_tape_brief(self) -> None:
        self._order_the_tape_phase()
        self._show("tape_brief")

    async def _async_stage_verify_offer(self) -> None:
        """Path B: the travel is enough, but the shutter can be asked all the same."""
        self._show("verify_offer")

    async def _async_stage_profile_name(self) -> None:
        self._show("profile_name")

    async def _async_stage_summary(self) -> None:
        if not self._build_the_review():
            self._show_problem("bad_point")
            return
        self._show(f"summary_{self._review['variant']}")  # type: ignore[index]

    async def _async_fraction_stage(self, step: str) -> None:
        """One reading's two movements: to an end stop, then to the percentage.

        Two screens rather than one because they are two different things to watch,
        and because that is what the dialog does (`_async_fraction_stage`): the run to
        the percentage is `tape_run`, entered when the homing is over.
        """
        direction, fraction, done = FRACTION_STAGES[step]
        self._pending = (direction, fraction)
        self._after_the_run = done
        # ...and no reading of this stage has been sent yet. Without this,
        # `repeat_tape` on a stage whose reading is still to come - which is what a
        # stale reading offers (§11.5) - would take back the reading of the stage
        # *before*, which was accepted two screens ago and is perfectly good.
        self._tape_target = None
        # ...and the answer of a verification that is being made again is not an answer
        # yet: the shutter is on its way to the end stop the run starts from.
        self._check = None
        self._begin_homing(step=step, direction=_other_end(direction), done="tape_run")

    @callback
    def _tape_phase(self) -> list[str]:
        """The readings that follow the briefing, read off the plan as the dialog does."""
        phase: list[str] = []
        for stage in self._plan[(self._index or 0) + 1 :]:
            if stage not in FRACTION_STAGES and stage != "height_read":
                break
            phase.append(stage)
        return phase

    @callback
    def _order_the_tape_phase(self) -> None:
        """Deal the readings out again, starting from the end stop the shutter is at."""
        phase = self._tape_phase()
        start = (self._index or 0) + 1
        self._plan[start : start + len(phase)] = order_the_readings(phase, self._at)

    # ------------------------------------------------------------------- the movements
    @callback
    def _begin_homing(self, *, step: str, direction: str, done: str) -> None:
        self._begin_movement(
            step=step,
            kind="homing",
            direction=direction,
            progress_action=HOMING_ACTION[direction],
            job=lambda: self._job_home(direction),
            settle=self._settle_home,
            done=done,
            anchor=dt_util.utcnow(),
            planned_s=self._full_run(direction),
        )

    async def _async_timed_run(self, brief: str, step: str, action: str, done: str) -> None:
        """Start a timed run - after bringing the shutter back to its end stop if need be.

        A stopwatch never starts from a point nobody knows (SPEC §3.7). When something
        outside the session has moved the shutter since it last reached the end stop
        this run begins at, the session takes it back there itself and returns to the
        same brief with a note, rather than refusing and asking the user to do it.
        """
        direction, from_end, homing_step = TIMED_RUN_BRIEFS[brief]
        if self._at != from_end:
            self._begin_movement(
                step=homing_step,
                kind="homing",
                direction=from_end,
                progress_action=HOMING_ACTION[from_end],
                job=lambda: self._job_home(from_end),
                settle=self._settle_home,
                done=brief,
                anchor=dt_util.utcnow(),
                planned_s=self._full_run(from_end),
                notice_when_done="rehomed",
            )
            return
        self._motor_start = None
        self._begin_movement(
            step=step,
            kind="free",
            direction=direction,
            progress_action=action,
            job=lambda: self._job_start(direction),
            settle=self._settle_start,
            done=done,
            anchor=None,
            planned_s=self._full_run(direction),
        )

    @callback
    def _begin_movement(
        self,
        *,
        step: str,
        kind: str,
        direction: str,
        progress_action: str,
        job: Callable[[], Awaitable[Any]],
        settle: Callable[[Any], None],
        done: str,
        anchor: datetime | None,
        planned_s: float | None,
        notice_when_done: str | None = None,
    ) -> None:
        """Publish the movement screen, then queue the primitive behind it.

        The screen goes out first and the awaiting happens afterwards: a panel that
        only heard about a movement once it was over would show nothing at all while a
        shutter ran for twenty seconds. `_pump` is what runs the queue, once, in a task
        of its own.

        The generation is taken **here**, when the work is queued, and not when the work
        begins: between the two there is a turn of the loop, and a stop - or a wall
        switch - that arrives in it has to be able to cancel a frame that has not gone
        out yet. Reading the counter at the start of the job would read it after it had
        already been raised, which is no check at all.
        """
        self._movement = _Movement(
            kind=kind, direction=direction, progress_action=progress_action,
            started_at=anchor, planned_s=planned_s,
        )
        self._press = None
        self._external_move = False
        self._show(step)
        generation = self._generation
        self._queued = lambda: self._async_movement_job(
            job, settle, done, notice_when_done, generation
        )

    @callback
    def _pump(self) -> None:
        """Run whatever the last transition queued, in one task for the whole chain."""
        if self._queued is None or self._pumping:
            return
        self._pumping = True
        self.hass.async_create_task(
            self._async_pump(), f"myhome calibration session {self.session_id}", eager_start=False
        )

    async def _async_pump(self) -> None:
        try:
            while self._queued is not None:
                work, self._queued = self._queued, None
                await work()
        finally:
            self._pumping = False

    async def _async_movement_job(
        self,
        job: Callable[[], Awaitable[Any]],
        settle: Callable[[Any], None],
        done: str,
        notice: str | None,
        generation: int,
    ) -> None:
        """One stage's movements, turning every failure into a screen that says so.

        The generation is checked **again right before the frame goes out**, and not
        only when this coroutine starts: a stop written in the turn of the loop between
        the queueing and here must stop the movement from happening at all, not merely
        from being published afterwards. Nothing this job measures is written into the
        session until it has passed the check on the way out either (`settle`), so a
        job that was overtaken leaves no trace of a shutter it no longer describes.
        """
        if generation != self._generation or self.ended:
            return
        self._error = None
        # Nothing is known about where the shutter is while it is moving, and nothing
        # is known about where it ended up if the movement failed.
        self._at = None
        outcome: Any = None
        try:
            if self._stop_first:
                self._stop_first = False
                with contextlib.suppress(CalibrationError):
                    await self._cover().async_calib_stop()
                if generation != self._generation or self.ended:
                    return
            outcome = await job()
        except CalibrationError as err:
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            self._error = (
                err.reason
                if err.reason in PROBLEM_REASONS or err.reason == REASON_UNKNOWN_COVER
                else REASON_UNKNOWN
            )
        except HomeAssistantError as err:
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            self._error = REASON_UNKNOWN
        except Exception:  # noqa: BLE001 - a session must not be left with a spinning bar
            LOGGER.exception("Panel calibration of %s failed unexpectedly", self.cover_name)
            self._error = REASON_UNKNOWN
        if generation != self._generation or self.ended:
            # A stop, an external movement or a cancellation has overtaken this job:
            # the screen it would have published is not the screen the user is on, and
            # what it measured is about a shutter that has since been moved.
            return
        if self._error is None:
            settle(outcome)
        if done not in PRESS_STEPS or self._error is not None:
            # A free run whose press is still to come goes on running: what has come
            # back is the *command*, not the shutter. Everything else is over.
            self._movement = None
        if self._error == REASON_UNKNOWN_COVER:
            await self.async_end("cover_gone", stop=True)
            return
        if self._error is not None:
            self._show_problem(self._error)
            return
        await self._async_goto(done, notice=notice)

    # Each job answers what it found and writes nothing: `_async_movement_job` assigns
    # it through the matching `_settle_*` once it knows the job was not overtaken.
    async def _job_home(self, direction: str) -> str:
        await self._cover().async_calib_home(direction)
        return direction

    @callback
    def _settle_home(self, direction: Any) -> None:
        self._at = str(direction)

    async def _job_start(self, direction: str) -> datetime:
        """Let it run free while we watch (it is already at the far end stop)."""
        return await self._cover().async_calib_start(direction)

    @callback
    def _settle_start(self, started: Any) -> None:
        self._motor_start = started
        if self._movement is not None:
            self._movement.started_at = started

    async def _job_stop_lift(self) -> tuple[datetime, datetime]:
        """Stop the lift-off run, noting when the frame went out and the motor stopped."""
        cover = self._cover()
        delivered = await cover.async_calib_stop()
        return delivered, await cover.async_calib_motor_stop()

    @callback
    def _settle_stop_lift(self, instants: Any) -> None:
        self._stop_delivered, self._motor_stopped = instants

    async def _job_fraction(self, direction: str, fraction: float) -> RunReport:
        return await self._cover().async_calib_run_fraction(direction, fraction)

    @callback
    def _settle_fraction(self, report: Any) -> None:
        self._report = report


    # ------------------------------------------------------------------ the router
    async def _async_goto(self, step: str, *, notice: str | None = None) -> None:
        """The steps a movement hands over to, some of which do something first."""
        if step == "tape_run":
            direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
            self._begin_movement(
                step="tape_run",
                kind="fraction",
                direction=direction,
                progress_action=RUNNING_ACTION[direction],
                job=lambda: self._job_fraction(direction, fraction),
                settle=self._settle_fraction,
                done=self._after_the_run,
                anchor=dt_util.utcnow(),
                planned_s=self._planned_fraction(direction, fraction),
            )
            return
        if step in PRESS_STEPS:
            self._arm_press(PRESS_STEPS[step])
            self._show(step)
            return
        if step == "lift_measured":
            self._lift_measured()
            return
        if step == "open_home_again":
            self._begin_homing(
                step="open_home_again", direction=DIRECTION_CLOSE, done="closed_again"
            )
            return
        self._show(step, notice=notice)

    @callback
    def _planned_fraction(self, direction: str, fraction: float) -> float:
        model = self._model_now()
        return calibration_run_seconds(
            direction,
            model[CONF_OPENING_TIME],
            model[CONF_CLOSING_TIME],
            model[CONF_SLAT_TIME],
            fraction,
        )

    @callback
    def _lift_measured(self) -> None:
        """Turn the press into a slat phase, and go and look at where it stopped."""
        measured = self._measured
        try:
            measured.slat_seconds = slat_time_from_press(self._motor_start, self._lift_off)
        except CalibrationError as err:
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            self._show_problem("bad_point")
            return
        if self._motor_start is not None and self._motor_stopped is not None:
            measured.lift_run_sec = (self._motor_stopped - self._motor_start).total_seconds()
        measured.lift_late = (
            self._stop_delivered is not None
            and self._lift_off is not None
            and (self._stop_delivered - self._lift_off).total_seconds() > LATE_STOP_SEC
        )
        self._show("lift_check_late" if measured.lift_late else "lift_check")

    # ------------------------------------------------------------- forgetting things
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

    @callback
    def _forget_the_travel(self) -> None:
        self._measured.height = None
        self._measured.height_measured = False

    @callback
    def _forget_the_reading(self) -> None:
        if self._tape_target == "descent" and self._measured.descent:
            self._measured.descent.pop()
        elif self._tape_target == "ascent" and self._measured.ascent:
            self._measured.ascent.pop()

    @callback
    def _anything_measured(self) -> bool:
        """True once this session holds a number nobody else has.

        What `leave` asks before deciding whether the session is worth keeping, and
        what the contract calls "something provisional left to protect".
        """
        measured = self._measured
        return bool(
            measured.height_measured
            or measured.opening
            or measured.closing
            or measured.slat_seconds is not None
            or measured.lift_run_sec is not None
            or measured.descent
            or measured.ascent
            or measured.deviation is not None
            or self._measured_name
        )

    # ---------------------------------------------------------------------- the clocks
    @callback
    def _touch(self) -> None:
        """Restart the lease: somebody is still having this conversation.

        How long it is worth waiting is a property of the screen the session is on, and
        is read off it rather than carried in a variable each step has to remember to
        set: a screen with nothing moving is waiting for somebody to read it (half an
        hour is an ordinary length of interruption), and one that follows a movement is
        waiting for somebody standing in front of a shutter with a tape (ten minutes of
        that means they walked away). It is the dialog's `_idle_timeout`, asked of the
        step instead of assigned before it, so a verb that touches the lease without
        changing the screen cannot silently make it half an hour.
        """
        if self.ended:
            return
        timeout = (
            MOVED_IDLE_TIMEOUT_SEC if self._screen().after_a_movement else IDLE_TIMEOUT_SEC
        )
        self._disarm_lease()
        self._lease_at = dt_util.utcnow() + timedelta(seconds=timeout)
        self._lease = async_call_later(self.hass, timeout, self._async_lease_expired)

    @callback
    def _disarm_lease(self) -> None:
        if self._lease is not None:
            self._lease()
            self._lease = None
        self._lease_at = None

    @callback
    def _disarm_press(self) -> None:
        if self._press_timer is not None:
            self._press_timer()
            self._press_timer = None

    @callback
    def _arm_press(self, kind: str) -> None:
        """Wait for one press, and give up on it out loud rather than for ever.

        The dialog can only notice a press that never came when a later one arrives
        (a flow cannot push a screen at a browser); the panel can, so it does.
        """
        now = dt_util.utcnow()
        self._shown_at = now
        self._press = _Press(kind=kind, expires_at=now + timedelta(seconds=PRESS_TIMEOUT_SEC))
        self._disarm_press()
        self._press_timer = async_call_later(
            self.hass, PRESS_TIMEOUT_SEC, self._async_press_expired
        )

    @callback
    def _timed_out(self) -> bool:
        """True when the press we were waiting for took longer than a user would."""
        if self._shown_at is None:  # pragma: no cover - every press step sets it first
            return False
        return (dt_util.utcnow() - self._shown_at).total_seconds() > PRESS_TIMEOUT_SEC

    async def _async_press_expired(self, _now: datetime) -> None:
        """Nobody pressed anything for a minute and a half."""
        self._press_timer = None
        if self.ended or self._press is None:
            return
        self._overtake()
        self._press = None
        self._movement = None
        self._show_problem(REASON_TIMEOUT)

    async def _async_lease_expired(self, _now: datetime) -> None:
        """Give the shutter back: nobody has touched this session for a long time."""
        self._lease = None
        if self.ended:
            return
        LOGGER.warning(
            "Panel calibration of %s: nothing happened for a long time, so the shutter "
            "is being given back. Nothing was saved; start again to measure it",
            self.cover_name,
        )
        await self.async_end("expired", stop=True)

    # ---------------------------------------------------------- the shutter on its own
    @callback
    def _state_changed(self, event: Event[EventStateChangedData]) -> None:
        """What the shutter is doing, including what nobody asked it to do (SPEC §3.7)."""
        if self.ended:
            return
        new = event.data.get("new_state")
        old = event.data.get("old_state")
        if new is None:
            return
        moving = new.state in (STATE_OPENING, STATE_CLOSING)
        was_moving = old is not None and old.state in (STATE_OPENING, STATE_CLOSING)
        if moving:
            direction = DIRECTION_OPEN if new.state == STATE_OPENING else DIRECTION_CLOSE
            if self._movement is not None and self._movement.direction == direction:
                return  # ours
            self._external(direction)
            return
        if was_moving and self._press is not None and self._press.kind == "lift_off":
            # The shutter stopped before the press that measures the lift-off: what
            # that step was about did not happen.
            self._interrupt()

    @callback
    def _external(self, _direction: str) -> None:
        """A movement of somebody else's, answered by where the session stands."""
        state = self._screen().state
        self._external_move = True
        self._at = None
        if state in ("running", "positioning"):
            self._interrupt()
            return
        if state == "awaiting_reading" and self._step in (
            "measure_descent",
            "measure_ascent",
            "measure_verify",
        ):
            # The reading was taken where the shutter no longer is. The field stays on
            # the screen - the user may have measured before it was touched, and they
            # are the one who knows - but the way forward is the step again.
            self._show(self._step, notice="reading_stale")
            return
        # Outside a measurement this is not an interruption at all: lowering a shutter
        # with the wall switch while reading the instructions is an ordinary gesture.
        self._publish()

    @callback
    def _interrupt(self) -> None:
        """The step was measuring something that has just stopped being true."""
        self._overtake()
        self._movement = None
        self._press = None
        self._disarm_press()
        self._at = None
        self._show_problem(REASON_INTERRUPTED)

    # ------------------------------------------------------------------- the ending
    @callback
    def _overtake(self) -> None:
        """Nothing queued or in flight is about this session any more.

        Raising the counter makes a job already awaiting a primitive publish nothing
        when it comes back; emptying the queue makes one that has not started yet not
        write its frame at all. Both are needed: the first alone would let the shutter
        be sent off after the stop that was supposed to prevent it.
        """
        self._generation += 1
        self._queued = None

    async def async_end(self, reason: str, *, stop: bool = False) -> None:
        """Finish the session, with or without a stop, and publish what became of it.

        The stop is written by the two endings that happen *to* a session rather than
        being asked for - the lease running out and the entry being unloaded - because
        both of them leave nobody watching a shutter that may still be running (the
        dialog's `_async_stop_if_moving`, 0.5.0 final review RISK-C). `cancel` and
        `leave` write nothing: a free run is heading for an end stop, and stopping it
        would leave the curtain at an arbitrary point instead of a known one.
        """
        if self.ended:
            return
        self._generation += 1
        entity = _live_entity(self.hass, self.entry, self.cover_unique_id)
        if stop and entity is not None and (entity.is_opening or entity.is_closing):
            with contextlib.suppress(CalibrationError, HomeAssistantError):
                await entity.async_calib_stop()
        self._end(reason)

    @callback
    def _end(self, reason: str) -> None:
        """Reserve the gateway if a run is still going, then publish the ending."""
        if self.ended:
            return
        self._generation += 1
        entity = _live_entity(self.hass, self.entry, self.cover_unique_id)
        moving = bool(entity is not None and (entity.is_opening or entity.is_closing))
        if moving and self._movement is not None:
            # A free run that nobody stopped is heading for its end stop, and a new
            # measurement cannot begin into a curtain that is still travelling: the
            # *gateway* stays reserved until it gets there, although the shutter itself
            # is released at once (contract §2.1).
            self._reserved_until = dt_util.utcnow() + timedelta(
                seconds=self._full_run(self._movement.direction) + CALIBRATION_SETTLE_SEC
            )
        self._finish(reason)

    @callback
    def _finish(self, reason: str, extra: Mapping[str, Any] | None = None) -> None:
        """The terminal snapshot, and everything this session was holding, let go.

        Idempotent: a session ends once. Two endings that raced - a `cancel` arriving
        while a `save` was inside `async_write` - would otherwise leave the outcome of
        whichever finished last on a session the other had already released.
        """
        if self.ended:
            return
        self._disarm_lease()
        self._disarm_press()
        self._movement = None
        self._press = None
        self._queued = None
        self._owner = None
        self.ended = True
        self._ended_at = dt_util.utcnow()
        self._outcome = {
            "reason": reason,
            "profile": None,
            "origin": None,
            "source": None,
            **dict(extra or {}),
        }
        # The session is over: what the *screen* was saying goes with it. A terminal
        # snapshot has no step, so a problem code or a notice left on it would describe
        # a screen that is not there any more (the fixture's endings say `null` for all
        # three), and a position nobody is keeping up to date is worse than none.
        self._at = None
        self._problem = None
        self._notice = None
        self._form_error = None
        if reason != "saved":
            self._measured = measure.Measured()
            # ...and the two instants of the lift-off press, which live beside the
            # measurements rather than in them: `measured.lift` is built from them, so a
            # session emptied without them would answer a terminal snapshot carrying the
            # one provisional value it had kept - against `docs/panel-websocket-api.md`
            # §12.1, which says that `measured` is emptied once a session has ended
            # without saving.
            self._lift_off = None
            self._stop_delivered = None
            self._plan = []
            self._index = None
            self._result = None
            self._review = None
            self._check = None
        if self._watching is not None:
            self._watching()
            self._watching = None
        if self._claim is not None:
            self._claim.close()
            self._claim = None
        self._publish()
        # ...and the gateway's picture, because the shutter has just been given back:
        # `overview.measuring` and `overview.session` both change here, and a panel that
        # is not on the wizard learns it from nowhere else.
        self._publish_the_overview()

    # -------------------------------------------------------------------- the writing
    async def _async_store_the_result(self, store: CalibrationStore, target: str) -> dict[str, Any]:
        """What Save writes, and the only thing this session ever writes.

        Path A's main exit is the contract's first one (§2.7): the profile *and* the
        assignment, with no values of the cover's own - the ones it had are removed,
        because they would hide the profile that was just measured on it. The dialog
        still writes both, on purpose (SPEC §2.3): the two are meant to differ until
        the dialog goes.
        """
        result = self._result
        assert result is not None  # noqa: S101 - `save` refuses outside the review
        raw = {**measure.raw(path=self._path or PATH_FIRST, measured=self._measured),
               "client": "panel", "save_target": target}
        name = self._measured_name or self._profile
        if target == "profile" and result.profile is not None and name:
            await store.async_set_profile(
                name,
                cover_profile_data(
                    name,
                    reference_height=result.profile[CONF_REFERENCE_HEIGHT],
                    opening_time=result.profile[CONF_OPENING_TIME],
                    closing_time=result.profile[CONF_CLOSING_TIME],
                    slat_time=result.profile[CONF_SLAT_TIME],
                    opening_roll=result.profile[CONF_OPENING_ROLL],
                    closing_roll=result.profile[CONF_CLOSING_ROLL],
                    reference_cover=self.cover_name,
                    measured_on=self.cover_unique_id,
                    raw=raw,
                ),
            )
        record = store.calibration(self.cover_unique_id)
        overrides, height, profile_name, wins, source = self._record_to_write(record, target)
        await store.async_set_calibration(
            self.cover_unique_id,
            cover_calibration_data(
                self.cover_unique_id,
                profile=profile_name,
                profile_wins=wins,
                height=height,
                overrides=overrides or None,
                source=source,
                raw=raw,
            ),
        )
        return {}

    @callback
    def _record_to_write(
        self, record: StoredCalibration | None, target: str
    ) -> tuple[dict[str, float], float | None, str | None, bool, str]:
        """The record `save` writes, which is also the record the review resolves.

        One function for both, so the row that says "after" on the screen and the
        record that is written afterwards cannot come from two different rules.

        Path A's main exit is the contract's: the profile just measured, assigned and
        *winning*, with no values of the cover's own - the ones it had are taken away,
        because they would hide the very profile that was measured on it (contract
        §2.7, SPEC §3.9). "Salva solo per questa tapparella" writes those five values
        instead and leaves the assignment exactly as it found it: the path measured a
        window, it said nothing about which kind of shutter it is.
        """
        result = self._result
        assert result is not None  # noqa: S101 - `save` refuses outside the review
        name = self._measured_name or self._profile
        if target == "profile" and self._path == PATH_FIRST:
            return {}, self._measured.height, name, True, CALIBRATION_SOURCE_PROFILE
        overrides, height = measure.merged_with(record, result, measured=self._measured)
        if self._path == PATH_FIRST:
            profile_name = record.profile if record is not None else None
            wins = bool(record is not None and record.profile_wins)
        else:
            profile_name = self._profile
            wins = measure.profile_still_wins(
                record, result, path=self._path or PATH_FIRST, profile=self._profile
            )
        source = (
            CALIBRATION_SOURCE_PROFILE if result.follows_profile else CALIBRATION_SOURCE_GUIDED
        )
        return overrides, height, profile_name, wins, source

    # -------------------------------------------------------------------- the review
    @callback
    def _build_the_review(self) -> bool:
        """What the shutter uses today, what it would use after Save, and who else moves.

        The "after" is not a prediction: the record and the profile the write would
        produce are run through `resolve_cover`, the very function the cover platform
        reads its numbers with, so the row on the screen and the number the shutter
        will move on cannot come from two different rules.
        """
        path = self._path or PATH_FIRST
        try:
            self._result = measure.result(
                path=path,
                measured=self._measured,
                measured_name=self._measured_name,
                profile=self._profile,
                profiles=self.profiles,
                entity_id=self.entity_id,
                yaml_key=self._yaml_key,
                height_known=measure.known_height(
                    record=self._record(), device=self._device(), profiles=self.profiles
                ),
            )
        except CalibrationError as err:
            # The same guard as `_fits`, one level up: the summary cannot be built, so
            # it is not shown. `bad_point` is the dialog's own screen for a measurement
            # that cannot be made into a model, it offers "Ripeti questo passo", and
            # the way out of it is the ✕ like everywhere else.
            LOGGER.warning(
                "Panel calibration of %s: the summary cannot be computed (%s)",
                self.cover_name,
                err,
            )
            self._result = None
            self._review = None
            return False
        result = self._result
        variant = self._variant()
        targets = self._targets()
        name = self._measured_name if path == PATH_FIRST else self._profile
        # Only path A's main exit writes a profile, so only it changes what the windows
        # that follow that profile will do. Path B names a profile too and changes
        # nothing about it: taking this to mean "a profile is in play" would put a page
        # of followers on that screen whose "before" and "after" are the same number,
        # which reads as a warning about a change nobody is making.
        writing_profile = bool(
            targets[0] == "profile" and path == PATH_FIRST and result.profile is not None and name
        )
        profiles_after = dict(self.profiles)
        if writing_profile:
            shaped = profile_as_config(
                name,
                cover_profile_data(
                    name,
                    reference_height=result.profile[CONF_REFERENCE_HEIGHT],
                    opening_time=result.profile[CONF_OPENING_TIME],
                    closing_time=result.profile[CONF_CLOSING_TIME],
                    slat_time=result.profile[CONF_SLAT_TIME],
                    opening_roll=result.profile[CONF_OPENING_ROLL],
                    closing_roll=result.profile[CONF_CLOSING_ROLL],
                ),
            )
            if shaped is not None:
                profiles_after[name] = shaped
        record = self._record()
        before = self._resolved(record=record)
        after = self._resolved(record=self._hypothetical(record, targets[0]), profiles=profiles_after)
        replaced, kept = measure.replaced_and_kept(record, result, measured=self._measured)
        deviation = self._measured.deviation
        self._review = {
            "variant": variant,
            "targets": targets,
            "profile_name": name,
            "profile_exists": bool(name) and name in self.profiles,
            "name_clash": "file" if name and name in yaml_profiles(self.hass, self.entry) else None,
            "rows": _rows(before.values, after.values, SESSION_REVIEW_ROW_KEYS),
            "side_effects": _rows(
                before.values,
                after.values,
                tuple(key for key in SESSION_VALUE_KEYS if key not in SESSION_REVIEW_ROW_KEYS),
                only_changes=True,
            ),
            "affected": self._affected(profiles_after, name if writing_profile else None),
            "accuracy_cm": None if deviation is None else round(abs(deviation), 1),
            "check_fraction": self._measured.verify_fraction,
            "replacing": _in_contract_names(replaced),
            "keeping": _in_contract_names(kept),
            "yaml": result.yaml,
        }
        return True

    @callback
    def _variant(self) -> str:
        if self._measured.precise:
            return "precise"
        if self._path == PATH_FIRST:
            return "basic"
        if self._path == PATH_REFINE:
            return "correction"
        return "short"

    @callback
    def _targets(self) -> list[str]:
        """The exits of `save`, the first being the main one (L0 handoff, §3.4)."""
        if self._path == PATH_FIRST:
            return ["profile", "cover_only"]
        if self._path == PATH_PROFILE:
            return ["profile"]
        return ["cover_only"]

    @callback
    def _hypothetical(self, record: StoredCalibration | None, target: str) -> StoredCalibration:
        """The record `save` would write, as the resolution reads a record."""
        overrides, height, profile_name, wins, source = self._record_to_write(record, target)
        return StoredCalibration(
            cover_unique_id=self.cover_unique_id,
            profile=profile_name,
            profile_wins=wins,
            height=height,
            overrides=overrides,
            source=source,
        )

    @callback
    def _affected(
        self, profiles_after: Mapping[str, Mapping[str, Any]], name: str | None
    ) -> list[dict[str, Any]]:
        """Every *other* shutter that follows the profile about to be written over.

        Not truncated. The contract's first exit is "update the profile this cover
        follows", and what makes that acceptable is seeing, before writing, every
        window it reaches (docs §12.5).
        """
        if not name or name not in self.profiles:
            return []
        store = self._store()
        rows: list[dict[str, Any]] = []
        for unique_id, device in basic_covers(self.hass, self.entry).items():
            if unique_id == self.cover_unique_id:
                continue
            record = None if store is None else store.calibration(unique_id)
            follows = (record.profile if record is not None else None) or device.get(CONF_PROFILE)
            if follows != name:
                continue
            before = resolve_cover(device, profiles=dict(self.profiles), calibration=record)
            after = resolve_cover(device, profiles=dict(profiles_after), calibration=record)
            rows.append(
                {
                    "cover_unique_id": unique_id,
                    "name": str(device.get(CONF_NAME) or unique_id),
                    "rows": _rows(before.values, after.values, SESSION_REVIEW_ROW_KEYS),
                }
            )
        return rows

    # ------------------------------------------------------------------ the snapshot
    @callback
    def _show(self, step: str, *, error: str | None = None, notice: str | None = None) -> None:
        """Move to one screen and publish it. The only way a step ever changes."""
        self._step = step
        self._problem = None
        self._form_error = error
        self._notice = notice
        self._publish()

    @callback
    def _show_problem(self, reason: str) -> None:
        code = reason if reason in (*PROBLEM_REASONS, REASON_INTERRUPTED) else REASON_UNKNOWN
        self._step = f"problem_{code}"
        self._problem = code
        self._form_error = None
        self._notice = None
        self._publish()

    @callback
    def _publish(self) -> None:
        """The one door every transition goes through.

        It is the only thing that moves `revision`, and it rearms the lease - the same
        invariant the dialog gets by overriding `async_show_form`/`_menu`/`_progress`:
        a screen that forgot to restart the clock cannot be written, because there is
        no other way to put one in front of anybody.
        """
        self.revision += 1
        self._touch()
        snapshot = self.snapshot()
        for send in list(self._subscribers):
            send(snapshot)

    @callback
    def snapshot(self) -> dict[str, Any]:
        """Everything a client needs, whole, as `docs/panel-websocket-api.md` §12 says.

        A read: it computes, it never moves and it never arms anything.
        """
        terminal = self.ended
        saved = terminal and self._outcome_reason() == "saved"
        screen = self._screen()
        now = dt_util.utcnow()
        measured = self._measured
        return {
            "session_id": self.session_id,
            "entry_id": self.entry.entry_id,
            "revision": self.revision,
            "server_time": _at_second(now),
            "cover": {
                "unique_id": self.cover_unique_id,
                "entity_id": self.entity_id,
                "name": self.cover_name,
            },
            "state": ("saved" if saved else "ended") if terminal else screen.state,
            "substate": None if terminal else screen.substate,
            "step": None if terminal else self._step,
            "path": self._path,
            "scope": self._scope,
            "profile": self._profile,
            "level": "thorough" if measured.precise else "basic",
            "plan": list(self._plan),
            "plan_index": self._index,
            "intent": dict(self._intent) if self._intent else None,
            "actions": [] if terminal else self._actions(),
            "form": None if terminal else self._form(),
            "placeholders": {"cover": self.cover_name} if terminal else self._placeholders(),
            "movement": None if self._movement is None else self._movement.as_json(),
            "press": None if self._press is None else self._press.as_json(),
            "reading": None if terminal else self._reading(),
            "measured": self._measured_json(),
            "fit": _fit_json(self._fits(), measured),
            "check": dict(self._check) if self._check is not None else None,
            "review": dict(self._review) if self._review is not None else None,
            "problem": None if self._problem is None else {"code": self._problem},
            "notice": self._notice,
            "position_known": _as_position(self._at),
            "external_move": self._external_move,
            "owner": None
            if self._owner is None
            else {"client_id": self._owner, "present_until": _at_second(self.present_until)},
            "idle_expires_at": None if terminal else _at_second(self._lease_expires_at()),
            "outcome": dict(self._outcome) if self._outcome is not None else None,
        }

    @callback
    def _measured_json(self) -> dict[str, Any]:
        """What has been measured so far, under the names of the published contract.

        `lift` carries **both** instants the contract names (§2.1): when the press
        reached the backend, which is what the slat phase is measured from exactly as
        the dialog measures it, and when the stop frame it asked for was written, which
        is the far end of the distance the tape then measures. Nothing is derived from
        the second here; it is exposed so that the two definitions the contract allows
        are visible side by side (SPEC decision 12.9).
        """
        measured = self._measured
        lift = None
        if self._lift_off is not None or measured.lift_run_sec is not None:
            lift = {
                "pressed_at": _at_second(self._lift_off),
                "stop_written_at": _at_second(self._stop_delivered),
                "gap_cm": measured.lift_gap_cm,
                "late": measured.lift_late,
            }
        pressed_slat = measured.opening is not None or measured.slat_seconds is not None
        return {
            "travel_cm": measured.height,
            "travel_measured": measured.height_measured,
            "opening_time_s": measured.opening.run_time if measured.opening else None,
            "closing_time_s": measured.closing.run_time if measured.closing else None,
            "slat_time_s": measured.slat_time if pressed_slat else None,
            "lift": lift,
            "descent": [list(point) for point in measured.descent],
            "ascent": [list(point) for point in measured.ascent],
            "times_adopted": measured.times_adopted,
        }

    @callback
    def _fits(self) -> tuple[DirectionFit, DirectionFit] | None:
        """The fit of both directions, or None because it could not be made.

        The guard lot B1 asked for (handoff §6, R1(b)). `fit_from_run` raises
        `CalibrationError` for a reading the model cannot place - a fraction outside
        `(0, 1]`, a travel of nothing, a bar measured above the curtain - and this is
        called from `snapshot()`, which **every verb runs to answer**, `cancel`
        included. Letting it out would leave a session that can neither be read nor
        cancelled, holding a shutter until the lease ran out: the exact opposite of
        lesson 2. The screen then shows what it has, which is no fit.
        """
        try:
            return measure.fits(self._measured)
        except CalibrationError as err:
            LOGGER.warning(
                "Panel calibration of %s: the measurements do not make a model (%s)",
                self.cover_name,
                err,
            )
            return None

    @callback
    def _outcome_reason(self) -> str:
        return str((self._outcome or {}).get("reason") or "")

    @callback
    def _lease_expires_at(self) -> datetime | None:
        return self._lease_at

    # ---- the pieces of the snapshot
    @callback
    def _form(self) -> dict[str, Any] | None:
        field = self._screen().form
        if field is None:
            return None
        if field == CONF_HEIGHT:
            known = self._measured.height
            if known is None:
                known = measure.known_height(
                    record=self._record(), device=self._device(), profiles=self.profiles
                )
            return _form(
                field, "number", unit="cm",
                suggested=known if known is not None else FALLBACK_HEIGHT_CM,
                minimum=MIN_HEIGHT_CM, maximum=MAX_HEIGHT_CM, error=self._form_error,
            )
        if field == "gap_cm":
            return _form(
                field, "number", unit="cm", optional=True,
                minimum=0.0, maximum=MAX_GAP_CM, error=self._form_error,
            )
        if field == "measured_cm":
            return _form(
                field, "number", unit="cm", minimum=0.0,
                maximum=self._measured.height, error=self._form_error,
            )
        if field == CONF_NAME:
            return _form(
                field, "text",
                suggested=self._measured_name or measure.suggested_name(self.entity_id),
                error=self._form_error,
            )
        choices = sorted(self.profiles)
        return _form(
            field, "choice", suggested=self._preselected_profile(choices), choices=choices,
            error=self._form_error,
        )

    @callback
    def _preselected_profile(self, choices: Sequence[str]) -> str | None:
        """The profile the choice opens on, as the dialog's two forms default it.

        Path B has nothing to go on and opens on the first name (`async_step_path_b`,
        :1800); a correction opens on the one already chosen in this conversation, else
        the one this window follows today, else the first - because a form that opened
        on somebody else's profile for a window the file assigns would be telling the
        user something untrue about their own installation (`async_step_path_c`,
        :1833-1841).
        """
        chosen = self._profile
        if chosen is None and self._step == "path_c":
            chosen = measure.assigned_profile(record=self._record(), device=self._device())
        if chosen is not None and chosen in choices:
            return chosen
        return choices[0] if choices else None

    @callback
    def _reading(self) -> dict[str, Any] | None:
        """Where the model expects the bar, for the reading the screen is asking for.

        Only for a run to a fraction: the curtain travel and the lift-off gap are read
        with the shutter standing still and have nothing to be compared with.
        """
        if self._step not in ("measure_descent", "measure_ascent", "measure_verify"):
            return None
        direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
        expected, tolerance = self._expected()
        return {
            "direction": direction,
            "fraction": fraction,
            "from_end_stop": _as_position(_other_end(direction)),
            "expected_cm": expected,
            "tolerance_cm": tolerance,
        }

    @callback
    def _expected(self) -> tuple[float | None, float]:
        """`calibration_measure.expected_cm`, in numbers instead of rendered strings.

        The dialog's method answers the two strings its text substitutes; the panel is
        given the values and formats them itself, so the rule is applied here and the
        parity with the ported function is a test
        (`test_the_expected_reading_is_the_dialog_s_own`).
        """
        direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
        height = self._measured.height
        if not height:
            return None, ROUGH_TOLERANCE_CM
        try:
            model = measure.model_values(
                path=self._path or PATH_FIRST,
                measured=self._measured,
                profiles=self.profiles,
                profile=self._profile,
            )
        except CalibrationError as err:
            # Same guard again: the expectation under a field is a courtesy, and a
            # model that cannot be built simply means the wider tolerance.
            LOGGER.warning("Panel calibration of %s: %s", self.cover_name, err)
            model = None
        if model is not None:
            roll = model[CONF_CLOSING_ROLL if direction == DIRECTION_CLOSE else CONF_OPENING_ROLL]
            tolerance = EXPECTED_TOLERANCE_CM
        else:
            from .const import DEFAULT_ROLL_SHUTTER  # noqa: PLC0415 - one constant, one use

            roll = DEFAULT_ROLL_SHUTTER
            tolerance = ROUGH_TOLERANCE_CM
        return predict_cm(direction, roll, 1.0, fraction, height), tolerance

    @callback
    def _placeholders(self) -> dict[str, Any]:
        """The values the step's own sentences substitute, as raw numbers and strings.

        The dialog's placeholder names, because the sentences are the dialog's: these
        are the keys of texts already translated into seven languages. The panel
        formats them in the user's language, which is why nothing here is rounded or
        given a unit.
        """
        values: dict[str, Any] = {"cover": self.cover_name}
        measured = self._measured
        step = self._step
        if step == "tape_brief":
            values["readings"] = len(self._tape_phase())
        elif step in ("open_result", "open_result_gap"):
            opening = measured.opening
            values["slat"] = (opening.slat_time or 0.0) if opening else None
            values["run"] = opening.run_time if opening else None
            values["gap"] = measured.lift_gap_cm
        elif step == "close_result":
            values["run"] = measured.closing.run_time if measured.closing else None
        elif step == "height_result":
            values["height"] = measured.height
        elif step in ("measure_descent", "measure_ascent", "measure_verify"):
            direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
            expected, tolerance = self._expected()
            values.update(
                percent=round(fraction * 100),
                direction=direction,
                expected=expected,
                tolerance=tolerance,
            )
        elif step == "tape_result":
            _direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
            points = measured.descent if self._tape_target == "descent" else measured.ascent
            values["percent"] = round(fraction * 100)
            values["measured"] = points[-1][1] if points else None
        elif step == "verify_result":
            # The number the sentence substitutes is the number that *decided* whether
            # the correction is offered - rounded first, and zero when the model this
            # window follows went away under the conversation and there was nothing to
            # compare against. It is the dialog's own arithmetic for its own sentence
            # (:3018-3022); a check with nothing behind it says so in `check`, whose
            # three numbers are then `null`.
            values["deviation"] = self._deviation_shown()
        elif step == "profile_name":
            values["replaced"] = "yes" if self._measured_name in self.profiles else ""
        if self._movement is not None and self._movement.kind == "fraction":
            _direction, fraction = self._pending or (DIRECTION_CLOSE, HALF_RUN)
            values["percent"] = round(fraction * 100)
        return values


# ------------------------------------------------------------------- small helpers
def _a_name(name: str | None) -> bool:
    """A profile name the store will take, checked again at Save (docs §13)."""
    return bool(name) and bool(_NAME_RE.match(str(name))) and name != NO_PROFILE


def _form(
    field: str,
    kind: str,
    *,
    optional: bool = False,
    unit: str | None = None,
    suggested: Any = None,
    minimum: float | None = None,
    maximum: float | None = None,
    choices: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "field": field,
        "kind": kind,
        "optional": optional,
        "unit": unit,
        "suggested": suggested,
        "min": minimum,
        "max": maximum,
        "choices": choices,
        "error": error,
    }


def _fit_json(
    fitted: tuple[DirectionFit, DirectionFit] | None, measured: measure.Measured
) -> dict[str, Any] | None:
    """Both directions of the fit, with the residual of every reading it explains."""
    if fitted is None:
        return None
    down, up = fitted
    return {
        "opening": _direction_json(up, measured.ascent),
        "closing": _direction_json(down, measured.descent),
    }


def _direction_json(
    direction: DirectionFit, readings: Sequence[tuple[float, float]]
) -> dict[str, Any]:
    """One fitted direction, with its readings in the seconds they were measured in.

    `residual_cm` is `None` for a direction fitted through a single point: it is
    reproduced exactly by construction, so what is left over is zero and means nothing
    at all (the same reason the basic summary has no accuracy line).
    """
    residuals = direction.fit.residuals_cm
    single = direction.fit.points <= 1
    return {
        "run_time_s": direction.corrected_run_time,
        "slat_time_s": direction.slat_time,
        "roll": direction.fit.roll,
        "time_scale": direction.fit.time_scale,
        "points": [
            {
                "motor_s": motor_s,
                "measured_cm": measured_cm,
                "residual_cm": None
                if single or index >= len(residuals)
                else residuals[index],
            }
            for index, (motor_s, measured_cm) in enumerate(readings)
        ],
    }


def _rows(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    keys: Sequence[str],
    *,
    only_changes: bool = False,
) -> list[dict[str, Any]]:
    """One row per key, in the contract's names: what it is today, what it would be."""
    rows: list[dict[str, Any]] = []
    for name in keys:
        key = _in_store_name(name)
        was = before.get(key)
        now = after.get(key)
        if only_changes and was == now:
            continue
        rows.append({"key": name, "before": was, "after": now})
    return rows


_TO_STORE = {contract: store for store, contract in SESSION_BOUNDARY_NAMES.items()}


def _in_store_name(name: str) -> str:
    return _TO_STORE.get(name, name)


def _in_contract_names(keys: Sequence[str]) -> list[str]:
    """Store keys as the session names them, in the order the review rows have."""
    named = {SESSION_BOUNDARY_NAMES.get(key, key) for key in keys}
    ordered = [key for key in SESSION_VALUE_KEYS if key in named]
    return ordered + sorted(named - set(ordered))


__all__ = [
    "IMPLEMENTED_LEVELS",
    "IMPLEMENTED_PATHS",
    "PRESENCE_SEC",
    "SESSIONS_DATA_KEY",
    "TERMINAL_TTL",
    "CalibrationSession",
    "async_end_all",
    "async_start",
    "current",
]
