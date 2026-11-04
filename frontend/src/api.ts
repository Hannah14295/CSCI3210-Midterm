import { z } from 'zod';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export function describeError(value: unknown): string {
  if (value instanceof Error) return value.message;
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(describeError).join(' ');
  if (value && typeof value === 'object') {
    return Object.entries(value).map(([key, message]) =>
      `${['detail', 'non_field_errors'].includes(key) ? '' : `${key}: `}${describeError(message)}`,
    ).join(' ');
  }
  return 'Something went wrong. Please try again.';
}

export async function request<T extends z.ZodType>(
  path: string, schema: T, token: string | null = null,
  options: { method?: 'GET' | 'POST'; body?: unknown; signal?: AbortSignal } = {},
): Promise<z.infer<T>> {
  let response: Response;
  try {
    response = await fetch(`/api/${path}`, {
      method: options.method || 'GET', credentials: 'omit', signal: options.signal,
      headers: {
        Accept: 'application/json',
        ...(token ? { Authorization: `Token ${token}` } : {}),
        ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(0, 'Cannot reach the backend. Check that Django is running on port 8000.');
  }
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, response.status >= 500
      ? 'The server could not finish this request. Please try again.'
      : describeError(data || `Request failed (${response.status}).`));
  }
  const parsed = schema.safeParse(data);
  if (!parsed.success) throw new ApiError(0, 'The server returned an unexpected response. Refresh and try again.');
  return parsed.data;
}
