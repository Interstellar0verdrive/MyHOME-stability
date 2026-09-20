"""Paths B and C, the thorough calibration and the two verifications.

The session walks the whole of SPEC §3.4 here: the window that is one of a kind
already measured, the window that follows a profile and stops in the wrong place, the
four extra readings and the check that end both of them, and the two screens that ask
the model a question instead of feeding it one.

What this file is really about is that **the panel and the dialog store the same
thing**. The arithmetic is shared and held equal function by function by
`test_calibration_measure.py`; what is not shared is the conversation, and a
conversation that collected the same numbers in a different order, or forgot to keep
one, would store something else entirely. So every path here is walked twice - once
through the session and once through the *dialog*, on its own entry, with the same
fake shutter and the same clock - and the two records are compared key by key. Path A
is the one deliberate difference (SPEC §3.9: its main exit writes no values of the
cover's own), and there the comparison is of what the shutter ends up *moving on*,
which has to be the same.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.const import CONF_NAME, STATE_OPENING
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util

from custom_components.myhome import calibration_session
from custom_components.myhome.calibration import REASON_BAD_POINT, CalibrationError, RunReport
from custom_components.myhome.calibration_flow import (
    HALF_RUN,
    PLAN_PRECISE,
    PLAN_PRECISE_TRAVEL,
    PLAN_PROFILE,
    PLAN_TIMES,
    PLAN_TIMES_AND_ROLLS,
    VERIFY_RUN,
    VERIFY_RUN_PROFILE,
)
from custom_components.myhome.calibration_session import (
    REFINE_THRESHOLD_CM,
    CalibrationSession,
    current,
)
from custom_components.myhome.calibration_store import (
    loaded_store,
    merged_profiles,
    resolve_cover,
)
from custom_components.myhome.const import (
    CONF_CLOSING_ROLL,
    CONF_CLOSING_TIME,
    CONF_HEIGHT,
    CONF_MEASURED_AT,
    CONF_OPENING_ROLL,
    CONF_OPENING_TIME,
    CONF_PROFILE,
    CONF_RAW,
    CONF_SLAT_TIME,
    DIRECTION_CLOSE,
)
from custom_components.myhome.cover import (
    calibration_ascent_cm,
    calibration_descent_cm,
    calibration_run_seconds,
)
from custom_components.myhome.panel_data import basic_covers, yaml_profiles
from custom_components.myhome.panel_write import PanelError
from custom_components.myhome.validate import derive_cover_from_profile

from .helpers_calibration import (
    CLOSING,
    HEIGHT,
    OPENING,
    ROLL_DOWN,
    ROLL_UP,
    SLAT,
    FakeRunner,
    ascent_cm,
    descent_cm,
)
from .helpers_core import MAC
from .helpers_platforms import entity_object, setup_myhome
from .test_calibration_session import (
    CLIENT,
    COVER_NAME,
    DEVICE_KEY,
    ENTITY,
    OTHER_CLIENT,
    PATH_A_BASIC,
    UNIQUE_ID,
    YAML_KEY,
    Act,
    act,
    check_the_snapshot,
    open_session,
    the_record,
    the_store,
    walk,
)

# --------------------------------------------------------------------------------------
# The windows these paths are walked on
# --------------------------------------------------------------------------------------
# The profile `tall` is the reference window itself: a window that really is one of
# those reads the tape exactly where the profile says it will, so path B's check comes
# out at nothing and the one that does not can be made to miss by a stated amount.
# The file's own numbers for the cover are *not* the shutter's, so "the calibration
# reached the store" can be told from "nothing moved at all".
FILE_OPENING = 30.0
FILE_CLOSING = 29.0
FILE_SLAT = 6.0
FILE_ROLL = 1.2

PROFILE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    {YAML_KEY}:
      where: '81'
      name: {COVER_NAME}
      opening_time: {FILE_OPENING}
      closing_time: {FILE_CLOSING}
      slat_time: {FILE_SLAT}
      roll: {FILE_ROLL}
      height: {HEIGHT}
  cover_profiles:
    tall:
      reference_height: {HEIGHT}
      opening_time: {OPENING}
      closing_time: {CLOSING}
      slat_time: {SLAT}
      opening_roll: {ROLL_UP}
      closing_roll: {ROLL_DOWN}
"""

# The same window with the run times the shutter really has and a roll that is wrong:
# the state the third scope of a correction exists for - the motor is right, the
# curtain winds differently - and the one in which the readings have something to
# recover.
IN_USE_YAML = PROFILE_YAML.replace(
    f"      opening_time: {FILE_OPENING}\n"
    f"      closing_time: {FILE_CLOSING}\n"
    f"      slat_time: {FILE_SLAT}\n",
    f"      opening_time: {OPENING}\n      closing_time: {CLOSING}\n      slat_time: {SLAT}\n",
)

# ...and with nobody anywhere knowing this window's own travel, which is what puts the
# tape reading in front of the thorough calibration (`PLAN_PRECISE_TRAVEL`).
NO_TRAVEL_YAML = IN_USE_YAML.replace(f"      height: {HEIGHT}\n", "")

# ...and the same window told to follow the profile. Nobody has measured *this*
# window's travel and the profile's reference height is another window's, so the two
# questions "what is this window's travel" and "what travel is it resolved with" have
# different answers here, which is the one arrangement that tells them apart.
ASSIGNED_YAML = NO_TRAVEL_YAML.replace(
    f"      roll: {FILE_ROLL}\n", f"      roll: {FILE_ROLL}\n      profile: tall\n"
)

# A second window that follows the same profile: what `review.affected` is about.
FOLLOWER_YAML = PROFILE_YAML.replace(
    "  cover_profiles:",
    """    landing_shutter:
      where: '82'
      name: Landing Shutter
      height: 150
      profile: tall
  cover_profiles:""",
)

# The one state in which following a profile changes a key nobody measured: the file
# writes a bus cost for this cover and the profile carries the installation's default.
BUS_COST_YAML = PROFILE_YAML.replace(
    f"      height: {HEIGHT}\n", f"      height: {HEIGHT}\n      stop_latency: 0.35\n"
)

# --------------------------------------------------------------------------------------
# The two windows of the live test of 20 September (`ANALYSIS-roll-scaling.md`)
# --------------------------------------------------------------------------------------
# A 198 cm window told to follow the profile of a 110 cm one. The scaling law gets the
# times nearly right and the rolls badly wrong, so `set_cover_position: 50` from closed
# put the bottom edge at 107 cm instead of 99 - and the check as it stood, half the
# closing time from the top, reported 3,5 cm and said the profile was fine. This is the
# case lot W3 exists for, and it is a bench and not an anecdote because every number
# below was measured on the wall.
LIVE_TRAVEL = 198.0
LIVE_WINDOW = {
    CONF_OPENING_TIME: 22.2,
    CONF_CLOSING_TIME: 21.3,
    CONF_SLAT_TIME: 4.4,
    CONF_OPENING_ROLL: 1.86,
    CONF_CLOSING_ROLL: 2.21,
}
LIVE_YAML = f"""
gateway:
  mac: {MAC}
  cover:
    {YAML_KEY}:
      where: '81'
      name: {COVER_NAME}
      opening_time: {LIVE_WINDOW[CONF_OPENING_TIME]}
      closing_time: {LIVE_WINDOW[CONF_CLOSING_TIME]}
      slat_time: {LIVE_WINDOW[CONF_SLAT_TIME]}
      opening_roll: {LIVE_WINDOW[CONF_OPENING_ROLL]}
      closing_roll: {LIVE_WINDOW[CONF_CLOSING_ROLL]}
  cover_profiles:
    short:
      reference_height: 110
      opening_time: 14.3
      closing_time: 14.3
      slat_time: 2.7
      roll: 2.07
      opening_roll: 2.07
      closing_roll: 2.33
"""


class ConfiguredWindow(FakeRunner):
    """A shutter that runs on the seconds the *entity* is configured with.

    `FakeRunner` answers as the reference window whatever the cover's configuration
    says, which is exactly right for every walk that measures a window from scratch and
    exactly wrong for path B's check: there the run is a fraction of the curtain time
    the cover is configured with today, and the model being questioned is a profile the
    cover does not follow yet. The two are different windows, and telling them apart is
    the whole of this lot.

    `where_the_bar_is` is the other half of it: the seconds the motor really spent, put
    through the model of the window that is really on the wall.
    """

    def __init__(self, cover: Any, configured: dict[str, float], window: dict[str, float],
                 travel: float) -> None:
        super().__init__(cover)
        self.configured = configured
        self.window = window
        self.travel = travel

    def seconds_of(self, direction: str, fraction: float) -> float:
        return calibration_run_seconds(
            direction,
            self.configured[CONF_OPENING_TIME],
            self.configured[CONF_CLOSING_TIME],
            self.configured[CONF_SLAT_TIME],
            fraction,
        )

    def where_the_bar_is(self, direction: str, fraction: float) -> float:
        """Centimetres above the closed rest position, on the real window's model."""
        seconds = self.seconds_of(direction, fraction)
        if direction == DIRECTION_CLOSE:
            return calibration_descent_cm(
                self.window[CONF_CLOSING_ROLL],
                self.window[CONF_SLAT_TIME],
                self.travel,
                self.window[CONF_CLOSING_TIME],
                seconds,
            )
        return calibration_ascent_cm(
            self.window[CONF_OPENING_ROLL],
            self.window[CONF_SLAT_TIME],
            self.travel,
            self.window[CONF_OPENING_TIME],
            seconds,
        )

    async def _run_fraction(self, direction: str, fraction: float) -> RunReport:
        self._maybe_fail("run")
        self.runs.append((direction, fraction))
        self.log.append(("run", direction))
        seconds = self.seconds_of(direction, fraction)
        now = dt_util.utcnow()
        return RunReport(
            motor_start=now,
            stop_written=now,
            motor_seconds=seconds,
            planned_seconds=seconds,
            fraction=fraction,
            direction=direction,
        )


# --------------------------------------------------------------------------------------
# One conversation, walked by the session and by the dialog
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Step:
    """One thing the user does, in the words of both conversations.

    `action` is the session's `act` and the dialog's menu option; `field` is the name
    the dialog's form gives the value the session sends as `submit`. Written once so
    that the two walks cannot drift apart in the fixture instead of in the code.
    """

    action: str
    value: Any = None
    field: str | None = None
    tick: float = 0.0


def for_the_session(steps: tuple[Step, ...]) -> tuple[Act, ...]:
    return tuple(Act(step.action, step.value, step.tick) for step in steps)


# Path A at the basic level, in the words of both conversations. The session's own
# walk of it lives in `test_calibration_session.py`; this one carries the field names
# the dialog's forms want, and a test holds the two to being the same conversation.
PATH_A: tuple[Step, ...] = (
    Step("path_a"),
    Step("begin"),
    Step("confirm_closed"),
    Step("open_start"),
    Step("lifted_off", tick=SLAT),
    Step("lift_accept"),
    Step("confirm_closed_again"),
    Step("open_full_start"),
    Step("stopped_open", tick=OPENING),
    Step("accept_step"),
    Step("submit", str(HEIGHT), field=CONF_HEIGHT),
    Step("accept_step"),
    Step("close_start"),
    Step("stopped_closed", tick=CLOSING),
    Step("accept_step"),
    Step("tape_start"),
    Step("submit", str(ascent_cm(0.5)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(descent_cm(0.5)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", "tall", field=CONF_NAME),
)

# Path B: the profile, the travel, and the offer of a check.
PATH_B: tuple[Step, ...] = (
    Step("path_b"),
    Step("submit", "tall", field=CONF_PROFILE),
    Step("tape_start"),
    Step("submit", str(HEIGHT), field=CONF_HEIGHT),
    Step("accept_step"),
    Step("skip_verify"),
)
# ...and the same with the check taken up. **Not** a conversation the dialog can be
# compared against any more: since lot W3 the panel's check is half the TRAVEL, going
# up from the closed end stop, while the dialog goes on running half the closing time
# down from the top (live finding 33, decided 20 September). The window really is one
# of those, so the tape finds the bar exactly at half its travel; the divergence itself
# has a test of its own, `test_the_panel_s_check_of_a_profile_is_not_the_dialog_s`.
PATH_B_CHECKED: tuple[Step, ...] = (
    *PATH_B[:-1],
    Step("verify_now"),
    Step("submit", str(HEIGHT / 2), field="measured_cm"),
    Step("accept_step"),
)

# The ascent and the descent, pressed for: the part paths A and C share.
THE_THREE_PRESSES: tuple[Step, ...] = (
    Step("confirm_closed"),
    Step("open_start"),
    Step("lifted_off", tick=SLAT),
    Step("lift_accept"),
    Step("confirm_closed_again"),
    Step("open_full_start"),
    Step("stopped_open", tick=OPENING),
    Step("accept_step"),
)
PATH_C_TIMES: tuple[Step, ...] = (
    Step("path_c"),
    Step("submit", "tall", field=CONF_PROFILE),
    Step("times_only"),
    *THE_THREE_PRESSES,
    Step("close_start"),
    Step("stopped_closed", tick=CLOSING),
    Step("accept_step"),
)
PATH_C_ROLLS: tuple[Step, ...] = (
    Step("path_c"),
    Step("submit", "tall", field=CONF_PROFILE),
    Step("times_and_rolls"),
    *THE_THREE_PRESSES,
    Step("submit", str(HEIGHT), field=CONF_HEIGHT),
    Step("accept_step"),
    Step("close_start"),
    Step("stopped_closed", tick=CLOSING),
    Step("accept_step"),
    # The tape phase. The shutter is at the bottom, so the ascent's reading is dealt
    # first, exactly as it is on path A.
    Step("tape_start"),
    Step("submit", str(ascent_cm(0.5)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(descent_cm(0.5)), field="measured_cm"),
    Step("accept_step"),
)
# The four readings of the thorough calibration, and the check that closes it.
THE_FOUR_READINGS: tuple[Step, ...] = (
    Step("tape_start"),
    Step("submit", str(descent_cm(0.25)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(descent_cm(0.75)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(ascent_cm(0.25)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(ascent_cm(0.75)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(descent_cm(VERIFY_RUN)), field="measured_cm"),
    Step("accept_step"),
)
# ...and the same four dealt from the bottom, which is where the descent of a
# correction leaves the shutter: `tape_brief` puts the reading whose run starts there
# first, so the ascent's quarter is asked for before the descent's.
THE_FOUR_READINGS_FROM_CLOSED: tuple[Step, ...] = (
    Step("tape_start"),
    Step("submit", str(ascent_cm(0.25)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(descent_cm(0.25)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(descent_cm(0.75)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(ascent_cm(0.75)), field="measured_cm"),
    Step("accept_step"),
    Step("submit", str(descent_cm(VERIFY_RUN)), field="measured_cm"),
    Step("accept_step"),
)
PATH_C_POINTS: tuple[Step, ...] = (
    Step("path_c"),
    Step("submit", "tall", field=CONF_PROFILE),
    Step("points_only"),
    *THE_FOUR_READINGS,
)
# The two conversations that reach the thorough level from a summary rather than
# choosing it: "Continua con la calibrazione approfondita" at the end of path A and at
# the end of a correction.
PATH_A_THOROUGH: tuple[Step, ...] = (*PATH_A, Step("refine"), *THE_FOUR_READINGS)
PATH_C_THOROUGH: tuple[Step, ...] = (
    *PATH_C_TIMES,
    Step("refine"),
    *THE_FOUR_READINGS_FROM_CLOSED,
)


# --------------------------------------------------------------------------------------
# Driving the dialog, for the comparison
# --------------------------------------------------------------------------------------
def storage(tmp_path: Path, name: str) -> Path:
    """A directory of its own for one of the two conversations' `myhome.yaml`."""
    folder = tmp_path / name
    folder.mkdir(exist_ok=True)
    return folder


async def _settled(hass: HomeAssistant, result: dict[str, Any]) -> dict[str, Any]:
    """Let the dialog's progress screens finish, and answer the screen after them."""
    while result["type"] is FlowResultType.SHOW_PROGRESS:
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_configure(result["flow_id"])
    return result


async def what_the_dialog_stores(
    hass: HomeAssistant,
    tmp_path: Path,
    freezer: FrozenDateTimeFactory,
    yaml_text: str,
    steps: tuple[Step, ...],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Walk the same conversation in *Configura*, and answer what it wrote.

    On an entry of its own, set up and unloaded inside this helper, so that the session
    under test never shares a gateway - or a store - with the dialog it is compared to.
    """
    async with setup_myhome(hass, storage(tmp_path, "dialog"), yaml_text) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        result = await hass.config_entries.options.async_init(entry.entry_id)
        for option, payload in (
            ("calibrate", None),
            ("cover", None),
            (None, {"cover": UNIQUE_ID}),
        ):
            data = {"next_step_id": option} if option is not None else payload
            result = await _settled(
                hass, await hass.config_entries.options.async_configure(result["flow_id"], data)
            )
        for step in (*steps, Step("save")):
            if step.tick:
                freezer.tick(timedelta(seconds=step.tick))
            data = (
                {step.field: step.value}
                if step.action == "submit"
                else {"next_step_id": step.action}
            )
            result = await _settled(
                hass, await hass.config_entries.options.async_configure(result["flow_id"], data)
            )
        store = loaded_store(hass, entry)
        assert store is not None
        written = (deepcopy(store.raw_covers), deepcopy(store.raw_profiles))
        for flow in list(hass.config_entries.options.async_progress()):
            hass.config_entries.options.async_abort(flow["flow_id"])
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
    return written


def to_the_microsecond(value: Any) -> Any:
    """One stored value with its floats rounded to the resolution of a timestamp.

    The two walks start at two different instants, and a press measured from either of
    them is the difference of two floats: 21.699999809 s against 21.700000048 s, which
    is two hundred nanoseconds of IEEE 754 and not a difference between the two
    conversations. A `datetime` cannot hold better than a microsecond in the first
    place, so that is where the comparison is made.
    """
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: to_the_microsecond(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_the_microsecond(item) for item in value]
    return value


def comparable(record: dict[str, Any]) -> dict[str, Any]:
    """One stored record without the two things the two conversations cannot share.

    `measured_at` is the wall clock of the walk, and the session adds `client` and
    `save_target` to the `raw` block so that a record can say which of the two wrote
    it (SPEC §3.9). Everything else - the values, the assignment, `profile_wins`, the
    source and every measurement kept beside them - has to be identical.
    """
    shown = {
        key: to_the_microsecond(value)
        for key, value in record.items()
        if key != CONF_MEASURED_AT
    }
    if isinstance(shown.get(CONF_RAW), dict):
        shown[CONF_RAW] = {
            key: value
            for key, value in shown[CONF_RAW].items()
            if key not in ("client", "save_target")
        }
    return shown


def resolved_values(hass: HomeAssistant, entry, unique_id: str = UNIQUE_ID) -> dict[str, Any]:
    """The travel model one window moves on now, through the cover's own function."""
    store = loaded_store(hass, entry)
    profiles = merged_profiles(
        yaml_profiles(hass, entry), {} if store is None else store.profiles
    )
    return dict(
        resolve_cover(
            basic_covers(hass, entry)[unique_id],
            profiles=profiles,
            calibration=None if store is None else store.calibration(unique_id),
        ).values
    )


async def save(session: CalibrationSession, target: str) -> dict[str, Any]:
    return await session.async_save(CLIENT, session.revision, target)


def test_path_a_is_the_same_conversation_on_both_sides() -> None:
    """The walk written here and the session's own are one list, not two.

    `PATH_A` carries the field names the dialog's forms want, which the session does
    not need; everything else about it has to be what `test_calibration_session.py`
    already walks, or the comparison below would be between two different measurements.
    """
    assert for_the_session(PATH_A) == PATH_A_BASIC


# --------------------------------------------------------------------------------------
# Path B
# --------------------------------------------------------------------------------------
async def test_path_b_is_the_profile_the_travel_and_nothing_else(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Two screens for the second window of a kind, and one tape reading between them.

    The whole of path B in the snapshot: the choice, the plan it installs, the one
    reading of its tape phase, the offer of a check and the summary that has nothing
    left to offer but Save.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)

        assert session.snapshot()["actions"] == ["path_a", "path_b", "path_c"]
        snapshot = await act(hass, session, Act("path_b"))
        assert snapshot["step"] == "path_b"
        assert snapshot["path"] == "path_b"
        assert snapshot["actions"] == []
        assert snapshot["form"]["field"] == CONF_PROFILE
        assert snapshot["form"]["kind"] == "choice"
        assert snapshot["form"]["choices"] == ["tall"]
        assert snapshot["form"]["suggested"] == "tall"
        assert runner.log == []

        snapshot = await act(hass, session, Act("submit", "tall"))
        assert snapshot["profile"] == "tall"
        assert snapshot["plan"] == list(PLAN_PROFILE)
        assert snapshot["step"] == "tape_brief"
        # One reading: the travel. `verify_offer` and `summary` are not readings.
        assert snapshot["placeholders"]["readings"] == 1

        snapshot = await walk(hass, session, for_the_session(PATH_B[2:4]), freezer=freezer)
        assert snapshot["step"] == "height_result"
        assert snapshot["measured"]["travel_cm"] == HEIGHT
        assert snapshot["measured"]["travel_measured"] is True

        snapshot = await act(hass, session, Act("accept_step"))
        assert snapshot["step"] == "verify_offer"
        assert snapshot["actions"] == ["verify_now", "skip_verify"]

        snapshot = await act(hass, session, Act("skip_verify"))
        assert snapshot["state"] == "review"
        assert snapshot["step"] == "summary_short"
        assert snapshot["level"] == "basic"
        assert snapshot["actions"] == []
        assert snapshot["review"]["variant"] == "short"
        assert snapshot["review"]["targets"] == ["profile"]
        assert snapshot["review"]["profile_name"] == "tall"
        assert snapshot["review"]["profile_exists"] is True
        # Nothing is written about the profile, so nobody else is touched by this.
        assert snapshot["review"]["affected"] == []
        assert snapshot["check"] is None
        for one in published:
            check_the_snapshot(one)

        await save(session, "profile")
        record = the_record(hass, entry)
        assert record[CONF_PROFILE] == "tall"
        assert record["profile_wins"] is True
        assert record[CONF_HEIGHT] == HEIGHT
        assert record.get("overrides") in (None, {})
        assert the_store(hass, entry).raw_profiles == {}
        # ...and the window now moves on the profile, scaled to the travel just read.
        values = resolved_values(hass, entry)
        assert values[CONF_OPENING_TIME] == pytest.approx(OPENING)
        assert values[CONF_CLOSING_TIME] == pytest.approx(CLOSING)


async def test_path_b_checks_the_profile_against_the_shutter(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The check: up from the closed end stop to half the travel, and a tape (lot W3).

    The shutter is sent where a `set_cover_position: 50` will send it once the profile
    is saved, so what the tape should read is **half the curtain travel** - 97,5 cm of
    195 - and the window really is one of those, so that is what it reads.

    `IN_USE_YAML` and not `PROFILE_YAML`: the run is a fraction of the curtain time the
    *cover* is configured with, and the bench's shutter answers as the reference window,
    so the two have to be the same window for the bar to land where the model aimed it.
    A cover whose configuration is not its shutter is the live case, and it has its own
    test below.
    """
    async with setup_myhome(hass, tmp_path, IN_USE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)

        snapshot = await walk(hass, session, for_the_session(PATH_B[:5]), freezer=freezer)
        snapshot = await act(hass, session, Act("verify_now"))
        assert snapshot["plan"] == [*PLAN_PROFILE[:3], "verify_b", "summary"]
        assert snapshot["step"] == "measure_verify"

        # Up, from the closed end stop: the ascent is where an inherited profile is most
        # wrong (the slat phase and the opening roll), and a check made only on the way
        # down never touches either (analysis of 20 September, §5 d).
        assert runner.homed[-1] == "close"
        direction, commanded = runner.runs[-1]
        assert direction == "open"
        reading = snapshot["reading"]
        assert reading["direction"] == "open"
        assert reading["from_end_stop"] == "closed"
        assert reading["fraction"] == commanded

        # ...and the run is the model's, not half of anything: with a roll of 2.12 the
        # bar reaches half the travel at 58,7 % of the ascent's curtain time.
        assert commanded == pytest.approx(0.58702, abs=1e-4)
        assert commanded != pytest.approx(HALF_RUN)
        assert ascent_cm(commanded) == pytest.approx(HEIGHT / 2)

        # The expectation is half the travel, which is a fact about the window and not
        # an output of the model being questioned: the one number the person holding the
        # tape can check without believing anything.
        assert reading["expected_cm"] == pytest.approx(HEIGHT / 2)
        assert reading["tolerance_cm"] == 4.0
        # ...and the sentences name the percentage of the TRAVEL, not of the run's time.
        assert snapshot["placeholders"]["percent"] == 50

        snapshot = await act(hass, session, Act("submit", str(HEIGHT / 2)))
        assert snapshot["state"] == "checking"
        assert snapshot["step"] == "verify_result"
        check = snapshot["check"]
        assert check["fraction"] == pytest.approx(commanded)
        assert check["measured_cm"] == pytest.approx(HEIGHT / 2)
        assert check["predicted_cm"] == pytest.approx(HEIGHT / 2)
        assert check["gap_cm"] == 0.0
        # The threshold, four centimetres since 20 September and the same one in the
        # dialog: it is what the panel's screens are written against ("a basic
        # calibration usually ends up within about 4 cm").
        assert check["threshold_cm"] == REFINE_THRESHOLD_CM == 4.0
        # The profile lives in `cover_profiles:` and was never measured here, so how
        # well it was measured is not known and is not guessed at.
        assert check["profile_level"] is None
        assert check["profile_check_cm"] is None
        assert snapshot["placeholders"]["deviation"] == 0.0
        # Nothing to correct, so the correction is not offered.
        assert snapshot["actions"] == ["accept_step", "repeat_tape"]

        snapshot = await act(hass, session, Act("accept_step"))
        assert snapshot["step"] == "summary_short"
        assert snapshot["review"]["accuracy_cm"] == 0.0
        assert snapshot["review"]["check_fraction"] == pytest.approx(commanded)
        for one in published:
            check_the_snapshot(one)


async def test_a_check_far_enough_out_offers_the_correction_and_keeps_the_travel(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Beyond 4 cm the profile is the thing in doubt, and path C is offered on the spot.

    Four and not three since 20 September: the panel's own screens say a basic
    calibration ends up within about 4 cm, and a check that offered a correction at
    3,1 cm would be contradicting the sentence the same route had just shown.

    And the travel just read with a tape survives the jump: it is the same window and
    the same tape, so a correction that asked for it again would be asking the user to
    walk back to the shutter for a number nobody doubts (`async_step_path_c`, :1823).
    """
    async with setup_myhome(hass, tmp_path, IN_USE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)

        await walk(hass, session, for_the_session(PATH_B[:5]), freezer=freezer)
        await act(hass, session, Act("verify_now"))
        # Five centimetres above half the travel, which is more than the threshold.
        snapshot = await act(hass, session, Act("submit", str(HEIGHT / 2 + 5.0)))
        assert snapshot["check"]["gap_cm"] == 5.0
        assert snapshot["actions"] == ["path_c", "accept_step", "repeat_tape"]

        # ...and the threshold is applied to the number the screen shows, not to the
        # one behind it: 4.04 cm reads "4,0 cm", and a screen that offered a correction
        # beside that sentence would be arguing with itself over a digit nobody can see.
        await act(hass, session, Act("repeat_tape"))
        snapshot = await act(hass, session, Act("submit", str(HEIGHT / 2 + 4.04)))
        assert snapshot["placeholders"]["deviation"] == 4.0
        assert snapshot["actions"] == ["accept_step", "repeat_tape"]

        await act(hass, session, Act("repeat_tape"))
        await act(hass, session, Act("submit", str(HEIGHT / 2 + 5.0)))

        snapshot = await act(hass, session, Act("path_c"))
        assert snapshot["step"] == "path_c"
        assert snapshot["path"] == "path_c"
        assert snapshot["form"]["suggested"] == "tall"
        # The verification belonged to the path that has just been left behind, and it
        # goes with it: a screen of a *correction* publishing a check with path B's
        # threshold on it would be describing a conversation that no longer exists.
        assert snapshot["check"] is None

        snapshot = await act(hass, session, Act("submit", "tall"))
        assert snapshot["step"] == "refine_scope"
        assert snapshot["check"] is None
        assert snapshot["actions"] == ["times_only", "times_and_rolls", "points_only"]
        assert snapshot["measured"]["travel_cm"] == HEIGHT
        assert snapshot["measured"]["travel_measured"] is True
        for one in published:
            check_the_snapshot(one)


async def test_a_start_that_names_a_profile_opens_the_choice_on_it(
    hass: HomeAssistant, tmp_path
) -> None:
    """"Ne ho gia' misurata una uguale" arrives from the panel with the kind named.

    The session is still born on the form and not past it: `start` never skips a
    screen, and the profile is what the choice opens on rather than what it answers.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry, path="path_b", profile="tall")

        snapshot = session.snapshot()
        assert snapshot["step"] == "path_b"
        assert snapshot["profile"] == "tall"
        assert snapshot["form"]["suggested"] == "tall"
        assert snapshot["plan"] == []
        assert runner.log == []
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


async def test_a_start_for_a_correction_with_no_profile_named_opens_the_choice(
    hass: HomeAssistant, tmp_path
) -> None:
    """"Correggi..." pressed without saying which profile: the form, opened on its own.

    The choice is a list of every profile there is, and it opens on the one this
    window follows today - not on the first name in the list, which for a window the
    file already assigns would be telling the user something untrue about their own
    installation.
    """
    async with setup_myhome(hass, tmp_path, ASSIGNED_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        store = the_store(hass, entry)
        await store.async_set_profile(
            "aaa",
            {
                CONF_NAME: "aaa",
                "reference_height": HEIGHT,
                CONF_OPENING_TIME: OPENING,
                CONF_CLOSING_TIME: CLOSING,
                CONF_SLAT_TIME: SLAT,
                CONF_OPENING_ROLL: ROLL_UP,
                CONF_CLOSING_ROLL: ROLL_DOWN,
            },
        )
        session = await open_session(hass, entry, path="path_c")

        snapshot = session.snapshot()
        assert snapshot["step"] == "path_c"
        assert snapshot["path"] == "path_c"
        assert snapshot["profile"] is None
        assert snapshot["form"]["choices"] == ["aaa", "tall"]
        assert snapshot["form"]["suggested"] == "tall"
        assert runner.log == []
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


async def test_reading_the_screens_of_a_check_never_touches_the_shutter(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The lesson of the v2 panel, on the screens this lot adds.

    A redraw that re-entered the step restarted its movements there, so a phone waking
    up sent a shutter off again. Read the offer of a check, the reading it asks for and
    the answer it gives as often as you like: the fake runner's log stays where the
    walk left it.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, for_the_session(PATH_B[:4]), freezer=freezer)

        for one, step in (
            (Act("accept_step"), "verify_offer"),
            (Act("verify_now"), "measure_verify"),
            (Act("submit", str(descent_cm(0.5))), "verify_result"),
        ):
            assert (await act(hass, session, one))["step"] == step
            so_far = list(runner.log)
            for _ in range(3):
                session.snapshot()
                session.attach(CLIENT)
                session.attach(OTHER_CLIENT)
                session.heartbeat(CLIENT)
                assert current(hass, entry) is session
                await hass.async_block_till_done()
            assert runner.log == so_far, step
            assert session.snapshot()["step"] == step
        await session.async_cancel(CLIENT)


async def test_a_verification_can_be_made_again(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Ripeti la misura" on a check: the run is made again and the answer goes with it.

    A verification fits nothing, so there is no reading to take back - but the answer
    it gave is about a shutter that is about to be moved again, and a screen that kept
    it would be reporting a gap measured before the run it is describing.

    And the run back to the closed end stop is planned on where the bar **is**. The
    check left it at half the travel, not at 0.59 of one, and a bar that announced the
    difference would be the promise of live finding 22 all over again.
    """
    async with setup_myhome(hass, tmp_path, IN_USE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)
        await walk(hass, session, for_the_session(PATH_B[:5]), freezer=freezer)
        await act(hass, session, Act("verify_now"))
        snapshot = await act(hass, session, Act("submit", str(HEIGHT / 2 + 4.0)))
        assert snapshot["check"]["gap_cm"] == 4.0
        runs = len(runner.runs)

        snapshot = await act(hass, session, Act("repeat_tape"))
        assert snapshot["step"] == "measure_verify"
        assert snapshot["check"] is None
        assert len(runner.runs) == runs + 1

        # The homing this repetition opened with: half the curtain to run down, plus
        # the slat phase it closes with. Half of the *time* would have promised 14.7 s
        # of a movement that takes 13.2.
        homings = [
            one["movement"]
            for one in published
            if one["step"] == "verify_b" and one["movement"] is not None
        ]
        assert homings, "the repetition did not home"
        assert homings[-1]["direction"] == "close"
        assert homings[-1]["planned_s"] == pytest.approx((CLOSING - SLAT) * 0.5 + SLAT)

        snapshot = await act(hass, session, Act("submit", str(HEIGHT / 2)))
        assert snapshot["check"]["gap_cm"] == 0.0
        assert snapshot["actions"] == ["accept_step", "repeat_tape"]
        check_the_snapshot(snapshot)


async def test_a_check_whose_profile_went_away_reports_no_gap_at_all(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one way a verification ends up with nothing to verify against.

    The profile this window was told to follow was deleted while the session stood
    open. The screen then reports no gap rather than inventing one, and the three
    numbers of the check are `null` - which is also why the correction is not offered
    off the back of it.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        store = the_store(hass, entry)
        await store.async_set_profile(
            "stored",
            {
                CONF_NAME: "stored",
                "reference_height": HEIGHT,
                CONF_OPENING_TIME: OPENING,
                CONF_CLOSING_TIME: CLOSING,
                CONF_SLAT_TIME: SLAT,
                CONF_OPENING_ROLL: ROLL_UP,
                CONF_CLOSING_ROLL: ROLL_DOWN,
            },
        )
        session = await open_session(hass, entry)
        await act(hass, session, Act("path_b"))
        await act(hass, session, Act("submit", "stored"))
        await walk(hass, session, for_the_session(PATH_B[2:5]), freezer=freezer)
        await act(hass, session, Act("verify_now"))
        await store.async_remove_profile("stored")

        snapshot = await act(hass, session, Act("submit", str(descent_cm(0.5))))
        assert snapshot["step"] == "verify_result"
        assert snapshot["check"]["predicted_cm"] is None
        assert snapshot["check"]["gap_cm"] is None
        assert snapshot["check"]["measured_cm"] == pytest.approx(descent_cm(0.5))
        assert snapshot["placeholders"]["deviation"] == 0.0
        assert snapshot["actions"] == ["accept_step", "repeat_tape"]
        check_the_snapshot(snapshot)


async def test_a_verification_the_arithmetic_refuses_is_a_problem_and_not_a_crash(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, monkeypatch
) -> None:
    """A reading the model cannot place leaves a way out, as everywhere else.

    `fit_from_run` raises for a point the model cannot explain - a fraction outside
    (0, 1], a travel of nothing - and the verification asks the fit for a model. The
    dialog's own screen for a measurement that cannot be made into one is `bad_point`,
    and it offers the step again.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, for_the_session(PATH_B[:5]), freezer=freezer)
        await act(hass, session, Act("verify_now"))

        def refuse(**_kwargs: Any) -> None:
            raise CalibrationError(REASON_BAD_POINT, "a reading the model cannot place")

        monkeypatch.setattr(calibration_session.measure, "model_values", refuse)
        snapshot = await act(hass, session, Act("submit", str(descent_cm(0.5))))
        assert snapshot["step"] == "problem_bad_point"
        assert snapshot["problem"] == {"code": "bad_point"}
        assert snapshot["actions"] == ["repeat_step"]
        assert snapshot["check"] is None
        check_the_snapshot(snapshot)


async def test_a_verification_read_where_the_shutter_no_longer_is_says_so(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The wall switch while the tape is being held against the check's own position.

    The reading is about a place the shutter has left, so the answer it would give is
    about nothing. The field stays on the screen - the user may well have measured
    before anybody touched it, and they are the one who knows - but the way forward is
    the run again, and it is the only way forward offered.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, for_the_session(PATH_B[:5]), freezer=freezer)
        await act(hass, session, Act("verify_now"))
        assert session.snapshot()["step"] == "measure_verify"

        hass.states.async_set(ENTITY, STATE_OPENING)
        await hass.async_block_till_done()

        snapshot = session.snapshot()
        assert snapshot["step"] == "measure_verify"
        assert snapshot["notice"] == "reading_stale"
        assert snapshot["external_move"] is True
        assert snapshot["form"]["field"] == "measured_cm"
        assert snapshot["actions"] == ["repeat_tape"]
        assert snapshot["check"] is None
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


async def test_the_check_says_how_well_the_profile_it_questions_was_measured(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """4 cm means nothing against a profile worth 4 cm and something against one worth 1.

    The threshold stays a fixed 4 cm (SPEC decision 20, amended 20 September); what the snapshot
    adds is the level of the profile being questioned and the gap its *own* check
    reported, read off the `raw` block that calibration kept - so the number can be
    read against something rather than taken on its own.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        store = the_store(hass, entry)
        await store.async_set_profile(
            "measured",
            {
                CONF_NAME: "measured",
                "reference_height": HEIGHT,
                CONF_OPENING_TIME: OPENING,
                CONF_CLOSING_TIME: CLOSING,
                CONF_SLAT_TIME: SLAT,
                CONF_OPENING_ROLL: ROLL_UP,
                CONF_CLOSING_ROLL: ROLL_DOWN,
                CONF_RAW: {"precise": True, "deviation_cm": -1.5},
            },
        )
        session = await open_session(hass, entry)
        await act(hass, session, Act("path_b"))
        await act(hass, session, Act("submit", "measured"))
        await walk(hass, session, for_the_session(PATH_B[2:5]), freezer=freezer)
        await act(hass, session, Act("verify_now"))
        snapshot = await act(hass, session, Act("submit", str(descent_cm(0.5))))

        assert snapshot["check"]["profile_level"] == "thorough"
        # A distance, not a direction: the profile's own check was 1.5 cm out.
        assert snapshot["check"]["profile_check_cm"] == 1.5
        check_the_snapshot(snapshot)


async def test_the_check_catches_the_window_of_the_twentieth_of_september(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The case this lot exists for, with the numbers measured on the wall.

    A 198 cm window is told to follow the profile of a 110 cm one. The scaling law gets
    the run times nearly right and the roll coefficients wrong by 0,8, so the command
    the user really uses - `set_cover_position: 50` from closed - overshoots by about
    nine centimetres. The check has one job: to say so before the profile is saved.

    Both checks are computed here on the same bench, and the contrast is the finding:

    * **half the closing time, from the top** (what the dialog does, and what the panel
      did until this lot): about 3 cm - **under** the four-centimetre threshold, so the
      profile would have been accepted. That is what happened on 20 September;
    * **half the travel, going up from closed** (this lot): about 9 cm, twice the
      threshold, and the correction is offered on the spot.

    The descending check is not merely less sensitive: it compares two outputs of the
    same wrong model, so part of the error cancels itself - the expectation falls
    *together with* the place the model thinks it is stopping.
    """
    async with setup_myhome(hass, tmp_path, LIVE_YAML) as (entry, _commands):
        runner = ConfiguredWindow(
            entity_object(hass, COVER, DEVICE_KEY), LIVE_WINDOW, LIVE_WINDOW, LIVE_TRAVEL
        )
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)

        await act(hass, session, Act("path_b"))
        await act(hass, session, Act("submit", "short"))
        snapshot = await walk(
            hass,
            session,
            (Act("tape_start"), Act("submit", str(LIVE_TRAVEL)), Act("accept_step")),
            freezer=freezer,
        )
        assert snapshot["step"] == "verify_offer"

        snapshot = await act(hass, session, Act("verify_now"))
        direction, commanded = runner.runs[-1]
        assert direction == "open"
        assert runner.seconds_of(direction, commanded) == pytest.approx(15.43, abs=0.05)
        # Where the bottom edge really ends up: 108,6 cm calculated, 107 cm measured on
        # the wall on 20 September - the difference is the stop latency, the start delay
        # and where the tape was held, none of which is modelled here.
        really = runner.where_the_bar_is(direction, commanded)
        assert really == pytest.approx(108.6, abs=0.2)
        assert snapshot["reading"]["expected_cm"] == pytest.approx(LIVE_TRAVEL / 2)

        snapshot = await act(hass, session, Act("submit", str(really)))
        assert snapshot["check"]["predicted_cm"] == pytest.approx(99.0)
        assert snapshot["check"]["gap_cm"] == pytest.approx(9.6, abs=0.2)
        assert snapshot["check"]["gap_cm"] > REFINE_THRESHOLD_CM
        assert snapshot["actions"] == ["path_c", "accept_step", "repeat_tape"]

        # ...and what the check it replaced would have said about the same window.
        inherited = derive_cover_from_profile(
            merged_profiles(yaml_profiles(hass, entry), {})["short"], LIVE_TRAVEL
        )
        down = runner.where_the_bar_is(DIRECTION_CLOSE, VERIFY_RUN_PROFILE)
        was_predicted = calibration_descent_cm(
            inherited[CONF_CLOSING_ROLL],
            inherited[CONF_SLAT_TIME],
            LIVE_TRAVEL,
            inherited[CONF_CLOSING_TIME],
            runner.seconds_of(DIRECTION_CLOSE, VERIFY_RUN_PROFILE),
        )
        assert abs(down - was_predicted) == pytest.approx(3.2, abs=0.3)
        assert abs(down - was_predicted) < REFINE_THRESHOLD_CM
        for one in published:
            check_the_snapshot(one)


async def test_a_check_this_cover_cannot_make_is_a_problem_and_not_a_shorter_run(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The profile wants more seconds than a whole run of this cover has.

    The run primitive is given a fraction of the curtain time the *cover* is configured
    with, and a fraction above 1 is clamped to a full run: the shutter would go to its
    end stop and the tape would be held against a check that was never made. A cover
    configured as a tenth of the window it really is says so instead - `bad_point`, the
    dialog's own screen for a measurement that cannot be made, with the step on offer
    again.
    """
    # The **cover's** three times and not the profile's, which is why the replacement is
    # counted: the two blocks carry the same three keys at the same indentation, and the
    # cover's come first.
    quick = IN_USE_YAML.replace(
        f"      opening_time: {OPENING}\n      closing_time: {CLOSING}\n      slat_time: {SLAT}\n",
        "      opening_time: 2.4\n      closing_time: 2.3\n      slat_time: 0.4\n",
        1,
    )
    async with setup_myhome(hass, tmp_path, quick) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)

        await walk(hass, session, for_the_session(PATH_B[:5]), freezer=freezer)
        runs = len(runner.runs)
        snapshot = await act(hass, session, Act("verify_now"))
        assert snapshot["step"] == "problem_bad_point"
        assert snapshot["problem"] == {"code": "bad_point"}
        assert snapshot["actions"] == ["repeat_step"]
        assert snapshot["check"] is None
        # Nothing was sent anywhere: the run that could not be made was not made.
        assert len(runner.runs) == runs
        for one in published:
            check_the_snapshot(one)
        await session.async_cancel(CLIENT)


async def test_a_check_that_gives_up_before_its_run_takes_its_answer_with_it(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A problem screen says a measurement could not be made; it does not give a verdict.

    "Repeat the measurement" on a verification re-enters the stage, and the stage works
    out where to send the shutter before it sends it anywhere. If the profile went out
    from under the conversation in between, it gives up there - and the answer of the
    verification *before* has to go with it, or a second client attaching to the session
    reads the verdict of a run nobody made.

    The invariant is `check_the_snapshot`'s now, so every walk of every path checks it;
    this is the one walk that reaches the state.
    """
    async with setup_myhome(hass, tmp_path, IN_USE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        store = the_store(hass, entry)
        await store.async_set_profile(
            "stored",
            {
                CONF_NAME: "stored",
                "reference_height": HEIGHT,
                CONF_OPENING_TIME: OPENING,
                CONF_CLOSING_TIME: CLOSING,
                CONF_SLAT_TIME: SLAT,
                CONF_OPENING_ROLL: ROLL_UP,
                CONF_CLOSING_ROLL: ROLL_DOWN,
            },
        )
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)

        await act(hass, session, Act("path_b"))
        await act(hass, session, Act("submit", "stored"))
        await walk(hass, session, for_the_session(PATH_B[2:5]), freezer=freezer)
        await act(hass, session, Act("verify_now"))
        snapshot = await act(hass, session, Act("submit", str(HEIGHT / 2 + 5.0)))
        assert snapshot["check"]["gap_cm"] == 5.0

        await store.async_remove_profile("stored")
        snapshot = await act(hass, session, Act("repeat_tape"))
        assert snapshot["step"] == "problem_bad_point"
        assert snapshot["problem"] == {"code": "bad_point"}
        assert snapshot["actions"] == ["repeat_step"]
        # The verdict of the run before it is gone, not carried onto a screen that says
        # the measurement could not be made at all.
        assert snapshot["check"] is None
        assert snapshot["placeholders"].get("deviation") is None
        for one in published:
            check_the_snapshot(one)
        await session.async_cancel(CLIENT)


async def test_the_panel_s_check_of_a_profile_is_not_the_dialog_s(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The one place the two conversations deliberately ask different questions.

    Everywhere else path B stores what the dialog stores, key for key
    (`test_the_session_stores_what_the_dialog_stores`). Its check does not, and this
    says exactly how: the dialog runs **down** from the top for half of the closing
    curtain time and compares the tape with what the profile predicts for the seconds
    the motor spent; the panel runs **up** from the closed end stop to half the curtain
    travel and compares the tape with half the travel.

    `calibration_flow.py` is not touched by any of it: the dialog's constants are
    imported and read, and what changed is which of them the session uses.
    """
    async with setup_myhome(hass, tmp_path, IN_USE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        # `PATH_B_CHECKED` is the conversation that left the dialog parity behind, so
        # this is where it is walked: the same list, minus the reading and what follows.
        await walk(hass, session, for_the_session(PATH_B_CHECKED[:-2]), freezer=freezer)
        snapshot = session.snapshot()
        assert snapshot["step"] == "measure_verify"

        direction, commanded = runner.runs[-1]
        assert (direction, commanded) != (DIRECTION_CLOSE, VERIFY_RUN_PROFILE)
        assert direction == "open"
        # The dialog's own run is still in the dialog's own constants, unchanged.
        assert VERIFY_RUN_PROFILE == HALF_RUN == 0.5
        assert snapshot["reading"]["expected_cm"] == pytest.approx(HEIGHT / 2)
        assert snapshot["reading"]["expected_cm"] != pytest.approx(
            descent_cm(VERIFY_RUN_PROFILE)
        )

        # The same tape reading, read by the two rules: half the travel says the window
        # is right, half the closing time says it is 17 cm out - about a window whose
        # profile is its own measurements.
        snapshot = await act(hass, session, Act("submit", str(HEIGHT / 2)))
        assert snapshot["check"]["gap_cm"] == 0.0
        assert abs(HEIGHT / 2 - descent_cm(VERIFY_RUN_PROFILE)) > REFINE_THRESHOLD_CM
        check_the_snapshot(snapshot)


# --------------------------------------------------------------------------------------
# Path C
# --------------------------------------------------------------------------------------
async def test_a_correction_starts_from_the_profile_and_the_travel_this_window_has(
    hass: HomeAssistant, tmp_path
) -> None:
    """The form opens on the profile this window follows, and keeps its known travel.

    Neither is measured here: the travel is what the record or the file already says
    about *this* window - never the reference height of the profile, which is another
    window's - and it is carried so that the summary does not show "-" for it and Save
    does not write a record that has forgotten it (final review, BUG-A).
    """
    async with setup_myhome(hass, tmp_path, FOLLOWER_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        snapshot = await act(hass, session, Act("path_c"))
        assert snapshot["form"]["choices"] == ["tall"]
        assert snapshot["form"]["suggested"] == "tall"

        snapshot = await act(hass, session, Act("submit", "tall"))
        assert snapshot["step"] == "refine_scope"
        assert snapshot["path"] == "path_c"
        assert snapshot["profile"] == "tall"
        assert snapshot["scope"] is None
        assert snapshot["measured"]["travel_cm"] == HEIGHT
        assert snapshot["measured"]["travel_measured"] is False
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


async def test_a_correction_never_starts_from_another_window_s_travel(
    hass: HomeAssistant, tmp_path
) -> None:
    """A window with no travel of its own starts the correction without one.

    It follows a profile, so a travel *can* be resolved for it - the profile's
    reference height, which is the window the profile was measured on. Carrying that
    into this conversation would scale every reading by somebody else's window and
    write it into this one's record as if it had been measured here. The screen says
    "-" instead, and the thorough calibration reads the tape first.
    """
    async with setup_myhome(hass, tmp_path, ASSIGNED_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await act(hass, session, Act("path_c"))
        snapshot = await act(hass, session, Act("submit", "tall"))

        assert snapshot["step"] == "refine_scope"
        assert snapshot["measured"]["travel_cm"] is None
        assert snapshot["measured"]["travel_measured"] is False

        snapshot = await act(hass, session, Act("points_only"))
        assert snapshot["plan"] == list(PLAN_PRECISE_TRAVEL)
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


async def test_a_start_that_names_a_scope_highlights_it_without_choosing_it(
    hass: HomeAssistant, tmp_path
) -> None:
    """"Calibrazione approfondita" on the detail screen arrives with its scope named.

    The session is born on `refine_scope` with the profile chosen - which is a screen
    before any movement - and the scope waits in `intent` for the user to press it. A
    start that chose it would be a movement nobody asked for.
    """
    async with setup_myhome(hass, tmp_path, FOLLOWER_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(
            hass, entry, path="path_c", profile="tall", scope="points_only"
        )

        snapshot = session.snapshot()
        assert snapshot["step"] == "refine_scope"
        assert snapshot["intent"] == {"scope": "points_only"}
        assert snapshot["scope"] is None
        assert snapshot["measured"]["travel_cm"] == HEIGHT
        assert snapshot["plan"] == []
        assert runner.log == []
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


@pytest.mark.parametrize(
    ("scope", "plan", "yaml_text"),
    [
        ("times_only", PLAN_TIMES, PROFILE_YAML),
        ("times_and_rolls", PLAN_TIMES_AND_ROLLS, PROFILE_YAML),
        ("points_only", PLAN_PRECISE, IN_USE_YAML),
        ("points_only", PLAN_PRECISE_TRAVEL, NO_TRAVEL_YAML),
    ],
    ids=["times_only", "times_and_rolls", "points_only", "points_only_without_a_travel"],
)
async def test_each_scope_installs_the_plan_the_dialog_installs(
    hass: HomeAssistant, tmp_path, scope: str, plan: tuple[str, ...], yaml_text: str
) -> None:
    """The three scopes, and the one that comes in two shapes.

    The thorough calibration is the same plan every time it is reached, with the
    curtain travel in front of it for a window nobody has ever measured one for: every
    reading of the phase is a number of centimetres out of that travel.
    """
    async with setup_myhome(hass, tmp_path, yaml_text) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry, path="path_c", profile="tall")

        snapshot = await act(hass, session, Act(scope))
        assert snapshot["scope"] == scope
        assert snapshot["plan"] == list(plan)
        assert snapshot["plan_index"] == 0
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


async def test_the_thorough_calibration_alone_adopts_the_times_in_use(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Nothing is pressed for, so the run times are the ones the cover moves on today.

    And the four readings recover the two roll coefficients over them: the window's
    times are right and its roll is not, which is what "it misses at mid-travel" means
    and what this scope exists for. What is stored is those two coefficients and
    nothing else, so a later correction of the profile still reaches this window.
    """
    async with setup_myhome(hass, tmp_path, IN_USE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)

        snapshot = await walk(
            hass, session, for_the_session(PATH_C_POINTS[:3]), freezer=freezer
        )
        assert snapshot["level"] == "thorough"
        assert snapshot["measured"]["times_adopted"] is True
        assert snapshot["measured"]["opening_time_s"] == pytest.approx(OPENING)
        assert snapshot["measured"]["closing_time_s"] == pytest.approx(CLOSING)
        assert snapshot["measured"]["slat_time_s"] == pytest.approx(SLAT)
        assert runner.log == []

        snapshot = await walk(
            hass, session, for_the_session(PATH_C_POINTS[3:]), freezer=freezer
        )
        assert snapshot["step"] == "summary_precise"
        assert snapshot["review"]["variant"] == "precise"
        assert snapshot["review"]["targets"] == ["cover_only"]
        # The readings found the shutter's own coefficients again.
        assert snapshot["fit"]["closing"]["roll"] == pytest.approx(ROLL_DOWN, abs=0.01)
        assert snapshot["fit"]["opening"]["roll"] == pytest.approx(ROLL_UP, abs=0.01)
        # ...and the time scale is pinned, because nobody pressed anything.
        assert snapshot["fit"]["closing"]["time_scale"] == 1.0
        assert snapshot["review"]["accuracy_cm"] == pytest.approx(0.0, abs=0.5)
        for one in published:
            check_the_snapshot(one)

        await save(session, "cover_only")
        record = the_record(hass, entry)
        assert sorted(record["overrides"]) == sorted([CONF_CLOSING_ROLL, CONF_OPENING_ROLL])
        assert record[CONF_PROFILE] == "tall"
        assert record["profile_wins"] is True
        assert record[CONF_RAW]["times_measured"] is False


async def test_the_thorough_calibration_grafted_onto_a_summary(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Continua con la calibrazione approfondita", pressed on path A's summary.

    The presses are not repeated: the plan replaces the tail of the one that got here,
    and the four readings are fitted over the times already measured - which is what
    lets the fit solve a scale factor on them as well as the roll, and is the whole
    reason the thorough level is more than "more readings".
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        published: list[dict[str, Any]] = []
        session.subscribe(published.append)

        snapshot = await walk(hass, session, for_the_session(PATH_A), freezer=freezer)
        assert snapshot["step"] == "summary_basic"
        assert snapshot["actions"] == ["refine"]
        assert snapshot["review"]["accuracy_cm"] is None
        basic = snapshot["plan"]

        snapshot = await act(hass, session, Act("refine"))
        assert snapshot["level"] == "thorough"
        assert snapshot["plan"] == [*basic[:-1], *PLAN_PRECISE]
        assert snapshot["step"] == "tape_brief"
        # The summary that was on the screen a moment ago is not an answer any more.
        assert snapshot["review"] is None

        snapshot = await walk(hass, session, for_the_session(THE_FOUR_READINGS), freezer=freezer)
        assert snapshot["step"] == "summary_precise"
        assert snapshot["review"]["variant"] == "precise"
        assert snapshot["review"]["targets"] == ["profile", "cover_only"]
        assert snapshot["check"]["fraction"] == VERIFY_RUN
        # ...which is a position nothing was fitted to. That is what makes it a
        # question put to the model rather than a repetition of one of its inputs.
        assert snapshot["check"]["fraction"] not in (0.25, 0.5, 0.75)
        # The check questions a fit, not a profile, so there is no threshold to read
        # it against and nothing to compare it with.
        assert snapshot["check"]["threshold_cm"] is None
        assert snapshot["check"]["profile_level"] is None
        assert snapshot["check"]["gap_cm"] == pytest.approx(0.0, abs=1.0)
        # Three readings per direction: every one of them has a residual of its own.
        for direction in ("opening", "closing"):
            points = snapshot["fit"][direction]["points"]
            assert len(points) == 3
            assert all(point["residual_cm"] is not None for point in points)
        for one in published:
            check_the_snapshot(one)


async def test_a_correction_can_go_on_to_the_thorough_calibration_too(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The same offer at the end of a correction, and the travel decides the plan.

    Nobody knows this window's travel here, so the thorough calibration grafted onto
    the summary of a correction reads it first: every reading of the phase is a number
    of centimetres out of it.
    """
    async with setup_myhome(hass, tmp_path, NO_TRAVEL_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)

        snapshot = await walk(hass, session, for_the_session(PATH_C_TIMES), freezer=freezer)
        assert snapshot["step"] == "summary_correction"
        assert snapshot["actions"] == ["refine"]
        assert snapshot["measured"]["travel_cm"] is None

        snapshot = await act(hass, session, Act("refine"))
        walked, thorough = snapshot["plan"][:3], snapshot["plan"][3:]
        assert walked == list(PLAN_TIMES[:-1])
        assert sorted(thorough) == sorted(PLAN_PRECISE_TRAVEL)
        # The briefing and the travel stay where the plan puts them; the four readings
        # are dealt from the end stop the shutter is standing at, which is the bottom.
        assert thorough[:2] == ["tape_brief", "height_read"]
        assert thorough[2] == "quarter_up"
        assert snapshot["step"] == "tape_brief"
        assert snapshot["placeholders"]["readings"] == len(PLAN_PRECISE_TRAVEL) - 2
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


async def test_a_correction_s_stopwatch_starts_from_a_known_end_stop_too(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """The wall switch during a correction's briefing, answered as path A answers it.

    A correction is the one path whose whole point is that the model is wrong, so the
    homing before its first timed run is bounded by a run time nobody trusts; a
    stopwatch started from a point nobody knows would measure something else entirely.
    The session takes the shutter back to the end stop by itself and says it did.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        runner = FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, for_the_session(PATH_C_TIMES[:4]), freezer=freezer)
        assert session.snapshot()["step"] == "open_brief"

        hass.states.async_set(ENTITY, STATE_OPENING)
        await hass.async_block_till_done()
        homings = len(runner.homed)

        snapshot = await act(hass, session, Act("open_start"), freezer=freezer)
        assert snapshot["step"] == "open_brief"
        assert snapshot["notice"] == "rehomed"
        assert snapshot["position_known"] == "closed"
        assert len(runner.homed) == homings + 1
        assert runner.started == []
        check_the_snapshot(snapshot)
        await session.async_cancel(CLIENT)


# --------------------------------------------------------------------------------------
# What the two conversations store
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("steps", "target", "yaml_text"),
    [
        (PATH_B, "profile", PROFILE_YAML),
        (PATH_C_TIMES, "cover_only", PROFILE_YAML),
        (PATH_C_ROLLS, "cover_only", PROFILE_YAML),
        (PATH_C_POINTS, "cover_only", IN_USE_YAML),
        (PATH_C_THOROUGH, "cover_only", PROFILE_YAML),
    ],
    ids=[
        "path_b",
        "times_only",
        "times_and_rolls",
        "points_only",
        "correction_then_thorough",
    ],
)
async def test_the_session_stores_what_the_dialog_stores(
    hass: HomeAssistant,
    tmp_path,
    freezer: FrozenDateTimeFactory,
    steps: tuple[Step, ...],
    target: str,
    yaml_text: str,
) -> None:
    """Paths B and C write the dialog's record, key for key (SPEC §3.9).

    The two conversations share their arithmetic and not their conversation, so this
    walks both of them over the same shutter with the same clock and compares what
    reached the store - the assignment, `profile_wins`, the values, the source and the
    measurements kept beside them. Only the wall clock and the two keys that say *who*
    wrote it are left out.

    **Path B with its check is not here any more** (lot W3): the two conversations now
    ask the shutter different questions, so the gap they store is a different number
    about a different run. The divergence is the point, and it is tested as such in
    `test_the_panel_s_check_of_a_profile_is_not_the_dialog_s`; path B *without* the
    check stays, because nothing else about it moved.
    """
    by_the_dialog, profiles_by_the_dialog = await what_the_dialog_stores(
        hass, tmp_path, freezer, yaml_text, steps
    )
    async with setup_myhome(hass, storage(tmp_path, "panel"), yaml_text) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, for_the_session(steps), freezer=freezer)
        assert snapshot["state"] == "review"
        if snapshot["step"] == "summary_precise":
            # ...and the readings really were the ones the stages asked for: a thorough
            # calibration fed an ascent where it wanted a descent would still agree with
            # a dialog fed the same mistake, and agree on nonsense.
            assert snapshot["review"]["accuracy_cm"] == pytest.approx(0.0, abs=1.0)
        await save(session, target)

        store = the_store(hass, entry)
        assert comparable(store.raw_covers[UNIQUE_ID]) == comparable(by_the_dialog[UNIQUE_ID])
        assert store.raw_profiles.keys() == profiles_by_the_dialog.keys()
        assert store.raw_covers.keys() == by_the_dialog.keys()


@pytest.mark.parametrize("steps", [PATH_A, PATH_A_THOROUGH], ids=["basic", "thorough"])
async def test_path_a_saved_as_a_profile_moves_the_shutter_on_the_dialog_s_numbers(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory, steps: tuple[Step, ...]
) -> None:
    """The one deliberate difference, and the proof that it is only a difference of place.

    The dialog writes the measured numbers twice - into the profile *and* into the
    cover - so that a later edit of the profile no longer reaches the very window it
    was measured on (#270). The session writes the profile and the assignment alone.
    The record is therefore not the dialog's; what the shutter *moves on* has to be,
    key for key, and that is what is compared here.
    """
    dialog_covers, dialog_profiles = await what_the_dialog_stores(
        hass, tmp_path, freezer, PROFILE_YAML, steps
    )
    async with setup_myhome(hass, storage(tmp_path, "panel"), PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, for_the_session(steps), freezer=freezer)
        await save(session, "profile")

        record = the_record(hass, entry)
        assert record.get("overrides") in (None, {})
        assert record[CONF_PROFILE] == "tall"
        assert record["profile_wins"] is True
        # The dialog wrote the same five numbers as values of the cover's own...
        own = dialog_covers[UNIQUE_ID]["overrides"]
        assert sorted(own) == sorted(
            [
                CONF_OPENING_TIME,
                CONF_CLOSING_TIME,
                CONF_SLAT_TIME,
                CONF_OPENING_ROLL,
                CONF_CLOSING_ROLL,
            ]
        )
        # ...and the window ends up moving on exactly those numbers all the same.
        values = resolved_values(hass, entry)
        for key, number in own.items():
            assert values[key] == pytest.approx(number), key
        assert set(dialog_profiles) == {"tall"}


async def test_path_a_saved_for_this_shutter_alone_is_the_dialog_s_record(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """"Salva solo per questa tapparella": the dialog's write, without the assignment.

    The path measured a window; it said nothing about which kind of shutter it is, so
    the assignment is left exactly as it was found and no profile is written.
    """
    dialog_covers, _profiles = await what_the_dialog_stores(
        hass, tmp_path, freezer, PROFILE_YAML, PATH_A
    )
    async with setup_myhome(hass, storage(tmp_path, "panel"), PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await walk(hass, session, for_the_session(PATH_A), freezer=freezer)
        await save(session, "cover_only")

        record = the_record(hass, entry)
        assert record["overrides"] == pytest.approx(dialog_covers[UNIQUE_ID]["overrides"])
        assert record[CONF_HEIGHT] == dialog_covers[UNIQUE_ID][CONF_HEIGHT]
        # The dialog names the profile it has just written; this exit writes none.
        assert record.get(CONF_PROFILE) is None
        assert record.get("profile_wins", False) is False
        assert the_store(hass, entry).raw_profiles == {}


# --------------------------------------------------------------------------------------
# What the review says before any of that happens
# --------------------------------------------------------------------------------------
async def test_the_review_of_a_correction_names_the_keys_it_replaces_and_keeps(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A correction writes only what it measured, over whatever was already there."""
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, for_the_session(PATH_C_TIMES), freezer=freezer)

        review = snapshot["review"]
        assert review["variant"] == "correction"
        assert review["replacing"] == ["opening_time_s", "closing_time_s", "slat_time_s"]
        assert review["keeping"] == ["travel_cm"]
        assert review["affected"] == []
        rows = {row["key"]: row for row in review["rows"]}
        assert rows["opening_time_s"]["before"] == pytest.approx(FILE_OPENING)
        assert rows["opening_time_s"]["after"] == pytest.approx(OPENING, abs=0.1)
        # The two coefficients were not measured here and move all the same: the
        # record now says this window follows `tall` *above* the keys the file writes
        # for it, which is what a correction confirms. Nothing changes silently - it is
        # on the screen, in the rows the user reads before pressing Save.
        assert rows[CONF_OPENING_ROLL]["before"] == pytest.approx(FILE_ROLL)
        assert rows[CONF_OPENING_ROLL]["after"] == pytest.approx(ROLL_UP)
        check_the_snapshot(snapshot)


async def test_the_review_of_a_correction_warns_about_the_key_nobody_measured(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """Confirming the profile can move a bus cost the file writes for this window.

    `stop_latency` is not measured by any path; it changes because the record now says
    the profile wins over the keys the file writes. Nothing changes silently: the
    review says so, and the panel shows it as a warning.
    """
    async with setup_myhome(hass, tmp_path, BUS_COST_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, for_the_session(PATH_C_TIMES), freezer=freezer)

        effects = {row["key"]: row for row in snapshot["review"]["side_effects"]}
        assert "stop_latency_s" in effects
        assert effects["stop_latency_s"]["before"] == pytest.approx(0.35)
        assert effects["stop_latency_s"]["after"] != pytest.approx(0.35)
        check_the_snapshot(snapshot)


async def test_the_review_of_path_b_touches_nobody_else(
    hass: HomeAssistant, tmp_path, freezer: FrozenDateTimeFactory
) -> None:
    """A second window follows the same profile, and path B leaves it exactly alone.

    Path B names a profile and changes nothing about it. Listing its followers here
    would put a page of rows on the screen whose "before" and "after" are the same
    number, which reads as a warning about a change nobody is making - so `affected`
    is what it means: the windows a Save is about to move.
    """
    async with setup_myhome(hass, tmp_path, FOLLOWER_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        snapshot = await walk(hass, session, for_the_session(PATH_B), freezer=freezer)

        assert snapshot["review"]["profile_exists"] is True
        assert snapshot["review"]["affected"] == []
        before = resolved_values(hass, entry, f"{MAC}-2-82")
        await save(session, "profile")
        assert resolved_values(hass, entry, f"{MAC}-2-82") == pytest.approx(before)


# --------------------------------------------------------------------------------------
# The refusals these paths add
# --------------------------------------------------------------------------------------
async def test_a_profile_nobody_defines_is_refused_rather_than_shown_as_a_field_error(
    hass: HomeAssistant, tmp_path
) -> None:
    """The profile field is a choice out of a list the snapshot carries.

    A value outside it is a client sending something it was not offered, which is the
    protocol's business; every field the user *types* into answers with `form.error`
    instead.
    """
    async with setup_myhome(hass, tmp_path, PROFILE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        await act(hass, session, Act("path_b"))
        revision = session.revision

        with pytest.raises(PanelError) as refused:
            await session.async_act(CLIENT, revision, "submit", "nobody")
        assert refused.value.translation_key == "unknown_profile"
        assert session.revision == revision
        assert session.snapshot()["step"] == "path_b"
        await session.async_cancel(CLIENT)


async def test_the_paths_a_window_with_no_profile_has(hass: HomeAssistant, tmp_path) -> None:
    """The last two paths need a profile to follow, so they are not offered without one."""
    async with setup_myhome(hass, tmp_path, NO_TRAVEL_YAML.replace(
        f"""  cover_profiles:
    tall:
      reference_height: {HEIGHT}
      opening_time: {OPENING}
      closing_time: {CLOSING}
      slat_time: {SLAT}
      opening_roll: {ROLL_UP}
      closing_roll: {ROLL_DOWN}
""",
        "",
    )) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry)
        assert session.snapshot()["actions"] == ["path_a"]

        with pytest.raises(PanelError) as refused:
            await session.async_act(CLIENT, session.revision, "path_b")
        assert refused.value.translation_key == "action_not_offered"
        await session.async_cancel(CLIENT)


async def test_the_thorough_calibration_of_a_window_the_gateway_has_forgotten(
    hass: HomeAssistant, tmp_path, monkeypatch
) -> None:
    """The one way the model in use cannot be read: the window is not configured any more.

    The entry was reloaded off an edited `myhome.yaml` under the session. There is no
    step to repeat, so the session ends the way it ends when the shutter goes away.
    """
    async with setup_myhome(hass, tmp_path, IN_USE_YAML) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        session = await open_session(hass, entry, path="path_c", profile="tall")
        monkeypatch.setattr(calibration_session, "basic_covers", lambda *args, **kwargs: {})

        snapshot = await act(hass, session, Act("points_only"))
        assert snapshot["state"] == "ended"
        assert snapshot["outcome"]["reason"] == "cover_gone"
        check_the_snapshot(snapshot)
