"""Tests for the gateway handler (Contract B) with a fake OWNd session layer.

Two levels:
- ``MyHOMEGatewayHandler`` is exercised with scriptable fakes replacing
  ``OWNEventChannel`` / ``OWNCommandChannel`` (no sockets at all);
- ``own_session`` is exercised against a tiny OpenWebNet server on the loopback
  interface (framing, negotiation, keepalive, timeouts).  No real gateway is used.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
import time
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager, contextmanager, suppress
from dataclasses import fields
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.button import DOMAIN as BUTTON
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.sensor import DOMAIN as SENSOR
from OWNd.message import OWNCommand, OWNLightingCommand, OWNMessage

from custom_components.myhome import gateway as gateway_module
from custom_components.myhome.const import (
    CONF_COMMAND_TIMEOUT_SEC,
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_IDLE_WATCHDOG_SEC,
    CONF_LONG_PRESS,
    CONF_LONG_RELEASE,
    CONF_PLATFORMS,
    CONF_PROBE_WINDOW_SEC,
    CONF_QUEUE_TTL_SEC,
    CONF_SHORT_PRESS,
    CONF_SHORT_RELEASE,
    DOMAIN,
    EVENT_CEN,
    EVENT_CENPLUS,
    LOGGER,
    SIGNAL_GATEWAY_CONNECTION,
    SIGNAL_GATEWAY_STATS,
)
from custom_components.myhome.gateway import (
    EVENT_LONG_PRESS_REPEAT,
    EVENT_ROTATE_CCW_FAST,
    EVENT_ROTATE_CCW_SLOW,
    EVENT_ROTATE_CW_FAST,
    EVENT_ROTATE_CW_SLOW,
    FRAME_COMMAND,
    FRAME_MONITOR,
    FRAME_REPLY,
    SESSION_STATE_AUTH_FAILED,
    SESSION_STATE_CONNECTED,
    SESSION_STATE_DISCONNECTED,
    GatewayStats,
    MyHOMEGatewayHandler,
    _entity_key_candidates,
    _message_entity_key,
    _QueuedCommand,
)
from custom_components.myhome.myhome_device import MyHOMEEntity
from custom_components.myhome.own_session import (
    AuthenticationError,
    CommandResult,
    OWNCommandChannel,
    OWNEventChannel,
    SessionError,
    enable_tcp_keepalive,
    parse_frame,
)

from .helpers_core import ENTRY_DATA_V2, MAC, wait_until
from .helpers_platforms import FakeGatewayStats

SIGNAL = SIGNAL_GATEWAY_CONNECTION.format(mac=MAC)
STATS_SIGNAL = SIGNAL_GATEWAY_STATS.format(mac=MAC)
LOGGER_NAME = LOGGER.name


def frame(raw: str) -> OWNMessage | str:
    return parse_frame(raw, LOGGER, "[test]")


# --------------------------------------------------------------------------- fakes
class FakeEventChannel:
    """Scriptable stand-in for ``OWNEventChannel``: feed frames / exceptions."""

    def __init__(self) -> None:
        self.frames: asyncio.Queue = asyncio.Queue()
        self.open_calls = 0
        self.closed = False
        self.open_error: BaseException | None = None

    async def open(self, timeout: float) -> None:
        self.open_calls += 1
        if self.open_error is not None:
            raise self.open_error

    async def get_next(self) -> Any:
        item = await self.frames.get()
        if isinstance(item, BaseException):
            raise item
        return item

    async def close(self) -> None:
        self.closed = True

    def feed(self, item: Any) -> None:
        self.frames.put_nowait(frame(item) if isinstance(item, str) else item)


class FakeCommandChannel:
    """Scriptable stand-in for ``OWNCommandChannel``."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.open_calls = 0
        self.closed = False
        self.open_error: BaseException | None = None
        self.responder: Callable[[str], CommandResult] | None = None

    async def open(self, timeout: float) -> None:
        self.open_calls += 1
        if self.open_error is not None:
            raise self.open_error

    async def send_command(self, message: Any, timeout: float) -> CommandResult:
        self.sent.append(str(message))
        if self.responder is not None:
            return self.responder(str(message))
        return CommandResult(True, [])

    async def close(self) -> None:
        self.closed = True


class Factory:
    """Replacement for a channel class: creates ``cls()`` per call, configurable per index."""

    def __init__(self, cls: type, configure: Callable[[Any, int], None] | None = None) -> None:
        self.cls = cls
        self.configure = configure
        self.instances: list[Any] = []

    def __call__(self, gateway: Any, logger: Any) -> Any:
        instance = self.cls()
        if self.configure is not None:
            self.configure(instance, len(self.instances))
        self.instances.append(instance)
        return instance


@contextmanager
def fake_channels(
    event: Factory | None = None, command: Factory | None = None
) -> Iterator[tuple[Factory, Factory, MagicMock]]:
    """Patch the channel classes and the dispatcher inside gateway.py."""
    event = event or Factory(FakeEventChannel)
    command = command or Factory(FakeCommandChannel)
    with (
        patch.object(gateway_module, "OWNEventChannel", event),
        patch.object(gateway_module, "OWNCommandChannel", command),
        patch.object(gateway_module, "async_dispatcher_send") as dispatch,
    ):
        yield event, command, dispatch


class RecordingEntity(MyHOMEEntity):
    """Entity stub that records what the dispatcher delivers."""

    def __init__(self, hass: Any, platform: str, key: str, handler: MyHOMEGatewayHandler, fail: bool = False) -> None:
        who, where = key.split("-", 1)
        super().__init__(hass, f"Test {key}", platform, key, who, where, None, None, handler)
        self.events: list[str] = []
        self.updates = 0
        self.fail = fail

    def handle_event(self, message: OWNMessage) -> None:
        if self.fail:
            raise RuntimeError("entity bug")
        self.events.append(str(message))

    async def async_update(self) -> None:
        self.updates += 1


def make_handler(
    platforms: dict[str, dict[str, dict[str, Any]]] | None = None,
    sensor_defaults: dict[str, Any] | None = None,
    generate_events: bool = False,
    options: dict[str, Any] | None = None,
    fast: bool = True,
) -> MyHOMEGatewayHandler:
    """Handler on a MagicMock hass with fast timings (``fast=False`` keeps the
    values the entry options produced)."""
    hass = MagicMock()
    gateway_cfg: dict[str, Any] = {CONF_PLATFORMS: platforms or {}}
    if sensor_defaults:
        gateway_cfg["sensor_defaults"] = sensor_defaults
    hass.data = {DOMAIN: {MAC: gateway_cfg}}
    hass.bus = MagicMock()
    entry = MagicMock()
    entry.data = dict(ENTRY_DATA_V2)
    entry.options = dict(options or {})
    entry.async_start_reauth = MagicMock()
    handler = MyHOMEGatewayHandler(hass, entry, generate_events=generate_events)
    hass.data[DOMAIN][MAC][CONF_ENTITY] = handler
    if fast:
        handler.initial_backoff = 0.01
        handler.max_backoff = 0.05
        handler.read_poll_interval = 0.03
        handler.idle_timeout = 0.12
        handler.probe_window = 0.1
        handler.command_session_idle = 0.2
        handler.command_timeout = 0.2
        handler.connect_timeout = 0.2
    return handler


def register(handler: MyHOMEGatewayHandler, platform: str, key: str, fail: bool = False, **cfg: Any) -> RecordingEntity:
    """Create a device config entry with a registered entity object."""
    entity = RecordingEntity(handler.hass, platform, key, handler, fail=fail)
    who, where = key.split("-", 1)
    device = {"who": who, "where": where, "name": f"Test {key}", CONF_ENTITIES: {platform: entity}, **cfg}
    handler.hass.data[DOMAIN][MAC][CONF_PLATFORMS].setdefault(platform, {})[key] = device
    return entity


@asynccontextmanager
async def running(handler: MyHOMEGatewayHandler, *, listening: bool = True, sending: bool = True):
    if listening:
        handler.listening_worker = asyncio.create_task(handler.listening_loop())
    if sending:
        handler.sending_workers.append(asyncio.create_task(handler.sending_loop(0)))
    try:
        yield
    finally:
        await handler.close_listener()


class SleepRecorder:
    """``asyncio`` stand-in for gateway.py that records what it is asked to sleep.

    Everything except ``sleep`` is delegated to the real module, so the loops keep
    using real queues and tasks; ``sleep`` returns at once and remembers the delay.
    That turns the reconnect pacing into an assertion on a list instead of an
    assertion on the wall clock (the suite's tightest timing was
    ``2 <= len(instances) <= 8`` after ``asyncio.sleep(0.3)``).
    """

    def __init__(self) -> None:
        self.delays: list[float] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(asyncio, name)

    async def sleep(self, delay: float, *args: Any, **kwargs: Any) -> Any:
        self.delays.append(delay)
        return await asyncio.sleep(0, *args, **kwargs)


@contextmanager
def recorded_sleep() -> Iterator[SleepRecorder]:
    """Replace ``asyncio`` inside gateway.py only, for the duration of the block."""
    recorder = SleepRecorder()
    with patch.object(gateway_module, "asyncio", recorder):
        yield recorder


class FakeClock:
    """Controllable replacement for ``MyHOMEGatewayHandler._now``.

    ``reads`` counts the calls, which is what the idle-watchdog tests wait on: it
    proves the listening loop ran its poll timeout again, without sleeping for a
    guessed number of milliseconds.
    """

    def __init__(self, value: float = 0.0) -> None:
        self.value = value
        self.reads = 0

    def __call__(self) -> float:
        self.reads += 1
        return self.value

    async def advance_to(self, value: float, *, polls: int = 3) -> None:
        """Move the clock and wait until the loop has looked at it ``polls`` times."""
        self.value = value
        target = self.reads + polls
        await wait_until(lambda: self.reads >= target)


def fired(hass: MagicMock, event_type: str) -> list[dict[str, Any]]:
    return [call.args[1] for call in hass.bus.async_fire.call_args_list if call.args[0] == event_type]


def queued(handler: MyHOMEGatewayHandler) -> list[str]:
    return [str(item.message) for item in list(handler.send_buffer._queue)]  # noqa: SLF001


def connection_calls(dispatch: MagicMock) -> list[bool]:
    """Availability payloads only (the handler also publishes stats snapshots)."""
    return [call.args[2] for call in dispatch.call_args_list if call.args[1] == SIGNAL]


def stats_calls(dispatch: MagicMock) -> list[GatewayStats]:
    return [call.args[2] for call in dispatch.call_args_list if call.args[1] == STATS_SIGNAL]


# --------------------------------------------------------------------------- command path
async def test_send_returns_bool_queue_bounded_and_closed() -> None:
    handler = make_handler()
    handler.send_buffer = asyncio.Queue(maxsize=2)
    command = OWNLightingCommand.switch_on("11")
    assert await handler.send(command) is True
    assert await handler.send_status_request(command) is True
    assert await handler.send(command) is False  # full
    assert handler.send_buffer.qsize() == 2
    with fake_channels():
        await handler.close_listener()
    assert handler.send_buffer.qsize() == 0  # drained
    assert await handler.send(command) is False  # closed


async def test_command_acknowledged_replies_dispatched(caplog: pytest.LogCaptureFixture) -> None:
    """sc-01 / gw-13: every reply frame read before the ACK reaches the entities."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    light = register(handler, LIGHT, "1-11")
    meter = register(handler, SENSOR, "18-51", **{"class": "power"})
    replies = [frame("*1*1*11##"), frame("*#18*51*51*1234567##")]

    def configure(channel: FakeCommandChannel, index: int) -> None:
        channel.responder = lambda message: CommandResult(True, list(replies))

    with fake_channels(command=Factory(FakeCommandChannel, configure)) as (_, command, _):
        async with running(handler, listening=False):
            assert await handler.send_status_request(OWNLightingCommand.status("0"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            await wait_until(lambda: meter.events)
    assert command.instances[0].sent == ["*#1*0##"]
    assert light.events == ["*1*1*11##"]
    assert meter.events == ["*#18*51*51*1234567##"]
    assert handler.send_buffer.qsize() == 0


async def test_command_retry_once_in_place_with_fresh_session() -> None:
    """gw-01 / gw-11: a failed send is retried once on a NEW session, never re-queued."""
    handler = make_handler()

    def configure(channel: FakeCommandChannel, index: int) -> None:
        if index == 0:

            def broken(message: str) -> CommandResult:
                raise SessionError("gateway closed the socket")

            channel.responder = broken

    with fake_channels(command=Factory(FakeCommandChannel, configure)) as (_, command, _):
        async with running(handler, listening=False):
            assert await handler.send(OWNLightingCommand.switch_on("11"))
            assert await handler.send(OWNLightingCommand.switch_off("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
    assert len(command.instances) == 2
    assert command.instances[0].sent == ["*1*1*11##"]
    assert command.instances[0].closed
    # Same command first, then the next one: order preserved, no duplicate.
    assert command.instances[1].sent == ["*1*1*11##", "*1*0*11##"]


async def test_command_dropped_after_two_failures(caplog: pytest.LogCaptureFixture) -> None:
    """gw-02: timeout / transport failure twice -> WARNING and drop, queue keeps moving."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()

    def configure(channel: FakeCommandChannel, index: int) -> None:
        if index < 2:

            def hung(message: str) -> CommandResult:
                raise TimeoutError()

            channel.responder = hung

    with fake_channels(command=Factory(FakeCommandChannel, configure)) as (_, command, _):
        async with running(handler, listening=False):
            assert await handler.send(OWNLightingCommand.switch_on("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            assert await handler.send(OWNLightingCommand.switch_on("12"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
    assert [channel.sent for channel in command.instances] == [["*1*1*11##"], ["*1*1*11##"], ["*1*1*12##"]]
    assert handler.send_buffer.qsize() == 0
    assert any(
        "dropped after two attempts" in record.message and record.levelno == logging.WARNING
        for record in caplog.records
    )


async def test_refused_command_is_reported_and_counted(caplog: pytest.LogCaptureFixture) -> None:
    """gw-02: a NACK is not a silent success.

    The command was delivered and the gateway said no. Pins: one rate-limited
    WARNING naming the refused frame, the reply frames of the refused command
    still reaching the entities, and the refusal counting as *sent* rather than
    *dropped* (it was answered). Mutation caught: `if result.acknowledged:` ->
    `if True:` in ``_on_command_result``, which makes the whole else arm dead and
    leaves the user with no trace of the refusal at all.
    """
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    light = register(handler, LIGHT, "1-11")

    def configure(channel: FakeCommandChannel, index: int) -> None:
        channel.responder = lambda message: CommandResult(False, [frame("*1*0*11##")])

    with fake_channels(command=Factory(FakeCommandChannel, configure)):
        async with running(handler, listening=False):
            assert await handler.send(OWNLightingCommand.switch_on("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            await wait_until(lambda: handler.stats.commands_sent == 1)
            # The identical refusal is rate limited: the key is per message.
            assert await handler.send(OWNLightingCommand.switch_on("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            await wait_until(lambda: handler.stats.commands_sent == 2)

    refusals = [
        record
        for record in caplog.records
        if "refused" in record.message and record.levelno == logging.WARNING
    ]
    assert len(refusals) == 1
    assert "*1*1*11##" in refusals[0].message
    assert light.events == ["*1*0*11##", "*1*0*11##"]
    assert handler.stats.commands_dropped == 0  # answered, just not accepted


async def test_command_ttl_expired_is_dropped_without_sending(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    stale = _QueuedCommand(OWNLightingCommand.switch_on("11"), False, time.monotonic() - 120)
    handler.send_buffer.put_nowait(stale)
    with fake_channels() as (_, command, _):
        async with running(handler, listening=False):
            await asyncio.wait_for(handler.send_buffer.join(), 2)
    assert all(channel.sent == [] for channel in command.instances)
    assert any(
        "Dropping `*1*1*11##`" in record.message and record.levelno == logging.WARNING
        for record in caplog.records
    )


async def test_command_auth_failure_starts_reauth() -> None:
    handler = make_handler()

    def configure(channel: FakeCommandChannel, index: int) -> None:
        channel.open_error = AuthenticationError("password_error")

    with fake_channels(command=Factory(FakeCommandChannel, configure)) as (_, command, _):
        async with running(handler, listening=False):
            assert await handler.send(OWNLightingCommand.switch_on("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            await wait_until(lambda: handler.sending_workers[0].done())
    assert handler.auth_failed is True
    handler.config_entry.async_start_reauth.assert_called_once_with(handler.hass)
    assert len(command.instances) == 1
    assert handler.stats.commands_dropped == 1  # the lost command is counted


async def test_idle_command_session_is_closed() -> None:
    handler = make_handler()
    handler.command_session_idle = 0.05
    with fake_channels() as (_, command, _):
        async with running(handler, listening=False):
            assert await handler.send(OWNLightingCommand.switch_on("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            await wait_until(lambda: command.instances[0].closed)
            assert await handler.send(OWNLightingCommand.switch_off("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
    assert len(command.instances) == 2


# --------------------------------------------------------------------------- event path
async def test_none_from_get_next_reconnects_with_backoff_no_hot_loop() -> None:
    """gw-04: None from the session is a broken connection; reconnects are paced.

    The pacing is asserted on the recorded delays rather than on how many
    reconnects fit into a real 0.3 s (which was the tightest wall-clock assertion
    in the suite and could exceed its ``<= 8`` upper bound on a loaded runner):
    every failed attempt but the first must be preceded by exactly one sleep, and
    the delays must grow. Mutation caught: dropping the ``asyncio.sleep(backoff)``
    from the transport-error arm, which turns reconnection into a hot loop.
    """
    handler = make_handler()
    handler.initial_backoff = 0.02
    handler.max_backoff = 0.08

    def configure(channel: FakeEventChannel, index: int) -> None:
        channel.feed(None)

    with recorded_sleep() as sleeps, fake_channels(event=Factory(FakeEventChannel, configure)) as (
        event,
        _,
        dispatch,
    ):
        async with running(handler, sending=False):
            await wait_until(lambda: len(sleeps.delays) >= 4)
            count = len(event.instances)
    # One paced attempt per sleep: never a hot loop, never a stalled loop.
    assert count >= 4
    assert sleeps.delays[:4] == [0.02, 0.04, 0.08, 0.08]
    assert all(channel.closed for channel in event.instances)
    assert connection_calls(dispatch)[:2] == [True, False]


async def test_backoff_stops_growing_at_max_backoff() -> None:
    """gw-04: the reconnect delay is capped, so an overnight outage never ends up
    waiting hours before the next attempt.

    Mutation caught: ``backoff = min(backoff * 2, self.max_backoff)`` ->
    ``backoff = backoff * 2`` in the listening loop. The existing pacing test only
    proves the delay *grows*; nothing proved it stops growing.
    """
    handler = make_handler()
    handler.initial_backoff = 0.01
    handler.max_backoff = 0.02

    def configure(channel: FakeEventChannel, index: int) -> None:
        channel.feed(None)

    with recorded_sleep() as sleeps, fake_channels(event=Factory(FakeEventChannel, configure)):
        async with running(handler, sending=False):
            await wait_until(lambda: len(sleeps.delays) >= 6)
            delays = list(sleeps.delays[:6])
    assert delays == [0.01, 0.02, 0.02, 0.02, 0.02, 0.02]
    assert max(delays) == handler.max_backoff


async def test_transport_error_reconnects_and_signals_availability() -> None:
    """gw-10: is_connected follows the event session and every transition is published once."""
    handler = make_handler()
    with fake_channels() as (event, _, dispatch):
        async with running(handler, sending=False):
            await wait_until(lambda: handler.is_connected)
            event.instances[0].feed(ConnectionResetError("rst"))
            await wait_until(lambda: len(event.instances) == 2 and handler.is_connected)
            event.instances[1].feed("*1*1*11##")
            await asyncio.sleep(0.05)
    assert connection_calls(dispatch) == [True, False, True, False]
    assert all(call.args[1] in (SIGNAL, STATS_SIGNAL) for call in dispatch.call_args_list)
    assert all(call.args[0] is handler.hass for call in dispatch.call_args_list)
    assert handler.is_connected is False


async def test_idle_watchdog_probes_then_reconnects(caplog: pytest.LogCaptureFixture) -> None:
    """gw-03: silence -> probe on the command session -> probe undeliverable -> reconnect."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    register(handler, LIGHT, "1-11")

    def configure(channel: FakeCommandChannel, index: int) -> None:
        channel.open_error = OSError("gateway down")  # the probe never reaches the gateway

    with fake_channels(command=Factory(FakeCommandChannel, configure)) as (event, command, _):
        async with running(handler):
            await wait_until(lambda: len(command.instances) >= 1, timeout=3)
            await wait_until(lambda: len(event.instances) == 2, timeout=3)
            # A live monitor keeps the second session: frames faster than idle_timeout.
            for _ in range(6):
                event.instances[1].feed("*1*1*11##")
                await asyncio.sleep(0.05)
            assert len(event.instances) == 2
    assert any("no answer on either session" in record.message for record in caplog.records)


async def test_answered_probe_keeps_the_session() -> None:
    """gw-03: a probe that IS answered inside ``probe_window`` must not reconnect.

    ``test_idle_watchdog_probes_then_reconnects`` only covers the unanswered case;
    on a quiet bus the answered case is the normal one.

    This used to claim it caught the mutation
    ``if now - self._probe_sent_at >= self.probe_window:`` -> ``if True:``. It does
    not any more: the fake command channel ACKs the probe, so the R7 short-circuit
    absorbs the mutation before the reconnect. What is pinned here is the *whole*
    quiet-bus sequence (probe sent once, no second monitor session, the answer
    clears the watchdog) through the real loops; the window boundary itself is
    pinned by ``test_probe_window_is_a_boundary`` and the short-circuit by
    ``test_only_a_command_ack_newer_than_the_probe_keeps_the_session``, both of
    which keep the command session mute and drive ``_check_idle`` by hand.

    The handler's clock is replaced, so the whole scenario is decided by the
    values below and not by how fast the machine is.
    """
    handler = make_handler()
    clock = FakeClock()
    handler._now = clock  # noqa: SLF001 - shadows the static clock on this instance
    handler.idle_timeout = 100.0
    handler.probe_window = 50.0
    handler.read_poll_interval = 0.01
    register(handler, LIGHT, "1-11")

    with fake_channels() as (event, command, _):
        async with running(handler):
            await wait_until(lambda: handler.is_connected)
            # Silence long enough for the watchdog to probe the bus.
            await clock.advance_to(150.0)
            await wait_until(lambda: command.instances and command.instances[0].sent)
            assert command.instances[0].sent == ["*#1*11##"]

            # Still inside the window: the gateway is allowed to be slow.
            await clock.advance_to(180.0)
            assert len(event.instances) == 1

            # The answer arrives: the session is healthy again.
            event.instances[0].feed("*1*1*11##")
            await wait_until(lambda: handler.recent_frames)
            await clock.advance_to(200.0)

    assert len(event.instances) == 1


async def test_a_bug_in_the_listening_loop_does_not_kill_the_task() -> None:
    """gw-16: the loop's catch-all is the "never give up" guarantee.

    ``test_dispatch_errors_never_tear_down_the_session`` covers errors raised
    *inside* the dispatcher, which are caught one level deeper. This raises in the
    loop body itself (``_record_frame``), which only the bare ``except Exception``
    of ``listening_loop`` can absorb. Mutation caught: narrowing that catch-all to
    a specific exception type, after which one unexpected bug silently ends the
    task and the gateway never comes back until Home Assistant is restarted.
    """
    handler = make_handler()
    good = register(handler, LIGHT, "1-11")
    real_record = handler._record_frame  # noqa: SLF001
    calls: list[str] = []

    def record_once_then_work(direction: str, message: Any) -> None:
        calls.append(str(message))
        if len(calls) == 1:
            raise RuntimeError("bug in the listening loop")
        real_record(direction, message)

    handler._record_frame = record_once_then_work  # noqa: SLF001

    with fake_channels() as (event, _, _):
        async with running(handler, sending=False):
            await wait_until(lambda: handler.is_connected)
            event.instances[0].feed("*1*1*11##")
            # The session is rebuilt instead of the task dying.
            await wait_until(lambda: len(event.instances) == 2)
            assert handler.listening_worker is not None and not handler.listening_worker.done()
            event.instances[1].feed("*1*1*11##")
            await wait_until(lambda: good.events == ["*1*1*11##"])

    assert handler.listening_worker is None  # only close_listener() ends it


async def test_probe_falls_back_to_an_energy_meter_then_a_climate_zone() -> None:
    """gw-03: the idle probe must work for a gateway with no lamp or shutter.

    ``_probe_command``'s two fallbacks are unreachable from the test fixture,
    which always has a point-to-point light, so a WHO 18-only or climate-only
    installation would have silently probed with the general lighting status - a
    frame such a gateway may not answer, which would make the watchdog reconnect
    for ever. Mutation caught: deleting either fallback arm.
    """
    energy_only = make_handler()
    register(energy_only, SENSOR, "18-51", **{"class": "power", "who": "18"})
    assert str(energy_only._probe_command()) == "*#18*51*51##"  # noqa: SLF001

    climate_only = make_handler()
    register(climate_only, CLIMATE, "4-2", zone="2")
    assert str(climate_only._probe_command()) == "*#4*2*0##"  # noqa: SLF001

    # Nothing configured at all: the general lighting status is the last resort.
    assert str(make_handler()._probe_command()) == "*#1*0##"  # noqa: SLF001


async def test_event_auth_failure_stops_loop_and_starts_reauth() -> None:
    """gw-05: password rejected on the monitor -> auth_failed, reauth, no reconnect storm."""
    handler = make_handler()

    def configure(channel: FakeEventChannel, index: int) -> None:
        channel.open_error = AuthenticationError("password_error")

    with fake_channels(event=Factory(FakeEventChannel, configure)) as (event, _, dispatch):
        async with running(handler, sending=False):
            await wait_until(lambda: handler.listening_worker is not None and handler.listening_worker.done())
            assert await handler.send(OWNLightingCommand.switch_on("11")) is False
    assert handler.auth_failed is True
    assert len(event.instances) == 1
    handler.config_entry.async_start_reauth.assert_called_once_with(handler.hass)
    assert not any(connection_calls(dispatch))
    assert stats_calls(dispatch)[-1].session_state == SESSION_STATE_AUTH_FAILED


async def test_dispatch_errors_never_tear_down_the_session(caplog: pytest.LogCaptureFixture) -> None:
    """gw-08 / plat-02 / plat-03: entity bugs and odd frames are isolated."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    broken = register(handler, LIGHT, "1-11", fail=True)
    good = register(handler, LIGHT, "1-12")
    with fake_channels() as (event, _, _):
        async with running(handler, sending=False):
            await wait_until(lambda: handler.is_connected)
            channel = event.instances[0]
            channel.feed("*1*1*11##")  # entity raises
            channel.feed("*1*7*99##")  # preset level for an unconfigured WHERE (plat-02)
            channel.feed("*#1*12*2*0*1*0##")  # dimension reply without state (plat-03)
            channel.feed("*25*21*21##")  # malformed CEN+ (OWNd parser raises)
            channel.feed("*1*1*12##")
            await wait_until(lambda: good.events)
    assert good.events == ["*#1*12*2*0*1*0##", "*1*1*12##"]
    assert broken.events == []
    assert len(event.instances) == 1
    assert sum("failed to handle" in record.message for record in caplog.records) == 1
    assert not any("reconnecting" in record.message for record in caplog.records)


async def test_button_platform_skipped_and_general_status_requested() -> None:
    """plat-09 / gw-18: buttons live in their own dict; general events re-request without sleeping."""
    handler = make_handler()
    light = register(handler, LIGHT, "1-11")
    button = register(handler, BUTTON, "1-11", source_platform=LIGHT)
    await handler._dispatch_message(frame("*1*1*11##"), from_monitor=True)  # noqa: SLF001
    assert light.events == ["*1*1*11##"]
    assert button.events == []
    await handler._dispatch_message(frame("*1*0*0##"), from_monitor=True)  # noqa: SLF001
    assert fired(handler.hass, "myhome_general_light_event") == [{"message": "*1*0*0##", "event": "off"}]
    await handler._dispatch_message(frame("*1*1*3##"), from_monitor=True)  # noqa: SLF001
    assert fired(handler.hass, "myhome_area_light_event") == [{"message": "*1*1*3##", "area": 3, "event": "on"}]
    assert queued(handler) == ["*#1*0##", "*#1*3##"]


async def test_general_area_group_automation_frames_never_reach_a_cover() -> None:
    """gw-18 (WHO 2): a general / area / group shutter frame is a bus event only.

    The lighting equivalents are covered above; the automation ones and the
    lighting *group* arm were not. Delivering such a frame to the entities would
    restart the timed position estimate of every cover in the house, and dropping
    the handler would silently stop the three ``myhome_*_automation_event`` events
    the docs and the shipped blueprints advertise. Mutation caught:
    ``_handle_automation_scope`` returning False, and the ``is_group`` arm of
    ``_handle_lighting_scope``.
    """
    handler = make_handler()
    cover = register(handler, COVER, "2-81")
    light = register(handler, LIGHT, "1-11")
    for raw in ("*2*1*0##", "*2*2*3##", "*2*0*#3##", "*1*1*#3##"):
        await handler._dispatch_message(frame(raw), from_monitor=True)  # noqa: SLF001

    assert fired(handler.hass, "myhome_general_automation_event") == [
        {"message": "*2*1*0##", "event": "open"}
    ]
    assert fired(handler.hass, "myhome_area_automation_event") == [
        {"message": "*2*2*3##", "area": 3, "event": "close"}
    ]
    assert fired(handler.hass, "myhome_group_automation_event") == [
        {"message": "*2*0*#3##", "group": 3, "event": "stop"}
    ]
    assert fired(handler.hass, "myhome_group_light_event") == [
        {"message": "*1*1*#3##", "group": 3, "event": "on"}
    ]
    assert cover.events == []
    assert light.events == []
    # A group frame matches no WHERE, so it must not re-request anything either.
    assert queued(handler) == []


async def test_preset_level_refreshes_configured_light() -> None:
    handler = make_handler()
    light = register(handler, LIGHT, "1-11")
    await handler._dispatch_message(frame("*1*7*11##"), from_monitor=True)  # noqa: SLF001
    assert light.updates == 1
    assert light.events == []


async def test_light_translation_frames_become_pushbutton_events() -> None:
    """A physical pushbutton's own frames (WHO 1 command translation) are republished
    as ``myhome_light_pushbutton_event`` and never reach the entity: the actuator's
    status frame that follows is what drives the light. Dimmer-mode holds (30/31)
    have no other trace on a relay."""
    handler = make_handler()
    light = register(handler, LIGHT, "1-42")
    for raw in (
        "*1*1000#1*42##",
        "*1*1000#30*42##",
        "*1*1000#31*42##",
        "*1*1000#0*42##",
        "*1*1000#7*42##",
        "*1*1000#11*42##",
    ):
        await handler._dispatch_message(frame(raw), from_monitor=True)  # noqa: SLF001
    events = fired(handler.hass, "myhome_light_pushbutton_event")
    assert [event["event"] for event in events] == ["on", "dim_up", "dim_down", "off", "dim_to_70", "what_11"]
    assert events[1] == {"mac": MAC, "where": "42", "what": 30, "event": "dim_up", "message": "*1*1000#30*42##"}
    assert light.events == []
    # A local-bus WHERE is passed through verbatim; a translation without a WHAT is dropped.
    await handler._dispatch_message(frame("*1*1000#30*11#4#3##"), from_monitor=True)  # noqa: SLF001
    assert fired(handler.hass, "myhome_light_pushbutton_event")[-1]["where"] == "11#4#3"
    await handler._dispatch_message(frame("*1*1000*11##"), from_monitor=True)  # noqa: SLF001
    assert len(fired(handler.hass, "myhome_light_pushbutton_event")) == 7
    # Translations of other WHOs are still dropped silently.
    await handler._dispatch_message(frame("*2*1000#1*85##"), from_monitor=True)  # noqa: SLF001
    assert len(fired(handler.hass, "myhome_light_pushbutton_event")) == 7


async def test_generate_events_never_fires_none(caplog: pytest.LogCaptureFixture) -> None:
    """gw-17: only real frames feed myhome_message_event; command replies do not."""
    handler = make_handler(generate_events=True)
    with fake_channels() as (event, _, _):
        async with running(handler, sending=False):
            await wait_until(lambda: handler.is_connected)
            event.instances[0].feed("*1*1*11##")
            event.instances[0].feed("*25*21*21##")  # unparsable -> raw text
            await wait_until(lambda: len(fired(handler.hass, "myhome_message_event")) == 2)
    await handler._dispatch_message(frame("*1*1*12##"), from_monitor=False)  # noqa: SLF001
    events = fired(handler.hass, "myhome_message_event")
    assert events[0]["message"] == "*1*1*11##"
    assert events[1] == {"gateway": handler.gateway.host, "message": "*25*21*21##"}
    assert len(events) == 2


async def test_heating_command_on_monitor_requests_zone_status() -> None:
    handler = make_handler()
    await handler._dispatch_message(frame("*#4*#1*#14*0215*3##"), from_monitor=True)  # noqa: SLF001
    assert queued(handler) == ["*#4*1##"]


# ------------------------------------------------------- bus interface (0.3.1 / 5.1-5.2)
def test_entity_key_candidates_cover_both_interface_spellings() -> None:
    """Config keys pad the F422 interface (unique_id stability), the bus does not."""
    assert _entity_key_candidates("1-11") == ("1-11",)
    assert _entity_key_candidates("4-#0") == ("4-#0",)
    assert _entity_key_candidates("1-11#4#3") == ("1-11#4#3", "1-11#4#03")
    assert _entity_key_candidates("1-11#4#03") == ("1-11#4#03", "1-11#4#3")
    assert _entity_key_candidates("1-0115#4#15") == ("1-0115#4#15",)


async def test_bus_interface_frames_reach_the_bus_entity_only() -> None:
    """5.1/5.2: on OWNd 0.7.48 `message.interface` was always None, so `*1*1*11#4#3##`
    drove the main-bus entity `1-11`.  With 0.7.49 it must reach the entity configured
    behind the interface - written padded or unpadded - and never `1-11`."""
    handler = make_handler()
    main = register(handler, LIGHT, "1-11")
    behind_bus = register(handler, LIGHT, "1-11#4#03")
    with fake_channels() as (event, _, _):
        async with running(handler, sending=False):
            await wait_until(lambda: handler.is_connected)
            channel = event.instances[0]
            channel.feed("*1*1*11#4#3##")  # unpadded, as the F422 writes it
            channel.feed("*1*0*11#4#03##")  # padded, as our device keys spell it
            channel.feed("*1*1*11##")  # main bus, same WHERE
            await wait_until(lambda: main.events)
    assert behind_bus.events == ["*1*1*11#4#3##", "*1*0*11#4#03##"]
    assert main.events == ["*1*1*11##"]


async def test_unpadded_config_key_also_resolves_padded_frames() -> None:
    """The tolerance works in both directions (a hand-written `1-11#4#3` device key)."""
    handler = make_handler()
    behind_bus = register(handler, LIGHT, "1-11#4#3")
    await handler._dispatch_message(frame("*1*1*11#4#03##"), from_monitor=True)  # noqa: SLF001
    await handler._dispatch_message(frame("*1*0*11#4#3##"), from_monitor=True)  # noqa: SLF001
    assert behind_bus.events == ["*1*1*11#4#03##", "*1*0*11#4#3##"]


# --------------------------------------------------- central heating unit (0.3.1 / 5.4)
def test_message_entity_key_routes_zone_0_to_the_central_unit() -> None:
    assert _message_entity_key(frame("*#4*0#1*20*1##")) == "4-#0"
    assert _message_entity_key(frame("*#4*1*0*0215##")) == "4-1"
    assert _message_entity_key(frame("*1*1*11##")) == "1-11"


async def test_central_unit_actuator_never_drives_zone_1() -> None:
    """5.4: OWNd rewrites `zone 0` to the first WHERE parameter, so `*#4*0#1*20*1##`
    (the central unit's actuator 1) reports entity `4-1` and de-synced zone 1
    (Jacopo Jannone, via michnovka)."""
    handler = make_handler()
    zone1 = register(handler, CLIMATE, "4-1")
    central = register(handler, CLIMATE, "4-#0")
    await handler._dispatch_message(frame("*#4*0#1*20*1##"), from_monitor=True)  # noqa: SLF001
    assert central.events == ["*#4*0#1*20*1##"]
    assert zone1.events == []
    # A real zone frame is untouched.
    await handler._dispatch_message(frame("*#4*1*0*0215##"), from_monitor=True)  # noqa: SLF001
    assert zone1.events == ["*#4*1*0*0215##"]
    assert len(central.events) == 1


# --------------------------------------------------------------------------- CEN+
async def test_cenplus_event_mapping() -> None:
    """gw-14: held once, repeats distinct, rotations named, never event=None."""
    handler = make_handler()
    for raw in ("*25*21#1*21##", "*25*22#1*21##", "*25*23#1*21##", "*25*23#1*21##", "*25*24#1*21##", "*25*25#2*22##"):
        await handler._dispatch_message(frame(raw), from_monitor=True)  # noqa: SLF001
    events = fired(handler.hass, "myhome_cenplus_event")
    assert [event["event"] for event in events] == [
        CONF_SHORT_PRESS,
        CONF_LONG_PRESS,
        EVENT_LONG_PRESS_REPEAT,
        EVENT_LONG_PRESS_REPEAT,
        CONF_LONG_RELEASE,
        EVENT_ROTATE_CW_SLOW,
    ]
    # 0.4.0: the payload gained "mac" (additive, so multi-gateway automations and the
    # device triggers can tell two gateways apart); the other three keys are unchanged.
    assert events[0] == {"object": 1, "pushbutton": 1, "event": CONF_SHORT_PRESS, "mac": MAC}
    assert events[-1] == {"object": 2, "pushbutton": 2, "event": EVENT_ROTATE_CW_SLOW, "mac": MAC}
    assert all(event["event"] is not None for event in events)


async def test_cen_and_cenplus_press_names_are_complete_and_distinct() -> None:
    """gw-14: every documented press maps to its own name.

    These names are the automation contract: they are the ``type``/``subtype``
    values of the device triggers, of the shipped blueprints and of
    docs/services-and-events.md, so two presses sharing a name - or a swapped
    pair - silently breaks every automation bound to them.
    ``test_cenplus_event_mapping`` only ever sends WHAT 25 of the four rotations,
    and no test sends a CEN frame with a ``#state`` suffix at all.

    Mutations caught: swapping any two of the four rotation names, and swapping
    ``short_release`` with ``long_press`` on the CEN side. The CEN branch *order*
    matters too: ``is_released_after_short_press`` raises ``TypeError`` when the
    frame carries no state (OWNd 0.7.49), so ``is_pressed`` has to be tested
    first - the bare ``*15*21*51##`` below is what pins that.
    """
    handler = make_handler()
    for raw in (
        "*25*21#1*21##",  # short press
        "*25*22#1*21##",  # held
        "*25*23#1*21##",  # still held
        "*25*24#1*21##",  # released
        "*25*25#1*21##",  # rotate clockwise, slow
        "*25*26#1*21##",  # rotate clockwise, fast
        "*25*27#1*21##",  # rotate counter-clockwise, slow
        "*25*28#1*21##",  # rotate counter-clockwise, fast
    ):
        await handler._dispatch_message(frame(raw), from_monitor=True)  # noqa: SLF001
    cenplus = [event["event"] for event in fired(handler.hass, EVENT_CENPLUS)]
    assert cenplus == [
        CONF_SHORT_PRESS,
        CONF_LONG_PRESS,
        EVENT_LONG_PRESS_REPEAT,
        CONF_LONG_RELEASE,
        EVENT_ROTATE_CW_SLOW,
        EVENT_ROTATE_CW_FAST,
        EVENT_ROTATE_CCW_SLOW,
        EVENT_ROTATE_CCW_FAST,
    ]
    assert len(set(cenplus)) == len(cenplus)

    # CEN frames carry the state in the WHAT suffix; the stateless frame first.
    for raw in ("*15*21*51##", "*15*21#1*51##", "*15*21#3*51##", "*15*21#2*51##"):
        await handler._dispatch_message(frame(raw), from_monitor=True)  # noqa: SLF001
    cen = [event["event"] for event in fired(handler.hass, EVENT_CEN)]
    assert cen == [CONF_SHORT_PRESS, CONF_SHORT_RELEASE, CONF_LONG_PRESS, CONF_LONG_RELEASE]
    assert len(set(cen)) == len(cen)


# --------------------------------------------------------------------------- energy throttle
async def test_throttle_applies_only_to_active_power() -> None:
    """gw-06 / sc-02 / sc-03: OR semantics on instant power; totals always pass.

    The interval arm is decided on ``FakeClock`` rather than on a real
    ``asyncio.sleep(0.25)`` against a 0.2 s interval: 50 ms of margin is what a
    loaded CI runner eats for breakfast, and the last frame would then arrive
    before the interval elapsed and be suppressed.
    """
    handler = make_handler(sensor_defaults={"min_delta_w": 5, "min_interval_sec": 0.2})
    clock = FakeClock()
    handler._now = clock  # noqa: SLF001 - the interval arm must be decided by hand
    meter = register(handler, SENSOR, "18-51", **{"class": "power", "min_delta_w": 5, "min_interval_sec": 0.2})

    async def dispatch(raw: str) -> None:
        await handler._dispatch_message(frame(raw), from_monitor=True)  # noqa: SLF001

    await dispatch("*#18*51*113*613##")  # first sample
    await dispatch("*#18*51*113*615##")  # +2 W, too soon -> suppressed
    await dispatch("*#18*51*51*1234567##")  # totaliser: always
    await dispatch("*#18*51*54*4321##")  # daily: always
    await dispatch("*#18*51*53*98765##")  # monthly: always
    await dispatch("*#18*51*113*616##")  # +3 W, still too soon -> suppressed
    await dispatch("*#18*51*113*630##")  # +17 W -> delta accepts
    clock.value = 1.0  # the 0.2 s interval has elapsed, and only that
    await dispatch("*#18*51*113*632##")  # +2 W but interval elapsed -> accepted (OR)
    assert meter.events == [
        "*#18*51*113*613##",
        "*#18*51*51*1234567##",
        "*#18*51*54*4321##",
        "*#18*51*53*98765##",
        "*#18*51*113*630##",
        "*#18*51*113*632##",
    ]


async def test_energy_delta_exactly_at_the_threshold_is_accepted() -> None:
    """Contract B says ``|dW| >= min_delta_w``, so the threshold itself must pass.

    ``test_throttle_applies_only_to_active_power`` only uses deltas of 2, 3 and
    17 W, so it never touches the boundary. Mutation caught: ``or abs(watts -
    last_w) >= settings.min_delta_w`` -> ``> settings.min_delta_w``, which for a
    meter whose load steps in exact ``min_delta_w`` increments suppresses every
    single update - the sensor freezes at its first reading.

    The clock is frozen so the interval arm can never be the reason a sample passes.
    """
    handler = make_handler(sensor_defaults={"min_delta_w": 5, "min_interval_sec": 1000})
    handler._now = FakeClock()  # noqa: SLF001 - the interval arm must never decide
    register(handler, SENSOR, "18-51", **{"class": "power", "min_delta_w": 5, "min_interval_sec": 1000})

    assert handler._should_process_active_power("18-51", 100) is True  # noqa: SLF001 - first sample
    assert handler._should_process_active_power("18-51", 104) is False  # noqa: SLF001 - 4 W
    assert handler._should_process_active_power("18-51", 105) is True  # noqa: SLF001 - exactly 5 W


async def test_throttle_reads_per_sensor_and_gateway_defaults() -> None:
    handler = make_handler(sensor_defaults={"min_delta_w": 5, "min_interval_sec": 5, "suppress_log_interval_sec": 60})
    register(handler, SENSOR, "18-51", **{"class": "power"})
    register(handler, SENSOR, "18-52", **{"class": "power", "min_delta_w": 1, "suppress_log_interval_sec": 10})
    default = handler._energy_settings_for("18-51")  # noqa: SLF001
    override = handler._energy_settings_for("18-52")  # noqa: SLF001
    assert (default.min_delta_w, default.min_interval_sec, default.suppress_log_interval_sec) == (5, 5.0, 60.0)
    assert (override.min_delta_w, override.min_interval_sec, override.suppress_log_interval_sec) == (1, 5.0, 10.0)
    # Thresholds at zero accept everything.
    register(handler, SENSOR, "18-53", **{"class": "power", "min_delta_w": 0, "min_interval_sec": 0})
    assert all(handler._should_process_active_power("18-53", w) for w in (100, 100, 100))  # noqa: SLF001


# --------------------------------------------------------------------------- stats / options / dedupe (0.3.0)
async def test_stats_snapshot_follows_frames_commands_and_reconnects() -> None:
    """The published snapshot mirrors what the sessions actually did."""
    handler = make_handler()
    register(handler, LIGHT, "1-11")
    assert handler.stats == GatewayStats()  # nothing happened yet
    with fake_channels() as (event, _, dispatch):
        async with running(handler):
            await wait_until(lambda: handler.is_connected)
            assert handler.stats.connected is True
            assert handler.stats.session_state == SESSION_STATE_CONNECTED
            assert stats_calls(dispatch)[-1].session_state == SESSION_STATE_CONNECTED

            event.instances[0].feed("*1*1*11##")
            await wait_until(lambda: handler.stats.frames_rx == 1)
            assert handler.stats.last_frame_at is not None
            assert handler.stats.last_frame_at.tzinfo is not None  # UTC aware

            assert await handler.send(OWNLightingCommand.switch_on("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            await wait_until(lambda: handler.stats.commands_sent == 1)

            event.instances[0].feed(ConnectionResetError("rst"))
            await wait_until(lambda: handler.stats.reconnects == 1, timeout=3)
    assert handler.stats.connected is False
    assert handler.stats.session_state == SESSION_STATE_DISCONNECTED
    assert handler.stats.queue_length == 0
    assert stats_calls(dispatch)[-1] == handler.stats  # the last publish is the final snapshot


async def test_stats_counts_dropped_commands() -> None:
    handler = make_handler()
    handler.send_buffer = asyncio.Queue(maxsize=1)
    with fake_channels() as (_, _, dispatch):
        assert await handler.send(OWNLightingCommand.switch_on("11")) is True
        assert await handler.send(OWNLightingCommand.switch_on("12")) is False  # queue full
        assert handler.stats.commands_dropped == 1
        assert handler.stats.queue_length == 1
        await handler.close_listener()  # the queued command is discarded too
        assert await handler.send(OWNLightingCommand.switch_on("13")) is False  # closed
    assert handler.stats.commands_dropped == 3
    assert handler.stats.queue_length == 0
    assert stats_calls(dispatch)[-1].commands_dropped == 3


async def test_stats_signal_is_throttled_but_never_stale() -> None:
    """At most one publish per interval; the newest snapshot is flushed after it."""
    handler = make_handler()
    handler.stats_publish_interval = 0.2
    with fake_channels() as (event, _, dispatch):
        async with running(handler, sending=False):
            await wait_until(lambda: handler.is_connected)
            before = len(stats_calls(dispatch))
            for _ in range(10):
                event.instances[0].feed("*1*1*11##")
            await wait_until(lambda: handler.stats.frames_rx == 10)
            assert len(stats_calls(dispatch)) - before <= 1  # ten frames, one window
            # ... and the suppressed publish is not lost: it lands within the interval.
            await wait_until(lambda: stats_calls(dispatch)[-1].frames_rx == 10, timeout=2)
    assert handler._stats_timer is None  # noqa: SLF001 - no timer left behind


async def test_options_configure_the_timing_knobs(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    defaults = make_handler(fast=False)
    assert (defaults.idle_timeout, defaults.probe_window, defaults.command_timeout, defaults.command_ttl) == (
        300.0,
        30.0,
        10.0,
        60.0,
    )
    tuned = make_handler(
        fast=False,
        options={
            CONF_IDLE_WATCHDOG_SEC: 120,
            CONF_PROBE_WINDOW_SEC: 15,
            CONF_COMMAND_TIMEOUT_SEC: 25,
            CONF_QUEUE_TTL_SEC: 90,
        },
    )
    assert (tuned.idle_timeout, tuned.probe_window, tuned.command_timeout, tuned.command_ttl) == (
        120.0,
        15.0,
        25.0,
        90.0,
    )
    assert tuned.session_parameters[CONF_IDLE_WATCHDOG_SEC] == 120.0
    assert tuned.session_parameters[CONF_QUEUE_TTL_SEC] == 90.0
    assert not caplog.records

    # Defensive: an out-of-range value is clamped, a non-numeric one falls back.
    guarded = make_handler(fast=False, options={CONF_IDLE_WATCHDOG_SEC: 1, CONF_COMMAND_TIMEOUT_SEC: "soon"})
    assert guarded.idle_timeout == 30.0  # the watchdog can never be switched off
    assert guarded.command_timeout == 10.0
    assert any("out of range" in record.message for record in caplog.records)
    assert any("is not a number" in record.message for record in caplog.records)


async def test_identical_pending_status_requests_are_coalesced(caplog: pytest.LogCaptureFixture) -> None:
    """G1-E: the same status frame is never queued twice while one is pending."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    assert await handler.send_status_request(OWNLightingCommand.status("0")) is True
    assert await handler.send_status_request(OWNLightingCommand.status("0")) is True  # coalesced
    assert await handler.send_status_request(OWNLightingCommand.status("11")) is True  # other WHERE
    assert await handler.send(OWNLightingCommand.switch_on("11")) is True
    assert await handler.send(OWNLightingCommand.switch_on("11")) is True  # commands are never coalesced
    assert queued(handler) == ["*#1*0##", "*#1*11##", "*1*1*11##", "*1*1*11##"]
    assert any("Coalescing status request" in record.message for record in caplog.records)

    # Once delivered, the same status request can be queued again.
    with fake_channels() as (_, command, _):
        async with running(handler, listening=False):
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            assert await handler.send_status_request(OWNLightingCommand.status("0")) is True
            await asyncio.wait_for(handler.send_buffer.join(), 2)
    assert command.instances[0].sent.count("*#1*0##") == 2


async def test_recent_frames_ring_buffer() -> None:
    """The last 50 frames (both directions) are kept for the diagnostics download."""
    handler = make_handler()
    register(handler, LIGHT, "1-11")

    def configure(channel: FakeCommandChannel, index: int) -> None:
        channel.responder = lambda message: CommandResult(True, [frame("*1*1*11##")])

    with fake_channels(command=Factory(FakeCommandChannel, configure)) as (event, _, _):
        async with running(handler):
            await wait_until(lambda: handler.is_connected)
            event.instances[0].feed("*1*1*12##")
            await wait_until(lambda: handler.recent_frames)
            assert await handler.send(OWNLightingCommand.switch_on("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            await wait_until(lambda: len(handler.recent_frames) >= 3)
    assert [record.direction for record in handler.recent_frames][:3] == [FRAME_MONITOR, FRAME_COMMAND, FRAME_REPLY]
    assert [record.frame for record in handler.recent_frames][:3] == ["*1*1*12##", "*1*1*11##", "*1*1*11##"]
    assert all(record.at.tzinfo is not None for record in handler.recent_frames)
    # Bounded: only the newest 50 survive.
    for index in range(60):
        handler._record_frame(FRAME_MONITOR, f"*1*1*{index}##")  # noqa: SLF001
    assert len(handler.recent_frames) == 50
    assert handler.recent_frames[0].frame == "*1*1*10##"


# --------------------------------------------------------------------------- shutdown
async def test_close_listener_is_idempotent_and_drains(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    with fake_channels() as (event, _, dispatch):
        handler.listening_worker = asyncio.create_task(handler.listening_loop())
        await wait_until(lambda: handler.is_connected)
        assert await handler.send(OWNLightingCommand.switch_on("11"))
        assert await handler.send(OWNLightingCommand.switch_off("11"))
        listening_task = handler.listening_worker
        assert await handler.close_listener() is True
        assert await handler.close_listener() is True
    assert listening_task.done()
    assert handler.listening_worker is None and handler.sending_workers == []
    assert event.instances[0].closed
    assert handler.send_buffer.qsize() == 0
    assert handler.is_connected is False
    assert connection_calls(dispatch) == [True, False]
    assert sum("Closing gateway sessions" in record.message for record in caplog.records) == 1
    assert any("2 queued command(s) discarded" in record.message for record in caplog.records)


async def test_loops_do_not_start_after_close() -> None:
    handler = make_handler()
    with fake_channels() as (event, command, _):
        await handler.close_listener()
        await handler.listening_loop()
        await handler.sending_loop(0)
    assert event.instances == [] and command.instances == []


# --------------------------------------------------------------------------- own_session on loopback
# `asyncio.open_connection` reads with a 64 KiB limit; a frame longer than that
# with no `##` in it is what makes `readuntil` raise `LimitOverrunError`.
OVER_LONG_FRAME_BYTES = 70_000


class FakeOWNServer:
    """Minimal OpenWebNet gateway: greeting ACK, session ACK (or nonce), scripted replies."""

    def __init__(
        self,
        replies: dict[str, list[str]] | None = None,
        *,
        nonce: str | None = None,
        password_ok: bool = True,
        answer: bool = True,
        initial_frames: list[str] | None = None,
        close_after_initial: bool = False,
        default_replies: list[str] | None = None,
        negotiation_ok: bool = True,
        close_during_negotiation: bool = False,
        flood_negotiation: bool = False,
        garbage_negotiation: bool = False,
        reset_after_initial: bool = False,
    ) -> None:
        self.replies = replies or {}
        self.nonce = nonce
        self.password_ok = password_ok
        self.answer = answer
        self.initial_frames = initial_frames or []
        self.close_after_initial = close_after_initial
        self.default_replies = ["*#*0##"] if default_replies is None else default_replies
        # Scripted negotiation / transport failures (F9).  OWNd's own session classes
        # swallow all of these and return None, which is exactly what own_session.py
        # exists to fix, so every one of them needs a server that can produce it.
        self.negotiation_ok = negotiation_ok
        self.close_during_negotiation = close_during_negotiation
        self.flood_negotiation = flood_negotiation
        self.garbage_negotiation = garbage_negotiation
        self.reset_after_initial = reset_after_initial
        self.received: list[str] = []
        self.sessions: list[str] = []
        self.monitor_writers: list[asyncio.StreamWriter] = []
        # Every accepted connection, so `__aexit__` can hang up on the ones a
        # failing test left behind (see the note there).
        self.clients: list[asyncio.StreamWriter] = []
        self.server: asyncio.AbstractServer | None = None
        self.port = 0

    async def push(self, frame: str) -> None:
        """Send ``frame`` on every open monitor (event) session."""
        for writer in list(self.monitor_writers):
            writer.write(frame.encode())
            await writer.drain()

    async def drop_monitors(self) -> None:
        """Close every monitor session from the gateway side (simulates a dead link)."""
        writers, self.monitor_writers = self.monitor_writers, []
        for writer in writers:
            writer.close()

    async def __aenter__(self) -> FakeOWNServer:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc: object) -> None:
        assert self.server is not None
        # `wait_closed()` also waits for the connection handlers, and a handler
        # parked on `readuntil` never returns on its own. A test that fails (or
        # raises) before closing its channel would otherwise hang here for ever
        # instead of reporting its assertion, which is exactly what happens while
        # mutation-testing the error paths below. Hang up first, then wait.
        for writer in self.clients:
            with suppress(Exception):  # already gone is the normal case
                writer.transport.abort()
        self.clients.clear()
        self.server.close()
        await self.server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.clients.append(writer)
        try:
            writer.write(b"*#*1##")
            session = (await reader.readuntil(b"##")).decode()
            self.sessions.append(session)
            if self.close_during_negotiation:
                # EOF between the greeting and the negotiation reply.
                return
            if self.garbage_negotiation:
                # A well-formed frame made of bytes that are not UTF-8: OWNd decodes
                # the negotiation reply without guarding, so this raises *inside* it.
                writer.write(b"\xff\xfe*#*1##")
                await writer.drain()
                await reader.readuntil(b"##")
                return
            if self.flood_negotiation:
                # A negotiation reply that never terminates: `readuntil` gives up
                # once the stream limit is exceeded.
                writer.write(b"*" * OVER_LONG_FRAME_BYTES)
                await writer.drain()
                await reader.readuntil(b"##")
                return
            if self.nonce is not None:
                writer.write(f"*#{self.nonce}##".encode())
                await writer.drain()
                self.received.append((await reader.readuntil(b"##")).decode())
                writer.write(b"*#*1##" if self.password_ok else b"*#*0##")
                await writer.drain()
                if not self.password_ok:
                    return
            else:
                writer.write(b"*#*1##" if self.negotiation_ok else b"*#*0##")
                if not self.negotiation_ok:
                    await writer.drain()
                    return
            for item in self.initial_frames:
                writer.write(item.encode())
            await writer.drain()
            if self.close_after_initial:
                return
            if self.reset_after_initial:
                # SO_LINGER 0 makes close() send an RST instead of a FIN, so the
                # client sees a connection *reset* rather than a clean EOF.
                sock = writer.get_extra_info("socket")
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                writer.transport.abort()
                return
            if session == "*99*1##":
                self.monitor_writers.append(writer)
            while True:
                command = (await reader.readuntil(b"##")).decode()
                self.received.append(command)
                if not self.answer:
                    continue
                for item in self.replies.get(command, self.default_replies):
                    writer.write(item.encode())
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            if writer in self.monitor_writers:
                self.monitor_writers.remove(writer)
            writer.close()


def make_gateway(port: int, password: str | None = "12345") -> Any:
    from OWNd.connection import OWNGateway

    return OWNGateway(
        {"address": "127.0.0.1", "port": port, "password": password, "serialNumber": MAC, "modelName": "Fake"}
    )


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_command_channel_reads_every_reply_until_ack() -> None:
    replies = {"*#1*0##": ["*1*1*11##", "*1*0*12##", "*#18*51*51*99##", "*#*1##"], "*1*1*99##": ["*#*0##"]}
    async with FakeOWNServer(replies) as server:
        channel = OWNCommandChannel(make_gateway(server.port), LOGGER)
        await channel.open(timeout=2)
        assert channel.is_open
        sock = channel._stream_writer.get_extra_info("socket")  # noqa: SLF001
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE) != 0
        result = await channel.send_command(OWNLightingCommand.status("0"), timeout=2)
        assert result.acknowledged is True
        assert [str(reply) for reply in result.replies] == ["*1*1*11##", "*1*0*12##", "*#18*51*51*99##"]
        # The next command sees ITS OWN answer, not leftovers of the previous one.
        result = await channel.send_command(OWNCommand.parse("*1*1*99##"), timeout=2)
        assert result.acknowledged is False and result.replies == []
        await channel.close()
        await channel.close()
        assert not channel.is_open
        with pytest.raises(SessionError):
            await channel.send_command(OWNLightingCommand.status("0"), timeout=1)
    assert server.sessions == ["*99*0##"]


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_command_channel_timeout_and_peer_close() -> None:
    async with FakeOWNServer(answer=False) as server:
        channel = OWNCommandChannel(make_gateway(server.port), LOGGER)
        await channel.open(timeout=2)
        with pytest.raises(TimeoutError):
            await channel.send_command(OWNLightingCommand.status("11"), timeout=0.1)
        assert not channel.is_open
        await channel.close()
    async with FakeOWNServer(initial_frames=["*1*1*11##"], close_after_initial=True) as server:
        channel = OWNEventChannel(make_gateway(server.port), LOGGER)
        await channel.open(timeout=2)
        assert str(await channel.get_next()) == "*1*1*11##"
        with pytest.raises(SessionError):
            await channel.get_next()
        await channel.close()
    assert server.sessions == ["*99*1##"]


@pytest.mark.slow  # ~2 s: three real loopback sessions, one of them a real connect timeout
@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_channel_open_failures() -> None:
    async with FakeOWNServer(nonce="603356072", password_ok=False) as server:
        channel = OWNCommandChannel(make_gateway(server.port), LOGGER)
        with pytest.raises(AuthenticationError) as excinfo:
            await channel.open(timeout=2)
        assert excinfo.value.reason == "password_error"
        assert not channel.is_open
        assert channel._stream_writer is None  # noqa: SLF001 - closed on failure
    async with FakeOWNServer(nonce="603356072", password_ok=True) as server:
        channel = OWNEventChannel(make_gateway(server.port), LOGGER)
        await channel.open(timeout=2)
        assert channel.is_open
        await channel.close()
    # Refused connection -> OSError, never a silent None.  The socket is bound and
    # never listened on, and stays open for the whole check: closing it first (as
    # this test used to) frees the port, and another process claiming it in the
    # meantime would turn the refusal into a successful connect.
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    closed_port = probe.getsockname()[1]
    try:
        channel = OWNCommandChannel(make_gateway(closed_port), LOGGER)
        with pytest.raises(OSError):
            await channel.open(timeout=2)
        await channel.close()
    finally:
        probe.close()


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_failed_negotiation_is_never_reported_as_an_open_session() -> None:
    """sess-01: a session that did not negotiate must raise, not come back "open".

    This is the worst failure mode in own_session.py: OWNd's own `connect()`
    returns `{"Success": False, ...}` instead of raising, so without the explicit
    `raise` the code falls straight through to `self._is_open = True` and hands
    the gateway handler a dead channel, which it then uses for every command
    until the first write fails.

    A negotiation refusal is NOT an authentication failure - it must stay a plain
    `SessionError`, because `AuthenticationError` is what starts a reauth flow and
    a reauth prompt is the wrong answer to a gateway that is simply busy.

    Mutation caught: deleting `raise SessionError(f"{self._type} session
    negotiation failed ({reason})")` in `OWNChannel.open`.
    """
    async with FakeOWNServer(negotiation_ok=False) as server:
        channel = OWNCommandChannel(make_gateway(server.port), LOGGER)
        with pytest.raises(SessionError) as excinfo:
            await channel.open(timeout=2)
        assert not isinstance(excinfo.value, AuthenticationError)
        assert "negotiation failed" in str(excinfo.value)
        assert "negotiation_refused" in str(excinfo.value)
        assert not channel.is_open
        assert channel._stream_writer is None  # noqa: SLF001 - the socket is closed on failure


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_negotiation_transport_failures_raise_session_errors() -> None:
    """sess-02: a gateway that dies mid-negotiation is a broken session, not a crash.

    Both of these reach `open()` as raw `asyncio` stream exceptions, which are
    neither `OSError` nor `TimeoutError`, so without their own `except` arms they
    would escape `open()` unconverted: the gateway handler's listening loop
    catches `_TRANSPORT_ERRORS` to pace its reconnects, and an exception outside
    that tuple takes the catch-all path instead (a full traceback in the log on
    every reconnect attempt of a rebooting gateway).

    Mutations caught: deleting either the `IncompleteReadError` or the
    `LimitOverrunError` arm of `OWNChannel.open`.
    """
    async with FakeOWNServer(close_during_negotiation=True) as server:
        channel = OWNEventChannel(make_gateway(server.port), LOGGER)
        with pytest.raises(SessionError) as excinfo:
            await channel.open(timeout=2)
        assert "during negotiation" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, asyncio.IncompleteReadError)
        assert not channel.is_open

    async with FakeOWNServer(flood_negotiation=True) as server:
        channel = OWNEventChannel(make_gateway(server.port), LOGGER)
        with pytest.raises(SessionError) as excinfo:
            await channel.open(timeout=2)
        assert "malformed negotiation frame" in str(excinfo.value)
        assert isinstance(excinfo.value.__cause__, asyncio.LimitOverrunError)
        assert not channel.is_open


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_read_frame_rejects_a_closed_session_and_an_over_long_frame() -> None:
    """sess-03: `read_frame` never returns garbage and never reads a dead socket.

    The "not open" guard is what stops the listening loop from reading a channel
    the gateway handler has already closed (it would raise `AttributeError` on a
    `None` reader instead of the `SessionError` the loop knows how to pace).
    The over-long arm additionally has to clear `_is_open`, or the handler would
    keep re-reading a stream whose buffer it can never drain.

    Mutations caught: deleting the `not self._is_open or reader is None` guard,
    and deleting `self._is_open = False` from the `LimitOverrunError` arm.
    """
    async with FakeOWNServer() as server:
        channel = OWNEventChannel(make_gateway(server.port), LOGGER)
        # Never opened: no socket has been created at all.
        with pytest.raises(SessionError, match="not open"):
            await channel.get_next()

        await channel.open(timeout=2)
        await channel.close()
        # Opened and then closed: the reader is gone, the guard is the only defence.
        with pytest.raises(SessionError, match="not open"):
            await channel.get_next()

    async with FakeOWNServer(initial_frames=["*" * OVER_LONG_FRAME_BYTES]) as server:
        channel = OWNEventChannel(make_gateway(server.port), LOGGER)
        await channel.open(timeout=2)
        with pytest.raises(SessionError, match="over-long frame"):
            await channel.get_next()
        assert not channel.is_open
        await channel.close()


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_connection_reset_mid_session_closes_the_channel() -> None:
    """sess-04: an RST is not a clean EOF, and must still mark the channel closed.

    Every other test in this file closes the fake server politely, so a reset -
    what a rebooting gateway, a NAT timeout or an unplugged cable actually
    produce - was never simulated. `OSError` is re-raised rather than wrapped
    (the caller wants the errno), which makes it the one error path that could
    silently skip `self._is_open = False` and leave the handler convinced the
    channel is usable for ever.

    Mutation caught: deleting `self._is_open = False` from the `except OSError`
    arm of `read_frame`.
    """
    async with FakeOWNServer(initial_frames=["*1*1*11##"], reset_after_initial=True) as server:
        channel = OWNEventChannel(make_gateway(server.port), LOGGER)
        await channel.open(timeout=2)
        assert str(await channel.get_next()) == "*1*1*11##"
        with pytest.raises(OSError) as excinfo:
            for _ in range(5):  # the RST may land after one more read on some stacks
                await channel.get_next()
        assert not isinstance(excinfo.value, SessionError)  # a real errno, not a wrapper
        assert not channel.is_open
        await channel.close()


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_command_session_survives_stray_signaling_and_unparsable_replies() -> None:
    """sess-05: only an ACK or a NACK ends a command; everything else is skipped.

    A gateway that interleaves an unsolicited signaling frame (here a stray nonce
    challenge) or a frame OWNd cannot parse must not desynchronise the session:
    if either were treated as the end of the command, the NEXT command would read
    this one's ACK and every reply after it would be attributed to the wrong
    frame - the exact desynchronisation `send_command` was written to prevent.

    Mutations caught: replacing the `continue` after "Ignoring signaling frame"
    with a `return CommandResult(False, replies)`, and dropping the final `else`
    so an unparsable frame is appended to `replies` (it is not an `OWNMessage`,
    so the caller would then dispatch a bare string).
    """
    replies = {
        # A stray nonce is an OWNSignaling that is neither ACK nor NACK; `*#*3##`
        # is not a frame OWNd can parse at all.  Both sit before the real reply.
        "*#1*0##": ["*#603356072##", "*#*3##", "*1*1*11##", "*#*1##"],
    }
    async with FakeOWNServer(replies) as server:
        channel = OWNCommandChannel(make_gateway(server.port), LOGGER)
        await channel.open(timeout=2)
        result = await channel.send_command(OWNLightingCommand.status("0"), timeout=2)
        assert result.acknowledged is True
        # Neither the signaling frame nor the unparsable one reaches the caller.
        assert [str(reply) for reply in result.replies] == ["*1*1*11##"]
        assert channel.is_open
        await channel.close()


def test_tcp_keepalive_is_best_effort() -> None:
    """sess-06: keepalive tuning must never break a working session.

    `enable_tcp_keepalive` runs on every `open()`. A transport with no socket
    (any non-TCP transport) and a socket that refuses the options (a platform
    without them, or a socket already torn down) both have to degrade to a
    plain `False`, because raising here would turn a perfectly good session into
    a reconnect loop.

    Mutations caught: dropping the `if sock is None: return False` guard, and
    narrowing or removing the `except OSError: return False`.
    """
    no_socket = MagicMock()
    no_socket.get_extra_info.return_value = None
    assert enable_tcp_keepalive(no_socket) is False

    refusing = MagicMock()
    refusing.get_extra_info.return_value.setsockopt.side_effect = OSError(22, "Invalid argument")
    assert enable_tcp_keepalive(refusing) is False

    accepting = MagicMock()
    assert enable_tcp_keepalive(accepting) is True


def test_fake_gateway_stats_stays_field_compatible() -> None:
    """``helpers_platforms.FakeGatewayStats`` is a hand-written copy of
    ``gateway.GatewayStats`` that the platform tests dispatch instead of the real
    snapshot. Nothing made the two stay in step: a field added to (or renamed in)
    the real dataclass would leave every platform test asserting a shape
    production no longer publishes.
    """
    assert {field.name for field in fields(FakeGatewayStats)} == {
        field.name for field in fields(GatewayStats)
    }


def test_parse_frame_never_raises() -> None:
    assert isinstance(frame("*1*1*11##"), OWNMessage)
    assert frame("*25*21*21##") == "*25*21*21##"  # OWNd raises IndexError
    assert frame("*#13**22*1##") == "*#13**22*1##"  # OWNd raises IndexError
    assert frame("garbage##") == "garbage##"


# --------------------------------------------------------------------------- review 2026-09-07
async def test_sending_worker_survives_an_unexpected_exception() -> None:
    """The command path must be as crash-proof as the event path."""
    handler = make_handler()

    class Boom(FakeCommandChannel):
        async def open(self, timeout: float) -> None:
            raise ValueError("gateway sent garbage during negotiation")

    with fake_channels(command=Factory(Boom)):
        async with running(handler, listening=False):
            assert await handler.send(OWNLightingCommand.switch_on("11")) is True
            await asyncio.wait_for(handler.send_buffer.join(), 2)
            await asyncio.sleep(0.05)
            assert not handler.sending_workers[0].done()
            assert handler.stats.commands_dropped >= 1


async def test_close_listener_closes_a_session_being_opened() -> None:
    """A channel whose open() is cancelled by close_listener must not leak."""
    handler = make_handler()
    opened: list[Any] = []

    class Slow(FakeCommandChannel):
        async def open(self, timeout: float) -> None:
            opened.append(self)
            await asyncio.sleep(5)

    with fake_channels(command=Factory(Slow)):
        async with running(handler, listening=False):
            assert await handler.send(OWNLightingCommand.switch_on("11")) is True
            await wait_until(lambda: bool(opened))
    assert opened and all(channel.closed for channel in opened)


async def test_idle_watchdog_does_not_reconnect_when_the_probe_cannot_be_queued() -> None:
    handler = make_handler()
    handler._stop_command_workers = True  # noqa: SLF001 - the queue refuses everything
    handler.idle_timeout = 0.0
    handler._last_rx = handler._now() - 1000  # noqa: SLF001
    await handler._check_idle()  # noqa: SLF001
    assert handler._probe_sent_at is None  # noqa: SLF001
    await handler._check_idle()  # noqa: SLF001 - must not raise


async def test_area_status_request_keeps_the_bus_where() -> None:
    handler = make_handler()
    for raw in ("*1*1*3##", "*1*1*00##", "*1*1*100##"):
        await handler._dispatch_message(frame(raw), from_monitor=True)  # noqa: SLF001
    assert queued(handler) == ["*#1*3##", "*#1*00##", "*#1*100##"]


async def test_log_throttle_keys_are_bounded() -> None:
    """``_LogThrottle`` never grows without a bound, whatever the keys look like."""
    handler = make_handler()
    for index in range(500):
        handler._log_limited(logging.WARNING, f"nack-{index}", "x")  # noqa: SLF001
    assert len(handler._throttle._last) <= gateway_module._LogThrottle.MAX_KEYS  # noqa: SLF001


async def test_nack_lines_are_keyed_by_who_and_where() -> None:
    """Two different commands to the same actuator share one throttle slot.

    ``test_log_throttle_keys_are_bounded`` only proves ``MAX_KEYS`` bites; this is
    what the NACK key itself is for. Mutation caught: keying the line on the whole
    frame (``f"nack-{item.message}"``), which gives a broken actuator one WARNING
    per distinct frame instead of one per actuator.
    """
    handler = make_handler()

    def configure(channel: FakeCommandChannel, index: int) -> None:
        channel.responder = lambda message: CommandResult(False, [])  # every command NACKed

    with fake_channels(command=Factory(FakeCommandChannel, configure)):
        async with running(handler, listening=False):
            assert await handler.send(OWNLightingCommand.switch_on("11"))
            assert await handler.send(OWNLightingCommand.switch_off("11"))
            await asyncio.wait_for(handler.send_buffer.join(), 2)
    assert len(handler._throttle._last) == 1  # noqa: SLF001
    key = next(iter(handler._throttle._last))  # noqa: SLF001
    assert key.startswith("nack-") and key.endswith("-11")


async def test_probe_window_is_a_boundary() -> None:
    """``probe_window`` decides when an unanswered probe becomes a reconnect.

    The reconnect path is only reachable when the command session is mute as well
    (a gateway that ACKs short-circuits it, see
    ``test_only_a_command_ack_newer_than_the_probe_keeps_the_session``), so nothing
    drains the command queue here and ``_check_idle`` is driven by hand on a fake
    clock. Mutations caught: ``if now - self._probe_sent_at >= self.probe_window:``
    -> ``if True:`` (every probe becomes a reconnect) and ``>=`` -> ``>`` (the
    boundary itself).
    """
    handler = make_handler()
    register(handler, LIGHT, "1-11")
    clock = FakeClock()
    handler._now = clock  # noqa: SLF001 - shadows the static clock on this instance
    handler.idle_timeout = 100.0
    handler.probe_window = 50.0
    handler._last_rx = -150.0  # noqa: SLF001 - silent for 150 s at clock 0

    await handler._check_idle()  # noqa: SLF001 - queues the probe and arms the window
    assert handler._probe_sent_at == 0.0  # noqa: SLF001
    assert queued(handler) == ["*#1*11##"]

    clock.value = 49.0
    await handler._check_idle()  # noqa: SLF001 - still inside the window: no reconnect

    clock.value = 50.0
    with pytest.raises(SessionError):
        await handler._check_idle()  # noqa: SLF001 - window elapsed, nothing answered


async def test_no_probe_before_the_idle_timeout() -> None:
    """gw-03: the watchdog stays quiet until ``idle_timeout`` has actually elapsed.

    ``test_option_plumbing`` and friends only assert that the attribute holds the
    number the options produced; nothing asserted that the number *gates* anything.
    Mutation caught: ``if idle < self.idle_timeout:`` -> ``if idle < 0.0:``, after
    which the watchdog probes the bus on every single poll of the listening loop
    (``read_poll_interval``: 1 s in production) instead of once every five minutes.
    """
    handler = make_handler()
    register(handler, LIGHT, "1-11")
    clock = FakeClock()
    handler._now = clock  # noqa: SLF001 - shadows the static clock on this instance
    handler.idle_timeout = 100.0
    handler._last_rx = 0.0  # noqa: SLF001

    clock.value = 99.0
    await handler._check_idle()  # noqa: SLF001 - one second short of the timeout
    assert handler._probe_sent_at is None  # noqa: SLF001
    assert queued(handler) == []

    clock.value = 100.0
    await handler._check_idle()  # noqa: SLF001 - the timeout itself must fire
    assert handler._probe_sent_at == 100.0  # noqa: SLF001
    assert queued(handler) == ["*#1*11##"]


async def test_only_a_command_ack_newer_than_the_probe_keeps_the_session() -> None:
    """gw-03 / R7: an ACK proves the gateway is alive only if it postdates the probe.

    The short-circuit exists for gateways that answer on the command port without
    mirroring the reply onto the monitor; both of its arms are decided here on a
    fake clock, with nothing draining the command queue, so neither depends on how
    fast the machine is. This replaces the wall-clock
    ``test_idle_watchdog_keeps_the_session_when_the_probe_is_acked``, which spent
    0.65 s asserting that nothing happened and passed just as happily when the
    runner was too slow to let the watchdog run at all.

    Mutation caught: ``if self._command_ack_at is not None and self._command_ack_at
    >= self._probe_sent_at:`` -> ``if self._command_ack_at is not None:``, after
    which a single ACK from any command the gateway ever answered suppresses the
    reconnect for good - the monitor session can be dead and the watchdog will
    never rebuild it.
    """
    # A stale ACK, from before the probe went out, proves nothing.
    stale = make_handler()
    register(stale, LIGHT, "1-11")
    stale_clock = FakeClock()
    stale._now = stale_clock  # noqa: SLF001
    stale.idle_timeout = 100.0
    stale.probe_window = 50.0
    stale._command_ack_at = -10.0  # noqa: SLF001 - answered ten seconds before clock 0
    stale._last_rx = -150.0  # noqa: SLF001 - silent for 150 s at clock 0

    await stale._check_idle()  # noqa: SLF001 - queues the probe and arms the window
    assert stale._probe_sent_at == 0.0  # noqa: SLF001
    stale_clock.value = 50.0
    with pytest.raises(SessionError):
        await stale._check_idle()  # noqa: SLF001

    # An ACK that postdates the probe re-arms the watchdog instead of reconnecting.
    alive = make_handler()
    register(alive, LIGHT, "1-11")
    alive_clock = FakeClock()
    alive._now = alive_clock  # noqa: SLF001
    alive.idle_timeout = 100.0
    alive.probe_window = 50.0
    alive._last_rx = -150.0  # noqa: SLF001

    await alive._check_idle()  # noqa: SLF001
    assert alive._probe_sent_at == 0.0  # noqa: SLF001
    alive._command_ack_at = 10.0  # noqa: SLF001 - the command port answered after the probe
    alive_clock.value = 50.0
    await alive._check_idle()  # noqa: SLF001 - must not raise
    assert alive._probe_sent_at is None  # noqa: SLF001 - disarmed
    assert alive._last_rx == 50.0  # noqa: SLF001 - the silence clock restarts


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_a_crash_inside_ownd_negotiation_is_a_session_error() -> None:
    """sess-01 (review 2 / G5): OWNd's ``_negotiate()`` is not exception-safe.

    It builds ``OWNSignaling(raw_response.decode())`` with no error handling, so any
    non-OpenWebNet peer listening on port 20000 makes it raise (here a
    ``UnicodeDecodeError``). Before the catch-all in ``own_session.open`` that
    exception escaped ``open()`` and reached ``sending_loop``; it must come back as
    a plain, reconnectable ``SessionError`` - never an ``AuthenticationError``,
    which would pop a reauth dialog at the user - and the socket must be closed.

    Mutation caught: narrowing ``except Exception`` in ``own_session.open`` to any
    other exception type.
    """
    async with FakeOWNServer(garbage_negotiation=True) as server:
        channel = OWNCommandChannel(make_gateway(server.port), LOGGER)
        with pytest.raises(SessionError) as excinfo:
            await channel.open(timeout=2)
        assert "negotiation crashed" in str(excinfo.value)
        assert not isinstance(excinfo.value, AuthenticationError)
        assert channel.is_open is False
        assert channel._stream_writer is None  # noqa: SLF001 - closed on failure
