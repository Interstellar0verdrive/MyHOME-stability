"""The guided calibration's test bench: the reference window and a shutter that behaves.

Shared by the dialog's tests (`test_calibration_flow.py`, where all of this was written
for 0.5.0 and from where it was moved unchanged), the parity tests of the ported
arithmetic (`test_calibration_measure.py`) and the panel's calibration session, which
drives the same four primitives and has to rediscover the same window.

The fake runner stands in for the four `async_calib_*` primitives of the real cover
entity (and `async_calib_motor_stop`): it answers the way the 195 cm reference window
below would, so the numbers a conversation stores can be checked against the ones it
was meant to rediscover rather than against themselves. The primitives themselves are
covered frame by frame in `test_calibration_runner.py`.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from custom_components.myhome.calibration import CalibrationError, RunReport, predict_cm
from custom_components.myhome.const import DIRECTION_CLOSE, DIRECTION_OPEN

# The reference window, once. The YAML of a test configures exactly what the fake
# shutter really is, so a calibration that works has to hand back the numbers below:
# anything else is the conversation inventing a shutter.
HEIGHT = 195.0
OPENING = 22.3
CLOSING = 21.7
SLAT = 4.7
ROLL_DOWN = 1.69
ROLL_UP = 2.12
CURTAIN_DOWN = CLOSING - SLAT  # 17.0 s
CURTAIN_UP = OPENING - SLAT  # 17.6 s


def descent_cm(fraction: float) -> float:
    """Where the bottom edge of the real window is after `fraction` of a descent."""
    return predict_cm(DIRECTION_CLOSE, ROLL_DOWN, 1.0, fraction, HEIGHT)


def ascent_cm(fraction: float) -> float:
    """...and after the slats plus `fraction` of an ascent."""
    return predict_cm(DIRECTION_OPEN, ROLL_UP, 1.0, fraction, HEIGHT)


class FakeRunner:
    """The four primitives of `MyHOMECover`, answered by a shutter that behaves.

    Every call is recorded, every failure is injectable, and the seconds handed back
    are the ones the reference window would really have spent - which is what makes
    the values the flow stores checkable.
    """

    def __init__(self, cover: Any) -> None:
        self.cover = cover
        self.homed: list[str] = []
        self.started: list[str] = []
        self.runs: list[tuple[str, float]] = []
        # ...and the same calls in the order they arrived, which is what a movement
        # count has to be read off: a homing that had nothing to run is not a movement,
        # and only the call before it says whether it had.
        self.log: list[tuple[str, str]] = []
        self.stops = 0
        self.stopped_at = dt_util.utcnow()
        self.fail: CalibrationError | None = None
        self.fail_on: str | None = None
        cover.async_calib_home = self._home
        cover.async_calib_start = self._start
        cover.async_calib_stop = self._stop
        cover.async_calib_motor_stop = self._motor_stop
        cover.async_calib_run_fraction = self._run_fraction
        # How long the motor goes on turning after our stop frame reaches the bus, and
        # how long the gateway sat on that frame before writing it. Both are zero on a
        # shutter that behaves, and both are what the lift-off check screen is about.
        self.stop_coast = 0.0
        self.stop_queue = 0.0

    def _maybe_fail(self, what: str) -> None:
        if self.fail is not None and self.fail_on in (None, what):
            error, self.fail = self.fail, None
            raise error

    async def _home(self, direction: str, timeout: float | None = None) -> None:
        self._maybe_fail("home")
        self.homed.append(direction)
        self.log.append(("home", direction))

    async def _start(self, direction: str):
        self._maybe_fail("start")
        self.started.append(direction)
        self.log.append(("start", direction))
        return dt_util.utcnow()

    async def _stop(self):
        self._maybe_fail("stop")
        self.stops += 1
        self.log.append(("stop", ""))
        # The instant our frame reached the bus, which is not the instant it was asked
        # for: a busy command queue holds it back, and the motor runs for all of it.
        self.stopped_at = dt_util.utcnow() + timedelta(seconds=self.stop_queue)
        return self.stopped_at

    async def _motor_stop(self):
        """The actuator's own "stopped", `stop_coast` after the frame went out."""
        return self.stopped_at + timedelta(seconds=self.stop_coast)

    async def _run_fraction(self, direction: str, fraction: float) -> RunReport:
        self._maybe_fail("run")
        self.runs.append((direction, fraction))
        self.log.append(("run", direction))
        seconds = (
            fraction * CURTAIN_DOWN
            if direction == DIRECTION_CLOSE
            else SLAT + fraction * CURTAIN_UP
        )
        now = dt_util.utcnow()
        return RunReport(
            motor_start=now,
            stop_written=now,
            motor_seconds=seconds,
            planned_seconds=seconds,
            fraction=fraction,
            direction=direction,
        )
