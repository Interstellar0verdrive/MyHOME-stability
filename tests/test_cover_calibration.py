"""Tests for the two cover calibration services (0.4.2).

The maths lives in pure module-level functions, so most of this file needs no Home
Assistant at all: the solver is fed measurements the model itself produced and has to
give the parameters back.  The two service tests then check the parts only the entity
can do - the order of the bus frames, the waits between them, and the two refusals.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.myhome import cover as cover_module
from custom_components.myhome.const import (
    DOMAIN,
    SERVICE_COVER_CALIBRATION_COMPUTE,
    SERVICE_COVER_CALIBRATION_RUN,
)

from .helpers_core import MAC
from .helpers_platforms import setup_myhome

# A shutter measured on a real window: 195 cm of travel, an asymmetric run and a slat
# phase.  The numbers are the ones the 0.4.2 specification works its example with.
CALIBRATION_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      opening_time: 22.3
      closing_time: 21.7
      slat_time: 4.7
      roll: 1.69
      height: 195
"""

ADVANCED_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      advanced: true
"""

ENTITY = "cover.hallway_shutter"
HEIGHT = 195.0
OPENING = 22.3
CLOSING = 21.7
SLAT = 4.7
# The motor seconds a `set_cover_position: 50` spends on this cover, which is exactly
# what `cover_calibration_run` reproduces: all curtain on the way down from the top,
# the slat phase plus half the curtain on the way up from the floor.
RUN_DOWN = (CLOSING - SLAT) / 2  # 8.5 s
RUN_UP = SLAT + (OPENING - SLAT) / 2  # 13.5 s


# --------------------------------------------------------------------------------------
# The two run lengths
# --------------------------------------------------------------------------------------
def test_the_run_reproduces_a_set_cover_position_50() -> None:
    """The calibration run is not "half the run": it is the position-50 motor time.

    Down from the top the slats never move, so half the *curtain* time is the whole
    movement; up from the floor the slats are opened first and only then does half the
    curtain time follow.  Getting this wrong is what makes the measured height
    impossible to invert: the compute step re-derives these very numbers.

    Mutation caught: halving `closing_time` / `opening_time` instead of the curtain
    time, or forgetting the slat phase on the way up.
    """
    assert cover_module.calibration_close_run_seconds(CLOSING, SLAT) == pytest.approx(8.5)
    assert cover_module.calibration_open_run_seconds(OPENING, SLAT) == pytest.approx(13.5)
    # Without a slat phase the two are simply half of each run.
    assert cover_module.calibration_close_run_seconds(20.0, 0.0) == 10.0
    assert cover_module.calibration_open_run_seconds(20.0, 0.0) == 10.0


# --------------------------------------------------------------------------------------
# The solver, on its own
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("roll", "slat"),
    [(1.0, 0.0), (1.2, 0.0), (1.69, 4.7), (1.7, 4.7), (2.4, 2.0), (3.5, 6.5), (5.0, 1.0)],
)
def test_the_solver_recovers_the_parameters_it_was_given(roll: float, slat: float) -> None:
    """Round trip through the model: predict two measurements, then solve them back.

    This is the only honest test of a solver: anything else pins the answer of one
    particular implementation rather than the equation it is supposed to invert.

    Mutation caught: any sign or scaling error in `calibration_descent_cm` /
    `calibration_ascent_cm` that the two directions do not share.
    """
    closed = cover_module.calibration_descent_cm(roll, slat, HEIGHT, CLOSING, RUN_DOWN)
    opened = cover_module.calibration_ascent_cm(roll, slat, HEIGHT, OPENING, RUN_UP)
    found_roll, found_slat = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=closed,
        closed_run_seconds=RUN_DOWN,
        opened_run_seconds=RUN_UP,
        opened_half_cm=opened,
    )
    assert found_roll == pytest.approx(roll, abs=0.02)
    assert found_slat == pytest.approx(slat, abs=0.1)


def test_a_known_slat_time_leaves_a_one_dimensional_solve() -> None:
    """With the slat time given, the descent alone fixes the roll - exactly.

    The measurement of the reference shutter: 195 cm of travel, 8.5 s of motor (half
    the 17 s curtain time of a 21.7 s closing run with a 4.7 s slat phase) leave the bar
    85 cm off the floor, and that is a roll of 1.69.  It is the sanity value of the
    specification's section 1 - half the curtain time ends at x = (3k+1)/(4(k+1)) - so
    the run length and the equation really do describe the same movement.

    Mutation caught: solving for the slat time anyway and ignoring the given value.
    """
    roll, slat = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=85.0,
        closed_run_seconds=RUN_DOWN,
        opened_run_seconds=RUN_UP,
        slat_time=SLAT,
    )
    assert slat == SLAT
    assert roll == pytest.approx(1.69, abs=0.02)
    # A given slat time wins even when the ascent measurement is there too.
    roll_again, slat_again = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=85.0,
        closed_run_seconds=RUN_DOWN,
        opened_run_seconds=RUN_UP,
        opened_half_cm=120.0,
        slat_time=SLAT,
    )
    assert (roll_again, slat_again) == (roll, slat)


def test_the_descent_ignores_the_slat_phase_and_the_ascent_does_not() -> None:
    """Why two measurements can identify two unknowns at all - and how weakly.

    Closing from the top the slats only move once the curtain is already on the floor,
    so the whole run is curtain; opening from the floor the *first* seconds are slats,
    so the same run lifts the curtain less the longer the slat phase is.  That
    asymmetry is the entire information content of the second measurement.

    It is also very small, and the assertion says so on purpose: with the run lengths
    the service itself uses, both halves stop the bar within a centimetre of each other
    whatever the slat time is, which is why measurements that disagree by more are
    refused rather than fitted (`CALIBRATION_MAX_ASCENT_RESIDUAL_CM`).

    Mutation caught: subtracting the slat time from the descent as well, which makes
    the pair of equations degenerate and the slat time unidentifiable.
    """
    descent = [cover_module.calibration_descent_cm(1.6, s, HEIGHT, CLOSING, RUN_DOWN) for s in (0.0, 3.0, 6.0)]
    ascent = [cover_module.calibration_ascent_cm(1.6, s, HEIGHT, OPENING, RUN_UP) for s in (0.0, 3.0, 6.0)]
    # The bar ends lower and lower in both cases, but not by the same amounts.
    assert descent[0] > descent[1] > descent[2]
    assert ascent[0] > ascent[1] > ascent[2]
    assert (descent[0] - descent[2]) != pytest.approx(ascent[0] - ascent[2], abs=0.5)
    # ...and the two predictions themselves never part company by much.
    for down, up in zip(descent, ascent, strict=True):
        assert abs(down - up) < cover_module.CALIBRATION_MAX_ASCENT_RESIDUAL_CM


def test_a_measurement_outside_the_model_is_refused() -> None:
    """A bar that cannot be where it was measured gets an explanation, not a number.

    The band quoted in the message is the whole of what the model can produce, which is
    what lets the user work out which of the four numbers they gave is wrong.  After
    8.5 s of the reference shutter's closing run the bar is between 65 cm (the fattest
    roll) and 98 cm (the linear one) off the floor, and nothing else.
    """
    with pytest.raises(ValueError, match="no shutter matches this measurement") as err:
        cover_module.solve_cover_calibration(
            height=HEIGHT,
            opening_time=OPENING,
            closing_time=CLOSING,
            closed_half_cm=150.0,
            closed_run_seconds=RUN_DOWN,
            opened_run_seconds=RUN_UP,
            slat_time=SLAT,
        )
    assert "between 65 cm and 98 cm" in str(err.value)
    assert "closing_time is the real full run" in str(err.value)

    # No slat time at all can put the bar 194 cm up after 8.5 s of closing.
    with pytest.raises(ValueError, match="no shutter matches"):
        cover_module.solve_cover_calibration(
            height=HEIGHT,
            opening_time=OPENING,
            closing_time=CLOSING,
            closed_half_cm=194.0,
            closed_run_seconds=RUN_DOWN,
            opened_run_seconds=RUN_UP,
            opened_half_cm=100.0,
        )


def test_two_measurements_that_disagree_are_refused_rather_than_fitted() -> None:
    """The real pair measured on the reference shutter: 85 cm down, 80 cm up.

    Both runs stop at the same point of the curtain's time axis, so one shutter must
    leave the bar at the same height both ways: the model can spread the two
    predictions by less than a centimetre over the whole range of slat times.  Five
    centimetres apart is therefore not a shutter with an unusual roll, it is a
    measurement or a configured run that is wrong - and the best fit of it is a `roll`
    pushed against the end of its range, which pasted into the YAML would be worse than
    no answer at all.

    Mutation caught: dropping the residual check and returning the boundary fit.
    """
    with pytest.raises(ValueError, match="do not describe one shutter") as err:
        cover_module.solve_cover_calibration(
            height=HEIGHT,
            opening_time=OPENING,
            closing_time=CLOSING,
            closed_half_cm=85.0,
            closed_run_seconds=RUN_DOWN,
            opened_run_seconds=RUN_UP,
            opened_half_cm=80.0,
        )
    assert "80 cm was measured" in str(err.value)
    assert "give the slat_time" in str(err.value)


def test_the_yaml_snippet_is_a_complete_profile() -> None:
    """The answer has to be paste-able, not merely correct."""
    snippet = cover_module.calibration_yaml("hallway_shutter", HEIGHT, OPENING, CLOSING, SLAT, 1.6899)
    assert "cover_profiles:" in snippet
    assert "  hallway_shutter:" in snippet
    assert "    reference_height: 195.0" in snippet
    assert "    opening_time: 22.3" in snippet
    assert "    closing_time: 21.7" in snippet
    assert "    slat_time: 4.7" in snippet
    # Rounded to two decimals: a third one says more than any tape measure can.
    assert "    roll: 1.69" in snippet
    assert "    profile: hallway_shutter" in snippet
    assert "    height: 195.0" in snippet


# --------------------------------------------------------------------------------------
# The two services
# --------------------------------------------------------------------------------------
async def _call(hass: HomeAssistant, service: str, **data: Any) -> dict:
    return await hass.services.async_call(
        DOMAIN, service, {ATTR_ENTITY_ID: ENTITY, **data}, blocking=True, return_response=True
    )


async def test_calibration_run_drives_the_cover_and_reports_the_motor_time(
    hass: HomeAssistant, tmp_path
) -> None:
    """`direction: close` opens fully first, then closes for half the curtain time.

    The waits are what the user's stopwatch would see: the full opposite run plus three
    seconds of settling, then exactly the position-50 motor time before the stop.

    Mutation caught: waiting the *same* direction's run before starting (which measures
    from an unknown position), halving the wrong direction's time, or halving the full
    run instead of the curtain time.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML) as (_entry, commands):
        with patch.object(cover_module, "_async_sleep", new=AsyncMock()) as sleep:
            response = await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")

        assert commands.sent_frames == ["*2*1*81##", "*2*2*81##", "*2*0*81##"]
        # The opening run (22.3 s) plus the settle, then (21.7 - 4.7) / 2 = 8.5 s.
        waits = [call.args[0] for call in sleep.await_args_list]
        assert waits[0] == pytest.approx(22.3 + cover_module.CALIBRATION_SETTLE_SEC)
        # The wait is measured from the moment the command went out, so it is the
        # motor time minus however long the command path took.
        assert waits[1] == pytest.approx(8.5, abs=0.01)
        assert response == {
            ENTITY: {
                "direction": "close",
                "motor_seconds": 8.5,
                "opening_time": 22.3,
                "closing_time": 21.7,
                "slat_time": 4.7,
            }
        }


async def test_calibration_run_open_spends_the_slat_phase_first(hass: HomeAssistant, tmp_path) -> None:
    """`direction: open` closes fully first, then opens for slat + half the curtain.

    4.7 s of slats and 8.8 s of curtain: 13.5 s, not half of the 22.3 s opening run.
    The asymmetry with the closing direction is the whole point - it is what makes the
    two measurements say different things.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML) as (_entry, commands):
        with patch.object(cover_module, "_async_sleep", new=AsyncMock()) as sleep:
            response = await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="open")

        assert commands.sent_frames == ["*2*2*81##", "*2*1*81##", "*2*0*81##"]
        waits = [call.args[0] for call in sleep.await_args_list]
        assert waits[0] == pytest.approx(21.7 + cover_module.CALIBRATION_SETTLE_SEC)
        assert waits[1] == pytest.approx(13.5, abs=0.01)
        assert response[ENTITY]["motor_seconds"] == 13.5
        assert response[ENTITY]["slat_time"] == 4.7


async def test_calibration_is_refused_on_an_advanced_cover(hass: HomeAssistant, tmp_path) -> None:
    """An advanced actuator reports its real position: there is nothing to calibrate.

    Both services refuse it, and the message names the entity - a service call may
    target a whole area, and "one of your covers" would not be actionable.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        with pytest.raises(ServiceValidationError, match=ENTITY):
            await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")
        with pytest.raises(ServiceValidationError, match="no travel model to calibrate"):
            await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85)
        assert commands.sent_frames == []


async def test_calibration_run_is_refused_while_the_cover_moves(hass: HomeAssistant, tmp_path) -> None:
    """A run that starts half way up measures nothing."""
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML) as (_entry, commands):
        await hass.services.async_call(COVER, "open_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        commands.clear()
        with pytest.raises(ServiceValidationError, match="already moving"):
            await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")
        assert commands.sent_frames == []


async def test_calibration_compute_returns_the_profile(hass: HomeAssistant, tmp_path) -> None:
    """The whole answer: the two solved values, the residuals and the YAML to paste.

    85 cm after the 8.5 s closing run of a 195 cm shutter with a 4.7 s slat phase is a
    roll of 1.69 - and the 8.5 s are re-derived from the cover's own configuration, the
    same way `cover_calibration_run` derived them, so the user carries nothing but the
    tape measure between the two calls.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        response = await _call(
            hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85, slat_time=4.7
        )
        result = response[ENTITY]
        assert result["roll"] == pytest.approx(1.69, abs=0.02)
        assert result["slat_time"] == 4.7
        assert result["opening_time"] == 22.3 and result["closing_time"] == 21.7
        assert result["height"] == 195.0
        # The run lengths the equations were inverted against, echoed back.
        assert result["closed_run_seconds"] == 8.5
        assert result["opened_run_seconds"] == 13.5
        # Solved, so the descent residual is zero; the ascent was not measured.
        assert result["residual_cm"] == {"closed_half_cm": 0.0}
        assert "cover_profiles:" in result["yaml"]
        assert "  hallway_shutter:" in result["yaml"]
        assert f"roll: {result['roll']}" in result["yaml"]


async def test_calibration_compute_uses_both_measurements_when_given(hass: HomeAssistant, tmp_path) -> None:
    """With both halves measured the slat time is solved for instead of assumed.

    The measurements below are what a shutter with roll 2.4 and a 2 s slat phase would
    produce, which is neither the configured roll (1.69) nor the configured slat time
    (4.7): the answer has to come from the numbers, not from the configuration.
    """
    closed = cover_module.calibration_descent_cm(2.4, 2.0, HEIGHT, CLOSING, RUN_DOWN)
    opened = cover_module.calibration_ascent_cm(2.4, 2.0, HEIGHT, OPENING, RUN_UP)
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        result = (
            await _call(
                hass,
                SERVICE_COVER_CALIBRATION_COMPUTE,
                height=195,
                closed_half_cm=closed,
                opened_half_cm=opened,
            )
        )[ENTITY]
        assert result["roll"] == pytest.approx(2.4, abs=0.02)
        assert result["slat_time"] == pytest.approx(2.0, abs=0.1)
        assert set(result["residual_cm"]) == {"closed_half_cm", "opened_half_cm"}
        assert abs(result["residual_cm"]["opened_half_cm"]) <= 0.5


async def test_calibration_compute_accepts_the_measured_run_lengths(hass: HomeAssistant, tmp_path) -> None:
    """The two run lengths default to the configuration but can be overridden.

    A user who edited `slat_time:` between the run and the compute (or who timed the
    motor by hand) would otherwise invert a movement that never happened.

    Mutation caught: ignoring the fields and always recomputing from the cover.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        stated = (
            await _call(
                hass,
                SERVICE_COVER_CALIBRATION_COMPUTE,
                height=195,
                closed_half_cm=85,
                slat_time=4.7,
                closed_run_seconds=8.5,
                opened_run_seconds=13.5,
            )
        )[ENTITY]
        assert stated["roll"] == pytest.approx(1.69, abs=0.02)
        # A longer run reaching the same height means a slower, i.e. straighter, tube.
        longer = (
            await _call(
                hass,
                SERVICE_COVER_CALIBRATION_COMPUTE,
                height=195,
                closed_half_cm=85,
                slat_time=4.7,
                closed_run_seconds=9.5,
            )
        )[ENTITY]
        assert longer["closed_run_seconds"] == 9.5
        assert longer["roll"] < stated["roll"]


async def test_calibration_compute_falls_back_to_the_configured_slat_time(
    hass: HomeAssistant, tmp_path
) -> None:
    """Without the second measurement there is nothing to solve the slat time from.

    Mutation caught: solving for it anyway from the descent alone, where it trades off
    against the roll and any answer fits.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        result = (await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85))[ENTITY]
        assert result["slat_time"] == 4.7


async def test_calibration_compute_rejects_impossible_measurements(hass: HomeAssistant, tmp_path) -> None:
    """A bar above the travel, or one no shutter could reach, is a measuring mistake."""
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        with pytest.raises(ServiceValidationError, match="above the curtain travel"):
            await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=200)
        with pytest.raises(ServiceValidationError, match="above the curtain travel"):
            await _call(
                hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85, opened_half_cm=300
            )
        with pytest.raises(ServiceValidationError, match="no shutter matches this measurement"):
            await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=150)
        # The real pair measured on this shutter: 5 cm apart, which one shutter cannot do.
        with pytest.raises(ServiceValidationError, match="do not describe one shutter"):
            await _call(
                hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85, opened_half_cm=80
            )
