import { motion } from 'motion/react';
import type { ApiAssessment, ApiNode } from '@/api/types';
import Counter from '@/components/bits/Counter';
import { Badge, type Tone } from '@/components/ui/StatusBadge';
import { confidencePct, fmt, geom } from '@/lib/format';
import { Explain } from '@/features/explain/Explain';
import type { FormulaId } from '@/features/explain/formulas';

const spring = { type: 'spring' as const, duration: 0.7, bounce: 0.12 };

export function verdict(a: ApiAssessment, node: ApiNode): { tone: Tone; text: string } {
  if (node.status === 'DEFAULTED') return { tone: 'defaulted', text: 'Blocked · defaulted identity' };
  const lcb = geom(a.lcb);
  const s2 = geom(a.sigma2);
  if (lcb <= 0 && s2 >= 0.99) return { tone: 'cold', text: 'Unknown, not risky' };
  if (lcb <= 0) return { tone: 'restricted', text: 'Below the lending floor' };
  if (s2 >= 0.6) return { tone: 'neel', text: 'Thin file · micro-limit' };
  return { tone: 'active', text: 'Established' };
}

/**
 * The dual-axis gauge. Primary number is Score_final (the lower confidence bound); the band
 * mu ± kappa·sqrt(sigma2) is drawn as hatching, so a thin file is visibly wide.
 */
export function ScoreGauge({ a, node, compact = false }: { a: ApiAssessment; node: ApiNode; compact?: boolean }) {
  const lcb = geom(a.lcb);
  const mu = geom(a.mu);
  const low = geom(a.bandLow);
  const high = geom(a.bandHigh);
  const lo = Math.min(-1, Math.floor(low));
  const hi = Math.max(4, Math.ceil(high + 0.25));
  const pos = (v: number) => ((v - lo) / (hi - lo)) * 100;
  const ticks = Array.from({ length: hi - lo + 1 }, (_, i) => lo + i);
  const v = verdict(a, node);
  const confidence = confidencePct(a.sigma2);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="text-[13px] text-ink-3">
            <Explain id="lcb">Score you can lend against</Explain>
          </p>
          <div className="mt-1 flex items-end gap-4">
            <Counter
              value={Number(fmt(a.lcb, 2))}
              decimals={2}
              locale="en-IN"
              fontSize={compact ? 56 : 84}
              fontWeight={600}
              textColor={lcb > 0 ? '#16181F' : '#6A6D76'}
              tabular
              motionBlur
              className="display leading-none"
              style={{ fontFamily: 'var(--font-display)', fontVariationSettings: "'wdth' 86", letterSpacing: '-0.03em' }}
            />
            <div className="mb-2.5">
              <Badge tone={v.tone}>{v.text}</Badge>
            </div>
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-[10px] border border-rule bg-rule">
          <Stat label="Expected capacity" sym="μ" id="mu" value={fmt(a.mu)} />
          <Stat label="Uncertainty" sym="σ²" id="sigma2" value={fmt(a.sigma2)} />
          <Stat label="Confidence" value={confidence} />
        </dl>
      </div>

      {/* Scale */}
      <div className="relative mt-9 h-[74px]" role="img" aria-label={`Band from ${fmt(a.bandLow)} to ${fmt(a.bandHigh)}, expected ${fmt(a.mu)}, lendable score ${fmt(a.lcb)}`}>
        <div className="absolute inset-x-0 top-[30px] h-[10px] rounded-full bg-paper-2" />
        <div className="absolute inset-y-[14px] left-0 rounded-l-full hatch-ink opacity-60" style={{ width: `${pos(0)}%` }} />
        <div className="absolute top-[6px] bottom-[18px] w-px border-l border-dashed border-ink-3" style={{ left: `${pos(0)}%` }}>
          <span className="absolute -top-[2px] left-1.5 text-[10.5px] whitespace-nowrap text-ink-3">lending floor</span>
        </div>
        <motion.div
          className="hatch absolute top-[20px] h-[30px] rounded-[6px] border border-neel-200"
          initial={false}
          animate={{ left: `${pos(low)}%`, width: `${Math.max(0.6, pos(high) - pos(low))}%` }}
          transition={spring}
        />
        <motion.div
          className="absolute top-[12px] h-[46px] w-[2px] -translate-x-1/2 rounded-full bg-ink"
          initial={false}
          animate={{ left: `${pos(mu)}%` }}
          transition={spring}
        >
          <span className="absolute -top-[18px] left-1/2 -translate-x-1/2 font-mono text-[11px] text-ink">μ</span>
        </motion.div>
        <motion.div className="absolute top-[26px] -translate-x-1/2" initial={false} animate={{ left: `${pos(lcb)}%` }} transition={spring}>
          <span className="block size-[18px] rotate-45 rounded-[3px] bg-neel-700 shadow-[0_0_0_3px_#FBFAF6]" />
        </motion.div>
        <div className="absolute inset-x-0 bottom-0 flex justify-between">
          {ticks.map((t) => (
            <span key={t} className="num w-6 text-center text-[11px] text-ink-3 first:text-left last:text-right" style={{ position: 'absolute', left: `calc(${pos(t)}% - 12px)` }}>
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-[12.5px] text-ink-2">
        <span className="inline-flex items-center gap-2">
          <span className="hatch inline-block h-3 w-6 rounded-[3px] border border-neel-200" />
          μ ± √σ²: wide means we don’t know you yet
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="inline-block size-2.5 rotate-45 rounded-[2px] bg-neel-700" />
          Lower bound = μ − √σ², what a lender can rely on
        </span>
      </div>
    </div>
  );
}

function Stat({ label, sym, id, value }: { label: string; sym?: string; id?: FormulaId; value: string }) {
  return (
    <div className="min-w-[112px] bg-surface px-4 py-3">
      <dt className="text-[11.5px] text-ink-3">
        {id ? (
          <Explain id={id}>
            {label} {sym ? <span className="font-mono">{sym}</span> : null}
          </Explain>
        ) : (
          <>
            {label} {sym ? <span className="font-mono">{sym}</span> : null}
          </>
        )}
      </dt>
      <dd className="num mt-0.5 text-[20px] font-medium tracking-tight">{value}</dd>
    </div>
  );
}
