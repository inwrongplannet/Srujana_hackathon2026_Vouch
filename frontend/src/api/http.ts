/**
 * The HTTP door to the real backend (FastAPI, `backend/src/veritrust/api`). Paths stay relative;
 * the Vite dev proxy forwards them to VITE_API_BASE_URL (default http://localhost:8000).
 */

/** A failed call, carrying the backend's `{ "detail": ... }` message when it sent one. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * The backend gave a business answer (a 4xx such as "over the limit" or "already decided"), as
 * opposed to an outage (no answer, a timeout or a 5xx). Outages fall back to demo data; business
 * answers are shown as they are.
 */
export function isRefusal(e: unknown): e is ApiError {
  return e instanceof ApiError && e.status >= 400 && e.status < 500;
}

let outageListener: ((message: string) => void) | null = null;

/**
 * Registers the one listener told about every outage (no answer or a 5xx), so the shared backend
 * status can turn offline when a call fails after `/health` said the backend was live.
 */
export function onOutage(listener: (message: string) => void) {
  outageListener = listener;
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    // FastAPI validation errors: a list of { loc, msg }.
    if (Array.isArray(detail)) return detail.map((d) => (d as { msg?: string }).msg ?? '').filter(Boolean).join('; ') || fallback;
  }
  return fallback;
}

/** JSON request with a timeout; status 0 means the backend did not answer at all. */
export async function request<T>(method: 'GET' | 'POST', path: string, body?: unknown, timeoutMs = 10_000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch {
    const message = 'The backend did not answer. Is it running, and does VITE_API_BASE_URL point at it?';
    outageListener?.(message);
    throw new ApiError(0, message);
  } finally {
    clearTimeout(timer);
  }
  const text = await res.text();
  let parsed: unknown;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = null;   // a non-JSON error page; the status line is used instead
  }
  if (!res.ok) {
    const error = new ApiError(res.status, detailOf(parsed, `${res.status} ${res.statusText}`));
    // The dev proxy answers 5xx when the backend is down, so a 5xx counts as an outage too.
    if (res.status >= 500) outageListener?.(error.message);
    throw error;
  }
  return parsed as T;
}
