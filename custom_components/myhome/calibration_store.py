"""Where a guided calibration is kept, and what it is worth against the file (0.5.0).

The guided flow does not write to the user's `myhome.yaml`. It cannot: the file is
theirs, it carries their comments and their ordering, and an integration that rewrote
it would eventually get it wrong. So the numbers it measures go into a **store of the
integration's own** - one `homeassistant.helpers.storage.Store` per config entry - and
this module is the three halves of that arrangement:

* the **schema**: what a profile and a per-cover record hold, built and read in one
  place so the flow, the entity and the diagnostics cannot disagree about it;
* the **store**: `CalibrationStore`, loaded once at setup and cached, because a cover
  reads its travel model in its constructor and the resolution below has to be a plain
  function call rather than an await; and
* the **precedence**: which of the four possible sources of a travel key wins, per key.

The first draft of 0.5.0 kept the same data in two *config subentry* types. It worked,
and it put two rows on the integration page that Home Assistant then grouped every
device under "devices not belonging to a subentry", offered a "rename" that renamed the
row and not the profile, and gave no way to look at a number, let alone correct one.
The data is the same shape; `async_import_legacy_subentries` moves an installation
written by that draft into the store, once, and deletes the subentries it read.

The precedence, highest first (spec 1.3):

1. an **override** stored for this cover - the guided flow measured *this* window, on
   this installation, with a tape;
2. the **profile**, scaled to this cover's height, *when the stored record says this
   cover follows it* (`profile_wins`, written by path B and by the assignment screen);
3. the key as **written in the file** for this cover;
4. the **profile**, scaled to this cover's height: the profile named by the stored
   record if there is one, else the `profile:` in the file, and the height from the
   stored record if there is one, else the `height:` in the file;
5. what the validator already resolved - the file's own profile chain, and the defaults.

Rules 1 and 3 are the pair worth stating twice, because the order between them is a
decision and not an obvious one. A measurement of *this* window beats the file, while a
*profile* - a measurement of some other window of the same kind - does not. The
difference is what the number is about: the flow only stores an override after the user
has watched that shutter move and read a tape against it, which is a more specific
statement about this window than a line typed in a file about all of them, and it is
removable in one click under "Configura" (`async_remove_calibration`), which is what
makes "the file wins again" a thing the user can ask for. A profile is the general
case, so it stays below the particular one the file states.

Rule 2 is the exception the user asks for by name. "(B) È simile a una tapparella già
misurata" and "Assegna un profilo" are the two screens on which somebody says *of this
window* "it is one of those" - after the file was written, on this installation - and a
rule that left them below the file's own run times made both of them do nothing at all
on a `myhome.yaml` that writes run times per cover (0.5.0 v2 review, BUG-1; final
review, RISK-A/RISK-B). What is stored for those two is the **intent** and not the
numbers: `profile_wins`, beside the name and the height. The numbers are derived here,
on every read, which is what makes a `cover_profiles:` profile corrected in the file
reach its followers on the next reload - and what makes it impossible for a stored copy
to go stale behind the user's back.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CALIBRATION_SOURCE_GUIDED,
    CALIBRATION_SOURCE_PROFILE,
    CALIBRATION_SOURCE_YAML,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_UNIQUE_ID,
    CONF_COVERS,
    CONF_HEIGHT,
    CONF_KEYS_FROM_FILE,
    CONF_MEASURED_AT,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_OVERRIDES,
    CONF_PROFILE,
    CONF_PROFILE_WINS,
    CONF_PROFILES,
    CONF_RAW,
    CONF_REFERENCE_COVER,
    CONF_REFERENCE_HEIGHT,
    CONF_ROLL,
    CONF_SLAT_TIME,
    CONF_SOURCE,
    CONF_START_DELAY,
    CONF_STOP_LATENCY,
    COVER_CALIBRATION_KEYS,
    DEFAULT_START_DELAY,
    DEFAULT_STOP_LATENCY,
    DOMAIN,
    LEGACY_SUBENTRY_COVER_CALIBRATION,
    LEGACY_SUBENTRY_COVER_PROFILE,
    LOGGER,
)
from .validate import derive_cover_from_profile

# A profile name may look like a YAML key, because it is one: the user can move a
# guided profile into `cover_profiles:` by hand and nothing else has to change.
PROFILE_NAME_PATTERN = r"^[A-Za-z0-9_]+$"

# One store per config entry, version 1. The entry id is in the key because a house
# with two gateways has two sets of shutters and one set of files.
STORAGE_VERSION = 1


def storage_key(entry_id: str) -> str:
    """The `.storage` file one gateway's calibrations live in."""
    return f"{DOMAIN}.calibration.{entry_id}"


# Where the loaded stores are kept. Not under `hass.data[DOMAIN]`, which holds only
# per-gateway dicts keyed by MAC address and nothing else (const.py, core-03).
STORE_DATA_KEY = f"{DOMAIN}_calibration_stores"

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

# The keys a profile really states about a window, in the shape a per-cover override
# is written in. The two bus costs (`stop_latency`, `start_delay`) are deliberately
# left out - they are the gateway's answer time and the motor's brake, constants of the
# installation rather than of the window (0.4.4) - and so is `roll`, which is only the
# fallback of the two directional ones.
_DERIVED_OVERRIDE_KEYS: tuple[tuple[str, int], ...] = (
    (CONF_OPENING_TIME, 1),
    (CONF_CLOSING_TIME, 1),
    (CONF_SLAT_TIME, 1),
    (CONF_OPENING_ROLL, 2),
    (CONF_CLOSING_ROLL, 2),
)


@callback
def profile_overrides(profile: Mapping[str, Any], height: float | None) -> dict[str, float]:
    """A profile, scaled to one window, in the shape that window's own overrides have.

    What "this window is one of those" comes to in numbers, rounded as the flow rounds
    them. Nothing stores the result any more - a record says `profile_wins` and the
    resolution derives it again on every read, so a profile corrected in `myhome.yaml`
    is never a frozen copy (final review, RISK-A). It is the summary screen and the
    YAML snippet it offers that need the numbers themselves, because a `profile:` line
    pasted into a file that already carries its own run times would not change them.
    """
    derived = derive_cover_from_profile(profile, height)
    return {key: round(float(derived[key]), digits) for key, digits in _DERIVED_OVERRIDE_KEYS}


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
    reference_cover: str | None = None,
    source: str = CALIBRATION_SOURCE_GUIDED,
    measured_at: str | None = None,
    raw: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One profile: one model of shutter, measured once.

    `raw` is whatever the flow wants to keep of how it got there - the presses, the
    tape readings, the residuals. Nothing reads it back; it is there so that a shutter
    that turns out to behave oddly can be argued about six months later with the
    measurements in hand rather than the conclusions alone. `reference_cover` is the
    window it was measured on, which the "Vedi i valori" screen shows and nothing else
    reads.
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
    if reference_cover:
        data[CONF_REFERENCE_COVER] = reference_cover
    if raw:
        data[CONF_RAW] = dict(raw)
    return data


@callback
def cover_calibration_data(
    cover_unique_id: str,
    *,
    profile: str | None = None,
    profile_wins: bool = False,
    height: float | None = None,
    overrides: Mapping[str, float] | None = None,
    source: str = CALIBRATION_SOURCE_GUIDED,
    measured_at: str | None = None,
    raw: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One cover's record: what this window needed.

    Everything but the cover it belongs to is optional, and the three combinations are
    the three paths of the flow: a profile and a height (this window is one of those,
    measured with a tape), a profile and some overrides (it is one of those but its own
    motor is slower), or overrides alone (nothing else is like it).

    `profile_wins` is the first of those two said out loud: the user named the kind of
    shutter *after* the file was written, so the profile is put above the keys the file
    writes for this cover (see `resolve_cover`). It is meaningless without a profile and
    is not written without one.

    Keys the travel model does not know are dropped rather than stored: a record is
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
        if profile_wins:
            data[CONF_PROFILE_WINS] = True
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
    """One cover's stored record, as the resolution below reads it."""

    cover_unique_id: str
    profile: str | None = None
    profile_wins: bool = False
    height: float | None = None
    overrides: Mapping[str, float] = field(default_factory=dict)
    source: str = CALIBRATION_SOURCE_GUIDED
    measured_at: str | None = None

    @property
    def says_anything(self) -> bool:
        """False for a record that would change nothing (an empty one, by hand)."""
        return bool(self.overrides) or self.profile is not None or self.height is not None

    @property
    def follows_a_profile(self) -> bool:
        """True when this window was *told* which kind of shutter it is.

        Path B and the assignment screen; never a hand edit of `myhome.yaml`, whose
        `profile:` is a line about the file's own precedence and not a statement made
        on this installation afterwards.
        """
        return self.profile is not None and self.profile_wins

    @property
    def is_a_measurement(self) -> bool:
        """True when this window itself was measured, rather than merely assigned.

        "Profili e tapparelle" and path B write a profile and a height; the guided
        flow writes the numbers it found. Only the second is a calibration in the sense
        the "Calibrazioni" screen means, and only the second makes `Calibration source`
        say `guided` - see `resolve_cover`. A window that was only assigned has no
        overrides at all, so the source goes on naming the profile.
        """
        return bool(self.overrides)


@callback
def stored_calibration(data: Mapping[str, Any]) -> StoredCalibration:
    """Read one cover's record out of the store (or out of a legacy subentry)."""
    overrides = data.get(CONF_OVERRIDES) or {}
    return StoredCalibration(
        cover_unique_id=str(data.get(CONF_COVER_UNIQUE_ID, "")),
        profile=data.get(CONF_PROFILE),
        profile_wins=bool(data.get(CONF_PROFILE_WINS)),
        height=data.get(CONF_HEIGHT),
        overrides={
            key: float(value) for key, value in overrides.items() if key in COVER_CALIBRATION_KEYS
        },
        source=data.get(CONF_SOURCE, CALIBRATION_SOURCE_GUIDED),
        measured_at=data.get(CONF_MEASURED_AT),
    )


@callback
def profile_as_config(name: str, data: Mapping[str, Any]) -> dict[str, Any] | None:
    """A stored profile in the shape `cover_profiles:` produces in `myhome.yaml`.

    So that the profile a flow stored and the profile a user wrote are the same thing
    to everything downstream - `derive_cover_from_profile` above all, which is what
    scales either of them to a window of a different height. None for a record that is
    not a profile at all (hand-edited storage, or one written by a future version this
    one does not understand): ignoring it leaves the cover on its YAML numbers, which
    is the safe way to be wrong.
    """
    opening = data.get(CONF_OPENING_TIME)
    reference = data.get(CONF_REFERENCE_HEIGHT)
    if not name or opening is None or not reference:
        LOGGER.warning(
            "Ignoring a stored cover profile without a name, an opening time or a "
            "reference height (%s)",
            name or "unnamed",
        )
        return None
    closing_roll = data.get(CONF_CLOSING_ROLL, data.get(CONF_ROLL, 1.0))
    return {
        CONF_REFERENCE_HEIGHT: float(reference),
        CONF_OPENING_TIME: float(opening),
        CONF_CLOSING_TIME: float(data.get(CONF_CLOSING_TIME, opening)),
        CONF_SLAT_TIME: float(data.get(CONF_SLAT_TIME, 0.0)),
        # `roll` is the fallback of the two directional ones and the one
        # `derive_cover_from_profile` grows the *curtain time* from, which is a length
        # of fabric and therefore the closing one (see that function).
        CONF_ROLL: float(closing_roll),
        CONF_OPENING_ROLL: float(data.get(CONF_OPENING_ROLL, closing_roll)),
        CONF_CLOSING_ROLL: float(closing_roll),
        # Never measured by the flow, never scaled by the profile: constants of the
        # installation (0.4.4).
        CONF_STOP_LATENCY: float(data.get(CONF_STOP_LATENCY, DEFAULT_STOP_LATENCY)),
        CONF_START_DELAY: float(data.get(CONF_START_DELAY, DEFAULT_START_DELAY)),
    }


# ---------------------------------------------------------------------------- store
class CalibrationStore:
    """Every guided calibration of one gateway, and the only thing that writes them.

    Loaded once, at setup, and kept in `hass.data` for the rest of the entry's life:
    the cover platform resolves twelve shutters in a loop inside `async_setup_entry`,
    and an `await` per shutter per reload would be twelve reads of the same file.
    Every write goes to disk immediately (`async_save` and not a delayed writer),
    because the next thing that happens after a write is a reload of the entry, and a
    calibration that survived the dialog but not the reload would be the worst kind of
    bug to be told about.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Nothing is read here; `async_load` does that."""
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, storage_key(entry_id))
        self._profiles: dict[str, dict[str, Any]] = {}
        self._covers: dict[str, dict[str, Any]] = {}

    # ----------------------------------------------------------------- reading
    async def async_load(self) -> None:
        """Read the file, forgiving anything in it that is not what it should be."""
        data = await self._store.async_load() or {}
        profiles = data.get(CONF_PROFILES)
        covers = data.get(CONF_COVERS)
        self._profiles = dict(profiles) if isinstance(profiles, dict) else {}
        self._covers = dict(covers) if isinstance(covers, dict) else {}

    @property
    def raw_profiles(self) -> dict[str, dict[str, Any]]:
        """Every stored profile, by name, exactly as it was written."""
        return dict(self._profiles)

    @property
    def raw_covers(self) -> dict[str, dict[str, Any]]:
        """Every stored per-cover record, by the cover's unique id."""
        return dict(self._covers)

    @property
    def profiles(self) -> dict[str, dict[str, Any]]:
        """The stored profiles in the shape `cover_profiles:` produces."""
        shaped: dict[str, dict[str, Any]] = {}
        for name, data in self._profiles.items():
            if (profile := profile_as_config(name, data)) is not None:
                shaped[name] = profile
        return shaped

    @property
    def calibrations(self) -> dict[str, StoredCalibration]:
        """Every per-cover record, keyed by the cover it is for."""
        return {
            unique_id: stored_calibration({CONF_COVER_UNIQUE_ID: unique_id, **data})
            for unique_id, data in self._covers.items()
        }

    def profile(self, name: str) -> dict[str, Any] | None:
        """One stored profile as it was written, or None."""
        data = self._profiles.get(name)
        return dict(data) if data is not None else None

    def calibration(self, cover_unique_id: str) -> StoredCalibration | None:
        """One cover's record, or None when nothing was ever stored for it."""
        data = self._covers.get(cover_unique_id)
        if data is None:
            return None
        return stored_calibration({CONF_COVER_UNIQUE_ID: cover_unique_id, **data})

    def covers_following(self, name: str) -> list[str]:
        """The unique ids of every cover the store assigns to that profile.

        What a deletion has to name before it happens: "Elimina" says which shutters
        lose the profile, and the confirmation screen is the only place the user finds
        out before the shutters do.
        """
        return sorted(
            unique_id
            for unique_id, data in self._covers.items()
            if data.get(CONF_PROFILE) == name
        )

    # ----------------------------------------------------------------- writing
    async def _async_save(self) -> None:
        await self._store.async_save({CONF_PROFILES: self._profiles, CONF_COVERS: self._covers})

    async def async_set_profile(self, name: str, data: Mapping[str, Any]) -> None:
        """Store (or replace) the profile called `name`.

        Replacing rather than adding: a user who calibrates the same kind of shutter
        twice means the second measurement, and the covers that follow the name go on
        following it. Nothing else has to happen for that to reach them - a follower's
        record holds the *name*, not a copy of the numbers, and `resolve_cover` scales
        the profile to it on every read (final review, RISK-A).
        """
        self._profiles[name] = dict(data)
        await self._async_save()

    async def async_remove_profile(self, name: str) -> list[str]:
        """Forget a profile, and answer with the covers that were following it.

        They lose the assignment rather than keeping a name that resolves to nothing:
        a cover pointed at a profile that is not there falls back to the file anyway
        (`resolve_cover` says so out loud), and a dangling name would make the
        "Profili e tapparelle" screen offer a profile that does not exist.
        """
        if name not in self._profiles:
            return []
        del self._profiles[name]
        orphans = self.covers_following(name)
        for unique_id in orphans:
            record = dict(self._covers[unique_id])
            # The assignment goes, and with it the precedence it carried; the height
            # and the overrides stay, because a tape was held against those.
            record.pop(CONF_PROFILE, None)
            record.pop(CONF_PROFILE_WINS, None)
            if stored_calibration({CONF_COVER_UNIQUE_ID: unique_id, **record}).says_anything:
                self._covers[unique_id] = record
            else:
                # Nothing left in it: a record saying only "no profile, no height, no
                # overrides" is a row on the "Calibrazioni" screen with nothing in it.
                del self._covers[unique_id]
        await self._async_save()
        return orphans

    async def async_set_calibration(self, cover_unique_id: str, data: Mapping[str, Any]) -> None:
        """Store (or replace) one cover's record."""
        record = {key: value for key, value in data.items() if key != CONF_COVER_UNIQUE_ID}
        self._covers[cover_unique_id] = record
        await self._async_save()

    async def async_remove_calibration(self, cover_unique_id: str) -> bool:
        """Forget one cover's record; False when there was none."""
        if cover_unique_id not in self._covers:
            return False
        del self._covers[cover_unique_id]
        await self._async_save()
        return True

    async def async_set_assignments(
        self, assignments: Mapping[str, tuple[str | None, float | None]]
    ) -> bool:
        """Point covers at profiles (and record their heights); True when anything moved.

        The write of the "Profili e tapparelle" screen. Assigning a profile is a
        statement about this window made after the file was written, so it is stored
        with `profile_wins` and the profile's values are put above the keys the file
        writes for that cover (final review, RISK-B: this screen and path B now mean
        the same thing by the same sentence). A cover assigned to no profile keeps
        whatever else was measured on it - the overrides are measurements of that
        window and have nothing to do with which kind of shutter it is.
        """
        changed = False
        for unique_id, (profile, height) in assignments.items():
            record = dict(self._covers.get(unique_id) or {})
            before = dict(record)
            if profile is None:
                record.pop(CONF_PROFILE, None)
                record.pop(CONF_PROFILE_WINS, None)
            else:
                record[CONF_PROFILE] = profile
                record[CONF_PROFILE_WINS] = True
            if height is not None:
                record[CONF_HEIGHT] = float(height)
            if record == before:
                continue
            changed = True
            if stored_calibration({CONF_COVER_UNIQUE_ID: unique_id, **record}).says_anything:
                record.setdefault(CONF_SOURCE, CALIBRATION_SOURCE_GUIDED)
                record[CONF_MEASURED_AT] = record.get(CONF_MEASURED_AT) or dt_util.utcnow().isoformat()
                self._covers[unique_id] = record
            else:
                self._covers.pop(unique_id, None)
        if changed:
            await self._async_save()
        return changed

    # ------------------------------------------------------------------ migration
    async def async_import_legacy_subentries(self, entry: ConfigEntry) -> int:
        """Move a 0.5.0-draft installation into the store, once, and tidy up after it.

        The two subentry types held exactly this data; what they could not hold was a
        user interface worth using. Anything already in the store wins - the store is
        the newer statement by construction, because nothing writes subentries any
        more - and every subentry read is removed, so the integration page loses the
        stray rows and Home Assistant stops grouping the devices under them.
        """
        imported = 0
        for subentry in list(entry.subentries.values()):
            data = dict(subentry.data)
            if subentry.subentry_type == LEGACY_SUBENTRY_COVER_PROFILE:
                name = str(data.get(CONF_NAME) or subentry.title)
                if name and name not in self._profiles:
                    self._profiles[name] = data
                    imported += 1
            elif subentry.subentry_type == LEGACY_SUBENTRY_COVER_CALIBRATION:
                unique_id = str(data.get(CONF_COVER_UNIQUE_ID) or "")
                if unique_id and unique_id not in self._covers:
                    self._covers[unique_id] = {
                        key: value for key, value in data.items() if key != CONF_COVER_UNIQUE_ID
                    }
                    imported += 1
            else:
                continue
            self._hass.config_entries.async_remove_subentry(entry, subentry.subentry_id)
        if imported:
            await self._async_save()
            LOGGER.info(
                "Moved %s stored cover calibration(s) of %s out of the config subentries "
                "and into the integration's own storage",
                imported,
                entry.title,
            )
        return imported


async def async_get_store(hass: HomeAssistant, entry: ConfigEntry) -> CalibrationStore:
    """The loaded store of this entry, reading it from disk the first time."""
    stores: dict[str, CalibrationStore] = hass.data.setdefault(STORE_DATA_KEY, {})
    store = stores.get(entry.entry_id)
    if store is None:
        store = CalibrationStore(hass, entry.entry_id)
        await store.async_load()
        stores[entry.entry_id] = store
    return store


@callback
def loaded_store(hass: HomeAssistant, entry: ConfigEntry) -> CalibrationStore | None:
    """The store of this entry if it has already been read, without reading it.

    What the cover platform uses: `async_setup_entry` loads the store before it
    forwards the platforms, so this is never None during a setup - and a caller that
    somehow arrives earlier gets the file's numbers rather than an await in a
    constructor.
    """
    return (hass.data.get(STORE_DATA_KEY) or {}).get(entry.entry_id)


@callback
def async_forget_store(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop the cached store (the entry is going away, or being set up again)."""
    (hass.data.get(STORE_DATA_KEY) or {}).pop(entry.entry_id, None)


async def async_remove_store(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the stored calibrations of an entry the user removed."""
    async_forget_store(hass, entry)
    await Store(hass, STORAGE_VERSION, storage_key(entry.entry_id)).async_remove()


# ----------------------------------------------------------------------- merging
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

    The profile is scaled here, on every read, rather than copied into the record when
    it is assigned: a `cover_profiles:` profile corrected in `myhome.yaml` therefore
    reaches every window that follows it on the next reload, which a stored copy could
    only have managed for the profiles the store itself owns (final review, RISK-A).

    Nothing here can fail: a record naming a profile that no longer exists falls back
    to the file, because a shutter that stops working because a profile was renamed
    would be worse than one that stops where it used to.
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

    # "This cover follows that profile, and I mean it": the two screens that say so
    # (path B, "Assegna un profilo") put the profile above the keys the file writes for
    # this cover - and still below a tape held against this window. Without the flag
    # the profile stays where spec 1.3 puts it, under the file.
    wins = calibration is not None and calibration.follows_a_profile

    values: dict[str, Any] = {}
    for key in COVER_CALIBRATION_KEYS:
        if key in overrides:
            values[key] = overrides[key]
        elif wins and key in derived:
            values[key] = derived[key]
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

    if calibration is not None and calibration.is_a_measurement:
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
    """`resolve_cover` with both kinds of stored data read off the loaded store.

    The one call the cover platform makes. A store that has not been loaded (an entry
    whose setup never got that far) resolves to the file alone.
    """
    store = loaded_store(hass, entry)
    return resolve_cover(
        device,
        profiles=merged_profiles(yaml_profiles, store.profiles if store else {}),
        calibration=store.calibration(unique_id) if store else None,
    )


@callback
def describe_profile(name: str, data: Mapping[str, Any]) -> str:
    """The numbers of one profile, as a block "Vedi i valori" can show.

    The nested keys are left out: `raw` is the measurements the flow kept for a human
    to argue with later, and a screen that printed them would bury the six numbers the
    user came to look at.
    """
    lines = [
        f"{key}: {value}"
        for key, value in data.items()
        if key not in (CONF_RAW, CONF_NAME) and not isinstance(value, dict)
    ]
    return "```yaml\n" + "\n".join(lines) + "\n```"


__all__ = [
    "PROFILE_NAME_PATTERN",
    "STORAGE_VERSION",
    "STORE_DATA_KEY",
    "CalibrationStore",
    "ResolvedCover",
    "StoredCalibration",
    "async_forget_store",
    "async_get_store",
    "async_remove_store",
    "cover_calibration_data",
    "cover_profile_data",
    "describe_profile",
    "loaded_store",
    "merged_profiles",
    "profile_as_config",
    "profile_overrides",
    "reset_name_clash_warnings",
    "resolve_cover",
    "resolve_cover_config",
    "storage_key",
    "stored_calibration",
]
