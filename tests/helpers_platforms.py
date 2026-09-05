"""Shared helpers for the platform tests (light / switch / cover / button / binary_sensor).

The integration is set up exactly as in ``test_init.py`` (OWNd mocked, idle loops), with
``MyHOMEGatewayHandler.send`` / ``send_status_request`` replaced by recorders so the
tests can assert the OpenWebNet frames each platform produces.
"""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from OWNd.message import OWNEvent, OWNMessage

from custom_components.myhome.const import (
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_PLATFORMS,
    DOMAIN,
    GATEWAY_DIAG_SUFFIXES,
    SIGNAL_GATEWAY_CONNECTION,
    SIGNAL_GATEWAY_STATS,
)

from .helpers_core import MAC, make_entry, mock_gateway, write_yaml

# Redacted copy of the user's real /config/myhome.yaml (20 lights, 12 covers, 3 power
# meters, no duplicate WHERE).
REAL_CONFIG_PATH = Path(__file__).resolve().parent / "fixtures" / "myhome.yaml"


def real_config_yaml() -> str:
    """The user's real configuration (tests/fixtures/myhome.yaml)."""
    return REAL_CONFIG_PATH.read_text(encoding="utf-8")


class Commands:
    """Frames sent by the platforms during a test."""

    def __init__(self) -> None:
        self.sent: list[OWNMessage] = []
        self.status: list[OWNMessage] = []

    @property
    def sent_frames(self) -> list[str]:
        return [str(message) for message in self.sent]

    @property
    def status_frames(self) -> list[str]:
        return [str(message) for message in self.status]

    def clear(self) -> None:
        self.sent.clear()
        self.status.clear()


@contextmanager
def mock_commands() -> Iterator[Commands]:
    """Record everything the entities send through the gateway handler."""
    commands = Commands()

    async def _send(self: Any, message: OWNMessage) -> bool:
        commands.sent.append(message)
        return True

    async def _send_status_request(self: Any, message: OWNMessage) -> bool:
        commands.status.append(message)
        return True

    with (
        patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send", _send),
        patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.send_status_request", _send_status_request),
    ):
        yield commands


async def set_connected(hass: HomeAssistant, connected: bool) -> None:
    """Flip the gateway connection state and fire the availability signal."""
    hass.data[DOMAIN][MAC][CONF_ENTITY].is_connected = connected
    async_dispatcher_send(hass, SIGNAL_GATEWAY_CONNECTION.format(mac=MAC), connected)
    await hass.async_block_till_done()


@asynccontextmanager
async def setup_myhome(
    hass: HomeAssistant,
    tmp_path: Path,
    yaml_text: str,
    *,
    connected: bool = True,
    clear_commands: bool = True,
) -> AsyncIterator[tuple[MockConfigEntry, Commands]]:
    """Set up the integration with ``yaml_text`` and yield the entry and the recorder."""
    entry = make_entry(write_yaml(tmp_path, yaml_text))
    with mock_gateway(), mock_commands() as commands:
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        if connected:
            await set_connected(hass, True)
        if clear_commands:
            commands.clear()
        yield entry, commands


def device_config(hass: HomeAssistant, platform: str, device_key: str) -> dict[str, Any]:
    """Validated configuration of one device."""
    return hass.data[DOMAIN][MAC][CONF_PLATFORMS][platform][device_key]


def entity_object(hass: HomeAssistant, platform: str, device_key: str, slot: str | None = None):
    """The entity instance a platform registered in ``hass.data``."""
    return device_config(hass, platform, device_key)[CONF_ENTITIES][slot or platform]


async def feed_event(hass: HomeAssistant, entity, frame: str) -> None:
    """Dispatch a bus frame to one entity, the way gateway.listening_loop does."""
    message = OWNEvent.parse(frame)
    assert message is not None, frame
    entity.handle_event(message)
    await hass.async_block_till_done()


# --------------------------------------------------------------- gateway diagnostics
# Unique ids of the five diagnostic entities of the gateway device (0.3.0, plan G1-B).
GATEWAY_DIAG_UNIQUE_IDS = {f"{MAC}-{suffix}" for suffix in GATEWAY_DIAG_SUFFIXES}


@dataclass(frozen=True)
class FakeGatewayStats:
    """Stand-in for ``gateway.GatewayStats`` (same field names, A1 owns the real one).

    The entities only read attributes off the published snapshot, so the tests can
    dispatch this dataclass without depending on the gateway implementation.
    """

    connected: bool = False
    last_frame_at: datetime | None = None
    frames_rx: int = 0
    reconnects: int = 0
    commands_sent: int = 0
    commands_dropped: int = 0
    queue_length: int = 0
    session_state: str = "disconnected"


async def dispatch_stats(hass: HomeAssistant, **fields: Any) -> FakeGatewayStats:
    """Publish a stats snapshot the way the gateway handler does."""
    stats = FakeGatewayStats(**fields)
    async_dispatcher_send(hass, SIGNAL_GATEWAY_STATS.format(mac=MAC), stats)
    await hass.async_block_till_done()
    return stats


def diagnostic_entity_id(hass: HomeAssistant, domain: str, suffix: str) -> str | None:
    """Entity id of one gateway diagnostic entity (its name comes from a translation)."""
    return er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{MAC}-{suffix}")
