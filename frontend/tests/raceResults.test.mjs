import assert from 'node:assert/strict';
import { test } from 'node:test';
import { raceResults } from '../src/raceResults.ts';

function score(id, wpm, accuracy) {
  return {
    id, player: { id, username: `Player ${id}` },
    finished_at: '2026-11-04T12:00:00Z', wpm, accuracy, elapsed_seconds: 60,
  };
}

test('results wait for server confirmation and every participant', () => {
  const players = [score(1, 80, 90), { ...score(2, 40, 100), finished_at: null }];
  assert.equal(raceResults({ status: 'running', participants: players }), null);
  assert.equal(raceResults({ status: 'finished', participants: players }), null);
  assert.equal(raceResults({ status: 'finished', participants: [] }), null);
  assert.equal(raceResults({ status: 'running', participants: [score(1, 80, 90)] }), null);
});

test('speed and accuracy can have different winners', () => {
  const players = [score(1, 80, 90), score(2, 40, 100), score(3, 60, 95)];
  const result = raceResults({ status: 'finished', participants: players });
  assert.deepEqual(result.scores.map(entry => entry.id), [1, 3, 2]);
  assert.deepEqual(result.speedWinners.map(entry => entry.id), [1]);
  assert.deepEqual(result.accuracyWinners.map(entry => entry.id), [2]);
  assert.deepEqual(players.map(entry => entry.id), [1, 2, 3]);
});

test('all tied winners are included, independently for both metrics', () => {
  const result = raceResults({ status: 'finished', participants: [score(1, 80, 100), score(2, 80, 90), score(3, 40, 100)] });
  assert.deepEqual(result.speedWinners.map(entry => entry.id), [1, 2]);
  assert.deepEqual(result.accuracyWinners.map(entry => entry.id), [1, 3]);
});

test('solo practice has a winner in both categories, including zero scores', () => {
  const result = raceResults({ status: 'finished', participants: [score(1, 0, 0)] });
  assert.equal(result.scores.length, 1);
  assert.equal(result.speedWinners[0].id, 1);
  assert.equal(result.accuracyWinners[0].id, 1);
});

test('missing or non-finite saved scores cannot announce winners', () => {
  for (const invalid of [{ accuracy: null }, { wpm: null }, { elapsed_seconds: null }, { wpm: NaN }, { accuracy: Infinity }]) {
    assert.equal(raceResults({ status: 'finished', participants: [{ ...score(1, 80, 100), ...invalid }] }), null);
  }
});
