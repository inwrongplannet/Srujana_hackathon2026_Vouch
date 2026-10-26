/**
 * "The problem": three pain points the bureau alone cannot see, each with its figure, its stated
 * limit and what Vouch does about it (`figures.ts`). On a wide screen the section pins and the
 * reader scrolls through the three; on a phone, or with reduced motion, they stack. The visuals
 * draw only the published figure: one in three is drawn as one of three people, never as 33%.
 */
import { useRef, useState } from 'react';
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll } from 'motion/react';
import { Link } from 'react-router';
import { IconArrowRight, IconPerson } from '@/components/icons';
import { GAP, PAINS } from './figures';
import { SourceLink } from './Evidence';

type Pain = (typeof PAINS)[number];
const EASE = [0.22, 1, 0.36, 1] as const;

/* ------------------------------------------------------------------ visuals */

/** 100 people; the ones without a numerical score are drawn in the hatching that means "unknown". */
function NoFile({ n }: { n: number }) {
  const reduce = useReducedMotion();
  return (
    <div>
      <div className="grid max-w-[380px] grid-cols-10 gap-1.5" role="img" aria-label={`${n} of 100 people had no numerical score`}>
        {Array.from({ length: 100 }, (_, i) => {
          const blank = i >= 100 - n;
          return (
            <motion.span
              key={i}
              className={`aspect-square rounded-full ${blank ? 'hatch border border-neel-300' : 'bg-neel-700'}`}
              initial={reduce ? false : { opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: reduce ? 0 : blank ? 0.6 + (i - (100 - n)) * 0.03 : i * 0.004 }}
            />
          );
        })}
      </div>
      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[11px] text-ink-3">
        <span className="inline-flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-neel-700" /> scored
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="hatch size-2.5 rounded-full border border-neel-300" /> no numerical score: unknown, not bad
        </span>
      </div>
    </div>
  );
}

/**
 * A CIBIL report's payment history: 36 months of days past due, 35 on time ("000") and one month
 * 30 days late after a hospital bill ("030"). Then the score: the starting value is illustrative,
 * the 50-80 point fall is the lender's published estimate, drawn as a range.
 */
const START_SCORE = 782;

function ScoreCrash({ maxDrop }: { maxDrop: number }) {
  const reduce = useReducedMotion();
  const minDrop = 50;
  const months = Array.from({ length: 36 }, (_, i) => i);
  const t = (i: number) => (reduce ? 0 : 0.05 + i * 0.045);
  return (
    <div className="max-w-[470px]">
      <p className="eyebrow">Payment history on a CIBIL report · last 36 months</p>
      <div className="mt-3 grid grid-cols-12 gap-1" role="img" aria-label="35 months paid on time, then one month 30 days late">
        {months.map((i) => {
          const late = i === 35;
          return (
            <motion.span
              key={i}
              className={`grid h-8 place-items-center rounded-[4px] font-mono text-[10.5px] ${late ? 'bg-defaulted text-paper' : 'bg-neel-50 text-neel-700'}`}
              initial={reduce ? false : { opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: late ? t(i) + 0.4 : t(i) }}
            >
              {late ? '030' : '000'}
            </motion.span>
          );
        })}
      </div>
      <div className="mt-2 flex justify-between font-mono text-[11px] text-ink-3">
        <span>35 months on time</span>
        <motion.span className="text-defaulted" initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: t(36) + 0.4 }}>
          hospital bill → 30 days late
        </motion.span>
      </div>

      <motion.div
        className="mt-6 rounded-[10px] border border-rule bg-surface p-4"
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: t(36) + 0.8 }}
      >
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="eyebrow">CIBIL Score</p>
            <p className="display num mt-1 text-[34px] leading-none">
              {START_SCORE}
              <span className="mx-2 text-ink-3">→</span>
              <span className="text-defaulted">
                {START_SCORE - maxDrop}–{START_SCORE - minDrop}
              </span>
            </p>
          </div>
          <p className="num font-mono text-[13px] text-defaulted">
            −{minDrop} to −{maxDrop}
          </p>
        </div>
        <div className="relative mt-4 h-2.5 rounded-full bg-paper-2" aria-hidden>
          {/* 300-900 scale: where the score was, and the range it falls into */}
          <span className="absolute inset-y-0 w-[2px] bg-ink" style={{ left: `${((START_SCORE - 300) / 600) * 100}%` }} />
          <motion.span
            className="absolute inset-y-0 rounded-full bg-defaulted/60"
            style={{ left: `${((START_SCORE - maxDrop - 300) / 600) * 100}%`, width: `${((maxDrop - minDrop) / 600) * 100}%` }}
            initial={reduce ? false : { scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ delay: t(36) + 1.1, duration: 0.5 }}
          />
        </div>
        <div className="mt-1.5 flex justify-between font-mono text-[10.5px] text-ink-3">
          <span>300</span>
          <span>900</span>
        </div>
        <p className="mt-3 text-[12.5px] text-ink-3">
          The starting score is illustrative; the fall is the lender’s estimate for one payment 30 days late. Thirty-five good months stay on the report, but
          the score moves on the one.
        </p>
      </motion.div>
    </div>
  );
}

/** How many never checked, how many were turned down without a reason, and what a reason looks like. */
function NoReason({ share }: { share: number }) {
  const reduce = useReducedMotion();
  return (
    <div className="max-w-[460px] space-y-6">
      <div>
        <div className="flex justify-between text-[12.5px] text-ink-2">
          <span>Never checked their credit score</span>
          <span className="num font-mono text-ink">{share}%</span>
        </div>
        <div className="mt-1.5 h-3 overflow-hidden rounded-r-[4px] bg-paper-2">
          <motion.div className="h-full rounded-r-[4px] bg-neel-700" initial={reduce ? false : { width: 0 }} animate={{ width: `${share}%` }} transition={{ duration: 0.9, ease: EASE }} />
        </div>
      </div>
      <div>
        <p className="text-[12.5px] text-ink-2">About one in three: rejected for a poor or missing history, often with no reason given</p>
        <div className="mt-2 flex gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className={`grid size-12 place-items-center rounded-full ${i === 0 ? 'bg-defaulted-tint text-defaulted' : 'bg-paper-2 text-ink-3'}`}
              initial={reduce ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.12 }}
            >
              <IconPerson size={22} />
            </motion.span>
          ))}
        </div>
      </div>
      <motion.div
        className="rounded-[10px] border border-rule bg-surface p-4"
        initial={reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <p className="eyebrow">A reason, as Vouch gives it</p>
        <p className="mt-2 text-[13.5px] text-ink">
          The requested EMI of ₹14,184 is above the ₹8,945 a month Lakshmi can afford. Over 24 months it fits.
        </p>
        <Link to="/app/assess" className="mt-2 inline-flex items-center gap-1 text-[12.5px] text-neel-700 hover:underline">
          See it on the Assessment desk <IconArrowRight size={13} />
        </Link>
      </motion.div>
    </div>
  );
}

function Visual({ p }: { p: Pain }) {
  if (p.key === 'no-file') return <NoFile n={p.draw} />;
  if (p.key === 'setback') return <ScoreCrash maxDrop={p.draw} />;
  return <NoReason share={p.draw} />;
}

/* ------------------------------------------------------------------ text */

function Copy({ p, n }: { p: Pain; n: number }) {
  return (
    <div>
      <p className="font-mono text-[11.5px] tracking-[0.12em] text-ink-3">
        0{n + 1} / 0{PAINS.length}
      </p>
      <h3 className="display mt-3 text-[clamp(26px,2.8vw,38px)] leading-[1.05]">{p.title}</h3>
      <p className="display num mt-5 text-[clamp(56px,7vw,96px)] leading-[0.9] tracking-[-0.03em] text-neel-700">{p.figure}</p>
      <p className="mt-3 max-w-[46ch] text-[16px] leading-snug text-ink">{p.line}</p>
      {p.key === 'no-file' ? (
        <p className="mt-3 max-w-[50ch] text-[13.5px] text-ink-2">
          Across India: <span className="font-medium text-ink">{GAP.value}</span> {GAP.line}{' '}
          <SourceLink source={GAP.source} className="mt-1" />
        </p>
      ) : null}
      {'context' in p ? (
        <p className="mt-3 max-w-[50ch] text-[13.5px] text-ink-2">
          <span className="font-medium text-ink">{p.context.value}</span> {p.context.line}{' '}
          <SourceLink source={p.context.source} className="mt-1" />
        </p>
      ) : null}
      <div className="mt-5 max-w-[50ch] border-l-2 border-neel-700 pl-4">
        <p className="eyebrow">What Vouch does</p>
        <p className="mt-1 text-[14.5px] leading-relaxed text-ink">{p.vouch}</p>
      </div>
      <p className="mt-4 max-w-[54ch] text-[12px] leading-relaxed text-ink-3">{p.caveat}</p>
      <SourceLink source={p.source} className="mt-2" />
    </div>
  );
}

/* ------------------------------------------------------------------ section */

/** Wide screens: the section pins while the reader scrolls through the three pain points. */
function Pinned() {
  const track = useRef<HTMLDivElement>(null);
  const [step, setStep] = useState(0);
  const { scrollYProgress } = useScroll({ target: track, offset: ['start start', 'end end'] });
  useMotionValueEvent(scrollYProgress, 'change', (v) => setStep(Math.min(PAINS.length - 1, Math.max(0, Math.floor(v * PAINS.length)))));

  const jump = (i: number) => {
    const el = track.current;
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY;
    const range = el.offsetHeight - window.innerHeight;
    window.scrollTo({ top: top + (range * (i + 0.5)) / PAINS.length, behavior: 'smooth' });
  };
  const p = PAINS[step]!;

  return (
    <div ref={track} className="relative mt-10" style={{ height: `${PAINS.length * 100}vh` }}>
      <div className="sticky top-16 flex h-[calc(100dvh-4rem)] items-center">
        <div className="grid w-full grid-cols-[auto_1fr_1fr] items-center gap-12">
          <ol className="flex flex-col gap-3" aria-label="Pain points">
            {PAINS.map((x, i) => (
              <li key={x.key}>
                <button
                  type="button"
                  onClick={() => jump(i)}
                  aria-current={i === step ? 'step' : undefined}
                  aria-label={`${i + 1}: ${x.title}`}
                  className={`block h-10 w-1.5 rounded-full transition-colors ${i === step ? 'bg-neel-700' : 'bg-rule-2 hover:bg-ink-3'}`}
                />
              </li>
            ))}
          </ol>
          <AnimatePresence mode="wait">
            <motion.div key={p.key} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.35, ease: EASE }}>
              <Copy p={p} n={step} />
            </motion.div>
          </AnimatePresence>
          <AnimatePresence mode="wait">
            <motion.div key={p.key} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
              <Visual p={p} />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

/** Phones and reduced motion: the three pain points, one after another. */
function Stacked() {
  const reduce = useReducedMotion();
  return (
    <div className="mt-12 space-y-20">
      {PAINS.map((p, i) => (
        <motion.div
          key={p.key}
          className="grid gap-10 lg:grid-cols-2 lg:items-center"
          initial={reduce ? false : { opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '0px 0px -15% 0px' }}
          transition={{ duration: 0.6, ease: EASE }}
        >
          <Copy p={p} n={i} />
          <Visual p={p} />
        </motion.div>
      ))}
    </div>
  );
}

export function Problem() {
  const reduce = useReducedMotion();
  return (
    <>
      {reduce ? null : (
        <div className="hidden lg:block">
          <Pinned />
        </div>
      )}
      <div className={reduce ? '' : 'lg:hidden'}>
        <Stacked />
      </div>
    </>
  );
}
