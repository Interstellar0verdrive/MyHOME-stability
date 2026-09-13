"""The panel's way in: three read commands over Home Assistant's WebSocket API.

Registered once per Home Assistant run - not once per gateway - from `async_setup`,
behind the same kind of flag the drawings' static path uses, because a command name is
global and registering it twice would mean the second gateway silently replacing the
first one's handler with an identical one.

Every command here is **admin-only**: because the panel is (`require_admin` on the panel
itself in the registration lot), and because a shutter's travel model is a setting rather
than a state - a household member who can open a cover has no business rewriting what
"open" means.

Four of them read, nine of them write and one subscribes. The handlers are deliberately
thin: a write unwraps its frame, calls one function in `panel_write.py`, and sends back
what it is given. Everything a write decides - the refusal while a measurement is
running, the one-at-a-time lock, the undo token, the signal that carries the new numbers
to the shutters without reloading the entry - is decided there, where it can be read
without a socket in it.

**What the answers are not.** They are not translated, not formatted and not rounded for
display: a WebSocket answer has no user in it, and the language is the user's. Tokens
travel; `myhome/calibration/texts` turns them into sentences in the browser, out of the
same seven files the guided flow reads.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .panel_data import (
    async_cover_detail,
    async_overview,
    async_preview,
    async_texts,
    is_advanced_cover,
)
from .panel_schemas import (
    ASSIGN_SCHEMA,
    COVER_DETAIL_SCHEMA,
    COVER_EDIT_SCHEMA,
    COVER_FORGET_SCHEMA,
    ERROR_ADVANCED_COVER,
    ERROR_ENTRY_NOT_LOADED,
    ERROR_UNKNOWN_COVER,
    ERROR_UNKNOWN_ENTRY,
    OVERVIEW_SCHEMA,
    PREVIEW_SCHEMA,
    PROFILE_DELETE_SCHEMA,
    PROFILE_EDIT_SCHEMA,
    PROFILE_RENAME_SCHEMA,
    REORDER_SCHEMA,
    SET_TRAVEL_SCHEMA,
    SUBSCRIBE_SCHEMA,
    TEXTS_SCHEMA,
    UNDO_SCHEMA,
    WS_EVENT_MEASURING,
    WS_EVENT_OVERVIEW,
)
from .panel_write import (
    PanelError,
    async_assign,
    async_cover_edit,
    async_cover_entity_ids,
    async_cover_forget,
    async_measuring,
    async_profile_delete,
    async_profile_edit,
    async_profile_rename,
    async_reorder,
    async_set_travel,
    async_subscribers,
    async_undo,
    async_write,
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
    websocket_api.async_register_command(hass, websocket_preview)
    websocket_api.async_register_command(hass, websocket_assign)
    websocket_api.async_register_command(hass, websocket_reorder)
    websocket_api.async_register_command(hass, websocket_set_travel)
    websocket_api.async_register_command(hass, websocket_cover_edit)
    websocket_api.async_register_command(hass, websocket_cover_forget)
    websocket_api.async_register_command(hass, websocket_profile_edit)
    websocket_api.async_register_command(hass, websocket_profile_rename)
    websocket_api.async_register_command(hass, websocket_profile_delete)
    websocket_api.async_register_command(hass, websocket_undo)
    websocket_api.async_register_command(hass, websocket_subscribe)
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


@websocket_api.require_admin
@websocket_api.websocket_command(PREVIEW_SCHEMA)
@websocket_api.async_response
async def websocket_preview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """What a batch of assignments would come to, with none of them made.

    The review panel's before/after table. It is a read: no lock, no store write, no
    signal, and allowed while a measurement is running exactly as every other read is.
    Each item carries either the answer or the one `translation_key` that stops it, so
    the whole command never refuses for one row's sake - see `panel_data.async_preview`
    for why that is the right shape for this one command and the wrong one for `assign`.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    connection.send_result(msg["id"], async_preview(hass, entry, msg["items"]))


# ----------------------------------------------------------------- the write commands
async def _write(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    what: str,
    work: Callable[[ConfigEntry, Any], Coroutine[Any, Any, dict[str, Any]]],
) -> None:
    """One write, its refusals, and the fresh overview it answers with.

    The whole of the write half's plumbing, once: `panel_write.async_write` takes the
    lock, snapshots the records, runs the command, keeps the undo, tells the shutters
    and rebuilds the overview; the only thing that happens here is turning a refusal
    into a frame. Every refusal carries `translation_domain="myhome"` and an English
    sentence beside the key, so a client is never left with a bare token.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    try:
        result = await async_write(hass, entry, what, work)
    except PanelError as err:
        connection.send_error(
            msg["id"],
            err.code,
            err.message,
            translation_key=err.translation_key,
            translation_domain=DOMAIN,
            translation_placeholders=err.placeholders,
        )
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command(ASSIGN_SCHEMA)
@websocket_api.async_response
async def websocket_assign(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Which shutters follow which profile, and where they sit - in one write."""
    await _write(
        hass,
        connection,
        msg,
        "assign",
        lambda entry, store: async_assign(
            hass,
            entry,
            store,
            assignments=msg["assignments"],
            order=msg.get("order"),
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(REORDER_SCHEMA)
@websocket_api.async_response
async def websocket_reorder(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The order the user dragged them into: one group's, or the whole gateway's."""
    await _write(
        hass,
        connection,
        msg,
        "reorder",
        lambda entry, store: async_reorder(
            hass,
            entry,
            store,
            order=msg["order"],
            group=msg.get("profile"),
            whole="profile" not in msg,
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(SET_TRAVEL_SCHEMA)
@websocket_api.async_response
async def websocket_set_travel(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """How far this window really travels - the number every profile is scaled by."""
    await _write(
        hass,
        connection,
        msg,
        "set_travel",
        lambda entry, store: async_set_travel(
            hass,
            entry,
            store,
            cover_unique_id=msg["cover_unique_id"],
            height=msg["height"],
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(COVER_EDIT_SCHEMA)
@websocket_api.async_response
async def websocket_cover_edit(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """This window's own numbers, typed: `null` for a key is "go back to inheriting"."""
    await _write(
        hass,
        connection,
        msg,
        "cover_edit",
        lambda entry, store: async_cover_edit(
            hass,
            entry,
            store,
            cover_unique_id=msg["cover_unique_id"],
            overrides=msg["overrides"],
            height=msg.get("height"),
            height_given="height" in msg,
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(COVER_FORGET_SCHEMA)
@websocket_api.async_response
async def websocket_cover_forget(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Throw this window's record away, and say what it falls back to."""
    await _write(
        hass,
        connection,
        msg,
        "cover_forget",
        lambda entry, store: async_cover_forget(
            hass,
            entry,
            store,
            cover_unique_id=msg["cover_unique_id"],
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(PROFILE_EDIT_SCHEMA)
@websocket_api.async_response
async def websocket_profile_edit(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The six numbers of one profile, and everybody who follows it."""
    await _write(
        hass,
        connection,
        msg,
        "profile_edit",
        lambda entry, store: async_profile_edit(
            hass,
            entry,
            store,
            name=msg["name"],
            values=msg["values"],
            reference_height=msg["reference_height"],
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(PROFILE_RENAME_SCHEMA)
@websocket_api.async_response
async def websocket_profile_rename(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Another name for a profile, and every follower moved onto it."""
    await _write(
        hass,
        connection,
        msg,
        "profile_rename",
        lambda entry, store: async_profile_rename(
            hass,
            entry,
            store,
            name=msg["name"],
            new_name=msg["new_name"],
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(PROFILE_DELETE_SCHEMA)
@websocket_api.async_response
async def websocket_profile_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Forget a profile, having said which shutters lose it."""
    await _write(
        hass,
        connection,
        msg,
        "profile_delete",
        lambda entry, store: async_profile_delete(
            hass, entry, store, name=msg["name"]
        ),
    )


@websocket_api.require_admin
@websocket_api.websocket_command(UNDO_SCHEMA)
@websocket_api.async_response
async def websocket_undo(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Put back exactly the records the last write replaced.

    A write like any other: it is refused while a measurement is running, it is refused
    while another write is being applied, and it reaches the shutters the same way.
    """
    await _write(
        hass,
        connection,
        msg,
        "undo",
        lambda entry, store: async_undo(
            hass, entry, store, token=msg["undo_token"]
        ),
    )


# ------------------------------------------------------------------ the subscription
@websocket_api.require_admin
@websocket_api.websocket_command(SUBSCRIBE_SCHEMA)
@websocket_api.async_response
async def websocket_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Watch one gateway: the overview after every change, and who is being measured.

    Two things a panel cannot find out by asking again. The overview arrives on
    subscribing and after every successful write and undo - the panel replaces its model
    with it, including the writes another browser tab made, which is what stops two
    people editing the same twelve shutters from each seeing half of it. `measuring`
    arrives whenever a guided calibration takes a shutter or gives it back, which is
    what raises and drops the read-only lock: the panel must not offer to change a
    travel model that something else is in the middle of measuring.

    `measuring` is read off **state changes** of the cover entities and not by polling
    the entity objects: the flow marks the entity and writes its state, so the flag
    reaches here the moment it reaches everybody else.

    The subscription dies with the socket - Home Assistant calls every `unsub` in
    `connection.subscriptions` when the connection closes - and nothing in 0.6.0 outlives
    it, because nothing in 0.6.0 holds a shutter.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    entry_id = entry.entry_id
    subscribers = async_subscribers(hass, entry_id)

    @callback
    def send(event: dict[str, Any]) -> None:
        connection.send_event(msg["id"], event)

    measuring = async_measuring(hass, entry)

    @callback
    def state_changed(_event: Event[EventStateChangedData]) -> None:
        """A cover of this gateway changed: say so only when the measurement did."""
        nonlocal measuring
        now = async_measuring(hass, entry)
        if now != measuring:
            measuring = now
            send({"type": WS_EVENT_MEASURING, **(now or {"cover_unique_id": None, "name": None})})

    subscribers.append(send)
    watching = async_track_state_change_event(
        hass, async_cover_entity_ids(hass, entry), state_changed
    )

    @callback
    def unsubscribe() -> None:
        watching()
        if send in subscribers:
            subscribers.remove(send)

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send({"type": WS_EVENT_OVERVIEW, "overview": async_overview(hass, entry)})


__all__ = ["WS_REGISTERED", "async_register"]
