/**
 * How Vouch works in four steps (frontend/Vouch_How_It_Works_Page.md): borrower and trusted peers,
 * then Vouch's assessment, then the lender's view with three separate signals. The steps play in
 * turn once the diagram is in view; clicking a step stops on it. Labels name what the prototype
 * really does: ring and credibility checks, the affordability engine, the desk's separate signals.
 */
import { useEffect, useRef, useState } from 'react';
import { motion, useInView, useReducedMotion } from 'motion/react';
import { IconArrowRight, IconPerson, IconShield, IconStatement } from '@/components/icons';

const STEPS = [
  { n: '01', title: 'A borrower applies', line: 'The borrower asks for a loan and, with consent, shares the financial evidence they have.' },
  {
    n: '02',
    title: 'People vouch for them',
    line: 'People who know the borrower put their own reputation behind them. Credibility counts for more than the number of endorsements.',
  },
  {
    n: '03',
    title: 'Vouch checks the evidence',
    line: 'Endorsements are checked for credibility and manipulation. Financial evidence and existing obligations are assessed separately, for affordability.',
  },
  {
    n: '04',
    title: 'The lender sees it all',
    line: 'Bureau profile, Vouch Score and affordability sit side by side, each with its evidence and limits. The lender makes the decision.',
  },
] as const;
const DWELL_MS = 2800;

function Zone({ label, on, children }: { label: string; on: boolean; children: React.ReactNode }) {
  return (
    <div
      className={`h-full rounded-[14px] border p-5 transition-[background-color,border-color,opacity] duration-300 ${
        on ? 'border-neel-700 bg-neel-50' : 'border-rule bg-surface opacity-60'
      }`}
    >
      <p className="eyebrow">{label}</p>
      <div className="mt-4 space-y-3">{children}</div>
    </div>
  );
}

function Item({ icon, title, line, on = true }: { icon: React.ReactNode; title: string; line: string; on?: boolean }) {
  return (
    <div className={`flex items-start gap-3 rounded-[10px] border bg-surface p-3 transition-colors ${on ? 'border-neel-300' : 'border-rule'}`}>
      <span className="grid size-8 shrink-0 place-items-center rounded-[8px] bg-neel-50 text-neel-700">{icon}</span>
      <span>
        <span className="block text-[14px] font-medium leading-tight">{title}</span>
        <span className="mt-0.5 block text-[12.5px] leading-snug text-ink-3">{line}</span>
      </span>
    </div>
  );
}

/** Arrow between zones; while its hand-off is the current step, a dot travels along it. */
function Handoff({ live }: { live: boolean }) {
  const reduce = useReducedMotion();
  const dot = 'absolute size-2.5 rounded-full bg-neel-700';
  const loop = { duration: 1, repeat: Infinity, ease: 'easeInOut' } as const;
  return (
    <div className="flex items-center justify-center py-2 max-lg:flex-col lg:py-0" aria-hidden>
      <div className="relative h-10 w-[2px] bg-rule-2 lg:h-[2px] lg:w-12">
        {live && !reduce ? (
          <>
            <motion.span className={`${dot} left-1/2 hidden -translate-x-1/2 max-lg:block`} animate={{ top: ['0%', '100%'] }} transition={loop} />
            <motion.span className={`${dot} top-1/2 hidden -translate-y-1/2 lg:block`} animate={{ left: ['0%', '100%'] }} transition={loop} />
          </>
        ) : null}
      </div>
      <IconArrowRight size={16} className={`rotate-90 lg:ml-1 lg:rotate-0 ${live ? 'text-neel-700' : 'text-ink-3'}`} />
    </div>
  );
}

export function HowFlow() {
  const reduce = useReducedMotion();
  const box = useRef<HTMLDivElement>(null);
  const seen = useInView(box, { margin: '0px 0px -20% 0px' });
  const [step, setStep] = useState(0);
  const [held, setHeld] = useState(false);

  // Plays the four steps in turn while the diagram is in view, until someone picks a step.
  useEffect(() => {
    if (!seen || held || reduce) return;
    const t = window.setTimeout(() => setStep((s) => (s + 1) % STEPS.length), step === STEPS.length - 1 ? DWELL_MS * 1.6 : DWELL_MS);
    return () => window.clearTimeout(t);
  }, [seen, held, reduce, step]);

  const pick = (i: number) => {
    setHeld(true);
    setStep(i);
  };

  return (
    <div ref={box} className="mt-10">
      <div role="tablist" aria-label="How Vouch works" className="grid grid-cols-2 gap-x-4 gap-y-3 border-b border-rule pb-3 sm:grid-cols-4">
        {STEPS.map((s, i) => (
          <button
            key={s.n}
            type="button"
            role="tab"
            aria-selected={i === step}
            onClick={() => pick(i)}
            className={`relative pb-2 text-left transition-colors ${i === step ? 'text-ink' : 'text-ink-3 hover:text-ink-2'}`}
          >
            <span className="block font-mono text-[11px] text-neel-700">{s.n}</span>
            <span className="display mt-0.5 block text-[clamp(15px,1.6vw,19px)] leading-tight">{s.title}</span>
            {i === step ? (
              <motion.span
                key={`${step}-${held}`}
                className="absolute inset-x-0 bottom-0 h-[2px] origin-left bg-neel-700 sm:-bottom-[13px]"
                initial={{ scaleX: held || reduce ? 1 : 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: held || reduce ? 0 : DWELL_MS / 1000, ease: 'linear' }}
              />
            ) : null}
          </button>
        ))}
      </div>
      <motion.p key={step} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-5 min-h-[3em] max-w-[70ch] text-[16px] text-ink-2">
        {STEPS[step]!.line}
      </motion.p>

      <div className="mt-6 grid items-stretch lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
        <Zone label="Borrower and trusted peers" on={step <= 1}>
          <Item icon={<IconPerson size={17} />} title="Borrower" line="A loan request, with consented evidence" on={step === 0} />
          <Item icon={<IconPerson size={17} />} title="Trusted peers" line="Accountable endorsements: their own reputation at stake" on={step === 1} />
        </Zone>
        <Handoff live={step === 2} />
        <Zone label="Vouch assessment" on={step === 2}>
          <Item icon={<IconShield size={17} />} title="Credibility checks" line="Who vouched, their record, rings and manipulation flagged" />
          <Item icon={<IconStatement size={17} />} title="Financial evidence" line="Income, obligations and cash flow, assessed separately" />
        </Zone>
        <Handoff live={step === 3} />
        <Zone label="Lender view" on={step === 3}>
          {[
            ['Bureau profile', 'or “no file”: unknown, not bad'],
            ['Vouch Score', 'with who vouched and how sure it is'],
            ['Affordability', 'what fits after essentials and EMIs'],
          ].map(([t, l]) => (
            <div key={t} className="rounded-[10px] border border-rule bg-surface px-3 py-2.5">
              <p className="text-[14px] font-medium leading-tight">{t}</p>
              <p className="mt-0.5 text-[12px] text-ink-3">{l} · evidence and limits shown</p>
            </div>
          ))}
          <p className={`pt-1 text-right font-mono text-[12px] tracking-[0.12em] transition-colors ${step === 3 ? 'text-neel-700' : 'text-ink-3'}`}>THE LENDER DECIDES</p>
        </Zone>
      </div>

      <p className="display mt-10 text-[clamp(22px,2.6vw,32px)] leading-tight">More context. Clearer reasons. A human decision.</p>
    </div>
  );
}
