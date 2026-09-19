"""The whole calibration, over the socket, from `start` to what the store holds.

Every other file of the session tests one layer of it. `test_calibration_session.py`
and `test_calibration_session_paths.py` drive the **controller** directly;
`test_websocket_session.py` tests the **door** command by command and then walks the
controller behind it, which is the right shape for "does this frame answer that". What
none of them does is put a whole conversation through the door: a panel does not call
`async_act`, it sends `myhome/calibration/session/act` twenty-one times, each one
carrying the `revision` the last event gave it, and then asks for the save.

So this file walks two paths with **nothing but frames**:

* path A on a shutter nobody has measured for itself, from the `start` that opens the
  choice of route to the `save` that writes a profile - and then reads the store;
* path C with a `scope` on the `start`, which is how a shutter's card asks for one of
  the three corrections, to the `save` that writes the shutter's own numbers.

The revision is deliberately never read off the controller object. Between two presses
the walk sends a `get` - a read that starts nothing - and takes the revision from its
answer, which is the only number a browser could have; the `session` events the
subscription pushes in the meantime are collected on the way and compared with it at
the end, so a transition that stopped being announced is a failing test rather than a
panel that quietly stops redrawing.

Mutation caught: an `act` handler that ignores the action or the value it is given; a
`start` that drops the `scope`; a `save` whose `target` does not decide what is
written; a transition that is carried out but never published.
"""

from __future__ import annotations

from typing import Any

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import DOMAIN as COVER
from homeassistant.core import HomeAssistant

from custom_components.myhome.calibration_store import loaded_store
from custom_components.myhome.panel_schemas import (
    WS_TYPE_SESSION_ACT,
    WS_TYPE_SESSION_GET,
    WS_TYPE_SESSION_SAVE,
    WS_TYPE_SESSION_START,
)

from .helpers_calibration import CLOSING, HEIGHT, OPENING, SLAT, FakeRunner
from .helpers_platforms import entity_object, setup_myhome
from .test_calibration_session import Act, check_the_snapshot
from .test_calibration_session_paths import PATH_A, PATH_C_TIMES, Step, for_the_session
from .test_websocket_api import CALIBRATION, FIRST, FIRST_ENTITY, YAML
from .test_websocket_session import CLIENT, DEVICE_KEY, answered, sent, subscribed

# The window the whole suite measures is 195 cm, and the fake runner answers as it
# would; the profile the walk names is a new one, so that the save has a profile to
# create rather than one to update.
NEW_PROFILE = "hallway_shutter"

# Path C with the scope already chosen on the `start`, which is what "Correct… → Times
# only" sends: the session is born on `refine_scope` with the scope marked, and the
# first thing the user does is confirm it. So the walk is the shared one without its
# first two steps - the route and the profile, both already in the frame.
PATH_C_AFTER_THE_START: tuple[Step, ...] = PATH_C_TIMES[2:]


class Walker:
    """One browser tab: it sends frames and knows only what the server told it."""

    def __init__(self, client, hass: HomeAssistant, entry) -> None:
        self._client = client
        self._hass = hass
        self._entry = entry
        self.pushed: list[dict[str, Any]] = []
        self.screens: list[dict[str, Any]] = []
        self.session_id: str | None = None
        self.revision: int | None = None

    def _remember(self, snapshot: dict[str, Any] | None) -> None:
        if snapshot is None:
            return
        self.screens.append(snapshot)
        self.session_id = snapshot["session_id"]
        self.revision = snapshot["revision"]

    async def _settle(self) -> dict[str, Any] | None:
        """Let what the last frame set in motion finish, then ask where it ended.

        A timed run ends by itself, well after the frame that started it was answered,
        so the revision the next frame has to carry is the one *that* transition
        published. `get` is the read that answers it, and reading up to its own answer
        collects every `session` event the subscription pushed on the way - which is
        how the frames below are chained without ever touching the controller object.
        """
        await self._hass.async_block_till_done()
        msg_id = await sent(
            self._client, {"type": WS_TYPE_SESSION_GET, "entry_id": self._entry.entry_id}
        )
        answer = await answered(self._client, msg_id, self.pushed)
        self._remember(answer["session"])
        return answer["session"]

    async def start(self, **fields: Any) -> dict[str, Any]:
        msg_id = await sent(
            self._client,
            {
                "type": WS_TYPE_SESSION_START,
                "entry_id": self._entry.entry_id,
                "cover_unique_id": FIRST,
                "client_id": CLIENT,
                **fields,
            },
        )
        answer = await answered(self._client, msg_id, self.pushed)
        self._remember(answer["session"])
        settled = await self._settle()
        assert settled is not None
        return settled

    async def act(self, one: Act, freezer: FrozenDateTimeFactory) -> dict[str, Any]:
        if one.tick:
            freezer.tick(one.tick)
        frame: dict[str, Any] = {
            "type": WS_TYPE_SESSION_ACT,
            "entry_id": self._entry.entry_id,
            "session_id": self.session_id,
            "client_id": CLIENT,
            "revision": self.revision,
            "action": one.action,
        }
        if one.value is not None:
            frame["value"] = one.value
        msg_id = await sent(self._client, frame)
        answer = await answered(self._client, msg_id, self.pushed)
        self._remember(answer["session"])
        settled = await self._settle()
        assert settled is not None, f"the session ended on {one.action}"
        return settled

    async def walk(self, acts, freezer: FrozenDateTimeFactory) -> dict[str, Any]:
        for one in acts:
            await self.act(one, freezer)
        return self.screens[-1]

    async def save(self, target: str) -> dict[str, Any]:
        msg_id = await sent(
            self._client,
            {
                "type": WS_TYPE_SESSION_SAVE,
                "entry_id": self._entry.entry_id,
                "session_id": self.session_id,
                "client_id": CLIENT,
                "revision": self.revision,
                "target": target,
            },
        )
        answer = await answered(self._client, msg_id, self.pushed)
        self._remember(answer["session"])
        return answer


async def test_path_a_is_measured_and_saved_without_ever_leaving_the_socket(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """Twenty-one frames and one save: the panel's own walk of path A.

    The three modules are the real ones - the handlers of `websocket_api.py`, the
    controller of `calibration_session.py` and the store the cover reads - and the only
    stand-in is the shutter itself. What this holds that the layer tests do not is the
    **chain**: every frame carries the revision the event before it published, so a
    transition that stopped being announced, or a value the handler passed on wrongly,
    stops the walk where it happened instead of showing up as a number at the end.

    The store is read afterwards rather than the snapshot, because the snapshot is what
    the session says it did and the store is what the shutter will run on tomorrow.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        await subscribed(client, entry.entry_id)
        walker = Walker(client, hass, entry)

        opened = await walker.start()
        assert opened["step"] == "path"
        assert opened["state"] == "armed"
        assert opened["actions"] == ["path_a", "path_b", "path_c"]

        walk = (*for_the_session(PATH_A)[:-1], Act("submit", NEW_PROFILE))
        snapshot = await walker.walk(walk, freezer)
        assert snapshot["step"] == "summary_basic"
        assert snapshot["state"] == "review"
        assert snapshot["review"]["targets"] == ["profile", "cover_only"]
        # The numbers the walk was meant to rediscover, found through the door.
        assert snapshot["measured"]["opening_time_s"] == pytest.approx(OPENING, abs=0.1)
        assert snapshot["measured"]["closing_time_s"] == pytest.approx(CLOSING, abs=0.1)
        assert snapshot["measured"]["slat_time_s"] == pytest.approx(SLAT, abs=0.1)
        assert snapshot["measured"]["travel_cm"] == pytest.approx(HEIGHT)
        for one in walker.screens:
            check_the_snapshot(one)

        answer = await walker.save("profile")
        assert answer["session"]["state"] == "saved"
        assert answer["session"]["outcome"]["reason"] == "saved"
        assert answer["session"]["outcome"]["profile"] == NEW_PROFILE

        store = loaded_store(hass, entry)
        profile = store.raw_profiles[NEW_PROFILE]
        assert profile["opening_time"] == pytest.approx(OPENING, abs=0.2)
        assert profile["closing_time"] == pytest.approx(CLOSING, abs=0.2)
        assert profile["reference_height"] == pytest.approx(HEIGHT)
        # The shutter follows what it was measured for, and carries no numbers of its
        # own any more: path A's exit is a profile plus an assignment, not both at once.
        record = store.raw_covers[FIRST]
        assert record["profile"] == NEW_PROFILE
        assert record["profile_wins"] is True
        assert record.get("overrides", {}) == {}
        # ...and the cover itself has already been told, without a reload.
        assert hass.states.get(FIRST_ENTITY).attributes["Profile"] == NEW_PROFILE

        # The other half: a panel that only subscribed saw the same conversation. The
        # last thing pushed is the save, and every revision arrived in order.
        assert [one["revision"] for one in walker.pushed] == sorted(
            one["revision"] for one in walker.pushed
        )
        assert walker.pushed[-1]["state"] == "saved"


async def test_a_correction_carries_its_scope_in_the_start_frame_and_writes_only_that(
    hass: HomeAssistant, tmp_path, hass_ws_client, freezer: FrozenDateTimeFactory
) -> None:
    """"Correct… → Times only" from the shutter's card, frame by frame to the store.

    The `start` is the interesting one: the panel names the path, the profile and the
    scope in it, so the session is born on the scope screen with the intention already
    marked rather than in a menu the user has to find their way through again. The walk
    then measures the two runs and nothing else, and the save writes the two run times
    onto the shutter while it goes on following its profile for the rest - which is
    what the origin chip calls *adjusted*.

    Mutation caught: a `start` that drops `scope` (the session would open on the menu
    with nothing marked); a save that writes a profile when the review offers only the
    shutter's own numbers.
    """
    async with setup_myhome(hass, tmp_path, YAML, calibration=CALIBRATION) as (entry, _commands):
        FakeRunner(entity_object(hass, COVER, DEVICE_KEY))
        client = await hass_ws_client(hass)
        await subscribed(client, entry.entry_id)
        walker = Walker(client, hass, entry)

        opened = await walker.start(path="path_c", profile="tall", scope="times_only")
        assert opened["step"] == "refine_scope"
        assert opened["path"] == "path_c"
        assert opened["intent"] == {"scope": "times_only"}
        assert "times_only" in opened["actions"]

        snapshot = await walker.walk(for_the_session(PATH_C_AFTER_THE_START), freezer)
        assert snapshot["step"] == "summary_correction"
        assert snapshot["state"] == "review"
        assert snapshot["scope"] == "times_only"
        assert snapshot["review"]["targets"] == ["cover_only"]
        assert snapshot["measured"]["opening_time_s"] == pytest.approx(OPENING, abs=0.1)
        assert snapshot["measured"]["closing_time_s"] == pytest.approx(CLOSING, abs=0.1)
        for one in walker.screens:
            check_the_snapshot(one)

        answer = await walker.save("cover_only")
        assert answer["session"]["state"] == "saved"

        store = loaded_store(hass, entry)
        # No profile was born, and the shutter keeps the one it had.
        assert NEW_PROFILE not in store.raw_profiles
        record = store.raw_covers[FIRST]
        assert record["profile"] == "tall"
        # Only what the scope measures is the shutter's own; the rolls stay the
        # profile's, which is the whole difference between "times only" and the rest.
        assert sorted(record["overrides"]) == ["closing_time", "opening_time", "slat_time"]
        assert record["overrides"]["opening_time"] == pytest.approx(OPENING, abs=0.2)
        assert walker.pushed[-1]["state"] == "saved"
