import { useEffect, useRef, useState } from 'react';
import type { RaceResults } from '../raceResults';
import { describeError } from '../api';
import { Notice } from './Notice';

export function RaceResultsDialog({ results, raceId, playerId, onBack, isHost, onRaceAgain }: {
  results: RaceResults; raceId: number; playerId: number; onBack: () => void;
  isHost: boolean; onRaceAgain: () => Promise<void>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function rematch() {
    setBusy(true); setError('');
    try { await onRaceAgain(); }
    catch (problem) { setError(describeError(problem)); }
    finally { setBusy(false); }
  }
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => { if (element?.open) element.close(); };
  }, [raceId]);

  return <>
    <button className="button primary" onClick={() => dialog.current?.showModal()}>View race results</button>
    <dialog ref={dialog} className="race-results-dialog" aria-labelledby="race-results-title">
      <div className="results-heading">
        <div><span className="eyebrow">RACE #{raceId}</span><h2 id="race-results-title">Race results</h2></div>
        <button className="button subtle" autoFocus aria-label="Close race results" onClick={() => dialog.current?.close()}>×</button>
      </div>
      <p className="muted">{results.scores.length === 1 ? 'Practice complete!' : 'Everyone has finished!'}</p>
      <div className="race-winners">
        <section className="winner-card">
          <h3>WPM {results.speedWinners.length === 1 ? 'winner' : 'winners'}</h3>
          <strong>{results.speedWinners.map(entry => entry.player.username).join(', ')}</strong>
          <span>{results.speedWinners[0].wpm.toFixed(2)} WPM</span>
        </section>
        <section className="winner-card">
          <h3>Accuracy {results.accuracyWinners.length === 1 ? 'winner' : 'winners'}</h3>
          <strong>{results.accuracyWinners.map(entry => entry.player.username).join(', ')}</strong>
          <span>{results.accuracyWinners[0].accuracy.toFixed(2)}%</span>
        </section>
      </div>
      <div className="table-scroll"><table className="race-score-table">
        <caption>Final scores</caption>
        <thead><tr><th scope="col">Racer</th><th scope="col">WPM</th><th scope="col">Accuracy</th><th scope="col">Time</th></tr></thead>
        <tbody>{results.scores.map(entry => <tr key={entry.id}>
          <th scope="row">{entry.player.username}{entry.player.id === playerId ? ' (you)' : ''}</th>
          <td>{entry.wpm.toFixed(2)}</td><td>{entry.accuracy.toFixed(2)}%</td><td>{entry.elapsed_seconds.toFixed(2)}s</td>
        </tr>)}</tbody>
      </table></div>
      <Notice message={error} />
      <div className="results-actions">
        <button className="button subtle" onClick={() => dialog.current?.close()}>Close</button>
        <button className="button subtle" onClick={onBack}>Back to race lobby</button>
        {isHost && <button className="button primary" disabled={busy} onClick={() => void rematch()}>{busy ? 'Creating race…' : 'Race again'}</button>}
      </div>
    </dialog>
  </>;
}
