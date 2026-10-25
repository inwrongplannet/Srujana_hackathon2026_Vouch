import { AnimatePresence, motion } from 'motion/react';
import { useEffect } from 'react';
import { useSnapshot } from '@/state/DemoProvider';
import { IconBlock, IconClose } from '@/components/icons';
import { EventRow } from './EventRow';

/** The simulated chain as a ledger you can open from anywhere. */
export function ChainDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const snapshot = useSnapshot();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-ink/10"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            role="dialog"
            aria-label="Contract events"
            className="fixed top-0 right-0 bottom-0 z-50 flex w-full max-w-[440px] flex-col border-l border-rule bg-surface shadow-[var(--shadow-float)]"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', duration: 0.45, bounce: 0.08 }}
          >
            <header className="flex items-start justify-between gap-4 border-b border-rule px-6 py-5">
              <div>
                <p className="eyebrow flex items-center gap-1.5">
                  <IconBlock size={14} /> Simulated chain
                </p>
                <h2 className="display mt-1.5 text-[26px] leading-none">Contract events</h2>
                <p className="mt-2 font-mono text-[12px] text-ink-3">block {snapshot.block.toLocaleString('en-IN')} · 3 contracts + breaker</p>
              </div>
              <button type="button" onClick={onClose} className="rounded-md p-1.5 text-ink-3 hover:bg-paper-2 hover:text-ink" aria-label="Close">
                <IconClose size={18} />
              </button>
            </header>
            <div className="flex-1 overflow-y-auto px-6">
              {snapshot.events.length === 0 ? (
                <EmptyLedger />
              ) : (
                <div className="ruled">
                  {snapshot.events.map((e) => (
                    <EventRow key={e.id} event={e} snapshot={snapshot} />
                  ))}
                </div>
              )}
            </div>
            <footer className="border-t border-rule px-6 py-3 text-[12px] text-ink-3">
              IdentityRegistry, VouchHub, LoanEscrow: simulated, no live chain on the demo path.
            </footer>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );
}

function EmptyLedger() {
  return (
    <div className="flex flex-col items-center py-16 text-center">
      <svg width="132" height="96" viewBox="0 0 132 96" aria-hidden>
        <rect x="10" y="28" width="34" height="34" rx="6" fill="none" stroke="#C9C2B4" strokeDasharray="3 4" />
        <rect x="49" y="28" width="34" height="34" rx="6" fill="none" stroke="#C9C2B4" strokeDasharray="3 4" />
        <rect x="88" y="28" width="34" height="34" rx="6" fill="#ECEEF7" stroke="#24368F" strokeWidth="1.5" />
        <path d="M44 45h5M83 45h5" stroke="#C9C2B4" />
        <circle cx="105" cy="45" r="4" fill="#24368F" />
      </svg>
      <p className="mt-4 font-medium">No events yet</p>
      <p className="mt-1 max-w-[30ch] text-[13px] text-ink-3">Anchoring an identity writes the first one.</p>
    </div>
  );
}
