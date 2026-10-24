import { describe, expect, it } from 'vitest';
import { D } from './params';
import { breakerTrips, cascade } from './slashing';
import type { GraphEdge } from './graph';

describe('slashing-cascade', () => {
  it('skill example: delta0 10, W_AB 0.4 -> B -10, A -2.0, ancestor -2.5, hop 3 untouched', () => {
    const edges: GraphEdge[] = [
      { from: 'far', to: 'anc' },
      { from: 'anc', to: 'A' },
      { from: 'A', to: 'B' },
    ];
    const weights = new Map([['A>B', D('0.4')]]);
    const p = cascade('B', D(10), edges, weights);
    const byNode = Object.fromEntries(p.map((x) => [x.node, x]));
    expect(byNode.B.delta.toString()).toBe('10');
    expect(byNode.A.delta.toString()).toBe('2');
    expect(byNode.A.k).toBe(1);
    expect(byNode.anc.delta.toString()).toBe('2.5');
    expect(byNode.anc.k).toBe(2);
    expect(byNode.far).toBeUndefined();
  });

  it('penalises an ancestor once even when it reaches the defaulter by two sponsors', () => {
    const edges: GraphEdge[] = [
      { from: 'anc', to: 'A1' },
      { from: 'anc', to: 'A2' },
      { from: 'A1', to: 'B' },
      { from: 'A2', to: 'B' },
    ];
    const p = cascade('B', D(4), edges, new Map());
    expect(p.filter((x) => x.node === 'anc')).toHaveLength(1);
  });

  it('circuit breaker: 2 of 5 already defaulted (40% > 30%) trips; 1 of 5 does not', () => {
    expect(breakerTrips(1, 5)).toBe(false);
    expect(breakerTrips(2, 5)).toBe(true);
  });
});
