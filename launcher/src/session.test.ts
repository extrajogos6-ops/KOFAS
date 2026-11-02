import assert from "node:assert/strict";
import test from "node:test";
import { actionPresentation, createGameAction, createStatusReceiver, parseStatus, type GameStatus } from "./session.ts";

test("late command replies cannot overwrite a newer process notification", () => {
  const receive = createStatusReceiver();
  assert.equal(receive({ phase: "running", detail: null, revision: 3 }).phase, "running");
  assert.equal(receive({ phase: "starting", detail: null, revision: 2 }).phase, "running");
  assert.equal(receive({ phase: "ready", detail: null, revision: 4 }).phase, "ready");
  for (const revision of [undefined, -1, "5", NaN, 1.5]) {
    assert.throws(() => receive({ phase: "running", detail: null, revision }));
  }
});

test("malformed bridge responses never become a ready or running game", () => {
  for (const value of [null, {}, { phase: "other", detail: null }, { phase: "ready", detail: 5 }]) {
    assert.throws(() => parseStatus(value));
  }
  assert.deepEqual(parseStatus({ phase: "running", detail: null }), { phase: "running", detail: null });
});

test("repeated clicks while a native request is pending start only one request", async () => {
  let finish: (value: unknown) => void = () => {};
  let calls = 0;
  const statuses: GameStatus[] = [];
  const action = createGameAction(() => ({ phase: "ready", detail: null }), () => {
    calls++;
    return new Promise(resolve => { finish = resolve; });
  }, status => statuses.push(status), message => assert.fail(message));
  const first = action();
  await action();
  assert.equal(calls, 1);
  assert.equal(statuses.at(-1)?.phase, "starting");
  finish({ phase: "running", detail: null });
  await first;
  assert.equal(statuses.at(-1)?.phase, "running");
});

test("a failed start reports the error and permits a later attempt", async () => {
  let calls = 0;
  const errors: string[] = [];
  const statuses: GameStatus[] = [];
  const action = createGameAction(() => ({ phase: "ready", detail: null }), async () => {
    if (++calls === 1) throw new Error("Python ausente");
    return { phase: "starting", detail: null };
  }, status => statuses.push(status), message => errors.push(message));
  await action();
  assert.deepEqual(errors, ["Python ausente"]);
  await action();
  assert.equal(calls, 2);
  assert.equal(statuses.at(-1)?.phase, "starting");
});

test("a running game displays STOP and uses the stop command", async () => {
  let state: GameStatus = { phase: "running", detail: null };
  const commands: string[] = [];
  const action = createGameAction(() => state, async command => {
    commands.push(command);
    return { phase: "ready", detail: null };
  }, value => { state = value; }, message => assert.fail(message));
  assert.equal(actionPresentation(state).label, "STOP");
  await action();
  assert.deepEqual(commands, ["stop"]);
  assert.equal(actionPresentation(state).label, "PLAY");
});

test("stop failure preserves the running state and repeated stop stays gated", async () => {
  let state: GameStatus = { phase: "running", detail: null };
  let fail: (reason: Error) => void = () => {};
  let calls = 0;
  const action = createGameAction(() => state, () => {
    calls++;
    return new Promise((_, reject) => { fail = reject; });
  }, value => { state = value; }, () => {});
  const first = action();
  assert.equal(state.phase, "stopping");
  assert.equal(actionPresentation(state).disabled, true);
  await action();
  assert.equal(calls, 1);
  fail(new Error("Acesso negado"));
  await first;
  assert.equal(state.phase, "running");
  assert.equal(actionPresentation(state).label, "STOP");
});

test("stopping is an accepted native status", () => {
  assert.deepEqual(parseStatus({ phase: "stopping", detail: null }), { phase: "stopping", detail: null });
});

test("a failed request preserves a newer native state instead of restoring stale state", async () => {
  let state: GameStatus = { phase: "ready", detail: null };
  let fail: (reason: Error) => void = () => {};
  const action = createGameAction(() => state, () => new Promise((_, reject) => { fail = reject; }),
    value => { state = value; }, () => {});
  const pending = action();
  state = { phase: "running", detail: null };
  fail(new Error("Resposta interrompida"));
  await pending;
  assert.equal(state.phase, "running");
});
