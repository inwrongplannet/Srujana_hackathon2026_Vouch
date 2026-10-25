import { motion } from 'motion/react';
import { IconCheck } from '@/components/icons';

/** Onboarding progress drawn as a tiny graph: steps are nodes, progress travels along edges. */
export function StepRail({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="flex items-center" aria-label="Onboarding progress">
      {steps.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={label} className="flex items-center" aria-current={active ? 'step' : undefined}>
            <div className="flex items-center gap-2">
              <span
                className={`grid size-6 place-items-center rounded-full text-[11px] font-semibold transition-colors duration-300 ${
                  done ? 'bg-neel-700 text-surface' : active ? 'bg-ink text-paper' : 'border border-dashed border-rule-2 text-ink-3'
                }`}
              >
                {done ? <IconCheck size={13} strokeWidth={2.4} /> : i + 1}
              </span>
              <span className={`hidden text-[12.5px] sm:inline ${active ? 'font-medium text-ink' : 'text-ink-3'}`}>{label}</span>
            </div>
            {i < steps.length - 1 ? (
              <span className="relative mx-3 h-px w-6 bg-rule-2 sm:w-8">
                <motion.span
                  className="absolute inset-y-0 left-0 bg-neel-700"
                  initial={false}
                  animate={{ width: done ? '100%' : '0%' }}
                  transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }}
                />
              </span>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
