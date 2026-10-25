/**
 * Small shared pieces of the community screens: a person mark, verified-evidence rows, the vouch
 * score with its known/evidence split, and the list of who vouched.
 */
import { initials, fmt } from '@/lib/format';
import { IconAlert, IconCheck } from '@/components/icons';
import { Badge } from '@/components/ui/StatusBadge';
import { communityScore, trackRecord, weight, type Member, type Vouch } from '@/mocks/engine/community';
import type { Ask, Verified } from '@/mocks/community';

export function PersonMark({ name, size = 40, stranger = false }: { name: string; size?: number; stranger?: boolean }) {
  return (
    <span
      className={`grid shrink-0 place-items-center rounded-full font-medium ${stranger ? 'border border-dashed border-ink-3 bg-surface text-ink-2' : 'bg-neel-50 text-neel-800'}`}
      style={{ width: size, height: size, fontSize: size * 0.36 }}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}

export function VerifiedRow({ item, compact = false }: { item: Verified; compact?: boolean }) {
  return (
    <li className="flex gap-3">
      <span
        className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full ${
          item.tone === 'ok' ? 'bg-active-tint text-active' : item.tone === 'warn' ? 'bg-restricted-tint text-restricted-ink' : 'hatch'
        }`}
        aria-hidden
      >
        {item.tone === 'ok' ? <IconCheck size={12} /> : item.tone === 'warn' ? <IconAlert size={12} /> : null}
      </span>
      <span>
        <span className="block text-[14px] leading-snug">{item.label}</span>
        {compact ? null : <span className="block text-[12.5px] text-ink-3">{item.detail}</span>}
      </span>
    </li>
  );
}

/** The score, then how much of it came from people who know them versus evidence vouches. */
export function ScoreBlock({ ask, members }: { ask: Ask; members: Record<string, Member> }) {
  const s = communityScore(members, ask.vouches);
  const total = Number(s.total.toString()) || 1;
  const knownShare = (Number(s.known.toString()) / total) * 100;
  const capped = s.evidence.gt(s.evidenceCounted);
  return (
    <div>
      <p className="eyebrow">Vouch score</p>
      <p className="display num mt-1 text-[44px] leading-none text-neel-700">
        {s.score ? fmt(s.score.toString(), 0) : '—'}
        <span className="ml-1.5 text-[15px] text-ink-3">{s.score ? '/ 100' : 'no vouches yet'}</span>
      </p>
      {s.score ? (
        <>
          <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-paper-3" aria-hidden>
            <span className="bg-neel-700" style={{ width: `${knownShare}%` }} />
            <span className="hatch" style={{ width: `${100 - knownShare}%` }} />
          </div>
          <p className="mt-2 flex flex-wrap gap-x-4 font-mono text-[11px] text-ink-3">
            <span><span className="mr-1 inline-block size-2 rounded-[2px] bg-neel-700" />known W {fmt(s.known.toString(), 2)}</span>
            <span><span className="hatch mr-1 inline-block size-2 rounded-[2px]" />evidence W {fmt(s.evidenceCounted.toString(), 2)}{capped ? ' (capped)' : ''}</span>
          </p>
        </>
      ) : null}
    </div>
  );
}

export function VouchList({ vouches, members, setback }: { vouches: Vouch[]; members: Record<string, Member>; setback?: Ask['setback'] }) {
  if (!vouches.length) return <p className="text-[14px] text-ink-3">Nobody has vouched yet. That is not a mark against them.</p>;
  return (
    <ul className="ruled">
      {vouches.map((v) => {
        const m = members[v.voucherId]!;
        const response = setback?.responses[v.voucherId];
        return (
          <li key={`${v.voucherId}-${v.kind}`} className="flex items-center gap-3 py-3">
            <PersonMark name={m.name} size={34} stranger={v.kind === 'EVIDENCE'} />
            <div className="min-w-0 flex-1">
              <p className="text-[14px] font-medium">{m.name}</p>
              <p className="text-[12px] text-ink-3">
                {v.kind === 'KNOWN'
                  ? `${(v.relationship ?? '').toLowerCase()} · ${v.yearsKnown} years`
                  : `read the file · record ${m.repaid} of ${m.resolved} repaid`}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <Badge tone={v.kind === 'KNOWN' ? 'neel' : 'plain'} dot={false} className="font-mono !text-[10.5px]">
                {v.kind}
              </Badge>
              {response && response !== 'PENDING' ? (
                <span className={`font-mono text-[10.5px] ${response === 'STAND_BY' ? 'text-active' : 'text-ink-3'}`}>
                  {response === 'STAND_BY' ? 'stood by' : 'stepped back'}
                </span>
              ) : (
                <span className="font-mono text-[10.5px] text-ink-3">w {fmt(weight(m, v).toString(), 2)}</span>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function recordLabel(m: Member) {
  return m.resolved ? `${m.repaid} of ${m.resolved} repaid · ${fmt(trackRecord(m).mul(100).toString(), 0)}%` : 'no record yet';
}
