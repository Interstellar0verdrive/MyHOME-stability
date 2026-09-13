"""The panel's way in: three read commands over Home Assistant's WebSocket API.

Registered once per Home Assistant run - not once per gateway - from `async_setup`,
behind the same kind of flag the drawings' static path uses, because a command name is
global and registering it twice would mean the second gateway silently replacing the
first one's handler with an identical one.

Every command here is **admin-only and read-only**. Admin-only because the panel is
(`require_admin` on the panel itself in the registration lot), and because a shutter's
travel model is a setting rather than a state: a household member who can open a cover
has no business rewriting what "open" means. Read-only because lot 2 is the read half -
the writes, with their reload debouncer, their refusal while a measurement is running
and their undo token, are lot 3, and shipping the reads first is what lets the panel be
built against a contract that cannot change under it.

**What the answers are not.** They are not translated, not formatted and not rounded for
display: a WebSocket answer has no user in it, and the language is the user's. Tokens
travel; `myhome/calibration/texts` turns them into sentences in the browser, out of the
same seven files the guided flow reads.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .panel_data import async_cover_detail, async_overview, async_texts, is_advanced_cover
from .panel_schemas import (
    COVER_DETAIL_SCHEMA,
    ERROR_ADVANCED_COVER,
    ERROR_ENTRY_NOT_LOADED,
    ERROR_UNKNOWN_COVER,
    ERROR_UNKNOWN_ENTRY,
    OVERVIEW_SCHEMA,
    TEXTS_SCHEMA,
)

# One registration per Home Assistant run, however many gateways are configured.
WS_REGISTERED = f"{DOMAIN}_websocket_registered"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the panel's commands, once.

    Idempotent in Home Assistant's own terms - registering a command name twice
    overwrites the first handler with the second - but guarded anyway, so that the count
    of registrations is something a test can assert and a future command with a
    subscription behind it cannot be quietly doubled.
    """
    if hass.data.get(WS_REGISTERED):
        return
    websocket_api.async_register_command(hass, websocket_overview)
    websocket_api.async_register_command(hass, websocket_cover_detail)
    websocket_api.async_register_command(hass, websocket_texts)
    hass.data[WS_REGISTERED] = True


# ------------------------------------------------------------------ the gateway
@callback
def _entry(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> ConfigEntry | None:
    """The gateway this message is about, or None with the refusal already sent.

    `entry_id` is optional and means "the one gateway I have" when it is left out, which
    is the shape of nearly every installation. A gateway that exists but is not loaded
    is a different answer from one that does not exist at all: its shutters are not
    there to be read, and the panel says "not loaded" rather than "not found", because
    the two ask the user to do different things about it.
    """
    entry_id = msg.get("entry_id")
    if entry_id is None:
        loaded = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        if not loaded:
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                "No MyHOME gateway is loaded",
                translation_key=ERROR_UNKNOWN_ENTRY,
                translation_domain=DOMAIN,
            )
            return None
        return loaded[0]

    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            f"No MyHOME gateway with the id {entry_id}",
            translation_key=ERROR_UNKNOWN_ENTRY,
            translation_domain=DOMAIN,
            translation_placeholders={"entry_id": str(entry_id)},
        )
        return None
    if entry.state is not ConfigEntryState.LOADED:
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            f"The gateway {entry.title} is not loaded",
            translation_key=ERROR_ENTRY_NOT_LOADED,
            translation_domain=DOMAIN,
            translation_placeholders={"gateway": entry.title},
        )
        return None
    return entry


# ----------------------------------------------------------------- the commands
@websocket_api.require_admin
@websocket_api.websocket_command(OVERVIEW_SCHEMA)
@websocket_api.async_response
async def websocket_overview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Everything the panel's main screen renders, for one gateway."""
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    connection.send_result(msg["id"], async_overview(hass, entry))


@websocket_api.require_admin
@websocket_api.websocket_command(COVER_DETAIL_SCHEMA)
@websocket_api.async_response
async def websocket_cover_detail(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """One shutter, key by key, with where every number came from."""
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    unique_id = msg["cover_unique_id"]
    detail = async_cover_detail(hass, entry, unique_id)
    if detail is None:
        # A shutter that reports its own position has no travel model to show, which is
        # a refusal and not an absence: `_covers` leaves it out for the same reason
        # every calibration primitive does.
        if is_advanced_cover(hass, entry, unique_id):
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_SUPPORTED,
                f"{unique_id} is an advanced shutter and has no travel model",
                translation_key=ERROR_ADVANCED_COVER,
                translation_domain=DOMAIN,
                translation_placeholders={"cover": str(unique_id)},
            )
            return
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            f"No cover with the unique id {unique_id} on {entry.title}",
            translation_key=ERROR_UNKNOWN_COVER,
            translation_domain=DOMAIN,
            translation_placeholders={"cover": str(unique_id)},
        )
        return
    connection.send_result(msg["id"], detail)


@websocket_api.require_admin
@websocket_api.websocket_command(TEXTS_SCHEMA)
@websocket_api.async_response
async def websocket_texts(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The integration's own sentences, in the nearest language it has.

    Behind `require_admin` like the rest, although it carries no data about anybody's
    house: the panel is admin-only, so an exception here would only be a second door
    into the same room.
    """
    language = msg.get("language") or hass.config.language
    connection.send_result(msg["id"], await async_texts(hass, language))


__all__ = ["WS_REGISTERED", "async_register"]
