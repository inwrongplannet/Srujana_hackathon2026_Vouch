import { describe, expect, it } from 'vitest';
import { D } from './params';
import { score, stddev } from './scoring';
import { emi } from './loan';

const noData = { aa: false, utility: false };

describe('dual-axis-scoring', () => {
  it('cold start: mu 0, sigma2 1.0, Score_final -1, limit 0', () => {
    const s = score({ rGraph: D(0), profile: null, sources: noData, nSettled: 0, inDegree: 0, proposedEmi: D(0) });
    expect(s.mu.toString()).toBe('0');
    expect(s.sigma2.toString()).toBe('1');
    expect(s.lcb.toString()).toBe('-1');
    expect(s.limit.toString()).toBe('0');
  });

  it('thin file: R_graph 2, one vouch, no data -> mu = 1.2 * e^0.1, Score_final = mu - 1', () => {
    const s = score({ rGraph: D(2), profile: null, sources: noData, nSettled: 0, inDegree: 1, proposedEmi: D(0) });
    expect(s.sigma2.toString()).toBe('1');
    expect(s.mu.toDecimalPlaces(10).toString()).toBe('1.3262051017');
    expect(s.lcb.toDecimalPlaces(10).toString()).toBe('0.3262051017');
    // 0.3262... * 10,000 INR, shown rounded down to a 500 step.
    expect(s.limit.toString()).toBe('3000');
  });

  it('rich file: five data sources at full completeness give sigma2 = 1/6', () => {
    const profile = {
      monthlyIncome: ['20000', '20000', '20000', '20000'],
      netFlows: ['5000', '5000', '5000', '5000'],
      obligations: '8000',
    };
    const s = score({ rGraph: D(40), profile, sources: { aa: true, utility: true }, nSettled: 3, inDegree: 4, proposedEmi: D(0) });
    expect(s.completeness.toString()).toBe('1');
    expect(s.sigma2.toDecimalPlaces(12).toString()).toBe('0.166666666667');
    // Flat income and flows: no instability, no volatility. DSCR 2.5 -> normalised 1. S_cf = 1.
    expect(s.cashflow!.sCashflow.toString()).toBe('1');
    // mu = (0.6*40 + 0.4*1) * e^0.7
    expect(s.mu.toDecimalPlaces(8).toString()).toBe('49.13556606');
  });

  it('more graph trust raises mu (alpha weighting is monotonic)', () => {
    const base = { profile: null, sources: noData, nSettled: 0, inDegree: 1, proposedEmi: D(0) };
    expect(score({ ...base, rGraph: D(3) }).mu.gt(score({ ...base, rGraph: D(2) }).mu)).toBe(true);
  });

  it('population standard deviation of a textbook series is 2', () => {
    expect(stddev(['2', '4', '4', '4', '5', '5', '7', '9'].map(D)).toString()).toBe('2');
  });
});

describe('finance-domain EMI', () => {
  it('INR 5,000 at 24% a.p.r. over 6 months is INR 892.63 a month', () => {
    expect(emi(D(5000), D('0.24'), 6).toDecimalPlaces(2).toString()).toBe('892.63');
  });
  it('zero rate divides evenly', () => {
    expect(emi(D(6000), D(0), 6).toString()).toBe('1000');
  });
});
