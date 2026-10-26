/**
 * A figure's label that explains itself: hover, focus or tap it to see the formula behind the
 * number, what each symbol means and which file computes it (`./formulas.ts`). The card is portalled
 * to the body so cards with overflow-hidden never clip it, and it flips above the label near the
 * bottom of the screen.
 */
import { Fragment, useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { FORMULAS, type FormulaId } from './formulas';

const WIDTH = 360;
const GAP = 8;
const EDGE = 16;

export function Explain({ id, children, className = '' }: { id: FormulaId; children: ReactNode; className?: string }) {
  const f = FORMULAS[id];
  const tipId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);

  const show = useCallback(() => {
    window.clearTimeout(closeTimer.current);
    setOpen(true);
  }, []);
  // A short delay lets the pointer cross the gap from the label into the card.
  const hide = useCallback(() => {
    window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setOpen(false), 120);
  }, []);

  useLayoutEffect(() => {
    if (!open || !trigger.current || !card.current) return;
    const t = trigger.current.getBoundingClientRect();
    const h = card.current.offsetHeight;
    const w = Math.min(WIDTH, window.innerWidth - 2 * EDGE);
    const left = Math.min(Math.max(EDGE, t.left), window.innerWidth - w - EDGE);
    const below = t.bottom + GAP + h <= window.innerHeight - EDGE;
    setPos({ left, top: below ? t.bottom + GAP : Math.max(EDGE, t.top - GAP - h) });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close();
    window.addEventListener('scroll', close, true);
    window.addEventListener('resize', close);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('scroll', close, true);
      window.removeEventListener('resize', close);
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  useEffect(() => () => window.clearTimeout(closeTimer.current), []);

  return (
    <>
      <button
        ref={trigger}
        type="button"
        aria-describedby={open ? tipId : undefined}
        className={`cursor-help text-left [text-transform:inherit] underline decoration-current/35 decoration-dotted underline-offset-[3px] transition-colors hover:decoration-current focus-visible:decoration-current ${className}`}
        onPointerEnter={(e) => e.pointerType === 'mouse' && show()}
        onPointerLeave={(e) => e.pointerType === 'mouse' && hide()}
        onFocus={show}
        onBlur={hide}
        onClick={() => (open ? setOpen(false) : show())}
      >
        {children}
      </button>
      {createPortal(
        <AnimatePresence onExitComplete={() => setPos(null)}>
          {open ? (
            <motion.div
              ref={card}
              id={tipId}
              role="tooltip"
              onPointerEnter={show}
              onPointerLeave={hide}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: pos ? 1 : 0, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.14 }}
              style={{ left: pos?.left ?? 0, top: pos?.top ?? 0, width: `min(${WIDTH}px, calc(100vw - ${2 * EDGE}px))` }}
              className="fixed z-[60] rounded-[10px] border border-rule-2 bg-surface p-4 text-left shadow-[var(--shadow-lift)]"
            >
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[13.5px] font-medium text-ink">{f.title}</p>
                <span className="font-mono text-[10px] tracking-[0.08em] whitespace-nowrap text-ink-3 uppercase">{f.engine}</span>
              </div>
              <div className="mt-2 space-y-1 rounded-[7px] bg-paper-2 px-3 py-2 font-mono text-[12px] leading-relaxed text-ink">
                {f.formula.map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
              {'terms' in f && f.terms ? (
                <dl className="mt-2.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[12px] leading-snug">
                  {f.terms.map(([sym, meaning]) => (
                    <Fragment key={sym}>
                      <dt className="font-mono whitespace-nowrap text-ink">{sym}</dt>
                      <dd className="text-ink-2">{meaning}</dd>
                    </Fragment>
                  ))}
                </dl>
              ) : null}
              {'note' in f && f.note ? <p className="mt-2.5 text-[12px] leading-snug text-ink-2">{f.note}</p> : null}
              <p className="mt-2.5 border-t border-rule pt-2 font-mono text-[10.5px] break-words text-ink-3">{f.source}</p>
            </motion.div>
          ) : null}
        </AnimatePresence>,
        document.body,
      )}
    </>
  );
}
