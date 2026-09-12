"""The maths of the guided cover calibration (0.5.0), with nothing of Home Assistant in it.

The guided calibration replaces the stopwatch with a tape measure. The integration
already knows when the motor starts (the actuator answers our frame with its own
"moving" status, 0.4.4), so the user only ever presses a button when something
*happens* - the bottom edge lifts off the floor, the shutter stops - and measures a
few heights with a tape. This module turns those two kinds of reading into the four
numbers the travel model runs on: the slat time, the two run times and the roll of
each direction.

Two things are solved together, per direction (`fit_direction`):

* **the roll** `k`, the ratio between the fat roll at the top of the travel and the
  bare tube at the bottom - the whole of the curtain model, see `roll_x` below; and
* **a time scale** `s = Tc_configured / Tc_true`, which is what makes the tape measure
  able to correct the presses. A press carries the user's reaction time, so the run
  time it produces is a little long or a little short; every later measurement of the
  same shutter is then taken at a fraction of a run time that is not quite the real
  one. Rather than pretend the presses are exact, the fit carries that error as one
  unknown and the centimetres pay for it: `s` above 1 means the configured curtain
  time is longer than the true one, so the corrected time is `Tc_configured / s`.

With one measurement only the roll can be solved (`s = 1`, the presses are taken at
their word), which is the base level of the flow; with the three measurements of the
precise level both come out of a least-squares fit.

Everything here is pure: floats in, floats out, no `hass`, no bus, no entity. The cover
entity owns the movements (`cover.py`, the `async_calib_*` primitives) and the config
subentry flow owns the questions (phase 2); this module is only ever given numbers.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from math import sqrt

from homeassistant.exceptions import HomeAssistantError

from .const import (
    DIRECTION_CLOSE,
    DIRECTION_OPEN,
    MAX_ROLL,
    MIN_ROLL,
    ROLL_LINEAR_TOLERANCE,
)

# How much of the interval between the thing happening and the button being pressed is
# taken off the measured time. Zero by default, and deliberately so: the flow's own
# answer to the reaction time is the time scale `s` of `fit_direction`, which measures
# it on the shutter instead of assuming a number for it. The constant stays because it
# is the one place a future release could put a measured correction, and because a
# reader looking for "where is the reaction time handled" has to find an answer.
PRESS_REACTION_SEC = 0.0

# The two ends of the fit. The roll range is the validator's own (`MIN_ROLL`/`MAX_ROLL`:
# below 1 the model is not a roll at all, above 5 no shutter has ever been measured).
# The scale range says how wrong a press may be before the answer is a mistake rather
# than a reaction: 0.7-1.3 is +/- 30 % of a run time, several seconds on a real shutter,
# which no hand is slow enough to produce. A fit that ends up on one of those bounds is
# not a fit, it is a measurement that belongs to another shutter.
DEFAULT_ROLL_BOUNDS = (MIN_ROLL, MAX_ROLL)
DEFAULT_SCALE_BOUNDS = (0.7, 1.3)

# The search: a grid over (k, s) that is re-drawn around its own best cell, five times.
# Nothing cleverer is warranted - the surface is smooth and two-dimensional, the whole
# search is under a thousand evaluations of eight lines of arithmetic, and a gradient
# method would have to carry a starting point and a failure mode for the sake of
# microseconds. Five rounds of a 12-cell grid narrow the roll to 4 * (2/12)**5, well
# under a thousandth, which is two orders of magnitude finer than anything a tape
# measure can say.
_FIT_GRID_CELLS = 12
_FIT_GRID_ROUNDS = 5


class CalibrationError(HomeAssistantError):
    """A calibration step that cannot go on, with a reason the flow can branch on.

    `reason` is a short machine-readable string (`no_echo`, `not_delivered`, ...): the
    config subentry flow of phase 2 shows a different text for each of them, and a
    translation key is not something to build out of a sentence. The message is the
    sentence, for the log and for a service call.
    """

    def __init__(self, reason: str, message: str | None = None) -> None:
        super().__init__(message or reason)
        self.reason = reason


# Reasons `CalibrationError` is raised with. The runner (`cover.py`) raises the first
# five, this module the last two.
REASON_NO_ECHO = "no_echo"
REASON_NOT_DELIVERED = "not_delivered"
REASON_NOT_STOPPED = "not_stopped"
REASON_BUSY = "busy"
REASON_ADVANCED = "advanced"
REASON_NO_POINTS = "no_points"
REASON_BAD_POINT = "bad_point"


# ------------------------------------------------------------------ the roll model
# `x` is the fraction of the CURTAIN travel measured from the top: x = 0 fully open,
# x = 1 curtain on the floor (so x = 1 - position/100). `tau` is the fraction of the
# curtain time. Descending from the top at constant motor speed, the curtain covers
# less and less distance per second as the roll on the tube gets thinner, and the two
# functions below are that relation and its inverse. They are pure and total: the whole
# roll model of the integration is these eight lines, and they live here rather than in
# `cover.py` (which imports them under their old private names) because the fit is
# nothing but this function read backwards.
def roll_tau(roll: float, x: float) -> float:
    """Fraction of the curtain time needed to descend from the top to `x`."""
    x = min(1.0, max(0.0, x))
    k = max(MIN_ROLL, roll)
    if k - 1.0 <= ROLL_LINEAR_TOLERANCE:
        return x
    return (k - sqrt(k * k - (k * k - 1) * x)) / (k - 1)


def roll_x(roll: float, tau: float) -> float:
    """Where the curtain is after descending from the top for `tau` of the curtain time."""
    tau = min(1.0, max(0.0, tau))
    k = max(MIN_ROLL, roll)
    if k - 1.0 <= ROLL_LINEAR_TOLERANCE:
        return tau
    return (k * k - (k - tau * (k - 1)) ** 2) / (k * k - 1)


def clamped_roll(roll: float | None, fallback: float) -> float:
    """A roll inside the physical range, falling back when the key was not written.

    Contract A already guarantees both, but the entity is also constructible by hand
    (tests, a config flow), and a roll below 1 makes `roll_x` return a position outside
    [0, 100] rather than merely a wrong one.
    """
    if not roll:
        return fallback
    return min(MAX_ROLL, max(MIN_ROLL, float(roll)))


# ------------------------------------------------------------------ what a step gives
@dataclass(frozen=True, slots=True)
class FitPoint:
    """One tape-measure reading, with the run it belongs to.

    `fraction` is tau: how much of the CONFIGURED curtain time of that direction the
    motor ran for. The configured time is whatever the flow has at that moment (the
    presses of the timed runs), which is exactly why the fit carries a scale: the
    fraction is known exactly, the time it is a fraction *of* is not.

    `measured_cm` is the height of the bottom edge above where it rests when the
    shutter is closed, and `height` the whole of that travel - so both ends of the
    model are the same reference the user measured against.
    """

    fraction: float
    measured_cm: float
    height: float


@dataclass(frozen=True, slots=True)
class FitResult:
    """What `fit_direction` found: the two parameters and how well they explain the data.

    `residuals_cm` is per point, in the order the points were given, model minus
    measurement - so a positive residual means the model puts the bar higher than the
    tape did. The flow shows `max_residual_cm` as "your shutter stops within X cm of
    the estimate", which is the only part of this a user can check.
    """

    roll: float
    time_scale: float
    residuals_cm: tuple[float, ...] = ()
    points: int = 0

    @property
    def max_residual_cm(self) -> float:
        """The worst point, in centimetres (0 when a single point was fitted exactly)."""
        return max((abs(value) for value in self.residuals_cm), default=0.0)

    @property
    def rms_residual_cm(self) -> float:
        """Root mean square of the residuals: the spread rather than the worst case."""
        if not self.residuals_cm:
            return 0.0
        return sqrt(sum(value * value for value in self.residuals_cm) / len(self.residuals_cm))


@dataclass(frozen=True, slots=True)
class PressTiming:
    """The two times one measured run yields, in seconds of motor.

    `slat_time` is None for a run whose slat press was not asked for (a descent in the
    base level, where the slats are assumed to take as long to close as they took to
    open).
    """

    slat_time: float | None
    run_time: float


@dataclass(frozen=True, slots=True)
class RunReport:
    """What one automatic run of the cover runner did (`async_calib_run_fraction`).

    `motor_start` and `stop_written` are instants on Home Assistant's own clock
    (`dt_util.utcnow()`), the two ends of the movement as the bus reported them;
    `motor_seconds` is the motor time between them as the actuator itself timed it
    where it said anything, and the model's two bus costs where it did not (the same
    measurement `cover_calibration_run` has reported since 0.4.4). `planned_seconds`
    is what the run asked for: the two differ by whatever the command queue cost, and
    the fit must be given the seconds that really happened.
    """

    motor_start: datetime
    stop_written: datetime | None
    motor_seconds: float
    planned_seconds: float
    fraction: float = 0.0
    direction: str = ""


# ------------------------------------------------------------------ times from presses
def _instant(value: datetime | float) -> float:
    """Seconds, from either a `datetime` or a number of seconds.

    The runner works on `dt_util.utcnow()` (as the whole cover model does) and a flow
    that timestamps a button press has the same clock to hand, but a caller with a
    monotonic reading should not have to convert it. Both are accepted and the
    difference between two of them is all this module ever looks at.
    """
    return value.timestamp() if isinstance(value, datetime) else float(value)


def timing_from_presses(
    motor_start: datetime | float,
    lift_off: datetime | float | None,
    stopped: datetime | float,
) -> PressTiming:
    """Turn one measured run into (slat time, run time).

    `motor_start` is the actuator's own word - the instant the motor really began to
    turn - so neither of the two times carries the bus delay the user never saw. The
    two presses are the user's: the bottom edge leaving the floor (the end of the slat
    phase, `lift_off`, optional) and the shutter coming to rest (`stopped`).

    `PRESS_REACTION_SEC` is taken off both, and is zero: the reaction time is solved
    for on the shutter instead (see `fit_direction`).

    Raises `CalibrationError` when the presses did not happen in the order the physics
    requires - which is a user who pressed the wrong button, not a bug, and the flow
    offers the step again.
    """
    started = _instant(motor_start)
    end = _instant(stopped) - PRESS_REACTION_SEC
    run_time = end - started
    if run_time <= 0:
        raise CalibrationError(
            REASON_BAD_POINT,
            f"the shutter was reported stopped {-run_time:.1f} s before the motor started",
        )
    slat_time: float | None = None
    if lift_off is not None:
        slat_time = _instant(lift_off) - PRESS_REACTION_SEC - started
        if slat_time < 0 or slat_time > run_time:
            raise CalibrationError(
                REASON_BAD_POINT,
                f"the slat press ({slat_time:.1f} s) is outside the run it belongs to "
                f"(0 - {run_time:.1f} s)",
            )
    return PressTiming(slat_time, run_time)


def corrected_curtain_time(configured_curtain: float, time_scale: float) -> float:
    """The true curtain time behind a configured one: `Tc_true = Tc_configured / s`."""
    if time_scale <= 0:  # pragma: no cover - the fit never leaves the scale bounds
        raise CalibrationError(REASON_BAD_POINT, f"a time scale of {time_scale} is not a ratio")
    return configured_curtain / time_scale


def corrected_run_time(configured_curtain: float, time_scale: float, slat_time: float) -> float:
    """The full run time to write: the slat phase plus the corrected curtain time.

    The slat phase is measured directly (a press at the instant the bottom edge lifts
    off) and needs no correction of its own beyond the one the press already carries;
    the curtain time is what the tape measure corrects.
    """
    return max(0.0, slat_time) + corrected_curtain_time(configured_curtain, time_scale)


# ------------------------------------------------------------------ the fit
def predict_cm(direction: str, roll: float, time_scale: float, fraction: float, height: float) -> float:
    """Where the model says the bottom edge is after `fraction` of the configured curtain time.

    The two directions are the same equation read from opposite ends, exactly as
    `calibration_descent_cm` / `calibration_ascent_cm` in `cover.py` are: a descent
    starts at the top and `tau` of the curtain time puts the bar at `x`; an ascent
    starts on the floor, so the bar is `tau` of the curtain time *above* it, which is
    where a descent of `1 - tau` would have left it.

    `fraction * time_scale` is the whole of the time scale's work: the run was
    `fraction` of the time the configuration believes in, and `time_scale` is how much
    longer that belief is than the truth.
    """
    effective = min(1.0, max(0.0, fraction * time_scale))
    if direction == DIRECTION_CLOSE:
        return height * (1.0 - roll_x(roll, effective))
    return height * (1.0 - roll_x(roll, 1.0 - effective))


def _check_points(direction: str, points: Sequence[FitPoint]) -> None:
    """Refuse a point that cannot have been measured, naming what is wrong with it."""
    if direction not in (DIRECTION_CLOSE, DIRECTION_OPEN):
        raise CalibrationError(
            REASON_BAD_POINT,
            f"{direction!r} is not a direction; expected {DIRECTION_CLOSE!r} or {DIRECTION_OPEN!r}",
        )
    if not points:
        raise CalibrationError(REASON_NO_POINTS, "a fit needs at least one measurement")
    for point in points:
        if point.height <= 0:
            raise CalibrationError(
                REASON_BAD_POINT, f"a curtain travel of {point.height} cm is not a height"
            )
        if not 0.0 < point.fraction <= 1.0:
            raise CalibrationError(
                REASON_BAD_POINT,
                f"a run of {point.fraction} of the curtain time is outside (0, 1]",
            )
        if not 0.0 <= point.measured_cm <= point.height:
            raise CalibrationError(
                REASON_BAD_POINT,
                f"a bar measured at {point.measured_cm:.0f} cm is outside the "
                f"{point.height:.0f} cm of curtain travel; measure from where the bottom "
                f"edge rests when the shutter is closed",
            )


def _residuals(direction: str, roll: float, scale: float, points: Iterable[FitPoint]) -> list[float]:
    """Model minus measurement, in centimetres, point by point."""
    return [
        predict_cm(direction, roll, scale, point.fraction, point.height) - point.measured_cm
        for point in points
    ]


def _sum_of_squares(direction: str, roll: float, scale: float, points: Sequence[FitPoint]) -> float:
    return sum(value * value for value in _residuals(direction, roll, scale, points))


def _fit_roll_only(direction: str, point: FitPoint, roll_bounds: tuple[float, float]) -> float:
    """The roll that puts the bar exactly where it was measured, with the presses trusted.

    One measurement cannot say anything about the time scale - any error in the run
    time can be absorbed by the roll and the other way round - so the base level of the
    flow solves the roll alone. The predicted height falls as the roll grows (a fatter
    roll at the top moves more curtain in the same time) in both directions, so a plain
    bisection converges; a measurement outside what the range can produce simply ends
    on the nearer bound, which is the honest answer to "this shutter is not a roll".
    """
    low, high = roll_bounds
    for _ in range(60):
        middle = (low + high) / 2
        if predict_cm(direction, middle, 1.0, point.fraction, point.height) > point.measured_cm:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def fit_direction(
    direction: str,
    points: Sequence[FitPoint],
    *,
    roll_bounds: tuple[float, float] = DEFAULT_ROLL_BOUNDS,
    scale_bounds: tuple[float, float] = DEFAULT_SCALE_BOUNDS,
) -> FitResult:
    """Fit the roll (and, from two points on, the time scale) of one direction.

    `direction` is `DIRECTION_CLOSE` or `DIRECTION_OPEN` (the spec calls this function
    `fit_direction(points, ...)`; the direction has to be an argument because the two
    directions are different equations, and passing it first reads as the name does).

    One point solves the roll alone and returns `time_scale = 1.0` with no residual -
    there is nothing left over to be a residual of. Two or three points solve both, by
    least squares over a grid that is re-drawn around its own best cell (see
    `_FIT_GRID_CELLS`).

    What the numbers are worth: with the three fractions of the precise level (25 %,
    50 %, 75 %) and a tape read to the nearest centimetre, the roll comes back within
    about 0.05 and the scale within about 0.005 *on average* - but the surface has a
    long flat valley, so a single unlucky set of readings can put the roll 0.2 out
    while predicting the shutter to within a centimetre and a half all the same. That
    is the honest way round: the pair is a means, the centimetres are the end, and
    `residuals_cm` is what says whether this shutter was measured or merely guessed at.
    """
    _check_points(direction, points)
    if len(points) == 1:
        return FitResult(
            roll=_fit_roll_only(direction, points[0], roll_bounds),
            time_scale=1.0,
            residuals_cm=(),
            points=1,
        )

    low_roll, high_roll = roll_bounds
    low_scale, high_scale = scale_bounds
    best_roll, best_scale = low_roll, low_scale
    for _ in range(_FIT_GRID_ROUNDS):
        best_error: float | None = None
        for i in range(_FIT_GRID_CELLS + 1):
            roll = low_roll + (high_roll - low_roll) * i / _FIT_GRID_CELLS
            for j in range(_FIT_GRID_CELLS + 1):
                scale = low_scale + (high_scale - low_scale) * j / _FIT_GRID_CELLS
                error = _sum_of_squares(direction, roll, scale, points)
                if best_error is None or error < best_error:
                    best_error, best_roll, best_scale = error, roll, scale
        # One cell either way around the winner: the minimum is inside that box
        # whatever the surface does in between, because every other cell of this round
        # was worse than its centre.
        roll_step = (high_roll - low_roll) / _FIT_GRID_CELLS
        scale_step = (high_scale - low_scale) / _FIT_GRID_CELLS
        low_roll, high_roll = (
            max(roll_bounds[0], best_roll - roll_step),
            min(roll_bounds[1], best_roll + roll_step),
        )
        low_scale, high_scale = (
            max(scale_bounds[0], best_scale - scale_step),
            min(scale_bounds[1], best_scale + scale_step),
        )
    return FitResult(
        roll=best_roll,
        time_scale=best_scale,
        residuals_cm=tuple(_residuals(direction, best_roll, best_scale, points)),
        points=len(points),
    )


@dataclass(frozen=True, slots=True)
class DirectionFit:
    """A fitted direction, with the run time its scale corrects, ready for a profile."""

    direction: str
    fit: FitResult
    slat_time: float
    run_time: float
    points: tuple[FitPoint, ...] = field(default_factory=tuple)

    @property
    def curtain_time(self) -> float:
        """The corrected curtain time: what the motor really spends moving the curtain."""
        return corrected_curtain_time(max(0.0, self.run_time - self.slat_time), self.fit.time_scale)

    @property
    def corrected_run_time(self) -> float:
        """The run time to write into the profile: slat phase plus corrected curtain."""
        return self.slat_time + self.curtain_time


def fit_from_run(
    direction: str,
    *,
    run_time: float,
    slat_time: float,
    measurements: Sequence[tuple[float, float]],
    height: float,
    roll_bounds: tuple[float, float] = DEFAULT_ROLL_BOUNDS,
    scale_bounds: tuple[float, float] = DEFAULT_SCALE_BOUNDS,
) -> DirectionFit:
    """Fit one direction from motor seconds rather than fractions.

    The flow measures in seconds - it asks the runner for "half of the curtain time"
    and gets back the seconds the motor really ran (`RunReport.motor_seconds`) - while
    the fit works in fractions of the configured curtain time. This is the one
    conversion between the two, in one place so that the slat phase is taken off the
    ascents exactly once.

    `measurements` is a list of (motor seconds of that run, measured centimetres).
    A descent from the top is all curtain; an ascent from the floor spends its first
    `slat_time` seconds on the slats and only the rest moves the bar, which is what the
    subtraction below is.
    """
    curtain = max(1e-3, run_time - slat_time)
    points = []
    for seconds, measured_cm in measurements:
        moving = seconds if direction == DIRECTION_CLOSE else max(0.0, seconds - slat_time)
        points.append(FitPoint(fraction=min(1.0, moving / curtain), measured_cm=measured_cm, height=height))
    fit = fit_direction(direction, points, roll_bounds=roll_bounds, scale_bounds=scale_bounds)
    return DirectionFit(
        direction=direction, fit=fit, slat_time=slat_time, run_time=run_time, points=tuple(points)
    )


def deviation_cm(
    direction: str,
    *,
    roll: float,
    height: float,
    run_time: float,
    slat_time: float,
    motor_seconds: float,
    measured_cm: float,
) -> float:
    """How far the shutter really stopped from where the model said it would, in cm.

    Positive means the bar ended *above* the estimate. This is the verification step
    of the flow (path B's optional check and the precise level's final one), and it is
    deliberately not a fit: it asks one question of the model as it currently stands.
    """
    curtain = max(1e-3, run_time - slat_time)
    moving = motor_seconds if direction == DIRECTION_CLOSE else max(0.0, motor_seconds - slat_time)
    predicted = predict_cm(direction, roll, 1.0, min(1.0, moving / curtain), height)
    return measured_cm - predicted


__all__ = [
    "DEFAULT_ROLL_BOUNDS",
    "DEFAULT_SCALE_BOUNDS",
    "PRESS_REACTION_SEC",
    "REASON_ADVANCED",
    "REASON_BAD_POINT",
    "REASON_BUSY",
    "REASON_NOT_DELIVERED",
    "REASON_NOT_STOPPED",
    "REASON_NO_ECHO",
    "REASON_NO_POINTS",
    "CalibrationError",
    "DirectionFit",
    "FitPoint",
    "FitResult",
    "PressTiming",
    "RunReport",
    "clamped_roll",
    "corrected_curtain_time",
    "corrected_run_time",
    "deviation_cm",
    "fit_direction",
    "fit_from_run",
    "predict_cm",
    "roll_tau",
    "roll_x",
    "timing_from_presses",
]
