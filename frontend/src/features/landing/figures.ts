/**
 * Published figures for the landing page, from the Vouch evidence dossier v2 (25 Oct 2026). Each
 * keeps its original source and the dossier's stated limit. Display copy only: nothing is computed
 * here, and percentages are used for bar widths, never for money.
 */
export type Source = { label: string; url: string };

export const SOURCES = {
  cibil: {
    label: 'TransUnion CIBIL, Credit Market Indicator, Dec 2024',
    url: 'https://newsroom.transunioncibil.com/41-of-first-time-borrowers-are-gen-z-according-to-transunion-cibils-latest-cmi-report/',
  },
  ibef: {
    label: 'IBEF, summary of CIBIL’s Unlocking Access report, 15 Sep 2026',
    url: 'https://www.ibef.org/news/first-time-borrowers-deepen-credit-reach-credit-uptake-among-eligible-indians-more-than-doubled-to-74-in-march-from-35-in-2017',
  },
  finreglab: {
    label: 'FinRegLab, cash-flow underwriting study, 2019',
    url: 'https://finreglab.org/research/the-use-of-cash-flow-data-in-underwriting-credit-empirical-research-findings/',
  },
  feigenberg: {
    label: 'Feigenberg, Field and Pande, Review of Economic Studies, 2013',
    url: 'https://academic.oup.com/restud/article-abstract/80/4/1459/1582821',
  },
  findex: {
    label: 'World Bank, Global Findex 2021, borrowing chapter',
    url: 'https://documents1.worldbank.org/curated/en/099852507072221689/pdf/IDU0376aae3a0b6c5042da0859f0f4a9d2f71938.pdf',
  },
  freedman: {
    label: 'Freedman and Jin, NBER Working Paper 19820',
    url: 'https://www.nber.org/papers/w19820',
  },
} satisfies Record<string, Source>;

/** India's credit gap, all from the same CIBIL report. */
export const GAP = {
  headline: { value: '451', unit: 'million', line: 'Indians have limited or no formal credit, out of 1.036 billion adults eligible to borrow.' },
  facts: [
    { value: '27%', line: 'of credit-eligible adults use formal credit: about 277 million people.' },
    { value: '16%', line: 'credit penetration among Gen Z, who make up 34% of the credit-eligible population.' },
    { value: '41%', line: 'of first-time borrowers are Gen Z.' },
  ],
  source: SOURCES.cibil,
};

/** March 2017 against March 2026, in percent. */
export const TREND = {
  rows: [
    { label: 'Eligible Indians who have borrowed at least once', from: 35, to: 74 },
    { label: 'New-to-credit borrowers’ share of new retail loans', from: 32, to: 13 },
  ],
  source: SOURCES.ibef,
};

export type Finding = {
  key: string;
  counter?: boolean;
  figure: string;
  unit?: string;
  title: string;
  body: string;
  limit: string;
  inVouch: string;
  source: Source;
};

export const FINDINGS: Finding[] = [
  {
    key: 'cashflow',
    figure: '90,000+',
    unit: 'loans studied',
    title: 'Cash flow carries signal',
    body: 'Across six non-bank lenders, cash-flow variables predicted credit risk, helped assess people with thin credit histories, and separated borrowers that traditional scores ranked alike.',
    limit: 'It does not test peer vouching or give one uplift figure.',
    inVouch: 'Affordability is its own signal, read from the bank statement, never from a vouch.',
    source: SOURCES.finreglab,
  },
  {
    key: 'accountability',
    figure: '3×',
    unit: 'less likely to default',
    title: 'Accountability changes repayment',
    body: 'In a randomised trial, microfinance clients put in weekly rather than monthly group meetings were three times less likely to default on their second loan.',
    limit: 'These were face-to-face groups, not app endorsements.',
    inVouch: 'Endorsers stake their own reputation and lose part of it if the borrower defaults.',
    source: SOURCES.feigenberg,
  },
  {
    key: 'informal',
    figure: '46%',
    unit: 'borrowed formally',
    title: 'Most borrowing is already personal',
    body: 'Among borrowers in developing economies, only 46% borrowed from a formal lender; about as many named family and friends as their only source of credit.',
    limit: 'It does not show that personal endorsements predict repayment.',
    inVouch: 'The trust already exists. Vouch makes it visible to a lender, with its evidence.',
    source: SOURCES.findex,
  },
  {
    key: 'ties',
    counter: true,
    figure: 'Ties ≠ trust',
    title: 'Social ties can fool lenders',
    body: 'On a large peer-to-peer platform, borrowers with social ties were funded more often and at lower rates, yet most of them were more likely to pay late or default.',
    limit: 'Counting connections misleads; it is the trap this design has to avoid.',
    inVouch: 'A vouch is weighted by the endorser’s own record, each extra vouch adds less, and rings of new accounts are checked.',
    source: SOURCES.freedman,
  },
];
