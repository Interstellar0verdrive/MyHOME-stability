"""Tests for scripts/release_notes.py, the step release.yml builds its body with.

The script is not part of the integration, but it is the gate on the release: a
version whose CHANGELOG section is missing must exit non-zero *before* anything is
committed, tagged or published, and the body it prints is what users read on the
release page. Nothing else in the tree imports it, so without this file its three
functions are only ever exercised by a real release.

Every test here works on a synthetic CHANGELOG written into ``tmp_path``: the
script opens ``CHANGELOG.md`` relatively, and pinning it to the real one would make
these tests fail every time the changelog is edited.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "release_notes.py"


def _module():
    """Import the script by path (``scripts/`` is not a package)."""
    spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release_notes = _module()


def _main(version: str) -> None:
    """Run the script's ``main()`` the way the workflow does: on ``sys.argv``."""
    argv = sys.argv
    sys.argv = ["release_notes.py", version]
    try:
        release_notes.main()
    finally:
        sys.argv = argv


CHANGELOG = """# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed

- Something not released yet.

## [0.4.0] - 2026-09-07

### Added

- A first paragraph that is hard-wrapped
  over three source lines and has to come
  back as one long line.
- A second list item that must not be joined to the first.

See [the cover guide](docs/covers.md) and the [changelog](CHANGELOG.md), plus
[the README](README.md) and a [blueprint](blueprints/room_hold.yaml). External
links such as [Keep a Changelog](https://keepachangelog.com/) and images like
[a picture](images/screenshot.png) stay as they are.

## [0.3.1] - 2026-08-01

### Fixed

- The oldest section in this fixture.

[Unreleased]: https://example.com/compare/v0.4.0...HEAD
[0.4.0]: https://example.com/releases/tag/v0.4.0
[0.3.1]: https://example.com/releases/tag/v0.3.1
"""


@pytest.fixture
def changelog(tmp_path, monkeypatch) -> Path:
    """Run the script against a synthetic CHANGELOG.md in the current directory."""
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CHANGELOG, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return path


@pytest.mark.usefixtures("changelog")
def test_a_section_stops_at_the_next_version() -> None:
    """A release body must hold that release's notes and nothing else.

    The section regex ends on a lookahead for the next ``## [`` heading. Without it
    every release page would carry the whole history below it - and the newest
    release, the one everyone reads, would be the worst offender.

    Mutation caught: dropping ``(?=\\n## \\[|\\Z)`` from the section pattern (0.4.0's
    body then swallows the 0.3.1 section and the link-reference block).
    """
    body = release_notes.section("0.4.0")

    assert body.startswith("### Added")
    assert "A first paragraph" in body
    assert "0.3.1" not in body
    assert "The oldest section in this fixture." not in body
    assert "Something not released yet." not in body


@pytest.mark.usefixtures("changelog")
def test_the_oldest_section_drops_the_keep_a_changelog_link_block() -> None:
    """The link-reference definitions at the end of the file are not release notes.

    They run to the end of the file, so they belong to whichever section is last -
    today that is the oldest one, but the same is true of any release cut from a
    file whose newest section is also its last. Printed verbatim they render on the
    release page as a wall of bare URLs.

    Mutation caught: dropping the ``re.sub(r"\\n\\[[^\\]]+\\]:[^\\n]*", "", ...)`` line.
    """
    body = release_notes.section("0.3.1")

    assert body == "### Fixed\n\n- The oldest section in this fixture."
    assert "https://example.com/releases/tag/v0.3.1" not in body


@pytest.mark.usefixtures("changelog")
def test_a_missing_section_stops_the_release() -> None:
    """A version with no changelog section must abort the job, not publish an empty page.

    This is the only check standing between "somebody forgot step 1" and a tagged,
    published release with an empty body. `release.yml` runs this step before the
    manifest bump, the tag and the zip precisely so that the failure costs nothing.

    Mutation caught: returning ``""`` instead of ``None`` from ``section()``, or
    dropping the ``sys.exit`` in ``main()`` - either turns the abort into a release
    with no notes.
    """
    assert release_notes.section("9.9.9") is None

    with pytest.raises(SystemExit) as excinfo:
        _main("9.9.9")
    assert excinfo.value.code != 0
    assert "9.9.9" in str(excinfo.value.code)


@pytest.mark.usefixtures("changelog")
def test_the_printed_body_is_unwrapped_and_its_repository_links_are_absolute(capsys) -> None:
    """End to end: what `release.yml` pipes into the release body.

    GitHub renders a single newline in a release body as a line break, so the
    hard-wrapped changelog would show ragged lines; and a release page resolves a
    relative link against the *release* URL, so ``docs/covers.md`` would 404.

    Mutations caught: dropping ``unwrap()`` or ``absolutize()`` from ``main()``.
    """
    _main("0.4.0")
    printed = capsys.readouterr().out

    assert (
        "- A first paragraph that is hard-wrapped over three source lines"
        " and has to come back as one long line." in printed
    )
    assert f"]({release_notes.REPO}docs/covers.md)" in printed
    assert "](https://keepachangelog.com/)" in printed


def test_unwrap_starts_a_new_block_on_list_items_headings_tables_and_fences() -> None:
    """Joining is per block: a list item, a heading, a table row or a fence ends one.

    Joining across them is not a cosmetic problem - it destroys the markup. Two list
    items become one, a heading is absorbed into the paragraph above it, and a table
    collapses into a single unrenderable row.

    Mutation caught: dropping the ``flush()`` guarded by
    ``re.match(r"^\\s*([-*]|\\d+\\.)\\s", line) or line.startswith("#") or ...``.
    """
    out = release_notes.unwrap(
        "one line\nand its continuation\n"
        "- first item\n  wrapped\n"
        "- second item\n"
        "## a heading\n"
        "| a | b |\n"
        "| - | - |\n"
        "```\nnot  joined\nat all\n```\n"
    )

    assert out.split("\n") == [
        "one line and its continuation",
        "- first item wrapped",
        "- second item",
        "## a heading",
        "| a | b |",
        "| - | - |",
        "```",
        "not  joined",
        "at all",
        "```",
        "",
    ]


def test_absolutize_rewrites_repository_paths_and_nothing_else() -> None:
    """Only the five repository-relative prefixes are rewritten.

    An over-eager rule would rewrite ``https://…`` into a repository path (a dead
    link on every release page) or mangle an anchor; a missing one leaves a 404
    behind. The set is exactly what the docs and the changelog link to.

    Mutation caught: widening the prefix group to ``[^)\\s]+`` (external links get
    the repository URL glued in front of them).
    """
    rewritten = release_notes.absolutize(
        "[a](docs/covers.md) [b](CHANGELOG.md) [c](README.md) [d](blueprints/x.yaml)"
    )
    assert rewritten == (
        f"[a]({release_notes.REPO}docs/covers.md) [b]({release_notes.REPO}CHANGELOG.md) "
        f"[c]({release_notes.REPO}README.md) [d]({release_notes.REPO}blueprints/x.yaml)"
    )

    untouched = "[e](https://example.com/docs/x.md) [f](#anchor) [g](images/shot.png)"
    assert release_notes.absolutize(untouched) == untouched
