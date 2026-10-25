/**
 * "Explain, don't invent": Suresh's assessment split the way the Vouch documentation requires,
 * into observed facts, what he reported, what the system inferred, and what is missing. Copy only;
 * the figures match the shock case in the hero.
 */
import { Reveal } from './Story';

const COLUMNS = [
  {
    title: 'Observed',
    tone: 'bg-active',
    note: 'verified records, with source and date',
    items: [
      'Bureau score 745 → 668 between Nov and Feb (bureau report, 1 Feb)',
      'Revolving balance up ₹48,000 in January (bureau report)',
      'Daily fare credits steady for 18 months (bank statement)',
    ],
  },
  {
    title: 'Reported',
    tone: 'bg-neel-500',
    note: 'his words, labelled as his',
    items: ['He reports a hospital bill not covered by insurance'],
  },
  {
    title: 'Inferred',
    tone: 'bg-restricted',
    note: 'interpretation, with confidence',
    items: ['The score fell because of utilisation, not missed payments (high: no late payments on file)'],
  },
  {
    title: 'Missing',
    tone: 'bg-ink-3',
    note: 'and what would resolve it',
    items: ['Purpose of the expense is unverified → hospital invoice, if he chooses to share it', 'Current living costs → one month of statements'],
  },
];

export function Explanation() {
  return (
    <div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {COLUMNS.map((c, n) => (
          <Reveal key={c.title} delay={n * 0.06} className="h-full">
            <div className="card h-full overflow-hidden">
              <div className={`h-[3px] ${c.tone}`} />
              <div className="p-5">
              <p className="display text-[22px]">{c.title}</p>
              <p className="text-[12px] text-ink-3">{c.note}</p>
              <ul className="mt-4 space-y-3 text-[13.5px] leading-snug text-ink-2">
                {c.items.map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
      <p className="mt-6 max-w-[70ch] text-[13.5px] leading-relaxed text-ink-3">
        By design, reasons come from these fields through fixed, versioned rules. A language model may rephrase them; it never invents a cause, labels a
        medical event without evidence, or makes the decision.
      </p>
    </div>
  );
}
