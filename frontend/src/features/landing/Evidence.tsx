/**
 * Published evidence on the landing page: India's credit gap, and what research says for and
 * against using cash flow and social ties. Figures and limits come from `figures.ts`.
 */
import { motion, useReducedMotion } from 'motion/react';
import { IconArrowUpRight } from '@/components/icons';
import { FINDINGS, GAP, TREND, type Finding, type Source } from './figures';
import { Reveal } from './Story';

function SourceLink({ source, className = '' }: { source: Source; className?: string }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-start gap-1 text-[12px] leading-snug text-ink-3 underline decoration-rule-2 underline-offset-2 hover:text-ink-2 ${className}`}
    >
      Source: {source.label}
      <IconArrowUpRight size={12} className="mt-0.5 shrink-0" />
    </a>
  );
}

function Bar({ year, value, tone }: { year: string; value: number; tone: string }) {
  const reduce = useReducedMotion();
  return (
    <div className="mt-1.5 grid grid-cols-[36px_1fr_36px] items-center gap-2 font-mono text-[11px] text-ink-3" title={`${year}: ${value}%`}>
      <span>{year}</span>
      <div className="h-2.5 overflow-hidden rounded-r-[4px] bg-paper-2">
        <motion.div
          className={`h-full rounded-r-[4px] ${tone}`}
          initial={reduce ? false : { width: 0 }}
          whileInView={{ width: `${value}%` }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          style={reduce ? { width: `${value}%` } : undefined}
        />
      </div>
      <span className="num text-right text-ink">{value}%</span>
    </div>
  );
}

/** The headline figure, under the section title. */
export function GapHeadline() {
  return (
    <div className="mt-10">
      <Reveal>
        <p className="display num text-[clamp(64px,9vw,128px)] leading-[0.85] tracking-[-0.04em] text-neel-700">
          {GAP.headline.value}
          <span className="text-[0.4em] tracking-[-0.02em] text-ink-3"> {GAP.headline.unit}</span>
        </p>
        <p className="mt-5 max-w-[40ch] text-[19px] leading-snug text-ink">{GAP.headline.line}</p>
        <p className="mt-4 max-w-[52ch] text-[14.5px] leading-relaxed text-ink-2">
          Not all of them were refused, and not all of them could repay. A blank file says nothing either way, which is why it should not decide alone.
        </p>
        <SourceLink source={GAP.source} className="mt-5" />
      </Reveal>
    </div>
  );
}

/** The supporting figures and the 2017-2026 trend, in the right-hand column. */
export function GapFacts() {
  return (
    <div className="lg:pt-8">
      <Reveal delay={0.1}>
        <div className="divide-y divide-rule border-y border-rule">
          {GAP.facts.map((f) => (
            <div key={f.value} className="grid grid-cols-[92px_1fr] items-baseline gap-4 py-4">
              <p className="display num text-[34px] leading-none">{f.value}</p>
              <p className="text-[15px] leading-snug text-ink-2">{f.line}</p>
            </div>
          ))}
        </div>

        <div className="card mt-6 p-5">
          <p className="eyebrow">March 2017 and March 2026</p>
          {TREND.rows.map((r) => (
            <div key={r.label} className="mt-4" role="img" aria-label={`${r.label}: ${r.from}% in 2017, ${r.to}% in 2026`}>
              <p className="text-[13.5px] text-ink">{r.label}</p>
              <Bar year="2017" value={r.from} tone="bg-neel-300" />
              <Bar year="2026" value={r.to} tone="bg-neel-700" />
            </div>
          ))}
          <p className="mt-4 text-[12.5px] leading-relaxed text-ink-3">
            More Indians have borrowed at least once, yet newcomers take a smaller share of new loans. Market context, not proof that scores are wrong.
          </p>
          <SourceLink source={TREND.source} className="mt-3" />
        </div>
      </Reveal>
    </div>
  );
}

function FindingCard({ f }: { f: Finding }) {
  return (
    <article className="card flex h-full flex-col overflow-hidden">
      <div className={`h-[3px] ${f.counter ? 'bg-restricted' : 'bg-neel-700'}`} />
      <div className="flex flex-1 flex-col p-6">
        <p className={`eyebrow ${f.counter ? '!text-restricted-ink' : ''}`}>{f.counter ? 'Counter-evidence' : 'Evidence'}</p>
        <p className={`display num mt-3 text-[44px] leading-none ${f.counter ? 'text-restricted-ink' : 'text-neel-700'}`}>
          {f.figure}
          {f.unit ? <span className="ml-2 text-[15px] tracking-normal text-ink-3">{f.unit}</span> : null}
        </p>
        <h3 className="display mt-4 text-[22px] leading-tight">{f.title}</h3>
        <p className="mt-2 text-[14.5px] leading-relaxed text-ink-2">{f.body}</p>
        <p className="mt-3 text-[12.5px] leading-relaxed text-ink-3">
          <span className="font-medium text-ink-2">What it does not show: </span>
          {f.limit}
        </p>
        <div className="mt-auto pt-5">
          <div className="border-t border-rule pt-4">
            <p className="eyebrow">In Vouch</p>
            <p className="mt-1.5 text-[14px] leading-relaxed text-ink">{f.inVouch}</p>
          </div>
          <SourceLink source={f.source} className="mt-4" />
        </div>
      </div>
    </article>
  );
}

export function Research() {
  return (
    <div className="mt-12">
      <div className="grid gap-4 md:grid-cols-2">
        {FINDINGS.map((f, n) => (
          <Reveal key={f.key} delay={n * 0.06} className="h-full">
            <FindingCard f={f} />
          </Reveal>
        ))}
      </div>
      <Reveal>
        <p className="mt-8 max-w-[72ch] text-[15px] leading-relaxed text-ink-2">
          The evidence supports testing verified cash flow and carefully weighted network signals beside the bureau. It does not yet show that a Vouch
          Score improves lending decisions in India.{' '}
          <span className="font-medium text-ink">That is the question this prototype is built to test.</span>
        </p>
      </Reveal>
    </div>
  );
}
