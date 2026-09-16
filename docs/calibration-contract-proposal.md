# Cover calibration: storage schema and session states

A proposal for the shared MyHOME panel, written for
[discussion #270](https://github.com/orgs/OpenWebNet-HA/discussions/270). It describes
two things a panel module and a backend have to agree on before either is written:

1. **what a calibration is, once it is stored** — the profile, the per-cover record,
   and the rule that decides which number a shutter actually runs on;
2. **what a measuring session is, while it runs** — its states, who owns it, what
   interrupts it and what each interruption does to the shutter.

It is written from an implementation that has run on twelve shutters since early
September, but it is not a description of that implementation's code: names here are
proposals, and anything the backend cannot support should be absent rather than
present and empty.

---

## Part 1 — Storage

### 1.1 Why a profile carries a reference travel

A timed cover has no position sensor, so its position is an estimate computed from how
long the motor has run. Two things make that estimate non-linear:

- **The slats.** On the way up, the first phase separates the slats while the bottom
  edge stays on its rest. Only after that does the curtain start to travel.
- **The roll.** The curtain winds onto a tube, so the tube's effective diameter grows as
  the cover opens. The cover moves faster near the top than near the bottom, and faster
  going down than going up because gravity helps.

The consequence is easy to state and easy to measure: with a linear model, a 198 cm
shutter sent to 50 % from fully open stops at about 85 cm from the floor instead of 99.
The correction is one coefficient per direction (the ratio between the roll's diameter
full and empty, typically 1.5 to 2.5) plus the slat time.

Those numbers are properties of a *kind* of shutter, not of one window: the same model
of curtain on a taller window has the same physics with more slats. That is what makes
a profile worth having — measure one window, and every similar window inherits the
result, scaled to its own travel. Without a reference travel, a profile only fits the
window it was measured on, and sharing it is a coincidence.

### 1.2 A profile

```jsonc
{
  "id": "0f3a…",                 // opaque, stable; display name is editable and not the key
  "name": "Tall french windows",
  "reference_travel_cm": 198.0,  // the travel of the cover this profile was measured on
  "opening_time_s": 24.10,       // full run, bottom end stop to top end stop
  "closing_time_s": 23.40,
  "slat_time_s": 2.74,           // part of opening_time_s: slats separating before travel
  "opening_roll": 2.10,          // roll diameter ratio, per direction
  "closing_roll": 2.29,
  "stop_latency_s": 0.30,        // gateway answer time; a property of the plant
  "start_delay_s": 0.55,         // motor start after the frame is written; ditto
  "measured_on": "cover_unique_id",   // which cover produced it, or null
  "measured_at": "2026-09-13T17:22:00Z"
}
```

Notes that matter more than the names:

- **`reference_travel_cm` is mandatory for a profile that is to be shared.** A backend
  running a linear model can store a profile without rolls and without a slat time; it
  cannot share one across covers of different travel without this field.
- **`stop_latency_s` and `start_delay_s` are never scaled.** They are the gateway's
  answer time and the motor's brake: the same on a 90 cm skylight as on a 250 cm door.
- **`measured_on` / `measured_at` are provenance, not configuration.** A profile that
  never recorded them says so with nulls; nothing should invent a date.

### 1.3 A cover's record

```jsonc
{
  "cover_unique_id": "…",        // identity is (entry_id, cover_unique_id)
  "profile_id": "0f3a…",         // the profile this cover was told to follow, or null
  "profile_assigned": true,      // somebody said so on this installation (see 1.5)
  "travel_cm": 154.0,            // this cover's own travel; what the profile scales to
  "overrides": {                 // this cover's own measured values, key by key
    "closing_time_s": 19.80
  },
  "source": "guided",            // guided | assigned | manual
  "measured_at": "2026-09-14T08:10:00Z"
}
```

An override is per key, not per record: a cover can have its own closing time and
inherit everything else. That is what makes "this one shutter drifts from its group"
cheap to fix without creating a profile for it.

### 1.4 Scaling a profile to a cover

With `k_ref` the profile's closing roll, `H_ref` its reference travel and `H` the
cover's travel:

```
k        = sqrt(1 + (k_ref^2 - 1) * H / H_ref)       # each roll grows this way
scale    = (k - 1) / (k_ref - 1)                      # H / H_ref for a linear profile
slat     = slat_time_s * H / H_ref
opening  = slat + (opening_time_s - slat_time_s) * scale
closing  =        (closing_time_s)               * scale
```

The curtain scale is taken from the **closing** roll and used for both directions on
purpose: it measures how much curtain the tube has to unwind, which is one length of
curtain whichever way the motor turns. The up/down difference the two rolls carry is
the motor's load, not the geometry; scaling each direction by its own roll would make
one profile predict two different curtain lengths. Without a travel on the cover there
is nothing to scale to and the profile is used as it stands.

A backend that implements only linear timing ignores the rolls and the slat time and
scales by `H / H_ref`, which is the same formula with `k_ref = 1`.

### 1.5 Precedence: which number does the shutter run on

Resolved key by key, in this order, and stated once so that the panel and the runtime
can never disagree:

| Order | Source | Shown as |
|---|---|---|
| 1 | the cover's own measured value (`overrides`) | **Measured** |
| 2 | the assigned profile, scaled to the cover's travel | **Inherited from «name»** |
| 3 | the key as written in `myhome.yaml` for this cover | **From the file** |
| 4 | a profile named by the file, or the integration's defaults | **Defaults** |

Two rules come out of it and are worth writing into the contract:

- A cover with both an assigned profile and its own measured values is **adjusted from
  «name»**: the profile fills every key the cover did not measure itself.
- The API exposes the resolved value **and** its origin, per key. A client must never
  compute precedence, and a screen that disagreed with the shutter about where a number
  came from would make the whole panel untrustworthy, silently.

### 1.6 What the API has to answer

For one gateway, in one read: the profiles with their values and provenance, the covers
with their travel, their assignment, their overrides, and per key the **effective value
plus its origin**. Enough to answer, without a second request per cover:

- which covers follow this profile;
- why does this cover behave differently from its group;
- what changes if I edit this profile (the before/after of every follower).

---

## Part 2 — The measuring session

### 2.1 Shape

One session per gateway, owned by the backend, not by the browser. A session has an
owner (the socket or the service call that started it), a lease that expires, and a
target cover. Opening a second one is refused, not queued: a shutter that two clients
are driving is the one failure mode with a physical consequence.

The backend is the timekeeper. Every duration is measured between bus events (the
motion anchor when the frame is written or the actuator reports movement, and the write
of the stop), never between browser clicks: a queue of twelve covers puts frames 0.1 to
12 s apart, which is 5 to 40 cm of curtain.

### 2.2 States

```
idle
 └─ armed                 target chosen, nothing has moved
     ├─ briefing          the instruction for the next run is on screen; nothing moves
     ├─ running           a run is in progress; a timer is running
     │   ├─ awaiting_endpoint   the user must confirm the physical end stop  (timed run)
     │   └─ awaiting_stop       the run ends by itself, or on the actuator's stop
     ├─ positioning       the backend drives the cover to a point to be measured
     ├─ awaiting_reading  "type what the tape says, in cm"                   (reading)
     ├─ fitting           the backend computes times, slat time and rolls
     ├─ checking          one out-of-sample run: predicted vs measured
     └─ review            all values on screen, nothing stored yet
         └─ saved
```

Three verbs, and each means exactly one thing:

- **stop** — write a stop frame now. The only verb that touches the shutter.
- **leave** — detach the client. A run in progress finishes by itself at the end stop;
  nothing is stored. This is what closing the window does.
- **cancel** — discard the provisional values and end the session. It does not imply
  movement; a run already under way still finishes on its own.

A lease expiry or the integration unloading does send a stop, because in those cases
nobody is watching any more.

### 2.3 Two kinds of step, and why they behave differently

- **Steps where the user acts at a moment**: confirming an end stop, pressing when the
  curtain arrives. The instruction must be read *before* anything moves, because a press
  that arrives late is a wrong measurement. So confirming an endpoint ends the step, and
  the next run starts from its own instruction.
- **Steps where the user only looks and measures**: the backend drives the cover to the
  point and asks for a number. Moving while the user reads costs nothing and saves a
  step, so these can be chained with one warning at the start of the phase.

### 2.4 Levels

- **Basic** — the timed runs plus one reading per direction. About 4 cm on the shutters
  I have measured; usable, and the shortest path for someone with one shutter.
- **Thorough** — readings at roughly 25 % and 75 % per direction, which is what fits the
  roll coefficients, plus one check at a position nothing was fitted to. About 1 cm.
- **Correction** — a short path for a cover that has drifted from its group: times only,
  times and rolls, or the readings alone, without redoing the whole measurement.

### 2.5 Refusals the session needs

`already_calibrating`, `unknown_cover`, `cover_unavailable`, `advanced_cover` (an
actuator that reports its own position has nothing to calibrate), `not_delivered` (the
frame never reached the bus), `no_echo` (the actuator never reported movement),
`not_stopped`, `timeout` (no press in time), `bad_reading` (a tape value that cannot be
true for this cover), `lease_expired`, `revision_conflict`.

A refusal carries a stable machine code and never a partially written result: a session
that fails stores nothing.

### 2.6 Writes

Save is explicit and atomic: one user operation, one transaction. The client sends the
revision it read; a write against a stale revision is refused rather than merged. The
exits from a review are three, and all three should exist:

1. **update the profile this cover follows** — touches the other followers, so it is the
   one that needs a before/after preview of every affected cover;
2. **save as a new profile and assign** — the first measurement of a kind of shutter;
3. **keep these values for this cover only** — the answer to "one shutter drifts", and
   what stops a plant accumulating one profile per cover.

---

## Part 3 — The tasks the screens should be judged against

Not a design, a checklist. Any interface that answers these without a detour is fine by
me, and the simple case must stay simple: someone with one shutter should calibrate,
review and save without passing through any management screen.

1. Calibrate a cover.
2. Make every similar cover use that result.
3. Understand why one cover behaves differently.
4. Correct that one cover without redoing the group.
5. Change a profile and know what it affects before writing.
6. Answer, six months later, "where does this number come from?"

And one acceptance case that is physical rather than architectural: send a calibrated
cover to 50 % from both end stops and check the bottom edge lands within 2 cm of the
expected height. API parity says the backend describes the runtime; this says the
runtime describes the shutter.
