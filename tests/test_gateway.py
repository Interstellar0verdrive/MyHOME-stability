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
import time
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from OWNd.message import OWNCommand, OWNLightingCommand, OWNMessage

from homeassistant.components.button import DOMAIN as BUTTON
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.sensor import DOMAIN as SENSOR

from custom_components.myhome import gateway as gateway_module
from custom_components.myhome.const import (
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_LONG_PRESS,
    CONF_LONG_RELEASE,
    CONF_PLATFORMS,
    CONF_SHORT_PRESS,
    DOMAIN,
    LOGGER,
    SIGNAL_GATEWAY_CONNECTION,
)
from custom_components.myhome.gateway import (
    EVENT_LONG_PRESS_REPEAT,
    EVENT_ROTATE_CW_SLOW,
    MyHOMEGatewayHandler,
    _QueuedCommand,
)
from custom_components.myhome.myhome_device import MyHOMEEntity
from custom_components.myhome.own_session import (
    AuthenticationError,
    CommandResult,
    OWNCommandChannel,
    OWNEventChannel,
    SessionError,
    parse_frame,
)

from .helpers_core import ENTRY_DATA_V2, MAC

SIGNAL = SIGNAL_GATEWAY_CONNECTION.format(mac=MAC)
LOGGER_NAME = LOGGER.name


def frame(raw: str) -> OWNMessage | str:
    return parse_frame(raw, LOGGER, "[test]")


async def wait_until(predicate: Callable[[], bool], timeout: float = 3.0) -> None:
    """Poll ``predicate`` until true or fail."""
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.005)


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
) -> MyHOMEGatewayHandler:
    """Handler on a MagicMock hass with fast timings."""
    hass = MagicMock()
    gateway_cfg: dict[str, Any] = {CONF_PLATFORMS: platforms or {}}
    if sensor_defaults:
        gateway_cfg["sensor_defaults"] = sensor_defaults
    hass.data = {DOMAIN: {MAC: gateway_cfg}}
    hass.bus = MagicMock()
    entry = MagicMock()
    entry.data = dict(ENTRY_DATA_V2)
    entry.async_start_reauth = MagicMock()
    handler = MyHOMEGatewayHandler(hass, entry, generate_events=generate_events)
    hass.data[DOMAIN][MAC][CONF_ENTITY] = handler
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


def fired(hass: MagicMock, event_type: str) -> list[dict[str, Any]]:
    return [call.args[1] for call in hass.bus.async_fire.call_args_list if call.args[0] == event_type]


def queued(handler: MyHOMEGatewayHandler) -> list[str]:
    return [str(item.message) for item in list(handler.send_buffer._queue)]  # noqa: SLF001


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
    assert any("dropped after two attempts" in record.message and record.levelno == logging.WARNING for record in caplog.records)


async def test_command_ttl_expired_is_dropped_without_sending(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    stale = _QueuedCommand(OWNLightingCommand.switch_on("11"), False, time.monotonic() - 120)
    handler.send_buffer.put_nowait(stale)
    with fake_channels() as (_, command, _):
        async with running(handler, listening=False):
            await asyncio.wait_for(handler.send_buffer.join(), 2)
    assert all(channel.sent == [] for channel in command.instances)
    assert any("Dropping `*1*1*11##`" in record.message and record.levelno == logging.WARNING for record in caplog.records)


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
    """gw-04: None from the session is a broken connection; reconnects are paced."""
    handler = make_handler()
    handler.initial_backoff = 0.02
    handler.max_backoff = 0.08

    def configure(channel: FakeEventChannel, index: int) -> None:
        channel.feed(None)

    with fake_channels(event=Factory(FakeEventChannel, configure)) as (event, _, dispatch):
        async with running(handler, sending=False):
            await asyncio.sleep(0.3)
            count = len(event.instances)
    # 0.02 + 0.04 + 0.08 + 0.08 ... -> a handful of attempts in 0.3 s, not thousands.
    assert 2 <= count <= 8
    assert all(channel.closed for channel in event.instances)
    assert dispatch.call_args_list[0].args == (handler.hass, SIGNAL, True)
    assert dispatch.call_args_list[1].args == (handler.hass, SIGNAL, False)


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
    assert [call.args[2] for call in dispatch.call_args_list] == [True, False, True, False]
    assert all(call.args[:2] == (handler.hass, SIGNAL) for call in dispatch.call_args_list)
    assert handler.is_connected is False


async def test_idle_watchdog_probes_then_reconnects(caplog: pytest.LogCaptureFixture) -> None:
    """gw-03: silence -> probe on the command session -> still silent -> reconnect."""
    caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)
    handler = make_handler()
    register(handler, LIGHT, "1-11")
    with fake_channels() as (event, command, _):
        async with running(handler):
            await wait_until(lambda: command.instances and command.instances[0].sent, timeout=3)
            assert command.instances[0].sent == ["*#1*11##"]  # point-to-point probe
            await wait_until(lambda: len(event.instances) == 2, timeout=3)
            # A live monitor keeps the second session: frames faster than idle_timeout.
            for _ in range(6):
                event.instances[1].feed("*1*1*11##")
                await asyncio.sleep(0.05)
            assert len(event.instances) == 2
    assert any("probe went unanswered" in record.message for record in caplog.records)


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
    assert not any(call.args[2] for call in dispatch.call_args_list)


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


async def test_preset_level_refreshes_configured_light() -> None:
    handler = make_handler()
    light = register(handler, LIGHT, "1-11")
    await handler._dispatch_message(frame("*1*7*11##"), from_monitor=True)  # noqa: SLF001
    assert light.updates == 1
    assert light.events == []


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
    assert events[0] == {"object": 1, "pushbutton": 1, "event": CONF_SHORT_PRESS}
    assert events[-1] == {"object": 2, "pushbutton": 2, "event": EVENT_ROTATE_CW_SLOW}
    assert all(event["event"] is not None for event in events)


# --------------------------------------------------------------------------- energy throttle
async def test_throttle_applies_only_to_active_power() -> None:
    """gw-06 / sc-02 / sc-03: OR semantics on instant power; totals always pass."""
    handler = make_handler(sensor_defaults={"min_delta_w": 5, "min_interval_sec": 0.2})
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
    await asyncio.sleep(0.25)
    await dispatch("*#18*51*113*632##")  # +2 W but interval elapsed -> accepted (OR)
    assert meter.events == [
        "*#18*51*113*613##",
        "*#18*51*51*1234567##",
        "*#18*51*54*4321##",
        "*#18*51*53*98765##",
        "*#18*51*113*630##",
        "*#18*51*113*632##",
    ]


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
    assert [call.args[2] for call in dispatch.call_args_list] == [True, False]
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
    ) -> None:
        self.replies = replies or {}
        self.nonce = nonce
        self.password_ok = password_ok
        self.answer = answer
        self.initial_frames = initial_frames or []
        self.close_after_initial = close_after_initial
        self.default_replies = ["*#*0##"] if default_replies is None else default_replies
        self.received: list[str] = []
        self.sessions: list[str] = []
        self.monitor_writers: list[asyncio.StreamWriter] = []
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
        self.server.close()
        await self.server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            writer.write(b"*#*1##")
            session = (await reader.readuntil(b"##")).decode()
            self.sessions.append(session)
            if self.nonce is not None:
                writer.write(f"*#{self.nonce}##".encode())
                await writer.drain()
                self.received.append((await reader.readuntil(b"##")).decode())
                writer.write(b"*#*1##" if self.password_ok else b"*#*0##")
                await writer.drain()
                if not self.password_ok:
                    return
            else:
                writer.write(b"*#*1##")
            for item in self.initial_frames:
                writer.write(item.encode())
            await writer.drain()
            if self.close_after_initial:
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

    return OWNGateway({"address": "127.0.0.1", "port": port, "password": password, "serialNumber": MAC, "modelName": "Fake"})


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
    # Refused connection -> OSError, never a silent None.
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    free_port = probe.getsockname()[1]
    probe.close()
    channel = OWNCommandChannel(make_gateway(free_port), LOGGER)
    with pytest.raises(OSError):
        await channel.open(timeout=2)
    await channel.close()


def test_parse_frame_never_raises() -> None:
    assert isinstance(frame("*1*1*11##"), OWNMessage)
    assert frame("*25*21*21##") == "*25*21*21##"  # OWNd raises IndexError
    assert frame("*#13**22*1##") == "*#13**22*1##"  # OWNd raises IndexError
    assert frame("garbage##") == "garbage##"
