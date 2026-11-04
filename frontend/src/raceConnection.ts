import type { Race } from './types';

export type ConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

const terminalCodes = new Set([1008, 1009, 4401, 4403]);

/** Recover transient interruptions; authentication/access failures require user action. */
export function createRaceConnection(options: {
  createSocket: () => WebSocket;
  onSocket: (socket: WebSocket) => void;
  onMessage: (event: MessageEvent, socket: WebSocket) => void;
  onState: (state: ConnectionState) => void;
  onDisconnect: (code: number, reason: string) => void;
  onProblem: (problem: unknown) => void;
}) {
  let socket: WebSocket | null = null;
  let stopped = false;
  let authenticated = false;
  let failures = 0;
  let previouslyConnected = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let connectTimer: ReturnType<typeof setTimeout> | null = null;
  let pingTimer: ReturnType<typeof setTimeout> | null = null;
  let pongTimer: ReturnType<typeof setTimeout> | null = null;

  function clearConnectionTimers() {
    if (connectTimer !== null) clearTimeout(connectTimer);
    if (pingTimer !== null) clearTimeout(pingTimer);
    if (pongTimer !== null) clearTimeout(pongTimer);
    connectTimer = pingTimer = pongTimer = null;
  }

  function detach(target: WebSocket) {
    target.onmessage = target.onclose = target.onerror = null;
  }

  function disconnected(target: WebSocket, code: number, reason: string) {
    if (stopped || target !== socket) return;
    detach(target);
    socket = null;
    authenticated = false;
    clearConnectionTimers();
    options.onDisconnect(code, reason);
    if (terminalCodes.has(code)) { options.onState('disconnected'); return; }
    options.onState('reconnecting');
    // Back off to 30 seconds rather than hammering a sleeping/unavailable server.
    const delay = code === 4429 ? 10_000 : Math.min(30_000, 1000 * 2 ** Math.min(failures, 5));
    failures++;
    retryTimer = setTimeout(connect, delay);
  }

  function restartStale(target: WebSocket, reason: string) {
    if (target !== socket || stopped) return;
    disconnected(target, 4000, reason);
    target.close(4000, reason);
  }

  function schedulePing() {
    if (pingTimer !== null) clearTimeout(pingTimer);
    pingTimer = setTimeout(ping, 20_000);
  }

  function ping() {
    if (pingTimer !== null) clearTimeout(pingTimer);
    pingTimer = null;
    const target = socket;
    if (!target || !authenticated || target.readyState !== 1 || pongTimer !== null) return;
    try {
      target.send(JSON.stringify({ type: 'ping' }));
      pongTimer = setTimeout(() => restartStale(target, 'Keepalive timed out'), 45_000);
    } catch {
      restartStale(target, 'Keepalive could not be sent');
    }
  }

  function connect() {
    retryTimer = null;
    if (stopped) return;
    options.onState(previouslyConnected || failures ? 'reconnecting' : 'connecting');
    let target: WebSocket;
    try { target = options.createSocket(); }
    catch (problem) {
      options.onProblem(problem);
      options.onState('disconnected');
      return;
    }
    socket = target;
    authenticated = false;
    target.onmessage = event => {
      if (stopped || target !== socket) return;
      // Any server message proves the connection is alive, not just pong.
      if (pongTimer !== null) {
        clearTimeout(pongTimer); pongTimer = null; schedulePing();
      }
      options.onMessage(event, target);
    };
    target.onclose = event => disconnected(target, event.code, event.reason);
    // Browsers provide the useful close code in onclose, after onerror.
    target.onerror = () => {};
    connectTimer = setTimeout(() => restartStale(target, 'Connection timed out'), 90_000);
    options.onSocket(target);
  }

  connect();
  return {
    connected() {
      if (stopped || !socket) return;
      authenticated = true;
      previouslyConnected = true;
      failures = 0;
      if (connectTimer !== null) clearTimeout(connectTimer);
      connectTimer = null;
      options.onState('connected');
      schedulePing();
    },
    reconnect() {
      if (stopped) return;
      if (retryTimer !== null) clearTimeout(retryTimer);
      retryTimer = null;
      clearConnectionTimers();
      const target = socket;
      socket = null;
      authenticated = false;
      if (target) { detach(target); target.close(); }
      connect();
    },
    check() {
      if (stopped) return;
      if (authenticated) ping();
      else if (retryTimer !== null) this.reconnect();
    },
    stop() {
      stopped = true;
      if (retryTimer !== null) clearTimeout(retryTimer);
      retryTimer = null;
      clearConnectionTimers();
      if (socket) { detach(socket); socket.close(); socket = null; }
    },
  };
}

/** Retain an unacknowledged append-only draft only when it extends saved input. */
export function restoreRaceDraft(saved: string, draft: string, canResume: boolean) {
  return canResume && draft.startsWith(saved) ? draft : saved;
}

export function mergeRaceSnapshot(previous: Race | null, incoming: Race): Race {
  if (!previous || previous.id !== incoming.id) return incoming;
  const states = { waiting: 0, running: 1, finished: 2 };
  return {
    ...incoming,
    status: states[previous.status] > states[incoming.status] ? previous.status : incoming.status,
    started_at: incoming.started_at || previous.started_at,
    participants: incoming.participants.map(entry => {
      const old = previous.participants.find(item => item.id === entry.id);
      return old && old.revision > entry.revision ? old : entry;
    }),
  };
}
