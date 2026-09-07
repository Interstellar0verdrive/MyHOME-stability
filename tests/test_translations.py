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
from pathlib import Path
from typing import Any

import pytest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "myhome"
STRINGS = COMPONENT / "strings.json"
TRANSLATIONS = sorted((COMPONENT / "translations").glob("*.json"))


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def leaf_keys(data: Any, prefix: str = "") -> set[str]:
    """Every dotted path of the JSON tree that ends on a string."""
    if not isinstance(data, dict):
        return {prefix}
    keys: set[str] = set()
    for key, value in data.items():
        keys |= leaf_keys(value, f"{prefix}.{key}" if prefix else key)
    return keys


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
