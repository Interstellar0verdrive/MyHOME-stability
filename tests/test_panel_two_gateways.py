"""A house with two gateways, and the six things that must not be shared between them.

Nearly every installation has one gateway, which is why `entry_id` is optional on the
reads and why a bug that mixes two up would have shipped without anybody noticing until
it reached the one house that has two - where it is not a cosmetic bug: gateway B's
shutters would be told to follow a profile measured on gateway A's windows, or locked
because somebody is measuring a shutter three rooms away, or left running the numbers
they had before a write they never received.

Everything in the panel is keyed by `entry_id` (the store file, the undo slot, the write
lock, the subscriber list) or by the gateway's MAC (the refresh signal). This file sets
two gateways up for real - the only other test in the suite that does is
`test_two_gateways_are_two_subscriptions`, and it covers the subscriber list alone - and
holds each of those keys separately.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from homeassistant.components.websocket_api import const as ws_const
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from custom_components.myhome.calibration_store import loaded_store, storage_key
from custom_components.myhome.const import (
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_PLATFORMS,
    DOMAIN,
    SIGNAL_GATEWAY_CONNECTION,
)
from custom_components.myhome.panel_schemas import (
    ERROR_BUSY_CALIBRATING,
    ERROR_UNDO_EXPIRED,
    ERROR_UNKNOWN_COVER,
    WS_EVENT_OVERVIEW,
    WS_TYPE_ASSIGN,
    WS_TYPE_OVERVIEW,
    WS_TYPE_PROFILE_DELETE,
    WS_TYPE_PROFILE_EDIT,
    WS_TYPE_REORDER,
    WS_TYPE_SET_TRAVEL,
    WS_TYPE_SUBSCRIBE,
    WS_TYPE_UNDO,
)
from custom_components.myhome.panel_write import async_subscribers

from .helpers_core import MAC, MAC2, make_entry, mock_gateway, write_yaml
from .helpers_platforms import mock_commands, setup_myhome
from .test_websocket_api import CALIBRATION, FIRST, SECOND, WRITE_YAML, ask, refused, result, row_of

# Gateway B: two shutters of its own, one of them with run times in the file so that a
# refresh that reached the wrong gateway would be visible in an attribute.
SECOND_YAML = f"""
gateway:
  mac: {MAC2}
  cover:
    garage_shutter:
      where: '81'
      name: Garage Shutter
      opening_time: 40
      closing_time: 39
      height: 200
    cellar_shutter:
      where: '82'
      name: Cellar Shutter
      height: 120
"""

GARAGE = f"{MAC2}-2-81"
CELLAR = f"{MAC2}-2-82"
GARAGE_ENTITY = "cover.garage_shutter"

# Five numbers inside `PROFILE_FIELDS`' own bounds - the rolls are 1-5 and the times
# 1-600, so `dict.fromkeys(..., 10)` is not a profile any command would accept.
PROFILE_NUMBERS = {
    "opening_time": 20.0,
    "closing_time": 19.5,
    "slat_time": 3.5,
    "opening_roll": 1.9,
    "closing_roll": 1.5,
}


@asynccontextmanager
async def two_gateways(hass: HomeAssistant, tmp_path) -> AsyncIterator[tuple[Any, Any]]:
    """Gateway A (with the suite's usual fixture) and gateway B, both loaded."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        first,
        _commands,
    ):
        second = make_entry(write_yaml(tmp_path, SECOND_YAML, name="second.yaml"), mac=MAC2)
        with mock_gateway(), mock_commands():
            second.add_to_hass(hass)
            assert await hass.config_entries.async_setup(second.entry_id)
            await hass.async_block_till_done()
            # ...and B is connected too, or its shutters are `unavailable` and publish
            # no travel attributes at all, which would make half of this file vacuous.
            hass.data[DOMAIN][MAC2][CONF_ENTITY].is_connected = True
            async_dispatcher_send(hass, SIGNAL_GATEWAY_CONNECTION.format(mac=MAC2), True)
            await hass.async_block_till_done()
            try:
                yield first, second
            finally:
                await hass.config_entries.async_unload(second.entry_id)
                await hass.async_block_till_done()


def cover_entity(hass: HomeAssistant, mac: str, key: str) -> Any:
    return hass.data[DOMAIN][mac][CONF_PLATFORMS]["cover"][key][CONF_ENTITIES]["cover"]


async def test_the_two_stores_are_two_files_and_neither_knows_the_other(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A profile, a record and an order written to one gateway reach only that one.

    The store is keyed by `entry_id` (`storage_key`), which is the reason this holds -
    stated here rather than left to be inferred from a key format, because a store keyed
    by the domain would pass every single-gateway test in the suite.

    Mutation caught: one store per integration; `loaded_store` reading the first entry.
    """
    async with two_gateways(hass, tmp_path) as (first, second):
        assert storage_key(first.entry_id) != storage_key(second.entry_id)
        client = await hass_ws_client(hass)

        # B starts with nothing at all, while A carries the fixture's profile and order.
        assert loaded_store(hass, second).raw_profiles == {}
        assert loaded_store(hass, second).raw_covers == {}
        assert loaded_store(hass, second).raw_order == []
        assert sorted(loaded_store(hass, first).raw_profiles) == ["tall"]

        # A write to B: a record, and an order.
        await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=second.entry_id,
            cover_unique_id=GARAGE,
            height=210,
        )
        await result(
            client, type=WS_TYPE_REORDER, entry_id=second.entry_id, order=[CELLAR, GARAGE]
        )
        assert loaded_store(hass, second).raw_order == [CELLAR, GARAGE]
        assert loaded_store(hass, second).calibration(GARAGE).height == 210.0

        # ...and A is exactly as it was, order included.
        assert loaded_store(hass, first).raw_order == [SECOND, FIRST]
        assert loaded_store(hass, first).calibration(GARAGE) is None
        assert sorted(loaded_store(hass, first).raw_profiles) == ["tall"]

        # A profile written to A is not a profile B has: the overviews name their own.
        of_first = await result(client, type=WS_TYPE_OVERVIEW, entry_id=first.entry_id)
        of_second = await result(client, type=WS_TYPE_OVERVIEW, entry_id=second.entry_id)
        assert {row["name"] for row in of_first["profiles"]} == {"tall", "from_the_file"}
        assert of_second["profiles"] == []
        assert {row["unique_id"] for row in of_second["covers"]} == {GARAGE, CELLAR}
        # Both answers list both gateways, so the picker has one rule (CONTRACT §2).
        for overview in (of_first, of_second):
            assert {item["entry_id"] for item in overview["entries"]} == {
                first.entry_id,
                second.entry_id,
            }
            assert all(item["loaded"] for item in overview["entries"])


async def test_a_shutter_of_the_other_gateway_is_a_shutter_that_is_not_there(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Every command is about one gateway, and its unique ids are that gateway's.

    The two sets of ids differ only in the MAC they start with, so a command that looked
    a cover up across every loaded entry would answer, and would then write gateway B's
    record into gateway A's file.

    Mutation caught: resolving a cover from `hass.data[DOMAIN]` rather than from the
    entry's own slice of it.
    """
    async with two_gateways(hass, tmp_path) as (first, _second):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=first.entry_id,
            cover_unique_id=GARAGE,
            height=200,
        )
        assert error["code"] == ws_const.ERR_NOT_FOUND
        assert error["translation_key"] == ERROR_UNKNOWN_COVER

        # ...and an *order* naming it is not an error: a browser tab left open across a
        # reconfiguration is not a client bug, so the id is dropped (CONTRACT §9.2).
        await result(
            client,
            type=WS_TYPE_REORDER,
            entry_id=first.entry_id,
            order=[FIRST, GARAGE, SECOND],
        )
        assert loaded_store(hass, first).raw_order == [FIRST, SECOND]


async def test_each_gateway_has_its_own_undo_and_cannot_spend_the_other_s(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """One slot per gateway, and a token is only a token for the gateway that issued it.

    Two admins on two gateways is the case this exists for: the panel offers "Annulla"
    on both screens at once, and the second write must not withdraw the first screen's
    offer. A token presented to the wrong gateway is `undo_expired` - which is the right
    sentence, because from that gateway's point of view there is nothing to take back.

    Mutation caught: one undo slot for the integration (the second write would silently
    withdraw the other gateway's offer, and the token would then undo the wrong file).
    """
    async with two_gateways(hass, tmp_path) as (first, second):
        client = await hass_ws_client(hass)
        for_first = (
            await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=first.entry_id,
                cover_unique_id=FIRST,
                height=180,
            )
        )["undo_token"]
        for_second = (
            await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=second.entry_id,
                cover_unique_id=GARAGE,
                height=210,
            )
        )["undo_token"]
        assert for_first and for_second and for_first != for_second

        # The wrong gateway does not know it.
        error = await refused(
            client, type=WS_TYPE_UNDO, entry_id=second.entry_id, undo_token=for_first
        )
        assert error["translation_key"] == ERROR_UNDO_EXPIRED
        # ...and the write to B did not withdraw A's offer.
        await result(client, type=WS_TYPE_UNDO, entry_id=first.entry_id, undo_token=for_first)
        assert loaded_store(hass, first).calibration(FIRST).height == 195.0
        assert loaded_store(hass, second).calibration(GARAGE).height == 210.0
        # B's own token is still worth what it was.
        await result(client, type=WS_TYPE_UNDO, entry_id=second.entry_id, undo_token=for_second)
        assert loaded_store(hass, second).calibration(GARAGE) is None


async def test_a_measurement_on_one_gateway_leaves_the_other_free(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The read-only lock is a statement about one gateway's shutters.

    A guided calibration holds one window and will write a profile when it is done, and
    what that profile is worth depends on the assignments it finds - on *that* gateway.
    A house with two would otherwise be unable to touch half of it because somebody is
    measuring a shutter in the other half.

    Mutation caught: `calibrating_now` walking every loaded gateway; the write lock kept
    as a boolean rather than as a set of entry ids.
    """
    async with two_gateways(hass, tmp_path) as (first, second):
        client = await hass_ws_client(hass)
        with cover_entity(hass, MAC, "2-81").calibration_session():
            error = await refused(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=first.entry_id,
                cover_unique_id=SECOND,
                height=170,
            )
            assert error["code"] == ws_const.ERR_NOT_ALLOWED
            assert error["translation_key"] == ERROR_BUSY_CALIBRATING
            assert error["translation_placeholders"]["cover"] == "Hallway Shutter"

            # The other gateway is not measuring anything and is not read-only.
            answer = await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=second.entry_id,
                cover_unique_id=GARAGE,
                height=210,
            )
            assert answer["overview"]["measuring"] is None
            assert row_of(answer["overview"], GARAGE)["height"] == 210.0

        # ...and A comes back the moment the session ends.
        await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=first.entry_id,
            cover_unique_id=SECOND,
            height=170,
        )


async def test_a_write_reaches_the_shutters_of_its_own_gateway_and_no_others(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`SIGNAL_CALIBRATION_CHANGED` is formatted with the MAC, and that is load-bearing.

    Every cover subscribes to its own gateway's signal, so a write to A re-resolves A's
    twelve windows and leaves B's alone. With one signal for the integration a write to
    either gateway would re-resolve every cover in the house - harmless by luck today,
    because each cover resolves against its own store, and a guarantee nobody stated.

    Mutation caught: a signal without the MAC in it; a refresh that walks
    `hass.data[DOMAIN]` instead of the entry it was told about.
    """
    async with two_gateways(hass, tmp_path) as (first, _second):
        client = await hass_ws_client(hass)
        before = hass.states.get(GARAGE_ENTITY).attributes["Opening time"]
        assert before == 40.0

        await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=first.entry_id,
            assignments=[{"cover_unique_id": SECOND, "profile": "tall", "height": 150}],
        )
        await hass.async_block_till_done()

        # A's second shutter swapped its numbers in place...
        assert hass.states.get("cover.landing_shutter").attributes["Profile"] == "tall"
        # ...and B's did not notice anything at all.
        assert hass.states.get(GARAGE_ENTITY).attributes["Opening time"] == before
        assert "Profile" not in hass.states.get(GARAGE_ENTITY).attributes


async def test_two_panels_on_two_gateways_are_told_apart(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """One socket, two subscriptions, and a push that carries the right gateway.

    The existing two-gateway test holds that a panel watching A is not woken by a write
    to B. This is the other half: both subscribed at once, from one connection, which is
    what a browser with two tabs of the same panel really does. The event has to arrive
    under the *subscribing* message's id, or the second tab would redraw itself with the
    first gateway's twelve shutters.

    Mutation caught: one subscriber list for the integration; a push that sends the
    overview of whichever entry wrote last.
    """
    async with two_gateways(hass, tmp_path) as (first, second):
        client = await hass_ws_client(hass)
        ids: dict[str, int] = {}
        for name, entry in (("first", first), ("second", second)):
            await client.send_json_auto_id(
                {"type": WS_TYPE_SUBSCRIBE, "entry_id": entry.entry_id}
            )
            answer = await client.receive_json()
            assert answer["success"], answer
            ids[name] = answer["id"]
            pushed = await client.receive_json()
            assert pushed["id"] == answer["id"]
            assert pushed["event"]["type"] == WS_EVENT_OVERVIEW
            assert pushed["event"]["overview"]["entry_id"] == entry.entry_id

        assert len(async_subscribers(hass, first.entry_id)) == 1
        assert len(async_subscribers(hass, second.entry_id)) == 1

        # A write to B reaches B's subscription only, with B's gateway in it.
        await client.send_json_auto_id(
            {
                "type": WS_TYPE_SET_TRAVEL,
                "entry_id": second.entry_id,
                "cover_unique_id": GARAGE,
                "height": 210,
            }
        )
        pushed = await client.receive_json()
        assert pushed["id"] == ids["second"]
        assert pushed["event"]["overview"]["entry_id"] == second.entry_id
        assert row_of(pushed["event"]["overview"], GARAGE)["height"] == 210.0
        assert (await client.receive_json())["success"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {
            "type": WS_TYPE_PROFILE_EDIT,
            "name": "tall",
            "values": PROFILE_NUMBERS,
            "reference_height": 200,
        },
        {"type": WS_TYPE_PROFILE_DELETE, "name": "tall"},
    ],
    ids=["profile_edit", "profile_delete"],
)
async def test_a_profile_of_one_gateway_is_not_a_profile_of_the_other(
    hass: HomeAssistant, tmp_path, hass_ws_client, payload: dict[str, Any]
) -> None:
    """Profiles are per gateway because they are measurements of its own windows.

    `tall` was measured on a window of gateway A. Gateway B has no profile of that name,
    and asking B to edit or delete it is `unknown_profile` rather than a write that
    reaches across - which would let one screen change the numbers another gateway's
    shutters run on, with nothing on either screen saying so.

    Mutation caught: looking the profile up in the first loaded store.
    """
    async with two_gateways(hass, tmp_path) as (first, second):
        client = await hass_ws_client(hass)
        error = await refused(client, **payload, entry_id=second.entry_id)
        assert error["code"] == ws_const.ERR_NOT_FOUND
        assert error["translation_key"] == "unknown_profile"
        # A's profile is untouched, numbers and all.
        assert loaded_store(hass, first).profile("tall")["opening_time"] == 22.3
        # ...and it still works where it belongs.
        answer = await ask(client, **payload, entry_id=first.entry_id)
        assert answer["success"], answer
