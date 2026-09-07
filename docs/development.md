# Development

Setting up a development environment, running the test suite, and linting.

Home Assistant 2026.9 needs **Python 3.14.2 or newer** (`homeassistant==2026.9.0`,
the version `requirements_test.txt` installs, declares
`Requires-Python: >=3.14.2`), which is what CI runs. `ruff.toml` still targets
`py313` because nothing in the tree uses 3.14-only syntax.

```bash
# Set up a virtual environment with the same Home Assistant / OWNd versions this
# integration targets, plus the test tooling. requirements_test.txt is the single
# list CI installs too (.github/workflows/tests.yml):
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt

# Lint (ruff.toml at the repository root pins the rule set and the line length,
# so the result does not depend on a global or editor configuration):
ruff check .

# Run the test suite (pytest.ini sets asyncio_mode = auto, required by the HA
# test plugin):
pytest tests -q

# The five tests that take half a second or more on their own carry the `slow`
# marker (a real connect timeout, a negotiation left to time out, the idle
# watchdog's probe window, a full config-entry setup against a loopback server,
# and two Home Assistant imports in two subprocesses); skipping them takes the run
# from ~16 s to ~11 s. Most of the
# other loopback-socket tests are fast and stay in both lanes, and every guarantee
# the marked ones cover is pinned in the fast lane as well:
pytest tests -q -m "not slow"
```

The first two of those commands run in CI on every push and pull request
(`.github/workflows/tests.yml`, Python 3.14 on `ubuntu-latest`): a change that
fails `ruff check .` or `pytest tests` is a red build. No workflow uses the
`not slow` lane; it is there for a local edit-run loop. Two of the other three
workflows validate the integration manifest (`hassfest.yml`) and the HACS metadata
(`validate.yml`); `release.yml` is the manual release job — see
[Releasing](#releasing) below.

What the two configuration files pin, so that a local run matches the build:

| `ruff.toml` | Value |
|---|---|
| `target-version` | `py313` |
| `line-length` | `120` (measured, not chosen: no line in the tree exceeds 120 characters, while 100 would have meant rewrapping several hundred working lines) |
| `select` | `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`, `RUF` |
| `ignore` | `RUF100` only — the tree carries `noqa` codes for rule families this selection does not enable |
| isort | `known-first-party` plus `combine-as-imports` |

Passing `--select` on the command line **replaces** that rule set instead of adding
to it, which is why the documented command is the bare `ruff check .`.

| `pytest.ini` | Value |
|---|---|
| `asyncio_mode` | `auto`, required by the Home Assistant test plugin |
| `markers` | a `slow` marker for the five long-running socket/subprocess tests, which `pytest.ini` describes as "half a second or more on its own" and which CI can split out with `-m "not slow"`, plus `strict_markers = true`: a misspelled mark is a **collection error**, not a silent no-op |
| `strict_config` | `true` — an unknown ini key fails the run |
| `timeout` | `60` seconds per test, which needs `pytest-timeout` (it is in `requirements_test.txt`) |

Keep `--strict-markers` and `--strict-config` in the **ini** keys, never moved into
`addopts`: from `addopts` they are silently ignored on pytest 9, and the suite would
go on passing while both guarantees were gone.

Every entry of `requirements_test.txt` is pinned, `ruff` and `pytest` included. A
floating `ruff` would turn a green build red with no change to the tree the day it
stabilises a preview rule in one of the selected families (`ruff check . --preview`
finds a few hundred such lines today), and `pytest.ini` depends on pytest-9
semantics. Bump either pin deliberately, in a commit that also fixes the fallout.
The exact count drifts with every `ruff` release, which is the whole point of the
pin, so it is not quoted here or in `requirements_test.txt`.

Coverage is not asked for by CI or by either command above, and its version is not
pinned here: `pytest-cov` arrives as a dependency of
`pytest-homeassistant-custom-component`, so the documented setup already has it and the
numbers may move a little when that pin is bumped. To reproduce the ones quoted in the
audits:

```bash
pytest tests -q --cov=custom_components/myhome --cov-report=term-missing
```

The tests never talk to a real gateway: `tests/test_gateway.py` and
`tests/test_init.py` spin up a loopback fake OpenWebNet server instead.
`tests/fixtures/myhome.yaml` is a fictional home — invented names and addresses
over the layout of a typical MyHOMEServer1 install — kept deliberately
realistic in size so the validator and the platforms are exercised at scale.

See [Architecture → Test strategy](architecture.md#test-strategy) for what each
test file covers, how the fake OpenWebNet server works, and what the end-to-end
test asserts.

## Releasing

`.github/workflows/release.yml` is the release mechanism. It owns the **tag**, the
**release notes** and the **`myhome.zip` asset** — the one the README tells users to
download — so do not create the tag or the release by hand: the workflow refuses to
run for a tag that already exists, and a hand-made release would carry no asset.

Prepare the branch first:

1. **Close the changelog section.** Rename the `## [Unreleased]` heading of
   `CHANGELOG.md` to `## [x.y.z] - YYYY-MM-DD`, open a fresh `## [Unreleased]` above
   it, and update the link-reference definitions at the bottom of the file: point
   `[Unreleased]:` at `compare/vx.y.z...HEAD` and add a `[x.y.z]:` tag URL.
2. **Scan the tracked files for anything personal** before committing (real device
   names, addresses, e-mail addresses): the fixture and the docs use an invented
   home on purpose.
3. **Push.** The workflow tags whatever it checks out, so the branch must already
   hold the release commit.

Then run the job:

4. **Actions → "Create Release" → Run workflow**, on the branch you just pushed,
   with `tag` = `vx.y.z` (tags are `v` + the version; the workflow strips the `v`
   for everything that wants the bare version). Optional inputs: a release `name`
   and a `prerelease` flag.

The workflow then, in order:

1. refuses a tag that already exists;
2. builds the release body from `CHANGELOG.md` with
   `python3 scripts/release_notes.py x.y.z` (the script opens `CHANGELOG.md`
   relatively, so it only works from the repository root — the workflow runs it
   there, and so should you if you preview it);
3. writes the version into `custom_components/myhome/manifest.json`, asserts that
   the file really says it, commits it and pushes that commit to the branch it ran
   on;
4. creates and pushes the tag, which therefore points **at** that bumped commit;
5. zips the *contents* of `custom_components/myhome/` into `myhome.zip` (no
   top-level folder in the archive) from the same bumped checkout;
6. publishes the release with that asset.

**The manifest version is therefore set by the workflow, not by you**, and steps
3-5 have to stay in that order: HACS reads `manifest.json` *from the tag*, so a tag
created before the bump would ship and advertise the previous version — the user
would install `vx.y.z`, be told they are running the version before it, and be
offered the same update for ever. The asset has the same problem, since it is built
from the checkout the tag covers. If step 1's changelog section is missing, the
notes step fails before anything is written, committed, tagged or published.

`scripts/release_notes.py` exists because GitHub renders every newline in a release
body as a line break, so the hard-wrapped changelog would show ragged lines: the
script unwraps each paragraph and rewrites relative `docs/`, `blueprints/`,
`README` and `CHANGELOG` links as absolute repository URLs, leaving external links
and anchors alone. To preview what the release will say:

```bash
python3 scripts/release_notes.py x.y.z | less
```

**Bumping the release action.** The publishing step runs
`softprops/action-gh-release`, a third-party action, with `contents: write`, so it is
pinned to a full commit SHA rather than to a tag, with the release that SHA belongs
to in a trailing comment:

```yaml
      - name: Create GitHub Release
        uses: softprops/action-gh-release@3bb12739c298aeb8a4eeaf626c5b8d85266b0e65  # v2.6.2
```

To move to a newer release of the action: find that release's commit on GitHub,
replace the 40 characters **and** the `# vX.Y.Z` comment in the same edit, then run
`pytest tests/test_release_workflow.py`. The suite only checks the *shape* of the ref
— it accepts a `vN` tag as readily as a 40-character SHA — so it will catch a branch
ref such as `@master`, but not a comment left behind on the previous version, nor a
pin quietly moved back to a tag. Keep the SHA form: the comment is the only
human-readable version marker there is.

### After the job

- `git pull` — the job pushed the manifest bump to the branch you ran it on, so
  your local `master` is one commit behind until you do.
- In Home Assistant, HACS → the repository → **Update information**, then download
  the new version and restart.
