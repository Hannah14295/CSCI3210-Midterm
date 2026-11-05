import assert from 'node:assert/strict';
import { test } from 'node:test';
import { passageDifficulty } from '../src/passageDifficulty.ts';

test('length categories use consistent boundaries and Unicode character counts', () => {
  assert.equal(passageDifficulty('x'.repeat(300)), 'short');
  assert.equal(passageDifficulty('x'.repeat(301)), 'medium');
  assert.equal(passageDifficulty('x'.repeat(500)), 'medium');
  assert.equal(passageDifficulty('x'.repeat(501)), 'long');
  assert.equal(passageDifficulty('🚗'.repeat(300)), 'short');
});
