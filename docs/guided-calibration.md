# Guided shutter calibration

A dialog that measures one shutter and writes the result where the integration
reads it. It replaces the tape-and-action procedure of
[Recipes → Calibrating a shutter in centimetres](recipes.md#calibrating-a-shutter-in-centimetres)
for everything except the cases that recipe still covers better: it asks for the
same measurements, does the arithmetic itself, and keeps the numbers inside Home
Assistant instead of asking you to paste them into a file.

Available since **0.5.0**.

## Contents

- [What it is for](#what-it-is-for)
- [Where to find it](#where-to-find-it)
- [The three paths](#the-three-paths)
- [The two levels](#the-two-levels)
- [How timing by button press works](#how-timing-by-button-press-works)
- [The management screens](#the-management-screens)
- [Where the data lives](#where-the-data-lives)
- [Idle timers and expired sessions](#idle-timers-and-expired-sessions)
- [Troubleshooting](#troubleshooting)

## What it is for

Only for **basic** covers — the ones whose actuator never reports where it is. On
those the percentage Home Assistant shows is an estimate computed from the run
times and the shape of the roll on the tube; the calibration measures those times
and that shape on your own shutter, so the estimate describes it rather than an
average of every shutter. Covers declared `advanced: true` report their real
position and have nothing to calibrate: they are not listed, and on a gateway with
no basic cover at all the menu item is not shown.

It does not make the estimate exact. What to expect afterwards:

- **1–2 cm** on runs that start or end at an end stop;
- **2–4 cm** between two intermediate positions, where neither end of the run
  re-synchronises anything.

Nothing drifts across runs: a basic actuator reaches `0` and `100` by running into
the physical end stop, not by a timer, and every full open or close puts the
estimate back on a known point. An error at mid-travel is the worst case, not an
accumulating one.

## Where to find it

**Settings → Devices & services → MyHOME → Configure**, then **"Calibrate a
shutter"**. There is nothing to add on the integration page and nothing to install:
the whole thing — the guided measurement, what it stored, and the connection
options that used to be the only content of that button — is behind **Configure**.

```
Configure
├── Calibrate a shutter        (only when the gateway has a basic cover)
├── Profiles and shutters
├── Calibrations
├── Gateway and connection
└── Close
```

Nothing moves until a screen announces it, nothing is written until the last
screen, and closing the dialog at any point — including with the X — leaves the
configuration exactly as it was. The movements the dialog makes are ordinary
commands; a shutter it has already moved stays where it is.

While a guided step owns a shutter the entity publishes `Calibrating: true` and
refuses `cover.set_cover_position`: two things timing the same motor would each
measure a run the other one stopped. `cover.open_cover`, `cover.close_cover` and
`cover.stop_cover` are not refused — the steps themselves use them.

Have a tape measure to hand, stand in front of the shutter you are measuring, and
bring the phone or the laptop with you: several screens ask you to watch the
shutter and press a button at a precise instant.

## The three paths

The second screen asks which shutter, the third how to measure it. The three are
alternatives, not steps.

### (A) The first shutter of this kind

The full measurement: seven movements, about three minutes, three button presses
and three tape readings.

| Step | What it measures |
|---|---|
| Close completely | Nothing — it gives every later measurement a known starting point |
| Timed ascent | The slat time (first press, the bottom edge leaving the base) and the full upward run (second press, the motor stopping at the top) |
| Height | The curtain travel, base to bottom edge with the shutter fully open |
| Timed descent | The full downward run (one press, the motor stopping at the bottom) |
| Half a descent | The roll coefficient going down |
| Half an ascent | The roll coefficient going up |

Before the summary it asks for a **profile name** — letters, digits and
underscores, no spaces and no accents, because it is also a key of the
configuration file. What it stores at Save:

- a **profile** under that name: reference height, opening and closing time, slat
  time, and one roll coefficient per direction. That is the description of the
  *kind* of shutter, and it is what path B hands to every other shutter like it;
- the same numbers as **this shutter's own values**, so the shutter that was
  measured runs on them whatever the configuration file says about it.

A name that is already in use **replaces** that profile, which is how a first
measurement that went badly is corrected. A `cover_profiles:` block of the same
name in the configuration file is not touched; it goes on being shadowed by the
stored one for as long as that one exists.

### (B) Similar to a shutter already measured

Pick the profile, measure the height, done — two screens and one tape reading. The
shutter is opened completely first, because the height is the distance the bottom
edge travels and that only means the whole travel when it is measured from the top.

It then offers a **check**: the shutter is sent to half its travel and you measure
where it really stopped. The screen reports the gap between that and where the
estimate put it. One or two centimetres is normal and already a good
approximation; three or more mean this shutter does not behave like the profile it
was given, and the screen offers path C on the spot.

What it stores: the profile name and the height — no numbers of its own. From that
moment the shutter **follows** the profile, run times included, scaled to its own
height, and the profile's values are used **instead of** the ones the configuration
file writes for that cover, if you use one: this is a statement about the shutter
made after the file was written, which a `profile:` named in the file is not.
`Calibration source` therefore says `profile <name>` for such a shutter. Correcting
the profile afterwards — in `cover_profiles:` or from **Profili e tapparelle →
Modifica i valori** — reaches this shutter too, at the next reload, scaled to its
own height; nothing of the profile was ever copied into it.

### (C) It has a profile but stops in the wrong place

For a shutter that was given a profile and does not behave like it: a slower motor,
a heavier curtain, a fatter tube. It asks how far to go:

- **its own run times** — two presses, about a minute. Enough for a shutter whose
  motor is simply slower or faster than the one the profile was measured on;
- **its run times and its own roll coefficients** — the same two presses plus two
  tape readings. What a shutter needs when it misses *at mid-travel*, which is not
  the motor running differently but the curtain winding differently.

Only the keys it actually measured are stored, and only for this shutter — merged
into whatever was already stored for it, so the height and any other override this
run did not re-measure stay exactly as they were. Everything still not covered
goes on coming from the profile.

## The two levels

Path A ends on a summary and an offer.

**Basic** — what the path A table above measures: three button presses and three
tape readings. One reading per direction fixes that direction's roll exactly, so
there is nothing left over to be an error: the summary has no accuracy line, and
says so rather than showing a dash.

**Precise** — about two more minutes and four more tape readings, at a quarter and
three quarters of the travel in each direction. With three points per direction the
fit solves the roll **and** a scale factor on the run times at the same time, which
is what absorbs the reaction time of the button presses: the tape corrects the
finger. Under each field the form prints the value the model expects
("about 49 cm; anything within 3 cm is normal"), so a reading taken from the wrong
reference point shows up while you are still standing there.

It closes with a **verification at 40 % of the descent** — deliberately a position
no measurement was fitted to, so it is a question put to the model rather than a
repetition. The precise summary reports the answer as "within X cm, verified at
40 %".

At the basic level the same expected-value line is drawn from the default geometry
of an ordinary shutter rather than from a model of yours, so it promises much less:
anything within 15 cm is normal there.

After every measurement — the presses as well as the tape readings — a confirmation
screen shows the value that was just taken and offers **"Repeat the measurement"**.
Repeating a step redoes only that step: the shutter is brought back to the end stop
that step starts from and the run is made again, and nothing already collected is
touched.

## How timing by button press works

There is no stopwatch anywhere in this procedure, and that is the point.

The integration already knows when the motor **starts**: the actuator answers a
direction command with its own "moving" status about half a second later, and the
step waits for it (up to three seconds from the moment the gateway reports the
frame written). What is left is when the motor **stops**, which nothing on the bus
reports precisely enough, and that is the button. One human reaction per
measurement instead of two, and no object to hold but the tape.

The screens are built around that:

- **Nothing moves by itself on a step with a press.** The instructions arrive
  first, in full — including that you will have to be quick — and the shutter
  starts when you press **"1) Start the shutter"**.
- **The screens shown while it is moving carry one line and a button.** Nobody
  reads three paragraphs while watching a shutter.
- **The automatic runs of the tape steps do start on their own**: there is nothing
  to press during them, only something to measure afterwards.
- A press that never comes is not believed: after about ninety seconds the step is
  abandoned with an explanation and a way to repeat it.

Two things are worth knowing before the descent: do **not** press when the bottom
edge touches the base. The motor keeps running for a moment after that, to close
the slats, and the press means the instant it stops altogether — recognisable
because the noise stops. And a press that went half a second astray moves the
estimate by a few centimetres, so repeating the measurement is always better than
guessing.

The screens that ask for a press, and the ones that ask for a tape reading, carry a
small diagram of what to look at.

## The management screens

### Profiles and shutters

**Assign a profile to each shutter** — one selector per basic cover, with
"No profile (the file's values, or the defaults)" at the top. Only rows that really
changed are written; submitting the form with nothing changed writes nothing at
all, on any row. A shutter newly assigned to a profile whose height nobody knows is
asked for it in a follow-up form: a profile is the measurement of a shutter of a
certain height and there is nothing to scale it by without one.

A shutter the configuration file itself gives a `profile:` opens this form already
selected on that profile, so choosing it again changes nothing on the row and
writes nothing — the shutter goes on running under the file's own order, where a
key the file writes for it still wins over the profile it names. To make it follow
that profile from above the file's keys, move the row to another profile and back,
or measure the shutter instead.

Dropping the assignment back to "No profile" removes the name and the numbers that
came with the profile. The height stays — somebody held a tape against that shutter
— and so does anything paths A or C measured on it.

**View, edit or delete a profile** — the profile's own screen lists the shutters
that follow it and offers:

- **View the values** — reference height, run times, slat time, both rolls, and
  which shutters follow it. Changes nothing;
- **Edit the values by hand** — a prefilled form. For the numbers you know better
  than the measurement did, the manufacturer's declared times for instance.
  Correcting a profile reaches every shutter that follows it at the next reload,
  scaled to each one's own height, and never touches an override paths A or C
  measured;
- **Delete the profile** — a confirmation screen that names the shutters that use
  it. They go back to the configuration file, if you use one, or to the defaults;
  their own measurements stay. A `cover_profiles:` entry of the same name in the
  file, until then shadowed, applies again from that moment.

A profile that lives in the configuration file is shown here and left alone: its
menu offers "View the values" and nothing else. The file is yours, and an edit that
silently created a stored profile shadowing it from then on would be the wrong kind
of help.

### Calibrations

One entry per shutter the integration is keeping something for:

- **View the values** — what is stored, key by key. What is listed beats the
  configuration file; what is not listed goes on coming from the file, the profile
  or the defaults;
- **Edit the values by hand** — a prefilled form, per shutter. A field left empty
  is not a zero: it means "nothing to say about this one", and the value goes back
  to coming from the profile or the file. Emptying the form deletes the record;
- **Measure again** — the guided calibration on that shutter. Path A or C merges
  into what is already stored, keeping the height and any override this run did
  not re-measure; picking a profile (path B) replaces the shutter's own measured
  overrides with the profile assignment instead;
- **Delete** — a confirmation, then back to the file or the profile. The
  measurements cannot be recovered: getting them back means measuring again.

### Gateway and connection

The form **Configure** used to open on, unchanged: address, port, password, the
path of the configuration file, the number of command sessions, the event option
and the session tunables. Saving it reloads the integration, as before.

## Where the data lives

In Home Assistant's own storage, one file per gateway (`myhome.calibration.<entry
id>` under `.storage`), never in `myhome.yaml`: the integration does not write your
configuration file. It holds two things — the **profiles** and, per shutter, its
**assignment, height and measured values**.

### Precedence

Per key, highest first:

1. the values the guided calibration stored **for that shutter** — path A, or
   **(C) Affina la calibrazione** measured on it directly;
2. a profile **assigned** to the shutter — from **Profili e tapparelle**, or chosen
   with path B — scaled to the shutter's height. This is a statement about that
   shutter made after the configuration file was written, so it is used **instead
   of** the keys the file writes for that cover;
3. the key as written for that cover in the **configuration file**, if you use one
   (including what the file implies: `roll:` stands for both directional rolls,
   `opening_time:` for `closing_time:`). A `profile:` the file itself gives a cover
   is not the statement rule 2 is and does not move here: a key the file writes for
   that cover still wins over the profile it names;
4. the file's own profile chain (the `profile:` it names, scaled to the height) and
   then the **defaults**.

A measurement of one shutter is more specific than a line typed about all of them,
which is why rule 1 beats everything else; an assigned profile is a statement about
that one shutter too, made after the file, which is why rule 2 beats rule 3; the
file's own `profile:` is not such a statement, which is why rule 4 does not beat
rule 3. Stored profiles and `cover_profiles:` share one namespace, and a stored
profile of the same name wins — the log says so once per name.

Nothing of an assigned profile is copied into the shutter's stored calibration:
only the name, the flag and the height are. Correcting the profile — in
`cover_profiles:` or from **Profili e tapparelle → Modifica i valori** — reaches
every shutter that follows it at the next reload, scaled to each one's own height.
Deleting it takes the assignment away and leaves the height and any measurement
alone; the shutter goes back to what the file says.

The `Calibration source` attribute of every basic cover says which of these it is
running on:

| Value | Meaning |
|---|---|
| `guided` | This shutter was measured (path A or C) — including one that was assigned a profile and then refined, since the refinement is the measurement — or its stored values were edited by hand |
| `profile <name>` | It follows that profile — assigned from the assignment form or by path B — and was not measured itself |
| `yaml` | Nothing is stored for it: the configuration file, the file's profile chain, or the defaults |

A calibration naming a profile that no longer exists logs a warning and falls back
to the file: a shutter does not stop working because a name changed.

### Deleting

Deleting a **calibration** returns that shutter to the configuration file, the
profile it follows, or the defaults. Deleting a **profile** returns every shutter
that followed it to the same, keeps their heights, and un-shadows a
`cover_profiles:` entry of that name. In both cases what is deleted is the
integration's copy: your configuration file is not touched, and neither is
anything you measured on another shutter.

### If you keep everything in the file

Every summary prints the `myhome.yaml` equivalent of what it measured, with the
profile name you chose — which is why the name is asked for before the summary and
not after. Copy it before closing: without Save nothing is kept.

```yaml
gateway:
  mac: "00:03:50:AA:BB:CC"

  cover_profiles:
    tall:
      reference_height: 195
      opening_time: 22.3
      closing_time: 21.7
      slat_time: 4.7
      closing_roll: 1.69
      opening_roll: 2.12

  cover:
    living_room_shutter:
      where: "81"
      name: "Living Room Shutter"
      profile: tall
      height: 195
```

Saving and pasting are not exclusive, but they are redundant: the stored values
beat the file key by key, so a shutter carrying both runs on the stored ones until
they are deleted.

## Idle timers and expired sessions

A browser tab that is simply closed — a laptop that sleeps, a phone that kills the
tab — tells nobody, and the dialog would otherwise hold the shutter for the rest of
the Home Assistant run. So a conversation that sits on one screen too long gives
the shutter back:

- **30 minutes** on a screen with nothing moving. Reading three paragraphs, being
  interrupted by the doorbell and coming back is an ordinary thing to do;
- **10 minutes** on a screen that follows a movement, where somebody is standing in
  front of a shutter with a tape in their hand.

Expiring does not abort anything on the spot and never leaves Home Assistant
showing "Invalid flow specified": the shutter is released (and stopped, if it was
still moving), and the next thing you click lands on a screen that says the session
expired through inactivity, that nothing was saved, and offers to start again or to
close. The measurements taken so far are gone — they were never written anywhere.

The same screen appears if the integration is reloaded, or its configuration
re-read, while a dialog is open.

## Troubleshooting

**"The shutter did not answer."** The command reached the bus but the actuator
never reported that it had started, so there is no instant to measure against and
the step was abandoned. The motor has most likely started all the same: a stop was
sent right after the error, but check the shutter is not still running before
repeating the step. Check too that nothing else is holding it — a wall pushbutton,
an automation. If it happens every time, that actuator does not report its own
status and the guided calibration cannot measure it; the
[action-based recipe](recipes.md#calibrating-a-shutter-in-centimetres) still can.

**"The command never reached the bus."** The gateway neither wrote the frame nor
said it had given up on it. Check the connection on the integration page and repeat
the step.

**The press went in late, or was missed.** Repeat the step rather than accepting
the number: that is what the confirmation screen after every measurement is for.
Half a second of reaction is a few centimetres of shutter. Going on to the precise
level also helps — the scale factor it fits absorbs a systematic reaction delay.

**The two presses are refused as impossible.** The instants do not hold together: a
shutter cannot stop before it starts, or open its slats after arriving. One press
per event, at the moment it happens.

**"This shutter is already being calibrated."** Another dialog is open on it, or
`myhome.cover_calibration_run` is driving it. Finish or close that one first.

**The verification is more than 3 cm out.** On path B that means this shutter does
not behave like the profile it was given; measure it on its own with path C, which
the verification screen offers directly. On a shutter measured with path A it means
one of the readings was taken from a different reference point — measure every
centimetre from where the bottom edge rests when the shutter is closed, not from
the floor or a sill when those differ — or that the shutter needs the precise level.

**A constant offset at every position and in both directions** is a reference
mismatch, not a bad model. An error that grows with the length of the run is the
times or the roll.

**Nothing appears under "Calibrate a shutter".** Every cover of that gateway is
declared `advanced: true`, or none is declared at all. Advanced actuators report
their own position and have nothing to calibrate.

**The shutter still runs on the old numbers.** The values reach it when the dialog
is closed, which is when the entry is rebuilt — once, and only if something was
stored. Check `Calibration source` in **Developer tools → States** afterwards.

See also [Troubleshooting → Cover position issues](troubleshooting.md#cover-position-issues)
for the symptoms that are not about the calibration dialog at all.
