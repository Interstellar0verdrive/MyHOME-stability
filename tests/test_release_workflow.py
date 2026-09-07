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

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
RELEASE = WORKFLOWS / "release.yml"

CHECKOUT = "Checkout repository"
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


def test_the_checkout_fetches_the_history_the_tag_guard_needs(steps, order) -> None:
    """The tag guard's local half is `git rev-parse`, which only sees fetched tags.

    `actions/checkout` fetches one commit and no tags by default, so on a shallow
    checkout `git rev-parse v0.4.1` fails for a tag that exists on the remote. The
    guard now asks the remote as well (see the test below), but the release notes are
    read from `CHANGELOG.md` and the rest of the job assumes a real history, so the
    full fetch is still part of what makes this job correct.

    Mutation caught: dropping `fetch-depth: 0` from the checkout step, or setting it
    to 1.
    """
    assert steps[order[CHECKOUT]]["with"]["fetch-depth"] == 0


def test_the_tag_guard_asks_the_remote_and_not_only_the_checkout(steps, order) -> None:
    """A tag that exists only on GitHub has to stop the job *before* anything is written.

    `git rev-parse` answers from the local object store, so a checkout that did not
    bring the tags down (a `fetch-depth` regression, a future `filter:`/`sparse`
    checkout, a re-run on a runner cache) makes the guard say "no such tag" for a tag
    that already exists. The job then bumps `manifest.json`, commits it and **pushes
    the commit to the branch**, and dies only afterwards on `git push origin <tag>` -
    leaving exactly the stray commit that
    `test_the_release_notes_and_the_tag_guard_run_before_anything_is_written` exists to
    prevent, reached by a different door. `git ls-remote` asks the remote itself and
    does not depend on what was fetched.

    Mutation caught: reverting the guard to `git rev-parse` alone (or dropping the
    `--exit-code`, without which `ls-remote` succeeds whether or not it found the tag).
    """
    run = steps[order[GUARD]]["run"]

    assert "git ls-remote" in run
    assert "--exit-code" in run  # without it ls-remote exits 0 on no match
    assert "--tags origin" in run
    assert 'refs/tags/$TAG' in run
    assert "exit 1" in run


def test_no_action_is_pinned_to_a_moving_ref(steps) -> None:
    """A release job with `contents: write` must not run whatever a branch says today.

    `softprops/action-gh-release` is third-party and gets the `GITHUB_TOKEN`; GitHub's
    hardening guide asks for a full commit SHA, and a version tag is the weaker form
    this repository accepts for now (see the *Releasing* section of
    docs/development.md). A branch ref - `@master`, `@main` - is neither: it is a
    third party's HEAD, executed with write access to this repository.

    This covers `release.yml` only. `hassfest.yml` and `validate.yml` deliberately use
    `@master` / `@main`, as their own comments explain, and neither job has write
    permissions.

    Mutation caught: re-pointing any `uses:` at a branch.
    """
    refs = {step["uses"] for step in steps if "uses" in step}
    assert refs, "the release job runs no actions at all?"
    for action in sorted(refs):
        ref = action.rsplit("@", 1)[-1]
        assert re.fullmatch(r"v\d+(?:\.\d+)*|[0-9a-f]{40}", ref), action
