"""The arithmetic of the guided calibration, without a single screen around it (0.6.0).

The guided calibration has lived in the "Configura" dialog since 0.5.0
(`calibration_flow.GuidedCalibrationMixin`), and in 0.6.0 it also runs inside the panel,
through a session controller of its own. The two must never disagree about a number:
the same presses and the same tape readings have to give the same profile, the same
overrides and the same record whichever of the two collected them.

The dialog is not touched to get there - it is the version the owner's shutters were
calibrated with, and a refactor under 134 screen-by-screen tests is a risk the release
does not need. So the parts of it that *compute* rather than show are ported here, one
function per method, line for line: whatever the method read off `self` (the path, the
measurements, the name, the profiles, the stored record, the cover's configuration) is
an argument here. `tests/test_calibration_measure.py` keeps the two copies equal: it
builds a real options flow, sets its conversation state by hand, and checks every
method against the function ported from it on the same data, to the last digit.

Nothing here talks to Home Assistant, moves a shutter or writes the store. The
constants and tables the dialog already defines are imported from it and never
redefined, so a threshold changed there is changed here too.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from .calibration import (
    FIXED_SCALE_BOUNDS,
    DirectionFit,
    PressTiming,
    RunReport,
    deviation_cm,
    fit_from_run,
    predict_cm,
    slat_time_from_gap,
)
from .calibration_flow import (
    _NOT_A_NAME,
    ERROR_ABOVE_THE_TRAVEL,
    ERROR_NOT_A_NUMBER,
    ERROR_OUT_OF_RANGE,
    EXPECTED_TOLERANCE_CM,
    HALF_RUN,
    PATH_FIRST,
    PATH_PROFILE,
    PATH_REFINE,
    ROUGH_TOLERANCE_CM,
    overrides_yaml,
    parse_number,
    profile_reference_yaml,
)
from .calibration_store import StoredCalibration, profile_overrides, resolve_cover
from .const import (
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_HEIGHT,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PROFILE,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
    DEFAULT_ROLL_SHUTTER,
    DIRECTION_CLOSE,
    DIRECTION_OPEN,
)
from .cover import calibration_yaml
from .validate import derive_cover_from_profile

# The five keys of the travel model, in the order `_values_in_use` asks for them.
_MODEL_KEYS: tuple[str, ...] = (
    CONF_OPENING_TIME,
    CONF_CLOSING_TIME,
    CONF_SLAT_TIME,
    CONF_OPENING_ROLL,
    CONF_CLOSING_ROLL,
)


@dataclass(slots=True)
class Measured:
    """Everything a conversation has collected, and nothing that was saved.

    Ported from `calibration_flow._Measured`: the same fields, the same defaults and the
    same `slat_time`, so that a session and the dialog describe a measurement with one
    shape. See the dialog's class for what each field means and why it is there.
    """

    height: float | None = None
    height_measured: bool = False
    opening: PressTiming | None = None
    closing: PressTiming | None = None
    slat_seconds: float | None = None
    lift_run_sec: float | None = None
    lift_gap_cm: float | None = None
    lift_late: bool = False
    descent: list[tuple[float, float]] = field(default_factory=list)
    ascent: list[tuple[float, float]] = field(default_factory=list)
    deviation: float | None = None
    verify_fraction: float | None = None
    precise: bool = False
    times_adopted: bool = False

    @property
    def slat_time(self) -> float:
        """The slat phase, from the one press that measures it (0 until then).

        Ported from `_Measured.slat_time`.
        """
        if self.opening is not None and self.opening.slat_time is not None:
            return self.opening.slat_time
        return self.slat_seconds or 0.0


@dataclass(slots=True)
class Result:
    """What Save is about to write, and what the summary shows.

    Ported from `calibration_flow._Result`: `profile` is filled by path A alone,
    `overrides` by the paths that measure this window (A and C), and `follows_profile`
    is path B's "this window is one of those".
    """

    yaml: str
    profile: dict[str, float] | None = None
    overrides: dict[str, float] = field(default_factory=dict)
    accuracy_cm: float | None = None
    follows_profile: bool = False


# ------------------------------------------------------------------ names
def suggested_name(entity_id: str) -> str:
    """A profile name the user can accept as it stands, from the cover's entity id.

    Ported from `calibration_flow._suggested_name`.
    """
    object_id = entity_id.split(".", 1)[-1] if entity_id else ""
    cleaned = _NOT_A_NAME.sub("_", object_id).strip("_")
    return cleaned or "shutter"


# ------------------------------------------------------------------ the model in use
def own_height(
    *, record: StoredCalibration | None, device: Mapping[str, Any]
) -> float | None:
    """The travel *this* window is known to have: its record's, else the file's.

    Ported from `CalibrationContextMixin._own_height`. Never a profile's
    `reference_height`, which is another window's travel and would silently scale a
    newly assigned profile by the old one's reference - which is why it is a function
    of its own and not the first two lines of `known_height`: a correction starts the
    conversation from this number, and starting it from a profile's would carry the
    profile's own window into the record of this one.
    """
    if record is not None and record.height:
        return float(record.height)
    if device.get(CONF_HEIGHT):
        return float(device[CONF_HEIGHT])
    return None


def assigned_profile(
    *, record: StoredCalibration | None, device: Mapping[str, Any]
) -> str | None:
    """The profile this window follows today, from wherever it is said.

    Ported from `CalibrationContextMixin._assigned_profile`: the stored assignment
    first, then the `profile:` written in the file - which is what a form offering the
    profiles has to open on, because opening on the first name in the list for a cover
    the file already assigns tells the user something untrue about their own
    installation (0.5.0 v2 review, RISK-1).
    """
    if record is not None and record.profile:
        return str(record.profile)
    name = device.get(CONF_PROFILE)
    return str(name) if name else None


def known_height(
    *,
    record: StoredCalibration | None,
    device: Mapping[str, Any],
    profiles: Mapping[str, Mapping[str, Any]],
) -> float | None:
    """The travel this window is already said to have, from wherever it is said.

    Ported from `CalibrationContextMixin._known_height`, which is `own_height` (the
    record's height, else the file's) and then the reference height of the profile the
    cover follows (`assigned_profile`) - the same two functions this one is built out
    of, for the same reason the dialog builds it out of its two methods. `record` is
    the cover's stored record, `device` its validated configuration, `profiles` both
    namespaces merged (`merged_profiles`).
    """
    own = own_height(record=record, device=device)
    if own is not None:
        return own
    name = assigned_profile(record=record, device=device)
    profile = profiles.get(name or "")
    if profile and profile.get(CONF_REFERENCE_HEIGHT):
        return float(profile[CONF_REFERENCE_HEIGHT])
    return None


def values_in_use(
    *,
    unique_id: str,
    device: Mapping[str, Any],
    profiles: Mapping[str, Mapping[str, Any]],
    record: StoredCalibration | None,
    profile: str | None,
    height: float | None,
) -> dict[str, float] | None:
    """The travel model this cover really moves on, as the readings start from it.

    Ported from `GuidedCalibrationMixin._values_in_use`. `device` is the cover's
    validated configuration (`{}` when it is not configured any more), `profiles` both
    namespaces merged, `record` its stored record, `profile` the one chosen in this
    conversation (the dialog's `_profile`) and `height` the travel it measured
    (`_measured.height`).
    """
    if not device:
        return None
    chosen = profile or (record.profile if record is not None else None)
    travel = height or (record.height if record is not None else None)
    if record is not None:
        record = replace(record, profile=chosen, height=travel)
    elif chosen is not None:
        record = StoredCalibration(cover_unique_id=unique_id, profile=chosen, height=travel)
    values = resolve_cover(device, profiles=profiles, calibration=record).values
    if any(values.get(key) is None for key in _MODEL_KEYS):
        return None
    return {key: float(values[key]) for key in _MODEL_KEYS}


def adopted_timings(measured: Measured, values: Mapping[str, float] | None) -> Measured | None:
    """The measurement with the times the cover moves on today taken as its own.

    Ported from `GuidedCalibrationMixin._adopt_the_model_in_use`, which writes the
    same three fields into the conversation and answers `True`; here the conversation
    is handed back as a copy and `None` stands for `False`. `values` is what
    `values_in_use` answered.

    A copy with lists of its own: `dataclasses.replace` copies shallowly, which would
    leave the two `Measured` sharing the very lists the readings are appended to, so a
    caller that kept the one it started from (an undo, a snapshot taken before the
    thorough calibration, a before-and-after) would see its own copy grow behind its
    back. The readings are copied here rather than left to a rule the caller has to
    remember.
    """
    if values is None:
        return None
    slat = values[CONF_SLAT_TIME]
    return replace(
        measured,
        opening=PressTiming(slat, values[CONF_OPENING_TIME]),
        closing=PressTiming(None, values[CONF_CLOSING_TIME]),
        times_adopted=True,
        descent=list(measured.descent),
        ascent=list(measured.ascent),
    )


# ------------------------------------------------------------------ the tape
def expected_cm(
    *,
    pending: tuple[str, float] | None,
    height: float | None,
    model: Mapping[str, float] | None,
) -> tuple[str, str]:
    """Where the model thinks the bar is, and how far out is still normal.

    Ported from `GuidedCalibrationMixin._expected_cm`. `pending` is the run the reading
    is about (`_pending`), `height` the travel (`_measured.height`) and `model` what
    `model_values` answers for this conversation. The method only asks for the model
    when there is a height; asking for it regardless changes nothing, because
    `model_values` reads and never writes.
    """
    direction, fraction = pending or (DIRECTION_CLOSE, HALF_RUN)
    if not height:
        return ("-", f"{ROUGH_TOLERANCE_CM:.0f}")
    if model is not None:
        roll = model[CONF_CLOSING_ROLL if direction == DIRECTION_CLOSE else CONF_OPENING_ROLL]
        tolerance = EXPECTED_TOLERANCE_CM
    else:
        roll = DEFAULT_ROLL_SHUTTER
        tolerance = ROUGH_TOLERANCE_CM
    expected = predict_cm(direction, roll, 1.0, fraction, height)
    return (f"{expected:.0f}", f"{tolerance:.0f}")


def accept_measurement(value: Any, *, height: float | None) -> tuple[float | None, str | None]:
    """A tape reading that is a number and fits inside this window's travel.

    Ported from `GuidedCalibrationMixin._accept_measurement`. The method reads the
    reading out of its form (`user_input[FIELD_MEASURED_CM]`); here `value` is the
    reading itself, as typed or as sent, and `height` is `_measured.height`.
    """
    number = parse_number(value)
    if number is None:
        return None, ERROR_NOT_A_NUMBER
    if number < 0:
        return None, ERROR_OUT_OF_RANGE
    if height is not None and number > height:
        return None, ERROR_ABOVE_THE_TRAVEL
    return number, None


def deviation(
    measured_cm: float,
    *,
    report: RunReport | None,
    height: float | None,
    model: Mapping[str, float] | None,
) -> float | None:
    """How far the shutter really stopped from where the model said it would.

    Ported from `GuidedCalibrationMixin._deviation`. `report` is the verification run
    (`_report`), `height` the travel and `model` what `model_values` answers.

    **Descents only**, as the dialog's method is: the direction is written in, and with
    it the closing roll and the reading of the motor seconds as pure curtain time. An
    ascent spends its first `slat_time` seconds on the slats and would need the opening
    roll, so a verification in the other direction is not this function with a
    parameter - it is `deviation_cm` called properly, or (path B since lot W3) no model
    at all, because half the travel is half the travel whichever way the bar got there.
    """
    if report is None or not height or model is None:
        return None
    return deviation_cm(
        DIRECTION_CLOSE,
        roll=model[CONF_CLOSING_ROLL],
        height=height,
        run_time=model[CONF_CLOSING_TIME],
        slat_time=model[CONF_SLAT_TIME],
        motor_seconds=report.motor_seconds,
        measured_cm=measured_cm,
    )


def model_values(
    *,
    path: str,
    measured: Measured,
    profiles: Mapping[str, Mapping[str, Any]],
    profile: str | None,
) -> dict[str, float] | None:
    """The travel model the verification is asking about.

    Ported from `GuidedCalibrationMixin._model_values`: on path B the profile scaled to
    this window, elsewhere the fit. `profiles` is both namespaces merged and `profile`
    the one chosen in this conversation (`_profile`).
    """
    if path == PATH_PROFILE:
        chosen = profiles.get(profile or "")
        if chosen is None:
            return None
        return derive_cover_from_profile(chosen, measured.height)
    fitted = fits(measured)
    if fitted is None:
        return None
    down, up = fitted
    return {
        CONF_CLOSING_TIME: down.corrected_run_time,
        CONF_OPENING_TIME: up.corrected_run_time,
        CONF_SLAT_TIME: up.slat_time,
        CONF_CLOSING_ROLL: down.fit.roll,
        CONF_OPENING_ROLL: up.fit.roll,
    }


# ------------------------------------------------------------------ the fit
def fit_both(measured: Measured, slat: float) -> tuple[DirectionFit, DirectionFit]:
    """One fit per direction, both told the same slat phase.

    Ported from `GuidedCalibrationMixin._fit_both`: the time scale is pinned at 1 when
    the times were adopted rather than pressed for.
    """
    height = measured.height or 0.0
    scale_bounds = {"scale_bounds": FIXED_SCALE_BOUNDS} if measured.times_adopted else {}
    down = fit_from_run(
        DIRECTION_CLOSE,
        run_time=measured.closing.run_time if measured.closing else 0.0,
        slat_time=slat,
        measurements=measured.descent,
        height=height,
        **scale_bounds,
    )
    up = fit_from_run(
        DIRECTION_OPEN,
        run_time=measured.opening.run_time if measured.opening else 0.0,
        slat_time=slat,
        measurements=measured.ascent,
        height=height,
        **scale_bounds,
    )
    return down, up


def slat_from_gap(
    measured: Measured, raw: float, *, roll: float, height: float | None, curtain: float
) -> float:
    """The slat phase the taped gap implies, or the press's own when none was taped.

    Ported from `GuidedCalibrationMixin._slat_from_gap`.
    """
    if measured.lift_gap_cm is None or measured.lift_run_sec is None:
        return raw
    if not height or curtain <= 0:
        return raw
    return slat_time_from_gap(
        stop_seconds=measured.lift_run_sec,
        gap_cm=measured.lift_gap_cm,
        roll=roll,
        height=height,
        curtain_time=curtain,
    )


def fits(measured: Measured) -> tuple[DirectionFit, DirectionFit] | None:
    """Fit both directions, or None when this conversation measured no centimetres.

    Ported from `GuidedCalibrationMixin._fits`: fitted once with the press's slat
    phase and again with the one the taped gap implies, when there is one.
    """
    if (
        measured.opening is None
        or measured.closing is None
        or not measured.height
        or not measured.descent
        or not measured.ascent
    ):
        return None
    down, up = fit_both(measured, measured.slat_time)
    refined = slat_from_gap(
        measured, up.slat_time, roll=up.fit.roll, height=measured.height, curtain=up.curtain_time
    )
    if refined != up.slat_time:
        down, up = fit_both(measured, refined)
    return down, up


# ------------------------------------------------------------------ the summary
def result(
    *,
    path: str,
    measured: Measured,
    measured_name: str | None,
    profile: str | None,
    profiles: Mapping[str, Mapping[str, Any]],
    entity_id: str,
    yaml_key: str,
    height_known: float | None,
) -> Result:
    """What Save would write, computed from what has been measured so far.

    Ported from `GuidedCalibrationMixin._result`. `measured_name` is the profile name
    chosen on path A (`_measured_name`), `profile` the one chosen on path B or C
    (`_profile`), `profiles` both namespaces merged, `entity_id` the cover's entity id
    (the dialog reads it off `_cover`, "" when there is none), `yaml_key` the key the
    file knows the cover by (`_yaml_key`), and `height_known` what `known_height`
    answers for this cover - which the method asks only on the path that times alone.
    """
    name = measured_name or suggested_name(entity_id)
    key = yaml_key or suggested_name(entity_id)
    if path == PATH_PROFILE:
        height = measured.height or 0.0
        chosen = profiles.get(profile or "")
        derived = profile_overrides(chosen, height) if chosen is not None else {}
        return Result(
            yaml=profile_reference_yaml(key, profile or "", height, derived),
            follows_profile=True,
        )
    fitted = fits(measured)
    if fitted is not None:
        down, up = fitted
        values = {
            CONF_OPENING_TIME: round(up.corrected_run_time, 1),
            CONF_CLOSING_TIME: round(down.corrected_run_time, 1),
            CONF_SLAT_TIME: round(up.slat_time, 1),
            CONF_OPENING_ROLL: round(up.fit.roll, 2),
            CONF_CLOSING_ROLL: round(down.fit.roll, 2),
        }
        accuracy = (
            max(down.fit.max_residual_cm, up.fit.max_residual_cm)
            if min(down.fit.points, up.fit.points) > 1
            else None
        )
        if path == PATH_FIRST:
            return Result(
                yaml=calibration_yaml(
                    name,
                    measured.height or 0.0,
                    values[CONF_OPENING_TIME],
                    values[CONF_CLOSING_TIME],
                    values[CONF_SLAT_TIME],
                    values[CONF_CLOSING_ROLL],
                    values[CONF_OPENING_ROLL],
                ),
                profile={CONF_REFERENCE_HEIGHT: measured.height or 0.0, **values},
                overrides=dict(values),
                accuracy_cm=accuracy,
            )
        if measured.times_adopted:
            rolls = {
                CONF_OPENING_ROLL: values[CONF_OPENING_ROLL],
                CONF_CLOSING_ROLL: values[CONF_CLOSING_ROLL],
            }
            return Result(
                yaml=overrides_yaml(key, rolls, measured.height),
                overrides=rolls,
                accuracy_cm=accuracy,
            )
        return Result(
            yaml=overrides_yaml(key, values, measured.height),
            overrides=values,
            accuracy_cm=accuracy,
        )
    slat = measured.slat_time
    chosen = profiles.get(profile or "")
    height = measured.height or height_known
    if chosen is not None and measured.opening is not None:
        model = derive_cover_from_profile(chosen, height)
        slat = slat_from_gap(
            measured,
            slat,
            roll=model[CONF_OPENING_ROLL],
            height=height,
            curtain=measured.opening.run_time - slat,
        )
    values = {
        CONF_OPENING_TIME: round(measured.opening.run_time, 1) if measured.opening else 0.0,
        CONF_CLOSING_TIME: round(measured.closing.run_time, 1) if measured.closing else 0.0,
        CONF_SLAT_TIME: round(slat, 1),
    }
    return Result(yaml=overrides_yaml(key, values, None), overrides=values)


# ------------------------------------------------------------------ saving
def raw(*, path: str, measured: Measured) -> dict[str, Any]:
    """The measurements themselves, kept beside the conclusions drawn from them.

    Ported from `GuidedCalibrationMixin._raw`. The panel's session adds its own keys
    (`client`, `save_target`) to what this answers; the dialog's keys are these.
    """
    return {
        "path": path,
        "precise": measured.precise,
        "height": measured.height,
        "opening_run": measured.opening.run_time if measured.opening else None,
        "closing_run": measured.closing.run_time if measured.closing else None,
        "slat": measured.slat_time,
        "times_measured": not measured.times_adopted,
        "descent": [list(point) for point in measured.descent],
        "ascent": [list(point) for point in measured.ascent],
        "deviation_cm": measured.deviation,
    }


def merged_with(
    record: StoredCalibration | None, result: Result, *, measured: Measured
) -> tuple[dict[str, float], float | None]:
    """What Save really writes: this measurement *over* what was already stored.

    Ported from `GuidedCalibrationMixin._merged_with`. Path B (`follows_profile`)
    supersedes what was stored; every other path keeps the keys it did not measure,
    and the height it did not read off a tape.
    """
    if result.follows_profile:
        return dict(result.overrides), measured.height
    kept = dict(record.overrides) if record is not None else {}
    merged = {**kept, **result.overrides}
    height = (
        measured.height
        if measured.height_measured
        else (record.height if record is not None else None)
    )
    return merged, height


def replaced_and_kept(
    record: StoredCalibration | None, result: Result, *, measured: Measured
) -> tuple[list[str], list[str]]:
    """The keys this Save overwrites, and the ones it leaves exactly as they are.

    Ported from `GuidedCalibrationMixin._replaced_and_kept`, which reads the record out
    of the store itself (`_store.calibration(_cover_unique_id)`); here it is passed in.
    """
    merged, height = merged_with(record, result, measured=measured)
    before = dict(record.overrides) if record is not None else {}
    moving = {key for key in set(before) | set(merged) if before.get(key) != merged.get(key)}
    replaced = sorted(moving)
    kept = sorted(key for key in merged if key not in moving)
    if measured.height_measured:
        replaced.append(CONF_HEIGHT)
    elif measured.height or height is not None:
        kept.append(CONF_HEIGHT)
    return replaced, kept


def profile_still_wins(
    record: StoredCalibration | None, result: Result, *, path: str, profile: str | None
) -> bool:
    """Whether the cover goes on following its profile *above* what the file writes.

    Ported from `GuidedCalibrationMixin._profile_still_wins`: path B is the statement
    itself, a correction (path C) keeps it when a profile was confirmed (`profile`, the
    dialog's `_profile`) or the record already carried it, and path A never sets it.
    """
    if result.follows_profile:
        return True
    if path != PATH_REFINE:
        return False
    return profile is not None or bool(record is not None and record.profile_wins)


__all__ = [
    "Measured",
    "Result",
    "accept_measurement",
    "adopted_timings",
    "assigned_profile",
    "deviation",
    "expected_cm",
    "fit_both",
    "fits",
    "known_height",
    "merged_with",
    "model_values",
    "own_height",
    "profile_still_wins",
    "raw",
    "replaced_and_kept",
    "result",
    "slat_from_gap",
    "suggested_name",
    "values_in_use",
]
