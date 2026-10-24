/**
 * Loan arithmetic (finance-domain skill). INR, Decimal, unrounded until presentation.
 */
import { D, Decimal, PARAMS } from './params';

/**
 * EMI = P*i*(1+i)^n / ((1+i)^n - 1) for periodic rate i over n periods; P/n when i = 0.
 */
export function emi(principal: Decimal, annualRate: Decimal, months: number): Decimal {
  const i = annualRate.div(12);
  if (i.isZero()) return principal.div(months);
  const growth = D(1).plus(i).pow(months);
  return principal.mul(i).mul(growth).div(growth.minus(1));
}

/** EMI for a demo micro-loan at the standard pricing. */
export function demoEmi(principal: Decimal): Decimal {
  return emi(principal, PARAMS.LOAN_APR, PARAMS.LOAN_TENOR_MONTHS);
}

/** delta0, the primary slash for a default on this principal. */
export function delta0For(principal: Decimal): Decimal {
  return principal.div(PARAMS.DELTA0_PER_INR);
}
