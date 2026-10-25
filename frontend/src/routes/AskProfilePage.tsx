import { Link, Navigate, useParams } from 'react-router';
import { IconArrowLeft } from '@/components/icons';
import { Badge } from '@/components/ui/StatusBadge';
import { PersonMark, ScoreBlock, VerifiedRow, VouchList } from '@/features/community/parts';
import { SetbackCard } from '@/features/community/SetbackCard';
import { VouchComposer } from '@/features/community/VouchComposer';
import { VIEWER_ID } from '@/mocks/community';
import { communityScore } from '@/mocks/engine/community';
import { fmt } from '@/lib/format';
import { useCommunity } from '@/state/communityStore';

function Trail({ trail }: { trail: number[] }) {
  const lo = Math.min(...trail) - 10;
  const hi = Math.max(...trail) + 10;
  const pts = trail.map((v, i) => `${(i / (trail.length - 1)) * 200},${48 - ((v - lo) / (hi - lo)) * 48}`).join(' ');
  const falling = trail.at(-1)! < trail[0]!;
  return (
    <div className="flex items-end gap-4">
      <svg width={200} height={48} viewBox="0 0 200 48" aria-hidden className="overflow-visible">
        <polyline points={pts} fill="none" stroke={falling ? 'var(--color-defaulted)' : 'var(--color-active)'} strokeWidth={1.75} />
      </svg>
      <p className="font-mono text-[12px] text-ink-3">
        {trail[0]} → {trail.at(-1)} over {trail.length} months (illustrative)
      </p>
    </div>
  );
}

export function AskProfilePage() {
  const { id } = useParams();
  const { asks, members } = useCommunity();
  const ask = asks.find((a) => a.id === id);
  if (!ask) return <Navigate to="/community" replace />;
  const knows = ask.knownBy.includes(VIEWER_ID);
  const shown = ask.verified.filter((x) => x.shown);
  const hidden = ask.verified.length - shown.length;
  const s = communityScore(members, ask.vouches);
  const known = ask.vouches.filter((v) => v.kind === 'KNOWN').length;
  const stood = ask.setback ? Object.values(ask.setback.responses).filter((r) => r === 'STAND_BY').length : 0;

  return (
    <div>
      <Link to="/community" className="inline-flex items-center gap-1.5 text-[13px] text-ink-3 hover:text-ink">
        <IconArrowLeft size={14} /> Discover
      </Link>
      <div className="mt-6 grid gap-8 lg:grid-cols-[1.25fr_1fr] lg:items-start">
        <div className="space-y-6">
          <div className="flex items-start gap-4">
            <PersonMark name={ask.name} size={56} stranger={!knows} />
            <div>
              <h1 className="display text-[34px] leading-tight">{ask.name}</h1>
              <p className="text-[14px] text-ink-3">
                {ask.trade} · {ask.place} · {ask.circle}
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {knows ? <Badge tone="neel">In your circle</Badge> : <Badge tone="plain">Stranger to you</Badge>}
                {ask.thinFile ? <Badge tone="cold">Thin file</Badge> : null}
              </div>
            </div>
          </div>

          <div className="card p-6">
            <p className="eyebrow">Asking for</p>
            <p className="display mt-1 text-[24px]">{ask.purpose}</p>
            <p className="text-[14px] text-ink-2">{ask.amountBand}</p>
            <p className="mt-4 border-l-2 border-rule-2 pl-4 text-[15px] leading-relaxed text-ink-2">“{ask.story}”</p>
            <p className="mt-2 text-[12px] text-ink-3">In their words; not verified.</p>
          </div>

          <div className="card p-6">
            <div className="flex items-baseline justify-between gap-3">
              <p className="eyebrow">Verified by the platform</p>
              <p className="text-[12px] text-ink-3">shown with consent{hidden ? ` · ${hidden} kept private` : ''}</p>
            </div>
            {shown.length ? (
              <ul className="mt-4 space-y-3">
                {shown.map((item) => (
                  <VerifiedRow key={item.key} item={item} />
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-[14px] text-ink-3">Nothing shared with strangers yet.</p>
            )}
            {ask.bureau.trail ? (
              <div className="mt-5 border-t border-rule pt-4">
                <p className="mb-2 text-[12.5px] text-ink-3">Bureau score</p>
                <Trail trail={ask.bureau.trail} />
              </div>
            ) : null}
            <p className="mt-5 text-[12px] text-ink-3">Summaries only. Strangers never see statements, transactions or exact income.</p>
          </div>

          <SetbackCard ask={ask} viewerId={VIEWER_ID} />
        </div>

        <aside className="space-y-5 lg:sticky lg:top-24">
          <div className="card p-6">
            <ScoreBlock ask={ask} members={members} />
            <div className="mt-6 border-t border-rule pt-6">
              <VouchComposer key={ask.id} ask={ask} viewerId={VIEWER_ID} />
            </div>
          </div>
          <div className="card p-6">
            <p className="eyebrow">Who vouched</p>
            <div className="mt-2">
              <VouchList vouches={ask.vouches} members={members} setback={ask.setback} />
            </div>
          </div>
          <div className="rounded-[10px] border border-dashed border-rule-2 p-5">
            <p className="font-mono text-[11px] tracking-[0.12em] text-ink-3">WHAT A LENDER SEES</p>
            <p className="mt-2 text-[14px] leading-relaxed text-ink-2">
              Vouch {s.score ? fmt(s.score.toString(), 0) : 'none yet'}: {known} known, {ask.vouches.length - known} evidence
              {ask.setback ? `; ${stood} of ${Object.keys(ask.setback.responses).length} stood by after the setback` : ''}. Shown beside the bureau
              score and affordability, never blended into them. No posts, names or chats.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
