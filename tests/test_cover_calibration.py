"""Tests for the two cover calibration services (0.4.2).

The maths lives in pure module-level functions, so most of this file needs no Home
Assistant at all: the solver is fed measurements the model itself produced and has to
give the parameters back.  The two service tests then check the parts only the entity
can do - the order of the bus frames, the waits between them, and the refusals.

Since the 0.4.2 amendment there are two independent one-dimensional problems, one per
direction: the closing run measures `closing_roll`, the opening run `opening_roll`, and
`slat_time` is an input to both rather than an unknown (both runs are a position-50, so
they stop at the same point of the curtain's time axis whatever the slat time is - the
pair is not identifiable from them).
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.myhome import cover as cover_module
from custom_components.myhome.const import (
    CONF_ENTITY,
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
    ("closing_roll", "opening_roll", "slat"),
    [
        (1.0, 1.0, 0.0),
        (1.2, 1.2, 0.0),
        (1.69, 2.12, 4.7),
        (2.4, 1.3, 2.0),
        (3.5, 4.9, 6.5),
        (5.0, 1.0, 1.0),
    ],
)
def test_the_solver_recovers_the_roll_of_each_direction(
    closing_roll: float, opening_roll: float, slat: float
) -> None:
    """Round trip through the model: predict two measurements, then solve them back.

    This is the only honest test of a solver: anything else pins the answer of one
    particular implementation rather than the equations it is supposed to invert.  The
    two directions are deliberately given different rolls, including the two extremes
    of the range, so a solver that shared one number between them could not pass.

    Mutation caught: any sign or scaling error in `calibration_descent_cm` /
    `calibration_ascent_cm`, and solving the ascent with the descent's equation.
    """
    closed = cover_module.calibration_descent_cm(closing_roll, slat, HEIGHT, CLOSING, RUN_DOWN)
    opened = cover_module.calibration_ascent_cm(opening_roll, slat, HEIGHT, OPENING, RUN_UP)
    found_closing, found_opening = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=closed,
        closed_run_seconds=RUN_DOWN,
        opened_run_seconds=RUN_UP,
        opened_half_cm=opened,
        slat_time=slat,
    )
    assert found_closing == pytest.approx(closing_roll, abs=0.02)
    assert found_opening == pytest.approx(opening_roll, abs=0.02)


def test_the_real_shutter_gives_one_roll_per_direction() -> None:
    """The measurements of the reference window: 85 cm down, 80 cm up.

    195 cm of travel, 8.5 s of motor down (half the 17 s curtain time of a 21.7 s
    closing run with a 4.7 s slat phase) leave the bar 85 cm off the floor, which is a
    closing roll of 1.69 - the sanity value of the specification's section 1, since
    half the curtain time ends at x = (3k+1)/(4(k+1)).  The same shutter measured
    upwards stops 80 cm off the floor, five centimetres lower, and that is an opening
    roll of 2.12: the motor is not equally loaded the two ways.

    Before the amendment this pair had no solution at all - one roll plus an unknown
    slat time predicts (almost) the same height both ways, so 85/80 was refused.  Two
    rolls is what makes the real data solvable.

    Mutation caught: feeding both measurements to the descent equation, which would
    answer 1.87 for the ascent instead of 2.12.
    """
    closing_roll, opening_roll = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=85.0,
        closed_run_seconds=RUN_DOWN,
        opened_run_seconds=RUN_UP,
        opened_half_cm=80.0,
        slat_time=SLAT,
    )
    assert closing_roll == pytest.approx(1.69, abs=0.02)
    assert 2.0 <= opening_roll <= 2.2
    # Both are exact solutions of their own equation, not a compromise between them.
    assert cover_module.calibration_descent_cm(
        closing_roll, SLAT, HEIGHT, CLOSING, RUN_DOWN
    ) == pytest.approx(85.0, abs=0.05)
    assert cover_module.calibration_ascent_cm(
        opening_roll, SLAT, HEIGHT, OPENING, RUN_UP
    ) == pytest.approx(80.0, abs=0.05)


def test_without_the_opening_measurement_only_the_closing_roll_is_answered() -> None:
    """One run, one roll: nothing is invented for the direction nobody measured.

    Mutation caught: defaulting the opening roll to the closing one inside the solver,
    which would publish a measured-looking number that was never measured.
    """
    closing_roll, opening_roll = cover_module.solve_cover_calibration(
        height=HEIGHT,
        opening_time=OPENING,
        closing_time=CLOSING,
        closed_half_cm=85.0,
        closed_run_seconds=RUN_DOWN,
        opened_run_seconds=RUN_UP,
        slat_time=SLAT,
    )
    assert closing_roll == pytest.approx(1.69, abs=0.02)
    assert opening_roll is None


def test_the_two_runs_stop_at_the_same_place_whatever_the_slat_time_is() -> None:
    """Why `slat_time` is an input and not an unknown (the amendment's finding).

    Both calibration runs are a `set_cover_position: 50` expressed in motor seconds, so
    the descent fraction and the ascent-equivalent fraction are the same function of
    the slat time - exactly 0.5 at the configured value and within a centimetre of each
    other everywhere else.  A single shutter therefore predicts the same height both
    ways for *every* slat time, which is precisely why the pair (roll, slat_time)
    cannot be recovered from these two measurements, and why the amendment spends the
    second measurement on the second roll instead.

    Mutation caught: reintroducing a slat-time sweep, which has nothing to walk on.
    """
    for slat in (0.0, 3.0, 4.7, 6.0):
        down = cover_module.calibration_descent_cm(1.6, slat, HEIGHT, CLOSING, RUN_DOWN)
        up = cover_module.calibration_ascent_cm(1.6, slat, HEIGHT, OPENING, RUN_UP)
        assert abs(down - up) < 1.0
    # At the configured slat time the two runs are the same movement mirrored, so the
    # two predictions coincide.
    assert cover_module.calibration_descent_cm(
        1.6, SLAT, HEIGHT, CLOSING, RUN_DOWN
    ) == pytest.approx(cover_module.calibration_ascent_cm(1.6, SLAT, HEIGHT, OPENING, RUN_UP))


def test_a_measurement_outside_the_model_is_refused() -> None:
    """A bar that cannot be where it was measured gets an explanation, not a number.

    The band quoted in the message is the whole of what the model can produce, which is
    what lets the user work out which of the numbers they gave is wrong.  After 8.5 s
    of the reference shutter's closing run the bar is between 65 cm (the fattest roll)
    and 98 cm (the linear one) off the floor, and nothing else; the upward run of the
    same shutter has the same band, because both are a position-50.

    Mutation caught: refusing silently, or quoting the band of the other direction.
    """
    with pytest.raises(ValueError, match="no roll matches closed_half_cm") as err:
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
    assert "8.5 s of a 21.7 s closing run started fully open" in str(err.value)
    assert "closing_time and slat_time are the real numbers" in str(err.value)

    # The ascent is refused on its own terms, and names its own field and run.
    with pytest.raises(ValueError, match="no roll matches opened_half_cm") as err:
        cover_module.solve_cover_calibration(
            height=HEIGHT,
            opening_time=OPENING,
            closing_time=CLOSING,
            closed_half_cm=85.0,
            closed_run_seconds=RUN_DOWN,
            opened_run_seconds=RUN_UP,
            opened_half_cm=20.0,
            slat_time=SLAT,
        )
    assert "13.5 s of a 22.3 s opening run started fully closed" in str(err.value)
    assert "opening_time and slat_time are the real numbers" in str(err.value)


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


def test_the_snippet_writes_two_rolls_only_when_they_differ() -> None:
    """One key when the two runs agree, two when they do not - and never all three.

    A `roll:` next to a directional pair would be a third number the user has to keep
    in step with the other two, and it would be the one key that no run measured.

    Mutation caught: always writing the mean, or always writing both.
    """
    together = cover_module.calibration_yaml(
        "hallway_shutter", HEIGHT, OPENING, CLOSING, SLAT, 1.69, 1.75
    )
    assert "    roll: 1.72" in together  # the mean of the two
    assert "opening_roll" not in together and "closing_roll" not in together

    apart = cover_module.calibration_yaml("hallway_shutter", HEIGHT, OPENING, CLOSING, SLAT, 1.69, 2.12)
    assert "    opening_roll: 2.12" in apart
    assert "    closing_roll: 1.69" in apart
    assert "\n    roll:" not in apart


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


async def test_calibration_compute_returns_the_closing_roll(hass: HomeAssistant, tmp_path) -> None:
    """One measurement, one answer: the closing roll and the YAML to paste.

    85 cm after the 8.5 s closing run of a 195 cm shutter with a 4.7 s slat phase is a
    roll of 1.69 - and the 8.5 s are re-derived from the cover's own configuration, the
    same way `cover_calibration_run` derived them, so the user carries nothing but the
    tape measure between the two calls.  `opening_roll` is absent, because no opening
    run was measured; `roll` is the closing one, which is the only one there is.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        response = await _call(
            hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85, slat_time=4.7
        )
        result = response[ENTITY]
        assert result["closing_roll"] == pytest.approx(1.69, abs=0.02)
        assert "opening_roll" not in result
        assert result["roll"] == result["closing_roll"]
        assert result["slat_time"] == 4.7
        assert result["opening_time"] == 22.3 and result["closing_time"] == 21.7
        assert result["height"] == 195.0
        # The run lengths the equations were inverted against, echoed back.
        assert result["closed_run_seconds"] == 8.5
        assert result["opened_run_seconds"] == 13.5
        assert "cover_profiles:" in result["yaml"]
        assert "  hallway_shutter:" in result["yaml"]
        assert f"roll: {result['roll']}" in result["yaml"]


async def test_calibration_compute_answers_two_rolls_for_the_real_shutter(
    hass: HomeAssistant, tmp_path
) -> None:
    """The 85 / 80 pair, end to end: two rolls and a snippet that carries both.

    This is the acceptance case of the amendment.  The same pair used to be refused as
    "not one shutter", because one roll and an unknown slat time cannot produce two
    different heights; read as one roll per direction it is an ordinary measurement of
    a motor that is not equally loaded up and down.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        result = (
            await _call(
                hass,
                SERVICE_COVER_CALIBRATION_COMPUTE,
                height=195,
                closed_half_cm=85,
                opened_half_cm=80,
            )
        )[ENTITY]
        assert result["closing_roll"] == pytest.approx(1.69, abs=0.02)
        assert 2.0 <= result["opening_roll"] <= 2.2
        # `roll` is the mean, for a user who wants one number and can live with it.
        assert result["roll"] == pytest.approx(
            (result["closing_roll"] + result["opening_roll"]) / 2, abs=0.01
        )
        # The two are far apart, so the snippet keeps them apart.
        assert f"opening_roll: {result['opening_roll']}" in result["yaml"]
        assert f"closing_roll: {result['closing_roll']}" in result["yaml"]
        assert "\n    roll:" not in result["yaml"]
        # The slat time was not given, so the cover's own configured value was used.
        assert result["slat_time"] == 4.7


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
        assert stated["closing_roll"] == pytest.approx(1.69, abs=0.02)
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
        assert longer["closing_roll"] < stated["closing_roll"]


async def test_calibration_compute_falls_back_to_the_configured_slat_time(
    hass: HomeAssistant, tmp_path
) -> None:
    """`slat_time` is never solved for: given it is trusted, otherwise it is read.

    Mutation caught: solving for it from the descent, where it trades off against the
    roll and any answer fits.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        configured = (await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85))[
            ENTITY
        ]
        assert configured["slat_time"] == 4.7
        given = (
            await _call(
                hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85, slat_time=2.0
            )
        )[ENTITY]
        assert given["slat_time"] == 2.0
        # A shorter slat phase means a longer curtain run, so the same 8.5 s cover less
        # of it: the bar ends higher for the same roll, and the solved roll is bigger.
        assert given["closing_roll"] > configured["closing_roll"]


async def test_calibration_compute_rejects_impossible_measurements(hass: HomeAssistant, tmp_path) -> None:
    """A bar above the travel, or one no roll could reach, is a measuring mistake."""
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        with pytest.raises(ServiceValidationError, match="above the curtain travel"):
            await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=200)
        with pytest.raises(ServiceValidationError, match="above the curtain travel"):
            await _call(
                hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85, opened_half_cm=300
            )
        with pytest.raises(ServiceValidationError, match="no roll matches closed_half_cm"):
            await _call(hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=150)
        with pytest.raises(ServiceValidationError, match="no roll matches opened_half_cm"):
            await _call(
                hass, SERVICE_COVER_CALIBRATION_COMPUTE, height=195, closed_half_cm=85, opened_half_cm=20
            )


# --------------------------------------------------------------------------------------
# The run is timed on the bus, not on the command queue (0.4.3)
# --------------------------------------------------------------------------------------
class CommandPath:
    """A command path that can make a class of frames slow, or lose it entirely.

    `MyHOMEGatewayHandler.send` only queues; what the calibration has to time is the
    write, so this stand-in reports the write through the delivery callback and can
    hold a frame back (`slow_prefix`, which costs `delay` seconds of the frozen clock
    before the write), give up on it (`drop_prefix`) or never answer at all
    (`silent`).
    """

    def __init__(
        self,
        freezer: FrozenDateTimeFactory | None = None,
        *,
        slow_prefix: str | None = None,
        delay: float = 0.0,
        drop_prefix: str | None = None,
        silent: bool = False,
    ) -> None:
        self.freezer = freezer
        self.slow_prefix = slow_prefix
        self.delay = delay
        self.drop_prefix = drop_prefix
        self.silent = silent
        self.frames: list[str] = []

    async def send(self, message: Any, *, on_delivered: Any = None, on_dropped: Any = None) -> bool:
        frame = str(message)
        self.frames.append(frame)
        if self.silent:
            # Queued, and then nothing at all: no write, no drop, no answer.
            return True
        if self.drop_prefix is not None and frame.startswith(self.drop_prefix):
            # Queued, then abandoned: the TTL expired, or the gateway never answered.
            if on_dropped is not None:
                on_dropped()
            return True
        if self.freezer is not None and self.slow_prefix is not None and frame.startswith(self.slow_prefix):
            self.freezer.tick(timedelta(seconds=self.delay))
        if on_delivered is not None:
            on_delivered(time.monotonic())
        return True


async def test_the_calibration_run_reports_the_time_the_motor_really_ran(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`motor_seconds` is the interval between the two writes, not the one we asked for.

    The user measures the bar with a tape and hands the number back to
    `cover_calibration_compute`, which inverts the model against exactly these
    seconds. If the stop waited four tenths of a second in the command queue, the
    motor ran for 8.9 s and the measurement belongs to 8.9 s: reporting the 8.5 s that
    were *intended* would push the error straight into the computed roll.

    Mutation caught: reporting the planned `motor_seconds` (the 0.4.2 shape).
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        path = CommandPath(freezer, slow_prefix="*2*0*", delay=0.4)

        async def _sleep(seconds: float) -> None:
            freezer.tick(timedelta(seconds=seconds))

        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", _sleep),
        ):
            response = await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")

        assert path.frames == ["*2*1*81##", "*2*2*81##", "*2*0*81##"]
        assert response[ENTITY]["motor_seconds"] == pytest.approx(RUN_DOWN + 0.4)


async def test_the_calibration_run_fails_when_the_movement_never_reaches_the_bus(
    hass: HomeAssistant, tmp_path
) -> None:
    """Nothing moved, so there is nothing to measure and nothing to report.

    A run that answered with the numbers it planned would send the user off to
    measure a shutter that never left its end stop.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        path = CommandPath(drop_prefix="*2*2*")
        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", new=AsyncMock()),
            pytest.raises(HomeAssistantError, match="did not start moving"),
        ):
            await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")
        assert path.frames == ["*2*1*81##", "*2*2*81##"]


async def test_the_calibration_run_fails_when_the_stop_never_reaches_the_bus(
    hass: HomeAssistant, tmp_path
) -> None:
    """The shutter runs on to its end stop: the half run the user should measure is gone."""
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        path = CommandPath(drop_prefix="*2*0*")
        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", new=AsyncMock()),
            pytest.raises(HomeAssistantError, match="never stopped"),
        ):
            await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")
        assert path.frames == ["*2*1*81##", "*2*2*81##", "*2*0*81##"]


async def test_the_calibration_run_gives_up_when_the_gateway_stops_answering(
    hass: HomeAssistant, tmp_path
) -> None:
    """A frame that is neither written nor abandoned must not park the service for ever.

    The wait is bounded by the command path's own worst case for one frame
    (`command_budget`), squeezed to a few milliseconds here; past it the run says what
    it knows, which is that it never saw the movement start.
    """
    async with setup_myhome(hass, tmp_path, CALIBRATION_YAML):
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        handler.connect_timeout = 0.001
        handler.command_timeout = 0.001
        silent = CommandPath(silent=True)

        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", silent.send),
            patch.object(cover_module, "_async_sleep", new=AsyncMock()),
            pytest.raises(HomeAssistantError, match="did not start moving"),
        ):
            await _call(hass, SERVICE_COVER_CALIBRATION_RUN, direction="close")
        assert silent.frames == ["*2*1*81##", "*2*2*81##"]
