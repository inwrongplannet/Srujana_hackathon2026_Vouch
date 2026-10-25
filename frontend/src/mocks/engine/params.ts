/**
 * Protocol and demo parameters for the mock engine.
 *
 * The mock engine stands in for the backend until it exists: all maths lives here, never in UI
 * components. Protocol constants are copied from the graph-trust-engine, dual-axis-scoring and
 * slashing-cascade skills. Values marked "demo" are not defined by those skills and are logged in
 * docs/DECISIONS.md.
 */
import Decimal from 'decimal.js';

// 40 significant digits, banker's rounding (finance-domain: ledgers use ROUND_HALF_EVEN).
Decimal.set({ precision: 40, rounding: Decimal.ROUND_HALF_EVEN });

export { Decimal };
export const D = (v: Decimal.Value): Decimal => new Decimal(v);

export const PARAMS = {
  /** Hop decay factor X (graph-trust-engine). */
  X: D('0.5'),
  /** Weight of graph trust against cash-flow score (dual-axis-scoring). */
  ALPHA: D('0.6'),
  /** Reputation multiplier for settled loans plus incoming vouches (dual-axis-scoring). */
  BETA: D('0.1'),
  /** Uncertainty penalty in the lower confidence bound (dual-axis-scoring). */
  KAPPA: D('1.0'),
  /** Cash-flow sub-score weights w1 (DSCR), w2 (income stability), w3 (volatility). */
  W1: D('0.5'),
  W2: D('0.3'),
  W3: D('0.2'),
  /** Cascade damping gamma (slashing-cascade). */
  GAMMA: D('0.5'),
  /** Circuit-breaker cluster default-rate threshold theta (slashing-cascade). */
  THETA: D('0.3'),

  /** demo: INR of credit per point of Score_final. */
  BASE_UNIT_INR: D('10000'),
  /** demo: limits are shown rounded down to this step (presentation only). */
  LIMIT_STEP_INR: D('500'),
  /** demo: primary slash delta0 = principal / this many INR. */
  DELTA0_PER_INR: D('5000'),
  /** demo: credibility minted to a borrower on settlement, as a fraction of delta0. */
  SETTLE_MINT: D('0.5'),
  /** demo: reputation yield to each direct sponsor on settlement, as a fraction of delta0. */
  SPONSOR_YIELD: D('0.1'),
  /** demo: normalisation ranges for cash-flow metrics (map to [0, 1]). */
  DSCR_MIN: D('0.5'),
  DSCR_MAX: D('2.5'),
  INCOME_CV_MAX: D('0.6'),
  VOLATILITY_MAX: D('1.0'),
  /** demo: fields an assessment expects (income, obligations, net flows, utility cadence, repayments). */
  EXPECTED_FIELDS: 5,
  /** demo: micro-loan pricing, 24% a.p.r. reducing balance, monthly, 6 instalments. */
  LOAN_APR: D('0.24'),
  LOAN_TENOR_MONTHS: 6,
  /** demo: grace window before LoanEscrow declares a default. */
  LOAN_TERM_DAYS: 30,
} as const;
