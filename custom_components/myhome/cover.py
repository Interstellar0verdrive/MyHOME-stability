"""Support for MyHOME covers (WHO 2 shutters, basic and advanced actuators).

Contract F: basic (non-advanced) actuators give no position feedback, they only
report "opening", "closing" and "stopped".  This module estimates the position from
the configured travel times, exposes it as `current_cover_position` (0 = closed,
100 = open), derives open/closed from it, implements `set_cover_position` with a
timed stop and restores the last position across restarts.  Such covers are flagged
`assumed_state`.

Two-phase travel model (0.4.0).  On a real roller shutter the motor run is not all
lift: starting from fully closed the first `slat_time` seconds only open the slats
("lamelle") while the curtain stays on the floor, and when closing the motor keeps
running for `slat_time` seconds after the curtain has touched the floor, to close
them again.  The model therefore splits every run into

* a **slat phase** of `slat_time` seconds, reported as `current_cover_tilt_position`
  (0 = slats closed, 100 = slats open), and
* a **curtain phase** of `opening_time - slat_time` (up) / `closing_time - slat_time`
  (down) seconds, reported as `current_cover_position` (0 = curtain on the floor,
  whatever the slats do, 100 = fully open).

The cover is *closed* only when the curtain is down **and** the slats are closed.
While the curtain is up the slats are necessarily open, so tilt is pinned to 100 and
tilt commands are no-ops.  `slat_time: 0` (the default) disables the whole thing and
reproduces the 0.3.x linear model exactly, tilt included (no tilt feature at all).

The slat phase is *timed* whenever `slat_time` is set, but it is only *exposed* as tilt
controls when `tilt: true` is written (0.4.2).  Most shutters cannot really be told to
hold their slats at 40 %, so the controls are opt-in; the timing model is not, because
a run from fully closed genuinely does spend `slat_time` on the slats before the
curtain leaves the floor, whether or not anybody can see it.

Roll model (0.4.2).  The curtain phase is not linear either: the curtain winds on a
tube, the motor turns at a constant speed, so the curtain moves fastest when it is up
(the roll is fat) and slowest when it is down.  `roll` = r_max / r_min describes that
in one number, and `_roll_tau` / `_roll_x` below are the whole of it; `roll: 1` gives
back the old linear model exactly, term for term.  A measured shutter turns out not to
behave the same way up and down (the motor is not equally loaded), so from 0.4.2 the
curtain phase carries one roll per direction: `closing_roll` for descents,
`opening_roll` for ascents, both defaulting to the common `roll`.

Advanced actuators report a real position through dimension 10; OWNd maps
`position == 0` to *closed* (`OWNAutomationEvent`), which matches the HA convention,
so their value is used verbatim.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from math import sqrt
from typing import Any

import voluptuous as vol
from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as PLATFORM,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
    CoverState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.restore_state import ExtraStoredData, RestoredExtraData, RestoreEntity
from homeassistant.util import dt as dt_util
from OWNd.message import (
    OWNAutomationCommand,
    OWNAutomationEvent,
)

from .const import (
    ATTR_CLOSED_HALF_CM,
    ATTR_CLOSED_RUN_SECONDS,
    ATTR_DIRECTION,
    ATTR_HEIGHT,
    ATTR_MOTOR_SECONDS,
    ATTR_OPENED_HALF_CM,
    ATTR_OPENED_RUN_SECONDS,
    CALIBRATION_DIRECTIONS,
    CONF_ADVANCED_SHUTTER,
    CONF_BUS_INTERFACE,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_MODEL,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
    CONF_HEIGHT,
    CONF_ICON,
    CONF_INVERTED,
    CONF_MANUFACTURER,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PLATFORMS,
    CONF_PROFILE,
    CONF_REFERENCE_HEIGHT,
    CONF_ROLL,
    CONF_SHUTTER_RUN,
    CONF_SLAT_TIME,
    CONF_TILT,
    CONF_WHERE,
    CONF_WHO,
    DEFAULT_ROLL,
    DEFAULT_SHUTTER_RUN,
    DEFAULT_SLAT_TIME,
    DEFAULT_TILT,
    DIRECTION_CLOSE,
    DOMAIN,
    LOGGER,
    MAX_ROLL,
    MIN_ROLL,
    ROLL_LINEAR_TOLERANCE,
    SERVICE_COVER_CALIBRATION_COMPUTE,
    SERVICE_COVER_CALIBRATION_RUN,
    bus_full_where,
)
from .gateway import MyHOMEGatewayHandler
from .myhome_device import MyHOMEEntity, address_attributes

# The gateway repeats our own commands back to us a moment later, and those repeats
# arrive as ordinary bus frames - they look exactly like somebody at the wall keypad.
# Only two shapes of repeat have ever been seen (MyHOMEServer1, 0.4.0):
#
#   * we tell the shutter to MOVE -> the gateway answers "stopped" first, and only
#     then the movement we asked for;
#   * we tell the shutter to STOP -> the gateway sends one more late copy of the
#     movement it was interrupting.
#
# So a frame is ignored as an echo only when it matches one of those two shapes and
# arrives within `STOP_ECHO_WINDOW_SEC` of our own command, and only once. Anything
# else is taken at face value. In particular a movement in a direction the gateway
# could not possibly be echoing - we stopped it while it was closing and it starts
# opening - is somebody at the keypad and is obeyed straight away.
#
# One case stays genuinely ambiguous: a keypad press in the *same* direction we have
# just stopped, inside the window. Nothing in the frame tells it apart from the echo,
# so we still ignore it, but we then ask the actuator what it is actually doing
# (`ECHO_RECHECK_DELAY_SEC`). If it really is running, its answer restarts the
# estimate a couple of seconds late - a small error instead of a position that would
# stay wrong until the next command.
STOP_ECHO_WINDOW_SEC = 1.5
# How long after an ignored movement frame the actuator is asked for its status.
# The answer can never be mistaken for an echo whatever this value is (`_is_echo`
# disarms the window before scheduling the re-check), so the number is only about
# usefulness: long enough for the gateway to have finished echoing our command and
# for a real movement to have made some progress worth asking about, short enough
# that the position is wrong for two seconds rather than until the next command.
ECHO_RECHECK_DELAY_SEC = 2.0
# An advanced actuator reports its own position, so no timer bounds its movement:
# if its "stopped" frame is lost the entity would read "Opening" for ever. This much
# on top of the longest configured run is when we stop waiting and ask the actuator
# what it is doing. Generous on purpose: an actuator that is genuinely still running
# answers with its direction, which re-arms the timer, so the only cost of
# overshooting is a stale "Opening" for that long.
#
# This is the one thing the timing keys (`shutter_run` / `opening_time` /
# `closing_time`) still do on an `advanced:` cover: they bound this timer, and
# nothing else. The position is always the actuator's own value, never an estimate,
# so a cover whose real run is longer than the default (`DEFAULT_SHUTTER_RUN` + 30 s)
# only needs them to keep the safety timer out of the way of its longest run.
ADVANCED_MOVE_MARGIN_SEC = 30.0
# When the bound expires the actuator is asked for its status *first*; the direction
# is dropped only if nothing answers within a grace period. Otherwise an actuator
# that is simply slower than the bound would leave "Opening" for a second or two in
# the middle of every long run - and, since an advanced cover is not `assumed_state`
# and is "closed" at position 0, would be published as *closed* while it is actually
# running up, firing every automation watching for it.
#
# That grace cannot be a fixed number of seconds. The status request travels the
# ordinary command path, and that path has a budget of its own: the command session
# may have to be re-opened first (`connect_timeout`, 10 s), the write and the ACK are
# allowed `command_timeout` (10 s by default, up to 60), and the whole thing gets one
# retry with a fresh session before the command is dropped. That is
# `MyHOMEGatewayHandler.command_budget` - 40 s with the defaults.
#
# Is a re-opened session really the case to size this on? Not certainly, but plausibly
# enough that the worst case is what counts. The command session is *shared by the
# whole gateway*, not held per entity: the sending worker closes it after a minute in
# which **nothing at all** was sent - by any entity, service call, discovery pass or
# watchdog probe - so "this cover has been quiet" proves nothing on its own. In a
# quiet house at three in the morning, which is exactly when a shutter runs on a
# schedule with nobody watching, the session usually is closed. And being wrong the
# cheap way costs a longer stale *Opening*, while being wrong the other way publishes
# a moving shutter as *closed* and wakes every automation watching for it.
#
# So the grace is the handler's own command budget plus the margin below (the answer
# still has to travel back and be dispatched once the gateway has ACKed it), read
# live, so it follows the option if the user changes it.
#
# It is a long wait - 42 s by default, against a default bound of 50 s - and it is
# meant to be: it is the price of never publishing a moving shutter as *closed*. A
# gateway that is dead rather than slow still ends the movement, one command budget
# after the bound instead of two seconds after it; and while it is dead the entity is
# unavailable anyway (the connection signal), so nobody is watching a stale direction.
#
# What the grace does *not* cover is a status request stuck behind a long queue: the
# queue's own bound is `command_ttl` (60 s by default), and holding *Opening* for
# that long after a lost frame is worse than the failure the bound exists for.
ADVANCED_PROBE_GRACE_MARGIN_SEC = 2.0
# How often the estimated position is pushed to Home Assistant while the cover moves.
POSITION_TICK = timedelta(seconds=1)
# A "stopped" frame during a free run *we* commanded is read as the physical end stop
# (which re-calibrates the estimate) once this fraction of the expected run has
# elapsed; earlier, it is taken for a real stop and the estimate is frozen.
END_STOP_MIN_FRACTION = 0.75

OPENING = "opening"
CLOSING = "closing"

# The curtain phase can never be zero: the validator keeps at least one second of it,
# this only protects the divisions against a hand-crafted device config.
MIN_CURTAIN_TIME = 0.001


# ------------------------------------------------------------------ the roll model
# `x` is the fraction of the CURTAIN travel measured from the top: x = 0 fully open,
# x = 1 curtain on the floor (so x = 1 - position/100).  `tau` is the fraction of the
# curtain time.  Descending from the top at constant motor speed, the curtain covers
# less and less distance per second as the roll on the tube gets thinner, and the two
# functions below are that relation and its inverse.  They are pure and total: the
# whole roll model of the integration is these eight lines.
def _roll_tau(roll: float, x: float) -> float:
    """Fraction of the curtain time needed to descend from the top to `x`."""
    x = min(1.0, max(0.0, x))
    k = max(MIN_ROLL, roll)
    if k - 1.0 <= ROLL_LINEAR_TOLERANCE:
        return x
    return (k - sqrt(k * k - (k * k - 1) * x)) / (k - 1)


def _roll_x(roll: float, tau: float) -> float:
    """Where the curtain is after descending from the top for `tau` of the curtain time."""
    tau = min(1.0, max(0.0, tau))
    k = max(MIN_ROLL, roll)
    if k - 1.0 <= ROLL_LINEAR_TOLERANCE:
        return tau
    return (k * k - (k - tau * (k - 1)) ** 2) / (k * k - 1)


def _clamped_roll(roll: float | None, fallback: float) -> float:
    """A roll inside the physical range, falling back when the key was not written.

    Contract A already guarantees both, but the entity is also constructible by hand
    (tests, a future config flow), and a roll below 1 makes `_roll_x` return a
    position outside [0, 100] rather than merely a wrong one.
    """
    if not roll:
        return fallback
    return min(MAX_ROLL, max(MIN_ROLL, float(roll)))


# ------------------------------------------------------------------ calibration
# Two service calls turn a tape measure into the pair of directional rolls:
# `cover_calibration_run` reproduces, on the real shutter, exactly the motor time a
# `set_cover_position: 50` would spend with the cover's current configuration and the
# old linear model, the user measures how far the bar ended from the floor, and
# `cover_calibration_compute` inverts the model to find the roll that predicts that
# measurement.  The run has to be a movement the *configuration* defines, not an
# arbitrary one: the compute step re-derives the same seconds from the same YAML, so
# the two services always talk about the same movement without passing anything but
# the measurement between them.
#
# `slat_time` is never solved for (0.4.2 amendment).  Both runs are a position-50, so
# they stop at the same point of the curtain's time axis whatever the slat time is, and
# the pair (roll, slat_time) is not identifiable from them: any slat time predicts the
# same two heights.  What the two measurements *do* carry is the up/down asymmetry of a
# real motor, so each run now solves its own direction's roll - two independent
# one-dimensional bisections, and one number per equation.
#
# How long the shutter is left to reach the far end before the measured run starts.
# The configured run is only an estimate, and an end stop reached a second early costs
# nothing, while starting the measured run before the curtain is really at the top
# invalidates the whole measurement.
CALIBRATION_SETTLE_SEC = 3.0
# 60 halvings take a [1, 5] bracket below floating point resolution; the loop is over
# in microseconds, so there is nothing to gain by stopping earlier.
CALIBRATION_BISECTION_STEPS = 60
# Below this difference the two directional rolls are written back as one `roll:` key.
# 0.1 is well inside what a tape measure can distinguish (on the reference shutter it is
# about 2 cm of bar), and two keys that say the same thing are two keys to keep in step.
CALIBRATION_SAME_ROLL_TOLERANCE = 0.1
# Name of the profile in the generated snippet when the entity has no object id yet.
CALIBRATION_FALLBACK_PROFILE = "standard"

CALIBRATION_RUN_SCHEMA = {
    vol.Required(ATTR_DIRECTION): vol.In(list(CALIBRATION_DIRECTIONS)),
}
CALIBRATION_COMPUTE_SCHEMA = {
    vol.Required(ATTR_HEIGHT): vol.All(vol.Coerce(float), vol.Range(min=0, min_included=False)),
    vol.Required(ATTR_CLOSED_HALF_CM): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional(ATTR_OPENED_HALF_CM): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional(CONF_SLAT_TIME): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional(ATTR_CLOSED_RUN_SECONDS): vol.All(vol.Coerce(float), vol.Range(min=0, min_included=False)),
    vol.Optional(ATTR_OPENED_RUN_SECONDS): vol.All(vol.Coerce(float), vol.Range(min=0, min_included=False)),
}


async def _async_sleep(seconds: float) -> None:
    """Wait, in a single place the tests can replace.

    Patching `asyncio.sleep` itself would reach every other coroutine in the process,
    including Home Assistant's own; the calibration is the only thing in this
    integration that really has to wait for a shutter to move.
    """
    await asyncio.sleep(seconds)


# The calibration runs one cover at a time, even when the service call targets
# several: the whole point is that somebody is standing in front of the shutter with a
# tape measure, and Home Assistant would otherwise run every targeted entity in
# parallel (`helpers.service.entity_service_call` gathers them).
_CALIBRATION_LOCK = asyncio.Lock()


def calibration_close_run_seconds(closing_time: float, slat_time: float) -> float:
    """Motor seconds a `set_cover_position: 50` spends closing from fully open.

    Closing starts with the curtain at the top and the slats already open, so every
    second of the run is curtain time and the slat phase - which only happens once the
    curtain is on the floor - is never reached.
    """
    return max(0.0, closing_time - slat_time) / 2


def calibration_open_run_seconds(opening_time: float, slat_time: float) -> float:
    """Motor seconds a `set_cover_position: 50` spends opening from fully closed.

    The mirror case is not symmetric: opening starts on the floor with the slats shut,
    so the first `slat_time` seconds only turn the slats and the curtain gets half of
    what is left.
    """
    return slat_time + max(0.0, opening_time - slat_time) / 2


def calibration_descent_cm(
    roll: float, slat: float, height: float, closing_time: float, run_seconds: float
) -> float:
    """Height of the bar after `run_seconds` of closing started from fully open.

    All of it is curtain time (the slats only close once the curtain has reached the
    floor), so the whole run is one descent along the roll model.
    """
    curtain = max(MIN_CURTAIN_TIME, closing_time - slat)
    return height * (1.0 - _roll_x(roll, min(1.0, run_seconds / curtain)))


def calibration_ascent_cm(
    roll: float, slat: float, height: float, opening_time: float, run_seconds: float
) -> float:
    """Height of the bar after `run_seconds` of opening started from fully closed.

    The first `slat` seconds only turn the slats, so the curtain rises for
    `run_seconds - slat` of the upward curtain time, and an ascent is the time reversal
    of a descent: a bar that is `tau_up` of the curtain time above the floor sits where
    a descent from the top would be after `1 - tau_up`.

    The roll here is the *opening* one, and the slat time is a known input rather than
    an unknown: with the run seconds the service itself uses, this equation and the
    descent one land on the same point of the curtain's time axis for every slat time,
    so the only thing that can make the two measured heights differ is the roll.
    """
    curtain = max(MIN_CURTAIN_TIME, opening_time - slat)
    moving = max(0.0, run_seconds - slat)
    return height * (1.0 - _roll_x(roll, 1.0 - min(1.0, moving / curtain)))


def _bisect_roll(predict: Callable[[float], float], target_cm: float) -> float | None:
    """The roll whose prediction is `target_cm`, or None when the range cannot reach it.

    Both `calibration_descent_cm` and `calibration_ascent_cm` fall as the roll grows (a
    fatter roll at the top means more curtain moved in the same time), so a plain
    bisection converges and the reachable band is simply the two ends of the range.
    """
    highest = predict(MIN_ROLL)
    lowest = predict(MAX_ROLL)
    if not lowest - 1e-9 <= target_cm <= highest + 1e-9:
        return None
    low, high = MIN_ROLL, MAX_ROLL
    for _ in range(CALIBRATION_BISECTION_STEPS):
        middle = (low + high) / 2
        if predict(middle) > target_cm:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def _unsolvable(
    field: str,
    measured_cm: float,
    run_seconds: float,
    run_word: str,
    time_key: str,
    full_seconds: float,
    start_word: str,
    lowest_cm: float,
    highest_cm: float,
) -> str:
    """Why no roll can have produced this measurement, and what to look at.

    The band is the whole of what the model can produce: the bar is highest with the
    smallest roll and lowest with the largest.  Quoting it is the only way the user can
    tell which of the numbers they gave is the wrong one - the measurement, the height,
    the run time or the end the run started from.
    """
    return (
        f"no roll matches {field}={measured_cm:.0f} cm: after {run_seconds:.1f} s of a "
        f"{full_seconds:.1f} s {run_word} run started fully {start_word}, the bar can only be "
        f"between {lowest_cm:.0f} cm and {highest_cm:.0f} cm from the floor. Check that the "
        f"height is the curtain travel and not the window, that the shutter really was fully "
        f"{start_word} when the run started, and that {time_key} and slat_time are the real "
        f"numbers of this cover"
    )


def solve_cover_calibration(
    height: float,
    opening_time: float,
    closing_time: float,
    closed_half_cm: float,
    *,
    closed_run_seconds: float,
    opened_run_seconds: float,
    slat_time: float,
    opened_half_cm: float | None = None,
) -> tuple[float, float | None]:
    """Recover (closing_roll, opening_roll) from one or two half-run measurements.

    Two independent one-dimensional problems, not one two-dimensional one: the closing
    run measures how the tube behaves on the way down and the opening run how it
    behaves on the way up, and neither says anything about the other.  The slat time is
    an input in both (see the section comment: it is not identifiable from these two
    runs, so it is taken from the stopwatch or from the configuration).

    Raises ``ValueError`` with an explanation when a measurement is outside everything
    the roll range can produce.
    """

    def descent(roll: float) -> float:
        return calibration_descent_cm(roll, slat_time, height, closing_time, closed_run_seconds)

    closing_roll = _bisect_roll(descent, closed_half_cm)
    if closing_roll is None:
        raise ValueError(
            _unsolvable(
                ATTR_CLOSED_HALF_CM,
                closed_half_cm,
                closed_run_seconds,
                "closing",
                CONF_CLOSING_TIME,
                closing_time,
                "open",
                descent(MAX_ROLL),
                descent(MIN_ROLL),
            )
        )
    if opened_half_cm is None:
        return closing_roll, None

    def ascent(roll: float) -> float:
        return calibration_ascent_cm(roll, slat_time, height, opening_time, opened_run_seconds)

    opening_roll = _bisect_roll(ascent, opened_half_cm)
    if opening_roll is None:
        raise ValueError(
            _unsolvable(
                ATTR_OPENED_HALF_CM,
                opened_half_cm,
                opened_run_seconds,
                "opening",
                CONF_OPENING_TIME,
                opening_time,
                "closed",
                ascent(MAX_ROLL),
                ascent(MIN_ROLL),
            )
        )
    return closing_roll, opening_roll


def calibration_yaml(
    name: str,
    height: float,
    opening_time: float,
    closing_time: float,
    slat_time: float,
    closing_roll: float,
    opening_roll: float | None = None,
) -> str:
    """The snippet to paste into ``myhome.yaml``: the profile, then the two cover lines.

    Two rolls that agree are written as the single ``roll:`` key they really are; two
    that differ are written separately and ``roll:`` is left out entirely, because a
    third number that neither run measured would only be one more thing to keep in step.
    """
    if opening_roll is None or abs(opening_roll - closing_roll) <= CALIBRATION_SAME_ROLL_TOLERANCE:
        common = closing_roll if opening_roll is None else (closing_roll + opening_roll) / 2
        rolls = f"    {CONF_ROLL}: {round(common, 2)}\n"
    else:
        rolls = (
            f"    {CONF_OPENING_ROLL}: {round(opening_roll, 2)}\n"
            f"    {CONF_CLOSING_ROLL}: {round(closing_roll, 2)}\n"
        )
    return (
        "cover_profiles:\n"
        f"  {name}:\n"
        f"    {CONF_REFERENCE_HEIGHT}: {round(height, 1)}\n"
        f"    {CONF_OPENING_TIME}: {round(opening_time, 1)}\n"
        f"    {CONF_CLOSING_TIME}: {round(closing_time, 1)}\n"
        f"    {CONF_SLAT_TIME}: {round(slat_time, 1)}\n"
        + rolls
        + "\n"
        "# on the cover itself:\n"
        f"    {CONF_PROFILE}: {name}\n"
        f"    {CONF_HEIGHT}: {round(height, 1)}\n"
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create the cover entities of this gateway (none when unconfigured)."""
    configured_covers = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS].get(PLATFORM, {})
    if not configured_covers:
        return

    gateway_handler = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_ENTITY]
    covers = [
        MyHOMECover(
            hass=hass,
            device_id=device_id,
            who=cfg[CONF_WHO],
            where=cfg[CONF_WHERE],
            interface=cfg.get(CONF_BUS_INTERFACE),
            name=cfg[CONF_NAME],
            entity_name=cfg[CONF_ENTITY_NAME],
            icon=cfg[CONF_ICON],
            device_class=cfg[CONF_DEVICE_CLASS],
            advanced=cfg[CONF_ADVANCED_SHUTTER],
            shutter_run=cfg[CONF_SHUTTER_RUN],
            slat_time=cfg.get(CONF_SLAT_TIME, DEFAULT_SLAT_TIME),
            opening_time=cfg.get(CONF_OPENING_TIME),
            closing_time=cfg.get(CONF_CLOSING_TIME),
            roll=cfg.get(CONF_ROLL, DEFAULT_ROLL),
            opening_roll=cfg.get(CONF_OPENING_ROLL),
            closing_roll=cfg.get(CONF_CLOSING_ROLL),
            tilt=cfg.get(CONF_TILT, DEFAULT_TILT),
            height=cfg.get(CONF_HEIGHT),
            profile=cfg.get(CONF_PROFILE),
            inverted=cfg[CONF_INVERTED],
            manufacturer=cfg[CONF_MANUFACTURER],
            model=cfg[CONF_DEVICE_MODEL],
            gateway=gateway_handler,
        )
        for device_id, cfg in configured_covers.items()
    ]

    platform = entity_platform.async_get_current_platform()
    # Both answer with data (`SupportsResponse.ONLY`): a calibration whose result is
    # only visible in the log would be useless from a script.
    platform.async_register_entity_service(
        SERVICE_COVER_CALIBRATION_RUN,
        CALIBRATION_RUN_SCHEMA,
        "async_calibration_run",
        supports_response=SupportsResponse.ONLY,
    )
    platform.async_register_entity_service(
        SERVICE_COVER_CALIBRATION_COMPUTE,
        CALIBRATION_COMPUTE_SCHEMA,
        "async_calibration_compute",
        supports_response=SupportsResponse.ONLY,
    )

    async_add_entities(covers)


class MyHOMECover(MyHOMEEntity, CoverEntity, RestoreEntity):
    """A WHO 2 shutter."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        entity_name: str | None,
        icon: str | None,
        device_id: str,
        who: str,
        where: str,
        interface: str | None,
        device_class: CoverDeviceClass | str | None,
        advanced: bool,
        shutter_run: float,
        inverted: bool,
        manufacturer: str | None,
        model: str | None,
        gateway: MyHOMEGatewayHandler,
        slat_time: float = DEFAULT_SLAT_TIME,
        opening_time: float | None = None,
        closing_time: float | None = None,
        roll: float = DEFAULT_ROLL,
        opening_roll: float | None = None,
        closing_roll: float | None = None,
        tilt: bool = DEFAULT_TILT,
        height: float | None = None,
        profile: str | None = None,
    ) -> None:
        super().__init__(
            hass=hass,
            name=name,
            platform=PLATFORM,
            device_id=device_id,
            who=who,
            where=where,
            manufacturer=manufacturer,
            model=model,
            gateway=gateway,
            entity_name=entity_name,
        )

        self._interface = interface
        # The interface must go on the bus unpadded (`11#4#3`): that is what the
        # F422 emits and what OWNd 0.7.49 parses back (0.3.1 / carferrer).
        self._full_where = bus_full_where(self._where, self._interface)

        try:
            self._attr_device_class = CoverDeviceClass(str(device_class).lower())
        except ValueError:
            self._attr_device_class = CoverDeviceClass.SHUTTER
        if icon is not None:
            self._attr_icon = icon

        self._advanced = bool(advanced)
        # Contract A guarantees a float >= 1; fall back to the schema default anyway.
        self._shutter_run = float(shutter_run or DEFAULT_SHUTTER_RUN)
        # Per-direction runs default to the common `shutter_run` (Contract A / 0.4.0).
        self._opening_time = float(opening_time or self._shutter_run)
        self._closing_time = float(closing_time or self._shutter_run)
        self._slat_time = max(0.0, float(slat_time or 0.0))
        # Contract A clamps it to [1, 5]; a hand-built entity might not.
        self._roll = _clamped_roll(roll, DEFAULT_ROLL)
        # A real shutter is not equally loaded in the two directions (the reference one
        # measures 1.6 down and 2.1 up), so the curtain phase carries one roll per
        # direction; both default to the common value (0.4.2 amendment).
        self._opening_roll = _clamped_roll(opening_roll, self._roll)
        self._closing_roll = _clamped_roll(closing_roll, self._roll)
        self._height = None if height is None else float(height)
        self._profile = profile
        # Curtain-only part of each run (the validator keeps it >= 1 s).
        self._curtain_up = max(MIN_CURTAIN_TIME, self._opening_time - self._slat_time)
        self._curtain_down = max(MIN_CURTAIN_TIME, self._closing_time - self._slat_time)
        self._inverted = bool(inverted)
        # The two-phase *timing* runs whenever a slat phase is configured on a basic
        # cover: opening from the floor really does spend `slat_time` on the slats
        # first, and pretending otherwise would put every later position out by that
        # much.  Whether the slats are also *exposed* as tilt controls is a separate,
        # opt-in question (`tilt:`, 0.4.2) - most actuators cannot hold them at 40 %.
        self._two_phase = not self._advanced and self._slat_time > 0
        self._has_tilt = bool(tilt) and self._two_phase

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        if self._has_tilt:
            self._attr_supported_features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.SET_TILT_POSITION
                | CoverEntityFeature.STOP_TILT
            )
        # Basic actuators never report their position: everything below the
        # `_estimate` line is an assumption (Contract F).
        self._attr_assumed_state = not self._advanced

        self._attr_extra_state_attributes = address_attributes(where, self._interface)
        if not self._advanced:
            # The whole model a basic cover's position comes from, in the order it is
            # read.  `Shutter run` is gone (0.4.2): it was always the same number as
            # `Opening time`, which is now always published.
            self._attr_extra_state_attributes["Opening time"] = self._opening_time
            self._attr_extra_state_attributes["Closing time"] = self._closing_time
            if self._slat_time > 0:
                self._attr_extra_state_attributes["Slat time"] = self._slat_time
            if self._opening_roll == self._closing_roll:
                # One number describes both runs: publishing two identical ones would
                # only invite the reader to look for a difference that is not there.
                self._attr_extra_state_attributes["Roll"] = self._opening_roll
            else:
                self._attr_extra_state_attributes["Opening roll"] = self._opening_roll
                self._attr_extra_state_attributes["Closing roll"] = self._closing_roll
            # These two say nothing about the movement, they say where the numbers
            # above came from - so they only appear when the file really has them.
            if self._height is not None:
                self._attr_extra_state_attributes["Height"] = self._height
            if self._profile is not None:
                self._attr_extra_state_attributes["Profile"] = self._profile

        self._attr_current_cover_position: int | None = None
        self._attr_current_cover_tilt_position: int | None = None
        self._attr_is_closed: bool | None = None

        # Movement bookkeeping for the time-based estimate.
        self._moving: str | None = None
        self._move_started_at: datetime | None = None
        self._move_start_position: int | None = None
        self._move_start_tilt: int | None = None
        # Set only when *we* have to stop the cover (`set_cover_position`, tilt).
        self._target_position: int | None = None
        # The last command *we* sent (OPENING / CLOSING / None = stop) and when: the
        # gateway echoes a "stopped" frame right before the "opening"/"closing" one,
        # and a late copy of the movement after our stop; both must be ignored
        # (see `_is_echo`).
        self._own_command_at: datetime | None = None
        self._own_command: str | None = None
        # Which movement our own stop interrupted: only *that* direction can come
        # back as a late echo, everything else is a real event.
        self._stopped_direction: str | None = None
        # True while a free run to an end stop that we commanded is in progress.
        self._own_free_run = False
        # True while a *continued* free run is inside the echo window it inherited
        # from the movement command that began it (see `_continue_to_end_stop`): the
        # one situation in which an ignored "stopped" frame may have been real.
        self._echo_after_restart = False
        self._move_duration: float | None = None
        # Where the estimate settles when the pending timer fires.
        self._end_position: int | None = None
        self._end_tilt: int | None = None
        self._stop_timer = None
        self._tick_unsub = None
        # One-shot status re-request after an ignored movement frame (see `_is_echo`).
        self._echo_recheck = None
        # Upper bound on how long an advanced actuator may report a direction. The
        # timing keys are used for this and for nothing else on an advanced cover
        # (see `ADVANCED_MOVE_MARGIN_SEC`): they never produce a position.
        self._advanced_move_timeout = max(self._opening_time, self._closing_time) + ADVANCED_MOVE_MARGIN_SEC
        self._advanced_timer = None
        # True between the safety timer's status request and its answer (or the end
        # of the grace): see `_async_advanced_movement_timeout`.
        self._advanced_probe_pending = False

    @property
    def _advanced_probe_grace(self) -> float:
        """How long the safety timer waits for the actuator's answer, in seconds.

        Read from the handler on every use rather than stored: it is the command
        path's own worst case for one request (`command_budget`: a session to open,
        a write to ACK, and one retry of both) plus a margin, so it must move with
        the option the user tunes (see `ADVANCED_PROBE_GRACE_MARGIN_SEC`).
        """
        return float(self._gateway_handler.command_budget) + ADVANCED_PROBE_GRACE_MARGIN_SEC

    # ------------------------------------------------------------------ state
    @property
    def current_cover_position(self) -> int | None:
        """Position of the *curtain* (0 = on the floor, 100 = fully open).

        Advanced actuators report it; for basic ones it is extrapolated from the
        movement start time and the configured travel times.
        """
        if self._advanced:
            return self._attr_current_cover_position
        return self._estimate()[0]

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Openness of the slats (0 = closed, 100 = open), or None without `slat_time`."""
        if not self._has_tilt:
            return None
        return self._estimate()[1]

    @property
    def is_opening(self) -> bool | None:
        """True while the cover is known to be opening."""
        return self._moving == OPENING

    @property
    def is_closing(self) -> bool | None:
        """True while the cover is known to be closing."""
        return self._moving == CLOSING

    @property
    def is_closed(self) -> bool | None:
        """Closed when the curtain is down *and* the slats are closed (plat-07)."""
        position = self.current_cover_position
        if position is None:
            return self._attr_is_closed
        if position != 0:
            return False
        if not self._has_tilt:
            return True
        tilt = self.current_cover_tilt_position
        return True if tilt is None else tilt == 0

    # ------------------------------------------------------------------ travel model
    def _normalise(self, position: float, tilt: float) -> tuple[int, int]:
        """Clamp a (position, tilt) pair to the states the shutter can physically be in.

        The slats can only be closed while the curtain rests on the floor, so any
        position above 0 implies fully open slats; without a slat phase the tilt
        simply follows the position (0/100) and is never published.
        """
        clamped = int(max(0, min(100, round(position))))
        if clamped > 0:
            return clamped, 100
        if not self._two_phase:
            return 0, 0
        # `_two_phase`, not `_has_tilt`: a cover with `tilt: false` still tracks where
        # the slats are, it just never publishes it.  Forgetting it here would make
        # every stop inside the slat phase cost a full `slat_time` again on the next
        # command.
        return 0, int(max(0, min(100, round(tilt))))

    def _curtain_tau(self, position: float, roll: float) -> float:
        """Where `position` sits on the curtain's time axis (0 at the top, 1 on the floor).

        The axis belongs to the *direction*: a descent and an ascent of the same shutter
        have their own roll, so the same position is a different fraction of each run.
        """
        return _roll_tau(roll, 1.0 - position / 100)

    def _curtain_position(self, tau: float, roll: float) -> float:
        """The curtain position (0-100) reached at time fraction `tau` of that run."""
        return (1.0 - _roll_x(roll, tau)) * 100

    def _travel(self, direction: str, position: int, tilt: int, elapsed: float) -> tuple[int, int]:
        """State reached `elapsed` seconds after leaving (`position`, `tilt`).

        The curtain part goes through the roll model: the run is converted to a
        position on the curtain's *time* axis, moved along it by the elapsed fraction
        of the run, and converted back.  Each direction uses its own roll (0.4.2
        amendment) and therefore its own time axis; within one run the conversion out
        and back is the same function, so nothing drifts.  The slat phase is unchanged:
        those seconds turn the slats, they wind nothing on the tube, so they stay
        linear.
        """
        slat = self._slat_time
        if direction == OPENING:
            if position <= 0 and slat > 0 and tilt < 100:
                # Slat phase first: the curtain does not move until the slats are open.
                slat_left = (100 - tilt) / 100 * slat
                if elapsed <= slat_left:
                    return self._normalise(0, tilt + elapsed / slat * 100)
                elapsed -= slat_left
            roll = self._opening_roll
            tau = self._curtain_tau(position, roll) - elapsed / self._curtain_up
            return self._normalise(self._curtain_position(tau, roll), 100)
        roll = self._closing_roll
        # Time still to run before the curtain touches the floor (tau = 1).
        curtain_left = (1.0 - self._curtain_tau(position, roll)) * self._curtain_down
        if elapsed < curtain_left:
            tau = self._curtain_tau(position, roll) + elapsed / self._curtain_down
            return self._normalise(self._curtain_position(tau, roll), 100)
        # The curtain is on the floor: the rest of the run closes the slats.
        elapsed -= curtain_left
        if slat <= 0:
            return self._normalise(0, 0)
        start_tilt = 100 if position > 0 else tilt
        return self._normalise(0, start_tilt - elapsed / slat * 100)

    def _travel_time(
        self,
        direction: str,
        position: int,
        tilt: int,
        target_position: int,
        target_tilt: int,
    ) -> float:
        """Seconds the motor must run to go from (`position`, `tilt`) to the target.

        The exact inverse of `_travel`: the curtain leg is the distance between the two
        positions measured on the curtain's time axis of *that direction* (which is what
        the roll model makes linear), the slat leg is unchanged.
        """
        slat = self._slat_time
        if direction == OPENING:
            seconds = 0.0
            if position <= 0 and slat > 0:
                # Opening past the floor always ends with the slats fully open.
                slat_target = 100 if target_position > 0 else target_tilt
                seconds += max(0.0, slat_target - tilt) / 100 * slat
            roll = self._opening_roll
            curtain = max(
                0.0, self._curtain_tau(position, roll) - self._curtain_tau(target_position, roll)
            )
            return seconds + curtain * self._curtain_up
        roll = self._closing_roll
        curtain = max(0.0, self._curtain_tau(target_position, roll) - self._curtain_tau(position, roll))
        seconds = curtain * self._curtain_down
        if target_position <= 0 and slat > 0:
            start_tilt = 100 if position > 0 else tilt
            seconds += max(0.0, start_tilt - target_tilt) / 100 * slat
        return seconds

    def _estimate(self) -> tuple[int | None, int | None]:
        """Current (position, tilt), extrapolated from the running movement."""
        if (
            self._moving is None
            or self._move_started_at is None
            or self._move_start_position is None
            or self._move_start_tilt is None
        ):
            return self._attr_current_cover_position, self._attr_current_cover_tilt_position
        elapsed = (dt_util.utcnow() - self._move_started_at).total_seconds()
        return self._travel(self._moving, self._move_start_position, self._move_start_tilt, elapsed)

    # ------------------------------------------------------------------ movement
    @callback
    def _cancel_timers(self) -> None:
        """Cancel the auto-stop, the position ticker and the two safety timers."""
        if self._stop_timer is not None:
            self._stop_timer()
            self._stop_timer = None
        if self._tick_unsub is not None:
            self._tick_unsub()
            self._tick_unsub = None
        self._cancel_echo_recheck()
        self._cancel_advanced_timer()

    @callback
    def _cancel_echo_recheck(self) -> None:
        """Drop the pending "was that frame real?" status request, if any."""
        if self._echo_recheck is not None:
            self._echo_recheck()
            self._echo_recheck = None

    @callback
    def _cancel_advanced_timer(self) -> None:
        """Drop the pending advanced-movement safety timer (and its grace), if any."""
        if self._advanced_timer is not None:
            self._advanced_timer()
            self._advanced_timer = None
        # Both routes an actuator frame can take reach this method before anything
        # else: a frame carrying a position through `_finish_movement` (which calls
        # `_cancel_timers`), a plain direction frame through
        # `_set_advanced_direction`. So an answer to the safety timer's status
        # request always clears the flag below, whatever the answer says - including
        # the commonest one of all, "stopped at N %", which never reaches
        # `_set_advanced_direction` at all.
        self._advanced_probe_pending = False

    @callback
    def _start_movement(
        self,
        direction: str,
        target_position: int | None = None,
        target_tilt: int | None = None,
        own_command: bool = False,
    ) -> None:
        """Start (or restart) the time-based estimate in `direction`.

        `own_command` marks movements we commanded (as opposed to keypad
        presses seen on the bus) so the gateway's stop echo can be ignored.

        `target_position` is set only when the movement must be stopped by us
        (`set_cover_position`, `set_cover_tilt_position`); otherwise the actuator
        stops at the end of its run and we only time the estimate.
        """
        position, tilt = self._estimate()
        self._cancel_timers()
        if position is None:
            # Nothing known yet: assume the opposite end so that a full travel
            # settles on the correct position.
            position, tilt = (0, 0) if direction == OPENING else (100, 100)
        if tilt is None:  # pragma: no cover - unreachable: only a cover without
            # `slat_time` can have a position and no tilt, and such a cover never
            # reports one (`current_cover_tilt_position`, `_attr_is_closed`).
            tilt = 100 if position > 0 else 0
        position, tilt = self._normalise(position, tilt)

        self._move_start_position = position
        self._move_start_tilt = tilt
        self._move_started_at = dt_util.utcnow()
        self._moving = direction
        self._target_position = target_position
        if own_command:
            self._own_command_at = dt_util.utcnow()
            self._own_command = direction
        else:
            self._own_command_at = None
            self._own_command = None
        self._stopped_direction = None
        self._own_free_run = own_command and target_position is None
        # A fresh movement is not a continued one; `_continue_to_end_stop` sets the
        # flag again after it has called us.
        self._echo_after_restart = False

        if target_position is None:
            # Free run to the end stop: fully open (slats open) or fully closed.
            end_position, end_tilt = (100, 100) if direction == OPENING else (0, 0)
        else:
            end_position = target_position
            end_tilt = 100 if target_tilt is None else target_tilt
        self._end_position, self._end_tilt = self._normalise(end_position, end_tilt)

        duration = self._travel_time(direction, position, tilt, self._end_position, self._end_tilt)
        self._move_duration = duration
        if duration <= 0:
            self._finish_movement(self._end_position, self._end_tilt)
            return

        self._stop_timer = async_call_later(self.hass, duration, self._async_movement_deadline)
        self._tick_unsub = async_track_time_interval(self.hass, self._async_position_tick, POSITION_TICK)

    @callback
    def _finish_movement(self, position: int | None, tilt: int | None = None) -> None:
        """Stop estimating and freeze the position (and the slats)."""
        self._cancel_timers()
        self._moving = None
        self._move_started_at = None
        self._move_start_position = None
        self._move_start_tilt = None
        self._target_position = None
        self._end_position = None
        self._end_tilt = None
        self._own_free_run = False
        self._echo_after_restart = False
        self._move_duration = None
        if position is not None:
            frozen_position, frozen_tilt = self._normalise(position, 100 if tilt is None else tilt)
            self._attr_current_cover_position = frozen_position
            self._attr_current_cover_tilt_position = frozen_tilt
            self._attr_is_closed = frozen_position == 0 and (not self._has_tilt or frozen_tilt == 0)

    @callback
    def _async_position_tick(self, now: datetime) -> None:
        """Push the estimated position to HA while the cover moves."""
        self.async_write_ha_state()

    async def _async_movement_deadline(self, now: datetime) -> None:
        """The cover reached its target (or the end of its run).

        A free run needs no command: the actuator stops by itself at the end stop,
        and all we do is settle the estimate there. A timed run (`set_cover_position`
        or a tilt) has to be stopped by us, and the command path can refuse to take
        that command (its queue is full, or the connection is closing) - in which
        case the shutter does *not* stop and the run turns into a free one, see
        `_continue_to_end_stop`.
        """
        self._stop_timer = None
        needs_stop = self._target_position is not None
        end_position, end_tilt = self._end_position, self._end_tilt
        # Read before `_finish_movement` clears it: `_mark_own_stop` needs to know
        # which movement this stop interrupts.
        interrupted = self._moving
        if not needs_stop:
            self._finish_movement(end_position, end_tilt)
        elif await self._gateway_handler.send(OWNAutomationCommand.stop_shutter(self._full_where)):
            self._finish_movement(end_position, end_tilt)
            # The gateway only echoes what it was actually given, so a stop that
            # never left the queue must not arm the window: it could then only
            # swallow a real frame from somebody else.
            self._mark_own_stop(interrupted)
        else:
            self._continue_to_end_stop()
        self.async_write_ha_state()

    @callback
    def _continue_to_end_stop(self) -> None:
        """Turn a timed run whose stop was refused into a free run to the end stop.

        The command never reached the bus, so the shutter is still running and will
        only stop when it hits the end of its travel. Settling the estimate on the
        target would freeze it on a position the cover never reached and leave it
        there for good - the actuator's own `stopped` frame at the end of the
        physical run would then simply re-freeze the same stale value. So the
        estimate keeps running instead, now towards the end stop, and that final
        frame re-calibrates it (`_reached_end_stop`), exactly as it does for an
        `open_cover` / `close_cover` we sent ourselves.

        Same rule as `async_stop_cover`: a stop the command path could not even take
        changes nothing about the movement that is still going on.
        """
        direction = self._moving
        if direction is None:  # pragma: no cover - the deadline only fires while moving
            return
        LOGGER.debug(
            "%s Cover %s: the stop that should have ended this run was refused; "
            "the shutter runs on to its end stop",
            self._gateway_handler.log_id,
            self._where,
        )
        # No `own_command`: we sent nothing just now, so there is no *new* echo to
        # expect and no window to arm. But the movement command that started this run
        # may still be inside its own window, and `_start_movement` clears that
        # bookkeeping - so save it across the restart and put it back. Otherwise the
        # gateway's late "stopped" copy of the command we sent when the run began is
        # taken for a real stop and ends the run, which is exactly the failure this
        # method exists to prevent. It only bites when the whole timed run is shorter
        # than the echo window (1.5 s) - an ordinary case: a 40 % tilt on a 3 s slat
        # time, or a slider nudge of a couple of percent.
        # The restart is seamless - `_start_movement` picks the current estimate up as
        # its starting point.
        own_command_at, own_command = self._own_command_at, self._own_command
        self._start_movement(direction)
        self._own_command_at, self._own_command = own_command_at, own_command
        # Set *after* the restart, which clears it. It marks the residual slice of
        # that inherited window as the one place where an ignored "stopped" frame may
        # have been a real stop - somebody at the keypad, or the actuator hitting an
        # obstacle - rather than the gateway's echo. Nothing in the frame tells the
        # two apart, so `_is_echo` still ignores it and asks the actuator instead
        # (`_schedule_echo_recheck`); without this flag the frame was swallowed with
        # no follow-up at all and the estimate ran on to the end stop while the
        # shutter stood still.
        self._echo_after_restart = own_command_at is not None
        # `_stopped_direction` stays None: we stopped nothing, so no movement frame
        # may be swallowed as the echo of a stop.
        # The movement itself is still the one *we* commanded, and it now ends where
        # the motor ends it: that is what makes the actuator's `stopped` frame at the
        # end count as the end stop instead of a stop half way.
        self._own_free_run = True

    @callback
    def _mark_own_stop(self, interrupted: str | None) -> None:
        """Remember that *we* just sent a stop, and which movement it interrupted.

        Only a late copy of `interrupted` can be the gateway echoing that stop back
        at us; a frame in the other direction is somebody at the keypad.
        """
        self._own_command_at = dt_util.utcnow()
        self._own_command = None
        self._stopped_direction = interrupted

    def _is_echo(self, frame_direction: str | None) -> bool:
        """True for a frame that can only be the gateway repeating our own command.

        Exactly two shapes qualify (see `STOP_ECHO_WINDOW_SEC`): the "stopped" frame
        that follows a movement *we* commanded, and a late copy of the movement our
        own stop interrupted. Each is ignored once. Every other frame - a stop we did
        not command, a movement in a direction we were not running - is a real event.
        """
        if self._own_command_at is None:
            return False
        recheck = False
        if self._own_command is not None:
            # We commanded a movement: only a "stopped" frame can be its echo.
            if frame_direction is not None:
                return False
            # During a *continued* run this window was inherited, not just armed: the
            # echo it was waiting for may already have gone by, and this frame may be
            # a real stop. Ask the actuator, exactly as for the ambiguous keypad press
            # below. Outside that case the window was armed a fraction of a second
            # ago by our own movement command, and the "stopped" frame that follows it
            # is the gateway's, so there is nothing to re-read.
            recheck = self._echo_after_restart
        else:
            # We commanded a stop: only the direction it interrupted can be echoed.
            if frame_direction is None or frame_direction != self._stopped_direction:
                return False
            recheck = True
        elapsed = (dt_util.utcnow() - self._own_command_at).total_seconds()
        if elapsed >= STOP_ECHO_WINDOW_SEC:
            return False
        LOGGER.debug(
            "%s Cover %s: ignoring the gateway echo (%s) %.2fs after our command",
            self._gateway_handler.log_id,
            self._where,
            frame_direction or "stopped",
            elapsed,
        )
        self._own_command_at = None
        if recheck:
            # It could just as well have been somebody pressing the same direction
            # again on the keypad, and nothing in the frame says which: ask the
            # actuator itself instead of silently losing the movement.
            self._schedule_echo_recheck()
        return True

    @callback
    def _schedule_echo_recheck(self) -> None:
        """Ask the actuator what it is really doing, once the echo window is over."""
        self._cancel_echo_recheck()
        self._echo_recheck = async_call_later(self.hass, ECHO_RECHECK_DELAY_SEC, self._async_echo_recheck)

    async def _async_echo_recheck(self, now: datetime) -> None:
        """The ignored movement frame may have been real: re-read the actuator status."""
        self._echo_recheck = None
        # A later frame already started the estimate: nothing was lost, so skip the
        # re-read. No test can reach this on HA 2026.9: `async_call_later` hands the
        # job to `create_eager_task`, so this coroutine runs *inside* the timer
        # callback and finishes without ever suspending (nothing on the way to
        # `send_status_request` awaits anything real). There is therefore no window
        # in which a bus frame could set `_moving` between the timer firing and this
        # line. The guard stays because that is a detail of how HA schedules jobs,
        # not a promise; it is excluded from coverage rather than chased.
        #
        # A continued free run is the exception, and the reason for the second half of
        # the condition: there the estimate is *deliberately* still running while we
        # ask, because the whole question is whether the shutter is still running with
        # it. The answer costs one status request and can only help - it either
        # confirms the direction or delivers a real stop.
        if self._moving is not None and not self._echo_after_restart:  # pragma: no cover - unreachable, see above
            return
        LOGGER.debug(
            "%s Cover %s: re-reading the status after an ignored movement frame",
            self._gateway_handler.log_id,
            self._where,
        )
        await self.async_update()

    @callback
    def _set_advanced_direction(self, direction: str | None) -> None:
        """Track an advanced actuator's direction, and bound how long it may last.

        Nothing times an advanced actuator (its position comes from its own status
        frames), so a lost "stopped" frame would leave the entity reading "Opening"
        for ever. The timer below is the only thing that ends such a movement, and
        the configured travel times are used here - and only here - to size it.
        """
        self._moving = direction
        self._cancel_advanced_timer()
        if direction is not None:
            self._advanced_timer = async_call_later(
                self.hass, self._advanced_move_timeout, self._async_advanced_movement_timeout
            )

    async def _async_advanced_movement_timeout(self, now: datetime) -> None:
        """The actuator never said it stopped: ask it, and only then give up on it.

        The direction is *not* cleared here. An actuator whose real run is longer
        than the bound is still moving, and publishing "not moving" in the middle of
        it would flip the entity to *Closed* / *Open* for as long as the answer
        takes (see `ADVANCED_PROBE_GRACE_MARGIN_SEC`). So the status is re-read
        first. Whatever comes back cancels the grace below - through
        `_cancel_advanced_timer`, which `_finish_movement` reaches for the commonest
        answer of all, "stopped at N %", and `_set_advanced_direction` reaches for a
        plain direction frame - and a "still running" answer re-arms the full bound.
        """
        self._advanced_timer = None
        # Same unreachable-guard as in `_async_echo_recheck`: the only thing that
        # clears `_moving` also cancels this timer, and the eager job start leaves no
        # window between the two. Kept for safety, excluded from coverage.
        if self._moving is None:  # pragma: no cover - unreachable: eager tasks, see `_async_echo_recheck`
            return
        LOGGER.debug(
            "%s Cover %s: no stop reported %.0fs after the movement started; re-reading the status",
            self._gateway_handler.log_id,
            self._where,
            self._advanced_move_timeout,
        )
        self._advanced_probe_pending = True
        # Armed before the request goes out so the ordering stays correct if
        # `send_status_request` ever becomes genuinely awaiting; today it only puts
        # the command on the queue and never suspends, so no frame can arrive in
        # between and there is no race to lose.
        self._advanced_timer = async_call_later(
            self.hass, self._advanced_probe_grace, self._async_advanced_probe_grace
        )
        await self.async_update()

    @callback
    def _async_advanced_probe_grace(self, now: datetime) -> None:
        """Nothing answered the safety timer's status request: drop the direction.

        This is the lost-"stopped"-frame case the bound exists for. The position is
        left alone - it is the actuator's own last value, never an estimate.
        """
        self._advanced_timer = None
        # And again: any answer to the status re-read goes through
        # `_cancel_advanced_timer`, which clears the flag *and* cancels this grace, so
        # neither half of the condition can be true when it fires. Excluded from
        # coverage for the same reason as the two guards above.
        if not self._advanced_probe_pending or self._moving is None:  # pragma: no cover - unreachable, see above
            return
        self._advanced_probe_pending = False
        LOGGER.debug(
            "%s Cover %s: no answer to the status re-read either; the movement is over as far as we know",
            self._gateway_handler.log_id,
            self._where,
        )
        self._moving = None
        self.async_write_ha_state()

    # ------------------------------------------------------------------ lifecycle
    @property
    def extra_restore_state_data(self) -> ExtraStoredData | None:
        """Persist the estimated position and tilt independently of the entity state.

        When the config entry is unloaded the gateway connection is closed first,
        so the entity is already ``unavailable`` (no attributes) by the time Home
        Assistant snapshots its state for restoration. Extra data survives that.
        """
        if self._advanced:
            return None
        # `_estimate`, not the two properties: a cover with `tilt: false` publishes no
        # tilt at all (`current_cover_tilt_position` is None there) but still tracks
        # where its slats are, and throwing that away on every restart would cost a
        # full `slat_time` of travel the first time the cover is asked to open.
        position, tilt = self._estimate()
        return RestoredExtraData({"position": position, "tilt": tilt})

    async def async_added_to_hass(self) -> None:
        """Restore the last known position/tilt, then register and request the status.

        The restore comes first on purpose: registering the entity sends a status
        request, and a movement reply could otherwise race the restore.
        """
        if not self._advanced and self._attr_current_cover_position is None:
            await self._async_restore_position()
        await super().async_added_to_hass()

    async def _async_restore_position(self) -> None:
        """Bring back the estimate saved by `extra_restore_state_data` (or the old state)."""
        position: int | None = None
        tilt: int | None = None
        extra_data = await self.async_get_last_extra_data()
        if extra_data is not None:
            stored = extra_data.as_dict()
            position = stored.get("position")
            tilt = stored.get("tilt")
        if position is None:
            last_state = await self.async_get_last_state()
            if last_state is None:
                return
            position = last_state.attributes.get(ATTR_CURRENT_POSITION)
            tilt = last_state.attributes.get(ATTR_CURRENT_TILT_POSITION)
            if position is None:
                if last_state.state == CoverState.CLOSED:
                    position = 0
                elif last_state.state == CoverState.OPEN:
                    position = 100
        if position is not None:
            if tilt is None:
                # Upgrades from a version without tilt: the slats are open unless the
                # curtain rests on the floor.
                tilt = 100 if int(position) > 0 else 0
            self._finish_movement(int(position), int(tilt))

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending timers before the entity goes away."""
        self._cancel_timers()
        await super().async_will_remove_from_hass()

    # ------------------------------------------------------------------ commands
    def _direction_command(self, direction: str):
        """The bus command that moves the cover in `direction` (honouring `inverted`)."""
        if (direction == OPENING) != self._inverted:
            return OWNAutomationCommand.raise_shutter
        return OWNAutomationCommand.lower_shutter

    async def async_update(self) -> None:
        """Ask the gateway for the current state (also called on entity add)."""
        await self._gateway_handler.send_status_request(OWNAutomationCommand.status(self._full_where))

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover, all the way to the upper end stop."""
        if await self._gateway_handler.send(self._direction_command(OPENING)(self._full_where)) and not self._advanced:
            self._start_movement(OPENING, own_command=True)
            self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover, all the way to the lower end stop (slats included)."""
        if await self._gateway_handler.send(self._direction_command(CLOSING)(self._full_where)) and not self._advanced:
            self._start_movement(CLOSING, own_command=True)
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover and freeze the estimated position and tilt.

        A stop the command path could not even take leaves everything as it was: the
        shutter is still running, so the estimate must keep running with it. Note
        that `send()` answers as soon as the command is *queued*, not when the
        gateway accepts it - a queued stop that later expires on `command_ttl` or is
        NACKed still ends the estimate here. Only the refusal below is knowable at
        this point.
        """
        sent = await self._gateway_handler.send(OWNAutomationCommand.stop_shutter(self._full_where))
        if self._advanced:
            # An advanced actuator reports its own position and its own direction:
            # there is no estimate here to end, and its `stopped` frame will do the
            # work. (This is *not* a refusal path - the command went out fine.)
            return
        if not sent:
            # The command never even reached the queue (it is full, or the handler is
            # closing), so the shutter is still running: touching the model here would
            # freeze the position at wherever the estimate had got to and leave it
            # there for good. Change nothing, exactly as `open`, `close` and
            # `set_position` do when their own command is refused.
            return
        interrupted = self._moving
        self._finish_movement(*self._estimate())
        # A stop the gateway never took cannot be echoed back, so arming the echo
        # window on it would only swallow somebody else's frame.
        self._mark_own_stop(interrupted)
        self.async_write_ha_state()

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop the slats: the same bus command as `stop_cover`."""
        await self.async_stop_cover(**kwargs)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the curtain to a specific position.

        Advanced actuators take the position directly; for basic ones the cover is
        moved in the right direction and stopped by a timer, after the run computed
        through both phases of the model (Contract F).  The two ends are run to the
        end stop instead, which also re-calibrates the estimate.
        """
        if ATTR_POSITION not in kwargs:
            return
        position = int(kwargs[ATTR_POSITION])

        if self._advanced:
            level = 100 - position if self._inverted else position
            await self._gateway_handler.send(OWNAutomationCommand.set_shutter_level(self._full_where, level))
            return

        current = self.current_cover_position
        if current is None:
            # Unknown position: run to the closest end first so the estimate has a
            # reference; a plain open/close is the honest approximation here.
            if position >= 50:
                await self.async_open_cover()
            else:
                await self.async_close_cover()
            return
        if position >= 100:
            await self.async_open_cover()
            return
        if position <= 0:
            await self.async_close_cover()
            return
        if position == current:
            if self._moving is not None:
                # Already passing through the target: stop here instead of ignoring it.
                await self.async_stop_cover()
            return

        direction = OPENING if position > current else CLOSING
        if await self._gateway_handler.send(self._direction_command(direction)(self._full_where)):
            # Above the floor the slats are always open.
            self._start_movement(direction, target_position=position, target_tilt=100, own_command=True)
            self.async_write_ha_state()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the slats (only meaningful with the curtain on the floor)."""
        await self._async_move_tilt(100)

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the slats: run down to the lower end stop."""
        await self._async_move_tilt(0)

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Set the slat openness proportionally inside the slat phase."""
        if ATTR_TILT_POSITION not in kwargs:
            return
        await self._async_move_tilt(int(kwargs[ATTR_TILT_POSITION]))

    async def _async_move_tilt(self, target_tilt: int) -> None:
        """Move the slats to `target_tilt` (0-100); no-op while the curtain is up."""
        if not self._has_tilt:
            return
        position, tilt = self._estimate()
        if position is None:
            LOGGER.debug(
                "%s Cover %s: tilt command ignored, the position is not known yet",
                self._gateway_handler.log_id,
                self._where,
            )
            return
        if position > 0:
            LOGGER.debug(
                "%s Cover %s: the slats are always open while the curtain is up (position %s%%), tilt command ignored",
                self._gateway_handler.log_id,
                self._where,
                position,
            )
            return
        if target_tilt <= 0:
            # Closing the slats means running into the lower end stop: let the
            # actuator stop by itself, it re-calibrates the estimate for free.
            await self.async_close_cover()
            return
        if tilt is None or target_tilt == tilt:
            return
        direction = OPENING if target_tilt > tilt else CLOSING
        if await self._gateway_handler.send(self._direction_command(direction)(self._full_where)):
            self._start_movement(direction, target_position=0, target_tilt=target_tilt, own_command=True)
            self.async_write_ha_state()

    def _reached_end_stop(self) -> bool:
        """A stop during our own free run counts as the end stop once most of it has run."""
        if self._move_started_at is None or not self._move_duration:
            return False
        elapsed = (dt_util.utcnow() - self._move_started_at).total_seconds()
        return elapsed >= END_STOP_MIN_FRACTION * self._move_duration

    # ------------------------------------------------------------------ calibration
    def _reject_calibration(self, service: str) -> None:
        """An advanced actuator has nothing to calibrate: it reports its own position."""
        if self._advanced:
            raise ServiceValidationError(
                f"{service}: {self.entity_id} is an 'advanced' cover, which reports its real "
                f"position; there is no travel model to calibrate"
            )

    @property
    def _profile_name(self) -> str:
        """Name for the generated profile: the cover's own object id."""
        object_id = self.entity_id.split(".", 1)[-1] if self.entity_id else ""
        return object_id or CALIBRATION_FALLBACK_PROFILE

    async def async_calibration_run(self, direction: str) -> dict[str, Any]:
        """Run the cover to the half way point of `direction` and stop it there.

        The cover is first sent all the way to the *opposite* end, because the run only
        means anything measured from a known end stop, and the model's own idea of where
        the cover is cannot be trusted - that is what is being calibrated. Then the
        requested direction runs for exactly the seconds a `set_cover_position: 50`
        would spend with this cover's current configuration under the old linear model,
        and is stopped, leaving the bar somewhere the user can measure.

        That is half the *curtain* time closing (the slats never move on the way down
        from the top) and the slat phase plus half the curtain time opening: the two
        motor times `cover_calibration_compute` re-derives from the same YAML.

        Everything goes through the ordinary entity methods, so the estimate, the echo
        window and the safety timers see this run exactly as they see a user's.
        """
        self._reject_calibration(SERVICE_COVER_CALIBRATION_RUN)
        async with _CALIBRATION_LOCK:
            if self._moving is not None:
                raise ServiceValidationError(
                    f"{SERVICE_COVER_CALIBRATION_RUN}: {self.entity_id} is already moving; "
                    f"stop it and try again"
                )
            closing = direction == DIRECTION_CLOSE
            full_run = self._opening_time if closing else self._closing_time
            motor_seconds = (
                calibration_close_run_seconds(self._closing_time, self._slat_time)
                if closing
                else calibration_open_run_seconds(self._opening_time, self._slat_time)
            )
            LOGGER.info(
                "%s Cover %s: calibration run '%s' - going to the far end (%.1fs), then %.1fs of travel",
                self._gateway_handler.log_id,
                self._where,
                direction,
                full_run,
                motor_seconds,
            )
            if closing:
                await self.async_open_cover()
            else:
                await self.async_close_cover()
            await _async_sleep(full_run + CALIBRATION_SETTLE_SEC)

            started = dt_util.utcnow()
            if closing:
                await self.async_close_cover()
            else:
                await self.async_open_cover()
            # Measured from the moment the command went out, not from before it: the
            # command path may have taken a while, and the motor only ran after it.
            spent = (dt_util.utcnow() - started).total_seconds()
            await _async_sleep(max(0.0, motor_seconds - spent))
            await self.async_stop_cover()
        return {
            ATTR_DIRECTION: direction,
            ATTR_MOTOR_SECONDS: round(motor_seconds, 1),
            CONF_OPENING_TIME: round(self._opening_time, 1),
            CONF_CLOSING_TIME: round(self._closing_time, 1),
            CONF_SLAT_TIME: round(self._slat_time, 1),
        }

    async def async_calibration_compute(
        self,
        height: float,
        closed_half_cm: float,
        opened_half_cm: float | None = None,
        slat_time: float | None = None,
        closed_run_seconds: float | None = None,
        opened_run_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Turn the measurements of `cover_calibration_run` into a profile.

        The closing measurement gives `closing_roll`, the opening one `opening_roll`,
        and the two are independent: each inverts its own run, so a shutter that is
        stiffer on the way up simply gets two numbers instead of one.

        `slat_time` is an input, never an answer (see the section comment): given here
        it is used as it stands, otherwise the cover's configured value is.

        The motor seconds default to the ones `cover_calibration_run` computed from
        this cover's configuration, so a user who did not touch the YAML in between has
        nothing to copy across; the two fields are there for the user who did, or who
        measured the runs by hand.
        """
        self._reject_calibration(SERVICE_COVER_CALIBRATION_COMPUTE)
        if closed_half_cm > height:
            raise ServiceValidationError(
                f"{SERVICE_COVER_CALIBRATION_COMPUTE}: closed_half_cm ({closed_half_cm}) is above the "
                f"curtain travel ({height} cm); measure from the floor to the bottom of the bar"
            )
        if opened_half_cm is not None and opened_half_cm > height:
            raise ServiceValidationError(
                f"{SERVICE_COVER_CALIBRATION_COMPUTE}: opened_half_cm ({opened_half_cm}) is above the "
                f"curtain travel ({height} cm); measure from the floor to the bottom of the bar"
            )
        slat = self._slat_time if slat_time is None else slat_time
        # Whatever the run really spent: the defaults are the very seconds it computed
        # from this same configuration, so the equations invert the movement that was
        # actually measured.
        if closed_run_seconds is None:
            closed_run_seconds = calibration_close_run_seconds(self._closing_time, self._slat_time)
        if opened_run_seconds is None:
            opened_run_seconds = calibration_open_run_seconds(self._opening_time, self._slat_time)
        try:
            closing_roll, opening_roll = solve_cover_calibration(
                height=height,
                opening_time=self._opening_time,
                closing_time=self._closing_time,
                closed_half_cm=closed_half_cm,
                closed_run_seconds=closed_run_seconds,
                opened_run_seconds=opened_run_seconds,
                opened_half_cm=opened_half_cm,
                slat_time=slat,
            )
        except ValueError as err:
            raise ServiceValidationError(f"{SERVICE_COVER_CALIBRATION_COMPUTE}: {err}") from err

        # `roll` is the one number to write when only one is wanted; with a single
        # measurement it is simply the one that was measured.
        common = closing_roll if opening_roll is None else (closing_roll + opening_roll) / 2
        answer: dict[str, Any] = {
            CONF_ROLL: round(common, 2),
            CONF_CLOSING_ROLL: round(closing_roll, 2),
            CONF_SLAT_TIME: round(slat, 1),
            CONF_OPENING_TIME: round(self._opening_time, 1),
            CONF_CLOSING_TIME: round(self._closing_time, 1),
            ATTR_HEIGHT: round(height, 1),
            ATTR_CLOSED_RUN_SECONDS: round(closed_run_seconds, 1),
            ATTR_OPENED_RUN_SECONDS: round(opened_run_seconds, 1),
            "yaml": calibration_yaml(
                self._profile_name,
                height,
                self._opening_time,
                self._closing_time,
                slat,
                closing_roll,
                opening_roll,
            ),
        }
        if opening_roll is not None:
            answer[CONF_OPENING_ROLL] = round(opening_roll, 2)
        return answer

    # ------------------------------------------------------------------ events
    def handle_event(self, message: OWNAutomationEvent) -> None:
        """Handle an event message (must never raise: it runs in the event loop)."""
        try:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)

            opening = message.is_opening
            closing = message.is_closing
            if self._inverted:
                opening, closing = closing, opening

            if message.current_position is not None and not self._advanced:
                # Only an advanced actuator reports its own position, and this cover is
                # declared basic - so its whole model is the time-based estimate. Taking
                # the position would swap models half way: `_finish_movement` would stop
                # the estimate and `_set_advanced_direction` would then set the direction
                # again *without* restarting it, leaving the entity reading "Opening" at
                # a frozen percentage until the advanced safety timer expires, and a
                # later plain movement frame could not repair it. What is wrong here is
                # the configuration, not the frame, so say so and change nothing.
                LOGGER.debug(
                    "%s Cover %s: ignoring a position report (%s%%) from a cover configured as basic; "
                    "if this actuator really reports its own position, give it `advanced: true`",
                    self._gateway_handler.log_id,
                    self._where,
                    message.current_position,
                )
                return
            if message.current_position is not None:
                # Advanced actuator: a real position (0 = closed), inverted if wired so.
                position = int(message.current_position)
                if self._inverted:
                    position = 100 - position
                self._finish_movement(position)
                # Dimension 10 also carries the state, and 11-14 mean "moving". Which
                # position those four carry is not settled: OWNd reads it as the
                # position the run *started* from ("is opening from initial position
                # N", OWNd/message.py:593 and 604), while for state 10 it reads it as
                # the current one ("is opened at N%", message.py:583). The value is
                # written either way, because under both readings it is the
                # actuator's own report of where the cover is or was when this run
                # began - which is also our last known position, so it can only
                # confirm it, never rewind it to something we never saw. What the
                # 11-14 frames add is the direction, and that is kept visible.
                if opening:
                    self._set_advanced_direction(OPENING)
                elif closing:
                    self._set_advanced_direction(CLOSING)
            elif self._advanced:
                # A plain WHAT frame from an advanced actuator: track the direction only,
                # the position comes from its own status frames, never from the timer.
                if opening:
                    self._set_advanced_direction(OPENING)
                elif closing:
                    self._set_advanced_direction(CLOSING)
                elif opening is False and closing is False:
                    self._set_advanced_direction(None)
            elif opening:
                # Someone pressed the keypad (or a scenario ran): the very same
                # two-phase model tracks the movement until it stops.
                if self._moving != OPENING and not self._is_echo(OPENING):
                    self._start_movement(OPENING)
            elif closing:
                if self._moving != CLOSING and not self._is_echo(CLOSING):
                    self._start_movement(CLOSING)
            elif opening is False and closing is False:
                if self._is_echo(None):
                    return
                if self._own_free_run and self._moving is not None and self._reached_end_stop():
                    # The actuator hit the end stop before our timer: snap to the end,
                    # this is what re-calibrates the estimate.
                    self._finish_movement(self._end_position, self._end_tilt)
                else:
                    # "Stopped": freeze wherever the estimate got to.
                    self._finish_movement(*self._estimate())
        except Exception:  # pragma: no cover - defensive, keeps the session alive
            LOGGER.exception("%s Error handling cover event %s", self._gateway_handler.log_id, message)
            return

        self.async_schedule_update_ha_state()
