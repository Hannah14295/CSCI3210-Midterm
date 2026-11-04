import { useCallback, useEffect, useRef, useState } from 'react';
import { describeError } from '../api';
import { webSocketUrl } from '../config';
import { socketEventSchema } from '../types';
import type { Race } from '../types';
import { createTypingSender } from '../typingSender';
import { createRaceConnection, mergeRaceSnapshot, restoreRaceDraft } from '../raceConnection';
import type { ConnectionState } from '../raceConnection';

export function useRace(raceId: number, token: string, playerId: number) {
  const [race, setRace] = useState<Race | null>(null);
  const [text, setText] = useState('');
  const [typedAt, setTypedAt] = useState(0);
  const [connection, setConnection] = useState<ConnectionState>('connecting');
  const [error, setError] = useState('');
  const senderRef = useRef<ReturnType<typeof createTypingSender> | null>(null);
  const connectionRef = useRef<ReturnType<typeof createRaceConnection> | null>(null);
  const draft = useRef('');
  const applyRace = useCallback((incoming: Race) => {
    setRace(previous => mergeRaceSnapshot(previous, incoming));
  }, []);

  useEffect(() => {
    const transport = createRaceConnection({
      createSocket: () => new WebSocket(webSocketUrl(raceId)),
      onState: state => {
        setConnection(state);
        if (state === 'connected') setError('');
      },
      onProblem: problem => setError(describeError(problem)),
      onSocket: socket => {
        setError('');
        senderRef.current?.stop();
        senderRef.current = createTypingSender(value => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'typing.update', text: value }));
          }
        });
      },
      onDisconnect: (code, reason) => {
        senderRef.current?.stop();
        const messages: Record<number, string> = {
          4401: 'Your login was rejected. Reload the page and log in again.',
          4403: 'You are not a participant in this race. Return to the lobby and join first.',
          1008: 'The server rejected this connection. Reload the page to try again.',
          1009: 'The server rejected an oversized message. Reload the page to reconnect.',
        };
        setError(messages[code] || 'Connection interrupted. Reconnecting…');
        console.warn('Race connection interrupted', { code, reason });
      },
      onMessage: (event, socket) => {
        if (typeof event.data !== 'string') return;
        let raw: unknown;
        try { raw = JSON.parse(event.data); }
        catch { setError('An unreadable live update arrived. Reconnect to refresh.'); return; }
        const parsed = socketEventSchema.safeParse(raw);
        if (!parsed.success) { setError('An unexpected live update arrived. Reconnect to refresh.'); return; }
        const data = parsed.data;
        const sender = senderRef.current;
        if (data.type === 'auth.required') socket.send(JSON.stringify({ type: 'authenticate', token }));
        if (data.type === 'connected') {
          const own = data.race.participants.find(entry => entry.player.id === playerId);
          const previousDraft = draft.current;
          const restored = restoreRaceDraft(data.your_text, previousDraft,
            data.race.status === 'running' && !own?.finished_at);
          draft.current = restored;
          setText(restored);
          setTypedAt(previous => previous && restored === previousDraft ? previous : Date.now());
          applyRace(data.race);
          transport.connected();
          if (data.race.status === 'finished' || own?.finished_at) sender?.stop();
          else if (restored !== data.your_text) {
            sender?.queue(restored, Array.from(restored).length === Array.from(data.race.paragraph_text).length);
          }
        }
        if (data.type === 'race.updated' || data.type === 'pong') {
          if (data.race.status === 'finished') sender?.stop();
          else {
            const own = data.race.participants.find(entry => entry.player.id === playerId);
            if (own) sender?.acknowledge(own.metrics.typed_characters);
          }
          applyRace(data.race);
        }
        if (data.type === 'progress.updated') {
          setRace(previous => previous ? ({ ...previous, participants: previous.participants.map(entry =>
            entry.player.id !== data.player.id || entry.revision > data.revision ? entry : {
              ...entry, revision: data.revision, metrics: data,
              wpm: data.finished_at ? data.wpm : null,
              accuracy: data.finished_at ? data.accuracy : null,
              finished_at: data.finished_at,
              elapsed_seconds: data.finished_at ? data.elapsed_seconds : null,
            },
          ) }) : previous);
          if (data.player.id === playerId) {
            if (data.finished_at) sender?.stop();
            else sender?.acknowledge(data.typed_characters);
            setError('');
          }
        }
        if (data.type === 'error') { sender?.reset(); setError(describeError(data.detail)); }
      },
    });
    connectionRef.current = transport;
    const checkConnection = () => transport.check();
    const onVisible = () => { if (document.visibilityState === 'visible') transport.check(); };
    window.addEventListener('online', checkConnection);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      transport.stop();
      senderRef.current?.stop();
      senderRef.current = null;
      connectionRef.current = null;
      window.removeEventListener('online', checkConnection);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [raceId, token, playerId, applyRace]);

  const updateText = useCallback((value: string, complete = false) => {
    draft.current = value;
    setText(value); setTypedAt(Date.now());
    senderRef.current?.queue(value, complete);
  }, []);
  return { race, text, typedAt, updateText, applyRace, connection, error,
    reconnect: () => connectionRef.current?.reconnect() };
}
