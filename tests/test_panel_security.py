"""The door, the shapes that come through it, and the two paths that lead off the host.

The panel is admin-only twice over - `require_admin=True` on the panel itself and
`@websocket_api.require_admin` on every command - and the reason is stated in CONTRACT
§1: a shutter's travel model is a *setting*, not a state, so somebody who may open a
cover has no business rewriting what "open" means. Two tests already hold that over a
hand-written list of payloads. This file holds it over the list the integration really
registers, so a fourteenth command cannot be added without one.

The rest is what an admin, or something running as one, can put into those commands: a
number that is not one, a key the model has never heard of, a name a hundred thousand
characters long, a language that is half of a path. None of it may reach past the schema
and the validators as an exception - a `TypeError` three layers down is a traceback in
the log and a spinner that never stops, where a refusal is a sentence the panel shows.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.http import HomeAssistantHTTP
from homeassistant.components.websocket_api import const as ws_const
from homeassistant.core import HomeAssistant

from custom_components.myhome import (
    PANEL_STATIC_URL,
    STATIC_URL_PATH,
    __file__ as INTEGRATION_FILE,
)
from custom_components.myhome.calibration_flow import _NAME_RE, NO_PROFILE
from custom_components.myhome.calibration_store import (
    PROFILE_NAME_MAX_LENGTH,
    PROFILE_NAME_PATTERN,
    loaded_store,
)
from custom_components.myhome.panel_schemas import (
    MEASURABLE_KEYS,
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

from .helpers_core import MAC, MAC2, make_entry, mock_gateway, write_yaml
from .helpers_platforms import setup_myhome
from .test_websocket_api import CALIBRATION, FIRST, SECOND, WRITE_YAML, refused, result

# Five numbers inside the profile's own bounds, so that a payload built for a *door*
# test is not refused by the validator before it reaches the door.
VALUES = {
    "opening_time": 20.0,
    "closing_time": 19.5,
    "slat_time": 3.5,
    "opening_roll": 1.9,
    "closing_roll": 1.5,
}

# One schema-valid payload per registered command, with `entry_id` filled in by the
# test. The set of keys is compared with what `async_register` really registered, so a
# command added to the integration and not to this map is a failing test rather than a
# command nobody checked the door of.
PAYLOADS: dict[str, dict[str, Any]] = {
    WS_TYPE_OVERVIEW: {},
    WS_TYPE_COVER_DETAIL: {"cover_unique_id": FIRST},
    WS_TYPE_TEXTS: {"language": "it"},
    WS_TYPE_PREVIEW: {"items": [{"cover_unique_id": FIRST, "profile": "tall"}]},
    WS_TYPE_ASSIGN: {"assignments": [{"cover_unique_id": FIRST, "profile": "tall"}]},
    WS_TYPE_REORDER: {"order": [FIRST, SECOND]},
    WS_TYPE_SET_TRAVEL: {"cover_unique_id": FIRST, "height": 180},
    WS_TYPE_COVER_EDIT: {"cover_unique_id": FIRST, "overrides": {"opening_time": 21.0}},
    WS_TYPE_COVER_FORGET: {"cover_unique_id": FIRST},
    WS_TYPE_PROFILE_EDIT: {"name": "tall", "values": VALUES, "reference_height": 195},
    WS_TYPE_PROFILE_RENAME: {"name": "tall", "new_name": "taller"},
    WS_TYPE_PROFILE_DELETE: {"name": "tall"},
    WS_TYPE_UNDO: {"undo_token": "deadbeef"},
    WS_TYPE_SUBSCRIBE: {},
}


def registered_commands(hass: HomeAssistant) -> set[str]:
    """Every command this integration really put on the socket."""
    return {name for name in hass.data["websocket_api"] if name.startswith("myhome/")}


# ------------------------------------------------------------------------ the door
async def test_the_map_below_names_every_command_the_integration_registers(
    hass: HomeAssistant, tmp_path
) -> None:
    """The guard that makes the next test complete rather than merely long.

    A parametrised refusal test is only worth what its list is: a command added to
    `async_register` and forgotten here would be a command with no door test, and
    nothing would say so. So the list is compared with the registry itself, and with the
    two tuples `panel_schemas` declares - which is also how a command that exists in the
    code and not in the contract is caught.

    Mutation caught: registering a command that is in neither tuple; adding a command to
    the integration without a payload here.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML) as (_entry, _commands):
        declared = {*WS_READ_COMMANDS, *WS_WRITE_COMMANDS, WS_TYPE_SUBSCRIBE}
        assert registered_commands(hass) == declared
        assert set(PAYLOADS) == declared


@pytest.mark.parametrize("command", sorted(PAYLOADS), ids=lambda name: name.split("/")[-1])
async def test_a_household_member_is_refused_at_every_single_command(
    hass: HomeAssistant, tmp_path, hass_ws_client, hass_admin_user, command: str
) -> None:
    """Fourteen commands, fourteen closed doors, and the payload is a valid one.

    Valid on purpose: Home Assistant validates the schema *before* the handler runs, so
    a test that sent nonsense would be answered `invalid_format` and would pass whether
    the admin check was there or not. Every payload here would be honoured for an
    administrator, which is what makes the refusal the thing under test.

    Mutation caught: dropping `require_admin` from any single command - including the
    reads, which are behind the same door because the panel is (an exception for them
    would only be a second way into the same room).
    """
    hass_admin_user.groups = []
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        # `texts` is the one command that is not about a gateway - it carries no
        # `entry_id` and its schema refuses one - and a frame refused by the schema
        # would answer `invalid_format` whether the door were locked or not.
        about_a_gateway = {} if command == WS_TYPE_TEXTS else {"entry_id": entry.entry_id}
        error = await refused(client, type=command, **about_a_gateway, **PAYLOADS[command])
        assert error["code"] == ws_const.ERR_UNAUTHORIZED, command
        # ...and nothing was written on the way to being refused.
        assert loaded_store(hass, entry).raw_covers == CALIBRATION["covers"]
        assert sorted(loaded_store(hass, entry).raw_profiles) == ["tall"]


# -------------------------------------------------------------------- bad payloads
# Every one of these is a frame a browser can send. The rule is the same for all of
# them: an answer, with a code the panel can render, and never a traceback.
BAD_PAYLOADS: list[tuple[str, dict[str, Any], str]] = [
    (
        "a travel that is a list",
        {"type": WS_TYPE_SET_TRAVEL, "cover_unique_id": FIRST, "height": [180]},
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "a travel that is a word",
        {"type": WS_TYPE_SET_TRAVEL, "cover_unique_id": FIRST, "height": "quite tall"},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        # A real socket cannot carry a JSON `NaN` at all - the server's parser refuses
        # the frame - but the *string* form goes straight through `parse_number`, which
        # is `float()`, and `float("nan")` is a number Python is happy with.
        "a travel written as nan",
        {"type": WS_TYPE_SET_TRAVEL, "cover_unique_id": FIRST, "height": "nan"},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a travel written as infinity",
        {"type": WS_TYPE_SET_TRAVEL, "cover_unique_id": FIRST, "height": "1e400"},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a negative travel",
        {"type": WS_TYPE_SET_TRAVEL, "cover_unique_id": FIRST, "height": -195},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a key the travel model has never heard of",
        {
            "type": WS_TYPE_COVER_EDIT,
            "cover_unique_id": FIRST,
            "overrides": {"tilt_angle": 30},
        },
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "a key beside the ones that belong",
        {
            "type": WS_TYPE_COVER_EDIT,
            "cover_unique_id": FIRST,
            "overrides": {"opening_time": 21.0},
            "and_also": True,
        },
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "an assignment that is not an object",
        {"type": WS_TYPE_ASSIGN, "assignments": ["tall"]},
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "an assignment with no profile key at all",
        {"type": WS_TYPE_ASSIGN, "assignments": [{"cover_unique_id": FIRST}]},
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "an order that is not a list",
        {"type": WS_TYPE_REORDER, "order": FIRST},
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "an order naming a shutter twice",
        {"type": WS_TYPE_REORDER, "order": [FIRST, FIRST]},
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "a profile with four of its five numbers",
        {
            "type": WS_TYPE_PROFILE_EDIT,
            "name": "tall",
            "values": {key: 10.0 for key in MEASURABLE_KEYS[:4]},
            "reference_height": 195,
        },
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "a profile number outside its bounds",
        {
            "type": WS_TYPE_PROFILE_EDIT,
            "name": "tall",
            "values": {**VALUES, "opening_roll": 40},
            "reference_height": 195,
        },
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a cover unique id that is a number",
        {"type": WS_TYPE_COVER_DETAIL, "cover_unique_id": 281},
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "a cover unique id shaped like a path",
        {"type": WS_TYPE_COVER_DETAIL, "cover_unique_id": "../../etc/passwd"},
        ws_const.ERR_NOT_FOUND,
    ),
    (
        "a profile name shaped like a path",
        {"type": WS_TYPE_PROFILE_DELETE, "name": "../../etc/passwd"},
        ws_const.ERR_NOT_FOUND,
    ),
    (
        "a new profile name shaped like a path",
        {"type": WS_TYPE_PROFILE_RENAME, "name": "tall", "new_name": "../../etc/passwd"},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a new profile name with a slash in it",
        {"type": WS_TYPE_PROFILE_RENAME, "name": "tall", "new_name": "tall/short"},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a new profile name that is unicode",
        {"type": WS_TYPE_PROFILE_RENAME, "name": "tall", "new_name": "tapparellé"},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a new profile name that is whitespace",
        {"type": WS_TYPE_PROFILE_RENAME, "name": "tall", "new_name": "   "},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a new profile name that is nothing",
        {"type": WS_TYPE_PROFILE_RENAME, "name": "tall", "new_name": ""},
        ws_const.ERR_SERVICE_VALIDATION_ERROR,
    ),
    (
        "a hundred thousand characters of profile name",
        {"type": WS_TYPE_PROFILE_RENAME, "name": "x" * 100_000, "new_name": "taller"},
        ws_const.ERR_NOT_FOUND,
    ),
    (
        "an undo token that is an object",
        {"type": WS_TYPE_UNDO, "undo_token": {"token": "deadbeef"}},
        ws_const.ERR_INVALID_FORMAT,
    ),
    (
        "an entry id that is null",
        {"type": WS_TYPE_SET_TRAVEL, "entry_id": None, "cover_unique_id": FIRST, "height": 180},
        ws_const.ERR_INVALID_FORMAT,
    ),
]


@pytest.mark.parametrize(
    ("case", "payload", "code"),
    BAD_PAYLOADS,
    ids=[case for case, _payload, _code in BAD_PAYLOADS],
)
async def test_a_frame_nobody_meant_to_send_is_answered_and_never_raised(
    hass: HomeAssistant,
    tmp_path,
    hass_ws_client,
    case: str,
    payload: dict[str, Any],
    code: str,
) -> None:
    """Twenty-four frames a browser can send, and twenty-four sentences back.

    The distinction the codes draw is the one the panel renders: `invalid_format` is a
    message that should never have been sent and there is nothing for the user to do
    about it, while `service_validation_error` is a number or a name *they* typed and
    the field is waiting for a correction. Getting them the wrong way round puts a
    developer's message under a user's field.

    What is being ruled out is the third outcome: an exception. A `TypeError` inside a
    handler is a traceback in the log and a request that never answers, which the panel
    shows as a spinner that does not stop.

    Mutation caught: `vol.Coerce(float)` in place of `parse_number` (a comma would stop
    being a decimal point and `nan` would stop being refused); dropping `vol.Unique()`
    from the order; validating a name after writing it.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        before = dict(loaded_store(hass, entry).raw_covers)
        profiles_before = dict(loaded_store(hass, entry).raw_profiles)
        client = await hass_ws_client(hass)
        error = await refused(client, **{"entry_id": entry.entry_id, **payload})
        assert error["code"] == code, case
        # Nothing at all was written on the way to the refusal.
        assert loaded_store(hass, entry).raw_covers == before, case
        assert loaded_store(hass, entry).raw_profiles == profiles_before, case
        # ...and the socket is still usable, which is what tells a refusal from a crash.
        assert (await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id))[
            "entry_id"
        ] == entry.entry_id


# ------------------------------------------------------------------- profile names
# A profile name is a YAML key, because the user may move a guided profile into their
# own `cover_profiles:` by hand and nothing else has to change. That is the whole rule,
# and it is one regular expression shared by the panel and the guided dialog - the
# alphabet and the length together, so that neither side can hold half of it.
NAMES: list[tuple[str, bool]] = [
    ("tall", True),
    ("__proto__", True),
    ("constructor", True),
    ("toString", True),
    # The cap, from both sides of it. Before 0.6.0 there was none, and `x` * 200 - or
    # `x` * 100 000 - was a name: accepted by the dialog and by the panel, written into
    # `.storage` as a dict key, and printed as a heading on a card and as a segment of
    # the panel's own hash route. The only bound was the WebSocket frame's, which is
    # not a bound anybody chose.
    ("a" * PROFILE_NAME_MAX_LENGTH, True),
    ("a" * (PROFILE_NAME_MAX_LENGTH + 1), False),
    ("a" * 200, False),
    ("_", True),
    ("0", True),
    ("", False),
    ("   ", False),
    ("tall shutters", False),
    ("tall-shutters", False),
    ("tall/short", False),
    ("..", False),
    (".", False),
    ("tapparellé", False),
    ("tall\n", False),
    ("\x00tall", False),
    (NO_PROFILE, False),
]


@pytest.mark.parametrize(("name", "usable"), NAMES, ids=[repr(name)[:24] for name, _ok in NAMES])
def test_the_panel_and_the_dialog_mean_the_same_thing_by_a_usable_name(
    name: str, usable: bool
) -> None:
    """One rule, two screens, and the two `__proto__` cases stated rather than assumed.

    `__proto__`, `constructor` and `toString` are **usable names**, and deliberately so:
    they are letters and underscores, they are valid YAML keys, and a Python mapping has
    no prototype for them to pollute. They are listed here so that the day somebody
    reaches for a denylist, they find a test saying what the rule really is - which is
    also the test that would catch a panel-side special case the dialog does not share.

    Everything with a separator, a dot, a space or a character outside ASCII is refused,
    which is what keeps a name that reaches a file path or a YAML document from being
    anything but a key. So is `NO_PROFILE`, the sentinel the assignment select uses for
    "Nessun profilo": a profile really called that would be unassignable for ever.

    Mutation caught: the panel restating the rule instead of importing it; a pattern
    that stops anchoring at the end of the string.
    """
    panel = bool(re.fullmatch(PROFILE_NAME_PATTERN, name)) and name != NO_PROFILE
    assert panel is usable, name

    # One rule and not two copies of one: the dialog compiles the store's own pattern.
    assert _NAME_RE.pattern == PROFILE_NAME_PATTERN

    # ...and it reaches the same verdict on the name as its own form hands it over. The
    # dialog strips first (`async_step_profile_name`), because a text field collects
    # whatever was typed into it; the panel does not, because a WebSocket frame is not a
    # form and " tall " is a name somebody's client built rather than one somebody
    # typed. So the two are compared on the stripped name, which is the only one the
    # dialog can produce - and the trailing-newline row is exactly why that matters:
    # `_NAME_RE.match` accepts a name with one, and the strip is what means it never
    # arrives with one.
    stripped = name.strip()
    dialog = bool(_NAME_RE.match(stripped)) and stripped != NO_PROFILE
    also_the_panel = (
        bool(re.fullmatch(PROFILE_NAME_PATTERN, stripped)) and stripped != NO_PROFILE
    )
    assert dialog is also_the_panel, name


async def test_a_profile_called_proto_is_stored_read_back_and_deleted_like_any_other(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """...and the name really does survive a round trip through every screen.

    The pattern says `__proto__` is a name; this says the rest of the stack agrees, so
    that "it is allowed" is not a claim about a regular expression alone. It is renamed
    to, read back out of the overview, followed by a shutter and deleted - the whole
    life of a profile, under the one name a JavaScript object would have refused to
    hold.

    Mutation caught: a backend that keys profiles by anything but a plain mapping.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        await result(
            client,
            type=WS_TYPE_PROFILE_RENAME,
            entry_id=entry.entry_id,
            name="tall",
            new_name="__proto__",
        )
        overview = await result(client, type=WS_TYPE_OVERVIEW, entry_id=entry.entry_id)
        profile = next(row for row in overview["profiles"] if row["name"] == "__proto__")
        assert profile["editable"] is True
        assert sorted(profile["followers"]) == sorted([FIRST, SECOND])
        assert {
            row["profile"] for row in overview["covers"] if row["unique_id"] in (FIRST, SECOND)
        } == {"__proto__"}
        assert loaded_store(hass, entry).profile("__proto__")["opening_time"] == 22.3

        answer = await result(
            client, type=WS_TYPE_PROFILE_DELETE, entry_id=entry.entry_id, name="__proto__"
        )
        assert sorted(answer["covers_affected"]) == sorted([FIRST, SECOND])
        assert loaded_store(hass, entry).profile("__proto__") is None


# -------------------------------------------------------------------- static paths
async def test_the_two_static_paths_are_absolute_and_neither_contains_the_other(
    hass: HomeAssistant, tmp_path
) -> None:
    """Home Assistant serves these; what this integration owns is what it hands over.

    Traversal out of a static resource is aiohttp's problem and it solves it, so the
    thing to hold here is the input: two **absolute** directories that really are inside
    the integration, under two URL prefixes neither of which is a prefix of the other.
    The second half is not security but routing - two aiohttp static resources where one
    prefix contains the other resolve by registration order, so a bundle under
    `/myhome_static/panel/` would be looked for under `images/` and 404 - and it is here
    because it is the same call and the same list.

    Mutation caught: a relative directory (which would resolve against whatever the
    process's working directory happened to be, and could serve anything); a panel URL
    nested under the drawings'.
    """
    register = AsyncMock()
    entry = make_entry(write_yaml(tmp_path, WRITE_YAML))
    with (
        mock_gateway(),
        patch.object(HomeAssistantHTTP, "async_register_static_paths", register),
    ):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    (configs,) = register.await_args.args
    inside = Path(INTEGRATION_FILE).parent.resolve()
    for config in configs:
        served = Path(config.path)
        assert served.is_absolute(), config.url_path
        assert served.resolve() == served, config.url_path
        assert inside in served.resolve().parents or served.resolve() == inside
    prefixes = [config.url_path for config in configs]
    assert prefixes == [STATIC_URL_PATH, PANEL_STATIC_URL]
    for one in prefixes:
        for other in prefixes:
            if one is not other:
                assert not other.startswith(f"{one}/"), (one, other)

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_a_gateway_that_is_not_this_one_is_not_readable_through_the_panel(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """An `entry_id` is not a capability: it names a gateway, and only a MyHOME one.

    A config entry id is not a secret - it is in every URL of the integrations page - so
    the check that matters is the one on the *domain*: a command carrying the entry id
    of some other integration must be `not_found` and not a traceback out of
    `hass.data[DOMAIN]`.

    Mutation caught: looking the entry up with `async_get_entry` and not checking what
    it belongs to.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        other = make_entry(write_yaml(tmp_path, WRITE_YAML, name="other.yaml"), mac=MAC2)
        other.add_to_hass(hass)  # added, never set up
        client = await hass_ws_client(hass)
        for entry_id in (other.entry_id, "not-an-entry-id", "", MAC):
            error = await refused(
                client,
                type=WS_TYPE_SET_TRAVEL,
                entry_id=entry_id,
                cover_unique_id=FIRST,
                height=180,
            )
            assert error["code"] == ws_const.ERR_NOT_FOUND, entry_id
        # ...and the gateway that is this one still answers.
        await result(
            client,
            type=WS_TYPE_SET_TRAVEL,
            entry_id=entry.entry_id,
            cover_unique_id=FIRST,
            height=180,
        )
