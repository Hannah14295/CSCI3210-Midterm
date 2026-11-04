import { useCallback, useEffect, useRef, useState } from 'react';
import { describeError } from '../api';
import { socketEventSchema } from '../types';
import type { Race } from '../types';

type Connection = 'connecting' | 'connected' | 'disconnected';

export function useRace(raceId: number, token: string, playerId: number) {
  const [race, setRace] = useState<Race | null>(null);
  const [text, setText] = useState('');
  const [connection, setConnection] = useState<Connection>('connecting');
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestText = useRef('');
  const pending = useRef(false);

  useEffect(() => {
    setConnection('connecting'); setError(''); setRace(null);
    pending.current = false;
    let active = true;
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    // Token mode avoids accidentally using a different account's admin cookie.
    const socket = new WebSocket(`${protocol}://${location.host}/ws/races/${raceId}/?auth=token`);
    socketRef.current = socket;
    socket.onmessage = event => {
      if (!active || typeof event.data !== 'string') return;
      let raw: unknown;
      try { raw = JSON.parse(event.data); } catch { setError('An unreadable live update arrived. Reconnect to refresh.'); return; }
      const parsed = socketEventSchema.safeParse(raw);
      if (!parsed.success) { setError('An unexpected live update arrived. Reconnect to refresh.'); return; }
      const data = parsed.data;
      if (data.type === 'auth.required') socket.send(JSON.stringify({ type: 'authenticate', token }));
      if (data.type === 'connected') {
        setRace(data.race); setText(data.your_text); latestText.current = data.your_text;
        setConnection('connected'); setError('');
      }
      if (data.type === 'race.updated') {
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
        if (data.player.id === playerId) setError('');
      }
      if (data.type === 'error') setError(describeError(data.detail));
    };
    socket.onclose = event => {
      if (!active) return;
      setConnection('disconnected');
      if (timer.current) clearTimeout(timer.current);
      timer.current = null;
      const messages: Record<number, string> = {
        4401: 'Your login was rejected. Sign out and log in again.',
        4403: 'You are not a participant in this race. Return to the lobby and join first.',
        4429: 'Updates were sent too quickly. Reconnect to continue.',
      };
      setError(messages[event.code] || 'Live connection closed. Reconnect to load your last saved input.');
    };
    socket.onerror = () => { if (active) setError('Cannot connect live. Check Django is running and reconnect.'); };
    return () => {
      active = false;
      if (timer.current) clearTimeout(timer.current);
      timer.current = null;
      socket.onmessage = null; socket.onclose = null; socket.onerror = null;
      if (socket.readyState === WebSocket.CONNECTING) socket.onopen = () => socket.close();
      else socket.close();
      socketRef.current = null;
    };
  }, [raceId, token, playerId, attempt]);

  const updateText = useCallback((value: string) => {
    setText(value); latestText.current = value; pending.current = true;
    if (timer.current) return;
    timer.current = setTimeout(() => {
      timer.current = null;
      const socket = socketRef.current;
      if (socket?.readyState === WebSocket.OPEN && pending.current) {
        socket.send(JSON.stringify({ type: 'typing.update', text: latestText.current }));
        pending.current = false;
      }
    }, 250);
  }, []);
  return { race, text, updateText, connection, error, reconnect: () => setAttempt(value => value + 1) };
}
