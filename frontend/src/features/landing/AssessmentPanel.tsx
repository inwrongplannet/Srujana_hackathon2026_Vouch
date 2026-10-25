/**
 * Hero: a lender's assessment, cycling through the three core cases in the Vouch documentation.
 * Four signals sit side by side and are never blended into one number; the bureau-only answer is
 * shown above them for contrast. Hover pauses; the case tabs are buttons.
 */
import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import Counter from '@/components/bits/Counter';
import { Badge, type Tone } from '@/components/ui/StatusBadge';
import { fmt } from '@/lib/format';
import { CASES, RING_UNCHECKED, type Case } from '@/mocks/story';

const DWELL_MS = 6000;

const affordTone: Record<Case['afford']['status'], Tone> = {
  sufficient: 'active',
  borderline: 'restricted',
  insufficient: 'defaulted',
  unknown: 'plain',
};

function Sparkline({ trail }: { trail: number[] }) {
  const W = 96;
  const H = 34;
  const lo = Math.min(...trail) - 10;
  const hi = Math.max(...trail) + 10;
  const pts = trail.map((v, i) => [(i / (trail.length - 1)) * W, H - ((v - lo) / (hi - lo)) * H] as const);
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} aria-hidden className="overflow-visible">
      <motion.polyline
        points={pts.map((p) => p.join(',')).join(' ')}
        fill="none"
        stroke="var(--color-defaulted)"
        strokeWidth={1.75}
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9, ease: 'easeOut' }}
      />
      <circle cx={pts.at(-1)![0]} cy={pts.at(-1)![1]} r={3} fill="var(--color-defaulted)" />
    </svg>
  );
}

function Cell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface p-4">
      <p className="eyebrow">{label}</p>
      <div className="mt-2">{children}</div>
    </div>
  );
}

export function AssessmentPanel() {
  const reduce = useReducedMotion();
  const [i, setI] = useState(0);
  const [paused, setPaused] = useState(false);
  const c = CASES[i]!;

  useEffect(() => {
    if (reduce || paused) return;
    const t = window.setTimeout(() => setI((n) => (n + 1) % CASES.length), DWELL_MS);
    return () => window.clearTimeout(t);
  }, [i, paused, reduce]);

  const trail = c.bureau.trail;
  const drop = trail ? trail.at(-1)! - trail.at(-4)! : 0;

  return (
    <div className="card overflow-hidden shadow-[var(--shadow-float)]" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
      <div className="grid grid-cols-3 border-b border-rule" role="tablist" aria-label="Example cases">
        {CASES.map((x, n) => (
          <button
            key={x.key}
            type="button"
            role="tab"
            aria-selected={n === i}
            onClick={() => setI(n)}
            className={`relative px-4 py-3 text-left text-[13px] transition-colors ${n === i ? 'text-ink' : 'text-ink-3 hover:text-ink-2'}`}
          >
            <span className="mr-1.5 font-mono text-[10.5px] text-neel-700">0{n + 1}</span>
            {x.tab}
            {n === i ? (
              <motion.span
                key={`${i}-${paused}`}
                className="absolute inset-x-0 bottom-0 h-[2px] origin-left bg-neel-700"
                initial={{ scaleX: reduce || paused ? 1 : 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: reduce || paused ? 0 : DWELL_MS / 1000, ease: 'linear' }}
              />
            ) : null}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={c.key} className="lg:min-h-[500px]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
          <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5">
            <p className="display text-[22px] leading-tight">{c.who}</p>
            <p className="text-[12.5px] text-ink-3">{c.what}</p>
          </div>
          <p className="mx-5 mt-3 flex items-center gap-2 rounded-[6px] border border-dashed border-rule-2 px-3 py-2 font-mono text-[11.5px] text-ink-3">
            <span className="tracking-[0.12em]">ONE-NUMBER LENDER</span>
            <span className="h-3 w-px bg-rule-2" />
            <span className={c.key === 'ring' ? 'text-restricted-ink' : 'text-defaulted'}>{c.legacy}</span>
          </p>

          <div className="mx-5 mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-[10px] border border-rule bg-rule">
            <Cell label="Bureau score">
              {trail ? (
                <div className="flex items-end justify-between gap-2">
                  <div>
                    <p className="display num text-[30px] leading-none">{trail.at(-1)}</p>
                    <p className="mt-1 font-mono text-[11px] whitespace-nowrap text-defaulted">{drop} in 3 months</p>
                  </div>
                  <Sparkline trail={trail} />
                </div>
              ) : (
                <div>
                  <p className="display text-[22px] leading-none text-ink-2">No file</p>
                  <div className="hatch mt-2 h-2.5 rounded-full" />
                </div>
              )}
            </Cell>
            <Cell label="Vouch score">
              {c.vouch.score ? (
                <div className="flex items-end gap-2">
                  <Counter
                    value={Number(fmt(c.vouch.score.toString(), 0))}
                    fontSize={30}
                    fontWeight={600}
                    textColor="#24368F"
                    tabular
                    className="display leading-none"
                    style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.02em' }}
                  />
                  <span className="mb-0.5 text-[12px] text-ink-3">/ 100</span>
                </div>
              ) : (
                <p className="display text-[20px] text-ink-2">Insufficient evidence</p>
              )}
              <p className="mt-1 text-[11.5px] text-ink-3">
                {c.vouchNote}
                {c.key === 'ring' && RING_UNCHECKED.score ? ` · ${fmt(RING_UNCHECKED.score.toString(), 0)} without ring checks` : ''}
              </p>
            </Cell>
            <Cell label="Affordability">
              <Badge tone={affordTone[c.afford.status]} className="capitalize">
                {c.afford.status}
              </Badge>
              <p className="mt-2 text-[11.5px] text-ink-3">{c.afford.note}</p>
            </Cell>
            <Cell label="Evidence">
              <div className="flex flex-wrap gap-1">
                {c.codes.map((x) => (
                  <Badge key={x.code} tone={x.tone} dot={false} className="!h-5 !px-1.5 font-mono !text-[9.5px]">
                    {x.code}
                  </Badge>
                ))}
              </div>
            </Cell>
          </div>

          <div className="px-5 pt-4 pb-5">
            <p className="text-[13.5px] leading-relaxed text-ink-2">{c.explanation}</p>
            <p className="mt-3 font-mono text-[10.5px] tracking-[0.12em] text-ink-3">SIGNALS, NOT A VERDICT · A PERSON DECIDES</p>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
