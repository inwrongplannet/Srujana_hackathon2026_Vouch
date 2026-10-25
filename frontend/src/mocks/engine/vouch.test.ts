import { describe, expect, it } from 'vitest';
import { D } from './params';
import { edgeWeight, scoreFromWeight, vouchScore, type Endorsement } from './vouch';

const edge = (reputation: number, reliability: string, utilisation: string, edgeQuality = '1'): Endorsement => ({
  reputation: D(reputation),
  reliability: D(reliability),
  utilisation: D(utilisation),
  edgeQuality: D(edgeQuality),
});

describe('vouch score', () => {
  it('matches the proposal worked example: W = 1.6 gives 41.3', () => {
    // 100 * (1 - e^(-1.6/3)) = 41.33 (Vouch scoring proposal, section 10).
    expect(scoreFromWeight(D('1.6')).toFixed(1)).toBe('41.3');
  });

  it('edge weight multiplies its factors', () => {
    // 0.8 * 0.9 * e^-0.5 * 1 = 0.43670...
    expect(edgeWeight(edge(80, '0.9', '0.5')).toFixed(4)).toBe('0.4367');
  });

  it('no endorsements is insufficient evidence, not zero', () => {
    const r = vouchScore([]);
    expect(r.status).toBe('INSUFFICIENT_VOUCH_EVIDENCE');
    expect(r.score).toBeNull();
  });

  it('has diminishing returns and stays under 100', () => {
    const one = vouchScore([edge(80, '0.9', '0')]).score!;
    const two = vouchScore([edge(80, '0.9', '0'), edge(80, '0.9', '0')]).score!;
    const many = vouchScore(Array.from({ length: 100 }, () => edge(80, '0.9', '0'))).score!;
    expect(two.minus(one).lt(one)).toBe(true);
    expect(many.lt(100)).toBe(true);
  });

  it('a penalised ring adds little', () => {
    const base = [edge(80, '0.9', '0.2')];
    const ring = Array.from({ length: 5 }, () => edge(50, '0.5', '0', '0.1'));
    const lift = vouchScore([...base, ...ring]).score!.minus(vouchScore(base).score!);
    expect(lift.lt(5)).toBe(true);
  });
});
