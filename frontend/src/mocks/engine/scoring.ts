/**
 * Dual-axis underwriting (dual-axis-scoring skill): mu_composite, sigma2_epistem and the
 * lower-confidence-bound Score_final. Money is Decimal INR; nothing here rounds except the
 * presentation-only limit step.
 */
import { D, Decimal, PARAMS } from './params';

/** Monthly figures in INR, as decimal strings. */
export interface CashflowProfile {
  monthlyIncome: string[];
  netFlows: string[];
  obligations: string;
}

export interface DataSources {
  /** Account Aggregator statement linked (simulated). */
  aa: boolean;
  /** Utility payment cadence linked (simulated). */
  utility: boolean;
}

export interface CashflowMetrics {
  meanIncome: Decimal;
  incomeCv: Decimal;
  volatility: Decimal;
  dscr: Decimal;
  debtService: Decimal;
  sCashflow: Decimal;
}

export interface ScoreInputs {
  rGraph: Decimal;
  profile: CashflowProfile | null;
  sources: DataSources;
  nSettled: number;
  inDegree: number;
  proposedEmi: Decimal;
}

export interface Score {
  completeness: Decimal;
  nData: number;
  cashflow: CashflowMetrics | null;
  mu: Decimal;
  sigma2: Decimal;
  sigma: Decimal;
  lcb: Decimal;
  bandLow: Decimal;
  bandHigh: Decimal;
  /** Score_final * base unit, floored at zero; full precision. */
  limitRaw: Decimal;
  /** limitRaw rounded down to the presentation step. */
  limit: Decimal;
}

const mean = (xs: Decimal[]): Decimal => xs.reduce((s, x) => s.plus(x), D(0)).div(xs.length);

/** Population standard deviation. */
export function stddev(xs: Decimal[]): Decimal {
  const m = mean(xs);
  return mean(xs.map((x) => x.minus(m).pow(2))).sqrt();
}

/** Map x from [lo, hi] into [0, 1], clamped. */
export function normalise(x: Decimal, lo: Decimal, hi: Decimal): Decimal {
  return Decimal.min(D(1), Decimal.max(D(0), x.minus(lo).div(hi.minus(lo))));
}

/** Fraction of the expected assessment fields that are present (missing fields are never imputed). */
export function completenessOf(sources: DataSources, nSettled: number): Decimal {
  const present = (sources.aa ? 3 : 0) + (sources.utility ? 1 : 0) + (nSettled > 0 ? 1 : 0);
  return D(present).div(PARAMS.EXPECTED_FIELDS);
}

/**
 * S_cashflow = (w1*DSCR_norm + w2*(1 - instability_norm) + w3*(1 - volatility_norm)) * completeness.
 * DSCR = mean monthly net operating income / (existing obligations + proposed EMI).
 */
export function cashflowMetrics(
  profile: CashflowProfile,
  proposedEmi: Decimal,
  completeness: Decimal,
): CashflowMetrics {
  const incomes = profile.monthlyIncome.map(D);
  const flows = profile.netFlows.map(D);
  const meanIncome = mean(incomes);
  const incomeCv = stddev(incomes).div(meanIncome);
  const volatility = stddev(flows).div(mean(flows.map((f) => f.abs())));
  const debtService = D(profile.obligations).plus(proposedEmi);
  const dscr = debtService.isZero() ? PARAMS.DSCR_MAX : meanIncome.div(debtService);
  const sCashflow = PARAMS.W1.mul(normalise(dscr, PARAMS.DSCR_MIN, PARAMS.DSCR_MAX))
    .plus(PARAMS.W2.mul(D(1).minus(normalise(incomeCv, D(0), PARAMS.INCOME_CV_MAX))))
    .plus(PARAMS.W3.mul(D(1).minus(normalise(volatility, D(0), PARAMS.VOLATILITY_MAX))))
    .mul(completeness);
  return { meanIncome, incomeCv, volatility, dscr, debtService, sCashflow };
}

export function score(input: ScoreInputs): Score {
  const completeness = completenessOf(input.sources, input.nSettled);
  const nData = (input.sources.aa ? 1 : 0) + (input.sources.utility ? 1 : 0) + input.nSettled;
  const cashflow =
    input.sources.aa && input.profile
      ? cashflowMetrics(input.profile, input.proposedEmi, completeness)
      : null;
  const sCashflow = cashflow?.sCashflow ?? D(0);

  const mu = PARAMS.ALPHA.mul(input.rGraph)
    .plus(D(1).minus(PARAMS.ALPHA).mul(sCashflow))
    .mul(PARAMS.BETA.mul(input.nSettled + input.inDegree).exp());
  const sigma2 = D(1).div(D(1).plus(D(nData).mul(completeness)));
  const sigma = sigma2.sqrt();
  const spread = PARAMS.KAPPA.mul(sigma);
  const lcb = mu.minus(spread);
  const limitRaw = Decimal.max(D(0), lcb).mul(PARAMS.BASE_UNIT_INR);
  const limit = limitRaw.div(PARAMS.LIMIT_STEP_INR).floor().mul(PARAMS.LIMIT_STEP_INR);

  return {
    completeness,
    nData,
    cashflow,
    mu,
    sigma2,
    sigma,
    lcb,
    bandLow: mu.minus(spread),
    bandHigh: mu.plus(spread),
    limitRaw,
    limit,
  };
}
