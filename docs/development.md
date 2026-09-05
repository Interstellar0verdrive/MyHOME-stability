# Development

Setting up a development environment, running the test suite, and linting.

```bash
# Set up a virtual environment with the same Home Assistant / OWNd versions this
# integration targets, plus the test tooling:
python3 -m venv .venv
source .venv/bin/activate
pip install homeassistant pytest pytest-homeassistant-custom-component ruff \
  "OWNd==0.7.48"

# Run the test suite (pytest.ini sets asyncio_mode = auto, required by the HA
# test plugin):
pytest tests

# Lint (matches what was run before this release):
ruff check custom_components tests --select F,E9,B,UP,ASYNC
```

The tests never talk to a real gateway: `tests/test_gateway.py` and
`tests/test_init.py` spin up a loopback fake OpenWebNet server instead. A test
fixture mirroring a real (redacted) `myhome.yaml` lives in `tests/fixtures/`.

See [Architecture → Test strategy](architecture.md#test-strategy) for what each
test file covers, how the fake OpenWebNet server works, and what the end-to-end
test asserts.
