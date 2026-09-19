# The panel's WebSocket API

This is the reference for the WebSocket commands behind the
[Profiles and covers panel](panel.md) — every `myhome/calibration/*` command, its
payload, its answer and its refusals. It is admin-only and internal to the panel:
nothing here is a public integration API, and its shape can change between releases
without notice. See [Profiles and covers panel](panel.md) for what the screen built
on it actually does.

## Contents

- [1. General rules](#1-general-rules)
- [2. `myhome/calibration/overview`](#2-myhomecalibrationoverview)
- [3. `myhome/calibration/cover_detail`](#3-myhomecalibrationcover_detail)
- [4. `myhome/calibration/texts`](#4-myhomecalibrationtexts)
- [5. Errors](#5-errors)
- [6. A worked example](#6-a-worked-example)
- [7. General rules for writes](#7-general-rules-for-writes)
- [8. The write commands](#8-the-write-commands)
- [9. `myhome/calibration/subscribe`](#9-myhomecalibrationsubscribe)
- [10. `myhome/calibration/preview`](#10-myhomecalibrationpreview)
- [11. The calibration session](#11-the-calibration-session)
- [12. The session snapshot](#12-the-session-snapshot)
- [13. Refusals of the session](#13-refusals-of-the-session)
- [14. The session and the published contract](#14-the-session-and-the-published-contract)

---

## 1. General rules

* **Admin only.** Every command carries `@websocket_api.require_admin`. A non-admin
  gets `unauthorized` from the decorator, before the handler runs. A shutter's travel
  model is a setting, not a state: somebody who may open a cover has no business
  rewriting what "open" means. The reads sit behind the same door as the writes
  because the panel itself is admin-only.
* **Nothing is localised, formatted or rounded.** Tokens travel (`origin`, `source`,
  `level`, the per-key `origin`); the panel turns them into sentences with
  `myhome/calibration/texts`. A WebSocket answer has no user in it, and the language
  belongs to the user.
* **Numbers are JSON numbers or `null`.** Dates are ISO-8601 as they were stored (UTC).
* **The client replaces its model; it never merges.** `overview` is built whole on
  every read. A client that merges server pushes into a model it also edits
  eventually shows a shutter following a profile the server deleted.
* **Advanced covers do not exist here.** They report their own position, so there is
  no travel model to show or correct, and every calibration primitive refuses them.
  They are absent from `overview` and are a *refusal* (`not_supported`) rather than
  an absence in `cover_detail`.
* **One resolution.** Every number and every origin comes from `resolve_cover_config`
  — the same call the cover entity makes in its own constructor. The panel never
  re-derives an origin or rescales a profile itself.

---

## 2. `myhome/calibration/overview`

```jsonc
{"type": "myhome/calibration/overview", "entry_id": "01J…"}   // entry_id optional
```

`entry_id` omitted means "the first loaded MyHOME gateway", which is what nearly every
installation has. A house with two reads `entries` in the answer and then asks again by
id. There is no "every entry at once" form: the payload is about one gateway, and a
panel showing two at a time would have to merge two orders.

### Answer

| Key | Type | Notes |
|---|---|---|
| `entries` | array | `{entry_id, title, mac, loaded}` for **every** configured gateway, loaded or not. Present even when there is one, so the picker has one rule. |
| `entry_id` | string | the gateway this payload is about |
| `measuring` | object \| null | `{cover_unique_id, name}` while a guided calibration is running on one of this gateway's shutters. The panel's read-only lock hangs off it, which is why it names the window rather than being a boolean. |
| `session` | object \| null | `{session_id, cover_unique_id, name, state, owner}` for the panel's own calibration session on this gateway, `null` when there is none. `state` is a token of §12.1 and `owner` the owner's `client_id` (`null` when nobody owns it). `measuring` says *that* a shutter is being measured, whoever is measuring it; `session` says *who*: `measuring` set with `session` at `null` is the guided dialog or the 0.4.2 action, and the panel offers to close that dialog (§11.2, `end_other`) rather than to resume a session it does not have. |
| `profiles` | array | §2.1 |
| `covers` | array | §2.2, **already in the order the user put them in** |
| `order` | array of string | the stored order verbatim — unique ids, some of which may name nothing any more. The panel sends this list back, whole, when it reorders. |
| `no_basic_covers` | bool | true for a gateway whose covers are all advanced. Not an error and not an empty list to be styled: the panel says it once. |

### 2.1 `profiles[]`

Sorted by name. Contains **every** name that is defined *or* followed, so a profile a
cover follows and nobody defines any more gets a row of its own rather than vanishing
from a list the user is reading to find out what their shutters are doing.

| Key | Type | Notes |
|---|---|---|
| `name` | string | |
| `source` | `"store"` \| `"yaml"` \| null | where the numbers are written. `null` only when `missing` is true. |
| `editable` | bool | true only for `"store"`. A `cover_profiles:` block belongs to a file this integration has never written and is not about to start writing. |
| `values` | object | the five: `opening_time`, `closing_time`, `slat_time`, `opening_roll`, `closing_roll`. `{}` when `missing`. `roll` is deliberately absent — it is the fallback of the two directional coefficients and never what a calibrated shutter runs on. |
| `reference_height` | number \| null | cm |
| `measured_on` | string \| null | unique id of the window it was measured on. `null` for every profile stored before 0.6.0 and every one written by hand; nothing guesses. |
| `measured_on_name` | string \| null | the name that window has **now**, or `null` when the id names a shutter this gateway no longer has |
| `measured_at` | string \| null | ISO-8601 |
| `followers` | array of unique id | follow it because somebody said so on this installation |
| `followers_from_file` | array of unique id | follow it because `myhome.yaml` says so. Two lists, because a deletion reaches the two differently and the confirmation has to say so. |
| `missing` | bool | true for a name that is followed and not defined |

### 2.2 `covers[]`

| Key | Type | Notes |
|---|---|---|
| `unique_id` | string | `"<mac>-<who>-<where>"` |
| `entity_id` | string \| null | `null` while the entity is not registered |
| `name` | string | |
| `area_id`, `area` | string \| null | resolved **server-side** from the entity registry, falling back to the device's. Either may be `null` and nothing groups, filters or sorts on them being present. |
| `height` | number \| null | this window's own travel in cm |
| `profile` | string \| null | |
| `profile_from_file` | bool | true when the profile comes from the cover's `profile:` line rather than from an assignment made here |
| `profile_missing` | bool | true when that profile is not defined any more: the shutter has silently fallen back to its own configuration, and the panel must not be silent about it |
| `origin` | token | one of `measured` / `inherited` / `adjusted` / `from_the_file` / `defaults`. Rendered through `selector.calibration_origin.options.*`, which carries `{profile}`. |
| `source` | string | the exact `Calibration source` attribute of the entity, character for character |
| `values` | object | the travel model the shutter really runs on, by key: `opening_time`, `closing_time`, `slat_time`, `roll`, `opening_roll`, `closing_roll`, `stop_latency`, `start_delay` |
| `has_own` | array of key | which of those were measured on **this** window |
| `level` | `"basic"` \| `"precise"` \| null | how thorough the guided calibration was, from its `raw` block. `null` for a record with no `raw`; the screen leaves the line out rather than guessing. |
| `verify_note` | number \| null | the tape check's deviation in cm, from the same block |
| `measured_at` | string \| null | of the *record*, not of the profile |
| `calibrating` | bool | |
| `order_index` | int | position in `covers` |

---

## 3. `myhome/calibration/cover_detail`

```jsonc
{"type": "myhome/calibration/cover_detail", "entry_id": "01J…", "cover_unique_id": "aa:bb:…-2-81"}
```

Both required.

### Answer

```jsonc
{"entry_id": "01J…", "cover": { …exactly a covers[] row… }, "keys": [ … ],
 "forget": {"falls_back_to": "profile", "profile": "tall", "travel_stays": true}}
```

`forget` is **what removing the measurement would leave**, read before it removes
anything: the same three facts the `cover_forget` command answers with afterwards,
computed the same way — resolve this window once more with the record gone.

| Key | Type | Notes |
|---|---|---|
| `falls_back_to` | `"profile"` \| `"file"` \| `"defaults"` | |
| `profile` | string \| null | the name, when a profile is what is left. Only `myhome.yaml`'s own `profile:` line survives the removal: an assignment made in this panel lives in the record and goes with it. |
| `travel_stays` | bool | `myhome.yaml`'s own `height:` survives; a travel somebody typed into this panel does not, and then no profile can be brought to the window at all. |

`keys[].inherited_*` is **not** the answer to that question and must not be used for
it: it takes this window's *overrides* away and leaves the record — which is right
for the empty field and its "inherits N" placeholder, and wrong for a removal that
takes the assignment and the travel too.

`keys[]`, one entry per key of `values`, in the model's own order:

| Key | Type | Notes |
|---|---|---|
| `key` | string | |
| `value` | number | what the shutter runs on today |
| `origin` | `own` \| `profile` \| `file` \| `default` | which of the four said it |
| `own` | bool | `origin == "own"`, spelled out because the screen asks it constantly |
| `inherited_value` | number \| null | **what this key would fall back to if this window's own measurement of it were removed.** The "inherits N" placeholder under an empty field, and the destination the removal confirmation names before it removes anything. Computed by running the same precedence loop a second time with the overrides taken away — not by a second rule. |
| `inherited_origin` | token \| null | and where *that* comes from |
| `profile_value` | number \| null | the profile scaled to this window, whether or not it is the one in use: what an impact preview compares against. `null` when the cover follows no profile. |
| `file_value` | number \| null | what `myhome.yaml` really writes for this cover, and only that. `null` for a key the file leaves out, however completely the validator filled it in. |
| `default_value` | number \| null | what the validator resolved where the file says nothing — this integration's own default. `null` where the file **does** write the key, because the default is then not visible from here. |

**Note on `stop_latency` / `start_delay`.** A stored profile carries them (filled with
the installation defaults by `profile_as_config`), so for a window that follows a
profile their `origin` is `profile` and not `default`. That is what the shutter is
running on, reported as it is rather than as it ought to be.

---

## 4. `myhome/calibration/texts`

```jsonc
{"type": "myhome/calibration/texts", "language": "it-CH"}   // language optional
```

Omitted, `language` is `hass.config.language` — the *server's*. The panel passes the
**user's**, which can differ.

### Answer

| Key | Type | Notes |
|---|---|---|
| `language` | string | the language actually served, after the fallback chain |
| `requested` | string | what was asked for |
| `fallback` | bool | the two differ |
| `texts` | object | four blocks of that language's file: `options`, `selector`, `exceptions` and `panel` (the file's `config_panel` block, renamed). Each block is merged key by key over English, so a key the language lacks carries the English text |

Fallback chain, resolved on the server because the browser cannot know which
translation files exist: the exact tag, then its primary subtag (`it-CH` → `it`,
`pt_BR` → `pt`), then `en`. A key that is not there renders as the key — visible in a
screenshot and impossible to mistake for a deliberate phrase.

Cached per language per Home Assistant run, read in an executor.

**No text is ever baked into the bundle.**

---

## 5. Errors

Every refusal carries `translation_domain="myhome"` and an English `message`
alongside the key, so a client is never left with a bare token.

| Situation | Code | `translation_key` |
|---|---|---|
| Not an admin | `unauthorized` | — (raised by the decorator) |
| Bad payload | `invalid_format` | — (schema validation) |
| No such config entry, or none loaded at all | `not_found` | `unknown_entry` |
| The gateway exists but is not loaded | `not_found` | `entry_not_loaded` |
| No such basic cover on that gateway | `not_found` | `unknown_cover` |
| An advanced shutter | `not_supported` | `advanced_cover` |

"Not loaded" is a different sentence from "not found" on purpose: the shutters are not
there to be read, which asks the user to do something about the gateway rather than
about the id they typed.

---

## 6. A worked example

This is a real `overview` answer, taken from the test suite's fixtures:

* two basic shutters and one advanced one (absent from the payload);
* `Hallway Shutter` writes its own run times in `myhome.yaml`, follows the stored
  profile `tall` and has measured two numbers of its own over it → `origin:
  "adjusted"`, `source: "profile tall, adjusted"`, `has_own: ["opening_time",
  "slat_time"]`, `level: "precise"`, `verify_note: 1.5`, area `Kitchen`;
* `Landing Shutter` only follows `tall`, at a different travel → `origin:
  "inherited"`, every number scaled, `has_own: []`, no area;
* two profiles: `tall` (stored, editable, with provenance) and `from_the_file` (from
  `cover_profiles:`, not editable, no provenance, no followers);
* the stored order is the reverse of the file's, and `order_index` follows it.

---

## 7. General rules for writes

* **`entry_id` is required.** Optional on the reads, where leaving it out means "the
  one gateway I have" and a panel opening for the first time asks what there is;
  required here, because a change applied to whichever gateway happened to be first
  in the list is not a thing anybody asked for.
* **Admin only**, like the reads, and for the stronger reason: a shutter's travel
  model is a setting.
* **Refused while a measurement is running.** Any basic cover of the entry with
  `calibrating` true and the whole gateway is read-only: `not_allowed` /
  `busy_calibrating`, with the window's name in `translation_placeholders["cover"]`.
  It applies to *every* write and not only the ones that name that window, because
  the guided calibration will store a profile when it is done and what that profile
  is worth depends on the assignments it finds. The panel is told before it tries —
  `overview.measuring`, and the `measuring` event of §9 — so this is a backstop and
  not the user interface.
* **One write at a time.** A write that arrives while another is being applied to the
  same gateway is *refused*, not queued: `not_allowed` / `write_in_progress`. Two
  writes are not independent — each reads the store, decides against what it read,
  and writes the whole of what it decided.
* **Every write answers with a fresh `overview`**, of exactly the shape §2 describes,
  and pushes the same payload to every subscriber (§9). The client replaces its
  model; it never merges.
* **Every write answers with an `undo_token`** — an opaque hex that takes exactly
  that write back, or `null` when the write changed nothing at all (§8.9).
* **No write reloads the config entry.** A write publishes a signal and every cover
  of that gateway re-runs `resolve_cover_config` against the file as written plus the
  store as it now is, and swaps its numbers in place. A movement already in flight
  keeps the model it started with and picks the new one up when it ends; everything
  else — the attributes, the `Calibration source`, the next movement — changes at
  once. There is no window of unavailability, and no third event covering one.
* **Atomic per call.** A command validates everything it was given before it writes
  anything: a batch half applied is a screen that has to explain which half.

---

## 8. The write commands

Payload keys not listed are refused by the schema (`invalid_format`). Every number
may arrive as a JSON number **or as a string**: the parser reads both and accepts a
comma for a decimal point, because a window measured as `85,5` in Italian is a
window. The ranges are the guided dialog's own constants and are not restated in this
layer.

### 8.1 `myhome/calibration/assign`

```jsonc
{"type": "myhome/calibration/assign", "entry_id": "01J…",
 "assignments": [{"cover_unique_id": "aa:bb:…-2-81", "profile": "tall", "height": 180}],
 "order": ["aa:bb:…-2-82", "aa:bb:…-2-81"]}          // optional
```

Assignment **and** position in one write, because on the screen they are one gesture.
`profile: null` takes the cover out of its profile; what the window keeps is what was
measured on *it* — its overrides and its travel, which are statements about that
window and not about which kind of shutter it is.

`height` is this window's travel and is here because a profile cannot be scaled onto a
window whose travel nobody knows. It is the same write `set_travel` makes on its own,
carried in the batch, which is what the review panel's missing-travels form collects.

`order` is the **whole gateway's** resulting order. Left out, every shutter that
changed group is spliced in after the last member the group it joined already has —
the end of the target group, which is what assigning without a drop position means.

Answer: `{overview, undo_token, applied}`. `applied` counts the items that really
changed something, so a row the user did not touch is not counted.

Refusals, all `service_validation_error` and all applying to the batch as a whole: the
`translation_key` is the first kind of problem found (`missing_travel` first when it is
there at all, because it is the one with a form behind it), the English `message` names
every offending item as `"<unique_id>: <key>"`, and `translation_placeholders` carry
`covers` (the ids that hit that first kind) and `count`. The kinds are `unknown_cover`,
`advanced_cover`, `unknown_profile`, `missing_travel`, `out_of_range`, `not_a_number`.

### 8.2 `myhome/calibration/reorder`

```jsonc
{"type": "myhome/calibration/reorder", "entry_id": "01J…",
 "order": ["aa:bb:…-2-81", "aa:bb:…-2-82"],
 "profile": "tall"}                                  // optional, may be null
```

Two shapes, for the panel's two gestures.

* **`profile` absent** — `order` is the whole gateway's order and replaces the stored
  one. This is `overview.order` sent back whole.
* **`profile` present** (`null` means "no profile") — `order` is that one group's
  full order. Its members go back into the places that group already holds in the
  one flat stored list, so the other groups do not move at all. An id in the list
  that does not follow that profile is `service_validation_error` / `unknown_cover`.

The full list either way and never a move: a move has to be applied to the state the
client last saw, and the client's idea of that state is the thing these commands
exist not to trust. Ids naming no cover of this gateway are dropped rather than
stored — a browser tab left open across a reconfiguration is not a client bug — but
an id named **twice** is one, and is refused by the schema (`invalid_format`) rather
than quietly deduplicated: a deduplicated list is a stored order different from the
one on the screen, with nothing saying so. The same applies to `assign`'s optional
`order`.

A group list **shorter** than the group is not refused, because there is a safe answer
to it: the members it leaves out keep their places at the end of that group rather than
falling out of the stored order altogether.

Answer: `{overview, undo_token}`.

### 8.3 `myhome/calibration/set_travel`

```jsonc
{"type": "myhome/calibration/set_travel", "entry_id": "01J…",
 "cover_unique_id": "aa:bb:…-2-82", "height": 165}   // `null` removes it
```

The one number every scaled profile depends on. `null` takes it out of the record and
the window goes back to whatever its own configuration says — which may be nothing, and
then no profile can be scaled onto it. Range 20-500 cm → `out_of_range`.

Answer: `{overview, undo_token}`.

### 8.4 `myhome/calibration/cover_edit`

```jsonc
{"type": "myhome/calibration/cover_edit", "entry_id": "01J…",
 "cover_unique_id": "aa:bb:…-2-81",
 "overrides": {"opening_time": 26.5, "slat_time": null},
 "height": 195}                                      // optional, may be null
```

`overrides` is a **patch**, not a form submitted whole: a key with a number is set, a
key with `null` is removed and the window inherits again (the empty field and its
"inherits N" placeholder), and a key the message does not mention is not touched. So
correcting one number is one number.

Only the five a window can have measured on it: `opening_time`, `closing_time`,
`slat_time`, `opening_roll`, `closing_roll`. Anything else is `invalid_format`, naming
the key, rather than a value stored and never read. Bounds: times 1-600 s, slat 0-60 s,
rolls 1-5 → `out_of_range` / `not_a_number`.

`height` behaves as in `set_travel` and is left alone when the key is absent.

The profile and its precedence are carried over untouched: correcting a number by hand
says nothing about which kind of shutter this is. A record left saying nothing at all —
every override cleared and no travel — is **deleted**, as the dialog's own hand edit
deletes it.

Answer: `{overview, undo_token}`.

### 8.5 `myhome/calibration/cover_forget`

```jsonc
{"type": "myhome/calibration/cover_forget", "entry_id": "01J…", "cover_unique_id": "…"}
```

The whole record, assignment included.

Answer: `{overview, undo_token, falls_back_to, profile}`. `falls_back_to` is
`"profile"` / `"file"` / `"defaults"`, and `profile` the name when there is one. Both are
read by **resolving the window again with the record gone**, not predicted from a rule,
so the sentence the panel shows and the numbers the shutter runs on are one answer.

### 8.6 `myhome/calibration/profile_edit`

```jsonc
{"type": "myhome/calibration/profile_edit", "entry_id": "01J…", "name": "tall",
 "values": {"opening_time": 22.3, "closing_time": 21.7, "slat_time": 4.7,
            "opening_roll": 2.12, "closing_roll": 1.69},
 "reference_height": 195}
```

All five values required, bounds as in §8.4 plus the reference height's own 20-500 cm
range. `measured_at` is re-stamped — the numbers have just been stated — and
`measured_on`, `reference_cover`, `source` and `raw` are carried over untouched: the
window they were measured on is still the window they were measured on.

A follower holds the *name* and not a copy of the numbers, so the edit reaches every one
of them on the next resolution, which is the signal this write ends with.

Answer: `{overview, undo_token, affected}` — every window that follows the name,
however it was told to.

A profile the panel may not write is `not_allowed` / `profile_not_editable` (see
§8.10); a name nobody defines is `not_found` / `unknown_profile`.

### 8.7 `myhome/calibration/profile_rename`

```jsonc
{"type": "myhome/calibration/profile_rename", "entry_id": "01J…",
 "name": "tall", "new_name": "taller"}
```

Three store writes in one awaited sequence, in the order that leaves no gap: the numbers
go in under the new name, every window assigned to the old one is repointed, and only
then is the old name removed.

`new_name` must match `^[A-Za-z0-9_]+$` and is refused if it is the "no profile"
sentinel → `service_validation_error` / `invalid_name`. A name already defined — in the
store or in `cover_profiles:` → `service_validation_error` / `name_in_use`. Renaming to
the same name is a no-op with `moved: 0`.

Answer: `{overview, undo_token, moved, from_file}`. `from_file` names the windows that
follow through their own `profile:` line in `myhome.yaml` and therefore could **not** be
moved: that line is in the user's file and this integration does not write it.

### 8.8 `myhome/calibration/profile_delete`

```jsonc
{"type": "myhome/calibration/profile_delete", "entry_id": "01J…", "name": "tall"}
```

Answer: `{overview, undo_token, covers_affected, from_file}` — the windows whose stored
assignment went with the profile (read *before* the deletion, because the deletion is
what strips it) and the windows whose `profile:` line names it (read after, and unchanged
by this).

Note on `from_file`: the validator refuses a `profile:` line naming a profile
`cover_profiles:` does not define, so a **stored** profile only ever has followers of
that kind through the clash where one name is written in both places and the store's
wins. Deleting the stored one is then exactly the write those windows have to be warned
about, because the file's profile — shadowed until then — comes back and their numbers
change.

### 8.9 `myhome/calibration/undo`

```jsonc
{"type": "myhome/calibration/undo", "entry_id": "01J…", "undo_token": "9f2c…"}
```

One slot per gateway, holding **only the records the last write actually changed**, as
they were before it. Applying it is an ordinary write: it takes the lock, it is refused
while a measurement is running, and it reaches the shutters the same way.

A token is withdrawn by the next write of the same gateway and by the clock after
**5 minutes**, whichever comes first: two writes later, "as they were" is a state that
was never on the screen. A token that is unknown, spent or expired is `not_found` /
`undo_expired`.

Answer: `{overview, undo_token, undone}` with `undo_token: null` — undoing an undo would
be two buttons swapping a gateway back and forth with nothing on the screen saying which
way round it is now. `undone` is the name of the command that was taken back
(`"assign"`, `"profile_edit"`, …).

Because only the changed records are restored, an undo leaves alone whatever else was
written meanwhile — the guided dialog, another screen — instead of putting a whole file
back over the top of it.

### 8.10 Refusals the writes add

| Situation | Code | `translation_key` |
|---|---|---|
| A guided calibration is running on any cover of the gateway | `not_allowed` | `busy_calibrating` (`{cover}`) |
| Another write of the same gateway is being applied | `not_allowed` | `write_in_progress` |
| A `cover_profiles:` profile, which this integration does not write | `not_allowed` | `profile_not_editable` (`{profile}`) |
| No stored profile of that name | `not_found` | `unknown_profile` (`{profile}`) |
| An expired, spent or unknown undo token | `not_found` | `undo_expired` |
| A profile assigned to a window whose travel nobody knows | `service_validation_error` | `missing_travel` (`{covers}`, `{count}`) |
| A name that is not a usable profile name | `service_validation_error` | `invalid_name` (`{profile}`) |
| A name that is already taken | `service_validation_error` | `name_in_use` (`{profile}`) |
| A number outside the dialog's own bounds, or not a number | `service_validation_error` | `out_of_range` / `not_a_number` (`{key}`, `{min}`, `{max}`) |
| A shutter that is not there, or an advanced one | `not_found` / `not_supported` | `unknown_cover` / `advanced_cover` |

`unknown_entry` and `entry_not_loaded` of §5 apply here too. A write that raises a
`HomeAssistantError` becomes `home_assistant_error` with that error's own translation
domain and key — Home Assistant's own connection handling does that, and nothing in
this integration duplicates it.

---

## 9. `myhome/calibration/subscribe`

```jsonc
{"type": "myhome/calibration/subscribe", "entry_id": "01J…"}   // entry_id optional
```

Answers `success` and then pushes events with that subscription's id. Three kinds:

| `type` | Payload | When |
|---|---|---|
| `overview` | `{"type": "overview", "overview": {…§2…}}` | on subscribing, and after every successful write and undo |
| `measuring` | `{"type": "measuring", "cover_unique_id": "…" \| null, "name": "…" \| null}` | whenever a guided calibration takes one of this gateway's shutters or gives it back |
| `session` | `{"type": "session", "session": {…§12…} \| null}` | on subscribing, and after every transition of the gateway's calibration session (§11.4) |

The overview is the whole payload every time and never a patch — a client that merged
server pushes into a model it also edits eventually shows a shutter following a profile
the server deleted. It is what stops two browser tabs on the same twelve shutters from
each seeing half of it.

A write's own answer arrives *after* the push, carrying an identical `overview`.

`measuring` is driven by **state changes** of the gateway's cover entities, reading them
back through the same resolution the overview uses: the guided flow marks the entity
and writes its state, so the flag reaches the panel the moment it reaches everybody
else. It is an object or `null`, not a boolean, because the read-only lock names the
window.

`measuring` says that a shutter is being measured, by the dialog, the 0.4.2 service or
the panel alike; `session` says *which* — a `null` session while `measuring` names a
shutter means the dialog or the service holds it. A client that does not know an event
type ignores it, which is how the third kind was added without breaking the first two.

There is no event covering a reload: a write does not reload the config entry (§7),
so there is no window of unavailability to be honest about.

The subscription dies with the socket — Home Assistant unsubscribes every listener
when the connection closes — and nothing of the subscription outlives it. A calibration
session does, on purpose: it belongs to the gateway and not to the socket (§11.1), and a
client that subscribes again receives it at once.

---

## 10. `myhome/calibration/preview`

```jsonc
{"type": "myhome/calibration/preview", "entry_id": "01J…",
 "items": [{"cover_unique_id": "aa:bb:…-2-81", "profile": "tall", "height": 180}],
 "profile_values": {                                  // optional
   "tall": {"opening_time": 21.0, "closing_time": 20.4, "slat_time": 4.4,
            "opening_roll": 2.1, "closing_roll": 1.7, "reference_height": 195}}}
```

"If these shutters followed these profiles, at these travels, what would they run on?"

The review panel shows a before and an after for every shutter it is about to move, and
the after is what that shutter would really run on — the profile brought to its own
travel, with whatever it measured for itself still above it. Working that out in the
browser would mean a second copy of the resolution logic, and two copies of a travel
model are two answers; the panel is forbidden from having one (§1). So it asks, and the
server answers with the function the shutter runs on.

`items` are **exactly `assign`'s `assignments`** — the same schema object, so the panel
sends the batch it is composing rather than a translation of it. There is no `order`: a
position is not a number a shutter runs on.

`entry_id` is **required**, like a write's and unlike the other reads': a preview is
always about a batch composed on one gateway's screen. Admin-only, like everything else
here. It is a **read**: no lock, no store write, no signal, no `undo_token`, and it is
allowed while a measurement is running, exactly as every other read is.

### `profile_values` — the same question one level up

The profile card's editor asks something no assignment can: "if this profile said these
numbers instead of the ones it has, what would each of its followers run on?" That is
the live impact preview beside the five fields, and the panel may no more scale a
profile for that screen than for the review panel. So the same command takes an
optional override.

```jsonc
"profile_values": {"<name>": {"opening_time":…, "closing_time":…, "slat_time":…,
                              "opening_roll":…, "closing_roll":…, "reference_height":…}}
```

* **Exactly `profile_edit`'s own six numbers**, all required, and refused by the schema
  (`invalid_format`) if one is missing: a half override would be a profile half from the
  form and half from the store, and there is no screen that means that.
* **It replaces numbers; it never defines a name.** A name the gateway does not have is
  not created by it, so an item asking for that name still answers `unknown_profile` —
  the one answer that tells the user their profile has gone stays reachable.
* **A number that cannot be used is a per-item `problem`, not a dead command.** It parses
  with the same lenient number parser (a comma is a decimal point) against the profile
  fields' own bounds; where it fails, the offending profile is not overridden and every
  item whose *resolved* profile is that name carries `not_a_number` or `out_of_range`
  instead of an answer — the same shape a bad `height` already has. The screen it serves
  has five fields being typed into, so a whole answer refused on the first keystroke
  would take the table off the screen exactly while the user was working on it.
* **It writes nothing**, like the rest of the command: the override lives in a copy of
  the merged profile mapping for the length of the call.
* **The overridden profile is built the way the write's is.** For a profile the store
  owns, the six numbers go into a copy of its own record and back out through the same
  path `profile_edit`'s numbers take, so `roll` — which a stored profile does not carry
  and the read side derives from `closing_roll` — is the one the write would produce
  rather than the one the profile had. For a profile only `cover_profiles:` defines, the
  numbers are merged and the file's own `roll:` is left alone: no write from here can
  change it, so there is no write for the answer to agree with.

**How the panel composes the items for it.** One item per follower, carrying that
follower's *current* assignment so that nothing but the numbers changes:
`profile: null` for a window whose `profile_from_file` is true (popping an assignment it
does not have leaves the record as it is, and the file goes on answering), and
`profile: <name>` for one the store assigned. Both rewrite the record into exactly what it
already was, which is what makes the answer an impact preview rather than an assignment
preview.

### Answer

```jsonc
{"entry_id": "01J…", "items": [ … ]}
```

One item out per item in, **in the same order**:

| Key | Type | Notes |
|---|---|---|
| `cover_unique_id` | string | |
| `profile` | string \| null | **the profile the window would really follow afterwards** — `overview`'s own field, read the same way. It is the profile in the question unless `myhome.yaml`'s own `profile:` line answers instead: a window the file assigns cannot be taken out of that profile from here, so an item asking for `null` is answered with the name it goes on following. On an item that carries a `problem` it is the name that was asked about, because nothing was resolved. |
| `height` | number \| null | the travel the answer was worked out at: the one in the question when it carried one, otherwise the one this window was already known to have |
| `problem` | token \| null | the one thing that stops this item, or `null` |
| `origin` | token \| null | what `overview` would say about this shutter afterwards |
| `source` | string \| null | …and the exact `Calibration source` string it would carry |
| `values` | object | the travel model it would run on, by key. `{}` when there is a problem |
| `keys` | array | `{key, value, origin}` per key of `values`, `origin` being `own` / `profile` / `file` / `default` as in §3. `[]` when there is a problem |
| `has_own` | array of key | what would still be measured on this window. An assignment never touches the overrides, so it is what it was |

### It refuses nothing

`assign` refuses a whole batch when one item cannot be written, because a batch half
applied is a screen that has to explain which half. A preview writes nothing, so there
is no half of anything — and a review panel showing eleven answers and one "this one
still needs its travel" is the screen the design asks for. Each item therefore carries
either an answer or the one `translation_key` that stops it.

`problem` is one of six, and every one of them is a key `assign` refuses with, so the
panel renders the same sentence whether the problem was found before the write was
attempted or by the write itself:

| `problem` | When |
|---|---|
| `unknown_cover` | no such shutter on this gateway |
| `advanced_cover` | a shutter that reports its own position |
| `unknown_profile` | no profile of that name, in the store or in the file |
| `missing_travel` | a profile asked for on a window whose travel nobody knows — the state the review panel's form exists to fix |
| `not_a_number` | a `height` that is not one (a comma is a decimal point, as everywhere) |
| `out_of_range` | a `height` outside 20-500 cm |

The whole command only refuses in the ways every read refuses: `unknown_entry`,
`entry_not_loaded`, `invalid_format`, `unauthorized` (§5).

### The parity invariant

The test suite previews a batch, makes it, and compares `values`, `origin`, `source`,
`has_own`, `height` and `profile` item by item against the resulting `overview` — over
a state matrix that includes a fixture whose `myhome.yaml` carries a `profile:` line,
the one state in which `profile` could disagree. That is not "close enough": the
preview rewrites the record exactly as the real write rewrites it and hands the result
to the same resolution the read path uses, so it is the write's own input run through
the read path.

---

## 11. The calibration session

The guided calibration — the measuring itself, until 0.6.0 only in *Configure →
"Calibrate a cover"* — as ten commands, one event and one object, the **snapshot**
(§12). This part of the API is specified ahead of its implementation: the names, the
payloads and the snapshot below are fixed first, so that the server and the panel can be
built against them at the same time, and `tests/test_session_contract.py` holds this
section, `panel_schemas.py`, `panel_src/src/engine/session-contract.ts` and
`tests/fixtures/panel_session_examples.json` to saying the same thing.

### 11.1 General rules

* **The rules of §1 and §7 apply.** Admin only; numbers are JSON numbers; nothing is
  localised or formatted; every refusal carries `translation_domain="myhome"`, a
  `translation_key` and an English `message`. `entry_id` is **required** on every
  session command, reads included: a session is always one gateway's.
* **One session per gateway, owned by the backend.** It lives on the server, not in the
  browser: closing a tab, locking a phone or losing the socket does not end it. A second
  `start` on the same gateway is **refused**, never queued (`already_calibrating`), and
  so is a `start` while any basic cover of the gateway is being calibrated by something
  else (the dialog, the 0.4.2 service) or while the gateway is still **reserved** by a
  session that ended during a free run (§11.6).
* **The backend is the only clock.** A press counts at the instant the `act` message
  reaches the backend, as a press in the dialog counts when its HTTP request arrives. No
  time from the browser enters a measurement, and the protocol has no field for one.
* **Owner and presence.** `client_id` is made by the panel, one per browser tab (kept in
  `sessionStorage`), pattern `^[A-Za-z0-9-]{8,64}$`. The client that starts a session
  owns it. The owner is **present** while its last `heartbeat` or verb is less than
  **45 s** old; the panel sends a heartbeat every **15 s**. Presence decides *who may
  act* and nothing else: when it lapses nothing stops, nothing is cancelled and nothing
  moves — the session simply becomes available to whichever client **acts** next (§11.3).
  A heartbeat is not an act: **it never takes ownership**, however long the owner has
  been away. A second tab left open on the wizard would otherwise become the owner by
  doing nothing, forty-five seconds after the phone in the user's hand went to sleep, and
  the phone would come back read-only in the middle of a tape reading. Ownership changes
  on a verb that does something (`act`, `stop`, `save`, `leave`, `cancel`) or on an
  `attach` — implicitly while the owner is absent, and with `claim: true`, after the
  screen has asked, while the owner is present.
* **The lease is the inactivity timer.** A session with no transition and no verb from
  its owner for **1800 s** on a screen where nothing has moved yet, or **600 s** after
  a movement, ends as `expired`, and a stop is written if the shutter is moving — the
  dialog's own watchdog, with the same two lengths. A **heartbeat does not renew it**:
  a tab forgotten open must not hold a shutter in calibration for ever. The snapshot
  says when it runs out (`idle_expires_at`).
* **`revision`** grows by one at every transition of the session and at nothing else —
  never at a heartbeat, never at a read. `act` and `save` carry the revision the client
  last read and are refused (`revision_conflict`) against any other, with nothing done:
  that is what makes a double tap on a press, or a retry after a reconnection, harmless.
  **`cancel` carries no revision and never can.** Transitions the user did not cause — a
  press timing out, a shutter brought back to its end stop — move the revision on their
  own, and a "Cancel" that answered "somebody moved on, try again" would be exactly the
  silent failure the panel exists to avoid. Cancelling is refused for one reason only
  (another client owns the session), and `force: true` overrides that.
* **A read never moves anything.** `get`, `attach` and the subscription answer with the
  snapshot and stop there. A movement starts only from an `act`, or from the end of the
  previous movement inside the same chain (a homing followed by its run to a fraction).
  A session picked up again shows where it stands; it does not re-enter its step.
* **Nothing is written before `save`.** Every step up to the review moves the shutter
  and nothing else.
* While a session holds a shutter, `calibrating` is true for it (as it is while the
  dialog measures), `overview.measuring` names it and every write of §8 is refused with
  `busy_calibrating` — except the session's own `save`.

### 11.2 The commands

| `type` | Payload, besides `entry_id` | Answer |
|---|---|---|
| `myhome/calibration/session/get` | — | `{session, capabilities}` |
| `myhome/calibration/session/start` | `cover_unique_id`, `client_id`, `path?`, `profile?`, `scope?` | `{session}` |
| `myhome/calibration/session/attach` | `session_id`, `client_id`, `claim?` | `{session}` |
| `myhome/calibration/session/heartbeat` | `session_id`, `client_id` | `{owner, present_until}` |
| `myhome/calibration/session/act` | `session_id`, `client_id`, `revision`, `action`, `value?` | `{session}` |
| `myhome/calibration/session/stop` | `session_id`, `client_id` | `{session}` |
| `myhome/calibration/session/leave` | `session_id`, `client_id` | `{session}` (may be `null`) |
| `myhome/calibration/session/cancel` | `client_id`, `session_id?`, `force?` | `{session, already_ended}` |
| `myhome/calibration/session/save` | `session_id`, `client_id`, `revision`, `target` | `{session, overview}` |
| `myhome/calibration/session/end_other` | — | `{flows_aborted, still_calibrating, overview}` |

Payload keys not listed are refused by the schema (`invalid_format`), as everywhere.

**`get`** answers the gateway's session — live, or terminal while it is still kept
(§11.6) — or `session: null`, and `capabilities`: what this backend offers, because
the contract (§2.5) asks a backend that offers less to say so rather than run a shorter
plan under the same name.

```jsonc
{"model": "roll_nonlinear", "paths": ["path_a", "path_b", "path_c"],
 "levels": ["basic", "thorough"], "scopes": ["times_only", "times_and_rolls", "points_only"],
 "check": true, "fit_residuals": true, "repeat_step": true,
 "save_targets": ["profile", "cover_only"], "bulk": false}
```

**`start`** opens a session on one basic cover and never moves it. It also never skips a
screen that comes before a movement:

| Payload | The session is born on |
|---|---|
| no `path` | `path` — the choice between the three paths |
| `path: "path_a"` | `path_a` — the warning before the first movement |
| `path: "path_b"` (with or without `profile`) | `path_b` — the profile form, preselected when `profile` names one |
| `path: "path_c"` without `profile` | `path_c` — the profile form |
| `path: "path_c"` with `profile` | `refine_scope`, with that profile chosen; `scope`, when given, is only highlighted (`intent`), not chosen |

`path_c` may also carry a `scope` without a `profile`: the session is then born on
`path_c` and the scope waits in `intent` for the screen after it. `profile` belongs to
paths B and C and `scope` to path C: anything else is `invalid_format`, because a start that dropped half of what it was asked would open a
screen other than the one the user pressed a button for. A profile nobody defines is
`unknown_profile`. The panel carries the user's *intention* in its own state and never
in the URL, so reloading the page can never start a session by itself.

```jsonc
{"type": "myhome/calibration/session/start", "entry_id": "01J…",
 "cover_unique_id": "aa:bb:…-2-82", "client_id": "3b0c7e1a-…",
 "path": "path_c", "profile": "tall", "scope": "points_only"}
```

**`attach`** reads the session as a given client. From the owner, or from anyone while
the owner is absent (in which case that client **becomes** the owner), it is the
session; from another client while the owner is present it is the same snapshot, read
only. `claim: true` takes the session from a present owner — the panel asks first
("Take control?"); the old owner's next heartbeat answers `owner: false` and its screen
turns read-only with its own "Take control".

**`heartbeat`** keeps the owner present. It answers `{owner: true, present_until}` to
the owner and `{owner: false, present_until: null}` to any other client — including one
whose session has no owner at all, because a heartbeat never takes ownership (§11.1). It
is never an error, so that losing ownership is a state the panel draws rather than a
failure it reports, and it changes neither `revision` nor the lease.

**`act`** is the conversation, and only ever a way *forward*: `action` is one of the
snapshot's `actions` — the dialog's own `menu_options` ids — or `"submit"` when the
snapshot has a `form`, with the field's content in `value`. The dialog's two ways out are
**not** actions of this API and are never in `actions`: `save` is the `save` command, and
`cancel_flow` is the `cancel` verb, which carries no revision precisely so that it cannot
be refused for concurrency. A screen the dialog gives a "Cancel" to is a screen the panel
closes with its own ✕, and the ✕ is on every screen. A number is sent **as the text that was typed** (`"96,5"`):
the server reads it with the same lenient parser as the dialog, so a decimal comma
survives. A value that cannot be accepted is **not a refusal**: the answer is the same
step again with `form.error` set (`not_a_number`, `out_of_range`, `above_the_travel`,
`invalid_name`), exactly as the dialog shows a field error, because it is the user's
mistake and not the protocol's. An action the step does not offer is refused
(`action_not_offered`), and so are `save` and `cancel_flow`, which are commands.

**The three verbs of the contract**, each with one meaning:

* **`stop`** writes a stop frame at once. It is the only verb that touches the shutter.
  If a movement of the session is under way — a homing, a free run waiting for a press,
  a run to a fraction — the step becomes `problem_interrupted`, because what it was
  measuring no longer holds, and `repeat_step` is offered. With nothing of the
  session's moving, it is a plain stop and the state does not change.
* **`leave`** detaches the client. Nothing is written and a run under way finishes by
  itself. A session that has **measured nothing yet** — `armed`, or `briefing` before
  the first measurement — ends (`ended`, reason `left`); any other stays, without an
  owner, and can be picked up until its lease runs out. It is what closing the window or
  navigating away does. Because it is sent as a page goes away, a session that no longer
  exists answers `{session: null}` rather than `unknown_session`, and a `leave` from a
  client that is not the owner does nothing and answers the snapshot rather than
  `session_owned`: a read-only tab being closed has nothing to leave, and a refusal there
  would be noise on a message nobody is waiting for.
* **`cancel`** discards the provisional values and ends the session (`ended`, reason
  `cancelled`). It does **not** stop the shutter: a run already under way finishes at
  its end stop, as the dialog's "Cancel" does. It carries **no `revision`** and is never
  refused for concurrency, and it is **idempotent**: on a session that has already ended
  it answers that session with `already_ended: true`. Without
  `session_id` it means the gateway's session, whichever it is; with `force: true` it
  ends it **whoever owns it** — the way out that always works, and what the banner's
  "End" sends. With no session at all it answers `{session: null, already_ended: true}`.

**`save`** writes the result, once, and only from `review`. `target` must be one of
`review.targets` (otherwise `action_not_offered`, with the target as `{action}`), and
`revision` the current one. What is written:

| Path | `target` | What is written |
|---|---|---|
| A | `"profile"` (the main exit) | the profile `review.profile_name` — the fitted values, reference travel = the travel measured, `measured_on` = this cover, `raw` — **and** this cover's record: that profile, `profile_wins`, its travel, `raw`, and **no values of its own**. Values it had of its own are removed: they would hide the profile just measured on it. A profile of that name that already exists is **updated**, and `review.affected` has shown beforehand every other cover following it, with a before and after. |
| A | `"cover_only"` | no profile; this cover's record with the five measured values over whatever it already had, its travel and `raw`; its assignment untouched |
| B | `"profile"` (the only exit) | this cover's record: the profile chosen, `profile_wins`, the travel measured, `raw`, no values of its own — what the dialog writes |
| C | `"cover_only"` (the only exit) | only the keys measured, over what was already stored; `profile_wins` kept; for "the thorough calibration only" just the two roll coefficients — what the dialog writes |

`target: "profile"` does not mean the same write on every path, and the table above is
what it means: on path A it **writes** the profile (creating it, or updating the one of
that name) and assigns it; on path B it writes no profile at all — the shutter is being
told which kind of shutter it is, and `cover_profiles` is not touched.

The write goes through the same door as every write of §8 — one write at a time per
gateway (`write_in_progress`), the covers pick up the new numbers **in place, without a
reload**, and every subscriber receives the new `overview` — with two differences: it is
not refused by the calibration it belongs to, and it hands back **no undo token** (three
minutes of measurements are not a gesture to take back by accident; "Remove the
measurement" on the cover card exists). The answer carries the `saved` snapshot and the
`overview`. `raw` records `"client": "panel"` and `"save_target"` beside what the dialog
records. Nothing is written before this command, and a refused `save` writes nothing.

**`end_other`** is for a shutter held by something that is not the panel. It aborts
**every open *Configure* dialog of the gateway** — the dialog releases the shutter
without stopping it, and if it had saved something the integration reloads, as it
always does when that dialog closes — and answers how many it aborted. When the
shutter is still being calibrated afterwards, it was the 0.4.2 service:
`still_calibrating: true`, and the run has to be left to finish. The panel says all of
this before asking for confirmation.

### 11.3 Who may call what

| Command | The owner, present | Another client, owner present | Another client, owner absent |
|---|---|---|---|
| `get`, `attach` without `claim` | yes | yes, read only | yes, and becomes the owner |
| `attach` with `claim` | yes | yes (the screen asks first) | yes |
| `act`, `stop`, `save` | yes | `session_owned` | yes, and becomes the owner |
| `leave` | yes | a no-op that answers the snapshot | yes, and becomes the owner |
| `heartbeat` | yes | `{owner: false}` | `{owner: false}`: it never takes ownership |
| `cancel` | yes | `session_owned`, unless `force: true` | yes |

`end_other` names no session and is not subject to ownership.

### 11.4 The event

`myhome/calibration/subscribe` (§9) pushes a third kind of event:

| `type` | Payload | When |
|---|---|---|
| `session` | `{"type": "session", "session": {…§12…} \| null}` | on subscribing, and after every transition of the gateway's session, in `revision` order |

There is no separate "motor started" event: the transition to `awaiting_endpoint`
**is** that signal, published the moment the actuator's echo arrives.

The event carries the snapshot and **not** `capabilities`, which only `get` answers: a
client that subscribes and never asks would have to assume what the backend offers, so
the panel calls `get` once when it opens the wizard.

### 11.5 Moving the shutter from outside

The session watches its shutter's state. A movement is **external** when the cover
starts opening or closing while none of the session's movements is under way, or in the
opposite direction to the one under way.

* **Outside a measurement** (`armed`, `briefing`, `awaiting_reading`, `checking`,
  `review`) it is **not an interruption**: `position_known` becomes `null`,
  `external_move` becomes `true`, and nothing else changes. Lowering the shutter with
  the wall switch while reading the instructions is a normal thing to do.
* **Before a timed run** (`open_start`, `open_full_start`, `close_start`), when the end
  stop the run starts from is no longer known, the session first **brings the shutter
  back to it by itself** — `positioning`, on the homing step of that stage
  (`open_timed`, `open_home_again`, `close_timed`) — and then returns to the same brief
  with `notice: "rehomed"`. A timed run never starts from an unknown point.
* **While a reading is awaited** after a run to a fraction, the reading no longer
  corresponds: `notice: "reading_stale"`, and `repeat_tape` is offered **first** in
  `actions` although a reading step has no menu of its own. Its label is the dialog's
  own, borrowed from the screen that normally offers it
  (`options.step.tape_result.menu_options.repeat_tape`): the same word, in the same seven
  languages. The field stays on the screen, because the user may have measured before the
  shutter was touched and is the one who knows.
* **During a measurement** (`running`, or a `positioning` that precedes a reading) a
  movement in the opposite direction, or a stop before the lift-off press, makes the
  step `problem_interrupted`. A stop while `awaiting_endpoint` with `press.kind =
  "end_stop"` is not one: it is the end stop the step is measuring.

`external_move` goes back to `false` the next time the session itself moves the shutter.

### 11.6 How a session ends

| Event | The session | A stop is written |
|---|---|---|
| `cancel` | `ended`, `cancelled` | **no** |
| `leave` with nothing measured | `ended`, `left` | no |
| `leave` with something measured, or the owner's presence lapsing | goes on, with no owner | no |
| The lease runs out | `ended`, `expired` | **yes**, if the shutter is moving |
| The integration unloads or reloads | `ended`, `unloaded` | **yes**, from a task |
| `save` succeeds | `saved` | no (nothing is moving) |
| The cover disappears from the gateway | `ended`, `cover_gone` | attempted |

* A terminal snapshot stays readable for **10 minutes**, so that a client coming back
  reads how it ended rather than `unknown_session`; a new `start` replaces it at once.
* **The gateway's reservation outlives the session** (contract §2.1): when a session
  ends while its shutter is still running — a free run cancelled — the gateway stays
  reserved until the cover stops moving, or until a full run in that direction plus the
  settle margin has passed. A `start` meanwhile is `already_calibrating` with
  `{by: "reserved"}`, which is the one value of `by` that names **no session and no
  dialog**: there is nothing to resume and nothing to close, only a run finishing by
  itself, and the screen says to wait rather than offering either. It is what the user
  meets pressing "Calibrate another shutter" right after cancelling one. The shutter
  itself is released at once: `calibrating` drops and its other commands work again.
* A reload made by the dialog when it closes after saving ends a panel session on the
  same gateway as `unloaded`, with a stop.

---

## 12. The session snapshot

One object, sent whole at every transition and never as a patch. Around 2 kB on the
screens that measure, and a little over 3 kB on a review; a review grows by roughly half
a kilobyte for every other shutter that follows the profile being written (`affected`),
so on a profile followed by a dozen shutters the review snapshot is several kilobytes.
That is deliberate: the one screen that has to show, before writing, what the write does
to every follower is the one screen worth the bytes, and it is published once per
transition and not per frame. **Every key is always present**; what does not apply is `null` (or `[]` for a
list). Instants are ISO-8601 in UTC from the backend's clock. Numbers are the values as
computed, not rounded for display, except where the dialog itself rounds before
storing or deciding: `review.rows[].after` for the measured keys (what `save` writes)
and `check.gap_cm` (the number the threshold decides on, to 0.1 cm).

### 12.1 Keys

| Key | Type | Notes |
|---|---|---|
| `session_id` | string | new for every session |
| `entry_id` | string | |
| `revision` | int | starts at 1, +1 per transition (§11.1) |
| `server_time` | instant | when this snapshot was built; the panel estimates its clock offset from it to animate elapsed times |
| `cover` | object | `{unique_id, entity_id, name}` |
| `state` | token | the contract's: `armed`, `briefing`, `running`, `positioning`, `awaiting_reading`, `checking`, `review`, `saved`, `ended`. No session is `session: null`, never an `idle` snapshot; `fitting` never appears, because the fit runs between two transitions |
| `substate` | token \| null | in `running` only: `awaiting_endpoint` (the user must press) or `awaiting_stop` (the run ends by itself or on the stop being written); `null` while the motor is starting |
| `step` | string \| null | the dialog's step id (§12.2): the key of `options.step.<step>` and the identity of the screen. `null` in `saved` and `ended` |
| `path` | token \| null | `path_a`, `path_b`, `path_c` |
| `scope` | token \| null | a correction's scope once chosen: `times_only`, `times_and_rolls`, `points_only` |
| `profile` | string \| null | the profile chosen on `path_b` / `path_c`, or named by `start` |
| `level` | token | `basic`, or `thorough` once the thorough calibration has been added |
| `plan` | array | the dialog's plan, as stage names — step ids plus `summary` — in the order they will be walked (the tape readings are reordered when the tape phase begins, as in the dialog). `[]` before a path is chosen, and once the session has ended without saving |
| `plan_index` | int \| null | where on `plan` the session stands |
| `intent` | object \| null | `{scope}` when `start` named a scope, for `refine_scope` to highlight |
| `actions` | array | the dialog's `menu_options` for this step, **in the dialog's order**, minus its two ways out: `save` (the `save` command) and `cancel_flow` (the `cancel` verb). Ways forward only. Labels: `options.step.<step>.menu_options.<action>`, except the borrowed `repeat_tape` of §11.5 |
| `form` | object \| null | §12.3 |
| `placeholders` | object | the values the step's texts substitute, under the **dialog's placeholder names** (`cover`, `percent`, `expected`, `run`, `deviation`, …), as raw numbers and strings: the panel formats them in the user's language |
| `movement` | object \| null | what the session is moving: `{kind, direction, progress_action, started_at, planned_s}`. `kind` is `homing` (to an end stop), `free` (a timed run the user ends, the lift-off run while its stop goes out included) or `fraction` (a run to a fraction of the travel); `progress_action` is the dialog's `options.progress.<action>` key for it; `started_at` is the motion anchor — the actuator's echo, or the frame written plus its start delay for an actuator that sends none — and `null` while the motor is starting; `planned_s` is the modelled duration, for a progress bar only. `null` when nothing of the session's is moving |
| `press` | object \| null | in `awaiting_endpoint`: `{kind, expires_at}`, `kind` being `lift_off` or `end_stop`. Past `expires_at` (90 s after the motor echoed) the backend moves to `problem_timeout` by itself |
| `reading` | object \| null | in `awaiting_reading` after a run to a fraction: `{direction, fraction, from_end_stop, expected_cm, tolerance_cm}` — where the model expects the bar and how far off is still normal (3 cm with a fitted model, 15 cm without). `null` for the travel and the lift-off gap |
| `measured` | object | what has been measured so far (§12.4). Emptied once the session has ended without saving: provisional values are discarded |
| `fit` | object \| null | `{opening, closing}`, each `{run_time_s, slat_time_s, roll, time_scale, points: [{motor_s, measured_cm, residual_cm}]}`, once both directions have a reading. `residual_cm` is model minus tape, and `null` for a direction fitted through a single point, which reproduces itself exactly and has nothing left over to be a residual |
| `check` | object \| null | a verification run: `{fraction, predicted_cm, measured_cm, gap_cm, threshold_cm, profile_level, profile_check_cm}`. In path B, `threshold_cm` is the fixed 3 cm above which the correction is offered, and `profile_level` / `profile_check_cm` say how the profile being checked was itself measured, so the gap can be read against it; all three are `null` for the thorough calibration's own check |
| `review` | object \| null | in `review` (and kept in `saved`): §12.5 |
| `problem` | object \| null | `{code}` on a `problem_<code>` step: `no_echo`, `not_delivered`, `not_stopped`, `busy`, `bad_point`, `timeout`, `unknown` — the dialog's — and `interrupted` |
| `notice` | token \| null | `rehomed` or `reading_stale` (§11.5): something to say about what happened around the step that is not a problem |
| `position_known` | token \| null | `closed` or `open`: the end stop the session last saw the shutter reach; `null` anywhere else, or once something outside the session has moved it (the dialog's `_at`) |
| `external_move` | bool | an external movement was seen since the session last moved the shutter (§11.5) |
| `owner` | object \| null | `{client_id, present_until}`; `null` when nobody owns it, and on a terminal snapshot |
| `idle_expires_at` | instant \| null | when the lease runs out; `null` on a terminal snapshot |
| `outcome` | object \| null | on a terminal snapshot: `{reason, profile, origin, source}`. `reason` is `saved`, `cancelled`, `expired`, `unloaded`, `left` or `cover_gone`; after a save, `profile`, `origin` and `source` are what `overview` now says about the cover |

A terminal snapshot has no `actions`, `form`, `movement`, `press`, `owner` or
`idle_expires_at`; a `saved` one keeps `measured`, `fit`, `check` and `review` as they
were, so the outcome screen can say what was written.

### 12.2 Steps

`step` is always one of the dialog's own step ids — the same `async_step_<id>` and the
same `options.step.<id>` texts — so that the panel shows sentences already translated
into seven languages. `problem_interrupted` is the one step the panel adds.

| `step` | `state` | `actions` / `form` |
|---|---|---|
| `path` | armed | `path_a`, `path_b`, `path_c` (the last two only when a profile exists) |
| `path_a` | armed | `begin` |
| `path_b`, `path_c` | armed | form `profile` (choice) |
| `refine_scope` | armed | `times_only`, `times_and_rolls`, `points_only` |
| `home_closed`, `open_timed`, `open_home_again`, `close_timed`, `height_read` | positioning | — (a homing) |
| `home_closed_done` | briefing | `confirm_closed`, `repeat_step`, `not_right` |
| `open_brief`, `open_full_brief`, `close_brief` | briefing | `open_start` / `open_full_start` / `close_start`, `repeat_step` |
| `open_start`, `open_full_start`, `close_start` | running, no substate | — (the motor is starting) |
| `open_lift` | running / awaiting_endpoint, press `lift_off` | `lifted_off`, `repeat_step`, `not_right` |
| `lift_stop` | running / awaiting_stop | — (the stop the press asked for) |
| `lift_check`, `lift_check_late` | briefing | `lift_too_early`, `lift_accept`, `lift_gap`, `not_right` |
| `lift_gap` | awaiting_reading | form `gap_cm`, optional (empty keeps the press) |
| `lift_early` | briefing | `repeat_step`, `lift_gap`, `not_right` |
| `closed_again` | briefing | `confirm_closed_again`, `repeat_step`, `not_right` |
| `open_top`, `close_bottom` | running / awaiting_endpoint, press `end_stop` | `stopped_open` / `stopped_closed`, `repeat_step`, `not_right` |
| `open_result`, `open_result_gap`, `close_result` | briefing | `accept_step`, `repeat_step` |
| `height` | awaiting_reading | form `height` (20-500 cm) |
| `height_result` | briefing | `accept_step`, `repeat_measure`, `not_right` |
| `tape_brief` | briefing | `tape_start` |
| `half_down`, `half_up`, `quarter_down`, `three_quarter_down`, `quarter_up`, `three_quarter_up`, `verify`, `verify_b` | positioning | — (the homing before a reading) |
| `tape_run` | positioning | — (the run to the fraction) |
| `measure_descent`, `measure_ascent`, `measure_verify` | awaiting_reading | form `measured_cm` |
| `tape_result` | briefing | `accept_step`, `repeat_tape`, `tape_not_right` |
| `verify_result` | checking | `path_c` (path B, gap above 3 cm), `accept_step`, `repeat_tape` |
| `verify_offer` | briefing | `verify_now`, `skip_verify` |
| `profile_name` | briefing | form `name` (text) |
| `summary_basic`, `summary_correction` | review | `refine`; the exits are `review.targets` |
| `summary_short`, `summary_precise` | review | — ; the exit is `review.targets` |
| `problem_<code>` | briefing | `repeat_step` |

The dialog offers `cancel_flow` on several of these screens and `save` on the four
summaries; neither is in `actions` (§11.2), because in the panel the way out is the ✕ on
every screen and the way to save is the `save` command.

The rules are the dialog's: `repeat_step` re-enters the stage the plan stands on, with
its own movements; `not_right` writes a stop first and then does the same; `accept_step`
moves on; `repeat_tape` throws the last reading away and repeats its movements;
`repeat_measure` asks for the travel again without moving anything. A movement that
fails does not end the session: it lands on `problem_<code>` with `repeat_step`.

The panel reuses the dialog's texts (`options.step.<step>`) for every step that has
them **except the four summaries**, which speak of closing the dialog and of *Configure →
Calibrations*; the list is `SESSION_REUSED_STEPS`. Positioning steps have no step text:
their screen is `options.progress.<movement.progress_action>`.

### 12.3 `form`

```jsonc
{"field": "measured_cm", "kind": "number", "optional": false, "unit": "cm",
 "suggested": null, "min": 0.0, "max": 195.0, "choices": null, "error": null}
```

| `field` | `kind` | Notes |
|---|---|---|
| `profile` | `choice` | `choices`: the profiles, sorted; `suggested`: the one preselected |
| `height` | `number` | 20-500 cm; `suggested`: the travel already known, or 200 |
| `measured_cm` | `number` | 0 to the travel (`above_the_travel` beyond it) |
| `gap_cm` | `number` | `optional: true`, 0-50 cm; under 1 cm is a shutter still on its rest (`lift_early`) |
| `name` | `text` | the profile name pattern of §8.7; `suggested`: one made from the entity id |

`error` is `null` or the dialog's `options.error.*` key of the last value sent:
`not_a_number`, `out_of_range`, `above_the_travel`, `invalid_name`. `unit` is `"cm"` or
`null`, and `choices` is present exactly for `kind: "choice"`.

`choices` carries the profile **names** only, in the order `overview.profiles[]` has them
(sorted by name), and nothing else: the line the screen shows under each name — its
reference travel and the shutter it was measured on — is read from `overview.profiles[]`
(`reference_height`, `measured_on_name`), which the panel already holds. One list of
profiles, answered by one command.

### 12.4 `measured`

| Key | Type | Notes |
|---|---|---|
| `travel_cm` | number \| null | the curtain travel this session works with |
| `travel_measured` | bool | read with a tape in this session, rather than already known |
| `opening_time_s`, `closing_time_s`, `slat_time_s` | number \| null | the presses' provisional results |
| `lift` | object \| null | the lift-off press, once it has arrived: `{pressed_at, stop_written_at, gap_cm, late}` — when the press reached the backend, when the stop it asked for was written, the gap read with the tape if one was, and whether the gateway held the stop back for more than a second. Both instants are there because the contract (§2.1) names both ends a run can have; how the slat time is derived from them is the dialog's, unchanged |
| `descent`, `ascent` | array | `[motor_s, measured_cm]` pairs, in the order they were read |
| `times_adopted` | bool | `true` for `points_only`, whose run times are the ones the cover already moves on rather than presses |

### 12.5 `review`

```jsonc
{"variant": "basic",                        // summary_<variant>: basic | short | correction | precise
 "targets": ["profile", "cover_only"],      // the exits of `save`, the first being the main one
 "profile_name": "tall", "profile_exists": true,
 "name_clash": null,                        // "file" when cover_profiles: defines the same name
 "rows": [{"key": "travel_cm", "before": 195.0, "after": 195.0},
          {"key": "opening_time_s", "before": 25.0, "after": 22.6}, …],
 "side_effects": [],                        // [{"key": "stop_latency_s", "before": 0.35, "after": 0.1}]
 "affected": [{"cover_unique_id": "…-2-82", "name": "Landing Shutter", "rows": [ … ]}],
 "accuracy_cm": null, "check_fraction": null,
 "replacing": ["travel_cm", "opening_time_s", …], "keeping": [],
 "yaml": "cover_profiles:\n  tall:\n    reference_height: 195.0\n …"}
```

* `rows` are always the six keys `travel_cm`, `opening_time_s`, `closing_time_s`,
  `slat_time_s`, `opening_roll`, `closing_roll`, in that order. `before` is what the
  cover runs on today; `after` is what it will run on after the main exit, **resolved
  by the server** with the same function the cover uses — the store as it would be,
  plus the new profile.
* `side_effects` lists any *other* key whose value would change — in practice the bus
  costs `stop_latency_s` / `start_delay_s`, when `myhome.yaml` writes them for this cover
  and the profile carries the installation's defaults, so that following the profile
  brings the profile's. Nothing changes silently. It is `[]` whenever the file writes no
  bus cost for this shutter, which is the ordinary case and the one every example in the
  fixture is in.
* `affected` is filled when the profile already exists: every other cover that follows
  it, with its own rows. It is not truncated — the contract's first exit is precisely
  "update the profile this cover follows", and it is worth a preview of **every** cover it
  reaches — which is why a review of a much-followed profile is the largest snapshot
  there is (see the head of §12).
* `accuracy_cm` and `check_fraction` are the thorough calibration's check — within how
  many centimetres, at which fraction of the descent. `null` otherwise, and the screen
  says the accuracy has not been verified rather than showing a dash.
* `replacing` are the keys this session measured and `save` writes; `keeping` the keys
  this cover already had stored that it leaves as they are.
* `yaml` is the `myhome.yaml` equivalent, as the dialog shows it.

### 12.6 A complete example

A basic calibration of path A, standing on the reading after the half descent: the
ascent's reading has been taken already (the tape phase started from the bottom, so
the ascent came first), the shutter has been brought to the top and run half-way down,
and the screen asks for the tape.

```json
{
  "session_id": "6f1d2c3b4a5e4f708192a3b4c5d6e7f8",
  "entry_id": "01EXAMPLEEXAMPLEEXAMPLEEXA",
  "revision": 32,
  "server_time": "2026-09-18T10:01:26.200000+00:00",
  "cover": {
    "unique_id": "00:03:50:aa:bb:cc-2-81",
    "entity_id": "cover.hallway_shutter",
    "name": "Hallway Shutter"
  },
  "state": "awaiting_reading",
  "substate": null,
  "step": "measure_descent",
  "path": "path_a",
  "scope": null,
  "profile": null,
  "level": "basic",
  "plan": [
    "home_closed",
    "open_timed",
    "height_read",
    "close_timed",
    "tape_brief",
    "half_up",
    "half_down",
    "profile_name",
    "summary"
  ],
  "plan_index": 6,
  "intent": null,
  "actions": [],
  "form": {
    "field": "measured_cm",
    "kind": "number",
    "optional": false,
    "unit": "cm",
    "suggested": null,
    "min": 0.0,
    "max": 195.0,
    "choices": null,
    "error": null
  },
  "placeholders": {
    "cover": "Hallway Shutter",
    "percent": 50,
    "direction": "close",
    "expected": 86.25,
    "tolerance": 15.0
  },
  "movement": null,
  "press": null,
  "reading": {
    "direction": "close",
    "fraction": 0.5,
    "from_end_stop": "open",
    "expected_cm": 86.25,
    "tolerance_cm": 15.0
  },
  "measured": {
    "travel_cm": 195.0,
    "travel_measured": true,
    "opening_time_s": 22.299999952316284,
    "closing_time_s": 21.700000047683716,
    "slat_time_s": 4.700000047683716,
    "lift": {
      "pressed_at": "2026-09-18T10:00:14.700000+00:00",
      "stop_written_at": "2026-09-18T10:00:14.700000+00:00",
      "gap_cm": null,
      "late": false
    },
    "descent": [],
    "ascent": [
      [
        13.5,
        81.5
      ]
    ],
    "times_adopted": false
  },
  "fit": null,
  "check": null,
  "review": null,
  "problem": null,
  "notice": null,
  "position_known": null,
  "external_move": false,
  "owner": {
    "client_id": "3b0c7e1a-5d2f-4a8e-9c61-0e7f4b2d9a10",
    "present_until": "2026-09-18T10:02:11.200000+00:00"
  },
  "idle_expires_at": "2026-09-18T10:11:26.200000+00:00",
  "outcome": null
}
```

The three run times are **raw**: they are clock differences and nothing rounds them
before they are saved, which is what "numbers as numbers, formatted by the panel"
(§1) means when the number is a measurement rather than a stored setting.

The panel answers it with:

```jsonc
{"type": "myhome/calibration/session/act", "entry_id": "01EXAMPLEEXAMPLEEXAMPLEEXA",
 "session_id": "6f1d2c3b4a5e4f708192a3b4c5d6e7f8", "client_id": "3b0c7e1a-…",
 "revision": 32, "action": "submit", "value": "83,5"}
```

`tests/fixtures/panel_session_examples.json` has one such snapshot for every screen the
panel draws — the first press, the lift-off check, a positioning, a field error, each
review, each check, each problem and each ending — plus an example frame of every
command. From the release that registers these commands the file is **regenerated from
the server** by `tests/test_websocket_session.py`, walk by walk, rather than written by
hand; the snapshot above is its `awaiting_reading_measure_descent`, copied, and a test
compares the two so that the example cannot go stale under a regeneration.

---

## 13. Refusals of the session

| Situation | Code | `translation_key` | Placeholders |
|---|---|---|---|
| A session of the panel's already exists on the gateway | `not_allowed` | `already_calibrating` | `{cover}`, `{by}`: `panel` |
| A cover of the gateway is being calibrated by the dialog or by the 0.4.2 action | `not_allowed` | `already_calibrating` | `{cover}`, `{by}`: `other` |
| The gateway is still reserved by a session that ended while its shutter ran on (§11.6) | `not_allowed` | `already_calibrating` | `{cover}`, `{by}`: `reserved` — nothing to resume and nothing to close; the screen says to wait |
| The cover has no entity, or it is `unavailable` | `not_found` | `cover_unavailable` | `{cover}` |
| No such `session_id` — never existed, or removed 10 minutes after it ended | `not_found` | `unknown_session` | — |
| A verb on a session that has ended (other than `cancel`, `get`, `attach`) | `not_allowed` | `session_ended` | `{reason}` |
| Another client owns the session and is present | `not_allowed` | `session_owned` | — |
| `revision` is not the current one | `not_allowed` | `revision_conflict` | — |
| An action the step does not offer, or a `save` target the review does not | `not_allowed` | `action_not_offered` | `{action}` |
| `save` outside `review` | `not_allowed` | `not_in_review` | — |
| The profile name is not usable, checked again at `save` | `service_validation_error` | `invalid_name` | `{profile}` |
| Another write of the gateway is being applied | `not_allowed` | `write_in_progress` | — |

Plus those of §5 and §8.10 that apply: `unknown_entry`, `entry_not_loaded`,
`unknown_cover`, `advanced_cover` (`not_supported`: an actuator that reports its own
position has nothing to calibrate) and `unknown_profile` (a `start` naming a profile
nobody defines). Malformed frames are `invalid_format`, from the schema.

No refusal leaves anything half written, and none is used for what is the user's to
correct: a value that cannot be a reading is a `form.error`, and a movement that fails
is a `problem` step.

The first eight keys are new with the session, and their sentences are written in
**English and Italian only** — the decision of 14 September, which is how the panel's own
block is written and which reaches these eight because they are the panel's sentences
even though `exceptions` is where Home Assistant resolves them. The other five languages
fall back to English key by key until the translation lot before the release;
`tests/test_translations.py` holds the tolerance to exactly these eight and to no other
refusal.

---

## 14. The session and the published contract

`docs/calibration-contract-proposal.md` Part 2 describes the session this API
implements. Where the two meet — states, verbs, names at the boundary — this API uses
the contract's words; where the dialog already had words for the screens, it keeps
them, because they are translated. This is the correspondence, and what is missing.

**States (§2.2).** `armed`, `briefing`, `running` with `awaiting_endpoint` /
`awaiting_stop`, `positioning`, `awaiting_reading`, `checking`, `review` and `saved` are
the contract's, one for one. Two differences:

* `fitting` never appears. The fit takes milliseconds and happens between two
  transitions; the contract asks that what a backend does not produce be absent rather
  than empty.
* `ended` is added, for every way a session finishes without being saved (the reason is
  in `outcome.reason`). `idle` is not a state here: it is `session: null`.

**Verbs (§2.2).** `stop`, `leave` and `cancel` mean exactly what the contract says:
only `stop` touches the shutter; `leave` ends a session only when nothing provisional
is left to protect; `cancel` discards and does not stop. `start`, `attach`,
`heartbeat`, `act`, `save` and `end_other` are the conversation around them.

**Timing (§2.1).** The backend is the only clock, and a run starts at the motion
anchor — the actuator's echo, or the frame written when there is none. The end of the
lift-off run is taken from the press, exactly as the dialog does, and the snapshot
exposes both the press and the instant the stop frame was written
(`measured.lift`), so that both of the contract's cases are visible; moving the
definition to "the stop frame written" would change the numbers against the dialog and
every measurement already made, and is left as a question.

**Lease and presence.** The contract's lease is the dialog's inactivity timer (1800 s,
600 s after a movement), renewed by transitions and by the owner's verbs, not by
heartbeats. Presence — a heartbeat every 15 s, lapsing after 45 s — is an addition of
this API, and it only decides who may act: a phone locked in the middle of a tape
reading must not lose the reading. **Reservation** of the gateway outlives the session
as the contract describes (§11.6).

**Names at the boundary (§1, §2).** The session's payloads use the contract's names;
the store, `myhome.yaml` and the fourteen older commands keep theirs, and renaming those
is left for the upstream port:

| In the store, the file and §2-§10 | In the session |
|---|---|
| `height` (a cover's) | `travel_cm` |
| `reference_height` (a profile's) | `reference_travel_cm` |
| `opening_time`, `closing_time`, `slat_time` | `opening_time_s`, `closing_time_s`, `slat_time_s` |
| `opening_roll`, `closing_roll` | unchanged |
| `stop_latency`, `start_delay` | `stop_latency_s`, `start_delay_s` |
| the dialog's inactivity watchdog | the lease, `idle_expires_at` |
| — | presence, `owner.present_until` |

The **placeholders** of the texts (`{cover}`, `{height}`, `{percent}` …) are not data
fields but names inside sentences already translated, and keep the dialog's names.

**Refusals (§2.6).** `already_calibrating`, `unknown_cover`, `cover_unavailable`,
`advanced_cover` and `revision_conflict` are refusals here as there. The others are not
refusals of a command, because none of them is the answer to one:

* `not_delivered`, `no_echo`, `not_stopped` and `timeout` happen to a *movement*, after
  the command that started it has been answered; they are `problem.code` on a
  `problem_<code>` step, with `repeat_step`, as in the dialog — and so are the dialog's
  `busy`, `bad_point` and `unknown`, and this API's `interrupted`;
* `bad_reading` is `form.error`, in the detail the dialog already had texts for:
  `not_a_number`, `out_of_range`, `above_the_travel`;
* `lease_expired` is an ending, `outcome.reason: "expired"`; a verb sent afterwards is
  `session_ended`.

**The plan (§2.5).** Path A at both levels, path B with its optional check, and path C
in its three scopes are the dialog's plans, walked in the same order, with the same
reordering of the tape readings. "Repeat this step" is a first-class transition
(`repeat_step`, `repeat_tape`); the reading step returns the expected value and its
tolerance (`reading`); the fit returns the residual at each point (`fit`); the check
returns the predicted position, the measured one and the gap (`check`).

**Writes (§2.7).** Save is explicit, atomic and refused against a stale revision. Of
the three exits, *save as a new profile and assign* and *keep these values for this
cover only* are the two `target`s of path A; *update the profile this cover follows* is
path A's `"profile"` target on a name that already exists, with the before and after of
every other follower shown first (`review.affected`) rather than a third button. Path A
now saves as the contract says — the profile and the assignment, **no values of the
cover's own** — while the dialog goes on saving as it always has; the difference is
deliberate.

**The session in the overview.** `overview.session` (§2) is the same session seen from
the outside: the one line a banner needs. It is declared with the rest of this contract
and appears in the overview when the server starts sending it; `overview.measuring`,
which predates the session and is raised by the dialog and the 0.4.2 action too, keeps
its meaning exactly.

**What is missing, and why.**

* **Calibrating several covers in one session**, or path B on every similar cover at
  once: the contract allows one session per gateway, and the curtain travel has to be
  read cover by cover anyway (`capabilities.bulk: false`).
* **Per-key provenance** in the store (`overrides.<key>.source`): a migration of the
  store, not of the session; the record keeps its record-level `source` and
  `measured_at`.
* **Path B's threshold read against the profile's own accuracy**: the threshold stays
  the dialog's fixed 3 cm. The snapshot shows the profile's level and the gap of its
  own check beside the gap (`check.profile_level`, `check.profile_check_cm`), so the
  number can be read against it by the person looking at it.
* **The type of shutter** at the start of path A (a curtain on a rail, a shutter with no
  slats): it changes the model, and is outside this version.
