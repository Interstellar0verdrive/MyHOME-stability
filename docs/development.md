# Development

Setting up a development environment, running the test suite, and linting.

```bash
# Set up a virtual environment with the same Home Assistant / OWNd versions this
# integration targets, plus the test tooling. These are the versions CI installs
# (.github/workflows/tests.yml); keep the two in sync:
python3 -m venv .venv
source .venv/bin/activate
pip install "homeassistant==2026.9.0" "OWNd==0.7.49" pytest \
  "pytest-homeassistant-custom-component==0.13.363" ruff

# Lint (ruff.toml at the repository root pins the rule set and the line length,
# so the result does not depend on a global or editor configuration):
ruff check .

# Run the test suite (pytest.ini sets asyncio_mode = auto, required by the HA
# test plugin):
pytest tests -q
```

Both commands run in CI on every push and pull request
(`.github/workflows/tests.yml`, Python 3.14 on `ubuntu-latest`): a change that
fails `ruff check .` or `pytest tests` is a red build. The two other workflows
validate the integration manifest (hassfest) and the HACS metadata.

The tests never talk to a real gateway: `tests/test_gateway.py` and
`tests/test_init.py` spin up a loopback fake OpenWebNet server instead. A test
fixture describing an entirely fictional home lives in `tests/fixtures/`.

See [Architecture → Test strategy](architecture.md#test-strategy) for what each
test file covers, how the fake OpenWebNet server works, and what the end-to-end
test asserts.

## Releasing

1. Set the version in `custom_components/myhome/manifest.json` and turn the
   `## [x.y.z] - unreleased` heading of `CHANGELOG.md` into the release date.
2. Scan the tracked files for anything personal before committing (real device
   names, addresses, e-mail addresses): the fixture and the docs use an invented
   home on purpose.
3. Tag and publish. GitHub release notes render every newline as a line break,
   so do not paste the hard-wrapped changelog: generate the notes with
   `python3 scripts/release_notes.py x.y.z > /tmp/notes.md` and pass
   `--notes-file /tmp/notes.md` to `gh release create`.
4. In Home Assistant, HACS → the repository → "Update information", then download
   the new version and restart.
