/**
 * The viewer vouches for a borrower, one of two ways. KNOWN: say how you know them. EVIDENCE: you
 * don't, but you read their verified summary and stake reputation on your judgement. Before the
 * hold, the composer shows the cost: points staked, the weight it will carry, the score change,
 * and the reputation won or lost on the outcome.
 */
import { useEffect, useState } from 'react';
import { backend, type VouchPreview } from '@/api/backend';
import { toApiId } from '@/api/communityAdapter';
import HoldButton from '@/components/bits/HoldButton';
import RubberSegment from '@/components/bits/RubberSegment';
import { IconCheck, IconVouch } from '@/components/icons';
import { fmt } from '@/lib/format';
import { D } from '@/mocks/engine/params';
import {
  JUDGE_MIN_RESOLVED,
  communityScore,
  rewardPreview,
  utilisation,
  weight,
  type Relationship,
  type Vouch,
  type VouchKind,
} from '@/mocks/engine/community';
import type { Ask } from '@/mocks/community';
import { community, useCommunity } from '@/state/communityStore';
import { recordLabel } from './parts';

const RELATIONSHIPS: { value: Relationship; label: string }[] = [
  { value: 'NEIGHBOUR', label: 'Neighbour' },
  { value: 'TRADE', label: 'We trade with each other' },
  { value: 'COLLEAGUE', label: 'Colleague' },
  { value: 'COMMUNITY', label: 'Same community or group' },
  { value: 'FAMILY', label: 'Family' },
];

function Stat({ label, value, tone = '' }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <p className="text-[12px] text-ink-3">{label}</p>
      <p className={`num mt-0.5 font-mono text-[15px] ${tone}`}>{value}</p>
    </div>
  );
}

export function VouchComposer({ ask, viewerId }: { ask: Ask; viewerId: string }) {
  const { members, source } = useCommunity();
  const me = members[viewerId]!;
  const knows = ask.knownBy.includes(viewerId);
  const [kind, setKind] = useState<VouchKind>(knows ? 'KNOWN' : 'EVIDENCE');
  const [relationship, setRelationship] = useState<Relationship>('NEIGHBOUR');
  const [years, setYears] = useState(9);
  const [stake, setStake] = useState(15);
  const [read, setRead] = useState(false);

  const already = ask.vouches.some((v) => v.voucherId === viewerId);
  const shown = ask.verified.filter((x) => x.shown);
  const vouch: Vouch = { voucherId: viewerId, kind, stake: D(stake), relationship, yearsKnown: years };
  const fits = utilisation(me, D(stake)) !== null;
  const w = weight(me, vouch);
  const local = {
    w,
    before: communityScore(members, ask.vouches).score,
    after: communityScore(members, [...ask.vouches, vouch]).score!,
    ...rewardPreview(w, ask.expectedRepay),
  };

  // Live, the preview is the backend's own (POST /vouch-preview); demo data uses the same formulas here.
  const [remote, setRemote] = useState<VouchPreview | null>(null);
  useEffect(() => {
    if (source !== 'live' || already) return;
    let alive = true;
    const t = window.setTimeout(() => {
      backend.community
        .preview(toApiId(ask.id), {
          voucher_id: toApiId(viewerId),
          kind,
          stake: String(stake),
          relationship: kind === 'KNOWN' ? relationship : undefined,
          years_known: kind === 'KNOWN' ? years : undefined,
          read_verified: kind === 'EVIDENCE' && read,
        })
        .then((r) => alive && setRemote(r))
        .catch(() => alive && setRemote(null));
    }, 250);
    return () => {
      alive = false;
      window.clearTimeout(t);
    };
  }, [source, already, ask.id, viewerId, kind, stake, relationship, years, read]);
  const preview =
    source === 'live' && remote
      ? {
          w: D(remote.weight),
          before: remote.score_before ? D(remote.score_before) : null,
          after: D(remote.score_after),
          gain: D(remote.gain_if_repaid),
          loss: D(remote.loss_if_default),
        }
      : local;

  if (already) {
    return (
      <div className="rounded-[10px] bg-active-tint/60 p-4 text-[14px]">
        <p className="font-medium text-active">You vouched for {ask.name.split(' ')[0]}.</p>
        <p className="mt-1 text-ink-2">Your stake stays committed until the loan settles or you step back after a setback.</p>
      </div>
    );
  }

  const evidenceBlocked = kind === 'EVIDENCE' && (shown.length === 0 || !read);
  const zeroWeight = preview.w.isZero();
  const disabled = !fits || evidenceBlocked;

  return (
    <div>
      <RubberSegment
        value={kind}
        onChange={(v) => setKind(v as VouchKind)}
        items={[
          { value: 'KNOWN', label: 'I know them' },
          { value: 'EVIDENCE', label: 'I read their file' },
        ]}
        trackColor="#E3DDCF"
        thumbColor="#FBFAF6"
        textColor="#464955"
        activeTextColor="#16181F"
        radius={10}
        aria-label="How you are vouching"
      />

      {kind === 'KNOWN' ? (
        <div className="mt-5 grid grid-cols-[1fr_96px] gap-3">
          <label className="text-[12.5px] text-ink-3">
            How do you know {ask.name.split(' ')[0]}?
            <select
              value={relationship}
              onChange={(e) => setRelationship(e.target.value as Relationship)}
              className="mt-1 h-10 w-full rounded-[7px] border border-rule-2 bg-surface px-2 text-[14px] text-ink"
            >
              {RELATIONSHIPS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[12.5px] text-ink-3">
            Years
            <input
              type="number"
              min={0}
              max={40}
              value={years}
              onChange={(e) => setYears(Math.max(0, Math.min(40, Number(e.target.value) || 0)))}
              className="mt-1 h-10 w-full rounded-[7px] border border-rule-2 bg-surface px-2 text-[14px] text-ink"
            />
          </label>
          {!knows ? (
            <p className="col-span-2 text-[12.5px] text-restricted-ink">
              Nobody in your circles is linked to {ask.name.split(' ')[0]}, so the lender sees this relationship as self-declared.
            </p>
          ) : null}
        </div>
      ) : (
        <div className="mt-5 space-y-3 text-[13px]">
          <p className="text-ink-2">
            Your judgement counts by your record: <span className="font-medium text-ink">{recordLabel(me)}</span>.
            {me.resolved < JUDGE_MIN_RESOLVED ? ` It counts fully after ${JUDGE_MIN_RESOLVED} outcomes.` : ''}
          </p>
          {shown.length ? (
            <label className="flex items-start gap-2.5 text-ink-2">
              <input type="checkbox" checked={read} onChange={(e) => setRead(e.target.checked)} className="mt-0.5 size-4 accent-[#24368F]" />
              I have read the {shown.length} verified items and I am staking my own reputation, not money.
            </label>
          ) : (
            <p className="text-restricted-ink">{ask.name.split(' ')[0]} has not shared anything verified with strangers yet.</p>
          )}
        </div>
      )}

      <label className="mt-5 block text-[12.5px] text-ink-3" htmlFor="stake">
        Points you stake · {fmt(me.budget.minus(me.committed).toString(), 0)} free of {fmt(me.budget.toString(), 0)}
      </label>
      <div className="mt-1 flex items-center gap-3">
        <input
          id="stake"
          type="range"
          min={5}
          max={25}
          value={stake}
          onChange={(e) => setStake(Number(e.target.value))}
          className="vt-range flex-1"
          style={{ ['--fill' as string]: `${((stake - 5) / 20) * 100}%` }}
        />
        <span className="num w-8 text-right font-mono text-[14px]">{stake}</span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4 rounded-[10px] border border-rule bg-paper-2/50 p-4">
        <Stat label="This vouch carries" value={`w ${fmt(preview.w.toString(), 2)}`} />
        <Stat
          label="Their score"
          value={`${preview.before ? fmt(preview.before.toString(), 0) : '—'} → ${fmt(preview.after.toString(), 0)}`}
        />
        <Stat label="If they repay" value={`+${fmt(preview.gain.toString(), 2)} rep`} tone="text-active" />
        <Stat label="If they default" value={`${fmt(preview.loss.toString(), 2)} rep`} tone="text-defaulted" />
        <p className="col-span-2 text-[12px] leading-relaxed text-ink-3">
          Comparable borrowers repay {fmt(ask.expectedRepay.mul(100).toString(), 0)}% of the time. The less expected the repayment, the more you
          earn for backing them.
        </p>
      </div>

      {!fits ? <p className="mt-3 text-[13px] text-defaulted">That stake is more than your free points.</p> : null}
      {zeroWeight && !disabled ? (
        <p className="mt-3 text-[13px] text-restricted-ink">With no record yet this vouch is logged but carries no weight.</p>
      ) : null}

      <div className="mt-5">
        <HoldButton
          key={`${kind}-${disabled}`}
          icon={<IconVouch size={18} />}
          doneIcon={<IconCheck size={18} />}
          doneLabel="Vouched"
          backgroundColor="#EBE6DB"
          fillColor="#24368F"
          textColor="#16181F"
          fillTextColor="#FBFAF6"
          size="lg"
          radius={10}
          holdTime={1200}
          glow={false}
          disabled={disabled}
          className="w-full"
          onHold={() => community.vouch(ask.id, vouch)}
        >
          Hold to vouch
        </HoldButton>
      </div>
    </div>
  );
}
