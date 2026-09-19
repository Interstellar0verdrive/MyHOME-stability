"""The ported arithmetic of the guided calibration gives the dialog's numbers exactly.

`calibration_measure.py` is a port, not a rewrite: the dialog (`calibration_flow.py`)
stays as 0.5.0 shipped it, and the panel's calibration session computes with the
functions ported from its methods. Two copies of one arithmetic are only safe while
something keeps them equal, and this is that something.

Every test builds a real `MyHomeOptionsFlowHandler` on a loaded entry, sets the
conversation's state by hand (`_path`, `_measured`, `_profile`, `_measured_name`,
`_pending`, `_report`, `_cover_unique_id`, `_yaml_key`, `_cover`) and asks each method
and the function ported from it the same question, over a matrix of conversations: the
three paths, the three scopes of a correction, a late press, a taped gap, a travel
nobody knows and a profile deleted under the conversation's feet. Everything is
deterministic, so the comparison is exact equality - including an exception, when the
method raises one.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import pytest
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.myhome import calibration_flow, calibration_measure
from custom_components.myhome.calibration import PressTiming, RunReport
from custom_components.myhome.calibration_flow import (
    FIELD_MEASURED_CM,
    PATH_FIRST,
    PATH_PROFILE,
    PATH_REFINE,
    QUARTER_RUN,
    THREE_QUARTER_RUN,
    VERIFY_RUN,
    VERIFY_RUN_PROFILE,
    _Measured,
    _Result,
)
from custom_components.myhome.calibration_measure import (
    Measured,
    Result,
    accept_measurement,
    adopted_timings,
    assigned_profile,
    deviation,
    expected_cm,
    fit_both,
    fits,
    known_height,
    merged_with,
    model_values,
    own_height,
    profile_still_wins,
    raw,
    replaced_and_kept,
    result,
    slat_from_gap,
    suggested_name,
    values_in_use,
)
from custom_components.myhome.calibration_store import (
    async_get_store,
    cover_profile_data,
    merged_profiles,
)
from custom_components.myhome.config_flow import MyHomeOptionsFlowHandler
from custom_components.myhome.const import (
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_PROFILES,
    CONF_COVERS_FROM_FILE,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PROFILE,
    CONF_PROFILE_WINS,
    CONF_SLAT_TIME,
    DIRECTION_CLOSE,
    DIRECTION_OPEN,
    DOMAIN,
)

from .helpers_calibration import (
    CLOSING,
    CURTAIN_DOWN,
    CURTAIN_UP,
    HEIGHT,
    OPENING,
    ROLL_DOWN,
    SLAT,
    ascent_cm,
    descent_cm,
)
from .helpers_core import MAC
from .helpers_platforms import device_config, entity_object, setup_myhome

DEVICE_KEY = "2-81"
UNIQUE_ID = f"{MAC}-{DEVICE_KEY}"
COVER_NAME = "Hallway Shutter"
# The key the file knows the cover by, deliberately not the entity's object id: the
# snippet of the summary is built from the first, and a port that took the second would
# pass every case that does not look.
YAML_KEY = "front_hall_roller"

# The reference window with its own run times in the file and a profile of the same
# kind beside it, which is where paths B and C start from.
#
# `tall` is deliberately *not* the file's own numbers, and states the two rolls apart
# rather than one `roll:`. A profile that repeats what the file writes for this cover
# makes the two indistinguishable, and a profile whose rolls are equal makes the two
# directions indistinguishable: either way a difference between the dialog and the port
# would land on identical numbers and go unseen (review B1, R4a).
TALL_OPENING = 23.1
TALL_CLOSING = 22.4
TALL_SLAT = 5.0
TALL_ROLL_UP = 2.2
TALL_ROLL_DOWN = 1.6
YAML = f"""
gateway:
  mac: {MAC}
  cover:
    {YAML_KEY}:
      where: '81'
      name: {COVER_NAME}
      opening_time: {OPENING}
      closing_time: {CLOSING}
      slat_time: {SLAT}
      roll: {ROLL_DOWN}
      height: {HEIGHT}
  cover_profiles:
    tall:
      reference_height: {HEIGHT}
      opening_time: {TALL_OPENING}
      closing_time: {TALL_CLOSING}
      slat_time: {TALL_SLAT}
      opening_roll: {TALL_ROLL_UP}
      closing_roll: {TALL_ROLL_DOWN}
"""
# ...and the same with no travel anywhere for the cover: the one case every function
# has to answer without a height.
NO_HEIGHT_YAML = YAML.replace(f"      height: {HEIGHT}\n", "")
# ...and one where the *file* says this window follows a profile, while the record
# assigns it another one. The two names differ, and so do the two reference heights, so
# the order `known_height` reads them in is visible instead of being a coin landing the
# same way twice (review B1, R4c).
PROFILE_IN_FILE_YAML = NO_HEIGHT_YAML.replace(
    f"      name: {COVER_NAME}\n",
    f"      name: {COVER_NAME}\n      profile: short\n",
).replace(
    "  cover_profiles:\n",
    "  cover_profiles:\n"
    "    short:\n"
    "      reference_height: 150.0\n"
    "      opening_time: 18.0\n"
    "      closing_time: 17.5\n"
    "      slat_time: 3.8\n"
    "      roll: 1.9\n",
)

# A profile of the integration's own store next to the file's, so that the namespaces
# are merged the way a cover merges them before either side reads a profile.
SHORT_PROFILE = cover_profile_data(
    "short",
    reference_height=150.0,
    opening_time=18.4,
    closing_time=17.9,
    slat_time=3.9,
    opening_roll=1.95,
    closing_roll=1.58,
    measured_at="2026-01-01T00:00:00+00:00",
)


def _store(covers: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"profiles": {"short": SHORT_PROFILE}, "covers": dict(covers or {})}


def _press(slat: float | None, run: float) -> PressTiming:
    return PressTiming(slat, run)


def _report(direction: str, fraction: float, seconds: float) -> RunReport:
    now = dt_util.utcnow()
    return RunReport(
        motor_start=now,
        stop_written=now,
        motor_seconds=seconds,
        planned_seconds=seconds,
        fraction=fraction,
        direction=direction,
    )


# Readings of the reference window, a little off where a real tape would be.
HALF_DOWN = (0.5 * CURTAIN_DOWN, descent_cm(0.5) + 0.8)
HALF_UP = (SLAT + 0.5 * CURTAIN_UP, ascent_cm(0.5) - 0.6)
PRECISE_DOWN = [
    (QUARTER_RUN * CURTAIN_DOWN, descent_cm(QUARTER_RUN) + 0.4),
    (THREE_QUARTER_RUN * CURTAIN_DOWN, descent_cm(THREE_QUARTER_RUN) - 0.9),
]
PRECISE_UP = [
    (SLAT + QUARTER_RUN * CURTAIN_UP, ascent_cm(QUARTER_RUN) + 1.1),
    (SLAT + THREE_QUARTER_RUN * CURTAIN_UP, ascent_cm(THREE_QUARTER_RUN) - 0.3),
]


@dataclass
class Case:
    """One conversation, as the dialog would hold it on its summary screen."""

    path: str
    measured: dict[str, Any]
    yaml: str = YAML
    covers: dict[str, Any] = field(default_factory=dict)
    profile: str | None = None
    measured_name: str | None = None
    pending: tuple[str, float] | None = None
    report: RunReport | None = None
    yaml_key: str = YAML_KEY
    with_cover: bool = True
    # "Solo la calibrazione approfondita": the times are taken off the model in use
    # before anything else is asked, by the method on one side and the function on the
    # other.
    adopt: bool = False


def _cases() -> dict[str, Case]:
    base = {
        "height": HEIGHT,
        "height_measured": True,
        "opening": _press(SLAT, OPENING + 0.4),
        "closing": _press(None, CLOSING + 0.3),
        "slat_seconds": SLAT,
        "descent": [HALF_DOWN],
        "ascent": [HALF_UP],
    }
    return {
        "a_basic": Case(PATH_FIRST, dict(base), measured_name="tall_new"),
        "a_with_gap": Case(
            PATH_FIRST,
            {
                **base,
                "opening": _press(SLAT + 0.2, OPENING + 0.4),
                "slat_seconds": SLAT + 0.2,
                "lift_run_sec": SLAT + 0.6,
                "lift_gap_cm": 4.0,
            },
            # No name chosen and no key in the file: both fall back to the entity id.
            yaml_key="",
        ),
        "a_late_press": Case(
            PATH_FIRST,
            {
                **base,
                "opening": _press(SLAT + 1.1, OPENING + 0.4),
                "slat_seconds": SLAT + 1.1,
                "lift_run_sec": SLAT + 1.5,
                "lift_gap_cm": 9.0,
                "lift_late": True,
            },
            measured_name="tall_new",
            # ...and no cover object at all, which is the moment after Save.
            with_cover=False,
            yaml_key="",
        ),
        "a_thorough": Case(
            PATH_FIRST,
            {
                **base,
                "descent": [HALF_DOWN, *PRECISE_DOWN],
                "ascent": [HALF_UP, *PRECISE_UP],
                "precise": True,
                "deviation": 0.8,
                "verify_fraction": VERIFY_RUN,
            },
            measured_name="tall_new",
            pending=(DIRECTION_CLOSE, VERIFY_RUN),
            report=_report(DIRECTION_CLOSE, VERIFY_RUN, VERIFY_RUN * CURTAIN_DOWN + 0.2),
            covers={UNIQUE_ID: {"overrides": {CONF_SLAT_TIME: 5.1}, "source": "guided"}},
        ),
        "b_without_check": Case(
            PATH_PROFILE,
            {"height": 150.0, "height_measured": True},
            profile="tall",
            covers={
                UNIQUE_ID: {
                    "overrides": {CONF_OPENING_ROLL: 2.3, CONF_CLOSING_ROLL: 1.7},
                    "height": 190.0,
                    "source": "guided",
                }
            },
        ),
        "b_with_check": Case(
            PATH_PROFILE,
            {
                "height": 150.0,
                "height_measured": True,
                "deviation": -1.2,
                "verify_fraction": VERIFY_RUN_PROFILE,
            },
            profile="short",
            pending=(DIRECTION_CLOSE, VERIFY_RUN_PROFILE),
            report=_report(DIRECTION_CLOSE, VERIFY_RUN_PROFILE, 7.1),
        ),
        "c_times_only": Case(
            PATH_REFINE,
            {
                "opening": _press(SLAT + 0.3, OPENING + 1.2),
                "closing": _press(None, CLOSING + 0.9),
                "slat_seconds": SLAT + 0.3,
                "lift_run_sec": SLAT + 0.7,
                "lift_gap_cm": 5.0,
            },
            profile="tall",
            covers={
                UNIQUE_ID: {
                    CONF_PROFILE: "tall",
                    CONF_PROFILE_WINS: True,
                    "height": 180.0,
                    "overrides": {CONF_SLAT_TIME: 5.0, CONF_OPENING_ROLL: 2.0},
                    "source": "guided",
                }
            },
        ),
        "c_times_and_rolls": Case(
            PATH_REFINE,
            dict(base),
            profile="short",
            covers={UNIQUE_ID: {"overrides": {CONF_CLOSING_ROLL: 1.5}, "source": "guided"}},
        ),
        "c_thorough_only": Case(
            PATH_REFINE,
            {
                # Carried in from the file, not read off a tape here.
                "height": HEIGHT,
                "descent": list(PRECISE_DOWN),
                "ascent": list(PRECISE_UP),
                "precise": True,
                "deviation": 0.4,
                "verify_fraction": VERIFY_RUN,
            },
            covers={
                UNIQUE_ID: {
                    CONF_PROFILE: "tall",
                    CONF_PROFILE_WINS: True,
                    "overrides": {CONF_OPENING_ROLL: 2.05},
                    "source": "guided",
                }
            },
            pending=(DIRECTION_CLOSE, VERIFY_RUN),
            report=_report(DIRECTION_CLOSE, VERIFY_RUN, 6.9),
            adopt=True,
        ),
        "c_no_travel": Case(
            PATH_REFINE,
            {
                "opening": _press(SLAT, OPENING + 0.6),
                "closing": _press(None, CLOSING + 0.2),
                "slat_seconds": SLAT,
                "lift_run_sec": SLAT + 0.5,
                "lift_gap_cm": 3.0,
            },
            yaml=NO_HEIGHT_YAML,
            profile="tall",
            pending=(DIRECTION_OPEN, 0.5),
        ),
        "a_no_travel": Case(
            PATH_FIRST,
            {**base, "height": None, "height_measured": False},
            yaml=NO_HEIGHT_YAML,
            measured_name="tall_new",
            report=_report(DIRECTION_CLOSE, VERIFY_RUN, 6.8),
        ),
        "c_height_from_profile": Case(
            # Nobody has ever measured this window and the file says nothing about its
            # travel: the only thing left that knows one is the profile the record
            # assigns it, which is the last step of `known_height` and the one no other
            # conversation of the matrix reaches (review B1, R4b).
            PATH_REFINE,
            {
                "opening": _press(SLAT, OPENING + 0.5),
                "closing": _press(None, CLOSING + 0.4),
                "slat_seconds": SLAT,
            },
            yaml=NO_HEIGHT_YAML,
            profile="tall",
            covers={
                UNIQUE_ID: {CONF_PROFILE: "tall", CONF_PROFILE_WINS: True, "source": "guided"}
            },
        ),
        "c_profile_in_file": Case(
            # The file assigns "short" to this window and the record assigns "tall":
            # the record is the one that decides, on every reader (review B1, R4c). And
            # no key in the file with a profile name already chosen, so the summary's
            # snippet has to fall back to the entity id rather than to that name
            # (review B1, R4d).
            PATH_REFINE,
            {
                "opening": _press(SLAT + 0.1, OPENING + 0.8),
                "closing": _press(None, CLOSING + 0.5),
                "slat_seconds": SLAT + 0.1,
            },
            yaml=PROFILE_IN_FILE_YAML,
            covers={UNIQUE_ID: {CONF_PROFILE: "tall", "source": "guided"}},
            measured_name="tall_new",
            yaml_key="",
        ),
        "a_gap_without_run": Case(
            # A gap taped with no lift-off run behind it, which is the guard of
            # `slat_from_gap` rather than its formula (review B1, R4e).
            PATH_FIRST,
            {
                **base,
                "opening": _press(SLAT + 0.4, OPENING + 0.4),
                "slat_seconds": SLAT + 0.4,
                "lift_gap_cm": 6.0,
            },
            measured_name="tall_new",
        ),
        "b_profile_gone": Case(
            PATH_PROFILE,
            {"height": 150.0, "height_measured": True, "verify_fraction": VERIFY_RUN_PROFILE},
            profile="gone",
            pending=(DIRECTION_CLOSE, VERIFY_RUN_PROFILE),
            report=_report(DIRECTION_CLOSE, VERIFY_RUN_PROFILE, 7.3),
            covers={UNIQUE_ID: {CONF_PROFILE: "gone", "source": "guided"}},
        ),
    }


CASES = _cases()


# --------------------------------------------------------------------------------------
# Comparing
# --------------------------------------------------------------------------------------
def outcome(call: Callable[[], Any]) -> tuple[Any, ...]:
    """What a call answered, or what it raised: parity covers the refusals too."""
    try:
        value = call()
    except Exception as err:  # noqa: BLE001 - whatever it is, both sides must agree
        return ("raised", type(err), str(err))
    return ("returned", comparable(value))


def comparable(value: Any) -> Any:
    """A `_Measured`/`Measured` or `_Result`/`Result` as the plain values it holds."""
    if isinstance(value, _Measured | Measured):
        return ("measured", {f.name: getattr(value, f.name) for f in fields(value)}, value.slat_time)
    if isinstance(value, _Result | Result):
        return ("result", {f.name: getattr(value, f.name) for f in fields(value)})
    if isinstance(value, tuple):
        return tuple(comparable(item) for item in value)
    return value


@dataclass
class Conversation:
    """The dialog with its state set by hand, and the same inputs for the functions."""

    flow: MyHomeOptionsFlowHandler
    case: Case
    measured: Measured
    device: dict[str, Any]
    # ...and the same cover as `myhome.yaml` wrote it, which is a different dictionary:
    # see `test_the_file_s_own_copy_of_the_cover_answers_the_same`.
    device_from_file: Mapping[str, Any]
    profiles: dict[str, Mapping[str, Any]]
    record: Any
    entity_id: str

    def model(self) -> dict[str, float] | None:
        return model_values(
            path=self.case.path,
            measured=self.measured,
            profiles=self.profiles,
            profile=self.case.profile,
        )

    def values(self) -> dict[str, float] | None:
        return values_in_use(
            unique_id=UNIQUE_ID,
            device=self.device,
            profiles=self.profiles,
            record=self.record,
            profile=self.case.profile,
            height=self.measured.height,
        )

    def height_known(self) -> float | None:
        return known_height(record=self.record, device=self.device, profiles=self.profiles)

    def result(self) -> Result:
        return result(
            path=self.case.path,
            measured=self.measured,
            measured_name=self.case.measured_name,
            profile=self.case.profile,
            profiles=self.profiles,
            entity_id=self.entity_id,
            yaml_key=self.case.yaml_key,
            height_known=self.height_known(),
        )


async def _converse(hass: HomeAssistant, entry: Any, case: Case) -> Conversation:
    """A real options flow on `entry`, in the middle of the conversation `case` is."""
    flow = MyHomeOptionsFlowHandler()
    flow.hass = hass
    flow.handler = entry.entry_id
    store = await async_get_store(hass, entry)
    flow._store_ref = store
    cover = entity_object(hass, COVER, DEVICE_KEY) if case.with_cover else None
    flow._cover = cover
    flow._cover_unique_id = UNIQUE_ID
    flow._cover_label = COVER_NAME
    flow._yaml_key = case.yaml_key
    flow._path = case.path
    flow._profile = case.profile
    flow._measured_name = case.measured_name
    flow._pending = case.pending
    flow._report = case.report
    flow._measured = _Measured(**_copied(case.measured))
    # The functions' inputs are read from where the dialog reads them from, not
    # through the dialog: the file's profiles merged with the stored ones, the cover's
    # validated configuration, its stored record.
    yaml_profiles = hass.data[DOMAIN][MAC].get(CONF_COVER_PROFILES) or {}
    conversation = Conversation(
        flow=flow,
        case=case,
        measured=Measured(**_copied(case.measured)),
        device=device_config(hass, COVER, DEVICE_KEY),
        device_from_file=hass.data[DOMAIN][MAC][CONF_COVERS_FROM_FILE][DEVICE_KEY],
        profiles=merged_profiles(yaml_profiles, store.profiles),
        record=store.calibration(UNIQUE_ID),
        entity_id=cover.entity_id if cover is not None else "",
    )
    if case.adopt:
        assert flow._adopt_the_model_in_use() is True
        adopted = adopted_timings(conversation.measured, conversation.values())
        assert adopted is not None
        assert comparable(adopted) == comparable(flow._measured)
        conversation.measured = adopted
    return conversation


def _copied(values: Mapping[str, Any]) -> dict[str, Any]:
    """The case's measurements, with lists of their own on each side."""
    return {key: list(value) if isinstance(value, list) else value for key, value in values.items()}


@pytest.fixture(params=sorted(CASES))
def case(request: pytest.FixtureRequest) -> Case:
    return CASES[request.param]


@pytest.fixture
async def conversation(hass: HomeAssistant, tmp_path: Path, case: Case):
    async with setup_myhome(hass, tmp_path, case.yaml, calibration=_store(case.covers)) as (entry, _):
        yield await _converse(hass, entry, case)


# --------------------------------------------------------------------------------------
# The matrix
# --------------------------------------------------------------------------------------
async def test_the_matrix_covers_every_conversation_the_plan_names() -> None:
    """Ten conversations at least, each of the ones the plan asks for among them."""
    assert len(CASES) >= 10
    paths = {case.path for case in CASES.values()}
    assert paths == {PATH_FIRST, PATH_PROFILE, PATH_REFINE}
    assert any(case.adopt for case in CASES.values())
    assert any(case.measured.get("lift_late") for case in CASES.values())
    assert any(case.measured.get("lift_gap_cm") for case in CASES.values())
    assert any(not case.measured.get("height") for case in CASES.values())
    assert any(case.profile == "gone" for case in CASES.values())
    # ...and the branches the first twelve conversations all happened to miss, each of
    # which a wrong port could have taken without any of them noticing (review B1, R4).
    assert any(case.yaml is PROFILE_IN_FILE_YAML for case in CASES.values())
    assert any(
        case.path != PATH_FIRST and not case.yaml_key and case.measured_name
        for case in CASES.values()
    )
    assert any(
        case.measured.get("lift_gap_cm") and not case.measured.get("lift_run_sec")
        for case in CASES.values()
    )


async def test_the_model_in_use_and_the_known_travel(conversation: Conversation) -> None:
    """`_values_in_use`, `_known_height` and `_adopt_the_model_in_use`."""
    c = conversation
    flow = c.flow
    assert outcome(flow._values_in_use) == outcome(c.values)
    assert outcome(lambda: flow._known_height(UNIQUE_ID)) == outcome(c.height_known)
    # The adoption, on a fresh copy of the case's measurements on each side (the method
    # writes into the conversation, so it is given one of its own and then put back).
    before = flow._measured
    flow._measured = _Measured(**_copied(c.case.measured))
    adopted_by_the_dialog = flow._adopt_the_model_in_use()
    adopted = adopted_timings(Measured(**_copied(c.case.measured)), c.values())
    assert adopted_by_the_dialog is (adopted is not None)
    if adopted is not None:
        assert comparable(adopted) == comparable(flow._measured)
    flow._measured = before


async def test_the_adopted_times_come_on_readings_of_their_own(
    conversation: Conversation,
) -> None:
    """`adopted_timings` hands back a measurement that shares nothing with its argument.

    The dialog's method writes into the conversation it already has, so the question
    never comes up there; the function returns a copy, and a copy that shared the very
    lists the readings are appended to would grow the caller's own measurement behind
    its back - a session that keeps the one it started from (an undo, the snapshot
    before the thorough calibration) would never see it happen (review B1, R2).
    """
    c = conversation
    adopted = adopted_timings(c.measured, c.values())
    assert adopted is not None
    assert adopted.descent is not c.measured.descent
    assert adopted.ascent is not c.measured.ascent
    before = (list(c.measured.descent), list(c.measured.ascent))
    adopted.descent.append((1.0, 2.0))
    adopted.ascent.append((3.0, 4.0))
    assert (c.measured.descent, c.measured.ascent) == before


async def test_the_travel_and_the_profile_this_window_is_told_it_has(
    conversation: Conversation,
) -> None:
    """`_own_height` and `_assigned_profile`, which a correction starts from.

    They are the two steps `_known_height` is built out of, and a correction uses each
    of them alone: the travel it opens the conversation on must be **this** window's
    and not the reference height of the profile it follows (`async_step_path_c`,
    :1826), and the profile its form opens on is the one the window is assigned
    today. Folding them into `known_height` alone would leave the session to write
    either rule out again.
    """
    c = conversation
    flow = c.flow
    assert own_height(record=c.record, device=c.device) == flow._own_height(UNIQUE_ID)
    assert assigned_profile(record=c.record, device=c.device) == flow._assigned_profile(UNIQUE_ID)
    # ...and on the file's own copy of the cover as well, which is the dictionary the
    # session passes (review B1, R3).
    assert own_height(record=c.record, device=c.device_from_file) == flow._own_height(UNIQUE_ID)
    assert assigned_profile(
        record=c.record, device=c.device_from_file
    ) == flow._assigned_profile(UNIQUE_ID)


async def test_the_file_s_own_copy_of_the_cover_answers_the_same(
    conversation: Conversation,
) -> None:
    """The two shapes of a cover's configuration give one answer, over the whole matrix.

    The dialog reads the validated dict out of `hass.data` (`_cover_config`), into which
    `cover._merge_the_travel_model` has already written the resolved numbers - the
    record's `height:` and `profile:` among them. A session must resolve against the
    untouched copy taken of the cover block before the platforms were forwarded
    (`CONF_COVERS_FROM_FILE`, `cover.py:878`). The two dictionaries are therefore not
    interchangeable, and this holds the two functions that read one of them to the same
    answer on both, whichever the controller ends up passing (review B1, R3).
    """
    c = conversation
    assert known_height(
        record=c.record, device=c.device_from_file, profiles=c.profiles
    ) == c.height_known()
    assert (
        values_in_use(
            unique_id=UNIQUE_ID,
            device=c.device_from_file,
            profiles=c.profiles,
            record=c.record,
            profile=c.case.profile,
            height=c.measured.height,
        )
        == c.values()
    )


async def test_the_model_in_use_of_a_cover_the_file_no_longer_has(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    """A window that is not configured any more has no model, whatever the store holds.

    `_values_in_use` looks the cover up in the file's own covers and answers `None` when
    it is not among them, before the store is read at all. The port takes that same
    dictionary as an argument, so the empty one has to mean the same thing - and the
    record deliberately carries a complete set of numbers here, which is what a
    resolution without the guard would hand back as a model (review B1, R4f).
    """
    gone = f"{MAC}-9-9"
    covers = {
        gone: {
            "overrides": {
                CONF_OPENING_TIME: 20.0,
                CONF_CLOSING_TIME: 19.5,
                CONF_SLAT_TIME: 4.0,
                CONF_OPENING_ROLL: 2.0,
                CONF_CLOSING_ROLL: 1.7,
            },
            "height": 200.0,
            "source": "guided",
        }
    }
    async with setup_myhome(hass, tmp_path, YAML, calibration=_store(covers)) as (entry, _):
        store = await async_get_store(hass, entry)
        flow = MyHomeOptionsFlowHandler()
        flow.hass = hass
        flow.handler = entry.entry_id
        flow._store_ref = store
        flow._cover_unique_id = gone
        flow._measured = _Measured()
        flow._profile = None
        yaml_profiles = hass.data[DOMAIN][MAC].get(CONF_COVER_PROFILES) or {}
        assert flow._values_in_use() is None
        assert (
            values_in_use(
                unique_id=gone,
                device={},
                profiles=merged_profiles(yaml_profiles, store.profiles),
                record=store.calibration(gone),
                profile=None,
                height=None,
            )
            is None
        )


async def test_the_fit(conversation: Conversation) -> None:
    """`_fits`, `_fit_both` and `_slat_from_gap`, and the model the check asks about."""
    c = conversation
    flow = c.flow
    assert outcome(flow._fits) == outcome(lambda: fits(c.measured))
    for slat in (c.measured.slat_time, SLAT, SLAT + 0.35):
        assert outcome(lambda slat=slat: flow._fit_both(slat)) == outcome(
            lambda slat=slat: fit_both(c.measured, slat)
        )
    for raw_slat, roll, height, curtain in (
        (c.measured.slat_time, 2.1, HEIGHT, CURTAIN_UP),
        (SLAT + 0.5, 1.8, 150.0, 14.0),
        (SLAT, 2.1, None, CURTAIN_UP),
        (SLAT, 2.1, HEIGHT, 0.0),
    ):
        assert flow._slat_from_gap(raw_slat, roll=roll, height=height, curtain=curtain) == slat_from_gap(
            c.measured, raw_slat, roll=roll, height=height, curtain=curtain
        )
    assert outcome(flow._model_values) == outcome(c.model)


async def test_the_tape(conversation: Conversation) -> None:
    """`_expected_cm`, `_accept_measurement` and `_deviation`, over several readings."""
    c = conversation
    flow = c.flow
    for pending in (
        c.case.pending,
        None,
        (DIRECTION_CLOSE, QUARTER_RUN),
        (DIRECTION_OPEN, THREE_QUARTER_RUN),
    ):
        flow._pending = pending
        assert outcome(flow._expected_cm) == outcome(
            lambda pending=pending: expected_cm(
                pending=pending, height=c.measured.height, model=c.model()
            )
        )
    flow._pending = c.case.pending
    for typed in (
        # What the dialog's form hands over: text, as typed, in either notation.
        "85,5",
        "85.5",
        42,
        0,
        "",
        "abc",
        "1.234,5",
        "-1",
        "150",
        "195",
        "400",
        None,
        # ...and what a WebSocket command will hand over: JSON numbers, which arrive as
        # floats and never went through a keyboard. The two sides have to agree on them
        # as well - including on the ones neither of them rejects today (review B1, A2
        # and R1): `nan` and `inf` are accepted by both, which is why the session's own
        # boundary has to refuse them before they ever get here.
        85.5,
        195.0,
        195.0000001,
        -0.5,
        float("nan"),
        float("inf"),
    ):
        # Compared as written rather than by value, because `nan` is equal to nothing,
        # itself included, and "both sides answered nan" is exactly what is being said.
        assert repr(flow._accept_measurement({FIELD_MEASURED_CM: typed})) == repr(
            accept_measurement(typed, height=c.measured.height)
        )
    for reading in (0.0, 60.0, 101.5, HEIGHT):
        assert outcome(lambda reading=reading: flow._deviation(reading)) == outcome(
            lambda reading=reading: deviation(
                reading, report=c.case.report, height=c.measured.height, model=c.model()
            )
        )


async def test_the_summary_and_the_save(conversation: Conversation) -> None:
    """`_result`, `_raw`, `_merged_with`, `_replaced_and_kept`, `_profile_still_wins`."""
    c = conversation
    flow = c.flow
    assert outcome(flow._result) == outcome(c.result)
    assert flow._raw() == raw(path=c.case.path, measured=c.measured)
    dialog_result = flow._result()
    ported_result = c.result()
    for record in (c.record, None):
        assert flow._merged_with(record, dialog_result) == merged_with(
            record, ported_result, measured=c.measured
        )
        assert flow._profile_still_wins(record, dialog_result) == profile_still_wins(
            record, ported_result, path=c.case.path, profile=c.case.profile
        )
    # The method reads the record out of the store itself.
    assert flow._replaced_and_kept(dialog_result) == replaced_and_kept(
        c.record, ported_result, measured=c.measured
    )


@pytest.mark.parametrize(
    "entity_id",
    ["cover.hallway_shutter", "cover.front-hall roller", "cover.__", "", "hallway", "cover.Säle_1"],
)
def test_the_suggested_name(entity_id: str) -> None:
    """`_suggested_name`, on ordinary ids and on ones with nothing usable in them."""
    assert suggested_name(entity_id) == calibration_flow._suggested_name(entity_id)


# --------------------------------------------------------------------------------------
# The shape of the port
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(("ported", "original"), [(Measured, _Measured), (Result, _Result)])
def test_the_ported_classes_have_the_dialogs_fields(ported: type, original: type) -> None:
    """Same fields, same order, same defaults: one shape for a measurement."""

    def shape(cls: type) -> list[tuple[str, Any, Any]]:
        return [(f.name, f.default, f.default_factory) for f in fields(cls)]

    assert shape(ported) == shape(original)
    assert shape(Measured) and Measured().slat_time == _Measured().slat_time == 0.0


MODULE = Path(calibration_measure.__file__)


def test_the_module_does_not_import_home_assistant_or_redefine_the_dialogs_constants() -> None:
    """The port depends on the maths and the store, never directly on Home Assistant.

    And whatever the dialog already names at module level is imported from it rather
    than written here a second time, so a threshold changed there is changed here.
    """
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported.append(("." * node.level) + (node.module or ""))
    assert not [name for name in imported if name.split(".")[0] == "homeassistant"], imported
    assigned = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign | ast.AnnAssign)
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name) and not target.id.startswith("__")
    }
    assert not assigned & set(vars(calibration_flow)), assigned & set(vars(calibration_flow))
    # ...and a closed list rather than only "not one of the dialog's names", because a
    # threshold copied here under a *different* name would pass the line above and be
    # exactly the second arithmetic this module exists to prevent (review of B1, A1).
    # Anything added to this set is a number the port owns; there is one, and it is a
    # list of keys rather than a value.
    assert assigned == {"_MODEL_KEYS"}, assigned
