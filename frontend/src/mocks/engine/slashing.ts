/**
 * Damped default cascade and circuit breaker (slashing-cascade skill).
 * Penalties are computed together and applied in one state replacement, so no partial cascade is
 * ever observable.
 */
import { D, Decimal, PARAMS } from './params';
import { edgeKey, type GraphEdge } from './graph';

export interface Penalty {
  node: string;
  /** Distance from the defaulter: 0 defaulter, 1 direct sponsor, 2 transitive ancestor. */
  k: 0 | 1 | 2;
  delta: Decimal;
}

/**
 * k=0: delta0. k=1: gamma * W_AB * delta0 per direct sponsor A. k=2: gamma^2 * delta0 per ancestor
 * (once each, at its shortest distance). k>=3: nothing.
 */
export function cascade(
  defaulter: string,
  delta0: Decimal,
  edges: GraphEdge[],
  weights: Map<string, Decimal>,
): Penalty[] {
  const sponsorsOf = (id: string): string[] => edges.filter((e) => e.to === id).map((e) => e.from);

  const penalties: Penalty[] = [{ node: defaulter, k: 0, delta: delta0 }];
  const seen = new Set([defaulter]);

  const direct = sponsorsOf(defaulter).filter((a) => !seen.has(a));
  for (const a of direct) {
    seen.add(a);
    const w = weights.get(edgeKey(a, defaulter)) ?? D(0);
    penalties.push({ node: a, k: 1, delta: PARAMS.GAMMA.mul(w).mul(delta0) });
  }
  for (const a of direct) {
    for (const ancestor of sponsorsOf(a)) {
      if (seen.has(ancestor)) continue;
      seen.add(ancestor);
      penalties.push({ node: ancestor, k: 2, delta: PARAMS.GAMMA.pow(2).mul(delta0) });
    }
  }
  return penalties;
}

/**
 * The breaker trips when the share of a cluster already defaulted exceeds theta at the moment a new
 * default arrives; that default's slashes are queued instead of applied.
 */
export function breakerTrips(defaultedInCluster: number, clusterSize: number): boolean {
  if (clusterSize === 0) return false;
  return D(defaultedInCluster).div(clusterSize).gt(PARAMS.THETA);
}
