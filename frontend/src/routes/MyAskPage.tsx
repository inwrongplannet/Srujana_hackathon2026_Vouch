import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { PersonMark, ScoreBlock, VerifiedRow, VouchList } from '@/features/community/parts';
import { BORROWER_ID } from '@/mocks/community';
import { community, useCommunity } from '@/state/communityStore';

/** Lakshmi's side: choose what strangers may see, follow who vouched, and post a setback if one comes. */
export function MyAskPage() {
  const { asks, members } = useCommunity();
  const ask = asks.find((a) => a.ownerId === BORROWER_ID)!;
  const [draft, setDraft] = useState('');
  const shown = ask.verified.filter((x) => x.shown);

  return (
    <div>
      <p className="font-mono text-[11.5px] tracking-[0.16em] text-neel-700">MY ASK · BORROWER VIEW</p>
      <h1 className="display mt-2 text-[clamp(30px,3.6vw,44px)] leading-[1.04]">{ask.purpose}</h1>
      <p className="mt-1 text-[15px] text-ink-2">
        {ask.amountBand} · posted to {ask.circle} and the public feed
      </p>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_1fr] lg:items-start">
        <div className="space-y-5">
          <div className="card p-6">
            <p className="eyebrow">What strangers can see</p>
            <p className="mt-1 text-[13px] text-ink-3">
              People who know you can vouch whatever you share. Strangers can only judge what you switch on here.
            </p>
            <ul className="ruled mt-4">
              {ask.verified.map((item) => (
                <li key={item.key} className="flex items-start justify-between gap-4 py-3">
                  <ul className="flex-1">
                    <VerifiedRow item={item} />
                  </ul>
                  <label className="inline-flex shrink-0 cursor-pointer items-center gap-2 text-[12.5px] text-ink-2">
                    <input
                      type="checkbox"
                      checked={item.shown}
                      onChange={(e) => community.setShown(ask.id, item.key, e.target.checked)}
                      className="size-4 accent-[#24368F]"
                    />
                    {item.shown ? 'Shown' : 'Private'}
                  </label>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-[12px] text-ink-3">
              {shown.length} of {ask.verified.length} shown. Statements and exact income are never shown to anyone on the platform.
            </p>
          </div>

          <div className="card p-6">
            <p className="eyebrow">If something goes wrong</p>
            {ask.setback ? (
              <p className="mt-2 text-[14px] text-ink-2">
                Setback posted {ask.setback.posted}. {Object.values(ask.setback.responses).filter((r) => r === 'STAND_BY').length} of{' '}
                {Object.keys(ask.setback.responses).length} vouchers have stood by so far.
              </p>
            ) : (
              <>
                <p className="mt-2 text-[13.5px] text-ink-2">
                  A bill, a slow season, a missed EMI: tell the people who vouched for you before the bureau does. They choose to stand by or
                  step back, and the lender sees how many stood by.
                </p>
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={3}
                  placeholder="What happened, and what you are doing about it"
                  className="mt-3 w-full rounded-[8px] border border-rule-2 bg-surface p-3 text-[14px]"
                />
                <Button className="mt-3" disabled={draft.trim().length < 10} onClick={() => community.postSetback(ask.id, draft.trim())}>
                  Post to my vouchers
                </Button>
              </>
            )}
          </div>
        </div>

        <div className="space-y-5">
          <div className="card p-6">
            <div className="flex items-center gap-3">
              <PersonMark name={ask.name} size={44} />
              <div>
                <p className="display text-[22px] leading-tight">{ask.name}</p>
                <p className="text-[13px] text-ink-3">
                  {ask.trade} · {ask.circle}
                </p>
              </div>
            </div>
            <div className="mt-5">
              <ScoreBlock ask={ask} members={members} />
            </div>
          </div>
          <div className="card p-6">
            <p className="eyebrow">Who vouched for you</p>
            <div className="mt-2">
              <VouchList vouches={ask.vouches} members={members} setback={ask.setback} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
