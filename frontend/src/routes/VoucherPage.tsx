import { useState } from 'react';
import { useSnapshot } from '@/state/DemoProvider';
import type { ApiVouchRequest } from '@/api/types';
import { Card, CardHead } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { Badge, StatusBadge } from '@/components/ui/StatusBadge';
import { IconAnchor, IconArrowRight, IconLock, IconVouch } from '@/components/icons';
import { dayDate, fmt, fmtSigned } from '@/lib/format';
import { PersonHeader } from '@/features/shared/PersonHeader';
import { CapacityMeter } from '@/features/voucher/CapacityMeter';
import { VouchReview } from '@/features/voucher/VouchReview';

export function VoucherPage() {
  const s = useSnapshot();
  const me = s.nodes[s.voucherId]!;
  const [reviewing, setReviewing] = useState<ApiVouchRequest | null>(null);

  const pending = s.requests.filter((r) => r.to === me.id && r.status === 'PENDING');
  const out = s.edges.filter((e) => e.from === me.id);
  const sponsors = s.edges.filter((e) => e.to === me.id);
  const myEvents = s.events.filter((e) => e.deltas.some((d) => d.node === me.id));

  return (
    <div className="space-y-6">
      <PersonHeader
        node={me}
        seat="Voucher"
        aside={
          <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-[12px] border border-rule bg-rule">
            {[
              ['Credibility R', fmt(me.R)],
              ['Capacity C', fmt(me.capacity)],
              ['Backing', `${out.length} people`],
            ].map(([k, v]) => (
              <div key={k} className="min-w-[120px] bg-surface px-4 py-2.5">
                <dt className="text-[11.5px] text-ink-3">{k}</dt>
                <dd className="num text-[18px] font-medium">{v}</dd>
              </div>
            ))}
          </dl>
        }
      />

      <div className="grid gap-5 lg:grid-cols-12">
        <Card className="p-7 lg:col-span-8">
          <CardHead
            eyebrow="Out-degree conservation"
            title="Your vouch capacity"
            aside={<span className="hidden font-mono text-[12.5px] text-ink-3 sm:inline">W = C / |Out| = {fmt(me.capacity)} / {out.length || 1}</span>}
          />
          <div className="mt-6">
            <CapacityMeter s={s} voucherId={me.id} height={64} />
          </div>
          <p className="mt-4 max-w-[64ch] text-[14px] text-ink-2">
            Your credibility is a fixed budget. Every new vouch takes an equal slice from all the others, so a vouch means something
            and can’t be handed out for a bribe. Hatched slices are locked behind open loans.
          </p>
        </Card>

        <Card className="flex flex-col p-6 lg:col-span-4">
          <CardHead eyebrow="Where your credibility comes from" title="Your sponsors" />
          <ul className="ruled mt-3 flex-1">
            {sponsors.map((e) => {
              const n = s.nodes[e.from]!;
              return (
                <li key={e.from} className="flex items-center gap-3 py-2.5">
                  <Avatar node={n} size={30} />
                  <span className="flex-1 text-[13.5px]">
                    <span className="block font-medium">{n.name}</span>
                    <span className="block text-[12px] text-ink-3">{n.kind === 'anchor' ? 'Institutional anchor' : n.role}</span>
                  </span>
                  <span className="num font-mono text-[12.5px] text-ink-2">W {fmt(e.weight)}</span>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 flex items-start gap-2 text-[12.5px] text-ink-3">
            <IconAnchor size={14} className="mt-0.5 shrink-0" />
            Trust starts at institutions that lend real money. A ring of friends vouching for each other creates none.
          </p>
        </Card>

        <Card className="p-6 lg:col-span-7">
          <CardHead eyebrow="Waiting on you" title={pending.length ? `${pending.length} vouch request${pending.length > 1 ? 's' : ''}` : 'No open requests'} />
          {pending.length === 0 ? (
            <div className="mt-6 flex items-center gap-5 rounded-[12px] border border-dashed border-rule-2 p-5">
              <span className="grid size-11 place-items-center rounded-full border border-dashed border-cold text-cold">
                <IconVouch size={20} />
              </span>
              <p className="text-[13.5px] text-ink-2">When someone asks you to back them, you’ll see exactly what it would cost you before you decide.</p>
            </div>
          ) : (
            <ul className="mt-4 space-y-3">
              {pending.map((r) => {
                const n = s.nodes[r.from]!;
                return (
                  <li key={r.id} className="flex flex-wrap items-center gap-4 rounded-[12px] border border-neel-200 bg-neel-50/60 p-4">
                    <Avatar node={n} size={44} />
                    <div className="min-w-[200px] flex-1">
                      <p className="flex flex-wrap items-center gap-2 font-medium">
                        {n.name} <StatusBadge node={n} />
                      </p>
                      <p className="mt-0.5 line-clamp-2 text-[13px] text-ink-2">“{r.note}”</p>
                      <p className="mt-1 text-[12px] text-ink-3">Asked {dayDate(r.day)}</p>
                    </div>
                    <Button onClick={() => setReviewing(r)} trailingIcon={<IconArrowRight size={16} />}>
                      Review
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card className="p-6 lg:col-span-5">
          <CardHead eyebrow="People you back" title={`${out.length} vouches`} />
          <ul className="ruled mt-3">
            {out.map((e) => {
              const n = s.nodes[e.to]!;
              return (
                <li key={e.to} className="flex items-center gap-3 py-2.5">
                  <Avatar node={n} size={30} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13.5px] font-medium">{n.name}</span>
                    <span className="block text-[12px] text-ink-3">{n.role}</span>
                  </span>
                  {e.lockedLoanId ? (
                    <Badge tone="neel" dot={false}>
                      <IconLock size={12} /> {e.lockedLoanId}
                    </Badge>
                  ) : (
                    <StatusBadge node={n} />
                  )}
                </li>
              );
            })}
          </ul>
        </Card>

        {myEvents.length ? (
          <Card className="p-6 lg:col-span-12">
            <CardHead eyebrow="Skin in the game" title="What your vouches have earned and cost" />
            <ul className="ruled mt-3">
              {myEvents.map((e) => {
                const d = e.deltas.find((x) => x.node === me.id)!;
                const neg = d.delta.startsWith('-');
                return (
                  <li key={e.id} className="flex items-center justify-between gap-4 py-3 text-[13.5px]">
                    <span>
                      <span className="font-mono text-[12.5px]">
                        {e.contract}.{e.name}
                      </span>
                      <span className="ml-2 text-ink-3">{e.summary}</span>
                    </span>
                    <span className={`num font-mono font-medium ${neg ? 'text-defaulted' : 'text-active'}`}>{fmtSigned(d.delta)}</span>
                  </li>
                );
              })}
            </ul>
          </Card>
        ) : null}
      </div>

      <VouchReview s={s} request={reviewing} onClose={() => setReviewing(null)} />
    </div>
  );
}
