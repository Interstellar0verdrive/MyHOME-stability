"""The panel's WebSocket contract, frozen: what goes in, and what comes back.

This module is deliberately data and no behaviour. It exists so that the backend and
the frontend can be written by two people at once without either waiting for the other:
the commands, their payloads and the shape of every answer are stated here once, in a
file both halves can read, and `.audit-2026-09/CONTRACT-0.6.0-ws.md` says the same thing
in prose with a worked example beside it. A change to either is a change to both.

**Scope.** The read half is four commands - one overview per gateway, one detail per
shutter, the sentences, and what an assignment nobody has made yet would come to - and
its first three are **frozen**: lot 3 added to this file and changed nothing in it. The
write half is the nine commands below it plus `subscribe`, and every one of them answers
with an `overview` of exactly the shape the read half declares. The third part is the
guided calibration's session (0.6.0 wizard, lot L0): ten commands, one event and the
snapshot they all carry, declared at the bottom of this file before any of them exists.

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

import math
from typing import Any

import voluptuous as vol
from homeassistant.helpers.typing import VolDictType

from .const import (
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_REFERENCE_HEIGHT,
    CONF_SLAT_TIME,
)

# --------------------------------------------------------------------- commands
WS_TYPE_OVERVIEW = "myhome/calibration/overview"
WS_TYPE_COVER_DETAIL = "myhome/calibration/cover_detail"
WS_TYPE_TEXTS = "myhome/calibration/texts"
WS_TYPE_PREVIEW = "myhome/calibration/preview"

WS_READ_COMMANDS: tuple[str, ...] = (
    WS_TYPE_OVERVIEW,
    WS_TYPE_COVER_DETAIL,
    WS_TYPE_TEXTS,
    WS_TYPE_PREVIEW,
)

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

# "If these shutters followed these profiles, at these travels, what would they run on?"
#
# The items are `ASSIGN_SCHEMA`'s items - the same three keys, read the same way - because
# the whole point of the command is that its answer is what `assign` would produce. It is
# declared after the assignment schema itself, below, for that reason.
#
# `entry_id` is **required**, like a write's and unlike the other reads': a preview is
# always about a batch the user is in the middle of composing on one gateway's screen,
# and there is no "the gateway I have" version of that question.


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

# The read that asks what the write above would come to (CONTRACT §11). One item in, one
# item out, in the same order, and `ASSIGNMENT_SCHEMA` for both so that the panel sends
# the batch it is composing rather than a translation of it. No `order`: a position is
# not a number the shutter runs on and previewing one would answer nothing.
# ...and, optionally, the numbers to pretend a profile has while the question is
# answered. `{name: {the five values, reference_height}}` - exactly what `profile_edit`
# would write - because the profile card's impact preview asks "if this profile said
# these instead, what would its followers run on?", and the panel may no more scale a
# profile for that screen than for the review panel. It overrides the numbers of a
# profile the gateway already has and never defines a new name; the whole override is
# read-only and reaches nothing but the answer (`panel_data._hypothetical_profiles`).
PROFILE_VALUES_SCHEMA = vol.Schema(
    {
        str: vol.Schema(
            {
                vol.Required(key): NUMBER
                for key in (*MEASURABLE_KEYS, CONF_REFERENCE_HEIGHT)
            }
        )
    }
)

PREVIEW_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_PREVIEW,
    vol.Required("entry_id"): str,
    vol.Required("items"): [ASSIGNMENT_SCHEMA],
    vol.Optional("profile_values"): PROFILE_VALUES_SCHEMA,
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
    # ...and, beside it, *whose* calibration it is: `SESSION_OVERVIEW_KEYS` for a
    # session of this panel's, `null` for the guided dialog, for the 0.4.2 action and
    # for a gateway nobody is measuring (0.6.0 wizard, lot B3). Declared with the rest
    # of the session's contract at the bottom of this file; the key is here because
    # this is the lot in which the server really sends it.
    "session",
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

# `forget` (lot 8) is what "Rimuovi la misura" would leave: `falls_back_to`
# (`"profile"` / `"file"` / `"defaults"`), the profile's name when there is one, and
# whether the curtain travel survives the removal - `myhome.yaml`'s own `height:` does,
# a travel somebody typed into the panel does not. It is the same three facts
# `cover_forget` answers with *after* the write, read the same way (resolve the window
# with the record gone), so the confirmation and the result cannot disagree.
COVER_DETAIL_KEYS: tuple[str, ...] = ("entry_id", "cover", "keys", "forget")

COVER_DETAIL_FORGET_KEYS: tuple[str, ...] = ("falls_back_to", "profile", "travel_stays")

PREVIEW_KEYS: tuple[str, ...] = ("entry_id", "items")

PREVIEW_ITEM_KEYS: tuple[str, ...] = (
    "cover_unique_id",
    # The profile that was asked about, and the travel the answer was worked out at -
    # the one in the question when it carried one, and otherwise the one this window was
    # already known to have.
    "profile",
    "height",
    # `null`, or the one `translation_key` that stops this item: `unknown_cover`,
    # `advanced_cover`, `unknown_profile`, `missing_travel`, `not_a_number`,
    # `out_of_range`. The same keys `assign` refuses with, so the panel shows the same
    # sentence whether the problem was found before the write or by it.
    "problem",
    # ...and, when there is no problem, exactly what the overview would say about this
    # shutter once the batch had been written: same tokens, same numbers, same function.
    "origin",
    "source",
    "values",
    # One entry per key of `values`: `{key, value, origin}`, the per-key origin being
    # `own` / `profile` / `file` / `default` as in `cover_detail`.
    "keys",
    "has_own",
)

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
# ...and, from the calibration session on (0.6.0 wizard), `session`: the whole snapshot of
# the gateway's session, or `null`, on subscribing and after every transition. It is on
# the same subscription rather than a second one because the panel already has one
# subscription that survives reconnections, and two would be two things to keep alive.
# Declared here with the rest of the session contract (lot L0); the server sends it from
# lot B3.
WS_EVENT_SESSION = "session"
WS_EVENT_TYPES: tuple[str, ...] = (WS_EVENT_OVERVIEW, WS_EVENT_MEASURING, WS_EVENT_SESSION)


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


# ============================================================ the calibration session
# 0.6.0 wizard, lot L0: the guided calibration moves into the panel, and this block is
# the whole of what the panel and the backend say to each other about it - frozen before
# either half is written, like the blocks above. `docs/panel-websocket-api.md` §11-§14
# says the same in prose, `panel_src/src/engine/session-contract.ts` restates it as
# TypeScript types, and `tests/fixtures/panel_session_examples.json` shows it: a change
# to one is a change to all four, in one commit that says it is a contract amendment.
#
# Two vocabularies meet here, on purpose (SPEC-0.6.0-wizard §3.4, §3.11):
#
# * **At the boundary** - `state`, the verbs, the names of measured values - the words
#   are the published contract's (`docs/calibration-contract-proposal.md` Part 2):
#   `awaiting_endpoint`, `travel_cm`, `opening_time_s`, `stop`/`leave`/`cancel`.
# * **Screen identity and text** - `step`, `actions`, `form.field`, `placeholders`,
#   `movement.progress_action` - are the guided dialog's own ids, because they are the
#   keys of `options.step.<step>` / `options.progress.<action>`, sentences already
#   translated into seven languages that the panel reuses instead of rewriting.
#
# None of the commands below is registered yet (lot B3 registers them), so they are in
# a tuple of their own and not in `WS_READ_COMMANDS` / `WS_WRITE_COMMANDS`, which the
# door tests compare with the commands really on the socket.
WS_TYPE_SESSION_GET = "myhome/calibration/session/get"
WS_TYPE_SESSION_START = "myhome/calibration/session/start"
WS_TYPE_SESSION_ATTACH = "myhome/calibration/session/attach"
WS_TYPE_SESSION_HEARTBEAT = "myhome/calibration/session/heartbeat"
WS_TYPE_SESSION_ACT = "myhome/calibration/session/act"
WS_TYPE_SESSION_STOP = "myhome/calibration/session/stop"
WS_TYPE_SESSION_LEAVE = "myhome/calibration/session/leave"
WS_TYPE_SESSION_CANCEL = "myhome/calibration/session/cancel"
WS_TYPE_SESSION_SAVE = "myhome/calibration/session/save"
WS_TYPE_SESSION_END_OTHER = "myhome/calibration/session/end_other"

WS_SESSION_COMMANDS: tuple[str, ...] = (
    WS_TYPE_SESSION_GET,
    WS_TYPE_SESSION_START,
    WS_TYPE_SESSION_ATTACH,
    WS_TYPE_SESSION_HEARTBEAT,
    WS_TYPE_SESSION_ACT,
    WS_TYPE_SESSION_STOP,
    WS_TYPE_SESSION_LEAVE,
    WS_TYPE_SESSION_CANCEL,
    WS_TYPE_SESSION_SAVE,
    WS_TYPE_SESSION_END_OTHER,
)

# --------------------------------------------------------------- the vocabularies
# The contract's states (§2.2), plus the terminal `ended` it leaves implicit. `idle` is
# not one of them: no session is `session: null`, not a snapshot saying "nothing". Nor
# is `fitting`: the fit runs synchronously between two transitions, and the contract
# asks that what a backend does not produce be absent rather than empty.
SESSION_STATES: tuple[str, ...] = (
    "armed",
    "briefing",
    "running",
    "positioning",
    "awaiting_reading",
    "checking",
    "review",
    "saved",
    "ended",
)
# Only `running` has one, and always one of these once the motor has echoed; before the
# echo (`open_start`, `open_full_start`, `close_start`) it is `null`.
SESSION_SUBSTATES: tuple[str, ...] = ("awaiting_endpoint", "awaiting_stop")

# Why a session is over: `outcome.reason`. `saved` goes with `state: "saved"`, every
# other one with `state: "ended"`.
SESSION_OUTCOMES: tuple[str, ...] = (
    "saved",
    "cancelled",
    "expired",
    "unloaded",
    "left",
    "cover_gone",
)

# `problem.code`: the dialog's `PROBLEM_REASONS`, in its order, plus the one the panel
# adds - a step whose measurement was spoiled by a stop or by a movement nobody in the
# session commanded (SPEC §3.5, §3.7). The step is `problem_<code>` for every one.
SESSION_PROBLEMS: tuple[str, ...] = (
    "no_echo",
    "not_delivered",
    "not_stopped",
    "busy",
    "bad_point",
    "timeout",
    "unknown",
    "interrupted",
)

# The dialog's own values, spelled as the dialog spells them (`calibration_flow.PATH_*`,
# the `refine_scope` menu).
SESSION_PATHS: tuple[str, ...] = ("path_a", "path_b", "path_c")
SESSION_SCOPES: tuple[str, ...] = ("times_only", "times_and_rolls", "points_only")
# The contract's two levels (§2.4). The dialog's texts and the stored `raw` block say
# "precise" for the second; the boundary says what the contract says.
SESSION_LEVELS: tuple[str, ...] = ("basic", "thorough")
SESSION_SAVE_TARGETS: tuple[str, ...] = ("profile", "cover_only")
# `review.variant`, which is the `summary_<variant>` step the review stands on.
SESSION_REVIEW_VARIANTS: tuple[str, ...] = ("basic", "short", "correction", "precise")
# `position_known`: the end stop the session last saw the shutter reach, `null` when it
# is anywhere else or when something outside the session has moved it since.
SESSION_POSITIONS: tuple[str, ...] = ("closed", "open")
# `movement.direction`, `reading.direction`: `const.DIRECTION_OPEN` / `DIRECTION_CLOSE`.
SESSION_DIRECTIONS: tuple[str, ...] = ("open", "close")
# `movement.kind`: to an end stop, a free run the user ends with a press (the lift-off
# run while its stop goes out included), and a run to a fraction of the travel.
SESSION_MOVEMENT_KINDS: tuple[str, ...] = ("homing", "free", "fraction")
# `movement.progress_action`: the key of the sentence the screen shows while that
# movement runs (`options.progress.<action>`), which is the dialog's own. Frozen as a
# vocabulary and not merely as "a string", so that the panel can map every one of them
# onto a screen and know the list is complete.
SESSION_PROGRESS_ACTIONS: tuple[str, ...] = (
    "homing_closed",
    "homing_open",
    "starting_open",
    "starting_close",
    "running_down",
    "running_up",
    "stopping_lift",
    "starting_open_full",
)
# `press.kind`: the instant the bottom edge leaves its rest, or the motor at an end stop.
SESSION_PRESS_KINDS: tuple[str, ...] = ("lift_off", "end_stop")
# `form.field` (the dialog's field names), `form.kind`, and `form.error` (the dialog's
# `options.error.*` keys, which are the contract's `bad_reading` in detail).
SESSION_FORM_FIELDS: tuple[str, ...] = ("profile", "height", "measured_cm", "gap_cm", "name")
SESSION_FORM_KINDS: tuple[str, ...] = ("number", "choice", "text")
# `form.unit`: the one unit any field of this conversation carries, or `null` for a name.
SESSION_FORM_UNITS: tuple[str, ...] = ("cm",)
SESSION_FORM_ERRORS: tuple[str, ...] = (
    "not_a_number",
    "out_of_range",
    "above_the_travel",
    "invalid_name",
)
# `notice`: something the screen has to say about what happened *around* the step,
# which is not a problem - nothing was lost. `rehomed`: the shutter had been moved from
# outside and the session brought it back to its end stop before timing anything.
# `reading_stale`: it was moved after it was positioned, so the reading on the screen
# would not be the reading of this step (SPEC §3.7).
SESSION_NOTICES: tuple[str, ...] = ("rehomed", "reading_stale")
# `already_calibrating`'s `{by}`: a live session of the panel's, anything else that holds
# the shutter (the dialog, the 0.4.2 service), or the gateway still reserved by a session
# that has already ended while its shutter ran on (§11.6 of the document). The third is
# not a session anybody can go back to, and the screen may not offer to resume it.
SESSION_HOLDERS: tuple[str, ...] = ("panel", "other", "reserved")

# Every step a snapshot can stand on (SPEC §3.4), under the dialog's own ids - the name
# of its `async_step_<id>` method, and of its `options.step.<id>` texts where it has
# any. `problem_interrupted` is the one step the dialog does not have. `saved` and
# `ended` have no step (`step: null`): their screens are the panel's own.
SESSION_STEPS: tuple[str, ...] = (
    # choosing
    "path",
    "path_a",
    "path_b",
    "path_c",
    "refine_scope",
    # the first homing
    "home_closed",
    "home_closed_done",
    # the ascent: two runs, two presses
    "open_timed",
    "open_brief",
    "open_start",
    "open_lift",
    "lift_stop",
    "lift_check",
    "lift_check_late",
    "lift_gap",
    "lift_early",
    "open_home_again",
    "closed_again",
    "open_full_brief",
    "open_full_start",
    "open_top",
    "open_result",
    "open_result_gap",
    # the curtain travel
    "height_read",
    "height",
    "height_result",
    # the descent
    "close_timed",
    "close_brief",
    "close_start",
    "close_bottom",
    "close_result",
    # the tape phase
    "tape_brief",
    "half_down",
    "half_up",
    "quarter_down",
    "three_quarter_down",
    "quarter_up",
    "three_quarter_up",
    "verify",
    "verify_b",
    "tape_run",
    "measure_descent",
    "measure_ascent",
    "tape_result",
    "measure_verify",
    "verify_result",
    "verify_offer",
    # the end
    "profile_name",
    "summary_basic",
    "summary_short",
    "summary_correction",
    "summary_precise",
    # what went wrong
    "problem_no_echo",
    "problem_not_delivered",
    "problem_not_stopped",
    "problem_busy",
    "problem_bad_point",
    "problem_timeout",
    "problem_unknown",
    "problem_interrupted",
)

# The steps whose `options.step.<step>` texts the panel shows as they are, in every
# language they are translated into (SPEC §5.5): every step above that has texts of its
# own, except the four summaries - which speak of closing the dialog and of
# "Configura -> Calibrazioni" - and `problem_interrupted`, which has none. The positioning
# stages are absent because they have no step text: their screen is
# `options.progress.<movement.progress_action>`. A test holds every step here to having
# its texts and to naming no dialog.
SESSION_REUSED_STEPS: tuple[str, ...] = (
    "path",
    "path_a",
    "path_b",
    "path_c",
    "refine_scope",
    "home_closed_done",
    "open_brief",
    "open_lift",
    "lift_check",
    "lift_check_late",
    "lift_gap",
    "lift_early",
    "closed_again",
    "open_full_brief",
    "open_top",
    "open_result",
    "open_result_gap",
    "height",
    "height_result",
    "close_brief",
    "close_bottom",
    "close_result",
    "tape_brief",
    "measure_descent",
    "measure_ascent",
    "tape_result",
    "measure_verify",
    "verify_result",
    "verify_offer",
    "profile_name",
    "problem_no_echo",
    "problem_not_delivered",
    "problem_not_stopped",
    "problem_busy",
    "problem_bad_point",
    "problem_timeout",
    "problem_unknown",
)

# What `plan` may contain: the dialog's plan stages (`calibration_flow.PLAN_*`), which
# are step ids plus `summary`, the stage the dialog resolves to one of the four
# `summary_<variant>` steps when it gets there.
SESSION_PLAN_STAGES: tuple[str, ...] = (
    "home_closed",
    "open_timed",
    "height_read",
    "close_timed",
    "tape_brief",
    "half_down",
    "half_up",
    "quarter_down",
    "three_quarter_down",
    "quarter_up",
    "three_quarter_up",
    "verify",
    "verify_b",
    "verify_offer",
    "profile_name",
    "summary",
)

# Every value `actions` can carry: the dialog's `menu_options` ids, each one a key of
# `options.step.<step>.menu_options` - which is where its label comes from. `actions` is
# a list of ways *forward* only: the dialog's two ways out are commands of their own, and
# neither is ever in it.
#
# * `save` is the `save` command, and the exits it offers are `review.targets`;
# * `cancel_flow` is the `cancel` verb. It is deliberately not an `act`, because `act`
#   carries a `revision` and is refused against a stale one - and a transition the user
#   did not cause (a press timing out, a rehoming) would then be able to refuse the
#   button that says "Cancel". Cancelling is never refused for concurrency (SPEC §5.2,
#   "Annulla mai silenzioso"), so it does not travel on a command that could be.
#
# `submit` is the one `act` value that is not a menu option: it sends `form`'s value.
SESSION_ACTIONS: tuple[str, ...] = (
    "path_a",
    "path_b",
    "path_c",
    "begin",
    "times_only",
    "times_and_rolls",
    "points_only",
    "confirm_closed",
    "open_start",
    "lifted_off",
    "lift_too_early",
    "lift_accept",
    "lift_gap",
    "confirm_closed_again",
    "open_full_start",
    "stopped_open",
    "accept_step",
    "repeat_measure",
    "close_start",
    "stopped_closed",
    "tape_start",
    "repeat_tape",
    "tape_not_right",
    "verify_now",
    "skip_verify",
    "refine",
    "repeat_step",
    "not_right",
)
SESSION_SUBMIT = "submit"

# The names of measured values at the boundary (SPEC §3.11), against the names the
# store, `myhome.yaml` and the fourteen existing commands use for the same thing. Only
# the new session commands speak the contract's names; renaming the old ones would
# break the panel already written, and is backlog for the upstream port.
SESSION_BOUNDARY_NAMES: dict[str, str] = {
    "height": "travel_cm",
    "reference_height": "reference_travel_cm",
    "opening_time": "opening_time_s",
    "closing_time": "closing_time_s",
    "slat_time": "slat_time_s",
    "opening_roll": "opening_roll",
    "closing_roll": "closing_roll",
    "stop_latency": "stop_latency_s",
    "start_delay": "start_delay_s",
}
# `review.rows[].key`, in the order the review lists them: the travel, then the five a
# window can have measured on it. `review.side_effects[].key` is any of the eight.
SESSION_REVIEW_ROW_KEYS: tuple[str, ...] = (
    "travel_cm",
    "opening_time_s",
    "closing_time_s",
    "slat_time_s",
    "opening_roll",
    "closing_roll",
)
SESSION_VALUE_KEYS: tuple[str, ...] = (
    *SESSION_REVIEW_ROW_KEYS,
    "stop_latency_s",
    "start_delay_s",
)

# What this backend offers (contract §2.5: "a backend that offers less should say so
# through its capabilities"). Answered by `get`, the same every time.
SESSION_CAPABILITIES: dict[str, Any] = {
    "model": "roll_nonlinear",
    "paths": list(SESSION_PATHS),
    "levels": list(SESSION_LEVELS),
    "scopes": list(SESSION_SCOPES),
    "check": True,
    "fit_residuals": True,
    "repeat_step": True,
    "save_targets": list(SESSION_SAVE_TARGETS),
    "bulk": False,
}

# ------------------------------------------------------------------ the payloads
# `client_id` is made by the panel, one per browser tab (`sessionStorage`), and is what
# ownership is held by. A UUID fits; so does anything else of that alphabet, which is
# the point of saying the alphabet rather than "a UUID".
CLIENT_ID = vol.All(str, vol.Match(r"^[A-Za-z0-9-]{8,64}$"))


def _not_a_bool(value: Any) -> Any:
    """Refuse `true`/`false` where a number is meant: Python counts a bool as an int."""
    if isinstance(value, bool):
        raise vol.Invalid("expected a number, not a boolean")
    return value


def _a_finite_number(value: Any) -> Any:
    """Refuse `NaN` and the two infinities where a measurement is meant.

    A JSON document has no literal for them, but `json.loads` reads `NaN`, `Infinity`
    and `-Infinity` by default and a client can put one on the wire. None of the three
    is a length: fed to the fit they make every number after them `nan`, and the screen
    three steps later is the one that breaks (lot B1, R1). The controller has its own
    net (`calibration_session._finite`, which is also what catches the *string* `"nan"`
    that `parse_number` would be happy with); this one is the door, so that a frame
    carrying one is `invalid_format` and never reaches the arithmetic at all.
    """
    if isinstance(value, float) and not math.isfinite(value):
        raise vol.Invalid("expected a finite number")
    return value


# The revision the client last read. A number that cannot be one is a malformed frame;
# a well-formed one that is not the current one is `revision_conflict`.
REVISION = vol.All(_not_a_bool, int, vol.Range(min=0))
# `act`'s value: the text typed in a field (a number stays a string, so a decimal comma
# survives to `parse_number`), the profile chosen, or nothing. A JSON number is taken
# too, for a client that has one - provided it is one.
SESSION_VALUE = vol.Any(
    None, str, vol.All(_not_a_bool, vol.Any(int, float), _a_finite_number)
)

SESSION_GET_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_GET,
    vol.Required("entry_id"): str,
}


def _start_combination(data: dict[str, Any]) -> dict[str, Any]:
    """`profile` belongs to paths B and C, `scope` to path C: anything else is malformed.

    Refused at the schema (`invalid_format`) rather than ignored, because a `start` that
    silently dropped half of what the panel asked for would open a screen other than the
    one the user pressed a button for.
    """
    path = data.get("path")
    if "profile" in data and path not in ("path_b", "path_c"):
        raise vol.Invalid("profile is only meaningful with path_b or path_c", path=["profile"])
    if "scope" in data and path != "path_c":
        raise vol.Invalid("scope is only meaningful with path_c", path=["scope"])
    return data


# `start` never moves anything and never skips a screen that comes before a movement:
# with no `path` the session is born on `path`, with `path_a` on `path_a` (the warning
# before the first movement), with `path_b` on `path_b` (the profile preselected when
# one is named), with `path_c` on `path_c`, or on `refine_scope` when the profile is
# named too - `scope` then only highlights that scope (`intent`), it does not choose it.
SESSION_START_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required("type"): WS_TYPE_SESSION_START,
            vol.Required("entry_id"): str,
            vol.Required("cover_unique_id"): str,
            vol.Required("client_id"): CLIENT_ID,
            vol.Optional("path"): vol.In(SESSION_PATHS),
            vol.Optional("profile"): str,
            vol.Optional("scope"): vol.In(SESSION_SCOPES),
        }
    ),
    _start_combination,
)

# `claim: true` takes the session from a present owner, after the screen asked. Without
# it an attach from another client is read-only while the owner is present, and makes
# the attaching client the owner when the owner is not.
SESSION_ATTACH_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_ATTACH,
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("client_id"): CLIENT_ID,
    vol.Optional("claim"): bool,
}

SESSION_HEARTBEAT_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_HEARTBEAT,
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("client_id"): CLIENT_ID,
}

# `action` is one of the snapshot's `actions`, or `submit` when it has a `form`; which
# ones are on offer is a question about the session, so an action that is not is a
# refusal (`action_not_offered`) and not a malformed frame.
SESSION_ACT_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_ACT,
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("client_id"): CLIENT_ID,
    vol.Required("revision"): REVISION,
    vol.Required("action"): str,
    vol.Optional("value"): SESSION_VALUE,
}

SESSION_STOP_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_STOP,
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("client_id"): CLIENT_ID,
}

SESSION_LEAVE_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_LEAVE,
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("client_id"): CLIENT_ID,
}

# `session_id` may be left out, and then the gateway's session is meant, whichever it
# is; with `force: true` it is ended whoever owns it. That pair is the way out that
# always works (SPEC §5.2), and the banner's "Termina".
SESSION_CANCEL_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_CANCEL,
    vol.Required("entry_id"): str,
    vol.Optional("session_id"): str,
    vol.Required("client_id"): CLIENT_ID,
    vol.Optional("force"): bool,
}

SESSION_SAVE_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_SAVE,
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("client_id"): CLIENT_ID,
    vol.Required("revision"): REVISION,
    vol.Required("target"): vol.In(SESSION_SAVE_TARGETS),
}

SESSION_END_OTHER_SCHEMA: VolDictType = {
    vol.Required("type"): WS_TYPE_SESSION_END_OTHER,
    vol.Required("entry_id"): str,
}

# --------------------------------------------------------------------- the answers
SESSION_GET_KEYS: tuple[str, ...] = ("session", "capabilities")
# `start`, `attach`, `act`, `stop` and `leave`. `leave` is the one that may answer
# `session: null`: it is sent as a page goes away, so a session that no longer exists is
# not worth a refusal there - it answers "nothing to leave" instead of `unknown_session`.
SESSION_ANSWER_KEYS: tuple[str, ...] = ("session",)
SESSION_HEARTBEAT_KEYS: tuple[str, ...] = ("owner", "present_until")
SESSION_CANCEL_KEYS: tuple[str, ...] = ("session", "already_ended")
SESSION_SAVE_KEYS: tuple[str, ...] = ("session", "overview")
SESSION_END_OTHER_KEYS: tuple[str, ...] = ("flows_aborted", "still_calibrating", "overview")

# The snapshot: a whole object at every transition, never a delta. Every key is always
# present; what does not apply is `null` (or `[]`, `{}` where the key is a collection).
SESSION_KEYS: tuple[str, ...] = (
    "session_id",
    "entry_id",
    # Grows by one at every transition and at nothing else (never at a heartbeat).
    "revision",
    # When this snapshot was built, by the one clock that measures anything.
    "server_time",
    "cover",
    "state",
    "substate",
    # The dialog step id, `null` in `saved` and `ended`.
    "step",
    "path",
    # The correction's scope, once chosen.
    "scope",
    # The profile chosen on `path_b` / `path_c` (or named by `start`), `null` otherwise.
    "profile",
    "level",
    # The dialog's plan, as stage names (`SESSION_PLAN_STAGES`), and where on it the
    # session stands. `[]` / `null` before a path is chosen and after a cancellation.
    "plan",
    "plan_index",
    # `{scope}` when `start` named a scope, for the screen to highlight.
    "intent",
    "actions",
    "form",
    # The raw values the step's texts substitute - numbers as numbers, formatted by the
    # panel - under the dialog's own placeholder names.
    "placeholders",
    "movement",
    "press",
    "reading",
    "measured",
    "fit",
    "check",
    "review",
    "problem",
    "notice",
    "position_known",
    "external_move",
    "owner",
    "idle_expires_at",
    "outcome",
)

SESSION_COVER_KEYS: tuple[str, ...] = ("unique_id", "entity_id", "name")
SESSION_INTENT_KEYS: tuple[str, ...] = ("scope",)
SESSION_FORM_KEYS: tuple[str, ...] = (
    "field",
    "kind",
    "optional",
    "unit",
    # What the field opens on: a number, a name, or the profile preselected.
    "suggested",
    "min",
    "max",
    # The profiles to choose from, sorted, for `kind: "choice"`; `null` otherwise.
    "choices",
    "error",
)
SESSION_MOVEMENT_KEYS: tuple[str, ...] = (
    "kind",
    "direction",
    "progress_action",
    # The motion anchor: the actuator's echo, or the frame written plus its start delay
    # when it has none. `null` while the motor is starting.
    "started_at",
    # How long the model expects the movement to take, for a progress bar and nothing
    # else: a measurement never reads it.
    "planned_s",
)
SESSION_PRESS_KEYS: tuple[str, ...] = ("kind", "expires_at")
SESSION_READING_KEYS: tuple[str, ...] = (
    "direction",
    "fraction",
    "from_end_stop",
    "expected_cm",
    "tolerance_cm",
)
SESSION_MEASURED_KEYS: tuple[str, ...] = (
    "travel_cm",
    # True when this session read the travel with a tape; false for one it only knows.
    "travel_measured",
    "opening_time_s",
    "closing_time_s",
    "slat_time_s",
    "lift",
    # `[[motor_s, measured_cm], ...]`, in the order they were read.
    "descent",
    "ascent",
    # True for `points_only`, whose run times are the ones the cover already moves on.
    "times_adopted",
)
# The lift-off press: when it reached the backend, when the stop it asked for was
# written, the gap the tape found (if one was read) and whether the gateway held the
# stop back. `measured.lift` is `null` until the press has arrived.
SESSION_LIFT_KEYS: tuple[str, ...] = ("pressed_at", "stop_written_at", "gap_cm", "late")
SESSION_FIT_KEYS: tuple[str, ...] = ("opening", "closing")
SESSION_FIT_DIRECTION_KEYS: tuple[str, ...] = (
    "run_time_s",
    "slat_time_s",
    "roll",
    "time_scale",
    "points",
)
SESSION_FIT_POINT_KEYS: tuple[str, ...] = ("motor_s", "measured_cm", "residual_cm")
SESSION_CHECK_KEYS: tuple[str, ...] = (
    "fraction",
    "predicted_cm",
    "measured_cm",
    "gap_cm",
    "threshold_cm",
    # How the profile being checked was itself measured - a level and the gap of its own
    # check - shown beside the gap so that 3 cm can be read against it (SPEC §2.2).
    "profile_level",
    "profile_check_cm",
)
SESSION_REVIEW_KEYS: tuple[str, ...] = (
    "variant",
    # The exits offered, the first being the main one (`SESSION_SAVE_TARGETS`).
    "targets",
    "profile_name",
    "profile_exists",
    # `"file"` when `cover_profiles:` defines the same name, `null` otherwise.
    "name_clash",
    "rows",
    "side_effects",
    "affected",
    "accuracy_cm",
    "check_fraction",
    "replacing",
    "keeping",
    "yaml",
)
SESSION_REVIEW_ROW_FIELDS: tuple[str, ...] = ("key", "before", "after")
SESSION_REVIEW_AFFECTED_KEYS: tuple[str, ...] = ("cover_unique_id", "name", "rows")
SESSION_PROBLEM_KEYS: tuple[str, ...] = ("code",)
SESSION_OWNER_KEYS: tuple[str, ...] = ("client_id", "present_until")
SESSION_OUTCOME_KEYS: tuple[str, ...] = ("reason", "profile", "origin", "source")

# ------------------------------------------------------- the session in the overview
# What `overview.session` will carry: the one line the panel's banner and its
# first-run screen need about the session running on this gateway, or `null`.
#
# It is declared here and **not** added to `OVERVIEW_KEYS` yet, on purpose: the key is
# part of the overview the moment the server sends it, and the server sends it from the
# lot that builds the session (B3), whose test regenerates `panel_overview_example.json`
# with it. Declaring the shape now is what stops that from being a change to the frozen
# contract: B3 adds `"session"` to `OVERVIEW_KEYS` and produces exactly these five keys.
#
# `measuring` (already there) says *that* a shutter of this gateway is being measured,
# whoever is measuring it; `session` says *who*: `measuring` set with `session` at `null`
# is the guided dialog or the 0.4.2 action, and the panel offers to close the dialog
# rather than to resume a session it does not have.
SESSION_OVERVIEW_KEYS: tuple[str, ...] = (
    "session_id",
    "cover_unique_id",
    "name",
    # One of `SESSION_STATES`.
    "state",
    # The owner's `client_id`, or `null` when the session has no owner: a panel comparing
    # it with its own tells "my session" from "somebody else's" without asking.
    "owner",
)


# ---------------------------------------------------------------------- refusals
# The refusals the session adds (SPEC §4.6), kept **out of** `WS_ERROR_KEYS`: that tuple
# is what `tests/test_translations.py` holds to having a sentence in **every** language,
# and these have one in English and Italian only - the panel is written in two languages
# (the decision of 14 September) and a translation lot before the release fills the other
# five. They stay a tuple of their own for that reason rather than being folded in by lot
# B3, which wrote their sentences: `refusal_keys()` reads both tuples, and the tolerance
# for the five languages is stated over this one.
# The session also answers with keys that already exist: `unknown_entry`,
# `entry_not_loaded`, `unknown_cover`, `advanced_cover`, `unknown_profile`,
# `invalid_name` and `write_in_progress`.
ERROR_ALREADY_CALIBRATING = "already_calibrating"
ERROR_COVER_UNAVAILABLE = "cover_unavailable"
ERROR_UNKNOWN_SESSION = "unknown_session"
ERROR_SESSION_ENDED = "session_ended"
ERROR_SESSION_OWNED = "session_owned"
ERROR_REVISION_CONFLICT = "revision_conflict"
ERROR_ACTION_NOT_OFFERED = "action_not_offered"
ERROR_NOT_IN_REVIEW = "not_in_review"

SESSION_ERROR_KEYS: tuple[str, ...] = (
    ERROR_ALREADY_CALIBRATING,
    ERROR_COVER_UNAVAILABLE,
    ERROR_UNKNOWN_SESSION,
    ERROR_SESSION_ENDED,
    ERROR_SESSION_OWNED,
    ERROR_REVISION_CONFLICT,
    ERROR_ACTION_NOT_OFFERED,
    ERROR_NOT_IN_REVIEW,
)


__all__ = [
    "ASSIGNMENT_SCHEMA",
    "ASSIGN_KEYS",
    "ASSIGN_SCHEMA",
    "CLIENT_ID",
    "COVER_DETAIL_FORGET_KEYS",
    "COVER_DETAIL_KEYS",
    "COVER_DETAIL_KEY_KEYS",
    "COVER_DETAIL_SCHEMA",
    "COVER_EDIT_KEYS",
    "COVER_EDIT_SCHEMA",
    "COVER_FORGET_KEYS",
    "COVER_FORGET_SCHEMA",
    "COVER_KEYS",
    "ERROR_ACTION_NOT_OFFERED",
    "ERROR_ADVANCED_COVER",
    "ERROR_ALREADY_CALIBRATING",
    "ERROR_BUSY_CALIBRATING",
    "ERROR_COVER_UNAVAILABLE",
    "ERROR_ENTRY_NOT_LOADED",
    "ERROR_MISSING_TRAVEL",
    "ERROR_NAME_IN_USE",
    "ERROR_NOT_IN_REVIEW",
    "ERROR_PROFILE_NOT_EDITABLE",
    "ERROR_REVISION_CONFLICT",
    "ERROR_SESSION_ENDED",
    "ERROR_SESSION_OWNED",
    "ERROR_UNDO_EXPIRED",
    "ERROR_UNKNOWN_COVER",
    "ERROR_UNKNOWN_ENTRY",
    "ERROR_UNKNOWN_PROFILE",
    "ERROR_UNKNOWN_SESSION",
    "ERROR_WRITE_IN_PROGRESS",
    "MEASURABLE_KEYS",
    "NUMBER",
    "ORDER",
    "OVERVIEW_KEYS",
    "OVERVIEW_SCHEMA",
    "PREVIEW_ITEM_KEYS",
    "PREVIEW_KEYS",
    "PREVIEW_SCHEMA",
    "PROFILE_DELETE_KEYS",
    "PROFILE_DELETE_SCHEMA",
    "PROFILE_EDIT_KEYS",
    "PROFILE_EDIT_SCHEMA",
    "PROFILE_KEYS",
    "PROFILE_RENAME_KEYS",
    "PROFILE_RENAME_SCHEMA",
    "PROFILE_VALUES_SCHEMA",
    "REORDER_KEYS",
    "REORDER_SCHEMA",
    "REVISION",
    "SESSION_ACTIONS",
    "SESSION_ACT_SCHEMA",
    "SESSION_ANSWER_KEYS",
    "SESSION_ATTACH_SCHEMA",
    "SESSION_BOUNDARY_NAMES",
    "SESSION_CANCEL_KEYS",
    "SESSION_CANCEL_SCHEMA",
    "SESSION_CAPABILITIES",
    "SESSION_CHECK_KEYS",
    "SESSION_COVER_KEYS",
    "SESSION_DIRECTIONS",
    "SESSION_END_OTHER_KEYS",
    "SESSION_END_OTHER_SCHEMA",
    "SESSION_ERROR_KEYS",
    "SESSION_FIT_DIRECTION_KEYS",
    "SESSION_FIT_KEYS",
    "SESSION_FIT_POINT_KEYS",
    "SESSION_FORM_ERRORS",
    "SESSION_FORM_FIELDS",
    "SESSION_FORM_KEYS",
    "SESSION_FORM_KINDS",
    "SESSION_FORM_UNITS",
    "SESSION_GET_KEYS",
    "SESSION_GET_SCHEMA",
    "SESSION_HEARTBEAT_KEYS",
    "SESSION_HEARTBEAT_SCHEMA",
    "SESSION_HOLDERS",
    "SESSION_INTENT_KEYS",
    "SESSION_KEYS",
    "SESSION_LEAVE_SCHEMA",
    "SESSION_LEVELS",
    "SESSION_LIFT_KEYS",
    "SESSION_MEASURED_KEYS",
    "SESSION_MOVEMENT_KEYS",
    "SESSION_MOVEMENT_KINDS",
    "SESSION_NOTICES",
    "SESSION_OUTCOMES",
    "SESSION_OUTCOME_KEYS",
    "SESSION_OVERVIEW_KEYS",
    "SESSION_OWNER_KEYS",
    "SESSION_PATHS",
    "SESSION_PLAN_STAGES",
    "SESSION_POSITIONS",
    "SESSION_PRESS_KEYS",
    "SESSION_PRESS_KINDS",
    "SESSION_PROBLEMS",
    "SESSION_PROBLEM_KEYS",
    "SESSION_PROGRESS_ACTIONS",
    "SESSION_READING_KEYS",
    "SESSION_REUSED_STEPS",
    "SESSION_REVIEW_AFFECTED_KEYS",
    "SESSION_REVIEW_KEYS",
    "SESSION_REVIEW_ROW_FIELDS",
    "SESSION_REVIEW_ROW_KEYS",
    "SESSION_REVIEW_VARIANTS",
    "SESSION_SAVE_KEYS",
    "SESSION_SAVE_SCHEMA",
    "SESSION_SAVE_TARGETS",
    "SESSION_SCOPES",
    "SESSION_START_SCHEMA",
    "SESSION_STATES",
    "SESSION_STEPS",
    "SESSION_STOP_SCHEMA",
    "SESSION_SUBMIT",
    "SESSION_SUBSTATES",
    "SESSION_VALUE",
    "SESSION_VALUE_KEYS",
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
    "WS_EVENT_SESSION",
    "WS_EVENT_TYPES",
    "WS_READ_COMMANDS",
    "WS_SESSION_COMMANDS",
    "WS_TYPE_ASSIGN",
    "WS_TYPE_COVER_DETAIL",
    "WS_TYPE_COVER_EDIT",
    "WS_TYPE_COVER_FORGET",
    "WS_TYPE_OVERVIEW",
    "WS_TYPE_PREVIEW",
    "WS_TYPE_PROFILE_DELETE",
    "WS_TYPE_PROFILE_EDIT",
    "WS_TYPE_PROFILE_RENAME",
    "WS_TYPE_REORDER",
    "WS_TYPE_SESSION_ACT",
    "WS_TYPE_SESSION_ATTACH",
    "WS_TYPE_SESSION_CANCEL",
    "WS_TYPE_SESSION_END_OTHER",
    "WS_TYPE_SESSION_GET",
    "WS_TYPE_SESSION_HEARTBEAT",
    "WS_TYPE_SESSION_LEAVE",
    "WS_TYPE_SESSION_SAVE",
    "WS_TYPE_SESSION_START",
    "WS_TYPE_SESSION_STOP",
    "WS_TYPE_SET_TRAVEL",
    "WS_TYPE_SUBSCRIBE",
    "WS_TYPE_TEXTS",
    "WS_TYPE_UNDO",
    "WS_WRITE_COMMANDS",
]
