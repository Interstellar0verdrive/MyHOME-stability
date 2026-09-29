"""Experimental, backend-owned measurement of one standard cover's travel times.

The bus starts the monotonic clock; the operator confirms the physical endpoints.
A queued Stop is never represented as an acknowledged or physically verified stop.
"""
from __future__ import annotations

import asyncio
import collections
import copy
import logging
import time
from time import monotonic as monotonic
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.decorators import (
    async_response,
    require_admin,
    websocket_command,
)
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CoreState, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util
from OWNd.message import OWNAutomationCommand

from .const import CONF_COVER_TRAVEL_TIMES, DOMAIN
from .cover_calibration_reservation import CalibrationReservation
from .cover_profile_provenance import EVIDENCE, evidence, unknown_provenance
from .cover_profiles import (
    DATA_KEY,
    ProfileError,
    get_store,
    snapshot,
    target,
    travel_time,
    write_profile,
)
from .data import MyHOMERuntimeData

if TYPE_CHECKING:
    from .gateway import MyHOMEGatewayHandler

LOGGER = logging.getLogger(__name__)

WS_START = "myhome/cover_calibration/start"
WS_ACTION = "myhome/cover_calibration/action"
LEASE_SECONDS = 20
RECOVERY_SECONDS = 600
START_SECONDS = 10
MAX_TRAVEL_SECONDS = 600
STOP_QUEUE_SECONDS = 30
TERMINAL = {"interrupted", "cancelled", "saved"}


class CalibrationSession:
    """One live controller; transient measurements never survive restart."""

    mode = "guided"
    travel_seconds = MAX_TRAVEL_SECONDS
    travel_reason = "travel_timeout"
    geometry_provenance: dict[str, Any] | None = None
    measured_travel: float | None = None
    safe_phases = {"confirm_closed", "confirm_open", "confirm_automatic", "review", "saving"}

    def __init__(self, hass: Any, store: Any, entry: Any, cover: Any, connection: Any, subscription_id: Any, *, direction: Any=None, profile: dict[str, Any] | None=None, client_id: str | None=None) -> None:
        self.hass, self.store, self.cover = hass, store, cover
        self.entry_id = entry.entry_id
        self.connection = connection
        self.subscription_id = subscription_id
        self.id = uuid4().hex
        self.revision = store.data["revision"]
        self.sequence = 0
        self.phase = "confirm_closed"
        self.reason: str | None = None
        self.values: dict[str, float] = {}
        self.provenance: dict[str, Any] = {}
        self.direction = direction
        if direction:
            profile = cast(dict[str, Any], profile)
            retained = "closing" if direction == "opening" else "opening"
            self.values[f"{retained}_time"] = profile[f"{retained}_time"]
            self.provenance[retained] = copy.deepcopy(profile["provenance"][retained])
            self.phase = "confirm_closed" if direction == "opening" else "confirm_open"
        self.started_at: float | None = None
        self.armed = False
        self.stop_requested = False
        self.listener = True
        self.closed = False
        self.client_id = client_id
        self.attachment = uuid4().hex
        self.retention: asyncio.TimerHandle | None = None
        self.lease: asyncio.TimerHandle | None = None
        self.deadline: asyncio.TimerHandle | None = None
        self.settle: asyncio.TimerHandle | None = None
        self.reservation = CalibrationReservation(self)
        self.shutdown = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._on_shutdown)
        self.touch()

    @callback
    def _on_shutdown(self, _event: Any) -> None:
        # HA removes a one-shot listener before invoking its callback.
        self.shutdown = None
        self.close("shutdown")
        self.reservation.completed()

    @property
    def active(self) -> Any:
        return self.phase not in TERMINAL

    def view(self) -> Any:
        return {"entry_id": self.entry_id, "entity_id": self.cover.entity_id,
                "session_id": self.id, "sequence": self.sequence, "revision": self.revision,
                "phase": self.phase, "mode": self.mode, "reason": self.reason, "values": dict(self.values),
                "elapsed": round(monotonic() - self.started_at, 2) if self.started_at is not None else None,
                "stop_requested": self.stop_requested,
                "travel_cm": self.store.data["covers"].get(self.cover.unique_id, {}).get("travel_cm"),
                "reference_travel_cm": (self.store.profile(self.cover.unique_id) or {}).get("reference_travel_cm"),
                "waiting_for_stop": self.closed and self.reservation.pending,
                **({"recoverable": not self.closed, "attached": self.listener and not self.closed, "attachment": self.attachment,
                    "recovery_seconds": RECOVERY_SECONDS} if self.client_id else {}),
                "save_modes": ["new", "cover", "shared"] if self.store.profile(self.cover.unique_id) else ["new", "cover"],
                **({"direction": self.direction} if self.direction else {})}

    def emit(self) -> None:
        self.sequence += 1
        if self.listener:
            self.connection.send_event(self.subscription_id, self.view())

    def touch(self) -> None:
        if self.lease:
            self.lease.cancel()
        self.lease = self.hass.loop.call_later(LEASE_SECONDS, self.detach, self.attachment, "heartbeat_timeout")

    def subscribe(self) -> None:
        """Bind cleanup to this attachment, never to a later controller."""
        token = self.attachment
        self.connection.subscriptions[self.subscription_id] = (lambda: self.detach(token)) if self.client_id else self.close

    def detach(self, token: str, reason: str="disconnected") -> None:
        """Retain safe checkpoints; invalidate any unattended movement immediately."""
        if self.closed or not self.listener or token != self.attachment:
            return
        if not self.client_id:
            self.close(reason)
            return
        if self.phase not in self.safe_phases:
            self.interrupt(reason)
        self.listener = False
        # Notify a still-open socket when its heartbeat lease expires.
        self.sequence += 1
        self.connection.send_event(self.subscription_id, self.view())
        if self.lease:
            self.lease.cancel()
        self.retention = self.hass.loop.call_later(RECOVERY_SECONDS, self.close, "recovery_expired")

    def attach(self, connection: Any, subscription_id: Any, client_id: str) -> None:
        """Claim a detached session without running or replaying any movement."""
        if self.closed or not self.client_id:
            raise ProfileError("calibration_expired")
        if self.listener:
            raise ProfileError("calibration_busy")
        self.connection, self.subscription_id = connection, subscription_id
        self.client_id, self.attachment = client_id, uuid4().hex
        self.listener = True
        if self.retention:
            self.retention.cancel()
            self.retention = None
        self.touch()
        self.subscribe()

    def arm_deadline(self, seconds: Any, reason: str) -> None:
        if self.deadline:
            self.deadline.cancel()
        self.deadline = self.hass.loop.call_later(seconds, self.interrupt, reason)

    def queue_stop(self) -> Any:
        expires = monotonic() + STOP_QUEUE_SECONDS
        generation = self.reservation.generation
        try:
            written = self.cover._gateway_handler.async_queue_calibration(
                OWNAutomationCommand.stop_shutter(self.cover._full_where),
                # During HA shutdown retain the best-effort Stop even after
                # runtime ownership/timers have been cleaned up.
                lambda: ((self.store.calibration is self or self.hass.state == CoreState.stopping)
                         and generation == self.reservation.generation
                         and monotonic() <= expires), self.store.calibration_command_lock,
            )
        except asyncio.QueueFull:
            self.stop_requested = False
            self.reason = "stop_queue_full"
            LOGGER.warning("Calibration Stop could not be queued for %s; use the physical control", self.cover.entity_id)
        else:
            self.stop_requested = True
            return written

    def interrupt(self, reason: str, send_stop: Any=True) -> None:
        if not self.active or self.phase == "saving":
            return
        self.phase, self.reason = "interrupted", reason
        self.values.clear()
        self.provenance.clear()
        self.started_at = None
        if self.deadline:
            self.deadline.cancel()
        if self.settle:
            self.settle.cancel()
        if send_stop:
            self.queue_stop()
        self.emit()

    def close(self, reason: str="cancelled") -> None:
        if self.closed:
            return
        self.closed = True
        try:
            # Invalidate queued motion before releasing the socket/store ownership.
            self.interrupt(reason, send_stop=reason != "recovery_expired")
            if self.phase != "saved":
                self.phase, self.reason = "cancelled", reason
            self.emit()
        finally:
            self.listener = False

            if self.lease:
                self.lease.cancel()
            if self.deadline:
                self.deadline.cancel()
            if self.retention:
                self.retention.cancel()
            if not self.reservation.pending:
                self.release()

    def release(self) -> None:
        """Release a closed client only after its outstanding movement is bounded."""
        if self.shutdown is not None:
            unsubscribe, self.shutdown = self.shutdown, None
            unsubscribe()
        if self.store.calibration is self:
            self.store.calibration = None
        if self.cover._calibration is self:
            self.cover._calibration = None

    def move(self, direction: Any) -> None:
        expected = "confirm_closed" if direction == "open" else "confirm_open"
        if self.phase != expected:
            raise ProfileError("calibration_step")
        # The action itself confirms the starting endpoint and stationary state.
        self.confirm_position(0 if direction == "open" else 100)
        self.queue_move(direction)

    def queue_move(self, direction: Any) -> Any:
        """Use the same guarded queue for guided and automatic movements."""
        token = self._motion_token = object()
        self.reservation.generation += 1
        self.phase = f"starting_{direction}"
        self.armed = False
        self.started_at = None
        self.stop_requested = False
        expires = monotonic() + START_SECONDS
        self.arm_deadline(START_SECONDS, "start_timeout")

        def guard() -> Any:
            if self._motion_token is not token or self.phase != f"starting_{direction}" or monotonic() > expires:
                return False
            self.armed = True
            self.reservation.dispatched()
            return True

        command = OWNAutomationCommand.raise_shutter if direction == "open" else OWNAutomationCommand.lower_shutter
        try:
            written = self.cover._gateway_handler.async_queue_calibration(
                command(self.cover._full_where), guard, self.store.calibration_command_lock,
            )
        except asyncio.QueueFull as error:
            self.interrupt("command_queue_full", send_stop=False)
            raise ProfileError("command_queue_full") from error
        self.emit()
        return written

    def on_event(self, event: Any) -> None:
        self.reservation.observe(event)
        if self.closed:
            return
        if self.phase not in {"starting_open", "starting_close", "opening", "closing"}:
            if self.active and (event.is_opening or event.is_closing):
                self.interrupt("unexpected_movement")
            return
        opening = self.phase in {"starting_open", "opening"}
        expected = event.is_opening if opening else event.is_closing
        opposite = event.is_closing if opening else event.is_opening
        if self.phase.startswith("starting_"):
            if expected and self.armed:
                self.phase = "opening" if opening else "closing"
                self.started_at = monotonic()
                self.arm_deadline(self.travel_seconds, self.travel_reason)
                self.emit()
            elif expected or opposite:
                self.interrupt("unexpected_movement")
        elif not expected:
            self.interrupt("unexpected_movement" if opposite else "unexpected_stop")

    def endpoint(self) -> None:
        if self.phase not in {"opening", "closing"}:
            raise ProfileError("calibration_step")
        direction = "opening" if self.phase == "opening" else "closing"
        elapsed = round(monotonic() - cast(float, self.started_at), 2)
        try:
            elapsed = travel_time(elapsed)
        except vol.Invalid as error:
            self.interrupt("invalid_measurement")
            raise ProfileError("invalid_profile") from error
        self.values[f"{direction}_time"] = elapsed
        self.provenance[direction] = evidence("guided", self.cover.unique_id)
        self.phase = "confirm_open" if direction == "opening" and not self.direction else "review"
        self.started_at = None
        cast(asyncio.TimerHandle, self.deadline).cancel()
        self.queue_stop()
        # The operator explicitly confirmed this physical endpoint. Bus Stop alone
        # cannot establish it. Keep the existing travel settings until Save.
        self.confirm_position(100 if direction == "opening" else 0)
        self.emit()

    def confirm_position(self, position: Any) -> None:
        cover = self.cover
        cover._cancel_stop_task()
        cover._attr_current_cover_position = cover._start_position = position
        cover._move_start_time = None
        cover._motion.confirm(position)
        cover._attr_is_opening = cover._attr_is_closing = False
        cover._attr_is_closed = position == 0
        cover.async_write_ha_state()

    async def action(self, msg: dict[str, Any]) -> Any:
        action = msg["action"]
        if action == "cancel":
            self.close()
            return self.view()
        if action == "stop":
            self.interrupt("stopped", send_stop=False)
            self.queue_stop()
            self.emit()
            return self.view()
        if action == "heartbeat":
            self.touch()
            return self.view()
        if action == "detach":
            self.detach(self.attachment)
            return self.view()
        if not self.active or msg.get("sequence") != self.sequence:
            raise ProfileError("calibration_step")
        entry, entity = target(self.hass, self.entry_id, self.cover.entity_id)
        if not snapshot(self.hass, self.store, entry, entity)["writable"]:
            self.interrupt("cover_unavailable")
            raise ProfileError("cover_unavailable")
        if self.mode == "geometry" and action not in {"save", "preview_save"}:
            self.geometry_action(msg)
        elif action == "run":
            if self.mode != "automatic" or self.phase != "confirm_automatic":
                raise ProfileError("calibration_step")
            self.queue_move("open")
        elif action in {"open", "close", "endpoint"} and self.mode != "guided":
            raise ProfileError("calibration_step")
        elif action in {"open", "close"}:
            self.move(action)
        elif action == "endpoint":
            self.endpoint()
        elif action in {"next", "lift", "reading", "repeat"}:
            raise ProfileError("calibration_step")
        elif action == "preview_save":
            if self.phase != "review" or msg.get("save_mode") != "shared" or "shared" not in self.view()["save_modes"]:
                raise ProfileError("calibration_step")
            from .cover_calibration_save import save_measurement
            preview = await save_measurement(self, msg, preview=True)
            return {**self.view(), "save_preview": preview}
        elif action == "save":
            if self.phase != "review":
                raise ProfileError("calibration_step")
            if msg.get("save_mode", "new") not in self.view()["save_modes"]:
                raise ProfileError("invalid_profile")
            self.phase = "saving"
            self.emit()
            try:
                revision = await self.save_profiles(msg)
            except (ProfileError, vol.Invalid, OSError):
                if self.store.calibration is self and not self.closed:
                    self.phase = "review"
                    self.emit()
                raise
            self.revision = revision
            self.phase = "saved"
            self.emit()
            self.close()
        return self.view()


    def geometry_action(self, msg: dict[str, Any]) -> None:
        """Only the geometry subclass implements these protocol actions."""
        raise ProfileError("calibration_step")

    async def save_profiles(self, msg: dict[str, Any]) -> Any:
        if msg.get("save_mode", "new") != "new":
            from .cover_calibration_save import save_measurement
            return await save_measurement(self, msg)
        travel = self.store.data["covers"].get(self.cover.unique_id, {}).get("travel_cm")
        result = await write_profile(self.hass, {
            "entry_id": self.entry_id, "entity_id": self.cover.entity_id,
            "revision": self.revision, "action": "save", "profile_id": None,
            "profile": {"name": msg.get("name", ""), **self.values,
                        **({"reference_travel_cm": travel} if travel is not None else {})},
        }, calibration=self)
        return result["revision"]


def ready_cover(hass: Any, store: Any, entry_id: str, entity_id: str) -> Any:
    """Validate the same target and stationary state for every calibration mode."""
    entry, entity = target(hass, entry_id, entity_id)
    view = snapshot(hass, store, entry, entity)
    if hass.state in (CoreState.stopping, CoreState.final_write, CoreState.stopped):
        raise ProfileError("cover_unavailable")
    if not view["writable"]:
        raise ProfileError(view["reason"])
    cover = store.covers[entity.unique_id]
    if cover.native_calibration_busy():
        raise ProfileError("calibration_busy")
    if (cover._attr_is_opening or cover._attr_is_closing or cover._move_start_time is not None
            or cover._pending_profile or cover._stop_task):
        raise ProfileError("calibration_moving")
    return cover


async def begin(hass: Any, connection: Any, msg: dict[str, Any]) -> Any:
    entry, entity = target(hass, msg["entry_id"], msg["entity_id"])
    store = get_store(hass, entry.entry_id)
    async with store.lock:
        await store.load()
        if store.calibration is not None and not store.calibration.closed and msg.get("client_id") == store.calibration.client_id and msg.get("client_id"):
            store.calibration.attach(connection, msg["id"], msg["client_id"])
            return store.calibration
        if store.calibration is not None:
            raise ProfileError("calibration_busy")
        cover = ready_cover(hass, store, entry.entry_id, msg["entity_id"])
        if msg["revision"] != store.data["revision"]:
            raise ProfileError("revision_conflict")
        options = {}
        if "direction" in msg:
            direction = vol.In(["opening", "closing"])(msg["direction"])
            if msg.get("mode", "guided") != "guided":
                raise ProfileError("invalid_profile")
            retained = "closing" if direction == "opening" else "opening"
            setting = cover.resolve_cover_settings(store.profile(cover.unique_id))[retained]
            # Resolve committed values even without an assignment. A native record
            # may lack the origin/date required by profile evidence; do not invent
            # a measurement or overwrite that original fallback record.
            try:
                if setting["origin"] == "native_fallback" and setting["provenance"]["origin_unique_id"] is None:
                    raise vol.Invalid("Native evidence has no recorded origin")
                provenance = EVIDENCE(setting["provenance"])
            except vol.Invalid:
                provenance = unknown_provenance()[retained]
            options = {"direction": direction, "profile": {
                f"{retained}_time": travel_time(setting["value"]),
                "provenance": {retained: provenance},
            }}
        session_type: type[CalibrationSession] = CalibrationSession
        if msg.get("mode", "guided") == "automatic":
            from .cover_calibration_automatic import AutomaticCalibrationSession
            session_type = AutomaticCalibrationSession
        if msg.get("mode") == "geometry":
            from .cover_calibration_geometry import GeometryCalibrationSession
            session_type = GeometryCalibrationSession
        session = session_type(hass, store, entry, cover, connection, msg["id"], client_id=msg.get("client_id"), **options)
        store.calibration = cover._calibration = session
        session.subscribe()
        return session


@websocket_command({
    vol.Required("type"): WS_START, vol.Required("entry_id"): str,
    vol.Required("entity_id"): str, vol.Required("revision"): vol.All(int, vol.Range(min=0)),
    vol.Optional("mode"): vol.In(["guided", "automatic", "geometry"]),
    vol.Optional("direction"): vol.In(["opening", "closing"]),
    vol.Optional("client_id"): vol.All(str, vol.Length(min=1, max=64)),
})
@require_admin
@async_response
async def ws_start(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    try:
        session = await begin(hass, connection, msg)
    except (ProfileError, vol.Invalid, OSError) as error:
        send_error(connection, msg, error)
        return
    connection.send_result(msg["id"])
    session.emit()


def send_error(connection: Any, msg: dict[str, Any], error: Any) -> None:
    code = str(error) if isinstance(error, ProfileError) else "invalid_profile" if isinstance(error, vol.Invalid) else "storage_error"
    connection.send_error(msg["id"], code, code)


@websocket_command({
    vol.Required("type"): WS_ACTION, vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("action"): vol.In(["run", "open", "close", "endpoint", "stop", "cancel", "save", "preview_save", "heartbeat", "detach", "next", "lift", "reading", "repeat"]),
    vol.Optional("reading_cm"): vol.Any(int, float),
    vol.Optional("attachment"): str,
    vol.Optional("sequence"): vol.All(int, vol.Range(min=0)),
    vol.Optional("name"): str,
    vol.Optional("save_mode"): vol.In(["new", "cover", "shared"]),
    vol.Optional("confirmation"): str,
    vol.Optional("names"): vol.All([str], vol.Length(min=1, max=20)),
})
@require_admin
@async_response
async def ws_action(hass: Any, connection: Any, msg: dict[str, Any]) -> None:
    store = hass.data.get(DATA_KEY, {}).get(msg["entry_id"])
    session = store.calibration if store else None
    if (session is None or session.id != msg["session_id"] or session.connection is not connection
            or not session.listener or (session.client_id and msg.get("attachment") != session.attachment)):
        connection.send_error(msg["id"], "calibration_expired", "Calibration session is not owned by this connection")
        return
    try:
        result = await session.action(msg)
    except (ProfileError, vol.Invalid, OSError) as error:
        send_error(connection, msg, error)
    else:
        connection.send_result(msg["id"], result)


@callback
def register_api(hass: Any) -> None:
    from .cover_calibration_batch import ws_batch_start, ws_targets
    from .cover_calibration_recovery import ws_resume
    websocket_api.async_register_command(hass, ws_resume)
    websocket_api.async_register_command(hass, ws_batch_start)
    websocket_api.async_register_command(hass, ws_targets)
    websocket_api.async_register_command(hass, ws_start)
    websocket_api.async_register_command(hass, ws_action)


# Native calibrate_cover service compatibility and per-gateway trace hub.
def _gateway_key(gateway: Any) -> str:
    """Return a unique key for the gateway (MAC address or object id)."""
    return str(getattr(gateway, "mac", "") or id(gateway))


def _normalize_mac(mac: Any) -> str | None:
    """One spelling for a gateway MAC so frames and requests compare equal."""
    if mac is None or str(mac).strip() == "":
        return None
    return dr.format_mac(str(mac))


def _calibration_lock(gateway: Any) -> asyncio.Lock:
    """Return the per-gateway calibration lock, rebinding if event loop changed."""
    return get_calibration_hub(gateway).lock


def _record_calibration_frame(gateway: Any, direction: str, raw: str, **extra: Any) -> None:
    """Record a frame during active calibration to the trace buffer."""
    hub = get_calibration_hub(gateway)
    hub.record_frame(direction, raw, **extra)


def get_last_calibration_trace(gateway_mac: str | None = None, hass: Any = None) -> list[dict[str, Any]]:
    """Return in-memory trace frames captured during recent cover calibrations.

    Traces are stored on each gateway's CoverCalibrationHub. When gateway_mac is
    provided, only that gateway's trace is returned (None is the only unfiltered
    read; a gateway without a MAC gets the frames recorded without one).
    """
    hubs = CoverCalibrationHub.all_hubs(hass)

    if gateway_mac is None:
        combined: list[dict[str, Any]] = []
        for hub in hubs:
            combined.extend(hub.get_trace())
        combined.sort(key=lambda f: f.get("timestamp", 0.0))
        return combined

    wanted = _normalize_mac(gateway_mac)
    for hub in hubs:
        if hub.mac == wanted:
            return hub.get_trace()
    return []


async def async_stop_cover_calibration(hass: Any = None, gateway_mac: str | None = None) -> bool:
    """Stop active and queued cover calibrations on one or all gateways."""
    stopped_any = False
    wanted_mac = _normalize_mac(gateway_mac) if gateway_mac else None

    for hub in CoverCalibrationHub.all_hubs(hass):
        if wanted_mac and hub.mac != wanted_mac:
            continue
        if await hub.async_stop():
            stopped_any = True

    return stopped_any


def _stored_calibration(config_entry: Any, device_id: str) -> dict[str, Any] | None:
    """Return the persisted calibration for a cover, if any."""
    options = getattr(config_entry, "options", None) or {}
    stored = options.get(CONF_COVER_TRAVEL_TIMES) or {}
    entry = stored.get(str(device_id))
    return dict(entry) if isinstance(entry, dict) else None


class CalibrationInterrupted(HomeAssistantError):
    """A wall-switch or scenario command interfered with a calibration run."""

    def __init__(self, name: str, cause: str) -> None:
        super().__init__(
            f"{name}: {cause}",
            translation_domain=DOMAIN,
            translation_key="calibration_interrupted",
            translation_placeholders={"name": name, "cause": cause},
        )


class CoverCalibrationHub:
    """Encapsulates calibration state and serialization per gateway."""

    _registry: dict[str, CoverCalibrationHub] = {}

    def __init__(self, gateway: Any) -> None:
        self.gateway: MyHOMEGatewayHandler = gateway
        self.trace: collections.deque[dict[str, Any]] = collections.deque(maxlen=1000)
        self._lock: asyncio.Lock | None = None
        self._active_cover: Any | None = None
        self._queued_covers: set[Any] = set()
        self._register()

    def _register(self) -> None:
        CoverCalibrationHub._registry[self.key] = self
        if self.mac:
            CoverCalibrationHub._registry[self.mac] = self

    def _unregister(self) -> None:
        if CoverCalibrationHub._registry.get(self.key) is self:
            CoverCalibrationHub._registry.pop(self.key, None)
        if self.mac and CoverCalibrationHub._registry.get(self.mac) is self:
            CoverCalibrationHub._registry.pop(self.mac, None)

    @classmethod
    def all_hubs(cls, hass: Any = None) -> list[CoverCalibrationHub]:
        """Return all active hubs from hass config entries and local registry."""
        hubs: list[CoverCalibrationHub] = []
        seen: set[int] = set()
        if hass is not None and hasattr(hass, "config_entries"):
            for entry in hass.config_entries.async_entries(DOMAIN):
                runtime = getattr(entry, "runtime_data", None)
                hub = getattr(runtime, "calibration_hub", None)
                if isinstance(hub, CoverCalibrationHub) and id(hub) not in seen:
                    hubs.append(hub)
                    seen.add(id(hub))
        for hub in list(cls._registry.values()):
            if id(hub) not in seen:
                hubs.append(hub)
                seen.add(id(hub))
        return hubs

    @classmethod
    def reset_for_tests(cls) -> None:
        """Reset all hubs and clear the registry (for test fixtures)."""
        for hub in list(cls._registry.values()):
            hub.cleanup()
        cls._registry.clear()





    @property
    def mac(self) -> str | None:
        """Return the normalized gateway MAC address."""
        return _normalize_mac(getattr(self.gateway, "mac", None))

    @property
    def key(self) -> str:
        """Return a unique key for the gateway."""
        return _gateway_key(self.gateway)

    @property
    def lock(self) -> asyncio.Lock:
        """Return the asyncio.Lock, dynamically rebinding if the running loop changed."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._lock is not None:
            bound_loop = getattr(self._lock, "_bound_loop", None) or getattr(self._lock, "_loop", None)
            if (bound_loop is not None and bound_loop.is_closed()) or (
                current_loop is not None and bound_loop is not current_loop
            ):
                self._lock = None

        if self._lock is None:
            self._lock = asyncio.Lock()
            if current_loop is not None:
                setattr(self._lock, "_bound_loop", current_loop)

        return self._lock

    @property
    def active_cover(self) -> Any | None:
        """Return the currently calibrating cover for this gateway."""
        return self._active_cover

    @active_cover.setter
    def active_cover(self, cover: Any | None) -> None:
        self._active_cover = cover

    @property
    def is_calibrating(self) -> bool:
        """Return True if any cover on this gateway is actively calibrating."""
        return bool(self._active_cover is not None and getattr(self._active_cover, "_calibrating", False))

    @property
    def queued_covers(self) -> set[Any]:
        """Return set of covers waiting for calibration lock on this gateway."""
        return self._queued_covers

    def record_frame(self, direction: str, raw: str, **extra: Any) -> None:
        """Record a calibration frame to this hub's trace buffer."""
        now = dt_util.utcnow()
        frame = {
            "timestamp": time.time(),
            "iso_time": now.isoformat(),
            "gateway_mac": self.mac,
            "direction": direction,
            "raw": str(raw).strip(),
            **extra,
        }
        self.trace.append(frame)

    def get_trace(self) -> list[dict[str, Any]]:
        """Return the in-memory trace frames recorded for this gateway."""
        return list(self.trace)

    async def async_stop(self) -> bool:
        """Stop active and queued calibrations on this gateway."""
        stopped_any = False
        queued = list(self.queued_covers)
        self.queued_covers.clear()
        for c in queued:
            c._calibration_interrupted = "Calibration stopped by user"
            c._fire_calibration_event("failed", error="Calibration stopped by user")
            stopped_any = True

        active = self.active_cover
        if active is not None and getattr(active, "_calibrating", False):
            active._calibration_interrupted = "Calibration stopped by user"
            active._motor_started.set()
            active._stopped_event.set()
            try:
                await active.async_stop_cover()
            except Exception as err:
                LOGGER.warning("Error stopping cover %s: %s", active.entity_id, err)
            stopped_any = True
            self.active_cover = None

        return stopped_any

    def cleanup(self) -> None:
        """Clean up all references when gateway unloads."""
        self._active_cover = None
        self._queued_covers.clear()
        self._lock = None
        self.trace.clear()
        self._unregister()


def get_calibration_hub(gateway: Any) -> CoverCalibrationHub:
    """Return or create the CoverCalibrationHub for a gateway handler."""
    entry = getattr(gateway, "config_entry", None)
    runtime = getattr(entry, "runtime_data", None) if entry is not None else None
    if isinstance(runtime, MyHOMERuntimeData):
        if runtime.calibration_hub is None:
            hub = getattr(gateway, "_calibration_hub", None)
            if not isinstance(hub, CoverCalibrationHub):
                hub = CoverCalibrationHub(gateway)
            runtime.calibration_hub = hub
        return runtime.calibration_hub

    if runtime is not None:
        raw_hub = getattr(runtime, "calibration_hub", None)
        if isinstance(raw_hub, CoverCalibrationHub):
            return raw_hub

    # Fallback when runtime_data is not available (e.g. mock objects in unit tests)
    hub = getattr(gateway, "_calibration_hub", None)
    if not isinstance(hub, CoverCalibrationHub):
        hub = CoverCalibrationHub(gateway)
        try:
            gateway._calibration_hub = hub
        except Exception:  # pragma: no cover - defensive
            pass
    return hub
