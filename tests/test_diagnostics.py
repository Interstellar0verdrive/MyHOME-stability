"""Tests for the MyHOME diagnostics platform (0.3.0, G1-A).

The gateway handler is the mocked one from ``helpers_core``; ``stats`` and
``recent_frames`` are set by hand to the shape A1 exposes in gateway.py, which is
exactly how diagnostics.py reads them (``getattr`` + duck typing).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
    get_diagnostics_for_device,
)

from custom_components.myhome.const import CONF_ENTITY, CONF_FILE_PATH, DOMAIN
from custom_components.myhome.diagnostics import REDACTED, REDACTED_FRAME, redact_frame
from custom_components.myhome.gateway import FRAME_MONITOR, FRAME_REPLY, FrameRecord

from .helpers_core import (
    ENTRY_DATA_V2,
    HOST,
    MAC,
    PASSWORD,
    make_entry,
    mock_gateway,
    write_yaml,
)

LAST_FRAME_AT = datetime(2026, 9, 5, 10, 11, 12, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class FakeStats:
    """Same fields as the GatewayStats dataclass of the 0.3.0 contract."""

    connected: bool = True
    last_frame_at: datetime | None = LAST_FRAME_AT
    frames_rx: int = 42
    reconnects: int = 2
    commands_sent: int = 7
    commands_dropped: int = 1
    queue_length: int = 0
    session_state: str = "connected"


# 60 frames: only the last 50 are reported, and the two session frames are redacted.
FRAMES: list[str] = [f"*1*1*{index}##" for index in range(56)] + [
    "*99*1##",
    "*#12345678##",  # nonce / password hash of the OPEN negotiation
    "*1*1*11##",
    "*#*1##",
]


# A SHA-1 HMAC session password as OWNd builds it: ``*#<Rb>*<hmac>##``, each half a
# hex digest written two decimal digits per hex character (80 digits for SHA-1).
HMAC_DIGITS = "1234567890" * 8
HMAC_PASSWORD_FRAME = f"*#{HMAC_DIGITS}*{HMAC_DIGITS}##"


MANIFEST_VERSION = json.loads(
    (Path(__file__).resolve().parents[1] / "custom_components" / "myhome" / "manifest.json").read_text()
)["version"]

async def _setup(hass: HomeAssistant, entry: MockConfigEntry):
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
    handler.stats = FakeStats()
    handler.recent_frames = list(FRAMES)
    return handler


async def test_config_entry_diagnostics(hass: HomeAssistant, hass_client, tmp_path) -> None:
    """Content, redaction and the frame ring buffer."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        await _setup(hass, entry)
        data = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    dumped = json.dumps(data)
    # Secrets and identity.
    assert PASSWORD not in dumped
    assert data["entry"]["data"]["password"] == "**REDACTED**"
    assert data["entry"]["data"]["mac"].startswith("00:03:50")
    assert data["entry"]["data"]["mac"].endswith(REDACTED)
    assert MAC not in dumped
    # Only the first two octets survive (they help read routing problems).
    assert data["entry"]["data"]["host"] == "192.0.x.x"
    assert HOST not in dumped
    assert data["entry"]["unique_id"].endswith(REDACTED)

    # Versions.
    assert data["versions"]["ownd"].startswith("0.7.")
    assert data["versions"]["home_assistant"]
    assert data["versions"]["myhome"] == MANIFEST_VERSION

    # Effective tunables (nothing set -> the 0.2.x values).
    assert data["effective_options"]["config_file_name"] == "myhome.yaml"
    assert data["effective_options"]["idle_watchdog_sec"] == 300
    assert data["effective_options"]["probe_window_sec"] == 30
    assert data["effective_options"]["command_timeout_sec"] == 10
    assert data["effective_options"]["queue_ttl_sec"] == 60
    assert data["effective_options"]["default_keepalive_minutes"] == 125

    # Config summary: counts and device keys, never the user's device names.
    assert data["config"]["device_count"] == 3  # light + cover + generated lock buttons
    assert data["config"]["platforms"]["light"] == {"count": 1, "device_keys": ["1-11"]}
    assert data["config"]["platforms"]["cover"] == {"count": 1, "device_keys": ["2-81"]}
    assert data["config"]["platforms"]["button"]["count"] == 1
    assert "Light Test" not in dumped
    assert "Cover Test" not in dumped

    # Handler stats and session parameters.
    handler = data["handler"]
    assert handler["loaded"] is True
    assert handler["stats"] == {
        "connected": True,
        "last_frame_at": LAST_FRAME_AT.isoformat(),
        "frames_rx": 42,
        "reconnects": 2,
        "commands_sent": 7,
        "commands_dropped": 1,
        "queue_length": 0,
        "session_state": "connected",
    }
    assert handler["session_parameters"]["idle_watchdog_sec"] == 300.0
    assert handler["session_parameters"]["command_timeout_sec"] == 10.0
    assert isinstance(handler["queue_size"], int)

    # Ring buffer: last 50, session frames replaced by a marker.
    frames = data["recent_frames"]
    assert len(frames) == 50
    assert frames[-4:] == [REDACTED_FRAME, REDACTED_FRAME, "*1*1*11##", "*#*1##"]
    assert "12345678" not in dumped


async def test_config_entry_diagnostics_reads_the_real_handler(hass: HomeAssistant, hass_client, tmp_path) -> None:
    """Without any hand-written stats the real GatewayStats snapshot is serialised."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        data = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    stats = data["handler"]["stats"]
    assert set(stats) == {
        "connected",
        "last_frame_at",
        "frames_rx",
        "reconnects",
        "commands_sent",
        "commands_dropped",
        "queue_length",
        "session_state",
    }
    assert stats["session_state"] == "disconnected"  # the loops are mocked out
    assert isinstance(data["recent_frames"], list)


async def test_diagnostics_survive_a_handler_without_the_new_attributes(
    hass: HomeAssistant, hass_client, tmp_path
) -> None:
    """diagnostics.py must never be the reason a bug report cannot be produced."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        handler = await _setup(hass, entry)
        handler.stats = None
        handler.recent_frames = None
        data = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert data["handler"]["loaded"] is True
    assert data["handler"]["stats"] is None
    assert data["recent_frames"] == []


async def test_device_diagnostics(hass: HomeAssistant, hass_client, tmp_path) -> None:
    """The device download adds the per-device validated config."""
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        await _setup(hass, entry)
        device_registry = dr.async_get(hass)

        light_device = device_registry.async_get_device_by_identifier((DOMAIN, f"{MAC}-1-11"), entry.entry_id)
        assert light_device is not None
        data = await get_diagnostics_for_device(hass, hass_client, entry, light_device)
        assert data["device"]["is_gateway"] is False
        assert data["device"]["device_keys"] == ["1-11"]
        light_config = data["device"]["config"]["light.1-11"]
        assert light_config["where"] == "11"
        # The device's own name is a free-form string the user wrote (usually a room
        # or a family name); the docs promise it is never in the download.
        assert light_config["name"] == REDACTED
        assert "Light Test" not in json.dumps(data)
        assert light_config["dimmable"] is False
        assert "entities" not in light_config  # live entity objects are never dumped
        # The shared sections are still there.
        assert data["config"]["platforms"]["light"]["count"] == 1
        assert len(data["recent_frames"]) == 50

        gateway_device = device_registry.async_get_device_by_identifier((DOMAIN, MAC), entry.entry_id)
        gateway_data = await get_diagnostics_for_device(hass, hass_client, entry, gateway_device)
        assert gateway_data["device"]["is_gateway"] is True
        assert gateway_data["device"]["config"] == {}


async def test_recent_frames_are_redacted_through_the_real_record_type(
    hass: HomeAssistant, hass_client, tmp_path
) -> None:
    """The ring buffer holds ``FrameRecord`` dataclasses, not strings.

    Feeding diagnostics the real type is the only way to exercise ``_jsonable``'s
    dataclass branch, which is what redacts the session-negotiation frames in
    production; with a ``list[str]`` the test takes the ``str`` fast path instead, and
    a broken dataclass branch would dump ``repr(FrameRecord(...))`` -- password hash
    included -- with the suite still green.
    """
    entry = make_entry(write_yaml(tmp_path))
    with mock_gateway():
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        handler.recent_frames.extend(
            [
                FrameRecord(FRAME_MONITOR, "*1*1*11##", LAST_FRAME_AT),
                FrameRecord(FRAME_REPLY, "*#12345678##", LAST_FRAME_AT),  # legacy nonce
                FrameRecord(FRAME_REPLY, HMAC_PASSWORD_FRAME, LAST_FRAME_AT),  # HMAC
                FrameRecord(FRAME_REPLY, "*99*1##", LAST_FRAME_AT),
            ]
        )
        data = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    frames = data["recent_frames"]
    assert [item["direction"] for item in frames] == [
        FRAME_MONITOR,
        FRAME_REPLY,
        FRAME_REPLY,
        FRAME_REPLY,
    ]
    assert [item["frame"] for item in frames] == [
        "*1*1*11##",
        REDACTED_FRAME,
        REDACTED_FRAME,
        REDACTED_FRAME,
    ]
    assert all(item["at"] == LAST_FRAME_AT.isoformat() for item in frames)
    dumped = json.dumps(data)
    assert "12345678" not in dumped
    assert HMAC_DIGITS not in dumped


def test_the_hmac_password_frame_is_redacted_but_a_status_request_is_not() -> None:
    """OWNd sends two shapes of password frame; only one used to be recognised.

    ``*#<Rb>*<hmac>##`` (SHA-1/SHA-256, what a modern gateway negotiates) has a ``*``
    between the two numbers, which the legacy ``*#<hash>##`` pattern never matched.
    Widening the pattern must not swallow an ordinary dimension request, which has
    the very same shape with short numbers.
    """
    assert redact_frame(HMAC_PASSWORD_FRAME) == REDACTED_FRAME
    assert redact_frame("*#12345678##") == REDACTED_FRAME
    assert redact_frame("*99*1##") == REDACTED_FRAME
    for kept in ("*#1*11##", "*#4*1*0*0235##", "*#18*51*113##", "*#*1##", "*1*1*11##"):
        assert redact_frame(kept) == kept


async def test_the_config_file_path_never_carries_the_directory(
    hass: HomeAssistant, hass_client, tmp_path
) -> None:
    """A container / core install points the option at a home directory: mask it.

    ``/home/<user>/...`` is more identifying than the MAC octets that *are* masked
    next to it, and the file name is all a bug report needs.
    """
    directory = tmp_path / "fictional_user"
    directory.mkdir()
    entry = make_entry(write_yaml(directory))
    with mock_gateway():
        await _setup(hass, entry)
        data = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    dumped = json.dumps(data)
    assert "fictional_user" not in dumped
    assert data["effective_options"]["config_file_name"] == "myhome.yaml"
    assert data["effective_options"]["config_file_is_default_location"] is False
    assert data["entry"]["options"][CONF_FILE_PATH] == "myhome.yaml"


@pytest.mark.parametrize("host", ["gateway.lan", "fd00::1"])
async def test_a_non_ipv4_host_is_masked_too(
    hass: HomeAssistant, hass_client, tmp_path, host: str
) -> None:
    """Only the IPv4 branch of ``_redact_host`` was ever exercised by the suite."""
    entry = make_entry(write_yaml(tmp_path), data={**ENTRY_DATA_V2, "host": host})
    with mock_gateway():
        await _setup(hass, entry)
        data = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert host not in json.dumps(data)
    assert data["entry"]["data"]["host"].endswith(REDACTED)
