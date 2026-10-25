/**
 * Community platform demo data: members who vouch, and people who posted an ask. All fictional.
 * "Verified" items are platform-computed summaries the borrower chose to show; strangers never
 * see raw statements. Bureau scores are illustrative, never a real bureau value.
 */
import { D, Decimal } from './engine/params';
import type { Member, Vouch } from './engine/community';

export const VIEWER_ID = 'meena';
export const BORROWER_ID = 'lakshmi';

export const MEMBERS: Record<string, Member> = {
  meena: { id: 'meena', name: 'Meena Patil', line: 'Kirana store, Old Hubballi', reputation: D(82), budget: D(100), committed: D(35), resolved: 7, repaid: 6 },
  ramesh: { id: 'ramesh', name: 'Ramesh Hegde', line: 'Cloth wholesaler, Durgadbail', reputation: D(74), budget: D(100), committed: D(40), resolved: 12, repaid: 11 },
  kavya: { id: 'kavya', name: 'Kavya Rao', line: 'Tiffin service, Vidyanagar', reputation: D(61), budget: D(80), committed: D(10), resolved: 1, repaid: 1 },
  anand: { id: 'anand', name: 'Anand Kulkarni', line: 'Retired bank officer · reads files', reputation: D(70), budget: D(100), committed: D(45), resolved: 15, repaid: 13 },
  farida: { id: 'farida', name: 'Farida Shaikh', line: 'Embroidery unit, Keshwapur', reputation: D(68), budget: D(90), committed: D(20), resolved: 5, repaid: 5 },
  basava: { id: 'basava', name: 'Basavaraj Angadi', line: 'Auto stand union, Gokul Road', reputation: D(55), budget: D(80), committed: D(15), resolved: 0, repaid: 0 },
};

export type Verified = { key: string; label: string; detail: string; tone: 'ok' | 'gap' | 'warn' };

export interface Ask {
  id: string;
  ownerId: string;
  name: string;
  trade: string;
  place: string;
  circle: string;
  purpose: string;
  amountBand: string;
  postedDays: number;
  story: string;
  /** Platform-verified summaries; `shown` is the borrower's consent for strangers to see each one. */
  verified: (Verified & { shown: boolean })[];
  thinFile: boolean;
  bureau: { status: 'NO_FILE' | 'AVAILABLE'; trail: number[] | null };
  /** Expected repayment rate for comparable borrowers; drives the reward for backing them. */
  expectedRepay: Decimal;
  vouches: Vouch[];
  setback?: { posted: string; text: string; reported: true; responses: Record<string, 'STAND_BY' | 'STEP_BACK' | 'PENDING'> };
  /** Who among members knows this person (offline relationship), for the viewer's default path. */
  knownBy: string[];
}

const v = (voucherId: string, kind: Vouch['kind'], stake: number, relationship?: Vouch['relationship'], yearsKnown?: number): Vouch => ({
  voucherId, kind, stake: D(stake), relationship, yearsKnown,
});

const SEED_ASKS: Ask[] = [
  {
    id: 'lakshmi', ownerId: 'lakshmi', name: 'Lakshmi Naik', trade: 'Tailoring unit', place: 'Hubballi', circle: "Tailors' Association",
    purpose: 'Two industrial sewing machines', amountBand: '₹1–2 lakh', postedDays: 2,
    story: 'Wedding-season orders are more than two machines can stitch. A third and fourth would let me take school-uniform contracts too.',
    verified: [
      { key: 'income', label: 'Income steady for 24 months', detail: 'About ₹38,000 a month · bank statement', tone: 'ok', shown: true },
      { key: 'rent', label: 'Rent and chit fund paid 24 of 24 months', detail: 'Bank statement', tone: 'ok', shown: true },
      { key: 'fit', label: 'Loan fits her worst month at 24 months', detail: 'Stress-tested · EMI about ₹7,931', tone: 'ok', shown: true },
      { key: 'bureau', label: 'No credit bureau file', detail: 'Never borrowed formally · recorded as unknown, not bad', tone: 'gap', shown: true },
    ],
    thinFile: true, bureau: { status: 'NO_FILE', trail: null }, expectedRepay: D('0.80'),
    vouches: [v('ramesh', 'KNOWN', 15, 'TRADE', 6), v('anand', 'EVIDENCE', 10)],
    knownBy: ['meena', 'ramesh', 'kavya'],
  },
  {
    id: 'suresh', ownerId: 'suresh', name: 'Suresh Kulkarni', trade: 'Auto-rickshaw driver', place: 'Gokul Road', circle: 'Auto stand union',
    purpose: 'Refinance a hospital bill into one EMI', amountBand: '₹50,000–75,000', postedDays: 9,
    story: 'Twelve years on the same stand. My father’s surgery in January took everything I had saved.',
    verified: [
      { key: 'income', label: 'Daily fares steady for 18 months', detail: 'About ₹32,000 a month · bank statement', tone: 'ok', shown: true },
      { key: 'bureau', label: 'Bureau score 745 → 668 in three months', detail: 'Utilisation up, one EMI 30 days late', tone: 'warn', shown: true },
      { key: 'dsr', label: 'Debt service 47% after the new EMI', detail: 'Borderline · review obligations', tone: 'warn', shown: true },
    ],
    thinFile: false, bureau: { status: 'AVAILABLE', trail: [744, 746, 745, 731, 689, 668] }, expectedRepay: D('0.85'),
    vouches: [v('meena', 'KNOWN', 15, 'NEIGHBOUR', 8), v('ramesh', 'KNOWN', 10, 'COMMUNITY', 5), v('basava', 'KNOWN', 10, 'COLLEAGUE', 12), v('farida', 'KNOWN', 10, 'COMMUNITY', 4)],
    setback: {
      posted: '3 weeks ago', reported: true,
      text: 'Hospital bill not covered by insurance. I was 30 days late on one EMI in February and have paid it since. Asking my vouchers to stand by while I refinance.',
      responses: { meena: 'PENDING', ramesh: 'STAND_BY', basava: 'STAND_BY', farida: 'STAND_BY' },
    },
    knownBy: ['meena', 'ramesh', 'basava', 'farida'],
  },
  {
    id: 'farida-ask', ownerId: 'farida', name: 'Farida Shaikh', trade: 'Embroidery unit', place: 'Keshwapur', circle: 'Women’s SHG federation',
    purpose: 'Working capital for the Eid season', amountBand: '₹50,000–1 lakh', postedDays: 4,
    story: 'Three repaid loans with the SHG. Bulk orders need thread and zari bought upfront.',
    verified: [
      { key: 'income', label: 'Income steady for 36 months', detail: 'About ₹41,000 a month', tone: 'ok', shown: true },
      { key: 'bureau', label: 'Bureau score 742, clean for 24 months', detail: 'Three closed loans, none late', tone: 'ok', shown: true },
    ],
    thinFile: false, bureau: { status: 'AVAILABLE', trail: [728, 731, 735, 738, 740, 742] }, expectedRepay: D('0.95'),
    vouches: [v('kavya', 'KNOWN', 8, 'COMMUNITY', 3)],
    knownBy: ['kavya'],
  },
  {
    id: 'imran', ownerId: 'imran', name: 'Imran Mulla', trade: 'Mobile repair stall', place: 'Old Hubballi', circle: 'Market association',
    purpose: 'Stock of spare screens and a soldering station', amountBand: '₹25,000–50,000', postedDays: 1,
    story: 'Two years at the stall, all cash and UPI. First time asking for a loan.',
    verified: [
      { key: 'income', label: 'UPI receipts for 9 months', detail: 'About ₹22,000 a month · partial statement', tone: 'ok', shown: true },
      { key: 'bureau', label: 'No credit bureau file', detail: 'Never borrowed formally', tone: 'gap', shown: true },
      { key: 'expenses', label: 'Living costs not shared', detail: 'Affordability unknown until shared', tone: 'gap', shown: true },
    ],
    thinFile: true, bureau: { status: 'NO_FILE', trail: null }, expectedRepay: D('0.78'),
    vouches: [],
    knownBy: [],
  },
];

/** Seed vouches keep the utilisation their voucher has today: their commitments already include these stakes. */
export const ASKS: Ask[] = SEED_ASKS.map((a) => ({
  ...a,
  vouches: a.vouches.map((x) => ({ ...x, utilisation: MEMBERS[x.voucherId]!.committed.div(MEMBERS[x.voucherId]!.budget) })),
}));
