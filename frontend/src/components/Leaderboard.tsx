import { useEffect, useState } from 'react';
import { describeError, request } from '../api';
import { pageSchema, resultSchema } from '../types';
import type { Result } from '../types';
import { Notice } from './Notice';

export function Leaderboard() {
  const [rows, setRows] = useState<Result[]>([]);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [count, setCount] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('');
    request(`leaderboard/?page=${page}`, pageSchema(resultSchema), null, { signal: controller.signal })
      .then(result => { setRows(result.results); setCount(result.count); setHasNext(Boolean(result.next)); })
      .catch(problem => { if (!controller.signal.aborted) setError(describeError(problem)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [page, refresh]);
  return <>
    <div className="page-heading"><div><span className="eyebrow">THE FAST LANE</span><h1>Leave your mark<span className="yellow-dot">.</span></h1><p className="muted">Every completed race. Ranked by speed.</p></div><button className="button subtle" disabled={loading} onClick={() => setRefresh(value => value + 1)}>↻ Refresh</button></div>
    <Notice message={error} />
    <section className="panel leaderboard-panel"><div className="section-heading"><h2>All-time results</h2><span className="mono muted">{count} completed runs</span></div>
      {loading ? <p role="status" className="empty">Loading results…</p> : !rows.length ? <div className="empty"><span className="empty-flag">⚑</span><h3>The podium is waiting.</h3><p>Finish a race to put your name on the board.</p></div> : <div className="table-scroll"><table><thead><tr><th scope="col">Rank</th><th scope="col">Racer</th><th scope="col">WPM</th><th scope="col">Time</th><th scope="col">Race</th><th scope="col">Finished</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><span className={`rank rank-${row.rank}`}>{String(row.rank).padStart(2, '0')}</span></td><td><strong>{row.player.username}</strong></td><td className="wpm-cell">{row.wpm.toFixed(2)}</td><td className="mono">{row.elapsed_seconds.toFixed(2)}s</td><td className="mono">#{row.race}</td><td className="muted">{new Date(row.finished_at).toLocaleDateString()}</td></tr>)}</tbody></table></div>}
      <div className="pagination"><button className="button subtle" disabled={loading || page === 1} onClick={() => setPage(value => value - 1)}>← Previous</button><span>Page {page}</span><button className="button subtle" disabled={loading || !hasNext} onClick={() => setPage(value => value + 1)}>Next →</button></div>
    </section>
    <p className="input-help">Each run is a separate result. Equal WPM is ordered by earlier finish time. Different passages can vary in difficulty.</p>
  </>;
}
