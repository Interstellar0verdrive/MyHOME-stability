"""MyHOME gateway handler: connection, command and event layer (Contract B).

One :class:`MyHOMEGatewayHandler` per gateway owns

- the EVENT (monitor) session: :meth:`listening_loop` keeps it alive with TCP
  keepalive plus an idle watchdog (no frame for ``idle_timeout`` -> probe through
  the command session -> still nothing on the monitor -> reconnect), verifies every
  ``connect`` result, reconnects with exponential backoff (1..60 s) and never hot
  loops; a password rejection sets ``auth_failed``, stops the loops and starts the
  reauth flow;
- the COMMAND session(s): :meth:`sending_loop` drains a bounded queue with a TTL,
  sends each command under a timeout, retries ONCE in place with a fresh session and
  then drops the command with a rate-limited WARNING - never "silently done";
- the dispatcher: every reply frame (monitor or command session) goes through
  :meth:`_dispatch_message`; every call into an entity is isolated with
  ``try``/``except`` so an entity bug never tears a session down;
- availability: ``is_connected`` is True only while the event session is verified
  alive and every transition is published on ``SIGNAL_GATEWAY_CONNECTION``.

The public surface consumed by ``__init__.py`` and the platforms (``mac``,
``unique_id``, ``name``, ``is_connected``, ``device_id``, ``auth_failed``,
``send``, ``send_status_request``, ``listening_loop``, ``sending_loop``,
``close_listener``, ``test``, the discovery hooks) is unchanged in shape.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from OWNd.connection import OWNGateway, OWNSession
from OWNd.message import (
    MESSAGE_TYPE_ACTIVE_POWER,
    OWNAutomationCommand,
    OWNAutomationEvent,
    OWNAuxEvent,
    OWNCENEvent,
    OWNCENPlusEvent,
    OWNCommand,
    OWNDryContactEvent,
    OWNEnergyCommand,
    OWNEnergyEvent,
    OWNGatewayCommand,
    OWNGatewayEvent,
    OWNHeatingCommand,
    OWNHeatingEvent,
    OWNLightingCommand,
    OWNLightingEvent,
    OWNMessage,
)

from homeassistant.components.button import DOMAIN as BUTTON
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.light import DOMAIN as LIGHT
from homeassistant.components.sensor import DOMAIN as SENSOR
from homeassistant.components.switch import DOMAIN as SWITCH
from homeassistant.const import (
    CONF_ENTITIES,
    CONF_FRIENDLY_NAME,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_BUS_INTERFACE,
    CONF_DEVICE_TYPE,
    CONF_FIRMWARE,
    CONF_INFO_LOG_INTERVAL_SEC,
    CONF_LONG_PRESS,
    CONF_LONG_RELEASE,
    CONF_MANUFACTURER,
    CONF_MANUFACTURER_URL,
    CONF_MIN_DELTA_W,
    CONF_MIN_INTERVAL_SEC,
    CONF_PLATFORMS,
    CONF_SENSOR_DEFAULTS,
    CONF_SHORT_PRESS,
    CONF_SHORT_RELEASE,
    CONF_SSDP_LOCATION,
    CONF_SSDP_ST,
    CONF_SUPPRESS_LOG_INTERVAL_SEC,
    CONF_UDN,
    CONF_WHERE,
    CONF_ZONE,
    DOMAIN,
    EVENT_LONG_PRESS_REPEAT,
    EVENT_ROTATE_CCW_FAST,
    EVENT_ROTATE_CCW_SLOW,
    EVENT_ROTATE_CW_FAST,
    EVENT_ROTATE_CW_SLOW,
    LOGGER,
    SIGNAL_GATEWAY_CONNECTION,
)
from .myhome_device import MyHOMEEntity
from .own_session import (
    AuthenticationError,
    CommandResult,
    OWNCommandChannel,
    OWNEventChannel,
    SessionError,
)

# --------------------------------------------------------------------------- tuning
# Command path (Contract B).
COMMAND_TIMEOUT_SEC = 10.0  # write + wait for ACK/NACK
CONNECT_TIMEOUT_SEC = 10.0  # TCP connect + negotiation, one attempt
COMMAND_QUEUE_MAXSIZE = 200
COMMAND_TTL_SEC = 60.0  # commands older than this are dropped when dequeued
COMMAND_SESSION_IDLE_SEC = 60.0  # close an unused command session (gateway session limit)
# Event path.
IDLE_TIMEOUT_SEC = 300.0  # no monitor frame for this long -> probe
PROBE_WINDOW_SEC = 30.0  # probe sent, still nothing on the monitor -> reconnect
READ_POLL_SEC = 30.0  # wake-up cadence of the listening loop (watchdog granularity)
INITIAL_BACKOFF_SEC = 1.0
MAX_BACKOFF_SEC = 60.0
# Logging.
LOG_RATE_LIMIT_SEC = 60.0
RECONNECT_LOG_RATE_LIMIT_SEC = 300.0

# Energy throttle code defaults (validate.py normally supplies every key).
DEFAULT_MIN_DELTA_W = 5
DEFAULT_MIN_INTERVAL_SEC = 1.0
DEFAULT_SUPPRESS_LOG_INTERVAL_SEC = 60.0
DEFAULT_INFO_LOG_INTERVAL_SEC = 0.0  # 0 = the INFO heartbeat is off (chatter stays at DEBUG)

_TRANSPORT_ERRORS = (SessionError, OSError, EOFError, TimeoutError)
_ENTITY_EVENT_TYPES = (OWNLightingEvent, OWNAutomationEvent, OWNDryContactEvent, OWNAuxEvent, OWNHeatingEvent)


@dataclass(slots=True)
class _QueuedCommand:
    message: OWNCommand
    is_status_request: bool
    enqueued_at: float


@dataclass(slots=True, frozen=True)
class _EnergySettings:
    min_delta_w: int
    min_interval_sec: float
    suppress_log_interval_sec: float
    info_log_interval_sec: float


class _LogThrottle:
    """Per-key rate limiter for repeated log lines (counts what it suppressed)."""

    def __init__(self) -> None:
        self._last: dict[str, float] = {}
        self._suppressed: dict[str, int] = {}

    def check(self, key: str, interval: float, now: float) -> tuple[bool, int]:
        """Return (log it?, number of suppressed lines since the last emitted one)."""
        last = self._last.get(key)
        if last is not None and interval > 0 and now - last < interval:
            self._suppressed[key] = self._suppressed.get(key, 0) + 1
            return False, 0
        self._last[key] = now
        return True, self._suppressed.pop(key, 0)

    def reset(self, key: str) -> None:
        self._last.pop(key, None)
        self._suppressed.pop(key, None)


def _safe_is_on(message: OWNLightingEvent | OWNAutomationEvent) -> bool | None:
    """``OWNLightingEvent.is_on`` raises TypeError on dimension replies without a
    state (timer / PIR / illuminance frames, plat-03): report "unknown" instead."""
    try:
        return bool(message.is_on)
    except TypeError:
        return None


def _automation_event_name(message: OWNAutomationEvent) -> str:
    if message.is_opening and not message.is_closing:
        return "open"
    if message.is_closing and not message.is_opening:
        return "close"
    return "stop"


class MyHOMEGatewayHandler:
    """Manages a single MyHOME Gateway."""

    def __init__(self, hass, config_entry, generate_events: bool = False) -> None:
        build_info = {
            "address": config_entry.data[CONF_HOST],
            "port": config_entry.data[CONF_PORT],
            "password": config_entry.data[CONF_PASSWORD],
            "ssdp_location": config_entry.data[CONF_SSDP_LOCATION],
            "ssdp_st": config_entry.data[CONF_SSDP_ST],
            "deviceType": config_entry.data[CONF_DEVICE_TYPE],
            "friendlyName": config_entry.data[CONF_FRIENDLY_NAME],
            "manufacturer": config_entry.data[CONF_MANUFACTURER],
            "manufacturerURL": config_entry.data[CONF_MANUFACTURER_URL],
            "modelName": config_entry.data[CONF_NAME],
            "modelNumber": config_entry.data[CONF_FIRMWARE],
            "serialNumber": config_entry.data[CONF_MAC],
            "UDN": config_entry.data[CONF_UDN],
        }
        self.hass = hass
        self.config_entry = config_entry
        self.generate_events = generate_events
        self.gateway = OWNGateway(build_info)

        # Contract B public state.
        self.device_id: str | None = None  # set by __init__.py after creating the gateway device
        self.auth_failed: bool = False
        self.is_connected: bool = False
        self.listening_worker: asyncio.Task | None = None
        self.sending_workers: list[asyncio.Task] = []
        self.send_buffer: asyncio.Queue[_QueuedCommand] = asyncio.Queue(maxsize=COMMAND_QUEUE_MAXSIZE)

        # Loop control.
        self._closed = False
        self._stop_event_listener = False
        self._stop_command_workers = False
        self._event_session: OWNEventChannel | None = None
        self._command_sessions: dict[int, OWNCommandChannel] = {}
        self._last_rx: float = 0.0
        self._probe_sent_at: float | None = None

        # Timing knobs (instance attributes so tests can shrink them).
        self.command_timeout = COMMAND_TIMEOUT_SEC
        self.connect_timeout = CONNECT_TIMEOUT_SEC
        self.command_ttl = COMMAND_TTL_SEC
        self.command_session_idle = COMMAND_SESSION_IDLE_SEC
        self.idle_timeout = IDLE_TIMEOUT_SEC
        self.probe_window = PROBE_WINDOW_SEC
        self.read_poll_interval = READ_POLL_SEC
        self.initial_backoff = INITIAL_BACKOFF_SEC
        self.max_backoff = MAX_BACKOFF_SEC

        # Energy throttle bookkeeping (instant active power only, gw-06 / sc-02 / sc-03).
        self._energy_settings_cache: dict[str, _EnergySettings] = {}
        self._last_energy_watts: dict[str, int] = {}
        self._last_energy_ts: dict[str, float] = {}
        self._energy_suppress_count: dict[str, int] = {}
        self._last_energy_suppress_log_ts: dict[str, float] = {}
        self._last_energy_info_log_ts: dict[str, float] = {}

        self._throttle = _LogThrottle()
        self.discovery_service = None

    # ------------------------------------------------------------------ properties
    @property
    def mac(self) -> str:
        return self.gateway.serial

    @property
    def unique_id(self) -> str:
        return self.mac

    @property
    def log_id(self) -> str:
        return self.gateway.log_id

    @property
    def manufacturer(self) -> str:
        return self.gateway.manufacturer

    @property
    def name(self) -> str:
        return f"{self.gateway.model_name} Gateway"

    @property
    def model(self) -> str:
        return self.gateway.model_name

    @property
    def firmware(self) -> str:
        return self.gateway.firmware

    async def test(self) -> dict | None:
        """Connection test used by setup / config flow (OWNd semantics: may return None)."""
        return await OWNSession(gateway=self.gateway, logger=LOGGER).test_connection()

    # ------------------------------------------------------------------ discovery hooks
    def initialize_discovery_service(self) -> None:
        """Create the discovery service (lazy import: discovery.py imports this module)."""
        if self.discovery_service is None:
            from .discovery import MyHOMEDeviceDiscoveryService

            self.discovery_service = MyHOMEDeviceDiscoveryService(self.hass, self.config_entry, self)
            LOGGER.debug("%s Discovery service initialized", self.log_id)

    async def start_device_discovery(self) -> None:
        if self.discovery_service:
            await self.discovery_service.start_discovery()
        else:
            LOGGER.warning("%s Discovery service not initialized", self.log_id)

    async def stop_device_discovery(self) -> None:
        if self.discovery_service:
            await self.discovery_service.stop_discovery()

    def handle_discovery_message(self, message: OWNMessage) -> None:
        if self.discovery_service:
            self.discovery_service.handle_discovery_message(message)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def _gw_cfg(self) -> dict[str, Any]:
        """The validated gateway config in hass.data (empty after unload)."""
        data = self.hass.data.get(DOMAIN) if isinstance(self.hass.data, dict) else None
        cfg = (data or {}).get(self.mac)
        return cfg if isinstance(cfg, dict) else {}

    def _platform_cfg(self, platform: str) -> dict[str, Any]:
        platforms = self._gw_cfg().get(CONF_PLATFORMS)
        cfg = (platforms or {}).get(platform)
        return cfg if isinstance(cfg, dict) else {}

    def _log_limited(
        self,
        level: int,
        key: str,
        msg: str,
        *args: Any,
        interval: float = LOG_RATE_LIMIT_SEC,
        exc_info: bool = False,
    ) -> None:
        """Log ``msg`` at ``level`` at most once per ``interval`` seconds per ``key``."""
        emit, suppressed = self._throttle.check(key, interval, self._now())
        if not emit:
            return
        if suppressed:
            msg = f"{msg} ({suppressed} similar message(s) suppressed)"
        LOGGER.log(level, msg, *args, exc_info=exc_info)

    def _set_connected(self, connected: bool) -> None:
        """Update ``is_connected`` and publish every transition (Contract B, gw-10)."""
        if connected == self.is_connected:
            return
        self.is_connected = connected
        LOGGER.info("%s Gateway is %s", self.log_id, "connected" if connected else "disconnected")
        try:
            async_dispatcher_send(self.hass, SIGNAL_GATEWAY_CONNECTION.format(mac=self.mac), connected)
        except Exception:  # noqa: BLE001 - never let a subscriber break the session loop
            LOGGER.exception("%s Error while publishing the connection state", self.log_id)

    async def _close_session(self, session: OWNEventChannel | OWNCommandChannel | None) -> None:
        if session is None:
            return
        try:
            await session.close()
        except Exception:  # noqa: BLE001 - closing must never raise
            LOGGER.debug("%s Error while closing a session", self.log_id, exc_info=True)

    def _handle_auth_failure(self, err: AuthenticationError, session_type: str) -> None:
        """Password rejected at runtime: stop everything and ask for reauth (gw-05)."""
        self._stop_event_listener = True
        self._stop_command_workers = True
        self._set_connected(False)
        if self.auth_failed:
            return
        self.auth_failed = True
        LOGGER.error(
            "%s The gateway rejected the password on the %s session (%s): reconfigure the integration",
            self.log_id,
            session_type,
            err.reason,
        )
        try:
            self.config_entry.async_start_reauth(self.hass)
        except Exception:  # noqa: BLE001 - reauth is best effort (e.g. entry being unloaded)
            LOGGER.debug("%s Could not start the reauth flow", self.log_id, exc_info=True)

    # ------------------------------------------------------------------ command API
    async def send(self, message: OWNCommand) -> bool:
        """Queue a command; False (and a rate-limited WARNING) if it cannot be queued."""
        return self._enqueue(message, is_status_request=False)

    async def send_status_request(self, message: OWNCommand) -> bool:
        """Queue a status request (logged at DEBUG only); same semantics as ``send``."""
        return self._enqueue(message, is_status_request=True)

    def _enqueue(self, message: OWNCommand, *, is_status_request: bool) -> bool:
        if self._closed or self._stop_command_workers:
            self._log_limited(
                logging.WARNING, "queue-closed", "%s Cannot send `%s`: the gateway handler is closed", self.log_id, message
            )
            return False
        try:
            self.send_buffer.put_nowait(_QueuedCommand(message, is_status_request, self._now()))
        except asyncio.QueueFull:
            self._log_limited(
                logging.WARNING,
                "queue-full",
                "%s Command queue full (%d pending): dropping `%s` - is the gateway reachable?",
                self.log_id,
                self.send_buffer.maxsize,
                message,
            )
            return False
        LOGGER.debug("%s Queued `%s`", self.log_id, message)
        return True

    def _drain_queue(self) -> list[_QueuedCommand]:
        dropped: list[_QueuedCommand] = []
        while True:
            try:
                dropped.append(self.send_buffer.get_nowait())
            except asyncio.QueueEmpty:
                return dropped
            self.send_buffer.task_done()

    # ------------------------------------------------------------------ sending loop
    async def sending_loop(self, worker_id: int) -> None:
        """Deliver queued commands on a command session (Contract B command path)."""
        if self._closed:
            return
        LOGGER.debug("%s Sending worker %s started", self.log_id, worker_id)
        session: OWNCommandChannel | None = None
        backoff = self.initial_backoff
        try:
            while not self._stop_command_workers:
                try:
                    item = await asyncio.wait_for(self.send_buffer.get(), timeout=self.command_session_idle)
                except TimeoutError:
                    # Nothing to send for a while: give the session back to the
                    # gateway (MyHOMEServer1 has a small concurrent-session limit).
                    if session is not None:
                        LOGGER.debug("%s Closing idle command session (worker %s)", self.log_id, worker_id)
                        await self._close_session(session)
                        session = None
                        self._command_sessions.pop(worker_id, None)
                    continue

                try:
                    age = self._now() - item.enqueued_at
                    if age > self.command_ttl:
                        self._log_limited(
                            logging.WARNING,
                            "cmd-expired",
                            "%s Dropping `%s`: queued %.0f s ago (gateway unreachable?)",
                            self.log_id,
                            item.message,
                            age,
                        )
                        continue

                    session, delivered = await self._deliver(session, worker_id, item)
                    if delivered:
                        backoff = self.initial_backoff
                    elif not self._stop_command_workers:
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, self.max_backoff)
                finally:
                    self.send_buffer.task_done()
        finally:
            await self._close_session(session)
            self._command_sessions.pop(worker_id, None)
            LOGGER.debug("%s Sending worker %s stopped", self.log_id, worker_id)

    async def _deliver(
        self, session: OWNCommandChannel | None, worker_id: int, item: _QueuedCommand
    ) -> tuple[OWNCommandChannel | None, bool]:
        """Send one command: retry ONCE in place with a fresh session, then drop it.

        Returns the (possibly new) session and whether the gateway answered
        (ACK or NACK).  Never re-queues (gw-11): ordering is preserved and a
        stale command is never replayed later.
        """
        for attempt in (1, 2):
            try:
                if session is None:
                    session = OWNCommandChannel(self.gateway, LOGGER)
                    await session.open(self.connect_timeout)
                    self._command_sessions[worker_id] = session
                    LOGGER.debug("%s Command session established (worker %s)", self.log_id, worker_id)
                result = await session.send_command(item.message, self.command_timeout)
            except AuthenticationError as err:
                await self._close_session(session)
                self._command_sessions.pop(worker_id, None)
                self._handle_auth_failure(err, "command")
                return None, False
            except _TRANSPORT_ERRORS as err:
                await self._close_session(session)
                session = None
                self._command_sessions.pop(worker_id, None)
                if attempt == 1:
                    LOGGER.debug(
                        "%s Sending `%s` failed (%s: %s); retrying once with a fresh session",
                        self.log_id,
                        item.message,
                        type(err).__name__,
                        err,
                    )
                    continue
                self._log_limited(
                    logging.WARNING,
                    "cmd-dropped",
                    "%s Command `%s` dropped after two attempts: %s: %s",
                    self.log_id,
                    item.message,
                    type(err).__name__,
                    err,
                )
                return None, False
            await self._on_command_result(item, result)
            return session, True
        return session, False  # pragma: no cover - loop always returns

    async def _on_command_result(self, item: _QueuedCommand, result: CommandResult) -> None:
        """Log the outcome and dispatch every reply frame like a monitor event (sc-01, gw-13)."""
        if result.acknowledged:
            LOGGER.debug("%s `%s` acknowledged (%d reply frame(s))", self.log_id, item.message, len(result.replies))
        else:
            self._log_limited(
                logging.WARNING,
                f"nack-{item.message}",
                "%s The gateway refused `%s` (NACK)",
                self.log_id,
                item.message,
            )
        for reply in result.replies:
            LOGGER.debug("%s Reply: `%s`", self.log_id, reply)
            await self._dispatch_message(reply, from_monitor=False)

    # ------------------------------------------------------------------ listening loop
    async def listening_loop(self) -> None:
        """Keep the event session alive and dispatch its frames (Contract B event path)."""
        if self._closed:
            return
        LOGGER.info("%s Listening loop started", self.log_id)
        session: OWNEventChannel | None = None
        backoff = self.initial_backoff
        try:
            while not self._stop_event_listener:
                try:
                    if session is None:
                        session = OWNEventChannel(self.gateway, LOGGER)
                        await session.open(self.connect_timeout)
                        self._event_session = session
                        self._last_rx = self._now()
                        self._probe_sent_at = None
                        # NOTE: the backoff is reset only once the session proves
                        # alive (a frame, or a full poll interval without failure):
                        # "connect then fail at once" must keep slowing down.
                        LOGGER.info("%s Event session established", self.log_id)
                        self._set_connected(True)

                    try:
                        message = await asyncio.wait_for(session.get_next(), timeout=self.read_poll_interval)
                    except TimeoutError:
                        # Nothing in read_poll_interval: the session survived, run
                        # the idle watchdog. Only the raw read sits inside wait_for,
                        # so a cancel here is safe (OWNd's own reconnect sleeps are
                        # never involved, gw-16).
                        backoff = self.initial_backoff
                        self._throttle.reset("event-lost")
                        await self._check_idle()
                        continue

                    if message is None:
                        # Only a plain OWNd session returns None (it swallowed an
                        # error): treat it as a broken connection, never spin (gw-04).
                        raise SessionError("event session returned no data")

                    self._last_rx = self._now()
                    self._probe_sent_at = None
                    backoff = self.initial_backoff
                    self._throttle.reset("event-lost")
                    if not isinstance(message, OWNMessage):
                        LOGGER.debug("%s Ignoring unparsable frame `%s`", self.log_id, message)
                        self._fire_raw_message_event(message)
                        continue
                    LOGGER.debug("%s Event: `%s`", self.log_id, message)
                    await self._dispatch_message(message, from_monitor=True)

                except AuthenticationError as err:
                    await self._close_session(session)
                    session = None
                    self._event_session = None
                    self._handle_auth_failure(err, "event")
                    break
                except _TRANSPORT_ERRORS as err:
                    self._set_connected(False)
                    await self._close_session(session)
                    session = None
                    self._event_session = None
                    if self._stop_event_listener:
                        break
                    self._log_limited(
                        logging.WARNING,
                        "event-lost",
                        "%s Event session lost (%s: %s); reconnecting in %.0f s",
                        self.log_id,
                        type(err).__name__,
                        err,
                        backoff,
                        interval=RECONNECT_LOG_RATE_LIMIT_SEC,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.max_backoff)
                except Exception:  # noqa: BLE001 - a bug in this loop must not kill the task
                    self._set_connected(False)
                    await self._close_session(session)
                    session = None
                    self._event_session = None
                    if self._stop_event_listener:
                        break
                    LOGGER.exception("%s Unexpected error in the listening loop; reconnecting in %.0f s", self.log_id, backoff)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.max_backoff)
        finally:
            self._set_connected(False)
            await self._close_session(session)
            self._event_session = None
            LOGGER.info("%s Listening loop stopped", self.log_id)

    async def _check_idle(self) -> None:
        """Idle watchdog (gw-03): probe after ``idle_timeout``, reconnect if the
        probe produces nothing on the monitor within ``probe_window``."""
        now = self._now()
        idle = now - self._last_rx
        if idle < self.idle_timeout:
            return
        if self._probe_sent_at is None:
            probe = self._probe_command()
            LOGGER.debug("%s No event for %.0f s: probing the bus with `%s`", self.log_id, idle, probe)
            self._probe_sent_at = now
            await self.send_status_request(probe)
            return
        if now - self._probe_sent_at >= self.probe_window:
            raise SessionError(f"no event for {idle:.0f} s and the probe went unanswered")

    def _probe_command(self) -> OWNCommand:
        """A harmless status request whose reply shows up on the monitor session.

        Prefer a point-to-point actuator of the configuration; fall back to an
        energy meter, a thermo zone and finally the general lighting status.
        """
        for platform, factory in ((LIGHT, OWNLightingCommand.status), (SWITCH, OWNLightingCommand.status), (COVER, OWNAutomationCommand.status)):
            for device in self._platform_cfg(platform).values():
                where = str(device.get(CONF_WHERE) or "")
                if where.isdigit() and len(where) in (2, 4) and where != "00":
                    interface = device.get(CONF_BUS_INTERFACE)
                    return factory(f"{where}#4#{interface}" if interface else where)
        for device in self._platform_cfg(SENSOR).values():
            where = str(device.get(CONF_WHERE) or "")
            if str(device.get("who")) == "18" and where:
                return OWNEnergyCommand.get_total_consumption(where)
        for device in self._platform_cfg(CLIMATE).values():
            zone = device.get(CONF_ZONE)
            if zone:
                return OWNHeatingCommand.get_temperature(str(zone))
        return OWNLightingCommand.status("0")

    # ------------------------------------------------------------------ dispatcher
    def _fire_raw_message_event(self, text: str) -> None:
        if self.generate_events:
            self.hass.bus.async_fire("myhome_message_event", {"gateway": str(self.gateway.host), "message": str(text)})

    async def _dispatch_message(self, message: OWNMessage, *, from_monitor: bool) -> None:
        """Route one parsed frame; never raises (gw-08).

        ``from_monitor`` frames also feed ``myhome_message_event`` (when enabled);
        replies read on the command session only reach discovery and the entities.
        """
        try:
            if self.generate_events and from_monitor:
                try:
                    content = {"gateway": str(self.gateway.host)}
                    content.update(message.event_content)
                    self.hass.bus.async_fire("myhome_message_event", content)
                except Exception:  # noqa: BLE001 - OWNd event_content can choke on odd frames
                    LOGGER.debug("%s Could not build event content for `%s`", self.log_id, message, exc_info=True)

            try:
                self.handle_discovery_message(message)
            except Exception:  # noqa: BLE001
                self._log_limited(logging.WARNING, "discovery", "%s Discovery failed on `%s`", self.log_id, message, exc_info=True)

            if isinstance(message, OWNEnergyEvent):
                self._handle_energy_event(message)
                return

            if isinstance(message, _ENTITY_EVENT_TYPES):
                if message.is_translation:
                    LOGGER.debug("%s Ignoring translation message `%s`", self.log_id, message)
                    return
                if isinstance(message, OWNLightingEvent) and await self._handle_lighting_scope(message):
                    return
                if isinstance(message, OWNAutomationEvent) and self._handle_automation_scope(message):
                    return
                if isinstance(message, OWNLightingEvent) and message.brightness_preset:
                    await self._refresh_light(message.entity)
                    return
                self._dispatch_to_entities(message)
                return

            if isinstance(message, OWNHeatingCommand) and message.dimension is not None and int(message.dimension) == 14:
                where = message.where[1:] if str(message.where).startswith("#") else message.where
                LOGGER.debug("%s Heating command seen, requesting status of zone %s", self.log_id, where)
                await self.send_status_request(OWNHeatingCommand.status(where))
                return

            if isinstance(message, OWNCENPlusEvent):
                self._fire_cenplus_event(message)
                return

            if isinstance(message, OWNCENEvent):
                self._fire_cen_event(message)
                return

            if isinstance(message, (OWNGatewayEvent, OWNGatewayCommand)):
                LOGGER.debug("%s %s", self.log_id, message.human_readable_log)
                return

            LOGGER.debug("%s Unsupported message `%s`", self.log_id, message)
        except Exception:  # noqa: BLE001 - dispatch errors must never reach the session loops
            self._log_limited(
                logging.ERROR, "dispatch", "%s Error while dispatching `%s`", self.log_id, message, exc_info=True
            )

    async def _handle_lighting_scope(self, message: OWNLightingEvent) -> bool:
        """General / area / group lighting frames: fire the bus event and re-request
        the affected states (no sleep in the receive path, gw-18)."""
        state = _safe_is_on(message)
        event = "on" if state else "off"
        if message.is_general:
            self.hass.bus.async_fire("myhome_general_light_event", {"message": str(message), "event": event})
            await self.send_status_request(OWNLightingCommand.status("0"))
            return True
        if message.is_area:
            self.hass.bus.async_fire(
                "myhome_area_light_event", {"message": str(message), "area": message.area, "event": event}
            )
            await self.send_status_request(OWNLightingCommand.status(message.area))
            return True
        if message.is_group:
            self.hass.bus.async_fire(
                "myhome_group_light_event", {"message": str(message), "group": message.group, "event": event}
            )
            return True
        return False

    def _handle_automation_scope(self, message: OWNAutomationEvent) -> bool:
        if message.is_general:
            self.hass.bus.async_fire(
                "myhome_general_automation_event", {"message": str(message), "event": _automation_event_name(message)}
            )
            return True
        if message.is_area:
            self.hass.bus.async_fire(
                "myhome_area_automation_event",
                {"message": str(message), "area": message.area, "event": _automation_event_name(message)},
            )
            return True
        if message.is_group:
            self.hass.bus.async_fire(
                "myhome_group_automation_event",
                {"message": str(message), "group": message.group, "event": _automation_event_name(message)},
            )
            return True
        return False

    def _entities_for(self, entity_key: str) -> list[MyHOMEEntity]:
        """Registered entity objects for a ``who-where`` key, buttons excluded (plat-09)."""
        found: list[MyHOMEEntity] = []
        platforms = self._gw_cfg().get(CONF_PLATFORMS) or {}
        for platform, devices in platforms.items():
            if platform == BUTTON or not isinstance(devices, dict):
                continue
            device = devices.get(entity_key)
            if not isinstance(device, dict):
                continue
            entities = device.get(CONF_ENTITIES) or {}
            found.extend(obj for obj in list(entities.values()) if isinstance(obj, MyHOMEEntity))
        return found

    def _dispatch_to_entities(self, message: OWNMessage) -> None:
        entities = self._entities_for(message.entity)
        if not entities:
            LOGGER.debug("%s No entity configured for `%s` (%s)", self.log_id, message, message.entity)
            return
        for obj in entities:
            try:
                obj.handle_event(message)
            except Exception:  # noqa: BLE001 - an entity bug must not affect the session (gw-08)
                self._log_limited(
                    logging.ERROR,
                    f"entity-{obj.unique_id}",
                    "%s %s failed to handle `%s`",
                    self.log_id,
                    obj.unique_id,
                    message,
                    exc_info=True,
                )

    async def _refresh_light(self, entity_key: str) -> None:
        """A dimmer reached a preset level: ask the light entity for its real brightness (plat-02)."""
        device = self._platform_cfg(LIGHT).get(entity_key)
        obj = (device.get(CONF_ENTITIES) or {}).get(LIGHT) if isinstance(device, dict) else None
        if not isinstance(obj, MyHOMEEntity):
            LOGGER.debug("%s Preset level for %s, which is not a configured light", self.log_id, entity_key)
            return
        try:
            await obj.async_update()
        except Exception:  # noqa: BLE001
            self._log_limited(
                logging.ERROR, f"entity-{obj.unique_id}", "%s %s failed to refresh", self.log_id, obj.unique_id, exc_info=True
            )

    def _fire_cenplus_event(self, message: OWNCENPlusEvent) -> None:
        """CEN+ contract: ``myhome_cenplus_event`` {object, pushbutton, event} (gw-14)."""
        if message.is_short_pressed:
            event = CONF_SHORT_PRESS
        elif message.is_held:
            event = CONF_LONG_PRESS
        elif message.is_still_held:
            event = EVENT_LONG_PRESS_REPEAT
        elif message.is_released:
            event = CONF_LONG_RELEASE
        elif message.is_slowly_turned_cw:
            event = EVENT_ROTATE_CW_SLOW
        elif message.is_quickly_turned_cw:
            event = EVENT_ROTATE_CW_FAST
        elif message.is_slowly_turned_ccw:
            event = EVENT_ROTATE_CCW_SLOW
        elif message.is_quickly_turned_ccw:
            event = EVENT_ROTATE_CCW_FAST
        else:
            LOGGER.debug("%s Ignoring unknown CEN+ frame `%s`", self.log_id, message)
            return
        self.hass.bus.async_fire(
            "myhome_cenplus_event",
            {"object": int(message.object), "pushbutton": int(message.push_button), "event": event},
        )
        LOGGER.debug("%s %s", self.log_id, message.human_readable_log)

    def _fire_cen_event(self, message: OWNCENEvent) -> None:
        if message.is_pressed:
            event = CONF_SHORT_PRESS
        elif message.is_released_after_short_press:
            event = CONF_SHORT_RELEASE
        elif message.is_held:
            event = CONF_LONG_PRESS
        elif message.is_released_after_long_press:
            event = CONF_LONG_RELEASE
        else:
            LOGGER.debug("%s Ignoring unknown CEN frame `%s`", self.log_id, message)
            return
        self.hass.bus.async_fire(
            "myhome_cen_event",
            {"object": int(message.object), "pushbutton": int(message.push_button), "event": event},
        )
        LOGGER.debug("%s %s", self.log_id, message.human_readable_log)

    # ------------------------------------------------------------------ energy throttle
    def _energy_settings_for(self, entity_key: str) -> _EnergySettings:
        """Per-sensor throttle settings: sensor dict (canonical keys, already merged
        with ``sensor_defaults`` by validate.py) -> gateway ``sensor_defaults`` -> code defaults."""
        cached = self._energy_settings_cache.get(entity_key)
        if cached is not None:
            return cached
        defaults = self._gw_cfg().get(CONF_SENSOR_DEFAULTS)
        defaults = defaults if isinstance(defaults, dict) else {}
        sensor_cfg = self._platform_cfg(SENSOR).get(entity_key)
        sensor_cfg = sensor_cfg if isinstance(sensor_cfg, dict) else {}

        def _value(key: str, fallback: float, cast: type) -> Any:
            raw = sensor_cfg.get(key, defaults.get(key, fallback))
            try:
                return cast(raw)
            except (TypeError, ValueError):
                return cast(fallback)

        settings = _EnergySettings(
            min_delta_w=_value(CONF_MIN_DELTA_W, DEFAULT_MIN_DELTA_W, int),
            min_interval_sec=_value(CONF_MIN_INTERVAL_SEC, DEFAULT_MIN_INTERVAL_SEC, float),
            suppress_log_interval_sec=_value(CONF_SUPPRESS_LOG_INTERVAL_SEC, DEFAULT_SUPPRESS_LOG_INTERVAL_SEC, float),
            info_log_interval_sec=_value(CONF_INFO_LOG_INTERVAL_SEC, DEFAULT_INFO_LOG_INTERVAL_SEC, float),
        )
        # Cache only once the config is actually there (the first frame can arrive
        # before hass.data is populated in unit tests).
        if sensor_cfg:
            self._energy_settings_cache[entity_key] = settings
        return settings

    def _should_process_active_power(self, entity_key: str, watts: int) -> bool:
        """Contract B: process if |dW| >= min_delta_w OR elapsed >= min_interval_sec.

        Either threshold at 0 accepts everything; the first sample always passes.
        """
        settings = self._energy_settings_for(entity_key)
        now = self._now()
        last_w = self._last_energy_watts.get(entity_key)
        last_ts = self._last_energy_ts.get(entity_key)
        accept = (
            last_w is None
            or last_ts is None
            or abs(watts - last_w) >= settings.min_delta_w
            or now - last_ts >= settings.min_interval_sec
        )
        if accept:
            self._last_energy_watts[entity_key] = watts
            self._last_energy_ts[entity_key] = now
        return accept

    def _sensor_display_name(self, entity_key: str) -> str:
        cfg = self._platform_cfg(SENSOR).get(entity_key)
        name = cfg.get(CONF_NAME) if isinstance(cfg, dict) else None
        return str(name).strip() if isinstance(name, str) and name.strip() else entity_key

    def _log_energy_suppression(self, entity_key: str, watts: int, settings: _EnergySettings) -> None:
        """Rate-limited DEBUG summary of suppressed instant-power frames."""
        now = self._now()
        self._energy_suppress_count[entity_key] = self._energy_suppress_count.get(entity_key, 0) + 1
        last = self._last_energy_suppress_log_ts.get(entity_key)
        interval = settings.suppress_log_interval_sec
        if last is not None and interval > 0 and now - last < interval:
            return
        count = self._energy_suppress_count.pop(entity_key, 0)
        self._last_energy_suppress_log_ts[entity_key] = now
        LOGGER.debug(
            "%s Suppressed %d instant power frame(s) for %s (%s) in the last ~%.0f s (latest %s W, min_delta_w=%s, min_interval_sec=%s)",
            self.log_id,
            count,
            self._sensor_display_name(entity_key),
            entity_key,
            interval,
            watts,
            settings.min_delta_w,
            settings.min_interval_sec,
        )

    def _maybe_log_energy_update_info(self, entity_key: str, watts: int, settings: _EnergySettings) -> None:
        """Optional INFO heartbeat for accepted instant power samples (``info_log_interval_sec`` > 0)."""
        interval = settings.info_log_interval_sec
        if interval <= 0:
            return
        now = self._now()
        last = self._last_energy_info_log_ts.get(entity_key)
        if last is not None and now - last < interval:
            return
        self._last_energy_info_log_ts[entity_key] = now
        LOGGER.info("%s Power sensor %s: %s W", self.log_id, self._sensor_display_name(entity_key), watts)

    def _handle_energy_event(self, message: OWNEnergyEvent) -> None:
        """Throttle ONLY instant active power (dimension 113); every other WHO=18
        frame (totaliser, daily, monthly...) is dispatched unfiltered (gw-06)."""
        if message.message_type == MESSAGE_TYPE_ACTIVE_POWER:
            watts = int(message.active_power)
            settings = self._energy_settings_for(message.entity)
            if not self._should_process_active_power(message.entity, watts):
                self._log_energy_suppression(message.entity, watts, settings)
                return
            self._maybe_log_energy_update_info(message.entity, watts, settings)
        self._dispatch_to_entities(message)

    # ------------------------------------------------------------------ shutdown
    async def close_listener(self) -> bool:
        """Stop the loops, close both sessions, drop the queue, publish offline.

        Idempotent: ``__init__.py`` calls it explicitly on unload and again through
        ``entry.async_on_unload``.  Safe to call from inside one of the loop tasks.
        """
        first_call = not self._closed
        self._closed = True
        self._stop_event_listener = True
        self._stop_command_workers = True
        if first_call:
            LOGGER.info("%s Closing gateway sessions", self.log_id)

        current = asyncio.current_task()
        tasks = [
            task
            for task in (self.listening_worker, *self.sending_workers)
            if task is not None and task is not current and not task.done()
        ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.listening_worker = None
        self.sending_workers = []

        # The loops close their own sessions in ``finally``; close anything left over
        # (a loop that was never started or is the current task).
        sessions = [self._event_session, *self._command_sessions.values()]
        self._event_session = None
        self._command_sessions = {}
        for session in sessions:
            await self._close_session(session)

        dropped = self._drain_queue()
        if dropped:
            LOGGER.warning(
                "%s %d queued command(s) discarded on shutdown: %s",
                self.log_id,
                len(dropped),
                ", ".join(str(item.message) for item in dropped[:10]) + (" ..." if len(dropped) > 10 else ""),
            )
        self._set_connected(False)
        return True
