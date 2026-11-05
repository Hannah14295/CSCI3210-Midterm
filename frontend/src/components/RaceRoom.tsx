import { memo, useEffect, useRef, useState } from 'react';
import { useAuth } from '../auth';
import { describeError, request } from '../api';
import { raceSchema } from '../types';
import { useRace } from '../hooks/useRace';
import { Notice } from './Notice';
import { RaceProgress } from './RaceProgress';
import { previewTyping } from '../typing';
import { raceResults } from '../raceResults';
import { RaceResultsDialog } from './RaceResultsDialog';
import { RaceMusic } from './RaceMusic';
import { FinishConfetti } from './FinishConfetti';
import { countdownAt } from '../countdown';

const Passage = memo(function Passage({
  target,
  text,
  cursor,
}: {
  target: string;
  text: string;
  cursor: number | null;
}) {
  const characters = Array.from(target);
  const typed = Array.from(text);
  const cursorPosition = cursor ?? typed.length;

  return (
    <div
      className="typing-passage"
      aria-label={`Passage: ${target}`}
    >
      {characters.map((character, index) => {
        let className = '';

        if (index < typed.length) {
          className = character === typed[index]
            ? 'char-correct'
            : 'char-wrong';
        }

        if (index === cursorPosition) {
          className += ' char-cursor';
        }

        return (
          <span key={index} aria-hidden="true" className={className}>
            {character}
          </span>
        );
      })}

      {cursorPosition === characters.length && (
        <span className="char-cursor" aria-hidden="true">
          {'\u200b'}
        </span>
      )}
    </div>
  );
});

export function RaceRoom({ raceId, onBack, onEnter }: { raceId: number; onBack: () => void; onEnter: (id: number) => void }) {
  const { token, user } = useAuth();
  if (!token || !user) return null;
  return <ConnectedRace raceId={raceId} token={token} playerId={user.id} onBack={onBack} onEnter={onEnter} />;
}

function ConnectedRace({ raceId, token, playerId, onBack, onEnter }: { raceId: number; token: string; playerId: number; onBack: () => void; onEnter: (id: number) => void }) {
  const { race, text, typedAt, typingStartedAt, clockOffset, updateText, applyRace, connection, error, reconnect } = useRace(raceId, token, playerId);
  const [now, setNow] = useState(Date.now);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [copied, setCopied] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  const [caret, setCaret] = useState<number | null>(null);
  const own = race?.participants.find(entry => entry.player.id === playerId);
  const finished = Boolean(own?.finished_at);
  const results = race ? raceResults(race) : null;
  const remaining = race?.participants.filter(entry => !entry.finished_at).length || 0;
  const countdown = race?.status === 'running' && !finished ? countdownAt(race.started_at, now + clockOffset) : null;
  const countingDown = countdown !== null && countdown > 0;
  const livePreview = connection === 'connected' && race?.status === 'running' && Boolean(race.started_at) && !finished && !countingDown;
  const complete = Boolean(race?.paragraph_text) && Array.from(text).length === Array.from(race?.paragraph_text || '').length;
  const metrics = livePreview && race
    ? previewTyping(race.paragraph_text, text,
      typingStartedAt === null ? 0 : ((complete ? typedAt : Math.max(now, typedAt)) - typingStartedAt) / 1000)
    : own?.metrics;
  const displayedParticipants = livePreview && race && metrics
    ? race.participants.map(entry => entry.player.id === playerId ? { ...entry, metrics } : entry)
    : race?.participants || [];
  const canType = livePreview && !complete;
  useEffect(() => {
    if (race?.next_race_id) onEnter(race.next_race_id);
  }, [race?.next_race_id, onEnter]);
  useEffect(() => {
    if (race?.status !== 'running' || finished) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 100);
    return () => window.clearInterval(timer);
  }, [race?.status, race?.started_at, finished]);
  useEffect(() => { if (canType) input.current?.focus(); }, [canType]);
  async function start() {
    setBusy(true); setActionError('');
    try { applyRace(await request(`races/${raceId}/start/`, raceSchema, token, { method: 'POST' })); }
    catch (problem) { setActionError(describeError(problem)); }
    finally { setBusy(false); }
  }
  async function copy() {
    try { await navigator.clipboard.writeText(String(raceId)); setCopied(true); }
    catch { setActionError(`Share this race ID: ${raceId}`); }
  }
  async function raceAgain() {
    const next = await request(`races/${raceId}/rematch/`, raceSchema, token, { method: 'POST' });
    onEnter(next.id);
  }
  return <div className="arena race-room">
    <div className="room-heading"><button className="text-button back" onClick={onBack}>← Race lobby</button><span className={`connection ${connection}`} role="status"><i />{connection === 'connected' ? 'Live connection' : connection}</span></div>
    <div className="page-heading"><div><span className="eyebrow">ROOM #{raceId}</span><h1>{finished ? 'Across the line.' : race?.status === 'running' ? 'Make every key count.' : 'Your starting line.'}</h1><p className="muted">{race ? `Hosted by ${race.host.username} · ${race.participants.length} ${race.participants.length === 1 ? 'racer' : 'racers'}` : 'Connecting to your race…'}</p></div><button className="button subtle" onClick={copy}>{copied ? 'ID copied ✓' : `Copy race ID #${raceId}`}</button></div>
    <Notice message={error || actionError} />
    <RaceMusic playing={canType} />
    {(connection === 'disconnected' || connection === 'reconnecting') && <button className="button dark" onClick={reconnect}>Reconnect to race</button>}
    {race && <>
      <RaceProgress participants={displayedParticipants} playerId={playerId} />
      {countdown !== null && <div className={`race-countdown${countingDown ? '' : ' go'}`} role="status" aria-live="polite" aria-atomic="true">
        <strong>{countingDown ? countdown : 'Go!'}</strong>
        {countingDown && <span>Get ready…</span>}
      </div>}
      <div className="stats-grid" aria-label="Your race statistics">
        <div><span>{livePreview ? 'WPM · LIVE ESTIMATE' : 'WORDS PER MINUTE'}</span><strong>{(metrics?.wpm || 0).toFixed(1)}<small> WPM</small></strong></div>
        <div><span>ACCURACY</span><strong>{(metrics?.accuracy ?? 100).toFixed(0)}<small>%</small></strong></div>
        <div><span>PROGRESS</span><strong>{(metrics?.progress || 0).toFixed(0)}<small>%</small></strong></div>
        <div><span>RACE STATUS</span><strong className="status-value">{race.status === 'finished' ? 'Finished' : finished ? 'Waiting for racers' : countingDown ? 'Starting…' : livePreview && complete ? 'Saving result…' : race.status}</strong></div>
      </div>
      {race.status === 'waiting' && <div className="waiting-banner"><div><strong>Everyone on the grid?</strong><p>{race.host.id === playerId ? 'Share the race ID, wait for your friends, then start when you’re ready.' : `Waiting for ${race.host.username} to start. Your input will unlock automatically.`}</p></div>{race.host.id === playerId && <button className="button primary" disabled={busy || connection !== 'connected'} onClick={() => void start()}>{busy ? 'Starting…' : 'Start race →'}</button>}</div>}
      {finished && race.status === 'running' && <div className="waiting-banner" role="status"><div><strong>Your result is saved.</strong><p>Waiting for {remaining} {remaining === 1 ? 'racer' : 'racers'} to finish.</p></div></div>}
      {results && <RaceResultsDialog results={results} raceId={raceId} playerId={playerId} onBack={onBack} isHost={race.host.id === playerId} onRaceAgain={raceAgain} />}
      {race.status === 'running' && !race.started_at && <Notice message="This race was manually marked Running without a start time. Create a fresh room through the lobby." />}
      <section className="panel typing-panel">
        <div className="section-heading">
          <span className="eyebrow">THE PASSAGE</span>
          <span className="muted">
            {Array.from(text).length}
            {' / '}
            {Array.from(race.paragraph_text).length} characters
          </span>
        </div>

        <div className="typing-surface">
          <Passage
            target={race.paragraph_text}
            text={text}
            cursor={caret}
          />

          <textarea
            ref={input}
            id="race-input"
            aria-label="Type the displayed passage"
            aria-description="Type forward only. Backspace and earlier edits are disabled."
            value={text}
            disabled={!canType}
            maxLength={race.paragraph_text.length}
            onKeyDown={event => {
              const blockedKeys = [
                'Backspace',
                'Delete',
                'ArrowLeft',
                'ArrowRight',
                'ArrowUp',
                'ArrowDown',
                'Home',
                'End',
              ];

              if (blockedKeys.includes(event.key)) {
                event.preventDefault();
              }
            }}
            onChange={event => {
              const nextText = event.target.value;

              // Previously entered characters must stay exactly as they were.
              if (nextText.startsWith(text)) {
                updateText(nextText, Array.from(nextText).length === Array.from(race.paragraph_text).length);
                setCaret(Array.from(nextText).length);
              }
            }}
            onSelect={event => {
              const field = event.currentTarget;
              const end = field.value.length;

              field.setSelectionRange(end, end);
              setCaret(Array.from(field.value).length);
            }}
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
          />
        </div>
      </section>
    </>}
    <FinishConfetti finished={own ? finished : null} />
  </div>;
}
