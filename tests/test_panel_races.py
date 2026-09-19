"""What happens when two things arrive at once, over the socket the browser really uses.

`tests/test_websocket_api.py` holds the lock and the undo one call at a time, by driving
`panel_write.async_write` directly - which is the right way to arrange an interleaving
and the wrong way to find out what a *connection* does with it. The frames a panel sends
are not spaced out by a test: a confirm button under an impatient finger, two browser
tabs on the same gateway and a reconnect that replays a subscription all put two
messages into one connection inside the same tick.

So everything here goes through `hass_ws_client`, and every race is arranged by holding
the store's own `async_save` open rather than by hoping the scheduler cooperates:

* two writes racing - exactly one is applied and the other is told why;
* a write and a guided calibration, in both orders;
* an undo racing a write, in both orders;
* a subscription that has been cancelled, and must not be written to afterwards;
* a config entry reloaded under an open subscription.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch

from homeassistant.components.websocket_api import const as ws_const
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from custom_components.myhome.calibration_store import (
    cover_calibration_data,
    loaded_store,
)
from custom_components.myhome.const import CALIBRATION_SOURCE_GUIDED, CONF_OPENING_TIME
from custom_components.myhome.panel_schemas import (
    ERROR_BUSY_CALIBRATING,
    ERROR_UNDO_EXPIRED,
    ERROR_WRITE_IN_PROGRESS,
    WS_EVENT_MEASURING,
    WS_EVENT_OVERVIEW,
    WS_EVENT_SESSION,
    WS_TYPE_OVERVIEW,
    WS_TYPE_SET_TRAVEL,
    WS_TYPE_SUBSCRIBE,
    WS_TYPE_UNDO,
)
from custom_components.myhome.panel_write import async_subscribers

from .helpers_platforms import entity_object, set_connected, setup_myhome
from .test_websocket_api import (
    CALIBRATION,
    FIRST,
    SECOND,
    WRITE_YAML,
    ask,
    refused,
    result,
    row_of,
)


def held_save() -> tuple[Any, asyncio.Event, asyncio.Event]:
    """A `Store.async_save` that stops in the middle and waits to be let go.

    The store save is the one real `await` inside a write, so holding it open is how a
    second frame is guaranteed to arrive while the first write is still being applied -
    rather than hoping two tasks interleave the way the test needs them to.
    """
    inside = asyncio.Event()
    release = asyncio.Event()
    real = Store.async_save

    async def slow(self: Any, data: Any) -> None:
        inside.set()
        await release.wait()
        await real(self, data)

    return slow, inside, release


async def test_two_writes_racing_down_one_socket_leave_exactly_one_of_them(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A confirm button under an impatient finger, and two tabs on the same gateway.

    Two writes are not independent - each reads the store, decides against what it read
    and writes the whole of what it decided - so the second is refused rather than
    queued, and the refusal is a sentence the panel can show (`write_in_progress`)
    rather than a lost frame or a store written twice.

    The store's own save is held open, so the second frame is certain to arrive while
    the first is still inside the write. Both answers are then read off the socket and
    the *file* is checked: one write was applied, and exactly one.

    Mutation caught: queueing the second write; answering the second one with a success
    it did not have. (The narrower claim - that the flag is taken with no `await` between
    it and the refusal - is
    `test_websocket_api.py::test_two_frames_in_one_tick_cannot_both_find_the_gateway_free`,
    and the per-gateway half is `test_panel_two_gateways.py`.)
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        slow, inside, release = held_save()
        with patch.object(Store, "async_save", slow):
            await client.send_json_auto_id(
                {
                    "type": WS_TYPE_SET_TRAVEL,
                    "entry_id": entry.entry_id,
                    "cover_unique_id": FIRST,
                    "height": 180,
                }
            )
            await inside.wait()
            second = await ask(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                cover_unique_id=SECOND,
                height=170,
            )
            release.set()
            first = await client.receive_json()

        assert first["success"] is True, first
        assert second["success"] is False, second
        assert second["error"]["code"] == ws_const.ERR_NOT_ALLOWED
        assert second["error"]["translation_key"] == ERROR_WRITE_IN_PROGRESS

        store = loaded_store(hass, entry)
        assert store.calibration(FIRST).height == 180.0
        # The refused one changed nothing at all: the second shutter kept the travel the
        # fixture gave it, which is the half a refusal has to leave alone.
        assert store.calibration(SECOND).height == 150.0
        # ...and the gateway is writable again the moment the first one is done.
        await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=SECOND,
            height=170,
        )


async def test_a_measurement_that_starts_first_refuses_the_write_that_follows_it(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The first of the two orders, over the socket, with the name in the refusal.

    The panel is told before it tries - `overview.measuring` and the `measuring` event -
    so this is the backstop. What matters here is that the backstop is a *sentence*: the
    frame carries `busy_calibrating` and the window's name in `translation_placeholders`,
    which is what the panel puts in the amber banner.

    Mutation caught: refusing with a bare code; refusing only the writes that name the
    window being measured (the guided conversation stores a profile when it is done, and
    what that profile is worth depends on the assignments it finds).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        cover = entity_object(hass, "cover", "2-81")
        with cover.calibration_session():
            error = await refused(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                # ...a *different* shutter, which is refused all the same.
                cover_unique_id=SECOND,
                height=170,
            )
            assert error["code"] == ws_const.ERR_NOT_ALLOWED
            assert error["translation_key"] == ERROR_BUSY_CALIBRATING
            assert error["translation_placeholders"] == {"cover": "Hallway Shutter"}
            # The reads are not refused: a measurement is exactly when somebody wants to
            # look at the screen.
            overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
            assert overview["measuring"] == {
                "cover_unique_id": FIRST,
                "name": "Hallway Shutter",
            }
        await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=SECOND,
            height=170,
        )


async def test_a_measurement_that_starts_inside_a_write_lets_that_write_finish(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The other order, and the one the lock cannot rule out.

    `_refuse_if_busy` runs before the write, so the only way past it is a session opening
    inside the store save itself. The defined outcome (handoff §1.4) is that the write
    finishes - its records are on the way to the disk and abandoning half of one would be
    worse than either outcome - and the session survives the signal that ends it. Held
    here over the socket, where the answer the panel really receives can be read.

    Mutation caught: a write that re-checks the lock after its own save and answers with
    a refusal for a change it has already made.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        cover = entity_object(hass, "cover", "2-81")
        slow, inside, release = held_save()
        with patch.object(Store, "async_save", slow):
            await client.send_json_auto_id(
                {
                    "type": WS_TYPE_SET_TRAVEL,
                    "entry_id": entry.entry_id,
                    "cover_unique_id": SECOND,
                    "height": 165,
                }
            )
            await inside.wait()
            with cover.calibration_session():
                release.set()
                answer = await client.receive_json()
                assert answer["success"] is True, answer
                assert row_of(answer["result"]["overview"], SECOND)["height"] == 165.0
                # The session is untouched by the swap that landed in it...
                assert cover.calibrating is True
                assert row_of(answer["result"]["overview"], FIRST)["calibrating"] is True
                # ...and the next write is refused, which is the state the panel is shown.
                error = await refused(
                    client,
                    type=WS_TYPE_SET_TRAVEL,
                    entry_id=entry.entry_id,
                    cover_unique_id=SECOND,
                    height=160,
                )
                assert error["translation_key"] == ERROR_BUSY_CALIBRATING
        assert cover.calibrating is False


async def test_a_write_that_lands_first_takes_the_undo_offer_away(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Two writes later, "as they were" is a state that was never on the screen.

    One slot per gateway, withdrawn by the next write: the strip's Annulla is an offer
    about the *last* change, and an undo that skipped a write in between would put back
    records the user never saw together. The refusal is `undo_expired`, which is the
    sentence the panel already shows for a token that has run out of time.

    Mutation caught: a stack of undo tokens; a token that survives the next write.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        first_token = (
            await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                cover_unique_id=FIRST,
                height=180,
            )
        )["undo_token"]
        second_token = (
            await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                cover_unique_id=SECOND,
                height=170,
            )
        )["undo_token"]

        error = await refused(
            client, type=WS_TYPE_UNDO, entry_id=entry.entry_id, undo_token=first_token
        )
        assert error["code"] == ws_const.ERR_NOT_FOUND
        assert error["translation_key"] == ERROR_UNDO_EXPIRED
        # Neither write was disturbed by the refusal.
        assert loaded_store(hass, entry).calibration(FIRST).height == 180.0

        # The live token still takes its own write back, and only its own.
        answer = await result(
            client, type=WS_TYPE_UNDO, entry_id=entry.entry_id, undo_token=second_token
        )
        assert answer["undo_token"] is None
        assert answer["undone"] == "set_travel"
        assert loaded_store(hass, entry).calibration(SECOND).height == 150.0
        assert loaded_store(hass, entry).calibration(FIRST).height == 180.0


async def test_the_dialog_writing_takes_the_undo_offer_away_too(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The guided calibration is a write of the same gateway, so it withdraws the offer.

    Before this, the offer was withdrawn only by a write that came through the panel.
    That left the sequence nobody would think to try and everybody eventually does:
    assign a profile from the panel, walk away, measure that same shutter with a tape
    under "Configura", come back and press Annulla. The token was still live - five
    minutes on the clock, and the guided calibration had not touched it - and the undo
    put the record back as it had been *before the measurement was taken*, silently,
    because an undo restores whatever it snapshotted rather than what it last saw.

    `store.async_set_calibration` is exactly the call `async_step_save` ends with, and
    the hand edit and "Elimina" reach the file through the same `_async_save`, which is
    where the withdrawal is. Driving the store rather than twenty screens of dialog is
    what keeps this test about the rule and not about the conversation.

    Mutation caught: withdrawing from `panel_write` instead of from the store, which
    leaves every writer the panel does not own free to be undone over.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        token = (
            await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                cover_unique_id=FIRST,
                height=180,
            )
        )["undo_token"]
        assert token is not None

        # ...and now the shutter is really measured, through the door the panel is not.
        store = loaded_store(hass, entry)
        await store.async_set_calibration(
            FIRST,
            cover_calibration_data(
                FIRST,
                height=205.0,
                overrides={CONF_OPENING_TIME: 31.5},
                source=CALIBRATION_SOURCE_GUIDED,
            ),
        )

        error = await refused(
            client, type=WS_TYPE_UNDO, entry_id=entry.entry_id, undo_token=token
        )
        assert error["code"] == ws_const.ERR_NOT_FOUND
        assert error["translation_key"] == ERROR_UNDO_EXPIRED
        # The measurement is still the measurement: the refusal changed nothing.
        record = loaded_store(hass, entry).calibration(FIRST)
        assert record.height == 205.0
        assert record.overrides[CONF_OPENING_TIME] == 31.5


async def test_an_undo_is_a_write_and_takes_the_lock_like_one(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A write arriving while an undo is being applied is refused, and the other way.

    An undo is not a rollback: it is a new write of the old records, so it reads the
    store and writes the whole of what it decided exactly as the write it takes back
    did. A change that slipped in beside it would decide against a store the undo is
    halfway through replacing.

    Mutation caught: an undo that writes outside `async_write` (no lock, no signal, no
    push).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        token = (
            await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                cover_unique_id=FIRST,
                height=180,
            )
        )["undo_token"]

        slow, inside, release = held_save()
        with patch.object(Store, "async_save", slow):
            await client.send_json_auto_id(
                {"type": WS_TYPE_UNDO, "entry_id": entry.entry_id, "undo_token": token}
            )
            await inside.wait()
            error = await refused(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                cover_unique_id=SECOND,
                height=170,
            )
            assert error["translation_key"] == ERROR_WRITE_IN_PROGRESS
            release.set()
            undone = await client.receive_json()
        assert undone["success"] is True, undone
        assert loaded_store(hass, entry).calibration(FIRST).height == 195.0


async def test_nothing_is_pushed_into_a_subscription_that_was_cancelled(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """An unsubscribe takes the callback *and* the state watch out of the way.

    The existing test reads the subscriber list; this one reads the socket, which is
    where the failure would really show: a write after the unsubscribe must put its own
    answer down the connection and nothing else, and a measurement starting afterwards
    must put nothing down it at all. A stray event carries a whole overview under a
    subscription id the panel has forgotten, and `home-assistant-js-websocket` drops it
    silently - so this cannot be seen from the browser.

    Mutation caught: removing the callback and leaving the state-change listener;
    removing neither.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        await client.send_json_auto_id({"type": WS_TYPE_SUBSCRIBE, "entry_id": entry.entry_id})
        subscription = await client.receive_json()
        assert subscription["success"] is True
        assert (await client.receive_json())["event"]["type"] == WS_EVENT_OVERVIEW
        # ...and the session event that follows it (0.6.0 wizard, lot B3), read here so
        # that what is left on the socket after the unsubscribe is only what a bug put
        # there.
        assert (await client.receive_json())["event"]["type"] == WS_EVENT_SESSION

        await client.send_json_auto_id(
            {"type": "unsubscribe_events", "subscription": subscription["id"]}
        )
        assert (await client.receive_json())["success"] is True
        await hass.async_block_till_done()
        assert async_subscribers(hass, entry.entry_id) == []

        # A measurement starts and ends, which is the other event this subscription
        # would have carried...
        with entity_object(hass, "cover", "2-81").calibration_session():
            await hass.async_block_till_done()
        await hass.async_block_till_done()

        # ...and then a write. The next frame on the socket is that write's own answer:
        # if anything had been pushed, it would be sitting in front of it.
        answer = await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=SECOND,
            height=170,
        )
        assert row_of(answer["overview"], SECOND)["height"] == 170.0


async def test_a_subscription_survives_the_gateway_being_reloaded_under_it(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A reload builds new entities; the panel's socket does not know that happened.

    A config entry is reloaded by everything but this panel - the options flow on close,
    a changed `myhome.yaml`, the user pressing Reload - and a panel open at the time goes
    on holding one subscription. The subscriber list is keyed by `entry_id`, which
    survives; the `measuring` watch is keyed by entity id, which also survives, and that
    is the half that could have been keyed by the entity *object* instead, which does
    not. Both are held here: a write after the reload still pushes, and a measurement on
    a shutter rebuilt by the reload still raises the lock.

    Mutation caught: a subscription keyed by anything a reload replaces; a `measuring`
    watch registered against the entity objects of the moment it was opened.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        await client.send_json_auto_id({"type": WS_TYPE_SUBSCRIBE, "entry_id": entry.entry_id})
        assert (await client.receive_json())["success"] is True
        assert (await client.receive_json())["event"]["type"] == WS_EVENT_OVERVIEW
        assert (await client.receive_json())["event"]["type"] == WS_EVENT_SESSION

        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        # A reload leaves the gateway handler disconnected until it dials back in, and
        # an unavailable entity publishes no attributes at all - so the reconnection is
        # part of what a reload is, and the `measuring` half of this test is about the
        # shutters as the user has them rather than about the second in between.
        await set_connected(hass, True)
        assert len(async_subscribers(hass, entry.entry_id)) == 1

        # The write still reaches the open panel, with the rebuilt gateway in it.
        await client.send_json_auto_id(
            {
                "type": WS_TYPE_SET_TRAVEL,
                "entry_id": entry.entry_id,
                "cover_unique_id": SECOND,
                "height": 170,
            }
        )
        pushed = await client.receive_json()
        assert pushed["event"]["type"] == WS_EVENT_OVERVIEW
        assert row_of(pushed["event"]["overview"], SECOND)["height"] == 170.0
        assert (await client.receive_json())["success"] is True

        # ...and so does a measurement on an entity object that did not exist when the
        # subscription was opened.
        with entity_object(hass, "cover", "2-81").calibration_session():
            await hass.async_block_till_done()
            event = (await client.receive_json())["event"]
            assert event["type"] == WS_EVENT_MEASURING
            assert event["cover_unique_id"] == FIRST
        await hass.async_block_till_done()
        event = (await client.receive_json())["event"]
        assert event["type"] == WS_EVENT_MEASURING
        assert event["cover_unique_id"] is None
