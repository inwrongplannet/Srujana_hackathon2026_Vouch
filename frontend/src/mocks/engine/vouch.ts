/**
 * Vouch Score, as proposed in the Vouch scoring proposal (sections 4.1 to 4.3). Decimal throughout.
 *
 *   w_ji = (R_j / 100) * h_j * exp(-lambda * U_j) * g_ji      effective weight of one endorsement
 *   W_i  = sum of w_ji over eligible endorsers
 *   S_i  = 100 * (1 - exp(-W_i / tau))                        diminishing returns, bounded 0..100
 *
 * No eligible endorsement returns no score ("insufficient vouch evidence"), never 0. The score is
 * not a repayment probability. tau and lambda are the proposal's untuned starting values.
 */
import { D, Decimal } from './params';

export const TAU = D(3);
export const LAMBDA = D(1);

export interface Endorsement {
  /** Endorser reputation R_j, 0..100. */
  reputation: Decimal;
  /** Endorser historical reliability h_j, 0..1. */
  reliability: Decimal;
  /** Share of the endorser's reputation budget already committed, U_j, 0..1. */
  utilisation: Decimal;
  /** Verified edge quality g_ji, 0..1; an abuse penalty (ring, duplicate) lowers it. */
  edgeQuality: Decimal;
}

const clamp = (v: Decimal, lo: Decimal.Value, hi: Decimal.Value) => Decimal.min(Decimal.max(v, lo), hi);

export function edgeWeight(e: Endorsement): Decimal {
  return clamp(e.reputation, 0, 100)
    .div(100)
    .mul(clamp(e.reliability, 0, 1))
    .mul(Decimal.exp(LAMBDA.neg().mul(clamp(e.utilisation, 0, 1))))
    .mul(clamp(e.edgeQuality, 0, 1));
}

export type VouchResult =
  | { status: 'SCORED'; score: Decimal; totalWeight: Decimal }
  | { status: 'INSUFFICIENT_VOUCH_EVIDENCE'; score: null; totalWeight: Decimal };

export function scoreFromWeight(totalWeight: Decimal): Decimal {
  return D(100).mul(D(1).minus(Decimal.exp(totalWeight.neg().div(TAU))));
}

export function vouchScore(eligible: Endorsement[]): VouchResult {
  const totalWeight = eligible.reduce((sum, e) => sum.plus(edgeWeight(e)), D(0));
  if (eligible.length === 0) return { status: 'INSUFFICIENT_VOUCH_EVIDENCE', score: null, totalWeight };
  return { status: 'SCORED', score: scoreFromWeight(totalWeight), totalWeight };
}
