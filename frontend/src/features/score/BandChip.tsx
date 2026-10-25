import type { ApiAssessment } from '@/api/types';
import { fmt, geom } from '@/lib/format';

/** Table-sized dual-axis readout: lendable score plus a tiny hatched band on a -1..5 scale. */
export function BandChip({ a }: { a: ApiAssessment }) {
  const lo = -1;
  const hi = 5;
  const pos = (v: number) => `${((Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo)) * 100}%`;
  const left = pos(geom(a.bandLow));
  const right = pos(geom(a.bandHigh));
  return (
    <div className="flex items-center gap-3">
      <span className={`num w-12 text-right font-mono text-[14px] font-medium ${geom(a.lcb) > 0 ? 'text-ink' : 'text-ink-3'}`}>{fmt(a.lcb)}</span>
      <span className="relative h-3 w-28 rounded-full bg-paper-2" aria-hidden>
        <span className="absolute inset-y-0 w-px bg-ink-3/60" style={{ left: pos(0) }} />
        <span className="hatch absolute inset-y-0 rounded-[3px] border border-neel-200" style={{ left, width: `calc(${right} - ${left})` }} />
        <span className="absolute -inset-y-0.5 w-[2px] rounded bg-ink" style={{ left: pos(geom(a.mu)) }} />
      </span>
    </div>
  );
}
