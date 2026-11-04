import { Component, StrictMode } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { AuthProvider } from './auth';
import App from './App';
import './styles.css';
import './arena.css';

class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) { /* The fallback keeps the page usable. */ }
  render() {
    if (this.state.failed) return <main><h1>The page hit a problem.</h1><p>Refresh to reconnect to your saved race.</p><button onClick={() => location.reload()}>Refresh page</button></main>;
    return this.props.children;
  }
}
createRoot(document.getElementById('root')!).render(<StrictMode><ErrorBoundary><AuthProvider><App /></AuthProvider></ErrorBoundary></StrictMode>);
