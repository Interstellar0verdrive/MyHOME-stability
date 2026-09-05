"""Tests for the MyHOME binary sensor platform."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache,
    mock_restore_cache_with_extra_data,
)

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR, BinarySensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import (
    CONF_PLATFORMS,
    DOMAIN,
    GATEWAY_DIAG_CONNECTED,
)

from .helpers_core import MAC
from .helpers_platforms import (
    GATEWAY_DIAG_UNIQUE_IDS,
    diagnostic_entity_id,
    dispatch_stats,
    entity_object,
    feed_event,
    set_connected,
    setup_myhome,
)

# A configuration without a single binary sensor: the gateway diagnostic entity of
# this platform must be created anyway (0.3.0, plan G1-B).
NO_BINARY_SENSOR_YAML = f"""
gateway:
  mac: {MAC}
  light:
    luce_test:
      where: '11'
      name: Luce Test
"""

SENSORS_YAML = f"""
gateway:
  mac: {MAC}
  binary_sensor:
    contatto_finestra:
      who: '25'
      where: '31'
      name: Contatto Finestra
      device_class: window
    contatto_porta:
      who: '25'
      where: '32'
      name: Contatto Porta
    aux_allarme:
      who: '9'
      where: '1'
      name: Aux Allarme
"""

MOTION_YAML = f"""
gateway:
  mac: {MAC}
  binary_sensor:
    sensore_movimento:
      who: '1'
      where: '11'
      name: Sensore Movimento
      class: motion
    sensore_invertito:
      who: '1'
      where: '12'
      name: Sensore Invertito
      class: motion
      inverted: true
"""


async def _advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_sensors_created_with_and_without_class(hass: HomeAssistant, tmp_path) -> None:
    """plat-01: `device_class` alias, WHO defaults and a `None` class must all work."""
    async with setup_myhome(hass, tmp_path, SENSORS_YAML) as (entry, _commands):
        entity_registry = er.async_get(hass)
        entries = [
            item
            for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            if item.domain == BINARY_SENSOR
        ]
        # Three configured sensors + the gateway "connected" diagnostic entity.
        assert len(entries) == 4

        platforms = hass.data[DOMAIN][MAC][CONF_PLATFORMS]
        # expected_unique_ids() lists the five gateway diagnostic ids as well; only the
        # connectivity one is a binary sensor.
        expected = expected_unique_ids(MAC, {BINARY_SENSOR: platforms[BINARY_SENSOR]})
        expected = (expected - GATEWAY_DIAG_UNIQUE_IDS) | {f"{MAC}-{GATEWAY_DIAG_CONNECTED}"}
        assert {item.unique_id for item in entries} == expected
        # plat-12 (known limitation): the class is part of the unique id, and the WHO 9
        # channel without class keeps the historical "-None" suffix.
        assert f"{MAC}-25-31-window" in expected
        assert f"{MAC}-25-32-opening" in expected
        assert f"{MAC}-9-1-None" in expected

        window = hass.states.get("binary_sensor.contatto_finestra_window")
        assert window.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.WINDOW
        assert window.attributes["friendly_name"] == "Contatto Finestra Window"

        aux = hass.states.get("binary_sensor.aux_allarme_sensor")
        assert aux is not None
        assert ATTR_DEVICE_CLASS not in aux.attributes
        assert aux.attributes["friendly_name"] == "Aux Allarme Sensor"


async def test_dry_contact_events(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, SENSORS_YAML, clear_commands=False) as (_entry, commands):
        assert "*#25*31##" in commands.status_frames

        sensor = entity_object(hass, BINARY_SENSOR, "25-31")
        await feed_event(hass, sensor, "*25*31#31*31##")
        assert hass.states.get("binary_sensor.contatto_finestra_window").state == STATE_ON
        await feed_event(hass, sensor, "*25*32#31*31##")
        assert hass.states.get("binary_sensor.contatto_finestra_window").state == STATE_OFF


async def test_motion_timeout_respects_inverted(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """plat-11: the timeout clears the sensor symmetrically for inverted sensors."""
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        normal = entity_object(hass, BINARY_SENSOR, "1-11")
        inverted = entity_object(hass, BINARY_SENSOR, "1-12")

        await feed_event(hass, normal, "*1*34*11##")
        await feed_event(hass, inverted, "*1*34*12##")
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_ON
        assert hass.states.get("binary_sensor.sensore_invertito_motion").state == STATE_OFF

        await _advance(hass, freezer, 316)
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_OFF
        assert hass.states.get("binary_sensor.sensore_invertito_motion").state == STATE_ON


async def test_motion_timeout_frame_updates_the_timer(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """The sensor's own timeout (+15 s margin) drives the expiry."""
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        normal = entity_object(hass, BINARY_SENSOR, "1-11")
        await feed_event(hass, normal, "*#1*11*7*0*1*0##")
        assert hass.states.get("binary_sensor.sensore_movimento_motion").attributes["Timeout"] == 75.0

        await feed_event(hass, normal, "*1*34*11##")
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_ON
        await _advance(hass, freezer, 60)
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_ON
        await _advance(hass, freezer, 20)
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_OFF


async def test_motion_sensitivity_and_unknown_frames(hass: HomeAssistant, tmp_path) -> None:
    """plat-03: unrelated dimension replies are ignored, never raised."""
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        normal = entity_object(hass, BINARY_SENSOR, "1-11")
        await feed_event(hass, normal, "*#1*11*5*3##")
        assert hass.states.get("binary_sensor.sensore_movimento_motion").attributes["Sensitivity"] == "very high"
        await feed_event(hass, normal, "*#1*11*2*0*1*0##")
        assert hass.states.get("binary_sensor.sensore_movimento_motion") is not None


async def test_motion_state_restored(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """A restart keeps the motion state and re-arms the remaining timeout."""
    mock_restore_cache(hass, (State("binary_sensor.sensore_movimento_motion", STATE_ON),))
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_ON
        await _advance(hass, freezer, 316)
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_OFF


async def test_availability_follows_connection_signal(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, SENSORS_YAML):
        await set_connected(hass, False)
        assert hass.states.get("binary_sensor.contatto_finestra_window").state == STATE_UNAVAILABLE
        await set_connected(hass, True)
        assert hass.states.get("binary_sensor.contatto_finestra_window").state != STATE_UNAVAILABLE


# ------------------------------------------------------------------ motion restore
async def test_motion_survives_entry_reload(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Reloading the entry keeps the motion state and the remaining timeout.

    On unload the gateway connection is closed before the entities are removed, so HA
    snapshots them as ``unavailable``: the state has to travel through
    ``extra_restore_state_data`` (same pattern as the cover position).
    """
    async with setup_myhome(hass, tmp_path, MOTION_YAML) as (entry, _commands):
        await feed_event(hass, entity_object(hass, BINARY_SENSOR, "1-11"), "*1*34*11##")
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_ON

        await _advance(hass, freezer, 100)  # 215 s left of the 315 s timeout
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_ON
        # The timeout is not restarted from scratch: what was left of it still applies.
        await _advance(hass, freezer, 200)
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_ON
        await _advance(hass, freezer, 20)
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_OFF


async def test_motion_extra_data_restores_expired_state(hass: HomeAssistant, tmp_path) -> None:
    """An expiry in the past clears the sensor instead of re-arming a timer."""
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State("binary_sensor.sensore_movimento_motion", STATE_UNAVAILABLE),
                {
                    "is_on": True,
                    "expires_at": (dt_util.utcnow() - timedelta(seconds=5)).isoformat(),
                },
            ),
        ),
    )
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        assert hass.states.get("binary_sensor.sensore_movimento_motion").state == STATE_OFF


# -------------------------------------------------------------- gateway diagnostics
async def test_gateway_connected_entity(hass: HomeAssistant, tmp_path) -> None:
    """G1-B: the connectivity entity lives on the gateway device and follows the stats."""
    async with setup_myhome(hass, tmp_path, SENSORS_YAML) as (entry, _commands):
        registry = er.async_get(hass)
        entry_id = diagnostic_entity_id(hass, BINARY_SENSOR, GATEWAY_DIAG_CONNECTED)
        assert entry_id is not None
        registry_entry = registry.async_get(entry_id)

        assert registry_entry.unique_id == f"{MAC}-{GATEWAY_DIAG_CONNECTED}"
        assert registry_entry.entity_category is EntityCategory.DIAGNOSTIC
        assert registry_entry.disabled_by is None  # enabled by default
        assert registry_entry.original_device_class is BinarySensorDeviceClass.CONNECTIVITY

        # It hangs on the gateway device itself, not on a bus device.
        gateway_device = dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, MAC), entry.entry_id
        )
        assert registry_entry.device_id == gateway_device.id

        await dispatch_stats(hass, connected=True, session_state="connected")
        assert hass.states.get(entry_id).state == STATE_ON

        await dispatch_stats(hass, connected=False, session_state="disconnected")
        assert hass.states.get(entry_id).state == STATE_OFF


async def test_gateway_connected_entity_stays_available(hass: HomeAssistant, tmp_path) -> None:
    """The diagnostic entity must survive the very outage it reports."""
    async with setup_myhome(hass, tmp_path, SENSORS_YAML):
        entity_id = diagnostic_entity_id(hass, BINARY_SENSOR, GATEWAY_DIAG_CONNECTED)
        await dispatch_stats(hass, connected=True, session_state="connected")
        await set_connected(hass, False)

        assert hass.states.get("binary_sensor.contatto_finestra_window").state == STATE_UNAVAILABLE
        assert hass.states.get(entity_id).state == STATE_ON

        await dispatch_stats(hass, connected=False, session_state="disconnected")
        assert hass.states.get(entity_id).state == STATE_OFF


async def test_gateway_connected_entity_without_binary_sensors(hass: HomeAssistant, tmp_path) -> None:
    """It is created even when the configuration declares no binary sensor at all."""
    async with setup_myhome(hass, tmp_path, NO_BINARY_SENSOR_YAML):
        entity_id = diagnostic_entity_id(hass, BINARY_SENSOR, GATEWAY_DIAG_CONNECTED)
        assert entity_id is not None
        await dispatch_stats(hass, connected=True, session_state="connected")
        assert hass.states.get(entity_id).state == STATE_ON
