"""The panel's WebSocket contract, frozen: what goes in, and what comes back.

This module is deliberately data and no behaviour. It exists so that the backend and
the frontend can be written by two people at once without either waiting for the other:
the commands, their payloads and the shape of every answer are stated here once, in a
file both halves can read, and `.audit-2026-09/CONTRACT-0.6.0-ws.md` says the same thing
in prose with a worked example beside it. A change to either is a change to both.

**Scope.** 0.6.0 lot 2 is the *read* half. The three commands below are all there is:
one overview per gateway, one detail per shutter, and the sentences. The writes
(`assign`, `reorder`, `set_travel`, `cover_edit`, `cover_forget`, `profile_edit`,
`profile_rename`, `profile_delete`, `undo`) and the `subscribe` stream belong to lot 3
and are not declared here even as placeholders: a schema for a command that does not
exist is a promise nobody checked.

**Two names resolved against the plan.**

* The plan's working name for a cover's identifier in a payload was sometimes
  `cover_id` and sometimes `cover_unique_id`. It is `cover_unique_id` everywhere here,
  because that is what the store, the entity and every write command of lot 3 call it,
  and one name for one thing is worth more than either spelling.
* The plan's working name for a key's provenance inside `cover_detail` was `origin_key`.
  It is `origin` here, matching the cover-level `origin` beside it: they answer the same
  question at two altitudes and reading them as two unrelated fields is the mistake the
  shared name prevents.

**Values.** Every number is a JSON number or `null`; nothing is a formatted string, and
nothing is localised. Dates are ISO-8601 in UTC exactly as they were stored. Tokens
(`origin`, per-key `origin`, `source`, `level`) are the integration's own constants and
are turned into words by the panel through `myhome/calibration/texts` - never by the
backend, because the language is the *user's* and a WebSocket answer has no user in it.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers.typing import VolDictType

# --------------------------------------------------------------------- commands
WS_TYPE_OVERVIEW = "myhome/calibration/overview"
WS_TYPE_COVER_DETAIL = "myhome/calibration/cover_detail"
WS_TYPE_TEXTS = "myhome/calibration/texts"

WS_READ_COMMANDS: tuple[str, ...] = (WS_TYPE_OVERVIEW, WS_TYPE_COVER_DETAIL, WS_TYPE_TEXTS)

# `entry_id` is optional on the overview: a house with one gateway - which is nearly
# every house - should not have to ask which one it has before it can ask anything else.
# Omitted, it means the first loaded gateway, and `entries` in the answer lists them all
# so a house with two can choose and then say which.
OVERVIEW_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_OVERVIEW,
    vol.Optional("entry_id"): str,
}

COVER_DETAIL_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_COVER_DETAIL,
    vol.Required("entry_id"): str,
    vol.Required("cover_unique_id"): str,
}

# Omitted, `language` means the language this Home Assistant is configured in. The panel
# passes the *user's* language, which can differ from the server's.
TEXTS_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_TEXTS,
    vol.Optional("language"): str,
}


# ----------------------------------------------------------------------- errors
# The translation keys every refusal carries, alongside `translation_domain="myhome"`,
# so that the panel shows the same seven-language sentence the dialog shows. Until the
# texts lot writes them, a client falls back to the English `message` sent beside them,
# which is why every `send_error` here carries a real sentence and not a token.
ERROR_UNKNOWN_ENTRY = "unknown_entry"
ERROR_ENTRY_NOT_LOADED = "entry_not_loaded"
ERROR_UNKNOWN_COVER = "unknown_cover"
ERROR_ADVANCED_COVER = "advanced_cover"

WS_ERROR_KEYS: tuple[str, ...] = (
    ERROR_UNKNOWN_ENTRY,
    ERROR_ENTRY_NOT_LOADED,
    ERROR_UNKNOWN_COVER,
    ERROR_ADVANCED_COVER,
)


# ------------------------------------------------------------------- the answers
# The shape of each answer, as a list of its top-level keys. Not a validator: the
# payload is built by `panel_data.py` and validating our own output on every read would
# cost twelve shutters' worth of voluptuous per keystroke to catch a mistake a test
# catches once. It is here so that "what does `overview` contain" has an answer in the
# source tree and not only in a document, and `tests/test_websocket_api.py` asserts the
# real payloads against these tuples - which is what makes an accidental rename of a key
# a failing test rather than a blank column in the panel.
OVERVIEW_KEYS: tuple[str, ...] = (
    # Every configured gateway: `{entry_id, title, mac, loaded}`. Present even when only
    # one exists, so the panel's gateway picker has one rule and not two.
    "entries",
    # The gateway this payload is about.
    "entry_id",
    # `{cover_unique_id, name}` while a guided calibration is running on one of this
    # gateway's shutters, `null` otherwise. The panel's read-only lock hangs off it.
    "measuring",
    # One row per profile: see `PROFILE_KEYS`.
    "profiles",
    # One row per basic cover, already in the order the user put them in: `COVER_KEYS`.
    "covers",
    # The stored order as it is on disk - unique ids, some of which may name nothing any
    # more. The panel sends this list back, whole, when it reorders.
    "order",
    # True for a gateway whose covers are all advanced: there is nothing here to manage,
    # and the panel says so rather than showing an empty list.
    "no_basic_covers",
)

PROFILE_KEYS: tuple[str, ...] = (
    "name",
    # "store" (a guided calibration wrote it), "yaml" (`cover_profiles:` in the user's
    # file), or `null` for a name that is followed and not defined anywhere.
    "source",
    # Only a stored profile can be changed from the panel; a `cover_profiles:` block
    # belongs to a file this integration does not write.
    "editable",
    # The five numbers, by key: opening_time, closing_time, slat_time, opening_roll,
    # closing_roll. `{}` for a missing profile.
    "values",
    "reference_height",
    # The window it was measured on, as a unique id, and the name that window has now.
    # Both `null` for every profile stored before 0.6.0 and for every one written by
    # hand: the panel says "provenance not recorded" and nothing guesses.
    "measured_on",
    "measured_on_name",
    "measured_at",
    # Unique ids of the shutters that follow it because somebody said so on this
    # installation, and of those that follow it because `myhome.yaml` says so. Two
    # lists, because a deletion reaches the two differently.
    "followers",
    "followers_from_file",
    # True for a name some cover follows that no profile defines any more.
    "missing",
)

COVER_KEYS: tuple[str, ...] = (
    "unique_id",
    # `null` while the entity is not registered (an entry mid-reload).
    "entity_id",
    "name",
    # Resolved server-side from the entity registry, falling back to the device's.
    # Either may be `null`, and nothing in the panel depends on them being there.
    "area_id",
    "area",
    # This window's own travel in cm, from the record or from the file. `null` when
    # nobody has ever said.
    "height",
    "profile",
    # True when the profile comes from the cover's `profile:` line rather than from an
    # assignment made here.
    "profile_from_file",
    # True when that profile is not defined any more: the shutter has silently fallen
    # back to its own configuration and the panel has to say so.
    "profile_missing",
    # One of CALIBRATION_ORIGINS: measured / inherited / adjusted / from_the_file /
    # defaults. The same token `resolve_cover` gives the entity - never re-derived.
    "origin",
    # The exact string the `Calibration source` attribute carries, for the parity test
    # and for a diagnostic line in the panel.
    "source",
    # The travel model the shutter really runs on, by key.
    "values",
    # The keys of `values` that were measured on *this* window.
    "has_own",
    # "basic" / "precise" / `null`: how thorough the guided calibration was, from the
    # `raw` block it kept. `null` for a record with no `raw`.
    "level",
    # The tape check's deviation in cm, from the same block. `null` when not recorded.
    "verify_note",
    "measured_at",
    "calibrating",
    # Position in `covers`, so the panel can reorder without recomputing it.
    "order_index",
)

COVER_DETAIL_KEYS: tuple[str, ...] = ("entry_id", "cover", "keys")

COVER_DETAIL_KEY_KEYS: tuple[str, ...] = (
    "key",
    # What the shutter runs on today, and which of the four said it.
    "value",
    "origin",
    "own",
    # What this key would fall back to if this window's own measurement of it were
    # removed - the "eredita N" placeholder under an empty field, and the destination
    # "Rimuovi la misura" names before it removes anything.
    "inherited_value",
    "inherited_origin",
    # The profile scaled to this window, whether or not it is the one in use: what an
    # impact preview compares against. `null` when the cover follows no profile.
    "profile_value",
    # What `myhome.yaml` really writes for this cover, and only that: `null` for a key
    # the file leaves out, however completely the validator filled it in.
    "file_value",
    # ...and what the validator resolved where the file says nothing, which is this
    # integration's own default. `null` where the file does write the key, because the
    # default is then not visible from here.
    "default_value",
)

TEXTS_KEYS: tuple[str, ...] = (
    # The language actually served, after the fallback chain.
    "language",
    # The language that was asked for.
    "requested",
    # True when the two differ.
    "fallback",
    # The `options`, `selector` and (from the texts lot on) `panel` blocks of that
    # language's file, verbatim. A key that is not there renders as the key.
    "texts",
)


__all__ = [
    "COVER_DETAIL_KEYS",
    "COVER_DETAIL_KEY_KEYS",
    "COVER_DETAIL_SCHEMA",
    "COVER_KEYS",
    "ERROR_ADVANCED_COVER",
    "ERROR_ENTRY_NOT_LOADED",
    "ERROR_UNKNOWN_COVER",
    "ERROR_UNKNOWN_ENTRY",
    "OVERVIEW_KEYS",
    "OVERVIEW_SCHEMA",
    "PROFILE_KEYS",
    "TEXTS_KEYS",
    "TEXTS_SCHEMA",
    "WS_ERROR_KEYS",
    "WS_READ_COMMANDS",
    "WS_TYPE_COVER_DETAIL",
    "WS_TYPE_OVERVIEW",
    "WS_TYPE_TEXTS",
]
