/**
 * Landing-page story data, built on the scenarios in the Vouch documentation: a first-time borrower,
 * a temporary shock that drops a bureau score, and an endorsement ring.
 *
 * Every person and figure here is demo data, not a real record; bureau scores are illustrative and
 * never a real bureau value. Derived figures are computed by the mock engine so components only
 * format.
 */
import { D, Decimal } from './engine/params';
import { evaluatePlan, incomeStats, searchPlans, type CashFlow, type Plan } from './engine/affordability';
import { vouchScore, type Endorsement, type VouchResult } from './engine/vouch';
import { formatMoney, inr } from '@/lib/format';

const MONTHS = [
  '2024-03', '2024-04', '2024-05', '2024-06', '2024-07', '2024-08', '2024-09', '2024-10',
  '2024-11', '2024-12', '2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06',
  '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12', '2026-01', '2026-02',
];
// Monthly UPI and cash-deposit credits to Lakshmi's account, INR. Wedding seasons peak, monsoon dips.
const CREDITS = [
  36500, 41000, 43500, 33000, 31920, 34000, 35500, 39000, 44000, 42500, 40000, 38500,
  36000, 41500, 42000, 33500, 32500, 34500, 36000, 38500, 43000, 41500, 39500, 34080,
];

export const LAKSHMI = {
  name: 'Lakshmi Naik',
  trade: 'tailoring unit, Hubballi',
  ask: { principal: '150000', months: 12 },
};

const income = incomeStats(CREDITS.map((c) => D(c)));
const worstIndex = CREDITS.indexOf(Math.min(...CREDITS));

export const CASH_FLOW: CashFlow = {
  income: income.mean,
  // Rent plus household and shop running costs, from her statement debits.
  essentials: D(20500),
  // A chit-fund contribution she already pays.
  obligations: D(2000),
};

export const STATEMENT = MONTHS.map((month, i) => ({ month, credit: String(CREDITS[i]) }));

export const INCOME = {
  mean: income.mean.toString(),
  worstFall: income.worstFall.toString(),
  worstMonth: MONTHS[worstIndex]!,
};

/** Demo lender pricing: 24% a year on a small-business term loan. */
const RATE = D('0.24');
export const CANDIDATES: Plan[] = [
  { principal: D(150000), annualRate: RATE, months: 12 },
  { principal: D(150000), annualRate: RATE, months: 18 },
  { principal: D(150000), annualRate: RATE, months: 24 },
  { principal: D(120000), annualRate: RATE, months: 18 },
];

export function stress(incomeFall: Decimal) {
  return searchPlans(CASH_FLOW, CANDIDATES, incomeFall);
}

/** The plan that survives her own worst month. */
export const FINAL = stress(income.worstFall);

/** People who could vouch for Lakshmi, plus a ring of new accounts, for the score builder. */
export interface Endorser extends Endorsement {
  key: string;
  name: string;
  line: string;
  ring?: boolean;
}
const e = (reputation: number, reliability: string, utilisation: string, edgeQuality = '1') => ({
  reputation: D(reputation),
  reliability: D(reliability),
  utilisation: D(utilisation),
  edgeQuality: D(edgeQuality),
});
export const ENDORSERS: Endorser[] = [
  { key: 'meena', name: 'Meena Patil', line: 'Kirana store next door · knows her 9 years', ...e(82, '0.95', '0.2') },
  { key: 'ramesh', name: 'Ramesh Hegde', line: 'Her cloth supplier · half his budget already staked', ...e(74, '0.90', '0.5') },
  { key: 'kavya', name: 'Kavya Rao', line: 'Neighbour · new to vouching', ...e(61, '0.85', '0.1') },
  // Accounts opened the same week that endorse each other: the abuse penalty cuts edge quality to 0.1.
  { key: 'ring', name: 'Five new accounts', line: 'Opened the same week · all endorse each other', ring: true, ...e(40, '0.50', '0', '0.1') },
];
export const RING_SIZE = 5;
export const DEFAULT_ENDORSERS = ['meena', 'ramesh'];

export function endorse(keys: string[]): VouchResult {
  return vouchScore(ENDORSERS.filter((x) => keys.includes(x.key)).flatMap((x) => (x.ring ? Array(RING_SIZE).fill(x) : [x])));
}

type Tone = 'active' | 'restricted' | 'defaulted' | 'cold' | 'neel' | 'plain';
export interface Case {
  key: string;
  tab: string;
  who: string;
  what: string;
  bureau: { status: 'AVAILABLE' | 'NO_FILE'; trail: number[] | null };
  vouch: VouchResult;
  vouchNote: string;
  afford: { status: 'sufficient' | 'borderline' | 'insufficient' | 'unknown'; note: string };
  codes: { code: string; tone: Tone }[];
  explanation: string;
  legacy: string;
}

const pick = FINAL.pick!;
const askedToday = evaluatePlan(CASH_FLOW, CANDIDATES[0]!, D(0));
const pickToday = evaluatePlan(CASH_FLOW, pick.plan, D(0));

// Suresh: stable income, then a large expense he reports as medical; revolving balance jumps.
const SURESH: CashFlow = { income: D(32000), essentials: D(16000), obligations: D(9500) };
const sureshPlan = evaluatePlan(SURESH, { principal: D(60000), annualRate: RATE, months: 12 }, D(0));

const pct = (v: Decimal) => `${v.mul(100).toFixed(0)}%`;

export const CASES: Case[] = [
  {
    key: 'nofile',
    tab: 'No credit file',
    who: LAKSHMI.name,
    what: 'Tailoring unit · first loan · asks ₹1,50,000',
    bureau: { status: 'NO_FILE', trail: null },
    vouch: endorse(DEFAULT_ENDORSERS),
    vouchNote: '2 eligible endorsements',
    afford: { status: 'sufficient', note: `at ${pick.plan.months} months · DSR ${pct(pickToday.dti)}` },
    codes: [
      { code: 'NO_FILE', tone: 'cold' },
      { code: 'INCOME_STABLE', tone: 'active' },
      { code: 'VOUCH_ELIGIBLE', tone: 'neel' },
    ],
    explanation: `No bureau file: recorded as unknown, not as bad. 24 months of statements show stable income. Two endorsements add evidence; they do not prove affordability. At ${LAKSHMI.ask.months} months the EMI leaves ${formatMoney(inr(askedToday.leftover.toString()))} spare; at ${pick.plan.months} months it survives her worst month.`,
    legacy: 'Declined: insufficient credit history',
  },
  {
    key: 'shock',
    tab: 'After a shock',
    who: 'Suresh Kulkarni',
    what: 'Auto-rickshaw driver · asks ₹60,000',
    bureau: { status: 'AVAILABLE', trail: [744, 746, 745, 731, 689, 668] },
    vouch: vouchScore([e(85, '0.95', '0.1'), e(80, '0.92', '0.2'), e(76, '0.90', '0.3'), e(70, '0.88', '0.1')]),
    vouchNote: '4 endorsements, unchanged by the shock',
    afford: { status: 'borderline', note: `DSR ${pct(sureshPlan.dti)} after the new EMI` },
    codes: [
      { code: 'UTILIZATION_SPIKE', tone: 'defaulted' },
      { code: 'OBLIGATION_INCREASE', tone: 'restricted' },
      { code: 'INCOME_STABLE', tone: 'active' },
      { code: 'PURPOSE_UNVERIFIED', tone: 'plain' },
    ],
    explanation:
      'The bureau score fell 77 points in three months as revolving utilisation rose. Recurring income looks stable. He reports a medical expense; the purpose is not verified. His endorsements held. Affordability is borderline: review current obligations before deciding.',
    legacy: 'Declined: score below cut-off',
  },
  {
    key: 'ring',
    tab: 'Endorsement ring',
    who: 'Account 7731',
    what: 'Opened 3 weeks ago · asks ₹2,00,000',
    bureau: { status: 'NO_FILE', trail: null },
    vouch: vouchScore(Array(12).fill(e(40, '0.50', '0', '0.1'))),
    vouchNote: '12 endorsements, all from one cluster',
    afford: { status: 'unknown', note: 'income not verified' },
    codes: [
      { code: 'RECIPROCAL_CLUSTER', tone: 'defaulted' },
      { code: 'BURST_ENDORSEMENTS', tone: 'restricted' },
      { code: 'INCOME_MISSING', tone: 'plain' },
    ],
    explanation:
      'Twelve endorsements arrived in one week from accounts that all endorse each other. Diminishing returns and the ring penalty keep the score low. Income is not verified, so affordability is unknown: flagged for review.',
    legacy: 'Approved: 12 references on file',
  },
];

/** The same ring without abuse checks, to show what the penalty prevents. */
export const RING_UNCHECKED = vouchScore(Array(12).fill(e(40, '0.50', '0')));

