/** One ask in the Discover feed: who, what for, the verified summary strangers may see, and both ways to vouch. */
import { Link } from 'react-router';
import { Badge } from '@/components/ui/StatusBadge';
import { IconArrowRight } from '@/components/icons';
import { fmt } from '@/lib/format';
import { communityScore, type Member } from '@/mocks/engine/community';
import type { Ask } from '@/mocks/community';
import { PersonMark, VerifiedRow } from './parts';

export function AskCard({ ask, members, viewerId }: { ask: Ask; members: Record<string, Member>; viewerId: string }) {
  const s = communityScore(members, ask.vouches);
  const known = ask.vouches.filter((v) => v.kind === 'KNOWN').length;
  const knows = ask.knownBy.includes(viewerId);
  const shown = ask.verified.filter((x) => x.shown);
  return (
    <article className="card flex h-full flex-col p-5 transition-shadow hover:shadow-[var(--shadow-lift)]">
      <div className="flex items-start gap-3">
        <PersonMark name={ask.name} stranger={!knows} />
        <div className="min-w-0 flex-1">
          <p className="display text-[20px] leading-tight">{ask.name}</p>
          <p className="text-[12.5px] text-ink-3">
            {ask.trade} · {ask.circle}
          </p>
        </div>
        <span className="font-mono text-[11px] text-ink-3">{ask.postedDays}d</span>
      </div>
      <p className="mt-4 text-[15px] font-medium">{ask.purpose}</p>
      <p className="text-[13px] text-ink-2">{ask.amountBand}</p>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {knows ? <Badge tone="neel">In your circle</Badge> : <Badge tone="plain">Stranger to you</Badge>}
        {ask.thinFile ? <Badge tone="cold">Thin file</Badge> : null}
        {ask.setback ? <Badge tone="restricted">Setback posted</Badge> : null}
      </div>
      <ul className="mt-4 space-y-2">
        {shown.slice(0, 3).map((item) => (
          <VerifiedRow key={item.key} item={item} compact />
        ))}
      </ul>
      <div className="mt-auto flex items-end justify-between gap-3 border-t border-rule pt-4">
        <div>
          <p className="display num text-[26px] leading-none text-neel-700">{s.score ? fmt(s.score.toString(), 0) : '—'}</p>
          <p className="mt-1 text-[11.5px] text-ink-3">
            {ask.vouches.length ? `${known} known · ${ask.vouches.length - known} evidence` : 'no vouches yet'}
          </p>
        </div>
        <Link
          to={`/community/p/${ask.id}`}
          className="inline-flex items-center gap-1.5 rounded-[8px] bg-ink px-3.5 py-2 text-[13px] font-medium text-paper hover:bg-neel-950"
        >
          {knows ? 'Vouch' : 'Read the file'} <IconArrowRight size={14} />
        </Link>
      </div>
    </article>
  );
}
