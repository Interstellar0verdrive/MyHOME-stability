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
  "slat_time_s": 2.74,           // the slat phase, part of each full run (see 1.4)
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
ratio    = H / H_ref
k        = sqrt(1 + (k_ref^2 - 1) * ratio)            # each roll grows this way
scale    = (k - 1) / (k_ref - 1)                      # the curtain-time scale
slat     = slat_time_s * ratio
opening  = slat + (opening_time_s - slat_time_s) * scale
closing  = slat + (closing_time_s - slat_time_s) * scale
```

The slat phase is taken out of both run times before scaling and added back after,
because it scales with the number of slats (`ratio`) while the curtain phase scales
with the roll. A profile whose roll is 1 has no roll growth to be proportional to and
the expression for `scale` divides by zero: in that case the scale is simply `ratio`,
which is the linear model.

The curtain scale is taken from the **closing** roll and used for both directions on
purpose: it measures how much curtain the tube has to unwind, which is one length of
curtain whichever way the motor turns. The up/down difference the two rolls carry is
the motor's load, not the geometry; scaling each direction by its own roll would make
one profile predict two different curtain lengths. Without a travel on the cover there
is nothing to scale to and the profile is used as it stands.

A backend that implements only linear timing ignores the rolls and the slat time and
scales both run times by `ratio`, which is the degenerate case above.

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
of the stop), never between browser clicks. On my plant, twelve covers commanded
together put their direction frames 0.1 to 1.2 s apart, so the last of them leaves the
socket up to 12 s after it was queued; on a 24 s shutter that is half the travel, and a
clock started at the click would record it as movement.

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

### 2.4 Levels, in one line each

- **Basic** — the timed runs plus one reading per direction. About 4 cm on the shutters
  I have measured; usable, and the shortest path for someone with one shutter.
- **Thorough** — readings at roughly 25 % and 75 % per direction, which is what fits the
  roll coefficients, plus one check at a position nothing was fitted to. About 1 cm.
- **Correction** — a short path for a cover that has drifted from its group: times only,
  times and rolls, or the readings alone, without redoing the whole measurement.

### 2.5 The measurement plan, end to end

The levels above describe the shape; this is the plan as it actually runs today, step
by step, because a contract that says "a reading step" without saying what a reading is
for leaves the important part unwritten. It is not meant to constrain a backend to this
exact sequence: it is what one implementation does, what each step buys, and what it
stores. A backend that offers less should say so through its capabilities rather than
run a shorter plan under the same name.

**The principle first: there is no stopwatch anywhere in it.** The integration already
knows when a motor *starts*, because the actuator answers a direction command with its
own moving status about half a second later, and the step waits for that (up to three
seconds from the moment the gateway reports the frame written). What nothing on the bus
reports precisely enough is when the motor *stops* at an end stop, and that is the one
thing the user supplies, with a press. One human reaction per measurement instead of
two, and nothing to hold but the tape measure.

#### Path A — the first cover of its kind

Eight movements, about four minutes, three presses and three tape readings.

| # | Step | Movement | User action | What it measures | Stored |
|---|---|---|---|---|---|
| 1 | Close completely | run to the bottom end stop | none | nothing | nothing — it gives every later step a known starting point |
| 2 | Ascent, first run ("lift-off") | starts on the user's "Start the cover" | **press 1**, at the instant the bottom edge leaves its rest; the press writes a stop at once | the slat time: the phase where the slats separate before the curtain travels | provisional |
| 3 | Lift-off check | none | answers what they see | whether press 1 was early, good, or late | corrects step 2 |
| 4 | Ascent, second run | closed again, then started by the user | **press 2**, at the instant the motor stops at the top | the full opening time | provisional |
| 5 | Curtain travel | none (the cover is open) | tape reading: base to bottom edge | the cover's own travel in cm | `travel_cm` |
| 6 | Descent | started by the user | **press 3**, when the motor stops at the bottom, slats closed | the full closing time | provisional |
| 7 | Half an ascent | automatic, ends by itself | tape reading | the opening roll coefficient | provisional |
| 8 | Half a descent | automatic, ends by itself | tape reading | the closing roll coefficient | provisional |

Step 3 is the one that repays explaining. Pressing at lift-off sends a stop
immediately, so the curtain comes to rest a few centimetres up and the screen asks what
the user sees. *Still on its rest* means the press went in before the edge moved: that
cannot be repaired and the run is repeated. *A few centimetres up* is a good press.
*A hand's breadth or more* is a late press, and measuring that gap with the tape puts
the instant back where it belongs: the curtain travelled that distance between the real
lift-off and the motor stopping, so the correction is arithmetic rather than a guess
(`t_lift = t_stop − gap / v0`, with `v0` the speed at the bottom derived from the run
time and the roll). If the gateway held the stop back — a busy command queue — the
screen says so, because then the gap is not the user's reaction.

Steps 7 and 8 are the **tape phase**: runs that end by themselves, with nothing to press
while they happen. One screen announces them together, says how many readings follow and
asks the user to stand clear; from there the cover positions itself between readings.
Their order is not fixed: each reading runs to its percentage from an end stop, and the
one that starts where the cover already stands is taken first, which saves a full run.

**Where the choice between the two levels happens.** After step 8 the basic
calibration is complete and the summary shows what it found. That screen is a fork with
three ways out: **save** (the cover is calibrated and usable, within about 4 cm), 
**continue with the thorough calibration**, or cancel. Choosing to continue does not
restart anything: the presses are not repeated, and the five extra readings are fitted
over the times already measured. So the user decides *after* seeing a result, not before
starting, and someone who only wants a working shutter never sees the longer path. The
same fork appears at the end of a correction (path C, first two scopes), for the same
reason and with the same effect.

At the end it asks for a profile name and stores two things: the **profile** (reference
travel, opening and closing time, slat time, one roll coefficient per direction) and the
same numbers as **this cover's own values**, so the measured cover runs on them whatever
the configuration file says.

#### Path B — a cover similar to one already measured

Three screens, one tape reading, two movements. Pick the profile, open the cover fully,
measure the travel. It stores the assignment and the travel and **no numbers of its own**:
from then on the cover follows the profile, scaled to its travel, and a later correction
of the profile reaches it.

It then offers a **check**: the cover is sent to half its travel and the user measures
where it really stopped. What the gap means depends on how the profile itself was
measured, and this is a place where my own implementation states it too simply today:
a profile measured at the basic level is worth about 4 cm to begin with, so a 3 cm gap
on a cover following it says nothing about that cover; a profile measured thoroughly is
worth about 1 cm, and there the same 3 cm is a real signal. So the contract should carry
the accuracy of a profile alongside its values (the gap its own check reported, or the
fact that it never had one), and the threshold offered here should be read against that
figure rather than against a constant. When the gap does exceed it, the screen offers
path C on the spot.

#### Path C — a cover that has a profile but stops in the wrong place

For a slower motor, a heavier curtain, a fatter tube. Three scopes:

- **Times only** — three presses, about two minutes. For a motor that is simply faster
  or slower than the one the profile was measured on.
- **Times and rolls** — the same three presses plus three readings (travel, and one at
  half the travel in each direction). Eight movements. This is what a cover needs when
  it misses *at mid-travel*, which is the curtain winding differently rather than the
  motor running differently.
- **Thorough only** — no timed run at all: four readings, at a quarter and at three
  quarters of the travel in each direction, plus the check. Ten movements. It keeps
  whatever times the cover runs on today and fits the two roll coefficients over them,
  and it stores **only those two**: nobody pressed anything, so the times are not
  claimed as this cover's own measurement and go on coming from the profile, which means
  a later correction of the profile still reaches this cover.

Only the keys actually measured are stored, merged into whatever was already there. A
correction also confirms which profile this cover starts from, so the profile keeps its
place above the keys the configuration file writes for it.

#### The two levels, concretely

**Basic** is the path A table: three presses, three readings (the lift-off gap is an
optional fourth). One reading per direction fixes that direction's roll exactly, so
there is nothing left over to be an error and the summary reports no accuracy figure —
it says so rather than showing a dash. On the covers I have measured this lands within
about 4 cm.

**Thorough** is not a different procedure but the continuation of the basic one, chosen at its summary. It adds about two minutes and five readings: a quarter and three quarters of
the travel in each direction, plus the check. With three points per direction the fit
solves the roll **and** a scale factor on the run times at the same time, and that scale
factor is what absorbs the reaction time of the presses: the tape corrects the finger.
This is why the thorough level is not merely "more precision", it is what makes a
button-press measurement trustworthy. It lands within about 1 cm.

It closes with a **check at 40 % of the descent**, deliberately a position nothing was
fitted to, so it is a question put to the model rather than a repetition of its inputs.
The gap reported there is the accuracy the summary names: "within X cm", measured at the
one position the fit never saw.

#### Two details that carry the whole thing

- **Every reading form prints the value the model expects** next to the field: "about
  49 cm; anything within 3 cm is normal" during a thorough calibration, and a much
  looser figure during a basic one, where the expectation comes from the geometry of an
  ordinary shutter rather than from a model of this cover. A reading taken from the
  wrong reference point shows up while the user is still standing at the window.
- **Every measurement can be repeated on the spot.** The confirmation screen after a
  press or a reading offers "Repeat the measurement", which redoes only that step: the
  cover is taken back to the end stop that step starts from and the run is made again,
  and nothing already collected is touched. After a reading it also offers "It did not
  do what it should", for a cover that never moved or moved the wrong way: that stops
  whatever is moving, throws the reading away and repeats the step's movements.

#### What this asks of the API

Nothing exotic, but four things a linear session does not need:

1. a step type that says **"drive to fraction f of the travel from end stop E, then ask
   for a reading in cm"**, with the expected value and its tolerance returned alongside
   the prompt;
2. a **fit** step that takes the readings and returns times, slat time and rolls, with
   the residual at each point, so the client can show what it found rather than a number
   out of nowhere;
3. a **check** result that carries the predicted position, the measured one and the gap,
   which is the accuracy figure a user is entitled to see before saving;
4. **repeat this step** as a first-class transition, not a cancel-and-start-again.

### 2.6 Refusals the session needs

`already_calibrating`, `unknown_cover`, `cover_unavailable`, `advanced_cover` (an
actuator that reports its own position has nothing to calibrate), `not_delivered` (the
frame never reached the bus), `no_echo` (the actuator never reported movement),
`not_stopped`, `timeout` (no press in time), `bad_reading` (a tape value that cannot be
true for this cover), `lease_expired`, `revision_conflict`.

A refusal carries a stable machine code and never a partially written result: a session
that fails stores nothing.

### 2.7 Writes

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
