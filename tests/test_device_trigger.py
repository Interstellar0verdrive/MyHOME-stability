"""Tests for the CEN / CEN+ device triggers (0.4.0).

Two levels are covered: what ``async_get_triggers`` offers to the automation editor,
and what actually happens when an automation built on one of those triggers is loaded
and the matching bus event is fired.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import voluptuous as vol
from homeassistant.components import automation
from homeassistant.components.device_automation import DeviceAutomationType
from homeassistant.components.device_automation.exceptions import (
    InvalidDeviceAutomationConfig,
)
from homeassistant.const import CONF_PLATFORM
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    async_get_device_automations,
    async_mock_service,
)

from custom_components.myhome.const import (
    DOMAIN,
    EVENT_CENPLUS,
    SCENARIO_CONTROL_EVENT_TYPES,
)
from custom_components.myhome.device_trigger import CONF_SUBTYPE, TRIGGER_SCHEMA

from .helpers_core import MAC
from .helpers_platforms import setup_myhome

SCENARIO_YAML = f"""
gateway:
  mac: {MAC}
  scenario_control:
    keypad_soggiorno:
      object: 25
      name: Keypad Soggiorno
      buttons: [1, 2]
    keypad_ingresso:
      protocol: cen
      where: '51'
      name: Keypad Ingresso
      buttons: [0]
  light:
    light_test:
      where: '11'
      name: Light Test
"""


def device_id_of(hass: HomeAssistant, entry_id: str, key: str) -> str:
    """Registry id of the scenario-control device with the given device key."""
    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, f"{MAC}-{key}"), entry_id)
    assert device is not None, key
    return device.id


def same_triggers(actual: list[dict[str, Any]], expected: list[dict[str, Any]]) -> bool:
    """Order-insensitive comparison (the editor does not care about the order)."""
    key = lambda item: tuple(sorted((k, str(v)) for k, v in item.items()))  # noqa: E731
    return sorted(actual, key=key) == sorted(expected, key=key)


@pytest.fixture
def calls(hass: HomeAssistant) -> list[ServiceCall]:
    """Service calls the test automations make."""
    return async_mock_service(hass, "test", "automation")


# ------------------------------------------------------------------- async_get_triggers
async def test_triggers_offered_for_a_cenplus_control(hass: HomeAssistant, tmp_path) -> None:
    """One trigger per (declared button x event name of the protocol)."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        device_id = device_id_of(hass, entry.entry_id, "cenplus-25")
        triggers = await async_get_device_automations(hass, DeviceAutomationType.TRIGGER, device_id)
        ours = [item for item in triggers if item["domain"] == DOMAIN]
        expected = [
            {
                CONF_PLATFORM: "device",
                "domain": DOMAIN,
                "device_id": device_id,
                "type": trigger_type,
                CONF_SUBTYPE: f"button_{button}",
                "metadata": {},
            }
            for button in (1, 2)
            for trigger_type in SCENARIO_CONTROL_EVENT_TYPES["cen_plus"]
        ]
        assert len(ours) == 2 * len(SCENARIO_CONTROL_EVENT_TYPES["cen_plus"])
        assert same_triggers(ours, expected)


async def test_triggers_offered_for_a_cen_control(hass: HomeAssistant, tmp_path) -> None:
    """CEN has its own, shorter set: no long-press repeat and no rotation."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        device_id = device_id_of(hass, entry.entry_id, "cen-51")
        triggers = await async_get_device_automations(hass, DeviceAutomationType.TRIGGER, device_id)
        ours = [item for item in triggers if item["domain"] == DOMAIN]
        assert {item["type"] for item in ours} == set(SCENARIO_CONTROL_EVENT_TYPES["cen"])
        assert {item[CONF_SUBTYPE] for item in ours} == {"button_0"}
        assert "pushbutton_long_press_repeat" not in {item["type"] for item in ours}


async def test_no_triggers_for_a_normal_device(hass: HomeAssistant, tmp_path) -> None:
    """A light is not a scenario control: our platform must offer nothing for it."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        device_id = device_id_of(hass, entry.entry_id, "1-11")
        triggers = await async_get_device_automations(hass, DeviceAutomationType.TRIGGER, device_id)
        assert [item for item in triggers if item["domain"] == DOMAIN] == []


@pytest.mark.parametrize(
    "bad",
    [
        {"type": "nope", CONF_SUBTYPE: "button_1"},
        {"type": "pushbutton_short_press", CONF_SUBTYPE: "button_33"},
        {"type": "pushbutton_short_press"},
        {CONF_SUBTYPE: "button_1"},
    ],
)
def test_trigger_schema_rejects_unknown_type_and_subtype(bad: dict[str, Any]) -> None:
    """The schema is a closed set: only real event names and buttons 0-32."""
    base = {CONF_PLATFORM: "device", "domain": DOMAIN, "device_id": "abc"}
    TRIGGER_SCHEMA({**base, "type": "pushbutton_short_press", CONF_SUBTYPE: "button_1"})
    with pytest.raises(vol.Invalid):
        TRIGGER_SCHEMA({**base, **bad})


# --------------------------------------------------------------------- attached trigger
async def _load_automation(hass: HomeAssistant, trigger: dict[str, Any], trigger_id: str) -> None:
    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": trigger,
                    "action": {
                        "service": "test.automation",
                        "data": {"id": trigger_id, "pushbutton": "{{ trigger.event.data.pushbutton }}"},
                    },
                }
            ]
        },
    )
    await hass.async_block_till_done()


async def test_attached_cenplus_trigger_fires(hass: HomeAssistant, tmp_path, calls) -> None:
    """The device trigger listens to myhome_cenplus_event filtered on mac/object/button/event."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        device_id = device_id_of(hass, entry.entry_id, "cenplus-25")
        await _load_automation(
            hass,
            {
                CONF_PLATFORM: "device",
                "domain": DOMAIN,
                "device_id": device_id,
                "type": "pushbutton_long_press",
                CONF_SUBTYPE: "button_2",
            },
            "long_press_2",
        )

        # The exact press the trigger stands for.
        hass.bus.async_fire(
            EVENT_CENPLUS,
            {"object": 25, "pushbutton": 2, "event": "pushbutton_long_press", "mac": MAC},
        )
        await hass.async_block_till_done()
        assert len(calls) == 1
        assert calls[0].data == {"id": "long_press_2", "pushbutton": 2}

        # Wrong button, wrong event, wrong object and wrong gateway must all be ignored.
        for payload in (
            {"object": 25, "pushbutton": 1, "event": "pushbutton_long_press", "mac": MAC},
            {"object": 25, "pushbutton": 2, "event": "pushbutton_short_press", "mac": MAC},
            {"object": 26, "pushbutton": 2, "event": "pushbutton_long_press", "mac": MAC},
            {"object": 25, "pushbutton": 2, "event": "pushbutton_long_press", "mac": "00:03:50:00:00:02"},
        ):
            hass.bus.async_fire(EVENT_CENPLUS, payload)
        await hass.async_block_till_done()
        assert len(calls) == 1


async def test_attached_cen_trigger_fires_on_a_real_frame(hass: HomeAssistant, tmp_path, calls) -> None:
    """End to end: a bus frame reaches the automation through the device trigger."""
    from .test_event import feed_frame

    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        device_id = device_id_of(hass, entry.entry_id, "cen-51")
        await _load_automation(
            hass,
            {
                CONF_PLATFORM: "device",
                "domain": DOMAIN,
                "device_id": device_id,
                "type": "pushbutton_short_press",
                CONF_SUBTYPE: "button_0",
            },
            "cen_press",
        )

        await feed_frame(hass, "*15*0*51##")
        assert [call.data["id"] for call in calls] == ["cen_press"]

        # A CEN+ frame with the same numbers must not reach a CEN trigger.
        hass.bus.async_fire(
            EVENT_CENPLUS, {"object": 51, "pushbutton": 0, "event": "pushbutton_short_press", "mac": MAC}
        )
        await hass.async_block_till_done()
        assert len(calls) == 1


async def test_trigger_on_a_removed_device_is_reported(hass: HomeAssistant, tmp_path) -> None:
    """A device that is gone must be reported, not silently swallowed.

    Returning ``None`` from ``async_attach_trigger`` makes Home Assistant log its own
    "Unknown error while setting up trigger (empty result)", which names neither the
    integration nor the device, and leaves the automation enabled but inert.
    """
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML):
        from custom_components.myhome import device_trigger

        config = {
            CONF_PLATFORM: "device",
            "domain": DOMAIN,
            "device_id": "does-not-exist",
            "type": "pushbutton_short_press",
            CONF_SUBTYPE: "button_1",
        }
        assert await device_trigger.async_get_triggers(hass, "does-not-exist") == []
        with pytest.raises(InvalidDeviceAutomationConfig, match="does-not-exist"):
            await device_trigger.async_validate_trigger_config(hass, config)
        with pytest.raises(InvalidDeviceAutomationConfig, match="scenario control"):
            await device_trigger.async_attach_trigger(
                hass,
                config,
                lambda *args, **kwargs: None,
                {"domain": DOMAIN, "name": "test", "home_assistant_start": False, "variables": {}, "trigger_data": {}},
            )


async def test_a_light_device_is_refused_as_a_scenario_control(hass: HomeAssistant, tmp_path) -> None:
    """The failure mode finding 1 describes: a picked light must break loudly.

    The device exists and belongs to a ``myhome`` config entry, so Home Assistant's own
    validation passes it; only our validator can tell that it can never fire.
    """
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        from custom_components.myhome import device_trigger

        device_id = device_id_of(hass, entry.entry_id, "1-11")
        with pytest.raises(InvalidDeviceAutomationConfig, match=r"MyHOME CEN/CEN\+ scenario control"):
            await device_trigger.async_validate_trigger_config(
                hass,
                {
                    CONF_PLATFORM: "device",
                    "domain": DOMAIN,
                    "device_id": device_id,
                    "type": "pushbutton_short_press",
                    CONF_SUBTYPE: "button_1",
                },
            )


async def test_an_event_the_protocol_cannot_fire_is_refused(hass: HomeAssistant, tmp_path) -> None:
    """A CEN control can never rotate or repeat a long press: refuse those triggers."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        from custom_components.myhome import device_trigger

        cen_device = device_id_of(hass, entry.entry_id, "cen-51")
        base = {CONF_PLATFORM: "device", "domain": DOMAIN, "device_id": cen_device}
        for bad_type in ("pushbutton_long_press_repeat", "rotate_cw_slow"):
            with pytest.raises(InvalidDeviceAutomationConfig, match=bad_type):
                await device_trigger.async_validate_trigger_config(
                    hass, {**base, "type": bad_type, CONF_SUBTYPE: "button_0"}
                )
        # A CEN event on the same device still validates.
        validated = await device_trigger.async_validate_trigger_config(
            hass, {**base, "type": "pushbutton_short_release", CONF_SUBTYPE: "button_0"}
        )
        assert validated["type"] == "pushbutton_short_release"


async def test_an_automation_on_a_light_device_fails_to_set_up(
    hass: HomeAssistant, tmp_path, calls, caplog
) -> None:
    """End to end: the automation must be disabled, with the device named (finding 1).

    Before the fix it came up as ``on`` -- no visible error on its card -- and never
    fired, which is the worst failure mode a blueprint can produce.
    """
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        device_id = device_id_of(hass, entry.entry_id, "1-11")
        await _load_automation(
            hass,
            {
                CONF_PLATFORM: "device",
                "domain": DOMAIN,
                "device_id": device_id,
                "type": "pushbutton_short_press",
                CONF_SUBTYPE: "button_1",
            },
            "on_a_light",
        )
        states = [hass.states.get(entity_id) for entity_id in hass.states.async_entity_ids(automation.DOMAIN)]
        assert all(state.state != "on" for state in states)
        assert f"Device {device_id} is not a MyHOME CEN/CEN+ scenario control" in caplog.text


async def test_buttons_default_when_the_entry_is_not_loaded(hass: HomeAssistant, tmp_path) -> None:
    """The editor lists triggers of unloaded entries too: fall back to the default list."""
    async with setup_myhome(hass, tmp_path, SCENARIO_YAML) as (entry, _commands):
        device_id = device_id_of(hass, entry.entry_id, "cenplus-25")
        hass.data[DOMAIN].pop(MAC)
        from custom_components.myhome import device_trigger

        triggers = await device_trigger.async_get_triggers(hass, device_id)
        assert {item[CONF_SUBTYPE] for item in triggers} == {"button_1", "button_2", "button_3", "button_4"}


# ------------------------------------------------------------------------- blueprints
@pytest.mark.parametrize("name", ["cenplus_button_light.yaml", "cenplus_button_cover.yaml"])
def test_shipped_blueprints_are_valid(name: str) -> None:
    """The blueprints we ship must parse, validate and use real device triggers."""
    from homeassistant.components.blueprint import models, schemas
    from homeassistant.util.yaml import loader as yaml_loader

    path = Path(__file__).resolve().parent.parent / "blueprints" / "automation" / "myhome" / name
    blueprint = models.Blueprint(
        schemas.BLUEPRINT_SCHEMA(yaml_loader.load_yaml(str(path))),
        expected_domain=automation.DOMAIN,
        schema=schemas.BLUEPRINT_SCHEMA,
    )
    assert "scenario_control" in blueprint.inputs

    # The device picker must offer scenario controls only: the ``event`` platform is
    # used by nothing else in this integration, and a trigger on any other MyHOME
    # device is refused by ``async_validate_trigger_config``, i.e. a dead automation.
    selector = blueprint.inputs["scenario_control"]["selector"]["device"]
    assert selector["filter"] == [{"integration": DOMAIN}]
    assert selector["entity"] == [{"domain": ["event"]}]

    # Both dropdowns stop at button 8, so both descriptions must say so.
    assert "buttons 1-8" in blueprint.metadata["description"]

    # Substitute the inputs the way Home Assistant does and check the triggers we get.
    inputs = {"scenario_control": "0123456789abcdef0123456789abcdef"}
    inputs.update(
        {"button": "button_3", "target_light": "light.kitchen"}
        if "light" in name
        else {"button_up": "button_1", "button_down": "button_2", "target_cover": "cover.living"}
    )
    config = models.BlueprintInputs(
        blueprint, {"use_blueprint": {"path": name, "input": inputs}, "alias": "t"}
    ).async_substitute()

    for trigger in config["triggers"]:
        assert trigger["trigger"] == "device"
        assert trigger["domain"] == DOMAIN
        assert trigger["type"] in SCENARIO_CONTROL_EVENT_TYPES["cen_plus"]
        assert trigger[CONF_SUBTYPE].startswith("button_")
        # The same dict must satisfy our own trigger schema (minus the trigger/platform
        # key rename Home Assistant does when it loads the automation).
        TRIGGER_SCHEMA(
            {k: v for k, v in trigger.items() if k not in ("trigger", "id")}
            | {CONF_PLATFORM: "device"}
        )
