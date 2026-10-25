import { describe, expect, it } from 'vitest';
import { D } from './params';
import { edgeWeights, rGraph, type GraphEdge, type GraphNode } from './graph';

const node = (id: string, R: string, kind: 'anchor' | 'person' = 'person'): GraphNode => ({ id, kind, R: D(R) });

describe('graph-trust-engine', () => {
  it('linear chain: anchor(R=10) -> A(R=4) -> B gives 10 * 4 * 0.5 = 20', () => {
    const nodes = [node('anc', '10', 'anchor'), node('A', '4'), node('B', '0')];
    const edges: GraphEdge[] = [{ from: 'anc', to: 'A' }, { from: 'A', to: 'B' }];
    expect(rGraph('B', nodes, edges).total.toString()).toBe('20');
  });

  it('absorbs a cycle back to the anchor without looping', () => {
    const nodes = [node('anc', '10', 'anchor'), node('A', '2'), node('B', '1')];
    const edges: GraphEdge[] = [
      { from: 'anc', to: 'A' },
      { from: 'A', to: 'B' },
      { from: 'B', to: 'anc' },
    ];
    const result = rGraph('B', nodes, edges);
    expect(result.total.toString()).toBe('10');
    expect(result.paths).toHaveLength(1);
  });

  it('counts a loop re-entry as absorbed with zero contribution', () => {
    const nodes = [node('anc', '4', 'anchor'), node('M', '2'), node('N', '1'), node('T', '0')];
    const edges: GraphEdge[] = [
      { from: 'anc', to: 'M' },
      { from: 'M', to: 'N' },
      { from: 'N', to: 'M' },
      { from: 'M', to: 'T' },
    ];
    const result = rGraph('T', nodes, edges);
    // anc -> M (4) -> T (2/2 * 0.5 = 0.5): 2. The M -> N -> M loop adds nothing.
    expect(result.total.toString()).toBe('2');
    expect(result.absorbed).toBe(1);
  });

  it('a node with R = 0 emits zero weight', () => {
    const nodes = [node('anc', '10', 'anchor'), node('Z', '0'), node('T', '0')];
    const edges: GraphEdge[] = [{ from: 'anc', to: 'Z' }, { from: 'Z', to: 'T' }];
    expect(rGraph('T', nodes, edges).total.toString()).toBe('0');
  });

  it('sums independent paths from two anchors', () => {
    const nodes = [node('a1', '6', 'anchor'), node('a2', '3', 'anchor'), node('T', '0')];
    const edges: GraphEdge[] = [{ from: 'a1', to: 'T' }, { from: 'a2', to: 'T' }];
    expect(rGraph('T', nodes, edges).total.toString()).toBe('9');
  });

  it('a third vouch from R = 9 re-weights all siblings to 3', () => {
    const nodes = [node('u', '9'), node('a', '0'), node('b', '0'), node('c', '0')];
    const edges: GraphEdge[] = [
      { from: 'u', to: 'a' },
      { from: 'u', to: 'b' },
      { from: 'u', to: 'c' },
    ];
    const w = edgeWeights(nodes, edges);
    expect([...w.values()].map((x) => x.toString())).toEqual(['3', '3', '3']);
  });
});
