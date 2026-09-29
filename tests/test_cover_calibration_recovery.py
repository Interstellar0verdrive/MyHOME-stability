"""Sessions read from several tabs: one owner, a lost socket changes nothing, no replayed motion."""
import copy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp.resolver import ThreadedResolver
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import Unauthorized
from pytest_socket import socket_enabled  # noqa: F401

from custom_components.myhome.cover_calibration import (
    IDLE_LEASE_SECONDS,
    LEASE_SECONDS,
    MOVED_LEASE_SECONDS,
    PRESENCE_SECONDS,
    WS_ACTION,
    WS_START,
    begin,
    register_api,
    ws_action,
)
from custom_components.myhome.cover_calibration_batch import begin_batch
from custom_components.myhome.cover_calibration_recovery import WS_RESUME, ws_resume
from custom_components.myhome.cover_profiles import (
    ProfileError,
    get_store,
    read_profile,
    remove_entry,
)
from tests.test_cover_calibration_batch import batch as batch_fixture
from tests.test_cover_calibration_batch import measure
from tests.test_cover_profiles import plant as plant_fixture
from tests.test_panel_cover_calibration import act, bus, measured
from tests.test_panel_cover_calibration import calibration as calibration_fixture

plant = plant_fixture
calibration = calibration_fixture
batch = batch_fixture


@pytest.fixture
async def recovering(hass, calibration):
    cal = calibration
    cal.session.close()
    cal.queue.clear()
    cal.request["client_id"] = "first-controller"
    cal.session = await begin(hass, cal.connection, cal.request)
    yield cal
    cal.session.close()


def disconnect(cal):
    cal.connection.subscriptions[77]()


def fire(handle):
    callback, args = handle._callback, handle._args
    handle.cancel()
    callback(*args)


def reader(cal, client_id, subscription_id=88, *, claim=False, sequence=None):
    """A second tab or socket subscribing with `resume`; returns its connection and token."""
    connection = MagicMock(subscriptions={}, user=SimpleNamespace(is_admin=True))
    subscriber, claimed = cal.session.attach(connection, subscription_id, client_id, claim=claim, sequence=sequence)
    return SimpleNamespace(connection=connection, token=subscriber.token, claimed=claimed)


async def call(hass, cal, connection, token, action, **extra):
    """One `action` over the websocket handler; returns the result or the error code."""
    connection.send_result.reset_mock()
    connection.send_error.reset_mock()
    ws_action(hass, connection, {"id": 9, "entry_id": cal.session.entry_id, "session_id": cal.session.id,
                                 "attachment": token, "action": action, "sequence": cal.session.sequence, **extra})
    await hass.async_block_till_done()
    if connection.send_error.called:
        return connection.send_error.call_args.args[1]
    return connection.send_result.call_args.args[1]


async def running(cal):
    """The owner has started a movement and the bus reports it."""
    await act(cal, "open")
    assert cal.queue[-1][1]()
    bus(cal, "*2*1*11##")
    assert cal.session.phase == "opening" and cal.session.reservation.pending


@pytest.mark.parametrize("checkpoint", ["initial", "half", "review"])
async def test_lost_socket_keeps_checkpoint_owner_and_evidence_without_commands(hass, recovering, checkpoint):
    cal, session = recovering, recovering.session
    if checkpoint == "review":
        await measured(cal)
    elif checkpoint == "half":
        await act(cal, "open")
        assert cal.queue[-1][1]()
        bus(cal, "*2*1*11##")
        cal.clock[0] += 22
        await act(cal, "endpoint")
    phase, values, evidence = session.phase, dict(session.values), copy.deepcopy(session.provenance)
    before, sequence = len(cal.queue), session.sequence
    assert (await call(hass, cal, cal.connection, session.attachment, "heartbeat"))["owner"] is True
    old_cleanup = cal.connection.subscriptions[77]
    old_token = session.attachment
    disconnect(cal)
    assert session.store.calibration is session and session.subscribers == {}
    assert (session.phase, session.values, session.provenance, session.sequence) == (phase, values, evidence, sequence)
    assert len(cal.queue) == before
    view = await read_profile(hass, session.entry_id, cal.cover.entity_id)
    assert view["calibration"]["session_id"] == session.id
    assert view["calibration"]["attached"]  # The owner is still present for 45 s.
    assert "attachment" not in view["calibration"]
    cal.clock[0] += PRESENCE_SECONDS + 1
    view = await read_profile(hass, session.entry_id, cal.cover.entity_id)
    assert not view["calibration"]["attached"] and view["calibration"]["recoverable"]
    # The same tab on a new socket: still the owner, and the old token is powerless.
    again = reader(cal, "first-controller", 88)
    assert not again.claimed and session.owner == "first-controller" and session.present()
    old_cleanup()
    assert again.token in session.subscribers
    for action in ("heartbeat", "stop", "cancel", "detach"):
        assert await call(hass, cal, cal.connection, old_token, action) == "calibration_expired"
    assert len(cal.queue) == before and session.sequence == sequence
    if checkpoint == "review":
        result = await call(hass, cal, again.connection, again.token, "save", name="Recovered")
        assert result["phase"] == "saved" and result["owner"] is True
        assert session.store.data["revision"] == 1


@pytest.mark.parametrize("phase", ["starting_open", "opening", "closing", "settling", "between_covers"])
async def test_lost_socket_during_cycle_keeps_measurement_and_writes_no_stop(recovering, phase):
    cal, session = recovering, recovering.session
    await act(cal, "open")
    guard = cal.queue[-1][1]
    session.phase = phase
    session.values["opening_time"] = 22
    session.settle = session.hass.loop.call_later(100, lambda: None)
    count = len(cal.queue)
    disconnect(cal)
    assert guard() is (phase == "starting_open")  # The queued Open is still the owner's.
    cal.clock[0] += 120  # Well past presence: nothing depends on it.
    assert session.phase == phase and session.values == {"opening_time": 22}
    assert not session.settle.cancelled() and not session.deadline.cancelled()
    assert len(cal.queue) == count and not session.closed
    session.attach(cal.connection, 78, "first-controller")
    assert len(cal.queue) == count
    session.settle.cancel()


async def test_idle_lease_ends_session_without_stop_when_nothing_moves(recovering):
    cal, session = recovering, recovering.session
    lease = session.lease
    assert session.lease_seconds == IDLE_LEASE_SECONDS
    disconnect(cal)
    assert session.lease is lease  # A lost socket does not touch the lease.
    fire(lease)
    assert session.closed and session.reason == "expired" and cal.queue == []
    assert session.store.calibration is None and cal.cover._calibration is None
    with pytest.raises(ProfileError, match="calibration_expired"):
        session.attach(cal.connection, 90, "too-late")


@pytest.mark.parametrize("cleanup", ["cancel", "unload", "shutdown", "remove"])
async def test_unattended_session_releases_gateway_on_explicit_lifecycle_end(hass, recovering, cleanup):
    cal, session = recovering, recovering.session
    disconnect(cal)
    lease = session.lease
    if cleanup == "cancel":
        again = reader(cal, "first-controller", 80)
        assert (await call(hass, cal, again.connection, again.token, "cancel"))["phase"] == "cancelled"
    elif cleanup == "unload":
        with patch("custom_components.myhome.myhome_device.MyHOMEEntity.async_will_remove_from_hass", new=AsyncMock()):
            await cal.cover.async_will_remove_from_hass()
    elif cleanup == "remove":
        await remove_entry(hass, session.entry_id)
    else:
        hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
        await hass.async_block_till_done()
    session.close()
    assert session.closed and lease.cancelled()
    assert session.store.calibration is None and cal.cover._calibration is None


async def test_review_save_failure_after_lost_socket_remains_recoverable(hass, recovering):
    cal, session = recovering, recovering.session
    await measured(cal)
    values = dict(session.values)
    async def fail(_data):
        disconnect(cal)
        raise OSError("disk")
    with patch.object(session.store.store, "async_save", side_effect=fail):
        with pytest.raises(OSError):
            await act(cal, "save", name="Retry")
    assert session.phase == "review" and session.values == values and session.subscribers == {}
    again = reader(cal, "first-controller", 80)
    assert (await call(hass, cal, again.connection, again.token, "save", name="Retry"))["phase"] == "saved"
    assert session.store.data["revision"] == 1


async def test_accepted_save_completes_after_lost_socket(recovering):
    cal, session = recovering, recovering.session
    await measured(cal)
    original = session.store.store.async_save
    async def save(data):
        disconnect(cal)
        await original(data)
    with patch.object(session.store.store, "async_save", side_effect=save):
        await act(cal, "save", name="Accepted")
    assert session.closed and session.phase == "saved" and session.lease.cancelled()
    assert session.store.data["revision"] == 1 and session.store.calibration is None


async def test_replayed_start_reads_its_session_and_never_takes_it(hass, recovering):
    cal, session = recovering, recovering.session
    await running(cal)
    count, sequence = len(cal.queue), session.sequence
    claimed = reader(cal, "second-tab", claim=True, sequence=session.sequence)
    assert claimed.claimed and session.owner == "second-tab"
    sequence = session.sequence
    # Home Assistant replays the first tab's start after a reconnection.
    assert await begin(hass, cal.connection, cal.request) is session
    assert session.owner == "second-tab" and session.sequence == sequence
    for changes in ({"client_id": "other"}, {"mode": "automatic"}, {"direction": "opening"},
                    {"entity_id": cal.plant.records[1].entity_id}):
        with pytest.raises(ProfileError, match="calibration_busy"):
            await begin(hass, cal.connection, {**cal.request, **changes})
    disconnect(cal)
    assert await begin(hass, cal.connection, cal.request) is session
    assert len(cal.queue) == count and session.phase == "opening"


async def test_batch_review_survives_recovery_and_replay(hass, batch):
    batch.session.close()
    batch.queue.clear()
    batch.request["client_id"] = "batch-controller"
    batch.session = await begin_batch(hass, batch.connection, batch.request)
    await measure(batch)
    results = copy.deepcopy(batch.session.results)
    disconnect(batch)
    assert await begin_batch(hass, batch.connection, batch.request) is batch.session
    assert batch.session.results == results
    assert len(batch.queue) == 6
    await batch.session.action({"action": "save", "sequence": batch.session.sequence, "names": ["One", "Two"]})
    assert batch.session.store.data["revision"] == 2


async def test_resume_endpoint_reads_live_sessions_and_rejects_missing_stale_and_legacy(hass, recovering):
    cal, session = recovering, recovering.session
    request = {"id": 90, "entry_id": session.entry_id, "session_id": session.id, "client_id": "resume"}
    for changes in ({"entry_id": "missing"}, {"session_id": "stale"}):
        ws_resume(hass, cal.connection, {**request, **changes})
        await hass.async_block_till_done()
        assert cal.connection.send_error.call_args.args[1] == "calibration_expired"
    sequence = session.sequence
    ws_resume(hass, cal.connection, request)
    await hass.async_block_till_done()
    cal.connection.send_result.assert_called_with(90)
    event = cal.connection.send_event.call_args.args
    assert event[0] == 90 and event[1]["read_only"] and not event[1]["owner"]
    assert session.owner == "first-controller" and session.sequence == sequence
    session.client_id = None
    with pytest.raises(ProfileError, match="calibration_expired"):
        session.attach(cal.connection, 90, "legacy")
    session.close()
    ws_resume(hass, cal.connection, request)
    await hass.async_block_till_done()
    assert cal.connection.send_error.call_args.args[1] == "calibration_expired"


def test_resume_requires_admin(hass):
    with pytest.raises(Unauthorized):
        ws_resume(hass, MagicMock(user=SimpleNamespace(is_admin=False)), {"id": 1})


async def test_real_websocket_lost_socket_read_only_resume_and_attachment_authorization(hass, plant, hass_ws_client):
    register_api(hass)
    queue = []
    plant.gateways[0].async_queue_calibration = lambda *args: queue.append(args)
    entry_id = plant.entries[0].entry_id
    with patch("aiohttp.connector.DefaultResolver", ThreadedResolver):
        first = await hass_ws_client(hass)
        await first.send_json({"id": 1, "type": WS_START, "entry_id": entry_id,
            "entity_id": plant.records[0].entity_id, "revision": 0, "client_id": "browser-one"})
        assert (await first.receive_json())["success"]
        state = (await first.receive_json())["event"]
        assert state["owner"] and not state["read_only"] and state["attached"]
        await first.close()
        await hass.async_block_till_done()
        session = get_store(hass, entry_id).calibration
        assert session and not session.closed and session.subscribers == {} and session.owner == "browser-one"
        second = await hass_ws_client(hass)
        await second.send_json({"id": 1, "type": WS_RESUME, "entry_id": entry_id,
            "session_id": state["session_id"], "client_id": "browser-two"})
        assert (await second.receive_json())["success"]
        resumed = (await second.receive_json())["event"]
        assert resumed["phase"] == state["phase"] and resumed["attachment"] != state["attachment"]
        assert resumed["read_only"] and not resumed["owner"] and resumed["sequence"] == state["sequence"]
        action = {"type": WS_ACTION, "entry_id": entry_id, "session_id": session.id, "action": "heartbeat"}
        await second.send_json({"id": 2, **action})
        assert (await second.receive_json())["error"]["code"] == "calibration_expired"
        await second.send_json({"id": 3, **action, "attachment": resumed["attachment"]})
        answer = await second.receive_json()
        assert answer["success"] and answer["result"]["owner"] is False
        await second.send_json({"id": 4, **action, "action": "detach", "attachment": resumed["attachment"]})
        answer = await second.receive_json()
        assert answer["id"] == 4 and answer["result"]["attached"] is False
        assert not session.closed and session.owner == "browser-one"
        await second.close()
        assert queue == []
        session.close()


async def test_close_releases_all_ownership_even_if_stop_queue_unexpectedly_fails(recovering):
    cal, session = recovering, recovering.session
    with patch.object(cal.cover._gateway_handler, "async_queue_calibration", side_effect=RuntimeError("broken queue")):
        with pytest.raises(RuntimeError, match="broken queue"):
            session.close()
    assert session.closed and not session.listener and session.lease.cancelled()
    assert session.store.calibration is None and cal.cover._calibration is None


# ---------------------------------------------------------------------------------
# Ownership per tab, presence and lease (maintainer decisions of 30 September).
# ---------------------------------------------------------------------------------
async def test_attach_only_reads_and_ownership_moves_only_on_an_explicit_claim(hass, recovering):
    """Decision 1: another tab reads; a verb is refused until it claims."""
    cal, session = recovering, recovering.session
    other = reader(cal, "second-tab")
    assert not other.claimed and session.owner == "first-controller"
    for action, extra in (("open", {}), ("cancel", {}), ("save", {"name": "Other"}), ("preview_save", {"save_mode": "shared"})):
        assert await call(hass, cal, other.connection, other.token, action, **extra) == "calibration_owned"
    assert cal.queue == [] and session.phase == "confirm_closed"
    # Presence lapsing does not hand the session over either.
    cal.clock[0] += PRESENCE_SECONDS + 1
    assert not session.present()
    assert await call(hass, cal, other.connection, other.token, "open") == "calibration_owned"
    stale = reader(cal, "second-tab", 89, claim=True, sequence=session.sequence - 1)
    assert not stale.claimed and session.owner == "first-controller"
    sequence = session.sequence
    claimant = MagicMock(subscriptions={}, user=SimpleNamespace(is_admin=True))
    ws_resume(hass, claimant, {"id": 90, "entry_id": session.entry_id, "session_id": session.id,
                               "client_id": "second-tab", "claim": True, "sequence": sequence})
    await hass.async_block_till_done()
    assert session.owner == "second-tab" and session.sequence == sequence + 1
    old_owner = cal.connection.send_event.call_args.args[1]
    assert old_owner["read_only"] and not old_owner["owner"]
    new_owner = claimant.send_event.call_args.args[1]
    assert new_owner["owner"] and not new_owner["read_only"]
    assert await call(hass, cal, cal.connection, session.attachment, "open") == "calibration_owned"
    result = await call(hass, cal, claimant, new_owner["attachment"], "open")
    assert result["phase"] == "starting_open" and len(cal.queue) == 1


async def test_replayed_subscription_with_an_old_sequence_never_takes_control(hass, recovering):
    """Decision 1: a reconnection replays `resume {claim}` with the sequence it last read."""
    cal, session = recovering, recovering.session
    first = reader(cal, "second-tab", claim=True, sequence=session.sequence)
    assert first.claimed
    session.emit()
    back = reader(cal, "first-controller", 91, claim=True, sequence=session.sequence - 1)
    assert not back.claimed and session.owner == "second-tab"
    # Nor does the first tab's replayed start.
    assert await begin(hass, cal.connection, cal.request) is session
    assert session.owner == "second-tab"


@pytest.mark.parametrize("checkpoint", ["initial", "starting", "running", "review"])
async def test_attach_claim_and_replay_never_send_a_command(hass, recovering, checkpoint):
    """Decision 2: after attach, claim or reconnection nothing reaches the bus by itself."""
    cal, session = recovering, recovering.session
    if checkpoint == "starting":
        await act(cal, "open")
    elif checkpoint == "running":
        await running(cal)
    elif checkpoint == "review":
        await measured(cal)
    before = len(cal.queue)
    phase = session.phase
    disconnect(cal)
    assert await begin(hass, cal.connection, cal.request) is session
    ws_resume(hass, cal.connection, {"id": 92, "entry_id": session.entry_id, "session_id": session.id,
                                     "client_id": "second-tab"})
    await hass.async_block_till_done()
    ws_resume(hass, cal.connection, {"id": 93, "entry_id": session.entry_id, "session_id": session.id,
                                     "client_id": "second-tab", "claim": True, "sequence": session.sequence})
    await hass.async_block_till_done()
    assert session.owner == "second-tab"
    assert len(cal.queue) == before and session.phase == phase


async def test_stop_is_accepted_from_every_reader_and_nothing_else_is(hass, recovering):
    """Decision 3: Stop is a safety control; its behaviour is still #374's (L2 changes it)."""
    cal, session = recovering, recovering.session
    await running(cal)
    other = reader(cal, "second-tab")
    for action in ("endpoint", "cancel", "save"):
        assert await call(hass, cal, other.connection, other.token, action) == "calibration_owned"
    count = len(cal.queue)
    result = await call(hass, cal, other.connection, other.token, "stop")
    assert result["phase"] == "interrupted" and result["reason"] == "stopped" and result["read_only"]
    assert len(cal.queue) == count + 1 and str(cal.queue[-1][0]) == "*2*0*11##"
    assert session.owner == "first-controller"  # Stop did not take the session.


async def test_heartbeat_never_takes_the_session_and_moves_nothing(hass, recovering):
    """Fork test_a_heartbeat_never_takes_the_session_over, and the lease is not renewed."""
    cal, session = recovering, recovering.session
    other = reader(cal, "second-tab")
    cal.clock[0] += PRESENCE_SECONDS + 5
    lease, sequence = session.lease, session.sequence
    for _ in range(3):
        beat = await call(hass, cal, other.connection, other.token, "heartbeat")
        assert beat["owner"] is False and beat["read_only"] is True
    assert session.owner == "first-controller" and not session.present()
    beat = await call(hass, cal, cal.connection, session.attachment, "heartbeat")
    assert beat["owner"] is True and session.present()
    assert session.lease is lease and session.sequence == sequence


async def test_presence_lapsing_during_a_run_stops_nothing_and_the_same_tab_carries_on(hass, recovering):
    """Acceptance: 120 s without heartbeat during a run; no Stop; the same tab records it."""
    cal, session = recovering, recovering.session
    await running(cal)
    count = len(cal.queue)
    disconnect(cal)
    cal.clock[0] += 120
    assert session.phase == "opening" and not session.closed and len(cal.queue) == count
    other = reader(cal, "second-tab")
    assert await call(hass, cal, other.connection, other.token, "endpoint") == "calibration_owned"
    again = reader(cal, "first-controller", 94)
    result = await call(hass, cal, again.connection, again.token, "endpoint")
    assert result["owner"] and result["values"] == {"opening_time": 120}
    assert len(cal.queue) == count + 1  # The Stop that ends every guided run, sent by the verb.


async def test_lease_is_half_an_hour_idle_and_ten_minutes_after_a_movement(hass, recovering):
    """Fork test_the_lease_is_the_dialog_s_watchdog_and_gives_the_shutter_back."""
    cal, session = recovering, recovering.session
    view = session.view()
    assert view["recovery_seconds"] == IDLE_LEASE_SECONDS == 1800
    assert session.lease.when() - hass.loop.time() == pytest.approx(IDLE_LEASE_SECONDS, abs=1)
    assert view["idle_expires_at"] is not None
    await act(cal, "open")
    assert session.view()["recovery_seconds"] == MOVED_LEASE_SECONDS == 600
    assert session.lease.when() - hass.loop.time() == pytest.approx(MOVED_LEASE_SECONDS, abs=1)
    fire(session.lease)
    view = session.view()
    assert session.closed and view["reason"] == "expired" and view["idle_expires_at"] is None
    assert not view["recoverable"] and not view["attached"]


@pytest.mark.parametrize("state", ["untouched", "measured_and_stopped", "moving"])
async def test_lease_expiry_writes_stop_only_while_a_movement_may_run(recovering, state):
    """Fork test_the_lease_stops_a_shutter_that_is_still_running_when_it_runs_out."""
    cal, session = recovering, recovering.session
    if state == "moving":
        await running(cal)
    elif state == "measured_and_stopped":
        await running(cal)
        cal.clock[0] += 22
        await act(cal, "endpoint")
        bus(cal, "*2*0*11##")
        assert not session.reservation.pending
    count = len(cal.queue)
    fire(session.lease)
    assert session.closed and session.reason == "expired"
    assert len(cal.queue) == count + (state == "moving")
    if state == "moving":
        assert str(cal.queue[-1][0]) == "*2*0*11##"
    assert (session.store.calibration is None) is (state != "moving")


async def test_every_transition_moves_the_sequence_and_rearms_the_lease_and_reads_move_neither(hass, recovering):
    """Fork test_every_transition_moves_the_revision_and_restarts_the_lease."""
    cal, session = recovering, recovering.session
    token = session.attachment

    async def movement_feedback():
        assert cal.queue[-1][1]()
        bus(cal, "*2*1*11##")

    for step in (lambda: call(hass, cal, cal.connection, token, "open"), movement_feedback,
                 lambda: call(hass, cal, cal.connection, token, "endpoint")):
        lease, sequence = session.lease, session.sequence
        await step()
        assert session.sequence == sequence + 1 and session.lease is not lease and lease.cancelled()
    lease, sequence = session.lease, session.sequence
    await call(hass, cal, cal.connection, token, "heartbeat")
    other = reader(cal, "second-tab")
    await call(hass, cal, other.connection, other.token, "heartbeat")
    assert await begin(hass, cal.connection, cal.request) is session
    await read_profile(hass, session.entry_id, cal.cover.entity_id)
    assert session.lease is lease and session.sequence == sequence


async def test_leave_from_a_reader_that_is_not_the_owner_does_nothing(hass, recovering):
    """Fork test_leave_from_a_client_that_is_not_the_owner_does_nothing."""
    cal, session = recovering, recovering.session
    other = reader(cal, "second-tab")
    result = await call(hass, cal, other.connection, other.token, "detach")
    assert result["attached"] is False and not session.closed and session.owner == "first-controller"
    cal.clock[0] += PRESENCE_SECONDS + 1
    late = reader(cal, "second-tab", 95)
    await call(hass, cal, late.connection, late.token, "detach")
    assert not session.closed and session.owner == "first-controller" and cal.queue == []


@pytest.mark.parametrize("moved", [False, True])
async def test_owner_leaving_ends_an_untouched_session_and_keeps_a_measured_one(hass, recovering, moved):
    cal, session = recovering, recovering.session
    if moved:
        await running(cal)
        cal.clock[0] += 22
        await act(cal, "endpoint")
    count = len(cal.queue)
    result = await call(hass, cal, cal.connection, session.attachment, "detach")
    assert result["attached"] is False and len(cal.queue) == count
    if not moved:
        assert session.closed and session.reason == "left" and session.store.calibration is None
        return
    assert not session.closed and session.owner == "first-controller" and not session.present()
    assert session.values == {"opening_time": 22}
    again = reader(cal, "first-controller", 96)
    assert (await call(hass, cal, again.connection, again.token, "heartbeat"))["owner"] is True


async def test_owner_leaving_an_interrupted_session_releases_it_without_stop(hass, recovering):
    cal, session = recovering, recovering.session
    await running(cal)
    bus(cal, "*2*2*11##")  # Unexpected movement: the #374 interruption, unchanged.
    assert session.phase == "interrupted"
    count = len(cal.queue)
    await call(hass, cal, cal.connection, session.attachment, "detach")
    assert session.closed and session.reason == "left" and len(cal.queue) == count


async def test_clients_without_client_id_keep_the_original_contract(hass, calibration):
    """Decision 4: no owner keys, heartbeat lease, and `detach` or a lost socket cancels."""
    cal, session = calibration, calibration.session
    assert {"owner", "read_only", "idle_expires_at", "recoverable"}.isdisjoint(session.view())
    assert session.lease.when() - hass.loop.time() == pytest.approx(LEASE_SECONDS, abs=1)
    await act(cal, "open")
    assert cal.queue[-1][1]()
    bus(cal, "*2*1*11##")
    ws_action(hass, cal.connection, {"id": 2, "entry_id": session.entry_id, "session_id": "stale", "action": "detach"})
    await hass.async_block_till_done()
    assert cal.connection.send_error.call_args.args[1] == "calibration_expired" and not session.closed
    ws_action(hass, cal.connection, {"id": 3, "entry_id": session.entry_id, "session_id": session.id, "action": "detach"})
    await hass.async_block_till_done()
    assert session.closed and session.reason == "disconnected"
    assert str(cal.queue[-1][0]) == "*2*0*11##"
    count = len(cal.queue)
    session.detach(session.attachment, "heartbeat_timeout")  # A late lease cannot close it twice.
    assert session.reason == "disconnected" and len(cal.queue) == count


async def test_real_websockets_two_tabs_one_owner_and_a_lost_socket(hass, plant, hass_ws_client):
    """Fork websocket tests 906 and 978: every reader is told who holds the session; a socket closing ends nothing."""
    register_api(hass)
    queue = []
    plant.gateways[0].async_queue_calibration = lambda *args: queue.append(args)
    entry_id = plant.entries[0].entry_id
    start = {"type": WS_START, "entry_id": entry_id, "entity_id": plant.records[0].entity_id,
             "revision": 0, "client_id": "tab-one"}

    async def answer(client, message_id):
        while (message := await client.receive_json())["id"] != message_id or message["type"] != "result":
            pass
        return message

    async def event(client, subscription):
        while (message := await client.receive_json())["id"] != subscription or message["type"] != "event":
            pass
        return message["event"]

    with patch("aiohttp.connector.DefaultResolver", ThreadedResolver):
        one = await hass_ws_client(hass)
        await one.send_json({"id": 1, **start})
        assert (await answer(one, 1))["success"]
        state = await event(one, 1)
        two = await hass_ws_client(hass)
        await two.send_json({"id": 1, "type": WS_RESUME, "entry_id": entry_id, "session_id": state["session_id"],
                             "client_id": "tab-two"})
        assert (await answer(two, 1))["success"]
        seen = await event(two, 1)
        assert seen["read_only"] and seen["sequence"] == state["sequence"]
        act_one = {"type": WS_ACTION, "entry_id": entry_id, "session_id": state["session_id"],
                   "attachment": state["attachment"]}
        await one.send_json({"id": 2, **act_one, "action": "open", "sequence": state["sequence"]})
        assert (await answer(one, 2))["result"]["owner"] is True
        moved = await event(two, 1)
        assert moved["phase"] == "starting_open" and moved["read_only"]
        await two.send_json({"id": 2, "type": WS_RESUME, "entry_id": entry_id, "session_id": state["session_id"],
                             "client_id": "tab-two", "claim": True, "sequence": moved["sequence"]})
        assert (await answer(two, 2))["success"]
        taken = await event(one, 1)
        assert taken["read_only"] and not taken["owner"] and taken["sequence"] == moved["sequence"] + 1
        await one.send_json({"id": 3, **act_one, "action": "cancel"})
        assert (await answer(one, 3))["error"]["code"] == "calibration_owned"
        await one.send_json({"id": 4, **act_one, "action": "stop"})
        assert (await answer(one, 4))["result"]["reason"] == "stopped"
        session = get_store(hass, entry_id).calibration
        count = len(queue)
        await two.close()
        await hass.async_block_till_done()
        assert not session.closed and session.owner == "tab-two" and len(queue) == count
        # Home Assistant replays the first tab's start after its own reconnection.
        three = await hass_ws_client(hass)
        await three.send_json({"id": 1, **start})
        assert (await answer(three, 1))["success"]
        replayed = await event(three, 1)
        assert replayed["read_only"] and replayed["sequence"] == session.sequence and len(queue) == count
        await one.close()
        await three.close()
        session.close()
