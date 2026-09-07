"""Tests for the MyHOME climate platform (findings sc-06/07/08/10/13/16/19).

Like ``test_sensor.py`` the gateway is mocked, so the frames the entity produces stay
in ``handler.send_buffer``.
"""

from __future__ import annotations

import pytest
from homeassistant.components.climate import (
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, ATTR_SUPPORTED_FEATURES, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from OWNd.message import OWNHeatingEvent
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
    zone_living:
      zone: '2'
      name: Zone Living
      heat: true
    zone_bathroom:
      zone: '3'
      name: Zone Bathroom
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

# A cooling-only zone and a zone addressed directly (`standalone: true`), neither of
# which any fixture used to cover (F10).
COOLING_YAML = f"""
gateway:
  mac: {MAC}
  climate:
    study_cooling:
      zone: '5'
      name: Study Cooling
      heat: false
      cool: true
    guest_room:
      zone: '6'
      name: Guest Room
      heat: true
      standalone: true
      icon: 'mdi:radiator'
"""

ZONE = "climate.zone_living"
FAN_ZONE = "climate.zone_bathroom"
CENTRAL = "climate.centrale"
COOLING_ZONE = "climate.study_cooling"
STANDALONE_ZONE = "climate.guest_room"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
    # No `hasattr` fallback: every climate test depends on the entities actually
    # being told the gateway is up, and a silent `handler.is_connected = True`
    # would set the attribute without publishing the availability signal - so a
    # rename of `_set_connected` used to WEAKEN every test in this file instead of
    # failing one of them. Fail loudly here instead.
    handler._set_connected(True)  # noqa: SLF001 - Contract B helper
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

        # (The no-temperature / no-set-point refusal is pinned, with its
        # translation_key, by test_service_errors_carry_their_own_translation_key.)

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

        # A real actuator frame wins over the derived value: the zone only supports
        # heating, so an active valve means HEATING whatever the temperatures say.
        # F10: this used to be asserted as `in (HEATING, IDLE)`, which any of the four
        # branches of the derivation satisfies.
        entity.handle_event(OWNHeatingEvent("*#4*2*19*0*1##"))
        await hass.async_block_till_done()
        assert hass.states.get(ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        # An idle valve on a zone that is not off is IDLE, not OFF.
        entity.handle_event(OWNHeatingEvent("*#4*2*19*0*0##"))
        await hass.async_block_till_done()
        assert hass.states.get(ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE


async def test_hvac_action_cooling_and_unknown_temperatures(hass: HomeAssistant, tmp_path) -> None:
    """F10: the COOL branches of the action derivation were never executed."""
    entry = make_entry(write_yaml(tmp_path, COOLING_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-5")

        # Mode known but no temperature yet -> IDLE rather than a wrong guess.
        entity.handle_event(OWNHeatingEvent("*4*210*5##"))  # mode cool
        await hass.async_block_till_done()
        assert hass.states.get(COOLING_ZONE).state == HVACMode.COOL
        assert hass.states.get(COOLING_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE

        entity.handle_event(OWNHeatingEvent("*#4*5*14*0200*3##"))  # target 20.0
        entity.handle_event(OWNHeatingEvent("*#4*5*0*0250##"))  # current 25.0
        await hass.async_block_till_done()
        assert hass.states.get(COOLING_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.COOLING

        entity.handle_event(OWNHeatingEvent("*#4*5*0*0180##"))  # current 18.0
        await hass.async_block_till_done()
        assert hass.states.get(COOLING_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE

        # An active valve on a cooling-only zone means COOLING.
        entity.handle_event(OWNHeatingEvent("*#4*5*19*1*0##"))
        await hass.async_block_till_done()
        assert hass.states.get(COOLING_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.COOLING


async def test_hvac_action_auto_with_both_supported_is_idle(hass: HomeAssistant, tmp_path) -> None:
    """F10: a zone that can do both cannot tell heating from cooling in AUTO."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3*14*0200*3##"))  # target 20.0
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0250##"))  # current 25.0
        entity.handle_event(OWNHeatingEvent("*4*311*3##"))  # mode auto
        await hass.async_block_till_done()
        state = hass.states.get(FAN_ZONE)
        assert state.state == HVACMode.AUTO
        assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE


async def test_actuator_status_does_not_freeze_a_heat_and_cool_zone(
    hass: HomeAssistant, tmp_path
) -> None:
    """P2-RISK-1: dimension 20 carries no direction, so it must not disable sc-19.

    OWNd builds MESSAGE_TYPE_ACTION from the valve status (dimension 19, which says
    heating/cooling) *and* from the actuator status (dimension 20, which only says
    active). On a `heat: true, cool: true` zone the actuator frame matched no branch
    and assigned nothing, yet set `_action_reported`: the temperature derivation was
    switched off for good and hvac_action froze at whatever it happened to hold.
    """
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3*14*0220*3##"))  # target 22.0
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0200##"))  # current 20.0
        entity.handle_event(OWNHeatingEvent("*4*110*3##"))  # mode heat
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        # Actuator 1 of the zone reports "on" - and nothing about the direction.
        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*1##"))
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0250##"))  # current 25.0 > target
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE

        # A valve frame, which does carry the direction, is still authoritative.
        entity.handle_event(OWNHeatingEvent("*#4*3*19*0*1##"))
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        # P3-NIT-2: the other direction of the same frame, which no test reached.
        entity.handle_event(OWNHeatingEvent("*#4*3*19*1*0##"))  # valve: cooling
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.COOLING


async def test_actuator_status_first_does_not_leave_hvac_action_unknown(
    hass: HomeAssistant, tmp_path
) -> None:
    """P2-RISK-1: the actuator-frame-first order used to freeze hvac_action at None.

    sc-19 exists precisely so that hvac_action is never `unknown`; a central unit that
    reports actuator status instead of valve status defeated it permanently.
    """
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*1##"))  # actuator on, first
        entity.handle_event(OWNHeatingEvent("*#4*3*14*0220*3##"))  # target 22.0
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0200##"))  # current 20.0
        entity.handle_event(OWNHeatingEvent("*4*110*3##"))  # mode heat
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING


async def test_actuator_off_is_authoritative_on_any_zone(hass: HomeAssistant, tmp_path) -> None:
    """An inactive actuator says "idle" without needing a direction, so it still wins."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3*14*0220*3##"))  # target 22.0
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0200##"))  # current 20.0, below
        entity.handle_event(OWNHeatingEvent("*4*110*3##"))  # mode heat
        entity.handle_event(OWNHeatingEvent("*#4*3#2*20*0##"))  # actuator 2 off
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE


async def test_an_actuator_that_switches_back_on_does_not_freeze_the_zone(
    hass: HomeAssistant, tmp_path
) -> None:
    """P3-BUG-1: off then on is the ordinary duty cycle of a single actuator.

    The "off" frame answers (idle) and used to latch `_action_reported` for ever, so
    the "on" frame that followed - which carries no direction on dimension 20, and
    therefore assigns nothing on a `heat: true, cool: true` zone - left hvac_action
    frozen at `idle` whatever the temperatures did afterwards.
    """
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3*14*0220*3##"))  # target 22.0
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0200##"))  # current 20.0
        entity.handle_event(OWNHeatingEvent("*4*110*3##"))  # mode heat
        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*0##"))  # actuator off -> idle
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE

        # Set point reached, room cools down again: the actuator restarts and says only
        # "active". The temperature derivation has to be back in charge from here.
        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*1##"))  # actuator on, no direction
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        entity.handle_event(OWNHeatingEvent("*#4*3*0*0150##"))  # current 15.0
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING


async def test_a_full_actuator_duty_cycle_is_followed_on_a_heat_and_cool_zone(
    hass: HomeAssistant, tmp_path
) -> None:
    """P3-BUG-1: off -> on -> off, the sequence a thermostat repeats all day."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3*14*0220*3##"))  # target 22.0
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0200##"))  # current 20.0, below
        entity.handle_event(OWNHeatingEvent("*4*110*3##"))  # mode heat
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*0##"))  # off: set point reached
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE

        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*1##"))  # on again, no direction
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*0##"))  # off again: still heard
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE


async def test_a_valve_direction_survives_a_direction_less_actuator_frame(
    hass: HomeAssistant, tmp_path
) -> None:
    """P4-RISK-1: a bare "actuator on" must not overrule a valve that named a direction.

    OWNd builds MESSAGE_TYPE_ACTION from two different dimensions. Dimension 19 (the
    valve status, `*#4*<zone>*19*<cool>*<heat>##`) carries the direction and is the
    authoritative one; dimension 20 (the actuator status) only says active or not.
    A plant whose central unit mirrors both sends them in that order, and the
    P3-BUG-1 fix - which drops `_action_reported` on any direction-less "active" -
    used to throw the valve's answer away, so `hvac_action` fell back to the
    temperature derivation and published `idle` while the valve was open. That
    happens precisely when the room is at or above the set point and the valve is
    modulating, and every automation keyed on `hvac_action` (a boiler relay, an "is
    anything calling for heat" template) then reads `idle`.

    Mutation caught: dropping the `if self._attr_hvac_action in (IDLE, OFF, None)`
    guard, after which the second frame below reports `idle`.
    """
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3*14*0220*3##"))  # target 22.0
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0250##"))  # current 25.0, above
        entity.handle_event(OWNHeatingEvent("*4*110*3##"))  # mode heat
        await hass.async_block_till_done()
        # Nothing has reported yet, so the derivation answers: warm enough -> idle.
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE

        entity.handle_event(OWNHeatingEvent("*#4*3*19*0*1##"))  # valve: heating
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        # The actuator confirms it is running but says nothing about the direction.
        # It agrees with the valve; it must not silently replace it.
        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*1##"))
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

        # A frame that really does contradict the valve is still heard.
        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*0##"))  # actuator off
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE

        # ...and from that `idle` the P3-BUG-1 duty cycle works exactly as before:
        # the next direction-less "on" hands the derivation back its job.
        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*1##"))
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0150##"))  # current 15.0, below
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING


async def test_all_message_types_reach_the_entity(hass: HomeAssistant, tmp_path) -> None:
    """F10: humidity, local offset, local set point and MODE_TARGET were never fed.

    ``handle_event`` has no try/except, and the local-offset branch adds the offset to
    the set point, so a frame arriving before any set point is known must not raise.
    """
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-2")

        # Offset first, with no set point known yet.
        entity.handle_event(OWNHeatingEvent("*#4*2*13*0001##"))  # local offset +1
        entity.handle_event(OWNHeatingEvent("*#4*2*60*45##"))  # humidity 45 %
        await hass.async_block_till_done()
        assert hass.states.get(ZONE).attributes["current_humidity"] == 45

        # The displayed set point includes the local offset.
        entity.handle_event(OWNHeatingEvent("*#4*2*14*0220*3##"))  # target 22.0
        await hass.async_block_till_done()
        assert hass.states.get(ZONE).attributes["temperature"] == 23.0

        # A local set point read off the knob works the other way round.
        entity.handle_event(OWNHeatingEvent("*#4*2*12*0215*3##"))
        await hass.async_block_till_done()
        assert hass.states.get(ZONE).attributes["temperature"] == 21.5

        # MODE_TARGET carries both the mode and the set point.
        entity.handle_event(OWNHeatingEvent("*4*110#0225*2##"))
        await hass.async_block_till_done()
        state = hass.states.get(ZONE)
        assert state.state == HVACMode.HEAT
        assert state.attributes["temperature"] == 23.5  # 22.5 + the +1 offset


@pytest.mark.parametrize(
    ("mode_frame", "expected"),
    [
        ("*4*110*2##", "*#4*#2*#14*0225*1##"),  # HEAT -> heating set point
        ("*4*103*2##", "*#4*#2*#14*0225*3##"),  # OFF  -> the neutral AUTO form
    ],
)
async def test_set_temperature_follows_the_current_mode(
    hass: HomeAssistant, tmp_path, mode_frame: str, expected: str
) -> None:
    """F10: every set_temperature test ran with `hvac_mode` still None."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        _entity(hass, "4-2").handle_event(OWNHeatingEvent(mode_frame))
        await hass.async_block_till_done()
        _drain(hass)

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_ENTITY_ID: ZONE, ATTR_TEMPERATURE: 22.5},
            blocking=True,
        )
        assert expected in _drain(hass)


async def test_cooling_zone_set_temperature(hass: HomeAssistant, tmp_path) -> None:
    """The COOL branch of async_set_temperature, on a zone that only cools."""
    entry = make_entry(write_yaml(tmp_path, COOLING_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        _entity(hass, "4-5").handle_event(OWNHeatingEvent("*4*210*5##"))  # mode cool
        await hass.async_block_till_done()
        _drain(hass)

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_ENTITY_ID: COOLING_ZONE, ATTR_TEMPERATURE: 19.0},
            blocking=True,
        )
        assert "*#4*#5*#14*0190*2##" in _drain(hass)
        assert hass.states.get(COOLING_ZONE).attributes["hvac_modes"] == [
            HVACMode.OFF,
            HVACMode.AUTO,
            HVACMode.COOL,
        ]


async def test_standalone_zone_and_icon(hass: HomeAssistant, tmp_path) -> None:
    """F10: `standalone: true` appeared in no fixture, so all four call sites ran False.

    A standalone zone is addressed directly (`*4*303*6##`), not through the central
    unit (`*4*303*#6##`).  The `icon` key is checked here too (INCONSISTENCY-1).
    """
    entry = make_entry(write_yaml(tmp_path, COOLING_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        assert hass.states.get(STANDALONE_ZONE).attributes["icon"] == "mdi:radiator"
        _drain(hass)

        await hass.services.async_call(
            CLIMATE_DOMAIN, "turn_off", {ATTR_ENTITY_ID: STANDALONE_ZONE}, blocking=True
        )
        assert "*4*303*6##" in _drain(hass)

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_hvac_mode",
            {ATTR_ENTITY_ID: STANDALONE_ZONE, ATTR_HVAC_MODE: HVACMode.AUTO},
            blocking=True,
        )
        assert "*4*311*6##" in _drain(hass)

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_temperature",
            {ATTR_ENTITY_ID: STANDALONE_ZONE, ATTR_TEMPERATURE: 21.5},
            blocking=True,
        )
        assert "*#4*6*#14*0215*3##" in _drain(hass)


async def test_service_errors_carry_their_own_translation_key(hass: HomeAssistant, tmp_path) -> None:
    """F10: a bare `pytest.raises(ServiceValidationError)` let the two keys be swapped."""
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-2")

        with pytest.raises(ServiceValidationError) as err:
            await entity.async_set_temperature()
        assert err.value.translation_key == "climate_no_target_temperature"

        with pytest.raises(ServiceValidationError) as err:
            await entity.async_set_hvac_mode(HVACMode.DRY)
        assert err.value.translation_key == "climate_unsupported_hvac_mode"


# --------------------------------------------------- central heating unit (0.3.1 / 5.4)
CENTRAL_ZONE_YAML = f"""
gateway:
  mac: {MAC}
  climate:
    zone_one:
      zone: '1'
      name: Zone One
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
        assert hass.states.get("climate.zone_one").attributes["current_temperature"] == 21.5


# ------------------------------------------------------- a zero-padded zone (P4-BUG-1)
PADDED_ZONE_YAML = f"""
gateway:
  mac: {MAC}
  climate:
    padded_zone:
      where: '01'
      name: Padded Zone
      heat: true
"""


async def test_a_zone_written_with_a_padded_where_still_receives_its_frames(
    hass: HomeAssistant, tmp_path
) -> None:
    """P4-BUG-1: ``where: '01'`` used to key the device ``4-01`` and never hear a frame.

    The validator's own advice is "always quote every 'where:' value", and every
    actuator address in the documentation is written padded, so ``'01'`` is what a
    careful user writes for zone 1. The entity was created, was named, was available
    and stayed ``unknown`` for ever - the only trace being the dispatcher's DEBUG
    line "No entity configured for 4-1".

    Routed through ``_dispatch_message`` on purpose: this is a test about the *key*
    the frame is looked up by, which calling ``handle_event`` directly would skip.
    """
    entry = make_entry(write_yaml(tmp_path, PADDED_ZONE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        handler = hass.data[DOMAIN][MAC][CONF_ENTITY]
        # The key OWNd builds for every WHO 4 frame of zone 1, from ``int(zone)``.
        assert OWNHeatingEvent("*4*110*1##").entity == "4-1"
        assert list(hass.data[DOMAIN][MAC][CONF_PLATFORMS][CLIMATE_DOMAIN]) == ["4-1"]

        await handler._dispatch_message(OWNHeatingEvent("*4*110*1##"), from_monitor=True)  # noqa: SLF001
        await handler._dispatch_message(OWNHeatingEvent("*#4*1*0*0215##"), from_monitor=True)  # noqa: SLF001
        await hass.async_block_till_done()
        state = hass.states.get("climate.padded_zone")
        assert state.state == HVACMode.HEAT
        assert state.attributes["current_temperature"] == 21.5


# ------------------------------------------------- climate + temperature probe (BUG-3)
ZONE_AND_PROBE_YAML = f"""
gateway:
  mac: {MAC}
  climate:
    living_zone:
      zone: '1'
      name: Living Zone
      heat: true
  sensor:
    living_probe:
      where: '1'
      name: Living Probe
      class: temperature
"""


async def test_zone_and_probe_share_a_device_without_renaming_the_zone(
    hass: HomeAssistant, tmp_path
) -> None:
    """BUG-3: docs/configuration.md sanctions this pairing, and it renamed the zone.

    Both devices key as ``4-1``, which is also the device registry identifier, so the
    two entities land on one device.  The sensor platform is set up after the climate
    one, so its ``name`` used to overwrite the device name - and the climate entity's
    friendly name *is* the device name.
    """
    entry = make_entry(write_yaml(tmp_path, ZONE_AND_PROBE_YAML))
    with mock_gateway():
        await _setup(hass, entry)

        assert hass.states.get("climate.living_zone").attributes["friendly_name"] == "Living Zone"
        probe = hass.states.get("sensor.living_zone_living_probe")
        assert probe is not None
        assert probe.attributes["friendly_name"] == "Living Zone Living Probe"

        # One device for both entities, named after the climate zone.
        registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device_by_identifier((DOMAIN, f"{MAC}-4-1"), entry.entry_id)
        assert device.name == "Living Zone"
        assert {
            item.unique_id
            for item in er.async_entries_for_device(registry, device.id)
        } == {f"{MAC}-4-1", f"{MAC}-4-1-temperature"}


async def test_no_platform_unload_entry(hass: HomeAssistant, tmp_path) -> None:
    """sc-13: the dead platform-level async_unload_entry is gone."""
    import custom_components.myhome.climate as climate_module

    assert not hasattr(climate_module, "async_unload_entry")

    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        # `isinstance(..., str)` was filler. The zone entity registers itself under
        # the documented unique id and takes itself back out on unload, exactly as
        # the sensor platform does (test_unload_drains_the_entities_registry_dict).
        entities = hass.data[DOMAIN][MAC][CONF_PLATFORMS][CLIMATE_DOMAIN]["4-2"][CONF_ENTITIES]
        assert entities[CLIMATE_DOMAIN].unique_id == f"{MAC}-4-2"
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entities == {}
    assert MAC not in hass.data[DOMAIN]


async def test_a_zone_switched_back_on_does_not_stay_reported_as_off(
    hass: HomeAssistant, tmp_path
) -> None:
    """A zone that was off and is switched on must not keep publishing `hvac_action: off`.

    An actuator frame received while the zone is off reports `off` and sets
    `_action_reported`, which is right at that moment. When the wall unit then puts
    the zone back on, no new actuator frame is due - the actuator has not changed
    state - so the mode frame is the only thing that arrives, and `_action_reported`
    sends the derivation home before it can look at the temperatures. The one line
    that keeps the two attributes from contradicting each other is the `off -> idle`
    correction in `_async_derive_hvac_action`.

    Mutation caught: deleting `if self._attr_hvac_action == HVACAction.OFF:
    self._attr_hvac_action = HVACAction.IDLE` from the `_action_reported` arm, after
    which the zone reads `hvac_mode: heat` and `hvac_action: off` at the same time -
    the thermostat card says the heating is off while the zone is asking for heat,
    and every automation keyed on `hvac_action` (a boiler relay, an "is anything
    calling for heat" template) reads `off` until the actuator next changes state.
    Replacing the correction's `IDLE` with `HEATING` is caught too: the actuator
    frame is still the authority, it just cannot mean "off" for a zone that is on.
    """
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3*14*0220*3##"))  # target 22.0
        entity.handle_event(OWNHeatingEvent("*#4*3*0*0200##"))  # current 20.0, below target
        entity.handle_event(OWNHeatingEvent("*4*303*3##"))  # mode off
        entity.handle_event(OWNHeatingEvent("*#4*3#2*20*0##"))  # the actuator confirms: off
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).state == HVACMode.OFF
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.OFF

        entity.handle_event(OWNHeatingEvent("*4*110*3##"))  # back on, heat
        await hass.async_block_till_done()
        state = hass.states.get(FAN_ZONE)
        assert state.state == HVACMode.HEAT
        # `idle`, not a re-derived `heating`: the actuator frame is still the
        # authority, it just cannot mean "off" for a zone that is on.
        assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE


async def test_an_actuator_off_before_the_mode_is_known_reports_idle_not_off(
    hass: HomeAssistant, tmp_path
) -> None:
    """An inactive actuator seen before any MODE frame means "idle", never "off".

    `hvac_action: off` is the entity saying *the user turned this zone off*, and the
    zone has not said anything of the kind yet: only a MODE frame can. A central unit
    that pushes actuator status at connection time (before the zone's mode) would
    otherwise leave the zone reading `off` until the first MODE frame arrives, which
    on a zone that is in fact heating is the opposite of what it does.

    `_async_derive_hvac_action` cannot repair this one: it returns immediately while
    `_attr_hvac_mode` is still None, so the ternary in the MESSAGE_TYPE_ACTION arm is
    the only thing that gets it right.

    Mutation caught: replacing that ternary with a bare `HVACAction.OFF`.
    """
    entry = make_entry(write_yaml(tmp_path, CLIMATE_YAML))
    with mock_gateway():
        await _setup(hass, entry)
        entity = _entity(hass, "4-3")  # heat + cool

        entity.handle_event(OWNHeatingEvent("*#4*3#1*20*0##"))  # actuator off, first
        await hass.async_block_till_done()
        assert hass.states.get(FAN_ZONE).attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE
