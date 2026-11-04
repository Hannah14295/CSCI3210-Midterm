import assert from 'node:assert/strict';
import { test } from 'node:test';
import { resolveBackendUrl } from '../src/config.ts';

test('local requests use the frontend origin so Vite can proxy them', () => {
  assert.equal(resolveBackendUrl('', '/api/races/', 'http://127.0.0.1:5173').href,
    'http://127.0.0.1:5173/api/races/');
});

test('GitHub Pages requests go to Render rather than the repository path', () => {
  assert.equal(resolveBackendUrl('https://typing.onrender.com/', '/api/auth/login/', 'https://hannah14295.github.io').href,
    'https://typing.onrender.com/api/auth/login/');
});

test('the same backend origin produces secure WebSocket URLs', () => {
  const url = resolveBackendUrl('https://typing.onrender.com', '/ws/races/7/', 'https://hannah14295.github.io');
  url.protocol = 'wss:';
  url.searchParams.set('auth', 'token');
  assert.equal(url.href, 'wss://typing.onrender.com/ws/races/7/?auth=token');
});

test('invalid backend origins and protocol-relative paths are rejected', () => {
  for (const base of ['https://typing.onrender.com/api/', 'https://user:pass@typing.onrender.com', 'javascript:alert(1)', 'https://typing.onrender.com?token=secret']) {
    assert.throws(() => resolveBackendUrl(base, '/api/races/', 'https://hannah14295.github.io'));
  }
  assert.throws(() => resolveBackendUrl('', '//untrusted.example', 'http://localhost:5173'));
});
