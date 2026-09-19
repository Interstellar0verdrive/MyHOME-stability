"""The panel's way in: twenty-four commands over Home Assistant's WebSocket API.

Registered once per Home Assistant run - not once per gateway - from `async_setup`,
behind the same kind of flag the drawings' static path uses, because a command name is
global and registering it twice would mean the second gateway silently replacing the
first one's handler with an identical one.

Every command here is **admin-only**: because the panel is (`require_admin` on the panel
itself in the registration lot), and because a shutter's travel model is a setting rather
than a state - a household member who can open a cover has no business rewriting what
"open" means.

Four of them read, nine of them write, one subscribes, and ten drive the guided
calibration's session (0.6.0 wizard, lot B3). The handlers are deliberately thin: a
write unwraps its frame, calls one function in `panel_write.py`, and sends back what it
is given; a session command finds the gateway's session and calls one method on it.
Everything a write decides - the refusal while a measurement is running, the
one-at-a-time lock, the undo token, the signal that carries the new numbers to the
shutters without reloading the entry - is decided there, and everything a session
decides is decided in `calibration_session.py`, where both can be read without a socket
in them. The one command with a body of its own here is `end_other`, which is about the
*other* thing holding a shutter - an open *Configure* dialog - and therefore about no
session at all.

**What the answers are not.** They are not translated, not formatted and not rounded for
display: a WebSocket answer has no user in it, and the language is the user's. Tokens
travel; `myhome/calibration/texts` turns them into sentences in the browser, out of the
same seven files the guided flow reads.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from . import calibration_session
from .calibration_session import CalibrationSession, async_start, current
from .const import DOMAIN
from .panel_data import (
    async_cover_detail,
    async_overview,
    async_preview,
    async_texts,
    calibrating_now,
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
    ERROR_UNKNOWN_SESSION,
    OVERVIEW_SCHEMA,
    PREVIEW_SCHEMA,
    PROFILE_DELETE_SCHEMA,
    PROFILE_EDIT_SCHEMA,
    PROFILE_RENAME_SCHEMA,
    REORDER_SCHEMA,
    SESSION_ACT_SCHEMA,
    SESSION_ATTACH_SCHEMA,
    SESSION_CANCEL_SCHEMA,
    SESSION_CAPABILITIES,
    SESSION_END_OTHER_SCHEMA,
    SESSION_GET_SCHEMA,
    SESSION_HEARTBEAT_SCHEMA,
    SESSION_LEAVE_SCHEMA,
    SESSION_SAVE_SCHEMA,
    SESSION_START_SCHEMA,
    SESSION_STOP_SCHEMA,
    SET_TRAVEL_SCHEMA,
    SUBSCRIBE_SCHEMA,
    TEXTS_SCHEMA,
    UNDO_SCHEMA,
    WS_EVENT_MEASURING,
    WS_EVENT_OVERVIEW,
    WS_EVENT_SESSION,
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
    # The guided calibration's session: ten commands behind the same flag, because a
    # command name is global whichever half of the panel it belongs to.
    websocket_api.async_register_command(hass, websocket_session_get)
    websocket_api.async_register_command(hass, websocket_session_start)
    websocket_api.async_register_command(hass, websocket_session_attach)
    websocket_api.async_register_command(hass, websocket_session_heartbeat)
    websocket_api.async_register_command(hass, websocket_session_act)
    websocket_api.async_register_command(hass, websocket_session_stop)
    websocket_api.async_register_command(hass, websocket_session_leave)
    websocket_api.async_register_command(hass, websocket_session_cancel)
    websocket_api.async_register_command(hass, websocket_session_save)
    websocket_api.async_register_command(hass, websocket_session_end_other)
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

    `profile_values` is the profile card's half of the same question - "if this profile
    said these numbers instead, what would its followers run on?" - and is as read-only
    as the rest: it replaces numbers in a copy of the profile mapping and reaches
    nothing else.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    connection.send_result(
        msg["id"], async_preview(hass, entry, msg["items"], msg.get("profile_values"))
    )


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

    `session` (0.6.0 wizard) is the third: the whole snapshot of the gateway's guided
    calibration, on subscribing and after every transition of it. It is on this
    subscription rather than on one of its own because the panel already keeps this one
    alive across reconnections, and two would be two things to keep alive.

    The subscription dies with the socket - Home Assistant calls every `unsub` in
    `connection.subscriptions` when the connection closes - and the **session does
    not**: it lives on the server precisely so that closing a tab or locking a phone
    does not end a measurement. Unsubscribing takes this socket off the session's list
    and off the gateway's, and stops there.
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
    watcher = _watch_the_session(hass, entry_id, send)

    @callback
    def unsubscribe() -> None:
        watching()
        _forget_the_session_watcher(hass, entry_id, watcher)
        if send in subscribers:
            subscribers.remove(send)

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    send({"type": WS_EVENT_OVERVIEW, "overview": async_overview(hass, entry)})
    session = current(hass, entry)
    send({"type": WS_EVENT_SESSION, "session": None if session is None else session.snapshot()})


# ============================================================ the calibration session
# Ten commands (SPEC §4.1, `docs/panel-websocket-api.md` §11), admin-only and
# `async_response` like the rest. Every one of them is three lines and a call: the
# gateway, the session, the method. Nothing about a calibration is decided here -
# what may be acted on, who owns it, what a refusal is - because a session that could
# only be read through a socket could only be tested through one.
#
# `entry_id` is **required** on all ten, reads included: a session is always one
# gateway's, and "the gateway I have" is a shape that belongs to a panel opening for
# the first time and not to a measurement in progress.


@dataclass(slots=True)
class _SessionWatcher:
    """One open socket's place in the queue for a gateway's session events.

    A session comes and goes under a subscription that outlives it, so what a socket
    holds is a place in this per-gateway list, and `_attach_the_session_watchers` hooks
    the list onto a session the moment `start` makes one. `drop` is what the session
    handed back when this watcher was hooked onto it, or `None` when there was nothing
    to hook onto.
    """

    send: Callable[[dict[str, Any]], None]
    drop: Callable[[], None] | None = None

    @callback
    def push(self, snapshot: dict[str, Any] | None) -> None:
        self.send({"type": WS_EVENT_SESSION, "session": snapshot})

    @callback
    def hook(self, session: CalibrationSession) -> None:
        """Follow this session instead of whatever was being followed before."""
        self.unhook()
        self.drop = session.subscribe(self.push)

    @callback
    def unhook(self) -> None:
        if self.drop is not None:
            self.drop()
            self.drop = None


# The watchers of each gateway, by entry id. Keyed per gateway like the overview's
# subscribers, and for the same reason: two gateways are two panels.
SESSION_WATCHERS_DATA_KEY = f"{DOMAIN}_calibration_session_watchers"


@callback
def _session_watchers(hass: HomeAssistant, entry_id: str) -> list[_SessionWatcher]:
    by_entry: dict[str, list[_SessionWatcher]] = hass.data.setdefault(
        SESSION_WATCHERS_DATA_KEY, {}
    )
    return by_entry.setdefault(entry_id, [])


@callback
def _watch_the_session(
    hass: HomeAssistant, entry_id: str, send: Callable[[dict[str, Any]], None]
) -> _SessionWatcher:
    """Put one socket in the queue, hooked onto the session there is, if there is one."""
    watcher = _SessionWatcher(send)
    _session_watchers(hass, entry_id).append(watcher)
    entry = hass.config_entries.async_get_entry(entry_id)
    session = None if entry is None else current(hass, entry)
    if session is not None:
        watcher.hook(session)
    return watcher


@callback
def _forget_the_session_watcher(
    hass: HomeAssistant, entry_id: str, watcher: _SessionWatcher
) -> None:
    """A socket closed: it stops hearing about the session, and the session goes on."""
    watcher.unhook()
    watchers = _session_watchers(hass, entry_id)
    if watcher in watchers:
        watchers.remove(watcher)


@callback
def _attach_the_session_watchers(
    hass: HomeAssistant, entry: ConfigEntry, session: CalibrationSession
) -> None:
    """Hook every open panel of this gateway onto a session that has just been made.

    Called from `start`, which is the only thing that makes one. The session's own
    first publication happened inside `async_start`, before anybody could be listening,
    so the snapshot is pushed once here: "on subscribing, and after every transition"
    (§11.4), and a start is a transition.
    """
    snapshot = session.snapshot()
    for watcher in list(_session_watchers(hass, entry.entry_id)):
        watcher.hook(session)
        watcher.push(snapshot)


@callback
def _refuse(
    connection: websocket_api.ActiveConnection, msg: dict[str, Any], err: PanelError
) -> None:
    """One refusal, as a frame: the key, the placeholders and the English sentence."""
    connection.send_error(
        msg["id"],
        err.code,
        err.message,
        translation_key=err.translation_key,
        translation_domain=DOMAIN,
        translation_placeholders=err.placeholders,
    )


@callback
def _the_session(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    entry: ConfigEntry,
) -> CalibrationSession | None:
    """The session this message names, or None with `unknown_session` already sent.

    A gateway holds one session at a time, so "the session with this id" is "the
    gateway's session, if that is the one you mean". An id that names another - a tab
    left open across a cancellation and a fresh start - is `not_found` and not somebody
    else's session quietly acted upon.
    """
    session = current(hass, entry)
    if session is not None and session.session_id == msg["session_id"]:
        return session
    connection.send_error(
        msg["id"],
        websocket_api.ERR_NOT_FOUND,
        "No calibration session with that id on this gateway",
        translation_key=ERROR_UNKNOWN_SESSION,
        translation_domain=DOMAIN,
    )
    return None


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_GET_SCHEMA)
@websocket_api.async_response
async def websocket_session_get(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """What this gateway is measuring, and what this backend can measure.

    A read: it never starts anything. `capabilities` travels with it because the
    published contract (§2.5) asks a backend that offers less than the whole
    conversation to say so, rather than running a shorter plan under the same name -
    and the event does not carry it, so a client that only subscribed would have to
    guess.

    The two keys that can be less than the contract's whole are **read off the
    controller** and not copied: `IMPLEMENTED_PATHS` and `IMPLEMENTED_LEVELS` are the
    tables the conversation itself narrows `actions` by and refuses a `start` against,
    so answering the contract's full lists beside them would be the declaration
    contradicting the thing it declares. Through the module rather than by name, so that
    what is answered is what those tables say *now* and not what they said when this
    module was imported. The rest of the answer is the contract's, because the rest is
    what this backend does.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    session = current(hass, entry)
    connection.send_result(
        msg["id"],
        {
            "session": None if session is None else session.snapshot(),
            "capabilities": {
                **SESSION_CAPABILITIES,
                "paths": list(calibration_session.IMPLEMENTED_PATHS),
                "levels": list(calibration_session.IMPLEMENTED_LEVELS),
            },
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_START_SCHEMA)
@websocket_api.async_response
async def websocket_session_start(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Open a session on one shutter. It moves nothing and skips no briefing."""
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    try:
        session = await async_start(
            hass,
            entry,
            cover_unique_id=msg["cover_unique_id"],
            client_id=msg["client_id"],
            path=msg.get("path"),
            profile=msg.get("profile"),
            scope=msg.get("scope"),
        )
    except PanelError as err:
        _refuse(connection, msg, err)
        return
    _attach_the_session_watchers(hass, entry, session)
    connection.send_result(msg["id"], {"session": session.snapshot()})


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_ATTACH_SCHEMA)
@websocket_api.async_response
async def websocket_session_attach(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Read the session as this client, taking it over where that is allowed."""
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    session = _the_session(hass, connection, msg, entry)
    if session is None:
        return
    try:
        answer = session.attach(msg["client_id"], msg.get("claim", False))
    except PanelError as err:
        _refuse(connection, msg, err)
        return
    connection.send_result(msg["id"], {"session": answer})


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_HEARTBEAT_SCHEMA)
@websocket_api.async_response
async def websocket_session_heartbeat(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Keep the owner present. Never a transition, never a claim, never a refusal.

    Not a refusal *of ownership*, that is: a client that is no longer the owner is told
    `owner: false` rather than refused, so that losing the session is a state the panel
    draws instead of a failure it reports. An id that names no session of this gateway
    is still `unknown_session`, because that is a client talking about something that
    is not there.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    session = _the_session(hass, connection, msg, entry)
    if session is None:
        return
    connection.send_result(msg["id"], session.heartbeat(msg["client_id"]))


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_ACT_SCHEMA)
@websocket_api.async_response
async def websocket_session_act(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """One step of the conversation, against the revision the client last read."""
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    session = _the_session(hass, connection, msg, entry)
    if session is None:
        return
    try:
        answer = await session.async_act(
            msg["client_id"], msg["revision"], msg["action"], msg.get("value")
        )
    except PanelError as err:
        _refuse(connection, msg, err)
        return
    connection.send_result(msg["id"], {"session": answer})


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_STOP_SCHEMA)
@websocket_api.async_response
async def websocket_session_stop(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Write a stop frame now: the one verb of this API that touches the shutter."""
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    session = _the_session(hass, connection, msg, entry)
    if session is None:
        return
    try:
        answer = await session.async_stop(msg["client_id"])
    except PanelError as err:
        _refuse(connection, msg, err)
        return
    connection.send_result(msg["id"], {"session": answer})


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_LEAVE_SCHEMA)
@websocket_api.async_response
async def websocket_session_leave(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Detach this client. Nothing is written and nothing is stopped.

    Sent as a page goes away, which is why a session that is no longer there answers
    `{session: null}` instead of `unknown_session`: a refusal on a message nobody is
    waiting for is noise, and the tab it would be sent to has already gone.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    session = current(hass, entry)
    if session is None or session.session_id != msg["session_id"]:
        connection.send_result(msg["id"], {"session": None})
        return
    connection.send_result(msg["id"], {"session": session.leave(msg["client_id"])})


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_CANCEL_SCHEMA)
@websocket_api.async_response
async def websocket_session_cancel(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Throw the provisional values away and end. The shutter is not stopped.

    The way out that always works (SPEC §5.2, "Annulla mai silenzioso"): no revision,
    never refused for concurrency, idempotent, and with `force: true` it ends the
    session whoever owns it. `session_id` may be left out and then means "the session
    this gateway has, whichever it is", which is what the overview's banner sends.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    session = current(hass, entry)
    if session is None:
        connection.send_result(msg["id"], {"session": None, "already_ended": True})
        return
    named = msg.get("session_id")
    if named is not None and named != session.session_id:
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            "No calibration session with that id on this gateway",
            translation_key=ERROR_UNKNOWN_SESSION,
            translation_domain=DOMAIN,
        )
        return
    try:
        answer = await session.async_cancel(msg["client_id"], msg.get("force", False))
    except PanelError as err:
        _refuse(connection, msg, err)
        return
    connection.send_result(msg["id"], answer)


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_SAVE_SCHEMA)
@websocket_api.async_response
async def websocket_session_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Write the result, once, and only from the review.

    It goes through `panel_write.async_write` like every other write of this API - one
    write at a time per gateway, the shutters picking the numbers up in place without a
    reload, every subscriber given the new overview - with the two differences the
    session earns: it is not refused by the calibration it belongs to, and it leaves no
    undo token.

    The answer's `overview` is the one the session publishes when it ends and not the
    one the write built - the write's was built while the session still held the shutter
    - and the session publishes it to every open panel itself, at this transition and at
    the five others. All of that is `CalibrationSession._publish_the_overview`, where it
    belongs: a client that calls `async_save` without a socket in front of it gets the
    same answer.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    session = _the_session(hass, connection, msg, entry)
    if session is None:
        return
    try:
        answer = await session.async_save(msg["client_id"], msg["revision"], msg["target"])
    except PanelError as err:
        _refuse(connection, msg, err)
        return
    connection.send_result(msg["id"], answer)


@websocket_api.require_admin
@websocket_api.websocket_command(SESSION_END_OTHER_SCHEMA)
@websocket_api.async_response
async def websocket_session_end_other(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Close the *Configure* dialogs of this gateway, and say what that left.

    The one session command with a body rather than a call, because what it acts on is
    not a session: it is the other thing that can be holding a shutter. Aborting an
    options flow runs the dialog's `async_remove`, which gives the shutter back
    **without stopping it** and, if that dialog had saved something, schedules the
    reload it always schedules when it closes. The panel says both of those before it
    asks for confirmation.

    Afterwards the shutter can still be in calibration, and then it was never the
    dialog: it is the 0.4.2 action, whose run nothing here may cut short.
    `still_calibrating` says so, and the screen asks the user to wait for the run to
    finish rather than offering a button that would do nothing.
    """
    entry = _entry(hass, connection, msg)
    if entry is None:
        return
    options = hass.config_entries.options
    # An options flow's handler *is* the entry id, so this is "every Configure dialog
    # open on this gateway" and never one open on another - the same call and the same
    # pair of methods `tests/test_calibration_flow.py` closes its own dialogs with.
    flows = list(options.async_progress_by_handler(entry.entry_id))
    for flow in flows:
        options.async_abort(flow["flow_id"])
    connection.send_result(
        msg["id"],
        {
            "flows_aborted": len(flows),
            "still_calibrating": bool(calibrating_now(hass, entry)),
            "overview": async_overview(hass, entry),
        },
    )


__all__ = ["SESSION_WATCHERS_DATA_KEY", "WS_REGISTERED", "async_register"]
