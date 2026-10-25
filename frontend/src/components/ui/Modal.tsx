import { useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { IconClose } from '@/components/icons';

/** Centered dialog (or right-hand sheet) with focus, Escape and backdrop handling. */
export function Modal({
  open,
  onClose,
  title,
  eyebrow,
  children,
  variant = 'center',
  width = 640,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  eyebrow?: ReactNode;
  children: ReactNode;
  variant?: 'center' | 'sheet';
  width?: number;
}) {
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
      prev?.focus();
    };
  }, [open, onClose]);

  const sheet = variant === 'sheet';
  return createPortal(
    <AnimatePresence>
      {open ? (
        <div className={`fixed inset-0 z-50 flex ${sheet ? 'justify-end' : 'items-center justify-center p-4'}`}>
          <motion.div className="absolute inset-0 bg-ink/25" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.div
            ref={panel}
            role="dialog"
            aria-modal="true"
            tabIndex={-1}
            className={`relative flex max-h-full w-full flex-col bg-surface shadow-[var(--shadow-float)] outline-none ${sheet ? 'h-full border-l border-rule' : 'max-h-[92dvh] rounded-[16px] border border-rule'}`}
            style={{ maxWidth: width }}
            initial={sheet ? { x: '100%' } : { opacity: 0, y: 18, scale: 0.98 }}
            animate={sheet ? { x: 0 } : { opacity: 1, y: 0, scale: 1 }}
            exit={sheet ? { x: '100%' } : { opacity: 0, y: 10, scale: 0.98 }}
            transition={{ type: 'spring', duration: 0.45, bounce: 0.08 }}
          >
            <header className="flex items-start justify-between gap-4 border-b border-rule px-6 py-5">
              <div>
                {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
                <h2 className="display mt-1 text-[26px] leading-tight">{title}</h2>
              </div>
              <button type="button" onClick={onClose} className="rounded-md p-1.5 text-ink-3 hover:bg-paper-2 hover:text-ink" aria-label="Close">
                <IconClose size={18} />
              </button>
            </header>
            <div className="flex-1 overflow-y-auto">{children}</div>
          </motion.div>
        </div>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}
