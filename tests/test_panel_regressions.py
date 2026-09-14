"""The defects the 0.6.0 reviews found, each with a test that fails if it comes back.

Seven lots were reviewed adversarially and nine real defects were fixed. Every one of
them was fixed *with* a test - the reviews say so, and they are right. This file is not
a second copy of those tests. It is the register: one short assertion per defect, taken
from a different angle from the original, plus a list of the tests that hold the ones a
second angle would only restate.

Why a register at all. A defect found by a review is a place the code was wrong once and
can be wrong again, and the test that caught it is usually inside a file about something
else, under a name that reads like the feature rather than like the bug. Six months from
now the fastest way to find out whether "the impact preview's roll" is still right is a
file that says so. Every docstring below names the review and the commit.

Where a second angle would be a copy - the frozen model's missing field is one - the
test here asserts the *shape* rather than the behaviour, so that the two together are
harder to break than either: one would survive a rewrite of the mechanism, the other
would not.
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.websocket_api import const as ws_const
from homeassistant.core import HomeAssistant

from custom_components.myhome import panel_data
from custom_components.myhome.calibration_store import (
    keys_written_by_the_file,
    loaded_store,
)
from custom_components.myhome.const import (
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_HEIGHT,
    CONF_KEYS_FROM_FILE,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_OVERRIDES,
    CONF_RAW,
    CONF_ROLL,
    CONF_SLAT_TIME,
    DOMAIN,
)
from custom_components.myhome.cover import _MovementModel
from custom_components.myhome.panel_schemas import (
    ERROR_MISSING_TRAVEL,
    ERROR_UNKNOWN_ENTRY,
    ERROR_UNKNOWN_PROFILE,
    WS_TYPE_ASSIGN,
    WS_TYPE_COVER_DETAIL,
    WS_TYPE_COVER_FORGET,
    WS_TYPE_OVERVIEW,
    WS_TYPE_PREVIEW,
    WS_TYPE_PROFILE_EDIT,
    WS_TYPE_PROFILE_RENAME,
    WS_TYPE_REORDER,
)

from .helpers_core import MAC
from .helpers_platforms import setup_myhome
from .test_calibration_flow import (
    OWN_NUMBERS_YAML,
    UNIQUE_ID,
    calibrating,
    choose,
    measured_profile,
    open_dialog,
    submit,
    the_store,
)
from .test_websocket_api import (
    CALIBRATION,
    FIRST,
    SECOND,
    WRITE_YAML,
    refused,
    result,
    row_of,
)

HERE = Path(__file__).resolve().parent


# --------------------------------------------------------- lot 3 review §1.1 (03a1e36)
def test_the_frozen_model_carries_every_number_a_run_is_timed_by() -> None:
    """`two_phase` is a *field* of `_MovementModel`, and that is the defect's shape.

    A calibration that took the slat phase away while the motor was turning the slats
    made `_normalise` - the last line of both travel functions - drop the whole slat leg
    of a run that still had three seconds of it to go: the shutter read "slats closed"
    with the slats half open, and the next command paid the slat phase a second time.
    The seven numbers were frozen; the flag derived from one of them was not.

    The behaviour is held by
    `test_panel_refresh.py::test_a_slat_phase_taken_away_leaves_the_run_in_flight_its_slat_leg`.
    What is held here is the shape, and it is deliberately a different kind of
    assertion: a rewrite of the mechanism that kept the behaviour would still have to
    keep a flag on the snapshot, and a snapshot that quietly lost a field again would
    fail this line before anybody had to reason about slats.

    Mutation caught: removing `two_phase` from the frozen model.
    """
    frozen = {field.name for field in fields(_MovementModel)}
    assert "two_phase" in frozen
    # ...and the reader really reads it off the snapshot rather than off the entity.
    source = ast.parse((HERE.parent / "custom_components" / "myhome" / "cover.py").read_text())
    normalise = next(
        node
        for node in ast.walk(source)
        if isinstance(node, ast.FunctionDef) and node.name == "_normalise"
    )
    read = {
        ast.unparse(node)
        for node in ast.walk(normalise)
        if isinstance(node, ast.Attribute)
    }
    assert "self._run.two_phase" in read
    assert "self._two_phase" not in read


# --------------------------------------------------------- lot 3 review §1.2 (694eb3e)
async def test_a_group_reorder_never_loses_a_member_and_never_dedupes_in_silence(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A list naming one shutter twice filled two of that group's seats and dropped one.

    `async_reorder`'s group branch puts a group's members back into the seats that group
    holds in the flat stored order, one seat per member. A repeated id took two seats,
    `normalised_order` deduplicated on the way into the store, and a different member of
    the group fell out of the order altogether: `{81, 82}` reordered as `[81, 81]` stored
    `[81, 84]`, with 82 gone and nothing on any screen saying so.

    Two halves, and both are here because they are two decisions: a repeat is refused
    (quietly deduplicating would leave the stored order different from the one on the
    screen), and a list merely *shorter* than the group is not - the members it leaves
    out keep their places at the end of that group.

    Mutation caught: `vol.Unique()` off the order schema; the group branch without its
    tail fill.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        before = loaded_store(hass, entry).raw_order

        error = await refused(
            client,
            type=WS_TYPE_REORDER,
            entry_id=entry.entry_id,
            order=[FIRST, FIRST],
            profile="tall",
        )
        assert error["code"] == ws_const.ERR_INVALID_FORMAT
        assert loaded_store(hass, entry).raw_order == before

        # ...and a group stated short keeps the member it does not name.
        await result(
            client, type=WS_TYPE_REORDER, entry_id=entry.entry_id, order=[FIRST], profile="tall"
        )
        stored = loaded_store(hass, entry).raw_order
        assert FIRST in stored and SECOND in stored, stored


# ------------------------------------------------------- lot 1-2 review §1 (62d0f34)
async def test_a_key_the_file_states_only_through_a_fallback_is_still_the_file_s(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """One rule for "what does the file write", and two readers that share it.

    `panel_data` computed the file's keys as `set(keys_from_file)` while the precedence
    beside it widened the same set by the file's own fallbacks - a cover whose file says
    `roll: 1.5` has stated both directional rolls, and one that says `opening_time:` has
    stated the descent too. So the detail screen printed `origin: "file"` next to
    `file_value: null`, and offered the user's own `roll:` line as this integration's
    default.

    The fix made the widening one exported function. Held here from the outside - the
    payload a browser really receives - and from the inside, with the function asked the
    same question directly, because "one rule" is the fix and two readers agreeing by
    accident is the bug.

    Mutation caught: reading `keys_from_file` anywhere but through
    `keys_written_by_the_file`.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML) as (entry, _commands):
        client = await hass_ws_client(hass)
        detail = await result(
            client, type=WS_TYPE_COVER_DETAIL, entry_id=entry.entry_id, cover_unique_id=FIRST
        )
        keys = {item["key"]: item for item in detail["keys"]}
        # The file writes `roll: 1.2` and `opening_time: 30`; it never writes these two.
        for key, value in ((CONF_OPENING_ROLL, 1.2), (CONF_CLOSING_ROLL, 1.2)):
            assert keys[key]["origin"] == "file", key
            assert keys[key]["file_value"] == value, key
            assert keys[key]["default_value"] is None, key

        # ...and the one function says the same thing about the same cover.
        written = keys_written_by_the_file(
            {CONF_KEYS_FROM_FILE: [CONF_ROLL, CONF_OPENING_TIME, CONF_SLAT_TIME]}
        )
        assert {CONF_OPENING_ROLL, CONF_CLOSING_ROLL, CONF_CLOSING_TIME} <= written


# ---------------------------------------------------------- lot 6b review §8 (f68ccf7)
@pytest.mark.parametrize(
    ("case", "assignments", "key", "its_own"),
    [
        (
            "a profile nobody defines",
            [{"cover_unique_id": FIRST, "profile": "nope"}],
            ERROR_UNKNOWN_PROFILE,
            {"profile": "nope"},
        ),
        (
            "a window whose travel nobody knows",
            [{"cover_unique_id": f"{MAC}-2-84", "profile": "tall"}],
            ERROR_MISSING_TRAVEL,
            {},
        ),
    ],
    ids=["unknown_profile", "missing_travel"],
)
async def test_a_refused_batch_carries_the_words_its_sentence_needs(
    hass: HomeAssistant,
    tmp_path,
    hass_ws_client,
    case: str,
    assignments: list[dict[str, Any]],
    key: str,
    its_own: dict[str, str],
) -> None:
    """`_refuse_the_batch` sends the offending item's placeholders, not an empty dict.

    A refusal is rendered by the panel through `exceptions.<key>.message`, and those
    sentences carry `{profile}`, `{covers}` and `{count}`. Sent without them the panel
    shows a sentence with braces in it - which is worse than no sentence, because it
    reads as a bug in the panel rather than as an answer about the user's own batch.

    The rendering itself is held in `test_translations.py`, over the real files. What is
    held here is the frame: the placeholders reach the socket, and they name the items
    that hit the *first* kind of problem, which is what the panel marks its rows from.

    Mutation caught: `placeholders = {}` in `_refuse_the_batch`.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        error = await refused(
            client, type=WS_TYPE_ASSIGN, entry_id=entry.entry_id, assignments=assignments
        )
        assert error["code"] == ws_const.ERR_SERVICE_VALIDATION_ERROR, case
        assert error["translation_key"] == key, case
        placeholders = error["translation_placeholders"]
        assert placeholders, case
        assert placeholders["count"] == "1", case
        assert placeholders["covers"], case
        # `covers` and `count` are the batch's; these are the offending *item's*, and
        # they are the half `placeholders = {}` used to drop while the other two went on
        # arriving - so a test that checked only the batch's would have stayed green.
        for name, value in its_own.items():
            assert placeholders.get(name) == value, (case, name)
        # An English sentence beside the key, so a client is never left with a token.
        assert "{" not in error["message"], case


# ----------------------------------------------------------- lot 8 review §1.1 (3577d72)
# `myhome.yaml` assigns the profile itself, which is the one state in which the preview
# could name a profile the write would not produce.
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
    porch_shutter:
      where: '81'
      name: Porch Shutter
      profile: from_the_file
      height: 195
"""
PORCH = f"{MAC}-2-81"


async def test_the_preview_names_the_profile_the_shutter_would_really_follow(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`preview.profile` is the profile that *applies*, not the one that was asked about.

    A window whose `myhome.yaml` carries a `profile:` line cannot be taken out of that
    profile from here: popping an assignment it does not have leaves the record as it is
    and the file goes on answering. The preview used to answer `null` to such an item
    while the row the write then produced said the name - `values`, `origin` and `source`
    all agreed, and only this field did not.

    The parity assertion was green for two lots because no fixture had such a window.
    That is the shape of this defect and the reason it is in this register: the test was
    right and the *fixture* was missing, which is a failure no amount of reading the
    assertion would have found.

    Mutation caught: answering the profile from the question instead of from the
    resolution.
    """
    async with setup_myhome(hass, tmp_path, FILE_PROFILE_YAML) as (entry, _commands):
        client = await hass_ws_client(hass)
        answer = await result(
            client,
            type=WS_TYPE_PREVIEW,
            entry_id=entry.entry_id,
            items=[{"cover_unique_id": PORCH, "profile": None}],
        )
        previewed = answer["items"][0]
        assert previewed["profile"] == "from_the_file"

        # ...and the write really does produce that row.
        written = await result(
            client,
            type=WS_TYPE_ASSIGN,
            entry_id=entry.entry_id,
            assignments=[{"cover_unique_id": PORCH, "profile": None}],
        )
        row = row_of(written["overview"], PORCH)
        for field in ("profile", "origin", "source", "values", "has_own", "height"):
            assert previewed[field] == row[field], field


# ----------------------------------------------------------- lot 8 review §1.2 (4b19c0a)
async def test_the_impact_preview_says_the_roll_the_edit_it_previews_would_write(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """A stored profile does not carry `roll`; the read path derives it from `closing_roll`.

    `_hypothetical_profiles` merged the six numbers straight into the config-shaped
    mapping, so overriding `closing_roll` left the *old* `roll` standing beside the new
    directional pair and the answer named a number `profile_edit` could not produce.
    Found by writing, for this command, the parity assertion the assignment preview has
    had since lot 3: preview with `profile_values`, then edit with the same numbers, then
    compare.

    Not user-visible on any screen that ships today, because the profile card draws
    `PROFILE_VALUE_KEYS` and `roll` is not one of them - which is exactly why it belongs
    here rather than only in a screen test: it is a contract field, and the next screen
    to read it would have read a lie.

    Mutation caught: merging the numbers instead of rebuilding the record through
    `profile_as_config`.
    """
    values = {
        CONF_OPENING_TIME: 20.0,
        CONF_CLOSING_TIME: 19.5,
        CONF_SLAT_TIME: 3.5,
        CONF_OPENING_ROLL: 1.9,
        CONF_CLOSING_ROLL: 1.5,
    }
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        previewed = (
            await result(
                client,
                type=WS_TYPE_PREVIEW,
                entry_id=entry.entry_id,
                items=[{"cover_unique_id": SECOND, "profile": "tall"}],
                profile_values={"tall": {**values, "reference_height": 195}},
            )
        )["items"][0]

        written = await result(
            client,
            type=WS_TYPE_PROFILE_EDIT,
            entry_id=entry.entry_id,
            name="tall",
            values=values,
            reference_height=195,
        )
        row = row_of(written["overview"], SECOND)
        assert previewed["values"][CONF_ROLL] == row["values"][CONF_ROLL]
        for field in ("values", "origin", "source", "has_own", "height", "profile"):
            assert previewed[field] == row[field], field


# ----------------------------------------------------------- lot 8 review §1.3 (c508722)
async def test_the_detail_and_the_removal_that_follows_it_are_one_answer(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """"Rimuovi la misura" names where the window lands, before it removes anything.

    The destination is read by resolving the window again with the record gone - the
    same resolution `cover_forget` performs *after* the write - and not predicted from a
    rule. `keys[].inherited_value` is not the answer to that question and must not be
    used for it: it takes the overrides away and leaves the record, which is right for
    an emptied field and wrong for a removal that takes the assignment and a
    panel-typed travel with it.

    Held by comparing the two answers rather than the two rules.

    Mutation caught: computing `forget` from `inherited_*`; computing it from a map of
    "what a record like this falls back to".
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML, calibration=CALIBRATION) as (
        entry,
        _commands,
    ):
        client = await hass_ws_client(hass)
        detail = await result(
            client, type=WS_TYPE_COVER_DETAIL, entry_id=entry.entry_id, cover_unique_id=FIRST
        )
        promised = detail["forget"]

        answer = await result(
            client, type=WS_TYPE_COVER_FORGET, entry_id=entry.entry_id, cover_unique_id=FIRST
        )
        assert promised["falls_back_to"] == answer["falls_back_to"]
        assert promised["profile"] == answer["profile"]
        # ...and the row the shutter really ends up with agrees with the promise.
        row = row_of(answer["overview"], FIRST)
        assert (row["profile"] is not None) is (promised["falls_back_to"] == "profile")


# ------------------------------------------------------------------------ the register
# The defects whose tests need no second angle, because a second angle would be a copy.
# Named so that deleting one is a failing test rather than a quiet loss: every one of
# them is the only thing standing between a fixed defect and its return.
HELD_ELSEWHERE: dict[str, tuple[str, str]] = {
    # lot 3 review §1.3: the snapshot's only work is on the path that does not go
    # through `_finish_movement` - a run reversed under the motor.
    "test_a_reversal_after_a_refresh_is_planned_with_the_new_model": (
        "tests/test_panel_refresh.py",
        "lot 3 review 1.3",
    ),
    # lot 3 review §1.3: the claim is taken with no `await` between it and the refusal
    # that guards it, over a store load that really suspends.
    "test_two_frames_in_one_tick_cannot_both_find_the_gateway_free": (
        "tests/test_websocket_api.py",
        "lot 3 review 1.3",
    ),
    # lot 3 review §1.4: the one order the lock cannot rule out, and its defined outcome.
    "test_a_measurement_that_opens_while_a_write_is_being_applied": (
        "tests/test_websocket_api.py",
        "lot 3 review 1.4",
    ),
    # lot 3 review §1.1, the behavioural half of the frozen model's missing field.
    "test_a_slat_phase_taken_away_leaves_the_run_in_flight_its_slat_leg": (
        "tests/test_panel_refresh.py",
        "lot 3 review 1.1",
    ),
    # lot 3 review §1.5: two gateways are two subscriptions.
    "test_two_gateways_are_two_subscriptions": (
        "tests/test_websocket_api.py",
        "lot 3 review 1.5",
    ),
}

# Deliberately not in the register: `tests/test_panel_build.py`, which holds lot 8's
# CSS-minifier rule. It is the frontend lot's file and its test names are that lot's to
# choose; naming one here would make a rename over there a failure over here, which is a
# coupling worth more than the guard.


def test_every_test_this_register_points_at_is_still_there() -> None:
    """A register of defects is worth what its entries still name.

    The tests above are the second angle on six defects; these six have only one, and a
    rename or a deletion would take the whole guard with it without a single failure -
    which is precisely how a fixed defect comes back. Read out of the files with `ast`
    rather than by importing them, so that naming a test here costs nothing at runtime.

    Mutation caught: deleting or renaming any of the six.
    """
    for name, (path, review) in HELD_ELSEWHERE.items():
        source = ast.parse((HERE.parent / path).read_text(encoding="utf-8"))
        defined = {
            node.name
            for node in ast.walk(source)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        assert name in defined, f"{path} no longer has {name} ({review})"


# ------------------------------------------------------- three branches nothing ran
# Not defects: three answers the contract states, that no test had ever asked for. They
# are here rather than in a file of their own because they are the same kind of thing as
# the register - a statement somebody made once, with nothing holding it - and because
# each of them is the answer a screen shows at exactly the moment the user is confused.


async def test_a_house_with_no_loaded_gateway_is_told_so_and_not_shown_an_empty_one(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """`entry_id` omitted means "the one gateway I have", and there may be none.

    The panel opens and asks what there is before it can draw anything, so this is the
    first frame of a first run and of every run where the gateway failed to set up.
    "Not found" and an empty overview are very different screens: the second is a house
    with no shutters in it and no reason why.

    Mutation caught: answering an overview built from no gateway at all; letting
    `loaded[0]` raise an `IndexError` into the connection.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML) as (entry, _commands):
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        client = await hass_ws_client(hass)
        error = await refused(client, type=WS_TYPE_OVERVIEW)
        assert error["code"] == ws_const.ERR_NOT_FOUND
        assert error["translation_key"] == ERROR_UNKNOWN_ENTRY
        assert error["translation_domain"] == DOMAIN


async def test_renaming_a_profile_to_the_name_it_has_moves_nothing(
    hass: HomeAssistant, tmp_path, hass_ws_client
) -> None:
    """CONTRACT §9.7: "renaming to the same name is a no-op with `moved: 0`".

    The rename is three store writes in one awaited sequence - the numbers under the new
    name, every follower repointed, the old name removed - and running that sequence
    with both names the same would write the profile, repoint its followers to where
    they already are, and then *delete the name it had just written*. The early return
    is what stops it, and nothing was asking for it.

    Mutation caught: dropping the `new_name == name` branch (the profile disappears and
    takes its followers' assignments with it).
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
            new_name="tall",
        )
        assert answer["moved"] == 0
        assert answer["from_file"] == []
        # A write that changed nothing offers no undo, and the profile is still there
        # with its followers on it.
        assert answer["undo_token"] is None
        assert loaded_store(hass, entry).profile("tall")["opening_time"] == 22.3
        assert sorted(loaded_store(hass, entry).covers_following("tall")) == sorted([FIRST, SECOND])


async def test_an_installation_with_no_translations_at_all_gets_an_empty_book(
    hass: HomeAssistant, tmp_path
) -> None:
    """The last line of `async_texts`, which a shipped installation cannot reach.

    `translations/en.json` ships with the integration, so the fallback chain always ends
    somewhere - unless the files are not there, which is what a half-finished HACS
    update or a partially restored backup looks like. The panel then shows its keys
    instead of its sentences, which is ugly and readable; an exception three layers up
    would be a panel that does not paint at all, on an installation whose owner is
    already trying to work out what went wrong.

    Mutation caught: raising, or returning `None`, when no language could be read.
    """
    async with setup_myhome(hass, tmp_path, WRITE_YAML) as (_entry, _commands):
        with patch.object(panel_data, "_read_language", return_value=None):
            hass.data.pop(panel_data.TEXTS_CACHE_KEY, None)
            answer = await panel_data.async_texts(hass, "it")
        assert answer == {
            "language": "en",
            "requested": "it",
            "fallback": True,
            "texts": {},
        }


async def test_a_hand_edit_in_the_dialog_keeps_the_measurements_behind_the_numbers(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The `raw` block survives a correction typed into the dialog — audit, 0.6.0.

    A guided calibration keeps the readings it took, under `raw`, for a human to argue
    with six months later. The panel's own hand edit carries that block over and said so
    in a docstring; the *dialog's* hand edit built the record without it, so a number
    corrected under "Configura" threw the evidence away.

    Harmless while nothing read it. 0.6.0 reads it: `cover_detail.cover.level` is how
    thorough the calibration was and `verify_note` is what the tape check came to, and
    both are taken out of `raw`. So correcting one run time by one tenth emptied two
    columns of a screen that had not asked about them, and no screen said why.

    The two writers agree now. This drives the dialog because that is the half that was
    wrong; `test_websocket_api` holds the panel's half from the other side.

    Mutation caught: dropping `raw=` from `async_step_calibration_edit` again; passing
    the record's own `raw` after the record has been rewritten, which is `None`.
    """
    async with calibrating(hass, tmp_path, OWN_NUMBERS_YAML) as (entry, _commands):
        await measured_profile(hass, entry, freezer)
        before = the_store(hass, entry).raw_covers[UNIQUE_ID][CONF_RAW]
        assert before, "path A is supposed to leave its readings on the record"

        result = await choose(hass, await open_dialog(hass, entry), "calibrations")
        result = await submit(hass, result, {"cover": UNIQUE_ID})
        result = await choose(hass, result, "calibration_edit")
        result = await submit(hass, result, {CONF_HEIGHT: "190", CONF_OPENING_TIME: "24,5"})
        assert result["step_id"] == "calibration_actions"

        record = the_store(hass, entry).raw_covers[UNIQUE_ID]
        assert record[CONF_OVERRIDES][CONF_OPENING_TIME] == 24.5
        assert record[CONF_RAW] == before
