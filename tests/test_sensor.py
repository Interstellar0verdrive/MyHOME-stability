"""Tests for the MyHOME sensor platform (Contract C/E, findings sc-04/05/11/12/15/17/18).

The gateway is mocked exactly like in ``test_init.py``: no socket is opened and the
sending loop is idle, so every command the entities produce stays in
``handler.send_buffer`` where the tests can inspect it.
"""

from __future__ import annotations

from datetime import timedelta

from OWNd.message import OWNEnergyEvent, OWNHeatingEvent, OWNLightingEvent

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache_with_extra_data,
)

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import (
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_PLATFORMS,
    DOMAIN,
    SIGNAL_GATEWAY_CONNECTION,
)

from .helpers_core import MAC, make_entry, mock_gateway, write_yaml

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
    casa_generale:
      where: '51'
      name: Casa Generale
      device_class: power
    elettrodomestico_cucina_frigo:
      where: '52'
      name: Elettrodomestico Cucina Frigo
      device_class: power
    elettrodomestico_cucina_forno:
      where: '53'
      name: Elettrodomestico Cucina Forno
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
    casa_generale:
      where: '51'
      name: Casa Generale
      device_class: power
"""

POWER_ENTITY = "sensor.casa_generale_power"
TOTAL_ENTITY = "sensor.casa_generale_energy"
DAILY_ENTITY = "sensor.casa_generale_energy_today"
MONTHLY_ENTITY = "sensor.casa_generale_energy_this_month"
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
        assert hass.states.get(POWER_ENTITY) is not None
        assert hass.states.get(TOTAL_ENTITY) is not None
        assert hass.states.get(DAILY_ENTITY) is None
        assert registry.async_get(DAILY_ENTITY).disabled_by is er.RegistryEntryDisabler.INTEGRATION

        # Contract C: nothing is polled, the entities drive their own timers.
        for entity_id in (POWER_ENTITY, TOTAL_ENTITY, TEMPERATURE_ENTITY, ILLUMINANCE_ENTITY):
            assert hass.states.get(entity_id) is not None
        assert _entity_object(hass, "18-51", "power").should_poll is False
        assert _entity_object(hass, "18-51", "total-energy").should_poll is False


async def test_names_do_not_repeat_the_device_name(hass: HomeAssistant, tmp_path) -> None:
    """sc-05: 'Casa Generale Casa Generale Power' is gone; translation keys are used."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)

        assert hass.states.get(POWER_ENTITY).attributes["friendly_name"] == "Casa Generale Power"
        assert hass.states.get(TOTAL_ENTITY).attributes["friendly_name"] == "Casa Generale Energy"
        # Single-entity devices keep the device name (Contract C).
        assert hass.states.get(TEMPERATURE_ENTITY).attributes["friendly_name"] == "Sonda Salotto"

        assert _entity_object(hass, "18-51", "power").translation_key == "power"
        assert _entity_object(hass, "18-51", "total-energy").translation_key == "energy_total"

        # sc-17: the meaningless "(5)1" attribute is gone; A/PL stays on the WHO=1 sensor.
        assert "Sensor" not in hass.states.get(POWER_ENTITY).attributes
        assert hass.states.get(ILLUMINANCE_ENTITY).attributes["A"] == "3"


# ------------------------------------------------------------------- keep-alive (E)
async def test_instant_power_keepalive(hass: HomeAssistant, tmp_path) -> None:
    """Contract E: armed at add, on every connection signal and on the interval."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry, connect=False)

        # Armed once for each meter when the entities were added.
        armed = [f for f in _drain(hass) if "#1200#1" in f]
        assert armed == [
            "*#18*51*#1200#1*125##",
            "*#18*52*#1200#1*125##",
            "*#18*53*#1200#1*125##",
        ]

        # Reconnect -> re-arm.
        _connect(hass)
        await hass.async_block_till_done()
        assert [f for f in _drain(hass) if "#1200#1" in f] == [
            "*#18*51*#1200#1*125##",
            "*#18*52*#1200#1*125##",
            "*#18*53*#1200#1*125##",
        ]

        # A disconnection must not send anything.
        _connect(hass, False)
        await hass.async_block_till_done()
        assert [f for f in _drain(hass) if "#1200#1" in f] == []

        # keepalive_minutes (125) - 5 -> re-armed every 120 minutes.
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=121))
        await hass.async_block_till_done()
        assert len([f for f in _drain(hass) if "#1200#1" in f]) == 3


async def test_keepalive_can_be_disabled(hass: HomeAssistant, tmp_path) -> None:
    """keepalive_minutes: 0 disables the automatic arming entirely."""
    entry = make_entry(write_yaml(tmp_path, NO_KEEPALIVE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        assert [f for f in _drain(hass) if "#1200#1" in f] == []

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=300))
        await hass.async_block_till_done()
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
async def test_energy_requests_and_updates(hass: HomeAssistant, tmp_path) -> None:
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
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
        await hass.async_block_till_done()
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
async def test_temperature_and_illuminance(hass: HomeAssistant, tmp_path) -> None:
    """sc-15: both are requested at add and re-requested on a timer, never polled."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        initial = _drain(hass)
        assert "*#4*2*0##" in initial
        assert "*#1*31*6##" in initial

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=6))
        await hass.async_block_till_done()
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


async def test_unload_removes_entities_from_the_registry_dict(hass: HomeAssistant, tmp_path) -> None:
    """sc-13: no platform-level async_unload_entry; the entities unregister themselves."""
    entry = make_entry(write_yaml(tmp_path, SENSOR_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        assert set(
            hass.data[DOMAIN][MAC][CONF_PLATFORMS]["sensor"]["18-51"][CONF_ENTITIES]
        ) >= {"power", "total-energy"}
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
    assert MAC not in hass.data[DOMAIN]

    import custom_components.myhome.sensor as sensor_module

    assert not hasattr(sensor_module, "async_unload_entry")
