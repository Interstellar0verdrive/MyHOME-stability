"""The panel's three read commands, over a real WebSocket.

Driven through `hass_ws_client`, so the frames under test are the frames the browser
sends: the schema is the registered one, the admin check is the registered decorator's,
and an error code is whatever really came back down the socket rather than whatever a
handler was asked to return. That matters more here than usual, because the payloads
below are a **frozen contract** - `custom_components/myhome/panel_schemas.py` and
`.audit-2026-09/CONTRACT-0.6.0-ws.md` - which the frontend is written against before the
write commands of lot 3 exist. A key renamed here and not there is a blank column in the
panel and no failure anywhere else, so the key lists are asserted whole.

0.6.0 lot 2 is the read half; nothing in this file writes anything, and there is no
command here that could.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.websocket_api import const as ws_const
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, translation

from custom_components.myhome import panel_data, panel_write
from custom_components.myhome.calibration_flow import (
    ERROR_NOT_A_NUMBER,
    ERROR_OUT_OF_RANGE,
)
from custom_components.myhome.calibration_store import (
    async_forget_store,
    cover_calibration_data,
    cover_profile_data,
    loaded_store,
)
from custom_components.myhome.const import (
    CALIBRATION_KEY_ORIGINS,
    CONF_CLOSING_TIME,
    CONF_COVER_UNIQUE_ID,
    CONF_COVERS,
    CONF_OPENING_TIME,
    CONF_ORDER,
    CONF_PROFILES,
    CONF_SLAT_TIME,
    DOMAIN,
)
from custom_components.myhome.panel_data import PREVIEW_PROBLEMS
from custom_components.myhome.panel_schemas import (
    ASSIGN_KEYS,
    COVER_DETAIL_KEY_KEYS,
    COVER_DETAIL_KEYS,
    COVER_EDIT_KEYS,
    COVER_FORGET_KEYS,
    COVER_KEYS,
    ERROR_ADVANCED_COVER,
    ERROR_BUSY_CALIBRATING,
    ERROR_ENTRY_NOT_LOADED,
    ERROR_MISSING_TRAVEL,
    ERROR_PROFILE_NOT_EDITABLE,
    ERROR_UNDO_EXPIRED,
    ERROR_UNKNOWN_COVER,
    ERROR_UNKNOWN_ENTRY,
    ERROR_UNKNOWN_PROFILE,
    ERROR_WRITE_IN_PROGRESS,
    MEASURABLE_KEYS,
    OVERVIEW_KEYS,
    PREVIEW_ITEM_KEYS,
    PREVIEW_KEYS,
    PROFILE_DELETE_KEYS,
    PROFILE_EDIT_KEYS,
    PROFILE_KEYS,
    PROFILE_RENAME_KEYS,
    REORDER_KEYS,
    SET_TRAVEL_KEYS,
    TEXTS_KEYS,
    UNDO_KEYS,
    WS_EVENT_MEASURING,
    WS_EVENT_OVERVIEW,
    WS_READ_COMMANDS,
    WS_TYPE_ASSIGN,
    WS_TYPE_COVER_DETAIL,
    WS_TYPE_COVER_EDIT,
    WS_TYPE_COVER_FORGET,
    WS_TYPE_OVERVIEW,
    WS_TYPE_PREVIEW,
    WS_TYPE_PROFILE_DELETE,
    WS_TYPE_PROFILE_EDIT,
    WS_TYPE_PROFILE_RENAME,
    WS_TYPE_REORDER,
    WS_TYPE_SET_TRAVEL,
    WS_TYPE_SUBSCRIBE,
    WS_TYPE_TEXTS,
    WS_TYPE_UNDO,
    WS_WRITE_COMMANDS,
)
from custom_components.myhome.panel_write import (
    UNDO_TTL,
    PanelError,
    async_set_travel,
    async_subscribers,
    async_write,
)
from custom_components.myhome.websocket_api import WS_REGISTERED

from .helpers_core import MAC, MAC2, make_entry, mock_gateway, write_yaml
from .helpers_platforms import entity_object, mock_commands, setup_myhome
from .test_panel_parity import assert_they_agree

FIRST = f"{MAC}-2-81"
SECOND = f"{MAC}-2-82"
ADVANCED = f"{MAC}-2-83"
FIRST_ENTITY = "cover.hallway_shutter"

HEIGHT = 195.0

# The Italian file, read back to check what the texts command really shipped against what
# is on disk rather than against a copy of it in this module.
IT_FILE = (
    Path(__file__).resolve().parents[1] / "custom_components" / "myhome" / "translations" / "it.json"
)

# Two basic shutters and one advanced one, a profile in the file and a profile in the
# store: the smallest configuration in which every branch of the payload has something
# to say. The first cover writes its own run times, which is what makes "the file" and
# "the profile" two different answers for it.
YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      opening_time: 30
      closing_time: 29
      slat_time: 6
      roll: 1.2
      height: {HEIGHT}
    landing_shutter:
      where: '82'
      name: Landing Shutter
      height: 150
    skylight:
      where: '83'
      name: Skylight
      advanced: true
  cover_profiles:
    from_the_file:
      reference_height: 200
      opening_time: 24
      closing_time: 23
      slat_time: 5
      roll: 1.5
"""

TALL = cover_profile_data(
    "tall",
    reference_height=HEIGHT,
    opening_time=22.3,
    closing_time=21.7,
    slat_time=4.7,
    opening_roll=2.12,
    closing_roll=1.69,
    reference_cover="Hallway Shutter",
    measured_on=FIRST,
    measured_at="2026-09-04T18:12:00+00:00",
)


def record(unique_id: str, **kwargs: Any) -> dict[str, Any]:
    data = cover_calibration_data(unique_id, **kwargs)
    return {key: value for key, value in data.items() if key != CONF_COVER_UNIQUE_ID}


# The first shutter measured two of its own numbers over the profile it follows (which
# is the `adjusted` case), the second only follows it, and the order is the one the user
# dragged them into - the reverse of the file's.
CALIBRATION: dict[str, Any] = {
    CONF_PROFILES: {"tall": TALL},
    CONF_COVERS: {
        FIRST: record(
            FIRST,
            profile="tall",
            profile_wins=True,
            height=HEIGHT,
            overrides={CONF_OPENING_TIME: 25.0, CONF_SLAT_TIME: 4.0},
            measured_at="2026-09-05T09:00:00+00:00",
            raw={"precise": True, "deviation_cm": 1.5},
        ),
        SECOND: record(
            SECOND,
            profile="tall",
            profile_wins=True,
            height=150.0,
            measured_at="2026-09-05T09:02:00+00:00",
        ),
    },
    CONF_ORDER: [SECOND, FIRST],
}

EXAMPLE = Path(__file__).resolve().parent / "fixtures" / "panel_overview_example.json"
# The entry id is a new ULID on every run, so the committed example carries a stable
# stand-in and the comparison puts it back.
EXAMPLE_ENTRY_ID = "01EXAMPLEEXAMPLEEXAMPLEEXA"


async def ask(client, **payload: Any) -> dict[str, Any]:
    """Send one command and hand back the whole answer frame."""
    await client.send_json_auto_id(payload)
    return await client.receive_json()


async def result(client, **payload: Any) -> dict[str, Any]:
    """...and the same, insisting that it worked."""
    message = await ask(client, **payload)
    assert message["success"], message
    return message["result"]


# ------------------------------------------------------------------ registration
async def test_the_commands_are_registered_once_per_home_assistant_run(
    hass: HomeAssistant, tmp_path
) -> None:
    """A command name is global, so it is registered in `async_setup` and guarded.

    Mutation caught: registering per config entry (a second gateway would replace the
    first one's handlers, which is harmless today and stops being harmless the moment a
    command holds a subscription).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (_entry, _commands):
        registered = hass.data["websocket_api"]
        for command in WS_READ_COMMANDS:
            assert command in registered
        assert hass.data[WS_REGISTERED] is True


# ---------------------------------------------------------------------- overview
async def test_the_overview_is_the_whole_gateway_in_one_answer(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Every profile, every basic shutter, in the order the user put them in.

    The key lists are asserted whole against `panel_schemas`, because the frontend is
    written against them before the write commands exist: a renamed key would otherwise
    be a blank column in the panel and a green suite here.

    Mutation caught: dropping `order_index`; listing advanced covers; grouping by
    profile in the payload (the panel groups, the server orders).
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        client = await hass_ws_client(hass)
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)

        assert tuple(overview) == OVERVIEW_KEYS
        assert overview["entry_id"] == entry.entry_id
        assert overview["measuring"] is None
        assert overview["no_basic_covers"] is False
        assert overview["order"] == [SECOND, FIRST]
        assert [item["entry_id"] for item in overview["entries"]] == [entry.entry_id]
        assert overview["entries"][0]["loaded"] is True
        assert overview["entries"][0]["mac"] == MAC

        # The dragged order wins over the file's, and the index is the position in it.
        covers = overview["covers"]
        assert [row["unique_id"] for row in covers] == [SECOND, FIRST]
        assert [row["order_index"] for row in covers] == [0, 1]
        assert all(tuple(row) == COVER_KEYS for row in covers)
        assert ADVANCED not in {row["unique_id"] for row in covers}

        first = covers[1]
        assert first["name"] == "Hallway Shutter"
        assert first["entity_id"] == FIRST_ENTITY
        assert first["profile"] == "tall"
        assert first["profile_from_file"] is False
        assert first["profile_missing"] is False
        # Two numbers of its own over a profile that answers for the rest.
        assert first["origin"] == "adjusted"
        assert first["source"] == "profile tall, adjusted"
        assert first["has_own"] == sorted([CONF_OPENING_TIME, CONF_SLAT_TIME])
        assert first["values"][CONF_OPENING_TIME] == 25.0
        assert first["height"] == HEIGHT
        assert first["level"] == "precise"
        assert first["verify_note"] == 1.5
        assert first["measured_at"] == "2026-09-05T09:00:00+00:00"
        assert first["calibrating"] is False

        profiles = {row["name"]: row for row in overview["profiles"]}
        assert sorted(profiles) == ["from_the_file", "tall"]
        assert all(tuple(row) == PROFILE_KEYS for row in profiles.values())

        tall = profiles["tall"]
        assert tall["source"] == "store"
        assert tall["editable"] is True
        assert tall["reference_height"] == HEIGHT
        assert tall["values"][CONF_OPENING_TIME] == 22.3
        assert tall["measured_on"] == FIRST
        assert tall["measured_on_name"] == "Hallway Shutter"
        assert tall["measured_at"] == "2026-09-04T18:12:00+00:00"
        assert sorted(tall["followers"]) == sorted([FIRST, SECOND])
        assert tall["followers_from_file"] == []
        assert tall["missing"] is False

        # A `cover_profiles:` profile is listed and is not editable here: it belongs to
        # a file this integration has never written.
        assert profiles["from_the_file"]["source"] == "yaml"
        assert profiles["from_the_file"]["editable"] is False
        assert profiles["from_the_file"]["measured_on"] is None
        assert profiles["from_the_file"]["measured_at"] is None


async def test_the_overview_needs_no_entry_id_in_a_house_with_one_gateway(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Nearly every installation has one gateway and should not have to say which.

    Mutation caught: making `entry_id` required (the panel would have to ask twice
    before it could draw anything).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        client = await hass_ws_client(hass)
        overview = await result(client, type=WS_TYPE_OVERVIEW)
        assert overview["entry_id"] == entry.entry_id


async def test_a_measurement_in_progress_is_named_in_the_overview(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The panel's read-only lock hangs off this, so it names the shutter.

    Read off the live entity - the object the guided flow marks - and not off a state
    object, which a reload would leave stale.

    Mutation caught: reporting a bare boolean (the banner could not say which window).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        cover = entity_object(hass, "cover", "2-81")
        client = await hass_ws_client(hass)
        assert (await result(client, type=WS_TYPE_OVERVIEW))["measuring"] is None

        with cover.calibration_session():
            overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
            assert overview["measuring"] == {
                "cover_unique_id": FIRST,
                "name": "Hallway Shutter",
            }
            assert [row["calibrating"] for row in overview["covers"]] == [True, False]


async def test_the_room_is_resolved_on_the_server(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The panel groups and filters by room, so the backend answers the question.

    From the entity's own area, and failing that from its device's - which is how a user
    who filed the gateway under a room and never touched a single cover still sees rooms
    in the panel. Both halves may be `None` and nothing depends on them being there.

    Mutation caught: sending the area *name* only (the filter chips need the id);
    resolving nothing and leaving it to the browser.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        area = ar.async_get(hass).async_get_or_create("Cucina")
        er.async_get(hass).async_update_entity(FIRST_ENTITY, area_id=area.id)
        client = await hass_ws_client(hass)
        covers = {
            row["unique_id"]: row
            for row in (await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id))[
                "covers"
            ]
        }
        assert covers[FIRST]["area_id"] == area.id
        assert covers[FIRST]["area"] == "Cucina"
        # The gateway's own device carries no area in this fixture, so the second
        # shutter has none - and that is a value, not a failure.
        assert covers[SECOND]["area_id"] is None
        assert covers[SECOND]["area"] is None

        # ...until the *device* has one: a user who filed the gateway under a room and
        # never touched a single cover still sees rooms in the panel, which is the
        # fallback the entity registry itself applies.
        landing = er.async_get(hass).async_get("cover.landing_shutter")
        assert landing.device_id is not None
        sala = ar.async_get(hass).async_get_or_create("Sala")
        dr.async_get(hass).async_update_device(landing.device_id, area_id=sala.id)
        covers = {
            row["unique_id"]: row
            for row in (await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id))[
                "covers"
            ]
        }
        assert covers[SECOND]["area_id"] == sala.id
        assert covers[SECOND]["area"] == "Sala"
        # The cover with its own area keeps it: the entity's answer comes first.
        assert covers[FIRST]["area"] == "Cucina"


async def test_an_unknown_gateway_is_not_found(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """...and a gateway that exists but is not loaded is a different sentence.

    Its shutters are not there to be read, which asks the user to do something about the
    gateway rather than about the id they typed.

    Mutation caught: answering an unloaded entry with an empty overview (the panel would
    show a house with no shutters in it and no reason why).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        client = await hass_ws_client(hass)
        message = await ask(client, type=WS_TYPE_OVERVIEW, entry_id="nope")
        assert message["success"] is False
        assert message["error"]["code"] == ws_const.ERR_NOT_FOUND
        assert message["error"]["translation_key"] == ERROR_UNKNOWN_ENTRY
        assert message["error"]["translation_domain"] == DOMAIN

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        message = await ask(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        assert message["success"] is False
        assert message["error"]["code"] == ws_const.ERR_NOT_FOUND
        assert message["error"]["translation_key"] == ERROR_ENTRY_NOT_LOADED


# ------------------------------------------------------------------ cover detail
async def test_a_cover_says_where_every_single_number_came_from(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Key by key: what it runs on, and what it would fall back to without its own.

    The second half is the whole reason this command exists. "Campo vuoto = torna a
    ereditare" is only an honest offer if the screen can print what it would go back to
    *before* the user empties the field, and the destination of "Rimuovi la misura" has
    to be named before anything is removed. It is the same precedence loop run twice,
    not a second rule.

    Mutation caught: computing the inherited value as "the profile's" (for a key the
    file writes and no profile answers, the fall-back is the file's number, not null).
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        client = await hass_ws_client(hass)
        detail = await result(
            client,
            type=WS_TYPE_COVER_DETAIL,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
        )
        assert tuple(detail) == COVER_DETAIL_KEYS
        assert detail["cover"]["unique_id"] == FIRST
        keys = {item["key"]: item for item in detail["keys"]}
        assert all(tuple(item) == COVER_DETAIL_KEY_KEYS for item in keys.values())
        # Four words and no fifth: the detail screen renders each of them, and a token
        # it has never heard of would render as nothing at all.
        assert {item["origin"] for item in keys.values()} <= set(CALIBRATION_KEY_ORIGINS)
        assert {
            item["inherited_origin"] for item in keys.values()
        } <= set(CALIBRATION_KEY_ORIGINS) | {None}

        # Measured on this window: its own, and it would go back to the profile.
        opening = keys[CONF_OPENING_TIME]
        assert opening["own"] is True
        assert opening["origin"] == "own"
        assert opening["value"] == 25.0
        assert opening["inherited_origin"] == "profile"
        assert opening["inherited_value"] == opening["profile_value"] == 22.3
        # ...and the file's own line for the same key is still visible beside it.
        assert opening["file_value"] == 30.0
        assert opening["default_value"] is None

        # Not measured here: the profile answers, and clearing nothing changes nothing.
        closing = keys["closing_time"]
        assert closing["own"] is False
        assert closing["origin"] == "profile"
        assert closing["value"] == closing["inherited_value"] == 21.7

        # The two bus costs are never measured and never scaled, but a profile still
        # carries them (`profile_as_config` fills them with the installation defaults),
        # so for a window that follows one they come from the profile like everything
        # else. Reported as it is, not as it ought to be: the panel's job is to say what
        # the shutter is running on.
        latency = keys["stop_latency"]
        assert latency["origin"] == "profile"
        assert latency["file_value"] is None


async def test_a_cover_with_no_profile_inherits_from_its_own_file(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """With nothing stored, every key is the file's or the default's and owns nothing.

    Mutation caught: marking a file value `own` (the detail screen would offer to remove
    a measurement that was never made).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        client = await hass_ws_client(hass)
        detail = await result(
            client,
            type=WS_TYPE_COVER_DETAIL,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
        )
        keys = {item["key"]: item for item in detail["keys"]}
        assert keys[CONF_OPENING_TIME]["origin"] == "file"
        assert keys[CONF_OPENING_TIME]["own"] is False
        assert keys[CONF_OPENING_TIME]["value"] == 30.0
        assert keys[CONF_OPENING_TIME]["file_value"] == 30.0
        assert keys[CONF_OPENING_TIME]["default_value"] is None
        assert keys[CONF_OPENING_TIME]["profile_value"] is None
        # ...and a key nobody states at all is this integration's own number, which is
        # what `default_value` is for.
        latency = keys["stop_latency"]
        assert latency["origin"] == "default"
        assert latency["file_value"] is None
        assert latency["default_value"] == latency["value"]
        assert detail["cover"]["profile"] is None
        assert detail["cover"]["has_own"] == []


async def test_a_key_the_file_states_through_a_fallback_is_still_the_file_s(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`roll:` states both directions and `opening_time:` states the descent too.

    The validator records only the keys it read, and the precedence widens that by what
    one written key says about another (`_finalize_cover`'s own fallbacks) - which is
    why these keys come back with `origin: "file"`. The two numbers beside that word
    have to be widened by the same rule: a `roll: 1.5` the user typed is not this
    integration's default, and a screen that offered it as one would be telling them
    their own file says nothing.

    Mutation caught: reading the narrower `keys_from_file` in `panel_data` (every one of
    these keys would come back `file_value: null, default_value: <the user's number>`
    under an origin that says the file wrote it).
    """
    yaml_text = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      opening_time: 30
      roll: 1.2
      height: {HEIGHT}
    landing_shutter:
      where: '82'
      name: Landing Shutter
      height: 150
"""
    async with setup_myhome(hass, tmp_path, yaml_text) as (entry, _commands):
        client = await hass_ws_client(hass)
        detail = await result(
            client,
            type=WS_TYPE_COVER_DETAIL,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
        )
        keys = {item["key"]: item for item in detail["keys"]}
        # The descent the file never wrote and nevertheless stated.
        for key in ("closing_time", "opening_roll", "closing_roll"):
            assert keys[key]["origin"] == "file", key
            assert keys[key]["file_value"] == keys[key]["value"], key
            assert keys[key]["default_value"] is None, key

        # ...and a shutter whose file says nothing at all beyond where it is: every key
        # is this integration's own number, which is the one case `default_value` is
        # there for.
        detail = await result(
            client,
            type=WS_TYPE_COVER_DETAIL,
            entry_id=entry.entry_id,
            cover_unique_id=SECOND,
        )
        assert detail["cover"]["origin"] == "defaults"
        for item in detail["keys"]:
            assert item["origin"] == "default", item["key"]
            assert item["own"] is False
            assert item["file_value"] is None
            assert item["profile_value"] is None
            assert item["default_value"] == item["value"] == item["inherited_value"]


async def test_a_shutter_that_is_not_there_and_one_that_is_not_ours(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """"No such cover" and "not a cover this panel does" are two different answers.

    An advanced shutter reports its own position, so it has no travel model to show and
    every calibration primitive refuses it. Telling the user it does not exist would be
    a lie about their own installation.

    Mutation caught: collapsing both onto `ERR_NOT_FOUND`.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        client = await hass_ws_client(hass)
        message = await ask(
            client,
            type=WS_TYPE_COVER_DETAIL,
            entry_id=entry.entry_id,
            cover_unique_id=f"{MAC}-2-99",
        )
        assert message["error"]["code"] == ws_const.ERR_NOT_FOUND
        assert message["error"]["translation_key"] == ERROR_UNKNOWN_COVER

        message = await ask(
            client,
            type=WS_TYPE_COVER_DETAIL,
            entry_id=entry.entry_id,
            cover_unique_id=ADVANCED,
        )
        assert message["error"]["code"] == ws_const.ERR_NOT_SUPPORTED
        assert message["error"]["translation_key"] == ERROR_ADVANCED_COVER
        assert message["error"]["translation_domain"] == DOMAIN


async def test_a_payload_that_is_not_one_is_refused_by_the_schema(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The registered schema is the one under test, not a hand-rolled check.

    Mutation caught: making `cover_unique_id` optional (the handler would go looking for
    `None` and answer "no such cover", which says nothing about the real mistake).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (entry, _commands):
        client = await hass_ws_client(hass)
        message = await ask(client, type=WS_TYPE_COVER_DETAIL, entry_id=entry.entry_id)
        assert message["success"] is False
        assert message["error"]["code"] == ws_const.ERR_INVALID_FORMAT


# ----------------------------------------------------------------------- texts
@pytest.mark.parametrize(
    ("asked", "served", "fallback"),
    [
        ("it", "it", False),
        ("en", "en", False),
        # A regional variant is the language it is a variant of.
        ("it-CH", "it", True),
        ("pt_BR", "pt", True),
        # ...and anything this integration has never been translated into is English,
        # because a panel with no words is worse than a panel in the wrong ones.
        ("zz", "en", True),
    ],
)
async def test_the_panel_is_served_the_nearest_language_there_is(
    hass: HomeAssistant, tmp_path, hass_ws_client, asked: str, served: str, fallback: bool
) -> None:
    """The fallback chain is resolved on the server, which is the only place that knows.

    The browser cannot know which of the seven files exist, and a panel that guessed
    would either ship the list or ask seven times.

    Mutation caught: falling back on the whole tag only (`it-CH` would be English);
    answering without saying which language was served (the panel could not tell a
    translated screen from an untranslated one).
    """
    async with setup_myhome(hass, tmp_path, YAML) as (_entry, _commands):
        client = await hass_ws_client(hass)
        texts = await result(client, type=WS_TYPE_TEXTS, language=asked)
        assert tuple(texts) == TEXTS_KEYS
        assert texts["language"] == served
        assert texts["requested"] == asked
        assert texts["fallback"] is fallback
        # The four blocks the panel really reads: the flow's own wording, the five origin
        # phrases it is forbidden from keeping its own copy of, the sentence behind every
        # refusal's `translation_key`, and its own screens.
        assert "step" in texts["texts"]["options"]
        assert "calibration_origin" in texts["texts"]["selector"]
        assert ERROR_UNKNOWN_COVER in texts["texts"]["exceptions"]
        assert "overview" in texts["texts"]["panel"]
        # Nothing else of the file travels: the panel has no use for the config flow's
        # screens or for the entity names.
        assert set(texts["texts"]) <= {"options", "selector", "exceptions", "panel"}


async def test_the_language_defaults_to_the_one_this_home_assistant_speaks(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Omitted, `language` is the server's - which the panel overrides with the user's.

    Mutation caught: defaulting to English (an Italian installation would open the panel
    in English until the frontend got around to asking again).
    """
    hass.config.language = "fr"
    async with setup_myhome(hass, tmp_path, YAML) as (_entry, _commands):
        client = await hass_ws_client(hass)
        texts = await result(client, type=WS_TYPE_TEXTS)
        assert texts["language"] == "fr"
        assert texts["fallback"] is False


def leaves(tree: Any, prefix: str = "") -> set[str]:
    """Every dotted path of a served block that ends on a string."""
    if not isinstance(tree, dict):
        return {prefix}
    return {key for name, value in tree.items() for key in leaves(value, f"{prefix}.{name}")}


async def test_a_language_still_being_written_is_served_over_english(
    hass: HomeAssistant, tmp_path
) -> None:
    """A key a language has not reached yet arrives in English, not as a dotted key.

    The decision of 14 September: `config_panel` is written in English and Italian while
    the screens that read it are built, and the other five catch up in one translation
    lot before the release. Whole-file selection would put a French user in front of an
    English panel the moment one key was added - or, with no fallback at all, in front of
    a screen of identifiers. `async_texts` lays the language over English key by key
    instead.

    Mutation caught: returning the requested language's file as it stands; merging only
    the top level (a `panel` block would replace English's whole tree); mutating the
    cached English tree while merging, which would serve French words to an English user.
    """
    english = {
        "config_panel": {"overview": {"title": "Profiles and covers", "summary": "Profiles: 2"}},
        "options": {"step": {"init": {"title": "Menu"}}},
    }
    french = {
        "config_panel": {"overview": {"title": "Profils et volets"}},
        "options": {"step": {"init": {"title": "Menu"}}},
    }
    files = {"en": english, "fr": french}
    with patch.object(panel_data, "_read_language", side_effect=files.get):
        answer = await panel_data.async_texts(hass, "fr")
        assert answer["language"] == "fr"
        assert answer["fallback"] is False
        panel = answer["texts"]["panel"]
        assert panel["overview"]["title"] == "Profils et volets"
        assert panel["overview"]["summary"] == "Profiles: 2"

        # ...and English is still English: the merge copies, it does not write back.
        served = await panel_data.async_texts(hass, "en")
        assert served["texts"]["panel"]["overview"]["title"] == "Profiles and covers"


@pytest.mark.parametrize("language", ["it", "fr", "nl", "es", "de", "pt"])
async def test_every_sentence_english_has_reaches_every_language(
    hass: HomeAssistant, tmp_path, language: str
) -> None:
    """The invariant the two-language rule rests on, over the real files.

    `tests/test_translations.py` lets the five lagging files carry a subset of
    `config_panel`; this is the other half of that permission - whatever they are missing,
    the panel is still served a complete book, because English is underneath. It holds
    just as well on the day the translation lot fills them.

    Mutation caught: dropping the merge, which would make a missing key a dotted
    identifier on a French screen with nothing failing anywhere.
    """
    english = await panel_data.async_texts(hass, "en")
    served = await panel_data.async_texts(hass, language)
    assert served["language"] == language
    for block in english["texts"]:
        assert leaves(served["texts"][block]) == leaves(english["texts"][block]), block


async def test_the_panels_own_block_arrives_under_the_name_the_frontend_uses(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`config_panel` in the file, `panel` in the payload, and the whole tree in between.

    The rename is not cosmetic and it is not a schema: Home Assistant's `hassfest`
    validates `strings.json` against a closed list of top-level keys, on which
    `config_panel` is the entry meant for a panel's own words and `panel` is not there at
    all - so the file cannot use the name the frontend is written against. This is the
    one place the two names meet, and a panel that asked for `t("panel.overview.title")`
    against a payload that said `config_panel` would render dotted identifiers on every
    screen with nothing failing anywhere else.

    Mutation caught: serving the block under its own name; dropping it from the filter
    (the whole panel would go wordless); shipping the sentences flattened or half.
    """
    async with setup_myhome(hass, tmp_path, YAML) as (_entry, _commands):
        client = await hass_ws_client(hass)
        texts = await result(client, type=WS_TYPE_TEXTS, language="it")
        panel = texts["texts"]["panel"]
        assert "config_panel" not in texts["texts"]
        # The eleven views, verbatim from the file rather than a subset of it.
        assert set(panel) == set(json.loads(IT_FILE.read_text(encoding="utf-8"))["config_panel"])
        # ...and nested, not flattened: the frontend walks `panel.common.action.close`.
        assert panel["common"]["action"]["close"] == "Chiudi"
        assert panel["overview"]["title"] == "Profili e tapparelle"


# ------------------------------------------------------------------- permissions
@pytest.mark.parametrize(
    "payload",
    [
        {"type": WS_TYPE_OVERVIEW},
        {"type": WS_TYPE_COVER_DETAIL, "entry_id": "x", "cover_unique_id": FIRST},
        {"type": WS_TYPE_TEXTS, "language": "it"},
    ],
    ids=["overview", "cover_detail", "texts"],
)
async def test_a_household_member_is_refused_every_one_of_them(
    hass: HomeAssistant, tmp_path, hass_ws_client, hass_admin_user, payload: dict[str, Any]
) -> None:
    """A shutter's travel model is a setting, not a state.

    Somebody who can open a cover has no business rewriting what "open" means, and the
    reads are behind the same door as the writes because the panel itself is admin-only:
    an exception for the reads would only be a second way into the same room.

    Mutation caught: dropping `require_admin` from any single command.
    """
    hass_admin_user.groups = []
    async with setup_myhome(hass, tmp_path, YAML) as (_entry, _commands):
        client = await hass_ws_client(hass)
        message = await ask(client, **payload)
        assert message["success"] is False
        assert message["error"]["code"] == ws_const.ERR_UNAUTHORIZED


# --------------------------------------------------------------- the frozen example
async def test_the_committed_example_is_still_what_the_server_sends(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`tests/fixtures/panel_overview_example.json` is the frontend's stand-in server.

    The screen engine and the views are built against that file before the write
    commands exist, so it has to be the real payload and not a hand-written likeness of
    one. This test regenerates it and compares, which makes a change to the contract a
    failing test *and* a visible diff in the fixture rather than a surprise in the
    browser three lots later.

    Run `python -m pytest tests/test_websocket_api.py -k committed_example` after any
    deliberate change, read the diff, and update the file.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        area = ar.async_get(hass).async_get_or_create("Cucina")
        er.async_get(hass).async_update_entity(FIRST_ENTITY, area_id=area.id)
        client = await hass_ws_client(hass)
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)

    # The entry id and the area id are new on every run; everything else is the fixture.
    serialised = json.dumps(overview).replace(entry.entry_id, EXAMPLE_ENTRY_ID).replace(
        area.id, "cucina"
    )
    assert json.loads(serialised) == json.loads(EXAMPLE.read_text(encoding="utf-8"))


async def test_the_store_the_example_was_built_from_is_the_one_on_disk(
    hass: HomeAssistant, tmp_path
) -> None:
    """A sanity check on the fixture above: the store really holds what it claims.

    Without it, a broken `setup_myhome` would make the example test pass by producing
    the same empty payload twice.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        store = loaded_store(hass, entry)
        assert store.raw_order == [SECOND, FIRST]
        assert sorted(store.raw_profiles) == ["tall"]
        assert sorted(store.raw_covers) == sorted([FIRST, SECOND])


# ======================================================================== the writes
# Nine commands and one subscription (0.6.0 lot 3). The frames below are the frames the
# browser sends, and what comes back is what really came down the socket: the schema is
# the registered one, the admin check the registered decorator's, and the refusals are
# the codes a client would have to handle.
#
# The invariant every one of them ends on is the one `test_panel_parity.py` states - the
# row the panel draws and the attributes the shutter publishes are one answer - because
# a write applies its numbers to the entity **in place** now (plan decision 4) rather
# than reloading the config entry, and an in-place swap is exactly where the two could
# start disagreeing.

THIRD = f"{MAC}-2-84"
SECOND_ENTITY = "cover.landing_shutter"
THIRD_ENTITY = "cover.attic_shutter"

# The reading fixture plus one shutter nobody has ever measured or given a travel to:
# the window a profile cannot be scaled onto, which is what the "corse mancanti" form
# exists for. Kept apart from `YAML` so the frozen example stays the payload it is.
# A second gateway, for the one test that needs two of them: the smallest thing that
# can be set up beside the first, because what it is for is the keying of the
# subscriber list and the undo slot and not anything it says about shutters.
SECOND_GATEWAY_YAML = f"""
gateway:
  mac: {MAC2}
  cover:
    garage_shutter:
      where: '81'
      name: Garage Shutter
      height: 200
"""

WRITE_YAML = YAML.replace(
    """    skylight:""",
    """    attic_shutter:
      where: '84'
      name: Attic Shutter
    skylight:""",
)


async def refused(client, **payload: Any) -> dict[str, Any]:
    """...and the same, insisting that it did not work."""
    message = await ask(client, **payload)
    assert message["success"] is False, message
    return message["error"]


def row_of(overview: dict[str, Any], unique_id: str) -> dict[str, Any]:
    return next(row for row in overview["covers"] if row["unique_id"] == unique_id)


def profile_of(overview: dict[str, Any], name: str) -> dict[str, Any]:
    return next(row for row in overview["profiles"] if row["name"] == name)


# ------------------------------------------------------------------ registration
async def test_every_write_command_is_registered_too(hass: HomeAssistant, tmp_path) -> None:
    """The nine writes and the subscription, under the one flag the reads use."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML) as (_entry, _commands):
        registered = hass.data["websocket_api"]
        for command in (*WS_WRITE_COMMANDS, WS_TYPE_SUBSCRIBE):
            assert command in registered


@pytest.mark.parametrize(
    "payload",
    [
        {"type": WS_TYPE_ASSIGN, "entry_id": "x", "assignments": []},
        {"type": WS_TYPE_REORDER, "entry_id": "x", "order": []},
        {"type": WS_TYPE_SET_TRAVEL, "entry_id": "x", "cover_unique_id": FIRST, "height": 200},
        {"type": WS_TYPE_COVER_EDIT, "entry_id": "x", "cover_unique_id": FIRST, "overrides": {}},
        {"type": WS_TYPE_COVER_FORGET, "entry_id": "x", "cover_unique_id": FIRST},
        {
            "type": WS_TYPE_PROFILE_EDIT,
            "entry_id": "x",
            "name": "tall",
            "values": dict.fromkeys(MEASURABLE_KEYS, 10),
            "reference_height": 200,
        },
        {"type": WS_TYPE_PROFILE_RENAME, "entry_id": "x", "name": "tall", "new_name": "short"},
        {"type": WS_TYPE_PROFILE_DELETE, "entry_id": "x", "name": "tall"},
        {"type": WS_TYPE_UNDO, "entry_id": "x", "undo_token": "deadbeef"},
        {"type": WS_TYPE_SUBSCRIBE},
    ],
    ids=[
        "assign",
        "reorder",
        "set_travel",
        "cover_edit",
        "cover_forget",
        "profile_edit",
        "profile_rename",
        "profile_delete",
        "undo",
        "subscribe",
    ],
)
async def test_a_household_member_may_not_write_either(
    hass: HomeAssistant, tmp_path, hass_ws_client, hass_admin_user, payload: dict[str, Any]
) -> None:
    """Rewriting what "open" means is a setting, and settings are the admin's.

    Mutation caught: dropping `require_admin` from any single write.
    """
    hass_admin_user.groups = []
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        _entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(client, **payload)
        assert error["code"] == ws_const.ERR_UNAUTHORIZED


# ------------------------------------------------------------------------- assign
async def test_assign_points_a_shutter_at_a_profile_and_answers_with_the_gateway(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """One write: the assignment, the travel it needs, and the whole overview back.

    The travel is in the batch because a profile is the measurement of a window of a
    certain height and this window's height was never known - which is the one thing
    that can stop an assignment, and the reason the review panel collects it first.

    Mutation caught: answering with a patch instead of the whole overview; dropping the
    supplied height (the profile would be applied unscaled).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": THIRD, "profile": "tall", "height": 180}],
        )
        assert tuple(answer) == ASSIGN_KEYS
        assert answer["applied"] == 1
        assert isinstance(answer["undo_token"], str)

        row = row_of(answer["overview"], THIRD)
        assert row["profile"] == "tall"
        assert row["profile_from_file"] is False
        assert row["origin"] == "inherited"
        assert row["height"] == 180.0
        # ...and the shutter itself is running on it, with no reload in between.
        assert_they_agree(hass, row, THIRD_ENTITY, origin="inherited")


async def test_assign_refuses_the_whole_batch_when_a_window_has_no_travel(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A profile cannot be scaled onto a window nobody has measured.

    And the batch is refused whole, not half applied: a screen that had to explain which
    half went through would be worse than one that explains what is missing.

    Mutation caught: writing the items that passed; accepting a profile with no travel
    (every follower would be scaled as though it were the reference window).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[
                {"cover_unique_id": SECOND, "profile": None},
                {"cover_unique_id": THIRD, "profile": "tall"},
            ],
        )
        assert error["code"] == ws_const.ERR_SERVICE_VALIDATION_ERROR
        assert error["translation_key"] == ERROR_MISSING_TRAVEL
        assert THIRD in error["message"]

        # Nothing was written: the item that would have passed did not either.
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        assert row_of(overview, SECOND)["profile"] == "tall"


# The three refusals a batch can raise whose sentence is written around the *item's* own
# words: a profile name, a field name, a pair of bounds. `_refuse_the_batch` rebuilds one
# refusal for the whole batch and used to throw those away, so the sentence reached the
# screen with its braces showing - REVIEW-0.6.0-lot6 §5.1, and `out_of_range` is reachable
# from the review panel's own "corse mancanti" form, because `height` is `vol.Any(float,
# int, str)` and everything else about it is decided here.
BRACED_REFUSALS: tuple[tuple[str, dict[str, Any], str], ...] = (
    (ERROR_UNKNOWN_PROFILE, {"cover_unique_id": FIRST, "profile": "gone"}, "gone"),
    (
        ERROR_NOT_A_NUMBER,
        {"cover_unique_id": FIRST, "profile": "tall", "height": "abc"},
        "height",
    ),
    (
        ERROR_OUT_OF_RANGE,
        {"cover_unique_id": FIRST, "profile": "tall", "height": 5000},
        "height",
    ),
    # The one the batch's own `{covers}`/`{count}` are for: it has to keep working.
    (ERROR_MISSING_TRAVEL, {"cover_unique_id": THIRD, "profile": "tall"}, THIRD),
)


@pytest.mark.parametrize(
    ("key", "assignment", "expected"),
    BRACED_REFUSALS,
    ids=[key for key, _assignment, _expected in BRACED_REFUSALS],
)
async def test_a_refused_batch_carries_the_words_its_own_sentence_asks_for(
    hass: HomeAssistant,
    tmp_path,
    hass_ws_client,
    key: str,
    assignment: dict[str, Any],
    expected: str,
) -> None:
    """The refusal is rendered the way Home Assistant renders it, and has no braces left.

    `exceptions.<key>.message` is resolved by
    `homeassistant.helpers.translation.async_get_exception_message`, which formats the
    sentence with whatever `translation_placeholders` carried. A batch that reports
    `unknown_profile` with only `{covers}` and `{count}` in the dict therefore renders
    "No stored profile is called “{profile}”." verbatim, braces and all.

    Mutation caught: rebuilding the batch's refusal from the keys alone and dropping the
    offending item's own placeholders (REVIEW-0.6.0-lot6 §5.1).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[assignment],
        )
        assert error["translation_key"] == key
        assert error["translation_domain"] == DOMAIN

        await translation.async_load_integrations(hass, {DOMAIN})
        rendered = translation.async_get_exception_message(
            DOMAIN, key, error["translation_placeholders"]
        )
        # The key itself comes back when nothing was found, which would make the rest of
        # this test vacuous.
        assert rendered != key
        assert "{" not in rendered, rendered
        assert expected in rendered


async def test_assign_names_every_item_it_refuses(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """An unknown id, an advanced shutter and a profile nobody defines, in one message.

    A WebSocket error carries one key, so the key is the first kind of problem and the
    sentence names each offending item with its own reason - which is what lets the panel
    mark the rows rather than only showing a banner.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[
                {"cover_unique_id": "nobody", "profile": None},
                {"cover_unique_id": ADVANCED, "profile": None},
                {"cover_unique_id": FIRST, "profile": "gone"},
            ],
        )
        assert error["code"] == ws_const.ERR_SERVICE_VALIDATION_ERROR
        assert f"nobody: {ERROR_UNKNOWN_COVER}" in error["message"]
        assert f"{ADVANCED}: {ERROR_ADVANCED_COVER}" in error["message"]
        assert f"{FIRST}: unknown_profile" in error["message"]


async def test_assign_puts_a_shutter_at_the_end_of_the_group_it_joins(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Assigned without a drop position - the tap path, the keyboard path.

    The end of the target group is the one place that is not a place somebody else
    chose. Groups are slices of the one flat order, so the splice is after the last
    member the group already has.

    Mutation caught: appending to the end of the whole list (the shutter would land
    under a different group and the user's order would rearrange itself).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        # The stored order is [SECOND, FIRST]; the third shutter follows nothing and so
        # comes after them both, in the file's order.
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        assert [row["unique_id"] for row in overview["covers"]] == [SECOND, FIRST, THIRD]

        answer = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": THIRD, "profile": "tall", "height": 180}],
        )
        # `tall` is [SECOND, FIRST]; the new follower goes after FIRST and not after
        # everything else, which here is the same place and in a bigger house is not.
        assert answer["overview"]["order"] == [SECOND, FIRST, THIRD]
        assert [row["unique_id"] for row in answer["overview"]["covers"]] == [
            SECOND,
            FIRST,
            THIRD,
        ]


async def test_assign_writes_the_order_it_is_given(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Assignment and position are one write, because on the screen they are one drop."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": THIRD, "profile": "tall", "height": 180}],
            order=[THIRD, FIRST, SECOND],
        )
        assert answer["overview"]["order"] == [THIRD, FIRST, SECOND]
        assert [row["unique_id"] for row in answer["overview"]["covers"]] == [
            THIRD,
            FIRST,
            SECOND,
        ]


async def test_assign_takes_a_profile_away_and_the_shutter_goes_back_to_its_file(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`profile: null` is "Togli dal profilo", which is a drop zone of its own.

    What the window keeps is what was measured *on it*: the overrides and the travel are
    statements about that window and have nothing to do with which kind of shutter it is.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": FIRST, "profile": None}],
        )
        row = row_of(answer["overview"], FIRST)
        assert row["profile"] is None
        assert row["origin"] == "measured"
        assert row["has_own"] == sorted([CONF_OPENING_TIME, CONF_SLAT_TIME])
        assert_they_agree(hass, row, FIRST_ENTITY, origin="measured")


# ------------------------------------------------------------------------ reorder
async def test_reorder_takes_the_whole_gateway_s_order(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The list the overview hands out, sent back whole (CONTRACT §2)."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_REORDER,
            entry_id=entry.entry_id,
            order=[FIRST, THIRD, SECOND, "a shutter that is not there"],
        )
        assert tuple(answer) == REORDER_KEYS
        # An id that names nothing is dropped rather than stored: a browser tab left
        # open across a reconfiguration must not write back a shutter that is gone.
        assert answer["overview"]["order"] == [FIRST, THIRD, SECOND]


async def test_reorder_of_one_group_leaves_the_other_groups_where_they_are(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A drag inside a group is a change to that group and to nothing else.

    The group's members go back into the places that group already holds in the one flat
    order, so the shutters that follow nothing do not move at all.

    Mutation caught: replacing the whole order with the group's list (every other
    shutter would be dropped out of the stored order).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_REORDER,
            entry_id=entry.entry_id,
            profile="tall",
            order=[FIRST, SECOND],
        )
        assert answer["overview"]["order"] == [FIRST, SECOND, THIRD]


async def test_reorder_of_one_group_keeps_every_member_of_it(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A group's list is that group's *full* order, and a short one costs nobody a place.

    The group's members are put back into the seats that group holds in the one flat
    order - one seat per member - so a list naming fewer than all of them would leave a
    seat empty and drop a shutter out of the stored order altogether. On the screen that
    is a window jumping to the end of its group for no reason anybody can see.

    Mutation caught: `zip(seats, wanted, strict=False)` without the tail that puts the
    members the list left out back at the end of the group.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_REORDER,
            entry_id=entry.entry_id,
            profile="tall",
            order=[FIRST],
        )
        assert set(answer["overview"]["order"]) == {FIRST, SECOND, THIRD}


async def test_reorder_refuses_an_order_that_names_a_shutter_twice(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Each shutter sits in exactly one place, so a repeated id is a broken client.

    Refused at the schema rather than quietly deduplicated: a deduplicated list is a
    stored order different from the one on the screen, with nothing saying so.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_REORDER,
            entry_id=entry.entry_id,
            order=[FIRST, SECOND, FIRST],
        )
        assert error["code"] == ws_const.ERR_INVALID_FORMAT
        error = await refused(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": FIRST, "profile": None}],
            order=[FIRST, FIRST],
        )
        assert error["code"] == ws_const.ERR_INVALID_FORMAT


async def test_reorder_refuses_a_shutter_that_does_not_follow_that_profile(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A group's order is about that group: an id from elsewhere is a client bug."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_REORDER,
            entry_id=entry.entry_id,
            profile="tall",
            order=[FIRST, THIRD],
        )
        assert error["code"] == ws_const.ERR_SERVICE_VALIDATION_ERROR
        assert error["translation_key"] == ERROR_UNKNOWN_COVER


# --------------------------------------------------------------------- set_travel
async def test_set_travel_rescales_the_profile_onto_that_window(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The one number every scaled profile depends on, and `null` takes it back."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        before = row_of(
            await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id), SECOND
        )
        answer = await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=SECOND,
            height=100,
        )
        assert tuple(answer) == SET_TRAVEL_KEYS
        row = row_of(answer["overview"], SECOND)
        assert row["height"] == 100.0
        assert row["values"][CONF_OPENING_TIME] < before["values"][CONF_OPENING_TIME]
        assert_they_agree(hass, row, SECOND_ENTITY)


async def test_set_travel_refuses_a_number_the_guided_form_would_refuse(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The bounds are the dialog's own (`MIN_HEIGHT_CM`/`MAX_HEIGHT_CM`), not a copy.

    Mutation caught: widening the range here (the panel would store a travel the guided
    conversation refuses, and the two screens would disagree about the same window).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=SECOND,
            height=5,
        )
        assert error["code"] == ws_const.ERR_SERVICE_VALIDATION_ERROR
        assert error["translation_key"] == "out_of_range"


@pytest.mark.parametrize(
    ("unique_id", "code", "key"),
    [
        ("nobody", ws_const.ERR_NOT_FOUND, ERROR_UNKNOWN_COVER),
        (ADVANCED, ws_const.ERR_NOT_SUPPORTED, ERROR_ADVANCED_COVER),
    ],
    ids=["unknown", "advanced"],
)
async def test_a_write_tells_an_unknown_shutter_from_one_it_does_not_do(
    hass: HomeAssistant, tmp_path, hass_ws_client, unique_id: str, code: str, key: str
) -> None:
    """Two different answers, because they ask the user to do two different things."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=unique_id,
            height=200,
        )
        assert error["code"] == code
        assert error["translation_key"] == key


# --------------------------------------------------------------------- cover_edit
async def test_cover_edit_stores_a_number_and_an_empty_field_goes_back_to_inheriting(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`null` is "stop overriding": the key leaves the record and the window inherits.

    Which is what the empty field with its "eredita N" placeholder means, and the one
    way to take back a number measured by mistake without deleting the whole record and
    the assignment with it.

    Mutation caught: storing `null` as a zero; replacing the whole override block (the
    key the message does not mention would be thrown away).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_COVER_EDIT,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            overrides={CONF_OPENING_TIME: "26,5", CONF_SLAT_TIME: None},
        )
        assert tuple(answer) == COVER_EDIT_KEYS
        row = row_of(answer["overview"], FIRST)
        # A comma is a decimal point to the person holding the tape, and the parser is
        # the guided dialog's own.
        assert row["values"][CONF_OPENING_TIME] == 26.5
        assert row["has_own"] == [CONF_OPENING_TIME]
        # ...and the profile goes on answering for the key that was cleared.
        assert row["profile"] == "tall"
        assert row["origin"] == "adjusted"
        assert_they_agree(hass, row, FIRST_ENTITY, origin="adjusted")


async def test_cover_edit_refuses_a_key_the_travel_model_does_not_know(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Refused by the registered schema, naming the key, rather than stored and ignored."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_COVER_EDIT,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            overrides={"curtain_colour": 3},
        )
        assert error["code"] == ws_const.ERR_INVALID_FORMAT


async def test_cover_edit_that_clears_everything_deletes_the_record(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A record holding only a source and a timestamp is invisible and immortal.

    The dialog's hand edit has deleted such a record all along (0.5.0 v2 review,
    RISK-3); so does this, through the same rule and not a second one.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": FIRST, "profile": None}],
        )
        await result(
            client,
            type=WS_TYPE_COVER_EDIT,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            overrides=dict.fromkeys(MEASURABLE_KEYS),
            height=None,
        )
        assert FIRST not in loaded_store(hass, entry).raw_covers


# ------------------------------------------------------------------- cover_forget
async def test_cover_forget_says_where_the_window_falls_back_to(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Removing a measurement names its destination before the user goes looking.

    Resolved after the deletion rather than predicted before it, so the sentence and the
    shutter are the same answer. This window writes its own run times in `myhome.yaml`
    and its record carried the assignment, so with the record gone it is the file's.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client, type=WS_TYPE_COVER_FORGET, entry_id=entry.entry_id, cover_unique_id=FIRST
        )
        assert tuple(answer) == COVER_FORGET_KEYS
        assert answer["falls_back_to"] == "file"
        assert answer["profile"] is None
        row = row_of(answer["overview"], FIRST)
        assert row["origin"] == "from_the_file"
        assert row["has_own"] == []
        assert_they_agree(hass, row, FIRST_ENTITY, origin="from_the_file")


# ------------------------------------------------------------------- profile_edit
async def test_profile_edit_reaches_every_follower(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A follower holds the *name*, so an edit reaches it on the next resolution.

    Which is now, without a reload: `affected` names the windows and the shutters
    themselves are already running on the new numbers by the time the answer arrives.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_PROFILE_EDIT,
            entry_id=entry.entry_id,
            name="tall",
            values={
                CONF_OPENING_TIME: 30.0,
                "closing_time": 29.0,
                CONF_SLAT_TIME: 5.0,
                "opening_roll": 2.0,
                "closing_roll": 1.8,
            },
            reference_height=HEIGHT,
        )
        assert tuple(answer) == PROFILE_EDIT_KEYS
        assert answer["affected"] == sorted([FIRST, SECOND])
        tall = profile_of(answer["overview"], "tall")
        assert tall["values"][CONF_OPENING_TIME] == 30.0
        # The provenance is carried over: the window it was measured on is still the
        # window it was measured on, and only the date it was last stated moves.
        assert tall["measured_on"] == FIRST
        assert tall["measured_at"] != "2026-09-04T18:12:00+00:00"
        # The follower that measured nothing of its own runs on the new numbers.
        assert_they_agree(hass, row_of(answer["overview"], SECOND), SECOND_ENTITY)


async def test_a_profile_written_in_the_file_is_not_the_panel_s_to_change(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`cover_profiles:` is a block of the user's own file, and this does not write it."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        for payload in (
            {
                "type": WS_TYPE_PROFILE_EDIT,
                "name": "from_the_file",
                "values": dict.fromkeys(MEASURABLE_KEYS, 10),
                "reference_height": 200,
            },
            {"type": WS_TYPE_PROFILE_RENAME, "name": "from_the_file", "new_name": "taller"},
            {"type": WS_TYPE_PROFILE_DELETE, "name": "from_the_file"},
        ):
            error = await refused(client, entry_id=entry.entry_id, **payload)
            assert error["code"] == ws_const.ERR_NOT_ALLOWED
            assert error["translation_key"] == ERROR_PROFILE_NOT_EDITABLE


# ----------------------------------------------------------------- profile_rename
async def test_profile_rename_moves_every_follower_and_leaves_no_old_key(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Three writes in one awaited sequence, in the order that leaves no gap.

    The numbers go in under the new name, the followers are repointed, and only then is
    the old name removed - so nothing in between leaves a shutter following a name
    nobody defines.

    Mutation caught: removing the old profile first (`async_remove_profile` would strip
    the assignment off every follower on the way).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_PROFILE_RENAME,
            entry_id=entry.entry_id,
            name="tall",
            new_name="taller",
        )
        assert tuple(answer) == PROFILE_RENAME_KEYS
        assert answer["moved"] == 2
        assert answer["from_file"] == []
        names = [row["name"] for row in answer["overview"]["profiles"]]
        assert "tall" not in names
        assert "taller" in names
        assert row_of(answer["overview"], FIRST)["profile"] == "taller"
        assert loaded_store(hass, entry).profile("tall") is None
        assert_they_agree(hass, row_of(answer["overview"], SECOND), SECOND_ENTITY)


@pytest.mark.parametrize(
    ("new_name", "key"),
    [("from_the_file", "name_in_use"), ("not a name", "invalid_name")],
    ids=["taken", "not a name"],
)
async def test_profile_rename_refuses_a_name_it_cannot_use(
    hass: HomeAssistant, tmp_path, hass_ws_client, new_name: str, key: str
) -> None:
    """A profile name is a YAML key, because the user may move it into their own file."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client,
            type=WS_TYPE_PROFILE_RENAME,
            entry_id=entry.entry_id,
            name="tall",
            new_name=new_name,
        )
        assert error["code"] == ws_const.ERR_SERVICE_VALIDATION_ERROR
        assert error["translation_key"] == key


# ----------------------------------------------------------------- profile_delete
async def test_profile_delete_names_the_shutters_before_and_after(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Two lists, because the deletion reaches the two kinds of follower differently.

    A stored assignment goes with the profile; a `profile:` line in `myhome.yaml` stays
    in the file and starts naming nothing, which this cannot touch and the user has to
    be told about.
    """
    # The validator refuses a `profile:` line naming a profile `cover_profiles:` does
    # not define, so a window can only follow through the file a name the file defines -
    # and the only way a *stored* profile has followers of that kind is the clash the
    # store wins: one name, written in both places. Deleting the stored one is then
    # exactly the write those windows have to be warned about, because the file's
    # profile, shadowed until now, comes back and their numbers change.
    yaml_text = WRITE_YAML.replace(
        """      name: Attic Shutter""",
        """      name: Attic Shutter
      profile: tall""",
    ).replace(
        """  cover_profiles:""",
        """  cover_profiles:
    tall:
      reference_height: 200
      opening_time: 40
      closing_time: 39
      roll: 1.1""",
    )
    async with setup_myhome(hass, tmp_path, yaml_text, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        before = row_of(
            await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id), THIRD
        )
        answer = await result(
            client, type=WS_TYPE_PROFILE_DELETE, entry_id=entry.entry_id, name="tall"
        )
        assert tuple(answer) == PROFILE_DELETE_KEYS
        assert answer["covers_affected"] == sorted([FIRST, SECOND])
        assert answer["from_file"] == [THIRD]
        # The stored profile is gone and the file's own one is what `tall` means now.
        row = row_of(answer["overview"], THIRD)
        assert row["profile"] == "tall"
        assert row["profile_from_file"] is True
        assert profile_of(answer["overview"], "tall")["source"] == "yaml"
        assert row["values"][CONF_OPENING_TIME] != before["values"][CONF_OPENING_TIME]
        assert_they_agree(hass, row, THIRD_ENTITY)


# -------------------------------------------------------------------------- the lock
async def test_no_write_is_taken_while_a_shutter_is_being_measured(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A guided conversation is holding a shutter and has numbers half measured.

    The panel is told before it tries - `overview.measuring`, and the `measuring` event -
    so this is the backstop. It is a backstop for every write and not only the ones that
    touch that window: the conversation will write a profile when it is done, and what
    that profile is worth depends on the assignments it finds.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        cover = entity_object(hass, "cover", "2-81")
        with cover.calibration_session():
            await hass.async_block_till_done()
            error = await refused(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                cover_unique_id=SECOND,
                height=160,
            )
            assert error["code"] == ws_const.ERR_NOT_ALLOWED
            assert error["translation_key"] == ERROR_BUSY_CALIBRATING
            assert error["translation_placeholders"]["cover"] == "Hallway Shutter"

        # ...and the moment it is over, the same write goes through.
        answer = await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=SECOND,
            height=160,
        )
        assert row_of(answer["overview"], SECOND)["height"] == 160.0


# ---------------------------------------------------------------------------- undo
async def test_undo_puts_the_records_back_and_only_works_once(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """One slot per gateway: a token is good until the next write, and then it is not.

    An undo is a *new write* of the old records and goes through the same door - which
    is also why it hands back no token of its own.

    Mutation caught: keeping the token after it is spent; restoring the whole file
    instead of the records that moved.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        before = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        written = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": FIRST, "profile": None}],
        )
        token = written["undo_token"]
        assert row_of(written["overview"], FIRST)["profile"] is None

        answer = await result(
            client, type=WS_TYPE_UNDO, entry_id=entry.entry_id, undo_token=token
        )
        assert tuple(answer) == UNDO_KEYS
        assert answer["undo_token"] is None
        assert answer["undone"] == "assign"
        assert row_of(answer["overview"], FIRST) == row_of(before, FIRST)
        assert_they_agree(hass, row_of(answer["overview"], FIRST), FIRST_ENTITY)

        error = await refused(
            client, type=WS_TYPE_UNDO, entry_id=entry.entry_id, undo_token=token
        )
        assert error["code"] == ws_const.ERR_NOT_FOUND
        assert error["translation_key"] == ERROR_UNDO_EXPIRED


async def test_a_token_is_withdrawn_by_the_next_write(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Two writes later, "as they were" is a state that was never on the screen."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        first = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": FIRST, "profile": None}],
        )
        await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=SECOND,
            height=160,
        )
        error = await refused(
            client, type=WS_TYPE_UNDO, entry_id=entry.entry_id, undo_token=first["undo_token"]
        )
        assert error["translation_key"] == ERROR_UNDO_EXPIRED


async def test_a_token_expires_on_the_clock_too(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """Five minutes is the changing-your-mind window, not the rest of the session."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        written = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": FIRST, "profile": None}],
        )
        freezer.tick(UNDO_TTL + timedelta(seconds=1))
        error = await refused(
            client, type=WS_TYPE_UNDO, entry_id=entry.entry_id, undo_token=written["undo_token"]
        )
        assert error["translation_key"] == ERROR_UNDO_EXPIRED


async def test_a_write_that_changes_nothing_offers_no_undo(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """An "Annulla" that does nothing is worse than no "Annulla"."""
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": FIRST, "profile": "tall"}],
        )
        assert answer["applied"] == 0
        assert answer["undo_token"] is None


# ----------------------------------------------------------------------- no reload
async def test_a_write_never_reloads_the_config_entry(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Plan decision 4, from the outside: the numbers arrive and the gateway stays up.

    Twelve assignments in a row used to be twelve reloads - every light, sensor and
    shutter of the house away and back each time. The shutters pick the new model up
    from a dispatcher signal instead.

    Mutation caught: falling back to `async_schedule_reload` after a write.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        with patch.object(
            hass.config_entries, "async_reload", autospec=True
        ) as reload, patch.object(
            hass.config_entries, "async_schedule_reload", autospec=True
        ) as scheduled:
            answer = await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry.entry_id,
                cover_unique_id=SECOND,
                height=170,
            )
        assert reload.call_count == 0
        assert scheduled.call_count == 0
        assert hass.states.get(SECOND_ENTITY).attributes["Height"] == 170.0
        assert_they_agree(hass, row_of(answer["overview"], SECOND), SECOND_ENTITY)


# --------------------------------------------------------------------- subscribe
async def test_subscribe_sends_the_overview_now_and_after_every_write(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """What stops two browser tabs each seeing half of the same twelve shutters.

    The whole payload every time and never a patch: a client that merged server pushes
    into a model it also edits eventually shows a shutter following a profile the server
    deleted (CONTRACT §1).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        await client.send_json_auto_id({"type": WS_TYPE_SUBSCRIBE, "entry_id": entry.entry_id})
        subscription = await client.receive_json()
        assert subscription["success"] is True
        sub_id = subscription["id"]

        first = await client.receive_json()
        assert first["id"] == sub_id
        assert first["event"]["type"] == WS_EVENT_OVERVIEW
        assert tuple(first["event"]["overview"]) == OVERVIEW_KEYS

        await client.send_json_auto_id(
            {
                "type": WS_TYPE_SET_TRAVEL,
                "entry_id": entry.entry_id,
                "cover_unique_id": SECOND,
                "height": 165,
            }
        )
        pushed = await client.receive_json()
        assert pushed["id"] == sub_id
        assert pushed["event"]["type"] == WS_EVENT_OVERVIEW
        assert row_of(pushed["event"]["overview"], SECOND)["height"] == 165.0
        # ...and the write's own answer comes after it, carrying the same payload.
        written = await client.receive_json()
        assert written["success"] is True
        assert written["result"]["overview"] == pushed["event"]["overview"]


async def test_subscribe_says_when_a_measurement_starts_and_when_it_ends(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The read-only lock hangs off this, which is why it names the window.

    Read off the covers' state changes rather than by polling the entity objects: the
    guided flow marks the entity and writes its state, so the flag reaches the panel the
    moment it reaches everybody else.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        await client.send_json_auto_id({"type": WS_TYPE_SUBSCRIBE, "entry_id": entry.entry_id})
        assert (await client.receive_json())["success"] is True
        assert (await client.receive_json())["event"]["type"] == WS_EVENT_OVERVIEW

        cover = entity_object(hass, "cover", "2-81")
        with cover.calibration_session():
            await hass.async_block_till_done()
            started = await client.receive_json()
            assert started["event"] == {
                "type": WS_EVENT_MEASURING,
                "cover_unique_id": FIRST,
                "name": "Hallway Shutter",
            }
        await hass.async_block_till_done()
        ended = await client.receive_json()
        assert ended["event"] == {
            "type": WS_EVENT_MEASURING,
            "cover_unique_id": None,
            "name": None,
        }


async def test_a_subscription_dies_with_the_socket(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """Nothing in 0.6.0 outlives a dropped connection, because nothing holds a shutter.

    Mutation caught: leaving the callback in the list after the unsubscribe (a write
    would push into a connection that is gone).
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
        assert len(async_subscribers(hass, entry.entry_id)) == 1

        await client.send_json_auto_id(
            {"type": "unsubscribe_events", "subscription": subscription["id"]}
        )
        assert (await client.receive_json())["success"] is True
        await hass.async_block_till_done()
        assert async_subscribers(hass, entry.entry_id) == []


async def test_a_second_write_is_refused_while_the_first_is_being_applied(
    hass: HomeAssistant, tmp_path
) -> None:
    """Two writes are not independent, so the second is refused and not queued.

    Each of them reads the store, decides against what it read and writes the whole of
    what it decided; the second would decide against a store the first is halfway
    through replacing. Driven here without a socket, because the interleaving is the
    point and a socket would only make it harder to arrange.

    Mutation caught: claiming the gateway after the store is loaded (two frames in one
    tick would both find it free).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        started = asyncio.Event()
        release = asyncio.Event()

        async def slow(_entry, _store) -> dict[str, Any]:
            started.set()
            await release.wait()
            return {}

        first = hass.async_create_task(async_write(hass, entry, "assign", slow))
        await started.wait()
        with pytest.raises(PanelError) as refusal:
            await async_write(hass, entry, "assign", slow)
        assert refusal.value.code == ws_const.ERR_NOT_ALLOWED
        assert refusal.value.translation_key == ERROR_WRITE_IN_PROGRESS

        release.set()
        await first
        # ...and the gateway is free again the moment the first one is done.
        await async_write(hass, entry, "assign", lambda _entry, _store: _nothing())


async def _nothing() -> dict[str, Any]:
    return {}


async def test_two_frames_in_one_tick_cannot_both_find_the_gateway_free(
    hass: HomeAssistant, tmp_path
) -> None:
    """The claim is taken with no `await` between it and the refusal that guards it.

    The socket delivers two frames in the same tick whenever the user double-taps, and
    the first thing a write does after the check is read the store - which really goes
    to the disk, and really suspends, the first time a gateway is written to after a
    restart. The suspension is the whole point, so it is arranged here rather than
    hoped for: a claim taken on the far side of it is a claim both writes get, and two
    writes each decide against a store the other is about to replace.

    Mutation caught: moving `writing.add(entry.entry_id)` below
    `await async_get_store(...)`.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        real = panel_write.async_get_store

        async def slow_store(hass_, entry_):
            # What the first write of a Home Assistant run really does here.
            await asyncio.sleep(0)
            return await real(hass_, entry_)

        outcomes: list[Any] = []

        async def write() -> None:
            try:
                outcomes.append(
                    await async_write(
                        hass,
                        entry,
                        "set_travel",
                        lambda entry_, store: async_set_travel(
                            hass, entry_, store, cover_unique_id=SECOND, height=165
                        ),
                    )
                )
            except PanelError as err:
                outcomes.append(err)

        with patch.object(panel_write, "async_get_store", slow_store):
            async_forget_store(hass, entry)
            # Created in the same tick, as two frames off one socket are.
            await asyncio.gather(
                hass.async_create_task(write()), hass.async_create_task(write())
            )
        refusals = [item for item in outcomes if isinstance(item, PanelError)]
        assert len(refusals) == 1, outcomes
        assert refusals[0].translation_key == ERROR_WRITE_IN_PROGRESS


async def test_a_measurement_that_opens_while_a_write_is_being_applied(
    hass: HomeAssistant, tmp_path
) -> None:
    """The one order the lock cannot rule out, and what it comes to.

    `_refuse_if_busy` runs before the write and the guided conversation is many screens
    long, so the only way round it is a session that opens inside the awaited store
    write itself. Defined outcome: the write finishes - its records are already on the
    way to the disk and abandoning half of it would be worse than either - and the
    signal it ends with reaches a cover that is now measuring, which the cover survives:
    the swap defers to the end of the run it is in (`_MovementModel`), and `Calibrating`
    is not one of the attributes a swap rewrites. The *next* write is refused as every
    write is, which is the state the panel is shown.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        cover = entity_object(hass, "cover", "2-81")
        with ExitStack() as sessions:

            async def work(entry_, store) -> dict[str, Any]:
                # The guided conversation takes the shutter exactly here, between the
                # refusal that guards this write and the signal that ends it.
                sessions.enter_context(cover.calibration_session())
                return await async_set_travel(
                    hass, entry_, store, cover_unique_id=SECOND, height=165
                )

            answer = await async_write(hass, entry, "set_travel", work)
            assert answer["undo_token"] is not None
            assert row_of(answer["overview"], SECOND)["height"] == 165.0
            # The session the swap landed in is untouched, and says so.
            assert cover.calibrating is True
            assert hass.states.get(FIRST_ENTITY).attributes["Calibrating"] is True
            assert row_of(answer["overview"], FIRST)["calibrating"] is True
            # ...and the next write is refused, which is what the panel is told.
            with pytest.raises(PanelError) as refusal:
                await async_write(hass, entry, "set_travel", lambda *_: _nothing())
            assert refusal.value.translation_key == ERROR_BUSY_CALIBRATING
        assert cover.calibrating is False


async def test_two_gateways_are_two_subscriptions(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A panel watching one gateway is not woken by a write to the other.

    The subscriber list is keyed by `entry_id` and so is the undo slot; this is the one
    test in the suite that sets two gateways up, which is what open point 7 of the lot's
    handoff asked for.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        second = make_entry(write_yaml(tmp_path, SECOND_GATEWAY_YAML, name="second.yaml"), mac=MAC2)
        with mock_gateway(), mock_commands():
            second.add_to_hass(hass)
            assert await hass.config_entries.async_setup(second.entry_id)
            await hass.async_block_till_done()

            client = await hass_ws_client(hass)
            await client.send_json_auto_id(
                {"type": WS_TYPE_SUBSCRIBE, "entry_id": entry.entry_id}
            )
            assert (await client.receive_json())["success"] is True
            assert (await client.receive_json())["event"]["type"] == WS_EVENT_OVERVIEW
            assert len(async_subscribers(hass, entry.entry_id)) == 1
            assert async_subscribers(hass, second.entry_id) == []

            # A write to the other gateway answers, and pushes nothing here.
            answer = await result(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=second.entry_id,
                cover_unique_id=f"{MAC2}-2-81",
                height=180,
            )
            assert answer["undo_token"] is not None
            # The next frame down the socket is the push from a write to *this* one.
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

        await hass.config_entries.async_unload(second.entry_id)
        await hass.async_block_till_done()


# ======================================================================= the preview
# `myhome/calibration/preview` (CONTRACT §11): the review panel's before/after table,
# answered by the same resolution the shutter runs on. It is a *read* - nothing is
# written, no lock is taken, a measurement does not stop it - and its whole reason for
# existing is that the panel must not scale a profile in JavaScript. So the test that
# matters is the parity one: preview an assignment, make it, and ask the overview; the
# two answers have to be the same numbers, the same tokens and the same source string.


async def item_of(answer: dict[str, Any], unique_id: str) -> dict[str, Any]:
    return next(item for item in answer["items"] if item["cover_unique_id"] == unique_id)


async def test_the_preview_is_exactly_what_the_assignment_would_produce(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The one invariant this command has: ask first, do it, and get the same answer.

    Not "close enough" and not "the same formula": the preview is the write's own input
    run through the read path, so every number, the origin token and the `Calibration
    source` string are compared whole. A frontend that scaled the profile itself is what
    this command exists to make unnecessary, and this is what would catch the drift.

    Mutation caught: previewing without `profile_wins` (the file's own run times would
    beat the profile, and the panel would promise numbers the shutter never used);
    ignoring the travel in the item (the profile would be previewed unscaled).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        items = [
            {"cover_unique_id": THIRD, "profile": "tall", "height": 180},
            {"cover_unique_id": FIRST, "profile": None},
        ]
        preview = await result(
            client, type=WS_TYPE_PREVIEW, entry_id=entry.entry_id, items=items
        )
        assert tuple(preview) == PREVIEW_KEYS
        assert preview["entry_id"] == entry.entry_id
        assert [item["cover_unique_id"] for item in preview["items"]] == [THIRD, FIRST]
        assert all(tuple(item) == PREVIEW_ITEM_KEYS for item in preview["items"])
        assert all(item["problem"] is None for item in preview["items"])

        answer = await result(
            client, type=WS_TYPE_ASSIGN, entry_id=entry.entry_id, assignments=items
        )
        for item in preview["items"]:
            row = row_of(answer["overview"], item["cover_unique_id"])
            assert item["values"] == row["values"]
            assert item["origin"] == row["origin"]
            assert item["source"] == row["source"]
            assert item["has_own"] == row["has_own"]
            assert item["height"] == row["height"]
            assert item["profile"] == row["profile"]


async def test_the_preview_writes_nothing_at_all(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """It is a question, and a question that changed the answer would be a write.

    Mutation caught: implementing it as an assign-and-roll-back (the store would be
    written twice and every subscriber told twice, for a table nobody confirmed).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        before = deepcopy(loaded_store(hass, entry).raw_covers)
        await result(
            client,
            type=WS_TYPE_PREVIEW,
            entry_id=entry.entry_id,
            items=[{"cover_unique_id": THIRD, "profile": "tall", "height": 180}],
        )
        assert loaded_store(hass, entry).raw_covers == before
        assert row_of(
            await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id), THIRD
        )["profile"] is None


async def test_the_preview_says_per_key_where_every_number_would_come_from(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A window with two numbers of its own keeps them, and the table has to say so.

    The `keys` list is the same vocabulary `cover_detail` uses - own / profile / file /
    default - so the review panel can mark the rows that will not move without asking a
    second command what "own" means.

    Mutation caught: dropping the overrides when the profile changes (the panel would
    promise the profile's ascent time to a window that measured its own).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        preview = await result(
            client,
            type=WS_TYPE_PREVIEW,
            entry_id=entry.entry_id,
            items=[{"cover_unique_id": FIRST, "profile": "from_the_file"}],
        )
        item = await item_of(preview, FIRST)
        origins = {row["key"]: row["origin"] for row in item["keys"]}
        assert origins[CONF_OPENING_TIME] == "own"
        assert origins[CONF_SLAT_TIME] == "own"
        assert origins[CONF_CLOSING_TIME] == "profile"
        assert item["has_own"] == sorted([CONF_OPENING_TIME, CONF_SLAT_TIME])
        # Its own measurements are untouched, and the profile answers for the rest.
        assert item["values"][CONF_OPENING_TIME] == 25.0
        assert item["origin"] == "adjusted"


async def test_a_window_with_no_travel_is_named_rather_than_refusing_the_batch(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The state the review panel's form exists to fix, reported one row at a time.

    `assign` refuses the whole batch for this, because a batch half written is a screen
    that has to explain which half. A preview writes nothing, so refusing eleven answers
    for the sake of the twelfth would only hide the table the user is reading while they
    type the missing number.

    Mutation caught: raising `_refuse_the_batch` from the preview (the review panel would
    go blank the moment one shutter had no travel, which is most of the time).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        preview = await result(
            client,
            type=WS_TYPE_PREVIEW,
            entry_id=entry.entry_id,
            items=[
                {"cover_unique_id": THIRD, "profile": "tall"},
                {"cover_unique_id": SECOND, "profile": "from_the_file"},
            ],
        )
        missing = await item_of(preview, THIRD)
        assert missing["problem"] == ERROR_MISSING_TRAVEL
        assert missing["values"] == {}
        assert missing["keys"] == []
        # ...and the row beside it is answered in full.
        answered = await item_of(preview, SECOND)
        assert answered["problem"] is None
        assert answered["values"][CONF_OPENING_TIME] > 0


@pytest.mark.parametrize(
    ("item", "problem"),
    [
        ({"cover_unique_id": f"{MAC}-2-99", "profile": None}, ERROR_UNKNOWN_COVER),
        ({"cover_unique_id": ADVANCED, "profile": None}, ERROR_ADVANCED_COVER),
        ({"cover_unique_id": FIRST, "profile": "gone"}, ERROR_UNKNOWN_PROFILE),
        ({"cover_unique_id": FIRST, "profile": "tall", "height": "abc"}, ERROR_NOT_A_NUMBER),
        ({"cover_unique_id": FIRST, "profile": "tall", "height": 5000}, ERROR_OUT_OF_RANGE),
    ],
    ids=["unknown_cover", "advanced_cover", "unknown_profile", "not_a_number", "out_of_range"],
)
async def test_every_problem_the_preview_names_is_one_assign_refuses_with(
    hass: HomeAssistant, tmp_path, hass_ws_client, item: dict[str, Any], problem: str
) -> None:
    """One vocabulary for the six problems, so one sentence explains each of them.

    The panel renders `exceptions.<key>.message` for a `problem` exactly as it renders it
    for a refusal, which is why the preview must not invent words of its own: a row that
    said "no such profile" in the table and something else in the refusal would be two
    facts about one mistake.

    Mutation caught: a private token set in the preview; a preview that answered numbers
    for a profile nobody defines (the row would read as though it were going to work).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        preview = await result(
            client, type=WS_TYPE_PREVIEW, entry_id=entry.entry_id, items=[item]
        )
        assert preview["items"][0]["problem"] == problem
        assert preview["items"][0]["values"] == {}
        assert problem in PREVIEW_PROBLEMS


async def test_the_preview_is_a_read_and_a_measurement_does_not_stop_it(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """The lock is on the writes. Reading what a change would come to is always allowed.

    Mutation caught: putting the preview behind `async_write` (the review panel would go
    dark for the whole of a guided calibration, which is precisely when a user is most
    likely to be looking at what they measured).
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        cover = entity_object(hass, "cover", "2-81")
        client = await hass_ws_client(hass)
        with cover.calibration_session():
            preview = await result(
                client,
                type=WS_TYPE_PREVIEW,
                entry_id=entry.entry_id,
                items=[{"cover_unique_id": SECOND, "profile": None}],
            )
            assert preview["items"][0]["problem"] is None
            # ...while a write to the same gateway is refused, which is the contrast.
            error = await refused(
                client,
                type=WS_TYPE_ASSIGN,
                entry_id=entry.entry_id,
                assignments=[{"cover_unique_id": SECOND, "profile": None}],
            )
            assert error["translation_key"] == ERROR_BUSY_CALIBRATING


async def test_the_preview_needs_a_gateway_and_a_household_member_may_not_ask(
    hass: HomeAssistant, tmp_path, hass_ws_client, hass_admin_user
) -> None:
    """Required `entry_id` like a write's, and admin-only like every other read.

    A preview is always about a batch composed on one gateway's screen, so there is no
    "the gateway I have" version of the question; and it answers what a shutter would
    run on, which is as much a setting as the write that would make it so.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(client, type=WS_TYPE_PREVIEW, items=[])
        assert error["code"] == ws_const.ERR_INVALID_FORMAT

        hass_admin_user.groups = []
        error = await refused(
            client, type=WS_TYPE_PREVIEW, entry_id=entry.entry_id, items=[]
        )
        assert error["code"] == ws_const.ERR_UNAUTHORIZED
