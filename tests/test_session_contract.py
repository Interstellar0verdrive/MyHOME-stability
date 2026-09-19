"""The calibration session's contract, frozen before either half of it is written.

0.6.0 wizard, lot L0. The guided calibration moves from the *Configure* dialog into the
panel, and the backend (lots B2-B4) and the frontend (lots F1-F3) are written at the
same time, each against the same four files:

* `custom_components/myhome/panel_schemas.py` - the names, the payload schemas and the
  keys of every answer;
* `panel_src/src/engine/session-contract.ts` - the same, as TypeScript types;
* `docs/panel-websocket-api.md` §11-§14 - the same, in prose;
* `tests/fixtures/panel_session_examples.json` - one snapshot per screen, written by
  hand until lot B3 regenerates it from the real controller.

Nothing here runs a session: no command is registered yet. What is tested is that the
four say the same thing, and that what they say is anchored in the code that already
exists - the dialog's real step ids, its real texts and their placeholders - so that a
contract written in the abstract cannot name a step the dialog does not have or a
sentence that talks about a dialog the panel does not show.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.myhome import panel_schemas as ps
from custom_components.myhome.calibration_flow import (
    ERROR_ABOVE_THE_TRAVEL,
    ERROR_INVALID_NAME,
    ERROR_NOT_A_NUMBER,
    ERROR_OUT_OF_RANGE,
    PATH_FIRST,
    PATH_PROFILE,
    PATH_REFINE,
    PLAN_FULL,
    PLAN_PRECISE,
    PLAN_PRECISE_TRAVEL,
    PLAN_PROFILE,
    PLAN_TIMES,
    PLAN_TIMES_AND_ROLLS,
    PLAN_VERIFY_B,
    PROBLEM_REASONS,
    GuidedCalibrationMixin,
)
from custom_components.myhome.const import DIRECTION_CLOSE, DIRECTION_OPEN

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "myhome"
FIXTURE = ROOT / "tests" / "fixtures" / "panel_session_examples.json"
CONTRACT_TS = ROOT / "panel_src" / "src" / "engine" / "session-contract.ts"
API_DOC = ROOT / "docs" / "panel-websocket-api.md"

# The two languages the maintainer writes and reads (decision of 18 Sep): the reuse of
# the dialog's texts is checked in both, because a word that names the dialog is a word
# in a sentence, and each language builds its sentences its own way.
TEXT_LANGUAGES = ("en", "it")
DIALOG_WORDS = ("dialog", "Configur", "Calibrazioni")
PLACEHOLDER = re.compile(r"\{(\w+)\}")

# The screens the frontend is built against before the backend exists (PLAN L0,
# criterion 4). One snapshot each, no more and no fewer: a missing one is a screen F2
# has nothing to draw, an extra one is a screen nobody asked for and nobody tests.
#
# Five are beyond the plan's list, added after the independent review: the profile form
# of path B (the only `choice` form there is), a shutter moved from outside while a
# screen was being read, a reading made stale by such a movement, and the two endings
# the texts of SPEC §5.5 cover and no example did (`left`, `cover_gone`).
SCENARIOS: tuple[str, ...] = (
    "armed_path",
    "armed_path_b_profile_choice",
    "armed_path_c_profile_choice",
    "armed_refine_scope_intent",
    "briefing_open_brief",
    "briefing_open_brief_rehomed",
    "running_open_start",
    "running_open_lift",
    "running_lift_stop",
    "briefing_lift_check",
    "briefing_lift_check_external",
    "awaiting_reading_lift_gap",
    "positioning_home_closed",
    "positioning_tape_run",
    "awaiting_reading_measure_descent",
    "awaiting_reading_measure_descent_error",
    "awaiting_reading_measure_descent_stale",
    "awaiting_reading_height",
    "briefing_profile_name",
    "review_basic",
    "review_basic_profile_exists",
    "review_precise",
    "review_short",
    "review_correction",
    "briefing_verify_offer",
    "positioning_verify",
    "awaiting_reading_measure_verify",
    "checking_verify_result_within",
    "checking_verify_result_offers_c",
    "problem_no_echo",
    "problem_interrupted",
    "saved_profile",
    "saved_cover_only",
    "ended_cancelled",
    "ended_expired",
    "ended_unloaded",
    "ended_left",
    "ended_cover_gone",
    "owned_by_other",
)

SCHEMAS: dict[str, Any] = {
    ps.WS_TYPE_SESSION_GET: ps.SESSION_GET_SCHEMA,
    ps.WS_TYPE_SESSION_START: ps.SESSION_START_SCHEMA,
    ps.WS_TYPE_SESSION_ATTACH: ps.SESSION_ATTACH_SCHEMA,
    ps.WS_TYPE_SESSION_HEARTBEAT: ps.SESSION_HEARTBEAT_SCHEMA,
    ps.WS_TYPE_SESSION_ACT: ps.SESSION_ACT_SCHEMA,
    ps.WS_TYPE_SESSION_STOP: ps.SESSION_STOP_SCHEMA,
    ps.WS_TYPE_SESSION_LEAVE: ps.SESSION_LEAVE_SCHEMA,
    ps.WS_TYPE_SESSION_CANCEL: ps.SESSION_CANCEL_SCHEMA,
    ps.WS_TYPE_SESSION_SAVE: ps.SESSION_SAVE_SCHEMA,
    ps.WS_TYPE_SESSION_END_OTHER: ps.SESSION_END_OTHER_SCHEMA,
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture() -> dict[str, Any]:
    return load(FIXTURE)


def scenarios() -> dict[str, dict[str, Any]]:
    return fixture()["scenarios"]


def step_texts(language: str) -> dict[str, Any]:
    return load(COMPONENT / "translations" / f"{language}.json")["options"]["step"]


def progress_texts(language: str) -> dict[str, str]:
    return load(COMPONENT / "translations" / f"{language}.json")["options"]["progress"]


def placeholders_in(text: Any) -> set[str]:
    return set(PLACEHOLDER.findall(json.dumps(text, ensure_ascii=False)))


def wire_schema(command: str) -> vol.Schema:
    """The schema exactly as Home Assistant will apply it, `id` and all.

    Built by the real decorator rather than by `vol.Schema(...)` here, so that the frames
    below are held to what the socket will do with them: HA extends a dict schema with
    its own base message schema, and a `vol.All` one by extending its first validator.
    """

    def handler(hass, connection, msg) -> None:  # pragma: no cover - never called
        """A command body nobody runs: only the schema the decorator attaches is read."""

    return websocket_api.websocket_command(SCHEMAS[command])(handler)._ws_schema


def keyed(value: Mapping[str, Any] | None, keys: tuple[str, ...], where: str) -> None:
    if value is not None:
        assert tuple(value) == keys, f"{where}: {sorted(set(value) ^ set(keys))}"


# ------------------------------------------------------------------ the fixture's shape
def test_the_fixture_has_one_snapshot_per_screen_the_plan_names() -> None:
    """The list of screens is the plan's, whole and in order.

    Mutation caught: a scenario renamed, dropped or added in the fixture alone.
    """
    assert tuple(scenarios()) == SCENARIOS


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_snapshot_has_exactly_the_keys_of_the_contract(name: str) -> None:
    """Every key always present, in the contract's order, and nothing else - all the way down.

    The frontend is written against these files before the server that produces them
    exists; a key present here and absent from `SESSION_KEYS` (or the reverse) would be
    a field F2 reads and B2 never writes.

    Mutation caught: a key added to a snapshot and not to the tuples; a sub-object missing
    a key; `lift` or a fit point with a stray field.
    """
    snap = scenarios()[name]
    keyed(snap, ps.SESSION_KEYS, "snapshot")
    keyed(snap["cover"], ps.SESSION_COVER_KEYS, "cover")
    keyed(snap["intent"], ps.SESSION_INTENT_KEYS, "intent")
    keyed(snap["form"], ps.SESSION_FORM_KEYS, "form")
    keyed(snap["movement"], ps.SESSION_MOVEMENT_KEYS, "movement")
    keyed(snap["press"], ps.SESSION_PRESS_KEYS, "press")
    keyed(snap["reading"], ps.SESSION_READING_KEYS, "reading")
    keyed(snap["measured"], ps.SESSION_MEASURED_KEYS, "measured")
    keyed(snap["measured"]["lift"], ps.SESSION_LIFT_KEYS, "measured.lift")
    keyed(snap["fit"], ps.SESSION_FIT_KEYS, "fit")
    for direction in (snap["fit"] or {}).values():
        keyed(direction, ps.SESSION_FIT_DIRECTION_KEYS, "fit.<direction>")
        for point in direction["points"]:
            keyed(point, ps.SESSION_FIT_POINT_KEYS, "fit.<direction>.points[]")
    keyed(snap["check"], ps.SESSION_CHECK_KEYS, "check")
    keyed(snap["review"], ps.SESSION_REVIEW_KEYS, "review")
    review = snap["review"] or {"rows": [], "side_effects": [], "affected": []}
    for row in (*review["rows"], *review["side_effects"]):
        keyed(row, ps.SESSION_REVIEW_ROW_FIELDS, "review.rows[]")
    for follower in review["affected"]:
        keyed(follower, ps.SESSION_REVIEW_AFFECTED_KEYS, "review.affected[]")
        for row in follower["rows"]:
            keyed(row, ps.SESSION_REVIEW_ROW_FIELDS, "review.affected[].rows[]")
    keyed(snap["problem"], ps.SESSION_PROBLEM_KEYS, "problem")
    keyed(snap["owner"], ps.SESSION_OWNER_KEYS, "owner")
    keyed(snap["outcome"], ps.SESSION_OUTCOME_KEYS, "outcome")


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_snapshot_speaks_only_the_contracts_vocabulary(name: str) -> None:
    """Every token is one the contract declares, and the tokens agree with each other.

    The rules of §12 that a hand-written example could get wrong: a substate only while
    running, no step on a terminal snapshot, a problem step that names its own code, a
    review whose variant is the summary it stands on, an outcome only when it is over.

    Mutation caught: `fitting` or `idle` as a state; an action the dialog does not have;
    `problem_no_echo` with `problem.code: "busy"`; an outcome on a live session.
    """
    snap = scenarios()[name]
    state = snap["state"]
    assert state in ps.SESSION_STATES
    assert (snap["substate"] is None) or (state == "running" and snap["substate"] in ps.SESSION_SUBSTATES)
    assert snap["path"] in (None, *ps.SESSION_PATHS)
    assert snap["scope"] in (None, *ps.SESSION_SCOPES)
    assert snap["level"] in ps.SESSION_LEVELS
    assert set(snap["plan"]) <= set(ps.SESSION_PLAN_STAGES)
    assert (snap["plan_index"] is None) == (not snap["plan"])
    if snap["plan"]:
        assert 0 <= snap["plan_index"] < len(snap["plan"])
    assert isinstance(snap["revision"], int) and snap["revision"] >= 0
    assert set(snap["actions"]) <= set(ps.SESSION_ACTIONS)
    assert snap["notice"] in (None, *ps.SESSION_NOTICES)
    # `{cover}` opens nearly every sentence of the dialog, and it is substituted from
    # `placeholders`, never from `cover`: the two have to name the same shutter.
    assert snap["placeholders"]["cover"] == snap["cover"]["name"]
    if snap["notice"] == "reading_stale":
        # The reading on the screen is not this step's any more, so repeating it is the
        # first thing offered (§11.5).
        assert snap["actions"][:1] == ["repeat_tape"]
    assert snap["position_known"] in (None, *ps.SESSION_POSITIONS)
    assert isinstance(snap["external_move"], bool)

    terminal = state in ("saved", "ended")
    assert (snap["step"] is None) == terminal
    assert (snap["outcome"] is not None) == terminal
    if terminal:
        assert snap["outcome"]["reason"] in ps.SESSION_OUTCOMES
        assert (snap["outcome"]["reason"] == "saved") == (state == "saved")
        assert snap["actions"] == [] and snap["owner"] is None and snap["idle_expires_at"] is None
        assert snap["movement"] is None and snap["press"] is None and snap["form"] is None
    else:
        assert snap["step"] in ps.SESSION_STEPS
        assert snap["idle_expires_at"] is not None

    if snap["problem"] is not None:
        assert snap["problem"]["code"] in ps.SESSION_PROBLEMS
        assert snap["step"] == f"problem_{snap['problem']['code']}"
    elif snap["step"] is not None:
        assert not snap["step"].startswith("problem_")

    if (form := snap["form"]) is not None:
        assert form["field"] in ps.SESSION_FORM_FIELDS
        assert form["kind"] in ps.SESSION_FORM_KINDS
        assert form["unit"] in (None, *ps.SESSION_FORM_UNITS)
        assert (form["choices"] is not None) == (form["kind"] == "choice")
        assert form["error"] in (None, *ps.SESSION_FORM_ERRORS)
    if (movement := snap["movement"]) is not None:
        assert movement["kind"] in ps.SESSION_MOVEMENT_KINDS
        assert movement["direction"] in ps.SESSION_DIRECTIONS
        assert movement["progress_action"] in ps.SESSION_PROGRESS_ACTIONS
    if snap["press"] is not None:
        assert snap["press"]["kind"] in ps.SESSION_PRESS_KINDS
        assert snap["substate"] == "awaiting_endpoint"
    if snap["substate"] == "awaiting_endpoint":
        assert snap["press"] is not None
    if snap["reading"] is not None:
        assert state == "awaiting_reading"
        assert snap["reading"]["direction"] in ps.SESSION_DIRECTIONS
        assert snap["reading"]["from_end_stop"] in ps.SESSION_POSITIONS
    if snap["intent"] is not None:
        assert snap["intent"]["scope"] in ps.SESSION_SCOPES
    if (review := snap["review"]) is not None:
        assert review["variant"] in ps.SESSION_REVIEW_VARIANTS
        if state == "review":
            assert snap["step"] == f"summary_{review['variant']}"
        assert review["targets"] and set(review["targets"]) <= set(ps.SESSION_SAVE_TARGETS)
        assert [row["key"] for row in review["rows"]] == list(ps.SESSION_REVIEW_ROW_KEYS)
        assert {row["key"] for row in review["side_effects"]} <= set(ps.SESSION_VALUE_KEYS)
        assert set(review["replacing"]) | set(review["keeping"]) <= set(ps.SESSION_REVIEW_ROW_KEYS)
        assert review["name_clash"] in (None, "file")
    elif state == "review":
        pytest.fail("a snapshot in review without its review")
    if snap["check"] is not None:
        assert snap["check"]["profile_level"] in (None, *ps.SESSION_LEVELS)


def test_every_owned_snapshot_has_an_owner_and_one_belongs_to_another_tab() -> None:
    """The fixture names the tab it is seen from, and one screen is somebody else's.

    `owned_by_other` is the read-only screen with "Prendi il controllo": it only means
    something if the owner in it is not the tab the other examples belong to.

    Mutation caught: every example owned by the same client, which would leave F2's
    read-only branch with no example to be drawn from.
    """
    data = fixture()
    this_tab = data["_example"]["this_client_id"]
    other_tab = data["_example"]["other_client_id"]
    owners = {name: snap["owner"]["client_id"] for name, snap in scenarios().items() if snap["owner"]}
    assert owners.pop("owned_by_other") == other_tab
    assert set(owners.values()) == {this_tab}


# ------------------------------------------------------------------ the fixture's lists
def test_the_fixture_restates_the_contract_lists_exactly() -> None:
    """`_contract` is the frontend's copy of the lists it cannot import from Python.

    `wizard/steps.ts` (lot F2) is tested to have a row for every step here, and to take
    the dialog's texts for every reused one: these lists are what it is tested against,
    so they must be the constants themselves.

    Mutation caught: a step added to `SESSION_STEPS` and not to the fixture, or the other
    way round; the capabilities edited in one place.
    """
    contract = fixture()["_contract"]
    assert contract["steps"] == list(ps.SESSION_STEPS)
    assert contract["reused_steps"] == list(ps.SESSION_REUSED_STEPS)
    assert contract["states"] == list(ps.SESSION_STATES)
    assert contract["error_keys"] == list(ps.SESSION_ERROR_KEYS)
    assert contract["problems"] == list(ps.SESSION_PROBLEMS)
    assert contract["outcomes"] == list(ps.SESSION_OUTCOMES)
    assert contract["plan_stages"] == list(ps.SESSION_PLAN_STAGES)
    assert contract["actions"] == list(ps.SESSION_ACTIONS)
    assert contract["save_targets"] == list(ps.SESSION_SAVE_TARGETS)
    assert contract["notices"] == list(ps.SESSION_NOTICES)
    assert contract["progress_actions"] == list(ps.SESSION_PROGRESS_ACTIONS)
    assert contract["holders"] == list(ps.SESSION_HOLDERS)
    assert contract["capabilities"] == json.loads(json.dumps(ps.SESSION_CAPABILITIES))


# ------------------------------------------------------------ anchored in the dialog
def test_every_step_is_a_step_the_dialog_really_has() -> None:
    """The step ids are the dialog's own `async_step_<id>` methods, not a likeness of them.

    They are the keys of seven languages of text; a step spelled differently here would be
    a screen with no words on it. `problem_interrupted` is the one step the panel adds.

    Mutation caught: `open_timed` written `open_time`; a step of the dialog renamed.
    """
    for step in ps.SESSION_STEPS:
        if step == "problem_interrupted":
            continue
        assert callable(getattr(GuidedCalibrationMixin, f"async_step_{step}", None)), step
    assert len(set(ps.SESSION_STEPS)) == len(ps.SESSION_STEPS)
    assert {f"problem_{code}" for code in ps.SESSION_PROBLEMS} <= set(ps.SESSION_STEPS)


def test_the_plans_and_their_stages_are_the_dialogs() -> None:
    """Every stage any plan of the dialog walks can appear in `plan`, and is a step.

    Mutation caught: a plan stage missing from `SESSION_PLAN_STAGES`, which B2 would then
    be unable to report without amending the contract.
    """
    stages: set[str] = set()
    for plan in (
        PLAN_FULL,
        PLAN_PRECISE,
        PLAN_PRECISE_TRAVEL,
        PLAN_PROFILE,
        PLAN_TIMES,
        PLAN_TIMES_AND_ROLLS,
        PLAN_VERIFY_B,
    ):
        stages |= set(plan)
    assert stages == set(ps.SESSION_PLAN_STAGES)
    assert set(ps.SESSION_PLAN_STAGES) - {"summary"} <= set(ps.SESSION_STEPS)


def test_the_vocabularies_that_come_from_the_dialog_are_the_dialogs() -> None:
    """Paths, problems, directions and form errors are the dialog's constants, spelled alike.

    Declared as literals in `panel_schemas` so the contract reads in one place without
    importing the dialog; held to the dialog here.

    Mutation caught: a reason added to `PROBLEM_REASONS` and not to the session; the
    session's `interrupted` placed anywhere but last.
    """
    assert ps.SESSION_PATHS == (PATH_FIRST, PATH_PROFILE, PATH_REFINE)
    assert (*PROBLEM_REASONS, "interrupted") == ps.SESSION_PROBLEMS
    assert set(ps.SESSION_DIRECTIONS) == {DIRECTION_OPEN, DIRECTION_CLOSE}
    assert set(ps.SESSION_PROGRESS_ACTIONS) == set(progress_texts("en"))
    assert set(ps.SESSION_FORM_ERRORS) == {
        ERROR_NOT_A_NUMBER,
        ERROR_OUT_OF_RANGE,
        ERROR_ABOVE_THE_TRAVEL,
        ERROR_INVALID_NAME,
    }
    capabilities = ps.SESSION_CAPABILITIES
    assert capabilities["paths"] == list(ps.SESSION_PATHS)
    assert capabilities["levels"] == list(ps.SESSION_LEVELS)
    assert capabilities["scopes"] == list(ps.SESSION_SCOPES)
    assert capabilities["save_targets"] == list(ps.SESSION_SAVE_TARGETS)


def test_every_action_is_a_menu_option_the_dialog_labels() -> None:
    """An action's label is `options.step.<step>.menu_options.<action>`, so it must have one.

    And the other way round: every menu option of a step the session walks is an action,
    except the dialog's two ways out - `save`, which is the `save` command, and
    `cancel_flow`, which is the `cancel` verb and must never travel on a message carrying
    a revision (§11.2).

    Mutation caught: an action invented for the panel with no label anywhere; a menu
    option of a reused step forgotten in `SESSION_ACTIONS`; `cancel_flow` put back among
    the actions, where a stale revision could refuse it.
    """
    texts = load(COMPONENT / "strings.json")["options"]["step"]
    labelled = {
        option
        for step in ps.SESSION_STEPS
        for option in texts.get(step, {}).get("menu_options", {})
    }
    assert set(ps.SESSION_ACTIONS) == labelled - {"save", "cancel_flow"}
    assert "cancel_flow" not in ps.SESSION_ACTIONS


# The one action offered on a screen whose own texts do not label it: a reading made
# stale by a movement from outside is repeated with `repeat_tape`, and a reading step has
# no menu of its own, so the label is borrowed from the screen that normally offers it
# (§11.5). Anything else borrowed would be a label the panel would have to invent.
BORROWED_LABELS: dict[str, str] = {"repeat_tape": "tape_result"}


@pytest.mark.parametrize("name", SCENARIOS)
def test_the_actions_of_a_reused_step_are_the_ones_its_texts_label(name: str) -> None:
    """A snapshot never offers, on a dialog screen, a button that screen has no label for.

    The one exception is written down rather than waved through: `repeat_tape` on a stale
    reading, whose label comes from `tape_result` and is checked to be there.

    Mutation caught: `lift_gap` offered on `open_lift`, whose texts do not name it; a
    borrowed label that does not exist where it is borrowed from.
    """
    snap = scenarios()[name]
    step = snap["step"]
    if step not in ps.SESSION_REUSED_STEPS:
        return
    texts = step_texts("en")
    labels = set(texts[step].get("menu_options", {}))
    for action in snap["actions"]:
        if action in labels:
            continue
        lender = BORROWED_LABELS.get(action)
        assert lender is not None, f"{step}: {action} has no label"
        assert action in texts[lender].get("menu_options", {}), f"{lender}: {action}"
        assert snap["notice"] is not None, f"{step}: {action} borrowed with no notice"


# ------------------------------------------------------------------- reusing the texts
def test_every_reused_step_has_its_texts_and_every_step_with_texts_is_reused() -> None:
    """The panel shows the dialog's sentences for exactly the steps that have them.

    Every reused step has `options.step.<step>` in `strings.json`, and every step of the
    session that has texts is reused - except the four summaries, which describe closing
    the dialog. A step left out of the list would get new panel texts where seven
    languages of good ones already exist (SPEC decision 12).

    Mutation caught: a reused step with no texts; `summary_basic` reused.
    """
    texts = load(COMPONENT / "strings.json")["options"]["step"]
    assert set(ps.SESSION_REUSED_STEPS) <= set(ps.SESSION_STEPS)
    for step in ps.SESSION_REUSED_STEPS:
        assert step in texts, step
    with_texts = {step for step in ps.SESSION_STEPS if step in texts}
    assert with_texts - set(ps.SESSION_REUSED_STEPS) == {
        "summary_basic",
        "summary_short",
        "summary_correction",
        "summary_precise",
    }


@pytest.mark.parametrize("language", TEXT_LANGUAGES)
def test_no_reused_step_talks_about_the_dialog(language: str) -> None:
    """A sentence shown in the panel may not send the user to a dialog they are not in.

    Verified by hand for SPEC §5.5 in Italian; held here in both maintained languages, so
    that a later edit of a dialog text that mentions "Configure" moves the step out of the
    reused list (and into new panel texts) instead of reaching the panel unnoticed.

    Mutation caught: `refused_already_calibrating` or `summary_*` added to the reused list.
    """
    texts = step_texts(language)
    for step in ps.SESSION_REUSED_STEPS:
        written = json.dumps(texts[step], ensure_ascii=False)
        for word in DIALOG_WORDS:
            assert word not in written, f"{language}: {step} says {word!r}"


@pytest.mark.parametrize("name", SCENARIOS)
def test_every_placeholder_of_a_reused_text_is_in_the_snapshot(name: str) -> None:
    """Every `{…}` the shown sentence substitutes has a value in `placeholders`.

    Checked for the step's own texts when the step is reused, and for the movement's
    progress text when something moves, in English and in Italian: the placeholder names
    are the dialog's, and the snapshot is what has to supply them.

    Mutation caught: `measure_descent` without `expected`; `tape_run` without `percent`;
    `verify_result` without `deviation`.
    """
    snap = scenarios()[name]
    supplied = set(snap["placeholders"])
    for language in TEXT_LANGUAGES:
        if snap["step"] in ps.SESSION_REUSED_STEPS:
            needed = placeholders_in(step_texts(language)[snap["step"]])
            assert needed <= supplied, f"{language}: {snap['step']} needs {needed - supplied}"
        if snap["movement"] is not None:
            needed = placeholders_in(progress_texts(language)[snap["movement"]["progress_action"]])
            assert needed <= supplied, f"{language}: {snap['movement']['progress_action']} needs {needed - supplied}"


# ----------------------------------------------------------------------- the schemas
def test_there_is_one_example_frame_per_command_and_one_schema_per_command() -> None:
    """Ten commands, ten schemas, ten example frames, and the event beside them.

    Mutation caught: a command declared without a schema or without an example.
    """
    frames = fixture()["frames"]
    assert tuple(frames) == ps.WS_SESSION_COMMANDS
    assert tuple(SCHEMAS) == ps.WS_SESSION_COMMANDS
    for command, frame in frames.items():
        assert frame["type"] == command
    assert ps.WS_EVENT_SESSION in ps.WS_EVENT_TYPES
    assert not set(ps.WS_SESSION_COMMANDS) & {*ps.WS_READ_COMMANDS, *ps.WS_WRITE_COMMANDS}


@pytest.mark.parametrize("command", ps.WS_SESSION_COMMANDS, ids=lambda name: name.split("/")[-1])
def test_the_schema_accepts_its_example_and_refuses_a_field_more(command: str) -> None:
    """The example frame goes through the wire schema; the same frame plus one field does not.

    Mutation caught: a schema built with `extra=ALLOW_EXTRA`; a required key the example
    does not carry.
    """
    schema = wire_schema(command)
    frame = {"id": 7, **fixture()["frames"][command]}
    assert schema(dict(frame)) == frame
    with pytest.raises(vol.Invalid):
        schema({**frame, "client_time": "2026-09-18T10:00:00+00:00"})


def bad_frames() -> Iterator[tuple[str, dict[str, Any]]]:
    """Frames the socket must refuse as malformed, each for one reason."""
    frames = load(FIXTURE)["frames"]
    start = frames[ps.WS_TYPE_SESSION_START]
    act = frames[ps.WS_TYPE_SESSION_ACT]
    save = frames[ps.WS_TYPE_SESSION_SAVE]
    yield "client id too short", {**act, "client_id": "tab"}
    yield "client id with a slash", {**act, "client_id": "tab/one/two"}
    yield "negative revision", {**act, "revision": -1}
    yield "revision as a boolean", {**act, "revision": True}
    yield "revision as a string", {**act, "revision": "35"}
    yield "value as a list", {**act, "value": ["96"]}
    yield "value as a boolean", {**act, "value": True}
    yield "no entry", {key: value for key, value in act.items() if key != "entry_id"}
    yield "unknown path", {**start, "path": "path_d"}
    yield "unknown scope", {**start, "scope": "everything"}
    yield "profile without a path", {
        key: value for key, value in start.items() if key not in ("path", "scope")
    }
    yield "profile with path_a", {**start, "path": "path_a", "scope": None}
    yield "scope with path_b", {**start, "path": "path_b"}
    yield "unknown target", {**save, "target": "everywhere"}


@pytest.mark.parametrize(("reason", "frame"), list(bad_frames()), ids=[r for r, _f in bad_frames()])
def test_the_schema_refuses_a_malformed_frame(reason: str, frame: dict[str, Any]) -> None:
    """Each frame is wrong in exactly one way, and each is `invalid_format` on the socket.

    Mutation caught: `client_id` without its pattern; a `revision` that takes `true`; a
    `start` that silently ignores a profile it was given with the wrong path.
    """
    schema = wire_schema(frame["type"])
    with pytest.raises(vol.Invalid):
        schema({"id": 7, **{key: value for key, value in frame.items() if value is not None}})


def test_start_accepts_every_combination_the_panel_sends() -> None:
    """The four ways in (SPEC §6), and a start with nothing but the cover.

    Mutation caught: `_start_combination` refusing `path_b` with its profile, or `path_c`
    with a scope and no profile (the scope is then only an intent).
    """
    schema = wire_schema(ps.WS_TYPE_SESSION_START)
    base = {
        "id": 1,
        "type": ps.WS_TYPE_SESSION_START,
        "entry_id": "01EXAMPLEEXAMPLEEXAMPLEEXA",
        "cover_unique_id": "00:03:50:aa:bb:cc-2-81",
        "client_id": "3b0c7e1a-5d2f-4a8e-9c61-0e7f4b2d9a10",
    }
    for extra in (
        {},
        {"path": "path_a"},
        {"path": "path_b"},
        {"path": "path_b", "profile": "tall"},
        {"path": "path_c"},
        {"path": "path_c", "profile": "tall"},
        {"path": "path_c", "scope": "times_only"},
        {"path": "path_c", "profile": "tall", "scope": "points_only"},
    ):
        assert schema({**base, **extra}) == {**base, **extra}


# ------------------------------------------------------------ the TypeScript restatement
def ts_union(source: str, name: str) -> list[str]:
    match = re.search(rf"export type {name} =([^;]*);", source)
    assert match, name
    return re.findall(r'"([^"]+)"', match.group(1))


def ts_fields(source: str, name: str) -> list[str]:
    match = re.search(rf"export interface {name} \{{\n(.*?)\n\}}", source, re.S)
    assert match, name
    return re.findall(r"^  (\w+)\??:", match.group(1), re.M)


TS_UNIONS: dict[str, tuple[str, ...]] = {
    "SessionState": ps.SESSION_STATES,
    "SessionSubstate": ps.SESSION_SUBSTATES,
    "SessionOutcomeReason": ps.SESSION_OUTCOMES,
    "SessionProblemCode": ps.SESSION_PROBLEMS,
    "SessionPath": ps.SESSION_PATHS,
    "SessionScope": ps.SESSION_SCOPES,
    "SessionLevel": ps.SESSION_LEVELS,
    "SessionSaveTarget": ps.SESSION_SAVE_TARGETS,
    "SessionReviewVariant": ps.SESSION_REVIEW_VARIANTS,
    "SessionPosition": ps.SESSION_POSITIONS,
    "SessionDirection": ps.SESSION_DIRECTIONS,
    "SessionMovementKind": ps.SESSION_MOVEMENT_KINDS,
    "SessionProgressAction": ps.SESSION_PROGRESS_ACTIONS,
    "SessionPressKind": ps.SESSION_PRESS_KINDS,
    "SessionFormField": ps.SESSION_FORM_FIELDS,
    "SessionFormKind": ps.SESSION_FORM_KINDS,
    "SessionFormUnit": ps.SESSION_FORM_UNITS,
    "SessionFormError": ps.SESSION_FORM_ERRORS,
    "SessionNotice": ps.SESSION_NOTICES,
    "SessionHolder": ps.SESSION_HOLDERS,
    "SessionStep": ps.SESSION_STEPS,
    "SessionReusedStep": ps.SESSION_REUSED_STEPS,
    "SessionPlanStage": ps.SESSION_PLAN_STAGES,
    "SessionAction": ps.SESSION_ACTIONS,
    "SessionSubmit": (ps.SESSION_SUBMIT,),
    "SessionReviewRowKey": ps.SESSION_REVIEW_ROW_KEYS,
    "SessionErrorKey": ps.SESSION_ERROR_KEYS,
    "SessionCommandType": ps.WS_SESSION_COMMANDS,
}

TS_INTERFACES: dict[str, tuple[str, ...]] = {
    "SessionSnapshot": ps.SESSION_KEYS,
    "SessionCover": ps.SESSION_COVER_KEYS,
    "SessionIntent": ps.SESSION_INTENT_KEYS,
    "SessionForm": ps.SESSION_FORM_KEYS,
    "SessionMovement": ps.SESSION_MOVEMENT_KEYS,
    "SessionPress": ps.SESSION_PRESS_KEYS,
    "SessionReading": ps.SESSION_READING_KEYS,
    "SessionLift": ps.SESSION_LIFT_KEYS,
    "SessionMeasured": ps.SESSION_MEASURED_KEYS,
    "SessionFit": ps.SESSION_FIT_KEYS,
    "SessionFitDirection": ps.SESSION_FIT_DIRECTION_KEYS,
    "SessionFitPoint": ps.SESSION_FIT_POINT_KEYS,
    "SessionCheck": ps.SESSION_CHECK_KEYS,
    "SessionReview": ps.SESSION_REVIEW_KEYS,
    "SessionReviewRow": ps.SESSION_REVIEW_ROW_FIELDS,
    "SessionReviewMeasuredRow": ps.SESSION_REVIEW_ROW_FIELDS,
    "OverviewSession": ps.SESSION_OVERVIEW_KEYS,
    "SessionReviewAffected": ps.SESSION_REVIEW_AFFECTED_KEYS,
    "SessionProblem": ps.SESSION_PROBLEM_KEYS,
    "SessionOwner": ps.SESSION_OWNER_KEYS,
    "SessionOutcome": ps.SESSION_OUTCOME_KEYS,
    "SessionCapabilities": tuple(ps.SESSION_CAPABILITIES),
    "SessionGetAnswer": ps.SESSION_GET_KEYS,
    "SessionAnswer": ps.SESSION_ANSWER_KEYS,
    "SessionHeartbeatAnswer": ps.SESSION_HEARTBEAT_KEYS,
    "SessionCancelAnswer": ps.SESSION_CANCEL_KEYS,
    "SessionSaveAnswer": ps.SESSION_SAVE_KEYS,
    "SessionEndOtherAnswer": ps.SESSION_END_OTHER_KEYS,
}

TS_REQUESTS: dict[str, str] = {
    "SessionGetRequest": ps.WS_TYPE_SESSION_GET,
    "SessionStartRequest": ps.WS_TYPE_SESSION_START,
    "SessionAttachRequest": ps.WS_TYPE_SESSION_ATTACH,
    "SessionHeartbeatRequest": ps.WS_TYPE_SESSION_HEARTBEAT,
    "SessionActRequest": ps.WS_TYPE_SESSION_ACT,
    "SessionStopRequest": ps.WS_TYPE_SESSION_STOP,
    "SessionLeaveRequest": ps.WS_TYPE_SESSION_LEAVE,
    "SessionCancelRequest": ps.WS_TYPE_SESSION_CANCEL,
    "SessionSaveRequest": ps.WS_TYPE_SESSION_SAVE,
    "SessionEndOtherRequest": ps.WS_TYPE_SESSION_END_OTHER,
}


def schema_keys(command: str) -> list[str]:
    schema = SCHEMAS[command]
    mapping = schema if isinstance(schema, dict) else schema.validators[0].schema
    return [str(marker) for marker in mapping]


def test_the_typescript_types_restate_the_python_tuples() -> None:
    """Every union, every interface and every request of the `.ts` file is the Python one.

    `npm run check` proves the file compiles; it cannot prove the file says what the
    server says. This reads it back: same members, same order, for every vocabulary and
    every object of the snapshot, and the same fields as the schema for every request.

    Mutation caught: a state added in Python and not in TypeScript; a snapshot key renamed
    on one side; an optional request field missing from the interface.
    """
    source = CONTRACT_TS.read_text(encoding="utf-8")
    for name, members in TS_UNIONS.items():
        assert ts_union(source, name) == list(members), name
    assert ts_union(source, "SessionValueKey") == ["stop_latency_s", "start_delay_s"]
    assert list(ps.SESSION_VALUE_KEYS[len(ps.SESSION_REVIEW_ROW_KEYS) :]) == [
        "stop_latency_s",
        "start_delay_s",
    ]
    for name, keys in TS_INTERFACES.items():
        assert ts_fields(source, name) == list(keys), name
    for name, command in TS_REQUESTS.items():
        assert ts_fields(source, name) == schema_keys(command), name


def test_the_typescript_contract_has_no_executable_code() -> None:
    """Types only (PLAN L0, criterion 2): nothing a bundle would carry, nothing to drift.

    Mutation caught: a `const` list of steps "for convenience", which would be a second
    copy of `SESSION_STEPS` the Python test above does not read.
    """
    source = CONTRACT_TS.read_text(encoding="utf-8")
    code = re.sub(r"//.*|/\*.*?\*/", "", source, flags=re.S)
    for word in ("const ", "let ", "var ", "function ", "class ", "enum ", "import "):
        assert word not in code, word


# ------------------------------------------------------------------------ the document
def test_the_api_document_names_every_command_error_and_state() -> None:
    """§11-§14 exist, are in the index, and mention every name the contract declares.

    Not a proof that the prose is right - that is the review's job - but a name that the
    document never mentions is a name somebody will have to guess the meaning of.

    Mutation caught: a command added to the tuples and not documented; the index left
    without the new sections.
    """
    doc = API_DOC.read_text(encoding="utf-8")
    for number in (11, 12, 13, 14):
        assert re.search(rf"^## {number}\. ", doc, re.M), number
        assert f"- [{number}. " in doc, number
    for name in (
        *ps.WS_SESSION_COMMANDS,
        *ps.SESSION_ERROR_KEYS,
        *ps.SESSION_STATES,
        *ps.SESSION_SUBSTATES,
        *ps.SESSION_OUTCOMES,
        *ps.SESSION_PROBLEMS,
        *ps.SESSION_NOTICES,
        *ps.SESSION_HOLDERS,
        *ps.SESSION_OVERVIEW_KEYS,
        ps.WS_EVENT_SESSION,
    ):
        assert f"`{name}`" in doc or f'"{name}"' in doc, name
