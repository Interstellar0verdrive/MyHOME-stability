"""The panel's WebSocket contract, frozen: what goes in, and what comes back.

This module is deliberately data and no behaviour. It exists so that the backend and
the frontend can be written by two people at once without either waiting for the other:
the commands, their payloads and the shape of every answer are stated here once, in a
file both halves can read, and `.audit-2026-09/CONTRACT-0.6.0-ws.md` says the same thing
in prose with a worked example beside it. A change to either is a change to both.

**Scope.** The read half is three commands - one overview per gateway, one detail per
shutter, and the sentences - and is **frozen**: lot 3 adds to this file and changes
nothing in it. The write half is the nine commands below it plus `subscribe`, and every
one of them answers with an `overview` of exactly the shape the read half declares.

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

from .const import (
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_SLAT_TIME,
)

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


# ------------------------------------------------------------------ write commands
# Nine commands and one subscription, added by lot 3. Every one of them is admin-only
# like the reads, every one is refused while a guided calibration is running on any
# shutter of the gateway, and every one answers with a fresh `overview` plus the token
# that takes it back.
#
# `entry_id` is **required** here and optional on the reads, which is not an
# inconsistency: a read with no gateway named is a panel opening for the first time and
# asking what there is, while a write with none would be a change applied to whichever
# gateway happened to be first in the list.
WS_TYPE_ASSIGN = "myhome/calibration/assign"
WS_TYPE_REORDER = "myhome/calibration/reorder"
WS_TYPE_SET_TRAVEL = "myhome/calibration/set_travel"
WS_TYPE_COVER_EDIT = "myhome/calibration/cover_edit"
WS_TYPE_COVER_FORGET = "myhome/calibration/cover_forget"
WS_TYPE_PROFILE_EDIT = "myhome/calibration/profile_edit"
WS_TYPE_PROFILE_RENAME = "myhome/calibration/profile_rename"
WS_TYPE_PROFILE_DELETE = "myhome/calibration/profile_delete"
WS_TYPE_UNDO = "myhome/calibration/undo"
WS_TYPE_SUBSCRIBE = "myhome/calibration/subscribe"

WS_WRITE_COMMANDS: tuple[str, ...] = (
    WS_TYPE_ASSIGN,
    WS_TYPE_REORDER,
    WS_TYPE_SET_TRAVEL,
    WS_TYPE_COVER_EDIT,
    WS_TYPE_COVER_FORGET,
    WS_TYPE_PROFILE_EDIT,
    WS_TYPE_PROFILE_RENAME,
    WS_TYPE_PROFILE_DELETE,
    WS_TYPE_UNDO,
)

# A number as a person may have written it. Not `vol.Coerce(float)`: the guided dialog
# accepts a comma for a decimal point, because a shutter measured as `85,5` in Italian is
# a shutter, and `calibration_flow.parse_number` is the one thing that reads either. The
# range is checked there too, against the dialog's own bounds - here would be a second
# copy of numbers that already exist.
NUMBER = vol.Any(float, int, str)

# The five numbers a window can have measured on it, which is what a hand edit may set
# or clear - and, because a profile *is* a window that was measured, the same five a
# profile states. Restricted at the schema, so a key the travel model does not know is
# `invalid_format` naming the key rather than a value quietly stored and never read.
# They are `panel_data.PROFILE_VALUE_KEYS` on the read side, pinned equal by a test.
MEASURABLE_KEYS: tuple[str, ...] = (
    CONF_OPENING_TIME,
    CONF_CLOSING_TIME,
    CONF_SLAT_TIME,
    CONF_OPENING_ROLL,
    CONF_CLOSING_ROLL,
)

# An order is a *full* list of unique ids and each shutter sits in exactly one place in
# it, so a repeated id is a client that has lost track of its own model. Refused at the
# schema (`invalid_format`) rather than quietly deduplicated: the stored order would then
# be a different order from the one on the screen, and nothing would have said so. Ids
# naming no cover of this gateway are still dropped rather than refused (CONTRACT §9.2) -
# a browser tab left open across a reconfiguration is not a client bug.
ORDER = vol.All([str], vol.Unique())

# One batch: which shutters follow which profile, and the order they end up in.
#
# Assignment and position are **one write**, because on the screen they are one gesture -
# a shutter dropped into a group lands at a place in it, and two writes would leave a
# moment in which it was in the group and nowhere in particular. `order` is the whole
# resulting order (of the gateway); leave it out and every shutter that changed group
# goes to the end of the group it went to, which is what the tap and keyboard paths mean.
#
# `height` is the window's travel, and it is here because a profile cannot be scaled onto
# a window whose travel nobody knows: the batch carries the missing ones, which is the
# same write `set_travel` makes on its own.
ASSIGNMENT_SCHEMA = vol.Schema(
    {
        vol.Required("cover_unique_id"): str,
        vol.Required("profile"): vol.Any(str, None),
        vol.Optional("height"): vol.Any(NUMBER, None),
    }
)

ASSIGN_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_ASSIGN,
    vol.Required("entry_id"): str,
    vol.Required("assignments"): [ASSIGNMENT_SCHEMA],
    vol.Optional("order"): ORDER,
}

# `profile` present (`null` included, which is "Senza profilo") means `order` is that one
# group's full order and the other groups do not move; absent, `order` is the whole
# gateway's. The full list either way and never a move: a move has to be applied to the
# state the client last saw, and that is the thing these commands exist not to trust.
REORDER_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_REORDER,
    vol.Required("entry_id"): str,
    vol.Required("order"): ORDER,
    vol.Optional("profile"): vol.Any(str, None),
}

SET_TRAVEL_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SET_TRAVEL,
    vol.Required("entry_id"): str,
    vol.Required("cover_unique_id"): str,
    # `null` removes it: the window goes back to whatever its own configuration says.
    vol.Required("height"): vol.Any(NUMBER, None),
}

# `null` for a key is "stop overriding" - the key leaves the record and the window
# inherits again, which is the empty field with its "eredita N" placeholder. A key the
# message does not mention is not touched, so correcting one number is one number.
COVER_EDIT_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_COVER_EDIT,
    vol.Required("entry_id"): str,
    vol.Required("cover_unique_id"): str,
    vol.Required("overrides"): vol.Schema(
        {vol.Optional(key): vol.Any(NUMBER, None) for key in MEASURABLE_KEYS}
    ),
    vol.Optional("height"): vol.Any(NUMBER, None),
}

COVER_FORGET_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_COVER_FORGET,
    vol.Required("entry_id"): str,
    vol.Required("cover_unique_id"): str,
}

PROFILE_EDIT_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_PROFILE_EDIT,
    vol.Required("entry_id"): str,
    vol.Required("name"): str,
    vol.Required("values"): vol.Schema(
        {vol.Required(key): NUMBER for key in MEASURABLE_KEYS}
    ),
    # The window the profile was measured on, which is what scales it onto every other.
    vol.Required("reference_height"): NUMBER,
}

PROFILE_RENAME_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_PROFILE_RENAME,
    vol.Required("entry_id"): str,
    vol.Required("name"): str,
    vol.Required("new_name"): str,
}

PROFILE_DELETE_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_PROFILE_DELETE,
    vol.Required("entry_id"): str,
    vol.Required("name"): str,
}

UNDO_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_UNDO,
    vol.Required("entry_id"): str,
    vol.Required("undo_token"): str,
}

SUBSCRIBE_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SUBSCRIBE,
    vol.Optional("entry_id"): str,
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
# ...and the refusals a write can add to those. The first two are the lock: a guided
# calibration is holding a shutter and has numbers half measured, or another change to
# the same gateway is being applied and this one would decide against a store it is
# about to stop being. The rest are what the guided dialog already refuses, under the
# keys it already uses (`not_a_number`, `out_of_range`, `invalid_name` come from
# `calibration_flow` itself and are not restated here).
ERROR_BUSY_CALIBRATING = "busy_calibrating"
ERROR_WRITE_IN_PROGRESS = "write_in_progress"
ERROR_MISSING_TRAVEL = "missing_travel"
ERROR_UNKNOWN_PROFILE = "unknown_profile"
ERROR_PROFILE_NOT_EDITABLE = "profile_not_editable"
ERROR_NAME_IN_USE = "name_in_use"
ERROR_UNDO_EXPIRED = "undo_expired"

WS_ERROR_KEYS: tuple[str, ...] = (
    ERROR_UNKNOWN_ENTRY,
    ERROR_ENTRY_NOT_LOADED,
    ERROR_UNKNOWN_COVER,
    ERROR_ADVANCED_COVER,
    ERROR_BUSY_CALIBRATING,
    ERROR_WRITE_IN_PROGRESS,
    ERROR_MISSING_TRAVEL,
    ERROR_UNKNOWN_PROFILE,
    ERROR_PROFILE_NOT_EDITABLE,
    ERROR_NAME_IN_USE,
    ERROR_UNDO_EXPIRED,
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

# ------------------------------------------------------- what a write answers with
# Every write answers with the same two keys and then its own. `overview` is the whole
# payload above, rebuilt after the write: the client replaces its model with it rather
# than patching, which is what makes a browser tab left open for a day either right or
# visibly stale and never quietly half of each.
#
# `undo_token` is an opaque hex that takes exactly that write back, `null` when the write
# changed nothing (a drag that ended where it started, a value retyped as it was) - there
# is nothing to take back and an "Annulla" that did nothing would be worse than none.
WRITE_KEYS: tuple[str, ...] = ("overview", "undo_token")

# ...how many of the batch's shutters really changed. A row the user did not touch is
# not counted, so the strip can say "3 tapparelle" and mean it.
ASSIGN_KEYS: tuple[str, ...] = (*WRITE_KEYS, "applied")
REORDER_KEYS: tuple[str, ...] = WRITE_KEYS
SET_TRAVEL_KEYS: tuple[str, ...] = WRITE_KEYS
COVER_EDIT_KEYS: tuple[str, ...] = WRITE_KEYS
# Where this window's numbers come from now that its own are gone: "profile", "file" or
# "defaults", and the profile's name when there is one. Resolved after the deletion
# rather than predicted before it, so the sentence and the shutter agree.
COVER_FORGET_KEYS: tuple[str, ...] = (*WRITE_KEYS, "falls_back_to", "profile")
# Every window that follows the profile, named before the user goes looking for them.
PROFILE_EDIT_KEYS: tuple[str, ...] = (*WRITE_KEYS, "affected")
# How many followers moved with the name, and the ones that could not: a window whose
# own `profile:` line in `myhome.yaml` names the old profile is the user's file talking,
# and this integration does not write that file.
PROFILE_RENAME_KEYS: tuple[str, ...] = (*WRITE_KEYS, "moved", "from_file")
# The same split at a deletion: the assignments that went with the profile, and the
# `profile:` lines that now name nothing.
PROFILE_DELETE_KEYS: tuple[str, ...] = (*WRITE_KEYS, "covers_affected", "from_file")
# An undo answers like any other write and hands back no token of its own (`undo_token`
# is `null`): undoing an undo would be two buttons swapping a gateway back and forth
# with nothing on the screen saying which way round it is now. `undone` names the
# command that was taken back.
UNDO_KEYS: tuple[str, ...] = (*WRITE_KEYS, "undone")

# ------------------------------------------------------------- what a subscription says
# `overview` on subscribing, after every successful write and after every undo;
# `measuring` whenever a guided calibration starts or ends on one of this gateway's
# shutters, which is what raises and drops the panel's read-only lock.
#
# The plan's third event, `applying`, is deliberately absent: it existed to cover the
# seconds a config entry spends reloading, and a write does not reload one any more
# (decision 4). There is no window to be honest about.
WS_EVENT_OVERVIEW = "overview"
WS_EVENT_MEASURING = "measuring"
WS_EVENT_TYPES: tuple[str, ...] = (WS_EVENT_OVERVIEW, WS_EVENT_MEASURING)


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
    "ASSIGNMENT_SCHEMA",
    "ASSIGN_KEYS",
    "ASSIGN_SCHEMA",
    "COVER_DETAIL_KEYS",
    "COVER_DETAIL_KEY_KEYS",
    "COVER_DETAIL_SCHEMA",
    "COVER_EDIT_KEYS",
    "COVER_EDIT_SCHEMA",
    "COVER_FORGET_KEYS",
    "COVER_FORGET_SCHEMA",
    "COVER_KEYS",
    "ERROR_ADVANCED_COVER",
    "ERROR_BUSY_CALIBRATING",
    "ERROR_ENTRY_NOT_LOADED",
    "ERROR_MISSING_TRAVEL",
    "ERROR_NAME_IN_USE",
    "ERROR_PROFILE_NOT_EDITABLE",
    "ERROR_UNDO_EXPIRED",
    "ERROR_UNKNOWN_COVER",
    "ERROR_UNKNOWN_ENTRY",
    "ERROR_UNKNOWN_PROFILE",
    "ERROR_WRITE_IN_PROGRESS",
    "MEASURABLE_KEYS",
    "NUMBER",
    "ORDER",
    "OVERVIEW_KEYS",
    "OVERVIEW_SCHEMA",
    "PROFILE_DELETE_KEYS",
    "PROFILE_DELETE_SCHEMA",
    "PROFILE_EDIT_KEYS",
    "PROFILE_EDIT_SCHEMA",
    "PROFILE_KEYS",
    "PROFILE_RENAME_KEYS",
    "PROFILE_RENAME_SCHEMA",
    "REORDER_KEYS",
    "REORDER_SCHEMA",
    "SET_TRAVEL_KEYS",
    "SET_TRAVEL_SCHEMA",
    "SUBSCRIBE_SCHEMA",
    "TEXTS_KEYS",
    "TEXTS_SCHEMA",
    "UNDO_KEYS",
    "UNDO_SCHEMA",
    "WRITE_KEYS",
    "WS_ERROR_KEYS",
    "WS_EVENT_MEASURING",
    "WS_EVENT_OVERVIEW",
    "WS_EVENT_TYPES",
    "WS_READ_COMMANDS",
    "WS_TYPE_ASSIGN",
    "WS_TYPE_COVER_DETAIL",
    "WS_TYPE_COVER_EDIT",
    "WS_TYPE_COVER_FORGET",
    "WS_TYPE_OVERVIEW",
    "WS_TYPE_PROFILE_DELETE",
    "WS_TYPE_PROFILE_EDIT",
    "WS_TYPE_PROFILE_RENAME",
    "WS_TYPE_REORDER",
    "WS_TYPE_SET_TRAVEL",
    "WS_TYPE_SUBSCRIBE",
    "WS_TYPE_TEXTS",
    "WS_TYPE_UNDO",
    "WS_WRITE_COMMANDS",
]
