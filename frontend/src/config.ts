/** Keep local proxy URLs and the hosted Render URL in one place. */
export function resolveBackendUrl(
  configuredOrigin: string,
  path: string,
  pageOrigin: string,
): URL {
  if (!path.startsWith('/') || path.startsWith('//')) {
    throw new Error('Backend paths must start with one slash.');
  }

  const base = new URL(configuredOrigin.trim() || pageOrigin);
  if (
    !['http:', 'https:'].includes(base.protocol)
    || base.username || base.password
    || base.pathname !== '/' || base.search || base.hash
  ) {
    throw new Error('VITE_BACKEND_URL must be an HTTP(S) origin without a path or credentials.');
  }

  return new URL(path, base.origin);
}

function backendUrl(path: string): URL {
  const configured = import.meta.env.VITE_BACKEND_URL || '';
  if (import.meta.env.PROD && !configured.trim()) {
    throw new Error('The website needs VITE_BACKEND_URL set to its Render backend URL.');
  }

  const url = resolveBackendUrl(configured, path, window.location.origin);
  if (import.meta.env.PROD && url.protocol !== 'https:') {
    throw new Error('The hosted backend URL must use HTTPS.');
  }
  return url;
}

export function apiUrl(path: string): string {
  return backendUrl(`/api/${path}`).toString();
}

export function webSocketUrl(raceId: number): string {
  const url = backendUrl(`/ws/races/${raceId}/`);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  // The token itself is sent as a frame, never placed in the URL.
  url.searchParams.set('auth', 'token');
  return url.toString();
}
