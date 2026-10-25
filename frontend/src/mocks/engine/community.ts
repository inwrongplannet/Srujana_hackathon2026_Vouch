/**
 * Hybrid vouching for the community platform: a KNOWN vouch (I know this person) and an EVIDENCE
 * vouch (I don't, but I read their verified data and stake my reputation on it). Decimal throughout.
 *
 * Both use the Vouch proposal's edge weight, w = R/100 * h * exp(-lambda * U) * g, and score,
 * S = 100 * (1 - exp(-W / tau)), but h and g mean different things:
 *  - KNOWN: h is the voucher's smoothed track record; g comes from the relationship and how long
 *    they have known each other. It adds private knowledge no dataset has.
 *  - EVIDENCE: the voucher adds no new facts (the lender sees the same data), only judgement, so h
 *    is the track record shrunk to zero until JUDGE_MIN_RESOLVED outcomes exist, g is a flat
 *    EVIDENCE_QUALITY, and evidence weight is capped (EVIDENCE_ONLY_CAP plus EVIDENCE_TO_KNOWN of the
 *    known weight) so strangers cannot carry a score; the cap only rises as known vouches arrive.
 * Constants are demo values logged in docs/DECISIONS.md.
 */
import { D, Decimal } from './params';
import { LAMBDA, TAU } from './vouch';

export type VouchKind = 'KNOWN' | 'EVIDENCE';
export type Relationship = 'FAMILY' | 'NEIGHBOUR' | 'COLLEAGUE' | 'TRADE' | 'COMMUNITY';

export const RELATIONSHIP_QUALITY: Record<Relationship, Decimal> = {
  FAMILY: D('0.65'),
  NEIGHBOUR: D('0.80'),
  COLLEAGUE: D('0.85'),
  TRADE: D('0.85'),
  COMMUNITY: D('0.80'),
};
export const EVIDENCE_QUALITY = D('0.60');
export const JUDGE_MIN_RESOLVED = 5;
/** Evidence weight counts up to this much on its own... */
export const EVIDENCE_ONLY_CAP = D('0.60');
/** ...plus this multiple of the known weight. */
export const EVIDENCE_TO_KNOWN = D(2).div(3);
export const LEARNING_RATE = D('0.10');

export interface Member {
  id: string;
  name: string;
  line: string;
  reputation: Decimal;   // R, 0..100
  budget: Decimal;       // reputation points available to stake
  committed: Decimal;    // points already staked elsewhere
  resolved: number;      // past vouches with a verified outcome
  repaid: number;        // of those, repaid
}

export interface Vouch {
  voucherId: string;
  kind: VouchKind;
  stake: Decimal;
  relationship?: Relationship;
  yearsKnown?: number;
  /** U fixed when the stake was made; later stakes by the same voucher do not reweight it. */
  utilisation?: Decimal;
}

/** Smoothed share of past vouches that repaid: (repaid + 1) / (resolved + 2); 0.5 with no record. */
export function trackRecord(m: Member): Decimal {
  return D(m.repaid + 1).div(m.resolved + 2);
}

/** h for the vouch kind. Evidence counts only once the voucher has a record to judge them by. */
export function reliability(m: Member, kind: VouchKind): Decimal {
  const record = trackRecord(m);
  if (kind === 'KNOWN') return record;
  return record.mul(Decimal.min(1, D(m.resolved).div(JUDGE_MIN_RESOLVED)));
}

/** g: relationship quality, rising from 60% to 100% of it over the first ten years known. */
export function quality(v: Vouch): Decimal {
  if (v.kind === 'EVIDENCE') return EVIDENCE_QUALITY;
  const base = RELATIONSHIP_QUALITY[v.relationship ?? 'COMMUNITY'];
  const years = Decimal.min(10, D(v.yearsKnown ?? 0));
  return base.mul(D('0.6').plus(years.div(10).mul('0.4')));
}

/** Utilisation after staking this vouch, U = (committed + stake) / budget, or null if over budget. */
export function utilisation(m: Member, stake: Decimal): Decimal | null {
  const after = m.committed.plus(stake);
  return after.gt(m.budget) ? null : after.div(m.budget);
}

/** Fixes U at staking time, so the vouch keeps the weight it had when it was given. */
export function staked(m: Member, v: Vouch): Vouch {
  return { ...v, utilisation: utilisation(m, v.stake) ?? D(1) };
}

export function weight(m: Member, v: Vouch): Decimal {
  const u = v.utilisation ?? utilisation(m, v.stake) ?? D(1);
  return m.reputation.div(100).mul(reliability(m, v.kind)).mul(LAMBDA.neg().mul(u).exp()).mul(quality(v));
}

export interface CommunityScore {
  score: Decimal | null;   // null: no vouches yet, which is "insufficient evidence", never 0
  known: Decimal;
  evidence: Decimal;       // raw evidence weight
  evidenceCounted: Decimal; // after the cap
  total: Decimal;
}

export function communityScore(members: Record<string, Member>, vouches: Vouch[]): CommunityScore {
  let known = D(0);
  let evidence = D(0);
  for (const v of vouches) {
    const w = weight(members[v.voucherId]!, v);
    if (v.kind === 'KNOWN') known = known.plus(w);
    else evidence = evidence.plus(w);
  }
  const cap = EVIDENCE_ONLY_CAP.plus(known.mul(EVIDENCE_TO_KNOWN));
  const evidenceCounted = Decimal.min(evidence, cap);
  const total = known.plus(evidenceCounted);
  return {
    score: vouches.length ? D(100).mul(D(1).minus(total.neg().div(TAU).exp())) : null,
    known,
    evidence,
    evidenceCounted,
    total,
  };
}

/**
 * Reputation at stake, in points (0..100 scale): repaid gives 100 * lr * w * (1 - p), a default
 * gives 100 * lr * w * (0 - p). Backing someone everyone expects to repay earns little; backing an
 * underrated borrower who repays earns the most.
 */
export function rewardPreview(w: Decimal, expectedRepay: Decimal): { gain: Decimal; loss: Decimal } {
  const scaled = D(100).mul(LEARNING_RATE).mul(w);
  return { gain: scaled.mul(D(1).minus(expectedRepay)), loss: scaled.mul(expectedRepay).neg() };
}
