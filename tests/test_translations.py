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

from custom_components.myhome.config_flow import TUNABLE_OPTIONS
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
