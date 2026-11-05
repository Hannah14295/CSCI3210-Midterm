import { useCallback, useEffect, useState } from 'react';
import { useAuth } from './auth';
import { AuthForm } from './components/AuthForm';
import { Lobby } from './components/Lobby';
import { RaceRoom } from './components/RaceRoom';
import { Leaderboard } from './components/Leaderboard';
import { JoinInvitation } from './components/JoinInvitation';
import { invitedRace } from './raceInvite';

export default function App() {
  const { user, token, checking } = useAuth();
  const [tab, setTab] = useState<'arena' | 'leaderboard'>('arena');
  const [raceId, setRaceId] = useState<number | null>(null);
  const [inviteId, setInviteId] = useState(() => invitedRace(window.location.hash));
  const clearInvite = useCallback(() => {
    setInviteId(null);
    if (invitedRace(window.location.hash)) window.history.replaceState(null, '', window.location.pathname + window.location.search);
  }, []);
  const enterInvite = useCallback((id: number) => { setRaceId(id); clearInvite(); }, [clearInvite]);
  useEffect(() => {
    const changed = () => { setInviteId(invitedRace(window.location.hash)); setTab('arena'); };
    window.addEventListener('hashchange', changed);
    return () => window.removeEventListener('hashchange', changed);
  }, []);
  return <div className="app-shell">
    <header className="site-header"><button className="brand" aria-label="TypeRacer home" onClick={() => { setTab('arena'); setRaceId(null); clearInvite(); }}>TypeRacer</button>
      <nav aria-label="Main navigation"><button className={tab === 'arena' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('arena')}>Race arena</button><button className={tab === 'leaderboard' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('leaderboard')}>Leaderboard</button></nav>
    </header>
    <main id="main">{checking ? <div className="empty" role="status">Checking your account…</div> : tab === 'leaderboard' ? <Leaderboard /> : !user ? <AuthForm /> : inviteId && token ? <JoinInvitation raceId={inviteId} token={token} playerId={user.id} onJoined={enterInvite} onCancel={clearInvite} /> : raceId ? <RaceRoom key={raceId} raceId={raceId} onBack={() => setRaceId(null)} onEnter={setRaceId} /> : <Lobby onEnter={setRaceId} />}</main>
  </div>;
}
