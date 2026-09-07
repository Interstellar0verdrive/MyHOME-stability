"""Tests for the discovery classifier (``discovery.py``).

Discovery is the feature that spares the user from hand-writing YAML, so what it
calls a device decides which ``myhome.yaml`` block they are told to write.  These
tests feed real OpenWebNet frames through ``OWNEvent.parse`` -- the same objects the
listening loop hands to ``handle_discovery_message`` -- and assert the classification,
the ``platform`` published in ``myhome_device_discovered`` and the YAML suggestion.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from homeassistant.core import HomeAssistant

from OWNd.message import OWNEvent

from custom_components.myhome.config_flow_discovery import generate_suggested_config
from custom_components.myhome.const import (
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DOMAIN,
)
from custom_components.myhome.discovery import MyHOMEDeviceDiscoveryService

from .helpers_core import MAC, make_entry, write_yaml


def make_service(hass: HomeAssistant, tmp_path) -> MyHOMEDeviceDiscoveryService:
    """A discovery service wired to a config entry but to no gateway session."""
    entry = make_entry(write_yaml(tmp_path))
    entry.add_to_hass(hass)
    handler = MagicMock()
    handler.log_id = "[test gateway]"
    service = MyHOMEDeviceDiscoveryService(hass, entry, handler)
    service._discovery_active = True
    return service


def device_info(hass: HomeAssistant, tmp_path, frame: str) -> dict[str, Any]:
    """What discovery makes of one raw frame."""
    message = OWNEvent.parse(frame)
    assert message is not None, frame
    info = make_service(hass, tmp_path)._extract_device_info(message)
    assert info is not None, frame
    return info


# ------------------------------------------------------------------ thermoregulation
@pytest.mark.parametrize(
    ("frame", "device_type", "platform"),
    [
        # A bare probe: it only ever reports a measured temperature.
        ("*#4*1*0*0235##", DEVICE_TYPE_BUS_THERMO_SENSOR, "sensor"),
        # A zone: it reports a mode and/or a set point.
        ("*4*1*1##", DEVICE_TYPE_BUS_THERMO_ZONE, "climate"),
        ("*#4*1*14*0220*3##", DEVICE_TYPE_BUS_THERMO_ZONE, "climate"),
    ],
)
def test_a_temperature_probe_is_not_a_thermo_zone(
    hass: HomeAssistant, tmp_path, frame: str, device_type: str, platform: str
) -> None:
    """``OWNHeatingEvent`` has no ``temperature`` attribute in OWNd 0.7.49.

    The old ``getattr(message, "temperature")`` test was therefore always ``None``
    and every WHO 4 frame came out as a zone, so a plant full of probes was suggested
    as a pile of ``climate:`` entries the user had to sort out by hand.
    """
    info = device_info(hass, tmp_path, frame)
    assert info["device_type"] == device_type
    assert info["platform"] == platform


def test_the_probe_reading_reaches_the_discovery_properties(hass: HomeAssistant, tmp_path) -> None:
    """The value is in ``main_temperature`` / ``secondary_temperature``, as in sensor.py."""
    info = device_info(hass, tmp_path, "*#4*1*0*0235##")
    assert info["properties"]["temperature"] == 23.5


def test_a_discovered_probe_is_suggested_as_a_temperature_sensor(
    hass: HomeAssistant, tmp_path
) -> None:
    """End of the chain: the YAML block the user is told to copy."""
    platform, cfg = generate_suggested_config(device_info(hass, tmp_path, "*#4*1*0*0235##"))
    assert platform == "sensor"
    assert cfg["who"] == "4"
    assert cfg["class"] == "temperature"


# ------------------------------------------------------------------ scenario controls
@pytest.mark.parametrize(
    ("frame", "device_type"),
    [
        ("*25*21#3*225##", DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL),
        ("*15*1*51##", DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL),
    ],
)
def test_a_scenario_control_is_discovered_as_an_event_device(
    hass: HomeAssistant, tmp_path, frame: str, device_type: str
) -> None:
    """Since 0.4.0 a declared scenario control is an ``event`` entity, not a button.

    ``platform`` is part of the public ``myhome_device_discovered`` payload, so
    "button" sent users looking for a ``button.*`` entity that never exists.
    """
    info = device_info(hass, tmp_path, frame)
    assert info["device_type"] == device_type
    assert info["platform"] == "event"


async def test_the_discovered_event_names_the_event_platform(hass: HomeAssistant, tmp_path) -> None:
    """The same value as read by an automation listening to the discovery event."""
    service = make_service(hass, tmp_path)
    seen: list[dict[str, Any]] = []
    hass.bus.async_listen(f"{DOMAIN}_device_discovered", lambda event: seen.append(dict(event.data)))

    service.handle_discovery_message(OWNEvent.parse("*25*21#3*225##"))
    await hass.async_block_till_done()

    assert [item["platform"] for item in seen] == ["event"]
    assert seen[0]["gateway_mac"] == MAC


def test_a_scenario_control_is_still_not_suggested_in_yaml(hass: HomeAssistant, tmp_path) -> None:
    """Documented limitation: it must be declared by hand under ``scenario_control:``.

    The suggestion writer only knows how to emit platform sections, so there is
    nothing to write for a keypad yet -- but that is a missing feature, not the
    "no entity representation" the docstring used to claim.
    """
    assert generate_suggested_config(device_info(hass, tmp_path, "*25*21#3*225##")) is None
