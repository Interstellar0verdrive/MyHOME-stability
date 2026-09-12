"""Tests for the cover runner of the guided calibration (0.5.0, spec 1.2).

The four primitives `MyHOMECover` gained - home, start, stop, run a fraction - are what
the config subentry flow of phase 2 drives a shutter with. They are timed on the bus,
not on the clock of whoever called them: a frame reaches the bus when the gateway says
it did (0.4.3) and the motor turns when the actuator says it does (0.4.4), and a guided
step that measured anything else would hand the fit seconds the shutter never spent.

`GuidedPath` below is a gateway that behaves: it writes what it is given, and the
actuator answers it on the monitor session a fraction of a second later, exactly as the
reference MyHOMEServer1 does. The frozen clock only ever moves where a real one would -
inside a wait, or between a frame and its answer.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import ATTR_POSITION, DOMAIN as COVER, CoverState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
from OWNd.message import OWNEvent
from pytest_homeassistant_custom_component.common import async_fire_time_changed, mock_restore_cache

from custom_components.myhome import cover as cover_module
from custom_components.myhome.calibration import (
    REASON_ADVANCED,
    REASON_BUSY,
    REASON_NO_ECHO,
    REASON_NOT_DELIVERED,
    REASON_NOT_STOPPED,
    CalibrationError,
)
from custom_components.myhome.const import ATTR_CALIBRATING, DIRECTION_CLOSE, DIRECTION_OPEN

from .helpers_core import MAC
from .helpers_platforms import entity_object, setup_myhome

# The reference window again (195 cm, 4.7 s of slats, an asymmetric run), so the
# seconds below can be read against the two services' own tests.
RUNNER_YAML = f"""
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
DEVICE_KEY = "2-81"
OPENING = 22.3
CLOSING = 21.7
SLAT = 4.7
CURTAIN_DOWN = CLOSING - SLAT  # 17.0 s
CURTAIN_UP = OPENING - SLAT  # 17.6 s
# What the bus costs, read off the entity's own defaults.
START_DELAY_SEC = cover_module.DEFAULT_START_DELAY
STOP_LATENCY_SEC = cover_module.DEFAULT_STOP_LATENCY
# How long the actuator takes to answer, on the installation 0.4.4 was measured on.
MOTOR_ECHO_SEC = 0.55
STOP_ECHO_SEC = STOP_LATENCY_SEC

RAISE = "*2*1*81##"
LOWER = "*2*2*81##"
STOP = "*2*0*81##"
MOVING_UP = "*2*1*81##"
MOVING_DOWN = "*2*2*81##"
STOPPED = "*2*0*81##"


class GuidedPath:
    """A gateway that writes every frame at once and an actuator that answers it.

    `send` reports the write through the delivery callback, as the handler does, and
    remembers what the actuator owes in answer: its own "moving" status `moving_after`
    seconds after a direction frame, its own "stopped" `stopped_after` seconds after a
    stop. Those answers are delivered either inside a wait (`sleep`, the way a real one
    arrives in the middle of a run) or at the next turn of the event loop, which is
    where a step waiting for the motor to start finds it.

    The frozen clock is moved onto the instant of each answer, so every timestamp the
    entity records is the one the bus really produced.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        freezer: FrozenDateTimeFactory | None,
        cover: Any,
        *,
        moving_after: float = MOTOR_ECHO_SEC,
        stopped_after: float = STOP_ECHO_SEC,
        answer: bool = True,
        drop_prefix: str | None = None,
        refuse_prefix: str | None = None,
        write_delay: float = 0.0,
    ) -> None:
        self.hass = hass
        self.freezer = freezer
        self.cover = cover
        self.moving_after = moving_after
        self.stopped_after = stopped_after
        self.answer = answer
        self.drop_prefix = drop_prefix
        self.refuse_prefix = refuse_prefix
        self.write_delay = write_delay
        self.frames: list[str] = []
        self.written: dict[str, datetime] = {}
        self.answered: dict[str, datetime] = {}
        self._due: list[tuple[datetime, str]] = []

    async def send(self, message: Any, *, on_delivered: Any = None, on_dropped: Any = None) -> bool:
        frame = str(message)
        self.frames.append(frame)
        if self.refuse_prefix is not None and frame.startswith(self.refuse_prefix):
            return False
        if self.drop_prefix is not None and frame.startswith(self.drop_prefix):
            if on_dropped is not None:
                on_dropped()
            return True
        if self.write_delay:
            # The command worker was busy with somebody else's frames.
            self.freezer.tick(timedelta(seconds=self.write_delay))
        self.written[frame] = dt_util.utcnow()
        if on_delivered is not None:
            on_delivered(time.monotonic())
        if self.answer:
            delay = self.stopped_after if frame.startswith("*2*0*") else self.moving_after
            self.plan(frame, delay)
        return True

    def plan(self, frame: str, after: float) -> None:
        """The actuator will say `frame` `after` seconds from now."""
        self._due.append((dt_util.utcnow() + timedelta(seconds=after), frame))
        self._due.sort(key=lambda item: item[0])
        self.hass.loop.call_soon(self._pump)

    def _pump(self) -> None:
        """Deliver the answer that is due first, with the clock moved onto its instant."""
        if not self._due:
            return
        instant, frame = self._due.pop(0)
        self.freezer.move_to(instant)
        self.answered.setdefault(frame, instant)
        self.cover.handle_event(OWNEvent.parse(frame))
        if self._due:
            self.hass.loop.call_soon(self._pump)

    async def sleep(self, seconds: float) -> None:
        """Wait, delivering whatever the actuator says while we do."""
        end = dt_util.utcnow() + timedelta(seconds=seconds)
        while self._due and self._due[0][0] <= end:
            self._pump()
            # Whatever that frame set off gets to run - including the end of the wait
            # itself, when it was the "stopped" a `async_calib_home` was waiting for.
            # Three turns of the loop, because that interrupt travels through a timer:
            # the callback reschedules it, the loop moves it to the ready queue, and
            # only then is this coroutine cancelled.
            for _ in range(3):
                await asyncio.sleep(0)
        self.freezer.move_to(end)
        await asyncio.sleep(0)


def _patched(path: GuidedPath):
    """Both seams at once: the command path and the only wait the calibration does."""
    return (
        patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
        patch.object(cover_module, "_async_sleep", path.sleep),
    )


# --------------------------------------------------------------------------------------
# Homing
# --------------------------------------------------------------------------------------
async def test_home_runs_to_the_end_stop_and_waits_out_the_modelled_run(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """With no word from the actuator, homing waits the run the configuration predicts.

    That is the same wait `cover_calibration_run` has always done - the full run of that
    direction plus the settle - and it is all a gateway that relays no status leaves us
    with.

    Mutation caught: waiting the *other* direction's run (the shutter would still be
    moving when the next step starts measuring from it).
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover, answer=False)
        started = dt_util.utcnow()
        with patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send):
            with patch.object(cover_module, "_async_sleep", new=AsyncMock()) as sleep:
                await cover.async_calib_home(DIRECTION_OPEN)
            assert path.frames == [RAISE]
            waits = [call.args[0] for call in sleep.await_args_list]
            assert waits == [pytest.approx(OPENING + cover_module.CALIBRATION_SETTLE_SEC)]

            # The mocked wait moved no clock, so the shutter is still notionally
            # running: let its own run finish before asking for the other end.
            freezer.tick(timedelta(seconds=OPENING + 1))
            async_fire_time_changed(hass)
            await hass.async_block_till_done()
            started = dt_util.utcnow()

            with patch.object(cover_module, "_async_sleep", new=AsyncMock()) as sleep:
                await cover.async_calib_home(DIRECTION_CLOSE)
            waits = [call.args[0] for call in sleep.await_args_list]
            assert waits == [pytest.approx(CLOSING + cover_module.CALIBRATION_SETTLE_SEC)]
        # The wait itself moved no clock: every second of it was the modelled one.
        assert dt_util.utcnow() == started


async def test_home_stops_waiting_when_the_actuator_says_it_has_arrived(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A real actuator reports its own stop, and the step goes on a second later.

    The modelled run is an estimate with a three-second settle on top of it; the
    shutter's own "stopped" is the truth, and waiting out the estimate after it would
    add the best part of a minute to a seven-movement flow for nothing.

    Mutation caught: dropping the interrupt (the wait then lasts the whole modelled run
    and the settle, and the clock at the end says so).
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        start = dt_util.utcnow()
        with _patched(path)[0], _patched(path)[1]:
            # The shutter really reaches the top in 18 s, four and a half short of the
            # modelled run and its settle.
            path.plan(STOPPED, 18.0)
            await cover.async_calib_home(DIRECTION_OPEN)
        elapsed = (dt_util.utcnow() - start).total_seconds()
        assert elapsed == pytest.approx(18.0 + cover_module.CALIBRATION_HOME_SETTLE_SEC, abs=0.01)
        assert path.frames == [RAISE]
        # And the estimate is at the end stop, which is what the next step measures from.
        assert hass.states.get(ENTITY).attributes["current_position"] == 100


async def test_home_only_waits_out_the_settle_when_the_shutter_is_already_there(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A cover the estimate already puts at that end stop has nothing to run.

    The frame still goes out - the estimate is what is being calibrated, so it is not
    to be trusted with "it is already open" - but the wait is the settle alone rather
    than a full run of standing still.
    """
    mock_restore_cache(hass, (State(ENTITY, CoverState.OPEN, {"current_position": 100}),))
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover, answer=False)
        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", new=AsyncMock()) as sleep,
        ):
            await cover.async_calib_home(DIRECTION_OPEN)
        assert path.frames == [RAISE]
        waits = [call.args[0] for call in sleep.await_args_list]
        assert waits == [cover_module.CALIBRATION_HOME_SETTLE_SEC]


# --------------------------------------------------------------------------------------
# Starting a free run, and the press that ends it
# --------------------------------------------------------------------------------------
async def test_start_answers_with_the_instant_the_motor_really_turned(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The motor start is the actuator's own word, half a second after the frame.

    Everything the user then presses is measured against this instant, so a run timed
    from the frame instead would put half a second of bus into every time the flow
    writes - 5 cm of bar on the reference window.

    Mutation caught: returning the delivery plus `start_delay` even though the actuator
    answered.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        frame_at = dt_util.utcnow()
        with _patched(path)[0], _patched(path)[1]:
            started = await cover.async_calib_start(DIRECTION_OPEN)
        assert path.frames == [RAISE]
        assert (started - frame_at).total_seconds() == pytest.approx(MOTOR_ECHO_SEC, abs=0.001)
        assert started == path.answered[MOVING_UP]
        # A free run: nothing was queued to stop it.
        assert STOP not in path.frames
        assert hass.states.get(ENTITY).state == CoverState.OPENING


async def test_start_falls_back_to_the_model_when_the_answer_beat_the_delivery(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The status may arrive before we even look: the wait then has nothing to do.

    What must not happen is a second wait for a frame that has already come and gone.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        with _patched(path)[0], _patched(path)[1]:
            started = await cover.async_calib_start(DIRECTION_CLOSE)
            # The same instant a second call reads off the entity.
            assert started == cover._motor_started_at
        assert path.frames == [LOWER]


async def test_start_gives_up_when_the_actuator_never_answers(hass: HomeAssistant, tmp_path) -> None:
    """No "moving" status within three seconds of the frame is "it did not respond".

    The flow shows that screen with a button to try again on it; what it must not do is
    time a run against a motor that never started, which is a measurement of nothing.

    The direction frame *was* delivered, so the motor is very probably running: the
    step unwinds through a `try/finally` that writes a best-effort stop, which is what
    `problem_no_echo` tells the user in seven languages ("a stop was sent right after
    the error"). Until 0.5.0 v2 that sentence was true of the timed run and false of
    this one - the primitive behind both *timed press* steps (review BUG-6).

    Mutation caught: waiting for ever (the flow would hang on a shutter whose fuse is
    out), falling back to `start_delay` the way the 0.4.2 service does, or leaving the
    shutter running after the failure.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        # No frozen clock here, and none is possible: the three seconds are a real
        # wait on the event loop, and freezegun stops the loop's own clock dead.
        path = GuidedPath(hass, None, cover, answer=False)
        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "CALIBRATION_MOTOR_ECHO_SEC", 0.01),
            pytest.raises(CalibrationError) as err,
        ):
            await cover.async_calib_start(DIRECTION_OPEN)
        assert err.value.reason == REASON_NO_ECHO
        assert ENTITY in str(err.value)
        assert path.frames == [RAISE, STOP]
        # The step is over, so the attribute is gone again even though it failed.
        assert ATTR_CALIBRATING not in hass.states.get(ENTITY).attributes


async def test_start_gives_up_when_the_frame_never_reaches_the_bus(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A dropped direction frame moved nothing, so there is nothing to time.

    Mutation caught: taking the enqueue for a delivery, after which the step measures a
    shutter that never left its end stop.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover, drop_prefix="*2*")
        with _patched(path)[0], _patched(path)[1], pytest.raises(CalibrationError) as err:
            await cover.async_calib_start(DIRECTION_OPEN)
        assert err.value.reason == REASON_NOT_DELIVERED
        assert "did not start moving" in str(err.value)


# --------------------------------------------------------------------------------------
# Stopping
# --------------------------------------------------------------------------------------
async def test_stop_answers_with_the_instant_the_frame_reached_the_bus(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Not the instant it was asked for: the motor runs for every second of the queue.

    A stop that waited 0.4 s to be written is 0.4 s of extra travel, and the flow
    measures the run it got, not the one it asked for.

    Mutation caught: reporting the moment `async_calib_stop` was called.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        with _patched(path)[0], _patched(path)[1]:
            await cover.async_calib_start(DIRECTION_CLOSE)
            asked_at = dt_util.utcnow()
            path.write_delay = 0.4
            written = await cover.async_calib_stop()
        assert path.frames == [LOWER, STOP]
        assert (written - asked_at).total_seconds() == pytest.approx(0.4, abs=0.001)
        assert written == path.written[STOP]


async def test_stop_says_so_when_the_command_path_would_not_take_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A stop nobody wrote stopped nothing: the shutter runs on to its end stop.

    The flow has to know, because the position it was about to have the user measure
    does not exist.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        with _patched(path)[0], _patched(path)[1]:
            await cover.async_calib_start(DIRECTION_CLOSE)
            path.refuse_prefix = "*2*0*"
            with pytest.raises(CalibrationError) as err:
                await cover.async_calib_stop()
        assert err.value.reason == REASON_NOT_STOPPED
        assert "never stopped" in str(err.value)


# --------------------------------------------------------------------------------------
# A measured run
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("direction", "fraction", "expected"),
    [
        (DIRECTION_CLOSE, 0.25, CURTAIN_DOWN * 0.25),
        (DIRECTION_CLOSE, 0.5, CURTAIN_DOWN * 0.5),
        (DIRECTION_CLOSE, 0.75, CURTAIN_DOWN * 0.75),
        (DIRECTION_OPEN, 0.25, SLAT + CURTAIN_UP * 0.25),
        (DIRECTION_OPEN, 0.75, SLAT + CURTAIN_UP * 0.75),
    ],
)
async def test_a_fraction_run_spends_the_motor_seconds_that_fraction_is_worth(
    hass: HomeAssistant,
    tmp_path,
    freezer: FrozenDateTimeFactory,
    direction: str,
    fraction: float,
    expected: float,
) -> None:
    """A quarter of the curtain, and the slat phase on top of it going up.

    The fraction is of the *curtain* travel, which is the axis the roll model is
    written on: a quarter of a run that includes a slat phase would be a quarter of
    nothing the fit can invert.

    Mutation caught: taking the fraction of the whole run, or adding the slat phase to
    a descent (where the slats never move at all).
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        with _patched(path)[0], _patched(path)[1]:
            report = await cover.async_calib_run_fraction(direction, fraction)
        assert path.frames == [LOWER if direction == DIRECTION_CLOSE else RAISE, STOP]
        assert report.planned_seconds == pytest.approx(expected)
        assert report.direction == direction
        assert report.fraction == fraction
        # The motor ran between the two status frames the actuator sent, and that is
        # what the report carries - what was asked for, to the hundredth, because this
        # gateway writes at once and this actuator brakes exactly as fast as the model
        # assumes it does.
        assert report.motor_seconds == pytest.approx(expected, abs=0.02)
        assert report.motor_start == path.answered[LOWER if direction == DIRECTION_CLOSE else RAISE]
        assert report.stop_written == path.written[STOP]


async def test_a_fraction_run_reports_the_seconds_the_queue_really_cost(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The stop waited in the queue, so the motor ran longer, and the report says so.

    The fit inverts the model against these seconds: reporting the seconds that were
    planned would push the whole queue delay into the roll.

    Mutation caught: returning `planned_seconds` as the measurement.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        # The actuator brakes exactly as fast as the model assumes, so every extra
        # second of motor below is the command queue's and nothing else.
        path = GuidedPath(hass, freezer, cover)

        async def _slow_stop(seconds: float) -> None:
            # The command worker gets round to the stop four tenths of a second late.
            path.write_delay = 0.4
            await path.sleep(seconds)

        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", _slow_stop),
        ):
            report = await cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5)
        assert report.planned_seconds == pytest.approx(CURTAIN_DOWN * 0.5)
        assert report.motor_seconds == pytest.approx(CURTAIN_DOWN * 0.5 + 0.4, abs=0.02)


async def test_a_fraction_run_needs_the_actuator_to_confirm_the_start(
    hass: HomeAssistant, tmp_path
) -> None:
    """A silent actuator ends the guided run before the shutter is left half way.

    The 0.4.2 service goes on in that case (it always has, and a bus that answers
    nothing still calibrates after a fashion); a guided step does not, because it has a
    screen to explain it on.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, None, cover, answer=False)
        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "CALIBRATION_MOTOR_ECHO_SEC", 0.01),
            pytest.raises(CalibrationError) as err,
        ):
            await cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5)
        assert err.value.reason == REASON_NO_ECHO
        # The direction frame *was* written, so the motor is very probably turning: the
        # run is abandoned with a stop, not with a shrug. (0.5.0 review, RISK-5: this
        # used to unwind past the stop and leave a shutter with no end limit running.)
        assert path.frames == [LOWER, STOP]


# --------------------------------------------------------------------------------------
# The cover is marked, and defended, while a step runs
# --------------------------------------------------------------------------------------
async def test_the_attribute_says_when_a_step_owns_the_cover(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """`Calibrating` is published while a primitive runs and gone the moment it ends.

    Mutation caught: leaving the attribute behind after the step (every later position
    command on that cover would then be refused for good).
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        assert cover.calibrating is False
        assert ATTR_CALIBRATING not in hass.states.get(ENTITY).attributes
        path = GuidedPath(hass, freezer, cover)
        seen: list[Any] = []

        async def _watch(seconds: float) -> None:
            seen.append(hass.states.get(ENTITY).attributes.get(ATTR_CALIBRATING))
            await path.sleep(seconds)

        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", _watch),
        ):
            await cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5)
        assert seen and all(value is True for value in seen)
        assert cover.calibrating is False
        assert ATTR_CALIBRATING not in hass.states.get(ENTITY).attributes


async def test_a_flow_holds_the_cover_across_its_steps(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The session is re-entrant: the attribute does not blink between two steps.

    The flow of phase 2 opens one around the whole conversation - which is minutes of a
    user reading screens - and each primitive opens one of its own inside it.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        with _patched(path)[0], _patched(path)[1], cover.calibration_session():
            assert cover.calibrating is True
            await cover.async_calib_home(DIRECTION_OPEN)
            assert cover.calibrating is True
            assert hass.states.get(ENTITY).attributes[ATTR_CALIBRATING] is True
        assert cover.calibrating is False


async def test_set_position_is_refused_while_the_cover_is_calibrating(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A position command in the middle of a guided run would falsify the measurement.

    It is refused where the user can see it (a `ServiceValidationError` reaches the
    caller of the service), and nothing at all goes on the bus.

    Mutation caught: refusing silently, which leaves an automation believing it moved
    the shutter.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        with cover.calibration_session():
            with pytest.raises(ServiceValidationError, match="being calibrated"):
                await hass.services.async_call(
                    COVER,
                    "set_cover_position",
                    {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40},
                    blocking=True,
                )
            assert commands.sent_frames == []
        # Once the session is over the cover takes its orders again.
        await hass.services.async_call(
            COVER, "set_cover_position", {ATTR_ENTITY_ID: ENTITY, ATTR_POSITION: 40}, blocking=True
        )
        assert commands.sent_frames == [LOWER]


async def test_a_step_that_has_to_start_from_a_standstill_refuses_a_moving_cover(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A run that starts half way up measures nothing; homing a moving cover is fine.

    The asymmetry is the point: `async_calib_home` is exactly what to do with a shutter
    that is running the wrong way, while `async_calib_run_fraction` needs it standing
    at the end stop it is about to leave.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        await hass.services.async_call(COVER, "open_cover", {ATTR_ENTITY_ID: ENTITY}, blocking=True)
        path = GuidedPath(hass, freezer, cover)
        with _patched(path)[0], _patched(path)[1]:
            with pytest.raises(CalibrationError) as err:
                await cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5)
            assert err.value.reason == REASON_BUSY
            with pytest.raises(CalibrationError) as err:
                await cover.async_calib_start(DIRECTION_CLOSE)
            assert err.value.reason == REASON_BUSY
            assert path.frames == []
            # Homing takes it as it finds it.
            with patch.object(cover_module, "_async_sleep", new=AsyncMock()):
                await cover.async_calib_home(DIRECTION_CLOSE)
            assert path.frames == [LOWER]


async def test_every_primitive_refuses_an_advanced_cover(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """An advanced actuator reports its real position: there is no model to calibrate."""
    async with setup_myhome(hass, tmp_path, ADVANCED_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        for call in (
            cover.async_calib_home(DIRECTION_OPEN),
            cover.async_calib_start(DIRECTION_OPEN),
            cover.async_calib_stop(),
            cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5),
        ):
            with pytest.raises(CalibrationError) as err:
                await call
            assert err.value.reason == REASON_ADVANCED
        assert commands.sent_frames == []


# --------------------------------------------------------------------------------------
# The frame that never left, the lock, and the stop that has to happen anyway (0.5.0 R3)
# --------------------------------------------------------------------------------------
async def test_homing_says_so_when_the_gateway_would_not_take_the_frame(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A homing nobody wrote left the shutter where it was, and must not report success.

    The two cases arrive here as one: a cover that is already at that end stop and a
    cover whose frame the command path refused both reach `async_calib_home` with
    `_movement_end_event` set, because only a *delivered* frame ever clears it. The
    first is fine - there was nothing to run - and the second is the one failure mode
    the whole release exists to avoid: the step returns after a second, the next one
    runs "50 % from the top" from half way down, and the user tapes a movement that
    never happened.

    Mutation caught: reading the event alone (0.5.0 review, BUG-4).
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        # The previous movement has ended, which is how a real shutter arrives here.
        cover._movement_end_event.set()  # noqa: SLF001 - the state this bug lives in
        path = GuidedPath(hass, freezer, cover, refuse_prefix="*2*")
        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", new=AsyncMock()) as sleep,
            pytest.raises(CalibrationError) as err,
        ):
            await cover.async_calib_home(DIRECTION_CLOSE)
        assert err.value.reason == REASON_NOT_DELIVERED
        assert ENTITY in str(err.value)
        # And it did not sit out the settle as if it had arrived.
        assert sleep.await_args_list == []


async def test_two_guided_movements_cannot_drive_the_same_shutter_at_once(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Two browser tabs, or a flow and the 0.4.2 service, on one motor.

    `_calib_idle_guard` samples `_moving` once, before the first await, so two runs
    that start within the same tick both pass it; the first stop then ends both and the
    second arrives on a standing shutter with a plausible, wrong `motor_seconds`. The
    lock is what makes that impossible, and refusing rather than queueing is what gives
    the second conversation a screen to say so on.

    Mutation caught: dropping `_calibration_claim` from any of the three primitives
    that drive the motor (0.5.0 review, RISK-3).
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        running = asyncio.Event()
        release = asyncio.Event()

        async def _gate(seconds: float) -> None:
            running.set()
            await release.wait()
            await path.sleep(seconds)

        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", _gate),
        ):
            first = hass.async_create_task(cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5))
            await running.wait()

            for call in (
                cover.async_calib_run_fraction(DIRECTION_OPEN, 0.25),
                cover.async_calib_start(DIRECTION_OPEN),
                cover.async_calib_home(DIRECTION_OPEN),
            ):
                with pytest.raises(CalibrationError) as err:
                    await call
                assert err.value.reason == REASON_BUSY

            release.set()
            report = await first
        assert report.motor_seconds > 0
        # Only the first run's frames ever reached the bus.
        assert path.frames == [LOWER, STOP]


async def test_the_old_service_refuses_a_shutter_a_guided_flow_is_holding(
    hass: HomeAssistant, tmp_path
) -> None:
    """`cover_calibration_run` and the guided flow are two ways to drive one shutter.

    The flow holds a calibration session for the whole conversation and only takes the
    lock around its own movements, so the lock alone would let the service in between
    two screens - and the flow would then time a run somebody else stopped.

    Mutation caught: dropping the `calibrating` test from the service (0.5.0 review,
    RISK-3).
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML) as (_entry, commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        with cover.calibration_session(), pytest.raises(ServiceValidationError) as err:
            await cover.async_calibration_run(DIRECTION_CLOSE)
        assert "guided calibration" in str(err.value)
        assert commands.sent_frames == []


async def test_a_run_cancelled_half_way_still_writes_the_stop(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Closing the dialog during a measured run must not leave the motor turning.

    Home Assistant cancels the progress task of a flow it removes
    (`FlowManager._async_remove_flow_progress` -> `async_cancel_progress_task`), which
    unwinds the run mid-sleep. The stop is written from the `finally`, shielded, so the
    cancellation reaches the caller at once and the frame still reaches the bus.

    Mutation caught: dropping the `try`/`finally` (0.5.0 review, RISK-5).
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        running = asyncio.Event()

        async def _never(seconds: float) -> None:
            running.set()
            await asyncio.Event().wait()

        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", _never),
        ):
            run = hass.async_create_task(cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5))
            await running.wait()
            run.cancel()
            with pytest.raises(asyncio.CancelledError):
                await run
            # The shielded stop lives in a task of its own: let it finish.
            for _ in range(20):
                await asyncio.sleep(0)
        assert path.frames == [LOWER, STOP]


async def test_a_stop_the_gateway_cannot_even_take_only_reaches_the_log(
    hass: HomeAssistant, tmp_path
) -> None:
    """The tidying-up stop must not replace the failure it is tidying up after.

    The caller is waiting to be told why the run failed - `no_echo`, here - and a
    second exception thrown from the `finally` would hide it behind something about a
    stop frame, which is not what went wrong.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, None, cover, answer=False)

        async def _send(_self: Any, message: Any, **kwargs: Any) -> bool:
            if str(message).startswith("*2*0*"):
                raise HomeAssistantError("the gateway went away")
            return await path.send(message, **kwargs)

        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _send),
            patch.object(cover_module, "CALIBRATION_MOTOR_ECHO_SEC", 0.01),
            pytest.raises(CalibrationError) as err,
        ):
            await cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5)
        assert err.value.reason == REASON_NO_ECHO


async def test_the_one_at_a_time_lock_is_one_per_gateway(hass: HomeAssistant, tmp_path) -> None:
    """A house with two gateways has two buses, two sets of shutters and two people.

    The lock exists so that two guided flows, or a flow and the 0.4.2 service, cannot
    interleave their runs on one motor: two runs that start within the same tick both
    pass the idle guard, the first stop ends both, and the fit is handed two plausible
    and wrong `motor_seconds`. None of that is true across gateways, where a single
    lock only answered the second house with `problem_busy` - whose screen says "this
    cover is already moving", which is not what had happened (review RISK-5).

    Mutation caught: going back to one module-level lock.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        mine = cover_module.calibration_lock(MAC)
        assert mine is cover_module.calibration_lock(MAC)
        assert mine is not cover_module.calibration_lock("00:11:22:33:44:55")
        # ...and it really is the one the primitives take.
        await mine.acquire()
        try:
            with pytest.raises(CalibrationError) as err:
                await cover.async_calib_home(DIRECTION_CLOSE)
            assert err.value.reason == REASON_BUSY
        finally:
            mine.release()


async def test_a_run_cut_short_is_not_settled_until_its_stop_is_on_the_bus(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """What a reload has to wait for, and the only exact way to wait for it.

    Closing the dialog cancels the progress task and then calls the options flow's
    `async_remove`, which schedules the reload: at that instant the `finally` that
    shields the stop has not run yet, so the reload could close the gateway sessions
    first and swallow the one stop the runner goes to some trouble to write. Two turns
    of the event loop used to stand in for the wait - a guess nothing could pin (final
    review, RISK-D, mutation M11).

    Mutation caught: setting the event in the `finally` of the run itself, which is
    reached while the shielded stop is still on its way; never clearing it, which makes
    every wait return at once.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        # The run is held in the wait it spends most of its life in, which is where the
        # dialog closing finds it.
        parked = asyncio.Event()

        async def _hold(_seconds: float) -> None:
            await parked.wait()

        with (
            patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", path.send),
            patch.object(cover_module, "_async_sleep", _hold),
        ):
            task = hass.async_create_task(cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5))
            for _ in range(12):
                await asyncio.sleep(0)
            assert path.frames == [LOWER]
            assert cover._calib_settled.is_set() is False  # noqa: SLF001

            # The dialog is closed: the task is cancelled and nobody awaits it.
            task.cancel()
            assert STOP not in path.frames

            assert await cover.async_calib_settled() is True
            assert STOP in path.frames
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def test_a_run_that_ends_by_itself_leaves_nothing_to_wait_for(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The common case costs the reload nothing at all.

    Mutation caught: leaving the event clear after a run that stopped the shutter
    itself, which would make every close of the dialog wait out the timeout.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        path = GuidedPath(hass, freezer, cover)
        with _patched(path)[0], _patched(path)[1]:
            await cover.async_calib_run_fraction(DIRECTION_CLOSE, 0.5)
        assert cover._calib_settled.is_set() is True  # noqa: SLF001
        assert await cover.async_calib_settled() is True


async def test_a_run_that_never_tidies_up_does_not_hold_the_reload_for_ever(
    hass: HomeAssistant, tmp_path
) -> None:
    """A gateway that is not answering is a reason to reload, not a reason to wait.

    Mutation caught: waiting on the event with no bound at all, which would leave the
    entry unloadable behind a stop nothing is ever going to write.
    """
    async with setup_myhome(hass, tmp_path, RUNNER_YAML):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        cover._calib_settled.clear()  # noqa: SLF001 - a run that never came back
        assert await cover.async_calib_settled(timeout=0.01) is False
