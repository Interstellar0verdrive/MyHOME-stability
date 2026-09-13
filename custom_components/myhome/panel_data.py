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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from .calibration_store import (
    ResolvedCover,
    loaded_store,
    merged_profiles,
    profile_overrides,
    profile_provenance,
    resolve_cover_config,
)
from .const import (
    CALIBRATION_KEY_ORIGIN_OWN,
    CONF_ADVANCED_SHUTTER,
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_COVER_PROFILES,
    CONF_COVERS_FROM_FILE,
    CONF_ENTITIES,
    CONF_KEYS_FROM_FILE,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PLATFORMS,
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
# The blocks the panel is served. `options.*` is the guided flow's own wording, which
# the panel reuses wherever it says the same thing (the key labels, the error reasons);
# `selector.*` carries the five origin phrases, which is the one vocabulary the panel is
# forbidden from having its own copy of; `panel.*` is the panel's own block and is
# absent until the texts lot writes it, which is why this is a filter and not a schema.
TEXT_BLOCKS: tuple[str, ...] = ("options", "selector", "panel")
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
        "profiles": _profile_rows(hass, entry, profiles=profiles, covers=covers),
        "covers": covers,
        "order": store.raw_order if store else [],
        # Not an error and not an empty list to be styled: a gateway with only advanced
        # shutters has nothing this panel can do anything about, and says so once.
        "no_basic_covers": not covers,
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

    written = set(cfg.get(CONF_KEYS_FROM_FILE) or ())
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

    return {"entry_id": entry.entry_id, "cover": row, "keys": keys}


# ------------------------------------------------------------------------- texts
def _read_language(language: str) -> dict[str, Any] | None:
    """Read one translation file off disk. Runs in an executor, never in the loop."""
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
    """
    wanted = (language or "").strip().replace("_", "-")
    tries = [wanted] if wanted else []
    if "-" in wanted:
        tries.append(wanted.split("-", 1)[0])
    tries.append(DEFAULT_LANGUAGE)
    seen: set[str] = set()
    return [item for item in tries if item and not (item in seen or seen.add(item))]


async def async_texts(hass: HomeAssistant, language: str) -> dict[str, Any]:
    """The integration's own sentences, in the nearest language it has.

    The panel never carries a sentence of its own: every word it shows comes from the
    same seven files the guided flow shows, which is what keeps one wording, one
    lexicon and one round of translation for two clients. A key that is missing renders
    as the key, which is visible in a screenshot and impossible to mistake for a
    deliberate phrase.

    Read once per language per Home Assistant run, in an executor, because a translation
    file is disk I/O and the resolution below is the same answer every time.
    """
    cache: dict[str, dict[str, Any]] = hass.data.setdefault(TEXTS_CACHE_KEY, {})
    for candidate in _candidates(language):
        if (cached := cache.get(candidate)) is None:
            loaded = await hass.async_add_executor_job(_read_language, candidate)
            if loaded is None:
                continue
            cached = cache[candidate] = {
                block: loaded[block] for block in TEXT_BLOCKS if block in loaded
            }
        return {
            "language": candidate,
            "requested": language,
            "fallback": candidate != language,
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
    "PROFILE_SOURCE_STORE",
    "PROFILE_SOURCE_YAML",
    "PROFILE_VALUE_KEYS",
    "TEXTS_CACHE_KEY",
    "async_cover_detail",
    "async_entries",
    "async_overview",
    "async_texts",
    "basic_covers",
    "calibrating_now",
    "is_advanced_cover",
    "yaml_profiles",
]
