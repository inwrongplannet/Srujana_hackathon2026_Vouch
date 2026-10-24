import type { ApiEvent, Snapshot } from '@/api/types';
import StatusMark from '@/components/bits/StatusMark';
import { dayDate, fmtSigned, shortHash } from '@/lib/format';

const contractTone: Record<ApiEvent['contract'], string> = {
  IdentityRegistry: 'text-ink-2 bg-paper-2',
  VouchHub: 'text-neel-800 bg-neel-50',
  LoanEscrow: 'text-active bg-active-tint',
  CircuitBreaker: 'text-restricted-ink bg-restricted-tint',
};

export function isAdverse(e: ApiEvent): boolean {
  return ['Slashed', 'Defaulted', 'Tripped', 'DuplicateRejected'].includes(e.name);
}

/** One contract event: status mark morphs from pending to confirmed as the block lands. */
export function EventRow({ event, snapshot, compact = false }: { event: ApiEvent; snapshot: Snapshot; compact?: boolean }) {
  const adverse = isAdverse(event);
  return (
    <div className="grid grid-cols-[22px_1fr] gap-3 py-3.5">
      <div className="pt-0.5">
        <StatusMark
          status={event.status === 'pending' ? 'running' : adverse ? 'failed' : 'done'}
          size={18}
          strokeWidth={1.8}
          color="#3D56C2"
          doneColor="#2E7A4D"
          errorColor="#A8352A"
        />
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-[4px] px-1.5 py-0.5 font-mono text-[10.5px] tracking-wide ${contractTone[event.contract]}`}>{event.contract}</span>
          <span className="font-mono text-[13px] font-medium text-ink">{event.name}</span>
          <span className="ml-auto text-[11.5px] text-ink-3">{event.status === 'pending' ? 'confirming…' : `${dayDate(event.day)}`}</span>
        </div>
        <p className="mt-1 text-[13px] leading-snug text-ink-2">{event.summary}</p>
        {!compact && event.deltas.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {event.deltas.map((d) => (
              <span
                key={d.node}
                className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11.5px] num ${
                  d.delta.startsWith('-') ? 'border-defaulted/25 text-defaulted' : 'border-active/25 text-active'
                }`}
              >
                {snapshot.nodes[d.node]?.name.split(' ')[0] ?? d.node}
                {d.k !== undefined ? <span className="text-ink-3">k{d.k}</span> : null}
                <b className="font-medium">{fmtSigned(d.delta)}</b>
              </span>
            ))}
          </div>
        ) : null}
        <p className="mt-1.5 font-mono text-[11px] text-ink-3">
          {shortHash(event.tx, 8, 6)} · block {event.block.toLocaleString('en-IN')}
        </p>
      </div>
    </div>
  );
}
