/**
 * What research says for and against using cash flow and social ties, as cards with each study's
 * limit and source. Figures come from `figures.ts`.
 */
import { IconArrowUpRight } from '@/components/icons';
import { FINDINGS, type Finding, type Source } from './figures';
import { Reveal } from './Story';

export function SourceLink({ source, className = '' }: { source: Source; className?: string }) {
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
