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
    ERROR_INVALID_NAME,
    ERROR_NOT_A_NUMBER,
    ERROR_OUT_OF_RANGE,
    HOMING_ACTION,
    NO_PROFILE,
    PROBLEM_REASONS,
    RUNNING_ACTION,
)
from custom_components.myhome.config_flow import TUNABLE_OPTIONS, MyHomeOptionsFlowHandler
from custom_components.myhome.const import (
    CALIBRATION_ORIGIN_ADJUSTED,
    CALIBRATION_ORIGIN_INHERITED,
    CALIBRATION_ORIGIN_SELECTOR,
    CALIBRATION_ORIGINS,
    CONF_DEFAULT_KEEPALIVE_MINUTES,
    CONF_SENSOR_DEFAULTS,
    CONF_WORKER_COUNT,
    MAX_COMMAND_WORKERS,
)
from custom_components.myhome.device_trigger import ALL_SUBTYPES, ALL_TRIGGER_TYPES
from custom_components.myhome.panel_schemas import SESSION_ERROR_KEYS, WS_ERROR_KEYS
from custom_components.myhome.validate import CONF_ENERGY_DEFAULTS

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "myhome"
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

# ------------------------------------------------- the panel is written in two languages
# **Decision of 14 September** (``.audit-2026-09/PLAN-0.6.0.md``). The panel's own block
# is being written while the screens that read it are being built, and a sentence that
# has to be translated into seven languages before it can be tried on a screen is a
# sentence nobody rewrites. So ``config_panel`` is developed in **English and Italian**:
# those two, plus ``strings.json``, are held key-for-key; the other five may carry a
# subset, and every key they *do* carry must still use the same placeholders.
# ``panel_data.async_texts`` serves each language over English key by key, so a key those
# five have not reached yet arrives as the English sentence rather than as a dotted
# identifier. One translation lot before the 0.6.0 release fills them.
#
# **Everything else keeps the full eight-file parity**, 0.5.0's blocks included: those
# sentences are shipped, and a user reading them in French is not a developer waiting
# for a lot.
#
# It is called ``config_panel`` in the file and ``panel`` in the payload - see the long
# comment above ``PANEL_VIEWS``.
PANEL_BLOCK = "config_panel"
PANEL_PREFIX = f"{PANEL_BLOCK}."
# The languages the panel's sentences are written in today.
PANEL_LANGUAGES = frozenset({"en", "it"})

# The same decision reaches one block outside ``config_panel``: the refusals the guided
# calibration's session sends (0.6.0 wizard, lot B3). They live under ``exceptions``,
# where Home Assistant resolves a ``translation_key``, so they cannot be moved inside the
# panel's block - and they are the panel's sentences all the same, written beside the
# screens that show them. The same five languages may therefore lag on exactly these
# keys, and on no other refusal: the ones of 0.5.0 and earlier are shipped, and a user
# reading them in French is not a developer waiting for a lot.
#
# ``async_get_exception_message`` falls back to English key by key, as
# ``panel_data.async_texts`` does for the panel, so a key those five have not reached yet
# arrives as the English sentence rather than as ``already_calibrating``.
SESSION_REFUSAL_KEYS = frozenset(f"exceptions.{key}.message" for key in SESSION_ERROR_KEYS)


def panel_may_lag(path: Path) -> bool:
    """True for a file whose ``config_panel`` block is allowed to be a subset."""
    return path != STRINGS and path.stem not in PANEL_LANGUAGES


def may_lag(path: Path, key: str) -> bool:
    """True for one dotted key a file written in two languages need not carry yet."""
    return panel_may_lag(path) and (key.startswith(PANEL_PREFIX) or key in SESSION_REFUSAL_KEYS)


def test_the_translation_files_are_found() -> None:
    """A glob that silently matches nothing would make every test below vacuous."""
    assert STRINGS.is_file()
    assert {path.stem for path in TRANSLATIONS} == {"de", "en", "es", "fr", "it", "nl", "pt"}


@pytest.mark.parametrize("path", TRANSLATIONS, ids=lambda path: path.stem)
def test_each_locale_has_the_same_keys_as_strings_json(path: Path) -> None:
    """Same key set, no more and no less - except the panel's block, which may lag.

    A key in one file and not the other seven is either an untranslated string the user
    sees in English or, more often, a leftover nobody removed. The one exception is
    ``config_panel`` in the five languages the panel is not being written in: see the
    decision of 14 September above. A key they do not have is still forbidden from being
    a key ``strings.json`` does not have.
    """
    expected = leaf_keys(load(STRINGS))
    actual = leaf_keys(load(path))
    assert actual - expected == set(), f"{path.name} has keys strings.json does not"
    missing = {key for key in expected - actual if not may_lag(path, key)}
    assert missing == set(), f"{path.name} is missing keys of strings.json"


def test_the_panel_is_written_in_english_and_italian_and_the_rest_may_lag() -> None:
    """The decision of 14 September, stated once and checked.

    Three files are held key-for-key over ``config_panel`` - ``strings.json``, ``en`` and
    ``it`` - and the five others are a subset of them. A *superset* is caught by the test
    above; what this adds is that the two development languages never drift apart, which
    is the pair the screens are actually built against, and that "may lag" never quietly
    becomes "has nothing at all".

    Mutation caught: writing a panel key in English and not in Italian; deleting the
    block from one of the five while the translation lot is still ahead.
    """
    expected = {key for key in leaf_keys(load(STRINGS)) if key.startswith(PANEL_PREFIX)}
    assert expected, "strings.json has no config_panel block at all"
    for path in TRANSLATIONS:
        actual = {key for key in leaf_keys(load(path)) if key.startswith(PANEL_PREFIX)}
        if panel_may_lag(path):
            assert actual <= expected, f"{path.name} invents panel keys"
            assert actual, f"{path.name} has lost the panel's block"
        else:
            assert actual == expected, f"{path.name} must carry every panel key"


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
        if key not in actual and may_lag(path, key):
            # A panel key this language has not reached yet, or one of the session's
            # refusals: the English one is served in its place. The key test above is
            # what holds that to those two lists and to nothing else.
            continue
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
    # `assigned` / `from_file` split `count`: the shutters told to follow the profile
    # from this dialog, and the ones whose own `profile:` key in the configuration file
    # names it. The deletion reaches the two differently, so the two screens that are
    # about it say both numbers.
    "profile_actions": {"profile", "covers", "values", "count", "assigned", "from_file"},
    # `followers` is `covers` with each shutter's origin after its name. Only the screen
    # that *shows* the profile prints it: the two that are about deleting it name the
    # shutters plainly, because there the question is which of them lose the profile.
    "profile_view": {
        "profile", "covers", "values", "count", "assigned", "from_file", "followers"
    },
    "profile_edit": {"profile", "covers", "values", "count", "assigned", "from_file"},
    "profile_delete": {"profile", "covers", "values", "count", "assigned", "from_file"},
    "profile_deleted": {"profile", "covers", "count", "assigned", "from_file"},
    "calibrations": {"count"},
    "no_calibrations": set(),
    "no_basic_covers": set(),
    # `origin` is where the values the shutter runs on come from, in words - the same
    # answer `Calibration source` gives, said as a sentence. The four screens are given
    # it; the two that show the stored keys print it, because "these are the keys" and
    # "this is what wins" are two different statements.
    "calibration_actions": {"cover", "values", "profile", "measured_at", "origin"},
    "calibration_view": {"cover", "values", "profile", "measured_at", "origin"},
    "calibration_edit": {"cover", "values", "profile", "measured_at", "origin"},
    "calibration_delete": {"cover", "values", "profile", "measured_at", "origin"},
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
    "open_brief": {"cover"},
    "open_lift": {"cover"},
    # The lift-off run's own screens: the check, the tape reading that can replace the
    # press, and the screen for a press that came before the bottom edge moved at all.
    "lift_check": {"cover"},
    "lift_check_late": {"cover"},
    "lift_gap": {"cover"},
    "lift_early": {"cover"},
    "closed_again": {"cover"},
    "open_full_brief": {"cover"},
    "open_top": {"cover"},
    # `gap` is passed to both, and only the second says it: the first is the screen for
    # a conversation that measured no gap, where it would read "- cm".
    "open_result": {"cover", "slat", "run", "gap"},
    "open_result_gap": {"cover", "slat", "run", "gap"},
    "close_brief": {"cover"},
    "close_bottom": {"cover"},
    "close_result": {"cover", "run"},
    "height": {"cover"},
    "height_result": {"cover", "height"},
    "measure_descent": {"cover", "percent", "direction", "expected", "tolerance"},
    "measure_ascent": {"cover", "percent", "direction", "expected", "tolerance"},
    "measure_verify": {"cover", "percent", "direction", "expected", "tolerance"},
    "tape_result": {"cover", "percent", "measured"},
    # The one warning of the tape phase, which counts the readings it is about.
    "tape_brief": {"cover", "readings"},
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
    # Path C's own summary: the short one's list of what a save replaces, and the basic
    # one's offer of the thorough calibration.
    "summary_correction": {
        "cover", "yaml", "height", "accuracy", "percent", "profile", "replacing", "keeping",
    },
    "summary_precise": {
        "cover", "yaml", "height", "accuracy", "percent", "profile", "replacing", "keeping",
    },
    # One `saved` screen per path: what was written is a different sentence on each.
    # `source` is what `Calibration source` now says about this cover, read off the
    # record that was just written: a correction leaves `guided` or
    # `profile <name>, adjusted` depending on whether the profile still answers for
    # anything, and the screen that sends the user to look at the attribute quotes it.
    # `source` is the token the attribute carries, `origin` the same answer in words:
    # the three screens print both, side by side, so that what the dialog says and what
    # Developer tools shows can be recognised as one statement.
    "saved": {"cover", "profile", "source", "origin"},
    "saved_profile": {"cover", "profile", "source", "origin"},
    "saved_refined": {"cover", "profile", "source", "origin"},
    # Every way out of the conversation is given `_placeholders()`, so every one of
    # them may name the shutter it is about.
    "cancelled": {"cover"},
    "expired": {"cover"},
    "refused_unknown_cover": {"cover"},
    "refused_already_calibrating": {"cover"},
    # Every `problem_*` screen, which are generated from `PROBLEM_REASONS`.
    **{f"problem_{reason}": {"cover"} for reason in PROBLEM_REASONS},
}
# One `saved` screen per path of the guided flow (`GuidedCalibrationMixin`).
SAVED_SCREENS = ("saved", "saved_profile", "saved_refined")
PROGRESS_PLACEHOLDERS: dict[str, set[str]] = {
    "homing_closed": {"cover"},
    "homing_open": {"cover"},
    "starting_open": {"cover"},
    "starting_open_full": {"cover"},
    "stopping_lift": {"cover"},
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
        "open_timed",
        "open_start",
        "lift_stop",
        "open_home_again",
        "open_full_start",
        "close_timed",
        "close_start",
        "half_down",
        "half_up",
        "quarter_down",
        "quarter_up",
        "three_quarter_down",
        "three_quarter_up",
        "tape_run",
        "height_read",
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


# The two of the five origin phrases that name the profile a shutter is running on.
# They are the only ones with anything to substitute, and the substitution is done by
# the flow rather than by the frontend - these are selector options and not a step's
# `description_placeholders`.
ORIGINS_THAT_NAME_A_PROFILE = {CALIBRATION_ORIGIN_INHERITED, CALIBRATION_ORIGIN_ADJUSTED}


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_the_five_origins_are_written_in_every_language(path: Path) -> None:
    """Where a cover's values come from, said in words, in all seven languages.

    The screens that print it (`calibration_view` and the action menu above it, the
    "Calibrazioni" list, the assignment form, the three saved screens and a profile's
    followers) are given a phrase this side of the wire, because `resolve_cover` is
    what decides which of the five applies and the frontend never sees that. A
    language missing one of them would show the raw `guided` on those screens.

    Mutation caught: adding an origin to `const.py` and to one file only, or writing
    `{profile}` into the three that have no profile to name - which would leave the
    slot in the text, since only the flow substitutes it.
    """
    options = load(path)["selector"][CALIBRATION_ORIGIN_SELECTOR]["options"]
    assert set(options) == set(CALIBRATION_ORIGINS), path.name
    for key, text in options.items():
        assert text.strip(), f"{path.name}: {key} is empty"
        assert ("{profile}" in text) is (key in ORIGINS_THAT_NAME_A_PROFILE), (
            f"{path.name}: {key}"
        )
        assert set(PLACEHOLDER.findall(text)) <= {"profile"}, f"{path.name}: {key}"


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
def test_the_three_paths_end_on_three_different_saved_screens(path: Path) -> None:
    """Save writes something different on each path, and each has to say which.

    Path A measured this shutter and named a profile after it; path B measured nothing
    but its height and gave it a profile measured on another window; path C measured a
    few of its numbers over a profile it goes on following. One text for all three told
    two of them that the shutter "moves on the values just measured", which is a
    sentence the user cannot check against the attributes (final review).

    Mutation caught: copying one of the three descriptions over another, in any of the
    eight files.
    """
    step = options_block(path)["step"]
    descriptions = [step[name]["description"] for name in SAVED_SCREENS]
    assert len(set(descriptions)) == len(SAVED_SCREENS), path.name


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

    Since the third scope of the correction there are two summaries that do offer it -
    path A's and path C's - and two that cannot: path B's, whose numbers are the
    profile's by intent, and the thorough one, which is what the button leads to.

    Mutation caught: describing the thorough calibration on a summary that does not
    offer it, or offering it on path B's.
    """
    steps = options_block(path)["step"]
    assert set(steps["summary_basic"]["menu_options"]) == {"save", "refine", "cancel_flow"}
    assert set(steps["summary_correction"]["menu_options"]) == {"save", "refine", "cancel_flow"}
    assert set(steps["summary_short"]["menu_options"]) == {"save", "cancel_flow"}
    assert set(steps["summary_precise"]["menu_options"]) == {"save", "cancel_flow"}
    # The name of the button, as it appears in the text of the screens that have it.
    refine = steps["summary_basic"]["menu_options"]["refine"].split("(")[0].strip()
    assert refine == steps["summary_correction"]["menu_options"]["refine"].split("(")[0].strip()
    assert refine in steps["summary_basic"]["description"], path.name
    assert refine in steps["summary_correction"]["description"], path.name
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


# ------------------------------------------------------------------- the panel
# 0.6.0 gives the integration a second client. The panel of "Profili e tapparelle" says
# the same things the options flow says, in the same words, out of the same eight files -
# that is the whole point of `myhome/calibration/texts` - and the block it adds is the
# one place where a sentence exists for the panel and for nothing else.
#
# **It is called `config_panel` in the file and `panel` in the payload.** Home Assistant's
# `hassfest` validates `strings.json` and `translations/en.json` against a closed list of
# top-level keys (`script/hassfest/translations.py`, `gen_strings_schema`, a schema that
# prevents extra keys), and that list has `config_panel` on it - an arbitrarily nested
# tree of slug keys, meant for exactly this - and no `panel`. A top-level `panel` block
# turns `.github/workflows/hassfest.yml` red. `panel_data.TEXT_BLOCKS` renames it on the
# way out so the frontend keeps the `panel.<view>.<element>` namespace it is written
# against; the tests below are written on the file's name, `PANEL_BLOCK`, which is
# declared beside the two-language rule at the top of this module.

# The twelve views, in the order `.audit-2026-09/PANEL-TEXT-KEYS.md` lists them. A
# thirteenth view is a decision, not an accident: it changes what lots 7 and 8 may reach
# for, so it goes through this list first. `screen` is the twelfth, added by the
# reconciliation of lot 6b: it is the wizard engine's own chrome - the phase line, the
# two live rows of a timed run, the stub a template renders when 0.7.0 has not filled it -
# and it is a view because it belongs to `<myhome-screen>` and to none of the eleven
# screens that use it.
PANEL_VIEWS: tuple[str, ...] = (
    "common",
    "firstrun",
    "overview",
    "assign",
    "review",
    "dialog",
    "toast",
    "detail",
    "profile",
    "banner",
    # The thirteenth, added by lot F1 of the 0.6.0 wizard: the guided calibration's own
    # screen. It is a view and not part of `screen` because `screen` is the engine's
    # chrome - the phase line, the two live rows of a timed run - and these are the
    # sentences of the wizard itself: what it says when there is nothing to show, what it
    # says when a drawing threw, and the ways out it offers when ending a session is
    # refused.
    "wizard",
    "screen",
    "error",
)

# Every `{placeholder}` the panel's own sentences may use, with what the frontend is
# expected to put in it. A name invented in one language and not in the six others is
# already caught by the parity test; this one catches a name invented in all eight, which
# is the way a `{profilo}` gets shipped.
PANEL_PLACEHOLDERS: dict[str, str] = {
    "cover": "the name of one shutter",
    "profile": "the name of one profile",
    "profiles": "how many profiles this gateway has",
    "covers": "a list of shutter names, or how many covers this gateway has",
    "gateway": "the title of the config entry",
    "count": "a number of things the sentence is about",
    "travel": "a curtain travel in centimetres",
    "reference": "the reference travel of a profile, in centimetres",
    "opening": "the opening time, in seconds",
    "closing": "the closing time, in seconds",
    "slat": "the slat opening time, in seconds",
    "deviation": "how far the check was out, in centimetres",
    "date": "a date, formatted by the browser",
    "target": "a phrase naming where an assignment is going",
    "destination": "a phrase naming what a cover falls back to",
    "keys": "a list of value names",
    "value": "one number, already formatted",
    "from": "where a pending assignment comes from",
    "to": "where a pending assignment goes",
    "key": "the name of one value of the travel model",
    "min": "the lowest number a field accepts",
    "max": "the highest number a field accepts",
    "entry_id": "the id of a config entry",
    "phase": "the name of one phase of the guided calibration",
    "index": "which step of that phase this is",
    "time": "a time of day, formatted by the browser",
    # The guided calibration's own six (lot F2). Every one of them is a number the panel
    # has already written out in the reader's language, with the decimals SPEC §5.3 fixes
    # for it, except `origin`, which is one of the five phrases of
    # `selector.calibration_origin.options.*` put into a sentence of the panel's.
    "seconds": "a count of seconds, already formatted",
    "origin": "where a shutter's values come from, as the origin phrases say it",
    "accuracy": "how close the check came, in centimetres",
    "percent": "a fraction of the travel, as a whole percentage",
    "measured": "what the tape read, in centimetres",
    "predicted": "where the model said the shutter would stop, in centimetres",
    "threshold": "the deviation above which a shutter is worth measuring on its own",
}


def panel_block(path: Path) -> dict[str, Any]:
    return load(path)[PANEL_BLOCK]


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_the_panel_has_its_own_block_in_every_file(path: Path) -> None:
    """Eight files, twelve views, and not a single sentence baked into the bundle.

    The panel resolves every word through `myhome/calibration/texts`; a key it asks for
    and nobody wrote renders as the dotted key itself, on screen, in production. The key
    sets are already held by `test_each_locale_has_the_same_keys_as_strings_json` and by
    the two-language rule above; what this adds is that the block is *there* at all, and
    that its top level is the twelve views and nothing else - a stray `panel.misc` is
    where a thirteenth view starts.

    Mutation caught: translating the block into six languages and forgetting the seventh;
    adding a view without deciding it belongs.
    """
    block = panel_block(path)
    if panel_may_lag(path):
        assert set(block) <= set(PANEL_VIEWS), path.name
        assert block, path.name
    else:
        assert set(block) == set(PANEL_VIEWS), path.name
    assert all(isinstance(view, dict) and view for view in block.values()), path.name


def test_the_panel_never_says_a_word_the_flow_already_says() -> None:
    """One wording for two clients: the panel reuses, it does not restate.

    The five origin phrases and the six value labels are the vocabulary the entity's
    `Calibration source` attribute and the dialog's forms are written in. A copy of them
    under `panel.*` is a second sentence that drifts on the first review that touches only
    one of the two - which is exactly how "Slat time" and "Slat opening time" both existed
    for a while. The panel reads `selector.calibration_origin.options.*` and
    `options.step.calibration_edit.data.*` instead, and lot 5 has no business adding a key
    that says what one of those already says.

    Mutation caught: pasting an origin phrase or a field label into the panel's block.
    """
    strings = load(STRINGS)
    reserved = set(strings["selector"]["calibration_origin"]["options"].values())
    reserved |= set(strings["options"]["step"]["calibration_edit"]["data"].values())
    reserved |= set(strings["options"]["step"]["profile_edit"]["data"].values())
    offences = [
        (key, text)
        for key, text in flatten(panel_block(STRINGS)).items()
        if text in reserved
    ]
    assert not offences, "\n".join(
        f"{PANEL_BLOCK}.{key}: {text!r} already exists in the flow's own strings"
        for key, text in offences
    )


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_the_panel_substitutes_only_names_that_mean_something(path: Path) -> None:
    """A placeholder is a promise that the frontend passes that name.

    Home Assistant substitutes nothing here: the panel does it itself, key by key, so a
    `{profilo}` in the Italian is rendered as five literal characters between braces to
    the one user who reads that file. The parity test holds the seven languages to the
    English; this holds the English to a list somebody decided.

    Mutation caught: inventing a placeholder name in the source language, where parity
    would then propagate it to all eight.
    """
    offences = {
        (key, name)
        for key, text in flatten(panel_block(path)).items()
        for name in PLACEHOLDER.findall(text)
        if name not in PANEL_PLACEHOLDERS
    }
    assert not offences, f"{path.name}: {sorted(offences)}"


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_the_panel_says_none_of_the_words_the_lexicon_struck_out(path: Path) -> None:
    """The lexicon of 13 September is about the feature, not about one of its clients.

    `test_no_screen_says_a_word_the_lexicon_struck_out` reads the `options` block because
    that was the only place with screens in it. The panel has screens now, and they are
    the screens a user reaches first: "livello preciso" on a chip in the panel and
    "calibrazione approfondita" on the dialog behind it is the same failure the sweep of
    13 September was about, in a new file.

    Mutation caught: any struck-out term entering the panel's block, in any language.
    """
    forbidden = FORBIDDEN_BY_THE_LEXICON[path.stem]
    offences = [
        (key, word, instead)
        for key, text in flatten(panel_block(path)).items()
        for word, instead in forbidden.items()
        if word in text.lower()
    ]
    assert not offences, "\n".join(
        f"{path.name}: {key}: {word!r} - say {instead}" for key, word, instead in offences
    )


# ------------------------------------------------ the bundle and the keys it asks for
# The panel paints before `myhome/calibration/texts` has answered, and it paints when that
# call fails, so the bundle carries one English sentence per key it uses. Those stand-ins
# are a *copy* of the English block, and a copy that nobody checks is a copy that drifts -
# which is how "Search for a shutter" in the bundle and "Search for a cover" in the file
# coexisted for a lot.
#
# They live in `panel_src/src/i18n/fallback.json`, imported by `src/i18n/keys.ts`, for the
# sake of this test: a suite that runs with no Node can read JSON exactly, and can only
# guess at a TypeScript object literal with sentences wrapped over three lines in it.
PANEL_SRC = ROOT / "panel_src" / "src"
PANEL_FALLBACK = PANEL_SRC / "i18n" / "fallback.json"
PANEL_KEYS_TS = PANEL_SRC / "i18n" / "keys.ts"
# `"panel.overview.title"` in a `t(...)` call. Every key the bundle asks for is written as
# one string literal on one line - the one exception, the refusal path, asks for
# `exceptions.<key>.message` and is held by `test_every_refusal_the_panel_can_send_has_a_-
# sentence` instead.
PANEL_KEY_LITERAL = re.compile(r'"(panel\.[a-z0-9_.]+)"')


def bundle_stand_ins() -> dict[str, str]:
    return json.loads(PANEL_FALLBACK.read_text(encoding="utf-8"))


def test_the_bundle_asks_only_for_keys_the_files_have() -> None:
    """A key in the bundle and not in `strings.json` renders as a dotted identifier.

    Nothing else catches it: the frontend has a fallback for exactly these keys, so the
    panel looks right in English and shows `panel.overview.group_values` to everybody
    else. The reconciliation of lot 6b made the two lists one; this is what keeps them
    one.

    Mutation caught: adding a `t("panel.…")` call for a key nobody wrote; renaming a key
    in the files and leaving the bundle behind.
    """
    written = {key for key in leaf_keys(load(STRINGS)) if key.startswith(PANEL_PREFIX)}
    # `config_panel` in the file, `panel` in the payload, and the bundle speaks payload.
    written = {key.replace(PANEL_BLOCK, "panel", 1) for key in written}
    asked = set(bundle_stand_ins())
    assert asked, "the bundle declares no keys at all"
    assert asked - written == set(), "the bundle asks for keys strings.json does not have"


def test_the_offline_stand_ins_are_the_english_sentences() -> None:
    """Word for word, because the stand-in is what an English user actually reads first.

    Mutation caught: rewording a sentence in the eight files and leaving the bundle's copy
    saying the old thing - which shows up as a flash of the previous wording on every load
    and nowhere else.
    """
    english = {
        key.replace(PANEL_BLOCK, "panel", 1): text
        for key, text in flatten(load(STRINGS)).items()
        if key.startswith(PANEL_PREFIX)
    }
    wrong = {
        key: (text, english[key])
        for key, text in bundle_stand_ins().items()
        if key in english and text != english[key]
    }
    assert not wrong, "\n".join(
        f"{key}: bundle says {mine!r}, the file says {theirs!r}"
        for key, (mine, theirs) in sorted(wrong.items())
    )


def test_every_key_the_sources_use_is_declared_and_every_declared_key_is_used() -> None:
    """The stand-in list is the bundle's worklist, so it is neither short nor long.

    A key used and not declared has no fallback and no test behind it; a key declared and
    not used is an English sentence shipped in the bundle for nobody - the decision of 13
    September about dead keys, applied to this file. `keys.ts` is read too, because a
    `fallback.json` nothing imports would pass every assertion above while the bundle
    carried whatever it liked.

    Mutation caught: a `t()` call the reconciliation missed; a stand-in kept after the
    call that used it went away.
    """
    assert "fallback.json" in PANEL_KEYS_TS.read_text(encoding="utf-8")
    used: set[str] = set()
    for source in sorted(PANEL_SRC.rglob("*.ts")):
        if source.name == "keys.ts":
            continue
        used |= set(PANEL_KEY_LITERAL.findall(source.read_text(encoding="utf-8")))
    declared = set(bundle_stand_ins())
    assert used - declared == set(), "a panel key is used with no stand-in beside it"
    assert declared - used == set(), "a stand-in nobody asks for"


# ------------------------------------------------------- the refusals of the panel
# Every `send_error` the panel's WebSocket API sends carries `translation_domain="myhome"`
# and a `translation_key`, and Home Assistant resolves that pair - both in
# `homeassistant.helpers.translation.async_get_exception_message`, which builds
# `component.<domain>.exceptions.<key>.message`, and in the frontend, which does the same
# for a WebSocket error - against the top-level `exceptions` block. Not `options.error.*`,
# which is where a *form field's* error lives and which says nothing about which shutter
# or which value it is about.
#
# The keys the read half already has are read off `WS_ERROR_KEYS`; the three the write
# commands share with the guided dialog are read off `calibration_flow`, which is where
# they are defined. The seven the write half adds (lot 3) are named below because this
# branch predates the commit that declares them: the assertion is a superset one, so the
# moment `WS_ERROR_KEYS` grows to carry them the two agree instead of drifting. The eight
# the session adds (0.6.0 wizard) are `SESSION_ERROR_KEYS`, a tuple of their own because
# those eight - and only those eight - may still be missing from the five languages the
# panel is not being written in.
WRITE_REFUSALS: tuple[str, ...] = (
    "busy_calibrating",
    "write_in_progress",
    "missing_travel",
    "unknown_profile",
    "profile_not_editable",
    "name_in_use",
    "undo_expired",
)


def refusal_keys() -> set[str]:
    """Every `translation_key` a refusal of the panel can carry, from the code."""
    return (
        set(WS_ERROR_KEYS)
        | {ERROR_NOT_A_NUMBER, ERROR_OUT_OF_RANGE, ERROR_INVALID_NAME}
        | set(WRITE_REFUSALS)
        | set(SESSION_ERROR_KEYS)
    )


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_every_refusal_the_panel_can_send_has_a_sentence(path: Path) -> None:
    """A refusal with no sentence is a token on the screen, in seven languages.

    Derived from the constants rather than from a list kept by hand, so a key added to
    `WS_ERROR_KEYS` with no text behind it fails here rather than reaching a user as
    `unknown_profile`.

    The session's eight are the one exception, and a narrow one: they are held over
    `strings.json`, English and Italian, and tolerated - **only they** - in the five
    languages the panel is not being written in, where the English sentence is served in
    their place. A sixth key added to that tolerance would fail the test below, which
    holds the set of them to the constant.

    Mutation caught: adding a refusal to the WebSocket API and translating it nowhere;
    writing the sentence under `options.error.*`, where nothing resolves it; letting a
    refusal that is not the session's go untranslated in French.
    """
    written = load(path).get("exceptions", {})
    wanted = refusal_keys()
    if panel_may_lag(path):
        wanted -= set(SESSION_ERROR_KEYS)
    missing = sorted(wanted - set(written))
    assert not missing, f"{path.name}: no exceptions.<key>.message for {missing}"
    for key in sorted(refusal_keys() & set(written)):
        assert set(written[key]) == {"message"}, f"{path.name}: exceptions.{key}"


def test_the_session_s_refusals_are_the_only_ones_five_languages_may_still_miss() -> None:
    """The tolerance above, stated as the list it is, and held to the constant.

    The decision of 14 September is about the panel's own sentences; these eight are
    under `exceptions` because that is where Home Assistant resolves a
    `translation_key`, and nowhere else. Without this test "the five may lag" would
    widen by one key at a time, and a user reading Italian-only refusals in Spanish is
    exactly what the eight-file parity was for.

    Mutation caught: adding an older refusal to the tolerated set; a language file that
    has lost the session's block *and* a sentence it used to have.
    """
    assert {key.split(".")[1] for key in SESSION_REFUSAL_KEYS} == set(SESSION_ERROR_KEYS)
    for path in (STRINGS, COMPONENT / "translations" / "en.json", COMPONENT / "translations" / "it.json"):
        written = set(load(path)["exceptions"])
        assert set(SESSION_ERROR_KEYS) <= written, path.name
    for path in TRANSLATIONS:
        if not panel_may_lag(path):
            continue
        written = set(load(path)["exceptions"])
        assert written - set(SESSION_ERROR_KEYS) == set(load(STRINGS)["exceptions"]) - set(
            SESSION_ERROR_KEYS
        ), f"{path.name}: a refusal that is not the session's is missing"


# What the handler passes and the sentence deliberately leaves out. Two reasons, both
# of them "the sentence would be worse with it":
#
# * `unknown_entry` is sent twice, once with the entry id the client asked for and once,
#   when no gateway is loaded at all, with nothing - so a sentence naming the id would
#   show braces on the second path;
# * `already_calibrating`'s `{by}` (`panel` / `other` / `reserved`) and `session_ended`'s
#   `{reason}` (`cancelled`, `expired`, ...) are **tokens for the panel to branch on** -
#   it has a screen for each - and not words in anybody's language. Printed, an Italian
#   sentence would end in the English word `reserved`.
#
# Everything not in here is passed *and* printed, which is the ordinary case.
TOKENS_NOT_PRINTED: dict[str, set[str]] = {
    "unknown_entry": {"entry_id"},
    "already_calibrating": {"by"},
    "session_ended": {"reason"},
}


def test_every_refusal_substitutes_what_the_code_really_passes() -> None:
    """The braces have to match the dict beside them, refusal by refusal.

    `PASSES` is what each refusal's `translation_placeholders` carries, read off the
    handlers; what the sentence may print is that, minus `TOKENS_NOT_PRINTED`. Stating
    the two separately is what keeps "this one is bare" an explained decision with a
    list behind it instead of a sentence that quietly stopped naming something.

    Mutation caught: writing a sentence around a placeholder the handler does not pass
    (braces on screen), or naming one it does pass under a different name; printing a
    token the panel is meant to switch on.
    """
    passes: dict[str, set[str]] = {
        "unknown_entry": {"entry_id"},
        "entry_not_loaded": {"gateway"},
        "unknown_cover": set(),
        "advanced_cover": set(),
        "busy_calibrating": {"cover"},
        "write_in_progress": set(),
        "missing_travel": {"covers", "count"},
        "unknown_profile": {"profile"},
        "profile_not_editable": {"profile"},
        "name_in_use": {"profile"},
        "undo_expired": set(),
        "not_a_number": {"key"},
        "out_of_range": {"key", "min", "max"},
        "invalid_name": {"profile"},
        # ...and the session's eight (0.6.0 wizard).
        "already_calibrating": {"cover", "by"},
        "cover_unavailable": {"cover"},
        "unknown_session": set(),
        "session_ended": {"reason"},
        "session_owned": set(),
        "revision_conflict": set(),
        "action_not_offered": {"action"},
        "not_in_review": set(),
    }
    assert set(passes) == refusal_keys()
    assert set(TOKENS_NOT_PRINTED) <= set(passes)
    for key, hidden in TOKENS_NOT_PRINTED.items():
        assert hidden <= passes[key], key
    for path in [STRINGS, *TRANSLATIONS]:
        written = load(path)["exceptions"]
        for key, names in passes.items():
            if key not in written and may_lag(path, f"exceptions.{key}.message"):
                continue
            printed = names - TOKENS_NOT_PRINTED.get(key, set())
            assert set(PLACEHOLDER.findall(written[key]["message"])) == printed, f"{path.name}: {key}"


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
    "lift_check": "lift_off.webp",
    "lift_check_late": "lift_off.webp",
    "lift_gap": "lift_off.webp",
    "open_full_brief": "top_stop.webp",
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


# ------------------------------------------------------------------- the lexicon
# The words the lexicon of 13 September struck out, per language, with what they were
# replaced by. They are checked against the `options` block alone - the screens of the
# dialog and the forms around them - because that is what the lexicon is about; the
# `services` descriptions and the entity names are prose about the actions and have
# their own vocabulary.
#
# Only unambiguous terms are here. "altezza"/"height" is not, and cannot be: the word
# is right for the height of the bottom edge above its rest, which three reading forms
# ask for, and wrong for the distance between the end stops, which is the curtain
# travel - a substring test cannot tell the two apart, and a test that forbade the word
# outright would forbid the screens that need it.
FORBIDDEN_BY_THE_LEXICON: dict[str, dict[str, str]] = {
    "en": {
        "basic level": 'the first level is the "basic calibration"',
        "precise level": 'the second level is the "thorough calibration"',
        "refine": 'path C is the "correction"; the level it offers is the thorough calibration',
        "improve the accur": '"Continue with the thorough calibration"',
        "rescaled": '"scaled", or "adjusted" where a profile is adapted to a cover',
    },
    "it": {
        "livello base": 'il primo livello è la "calibrazione base"',
        "livello preciso": 'il secondo livello è la "calibrazione approfondita"',
        "affin": 'il percorso C è la "correzione"; il livello che offre è quello approfondito',
        "migliora la precis": '"Continua con la calibrazione approfondita"',
        "riadatt": '"adattato": il profilo viene adattato alla tapparella, non riadattato',
        "taratura": '"calibrazione" per tutta la funzione',
    },
    "fr": {
        "calibrage": '"la calibration" partout, y compris pour les deux niveaux',
        "affin": 'le chemin C est la "correction"',
        "niveau précis": '"la calibration approfondie"',
        "réadapt": '"adapté" / "ajusté"',
    },
    "nl": {
        "basisniveau": '"basiskalibratie"',
        "nauwkeurig niveau": '"uitgebreide kalibratie"',
        "verfijn": 'pad C is de "correctie"',
        "herschaal": '"geschaald" / "aangepast"',
    },
    "es": {
        "nivel básico": '"calibración básica"',
        "nivel preciso": '"calibración detallada"',
        "afina": 'la vía C es la "corrección"',
        "reescalad": '"escalado" / "ajustado"',
    },
    "de": {
        "basisstufe": '"Basis-Kalibrierung"',
        "genaue stufe": '"erweiterte Kalibrierung"',
        "verfeiner": 'Weg C ist die "Korrektur"',
        "neu skaliert": '"umgerechnet" / "angepasst"',
    },
    "pt": {
        "nível básico": '"calibração básica"',
        "nível preciso": '"calibração aprofundada"',
        "afina": 'o caminho C é a "correção"',
        "reescalad": '"ajustado"',
    },
}
FORBIDDEN_BY_THE_LEXICON["strings"] = FORBIDDEN_BY_THE_LEXICON["en"]


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_no_screen_says_a_word_the_lexicon_struck_out(path: Path) -> None:
    """One word per concept, in eight files, after two renamings that went half way.

    The second level was "il livello preciso", then "affina", then "migliora la
    precisione", each on a different screen and each in seven languages; path C was
    "affina la calibrazione" on one screen and "la correzione" on the next. The sweep
    of 13 September settled all of it, and this is what keeps the next text review from
    reintroducing one of them on the one screen nobody rereads.

    Mutation caught: any struck-out term coming back into any `options` text, in any
    language - the menu labels and the field names included.
    """
    forbidden = FORBIDDEN_BY_THE_LEXICON[path.stem]
    offences = [
        (key, word, instead)
        for key, text in flatten(options_block(path)).items()
        for word, instead in forbidden.items()
        if word in text.lower()
    ]
    assert not offences, "\n".join(
        f"{path.name}: {key}: {word!r} - say {instead}" for key, word, instead in offences
    )


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


# How many movements path A promises, in the word each language writes it with. The
# number itself is checked against the shutter in
# `test_calibration_flow.test_path_a_makes_the_number_of_movements_it_promises`; what is
# checked here is that the eight files agree about it, which is what went wrong when the
# ascent became two runs and again when the readings were reordered.
MOVEMENTS_PROMISED: dict[str, tuple[str, str]] = {
    "strings": ("Eight movements in all", "Nine movements"),
    "en": ("Eight movements in all", "Nine movements"),
    "it": ("otto movimenti", "nove movimenti"),
    "fr": ("Huit mouvements", "Neuf mouvements"),
    "nl": ("Acht bewegingen", "Negen bewegingen"),
    "es": ("Ocho movimientos", "Nueve movimientos"),
    "de": ("Acht Bewegungen", "Neun Bewegungen"),
    "pt": ("Oito movimentos", "Nove movimentos"),
}


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_every_language_promises_the_same_number_of_movements(path: Path) -> None:
    """Mutation caught: correcting the count in the Italian and nowhere else."""
    says, stale = MOVEMENTS_PROMISED[path.stem]
    description = options_block(path)["step"]["path_a"]["description"]
    assert says in description, f"{path.name}: path_a no longer says {says!r}"
    assert stale not in description, f"{path.name}: path_a still says {stale!r}"


# The word each language counts movements in, for the three entries of `refine_scope`.
# Every entry names what it costs, because the three are chosen against each other and
# "how long will this take" is the whole of the question being asked. The numbers are
# replayed against the shutter in `test_calibration_flow`
# (`test_the_thorough_scope_makes_the_movements_its_entry_promises` and the walks of the
# other two scopes); what is checked here is that the eight files agree about them.
SCOPE_MOVEMENTS: dict[str, str] = {
    "strings": "movements",
    "en": "movements",
    "it": "movimenti",
    "fr": "mouvements",
    "nl": "bewegingen",
    "es": "movimientos",
    "de": "Bewegungen",
    "pt": "movimentos",
}
SCOPE_COSTS: tuple[tuple[str, int], ...] = (
    ("times_only", 5),
    ("times_and_rolls", 8),
    ("points_only", 10),
)


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda path: path.stem)
def test_every_language_promises_the_same_counts_for_the_three_scopes(path: Path) -> None:
    """Mutation caught: correcting a count in one file, or adding a scope to one file."""
    options = options_block(path)["step"]["refine_scope"]["menu_options"]
    assert list(options) == [option for option, _cost in SCOPE_COSTS] + ["cancel_flow"]
    word = SCOPE_MOVEMENTS[path.stem]
    for option, cost in SCOPE_COSTS:
        assert f"{cost} {word}" in options[option], f"{path.name}: {option} no longer says {cost}"


# The screens a shutter is moving through while they are on the screen. "Nobody reads
# while watching the shutter": everything they would have said belongs to the briefing
# before the "Avvia" button, and what is left is one line and a button.
DURING_THE_MOVEMENT = {
    "open_lift": "open_brief",
    # Since the ascent became two runs, the screen that briefs the second press is the
    # second run's own briefing and not the first's.
    "open_top": "open_full_brief",
    "close_bottom": "close_brief",
}


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
    "de": ("motor", "lamellen", "auflagefläche"),
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
    for briefing in ("open_brief", "open_full_brief", "close_brief"):
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
    "de": ("drücken sie nicht", "auflagefläche", "lamellen eingeschlossen"),
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


# --------------------------------------------------------------- the documentation
# The pages quote the dialog's buttons and headings by name, because a page that
# paraphrases them leaves the reader hunting for a button that does not read like
# that. Each label below has to exist *verbatim* in the English strings and to be
# quoted *verbatim* in that page: a rename that catches only one of the two turns
# the documentation into a set of directions to a screen nobody can find. The 0.5.0
# text review renamed "Slat time" to "Slat opening time" and would have left
# `guided-calibration.md` listing a field by its old name.
DOCUMENTED_LABELS: dict[str, tuple[str, ...]] = {
    "docs/guided-calibration.md": (
        "Calibrate a cover",
        "(A) It is the first cover of its kind",
        "(B) It is similar to a cover already measured",
        "(C) It has a profile but stops in the wrong place",
        # The third scope of the correction and the button that reaches the same level
        # from a summary: both are quoted by the page, and both are new enough to be
        # renamed by the next text review.
        "Thorough calibration only",
        "Continue with the thorough calibration",
        "Start the cover",
        "1) Press when the bottom edge leaves the base",
        "2) Press when the motor stops at the top",
        "Press when the motor stops at the bottom",
        "Repeat the measurement",
        "It did not do what it should",
        "View the values",
        "Edit the values by hand",
        "Measure it again",
        "Delete the profile",
        "Delete the calibration",
        "No profile (the file's values, or the defaults)",
        "The cover did not answer",
        "The command never reached the bus",
        "The cover is already moving",
        "This cover is already being calibrated",
        # ...and the panel, which the page's last section sends the reader to by the
        # name at the top of its overview - and, since 0.6.0, by the two buttons of it
        # that open this same conversation there.
        "Profiles and covers",
        "Measure a cover",
        "Measure again",
        "Correct\u2026",
    ),
    # The panel's own page. Forty-six labels, which is what a page describing four
    # screens costs: the same two assertions as everywhere else, and the reason they
    # matter more here is that the panel's words live in `config_panel`, a block the
    # guided dialog never renders - so nothing else in the suite would notice a rename
    # on one side of it. Sentences carrying a placeholder (`{profile}`, `{count}`) are
    # deliberately absent: the page paraphrases those in italics, because an exact value
    # is what this test compares and a placeholder cannot be one.
    "docs/panel.md": (
        "Profiles and covers",
        "No profile",
        "Where it was measured is not recorded.",
        # The three origin words with no placeholder in them. The other two
        # (`inherited`, `adjusted`) carry `{profile}` in the selector and are quoted
        # from the panel's own placeholder-free pair instead.
        "Measured",
        "From the file",
        "Defaults",
        "Inherited",
        "Adjusted",
        "Search for a cover",
        "Filter by room",
        "All rooms",
        "No profile yet",
        "Measure a cover",
        "Take out of the profile \u2014 drop here",
        "Which profile?",
        "Withdraw this change",
        "Discard everything",
        "Review and confirm",
        "Before",
        "After",
        "How far does the curtain of these covers run?",
        "Curtain travel",
        "Back to the overview",
        "Undo",
        "Cover detail",
        "Values in use",
        "Edit the values by hand",
        "Set the curtain travel\u2026",
        "Remove the measurement\u2026",
        "Measure again",
        "Correct\u2026",
        "Times only",
        "Times and rolls",
        "Thorough calibration only",
        "Thorough calibration",
        "Profile card",
        "Impact preview",
        "Edit the values\u2026",
        "Rename\u2026",
        "Delete the profile\u2026",
        "Measurement in progress",
        "Resume the session",
        "End it",
        # The calibration, which since 0.6.0 runs on this page: the question the choice
        # of shutter asks, the screen a busy gateway answers with, and the controls of
        # a measurement under way. Sentences carrying a placeholder are paraphrased
        # here as everywhere else - "Save as the profile «{profile}»" among them.
        "Which shutter is being measured?",
        "The shutter is already in calibration",
        "Close the dialog and free the shutter",
        "Open Configure",
        "Stop the shutter",
        "Leave the calibration",
        "Buzz and beep when the motor starts",
        "Show every value, roll coefficients included",
        "Save for this shutter only",
        # The two doors out of the panel and into the dialog, which the page names
        # because the dialog stays a complete alternative. `Calibrate a cover` - the
        # third one - is *not* here: lot 11's handoff lists it, but the page never
        # quotes the label, it links the guided-calibration page instead. The map says
        # what the page really does, because the test asserts both directions and a
        # label listed here that the page does not carry is a failing suite, not a
        # documented one.
        "Calibrations",
        "Gateway and connection",
    ),
    "docs/configuration.md": (
        "Calibrate a cover",
        "Profiles and covers",
        "Calibrations",
        "Gateway and connection",
        "(B) It is similar to a cover already measured",
        "(C) It has a profile but stops in the wrong place",
    ),
    "docs/recipes.md": (
        "Calibrate a cover",
        "Generate events in Home Assistant for each message received",
    ),
    "docs/troubleshooting.md": ("Calibrate a cover",),
    "README.md": ("Calibrate a cover",),
    "CHANGELOG.md": ("Calibrate a cover", "Gateway and connection"),
}


@pytest.mark.parametrize("page", sorted(DOCUMENTED_LABELS), ids=lambda page: page.replace("/", "-"))
def test_the_docs_quote_labels_that_exist(page: str) -> None:
    """Every label a page names is a label the English file really carries.

    Mutation caught: renaming a button or a screen title in `strings.json` and
    leaving the page that tells the user to click it behind - which no other test
    sees, because the docs are not loaded by anything the flow tests exercise.
    """
    english = set(flatten(load(STRINGS)).values())
    # A label may be wrapped across two lines of Markdown, so both sides are read
    # with their whitespace collapsed.
    text = re.sub(r"\s+", " ", (ROOT / page).read_text(encoding="utf-8"))
    for label in DOCUMENTED_LABELS[page]:
        assert any(label == value or value.startswith(f"{label} (") for value in english), (
            f"{page} quotes {label!r}, which is not a label of strings.json"
        )
        assert re.sub(r"\s+", " ", label) in text, f"{page} no longer quotes {label!r}"
