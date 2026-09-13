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

import json
from pathlib import Path
from typing import Any

import pytest
from homeassistant.components.websocket_api import const as ws_const
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from custom_components.myhome.calibration_store import (
    cover_calibration_data,
    cover_profile_data,
    loaded_store,
)
from custom_components.myhome.const import (
    CALIBRATION_KEY_ORIGINS,
    CONF_COVER_UNIQUE_ID,
    CONF_COVERS,
    CONF_OPENING_TIME,
    CONF_ORDER,
    CONF_PROFILES,
    CONF_SLAT_TIME,
    DOMAIN,
)
from custom_components.myhome.panel_schemas import (
    COVER_DETAIL_KEY_KEYS,
    COVER_DETAIL_KEYS,
    COVER_KEYS,
    ERROR_ADVANCED_COVER,
    ERROR_ENTRY_NOT_LOADED,
    ERROR_UNKNOWN_COVER,
    ERROR_UNKNOWN_ENTRY,
    OVERVIEW_KEYS,
    PROFILE_KEYS,
    TEXTS_KEYS,
    WS_READ_COMMANDS,
    WS_TYPE_COVER_DETAIL,
    WS_TYPE_OVERVIEW,
    WS_TYPE_TEXTS,
)
from custom_components.myhome.websocket_api import WS_REGISTERED

from .helpers_core import MAC
from .helpers_platforms import entity_object, setup_myhome

FIRST = f"{MAC}-2-81"
SECOND = f"{MAC}-2-82"
ADVANCED = f"{MAC}-2-83"
FIRST_ENTITY = "cover.hallway_shutter"

HEIGHT = 195.0

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
        # The two blocks the panel really reads: the flow's own wording, and the five
        # origin phrases it is forbidden from keeping its own copy of.
        assert "step" in texts["texts"]["options"]
        assert "calibration_origin" in texts["texts"]["selector"]
        # Nothing else of the file travels: the panel has no use for the config flow's
        # screens or for the entity names.
        assert set(texts["texts"]) <= {"options", "selector", "panel"}


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
