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
    HOMING_ACTION,
    NO_PROFILE,
    PROBLEM_REASONS,
    RUNNING_ACTION,
)
from custom_components.myhome.config_flow import TUNABLE_OPTIONS, MyHomeOptionsFlowHandler
from custom_components.myhome.const import (
    CONF_DEFAULT_KEEPALIVE_MINUTES,
    CONF_SENSOR_DEFAULTS,
    CONF_WORKER_COUNT,
    MAX_COMMAND_WORKERS,
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
    assert {path.stem for path in TRANSLATIONS} == {"de", "en", "es", "fr", "it", "nl", "pt"}


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
        step = load(path)["options"]["step"]["gateway"]
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
        description = load(path)["options"]["step"]["gateway"]["data_description"][
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


# ------------------------------------------------------------------- the options flow
# 0.5.0 v2 put the guided calibration and the management of what it stores inside the
# options flow, so every screen of both is a step id, a menu option, a progress action,
# an error key or a selector option that has to exist in seven files. The tests below
# pin the two halves to each other: a step the code can show and nobody wrote a text
# for renders as a raw key, and a text nobody can reach is a translation seven people
# maintain for nothing.
FLOW = MyHomeOptionsFlowHandler

# What each screen is given to substitute into its text. Anything else in a `{...}`
# renders as braces to the user, and a placeholder the code passes and no text uses is
# merely unused - so this is the upper bound, not the exact set.
STEP_PLACEHOLDERS: dict[str, set[str]] = {
    "init": {"gateway"},
    "gateway": set(),
    # management
    "profiles_covers": {"profiles", "covers"},
    "assign_covers": {"covers"},
    "assign_heights": {"covers"},
    "pick_profile": set(),
    "profile_actions": {"profile", "covers", "values", "count"},
    "profile_view": {"profile", "covers", "values", "count"},
    "profile_edit": {"profile", "covers", "values", "count"},
    "profile_delete": {"profile", "covers", "values", "count"},
    "profile_deleted": {"profile", "covers", "count"},
    "calibrations": {"count"},
    "no_calibrations": set(),
    "no_basic_covers": set(),
    "calibration_actions": {"cover", "values", "profile", "measured_at"},
    "calibration_view": {"cover", "values", "profile", "measured_at"},
    "calibration_edit": {"cover", "values", "profile", "measured_at"},
    "calibration_delete": {"cover", "values", "profile", "measured_at"},
    "calibration_deleted": {"cover"},
    # the guided flow
    "calibrate": set(),
    "cover": set(),
    "path": {"cover"},
    "path_a": {"cover"},
    "path_b": {"cover"},
    "path_c": {"cover"},
    "refine_scope": {"cover"},
    "home_closed_done": {"cover"},
    "home_open_done": {"cover"},
    "open_brief": {"cover"},
    "open_lift": {"cover"},
    "open_top": {"cover"},
    "open_result": {"cover", "slat", "run"},
    "close_brief": {"cover"},
    "close_bottom": {"cover"},
    "close_result": {"cover", "run"},
    "height": {"cover"},
    "height_result": {"cover", "height"},
    "measure_descent": {"cover", "percent", "direction", "expected", "tolerance"},
    "measure_ascent": {"cover", "percent", "direction", "expected", "tolerance"},
    "measure_verify": {"cover", "percent", "direction", "expected", "tolerance"},
    "tape_result": {"cover", "percent", "measured"},
    "verify_offer": {"cover"},
    "verify_result": {"cover", "deviation"},
    "profile_name": {"cover", "replaced"},
    "summary_basic": {"cover", "yaml", "height", "accuracy", "percent", "profile"},
    "summary_precise": {"cover", "yaml", "height", "accuracy", "percent", "profile"},
    "saved": {"cover", "profile"},
    "cancelled": set(),
    "expired": {"cover"},
    "refused_unknown_cover": set(),
    "refused_already_calibrating": set(),
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


def options_block(path: Path) -> dict[str, Any]:
    return load(path)["options"]


def test_every_written_step_is_one_the_flow_can_show() -> None:
    """A step id in the strings with no ``async_step_`` behind it is a dead text.

    Mutation caught: renaming a step in the code and leaving seven translations behind
    (or the reverse, which the next test catches).
    """
    for step in options_block(STRINGS)["step"]:
        assert hasattr(FLOW, f"async_step_{step}"), step


def test_every_menu_option_is_a_step_and_is_labelled() -> None:
    """Home Assistant routes a menu choice straight to ``async_step_<option>``.

    An option with no method raises ``UnknownStep`` inside the dialog; one with no label
    is shown to the user as its own key.

    Mutation caught: offering an option the flow does not implement (which no happy
    path would reach, because the happy path never clicks it).
    """
    for step_id, step in options_block(STRINGS)["step"].items():
        for option in step.get("menu_options", {}):
            assert hasattr(FLOW, f"async_step_{option}"), f"{step_id} -> {option}"


def test_every_screen_the_flow_can_show_is_written_down() -> None:
    """The other direction: a ``step_id=`` in the code with no text renders as a key.

    The step ids are read out of the source rather than off the class, because a
    ``async_step_`` method is not necessarily a screen - half of them route.

    Mutation caught: a new screen with no text in any of the seven files.
    """
    source = (COMPONENT / "calibration_flow.py").read_text(encoding="utf-8")
    source += (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
    shown = set(re.findall(r'step_id="([a-z_]+)"', source))
    # The press menus and the tape forms name their step in a positional argument.
    shown |= {"open_lift", "open_top", "close_bottom"}
    shown |= {"measure_descent", "measure_ascent", "measure_verify"}
    shown |= {f"problem_{reason}" for reason in PROBLEM_REASONS}
    shown |= {"refused_unknown_cover", "refused_already_calibrating"}
    # ...and the config flow's own steps, which live under `config`, not `options`.
    shown -= {"user", "custom", "port", "password", "reauth_confirm", "ssdp_confirm"}
    # A progress screen has a `progress` text and no step text.
    shown -= set(PROGRESS_PLACEHOLDERS) | {
        "home_closed",
        "home_open",
        "open_timed",
        "open_start",
        "close_timed",
        "close_start",
        "half_down",
        "half_up",
        "quarter_down",
        "quarter_up",
        "three_quarter_down",
        "three_quarter_up",
        "verify",
        "verify_b",
    }
    written = set(options_block(STRINGS)["step"])
    assert shown == written


def test_every_failure_of_the_engine_has_a_screen_of_its_own() -> None:
    """One screen per reason, because each one needs something different done about it.

    ``PROBLEM_REASONS`` is what the flow maps an engine failure onto; the steps named
    ``problem_*`` are what it shows. A reason with no screen would raise ``UnknownStep``
    at the worst possible moment - just after a shutter misbehaved.

    Mutation caught: adding a reason to the engine and to ``PROBLEM_REASONS`` without
    writing the screen that explains it.
    """
    steps = options_block(STRINGS)["step"]
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
    written = set(options_block(STRINGS)["progress"])
    assert used == written


def test_every_form_error_the_flow_sets_is_written_down() -> None:
    """Every way a form of this dialog can be answered wrongly, and its sentence."""
    source = (COMPONENT / "calibration_flow.py").read_text(encoding="utf-8")
    # `config_flow.py` also carries the config flow's own errors, which live under
    # `config.error`; only the ones the *options* flow sets belong here.
    source += "\n".join(
        line
        for line in (COMPONENT / "config_flow.py").read_text(encoding="utf-8").splitlines()
        if "invalid_host" in line or "invalid_config_path" in line
    )
    used = set(re.findall(r'errors\[[A-Za-z_]+\] = "([a-z_]+)"', source))
    used |= set(re.findall(r'ERROR_[A-Z_]+ = "([a-z_]+)"', source))
    written = set(options_block(STRINGS)["error"])
    assert used == written


def test_the_no_profile_option_of_the_assignment_form_is_translated() -> None:
    """The one select option that is a sentence rather than a name the user gave.

    Its value is `NO_PROFILE`, and Home Assistant looks its label up under
    ``selector.profile_choice.options``. Without the text the user is offered a
    dropdown whose first entry reads ``__none__``.
    """
    for path in [STRINGS, *TRANSLATIONS]:
        options = load(path)["selector"]["profile_choice"]["options"]
        assert set(options) == {NO_PROFILE}, path.name
        assert options[NO_PROFILE], path.name


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_no_screen_substitutes_something_the_flow_does_not_pass(path: Path) -> None:
    """A ``{placeholder}`` the step is never given renders as braces to the user.

    The parity test above only checks that the seven files agree with each other, so a
    placeholder invented in ``strings.json`` and faithfully copied into the other six
    would pass it. This one checks them against the code.

    Mutation caught: writing ``{cover}`` into the two screens that run before a cover
    has been chosen, or ``{percent}`` into a screen that is not about a fraction.
    """
    block = options_block(path)
    for step_id, step in block["step"].items():
        allowed = STEP_PLACEHOLDERS[step_id]
        for text in flatten(step).values():
            assert set(PLACEHOLDER.findall(text)) <= allowed, f"{path.name}: {step_id}"
    for action, text in block["progress"].items():
        assert set(PLACEHOLDER.findall(text)) <= PROGRESS_PLACEHOLDERS[action], action


# ------------------------------------------------------------------- the drawings
# Three moments of the guided calibration are hard to put into words and easy to draw:
# where the tape goes, which instant "it leaves its rest" means, and which one "it
# stops at the top" means. A config-flow description is rendered as Markdown, so each
# of those screens opens with an image served from `/myhome_static` (registered once in
# `__init__.async_setup`, out of `custom_components/myhome/images`).
STEP_IMAGES: dict[str, str] = {
    "height": "height.webp",
    "open_brief": "lift_off.webp",
    "open_lift": "lift_off.webp",
    "open_top": "top_stop.webp",
    "measure_descent": "reading.webp",
    "measure_ascent": "reading.webp",
    "measure_verify": "reading.webp",
}


def test_the_drawings_are_shipped_with_the_integration() -> None:
    """A Markdown image pointing at a file that is not in the package renders broken."""
    images = COMPONENT / "images"
    assert {path.name for path in images.glob("*.webp")} == set(STEP_IMAGES.values())


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_each_illustrated_screen_opens_with_its_drawing(path: Path) -> None:
    """The image comes first, then the text, in all seven languages.

    Mutation caught: adding a screen to `STEP_IMAGES` and illustrating it in Italian
    only, or renaming a file under `images/` and leaving the eight files pointing at
    the old name.
    """
    steps = options_block(path)["step"]
    for step_id, image in STEP_IMAGES.items():
        description = steps[step_id]["description"]
        assert description.startswith(f"![](/myhome_static/{image})\n\n"), f"{path.name}: {step_id}"


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_no_other_screen_points_at_the_static_path(path: Path) -> None:
    """Every `/myhome_static/` reference is one of the drawings above.

    Mutation caught: a screen left pointing at a file the merge never brought in.
    """
    for key, text in flatten(load(path)).items():
        if "/myhome_static/" not in text:
            continue
        step_id = key.split(".")[2]
        assert key == f"options.step.{step_id}.description", key
        assert text.count("/myhome_static/") == 1, key
        assert f"/myhome_static/{STEP_IMAGES[step_id]}" in text, key
