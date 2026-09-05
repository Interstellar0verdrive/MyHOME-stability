"""Tests for the MyHOME climate platform (findings sc-06/07/08/10/13/16/19).

Like ``test_sensor.py`` the gateway is mocked, so the frames the entity produces stay
in ``handler.send_buffer``.
"""

from __future__ import annotations

import pytest
from OWNd.message import OWNHeatingEvent

from homeassistant.components.climate import (
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import (
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_PLATFORMS,
    DOMAIN,
)

from .helpers_core import MAC, make_entry, mock_gateway, write_yaml

CLIMATE_YAML = f"""
gateway:
  mac: {MAC}
  climate:
    zona_salotto:
      zone: '2'
      name: Zona Salotto
      heat: true
    zona_bagno:
      zone: '3'
      name: Zona Bagno
      heat: true
      cool: true
      fan: true
    centrale:
      zone: '#0'
      name: Centrale
      heat: true
      cool: true
      central: true
"""

ZONE = "climate.zona_salotto"
FAN_ZONE = "climate.zona_bagno"
CENTRAL = "climate.centrale"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
    if hasattr(handler, "_set_connected"):
        handler._set_connected(True)  # noqa: SLF001 - Contract B helper
    else:  # pragma: no cover - older gateway.py
        handler.is_connected = True
    await hass.async_block_till_done()


def _drain(hass: HomeAssistant) -> list[str]:
    handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
    frames: list[str] = []
    while not handler.send_buffer.empty():
        item = handler.send_buffer.get_nowait()
        message = item["message"] if isinstance(item, dict) else item.message
        frames.append(str(message))
    return frames


def _entity(hass: HomeAssistant, device_key: str):
    return hass.data[DOMAIN][MAC][CONF_PLATFORMS][CLIMATE_DOMAIN][device_key][CONF_ENTITIES][
        CLIMATE_DOMAIN
    ]


async def test_entities_features_and_modes(hass: HomeAssistant, tmp_path) -> None:
    """sc-06/07/08: TURN_ON/TURN_OFF, no FAN_MODE, AUTO also on the central unit."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)

        registry = er.async_get(hass)
        created = {e.unique_id for e in er.async_entries_for_config_entry(registry, entry.entry_id)}
        assert created == expected_unique_ids(MAC, hass.data[DOMAIN][MAC][CONF_PLATFORMS])
        assert f"{MAC}-4-2" in created
        assert f"{MAC}-4-#0" in created

        state = hass.states.get(ZONE)
        features = ClimateEntityFeature(state.attributes[ATTR_SUPPORTED_FEATURES])
        assert ClimateEntityFeature.TARGET_TEMPERATURE in features
        assert ClimateEntityFeature.TURN_ON in features
        assert ClimateEntityFeature.TURN_OFF in features
        assert ClimateEntityFeature.FAN_MODE not in features
        assert state.attributes["hvac_modes"] == [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT]

        # sc-08: the central unit used to be denied AUTO, so a weekly program left it
        # `unknown` forever.
        central = hass.states.get(CENTRAL)
        assert HVACMode.AUTO in central.attributes["hvac_modes"]
        assert central.attributes["hvac_modes"] == [
            HVACMode.OFF,
            HVACMode.AUTO,
            HVACMode.HEAT,
            HVACMode.COOL,
        ]

        # Every zone asks for its status when it is added.
        assert "*#4*2##" in _drain(hass)


async def test_fan_option_is_ignored_with_a_warning(hass: HomeAssistant, tmp_path, caplog) -> None:
    """sc-07: FAN_MODE is no longer advertised (async_set_fan_mode never existed)."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        features = ClimateEntityFeature(hass.states.get(FAN_ZONE).attributes[ATTR_SUPPORTED_FEATURES])
        assert ClimateEntityFeature.FAN_MODE not in features
        assert "fan_modes" not in hass.states.get(FAN_ZONE).attributes
    assert "fan speed is not supported" in caplog.text


async def test_central_unit_reports_auto(hass: HomeAssistant, tmp_path) -> None:
    """sc-08: `*4*311*#0##` (weekly program) is now reflected."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        _entity(hass, "4-#0").handle_event(OWNHeatingEvent("*4*311*#0##"))
        await hass.async_block_till_done()
        assert hass.states.get(CENTRAL).state == HVACMode.AUTO


async def test_turn_off_and_on(hass: HomeAssistant, tmp_path) -> None:
    """sc-06: climate.turn_off/turn_on are accepted and produce OWN frames."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        _drain(hass)

        await hass.services.async_call(
            CLIMATE_DOMAIN, "turn_off", {ATTR_ENTITY_ID: ZONE}, blocking=True
        )
        assert "*4*303*#2##" in _drain(hass)

        # turn_on picks HEAT (HA's preference order); with no set point known yet the
        # entity falls back to the default target instead of doing nothing (sc-10).
        await hass.services.async_call(
            CLIMATE_DOMAIN, "turn_on", {ATTR_ENTITY_ID: ZONE}, blocking=True
        )
        assert "*#4*#2*#14*0200*1##" in _drain(hass)


async def test_set_hvac_mode_without_known_target(hass: HomeAssistant, tmp_path, caplog) -> None:
    """sc-10: HEAT used to be silently dropped while the set point was unknown."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        _drain(hass)

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_hvac_mode",
            {ATTR_ENTITY_ID: ZONE, ATTR_HVAC_MODE: HVACMode.HEAT},
            blocking=True,
        )
        frames = _drain(hass)
        assert "*#4*2##" in frames  # status re-requested
        assert "*#4*#2*#14*0200*1##" in frames  # 20.0 C in heating mode
        assert "no known set point yet" in caplog.text

        # Once the zone reported its set point the real value is used.
        _entity(hass, "4-2").handle_event(OWNHeatingEvent("*#4*2*14*0220*3##"))
        await hass.async_block_till_done()
        _drain(hass)
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_hvac_mode",
            {ATTR_ENTITY_ID: ZONE, ATTR_HVAC_MODE: HVACMode.HEAT},
            blocking=True,
        )
        assert "*#4*#2*#14*0220*1##" in _drain(hass)


async def test_set_temperature(hass: HomeAssistant, tmp_path) -> None:
    """sc-16: a set_temperature without a target must not raise TypeError."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        _drain(hass)

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_ENTITY_ID: ZONE, ATTR_TEMPERATURE: 22.5},
            blocking=True,
        )
        assert "*#4*#2*#14*0225*3##" in _drain(hass)

        # Direct call without a temperature and without a known set point: a readable
        # error instead of `None - offset`.
        with pytest.raises(ServiceValidationError):
            await _entity(hass, "4-2").async_set_temperature()

        # With a known set point the same call re-sends it.
        _entity(hass, "4-2").handle_event(OWNHeatingEvent("*#4*2*14*0220*3##"))
        await hass.async_block_till_done()
        _drain(hass)
        await _entity(hass, "4-2").async_set_temperature()
        assert "*#4*#2*#14*0220*3##" in _drain(hass)


async def test_hvac_action_is_derived_from_mode(hass: HomeAssistant, tmp_path) -> None:
    """sc-19: hvac_action no longer stays unknown until a valve frame arrives."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-2")

        entity.handle_event(OWNHeatingEvent("*4*103*2##"))  # mode off
        await hass.async_block_till_done()
        assert hass.states.get(ZONE).state == HVACMode.OFF
        assert hass.states.get(ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.OFF

        entity.handle_event(OWNHeatingEvent("*#4*2*14*0220*3##"))  # target 22.0
        entity.handle_event(OWNHeatingEvent("*#4*2*0*0200*3##"))  # current 20.0
        entity.handle_event(OWNHeatingEvent("*4*110*2##"))  # mode heat
        await hass.async_block_till_done()
        state = hass.states.get(ZONE)
        assert state.state == HVACMode.HEAT
        assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        entity.handle_event(OWNHeatingEvent("*#4*2*0*0250*3##"))  # current 25.0
        await hass.async_block_till_done()
        assert hass.states.get(ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE

        # A real actuator frame wins over the derived value.
        entity.handle_event(OWNHeatingEvent("*#4*2*19*1*1##"))
        await hass.async_block_till_done()
        assert hass.states.get(ZONE).attributes[ATTR_HVAC_ACTION] in (
            HVACAction.HEATING,
            HVACAction.IDLE,
        )


# --------------------------------------------------- central heating unit (0.3.1 / 5.4)
CENTRAL_ZONE_YAML = f"""
gateway:
  mac: {MAC}
  climate:
    zona_uno:
      zone: '1'
      name: Zona Uno
      heat: true
    centrale:
      zone: '#0'
      name: Centrale
      heat: true
      central: true
"""


def _record(entity, sink: list[str]) -> None:
    """Wrap ``handle_event`` so the test sees exactly what the dispatcher delivered."""
    original = entity.handle_event

    def spy(message) -> None:
        sink.append(str(message))
        original(message)

    entity.handle_event = spy


async def test_central_unit_frame_is_not_applied_to_zone_1(hass: HomeAssistant, tmp_path) -> None:
    """0.3.1 (forks review 5.4, Jacopo Jannone via michnovka): OWNd rewrites a heating
    ``zone 0`` to the zone in the first WHERE parameter, so ``*#4*0#1*20*1##`` - the
    central unit's actuator 1 - reported entity ``4-1`` and drove zone 1's climate
    entity with the central unit's state.  OWNd is pinned: the guard is in our
    dispatcher and never touches its private ``_zone``."""
    entry = make_entry(write_yaml(tmp_path, CENTRAL_ZONE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]

        # OWNd itself still mis-reports the entity: we are guarding, not patching.
        assert OWNHeatingEvent("*#4*0#1*20*1##").entity == "4-1"

        zone_seen: list[str] = []
        central_seen: list[str] = []
        _record(_entity(hass, "4-1"), zone_seen)
        _record(_entity(hass, "4-#0"), central_seen)

        await handler._dispatch_message(OWNHeatingEvent("*#4*0#1*20*1##"), from_monitor=True)  # noqa: SLF001
        await hass.async_block_till_done()
        assert central_seen == ["*#4*0#1*20*1##"]
        assert zone_seen == []

        # A genuine zone-1 frame is untouched.
        await handler._dispatch_message(OWNHeatingEvent("*#4*1*0*0215##"), from_monitor=True)  # noqa: SLF001
        await hass.async_block_till_done()
        assert zone_seen == ["*#4*1*0*0215##"]
        assert len(central_seen) == 1
        assert hass.states.get("climate.zona_uno").attributes["current_temperature"] == 21.5


async def test_no_platform_unload_entry(hass: HomeAssistant, tmp_path) -> None:
    """sc-13: the dead platform-level async_unload_entry is gone."""
    import custom_components.myhome.climate as climate_module

    assert not hasattr(climate_module, "async_unload_entry")

    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        assert isinstance(
            hass.data[DOMAIN][MAC][CONF_PLATFORMS][CLIMATE_DOMAIN]["4-2"][CONF_ENTITIES][
                CLIMATE_DOMAIN
            ].unique_id,
            str,
        )
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
    assert MAC not in hass.data[DOMAIN]
