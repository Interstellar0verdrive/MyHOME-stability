"""L-73: the verified precision kept with the cover at save, and when it stops applying."""
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from custom_components.myhome.cover_profiles import get_store, write_profile
from custom_components.myhome.cover_settings import CHECK_FIELDS, COVER_RECORD
from custom_components.myhome.cover_settings_api import overview
from tests.test_cover_calibration_check import verdict
from tests.test_cover_calibration_geometry import geometry as geometry_fixture
from tests.test_cover_calibration_geometry import review
from tests.test_cover_profiles import message
from tests.test_cover_profiles import plant as plant_fixture
from tests.test_panel_cover_calibration import act, measured
from tests.test_panel_cover_calibration import calibration as calibration_fixture

geometry = geometry_fixture
plant = plant_fixture
calibration = calibration_fixture

CLOCK = "custom_components.myhome.cover_settings.dt_util.utcnow"
SAVED = datetime(2026, 10, 10, 12, tzinfo=UTC)
OLD = {"check_cm": 3, "check_measured_cm": 97.0, "check_expected_cm": 100.0, "check_at": "2026-10-01T09:00:00+00:00"}


def record(hass, plant, index=0):
    return get_store(hass, plant.records[index].config_entry_id).data["covers"].get(plant.covers[index].unique_id, {})


def stored(hass, plant, index=0):
    return {key: record(hass, plant, index).get(key) for key in CHECK_FIELDS}


def seed(hass, plant, index=0, check=OLD):
    """A check kept from an earlier save (no revision change: as loaded from storage)."""
    store = get_store(hass, plant.records[index].config_entry_id)
    store.data["covers"].setdefault(plant.covers[index].unique_id, {"overrides": {}}).update(check)


async def listed(hass, plant, index=0):
    covers = (await overview(hass, plant.records[index].config_entry_id))["covers"]
    item = next(cover for cover in covers if cover["entity_id"] == plant.records[index].entity_id)
    return {key: item[key] for key in CHECK_FIELDS}


async def test_a_base_calibration_saved_with_its_check_keeps_the_gap_the_heights_and_the_date(hass, geometry):
    cal = geometry
    check = await verdict(cal, reading_offset=-5.4)
    assert check["deviation_cm"] == -5
    with patch(CLOCK, return_value=SAVED):
        await act(cal, "save", name="Checked")
    expected = {"check_cm": 5, "check_measured_cm": check["measured_cm"], "check_expected_cm": check["expected_cm"],
                "check_at": "2026-10-10T12:00:00+00:00"}
    assert stored(hass, cal.plant) == expected
    assert COVER_RECORD(record(hass, cal.plant))  # What is stored is what the store loads back.
    assert await listed(hass, cal.plant) == expected


async def test_a_base_calibration_saved_without_a_completed_check_clears_the_old_one(hass, geometry):
    cal = geometry
    seed(hass, cal.plant)
    await review(cal)
    await act(cal, "save", name="Unchecked")
    assert stored(hass, cal.plant) == dict.fromkeys(CHECK_FIELDS)
    assert await listed(hass, cal.plant) == dict.fromkeys(CHECK_FIELDS)
    assert "travel_cm" in record(hass, cal.plant), "the rest of the record stays"


async def test_a_times_only_save_clears_the_check(hass, calibration):
    cal = calibration
    seed(hass, cal.plant)
    await measured(cal)
    await act(cal, "save", name="Times")
    assert stored(hass, cal.plant) == dict.fromkeys(CHECK_FIELDS)
    # Nothing else was kept for the cover: its record goes, as before.
    assert record(hass, cal.plant) == {}


async def test_a_cancelled_session_changes_nothing(hass, geometry):
    cal = geometry
    seed(hass, cal.plant)
    await verdict(cal, reading_offset=7)
    await act(cal, "cancel")
    assert stored(hass, cal.plant) == OLD


async def test_an_assigned_or_copied_profile_never_carries_the_check(hass, plant):
    first = await write_profile(hass, message(plant))
    seed(hass, plant, 0)
    seed(hass, plant, 1, {**OLD, "check_cm": 1})
    # The other cover follows the checked cover's profile: its own old check describes other times, and goes.
    await write_profile(hass, message(plant, 1, index=1, action="assign", profile_id=first["assigned_profile_id"]))
    assert stored(hass, plant, 1) == dict.fromkeys(CHECK_FIELDS)
    assert stored(hass, plant, 0) == OLD, "the measured cover keeps its own"
    copied = await write_profile(hass, message(plant, 2, index=1, copy_from_profile_id=first["assigned_profile_id"],
                                 profile={"name": "Copy", "opening_time": 42.5, "closing_time": 50}))
    assert copied["assigned_profile_id"] != first["assigned_profile_id"]
    assert stored(hass, plant, 1) == dict.fromkeys(CHECK_FIELDS)
    assert await listed(hass, plant, 1) == dict.fromkeys(CHECK_FIELDS)


async def test_changes_that_keep_the_cover_s_times_keep_the_check_and_new_times_clear_it(hass, plant):
    first = await write_profile(hass, message(plant))
    profile_id = first["assigned_profile_id"]
    seed(hass, plant)
    # A rename and a new travel: the same times, the check still describes them.
    await write_profile(hass, message(plant, 1, profile_id=profile_id, profile={"name": "Renamed", "travel_time": 42.5}))
    await write_profile(hass, message(plant, 2, action="travel", travel_cm=180))
    assert stored(hass, plant) == OLD
    # Times typed by hand: the check no longer applies.
    await write_profile(hass, message(plant, 3, action="overrides", overrides={"opening": 40}))
    assert stored(hass, plant) == dict.fromkeys(CHECK_FIELDS)
    seed(hass, plant)
    await write_profile(hass, message(plant, 4, profile_id=profile_id, profile={"name": "Renamed", "opening_time": 41, "closing_time": 42.5}))
    assert stored(hass, plant) == dict.fromkeys(CHECK_FIELDS)


async def test_an_old_record_without_the_fields_has_no_check(hass, plant):
    assert COVER_RECORD({"overrides": {}, "travel_cm": 150}) == {"overrides": {}, "travel_cm": 150}
    await write_profile(hass, message(plant, action="travel", travel_cm=150))
    assert await listed(hass, plant) == dict.fromkeys(CHECK_FIELDS)


@pytest.mark.parametrize("bad", [{"check_cm": -1}, {"check_cm": 2.5}, {"check_measured_cm": -3}])
def test_the_stored_check_is_validated(bad):
    with pytest.raises(Exception):
        COVER_RECORD({"overrides": {}, **OLD, **bad})
