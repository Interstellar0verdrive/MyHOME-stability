# Guided shutter calibration

A guided conversation that measures one shutter and writes the result where the
integration reads it. It replaces the tape-and-action procedure of
[Recipes → Calibrating a shutter in centimetres](recipes.md#calibrating-a-shutter-in-centimetres)
for everything except the cases that recipe still covers better: it asks for the
same measurements, does the arithmetic itself, and keeps the numbers inside Home
Assistant instead of asking you to paste them into a file.

Available since **0.5.0** as a dialog under *Configure*. Since **0.6.0** the same
conversation also runs in the [Profiles and covers panel](panel.md), which is where
its buttons lead from; the dialog is unchanged and remains a complete alternative.
This page describes the measuring itself, which is the same on both — the routes, the
presses, the readings and the arithmetic. Where the two differ it says so.

## Contents

- [What it is for](#what-it-is-for)
- [Where to find it](#where-to-find-it)
- [The three paths](#the-three-paths)
- [The two levels](#the-two-levels)
- [How timing by button press works](#how-timing-by-button-press-works)
- [The management screens](#the-management-screens)
- [The panel, for the same job on one page](#the-panel-for-the-same-job-on-one-page)
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

It does not make the estimate exact. What to expect afterwards, on an ordinary
shutter — a promise this document keeps deliberately modest, because it has to hold
on installations nobody here has seen:

- **about 4 cm** after the basic calibration;
- **about 2 cm** after the thorough one;
- **less than either** on runs that start or end at an end stop, which
  re-synchronise the estimate by themselves.

Nothing drifts across runs: a basic actuator reaches `0` and `100` by running into
the physical end stop, not by a timer, and every full open or close puts the
estimate back on a known point. An error at mid-travel is the worst case, not an
accumulating one.

## Where to find it

Two doors onto the same conversation.

**In the panel** (since 0.6.0): *Profili e tapparelle* → **Measure a cover**, which
asks which shutter, or **Measure again** / **Correct…** on a shutter's own card, which
do not have to ask. The measurement then runs on that page, at
`/myhome-calibration#/calibrate`. This is the route the panel's own buttons take, and
the one this page's screenshots of a full page belong to.

**In the dialog**: **Settings → Devices & services → MyHOME → Configure**, then
**"Calibrate a cover"**. There is nothing to add on the integration page and nothing
to install: the whole thing — the guided measurement, what it stored, and the
connection options that used to be the only content of that button — is behind
**Configure**.

```
Configure
├── Calibrate a cover          (only when the gateway has a basic cover)
├── Profiles and covers
├── Calibrations
├── Gateway and connection
└── Close
```

Nothing moves until a screen announces it, nothing is written until the last
screen, and closing the dialog at any point — including with the X — leaves the
configuration exactly as it was. That is also the way out of a screen showing a
progress bar, which by design carries no Cancel button of its own: Home Assistant
draws none on a progress step, and a movement already under way is heading for an
end stop anyway. The movements the dialog makes are ordinary commands; a shutter it
has already moved stays where it is. A run still under way when you cancel or close
is not cut short — it ends at the end stop it was heading for — while a session that
expires through inactivity does send a stop (see
[Idle timers and expired sessions](#idle-timers-and-expired-sessions)).

In the panel the same holds with one difference: **closing the page is not closing the
conversation**. The measurement lives on the gateway, so the tab can be closed and the
calibration picked up again from another one; *Leave the calibration* is what throws it
away, and it asks first whenever there is something to throw.

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

### (A) It is the first cover of its kind

The full measurement: eight movements, about four minutes, three button presses and
three tape readings (four if you take the optional one).

| Step | What it measures |
|---|---|
| Close completely | Nothing — it gives every later measurement a known starting point |
| Timed ascent, first run | The slat time. One press, at the instant the bottom edge leaves the base; the dialog stops the shutter on that press, a few centimetres up |
| The lift-off check | Nothing by itself: it asks where the bottom edge ended up, and offers an optional tape reading of the gap that makes the lift-off instant exact |
| Timed ascent, second run | The full upward run. The shutter is closed again, started again and left to run; one press, at the instant the motor stops at the top |
| Curtain travel | Base to bottom edge with the shutter fully open |
| Timed descent | The full downward run (one press, the motor stopping at the bottom) |
| Half an ascent | The roll coefficient going up |
| Half a descent | The roll coefficient going down |

The last two are the **tape phase**: runs that end by themselves, with a reading to
take afterwards and nothing to press while they happen. One screen warns before the
first of them, and from there the shutter moves between the readings on its own. Their
order is not fixed: each reading runs to its percentage from one end stop, and the one
that starts where the shutter already stands is taken first. The timed descent leaves
it at the bottom, so the ascent is read first and the shutter is opened completely once,
between the two readings, instead of twice.

Before the summary it asks for a **profile name** — letters, digits and
underscores, no spaces and no accents, because it is also a key of the
configuration file. What it stores at Save:

- a **profile** under that name: reference travel, opening and closing time, slat
  time, and one roll coefficient per direction. That is the description of the
  *kind* of shutter, and it is what path B hands to every other shutter like it;
- the same numbers as **this shutter's own values**, so the shutter that was
  measured runs on them whatever the configuration file says about it.

A name that is already in use **replaces** that profile, which is how a first
measurement that went badly is corrected. A `cover_profiles:` block of the same
name in the configuration file is not touched; it goes on being shadowed by the
stored one for as long as that one exists.

### (B) It is similar to a cover already measured

Pick the profile, measure the curtain travel, done — three screens and one tape
reading. The shutter is opened completely first, because the curtain travel is the
distance the bottom edge runs and that only means the whole of it when it is measured
from the top;
that opening is announced by the same warning screen the tape phase of path A opens
with, and then happens by itself.

It then offers a **check**: the shutter is sent to half its travel and you measure
where it really stopped. The screen reports the gap between that and where the
estimate put it. One or two centimetres is normal and already a good
approximation; three or more mean this shutter does not behave like the profile it
was given, and the screen offers path C on the spot.

What it stores: the profile name and the curtain travel — no numbers of its own. From
that moment the shutter **follows** the profile, run times included, scaled to its own
travel, and the profile's values are used **instead of** the ones the configuration
file writes for that cover, if you use one: this is a statement about the shutter
made after the file was written, which a `profile:` named in the file is not.
`Calibration source` therefore says `profile <name>` for such a shutter. Correcting
the profile afterwards — in `cover_profiles:` or from **Profiles and covers → Edit
the values by hand** — reaches this shutter too, at the next reload, scaled to its
own travel; nothing of the profile was ever copied into it.

### (C) It has a profile but stops in the wrong place

For a shutter that was given a profile and does not behave like it: a slower motor,
a heavier curtain, a fatter tube. It asks how far to go:

- **its own run times** — three presses, about two minutes. Enough for a shutter
  whose motor is simply slower or faster than the one the profile was measured on;
- **its run times and its own roll coefficients** — the same three presses plus
  three tape readings: the curtain travel, and one at half the travel in each
  direction. What a shutter needs when it misses *at mid-travel*, which is not
  the motor running differently but the curtain winding differently. Eight
  movements;
- **Thorough calibration only** — no timed run at all: four tape readings, at a
  quarter and at three quarters of the travel in each direction, and the check that
  closes them. Ten movements. For a shutter that has already been measured and whose
  times are right: it keeps every time that shutter runs on today — its own stored
  values, or the profile it follows scaled to its travel — and the readings fit the
  two roll coefficients over them. It stores **only those two**: nobody pressed
  anything here, so the run times are not claimed as this shutter's own measurements
  and go on coming from wherever they came from, which means a later correction of the
  profile still reaches this window like every other one that follows it. A curtain
  travel already known is not asked for again; one nobody has ever measured is asked
  for first, and costs no movement of its own, because the shutter has to be taken to
  the top for it in any case.

Only the keys it actually measured are stored, and only for this shutter — merged
into whatever was already stored for it, so the curtain travel and any other override
this run did not re-measure stay exactly as they were. Everything still not covered
goes on coming from the profile, and the shutter goes on following it: a correction
confirms which profile this shutter starts from, which is the same statement the
assignment form makes, so the profile keeps its place **above** the keys the
configuration file writes for this cover. A correction of the run times alone
therefore leaves `Calibration source` reading `profile <name>, adjusted`; only the
scope that covers all five keys leaves it reading `guided`.

The first two scopes end on a summary that offers **"Continue with the thorough
calibration"**, which is the third scope run there and then, on the times just
measured.

## The two levels

Path A ends on a summary and an offer, and so does a correction.

**Basic calibration** — what the path A table above measures: three button presses and three
tape readings (the lift-off gap is a fourth, and optional). One reading per direction fixes that direction's roll exactly, so
there is nothing left over to be an error: the summary has no accuracy line, and
says so rather than showing a dash.

**Thorough** — about two more minutes and five more tape readings: four at a quarter
and three quarters of the travel in each direction, and one more for the check that
closes it. With three points per direction the
fit solves the roll **and** a scale factor on the run times at the same time, which
is what absorbs the reaction time of the button presses: the tape corrects the
finger. Under each field the form prints the value the model expects
("about 49 cm; anything within 4 cm is normal"), so a reading taken from the wrong
reference point shows up while you are still standing there.

It closes with a **verification at 40 % of the descent** — deliberately a position
no measurement was fitted to, so it is a question put to the model rather than a
repetition. Its answer is the gap reported by the screen that follows the reading,
and it is the **accuracy** the thorough summary then names: "within X cm", measured
at the one position nothing was fitted to rather than over the readings the fit was
given.

At the basic calibration the same expected-value line is drawn from the default geometry
of an ordinary shutter rather than from a model of yours, so it promises much less:
anything within 15 cm is normal there.

After every measurement — the presses as well as the tape readings — a confirmation
screen shows the value that was just taken and offers **"Repeat the measurement"**.
Repeating a step redoes only that step: the shutter is brought back to the end stop
that step starts from and the run is made again, and nothing already collected is
touched. The confirmation of a tape reading also carries **"It did not do what it
should"**, for a shutter that never moved or moved the wrong way: nothing is confirmed
*before* the runs of the tape phase, so that is where they are reported. It stops
whatever is moving, throws the reading away and makes the step's movements again.

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
  starts when you press **"Start the cover"**.
- **The ascent asks for two presses, one on each of its two runs, and the descent
  for one.** The ascent's buttons are numbered — **"1) Press when the bottom edge
  leaves the base"** and **"2) Press when the motor stops at the top"** — because
  they are the first and second measurement of the same thing; the descent's single
  **"Press when the motor stops at the bottom"** carries no number.
- **The first ascent press is checked, and can be corrected.** Pressing it sends a
  stop at once, so the shutter comes to rest a little above the base and the next
  screen asks what you see. Still touching the base means the press went in before
  the edge moved: that one cannot be repaired, and the run is made again. A few
  centimetres up is a press that went well. A hand's breadth or more is a late
  press, and measuring the gap with the tape puts the instant back where it
  belongs — the curtain moved that distance between the real lift-off and the
  motor stopping, which is arithmetic rather than guesswork. If the gateway held
  the stop back — a busy command queue — the screen says so, because the gap is
  then not yours.
- **The screens shown while it is moving carry one line and a button.** Nobody
  reads three paragraphs while watching a shutter.
- **The automatic runs of the tape steps do start on their own**: there is nothing
  to press during them, only something to measure afterwards. They are announced
  together, once, by a screen that says how many readings follow and asks you to stand
  clear; after that they chain, each movement naming itself on the progress bar
  ("is being closed completely", "is being run up to about 50% of its travel").
- A press that never comes is not believed: after about ninety seconds the step is
  abandoned with an explanation and a way to repeat it.

Two things are worth knowing before the descent: do **not** press when the bottom
edge touches the base. The motor keeps running for a moment after that, to close
the slats, and the press means the instant it stops altogether — recognisable
because the noise stops. And a press that went half a second astray moves the
estimate by a few centimetres, so repeating the measurement is always better than
guessing.

The ascent's first briefing opens with one drawing showing both of its presses; the
press screen of each run, the briefing of the second run, and the lift-off check and
its gap form all repeat the one that belongs to them. The curtain-travel form and the
three tape-reading forms show where to hold the tape. The descent asks for the same gesture
as the second ascent press and carries no drawing of its own.

## The management screens

### Profiles and covers

**Give each cover a profile** — one selector per basic cover, with
"No profile (the file's values, or the defaults)" at the top. Only rows that really
changed are written; submitting the form with nothing changed writes nothing at
all, on any row. A shutter newly assigned to a profile whose curtain travel nobody knows is
asked for it in a follow-up form: a profile is the measurement of a shutter of a
certain travel and there is nothing to scale it by without one.

A shutter the configuration file itself gives a `profile:` opens this form already
selected on that profile, so choosing it again changes nothing on the row and
writes nothing — the shutter goes on running under the file's own order, where a
key the file writes for it still wins over the profile it names. To make it follow
that profile from above the file's keys, move the row to another profile and back,
or measure the shutter instead.

Dropping the assignment back to "No profile" removes the name and the numbers that
came with the profile. The curtain travel stays — somebody held a tape against that shutter
— and so does anything paths A or C measured on it.

**View, edit or delete a profile** — the profile's own screen lists the shutters
that follow it and offers:

- **View the values** — reference travel, run times, slat opening time, both rolls,
  and which shutters follow it. Changes nothing;
- **Edit the values by hand** — a prefilled form. For the numbers you know better
  than the measurement did, the manufacturer's declared times for instance.
  Correcting a profile reaches every shutter that follows it at the next reload,
  scaled to each one's own curtain travel, and never touches an override paths A or C
  measured;
- **Delete the profile** — a confirmation screen that names the shutters that use
  it, counting the ones it was assigned to here and the ones whose own `profile:`
  key in the file names it separately. They go back to the configuration file, if
  you use one, or to the defaults; their own measurements stay. A `cover_profiles:`
  entry of the same name in the file, until then shadowed, applies again from that
  moment — to the shutters whose own entry in the file names it. A shutter that was
  given the profile from this dialog alone is left following none.

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
- **Measure it again** — the guided calibration on that shutter. Path A or C merges
  into what is already stored, keeping the curtain travel and any override this run did
  not re-measure; picking a profile (path B) replaces the shutter's own measured
  overrides with the profile assignment instead;
- **Delete the calibration** — a confirmation, then back to the file or the
  profile. The
  measurements cannot be recovered: getting them back means measuring again.

### Gateway and connection

The form **Configure** used to open on, unchanged: address, port, password, the
path of the configuration file, the number of command sessions, the event option
and the session tunables. Saving it reloads the integration, as before.

## The panel, for the same job on one page

Since **0.6.0** everything under *Profiles and covers* and *Calibrations* also exists
as a full-page screen, **Profiles and covers**, which shows every basic cover of a
gateway grouped by the profile it follows instead of one selector at a time. Covers
are moved between groups by dragging, by a long press on a phone or from the
keyboard; the batch is reviewed with a before/after of the values each cover would
end up on, confirmed in one write, and undone from the strip that follows it. It has
a card per cover and a card per profile, with the same hand edit, the same removal
and the same deletion as the screens above.

It is admin only and its sidebar entry is hidden until somebody turns it on. The full
page is [Profiles and covers panel](panel.md).

**The measuring runs there too.** The three routes, the presses, the tape readings and
the arithmetic are the same — the panel asks the same questions of the same shutter and
gets the same numbers out of it. What it adds is that the conversation **lives on the
gateway rather than in the window it is being driven from**: closing the tab or locking
the phone does not end it and does not lose a reading, a second device can be told to
take it over, and the panel can close a *Configure* dialog that is holding a shutter it
wants. A dialog cannot do any of that, because a dialog is a flow inside one browser.

Two differences worth knowing, both of them deliberate:

- **What route (A) saves.** The dialog stores the profile **and** the same values on
  the shutter itself, so the shutter's origin reads *Measured*. The panel stores the
  profile and **assigns** the shutter to it, with nothing of its own, so the origin
  reads *Inherited from profile «…»* — which is what the published calibration contract
  asks for, and what makes every later correction of that profile reach this shutter
  too. The numbers the shutter runs on are the same either way, and **Save for this
  shutter only** is offered on both if that is what you want.
- **No undo after a save.** The panel's assignment screens offer *Undo* for a few
  seconds; a calibration does not, on either side. Three minutes of measuring are not a
  gesture to take back by accident, and the way back is *Remove the measurement…* on the
  shutter's card.

Everything else is one store seen twice: a change made in either is visible in the
other as soon as the screen is drawn again, and the dialog goes on working unchanged on
an installation where the panel cannot be loaded. Only one of the two may hold a shutter
at a time — whichever asks second is told who has it, and by which of them.

## Where the data lives

In Home Assistant's own storage, one file per gateway (`myhome.calibration.<entry
id>` under `.storage`), never in `myhome.yaml`: the integration does not write your
configuration file. It holds two things — the **profiles** and, per shutter, its
**assignment, curtain travel and measured values**.

### Precedence

Per key, highest first:

1. the values the guided calibration stored **for that shutter** — path A, or
   **(C) It has a profile but stops in the wrong place** measured on it directly;
2. a profile **assigned** to the shutter — from **Profiles and covers**, or chosen
   with path B — scaled to the shutter's curtain travel. This is a statement about that
   shutter made after the configuration file was written, so it is used **instead
   of** the keys the file writes for that cover;
3. the key as written for that cover in the **configuration file**, if you use one
   (including what the file implies: `roll:` stands for both directional rolls,
   `opening_time:` for `closing_time:`). A `profile:` the file itself gives a cover
   is not the statement rule 2 is and does not move here: a key the file writes for
   that cover still wins over the profile it names;
4. the file's own profile chain (the `profile:` it names, scaled to the travel) and
   then the **defaults**.

A measurement of one shutter is more specific than a line typed about all of them,
which is why rule 1 beats everything else; an assigned profile is a statement about
that one shutter too, made after the file, which is why rule 2 beats rule 3; the
file's own `profile:` is not such a statement, which is why rule 4 does not beat
rule 3. Stored profiles and `cover_profiles:` share one namespace, and a stored
profile of the same name wins — the log says so once per name.

Nothing of an assigned profile is copied into the shutter's stored calibration:
only the name, the flag and the curtain travel are. Correcting the profile — in
`cover_profiles:` or from **Profiles and covers → Edit the values by hand** —
reaches every shutter that follows it at the next reload, scaled to each one's own
travel. Deleting it takes the assignment away and leaves the curtain travel and any
measurement alone; the shutter goes back to what the file says.

The `Calibration source` attribute of every basic cover says which of these it is
running on:

| Value | Meaning |
|---|---|
| `guided` | **Measured**: every key of the travel model comes from this shutter's own stored values — path A, a correction that covered them all — or from values edited by hand. Nothing of a profile is in use |
| `profile <name>` | **Inherited**: it follows that profile — assigned from the assignment form or by path B — and was not measured itself |
| `profile <name>, adjusted` | **Adjusted**: both at once. Some keys were measured on this shutter and the rest still come from the profile, which is what a correction of the run times alone leaves behind |
| `yaml` | Nothing is stored for it: the configuration file, the file's profile chain, or the defaults |

Only the five keys a guided calibration can measure decide which of the first three
it is: `roll:` is the fallback of the two directional coefficients and is never what a
shutter that has both of them runs on.

The dialog says the same thing in words rather than in tokens, on every screen that is
about where a shutter's numbers come from — the **Calibrations** list, the action menu
and **View the values** under it, **Give each cover a profile**, the three screens that
close a calibration, and a profile's list of followers:

| On the screen | The attribute |
|---|---|
| **Measured** | `guided` |
| **Inherited from profile "name"** | `profile <name>` |
| **Adjusted from profile "name"** | `profile <name>, adjusted` |
| **From the file** | `yaml`, with the keys written in `myhome.yaml` |
| **Defaults** | `yaml`, with nothing written anywhere |

Five rather than four: `yaml` answers "the file or the store", which leaves "somebody
wrote these times" and "nobody ever said" under one word, and those are not the same
news to the person reading the screen. Both are decided in the same place as the
token, so a screen and an attribute cannot disagree about one shutter.

A calibration naming a profile that no longer exists logs a warning and falls back
to the file: a shutter does not stop working because a name changed.

### Deleting

Deleting a **calibration** returns that shutter to the configuration file, the
profile it follows, or the defaults. Deleting a **profile** returns every shutter
that followed it to the same, keeps their curtain travels, and un-shadows a
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
tab — tells nobody, and the conversation would otherwise hold the shutter for the rest
of the Home Assistant run. So one that sits on one screen too long gives the shutter
back, in the panel exactly as in the dialog:

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
re-read, while a calibration is open — including the reload the dialog itself does when
it is closed after saving, which ends a calibration the panel was holding on the same
gateway.

## Troubleshooting

**"The cover did not answer."** The command reached the bus but the actuator
never reported that it had started, so there is no instant to measure against and
the step was abandoned. The motor has most likely started all the same: a stop was
sent right after the error, but check the shutter is not still running before
repeating the step. Why the actuator stayed silent is not something the dialog can
tell — a shutter that something else was already driving is caught before the step
starts, and says **"The cover is already moving"** instead. If it happens every
time, that actuator does not report its own status and the guided calibration
cannot measure it; the
[action-based recipe](recipes.md#calibrating-a-shutter-in-centimetres) still can.

**"The command never reached the bus."** The gateway would not take the frame,
dropped it, or never said what became of it — which of the three is not something
the dialog can tell — so the shutter was never asked to move and nothing was
measured. Check the connection on the integration page and repeat the step.

**The press went in late, or was missed.** Repeat the step rather than accepting
the number: that is what the confirmation screen after every measurement is for.
Half a second of reaction is a few centimetres of shutter. Going on to the thorough
calibration also helps — the scale factor it fits absorbs a systematic reaction delay
— and on a shutter that has already been measured it can be run on its own, from
**(C) It has a profile but stops in the wrong place**, without timing anything again.

**A press is refused as impossible.** The instants do not hold together: a
shutter cannot stop before it starts, or open its slats after arriving. One press
per event, at the moment it happens.

**"This cover is already being calibrated."** Another dialog is open on it, a
calibration is running on it in the panel, or `myhome.cover_calibration_run` is driving
it. Finish or close that one first — the panel says which of the three it is, and can
close a dialog for you.

**The verification is more than 4 cm out.** On path B that means this shutter does
not behave like the profile it was given; measure it on its own with path C, which
the verification screen offers directly. On a shutter measured with path A it means
one of the readings was taken from a different reference point — measure every
centimetre from where the bottom edge rests when the shutter is closed, not from
the floor or a sill when those differ — or that the shutter needs the thorough
calibration.

**A constant offset at every position and in both directions** is a reference
mismatch, not a bad model. An error that grows with the length of the run is the
times or the roll.

**Nothing appears under "Calibrate a cover".** Every cover of that gateway is
declared `advanced: true`, or none is declared at all. Advanced actuators report
their own position and have nothing to calibrate.

**The shutter still runs on the old numbers.** From the dialog, the values reach it
when the dialog is closed, which is when the entry is rebuilt — once, and only if
something was stored. From the panel they reach it at the moment of the save, with no
rebuild at all. Check `Calibration source` in **Developer tools → States** afterwards.

See also [Troubleshooting → Cover position issues](troubleshooting.md#cover-position-issues)
for the symptoms that are not about the calibration dialog at all.
