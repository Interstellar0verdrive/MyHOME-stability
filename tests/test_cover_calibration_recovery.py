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

