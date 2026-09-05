"""Tests for the MyHOME diagnostics platform (0.3.0, G1-A).

The gateway handler is the mocked one from ``helpers_core``; ``stats`` and
``recent_frames`` are set by hand to the shape A1 exposes in gateway.py, which is
exactly how diagnostics.py reads them (``getattr`` + duck typing).
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass
from datetime import UTC, datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
    get_diagnostics_for_device,
)

from custom_components.myhome.const import CONF_ENTITY, DOMAIN
from custom_components.myhome.diagnostics import REDACTED, REDACTED_FRAME

from .helpers_core import HOST, MAC, PASSWORD, make_entry, mock_gateway, write_yaml

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
    assert data["entry"]["data"]["host"] == "192.168.x.x"
    assert HOST not in dumped
    assert data["entry"]["unique_id"].endswith(REDACTED)

    # Versions.
    assert data["versions"]["ownd"].startswith("0.7.")
    assert data["versions"]["home_assistant"]
    assert data["versions"]["myhome"] == MANIFEST_VERSION

    # Effective tunables (nothing set -> the 0.2.x values).
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
    assert "Luce Test" not in dumped
    assert "Tapparella Test" not in dumped

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
        assert light_config["name"] == "Luce Test"
        assert light_config["dimmable"] is False
        assert "entities" not in light_config  # live entity objects are never dumped
        # The shared sections are still there.
        assert data["config"]["platforms"]["light"]["count"] == 1
        assert len(data["recent_frames"]) == 50

        gateway_device = device_registry.async_get_device_by_identifier((DOMAIN, MAC), entry.entry_id)
        gateway_data = await get_diagnostics_for_device(hass, hass_client, entry, gateway_device)
        assert gateway_data["device"]["is_gateway"] is True
        assert gateway_data["device"]["config"] == {}
