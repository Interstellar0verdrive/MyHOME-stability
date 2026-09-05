"""Support for MyHOME covers (WHO 2 shutters, basic and advanced actuators).

Contract F: basic (non-advanced) actuators give no position feedback, they only
report "opening", "closing" and "stopped".  This module estimates the position from
the configured `shutter_run` (full travel time in seconds), exposes it as
`current_cover_position` (0 = closed, 100 = open), derives open/closed from it,
implements `set_cover_position` with a timed stop and restores the last position
across restarts.  Such covers are flagged `assumed_state`.

Advanced actuators report a real position through dimension 10; OWNd maps
`position == 0` to *closed* (`OWNAutomationEvent`), which matches the HA convention,
so their value is used verbatim.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
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
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from OWNd.message import (
    OWNAutomationCommand,
    OWNAutomationEvent,
)

from .const import (
    CONF_ADVANCED_SHUTTER,
    CONF_BUS_INTERFACE,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_MODEL,
    CONF_ENTITY,
    CONF_ENTITY_NAME,
    CONF_ICON,
    CONF_INVERTED,
    CONF_MANUFACTURER,
    CONF_PLATFORMS,
    CONF_SHUTTER_RUN,
    CONF_WHERE,
    CONF_WHO,
    DEFAULT_SHUTTER_RUN,
    DOMAIN,
    LOGGER,
)
from .gateway import MyHOMEGatewayHandler
from .myhome_device import MyHOMEEntity, address_attributes

# How often the estimated position is pushed to Home Assistant while the cover moves.
POSITION_TICK = timedelta(seconds=1)

OPENING = "opening"
CLOSING = "closing"


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
        self._full_where = f"{self._where}#4#{self._interface}" if self._interface is not None else self._where

        try:
            self._attr_device_class = CoverDeviceClass(str(device_class).lower())
        except ValueError:
            self._attr_device_class = CoverDeviceClass.SHUTTER
        if icon is not None:
            self._attr_icon = icon

        self._advanced = bool(advanced)
        # Contract A guarantees a float >= 1; fall back to the schema default anyway.
        self._shutter_run = float(shutter_run or DEFAULT_SHUTTER_RUN)
        self._inverted = bool(inverted)

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        # Basic actuators never report their position: everything below the
        # `_estimated_position` line is an assumption (Contract F).
        self._attr_assumed_state = not self._advanced

        self._attr_extra_state_attributes = address_attributes(where, self._interface)
        if not self._advanced:
            self._attr_extra_state_attributes["Shutter run"] = self._shutter_run

        self._attr_current_cover_position: int | None = None
        self._attr_is_closed: bool | None = None

        # Movement bookkeeping for the time-based estimate.
        self._moving: str | None = None
        self._move_started_at: datetime | None = None
        self._move_start_position: int | None = None
        self._target_position: int | None = None
        self._stop_timer = None
        self._tick_unsub = None

    # ------------------------------------------------------------------ state
    @property
    def current_cover_position(self) -> int | None:
        """Position of the cover (0 closed, 100 open).

        Advanced actuators report it; for basic ones it is extrapolated from the
        movement start time and `shutter_run`.
        """
        if self._advanced:
            return self._attr_current_cover_position
        return self._estimated_position()

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
        """Closed when the (estimated) position reached 0 (plat-07)."""
        position = self.current_cover_position
        if position is None:
            return self._attr_is_closed
        return position == 0

    def _estimated_position(self) -> int | None:
        """Extrapolate the position from the running movement."""
        if self._moving is None or self._move_started_at is None or self._move_start_position is None:
            return self._attr_current_cover_position
        elapsed = (dt_util.utcnow() - self._move_started_at).total_seconds()
        travelled = elapsed / self._shutter_run * 100
        if self._moving == CLOSING:
            travelled = -travelled
        return int(max(0, min(100, round(self._move_start_position + travelled))))

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
    def _start_movement(self, direction: str, target: int | None = None) -> None:
        """Start (or restart) the time-based estimate in `direction`.

        `target` is set only when the movement must be stopped by us
        (`set_cover_position`); otherwise the actuator stops at the end of its run.
        """
        position = self.current_cover_position
        self._cancel_timers()
        if position is None:
            # Nothing known yet: assume the opposite end so that a full travel
            # settles on the correct position.
            position = 0 if direction == OPENING else 100

        self._move_start_position = position
        self._move_started_at = dt_util.utcnow()
        self._moving = direction
        self._target_position = target

        end_position = target if target is not None else (100 if direction == OPENING else 0)
        distance = abs(end_position - position)
        if distance == 0:
            self._finish_movement(end_position)
            return
        duration = distance / 100 * self._shutter_run

        self._stop_timer = async_call_later(self.hass, duration, self._async_movement_deadline)
        self._tick_unsub = async_track_time_interval(self.hass, self._async_position_tick, POSITION_TICK)

    @callback
    def _finish_movement(self, position: int | None) -> None:
        """Stop estimating and freeze the position."""
        self._cancel_timers()
        self._moving = None
        self._move_started_at = None
        self._move_start_position = None
        self._target_position = None
        if position is not None:
            self._attr_current_cover_position = position
            self._attr_is_closed = position == 0

    @callback
    def _async_position_tick(self, now: datetime) -> None:
        """Push the estimated position to HA while the cover moves."""
        self.async_write_ha_state()

    async def _async_movement_deadline(self, now: datetime) -> None:
        """The cover reached its target (or the end of its run)."""
        self._stop_timer = None
        target = self._target_position
        end_position = target if target is not None else (100 if self._moving == OPENING else 0)
        needs_stop = target is not None
        self._finish_movement(end_position)
        if needs_stop:
            await self._gateway_handler.send(OWNAutomationCommand.stop_shutter(self._full_where))
        self.async_write_ha_state()

    # ------------------------------------------------------------------ lifecycle
    async def async_added_to_hass(self) -> None:
        """Register, request the status and restore the last known position."""
        await super().async_added_to_hass()
        if self._advanced or self._attr_current_cover_position is not None:
            return
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        position = last_state.attributes.get(ATTR_CURRENT_POSITION)
        if position is None:
            if last_state.state == CoverState.CLOSED:
                position = 0
            elif last_state.state == CoverState.OPEN:
                position = 100
        if position is not None:
            self._attr_current_cover_position = int(position)
            self._attr_is_closed = self._attr_current_cover_position == 0
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending timers before the entity goes away."""
        self._cancel_timers()
        await super().async_will_remove_from_hass()

    # ------------------------------------------------------------------ commands
    async def async_update(self) -> None:
        """Ask the gateway for the current state (also called on entity add)."""
        await self._gateway_handler.send_status_request(OWNAutomationCommand.status(self._full_where))

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        command = OWNAutomationCommand.lower_shutter if self._inverted else OWNAutomationCommand.raise_shutter
        if await self._gateway_handler.send(command(self._full_where)) and not self._advanced:
            self._start_movement(OPENING)
            self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        command = OWNAutomationCommand.raise_shutter if self._inverted else OWNAutomationCommand.lower_shutter
        if await self._gateway_handler.send(command(self._full_where)) and not self._advanced:
            self._start_movement(CLOSING)
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover and freeze the estimated position."""
        await self._gateway_handler.send(OWNAutomationCommand.stop_shutter(self._full_where))
        if not self._advanced:
            self._finish_movement(self.current_cover_position)
            self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position.

        Advanced actuators take the position directly; for basic ones the cover is
        moved in the right direction and stopped by a timer (Contract F).
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
        if position == current:
            return

        direction = OPENING if position > current else CLOSING
        command = (
            OWNAutomationCommand.raise_shutter if (direction == OPENING) != self._inverted else OWNAutomationCommand.lower_shutter
        )
        if await self._gateway_handler.send(command(self._full_where)):
            self._start_movement(direction, target=position)
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
                if self._moving != OPENING:
                    self._start_movement(OPENING)
            elif closing:
                if self._moving != CLOSING:
                    self._start_movement(CLOSING)
            elif opening is False and closing is False:
                # "Stopped": freeze wherever the estimate got to.
                self._finish_movement(self.current_cover_position)
        except Exception:  # pragma: no cover - defensive, keeps the session alive
            LOGGER.exception("%s Error handling cover event %s", self._gateway_handler.log_id, message)
            return

        self.async_schedule_update_ha_state()
