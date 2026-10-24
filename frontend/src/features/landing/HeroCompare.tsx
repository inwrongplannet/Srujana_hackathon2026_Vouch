import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { api } from '@/api/client';
import type { VouchPreview } from '@/api/types';
import { IconAnchor, IconClose } from '@/components/icons';
import { fmt, formatMoney } from '@/lib/format';

/** One person, two systems: the bureau's dead end against VeriTrust's honest uncertainty. */
export function HeroCompare() {
  const [p, setP] = useState<VouchPreview | null>(null);
  useEffect(() => {
    void api.storyPreview().then(setP);
  }, []);
  const a = p?.requesterAfter;
  const top = a?.paths[0];
  return (
    <div className="relative mx-auto w-full max-w-[460px] pb-6">
      {/* Bureau card: flat, grey, final */}
      <motion.div
        initial={{ opacity: 0, y: 16, rotate: -1 }}
        animate={{ opacity: 1, y: 0, rotate: -3 }}
        transition={{ delay: 0.35, duration: 0.6, ease: [0.2, 0, 0, 1] }}
        className="relative w-[82%] rounded-[14px] border border-rule-2 bg-paper-2 p-5 text-ink-3 shadow-[var(--shadow-lift)]"
      >
        <p className="font-mono text-[10.5px] tracking-[0.14em]">TYPICAL BUREAU REPORT</p>
        <div className="mt-3 flex items-end justify-between">
          <div>
            <p className="text-[13px]">Lakshmi Naik · tailor</p>
            <p className="mt-1 text-[12px]">No credit history found</p>
          </div>
          <p className="display text-[46px] leading-none text-ink-3/80">−1</p>
        </div>
        <div className="mt-4 flex items-center gap-2 rounded-[8px] border border-dashed border-rule-2 px-3 py-2 text-[13px]">
          <IconClose size={15} /> Application declined: insufficient file
        </div>
      </motion.div>

      {/* VeriTrust card: the same person, read properly */}
      <motion.div
        initial={{ opacity: 0, y: 26 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.75, duration: 0.7, ease: [0.2, 0, 0, 1] }}
        className="relative -mt-3 ml-auto w-[88%] rounded-[16px] border border-rule bg-surface p-5 shadow-[var(--shadow-float)]"
      >
        <div className="flex items-center justify-between">
          <p className="font-mono text-[10.5px] tracking-[0.14em] text-neel-700">VERITRUST ASSESSMENT</p>
          <span className="rounded-full bg-cold-tint px-2 py-0.5 text-[11px] font-medium text-[#55585f]">Unknown, not risky</span>
        </div>
        <div className="mt-3 grid grid-cols-[auto_1fr] items-end gap-4">
          <p className="display num text-[46px] leading-none">{a ? fmt(a.lcb) : '…'}</p>
          <div className="pb-1.5">
            <div className="relative h-6">
              <div className="absolute inset-x-0 top-[9px] h-[6px] rounded-full bg-paper-2" />
              <motion.div
                className="hatch absolute top-0 h-6 rounded-[5px] border border-neel-200"
                initial={{ left: '8%', width: '84%' }}
                animate={{ left: '20%', width: '50%' }}
                transition={{ delay: 1.4, duration: 1.2, ease: [0.2, 0, 0, 1] }}
              />
              <motion.div className="absolute top-[-3px] h-[30px] w-[2px] rounded bg-ink" initial={{ left: '40%' }} animate={{ left: '45%' }} transition={{ delay: 1.4, duration: 1.2 }} />
              <motion.span
                className="absolute top-[5px] block size-3.5 -translate-x-1/2 rotate-45 rounded-[2px] bg-neel-700"
                initial={{ left: '8%' }}
                animate={{ left: '20%' }}
                transition={{ delay: 1.4, duration: 1.2, ease: [0.2, 0, 0, 1] }}
              />
            </div>
            <p className="mt-1 text-[11px] text-ink-3">{a ? `μ ${fmt(a.mu)} · σ² ${fmt(a.sigma2)} · one vouch, no data yet` : ''}</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-1.5 text-[12.5px]">
          <span className="inline-flex items-center gap-1 rounded-[5px] bg-neel-700 px-1.5 py-0.5 font-medium text-surface">
            <IconAnchor size={12} /> Sahyog
          </span>
          <span className="text-ink-3">→</span> Ramesh <span className="text-ink-3">→</span> Meena <span className="text-ink-3">→</span>
          <b>Lakshmi</b>
          <span className="ml-auto font-mono text-ink-2">{top ? `+${fmt(top.trust)}` : ''}</span>
        </div>
        <div className="mt-4 flex items-center justify-between rounded-[10px] bg-neel-50 px-4 py-3">
          <span className="text-[13px] text-neel-900">First limit, from one vouch</span>
          <span className="display num text-[24px] leading-none text-neel-700">{a ? formatMoney(a.limit) : '…'}</span>
        </div>
      </motion.div>
    </div>
  );
}
