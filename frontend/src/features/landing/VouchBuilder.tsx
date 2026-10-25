/**
 * "What a vouch is worth": toggle endorsers for Lakshmi and watch the Vouch Score move along its
 * saturating curve. Strong endorsers count most, a busy endorser counts less, and a ring of new
 * accounts barely moves it. Scores come from the engine; the curve is drawn from the same formula.
 */
import { useState } from 'react';
import { motion } from 'motion/react';
import { D } from '@/mocks/engine/params';
import { edgeWeight, scoreFromWeight, TAU } from '@/mocks/engine/vouch';
import { fmt, geom } from '@/lib/format';
import { DEFAULT_ENDORSERS, ENDORSERS, RING_SIZE, endorse } from '@/mocks/story';
import { IconCheck } from '@/components/icons';

const W_MAX = 4;
const CW = 420;
const CH = 200;
const CURVE = Array.from({ length: 41 }, (_, k) => {
  const w = (k / 40) * W_MAX;
  return [(w / W_MAX) * CW, CH - (geom(scoreFromWeight(D(w)).toString()) / 100) * CH] as const;
});

export function VouchBuilder() {
  const [on, setOn] = useState<string[]>(DEFAULT_ENDORSERS);
  const result = endorse(on);
  const w = geom(result.totalWeight.toString());
  const s = result.score ? geom(result.score.toString()) : 0;
  const toggle = (k: string) => setOn((xs) => (xs.includes(k) ? xs.filter((x) => x !== k) : [...xs, k]));

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_1.1fr] lg:items-start">
      <ul className="space-y-2.5">
        {ENDORSERS.map((x) => {
          const active = on.includes(x.key);
          const each = edgeWeight(x);
          return (
            <li key={x.key}>
              <button
                type="button"
                aria-pressed={active}
                onClick={() => toggle(x.key)}
                className={`flex w-full items-center gap-4 rounded-[10px] border px-4 py-3 text-left transition-colors ${active ? 'border-neel-700 bg-neel-50' : 'border-rule bg-surface hover:border-rule-2'}`}
              >
                <span className={`flex size-5 shrink-0 items-center justify-center rounded-[5px] border ${active ? 'border-neel-700 bg-neel-700 text-surface' : 'border-rule-2'}`}>
                  {active ? <IconCheck size={13} /> : null}
                </span>
                <span className="min-w-0 flex-1">
                  <span className={`block text-[14.5px] font-medium ${x.ring ? 'text-defaulted' : ''}`}>{x.name}</span>
                  <span className="block text-[12.5px] text-ink-3">{x.line}</span>
                </span>
                <span className="text-right font-mono text-[12px] text-ink-2">
                  w = {fmt(each.toString(), 2)}
                  {x.ring ? <span className="block text-[10.5px] text-ink-3">× {RING_SIZE}</span> : null}
                </span>
              </button>
            </li>
          );
        })}
        <li className="pt-2 text-[12.5px] leading-relaxed text-ink-3">
          w = reputation × reliability × e<sup>−committed</sup> × edge quality. Untick everyone: the answer is “insufficient evidence”, never 0.
        </li>
      </ul>

      <div className="card p-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Vouch score</p>
            <p className="display num mt-1 text-[56px] leading-none text-neel-700">
              {result.score ? fmt(result.score.toString(), 0) : '—'}
              <span className="ml-1 text-[18px] text-ink-3">{result.score ? '/ 100' : 'insufficient evidence'}</span>
            </p>
          </div>
          <p className="font-mono text-[12px] text-ink-2">W = {fmt(result.totalWeight.toString(), 2)}</p>
        </div>
        <svg viewBox={`-34 -10 ${CW + 44} ${CH + 44}`} className="mt-6 w-full" role="img" aria-label={`Score ${fmt(String(s), 0)} at total weight ${fmt(String(w), 2)}`}>
          {[0, 50, 100].map((v) => (
            <g key={v}>
              <line x1={0} x2={CW} y1={CH - (v / 100) * CH} y2={CH - (v / 100) * CH} stroke="var(--color-rule)" />
              <text x={-4} y={CH - (v / 100) * CH + 4} textAnchor="end" className="fill-ink-3 font-mono text-[10px]">
                {v}
              </text>
            </g>
          ))}
          <polyline points={CURVE.map((p) => p.join(',')).join(' ')} fill="none" stroke="var(--color-ink-3)" strokeWidth={1.5} strokeDasharray="4 4" />
          <motion.line
            x1={0}
            x2={0}
            y1={CH}
            animate={{ x1: (Math.min(w, W_MAX) / W_MAX) * CW, x2: (Math.min(w, W_MAX) / W_MAX) * CW, y2: CH - (s / 100) * CH }}
            stroke="var(--color-neel-300)"
          />
          <motion.circle
            r={7}
            fill="var(--color-neel-700)"
            initial={false}
            animate={{ cx: (Math.min(w, W_MAX) / W_MAX) * CW, cy: CH - (s / 100) * CH }}
            transition={{ type: 'spring', stiffness: 200, damping: 22 }}
          />
          <text x={CW} y={CH + 24} textAnchor="end" className="fill-ink-3 font-mono text-[10px]">
            total endorsement weight W → (score = 100 × (1 − e^(−W/{TAU.toString()})))
          </text>
        </svg>
        <p className="mt-4 text-[13.5px] leading-relaxed text-ink-2">
          Each extra endorsement adds less than the last. Popularity can’t buy a high score, and no score, however high, overrides affordability.
        </p>
      </div>
    </div>
  );
}
