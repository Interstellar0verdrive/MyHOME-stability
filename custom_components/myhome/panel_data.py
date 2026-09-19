"""What the panel reads: one gateway's calibrations, in the shape a screen renders.

This module answers three questions and writes nothing at all:

* **`async_overview`** - every profile of one gateway, every basic shutter of it, which
  profile each shutter follows, what it is running on and where that came from, in the
  order the user dragged them into. One call, one payload, because the panel replaces
  its model wholesale on every read rather than patching it (0.6.0 plan, R-W3): a client
  that merges server pushes into a model it also edits is a client that eventually shows
  a shutter following a profile the server deleted.
* **`async_cover_detail`** - the same row plus, key by key, the number, which of the four
  sources said it, and what it would fall back to with this window's own measurements
  taken away. That last one is the "eredita N" under an empty field and the destination
  "Rimuovi la misura" has to name before it removes anything.
* **`async_texts`** - the integration's own translations for one language, so that no
  sentence the panel shows is baked into the bundle.
* **`async_preview`** - the same resolution again, for an assignment nobody has made
  yet: "if this shutter followed that profile, at that travel, what would it run on?"
  It is the before/after table of the review panel, and - with `profile_values` - the
  profile card's impact preview as well. It is here rather than in the browser for the
  reason the rest of this module is: the answer is `resolve_cover`'s, and a second one
  worked out in JavaScript would be a second travel model. It writes nothing, takes no
  lock and refuses nothing - see `async_preview`.

**Where the answers come from, and why not from here.** Every number and every origin in
the overview is `resolve_cover_config` - the very call `cover.py` makes in the entity's
constructor. Not a second implementation of the precedence, not a re-derivation in
JavaScript, not "the same rule, kept in step by hand": the same function, so a shutter
whose `Calibration source` attribute says `profile tall, adjusted` cannot be a shutter
the panel calls measured. `tests/test_panel_parity.py` holds that invariant over the
state matrix; it is the one invariant the whole panel rests on, because a panel that
disagrees with the thing it is explaining teaches the user something false.

**Areas are resolved here rather than in the browser.** The panel groups, filters and
orders by room, and the entity registry is the only place that knows which room a cover
is in - through the entity, and failing that through its device. Resolving it in the
frontend would mean a second registry subscription, a second source of truth for
grouping, and a race between the two on every reload. `area` is allowed to be `None`
everywhere: nothing groups, filters or sorts on it being present.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from .calibration_flow import MAX_HEIGHT_CM, MIN_HEIGHT_CM, PROFILE_FIELDS, parse_number
from .calibration_store import (
    ResolvedCover,
    keys_written_by_the_file,
    loaded_store,
    merged_profiles,
    profile_as_config,
    profile_overrides,
    profile_provenance,
    resolve_cover,
    resolve_cover_config,
    stored_calibration,
)
from .const import (
    CALIBRATION_KEY_ORIGIN_OWN,
    CALIBRATION_ORIGIN_FILE,
    CALIBRATION_ORIGIN_INHERITED,
    CONF_ADVANCED_SHUTTER,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_PROFILES,
    CONF_COVER_UNIQUE_ID,
    CONF_COVERS_FROM_FILE,
    CONF_ENTITIES,
    CONF_HEIGHT,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PLATFORMS,
    CONF_PROFILE,
    CONF_PROFILE_WINS,
    CONF_RAW,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
    COVER_CALIBRATION_KEYS,
    DOMAIN,
    LOGGER,
)

# The five numbers a profile really states about a window, in the order a screen reads
# them. `roll` is left out on purpose: it is the fallback of the two directional
# coefficients and never what a calibrated shutter runs on, so printing it beside them
# would offer the user a sixth number to correct that corrects nothing.
PROFILE_VALUE_KEYS: tuple[str, ...] = (
    CONF_OPENING_TIME,
    CONF_CLOSING_TIME,
    CONF_SLAT_TIME,
    CONF_OPENING_ROLL,
    CONF_CLOSING_ROLL,
)

# Where a profile's numbers were written: by a guided calibration into this
# integration's own storage, or by the user into `cover_profiles:`. Only the first can
# be edited from the panel - the second belongs to a file the panel does not write.
PROFILE_SOURCE_STORE = "store"
PROFILE_SOURCE_YAML = "yaml"

# The two levels a guided calibration runs at, as the `raw` block records them.
CALIBRATION_LEVEL_BASIC = "basic"
CALIBRATION_LEVEL_PRECISE = "precise"

# The translations, and the one language every fallback ends at.
_TRANSLATIONS_DIR = Path(__file__).parent / "translations"
DEFAULT_LANGUAGE = "en"

# What a language may be spelled with before it is allowed to name a file. The panel
# sends the *user's* language, which arrives from the browser through a WebSocket frame
# and is therefore a string somebody can choose - and one keystroke later it is half of
# a path. A BCP 47 tag is letters, digits and hyphens and nothing else; anything with a
# separator, a dot or a null byte in it is not a language this integration has ever
# shipped, and is refused before the disk is touched rather than after.
_A_LANGUAGE = re.compile(r"^[A-Za-z0-9-]{1,32}$")
# The blocks the panel is served, as `{the name in the file: the name in the payload}`.
#
# `options.*` is the guided flow's own wording, which the panel reuses wherever it says
# the same thing (the key labels, the four form errors); `selector.*` carries the five
# origin phrases, which is the one vocabulary the panel is forbidden from having its own
# copy of; `exceptions.*` holds the sentence behind every `translation_key` a refusal
# carries, so the panel prints the same words Home Assistant would.
#
# The rename is the fourth. The panel's own block is **`config_panel` in the file and
# `panel` in the payload**, because those are two different authorities: Home Assistant's
# `hassfest` validates `strings.json` against a fixed list of top-level keys and rejects
# everything else (`script/hassfest/translations.py`, `gen_strings_schema`, a schema with
# `PREVENT_EXTRA`), and `config_panel` is the one entry on that list meant for a panel's
# own words - an arbitrarily nested tree of slug keys. The frontend, meanwhile, is
# written against `panel.<view>.<element>` and would have to change in every file to say
# `config_panel.` instead, for a prefix nobody reading the screen would learn anything
# from. So the file uses the name the validator knows and the payload uses the name the
# panel knows, and this one line is where the two meet.
TEXT_BLOCKS: Mapping[str, str] = {
    "options": "options",
    "selector": "selector",
    "exceptions": "exceptions",
    "config_panel": "panel",
}
# Read once per language per Home Assistant run.
TEXTS_CACHE_KEY = f"{DOMAIN}_panel_texts"


# ------------------------------------------------------------------- the gateway
@callback
def _gateway(hass: HomeAssistant, entry: ConfigEntry) -> tuple[str, Mapping[str, Any]]:
    """This entry's MAC and its slice of `hass.data`, empty while it is not loaded."""
    mac = str(entry.data.get(CONF_MAC) or "")
    return mac, (hass.data.get(DOMAIN) or {}).get(mac) or {}


@callback
def _covers_as_written(hass: HomeAssistant, entry: ConfigEntry) -> Mapping[str, Mapping[str, Any]]:
    """Every cover of this gateway, by device key, **as `myhome.yaml` wrote it**.

    Not the validated dict the entity reads. `cover.async_setup_entry` merges the
    resolved travel model back into that one, which is right for a reader that wants the
    numbers the shutter runs on and fatal for this one: once a measurement of 25 s has
    been written over a file that says 30 s, nothing can answer "what does the file say"
    or "what would this fall back to if the measurement went away". The copy taken at
    setup (`CONF_COVERS_FROM_FILE`) is that same dict before the merge, and resolving
    against it gives exactly what the entity's constructor computed - by construction,
    since it is the same input and the same function.
    """
    _mac, gateway = _gateway(hass, entry)
    written = gateway.get(CONF_COVERS_FROM_FILE)
    if isinstance(written, Mapping):
        return written
    # An entry set up by a version of this integration that did not take the copy, or a
    # gateway that is not loaded: the merged dict is a worse answer than none at all for
    # the two file questions, and the right answer for everything else.
    return (gateway.get(CONF_PLATFORMS) or {}).get(COVER) or {}


@callback
def basic_covers(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, dict[str, Any]]:
    """The basic covers of one gateway, by unique id, in the file's own order.

    Advanced covers are left out, exactly as `CalibrationContextMixin._covers` leaves
    them out and for the same reason: they report their own position, so there is no
    travel model to calibrate and every calibration primitive refuses them. The order is
    the iteration order of the validated configuration, which is the order of
    `myhome.yaml` - the fallback the stored order falls back to.
    """
    mac, _gw = _gateway(hass, entry)
    return {
        f"{mac}-{key}": dict(cfg)
        for key, cfg in _covers_as_written(hass, entry).items()
        if not cfg.get(CONF_ADVANCED_SHUTTER)
    }


@callback
def is_advanced_cover(hass: HomeAssistant, entry: ConfigEntry, unique_id: str) -> bool:
    """True when that unique id names a cover the panel refuses rather than ignores.

    The difference matters to the answer the user gets: a unique id that names nothing
    is "not found", and one that names a shutter which reports its own position is "not
    something this panel does", which is a different sentence.
    """
    mac, _gw = _gateway(hass, entry)
    for key, cfg in _covers_as_written(hass, entry).items():
        if f"{mac}-{key}" == unique_id:
            return bool(cfg.get(CONF_ADVANCED_SHUTTER))
    return False


@callback
def yaml_profiles(hass: HomeAssistant, entry: ConfigEntry) -> Mapping[str, Mapping[str, Any]]:
    """The `cover_profiles:` block of this gateway's configuration file."""
    _mac, gateway = _gateway(hass, entry)
    return gateway.get(CONF_COVER_PROFILES) or {}


@callback
def calibrating_now(hass: HomeAssistant, entry: ConfigEntry) -> set[str]:
    """The unique ids of the shutters a measurement is running on, right now.

    Read off the live entities - the objects the guided flow marks and unmarks - and not
    off the state machine, whose copy of the attribute a reload would leave stale. An
    entry in the middle of a reload has no entities at all, and nothing is being
    measured during one.
    """
    mac, gateway = _gateway(hass, entry)
    covers = (gateway.get(CONF_PLATFORMS) or {}).get(COVER) or {}
    running: set[str] = set()
    for key, cfg in covers.items():
        entity = (cfg.get(CONF_ENTITIES) or {}).get(COVER)
        if entity is not None and getattr(entity, "calibrating", False):
            running.add(f"{mac}-{key}")
    return running


# ---------------------------------------------------------------------- registries
@callback
def _registry_row(hass: HomeAssistant, unique_id: str) -> tuple[str | None, str | None, str | None]:
    """One cover's `(entity_id, area_id, area name)`, or three Nones.

    The entity's own area first, then its device's - which is the order Home Assistant
    itself resolves an area in, and the reason a user who filed the whole gateway under
    a room and never touched a single cover still sees rooms in the panel.
    """
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(COVER, DOMAIN, unique_id)
    if entity_id is None:
        return None, None, None
    entry = registry.async_get(entity_id)
    if entry is None:
        return entity_id, None, None
    area_id = entry.area_id
    if area_id is None and entry.device_id:
        device = dr.async_get(hass).async_get(entry.device_id)
        area_id = device.area_id if device else None
    if area_id is None:
        return entity_id, None, None
    area = ar.async_get(hass).async_get_area(area_id)
    return entity_id, area_id, area.name if area else None


# --------------------------------------------------------------------- the rows
@callback
def _level_and_note(record: Mapping[str, Any] | None) -> tuple[str | None, float | None]:
    """How thoroughly this window was measured, and by how much the check was out.

    Both come out of the `raw` block the guided flow keeps beside its conclusions. A
    record written by hand, or imported from the first draft, has no `raw`: the two are
    then `None` and the screen leaves the line out rather than guessing at a level.
    """
    raw = (record or {}).get(CONF_RAW)
    if not isinstance(raw, Mapping):
        return None, None
    level = CALIBRATION_LEVEL_PRECISE if raw.get("precise") else CALIBRATION_LEVEL_BASIC
    deviation = raw.get("deviation_cm")
    return level, float(deviation) if isinstance(deviation, (int, float)) else None


@callback
def _values(resolved: ResolvedCover) -> dict[str, float]:
    """The travel model this shutter runs on, restricted to the keys it is made of."""
    return {
        key: resolved.values[key]
        for key in COVER_CALIBRATION_KEYS
        if key in resolved.values
    }


@callback
def _cover_row(
    hass: HomeAssistant,
    entry: ConfigEntry,
    unique_id: str,
    cfg: Mapping[str, Any],
    *,
    profiles: Mapping[str, Mapping[str, Any]],
    calibrating: set[str],
) -> tuple[dict[str, Any], ResolvedCover]:
    """One shutter as the panel shows it, and the resolution the row was read off.

    The resolution is handed back rather than recomputed by the caller, so the detail
    view and the overview row are the same answer to the same question and not two.
    """
    store = loaded_store(hass, entry)
    record = store.raw_covers.get(unique_id) if store else None
    resolved = resolve_cover_config(hass, entry, cfg, unique_id, yaml_profiles(hass, entry))
    entity_id, area_id, area = _registry_row(hass, unique_id)
    level, verify_note = _level_and_note(record)
    stored = store.calibration(unique_id) if store else None
    row = {
        "unique_id": unique_id,
        "entity_id": entity_id,
        "name": str(cfg.get(CONF_NAME) or unique_id),
        "area_id": area_id,
        "area": area,
        "height": resolved.height,
        "profile": resolved.profile,
        # The profile this window follows because the *file* says so, rather than
        # because somebody said so on this installation. The panel says the two
        # differently: the second can be changed here, the first is a line in a file.
        "profile_from_file": resolved.profile is not None
        and (stored is None or stored.profile is None),
        "profile_missing": resolved.profile is not None and resolved.profile not in profiles,
        "origin": resolved.origin,
        "source": resolved.source,
        "values": _values(resolved),
        # Which of those numbers were measured on *this* window: what the detail screen
        # marks "valore proprio" and what the review table's "some values are its own"
        # note is counted from.
        "has_own": sorted(stored.overrides) if stored else [],
        "level": level,
        "verify_note": verify_note,
        "measured_at": stored.measured_at if stored else None,
        "calibrating": unique_id in calibrating,
    }
    return row, resolved


@callback
def _profile_rows(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    profiles: Mapping[str, Mapping[str, Any]],
    covers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Every profile of this gateway, with the shutters that follow it.

    Including the ones that are not there: a cover whose record names a profile nobody
    defines any more falls back to its own configuration, silently as far as the shutter
    is concerned and with a warning in the log. The panel has to say it out loud, so the
    name gets a row of its own marked `missing` rather than disappearing from a list the
    user is reading to find out what their shutters are doing.
    """
    store = loaded_store(hass, entry)
    stored_profiles = store.profiles if store else {}
    raw_profiles = store.raw_profiles if store else {}
    names = {row["profile"] for row in covers if row["profile"]} | set(profiles)
    by_id = {row["unique_id"]: row for row in covers}

    rows: list[dict[str, Any]] = []
    for name in sorted(names):
        profile = profiles.get(name)
        followers = [
            row["unique_id"]
            for row in covers
            if row["profile"] == name and not row["profile_from_file"]
        ]
        from_file = [
            row["unique_id"]
            for row in covers
            if row["profile"] == name and row["profile_from_file"]
        ]
        measured_on, measured_at = profile_provenance(raw_profiles.get(name) or {})
        source = (
            PROFILE_SOURCE_STORE
            if name in stored_profiles
            else PROFILE_SOURCE_YAML
            if profile is not None
            else None
        )
        rows.append(
            {
                "name": name,
                "source": source,
                # A `cover_profiles:` profile is read-only here: it is a block of the
                # user's own file, which this integration has never written and is not
                # about to start writing.
                "editable": source == PROFILE_SOURCE_STORE,
                "values": {
                    key: float(profile[key])
                    for key in PROFILE_VALUE_KEYS
                    if profile is not None and key in profile
                },
                "reference_height": (
                    float(profile[CONF_REFERENCE_HEIGHT])
                    if profile is not None and profile.get(CONF_REFERENCE_HEIGHT)
                    else None
                ),
                "measured_on": measured_on,
                # The name that window has *now*, which is what a sentence prints. None
                # when the id names a shutter this gateway no longer has.
                "measured_on_name": (
                    by_id[measured_on]["name"] if measured_on in by_id else None
                ),
                "measured_at": measured_at,
                "followers": followers,
                "followers_from_file": from_file,
                "missing": profile is None,
            }
        )
    return rows


# ------------------------------------------------------------------- the payloads
@callback
def async_entries(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Every configured gateway, so the panel can offer a picker when there are two."""
    return [
        {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "mac": str(entry.data.get(CONF_MAC) or ""),
            "loaded": entry.state is ConfigEntryState.LOADED,
        }
        for entry in hass.config_entries.async_entries(DOMAIN)
    ]


@callback
def async_overview(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Everything the panel's main screen renders, for one gateway.

    Built whole on every read. There is no incremental form of this and there is not
    meant to be: the payload is a dozen shutters and a handful of profiles, the client
    replaces its model with it rather than merging, and a write answers with a fresh one
    - which is what makes a browser tab left open for a day either right or visibly
    stale, and never quietly half of each.
    """
    store = loaded_store(hass, entry)
    profiles = merged_profiles(yaml_profiles(hass, entry), store.profiles if store else {})
    covers_cfg = basic_covers(hass, entry)

    calibrating = calibrating_now(hass, entry)

    rows: dict[str, dict[str, Any]] = {}
    measuring: dict[str, Any] | None = None
    for unique_id, cfg in covers_cfg.items():
        row, _resolved = _cover_row(
            hass, entry, unique_id, cfg, profiles=profiles, calibrating=calibrating
        )
        rows[unique_id] = row
        if measuring is None and row["calibrating"]:
            measuring = {"cover_unique_id": unique_id, "name": row["name"]}

    # The stored order first, the file's order for everything it does not name. Applied
    # across the whole gateway rather than per group: a group is a slice of this list,
    # so ordering it once orders every group, and a shutter that moves from one profile
    # to another keeps the place the user gave it.
    ordered = store.ordered(list(rows)) if store else list(rows)
    covers = [rows[unique_id] for unique_id in ordered]
    for index, row in enumerate(covers):
        row["order_index"] = index

    return {
        "entries": async_entries(hass),
        "entry_id": entry.entry_id,
        "measuring": measuring,
        "session": _session_row(hass, entry),
        "profiles": _profile_rows(hass, entry, profiles=profiles, covers=covers),
        "covers": covers,
        "order": store.raw_order if store else [],
        # Not an error and not an empty list to be styled: a gateway with only advanced
        # shutters has nothing this panel can do anything about, and says so once.
        "no_basic_covers": not covers,
    }


@callback
def _session_row(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any] | None:
    """The one line the banner needs about this gateway's session, or None.

    `measuring` beside it says *that* a shutter is being measured, whoever is measuring
    it; this says *who*, so that `measuring` set with `session` at `null` reads as "the
    guided dialog or the 0.4.2 action" and the panel offers to close the dialog rather
    than to resume a session it does not have (`panel_schemas.SESSION_OVERVIEW_KEYS`).

    Read off the snapshot and not off the session's own attributes: `state` and `owner`
    are answers the session composes - a terminal one has no owner and says `saved` or
    `ended` rather than the screen it stopped on - and two places computing them would
    be two places to keep in step. The import is inside the function because
    `calibration_session` reads this module: the session is built out of the panel's
    view of a gateway, and the overview only borrows a line back from it.

    **This read has one side effect**, and it is deliberate: `current()` forgets a
    session that ended more than ten minutes ago, which is how this key goes back to
    `null` by itself. So an overview built at any moment is right, and no timer is
    needed to make it so - but a reader expecting a pure read should know that the
    tenth-minute forgetting happens here, in the first overview anybody asks for after
    it falls due.
    """
    from .calibration_session import current  # noqa: PLC0415 - the cycle is the point

    session = current(hass, entry)
    if session is None:
        return None
    snapshot = session.snapshot()
    return {
        "session_id": snapshot["session_id"],
        "cover_unique_id": snapshot["cover"]["unique_id"],
        "name": snapshot["cover"]["name"],
        "state": snapshot["state"],
        "owner": None if snapshot["owner"] is None else snapshot["owner"]["client_id"],
    }


@callback
def async_cover_detail(
    hass: HomeAssistant, entry: ConfigEntry, cover_unique_id: str
) -> dict[str, Any] | None:
    """One shutter, key by key. None when this gateway has no such basic cover.

    Every key carries four numbers and two origins, and the reason there are two is the
    empty field: `value` and `origin` are what the shutter runs on today, `inherited_*`
    is what it would run on if this window's own measurement of that key were removed.
    The detail screen prints the second as the placeholder of an empty field, and the
    "Rimuovi la misura" confirmation names it, so that removing something never means
    finding out afterwards what it fell back to.
    """
    cfg = basic_covers(hass, entry).get(cover_unique_id)
    if cfg is None:
        return None
    store = loaded_store(hass, entry)
    profiles = merged_profiles(yaml_profiles(hass, entry), store.profiles if store else {})
    row, resolved = _cover_row(
        hass,
        entry,
        cover_unique_id,
        cfg,
        profiles=profiles,
        calibrating=calibrating_now(hass, entry),
    )

    # The same set the precedence used, fallbacks included: a cover whose file says
    # `roll: 1.5` has stated both directional rolls, and the loop above calls them
    # `file` for exactly that reason. Reading the narrower `keys_from_file` here would
    # print the user's own number as this integration's default, beside an origin that
    # says the file wrote it.
    written = keys_written_by_the_file(cfg)
    profile = profiles.get(resolved.profile) if resolved.profile else None
    # The profile scaled to this window, whatever the precedence does with it: the
    # numbers an impact preview compares against, and the same scaling the resolution
    # itself uses, because it is the same function.
    scaled = profile_overrides(profile, resolved.height) if profile is not None else {}
    keys = []
    for key in COVER_CALIBRATION_KEYS:
        item = resolved.keys.get(key)
        if item is None:
            continue
        inherits = resolved.inherited.get(key)
        keys.append(
            {
                "key": key,
                "value": item.value,
                "origin": item.origin,
                "own": item.origin == CALIBRATION_KEY_ORIGIN_OWN,
                "inherited_value": inherits.value if inherits else None,
                "inherited_origin": inherits.origin if inherits else None,
                "profile_value": scaled.get(key),
                # What `myhome.yaml` really writes for this cover, and only that: a key
                # the file leaves out has no file value, however completely the
                # validator filled it in.
                "file_value": cfg.get(key) if key in written else None,
                # ...and what the validator resolved where the file says nothing, which
                # is this integration's own default for that key. `None` where the file
                # does write it, because the default is then not visible from here.
                "default_value": cfg.get(key) if key not in written else None,
            }
        )

    # What "Rimuovi la misura" would leave, answered before it removes anything.
    #
    # `inherited_value` above answers a narrower question - what one key falls back to
    # with this window's *overrides* taken away - and it is the right answer for the
    # empty field and its "eredita N". It is the wrong answer for the confirmation,
    # because `cover_forget` takes the whole record, the travel with it: a window whose
    # travel only the record knew cannot be scaled a profile afterwards, so the
    # destination the keys promise would be a profile the shutter would not in fact
    # reach. This resolves the window once more with the record gone - which is exactly
    # what `panel_write.async_cover_forget` does after the write - so the sentence the
    # user reads before and the one they read after are one answer.
    forgotten = resolve_cover(cfg, profiles=profiles, calibration=None)
    falls_back_to = {
        CALIBRATION_ORIGIN_INHERITED: "profile",
        CALIBRATION_ORIGIN_FILE: "file",
    }.get(forgotten.origin, "defaults")

    return {
        "entry_id": entry.entry_id,
        "cover": row,
        "keys": keys,
        "forget": {
            "falls_back_to": falls_back_to,
            "profile": forgotten.profile,
            # `myhome.yaml` may state the travel itself, and then it survives the
            # removal; a travel somebody typed into this panel does not. The design's
            # "la corsa del telo resta" is true in the first case and a promise in the
            # second, so the screen is told which it is instead of assuming.
            "travel_stays": forgotten.height is not None,
        },
    }


# ----------------------------------------------------------------------- preview
# The tokens a previewed item can carry instead of an answer. They are the
# `translation_key`s `assign` refuses with, deliberately: the review panel renders the
# same `exceptions.<key>.message` sentence whether the problem was found before the
# write was attempted or by the write itself, and a second vocabulary for the same six
# problems would be two sentences for one fact.
PREVIEW_PROBLEMS: tuple[str, ...] = (
    "unknown_cover",
    "advanced_cover",
    "unknown_profile",
    "missing_travel",
    "not_a_number",
    "out_of_range",
)


@callback
def _hypothetical_profiles(
    profiles: Mapping[str, Mapping[str, Any]],
    profile_values: Mapping[str, Mapping[str, Any]] | None,
    raw_profiles: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, str]]:
    """The gateway's profiles with some of their numbers replaced, for one answer only.

    The profile card's editor has a question no assignment can ask: "if this profile said
    these numbers instead, what would each of its followers run on?" - which is the live
    impact preview beside the fields. It is the same question the review panel asks, one
    level up, and it has to be answered by the same function for the same reason: a
    profile scaled in JavaScript is a second travel model.

    Two rules, both deliberate.

    * **A name nothing defines is not defined here.** The override replaces the numbers
      of a profile the gateway already has; it never invents one. So an item that asks
      for a name nobody defines still answers `unknown_profile`, and the preview cannot
      be used to ask about a profile that does not exist.
    * **A number that cannot be used does not silently become the stored one.** The
      offending name is handed back in `broken`, and every item that would resolve
      through it carries that problem instead of an answer - the same shape a bad
      `height` already has, and the reason this read still refuses nothing.

    **The overridden profile is built the way the write's would be.** The six numbers
    are `profile_edit`'s, and what `profile_edit` writes reaches the resolution through
    `profile_as_config` - which derives `roll` from `closing_roll`, because a stored
    profile does not carry one. Merging the six numbers straight into the config-shaped
    mapping would leave the old `roll` standing beside the new directional pair, and the
    preview would answer a number the write it is previewing could not produce. So a
    profile the store owns is re-shaped from its own record; one that only
    `cover_profiles:` defines is not, because its `roll:` is the file's own statement and
    no write from here can touch it.

    Nothing is written: the mapping is a copy that lives for the length of the call, and
    so is the record `profile_as_config` is handed.
    """
    merged = dict(profiles)
    broken: dict[str, str] = {}
    for name, values in (profile_values or {}).items():
        if name not in merged:
            continue
        numbers: dict[str, float] = {}
        problem: str | None = None
        for key, low, high in PROFILE_FIELDS:
            number = parse_number(values.get(key))
            if number is None:
                problem = "not_a_number"
                break
            if not low <= number <= high:
                problem = "out_of_range"
                break
            numbers[key] = number
        if problem is not None:
            broken[name] = problem
            continue
        stored = raw_profiles.get(name)
        shaped = None if stored is None else profile_as_config(name, {**stored, **numbers})
        merged[name] = shaped if shaped is not None else {**merged[name], **numbers}
    return merged, broken


@callback
def _previewed(
    hass: HomeAssistant,
    entry: ConfigEntry,
    item: Mapping[str, Any],
    *,
    covers: Mapping[str, Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, Any]],
    broken: Mapping[str, str],
) -> dict[str, Any]:
    """One hypothetical assignment, resolved - or the one problem that stops it.

    The record is rewritten exactly as `CalibrationStore.async_set_assignments` rewrites
    it (profile in or out, `profile_wins` with it, the travel when one is given, and the
    whole record gone when what is left says nothing), and the result is handed to
    `resolve_cover`. So this is not a prediction of what the write would do: it is the
    write's own input run through the read path, which is why
    `tests/test_websocket_api.py` can assert the two agree key for key.
    """
    unique_id = str(item[CONF_COVER_UNIQUE_ID])
    answer: dict[str, Any] = {
        "cover_unique_id": unique_id,
        "profile": None,
        "height": None,
        "problem": None,
        "origin": None,
        "source": None,
        "values": {},
        "keys": [],
        "has_own": [],
    }

    cfg = covers.get(unique_id)
    if cfg is None:
        answer["problem"] = (
            "advanced_cover" if is_advanced_cover(hass, entry, unique_id) else "unknown_cover"
        )
        return answer

    name = item.get(CONF_PROFILE)
    profile = None if name is None else str(name)
    answer["profile"] = profile
    if profile is not None and profile not in profiles:
        answer["problem"] = "unknown_profile"
        return answer

    height: float | None = None
    if item.get(CONF_HEIGHT) is not None:
        height = parse_number(item[CONF_HEIGHT])
        if height is None:
            answer["problem"] = "not_a_number"
            return answer
        if not MIN_HEIGHT_CM <= height <= MAX_HEIGHT_CM:
            answer["problem"] = "out_of_range"
            return answer

    store = loaded_store(hass, entry)
    record = dict((store.raw_covers.get(unique_id) if store else None) or {})
    if profile is None:
        record.pop(CONF_PROFILE, None)
        record.pop(CONF_PROFILE_WINS, None)
    else:
        record[CONF_PROFILE] = profile
        record[CONF_PROFILE_WINS] = True
    if height is not None:
        record[CONF_HEIGHT] = height
    calibration = stored_calibration({CONF_COVER_UNIQUE_ID: unique_id, **record})
    # A record that has stopped saying anything is deleted by the write, and a deleted
    # record is no record at all to the resolution. Saying it here is what keeps the two
    # answers the same for a shutter taken out of its only profile.
    resolved = resolve_cover(
        cfg, profiles=profiles, calibration=calibration if calibration.says_anything else None
    )

    # A profile is the measurement of a window of a certain travel, so a window whose
    # travel nobody knows cannot be given one. It is not an error to ask - it is the
    # state the review panel's form exists to fix - so the row comes back named, with
    # the problem on it and no numbers, and the panel shows the field instead of a table.
    if profile is not None and resolved.height is None:
        answer["problem"] = "missing_travel"
        return answer

    # A hypothetical profile whose numbers could not be read answers nothing for the
    # windows that would run on it - and `resolved.profile`, not the one in the
    # question, is which of them those are: a window whose `myhome.yaml` names a
    # profile follows it whatever the item asked.
    if resolved.profile is not None and resolved.profile in broken:
        answer["problem"] = broken[resolved.profile]
        return answer

    # The profile the window would really follow afterwards, which is the one asked
    # about unless the file's own `profile:` line answers instead. It is `overview`'s
    # own field, read the same way, so the row before and the row after are comparable
    # (REVIEW lot 7, open point 1).
    answer["profile"] = resolved.profile
    answer["height"] = resolved.height
    answer["origin"] = resolved.origin
    answer["source"] = resolved.source
    answer["values"] = _values(resolved)
    answer["keys"] = [
        {"key": key, "value": resolved.keys[key].value, "origin": resolved.keys[key].origin}
        for key in COVER_CALIBRATION_KEYS
        if key in resolved.keys
    ]
    answer["has_own"] = sorted(calibration.overrides)
    return answer


@callback
def async_preview(
    hass: HomeAssistant,
    entry: ConfigEntry,
    items: Sequence[Mapping[str, Any]],
    profile_values: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """What a batch of assignments would come to, without making any of them.

    The review panel shows a before and an after for every shutter it is about to move,
    and the after is what that shutter would really run on: the profile brought to its
    own travel, with whatever it measured for itself still on top. Computing that in the
    browser would mean a second copy of `derive_cover_from_profile` and of the
    precedence, and two copies of a travel model are two answers - the one thing this
    whole module exists to prevent. So the panel asks, and the server answers with the
    same function the shutter runs on.

    **It refuses nothing.** Every other command of this API answers a batch as a batch:
    `assign` refuses the whole of one if a single item cannot be written, because a batch
    half applied is a screen that has to explain which half. A preview writes nothing, so
    there is no half of anything, and a review panel showing eleven answers and one "this
    one still needs its travel" is exactly the screen the design asks for. Each item
    therefore carries either an answer or the one `translation_key` that stops it, and
    the panel renders that key's own sentence - the same sentence `assign` would send if
    the user confirmed anyway.

    **`profile_values`** asks the same question one level up: "if this profile said
    these numbers instead of the ones it has, what would each of these windows run on?"
    That is the profile card's live impact preview, and it is here for the reason the
    rest of this module is - the panel may not scale a profile itself. It changes
    nothing: the override lives in a copy of the profile mapping for the length of the
    call (`_hypothetical_profiles`), and the store is not touched by it any more than it
    is by the assignment above.

    No lock, no store write, no signal: this is a read, and a read during a measurement
    is allowed like every other read.
    """
    store = loaded_store(hass, entry)
    profiles, broken = _hypothetical_profiles(
        merged_profiles(yaml_profiles(hass, entry), store.profiles if store else {}),
        profile_values,
        store.raw_profiles if store else {},
    )
    covers = basic_covers(hass, entry)
    return {
        "entry_id": entry.entry_id,
        "items": [
            _previewed(hass, entry, item, covers=covers, profiles=profiles, broken=broken)
            for item in items
        ],
    }


# ------------------------------------------------------------------------- texts
def _read_language(language: str) -> dict[str, Any] | None:
    """Read one translation file off disk. Runs in an executor, never in the loop.

    The name is checked before it is joined to a path. `Path.__truediv__` resolves
    `..`, so a `language` of `../../../../etc/something` named a file well outside the
    integration - and a JSON file found there was served back through `_blocks`, which
    keeps whichever of `options` / `selector` / `config_panel` it happened to carry. It
    took an administrator to ask, and an administrator has no business reading arbitrary
    files off the host through a shutter panel either. A name that is not a language tag
    reads as "no file for that language", which is what the fallback chain already knows
    how to answer.
    """
    if not _A_LANGUAGE.match(language):
        LOGGER.warning("Ignoring a language that is not a language tag (%r)", language[:64])
        return None
    path = _TRANSLATIONS_DIR / f"{language}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@callback
def _candidates(language: str) -> list[str]:
    """The languages to try, in order: the one asked for, its base, then English.

    `it-CH` is Italian even though no `it-CH.json` exists, and an unknown language is
    English rather than nothing at all - a panel with no words is worse than a panel in
    the wrong one.

    **Lower-cased, because the answer must not depend on the filesystem.** A BCP 47 tag
    is case-insensitive and every file this integration ships is named in lower case, so
    `IT` is Italian; without the fold it was Italian on a macOS installation - whose
    filesystem matches `IT.json` to `it.json` - and English on a Linux one, from one
    request, over a name that came out of a browser. A language is half of a path
    (`_read_language`), and a path that resolves differently per host is not a thing to
    leave to the host.
    """
    wanted = (language or "").strip().replace("_", "-").lower()
    tries = [wanted] if wanted else []
    if "-" in wanted:
        tries.append(wanted.split("-", 1)[0])
    tries.append(DEFAULT_LANGUAGE)
    seen: set[str] = set()
    return [item for item in tries if item and not (item in seen or seen.add(item))]


async def _blocks(hass: HomeAssistant, language: str) -> dict[str, Any] | None:
    """The four blocks of one translation file, renamed, or None when there is no file."""
    loaded = await hass.async_add_executor_job(_read_language, language)
    if loaded is None:
        return None
    return {served: loaded[block] for block, served in TEXT_BLOCKS.items() if block in loaded}


@callback
def _over_english(english: Mapping[str, Any], wanted: Mapping[str, Any]) -> dict[str, Any]:
    """`wanted` laid over `english`, key by key, all the way down the tree.

    The panel's own block is written in **two languages during development** - the
    decision of 14 September, `.audit-2026-09/PLAN-0.6.0.md` - so `fr.json` is allowed to
    carry only some of `config_panel`, and a key it has not reached yet must arrive as
    the English sentence rather than as the dotted key. Whole-file selection would put a
    French user in front of an English panel the moment one key was added, or in front of
    a screen of identifiers; merging key by key gives them everything French that exists
    and English for the rest, which is what every screen of Home Assistant does.

    A leaf always wins over a leaf. Only two mappings are merged: a language that turned
    a sentence into a sub-tree, or the other way round, is taking the key over whole.
    """
    merged = dict(english)
    for key, value in wanted.items():
        under = merged.get(key)
        merged[key] = (
            _over_english(under, value)
            if isinstance(under, Mapping) and isinstance(value, Mapping)
            else value
        )
    return merged


async def async_texts(hass: HomeAssistant, language: str) -> dict[str, Any]:
    """The integration's own sentences, in the nearest language it has.

    The panel never carries a sentence of its own: every word it shows comes from the
    same seven files the guided flow shows, which is what keeps one wording, one
    lexicon and one round of translation for two clients. A key that is missing renders
    as the key, which is visible in a screenshot and impossible to mistake for a
    deliberate phrase.

    Four blocks travel, and one of them is renamed on the way out: see `TEXT_BLOCKS`.
    Every language is served **over English**, key by key, so that a block still being
    written - which under the decision of 14 September is every language but English and
    Italian, for `config_panel` - falls back a sentence at a time instead of a file at a
    time.

    Read once per language per Home Assistant run, in an executor, because a translation
    file is disk I/O and the resolution below is the same answer every time.
    """
    cache: dict[str, dict[str, Any]] = hass.data.setdefault(TEXTS_CACHE_KEY, {})
    candidates = _candidates(language)
    # The request as the chain really read it, which is what `fallback` is about: `IT`
    # served out of `it.json` is the language that was asked for and not a fallback from
    # it, and a panel that was told otherwise would show the "translated into English"
    # notice on a fully Italian screen.
    asked_for = candidates[0]
    for candidate in candidates:
        if (cached := cache.get(candidate)) is None:
            blocks = await _blocks(hass, candidate)
            if blocks is None:
                continue
            if candidate == DEFAULT_LANGUAGE:
                cached = cache[candidate] = blocks
            else:
                english = cache.get(DEFAULT_LANGUAGE)
                if english is None:
                    english = cache[DEFAULT_LANGUAGE] = (
                        await _blocks(hass, DEFAULT_LANGUAGE) or {}
                    )
                cached = cache[candidate] = _over_english(english, blocks)
        return {
            "language": candidate,
            "requested": language,
            "fallback": candidate != asked_for,
            "texts": cached,
        }
    # Unreachable while `translations/en.json` ships with the integration; a broken
    # installation gets an empty book rather than an exception three layers up.
    LOGGER.warning("No translations could be read for the panel (asked for %s)", language)
    return {"language": DEFAULT_LANGUAGE, "requested": language, "fallback": True, "texts": {}}


__all__ = [
    "CALIBRATION_LEVEL_BASIC",
    "CALIBRATION_LEVEL_PRECISE",
    "DEFAULT_LANGUAGE",
    "PREVIEW_PROBLEMS",
    "PROFILE_SOURCE_STORE",
    "PROFILE_SOURCE_YAML",
    "PROFILE_VALUE_KEYS",
    "TEXTS_CACHE_KEY",
    "async_cover_detail",
    "async_entries",
    "async_overview",
    "async_preview",
    "async_texts",
    "basic_covers",
    "calibrating_now",
    "is_advanced_cover",
    "yaml_profiles",
]
