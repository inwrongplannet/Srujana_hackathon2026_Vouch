/**
 * Three ideas from the Vouch design, as tabs over one panel so the page stays short: what a vouch is
 * worth, whether the loan survives a bad month, and how the assessment explains itself.
 */
import { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { VouchBuilder } from './VouchBuilder';
import { BreakTheLoan } from './BreakTheLoan';
import { Explanation } from './Explanation';

const TABS = [
  { key: 'vouch', n: '01', label: 'What a vouch is worth', line: 'Endorsers stake their own reputation. Quality counts; volume barely does.', body: <VouchBuilder /> },
  { key: 'stress', n: '02', label: 'Will the loan survive?', line: 'Affordability stays its own signal. Every plan is tested against her worst month.', body: <BreakTheLoan /> },
  { key: 'explain', n: '03', label: 'Explain, don’t invent', line: 'When a score falls, we separate what we saw from what we were told.', body: <Explanation /> },
] as const;

export function HowItDecides() {
  const [key, setKey] = useState<(typeof TABS)[number]['key']>('vouch');
  const tab = TABS.find((t) => t.key === key)!;
  return (
    <div className="mt-10">
      <div role="tablist" aria-label="How Vouch works" className="grid grid-cols-3 border-b border-rule">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={key === t.key}
            onClick={() => setKey(t.key)}
            className={`relative pr-3 pb-4 text-left transition-colors ${key === t.key ? 'text-ink' : 'text-ink-3 hover:text-ink-2'}`}
          >
            <span className="block font-mono text-[11px] text-neel-700">{t.n}</span>
            <span className="display mt-1 block text-[clamp(16px,2vw,24px)] leading-tight">{t.label}</span>
            {key === t.key ? <motion.span layoutId="how-tab" className="absolute inset-x-0 -bottom-px h-[2px] bg-ink" /> : null}
          </button>
        ))}
      </div>
      <p className="mt-6 mb-8 text-[16px] text-ink-2">{tab.line}</p>
      <AnimatePresence mode="wait">
        <motion.div key={tab.key} role="tabpanel" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.25 }}>
          {tab.body}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
