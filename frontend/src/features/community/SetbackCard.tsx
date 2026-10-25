/**
 * A borrower's setback update and their vouchers' answers. Standing by renews the vouch; stepping
 * back withdraws it and frees the stake, quietly. The lender sees the tally, not the people.
 */
import { motion } from 'motion/react';
import { Button } from '@/components/ui/Button';
import { IconAlert } from '@/components/icons';
import type { Ask } from '@/mocks/community';
import { community } from '@/state/communityStore';

export function SetbackCard({ ask, viewerId }: { ask: Ask; viewerId: string }) {
  const setback = ask.setback;
  if (!setback) return null;
  const responses = Object.values(setback.responses);
  const stood = responses.filter((r) => r === 'STAND_BY').length;
  const mine = setback.responses[viewerId];
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2 border-b border-rule bg-restricted-tint/50 px-5 py-3 text-restricted-ink">
        <IconAlert size={16} />
        <p className="font-mono text-[11px] tracking-[0.12em]">SETBACK UPDATE · {setback.posted.toUpperCase()}</p>
      </div>
      <div className="p-5">
        <p className="text-[15px] leading-relaxed">“{setback.text}”</p>
        <p className="mt-2 text-[12px] text-ink-3">Reported by {ask.name.split(' ')[0]}; the purpose is not verified.</p>
        <div className="mt-4 flex items-center gap-1.5" aria-label={`${stood} of ${responses.length} vouchers stood by`}>
          {responses.map((r, i) => (
            <span
              key={i}
              className={`h-2 flex-1 rounded-full ${r === 'STAND_BY' ? 'bg-active' : r === 'STEP_BACK' ? 'bg-defaulted/40' : 'hatch'}`}
            />
          ))}
        </div>
        <p className="mt-2 text-[13px] text-ink-2">
          {stood} of {responses.length} vouchers stood by
        </p>
        {mine === 'PENDING' ? (
          <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-5 rounded-[10px] border border-neel-200 bg-neel-50 p-4">
            <p className="text-[14px] font-medium">You vouched for {ask.name.split(' ')[0]}. Do you stand by it?</p>
            <p className="mt-1 text-[12.5px] text-ink-2">
              Standing by keeps your stake on them. Stepping back frees it; nobody is told it was you.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button onClick={() => community.respond(ask.id, viewerId, 'STAND_BY')}>Stand by</Button>
              <Button variant="secondary" onClick={() => community.respond(ask.id, viewerId, 'STEP_BACK')}>
                Step back
              </Button>
            </div>
          </motion.div>
        ) : mine ? (
          <p className={`mt-4 text-[13px] font-medium ${mine === 'STAND_BY' ? 'text-active' : 'text-ink-3'}`}>
            {mine === 'STAND_BY' ? 'You stood by. Your vouch renews.' : 'You stepped back. Your stake is free again.'}
          </p>
        ) : null}
      </div>
    </div>
  );
}
