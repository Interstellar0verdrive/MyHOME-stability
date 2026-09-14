"""The committed bundle: is it there, is it the one the build makes, is it served.

The panel ships as a built file (`custom_components/myhome/frontend/myhome-panel.js`)
because HACS copies the integration directory as it exists at the tag and `release.yml`
zips the same directory: there is no build step at the user's end, and a branch install
with no bundle would show a blank page. The cost of that decision is a generated file in
the tree, and these tests are half of what pays for it.

The other half is `.github/workflows/panel.yml`, which rebuilds the bundle from
`panel_src/` and fails on any difference. That job needs node; these tests need nothing,
and run in the suite everybody already runs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import custom_components.myhome as myhome
from custom_components.myhome import PANEL_BUNDLE, PANEL_DIR, PANEL_ELEMENT, PANEL_STATIC_URL

# `build.mjs` writes this as the bundle's first line and nothing else does.
BANNER = "/* MyHOME calibration panel */"

BUNDLE = Path(PANEL_DIR) / PANEL_BUNDLE


def test_the_bundle_ships_with_the_integration() -> None:
    """It exists, it is not empty, and it is inside the directory HACS copies.

    Mutation caught: building somewhere outside `custom_components/myhome/`, which every
    developer's own Home Assistant would keep serving out of its cache while every user's
    installation got a 404.
    """
    assert BUNDLE.is_file()
    assert BUNDLE.stat().st_size > 0
    assert BUNDLE.parent.parent == Path(myhome.__file__).parent


def test_the_bundle_is_the_one_the_build_makes() -> None:
    """The banner is the build's signature: no banner, no `npm run build`.

    A hand-edited bundle is the failure mode a committed build artefact invites - a
    one-line fix applied to the generated file, working perfectly, and silently undone by
    the next real build. The banner catches the version of that mistake that starts with
    somebody writing the file from scratch; `panel.yml`'s `git diff --exit-code` catches
    the rest.

    Mutation caught: committing a bundle produced by anything but `panel_src/build.mjs`.
    """
    text = BUNDLE.read_text(encoding="utf-8")
    assert text.startswith(BANNER)
    # One ES module, minified: the element definition has to be in it.
    assert PANEL_ELEMENT in text
    assert "\n" in text  # a banner and a body, not a banner alone


def test_the_bundle_does_not_carry_a_version_and_must_not_start_to() -> None:
    """The version reaches the panel at runtime, never through the file.

    `release.yml` rewrites `manifest.json`'s version and commits it immediately before it
    tags. A bundle that embedded the version would be stale from that commit on, and
    `panel.yml` - which rebuilds and diffs - would go red on `main` after every release
    until somebody rebuilt by hand. So the registration puts the version in the panel's
    `config` and in the `?v=` of its URL, and the file itself says nothing about it.

    Mutation caught: reintroducing a build-time version stamp (`__MYHOME_PANEL_VERSION__`
    or the version in the banner), which would make every release a manual rebuild.
    """
    version = json.loads(
        (Path(myhome.__file__).parent / "manifest.json").read_text(encoding="utf-8")
    )["version"]
    text = BUNDLE.read_text(encoding="utf-8")
    assert "__MYHOME_PANEL_VERSION__" not in text
    assert version not in text.splitlines()[0]


def test_the_served_url_resolves_to_the_committed_file() -> None:
    """`/myhome_panel/myhome-panel.js` and the file on disk are the same thing.

    `_async_register_static_paths` serves `PANEL_DIR` at `PANEL_STATIC_URL`, and the
    registration builds the module URL out of the same two constants: this asserts that
    the join of them names a file that is actually there, which is the one mistake the
    two halves cannot catch on their own.

    Mutation caught: renaming the bundle on one side only.
    """
    assert PANEL_STATIC_URL.startswith("/")
    assert not PANEL_STATIC_URL.endswith("/")
    served = f"{PANEL_STATIC_URL}/{PANEL_BUNDLE}"
    assert served == "/myhome_panel/myhome-panel.js"
    assert (Path(PANEL_DIR) / served.removeprefix(f"{PANEL_STATIC_URL}/")).is_file()


def test_the_bundle_carries_lits_copyright_notice() -> None:
    """Lit is BSD-3-Clause, and the bundle is a binary redistribution of it.

    Clause 2 asks a redistribution in binary form to reproduce the copyright notice, the
    conditions and the disclaimer "in the documentation and/or other materials provided
    with the distribution". The bundle is what HACS copies into every installation and
    what `release.yml` puts in the zip, so the notice has to be in it (esbuild's
    `legalComments: "eof"`) and the text it refers to has to ship beside it.

    Mutation caught: `legalComments: "none"`, which silently strips every `@license`
    header out of the file that is actually distributed - the state this started in - or
    deleting the notices file that the shortened notice points at.
    """
    text = BUNDLE.read_text(encoding="utf-8")
    assert "SPDX-License-Identifier: BSD-3-Clause" in text
    assert "Google LLC" in text

    notices = BUNDLE.parent / "THIRD_PARTY_NOTICES.md"
    assert notices.is_file()
    licence = notices.read_text(encoding="utf-8")
    assert "BSD 3-Clause License" in licence
    # The disclaimer is the half of the licence a summary always loses.
    assert "THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS" in licence


def test_the_bundle_stays_inside_its_budget() -> None:
    """250 kB minified is the ceiling (risk R5, raised 14 Sept).

    The plan's original number was 150 kB, set before the management screens existed and
    reached by lot 8 with two lots still to come. It was never a download limit - the
    bundle is served once, from the user's own installation, gzipped by HA's own web
    server - but a tripwire for the kind of dependency that doubles a panel: a Markdown
    library, an icon font, a date library, a CSS framework. 250 kB is the same tripwire
    with room for the screens the plan itself asks for, and every one of those
    dependencies still trips it.

    Mutation caught: a dependency that doubles the download for a convenience.
    """
    assert BUNDLE.stat().st_size < 250 * 1024


# `build.mjs` minifies every Lit `css` block through esbuild's CSS minifier, and it finds
# those blocks with a regular expression. The expression is safe only while no `css` block
# in the panel's source interpolates or escapes anything - a block that did would have the
# wrong closing backtick, and the build would either throw or, worse, ship a stylesheet
# somebody's editor cannot explain. Nothing in the toolchain enforces that: `tsc` reads the
# source, not the transform, so a mangled stylesheet is a silent change of appearance.
CSS_BLOCK = re.compile(r"(?:^|[\s=(,\[:])css`([^`]*)`", re.MULTILINE)

PANEL_SOURCE = Path(myhome.__file__).parent.parent.parent / "panel_src" / "src"


def test_every_stylesheet_is_one_the_build_can_minify() -> None:
    """One `css` block, one match, and nothing interpolated inside any of them.

    Two assertions, because the regular expression can fail in two directions. Counting
    the bare occurrences of ``css`` against the blocks it matched catches a stylesheet the
    expression walks past - which would ship unminified and unnoticed. Looking inside each
    block for `${` or a backslash catches the case the head of `build.mjs` warns about: an
    interpolation makes the closing backtick the wrong one, so the "stylesheet" handed to
    the minifier would be half a program.

    It is a Python test about TypeScript because this is the suite everybody runs and
    `panel_src/` has no test runner of its own; the file it reads is in the repository
    either way.

    Mutation caught: writing `css` with an interpolated value in it (a token, a shared
    length), which is the natural thing to reach for and the one thing this build cannot
    take.
    """
    sources = sorted(PANEL_SOURCE.rglob("*.ts"))
    assert sources, PANEL_SOURCE
    for source in sources:
        text = source.read_text(encoding="utf-8")
        blocks = CSS_BLOCK.findall(text)
        assert text.count("css`") == len(blocks), f"{source.name}: a stylesheet is not matched"
        for block in blocks:
            assert "${" not in block, f"{source.name}: a stylesheet interpolates"
            assert "\\" not in block, f"{source.name}: a stylesheet escapes"
