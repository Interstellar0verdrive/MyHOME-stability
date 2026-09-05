"""Support for MyHOME covers (WHO 2 shutters, basic and advanced actuators).

Contract F: basic (non-advanced) actuators give no position feedback, they only
report "opening", "closing" and "stopped".  This module estimates the position from
the configured travel times, exposes it as `current_cover_position` (0 = closed,
100 = open), derives open/closed from it, implements `set_cover_position` with a
timed stop and restores the last position across restarts.  Such covers are flagged
`assumed_state`.

Two-phase travel model (0.4.0).  On a real roller shutter the motor run is not all
lift: starting from fully closed the first `slat_time` seconds only open the slats
("lamelle") while the curtain stays on the floor, and when closing the motor keeps
running for `slat_time` seconds after the curtain has touched the floor, to close
them again.  The model therefore splits every run into

* a **slat phase** of `slat_time` seconds, reported as `current_cover_tilt_position`
  (0 = slats closed, 100 = slats open), and
* a **curtain phase** of `opening_time - slat_time` (up) / `closing_time - slat_time`
  (down) seconds, reported as `current_cover_position` (0 = curtain on the floor,
  whatever the slats do, 100 = fully open).

The cover is *closed* only when the curtain is down **and** the slats are closed.
While the curtain is up the slats are necessarily open, so tilt is pinned to 100 and
tilt commands are no-ops.  `slat_time: 0` (the default) disables the whole thing and
reproduces the 0.3.x linear model exactly, tilt included (no tilt feature at all).

Advanced actuators report a real position through dimension 10; OWNd maps
`position == 0` to *closed* (`OWNAutomationEvent`), which matches the HA convention,
so their value is used verbatim.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DOMAIN as PLATFORM,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
    CoverState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.restore_state import ExtraStoredData, RestoredExtraData, RestoreEntity
from homeassistant.util import dt as dt_util

from OWNd.message import (
    OWNAutomationCommand,
    OWNAutomationEvent,
)

from .const import (
    CONF_ADVANCED_SHUTTER,
    CONF_BUS_INTERFACE,
    CONF_CLOSING_TIME,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_MODEL,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
    CONF_ICON,
    CONF_INVERTED,
    CONF_MANUFACTURER,
    CONF_OPENING_TIME,
    CONF_PLATFORMS,
    CONF_SHUTTER_RUN,
    CONF_SLAT_TIME,
    CONF_WHERE,
    CONF_WHO,
    DEFAULT_SHUTTER_RUN,
    DEFAULT_SLAT_TIME,
    DOMAIN,
    LOGGER,
    bus_full_where,
)
from .gateway import MyHOMEGatewayHandler
from .myhome_device import MyHOMEEntity, address_attributes

# How often the estimated position is pushed to Home Assistant while the cover moves.
POSITION_TICK = timedelta(seconds=1)

OPENING = "opening"
CLOSING = "closing"

# The curtain phase can never be zero: the validator keeps at least one second of it,
# this only protects the divisions against a hand-crafted device config.
MIN_CURTAIN_TIME = 0.001


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the cover entities of this gateway (none when unconfigured)."""
    configured_covers = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_PLATFORMS].get(PLATFORM, {})
    if not configured_covers:
        return

    gateway_handler = hass.data[DOMAIN][config_entry.data[CONF_MAC]][CONF_ENTITY]
    covers = [
        MyHOMECover(
            hass=hass,
            device_id=device_id,
            who=cfg[CONF_WHO],
            where=cfg[CONF_WHERE],
            interface=cfg.get(CONF_BUS_INTERFACE),
            name=cfg[CONF_NAME],
            entity_name=cfg[CONF_ENTITY_NAME],
            icon=cfg[CONF_ICON],
            device_class=cfg[CONF_DEVICE_CLASS],
            advanced=cfg[CONF_ADVANCED_SHUTTER],
            shutter_run=cfg[CONF_SHUTTER_RUN],
            slat_time=cfg.get(CONF_SLAT_TIME, DEFAULT_SLAT_TIME),
            opening_time=cfg.get(CONF_OPENING_TIME),
            closing_time=cfg.get(CONF_CLOSING_TIME),
            inverted=cfg[CONF_INVERTED],
            manufacturer=cfg[CONF_MANUFACTURER],
            model=cfg[CONF_DEVICE_MODEL],
            gateway=gateway_handler,
        )
        for device_id, cfg in configured_covers.items()
    ]

    async_add_entities(covers)


class MyHOMECover(MyHOMEEntity, CoverEntity, RestoreEntity):
    """A WHO 2 shutter."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        entity_name: str | None,
        icon: str | None,
        device_id: str,
        who: str,
        where: str,
        interface: str | None,
        device_class: CoverDeviceClass | str | None,
        advanced: bool,
        shutter_run: float,
        inverted: bool,
        manufacturer: str | None,
        model: str | None,
        gateway: MyHOMEGatewayHandler,
        slat_time: float = DEFAULT_SLAT_TIME,
        opening_time: float | None = None,
        closing_time: float | None = None,
    ) -> None:
        super().__init__(
            hass=hass,
            name=name,
            platform=PLATFORM,
            device_id=device_id,
            who=who,
            where=where,
            manufacturer=manufacturer,
            model=model,
            gateway=gateway,
            entity_name=entity_name,
        )

        self._interface = interface
        # The interface must go on the bus unpadded (`11#4#3`): that is what the
        # F422 emits and what OWNd 0.7.49 parses back (0.3.1 / carferrer).
        self._full_where = bus_full_where(self._where, self._interface)

        try:
            self._attr_device_class = CoverDeviceClass(str(device_class).lower())
        except ValueError:
            self._attr_device_class = CoverDeviceClass.SHUTTER
        if icon is not None:
            self._attr_icon = icon

        self._advanced = bool(advanced)
        # Contract A guarantees a float >= 1; fall back to the schema default anyway.
        self._shutter_run = float(shutter_run or DEFAULT_SHUTTER_RUN)
        # Per-direction runs default to the common `shutter_run` (Contract A / 0.4.0).
        self._opening_time = float(opening_time or self._shutter_run)
        self._closing_time = float(closing_time or self._shutter_run)
        self._slat_time = max(0.0, float(slat_time or 0.0))
        # Curtain-only part of each run (the validator keeps it >= 1 s).
        self._curtain_up = max(MIN_CURTAIN_TIME, self._opening_time - self._slat_time)
        self._curtain_down = max(MIN_CURTAIN_TIME, self._closing_time - self._slat_time)
        self._inverted = bool(inverted)
        # Tilt is only meaningful on a basic cover with a configured slat phase.
        self._has_tilt = not self._advanced and self._slat_time > 0

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        if self._has_tilt:
            self._attr_supported_features |= (
                CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.SET_TILT_POSITION
                | CoverEntityFeature.STOP_TILT
            )
        # Basic actuators never report their position: everything below the
        # `_estimate` line is an assumption (Contract F).
        self._attr_assumed_state = not self._advanced

        self._attr_extra_state_attributes = address_attributes(where, self._interface)
        if not self._advanced:
            self._attr_extra_state_attributes["Shutter run"] = self._shutter_run
            # Only advertise the 0.4.0 keys when they actually change the model.
            if self._slat_time > 0:
                self._attr_extra_state_attributes["Slat time"] = self._slat_time
            if self._opening_time != self._shutter_run:
                self._attr_extra_state_attributes["Opening time"] = self._opening_time
            if self._closing_time != self._shutter_run:
                self._attr_extra_state_attributes["Closing time"] = self._closing_time

        self._attr_current_cover_position: int | None = None
        self._attr_current_cover_tilt_position: int | None = None
        self._attr_is_closed: bool | None = None

        # Movement bookkeeping for the time-based estimate.
        self._moving: str | None = None
        self._move_started_at: datetime | None = None
        self._move_start_position: int | None = None
        self._move_start_tilt: int | None = None
        # Set only when *we* have to stop the cover (`set_cover_position`, tilt).
        self._target_position: int | None = None
        # Where the estimate settles when the pending timer fires.
        self._end_position: int | None = None
        self._end_tilt: int | None = None
        self._stop_timer = None
        self._tick_unsub = None

    # ------------------------------------------------------------------ state
    @property
    def current_cover_position(self) -> int | None:
        """Position of the *curtain* (0 = on the floor, 100 = fully open).

        Advanced actuators report it; for basic ones it is extrapolated from the
        movement start time and the configured travel times.
        """
        if self._advanced:
            return self._attr_current_cover_position
        return self._estimate()[0]

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Openness of the slats (0 = closed, 100 = open), or None without `slat_time`."""
        if not self._has_tilt:
            return None
        return self._estimate()[1]

    @property
    def is_opening(self) -> bool | None:
        """True while the cover is known to be opening."""
        return self._moving == OPENING

    @property
    def is_closing(self) -> bool | None:
        """True while the cover is known to be closing."""
        return self._moving == CLOSING

    @property
    def is_closed(self) -> bool | None:
        """Closed when the curtain is down *and* the slats are closed (plat-07)."""
        position = self.current_cover_position
        if position is None:
            return self._attr_is_closed
        if position != 0:
            return False
        if not self._has_tilt:
            return True
        tilt = self.current_cover_tilt_position
        return True if tilt is None else tilt == 0

    # ------------------------------------------------------------------ travel model
    def _normalise(self, position: float, tilt: float) -> tuple[int, int]:
        """Clamp a (position, tilt) pair to the states the shutter can physically be in.

        The slats can only be closed while the curtain rests on the floor, so any
        position above 0 implies fully open slats; without a slat phase the tilt
        simply follows the position (0/100) and is never published.
        """
        clamped = int(max(0, min(100, round(position))))
        if clamped > 0:
            return clamped, 100
        if self._slat_time <= 0:
            return 0, 0
        return 0, int(max(0, min(100, round(tilt))))

    def _travel(self, direction: str, position: int, tilt: int, elapsed: float) -> tuple[int, int]:
        """State reached `elapsed` seconds after leaving (`position`, `tilt`)."""
        slat = self._slat_time
        if direction == OPENING:
            if position <= 0 and slat > 0 and tilt < 100:
                # Slat phase first: the curtain does not move until the slats are open.
                slat_left = (100 - tilt) / 100 * slat
                if elapsed <= slat_left:
                    return self._normalise(0, tilt + elapsed / slat * 100)
                elapsed -= slat_left
            return self._normalise(position + elapsed / self._curtain_up * 100, 100)
        curtain_left = position / 100 * self._curtain_down
        if elapsed < curtain_left:
            return self._normalise(position - elapsed / self._curtain_down * 100, 100)
        # The curtain is on the floor: the rest of the run closes the slats.
        elapsed -= curtain_left
        if slat <= 0:
            return self._normalise(0, 0)
        start_tilt = 100 if position > 0 else tilt
        return self._normalise(0, start_tilt - elapsed / slat * 100)

    def _travel_time(
        self,
        direction: str,
        position: int,
        tilt: int,
        target_position: int,
        target_tilt: int,
    ) -> float:
        """Seconds the motor must run to go from (`position`, `tilt`) to the target."""
        slat = self._slat_time
        if direction == OPENING:
            seconds = 0.0
            if position <= 0 and slat > 0:
                # Opening past the floor always ends with the slats fully open.
                slat_target = 100 if target_position > 0 else target_tilt
                seconds += max(0.0, slat_target - tilt) / 100 * slat
            return seconds + max(0.0, target_position - position) / 100 * self._curtain_up
        seconds = max(0.0, position - target_position) / 100 * self._curtain_down
        if target_position <= 0 and slat > 0:
            start_tilt = 100 if position > 0 else tilt
            seconds += max(0.0, start_tilt - target_tilt) / 100 * slat
        return seconds

    def _estimate(self) -> tuple[int | None, int | None]:
        """Current (position, tilt), extrapolated from the running movement."""
        if (
            self._moving is None
            or self._move_started_at is None
            or self._move_start_position is None
            or self._move_start_tilt is None
        ):
            return self._attr_current_cover_position, self._attr_current_cover_tilt_position
        elapsed = (dt_util.utcnow() - self._move_started_at).total_seconds()
        return self._travel(self._moving, self._move_start_position, self._move_start_tilt, elapsed)

    # ------------------------------------------------------------------ movement
    @callback
    def _cancel_timers(self) -> None:
        """Cancel the auto-stop and the position ticker."""
        if self._stop_timer is not None:
            self._stop_timer()
            self._stop_timer = None
        if self._tick_unsub is not None:
            self._tick_unsub()
            self._tick_unsub = None

    @callback
    def _start_movement(
        self,
        direction: str,
        target_position: int | None = None,
        target_tilt: int | None = None,
    ) -> None:
        """Start (or restart) the time-based estimate in `direction`.

        `target_position` is set only when the movement must be stopped by us
        (`set_cover_position`, `set_cover_tilt_position`); otherwise the actuator
        stops at the end of its run and we only time the estimate.
        """
        position, tilt = self._estimate()
        self._cancel_timers()
        if position is None:
            # Nothing known yet: assume the opposite end so that a full travel
            # settles on the correct position.
            position, tilt = (0, 0) if direction == OPENING else (100, 100)
        if tilt is None:
            tilt = 100 if position > 0 else 0
        position, tilt = self._normalise(position, tilt)

        self._move_start_position = position
        self._move_start_tilt = tilt
        self._move_started_at = dt_util.utcnow()
        self._moving = direction
        self._target_position = target_position

        if target_position is None:
            # Free run to the end stop: fully open (slats open) or fully closed.
            end_position, end_tilt = (100, 100) if direction == OPENING else (0, 0)
        else:
            end_position = target_position
            end_tilt = 100 if target_tilt is None else target_tilt
        self._end_position, self._end_tilt = self._normalise(end_position, end_tilt)

        duration = self._travel_time(direction, position, tilt, self._end_position, self._end_tilt)
        if duration <= 0:
            self._finish_movement(self._end_position, self._end_tilt)
            return

        self._stop_timer = async_call_later(self.hass, duration, self._async_movement_deadline)
        self._tick_unsub = async_track_time_interval(self.hass, self._async_position_tick, POSITION_TICK)

    @callback
    def _finish_movement(self, position: int | None, tilt: int | None = None) -> None:
        """Stop estimating and freeze the position (and the slats)."""
        self._cancel_timers()
        self._moving = None
        self._move_started_at = None
        self._move_start_position = None
        self._move_start_tilt = None
        self._target_position = None
        self._end_position = None
        self._end_tilt = None
        if position is not None:
            frozen_position, frozen_tilt = self._normalise(position, 100 if tilt is None else tilt)
            self._attr_current_cover_position = frozen_position
            self._attr_current_cover_tilt_position = frozen_tilt
            self._attr_is_closed = frozen_position == 0 and frozen_tilt == 0

    @callback
    def _async_position_tick(self, now: datetime) -> None:
        """Push the estimated position to HA while the cover moves."""
        self.async_write_ha_state()

    async def _async_movement_deadline(self, now: datetime) -> None:
        """The cover reached its target (or the end of its run)."""
        self._stop_timer = None
        needs_stop = self._target_position is not None
        end_position, end_tilt = self._end_position, self._end_tilt
        self._finish_movement(end_position, end_tilt)
        if needs_stop:
            await self._gateway_handler.send(OWNAutomationCommand.stop_shutter(self._full_where))
        self.async_write_ha_state()

    # ------------------------------------------------------------------ lifecycle
    @property
    def extra_restore_state_data(self) -> ExtraStoredData | None:
        """Persist the estimated position and tilt independently of the entity state.

        When the config entry is unloaded the gateway connection is closed first,
        so the entity is already ``unavailable`` (no attributes) by the time Home
        Assistant snapshots its state for restoration. Extra data survives that.
        """
        if self._advanced:
            return None
        return RestoredExtraData(
            {"position": self.current_cover_position, "tilt": self.current_cover_tilt_position}
        )

    async def async_added_to_hass(self) -> None:
        """Register, request the status and restore the last known position/tilt."""
        await super().async_added_to_hass()
        if self._advanced or self._attr_current_cover_position is not None:
            return
        position: int | None = None
        tilt: int | None = None
        extra_data = await self.async_get_last_extra_data()
        if extra_data is not None:
            stored = extra_data.as_dict()
            position = stored.get("position")
            tilt = stored.get("tilt")
        if position is None:
            last_state = await self.async_get_last_state()
            if last_state is None:
                return
            position = last_state.attributes.get(ATTR_CURRENT_POSITION)
            tilt = last_state.attributes.get(ATTR_CURRENT_TILT_POSITION)
            if position is None:
                if last_state.state == CoverState.CLOSED:
                    position = 0
                elif last_state.state == CoverState.OPEN:
                    position = 100
        if position is not None:
            if tilt is None:
                # Upgrades from a version without tilt: the slats are open unless the
                # curtain rests on the floor.
                tilt = 100 if int(position) > 0 else 0
            self._finish_movement(int(position), int(tilt))
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending timers before the entity goes away."""
        self._cancel_timers()
        await super().async_will_remove_from_hass()

    # ------------------------------------------------------------------ commands
    def _direction_command(self, direction: str):
        """The bus command that moves the cover in `direction` (honouring `inverted`)."""
        if (direction == OPENING) != self._inverted:
            return OWNAutomationCommand.raise_shutter
        return OWNAutomationCommand.lower_shutter

    async def async_update(self) -> None:
        """Ask the gateway for the current state (also called on entity add)."""
        await self._gateway_handler.send_status_request(OWNAutomationCommand.status(self._full_where))

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover, all the way to the upper end stop."""
        if await self._gateway_handler.send(self._direction_command(OPENING)(self._full_where)) and not self._advanced:
            self._start_movement(OPENING)
            self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover, all the way to the lower end stop (slats included)."""
        if await self._gateway_handler.send(self._direction_command(CLOSING)(self._full_where)) and not self._advanced:
            self._start_movement(CLOSING)
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover and freeze the estimated position and tilt."""
        await self._gateway_handler.send(OWNAutomationCommand.stop_shutter(self._full_where))
        if not self._advanced:
            self._finish_movement(*self._estimate())
            self.async_write_ha_state()

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """Stop the slats: the same bus command as `stop_cover`."""
        await self.async_stop_cover(**kwargs)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the curtain to a specific position.

        Advanced actuators take the position directly; for basic ones the cover is
        moved in the right direction and stopped by a timer, after the run computed
        through both phases of the model (Contract F).  The two ends are run to the
        end stop instead, which also re-calibrates the estimate.
        """
        if ATTR_POSITION not in kwargs:
            return
        position = int(kwargs[ATTR_POSITION])

        if self._advanced:
            await self._gateway_handler.send(OWNAutomationCommand.set_shutter_level(self._full_where, position))
            return

        current = self.current_cover_position
        if current is None:
            # Unknown position: run to the closest end first so the estimate has a
            # reference; a plain open/close is the honest approximation here.
            if position >= 50:
                await self.async_open_cover()
            else:
                await self.async_close_cover()
            return
        if position >= 100:
            await self.async_open_cover()
            return
        if position <= 0:
            await self.async_close_cover()
            return
        if position == current:
            return

        direction = OPENING if position > current else CLOSING
        if await self._gateway_handler.send(self._direction_command(direction)(self._full_where)):
            # Above the floor the slats are always open.
            self._start_movement(direction, target_position=position, target_tilt=100)
            self.async_write_ha_state()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the slats (only meaningful with the curtain on the floor)."""
        await self._async_move_tilt(100)

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the slats: run down to the lower end stop."""
        await self._async_move_tilt(0)

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Set the slat openness proportionally inside the slat phase."""
        if ATTR_TILT_POSITION not in kwargs:
            return
        await self._async_move_tilt(int(kwargs[ATTR_TILT_POSITION]))

    async def _async_move_tilt(self, target_tilt: int) -> None:
        """Move the slats to `target_tilt` (0-100); no-op while the curtain is up."""
        if not self._has_tilt:
            return
        position, tilt = self._estimate()
        if position is None:
            LOGGER.debug(
                "%s Cover %s: tilt command ignored, the position is not known yet",
                self._gateway_handler.log_id,
                self._where,
            )
            return
        if position > 0:
            LOGGER.debug(
                "%s Cover %s: the slats are always open while the curtain is up (position %s%%), tilt command ignored",
                self._gateway_handler.log_id,
                self._where,
                position,
            )
            return
        if target_tilt <= 0:
            # Closing the slats means running into the lower end stop: let the
            # actuator stop by itself, it re-calibrates the estimate for free.
            await self.async_close_cover()
            return
        if tilt is None or target_tilt == tilt:
            return
        direction = OPENING if target_tilt > tilt else CLOSING
        if await self._gateway_handler.send(self._direction_command(direction)(self._full_where)):
            self._start_movement(direction, target_position=0, target_tilt=target_tilt)
            self.async_write_ha_state()

    # ------------------------------------------------------------------ events
    def handle_event(self, message: OWNAutomationEvent) -> None:
        """Handle an event message (must never raise: it runs in the event loop)."""
        try:
            LOGGER.debug("%s %s", self._gateway_handler.log_id, message.human_readable_log)

            opening = message.is_opening
            closing = message.is_closing
            if self._inverted:
                opening, closing = closing, opening

            if message.current_position is not None:
                # Advanced actuator: a real position (0 = closed).
                self._finish_movement(int(message.current_position))
                if message.is_closed is not None:
                    self._attr_is_closed = message.is_closed
            elif opening:
                # Someone pressed the keypad (or a scenario ran): the very same
                # two-phase model tracks the movement until it stops.
                if self._moving != OPENING:
                    self._start_movement(OPENING)
            elif closing:
                if self._moving != CLOSING:
                    self._start_movement(CLOSING)
            elif opening is False and closing is False:
                # "Stopped": freeze wherever the estimate got to.
                self._finish_movement(*self._estimate())
        except Exception:  # pragma: no cover - defensive, keeps the session alive
            LOGGER.exception("%s Error handling cover event %s", self._gateway_handler.log_id, message)
            return

        self.async_schedule_update_ha_state()
