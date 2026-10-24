/**
 * The only door from UI to data. Every call is async and returns contract-shaped data, so swapping
 * the mock server for `fetch(VITE_API_BASE_URL + path)` later touches this file alone.
 */
import { MockServer } from '@/mocks/server';
import { BORROWER_SEED, VOUCH_NOTE } from '@/mocks/seed';
import type {
  StoryStep,
  DemoIdentity,
  RegisterResponse,
  SimulateRequest,
  SimulateResponse,
  Snapshot,
  VouchPreview,
} from './types';

// ZK_STUB: the demo protocol salt is a public test value, not a secret; production uses the
// Poseidon circuit's protocol salt (zk-identity-stub skill).
const protocolSalt = import.meta.env.VITE_DEMO_PROTOCOL_SALT || 'veritrust-public-demo-salt';

export const server = new MockServer(protocolSalt);

const latency = (ms = 160) => new Promise((r) => setTimeout(r, ms));

export const api = {
  subscribe: server.subscribe,
  snapshot: (): Snapshot => server.getSnapshot(),

  async lookupIdentity(rawId: string): Promise<DemoIdentity | null> {
    await latency(420);
    return server.lookupIdentity(rawId);
  },
  identities: (): DemoIdentity[] => server.identities(),

  async register(rawId: string): Promise<RegisterResponse> {
    await latency(300);
    return server.register(rawId);
  },
  async requestVouch(from: string, to: string, note: string): Promise<void> {
    await latency();
    server.requestVouch(from, to, note);
  },
  async respondVouch(requestId: string, accept: boolean): Promise<void> {
    await latency();
    server.respondVouch(requestId, accept);
  },
  async linkSource(nodeId: string, source: 'aa' | 'utility'): Promise<void> {
    await latency(900);
    server.linkSource(nodeId, source);
  },
  async applyLoan(borrower: string, principal: string, purpose: string): Promise<void> {
    await latency();
    server.applyLoan(borrower, principal, purpose);
  },
  async decideLoan(loanId: string, approve: boolean, amount?: string): Promise<void> {
    await latency();
    server.decideLoan(loanId, approve, amount);
  },
  async advance(days: number): Promise<void> {
    await latency(120);
    server.advance(days);
  },
  async settle(loanId: string): Promise<void> {
    await latency();
    server.settle(loanId);
  },
  async defaultLoan(loanId: string): Promise<void> {
    await latency();
    server.defaultLoan(loanId);
  },
  async regionalShock(): Promise<void> {
    await latency();
    server.regionalShock();
  },
  async restructure(clusterId: string): Promise<void> {
    await latency();
    server.restructure(clusterId);
  },
  async previewVouch(voucherId: string, requesterId: string): Promise<VouchPreview> {
    await latency(220);
    return server.previewVouch(voucherId, requesterId);
  },
  async simulate(req: SimulateRequest): Promise<SimulateResponse> {
    await latency(140);
    return server.simulate(req);
  },
  async reset(): Promise<void> {
    await latency(80);
    server.reset();
  },

  /** The borrower's file after her first vouch, computed on a scratch server (landing page hero). */
  async storyPreview(): Promise<VouchPreview> {
    const scratch = new MockServer(protocolSalt);
    await scratch.ready;
    await scratch.register(BORROWER_SEED.rawId!);
    const snap = scratch.getSnapshot();
    return scratch.previewVouch(snap.voucherId, snap.borrowerId);
  },

  /**
   * Presenter fallback: replays the story up to `step` (e.g. `?jump=approve` in the URL), so any
   * scene can be shown without clicking through the ones before it.
   */
  async jumpTo(step: StoryStep): Promise<void> {
    const order: StoryStep[] = ['register', 'request', 'vouch', 'apply', 'approve', 'advance', 'outcome', 'settled', 'defaulted'];
    const target = order.indexOf(step);
    if (target < 0) return;
    server.reset();
    const s = () => server.getSnapshot();
    if (target >= order.indexOf('request')) await server.register(BORROWER_SEED.rawId!);
    if (target >= order.indexOf('vouch')) server.requestVouch(s().borrowerId, s().voucherId, VOUCH_NOTE);
    if (target >= order.indexOf('apply')) server.respondVouch(s().requests[0]!.id, true);
    if (target >= order.indexOf('approve')) server.applyLoan(s().borrowerId, '5000', 'Industrial sewing-machine motor');
    const loan = () => s().loans.find((l) => l.borrower === s().borrowerId)!;
    if (target >= order.indexOf('advance')) server.decideLoan(loan().id, true);
    if (target >= order.indexOf('outcome')) server.advance(30);
    if (step === 'settled') server.settle(loan().id);
    if (step === 'defaulted') server.defaultLoan(loan().id);
  },
};
