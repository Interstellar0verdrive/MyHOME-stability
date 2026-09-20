# Profiles and covers panel

A full-page screen inside Home Assistant that shows every basic cover of a MyHOME
gateway grouped by the profile it follows, and lets you move covers between those
groups, correct what was measured and look after the profiles themselves. It is the
[guided calibration](guided-calibration.md) taken out of a dialog: the same stored
data, the same rules about what beats what, on a page you can see all of at once.

**Measuring a cover happens here too.** Every button that leads to a measurement —
*Measure a cover* on the overview, *Measure again* and *Correct…* on a cover's card —
opens the calibration on the page the user is already standing on, at
`/myhome-calibration#/calibrate`. The *Configure* dialog is unchanged and stays a
complete alternative for everything the panel does, measuring included; a calibration
held by that dialog is recognised for what it is and can be closed from here when it
is in the way.

Outside that calibration the panel only reads the bus: the management screens move
nothing.

Available since **0.6.0**. For the WebSocket commands behind it, see
[The panel's WebSocket API](panel-websocket-api.md).

## Contents

- [What it is for](#what-it-is-for)
- [How to open it](#how-to-open-it)
- [The overview](#the-overview)
- [Assigning covers to profiles](#assigning-covers-to-profiles)
- [Reordering](#reordering)
- [The cover detail](#the-cover-detail)
- [The profile card](#the-profile-card)
- [Measuring a cover](#measuring-a-cover)
- [When changes take effect](#when-changes-take-effect)
- [What the panel never does](#what-the-panel-never-does)
- [Troubleshooting](#troubleshooting)
- [Screenshots](#screenshots)

## What it is for

For the house with more than two or three shutters. One cover is measured well and
the others are told to follow it, and doing that in a menu — one selector per cover,
one screen at a time — hides the only thing worth looking at:
which covers are on which profile, and which ones are on nothing at all. The panel
draws that as groups, and assigning a cover is moving it from one group to another.

It is **admin only**, because a travel model is a setting rather than a state:
somebody who may open a cover has no business rewriting what "open" means. A
non-admin account does not see the entry in the sidebar editor and gets nothing at
the address.

Only **basic** covers appear. A cover declared `advanced: true` reports its real
position, has no travel model to correct, and is absent from the panel exactly as it
is absent from the guided calibration. A gateway whose covers are all advanced says
so in one sentence instead of showing an empty page.

## How to open it

The panel registers itself once per Home Assistant run, at
`/myhome-calibration`, and puts an entry in the sidebar — **hidden by default**. The
sidebar of a house is not the integration's to fill: the entry exists so it can be
turned on, and is invisible until somebody does.

**To show it**: open your own user page (click your name at the bottom of the
sidebar), find the sidebar settings there, and drag **Profili e tapparelle** up out
of the hidden items. The choice is per user — turning it on for yourself does not put
it in anybody else's sidebar, and a user who has already placed it keeps it across
upgrades.

That name is in Italian on purpose and is the one string on the whole page the
integration's translations cannot reach: a panel is registered once for the whole
installation rather than per user, so Home Assistant has no language to render its
sidebar title in. Inside, every sentence follows the language of whoever is looking
at it, and the page's own title reads **Profiles and covers**.

**By address**: `http://<your home assistant>/myhome-calibration` works whether or
not the sidebar entry is showing, which is the quickest way in if you only need it
now and then. The two cards have addresses of their own — the panel routes
`/myhome-calibration/cover/<unique id>` and `/myhome-calibration/profile/<name>` —
so a card can be bookmarked or linked from a dashboard. Opening one of those
addresses shows the overview with that card open over it, which is also what happens
when you open a card from the list: the list never goes away underneath.

**From the dialog**: the first screen of **Configure** ends with a line saying that
profiles and covers can also be managed from the panel, and the word *panel* in it is
a link straight to `/myhome-calibration`. It is the one route into the panel that
needs neither the sidebar entry nor a typed address, and it is the route somebody who
has just finished measuring a cover is already standing on.

Whether that link opens in this tab or another is the frontend's own behaviour for a
link inside a dialog and is not something this integration chooses. Either way the
panel re-reads the gateway every time it is looked at again, so a measurement made in
the dialog is on the screen without a reload.

**One gateway or several**: the header carries a gateway selector only when more
than one MyHOME gateway is configured. Switching gateway drops anything half-composed
on the screen, because the covers it names belong to the gateway being left.

## The overview

One card per profile, in the order the profiles are named, then a last group for the
covers that follow none — **No profile**, which is not a fault: a cover with
measurements of its own sits perfectly well there.

Each profile card carries three lines under its name: the values (reference travel,
ascent, descent and slat time), where the profile came from, and how many covers
follow it. The provenance line says *Measured on <cover> · <date>* when the store
recorded it, names the date alone when the cover it was measured on is no longer on
this gateway, and otherwise says **Where it was measured is not recorded.** — which
is what every profile stored before 0.6.0 says, and what one typed by hand says.
Nothing guesses.

A profile that a cover follows and nothing defines any more still gets a card,
marked: the covers under it have quietly fallen back to their own configuration, and
a list that made the name disappear would be a list that hides exactly that. A
profile written in the configuration file's `cover_profiles:` block is shown and
marked read-only from here; that file is yours and the integration does not write it.

### The origin chip

Every cover row carries a chip saying where the numbers it is running on come from.
Five states, the same five words the dialog uses and the same ones behind the
`Calibration source` attribute:

| Chip | What it means |
|---|---|
| **Measured** | every key of the travel model was measured on this cover, or typed for it by hand; nothing of a profile is in use |
| *Inherited from profile “name”* | it follows that profile, scaled to its own curtain travel, and was never measured itself |
| *Adjusted from profile “name”* | both at once: some keys were measured on this cover and the profile still answers for the rest, which is what a correction of the run times alone leaves behind |
| **From the file** | nothing is stored for it and `myhome.yaml` writes its keys |
| **Defaults** | nothing is stored for it and nothing is written for it anywhere |

Inside the group of the very profile a cover follows, the chip shortens to
**Inherited** or **Adjusted**: the heading above it already says which profile, and
repeating the name on every row of a group of twelve says nothing twice.

The chip is not worked out in the browser. It is the same answer the cover entity
publishes, computed once on the server by the one function both of them call, so the
page and the attribute cannot disagree about a cover.

Under the name, each row says the room it is in and its curtain travel — or that the
travel is not recorded, or that it is one the next confirmation will ask for.

### Finding a cover

Two controls above the groups: **Search for a cover**, which matches the name, and
**Filter by room**, whose first entry is **All rooms**. They filter the rows inside
the groups rather than flattening them, so what is on screen is always the same
picture. The room comes from the entity's own area, or from its device's; a cover
that has neither is not hidden by the filter's absence of an answer, it simply has no
room to be filtered by.

### The first run

A gateway with no profile at all does not show an empty list. It shows **No profile
yet**, a paragraph on what a profile is, and **Measure a cover**, which opens the
calibration here and asks which shutter to measure. When it is done the profile
appears here.

## Assigning covers to profiles

Moving a cover from one group to another is assigning it. There are three ways in,
and they compose the same change:

- **On a desktop**, drag the row by its handle. The target group is outlined, an
  insertion line shows where the row would land, and a fixed **Take out of the
  profile — drop here** zone appears for the length of the drag. `Esc` cancels.
- **On a phone**, press and hold the row for about half a second. The groups collapse
  to their titles, and a tap on one of them moves the cover to the end of it. There
  is no dragging below 600 px of width: a long press that scrolls the page instead of
  picking a row up is worse than a tap.
- **With the keyboard**, `Enter` or `Space` on the handle opens **Which profile?** —
  the list of profiles plus **No profile**, with the current one marked. This is a
  complete third path, not a fallback: everything the other two can compose, it can.

### Pending changes

**Nothing is written by any of the three.** A moved cover carries a chip saying where
it would go, and a bar at the foot of the page counts the changes and says that
nothing is written yet. Each pending change can be withdrawn on its own with
**Withdraw this change**, and the whole batch with **Discard everything**. Moving a
cover back to the group it started in withdraws its change rather than recording a
second one, so the count on the bar is the number of things the write would really
do.

The pending changes survive the page being refreshed underneath them: if somebody
else assigns a cover in another browser tab while a batch is half composed here, the
groups are redrawn from the new data with the pending changes laid back over them.

### Review and confirm

**Review and confirm** opens a panel from the right — a sheet from the bottom on a
phone — with one card per cover: its name, where it is going, and a **Before** / **After**
table of the values it would end up running on. The "after" column is not arithmetic
done in the browser: the server is asked what each cover would resolve to if the
batch were written, and answers with the profile already scaled to that cover's own
travel.

Each card carries the sentence that matters for that cover:

- one with values of its own for everything is told that nothing changes — the
  profile would only count for values removed later on;
- one with some values of its own is told that those stay and only the inherited
  values change;
- one leaving a profile is told whether the configuration file's values come back or
  the defaults do, and that its travel and its own values stay either way.

**The missing travels.** A profile is the measurement of one cover of a certain
travel, brought to the others in proportion, so a cover whose travel nobody knows
cannot be given one. The review panel collects them in a form of its own — **How far
does the curtain of these covers run?** — with one **Curtain travel** field per cover,
in centimetres, decimals with a comma or a point. Until they are all filled in, the
confirm button counts how many are missing instead of confirming, and the server
refuses the batch as a whole if one gets through. Nothing is written by halves.

**Back to the overview** leaves the panel with the batch intact.

Confirming writes every assignment, every collected travel and the resulting order in
**one** write. A refusal — a measurement started meanwhile, another write still being
applied, a travel out of range — appears at the top of the review panel and throws
nothing away: the changes are still pending and the numbers are still in their
fields.

### Undo

After a successful write a strip says how many assignments were applied and offers
**Undo** for seven seconds. It restores exactly the records that write changed, as
they were, which is why an undo does not put back a cover somebody measured in the
meantime.

The offer is on screen for seven seconds; the server holds the undo for **five
minutes**, or until the next write to that gateway, whichever comes first. The strip
is deliberately the shorter of the two — an offer still on screen after the thing
behind it has expired is worse than no offer — and the five minutes are what makes an
undo issued from a second browser tab, or a moment later from the keyboard, still
land. Undoing an undo is not offered: two buttons swapping a gateway back and forth
with nothing on screen saying which way round it is now is not a state anybody can
read.

## Reordering

Dropping a cover inside its own group reorders it. The order is the panel's own —
Home Assistant has no opinion about the order of two shutters — and it is
**remembered** rather than confirmed: with nothing else pending it is written
straight away, with an undo on the strip. With a batch in flight it travels with the
batch and is written by the same confirmation.

The order is stored per gateway and survives a restart, an upgrade and a second
browser. A cover that is removed from the configuration leaves its place behind
harmlessly: the stored order may name things that no longer exist, and they are
dropped on the next write rather than being an error anybody has to see.

## The cover detail

Opening a cover's name opens its card: **Cover detail**, at
`/myhome-calibration/cover/<unique id>`. It opens **over** the overview — a panel
from the right on a desktop, a sheet from the bottom on a phone — and the list stays
behind it, so closing the card leaves you where you were in it. The ✕ in the card's
own header closes it, and so does Escape; on a phone, so does a tap on the dark half
of the screen.

### Values in use

**Values in use** lists the five keys a calibration can measure — the two run times,
the slat opening time and the two roll coefficients — with the number the cover is
running on today and, under it, who said so: *own value, measured on this cover*,
*inherited from the profile “name”*, *from the configuration file*, or *default
value*. A value of its own always wins; then the assigned profile, then the file,
then the defaults. Where the value is the cover's own, the row also says what it
would go back to if that own value were removed.

### Editing by hand

**Edit the values by hand** opens the five fields prefilled. They count for this
cover alone and beat both the profile and the file — the manufacturer's declared
times, for instance, or a number you know better than the measurement did.

**A field left empty is not a zero.** It means "nothing to say about this one", and
that key goes back to coming from the profile or from the file; the placeholder in an
empty field is the number it would inherit, so the consequence is on screen before
the save. Emptying every field is the same as removing the measurement, and the page
says so in those words.

**The slat opening time and the two roll coefficients come after a note.** They are
parameters of the position model rather than times read off a stopwatch, so the form
puts an **Advanced parameters** box right in front of the first of them: change them
only knowing what they mean, and when in doubt take them from the guided calibration,
which measures them on the real cover. The two run times stay above it. The profile's
editor below does the same, with the reference travel above the note too.

**Set the curtain travel…** is its own control and its own write, because the travel
is what a profile is scaled by rather than one of the measured values. Typing a
travel shows, beside the field, what the cover would run on with it.

### Removing the measurement

**Remove the measurement…** takes the whole record: the measured values, the
assignment made from this panel, and a travel nobody else states. The confirmation
names where the cover will land — the values inherited from a profile the
configuration file itself assigns, the values of the configuration file, or the
defaults — and adds that the curtain travel stays when `myhome.yaml` is the one
stating it. That destination is not predicted from a rule: it is the cover resolved
once more with the record gone, which is the same answer the write itself gives
afterwards.

The measurements cannot be recovered. Getting them back means measuring again.

### Measuring it again, and correcting it

Three controls open the [calibration](#measuring-a-cover) **on this cover**, without
leaving the panel and without asking which cover it is again:

| Control | What it opens |
|---|---|
| **Measure again** | the calibration from the start; the route is chosen on the first screen |
| **Correct…** | the correction, in one of its three scopes — **Times only**, **Times and rolls**, **Thorough calibration only** |
| **Thorough calibration** | the readings at 25 and 75 % per direction, and the check |

A correction starts from the profile the cover should follow, so on a gateway that has
no profile at all **Correct…** and **Thorough calibration** cannot be pressed and say
why: there is nothing to correct against, and **Measure again** is the answer — a
profile is born at the end of it.

## The profile card

Opening a profile's name opens **Profile card**, at
`/myhome-calibration/profile/<name>`: its values, its reference travel, where it was
measured and everything that follows it. It opens over the overview in the same panel
the cover's card uses, and when you reach it *from* a cover's card — or a cover's card
from it — the ✕ becomes an arrow back to the card you came from. One step: the second
press closes the panel and leaves the list.

**Followers** are listed with what each one actually takes from the profile —
inherited, adjusted with the keys that are the cover's own named, or measured and
therefore taking nothing — and each is a way into its own card. A cover that follows
through its own `profile:` line in `myhome.yaml` is marked *from the configuration
file*, because a change made here cannot move it: that line is in your file. On the
overview the same fact is said once, in the group's own header, rather than under
every cover in it.

**Edit the values…** is the profile's own five numbers and its reference travel,
with an **Impact preview** beside the fields: one line per follower, saying what that
cover would end up with, key by key, for the keys it actually inherits. A follower
that measured everything says so and changes nothing; one whose travel is not
recorded says the profile cannot be brought to it. The preview is asked of the server
with the numbers as they are being typed, so it is the real answer and not an
estimate — and while a field is unusable it says to correct the fields rather than
showing the last good answer as if it still applied.

**Rename…** takes a name of letters, digits and underscores, up to 64 of them — no
spaces and no accents, because the name is also a key of the configuration file. The rename follows
every cover the panel assigned to the profile. Covers whose own `profile:` line in
the file names the old profile are not moved, and the confirmation says which ones
those are.

**Delete the profile…** names the covers that will lose it before anything happens,
and says where they land: the values of the configuration file where those exist, or
the defaults. Their curtain travels and their own measured values stay. If a
`cover_profiles:` entry of the same name was being shadowed by this profile, it
applies again from that moment — which is exactly why the covers concerned are named
rather than counted.

A profile that lives in the configuration file offers none of the three and says why.

## Measuring a cover

The guided calibration runs at `/myhome-calibration#/calibrate`, inside the panel, on
the same page as everything above. It is the same conversation as *Configure →
"Calibrate a cover"* — the same routes, the same presses, the same arithmetic and the
same three tape readings — drawn as a full page instead of a dialog. The whole of it is
described in [Guided calibration](guided-calibration.md); what follows is what is
different about having it here.

**The session lives on the server, not in the browser.** One per gateway. Closing the
tab, locking the phone or losing the connection does not end it and does not lose a
reading: opening the panel again shows the calibration where it was left. That is also
why the address alone never starts one — what is being measured travels inside the
page, so a reload or a pasted link lands on the calibration that exists, or on nothing,
and never sets a shutter moving.

**Which shutter.** *Measure a cover*, from the overview or from the first-run card,
asks **Which shutter is being measured?** and lists the gateway's basic covers with
their room, their curtain travel and the same origin chip the overview carries. The
three controls on a cover's card skip that question, because they already know.

**One at a time, per gateway.** If something else already holds a shutter of this
gateway, the calibration does not refuse and stop: it shows **The shutter is already in
calibration** and says which of the three holders it is — another panel or another tab,
which can be followed and taken over from its own screen; the *Configure* dialog, which
offers **Close the dialog and free the shutter** after asking, because the unsaved
measurements of that dialog are lost; or a run started by the 0.4.2 action, which has no
window to close and is waited out.

**While it runs.** The shutter moves, and every screen says so before it does: nothing
moves before a screen has announced it. During a run there are one or two lines and a
button, the motor line counts the seconds off the server's clock beside the estimated
position, and **Stop the shutter** is offered wherever something is moving. The phone
buzzes and beeps when the motor really starts, which is a switch on the briefing
(**Buzz and beep when the motor starts**) remembered in that browser. **Leave the
calibration** asks first whenever there is a measurement to throw away.

**What it saves.** The review shows what the cover uses today beside what it would use
afterwards, and nothing has been written until it is confirmed. The curtain travel and
the two run times are in front; the roll coefficients, the slat time, the values a save
would change without having measured them and the `myhome.yaml` equivalent are behind
**Show every value, roll coefficients included**. The first route offers both **Save as
the profile «…»** — which writes the profile and assigns the cover to it — and **Save
for this shutter only**; a correction offers only the second, because a correction is
about one window. Saving reaches the covers in place, without reloading the integration.

## When changes take effect

**Immediately, and without a reload.** A write publishes a signal, every cover of
that gateway re-reads its travel model — the file as it is written plus the store as
it now is — and swaps its numbers in place. No entity is recreated, no entity id
changes, no history is lost and nothing goes unavailable. A movement already under
way keeps the model it started with and picks the new one up when it ends; everything
else — the attributes, `Calibration source`, the next movement — changes at once.

This is the one behaviour that differs from 0.5.0, where every saved calibration
rebuilt the config entry. That is the right price for one guided measurement and much
too high for a panel where assigning twelve covers would take the whole gateway away
and back twelve times.

**While a guided calibration is running, the management screens only read.** A banner
says **Measurement in progress** and names the cover, and every handle and every write
control is disabled. Pending changes are kept while the lock lasts — they are not thrown
away, only held. The lock covers the whole gateway and not just the cover being
measured, because a measurement that ends by storing a profile changes what the
assignments around it are worth.

The banner says *which* of the three holders has the cover, and offers what can be done
about that one:

| Holder | What the banner offers |
|---|---|
| a calibration of this panel | **Resume the session**, which goes back to it, and **End it**, which asks first |
| the *Configure* dialog | **Open Configure**, and **Close the dialog and free the shutter**, which asks first because that dialog's unsaved measurements are lost |
| a run started by the 0.4.2 action | nothing to press: it has no window to close, and the sentence says to wait |

The panel is told about the lock before it lets anything be attempted, so the refusal
from the server is a backstop and not the user interface.

## What the panel never does

- **It never writes `myhome.yaml`.** Everything it stores goes to Home Assistant's
  own storage, one file per gateway, exactly where the guided calibration puts it.
  Your configuration file is read and never rewritten — which is also why a
  `cover_profiles:` profile is read-only here, and why a cover the file assigns to a
  profile cannot be reassigned from this page.
- **It moves a shutter only inside a calibration.** No control of the overview, of the
  two cards or of an assignment ever sends a command to the bus; the only screens that
  do are the guided calibration's, and each of them says what is about to move before
  it moves.
- **It does not configure the gateway.** Address, port, password, the file path and
  the session tunables stay under *Configure → Gateway and connection*.
- **It does not replace the dialog.** *Configure → Profiles and covers*,
  *Configure → Calibrations* and *Configure → "Calibrate a cover"* do everything the
  panel does, unchanged, and are the way in on a version of Home Assistant where the
  panel cannot load at all.
- **It does not show advanced covers**, which have no travel model to manage.

## Troubleshooting

**The panel is not in the sidebar.** It is hidden by default, per user. Open your own
user page from the bottom of the sidebar, go to the sidebar settings there, and move
**Profili e tapparelle** out of the hidden items. If it is not even in the hidden
list, the integration has not finished setting up: check that at least one MyHOME
gateway is loaded, then reload the page.

**The address says the page is not available, or the sidebar entry is missing on one
account.** The panel is admin only, and so is every command behind it. There is no
read-only mode: a non-admin sees nothing at `/myhome-calibration`, calibration
included. The dialog is equally admin-only, so this is not a door the panel closed.

**The page is blank, or says it could not start.** The panel catches its own
start-up errors and draws a plain sentence with a link to the integration page rather
than a white screen. It is usually a stale bundle, although that is now hard to
arrange: the page is served with a cache key —
`/myhome_panel/myhome-panel.js?v=<version>-<fingerprint>` — in which the fingerprint
is twelve characters of the bundle's own checksum, computed when the panel is
registered. It moves whenever a single byte of the file moves, so any new bundle
— a release, a hand-copied one, a version installed twice — is asked for at an
address the browser has never seen. A browser that has cached the old file anyway is
cleared with a hard refresh (`Ctrl`+`Shift`+`R`, or `Cmd`+`Shift`+`R` on a Mac). If
that does not do it, restart Home Assistant: the module URL is composed when the panel
is registered, so a file replaced under a running Home Assistant keeps the old address
until the next restart.

**A line at the foot of the page says live updates are not available.** The panel is
talking to a version of the integration that does not push changes, so it re-reads
every thirty seconds instead. Everything works; it is slower to notice a change made
elsewhere. It normally means the frontend bundle and the Python code are from
different versions — reinstall the integration, restart, then hard-refresh.

**A change was refused.** The sentence says which of the three it is: a guided
calibration is running on one of this gateway's covers, another write is still being
applied, or a value is out of range. Nothing was written in any of them, and nothing
on screen was thrown away.

**A cover is missing from the page.** Either it is `advanced: true`, and has no
travel model to manage, or its gateway is not the one selected in the header.

**Two browsers disagree.** They should not: every write pushes the whole new picture
to everybody looking at that gateway. A tab that was asleep catches up when it is
looked at again.

## Screenshots

The screens are captured on a live installation at release time. Until then, the
images this page will carry are listed here by name, so the page and the files cannot
drift apart:

| File | What it shows |
|---|---|
| `docs/images/panel/overview.png` | the overview: two profile groups, the "No profile" group, the origin chips |
| `docs/images/panel/assign-pending.png` | a cover moved between groups, the pending bar at the foot of the page |
| `docs/images/panel/review.png` | the review panel, with the before/after table and a missing travel |
| `docs/images/panel/cover-detail.png` | the cover detail, values in use with their origin |
| `docs/images/panel/profile-card.png` | the profile card, followers and the impact preview |
| `docs/images/panel/measuring.png` | the read-only lock while a guided calibration is running |
| `docs/images/panel/calibrate-pick.png` | the choice of shutter, with the origin chips |
| `docs/images/panel/calibrate-step.png` | a timed run: the motor line, the estimated position and the big button |
| `docs/images/panel/calibrate-review.png` | the review before saving, with the two exits |

*Added at release.*

## See also

- [Guided calibration](guided-calibration.md) — the measuring conversation itself: the
  three routes, the two levels, how timing by button press works, and the *Configure*
  dialog that runs the same one.
- [Configuration → Cover](configuration.md#cover) — the `myhome.yaml` keys, the
  precedence between the file and what is stored, and the `Calibration source`
  attribute.
- [Architecture → The panel](architecture.md#the-panel) — for contributors: how it is
  registered and served, and how to rebuild the bundle.
- [The panel's WebSocket API](panel-websocket-api.md) — for contributors: every
  command behind the panel, its payload, its answer and its refusals.
