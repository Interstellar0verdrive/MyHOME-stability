# Development

Setting up a development environment, running the test suite, and linting.

```bash
# Set up a virtual environment with the same Home Assistant / OWNd versions this
# integration targets, plus the test tooling:
python3 -m venv .venv
source .venv/bin/activate
pip install homeassistant pytest pytest-homeassistant-custom-component ruff \
  "OWNd==0.7.49"

# Run the test suite (pytest.ini sets asyncio_mode = auto, required by the HA
# test plugin):
pytest tests

# Lint (the same selection CI and the release checklist use):
ruff check custom_components tests --select F,E9,B,UP,ASYNC
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
