"""What the panel writes: the nine commands, and the one place that decides them.

`panel_data.py` is the read half and writes nothing; this is its opposite number, and
between them they are everything the panel can do to a gateway. `websocket_api.py` is
deliberately thin over both - it unwraps a frame, calls one function here, and sends
back what it is given - so that "what does `assign` do" has an answer in one file that
can be read without a socket in it.

**Nothing here decides anything twice.** Every rule these commands enforce already
existed, on the other side of a dialog, and is imported rather than restated:

* the ranges and the number parsing are `calibration_flow`'s own (`PROFILE_FIELDS`,
  `CALIBRATION_FIELDS`, `MIN_HEIGHT_CM`/`MAX_HEIGHT_CM`, `parse_number`), so a value the
  guided conversation refuses is a value the panel refuses, in the same words;
* the precedence is `resolve_cover`'s, reached through `panel_data`, and is never
  re-derived to work out what a write would come to;
* what a record means - when an assignment wins over the file, when a record has stopped
  saying anything and must go - is `calibration_store`'s, through `cover_calibration_-
  data`, `async_set_assignments` and `async_remove_profile`.

**Three rules every write obeys.**

* *Refused while a measurement is running.* Any cover of the entry with `calibrating`
  true and the whole entry is read-only: a guided conversation is holding a shutter, has
  numbers half measured, and will write them when it is done. The panel is told before
  it tries - `overview.measuring`, and the `measuring` event of the subscription - so
  this is the backstop and not the user interface.
* *One write at a time.* A second write that arrives while one is being applied is
  refused rather than queued. They are not independent: each reads the store, decides
  against what it read, and writes the whole of what it decided.
* *Every write answers with a fresh `overview`* and publishes the same to every
  subscriber, plus a token that takes it back. The client replaces its model; it never
  merges (CONTRACT §1).

**And no reload.** A write reaches the shutters through `SIGNAL_CALIBRATION_CHANGED`,
which makes every cover of that gateway re-resolve and swap its numbers in place (plan
decision 4, `cover.async_apply_calibration`). The config entry is not touched.
"""

from __future__ import annotations

import re
import secrets
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.websocket_api import (
    ERR_NOT_ALLOWED,
    ERR_NOT_FOUND,
    ERR_NOT_SUPPORTED,
    ERR_SERVICE_VALIDATION_ERROR,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .calibration_flow import (
    CALIBRATION_FIELDS,
    ERROR_INVALID_NAME,
    ERROR_NOT_A_NUMBER,
    ERROR_OUT_OF_RANGE,
    MAX_HEIGHT_CM,
    MIN_HEIGHT_CM,
    NO_PROFILE,
    PROFILE_FIELDS,
    parse_number,
)
from .calibration_store import (
    PROFILE_NAME_PATTERN,
    CalibrationStore,
    async_get_store,
    cover_calibration_data,
    cover_profile_data,
    merged_profiles,
    resolve_cover_config,
    stored_calibration,
)
from .const import (
    CALIBRATION_ORIGIN_FILE,
    CALIBRATION_ORIGIN_INHERITED,
    CALIBRATION_SOURCE_MANUAL,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_HEIGHT,
    CONF_MEASURED_ON,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PROFILE,
    CONF_RAW,
    CONF_REFERENCE_COVER,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
    CONF_SOURCE,
    DOMAIN,
    LOGGER,
    SIGNAL_CALIBRATION_CHANGED,
)
from .panel_data import (
    async_overview,
    basic_covers,
    calibrating_now,
    is_advanced_cover,
    yaml_profiles,
)
from .panel_schemas import (
    ERROR_ADVANCED_COVER,
    ERROR_BUSY_CALIBRATING,
    ERROR_MISSING_TRAVEL,
    ERROR_NAME_IN_USE,
    ERROR_PROFILE_NOT_EDITABLE,
    ERROR_UNDO_EXPIRED,
    ERROR_UNKNOWN_COVER,
    ERROR_UNKNOWN_PROFILE,
    ERROR_WRITE_IN_PROGRESS,
)

# Where the one-slot undo of each entry lives, and where the entries being written to
# right now are remembered. Both in `hass.data` and not in a module global: a test runs
# several Home Assistants in one process, and a lock that outlived one of them would be
# a write refused for a reason nobody could see.
UNDO_DATA_KEY = f"{DOMAIN}_panel_undo"
WRITING_DATA_KEY = f"{DOMAIN}_panel_writing"

# How long a token is worth offering. The strip in the panel offers "Annulla" for a few
# seconds; five minutes is the reading-the-screen-and-changing-your-mind window, after
# which the offer is withdrawn rather than left to apply a state nobody remembers. The
# next write of the same gateway withdraws it too, whatever the clock says: an undo is a
# write of the records as they were, and two writes later "as they were" is a state that
# was never on the screen.
UNDO_TTL = timedelta(minutes=5)

# The five numbers a profile is made of, as the hand-editing form of the guided dialog
# lists them - `reference_height` first, which is the one that scales all the others.
PROFILE_VALUE_FIELDS = tuple(
    (key, low, high) for key, low, high in PROFILE_FIELDS if key != CONF_REFERENCE_HEIGHT
)


class PanelError(Exception):
    """A refusal, in the shape `connection.send_error` wants.

    Carried as an exception so that a command reads as the sequence of things it does
    rather than as a ladder of early returns, and so that the one place that catches it
    (`websocket_api`) is the one place that knows there is a socket at all.
    """

    def __init__(
        self,
        code: str,
        translation_key: str,
        message: str,
        placeholders: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.translation_key = translation_key
        self.message = message
        self.placeholders = dict(placeholders or {})


# ------------------------------------------------------------------------ the undo
@dataclass(frozen=True, slots=True)
class _StoreState:
    """Everything one gateway's store holds, copied out of it.

    Taken before a write and compared with the same thing after it, which is how a
    command gets its undo without keeping a list of what it touched: whatever differs
    *is* what it touched, however many store primitives it went through on the way.
    """

    profiles: dict[str, dict[str, Any]]
    covers: dict[str, dict[str, Any]]
    order: list[str]

    @classmethod
    def of(cls, store: CalibrationStore) -> _StoreState:
        return cls(
            profiles=deepcopy(store.raw_profiles),
            covers=deepcopy(store.raw_covers),
            order=list(store.raw_order),
        )


@dataclass(frozen=True, slots=True)
class _Undo:
    """One write, as the records were before it."""

    token: str
    expires_at: datetime
    profiles: dict[str, dict[str, Any] | None]
    covers: dict[str, dict[str, Any] | None]
    order: list[str] | None = None
    # What the command was, for the log line the undo writes.
    what: str = ""


@dataclass(slots=True)
class _Diff:
    """The keys two snapshots disagree about, and what the first one said about them."""

    profiles: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    covers: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    order: list[str] | None = None

    @property
    def anything(self) -> bool:
        return bool(self.profiles or self.covers) or self.order is not None


@callback
def _diff(before: _StoreState, after: _StoreState) -> _Diff:
    """What `before` said about every record `after` disagrees with.

    Only the records that moved, so an undo of one command leaves alone whatever else
    has been written since - the guided dialog, another gateway's screen - instead of
    restoring a whole file over the top of it.
    """
    diff = _Diff()
    for name in set(before.profiles) | set(after.profiles):
        if before.profiles.get(name) != after.profiles.get(name):
            diff.profiles[name] = before.profiles.get(name)
    for unique_id in set(before.covers) | set(after.covers):
        if before.covers.get(unique_id) != after.covers.get(unique_id):
            diff.covers[unique_id] = before.covers.get(unique_id)
    if before.order != after.order:
        diff.order = list(before.order)
    return diff


@callback
def _remember(hass: HomeAssistant, entry: ConfigEntry, diff: _Diff, what: str) -> str | None:
    """Keep the records as they were, under a new token, and forget the previous one.

    None when the write changed nothing at all, because there is nothing to take back
    and offering "Annulla" for it would be a button that does nothing.
    """
    slots: dict[str, _Undo] = hass.data.setdefault(UNDO_DATA_KEY, {})
    if not diff.anything:
        slots.pop(entry.entry_id, None)
        return None
    token = secrets.token_hex(8)
    slots[entry.entry_id] = _Undo(
        token=token,
        expires_at=dt_util.utcnow() + UNDO_TTL,
        profiles=diff.profiles,
        covers=diff.covers,
        order=diff.order,
        what=what,
    )
    return token


@callback
def _take(hass: HomeAssistant, entry: ConfigEntry, token: str) -> _Undo:
    """The records one token stands for, or the refusal that it stands for nothing."""
    slots: dict[str, _Undo] = hass.data.setdefault(UNDO_DATA_KEY, {})
    undo = slots.get(entry.entry_id)
    if undo is None or undo.token != token or undo.expires_at <= dt_util.utcnow():
        raise PanelError(
            ERR_NOT_FOUND,
            ERROR_UNDO_EXPIRED,
            "There is nothing left to undo: the offer expired, or something else has "
            "been written since",
        )
    slots.pop(entry.entry_id, None)
    return undo


# ------------------------------------------------------------------------ the lock
@callback
def _refuse_if_busy(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Refuse a write while a measurement is running, or while one is being applied."""
    measuring = calibrating_now(hass, entry)
    if measuring:
        unique_id = sorted(measuring)[0]
        name = str(basic_covers(hass, entry).get(unique_id, {}).get("name") or unique_id)
        raise PanelError(
            ERR_NOT_ALLOWED,
            ERROR_BUSY_CALIBRATING,
            f"A guided calibration is running on {name}; nothing can be written to this "
            f"gateway until it is over",
            {"cover": name},
        )
    if entry.entry_id in hass.data.setdefault(WRITING_DATA_KEY, set()):
        raise PanelError(
            ERR_NOT_ALLOWED,
            ERROR_WRITE_IN_PROGRESS,
            "Another change to this gateway is being applied; try again in a moment",
        )


# --------------------------------------------------------------------- validation
@callback
def _number(value: Any, key: str, low: float, high: float) -> float:
    """One number as a person may have typed it, refused in the dialog's own words."""
    number = parse_number(value)
    if number is None:
        raise PanelError(
            ERR_SERVICE_VALIDATION_ERROR,
            ERROR_NOT_A_NUMBER,
            f"{key}: {value!r} is not a number",
            {"key": key},
        )
    if not low <= number <= high:
        raise PanelError(
            ERR_SERVICE_VALIDATION_ERROR,
            ERROR_OUT_OF_RANGE,
            f"{key}: {number} is outside {low}-{high}",
            {"key": key, "min": str(low), "max": str(high)},
        )
    return number


@callback
def _height(value: Any) -> float:
    """A window's travel, in centimetres, within the bounds the guided form uses."""
    return _number(value, CONF_HEIGHT, MIN_HEIGHT_CM, MAX_HEIGHT_CM)


@callback
def _cover_config(hass: HomeAssistant, entry: ConfigEntry, unique_id: str) -> dict[str, Any]:
    """One basic cover of this gateway, or the refusal for whatever else it is.

    "No such shutter" and "a shutter that reports its own position" are two different
    answers and stay two: the second is something this panel does not do, not something
    the user mistyped.
    """
    cfg = basic_covers(hass, entry).get(unique_id)
    if cfg is not None:
        return cfg
    if is_advanced_cover(hass, entry, unique_id):
        raise PanelError(
            ERR_NOT_SUPPORTED,
            ERROR_ADVANCED_COVER,
            f"{unique_id} is an advanced shutter and has no travel model",
            {"cover": unique_id},
        )
    raise PanelError(
        ERR_NOT_FOUND,
        ERROR_UNKNOWN_COVER,
        f"No cover with the unique id {unique_id} on {entry.title}",
        {"cover": unique_id},
    )


@callback
def _stored_profile(store: CalibrationStore, name: str) -> dict[str, Any]:
    """The profile this command may change, or why it may not.

    A `cover_profiles:` profile is a block of the user's own file: the panel shows it,
    says where it comes from, and does not write it. A name nobody defines at all is a
    different answer again.
    """
    profile = store.profile(name)
    if profile is not None:
        return profile
    raise PanelError(
        ERR_NOT_FOUND,
        ERROR_UNKNOWN_PROFILE,
        f"No stored profile called {name}",
        {"profile": name},
    )


@callback
def _refuse_a_file_profile(
    hass: HomeAssistant, entry: ConfigEntry, store: CalibrationStore, name: str
) -> None:
    """...and the same refusal one step earlier, for a name only the file defines."""
    if store.profile(name) is None and name in yaml_profiles(hass, entry):
        raise PanelError(
            ERR_NOT_ALLOWED,
            ERROR_PROFILE_NOT_EDITABLE,
            f"The profile {name} is written in myhome.yaml, which this integration does "
            f"not edit",
            {"profile": name},
        )


# ------------------------------------------------------------------------ the order
@callback
def _profile_now(store: CalibrationStore, cfg: Mapping[str, Any], unique_id: str) -> str:
    """Which group a shutter is in: the profile it follows, or "" for none.

    The stored assignment first and the file's `profile:` after it, which is the order
    the resolution itself reads them in.
    """
    record = store.calibration(unique_id)
    if record is not None and record.profile:
        return str(record.profile)
    return str(cfg.get(CONF_PROFILE) or "")


@callback
def _appended_to_their_groups(
    store: CalibrationStore, covers: Mapping[str, Mapping[str, Any]], moved: Sequence[str]
) -> list[str]:
    """The whole order again, with each moved shutter at the end of its new group.

    What "assigned without a drop position" means: the tap path, the keyboard path and
    "Quale profilo?" all put a window into a group without saying where in it, and the
    end of the group is the one place that is not a place somebody else chose. Groups
    are slices of this one flat list (`CalibrationStore.ordered`), so the splice is
    after the last member the group already has, and a group that has none yet takes the
    end of the list.
    """
    order = store.ordered(list(covers))
    for unique_id in moved:
        if unique_id not in order:  # pragma: no cover - `ordered` names them all
            continue
        order.remove(unique_id)
        group = _profile_now(store, covers[unique_id], unique_id)
        at = len(order)
        for index, other in enumerate(order):
            if _profile_now(store, covers[other], other) == group:
                at = index + 1
        order.insert(at, unique_id)
    return order


# ------------------------------------------------------------------- one cover's record
@callback
def _rewritten_record(
    store: CalibrationStore,
    unique_id: str,
    *,
    height: float | None,
    overrides: Mapping[str, float],
) -> dict[str, Any]:
    """One cover's record with new numbers in it and everything else as it was.

    The profile and its precedence are carried over untouched, exactly as
    `async_step_calibration_edit` carries them: correcting a number by hand says nothing
    about which kind of shutter this is, and a window that was told to follow a profile
    goes on following it with the typed numbers sitting above it.

    The `raw` block is carried over too, which is the one place this differs from the
    dialog's own hand edit (which drops it). It is the measurements the guided
    conversation kept for a human to argue with six months later, and it is where the
    panel reads how thorough that calibration was; correcting one number is not a reason
    to forget either.
    """
    record = store.calibration(unique_id)
    raw = (store.raw_covers.get(unique_id) or {}).get(CONF_RAW)
    return cover_calibration_data(
        unique_id,
        profile=record.profile if record else None,
        profile_wins=bool(record and record.profile_wins),
        height=height,
        overrides=dict(overrides) or None,
        source=CALIBRATION_SOURCE_MANUAL,
        raw=raw,
    )


async def _store_the_record(
    store: CalibrationStore, unique_id: str, data: Mapping[str, Any]
) -> None:
    """Write it, or delete it when it has stopped saying anything.

    A record holding only a source and a timestamp is invisible on every screen that
    lists what `says_anything` and immortal in `.storage` (0.5.0 v2 review, RISK-3);
    the dialog has deleted such a record all along and so does this.
    """
    if stored_calibration(data).says_anything:
        await store.async_set_calibration(unique_id, data)
    else:
        await store.async_remove_calibration(unique_id)


# ------------------------------------------------------------------------ the commands
async def async_assign(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    assignments: Sequence[Mapping[str, Any]],
    order: Sequence[str] | None,
) -> dict[str, Any]:
    """Point shutters at profiles, in one batch, with the order they end up in.

    Assignment and position are one write, because on the screen they are one gesture:
    the shutter is dropped into a group *at a place*, and two writes would leave a
    moment in which it was in the group and nowhere in particular. `order` is the whole
    resulting order; without it, every shutter that changed group goes to the end of the
    one it went to.

    A travel is required of every window that is given a profile, because a profile is
    the measurement of a window of a certain height and there is nothing to scale it by
    otherwise. It may already be known - measured here, or written in the file - and
    where it is not the batch carries it, which is what the review panel's "corse
    mancanti" form collects and is the same write `set_travel` makes on its own.

    Nothing is applied unless every item passes: a batch half written is a screen that
    has to explain which half.
    """
    covers = basic_covers(hass, entry)
    profiles = merged_profiles(yaml_profiles(hass, entry), store.profiles)
    wanted: dict[str, tuple[str | None, float | None]] = {}
    problems: list[_Problem] = []

    for item in assignments:
        unique_id = str(item["cover_unique_id"])
        try:
            cfg = _cover_config(hass, entry, unique_id)
        except PanelError as err:
            problems.append(_Problem(unique_id, err.translation_key, err.placeholders))
            continue
        name = item.get(CONF_PROFILE)
        profile = None if name is None else str(name)
        if profile is not None and profile not in profiles:
            problems.append(_Problem(unique_id, ERROR_UNKNOWN_PROFILE, {"profile": profile}))
            continue
        height: float | None = None
        if item.get(CONF_HEIGHT) is not None:
            try:
                height = _height(item[CONF_HEIGHT])
            except PanelError as err:
                problems.append(_Problem(unique_id, err.translation_key, err.placeholders))
                continue
        if profile is not None and height is None and _known_travel(store, cfg, unique_id) is None:
            problems.append(_Problem(unique_id, ERROR_MISSING_TRAVEL, {}))
            continue
        wanted[unique_id] = (profile, height)

    if problems:
        _refuse_the_batch(problems)

    before = dict(store.raw_covers)
    await store.async_set_assignments(wanted)
    applied = sum(
        1 for unique_id in wanted if before.get(unique_id) != store.raw_covers.get(unique_id)
    )

    if order is not None:
        await store.async_set_order(order, known=covers)
    else:
        moved = [
            unique_id
            for unique_id in wanted
            if before.get(unique_id, {}).get(CONF_PROFILE)
            != store.raw_covers.get(unique_id, {}).get(CONF_PROFILE)
        ]
        if moved:
            await store.async_set_order(
                _appended_to_their_groups(store, covers, moved), known=covers
            )
    return {"applied": applied}


@callback
def _known_travel(
    store: CalibrationStore, cfg: Mapping[str, Any], unique_id: str
) -> float | None:
    """The travel *this* window is already known to have: its record's, else the file's.

    Never a profile's `reference_height`, which is another window's travel and would
    scale a newly assigned profile by the wrong one - `_own_height` in the dialog, and
    the same rule for the same reason.
    """
    record = store.calibration(unique_id)
    if record is not None and record.height:
        return float(record.height)
    if cfg.get(CONF_HEIGHT):
        return float(cfg[CONF_HEIGHT])
    return None


@dataclass(frozen=True, slots=True)
class _Problem:
    """One item of a batch that cannot be written, with the words its refusal needs.

    The placeholders are the item's own - `{profile}` for a profile nobody defines,
    `{key}`/`{min}`/`{max}` for a number outside its range - and they are carried here
    rather than thrown away, because the sentence the user reads is the sentence written
    for that `translation_key` and it asks for them by name. Dropping them is how
    "Weg nimmt eine Zahl zwischen {min} und {max} an." reached a screen (REVIEW lot 6
    §5.1).
    """

    unique_id: str
    key: str
    placeholders: Mapping[str, Any]


@callback
def _refuse_the_batch(problems: Sequence[_Problem]) -> None:
    """One refusal for the batch, saying which item failed and why.

    A WebSocket error carries one key and a sentence, so the key is the first kind of
    problem found and the sentence names every offending shutter with its own reason -
    the panel shows the sentence and marks the rows. A travel nobody has measured is
    reported first when it is there at all: it is the one problem with a form behind it,
    and the screen that collects the missing numbers is the answer to it.

    **Both vocabularies travel.** `{covers}` and `{count}` are the batch's own, and
    `exceptions.missing_travel.message` is written around them; the first offending
    item's placeholders are what every other sentence here is written around, and a
    placeholder a sentence does not use costs nothing while one it does use and does not
    get is a pair of braces on the screen.
    """
    kinds = [problem.key for problem in problems]
    first = ERROR_MISSING_TRAVEL if ERROR_MISSING_TRAVEL in kinds else kinds[0]
    offending = [problem for problem in problems if problem.key == first]
    placeholders: dict[str, Any] = dict(offending[0].placeholders)
    placeholders["covers"] = ", ".join(problem.unique_id for problem in offending)
    placeholders["count"] = str(len(offending))
    raise PanelError(
        ERR_SERVICE_VALIDATION_ERROR,
        first,
        "; ".join(f"{problem.unique_id}: {problem.key}" for problem in problems),
        placeholders,
    )


async def async_reorder(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    order: Sequence[str],
    group: str | None,
    whole: bool,
) -> dict[str, Any]:
    """Put the shutters in that order.

    Two shapes, because the panel has two gestures. Dragging inside one group re-states
    that group from top to bottom and says which group it is (`profile`, `null` for
    "Senza profilo"); the group's members are put back into the one flat stored order in
    the places that group already occupies, so the other groups do not move at all.
    Without `profile` the list is the whole gateway's order and replaces it.

    The list is the *full* order either way, never a move: a move has to be applied to
    the state the client last saw, and the client's idea of that state is the thing this
    command exists to stop trusting.
    """
    covers = basic_covers(hass, entry)
    if whole:
        await store.async_set_order(order, known=covers)
        return {}

    wanted = [unique_id for unique_id in order if unique_id in covers]
    members = {
        unique_id
        for unique_id, cfg in covers.items()
        if _profile_now(store, cfg, unique_id) == (group or "")
    }
    unknown = [unique_id for unique_id in order if unique_id not in members]
    if unknown:
        raise PanelError(
            ERR_SERVICE_VALIDATION_ERROR,
            ERROR_UNKNOWN_COVER,
            f"{', '.join(unknown)} does not follow {group or 'no profile'}",
            {"covers": ", ".join(unknown), "profile": group or ""},
        )
    # The list is the group's *full* order, and a client that sends a short one (or the
    # same id twice, which the schema refuses but an internal caller could still send)
    # must not cost a member its place: the seats below are the group's, one per member,
    # and a member left out of `wanted` would leave a seat empty and fall out of the
    # stored order altogether - which reads on the screen as a shutter that jumped to
    # the end of its group for no reason anybody can see.
    wanted = list(dict.fromkeys(wanted))
    wanted += [
        unique_id
        for unique_id in store.ordered(list(covers))
        if unique_id in members and unique_id not in wanted
    ]
    rest = [unique_id for unique_id in store.ordered(list(covers)) if unique_id not in members]
    # The places that group holds in the whole order, filled again in the order asked
    # for. Everything else keeps its own place, which is what makes one group's drag one
    # group's change.
    seats = [
        index
        for index, unique_id in enumerate(store.ordered(list(covers)))
        if unique_id in members
    ]
    merged = list(rest)
    for seat, unique_id in zip(seats, wanted, strict=False):
        merged.insert(min(seat, len(merged)), unique_id)
    await store.async_set_order(merged, known=covers)
    return {}


async def async_set_travel(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    cover_unique_id: str,
    height: Any,
) -> dict[str, Any]:
    """Say how far this window really travels, or stop saying it.

    The one number every scaled profile depends on. `null` removes it from the record
    and the window goes back to whatever its own configuration says - which may be
    nothing at all, and then a profile cannot be scaled onto it any more.
    """
    _cover_config(hass, entry, cover_unique_id)
    record = store.calibration(cover_unique_id)
    data = _rewritten_record(
        store,
        cover_unique_id,
        height=None if height is None else _height(height),
        overrides=dict(record.overrides) if record else {},
    )
    await _store_the_record(store, cover_unique_id, data)
    return {}


async def async_cover_edit(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    cover_unique_id: str,
    overrides: Mapping[str, Any],
    height: Any,
    height_given: bool,
) -> dict[str, Any]:
    """Type this window's own numbers, key by key.

    `null` is "stop overriding": the key goes out of the record and the window inherits
    again, which is what the empty field with its "eredita N" placeholder means on the
    screen. A key the message does not mention is not touched, so correcting one number
    is one number and not a form submitted whole.

    The bounds are `CALIBRATION_FIELDS`, which is the guided dialog's own hand-edit
    form: a number it refuses is refused here in the same words.
    """
    _cover_config(hass, entry, cover_unique_id)
    record = store.calibration(cover_unique_id)
    wanted = dict(record.overrides) if record else {}
    bounds = {key: (low, high) for key, low, high in CALIBRATION_FIELDS}
    for key, value in overrides.items():
        if value is None:
            wanted.pop(key, None)
            continue
        low, high = bounds[key]
        wanted[key] = _number(value, key, low, high)
    travel = record.height if record else None
    if height_given:
        travel = None if height is None else _height(height)
    data = _rewritten_record(store, cover_unique_id, height=travel, overrides=wanted)
    await _store_the_record(store, cover_unique_id, data)
    return {}


async def async_cover_forget(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    cover_unique_id: str,
) -> dict[str, Any]:
    """Throw this window's own record away, and say what it falls back to.

    The whole record, assignment included - the same thing "Elimina" does in the dialog,
    where a measurement deleted takes the profile that was assigned beside it. What the
    shutter then runs on is answered by resolving it again with the record gone, rather
    than by a rule about what it ought to be, so the sentence the panel shows and the
    numbers the shutter runs on are the same answer.
    """
    cfg = _cover_config(hass, entry, cover_unique_id)
    await store.async_remove_calibration(cover_unique_id)
    resolved = resolve_cover_config(
        hass, entry, cfg, cover_unique_id, yaml_profiles(hass, entry)
    )
    falls_back_to = {
        CALIBRATION_ORIGIN_INHERITED: "profile",
        CALIBRATION_ORIGIN_FILE: "file",
    }.get(resolved.origin, "defaults")
    return {"falls_back_to": falls_back_to, "profile": resolved.profile}


async def async_profile_edit(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    name: str,
    values: Mapping[str, Any],
    reference_height: Any,
) -> dict[str, Any]:
    """The six numbers of one profile, by hand, and everybody who follows it.

    A profile's numbers are not copied into its followers - a record holds the *name* -
    so an edit reaches every window that follows it on the next resolution, which is the
    signal this write ends with. `affected` is who those windows are, named before the
    user has to go and look.

    `measured_at` is re-stamped because the numbers have just been stated; `measured_on`
    is carried over untouched, because the window they were measured on is still the
    window they were measured on. The same rule as `async_step_profile_edit`.
    """
    _refuse_a_file_profile(hass, entry, store, name)
    stored = _stored_profile(store, name)
    numbers = {
        key: _number(values[key], key, low, high) for key, low, high in PROFILE_VALUE_FIELDS
    }
    travel = _number(
        reference_height, CONF_REFERENCE_HEIGHT, MIN_HEIGHT_CM, MAX_HEIGHT_CM
    )
    followers = sorted(_followers(hass, entry, store, name))
    await store.async_set_profile(
        name,
        cover_profile_data(
            name,
            reference_height=travel,
            opening_time=numbers[CONF_OPENING_TIME],
            closing_time=numbers[CONF_CLOSING_TIME],
            slat_time=numbers[CONF_SLAT_TIME],
            opening_roll=numbers[CONF_OPENING_ROLL],
            closing_roll=numbers[CONF_CLOSING_ROLL],
            reference_cover=stored.get(CONF_REFERENCE_COVER),
            measured_on=stored.get(CONF_MEASURED_ON),
            source=stored.get(CONF_SOURCE) or CALIBRATION_SOURCE_MANUAL,
            raw=stored.get(CONF_RAW),
        ),
    )
    return {"affected": followers}


async def async_profile_rename(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    name: str,
    new_name: str,
) -> dict[str, Any]:
    """Give a profile another name, and take every follower with it.

    Three writes in one awaited sequence, because the store keys a profile by its name:
    the numbers go in under the new name, every window assigned to the old one is
    repointed, and only then is the old name removed - in that order, so that nothing in
    between leaves a shutter following a name nobody defines.

    A window that follows through its own `profile:` line in `myhome.yaml` cannot be
    repointed: the line is in the user's file and this integration does not write it.
    Those are named in the answer (`from_file`) rather than quietly left behind pointing
    at a profile that has gone.
    """
    _refuse_a_file_profile(hass, entry, store, name)
    stored = _stored_profile(store, name)
    _refuse_a_bad_name(new_name)
    if new_name != name and (
        store.profile(new_name) is not None or new_name in yaml_profiles(hass, entry)
    ):
        raise PanelError(
            ERR_SERVICE_VALIDATION_ERROR,
            ERROR_NAME_IN_USE,
            f"There is already a profile called {new_name}",
            {"profile": new_name},
        )
    if new_name == name:
        return {"moved": 0, "from_file": []}

    assigned = store.covers_following(name)
    from_file = sorted(_followers_from_file(hass, entry, store, name))
    await store.async_set_profile(new_name, {**stored, "name": new_name})
    if assigned:
        await store.async_set_assignments({unique_id: (new_name, None) for unique_id in assigned})
    await store.async_remove_profile(name)
    LOGGER.info(
        "Cover profile '%s' renamed to '%s'; %s shutter(s) followed it and %s follow it "
        "through the configuration file and did not",
        name,
        new_name,
        len(assigned),
        len(from_file),
    )
    return {"moved": len(assigned), "from_file": from_file}


async def async_profile_delete(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    name: str,
) -> dict[str, Any]:
    """Forget a profile, having said which shutters lose it.

    Read before the deletion and again after it, because the two lists are different
    questions: `covers_affected` are the windows whose stored assignment goes with the
    profile - they are the ones `async_remove_profile` strips - and `from_file` are the
    windows whose `profile:` line in `myhome.yaml` now names nothing, which this cannot
    touch and which the user has to be told about. The same split the dialog's own
    confirmation makes, for the same reason.
    """
    _refuse_a_file_profile(hass, entry, store, name)
    _stored_profile(store, name)
    from_file = sorted(_followers_from_file(hass, entry, store, name))
    orphans = await store.async_remove_profile(name)
    LOGGER.info(
        "Cover profile '%s' deleted; %s shutter(s) lost the assignment and %s follow(ed) "
        "it through the configuration file",
        name,
        len(orphans),
        len(from_file),
    )
    return {"covers_affected": list(orphans), "from_file": from_file}


@callback
def _refuse_a_bad_name(name: str) -> None:
    """A profile name is a YAML key, because the user may move it into their own file."""
    if not re.fullmatch(PROFILE_NAME_PATTERN, name) or name == NO_PROFILE:
        raise PanelError(
            ERR_SERVICE_VALIDATION_ERROR,
            ERROR_INVALID_NAME,
            f"{name!r} is not a usable profile name",
            {"profile": name},
        )


@callback
def _followers(
    hass: HomeAssistant, entry: ConfigEntry, store: CalibrationStore, name: str
) -> set[str]:
    """Every window that follows that profile, however it was told to."""
    return set(store.covers_following(name)) | _followers_from_file(hass, entry, store, name)


@callback
def _followers_from_file(
    hass: HomeAssistant, entry: ConfigEntry, store: CalibrationStore, name: str
) -> set[str]:
    """...and only the ones told so by `myhome.yaml`.

    A stored assignment outranks the file's key, so a window that has both is counted on
    the side that really decides - which is `_covers_following`'s rule in the dialog.
    """
    following: set[str] = set()
    for unique_id, cfg in basic_covers(hass, entry).items():
        if cfg.get(CONF_PROFILE) != name:
            continue
        record = store.calibration(unique_id)
        if record is not None and record.profile:
            continue
        following.add(unique_id)
    return following


async def async_undo(
    hass: HomeAssistant,
    entry: ConfigEntry,
    store: CalibrationStore,
    *,
    token: str,
) -> dict[str, Any]:
    """Put back exactly the records the last write replaced.

    A new write of the old numbers, not a rollback: it takes the lock like any other, it
    reaches the shutters the same way, and it leaves no token of its own - undoing an
    undo would be a pair of buttons swapping a gateway back and forth with nothing on
    the screen to say which way round it is now.
    """
    undo = _take(hass, entry, token)
    await store.async_restore(profiles=undo.profiles, covers=undo.covers, order=undo.order)
    LOGGER.info("The panel's last change to %s (%s) was undone", entry.title, undo.what)
    return {"undone": undo.what}


# ------------------------------------------------------------------- the write itself
async def async_write(
    hass: HomeAssistant,
    entry: ConfigEntry,
    what: str,
    work: Any,
) -> dict[str, Any]:
    """Run one write under the rules every write obeys, and answer for it.

    The lock, the snapshot, the store primitive the command is made of, the undo token,
    the signal that carries it to the shutters, and the fresh overview - once, here, so
    that a command is the thing it does and nothing else.

    An `undo` is passed through the same door on purpose: it is refused while a
    measurement is running, it is refused while another write is being applied, and it
    reaches the covers exactly as the write it takes back did.
    """
    _refuse_if_busy(hass, entry)
    # Taken with no `await` between the refusal and the claim, so two frames that
    # arrived in the same tick cannot both find the gateway free.
    writing: set[str] = hass.data.setdefault(WRITING_DATA_KEY, set())
    writing.add(entry.entry_id)
    try:
        store = await async_get_store(hass, entry)
        before = _StoreState.of(store)
        extra = await work(entry, store)
        after = _StoreState.of(store)
    finally:
        writing.discard(entry.entry_id)

    diff = _diff(before, after)
    token = None if what == "undo" else _remember(hass, entry, diff, what)
    if diff.anything:
        # ...and this is how it reaches the shutters: every cover of this gateway
        # re-resolves and swaps its numbers in place. No reload (plan decision 4).
        async_dispatcher_send(
            hass,
            SIGNAL_CALIBRATION_CHANGED.format(mac=str(entry.data.get(CONF_MAC) or "")),
            entry.entry_id,
        )
    overview = async_overview(hass, entry)
    async_publish(hass, entry, overview)
    return {"overview": overview, "undo_token": token, **extra}


# ------------------------------------------------------------------- the subscriptions
SUBSCRIBERS_DATA_KEY = f"{DOMAIN}_panel_subscribers"


@callback
def async_subscribers(hass: HomeAssistant, entry_id: str) -> list[Any]:
    """The callbacks watching one gateway, as a list that can be added to."""
    by_entry: dict[str, list[Any]] = hass.data.setdefault(SUBSCRIBERS_DATA_KEY, {})
    return by_entry.setdefault(entry_id, [])


@callback
def async_publish(hass: HomeAssistant, entry: ConfigEntry, overview: Mapping[str, Any]) -> None:
    """Push a fresh overview to every open panel of this gateway.

    The whole payload and not a patch: a client that merged server pushes into a model
    it also edits eventually shows a shutter following a profile the server deleted
    (CONTRACT §1). It is cheap - a dozen shutters and a handful of profiles - and it is
    the one shape everything in this API answers with.
    """
    for send in list(async_subscribers(hass, entry.entry_id)):
        send({"type": "overview", "overview": overview})


@callback
def async_cover_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> list[str]:
    """The entity ids of this gateway's basic covers, for the `measuring` watch.

    Read off the overview rows rather than the registry a second time, so the panel and
    the watch cannot disagree about which shutters there are.
    """
    return [
        row["entity_id"]
        for row in async_overview(hass, entry)["covers"]
        if row["entity_id"]
    ]


@callback
def async_measuring(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any] | None:
    """Which window is being measured right now, as the overview reports it."""
    measuring = calibrating_now(hass, entry)
    if not measuring:
        return None
    unique_id = sorted(measuring)[0]
    covers = basic_covers(hass, entry)
    return {
        "cover_unique_id": unique_id,
        "name": str(covers.get(unique_id, {}).get("name") or unique_id),
    }


__all__ = [
    "UNDO_TTL",
    "PanelError",
    "async_assign",
    "async_cover_edit",
    "async_cover_entity_ids",
    "async_cover_forget",
    "async_measuring",
    "async_profile_delete",
    "async_profile_edit",
    "async_profile_rename",
    "async_publish",
    "async_reorder",
    "async_set_travel",
    "async_subscribers",
    "async_undo",
    "async_write",
]

