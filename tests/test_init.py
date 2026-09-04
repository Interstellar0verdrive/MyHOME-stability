"""Tests for the MyHOME config entry lifecycle (Contract D)."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.myhome import normalise_entry_data
from custom_components.myhome.const import CONF_ENTITY, CONF_FILE_PATH, DOMAIN

from .helpers_core import (
    ENTRY_DATA_V2,
    LEGACY_ENTRY_DATA_V1,
    MAC,
    MAC2,
    make_entry,
    mock_gateway,
    write_yaml,
)

SERVICES = ("sync_time", "send_message", "start_discovery", "stop_discovery")


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

        light = entity_registry.async_get("light.luce_test")
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

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert MAC not in hass.data[DOMAIN]
    assert handler.listening_worker is None
    assert handler.sending_workers == []
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

    path = write_yaml(tmp_path, "gateway:\n  mac: 00:03:50:a4:a5:a5\n  light:\n    a: {where: '11', name: A}\n    b: {where: '11', name: B}\n")
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
    assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)


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


async def test_services_validation(hass: HomeAssistant, tmp_path) -> None:
    """core-07: schemas, ServiceValidationError, optional gateway."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        assert await _setup(hass, entry)
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]

        before = handler.send_buffer.qsize()
        await hass.services.async_call(DOMAIN, "sync_time", {}, blocking=True)
        assert handler.send_buffer.qsize() == before + 1

        await hass.services.async_call(DOMAIN, "send_message", {"gateway": "00-03-50-A4-A5-A5", "message": "*1*0*11##"}, blocking=True)
        assert handler.send_buffer.qsize() == before + 2

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(DOMAIN, "send_message", {"message": "not a frame"}, blocking=True)
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(DOMAIN, "send_message", {"gateway": "zz", "message": "*1*0*11##"}, blocking=True)
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(DOMAIN, "sync_time", {"gateway": MAC2}, blocking=True)
        with pytest.raises(Exception):  # vol.Invalid from the service schema (non-string message)
            await hass.services.async_call(DOMAIN, "send_message", {"message": 1}, blocking=True)


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

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(DOMAIN, "sync_time", {}, blocking=True)
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
