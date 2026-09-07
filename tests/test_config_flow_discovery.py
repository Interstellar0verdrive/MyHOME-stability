"""Tests for the discovery -> YAML suggestion path (``config_flow_discovery.py``).

Two things make this module worth pinning hard:

* the dict ``generate_suggested_config`` emits is a *wire contract* with
  ``validate.py``. Whatever lands in ``myhome_discovered.yaml`` is copy-pasted by
  the user into their ``myhome.yaml``, so a wrong or missing key is a suggestion
  that fails validation on the user's next restart. The expected dicts below
  therefore spell the YAML keys as literals (``"who"``, ``"class"``, ...) rather
  than through the ``CONF_*`` constants: these strings are user-visible YAML, and
  a test that imports the constant would happily follow it if it were renamed.
* ``_merge_and_write`` is the only code in the integration that writes a file the
  user may have edited. Everything about it is a data-loss question: it must never
  clobber a file it could not parse, and it must never leave a half-written
  temporary file behind in the user's config directory.

Nothing here touches the network, the bus or a real gateway; ``_merge_and_write``
runs against ``tmp_path`` and the addresses are the fictional ones from
``helpers_core``.
"""

from __future__ import annotations

import glob
import logging
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.myhome.config_flow_discovery import (
    _SUGGESTABLE,
    MyHOMEDiscoverySuggestions,
    _merge_and_write,
    generate_suggested_config,
    is_device_configured,
)
from custom_components.myhome.const import (
    CONF_FILE_PATH,
    CONF_PLATFORMS,
    DEVICE_TYPE_BUS_ALARM_SYSTEM,
    DEVICE_TYPE_BUS_AUTOMATION,
    DEVICE_TYPE_BUS_AUX,
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_DIMMER,
    DEVICE_TYPE_BUS_DRY_CONTACT_IR,
    DEVICE_TYPE_BUS_ENERGY_METER,
    DEVICE_TYPE_BUS_LIGHT_GROUP,
    DEVICE_TYPE_BUS_ON_OFF_SWITCH,
    DEVICE_TYPE_BUS_THERMO_CU,
    DEVICE_TYPE_BUS_THERMO_SENSOR,
    DEVICE_TYPE_BUS_THERMO_ZONE,
    DISCOVERED_CONFIG_FILE,
    DOMAIN,
)
from custom_components.myhome.validate import config_schema

from .helpers_core import MAC, MAC2, make_entry

# device_type -> (WHERE as discovered, name, expected platform, expected FULL device dict).
# One entry per _SUGGESTABLE key; ``test_suggestion_table_covers_every_suggestable_type``
# fails if a new device type is added to the module without landing here too.
_SUGGESTION_CASES: dict[str, tuple[str, str, str, dict[str, Any]]] = {
    DEVICE_TYPE_BUS_ON_OFF_SWITCH: (
        "11",
        "Hallway Lamp",
        "light",
        {"who": "1", "where": "11", "name": "Hallway Lamp", "dimmable": False},
    ),
    DEVICE_TYPE_BUS_DIMMER: (
        "12",
        "Dining Dimmer",
        "light",
        {"who": "1", "where": "12", "name": "Dining Dimmer", "dimmable": True},
    ),
    DEVICE_TYPE_BUS_AUTOMATION: (
        "54",
        "Study Blind",
        "cover",
        {"who": "2", "where": "54", "name": "Study Blind", "shutter_run": 20},
    ),
    DEVICE_TYPE_BUS_ENERGY_METER: (
        "5#1",
        "Main Meter",
        "sensor",
        {"who": "18", "where": "5#1", "name": "Main Meter", "class": "power"},
    ),
    DEVICE_TYPE_BUS_THERMO_ZONE: (
        "3",
        "Bedroom Zone",
        "climate",
        {"who": "4", "zone": "3", "name": "Bedroom Zone"},
    ),
    # The central unit.  ``discovery.py`` reports its WHERE as ``#0`` -- the bare
    # ``0`` OWNd puts on the frame is refused by ``validate.Zone``, so a suggestion
    # built from it made the whole myhome.yaml unloadable.
    DEVICE_TYPE_BUS_THERMO_CU: (
        "#0",
        "Central Unit",
        "climate",
        {"who": "4", "zone": "#0", "name": "Central Unit"},
    ),
    DEVICE_TYPE_BUS_THERMO_SENSOR: (
        "3",
        "Bedroom Probe",
        "sensor",
        {"who": "4", "where": "3", "name": "Bedroom Probe", "class": "temperature"},
    ),
    DEVICE_TYPE_BUS_DRY_CONTACT_IR: (
        "31",
        "Garage Sensor",
        "binary_sensor",
        {"who": "25", "where": "31", "name": "Garage Sensor", "class": "motion"},
    ),
    # WHO 9 only validates under ``binary_sensor``; ``switch`` is WHO 1.
    DEVICE_TYPE_BUS_AUX: (
        "9",
        "Aux Line",
        "binary_sensor",
        {"who": "9", "where": "9", "name": "Aux Line"},
    ),
}

# Discovered device types that have no entity representation at all.
_NOT_SUGGESTABLE = [
    DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL,
    DEVICE_TYPE_BUS_ALARM_SYSTEM,
    DEVICE_TYPE_BUS_LIGHT_GROUP,
]


def _device_info(device_type: str, where: Any, name: str, interface: str | None = None) -> dict[str, Any]:
    """The subset of a discovered-device payload the suggestion code reads."""
    return {
        "device_type": device_type,
        "where": where,
        "interface": interface,
        "name": name,
        "unique_id": f"{MAC}-{where}",
    }


# --------------------------------------------------------------------------------------
# generate_suggested_config
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("device_type", "where", "name", "platform", "expected"),
    [(dt, *case) for dt, case in _SUGGESTION_CASES.items()],
    ids=list(_SUGGESTION_CASES),
)
def test_generate_suggested_config_emits_the_full_yaml_contract(
    device_type: str, where: str, name: str, platform: str, expected: dict[str, Any]
) -> None:
    """Pins the COMPLETE suggested device dict, and the platform it is filed under,
    for every discoverable device type.

    Why it matters in production: this dict is written verbatim into
    ``myhome_discovered.yaml`` and the user pastes it into ``myhome.yaml``. The
    schema in ``validate.py`` is strict, so any drift here produces suggestions
    that refuse to load: a climate device keyed on ``where`` instead of ``zone``, a
    sensor without the ``class`` its WHO requires (validate.py rejects a classless
    sensor outright, and pairs ``power``<->WHO 18 / ``temperature``<->WHO 4), a
    cover without ``shutter_run`` (a required key), or a dimmer suggested as an
    on/off light so half the user's lights lose brightness.

    Mutations caught: swapping any (platform, WHO) pair in ``_SUGGESTABLE``;
    emitting ``where`` instead of ``zone`` for climate (or both); inverting the
    ``dimmable`` comparison; changing the ``shutter_run: 20`` default; wiring the
    wrong ``class`` string ("power"/"temperature"/"motion") to a device type;
    adding a stray key or dropping ``name``.
    """
    result = generate_suggested_config(_device_info(device_type, where, name))
    assert result is not None
    assert result == (platform, expected)


def test_suggestion_table_covers_every_suggestable_type() -> None:
    """Pins that the table above enumerates every entry of ``_SUGGESTABLE``.

    Why it matters in production: a new discoverable device type is exactly the
    moment a wrong platform/WHO/class combination sneaks in, and it would sail
    through a parametrised test that simply does not mention it.

    Mutation caught: adding an entry to ``_SUGGESTABLE`` (or removing one) without
    updating ``_SUGGESTION_CASES`` - the assertion fails instead of the new type
    silently going untested.
    """
    assert set(_SUGGESTION_CASES) == set(_SUGGESTABLE)


# WHEREs used by the round-trip test below instead of the ones in _SUGGESTION_CASES.
# The energy meter's ``5#1`` is a synthetic value that exists there only to exercise
# the ``#`` -> ``_`` sanitisation of the suggestion key: OWNd reports the WHERE of an
# energy frame without its interface part (``*#18*5#1*113*1234##`` -> ``where == '5'``),
# so discovery cannot produce it, and ``SENSOR_WHERE`` rightly refuses it.
_VALIDATOR_WHERE: dict[str, str] = {DEVICE_TYPE_BUS_ENERGY_METER: "51"}


@pytest.mark.parametrize("device_type", list(_SUGGESTION_CASES), ids=list(_SUGGESTION_CASES))
def test_every_suggestion_survives_the_real_validator(device_type: str) -> None:
    """Pins that every suggested block is YAML ``validate.py`` actually accepts.

    Why it matters in production: the previous test pins the dict, this one pins that
    the dict is *usable*. An auxiliary channel used to be suggested as
    ``switch: {who: '9'}``, and ``SWITCH_FIELDS`` is ``_who("1")``: pasting the
    suggestion did not create a broken switch, it made the whole ``myhome.yaml``
    unloadable, so every other device of that gateway disappeared too.

    Mutation caught: pointing a suggestion at a platform whose schema refuses its
    WHO, dropping a required key (a cover without ``shutter_run``), or emitting a
    class the platform does not allow.
    """
    where = _VALIDATOR_WHERE.get(device_type, _SUGGESTION_CASES[device_type][0])
    platform, cfg = generate_suggested_config(_device_info(device_type, where, "Discovered Device"))
    result = config_schema({MAC: {platform: {f"discovered_{where}": dict(cfg)}}})
    assert list(result[MAC.lower()][CONF_PLATFORMS]) == [platform]


@pytest.mark.parametrize("device_type", _NOT_SUGGESTABLE)
def test_generate_suggested_config_returns_none_for_devices_it_cannot_write(device_type: str) -> None:
    """Pins that a device type the writer cannot express yields no suggestion.

    "Not suggested" is not the same as "not supported": since 0.4.0 a CEN/CEN+
    scenario control *does* have an entity representation (the ``event`` platform),
    but it is declared under ``scenario_control:`` rather than under a platform
    section, which this writer cannot emit. The alarm system and light groups have no
    standalone YAML device form at all. (The thermo central unit used to be in this
    list; it *is* suggestable -- as ``climate: {zone: '#0'}`` -- and is covered by
    ``_SUGGESTION_CASES`` instead.)

    Why it matters in production: a suggestion for one of them would be an entry the
    user pastes in and that then fails validation, or worse creates a duplicate of a
    device configured elsewhere.

    Mutation caught: adding any of these types to ``_SUGGESTABLE``, or replacing
    the ``not in`` guard with a fallback that invents a platform.
    """
    assert generate_suggested_config(_device_info(device_type, "11", "Nothing To Suggest")) is None


def test_a_device_behind_a_bus_interface_is_suggested_with_its_interface() -> None:
    """Pins the ``interface:`` key of the suggested block, and that it validates.

    Why it matters in production: ``where: '11'`` and ``where: '11', interface: '3'``
    are two different actuators. Without the key the pasted block commands the
    main-bus device (``light.turn_on`` sends ``*1*1*11##`` instead of
    ``*1*1*11#4#3##``) and never receives an update, because the gateway dispatches
    the riser's frames by ``1-11#4#03``. The value is written unpadded, which is the
    form ``validate.BusInterface`` stores and every ``_full_where`` the platforms
    build is made of.

    Mutations caught: dropping the ``interface`` key from the suggestion; writing it
    padded (``'03'`` would be normalised by the schema but is not what the bus
    sends); or emitting it on a WHO whose frames never carry one, which
    ``validate._reject_unusable_interface`` refuses outright.
    """
    platform, cfg = generate_suggested_config(
        _device_info(DEVICE_TYPE_BUS_ON_OFF_SWITCH, "11", "Riser Lamp", interface="3")
    )
    assert (platform, cfg) == (
        "light",
        {"who": "1", "where": "11", "interface": "3", "name": "Riser Lamp", "dimmable": False},
    )

    result = config_schema({MAC: {platform: {"discovered_1_11_4_03": dict(cfg)}}})
    assert list(result[MAC.lower()][CONF_PLATFORMS]["light"]) == ["1-11#4#03"]


def test_an_interface_is_never_suggested_for_a_who_that_cannot_carry_one() -> None:
    """Pins the ``INTERFACE_CAPABLE_WHO`` guard on the way *out* of discovery.

    Why it matters in production: only WHO 1, 2 and 15 frames carry the ``#4#N``
    WHERE parameter, and ``validate.py`` rejects the whole file if any other WHO
    declares an ``interface:``. Discovery cannot produce one today (OWNd returns
    ``None`` for every other WHO), so this guard exists to keep a future classifier
    from writing YAML that refuses to load.

    Mutation caught: writing ``cfg["interface"]`` unconditionally - ``config_schema``
    then raises for the meter below.
    """
    _, cfg = generate_suggested_config(
        _device_info(DEVICE_TYPE_BUS_ENERGY_METER, "51", "Main Meter", interface="3")
    )
    assert "interface" not in cfg
    config_schema({MAC: {"sensor": {"discovered_18_51": dict(cfg)}}})


def test_generate_suggested_config_stringifies_where() -> None:
    """Pins that WHERE is written as a YAML string even when discovery reports an int.

    Why it matters in production: OpenWebNet WHERE values are textual addresses -
    ``'011'`` and ``11`` are different buses. Dumping an int makes YAML emit
    ``where: 11``, which reloads as an int and loses any leading zero the user
    later types, and the schema's WHERE validators expect a string.

    Mutation caught: dropping the ``str()`` around ``device_info["where"]``.
    """
    platform, cfg = generate_suggested_config(_device_info(DEVICE_TYPE_BUS_ON_OFF_SWITCH, 11, "Int Where"))
    assert platform == "light"
    assert cfg["where"] == "11"
    assert isinstance(cfg["where"], str)


# --------------------------------------------------------------------------------------
# _merge_and_write
# --------------------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_merge_and_write_creates_the_file_when_absent(tmp_path: Path) -> None:
    """Pins that a missing target file is created, carries the suggestions under the
    gateway MAC, and that the return value counts every entry as new.

    Why it matters in production: on a first discovery run the file does not
    exist. If ``FileNotFoundError`` were not swallowed the whole flush would fail
    and the user would get no suggestions at all; if the count were wrong the log
    line would tell them "0 new" and they would never look at the file.

    Mutation caught: removing the ``except FileNotFoundError: pass`` arm, or
    returning something other than the number of newly added keys (e.g. 0, or the
    total).
    """
    target = tmp_path / DISCOVERED_CONFIG_FILE
    added = _merge_and_write(
        str(target),
        MAC,
        {"light": {"discovered_1_11": {"who": "1", "where": "11", "name": "Hallway Lamp"}}},
    )

    assert added == 1
    assert target.exists()
    assert _read_yaml(target) == {
        MAC: {"light": {"discovered_1_11": {"who": "1", "where": "11", "name": "Hallway Lamp"}}}
    }


def test_merge_and_write_preserves_existing_entries_and_counts_only_new_keys(tmp_path: Path) -> None:
    """Pins the merge semantics: unrelated gateways, unrelated platforms and
    unrelated devices survive, and ``added`` counts only keys that were not there.

    Why it matters in production: discovery re-runs on every reload. A merge that
    replaced the file would wipe the suggestions the user has not triaged yet
    (including those of a second gateway that is not being discovered right now),
    and a count that included re-written keys would keep claiming "N new" forever,
    training the user to ignore the message.

    Mutation caught: writing ``existing = {}`` unconditionally instead of loading
    the file; ``existing[mac] = {}`` instead of ``setdefault``; incrementing
    ``added`` outside the ``if key not in platform_cfg`` guard.
    """
    target = tmp_path / DISCOVERED_CONFIG_FILE
    target.write_text(
        f"""
'{MAC2}':
  light:
    discovered_1_99:
      who: '1'
      where: '99'
      name: Second Gateway Lamp
'{MAC}':
  cover:
    discovered_2_54:
      who: '2'
      where: '54'
      name: Study Blind
      shutter_run: 20
  light:
    discovered_1_11:
      who: '1'
      where: '11'
      name: Hallway Lamp
""",
        encoding="utf-8",
    )

    suggestions = {
        "light": {
            "discovered_1_11": {"who": "1", "where": "11", "name": "Hallway Lamp"},
            "discovered_1_12": {"who": "1", "where": "12", "name": "Dining Dimmer", "dimmable": True},
        },
        "switch": {"discovered_9_9": {"who": "9", "where": "9", "name": "Aux Line"}},
    }
    added = _merge_and_write(str(target), MAC, suggestions)

    # discovered_1_11 already existed: only the dimmer and the aux switch are new.
    assert added == 2

    merged = _read_yaml(target)
    # The other gateway is untouched...
    assert merged[MAC2] == {
        "light": {"discovered_1_99": {"who": "1", "where": "99", "name": "Second Gateway Lamp"}}
    }
    # ...and so is a platform of this gateway that discovery said nothing about.
    assert merged[MAC]["cover"] == {
        "discovered_2_54": {"who": "2", "where": "54", "name": "Study Blind", "shutter_run": 20}
    }
    assert merged[MAC]["light"] == suggestions["light"]
    assert merged[MAC]["switch"] == suggestions["switch"]

    # Re-writing the very same suggestions adds nothing new.
    assert _merge_and_write(str(target), MAC, suggestions) == 0


def test_merge_and_write_replaces_non_mapping_nodes_instead_of_crashing(tmp_path: Path) -> None:
    """Pins the two ``isinstance(..., dict)`` guards on the gateway and platform nodes.

    Why it matters in production: the discovered file is plain YAML the user may
    have edited by hand (or truncated). If a gateway or platform node ends up as a
    scalar or a list, ``setdefault``/item assignment on it raises, the executor job
    dies and - because the exception is not an ``OSError`` - it escapes
    ``async_flush``'s handler and fails the config-entry setup.

    Mutation caught: deleting either ``if not isinstance(...): ... = {}`` guard.
    """
    target = tmp_path / DISCOVERED_CONFIG_FILE
    target.write_text(f"'{MAC}': not-a-mapping\n'{MAC2}':\n  light: []\n", encoding="utf-8")

    added = _merge_and_write(str(target), MAC, {"light": {"discovered_1_11": {"who": "1", "where": "11"}}})
    assert added == 1
    assert _read_yaml(target)[MAC] == {"light": {"discovered_1_11": {"who": "1", "where": "11"}}}

    # Same guard, one level down: the gateway node is a mapping but the platform is a list.
    added = _merge_and_write(str(target), MAC2, {"light": {"discovered_1_99": {"who": "1", "where": "99"}}})
    assert added == 1
    assert _read_yaml(target)[MAC2] == {"light": {"discovered_1_99": {"who": "1", "where": "99"}}}


def test_merge_and_write_never_overwrites_unparsable_yaml(tmp_path: Path) -> None:
    """Pins the data-loss guard: a target file that is not valid YAML must come out
    BYTE-IDENTICAL, with the suggestions diverted to a ``.new`` sibling.

    Why it matters in production: the user is invited to edit this file, and a
    half-finished edit is exactly what an unattended reload would hit. Parsing it
    as ``{}`` and dumping over it would silently destroy their work with no way
    back - the single worst thing this integration could do to a file.

    Mutation caught: removing the ``except yaml.YAMLError`` arm (the write then
    lands on the original path and the byte comparison fails); or keeping the arm
    but forgetting ``path = f"{path}.new"``.
    """
    target = tmp_path / DISCOVERED_CONFIG_FILE
    broken = "gateway:\n  light: [unclosed\n    still broken:\n"
    target.write_bytes(broken.encode("utf-8"))
    before = target.read_bytes()

    added = _merge_and_write(
        str(target),
        MAC,
        {"light": {"discovered_1_11": {"who": "1", "where": "11", "name": "Hallway Lamp"}}},
    )

    assert target.read_bytes() == before, "an unparsable target file must never be rewritten"
    assert added == 1

    sibling = tmp_path / f"{DISCOVERED_CONFIG_FILE}.new"
    assert sibling.exists()
    assert _read_yaml(sibling) == {
        MAC: {"light": {"discovered_1_11": {"who": "1", "where": "11", "name": "Hallway Lamp"}}}
    }


def test_merge_and_write_cleans_up_its_tmp_file_when_the_write_fails(tmp_path: Path) -> None:
    """Pins the atomic-write failure path: the exception propagates, the previous
    target file is byte-identical, and no ``.myhome_discovered.*.tmp`` is left over.

    Why it matters in production: the temp file is created *inside* the user's
    config directory (it has to be, for ``os.replace`` to be atomic). A leaked one
    per failed reload is litter in the directory Home Assistant itself scans, and
    silently swallowing the failure would make the caller log a success it never
    achieved.

    Mutation caught: dropping the ``except BaseException`` cleanup block (a
    ``.tmp`` file survives); swallowing the error instead of re-``raise``-ing;
    calling ``os.replace`` before the dump so a doomed write still truncates the
    target.
    """
    target = tmp_path / DISCOVERED_CONFIG_FILE
    target.write_text(f"'{MAC}':\n  light:\n    keep_me:\n      who: '1'\n      where: '11'\n", encoding="utf-8")
    before = target.read_bytes()

    with (
        patch.object(yaml, "safe_dump", side_effect=RuntimeError("disk on fire")),
        pytest.raises(RuntimeError, match="disk on fire"),
    ):
        _merge_and_write(str(target), MAC, {"light": {"discovered_1_12": {"who": "1", "where": "12"}}})

    assert target.read_bytes() == before
    assert glob.glob(os.path.join(str(tmp_path), ".myhome_discovered.*.tmp")) == []
    assert sorted(item.name for item in tmp_path.iterdir()) == [DISCOVERED_CONFIG_FILE]


# --------------------------------------------------------------------------------------
# is_device_configured
# --------------------------------------------------------------------------------------


def _load_platforms(hass: HomeAssistant, mac: str, platforms: dict[str, Any]) -> None:
    """Put a validated-config shape into hass.data, as __init__ does at setup."""
    hass.data.setdefault(DOMAIN, {})[mac] = {CONF_PLATFORMS: platforms}


async def test_is_device_configured_compares_the_whole_device_key(hass: HomeAssistant) -> None:
    """Pins that the filter matches on ``validate.device_key``, interface included.

    Why it matters in production: this is the only thing that keeps discovery from
    suggesting devices the user already has, and the interface is part of a device's
    identity. ``1-11`` (the actuator 11 on the main bus) and ``1-11#4#03`` (the
    actuator 11 on the riser behind bus interface 3) are two different physical
    devices; a filter that reduced one to the other suppressed a suggestion for a
    device the user does *not* have configured, which is worse than a duplicate
    because nothing says it happened.

    The suggestion carries the interface unpadded (``3``), as ``myhome.yaml`` spells
    it, and ``device_key`` pads it (``#4#03``) exactly as it did when the user's own
    configuration was loaded, so the two strings meet.

    Mutations caught: comparing ``f"{who}-{where}"`` instead of the device key (the
    interfaced switch stops matching); re-introducing a ``split("#", 1)`` fallback
    (the main-bus lamp of the second gateway starts matching the riser one).
    """
    _load_platforms(hass, MAC, {"light": {"1-11": {}}, "climate": {"4-3": {}}})
    # Second gateway: its ONLY device is behind a bus interface.
    _load_platforms(hass, MAC2, {"switch": {"1-23#4#01": {}}})

    assert is_device_configured(hass, MAC, {"who": "1", "where": "11"}) is True
    assert is_device_configured(hass, MAC, {"who": "4", "zone": "3"}) is True
    assert is_device_configured(hass, MAC2, {"who": "1", "where": "23", "interface": "1"}) is True

    # The same WHERE without the interface is the main-bus device: a different one.
    assert is_device_configured(hass, MAC2, {"who": "1", "where": "23"}) is False
    assert is_device_configured(hass, MAC, {"who": "1", "where": "11", "interface": "3"}) is False
    # Prefix-only collisions must NOT match: "1-1" is a different WHERE than "1-11".
    assert is_device_configured(hass, MAC, {"who": "1", "where": "1"}) is False
    assert is_device_configured(hass, MAC, {"who": "2", "where": "11"}) is False
    # ...and a gateway with nothing loaded knows nothing.
    assert is_device_configured(hass, "00:03:50:00:00:03", {"who": "1", "where": "11"}) is False


async def test_is_device_configured_ignores_non_dict_platform_payloads(hass: HomeAssistant) -> None:
    """Pins the ``not isinstance(devices, dict)`` guard.

    Why it matters in production: ``hass.data[DOMAIN][mac][CONF_PLATFORMS]`` also
    carries non-device bookkeeping, and iterating a list of strings would compare
    the *values* as if they were device keys. That produces phantom "already
    configured" hits, and discovery then silently suggests nothing for a device the
    user does not actually have.

    Mutation caught: removing the ``continue`` (the list entry ``"1-11"`` would be
    iterated and matched, flipping the first assertion to True).
    """
    _load_platforms(hass, MAC, {"light": ["1-11"], "cover": {"2-54": {}}})

    assert is_device_configured(hass, MAC, {"who": "1", "where": "11"}) is False
    assert is_device_configured(hass, MAC, {"who": "2", "where": "54"}) is True


# --------------------------------------------------------------------------------------
# MyHOMEDiscoverySuggestions
# --------------------------------------------------------------------------------------


async def test_path_is_the_discovered_file_beside_the_configured_yaml(hass: HomeAssistant, tmp_path: Path) -> None:
    """Pins that the target is ``myhome_discovered.yaml`` in the directory of the
    configured ``myhome.yaml`` (cf-06), and never the configured file itself.

    Why it matters in production: the whole design promise is that the user's
    ``myhome.yaml`` is read-only to the integration. If the option were used as the
    target path rather than as a directory hint, discovery would overwrite the
    user's hand-written configuration on the first reload.

    Mutation caught: returning ``config_file`` itself, or using
    ``hass.config.config_dir`` while ignoring the option (the file would appear in
    the wrong directory for anyone keeping their config elsewhere).
    """
    config_file = tmp_path / "sub" / "myhome.yaml"
    entry = make_entry(config_file)
    suggestions = MyHOMEDiscoverySuggestions(hass, entry)

    assert suggestions.path == str(tmp_path / "sub" / DISCOVERED_CONFIG_FILE)
    assert suggestions.path != str(config_file)


@pytest.mark.parametrize(
    "options",
    [
        # Entries created before the option existed carry no path at all.
        {},
        # ``config_file_path: myhome.yaml`` is a legal value whose dirname is "".
        {CONF_FILE_PATH: "myhome.yaml"},
    ],
    ids=["no-option", "bare-filename"],
)
async def test_path_falls_back_to_the_config_dir(hass: HomeAssistant, options: dict) -> None:
    """Pins the fallback for both ways of ending up without a directory.

    Why it matters in production: an empty directory makes ``os.path.join`` return
    a *relative* filename, so the suggestions are written wherever the Home
    Assistant process happens to be cwd'ed - somewhere the user will never find
    them, on a run they were told produced a file.

    Mutations caught: dropping the ``or self.hass.config.config_dir`` fallback,
    dropping the ``if config_file`` guard, or reducing
    ``os.path.join(directory or self.hass.config.config_dir, ...)`` to
    ``os.path.join(directory, ...)``.
    """
    entry = MockConfigEntry(domain=DOMAIN, unique_id=MAC, data={"mac": MAC}, options=options)
    suggestions = MyHOMEDiscoverySuggestions(hass, entry)

    assert suggestions.path == os.path.join(hass.config.config_dir, DISCOVERED_CONFIG_FILE)
    assert os.path.isabs(suggestions.path)


async def test_add_queues_only_new_suggestable_devices(hass: HomeAssistant, tmp_path: Path) -> None:
    """Pins ``add()``'s three outcomes and the shape of the generated YAML key.

    Why it matters in production: ``add()`` is the gate between the bus scan and
    the file. Queueing an unsupported device type would emit an entry that fails
    validation; queueing an already-configured one would hand the user a duplicate;
    and the key must be a valid YAML identifier, so the ``#`` of an interfaced or
    composite WHERE has to become ``_`` (``discovered_1-11#4#01`` would be a
    confusing key and collides with nothing the user can safely retype).  It is
    derived from ``validate.device_key``, so the riser lamp below cannot land on the
    key of the main-bus lamp with the same WHERE.

    Mutation caught: returning True unconditionally; dropping the
    ``is_device_configured`` check; removing ``.replace("#", "_")``; or keying on
    ``who``/``where`` alone, which loses the interface.
    """
    entry = make_entry(tmp_path / "myhome.yaml")
    _load_platforms(hass, MAC, {"light": {"1-11": {}}})
    suggestions = MyHOMEDiscoverySuggestions(hass, entry)

    # No entity representation -> not queued.
    assert suggestions.add(_device_info(DEVICE_TYPE_BUS_CEN_SCENARIO_CONTROL, "21", "Wall Keypad")) is False
    # Already in the user's configuration -> not queued.
    assert suggestions.add(_device_info(DEVICE_TYPE_BUS_ON_OFF_SWITCH, "11", "Hallway Lamp")) is False
    assert suggestions.pending_count == 0

    # Genuinely new, with a WHERE that needs sanitising for the key.
    assert suggestions.add(_device_info(DEVICE_TYPE_BUS_ENERGY_METER, "5#1", "Main Meter")) is True
    # Climate is keyed on the zone the config carries under `zone`, not `where`.
    assert suggestions.add(_device_info(DEVICE_TYPE_BUS_THERMO_ZONE, "3", "Bedroom Zone")) is True
    assert suggestions.pending_count == 2

    # Same WHERE as the configured lamp above, but on a riser: a different device,
    # so it *is* queued, under a key of its own.
    assert suggestions.add(_device_info(DEVICE_TYPE_BUS_ON_OFF_SWITCH, "11", "Riser Lamp", "3")) is True

    pending = suggestions._pending  # noqa: SLF001 - the queue is the unit under test
    assert set(pending) == {"sensor", "climate", "light"}
    assert list(pending["light"]) == ["discovered_1_11_4_03"]
    assert pending["sensor"] == {
        "discovered_18_5_1": {"who": "18", "where": "5#1", "name": "Main Meter", "class": "power"}
    }
    assert pending["climate"] == {"discovered_4_3": {"who": "4", "zone": "3", "name": "Bedroom Zone"}}


async def test_a_config_directory_it_cannot_write_is_reported_not_swallowed(
    hass: HomeAssistant, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A discovery run that finds devices and writes nothing must say so.

    ``async_flush`` empties the queue *before* the write, so when the write fails the
    suggestions are gone: an unwritable ``/config`` (a read-only mount, a
    root-owned ``myhome_discovered.yaml`` left by an earlier container) would
    otherwise end the run with the usual "Discovery finished" INFO missing and
    nothing at all in its place, and the user would go looking for a file that was
    never created. The ERROR is the only trace, so it has to name the path.

    It must also stay an ERROR rather than an exception: ``async_flush`` runs from the
    stop service and from the discovery timeout, and a raise there would abort the
    run's teardown.

    Mutation caught: dropping the ``except OSError`` arm (the error escapes into the
    caller), or logging it without ``self.path``.
    """
    entry = make_entry(tmp_path / "myhome.yaml")
    _load_platforms(hass, MAC, {})
    suggestions = MyHOMEDiscoverySuggestions(hass, entry)
    assert suggestions.add(_device_info(DEVICE_TYPE_BUS_ON_OFF_SWITCH, "11", "Hallway Lamp")) is True

    with (
        caplog.at_level(logging.ERROR, logger="custom_components.myhome"),
        patch(
            "custom_components.myhome.config_flow_discovery._merge_and_write",
            side_effect=OSError("Read-only file system"),
        ),
    ):
        await suggestions.async_flush()  # must not raise

    errors = [record.message for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(errors) == 1
    assert "Could not write discovery suggestions" in errors[0]
    assert suggestions.path in errors[0]
    assert "Read-only file system" in errors[0]
    # The queue was emptied before the write, so nothing is left to retry with.
    assert suggestions.pending_count == 0
