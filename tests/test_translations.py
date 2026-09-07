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

from custom_components.myhome.const import CONF_WORKER_COUNT, MAX_COMMAND_WORKERS

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
    """The worker count was the one option with a label and no ``data_description``.

    Its range is also the one the runtime clamps to (MAX_COMMAND_WORKERS), so the
    text has to name that number: a user who reads "1-10" and saves 8 gets 4.
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
