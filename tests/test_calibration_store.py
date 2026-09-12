"""Tests for where a guided calibration is kept, and what it beats (0.5.0, spec 1.3).

Two halves, and they are tested differently. The **precedence** is a pure function of
three mappings (the validated cover, the profiles, the stored calibration), so most of
this file is a matrix run straight through `resolve_cover` with no Home Assistant in
sight. The **storage** is a `Store` of the integration's own, one per config entry, so
the rest of it sets the integration up with the store already written and reads the
cover back out. (Up to the first draft of 0.5.0 the same data lived in config
subentries; the migration out of them has a test of its own at the end.)

The order under test, highest first: an override stored for this cover, the key as
written in `myhome.yaml`, the profile (stored one first, scaled to the stored height if
there is one), and last what the validator already resolved.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.myhome import calibration_store
from custom_components.myhome.calibration_store import (
    CalibrationStore,
    StoredCalibration,
    async_get_store,
    cover_calibration_data,
    cover_profile_data,
    loaded_store,
    merged_profiles,
    profile_as_config,
    resolve_cover,
)
from custom_components.myhome.const import (
    ATTR_CALIBRATION_SOURCE,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_UNIQUE_ID,
    CONF_COVERS,
    CONF_HEIGHT,
    CONF_KEYS_FROM_FILE,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_OVERRIDES,
    CONF_PROFILE,
    CONF_PROFILES,
    CONF_RAW,
    CONF_REFERENCE_HEIGHT,
    CONF_ROLL,
    CONF_SLAT_TIME,
    CONF_SOURCE,
    CONF_START_DELAY,
    CONF_STOP_LATENCY,
    LEGACY_SUBENTRY_COVER_CALIBRATION,
    LEGACY_SUBENTRY_COVER_PROFILE,
)

from .helpers_core import MAC
from .helpers_platforms import device_config, set_connected, setup_myhome

ENTITY = "cover.hallway_shutter"
DEVICE_KEY = "2-81"
UNIQUE_ID = f"{MAC}-{DEVICE_KEY}"

# A cover that writes two of its own times and follows a profile for the rest.
YAML = f"""
gateway:
  mac: {MAC}
  cover_profiles:
    tall:
      reference_height: 195
      opening_time: 22.3
      closing_time: 21.7
      slat_time: 4.7
      roll: 1.6
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      profile: tall
      height: 195
"""

# The same cover with nothing but its own numbers in the file.
PLAIN_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      opening_time: 20
      closing_time: 19
      slat_time: 3
      roll: 1.5
"""

# A cover that writes one time and leaves everything else to be filled in.
SPARSE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      opening_time: 20
"""


def _validated(**keys: Any) -> dict[str, Any]:
    """A cover as the validator leaves it: every key filled in, and which ones are the file's.

    `keys_from_file` is the marker `record_cover_keys_from_file` adds, and the whole
    precedence hangs off it - it is the only thing that says whether `closing_time` was
    typed by the user or derived from a profile.
    """
    device = {
        CONF_OPENING_TIME: 20.0,
        CONF_CLOSING_TIME: 20.0,
        CONF_SLAT_TIME: 0.0,
        CONF_ROLL: 1.6,
        CONF_OPENING_ROLL: 1.6,
        CONF_CLOSING_ROLL: 1.6,
        CONF_STOP_LATENCY: 0.1,
        CONF_START_DELAY: 0.5,
        CONF_KEYS_FROM_FILE: [],
    }
    device.update(keys)
    return device


PROFILE = {
    CONF_REFERENCE_HEIGHT: 195.0,
    CONF_OPENING_TIME: 22.3,
    CONF_CLOSING_TIME: 21.7,
    CONF_SLAT_TIME: 4.7,
    CONF_ROLL: 1.6,
    CONF_OPENING_ROLL: 1.6,
    CONF_CLOSING_ROLL: 1.6,
    CONF_STOP_LATENCY: 0.1,
    CONF_START_DELAY: 0.5,
}


# --------------------------------------------------------------------------------------
# The precedence, key by key
# --------------------------------------------------------------------------------------
def test_an_override_beats_everything() -> None:
    """The guided flow measured *this* window: nothing knows better than that.

    Mutation caught: reading the file before the override, which would make a
    calibration invisible on any cover whose times are written out.
    """
    device = _validated(
        **{CONF_OPENING_TIME: 20.0, CONF_KEYS_FROM_FILE: [CONF_OPENING_TIME], CONF_PROFILE: "tall"}
    )
    resolved = resolve_cover(
        device,
        profiles={"tall": PROFILE},
        calibration=StoredCalibration(UNIQUE_ID, overrides={CONF_OPENING_TIME: 23.4}),
    )
    assert resolved.values[CONF_OPENING_TIME] == 23.4


def test_a_common_key_in_the_file_speaks_for_its_directional_pair() -> None:
    """`roll: 1.5` in the file says what both directions do, so a profile cannot.

    The file's own fallbacks are part of what the file says: `_finalize_cover` lets one
    `roll:` stand for both directional rolls and one `opening_time:` for both runs.
    Reading only the keys that literally appear would let a profile fill in the pair and
    contradict the line the user did write.

    Mutation caught: dropping `_IMPLIED_BY_THE_FILE`, after which a profiled cover whose
    file says `roll: 1.5` silently runs on the profile's rolls.
    """
    device = _validated(
        **{
            CONF_ROLL: 1.5,
            CONF_OPENING_ROLL: 1.5,
            CONF_CLOSING_ROLL: 1.5,
            CONF_OPENING_TIME: 20.0,
            CONF_CLOSING_TIME: 20.0,
            CONF_PROFILE: "tall",
            CONF_KEYS_FROM_FILE: [CONF_ROLL, CONF_OPENING_TIME],
        }
    )
    profile = {**PROFILE, CONF_OPENING_ROLL: 2.12, CONF_CLOSING_ROLL: 1.69, CONF_ROLL: 1.69}
    resolved = resolve_cover(device, profiles={"tall": profile}, calibration=None)
    assert resolved.values[CONF_OPENING_ROLL] == 1.5
    assert resolved.values[CONF_CLOSING_ROLL] == 1.5
    assert resolved.values[CONF_CLOSING_TIME] == 20.0
    # What the file says nothing about is still the profile's.
    assert resolved.values[CONF_SLAT_TIME] == pytest.approx(4.7)


def test_what_the_file_says_beats_a_profile() -> None:
    """A key the user wrote is about *this* window; a profile is about that kind of window.

    So the file sits above the profile and below an override measured on this very
    shutter - see the module docstring, where that order is argued out.

    Mutation caught: dropping the `keys_from_file` term, after which a profile silently
    replaces the times a user typed.
    """
    device = _validated(
        **{
            CONF_OPENING_TIME: 20.0,
            CONF_CLOSING_TIME: 18.0,
            CONF_KEYS_FROM_FILE: [CONF_CLOSING_TIME],
            CONF_PROFILE: "tall",
            CONF_HEIGHT: 195.0,
        }
    )
    resolved = resolve_cover(device, profiles={"tall": PROFILE}, calibration=None)
    assert resolved.values[CONF_CLOSING_TIME] == 18.0  # the file's
    assert resolved.values[CONF_OPENING_TIME] == pytest.approx(22.3)  # the profile's


def test_a_stored_profile_is_scaled_to_the_stored_height() -> None:
    """Path B of the flow: this window is one of those, and it is 150 cm tall.

    The profile is measured at one height and scaled to each window (0.4.2); the height
    the guided flow measured wins over the one in the file, because it is the one that
    was measured with a tape rather than remembered.

    Mutation caught: taking the height from the file when both exist, which scales a
    profile to the wrong window and is invisible until the shutter stops 10 cm out.
    """
    device = _validated(**{CONF_PROFILE: "tall", CONF_HEIGHT: 195.0})
    resolved = resolve_cover(
        device,
        profiles={"tall": PROFILE},
        calibration=StoredCalibration(UNIQUE_ID, profile="tall", height=150.0),
    )
    assert resolved.height == 150.0
    # Shorter window, less curtain on the tube: a smaller roll and a shorter run.
    assert resolved.values[CONF_CLOSING_ROLL] < PROFILE[CONF_CLOSING_ROLL]
    assert resolved.values[CONF_OPENING_TIME] < PROFILE[CONF_OPENING_TIME]
    # The bus costs belong to the installation, not to the window: never scaled.
    assert resolved.values[CONF_STOP_LATENCY] == 0.1
    assert resolved.values[CONF_START_DELAY] == 0.5


def test_a_stored_calibration_can_name_a_profile_the_file_does_not() -> None:
    """The commonest path of all: the file says nothing, the flow says everything."""
    resolved = resolve_cover(
        _validated(),
        profiles={"tall": PROFILE},
        calibration=StoredCalibration(UNIQUE_ID, profile="tall", height=195.0),
    )
    assert resolved.profile == "tall"
    assert resolved.values[CONF_OPENING_TIME] == pytest.approx(22.3)
    assert resolved.values[CONF_SLAT_TIME] == pytest.approx(4.7)


def test_without_anything_stored_the_validated_configuration_is_kept() -> None:
    """No calibration, no profile: the resolution changes nothing at all.

    This is every cover of every installation that never runs the flow, so it is the
    case that must be exactly the 0.4.5 behaviour, term for term.
    """
    device = _validated(**{CONF_OPENING_TIME: 30.0, CONF_KEYS_FROM_FILE: [CONF_OPENING_TIME]})
    resolved = resolve_cover(device, profiles={}, calibration=None)
    assert resolved.values[CONF_OPENING_TIME] == 30.0
    assert resolved.values[CONF_CLOSING_TIME] == device[CONF_CLOSING_TIME]
    assert resolved.source == "yaml"
    assert resolved.profile is None


def test_a_calibration_that_says_nothing_is_not_a_calibration() -> None:
    """An empty subentry (hand-edited storage) leaves the cover on its file numbers."""
    resolved = resolve_cover(_validated(), profiles={}, calibration=StoredCalibration(UNIQUE_ID))
    assert resolved.source == "yaml"


def test_a_calibration_naming_a_profile_that_is_gone_falls_back(caplog) -> None:
    """A renamed profile must not take the shutter down with it.

    The cover keeps the configuration it was validated with and the log says why; a
    shutter that stopped working because a name changed would be worse than one that
    stops where it always did.
    """
    device = _validated(**{CONF_OPENING_TIME: 30.0, CONF_KEYS_FROM_FILE: [CONF_OPENING_TIME]})
    with caplog.at_level(logging.WARNING):
        resolved = resolve_cover(
            device, profiles={}, calibration=StoredCalibration(UNIQUE_ID, profile="gone")
        )
    assert resolved.values[CONF_OPENING_TIME] == 30.0
    assert "not defined any more" in caplog.text


@pytest.mark.parametrize(
    ("calibration", "profiles", "expected"),
    [
        (None, {}, "yaml"),
        (None, {"tall": PROFILE}, "profile tall"),
        (StoredCalibration(UNIQUE_ID, height=150.0), {}, "yaml"),
        (StoredCalibration(UNIQUE_ID, profile="tall"), {"tall": PROFILE}, "profile tall"),
        (
            StoredCalibration(UNIQUE_ID, overrides={CONF_OPENING_TIME: 22.3}),
            {},
            "guided",
        ),
    ],
)
def test_the_source_says_where_the_numbers_came_from(
    calibration: StoredCalibration | None, profiles: dict, expected: str
) -> None:
    """Three answers, and the entity publishes whichever applies.

    A shutter whose times came from the guided flow looks exactly like one whose times
    were typed into the file, and the difference is the first thing to establish when
    one of them stops where it should not.

    `guided` is reserved for a record that carries *measurements* of this window. A
    record that only says "this one is a `tall`" - which is what the assignment screen
    and path B write - changes nothing but which profile applies, and the source says
    so: the 0.5.0 review found `guided` on a shutter every one of whose travel keys
    still came from the file.
    """
    device = _validated(**({CONF_PROFILE: "tall"} if profiles else {}))
    assert resolve_cover(device, profiles=profiles, calibration=calibration).source == expected


# --------------------------------------------------------------------------------------
# One namespace for both kinds of profile
# --------------------------------------------------------------------------------------
def test_a_stored_profile_of_the_same_name_wins_and_says_so(caplog) -> None:
    """`profile: tall` is one word and has to mean one thing.

    The stored one wins: the user ran the flow on this installation *after* writing the
    file, and the name came from the flow in the first place. Said out loud once per
    name, because a profile that quietly stops being the one in the file costs an
    evening.

    Mutation caught: letting the file win (the calibration would then appear to do
    nothing at all), or warning once per cover per reload (twelve covers, twelve lines).
    """
    calibration_store.reset_name_clash_warnings()
    stored = {"tall": {**PROFILE, CONF_OPENING_TIME: 30.0}}
    with caplog.at_level(logging.WARNING):
        merged = merged_profiles({"tall": PROFILE}, stored)
        merged_again = merged_profiles({"tall": PROFILE}, stored)
    assert merged["tall"][CONF_OPENING_TIME] == 30.0
    assert merged_again == merged
    assert caplog.text.count("is defined both in") == 1
    assert "tall" in caplog.text


def test_profiles_that_do_not_clash_are_simply_both_there() -> None:
    """Two namespaces would be two things to explain; there is one."""
    calibration_store.reset_name_clash_warnings()
    merged = merged_profiles({"tall": PROFILE}, {"short": PROFILE})
    assert sorted(merged) == ["short", "tall"]


# --------------------------------------------------------------------------------------
# The store itself
# --------------------------------------------------------------------------------------
PROFILE_DATA = cover_profile_data(
    "tall",
    reference_height=195.0,
    opening_time=22.3,
    closing_time=21.7,
    slat_time=4.7,
    opening_roll=2.12,
    closing_roll=1.69,
    reference_cover="Hallway Shutter",
    raw={"presses": 3},
)


def stored(profiles: dict | None = None, covers: dict | None = None) -> dict:
    """The shape of the store file: two sections, and nothing else."""
    return {CONF_PROFILES: profiles or {}, CONF_COVERS: covers or {}}


def calibration_record(**kwargs: Any) -> dict:
    data = cover_calibration_data(UNIQUE_ID, **kwargs)
    return {key: value for key, value in data.items() if key != CONF_COVER_UNIQUE_ID}


async def load_store(hass: HomeAssistant, entry) -> CalibrationStore:
    return await async_get_store(hass, entry)


async def test_the_stored_shapes_are_read_back_as_they_were_written(
    hass: HomeAssistant, tmp_path
) -> None:
    """What the flow writes is what the resolution reads: one schema, in one place."""
    async with setup_myhome(
        hass,
        tmp_path,
        PLAIN_YAML,
        calibration=stored(
            profiles={"tall": PROFILE_DATA},
            covers={UNIQUE_ID: calibration_record(profile="tall", height=150.0)},
        ),
    ) as (entry, _commands):
        store = loaded_store(hass, entry)
        profiles = store.profiles
        assert sorted(profiles) == ["tall"]
        assert profiles["tall"][CONF_OPENING_ROLL] == 2.12
        assert profiles["tall"][CONF_CLOSING_ROLL] == 1.69
        # `roll` is the fallback of the two, and the one the height scaling reads: the
        # closing one, which measures the length of fabric on the tube.
        assert profiles["tall"][CONF_ROLL] == 1.69
        # Never measured by the flow, so the installation defaults stand.
        assert profiles["tall"][CONF_STOP_LATENCY] == 0.1
        # The record as it was written is kept too, for the screens that show it.
        assert store.profile("tall")["reference_cover"] == "Hallway Shutter"
        assert store.profile("tall")[CONF_RAW] == {"presses": 3}

        calibrations = store.calibrations
        assert list(calibrations) == [UNIQUE_ID]
        assert calibrations[UNIQUE_ID].profile == "tall"
        assert calibrations[UNIQUE_ID].height == 150.0
        assert calibrations[UNIQUE_ID].source == "guided"
        assert calibrations[UNIQUE_ID].measured_at is not None
        assert store.covers_following("tall") == [UNIQUE_ID]


def test_a_stored_shape_that_is_not_one_is_ignored_rather_than_obeyed(caplog) -> None:
    """Hand-edited storage, or a record from a version this one does not know.

    Ignoring it leaves the cover on its file numbers, which is the safe way to be
    wrong; half-reading it would give the shutter a run time of `None`.
    """
    with caplog.at_level(logging.WARNING):
        assert profile_as_config("tall", {CONF_NAME: "tall"}) is None
    assert "without a name, an opening time or a reference height" in caplog.text


async def test_a_store_file_that_is_not_a_store_leaves_the_covers_alone(
    hass: HomeAssistant, tmp_path
) -> None:
    """A `.storage` file edited into nonsense must not take the shutters down.

    Mutation caught: reading the two sections without checking that they are mappings
    (the next `.items()` would raise inside `async_setup_entry`).
    """
    async with setup_myhome(
        hass, tmp_path, PLAIN_YAML, calibration={CONF_PROFILES: "?", CONF_COVERS: 3}
    ) as (entry, _commands):
        store = loaded_store(hass, entry)
        assert store.profiles == {}
        assert store.calibrations == {}
        assert hass.states.get(ENTITY).attributes["Opening time"] == 20.0


def test_the_builders_keep_only_what_the_travel_model_knows(caplog) -> None:
    """A key the model never reads is a key nobody would ever notice doing nothing."""
    with caplog.at_level(logging.WARNING):
        data = cover_calibration_data(
            UNIQUE_ID, overrides={CONF_OPENING_TIME: 22.0, "tilt_angle": 30.0}
        )
    assert data[CONF_OVERRIDES] == {CONF_OPENING_TIME: 22.0}
    assert "tilt_angle" in caplog.text
    assert data[CONF_SOURCE] == "guided"
    # Nothing optional is invented: a calibration with no overrides has no key for them.
    assert CONF_OVERRIDES not in cover_calibration_data(UNIQUE_ID, height=150.0)
    assert CONF_RAW not in cover_calibration_data(UNIQUE_ID)
    # What the flow chooses to keep of how it got there is kept verbatim: nothing reads
    # it back, and that is the point - it is there to be read by a person, later.
    kept_raw = cover_calibration_data(UNIQUE_ID, raw={"half_down_cm": 85, "half_up_cm": 80})
    assert kept_raw[CONF_RAW] == {"half_down_cm": 85, "half_up_cm": 80}


def test_the_closing_slat_press_is_stored_even_though_nothing_reads_it_yet() -> None:
    """The precise level can measure it; the travel model still has one slat time.

    Storing it costs nothing and keeps a measurement that was actually made, so the
    release that gives the model an asymmetric slat phase has the data waiting for it.
    See the phase 1 handoff - this is a deliberate gap, not an oversight.
    """
    data = cover_profile_data(
        "tall",
        reference_height=195.0,
        opening_time=22.3,
        closing_time=21.7,
        slat_time=4.7,
        closing_slat_time=5.4,
        opening_roll=2.1,
        closing_roll=1.7,
    )
    assert data["closing_slat_time"] == 5.4


# --------------------------------------------------------------------------------------
# End to end: a cover that reads the store at setup
# --------------------------------------------------------------------------------------
async def test_a_stored_calibration_reaches_the_entity(hass: HomeAssistant, tmp_path) -> None:
    """The whole point: the shutter runs on the numbers the flow measured.

    Mutation caught: resolving the calibration and then building the entity from the
    unresolved configuration (the attributes would be right and the movements wrong -
    or the other way round, which is worse).
    """
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(
        hass,
        tmp_path,
        PLAIN_YAML,
        calibration=stored(
            covers={
                UNIQUE_ID: calibration_record(
                    overrides={
                        CONF_OPENING_TIME: 22.3,
                        CONF_CLOSING_TIME: 21.7,
                        CONF_SLAT_TIME: 4.7,
                        CONF_OPENING_ROLL: 2.12,
                        CONF_CLOSING_ROLL: 1.69,
                    }
                )
            }
        ),
    ):
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == 22.3
        assert state.attributes["Closing time"] == 21.7
        assert state.attributes["Slat time"] == 4.7
        assert state.attributes["Opening roll"] == 2.12
        assert state.attributes["Closing roll"] == 1.69
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "guided"
        # And the configuration everything else reads says the same thing.
        assert device_config(hass, COVER, DEVICE_KEY)[CONF_OPENING_TIME] == 22.3
        assert device_config(hass, COVER, DEVICE_KEY)["shutter_run"] == 22.3


async def test_a_stored_profile_does_not_overrule_the_file(hass: HomeAssistant, tmp_path) -> None:
    """A profile is about that *kind* of window; the file is about this one.

    So a stored profile fills in only what the file leaves out - which is also the
    per-key part of the rule: `opening_time` stays the file's while the slat phase and
    the rolls come from the profile.
    """
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(
        hass,
        tmp_path,
        SPARSE_YAML,
        calibration=stored(
            profiles={"tall": PROFILE_DATA},
            covers={UNIQUE_ID: calibration_record(profile="tall", height=195.0)},
        ),
    ):
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == 20.0  # the file's
        # ... and so is the closing time, which the file states by leaving it out: a
        # cover that writes one run time has said both are the same (`_finalize_cover`).
        assert state.attributes["Closing time"] == 20.0
        assert state.attributes["Slat time"] == pytest.approx(4.7)  # the profile's
        assert state.attributes["Opening roll"] == pytest.approx(2.12)  # the profile's
        # Nothing was measured on *this* window, so the source names the profile rather
        # than claiming a guided calibration that never touched it (review BUG-1).
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "profile tall"


async def test_a_stored_profile_reaches_a_cover_that_names_it_in_the_file(
    hass: HomeAssistant, tmp_path
) -> None:
    """The name clash, end to end: `profile: tall` resolves to the measured one.

    The file defines `tall` and so does a guided calibration; the cover follows the
    guided one, and `Calibration source` says `profile tall` because this particular
    window has no measurements of its own.
    """
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(
        hass,
        tmp_path,
        YAML,
        calibration=stored(profiles={"tall": {**PROFILE_DATA, CONF_OPENING_TIME: 30.0}}),
    ):
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == 30.0
        assert state.attributes["Opening roll"] == 2.12
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "profile tall"


async def test_a_cover_with_nothing_stored_is_exactly_what_the_file_says(
    hass: HomeAssistant, tmp_path
) -> None:
    """Every installation that never runs the flow: unchanged, attribute apart."""
    async with setup_myhome(hass, tmp_path, PLAIN_YAML):
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == 20.0
        assert state.attributes["Closing time"] == 19.0
        assert state.attributes["Roll"] == 1.5
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "yaml"


# --------------------------------------------------------------------------------------
# Writing, replacing and removing
# --------------------------------------------------------------------------------------
async def test_storing_the_same_profile_twice_replaces_it(hass: HomeAssistant, tmp_path) -> None:
    """A second calibration of the same kind of shutter means the second measurement.

    Two profiles with one name would make the namespace depend on which one storage
    happened to list first.

    Mutation caught: adding instead of replacing.
    """
    async with setup_myhome(hass, tmp_path, PLAIN_YAML) as (entry, _commands):
        store = await load_store(hass, entry)
        await store.async_set_profile("tall", PROFILE_DATA)
        await store.async_set_profile("tall", {**PROFILE_DATA, CONF_OPENING_TIME: 23.4})
        assert list(store.raw_profiles) == ["tall"]
        assert store.profiles["tall"][CONF_OPENING_TIME] == 23.4
        # ...and it really is on disk: a fresh store of the same entry reads it back.
        again = CalibrationStore(hass, entry.entry_id)
        await again.async_load()
        assert again.profiles["tall"][CONF_OPENING_TIME] == 23.4


async def test_deleting_a_profile_hands_its_covers_back(hass: HomeAssistant, tmp_path) -> None:
    """The covers that followed it lose the assignment, and the caller is told which.

    A name that resolves to nothing would make the assignment screen offer a profile
    that is not there, and `resolve_cover` would log a warning per cover per reload.

    Mutation caught: deleting the profile and leaving the covers pointing at it.
    """
    async with setup_myhome(hass, tmp_path, PLAIN_YAML) as (entry, _commands):
        store = await load_store(hass, entry)
        await store.async_set_profile("tall", PROFILE_DATA)
        await store.async_set_calibration(
            UNIQUE_ID, cover_calibration_data(UNIQUE_ID, profile="tall", height=195.0)
        )
        other = f"{MAC}-2-82"
        await store.async_set_calibration(
            other,
            cover_calibration_data(other, profile="tall", overrides={CONF_SLAT_TIME: 4.7}),
        )
        # A third that was only ever *assigned*, with nothing measured on it at all.
        bare = f"{MAC}-2-83"
        await store.async_set_calibration(bare, cover_calibration_data(bare, profile="tall"))

        orphans = await store.async_remove_profile("tall")
        assert orphans == sorted([UNIQUE_ID, other, bare])
        # The record that said nothing but the name goes with the name: a row on the
        # "Calibrazioni" screen with nothing in it is a row nobody can act on.
        assert bare not in store.raw_covers
        assert store.profiles == {}
        # Both keep what was measured on them - a height is a measurement of *that*
        # window and outlives the kind it was filed under - and both lose the name.
        assert store.calibration(UNIQUE_ID).profile is None
        assert store.calibration(UNIQUE_ID).height == 195.0
        assert store.calibration(other).profile is None
        assert store.calibration(other).overrides == {CONF_SLAT_TIME: 4.7}
        # Deleting it twice is not an error, and answers with nobody.
        assert await store.async_remove_profile("tall") == []


async def test_removing_a_calibration_gives_the_cover_back_to_the_file(
    hass: HomeAssistant, tmp_path
) -> None:
    """"Elimina la calibrazione" means the shutter goes back to the file.

    The entity reads its travel model once, in its constructor, so the removal only
    reaches the shutter through a reload - which the options dialog does when it
    closes. Here the reload is done by hand, because this test is about the store.
    """
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(
        hass,
        tmp_path,
        PLAIN_YAML,
        calibration=stored(covers={UNIQUE_ID: calibration_record(overrides={CONF_OPENING_TIME: 22.3})}),
    ) as (entry, _commands):
        assert hass.states.get(ENTITY).attributes["Opening time"] == 22.3

        store = loaded_store(hass, entry)
        assert await store.async_remove_calibration(UNIQUE_ID) is True
        assert await store.async_remove_calibration(UNIQUE_ID) is False

        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        await set_connected(hass, True)

        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == 20.0
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "yaml"


async def test_assigning_a_profile_writes_only_what_changed(
    hass: HomeAssistant, tmp_path
) -> None:
    """The assignment screen's write: a profile, a height, and nothing else touched.

    Mutation caught: reporting a change when there is none (the dialog would reload the
    entry - and disconnect the gateway - every time somebody opened the form and
    pressed Submit).
    """
    async with setup_myhome(hass, tmp_path, PLAIN_YAML) as (entry, _commands):
        store = await load_store(hass, entry)
        await store.async_set_profile("tall", PROFILE_DATA)
        assert await store.async_set_assignments({UNIQUE_ID: ("tall", 195.0)}) is True
        assert store.calibration(UNIQUE_ID).profile == "tall"
        assert store.calibration(UNIQUE_ID).height == 195.0
        # The same answer twice is not a change.
        assert await store.async_set_assignments({UNIQUE_ID: ("tall", 195.0)}) is False
        # "Nessun profilo" drops the name and keeps the height, which was measured on
        # this window and is the one thing the assignment screen learned about it.
        assert await store.async_set_assignments({UNIQUE_ID: (None, None)}) is True
        assert store.calibration(UNIQUE_ID).profile is None
        assert store.calibration(UNIQUE_ID).height == 195.0
        # ...but a cover that was only ever assigned loses its record entirely.
        other = f"{MAC}-2-82"
        assert await store.async_set_assignments({other: ("tall", None)}) is True
        assert await store.async_set_assignments({other: (None, None)}) is True
        assert other not in store.raw_covers


async def test_removing_the_entry_removes_its_store(hass: HomeAssistant, tmp_path) -> None:
    """The shutters go with the gateway, so their measurements have nobody left."""
    async with setup_myhome(
        hass,
        tmp_path,
        PLAIN_YAML,
        calibration=stored(covers={UNIQUE_ID: calibration_record(overrides={CONF_SLAT_TIME: 4.7})}),
    ) as (entry, _commands):
        assert loaded_store(hass, entry).calibrations[UNIQUE_ID].overrides
        entry_id = entry.entry_id

    await hass.config_entries.async_remove(entry_id)
    await hass.async_block_till_done()
    left = CalibrationStore(hass, entry_id)
    await left.async_load()
    assert left.raw_profiles == {}
    assert left.raw_covers == {}


# --------------------------------------------------------------------------------------
# Out of the first draft's config subentries
# --------------------------------------------------------------------------------------
def _profile_subentry(name: str = "tall", **overrides: Any) -> Any:
    data = dict(PROFILE_DATA)
    data[CONF_NAME] = name
    data.update(overrides)
    return ConfigSubentryData(
        data=data,
        subentry_type=LEGACY_SUBENTRY_COVER_PROFILE,
        title=name,
        unique_id=f"{LEGACY_SUBENTRY_COVER_PROFILE}-{name}",
    )


def _calibration_subentry(**kwargs: Any) -> Any:
    return ConfigSubentryData(
        data=cover_calibration_data(UNIQUE_ID, **kwargs),
        subentry_type=LEGACY_SUBENTRY_COVER_CALIBRATION,
        title="Hallway Shutter",
        unique_id=f"{LEGACY_SUBENTRY_COVER_CALIBRATION}-{UNIQUE_ID}",
    )


async def test_an_installation_written_by_the_first_draft_is_moved_into_the_store(
    hass: HomeAssistant, tmp_path
) -> None:
    """The two subentry types are read once, imported, and deleted.

    That last part is what takes the stray rows off the integration page and stops
    Home Assistant filing every device under "devices not belonging to a subentry",
    which is the whole reason the storage moved.

    Mutation caught: importing without removing (the page would keep the rows and the
    next setup would import them again over whatever the user had since edited).
    """
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(
        hass,
        tmp_path,
        PLAIN_YAML,
        subentries=[
            _profile_subentry(),
            _calibration_subentry(
                profile="tall", height=195.0, overrides={CONF_OPENING_TIME: 22.3}
            ),
        ],
    ) as (entry, _commands):
        store = loaded_store(hass, entry)
        assert store.profiles["tall"][CONF_OPENING_TIME] == 22.3
        assert store.calibration(UNIQUE_ID).profile == "tall"
        assert store.calibration(UNIQUE_ID).height == 195.0
        assert store.calibration(UNIQUE_ID).overrides == {CONF_OPENING_TIME: 22.3}
        assert entry.subentries == {}
        # And the shutter runs on them, on this very setup.
        assert hass.states.get(ENTITY).attributes["Opening time"] == 22.3


async def test_the_store_wins_over_a_subentry_that_says_something_else(
    hass: HomeAssistant, tmp_path
) -> None:
    """The store is the newer statement by construction: nothing writes subentries now.

    Mutation caught: letting the import overwrite what the user has since measured.
    """
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(
        hass,
        tmp_path,
        PLAIN_YAML,
        subentries=[_calibration_subentry(overrides={CONF_OPENING_TIME: 30.0})],
        calibration=stored(covers={UNIQUE_ID: calibration_record(overrides={CONF_OPENING_TIME: 22.3})}),
    ) as (entry, _commands):
        assert loaded_store(hass, entry).calibration(UNIQUE_ID).overrides == {
            CONF_OPENING_TIME: 22.3
        }
        assert entry.subentries == {}
        assert hass.states.get(ENTITY).attributes["Opening time"] == 22.3


async def test_a_subentry_of_another_kind_is_left_where_it_is(
    hass: HomeAssistant, tmp_path
) -> None:
    """The import is about two types and only those two."""
    other = ConfigSubentryData(
        data={"anything": 1}, subentry_type="something_else", title="?", unique_id="x"
    )
    async with setup_myhome(hass, tmp_path, PLAIN_YAML, subentries=[other]) as (entry, _commands):
        assert [s.subentry_type for s in entry.subentries.values()] == ["something_else"]
        assert loaded_store(hass, entry).raw_profiles == {}
