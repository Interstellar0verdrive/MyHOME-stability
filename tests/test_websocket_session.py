"""The session on the socket: ten commands, one event, and the fixture made real.

The controller is `tests/test_calibration_session.py`'s subject; this file is about the
**door** it is reached through. Three things, in order:

* every command answered - the successes, the malformed frames, the refusals of SPEC
  §4.6 - through a real `hass_ws_client`, because a schema applied by hand is not the
  schema Home Assistant applies;
* the subscription: `session` arrives on subscribing and after every transition, in
  `revision` order, and closing the socket takes the subscriber away and **leaves the
  session running** - which is the whole reason the session lives on the server;
* `tests/fixtures/panel_session_examples.json`, regenerated from the controller instead
  of written by hand. It is the frontend's stand-in server (`npm run session`,
  `test/wizard-model.test.ts`, the harness), and a hand-written likeness of a payload is
  the one kind of fixture that can be wrong in every direction at once.

The bench is `panel_overview_example.json`'s: the same two shutters, the same profile
and the same numbers, so that a review's `before` column really is what the panel's
overview shows for that window on the same page.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import voluptuous as vol
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components import websocket_api
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.components.websocket_api import const as ws_const
from homeassistant.const import CONF_MAC, STATE_CLOSING, STATE_OPENING
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.myhome import calibration_session
from custom_components.myhome.calibration import REASON_NO_ECHO, CalibrationError
from custom_components.myhome.calibration_flow import MOVED_IDLE_TIMEOUT_SEC
from custom_components.myhome.calibration_session import CalibrationSession, async_start, current
from custom_components.myhome.calibration_store import loaded_store
from custom_components.myhome.const import CONF_PLATFORMS, DOMAIN
from custom_components.myhome.panel_schemas import (
    SESSION_ACT_SCHEMA,
    SESSION_ANSWER_KEYS,
    SESSION_CANCEL_KEYS,
    SESSION_CAPABILITIES,
    SESSION_END_OTHER_KEYS,
    SESSION_GET_KEYS,
    SESSION_HEARTBEAT_KEYS,
    SESSION_KEYS,
    SESSION_LEVELS,
    SESSION_OVERVIEW_KEYS,
    SESSION_PATHS,
    SESSION_SAVE_KEYS,
    WS_EVENT_OVERVIEW,
    WS_EVENT_SESSION,
    WS_SESSION_COMMANDS,
    WS_TYPE_OVERVIEW,
    WS_TYPE_SESSION_ACT,
    WS_TYPE_SESSION_ATTACH,
    WS_TYPE_SESSION_CANCEL,
    WS_TYPE_SESSION_END_OTHER,
    WS_TYPE_SESSION_GET,
    WS_TYPE_SESSION_HEARTBEAT,
    WS_TYPE_SESSION_LEAVE,
    WS_TYPE_SESSION_SAVE,
    WS_TYPE_SESSION_START,
    WS_TYPE_SESSION_STOP,
    WS_TYPE_SUBSCRIBE,
)
from custom_components.myhome.websocket_api import SESSION_WATCHERS_DATA_KEY

from .helpers_calibration import CLOSING, HEIGHT, OPENING, SLAT, FakeRunner, ascent_cm, descent_cm
from .helpers_platforms import entity_object, setup_myhome
from .test_calibration_session import PATH_A_BASIC, Act, act, check_the_snapshot, walk
from .test_panel_two_gateways import two_gateways
from .test_websocket_api import (
    ADVANCED,
    CALIBRATION,
    EXAMPLE_ENTRY_ID,
    FIRST,
    SECOND,
    YAML,
    refused,
    result,
)

# The two browser tabs of the fixture, and the identifiers it normalises the volatile
# ones to. `_example` in the committed file carries all three.
CLIENT = "3b0c7e1a-5d2f-4a8e-9c61-0e7f4b2d9a10"
OTHER_CLIENT = "8d41f6b2-7c3e-4f95-a0d8-2b6e9c1f7e33"
EXAMPLE_SESSION_ID = "6f1d2c3b4a5e4f708192a3b4c5d6e7f8"

DEVICE_KEY = "2-81"
ENTITY = "cover.hallway_shutter"
EXAMPLES = Path(__file__).resolve().parent / "fixtures" / "panel_session_examples.json"


def the_fixture() -> dict[str, Any]:
    return json.loads(EXAMPLES.read_text(encoding="utf-8"))


async def open_session(
    hass: HomeAssistant, entry, cover: str = FIRST, **kwargs
) -> CalibrationSession:
    """Start the gateway's session on one shutter and let its screen settle."""
    session = await async_start(hass, entry, cover_unique_id=cover, client_id=CLIENT, **kwargs)
    await hass.async_block_till_done()
    return session


async def subscribed(client, entry_id: str) -> int:
    """Subscribe, swallow the two events that always open one, and answer with the id."""
    await client.send_json_auto_id({"type": WS_TYPE_SUBSCRIBE, "entry_id": entry_id})
    answer = await client.receive_json()
    assert answer["success"], answer
    assert (await client.receive_json())["event"]["type"] == WS_EVENT_OVERVIEW
    assert (await client.receive_json())["event"]["type"] == WS_EVENT_SESSION
    return answer["id"]


async def sent(client, payload: dict[str, Any]) -> int:
    """Send one frame and hand back the id the client gave it."""
    await client.send_json_auto_id(payload)
    return int(payload["id"])


async def answered(
    client,
    msg_id: int,
    seen: list[dict[str, Any]] | None = None,
    overviews: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The answer to one command, reading past the events that overtake it.

    A subscription and a command share one socket, and the events a command causes go
    out **before** its own answer: `send_result` is the last thing a handler does. So a
    test that has both open reads until it finds its id, keeping the session snapshots
    it stepped over when it was asked to.
    """
    while True:
        message = await client.receive_json()
        if message.get("type") == "event":
            if seen is not None and message["event"]["type"] == WS_EVENT_SESSION:
                seen.append(message["event"]["session"])
            if overviews is not None and message["event"]["type"] == WS_EVENT_OVERVIEW:
                overviews.append(message["event"]["overview"])
            continue
        assert message["id"] == msg_id, message
        assert message["success"], message
        return message["result"]


async def started_over_the_socket(
    client, hass, entry, seen=None, overviews=None, **fields
) -> CalibrationSession:
    """Open the session the way the panel opens one, and hand back the controller's.

    Through the socket on purpose wherever a subscription is watching: the ten commands
    are what hooks an open panel onto a session that did not exist when it subscribed,
    so a test that called `async_start` directly would be testing a path no browser
    takes.
    """
    msg_id = await sent(
        client,
        {
            "type": WS_TYPE_SESSION_START,
            "entry_id": entry.entry_id,
            "cover_unique_id": FIRST,
            "client_id": CLIENT,
            **fields,
        },
    )
    answer = await answered(client, msg_id, seen, overviews)
    await hass.async_block_till_done()
    session = current(hass, entry)
    assert session is not None and session.session_id == answer["session"]["session_id"]
    return session


async def session_events(
    client,
    sub_id: int,
    seen: list[dict[str, Any]],
    upto: int,
    overviews: list[dict[str, Any]] | None = None,
) -> None:
    """Read until the subscription has carried the snapshot of revision `upto`.

    A session holds its shutter, so `measuring` travels down the same subscription and
    is stepped over here: what this file is about is the `session` events and their
    order.
    """
    while len(seen) < upto:
        message = await client.receive_json()
        assert message["id"] == sub_id, message
        if message["event"]["type"] == WS_EVENT_SESSION:
            seen.append(message["event"]["session"])
        elif overviews is not None and message["event"]["type"] == WS_EVENT_OVERVIEW:
            overviews.append(message["event"]["overview"])


# ======================================================================= the commands
async def test_the_ten_commands_are_registered_under_the_one_flag(
    hass: HomeAssistant, tmp_path
) -> None:
    """A command name is global, so the session's ten go up with the other fourteen."""
    async with setup_myhome(hass, tmp_path, YAML) as (_entry, _commands):
        registered = hass.data["websocket_api"]
        for command in WS_SESSION_COMMANDS:
            assert command in registered


async def test_get_answers_nothing_and_what_this_backend_can_do(
    hass: HomeAssistant, tmp_path, hass_ws_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A gateway with no session answers `null` - and still says what it offers.

    `capabilities` is the contract's §2.5 question, and it is answered by `get` and by
    nothing else: a client that only subscribed would have to assume, and assuming is
    how a panel offers a path the backend cannot walk.

    Mutation caught: answering `capabilities` only when there is a session; leaving it
    out of the answer.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        client = await hass_ws_client(hass)
        answer = await result(client, type=WS_TYPE_SESSION_GET, entry_id=entry.entry_id)
        assert tuple(answer) == SESSION_GET_KEYS
        assert answer["session"] is None
        # The paths and the levels are what the conversation can really walk, read off
        # the controller's own tables: `actions` is narrowed by them and a `start` is
        # refused against them, so a declaration copied from the contract would be the
        # backend contradicting itself the moment the two differ. Everything else is
        # the contract's, because everything else is what this backend does.
        assert answer["capabilities"] == {
            **SESSION_CAPABILITIES,
            "paths": list(calibration_session.IMPLEMENTED_PATHS),
            "levels": list(calibration_session.IMPLEMENTED_LEVELS),
        }
        assert set(answer["capabilities"]["paths"]) <= set(SESSION_PATHS)
        assert set(answer["capabilities"]["levels"]) <= set(SESSION_LEVELS)

        # ...and it says less as long as the backend does less: with every path walked
        # it is the contract's own list, whole.
        monkeypatch.setattr(calibration_session, "IMPLEMENTED_PATHS", SESSION_PATHS)
        monkeypatch.setattr(calibration_session, "IMPLEMENTED_LEVELS", SESSION_LEVELS)
        answer = await result(client, type=WS_TYPE_SESSION_GET, entry_id=entry.entry_id)
        assert answer["capabilities"] == SESSION_CAPABILITIES


async def test_start_opens_a_session_that_get_then_answers(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The first screen, over the socket, with nothing moved and nothing written."""
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_SESSION_START,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            client_id=CLIENT,
            path="path_a",
        )
        assert tuple(answer) == SESSION_ANSWER_KEYS
        snapshot = answer["session"]
        assert tuple(snapshot) == SESSION_KEYS
        assert snapshot["step"] == "path_a"
        assert snapshot["owner"]["client_id"] == CLIENT
        assert runner.log == []

        again = await result(client, type=WS_TYPE_SESSION_GET, entry_id=entry.entry_id)
        assert again["session"]["session_id"] == snapshot["session_id"]
        assert runner.log == []
        await current(hass, entry).async_cancel(CLIENT)


async def test_every_verb_comes_back_through_the_socket(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """`attach`, `heartbeat`, `act`, `stop`, `leave` and `cancel`, each answering its shape.

    One session walked over the wire rather than six tests of one frame each: what is
    being held is that the handlers are thin - the answer is the controller's, whole and
    unrewrapped - and that every answer is exactly the tuple of keys the contract
    declares for it.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        started = await result(
            client,
            type=WS_TYPE_SESSION_START,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            client_id=CLIENT,
        )
        session_id = started["session"]["session_id"]
        common = {"entry_id": entry.entry_id, "session_id": session_id, "client_id": CLIENT}

        attached = await result(client, type=WS_TYPE_SESSION_ATTACH, **common)
        assert tuple(attached) == SESSION_ANSWER_KEYS
        assert attached["session"]["owner"]["client_id"] == CLIENT

        beat = await result(client, type=WS_TYPE_SESSION_HEARTBEAT, **common)
        assert tuple(beat) == SESSION_HEARTBEAT_KEYS
        assert beat["owner"] is True
        assert beat["present_until"] is not None
        # A heartbeat is not a transition: the revision has not moved.
        assert (await result(client, type=WS_TYPE_SESSION_GET, entry_id=entry.entry_id))[
            "session"
        ]["revision"] == attached["session"]["revision"]

        acted = await result(
            client,
            type=WS_TYPE_SESSION_ACT,
            **common,
            revision=attached["session"]["revision"],
            action="path_a",
        )
        assert acted["session"]["step"] == "path_a"

        stopped = await result(client, type=WS_TYPE_SESSION_STOP, **common)
        assert tuple(stopped) == SESSION_ANSWER_KEYS
        assert runner.stops == 1

        left = await result(client, type=WS_TYPE_SESSION_LEAVE, **common)
        # Nothing has been measured, so leaving ends it - and answers how it ended.
        assert left["session"]["outcome"]["reason"] == "left"

        cancelled = await result(
            client, type=WS_TYPE_SESSION_CANCEL, entry_id=entry.entry_id, client_id=CLIENT
        )
        assert tuple(cancelled) == SESSION_CANCEL_KEYS
        assert cancelled["already_ended"] is True


async def test_cancel_ends_the_session_it_names_and_never_the_one_that_replaced_it(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Named, it is one session; unnamed, it is whichever one the gateway has.

    Both are wanted, and they are different messages. "End it" from the overview's
    banner carries no `session_id`, because the banner is about a gateway; the wizard
    carries the one it is showing. A tab left open across a cancellation and a fresh
    start sends the id of a calibration that is over, and ending the one that took its
    place - somebody else's, on another shutter - is exactly what the id is there to
    prevent.

    Mutation caught: cancelling the gateway's session whatever `session_id` says.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        session = await open_session(hass, entry)

        error = await refused(
            client,
            type=WS_TYPE_SESSION_CANCEL,
            entry_id=entry.entry_id,
            client_id=CLIENT,
            session_id=EXAMPLE_SESSION_ID,
        )
        assert (error["code"], error["translation_key"]) == (
            ws_const.ERR_NOT_FOUND,
            "unknown_session",
        )
        assert session.ended is False

        # ...and with no id at all it is the gateway's, whichever it is.
        answer = await result(
            client, type=WS_TYPE_SESSION_CANCEL, entry_id=entry.entry_id, client_id=CLIENT
        )
        assert answer["already_ended"] is False
        assert answer["session"]["outcome"]["reason"] == "cancelled"
        assert session.ended is True


async def test_a_value_that_cannot_be_a_reading_is_a_form_error_and_not_a_refusal(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """The user's mistake is the user's to correct, and the socket says so with a screen.

    Mutation caught: refusing a bad reading (the panel would show a red banner and lose
    the field), or accepting `nan` (every number three screens later becomes `nan`).
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, PATH_A_BASIC[:10], freezer=freezer)
        assert session.snapshot()["step"] == "height"

        client = await hass_ws_client(hass)
        common = {
            "entry_id": entry.entry_id,
            "session_id": session.session_id,
            "client_id": CLIENT,
        }
        for written in ("nan", "-inf", "not a number"):
            answer = await result(
                client,
                type=WS_TYPE_SESSION_ACT,
                **common,
                revision=session.revision,
                action="submit",
                value=written,
            )
            assert answer["session"]["step"] == "height", written
            assert answer["session"]["form"]["error"] == "not_a_number", written

        # ...and a decimal comma survives the wire, which is why a number travels as text.
        answer = await result(
            client,
            type=WS_TYPE_SESSION_ACT,
            **common,
            revision=session.revision,
            action="submit",
            value="195,0",
        )
        assert answer["session"]["step"] == "height_result"
        assert answer["session"]["measured"]["travel_cm"] == HEIGHT
        await session.async_cancel(CLIENT)



# ======================================================================= the refusals
async def test_a_command_about_a_gateway_that_is_not_there_is_refused(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`entry_id` names a MyHOME gateway or it names nothing: the rule of §1, on all ten.

    Mutation caught: a session command that looks the entry up without checking what
    integration it belongs to.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        client = await hass_ws_client(hass)
        payloads: dict[str, dict[str, Any]] = {
            WS_TYPE_SESSION_GET: {},
            WS_TYPE_SESSION_START: {"cover_unique_id": FIRST, "client_id": CLIENT},
            WS_TYPE_SESSION_ATTACH: {"session_id": EXAMPLE_SESSION_ID, "client_id": CLIENT},
            WS_TYPE_SESSION_HEARTBEAT: {"session_id": EXAMPLE_SESSION_ID, "client_id": CLIENT},
            WS_TYPE_SESSION_ACT: {
                "session_id": EXAMPLE_SESSION_ID,
                "client_id": CLIENT,
                "revision": 1,
                "action": "path_a",
            },
            WS_TYPE_SESSION_STOP: {"session_id": EXAMPLE_SESSION_ID, "client_id": CLIENT},
            WS_TYPE_SESSION_LEAVE: {"session_id": EXAMPLE_SESSION_ID, "client_id": CLIENT},
            WS_TYPE_SESSION_CANCEL: {"client_id": CLIENT},
            WS_TYPE_SESSION_SAVE: {
                "session_id": EXAMPLE_SESSION_ID,
                "client_id": CLIENT,
                "revision": 1,
                "target": "profile",
            },
            WS_TYPE_SESSION_END_OTHER: {},
        }
        assert set(payloads) == set(WS_SESSION_COMMANDS)
        for command, payload in payloads.items():
            error = await refused(client, type=command, entry_id="01NOTAGATEWAY", **payload)
            assert error["code"] == ws_const.ERR_NOT_FOUND, command
            assert error["translation_key"] == "unknown_entry", command
        # ...and the gateway that is this one still answers every one of them.
        assert (await result(client, type=WS_TYPE_SESSION_GET, entry_id=entry.entry_id))[
            "session"
        ] is None


BAD_FRAMES: list[tuple[str, dict[str, Any]]] = [
    # `client_id` is an alphabet and a length, and both halves are the schema's.
    ("a client id with a slash in it", {"client_id": "../../etc"}),
    ("a client id of four characters", {"client_id": "abcd"}),
    # `profile` belongs to paths B and C, `scope` to path C.
    ("a profile on path A", {"path": "path_a", "profile": "tall"}),
    ("a scope on path B", {"path": "path_b", "scope": "times_only"}),
    ("a path nobody walks", {"path": "path_z"}),
    ("a scope nobody narrows to", {"path": "path_c", "scope": "the_lot"}),
    # `revision` is a number, and `True` is not one however Python counts it.
    ("a revision that is a boolean", {"type": WS_TYPE_SESSION_ACT, "revision": True}),
    ("a revision that is a word", {"type": WS_TYPE_SESSION_ACT, "revision": "1"}),
    ("a negative revision", {"type": WS_TYPE_SESSION_ACT, "revision": -1}),
    # A value is a string, a number or nothing: never a list, never a boolean.
    ("a value that is a list", {"type": WS_TYPE_SESSION_ACT, "value": [195]}),
    ("a value that is a boolean", {"type": WS_TYPE_SESSION_ACT, "value": True}),
    ("a save target nobody offers", {"type": WS_TYPE_SESSION_SAVE, "target": "everything"}),
    ("a key beside the ones that belong", {"type": WS_TYPE_SESSION_GET, "and_also": True}),
    ("no session id where one is required", {"type": WS_TYPE_SESSION_STOP, "session_id": None}),
]

# The well-formed frame each of the cases above spoils one key of. A `start` unless the
# case names another command, because most of the schema's rules are `start`'s.
WELL_FORMED: dict[str, dict[str, Any]] = {
    WS_TYPE_SESSION_START: {"cover_unique_id": FIRST, "client_id": CLIENT},
    WS_TYPE_SESSION_ACT: {
        "session_id": EXAMPLE_SESSION_ID,
        "client_id": CLIENT,
        "revision": 1,
        "action": "submit",
    },
    WS_TYPE_SESSION_SAVE: {
        "session_id": EXAMPLE_SESSION_ID,
        "client_id": CLIENT,
        "revision": 1,
        "target": "profile",
    },
    WS_TYPE_SESSION_STOP: {"session_id": EXAMPLE_SESSION_ID, "client_id": CLIENT},
    WS_TYPE_SESSION_GET: {},
}


def spoiled(payload: dict[str, Any]) -> dict[str, Any]:
    """One well-formed frame with the case's key put wrong (or taken out, for `None`)."""
    command = payload.get("type", WS_TYPE_SESSION_START)
    frame = {"type": command, **WELL_FORMED[command], **payload}
    return {key: value for key, value in frame.items() if value is not None}


@pytest.mark.parametrize(
    ("case", "payload"), BAD_FRAMES, ids=[case for case, _payload in BAD_FRAMES]
)
async def test_a_session_frame_nobody_meant_to_send_is_answered_and_never_raised(
    hass: HomeAssistant, tmp_path, hass_ws_client, case: str, payload: dict[str, Any]
) -> None:
    """Fourteen frames a browser can send, and fourteen `invalid_format`s back.

    All of them stop at the schema, which is where a malformed frame belongs: there is
    nothing for the user to do about any of them, and the distinction from
    `service_validation_error` is the one the panel renders. The socket is still usable
    afterwards, which is what tells a refusal from a crash.

    Mutation caught: `vol.Coerce(float)` in place of the finite-number check (`NaN`
    would reach the arithmetic); dropping the combination rule from `start`; widening
    `client_id` to any string.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        error = await refused(client, entry_id=entry.entry_id, **spoiled(payload))
        assert error["code"] == ws_const.ERR_INVALID_FORMAT, case
        assert loaded_store(hass, entry).raw_profiles == CALIBRATION["profiles"], case
        assert (await result(client, type=WS_TYPE_SESSION_GET, entry_id=entry.entry_id))[
            "session"
        ] is None, case


def test_a_number_that_is_not_one_never_reaches_the_arithmetic() -> None:
    """`NaN` and the two infinities, refused by the schema Home Assistant applies.

    Not a socket test, and it cannot be one: Home Assistant's own parser refuses a frame
    carrying a JSON `NaN` and closes the connection, which is a second door in front of
    this one. What can reach `act` is an *embedder* whose `json.loads` reads the three
    non-numbers (the default one does), so the validator is held here through the real
    decorator - the schema as the socket would apply it, `id` and all.

    The string forms - `"nan"`, `"-inf"` - go straight through `parse_number`, which is
    `float()` underneath: those are caught one layer down and are the subject of
    `test_a_value_that_cannot_be_a_reading_is_a_form_error_and_not_a_refusal`, because
    they are something a person could have typed and are therefore a field error.

    Mutation caught: `vol.Any(int, float)` with no finiteness check - `float("nan")`
    passes it, and every fitted number after such a reading becomes `nan`.
    """

    def handler(hass, connection, msg) -> None:  # pragma: no cover - never called
        """A command body nobody runs: only the schema the decorator attaches is read."""

    schema = websocket_api.websocket_command(SESSION_ACT_SCHEMA)(handler)._ws_schema
    frame = {
        "id": 1,
        "type": WS_TYPE_SESSION_ACT,
        "entry_id": EXAMPLE_ENTRY_ID,
        "session_id": EXAMPLE_SESSION_ID,
        "client_id": CLIENT,
        "revision": 1,
        "action": "submit",
    }
    # A number is a number, and a number written as text still is.
    assert schema({**frame, "value": 86.25})["value"] == 86.25
    assert schema({**frame, "value": "86,25"})["value"] == "86,25"
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(vol.Invalid):
            schema({**frame, "value": value})


async def test_every_refusal_of_the_session_comes_back_with_its_key(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """The eight of SPEC §4.6, each from the state that really produces it.

    Every one of them carries `translation_domain="myhome"`, the key and an English
    sentence: a client is never left with a bare token, and the panel has a screen for
    each. `unknown_profile`, `unknown_cover`, `advanced_cover` and `cover_unavailable`
    come from the same door, before anything is taken hold of.

    Mutation caught: a refusal sent without its domain (the frontend would render the
    key); `session_owned` answered where `revision_conflict` belongs.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        start = {
            "type": WS_TYPE_SESSION_START,
            "entry_id": entry.entry_id,
            "client_id": CLIENT,
        }

        # ...before any session exists.
        error = await refused(client, **start, cover_unique_id=f"{FIRST}-nope")
        assert (error["code"], error["translation_key"]) == (
            ws_const.ERR_NOT_FOUND,
            "unknown_cover",
        )
        error = await refused(client, **start, cover_unique_id=ADVANCED)
        assert (error["code"], error["translation_key"]) == (
            ws_const.ERR_NOT_SUPPORTED,
            "advanced_cover",
        )
        error = await refused(
            client,
            type=WS_TYPE_SESSION_ATTACH,
            entry_id=entry.entry_id,
            session_id=EXAMPLE_SESSION_ID,
            client_id=CLIENT,
        )
        assert (error["code"], error["translation_key"]) == (
            ws_const.ERR_NOT_FOUND,
            "unknown_session",
        )
        # Every one of them carries the domain beside the key: without it Home
        # Assistant resolves nothing and the panel is handed the token itself.
        assert error["translation_domain"] == "myhome"

        # ...and then one does.
        session = await open_session(hass, entry)
        error = await refused(client, **start, cover_unique_id=SECOND)
        assert (error["code"], error["translation_key"]) == (
            ws_const.ERR_NOT_ALLOWED,
            "already_calibrating",
        )
        assert error["translation_placeholders"] == {"cover": "Hallway Shutter", "by": "panel"}
        assert "Hallway Shutter" in error["message"]

        # ...and an id that names another session is `unknown_session` too, which is
        # the case that matters: a tab left open across a cancellation and a fresh
        # start must not act on the session that took its place.
        for command in (WS_TYPE_SESSION_ATTACH, WS_TYPE_SESSION_HEARTBEAT, WS_TYPE_SESSION_STOP):
            error = await refused(
                client,
                type=command,
                entry_id=entry.entry_id,
                session_id=EXAMPLE_SESSION_ID,
                client_id=CLIENT,
            )
            assert error["translation_key"] == "unknown_session", command
        error = await refused(
            client,
            type=WS_TYPE_SESSION_ACT,
            entry_id=entry.entry_id,
            session_id=EXAMPLE_SESSION_ID,
            client_id=CLIENT,
            revision=session.revision,
            action="path_a",
        )
        assert error["translation_key"] == "unknown_session"
        assert session.snapshot()["path"] is None

        common = {
            "entry_id": entry.entry_id,
            "session_id": session.session_id,
            "client_id": CLIENT,
        }
        error = await refused(
            client, type=WS_TYPE_SESSION_ACT, **common, revision=99, action="path_a"
        )
        assert error["translation_key"] == "revision_conflict"
        assert error["translation_domain"] == "myhome"
        error = await refused(
            client, type=WS_TYPE_SESSION_ACT, **common, revision=session.revision, action="begin"
        )
        assert error["translation_key"] == "action_not_offered"
        assert error["translation_placeholders"] == {"action": "begin"}
        error = await refused(
            client, type=WS_TYPE_SESSION_SAVE, **common, revision=session.revision, target="profile"
        )
        assert error["translation_key"] == "not_in_review"

        # ...owned by somebody else, and present.
        error = await refused(
            client,
            type=WS_TYPE_SESSION_ACT,
            entry_id=entry.entry_id,
            session_id=session.session_id,
            client_id=OTHER_CLIENT,
            revision=session.revision,
            action="path_a",
        )
        assert error["translation_key"] == "session_owned"

        # ...and ended.
        await session.async_cancel(CLIENT)
        error = await refused(
            client, type=WS_TYPE_SESSION_ACT, **common, revision=session.revision, action="path_a"
        )
        assert error["translation_key"] == "session_ended"
        assert error["translation_placeholders"] == {"reason": "cancelled"}


async def test_a_shutter_whose_entity_is_unavailable_is_not_calibrated(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`cover_unavailable`: the gateway is loaded and the window is not answering.

    Mutation caught: starting a session on an unavailable cover (every primitive would
    refuse, one screen at a time, with the shutter held).
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        hass.states.async_set(ENTITY, "unavailable")
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_SESSION_START,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            client_id=CLIENT,
        )
        assert (error["code"], error["translation_key"]) == (
            ws_const.ERR_NOT_FOUND,
            "cover_unavailable",
        )
        assert error["translation_placeholders"] == {"cover": "Hallway Shutter"}
        assert current(hass, entry) is None


# ==================================================================== the subscription
async def test_the_subscription_carries_the_session_now_and_at_every_transition(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """`session` on subscribing, then one event per transition, in `revision` order.

    The order is the assertion that matters: the panel replaces its model with whatever
    arrives, so two events out of order would leave it showing the screen before last -
    and a session publishes from timers and from state changes as well as from verbs,
    which is precisely where an ordering could be lost.

    Mutation caught: pushing the snapshot from the handler instead of from the session's
    own publication (a transition nobody asked for - a press timing out - would reach
    nobody); a subscription that hears about a session made after it subscribed only
    when the next write happens.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        sub_id = await subscribed(client, entry.entry_id)

        seen: list[dict[str, Any]] = []
        session = await started_over_the_socket(client, hass, entry, seen=seen)
        await session_events(client, sub_id, seen, session.revision)
        assert [snapshot["revision"] for snapshot in seen] == list(range(1, session.revision + 1))
        assert seen[0]["step"] == "path"

        await act(hass, session, Act("path_a"), freezer=freezer)
        await session_events(client, sub_id, seen, session.revision)
        assert [snapshot["revision"] for snapshot in seen] == list(range(1, session.revision + 1))
        assert seen[-1]["step"] == "path_a"
        for snapshot in seen:
            check_the_snapshot(snapshot)

        await session.async_cancel(CLIENT)


async def test_a_panel_that_opens_on_a_session_already_running_is_told_about_it(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The first event of a subscription is the session there is, not an empty one.

    Mutation caught: sending `session: null` on subscribing and waiting for the next
    transition (a phone picking the wizard up again would show nothing until somebody
    pressed something on the other device).
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry, path="path_a")

        client = await hass_ws_client(hass)
        await client.send_json_auto_id({"type": WS_TYPE_SUBSCRIBE, "entry_id": entry.entry_id})
        assert (await client.receive_json())["success"] is True
        overview = (await client.receive_json())["event"]
        assert overview["overview"]["session"]["session_id"] == session.session_id
        event = (await client.receive_json())["event"]
        assert event["type"] == WS_EVENT_SESSION
        assert event["session"]["session_id"] == session.session_id
        assert event["session"]["step"] == "path_a"
        await session.async_cancel(CLIENT)


async def test_a_panel_already_open_is_told_who_is_holding_the_shutter_at_every_turn(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """`overview.session` is pushed when a session appears and when it goes.

    A calibration writes nothing until it is saved, so nothing in `panel_write`
    publishes an overview for it - and a panel that was already subscribed when the
    session began would read `session: null` for the whole of it. The document says what
    that means: `measuring` set beside `session: null` is *the guided dialog or the
    0.4.2 action*, and the screen offers to close a dialog rather than to join a
    calibration. The second screen in the house would offer a button that aborts no flow
    and answers `still_calibrating: true`.

    The invariant asserted on **every** overview this tab is given is the one that
    sentence rests on: a shutter of this gateway being measured by the panel is never
    reported with no session beside it.

    Mutation caught: publishing the overview only from the writes (a second panel never
    sees the calibration begin); publishing it at the start and not at the end (the
    banner names a calibration that is over until the next write of any kind).
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        sub_id = await subscribed(client, entry.entry_id)
        overviews: list[dict[str, Any]] = []
        seen: list[dict[str, Any]] = []

        session = await started_over_the_socket(
            client, hass, entry, seen=seen, overviews=overviews
        )
        assert overviews, "the tab that was already open was never told the session began"
        assert overviews[-1]["session"] == {
            "session_id": session.session_id,
            "cover_unique_id": FIRST,
            "name": "Hallway Shutter",
            "state": "armed",
            "owner": CLIENT,
        }
        assert overviews[-1]["measuring"]["cover_unique_id"] == FIRST

        # A step of the conversation is not a change of hands: no overview goes out.
        so_far = len(overviews)
        await act(hass, session, Act("path_a"), freezer=freezer)
        await session_events(client, sub_id, seen, session.revision, overviews=overviews)
        assert len(overviews) == so_far

        # ...and the ending is, whichever ending it is.
        msg_id = await sent(
            client,
            {
                "type": WS_TYPE_SESSION_CANCEL,
                "entry_id": entry.entry_id,
                "client_id": CLIENT,
                "session_id": session.session_id,
            },
        )
        await answered(client, msg_id, overviews=overviews)
        assert overviews[-1]["session"]["state"] == "ended"
        assert overviews[-1]["measuring"] is None

        # The invariant that sentence rests on, on every overview this tab was given:
        # `measuring` set with `session` at `null` would mean "the dialog". The converse
        # is not an invariant - a terminal session stays readable for ten minutes after
        # the shutter has been given back, which is how the outcome screen survives a
        # reload.
        for overview in overviews:
            if overview["measuring"] is not None:
                assert overview["session"] is not None, overview["measuring"]
                assert overview["session"]["state"] not in ("saved", "ended"), overview["session"]


async def test_the_socket_closing_takes_the_subscriber_away_and_leaves_the_session(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """The whole reason the session is on the server: a tab closing does not end it.

    What goes is the subscriber; what stays is the measurement, its owner and everything
    measured so far - and the next socket reads it with `get`.

    Mutation caught: ending the session in the unsubscribe; leaving the callback hooked
    onto the session after the connection is gone (the next transition would push into
    a closed connection).
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        sub_id = await subscribed(client, entry.entry_id)
        seen: list[dict[str, Any]] = []
        session = await started_over_the_socket(client, hass, entry, seen=seen)
        await act(hass, session, Act("path_a"), freezer=freezer)
        await session_events(client, sub_id, seen, session.revision)

        await client.send_json_auto_id({"type": "unsubscribe_events", "subscription": sub_id})
        assert (await client.receive_json())["success"] is True
        await hass.async_block_till_done()
        assert hass.data[SESSION_WATCHERS_DATA_KEY][entry.entry_id] == []

        # The session did not notice, and the transitions it makes reach nobody.
        await act(hass, session, Act("begin"), freezer=freezer)
        assert current(hass, entry) is session
        assert session.ended is False
        answer = await result(client, type=WS_TYPE_SESSION_GET, entry_id=entry.entry_id)
        assert answer["session"]["session_id"] == session.session_id
        assert answer["session"]["path"] == "path_a"
        await session.async_cancel(CLIENT)


# ========================================================================== the save
async def test_save_writes_once_publishes_the_overview_and_reloads_nothing(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """Three minutes of measuring, written in place and without a reload.

    A reload is what the guided dialog does when it closes after saving, and it is a
    disconnect and a reconnect on a real gateway - very likely while the shutter is
    still moving. The panel's write reaches the covers in place instead (plan decision
    4), and the session's save goes through that same door: one write, the fresh
    overview to every open panel, the signal to the shutters, and no
    `async_schedule_reload`.

    Mutation caught: saving twice (the second would find the store it had just written);
    scheduling a reload; answering without the overview.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        sub_id = await subscribed(client, entry.entry_id)
        session = await started_over_the_socket(client, hass, entry)
        await walk(hass, session, A_NAMED_AFTER_THE_WINDOW, freezer=freezer)
        assert session.snapshot()["state"] == "review"

        seen: list[dict[str, Any]] = []
        with (
            patch.object(hass.config_entries, "async_schedule_reload", autospec=True) as scheduled,
            patch.object(hass.config_entries, "async_reload", autospec=True) as reloaded,
        ):
            msg_id = await sent(
                client,
                {
                    "type": WS_TYPE_SESSION_SAVE,
                    "entry_id": entry.entry_id,
                    "session_id": session.session_id,
                    "client_id": CLIENT,
                    "revision": session.revision,
                    "target": "profile",
                },
            )
            answer = await answered(client, msg_id, seen)
        assert scheduled.call_count == 0
        assert reloaded.call_count == 0
        assert tuple(answer) == SESSION_SAVE_KEYS
        assert answer["session"]["state"] == "saved"
        assert answer["session"]["outcome"]["reason"] == "saved"
        # Written once: the profile is there, the cover follows it, and the shutter is
        # running on it without anything having been reloaded.
        store = loaded_store(hass, entry)
        assert store.raw_profiles["hallway_shutter"]["opening_time"] == pytest.approx(22.3, abs=0.2)
        assert store.raw_covers[FIRST]["profile"] == "hallway_shutter"
        assert hass.states.get(ENTITY).attributes["Profile"] == "hallway_shutter"
        # ...and it left no undo token, because three minutes of measuring are not a
        # gesture to take back by accident.
        assert "undo_token" not in answer

        # Every open panel was given the session's last transition on the way, and the
        # overview that the write published with it says the same thing.
        assert seen[-1]["state"] == "saved"
        assert answer["overview"]["session"]["state"] == "saved"
        assert sub_id


# ======================================================================= `end_other`
async def test_end_other_closes_the_dialogs_of_this_gateway_and_frees_the_shutter(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The *Configure* dialog is measuring: the panel closes it rather than fighting it.

    Driven through the real options flow, because what has to be released is the
    `calibrating` flag the dialog's own `_claim` sets - and what aborts it is the pair
    of methods Home Assistant gives for it, not a private one.

    Mutation caught: aborting the flows of every gateway; answering `still_calibrating`
    before the abort has taken effect; counting a flow that was not aborted.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        manager = hass.config_entries.options
        opened = await manager.async_init(entry.entry_id)
        opened = await manager.async_configure(opened["flow_id"], {"next_step_id": "calibrate"})
        opened = await manager.async_configure(opened["flow_id"], {"next_step_id": "cover"})
        opened = await manager.async_configure(opened["flow_id"], {"cover": FIRST})
        assert opened["step_id"] == "path"
        assert cover.calibrating is True

        client = await hass_ws_client(hass)
        # ...and while it holds the shutter, the panel cannot start a session at all.
        error = await refused(
            client,
            type=WS_TYPE_SESSION_START,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            client_id=CLIENT,
        )
        assert error["translation_placeholders"]["by"] == "other"

        answer = await result(
            client, type=WS_TYPE_SESSION_END_OTHER, entry_id=entry.entry_id
        )
        assert tuple(answer) == SESSION_END_OTHER_KEYS
        assert answer["flows_aborted"] == 1
        assert answer["still_calibrating"] is False
        assert answer["overview"]["measuring"] is None
        assert cover.calibrating is False
        assert list(manager.async_progress_by_handler(entry.entry_id)) == []

        # ...and now the panel can measure it.
        started = await result(
            client,
            type=WS_TYPE_SESSION_START,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            client_id=CLIENT,
        )
        assert started["session"]["step"] == "path"
        await current(hass, entry).async_cancel(CLIENT)


async def test_end_other_says_when_what_is_holding_the_shutter_is_not_a_dialog(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Nothing to abort and the shutter still in calibration: it is the 0.4.2 action.

    Its run is nothing this command may cut short - it is a real shutter travelling -
    so the answer says so and the screen asks the user to wait.

    Mutation caught: reporting `still_calibrating: false` because no dialog was open.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        cover = entity_object(hass, COVER, DEVICE_KEY)
        FakeRunner(cover)
        client = await hass_ws_client(hass)
        with cover.calibration_session():
            await hass.async_block_till_done()
            answer = await result(
                client, type=WS_TYPE_SESSION_END_OTHER, entry_id=entry.entry_id
            )
        assert answer["flows_aborted"] == 0
        assert answer["still_calibrating"] is True
        assert answer["overview"]["measuring"]["cover_unique_id"] == FIRST


async def test_end_other_closes_the_dialogs_of_this_gateway_and_not_of_another(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A dialog open on each of two gateways, and only one of them is closed.

    An options flow's handler is the entry id, which is what makes "every Configure
    dialog of this gateway" a question Home Assistant can answer. Asked without it, the
    same call answers *every* flow in progress - config flows of other integrations
    included - and a panel closing one dialog would close somebody else's.

    Mutation caught: `async_progress()` in place of
    `async_progress_by_handler(entry.entry_id)`.
    """
    async with two_gateways(hass, tmp_path) as (first, second):
        manager = hass.config_entries.options
        opened = []
        for entry in (first, second):
            flow = await manager.async_init(entry.entry_id)
            opened.append(flow["flow_id"])
        assert len(list(manager.async_progress())) == 2

        client = await hass_ws_client(hass)
        answer = await result(client, type=WS_TYPE_SESSION_END_OTHER, entry_id=first.entry_id)
        assert answer["flows_aborted"] == 1
        left = [flow["flow_id"] for flow in manager.async_progress()]
        assert left == [opened[1]]
        manager.async_abort(opened[1])


# ================================================================== `overview.session`
async def test_the_overview_says_which_client_is_holding_the_shutter(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """`measuring` says *that*; `session` says *who*, which is what the banner needs.

    `measuring` set with `session` at `null` is the guided dialog or the 0.4.2 action,
    and the panel then offers to close the dialog rather than to resume a session it
    does not have.

    Mutation caught: building the line from the session's attributes instead of from its
    snapshot (a terminal session would answer the screen it stopped on rather than
    `saved`); leaving `session` set after the session has been forgotten.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        assert (await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id))[
            "session"
        ] is None

        session = await open_session(hass, entry, path="path_a")
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        assert tuple(overview["session"]) == SESSION_OVERVIEW_KEYS
        assert overview["session"] == {
            "session_id": session.session_id,
            "cover_unique_id": FIRST,
            "name": "Hallway Shutter",
            "state": "armed",
            "owner": CLIENT,
        }
        # The shutter is held, so the read-only lock is up as well.
        assert overview["measuring"] == {"cover_unique_id": FIRST, "name": "Hallway Shutter"}

        # A session with no owner is a session anybody may pick up, and the banner says
        # so by finding `owner: null` rather than by guessing.
        await walk(hass, session, PATH_A_BASIC[1:5], freezer=freezer)
        session.leave(CLIENT)
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        assert overview["session"]["owner"] is None
        assert overview["session"]["state"] == "briefing"

        # ...and a terminal one reads as terminal until it is forgotten.
        await session.async_cancel(CLIENT)
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        assert overview["session"]["state"] == "ended"
        assert overview["measuring"] is None

        freezer.tick(calibration_session.TERMINAL_TTL + timedelta(seconds=1))
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        assert overview["session"] is None


# A tape does not read the model back. The shared walk of `test_calibration_session.py`
# hands the session exactly what the reference window would do if its curtain obeyed the
# arithmetic to the millimetre, which is the right input for a test that checks the
# rediscovered numbers - and the wrong one for this fixture: the fake window *is* the
# `tall` profile of `panel_overview_example.json`, so a perfect reading rediscovers that
# profile and every review comes out with its "before" and "after" columns carrying the
# same six numbers. The panel's review screen cannot be built against a table where
# nothing changes, and neither can the list of the windows the profile reaches.
#
# So the two tape readings are a centimetre and a half off the model, which is what a
# person with a tape really writes down. They are inputs and not outputs: everything
# downstream - the fit, the two roll coefficients, the profile written, the row of every
# follower - is what the server computes from them.
TAPE_ASCENT = round(ascent_cm(0.5) + 1.5, 1)
TAPE_DESCENT = round(descent_cm(0.5) - 1.5, 1)


def with_a_real_tape(acts: tuple[Act, ...]) -> tuple[Act, ...]:
    """The shared walk with its two readings replaced by the ones above."""
    instead = {str(ascent_cm(0.5)): str(TAPE_ASCENT), str(descent_cm(0.5)): str(TAPE_DESCENT)}
    return tuple(
        Act(one.action, instead.get(str(one.value), one.value), one.tick) for one in acts
    )


def at_human_speed(acts: tuple[Act, ...]) -> tuple[Act, ...]:
    """Two and a half seconds in front of every screen that measures nothing.

    The shared walk presses instantly wherever the press is not itself a measurement,
    which is right for a test about numbers and wrong for a fixture about *screens*: a
    dozen snapshots carrying the same `server_time` to the millisecond would let a panel
    be built that quietly assumes instants never move. The ticks that **are** the
    measurement - the slat phase, the two timed runs - are left exactly as they are.
    """
    return tuple(one if one.tick else Act(one.action, one.value, 2.5) for one in acts)


A_TAPED = at_human_speed(with_a_real_tape(PATH_A_BASIC))
# ...and with the profile named after the window itself rather than after the profile
# that already exists, which is what makes `review_basic` a review that **creates** a
# profile and `review_basic_profile_exists` one that updates one.
A_NAMED_AFTER_THE_WINDOW = (*A_TAPED[:-1], Act("submit", "hallway_shutter"))


# ============================================================= the committed examples
# `tests/fixtures/panel_session_examples.json` is the frontend's stand-in server: the
# harness draws from it, `npm run session` drives the built bundle against it, and
# `test/wizard-model.test.ts` builds a screen model out of every one of its scenarios.
# Lot L0 wrote it by hand, before there was a controller; from here on it is **what the
# controller really publishes**, walk by walk, so that a screen the panel cannot draw is
# a failing test and a visible diff instead of a surprise in a browser three lots later.
#
# Run `python -m pytest tests/test_websocket_session.py -k committed_session_examples`
# after any deliberate change, read the diff, and update the file.
#
# **Two things are normalised and nothing else.** The session id is a fresh `uuid4` and
# the entry id a fresh ULID on every run; the committed file carries a stable stand-in
# for each. Everything else, the instants included, is real: the walks run under a
# frozen clock that starts at `FIXTURE_START`, so the same walk produces the same
# seconds every time, and the fixture keeps hours a panel can subtract.
FIXTURE_START = datetime(2026, 9, 18, 10, 0, tzinfo=UTC)

# Nothing is written by hand any more. The six snapshots that stood on paths B and C, on
# the thorough level and on the verifications were lot L0's until the backend could walk
# them; they are walked here now, and five more went with them.
STILL_BY_HAND: frozenset[str] = frozenset()


class Recorder:
    """Every snapshot one session published, in the order it published them.

    The screens inside a movement - the frame going out before the actuator has echoed,
    a homing under way, the run to a fraction - are never what a verb *answers*: by the
    time `act` comes back the movement is over. They are events, so they are collected
    as events.
    """

    def __init__(self, session: CalibrationSession) -> None:
        self.seen: list[dict[str, Any]] = [session.snapshot()]
        self.drop = session.subscribe(self.seen.append)

    def on(self, step: str, **fields: Any) -> dict[str, Any]:
        """The first snapshot published on that step, with those fields."""
        for snapshot in self.seen:
            if snapshot["step"] == step and all(
                snapshot[key] == value for key, value in fields.items()
            ):
                return snapshot
        raise AssertionError(f"no snapshot on {step} with {fields} among {self.steps()}")

    def steps(self) -> list[str]:
        return [snapshot["step"] for snapshot in self.seen]


def normalised(snapshot: dict[str, Any]) -> dict[str, Any]:
    """One snapshot with the two identifiers nobody can predict put back."""
    text = json.dumps(snapshot)
    return json.loads(
        text.replace(snapshot["session_id"], EXAMPLE_SESSION_ID).replace(
            snapshot["entry_id"], EXAMPLE_ENTRY_ID
        )
    )


def they_are_the_committed_examples(produced: dict[str, dict[str, Any]]) -> None:
    """Compare what the controller published with what is in the file, scenario by one."""
    committed = the_fixture()["scenarios"]
    wrong: list[str] = []
    for name, snapshot in produced.items():
        assert name in committed, f"{name} is not a scenario of the fixture"
        check_the_snapshot(snapshot)
        mine = normalised(snapshot)
        if mine != committed[name]:
            wrong.append(
                f"--- {name} ---\nthe server sends:\n"
                f"{json.dumps(mine, indent=2, ensure_ascii=False)}\n"
                f"the fixture says:\n{json.dumps(committed[name], indent=2, ensure_ascii=False)}"
            )
    assert not wrong, "\n".join(wrong)


def test_the_fixture_names_every_scenario_the_walks_below_produce() -> None:
    """The list of what is regenerated and the list of what is not, together and whole.

    Without this, a scenario dropped from a walk would simply stop being compared with
    anything and the hand-written snapshot beside it would go stale in silence.

    Mutation caught: taking a name out of `REGENERATED` and leaving the file's scenario
    behind; lot B4 walking a scenario without taking it out of `STILL_BY_HAND`.
    """
    committed = set(the_fixture()["scenarios"])
    assert committed == REGENERATED | STILL_BY_HAND
    assert not REGENERATED & STILL_BY_HAND


PATH_A_SCREENS = (
    "armed_path",
    "briefing_open_brief",
    "running_open_start",
    "running_open_lift",
    "running_lift_stop",
    "briefing_lift_check",
    "positioning_home_closed",
    "positioning_tape_run",
    "awaiting_reading_height",
    "awaiting_reading_measure_descent",
    "briefing_profile_name",
    "review_basic",
)


async def test_the_committed_session_examples_are_what_the_server_sends_on_path_a(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Twelve screens of one walk, from the shutter's first movement to its summary."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        seen = Recorder(session)
        review = await walk(hass, session, A_NAMED_AFTER_THE_WINDOW, freezer=freezer)

        they_are_the_committed_examples(
            {
                "armed_path": seen.seen[0],
                "briefing_open_brief": seen.on("open_brief"),
                "running_open_start": seen.on("open_start"),
                "running_open_lift": seen.on("open_lift"),
                "running_lift_stop": seen.on("lift_stop"),
                "briefing_lift_check": seen.on("lift_check"),
                "positioning_home_closed": seen.on("home_closed"),
                "positioning_tape_run": seen.on("tape_run"),
                "awaiting_reading_height": seen.on("height"),
                "awaiting_reading_measure_descent": seen.on("measure_descent"),
                "briefing_profile_name": seen.on("profile_name"),
                "review_basic": review,
            }
        )
        await session.async_cancel(CLIENT)


@pytest.mark.parametrize(
    ("name", "target"), [("saved_profile", "profile"), ("saved_cover_only", "cover_only")]
)
async def test_the_committed_session_examples_are_what_the_server_sends_when_it_saves(
    hass: HomeAssistant,
    tmp_path,
    freezer: FrozenDateTimeFactory,
    name: str,
    target: str,
) -> None:
    """The two exits of path A, each with the outcome the shutter really ended on."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, A_NAMED_AFTER_THE_WINDOW, freezer=freezer)
        answer = await session.async_save(CLIENT, session.revision, target)
        they_are_the_committed_examples({name: answer["session"]})


async def test_the_committed_session_examples_are_what_the_server_sends_over_a_profile(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The review that updates a profile, with every other window it reaches named."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        review = await walk(hass, session, A_TAPED, freezer=freezer)
        they_are_the_committed_examples({"review_basic_profile_exists": review})
        await session.async_cancel(CLIENT)


async def test_the_committed_session_examples_are_what_the_server_sends_off_the_straight_road(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The gap form, a reading that cannot be one, and the three ways out of a step.

    Each of them is a branch of the same walk taken at one screen, so each gets its own
    session: a fixture built by walking on from a screen already perturbed would show
    states no user ever reaches.
    """
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        produced: dict[str, dict[str, Any]] = {}

        # The bottom edge did not leave its rest where it was expected to: the tape
        # measures the gap, and the session asks for it.
        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:5], freezer=freezer)
        produced["awaiting_reading_lift_gap"] = await act(
            hass, session, Act("lift_gap"), freezer=freezer
        )
        await session.async_cancel(CLIENT)

        # A reading longer than the whole curtain: the user's mistake, so the field
        # comes back with an error on it and not a refusal.
        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:18], freezer=freezer)
        assert session.snapshot()["step"] == "measure_descent"
        produced["awaiting_reading_measure_descent_error"] = await act(
            hass, session, Act("submit", "500"), freezer=freezer
        )
        await session.async_cancel(CLIENT)

        they_are_the_committed_examples(produced)


async def test_the_committed_session_examples_are_what_the_server_sends_when_something_else_moves_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The wall switch, at the three moments it means three different things (§11.5)."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        produced: dict[str, dict[str, Any]] = {}

        # Before a timed run: the session takes the shutter back to its end stop first.
        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:3], freezer=freezer)
        hass.states.async_set(ENTITY, STATE_OPENING)
        await hass.async_block_till_done()
        produced["briefing_open_brief_rehomed"] = await act(
            hass, session, Act("open_start"), freezer=freezer
        )
        await session.async_cancel(CLIENT)

        # Outside a measurement: not an interruption, and nothing is repeated.
        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:5], freezer=freezer)
        hass.states.async_set(ENTITY, STATE_OPENING)
        await hass.async_block_till_done()
        produced["briefing_lift_check_external"] = session.snapshot()
        await session.async_cancel(CLIENT)

        # While a reading is awaited: the field stays, and the way forward is the step.
        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:18], freezer=freezer)
        hass.states.async_set(ENTITY, STATE_CLOSING)
        await hass.async_block_till_done()
        produced["awaiting_reading_measure_descent_stale"] = session.snapshot()
        await session.async_cancel(CLIENT)

        they_are_the_committed_examples(produced)


async def test_the_committed_session_examples_are_what_the_server_sends_when_it_goes_wrong(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The gateway that did not answer, and the step a stop made meaningless."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        produced: dict[str, dict[str, Any]] = {}

        session = await open_session(hass, entry)
        runner.fail = CalibrationError(REASON_NO_ECHO, "the actuator never answered")
        runner.fail_on = "home"
        produced["problem_no_echo"] = await walk(
            hass, session, A_TAPED[:2], freezer=freezer
        )
        await session.async_cancel(CLIENT)

        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:4], freezer=freezer)
        assert session.snapshot()["step"] == "open_lift"
        produced["problem_interrupted"] = await session.async_stop(CLIENT)
        await session.async_cancel(CLIENT)

        they_are_the_committed_examples(produced)


async def test_the_committed_session_examples_are_what_the_server_sends_at_the_end(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The five ways a calibration finishes without being saved (§11.6).

    Each of them is a whole session of its own, because a terminal snapshot is the last
    thing a session ever says.
    """
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        produced: dict[str, dict[str, Any]] = {}

        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:5], freezer=freezer)
        await session.async_cancel(CLIENT)
        produced["ended_cancelled"] = session.snapshot()

        session = await open_session(hass, entry)
        produced["ended_left"] = session.leave(CLIENT)

        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:5], freezer=freezer)
        freezer.tick(timedelta(seconds=MOVED_IDLE_TIMEOUT_SEC + 1))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        produced["ended_expired"] = session.snapshot()

        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:5], freezer=freezer)
        await calibration_session.async_end_all(hass, entry, "unloaded")
        produced["ended_unloaded"] = session.snapshot()

        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:2], freezer=freezer)
        # The shutter is taken out of the gateway under the session: the next movement
        # finds no entity at all, which is the one ending nobody asked for.
        mac = str(entry.data[CONF_MAC])
        hass.data[DOMAIN][mac][CONF_PLATFORMS][COVER].pop(DEVICE_KEY)
        await act(hass, session, Act("confirm_closed"), freezer=freezer)
        produced["ended_cover_gone"] = session.snapshot()

        they_are_the_committed_examples(produced)


async def test_the_committed_session_examples_are_what_the_server_sends_to_the_other_tab(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one snapshot in the file whose owner is the second browser tab."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, A_TAPED[:6], freezer=freezer)
        assert session.snapshot()["step"] == "closed_again"
        # "Take control" on the other device: the only way the session changes hands
        # while the client holding it is still there.
        taken = session.attach(OTHER_CLIENT, claim=True)
        they_are_the_committed_examples({"owned_by_other": taken})
        await session.async_cancel(OTHER_CLIENT)



# ------------------------------------------------------- the other two paths, and the checks
# Paths B and C are about a window that is *one of a kind already measured*, so their
# scenarios stand on the second shutter of the example gateway - the one that follows
# `tall` and whose own travel nobody has measured with a tape. The profile really is the
# reference window, so a reading taken where the profile predicts comes out at nothing
# and one that misses can be made to miss by a stated amount.
SECOND_NAME = "Landing Shutter"
# What the tape finds this window's travel to be: a centimetre more than the file says,
# so that the review of a short path has a "before" and an "after" that differ.
SECOND_TRAVEL = 151.0
# Scaled onto this window, the profile predicts the bar at **50.3 cm** half way down the
# descent. One tape reading agrees with it and one misses by more than the three
# centimetres at which the correction is offered on the spot - which are the two answers
# the check exists to tell apart, and the two screens the panel has to draw.
A_READING_ON_THE_MARK = 50.3
A_READING_THAT_MISSES = 54.6

PATH_B_TO_THE_OFFER: tuple[Act, ...] = (
    Act("submit", "tall", 2.5),
    Act("tape_start", None, 2.5),
    Act("submit", str(SECOND_TRAVEL), 2.5),
    Act("accept_step", None, 2.5),
)
PATH_C_TIMES_ONLY: tuple[Act, ...] = (
    Act("submit", "tall", 2.5),
    Act("times_only", None, 2.5),
    Act("confirm_closed", None, 2.5),
    Act("open_start", None, 2.5),
    Act("lifted_off", None, SLAT),
    Act("lift_accept", None, 2.5),
    Act("confirm_closed_again", None, 2.5),
    Act("open_full_start", None, 2.5),
    Act("stopped_open", None, OPENING),
    Act("accept_step", None, 2.5),
    Act("close_start", None, 2.5),
    Act("stopped_closed", None, CLOSING),
    Act("accept_step", None, 2.5),
)
# The four readings of the thorough calibration and the check that closes it, grafted
# onto the summary of path A. The tape is a centimetre and a half off the model here
# too, for the same reason the two readings of path A are.
THE_FOUR_READINGS: tuple[Act, ...] = (
    Act("refine", None, 2.5),
    Act("tape_start", None, 2.5),
    Act("submit", str(round(descent_cm(0.25) + 1.5, 1)), 2.5),
    Act("accept_step", None, 2.5),
    Act("submit", str(round(descent_cm(0.75) - 1.5, 1)), 2.5),
    Act("accept_step", None, 2.5),
    Act("submit", str(round(ascent_cm(0.25) - 1.5, 1)), 2.5),
    Act("accept_step", None, 2.5),
    Act("submit", str(round(ascent_cm(0.75) + 1.5, 1)), 2.5),
    Act("accept_step", None, 2.5),
    Act("submit", str(round(descent_cm(0.40) + 0.8, 1)), 2.5),
    Act("accept_step", None, 2.5),
)


async def test_the_committed_session_examples_are_what_the_server_sends_when_it_is_told_the_kind(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Path B: the profile, the travel, the offer of a check, and both of its answers."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, "2-82"))
        produced: dict[str, dict[str, Any]] = {}

        # The choice itself, on a `start` that named no profile; then the offer, and the
        # summary of somebody who did not take it up.
        session = await open_session(hass, entry, SECOND, path="path_b")
        produced["armed_path_b_profile_choice"] = session.snapshot()
        await walk(hass, session, PATH_B_TO_THE_OFFER, freezer=freezer)
        produced["briefing_verify_offer"] = session.snapshot()
        produced["review_short"] = await act(
            hass, session, Act("skip_verify", None, 2.5), freezer=freezer
        )
        await session.async_cancel(CLIENT)

        # ...and taken up: the run to the middle of the descent, the tape, and a reading
        # that agrees with the profile.
        session = await open_session(hass, entry, SECOND, path="path_b")
        await walk(hass, session, PATH_B_TO_THE_OFFER, freezer=freezer)
        seen = Recorder(session)
        await act(hass, session, Act("verify_now", None, 2.5), freezer=freezer)
        produced["positioning_verify"] = seen.on("verify_b")
        produced["awaiting_reading_measure_verify"] = seen.on("measure_verify")
        produced["checking_verify_result_within"] = await act(
            hass, session, Act("submit", str(A_READING_ON_THE_MARK), 2.5), freezer=freezer
        )
        await session.async_cancel(CLIENT)

        # ...and a reading that does not: the correction is offered on the spot, and the
        # travel just measured goes with it.
        session = await open_session(hass, entry, SECOND, path="path_b")
        await walk(
            hass,
            session,
            (*PATH_B_TO_THE_OFFER, Act("verify_now", None, 2.5)),
            freezer=freezer,
        )
        produced["checking_verify_result_offers_c"] = await act(
            hass, session, Act("submit", str(A_READING_THAT_MISSES), 2.5), freezer=freezer
        )
        await session.async_cancel(CLIENT)

        they_are_the_committed_examples(produced)


async def test_the_committed_session_examples_are_what_the_server_sends_for_a_correction(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Path C: the profile is right and the window stops in the wrong place."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, "2-82"))
        produced: dict[str, dict[str, Any]] = {}

        session = await open_session(hass, entry, SECOND, path="path_c")
        produced["armed_path_c_profile_choice"] = session.snapshot()
        await session.async_cancel(CLIENT)

        # ...and the same with the profile named and a scope highlighted: `start` says
        # which correction the panel came in for, and the screen shows it chosen by
        # nobody yet.
        session = await open_session(
            hass, entry, SECOND, path="path_c", profile="tall", scope="points_only"
        )
        produced["armed_refine_scope_intent"] = session.snapshot()
        await session.async_cancel(CLIENT)

        session = await open_session(hass, entry, SECOND, path="path_c")
        produced["review_correction"] = await walk(
            hass, session, PATH_C_TIMES_ONLY, freezer=freezer
        )
        await session.async_cancel(CLIENT)

        they_are_the_committed_examples(produced)


async def test_the_committed_session_examples_are_what_the_server_sends_at_the_thorough_level(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The four readings and the check grafted onto the summary of path A."""
    freezer.move_to(FIXTURE_START)
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, A_NAMED_AFTER_THE_WINDOW, freezer=freezer)
        review = await walk(hass, session, THE_FOUR_READINGS, freezer=freezer)
        they_are_the_committed_examples({"review_precise": review})
        await session.async_cancel(CLIENT)


REGENERATED: frozenset[str] = frozenset(
    {
        *PATH_A_SCREENS,
        "review_basic_profile_exists",
        "saved_profile",
        "saved_cover_only",
        "awaiting_reading_lift_gap",
        "awaiting_reading_measure_descent_error",
        "briefing_open_brief_rehomed",
        "briefing_lift_check_external",
        "awaiting_reading_measure_descent_stale",
        "problem_no_echo",
        "problem_interrupted",
        "ended_cancelled",
        "ended_left",
        "ended_expired",
        "ended_unloaded",
        "ended_cover_gone",
        "owned_by_other",
        # ...and the paths lot B4 walks.
        "armed_path_b_profile_choice",
        "armed_path_c_profile_choice",
        "armed_refine_scope_intent",
        "briefing_verify_offer",
        "positioning_verify",
        "awaiting_reading_measure_verify",
        "checking_verify_result_within",
        "checking_verify_result_offers_c",
        "review_short",
        "review_correction",
        "review_precise",
    }
)


def test_the_documents_worked_example_is_one_of_the_fixtures_own() -> None:
    """§12.6 is a copy of a scenario, so it is compared with the scenario it copies.

    Lot L0 left this as a thing to remember: the document's complete example was copied
    from `awaiting_reading_measure_descent` by hand, and a regeneration that moved its
    numbers would leave the only worked example in the API document describing a payload
    the server no longer sends. It is one `json.loads` away from being checked, so it is
    checked.

    Mutation caught: regenerating the fixture and not recopying the example.
    """
    document = (
        Path(__file__).resolve().parents[1] / "docs" / "panel-websocket-api.md"
    ).read_text(encoding="utf-8")
    body = document.split("### 12.6 A complete example", 1)[1]
    written = body.split("```json", 1)[1].split("```", 1)[0]
    assert json.loads(written) == the_fixture()["scenarios"]["awaiting_reading_measure_descent"]
