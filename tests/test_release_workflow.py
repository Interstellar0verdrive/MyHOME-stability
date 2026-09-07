"""Tests for the order of the steps in .github/workflows/release.yml.

The release job is run by hand, a few times a year, and its only failure mode that
does *not* show up as a red build is the order of its steps: the tag, the zip and
the manifest bump all read or write the same checkout, and HACS reads
`manifest.json` **from the tag**. Getting that order wrong ships a release that
advertises the previous version, which is invisible in CI and visible to every
user (see the *Releasing* section of docs/development.md).

Nothing else in the tree looks at this file, so these are the only tests that will
notice if the steps are shuffled again.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
RELEASE = WORKFLOWS / "release.yml"

BUMP = "Set the manifest version and commit it"
TAG = "Create and push tag"
ZIP = "Create myhome.zip"
NOTES = "Generate release notes from CHANGELOG.md"
GUARD = "Check if tag already exists"
PUBLISH = "Create GitHub Release"


@pytest.fixture(scope="module")
def steps() -> list[dict]:
    """The release job's steps, in file order."""
    workflow = yaml.safe_load(RELEASE.read_text(encoding="utf-8"))
    return workflow["jobs"]["release"]["steps"]


@pytest.fixture(scope="module")
def order(steps) -> dict[str, int]:
    """Step name -> position, so the assertions read as the order they pin."""
    return {step["name"]: index for index, step in enumerate(steps) if "name" in step}


def test_the_manifest_is_bumped_before_the_tag_and_the_zip(order) -> None:
    """The tag has to point at the commit that already carries the new version.

    HACS reads `manifest.json` from the tag and Home Assistant shows that string in
    *Settings -> Devices & services*. With the bump after the tag (which is how this
    job was written until the 2026-09 review) releasing `v0.4.1` produces a tag whose
    manifest still says `0.4.0`: the user installs the new version, is told they are
    running the old one, and HACS keeps offering the same update for ever because the
    installed version never matches the release tag. `myhome.zip` is built from the
    same checkout, so a manual installer gets the identical wrong number.

    Mutation caught: moving `Set the manifest version and commit it` back to the end
    of the job (or anywhere after `Create and push tag` / `Create myhome.zip`).
    """
    assert order[BUMP] < order[TAG] < order[ZIP] < order[PUBLISH]


def test_the_release_notes_and_the_tag_guard_run_before_anything_is_written(order) -> None:
    """A release that cannot be described must cost nothing to abandon.

    `scripts/release_notes.py` exits non-zero when `CHANGELOG.md` has no section for
    the version (tests/test_release_notes.py pins that), and the guard refuses a tag
    that already exists. Both have to run before the first step that changes the
    repository, or a forgotten changelog section leaves a stray commit - or a stray
    tag - on the branch.

    Mutation caught: moving `Generate release notes from CHANGELOG.md` or
    `Check if tag already exists` after the manifest bump.
    """
    assert order[GUARD] < order[NOTES] < order[BUMP]


def test_the_bump_step_verifies_and_commits_what_it_wrote(steps, order) -> None:
    """The bump is only worth anything if it is committed and actually took effect.

    The step edits `manifest.json` with `sed`; a `sed` that matches nothing used to
    print `Warning: manifest.json was not updated` and carry on, which is a warning
    inside a job nobody watches. It now asserts the file really says the version, and
    it commits and pushes before the tag is created - without the commit the tag would
    cover the unbumped tree again.

    Mutation caught: dropping the verification, the `git commit` or the `git push`
    from the step (each of them silently restores the shipped-the-old-version bug).
    """
    run = steps[order[BUMP]]["run"]

    assert 'sed -i \'s/"version": "[^"]*"/"version": "\'"$VERSION"\'"/\'' in run
    assert 'sys.exit(0 if got == version else' in run  # the assertion, not a warning
    assert "git commit -m" in run
    assert 'git push origin HEAD:"${{ github.ref_name }}"' in run
    assert "Warning" not in run


def test_the_job_bumps_the_manifest_exactly_once(steps) -> None:
    """One writer for the version, so the two cannot drift apart.

    The reordering fix replaces a trailing bump step rather than adding to it; a
    second `sed` on `manifest.json` after the tag would write the same value into an
    untagged follow-up commit and make the history look like the bug is still there.

    Mutation caught: re-adding the old `Update manifest version` step at the end.
    """
    writers = [step for step in steps if "manifest.json" in step.get("run", "")]
    assert [step["name"] for step in writers] == [BUMP]
