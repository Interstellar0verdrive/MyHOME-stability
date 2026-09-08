"""MyHOME gateway handler: connection, command and event layer (Contract B).

One :class:`MyHOMEGatewayHandler` per gateway owns

- the EVENT (monitor) session: :meth:`listening_loop` keeps it alive with TCP
  keepalive plus an idle watchdog (no frame for ``idle_timeout`` -> probe through
  the command session -> reconnect only if the command session did not answer
  either, because a gateway that ACKs is alive even when it does not mirror its
  replies onto the monitor), verifies every ``connect`` result, reconnects with
  exponential backoff (1..60 s) and never hot loops; a password rejection sets
  ``auth_failed``, stops the loops and starts the reauth flow;
- the COMMAND session(s): :meth:`sending_loop` drains a bounded queue with a TTL,
  sends each command under a timeout, retries ONCE in place with a fresh session and
  then drops the command with a rate-limited WARNING - never "silently done".  Stop
  frames overtake the rest of the queue, and every command can report when it really
  reached the bus (or that it never did): see :class:`_QueuedCommand` and
  :class:`_CommandQueue` (0.4.3);
- the dispatcher: every reply frame (monitor or command session) goes through
  :meth:`_dispatch_message`; every call into an entity is isolated with
  ``try``/``except`` so an entity bug never tears a session down;
- availability: ``is_connected`` is True only while the event session is verified
  alive and every transition is published on ``SIGNAL_GATEWAY_CONNECTION``;
- observability (0.3.0): a :class:`GatewayStats` snapshot (``handler.stats``)
  published on ``SIGNAL_GATEWAY_STATS`` and a ring buffer of the last 50 frames
  (``handler.recent_frames``) for the diagnostics download.

The public surface consumed by ``__init__.py``, ``diagnostics.py`` and the
platforms (``mac``, ``unique_id``, ``name``, ``is_connected``, ``device_id``,
``auth_failed``, ``stats``, ``recent_frames``, ``session_parameters``, ``send``,
``send_status_request``, ``listening_loop``, ``sending_loop``, ``close_listener``,
``test``, the discovery hooks) is unchanged in shape.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.components.button import DOMAIN as BUTTON
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.event import DOMAIN as EVENT
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
from homeassistant.util import dt as dt_util
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

from .const import (
    ATTR_MAC,
    CONF_BUS_INTERFACE,
    CONF_COMMAND_TIMEOUT_SEC,
    CONF_DEVICE_TYPE,
    CONF_FIRMWARE,
    CONF_IDLE_WATCHDOG_SEC,
    CONF_INFO_LOG_INTERVAL_SEC,
    CONF_LONG_PRESS,
    CONF_LONG_RELEASE,
    CONF_MANUFACTURER,
    CONF_MANUFACTURER_URL,
    CONF_MIN_DELTA_W,
    CONF_MIN_INTERVAL_SEC,
    CONF_PLATFORMS,
    CONF_PROBE_WINDOW_SEC,
    CONF_QUEUE_TTL_SEC,
    CONF_SENSOR_DEFAULTS,
    CONF_SHORT_PRESS,
    CONF_SHORT_RELEASE,
    CONF_SSDP_LOCATION,
    CONF_SSDP_ST,
    CONF_SUPPRESS_LOG_INTERVAL_SEC,
    CONF_UDN,
    CONF_WHERE,
    CONF_ZONE,
    DEFAULT_COMMAND_TIMEOUT_SEC,
    DEFAULT_IDLE_WATCHDOG_SEC,
    DEFAULT_PROBE_WINDOW_SEC,
    DEFAULT_QUEUE_TTL_SEC,
    DOMAIN,
    EVENT_CEN,
    EVENT_CENPLUS,
    EVENT_LIGHT_PUSHBUTTON,
    EVENT_LONG_PRESS_REPEAT,
    EVENT_ROTATE_CCW_FAST,
    EVENT_ROTATE_CCW_SLOW,
    EVENT_ROTATE_CW_FAST,
    EVENT_ROTATE_CW_SLOW,
    LIGHT_PUSHBUTTON_EVENTS,
    LOGGER,
    PROTOCOL_CEN,
    PROTOCOL_CEN_PLUS,
    SIGNAL_GATEWAY_CONNECTION,
    SIGNAL_GATEWAY_STATS,
    bus_full_where,
    is_bus_scope_address,
    scenario_control_key,
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
COMMAND_TIMEOUT_SEC = float(DEFAULT_COMMAND_TIMEOUT_SEC)  # write + wait for ACK/NACK
CONNECT_TIMEOUT_SEC = 10.0  # TCP connect + negotiation, one attempt
# `_deliver` gives every command one fresh-session retry and then drops it. Named so
# that the worst case one command may take (`command_budget`) is derived from the
# retry loop itself instead of being written down twice.
COMMAND_ATTEMPTS = 2
COMMAND_QUEUE_MAXSIZE = 200
# A WHO 2 stop (`*2*0*<where>##`) overtakes everything else in the queue (0.4.3).
# A late stop lengthens a shutter's run exactly as a late start shortens it, and a
# scene that moves twelve covers queues twelve stops as well: they must not wait
# behind the movement and status frames of the covers that come after them.
STOP_FRAME_PREFIX = "*2*0*"
COMMAND_TTL_SEC = float(DEFAULT_QUEUE_TTL_SEC)  # commands older than this are dropped when dequeued
COMMAND_SESSION_IDLE_SEC = 60.0  # close an unused command session (gateway session limit)
# Event path.
IDLE_TIMEOUT_SEC = float(DEFAULT_IDLE_WATCHDOG_SEC)  # no monitor frame for this long -> probe
PROBE_WINDOW_SEC = float(DEFAULT_PROBE_WINDOW_SEC)  # probe sent, still nothing on the monitor -> reconnect
READ_POLL_SEC = 30.0  # wake-up cadence of the listening loop (watchdog granularity)
INITIAL_BACKOFF_SEC = 1.0
MAX_BACKOFF_SEC = 60.0
# Logging.
LOG_RATE_LIMIT_SEC = 60.0
RECONNECT_LOG_RATE_LIMIT_SEC = 300.0

# Observability (0.3.0).
STATS_PUBLISH_INTERVAL_SEC = 1.0  # SIGNAL_GATEWAY_STATS is throttled to <= 1/s
RECENT_FRAMES_MAXLEN = 50  # ring buffer shown in the diagnostics download

# Guardrails for the user-facing options: (minimum, maximum) in seconds.  A value
# outside the range is clamped (WARNING) and a non-numeric one falls back to the
# default, so a hand-edited entry can never disable the watchdog or the TTL.
IDLE_WATCHDOG_RANGE = (30.0, 3600.0)
PROBE_WINDOW_RANGE = (5.0, 600.0)
COMMAND_TIMEOUT_RANGE = (2.0, 60.0)
QUEUE_TTL_RANGE = (5.0, 3600.0)

# ``GatewayStats.session_state`` values (event session).
SESSION_STATE_DISCONNECTED = "disconnected"
SESSION_STATE_CONNECTING = "connecting"
SESSION_STATE_CONNECTED = "connected"
SESSION_STATE_AUTH_FAILED = "auth_failed"

# ``FrameRecord.direction`` values.
FRAME_MONITOR = "monitor"  # pushed by the gateway on the event session
FRAME_REPLY = "reply"  # read on a command session before the ACK/NACK
FRAME_COMMAND = "command"  # written by us on a command session

# Energy throttle code defaults (validate.py normally supplies every key).
DEFAULT_MIN_DELTA_W = 5
DEFAULT_MIN_INTERVAL_SEC = 1.0
DEFAULT_SUPPRESS_LOG_INTERVAL_SEC = 60.0
DEFAULT_INFO_LOG_INTERVAL_SEC = 0.0  # 0 = the INFO heartbeat is off (chatter stays at DEBUG)

_TRANSPORT_ERRORS = (SessionError, OSError, EOFError, TimeoutError)
_ENTITY_EVENT_TYPES = (OWNLightingEvent, OWNAutomationEvent, OWNDryContactEvent, OWNAuxEvent, OWNHeatingEvent)
# *1*1000#WHAT[#...]*WHERE## — WHO 1 command translation (physical pushbutton echo).
_LIGHT_TRANSLATION_RE = re.compile(r"^\*1\*1000#(?P<what>\d+)(?:#[^*]*)?\*(?P<where>[^*]+)##$")


@dataclass(slots=True, frozen=True)
class GatewayStats:
    """Immutable health snapshot of one gateway handler (0.3.0 contract).

    ``handler.stats`` always holds the latest one; the same object is published on
    ``SIGNAL_GATEWAY_STATS.format(mac=...)`` (throttled to at most once per second,
    immediately on connect / disconnect / auth failure / dropped command) and is
    consumed by the gateway diagnostic entities and by ``diagnostics.py``.

    ``frames_rx`` / ``last_frame_at`` count every frame *received* from the gateway
    (monitor frames and command-session replies alike): both prove the bus is alive.
    ``commands_sent`` counts the commands the gateway answered (ACK or NACK);
    ``commands_dropped`` counts the ones that never made it (queue full or closed,
    TTL expired, two failed attempts, a rejected password, an unexpected error in
    the sending loop, discarded on shutdown).
    """

    connected: bool = False
    last_frame_at: datetime | None = None
    frames_rx: int = 0
    reconnects: int = 0
    commands_sent: int = 0
    commands_dropped: int = 0
    queue_length: int = 0
    session_state: str = SESSION_STATE_DISCONNECTED


@dataclass(slots=True, frozen=True)
class FrameRecord:
    """One entry of the ``recent_frames`` ring buffer (diagnostics only)."""

    direction: str  # FRAME_MONITOR | FRAME_REPLY | FRAME_COMMAND
    frame: str
    at: datetime  # UTC


@dataclass(slots=True)
class _QueuedCommand:
    """One frame waiting for the sending worker, and how to report its fate.

    ``send()`` only *queues*: the frame reaches the bus when a worker writes it,
    which on a busy queue is a tenth of a second per frame later (0.4.3). A caller
    that times something against the bus - a cover estimating where its shutter is -
    passes ``on_delivered`` / ``on_dropped`` and gets told which happened and when.

    Exactly one of the two runs, exactly once: ``on_delivered`` with the monotonic
    timestamp taken immediately *before* the write the gateway answered (ACK and NACK
    both mean "the gateway took the frame"), or ``on_dropped`` when the frame never
    reached the bus at all. Both run on the event loop, and an exception in one is
    logged and swallowed: a caller's bug must never take a sending worker down.

    A NACK counts as delivered on purpose, and the consequence is worth naming: a
    cover re-bases its motor clock on a frame the gateway *refused*, so it times a
    run that never started. Telling the two apart would need a third callback, and
    the alternative is worse - 0.4.2 started the same estimate at the enqueue, which
    is the same wrongness a fraction of a second earlier. The refusal is logged as a
    WARNING by ``_on_command_result``, which is where a user finds out.
    """

    message: OWNCommand
    is_status_request: bool
    enqueued_at: float
    frame: str = field(default="")
    on_delivered: Callable[[float], None] | None = None
    on_dropped: Callable[[], None] | None = None
    # Derived in `__post_init__`: stop frames jump the queue (`_CommandQueue`).
    is_stop: bool = field(default=False)
    settled: bool = field(default=False)

    def __post_init__(self) -> None:
        if not self.frame:
            self.frame = str(self.message)
        self.is_stop = self.frame.startswith(STOP_FRAME_PREFIX)

    def mark_delivered(self, at: float) -> None:
        """The gateway answered the write that started at monotonic ``at``."""
        self._settle(self.on_delivered, at)

    def mark_dropped(self) -> None:
        """The frame never reached the bus (a no-op once the command has settled)."""
        self._settle(self.on_dropped)

    def _settle(self, callback: Callable[..., None] | None, *args: Any) -> None:
        if self.settled:
            return
        # Set *before* the call: a callback that raises has still settled the
        # command, so the `finally` net in `sending_loop` cannot call the other one.
        self.settled = True
        if callback is None:
            return
        try:
            callback(*args)
        except Exception:  # noqa: BLE001 - a caller's bug must not kill the worker
            LOGGER.exception("Error in the delivery callback of `%s`", self.frame)


class _CommandQueue(asyncio.Queue):
    """The command queue: FIFO, except that stop frames overtake *other* devices (0.4.3).

    Two deques behind one ``asyncio.Queue``, so the bound (``COMMAND_QUEUE_MAXSIZE``),
    the waiters and ``task_done`` / ``join`` are the standard ones and the total is
    still what ``queue_length`` reports. Ordering *among* stops and *among* everything
    else stays FIFO.

    One frame never overtakes another addressed to the **same WHERE**: a stop queued
    while that cover's own direction frame is still waiting is appended to the
    ordinary deque instead, behind it. Otherwise the actuator would be told to stop
    while it stands still and *then* told to move - and nothing would ever stop it
    again, so the shutter would run to its end stop. The point of the priority is a
    stop that is late because *twelve other covers* are ahead of it, and that is
    exactly what is left.
    """

    _queue: deque[_QueuedCommand]
    _stops: deque[_QueuedCommand]

    def _init(self, maxsize: int) -> None:
        self._queue = deque()
        self._stops = deque()

    def _get(self) -> _QueuedCommand:
        return (self._stops or self._queue).popleft()

    def _put(self, item: _QueuedCommand) -> None:
        if getattr(item, "is_stop", False) and not self._addresses_something_queued(item):
            self._stops.append(item)
            return
        self._queue.append(item)

    def _addresses_something_queued(self, item: _QueuedCommand) -> bool:
        """True when an ordinary frame for the same WHERE is already waiting.

        Only the ordinary deque is searched: everything in ``_stops`` is written
        before it anyway, so a stop that follows another stop is already in order.
        """
        where = getattr(item.message, "where", None)
        if where is None:  # pragma: no cover - every WHO 2 frame carries a WHERE
            return True
        return any(getattr(other.message, "where", None) == where for other in self._queue)

    def qsize(self) -> int:
        return len(self._queue) + len(self._stops)

    def empty(self) -> bool:
        return not self._queue and not self._stops

    def pending(self) -> tuple[_QueuedCommand, ...]:
        """Everything still waiting, in the order it will be delivered."""
        return (*self._stops, *self._queue)


@dataclass(slots=True, frozen=True)
class _EnergySettings:
    min_delta_w: int
    min_interval_sec: float
    suppress_log_interval_sec: float
    info_log_interval_sec: float


class _LogThrottle:
    """Per-key rate limiter for repeated log lines (counts what it suppressed).

    ``MAX_KEYS`` bounds the map: some keys derive from bus addresses, so an
    unbounded key space would be an unbounded dict. When the cap is reached the
    quarter that was *logged* longest ago is dropped -- those keys log one line
    early next time and lose the "suppressed N lines" count they had pending.
    Note that the timestamp is the last line **emitted**, so a key that is being
    suppressed continuously looks stale and goes first; both effects only ever
    cost an extra log line, which is why the cheap rule is good enough.
    """

    MAX_KEYS = 256

    def __init__(self) -> None:
        self._last: dict[str, float] = {}
        self._suppressed: dict[str, int] = {}

    def check(self, key: str, interval: float, now: float) -> tuple[bool, int]:
        """Return (log it?, number of suppressed lines since the last emitted one)."""
        last = self._last.get(key)
        if last is not None and interval > 0 and now - last < interval:
            self._suppressed[key] = self._suppressed.get(key, 0) + 1
            return False, 0
        if last is None and len(self._last) >= self.MAX_KEYS:
            for stale in sorted(self._last, key=self._last.get)[: self.MAX_KEYS // 4]:
                self.reset(stale)
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


# ``<who>-<where>#4#<interface>`` with the interface written as 1 or 2 digits.
_INTERFACE_KEY_RE = re.compile(r"^(?P<base>.+)#4#(?P<interface>\d{1,2})$")


def _entity_key_candidates(entity_key: str) -> tuple[str, ...]:
    """The key itself, then its bus-interface variants, in lookup order.

    Configuration keys keep the F422 interface zero padded (``1-11#4#03``) because
    that string is also the tail of every entity ``unique_id`` and renaming it would
    orphan the history of every user behind a local bus (see
    ``validate.device_key``).  OWNd 0.7.49 reports the interface exactly as the bus
    wrote it, which is normally unpadded (``1-11#4#3``).  Trying the int-normalised
    variants makes both spellings resolve, whichever side they come from.
    """
    match = _INTERFACE_KEY_RE.match(entity_key)
    if match is None:
        return (entity_key,)
    base, interface = match.group("base"), int(match.group("interface"))
    # dict.fromkeys keeps the order and drops the duplicate when the key is already
    # in one of the two canonical spellings.
    return tuple(dict.fromkeys((entity_key, f"{base}#4#{interface:02d}", f"{base}#4#{interface}")))


def _message_entity_key(message: OWNMessage) -> str:
    """Configuration key of the entity a frame belongs to.

    Identical to ``message.entity`` except for the central heating unit: OWNd
    rewrites a ``zone 0`` frame to the zone found in the first WHERE parameter
    (``OWNHeatingEvent.__init__``), so ``*#4*0#1*20*1##`` — the central unit's
    actuator 1 — reports ``4-1`` and would drive zone 1's climate entity with the
    central unit's state.  WHERE ``0`` means the central unit, whose key is ``4-#0``
    (guard contributed by Jacopo Jannone via michnovka; OWNd stays untouched, its
    private ``_zone`` is never mutated).
    """
    if isinstance(message, OWNHeatingEvent) and str(message.where) == "0":
        return f"{message.who}-#0"
    return str(message.entity)


class MyHOMEGatewayHandler:
    """Manages a single MyHOME Gateway.

    Tunables (read once at handler creation from ``config_entry.options``; the
    options flow reloads the entry, so a change always rebuilds the handler):

    ===================== ================================ ======= ==============
    option                attribute                        default range (s)
    ===================== ================================ ======= ==============
    ``idle_watchdog_sec``  ``idle_timeout``                 300     30 .. 3600
    ``probe_window_sec``   ``probe_window``                 30      5 .. 600
    ``command_timeout_sec`` ``command_timeout``             10      2 .. 60
    ``queue_ttl_sec``      ``command_ttl``                  60      5 .. 3600
    ===================== ================================ ======= ==============

    - ``idle_watchdog_sec``: silence on the monitor session for this long triggers
      a harmless status request through the command session;
    - ``probe_window_sec``: if nothing arrives on the monitor and no status request
      is acknowledged on the command session within this window, the event session
      is closed and reconnected with backoff; any ACKed status request re-arms the
      watchdog, it need not be the probe;
    - ``command_timeout_sec``: how long one command may take to be written and
      acknowledged (NACK included) before the session is considered broken;
    - ``queue_ttl_sec``: commands still queued after this long are dropped instead
      of being replayed against a gateway that has moved on.

    A non-numeric value falls back to the default and an out-of-range one is
    clamped, both with a WARNING: the watchdog can never be switched off by a
    hand-edited entry.  The remaining knobs (``connect_timeout``,
    ``command_session_idle``, ``read_poll_interval``, ``initial_backoff``,
    ``max_backoff``, ``stats_publish_interval``) stay code constants and are only
    shrunk by the tests.
    """

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
        self.send_buffer: asyncio.Queue[_QueuedCommand] = _CommandQueue(maxsize=COMMAND_QUEUE_MAXSIZE)

        # Loop control.
        self._closed = False
        self._stop_event_listener = False
        self._stop_command_workers = False
        self._event_session: OWNEventChannel | None = None
        self._command_sessions: dict[int, OWNCommandChannel] = {}
        self._last_rx: float = 0.0
        self._probe_sent_at: float | None = None
        # When the command session last ACKed *any* status request (not just the
        # watchdog probe: a sensor re-arming or a heating follow-up sets it too).
        # `_check_idle` reads it as "the gateway is reachable on the command port",
        # which is weaker than "our probe was answered".
        self._command_ack_at: float | None = None

        # Timing knobs: the four user-facing ones come from the entry options,
        # the rest are code constants (instance attributes so tests can shrink them).
        options = self._entry_options()
        self.command_timeout = self._option(
            options, CONF_COMMAND_TIMEOUT_SEC, COMMAND_TIMEOUT_SEC, COMMAND_TIMEOUT_RANGE
        )
        self.command_ttl = self._option(options, CONF_QUEUE_TTL_SEC, COMMAND_TTL_SEC, QUEUE_TTL_RANGE)
        self.idle_timeout = self._option(options, CONF_IDLE_WATCHDOG_SEC, IDLE_TIMEOUT_SEC, IDLE_WATCHDOG_RANGE)
        self.probe_window = self._option(options, CONF_PROBE_WINDOW_SEC, PROBE_WINDOW_SEC, PROBE_WINDOW_RANGE)
        self.connect_timeout = CONNECT_TIMEOUT_SEC
        self.command_session_idle = COMMAND_SESSION_IDLE_SEC
        self.read_poll_interval = READ_POLL_SEC
        self.initial_backoff = INITIAL_BACKOFF_SEC
        self.max_backoff = MAX_BACKOFF_SEC
        self.stats_publish_interval = STATS_PUBLISH_INTERVAL_SEC

        # Observability (0.3.0): counters + the published snapshot + the ring buffer.
        self.recent_frames: deque[FrameRecord] = deque(maxlen=RECENT_FRAMES_MAXLEN)
        self._frames_rx = 0
        self._last_frame_at: datetime | None = None
        self._reconnects = 0
        self._commands_sent = 0
        self._commands_dropped = 0
        self._session_state = SESSION_STATE_DISCONNECTED
        self._event_sessions_opened = 0
        self._last_stats_publish: float | None = None
        self._stats_timer: asyncio.TimerHandle | None = None
        self.stats: GatewayStats = self._snapshot()

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

    @property
    def command_budget(self) -> float:
        """Longest one command may legitimately take, from dequeue to answer, in seconds.

        `_deliver` may have to open a command session before it can write, and it
        gives the whole thing one retry with a new session before dropping the
        command. So the bound is `COMMAND_ATTEMPTS` times a connect plus a write-and-
        ACK, i.e. 40 s with the default options.

        Note what that session is: `sending_loop` holds **one per sending worker**
        (one worker by default), shared by every entity, service call, discovery pass
        and watchdog probe of this gateway, and it is closed only when the whole
        `send_buffer` has stayed empty for `command_session_idle`. So "this entity has
        been quiet for a minute" says nothing at all about whether a connection has to
        be re-opened - only "nothing whatsoever has been sent for a minute" does, which
        is likely in a quiet house but never certain. The bound above is the worst
        case, and it is sized on the worst case on purpose.

        It is *not* the whole wait a caller sees: commands queued ahead of this one
        add their own time (bounded only by `command_ttl`). It is what a single
        command may cost once it reaches the front of the queue, and it is what
        cover.py sizes its status grace on - read live, so it follows the user's
        `command_timeout_sec` option.
        """
        return COMMAND_ATTEMPTS * (float(self.connect_timeout) + float(self.command_timeout))

    @property
    def session_parameters(self) -> dict[str, float]:
        """The timing knobs actually in effect (diagnostics download, G1-A)."""
        return {
            CONF_IDLE_WATCHDOG_SEC: self.idle_timeout,
            CONF_PROBE_WINDOW_SEC: self.probe_window,
            CONF_COMMAND_TIMEOUT_SEC: self.command_timeout,
            CONF_QUEUE_TTL_SEC: self.command_ttl,
            "connect_timeout_sec": self.connect_timeout,
            "command_session_idle_sec": self.command_session_idle,
            "read_poll_interval_sec": self.read_poll_interval,
            "queue_maxsize": float(self.send_buffer.maxsize),
        }

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

    # ------------------------------------------------------------------ options
    def _entry_options(self) -> Mapping[str, Any]:
        """``config_entry.options`` as a mapping (empty for a mock or a bare entry)."""
        options = getattr(self.config_entry, "options", None)
        return options if isinstance(options, Mapping) else {}

    def _option(self, options: Mapping[str, Any], key: str, default: float, bounds: tuple[float, float]) -> float:
        """One numeric option, defaulted when unusable and clamped to ``bounds``."""
        raw = options.get(key)
        if raw is None:
            return float(default)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            LOGGER.warning("%s Option `%s` is not a number (%r): using %s s", self.log_id, key, raw, default)
            return float(default)
        minimum, maximum = bounds
        clamped = min(max(value, minimum), maximum)
        if clamped != value:
            LOGGER.warning(
                "%s Option `%s` = %s s is out of range (%s..%s): using %s s",
                self.log_id,
                key,
                value,
                minimum,
                maximum,
                clamped,
            )
        return clamped

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

    def _set_connected(self, connected: bool, *, session_state: str | None = None) -> None:
        """Update ``is_connected`` and publish every transition (Contract B, gw-10)."""
        if session_state is not None:
            state = session_state
        elif connected:
            state = SESSION_STATE_CONNECTED
        else:
            # A rejected password outlives the loop teardown that follows it: the
            # entry stays in reauth until the user fixes it (never "disconnected").
            state = SESSION_STATE_AUTH_FAILED if self.auth_failed else SESSION_STATE_DISCONNECTED
        changed = connected != self.is_connected
        state_changed = state != self._session_state
        self.is_connected = connected
        self._session_state = state
        if changed:
            LOGGER.info("%s Gateway is %s", self.log_id, "connected" if connected else "disconnected")
            try:
                async_dispatcher_send(self.hass, SIGNAL_GATEWAY_CONNECTION.format(mac=self.mac), connected)
            except Exception:  # noqa: BLE001 - never let a subscriber break the session loop
                LOGGER.exception("%s Error while publishing the connection state", self.log_id)
        # Connection lifecycle: the stats consumers must see it without waiting.
        self._refresh_stats(publish=changed or state_changed, immediate=True)

    def _set_session_state(self, state: str) -> None:
        """Move the event session to ``state`` (``is_connected`` untouched)."""
        if state == self._session_state:
            return
        self._session_state = state
        self._refresh_stats(publish=True, immediate=True)

    # ------------------------------------------------------------------ stats (0.3.0)
    def _snapshot(self) -> GatewayStats:
        return GatewayStats(
            connected=self.is_connected,
            last_frame_at=self._last_frame_at,
            frames_rx=self._frames_rx,
            reconnects=self._reconnects,
            commands_sent=self._commands_sent,
            commands_dropped=self._commands_dropped,
            queue_length=self.send_buffer.qsize(),
            session_state=self._session_state,
        )

    def _refresh_stats(self, *, publish: bool = False, immediate: bool = False) -> None:
        """Rebuild ``self.stats`` and optionally publish it on the stats signal."""
        self.stats = self._snapshot()
        if publish:
            self._publish_stats(immediate=immediate)

    def _publish_stats(self, *, immediate: bool = False) -> None:
        """Send the current snapshot, at most once per ``stats_publish_interval``.

        A suppressed publish is not lost: a timer flushes the newest snapshot when
        the window closes, so a consumer never waits more than the interval.
        """
        now = self._now()
        last = self._last_stats_publish
        if not immediate and last is not None and now - last < self.stats_publish_interval:
            self._schedule_stats_flush(self.stats_publish_interval - (now - last))
            return
        self._cancel_stats_flush()
        self._last_stats_publish = now
        try:
            async_dispatcher_send(self.hass, SIGNAL_GATEWAY_STATS.format(mac=self.mac), self.stats)
        except Exception:  # noqa: BLE001 - a diagnostic subscriber must not break a session loop
            LOGGER.exception("%s Error while publishing the gateway stats", self.log_id)

    def _schedule_stats_flush(self, delay: float) -> None:
        if self._stats_timer is not None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # pragma: no cover - only outside the event loop
            return
        self._stats_timer = loop.call_later(max(0.0, delay), self._flush_stats)

    def _flush_stats(self) -> None:
        self._stats_timer = None
        if self._closed:
            return
        self._refresh_stats(publish=True, immediate=True)

    def _cancel_stats_flush(self) -> None:
        timer, self._stats_timer = self._stats_timer, None
        if timer is not None:
            timer.cancel()

    def _record_frame(self, direction: str, frame: Any) -> None:
        """Append to the ring buffer; received frames also move the rx counters."""
        now = dt_util.utcnow()
        self.recent_frames.append(FrameRecord(direction, str(frame), now))
        if direction != FRAME_COMMAND:
            self._frames_rx += 1
            self._last_frame_at = now

    async def _close_session(self, session: OWNEventChannel | OWNCommandChannel | None) -> None:
        if session is None:
            return
        try:
            await session.close()
        except Exception:  # noqa: BLE001 - closing must never raise
            LOGGER.debug("%s Error while closing a session", self.log_id, exc_info=True)

    def _handle_auth_failure(self, err: AuthenticationError, session_type: str) -> None:
        """Password rejected at runtime: stop everything and ask for reauth (gw-05).

        The workers leave their loop on the flag below without draining, and the
        config entry stays loaded until the user has completed the reauth flow - so
        whatever is still queued is settled here (0.4.3). Every command reaches
        exactly one of its two callbacks, on this path like on every other.
        """
        self._stop_event_listener = True
        self._stop_command_workers = True
        self._discard_queued("after the gateway rejected the password")
        self._set_connected(False, session_state=SESSION_STATE_AUTH_FAILED)
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
    async def send(
        self,
        message: OWNCommand,
        *,
        on_delivered: Callable[[float], None] | None = None,
        on_dropped: Callable[[], None] | None = None,
    ) -> bool:
        """Queue a command; False (and a rate-limited WARNING) if it cannot be queued.

        The return value says only that the frame was *queued*. A caller that has to
        know when it actually reached the bus - covers time their motor runs on it -
        passes the two callbacks documented on :class:`_QueuedCommand`.
        """
        return self._enqueue(message, is_status_request=False, on_delivered=on_delivered, on_dropped=on_dropped)

    async def send_status_request(
        self,
        message: OWNCommand,
        *,
        on_delivered: Callable[[float], None] | None = None,
        on_dropped: Callable[[], None] | None = None,
    ) -> bool:
        """Queue a status request; same semantics as ``send``, plus coalescing.

        An identical status frame already waiting in the queue is *coalesced*: the
        request is reported as accepted without queueing a second copy.  Asking the
        same WHERE twice in a row can only produce the same answer, and several
        code paths (general/area lighting events, the idle probe, entities re-arming
        on the connection signal) legitimately race to ask for it.

        A caller that asked to be told what happened to *its* frame is never
        coalesced (0.4.3): the queued copy carries somebody else's callbacks, so
        merging the two would silently leave this one without either.
        """
        frame = str(message)
        if on_delivered is None and on_dropped is None and self._has_pending_status(frame):
            LOGGER.debug("%s Coalescing status request `%s`: an identical one is already queued", self.log_id, frame)
            return True
        return self._enqueue(message, is_status_request=True, on_delivered=on_delivered, on_dropped=on_dropped)

    def _has_pending_status(self, frame: str) -> bool:
        """True when an identical status request is still waiting in the queue.

        The queue is the single source of truth: a separate counter would go out
        of sync as soon as anything drained the queue outside ``sending_loop``.
        At most ``COMMAND_QUEUE_MAXSIZE`` string comparisons, only for status
        requests, so the command path is untouched.
        """
        return any(
            isinstance(item, _QueuedCommand) and item.is_status_request and item.frame == frame
            for item in self._pending_commands()
        )

    def _pending_commands(self) -> tuple[Any, ...]:
        """Everything still in the queue (a plain ``asyncio.Queue`` works too)."""
        pending = getattr(self.send_buffer, "pending", None)
        if callable(pending):
            return pending()
        return tuple(getattr(self.send_buffer, "_queue", ()))

    def _enqueue(
        self,
        message: OWNCommand,
        *,
        is_status_request: bool,
        on_delivered: Callable[[float], None] | None = None,
        on_dropped: Callable[[], None] | None = None,
    ) -> bool:
        item = _QueuedCommand(
            message, is_status_request, self._now(), on_delivered=on_delivered, on_dropped=on_dropped
        )
        if self._closed or self._stop_command_workers:
            self._log_limited(
                logging.WARNING,
                "queue-closed",
                "%s Cannot send `%s`: the gateway handler is closed",
                self.log_id,
                message,
            )
            item.mark_dropped()
            self._commands_dropped += 1
            self._refresh_stats(publish=True, immediate=True)
            return False
        try:
            self.send_buffer.put_nowait(item)
        except asyncio.QueueFull:
            self._log_limited(
                logging.WARNING,
                "queue-full",
                "%s Command queue full (%d pending): dropping `%s` - is the gateway reachable?",
                self.log_id,
                self.send_buffer.maxsize,
                message,
            )
            item.mark_dropped()
            self._commands_dropped += 1
            self._refresh_stats(publish=True, immediate=True)
            return False
        LOGGER.debug("%s Queued `%s`", self.log_id, message)
        # The queue length alone is not worth a dispatch: the snapshot stays fresh
        # and is published by the next frame / command / lifecycle event.
        self._refresh_stats()
        return True

    def _discard_queued(self, reason: str) -> None:
        """Drop everything still queued and tell each caller so.

        The one place that settles a whole queue: the workers are stopping (a
        shutdown, a rejected password), so nothing behind the current frame will
        ever be written.
        """
        dropped = self._drain_queue()
        if not dropped:
            return
        for item in dropped:
            item.mark_dropped()
        self._commands_dropped += len(dropped)
        LOGGER.warning(
            "%s %d queued command(s) discarded %s: %s",
            self.log_id,
            len(dropped),
            reason,
            ", ".join(str(item.message) for item in dropped[:10]) + (" ..." if len(dropped) > 10 else ""),
        )

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
                        item.mark_dropped()
                        self._commands_dropped += 1
                        self._refresh_stats(publish=True, immediate=True)
                        continue

                    session, delivered = await self._deliver(session, worker_id, item)
                    if delivered:
                        backoff = self.initial_backoff
                    elif not self._stop_command_workers:
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, self.max_backoff)
                except Exception:  # noqa: BLE001 - a bug here must not kill the worker
                    # Same contract as the listening loop: the task survives, the
                    # command is dropped and counted, the worker backs off.
                    LOGGER.exception(
                        "%s Unexpected error while sending `%s`; dropping it and retrying in %.0f s",
                        self.log_id,
                        item.message,
                        backoff,
                    )
                    await self._close_session(session)
                    session = None
                    self._command_sessions.pop(worker_id, None)
                    item.mark_dropped()
                    self._commands_dropped += 1
                    self._refresh_stats(publish=True, immediate=True)
                    if not self._stop_command_workers:
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, self.max_backoff)
                finally:
                    # The single settle point: every branch above has already called
                    # `mark_delivered` or `mark_dropped`, and both are idempotent, so
                    # this only catches what nothing else could - a worker cancelled
                    # in the middle of a write (a reload, a shutdown), which is a
                    # command that never reached the bus like any other.
                    item.mark_dropped()
                    self.send_buffer.task_done()
        finally:
            await self._close_session(session)
            self._command_sessions.pop(worker_id, None)
            LOGGER.debug("%s Sending worker %s stopped", self.log_id, worker_id)

    async def _deliver(
        self, session: OWNCommandChannel | None, worker_id: int, item: _QueuedCommand
    ) -> tuple[OWNCommandChannel | None, bool]:
        """Send one command: `COMMAND_ATTEMPTS` tries in place, a fresh session each time.

        Returns the (possibly new) session and whether the gateway answered
        (ACK or NACK).  Never re-queues (gw-11): ordering is preserved and a
        stale command is never replayed later.
        """
        for attempt in range(1, COMMAND_ATTEMPTS + 1):
            try:
                if session is None:
                    new_session = OWNCommandChannel(self.gateway, LOGGER)
                    try:
                        await new_session.open(self.connect_timeout)
                    except BaseException:
                        # Includes CancelledError (close_listener during a reload): a
                        # channel we opened must never outlive this frame, gateways
                        # limit the number of concurrent sessions.
                        await self._close_session(new_session)
                        raise
                    session = new_session
                    self._command_sessions[worker_id] = session
                    LOGGER.debug("%s Command session established (worker %s)", self.log_id, worker_id)
                self._record_frame(FRAME_COMMAND, item.frame)
                # Taken immediately before the write, and handed to `on_delivered`
                # only if that write is answered: it is the closest thing we have to
                # the moment the frame hit the socket, which is the moment a motor
                # starts (0.4.3).
                written_at = self._now()
                result = await session.send_command(item.message, self.command_timeout)
            except AuthenticationError as err:
                await self._close_session(session)
                self._command_sessions.pop(worker_id, None)
                self._handle_auth_failure(err, "command")
                # The command is abandoned like any other undeliverable one.
                item.mark_dropped()
                self._commands_dropped += 1
                self._refresh_stats(publish=True, immediate=True)
                return None, False
            except _TRANSPORT_ERRORS as err:
                await self._close_session(session)
                session = None
                self._command_sessions.pop(worker_id, None)
                if attempt < COMMAND_ATTEMPTS:
                    LOGGER.debug(
                        "%s Sending `%s` failed (%s: %s); retrying with a fresh session",
                        self.log_id,
                        item.message,
                        type(err).__name__,
                        err,
                    )
                    continue
                self._log_limited(
                    logging.WARNING,
                    "cmd-dropped",
                    # The count comes from the constant, not from the prose: if the
                    # retry loop is ever allowed another attempt the message follows.
                    "%s Command `%s` dropped after %s attempts: %s: %s",
                    self.log_id,
                    item.message,
                    COMMAND_ATTEMPTS,
                    type(err).__name__,
                    err,
                )
                item.mark_dropped()
                self._commands_dropped += 1
                self._refresh_stats(publish=True, immediate=True)
                return None, False
            # Before the replies are dispatched: a cover must re-base its movement
            # clock on the write it just made before it is told what came back.
            item.mark_delivered(written_at)
            await self._on_command_result(item, result)
            return session, True
        return session, False  # pragma: no cover - loop always returns

    async def _on_command_result(self, item: _QueuedCommand, result: CommandResult) -> None:
        """Log the outcome and dispatch every reply frame like a monitor event (sc-01, gw-13)."""
        if result.acknowledged:
            LOGGER.debug("%s `%s` acknowledged (%d reply frame(s))", self.log_id, item.message, len(result.replies))
            if item.is_status_request:
                self._command_ack_at = self._now()
        else:
            self._log_limited(
                logging.WARNING,
                f"nack-{getattr(item.message, 'who', '?')}-{getattr(item.message, 'where', '?')}",
                "%s The gateway refused `%s` (NACK)",
                self.log_id,
                item.message,
            )
        self._commands_sent += 1
        for reply in result.replies:
            LOGGER.debug("%s Reply: `%s`", self.log_id, reply)
            self._record_frame(FRAME_REPLY, reply)
            await self._dispatch_message(reply, from_monitor=False)
        self._refresh_stats(publish=True)

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
                        self._set_session_state(SESSION_STATE_CONNECTING)
                        session = OWNEventChannel(self.gateway, LOGGER)
                        await session.open(self.connect_timeout)
                        self._event_session = session
                        self._last_rx = self._now()
                        self._probe_sent_at = None
                        if self._event_sessions_opened:
                            self._reconnects += 1
                        self._event_sessions_opened += 1
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
                    self._record_frame(FRAME_MONITOR, message)
                    self._refresh_stats(publish=True)
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
                    LOGGER.exception(
                        "%s Unexpected error in the listening loop; reconnecting in %.0f s", self.log_id, backoff
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self.max_backoff)
        finally:
            self._set_connected(False)
            await self._close_session(session)
            self._event_session = None
            LOGGER.info("%s Listening loop stopped", self.log_id)

    async def _check_idle(self) -> None:
        """Idle watchdog (gw-03): after ``idle_timeout`` without a monitor frame, probe
        through the command session; reconnect only if nothing arrived on the monitor
        **and** no status request was acknowledged on the command session within
        ``probe_window``.

        That second half is narrower than "the command session said nothing", and
        deliberately so: only a status request stamps ``_command_ack_at``
        (``_on_command_result``), because only a status request is a question we know
        the gateway had to answer. An ordinary command it ACKs, or a status request it
        NACKs, does not re-arm the watchdog, and the monitor session is rebuilt even
        though the command port is demonstrably alive - so the log must not claim
        neither session answered.

        Any status request the gateway ACKs on the command port proves it is alive -
        it need not be the probe itself - even when it does not mirror command replies
        onto the monitor, so in that case the monitor is left to TCP keepalive instead
        of being dropped and rebuilt (R7).
        """
        now = self._now()
        idle = now - self._last_rx
        if idle < self.idle_timeout:
            return
        if self._probe_sent_at is None:
            probe = self._probe_command()
            LOGGER.debug("%s No event for %.0f s: probing the bus with `%s`", self.log_id, idle, probe)
            if not await self.send_status_request(probe):
                # The command path refused it (queue full or closed): reconnecting
                # the monitor cannot help. Leave the watchdog unarmed, retry next poll.
                self._log_limited(
                    logging.WARNING,
                    "probe-not-queued",
                    "%s Idle watchdog could not queue its probe; the event session is left alone",
                    self.log_id,
                )
                return
            self._probe_sent_at = now
            return
        if now - self._probe_sent_at >= self.probe_window:
            if self._command_ack_at is not None and self._command_ack_at >= self._probe_sent_at:
                # A status request was ACKed after the probe went out, so the gateway
                # is reachable on the command port (it need not have been the probe
                # itself). This gateway simply does not mirror replies onto the monitor;
                # that socket is guarded by TCP keepalive, so re-arm instead of churning.
                self._log_limited(
                    logging.DEBUG,
                    "probe-not-mirrored",
                    "%s The command session answered a status request after the probe went out but nothing "
                    "was mirrored on the monitor; not reconnecting",
                    self.log_id,
                )
                self._last_rx = now
                self._probe_sent_at = None
                return
            # Each clause carries its own window on purpose: `idle` is the monitor's
            # silence, while the ACK is only looked for since the probe went out. One
            # trailing duration would read as if it qualified both, and send a user
            # hunting for a gateway that has been dead for `idle` seconds while it was
            # in fact answering their lights all along.
            # Both numbers are measurements, not options. This check only runs once
            # every `read_poll_interval` (30 s), so the time since the probe is the
            # **Probe window** option rounded up to the next poll - printing the
            # option itself would understate the silence we actually looked at, by a
            # factor of six with the smallest window the options allow.
            raise SessionError(
                f"nothing on the monitor for {idle:.0f} s and no status request acknowledged "
                f"on the command session in the last {now - self._probe_sent_at:.0f} s"
            )

    def _probe_command(self) -> OWNCommand:
        """A harmless status request whose reply shows up on the monitor session.

        Prefer a point-to-point actuator of the configuration; fall back to an
        energy meter, a thermo zone and finally the general lighting status.
        """
        for platform, factory in (
            (LIGHT, OWNLightingCommand.status),
            (SWITCH, OWNLightingCommand.status),
            (COVER, OWNAutomationCommand.status),
        ):
            for device in self._platform_cfg(platform).values():
                where = str(device.get(CONF_WHERE) or "")
                if where.isdigit() and len(where) in (2, 4) and where != "00":
                    return factory(bus_full_where(where, device.get(CONF_BUS_INTERFACE)))
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
                self._log_limited(
                    logging.WARNING, "discovery", "%s Discovery failed on `%s`", self.log_id, message, exc_info=True
                )

            if isinstance(message, OWNEnergyEvent):
                self._handle_energy_event(message)
                return

            if isinstance(message, _ENTITY_EVENT_TYPES):
                if message.is_translation:
                    if isinstance(message, OWNLightingEvent):
                        self._fire_light_pushbutton_event(message)
                    else:
                        LOGGER.debug("%s Ignoring translation message `%s`", self.log_id, message)
                    return
                if isinstance(message, OWNLightingEvent) and await self._handle_lighting_scope(message):
                    return
                if isinstance(message, OWNAutomationEvent) and self._handle_automation_scope(message):
                    return
                if isinstance(message, OWNLightingEvent) and message.brightness_preset:
                    await self._refresh_light(_message_entity_key(message))
                    return
                self._dispatch_to_entities(message)
                return

            if (
                isinstance(message, OWNHeatingCommand)
                and message.dimension is not None
                and int(message.dimension) == 14
            ):
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
        # Exactly the three branches below, in one predicate `discovery.py` shares:
        # what this method refuses to dispatch to an entity is what discovery must
        # refuse to announce as a device (const.is_bus_scope_address).
        if not is_bus_scope_address(message):
            return False
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
            # The WHERE as it came off the bus, not the decoded area: OWNd turns "00"
            # into 0 and "100" into 10, and *#1*10## is the actuator A=1 PL=0.
            await self.send_status_request(OWNLightingCommand.status(str(message.where)))
            return True
        if message.is_group:
            self.hass.bus.async_fire(
                "myhome_group_light_event", {"message": str(message), "group": message.group, "event": event}
            )
            return True
        return False

    def _handle_automation_scope(self, message: OWNAutomationEvent) -> bool:
        # Same shared predicate as _handle_lighting_scope, same reason.
        if not is_bus_scope_address(message):
            return False
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
        candidates = _entity_key_candidates(entity_key)
        platforms = self._gw_cfg().get(CONF_PLATFORMS) or {}
        for platform, devices in platforms.items():
            if platform == BUTTON or not isinstance(devices, dict):
                continue
            device = next((devices[key] for key in candidates if key in devices), None)
            if not isinstance(device, dict):
                continue
            entities = device.get(CONF_ENTITIES) or {}
            found.extend(obj for obj in list(entities.values()) if isinstance(obj, MyHOMEEntity))
        return found

    def _dispatch_to_entities(self, message: OWNMessage) -> None:
        entity_key = _message_entity_key(message)
        entities = self._entities_for(entity_key)
        if not entities:
            LOGGER.debug("%s No entity configured for `%s` (%s)", self.log_id, message, entity_key)
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
        lights = self._platform_cfg(LIGHT)
        device = next((lights[key] for key in _entity_key_candidates(entity_key) if key in lights), None)
        obj = (device.get(CONF_ENTITIES) or {}).get(LIGHT) if isinstance(device, dict) else None
        if not isinstance(obj, MyHOMEEntity):
            LOGGER.debug("%s Preset level for %s, which is not a configured light", self.log_id, entity_key)
            return
        try:
            await obj.async_update()
        except Exception:  # noqa: BLE001
            self._log_limited(
                logging.ERROR,
                f"entity-{obj.unique_id}",
                "%s %s failed to refresh",
                self.log_id,
                obj.unique_id,
                exc_info=True,
            )

    def _fire_light_pushbutton_event(self, message: OWNLightingEvent) -> None:
        """Republish a WHO 1 command translation as ``myhome_light_pushbutton_event``.

        ``*1*1000#WHAT*WHERE##`` is the gateway's echo of what a physical pushbutton
        sent; the actuator's own status frame follows and drives the entity. For a
        pushbutton in dimmer mode wired to a relay, the hold (WHAT 30 = up, 31 = down,
        one frame every ~0.5 s while held) reaches the bus and nothing else, so this
        is the only way to act on it. Payload: ``mac``, ``where``, ``what`` (int),
        ``event`` (``on``/``off``/``dim_up``/``dim_down``/``dim_to_<pct>``/``what_<n>``)
        and the raw ``message``. Never raises: an unparsable frame is logged and dropped.
        """
        match = _LIGHT_TRANSLATION_RE.match(str(message))
        if match is None:
            LOGGER.debug("%s Could not read the WHAT of light translation `%s`", self.log_id, message)
            return
        what = int(match.group("what"))
        where = match.group("where")
        event = LIGHT_PUSHBUTTON_EVENTS.get(what)
        if event is None:
            event = f"dim_to_{what * 10}" if 2 <= what <= 10 else f"what_{what}"
        self.hass.bus.async_fire(
            EVENT_LIGHT_PUSHBUTTON,
            {ATTR_MAC: self.mac, "where": where, "what": what, "event": event, "message": str(message)},
        )
        LOGGER.debug("%s Light pushbutton %s on WHERE %s (`%s`)", self.log_id, event, where, message)

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
        object_id = int(message.object)
        pushbutton = int(message.push_button)
        # ``mac`` (0.4.0) is additive: it disambiguates two gateways that can produce the
        # same object/pushbutton pair, and is what the device triggers match on.
        self.hass.bus.async_fire(
            EVENT_CENPLUS,
            {"object": object_id, "pushbutton": pushbutton, "event": event, ATTR_MAC: self.mac},
        )
        self._dispatch_scenario_event(PROTOCOL_CEN_PLUS, object_id, event, pushbutton)
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
        object_id = int(message.object)
        pushbutton = int(message.push_button)
        self.hass.bus.async_fire(
            EVENT_CEN,
            {"object": object_id, "pushbutton": pushbutton, "event": event, ATTR_MAC: self.mac},
        )
        self._dispatch_scenario_event(PROTOCOL_CEN, object_id, event, pushbutton)
        LOGGER.debug("%s %s", self.log_id, message.human_readable_log)

    def _dispatch_scenario_event(self, protocol: str, object_id: int, event: str, pushbutton: int) -> None:
        """Push a CEN/CEN+ press into the event entity of that control, if declared.

        Controls that are not in ``myhome.yaml`` own no entity and are silently skipped:
        the bus event above is their whole contract (0.3.x behaviour).
        """
        key = scenario_control_key(protocol, object_id)
        device = self._platform_cfg(EVENT).get(key)
        if not isinstance(device, dict):
            LOGGER.debug(
                "%s %s control %s is not declared in myhome.yaml (bus event only)", self.log_id, protocol, key
            )
            return
        obj = (device.get(CONF_ENTITIES) or {}).get(EVENT)
        if obj is None:
            return
        try:
            obj.handle_scenario_event(event, pushbutton)
        except Exception:  # noqa: BLE001 - an entity bug must not affect the session (gw-08)
            self._log_limited(
                logging.ERROR,
                f"entity-{key}",
                "%s %s failed to handle scenario event `%s` on button %s",
                self.log_id,
                key,
                event,
                pushbutton,
                exc_info=True,
            )

    # ------------------------------------------------------------------ energy throttle
    def _sensor_cfg(self, entity_key: str) -> dict[str, Any]:
        """Configuration of one sensor, whichever way its bus interface is spelled.

        NIT-6: the throttle looked the key up verbatim while ``_dispatch_to_entities``
        goes through ``_entity_key_candidates``, so a ``#4#3``-spelled key would have
        silently fallen back to the built-in defaults instead of the configured ones.
        """
        sensors = self._platform_cfg(SENSOR)
        for key in _entity_key_candidates(entity_key):
            cfg = sensors.get(key)
            if isinstance(cfg, dict):
                return cfg
        return {}

    def _energy_settings_for(self, entity_key: str) -> _EnergySettings:
        """Per-sensor throttle settings: sensor dict (canonical keys, already merged
        with ``sensor_defaults`` by validate.py) -> gateway ``sensor_defaults`` -> code defaults."""
        cached = self._energy_settings_cache.get(entity_key)
        if cached is not None:
            return cached
        defaults = self._gw_cfg().get(CONF_SENSOR_DEFAULTS)
        defaults = defaults if isinstance(defaults, dict) else {}
        sensor_cfg = self._sensor_cfg(entity_key)

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
        cfg = self._sensor_cfg(entity_key)
        name = cfg.get(CONF_NAME)
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
            "%s Suppressed %d instant power frame(s) for %s (%s) in the last ~%.0f s "
            "(latest %s W, min_delta_w=%s, min_interval_sec=%s)",
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

        self._discard_queued("on shutdown")
        self._set_connected(False)
        # Final snapshot (queue drained) and no timer left behind.
        self._refresh_stats(publish=True, immediate=True)
        self._cancel_stats_flush()
        return True
