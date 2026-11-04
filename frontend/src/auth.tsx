import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { request } from './api';
import { authSchema, userSchema } from './types';
import type { User } from './types';

interface AuthState {
  token: string | null; user: User | null; checking: boolean;
  authenticate: (mode: 'login' | 'register', username: string, password: string) => Promise<void>;
  signOut: () => void;
}
const AuthContext = createContext<AuthState | null>(null);
const storageKey = 'typeway-token';
function storedToken() {
  try { return sessionStorage.getItem(storageKey); } catch { return null; }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(storedToken);
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(Boolean(token));
  const signOut = useCallback(() => {
    setToken(null); setUser(null); setChecking(false);
    try { sessionStorage.removeItem(storageKey); } catch { /* Memory-only session. */ }
  }, []);
  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    setChecking(true);
    request('auth/me/', userSchema, token, { signal: controller.signal })
      .then(setUser)
      .catch(() => { if (!controller.signal.aborted) signOut(); })
      .finally(() => { if (!controller.signal.aborted) setChecking(false); });
    return () => controller.abort();
  }, [token, signOut]);
  const authenticate = useCallback(async (mode: 'login' | 'register', username: string, password: string) => {
    const result = await request(`auth/${mode}/`, authSchema, null, { method: 'POST', body: { username, password } });
    try { sessionStorage.setItem(storageKey, result.token); } catch { /* Memory-only session. */ }
    setUser(result.user); setToken(result.token);
  }, []);
  const value = useMemo(() => ({ token, user, checking, authenticate, signOut }), [token, user, checking, authenticate, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth requires AuthProvider');
  return context;
}
