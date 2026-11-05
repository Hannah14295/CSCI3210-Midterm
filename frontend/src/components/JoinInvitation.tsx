import { useEffect, useState } from 'react';
import { describeError, request } from '../api';
import { participantSchema, raceSchema } from '../types';
import { Notice } from './Notice';

export function JoinInvitation({ raceId, token, playerId, onJoined, onCancel }: {
  raceId: number; token: string; playerId: number;
  onJoined: (id: number) => void; onCancel: () => void;
}) {
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    async function join() {
      try {
        const race = await request(`races/${raceId}/`, raceSchema, token, { signal: controller.signal });
        if (!race.participants.some(entry => entry.player.id === playerId)) {
          await request(`races/${raceId}/join/`, participantSchema, token, { method: 'POST', signal: controller.signal });
        }
        if (!controller.signal.aborted) onJoined(raceId);
      } catch (problem) { if (!controller.signal.aborted) setError(describeError(problem)); }
    }
    void join();
    return () => controller.abort();
  }, [raceId, token, playerId, onJoined]);
  return <div className="arena"><h1>Joining race #{raceId}</h1>
    {error ? <Notice message={error} /> : <p role="status">Joining room…</p>}
    <button className="button subtle" onClick={onCancel}>Back to race lobby</button>
  </div>;
}
