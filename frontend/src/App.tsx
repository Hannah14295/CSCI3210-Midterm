import { useState } from 'react';
import { useAuth } from './auth';
import { AuthForm } from './components/AuthForm';
import { Lobby } from './components/Lobby';
import { RaceRoom } from './components/RaceRoom';
import { Leaderboard } from './components/Leaderboard';

export default function App() {
  const { user, checking } = useAuth();
  const [tab, setTab] = useState<'arena' | 'leaderboard'>('arena');
  const [raceId, setRaceId] = useState<number | null>(null);
  return <div className="app-shell">
    <header className="site-header"><button className="brand" aria-label="TypeRacer home" onClick={() => { setTab('arena'); setRaceId(null); }}>TypeRacer</button>
      <nav aria-label="Main navigation"><button className={tab === 'arena' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('arena')}>Race arena</button><button className={tab === 'leaderboard' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('leaderboard')}>Leaderboard</button></nav>
    </header>
    <main id="main">{checking ? <div className="empty" role="status">Checking your account…</div> : tab === 'leaderboard' ? <Leaderboard /> : !user ? <AuthForm /> : raceId ? <RaceRoom key={raceId} raceId={raceId} onBack={() => setRaceId(null)} /> : <Lobby onEnter={setRaceId} />}</main>
  </div>;
}
