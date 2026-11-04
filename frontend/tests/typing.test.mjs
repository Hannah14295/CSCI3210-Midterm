import assert from 'node:assert/strict';
import { test } from 'node:test';
import { previewTyping } from '../src/typing.ts';
import { createTypingSender } from '../src/typingSender.ts';

test('live estimates count mistakes and finish by length, matching server rules', () => {
  assert.deepEqual(previewTyping('hello', 'hexlo', 2), {
    typed_characters: 5, correct_characters: 4, correct_prefix: 2,
    progress: 100, accuracy: 80, complete: true, wpm: 24,
  });
  assert.equal(previewTyping('hello', 'he', 12).wpm, 2);
});

test('empty input, zero time, and Unicode use the server character-count rules', () => {
  assert.equal(previewTyping('hello', '', 0).accuracy, 100);
  assert.equal(previewTyping('hello', 'h', 0).wpm, 0);
  assert.equal(previewTyping('', '', 1).complete, false);
  const metrics = previewTyping('a🚗é', 'a🚗', 1);
  assert.equal(metrics.typed_characters, 2);
  assert.equal(metrics.correct_characters, 2);
  assert.equal(metrics.correct_prefix, 2);
  assert.equal(metrics.progress, 2 / 3 * 100);
});

function setup(t) {
  t.mock.timers.enable({ apis: ['Date', 'setTimeout'], now: 1000 });
  const sent = [];
  return { sent, sender: createTypingSender(text => sent.push(text)) };
}

test('normal typing combines keystrokes into one update every 250ms', t => {
  const { sender, sent } = setup(t);
  sender.queue('h');
  t.mock.timers.tick(100);
  sender.queue('he');
  t.mock.timers.tick(149);
  assert.deepEqual(sent, []);
  t.mock.timers.tick(1);
  assert.deepEqual(sent, ['he']);
  sender.acknowledge(2);
  sender.queue('hel');
  t.mock.timers.tick(250);
  assert.deepEqual(sent, ['he', 'hel']);
});

test('a slow server gets only the latest input instead of a backlog', t => {
  const { sender, sent } = setup(t);
  sender.queue('h');
  t.mock.timers.tick(250);
  for (const text of ['he', 'hel', 'hell', 'hello']) {
    sender.queue(text);
    t.mock.timers.tick(1000);
  }
  assert.deepEqual(sent, ['h']);
  sender.acknowledge(1);
  assert.deepEqual(sent, ['h', 'hello']);
});

test('the completed passage is sent immediately without the normal batching delay', t => {
  const { sender, sent } = setup(t);
  sender.queue('h');
  sender.queue('hello', true);
  assert.deepEqual(sent, ['hello']);
  t.mock.timers.tick(1000);
  assert.deepEqual(sent, ['hello']);
});

test('completion waits for the in-flight update, then sends immediately', t => {
  const { sender, sent } = setup(t);
  sender.queue('he');
  t.mock.timers.tick(250);
  sender.queue('hello', true);
  sender.acknowledge(1); // An older snapshot must not release the current update.
  assert.deepEqual(sent, ['he']);
  sender.acknowledge(2);
  assert.deepEqual(sent, ['he', 'hello']);
});

test('disconnect or race end cancels unsent input and ignores late acknowledgments', t => {
  const { sender, sent } = setup(t);
  sender.queue('h');
  sender.stop();
  sender.acknowledge(1);
  sender.queue('hello', true);
  t.mock.timers.tick(1000);
  assert.deepEqual(sent, []);
});

test('rejected input is not retried automatically', t => {
  const { sender, sent } = setup(t);
  sender.queue('h');
  t.mock.timers.tick(250);
  sender.queue('he');
  sender.reset();
  sender.acknowledge(1);
  t.mock.timers.tick(1000);
  assert.deepEqual(sent, ['h']);
});

test('Unicode acknowledgments release the next update using code-point counts', t => {
  const { sender, sent } = setup(t);
  sender.queue('🚗');
  t.mock.timers.tick(250);
  sender.queue('🚗é', true);
  sender.acknowledge(1);
  assert.deepEqual(sent, ['🚗', '🚗é']);
});
