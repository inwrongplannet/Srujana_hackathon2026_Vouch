import { AnimatePresence, motion } from 'motion/react';
import type { Snapshot } from '@/api/types';
import { IconLock } from '@/components/icons';
import { fmt } from '@/lib/format';

const layoutSpring = { type: 'spring' as const, duration: 0.6, bounce: 0.12 };

/**
 * Vouch capacity C = max(0, R), split equally across every outgoing vouch. A preview segment
 * squeezes in and every existing segment visibly thins: vouching has a cost.
 */
export function CapacityMeter({
  s,
  voucherId,
  preview,
  height = 56,
}: {
  s: Snapshot;
  voucherId: string;
  preview?: { requesterId: string; weightAfter: string } | null;
  height?: number;
}) {
  const out = s.edges.filter((e) => e.from === voucherId);
  const segs = [
    ...out.map((e) => ({ id: e.to, weight: preview ? preview.weightAfter : e.weight, locked: !!e.lockedLoanId, ghost: false })),
    ...(preview ? [{ id: preview.requesterId, weight: preview.weightAfter, locked: false, ghost: true }] : []),
  ];
  const shades = ['#24368F', '#2F45AA', '#3D56C2', '#4C64CB', '#5A71D2'];

  if (segs.length === 0) {
    return (
      <div className="hatch grid place-items-center rounded-[10px] border border-dashed border-neel-200 text-[13px] text-neel-800" style={{ height }}>
        Capacity unallocated
      </div>
    );
  }

  return (
    <div className="flex gap-[3px]" style={{ height }} role="img" aria-label={`${segs.length} vouches sharing capacity, ${fmt(segs[0]!.weight)} each`}>
      <AnimatePresence initial={false}>
        {segs.map((seg, i) => {
          const n = s.nodes[seg.id]!;
          return (
            <motion.div
              key={seg.id}
              layout
              initial={{ flexGrow: 0.0001, opacity: 0 }}
              animate={{ flexGrow: 1, opacity: 1 }}
              exit={{ flexGrow: 0.0001, opacity: 0 }}
              transition={layoutSpring}
              className={`relative flex min-w-0 basis-0 flex-col justify-center overflow-hidden rounded-[8px] px-3 ${
                seg.ghost ? 'hatch border border-dashed border-neel-500 text-neel-900' : 'text-surface'
              }`}
              style={seg.ghost ? undefined : { background: shades[i % shades.length] }}
            >
              {seg.locked ? <span className="hatch-ink absolute inset-0 opacity-40" /> : null}
              <span className="relative flex items-center gap-1 truncate text-[12.5px] font-medium">
                {seg.locked ? <IconLock size={12} /> : null}
                {seg.ghost ? `${n.name.split(' ')[0]} · new` : n.name.split(' ')[0]}
              </span>
              <motion.span key={seg.weight} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} className="relative num font-mono text-[12px] opacity-80">
                W {fmt(seg.weight)}
              </motion.span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
