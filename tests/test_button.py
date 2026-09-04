"""Tests for the MyHOME Lock/Unlock buttons (WHO 14)."""

from __future__ import annotations

from homeassistant.components.button import DOMAIN as BUTTON
from homeassistant.const import ATTR_ENTITY_ID, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from OWNd.message import OWNCommand

from custom_components.myhome import expected_unique_ids
from custom_components.myhome.const import CONF_ENTITIES, CONF_PLATFORMS, DOMAIN

from .helpers_core import MAC
from .helpers_platforms import device_config, entity_object, real_config_yaml, setup_myhome

LOCK_YAML = f"""
gateway:
  mac: {MAC}
  light:
    luce_test:
      where: '11'
      name: Luce Test
      lock_buttons: true
    luce_senza_pulsanti:
      where: '12'
      name: Luce Senza Pulsanti
"""


async def test_no_buttons_without_opt_in(hass: HomeAssistant, tmp_path) -> None:
    """plat-08: the user's real config has no `lock_buttons`, so no buttons at all."""
    async with setup_myhome(hass, tmp_path, real_config_yaml()) as (entry, _commands):
        entity_registry = er.async_get(hass)
        buttons = [
            item
            for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            if item.domain == BUTTON
        ]
        assert buttons == []
        assert BUTTON not in hass.data[DOMAIN][MAC][CONF_PLATFORMS]


async def test_buttons_created_for_opted_in_device(hass: HomeAssistant, tmp_path) -> None:
    """Two buttons on the opted-in light only, with the documented unique ids."""
    async with setup_myhome(hass, tmp_path, LOCK_YAML) as (entry, _commands):
        entity_registry = er.async_get(hass)
        buttons = [
            item
            for item in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
            if item.domain == BUTTON
        ]
        assert len(buttons) == 2
        assert {item.unique_id for item in buttons} == {f"{MAC}-1-11-disable", f"{MAC}-1-11-enable"}

        platforms = hass.data[DOMAIN][MAC][CONF_PLATFORMS]
        assert {item.unique_id for item in buttons} == expected_unique_ids(MAC, {BUTTON: platforms[BUTTON]})

        for item in buttons:
            assert item.entity_category is EntityCategory.CONFIG
        assert {item.translation_key for item in buttons} == {"lock", "unlock"}

        # plat-09: the button config is a copy, it does not share the light's entities.
        assert device_config(hass, BUTTON, "1-11") is not device_config(hass, "light", "1-11")
        assert device_config(hass, BUTTON, "1-11")["source_platform"] == "light"
        assert set(device_config(hass, BUTTON, "1-11")[CONF_ENTITIES]) == {"disable", "enable"}
        assert set(device_config(hass, "light", "1-11")[CONF_ENTITIES]) == {"light"}


async def test_button_names_and_press(hass: HomeAssistant, tmp_path) -> None:
    """plat-16: translated names; plat-08: a parsed OWNCommand, never a raw string."""
    async with setup_myhome(hass, tmp_path, LOCK_YAML) as (_entry, commands):
        lock = hass.states.get("button.luce_test_lock")
        unlock = hass.states.get("button.luce_test_unlock")
        assert lock.attributes["friendly_name"] == "Luce Test Lock"
        assert unlock.attributes["friendly_name"] == "Luce Test Unlock"

        await hass.services.async_call(BUTTON, "press", {ATTR_ENTITY_ID: "button.luce_test_lock"}, blocking=True)
        await hass.services.async_call(BUTTON, "press", {ATTR_ENTITY_ID: "button.luce_test_unlock"}, blocking=True)
        assert commands.sent_frames == ["*14*0*11##", "*14*1*11##"]
        assert all(isinstance(message, OWNCommand) for message in commands.sent)
        assert all(message.is_valid for message in commands.sent)


async def test_buttons_use_their_own_registry_slots(hass: HomeAssistant, tmp_path) -> None:
    """Both buttons of a device must coexist in the shared `entities` dict."""
    async with setup_myhome(hass, tmp_path, LOCK_YAML):
        disable = entity_object(hass, BUTTON, "1-11", "disable")
        enable = entity_object(hass, BUTTON, "1-11", "enable")
        assert disable is not enable
        assert disable.unique_id.endswith("-disable")
        assert enable.unique_id.endswith("-enable")
