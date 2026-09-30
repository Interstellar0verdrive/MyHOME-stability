"""Explicitly briefed basic slat/roll measurement, owned by the existing session."""
from __future__ import annotations

import asyncio
import math
from typing import Any, cast

import voluptuous as vol

from . import cover_calibration as guided
from .cover_calibration_fit import closing_fit, opening_fit, opening_roll_fit
from .cover_profile_provenance import evidence
from .cover_profiles import ProfileError, travel_time, write_profile
from .cover_settings import centimetres

# Lift-off gap limits in cm. A reading below TOUCHING_CM means the edge still
# rests on its sill; the 1 cm rule is to be validated on real installations.
# The joint fit loses precision as the gap grows: from GAP_WARN_CM a reading is
# accepted with a warning, above MAX_GAP_CM it is refused.
TOUCHING_CM = 1.0
GAP_WARN_CM = 10.0
MAX_GAP_CM = 20.0
# True: such a reading discards the lift-off run and repeats it. False: refuse it.
LIFT_REPEAT_BELOW_TOUCHING = True


class GeometryCalibrationSession(guided.CalibrationSession):
    """No browser timings, unattended continuation, or partially saved geometry."""

    mode = "geometry"
    safe_phases = guided.CalibrationSession.safe_phases | {"briefing", "reading"}

    def __init__(self, *args: Any, slats: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.phase, self.step = "briefing", "home"
        # Without slats there is no lift-off: the full ascent follows the first close.
        self.slats = slats
        self.after_position = "lift" if slats else "opening"
        self.lift_attempts = 1
        self.still_resting = False
        self.gap_warning = False
        self.after_stop = "briefing"
        self.stop_written = False
        self.samples: dict[str, float] = {}
        self.readings: dict[str, float] = {}
        self.geometry: dict[str, float] = {}
        self.geometry_provenance: dict[str, Any] = {}

    def view(self) -> Any:
        return {**super().view(), "step": self.step, "save_modes": ["new"],
                "travel_cm": self.measured_travel, "geometry": dict(self.geometry),
                "readings": dict(self.readings), "samples": dict(self.samples),
                "accuracy": None, "independent_check": False,
                "can_repeat": self.phase in {"reading", "review"} or (self.phase == "briefing" and self.step == "half_open")
                or self.gap_warning,
                "reading_kind": "travel" if self.step == "opening" else self.step,
                "expected_cm": self.measured_travel / 2 if self.measured_travel and self.step.startswith("half_") else None,
                "slats": self.slats, "lift_attempts": self.lift_attempts, "still_resting": self.still_resting,
                "touching_cm": TOUCHING_CM, "max_gap_cm": MAX_GAP_CM, "lift_repeat": LIFT_REPEAT_BELOW_TOUCHING,
                "gap_warn_cm": GAP_WARN_CM, "gap_warning": self.gap_warning}

    def interrupt(self, reason: str, send_stop: Any = True) -> None:
        if not self.active or self.phase == "saving":
            return
        self.geometry.clear()
        self.geometry_provenance = {}
        self.samples.clear()
        self.readings.clear()
        self.measured_travel = None
        self.still_resting = self.gap_warning = False
        super().interrupt(reason, send_stop)

    def geometry_action(self, msg: dict[str, Any]) -> None:
        action = msg["action"]
        if action == "next" and self.phase == "briefing":
            self.gap_warning = False  # Moving on accepts the wide gap.
            direction = "close" if self.step in {"home", "reset", "closing", "half_close"} else "open"
            written = self.queue_move(direction)
            written.add_done_callback(self._movement_delivered)
        elif action == "lift" and self.step == "lift" and self.phase == "opening":
            self._sample_stop()
        elif action == "endpoint" and self.phase in {"opening", "closing"} and self.step in {"home", "reset", "opening", "closing", "top"}:
            self._endpoint()
        elif action == "reading" and self.phase == "reading":
            try:
                self._reading(msg.get("reading_cm"))
            except vol.Invalid as error:
                raise ProfileError("invalid_reading") from error
        elif action == "repeat" and self.view()["can_repeat"]:
            self._repeat()
        else:
            raise ProfileError("calibration_step")

    def _movement_delivered(self, future: asyncio.Future[float]) -> None:
        if future.cancelled() and self.active and not self.closed:
            self.interrupt("not_delivered")

    def on_event(self, event: Any) -> None:
        if self.phase == "geometry_wait_stop":
            self.reservation.observe(event)
            opening = self.step in {"lift", "opening", "half_open", "top"}
            if (event.is_closing if opening else event.is_opening):
                self.interrupt("unexpected_movement")
            elif event.state == 0 and self.stop_written:
                self._stopped()
            return
        starting = self.phase.startswith("starting_")
        super().on_event(event)
        if starting and self.phase in {"opening", "closing"} and self.step.startswith("half_"):
            seconds = (((self.samples["lift"] if self.slats else 0.0) + self.values["opening_time"]) / 2 if self.step == "half_open"
                       else (self.values["closing_time"] - self.geometry["slat_time_s"]) / 2)
            # Reuse the motion deadline: interruption/close already cancels it.
            cast(asyncio.TimerHandle, self.deadline).cancel()
            self.deadline = self.hass.loop.call_later(seconds, self._sample_stop)

    def _sample_stop(self) -> None:
        self.phase, self.after_stop, self.stop_written = "geometry_wait_stop", "reading", False
        self.arm_deadline(guided.STOP_QUEUE_SECONDS, "not_stopped")
        written = self.queue_stop()
        if written is None:
            self.interrupt("stop_queue_full", send_stop=False)
            return
        written.add_done_callback(self._sample_written)
        self.emit()

    def _sample_written(self, future: asyncio.Future[float]) -> None:
        if self.closed or self.phase != "geometry_wait_stop":
            return
        if future.cancelled():
            self.interrupt("not_delivered")
            return
        elapsed = future.result() - cast(float, self.started_at)
        if not 0 <= elapsed <= guided.MAX_TRAVEL_SECONDS:
            self.interrupt("invalid_measurement")
            return
        self.samples[self.step] = elapsed
        self.stop_written = True
        if not self.reservation.pending:
            self._stopped()
        else:
            self.emit()

    def _endpoint(self) -> None:
        old_step = self.step
        if old_step in {"opening", "closing"}:
            try:
                value = travel_time(guided.monotonic() - cast(float, self.started_at))
            except vol.Invalid as error:
                self.interrupt("invalid_measurement")
                raise ProfileError("invalid_profile") from error
            self.values[f"{old_step}_time"] = value
            self.provenance[old_step] = evidence("guided", self.cover.unique_id)
        self.confirm_position(0 if old_step in {"home", "reset", "closing"} else 100)
        self.after_stop = "reading" if old_step == "opening" else "briefing"
        self.phase, self.stop_written = "geometry_wait_stop", True
        self.started_at = None
        self.arm_deadline(guided.STOP_QUEUE_SECONDS, "not_stopped")
        written = self.queue_stop()
        if written is None:
            self.interrupt("stop_queue_full", send_stop=False)
            return
        written.add_done_callback(self._movement_delivered)
        self.emit()

    def _stopped(self) -> None:
        cast(asyncio.TimerHandle, self.deadline).cancel()
        self.started_at = None
        self.phase = self.after_stop
        if self.phase == "briefing":
            self.step = self.after_position if self.step in {"home", "reset", "top"} else "half_open"
        self.emit()

    def _gap(self, value: Any) -> float:
        """A lift-off gap in cm; below TOUCHING_CM only when that repeats the run."""
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise vol.Invalid("The gap must be a reading in cm")
        if value > MAX_GAP_CM or (value < TOUCHING_CM and not LIFT_REPEAT_BELOW_TOUCHING):
            raise ProfileError("invalid_gap")
        return float(value)

    def _reading(self, value: Any) -> None:
        number = self._gap(value) if self.step == "lift" else centimetres(value)
        if self.step == "lift":
            # Still resting: keep nothing of this run, return to the bottom and lift off again.
            self.still_resting = number < TOUCHING_CM
            if self.still_resting:
                del self.samples["lift"]
                self.lift_attempts += 1
            else:
                self.readings["gap"] = number
            # A wide gap is kept, and the lift-off run may still be repeated before moving on.
            self.gap_warning = number >= GAP_WARN_CM
            self.step, self.after_position = "reset", "lift" if self.still_resting else "opening"
        elif self.step == "opening":
            if number <= self.readings.get("gap", 0.0):
                raise vol.Invalid("Travel must exceed the lift-off gap")
            self.measured_travel = number
            self.step = "closing"
        elif self.step == "half_open":
            if self.slats:
                slat, roll = opening_fit(self.values["opening_time"], self.samples["lift"], self.readings["gap"],
                                         cast(float, self.measured_travel), self.samples["half_open"], number)
            else:
                slat, roll = 0.0, opening_roll_fit(self.values["opening_time"], 0.0, self.samples["half_open"],
                                                   number, cast(float, self.measured_travel))
            if slat >= self.values["closing_time"]:
                raise vol.Invalid("Slat time exceeds closing time")
            self.geometry = {"slat_time_s": slat, "opening_roll": roll}
            self.geometry_provenance = {key: evidence("guided", self.cover.unique_id) for key in self.geometry}
            self.readings["half_open"] = number
            self.step, self.after_position = "top", "half_close"
        else:
            roll = closing_fit(self.values["closing_time"], self.geometry["slat_time_s"], self.samples["half_close"],
                               number, cast(float, self.measured_travel))
            self.geometry["closing_roll"] = roll
            self.geometry_provenance["closing_roll"] = evidence("guided", self.cover.unique_id)
            self.readings["half_close"] = number
            self.phase = "review"
            self.emit()
            return
        self.phase = "briefing"
        self.emit()

    def _repeat(self) -> None:
        target = "lift" if self.gap_warning else "closing" if self.phase == "briefing" and self.step == "half_open" else self.step
        # Without slats the return to the bottom is the same close as the first one.
        self.step = "top" if target in {"half_close", "closing"} else "reset" if self.slats else "home"
        self.after_position = target
        if target == "lift":  # A lift-off run repeated on request is one more attempt, and keeps nothing.
            self.lift_attempts += 1
            self.samples.pop("lift", None)
            self.readings.pop("gap", None)
        self.still_resting = self.gap_warning = False
        self.phase = "briefing"
        self.emit()

    async def save_profiles(self, msg: dict[str, Any]) -> Any:
        result = await write_profile(self.hass, {
            "entry_id": self.entry_id, "entity_id": self.cover.entity_id,
            "revision": self.revision, "action": "save", "profile_id": None,
            "profile": {"name": msg.get("name", ""), **self.values,
                        "reference_travel_cm": self.measured_travel, "geometry": self.geometry},
        }, calibration=self)
        # This tape reading is an actual physical observation, not an old-model
        # estimate. Seed the newly applied model only after the atomic save.
        self.confirm_position(100 * self.readings["half_close"] / cast(float, self.measured_travel))
        return result["revision"]
