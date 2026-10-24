import { createContext, useContext, useSyncExternalStore, type ReactNode } from 'react';
import { api } from '@/api/client';
import type { Snapshot } from '@/api/types';

const SnapshotContext = createContext<Snapshot | null>(null);

/** Subscribes the whole app to the (mock) server's published snapshots. */
export function DemoProvider({ children }: { children: ReactNode }) {
  const snapshot = useSyncExternalStore(api.subscribe, api.snapshot);
  return <SnapshotContext.Provider value={snapshot}>{children}</SnapshotContext.Provider>;
}

export function useSnapshot(): Snapshot {
  const s = useContext(SnapshotContext);
  if (!s) throw new Error('useSnapshot must be used inside <DemoProvider>');
  return s;
}
