import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { AnimatePresence, motion } from 'motion/react';
import { api } from '@/api/client';
import type { StoryStep } from '@/api/types';
import { useSnapshot } from '@/state/DemoProvider';
import {
  IconArrowRight,
  IconChevronDown,
  IconClockForward,
  IconReset,
  IconStorm,
  IconCheck,
  IconAlert,
} from '@/components/icons';
import { dayDate } from '@/lib/format';

const RAIL: { key: StoryStep[]; label: string }[] = [
  { key: ['register'], label: 'Anchor' },
  { key: ['request'], label: 'Ask' },
  { key: ['vouch'], label: 'Vouch' },
  { key: ['apply'], label: 'Apply' },
  { key: ['approve'], label: 'Approve' },
  { key: ['advance'], label: '30 days' },
  { key: ['outcome', 'settled', 'defaulted'], label: 'Outcome' },
];

interface Cue {
  text: string;
  go?: { label: string; path: string };
}

const CUES: Record<StoryStep, Cue> = {
  register: { text: 'Lakshmi, a tailor with no credit file, anchors her identity.', go: { label: 'Open sign-in', path: '/login' } },
  request: { text: 'She asks Meena, who buys from her, for a vouch.', go: { label: 'Lakshmi’s view', path: '/app/borrower' } },
  vouch: { text: 'Meena sees what she would risk, then holds to vouch.', go: { label: 'Meena’s view', path: '/app/voucher' } },
  apply: { text: 'One vouch opens a micro-limit. Lakshmi applies for ₹5,000.', go: { label: 'Lakshmi’s view', path: '/app/borrower' } },
  approve: { text: 'Sahyog reads the path-by-path score and decides.', go: { label: 'Lender console', path: '/app/lender/p_lakshmi' } },
  advance: { text: 'The loan is out. Move the clock to the due date.' },
  outcome: { text: 'Due today. Repay, or default and watch the cascade stop at hop 2.' },
  settled: { text: 'Repaid: credibility minted, Meena earns yield. Try a regional shock next.' },
  defaulted: { text: 'Defaulted: damped penalties, hop 3 untouched. Try a regional shock next.' },
};

/** Presenter controls. Dark ink so it never reads as part of the product UI. */
export function DirectorBar() {
  const s = useSnapshot();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const loan = [...s.loans].reverse().find((l) => l.borrower === s.borrowerId);
  const stepIndex = RAIL.findIndex((r) => r.key.includes(s.story));
  const cue = CUES[s.story];
  const gadag = s.clusters.find((c) => c.id === 'gadag');
  const shockUsed = s.loans.some((l) => l.id === 'L-1987' && l.status === 'DEFAULTED');

  async function run(key: string, fn: () => Promise<void>) {
    setBusy(key);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-30 flex justify-center px-4">
      <AnimatePresence mode="wait" initial={false}>
        {open ? (
          <motion.div
            key="open"
            initial={{ y: 24, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 24, opacity: 0 }}
            transition={{ type: 'spring', duration: 0.4, bounce: 0.1 }}
            className="pointer-events-auto w-full max-w-[980px] rounded-[16px] bg-ink text-paper shadow-[0_24px_60px_-20px_rgb(12_18_51/0.6)]"
          >
            <div className="flex items-center gap-4 px-4 pt-3">
              <span className="font-mono text-[10.5px] tracking-[0.14em] text-neel-300">DEMO DIRECTOR</span>
              <ol className="flex flex-1 items-center">
                {RAIL.map((r, i) => (
                  <li key={r.label} className="flex flex-1 items-center last:flex-none">
                    <span className="flex items-center gap-1.5">
                      <span
                        className={`size-2 rounded-full transition-colors ${
                          i < stepIndex ? 'bg-neel-300' : i === stepIndex ? 'bg-paper ring-4 ring-paper/15' : 'border border-paper/30'
                        }`}
                      />
                      <span className={`hidden text-[11px] md:inline ${i === stepIndex ? 'text-paper' : 'text-paper/45'}`}>{r.label}</span>
                    </span>
                    {i < RAIL.length - 1 ? <span className={`mx-2 h-px flex-1 ${i < stepIndex ? 'bg-neel-300/70' : 'bg-paper/15'}`} /> : null}
                  </li>
                ))}
              </ol>
              <span className="hidden font-mono text-[11px] text-paper/50 sm:inline">
                Day {s.day} · {dayDate(s.day)}
              </span>
              <button type="button" onClick={() => setOpen(false)} className="rounded p-1 text-paper/60 hover:bg-paper/10 hover:text-paper" aria-label="Hide director">
                <IconChevronDown size={16} />
              </button>
            </div>

            <div className="flex flex-wrap items-center gap-3 px-4 pt-2.5 pb-3.5">
              <p className="basis-full text-[13.5px] text-paper/90 sm:min-w-[240px] sm:flex-1 sm:basis-auto sm:text-[14px]">{cue.text}</p>

              {cue.go && pathname !== cue.go.path ? (
                <DirectorButton primary onClick={() => navigate(cue.go!.path)} icon={<IconArrowRight size={15} />}>
                  {cue.go.label}
                </DirectorButton>
              ) : null}

              {s.story === 'advance' && loan ? (
                <DirectorButton primary busy={busy === 'adv'} onClick={() => run('adv', () => api.advance(30))} icon={<IconClockForward size={15} />}>
                  Advance 30 days
                </DirectorButton>
              ) : null}

              {s.story === 'outcome' && loan ? (
                <>
                  <DirectorButton primary busy={busy === 'repay'} onClick={() => run('repay', () => api.settle(loan.id))} icon={<IconCheck size={15} />}>
                    Lakshmi repays
                  </DirectorButton>
                  <DirectorButton danger busy={busy === 'def'} onClick={() => run('def', async () => { await api.defaultLoan(loan.id); navigate('/app/lender/p_lakshmi'); })} icon={<IconAlert size={15} />}>
                    Lakshmi defaults
                  </DirectorButton>
                </>
              ) : null}

              <span className="mx-1 hidden h-6 w-px bg-paper/15 sm:block" />

              {!shockUsed ? (
                <DirectorButton
                  label="Regional shock"
                  busy={busy === 'shock'}
                  onClick={() => run('shock', async () => { await api.regionalShock(); navigate('/app/lender'); })}
                  icon={<IconStorm size={15} />}
                >
                  <span className="hidden sm:inline">Regional shock</span>
                </DirectorButton>
              ) : gadag?.tripped ? (
                <span className="text-[12px] text-restricted">Gadag breaker open</span>
              ) : null}
              <DirectorButton
                label="Reset"
                busy={busy === 'reset'}
                onClick={() => run('reset', async () => { await api.reset(); navigate('/login'); })}
                icon={<IconReset size={15} />}
              >
                <span className="hidden sm:inline">Reset</span>
              </DirectorButton>
            </div>
          </motion.div>
        ) : (
          <motion.button
            key="closed"
            type="button"
            initial={{ y: 16, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 16, opacity: 0 }}
            onClick={() => setOpen(true)}
            className="pointer-events-auto flex items-center gap-2 rounded-full bg-ink px-4 py-2 font-mono text-[11px] tracking-[0.12em] text-paper shadow-[var(--shadow-float)]"
          >
            <span className="size-1.5 rounded-full bg-neel-300" /> DIRECTOR
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}

function DirectorButton({
  children,
  onClick,
  icon,
  primary,
  danger,
  busy,
  label,
}: {
  children: React.ReactNode;
  /** Accessible name when the visible text is hidden on small screens. */
  label?: string;
  onClick: () => void;
  icon?: React.ReactNode;
  primary?: boolean;
  danger?: boolean;
  busy?: boolean;
}) {
  const tone = primary
    ? 'bg-paper text-ink hover:bg-white'
    : danger
      ? 'bg-defaulted text-paper hover:bg-[#93291f]'
      : 'bg-paper/8 text-paper hover:bg-paper/15 border border-paper/15';
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`inline-flex h-9 items-center gap-1.5 rounded-[8px] px-3.5 text-[13px] font-medium transition-colors disabled:opacity-60 ${tone}`}
    >
      {icon}
      {children}
    </button>
  );
}
