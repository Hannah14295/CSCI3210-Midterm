import { memo } from 'react';
import type { Participant } from '../types';

export const RaceProgress = memo(function RaceProgress({
  participants, playerId,
}: { participants: Participant[]; playerId: number }) {
  return <section className="race-progress" aria-label="Racer progress">
    <h2>Racers</h2>
    <ul className="racer-list">
      {participants.map(entry => <li className="racer-progress" key={entry.id}>
        <span id={`racer-${entry.id}`}>
          {entry.player.username}{entry.player.id === playerId ? ' (you)' : ''}
        </span>{' '}
        <progress aria-labelledby={`racer-${entry.id}`} max={100} value={entry.metrics.progress} />{' '}
        <span>{entry.metrics.progress.toFixed(0)}%</span>
      </li>)}
    </ul>
  </section>;
});
