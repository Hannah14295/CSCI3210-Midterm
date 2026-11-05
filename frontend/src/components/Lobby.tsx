import { useEffect, useState } from 'react';
import { useAuth } from '../auth';
import { describeError, request } from '../api';
import { pageSchema, paragraphSchema, participantSchema, raceSchema } from '../types';
import type { Paragraph, Race } from '../types';
import { Notice } from './Notice';
import { passageDifficulty } from '../passageDifficulty';

export function Lobby({ onEnter }: { onEnter: (id: number) => void }) {
  const { token, user } = useAuth();
  const [paragraphs, setParagraphs] = useState<Paragraph[]>([]);
  const [races, setRaces] = useState<Race[]>([]);
  const [selection, setSelection] = useState('');
  const [difficulty, setDifficulty] = useState('all');
  const [joinId, setJoinId] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    Promise.all([
      request('paragraphs/', pageSchema(paragraphSchema), token, { signal: controller.signal }),
      request('races/', pageSchema(raceSchema), token, { signal: controller.signal }),
    ]).then(([passages, rooms]) => {
      setParagraphs(passages.results); setRaces(rooms.results.slice(0, 10));
      setSelection(previous => previous || String(passages.results[0]?.id || ''));
    }).catch(problem => { if (!controller.signal.aborted) setError(describeError(problem)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [token, refresh]);
  async function act(action: () => Promise<number>) {
    setBusy(true); setError('');
    try { onEnter(await action()); }
    catch (problem) { setError(describeError(problem)); }
    finally { setBusy(false); }
  }
  function enter(race: Race) {
    if (race.participants.some(entry => entry.player.id === user?.id)) onEnter(race.id);
    else void act(async () => { await request(`races/${race.id}/join/`, participantSchema, token, { method: 'POST' }); return race.id; });
  }
  const passage = paragraphs.find(item => item.id === Number(selection));
  const choices = paragraphs.filter(item => difficulty === 'all' || passageDifficulty(item.text) === difficulty);
  return <div className="arena lobby">
    <div className="page-heading"><div><h1>Ready to play?</h1><p className="muted">Choose your own room or join another player's room.</p></div></div>
    <Notice message={error} />
    <div className="lobby-grid">
      <section className="panel create-panel"><span className="section-number">01 / CREATE</span><h2>Set the pace.</h2><p className="muted">Choose a passage. You’ll be the host and the first racer.</p>
        <form onSubmit={e => { e.preventDefault(); void act(async () => (await request('races/', raceSchema, token, { method: 'POST', body: { paragraph: Number(selection) } })).id); }}>
          <label htmlFor="difficulty-select">Difficulty by length</label>
          <select id="difficulty-select" value={difficulty} disabled={loading || busy} onChange={e => {
            const next = e.target.value;
            setDifficulty(next);
            const available = paragraphs.filter(item => next === 'all' || passageDifficulty(item.text) === next);
            setSelection(available.some(item => String(item.id) === selection) ? selection : String(available[0]?.id || ''));
          }}>
            <option value="all">All lengths</option><option value="short">Short · up to 300 characters</option><option value="medium">Medium · 301–500 characters</option><option value="long">Long · 501+ characters</option>
          </select>
          <label htmlFor="passage-select">Typing passage</label>
          <select id="passage-select" value={selection} required disabled={loading || busy || !choices.length} onChange={e => setSelection(e.target.value)}>{choices.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select>
          <div className="passage-preview">{loading ? 'Loading passages…' : passage?.text || 'No passages in this length category.'}</div>
          <div className="passage-meta"><span>{passage ? Array.from(passage.text).length : 0} characters</span></div>
          <button className="button primary wide" disabled={loading || busy || !selection}>{busy ? 'Please wait…' : 'Create a race →'}</button>
        </form>
      </section>
      <section className="panel join-panel"><span className="section-number">02 / JOIN</span><h2>Got a race ID?</h2><p className="muted">Enter a friend’s room number to join their starting grid.</p>
        <form onSubmit={e => {
          e.preventDefault(); void act(async () => {
            const race = await request(`races/${Number(joinId)}/`, raceSchema, token);
            if (!race.participants.some(entry => entry.player.id === user?.id)) await request(`races/${race.id}/join/`, participantSchema, token, { method: 'POST' });
            return race.id;
          });
        }}><label htmlFor="join-id">Race ID</label><input id="join-id" type="number" min="1" step="1" placeholder="e.g. 12" required value={joinId} onChange={e => setJoinId(e.target.value)} /><button className="button primary wide" disabled={busy}>Join room →</button></form>
      </section>
    </div>
    <section className="rooms-section"><div className="section-heading"><div><h2>Last 10 rooms</h2></div><button className="button subtle" disabled={loading || busy} onClick={() => setRefresh(value => value + 1)}>↻ Refresh</button></div>
      {loading ? <p className="muted" role="status">Loading rooms…</p> : !races.length ? <div className="empty">The track is quiet. Create the first race.</div> : <div className="rooms-list">{races.map(race => {
        const joined = race.participants.some(entry => entry.player.id === user?.id);
        return <div className="room-row" key={race.id}><span className="room-id">#{race.id}</span><div className="room-info"><strong>{race.host.username}’s race</strong><span>{race.participants.length} {race.participants.length === 1 ? 'racer' : 'racers'}</span></div><span className={`status-tag ${race.status}`}>{race.status}</span><button className="button subtle" disabled={busy || (!joined && race.status !== 'waiting')} onClick={() => enter(race)}>{joined ? 'Open room →' : race.status === 'waiting' ? 'Join →' : 'Closed'}</button></div>;
      })}</div>}
    </section>
  </div>;
}
