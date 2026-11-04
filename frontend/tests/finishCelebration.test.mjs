import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createFinishCelebration } from '../src/finishCelebration.ts';

test('each racer celebrates their own confirmed finish once', () => {
  const first = createFinishCelebration();
  const second = createFinishCelebration();
  assert.equal(first(null), false);
  assert.equal(first(false), false);
  assert.equal(second(false), false);
  assert.equal(first(true), true);
  assert.equal(second(false), false);
  assert.equal(first(true), false);
  assert.equal(second(true), true);
});

test('opening a completed race does not replay confetti', () => {
  const celebrate = createFinishCelebration();
  assert.equal(celebrate(null), false);
  assert.equal(celebrate(true), false);
  assert.equal(celebrate(true), false);
});

test('reconnects and repeated snapshots do not replay a celebration', () => {
  const celebrate = createFinishCelebration();
  assert.equal(celebrate(false), false);
  assert.equal(celebrate(true), true);
  assert.equal(celebrate(null), false);
  assert.equal(celebrate(false), false);
  assert.equal(celebrate(true), false);
});
