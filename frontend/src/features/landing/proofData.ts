/**
 * Figures for the landing page's "Does it work?" section, copied from our dataset build:
 * real Prosper aggregates (data/prosper/prosper_check.json) and the simulated shock study
 * (data/synth/shock_validation.json, data/combined/README.md). Rates are decimal strings exactly as
 * reported; per-100 dot counts are derived here with Decimal so components only draw.
 */
import { D, Decimal } from '@/mocks/engine/params';

/** Whole dots out of `of` for a rate, half-even rounded. */
export const dotsFor = (rate: string, of: number) => D(rate).mul(of).toDecimalPlaces(0, Decimal.ROUND_HALF_EVEN).toNumber();

/** A rate as a percentage with one decimal, for labels. */
export const pct1 = (rate: string) => `${D(rate).mul(100).toFixed(1)}%`;

/** Percentage points between two rates, one decimal, always positive. */
export const gapPoints = (a: string, b: string) => D(a).minus(b).abs().mul(100).toFixed(1);

export type Cell = { n: number; rate: string };

/** Real Prosper loans (US, 2005-2014), resolved outcomes, endorsements carried no stake. */
export const REAL = {
  resolved: 54715,
  bandAdjustedGap: '0.0436',
  source: 'Prosper loans, our aggregation (data/prosper/prosper_check.json); Freedman and Jin report 4.1 points on the same platform',
  links: [
    { label: 'Dataset: Prosper Loan Data, 113,937 loans (public mirror we downloaded)', url: 'https://s3.amazonaws.com/udacity-hosted-downloads/ud651/prosperLoanData.csv' },
    { label: 'Freedman and Jin, NBER Working Paper 19820', url: 'https://www.nber.org/papers/w19820' },
  ],
  cells: [
    { key: 'lt600', label: 'Under 600', endorsed: { n: 678, rate: '0.4823' }, plain: { n: 6085, rate: '0.5614' } },
    { key: '600', label: '600–659', endorsed: { n: 1209, rate: '0.3366' }, plain: { n: 11670, rate: '0.3674' } },
    { key: '660', label: '660–719', endorsed: { n: 1091, rate: '0.2521' }, plain: { n: 16602, rate: '0.2963' } },
    { key: '720', label: '720 and up', endorsed: { n: 1220, rate: '0.1516' }, plain: { n: 16160, rate: '0.1877' } },
    { key: 'fell20', label: 'Score fell 20+', endorsed: { n: 261, rate: '0.2146' }, plain: { n: 3069, rate: '0.3047' } },
  ],
} as const;

/** Simulated shock study: every borrower lost 50+ bureau points to a recorded shock. */
export const SHOCK = {
  borrowers: 2289,
  perDot: 10,
  groups: [
    { key: 'held', label: 'Vouch held', note: 'endorsers stayed', n: 191, rate: '0.2147' },
    { key: 'faded', label: 'Vouch faded', note: 'endorsers walked away', n: 886, rate: '0.347' },
    { key: 'none', label: 'No vouch', note: 'nobody to ask', n: 1212, rate: '0.479' },
  ],
  stratifiedGap: '20.5',
  ci: ['14.6', '26.7'],
  source: 'Simulated borrowers in our dataset build; every rule and rate is sourced in data/combined/README.md',
} as const;

/** Same shocked borrowers, by how strong the vouch was afterwards (quartiles of the Vouch Score). */
export const DOSE = [
  { label: 'No vouch', floor: null, rate: '0.4751' },
  { label: 'Weakest quarter', floor: 3, rate: '0.4280' },
  { label: 'Second quarter', floor: 20, rate: '0.3690' },
  { label: 'Third quarter', floor: 33, rate: '0.2731' },
  { label: 'Strongest quarter', floor: 45, rate: '0.2426' },
] as const;
