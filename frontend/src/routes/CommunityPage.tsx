import { useState } from 'react';
import RubberSegment from '@/components/bits/RubberSegment';
import { AskCard } from '@/features/community/AskCard';
import { VIEWER_ID } from '@/mocks/community';
import { useCommunity } from '@/state/communityStore';

const FILTERS = [
  { value: 'all', label: 'Everyone' },
  { value: 'circle', label: 'In my circles' },
  { value: 'thin', label: 'Thin file' },
  { value: 'setback', label: 'After a setback' },
] as const;

export function CommunityPage() {
  const { asks, members } = useCommunity();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]['value']>('all');
  const others = asks.filter((a) => a.ownerId !== VIEWER_ID);
  const matches = (f: typeof filter) => (a: (typeof asks)[number]) =>
    f === 'circle' ? a.knownBy.includes(VIEWER_ID) : f === 'thin' ? a.thinFile : f === 'setback' ? !!a.setback : true;
  const shown = others
    .filter(matches(filter))
    // Strongest verified evidence first; never by how urgent or needy a post sounds.
    .sort((a, b) => b.verified.filter((x) => x.shown && x.tone === 'ok').length - a.verified.filter((x) => x.shown && x.tone === 'ok').length);

  return (
    <div>
      <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr] lg:items-end">
        <div>
          <p className="font-mono text-[11.5px] tracking-[0.16em] text-neel-700">DISCOVER</p>
          <h1 className="display mt-2 text-[clamp(32px,4vw,48px)] leading-[1.02]">People asking for a vouch</h1>
        </div>
        <p className="max-w-[52ch] text-[15px] leading-relaxed text-ink-2">
          Vouch for someone you know, or for a stranger whose verified file convinces you. Either way you stake your own reputation, never
          money, and you earn the most for backing people others overlook.
        </p>
      </div>
      <div className="-mx-4 mt-8 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0">
        <RubberSegment
          value={filter}
          onChange={(v) => setFilter(v as typeof filter)}
          items={FILTERS.map((f) => ({
            value: f.value,
            label: (
              <span className="flex items-baseline gap-1.5 whitespace-nowrap">
                {f.label}
                <span className="num text-[11.5px] opacity-60">{others.filter(matches(f.value)).length}</span>
              </span>
            ),
          }))}
          trackColor="#E3DDCF"
          thumbColor="#FBFAF6"
          textColor="#464955"
          activeTextColor="#16181F"
          radius={10}
          equalSlots={false}
          className="w-max"
          aria-label="Filter asks"
        />
      </div>
      <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {shown.map((ask) => (
          <AskCard key={ask.id} ask={ask} members={members} viewerId={VIEWER_ID} />
        ))}
      </div>
      {!shown.length ? <p className="mt-10 text-[15px] text-ink-3">No asks match this filter.</p> : null}
    </div>
  );
}
