/**
 * Is the real backend reachable? One shared probe of `GET /health`, so every screen agrees on
 * whether it shows live results or tells the presenter how to start the server.
 */
import { useSyncExternalStore } from 'react';
import { backend, type Health } from '@/api/backend';

export type BackendState =
  | { status: 'checking' }
  | { status: 'live'; health: Health }
  | { status: 'offline'; message: string };

let state: BackendState = { status: 'checking' };
const listeners = new Set<() => void>();
let inFlight: Promise<void> | null = null;

function set(next: BackendState) {
  state = next;
  listeners.forEach((l) => l());
}

/** Probe the backend again (on mount, and from the "Try again" button). */
export function checkBackend(): Promise<void> {
  if (inFlight) return inFlight;
  set({ status: 'checking' });
  inFlight = backend
    .health()
    .then((health) => set({ status: 'live', health }))
    .catch((e: unknown) => set({ status: 'offline', message: e instanceof Error ? e.message : 'Unreachable' }))
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useBackend(): BackendState {
  return useSyncExternalStore(subscribe, () => state);
}
