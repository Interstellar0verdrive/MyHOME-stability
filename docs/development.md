# Development

Setting up a development environment, running the test suite, and linting.

Home Assistant 2026.9 needs **Python 3.13 or newer** (`ruff.toml` pins
`target-version = "py313"`); CI runs 3.14.

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
```

Both commands run in CI on every push and pull request
(`.github/workflows/tests.yml`, Python 3.14 on `ubuntu-latest`): a change that
fails `ruff check .` or `pytest tests` is a red build. Two of the other three
workflows validate the integration manifest (`hassfest.yml`) and the HACS metadata
(`validate.yml`); `release.yml` is the manual release job — see
[Releasing](#releasing) below.

What the two configuration files pin, so that a local run matches the build:

| `ruff.toml` | Value |
|---|---|
| `target-version` | `py313` |
| `line-length` | `120` (measured on this tree: the median line is 38 characters and the 99th percentile 112, so 100 would have meant rewrapping ~400 working lines) |
| `select` | `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`, `RUF` |
| `ignore` | `RUF100` only — the tree carries `noqa` codes for rule families this selection does not enable |
| isort | `known-first-party` plus `combine-as-imports` |

Passing `--select` on the command line **replaces** that rule set instead of adding
to it, which is why the documented command is the bare `ruff check .`.

| `pytest.ini` | Value |
|---|---|
| `asyncio_mode` | `auto`, required by the Home Assistant test plugin |
| `markers` | a `slow` marker, plus `strict_markers = true`: a misspelled mark is a **collection error**, not a silent no-op |
| `strict_config` | `true` — an unknown ini key fails the run |
| `timeout` | `60` seconds per test, which needs `pytest-timeout` (it is in `requirements_test.txt`) |

Keep `--strict-markers` and `--strict-config` in the **ini** keys, never moved into
`addopts`: from `addopts` they are silently ignored on pytest 9, and the suite would
go on passing while both guarantees were gone.

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

The workflow then, in order: refuses a tag that already exists; builds the release
body from `CHANGELOG.md` with `python3 scripts/release_notes.py x.y.z` (the script
opens `CHANGELOG.md` relatively, so it only works from the repository root — the
workflow runs it there, and so should you if you preview it); creates and pushes the
tag; zips `custom_components/myhome/` into `myhome.zip`; publishes the release with
that asset; and finally bumps `"version"` in `custom_components/myhome/manifest.json`
and pushes that commit back to the branch it ran on. **The manifest version is
therefore set by the workflow, not by you** — if step 1's section is missing, the
notes step fails before the tag is pushed and nothing is published.

`scripts/release_notes.py` exists because GitHub renders every newline in a release
body as a line break, so the hard-wrapped changelog would show ragged lines: the
script unwraps each paragraph and rewrites relative `docs/...` links as absolute
repository URLs. To preview what the release will say:

```bash
python3 scripts/release_notes.py x.y.z | less
```

5. In Home Assistant, HACS → the repository → "Update information", then download
   the new version and restart.
