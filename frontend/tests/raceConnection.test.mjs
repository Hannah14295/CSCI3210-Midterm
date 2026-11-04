import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createRaceConnection, mergeRaceSnapshot, restoreRaceDraft } from '../src/raceConnection.ts';

class FakeSocket {
  readyState = 1;
  onmessage = null;
  onclose = null;
  onerror = null;
  sent = [];
  send(data) { this.sent.push(JSON.parse(data)); }
  close() { this.readyState = 3; }
  message(data) { this.onmessage?.({ data: JSON.stringify(data) }); }
  disconnect(code = 1006) {
    this.readyState = 3;
    this.onclose?.({ code, reason: 'Test interruption' });
  }
}

function setup(t) {
  t.mock.timers.enable({ apis: ['Date', 'setTimeout'], now: 1000 });
  const sockets = [], states = [], closes = [], messages = [];
  const client = createRaceConnection({
    createSocket: () => { const socket = new FakeSocket(); sockets.push(socket); return socket; },
    onSocket: () => {}, onMessage: event => messages.push(JSON.parse(event.data)),
    onState: state => states.push(state), onDisconnect: code => closes.push(code),
    onProblem: problem => { throw problem; },
  });
  return { client, sockets, states, closes, messages };
}

test('an idle authenticated room sends keepalives and remains connected with replies', t => {
  const { client, sockets, states } = setup(t);
  client.connected();
  for (let index = 0; index < 6; index++) {
    t.mock.timers.tick(20_000);
    assert.equal(sockets[0].sent.at(-1).type, 'ping');
    sockets[0].message({ type: 'pong' });
  }
  assert.equal(sockets.length, 1);
  assert.equal(states.at(-1), 'connected');
  client.stop();
});

test('unexpected closures reconnect automatically and reset backoff after success', t => {
  const { client, sockets, states } = setup(t);
  client.connected();
  sockets[0].disconnect();
  assert.equal(states.at(-1), 'reconnecting');
  t.mock.timers.tick(999);
  assert.equal(sockets.length, 1);
  t.mock.timers.tick(1);
  assert.equal(sockets.length, 2);
  client.connected();
  sockets[1].disconnect(1001);
  t.mock.timers.tick(1000);
  assert.equal(sockets.length, 3);
  client.stop();
});

test('a silent half-open connection is replaced after its keepalive expires', t => {
  const { client, sockets, closes } = setup(t);
  client.connected();
  t.mock.timers.tick(20_000);
  t.mock.timers.tick(45_000);
  assert.equal(sockets[0].readyState, 3);
  assert.deepEqual(closes, [4000]);
  t.mock.timers.tick(1000);
  assert.equal(sockets.length, 2);
  client.stop();
});

test('any incoming race update can satisfy a pending keepalive', t => {
  const { client, sockets, messages } = setup(t);
  client.connected();
  t.mock.timers.tick(20_000);
  sockets[0].message({ type: 'race.updated' });
  assert.equal(messages.length, 1);
  t.mock.timers.tick(20_000);
  sockets[0].message({ type: 'pong' });
  t.mock.timers.tick(25_000);
  assert.equal(sockets.length, 1);
  client.stop();
});

for (const code of [4401, 4403, 1008, 1009]) {
  test(`connection rejection ${code} does not cause endless retries`, t => {
    const { client, sockets, states } = setup(t);
    sockets[0].disconnect(code);
    client.check();
    t.mock.timers.tick(180_000);
    assert.equal(sockets.length, 1);
    assert.equal(states.at(-1), 'disconnected');
    client.stop();
  });
}

test('repeated failures back off and a manual retry cancels the scheduled retry', t => {
  const { client, sockets } = setup(t);
  for (const wait of [1000, 2000, 4000, 8000, 16000, 30000, 30000]) {
    sockets.at(-1).disconnect();
    const count = sockets.length;
    t.mock.timers.tick(wait - 1);
    assert.equal(sockets.length, count);
    t.mock.timers.tick(1);
    assert.equal(sockets.length, count + 1);
  }
  sockets.at(-1).disconnect();
  client.reconnect();
  client.connected();
  const count = sockets.length;
  t.mock.timers.tick(30_000);
  assert.equal(sockets.length, count);
  client.stop();
});

test('rate-limited connections wait before reconnecting', t => {
  const { client, sockets } = setup(t);
  sockets[0].disconnect(4429);
  t.mock.timers.tick(9999);
  assert.equal(sockets.length, 1);
  t.mock.timers.tick(1);
  assert.equal(sockets.length, 2);
  client.stop();
});

test('a stalled handshake is retried and unmount cancels all recovery', t => {
  const { client, sockets } = setup(t);
  sockets[0].readyState = 0;
  t.mock.timers.tick(90_000);
  t.mock.timers.tick(1000);
  assert.equal(sockets.length, 2);
  sockets[1].disconnect();
  client.stop();
  t.mock.timers.tick(180_000);
  assert.equal(sockets.length, 2);
});

test('returning to the tab probes the connection without accumulating ping timers', t => {
  const { client, sockets } = setup(t);
  client.connected();
  client.check();
  client.check();
  assert.equal(sockets[0].sent.length, 1);
  sockets[0].message({ type: 'pong' });
  t.mock.timers.tick(20_000);
  assert.equal(sockets[0].sent.length, 2);
  client.stop();
});

test('old sockets cannot update state after reconnection', t => {
  const { client, sockets, messages } = setup(t);
  const staleHandler = sockets[0].onmessage;
  client.reconnect();
  staleHandler({ data: JSON.stringify({ type: 'race.updated' }) });
  assert.equal(messages.length, 0);
  client.stop();
});

test('reconnection keeps only drafts compatible with saved append-only input', () => {
  assert.equal(restoreRaceDraft('hello', 'hello world', true), 'hello world');
  assert.equal(restoreRaceDraft('hello world', 'hello', true), 'hello world');
  assert.equal(restoreRaceDraft('hello', 'hexlo world', true), 'hello');
  assert.equal(restoreRaceDraft('hello', 'hello world', false), 'hello');
});

test('a delayed start response cannot reverse a final snapshot or newer progress', () => {
  const previous = { id: 1, status: 'finished', started_at: 'start', participants: [{ id: 1, revision: 3 }] };
  const incoming = { id: 1, status: 'running', started_at: 'start', participants: [{ id: 1, revision: 2 }] };
  const merged = mergeRaceSnapshot(previous, incoming);
  assert.equal(merged.status, 'finished');
  assert.equal(merged.participants[0].revision, 3);
  assert.equal(mergeRaceSnapshot(null, incoming), incoming);
});
