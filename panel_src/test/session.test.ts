// The session client, on fake timers and against a gateway that answers what it is told
// to.
//
// Three of the five lessons of 18 September are here, and each one is a test that would
// pass on the v2 panel's code only by accident:
//
// * the heartbeat is on a timer of its own, and **a listener that throws does not stop
//   it** - the v2 panel sent its presence signal from the render path, so the first
//   drawing error took the session away from the person holding the tape measure;
// * "Cancel" answers on all four branches and never with `undefined`;
// * the `client_id` is stable across two clients of the same tab, with `sessionStorage`
//   and without it.
//
// No DOM: `SessionClient` is a class with a connection and a timer, and that is the whole
// of its dependencies.

import assert from "node:assert/strict";
import { describe, it, mock, type TestContext } from "node:test";

import {
  SessionClient,
  HEARTBEAT_MS,
  CLIENT_ID_KEY,
  readClientId,
  type KeyValueStore,
} from "../src/engine/session";
import { type SessionSnapshot } from "../src/engine/session-contract";
import { type HaConnection } from "../src/types/ha";

const CLIENT = "3b0c7e1a-5d2f-4a8e-9c61-0e7f4b2d9a10";
const OTHER = "8d41f6b2-7c3e-4f95-a0d8-2b6e9c1f7e33";
const ENTRY = "01EXAMPLEEXAMPLEEXAMPLEEXA";
const SESSION = "6f1d2c3b4a5e4f708192a3b4c5d6e7f8";

/** A snapshot with only what this file reads; the whole shape is the contract's. */
const snapshot = (over: Partial<SessionSnapshot> = {}): SessionSnapshot =>
  ({
    session_id: SESSION,
    entry_id: ENTRY,
    revision: 7,
    server_time: "2026-09-18T10:04:22.300+00:00",
    cover: { unique_id: "00:03:50:aa:bb:cc-2-81", entity_id: "cover.hallway_shutter", name: "Hallway Shutter" },
    state: "running",
    substate: "awaiting_endpoint",
    step: "open_top",
    path: "path_a",
    scope: null,
    profile: null,
    level: "basic",
    plan: [],
    plan_index: 1,
    intent: null,
    actions: ["stopped_open"],
    form: null,
    placeholders: { cover: "Hallway Shutter" },
    movement: null,
    press: null,
    reading: null,
    measured: {
      travel_cm: null,
      travel_measured: false,
      opening_time_s: null,
      closing_time_s: null,
      slat_time_s: null,
      lift: null,
      descent: [],
      ascent: [],
      times_adopted: false,
    },
    fit: null,
    check: null,
    review: null,
    problem: null,
    notice: null,
    position_known: "closed",
    external_move: false,
    owner: { client_id: CLIENT, present_until: "2026-09-18T10:05:07.300+00:00" },
    idle_expires_at: "2026-09-18T10:14:22.300+00:00",
    outcome: null,
    ...over,
  }) as SessionSnapshot;

interface Sent {
  type: string;
  [key: string]: unknown;
}

/**
 * A gateway that records what it was asked and answers what the test set.
 *
 * `answers` is read by command name; a function may throw to refuse, exactly as
 * `sendMessagePromise` rejects with the backend's error object.
 */
const gateway = (answers: Record<string, (message: Sent) => unknown> = {}) => {
  const sent: Sent[] = [];
  const connection: HaConnection = {
    sendMessagePromise: <T,>(message: Record<string, unknown>): Promise<T> => {
      const frame = message as Sent;
      sent.push(frame);
      const name = frame.type.replace("myhome/calibration/session/", "");
      const answer = answers[name];
      if (!answer) {
        return Promise.reject({ code: "unknown_command", message: "unknown command" });
      }
      try {
        return Promise.resolve(answer(frame) as T);
      } catch (error) {
        return Promise.reject(error);
      }
    },
    subscribeMessage: () => Promise.resolve(async () => undefined),
  };
  return {
    connection,
    sent,
    count: (name: string) => sent.filter((one) => one.type.endsWith(`/${name}`)).length,
    last: (name: string) => [...sent].reverse().find((one) => one.type.endsWith(`/${name}`)),
  };
};

/**
 * A client of that gateway, given back at the end of the test.
 *
 * The `after` is not tidiness: a client still holding its presence timer when the test
 * that made it has failed keeps the whole run alive, and the first assertion to fail
 * would be reported as a suite that never ends.
 */
const client = (
  t: TestContext,
  bench: ReturnType<typeof gateway>,
  onChange?: (session: SessionSnapshot | null) => void,
): SessionClient => {
  const session = new SessionClient({
    connection: bench.connection,
    entryId: ENTRY,
    clientId: CLIENT,
    storage: null,
    onChange,
  });
  t.after(() => session.dispose());
  return session;
};

/** Let the promises the timer started settle, without letting the clock move. */
const settle = async (): Promise<void> => {
  for (let round = 0; round < 6; round += 1) {
    await Promise.resolve();
  }
};

describe("the presence signal", () => {
  it("beats every fifteen seconds on a timer of its own", async (t) => {
    t.mock.timers.enable({ apis: ["setInterval"] });
    const bench = gateway({
      start: () => ({ session: snapshot() }),
      heartbeat: () => ({ owner: true, present_until: "2026-09-18T10:06:00+00:00" }),
    });
    const session = client(t, bench);
    await session.start({ cover: "00:03:50:aa:bb:cc-2-81" });
    assert.equal(bench.count("heartbeat"), 0, "a start is not a beat");
    t.mock.timers.tick(HEARTBEAT_MS * 3 + 1);
    assert.equal(bench.count("heartbeat"), 3);
    const beat = bench.last("heartbeat");
    assert.equal(beat?.session_id, SESSION);
    assert.equal(beat?.client_id, CLIENT);
    assert.equal(beat?.entry_id, ENTRY);
    session.dispose();
    t.mock.timers.tick(HEARTBEAT_MS * 3);
    assert.equal(bench.count("heartbeat"), 3, "disposing stops it");
  });

  it("goes on beating although the drawing throws every time it is told - lesson 1", async (t) => {
    t.mock.timers.enable({ apis: ["setInterval"] });
    // The listener is the repaint. In the v2 panel this exception reached the code that
    // sent the presence signal, the signal stopped, and forty-five seconds later the
    // server handed the session to somebody else while the user was reading a tape.
    let draws = 0;
    const bench = gateway({
      start: () => ({ session: snapshot() }),
      heartbeat: () => ({ owner: true, present_until: "2026-09-18T10:06:00+00:00" }),
    });
    const errors: unknown[] = [];
    mock.method(console, "error", (...args: unknown[]) => errors.push(args));
    const session = client(t, bench, () => {
      draws += 1;
      throw new Error("the wizard could not be drawn");
    });
    await session.start({ cover: "00:03:50:aa:bb:cc-2-81" });
    assert.ok(draws > 0, "the listener really was called");
    t.mock.timers.tick(HEARTBEAT_MS * 4 + 1);
    assert.equal(bench.count("heartbeat"), 4);
    assert.ok(session.beating);
    // Reported, and reported once: a stack trace every fifteen seconds buries the first.
    assert.equal(errors.length, 1);
    mock.restoreAll();
  });

  it("stops when the session is over, and not before", async (t) => {
    t.mock.timers.enable({ apis: ["setInterval"] });
    const bench = gateway({
      start: () => ({ session: snapshot() }),
      heartbeat: () => ({ owner: true, present_until: null }),
    });
    const session = client(t, bench);
    await session.start({ cover: "00:03:50:aa:bb:cc-2-81" });
    t.mock.timers.tick(HEARTBEAT_MS + 1);
    assert.equal(bench.count("heartbeat"), 1);
    session.apply(snapshot({ state: "saved", step: null, owner: null }));
    t.mock.timers.tick(HEARTBEAT_MS * 5);
    assert.equal(bench.count("heartbeat"), 1, "a session that is over is not kept alive");
    assert.equal(session.beating, false);
  });

  it("does not stop for a socket that is down, and does stop for a session that is gone", async (t) => {
    t.mock.timers.enable({ apis: ["setInterval"] });
    let refusal: unknown = { code: "unknown_error", message: "socket down" };
    const bench = gateway({
      start: () => ({ session: snapshot() }),
      heartbeat: () => {
        throw refusal;
      },
    });
    const session = client(t, bench);
    await session.start({ cover: "00:03:50:aa:bb:cc-2-81" });
    t.mock.timers.tick(HEARTBEAT_MS * 2 + 1);
    await settle();
    assert.equal(bench.count("heartbeat"), 2);
    assert.ok(session.beating, "a lift between two routers is not the end of a session");
    refusal = { code: "not_found", message: "no such session", translation_key: "unknown_session" };
    t.mock.timers.tick(HEARTBEAT_MS + 1);
    await settle();
    t.mock.timers.tick(HEARTBEAT_MS * 3);
    assert.equal(bench.count("heartbeat"), 3, "there is nothing left to be present for");
  });

  it("says the tab is read-only when the answer says somebody else owns it", async (t) => {
    t.mock.timers.enable({ apis: ["setInterval"] });
    let owner = true;
    const bench = gateway({
      start: () => ({ session: snapshot() }),
      heartbeat: () => ({ owner, present_until: owner ? "2026-09-18T10:06:00+00:00" : null }),
    });
    const seen: boolean[] = [];
    const session = new SessionClient({
      connection: bench.connection,
      entryId: ENTRY,
      clientId: CLIENT,
      storage: null,
      onChange: () => seen.push(session.owner),
    });
    await session.start({ cover: "00:03:50:aa:bb:cc-2-81" });
    assert.equal(session.owner, true);
    owner = false;
    t.mock.timers.tick(HEARTBEAT_MS + 1);
    await settle();
    assert.equal(session.owner, false);
    assert.ok(seen.includes(false), "the screen was told, so it can offer to take it back");
  });

  it("never sends an act of its own when a session is picked up again - lesson 5", async (t) => {
    const bench = gateway({
      get: () => ({ session: snapshot({ state: "positioning", step: "tape_run", actions: [] }), capabilities: null }),
      attach: () => ({ session: snapshot({ state: "positioning", step: "tape_run", actions: [] }) }),
      heartbeat: () => ({ owner: true, present_until: null }),
    });
    const session = client(t, bench);
    await session.get();
    await session.attach(SESSION);
    session.apply(snapshot({ state: "positioning", step: "tape_run" }));
    await session.resume();
    assert.equal(bench.count("act"), 0);
    assert.equal(bench.count("stop"), 0);
  });
});

describe("cancelling", () => {
  it("branch 1: it worked, or it had already ended", async (t) => {
    const done = gateway({ cancel: () => ({ session: snapshot({ state: "ended" }), already_ended: false }) });
    const first = await client(t, done).cancel();
    assert.equal(first.ok, true);
    assert.equal(first.branch, "cancelled");
    assert.deepEqual(first.recovery, []);

    const twice = gateway({ cancel: () => ({ session: snapshot({ state: "ended" }), already_ended: true }) });
    const second = await client(t, twice).cancel();
    assert.equal(second.ok, true);
    assert.equal(second.branch, "already_ended");
  });

  it("branch 2: another client owns it, so the screen offers to take control", async (t) => {
    // The gateway keeps the one fact this branch is about: who owns the session. A cancel
    // from anybody else is refused until they have taken it, or forced it.
    let owner = OTHER;
    const bench = gateway({
      get: () => ({ session: snapshot({ owner: { client_id: owner, present_until: "2026-09-18T10:06:00+00:00" } }), capabilities: null }),
      cancel: (message) => {
        if (!message.force && owner !== CLIENT) {
          throw { code: "not_allowed", message: "another client owns this session", translation_key: "session_owned" };
        }
        return { session: snapshot({ state: "ended", owner: null }), already_ended: false };
      },
      attach: (message) => {
        if (message.claim) {
          owner = CLIENT;
        }
        return { session: snapshot({ owner: { client_id: owner, present_until: "2026-09-18T10:06:00+00:00" } }) };
      },
      heartbeat: () => ({ owner: owner === CLIENT, present_until: null }),
    });
    const session = client(t, bench);
    await session.get();
    const refused = await session.cancel();
    assert.equal(refused.ok, false);
    assert.equal(refused.branch, "owned");
    assert.deepEqual(refused.recovery, ["claim", "force"]);

    // …and the offer works: attach with `claim`, then cancel.
    const taken = await session.claimAndCancel();
    assert.equal(taken.ok, true);
    assert.equal(taken.branch, "cancelled");
    assert.equal(bench.last("attach")?.claim, true);
  });

  it("branch 3: the session is not there any more, which is what was asked for", async (t) => {
    const bench = gateway({
      get: () => ({ session: snapshot({ state: "ended", outcome: { reason: "expired", profile: null, origin: null, source: null } }), capabilities: null }),
      cancel: () => {
        throw { code: "not_found", message: "no such session", translation_key: "unknown_session" };
      },
    });
    const session = client(t, bench);
    await session.get();
    const outcome = await session.cancel();
    assert.equal(outcome.ok, true);
    assert.equal(outcome.branch, "gone");
    assert.equal(outcome.session?.outcome?.reason, "expired", "the reason is shown where it is known");
    assert.equal(outcome.error?.translation_key, "unknown_session");
  });

  it("branch 4: the gateway did not answer, so 'Try again' and 'End anyway' - lesson 2", async (t) => {
    const bench = gateway({
      get: () => ({ session: snapshot(), capabilities: null }),
      cancel: () => {
        throw new Error("the connection is closed");
      },
    });
    const session = client(t, bench);
    await session.get();
    const first = await session.cancel();
    assert.equal(first.ok, false);
    assert.equal(first.branch, "unconfirmed");
    assert.deepEqual(first.recovery, ["retry", "force"]);
    assert.equal(first.freedAt, "2026-09-18T10:14:22.300+00:00");

    // And when "End anyway" is what failed, the one true sentence left is the lease.
    const forced = await session.cancel({ force: true });
    assert.equal(forced.ok, false);
    assert.deepEqual(forced.recovery, ["wait"]);
    assert.equal(forced.freedAt, "2026-09-18T10:14:22.300+00:00");
  });

  it("answers on every branch, and never with undefined", async (t) => {
    const refusals = [
      { code: "not_allowed", message: "owned", translation_key: "session_owned" },
      { code: "not_found", message: "gone", translation_key: "unknown_session" },
      { code: "not_allowed", message: "over", translation_key: "session_ended" },
      { code: "not_found", message: "no entry", translation_key: "unknown_entry" },
      new Error("socket down"),
      "a string nobody typed",
    ];
    for (const raw of refusals) {
      const bench = gateway({
        cancel: () => {
          throw raw;
        },
      });
      const outcome = await client(t, bench).cancel();
      assert.ok(outcome, `no outcome for ${String(raw)}`);
      assert.ok(typeof outcome.branch === "string");
      assert.ok(outcome.ok || outcome.recovery.length > 0, "a refusal with nothing to press");
    }
  });
});

describe("the verbs", () => {
  it("guards an act with the revision the screen last read", async (t) => {
    const bench = gateway({
      get: () => ({ session: snapshot({ revision: 12 }), capabilities: null }),
      act: () => {
        throw { code: "not_allowed", message: "stale revision", translation_key: "revision_conflict" };
      },
    });
    const session = client(t, bench);
    await session.get();
    const result = await session.act("stopped_open");
    assert.equal(result.ok, false);
    assert.equal(bench.last("act")?.revision, 12);
    // A conflict is not an error to show and leave: reading again is the recovery, and
    // the screen that comes back is the true one.
    assert.deepEqual(result.ok === false ? result.recovery : [], ["reload"]);
  });

  it("sends a typed number as the text that was typed", async (t) => {
    const bench = gateway({
      get: () => ({ session: snapshot({ revision: 3 }), capabilities: null }),
      act: () => ({ session: snapshot({ revision: 4 }) }),
    });
    const session = client(t, bench);
    await session.get();
    await session.act("submit", "96,5");
    assert.equal(bench.last("act")?.value, "96,5");
  });

  it("leaves without a session rather than refusing, because it is sent as a page goes away", async (t) => {
    const bench = gateway({});
    const result = await client(t, bench).leave();
    assert.equal(result.ok, true);
    assert.equal(bench.count("leave"), 0, "there was nothing to leave");
  });

  it("answers a refusal of every verb with something to press", async (t) => {
    const refuse = () => {
      throw { code: "not_found", message: "no gateway", translation_key: "entry_not_loaded" };
    };
    const bench = gateway({ get: refuse, start: refuse, attach: refuse, act: refuse, stop: refuse, save: refuse, leave: refuse });
    const session = client(t, bench);
    session.apply(snapshot());
    for (const result of [
      await session.get(),
      await session.start({ cover: "x" }),
      await session.attach(SESSION),
      await session.act("stopped_open"),
      await session.stop(),
      await session.save("profile"),
      await session.leave(),
    ]) {
      assert.ok(result, "a verb answered nothing at all");
      if (result.ok === false) {
        assert.ok(result.recovery.length > 0);
        assert.ok(result.error.code);
      }
    }
  });
});

describe("who this tab is", () => {
  it("keeps one name across two clients of the same tab", () => {
    const kept: Record<string, string> = {};
    const storage: KeyValueStore = {
      getItem: (key) => kept[key] ?? null,
      setItem: (key, value) => {
        kept[key] = value;
      },
    };
    const first = readClientId(storage);
    const second = readClientId(storage);
    assert.equal(first, second);
    assert.equal(kept[CLIENT_ID_KEY], first);
    assert.match(first, /^[A-Za-z0-9-]{8,64}$/);
  });

  it("makes one for the life of the element when the store is not there, or throws", () => {
    const thrower: KeyValueStore = {
      getItem: () => {
        throw new Error("the browser is in private mode");
      },
      setItem: () => {
        throw new Error("the browser is in private mode");
      },
    };
    for (const storage of [null, thrower]) {
      const made = readClientId(storage);
      assert.match(made, /^[A-Za-z0-9-]{8,64}$/);
    }
    const bench = gateway({ get: () => ({ session: null, capabilities: null }) });
    const session = new SessionClient({ connection: bench.connection, entryId: ENTRY, storage: null });
    assert.match(session.clientId, /^[A-Za-z0-9-]{8,64}$/);
  });

  it("refuses a kept name that is not a name the backend would accept", () => {
    const storage: KeyValueStore = {
      getItem: () => "short",
      setItem: () => undefined,
    };
    assert.notEqual(readClientId(storage), "short");
  });
});
