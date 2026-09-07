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
    DEVICE_TYPE_BUS_ALARM_ZONE,
    DEVICE_TYPE_BUS_AUX,
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
        # WHERE above 99 is "<sensor digit><zone>": a probe of its own, and the only
        # shape OWNd reports as ``secondary_temperature``.
        ("*#4*112*0*0198##", DEVICE_TYPE_BUS_THERMO_SENSOR, "sensor"),
        # A plain zone number: this is the zone's own main sensor, i.e. the zone.
        ("*#4*1*0*0235##", DEVICE_TYPE_BUS_THERMO_ZONE, "climate"),
        ("*4*1*1##", DEVICE_TYPE_BUS_THERMO_ZONE, "climate"),
        ("*#4*1*14*0220*3##", DEVICE_TYPE_BUS_THERMO_ZONE, "climate"),
    ],
)
def test_only_a_secondary_sensor_is_a_probe_and_not_a_zone(
    hass: HomeAssistant, tmp_path, frame: str, device_type: str, platform: str
) -> None:
    """``main_temperature`` is a *zone* reporting its own sensor, not a bare probe.

    OWNd sets ``MESSAGE_TYPE_MAIN_TEMPERATURE`` whenever the WHERE is a plain zone
    number and ``MESSAGE_TYPE_SECONDARY_TEMPERATURE`` only for the ``<sensor><zone>``
    form, so classifying every temperature frame as a probe told the user to write a
    read-only ``sensor:`` block for a room that needs a ``climate:`` one.
    """
    info = device_info(hass, tmp_path, frame)
    assert info["device_type"] == device_type
    assert info["platform"] == platform


@pytest.mark.parametrize(
    "frames",
    [
        ("*#4*1*0*0235##", "*4*1*1##"),
        ("*4*1*1##", "*#4*1*0*0235##"),
    ],
    ids=["temperature-first", "mode-first"],
)
def test_a_zone_is_classified_the_same_whichever_frame_arrives_first(
    hass: HomeAssistant, tmp_path, frames: tuple[str, str]
) -> None:
    """The first WHO 4 frame of a WHERE wins and is never revised.

    Both frames of zone 1 produce the same ``unique_id``, and
    ``handle_discovery_message`` returns early for a unique id it has already seen,
    so a classifier that needed the mode frame would give a different answer
    depending on which frame the 60-second window happened to catch first -- and a
    zone broadcasts its temperature far more often than it changes mode.
    """
    service = make_service(hass, tmp_path)
    for frame in frames:
        service.handle_discovery_message(OWNEvent.parse(frame))

    discovered = list(service.get_discovered_devices().values())
    assert len(discovered) == 1
    assert discovered[0]["device_type"] == DEVICE_TYPE_BUS_THERMO_ZONE
    assert discovered[0]["platform"] == "climate"


def test_the_probe_reading_reaches_the_discovery_properties(hass: HomeAssistant, tmp_path) -> None:
    """The value is in ``main_temperature`` / ``secondary_temperature``, as in sensor.py."""
    assert device_info(hass, tmp_path, "*#4*1*0*0235##")["properties"]["temperature"] == 23.5
    assert device_info(hass, tmp_path, "*#4*112*0*0198##")["properties"]["temperature"] == 19.8


def test_a_discovered_probe_is_suggested_as_a_temperature_sensor(
    hass: HomeAssistant, tmp_path
) -> None:
    """End of the chain: the YAML block the user is told to copy."""
    platform, cfg = generate_suggested_config(device_info(hass, tmp_path, "*#4*112*0*0198##"))
    assert platform == "sensor"
    assert cfg["who"] == "4"
    assert cfg["class"] == "temperature"


def test_a_discovered_zone_is_suggested_as_a_climate_block(hass: HomeAssistant, tmp_path) -> None:
    """The other end of R1: a zone must not be suggested as a read-only sensor."""
    platform, cfg = generate_suggested_config(device_info(hass, tmp_path, "*#4*1*0*0235##"))
    assert platform == "climate"
    assert cfg == {"who": "4", "zone": "1", "name": cfg["name"]}


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


# ------------------------------------------------------------------ no YAML section
@pytest.mark.parametrize(
    ("frame", "device_type"),
    [
        # WHO 5, an alarm zone: there is no alarm platform, and every section that
        # exists refuses WHO 5 (binary_sensor is WHO 1/9/25).
        ("*5*17*0##", DEVICE_TYPE_BUS_ALARM_ZONE),
    ],
)
def test_a_device_with_no_yaml_section_publishes_platform_none(
    hass: HomeAssistant, tmp_path, frame: str, device_type: str
) -> None:
    """``platform`` is "the section the device would be declared under" (public payload).

    An alarm device was published as ``binary_sensor``, which is the same stale-value
    bug the round-1 fix removed for scenario controls: it sends the reader to a
    section that would reject the device.  ``None`` says what is true.
    """
    info = device_info(hass, tmp_path, frame)
    assert info["device_type"] == device_type
    assert info["platform"] is None
    assert generate_suggested_config(info) is None


def test_an_auxiliary_channel_is_published_as_a_binary_sensor(
    hass: HomeAssistant, tmp_path
) -> None:
    """WHO 9 is accepted by the binary_sensor schema only, never by ``switch``.

    The published hint and the YAML suggestion must name the same section, or the
    user pastes a block that makes the whole ``myhome.yaml`` unloadable.
    """
    info = device_info(hass, tmp_path, "*9*1*3##")
    assert info["device_type"] == DEVICE_TYPE_BUS_AUX
    assert info["platform"] == "binary_sensor"
    assert generate_suggested_config(info) == (
        "binary_sensor",
        {"who": "9", "where": "3", "name": info["name"]},
    )


def test_a_scenario_control_is_still_not_suggested_in_yaml(hass: HomeAssistant, tmp_path) -> None:
    """Documented limitation: it must be declared by hand under ``scenario_control:``.

    The suggestion writer only knows how to emit platform sections, so there is
    nothing to write for a keypad yet -- but that is a missing feature, not the
    "no entity representation" the docstring used to claim.
    """
    assert generate_suggested_config(device_info(hass, tmp_path, "*25*21#3*225##")) is None
