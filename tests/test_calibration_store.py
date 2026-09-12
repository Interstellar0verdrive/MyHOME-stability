"""Tests for where a guided calibration is kept, and what it beats (0.5.0, spec 1.3).

Two halves, and they are tested differently. The **precedence** is a pure function of
three mappings (the validated cover, the profiles, the stored calibration), so most of
this file is a matrix run straight through `resolve_cover` with no Home Assistant in
sight. The **storage** is config subentries of the gateway's entry, so the rest of it
sets the integration up with subentries in place and reads the cover back out.

The order under test, highest first: an override stored for this cover, the key as
written in `myhome.yaml`, the profile (stored one first, scaled to the stored height if
there is one), and last what the validator already resolved.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.config_entries import ConfigSubentry, ConfigSubentryData
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.myhome import calibration_store
from custom_components.myhome.calibration_store import (
    StoredCalibration,
    async_remove_cover_calibration,
    async_remove_cover_profile,
    async_set_cover_calibration,
    async_set_cover_profile,
    cover_calibration_data,
    cover_profile_data,
    merged_profiles,
    resolve_cover,
    stored_calibrations,
    stored_profiles,
)
from custom_components.myhome.const import (
    ATTR_CALIBRATION_SOURCE,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_UNIQUE_ID,
    CONF_HEIGHT,
    CONF_KEYS_FROM_FILE,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_OVERRIDES,
    CONF_PROFILE,
    CONF_RAW,
    CONF_REFERENCE_HEIGHT,
    CONF_ROLL,
    CONF_SLAT_TIME,
    CONF_SOURCE,
    CONF_START_DELAY,
    CONF_STOP_LATENCY,
    DOMAIN,
    SUBENTRY_COVER_CALIBRATION,
    SUBENTRY_COVER_PROFILE,
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
        (StoredCalibration(UNIQUE_ID, height=150.0), {}, "guided"),
        (StoredCalibration(UNIQUE_ID, profile="tall"), {"tall": PROFILE}, "guided"),
    ],
)
def test_the_source_says_where_the_numbers_came_from(
    calibration: StoredCalibration | None, profiles: dict, expected: str
) -> None:
    """Three answers, and the entity publishes whichever applies.

    A shutter whose times came from the guided flow looks exactly like one whose times
    were typed into the file, and the difference is the first thing to establish when
    one of them stops where it should not.
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
# The subentries themselves
# --------------------------------------------------------------------------------------
def _profile_subentry(name: str = "tall", **overrides: Any) -> ConfigSubentryData:
    data = cover_profile_data(
        name,
        reference_height=195.0,
        opening_time=22.3,
        closing_time=21.7,
        slat_time=4.7,
        opening_roll=2.12,
        closing_roll=1.69,
        raw={"presses": 3},
    )
    data.update(overrides)
    return ConfigSubentryData(
        data=data,
        subentry_type=SUBENTRY_COVER_PROFILE,
        title=name,
        unique_id=f"{SUBENTRY_COVER_PROFILE}-{name}",
    )


def _calibration_subentry(**kwargs: Any) -> ConfigSubentryData:
    data = cover_calibration_data(UNIQUE_ID, **kwargs)
    return ConfigSubentryData(
        data=data,
        subentry_type=SUBENTRY_COVER_CALIBRATION,
        title="Hallway Shutter",
        unique_id=f"{SUBENTRY_COVER_CALIBRATION}-{UNIQUE_ID}",
    )


def test_the_stored_shapes_are_read_back_as_they_were_written(hass: HomeAssistant) -> None:
    """What the flow writes is what the resolution reads: one schema, in one place."""
    entry_subentries = {}
    for data in (_profile_subentry(), _calibration_subentry(profile="tall", height=150.0)):
        subentry = ConfigSubentry(**data)
        entry_subentries[subentry.subentry_id] = subentry
    entry = type("Entry", (), {"subentries": entry_subentries})()

    profiles = stored_profiles(entry)
    assert sorted(profiles) == ["tall"]
    assert profiles["tall"][CONF_OPENING_ROLL] == 2.12
    assert profiles["tall"][CONF_CLOSING_ROLL] == 1.69
    # `roll` is the fallback of the two, and the one the height scaling reads: the
    # closing one, which measures the length of fabric on the tube.
    assert profiles["tall"][CONF_ROLL] == 1.69
    # Never measured by the flow, so the installation defaults stand.
    assert profiles["tall"][CONF_STOP_LATENCY] == 0.1

    calibrations = stored_calibrations(entry)
    assert list(calibrations) == [UNIQUE_ID]
    assert calibrations[UNIQUE_ID].profile == "tall"
    assert calibrations[UNIQUE_ID].height == 150.0
    assert calibrations[UNIQUE_ID].source == "guided"
    assert calibrations[UNIQUE_ID].measured_at is not None


def test_a_stored_shape_that_is_not_one_is_ignored_rather_than_obeyed(caplog) -> None:
    """Hand-edited storage, or a subentry from a version this one does not know.

    Ignoring it leaves the cover on its file numbers, which is the safe way to be
    wrong; half-reading it would give the shutter a run time of `None`.
    """
    broken = ConfigSubentry(
        data={CONF_NAME: "tall"}, subentry_type=SUBENTRY_COVER_PROFILE, title="tall", unique_id=None
    )
    nameless = ConfigSubentry(
        data={}, subentry_type=SUBENTRY_COVER_CALIBRATION, title="?", unique_id=None
    )
    entry = type(
        "Entry", (), {"subentries": {broken.subentry_id: broken, nameless.subentry_id: nameless}}
    )()
    with caplog.at_level(logging.WARNING):
        assert stored_profiles(entry) == {}
        assert stored_calibrations(entry) == {}
    assert "without a name, an opening time or a reference height" in caplog.text
    assert "names no cover" in caplog.text


def test_two_calibrations_for_one_cover_are_reported(caplog) -> None:
    """Storage should not hold two, and if it does the shutter must not depend on order."""
    first = ConfigSubentry(
        data={CONF_COVER_UNIQUE_ID: UNIQUE_ID, CONF_HEIGHT: 150.0},
        subentry_type=SUBENTRY_COVER_CALIBRATION,
        title="one",
        unique_id=None,
    )
    second = ConfigSubentry(
        data={CONF_COVER_UNIQUE_ID: UNIQUE_ID, CONF_HEIGHT: 160.0},
        subentry_type=SUBENTRY_COVER_CALIBRATION,
        title="two",
        unique_id=None,
    )
    entry = type(
        "Entry", (), {"subentries": {first.subentry_id: first, second.subentry_id: second}}
    )()
    with caplog.at_level(logging.WARNING):
        calibrations = stored_calibrations(entry)
    assert calibrations[UNIQUE_ID].height == 160.0
    assert "Two stored calibrations" in caplog.text


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
# End to end: a cover that reads its subentries at setup
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
        subentries=[
            _calibration_subentry(
                overrides={
                    CONF_OPENING_TIME: 22.3,
                    CONF_CLOSING_TIME: 21.7,
                    CONF_SLAT_TIME: 4.7,
                    CONF_OPENING_ROLL: 2.12,
                    CONF_CLOSING_ROLL: 1.69,
                }
            )
        ],
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
        subentries=[
            _profile_subentry(),
            _calibration_subentry(profile="tall", height=195.0),
        ],
    ):
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == 20.0  # the file's
        # ... and so is the closing time, which the file states by leaving it out: a
        # cover that writes one run time has said both are the same (`_finalize_cover`).
        assert state.attributes["Closing time"] == 20.0
        assert state.attributes["Slat time"] == pytest.approx(4.7)  # the profile's
        assert state.attributes["Opening roll"] == pytest.approx(2.12)  # the profile's
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "guided"


async def test_a_stored_profile_reaches_a_cover_that_names_it_in_the_file(
    hass: HomeAssistant, tmp_path
) -> None:
    """The name clash, end to end: `profile: tall` resolves to the measured one.

    The file defines `tall` and so does a guided calibration; the cover follows the
    guided one, and `Calibration source` says `profile tall` because this particular
    window has no calibration of its own.
    """
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(
        hass, tmp_path, YAML, subentries=[_profile_subentry(**{CONF_OPENING_TIME: 30.0})]
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

    Two subentries with one name would make the namespace of profiles depend on which
    one storage happened to list first.

    Mutation caught: adding instead of updating.
    """
    async with setup_myhome(hass, tmp_path, PLAIN_YAML) as (entry, _commands):
        first = cover_profile_data(
            "tall",
            reference_height=195.0,
            opening_time=22.3,
            closing_time=21.7,
            slat_time=4.7,
            opening_roll=2.12,
            closing_roll=1.69,
        )
        async_set_cover_profile(hass, entry, "tall", first, reload=False)
        second = {**first, CONF_OPENING_TIME: 23.4}
        async_set_cover_profile(hass, entry, "tall", second, reload=False)
        await hass.async_block_till_done()
        profiles = [
            subentry
            for subentry in entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_COVER_PROFILE
        ]
        assert len(profiles) == 1
        assert profiles[0].data[CONF_OPENING_TIME] == 23.4
        assert stored_profiles(entry)["tall"][CONF_OPENING_TIME] == 23.4


async def test_removing_a_calibration_gives_the_cover_back_to_the_file(
    hass: HomeAssistant, tmp_path
) -> None:
    """"Remove calibration" means the shutter goes back to `myhome.yaml`.

    The entity reads its travel model once, in its constructor, so the removal has to
    reload the entry - which is what the store does, and what makes the promise of the
    UX ("you can always undo this") true without a restart.

    Mutation caught: removing the subentry without reloading (the cover would keep the
    calibration until the next restart, which is exactly when the user is watching).
    """
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(
        hass, tmp_path, PLAIN_YAML, subentries=[_calibration_subentry(overrides={CONF_OPENING_TIME: 22.3})]
    ) as (entry, _commands):
        assert hass.states.get(ENTITY).attributes["Opening time"] == 22.3

        assert async_remove_cover_calibration(hass, entry, UNIQUE_ID) is True
        await hass.async_block_till_done()
        # The reload built a new gateway handler, which starts disconnected.
        await set_connected(hass, True)

        assert stored_calibrations(entry) == {}
        state = hass.states.get(ENTITY)
        assert state.attributes["Opening time"] == 20.0
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "yaml"


async def test_removing_what_is_not_there_changes_nothing(hass: HomeAssistant, tmp_path) -> None:
    """A flow that cancels, or a second delete: False, and no reload."""
    async with setup_myhome(hass, tmp_path, PLAIN_YAML) as (entry, _commands):
        assert async_remove_cover_calibration(hass, entry, UNIQUE_ID) is False
        assert async_remove_cover_profile(hass, entry, "tall") is False


async def test_storing_a_calibration_reloads_the_entry(hass: HomeAssistant, tmp_path) -> None:
    """The numbers reach the shutter at once, not at the next restart."""
    calibration_store.reset_name_clash_warnings()
    async with setup_myhome(hass, tmp_path, PLAIN_YAML) as (entry, _commands):
        assert hass.states.get(ENTITY).attributes["Opening time"] == 20.0
        async_set_cover_calibration(
            hass,
            entry,
            UNIQUE_ID,
            cover_calibration_data(UNIQUE_ID, overrides={CONF_SLAT_TIME: 4.7}),
        )
        await hass.async_block_till_done()
        await set_connected(hass, True)
        state = hass.states.get(ENTITY)
        assert state.attributes["Slat time"] == 4.7
        assert state.attributes[ATTR_CALIBRATION_SOURCE] == "guided"
        assert hass.data[DOMAIN][MAC] is not None
