import { memo, useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth';
import { describeError, request } from '../api';
import { raceSchema } from '../types';
import { useRace } from '../hooks/useRace';
import { Notice } from './Notice';
import { RaceTrack } from './RaceTrack';

const Passage = memo(function Passage({ target, text }: { target: string; text: string }) {
  const typed = Array.from(text);
  return <div className="typing-passage" aria-label={`Passage: ${target}`}>{Array.from(target).map((character, index) =>
    <span key={index} aria-hidden="true" className={`${index < typed.length ? character === typed[index] ? 'char-correct' : 'char-wrong' : ''} ${index === typed.length ? 'char-cursor' : ''}`}>{character}</span>,
  )}</div>;
});

export function RaceRoom({ raceId, onBack }: { raceId: number; onBack: () => void }) {
  const { token, user } = useAuth();
  if (!token || !user) return null;
  return <ConnectedRace raceId={raceId} token={token} playerId={user.id} onBack={onBack} />;
}

function ConnectedRace({ raceId, token, playerId, onBack }: { raceId: number; token: string; playerId: number; onBack: () => void }) {
  const { race, text, updateText, connection, error, reconnect } = useRace(raceId, token, playerId);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [copied, setCopied] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const own = race?.participants.find(entry => entry.player.id === playerId);
  const finished = Boolean(own?.finished_at);
  const canType = connection === 'connected' && race?.status === 'running' && Boolean(race.started_at) && !finished;
  useEffect(() => { if (canType) input.current?.focus(); }, [canType]);
  async function start() {
    setBusy(true); setActionError('');
    try { await request(`races/${raceId}/start/`, raceSchema, token, { method: 'POST' }); }
    catch (problem) { setActionError(describeError(problem)); }
    finally { setBusy(false); }
  }
  async function copy() {
    try { await navigator.clipboard.writeText(String(raceId)); setCopied(true); }
    catch { setActionError(`Share this race ID: ${raceId}`); }
  }
  return <>
    <div className="room-heading"><button className="text-button back" onClick={onBack}>← Race lobby</button><span className={`connection ${connection}`} role="status"><i />{connection === 'connected' ? 'Live connection' : connection}</span></div>
    <div className="page-heading"><div><span className="eyebrow">ROOM #{raceId}</span><h1>{finished ? 'Across the line.' : race?.status === 'running' ? 'Make every key count.' : 'Your starting line.'}</h1><p className="muted">{race ? `Hosted by ${race.host.username} · ${race.participants.length} ${race.participants.length === 1 ? 'racer' : 'racers'}` : 'Connecting to your race…'}</p></div><button className="button subtle" onClick={copy}>{copied ? 'ID copied ✓' : `Copy race ID #${raceId}`}</button></div>
    <Notice message={error || actionError} />
    {connection === 'disconnected' && <button className="button dark" onClick={reconnect}>Reconnect to race</button>}
    {race && <>
      <RaceTrack participants={race.participants} playerId={playerId} />
      <div className="stats-grid" aria-label="Your race statistics">
        <div><span>WORDS PER MINUTE</span><strong>{(own?.metrics.wpm || 0).toFixed(1)}<small> WPM</small></strong></div>
        <div><span>ACCURACY</span><strong>{(own?.metrics.accuracy ?? 100).toFixed(0)}<small>%</small></strong></div>
        <div><span>PROGRESS</span><strong>{(own?.metrics.progress || 0).toFixed(0)}<small>%</small></strong></div>
        <div><span>RACE STATUS</span><strong className="status-value">{finished ? 'Finished' : race.status}</strong></div>
      </div>
      {race.status === 'waiting' && <div className="waiting-banner"><div><strong>Everyone on the grid?</strong><p>{race.host.id === playerId ? 'Share the race ID, wait for your friends, then start when you’re ready.' : `Waiting for ${race.host.username} to start. Your input will unlock automatically.`}</p></div>{race.host.id === playerId && <button className="button primary" disabled={busy || connection !== 'connected'} onClick={() => void start()}>{busy ? 'Starting…' : 'Start race →'}</button>}</div>}
      {finished && <div className="finish-banner" role="status"><span className="finish-icon">⚑</span><div><strong>Result saved. Nice run.</strong><p>{own?.wpm?.toFixed(2)} WPM in {own?.elapsed_seconds?.toFixed(2)} seconds. Your result is on the leaderboard.</p></div></div>}
      {race.status === 'running' && !race.started_at && <Notice message="This race was manually marked Running without a start time. Create a fresh room through the lobby." />}
      <section className="panel typing-panel"><div className="section-heading"><span className="eyebrow">THE PASSAGE</span><span className="muted">{Array.from(race.paragraph_text).length} characters</span></div>
        <Passage target={race.paragraph_text} text={text} />
        <label htmlFor="race-input">Your typing</label>
        <textarea ref={input} id="race-input" value={text} disabled={!canType} maxLength={race.paragraph_text.length} onChange={event => updateText(event.target.value)} spellCheck={false} autoComplete="off" autoCorrect="off" autoCapitalize="off" placeholder={race.status === 'waiting' ? 'Your input unlocks when the host starts…' : finished ? 'Your result is saved.' : 'Type the passage here…'} aria-describedby="typing-tip" />
        <div className="typing-bottom"><span id="typing-tip">Correct mistakes to move forward. Match spaces and punctuation.</span><span>{Array.from(text).length} / {Array.from(race.paragraph_text).length}</span></div>
      </section>
      <section className="racers-section"><h2>On the track</h2><div className="rooms-list">{race.participants.map(entry => <div className="room-row" key={entry.id}><span className="avatar">{entry.player.username.charAt(0).toUpperCase()}</span><div className="room-info"><strong>{entry.player.username}{entry.player.id === playerId ? ' (you)' : ''}</strong><span>{entry.finished_at ? 'Finished' : `${entry.metrics.progress.toFixed(0)}% complete`}</span></div><span className="mono">{entry.metrics.wpm.toFixed(1)} WPM</span><progress aria-label={`${entry.player.username} progress`} value={entry.metrics.progress} max={100} /></div>)}</div></section>
      <p className="input-help">Accuracy describes your current text. WPM uses five characters per word and the shared server start time.</p>
    </>}
  </>;
}
