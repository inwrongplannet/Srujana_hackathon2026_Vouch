/**
 * Trust graph maths (graph-trust-engine skill). Decimal only; the visited set is per path.
 */
import { D, Decimal, PARAMS } from './params';

export interface GraphNode {
  id: string;
  kind: 'anchor' | 'person';
  R: Decimal;
}

export interface GraphEdge {
  from: string;
  to: string;
}

export interface TrustPath {
  /** Node ids from the anchor (index 0) to the target. */
  nodes: string[];
  trust: Decimal;
}

export const edgeKey = (from: string, to: string): string => `${from}>${to}`;

/** C_u = max(0, R_u). */
export function capacity(R: Decimal): Decimal {
  return Decimal.max(D(0), R);
}

/**
 * Out-degree conservation: W_uv = C_u / |Out(u)| for every v in Out(u), derived for all edges at once
 * so adding or removing one vouch re-weights every sibling atomically.
 */
export function edgeWeights(nodes: GraphNode[], edges: GraphEdge[]): Map<string, Decimal> {
  const R = new Map(nodes.map((n) => [n.id, n.R]));
  const outDegree = new Map<string, number>();
  for (const e of edges) outDegree.set(e.from, (outDegree.get(e.from) ?? 0) + 1);
  const weights = new Map<string, Decimal>();
  for (const e of edges) {
    const c = capacity(R.get(e.from) ?? D(0));
    weights.set(edgeKey(e.from, e.to), c.div(outDegree.get(e.from)!));
  }
  return weights;
}

export interface RGraphResult {
  total: Decimal;
  paths: TrustPath[];
  /** How many cycle re-entries were absorbed (each contributes zero). */
  absorbed: number;
}

/**
 * R_graph(T) = sum over simple anchor-to-T paths of Trust(P),
 * Trust(P) = W_{v0,v1} * prod_{i=1}^{k-1} (W_{vi,vi+1} * X).
 * The first hop is not decayed. Re-entering a node already on the current path yields zero.
 */
export function rGraph(
  target: string,
  nodes: GraphNode[],
  edges: GraphEdge[],
  weights: Map<string, Decimal> = edgeWeights(nodes, edges),
): RGraphResult {
  const out = new Map<string, string[]>();
  for (const e of edges) out.set(e.from, [...(out.get(e.from) ?? []), e.to]);

  const paths: TrustPath[] = [];
  let absorbed = 0;

  const walk = (current: string, visited: Set<string>, trust: Decimal, path: string[]): void => {
    if (current === target) {
      paths.push({ nodes: path, trust });
      return;
    }
    for (const next of out.get(current) ?? []) {
      if (visited.has(next)) {
        absorbed += 1;
        continue;
      }
      const w = weights.get(edgeKey(current, next)) ?? D(0);
      const hop = path.length === 1 ? w : w.mul(PARAMS.X);
      walk(next, new Set(visited).add(next), trust.mul(hop), [...path, next]);
    }
  };

  for (const anchor of nodes.filter((n) => n.kind === 'anchor')) {
    if (anchor.id === target) continue;
    walk(anchor.id, new Set([anchor.id]), D(1), [anchor.id]);
  }

  const total = paths.reduce((sum, p) => sum.plus(p.trust), D(0));
  paths.sort((a, b) => b.trust.cmp(a.trust));
  return { total, paths, absorbed };
}
