"""The one invariant the whole panel rests on: it agrees with the shutter.

The panel exists to explain a travel model to the person who has to live with it. A
panel that calls a shutter *measured* while the shutter's own `Calibration source`
attribute calls it *adjusted* does not merely have a bug: it teaches the user something
false about their own house, and every screen after that is untrustworthy. So the rule
is not "keep the two in step" - it is that there is only one of them.
`panel_data.async_overview` reads `resolve_cover_config`, which is the very call
`cover.py` makes in the entity's constructor.

This file is what holds that. For a matrix of store states - nothing stored, the file
alone, an assignment, an assignment plus a height, a measurement, a measurement over an
assignment, and an assignment to a profile that is not there any more - it sets the
integration up for real, lets the cover entity build itself, and asserts that the row
the panel would draw and the attributes the entity publishes are the same statement.
Every one of the five origins is exercised, because the interesting failure is not "the
numbers differ" (they would not) but "the *word* differs", which is what a second
implementation of the precedence would produce and what nothing else in the suite would
catch.
"""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.myhome.calibration_store import (
    cover_calibration_data,
    cover_profile_data,
)
from custom_components.myhome.const import (
    ATTR_CALIBRATION_SOURCE,
    CALIBRATION_ORIGIN_ADJUSTED,
    CALIBRATION_ORIGIN_DEFAULTS,
    CALIBRATION_ORIGIN_FILE,
    CALIBRATION_ORIGIN_INHERITED,
    CALIBRATION_ORIGIN_MEASURED,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_UNIQUE_ID,
    CONF_COVERS,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PROFILES,
    CONF_SLAT_TIME,
)
from custom_components.myhome.panel_data import async_overview

from .helpers_core import MAC
from .helpers_platforms import setup_myhome

ENTITY = "cover.hallway_shutter"
DEVICE_KEY = "2-81"
UNIQUE_ID = f"{MAC}-{DEVICE_KEY}"

HEIGHT = 195.0

# The same reference window the rest of the suite measures, and a profile of the same
# shape, so the numbers below are the ones every other file already believes.
PROFILE = cover_profile_data(
    "tall",
    reference_height=HEIGHT,
    opening_time=22.3,
    closing_time=21.7,
    slat_time=4.7,
    opening_roll=2.12,
    closing_roll=1.69,
    reference_cover="Hallway Shutter",
    measured_on=UNIQUE_ID,
    measured_at="2026-09-04T18:12:00+00:00",
)

# A cover the file says nothing about beyond where it is: the "nobody ever said" case.
BARE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      height: {HEIGHT}
"""

# ...and the same cover with its own run times written against it in the file.
FILE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    hallway_shutter:
      where: '81'
      name: Hallway Shutter
      opening_time: 30
      closing_time: 29
      slat_time: 6
      roll: 1.2
      height: {HEIGHT}
"""


def record(**kwargs: Any) -> dict[str, Any]:
    data = cover_calibration_data(UNIQUE_ID, **kwargs)
    return {key: value for key, value in data.items() if key != CONF_COVER_UNIQUE_ID}


def store_file(profiles: dict | None = None, covers: dict | None = None) -> dict:
    return {CONF_PROFILES: profiles or {}, CONF_COVERS: covers or {}}


def the_row(hass: HomeAssistant, entry) -> dict[str, Any]:
    """The one cover of the overview."""
    overview = async_overview(hass, entry)
    assert len(overview["covers"]) == 1
    return overview["covers"][0]


# The seven states, each with the origin the guided flow's own screens call it. The
# names are the ones the plan's parity matrix uses.
MATRIX: list[tuple[str, str, dict[str, Any] | None, str]] = [
    ("nothing stored, nothing written", BARE_YAML, None, CALIBRATION_ORIGIN_DEFAULTS),
    ("the file alone", FILE_YAML, None, CALIBRATION_ORIGIN_FILE),
    (
        "assigned to a profile",
        BARE_YAML,
        store_file(
            profiles={"tall": PROFILE},
            covers={UNIQUE_ID: record(profile="tall", profile_wins=True)},
        ),
        CALIBRATION_ORIGIN_INHERITED,
    ),
    (
        "assigned to a profile, over a file that writes its own times",
        FILE_YAML,
        store_file(
            profiles={"tall": PROFILE},
            covers={UNIQUE_ID: record(profile="tall", profile_wins=True, height=150.0)},
        ),
        CALIBRATION_ORIGIN_INHERITED,
    ),
    (
        "measured, and nothing else",
        FILE_YAML,
        store_file(
            covers={
                UNIQUE_ID: record(
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
        CALIBRATION_ORIGIN_MEASURED,
    ),
    (
        "two numbers of its own over a profile that answers for the rest",
        BARE_YAML,
        store_file(
            profiles={"tall": PROFILE},
            covers={
                UNIQUE_ID: record(
                    profile="tall",
                    profile_wins=True,
                    height=HEIGHT,
                    overrides={CONF_OPENING_TIME: 25.0, CONF_CLOSING_TIME: 24.0},
                )
            },
        ),
        CALIBRATION_ORIGIN_ADJUSTED,
    ),
    (
        # ...and the same state reached from the other side: the two coefficients
        # corrected by hand and every run time still the profile's. `adjusted` is one
        # word for two quite different shutters, and a panel that got the second of
        # them wrong would be wrong about the very screen that produced it.
        "the two rolls of its own over a profile that answers for the times",
        BARE_YAML,
        store_file(
            profiles={"tall": PROFILE},
            covers={
                UNIQUE_ID: record(
                    profile="tall",
                    profile_wins=True,
                    height=HEIGHT,
                    overrides={CONF_OPENING_ROLL: 2.5, CONF_CLOSING_ROLL: 2.6},
                )
            },
        ),
        CALIBRATION_ORIGIN_ADJUSTED,
    ),
    (
        "assigned to a profile that is not defined any more",
        FILE_YAML,
        store_file(covers={UNIQUE_ID: record(profile="gone", profile_wins=True)}),
        CALIBRATION_ORIGIN_FILE,
    ),
]


@pytest.mark.parametrize(
    ("case", "yaml_text", "calibration", "origin"),
    MATRIX,
    ids=[case for case, _yaml, _cal, _origin in MATRIX],
)
async def test_the_panel_and_the_shutter_say_the_same_thing(
    hass: HomeAssistant, tmp_path, case: str, yaml_text: str, calibration, origin: str
) -> None:
    """The row the panel draws and the attributes the entity publishes are one answer.

    `source` is compared verbatim against the attribute rather than reconstructed from
    the origin: it is the string a user reads in the developer tools next to the shutter
    they are looking at in the panel, and the whole point is that those two agree
    character for character. `origin` is compared against the expected word, so that a
    change of precedence has to be *stated* in this table rather than silently adopted
    by a test that only checks the two halves match each other.

    Mutation caught: re-deriving the origin in `panel_data` (any rule that is not
    `resolve_cover`'s own will part company with the attribute on at least the
    `adjusted` and the `missing profile` rows).
    """
    async with setup_myhome(hass, tmp_path, yaml_text, calibration=calibration) as (
        entry,
        _commands,
    ):
        row = the_row(hass, entry)
        state = hass.states.get(ENTITY)
        assert state is not None, case

        attributes = state.attributes
        assert row["origin"] == origin, case
        assert row["source"] == attributes[ATTR_CALIBRATION_SOURCE], case
        # ...and the model itself, key by key, as the entity really runs it. The entity
        # publishes one `Roll` when both directions agree and two when they do not
        # (0.4.2), so the pair is read the way a reader of the attributes would read it.
        assert row["values"][CONF_OPENING_TIME] == attributes["Opening time"], case
        assert row["values"][CONF_CLOSING_TIME] == attributes["Closing time"], case
        rolls = (
            (attributes["Roll"], attributes["Roll"])
            if "Roll" in attributes
            else (attributes["Opening roll"], attributes["Closing roll"])
        )
        assert (row["values"][CONF_OPENING_ROLL], row["values"][CONF_CLOSING_ROLL]) == rolls, case
        assert row["profile"] == attributes.get("Profile"), case
        assert row["height"] == attributes.get("Height"), case


async def test_a_profile_that_is_not_there_any_more_is_said_out_loud(
    hass: HomeAssistant, tmp_path
) -> None:
    """The shutter falls back quietly; the panel is not allowed to.

    `resolve_cover` logs a warning and runs the cover on its own configuration, which is
    the right thing for a shutter to do and the wrong thing for a screen to do: somebody
    reading the panel to find out why a window is slow needs the name that is dangling.

    Mutation caught: listing only the profiles that exist (the row would vanish and the
    cover would appear to follow nothing).
    """
    async with setup_myhome(
        hass,
        tmp_path,
        FILE_YAML,
        calibration=store_file(covers={UNIQUE_ID: record(profile="gone", profile_wins=True)}),
    ) as (entry, _commands):
        overview = async_overview(hass, entry)
        row = overview["covers"][0]
        assert row["profile"] == "gone"
        assert row["profile_missing"] is True
        missing = [item for item in overview["profiles"] if item["name"] == "gone"]
        assert len(missing) == 1
        assert missing[0]["missing"] is True
        assert missing[0]["source"] is None
        assert missing[0]["editable"] is False
        assert missing[0]["followers"] == [UNIQUE_ID]


async def test_an_advanced_shutter_is_not_in_the_panel_at_all(
    hass: HomeAssistant, tmp_path
) -> None:
    """It reports its own position, so there is no travel model to show or to correct.

    Left out exactly where the guided flow leaves it out, and for the same reason. A
    gateway with nothing else says so once instead of drawing an empty page.

    Mutation caught: listing advanced covers (every one of them would offer an
    assignment that no primitive would ever honour).
    """
    yaml_text = (
        BARE_YAML
        + """    skylight:
      where: '82'
      name: Skylight
      advanced: true
"""
    )
    async with setup_myhome(hass, tmp_path, yaml_text) as (entry, _commands):
        overview = async_overview(hass, entry)
        assert [row["name"] for row in overview["covers"]] == ["Hallway Shutter"]
        assert overview["no_basic_covers"] is False

    advanced_only = f"""
gateway:
  mac: {MAC}
  cover:
    skylight:
      where: '82'
      name: Skylight
      advanced: true
"""
    async with setup_myhome(hass, tmp_path, advanced_only) as (entry, _commands):
        overview = async_overview(hass, entry)
        assert overview["covers"] == []
        assert overview["no_basic_covers"] is True
