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
    closed = cover_module.calibration_descent_cm(roll, slat, HEIGHT, CLOSING)
    opened = cover_module.calibration_ascent_cm(roll, slat, HEIGHT, OPENING)
    found_roll, found_slat = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=closed,
        opened_half_cm=opened,
    )
    assert found_roll == pytest.approx(roll, abs=0.02)
    assert found_slat == pytest.approx(slat, abs=0.1)


def test_a_known_slat_time_leaves_a_one_dimensional_solve() -> None:
    """With the slat time given, the descent alone fixes the roll - exactly.

    The measurement of the reference shutter: 195 cm of travel, a 21.7 s closing run
    and a 4.7 s slat phase leave the bar 59 cm off the floor after half the run, and
    that is a roll of 1.69.

    Mutation caught: solving for the slat time anyway and ignoring the given value.
    """
    roll, slat = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=59.0,
        slat_time=4.7,
    )
    assert slat == 4.7
    assert roll == pytest.approx(1.69, abs=0.01)
    # A given slat time wins even when the ascent measurement is there too.
    roll_again, slat_again = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=59.0,
        opened_half_cm=120.0,
        slat_time=4.7,
    )
    assert (roll_again, slat_again) == (roll, slat)


def test_the_descent_ignores_the_slat_phase_and_the_ascent_does_not() -> None:
    """Why two measurements identify two unknowns, in one assertion.

    Closing from the top the slats only move once the curtain is already on the floor,
    so the whole half run is curtain; opening from the floor the *first* seconds are
    slats, so the same half run lifts the curtain less the longer the slat phase is.
    That asymmetry is the entire information content of the second measurement.

    Mutation caught: subtracting the slat time from the descent as well, which makes
    the pair of equations degenerate and the slat time unidentifiable.
    """
    descent = [cover_module.calibration_descent_cm(1.6, slat, HEIGHT, CLOSING) for slat in (0.0, 3.0, 6.0)]
    ascent = [cover_module.calibration_ascent_cm(1.6, slat, HEIGHT, OPENING) for slat in (0.0, 3.0, 6.0)]
    # The bar ends lower and lower in both cases, but not by the same amounts.
    assert descent[0] > descent[1] > descent[2]
    assert ascent[0] > ascent[1] > ascent[2]
    assert (descent[0] - descent[2]) != pytest.approx(ascent[0] - ascent[2], abs=1.0)


def test_a_measurement_outside_the_model_is_refused() -> None:
    """A bar that cannot be where it was measured gets an explanation, not a number.

    The band quoted in the message is the whole of what the model can produce, which is
    what lets the user work out which of the four numbers they gave is wrong.
    """
    with pytest.raises(ValueError, match="no shutter matches this measurement") as err:
        cover_module.solve_cover_calibration(
            height=HEIGHT,
            opening_time=OPENING,
            closing_time=CLOSING,
            closed_half_cm=185.0,
            slat_time=4.7,
        )
    # The reachable band with a 4.7 s slat phase, both ends named.
    assert "between 41 cm and 71 cm" in str(err.value)
    assert "closing_time is the real full run" in str(err.value)

    with pytest.raises(ValueError, match="no shutter matches"):
        cover_module.solve_cover_calibration(
            height=HEIGHT,
            opening_time=OPENING,
            closing_time=CLOSING,
            closed_half_cm=194.0,
            opened_half_cm=100.0,
        )


def test_the_yaml_snippet_is_a_complete_profile() -> None:
    """The answer has to be paste-able, not merely correct."""
    snippet = cover_module.calibration_yaml("hallway_shutter", HEIGHT, OPENING, CLOSING, 4.7, 1.6899)
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


async def test_calibration_run_drives_the_cover_and_reports_the_half_time(
    hass: HomeAssistant, tmp_path
) -> None:
    """`direction: close` opens fully first, then closes for half the closing run.

    The waits are what the user's stopwatch would see: the full opposite run plus three
    seconds of settling, then exactly half the run being measured before the stop.

    Mutation caught: waiting the *same* direction's run before starting (which measures
    from an unknown position), or halving the wrong direction's time.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML) as (_entry, commands):
        with patch.object(cover_module, "_async_sleep", new=AsyncMock()) as sleep:
            response = await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")

        assert commands.sent_frames == ["*2*1*81##", "*2*2*81##", "*2*0*81##"]
        # The opening run (22.3 s) plus the settle, then half the closing run (10.85 s).
        waits = [call.args[0] for call in sleep.await_args_list]
        assert waits[0] == pytest.approx(22.3 + cover_module.CALIBRATION_SETTLE_SEC)
        # The wait is measured from the moment the command went out, so it is the
        # half run minus however long the command path took.
        assert waits[1] == pytest.approx(21.7 / 2, abs=0.01)
        assert response == {
            ENTITY: {
                "direction": "close",
                # 10.85 s, rounded to one decimal for a human to read.
                "motor_seconds": 10.8,
                "opening_time": 22.3,
                "closing_time": 21.7,
            }
        }


async def test_calibration_run_open_is_the_mirror_image(hass: HomeAssistant, tmp_path) -> None:
    """`direction: open` closes fully first, then opens for half the opening run."""
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML) as (_entry, commands):
        with patch.object(cover_module, "_async_sleep", new=AsyncMock()) as sleep:
            response = await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="open")

        assert commands.sent_frames == ["*2*2*81##", "*2*1*81##", "*2*0*81##"]
        waits = [call.args[0] for call in sleep.await_args_list]
        assert waits[0] == pytest.approx(21.7 + cover_module.CALIBRATION_SETTLE_SEC)
        assert waits[1] == pytest.approx(22.3 / 2, abs=0.01)
        assert response[ENTITY]["motor_seconds"] == 11.2


async def test_calibration_is_refused_on_an_advanced_cover(hass: HomeAssistant, tmp_path) -> None:
    """An advanced actuator reports its real position: there is nothing to calibrate.

    Both services refuse it, and the message names the entity - a service call may
    target a whole area, and "one of your covers" would not be actionable.
    """
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        with pytest.raises(ServiceValidationError, match=ENTITY):
            await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")
        with pytest.raises(ServiceValidationError, match="no travel model to calibrate"):
            await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=59)
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

    59 cm after half the 21.7 s closing run of a 195 cm shutter with a 4.7 s slat phase
    is a roll of 1.69 - the cover's own configured times are the ones the run used, so
    they are the ones the equations are inverted against.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        response = await _call(
            hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=59, slat_time=4.7
        )
        result = response[ENTITY]
        assert result["roll"] == pytest.approx(1.69, abs=0.01)
        assert result["slat_time"] == 4.7
        assert result["opening_time"] == 22.3 and result["closing_time"] == 21.7
        assert result["height"] == 195.0
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
    closed = cover_module.calibration_descent_cm(2.4, 2.0, HEIGHT, CLOSING)
    opened = cover_module.calibration_ascent_cm(2.4, 2.0, HEIGHT, OPENING)
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


async def test_calibration_compute_falls_back_to_the_configured_slat_time(
    hass: HomeAssistant, tmp_path
) -> None:
    """Without the second measurement there is nothing to solve the slat time from.

    Mutation caught: solving for it anyway from the descent alone, where it trades off
    against the roll and any answer fits.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        result = (await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=59))[ENTITY]
        assert result["slat_time"] == 4.7


async def test_calibration_compute_rejects_impossible_measurements(hass: HomeAssistant, tmp_path) -> None:
    """A bar above the travel, or one no shutter could reach, is a measuring mistake."""
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        with pytest.raises(ServiceValidationError, match="above the curtain travel"):
            await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=200)
        with pytest.raises(ServiceValidationError, match="above the curtain travel"):
            await _call(
                hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=59, opened_half_cm=300
            )
        with pytest.raises(ServiceValidationError, match="no shutter matches this measurement"):
            await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=150)
