"""Where a guided calibration is kept, and what it is worth against ``myhome.yaml`` (0.5.0).

The guided flow of phase 2 does not write to the user's file. It cannot: the file is
theirs, it carries their comments and their ordering, and an integration that rewrote
it would eventually get it wrong. So the numbers it measures go into **config
subentries** of the gateway's own config entry - the place Home Assistant provides for
exactly this, with its own UI, its own delete button and its own storage - and this
module is the two halves of that arrangement:

* the **schema**: what a `cover_profile` and a `cover_calibration` subentry hold, built
  and read in one place so the flow, the entity and the diagnostics cannot disagree
  about it; and
* the **precedence**: which of the four possible sources of a travel key wins, per key.

The precedence, highest first (spec 1.3):

1. an **override** stored for this cover (`cover_calibration.overrides`) - the guided
   flow measured *this* window, on this installation, with a tape;
2. the key as **written in the file** for this cover;
3. the **profile**, scaled to this cover's height: the profile named by the stored
   calibration if there is one, else the `profile:` in the file, and the height from the
   stored calibration if there is one, else the `height:` in the file;
4. what the validator already resolved - the file's own profile chain, and the defaults.

Rules 1 and 2 are the pair worth stating twice, because the order between them is a
decision and not an obvious one. A measurement of *this* window beats the file, while a
*profile* - a measurement of some other window of the same kind - does not. The
difference is what the number is about: the flow only stores an override after the user
has watched that shutter move and read a tape against it, which is a more specific
statement about this window than a line typed in a file about all of them, and it is
removable in one click from the integration page (`async_remove_cover_calibration`),
which is what makes "the file wins again" a thing the user can ask for. A profile is
the general case, so it stays below the particular one the file states.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import (
    CALIBRATION_SOURCE_GUIDED,
    CALIBRATION_SOURCE_PROFILE,
    CALIBRATION_SOURCE_YAML,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_SLAT_TIME,
    CONF_CLOSING_TIME,
    CONF_COVER_UNIQUE_ID,
    CONF_HEIGHT,
    CONF_KEYS_FROM_FILE,
    CONF_MEASURED_AT,
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
    COVER_CALIBRATION_KEYS,
    DEFAULT_START_DELAY,
    DEFAULT_STOP_LATENCY,
    LOGGER,
    SUBENTRY_COVER_CALIBRATION,
    SUBENTRY_COVER_PROFILE,
)
from .validate import derive_cover_from_profile

# A profile name may look like a YAML key, because it is one: the user can move a
# guided profile into `cover_profiles:` by hand and nothing else has to change.
PROFILE_NAME_PATTERN = r"^[A-Za-z0-9_]+$"

# The file's own fallbacks, mirrored here. `_finalize_cover` lets a cover that writes
# `roll:` say what *both* directions do and one that writes only `opening_time` say what
# the downward run does too, so a cover whose file says `roll: 1.5` has stated its two
# directional rolls even though neither key appears in it. Without this, a profile would
# fill those in and quietly contradict the line the user did write.
_IMPLIED_BY_THE_FILE: dict[str, tuple[str, ...]] = {
    CONF_ROLL: (CONF_OPENING_ROLL, CONF_CLOSING_ROLL),
    CONF_OPENING_TIME: (CONF_CLOSING_TIME,),
}

# Names that have already been reported as defined twice, so the warning is said once
# per name and not once per cover per reload.
_CLASH_REPORTED: set[str] = set()


@callback
def reset_name_clash_warnings() -> None:
    """Forget which clashing names have been reported (a reload says it again once)."""
    _CLASH_REPORTED.clear()


# --------------------------------------------------------------------------- schema
@callback
def cover_profile_data(
    name: str,
    *,
    reference_height: float,
    opening_time: float,
    closing_time: float,
    slat_time: float,
    opening_roll: float,
    closing_roll: float,
    closing_slat_time: float | None = None,
    source: str = CALIBRATION_SOURCE_GUIDED,
    measured_at: str | None = None,
    raw: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The data of a `cover_profile` subentry: one model of shutter, measured once.

    `raw` is whatever the flow wants to keep of how it got there - the presses, the
    tape readings, the residuals. Nothing reads it back; it is there so that a shutter
    that turns out to behave oddly can be argued about six months later with the
    measurements in hand rather than the conclusions alone.
    """
    data: dict[str, Any] = {
        CONF_NAME: name,
        CONF_REFERENCE_HEIGHT: float(reference_height),
        CONF_OPENING_TIME: float(opening_time),
        CONF_CLOSING_TIME: float(closing_time),
        CONF_SLAT_TIME: float(slat_time),
        CONF_OPENING_ROLL: float(opening_roll),
        CONF_CLOSING_ROLL: float(closing_roll),
        CONF_SOURCE: source,
        CONF_MEASURED_AT: measured_at or dt_util.utcnow().isoformat(),
    }
    if closing_slat_time is not None:
        data[CONF_CLOSING_SLAT_TIME] = float(closing_slat_time)
    if raw:
        data[CONF_RAW] = dict(raw)
    return data


@callback
def cover_calibration_data(
    cover_unique_id: str,
    *,
    profile: str | None = None,
    height: float | None = None,
    overrides: Mapping[str, float] | None = None,
    source: str = CALIBRATION_SOURCE_GUIDED,
    measured_at: str | None = None,
    raw: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The data of a `cover_calibration` subentry: what one window needed.

    Everything but the cover it belongs to is optional, and the three combinations are
    the three paths of the flow: a profile and a height (this window is one of those,
    measured with a tape), a profile and some overrides (it is one of those but its own
    motor is slower), or overrides alone (nothing else is like it).

    Keys the travel model does not know are dropped rather than stored: a subentry is
    read back verbatim into the resolution below, and a typo that survived storage
    would be a key nobody ever notices doing nothing.
    """
    data: dict[str, Any] = {
        CONF_COVER_UNIQUE_ID: cover_unique_id,
        CONF_SOURCE: source,
        CONF_MEASURED_AT: measured_at or dt_util.utcnow().isoformat(),
    }
    if profile is not None:
        data[CONF_PROFILE] = profile
    if height is not None:
        data[CONF_HEIGHT] = float(height)
    kept = {
        key: float(value) for key, value in (overrides or {}).items() if key in COVER_CALIBRATION_KEYS
    }
    dropped = sorted(set(overrides or {}) - set(kept))
    if dropped:
        LOGGER.warning(
            "Calibration of %s: %s is not part of the travel model and was not stored",
            cover_unique_id,
            ", ".join(dropped),
        )
    if kept:
        data[CONF_OVERRIDES] = kept
    if raw:
        data[CONF_RAW] = dict(raw)
    return data


@dataclass(frozen=True, slots=True)
class StoredCalibration:
    """One `cover_calibration` subentry, as the resolution below reads it."""

    cover_unique_id: str
    profile: str | None = None
    height: float | None = None
    overrides: Mapping[str, float] = field(default_factory=dict)
    source: str = CALIBRATION_SOURCE_GUIDED
    measured_at: str | None = None
    subentry_id: str | None = None

    @property
    def says_anything(self) -> bool:
        """False for a subentry that would change nothing (an empty one, by hand)."""
        return bool(self.overrides) or self.profile is not None or self.height is not None


def _stored_calibration(subentry: ConfigSubentry) -> StoredCalibration:
    data = subentry.data
    overrides = data.get(CONF_OVERRIDES) or {}
    return StoredCalibration(
        cover_unique_id=str(data.get(CONF_COVER_UNIQUE_ID, "")),
        profile=data.get(CONF_PROFILE),
        height=data.get(CONF_HEIGHT),
        overrides={
            key: float(value) for key, value in overrides.items() if key in COVER_CALIBRATION_KEYS
        },
        source=data.get(CONF_SOURCE, CALIBRATION_SOURCE_GUIDED),
        measured_at=data.get(CONF_MEASURED_AT),
        subentry_id=subentry.subentry_id,
    )


@callback
def stored_profiles(entry: ConfigEntry) -> dict[str, dict[str, Any]]:
    """Every `cover_profile` subentry of this gateway, keyed by its name.

    The shape is the one `cover_profiles:` produces in `myhome.yaml`, so the profile a
    flow stored and the profile a user wrote are the same thing to everything
    downstream - `derive_cover_from_profile` above all, which is what scales either of
    them to a window of a different height.
    """
    profiles: dict[str, dict[str, Any]] = {}
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_COVER_PROFILE:
            continue
        data = subentry.data
        name = data.get(CONF_NAME) or subentry.title
        opening = data.get(CONF_OPENING_TIME)
        reference = data.get(CONF_REFERENCE_HEIGHT)
        if not name or opening is None or not reference:
            # A subentry that is not a profile at all (hand-edited storage, or one
            # written by a future version this one does not understand). Ignoring it
            # leaves the cover on its YAML numbers, which is the safe way to be wrong.
            LOGGER.warning(
                "Ignoring a stored cover profile without a name, an opening time or a "
                "reference height (subentry %s)",
                subentry.subentry_id,
            )
            continue
        closing_roll = data.get(CONF_CLOSING_ROLL, data.get(CONF_ROLL, 1.0))
        profiles[str(name)] = {
            CONF_REFERENCE_HEIGHT: float(reference),
            CONF_OPENING_TIME: float(opening),
            CONF_CLOSING_TIME: float(data.get(CONF_CLOSING_TIME, opening)),
            CONF_SLAT_TIME: float(data.get(CONF_SLAT_TIME, 0.0)),
            # `roll` is the fallback of the two directional ones and the one
            # `derive_cover_from_profile` grows the *curtain time* from, which is a
            # length of fabric and therefore the closing one (see that function).
            CONF_ROLL: float(closing_roll),
            CONF_OPENING_ROLL: float(data.get(CONF_OPENING_ROLL, closing_roll)),
            CONF_CLOSING_ROLL: float(closing_roll),
            # Never measured by the flow, never scaled by the profile: constants of the
            # installation (0.4.4).
            CONF_STOP_LATENCY: float(data.get(CONF_STOP_LATENCY, DEFAULT_STOP_LATENCY)),
            CONF_START_DELAY: float(data.get(CONF_START_DELAY, DEFAULT_START_DELAY)),
        }
    return profiles


@callback
def stored_calibrations(entry: ConfigEntry) -> dict[str, StoredCalibration]:
    """Every `cover_calibration` subentry of this gateway, keyed by the cover it is for.

    One per cover: re-running the flow on the same shutter replaces the subentry rather
    than adding a second one (`async_set_cover_calibration`). Should storage hold two
    all the same, the last one wins and the duplicate is reported - silently preferring
    one of them would make the shutter's behaviour depend on a dictionary's order.
    """
    calibrations: dict[str, StoredCalibration] = {}
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_COVER_CALIBRATION:
            continue
        stored = _stored_calibration(subentry)
        if not stored.cover_unique_id:
            LOGGER.warning(
                "Ignoring a stored cover calibration that names no cover (subentry %s)",
                subentry.subentry_id,
            )
            continue
        if stored.cover_unique_id in calibrations:
            LOGGER.warning(
                "Two stored calibrations for the same cover (%s): the last one is used",
                stored.cover_unique_id,
            )
        calibrations[stored.cover_unique_id] = stored
    return calibrations


@callback
def merged_profiles(
    yaml_profiles: Mapping[str, Mapping[str, Any]], ui_profiles: Mapping[str, Mapping[str, Any]]
) -> dict[str, Mapping[str, Any]]:
    """One namespace for both kinds of profile, with the stored one winning a clash.

    They share a namespace because a cover's `profile:` is one word and has to mean one
    thing. A stored profile wins because it is the more recent statement of intent: the
    user ran the flow *after* writing the file, on this very installation, and the flow
    is where the name came from. It is said out loud, once per name, because a profile
    that quietly stops being the one in the file is the kind of thing that costs an
    evening.
    """
    merged: dict[str, Mapping[str, Any]] = dict(yaml_profiles)
    for name, profile in ui_profiles.items():
        if name in yaml_profiles and name not in _CLASH_REPORTED:
            _CLASH_REPORTED.add(name)
            LOGGER.warning(
                "Cover profile '%s' is defined both in 'cover_profiles:' and by a guided "
                "calibration; the guided one is used. Rename one of the two (or remove the "
                "calibration) to get the file's back",
                name,
            )
        merged[name] = profile
    return merged


# ----------------------------------------------------------------------- precedence
@dataclass(frozen=True, slots=True)
class ResolvedCover:
    """The travel model one cover really runs on, and where it came from."""

    values: dict[str, Any]
    source: str
    profile: str | None = None
    height: float | None = None


@callback
def resolve_cover(
    device: Mapping[str, Any],
    *,
    profiles: Mapping[str, Mapping[str, Any]],
    calibration: StoredCalibration | None = None,
) -> ResolvedCover:
    """Merge a stored calibration into one cover's validated configuration.

    `device` is the dict the validator produced (every key already filled in from the
    file, the file's profile and the defaults) plus `keys_from_file`, which is the only
    thing that says which of those values the user actually wrote. See the module
    docstring for the order; the whole of it is the loop below.

    Nothing here can fail: a calibration naming a profile that no longer exists falls
    back to the file, because a shutter that stops working because a profile was
    renamed would be worse than one that stops where it used to.
    """
    written = set(device.get(CONF_KEYS_FROM_FILE) or ())
    for key, implied in _IMPLIED_BY_THE_FILE.items():
        if key in written:
            written.update(implied)
    overrides = calibration.overrides if calibration else {}
    name = (calibration.profile if calibration else None) or device.get(CONF_PROFILE)
    height = (calibration.height if calibration else None) or device.get(CONF_HEIGHT)
    derived: Mapping[str, Any] = {}
    if name is not None:
        profile = profiles.get(name)
        if profile is None:
            LOGGER.warning(
                "Cover %s follows the profile '%s', which is not defined any more: "
                "its own configuration is used instead",
                device.get(CONF_COVER_UNIQUE_ID) or name,
                name,
            )
        else:
            derived = derive_cover_from_profile(profile, height)

    values: dict[str, Any] = {}
    for key in COVER_CALIBRATION_KEYS:
        if key in overrides:
            values[key] = overrides[key]
        elif key in written:
            values[key] = device[key]
        elif key in derived:
            values[key] = derived[key]
        elif key in device:
            values[key] = device[key]
    if height is not None:
        values[CONF_HEIGHT] = height
    if name is not None:
        values[CONF_PROFILE] = name

    if calibration is not None and calibration.says_anything:
        source = CALIBRATION_SOURCE_GUIDED
    elif name is not None and name in profiles:
        source = f"{CALIBRATION_SOURCE_PROFILE} {name}"
    else:
        source = CALIBRATION_SOURCE_YAML
    return ResolvedCover(values=values, source=source, profile=name, height=height)


@callback
def resolve_cover_config(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: Mapping[str, Any],
    unique_id: str,
    yaml_profiles: Mapping[str, Mapping[str, Any]],
) -> ResolvedCover:
    """`resolve_cover` with both kinds of stored data read off the config entry.

    The one call the cover platform makes (`hass` is taken for symmetry with everything
    else that reads the entry, and because a future release that moves this into a
    helper store will need it).
    """
    return resolve_cover(
        device,
        profiles=merged_profiles(yaml_profiles, stored_profiles(entry)),
        calibration=stored_calibrations(entry).get(unique_id),
    )


# ------------------------------------------------------------------ writing it down
# The four calls phase 2 makes. They are `@callback`s rather than coroutines because
# `ConfigEntries.async_add_subentry` and friends are: adding a subentry writes the
# entry's own storage, and the write is debounced by Home Assistant itself.
@callback
def async_set_cover_profile(
    hass: HomeAssistant, entry: ConfigEntry, name: str, data: Mapping[str, Any], *, reload: bool = True
) -> ConfigSubentry:
    """Store (or replace) the profile called `name`.

    Replacing rather than adding is the whole reason this is not one line at the call
    site: a user who calibrates the same kind of shutter twice means the second
    measurement, and two subentries with the same name would make the namespace of
    profiles depend on which one storage happened to list first.
    """
    return _async_store(
        hass,
        entry,
        subentry_type=SUBENTRY_COVER_PROFILE,
        unique_id=f"{SUBENTRY_COVER_PROFILE}-{name}",
        title=name,
        data=data,
        reload=reload,
    )


@callback
def async_set_cover_calibration(
    hass: HomeAssistant,
    entry: ConfigEntry,
    cover_unique_id: str,
    data: Mapping[str, Any],
    *,
    title: str | None = None,
    reload: bool = True,
) -> ConfigSubentry:
    """Store (or replace) the calibration of one cover."""
    return _async_store(
        hass,
        entry,
        subentry_type=SUBENTRY_COVER_CALIBRATION,
        unique_id=f"{SUBENTRY_COVER_CALIBRATION}-{cover_unique_id}",
        title=title or cover_unique_id,
        data=data,
        reload=reload,
    )


@callback
def async_remove_cover_profile(
    hass: HomeAssistant, entry: ConfigEntry, name: str, *, reload: bool = True
) -> bool:
    """Forget the profile called `name`; False when there was none."""
    return _async_remove(
        hass, entry, SUBENTRY_COVER_PROFILE, f"{SUBENTRY_COVER_PROFILE}-{name}", reload=reload
    )


@callback
def async_remove_cover_calibration(
    hass: HomeAssistant, entry: ConfigEntry, cover_unique_id: str, *, reload: bool = True
) -> bool:
    """Forget one cover's calibration; False when there was none.

    The cover goes back to what `myhome.yaml` says about it when the entry is next
    loaded - which `reload` does at once, and which is also what makes a calibration
    removed from Home Assistant's own subentry list take effect.
    """
    return _async_remove(
        hass,
        entry,
        SUBENTRY_COVER_CALIBRATION,
        f"{SUBENTRY_COVER_CALIBRATION}-{cover_unique_id}",
        reload=reload,
    )


@callback
def _find(entry: ConfigEntry, subentry_type: str, unique_id: str) -> ConfigSubentry | None:
    for subentry in entry.subentries.values():
        if subentry.subentry_type == subentry_type and subentry.unique_id == unique_id:
            return subentry
    return None


@callback
def _async_store(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    subentry_type: str,
    unique_id: str,
    title: str,
    data: Mapping[str, Any],
    reload: bool,
) -> ConfigSubentry:
    existing = _find(entry, subentry_type, unique_id)
    if existing is not None:
        hass.config_entries.async_update_subentry(entry, existing, data=dict(data), title=title)
        subentry = entry.subentries[existing.subentry_id]
    else:
        subentry = ConfigSubentry(
            data=dict(data), subentry_type=subentry_type, title=title, unique_id=unique_id
        )
        hass.config_entries.async_add_subentry(entry, subentry)
    _async_reload(hass, entry, reload)
    return subentry


@callback
def _async_remove(
    hass: HomeAssistant, entry: ConfigEntry, subentry_type: str, unique_id: str, *, reload: bool
) -> bool:
    existing = _find(entry, subentry_type, unique_id)
    if existing is None:
        return False
    hass.config_entries.async_remove_subentry(entry, existing.subentry_id)
    _async_reload(hass, entry, reload)
    return True


@callback
def _async_reload(hass: HomeAssistant, entry: ConfigEntry, reload: bool) -> None:
    """Rebuild the entities, because a cover reads its travel model once, at setup.

    Home Assistant does not reload an entry when a subentry changes - neither when a
    flow creates one nor when the user deletes one from the integration page - so the
    caller does it here. A calibration that only took effect after a restart would be
    a calibration the user does not believe in.
    """
    if reload and entry.state.recoverable:
        hass.config_entries.async_schedule_reload(entry.entry_id)
