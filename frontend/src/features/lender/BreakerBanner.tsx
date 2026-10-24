import { useState } from 'react';
import { api } from '@/api/client';
import type { Snapshot } from '@/api/types';
import { Button } from '@/components/ui/Button';
import { IconBreaker } from '@/components/icons';

/** Shown while a cluster's circuit breaker is open: slashing paused, defaults queued for review. */
export function BreakerBanner({ s }: { s: Snapshot }) {
  const [busy, setBusy] = useState<string | null>(null);
  const tripped = s.clusters.filter((c) => c.tripped);
  if (tripped.length === 0) return null;
  return (
    <div className="space-y-3">
      {tripped.map((c) => (
        <div key={c.id} className="relative overflow-hidden rounded-[14px] border border-restricted/40 bg-restricted-tint">
          <span className="hatch-ink absolute inset-y-0 left-0 w-2 bg-restricted" />
          <div className="flex flex-wrap items-center gap-5 py-4 pr-5 pl-7">
            <span className="grid size-11 place-items-center rounded-[10px] bg-restricted text-surface">
              <IconBreaker size={22} />
            </span>
            <div className="min-w-[260px] flex-1">
              <p className="font-medium text-restricted-ink">Circuit breaker open · {c.name}</p>
              <p className="text-[13.5px] text-ink-2">
                {c.defaulted} of {c.members.length} members defaulted in one cycle, above the 30% threshold. This looks like a shared shock, not
                bad character: automated slashing is paused and {c.queued.length} slash{c.queued.length === 1 ? ' is' : 'es are'} queued ({c.queued.join(', ')}). Sponsors
                are not penalised while the review is open.
              </p>
            </div>
            <Button
              variant="secondary"
              loading={busy === c.id}
              onClick={async () => {
                setBusy(c.id);
                await api.restructure(c.id);
                setBusy(null);
              }}
            >
              Restructure and resume
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
