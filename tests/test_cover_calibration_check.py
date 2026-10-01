"""The check: a timed run from an end stop towards a height, a tape reading and a verdict in whole centimetres."""
import asyncio
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from aiohttp.resolver import ThreadedResolver
from pytest_socket import socket_enabled  # noqa: F401

from custom_components.myhome.cover_calibration import WS_ACTION, WS_START, register_api
from custom_components.myhome.cover_calibration_check import (
    CHECK_THRESHOLD_CM,
    CalibrationCheck,
    deviation_cm,
    passes,
    tenth,
)
from custom_components.myhome.cover_calibration_fit import winding
from custom_components.myhome.cover_geometry import profile_motion
from custom_components.myhome.cover_motion import CoverMotionModel
from custom_components.myhome.cover_profiles import ProfileError
from tests.test_cover_calibration_geometry import endpoint, review, start, stopped
from tests.test_cover_calibration_geometry import geometry as geometry_fixture
from tests.test_cover_calibration_recovery import call, reader
from tests.test_cover_profiles import plant as plant_fixture
from tests.test_panel_cover_calibration import act, bus

geometry = geometry_fixture
plant = plant_fixture

# The model the geometry tests measure: 22 s up, 20 s down, 2 s of slats, rolls 2 and 3, 200 cm.
MODEL = CoverMotionModel(opening_time_s=22, closing_time_s=20, slat_time_s=2, opening_roll=2, closing_roll=3)
TRAVEL = 200.0
RAISE, LOWER, STOP = "*2*1*11##", "*2*2*11##", "*2*0*11##"


def height_after(seconds, *, opening=True, model=MODEL):
    """Where the bottom edge is after `seconds` of motor from an end stop, by the runtime's own inversion."""
    total, roll = (model.opening_time_s, model.opening_roll) if opening else (model.closing_time_s, model.closing_roll)
    curtain = total - model.slat_time_s
    wound = (seconds - model.slat_time_s) / curtain if opening else 1 - seconds / curtain
    return wound * (2 + (roll - 1) * wound) / (roll + 1)


def commands(cal, since=0):
    return [str(item[0]) for item in cal.queue[since:]]


async def timed(cal, *, late=0.0):
    """Start the check run; its Stop is written `late` seconds after the planned time."""
    await start(cal)
    planned = cal.session.check.planned_seconds
    cal.clock[0] += planned - .2
    callback = cal.session.deadline._callback
    cal.session.deadline.cancel()
    callback()
    await stopped(cal, elapsed=.2 + late)
    assert cal.session.phase == "reading" and cal.session.step == "check"
    return planned


async def checked(cal, *, late=0.0, **extra):
    """From review: the check action, the return to its end stop and the timed run."""
    await act(cal, "check", **extra)
    await endpoint(cal, 9)
    assert (cal.session.phase, cal.session.step) == ("briefing", "check")
    return await timed(cal, late=late)


# ---------------------------------------------------------------------------------
# The verdict.
# ---------------------------------------------------------------------------------
@pytest.mark.parametrize(("gap", "whole", "passed"), [
    (0, 0, True), (3.49, 3, True), (3.5, 4, True), (4.49, 4, True), (4.5, 5, False), (4.51, 5, False), (5, 5, False),
    (-3.49, -3, True), (-3.5, -4, True), (-4.49, -4, True), (-4.5, -5, False), (-4.51, -5, False), (-5, -5, False)])
def test_the_verdict_is_on_the_whole_centimetre_rounded_half_away_from_zero(gap, whole, passed):
    measured = round(100.0 + gap, 2)
    assert deviation_cm(measured, 100.0) == whole
    assert passes(whole) is passed
    assert CHECK_THRESHOLD_CM == 4


def test_the_verdict_never_rounds_half_to_even_nor_follows_binary_noise():
    assert round(4.5) == 4 and deviation_cm(104.5, 100) == 5  # Python's round() would pass it.
    assert 9.7 - 5.2 < 4.5 and round(9.7 - 5.2) == 4 and deviation_cm(9.7, 5.2) == 5
    assert deviation_cm(97.5, 100) == -3 and deviation_cm(95.5, 100) == -5
    assert tenth(99.95) == 100.0 and tenth(-.05) == -.1 and tenth(108.60144) == 108.6


def test_a_check_plans_half_the_travel_upwards_from_the_bottom_by_default():
    check = CalibrationCheck.plan(MODEL, TRAVEL)
    assert (check.direction, check.target_cm, check.opening) == ("opening", 100.0, True)
    assert (check.start.height, check.start.slats) == (0, 0)
    # The slat phase, then the curtain to half the travel along the opening roll.
    assert check.planned_seconds == pytest.approx(2 + 20 * winding(.5, 2))
    down = CalibrationCheck.plan(MODEL, TRAVEL, "closing", 50)
    assert (down.start.height, down.start.slats) == (1, 1)
    assert down.planned_seconds == pytest.approx(18 * (1 - winding(.25, 3)))
    assert height_after(down.planned_seconds, opening=False) == pytest.approx(.25)
    assert check.view() == {"direction": "opening", "target_cm": 100.0, "check_seconds": None, "expected_cm": None,
                            "measured_cm": None, "deviation_cm": None, "passed": None}


@pytest.mark.parametrize(("direction", "target"), [
    (None, 0), (None, -1), (None, TRAVEL), (None, 250), (None, float("nan")), (None, float("inf")),
    (None, True), (None, "100"), ("up", None), ("open", 50)])
def test_a_check_the_cover_cannot_make_is_refused_rather_than_shortened(direction, target):
    with pytest.raises(ProfileError, match="invalid_check"):
        CalibrationCheck.plan(MODEL, TRAVEL, direction, target)


def test_no_run_no_verdict_and_readings_outside_the_travel_are_refused():
    """Fork: a check with nothing to verify against reports no gap at all, never a gap of zero."""
    check = CalibrationCheck.plan(MODEL, TRAVEL)
    with pytest.raises(ProfileError, match="calibration_step"):
        check.read(100)
    assert set(check.view().values()) == {"opening", 100.0, None}
    check.ran(check.planned_seconds + .5)
    assert check.check_seconds == pytest.approx(check.planned_seconds + .5)
    # The late Stop is not the model's fault: the expectation follows the real motor time.
    assert check.expected_cm == tenth(TRAVEL * height_after(check.planned_seconds + .5)) > 100.4
    for value in (-.1, 0, .09, TRAVEL + .1, float("nan"), float("inf"), True, None, "100"):
        with pytest.raises(vol.Invalid):
            check.read(value)
        assert check.measured_cm is None
    # From 0.1 cm, as every other tape reading, up to the travel.
    for value in (.1, TRAVEL):
        check.read(value)
        assert check.measured_cm == value and check.passed is False
    again = check.again()
    assert (again.direction, again.target_cm, again.model) == ("opening", 100.0, MODEL)
    assert again.check_seconds is again.expected_cm is again.measured_cm is again.passed is None


def test_the_window_of_the_twentieth_of_september_fails_going_up_and_passes_coming_down():
    """Fork `test_calibration_session_paths.py:1100`: a 198 cm window told to follow a 110 cm profile.

    The real window, measured on the wall, opens in 22.2 s with 4.4 s of slats and rolls 1.86
    and 2.21; the inherited profile, scaled to 198 cm, gets the times nearly right and the
    rolls wrong. Rising from the bottom to half the travel the edge stops near 108.6 cm (107
    measured that day) instead of 99: the check says so. The descent from the top, which
    crosses neither the slat phase nor the opening roll, stays within the threshold.
    """
    short = {"opening_time": 14.3, "closing_time": 14.3, "reference_travel_cm": 110,
             "geometry": {"slat_time_s": 2.7, "opening_roll": 2.07, "closing_roll": 2.33}}
    inherited = profile_motion(short, travel_cm=198)
    window = CoverMotionModel(opening_time_s=22.2, closing_time_s=21.3, slat_time_s=4.4, opening_roll=1.86, closing_roll=2.21)

    up = CalibrationCheck.plan(inherited, 198)
    assert up.planned_seconds == pytest.approx(15.43, abs=.05)
    up.ran(up.planned_seconds)
    really = 198 * height_after(up.planned_seconds, model=window)
    assert really == pytest.approx(108.6, abs=.2)
    up.read(round(really, 1))
    assert up.view() == {"direction": "opening", "target_cm": 99.0, "check_seconds": pytest.approx(15.43, abs=.05),
                         "expected_cm": 99.0, "measured_cm": 108.6, "deviation_cm": 10, "passed": False}

    down = CalibrationCheck.plan(inherited, 198, "closing")
    down.ran(down.planned_seconds)
    really = 198 * height_after(down.planned_seconds, opening=False, model=window)
    down.read(round(really, 1))
    assert (down.expected_cm, down.deviation_cm, down.passed) == (99.0, 3, True)


# ---------------------------------------------------------------------------------
# The check in a geometry session.
# ---------------------------------------------------------------------------------
async def test_a_check_from_review_homes_runs_timed_and_returns_the_verdict(hass, geometry):
    cal = geometry
    await review(cal)
    sent = len(cal.queue)
    assert cal.session.view()["check"] is None and cal.session.view()["check_threshold_cm"] == 4
    await act(cal, "check")
    view = cal.session.view()
    # Its own briefing first: nothing moves until `next`.
    assert (view["phase"], view["step"], cal.session.after_position) == ("briefing", "home", "check")
    assert view["check"]["direction"] == "opening" and view["check"]["target_cm"] == 100.0
    assert len(cal.queue) == sent
    # Every reader sees the transition.
    assert cal.connection.send_event.call_args.args[1]["step"] == "home"
    assert cal.connection.send_event.call_args.args[1]["sequence"] == view["sequence"]
    await endpoint(cal, 9)
    assert (cal.session.phase, cal.session.step, cal.session.view()["check"]["expected_cm"]) == ("briefing", "check", None)
    await start(cal)
    planned = 2 + 20 * winding(.5, 2)
    assert cal.session.deadline.when() - hass.loop.time() == pytest.approx(planned, abs=.1)
    cal.clock[0] += planned - .2
    callback = cal.session.deadline._callback
    cal.session.deadline.cancel()
    callback()
    await stopped(cal, elapsed=.7)  # The Stop leaves half a second late.
    view = cal.session.view()
    assert (view["phase"], view["step"], view["reading_kind"], view["can_repeat"]) == ("reading", "check", "check", True)
    assert view["check"]["check_seconds"] == pytest.approx(planned + .5)
    expected = tenth(TRAVEL * height_after(planned + .5))
    assert view["check"]["expected_cm"] == expected and view["expected_cm"] is None
    # The bus saw exactly: down to the bottom, Stop, up, the timed Stop. Nothing at the reading.
    assert commands(cal, sent) == [LOWER, STOP, RAISE, STOP]
    await act(cal, "reading", reading_cm=expected + 4.5)
    view = cal.session.view()
    assert (view["phase"], view["step"], view["can_repeat"]) == ("review", "half_close", True)
    assert view["check"] == {"direction": "opening", "target_cm": 100.0, "check_seconds": pytest.approx(planned + .5),
                             "expected_cm": expected, "measured_cm": expected + 4.5, "deviation_cm": 5, "passed": False}
    assert commands(cal, sent) == [LOWER, STOP, RAISE, STOP]
    # The measurement is untouched and Save stays available whatever the verdict.
    assert cal.session.values == {"opening_time": 22, "closing_time": 20}
    assert cal.session.geometry == pytest.approx({"slat_time_s": 2, "opening_roll": 2, "closing_roll": 3})
    result = await act(cal, "save", name="Checked roll")
    assert result["phase"] == "saved" and result["check"] is None
    # The last tape reading is the check's: it seeds the runtime position.
    assert cal.cover._motion.position.height == pytest.approx((expected + 4.5) / TRAVEL)


async def test_a_check_downwards_to_a_chosen_height_homes_at_the_top(hass, geometry):
    cal = geometry
    await review(cal)
    sent = len(cal.queue)
    await act(cal, "check", direction="closing", target_cm=50)
    assert (cal.session.step, cal.session.view()["check"]["target_cm"]) == ("top", 50.0)
    await endpoint(cal, 9)
    planned = await timed(cal)
    assert planned == pytest.approx(18 * (1 - winding(.25, 3)))
    assert commands(cal, sent) == [RAISE, STOP, LOWER, STOP]
    assert cal.session.check.expected_cm == 50.0
    await act(cal, "reading", reading_cm=46.5)
    assert cal.session.view()["check"]["deviation_cm"] == -4
    assert cal.session.view()["check"]["passed"] is True


async def test_the_reading_takes_decimals_and_refuses_values_outside_the_travel(geometry):
    cal = geometry
    await review(cal)
    await checked(cal)
    expected = cal.session.check.expected_cm
    for value in (-.1, 0, .05, TRAVEL + .1, float("nan"), True):
        with pytest.raises(ProfileError, match="invalid_reading"):
            await act(cal, "reading", reading_cm=value)
        assert cal.session.phase == "reading" and cal.session.view()["check"]["measured_cm"] is None
    # 99,5 typed in the panel arrives as 99.5.
    await act(cal, "reading", reading_cm=expected - .5)
    assert cal.session.view()["check"]["deviation_cm"] == -1 and cal.session.check.passed


async def test_repeat_on_the_reading_runs_the_same_check_again_from_its_end_stop(geometry):
    cal = geometry
    await review(cal)
    await checked(cal, direction="closing", target_cm=60)
    sent = len(cal.queue)
    await act(cal, "repeat")
    view = cal.session.view()
    assert (view["phase"], view["step"], cal.session.after_position) == ("briefing", "top", "check")
    assert view["check"] == {"direction": "closing", "target_cm": 60.0, "check_seconds": None, "expected_cm": None,
                             "measured_cm": None, "deviation_cm": None, "passed": None}
    assert len(cal.queue) == sent
    await endpoint(cal, 5)
    await timed(cal)
    await act(cal, "reading", reading_cm=60)
    assert cal.session.check.passed is True and cal.session.phase == "review"


async def test_repeating_a_measurement_after_a_check_clears_it(geometry):
    cal = geometry
    await review(cal)
    await checked(cal)
    await act(cal, "reading", reading_cm=cal.session.check.expected_cm)
    await act(cal, "repeat")
    assert (cal.session.step, cal.session.after_position) == ("top", "half_close")
    assert cal.session.check is None and cal.session.view()["check"] is None


async def test_stop_in_review_keeps_the_verdict(geometry):
    cal = geometry
    await review(cal)
    await checked(cal)
    await act(cal, "reading", reading_cm=cal.session.check.expected_cm)
    verdict = cal.session.view()["check"]
    await act(cal, "stop")
    assert cal.session.phase == "review" and cal.session.view()["check"] == verdict


@pytest.mark.parametrize("moment", ["briefing", "homing", "running", "reading"])
async def test_stop_during_a_check_interrupts_like_any_run_and_clears_it(geometry, moment):
    cal = geometry
    await review(cal)
    await act(cal, "check")
    if moment != "briefing":
        await start(cal)
    if moment in {"running", "reading"}:
        cal.clock[0] += 4
        await act(cal, "endpoint")
        await stopped(cal, elapsed=.4)
        await start(cal) if moment == "running" else await timed(cal)
    await act(cal, "stop")
    view = cal.session.view()
    assert view["phase"] == "interrupted" and view["check"] is None and cal.session.check is None
    assert view["geometry"] == {} and view["values"] == {}


async def test_a_new_check_drops_the_old_verdict_and_an_interruption_before_its_run_leaves_none(geometry):
    """Fork `test_calibration_session_paths.py:1344`: a check that gives up takes its answer with it."""
    cal = geometry
    await review(cal)
    await checked(cal)
    await act(cal, "reading", reading_cm=cal.session.check.expected_cm + 5)
    assert cal.session.view()["check"]["deviation_cm"] == 5
    await act(cal, "check")
    assert cal.session.view()["check"]["deviation_cm"] is None
    await act(cal, "next")
    assert cal.queue[-1][1]()
    cal.queue[-1][3].cancel()  # The return to the bottom never reached the bus.
    await asyncio.sleep(0)
    assert cal.session.reason == "not_delivered" and cal.session.view()["check"] is None


async def test_a_check_movement_the_bus_contradicts_interrupts(geometry):
    cal = geometry
    await review(cal)
    await act(cal, "check")
    await endpoint(cal, 9)
    await start(cal)
    callback = cal.session.deadline._callback
    cal.session.deadline.cancel()
    callback()  # Timed Stop requested; the actuator then reports the opposite direction.
    bus(cal, LOWER)
    assert cal.session.reason == "unexpected_movement" and cal.session.view()["check"] is None


async def test_a_check_is_offered_only_in_review_to_its_owner_with_the_current_sequence(hass, geometry):
    cal = geometry
    with pytest.raises(ProfileError, match="calibration_step"):
        await act(cal, "check")  # The very first briefing: nothing measured yet.
    await review(cal)
    sent = len(cal.queue)
    with pytest.raises(ProfileError, match="calibration_step"):
        await cal.session.action({"action": "check", "sequence": cal.session.sequence - 1})
    other = reader(cal, "second-tab")
    assert await call(hass, cal, other.connection, other.token, "check") == "calibration_owned"
    owner = next(item for item in cal.session.subscribers.values() if item.client_id == "owner")
    assert (await call(hass, cal, cal.connection, owner.token, "check"))["step"] == "home"
    with pytest.raises(ProfileError, match="calibration_step"):
        await act(cal, "check")  # Already in a check.
    assert len(cal.queue) == sent


@pytest.mark.parametrize("extra", [{"target_cm": 0}, {"target_cm": 200}, {"target_cm": 250}, {"target_cm": -5},
                                   {"direction": "sideways"}])
async def test_a_check_the_cover_cannot_make_sends_nothing_and_keeps_review(geometry, extra):
    """Fork `test_calibration_session_paths.py:1304`: refused, not clamped into another run."""
    cal = geometry
    await review(cal)
    sent, sequence = len(cal.queue), cal.session.sequence
    with pytest.raises(ProfileError, match="invalid_check"):
        await act(cal, "check", **extra)
    assert (cal.session.phase, cal.session.step, cal.session.sequence) == ("review", "half_close", sequence)
    assert cal.session.view()["check"] is None and len(cal.queue) == sent


async def test_a_refused_check_keeps_the_previous_verdict(geometry):
    cal = geometry
    await review(cal)
    await checked(cal)
    await act(cal, "reading", reading_cm=cal.session.check.expected_cm)
    verdict = cal.session.view()["check"]
    with pytest.raises(ProfileError, match="invalid_check"):
        await act(cal, "check", target_cm=500)
    assert cal.session.view()["check"] == verdict


async def test_the_check_is_null_once_the_session_ends(geometry):
    cal = geometry
    await review(cal)
    await checked(cal)
    await act(cal, "reading", reading_cm=cal.session.check.expected_cm)
    cal.session.close()
    view = cal.session.view()
    assert view["phase"] == "cancelled" and view["check"] is None


async def test_timing_only_sessions_refuse_check(geometry):
    cal = geometry
    cal.session.mode = "guided"
    with pytest.raises(ProfileError, match="calibration_step"):
        await act(cal, "check")


async def test_the_websocket_schema_takes_a_direction_and_a_numeric_target(hass, plant, hass_ws_client):
    plant.gateways[0].async_queue_calibration = MagicMock()
    request = {"entry_id": plant.entries[0].entry_id, "entity_id": plant.records[0].entity_id, "revision": 0}
    register_api(hass)
    with patch("aiohttp.connector.DefaultResolver", ThreadedResolver):
        client = await hass_ws_client(hass)
        try:
            await client.send_json({"id": 1, "type": WS_START, **request, "mode": "geometry", "client_id": "owner"})
            assert (await client.receive_json())["success"]
            event = (await client.receive_json())["event"]
            assert event["check"] is None and event["check_threshold_cm"] == 4
            base = {"type": WS_ACTION, "entry_id": request["entry_id"], "session_id": event["session_id"],
                    "attachment": event["attachment"], "sequence": event["sequence"], "action": "check"}
            for number, extra in enumerate([{"direction": "up"}, {"target_cm": "100"}], start=2):
                await client.send_json({"id": number, **base, **extra})
                assert (await client.receive_json())["error"]["code"] == "invalid_format"
            await client.send_json({"id": 4, **base, "direction": "closing", "target_cm": 80.5})
            assert (await client.receive_json())["error"]["code"] == "calibration_step"  # Valid, but not in review.
        finally:
            await client.close()
    await hass.async_block_till_done()
