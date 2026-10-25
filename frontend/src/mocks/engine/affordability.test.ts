import { describe, expect, it } from 'vitest';
import { D } from './params';
import { evaluatePlan, incomeStats, searchPlans, type CashFlow } from './affordability';

const cf: CashFlow = { income: D(38000), essentials: D(20500), obligations: D(2000) };
const plan = (principal: number, months: number) => ({ principal: D(principal), annualRate: D('0.24'), months });

describe('affordability', () => {
  it('EMI and interest match the amortization table', () => {
    // ₹1,50,000 at 24% a year (2% a month) over 12 months: EMI ₹14,183.94, interest ₹20,207.27
    // (cross-checked with Python Decimal).
    const r = evaluatePlan(cf, plan(150000, 12), D(0));
    expect(r.emi.toFixed(2)).toBe('14183.94');
    expect(r.totalInterest.toFixed(2)).toBe('20207.27');
    expect(r.leftover.toFixed(2)).toBe('1316.06');
    expect(r.fits).toBe(true);
  });

  it('finds the income fall that breaks the plan', () => {
    // 1 - (20500 + 2000 + 14183.90) / 38000 = 0.0346...
    const r = evaluatePlan(cf, plan(150000, 12), D(0));
    expect(r.breaksAt.toFixed(4)).toBe('0.0346');
    expect(r.binding).toBe('leftover');
    expect(evaluatePlan(cf, plan(150000, 12), D('0.05')).fits).toBe(false);
  });

  it('DTI binds when obligations are heavy', () => {
    const heavy: CashFlow = { income: D(40000), essentials: D(4000), obligations: D(15000) };
    const r = evaluatePlan(heavy, plan(50000, 12), D(0));
    // EMI ₹4,727.98; DTI (15000 + 4727.98) / 40000 = 0.4932 fits, and breaks at a 1.36% fall.
    expect(r.binding).toBe('dti');
    expect(r.fits).toBe(true);
    expect(r.breaksAt.toFixed(4)).toBe('0.0136');
  });

  it('picks the largest principal that fits, then the cheapest', () => {
    const { pick } = searchPlans(cf, [plan(150000, 12), plan(150000, 18), plan(150000, 24), plan(120000, 18)], D('0.16'));
    expect(pick?.plan.months).toBe(24);
    expect(pick?.plan.principal.toNumber()).toBe(150000);
  });

  it('reports no plan when nothing fits', () => {
    expect(searchPlans(cf, [plan(150000, 12)], D('0.3')).pick).toBeNull();
  });

  it('income stats', () => {
    const s = incomeStats([D(40000), D(30000), D(50000)]);
    expect(s.mean.toFixed(0)).toBe('40000');
    expect(s.worstFall.toFixed(2)).toBe('0.25');
  });
});
