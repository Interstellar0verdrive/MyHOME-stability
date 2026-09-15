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

Answers `success` and then pushes events with that subscription's id. Two kinds:

| `type` | Payload | When |
|---|---|---|
| `overview` | `{"type": "overview", "overview": {…§2…}}` | on subscribing, and after every successful write and undo |
| `measuring` | `{"type": "measuring", "cover_unique_id": "…" \| null, "name": "…" \| null}` | whenever a guided calibration takes one of this gateway's shutters or gives it back |

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

There is no third event covering a reload: a write does not reload the config entry (§7),
so there is no window of unavailability to be honest about.

The subscription dies with the socket — Home Assistant unsubscribes every listener
when the connection closes — and nothing here outlives it, because nothing here holds
a shutter.

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
