import { useState } from 'react';
import { useAuth } from './auth';
import { AuthForm } from './components/AuthForm';
import { Lobby } from './components/Lobby';
import { RaceRoom } from './components/RaceRoom';
import { Leaderboard } from './components/Leaderboard';

export default function App() {
  const { user, checking, signOut } = useAuth();
  const [tab, setTab] = useState<'arena' | 'leaderboard'>('arena');
  const [raceId, setRaceId] = useState<number | null>(null);
  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header"><button className="brand" aria-label="Typeway home" onClick={() => { setTab('arena'); setRaceId(null); }}><span className="brand-icon" aria-hidden="true">↗</span>typeway<span className="brand-period">.</span></button>
      <nav aria-label="Main navigation"><button className={tab === 'arena' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('arena')}>Race arena</button><button className={tab === 'leaderboard' ? 'nav-item active' : 'nav-item'} onClick={() => setTab('leaderboard')}>Leaderboard</button></nav>
      <div className="account-area">{user ? <><span className="account-name"><span className="avatar small">{user.username.charAt(0).toUpperCase()}</span>{user.username}</span><button className="text-button muted" onClick={() => { signOut(); setRaceId(null); }}>Sign out</button></> : <span className="header-caption">A little practice. A lot of pace.</span>}</div>
    </header>
    <main id="main">{checking ? <div className="empty" role="status">Checking your account…</div> : tab === 'leaderboard' ? <Leaderboard /> : !user ? <AuthForm /> : raceId ? <RaceRoom key={raceId} raceId={raceId} onBack={() => setRaceId(null)} /> : <Lobby onEnter={setRaceId} />}</main>
    <footer><span>TYPEWAY <span className="footer-divider">/</span> BUILT FOR THE NEXT PERSONAL BEST</span><span>Accuracy first. Speed follows. ↗</span></footer>
  </div>;
}
