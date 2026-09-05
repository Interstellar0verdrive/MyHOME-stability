"""Tests for ``custom_components.myhome.validate`` (Contract A of the fix-phase contracts).

Pure-python: no ``hass`` fixture is needed.  The module is loaded through
``_load_validate()`` so that the tests keep working while the package ``__init__``
is being reworked (a stub package is registered when the real one fails to import).
"""
from __future__ import annotations

import copy
import importlib
import json
import logging
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
# Redacted copy of the user's real configuration (20 lights, 12 covers, 3 power meters).
USER_YAML = REPO_ROOT / "tests" / "fixtures" / "myhome.yaml"
MAC = "00:03:50:AA:BB:CC"
MAC_NORM = "00:03:50:aa:bb:cc"
MAC2 = "00:03:50:00:00:02"


def _load_validate():
    """Import ``custom_components.myhome.validate`` even if the package __init__ is broken."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        return importlib.import_module("custom_components.myhome.validate")
    except ImportError:
        for name in list(sys.modules):
            if name.startswith("custom_components"):
                del sys.modules[name]
        parent = types.ModuleType("custom_components")
        parent.__path__ = [str(REPO_ROOT / "custom_components")]
        package = types.ModuleType("custom_components.myhome")
        package.__path__ = [str(REPO_ROOT / "custom_components" / "myhome")]
        sys.modules["custom_components"] = parent
        sys.modules["custom_components.myhome"] = package
        importlib.import_module("custom_components.myhome.const")
        return importlib.import_module("custom_components.myhome.validate")


validate = _load_validate()
Invalid = validate.Invalid


def gw(**sections) -> dict:
    """A ``gateway:`` style config with the given platform sections."""
    return {"gateway": {"mac": MAC, **sections}}


def platforms(out: dict, mac: str = MAC_NORM) -> dict:
    return out[mac][validate.CONF_PLATFORMS]


def check(data: dict) -> dict:
    return validate.config_schema(copy.deepcopy(data))


# --------------------------------------------------------------------------------------
# The user's real configuration
# --------------------------------------------------------------------------------------
@pytest.fixture
def user_config() -> dict:
    return yaml.safe_load(USER_YAML.read_text())


def test_user_config_duplicate_where_raises(user_config):
    # The historical bug (val-01 / CONSOLIDATED F): a second cover reusing WHERE '81'
    # used to overwrite the first one silently.  The fixture is clean, so the
    # duplicate is injected here.
    covers = user_config["gateway"]["cover"]
    assert covers["kids_room_shutter_2"]["where"] == "81"
    covers["kids_room_shutter_old"] = {"where": "81", "name": "Kids Room Shutter Old"}
    with pytest.raises(Invalid) as err:
        check(user_config)
    message = str(err.value)
    assert "'81'" in message
    assert "kids_room_shutter_old" in message
    assert "kids_room_shutter_2" in message
    # The path points at the second occurrence (the injected one).
    assert err.value.path == ["gateway", "cover", "kids_room_shutter_old", "where"]


def test_user_config_after_rename(user_config):
    # The fixture holds 12 covers; adding the "renamed" one (WHERE '87') gives 13.
    user_config["gateway"]["cover"]["kids_room_shutter_old"] = {
        "where": "87",
        "name": "Kids Room Shutter Old",
    }
    out = check(user_config)
    assert list(out) == [MAC_NORM]
    plat = platforms(out)
    assert set(plat) == {"light", "cover", "sensor"}  # no lock_buttons -> no button platform
    assert len(plat["cover"]) == 13
    assert len(plat["light"]) == 20
    assert len(plat["sensor"]) == 3
    assert "2-87" in plat["cover"] and "2-81" in plat["cover"]

    for sensor in plat["sensor"].values():
        assert sensor["keepalive_minutes"] == 125
        assert sensor["class"] == validate.SensorDeviceClass.POWER
        assert sensor["who"] == "18"
        assert set(sensor["entities"]) == {"daily-energy", "monthly-energy", "total-energy", "power"}
    assert plat["sensor"]["18-53"]["min_delta_w"] == 1  # per-sensor override
    assert plat["sensor"]["18-51"]["min_delta_w"] == 5  # gateway sensor_defaults
    assert plat["sensor"]["18-51"]["min_interval_sec"] == 5.0
    assert out[MAC_NORM]["sensor_defaults"] == {
        "min_delta_w": 5,
        "min_interval_sec": 5.0,
        "suppress_log_interval_sec": 60.0,
        "keepalive_minutes": 125,
    }

    cover = plat["cover"]["2-91"]
    assert cover["shutter_run"] == 30.0
    assert cover["class"] == validate.CoverDeviceClass.SHUTTER
    assert "device_class" not in cover
    assert cover["icon"] == "mdi:window-shutter"
    assert cover["inverted"] is False and cover["advanced"] is False
    assert plat["light"]["1-11"]["icon"] == "mdi:ceiling-light"


# --------------------------------------------------------------------------------------
# Root styles (val-04, val-14)
# --------------------------------------------------------------------------------------
def test_legacy_mac_root():
    out = check({MAC: {"light": {"a": {"where": "15", "name": "A"}}}})
    assert list(out) == [MAC_NORM]
    assert list(platforms(out)["light"]) == ["1-15"]


def test_mac_root_with_matching_inner_mac():
    out = check({MAC: {"mac": MAC_NORM, "light": {"a": {"where": "15", "name": "A"}}}})
    assert list(out) == [MAC_NORM]


def test_mac_root_with_mismatching_inner_mac():
    with pytest.raises(Invalid, match="must match"):
        check({MAC: {"mac": MAC2, "light": {}}})


def test_multi_gateway():
    out = check(
        {
            "gateway": {"mac": MAC, "light": {"a": {"where": "15", "name": "A"}}},
            MAC2: {"switch": {"b": {"where": "15", "name": "B"}}},
        }
    )
    assert set(out) == {MAC_NORM, MAC2}
    assert list(platforms(out)["light"]) == ["1-15"]
    assert list(platforms(out, MAC2)["switch"]) == ["1-15"]


def test_duplicate_mac_roots():
    with pytest.raises(Invalid, match="configured twice"):
        check({"gateway": {"mac": MAC}, MAC: {}})


def test_root_without_mac():
    with pytest.raises(Invalid, match="needs a 'mac"):
        check({"casa": {"light": {}}})


def test_non_string_root_key():
    with pytest.raises(Invalid):
        check({1: {"mac": MAC}})


# --------------------------------------------------------------------------------------
# MAC and ranges (val-05, val-06)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("mac", [350, None, "", "00:03:50", "zz:03:50:aa:bb:cc"])
def test_invalid_mac_raises_invalid(mac):
    with pytest.raises(Invalid):
        check({"gateway": {"mac": mac}})


@pytest.mark.parametrize("mac", ["00:03:50:AA:BB:CC", "00-03-50-aa-bb-cc", "000350AABBCC", "00.03.50.aa.bb.cc"])
def test_mac_notations(mac):
    assert validate.MacAddress()(mac) == MAC_NORM


def test_negative_ranges_raise():
    with pytest.raises(Invalid, match="at least 0"):
        check(gw(energy={"min_delta_w": -5}))
    with pytest.raises(Invalid, match="at least 0"):
        check(gw(sensor={"s": {"where": "51", "name": "S", "class": "power", "min_interval_sec": -1}}))
    with pytest.raises(Invalid, match="at most 255"):
        check(gw(sensor={"s": {"where": "51", "name": "S", "class": "power", "keepalive_minutes": 300}}))
    with pytest.raises(Invalid):
        check(gw(cover={"c": {"where": "81", "name": "C", "shutter_run": 0}}))


# --------------------------------------------------------------------------------------
# Cover two-phase travel: slat_time / opening_time / closing_time (0.4.0)
# --------------------------------------------------------------------------------------
def test_cover_travel_times_default_to_shutter_run():
    """``opening_time`` / ``closing_time`` fall back to ``shutter_run``, per direction."""
    out = check(
        gw(
            cover={
                "sym": {"where": "81", "name": "Sym", "shutter_run": 30, "slat_time": 3},
                "asym": {
                    "where": "82",
                    "name": "Asym",
                    "shutter_run": 30,
                    "slat_time": 3,
                    "opening_time": 32,
                    "closing_time": 28,
                },
                "up_only": {"where": "83", "name": "Up", "shutter_run": 30, "opening_time": 34},
            }
        )
    )
    plat = platforms(out)
    sym = plat["cover"]["2-81"]
    assert sym["slat_time"] == 3.0 and sym["opening_time"] == 30.0 and sym["closing_time"] == 30.0
    asym = plat["cover"]["2-82"]
    assert asym["opening_time"] == 32.0 and asym["closing_time"] == 28.0
    assert isinstance(asym["opening_time"], float)
    up_only = plat["cover"]["2-83"]
    assert up_only["opening_time"] == 34.0 and up_only["closing_time"] == 30.0


def test_cover_slat_time_must_leave_curtain_travel():
    """``slat_time`` must be smaller than the shortest run minus one second."""
    # 3 < 30 - 1: fine.  27 is not smaller than 28 - 1 = 27.
    check(gw(cover={"c": {"where": "81", "name": "C", "shutter_run": 30, "slat_time": 3}}))
    with pytest.raises(Invalid, match="slat_time"):
        check(gw(cover={"c": {"where": "81", "name": "C", "shutter_run": 28, "slat_time": 27}}))
    with pytest.raises(Invalid, match="slat_time"):
        check(gw(cover={"c": {"where": "81", "name": "C", "shutter_run": 30, "slat_time": 40}}))
    # The check looks at the *shortest* of the two directions.
    with pytest.raises(Invalid, match="closing_time=10"):
        check(
            gw(
                cover={
                    "c": {
                        "where": "81",
                        "name": "C",
                        "shutter_run": 30,
                        "opening_time": 30,
                        "closing_time": 10,
                        "slat_time": 12,
                    }
                }
            )
        )
    with pytest.raises(Invalid, match="at least 0"):
        check(gw(cover={"c": {"where": "81", "name": "C", "slat_time": -1}}))
    with pytest.raises(Invalid, match="at least 1"):
        check(gw(cover={"c": {"where": "81", "name": "C", "opening_time": 0}}))


def test_cover_slat_time_error_names_the_device():
    with pytest.raises(Invalid) as err:
        check(gw(cover={"shutter": {"where": "81", "name": "T", "shutter_run": 5, "slat_time": 4}}))
    assert err.value.path == ["gateway", "cover", "shutter", "slat_time"]



# --------------------------------------------------------------------------------------
# device_class alias and per-platform defaults (val-02, val-08, val-12)
# --------------------------------------------------------------------------------------
COMMON_KEYS = {"who", "where", "name", "entity_name", "icon", "icon_on", "manufacturer", "model", "entities"}


def test_defaults_per_platform():
    out = check(
        gw(
            light={"l": {"where": "11", "name": "L"}},
            switch={"s": {"where": "12", "name": "S"}},
            cover={"c": {"where": "81", "name": "C"}},
            binary_sensor={"b": {"where": "301", "name": "B"}},
            sensor={"e": {"where": "51", "name": "E", "class": "power"}},
            climate={"z": {"zone": "3"}},
        )
    )
    plat = platforms(out)
    light = plat["light"]["1-11"]
    assert COMMON_KEYS <= set(light)
    assert light["dimmable"] is False and light["lock_buttons"] is False
    assert light["manufacturer"] == "BTicino S.p.A." and light["model"] is None
    assert light["entities"] == {} and light["icon"] is None and light["entity_name"] is None

    switch = plat["switch"]["1-12"]
    assert COMMON_KEYS <= set(switch)
    assert switch["class"] == validate.SwitchDeviceClass.SWITCH

    cover = plat["cover"]["2-81"]
    assert COMMON_KEYS <= set(cover)
    assert cover["advanced"] is False and cover["inverted"] is False
    assert cover["shutter_run"] == 20.0 and isinstance(cover["shutter_run"], float)
    assert cover["class"] == validate.CoverDeviceClass.SHUTTER
    # 0.4.0 two-phase travel: off by default, both directions follow ``shutter_run``.
    assert cover["slat_time"] == 0.0 and isinstance(cover["slat_time"], float)
    assert cover["opening_time"] == 20.0 and cover["closing_time"] == 20.0

    binary = plat["binary_sensor"]["25-301"]
    assert COMMON_KEYS <= set(binary)
    assert binary["class"] == validate.BinarySensorDeviceClass.OPENING and binary["inverted"] is False

    sensor = plat["sensor"]["18-51"]
    assert COMMON_KEYS <= set(sensor)
    for key in ("min_delta_w", "min_interval_sec", "suppress_log_interval_sec", "keepalive_minutes"):
        assert key in sensor

    climate = plat["climate"]["4-3"]
    assert climate["zone"] == "3" and climate["name"] == "Zone 3"
    for key in ("heat", "cool", "fan", "standalone", "central", "entities", "manufacturer", "model", "icon", "icon_on", "entity_name"):
        assert key in climate

    # Each device dict has its own entities mapping.
    assert light["entities"] is not switch["entities"]


def test_binary_sensor_class_default_by_who():
    out = check(
        gw(
            binary_sensor={
                "a": {"where": "302", "name": "A"},
                "b": {"where": "303", "name": "B", "who": 1},
                "c": {"where": "304", "name": "C", "who": "9"},
                "d": {"where": "305", "name": "D", "device_class": "window"},
                "e": {"where": "306", "name": "E", "class": "motion"},
            }
        )
    )
    classes = {key: dev["class"] for key, dev in platforms(out)["binary_sensor"].items()}
    assert classes == {
        "25-302": validate.BinarySensorDeviceClass.OPENING,
        "1-303": validate.BinarySensorDeviceClass.MOTION,
        "9-304": None,
        "25-305": validate.BinarySensorDeviceClass.WINDOW,
        "25-306": validate.BinarySensorDeviceClass.MOTION,
    }
    assert all("device_class" not in dev for dev in platforms(out)["binary_sensor"].values())


@pytest.mark.parametrize(
    ("platform", "device", "expected"),
    [
        ("switch", {"where": "12", "name": "S", "device_class": "outlet"}, "outlet"),
        ("cover", {"where": "81", "name": "C", "device_class": "blind"}, "blind"),
        ("sensor", {"where": "51", "name": "E", "device_class": "energy"}, "energy"),
        ("binary_sensor", {"where": "301", "name": "B", "device_class": "door"}, "door"),
    ],
)
def test_device_class_alias_everywhere(platform, device, expected):
    out = check(gw(**{platform: {"x": device}}))
    (dev,) = platforms(out)[platform].values()
    assert dev["class"] == expected
    assert "device_class" not in dev


def test_class_and_device_class_conflict():
    with pytest.raises(Invalid, match="both class"):
        check(gw(cover={"c": {"where": "81", "name": "C", "class": "shutter", "device_class": "blind"}}))
    out = check(gw(cover={"c": {"where": "81", "name": "C", "class": "shutter", "device_class": "shutter"}}))
    assert platforms(out)["cover"]["2-81"]["class"] == validate.CoverDeviceClass.SHUTTER


def test_sensor_requires_class_and_matching_who():
    with pytest.raises(Invalid, match="missing the required sensor class") as err:
        check(gw(sensor={"s": {"where": "51", "name": "S"}}))
    assert err.value.path == ["gateway", "sensor", "s", "class"]
    with pytest.raises(Invalid, match="requires who 18"):
        check(gw(sensor={"s": {"where": "51", "name": "S", "class": "power", "who": "4"}}))
    out = check(gw(sensor={"t": {"where": "1", "name": "T", "class": "temperature"}, "i": {"where": "12", "name": "I", "class": "illuminance"}}))
    assert set(platforms(out)["sensor"]) == {"4-1", "1-12"}
    assert platforms(out)["sensor"]["4-1"]["entities"] == {}


# --------------------------------------------------------------------------------------
# Bus interface normalisation (0.3.1, forks review 5.2 - carferrer)
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("given", [3, "3", "03"])
def test_bus_interface_is_stored_unpadded(given):
    """`interface` is accepted as an int or as 1-2 digits and stored as the bus writes
    it (`3`), so `_full_where` matches what OWNd 0.7.49 parses out of the frame."""
    out = check(gw(light={"a": {"where": "11", "interface": given, "name": "A"}}))
    device = platforms(out)["light"]["1-11#4#03"]
    assert device["interface"] == "3"


def test_bus_interface_device_key_stays_zero_padded():
    """The device key is the tail of every unique_id: unpadding it would rename the
    entities of every user behind an F422, so the padding survives here only."""
    out = check(gw(light={"a": {"where": "0115", "interface": 1, "name": "A"}}))
    assert set(platforms(out)["light"]) == {"1-0115#4#01"}
    out = check(gw(switch={"s": {"where": "23", "interface": "15", "name": "S"}}))
    assert set(platforms(out)["switch"]) == {"1-23#4#15"}
    out = check(gw(switch={"s": {"where": "23", "interface": 0, "name": "S"}}))
    assert set(platforms(out)["switch"]) == {"1-23#4#00"}


@pytest.mark.parametrize("given", [16, "16", "003", -1, "abc", "", True, 1.0])
def test_invalid_bus_interface_is_rejected(given):
    with pytest.raises(Invalid, match="Bus Interface"):
        check(gw(light={"a": {"where": "11", "interface": given, "name": "A"}}))


def test_normalise_bus_interface_helper():
    from custom_components.myhome import const

    assert const.normalise_bus_interface(3) == "3"
    assert const.normalise_bus_interface("03") == "3"
    assert const.normalise_bus_interface("15") == "15"
    assert const.normalise_bus_interface(0) == "0"
    assert const.normalise_bus_interface(None) is None
    assert const.normalise_bus_interface(True) is None
    assert const.normalise_bus_interface("16") is None
    assert const.bus_full_where("11", "03") == "11#4#3"
    assert const.bus_full_where("11", 3) == "11#4#3"
    assert const.bus_full_where("11", None) == "11"


# --------------------------------------------------------------------------------------
# Duplicate detection (val-01)
# --------------------------------------------------------------------------------------
def test_duplicate_within_platform():
    with pytest.raises(Invalid) as err:
        check(gw(light={"a": {"where": "12", "name": "A"}, "b": {"where": "12", "name": "B"}}))
    assert "'a'" in str(err.value) and "'b'" in str(err.value) and "'12'" in str(err.value)


def test_duplicate_across_platforms():
    with pytest.raises(Invalid, match="switch 's' collides with light 'l'"):
        check(gw(light={"l": {"where": "12", "name": "L"}}, switch={"s": {"where": "12", "name": "S"}}))


def test_duplicate_after_normalisation():
    # '#1' and '#01' are the same group; '01' interface vs 1 interface are the same key.
    with pytest.raises(Invalid, match="Duplicate"):
        check(gw(light={"a": {"where": "#1", "name": "A"}, "b": {"where": "#01", "name": "B"}}))
    with pytest.raises(Invalid, match="1-0115#4#01"):
        check(gw(light={"a": {"where": "0115", "interface": 1, "name": "A"}, "b": {"where": "0115", "interface": "01", "name": "B"}}))


def test_climate_zone_and_temperature_sensor_may_share_zone():
    out = check(gw(climate={"z": {"zone": 1}}, sensor={"t": {"where": "1", "name": "T", "class": "temperature"}}))
    assert "4-1" in platforms(out)["climate"] and "4-1" in platforms(out)["sensor"]
    with pytest.raises(Invalid, match="climate 'z2' collides with climate 'z1'"):
        check(gw(climate={"z1": {"zone": 1}, "z2": {"zone": "1"}}, sensor={"t": {"where": "1", "name": "T", "class": "temperature"}}))


# --------------------------------------------------------------------------------------
# Lock/Unlock buttons (val-10)
# --------------------------------------------------------------------------------------
def test_lock_buttons_opt_in_and_point_to_point_only():
    out = check(
        gw(
            light={
                "p2p": {"where": "12", "name": "P", "lock_buttons": True},
                "p2p4": {"where": "0115", "name": "P4", "lock_buttons": True, "interface": "01"},
                "area": {"where": "1", "name": "Area", "lock_buttons": True},
                "area00": {"where": "00", "name": "Area00", "lock_buttons": True},
                "general": {"where": "0", "name": "Gen", "lock_buttons": True},
                "group": {"where": "#3", "name": "Grp", "lock_buttons": True},
                "no": {"where": "13", "name": "No"},
            },
            cover={"c": {"where": "81", "name": "C", "lock_buttons": True}},
            switch={"s": {"where": "14", "name": "S", "lock_buttons": "yes"}},
        )
    )
    plat = platforms(out)
    assert set(plat["button"]) == {"1-12", "1-0115#4#01", "2-81", "1-14"}
    for key, button in plat["button"].items():
        source = button["source_platform"]
        assert source in ("light", "switch", "cover")
        original = plat[source][key]
        assert button is not original
        assert button["entities"] == {} and button["entities"] is not original["entities"]
        assert {k: v for k, v in button.items() if k not in ("entities", "source_platform")} == {
            k: v for k, v in original.items() if k != "entities"
        }
    assert "source_platform" not in plat["light"]["1-12"]


def test_no_button_platform_without_lock_buttons():
    out = check(gw(light={"a": {"where": "12", "name": "A"}}))
    assert "button" not in platforms(out)


# --------------------------------------------------------------------------------------
# CEN / CEN+ scenario controls (0.4.0)
# --------------------------------------------------------------------------------------
def _events(out: dict) -> dict:
    """The ``event`` platform section produced by a ``scenario_control:`` block."""
    return platforms(out)["event"]


def test_scenario_control_defaults_cen_plus():
    """cen_plus is the default protocol; the address becomes who/where/object."""
    out = check(gw(scenario_control={"keypad": {"object": 25, "name": "Keypad"}}))
    devices = _events(out)
    assert list(devices) == ["cenplus-25"]
    device = devices["cenplus-25"]
    assert device["protocol"] == "cen_plus"
    assert device["object"] == 25
    assert device["where"] == "25"
    assert device["who"] == "25"
    assert device["buttons"] == [1, 2, 3, 4]
    assert device["name"] == "Keypad"
    assert device["entity_name"] is None
    assert device["manufacturer"] == "BTicino S.p.A."
    assert device["model"] == "CEN+ scenario control"
    assert device["entities"] == {}


def test_scenario_control_cen_uses_where():
    out = check(
        gw(
            scenario_control={
                "ingresso": {
                    "protocol": "cen",
                    "where": "051",
                    "name": "Ingresso",
                    "buttons": [0, 1, 2],
                    "model": "HD4652",
                    "entity_name": "Keypad",
                }
            }
        )
    )
    # The bus writes the address unpadded, so '051' keys as cen-51.
    device = _events(out)["cen-51"]
    assert device["protocol"] == "cen"
    assert device["who"] == "15"
    assert device["object"] == 51
    assert device["where"] == "51"
    assert device["buttons"] == [0, 1, 2]
    assert device["model"] == "HD4652"
    assert device["entity_name"] == "Keypad"


@pytest.mark.parametrize(
    ("device", "path_tail"),
    [
        ({"name": "X"}, "object"),                                   # cen_plus without object
        ({"protocol": "cen", "name": "X"}, "where"),                 # cen without where
        ({"protocol": "cen", "object": 5, "name": "X"}, "object"),   # cen addressed by object
        ({"object": 5, "where": "51", "name": "X"}, "where"),        # cen_plus addressed by where
    ],
)
def test_scenario_control_address_must_match_protocol(device, path_tail):
    with pytest.raises(Invalid) as err:
        check(gw(scenario_control={"kp": device}))
    assert str(err.value.path[-1]) == path_tail


@pytest.mark.parametrize("object_id", [0, 2048, -1])
def test_scenario_control_object_out_of_range(object_id):
    with pytest.raises(Invalid):
        check(gw(scenario_control={"kp": {"object": object_id, "name": "X"}}))


@pytest.mark.parametrize("protocol", ["cenplus", "CEN", "", 1])
def test_scenario_control_unknown_protocol(protocol):
    with pytest.raises(Invalid):
        check(gw(scenario_control={"kp": {"protocol": protocol, "object": 3, "name": "X"}}))


@pytest.mark.parametrize(
    ("protocol", "extra", "buttons"),
    [
        ("cen_plus", {"object": 3}, [0]),    # CEN+ buttons are 1-32
        ("cen_plus", {"object": 3}, [33]),
        ("cen", {"where": "51"}, [32]),      # CEN buttons are 0-31
        ("cen", {"where": "51"}, [-1]),
    ],
)
def test_scenario_control_button_range_per_protocol(protocol, extra, buttons):
    with pytest.raises(Invalid) as err:
        check(gw(scenario_control={"kp": {"protocol": protocol, "name": "X", "buttons": buttons, **extra}}))
    assert "buttons" in str(err.value)


@pytest.mark.parametrize("buttons", [[1, 1], [], ["a"], [None], [True]])
def test_scenario_control_invalid_button_list(buttons):
    with pytest.raises(Invalid):
        check(gw(scenario_control={"kp": {"object": 3, "name": "X", "buttons": buttons}}))


def test_scenario_control_buttons_accept_strings_and_scalar():
    out = check(gw(scenario_control={"kp": {"object": 3, "name": "X", "buttons": ["1", 2]}}))
    assert _events(out)["cenplus-3"]["buttons"] == [1, 2]
    out = check(gw(scenario_control={"kp": {"object": 3, "name": "X", "buttons": 7}}))
    assert _events(out)["cenplus-3"]["buttons"] == [7]


def test_scenario_control_name_is_required():
    with pytest.raises(Invalid):
        check(gw(scenario_control={"kp": {"object": 3}}))


def test_scenario_control_duplicate_address():
    with pytest.raises(Invalid) as err:
        check(
            gw(
                scenario_control={
                    "kp": {"object": 25, "name": "A"},
                    "kp_again": {"object": 25, "name": "B"},
                }
            )
        )
    assert "cenplus-25" in str(err.value)


def test_scenario_control_cen_and_cen_plus_same_number_coexist():
    """cen-5 and cenplus-5 are different devices: no collision."""
    out = check(
        gw(
            scenario_control={
                "plus": {"object": 5, "name": "Plus"},
                "classic": {"protocol": "cen", "where": "5", "name": "Classic"},
            }
        )
    )
    assert set(_events(out)) == {"cenplus-5", "cen-5"}


def test_scenario_control_unknown_key_warns_with_the_yaml_section_name(caplog):
    validate.reset_unknown_key_warnings()
    with caplog.at_level(logging.WARNING):
        out = check(gw(scenario_control={"kp": {"object": 3, "name": "X", "buttonz": [1]}}))
    assert "buttonz" in caplog.text
    assert "scenario_control.kp" in caplog.text
    assert "did you mean 'buttons'?" in caplog.text
    # Unknown keys are never fatal and are kept.
    assert _events(out)["cenplus-3"]["buttonz"] == [1]


def test_no_event_platform_without_scenario_controls():
    out = check(gw(light={"a": {"where": "11", "name": "A"}}))
    assert "event" not in platforms(out)


def test_empty_scenario_control_section_is_accepted():
    out = check(gw(scenario_control=None))
    assert platforms(out)["event"] == {}


# --------------------------------------------------------------------------------------
# Sensor defaults merge and keep-alive (val-13, Contract E)
# --------------------------------------------------------------------------------------
def test_sensor_defaults_merge_and_overrides():
    out = check(
        gw(
            energy={"min_delta_w": 7, "info_log_interval_sec": 10, "keepalive_minutes": 60},
            sensor_defaults={"refresh_period": 3, "keepalive_minutes": 0},
            sensor={
                "a": {"where": "51", "name": "A", "class": "power", "energy_min_delta_w": 2},
                "b": {"where": "52", "name": "B", "class": "power", "keepalive_minutes": 30, "min_interval_sec": 9},
            },
        )
    )
    entry = out[MAC_NORM]
    assert "energy" not in entry
    assert entry["sensor_defaults"] == {
        "min_delta_w": 7,
        "min_interval_sec": 3.0,
        "suppress_log_interval_sec": 60.0,
        "keepalive_minutes": 0,  # sensor_defaults wins over energy
        "info_log_interval_sec": 10.0,
    }
    a = platforms(out)["sensor"]["18-51"]
    assert a["min_delta_w"] == 2 and a["min_interval_sec"] == 3.0 and a["keepalive_minutes"] == 0
    assert a["info_log_interval_sec"] == 10.0
    b = platforms(out)["sensor"]["18-52"]
    assert b["keepalive_minutes"] == 30 and b["min_interval_sec"] == 9.0 and b["min_delta_w"] == 7


def test_builtin_sensor_defaults():
    out = check(gw(sensor={"a": {"where": "51", "name": "A", "class": "power"}}))
    a = platforms(out)["sensor"]["18-51"]
    assert (a["min_delta_w"], a["min_interval_sec"], a["suppress_log_interval_sec"], a["keepalive_minutes"]) == (5, 1.0, 60.0, 125)


# --------------------------------------------------------------------------------------
# Unknown keys (val-07)
# --------------------------------------------------------------------------------------
def test_unknown_keys_warn_but_never_raise(caplog):
    validate.reset_unknown_key_warnings()
    with caplog.at_level(logging.WARNING, logger="custom_components.myhome"):
        out = check(
            gw(
                bogus_root=1,
                sensor_defaults={"bogus": 1},
                light={"a": {"where": "15", "name": "A", "dimable": True, "icon-on": "x"}},
            )
        )
    messages = [rec.getMessage() for rec in caplog.records if rec.levelno == logging.WARNING]
    assert any("'dimable'" in m and "did you mean 'dimmable'" in m for m in messages)
    assert any("'icon-on'" in m and "did you mean 'icon_on'" in m for m in messages)
    assert any("'bogus_root'" in m for m in messages)
    assert any("'bogus'" in m and "sensor_defaults" in m for m in messages)
    # Unknown keys are kept (backward compatible) and the light is created non-dimmable.
    light = platforms(out)["light"]["1-15"]
    assert light["dimable"] is True and light["dimmable"] is False

    # Reported once only.
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="custom_components.myhome"):
        check(gw(light={"a": {"where": "15", "name": "A", "dimable": True}}))
    assert not [rec for rec in caplog.records if "dimable" in rec.getMessage()]


# --------------------------------------------------------------------------------------
# Climate (val-03)
# --------------------------------------------------------------------------------------
def test_climate_where_is_treated_as_zone():
    out = check(
        gw(
            climate={
                "discovered": {"where": "4"},
                "central_zone": {"central": True, "zone": "2", "name": "X"},
                "cu": {},
                "named": {"zone": 7, "name": "Studio", "cool": True, "fan": "on"},
            }
        )
    )
    climate = platforms(out)["climate"]
    assert set(climate) == {"4-4", "4-2", "4-#0", "4-7"}
    assert climate["4-4"]["zone"] == "4" and climate["4-4"]["name"] == "Zone 4" and "where" not in climate["4-4"]
    assert climate["4-2"]["zone"] == "#0#2" and climate["4-2"]["name"] == "X"
    assert climate["4-#0"]["zone"] == "#0" and climate["4-#0"]["name"] == "Central unit"
    assert climate["4-7"]["cool"] is True and climate["4-7"]["fan"] is True and climate["4-7"]["heat"] is True
    with pytest.raises(Invalid, match="both zone"):
        check(gw(climate={"z": {"zone": "1", "where": "2"}}))
    with pytest.raises(Invalid, match="Invalid zone"):
        check(gw(climate={"z": {"zone": "abc"}}))


# --------------------------------------------------------------------------------------
# WHERE handling (val-11)
# --------------------------------------------------------------------------------------
def test_unquoted_where_ints():
    assert list(platforms(check(gw(light={"a": {"where": 15, "name": "A"}})))["light"]) == ["1-15"]
    assert list(platforms(check(gw(light={"a": {"where": 0, "name": "A"}})))["light"]) == ["1-0"]
    assert list(platforms(check(gw(light={"a": {"where": 10, "name": "A"}})))["light"]) == ["1-10"]
    assert list(platforms(check(gw(sensor={"a": {"where": 51, "name": "A", "class": "power"}})))["sensor"]) == ["18-51"]
    with pytest.raises(Invalid, match="quote it"):
        check(gw(light={"a": {"where": 1, "name": "A"}}))  # YAML `where: 01`
    with pytest.raises(Invalid, match="quote it"):
        check(gw(light={"a": {"where": 8, "name": "A"}}))  # YAML `where: 010` (octal)
    with pytest.raises(Invalid, match="WHERE"):
        check(gw(light={"a": {"where": None, "name": "A"}}))


@pytest.mark.parametrize("where", ["abc", "123", "1116", "#0", "#256", "", " "])
def test_invalid_actuator_where(where):
    with pytest.raises(Invalid):
        check(gw(light={"a": {"where": where, "name": "A"}}))


@pytest.mark.parametrize(("where", "key"), [("0", "1-0"), ("00", "1-00"), ("9", "1-9"), ("#01", "1-#1"), ("0915", "1-0915"), ("1015", "1-1015")])
def test_valid_actuator_where(where, key):
    assert list(platforms(check(gw(light={"a": {"where": where, "name": "A"}})))["light"]) == [key]


def test_who_accepts_unquoted_int_and_rejects_others():
    out = check(gw(cover={"c": {"where": "81", "name": "C", "who": 2}}))
    assert platforms(out)["cover"]["2-81"]["who"] == "2"
    with pytest.raises(Invalid):
        check(gw(cover={"c": {"where": "81", "name": "C", "who": "1"}}))


def test_empty_sections_are_accepted():
    out = check({"gateway": {"mac": MAC, "light": None, "sensor_defaults": None}})
    assert platforms(out)["light"] == {}
    out = check({"gateway": {"mac": MAC}})
    assert platforms(out) == {}


def test_missing_required_fields():
    with pytest.raises(Invalid):
        check(gw(light={"a": {"name": "A"}}))
    with pytest.raises(Invalid):
        check(gw(light={"a": {"where": "15"}}))
    with pytest.raises(Invalid):
        check(gw(light={"a": None}))


# --------------------------------------------------------------------------------------
# Engine agreement: probatio shim (what HA 2026.9 uses) vs real voluptuous
# --------------------------------------------------------------------------------------
_ENGINE_SCRIPT = textwrap.dedent(
    '''
    import copy, importlib, json, os, sys, types
    engine, root = sys.argv[1], sys.argv[2]
    sys.path.insert(0, root)
    import homeassistant, homeassistant.helpers.device_registry, homeassistant.const
    for comp in ("light", "switch", "button", "cover", "binary_sensor", "sensor", "climate"):
        importlib.import_module(f"homeassistant.components.{comp}")
    if engine == "voluptuous":
        for k in list(sys.modules):
            if k == "voluptuous" or k.startswith("voluptuous."):
                del sys.modules[k]
    import voluptuous as vol
    assert ("probatio" in vol.__file__) == (engine == "probatio"), vol.__file__
    parent = types.ModuleType("custom_components"); parent.__path__ = [os.path.join(root, "custom_components")]
    pkg = types.ModuleType("custom_components.myhome"); pkg.__path__ = [os.path.join(root, "custom_components", "myhome")]
    sys.modules["custom_components"] = parent; sys.modules["custom_components.myhome"] = pkg
    importlib.import_module("custom_components.myhome.const")
    validate = importlib.import_module("custom_components.myhome.validate")
    assert validate.Schema is vol.Schema
    cases = json.load(sys.stdin)
    results = []
    for case in cases:
        try:
            out = validate.config_schema(copy.deepcopy(case))
            results.append({"ok": json.loads(json.dumps(out, default=str, sort_keys=True))})
        except vol.Invalid as err:
            results.append({"invalid": [str(p) for p in err.path]})
    json.dump(results, sys.stdout, sort_keys=True)
    '''
)

_ENGINE_CASES = [
    {"gateway": {"mac": MAC, "light": {"a": {"where": "15", "name": "A", "lock_buttons": True}, "b": {"where": "#01", "name": "B"}}}},
    {MAC: {"cover": {"c": {"where": 81, "name": "C", "device_class": "blind", "shutter_run": 25}}}},
    {"gateway": {"mac": MAC, "energy": {"min_delta_w": 7}, "sensor_defaults": {"refresh_period": 3}, "sensor": {"s": {"where": "51", "name": "S", "device_class": "power", "min_delta_w": 1}}}},
    {"gateway": {"mac": MAC, "binary_sensor": {"a": {"where": "302", "name": "A"}, "b": {"where": "303", "name": "B", "who": 1}}}},
    {"gateway": {"mac": MAC, "climate": {"z": {"where": "4"}, "c": {"central": True, "zone": 2, "name": "X"}, "cu": {}}}},
    {"gateway": {"mac": MAC, "light": {"a": {"where": "12", "name": "A"}}, "switch": {"b": {"where": "12", "name": "B"}}}},
    {"gateway": {"mac": MAC, "light": {"a": {"where": 1, "name": "A"}}}},
    {"gateway": {"mac": 350}},
    {"gateway": {"mac": MAC, "energy": {"min_delta_w": -5}}},
    {"gateway": {"mac": MAC, "cover": {"c": {"where": "81", "name": "C", "class": "shutter", "device_class": "blind"}}}},
    {"gateway": {"mac": MAC}, MAC: {}},
    {"gateway": {"mac": MAC, "scenario_control": {"kp": {"object": 25, "name": "K"}, "cen": {"protocol": "cen", "where": "51", "name": "C", "buttons": [0, 1]}}}},
    {"gateway": {"mac": MAC, "scenario_control": {"kp": {"protocol": "cen", "object": 25, "name": "K"}}}},
]


def _run_engine(engine: str) -> list:
    proc = subprocess.run(
        [sys.executable, "-c", _ENGINE_SCRIPT, engine, str(REPO_ROOT)],
        input=json.dumps(_ENGINE_CASES),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_probatio_and_voluptuous_agree():
    probatio_results = _run_engine("probatio")
    voluptuous_results = _run_engine("voluptuous")
    assert len(probatio_results) == len(_ENGINE_CASES)
    assert probatio_results == voluptuous_results
    # Sanity: the case list covers both outcomes.
    assert any("ok" in r for r in probatio_results) and any("invalid" in r for r in probatio_results)
