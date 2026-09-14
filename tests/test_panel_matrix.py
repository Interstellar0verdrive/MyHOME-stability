"""Every state a shutter can be in, put through every write the panel can make.

`tests/test_panel_parity.py` holds the one invariant the panel rests on - the row it
draws and the attributes the entity publishes are one answer - over the seven states a
*store* can be in. This file holds the same invariant over the seven states **crossed
with every write**, which is the half a read-only matrix cannot reach: a write is the
only thing that can leave the three answers disagreeing, because it is the only thing
that changes the store under a shutter that is not being rebuilt.

Three answers, not two, and the same three after every single write:

* the **overview row** and the entity's own `Calibration source` attribute and travel
  numbers (`assert_they_agree`, imported rather than restated);
* the **cover detail**, key by key, against that row - the screen the user opens to ask
  "where does this number come from" must not answer differently from the list they
  opened it from;
* the **preview** of the assignment the shutter already has, against the row it already
  has. That is the identity case of `myhome/calibration/preview`, valid in every state,
  and it is what makes "the preview is the write's own input run through the read path"
  a statement about all of them rather than about the one batch a test happened to send.

The writes are the nine commands plus the undo, and `cover_edit` is run once per key a
window can have measured on it, because the five are not interchangeable: two of them
are scaled by the travel and three are not, and a screen that got one of them wrong
would be wrong about the field the user was typing in.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.myhome.calibration_store import (
    cover_calibration_data,
    cover_profile_data,
)
from custom_components.myhome.const import (
    CALIBRATION_KEY_ORIGINS,
    CALIBRATION_ORIGINS,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_UNIQUE_ID,
    CONF_COVERS,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_ORDER,
    CONF_PROFILES,
    CONF_SLAT_TIME,
)
from custom_components.myhome.panel_data import async_cover_detail, async_overview, async_preview
from custom_components.myhome.panel_schemas import (
    MEASURABLE_KEYS,
    WS_TYPE_ASSIGN,
    WS_TYPE_COVER_EDIT,
    WS_TYPE_COVER_FORGET,
    WS_TYPE_PROFILE_DELETE,
    WS_TYPE_PROFILE_EDIT,
    WS_TYPE_PROFILE_RENAME,
    WS_TYPE_REORDER,
    WS_TYPE_SET_TRAVEL,
    WS_TYPE_UNDO,
)

from .helpers_core import MAC
from .helpers_platforms import setup_myhome
from .test_panel_parity import assert_they_agree

ENTITY = "cover.hallway_shutter"
UNIQUE_ID = f"{MAC}-2-81"
OTHER = f"{MAC}-2-82"

HEIGHT = 195.0

PROFILE = cover_profile_data(
    "tall",
    reference_height=HEIGHT,
    opening_time=22.3,
    closing_time=21.7,
    slat_time=4.7,
    opening_roll=2.12,
    closing_roll=1.69,
    reference_cover="Hallway Shutter",
    measured_on=UNIQUE_ID,
    measured_at="2026-09-04T18:12:00+00:00",
)

# Three files, because three of the states below are statements `myhome.yaml` makes and
# no store can reach: a window with nothing but a travel, a window whose run times are
# written against it, and a window the file itself puts in a profile.
BARE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      height: {HEIGHT}
    landing_shutter:
      where: '82'
      name: Landing Shutter
      height: 150
"""

FILE_YAML = BARE_YAML.replace(
    f"""      name: Hallway Shutter
      height: {HEIGHT}""",
    f"""      name: Hallway Shutter
      opening_time: 30
      closing_time: 29
      slat_time: 6
      roll: 1.2
      height: {HEIGHT}""",
)

# The file's own `profile:` line, which is the one assignment this integration may not
# take away: `cover_profiles:` defines the name and the cover block points at it.
FILE_PROFILE_YAML = f"""
gateway:
  mac: {MAC}
  cover_profiles:
    from_the_file:
      reference_height: 200
      opening_time: 24
      closing_time: 23
      slat_time: 5
      roll: 1.5
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      profile: from_the_file
      height: {HEIGHT}
    landing_shutter:
      where: '82'
      name: Landing Shutter
      height: 150
"""


def record(**kwargs: Any) -> dict[str, Any]:
    data = cover_calibration_data(UNIQUE_ID, **kwargs)
    return {key: value for key, value in data.items() if key != CONF_COVER_UNIQUE_ID}


def stored(covers: dict | None = None) -> dict[str, Any]:
    """A store file with the profile always defined, and this window in some state.

    `tall` is defined in every one of them, followed or not, so that the three profile
    commands have something to work on in every row of the matrix: the states differ in
    what the *window* says, which is the axis this file crosses with the writes.
    """
    return {
        CONF_PROFILES: {"tall": PROFILE},
        CONF_COVERS: covers or {},
        CONF_ORDER: [OTHER, UNIQUE_ID],
    }


# The seven states, named as the guided flow's own screens name them. Each is a file
# and a store, and the origin the resolution gives it before anything is written.
STATES: list[tuple[str, str, dict[str, Any]]] = [
    ("nothing anybody ever said", BARE_YAML, stored()),
    ("the file's own run times", FILE_YAML, stored()),
    ("a profile the file assigns", FILE_PROFILE_YAML, stored()),
    (
        "a profile the panel assigned",
        BARE_YAML,
        stored({UNIQUE_ID: record(profile="tall", profile_wins=True, height=HEIGHT)}),
    ),
    (
        "its own run times over that profile",
        BARE_YAML,
        stored(
            {
                UNIQUE_ID: record(
                    profile="tall",
                    profile_wins=True,
                    height=HEIGHT,
                    overrides={CONF_OPENING_TIME: 25.0, CONF_CLOSING_TIME: 24.0},
                )
            }
        ),
    ),
    (
        "its own two rolls over that profile",
        BARE_YAML,
        stored(
            {
                UNIQUE_ID: record(
                    profile="tall",
                    profile_wins=True,
                    height=HEIGHT,
                    overrides={CONF_OPENING_ROLL: 2.5, CONF_CLOSING_ROLL: 2.6},
                )
            }
        ),
    ),
    (
        "measured, and following nothing",
        FILE_YAML,
        stored(
            {
                UNIQUE_ID: record(
                    height=HEIGHT,
                    overrides={
                        CONF_OPENING_TIME: 22.3,
                        CONF_CLOSING_TIME: 21.7,
                        CONF_SLAT_TIME: 4.7,
                        CONF_OPENING_ROLL: 2.12,
                        CONF_CLOSING_ROLL: 1.69,
                    },
                )
            }
        ),
    ),
]

# The ten writes, as the frame the browser sends. `entry_id` is filled in by the runner,
# because a fixture cannot know it.
WRITES: list[tuple[str, dict[str, Any]]] = [
    (
        "assign to a profile",
        {
            "type": WS_TYPE_ASSIGN,
            "assignments": [{"cover_unique_id": UNIQUE_ID, "profile": "tall", "height": 180}],
        },
    ),
    (
        "take it out of its profile",
        {
            "type": WS_TYPE_ASSIGN,
            "assignments": [{"cover_unique_id": UNIQUE_ID, "profile": None}],
        },
    ),
    (
        "set the travel",
        {"type": WS_TYPE_SET_TRAVEL, "cover_unique_id": UNIQUE_ID, "height": 165},
    ),
    (
        "take the travel away",
        {"type": WS_TYPE_SET_TRAVEL, "cover_unique_id": UNIQUE_ID, "height": None},
    ),
    (
        "forget the measurement",
        {"type": WS_TYPE_COVER_FORGET, "cover_unique_id": UNIQUE_ID},
    ),
    (
        "correct the profile",
        {
            "type": WS_TYPE_PROFILE_EDIT,
            "name": "tall",
            "values": {
                CONF_OPENING_TIME: 20.0,
                CONF_CLOSING_TIME: 19.5,
                CONF_SLAT_TIME: 3.5,
                CONF_OPENING_ROLL: 1.9,
                CONF_CLOSING_ROLL: 1.5,
            },
            "reference_height": 180,
        },
    ),
    ("rename the profile", {"type": WS_TYPE_PROFILE_RENAME, "name": "tall", "new_name": "taller"}),
    ("delete the profile", {"type": WS_TYPE_PROFILE_DELETE, "name": "tall"}),
    ("reorder the gateway", {"type": WS_TYPE_REORDER, "order": [UNIQUE_ID, OTHER]}),
]

# ...and `cover_edit`, once per key, because the five are not interchangeable: two of
# them are what a travel scales and three of them are not.
WRITES += [
    (
        f"correct {key} by hand",
        {
            "type": WS_TYPE_COVER_EDIT,
            "cover_unique_id": UNIQUE_ID,
            "overrides": {key: 2.0 if key.endswith("roll") else 18.0},
        },
    )
    for key in MEASURABLE_KEYS
]


def current_assignment(row: dict[str, Any]) -> dict[str, Any]:
    """The preview item that asks for the assignment this window already has.

    `profile: null` for a window the *file* assigns - popping an assignment it does not
    have leaves the record as it is and the file goes on answering - and the name for one
    the store assigned. Both rewrite the record into exactly what it already was, which
    is the rule CONTRACT §11 gives the panel for an impact preview, and what makes the
    answer comparable with the row.
    """
    return {
        "cover_unique_id": row["unique_id"],
        "profile": None if row["profile_from_file"] else row["profile"],
    }


def assert_the_three_answers_are_one(
    hass: HomeAssistant, entry, *, case: str
) -> dict[str, Any]:
    """Overview row, cover detail and preview, against the shutter and each other.

    Exported as a block rather than three assertions because they are one claim: there
    is a single resolution, `resolve_cover_config`, and every screen of the panel is a
    projection of it. Anything that re-derives an origin, rescales a profile or caches a
    number parts company here and nowhere else.
    """
    overview = async_overview(hass, entry)
    row = next(item for item in overview["covers"] if item["unique_id"] == UNIQUE_ID)

    # 1. The row and the shutter itself.
    assert row["origin"] in CALIBRATION_ORIGINS, case
    assert_they_agree(hass, row, ENTITY, case=case)

    # 2. The detail screen and the row it was opened from.
    detail = async_cover_detail(hass, entry, UNIQUE_ID)
    assert detail is not None, case
    # Every field but the position, which is a fact about the list and not about the
    # shutter: `cover_detail` answers about one window and has no list to be nth of.
    assert {
        key: value for key, value in detail["cover"].items() if key != "order_index"
    } == {key: value for key, value in row.items() if key != "order_index"}, case
    keys = {item["key"]: item for item in detail["keys"]}
    assert set(keys) == set(row["values"]), case
    for key, item in keys.items():
        assert item["value"] == row["values"][key], (case, key)
        assert item["origin"] in CALIBRATION_KEY_ORIGINS, (case, key)
        assert item["own"] is (key in row["has_own"]), (case, key)

    # 3. The preview of the assignment it already has, against the row it already has.
    preview = async_preview(hass, entry, items=[current_assignment(row)])
    answer = preview["items"][0]
    assert answer["problem"] is None, case
    for field in ("values", "origin", "source", "has_own", "height", "profile"):
        assert answer[field] == row[field], (case, field)
    return row


@pytest.mark.parametrize(
    ("state", "yaml_text", "calibration"),
    STATES,
    ids=[state for state, _yaml, _cal in STATES],
)
@pytest.mark.parametrize(
    ("write", "payload"),
    WRITES,
    ids=[write for write, _payload in WRITES],
)
async def test_the_three_answers_are_one_before_and_after_every_write(
    hass: HomeAssistant,
    tmp_path,
    hass_ws_client,
    state: str,
    yaml_text: str,
    calibration: dict[str, Any],
    write: str,
    payload: dict[str, Any],
) -> None:
    """The matrix: seven states, fourteen writes, the same three answers each time.

    Every write is sent as the frame the browser sends, so the schema, the admin check
    and the refusals under test are the registered ones. A write that this state makes a
    no-op still has to answer - `applied: 0`, `undo_token: null` - and the three answers
    still have to agree afterwards, which is the case a happy-path test never reaches.

    Then the undo, which is a write like any other and is held to the same three
    answers: it is the one write that puts records back rather than deciding them, and
    the state it leaves has to be a state the read path can describe.

    Mutation caught: any second implementation of the precedence (the detail's per-key
    `origin` re-derived from `overrides`, the preview scaling a profile of its own, the
    entity keeping a number the store no longer says).
    """
    case = f"{state} / {write}"
    async with setup_myhome(hass, tmp_path, yaml_text, calibration=calibration) as (
        entry,
        _commands,
    ):
        before = assert_the_three_answers_are_one(hass, entry, case=f"{case} (before)")

        client = await hass_ws_client(hass)
        await client.send_json_auto_id({**payload, "entry_id": entry.entry_id})
        message = await client.receive_json()
        assert message["success"], (case, message)
        answer = message["result"]
        await hass.async_block_till_done()

        # The write answers with the gateway, and the gateway it answers with is the one
        # the next read gives - the client replaces its model with this and nothing else.
        after = assert_the_three_answers_are_one(hass, entry, case=f"{case} (after)")
        assert (
            next(
                item
                for item in answer["overview"]["covers"]
                if item["unique_id"] == UNIQUE_ID
            )
            == after
        ), case

        token = answer["undo_token"]
        if token is None:
            # Nothing changed, so there is nothing to take back and no button for it.
            assert after == before, case
            return

        await client.send_json_auto_id(
            {"type": WS_TYPE_UNDO, "entry_id": entry.entry_id, "undo_token": token}
        )
        undone = await client.receive_json()
        assert undone["success"], (case, undone)
        await hass.async_block_till_done()
        assert assert_the_three_answers_are_one(hass, entry, case=f"{case} (undone)") == before, (
            case
        )
