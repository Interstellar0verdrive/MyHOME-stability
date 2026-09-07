"""Tests for the MyHOME config entry lifecycle (Contract D)."""

from __future__ import annotations

import threading
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er, issue_registry as ir
from OWNd.message import OWNGatewayCommand
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myhome import expected_unique_ids, issue_id, normalise_entry_data
from custom_components.myhome.const import (
    CONF_ENTITY,
    CONF_FILE_PATH,
    CONF_PLATFORMS,
    CONF_WORKER_COUNT,
    DOMAIN,
    GATEWAY_DIAG_SUFFIXES,
    ISSUE_NO_DEVICES_FOR_GATEWAY,
    ISSUE_UNKNOWN_KEYS,
    ISSUE_YAML_INVALID,
    MAX_COMMAND_WORKERS,
)

from .helpers_core import (
    BASIC_YAML,
    ENTRY_DATA_V2,
    LEGACY_ENTRY_DATA_V1,
    MAC,
    MAC2,
    make_entry,
    mock_gateway,
    write_yaml,
)
from .helpers_platforms import REAL_CONFIG_PATH
from .test_gateway import FakeOWNServer, wait_until

SERVICES = ("sync_time", "send_message", "start_discovery", "stop_discovery")

# The five diagnostic entities of the gateway device exist for every gateway, with or
# without devices in myhome.yaml (0.3.0, G1-B).
GATEWAY_DIAG_IDS = {f"{MAC}-{suffix}" for suffix in GATEWAY_DIAG_SUFFIXES}


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> bool:
    entry.add_to_hass(hass)
    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return result


async def test_setup_and_unload(hass: HomeAssistant, tmp_path) -> None:
    """Entities, gateway device, services and clean unload."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        assert await _setup(hass, entry)
        assert entry.state is ConfigEntryState.LOADED

        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        assert handler.listening_worker is not None
        assert len(handler.sending_workers) == 1

        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)

        light = entity_registry.async_get("light.light_test")
        assert light is not None
        assert light.unique_id == f"{MAC}-1-11"
        assert light.config_entry_id == entry.entry_id
        assert entity_registry.async_get_entity_id("cover", DOMAIN, f"{MAC}-2-81") is not None
        assert entity_registry.async_get_entity_id("button", DOMAIN, f"{MAC}-2-81-disable") is not None
        assert entity_registry.async_get_entity_id("button", DOMAIN, f"{MAC}-2-81-enable") is not None

        gateway_device = device_registry.async_get_device_by_identifier((DOMAIN, MAC), entry.entry_id)
        assert gateway_device is not None
        assert gateway_device.manufacturer == "BTicino S.p.A."
        assert gateway_device.model == "MyHOMEServer1"
        assert gateway_device.sw_version is None
        assert handler.device_id == gateway_device.id

        light_device = device_registry.async_get(light.device_id)
        assert light_device.via_device_id == gateway_device.id

        for service in SERVICES:
            assert hass.services.has_service(DOMAIN, service)

        # Held on to across the unload: nulling the handler's two fields proves
        # nothing about the tasks themselves.  Under `mock_gateway` both loops are
        # `await asyncio.Event().wait()`, so they can only ever end by cancellation.
        workers = [handler.listening_worker, *handler.sending_workers]
        assert not any(task.done() for task in workers)

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert MAC not in hass.data[DOMAIN]
    assert handler.listening_worker is None
    assert handler.sending_workers == []
    # core-10: every loop task is really finished, not merely forgotten, so none of
    # them can run against the `hass.data` entry that has just been popped.  Two
    # independent mechanisms guarantee it - `close_listener` cancels and awaits
    # them, and they are `entry.async_create_background_task`s, which Home
    # Assistant cancels on unload - which is exactly why the third pass that used
    # to live in `_async_cancel_workers` could never do anything.
    assert all(task.done() for task in workers)
    for service in SERVICES:
        assert not hass.services.has_service(DOMAIN, service)


async def test_reload_twice_keeps_services_working(hass: HomeAssistant, tmp_path) -> None:
    """core-03: after reloads the default gateway is still resolved."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        assert await _setup(hass, entry)
        for _ in range(2):
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
        assert set(hass.data[DOMAIN]) == {MAC}
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        before = handler.send_buffer.qsize()
        await hass.services.async_call(DOMAIN, "send_message", {"message": "*1*1*11##"}, blocking=True)
        assert handler.send_buffer.qsize() == before + 1


async def test_migration_unwraps_legacy_lists(hass: HomeAssistant, tmp_path) -> None:
    """core-06 / cf-03: version 1 entries with list-valued data are migrated."""
    entry = make_entry(write_yaml(tmp_path), data=LEGACY_ENTRY_DATA_V1, version=1)
    with mock_gateway():
        assert await _setup(hass, entry)
    assert entry.version == 2
    assert entry.data["manufacturer"] == "BTicino S.p.A."
    assert entry.data["firmware"] is None
    assert entry.data["ssdp_location"] is None
    assert entry.data["UDN"] is None
    assert entry.data["host"] == ENTRY_DATA_V2["host"]

    gateway_device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, MAC), entry.entry_id)
    assert gateway_device.manufacturer == "BTicino S.p.A."
    assert gateway_device.sw_version is None


def test_normalise_entry_data_only_unwraps_singletons() -> None:
    data = normalise_entry_data({"manufacturer": ["A"], "firmware": [None], "host": "h", "port": 20000, "UDN": []})
    assert data == {"manufacturer": "A", "firmware": None, "host": "h", "port": 20000, "UDN": []}


async def test_connection_refused_is_not_ready(hass: HomeAssistant, tmp_path) -> None:
    """core-08: OWNd returning None -> ConfigEntryNotReady, not a TypeError."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway(test_result=None):
        assert not await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert MAC not in hass.data[DOMAIN]


async def test_os_error_is_not_ready(hass: HomeAssistant, tmp_path) -> None:
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway(test_side_effect=OSError("no route to host")):
        assert not await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_auth_failure_starts_reauth(hass: HomeAssistant, tmp_path) -> None:
    """core-02 / cf-02: wrong password -> ConfigEntryAuthFailed -> reauth flow."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway(test_result={"Success": False, "Message": "password_error"}):
        assert not await _setup(hass, entry)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH
    assert flows[0]["context"]["entry_id"] == entry.entry_id
    assert flows[0]["step_id"] == "reauth_confirm"


async def test_invalid_yaml_is_setup_error(hass: HomeAssistant, tmp_path) -> None:
    """core-08: YAML/schema errors become a readable ConfigEntryError."""
    path = write_yaml(tmp_path, "gateway: [1, 2]\n")
    entry = make_entry(path)
    with mock_gateway():
        assert not await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert str(path) in (entry.reason or "")

    path = write_yaml(
        tmp_path,
        "gateway:\n  mac: 00:03:50:aa:bb:cc\n  light:\n"
        "    a: {where: '11', name: A}\n    b: {where: '11', name: B}\n",
    )
    entry = make_entry(path, mac=MAC2)
    with mock_gateway():
        assert not await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert "Duplicate WHERE" in (entry.reason or "")


async def test_missing_file_is_created(hass: HomeAssistant, tmp_path, caplog) -> None:
    path = tmp_path / "missing.yaml"
    entry = make_entry(path)
    with mock_gateway():
        assert await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert path.is_file()
    assert "not found" in caplog.text
    # No device from the file, but the gateway diagnostic entities are still there.
    entries = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert {entity.unique_id for entity in entries} == GATEWAY_DIAG_IDS


async def test_registry_pruning_keeps_user_disabled_entities(hass: HomeAssistant, tmp_path) -> None:
    """core-05: stale entries go, user-disabled configured entities stay, gateway device stays."""
    entry = make_entry(write_yaml(tmp_path))
    entry.add_to_hass(hass)
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    stale = entity_registry.async_get_or_create("light", DOMAIN, f"{MAC}-1-99", config_entry=entry)
    disabled = entity_registry.async_get_or_create(
        "button", DOMAIN, f"{MAC}-2-81-disable", config_entry=entry, disabled_by=er.RegistryEntryDisabler.USER
    )
    stale_device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, f"{MAC}-1-99")}, name="Stale"
    )

    with mock_gateway():
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entity_registry.async_get(stale.entity_id) is None
    kept = entity_registry.async_get(disabled.entity_id)
    assert kept is not None
    assert kept.disabled_by is er.RegistryEntryDisabler.USER
    assert device_registry.async_get(stale_device.id) is None
    assert device_registry.async_get_device_by_identifier((DOMAIN, MAC), entry.entry_id) is not None
    # The gateway diagnostic entities have no YAML counterpart: pruning must keep them.
    kept_ids = {entity.unique_id for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id)}
    assert kept_ids >= GATEWAY_DIAG_IDS


async def test_services_validation(hass: HomeAssistant, tmp_path) -> None:
    """core-07: schemas, ServiceValidationError, optional gateway."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        assert await _setup(hass, entry)
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]

        before = handler.send_buffer.qsize()
        await hass.services.async_call(DOMAIN, "sync_time", {}, blocking=True)
        assert handler.send_buffer.qsize() == before + 1

        await hass.services.async_call(
            DOMAIN, "send_message", {"gateway": "00-03-50-AA-BB-CC", "message": "*1*0*11##"}, blocking=True
        )
        assert handler.send_buffer.qsize() == before + 2

        # Each refusal is pinned to its own `translation_key`: a bare
        # `pytest.raises(ServiceValidationError)` cannot tell the four apart, so
        # deleting any one branch leaves the user with a different (wrong) message
        # and a green suite.  `invalid_gateway` is the clearest case: without it
        # "zz" falls through to `gateway_not_found`, which also raises.
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(DOMAIN, "send_message", {"message": "not a frame"}, blocking=True)
        assert err.value.translation_key == "invalid_message"
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(
                DOMAIN, "send_message", {"gateway": "zz", "message": "*1*0*11##"}, blocking=True
            )
        assert err.value.translation_key == "invalid_gateway"
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(DOMAIN, "sync_time", {"gateway": MAC2}, blocking=True)
        assert err.value.translation_key == "gateway_not_found"
        with pytest.raises(ServiceValidationError) as err:  # cv.string coerces 1 -> "1", not a frame
            await hass.services.async_call(DOMAIN, "send_message", {"message": 1}, blocking=True)
        assert err.value.translation_key == "invalid_message"


async def test_sync_time_builds_the_command_off_the_event_loop(hass: HomeAssistant, tmp_path) -> None:
    """0.3.1 (forks review 5.3, found by sxpert): ``OWNGatewayCommand.set_datetime_to_now``
    calls ``pytz.timezone()``, which reads the tz database from disk.  Building the
    command in the event loop is exactly what Home Assistant reports as a blocking
    call, so it must happen in ``hass.async_add_executor_job``."""
    entry = make_entry(write_yaml(tmp_path))
    threads: list[str] = []
    real = OWNGatewayCommand.set_datetime_to_now

    def spy(time_zone: str):
        threads.append(threading.current_thread().name)
        return real(time_zone)

    with mock_gateway():
        assert await _setup(hass, entry)
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        before = handler.send_buffer.qsize()
        loop_thread = threading.current_thread().name

        with patch.object(OWNGatewayCommand, "set_datetime_to_now", spy):
            await hass.services.async_call(DOMAIN, "sync_time", {}, blocking=True)

        # The command was still built and queued...
        assert handler.send_buffer.qsize() == before + 1
        # ...but not on the event loop thread.
        assert threads and loop_thread not in threads


async def test_two_gateways_require_explicit_gateway(hass: HomeAssistant, tmp_path) -> None:
    yaml = f"""
gateway:
  mac: {MAC}
  light:
    a: {{where: '11', name: A}}
{MAC2}:
  light:
    b: {{where: '12', name: B}}
"""
    path = write_yaml(tmp_path, yaml)
    entry1 = make_entry(path)
    entry2 = make_entry(path, mac=MAC2)
    with mock_gateway():
        assert await _setup(hass, entry1)
        assert await _setup(hass, entry2)
        assert set(hass.data[DOMAIN]) == {MAC, MAC2}

        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(DOMAIN, "sync_time", {}, blocking=True)
        # Two gateways loaded and none named: `gateway` stops being optional.
        assert err.value.translation_key == "gateway_required"
        assert err.value.translation_placeholders == {"count": "2"}
        await hass.services.async_call(DOMAIN, "sync_time", {"gateway": MAC2}, blocking=True)

        # Services survive the unload of ONE entry.
        assert await hass.config_entries.async_unload(entry1.entry_id)
        await hass.async_block_till_done()
        assert hass.services.has_service(DOMAIN, "sync_time")
        assert set(hass.data[DOMAIN]) == {MAC2}

        assert await hass.config_entries.async_unload(entry2.entry_id)
        await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, "sync_time")


async def test_default_file_path_option(hass: HomeAssistant, tmp_path) -> None:
    """An explicit empty option falls back to <config>/myhome.yaml."""
    entry = make_entry(write_yaml(tmp_path), options={CONF_FILE_PATH: ""})
    with mock_gateway(), pytest_default_path(hass, tmp_path):
        assert await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED


class pytest_default_path:  # noqa: N801 - tiny context helper
    """Point hass.config.config_dir at tmp_path for the duration of the test."""

    def __init__(self, hass: HomeAssistant, tmp_path) -> None:
        self.hass = hass
        self.tmp_path = tmp_path
        self._old = hass.config.config_dir

    def __enter__(self):
        self.hass.config.config_dir = str(self.tmp_path)
        return self

    def __exit__(self, *exc):
        self.hass.config.config_dir = self._old
        return False


# --------------------------------------------------------------------------- repairs (0.3.0)
def _issue(hass: HomeAssistant, entry: MockConfigEntry, issue: str):
    return ir.async_get(hass).async_get_issue(DOMAIN, issue_id(entry, issue))


def test_expected_unique_ids_always_contain_the_gateway_diagnostics() -> None:
    """G1-B: the five diagnostic ids must never be pruned, even with an empty config."""
    assert expected_unique_ids(MAC, {}) == GATEWAY_DIAG_IDS
    with_light = expected_unique_ids(MAC, {"light": {"1-11": {}}})
    assert with_light == GATEWAY_DIAG_IDS | {f"{MAC}-1-11"}


async def test_repair_invalid_yaml_created_then_cleared(hass: HomeAssistant, tmp_path) -> None:
    """G1-C: a broken file raises an error issue; fixing it and reloading clears it."""
    path = write_yaml(tmp_path, "gateway: [1, 2]\n")
    entry = make_entry(path)
    with mock_gateway():
        assert not await _setup(hass, entry)

    issue = _issue(hass, entry, ISSUE_YAML_INVALID)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.ERROR
    assert issue.is_fixable is False
    assert issue.translation_placeholders["path"] == str(path)
    # `gateway: [1, 2]` IS a mapping at the top level, so this is the schema engine
    # rejecting the section - not `__init__.py`'s own "must contain a mapping"
    # branch, which the test below covers. Assert only what this integration
    # controls (the offending key reaches the user); the exact wording belongs to
    # the engine and is pinned by `test_probatio_and_voluptuous_agree`, which also
    # documents that the two engines render the path differently.
    assert "gateway" in issue.translation_placeholders["message"]

    path.write_text(BASIC_YAML, encoding="utf-8")
    with mock_gateway():
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert _issue(hass, entry, ISSUE_YAML_INVALID) is None


async def test_repair_top_level_not_a_mapping(hass: HomeAssistant, tmp_path) -> None:
    """G1-C: a configuration file that is not a mapping at all is reported by name.

    `__init__.py` checks this itself, before the schema ever runs, because the
    schema's own error for a list would be unreadable. The check had no test: the
    only file that reached the repair issue was `gateway: [1, 2]`, which IS a
    mapping, so the branch was a coverage miss and the assertion that looked like
    it covered it was really reading the schema engine's wording.

    Mutation caught: deleting the `if not isinstance(parsed, dict)` branch, after
    which a YAML list reaches `config_schema` and the user gets the engine's
    complaint about `data` instead of a sentence naming the actual problem.
    """
    path = write_yaml(tmp_path, "- 1\n- 2\n")
    entry = make_entry(path)
    with mock_gateway():
        assert not await _setup(hass, entry)

    issue = _issue(hass, entry, ISSUE_YAML_INVALID)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.ERROR
    message = issue.translation_placeholders["message"]
    assert "must contain a mapping" in message
    assert "found list" in message  # the type is named, so the user can see what they wrote


async def test_repair_unknown_keys_created_then_cleared(hass: HomeAssistant, tmp_path) -> None:
    """G1-C: unknown keys are collected by validate.py and listed in a warning issue."""
    bad = f"""
gateway:
  mac: {MAC}
  light:
    light_test:
      where: '11'
      name: Light Test
      dimable: true
"""
    path = write_yaml(tmp_path, bad)
    entry = make_entry(path)
    with mock_gateway():
        assert await _setup(hass, entry)

    issue = _issue(hass, entry, ISSUE_UNKNOWN_KEYS)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_placeholders["count"] == "1"
    assert "dimable" in issue.translation_placeholders["keys"]
    assert "dimmable" in issue.translation_placeholders["keys"]  # difflib hint

    path.write_text(BASIC_YAML, encoding="utf-8")
    with mock_gateway():
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert _issue(hass, entry, ISSUE_UNKNOWN_KEYS) is None


async def test_repair_no_devices_for_gateway_created_then_cleared(hass: HomeAssistant, tmp_path) -> None:
    """G1-C: the gateway MAC is absent from the file -> warning issue, no crash."""
    path = write_yaml(tmp_path)
    entry = make_entry(path, mac=MAC2)
    with mock_gateway():
        assert await _setup(hass, entry)
    assert entry.state is ConfigEntryState.LOADED

    issue = _issue(hass, entry, ISSUE_NO_DEVICES_FOR_GATEWAY)
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert issue.translation_placeholders["mac"] == MAC2
    assert MAC in issue.translation_placeholders["others"]

    path.write_text(BASIC_YAML.replace(MAC, MAC2), encoding="utf-8")
    with mock_gateway():
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert _issue(hass, entry, ISSUE_NO_DEVICES_FOR_GATEWAY) is None


async def test_repairs_removed_with_the_entry(hass: HomeAssistant, tmp_path) -> None:
    """Removing the gateway must not leave its repair issues behind."""
    entry = make_entry(write_yaml(tmp_path), mac=MAC2)
    with mock_gateway():
        assert await _setup(hass, entry)
        assert _issue(hass, entry, ISSUE_NO_DEVICES_FOR_GATEWAY) is not None
        assert await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()
    assert _issue(hass, entry, ISSUE_NO_DEVICES_FOR_GATEWAY) is None


# --------------------------------------------------------------------------- end to end
@pytest.mark.slow  # ~1.1 s: a real socket server plus a full config-entry setup
@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_end_to_end_with_fake_gateway(hass: HomeAssistant) -> None:
    """Real setup against a loopback OpenWebNet server: no OWNd mock at all.

    Uses the user's configuration (tests/fixtures/myhome.yaml): the connection test,
    the event and command sessions, the dispatcher and the entities are the real
    ones.  Checks a light event, a cover event, an energy totaliser reply read on
    the command session, and the availability transitions on the connection signal.
    """
    light_key, cover_key, meter_key = f"{MAC}-1-11", f"{MAC}-2-81", f"{MAC}-18-51-total-energy"
    replies = {
        "*#1*11##": ["*1*0*11##", "*#*1##"],  # light status: off
        "*#18*51*51##": ["*#18*51*51*12345##", "*#*1##"],  # energy totaliser reply (sc-01)
    }
    async with FakeOWNServer(replies, default_replies=["*#*1##"]) as server:
        entry = make_entry(REAL_CONFIG_PATH, data={**ENTRY_DATA_V2, "host": "127.0.0.1", "port": server.port})
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        registry = er.async_get(hass)
        light_id = registry.async_get_entity_id("light", DOMAIN, light_key)
        cover_id = registry.async_get_entity_id("cover", DOMAIN, cover_key)
        meter_id = registry.async_get_entity_id("sensor", DOMAIN, meter_key)
        assert light_id and cover_id and meter_id

        # Event session up -> SIGNAL_GATEWAY_CONNECTION(True) -> entities available.
        await wait_until(lambda: handler.is_connected)
        await wait_until(lambda: hass.states.get(light_id).state != "unavailable")
        assert "*99*1##" in server.sessions
        assert len(server.monitor_writers) == 1

        # Command session: status requests answered, totaliser reply dispatched.
        await wait_until(lambda: hass.states.get(light_id).state == "off")
        await wait_until(lambda: hass.states.get(meter_id).state == "12345")
        assert "*#18*51*#1200#1*125##" in server.received  # Contract E keep-alive armed
        assert all(session in ("*99*0##", "*99*1##") for session in server.sessions)

        # Monitor frames: light on, cover opening then stopped.
        await server.push("*1*1*11##")
        await wait_until(lambda: hass.states.get(light_id).state == "on")
        await server.push("*2*1*81##")
        await wait_until(lambda: hass.states.get(cover_id).state == "opening")
        await server.push("*2*0*81##")
        await wait_until(lambda: hass.states.get(cover_id).state in ("open", "closed"))
        assert isinstance(hass.states.get(cover_id).attributes.get("current_position"), int)

        # The gateway drops the monitor session: unavailable, then back after the
        # reconnect (initial backoff 1 s) with the last known state.
        # Monitor sessions so far: the connection test (OWNSession.test_connection
        # negotiates a *99*1## session) plus the listening loop's own session.
        monitors_before = server.sessions.count("*99*1##")
        await server.drop_monitors()
        await wait_until(lambda: hass.states.get(light_id).state == "unavailable")
        assert hass.states.get(meter_id).state == "unavailable"
        await wait_until(lambda: handler.is_connected and hass.states.get(light_id).state == "on", timeout=6.0)
        assert hass.states.get(meter_id).state == "12345"
        # Exactly one reconnect, and only one live monitor session at any time.
        assert server.sessions.count("*99*1##") == monitors_before + 1
        assert len(server.monitor_writers) == 1

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED
        await wait_until(lambda: not server.monitor_writers)


# Unique ids of the second (fictional) gateway of tests/fixtures/myhome.yaml, one
# device per platform the main gateway does not use.
SECOND_GATEWAY_ENTITIES: dict[str, tuple[str, ...]] = {
    "light": (f"{MAC2}-1-11", f"{MAC2}-1-12#4#03"),  # dimmable + behind bus interface 3
    "switch": (f"{MAC2}-1-15",),
    "cover": (f"{MAC2}-2-81",),
    "binary_sensor": (f"{MAC2}-25-31-door",),
    "climate": (f"{MAC2}-4-1",),
    "sensor": (f"{MAC2}-4-32-temperature",),
    "event": (f"{MAC2}-cenplus-5-event", f"{MAC2}-cen-51-event"),
    "button": (f"{MAC2}-1-11-disable", f"{MAC2}-1-11-enable"),  # lock_buttons: true
}


@pytest.mark.usefixtures("socket_enabled")  # loopback only; pytest-socket blocks sockets by default
async def test_end_to_end_second_gateway_covers_every_platform(hass: HomeAssistant) -> None:
    """Every shipped platform is set up and driven by real frames, not just three.

    ``test_end_to_end_with_fake_gateway`` above only proves light, cover and the
    WHO 18 sensors, because that is all the main gateway of the fixture declares.
    The second gateway declares one device of each remaining platform, so switch,
    binary_sensor, climate, event (CEN *and* CEN+), button (``lock_buttons``), a
    dimmable light, a light behind a local bus interface and a WHO 4 temperature
    sensor all go through the real setup, the real session and the real
    dispatcher here.

    Pins: the platform list, the unique-id shape of every platform, and the
    routing of a monitor frame to each of them.  Mutations caught: dropping a
    platform from ``PLATFORMS``, and any ``_dispatch_to_entities`` regression that
    stops one message type from reaching its entity (a bug the platform tests
    cannot see, since ``feed_event`` calls ``handle_event`` directly).
    """
    async with FakeOWNServer(default_replies=["*#*1##"]) as server:
        entry = make_entry(
            REAL_CONFIG_PATH,
            data={**ENTRY_DATA_V2, "host": "127.0.0.1", "port": server.port},
            mac=MAC2,
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        handler = hass.data[DOMAIN][MAC2][CONF_ENTITY]

        registry = er.async_get(hass)
        entity_ids: dict[str, str] = {}
        for domain, unique_ids in SECOND_GATEWAY_ENTITIES.items():
            for unique_id in unique_ids:
                entity_id = registry.async_get_entity_id(domain, DOMAIN, unique_id)
                assert entity_id is not None, f"{domain} entity {unique_id} was not created"
                entity_ids[unique_id] = entity_id

        # Nothing was pruned and nothing extra was invented.
        assert {item.unique_id for item in er.async_entries_for_config_entry(registry, entry.entry_id)} == (
            expected_unique_ids(MAC2, hass.data[DOMAIN][MAC2][CONF_PLATFORMS])
        )

        await wait_until(lambda: handler.is_connected)
        light_id = entity_ids[f"{MAC2}-1-11"]
        await wait_until(lambda: hass.states.get(light_id).state != "unavailable")

        # One monitor frame per platform, straight off the fake gateway's bus.
        await server.push("*1*1*11##")  # dimmable light on
        await wait_until(lambda: hass.states.get(light_id).state == "on")

        switch_id = entity_ids[f"{MAC2}-1-15"]
        await server.push("*1*1*15##")
        await wait_until(lambda: hass.states.get(switch_id).state == "on")

        cover_id = entity_ids[f"{MAC2}-2-81"]
        await server.push("*2*1*81##")
        await wait_until(lambda: hass.states.get(cover_id).state == "opening")

        door_id = entity_ids[f"{MAC2}-25-31-door"]
        await server.push("*25*31#31*31##")
        await wait_until(lambda: hass.states.get(door_id).state == "on")

        climate_id = entity_ids[f"{MAC2}-4-1"]
        await server.push("*#4*1*0*0205*3##")  # zone 1 measures 20.5 C
        await wait_until(lambda: hass.states.get(climate_id).attributes.get("current_temperature") == 20.5)

        cenplus_id = entity_ids[f"{MAC2}-cenplus-5-event"]
        await server.push("*25*21#1*25##")  # CEN+ object 5, pushbutton 1, short press
        await wait_until(
            lambda: hass.states.get(cenplus_id).attributes.get("event_type") == "pushbutton_short_press"
        )

        cen_id = entity_ids[f"{MAC2}-cen-51-event"]
        await server.push("*15*1*51##")  # CEN WHERE 51, pushbutton 1, pressed
        await wait_until(
            lambda: hass.states.get(cen_id).attributes.get("event_type") == "pushbutton_short_press"
        )

        # The bus-interface light and the WHO 4 sensor have no state yet, but they
        # follow the gateway's availability like every other entity.
        for unique_id in (f"{MAC2}-1-12#4#03", f"{MAC2}-4-32-temperature"):
            assert hass.states.get(entity_ids[unique_id]).state != "unavailable"

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.NOT_LOADED


async def test_send_message_accepts_frames_ownd_cannot_type(hass: HomeAssistant, tmp_path) -> None:
    """A CEN+ virtual press (WHERE starting with '#') is a valid frame even if OWNd's typed parser crashes on it."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        assert await _setup(hass, entry)
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        before = handler.send_buffer.qsize()
        await hass.services.async_call(DOMAIN, "send_message", {"message": "*25*21#1*#2##"}, blocking=True)
        assert handler.send_buffer.qsize() == before + 1
        with pytest.raises(ServiceValidationError) as err:
            await hass.services.async_call(DOMAIN, "send_message", {"message": "*25*21#1*#2"}, blocking=True)
        assert err.value.translation_key == "invalid_message"


# --------------------------------------------------------------------------- review 2026-09-07
async def test_worker_count_option_is_guarded(hass: HomeAssistant, tmp_path, caplog: pytest.LogCaptureFixture) -> None:
    """A hand-edited option must neither crash the setup nor flood the gateway with sessions."""
    entry = make_entry(write_yaml(tmp_path), options={CONF_WORKER_COUNT: "abc"})
    with mock_gateway():
        assert await _setup(hass, entry)
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        assert len(handler.sending_workers) == 1
        assert "is not a number" in caplog.text
        assert await hass.config_entries.async_unload(entry.entry_id)

    entry = make_entry(write_yaml(tmp_path), options={CONF_WORKER_COUNT: 99}, mac="00:03:50:aa:bb:dd")
    with mock_gateway():
        assert await _setup(hass, entry)
        handler = hass.data[DOMAIN]["00:03:50:aa:bb:dd"][CONF_ENTITY]
        assert len(handler.sending_workers) == MAX_COMMAND_WORKERS
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_failed_platform_unload_is_reported(
    hass: HomeAssistant, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        assert await _setup(hass, entry)
        with patch.object(hass.config_entries, "async_unload_platforms", return_value=False):
            assert await hass.config_entries.async_unload(entry.entry_id) is False
        assert "reload the integration to recover" in caplog.text

