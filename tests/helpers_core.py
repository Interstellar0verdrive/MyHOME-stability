"""Shared helpers for the core (__init__ / config flow) tests.

OWNd is never allowed to open sockets here: ``OWNSession.test_connection`` is mocked
and the gateway handler's listening/sending loops are replaced by idle coroutines.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myhome.const import CONF_FILE_PATH, CONF_WORKER_COUNT, DOMAIN

MAC = "00:03:50:a4:a5:a5"
MAC2 = "00:03:50:00:00:02"
HOST = "192.168.2.100"
PASSWORD = "12345"

TEST_OK = {"Success": True, "Message": None}

# Data as written by the v0.1.x manual config flow (1-tuples persisted as JSON lists).
LEGACY_ENTRY_DATA_V1: dict[str, Any] = {
    "id": MAC,
    "host": HOST,
    "port": 20000,
    "password": PASSWORD,
    "ssdp_location": [None],
    "ssdp_st": [None],
    "deviceType": [None],
    "friendly_name": [None],
    "manufacturer": ["BTicino S.p.A."],
    "manufacturerURL": ["http://www.bticino.it"],
    "name": "MyHOMEServer1",
    "firmware": [None],
    "mac": MAC,
    "UDN": [None],
}

ENTRY_DATA_V2: dict[str, Any] = {
    "id": MAC,
    "host": HOST,
    "port": 20000,
    "password": PASSWORD,
    "ssdp_location": None,
    "ssdp_st": None,
    "deviceType": None,
    "friendly_name": None,
    "manufacturer": "BTicino S.p.A.",
    "manufacturerURL": "http://www.bticino.it",
    "name": "MyHOMEServer1",
    "firmware": None,
    "mac": MAC,
    "UDN": None,
}

BASIC_YAML = f"""
gateway:
  mac: {MAC}
  light:
    luce_test:
      where: '11'
      name: Luce Test
  cover:
    tapparella_test:
      where: '81'
      name: Tapparella Test
      lock_buttons: true
"""


def write_yaml(tmp_path: Path, content: str = BASIC_YAML, name: str = "myhome.yaml") -> Path:
    """Write a myhome.yaml into tmp_path and return its path."""
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def make_entry(
    config_path: Path | str,
    *,
    data: dict[str, Any] | None = None,
    version: int = 2,
    mac: str = MAC,
    options: dict[str, Any] | None = None,
) -> MockConfigEntry:
    """Config entry pointing at ``config_path``."""
    entry_data = dict(data or ENTRY_DATA_V2)
    entry_data["mac"] = mac
    entry_data["id"] = mac
    return MockConfigEntry(
        domain=DOMAIN,
        title="MyHOMEServer1 Gateway",
        unique_id=mac,
        version=version,
        minor_version=1,
        data=entry_data,
        options={CONF_WORKER_COUNT: 1, CONF_FILE_PATH: str(config_path), **(options or {})},
    )


async def _idle_listening(self) -> None:  # noqa: ANN001 - patched method
    await asyncio.Event().wait()


async def _idle_sending(self, worker_id: int) -> None:  # noqa: ANN001 - patched method
    await asyncio.Event().wait()


@contextmanager
def mock_gateway(test_result: Any = TEST_OK, *, test_side_effect: Exception | None = None) -> Iterator[MagicMock]:
    """Mock OWNd inside gateway.py: connection test + idle loops."""
    session = MagicMock()
    session.test_connection = AsyncMock(return_value=test_result, side_effect=test_side_effect)
    with (
        patch("custom_components.myhome.gateway.OWNSession", return_value=session) as session_cls,
        patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.listening_loop", _idle_listening),
        patch("custom_components.myhome.gateway.MyHOMEGatewayHandler.sending_loop", _idle_sending),
    ):
        yield session_cls
