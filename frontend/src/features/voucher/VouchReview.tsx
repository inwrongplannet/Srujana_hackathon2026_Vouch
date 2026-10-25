import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { ApiVouchRequest, Snapshot, VouchPreview } from '@/api/types';
import { Modal } from '@/components/ui/Modal';
import { Avatar } from '@/components/ui/Avatar';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { Button } from '@/components/ui/Button';
import { InkDots } from '@/components/ui/InkDots';
import HoldButton from '@/components/bits/HoldButton';
import Counter from '@/components/bits/Counter';
import { IconAlert, IconArrowRight, IconCheck, IconLock, IconVouch } from '@/components/icons';
import { fmt, fmtSigned, formatMoney, geom } from '@/lib/format';
import { CapacityMeter } from './CapacityMeter';

/** Review a vouch request with the full price of saying yes, computed by the protocol. */
export function VouchReview({ s, request, onClose }: { s: Snapshot; request: ApiVouchRequest | null; onClose: () => void }) {
  const [p, setP] = useState<VouchPreview | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    setP(null);
    setShowPreview(false);
    setDone(false);
    if (!request) return;
    let alive = true;
    void api.previewVouch(request.to, request.from).then((res) => {
      if (!alive) return;
      setP(res);
      // Let the reviewer see the meter as it is, then the new segment squeezing in.
      setTimeout(() => alive && setShowPreview(true), 650);
    });
    return () => {
      alive = false;
    };
  }, [request]);

  const requester = request ? s.nodes[request.from]! : null;
  const voucher = request ? s.nodes[request.to]! : null;

  return (
    <Modal open={!!request} onClose={onClose} variant="sheet" width={600} eyebrow="Vouch request" title={requester ? `Back ${requester.name.split(' ')[0]}?` : ''}>
      {request && requester && voucher ? (
        <div className="space-y-7 p-6">
          <div className="flex gap-4">
            <Avatar node={requester} size={46} />
            <div className="min-w-0">
              <p className="flex flex-wrap items-center gap-2 font-medium">
                {requester.name} <StatusBadge node={requester} />
              </p>
              <p className="text-[13px] text-ink-3">
                {requester.role} · {requester.place}
              </p>
              <blockquote className="mt-3 border-l-2 border-neel-200 pl-3 text-[14px] text-ink-2">“{request.note}”</blockquote>
            </div>
          </div>

          {!p ? (
            <div className="flex items-center gap-2 text-[13px] text-ink-3">
              <InkDots className="text-neel-500" /> Pricing this vouch on the graph…
            </div>
          ) : (
            <>
              <section>
                <div className="flex items-baseline justify-between">
                  <p className="eyebrow">Your capacity, C = {fmt(p.capacity)}</p>
                  <p className="font-mono text-[12px] text-ink-3">
                    W = C / |Out| = {fmt(p.capacity)} / {showPreview ? p.outDegreeAfter : p.outDegreeAfter - 1}
                  </p>
                </div>
                <div className="mt-3">
                  <CapacityMeter s={s} voucherId={voucher.id} preview={showPreview ? { requesterId: requester.id, weightAfter: p.weightAfter } : null} height={60} />
                </div>
                <p className="mt-2 text-[13px] text-ink-2">
                  Adding {requester.name.split(' ')[0]} thins every vouch you’ve given from <b className="num">{p.weightBefore ? fmt(p.weightBefore) : '—'}</b> to{' '}
                  <b className="num">{fmt(p.weightAfter)}</b>. Your trust is finite, so it can’t be sold in bulk.
                </p>
              </section>

              <section className="overflow-hidden rounded-[12px] border border-rule">
                <div className="grid grid-cols-2 divide-x divide-rule">
                  <div className="p-4">
                    <p className="text-[12.5px] text-ink-3">If {requester.name.split(' ')[0]} defaults, you lose</p>
                    <p className="display num mt-1 text-[34px] leading-none text-defaulted">{fmtSigned(`-${p.penaltyIfDefault}`)}</p>
                    <p className="mt-2 font-mono text-[11.5px] text-ink-3">
                      γ·W·Δ₀ = 0.5 × {fmt(p.weightAfter)} × {fmt(p.delta0)}
                    </p>
                  </div>
                  <div className="p-4">
                    <p className="text-[12.5px] text-ink-3">If they repay, you earn</p>
                    <p className="display num mt-1 text-[34px] leading-none text-active">{fmtSigned(p.yieldIfRepaid)}</p>
                    <p className="mt-2 text-[11.5px] text-ink-3">and your locked capacity returns</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 border-t border-rule bg-paper px-4 py-2.5 text-[12.5px] text-ink-2">
                  <IconLock size={14} className="text-ink-3" /> Locked while their {formatMoney(p.principal)} loan is open · Δ₀ = principal ÷ ₹5,000
                </div>
                {p.ancestors.length ? (
                  <div className="flex items-start gap-2 border-t border-rule px-4 py-2.5 text-[12.5px] text-ink-2">
                    <IconAlert size={14} className="mt-0.5 shrink-0 text-restricted" />
                    <span>
                      Two hops up, the people who vouched for you would lose {fmt(p.ancestors[0]!.delta)} each (
                      {p.ancestors.map((a) => s.nodes[a.node]!.name.split(' ')[0]).join(', ')}). Nobody further away is touched.
                    </span>
                  </div>
                ) : null}
              </section>

              <section className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 rounded-[12px] bg-neel-50 p-4">
                <div>
                  <p className="text-[12px] text-neel-800">Their limit today</p>
                  <p className="display num text-[26px] leading-tight">{formatMoney(p.requesterBefore.limit)}</p>
                  <p className="font-mono text-[11px] text-ink-3">σ² {fmt(p.requesterBefore.sigma2)}</p>
                </div>
                <IconArrowRight size={20} className="text-neel-500" />
                <div>
                  <p className="text-[12px] text-neel-800">With your vouch</p>
                  <Counter
                    value={geom(p.requesterAfter.limit.amount)}
                    locale="en-IN"
                    format={{ style: 'currency', currency: 'INR', maximumFractionDigits: 0 }}
                    fontSize={26}
                    fontWeight={600}
                    textColor="#24368F"
                    tabular
                    style={{ fontFamily: 'var(--font-display)', fontVariationSettings: "'wdth' 90" }}
                  />
                  <p className="font-mono text-[11px] text-ink-3">R_graph {fmt(p.requesterAfter.rGraph)}</p>
                </div>
              </section>

              {p.dilution.length ? (
                <section>
                  <p className="eyebrow">Also changes</p>
                  <ul className="ruled mt-2 text-[13px]">
                    {p.dilution.map((d) => (
                      <li key={d.node} className="flex justify-between py-2">
                        <span>{s.nodes[d.node]!.name}’s graph trust</span>
                        <span className="num font-mono">
                          {fmt(d.before)} → <span className="text-restricted-ink">{fmt(d.after)}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              <div className="sticky bottom-0 -mx-6 -mb-6 flex items-center gap-3 border-t border-rule bg-surface/95 px-6 py-4 backdrop-blur">
                {done ? (
                  <p className="flex items-center gap-2 font-medium text-active">
                    <IconCheck size={18} /> Vouch cast on VouchHub
                  </p>
                ) : (
                  <>
                    <HoldButton
                      icon={<IconVouch size={18} />}
                      doneIcon={<IconCheck size={18} />}
                      doneLabel="Vouched"
                      backgroundColor="#EBE6DB"
                      fillColor="#24368F"
                      textColor="#16181F"
                      fillTextColor="#FBFAF6"
                      size="lg"
                      radius={10}
                      holdTime={1300}
                      glow={false}
                      className="flex-1"
                      onHold={async () => {
                        await api.respondVouch(request.id, true);
                        setDone(true);
                        setTimeout(onClose, 1100);
                      }}
                    >
                      Hold to vouch
                    </HoldButton>
                    <Button
                      variant="ghost"
                      size="lg"
                      onClick={async () => {
                        await api.respondVouch(request.id, false);
                        onClose();
                      }}
                    >
                      Decline
                    </Button>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      ) : null}
    </Modal>
  );
}
