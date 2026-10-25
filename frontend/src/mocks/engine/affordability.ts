/**
 * Affordability stress test and repayment-plan search (docs/SPEC.md, section 4). INR, Decimal,
 * unrounded until presentation.
 *
 * A plan fits when, after an income fall, two constraints hold:
 *  - money left = income - essentials - existing obligations - EMI stays at or above zero, and
 *  - DTI = (existing obligations + EMI) / income stays at or below DTI_LIMIT (finance-domain DTI).
 */
import { D, Decimal } from './params';
import { emi } from './loan';

/** Demo policy cap on DTI; not set by a skill, logged in docs/DECISIONS.md. */
export const DTI_LIMIT = D('0.5');

export interface CashFlow {
  /** Average monthly income, INR. */
  income: Decimal;
  /** Monthly essentials including rent, INR. */
  essentials: Decimal;
  /** Monthly payments already owed (loans, chit funds), INR. */
  obligations: Decimal;
}

export interface Plan {
  principal: Decimal;
  annualRate: Decimal;
  months: number;
}

export interface PlanResult {
  plan: Plan;
  emi: Decimal;
  totalInterest: Decimal;
  /** Money left each month at the tested income fall; negative means the month does not close. */
  leftover: Decimal;
  dti: Decimal;
  fits: boolean;
  /** Smallest income fall (fraction, 0..1) at which either constraint breaks. */
  breaksAt: Decimal;
  /** Which constraint breaks first as income falls. */
  binding: 'leftover' | 'dti';
}

/** Mean, worst month and the worst month's fall below the mean, from monthly credits. */
export function incomeStats(credits: Decimal[]): { mean: Decimal; worst: Decimal; worstFall: Decimal } {
  const mean = credits.reduce((a, b) => a.plus(b), D(0)).div(credits.length);
  const worst = Decimal.min(...credits);
  return { mean, worst, worstFall: D(1).minus(worst.div(mean)) };
}

export function evaluatePlan(cf: CashFlow, plan: Plan, incomeFall: Decimal): PlanResult {
  const payment = emi(plan.principal, plan.annualRate, plan.months);
  const income = cf.income.mul(D(1).minus(incomeFall));
  const leftover = income.minus(cf.essentials).minus(cf.obligations).minus(payment);
  const dti = cf.obligations.plus(payment).div(income);
  const leftoverBreak = D(1).minus(cf.essentials.plus(cf.obligations).plus(payment).div(cf.income));
  const dtiBreak = D(1).minus(cf.obligations.plus(payment).div(DTI_LIMIT.mul(cf.income)));
  const binding = leftoverBreak.lte(dtiBreak) ? 'leftover' : 'dti';
  return {
    plan,
    emi: payment,
    totalInterest: payment.mul(plan.months).minus(plan.principal),
    leftover,
    dti,
    fits: leftover.gte(0) && dti.lte(DTI_LIMIT),
    breaksAt: Decimal.max(0, Decimal.min(leftoverBreak, dtiBreak)),
    binding,
  };
}

/**
 * Tests every candidate at the given income fall and picks one: the largest principal that fits,
 * then the lowest total interest. Returns null as the pick when nothing fits; re-dating payments is
 * not a candidate, because it cannot make an unaffordable loan safe.
 */
export function searchPlans(cf: CashFlow, candidates: Plan[], incomeFall: Decimal): { results: PlanResult[]; pick: PlanResult | null } {
  const results = candidates.map((p) => evaluatePlan(cf, p, incomeFall));
  const feasible = results
    .filter((r) => r.fits)
    .sort((a, b) => b.plan.principal.cmp(a.plan.principal) || a.totalInterest.cmp(b.totalInterest));
  return { results, pick: feasible[0] ?? null };
}
