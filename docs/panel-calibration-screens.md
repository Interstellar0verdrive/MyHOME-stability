# Calibration tab and wizard (panel 0.43.0)

Panel 0.43.0 adds a **Calibration** view to WHO 2 covers, next to **Devices** and **Profiles**, and a calibration
wizard that opens inside it. The backend is unchanged: every step that exists today runs on the current session
API ([WebSocket API](panel-websocket-api.md)); the steps whose verbs do not exist yet run as a local **preview**
that sends nothing to Home Assistant and says so on screen. The profile dialog keeps its calibration section and
adds **New guided measurement**, which opens the wizard on the same cover.

This page maps each screen of the design mockups (boards T-xx, A-xx, B-xx, C-xx, S-xx) to the code that draws it,
the texts it uses and the message it sends.

## Files

| File | Role |
| --- | --- |
| `panel-calibration-tab.js` | The Calibration view: list, filters, expanded row, row menu, Assign profile, open session, several covers in sequence |
| `panel-calibration-wizard.js` | The wizard: layout, events, sessions, automatic continuation, leaving |
| `panel-calibration-screens.js` | `buildScreen()`: which board a moment is, as plain data (no DOM, no messages) |
| `panel-calibration-gateway.js` | `LiveCalibrationGateway` (the existing session) and `PreviewCalibrationGateway` (local) |
| `panel-calibration-text.js` | `**bold**` and paragraphs from escaped text, localized numbers, dates and lists |
| `panel-translations.js` | `calTab…` (view), `wiz_T001…` (generated from the translation sheet), `wiz…` (screen-only) |

The wizard never builds a WebSocket message itself. `LiveCalibrationGateway` extends the `CoverCalibration` engine of
the profile dialog and only replaces its drawing, so subscriptions, heartbeats, reconnection, take control (two taps
while the owner is present), Cancel and the per-tab identity are the ones already documented and tested.

## Calibration view (T-01…T-05)

| Board | What is shown | Data | Texts |
| --- | --- | --- | --- |
| T-01 list | Timed covers (no position sensor): name, room and bus address (`Address: 86 · A: 8 · PL: 6`), status, profile (the date of the last measurement is in the details, and on phones under the name); Measure / Fine-tune; ⋮ with every secondary action (Fine-tune, Measure or Remeasure, Assign profile, Details); the whole row opens its details | `cover_profiles/overview` per gateway | `calTabTitle`, `calTabIntro`, `calTabCol*`, `calTabStatus_*`, `calTabMeasuredOn`, T363 |
| T-02 filter | All / To measure / Calibrated / With profile, with counts as grey badges; help note on To measure | same | `calTabFilter_*`, `calTabCount*`, `calTabToMeasureHelp` |
| T-03 session | The covers of the open session marked In progress (a tab guides it / no tab guides it / paused / waiting for the stop) with Open session; new measurements disabled | `cover_profiles/read` on one cover: its `calibration` is the gateway's single session | `calTabRunning_*`, `calTabBusy`, `calOpenSession` |
| T-04 empty | No timed cover | overview | `calTabEmpty*`, `calTabHowItWorks*` |
| T-05 details | Row expanded in place: three blocks of at most 360 px (values in use, last measurement and method, profile and who else follows it), in columns while they fit; notes in one shared style (`.cal-note`), including where the times of a never measured cover come from (defaults or YAML); each block ends with its own action, left-aligned 20 px under its content: values → Fine-tune (only with measured rolls), last measurement → Remeasure or Measure, profile → Assign profile | overview `effective` values, origin and provenance | `calTabValues`, `calTabSlats*`, `calTabMethod_*`, `calTabFollowers*`, `wiz_T093`, `wiz_T094`, `wiz_T041`, `wiz_T105`, `wiz_T106`, T377, T378 |

The session is read from one cover (up to three are tried in turn if a read fails); when none answers but the
overview reports the gateway reserved (`assignment_reason: calibration_busy`), new measurements stay disabled.

Status comes from the saved evidence: **To measure** without a guided or automatic measurement, **Times measured**
with one, **Times and roll** with roll coefficients. *Measure several covers in sequence* opens a dialog with the look
of the profile dialog, with the existing selection (`cover_calibration/targets`, covers named as in the panel) and
automatic run (`batch_start`) (T363–T366). *Assign profile* opens a dialog listing the gateway's profiles as on B-01
(type with or without slats, where and when measured, reference travel, how many covers follow it) and assigns the
chosen one with `cover_profiles/write` `assign` (T368–T376); it never opens the Travel profile dialog. *Open session*
opens the wizard for a `geometry` session and the existing view, in the same dialog, for guided, automatic and
sequence sessions. Above 1024 px the rows are columns (cover, status, profile, actions; the three blocks of the details
sit under the first three), below they are cards. Rendering the view sends no calibration message.

## Wizard layout

Desktop (≥ 1024 px): header with the cover name, its address and **Discard calibration**; stepper (left), instruction
(centre), actions (right). Phone: a full screen with the header and ✕, a one-line stepper with **Steps** (a sheet with
the whole stepper), the instruction scrolling, the actions anchored at the bottom. The stepper shows the phases of the
path, the current one half filled, and under each reached phase its measured values. The stopwatch appears only in
the timed runs; waits show their stages and, in the timed half runs, a progress bar. Every new step moves the focus
to its title; the Steps sheet and the Discard dialog keep Tab inside and close with Escape, and closing the dialog
returns the focus to the screen's confirming button (or its title). After every change of screen or of its buttons the
confirming buttons stay disabled for `CONFIRM_GUARD_MS` (700 ms), so a slow double tap never confirms an end stop the
cover has not reached nor skips the second tap of *Take control*; Stop is never held back.

## Path A — first cover of its type

Live: `myhome/cover_calibration/start` with `mode: "geometry"` (and `slats: false` for a cover without slats), then
`myhome/cover_calibration/action`. "Auto" marks the `next` the wizard sends after the user's previous press, because
the mockups show that movement without a press. **The rule** (`CalibrationWizard._autoNext`): an automatic verb is
sent only on the view that immediately follows a press of the user in this tab (through the movement and the stop
that press started, never past a stop that waits for the user), once per `sequence`, and never after a replayed
subscription (a new `attachment`: Home Assistant reconnected), a reconnection, a claim, a lost connection, a refused
verb or a view this tab does not own. When it does not happen, the screen offers the same `next` as a button.

| Board | Session (`phase` / `step`) | Texts | Sent |
| --- | --- | --- | --- |
| A-01 | before the session | T001, T003–T006 | nothing |
| A-02 | before the session | T015–T019 | nothing |
| A-03 | before the session | T021–T025, T198, T199 | `start` on «Understood, begin» |
| A-04 | `briefing`/`starting_close` · `home` | T027, T029, T028 | `next` (auto) |
| A-05 | `closing` · `home` | T030–T032 | `endpoint` |
| A-06 | `briefing` · `lift` (local briefing) | T035–T037 | nothing |
| A-07 | `briefing`/`opening` · `lift` | T042–T046, T028 | `next`, then `lift` |
| A-08 | `reading` · `lift`; `briefing` · `reset` with `gap_warning` | T047–T051, `calGapWarning` | `reading`; `next` or `repeat` after a wide gap |
| A-09 / A-10 | `reset` | T027, T052; T053, T054, T032 | `next` (auto), `endpoint` |
| A-11 | `briefing`/`opening` · `opening` | T055 (T040 without slats), T056, T045, T057 | `next`, `endpoint` |
| A-12 | `reading` · `opening` (local) | T058–T061 | `repeat` |
| A-13 | `reading` · `opening` | T062–T066 | `reading` (travel, 20–500 cm, saved travel offered) |
| A-14 | `briefing`/`closing` · `closing` | T068–T070 | `next`, `endpoint` |
| A-15 / A-16 | `briefing` · `half_open` (local) | T071, T072, T060, T061; T074–T076 | `repeat`; `next` |
| A-17 / A-18 | `opening` · `half_open`; `reading` | T027, T079, T080; T081, T082, `calReadingRange`, T051, T033 | `reading`, `repeat` |
| A-19 | `top`, then `closing` · `half_close` | T086, T084, T085, `wizTopReached` | `next` (auto), `endpoint`, `next` (auto) |
| A-20 | `reading` · `half_close` | T087, T088, `calReadingRange` | `reading`, `repeat` |
| A-30 / A-31 | `check`: briefing, run, `reading` (only if a session reaches a check; the wizard offers none) | T027, T086; T138, T139, T123, T051, T033 | `next`, Stop; `reading` (0.1 cm to the travel), `repeat` |
| A-21 / A-21c / A-21d | `review` | T091, T092/T107, T093–T106, T108–T112, T280, T281/T289, `wizTable*`, `wizTechnical` | `save` (`save_mode: "new"`, `name`) |
| A-22…A-33 | preview `refine` | T113–T152 | nothing (preview) |
| A-34 | after `saved` | T153–T158 | nothing |

The intermediate readings (A-18, A-20) use the session's `reading_range`: the hint gives the heights the fit
accepts, shown inside their true ends (`calReadingRange`, the text of the profile dialog), a value outside it is
refused in the field with `profileError_reading_out_of_range` before anything is sent, and the mockups' rough
expectation (T083) is shown only when the view carries no range. As in the profile dialog, the intermediate runs show
no elapsed time (Home Assistant stops them); their wait card keeps the stages and a progress bar. A check run, which
Home Assistant stops in the same way, is shown alike.

The summary has one **Save** and the switch *Also save as reusable profile*: on for a first cover, off when the cover
already follows a profile; on with a followed profile offers *Create a new profile* (default) or *Update «…»*. Today a
`geometry` session saves only as a new profile, so saving on the cover only or updating a shared profile shows
`wizSaveUnavailable` and keeps Save disabled. *Continue with fine-tuning* saves first, then opens fine-tuning.

## Path B — like a cover already measured (preview)

| Board | Preview state | Texts |
| --- | --- | --- |
| B-01 | before | T161–T165 (profile drop-down, where it was measured and who follows it) |
| B-02 | before | T167, T168, T076 |
| B-03 / B-04 | `positioning` · `open_full`; `reading` · `travel` | T027, T170; T062–T066 |
| B-05 / B-06 | `positioning` · `check`; `reading` · `check` | T171, T172, T086; T138, T173, T123 |
| B-07 / B-07b | `check_result` | T141, T175, T060, T143; T144, T176, T177 (opens path C) |
| B-08 / B-09 | `review`; `saved` | T179–T181, T280, T284; T154, T182, T158 |

## Path C — has a profile but stops at the wrong point

C-01 (T184–T188) shows what the cover uses; C-02 (T189–T196) chooses the case:

| Case | Runs on | Boards | Save |
| --- | --- | --- | --- |
| Everything (preselected) | live `geometry`, as path A | C-03…C-21 (T197, T201–T203, T205, T210, T285), fine-tuning preview C-22…C-33 (T226, T286), C-34 (T228) | new profile live; on the cover only waits for the backend |
| Times only | live `guided` (both directions) | C-35 (T230, T231), C-05 · C-11 · C-12 · C-14 with `calPhase_*`, C-36 (T179, T233, T287) | `save_mode: "cover"` |
| Tape readings only | preview `rolls` | C-37 (T235, T236), C-22…C-32, C-38 (T149, T238, T239, T288), C-34 | preview |

## States

| Board | When | Texts | Actions |
| --- | --- | --- | --- |
| S-01…S-05 | the session ended with a reason (`interrupted`) | titles T240, T244, T248, T252, T254 by family; body `calReason_<reason>` | Start over (T261), Close |
| S-01…S-05 | a published `problem` (future) | T240–T258 | `repeat_step` |
| S-06 | `expired` | T259, T260 | Start over, Close |
| S-07 | read-only view | T262 (status line), T263–T265, `calConfirmTakeControl`; no reading field | Take control (two taps while the owner is present); Stop while it may move |
| S-08 | Discard during a session | T267, T269, T270, `wizExitBodyLive` (live) / T268 (preview) | `cancel`; Stop beside it while it may move |

A session reopened from the list is drawn as path C (remeasure everything) when its cover already follows a profile,
otherwise as path A; its slat choice comes from the view.

## Preview steps and the backend they wait for

| Preview | Future backend | Where to connect |
| --- | --- | --- |
| Fine-tuning `refine` (A, C) | `refine` on the record just saved | `CalibrationWizard._startRefine` |
| Path B `profile` | mode `profile_check`; save = follow the profile with the measured travel | `CalibrationWizard._begin`, `_save` |
| Path C `rolls` | mode `rolls` | `CalibrationWizard._begin` |
| Save targets `cover_only` / `profile_update` in `geometry` | unified `save {target}` | `LiveCalibrationGateway.supports`, `save` |
| Session in the overview | `calibration` in `cover_profiles/overview` | `CalibrationTab._read` |
| Verified status, start time | check result stored with its evidence; `started_at` | `coverStatus`, `CalibrationTab._row` |
| Problems as steps | `problem` + `repeat_step` | already drawn by `buildScreen` |

The preview is announced before it starts: a line (T318) under path B on A-02, under the start of B-02 and C-37, and
(T319) under *Continue with fine-tuning*, which saves the calibration for real first. The end of a preview is titled
*Preview of the summary* (T320) and says that nothing was saved (T321) or that only the calibration before the
fine-tuning was (T322).

The preview check rounds the gap half up to the whole centimetre and passes up to 4 cm (`roundHalfUp`,
`CHECK_THRESHOLD_CM`); its heights come from a rough linear model only meant to fill the screens.

## Texts

`wiz_T…` keys are generated from the translation sheet (`ui-texts-en.csv`, columns `italian` and `english`): the
example names and numbers of the mockups become placeholders (`{cover}`, `{profile}`, `{seconds}`, `{cm}`, `{gap}`,
`{travel}`, …), `**…**` marks bold text, blank lines separate paragraphs. Texts with a count have zero and one forms
(rows T305–T317, chosen by `counted()` in `panel-calibration-screens.js`); the tab summary uses `calTabCount*` and
`calTabCount*_one`. Rows that only describe the mockups (example
names, scrims, phone annotations), the phase lines (built from `wizPhaseLine`) and copies of identical texts are
left out. `calTab…` and the few `wiz…` keys without a `_T` number are screen texts not in the sheet yet.

## Tests

`tests/frontend/calibration-tab.test.mjs`, `calibration-wizard.test.mjs`, `calibration-path-b.test.mjs` and
`calibration-path-c.test.mjs` drive the panel with `fake-calibration.mjs`, a stand-in for Home Assistant whose
`geometry` and `guided` transitions follow the backend modules; bus events are explicit calls, so each test decides
when the cover moves and checks the exact messages sent.
