/**
 * What each figure on screen means and how it is computed, for the hover explanations. Every
 * entry is copied from the code that produces the figure, never from a spec: backend figures from
 * `backend/src/veritrust/`, story and community figures from `src/mocks/engine/` (the community
 * maths is mirrored in `backend/src/veritrust/community.py`). When a formula changes there, change
 * it here.
 */

export type Engine = 'backend' | 'demo engine' | 'backend and demo engine';

export interface Formula {
  title: string;
  engine: Engine;
  /** One formula per line, in plain Unicode. */
  formula: string[];
  /** Symbol, then what it stands for. */
  terms?: [string, string][];
  note?: string;
  source: string;
}

export const FORMULAS = {
  // Assessment desk: the backend.
  vouchScore: {
    title: 'Vouch Score',
    engine: 'backend',
    formula: ['V = 100 × (1 − e^(−W/τ)) × (0.35 + 0.65·C)'],
    terms: [
      ['W', 'sum over incoming vouches of edge weight × rank factor α × voucher credibility'],
      ['credibility', 'min(1, R/10) × 1.00 for an institution, 0.85 for a person; 0 if the voucher is not active'],
      ['τ', '3, so each extra vouch adds less than the one before'],
      ['C', 'outcome quality of the vouchers (below)'],
    ],
    note: 'Bounded 0 to 100. No vouches means missing evidence, not risk.',
    source: 'backend/src/veritrust/scoring.py · compute_vouch_score',
  },
  endorsements: {
    title: 'Endorsements and confidence',
    engine: 'backend',
    formula: ['high: 3 or more vouches and W ≥ 2', 'medium: at least 1 vouch', 'low: none'],
    note: 'Counts every incoming vouch from the trust graph.',
    source: 'backend/src/veritrust/scoring.py · compute_vouch_score',
  },
  outcomeQuality: {
    title: 'Outcome quality C',
    engine: 'backend',
    formula: ['C = (settled + 1) / (settled + defaulted + 2)'],
    terms: [
      ['settled', 'loans the vouchers repaid'],
      ['defaulted', 'vouchers who defaulted'],
    ],
    note: 'Laplace smoothing: 0.50 with no record, rising as vouchers repay.',
    source: 'backend/src/veritrust/scoring.py · compute_vouch_score',
  },
  buffer: {
    title: 'Cash kept aside',
    engine: 'backend',
    formula: ['B = max(₹3,000, 15% × I) × m'],
    terms: [
      ['I', 'monthly income'],
      ['m', '1.00 when verified and at least 85% complete, 1.15 when at least 50% complete, 1.30 for a thin file'],
    ],
    note: 'Missing data widens the safety margin; it is never read as bad behaviour.',
    source: 'backend/src/veritrust/affordability.py · AffordabilityEngine.evaluate',
  },
  disposable: {
    title: 'Disposable a month',
    engine: 'backend',
    formula: ['D = I − (essentials + existing EMIs) − B'],
    terms: [
      ['I', 'monthly income'],
      ['B', 'cash kept aside'],
    ],
    note: 'Sufficient at ₹3,000 or more, borderline below that, insufficient at zero or less.',
    source: 'backend/src/veritrust/affordability.py · AffordabilityEngine.evaluate',
  },
  maxEmi: {
    title: 'Largest safe EMI',
    engine: 'backend',
    formula: ['EMI_max = min(D, 40% × I, 50% × I − existing EMIs)'],
    terms: [
      ['D', 'disposable a month'],
      ['40% × I', 'instalment-to-income (FOIR) cap'],
      ['50% × I', 'total debt-to-income cap'],
    ],
    note: '"Set by" names whichever of the three is smallest.',
    source: 'backend/src/veritrust/affordability.py · AffordabilityEngine.evaluate',
  },
  emi: {
    title: 'Monthly EMI',
    engine: 'backend and demo engine',
    formula: ['EMI = P × r(1 + r)^n / ((1 + r)^n − 1)', 'EMI = P / n when r = 0'],
    terms: [
      ['P', 'amount borrowed'],
      ['r', 'annual rate / 12'],
      ['n', 'months'],
    ],
    note: 'Reducing balance, rounded to the paisa.',
    source: 'backend/src/veritrust/affordability.py · calculate_emi',
  },
  stress: {
    title: 'Stress test',
    engine: 'backend',
    formula: [
      'each month: income × N(1, 0.15), floored at 0',
      '5% chance 40% of it arrives a month late',
      '10% chance of an emergency of N(₹4,000, ₹2,000)',
      'shortfall: cash after essentials < EMI',
      'tolerance = (I − essentials − EMI) / I',
    ],
    note: '2,000 futures over the loan term, seed 42, so every run repeats. Resilient at 5% shortfall or less, moderate at 15% or less, fragile above.',
    source: 'backend/src/veritrust/stress_tester.py · MonteCarloStressTester',
  },
  defaultProbability: {
    title: 'Default probability',
    engine: 'backend',
    formula: ['P = 1 / (1 + e^(−logit))', 'logit = base + Σ log-odds of each factor, held to ±6'],
    note: 'A scorecard with set log-odds per factor: the ones listed under "Lowers risk" and "Raises risk". The trained models in backend/ml/ run offline, for benchmarks only. If this fails, a rule-based fallback adds up fixed risk steps instead and holds P between 1% and 95%.',
    source: 'backend/src/veritrust/prediction.py · evaluate_credit_prediction',
  },
  conformal: {
    title: 'Conformal set and decision',
    engine: 'backend',
    formula: [
      'REPAY in the set when P ≤ 55%; DEFAULT when P ≥ 45%',
      'both → review · DEFAULT only → decline candidate',
      'REPAY only → eligible, or review if uncertainty > 0.45 or data is stale',
      'EMI does not fit → decline candidate',
    ],
    note: 'Rule-based fallback: decline candidate when the EMI does not fit or P ≥ 35%, eligible when P ≤ 14% with fresh data and uncertainty ≤ 0.45, otherwise review. Either way the lender decides.',
    source: 'backend/src/veritrust/prediction.py · evaluate_credit_prediction',
  },
  modelUncertainty: {
    title: 'Model uncertainty',
    engine: 'backend',
    formula: ['σ² = 1 − C_comp × (1 − σ²_base)', 'σ²_base = 1 / (1 + N × completeness)', 'C_comp = 0.6·C_vouch + 0.4·C_cash'],
    terms: [
      ['N', 'settled loans + eligible vouches (+1 with financials on file)'],
      ['C', '2^(−age / half-life): vouches 24 months, cash flow 6 months'],
    ],
    note: 'Old evidence counts for less, so uncertainty creeps back up until it is re-verified.',
    source: 'backend/src/veritrust/prediction.py, temporal.py',
  },
  modelScale: {
    title: 'Model scale',
    engine: 'backend',
    formula: ['score = clamp(600 − 40 × logit / ln 2, 300, 900)'],
    note: 'Every 40 points halves the odds of default. A model scale, not a bureau score.',
    source: 'backend/src/veritrust/prediction.py · evaluate_credit_prediction',
  },
  fee: {
    title: 'Platform fee',
    engine: 'backend',
    formula: ['fee = round(amount × 1%, 2)', 'net = amount − fee'],
    note: 'Taken on each disbursement and each repayment, rounded half up to the paisa, and added to the platform treasury.',
    source: 'backend/src/veritrust/lending.py · compute_platform_fee',
  },

  // Guided story and lender console: the demo engine.
  mu: {
    title: 'Expected capacity μ',
    engine: 'demo engine',
    formula: ['μ = (0.6·R_graph + 0.4·S_cf) × e^(0.1 × (settled + vouches in))'],
    terms: [
      ['R_graph', 'trust reaching this person from institutions'],
      ['S_cf', 'cash-flow score, 0 when no statement is linked'],
    ],
    note: 'Each settled loan and incoming vouch compounds capacity by about 10%.',
    source: 'frontend/src/mocks/engine/scoring.ts · score',
  },
  sigma2: {
    title: 'Uncertainty σ²',
    engine: 'demo engine',
    formula: ['σ² = 1 / (1 + N × completeness)'],
    terms: [
      ['N', 'linked sources + settled loans'],
      ['completeness', 'share of the 5 expected fields present'],
    ],
    note: '1.00 means nothing is known yet. That is uncertainty, never bad credit, and missing fields are never filled in.',
    source: 'frontend/src/mocks/engine/scoring.ts · score',
  },
  lcb: {
    title: 'Lendable score',
    engine: 'demo engine',
    formula: ['Score_final = μ − κ√σ²   (κ = 1)', 'band = μ ± √σ²'],
    note: 'The lower end of what we know: the number a lender can rely on. A wide band means we do not know the person yet.',
    source: 'frontend/src/mocks/engine/scoring.ts · score',
  },
  limit: {
    title: 'Model limit',
    engine: 'demo engine',
    formula: ['limit = max(0, Score_final) × ₹10,000', 'shown rounded down to ₹500'],
    source: 'frontend/src/mocks/engine/scoring.ts · score',
  },
  rGraph: {
    title: 'Trust from the graph',
    engine: 'demo engine',
    formula: ['W = C / |Out|,  C = max(0, R)', 'Trust(path) = W₁ × Π (Wᵢ × 0.5) for later hops', 'R_graph = Σ Trust over every institution-to-person path'],
    note: 'A voucher splits their capacity evenly across everyone they back. A path that loops back on itself counts 0, so a ring cannot vouch itself up.',
    source: 'frontend/src/mocks/engine/graph.ts · rGraph',
  },
  cashflow: {
    title: 'Cash-flow score',
    engine: 'demo engine',
    formula: ['S_cf = (0.5·DSCR_n + 0.3·(1 − CV_n) + 0.2·(1 − vol_n)) × completeness', 'DSCR = mean income / (obligations + new EMI)'],
    terms: [
      ['_n', 'scaled to 0..1: DSCR over 0.5..2.5, income variation over 0..0.6, volatility over 0..1'],
    ],
    source: 'frontend/src/mocks/engine/scoring.ts · cashflowMetrics',
  },
  cascade: {
    title: 'If it defaults',
    engine: 'demo engine',
    formula: ['Δ₀ = principal / ₹5,000', 'each direct voucher: 0.5 × W × Δ₀', 'their vouchers: 0.25 × Δ₀', 'further out: nothing'],
    note: 'Applied in one step. If more than 30% of a cluster has already defaulted, the breaker trips and the slash is queued for review instead.',
    source: 'frontend/src/mocks/engine/slashing.ts · cascade',
  },

  // Community: the demo engine, mirrored in the backend.
  vouchWeight: {
    title: 'Weight of this vouch',
    engine: 'backend and demo engine',
    formula: ['w = R/100 × h × e^(−U) × g'],
    terms: [
      ['R', 'your reputation, 0..100'],
      ['h', 'your record: (repaid + 1) / (resolved + 2); for a stranger vouch, × min(1, resolved/5)'],
      ['U', 'share of your points staked, counting this vouch (always 15 points)'],
      ['g', 'relationship × (0.6 + 0.4 × years known/10, up to 10 years); 0.60 for a stranger vouch'],
    ],
    source: 'frontend/src/mocks/engine/community.ts · weight',
  },
  communityScore: {
    title: 'Community score',
    engine: 'backend and demo engine',
    formula: ['S = 100 × (1 − e^(−W/3))', 'W = known + min(evidence, 0.60 + ⅔ × known)'],
    note: 'Stranger vouches are capped, and the cap only rises as people who know the borrower vouch, so strangers alone cannot carry a score.',
    source: 'frontend/src/mocks/engine/community.ts · communityScore',
  },
  reward: {
    title: 'What you win or lose',
    engine: 'backend and demo engine',
    formula: ['repaid: +10 × w × (1 − p)', 'default: −10 × w × p'],
    terms: [['p', 'how often comparable borrowers repay']],
    note: 'Backing someone everyone expects to repay earns little; backing an overlooked borrower who repays earns the most.',
    source: 'frontend/src/mocks/engine/community.ts · rewardPreview',
  },
} satisfies Record<string, Formula>;

export type FormulaId = keyof typeof FORMULAS;
