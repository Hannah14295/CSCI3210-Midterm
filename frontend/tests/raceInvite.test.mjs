import assert from 'node:assert/strict';
import { test } from 'node:test';
import { invitedRace, raceInviteUrl } from '../src/raceInvite.ts';

test('invite links preserve local and GitHub Pages paths', () => {
  assert.equal(raceInviteUrl('http://127.0.0.1:5173/#main', 12), 'http://127.0.0.1:5173/#race=12');
  assert.equal(raceInviteUrl('https://hannah14295.github.io/CSCI3210-Midterm/', 12), 'https://hannah14295.github.io/CSCI3210-Midterm/#race=12');
  assert.equal(invitedRace('#race=12'), 12);
  for (const hash of ['#main', '#race=0', '#race=-1', '#race=foo', '#race=9007199254740992']) assert.equal(invitedRace(hash), null);
});
