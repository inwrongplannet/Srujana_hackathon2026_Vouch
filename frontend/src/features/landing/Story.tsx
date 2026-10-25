/**
 * Shared pieces of the landing page: scroll reveal, section frame and rubber stamp. Motion only
 * marks a change of state (a reveal, a stamp landing), never decoration.
 */
import type { ReactNode } from 'react';
import { motion, useReducedMotion } from 'motion/react';

const EASE = [0.22, 1, 0.36, 1] as const;

export function Reveal({ children, delay = 0, className = '' }: { children: ReactNode; delay?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '0px 0px -12% 0px' }}
      transition={{ duration: 0.7, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

export function Section({ id, kicker, title, children }: { id?: string; kicker: string; title: ReactNode; children: ReactNode }) {
  return (
    <section id={id} className="border-t border-rule">
      <div className="mx-auto max-w-[1180px] px-4 py-20 sm:px-8 lg:py-24">
        <Reveal>
          <p className="font-mono text-[11.5px] tracking-[0.16em] text-neel-700">{kicker.toUpperCase()}</p>
          <h2 className="display mt-3 max-w-[24ch] text-[clamp(32px,4.2vw,56px)] leading-[1] tracking-[-0.025em] text-balance">{title}</h2>
        </Reveal>
        {children}
      </div>
    </section>
  );
}

const stampTone = {
  declined: 'text-defaulted border-defaulted',
  approved: 'text-active border-active',
} as const;

/** A rubber stamp that lands when it mounts in view. */
export function Stamp({ tone, children, delay = 0.35 }: { tone: keyof typeof stampTone; children: ReactNode; delay?: number }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      aria-hidden
      className={`pointer-events-none select-none rounded-[6px] border-[3px] px-3.5 py-1 font-mono text-[clamp(18px,2vw,24px)] font-semibold tracking-[0.18em] mix-blend-multiply ${stampTone[tone]}`}
      style={{ boxShadow: 'inset 0 0 0 2px var(--color-surface), inset 0 0 0 3px currentColor' }}
      initial={reduce ? false : { opacity: 0, scale: 1.9, rotate: -16 }}
      whileInView={{ opacity: 0.86, scale: 1, rotate: -9 }}
      viewport={{ once: true }}
      transition={{ type: 'spring', stiffness: 520, damping: 22, delay }}
    >
      {children}
    </motion.div>
  );
}
