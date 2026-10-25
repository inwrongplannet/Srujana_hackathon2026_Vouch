/**
 * Chapter 6: we try to break the loan before it breaks her. The reader drags an income fall; each
 * candidate plan shows the fall at which it stops fitting (its tipping point) on a shared ruler.
 */
import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { D } from '@/mocks/engine/params';
import { formatMoney, geom, inr, pct } from '@/lib/format';
import { INCOME, LAKSHMI, stress } from '@/mocks/story';
import { Badge } from '@/components/ui/StatusBadge';
import { Reveal } from './Story';

const MAX_FALL = 30;

export function BreakTheLoan() {
  const worst = Math.round(geom(INCOME.worstFall) * 100);
  // Opens on her own worst month, where the loan she asked for already breaks.
  const [fall, setFall] = useState(worst);
  const { results, pick } = useMemo(() => stress(D(fall).div(100)), [fall]);
  const holding = results.filter((r) => r.fits).length;
  const at = (v: number) => `${(Math.min(v, MAX_FALL) / MAX_FALL) * 100}%`;

  return (
    <div>
      <Reveal>
        <div className="card p-6 sm:p-8">
          <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
            <div>
              <label htmlFor="fall" className="eyebrow">
                Her income falls by
              </label>
              <p className="display num mt-1 text-[clamp(44px,5vw,64px)] leading-none">{fall}%</p>
            </div>
            <p className="max-w-[40ch] text-[15px] text-ink-2 md:text-right">
              {fall === worst ? (
                <span className="text-restricted-ink">This is her own worst month so far. </span>
              ) : null}
              {holding} of {results.length} plans still fit. {pick ? null : <span className="font-medium text-defaulted">No tested plan fits at this fall.</span>}
            </p>
          </div>

          <div className="relative mt-6">
            <input
              id="fall"
              type="range"
              min={0}
              max={MAX_FALL}
              step={1}
              value={fall}
              onChange={(e) => setFall(Number(e.target.value))}
              className="vt-range w-full"
              style={{ ['--fill' as string]: at(fall) }}
              aria-valuetext={`${fall}% income fall`}
            />
            <button
              type="button"
              onClick={() => setFall(worst)}
              className="absolute top-6 -translate-x-1/2 font-mono text-[10.5px] whitespace-nowrap text-restricted-ink hover:underline"
              style={{ left: at(worst) }}
            >
              <svg width="8" height="6" viewBox="0 0 8 6" className="mr-1 inline fill-current align-[1px]" aria-hidden>
                <path d="M4 0 8 6H0z" />
              </svg>
              her worst month, −{worst}%
            </button>
          </div>

          <div className="mt-12 overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-[14px]">
              <thead>
                <tr className="border-b border-ink font-mono text-[11px] tracking-[0.08em] text-ink-3">
                  <th className="py-2 font-normal">PLAN</th>
                  <th className="py-2 text-right font-normal">EMI</th>
                  <th className="py-2 text-right font-normal">INTEREST</th>
                  <th className="py-2 text-right font-normal">LEFT THIS MONTH</th>
                  <th className="w-[34%] py-2 pl-8 font-normal">FITS UNTIL INCOME FALLS</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => {
                  const asked = r.plan.principal.eq(LAKSHMI.ask.principal) && r.plan.months === LAKSHMI.ask.months;
                  const breaks = geom(r.breaksAt.toString()) * 100;
                  return (
                    <tr key={`${r.plan.principal}-${r.plan.months}`} className={`border-b border-rule ${pick === r ? 'bg-active-tint/50' : ''}`}>
                      <td className="py-4 pr-4">
                        <p className="num font-medium">
                          {formatMoney(inr(r.plan.principal.toString()))} · {r.plan.months} months
                        </p>
                        <p className="mt-0.5 text-[12px] text-ink-3">{asked ? 'what she asked for' : pick === r ? 'the plan we would offer' : ' '}</p>
                      </td>
                      <td className="num py-4 text-right font-mono">{formatMoney(inr(r.emi.toString()))}</td>
                      <td className="num py-4 text-right font-mono text-ink-2">{formatMoney(inr(r.totalInterest.toString()))}</td>
                      <td className={`num py-4 text-right font-mono ${r.leftover.isNegative() ? 'text-defaulted' : ''}`}>
                        {r.leftover.isNegative() ? '−' : ''}
                        {formatMoney(inr(r.leftover.abs().toString()))}
                      </td>
                      <td className="py-4 pl-8">
                        <div className="flex items-center gap-3">
                          <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-defaulted-tint">
                            <motion.div
                              className="absolute inset-y-0 left-0 bg-active"
                              initial={false}
                              animate={{ width: at(breaks) }}
                            />
                            <div className="absolute inset-y-[-3px] w-[2px] bg-ink" style={{ left: at(fall) }} />
                          </div>
                          <Badge tone={r.fits ? 'active' : 'defaulted'} className="w-[72px] justify-center">
                            {pct(r.breaksAt.toString(), 1)}
                          </Badge>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-5 text-[12.5px] leading-relaxed text-ink-3">
            Fits = money left after essentials and EMIs stays above zero, and EMIs stay under half her income. 24% a year, demo pricing.
          </p>
        </div>
      </Reveal>
    </div>
  );
}
