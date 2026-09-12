"""Tests for the pure maths of the guided calibration (0.5.0, `calibration.py`).

No Home Assistant anywhere in this file: the module is floats in, floats out, and the
only honest way to test a solver is to make the model produce measurements and ask the
solver to give the parameters back.

Two kinds of test, and they answer different questions:

* the **round trip**, with no noise at all, which pins the equations - any sign error,
  any swapped direction, any mis-scaled fraction shows up at the sixth decimal; and
* the **recovery under noise**, which pins what the flow can promise a user: a tape
  read to the nearest centimetre has half a centimetre of slack in it, and the fit has
  to come back close enough for the shutter to stop where the user expects.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

import pytest

from custom_components.myhome import calibration, cover as cover_module
from custom_components.myhome.calibration import (
    CalibrationError,
    FitPoint,
    FitResult,
    fit_direction,
    fit_from_run,
    predict_cm,
    timing_from_presses,
)
from custom_components.myhome.const import DIRECTION_CLOSE, DIRECTION_OPEN

# The reference window of the 0.4.2 specification, and the one the existing calibration
# services are tested against: 195 cm of travel, 4.7 s of slats, an asymmetric run.
HEIGHT = 195.0
OPENING = 22.3
CLOSING = 21.7
SLAT = 4.7
# The motor seconds a `set_cover_position: 50` spends on it, down and up.
RUN_DOWN = (CLOSING - SLAT) / 2  # 8.5 s
RUN_UP = SLAT + (OPENING - SLAT) / 2  # 13.5 s
# Half a centimetre either way: a tape measure read to the nearest centimetre.
TAPE_NOISE_CM = 0.5
# The three fractions the precise level of the flow measures at.
PRECISE_FRACTIONS = (0.25, 0.5, 0.75)


def _points(direction: str, roll: float, scale: float, fractions=PRECISE_FRACTIONS, noise=None):
    """Measurements the model itself produced, optionally with a tape measure's slack."""
    return [
        FitPoint(
            fraction=fraction,
            measured_cm=predict_cm(direction, roll, scale, fraction, HEIGHT)
            + (0.0 if noise is None else noise()),
            height=HEIGHT,
        )
        for fraction in fractions
    ]


# --------------------------------------------------------------------------------------
# The model itself
# --------------------------------------------------------------------------------------
def test_the_cover_uses_this_very_roll_model() -> None:
    """`cover.py` imports the functions rather than keeping a copy of them.

    The guided calibration inverts the travel model, so the two must be the same eight
    lines: a solver free to drift away from the model the shutter runs on would answer
    a question nobody asked.

    Mutation caught: re-introducing a private copy of `_roll_x` in `cover.py`.
    """
    assert cover_module._roll_x is calibration.roll_x
    assert cover_module._roll_tau is calibration.roll_tau
    assert cover_module._clamped_roll is calibration.clamped_roll


@pytest.mark.parametrize("roll", [1.0, 1.6, 2.12, 5.0])
def test_predict_cm_spans_the_whole_travel(roll: float) -> None:
    """Both directions start at one end of the window and finish at the other.

    A descent starts at the top (the whole height above the closed position) and ends
    on the floor; an ascent does the same journey backwards. Anything else means the
    two equations have been swapped, which is the one mistake that produces plausible
    numbers everywhere in between.
    """
    assert predict_cm(DIRECTION_CLOSE, roll, 1.0, 1e-9, HEIGHT) == pytest.approx(HEIGHT, abs=1e-6)
    assert predict_cm(DIRECTION_CLOSE, roll, 1.0, 1.0, HEIGHT) == pytest.approx(0.0, abs=1e-9)
    assert predict_cm(DIRECTION_OPEN, roll, 1.0, 1e-9, HEIGHT) == pytest.approx(0.0, abs=1e-6)
    assert predict_cm(DIRECTION_OPEN, roll, 1.0, 1.0, HEIGHT) == pytest.approx(HEIGHT, abs=1e-9)
    # Half way through the run the two are the same point, whatever the roll: that is
    # why a single half-run measurement per direction cannot separate roll from time.
    assert predict_cm(DIRECTION_CLOSE, roll, 1.0, 0.5, HEIGHT) == pytest.approx(
        predict_cm(DIRECTION_OPEN, roll, 1.0, 0.5, HEIGHT)
    )


def test_the_time_scale_stretches_the_run() -> None:
    """`s` is `Tc_configured / Tc_true`: above 1 the shutter is further along than believed.

    Mutation caught: dividing by the scale instead of multiplying, which turns every
    correction the wrong way round and makes the fit chase its own tail.
    """
    slow = predict_cm(DIRECTION_CLOSE, 1.6, 1.0, 0.5, HEIGHT)
    faster = predict_cm(DIRECTION_CLOSE, 1.6, 1.2, 0.5, HEIGHT)
    assert faster < slow  # 20 % more of the real run has gone by, so the bar is lower
    # A scale of 1.2 at 50 % is the same point as a scale of 1 at 60 %.
    assert faster == pytest.approx(predict_cm(DIRECTION_CLOSE, 1.6, 1.0, 0.6, HEIGHT))


# --------------------------------------------------------------------------------------
# The fit, without noise
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("direction", [DIRECTION_CLOSE, DIRECTION_OPEN])
@pytest.mark.parametrize(("roll", "scale"), [(1.0, 1.0), (1.69, 1.05), (2.12, 0.92), (3.4, 1.2)])
def test_three_clean_points_give_the_parameters_back(direction: str, roll: float, scale: float) -> None:
    """The round trip: predict three heights, then solve them back.

    Mutation caught: any scaling error in `predict_cm`, and a grid that shrinks around
    the wrong cell (the answer is then out in the second decimal).
    """
    result = fit_direction(direction, _points(direction, roll, scale))
    assert result.roll == pytest.approx(roll, abs=0.01)
    assert result.time_scale == pytest.approx(scale, abs=0.005)
    assert result.max_residual_cm < 0.1
    assert result.rms_residual_cm < 0.1
    assert result.points == 3


@pytest.mark.parametrize("direction", [DIRECTION_CLOSE, DIRECTION_OPEN])
def test_two_points_are_enough_for_both_parameters(direction: str) -> None:
    """Two equations, two unknowns: the fit is exact when the readings are.

    Mutation caught: falling back to the single-point branch for anything short of
    three measurements, which would silently trust the presses.
    """
    result = fit_direction(direction, _points(direction, 1.8, 1.1, fractions=(0.3, 0.7)))
    assert result.roll == pytest.approx(1.8, abs=0.01)
    assert result.time_scale == pytest.approx(1.1, abs=0.005)
    assert result.max_residual_cm < 0.05


def test_one_point_solves_the_roll_and_trusts_the_presses() -> None:
    """The base level of the flow: one measurement, one number, and no invented scale.

    A single height cannot tell a fatter roll from a longer run - they move the bar the
    same way - so the scale stays at 1 and says so, rather than coming back as
    whatever the grid happened to land on.

    Mutation caught: fitting two parameters to one point (the grid then returns a
    scale off the edge of its range, and the roll with it).
    """
    result = fit_direction(DIRECTION_CLOSE, _points(DIRECTION_CLOSE, 1.69, 1.0, fractions=(0.5,)))
    assert result.roll == pytest.approx(1.69, abs=0.01)
    assert result.time_scale == 1.0
    assert result.residuals_cm == ()
    assert result.max_residual_cm == 0.0
    assert result.rms_residual_cm == 0.0
    assert result.points == 1


def test_a_single_point_outside_the_roll_range_lands_on_its_bound() -> None:
    """A shutter that is not a roll at all gets the nearest roll there is, not an error.

    The flow has a use for "as linear as this model goes"; what it has no use for is a
    step that fails after the user has measured. The residual - which the flow shows -
    is where such a shutter shows up.
    """
    linear_limit = predict_cm(DIRECTION_CLOSE, 1.0, 1.0, 0.5, HEIGHT)
    point = FitPoint(fraction=0.5, measured_cm=linear_limit + 5, height=HEIGHT)
    assert fit_direction(DIRECTION_CLOSE, [point]).roll == pytest.approx(calibration.MIN_ROLL, abs=1e-6)
    fattest = predict_cm(DIRECTION_CLOSE, 5.0, 1.0, 0.5, HEIGHT)
    point = FitPoint(fraction=0.5, measured_cm=max(0.0, fattest - 5), height=HEIGHT)
    assert fit_direction(DIRECTION_CLOSE, [point]).roll == pytest.approx(calibration.MAX_ROLL, abs=1e-6)


def test_the_fit_stays_inside_the_bounds_it_was_given() -> None:
    """A caller that narrows the search gets an answer from inside it.

    Path C of the flow refines a shutter that already has a profile: pinning the scale
    to the profile's own is how "its own coefficients, the profile's times" is asked
    for.
    """
    result = fit_direction(
        DIRECTION_CLOSE,
        _points(DIRECTION_CLOSE, 2.5, 1.15),
        roll_bounds=(1.0, 2.0),
        scale_bounds=(1.0, 1.0),
    )
    assert 1.0 <= result.roll <= 2.0
    assert result.time_scale == 1.0
    # It could not reach the truth, and the residuals say so rather than hiding it.
    assert result.max_residual_cm > 1.0


# --------------------------------------------------------------------------------------
# The fit, with a tape measure's noise (spec 1.1)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("direction", "roll", "scale"),
    [(DIRECTION_CLOSE, 1.69, 1.05), (DIRECTION_OPEN, 2.12, 0.92), (DIRECTION_CLOSE, 1.0, 1.0)],
)
def test_the_fit_recovers_the_shutter_through_the_tape_measure(
    direction: str, roll: float, scale: float
) -> None:
    """Half a centimetre of reading error, and the parameters still come back.

    The specification asks for the roll within 0.05 and the scale within 0.02, and that
    is what is asserted - **on the average of many draws**, because it is an average
    kind of statement: the least-squares surface has a long flat valley (a fatter roll
    and a slightly shorter run put the bar in nearly the same place at every fraction),
    so one unlucky set of three readings can put the roll 0.2 out while still
    predicting the shutter to within a centimetre and a half.

    Which is why the second assertion is the one that matters to a user: whatever the
    pair comes out as, the model built from it must place the bar within two
    centimetres of the real one *everywhere in the travel*, not only at the three
    points that were measured. That is the promise the flow makes. (Everywhere means
    the interior of the run: the last tenth is the end stop, where the shutter stops
    because it has run out of window and the estimate is re-calibrated anyway.)

    Mutation caught: a fit that optimises the fractions rather than the centimetres
    (the prediction error then grows at the ends of the travel, where nothing was
    measured).
    """
    draws = random.Random(20260912)
    roll_errors: list[float] = []
    scale_errors: list[float] = []
    worst_cm = 0.0
    for _ in range(40):
        points = _points(
            direction, roll, scale, noise=lambda: draws.uniform(-TAPE_NOISE_CM, TAPE_NOISE_CM)
        )
        result = fit_direction(direction, points)
        roll_errors.append(abs(result.roll - roll))
        scale_errors.append(abs(result.time_scale - scale))
        worst_cm = max(
            worst_cm,
            max(
                abs(
                    predict_cm(direction, result.roll, result.time_scale, fraction, HEIGHT)
                    - predict_cm(direction, roll, scale, fraction, HEIGHT)
                )
                for fraction in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
            ),
        )
    assert sum(roll_errors) / len(roll_errors) < 0.05
    assert sum(scale_errors) / len(scale_errors) < 0.02
    assert worst_cm < 2.0


def test_noise_free_recovery_is_exact_in_both_directions() -> None:
    """The same recovery with the noise switched off: the fit has no bias of its own.

    A solver whose answer is a few hundredths out on clean data would spend the whole
    error budget before the tape measure had contributed anything.
    """
    for direction in (DIRECTION_CLOSE, DIRECTION_OPEN):
        result = fit_direction(direction, _points(direction, 1.9, 1.08))
        assert result.roll == pytest.approx(1.9, abs=0.005)
        assert result.time_scale == pytest.approx(1.08, abs=0.002)


# --------------------------------------------------------------------------------------
# The measurements of the reference shutter (the data the 0.4.2 services were built on)
# --------------------------------------------------------------------------------------
def test_the_real_shutter_gives_the_same_two_rolls_as_the_services() -> None:
    """85 cm down, 80 cm up: 1.69 and 2.12, the numbers of the 0.4.2 amendment.

    The guided flow measures the same shutter a different way, so it had better agree
    with the service that measured it first - `solve_cover_calibration` inverts exactly
    these two runs, and the two code paths must not drift apart.

    Mutation caught: taking the slat phase off a descent (or not taking it off an
    ascent), which moves both answers by a tenth.
    """
    down = fit_from_run(
        DIRECTION_CLOSE,
        run_time=CLOSING,
        slat_time=SLAT,
        measurements=[(RUN_DOWN, 85.0)],
        height=HEIGHT,
    )
    up = fit_from_run(
        DIRECTION_OPEN,
        run_time=OPENING,
        slat_time=SLAT,
        measurements=[(RUN_UP, 80.0)],
        height=HEIGHT,
    )
    assert down.fit.roll == pytest.approx(1.69, abs=0.02)
    assert 2.0 <= up.fit.roll <= 2.2
    # The very same answer the service gives, to the last digit it publishes.
    service_closing, service_opening = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=85.0,
        closed_run_seconds=RUN_DOWN,
        opened_run_seconds=RUN_UP,
        opened_half_cm=80.0,
        slat_time=SLAT,
    )
    assert down.fit.roll == pytest.approx(service_closing, abs=0.005)
    assert up.fit.roll == pytest.approx(service_opening, abs=0.005)
    # One point, so the presses are taken at their word and the times are unchanged.
    assert down.fit.time_scale == 1.0
    assert down.corrected_run_time == pytest.approx(CLOSING)
    assert up.corrected_run_time == pytest.approx(OPENING)


def test_fit_from_run_converts_seconds_into_fractions_once() -> None:
    """The slat phase is taken off the ascents and nothing else.

    A descent from the top never touches the slats (they are already open and the
    curtain leaves the top at once); an ascent from the floor spends its first seconds
    turning them. Getting that wrong is what makes a shutter's two directions look
    like two different windows.
    """
    down = fit_from_run(
        DIRECTION_CLOSE, run_time=21.7, slat_time=4.7, measurements=[(8.5, 85.0)], height=HEIGHT
    )
    assert down.points[0].fraction == pytest.approx(8.5 / 17.0)
    up = fit_from_run(
        DIRECTION_OPEN, run_time=22.3, slat_time=4.7, measurements=[(13.5, 80.0)], height=HEIGHT
    )
    assert up.points[0].fraction == pytest.approx(8.8 / 17.6)
    # A run longer than the curtain time is the end stop, not an extrapolation.
    long_run = fit_from_run(
        DIRECTION_CLOSE, run_time=21.7, slat_time=4.7, measurements=[(60.0, 0.0)], height=HEIGHT
    )
    assert long_run.points[0].fraction == 1.0


def test_a_fitted_scale_corrects_the_run_times() -> None:
    """`Tc_true = Tc_configured / s`, and the slat phase rides along unscaled.

    The press that ends the slat phase is a direct measurement of it; only the curtain
    time is what the centimetres correct. Scaling the whole run would move the slat
    phase by the reaction time of a press that was never in doubt.
    """
    fit = calibration.DirectionFit(
        direction=DIRECTION_CLOSE,
        fit=FitResult(roll=1.7, time_scale=1.1),
        slat_time=4.7,
        run_time=21.7,
    )
    assert fit.curtain_time == pytest.approx(17.0 / 1.1)
    assert fit.corrected_run_time == pytest.approx(4.7 + 17.0 / 1.1)
    assert calibration.corrected_run_time(17.0, 1.1, 4.7) == pytest.approx(fit.corrected_run_time)
    assert calibration.corrected_curtain_time(17.0, 1.0) == 17.0


# --------------------------------------------------------------------------------------
# Times from button presses
# --------------------------------------------------------------------------------------
def test_timing_from_presses_measures_from_the_motor() -> None:
    """Both times start at the instant the actuator said the motor was running.

    That is the whole point of the "no stopwatch" principle: the user's reaction time
    enters each measurement once (at the press) instead of twice (start and stop), and
    the bus delay does not enter it at all.
    """
    start = datetime(2026, 9, 12, 10, 0, 0)
    timing = timing_from_presses(
        start, start + timedelta(seconds=4.8), start + timedelta(seconds=22.1)
    )
    assert timing.slat_time == pytest.approx(4.8)
    assert timing.run_time == pytest.approx(22.1)
    # Plain seconds work as well as instants: a caller with a monotonic clock is not
    # made to convert it.
    plain = timing_from_presses(100.0, 104.8, 122.1)
    assert plain.slat_time == pytest.approx(timing.slat_time)
    assert plain.run_time == pytest.approx(timing.run_time)


def test_timing_from_presses_without_the_slat_press() -> None:
    """A run measured with one press only: the run time, and nothing invented for the slats."""
    timing = timing_from_presses(0.0, None, 21.4)
    assert timing.slat_time is None
    assert timing.run_time == pytest.approx(21.4)


def test_the_reaction_constant_is_taken_off_both_ends() -> None:
    """`PRESS_REACTION_SEC` is zero, but it is wired in, not merely declared.

    Mutation caught: a constant that documents a correction nobody applies (the day it
    is set to 0.2 s nothing would change).
    """
    with patch_reaction(0.2):
        timing = timing_from_presses(0.0, 5.0, 20.0)
    assert timing.slat_time == pytest.approx(4.8)
    assert timing.run_time == pytest.approx(19.8)


def test_presses_in_an_impossible_order_are_refused() -> None:
    """A press before the motor started, or a slat press after the shutter stopped.

    The flow offers the step again rather than fitting a negative run.
    """
    with pytest.raises(CalibrationError) as err:
        timing_from_presses(10.0, None, 9.0)
    assert err.value.reason == calibration.REASON_BAD_POINT
    with pytest.raises(CalibrationError, match="outside the run"):
        timing_from_presses(0.0, 25.0, 20.0)
    with pytest.raises(CalibrationError, match="outside the run"):
        timing_from_presses(10.0, 9.0, 20.0)


# --------------------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------------------
def test_a_fit_without_points_says_so() -> None:
    with pytest.raises(CalibrationError) as err:
        fit_direction(DIRECTION_CLOSE, [])
    assert err.value.reason == calibration.REASON_NO_POINTS


@pytest.mark.parametrize(
    ("point", "match"),
    [
        (FitPoint(fraction=0.5, measured_cm=10.0, height=0.0), "not a height"),
        (FitPoint(fraction=0.0, measured_cm=10.0, height=195.0), "outside"),
        (FitPoint(fraction=1.4, measured_cm=10.0, height=195.0), "outside"),
        (FitPoint(fraction=0.5, measured_cm=220.0, height=195.0), "curtain travel"),
        (FitPoint(fraction=0.5, measured_cm=-1.0, height=195.0), "curtain travel"),
    ],
)
def test_a_measurement_that_cannot_have_happened_is_refused(point: FitPoint, match: str) -> None:
    """Every refusal names the number that is wrong, because the user has to fix it.

    A bar measured above the travel is the commonest of these by far: it means the
    height was measured to the window and not to the curtain's own journey.
    """
    with pytest.raises(CalibrationError, match=match) as err:
        fit_direction(DIRECTION_CLOSE, [point])
    assert err.value.reason == calibration.REASON_BAD_POINT


def test_an_unknown_direction_is_refused() -> None:
    """The two equations are not interchangeable, so neither is the argument."""
    with pytest.raises(CalibrationError, match="not a direction"):
        fit_direction("sideways", _points(DIRECTION_CLOSE, 1.6, 1.0))


def test_the_error_carries_a_reason_for_the_flow_to_branch_on() -> None:
    """`CalibrationError` is a `HomeAssistantError` with a machine-readable reason.

    The flow of phase 2 turns the reason into a translation key; the message is for
    the log and for a service call.
    """
    err = CalibrationError(calibration.REASON_NO_ECHO, "the shutter never answered")
    assert err.reason == "no_echo"
    assert str(err) == "the shutter never answered"
    assert str(CalibrationError(calibration.REASON_BUSY)) == "busy"


# --------------------------------------------------------------------------------------
# The verification step
# --------------------------------------------------------------------------------------
def test_deviation_is_measured_against_the_model_as_it_stands() -> None:
    """Path B's check: run to a position, measure, and say how far off the estimate was.

    Positive means the shutter stopped higher than the model believed. The sign is
    what the flow's sentence is built on, so it is pinned here.
    """
    predicted = predict_cm(DIRECTION_CLOSE, 1.69, 1.0, 8.5 / 17.0, HEIGHT)
    assert calibration.deviation_cm(
        DIRECTION_CLOSE,
        roll=1.69,
        height=HEIGHT,
        run_time=CLOSING,
        slat_time=SLAT,
        motor_seconds=RUN_DOWN,
        measured_cm=predicted + 4.0,
    ) == pytest.approx(4.0)
    # An ascent is measured through its own equation, slat phase and all.
    up_predicted = predict_cm(DIRECTION_OPEN, 2.12, 1.0, 8.8 / 17.6, HEIGHT)
    assert calibration.deviation_cm(
        DIRECTION_OPEN,
        roll=2.12,
        height=HEIGHT,
        run_time=OPENING,
        slat_time=SLAT,
        motor_seconds=RUN_UP,
        measured_cm=up_predicted - 3.0,
    ) == pytest.approx(-3.0)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
class patch_reaction:  # noqa: N801 - a context manager used as one, not a class
    """Temporarily give `PRESS_REACTION_SEC` a value, the way a future release might."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self.previous = calibration.PRESS_REACTION_SEC

    def __enter__(self) -> None:
        calibration.PRESS_REACTION_SEC = self.seconds

    def __exit__(self, *exc: object) -> None:
        calibration.PRESS_REACTION_SEC = self.previous
