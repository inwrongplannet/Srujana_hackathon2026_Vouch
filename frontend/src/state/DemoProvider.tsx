import { createContext, useContext, useEffect, useSyncExternalStore, type ReactNode } from 'react';
import { api } from '@/api/client';
import type { Snapshot, StoryStep } from '@/api/types';

const SnapshotContext = createContext<Snapshot | null>(null);
// StrictMode mounts effects twice in development; the jump must run once.
let jumped = false;

/** Subscribes the whole app to the (mock) server's published snapshots. */
export function DemoProvider({ children }: { children: ReactNode }) {
  const snapshot = useSyncExternalStore(api.subscribe, api.snapshot);
  useEffect(() => {
    const jump = new URLSearchParams(window.location.search).get('jump');
    if (jump && !jumped) {
      jumped = true;
      void api.jumpTo(jump as StoryStep);
    }
  }, []);
  return <SnapshotContext.Provider value={snapshot}>{children}</SnapshotContext.Provider>;
}

export function useSnapshot(): Snapshot {
  const s = useContext(SnapshotContext);
  if (!s) throw new Error('useSnapshot must be used inside <DemoProvider>');
  return s;
}
