"""End of run of a modelled timed cover: direct commands, percentage endpoints and wall runs.

The bus timeline is the one recorded on a MyHOMEServer1 with F411-type actuators: a
direction frame is answered by a stop status (~0.08 s) and the direction status
(~0.57 s, the motor start); the actuator reports nothing at the physical end stop and
sends its stop status only when its relay timer expires, 60 s after the start (120 s
with M=1). The cover in these tests closes in 17 s and opens in 20 s.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from OWNd.message import OWNMessage

from custom_components.myhome.cover_motion import END_SETTLE_MARGIN, MotionPosition
from tests.test_cover_nonlinear_backend import nonlinear
from tests.test_cover_profiles import plant as plant_fixture
from tests.test_cover_travel_scaling import write
from tests.test_panel_cover_calibration import act

plant = plant_fixture

REAL_SLEEP = asyncio.sleep
CLOSE, OPEN, STOP = "*2*2*11##", "*2*1*11##", "*2*0*11##"
CLOSING_S, OPENING_S = 17, 20
RELAYED_STOP_S, MOTOR_START_S = 0.08, 0.57  # after the write, from the bus traces
TIMER_S = 60.0  # the actuator's relay timer: its only stop status for a full run

# Reproduction of the reported behaviour; the fix in the next commit removes these marks.
REPRODUCES = pytest.mark.xfail(strict=True, reason="end of run not settled at the model end (reproduction)")


async def settle(rounds=12):
    for _ in range(rounds):
        await REAL_SLEEP(0)


class BusClock:
    """Monotonic time for the cover module; its asyncio.sleep waits for `advance`."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleepers: list[list] = []

    async def sleep(self, delay, *args, **kwargs):
        if delay <= 0:
            await REAL_SLEEP(0)
            return
        entry = [self.now + delay, asyncio.get_running_loop().create_future()]
        self.sleepers.append(entry)
        try:
            await entry[1]
        finally:
            if entry in self.sleepers:
                self.sleepers.remove(entry)

    async def advance(self, seconds):
        target = self.now + seconds
        while True:
            await settle()
            due = [entry for entry in self.sleepers if entry[0] <= target and not entry[1].done()]
            if not due:
                break
            entry = min(due, key=lambda item: item[0])
            self.sleepers.remove(entry)
            self.now = max(self.now, entry[0])
            entry[1].set_result(None)
        self.now = target
        await settle()


@pytest.fixture
async def modelled(hass, plant):
    await write(hass, plant, profile=nonlinear(opening_time=OPENING_S, closing_time=CLOSING_S,
                                               reference_travel_cm=None))
    cover = plant.covers[0]
    assert cover._motion.model is not None and cover._motion.model.closing_time_s == CLOSING_S
    cover.platform = MagicMock()  # _publish_state writes through async_schedule_update_ha_state
    clock = BusClock()
    sent: list[tuple[str, asyncio.Future]] = []

    async def send(command):
        # Written at once (an idle queue); the tests play the gateway's relayed frames.
        future = asyncio.get_running_loop().create_future()
        future.set_result(clock.now)
        sent.append((str(command), future))
        return future

    plant.gateways[0].send = AsyncMock(side_effect=send)
    with patch("custom_components.myhome.cover.time") as cover_time, \
         patch("custom_components.myhome.cover_calibration.monotonic", side_effect=lambda: clock.now), \
         patch("custom_components.myhome.cover.asyncio.sleep", side_effect=clock.sleep):
        cover_time.monotonic.side_effect = lambda: clock.now
        yield SimpleNamespace(cover=cover, clock=clock, sent=sent, plant=plant, hass=hass)
        cover._cancel_stop_task()
        await settle()


def bus(m, raw):
    m.cover.handle_event(OWNMessage.parse(raw))


def at_end(m, height):
    """Put the cover at a confirmed end, as a previous full run leaves it."""
    m.cover._motion.confirm(height)
    m.cover._attr_current_cover_position = m.cover._start_position = height
    m.cover._attr_is_closed = height == 0


async def written_and_started(m, raw):
    """The frame HA queued reaches the bus; the gateway relays a stop status, then the motor start."""
    await settle()
    assert m.sent[-1][0] == raw
    await m.clock.advance(RELAYED_STOP_S)
    bus(m, STOP)
    await m.clock.advance(MOTOR_START_S - RELAYED_STOP_S)
    bus(m, raw)
    return m.clock.now  # motor start


async def wall_run(m, raw):
    """A keypad press: the same relayed frames, no frame from Home Assistant."""
    bus(m, STOP)
    await m.clock.advance(MOTOR_START_S - RELAYED_STOP_S)
    bus(m, raw)
    return m.clock.now


def state(m):
    return m.cover.state, m.cover.current_cover_position


async def until(m, motor_start, seconds):
    await m.clock.advance(motor_start + seconds - m.clock.now)


def commands(m):
    return [command for command, _ in m.sent]


# (a) direct open / close.

@REPRODUCES
@pytest.mark.parametrize("known", [True, False], ids=["from_known", "from_unknown"])
async def test_direct_close_settles_at_the_model_end_not_at_the_timer(modelled, known):
    m = modelled
    if known:
        at_end(m, 100)
    await m.cover.async_close_cover()
    start = await written_and_started(m, CLOSE)
    await until(m, start, CLOSING_S - 1)
    assert m.cover.state == "closing"
    await until(m, start, CLOSING_S + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("closed", 0)
    assert m.cover._motion.position == MotionPosition(0, 0)
    assert commands(m) == [CLOSE]  # a full run ends on the limit switch: no Stop is written
    assert m.cover._stop_task is None


@REPRODUCES
async def test_direct_open_settles_at_the_model_end(modelled):
    m = modelled
    at_end(m, 0)
    await m.cover.async_open_cover()
    start = await written_and_started(m, OPEN)
    await until(m, start, OPENING_S + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("open", 100)
    assert commands(m) == [OPEN]


@REPRODUCES
async def test_direct_close_from_mid_travel_settles_at_the_remaining_model_time(modelled):
    m = modelled
    at_end(m, 100)
    m.cover._motion.position = MotionPosition(0.5, 1)
    m.cover._attr_current_cover_position = m.cover._start_position = 50
    remaining = m.cover._motion.model.duration(MotionPosition(0.5, 1), MotionPosition(0, 0), opening=False)
    await m.cover.async_close_cover()
    start = await written_and_started(m, CLOSE)
    await until(m, start, remaining + END_SETTLE_MARGIN - 0.2)
    assert m.cover.state == "closing"
    await until(m, start, remaining + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("closed", 0)


# (b) set_cover_position 0 / 100.

@REPRODUCES
@pytest.mark.parametrize("known", [True, False], ids=["from_known", "from_unknown"])
async def test_position_zero_is_a_full_run_that_settles_at_the_model_end(modelled, known):
    m = modelled
    if known:
        at_end(m, 100)
    await m.cover.async_set_cover_position(position=0)
    start = await written_and_started(m, CLOSE)
    await until(m, start, CLOSING_S + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("closed", 0)
    assert commands(m) == [CLOSE]


@REPRODUCES
@pytest.mark.parametrize("known", [True, False], ids=["from_known", "from_unknown"])
async def test_position_hundred_is_a_full_run_that_settles_at_the_model_end(modelled, known):
    m = modelled
    if known:
        at_end(m, 0)
    await m.cover.async_set_cover_position(position=100)
    start = await written_and_started(m, OPEN)
    await until(m, start, OPENING_S + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("open", 100)
    assert commands(m) == [OPEN]


# (c) wall commands.

@REPRODUCES
@pytest.mark.parametrize("known", [True, False], ids=["from_known", "from_unknown"])
async def test_wall_close_settles_at_the_model_end(modelled, known):
    m = modelled
    if known:
        at_end(m, 100)
    start = await wall_run(m, CLOSE)
    assert m.cover.state == "closing"
    await until(m, start, CLOSING_S + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("closed", 0)
    assert m.sent == []


@REPRODUCES
async def test_wall_open_settles_and_a_reversal_rearms_for_the_new_direction(modelled):
    m = modelled
    at_end(m, 0)
    start = await wall_run(m, OPEN)
    await until(m, start, 5)
    reversal = await wall_run(m, CLOSE)  # an opposite press while the first run is under way
    await until(m, start, OPENING_S + END_SETTLE_MARGIN + 0.1)
    assert m.cover.state == "closing"  # the opening run's settle is gone
    expected = m.cover._motion.model.duration(m.cover._motion.position, MotionPosition(0, 0), opening=False)
    await until(m, reversal, expected + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("closed", 0)


# (d) a stop before the end.

@pytest.mark.parametrize("command", ["direct", "wall"])
async def test_early_stop_freezes_the_model_position_and_never_settles(modelled, command):
    m = modelled
    at_end(m, 100)
    if command == "direct":
        await m.cover.async_close_cover()
        start = await written_and_started(m, CLOSE)
    else:
        start = await wall_run(m, CLOSE)
    await until(m, start, 8)
    bus(m, STOP)  # a keypad stop, outside any echo window
    expected = m.cover._motion.model.advance(MotionPosition(1, 1), opening=False, motor_seconds=8)
    assert m.cover._motion.position == expected
    assert state(m) == ("open", round(expected.height * 100))
    await until(m, start, TIMER_S + 1)
    assert state(m) == ("open", round(expected.height * 100))
    assert m.cover._stop_task is None


@REPRODUCES
async def test_early_stop_from_an_unknown_position_stays_unknown(modelled):
    m = modelled
    await m.cover.async_close_cover()
    start = await written_and_started(m, CLOSE)
    await until(m, start, 8)
    bus(m, STOP)
    assert state(m) == (None, None)
    await until(m, start, TIMER_S + 1)
    assert state(m) == (None, None)  # never "closed": the model cannot place this stop


# (e) the actuator's late timer stop.

@pytest.mark.parametrize("command", [
    pytest.param("direct", marks=REPRODUCES),
    "position",  # passes before the fix too: the auto-stop writes a Stop at the model time
    pytest.param("wall", marks=REPRODUCES),
])
async def test_late_timer_stop_after_the_settle_changes_nothing(modelled, command):
    m = modelled
    at_end(m, 100)
    if command == "wall":
        start = await wall_run(m, CLOSE)
    else:
        await (m.cover.async_close_cover() if command == "direct" else m.cover.async_set_cover_position(position=0))
        start = await written_and_started(m, CLOSE)
    await until(m, start, CLOSING_S + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("closed", 0)
    writes = m.cover.async_schedule_update_ha_state.call_count
    await until(m, start, TIMER_S)
    assert m.cover.async_schedule_update_ha_state.call_count == writes  # nothing happened in between
    bus(m, STOP)
    assert state(m) == ("closed", 0)
    assert m.cover._motion.position == MotionPosition(0, 0) and m.cover._stop_task is None
    await until(m, start, 2 * TIMER_S + 1)
    assert state(m) == ("closed", 0) and m.cover._stop_task is None


@REPRODUCES
async def test_settle_writes_the_final_state_once(modelled):
    m = modelled
    at_end(m, 100)
    await m.cover.async_close_cover()
    start = await written_and_started(m, CLOSE)
    await until(m, start, CLOSING_S + END_SETTLE_MARGIN - 0.1)
    writes = m.cover.async_schedule_update_ha_state.call_count + m.cover.async_write_ha_state.call_count
    await until(m, start, CLOSING_S + END_SETTLE_MARGIN + 0.1)
    assert m.cover.async_schedule_update_ha_state.call_count + m.cover.async_write_ha_state.call_count == writes + 1


@REPRODUCES
async def test_removal_cancels_a_pending_settle(modelled):
    m = modelled
    at_end(m, 100)
    start = await wall_run(m, CLOSE)
    task = m.cover._stop_task
    assert task is not None and not task.done()
    try:
        await m.cover.async_will_remove_from_hass()
    except Exception:  # noqa: BLE001 - the base-class teardown of an entity built without a platform
        pass
    await settle()
    assert task.cancelled() and m.cover._stop_task is None
    await until(m, start, CLOSING_S + END_SETTLE_MARGIN + 1)
    assert m.cover.state == "closing"


async def test_cover_without_a_motion_model_keeps_its_behaviour(modelled):
    """Out of scope: a linear timed cover with a known position still ends on the actuator's stop."""
    cover = modelled.plant.covers[1]
    assert cover._motion.model is None
    cover._attr_current_cover_position = cover._start_position = 100
    cover.handle_event(OWNMessage.parse("*2*2*12##"))
    assert cover.state == "closing" and cover._stop_task is None


# (f) a guided calibration session owns the cover.

async def begin_session(m, queue):
    from custom_components.myhome.cover_calibration import begin
    from custom_components.myhome.cover_profiles import get_store

    m.plant.gateways[0].async_queue_calibration = lambda message, guard, lock: queue.append((message, guard, lock))
    store = get_store(m.hass, m.plant.entries[0].entry_id)
    connection = MagicMock(subscriptions={}, user=SimpleNamespace(is_admin=True))
    request = {"id": 78, "entry_id": m.plant.entries[0].entry_id, "entity_id": m.plant.records[0].entity_id,
               "revision": store.data["revision"], "mode": "guided"}
    return await begin(m.hass, connection, request)


@pytest.fixture
async def session(modelled):
    queue = []
    calibration = await begin_session(modelled, queue)
    yield SimpleNamespace(session=calibration, queue=queue, cover=modelled.cover, m=modelled)
    calibration.close()


@REPRODUCES
async def test_a_settled_run_leaves_the_cover_ready_for_a_session(modelled):
    m = modelled
    await m.cover.async_close_cover()
    start = await written_and_started(m, CLOSE)
    await until(m, start, CLOSING_S + END_SETTLE_MARGIN + 0.1)
    assert state(m) == ("closed", 0)
    calibration = await begin_session(m, [])  # not refused as calibration_moving
    calibration.close()


@pytest.mark.parametrize("action,frame,run_s", [("open", OPEN, OPENING_S), ("close", CLOSE, CLOSING_S)])
async def test_guided_session_runs_are_never_settled(session, action, frame, run_s):
    cal, m = session, session.m
    if action == "close":
        cal.session.phase = "confirm_open"
    await act(cal, action)
    assert cal.queue[-1][1]()  # the worker writes the raw frame
    await m.clock.advance(2)
    bus(m, frame)  # the session's run, seen by the cover as a run it did not command
    assert cal.session.phase == ("opening" if action == "open" else "closing")
    assert m.cover._stop_task is None
    await m.clock.advance(run_s + END_SETTLE_MARGIN + 5)  # longer than the time in use: still measuring
    assert m.cover.state == ("opening" if action == "open" else "closing")
    assert cal.session.phase == ("opening" if action == "open" else "closing")
    await act(cal, "endpoint")
    assert m.cover.current_cover_position == (100 if action == "open" else 0)
    assert m.cover._stop_task is None
