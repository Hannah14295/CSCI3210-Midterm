import { useCallback, useEffect, useRef, useState } from 'react';
import { describeError } from '../api';
import { webSocketUrl } from '../config';
import { socketEventSchema } from '../types';
import type { Race } from '../types';
import { createTypingSender } from '../typingSender';

type Connection = 'connecting' | 'connected' | 'disconnected';

export function useRace(raceId: number, token: string, playerId: number) {
  const [race, setRace] = useState<Race | null>(null);
  const [text, setText] = useState('');
  const [typedAt, setTypedAt] = useState(0);
  const [connection, setConnection] = useState<Connection>('connecting');
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const senderRef = useRef<ReturnType<typeof createTypingSender> | null>(null);

  useEffect(() => {
    setConnection('connecting'); setError(''); setRace(null);
    let active = true;
    // Token mode avoids accidentally using a different account's admin cookie.
    let socket: WebSocket;
    try {
      socket = new WebSocket(webSocketUrl(raceId));
    } catch (problem) {
      setError(describeError(problem));
      setConnection('disconnected');
      return;
    }
    const sender = createTypingSender(value => {
      if (active && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'typing.update', text: value }));
      }
    });
    senderRef.current = sender;
    socket.onmessage = event => {
      if (!active || typeof event.data !== 'string') return;
      let raw: unknown;
      try { raw = JSON.parse(event.data); } catch { setError('An unreadable live update arrived. Reconnect to refresh.'); return; }
      const parsed = socketEventSchema.safeParse(raw);
      if (!parsed.success) { setError('An unexpected live update arrived. Reconnect to refresh.'); return; }
      const data = parsed.data;
      if (data.type === 'auth.required') socket.send(JSON.stringify({ type: 'authenticate', token }));
      if (data.type === 'connected') {
        setRace(data.race); setText(data.your_text); setTypedAt(Date.now());
        setConnection('connected'); setError('');
      }
      if (data.type === 'race.updated') {
        if (data.race.status === 'finished') sender.stop();
        else {
          const own = data.race.participants.find(entry => entry.player.id === playerId);
          if (own) sender.acknowledge(own.metrics.typed_characters);
        }
        setRace(previous => ({
          ...data.race,
          participants: data.race.participants.map(entry => {
            const old = previous?.participants.find(item => item.id === entry.id);
            return old && old.revision > entry.revision ? old : entry;
          }),
        }));
      }
      if (data.type === 'progress.updated') {
        setRace(previous => previous ? ({ ...previous, participants: previous.participants.map(entry =>
          entry.player.id !== data.player.id || entry.revision > data.revision ? entry : {
            ...entry, revision: data.revision, metrics: data,
            wpm: data.finished_at ? data.wpm : null,
            finished_at: data.finished_at,
            elapsed_seconds: data.finished_at ? data.elapsed_seconds : null,
          },
        ) }) : previous);
        if (data.player.id === playerId) {
          if (data.finished_at) sender.stop();
          else sender.acknowledge(data.typed_characters);
          setError('');
        }
      }
      if (data.type === 'error') { sender.reset(); setError(describeError(data.detail)); }
    };
    socket.onclose = event => {
      if (!active) return;
      setConnection('disconnected');
      sender.stop();
      const messages: Record<number, string> = {
        4401: 'Your login was rejected. Sign out and log in again.',
        4403: 'You are not a participant in this race. Return to the lobby and join first.',
        4429: 'Updates were sent too quickly. Reconnect to continue.',
      };
      setError(messages[event.code] || 'Live connection closed. Reconnect to load your last saved input.');
    };
    socket.onerror = () => {
      if (active) setError('Cannot connect live. The server may be starting up; try reconnecting shortly.');
    };
    return () => {
      active = false;
      sender.stop();
      senderRef.current = null;
      socket.onmessage = null; socket.onclose = null; socket.onerror = null;
      if (socket.readyState === WebSocket.CONNECTING) socket.onopen = () => socket.close();
      else socket.close();
    };
  }, [raceId, token, playerId, attempt]);

  const updateText = useCallback((value: string, complete = false) => {
    setText(value); setTypedAt(Date.now());
    senderRef.current?.queue(value, complete);
  }, []);
  return { race, text, typedAt, updateText, connection, error, reconnect: () => setAttempt(value => value + 1) };
}
