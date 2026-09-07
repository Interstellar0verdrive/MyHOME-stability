"""Tests for the MyHOME sensor platform (Contract C/E, findings sc-04/05/11/12/15/17/18).

The gateway is mocked exactly like in ``test_init.py``: no socket is opened and the
sending loop is idle, so every command the entities produce stays in
``handler.send_buffer`` where the tests can inspect it.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.sensor import DOMAIN as SENSOR, SensorDeviceClass
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, EntityCategory
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util
from OWNd.message import OWNEnergyEvent, OWNHeatingEvent, OWNLightingEvent
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import (
    CONF_DEFAULT_KEEPALIVE_MINUTES,
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_KEEPALIVE_MINUTES,
    CONF_PLATFORMS,
    DOMAIN,
    GATEWAY_DIAG_COMMANDS_DROPPED,
    GATEWAY_DIAG_LAST_FRAME,
    GATEWAY_DIAG_QUEUE_LENGTH,
    GATEWAY_DIAG_RECONNECTS,
    SIGNAL_GATEWAY_CONNECTION,
)
from custom_components.myhome.sensor import (
    CONF_KEEPALIVE_MINUTES_DEFAULTED,
    keepalive_minutes_for,
)

from .helpers_core import MAC, make_entry, mock_gateway, write_yaml
from .helpers_platforms import (
    GATEWAY_DIAG_UNIQUE_IDS,
    diagnostic_entity_id,
    dispatch_stats,
    feed_frame,
)

# The user's real configuration: three WHO=18 meters (one with a per-sensor override),
# plus a thermo probe and an illuminance sensor to cover the other two sensor classes.
SENSOR_YAML = f"""
gateway:
  mac: {MAC}
  sensor_defaults:
    min_delta_w: 5
    min_interval_sec: 5
    suppress_log_interval_sec: 60
  sensor:
    mains_power:
      where: '51'
      name: Mains Power
      device_class: power
    fridge:
      where: '52'
      name: Fridge
      device_class: power
    oven:
      where: '53'
      name: Oven
      device_class: power
      min_delta_w: 1
    sonda_salotto:
      where: '2'
      name: Sonda Salotto
      device_class: temperature
    luminosita_ingresso:
      where: '31'
      name: Luminosita Ingresso
      device_class: illuminance
"""

NO_KEEPALIVE_YAML = f"""
gateway:
  mac: {MAC}
  sensor_defaults:
    keepalive_minutes: 0
  sensor:
    mains_power:
      where: '51'
      name: Mains Power
      device_class: power
"""

# Only a light: the four gateway diagnostic sensors must be created anyway (G1-B).
NO_SENSOR_YAML = f"""
gateway:
  mac: {MAC}
  light:
    light_test:
      where: '11'
      name: Light Test
"""

# One meter without `keepalive_minutes` (validate.py injects the built-in 125 and marks
# it, so the `default_keepalive_minutes` option wins), one that sets a different value
# and one that writes the built-in default itself: the last two are the user's choice
# and the option must not touch them (RISK-1).
KEEPALIVE_OPTION_YAML = f"""
gateway:
  mac: {MAC}
  sensor:
    mains_power:
      where: '51'
      name: Mains Power
      device_class: power
    kitchen:
      where: '52'
      name: Kitchen
      device_class: power
      keepalive_minutes: 60
    garden:
      where: '53'
      name: Garden
      device_class: power
      keepalive_minutes: 125
"""

# P5-BUG-1: the WHERE of a thermo probe is a zone, written here the way a careful user
# writes it - quoted and padded, as the validator's own advice and the documented
# actuator addresses both suggest.
PADDED_PROBE_YAML = f"""
gateway:
  mac: {MAC}
  sensor:
    sonda_uno:
      where: '01'
      name: Sonda Uno
      device_class: temperature
"""

POWER_ENTITY = "sensor.mains_power_power"
TOTAL_ENTITY = "sensor.mains_power_energy"
DAILY_ENTITY = "sensor.mains_power_energy_today"
MONTHLY_ENTITY = "sensor.mains_power_energy_this_month"
TEMPERATURE_ENTITY = "sensor.sonda_salotto"
ILLUMINANCE_ENTITY = "sensor.luminosita_ingresso"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry, *, connect: bool = True) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    if connect:
        # The mocked listening loop never marks the session up, but the entities are
        # only available (and only write states) while the gateway is connected.
        _connect(hass)
        await hass.async_block_till_done()


def _handler(hass: HomeAssistant):
    return hass.data[DOMAIN][MAC][CONF_ENTITY]


def _connect(hass: HomeAssistant, connected: bool = True) -> None:
    """Mark the mocked gateway session as up so the entities are available."""
    handler = _handler(hass)
    if hasattr(handler, "_set_connected"):
        handler._set_connected(connected)  # noqa: SLF001 - Contract B helper
    else:  # pragma: no cover - older gateway.py
        handler.is_connected = connected
        async_dispatcher_send(hass, SIGNAL_GATEWAY_CONNECTION.format(mac=MAC), connected)


def _drain(hass: HomeAssistant) -> list[str]:
    """Empty the gateway send buffer and return the frames as strings."""
    handler = _handler(hass)
    frames: list[str] = []
    while not handler.send_buffer.empty():
        item = handler.send_buffer.get_nowait()
        # Contract B queues a small dataclass; older builds queued a dict.
        message = item["message"] if isinstance(item, dict) else item.message
        frames.append(str(message))
    return frames


async def _advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **delta) -> None:
    """Move the frozen clock and fire the timers due at the new time.

    F16: these tests used to pass ``dt_util.utcnow() + timedelta(...)`` to
    ``async_fire_time_changed`` while the clock kept running, so a run started a few
    minutes before local midnight also fired the daily/monthly boundary callback.
    """
    freezer.tick(timedelta(**delta))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _entity_object(hass: HomeAssistant, device_key: str, slot: str):
    return hass.data[DOMAIN][MAC][CONF_PLATFORMS]["sensor"][device_key][CONF_ENTITIES][slot]


async def _enable_disabled_entities(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Enable the entities that are disabled by default and reload the entry."""
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION:
            registry.async_update_entity(entity.entity_id, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    _connect(hass)
    await hass.async_block_till_done()


# --------------------------------------------------------------------------- entities
async def test_entities_and_unique_ids(hass: HomeAssistant, tmp_path) -> None:
    """Every configured slot exists and the unique ids match expected_unique_ids()."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)

        registry = er.async_get(hass)
        created = {
            e.unique_id for e in er.async_entries_for_config_entry(registry, entry.entry_id)
        }
        assert created == expected_unique_ids(MAC, hass.data[DOMAIN][MAC][CONF_PLATFORMS])

        # sc-12: the ids keep the historical format, so existing entity ids survive.
        for where in ("51", "52", "53"):
            for suffix in ("power", "daily-energy", "monthly-energy", "total-energy"):
                assert f"{MAC}-18-{where}-{suffix}" in created
        assert f"{MAC}-4-2-temperature" in created
        assert f"{MAC}-1-31-illuminance" in created

        # Enabled by default: power + total energy; daily/monthly stay opt-in.
        # (The two enabled ones are checked by the Contract C loop below.)
        assert hass.states.get(DAILY_ENTITY) is None
        assert registry.async_get(DAILY_ENTITY).disabled_by is er.RegistryEntryDisabler.INTEGRATION

        # Contract C: nothing is polled, the entities drive their own timers.
        for entity_id in (POWER_ENTITY, TOTAL_ENTITY, TEMPERATURE_ENTITY, ILLUMINANCE_ENTITY):
            assert hass.states.get(entity_id) is not None
        assert _entity_object(hass, "18-51", "power").should_poll is False
        assert _entity_object(hass, "18-51", "total-energy").should_poll is False


ENERGY_ONLY_YAML = f"""
gateway:
  mac: {MAC}
  sensor:
    garden_meter:
      where: '54'
      name: Garden Meter
      class: energy
"""

# `entity_name` on a power meter, an `icon` on a probe, and an illuminance sensor
# behind an F422 local bus.
NAMED_SENSOR_YAML = f"""
gateway:
  mac: {MAC}
  sensor:
    mains_power:
      where: '51'
      name: Mains Power
      class: power
      entity_name: Mains
    study_probe:
      where: '2'
      name: Study Probe
      class: temperature
      icon: 'mdi:thermometer-lines'
    hall_light_level:
      where: '31'
      name: Hall Light Level
      class: illuminance
      interface: 3
"""


# A WHO 1 sensor behind an F422: the configuration keeps the interface zero padded
# (it is the tail of the unique id), the bus writes it unpadded.
INTERFACE_SENSOR_YAML = f"""
gateway:
  mac: {MAC}
  sensor:
    hall_light_level:
      where: '31'
      name: Hall Light Level
      class: illuminance
      interface: 3
      min_delta_w: 42
"""


async def test_sensor_config_lookup_normalises_the_bus_interface(hass: HomeAssistant, tmp_path) -> None:
    """NIT-6: the energy throttle looked the sensor up with the raw key.

    ``_dispatch_to_entities`` resolves ``1-31#4#3`` (as the bus writes it) against the
    configured ``1-31#4#03``; the throttle did not, so it would have fallen back to the
    built-in defaults for a device whose key came from a frame.
    """
    entry = make_entry(write_yaml(tmp_path, INTERFACE_SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        handler = _handler(hass)
        assert "1-31#4#03" in hass.data[DOMAIN][MAC][CONF_PLATFORMS]["sensor"]

        for key in ("1-31#4#03", "1-31#4#3"):
            assert handler._sensor_display_name(key) == "Hall Light Level"
            assert handler._energy_settings_for(key).min_delta_w == 42


async def test_class_energy_creates_only_the_three_totalisers(hass: HomeAssistant, tmp_path) -> None:
    """INCONSISTENCY-6: `class: energy` is not a lighter `class: power`.

    It creates the three totalisers and nothing else - no Power entity, no instant
    power stream - so the keep-alive and filter keys have no effect on such a device.

    "only" is asserted as an exact set, not with ``in`` / ``not in``: the old form
    accepted any number of extra entities, so a regression that also built the
    Power entity (and with it the instant-power keep-alive this class exists to
    avoid) would have kept it green. Mutation caught: adding any further slot to
    the ``class: energy`` branch of ``sensor.async_setup_entry``.
    """
    entry = make_entry(write_yaml(tmp_path, ENERGY_ONLY_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        registry = er.async_get(hass)
        entries = er.async_entries_for_config_entry(registry, entry.entry_id)
        created = {e.unique_id for e in entries}
        assert created == {
            f"{MAC}-18-54-{suffix}" for suffix in ("daily-energy", "monthly-energy", "total-energy")
        } | GATEWAY_DIAG_UNIQUE_IDS
        # Only the total is enabled by default; nothing arms the instant power stream.
        disabled_by = {e.unique_id: e.disabled_by for e in entries}
        assert disabled_by[f"{MAC}-18-54-total-energy"] is None
        for suffix in ("daily-energy", "monthly-energy"):
            assert disabled_by[f"{MAC}-18-54-{suffix}"] is er.RegistryEntryDisabler.INTEGRATION
        assert hass.states.get("sensor.garden_meter_energy") is not None
        assert [f for f in _drain(hass) if "#1200#1" in f] == []


async def test_entity_name_icon_and_interface_on_sensors(hass: HomeAssistant, tmp_path) -> None:
    """INCONSISTENCY-1 / INCONSISTENCY-2 / BUG-1 on the sensor platform."""
    entry = make_entry(write_yaml(tmp_path, NAMED_SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)

        # INCONSISTENCY-2: `entity_name` reaches the Power entity (the meter's main
        # entity); the totalisers keep their own translated names.
        power = hass.states.get("sensor.mains_power_mains")
        assert power is not None
        assert power.attributes["friendly_name"] == "Mains Power Mains"
        assert hass.states.get("sensor.mains_power_energy").attributes["friendly_name"] == (
            "Mains Power Energy"
        )

        # INCONSISTENCY-1: `icon` was accepted, documented and ignored on this platform.
        assert hass.states.get("sensor.study_probe").attributes["icon"] == "mdi:thermometer-lines"

        # BUG-1: a WHO 1 sensor behind a bus interface must query `31#4#3`, not `31`.
        lux = hass.states.get("sensor.hall_light_level")
        assert lux.attributes["Int"] == "3"
        assert "*#1*31#4#3*6##" in _drain(hass)


async def test_names_do_not_repeat_the_device_name(hass: HomeAssistant, tmp_path) -> None:
    """sc-05: 'Mains Power Mains Power Power' is gone; translation keys are used."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)

        assert hass.states.get(POWER_ENTITY).attributes["friendly_name"] == "Mains Power Power"
        assert hass.states.get(TOTAL_ENTITY).attributes["friendly_name"] == "Mains Power Energy"
        # Single-entity devices keep the device name (Contract C).
        assert hass.states.get(TEMPERATURE_ENTITY).attributes["friendly_name"] == "Sonda Salotto"

        assert _entity_object(hass, "18-51", "power").translation_key == "power"
        assert _entity_object(hass, "18-51", "total-energy").translation_key == "energy_total"

        # sc-17: the meaningless "(5)1" attribute is gone; A/PL stays on the WHO=1 sensor.
        assert "Sensor" not in hass.states.get(POWER_ENTITY).attributes
        assert hass.states.get(ILLUMINANCE_ENTITY).attributes["A"] == "3"


# ------------------------------------------------------------------- keep-alive (E)
async def test_instant_power_keepalive(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Contract E: armed at add, on every connection signal and on the interval.

    F16: the three meters arm through independent tasks, so the *set* of frames is the
    contract, not their order.
    """
    armed_frames = {
        "*#18*51*#1200#1*125##",
        "*#18*52*#1200#1*125##",
        "*#18*53*#1200#1*125##",
    }
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry, connect=False)

        # Armed once for each meter when the entities were added.
        assert {f for f in _drain(hass) if "#1200#1" in f} == armed_frames

        # Reconnect -> re-arm.
        _connect(hass)
        await hass.async_block_till_done()
        assert {f for f in _drain(hass) if "#1200#1" in f} == armed_frames

        # A disconnection must not send anything.
        _connect(hass, False)
        await hass.async_block_till_done()
        assert [f for f in _drain(hass) if "#1200#1" in f] == []

        # keepalive_minutes (125) - 5 -> re-armed every 120 minutes.
        await _advance(hass, freezer, minutes=121)
        assert len([f for f in _drain(hass) if "#1200#1" in f]) == 3


async def test_keepalive_can_be_disabled(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """keepalive_minutes: 0 disables the automatic arming entirely."""
    entry = make_entry(write_yaml(tmp_path, NO_KEEPALIVE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        assert [f for f in _drain(hass) if "#1200#1" in f] == []

        await _advance(hass, freezer, minutes=300)
        assert [f for f in _drain(hass) if "#1200#1" in f] == []

        # The service still works and falls back to the built-in default.
        await hass.services.async_call(
            DOMAIN,
            "start_sending_instant_power",
            {"entity_id": POWER_ENTITY},
            blocking=True,
        )
        assert [f for f in _drain(hass) if "#1200#1" in f] == ["*#18*51*#1200#1*125##"]


async def test_instant_power_service_duration(hass: HomeAssistant, tmp_path) -> None:
    """sc-04: `duration` is optional (defaults to keepalive_minutes) and honoured."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        _drain(hass)

        await hass.services.async_call(
            DOMAIN, "start_sending_instant_power", {"entity_id": POWER_ENTITY}, blocking=True
        )
        assert [f for f in _drain(hass) if "#1200#1" in f] == ["*#18*51*#1200#1*125##"]

        await hass.services.async_call(
            DOMAIN,
            "start_sending_instant_power",
            {"entity_id": POWER_ENTITY, "duration": 30},
            blocking=True,
        )
        assert [f for f in _drain(hass) if "#1200#1" in f] == ["*#18*51*#1200#1*30##"]


async def test_power_value_from_event(hass: HomeAssistant, tmp_path) -> None:
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        power = _entity_object(hass, "18-51", "power")
        power.handle_event(OWNEnergyEvent("*#18*51*113*613##"))
        await hass.async_block_till_done()
        assert hass.states.get(POWER_ENTITY).state == "613"

        # A totaliser frame belongs to a sibling entity and must be ignored.
        power.handle_event(OWNEnergyEvent("*#18*51*51*1234##"))
        await hass.async_block_till_done()
        assert hass.states.get(POWER_ENTITY).state == "613"


# ------------------------------------------------------------------------- energy
async def test_energy_requests_and_updates(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """sc-01/sc-18: totals are requested at add, refreshed, and only own frames apply."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        await _enable_disabled_entities(hass, entry)
        assert _entity_object(hass, "18-51", "daily-energy").translation_key == "energy_today"
        assert _entity_object(hass, "18-51", "monthly-energy").translation_key == "energy_month"

        requests = [f for f in _drain(hass) if f.startswith("*#18") and "#1200" not in f]
        for frame in ("*#18*51*51##", "*#18*51*54##", "*#18*51*53##"):
            assert frame in requests

        total = _entity_object(hass, "18-51", "total-energy")
        daily = _entity_object(hass, "18-51", "daily-energy")
        monthly = _entity_object(hass, "18-51", "monthly-energy")

        total.handle_event(OWNEnergyEvent("*#18*51*51*1234##"))
        daily.handle_event(OWNEnergyEvent("*#18*51*54*77##"))
        monthly.handle_event(OWNEnergyEvent("*#18*51*53*888##"))
        await hass.async_block_till_done()

        assert hass.states.get(TOTAL_ENTITY).state == "1234"
        assert hass.states.get(DAILY_ENTITY).state == "77"
        assert hass.states.get(MONTHLY_ENTITY).state == "888"
        assert hass.states.get(TOTAL_ENTITY).attributes["state_class"] == "total_increasing"

        # A frame for a sibling entity leaves this one alone (sc-18).
        total.handle_event(OWNEnergyEvent("*#18*51*54*99##"))
        await hass.async_block_till_done()
        assert hass.states.get(TOTAL_ENTITY).state == "1234"

        # Periodic refresh (5 minutes) and the midnight boundary for daily/monthly.
        _drain(hass)
        await _advance(hass, freezer, minutes=6)
        refreshed = _drain(hass)
        assert "*#18*51*51##" in refreshed
        assert "*#18*51*54##" in refreshed


async def test_energy_restores_previous_value(hass: HomeAssistant, tmp_path) -> None:
    """sc-11: a restart no longer leaves the totaliser `unknown`."""
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State(TOTAL_ENTITY, "4242"),
                {"native_value": 4242, "native_unit_of_measurement": "Wh"},
            ),
        ),
    )
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        assert hass.states.get(TOTAL_ENTITY).state == "4242"


async def test_energy_ignores_implausible_values(hass: HomeAssistant, tmp_path) -> None:
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        total = _entity_object(hass, "18-51", "total-energy")
        total.handle_event(OWNEnergyEvent("*#18*51*51*1234##"))
        await hass.async_block_till_done()

        event = OWNEnergyEvent("*#18*51*51*1234##")
        event._total_consumption = -5  # noqa: SLF001 - simulate a corrupted frame
        total.handle_event(event)
        event._total_consumption = None  # noqa: SLF001
        total.handle_event(event)
        await hass.async_block_till_done()
        assert hass.states.get(TOTAL_ENTITY).state == "1234"


# ------------------------------------------------------- temperature / illuminance
async def test_temperature_and_illuminance(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """sc-15: both are requested at add and re-requested on a timer, never polled."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        initial = _drain(hass)
        assert "*#4*2*0##" in initial
        assert "*#1*31*6##" in initial

        await _advance(hass, freezer, minutes=6)
        refreshed = _drain(hass)
        assert "*#4*2*0##" in refreshed
        assert "*#1*31*6##" in refreshed

        _entity_object(hass, "4-2", "temperature").handle_event(
            OWNHeatingEvent("*#4*2*0*0250*3##")
        )
        _entity_object(hass, "1-31", "illuminance").handle_event(
            OWNLightingEvent("*#1*31*6*450##")
        )
        await hass.async_block_till_done()
        assert hass.states.get(TEMPERATURE_ENTITY).state == "25.0"
        assert hass.states.get(ILLUMINANCE_ENTITY).state == "450"


async def test_a_padded_temperature_probe_receives_its_frames(hass: HomeAssistant, tmp_path) -> None:
    """P5-BUG-1, end to end: ``where: '01'`` used to key ``4-01`` and never meet a frame.

    Routed through ``feed_frame`` (and therefore through the gateway dispatcher) on
    purpose: this is a test about the *key a frame is looked up by*, which
    ``feed_event`` bypasses by handing the message to the entity itself. Before the
    fix the entity existed, was named, was available and stayed ``unknown`` for ever.
    """
    entry = make_entry(write_yaml(tmp_path, PADDED_PROBE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        await feed_frame(hass, "*#4*1*0*0215##")
        assert hass.states.get("sensor.sonda_uno").state == "21.5"


async def test_pending_refresh_does_not_outlive_the_entity(hass: HomeAssistant, tmp_path) -> None:
    """RISK-4: the refresh tasks were tied to neither the entity nor the config entry.

    A refresh still in flight when the entry is reloaded could call
    ``send_status_request`` on a handler ``close_listener()`` had already torn down.
    The entity now keeps the handle and cancels it on the way out.
    """
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        sensor = _entity_object(hass, "4-2", "temperature")
        _drain(hass)

        started = asyncio.Event()
        release = asyncio.Event()
        late_requests: list[str] = []

        async def _blocking_update() -> None:
            started.set()
            await release.wait()
            late_requests.append("request sent after removal")

        sensor.async_update = _blocking_update
        sensor._async_periodic_refresh(dt_util.utcnow())  # the timer callback
        await started.wait()
        (task,) = sensor._pending_updates  # the handle is the fix

        await sensor.async_will_remove_from_hass()
        release.set()
        await hass.async_block_till_done()

        assert task.cancelled()
        assert late_requests == []
        assert not sensor._pending_updates


async def test_unload_drains_the_entities_registry_dict(hass: HomeAssistant, tmp_path) -> None:
    """sc-13: no platform-level async_unload_entry; the entities unregister themselves.

    This used to assert ``MAC not in hass.data[DOMAIN]``, which is ``__init__``'s
    ``async_unload_entry`` dropping the whole per-gateway dict and says nothing
    about ``MyHOMEEntity.async_will_remove_from_hass`` - the code the name refers
    to. Replacing that method's body with ``return`` left the suite green.

    The bug it now catches is the classic reload leak: a stale entity object left
    in ``hass.data[...][CONF_ENTITIES]``, so after a reload the gateway dispatcher
    keeps pushing frames into an entity that is detached from ``hass``. The dict
    object is captured *before* the unload, so the ``__init__`` teardown cannot be
    what empties it.

    ``daily-energy`` and ``monthly-energy`` are disabled by default: they are never
    added to ``hass``, so nothing ever removes them and they correctly stay behind.
    That asymmetry is the proof that the two enabled slots left by themselves.
    """
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entities = hass.data[DOMAIN][MAC][CONF_PLATFORMS]["sensor"]["18-51"][CONF_ENTITIES]
        assert set(entities) == {"power", "daily-energy", "monthly-energy", "total-energy"}
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert set(entities) == {"daily-energy", "monthly-energy"}
    assert MAC not in hass.data[DOMAIN]

    import custom_components.myhome.sensor as sensor_module

    assert not hasattr(sensor_module, "async_unload_entry")


# ----------------------------------------------------- keep-alive default option
def test_keepalive_minutes_for_option_precedence(tmp_path) -> None:
    """The option only replaces a keep-alive the user did not write herself."""
    entry = make_entry(tmp_path / "myhome.yaml", options={CONF_DEFAULT_KEEPALIVE_MINUTES: 30})
    plain = make_entry(tmp_path / "myhome.yaml")

    # validate.py marks the injected default -> the option wins whatever the value.
    assert keepalive_minutes_for({CONF_KEEPALIVE_MINUTES: 125, CONF_KEEPALIVE_MINUTES_DEFAULTED: True}, entry) == 30
    assert keepalive_minutes_for({CONF_KEEPALIVE_MINUTES: 60, CONF_KEEPALIVE_MINUTES_DEFAULTED: True}, entry) == 30
    # Explicitly marked as user-provided -> YAML wins.
    assert keepalive_minutes_for({CONF_KEEPALIVE_MINUTES: 60, CONF_KEEPALIVE_MINUTES_DEFAULTED: False}, entry) == 60
    # RISK-1: without the marker the value is the user's, whatever it is.  The old
    # fallback (value == DEFAULT_KEEPALIVE_MINUTES) silently overrode an explicit
    # `keepalive_minutes: 125`, which docs/configuration.md promises never happens.
    assert keepalive_minutes_for({CONF_KEEPALIVE_MINUTES: 125}, entry) == 125
    assert keepalive_minutes_for({CONF_KEEPALIVE_MINUTES: 60}, entry) == 60
    assert keepalive_minutes_for({CONF_KEEPALIVE_MINUTES: 0}, entry) == 0
    # Without the option nothing changes at all.
    assert keepalive_minutes_for({CONF_KEEPALIVE_MINUTES: 125}, plain) == 125


@pytest.mark.parametrize("option", ["abc", "", "30.0", None, "inf", "-inf", 1e400, float("nan")])
def test_keepalive_option_that_is_not_an_int_never_breaks_the_platform(tmp_path, caplog, option) -> None:
    """P2-NIT-1: `int(option)` was the one TUNABLE_OPTIONS read without a defensive parse.

    A hand-edited `.storage` entry raised `ValueError` inside `sensor.async_setup_entry`,
    taking the whole sensor platform - the four gateway diagnostic sensors included -
    down with it. `gateway._option()` and `__init__`'s `worker_count` both promise the
    opposite for this family of options.

    P3-NIT-4: the infinities go through `float()` happily and only `int()` refuses
    them, with `OverflowError` - which the first version of the parse did not catch,
    so they escaped through the very gap it was written to close. `nan` raises
    `ValueError` and was caught all along; it is here so the pair cannot drift apart.
    """
    entry = make_entry(tmp_path / "myhome.yaml", options={CONF_DEFAULT_KEEPALIVE_MINUTES: option})
    device = {CONF_KEEPALIVE_MINUTES: 125, CONF_KEEPALIVE_MINUTES_DEFAULTED: True}
    with caplog.at_level(logging.WARNING, logger="custom_components.myhome"):
        result = keepalive_minutes_for(device, entry)
    if option == "30.0":
        # A number that merely does not spell as an int is used, not thrown away.
        assert result == 30
        assert "is not a number" not in caplog.text
    elif option is None:
        # No option at all: the configured value, silently.
        assert result == 125
        assert "is not a number" not in caplog.text
    else:
        assert result == 125
        assert "is not a number" in caplog.text


async def test_default_keepalive_option_is_used(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """G1-D: `default_keepalive_minutes` replaces the injected default, not a YAML value.

    RISK-1: `garden` writes exactly the built-in default (125).  It used to be
    indistinguishable from a meter with no `keepalive_minutes` at all, so the option
    replaced it and the user lost that meter's stream without a single log line.
    """
    entry = make_entry(
        write_yaml(tmp_path, KEEPALIVE_OPTION_YAML),
        options={CONF_DEFAULT_KEEPALIVE_MINUTES: 30},
    )
    with mock_gateway():
        await _setup(hass, entry, connect=False)
        armed = {f for f in _drain(hass) if "#1200#1" in f}
        assert armed == {
            "*#18*51*#1200#1*30##",
            "*#18*52*#1200#1*60##",
            "*#18*53*#1200#1*125##",
        }

        # The re-arm interval follows the effective value (30 - 5 = 25 minutes).
        freezer.tick(timedelta(minutes=26))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert "*#18*51*#1200#1*30##" in _drain(hass)


# --------------------------------------------------- temperature / illuminance (E)
async def test_environment_sensors_requested_on_reconnect(hass: HomeAssistant, tmp_path) -> None:
    """G1-E: temperature and illuminance are re-requested on every connection signal."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry, connect=False)
        _drain(hass)

        _connect(hass)
        await hass.async_block_till_done()
        reconnected = _drain(hass)
        assert "*#4*2*0##" in reconnected
        assert "*#1*31*6##" in reconnected

        # A disconnection asks for nothing.
        _connect(hass, False)
        await hass.async_block_till_done()
        idle = _drain(hass)
        assert "*#4*2*0##" not in idle
        assert "*#1*31*6##" not in idle


# ------------------------------------------------------------- gateway diagnostics
async def test_gateway_diagnostic_sensors(hass: HomeAssistant, tmp_path) -> None:
    """G1-B: four diagnostic sensors on the gateway device, fed by the stats signal."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        registry = er.async_get(hass)

        expected_flags = {
            GATEWAY_DIAG_LAST_FRAME: (None, True),
            GATEWAY_DIAG_RECONNECTS: ("total_increasing", False),
            GATEWAY_DIAG_COMMANDS_DROPPED: ("total_increasing", False),
            GATEWAY_DIAG_QUEUE_LENGTH: ("measurement", False),
        }
        # Registry-level flags first; the state classes need the counters enabled.
        for suffix, (_state_class, enabled) in expected_flags.items():
            entity_id = diagnostic_entity_id(hass, SENSOR, suffix)
            assert entity_id is not None, suffix
            registry_entry = registry.async_get(entity_id)
            assert registry_entry.unique_id == f"{MAC}-{suffix}"
            assert registry_entry.entity_category is EntityCategory.DIAGNOSTIC
            assert (registry_entry.disabled_by is None) is enabled, suffix

        last_frame_id = diagnostic_entity_id(hass, SENSOR, GATEWAY_DIAG_LAST_FRAME)
        assert registry.async_get(last_frame_id).original_device_class is SensorDeviceClass.TIMESTAMP

        # The three counters are disabled by default; enable them and check the states.
        await _enable_disabled_entities(hass, entry)
        # Home Assistant renders a timestamp state with second precision.
        stamp = dt_util.utcnow().replace(microsecond=0)
        await dispatch_stats(
            hass,
            connected=True,
            last_frame_at=stamp,
            frames_rx=12,
            reconnects=3,
            commands_dropped=2,
            queue_length=7,
            session_state="connected",
        )

        assert hass.states.get(diagnostic_entity_id(hass, SENSOR, GATEWAY_DIAG_LAST_FRAME)).state == stamp.isoformat()
        assert hass.states.get(diagnostic_entity_id(hass, SENSOR, GATEWAY_DIAG_RECONNECTS)).state == "3"
        assert hass.states.get(diagnostic_entity_id(hass, SENSOR, GATEWAY_DIAG_COMMANDS_DROPPED)).state == "2"
        assert hass.states.get(diagnostic_entity_id(hass, SENSOR, GATEWAY_DIAG_QUEUE_LENGTH)).state == "7"

        # The first element of `expected_flags` was computed and thrown away, so only
        # queue_length's state class was ever checked. A counter silently downgraded
        # from `total_increasing` to `measurement` breaks Home Assistant's long-term
        # statistics for it - the whole reason these entities exist - and nothing
        # noticed. Mutation caught: either counter's `_attr_state_class`.
        for suffix, (state_class, _enabled) in expected_flags.items():
            state = hass.states.get(diagnostic_entity_id(hass, SENSOR, suffix))
            assert state.attributes.get("state_class") == state_class, suffix


async def test_gateway_diagnostic_sensors_stay_available(hass: HomeAssistant, tmp_path) -> None:
    """They report the outage, so they must not become `unavailable` during one."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)

        _connect(hass, False)
        await hass.async_block_till_done()
        stamp = dt_util.utcnow().replace(microsecond=0)
        await dispatch_stats(hass, connected=False, last_frame_at=stamp, session_state="disconnected")

        # The bus entities are unavailable, the diagnostic ones still report a value.
        assert hass.states.get(POWER_ENTITY).state == STATE_UNAVAILABLE
        last_frame = hass.states.get(diagnostic_entity_id(hass, SENSOR, GATEWAY_DIAG_LAST_FRAME))
        assert last_frame.state == stamp.isoformat()


async def test_gateway_diagnostic_sensors_without_sensors(hass: HomeAssistant, tmp_path) -> None:
    """They exist even when the configuration declares no sensor at all."""
    entry = make_entry(write_yaml(tmp_path, NO_SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity_id = diagnostic_entity_id(hass, SENSOR, GATEWAY_DIAG_LAST_FRAME)
        assert entity_id is not None
        stamp = dt_util.utcnow().replace(microsecond=0)
        await dispatch_stats(hass, connected=True, last_frame_at=stamp, session_state="connected")
        assert hass.states.get(entity_id).state == stamp.isoformat()
