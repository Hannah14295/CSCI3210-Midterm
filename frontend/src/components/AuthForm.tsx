import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../auth';
import { describeError } from '../api';
import { Notice } from './Notice';

export function AuthForm() {
  const { authenticate } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try { await authenticate(mode, username, password); setPassword(''); }
    catch (problem) { setError(describeError(problem)); }
    finally { setBusy(false); }
  }
  return <div className="auth-layout">
    <section className="panel auth-panel" aria-labelledby="auth-title">
      <h2 id="auth-title">{mode === 'login' ? 'Welcome!' : 'Join the starting line.'}</h2>
      <p className="muted">{mode === 'login' ? 'Log in to create a room or join a race.' : 'Create a player account to start racing.'}</p>
      <form onSubmit={submit}>
        <label htmlFor="username">Username</label>
        <input id="username" name="username" autoComplete="username" maxLength={150} required value={username} onChange={e => setUsername(e.target.value)} />
        <label htmlFor="password">Password</label>
        <input id="password" name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} maxLength={128} required value={password} onChange={e => setPassword(e.target.value)} />
        {mode === 'register' && <p className="input-help">Use at least 8 characters. Avoid common passwords and passwords similar to your username.</p>}
        <Notice message={error} />
        <button className="button primary wide" disabled={busy}>{busy ? mode === 'login' ? 'Logging in…' : 'Creating account…' : mode === 'login' ? 'Log in →' : 'Create account →'}</button>
      </form>
      <p className="auth-switch">{mode === 'login' ? 'New to the track?' : 'Already have an account?'} <button className="text-button" disabled={busy} onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>{mode === 'login' ? 'Create an account' : 'Log in'}</button></p>
    </section>
  </div>;
}
