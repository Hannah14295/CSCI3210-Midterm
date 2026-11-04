import assert from 'node:assert/strict';
import { test } from 'node:test';
import { countdownAt } from '../src/countdown.ts';
import { createTypingSender } from '../src/typingSender.ts';

test('the shared start deadline counts 3, 2, 1 and keeps Go visible', () => {
  const go = Date.parse('2026-11-04T12:00:03Z');
  const start = new Date(go).toISOString();
  assert.equal(countdownAt(start, go - 3000), 3);
  assert.equal(countdownAt(start, go - 2000), 2);
  assert.equal(countdownAt(start, go - 1), 1);
  assert.equal(countdownAt(start, go), 0);
  assert.equal(countdownAt(start, go + 999), 0);
  assert.equal(countdownAt(start, go + 1000), 0);
  assert.equal(countdownAt(start, go + 60_000), 0);
  assert.equal(countdownAt(null, go), null);
});

test('the first keystroke is sent immediately rather than waiting for batching', t => {
  t.mock.timers.enable({ apis: ['Date', 'setTimeout'], now: 1000 });
  const sent = [];
  const sender = createTypingSender(text => sent.push(text));
  sender.queue('h', false, true);
  assert.deepEqual(sent, ['h']);
  sender.acknowledge(1);
  sender.queue('he');
  t.mock.timers.tick(249);
  assert.deepEqual(sent, ['h']);
  t.mock.timers.tick(1);
  assert.deepEqual(sent, ['h', 'he']);
  sender.stop();
});
