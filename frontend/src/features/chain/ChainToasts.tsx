import { useEffect, useRef, useState } from 'react';
import { useSnapshot } from '@/state/DemoProvider';
import SwipeToast from '@/components/bits/SwipeToast';
import { IconAlert, IconBlock, IconCheck } from '@/components/icons';
import { shortHash } from '@/lib/format';
import { isAdverse } from './EventRow';
import type { ApiEvent } from '@/api/types';

/** Surfaces each newly confirmed contract event once, top right, swipe to dismiss. */
export function ChainToasts({ onOpenLedger }: { onOpenLedger: () => void }) {
  const { events } = useSnapshot();
  const seen = useRef<Set<string> | null>(null);
  const [queue, setQueue] = useState<ApiEvent[]>([]);

  useEffect(() => {
    const confirmed = events.filter((e) => e.status === 'confirmed');
    if (seen.current === null) {
      // Don't replay history on first mount.
      seen.current = new Set(confirmed.map((e) => e.id));
      return;
    }
    const fresh = confirmed.filter((e) => !seen.current!.has(e.id));
    if (fresh.length === 0) return;
    fresh.forEach((e) => seen.current!.add(e.id));
    setQueue((q) => [...fresh.reverse(), ...q].slice(0, 2));
  }, [events]);

  return (
    <div className="pointer-events-none fixed top-[76px] right-5 z-30 flex w-[360px] flex-col items-end">
      {queue.map((e) => (
        <div key={e.id} className="pointer-events-auto w-full">
          <SwipeToast
            inline
            title={`${e.contract}.${e.name}`}
            description={`${e.summary} · ${shortHash(e.tx, 6, 4)}`}
            icon={isAdverse(e) ? <IconAlert className="text-defaulted" /> : e.contract === 'LoanEscrow' ? <IconCheck className="text-active" /> : <IconBlock className="text-neel-700" />}
            actionLabel="Ledger"
            onAction={onOpenLedger}
            onClose={() => setQueue((q) => q.filter((x) => x.id !== e.id))}
            background="#FBFAF6"
            color="#16181F"
            fuseColor={isAdverse(e) ? '#A8352A' : '#3D56C2'}
            width={360}
            radius={12}
            duration={4200}
            className="text-[13px] [&_[role=status]]:border [&_[role=status]]:border-rule [&_[role=status]]:shadow-[var(--shadow-float)]"
          />
        </div>
      ))}
    </div>
  );
}
