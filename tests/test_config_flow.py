"""Tests for the MyHOME config flow, SSDP flow, reauth and options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers.service_info.ssdp import SsdpServiceInfo

from custom_components.myhome.config_flow import MANUAL_ENTRY, validate_host
from custom_components.myhome.const import (
    CONF_COMMAND_TIMEOUT_SEC,
    CONF_DEFAULT_KEEPALIVE_MINUTES,
    CONF_FILE_PATH,
    CONF_GENERATE_EVENTS,
    CONF_IDLE_WATCHDOG_SEC,
    CONF_OWN_PASSWORD,
    CONF_PROBE_WINDOW_SEC,
    CONF_QUEUE_TTL_SEC,
    CONF_WORKER_COUNT,
    DEFAULT_COMMAND_TIMEOUT_SEC,
    DEFAULT_IDLE_WATCHDOG_SEC,
    DEFAULT_KEEPALIVE_MINUTES,
    DEFAULT_PROBE_WINDOW_SEC,
    DEFAULT_QUEUE_TTL_SEC,
    DOMAIN,
    MAX_COMMAND_WORKERS,
)

from .helpers_core import ENTRY_DATA_V2, HOST, MAC, PASSWORD, TEST_OK, make_entry, write_yaml

CUSTOM_INPUT = {"address": HOST, "port": 20000, "serialNumber": "00-03-50-AA-BB-CC", "modelName": "MyHOMEServer1"}


@pytest.fixture(autouse=True)
def no_ssdp_discovery():
    """OWNd multicast discovery is never run in tests."""
    with patch("custom_components.myhome.config_flow.find_gateways", AsyncMock(return_value=[])) as mock:
        yield mock


@pytest.fixture(autouse=True)
def no_port_lookup():
    """The gateway's description.xml is never fetched in tests.

    ``get_port`` was patched only inside the two SSDP happy-path tests, so any
    regression letting another test reach ``ssdp_confirm`` would have issued a real
    HTTP request from the suite.  Tests that care about the port patch it themselves;
    their ``with patch(...)`` wins over this one.
    """
    with patch("custom_components.myhome.config_flow.get_port", AsyncMock(return_value=None)) as mock:
        yield mock


@pytest.fixture
def mock_test_connection():
    """Mock OWNSession.test_connection used by the flow."""
    session = MagicMock()
    session.test_connection = AsyncMock(return_value=TEST_OK)
    with patch("custom_components.myhome.config_flow.OWNSession", return_value=session):
        yield session.test_connection


@pytest.fixture
def mock_setup_entry():
    with (
        patch("custom_components.myhome.async_setup_entry", AsyncMock(return_value=True)) as setup,
        patch("custom_components.myhome.async_unload_entry", AsyncMock(return_value=True)),
    ):
        yield setup


def test_validate_host() -> None:
    assert validate_host(" 192.168.1.5 ") == "192.168.1.5"
    assert validate_host("fe80::1") == "fe80::1"
    assert validate_host("gateway.local") == "gateway.local"
    for bad in ("", "192.168.1.300", "bad host", "-x.local"):
        with pytest.raises(ValueError):
            validate_host(bad)


async def _start_manual(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"serial": MANUAL_ENTRY})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "custom"
    return result


async def test_manual_flow_creates_entry(hass: HomeAssistant, mock_test_connection, mock_setup_entry) -> None:
    """cf-03: plain values in entry data; cf-04: errors are not sticky."""
    result = await _start_manual(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**CUSTOM_INPUT, "address": "192.168.1.300"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"address": "invalid_host"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**CUSTOM_INPUT, "serialNumber": "nope"})
    assert result["errors"] == {"serialNumber": "invalid_mac"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], CUSTOM_INPUT)
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "MyHOMEServer1 Gateway"
    data = result["data"]
    assert data["mac"] == MAC
    assert data[CONF_HOST] == HOST
    assert data[CONF_PORT] == 20000
    assert data["manufacturer"] == "BTicino S.p.A."
    assert data["firmware"] is None
    assert data["ssdp_location"] is None
    assert not any(isinstance(value, (list, tuple)) for value in data.values())
    assert result["options"] == {CONF_WORKER_COUNT: 1}
    assert result["result"].unique_id == MAC
    assert result["result"].version == 2
    assert mock_test_connection.await_count == 1


async def test_manual_flow_password_required(hass: HomeAssistant, mock_test_connection, mock_setup_entry) -> None:
    mock_test_connection.side_effect = [
        {"Success": False, "Message": "password_required"},
        {"Success": False, "Message": "password_error"},
        TEST_OK,
    ]
    result = await _start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CUSTOM_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "password"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "wrong"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "password"
    assert result["errors"] == {"password": "password_error"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": PASSWORD})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PASSWORD] == PASSWORD


async def test_manual_flow_cannot_connect(hass: HomeAssistant, mock_test_connection) -> None:
    """cf-07: None / OSError -> back to the form with cannot_connect."""
    mock_test_connection.side_effect = [
        None,
        OSError("unreachable"),
        {"Success": False, "Message": "negotiation_refused"},
    ]
    result = await _start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CUSTOM_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "custom"
    assert result["errors"] == {"base": "cannot_connect"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], CUSTOM_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], CUSTOM_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "negotiation_refused"


async def test_manual_flow_already_configured(
    hass: HomeAssistant, mock_test_connection, mock_setup_entry, tmp_path
) -> None:
    """cf-09: re-adding the gateway aborts and only refreshes the host."""
    entry = make_entry(write_yaml(tmp_path))
    entry.add_to_hass(hass)
    result = await _start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {**CUSTOM_INPUT, "address": "10.0.0.9"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "10.0.0.9"
    assert mock_test_connection.await_count == 0


async def test_user_flow_discovered_gateway(
    hass: HomeAssistant, no_ssdp_discovery, mock_test_connection, mock_setup_entry
) -> None:
    no_ssdp_discovery.return_value = [
        {
            "address": HOST,
            "port": 20000,
            "serialNumber": "00:03:50:AA:BB:CC",
            "modelName": "MyHomeServer1",
            "modelNumber": "2.1.0",
            "manufacturer": "BTicino S.p.A.",
            "manufacturerURL": "http://www.bticino.it",
            "friendlyName": "MyHOMEServer1",
            "deviceType": "urn:schemas-upnp-org:device:Basic:1",
            "UDN": "uuid:1234",
            "ssdp_location": f"http://{HOST}:49152/description.xml",
            "ssdp_st": "upnp:rootdevice",
        }
    ]
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"serial": "00:03:50:AA:BB:CC"})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["mac"] == MAC
    assert result["data"]["firmware"] == "2.1.0"
    assert result["data"][CONF_PORT] == 20000
    assert result["result"].unique_id == MAC


def _ssdp_info(serial: str = "00:03:50:AA:BB:CC") -> SsdpServiceInfo:
    return SsdpServiceInfo(
        ssdp_usn="uuid:1234::upnp:rootdevice",
        ssdp_st="upnp:rootdevice",
        ssdp_location=f"http://{HOST}:49152/description.xml",
        ssdp_headers={"_host": HOST},
        upnp={
            "serialNumber": serial,
            "modelName": "MyHomeServer1",
            "modelNumber": "2.1.0",
            "manufacturer": "BTicino S.p.A.",
            "friendlyName": "MyHOMEServer1",
            "UDN": "uuid:1234",
        },
    )


async def test_ssdp_flow(hass: HomeAssistant, mock_test_connection, mock_setup_entry) -> None:
    """cf-08 / cf-14: confirm step, real port lookup, no hard-coded 20000."""
    with patch("custom_components.myhome.config_flow.get_port", AsyncMock(return_value=20001)):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=_ssdp_info()
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "ssdp_confirm"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == 20001
    assert result["data"][CONF_HOST] == HOST
    assert result["data"]["mac"] == MAC
    assert result["data"]["firmware"] == "2.1.0"


async def test_ssdp_flow_port_lookup_fails(hass: HomeAssistant, mock_test_connection, mock_setup_entry) -> None:
    with patch("custom_components.myhome.config_flow.get_port", AsyncMock(side_effect=OSError("boom"))):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=_ssdp_info()
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "port"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PORT: 20002})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == 20002


async def test_ssdp_already_configured_keeps_custom_port(hass: HomeAssistant, mock_setup_entry, tmp_path) -> None:
    entry = make_entry(write_yaml(tmp_path), data={**ENTRY_DATA_V2, CONF_PORT: 20123, CONF_HOST: "10.0.0.1"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=_ssdp_info()
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_PORT] == 20123
    assert entry.data[CONF_HOST] == HOST


async def test_ssdp_without_serial_aborts(hass: HomeAssistant) -> None:
    info = _ssdp_info()
    info.upnp = {"modelName": "MyHomeServer1"}
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=info
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_serial"


async def test_reauth_flow(hass: HomeAssistant, mock_test_connection, mock_setup_entry, tmp_path) -> None:
    """cf-02: reauth uses the entry from the context and updates the password."""
    entry = make_entry(write_yaml(tmp_path))
    entry.add_to_hass(hass)
    entry.async_start_reauth(hass)
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"

    mock_test_connection.side_effect = [{"Success": False, "Message": "password_error"}, TEST_OK]
    result = await hass.config_entries.flow.async_configure(flows[0]["flow_id"], {"password": "bad"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"password": "password_error"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "54321"})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "54321"
    assert entry.data[CONF_HOST] == HOST
    assert mock_setup_entry.await_count == 1  # reloaded once


async def test_reauth_against_an_unreachable_gateway(
    hass: HomeAssistant, mock_test_connection, mock_setup_entry, tmp_path
) -> None:
    """cf-07 for the reauth path: the user must land back on the password form.

    This is the path someone hits after changing the gateway password while the
    gateway is also unreachable; aborting instead would leave them with no form to
    correct anything in.
    """
    entry = make_entry(write_yaml(tmp_path))
    entry.add_to_hass(hass)
    entry.async_start_reauth(hass)
    await hass.async_block_till_done()
    flow = hass.config_entries.flow.async_progress_by_handler(DOMAIN)[0]

    mock_test_connection.side_effect = [None]
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"password": "54321"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_legacy_open_auth_asks_for_a_numeric_password(
    hass: HomeAssistant, mock_test_connection, mock_setup_entry
) -> None:
    """cf-13: OWNd raises ValueError when the nonce algorithm gets a non-numeric password."""
    mock_test_connection.side_effect = [ValueError("not numeric"), TEST_OK]
    result = await _start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CUSTOM_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "password"
    assert result["errors"] == {"password": "password_numeric"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": PASSWORD})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_a_discovered_gateway_without_a_port_asks_for_one(
    hass: HomeAssistant, no_ssdp_discovery, mock_test_connection, mock_setup_entry
) -> None:
    """OWNd multicast discovery does not always report the OpenWebNet port."""
    no_ssdp_discovery.return_value = [
        {
            "address": HOST,
            "port": None,
            "serialNumber": "00:03:50:AA:BB:CC",
            "modelName": "MyHomeServer1",
            "manufacturer": "BTicino S.p.A.",
        }
    ]
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"serial": "00:03:50:AA:BB:CC"})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "port"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PORT: 20005})
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == 20005


async def test_discovery_never_raises(hass: HomeAssistant, no_ssdp_discovery, mock_test_connection) -> None:
    """cf-16: a failing multicast discovery must still show the manual-entry form."""
    no_ssdp_discovery.side_effect = OSError("no route to host")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    # Only the "Custom" entry is offered, and it still works.
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"serial": MANUAL_ENTRY})
    assert result["step_id"] == "custom"


async def test_ssdp_takes_the_host_from_the_location_when_the_header_is_missing(
    hass: HomeAssistant, mock_test_connection, mock_setup_entry
) -> None:
    """``_host`` is a convenience header; the location URL is the real source."""
    info = _ssdp_info()
    info.ssdp_headers = {}
    with patch("custom_components.myhome.config_flow.get_port", AsyncMock(return_value=20001)):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_SSDP}, data=info
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == HOST


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("connection_refused", "cannot_connect"),
        ("negotiation_refused", "negotiation_refused"),
        ("negociation_error", "negotiation_error"),  # OWNd's own spelling
        ("negotiation_failed", "negotiation_failed"),
        ("something_new", "unknown"),
    ],
)
async def test_every_ownd_failure_message_maps_to_an_abort_reason(
    hass: HomeAssistant, mock_test_connection, message: str, reason: str
) -> None:
    """The keys are OWNd's strings, typo included: pin them, they are not ours.

    Only ``negotiation_refused`` was asserted, so a renamed OWNd message would have
    silently degraded every abort to "unknown" with the suite green.
    """
    mock_test_connection.side_effect = [{"Success": False, "Message": message}]
    result = await _start_manual(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], CUSTOM_INPUT)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


def _suggested(result) -> dict:
    """Suggested values of the tunable number selectors shown by the options form."""
    keys = (
        CONF_IDLE_WATCHDOG_SEC,
        CONF_PROBE_WINDOW_SEC,
        CONF_COMMAND_TIMEOUT_SEC,
        CONF_QUEUE_TTL_SEC,
        CONF_DEFAULT_KEEPALIVE_MINUTES,
    )
    suggested = {}
    for marker in result["data_schema"].schema:
        name = getattr(marker, "schema", marker)
        if name in keys:
            suggested[name] = (marker.description or {}).get("suggested_value")
    return suggested


async def test_options_flow(hass: HomeAssistant, mock_setup_entry, tmp_path) -> None:
    """cf-01 / cf-10 / core-09: options flow opens, validates and reloads."""
    path = write_yaml(tmp_path)
    entry = make_entry(path)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert mock_setup_entry.await_count == 1

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    # G1-D: unset tunables are pre-filled with the values 0.2.x used internally.
    assert _suggested(result) == {
        CONF_IDLE_WATCHDOG_SEC: DEFAULT_IDLE_WATCHDOG_SEC,
        CONF_PROBE_WINDOW_SEC: DEFAULT_PROBE_WINDOW_SEC,
        CONF_COMMAND_TIMEOUT_SEC: DEFAULT_COMMAND_TIMEOUT_SEC,
        CONF_QUEUE_TTL_SEC: DEFAULT_QUEUE_TTL_SEC,
        CONF_DEFAULT_KEEPALIVE_MINUTES: DEFAULT_KEEPALIVE_MINUTES,
    }

    good = {
        "address": HOST,
        CONF_PORT: 20000,
        "password": PASSWORD,
        CONF_FILE_PATH: str(path),
        CONF_WORKER_COUNT: 2,
        CONF_GENERATE_EVENTS: True,
        # NumberSelector hands floats back to the flow.
        CONF_IDLE_WATCHDOG_SEC: 120.0,
        CONF_PROBE_WINDOW_SEC: 15.0,
        CONF_COMMAND_TIMEOUT_SEC: 5.0,
        CONF_QUEUE_TTL_SEC: 30.0,
        CONF_DEFAULT_KEEPALIVE_MINUTES: 0.0,
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**good, CONF_FILE_PATH: str(tmp_path / "nope.yaml")}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_FILE_PATH: "invalid_config_path"}

    result = await hass.config_entries.options.async_configure(result["flow_id"], {**good, "address": "not valid!"})
    assert result["errors"] == {"address": "invalid_host"}

    result = await hass.config_entries.options.async_configure(result["flow_id"], good)
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        CONF_WORKER_COUNT: 2,
        CONF_FILE_PATH: str(path),
        CONF_GENERATE_EVENTS: True,
        CONF_IDLE_WATCHDOG_SEC: 120,
        CONF_PROBE_WINDOW_SEC: 15,
        CONF_COMMAND_TIMEOUT_SEC: 5,
        CONF_QUEUE_TTL_SEC: 30,
        CONF_DEFAULT_KEEPALIVE_MINUTES: 0,
    }
    # The floats of the selector are stored as ints for the handler / sensors.
    assert all(isinstance(entry.options[key], int) for key in (CONF_IDLE_WATCHDOG_SEC, CONF_DEFAULT_KEEPALIVE_MINUTES))
    assert mock_setup_entry.await_count == 2  # OptionsFlowWithReload reloaded the entry

    # Only the connection data changes -> still exactly one reload.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert _suggested(result)[CONF_IDLE_WATCHDOG_SEC] == 120
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**good, "address": "10.0.0.2", "password": "999"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_HOST] == "10.0.0.2"
    assert entry.data[CONF_PASSWORD] == "999"
    assert mock_setup_entry.await_count == 3


async def test_options_flow_refuses_more_workers_than_the_setup_will_start(
    hass: HomeAssistant, mock_setup_entry, tmp_path
) -> None:
    """The form's range and the runtime clamp must be the same number.

    ``__init__.async_setup_entry`` clamps the worker count to MAX_COMMAND_WORKERS, so
    a form that accepted 1-10 let a user save 8, read 8 back at every visit and run 4,
    with nothing anywhere saying so.
    """
    path = write_yaml(tmp_path)
    entry = make_entry(path)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    submission = {
        "address": HOST,
        CONF_PORT: 20000,
        "password": PASSWORD,
        CONF_FILE_PATH: str(path),
        CONF_GENERATE_EVENTS: False,
        CONF_IDLE_WATCHDOG_SEC: float(DEFAULT_IDLE_WATCHDOG_SEC),
        CONF_PROBE_WINDOW_SEC: float(DEFAULT_PROBE_WINDOW_SEC),
        CONF_COMMAND_TIMEOUT_SEC: float(DEFAULT_COMMAND_TIMEOUT_SEC),
        CONF_QUEUE_TTL_SEC: float(DEFAULT_QUEUE_TTL_SEC),
        CONF_DEFAULT_KEEPALIVE_MINUTES: float(DEFAULT_KEEPALIVE_MINUTES),
    }
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"], {**submission, CONF_WORKER_COUNT: MAX_COMMAND_WORKERS + 1}
        )

    # The top of the range is still accepted.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**submission, CONF_WORKER_COUNT: MAX_COMMAND_WORKERS}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_WORKER_COUNT] == MAX_COMMAND_WORKERS


async def test_options_flow_keeps_no_password_as_none(hass: HomeAssistant, mock_setup_entry, tmp_path) -> None:
    """A gateway configured without a password must not gain an empty-string one.

    The password field is Required and pre-filled with "", so opening the options
    dialog and pressing Submit used to rewrite None into "".  OWNd treats the two
    differently: None makes it ask for a password (which surfaces as our reauth
    flow), "" makes it hash the empty string and report "Invalid password".
    """
    path = write_yaml(tmp_path)
    entry = make_entry(path, data={**ENTRY_DATA_V2, CONF_PASSWORD: None})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)

    # The *read* half of the same problem: the form must suggest "" and not None.
    # A selector rendered from None shows the literal string "None", so a user who
    # opens the dialog and presses Submit stores "None" as the gateway password and
    # locks themselves out. Mutation caught: `entry.data.get(CONF_PASSWORD) or ""`
    # -> `entry.data.get(CONF_PASSWORD)`.
    password_key = next(key for key in result["data_schema"].schema if key == CONF_OWN_PASSWORD)
    assert password_key.description["suggested_value"] == ""

    unchanged = {
        "address": HOST,
        CONF_PORT: 20000,
        "password": "",  # what the pre-filled form hands back untouched
        CONF_FILE_PATH: str(path),
        CONF_WORKER_COUNT: 1,
        CONF_GENERATE_EVENTS: False,
        CONF_IDLE_WATCHDOG_SEC: float(DEFAULT_IDLE_WATCHDOG_SEC),
        CONF_PROBE_WINDOW_SEC: float(DEFAULT_PROBE_WINDOW_SEC),
        CONF_COMMAND_TIMEOUT_SEC: float(DEFAULT_COMMAND_TIMEOUT_SEC),
        CONF_QUEUE_TTL_SEC: float(DEFAULT_QUEUE_TTL_SEC),
        CONF_DEFAULT_KEEPALIVE_MINUTES: float(DEFAULT_KEEPALIVE_MINUTES),
    }
    result = await hass.config_entries.options.async_configure(result["flow_id"], unchanged)
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data[CONF_PASSWORD] is None
