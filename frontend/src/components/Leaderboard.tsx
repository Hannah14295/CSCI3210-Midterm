import { useEffect, useState } from 'react';
import { describeError, request } from '../api';
import { pageSchema, resultSchema } from '../types';
import type { Result } from '../types';
import { Notice } from './Notice';

type Metric = 'wpm' | 'accuracy';

function Rankings({ metric, rows, loading }: { metric: Metric; rows: Result[]; loading: boolean }) {
  const isSpeed = metric === 'wpm';
  return <section className="panel leaderboard-panel" aria-labelledby={`${metric}-title`} aria-busy={loading}>
    <div className="section-heading">
      <h2 id={`${metric}-title`}>{isSpeed ? 'WPM' : 'Accuracy'}</h2>
      <span className="leaderboard-category">{isSpeed ? 'Speed' : 'Precision'}</span>
    </div>
    {loading ? <p role="status" className="empty">Loading results…</p>
      : !rows.length ? <div className="empty"><h3>No results yet</h3><p>Finish a race to join the leaderboard.</p></div>
      : <div className="table-scroll"><table>
        <thead><tr>
          <th scope="col">Rank</th><th scope="col">Racer</th>
          <th scope="col">{isSpeed ? 'WPM' : 'Accuracy'}</th>
          <th scope="col">{isSpeed ? 'Accuracy' : 'WPM'}</th>
        </tr></thead>
        <tbody>{rows.map(row => {
          const accuracy = row.accuracy === null ? '—' : `${row.accuracy.toFixed(2)}%`;
          return <tr key={row.id}>
            <td><span className={`rank rank-${row.rank}`}>{row.rank}</span></td>
            <th scope="row" className="racer-name">{row.player.username}<span className="result-race">Race #{row.race}</span></th>
            <td className="score-cell">{isSpeed ? row.wpm.toFixed(2) : accuracy}</td>
            <td className="secondary-score">{isSpeed ? accuracy : row.wpm.toFixed(2)}</td>
          </tr>;
        })}</tbody>
      </table></div>}
  </section>;
}

export function Leaderboard() {
  const [speed, setSpeed] = useState<Result[]>([]);
  const [accuracy, setAccuracy] = useState<Result[]>([]);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    Promise.all([
      request('leaderboard/?metric=wpm&limit=10', pageSchema(resultSchema), null, { signal: controller.signal }),
      request('leaderboard/?metric=accuracy&limit=10', pageSchema(resultSchema), null, { signal: controller.signal }),
    ]).then(([fastest, mostAccurate]) => {
      setSpeed(fastest.results.slice(0, 10));
      setAccuracy(mostAccurate.results.slice(0, 10));
    }).catch(problem => { if (!controller.signal.aborted) setError(describeError(problem)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [refresh]);
  return <div className="arena leaderboards">
    <div className="page-heading">
      <div><h1>Leaderboards</h1><p className="muted">Completed races ranked by speed and accuracy.</p></div>
      <button className="button subtle" disabled={loading} onClick={() => setRefresh(value => value + 1)}>↻ Refresh</button>
    </div>
    <Notice message={error} />
    <div className="leaderboard-grid">
      <Rankings metric="wpm" rows={speed} loading={loading} />
      <Rankings metric="accuracy" rows={accuracy} loading={loading} />
    </div>
  </div>;
}
