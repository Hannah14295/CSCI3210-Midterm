import assert from 'node:assert/strict';
import { test } from 'node:test';
import { fadeOutAudio } from '../src/audioFade.ts';

function setup(t, volume = 0.4) {
  t.mock.timers.enable({ apis: ['Date', 'setTimeout'], now: 1000 });
  const pauses = [];
  const track = {
    volume, paused: false, currentTime: 42,
    pause() { pauses.push(this.volume); this.paused = true; },
  };
  return { track, pauses };
}

test('music keeps playing during the fade and stops silently after two seconds', t => {
  const { track, pauses } = setup(t);
  fadeOutAudio(track);
  assert.equal(track.paused, false);
  assert.equal(track.volume, 0.4);
  t.mock.timers.tick(1000);
  assert.equal(track.paused, false);
  assert.ok(track.volume > 0 && track.volume < 0.4);
  t.mock.timers.tick(1000);
  assert.deepEqual(pauses, [0]);
  assert.equal(track.currentTime, 0);
  assert.equal(track.volume, 0.4);
});

test('resuming or leaving cancels the fade without a delayed pause', t => {
  const { track, pauses } = setup(t);
  const cancel = fadeOutAudio(track);
  t.mock.timers.tick(700);
  cancel();
  assert.equal(track.volume, 0.4);
  t.mock.timers.tick(5000);
  assert.deepEqual(pauses, []);
});

test('the listener volume setting is preserved instead of forcing the default', t => {
  const { track, pauses } = setup(t, 0.75);
  fadeOutAudio(track);
  t.mock.timers.tick(2000);
  assert.deepEqual(pauses, [0]);
  assert.equal(track.volume, 0.75);
});

test('already-paused music is rewound without starting a fade timer', t => {
  const { track, pauses } = setup(t);
  track.paused = true;
  fadeOutAudio(track);
  assert.equal(track.currentTime, 0);
  t.mock.timers.tick(5000);
  assert.deepEqual(pauses, [0]);
  assert.equal(track.volume, 0.4);
});
