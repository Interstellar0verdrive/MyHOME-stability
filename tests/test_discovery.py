"""Tests for the discovery classifier (``discovery.py``).

Discovery is the feature that spares the user from hand-writing YAML, so what it
calls a device decides which ``myhome.yaml`` block they are told to write.  These
tests feed real OpenWebNet frames through ``OWNEvent.parse`` -- the same objects the
listening loop hands to ``handle_discovery_message`` -- and assert the classification,
the ``platform`` published in ``myhome_device_discovered`` and the YAML suggestion.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from OWNd.message import OWNCommand, OWNEvent

from custom_components.myhome import discovery as discovery_module
from custom_components.myhome.config_flow_discovery import generate_suggested_config
from custom_components.myhome.const import (
    CONF_ENTITY,
    CONF_PLATFORMS,
    DEVICE_TYPE_BUS_ALARM_ZONE,
    DEVICE_TYPE_BUS_AUX,
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_THERMO_CU,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DEVICE_TYPE_TO_PLATFORM,
    DOMAIN,
    SERVICE_START_DISCOVERY,
    SERVICE_STOP_DISCOVERY,
)
from custom_components.myhome.discovery import (
    _DEVICE_CATEGORY,
    DISCOVERY_TIMEOUT_SEC,
    MyHOMEDeviceDiscoveryService,
)
from custom_components.myhome.validate import config_schema

from .helpers_core import MAC, make_entry, mock_gateway, wait_until, write_yaml


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


# The three shapes a thermoregulation central unit really puts on the bus: a
# plant-wide mode change, the plant temperature and the CU's own actuator status.
# All three carry ``where == '0'`` on OWNd 0.7.49 (``entity`` is ``4-#0`` for the
# first two and, for the third, the zone of the first WHERE parameter - which is why
# gateway.py keys these frames itself instead of trusting ``entity``).
_CENTRAL_UNIT_FRAMES = ("*4*1*0##", "*#4*0*0*0235##", "*#4*0#1*20*1##")


@pytest.mark.parametrize("frame", _CENTRAL_UNIT_FRAMES)
def test_the_central_unit_is_not_discovered_as_zone_zero(
    hass: HomeAssistant, tmp_path, frame: str
) -> None:
    """WHERE ``0`` on WHO 4 is the central unit, and its zone is spelled ``#0``.

    Why it matters in production: ``validate.Zone`` accepts ``#0``, ``1``-``99`` and
    ``#0#<zone>`` and refuses a bare ``0``.  Classifying these frames as
    ``bus_thermo_zone`` produced ``climate: {zone: '0'}`` in
    ``myhome_discovered.yaml``; pasting that block does not break one device, it makes
    the whole ``myhome.yaml`` fail to load, so every other device of the gateway
    disappears -- the exact failure the WHO 9 fix removed one round earlier.  Any
    plant with a thermo central unit emits these frames.

    Mutations caught: dropping the WHERE-``0`` branch of
    ``_determine_thermo_device_type`` (the device becomes a zone again), or reporting
    the WHERE verbatim instead of re-spelling it ``#0`` (the unique id stops matching
    the ``4-#0`` key gateway.py and validate.py use for the same device).
    """
    info = device_info(hass, tmp_path, frame)
    assert info["device_type"] == DEVICE_TYPE_BUS_THERMO_CU
    assert info["device_type"] != DEVICE_TYPE_BUS_THERMO_ZONE
    assert info["where"] == "#0"
    assert info["unique_id"] == f"{MAC}-4-#0"
    assert info["platform"] == "climate"


@pytest.mark.parametrize("frame", _CENTRAL_UNIT_FRAMES)
def test_a_central_unit_frame_produces_yaml_the_validator_accepts(
    hass: HomeAssistant, tmp_path, frame: str
) -> None:
    """The whole chain for the central unit: frame -> suggestion -> validate.py.

    Why it matters in production: the round-trip test in
    ``test_config_flow_discovery.py`` feeds the classifier's *output*; this one starts
    from the frame, so it also fails if the classifier ever hands the writer a WHERE
    the schema refuses.  ``climate.py`` really builds a central-unit entity for
    ``zone: '#0'`` (AUTO included), so the suggestion is worth pasting.

    Mutation caught: emitting ``zone: '0'`` -- ``config_schema`` raises instead of
    returning a platform.
    """
    platform, cfg = generate_suggested_config(device_info(hass, tmp_path, frame))
    assert (platform, cfg["zone"]) == ("climate", "#0")
    result = config_schema({MAC: {platform: {"discovered_4__0": dict(cfg)}}})
    assert list(result[MAC.lower()]["platforms"]) == ["climate"]


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
def test_the_published_platform_values_are_exactly_the_documented_ones() -> None:
    """``platform`` is a public event payload, so its value set is a contract.

    Why it matters in production: ``docs/services-and-events.md`` enumerates the
    values an automation may switch on.  It still listed ``switch``, and after the
    WHO 9 fix (an auxiliary channel is a ``binary_sensor``; ``switch`` is WHO 1 only)
    no row can produce it -- the mirror image of the bug that fix removed, which was
    naming a section that would reject the device.

    Mutation caught: adding a value here without the docs sentence catching up, or
    re-introducing a section this integration does not build entities for.
    """
    assert set(DEVICE_TYPE_TO_PLATFORM.values()) - {None} == {
        "light",
        "cover",
        "sensor",
        "climate",
        "event",
        "binary_sensor",
    }


@pytest.mark.parametrize(
    ("frame", "category"),
    [
        ("*1*1*11##", "lighting"),
        ("*#1*11*1*180*255##", "lighting"),
        ("*2*1*81##", "automation"),
        ("*#18*51*113*613##", "energy"),
        ("*#4*1*0*0235##", "thermoregulation"),
        ("*4*1*0##", "thermoregulation"),
        ("*15*1*51##", "scenario"),
        ("*25*21#3*225##", "scenario"),
        ("*9*1*3##", "auxiliary"),
        ("*5*11*12##", "alarm"),
    ],
)
def test_the_discovery_event_carries_the_category_of_the_device(
    hass: HomeAssistant, tmp_path, frame: str, category: str
) -> None:
    """``category`` is published verbatim in ``myhome_device_discovered``.

    ``handle_discovery_message`` fires the whole ``device_info`` dict as
    ``discovered_device``, so every key in it is a value automations can switch on -
    ``category`` included, even though it is only a grouping for the notification.
    Nothing asserted it: the key could be renamed, re-valued or deleted outright and
    the suite stayed green, which is how a published payload quietly loses a field.

    Mutation caught: changing any ``_DEVICE_CATEGORY`` value, or dropping the
    ``"category"`` key from ``_extract_device_info``.
    """
    assert device_info(hass, tmp_path, frame)["category"] == category


def test_the_published_category_values_are_the_ones_discovery_can_produce() -> None:
    """The value set is small and closed, so state it once.

    ``DEVICE_TYPE_GENERIC`` and ``DEVICE_TYPE_BUS_LIGHT_GROUP`` are the two supported
    types with no row here; neither can reach ``_extract_device_info``
    (``_determine_lighting_device_type`` returns only dimmer/on-off, and a group WHERE
    is dropped by the ``#`` guard above), so the ``"generic"`` default is defensive.

    Mutation caught: adding a category without deciding what it means, or renaming one.
    """
    assert set(_DEVICE_CATEGORY.values()) == {
        "lighting",
        "automation",
        "energy",
        "thermoregulation",
        "scenario",
        "auxiliary",
        "alarm",
    }


@pytest.mark.parametrize(
    ("frame", "device_type"),
    [
        # A real burglar-alarm sensor frame: WHERE is "<zone><sensor>", so this is
        # sensor 2 of zone 1 (OWNd's OWNAlarmEvent reads it that way).  It carries no
        # "#", so it is not taken for a group address and really reaches this code.
        ("*5*11*12##", DEVICE_TYPE_BUS_ALARM_ZONE),
        # The control panel itself: a single-character WHERE.
        ("*5*17*0##", DEVICE_TYPE_BUS_ALARM_ZONE),
    ],
    ids=["zone-sensor", "control-panel"],
)
def test_a_device_with_no_yaml_section_publishes_platform_none(
    hass: HomeAssistant, tmp_path, frame: str, device_type: str
) -> None:
    """``platform`` is "the section the device would be declared under" (public payload).

    An alarm device was published as ``binary_sensor``, which is the same stale-value
    bug the round-1 fix removed for scenario controls: it sends the reader to a
    section that would reject the device (``binary_sensor`` is WHO 1/9/25).  ``None``
    says what is true.

    The first case is the reason this is an observable behaviour and not only a table
    entry: a burglar alarm reports its sensors with a plain WHERE.
    """
    info = device_info(hass, tmp_path, frame)
    assert info["device_type"] == device_type
    assert info["platform"] is None
    assert generate_suggested_config(info) is None


@pytest.mark.parametrize("frame", ["*5*1*#1##", "*5*5*#2##"])
def test_an_alarm_zone_address_is_not_taken_for_a_device(
    hass: HomeAssistant, tmp_path, frame: str
) -> None:
    """``*5*<what>*#<zone>##`` is dropped by the group-address guard, on purpose.

    Why it matters in production: on WHO 5 a leading ``#`` is zone N, not a group, so
    this guard is wider than its name.  Letting these frames through would announce a
    device the integration has no entity and no ``myhome.yaml`` section for, and add
    it to the "must be declared by hand" count -- which promises the user something
    that cannot be done for an alarm zone.  This test states the choice so the next
    reader does not "fix" the guard by accident.

    Mutation caught: narrowing the guard to let ``#``-prefixed WHO 5 WHEREs through.
    """
    message = OWNEvent.parse(frame)
    assert message is not None and message.where.startswith("#")
    assert make_service(hass, tmp_path)._extract_device_info(message) is None  # noqa: SLF001


# ------------------------------------------------------------------ plant-wide addresses
# Every WHERE OWNd 0.7.49 decodes as a *scope* instead of a device, on both WHOs that
# have them.  ``100`` is area 10: the bus spells it with three digits and
# ``validate.py`` with two, which is why that one did not merely add a useless entity
# but made the whole ``myhome.yaml`` unloadable.
_SCOPE_FRAMES = [
    "*1*1*0##",  # general: every light of the plant
    "*1*1*00##",  # area 0
    "*1*1*1##",  # area 1
    "*1*1*9##",  # area 9
    "*1*1*100##",  # area 10, spelled with three digits on the bus
    "*1*1*#5##",  # group 5
    "*2*1*0##",  # ...and the same five shapes on WHO 2
    "*2*1*00##",
    "*2*1*4##",
    "*2*1*100##",
    "*2*1*#7##",
]


@pytest.mark.parametrize("frame", _SCOPE_FRAMES)
async def test_a_plant_wide_address_is_not_taken_for_a_device(
    hass: HomeAssistant, tmp_path, frame: str
) -> None:
    """A general, area or group WHERE is a scope, and discovery must ignore it.

    Why it matters in production: any plant-wide or area button press during the
    60-second run produces one of these frames, and discovery used to drop only the
    ``#``-prefixed ones.  What the user was then handed, between their real
    actuators:

    * ``light: {where: '0'}`` -- an entity named "MyHOME Bus On Off Switch 0" whose
      ``turn_on`` sends ``*1*1*0##``, i.e. switches on *every* light of the house,
      and which can never show a state because ``gateway._handle_lighting_scope``
      intercepts every frame that would update it;
    * ``light: {where: '100'}`` -- area 10, which ``validate.py`` refuses ("expecting
      a valid General ('0'), Area ('00', '1'-'9', '10') ... "), so pasting the block
      does not break one device: the whole ``myhome.yaml`` fails to load and every
      device of that gateway disappears.

    The gateway already refuses to dispatch exactly these frames to an entity, one
    ``if`` further down the same dispatcher, so the two now share one predicate
    (``const.is_bus_scope_address``).

    Mutation caught: dropping the ``is_bus_scope_address`` guard from
    ``_extract_device_info`` (every frame here becomes a device again), or narrowing
    the predicate to one of its three branches.
    """
    message = OWNEvent.parse(frame)
    # The classification is OWNd's, not ours: assert it from the library's own
    # properties so this test still means something if our helper changes.
    assert message is not None
    assert message.is_general or message.is_area or message.is_group

    service = make_service(hass, tmp_path)
    seen: list[dict[str, Any]] = []
    hass.bus.async_listen(f"{DOMAIN}_device_discovered", lambda event: seen.append(dict(event.data)))

    assert service._extract_device_info(message) is None  # noqa: SLF001
    service.handle_discovery_message(message)
    await hass.async_block_till_done()

    assert seen == []
    assert service.get_discovered_devices() == {}
    assert service.suggestions.pending_count == 0


# ------------------------------------------------------------------ bus interface (F422)
def test_a_device_behind_a_bus_interface_keeps_its_interface(hass: HomeAssistant, tmp_path) -> None:
    """OWNd keeps the F422 interface in ``entity``, not in ``where`` -- read it there.

    Why it matters in production: ``*1*1*11#4#3##`` is the actuator 11 of a private
    riser behind an F422, a different physical device from the main-bus actuator 11.
    OWNd 0.7.49 parses it as ``where == '11'`` and ``entity == '1-11#4#3'``, and
    discovery read ``where``.  The suggestion was therefore ``light: {where: '11'}``
    with no ``interface:``, which (1) drives the wrong actuator, since ``turn_on``
    sends ``*1*1*11##``, and (2) never updates, because the gateway dispatches these
    frames by ``1-11#4#03`` / ``1-11#4#3`` and never by the bare ``1-11``.

    The unique id keeps the interface zero padded, like ``validate.device_key``: it
    is the tail of the entity ``unique_id`` and the device registry identifier, so
    the two must agree character for character.

    Mutations caught: reading ``where`` without the interface (the unique id becomes
    the main-bus one and the ``interface`` key disappears), or emitting the padded
    ``03`` in the YAML value, which ``validate.BusInterface`` normalises but
    ``bus_full_where`` would then spell ``11#4#03`` -- a WHERE no bus sends.
    """
    info = device_info(hass, tmp_path, "*1*1*11#4#3##")

    assert info["unique_id"] == f"{MAC}-1-11#4#03"
    assert info["unique_id"] != f"{MAC}-1-11"
    assert (info["where"], info["interface"]) == ("11", "3")
    assert info["properties"]["ownId"] == "1*11#4#3"

    platform, cfg = generate_suggested_config(info)
    assert (platform, cfg["where"], cfg["interface"]) == ("light", "11", "3")


def test_the_two_spellings_of_an_interface_are_the_same_device(hass: HomeAssistant, tmp_path) -> None:
    """``#4#3`` and ``#4#03`` come off the same bus and must not be two devices.

    OWNd reports the interface exactly as the frame spells it, and both spellings
    occur; ``gateway._entity_key_candidates`` already resolves them to one entity, so
    discovery must not announce the same actuator twice, once per spelling.
    """
    service = make_service(hass, tmp_path)
    for frame in ("*1*1*11#4#3##", "*1*1*11#4#03##"):
        service.handle_discovery_message(OWNEvent.parse(frame))

    assert list(service.get_discovered_devices()) == [f"{MAC}-1-11#4#03"]


def test_a_bus_interface_out_of_range_is_not_a_main_bus_device(hass: HomeAssistant, tmp_path) -> None:
    """A ``#4#`` value the integration cannot use must drop the frame, not the interface.

    Why it matters in production: ``normalise_bus_interface`` answers ``None`` for
    anything outside 0-15, and ``None`` is also how this module spells "on the main
    bus".  A ``*1*1*11#4#16##`` frame was therefore discovered as ``{mac}-1-11`` and
    suggested with no ``interface:`` at all -- the exact wrong suggestion reading the
    interface was added to remove, this time for a device that is certainly not on the
    main bus.  ``validate.BusInterface`` refuses the same value outright ("it must be
    1 or 2 digits between 0 and 15"), so discovery refuses the frame too: no
    suggestion is better than a wrong one.

    An F422 local bus is a 0-15 field on the wire, so such a frame should not exist on
    real hardware; what is pinned here is the failure mode, not the frame.

    Mutation caught: dropping the ``if raw_interface and interface is None`` guard -
    the device comes back as the main-bus ``{mac}-1-11``.
    """
    service = make_service(hass, tmp_path)
    for frame in ("*1*1*11#4#16##", "*15*1*11#4#16##"):
        service.handle_discovery_message(OWNEvent.parse(frame))

    assert service.get_discovered_devices() == {}
    assert service.suggestions.pending_count == 0
    assert service.suggestions._skipped == []  # noqa: SLF001
    # The two values on either side of the range boundary are still real devices.
    for frame, unique_id in (("*1*1*11#4#0##", f"{MAC}-1-11#4#00"), ("*1*1*12#4#15##", f"{MAC}-1-12#4#15")):
        service.handle_discovery_message(OWNEvent.parse(frame))
        assert unique_id in service.get_discovered_devices(), frame


async def test_the_main_bus_and_the_riser_are_two_devices(
    hass: HomeAssistant, tmp_path, caplog
) -> None:
    """A plant with actuator 11 on the main bus *and* at ``11#4#3`` has two devices.

    Why it matters in production: ``handle_discovery_message`` keeps the first
    ``unique_id`` it sees and discards every repeat.  While the interface was dropped
    both actuators were keyed ``{mac}-1-11``, so whichever answered second was never
    announced and never suggested -- silently, with the user left believing the run
    saw everything on the bus.

    Mutation caught: building the unique id from ``message.where`` alone; the second
    frame is then swallowed as a duplicate and this test sees one device.
    """
    service = make_service(hass, tmp_path)
    seen: list[dict[str, Any]] = []
    hass.bus.async_listen(f"{DOMAIN}_device_discovered", lambda event: seen.append(dict(event.data)))

    for frame in ("*1*1*11##", "*1*1*11#4#3##"):
        service.handle_discovery_message(OWNEvent.parse(frame))
    await hass.async_block_till_done()

    assert sorted(service.get_discovered_devices()) == [f"{MAC}-1-11", f"{MAC}-1-11#4#03"]
    assert len(seen) == 2
    assert service.suggestions.pending_count == 2
    # ...and the INFO line the user reads tells them apart, which "WHERE=11" twice
    # would not.
    announced = [line for line in caplog.text.splitlines() if "Discovered" in line]
    assert len(announced) == 2
    assert announced[0].endswith("WHERE=11")
    assert announced[1].endswith("WHERE=11#4#3")


# Frames a real 60-second run can see, in one list: the devices worth suggesting, the
# scopes that are not devices, and the families that have no YAML section.  The WHEREs
# are the documentation-range ones used everywhere in this suite.
_RUN_FRAMES = (
    "*1*1*11##",  # a lamp on the main bus
    "*1*5*12##",  # a dimmer (brightness preset)
    "*1*1*11#4#3##",  # the same address on a private riser behind an F422
    "*2*1*54##",  # a shutter
    "*2*1*31#4#2##",  # ...and one behind an interface
    "*#18*51*113*613##",  # an energy meter
    "*#4*1*0*0235##",  # a thermoregulation zone
    "*#4*112*0*0198##",  # a temperature probe
    "*4*1*0##",  # the thermoregulation central unit
    "*25*21#3*225##",  # a CEN+ keypad: announced, never suggested
    "*9*1*3##",  # an auxiliary channel
    *_SCOPE_FRAMES,  # ...and every plant-wide address, which must produce nothing
)


async def test_a_whole_run_produces_yaml_the_validator_accepts(hass: HomeAssistant, tmp_path) -> None:
    """End to end: every frame of a run -> the suggestions file -> ``validate.py``.

    Why it matters in production: ``myhome_discovered.yaml`` is copied into
    ``myhome.yaml`` as a block, so a *single* suggestion the schema refuses takes the
    whole file down with it -- every device of that gateway disappears, and the error
    the user sees names the pasted line, not discovery.  The per-type tests feed the
    classifier's output; this one starts from raw frames and ends in
    ``config_schema``, so it also fails when the classifier hands the writer a WHERE
    the schema never accepts (``where: '100'``, ``zone: '0'``, an unpadded interface
    the schema refuses...).

    Mutations caught: any of the above, plus letting a scope frame through -- the
    area-10 suggestion alone makes ``config_schema`` raise here.
    """
    service = make_service(hass, tmp_path)
    for frame in _RUN_FRAMES:
        service.handle_discovery_message(OWNEvent.parse(frame))
    await hass.async_block_till_done()

    pending = {platform: dict(devices) for platform, devices in service.suggestions._pending.items()}  # noqa: SLF001
    assert pending, "the run must have produced suggestions, or this test proves nothing"

    result = config_schema({MAC: pending})
    assert sorted(result[MAC.lower()][CONF_PLATFORMS]) == sorted(pending)

    # No scope address survived into the file the user is told to copy.  Only WHO 1
    # and WHO 2 have them: "1" is a perfectly ordinary thermoregulation zone.
    lighting_wheres = {
        cfg["where"] for platform in ("light", "cover") for cfg in pending.get(platform, {}).values()
    }
    assert lighting_wheres.isdisjoint({"0", "00", "1", "9", "100"})


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


# ------------------------------------------------------------------ de-duplication
async def test_a_device_is_announced_only_once(hass: HomeAssistant, tmp_path) -> None:
    """A busy bus answers the same WHERE repeatedly; the user must see it once.

    A discovery run opens with broadcast status requests, so every device on the
    bus answers, and a lamp somebody is using answers again on every keypress -
    repetition is the normal case here, not an edge case. Mutation caught:
    ``if unique_id in self._discovered_devices:`` -> ``if False and ...``, after
    which each repeat re-announces the device: a duplicate
    ``myhome_device_discovered`` event for the user's automations, a duplicate INFO
    line and a duplicate YAML suggestion.
    """
    service = make_service(hass, tmp_path)
    seen: list[dict[str, Any]] = []
    hass.bus.async_listen(f"{DOMAIN}_device_discovered", lambda event: seen.append(dict(event.data)))

    for _ in range(3):
        service.handle_discovery_message(OWNEvent.parse("*1*1*11##"))
    await hass.async_block_till_done()

    assert len(seen) == 1
    assert len(service.get_discovered_devices()) == 1
    assert service.suggestions.pending_count == 1


# ------------------------------------------------------------------ device properties
@pytest.mark.parametrize(
    ("frame", "expected"),
    [
        # An on/off frame says nothing about a dimmer, so the suggestion is the safe
        # one *and* carries the note that tells the user how to correct it.
        (
            "*1*1*11##",
            {
                "dimmable": False,
                "note": "Detected as on/off switch; set `dimmable: true` manually for dimmers",
            },
        ),
        # A brightness preset (`*1*<level>*<where>##`) is a dimmer, with no level to report.
        ("*1*5*11##", {"dimmable": True}),
        # A dimension frame carries the percentage OWNd puts in `brightness`.
        ("*#1*11*1*180*255##", {"dimmable": True, "brightness": 80}),
        ("*2*1*81##", {"shutter_type": "standard"}),
        ("*#18*51*113*613##", {"meter_type": "energy", "power": 613}),
    ],
    ids=["on-off", "preset-dimmer", "brightness-dimmer", "shutter", "meter"],
)
def test_the_discovery_properties_describe_the_device(
    hass: HomeAssistant, tmp_path, frame: str, expected: dict[str, Any]
) -> None:
    """``_add_device_specific_properties`` writes what the user is handed to paste.

    These keys reach the ``myhome_device_discovered`` payload and (through
    ``generate_suggested_config``) the ``myhome_discovered.yaml`` block, so they are
    user-visible text, not internals: ``dimmable: False`` plus the note is what
    turns an unrecognised dimmer into a one-line fix instead of a lamp that only
    ever switches. Mutations caught: dropping any branch (the key disappears),
    swapping the ``brightness``/``brightness_preset`` arms, or dropping the note.
    """
    properties = device_info(hass, tmp_path, frame)["properties"]
    assert {key: properties.get(key) for key in expected} == expected
    # The note belongs to the on/off case only: a device already known to be
    # dimmable must not be advertised as needing a manual correction.
    assert ("note" in properties) is ("note" in expected)


def test_a_dimmer_is_suggested_as_a_dimmable_light(hass: HomeAssistant, tmp_path) -> None:
    """End of the chain for the property above: `dimmable` reaches the YAML block.

    The on/off case is written out as `dimmable: false` rather than left implicit,
    which is what makes the note above actionable: the user flips one word instead
    of working out which key to add.
    """
    dimmer = generate_suggested_config(device_info(hass, tmp_path, "*1*5*11##"))
    on_off = generate_suggested_config(device_info(hass, tmp_path, "*1*1*11##"))
    assert dimmer == ("light", {"who": "1", "where": "11", "name": dimmer[1]["name"], "dimmable": True})
    assert on_off == ("light", {"who": "1", "where": "11", "name": on_off[1]["name"], "dimmable": False})


# ------------------------------------------------------------------ service lifecycle
class _NoSleep:
    """``asyncio`` stand-in for discovery.py that records what it is asked to sleep.

    Everything except ``sleep`` is the real module, so the worker keeps using real
    tasks and events; ``sleep`` returns at once and remembers the delay. Without it
    ``_send_discovery_commands`` paces its broadcast requests 0.5 s apart and every
    lifecycle test below would cost seconds of wall clock.

    ``hold_from`` parks the worker inside ``_send_discovery_commands`` from that
    sleep onwards, which is the state a reload has to be able to interrupt.
    """

    def __init__(self, hold_from: int | None = None) -> None:
        self.delays: list[float] = []
        self._hold_from = hold_from

    def __getattr__(self, name: str) -> Any:
        return getattr(asyncio, name)

    async def sleep(self, delay: float, *args: Any, **kwargs: Any) -> Any:
        self.delays.append(delay)
        if self._hold_from is not None and len(self.delays) >= self._hold_from:
            await asyncio.Event().wait()  # only a cancellation gets the worker out
        return await asyncio.sleep(0, *args, **kwargs)


@contextmanager
def no_discovery_sleep(hold_from: int | None = None) -> Iterator[_NoSleep]:
    """Replace ``asyncio`` inside discovery.py only, for the duration of the block."""
    recorder = _NoSleep(hold_from)
    with patch.object(discovery_module, "asyncio", recorder):
        yield recorder


# A myhome.yaml that already declares the two keypads the run below sees, so the
# end-of-run report has something real to stay quiet about.  ``object: 25`` is CEN+
# WHERE 225 and the CEN control is addressed by its WHERE.
DECLARED_KEYPADS_YAML = f"""
gateway:
  mac: {MAC}
  scenario_control:
    kitchen_keypad:
      object: 25
      name: Kitchen Keypad
    hallway_keypad:
      protocol: cen
      where: '11'
      name: Hallway Keypad
  light:
    light_test:
      where: '11'
      name: Light Test
"""


@asynccontextmanager
async def running_gateway(hass: HomeAssistant, tmp_path, yaml_text: str | None = None) -> AsyncIterator[Any]:
    """A loaded config entry with the real handler and its real discovery service."""
    entry = make_entry(write_yaml(tmp_path) if yaml_text is None else write_yaml(tmp_path, yaml_text))
    entry.add_to_hass(hass)
    with mock_gateway():
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        yield entry


def completed_events(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Collector for the public ``myhome_discovery_completed`` event."""
    seen: list[dict[str, Any]] = []
    hass.bus.async_listen(f"{DOMAIN}_discovery_completed", lambda event: seen.append(dict(event.data)))
    return seen


async def test_the_stop_service_ends_the_run_and_reports_what_was_found(
    hass: HomeAssistant, tmp_path
) -> None:
    """``myhome.start_discovery`` / ``myhome.stop_discovery`` are the whole feature.

    Nothing covered the run itself: only the classifier was tested. What a user
    can observe is pinned here end to end - the broadcast status requests actually
    reach the bus, the worker stays alive until it is told to stop, and the public
    ``myhome_discovery_completed`` event names the reason and the devices seen, so
    an automation can act on it.

    Mutations caught: dropping a frame from ``_DISCOVERY_COMMANDS`` or its 0.5 s
    pacing; ``_discovery_worker`` returning instead of waiting on ``_stopped``;
    ``stop_discovery`` firing the event with a different ``reason`` or without
    ``discovered_count`` / ``discovered_devices``.
    """
    async with running_gateway(hass, tmp_path) as entry:
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        service = handler.discovery_service
        completed = completed_events(hass)

        with no_discovery_sleep() as sleeps:
            await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()

            assert service.is_discovery_active() is True
            assert service._discovery_task is not None  # noqa: SLF001
            assert service._timer_handle is not None  # noqa: SLF001

            # The broadcast status requests go out paced. The worker is a
            # config-entry *background* task, which `async_block_till_done` does not
            # wait for by design, so the queue is polled instead of assumed.
            # There is no WHO 25 entry: there is no general status request for dry
            # contacts and keypads never answer one - see
            # ``test_every_discovery_command_reaches_the_bus``.
            await wait_until(lambda: len(sleeps.delays) == 5)
            assert [str(item.message) for item in list(handler.send_buffer._queue)][-5:] == [  # noqa: SLF001
                "*#1*0##", "*#2*0##", "*#4*0##", "*#18*0##", "*#9*0##",
            ]
            assert sleeps.delays == [0.5] * 5
            # ...and the worker stays parked on `_stopped` instead of returning.
            assert not service._discovery_task.done()  # noqa: SLF001

            # A device answers one of them while the run is open. WHERE 12 is *not*
            # in the fixture's myhome.yaml (11 and 81 are), so it is a genuinely new
            # device and reaches the suggestions file below.
            service.handle_discovery_message(OWNEvent.parse("*1*1*12##"))

            await hass.services.async_call(DOMAIN, SERVICE_STOP_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()

        assert service.is_discovery_active() is False
        assert service._discovery_task is None  # noqa: SLF001
        assert service._timer_handle is None  # noqa: SLF001
        assert completed == [
            {
                "gateway_mac": MAC,
                "reason": "stopped",
                "discovered_count": 1,
                "discovered_devices": [f"{MAC}-1-12"],
            }
        ]
        # The payoff of the whole run: the YAML block is on disk, beside the user's
        # own myhome.yaml and never inside it. Mutation caught: dropping the
        # `await self.suggestions.async_flush()` at the end of `stop_discovery`,
        # after which a run finds devices, announces them and writes nothing.
        suggested = tmp_path / "myhome_discovered.yaml"
        assert suggested.is_file()
        assert "discovered_1_12" in suggested.read_text(encoding="utf-8")

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_the_declare_by_hand_count_is_the_count_of_one_run(
    hass: HomeAssistant, tmp_path, caplog
) -> None:
    """Two runs, one keypad: the second run must still report ``1 device(s)``.

    Why it matters in production: the "must be declared by hand" line is the only
    report a user gets about a CEN/CEN+ control (there is no status request a keypad
    answers, so it is discovered only from the frames it emits, and the writer cannot
    express a ``scenario_control:`` block).  ``MyHOMEDiscoverySuggestions`` is created
    once per config entry and outlives the run, while ``_discovered_devices`` is
    cleared at the start of every run, so the same keypad used to be appended to
    ``_skipped`` again on every run: a count of "3 device(s)" for one keypad sends the
    user looking for two devices that do not exist.

    Mutation caught: dropping ``self.suggestions.reset()`` from ``start_discovery``
    (or the ``_skipped.clear()`` inside it) - the second run reports 2.
    """
    async with running_gateway(hass, tmp_path) as entry:
        service = hass.data[DOMAIN][MAC][CONF_ENTITY].discovery_service

        counts: list[str] = []
        for _ in range(3):
            with no_discovery_sleep():
                await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
                await hass.async_block_till_done()
                # A CEN+ keypad: discovered, announced, and impossible to suggest.
                service.handle_discovery_message(OWNEvent.parse("*25*21#3*225##"))
                caplog.clear()
                await hass.services.async_call(DOMAIN, SERVICE_STOP_DISCOVERY, {}, blocking=True)
                await hass.async_block_till_done()
            counts += [line for line in caplog.text.splitlines() if "declared by hand" in line]

        assert len(counts) == 3, caplog.text
        for line in counts:
            assert "1 device(s)" in line, line

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_a_device_that_cannot_be_declared_is_reported_apart_from_one_that_can(
    hass: HomeAssistant, tmp_path, caplog
) -> None:
    """"Declare it by hand" must not be said of a device that cannot be declared.

    Why it matters in production: this line is the entire user-facing output of a
    run for everything the writer cannot express, and it lumped two opposite answers
    together.  A CEN/CEN+ keypad really can be added by hand, under
    ``scenario_control:`` -- that is what ``docs/discovery.md`` tells the user to do.
    A burglar-alarm device cannot: there is no alarm section anywhere in the file
    schema, and every existing section refuses WHO 5.  Reading "1 device(s) ... must
    be declared by hand (bus_alarm_zone@12)", a careful maintainer goes looking
    through ``docs/configuration.md`` for a chapter that does not exist.

    Both frames are real: ``*25*21#3*225##`` is button 21 of a CEN+ keypad, and
    ``*5*11*12##`` is sensor 2 of alarm zone 1, whose plain WHERE is exactly why it
    survives discovery's address guards.

    Mutation caught: appending every non-suggestable device to one list again - the
    two device types then share a clause and the alarm one is described as
    declarable.
    """
    async with running_gateway(hass, tmp_path) as entry:
        service = hass.data[DOMAIN][MAC][CONF_ENTITY].discovery_service

        with no_discovery_sleep():
            await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()
            service.handle_discovery_message(OWNEvent.parse("*25*21#3*225##"))
            service.handle_discovery_message(OWNEvent.parse("*5*11*12##"))
            caplog.clear()
            await hass.services.async_call(DOMAIN, SERVICE_STOP_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()

        reported = [line for line in caplog.text.splitlines() if "Discovery finished" in line]
        assert len(reported) == 1, caplog.text
        line = reported[0]
        # The keypad: declarable, and the line says where.
        assert "1 device(s) must be declared by hand under `scenario_control:`" in line
        assert "bus_cenplus_scenario_control@225" in line
        # The alarm sensor: not declarable, and not described as if it were.
        assert "1 device(s) belong to a family this integration has no support for" in line
        assert "bus_alarm_zone@12" in line
        assert line.index("scenario_control") < line.index("no support for")

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_a_keypad_already_declared_is_not_reported_as_one_to_declare(
    hass: HomeAssistant, tmp_path, caplog
) -> None:
    """End to end: a run over a plant whose keypads are configured says nothing.

    Why it matters in production: "N device(s) must be declared by hand under
    ``scenario_control:``" is written as an instruction, and it is the only thing a
    run ever says about a CEN/CEN+ control.  ``MyHOMEDiscoverySuggestions.add`` gave
    up as soon as the writer said "cannot suggest this" - which is always, for a
    keypad - so it never asked whether the control was already declared, and the owner
    of a plant configured months ago was told to declare it again on every run.  A
    lamp in the same file is filtered out and never mentioned, so the asymmetry was
    not something a reader could infer.

    The declared spellings are the two real ones: a CEN+ control keyed by ``object``
    (WHERE 225) and a CEN control keyed by ``where``.

    Mutation caught: dropping the ``is_scenario_control_configured`` check from
    ``add()`` - the run closes with "2 device(s) must be declared by hand".
    """
    async with running_gateway(hass, tmp_path, DECLARED_KEYPADS_YAML) as entry:
        service = hass.data[DOMAIN][MAC][CONF_ENTITY].discovery_service
        assert set(hass.data[DOMAIN][MAC][CONF_PLATFORMS]["event"]) == {"cenplus-25", "cen-11"}

        with no_discovery_sleep():
            await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()
            service.handle_discovery_message(OWNEvent.parse("*25*21#3*225##"))  # the CEN+ keypad
            service.handle_discovery_message(OWNEvent.parse("*15*1*11##"))  # the CEN keypad
            service.handle_discovery_message(OWNEvent.parse("*25*21#3*299##"))  # object 99: NOT declared
            caplog.clear()
            await hass.services.async_call(DOMAIN, SERVICE_STOP_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()

        # All three were seen; only the undeclared one is something to do.
        assert len(service.get_discovered_devices()) == 3
        reported = [line for line in caplog.text.splitlines() if "declared by hand" in line]
        assert len(reported) == 1, caplog.text
        assert "1 device(s) must be declared by hand" in reported[0]
        assert "bus_cenplus_scenario_control@299" in reported[0]
        assert "@225" not in reported[0]
        assert "bus_cen_scenario_control" not in reported[0]

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()



async def test_a_second_start_does_not_restart_the_run(hass: HomeAssistant, tmp_path) -> None:
    """Calling ``myhome.start_discovery`` twice must not lose what the first found.

    The refusal is the reason ``start_discovery`` clears ``_discovered_devices``
    only on a genuine start. Mutation caught: dropping the ``if
    self._discovery_active: return`` guard, which restarts the worker (leaking the
    first one and its timer) and throws away everything the open run had collected.
    """
    async with running_gateway(hass, tmp_path) as entry:
        service = hass.data[DOMAIN][MAC][CONF_ENTITY].discovery_service

        with no_discovery_sleep():
            await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()
            service.handle_discovery_message(OWNEvent.parse("*1*1*11##"))
            first_task = service._discovery_task  # noqa: SLF001
            first_timer = service._timer_handle  # noqa: SLF001

            await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()

            assert service._discovery_task is first_task  # noqa: SLF001
            assert service._timer_handle is first_timer  # noqa: SLF001
            assert list(service.get_discovered_devices()) == [f"{MAC}-1-11"]

            await hass.services.async_call(DOMAIN, SERVICE_STOP_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_the_timeout_ends_the_run_and_says_so(hass: HomeAssistant, tmp_path) -> None:
    """A run nobody stops must end on its own, and say which way it ended.

    The timer is armed for ``DISCOVERY_TIMEOUT_SEC`` and then fired by hand, so the
    test costs nothing and does not depend on the loop clock. Mutations caught:
    ``call_later(self._discovery_timeout, ...)`` with any other delay; ``_on_timeout``
    stopping the run with a reason other than ``"timeout"`` (the payload automations
    read to tell "it finished" from "I stopped it"); and ``_on_timeout`` leaving
    ``_timer_handle`` set, which makes the next ``stop_discovery`` cancel a handle
    that has already run.
    """
    async with running_gateway(hass, tmp_path) as entry:
        service = hass.data[DOMAIN][MAC][CONF_ENTITY].discovery_service
        completed = completed_events(hass)

        with no_discovery_sleep():
            await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()

            armed_for = service._timer_handle.when() - hass.loop.time()  # noqa: SLF001
            assert armed_for == pytest.approx(DISCOVERY_TIMEOUT_SEC, abs=1.0)

            service._timer_handle.cancel()  # noqa: SLF001 - fired by hand instead
            service._on_timeout()  # noqa: SLF001 - what the loop would have called
            await hass.async_block_till_done()

        assert service.is_discovery_active() is False
        assert service._timer_handle is None  # noqa: SLF001
        assert service._discovery_task is None  # noqa: SLF001
        assert [item["reason"] for item in completed] == ["timeout"]

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_unloading_the_entry_cancels_the_worker_and_the_timer(
    hass: HomeAssistant, tmp_path
) -> None:
    """core-10: an open discovery run must not survive the entry that owns it.

    ``async_unload_entry`` awaits ``stop_device_discovery()`` before it closes the
    gateway; without it every reload with discovery open leaks a ``call_later``
    handle, and the run stays "active" against a ``hass.data`` that no longer
    exists. Mutations caught: dropping the ``_timer_handle.cancel()`` block from
    ``stop_discovery``, or the ``await handler.stop_device_discovery()`` line from
    ``__init__.async_unload_entry``; the second also trips Home Assistant's own
    lingering-timer check.

    The *task* is cancelled twice over - explicitly here and by Home Assistant,
    which owns every ``config_entry.async_create_background_task`` - so removing
    the explicit ``task.cancel()`` is invisible on this path. It is not invisible
    on the service path, which is where
    ``test_stopping_mid_scan_does_not_leave_the_worker_running`` pins it.
    """
    async with running_gateway(hass, tmp_path) as entry:
        service = hass.data[DOMAIN][MAC][CONF_ENTITY].discovery_service
        completed = completed_events(hass)

        # The worker is parked mid-scan, between two paced status requests: this is
        # the state `_stopped.set()` alone cannot get it out of, so only the
        # cancellation can, and the assertions below are about the cancellation.
        with no_discovery_sleep(hold_from=1) as sleeps:
            await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()
            task = service._discovery_task  # noqa: SLF001
            timer = service._timer_handle  # noqa: SLF001
            assert task is not None and not task.done()
            await wait_until(lambda: bool(sleeps.delays))

            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()

    assert task.cancelled()
    assert timer.cancelled()
    assert service.is_discovery_active() is False
    assert service._discovery_task is None  # noqa: SLF001
    assert service._timer_handle is None  # noqa: SLF001
    # The suggestions are flushed on the way out, so a run interrupted by a reload
    # still leaves the user the YAML it had collected.
    assert [item["reason"] for item in completed] == ["stopped"]


def test_every_discovery_command_reaches_the_bus() -> None:
    """Every entry of ``_DISCOVERY_COMMANDS`` must be a frame OWNd can build.

    The list is the definition of what a discovery run scans; an entry OWNd cannot
    parse is a silent hole in that scan. `*#25*0##` used to be such a hole: OWNd
    0.7.49 refuses to build it, so the WHO 25 "scan" never left the machine. The
    entry is gone and the docs say what that means; this test keeps the list honest.
    """
    unparsable = [
        raw
        for raw in discovery_module._DISCOVERY_COMMANDS  # noqa: SLF001 - the list under test
        if (command := OWNCommand.parse(raw)) is None or not command.is_valid
    ]
    assert unparsable == []


async def test_stopping_mid_scan_does_not_leave_the_worker_running(
    hass: HomeAssistant, tmp_path
) -> None:
    """``myhome.stop_discovery`` must end the worker, not merely ask it to notice.

    ``_send_discovery_commands`` only re-reads ``_discovery_active`` between two
    paced requests, so a worker parked in that 0.5 s gap cannot see the flag or the
    ``_stopped`` event: nothing but the cancellation gets it out. Mutation caught:
    dropping the ``task.cancel()`` / ``await task`` block from ``stop_discovery``,
    after which the service call returns while the scan is still going, keeps
    pushing broadcast requests at a gateway the user just told it to leave alone,
    and the next ``start_discovery`` runs alongside it.

    (On the unload path Home Assistant cancels the background task itself, which is
    why that mutation is only visible from here.)
    """
    async with running_gateway(hass, tmp_path) as entry:
        service = hass.data[DOMAIN][MAC][CONF_ENTITY].discovery_service

        with no_discovery_sleep(hold_from=1) as sleeps:
            await hass.services.async_call(DOMAIN, SERVICE_START_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()
            task = service._discovery_task  # noqa: SLF001
            await wait_until(lambda: bool(sleeps.delays))
            assert not task.done()  # parked between two requests

            await hass.services.async_call(DOMAIN, SERVICE_STOP_DISCOVERY, {}, blocking=True)
            await hass.async_block_till_done()
            assert task.cancelled()

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
