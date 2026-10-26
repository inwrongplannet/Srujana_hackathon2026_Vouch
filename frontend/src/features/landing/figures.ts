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
  cibilCsc: {
    label: 'TransUnion CIBIL, CIBIL–CSC partnership, first year',
    url: 'https://newsroom.transunion.in/transunion-cibil-and-csc-partnership-benefits-15-lakh-consumers-in-first-year/',
  },
  bajaj: {
    label: 'Bajaj Housing Finance, how a missed payment affects your CIBIL Score',
    url: 'https://www.bajajhousingfinance.in/resources/how-does-missing-payment-affect-cibil-score',
  },
  tataDpd: {
    label: 'Tata Capital, Days Past Due in the CIBIL report',
    url: 'https://www.tatacapital.com/blog/credit-score/days-past-due-in-cibil-report/',
  },
  zet: {
    label: 'ZET survey of 1,000+ people, reported by The Economic Times',
    url: 'https://economictimes.indiatimes.com/industry/banking/finance/banking/nearly-half-of-indian-consumers-never-checked-their-credit-score-zet-study/articleshow/123948262.cms',
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

/** India's credit gap, the national context for the first pain point. */
export const GAP = {
  value: '451 million',
  line: 'Indians have limited or no formal credit, out of 1.036 billion adults eligible to borrow.',
  source: SOURCES.cibil,
};

/**
 * Three pain points (frontend/Vouch_Three_Pain_Points_Statistical_Evidence.md), each with its
 * figure, its stated limit and what Vouch does about it. `draw` is the same figure as a number,
 * used only for drawing; "about one in three" is drawn as one of three, never as a precise share.
 */
export const PAINS = [
  {
    key: 'no-file',
    title: 'No score is not a bad score.',
    figure: '19%',
    draw: 19,
    line: 'of 150,000 people in a CIBIL–CSC programme were not eligible for a numerical CIBIL Score, potentially because they had no credit history.',
    caveat: 'One programme’s population, not a national estimate; it does not show that all of them could repay.',
    vouch: 'Vouch records a missing file as unknown, not bad, and looks at cash flow and accountable endorsements instead.',
    source: SOURCES.cibilCsc,
  },
  {
    key: 'setback',
    title: 'Years of paying on time, undone by one emergency.',
    figure: '50–80 points',
    draw: 80,
    line: 'can come off a CIBIL Score for a single payment 30 days late, by a lender’s published estimate, however clean the record before it.',
    context: {
      value: '36 months',
      line: 'of payment status sit on a CIBIL report. Thirty-five on-time months read 000; the one late month after a hospital bill reads 030, and the score follows it.',
      source: SOURCES.tataDpd,
    },
    caveat: 'A lender’s estimate: TransUnion CIBIL does not publish how many points a late payment costs, and the drop depends on the rest of the report. The late entry can stay on the report for up to seven years.',
    vouch: 'Vouch reads cash flow before and after the emergency, and who stood by the person, so years of good behaviour still count.',
    source: SOURCES.bajaj,
  },
  {
    key: 'no-reason',
    title: 'A no without a reason.',
    figure: '45%',
    draw: 45,
    line: 'of 1,000+ people surveyed had never checked their credit score; about one in three said they were rejected for a poor or missing credit history, often without an explanation.',
    caveat: 'A survey of reported experiences, not a national estimate; it does not show that bureaus give no explanations.',
    vouch: 'Vouch explains its own assessment: the evidence used, what is missing, and what would change the answer.',
    source: SOURCES.zet,
  },
] as const;

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
