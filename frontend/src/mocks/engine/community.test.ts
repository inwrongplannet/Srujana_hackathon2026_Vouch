import { describe, expect, it } from 'vitest';
import { D } from './params';
import { communityScore, quality, reliability, rewardPreview, staked, trackRecord, utilisation, weight, type Member } from './community';

const member = (resolved: number, repaid: number, committed = '0'): Member => ({
  id: 'm',
  name: 'M',
  line: '',
  reputation: D(80),
  budget: D(100),
  committed: D(committed),
  resolved,
  repaid,
});

describe('community vouching', () => {
  it('track record is smoothed: no record is 0.5, 6 of 7 is 7/9', () => {
    expect(trackRecord(member(0, 0)).toFixed(4)).toBe('0.5000');
    expect(trackRecord(member(7, 6)).toFixed(4)).toBe('0.7778');
  });

  it('an evidence vouch counts only once the voucher has a record', () => {
    expect(reliability(member(0, 0), 'EVIDENCE').toFixed(4)).toBe('0.0000');
    // 2 of 5 needed outcomes: 0.75 * 0.4 = 0.30.
    expect(reliability(member(2, 2), 'EVIDENCE').toFixed(4)).toBe('0.3000');
    expect(reliability(member(7, 6), 'EVIDENCE').toFixed(4)).toBe('0.7778');
  });

  it('relationship quality grows with years known', () => {
    // Neighbour 0.80 x (0.6 + 0.4 * 9/10) = 0.768.
    expect(quality({ voucherId: 'm', kind: 'KNOWN', stake: D(10), relationship: 'NEIGHBOUR', yearsKnown: 9 }).toFixed(4)).toBe('0.7680');
  });

  it('refuses a stake over budget', () => {
    expect(utilisation(member(0, 0, '95'), D(10))).toBeNull();
    expect(utilisation(member(0, 0, '35'), D(15))!.toFixed(2)).toBe('0.50');
  });

  it('known weight: R/100 * h * e^-U * g', () => {
    // 0.8 * (7/9) * e^-0.5 * 0.768 = 0.28979...
    const w = weight(member(7, 6, '35'), { voucherId: 'm', kind: 'KNOWN', stake: D(15), relationship: 'NEIGHBOUR', yearsKnown: 9 });
    expect(w.toFixed(4)).toBe('0.2898');
  });

  it('evidence counts up to 0.6 plus two-thirds of the known weight', () => {
    const members = { s: member(20, 20), k: member(20, 20) };
    const strangers = Array.from({ length: 10 }, () => ({ voucherId: 's', kind: 'EVIDENCE' as const, stake: D(5) }));
    const alone = communityScore(members, strangers);
    expect(alone.evidenceCounted.toFixed(2)).toBe('0.60');
    const mixed = communityScore(members, [...strangers, { voucherId: 'k', kind: 'KNOWN', stake: D(5), relationship: 'TRADE', yearsKnown: 10 }]);
    expect(mixed.evidenceCounted.toFixed(4)).toBe(D('0.6').plus(mixed.known.mul(2).div(3)).toFixed(4));
    expect(mixed.score!.gt(alone.score!)).toBe(true);
  });

  it('no vouches is no score, not zero', () => {
    expect(communityScore({}, []).score).toBeNull();
  });

  it('backing an underrated borrower earns more than a safe bet', () => {
    // 100 * 0.1 * 0.5 * (1 - 0.80) = 1.0 points; safe bet at 0.95 gives 0.25.
    expect(rewardPreview(D('0.5'), D('0.80')).gain.toFixed(2)).toBe('1.00');
    expect(rewardPreview(D('0.5'), D('0.95')).gain.toFixed(2)).toBe('0.25');
    expect(rewardPreview(D('0.5'), D('0.80')).loss.toFixed(2)).toBe('-4.00');
  });

  it('a vouch keeps the utilisation it was staked at', () => {
    const m = member(7, 6, '35');
    const v = staked(m, { voucherId: 'm', kind: 'KNOWN', stake: D(15), relationship: 'NEIGHBOUR', yearsKnown: 9 });
    const before = weight(m, v);
    expect(weight({ ...m, committed: D(80) }, v).eq(before)).toBe(true);
  });
});
