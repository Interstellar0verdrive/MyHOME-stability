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
    # `replacing` / `keeping` are the two lists of keys the save is about to write over
    # and to leave exactly as they are (final review, BUG-A): every summary is given
    # them, and the short one - the only summary reached on a window something may
    # already be stored for - says them out loud.
    "summary_basic": {
        "cover", "yaml", "height", "accuracy", "percent", "profile", "replacing", "keeping",
    },
    "summary_short": {
        "cover", "yaml", "height", "accuracy", "percent", "profile", "replacing", "keeping",
    },
    "summary_precise": {
        "cover", "yaml", "height", "accuracy", "percent", "profile", "replacing", "keeping",
    },
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
    dropdown whose first entry reads ``no_profile``.
    """
    for path in [STRINGS, *TRANSLATIONS]:
        options = load(path)["selector"]["profile_choice"]["options"]
        assert set(options) == {NO_PROFILE}, path.name
        assert options[NO_PROFILE], path.name


# hassfest's rule for a translation key: lowercase letters, digits, hyphen and
# underscore, and neither a hyphen nor an underscore at either end.
TRANSLATION_KEY_RE = re.compile(r"^(?![-_])(?!.*[-_]$)[a-z0-9_-]+$")


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_every_selector_option_key_is_a_valid_translation_key(path: Path) -> None:
    """hassfest refuses the whole file over one option key that is not a slug.

    The assignment select's "no profile" sentinel used to be spelled `__none__`, which
    reads as "not a name anybody would give a profile" and is exactly what hassfest
    rejects - it failed "Validate with hassfest" on every push until it was renamed.

    Mutation caught: spelling any sentinel with a leading or trailing underscore again.
    """
    for key, selector in load(path)["selector"].items():
        assert TRANSLATION_KEY_RE.match(key), f"{path.name}: selector.{key}"
        for option in selector.get("options", {}):
            assert TRANSLATION_KEY_RE.match(option), f"{path.name}: selector.{key}.{option}"


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


# Every menu option that goes *back* rather than on: the screens they belong to list
# them last, because Home Assistant renders every menu entry with the same chevron and
# there is nothing else to tell an action from a way out (FLOW, second live walk-through).
RETURN_OPTIONS = frozenset(
    {
        "init",
        "finish",
        "cancel_flow",
        "profiles_covers",
        "calibrations",
        "profile_actions",
        "calibration_actions",
    }
)


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_no_menu_title_asks_for_a_substitution(path: Path) -> None:
    """A menu's header is rendered without `description_placeholders`, so it cannot.

    The frontend passes the placeholders to a menu's *description* and not to its
    title (`renderMenuDescription` against `renderMenuHeader`), and formatjs answers a
    substitution it was not given by replacing the whole string with "Translation
    [formatjs Error: MISSING_VALUE] The intl string context variable ...". The second
    live walk-through read exactly that on the first screen of "Configura", whose
    title said `{gateway}`. What those titles carried now lives in the descriptions,
    which do get them.

    Mutation caught: putting `{cover}` back into the title of any screen that is a
    menu.
    """
    for step_id, step in options_block(path)["step"].items():
        if "menu_options" not in step:
            continue
        assert not PLACEHOLDER.findall(step.get("title", "")), f"{path.name}: {step_id}"


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_only_the_summary_that_offers_the_refinement_describes_it(path: Path) -> None:
    """Two summaries at the basic level, because only path A can do better.

    The unconditional text used to promise "Migliora la precisione" to paths B and C,
    which have no such button - the one thing the live feedback asked for by name
    (0.5.0 v2 review, BUG-5).

    Mutation caught: describing the refinement on the short summary, or offering it
    there.
    """
    steps = options_block(path)["step"]
    assert set(steps["summary_basic"]["menu_options"]) == {"save", "refine", "cancel_flow"}
    assert set(steps["summary_short"]["menu_options"]) == {"save", "cancel_flow"}
    assert set(steps["summary_precise"]["menu_options"]) == {"save", "cancel_flow"}
    # The name of the button, as it appears in the text of the screen that has it.
    refine = steps["summary_basic"]["menu_options"]["refine"].split("(")[0].strip()
    assert refine in steps["summary_basic"]["description"], path.name
    assert refine not in steps["summary_short"]["description"], path.name
    assert refine not in steps["summary_precise"]["description"], path.name


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_no_menu_option_draws_an_arrow_of_its_own(path: Path) -> None:
    """Home Assistant gives every menu entry the same chevron, and only that one.

    An "← Torna al menu" was considered and refused: the arrow in the label would sit
    next to a chevron pointing the other way. The way back is told from the way on by
    being last, which `test_calibration_flow.check_the_screen_renders` pins against
    every menu the dialog really shows.
    """
    for step_id, step in options_block(path)["step"].items():
        for option, label in (step.get("menu_options") or {}).items():
            assert not re.search(r"[\u2190\u2192\u21e6\u21e8]|<-|->", label), (
                f"{path.name}: {step_id} -> {option}"
            )


# ------------------------------------------------------------------- the drawings
# Three moments of the guided calibration are hard to put into words and easy to draw:
# where the tape goes, which instant "it leaves its rest" means, and which one "it
# stops at the top" means. A config-flow description is rendered as Markdown, so each
# of those screens opens with an image served from `/myhome_static` (registered once in
# `__init__.async_setup`, out of `custom_components/myhome/images`).
STEP_IMAGES: dict[str, str] = {
    "height": "height.webp",
    "open_brief": "ascent_presses.webp",
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


# --------------------------------------------------------------- the words themselves
# The Italian is the original every other file is translated from, and the owner read it
# out loud twice in front of a real shutter.  These are the four things he asked for by
# name, each of which survived one rewrite before it was caught.
FORBIDDEN_ITALIAN: dict[str, str] = {
    "finestr": (
        'a window is not a shutter, and the dialog is not a window either: "tapparella" '
        'for the thing that moves, "vano" for the hole in the wall, "dialogo" for this box'
    ),
    "così che": 'dialectal with a subjunctive: "in questo modo ..." with an indicative',
    "cosi' che": "the same, unaccented",
    "fino in fondo": '"completamente", in both directions, because a shutter opens upwards',
    " lei ": "a shutter is a thing: no personal pronoun stands for it",
    " lui ": "the same",
    " lui:": "the same, before a colon",
    " lei:": "the same, before a colon",
}


# One "finestra" is a window of time and not a hole in a wall: the label of the probe
# window, in the connection form, which has nothing to do with shutters.
EXEMPT_FROM_THE_ITALIAN_RULES = {"options.step.gateway.data.probe_window_sec"}


def test_the_italian_says_none_of_the_words_the_live_test_struck_out() -> None:
    """Four rules, read off the owner's two walk-throughs (FLOW, "Feedback ...").

    They are checked on the Italian alone because the Italian is the one that was read
    out loud: the other six are translations of it, and the words the rules are about
    ("finestra" against "tapparella") are a distinction the other languages draw with
    different words anyway.

    Mutation caught: any of the four creeping back into any Italian string - the ones
    the flow shows, the service descriptions, the entity names.
    """
    italian = COMPONENT / "translations" / "it.json"
    offences = [
        (key, word)
        for key, text in flatten(load(italian)).items()
        if key not in EXEMPT_FROM_THE_ITALIAN_RULES
        for word in FORBIDDEN_ITALIAN
        if word in text.lower()
    ]
    assert not offences, "\n".join(
        f"{key}: {word!r} - {FORBIDDEN_ITALIAN[word]}" for key, word in offences
    )


# The screens a shutter is moving through while they are on the screen. "Nobody reads
# while watching the shutter": everything they would have said belongs to the briefing
# before the "Avvia" button, and what is left is one line and a button.
DURING_THE_MOVEMENT = {"open_lift": "open_brief", "open_top": "open_brief", "close_bottom": "close_brief"}


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_the_moving_screens_say_one_thing_and_the_briefing_says_the_rest(path: Path) -> None:
    """The timed steps put every instruction on the screen *before* "Avvia".

    A press that is half a second late moves the estimate by centimetres, and the
    second live walk-through lost both presses of the ascent to a screen that was still
    explaining itself while the shutter ran.

    Mutation caught: moving an instruction back into a screen shown during a movement,
    in any of the eight files.
    """
    steps = options_block(path)["step"]
    for moving, briefing in DURING_THE_MOVEMENT.items():
        lines = [
            line
            for line in steps[moving]["description"].splitlines()
            if line.strip() and not line.startswith("![](")
        ]
        # The cover's name (a menu title cannot carry it) and one instruction.
        assert len(lines) == 2, f"{path.name}: {moving}: {lines}"
        assert len(steps[briefing]["description"]) > len(steps[moving]["description"]), (
            f"{path.name}: {briefing} against {moving}"
        )


# What the briefing of a timed step has to have named, in the language of each file:
# the motor (the press is the motor stopping, not the curtain arriving), the slats (the
# reason the two are not the same instant) and the base the bottom edge rests on.
TIMED_VOCABULARY: dict[str, tuple[str, str, str]] = {
    "strings": ("motor", "slats", "base"),
    "en": ("motor", "slats", "base"),
    "it": ("motore", "lamelle", "base"),
    "fr": ("moteur", "lames", "base"),
    "nl": ("motor", "lamellen", "basis"),
    "es": ("motor", "lamas", "base"),
    "de": ("motor", "lamellen", "grundlinie"),
    "pt": ("motor", "lâminas", "base"),
}


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_both_briefings_name_the_motor_the_slats_and_the_base(path: Path) -> None:
    """The one thing the second walk-through got wrong twice, in all eight files.

    Going up, the bottom edge leaves the base a second or two after the motor starts;
    coming down, the curtain goes on moving after the bottom edge touches, to close the
    slats. Both presses are the *motor*, and both briefings have to say so before the
    shutter is allowed to move.

    Mutation caught: translating the warning away in one language, which no structural
    check would otherwise see.
    """
    steps = options_block(path)["step"]
    for briefing in ("open_brief", "close_brief"):
        description = steps[briefing]["description"].lower()
        for word in TIMED_VOCABULARY[path.stem]:
            assert word in description, f"{path.name}: {briefing}: {word!r}"


# The single most consequential sentence in the whole flow, in the language of each
# file: **do not press** when the bottom edge touches **the base**, because the curtain
# goes on moving to close **the slats**. A press at the floor mis-measures the closing
# run by the whole slat phase, and every position the model computes afterwards is out
# by it. The three fragments have to appear in one and the same paragraph, so that a
# translation which keeps the words and loses the warning cannot pass.
CLOSE_WARNING: dict[str, tuple[str, str, str]] = {
    "strings": ("do not press", "base", "slats included"),
    "en": ("do not press", "base", "slats included"),
    "it": ("non premere", "base", "lamelle comprese"),
    "fr": ("n'appuyez pas", "base", "lames comprises"),
    "nl": ("druk niet", "basis", "lamellen inbegrepen"),
    "es": ("no pulses", "base", "lamas incluidas"),
    "de": ("drücken sie nicht", "grundlinie", "lamellen eingeschlossen"),
    "pt": ("não carregue", "base", "lâminas incluídas"),
}


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_the_closing_briefing_says_not_to_press_at_the_base(path: Path) -> None:
    """The warning is a negation, and a test that only looks for words cannot see it.

    `test_both_briefings_name_the_motor_the_slats_and_the_base` is satisfied by the
    three words appearing anywhere, so deleting the whole "Attenzione: non premere
    quando il bordo inferiore tocca la base" paragraph from the file the owner reads
    left all 1117 tests green (final review, mutation M22). FLOW asks for that sentence
    "esplicitamente", and it is the one the second live walk-through got wrong twice.

    Mutation caught: dropping the paragraph, or translating the negation away, in any
    of the eight files.
    """
    paragraphs = options_block(path)["step"]["close_brief"]["description"].lower().split("\n\n")
    wanted = CLOSE_WARNING[path.stem]
    assert any(all(fragment in paragraph for fragment in wanted) for paragraph in paragraphs), (
        f"{path.name}: close_brief never says {wanted!r} in one paragraph"
    )


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_the_three_ways_are_lettered_and_not_numbered(path: Path) -> None:
    """A, B and C, in the text and on the buttons: they are not steps in a sequence.

    Mutation caught: a label that stops announcing its letter, in any language - the
    paragraph above it says "the first (A) ...", and a button that does not answer it
    leaves the reader counting.
    """
    step = options_block(path)["step"]["path"]
    for option, letter in (("path_a", "(A)"), ("path_b", "(B)"), ("path_c", "(C)")):
        assert step["menu_options"][option].startswith(f"{letter} "), f"{path.name}: {option}"
        assert letter in step["description"], f"{path.name}: {letter}"
    assert set(step["menu_options"]) == {"path_a", "path_b", "path_c", "cancel_flow"}
