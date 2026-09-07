"""Tests for the MyHOME binary sensor platform."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR, BinarySensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    EntityCategory,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache,
    mock_restore_cache_with_extra_data,
)

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
    light_test:
      where: '11'
      name: Light Test
"""

SENSORS_YAML = f"""
gateway:
  mac: {MAC}
  binary_sensor:
    window_contact:
      who: '25'
      where: '31'
      name: Window Contact
      device_class: window
    door_contact:
      who: '25'
      where: '32'
      name: Door Contact
      entity_name: Left Wing
    alarm_aux:
      who: '9'
      where: '1'
      name: Alarm Aux
"""

# `inverted` on the two flavours that never had a test for it (F7), plus the icon pair
# the documentation shows on a binary sensor (INCONSISTENCY-1).
INVERTED_YAML = f"""
gateway:
  mac: {MAC}
  binary_sensor:
    garden_gate:
      who: '25'
      where: '33'
      name: Garden Gate
      class: door
      inverted: true
      icon: 'mdi:gate'
      icon_on: 'mdi:gate-open'
    alarm_relay:
      who: '9'
      where: '2'
      name: Alarm Relay
      inverted: true
    back_door:
      who: '25'
      where: '34'
      name: Back Door
      class: door
      icon_on: 'mdi:door-open'
"""

MOTION_YAML = f"""
gateway:
  mac: {MAC}
  binary_sensor:
    motion_sensor:
      who: '1'
      where: '11'
      name: Motion Sensor
      class: motion
    inverted_sensor:
      who: '1'
      where: '12'
      name: Inverted Sensor
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

        # INCONSISTENCY-3: the binary sensor is the main entity of its device, like a
        # light or a cover, so it is named after the device - not after a hardcoded
        # English class label appended to it ("Window Contact Window", id ..._window).
        window = hass.states.get("binary_sensor.window_contact")
        assert window.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.WINDOW
        assert window.attributes["friendly_name"] == "Window Contact"

        aux = hass.states.get("binary_sensor.alarm_aux")
        assert aux is not None
        assert ATTR_DEVICE_CLASS not in aux.attributes
        assert aux.attributes["friendly_name"] == "Alarm Aux"

        # An explicit entity_name still names the entity inside its device.
        named = hass.states.get("binary_sensor.door_contact_left_wing")
        assert named.attributes["friendly_name"] == "Door Contact Left Wing"


async def test_dry_contact_events(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, SENSORS_YAML, clear_commands=False) as (_entry, commands):
        assert "*#25*31##" in commands.status_frames

        sensor = entity_object(hass, BINARY_SENSOR, "25-31")
        await feed_event(hass, sensor, "*25*31#31*31##")
        assert hass.states.get("binary_sensor.window_contact").state == STATE_ON
        await feed_event(hass, sensor, "*25*32#31*31##")
        assert hass.states.get("binary_sensor.window_contact").state == STATE_OFF


async def test_inverted_dry_contact_and_auxiliary(hass: HomeAssistant, tmp_path) -> None:
    """F7: `inverted` was only ever tested on the motion sensor.

    The dry contact and the auxiliary channel go through ``_apply_state``, a different
    line, which nothing exercised: dropping the ``!= self._inverted`` left the suite
    green while every inverted contact reported the opposite state.
    """
    async with setup_myhome(hass, tmp_path, INVERTED_YAML):
        gate = entity_object(hass, BINARY_SENSOR, "25-33")
        relay = entity_object(hass, BINARY_SENSOR, "9-2")

        # `*25*32#31*33##` is the contact's OFF frame: an inverted sensor reads it ON.
        await feed_event(hass, gate, "*25*32#31*33##")
        assert hass.states.get("binary_sensor.garden_gate").state == STATE_ON
        await feed_event(hass, gate, "*25*31#31*33##")
        assert hass.states.get("binary_sensor.garden_gate").state == STATE_OFF

        # F7: the WHO 9 entity was created but never fed a frame at all.
        await feed_event(hass, relay, "*9*2*2##")
        assert hass.states.get("binary_sensor.alarm_relay").state == STATE_ON
        await feed_event(hass, relay, "*9*1*2##")
        assert hass.states.get("binary_sensor.alarm_relay").state == STATE_OFF


async def test_icon_and_icon_on_are_honoured(hass: HomeAssistant, tmp_path) -> None:
    """INCONSISTENCY-1: both keys were accepted, documented and then ignored here."""
    async with setup_myhome(hass, tmp_path, INVERTED_YAML):
        gate = entity_object(hass, BINARY_SENSOR, "25-33")
        assert hass.states.get("binary_sensor.garden_gate").attributes["icon"] == "mdi:gate"
        await feed_event(hass, gate, "*25*32#31*33##")
        assert hass.states.get("binary_sensor.garden_gate").attributes["icon"] == "mdi:gate-open"


async def test_icon_on_alone_is_applied(hass: HomeAssistant, tmp_path) -> None:
    """P2-INCONSISTENCY-1: `icon_on` is documented as an independent key.

    Without an `icon` next to it the pair was skipped entirely, so a configuration that
    sets only `icon_on` got no icon at all - and no way to tell whether the key had
    been rejected or mis-spelled. While off the entity falls back to what HA would
    show on its own (the `door` device-class icon), which is the point of leaving
    `icon` out.
    """
    async with setup_myhome(hass, tmp_path, INVERTED_YAML):
        door = entity_object(hass, BINARY_SENSOR, "25-34")
        assert "icon" not in hass.states.get("binary_sensor.back_door").attributes

        await feed_event(hass, door, "*25*31#31*34##")
        assert hass.states.get("binary_sensor.back_door").state == STATE_ON
        assert hass.states.get("binary_sensor.back_door").attributes["icon"] == "mdi:door-open"

        await feed_event(hass, door, "*25*32#31*34##")
        assert hass.states.get("binary_sensor.back_door").state == STATE_OFF
        assert "icon" not in hass.states.get("binary_sensor.back_door").attributes


async def test_motion_timeout_respects_inverted(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """plat-11: the timeout clears the sensor symmetrically for inverted sensors."""
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        normal = entity_object(hass, BINARY_SENSOR, "1-11")
        inverted = entity_object(hass, BINARY_SENSOR, "1-12")

        await feed_event(hass, normal, "*1*34*11##")
        await feed_event(hass, inverted, "*1*34*12##")
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_ON
        assert hass.states.get("binary_sensor.inverted_sensor").state == STATE_OFF

        await _advance(hass, freezer, 316)
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_OFF
        assert hass.states.get("binary_sensor.inverted_sensor").state == STATE_ON


async def test_motion_timeout_frame_updates_the_timer(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The sensor's own timeout (+15 s margin) drives the expiry."""
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        normal = entity_object(hass, BINARY_SENSOR, "1-11")
        await feed_event(hass, normal, "*#1*11*7*0*1*0##")
        assert hass.states.get("binary_sensor.motion_sensor").attributes["Timeout"] == 75.0

        await feed_event(hass, normal, "*1*34*11##")
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_ON
        await _advance(hass, freezer, 60)
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_ON
        await _advance(hass, freezer, 20)
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_OFF


async def test_motion_sensitivity_and_unknown_frames(hass: HomeAssistant, tmp_path) -> None:
    """plat-03: unrelated dimension replies are ignored, never raised.

    "Ignored" is now asserted as *nothing changed* rather than as `is not None`.
    The entity still existing only proves the frame did not raise: the old
    assertion kept passing for the whole class of regressions where an unrelated
    frame quietly clobbers the state or an attribute of a motion sensor, which is
    the actual guarantee `handle_event`'s message-type filter is there to give.

    Mutation caught: the plausible "simplify handle_event" refactor that drops the
    message-type filter and widens the last arm to a bare `else`, after which a
    timer reply rewrites the sensor's Sensitivity. Note that dropping the filter
    *on its own* is inert - the `if/elif` chain below it matches nothing for such
    a frame - so no single-line mutation of it is observable; what the snapshot
    pins is the pair, and with it the whole class of "an unrelated frame quietly
    changed something", which `is not None` could never have seen.

    Note: `binary_sensor.py`'s `0 <= sensitivity < len(PIR_SENSITIVITY)` range
    check cannot be reached from a real frame on OWNd 0.7.49 - OWNd builds its own
    log line with `PIR_SENSITIVITY_MAPPING[value]` first and raises IndexError, so
    `parse_frame` returns the raw text and the message never reaches an entity.
    The guard is defensive against a future OWNd that widens that mapping; it is
    deliberately not what this test pins.
    """
    entity_id = "binary_sensor.motion_sensor"
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        normal = entity_object(hass, BINARY_SENSOR, "1-11")
        await feed_event(hass, normal, "*#1*11*5*3##")
        assert hass.states.get(entity_id).attributes["Sensitivity"] == "very high"

        before = hass.states.get(entity_id)
        # A dimension reply that belongs to another feature of the same WHERE.
        await feed_event(hass, normal, "*#1*11*2*0*1*0##")
        after = hass.states.get(entity_id)
        assert after.state == before.state
        assert dict(after.attributes) == dict(before.attributes)

        # A real PIR frame still gets through: the filter is not a blanket refusal.
        await feed_event(hass, normal, "*#1*11*5*0##")
        assert hass.states.get(entity_id).attributes["Sensitivity"] == "low"


async def test_motion_state_restored(hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory) -> None:
    """A restart keeps the motion state and re-arms the remaining timeout."""
    mock_restore_cache(hass, (State("binary_sensor.motion_sensor", STATE_ON),))
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_ON
        await _advance(hass, freezer, 316)
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_OFF


async def test_availability_follows_connection_signal(hass: HomeAssistant, tmp_path) -> None:
    async with setup_myhome(hass, tmp_path, SENSORS_YAML):
        await set_connected(hass, False)
        assert hass.states.get("binary_sensor.window_contact").state == STATE_UNAVAILABLE
        await set_connected(hass, True)
        assert hass.states.get("binary_sensor.window_contact").state != STATE_UNAVAILABLE


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
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_ON

        await _advance(hass, freezer, 100)  # 215 s left of the 315 s timeout
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_ON
        # The timeout is not restarted from scratch: what was left of it still applies.
        await _advance(hass, freezer, 200)
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_ON
        await _advance(hass, freezer, 20)
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_OFF


async def test_motion_extra_data_restores_expired_state(hass: HomeAssistant, tmp_path) -> None:
    """An expiry in the past clears the sensor instead of re-arming a timer."""
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State("binary_sensor.motion_sensor", STATE_UNAVAILABLE),
                {
                    "is_on": True,
                    "expires_at": (dt_util.utcnow() - timedelta(seconds=5)).isoformat(),
                },
            ),
        ),
    )
    async with setup_myhome(hass, tmp_path, MOTION_YAML):
        assert hass.states.get("binary_sensor.motion_sensor").state == STATE_OFF


# ------------------------------------------------------------------ WHO 9 auxiliary
async def test_auxiliary_channel_starts_unknown(hass: HomeAssistant, tmp_path) -> None:
    """P2-RISK-2: a WHO 9 channel cannot be queried, so it does not know its state.

    It used to report a hard `off` from the moment it was created, whatever the bus
    actually held and whatever `inverted` said (P3-NIT-5: `__init__` assigned
    `_attr_is_on` directly, so the inversion was not applied to the initial value) - an
    automation saw a transition that never happened. OWNd 0.7.49 has no auxiliary
    command class at all, so `unknown` until the first spontaneous frame is the only
    honest answer.
    """
    async with setup_myhome(hass, tmp_path, INVERTED_YAML):
        assert hass.states.get("binary_sensor.alarm_relay").state == STATE_UNKNOWN

        # `*9*2*2##` is WHAT 2 (toggle, `is_on` False); the channel is `inverted`.
        await feed_event(hass, entity_object(hass, BINARY_SENSOR, "9-2"), "*9*2*2##")
        assert hass.states.get("binary_sensor.alarm_relay").state == STATE_ON


async def test_auxiliary_channel_survives_a_reload(hass: HomeAssistant, tmp_path) -> None:
    """P2-RISK-2: the channel used to silently fall back to `off` on every reload.

    On unload the gateway connection is closed before the entities are removed, so HA
    snapshots them as ``unavailable``: the value has to travel through
    ``extra_restore_state_data`` (same pattern as the motion sensor).
    """
    async with setup_myhome(hass, tmp_path, INVERTED_YAML) as (entry, _commands):
        await feed_event(hass, entity_object(hass, BINARY_SENSOR, "9-2"), "*9*2*2##")
        assert hass.states.get("binary_sensor.alarm_relay").state == STATE_ON

        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        assert hass.states.get("binary_sensor.alarm_relay").state == STATE_ON


async def test_auxiliary_channel_restored_after_a_restart(hass: HomeAssistant, tmp_path) -> None:
    """A restart leaves a usable state snapshot rather than extra data."""
    mock_restore_cache(hass, (State("binary_sensor.alarm_relay", STATE_ON),))
    async with setup_myhome(hass, tmp_path, INVERTED_YAML):
        assert hass.states.get("binary_sensor.alarm_relay").state == STATE_ON


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

        assert hass.states.get("binary_sensor.window_contact").state == STATE_UNAVAILABLE
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
