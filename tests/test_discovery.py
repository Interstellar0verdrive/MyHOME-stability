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
    DEVICE_TYPE_BUS_ALARM_ZONE,
    DEVICE_TYPE_BUS_AUX,
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_CENPLUS_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DOMAIN,
    SERVICE_START_DISCOVERY,
    SERVICE_STOP_DISCOVERY,
)
from custom_components.myhome.discovery import (
    DISCOVERY_TIMEOUT_SEC,
    MyHOMEDeviceDiscoveryService,
)

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


@asynccontextmanager
async def running_gateway(hass: HomeAssistant, tmp_path) -> AsyncIterator[Any]:
    """A loaded config entry with the real handler and its real discovery service."""
    entry = make_entry(write_yaml(tmp_path))
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
            # `*#25*0##` is missing on purpose: OWNd 0.7.49 cannot parse it and
            # `_send_discovery_commands` skips it - see
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG: `*#25*0##` never leaves the machine. `_DISCOVERY_COMMANDS` lists six "
        "broadcast status requests, one of them the CEN / dry-contact scan, but "
        "`OWNCommand.parse('*#25*0##')` returns None on OWNd 0.7.49, so "
        "`_send_discovery_commands` logs a DEBUG line and skips it. A discovery run "
        "therefore never asks WHO 25 anything: a scenario control is found only if "
        "somebody happens to press one of its buttons inside the 60-second window, "
        "which is exactly the device the user most needs discovery's help to declare. "
        "Fix belongs in custom_components/ (build the command another way, or drop "
        "the entry and say so), so this test is left failing on purpose."
    ),
)
def test_every_discovery_command_reaches_the_bus() -> None:
    """Every entry of ``_DISCOVERY_COMMANDS`` must be a frame OWNd can build.

    The list is the definition of what a discovery run scans; an entry OWNd cannot
    parse is a silent hole in that scan, visible to the user only as "discovery
    never finds my keypad".
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
