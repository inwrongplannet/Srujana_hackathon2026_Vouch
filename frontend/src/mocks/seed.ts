/**
 * Deterministic demo world. Every person, institution and figure here is fictional and
 * illustrative. Demo identity numbers start with 0000, which no real Aadhaar number does.
 */
import type { CashflowProfile, DataSources } from './engine/scoring';
import type { NodeKind, NodeStatus } from '@/api/types';

export interface SeedNode {
  id: string;
  kind: NodeKind;
  name: string;
  role: string;
  place: string;
  cluster: string;
  R: string;
  status: NodeStatus;
  sources: DataSources;
  settledLoans: number;
  profile: CashflowProfile | null;
  /** Demo identity number (digits only) for people who can sign in. */
  rawId?: string;
  /** ZK_STUB per-user salt (zk-identity-stub: stored on the demo record). */
  userSalt?: string;
  joinedDay: number;
}

export interface SeedLoan {
  id: string;
  borrower: string;
  principal: string;
  purpose: string;
  status: 'APPLIED' | 'DISBURSED';
  appliedDay: number;
  disbursedDay?: number;
}

const none: DataSources = { aa: false, utility: false };

export const BORROWER_ID = 'p_lakshmi';
export const VOUCHER_ID = 'p_meena';
export const LENDER_ID = 'a_sahyog';

export const CLUSTERS = [
  { id: 'hubballi', name: 'Hubballi · small trade' },
  { id: 'gadag', name: 'Gadag · agriculture' },
];

/** The borrower joins during the demo; this is her identity record, not yet a graph node. */
export const BORROWER_SEED: SeedNode = {
  id: BORROWER_ID,
  kind: 'person',
  name: 'Lakshmi Naik',
  role: 'Tailoring unit',
  place: 'Old Hubballi',
  cluster: 'hubballi',
  R: '0',
  status: 'ACTIVE',
  sources: none,
  settledLoans: 0,
  rawId: '000000004821',
  userSalt: 'demo-salt-lakshmi',
  joinedDay: 0,
  profile: {
    monthlyIncome: ['8200', '7600', '8900', '7800', '8400', '8100'],
    netFlows: ['1900', '1200', '2400', '1500', '2000', '1700'],
    obligations: '3500',
  },
};

export const SEED_NODES: SeedNode[] = [
  { id: 'a_sahyog', kind: 'anchor', name: 'Sahyog Microfinance', role: 'Microfinance lender', place: 'Hubballi', cluster: 'hubballi', R: '8', status: 'ACTIVE', sources: none, settledLoans: 0, profile: null, joinedDay: -900 },
  { id: 'a_jyoti', kind: 'anchor', name: 'Jyoti Power Co-op', role: 'Electricity utility', place: 'Dharwad', cluster: 'hubballi', R: '6', status: 'ACTIVE', sources: none, settledLoans: 0, profile: null, joinedDay: -900 },
  { id: 'a_krishi', kind: 'anchor', name: 'Krishi Co-op Bank', role: 'Co-operative bank', place: 'Gadag', cluster: 'gadag', R: '5', status: 'ACTIVE', sources: none, settledLoans: 0, profile: null, joinedDay: -900 },

  { id: 'p_ramesh', kind: 'person', name: 'Ramesh Hegde', role: 'Kirana wholesaler', place: 'Durgadbail', cluster: 'hubballi', R: '4', status: 'ACTIVE', sources: { aa: true, utility: true }, settledLoans: 6, profile: null, joinedDay: -640 },
  { id: 'p_meena', kind: 'person', name: 'Meena Patil', role: 'Runs a kirana store', place: 'Old Hubballi', cluster: 'hubballi', R: '2.8', status: 'ACTIVE', sources: { aa: true, utility: true }, settledLoans: 4, profile: null, rawId: '000000001102', userSalt: 'demo-salt-meena', joinedDay: -410 },
  { id: 'p_kavya', kind: 'person', name: 'Kavya Rao', role: 'Tiffin service', place: 'Vidyanagar', cluster: 'hubballi', R: '1.6', status: 'ACTIVE', sources: { aa: true, utility: false }, settledLoans: 2, profile: null, joinedDay: -300 },
  {
    id: 'p_farida', kind: 'person', name: 'Farida Shaikh', role: 'Embroidery unit', place: 'Keshwapur', cluster: 'hubballi', R: '2.2', status: 'ACTIVE', sources: { aa: true, utility: true }, settledLoans: 3, joinedDay: -380,
    profile: { monthlyIncome: ['21500', '23000', '22400', '24100', '22800', '23600'], netFlows: ['5200', '6100', '5600', '6900', '5800', '6300'], obligations: '6000' },
  },
  {
    id: 'p_suresh', kind: 'person', name: 'Suresh Kulkarni', role: 'Auto-rickshaw driver', place: 'Gokul Road', cluster: 'hubballi', R: '1.1', status: 'ACTIVE', sources: { aa: true, utility: false }, settledLoans: 1, joinedDay: -150,
    profile: { monthlyIncome: ['15800', '14200', '17100', '12900', '16400', '15100'], netFlows: ['2600', '1100', '3900', '-400', '3100', '2200'], obligations: '5200' },
  },
  { id: 'p_anita', kind: 'person', name: 'Anita Desai', role: 'Vegetable vendor', place: 'Janata Bazaar', cluster: 'hubballi', R: '0.4', status: 'ACTIVE', sources: none, settledLoans: 0, profile: null, joinedDay: -40 },
  { id: 'p_joseph', kind: 'person', name: "Joseph D'Souza", role: 'Mobile repair', place: 'Lamington Road', cluster: 'hubballi', R: '-0.4', status: 'RESTRICTED', sources: { aa: true, utility: false }, settledLoans: 1, profile: null, joinedDay: -260 },
  { id: 'p_vinod', kind: 'person', name: 'Vinod Shetty', role: 'Scrap dealer', place: 'Unkal', cluster: 'hubballi', R: '-1.2', status: 'DEFAULTED', sources: none, settledLoans: 0, profile: null, rawId: '000000000007', userSalt: 'demo-salt-vinod', joinedDay: -220 },

  { id: 'p_basava', kind: 'person', name: 'Basavaraj Angadi', role: 'Farmer-producer lead', place: 'Gadag', cluster: 'gadag', R: '3', status: 'ACTIVE', sources: { aa: true, utility: true }, settledLoans: 5, profile: null, joinedDay: -700 },
  { id: 'p_mallappa', kind: 'person', name: 'Mallappa Koti', role: 'Groundnut farmer', place: 'Mulgund', cluster: 'gadag', R: '1', status: 'ACTIVE', sources: { aa: false, utility: true }, settledLoans: 2, profile: null, joinedDay: -330 },
  { id: 'p_shivu', kind: 'person', name: 'Shivakumar Hosamani', role: 'Jowar farmer', place: 'Lakshmeshwar', cluster: 'gadag', R: '1', status: 'ACTIVE', sources: { aa: false, utility: true }, settledLoans: 2, profile: null, joinedDay: -330 },
  { id: 'p_girija', kind: 'person', name: 'Girija Pujar', role: 'Onion farmer', place: 'Naregal', cluster: 'gadag', R: '1', status: 'ACTIVE', sources: { aa: false, utility: true }, settledLoans: 1, profile: null, joinedDay: -300 },
  { id: 'p_hanu', kind: 'person', name: 'Hanumanth Badiger', role: 'Dairy farmer', place: 'Ron', cluster: 'gadag', R: '1', status: 'ACTIVE', sources: { aa: false, utility: true }, settledLoans: 3, profile: null, joinedDay: -320 },
];

export const SEED_EDGES: { from: string; to: string; createdDay: number }[] = [
  { from: 'a_sahyog', to: 'p_ramesh', createdDay: -600 },
  { from: 'a_sahyog', to: 'p_kavya', createdDay: -280 },
  { from: 'a_jyoti', to: 'p_meena', createdDay: -390 },
  { from: 'a_jyoti', to: 'p_farida', createdDay: -350 },
  { from: 'p_ramesh', to: 'p_meena', createdDay: -400 },
  { from: 'p_ramesh', to: 'p_joseph', createdDay: -250 },
  { from: 'p_meena', to: 'p_farida', createdDay: -340 },
  { from: 'p_meena', to: 'p_suresh', createdDay: -140 },
  { from: 'p_meena', to: 'p_anita', createdDay: -35 },
  { from: 'p_kavya', to: 'p_suresh', createdDay: -120 },
  // A mutual vouch: the protocol absorbs the loop instead of letting it inflate either score.
  { from: 'p_anita', to: 'p_meena', createdDay: -30 },
  { from: 'p_joseph', to: 'p_vinod', createdDay: -210 },
  { from: 'a_krishi', to: 'p_basava', createdDay: -650 },
  { from: 'p_basava', to: 'p_mallappa', createdDay: -320 },
  { from: 'p_basava', to: 'p_shivu', createdDay: -320 },
  { from: 'p_basava', to: 'p_girija', createdDay: -290 },
  { from: 'p_basava', to: 'p_hanu', createdDay: -310 },
];

export const SEED_LOANS: SeedLoan[] = [
  { id: 'L-2041', borrower: 'p_farida', principal: '25000', purpose: 'Second sewing machine', status: 'APPLIED', appliedDay: -2 },
  { id: 'L-2043', borrower: 'p_suresh', principal: '15000', purpose: 'Engine overhaul', status: 'APPLIED', appliedDay: -1 },
  { id: 'L-2044', borrower: 'p_anita', principal: '5000', purpose: 'Cart and scale', status: 'APPLIED', appliedDay: 0 },
  { id: 'L-1987', borrower: 'p_mallappa', principal: '20000', purpose: 'Kharif seed and fertiliser', status: 'DISBURSED', appliedDay: -48, disbursedDay: -45 },
  { id: 'L-1988', borrower: 'p_shivu', principal: '20000', purpose: 'Kharif seed and fertiliser', status: 'DISBURSED', appliedDay: -48, disbursedDay: -45 },
  { id: 'L-1990', borrower: 'p_girija', principal: '20000', purpose: 'Drip line repair', status: 'DISBURSED', appliedDay: -46, disbursedDay: -44 },
  { id: 'L-1993', borrower: 'p_hanu', principal: '20000', purpose: 'Fodder stock', status: 'DISBURSED', appliedDay: -46, disbursedDay: -44 },
];

/** Loans the demo story's shock defaults at once (3 of 5 Gadag members). */
export const SHOCK_LOANS = ['L-1987', 'L-1988', 'L-1990'];

export const VOUCH_NOTE = 'I stitch school uniforms for 40 families in Old Hubballi. Meena has bought from me for three years.';
