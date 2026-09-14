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

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CALIBRATION_KEY_ORIGIN_DEFAULT,
    CALIBRATION_KEY_ORIGIN_FILE,
    CALIBRATION_KEY_ORIGIN_OWN,
    CALIBRATION_KEY_ORIGIN_PROFILE,
    CALIBRATION_ORIGIN_ADJUSTED,
    CALIBRATION_ORIGIN_DEFAULTS,
    CALIBRATION_ORIGIN_FILE,
    CALIBRATION_ORIGIN_INHERITED,
    CALIBRATION_ORIGIN_MEASURED,
    CALIBRATION_SOURCE_ADJUSTED,
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
    CONF_MEASURED_ON,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_ORDER,
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
#
# ...and it is no longer than this. The length is part of the pattern rather than a
# second check beside it, so that the two readers of the pattern - the guided dialog
# (`calibration_flow._NAME_RE`) and the panel (`panel_write._refuse_a_bad_name`) - cannot
# come to disagree about what a usable name is: the panel must never refuse a name the
# dialog accepts, and the one way to guarantee that is for there to be one rule.
#
# Sixty-four characters is longer than any name a person types and short enough that the
# string is bounded everywhere it ends up: a key of the `.storage` file, a segment of the
# panel's own hash route, a `{profile}` in a refusal, a heading on a card. Without it the
# only bound was the WebSocket frame limit, which is not a bound anybody chose.
PROFILE_NAME_MAX_LENGTH = 64
PROFILE_NAME_PATTERN = rf"^[A-Za-z0-9_]{{1,{PROFILE_NAME_MAX_LENGTH}}}$"

# One store per config entry, version 1. The entry id is in the key because a house
# with two gateways has two sets of shutters and one set of files.
STORAGE_VERSION = 1

# ...and minor 2 from 0.6.0 on: the flat `order` list at the top level and the two
# provenance keys of a profile (`measured_on`, `measured_at`).
#
# The *minor* goes up and the major stays where it is, on purpose. `Store` migrates on
# a minor mismatch as readily as on a major one, and both additions are purely
# additive: a user who tries 0.6.0 and rolls back to 0.5.0 hands the file to a store
# built at minor 1, which reads `profiles` and `covers` exactly as it always did and
# ignores the third key. A major bump would have made that rollback a data loss.
STORAGE_MINOR_VERSION = 2


def storage_key(entry_id: str) -> str:
    """The `.storage` file one gateway's calibrations live in."""
    return f"{DOMAIN}.calibration.{entry_id}"


# Where the loaded stores are kept. Not under `hass.data[DOMAIN]`, which holds only
# per-gateway dicts keyed by MAC address and nothing else (const.py, core-03).
STORE_DATA_KEY = f"{DOMAIN}_calibration_stores"

# ...and where the panel's one-slot undo of each gateway lives. The slot belongs to
# `panel_write.py`, which is the only thing that fills it and the only thing that spends
# it; the *key* is here because this module is the one that knows when the records under
# that slot have stopped being the records it was taken against.
#
# An undo is a write of the file as it was before one particular change. That is worth
# offering while nothing else has touched the file, and is a silent data loss the moment
# something has: the guided calibration writes the same records through the same store
# (`async_step_save`, the hand edit, "Elimina"), and before this the offer survived all
# three. Three minutes with a tape against a window, and an "Annulla" still on the screen
# from before it, put the old numbers back with nothing saying so.
#
# So every save withdraws it - see `CalibrationStore._async_save`, which is the one
# chokepoint every writer of this module goes through. A panel write withdraws its
# predecessor on the way past and then installs its own (`panel_write._remember` runs
# after the command it is remembering), which is the behaviour that was already
# documented and is now also true of the writers this module has that the panel does not.
UNDO_DATA_KEY = f"{DOMAIN}_panel_undo"


@callback
def forget_the_undo(hass: HomeAssistant, entry_id: str) -> None:
    """Withdraw the panel's outstanding "Annulla" for one gateway.

    Called on every write of the store, from `_async_save`. Doing nothing when there is
    no slot is the common case by a long way - most installations never open the panel -
    so this is a `dict.get` and a `pop` and is meant to be.
    """
    slots = hass.data.get(UNDO_DATA_KEY)
    if slots:
        slots.pop(entry_id, None)

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
def keys_written_by_the_file(device: Mapping[str, Any]) -> set[str]:
    """Which travel keys `myhome.yaml` really states for this cover, fallbacks included.

    The validator records the keys it actually read (`keys_from_file`); this widens that
    by what one written key says about another, exactly as `_finalize_cover` widens the
    values themselves - a cover whose file says `roll: 1.5` has stated both directional
    rolls, and one that says `opening_time:` has stated the downward run too.

    One function because there are two readers and they must not disagree: the
    precedence below decides that such a key comes from the *file*, and the panel's
    detail view prints what the file writes for it beside that word. Answering the two
    questions from two different sets is how a screen ends up calling the user's own
    `roll: 1.5` the integration's default.
    """
    written = set(device.get(CONF_KEYS_FROM_FILE) or ())
    for key, implied in _IMPLIED_BY_THE_FILE.items():
        if key in written:
            written.update(implied)
    return written


@callback
def _a_stored_number(value: Any) -> float | None:
    """One number as a `.storage` file holds it, or None when it is not one.

    Every number below this line has been through a JSON file that a person is allowed
    to open in an editor, so `float(value)` is a call that can raise on a byte nobody
    typed on purpose - and raising here takes the whole cover platform down, because
    the resolution runs inside `cover.async_setup_entry`. A key that is not a number is
    therefore a key that was never said, which is the same answer the file would give
    by leaving it out, and the shutter goes on running on what is left.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@callback
def _records_only(
    section: Mapping[str, Any], what: str, entry_id: str
) -> dict[str, dict[str, Any]]:
    """The entries of one stored section that are records, and a word about the rest.

    A record is a mapping keyed by a string; anything else in that place is a file
    somebody edited by hand (or a section a future version writes differently), and it
    is dropped rather than handed on. Dropping it here, once, is what keeps every
    reader below - `profile_as_config`, `stored_calibration`, `covers_following`,
    `calibrations` - from having to ask whether its own input is a mapping, and what
    stops a single bad line in `.storage` from taking every shutter of the gateway off
    the screen with an `AttributeError` inside the cover platform's setup.
    """
    kept: dict[str, dict[str, Any]] = {}
    for key, value in section.items():
        if isinstance(key, str) and isinstance(value, Mapping):
            kept[key] = dict(value)
        else:
            LOGGER.warning(
                "Ignoring a stored %s that is not a record (%s, in the calibration file "
                "of %s); the shutters go on running on what is left",
                what,
                key,
                entry_id,
            )
    return kept


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
    measured_on: str | None = None,
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

    `measured_on` is that same window as a **unique id** (0.6.0). The name beside it is
    the name that window had on the day and is what a sentence prints; the id is what a
    screen can follow back to the cover that is there now, and what survives a rename.
    It is written by the one path that really measured a shutter and is never derived
    from anything: a profile that arrives without it - written by hand, imported, or
    stored before 0.6.0 - keeps arriving without it, and the screens say "provenance
    not recorded" rather than guessing which window it might have been.
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
    if measured_on:
        data[CONF_MEASURED_ON] = measured_on
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
    stored = data.get(CONF_OVERRIDES)
    overrides = stored if isinstance(stored, Mapping) else {}
    profile = data.get(CONF_PROFILE)
    return StoredCalibration(
        cover_unique_id=str(data.get(CONF_COVER_UNIQUE_ID, "")),
        # Every field is read the way the file may really hold it rather than the way
        # the flow writes it: this record has been through a JSON file a person can
        # edit, and a `TypeError` here is raised inside the cover platform's setup.
        profile=profile if isinstance(profile, str) else None,
        profile_wins=bool(data.get(CONF_PROFILE_WINS)),
        height=_a_stored_number(data.get(CONF_HEIGHT)),
        overrides={
            key: number
            for key, value in overrides.items()
            if key in COVER_CALIBRATION_KEYS and (number := _a_stored_number(value)) is not None
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
    opening = _a_stored_number(data.get(CONF_OPENING_TIME))
    reference = _a_stored_number(data.get(CONF_REFERENCE_HEIGHT))
    if not name or opening is None or not reference:
        LOGGER.warning(
            "Ignoring a stored cover profile without a name, an opening time or a "
            "reference height (%s)",
            name or "unnamed",
        )
        return None

    def number(key: str, fallback: float) -> float:
        """One of the profile's numbers, or the fallback where the file has nonsense."""
        read = _a_stored_number(data.get(key))
        return fallback if read is None else read

    closing_roll = number(CONF_CLOSING_ROLL, number(CONF_ROLL, 1.0))
    return {
        CONF_REFERENCE_HEIGHT: reference,
        CONF_OPENING_TIME: opening,
        CONF_CLOSING_TIME: number(CONF_CLOSING_TIME, opening),
        CONF_SLAT_TIME: number(CONF_SLAT_TIME, 0.0),
        # `roll` is the fallback of the two directional ones and the one
        # `derive_cover_from_profile` grows the *curtain time* from, which is a length
        # of fabric and therefore the closing one (see that function).
        CONF_ROLL: closing_roll,
        CONF_OPENING_ROLL: number(CONF_OPENING_ROLL, closing_roll),
        CONF_CLOSING_ROLL: closing_roll,
        # Never measured by the flow, never scaled by the profile: constants of the
        # installation (0.4.4).
        CONF_STOP_LATENCY: number(CONF_STOP_LATENCY, DEFAULT_STOP_LATENCY),
        CONF_START_DELAY: number(CONF_START_DELAY, DEFAULT_START_DELAY),
    }


@callback
def profile_provenance(data: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Where a stored profile was measured, as `(cover unique id, ISO date)`.

    `(None, None)` for a profile that never said - which is every profile on every
    installation upgraded from 0.5.0, and every profile a user wrote into the store by
    hand. Read in one place so the panel and any screen after it answer the question
    the same way, and so that "not recorded" is a value and not a missing key somebody
    has to remember to check for.
    """
    measured_on = data.get(CONF_MEASURED_ON)
    measured_at = data.get(CONF_MEASURED_AT)
    return (
        str(measured_on) if measured_on else None,
        str(measured_at) if measured_at else None,
    )


@callback
def normalised_order(order: Iterable[Any]) -> list[str]:
    """A stored order made safe to use: strings, no blanks, no repeats, order kept.

    The list is user data that has been through a browser, a socket and a JSON file,
    so nothing about it is guaranteed. Ids that name no cover are *not* dropped here -
    see `CalibrationStore.ordered`: a gateway that is halfway through a reload, or a
    shutter commented out of `myhome.yaml` for an afternoon, would otherwise have its
    place in the list thrown away by a read.
    """
    seen: set[str] = set()
    kept: list[str] = []
    for item in order:
        if not isinstance(item, str) or not item or item in seen:
            continue
        seen.add(item)
        kept.append(item)
    return kept


class _MyHomeCalibrationStore(Store[dict[str, Any]]):
    """The `Store` behind `CalibrationStore`, with the one migration it has.

    Minor 1 -> 2 (0.5.0 -> 0.6.0) adds the top-level `order` key and nothing else. The
    two profile keys `measured_on` and `measured_at` are deliberately *not* filled in
    here: nothing in 0.5.0 recorded which window a profile was measured on, and the
    only way to guess it would be to look for a follower whose overrides happen to
    match the profile's values - a heuristic that is sometimes right, silently wrong
    the rest of the time, and impossible for the user to tell apart from a fact. A
    profile that does not know says so (maintainer's decision, 13 Sept).
    """

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Bring a file written by an older MyHOME up to the shape read below."""
        if old_major_version > STORAGE_VERSION:
            # A file from a future version: `Store` has already refused anything past
            # `max_readable_version`, so this is unreachable today and is here so that
            # a later major does not silently fall through the branch below.
            raise NotImplementedError
        data = dict(old_data)
        if old_minor_version < 2:
            data.setdefault(CONF_ORDER, [])
        return data


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
        self._entry_id = entry_id
        self._store: Store[dict[str, Any]] = _MyHomeCalibrationStore(
            hass,
            STORAGE_VERSION,
            storage_key(entry_id),
            minor_version=STORAGE_MINOR_VERSION,
        )
        self._profiles: dict[str, dict[str, Any]] = {}
        self._covers: dict[str, dict[str, Any]] = {}
        self._order: list[str] = []

    # ----------------------------------------------------------------- reading
    async def async_load(self) -> None:
        """Read the file, forgiving anything in it that is not what it should be."""
        data = await self._store.async_load() or {}
        profiles = data.get(CONF_PROFILES)
        covers = data.get(CONF_COVERS)
        order = data.get(CONF_ORDER)
        self._profiles = (
            _records_only(profiles, "cover profile", self._entry_id)
            if isinstance(profiles, dict)
            else {}
        )
        self._covers = (
            _records_only(covers, "calibration", self._entry_id)
            if isinstance(covers, dict)
            else {}
        )
        # Forgiven exactly as the two dicts above are: a list that is not a list is no
        # list at all, and the shutters go back to the file's own order.
        self._order = normalised_order(order) if isinstance(order, list) else []

    @property
    def raw_profiles(self) -> dict[str, dict[str, Any]]:
        """Every stored profile, by name, exactly as it was written."""
        return dict(self._profiles)

    @property
    def raw_covers(self) -> dict[str, dict[str, Any]]:
        """Every stored per-cover record, by the cover's unique id."""
        return dict(self._covers)

    @property
    def raw_order(self) -> list[str]:
        """The order the user dragged the shutters into, exactly as it is stored.

        Unique ids, some of which may name nothing any more. `ordered` is what a screen
        wants; this is what a diagnostic dump and the write path want.
        """
        return list(self._order)

    def ordered(self, unique_ids: Iterable[str]) -> list[str]:
        """Those shutters, in the order the user put them in.

        The rule, and the only one: a cover the list names comes first, in the list's
        order; a cover it does not name follows, in the order it was handed in - which
        is the gateway's, which is `myhome.yaml`'s. So a shutter added to the file
        lands at the end of its group rather than at a place nobody chose for it, a
        shutter removed from the file takes no gap with it, and neither event needs the
        stored list rewritten. Covers are grouped by their profile *before* this is
        called: the list orders within a group and never decides which group anything
        is in.
        """
        known = list(unique_ids)
        rest = set(known)
        first = [unique_id for unique_id in self._order if unique_id in rest]
        placed = set(first)
        return first + [unique_id for unique_id in known if unique_id not in placed]

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
        """Write the file, and withdraw whatever undo was standing against the old one.

        The one chokepoint: every writer in this module comes through here, which is why
        the withdrawal is here and not in each of them. See `UNDO_DATA_KEY` for what the
        offer was surviving before, and `panel_write.async_write` for why a panel write
        that installs its own token immediately afterwards is unaffected.
        """
        forget_the_undo(self._hass, self._entry_id)
        await self._store.async_save(
            {
                CONF_PROFILES: self._profiles,
                CONF_COVERS: self._covers,
                CONF_ORDER: self._order,
            }
        )

    async def async_set_order(
        self, order: Sequence[str], *, known: Iterable[str] | None = None
    ) -> bool:
        """Replace the whole order with that one; True when the file changed.

        The whole list and not a move, because the panel sends the whole list: the
        group the user dropped a shutter into is re-stated from top to bottom, which is
        what makes assignment and position one write and leaves nothing to reconcile.

        `known` is the covers that exist, when the caller knows them - the write path
        does - and ids outside it are dropped, so a browser tab left open across a
        reconfiguration cannot write back a shutter that is gone. A caller that does
        not pass it (the migration path, a test) keeps whatever it sent.
        """
        wanted = normalised_order(order)
        if known is not None:
            allowed = set(known)
            wanted = [unique_id for unique_id in wanted if unique_id in allowed]
        if wanted == self._order:
            return False
        self._order = wanted
        await self._async_save()
        return True

    async def async_restore(
        self,
        *,
        profiles: Mapping[str, Mapping[str, Any] | None] | None = None,
        covers: Mapping[str, Mapping[str, Any] | None] | None = None,
        order: Sequence[str] | None = None,
    ) -> bool:
        """Put these records back exactly as they are given; True when anything moved.

        The undo path, and the only thing in this module that writes a record without
        deciding anything about it. Every other writer has an opinion - `async_set_-
        assignments` drops a record that would say nothing, `async_remove_profile` takes
        the assignment off every follower - and an undo that went through them would be
        a *second* write of its own rather than the first one taken back. What is handed
        here is what was read out of the file before the write, key by key, and `None`
        means the key was not there and must not be there afterwards either.

        One save for the lot, so a half-applied undo is not a state the file can be left
        in. A key that is not mentioned is not touched, which is what makes the undo of
        one command safe on a file something else has written to meanwhile.
        """
        changed = False
        for name, data in (profiles or {}).items():
            if data is None:
                changed = self._profiles.pop(name, None) is not None or changed
            elif self._profiles.get(name) != data:
                self._profiles[name] = dict(data)
                changed = True
        for unique_id, record in (covers or {}).items():
            if record is None:
                changed = self._covers.pop(unique_id, None) is not None or changed
            elif self._covers.get(unique_id) != record:
                self._covers[unique_id] = dict(record)
                changed = True
        if order is not None:
            wanted = normalised_order(order)
            if wanted != self._order:
                self._order = wanted
                changed = True
        if changed:
            await self._async_save()
        return changed

    async def async_set_profile(self, name: str, data: Mapping[str, Any]) -> None:
        """Store (or replace) the profile called `name`.

        Replacing rather than adding: a user who calibrates the same kind of shutter
        twice means the second measurement, and the covers that follow the name go on
        following it. Nothing else has to happen for that to reach them - a follower's
        record holds the *name*, not a copy of the numbers, and `resolve_cover` scales
        the profile to it on every read (final review, RISK-A).

        Whatever the caller built is written verbatim, `measured_on` and `measured_at`
        included: this is the one place a profile's provenance is recorded and it is
        never filled in here, because the only thing that knows which window was under
        the tape is the conversation that measured it.
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
class ResolvedKey:
    """One key of the travel model: the number, and which of the four said it."""

    value: Any
    origin: str


@callback
def resolve_cover_keys(
    device: Mapping[str, Any],
    *,
    overrides: Mapping[str, float],
    derived: Mapping[str, Any],
    written: Iterable[str],
    wins: bool,
    keys: Iterable[str] = COVER_CALIBRATION_KEYS,
) -> dict[str, ResolvedKey]:
    """The precedence of the module docstring, key by key, and the only place it lives.

    `resolve_cover` below is this loop plus the reading of the flags off it; the panel's
    detail view is this loop run twice, once as things are and once as they would be
    with this window's own numbers taken away, which is what "eredita N" under an empty
    field means. Neither has a second copy of the order, because a screen that disagreed
    with the shutter about where a number came from would make the whole panel
    untrustworthy and would do it silently.

    `written` is the set of keys `myhome.yaml` really carries for this cover (the
    validator's `keys_from_file`, widened by what one written key implies about
    another); `derived` is the profile already scaled to this window; `wins` is the
    record's "somebody said, on this installation, that this shutter is one of those".
    """
    written = set(written)
    resolved: dict[str, ResolvedKey] = {}
    for key in keys:
        if key in overrides:
            resolved[key] = ResolvedKey(overrides[key], CALIBRATION_KEY_ORIGIN_OWN)
        elif wins and key in derived:
            resolved[key] = ResolvedKey(derived[key], CALIBRATION_KEY_ORIGIN_PROFILE)
        elif key in written:
            resolved[key] = ResolvedKey(device[key], CALIBRATION_KEY_ORIGIN_FILE)
        elif key in derived:
            resolved[key] = ResolvedKey(derived[key], CALIBRATION_KEY_ORIGIN_PROFILE)
        elif key in device:
            # Whatever the validator already resolved: the file's own profile chain,
            # and below that the numbers this integration gives any shutter.
            resolved[key] = ResolvedKey(device[key], CALIBRATION_KEY_ORIGIN_DEFAULT)
    return resolved


@dataclass(frozen=True, slots=True)
class ResolvedCover:
    """The travel model one cover really runs on, and where it came from.

    `source` is the token the `Calibration source` attribute carries and `origin` the
    same answer as one of `CALIBRATION_ORIGINS`, for the screens that say it in words.
    Both are decided in one place (`resolve_cover`), so a shutter the attribute calls
    `profile tall, adjusted` cannot be a shutter the dialog calls measured.

    `keys` is the same answer once per key, and `inherited` is what each key would fall
    back to if this window's own measurements were removed - the placeholder the detail
    screen prints under an empty field, and the destination "Rimuovi la misura" has to
    name before it does anything.
    """

    values: dict[str, Any]
    source: str
    origin: str = CALIBRATION_ORIGIN_DEFAULTS
    profile: str | None = None
    height: float | None = None
    keys: Mapping[str, ResolvedKey] = field(default_factory=dict)
    inherited: Mapping[str, ResolvedKey] = field(default_factory=dict)


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
    written = keys_written_by_the_file(device)
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

    resolved = resolve_cover_keys(
        device, overrides=overrides, derived=derived, written=written, wins=wins
    )
    # ...and the same loop again with this window's own numbers taken away, which is
    # what every one of its keys would fall back to. Nothing here reads it; the panel's
    # detail screen does, and it is computed here so that "eredita N" and the number
    # the shutter runs on can never come from two different rules.
    inherited = resolve_cover_keys(
        device, overrides={}, derived=derived, written=written, wins=wins
    )
    values: dict[str, Any] = {key: item.value for key, item in resolved.items()}
    # ...and, per key, which of the two sources the user asks about answered it: the
    # profile, or a tape held against this window. What `Calibration source` says is
    # read off these two below, because "measured" and "inherited" are not the only two
    # answers - a correction of the run times alone leaves a shutter running on both.
    # Only the five keys a guided calibration ever measures are counted: `roll` is the
    # fallback of the two directional ones and is never what the shutter runs on when
    # they are set, so a profile answering for it is not the profile being in use.
    measurable = {key for key, _digits in _DERIVED_OVERRIDE_KEYS}
    said = {
        origin: any(
            item.origin == origin and key in measurable for key, item in resolved.items()
        )
        for origin in (
            CALIBRATION_KEY_ORIGIN_OWN,
            CALIBRATION_KEY_ORIGIN_PROFILE,
            CALIBRATION_KEY_ORIGIN_FILE,
        )
    }
    from_the_profile = said[CALIBRATION_KEY_ORIGIN_PROFILE]
    of_its_own = said[CALIBRATION_KEY_ORIGIN_OWN]
    of_the_file = said[CALIBRATION_KEY_ORIGIN_FILE]
    if height is not None:
        values[CONF_HEIGHT] = height
    if name is not None:
        values[CONF_PROFILE] = name

    named = name is not None and name in profiles
    if calibration is not None and calibration.is_a_measurement:
        # Measured, and then: adjusted when the profile is still answering for some of
        # the keys this window did not measure, plain `guided` when it is not.
        origin = (
            CALIBRATION_ORIGIN_ADJUSTED
            if named and from_the_profile and of_its_own
            else CALIBRATION_ORIGIN_MEASURED
        )
    elif named:
        origin = CALIBRATION_ORIGIN_INHERITED
    elif of_the_file:
        origin = CALIBRATION_ORIGIN_FILE
    else:
        # Nothing stored, nothing written: the shutter is running on the numbers this
        # integration would give any shutter. The attribute says `yaml` for this and
        # for the line above alike, because what it answers is "the file or the store";
        # the screens tell the two apart, because "somebody wrote this" and "nobody
        # ever said" are different news to the person reading them.
        origin = CALIBRATION_ORIGIN_DEFAULTS
    source = {
        CALIBRATION_ORIGIN_MEASURED: CALIBRATION_SOURCE_GUIDED,
        CALIBRATION_ORIGIN_ADJUSTED: (
            f"{CALIBRATION_SOURCE_PROFILE} {name}, {CALIBRATION_SOURCE_ADJUSTED}"
        ),
        CALIBRATION_ORIGIN_INHERITED: f"{CALIBRATION_SOURCE_PROFILE} {name}",
    }.get(origin, CALIBRATION_SOURCE_YAML)
    return ResolvedCover(
        values=values,
        source=source,
        origin=origin,
        profile=name,
        height=height,
        keys=resolved,
        inherited=inherited,
    )


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
    "PROFILE_NAME_MAX_LENGTH",
    "PROFILE_NAME_PATTERN",
    "STORAGE_MINOR_VERSION",
    "STORAGE_VERSION",
    "STORE_DATA_KEY",
    "UNDO_DATA_KEY",
    "CalibrationStore",
    "ResolvedCover",
    "ResolvedKey",
    "StoredCalibration",
    "async_forget_store",
    "async_get_store",
    "async_remove_store",
    "cover_calibration_data",
    "cover_profile_data",
    "describe_profile",
    "forget_the_undo",
    "keys_written_by_the_file",
    "loaded_store",
    "merged_profiles",
    "normalised_order",
    "profile_as_config",
    "profile_overrides",
    "profile_provenance",
    "reset_name_clash_warnings",
    "resolve_cover",
    "resolve_cover_config",
    "resolve_cover_keys",
    "storage_key",
    "stored_calibration",
]
