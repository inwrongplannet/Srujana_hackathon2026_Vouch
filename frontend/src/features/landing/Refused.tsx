/**
 * Chapter 3: she is not rare. 100 squares for 100 people a bureau-only rule refused for having no
 * file, filled in as they repaid or defaulted. Figures from our dataset build, not about any one person.
 */
import { motion, useReducedMotion } from 'motion/react';
import { pct } from '@/lib/format';
import { DATASET, REPAID_OF_100 } from '@/mocks/story';
import { Reveal } from './Story';

const count = new Intl.NumberFormat('en-IN');

export function Refused() {
  const reduce = useReducedMotion();
  return (
    <div className="mt-12 grid gap-12 lg:grid-cols-[0.9fr_1fr] lg:items-center">
      <Reveal>
        <div
          className="grid max-w-[380px] grid-cols-10 gap-1.5 sm:gap-2"
          role="img"
          aria-label={`${REPAID_OF_100} of 100 refused applicants repaid; ${100 - REPAID_OF_100} defaulted`}
        >
          {Array.from({ length: 100 }, (_, i) => {
            const repaid = i < REPAID_OF_100;
            return (
              <motion.div
                key={i}
                className={`aspect-square rounded-[3px] ${repaid ? 'bg-neel-700' : 'border-[1.5px] border-defaulted bg-defaulted-tint'}`}
                initial={reduce ? false : { opacity: 0, scale: 0.4 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true, margin: '0px 0px -15% 0px' }}
                transition={{ duration: 0.35, delay: 0.2 + i * 0.012, ease: [0.22, 1, 0.36, 1] }}
              />
            );
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-x-6 gap-y-1 font-mono text-[11px] text-ink-3">
          <span className="inline-flex items-center gap-2"><span className="size-2.5 rounded-[2px] bg-neel-700" />repaid</span>
          <span className="inline-flex items-center gap-2"><span className="size-2.5 rounded-[2px] border border-defaulted bg-defaulted-tint" />defaulted</span>
        </div>
      </Reveal>

      <div>
        <Reveal>
          <p className="display text-[clamp(64px,9vw,128px)] leading-[0.85] tracking-[-0.04em] text-neel-700">
            {REPAID_OF_100}
            <span className="text-ink-3"> / 100</span>
          </p>
          <p className="mt-5 max-w-[42ch] text-[19px] leading-snug text-ink">
            of the people turned away for having no credit file would have paid the loan back.
          </p>
        </Reveal>
        <Reveal delay={0.1}>
          <div className="mt-10 space-y-4 border-t border-rule pt-6 text-[15.5px] leading-relaxed text-ink-2">
            <p>
              A bureau-only rule, replayed on {count.format(DATASET.applicants)} real applicants, refused{' '}
              <span className="num font-medium text-ink">{count.format(DATASET.refusedNoFile)}</span> for having no file. They defaulted at{' '}
              <span className="num font-medium text-ink">{pct(DATASET.defaultNoFile, 1)}</span> against{' '}
              <span className="num font-medium text-ink">{pct(DATASET.defaultWithFile, 1)}</span> for everyone else.
            </p>
            <p className="display text-[24px] leading-tight text-ink">A little riskier. Refused as if certain.</p>
          </div>
          <p className="mt-6 max-w-[60ch] text-[12px] leading-relaxed text-ink-3">Source: {DATASET.source}</p>
        </Reveal>
      </div>
    </div>
  );
}
