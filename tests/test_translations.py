"""Structural tests for ``strings.json`` and the four ``translations/*.json``.

``strings.json`` is the canonical file for a config-flow integration (it is what
hassfest-style structure checks read, and what a translation pipeline generates
``translations/en.json`` from); the locale files must stay a key-for-key translation
of it.  A key that exists in one file only is either an untranslated string the user
sees in English or, more often, a leftover nobody removed -- the eight dead
``invalid_port`` entries were exactly that.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from custom_components.myhome.calibration_flow import (
    CLAIM_REASONS,
    HOMING_ACTION,
    PROBLEM_REASONS,
    RUNNING_ACTION,
    CoverCalibrationFlow,
    CoverProfileFlow,
)
from custom_components.myhome.config_flow import TUNABLE_OPTIONS
from custom_components.myhome.const import (
    CONF_DEFAULT_KEEPALIVE_MINUTES,
    CONF_SENSOR_DEFAULTS,
    CONF_WORKER_COUNT,
    MAX_COMMAND_WORKERS,
    SUBENTRY_COVER_CALIBRATION,
    SUBENTRY_COVER_PROFILE,
)
from custom_components.myhome.device_trigger import ALL_SUBTYPES, ALL_TRIGGER_TYPES
from custom_components.myhome.validate import CONF_ENERGY_DEFAULTS

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "myhome"
STRINGS = COMPONENT / "strings.json"
TRANSLATIONS = sorted((COMPONENT / "translations").glob("*.json"))


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def leaf_keys(data: Any, prefix: str = "") -> set[str]:
    """Every dotted path of the JSON tree that ends on a string."""
    return set(flatten(data, prefix))


def flatten(data: Any, prefix: str = "") -> dict[str, Any]:
    """The JSON tree as ``{dotted path: leaf value}``."""
    if not isinstance(data, dict):
        return {prefix: data}
    flat: dict[str, Any] = {}
    for key, value in data.items():
        flat |= flatten(value, f"{prefix}.{key}" if prefix else key)
    return flat


# Home Assistant substitutes ``{name}``-style placeholders; a locale that drops one
# loses the only piece of information the string carries, and one that invents a
# placeholder renders the braces verbatim to the user.
PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def test_the_translation_files_are_found() -> None:
    """A glob that silently matches nothing would make every test below vacuous."""
    assert STRINGS.is_file()
    assert {path.stem for path in TRANSLATIONS} == {"en", "fr", "it", "nl"}


@pytest.mark.parametrize("path", TRANSLATIONS, ids=lambda path: path.stem)
def test_each_locale_has_the_same_keys_as_strings_json(path: Path) -> None:
    """Same key set, no more and no less."""
    expected = leaf_keys(load(STRINGS))
    actual = leaf_keys(load(path))
    assert actual - expected == set(), f"{path.name} has keys strings.json does not"
    assert expected - actual == set(), f"{path.name} is missing keys of strings.json"


@pytest.mark.parametrize("path", TRANSLATIONS, ids=lambda path: path.stem)
def test_each_locale_uses_the_same_placeholders_as_strings_json(path: Path) -> None:
    """Same key set is not enough: the ``{...}`` substitutions must match too.

    A locale that drops ``{path}`` from ``issues.yaml_invalid.description`` keeps the
    same key set and the suite stays green, while the user is told their
    configuration is invalid without being told which file; one that invents a
    placeholder shows the braces verbatim.
    """
    expected = flatten(load(STRINGS))
    actual = flatten(load(path))
    for key, text in expected.items():
        assert isinstance(text, str), key
        assert set(PLACEHOLDER.findall(actual[key])) == set(PLACEHOLDER.findall(text)), key


def test_every_options_tunable_documents_its_range() -> None:
    """Every option with a label has a ``data_description``, naming its REAL range.

    The ranges live in ``config_flow.TUNABLE_OPTIONS`` (and MAX_COMMAND_WORKERS for
    the worker count) and are repeated as prose in five files.  Checking only that a
    description exists, or only the worker count's number, leaves the other five
    sentences free to go stale in all five languages with the suite green -- and the
    worker count's own range is the one the runtime clamps to, so a user who reads
    "1-10" and saves 8 gets 4.

    Mutation caught: changing a bound in ``TUNABLE_OPTIONS`` without rewriting the
    five sentences that quote it.
    """
    for path in [STRINGS, *TRANSLATIONS]:
        step = load(path)["options"]["step"]["init"]
        assert set(step["data_description"]) == set(step["data"]) - {
            "address",
            "port",
            "password",
            "config_file_path",
            "generate_events",
        }, path.name
        assert f"1-{MAX_COMMAND_WORKERS}" in step["data_description"][CONF_WORKER_COUNT], path.name
        for key, _default, minimum, maximum, _unit in TUNABLE_OPTIONS:
            assert f"({minimum}-{maximum})" in step["data_description"][key], f"{path.name}: {key}"


def test_the_keepalive_option_names_both_blocks_that_beat_it() -> None:
    """P6-INCONSISTENCY-2: ``energy:`` is an alias of ``sensor_defaults:`` and blocks it too.

    ``_merge_sensor_defaults`` reads both block names and records both in ``from_file``,
    so a ``keepalive_minutes`` written under the legacy ``energy:`` spelling is *not*
    marked as defaulted and the option cannot replace it - exactly like one written under
    ``sensor_defaults:``.  The description was rewritten in round 5 precisely so the
    option would stop looking as if it did nothing, and it named only one of the two
    blocks: the user with the older spelling is the one most likely to read it.

    Mutation caught: dropping the alias from the sentence in any of the five files.
    """
    for path in [STRINGS, *TRANSLATIONS]:
        description = load(path)["options"]["step"]["init"]["data_description"][
            CONF_DEFAULT_KEEPALIVE_MINUTES
        ]
        # The trailing colon is what makes these YAML keys rather than ordinary words:
        # "energy" alone is in the English sentence anyway ("the energy meters").
        assert f"{CONF_SENSOR_DEFAULTS}:" in description, path.name
        assert f"{CONF_ENERGY_DEFAULTS}:" in description, path.name


def test_the_device_automation_translations_cover_every_trigger() -> None:
    """The automation editor labels each trigger from these two tables.

    Why it matters in production: ``ALL_SUBTYPES`` is *computed* from
    ``SCENARIO_CONTROL_BUTTON_RANGE`` and ``ALL_TRIGGER_TYPES`` from
    ``SCENARIO_CONTROL_EVENT_TYPES``, so widening either constant silently produces
    triggers the editor shows by their raw key.  Nothing pinned the two together.

    Mutation caught: adding a protocol event or widening a button range without
    adding the ``device_automation`` strings for it (and the reverse: a leftover
    subtype no protocol can address).
    """
    device_automation = load(STRINGS)["device_automation"]
    assert set(device_automation["trigger_subtype"]) == set(ALL_SUBTYPES)
    assert set(device_automation["trigger_type"]) == set(ALL_TRIGGER_TYPES)


def test_strings_json_and_the_english_translation_are_identical() -> None:
    """``translations/en.json`` is the generated copy of the canonical file."""
    assert load(STRINGS) == load(COMPONENT / "translations" / "en.json")


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_no_dead_error_keys(path: Path) -> None:
    """``invalid_port`` was in all four locales and assigned nowhere.

    Port validation happens inside the voluptuous schema (``PORT_VALIDATOR``), whose
    failure Home Assistant renders with its own message, so nothing ever sets
    ``errors[CONF_PORT] = "invalid_port"``.  Keeping the key suggested a code path
    that does not exist.
    """
    assert [key for key in leaf_keys(load(path)) if key.endswith(".invalid_port")] == []


# --------------------------------------------------------------- config_subentries
# The guided calibration of 0.5.0 is two config subentry flows, and every screen of it
# is a step id, a menu option, a progress action, an error key or an abort reason that
# has to exist in five files. The tests below pin the two halves to each other: a step
# the code can show and nobody wrote a text for renders as a raw key, and a text nobody
# can reach is a translation five people maintain for nothing.
SUBENTRY_FLOWS = {
    SUBENTRY_COVER_CALIBRATION: CoverCalibrationFlow,
    SUBENTRY_COVER_PROFILE: CoverProfileFlow,
}

# What each screen is given to substitute into its text. Anything else in a `{...}`
# renders as braces to the user, and a placeholder the code passes and no text uses is
# merely unused - so this is the upper bound, not the exact set.
STEP_PLACEHOLDERS: dict[str, set[str]] = {
    "user": set(),
    "cover": set(),
    "reconfigure": {"cover", "profile", "values"},
    "path": {"cover"},
    "path_a": {"cover"},
    "path_b": {"cover"},
    "path_c": {"cover"},
    "refine_scope": {"cover"},
    "home_closed_done": {"cover"},
    "home_open_done": {"cover"},
    "open_lift": {"cover"},
    "open_top": {"cover"},
    "close_bottom": {"cover"},
    "height": {"cover"},
    "measure_descent": {"cover", "percent", "direction"},
    "measure_ascent": {"cover", "percent", "direction"},
    "measure_verify": {"cover", "percent", "direction"},
    "verify_offer": {"cover"},
    "verify_result": {"cover", "deviation"},
    "summary": {"cover", "yaml", "accuracy", "height"},
    "profile_name": {"cover"},
    # Every `problem_*` screen, which are generated from `PROBLEM_REASONS`.
    **{f"problem_{reason}": {"cover"} for reason in PROBLEM_REASONS},
}
PROGRESS_PLACEHOLDERS: dict[str, set[str]] = {
    "homing_closed": {"cover"},
    "homing_open": {"cover"},
    "starting_open": {"cover"},
    "starting_close": {"cover"},
    "running_down": {"cover", "percent"},
    "running_up": {"cover", "percent"},
}


def subentry_block(path: Path, subentry_type: str) -> dict[str, Any]:
    return load(path)["config_subentries"][subentry_type]


@pytest.mark.parametrize("subentry_type", sorted(SUBENTRY_FLOWS))
def test_every_subentry_type_declares_the_structure_hassfest_expects(subentry_type: str) -> None:
    """`entry_type` and `initiate_flow` name the rows and buttons of the integration page.

    Without them the page shows the raw subentry type as the name of the thing the user
    is about to add, in every language.

    Mutation caught: adding a subentry type to ``async_get_supported_subentry_types``
    and only writing its steps.
    """
    for path in [STRINGS, *TRANSLATIONS]:
        block = subentry_block(path, subentry_type)
        assert block["entry_type"], path.name
        assert block["initiate_flow"]["user"], path.name
        assert block["initiate_flow"]["reconfigure"], path.name


@pytest.mark.parametrize("subentry_type", sorted(SUBENTRY_FLOWS))
def test_every_written_step_is_one_the_flow_can_show(subentry_type: str) -> None:
    """A step id in the strings with no ``async_step_`` behind it is a dead text.

    Mutation caught: renaming a step in the code and leaving five translations behind
    (or the reverse, which the next test catches).
    """
    flow = SUBENTRY_FLOWS[subentry_type]
    for step in subentry_block(STRINGS, subentry_type)["step"]:
        assert hasattr(flow, f"async_step_{step}"), step


@pytest.mark.parametrize("subentry_type", sorted(SUBENTRY_FLOWS))
def test_every_menu_option_is_a_step_and_is_labelled(subentry_type: str) -> None:
    """Home Assistant routes a menu choice straight to ``async_step_<option>``.

    An option with no method raises ``UnknownStep`` inside the dialog; one with no label
    is shown to the user as its own key.

    Mutation caught: offering an option the flow does not implement (which no happy
    path would reach, because the happy path never clicks it).
    """
    flow = SUBENTRY_FLOWS[subentry_type]
    steps = subentry_block(STRINGS, subentry_type)["step"]
    for step_id, step in steps.items():
        for option in step.get("menu_options", {}):
            assert hasattr(flow, f"async_step_{option}"), f"{step_id} -> {option}"


def test_every_failure_of_the_engine_has_a_screen_of_its_own() -> None:
    """One screen per reason, because each one needs something different done about it.

    ``PROBLEM_REASONS`` is what the flow maps an engine failure onto; the steps named
    ``problem_*`` are what it shows. A reason with no screen would raise ``UnknownStep``
    at the worst possible moment - just after a shutter misbehaved.

    Mutation caught: adding a reason to the engine and to ``PROBLEM_REASONS`` without
    writing the screen that explains it.
    """
    steps = subentry_block(STRINGS, SUBENTRY_COVER_CALIBRATION)["step"]
    written = {step for step in steps if step.startswith("problem_")}
    assert written == {f"problem_{reason}" for reason in PROBLEM_REASONS}
    for step in written:
        assert set(steps[step]["menu_options"]) == {"repeat_step", "cancel_flow"}, step


def test_every_progress_action_the_flow_uses_is_written_down() -> None:
    """A progress screen shows ``progress.<action>``, and nothing else.

    It is the only kind of screen with no step text at all, so a missing action leaves
    the user watching a spinner with no idea what is moving.

    Mutation caught: a new automatic movement with a new action name (or a renamed one).
    """
    source = (COMPONENT / "calibration_flow.py").read_text(encoding="utf-8")
    used = (
        set(re.findall(r'action="([a-z_]+)"', source))
        | set(RUNNING_ACTION.values())
        | set(HOMING_ACTION.values())
    )
    written = set(subentry_block(STRINGS, SUBENTRY_COVER_CALIBRATION)["progress"])
    assert used == written


def test_every_abort_reason_the_flow_uses_is_written_down() -> None:
    """An abort with no text closes the dialog on a raw key.

    Mutation caught: a new ``async_abort(reason=...)`` with nothing written for it, and
    a reason kept in the files after the branch that raised it was deleted.

    ``CLAIM_REASONS`` is here because ``_claim`` answers *with* a reason rather than
    aborting itself, so those two never appear at a ``reason="..."``.
    """
    source = (COMPONENT / "calibration_flow.py").read_text(encoding="utf-8")
    used = set(re.findall(r'reason="([a-z_]+)"', source)) | set(CLAIM_REASONS)
    written = set()
    for subentry_type in SUBENTRY_FLOWS:
        written |= set(subentry_block(STRINGS, subentry_type)["abort"])
    assert used == written


def test_every_form_error_the_flow_sets_is_written_down() -> None:
    """The three ways a form can be answered wrongly, and their sentences."""
    source = (COMPONENT / "calibration_flow.py").read_text(encoding="utf-8")
    used = set(re.findall(r'errors=\{[^}]*: "([a-z_]+)"', source))
    used |= set(re.findall(r'errors\[[A-Z_a-z]+\] = "([a-z_]+)"', source))
    written = set(subentry_block(STRINGS, SUBENTRY_COVER_CALIBRATION)["error"])
    assert used == written


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_no_screen_substitutes_something_the_flow_does_not_pass(path: Path) -> None:
    """A ``{placeholder}`` the step is never given renders as braces to the user.

    The parity test above only checks that the five files agree with each other, so a
    placeholder invented in ``strings.json`` and faithfully copied into the other four
    would pass it. This one checks them against the code.

    Mutation caught: writing ``{cover}`` into the two screens that run before a cover
    has been chosen, or ``{percent}`` into a screen that is not about a fraction.
    """
    for subentry_type in SUBENTRY_FLOWS:
        block = subentry_block(path, subentry_type)
        for step_id, step in block["step"].items():
            allowed = STEP_PLACEHOLDERS[step_id]
            for text in flatten(step).values():
                assert set(PLACEHOLDER.findall(text)) <= allowed, f"{path.name}: {step_id}"
        for action, text in block.get("progress", {}).items():
            assert set(PLACEHOLDER.findall(text)) <= PROGRESS_PLACEHOLDERS[action], action
        for reason, text in block["abort"].items():
            assert set(PLACEHOLDER.findall(text)) <= {"cover"}, reason
