/**
 * In-memory stand-in for the backend. It owns all protocol maths (via ./engine) and publishes
 * immutable snapshots; every mutation lands in one commit, so a cascade is never seen half-applied.
 */
import type {
  ApiAssessment,
  ApiCascade,
  ApiEvent,
  ApiNode,
  ApiDelta,
  Contract,
  LoanStatus,
  NodeStatus,
  RegisterResponse,
  SimulateRequest,
  SimulateResponse,
  Snapshot,
  StoryStep,
  DemoIdentity,
} from '@/api/types';
import { D, Decimal, PARAMS } from './engine/params';
import { capacity, edgeWeights, edgeKey, rGraph, type GraphEdge, type GraphNode } from './engine/graph';
import { score, type CashflowProfile, type DataSources } from './engine/scoring';
import { demoEmi, delta0For } from './engine/loan';
import { breakerTrips, cascade } from './engine/slashing';
import { nullifierStub } from './engine/nullifier';
import {
  BORROWER_ID,
  BORROWER_SEED,
  CLUSTERS,
  LENDER_ID,
  SEED_EDGES,
  SEED_LOANS,
  SEED_NODES,
  SHOCK_LOANS,
  VOUCHER_ID,
  type SeedNode,
} from './seed';

interface NodeRec {
  seed: SeedNode;
  R: Decimal;
  status: NodeStatus;
  registered: boolean;
  nullifier: string | null;
  joinedDay: number;
  settledLoans: number;
  sources: DataSources;
}

interface EdgeRec {
  from: string;
  to: string;
  createdDay: number;
  lockedLoanId: string | null;
}

interface LoanRec {
  id: string;
  borrower: string;
  principal: Decimal;
  purpose: string;
  status: LoanStatus;
  appliedDay: number;
  disbursedDay: number | null;
  dueDay: number | null;
  closedDay: number | null;
  slashQueued: boolean;
}

interface RequestRec {
  id: string;
  from: string;
  to: string;
  status: 'PENDING' | 'ACCEPTED' | 'DECLINED';
  day: number;
  note: string;
}

interface ClusterRec {
  id: string;
  name: string;
  tripped: boolean;
  queued: string[];
}

interface State {
  day: number;
  block: number;
  seq: number;
  nodes: Map<string, NodeRec>;
  edges: EdgeRec[];
  loans: LoanRec[];
  requests: RequestRec[];
  events: ApiEvent[];
  clusters: ClusterRec[];
  lastCascade: ApiCascade | null;
}

const BLOCKS_PER_DAY = 7200;
const CONFIRM_MS = 1400;
const inr = (amount: Decimal) => ({ amount: amount.toString(), currency: 'INR' as const });

/** Deterministic 64-hex-digit pseudo transaction hash (display only). */
function txHash(seed: string): string {
  let out = '';
  for (let round = 0; out.length < 64; round += 1) {
    let h = 0x811c9dc5 ^ round;
    for (let i = 0; i < seed.length; i += 1) {
      h ^= seed.charCodeAt(i);
      h = Math.imul(h, 0x01000193);
    }
    out += (h >>> 0).toString(16).padStart(8, '0');
  }
  return `0x${out.slice(0, 64)}`;
}

function initialState(): State {
  const nodes = new Map<string, NodeRec>();
  for (const seed of [...SEED_NODES, BORROWER_SEED]) {
    nodes.set(seed.id, {
      seed,
      R: D(seed.R),
      status: seed.status,
      registered: seed.id !== BORROWER_ID,
      nullifier: null,
      joinedDay: seed.joinedDay,
      settledLoans: seed.settledLoans,
      sources: { ...seed.sources },
    });
  }
  const loans: LoanRec[] = SEED_LOANS.map((l) => ({
    id: l.id,
    borrower: l.borrower,
    principal: D(l.principal),
    purpose: l.purpose,
    status: l.status,
    appliedDay: l.appliedDay,
    disbursedDay: l.disbursedDay ?? null,
    // Seeded crop loans run a 60-day season.
    dueDay: l.disbursedDay != null ? l.disbursedDay + 60 : null,
    closedDay: null,
    slashQueued: false,
  }));
  return {
    day: 0,
    block: 18_204_117,
    seq: 0,
    nodes,
    edges: SEED_EDGES.map((e) => ({ ...e, lockedLoanId: null })),
    loans,
    requests: [],
    events: [],
    clusters: CLUSTERS.map((c) => ({ ...c, tripped: false, queued: [] })),
    lastCascade: null,
  };
}

export class MockServer {
  private state: State = initialState();
  private snapshot: Snapshot;
  private version = 0;
  private listeners = new Set<() => void>();
  private timers: ReturnType<typeof setTimeout>[] = [];
  readonly ready: Promise<void>;

  constructor(private readonly protocolSalt: string) {
    this.snapshot = this.build();
    this.ready = this.anchorSeedIdentities();
  }

  // ---------- subscription ----------

  subscribe = (fn: () => void): (() => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };

  getSnapshot = (): Snapshot => this.snapshot;

  private commit(): void {
    this.snapshot = this.build();
    for (const fn of this.listeners) fn();
  }

  // ---------- identity ----------

  identities(): DemoIdentity[] {
    return [...this.state.nodes.values()]
      .filter((n) => n.seed.rawId)
      .map((n) => ({
        rawId: n.seed.rawId!,
        name: n.seed.name,
        district: n.seed.place.includes('Hubballi') ? 'Dharwad district' : n.seed.place,
        occupation: n.seed.role,
        yearOfBirth: n.seed.id === BORROWER_ID ? '1989' : '1984',
      }));
  }

  lookupIdentity(rawId: string): DemoIdentity | null {
    return this.identities().find((i) => i.rawId === rawId) ?? null;
  }

  /** ZK_STUB registration: same demo ID always yields the same nullifier and the same record. */
  async register(rawId: string): Promise<RegisterResponse> {
    await this.ready;
    const rec = [...this.state.nodes.values()].find((n) => n.seed.rawId === rawId);
    if (!rec) throw new Error('This is not one of the demo identities.');
    const nullifier = await nullifierStub(rawId, rec.seed.userSalt!, this.protocolSalt);
    const existing = [...this.state.nodes.values()].find((n) => n.registered && n.nullifier === nullifier);
    if (existing) {
      this.emit('IdentityRegistry', 'DuplicateRejected', `Nullifier already anchored; resolved to the existing ${existing.status} record`, [existing.seed.id], []);
      this.commit();
      return { node: this.snapshot.nodes[existing.seed.id], nullifier, existing: true };
    }
    rec.registered = true;
    rec.nullifier = nullifier;
    rec.joinedDay = this.state.day;
    this.emit('IdentityRegistry', 'Registered', 'New identity anchored · credibility 0, uncertainty 1.00', [rec.seed.id], []);
    this.commit();
    return { node: this.snapshot.nodes[rec.seed.id], nullifier, existing: false };
  }

  private async anchorSeedIdentities(): Promise<void> {
    for (const rec of this.state.nodes.values()) {
      if (rec.registered && rec.seed.rawId && rec.seed.userSalt) {
        rec.nullifier = await nullifierStub(rec.seed.rawId, rec.seed.userSalt, this.protocolSalt);
      }
    }
    this.commit();
  }

  // ---------- vouching ----------

  requestVouch(from: string, to: string, note: string): void {
    const s = this.state;
    if (s.requests.some((r) => r.from === from && r.to === to && r.status === 'PENDING')) return;
    s.requests.push({ id: `VR-${s.requests.length + 1}`, from, to, status: 'PENDING', day: s.day, note });
    this.commit();
  }

  respondVouch(requestId: string, accept: boolean): void {
    const s = this.state;
    const req = s.requests.find((r) => r.id === requestId);
    if (!req || req.status !== 'PENDING') return;
    if (!accept) {
      req.status = 'DECLINED';
      this.commit();
      return;
    }
    const voucher = s.nodes.get(req.to)!;
    if (capacity(voucher.R).isZero()) throw new Error('No vouch capacity: credibility must be above zero.');
    req.status = 'ACCEPTED';
    s.edges.push({ from: req.to, to: req.from, createdDay: s.day, lockedLoanId: null });
    const out = s.edges.filter((e) => e.from === req.to).length;
    const w = capacity(voucher.R).div(out);
    this.emit('VouchHub', 'VouchCast', `${voucher.seed.name} → ${s.nodes.get(req.from)!.seed.name} · ${out} vouches now share ${capacity(voucher.R).toString()} at ${w.toDecimalPlaces(2).toString()} each`, [req.to, req.from], []);
    this.commit();
  }

  // ---------- data sources ----------

  linkSource(nodeId: string, source: keyof DataSources): void {
    const rec = this.state.nodes.get(nodeId);
    if (!rec || rec.sources[source]) return;
    rec.sources[source] = true;
    this.commit();
  }

  // ---------- loans ----------

  applyLoan(borrower: string, principal: string, purpose: string): void {
    const s = this.state;
    if (s.loans.some((l) => l.borrower === borrower && (l.status === 'APPLIED' || l.status === 'DISBURSED'))) return;
    s.loans.push({
      id: `L-${2045 + s.loans.length - SEED_LOANS.length}`,
      borrower,
      principal: D(principal),
      purpose,
      status: 'APPLIED',
      appliedDay: s.day,
      disbursedDay: null,
      dueDay: null,
      closedDay: null,
      slashQueued: false,
    });
    this.commit();
  }

  decideLoan(loanId: string, approve: boolean, amount?: string): void {
    const s = this.state;
    const loan = s.loans.find((l) => l.id === loanId);
    if (!loan || loan.status !== 'APPLIED') return;
    if (!approve) {
      loan.status = 'DECLINED';
      loan.closedDay = s.day;
      this.commit();
      return;
    }
    if (amount) loan.principal = D(amount);
    loan.status = 'DISBURSED';
    loan.disbursedDay = s.day;
    loan.dueDay = s.day + PARAMS.LOAN_TERM_DAYS;
    for (const e of s.edges) if (e.to === loan.borrower) e.lockedLoanId = loan.id;
    this.emit('LoanEscrow', 'Disbursed', `${loan.id} · ₹${loan.principal.toString()} released to ${s.nodes.get(loan.borrower)!.seed.name}; backing vouches locked`, [LENDER_ID, loan.borrower], []);
    this.commit();
  }

  advance(days: number): void {
    this.state.day += days;
    this.state.block += days * BLOCKS_PER_DAY;
    this.commit();
  }

  settle(loanId: string): void {
    const s = this.state;
    const loan = s.loans.find((l) => l.id === loanId);
    if (!loan || loan.status !== 'DISBURSED') return;
    const d0 = delta0For(loan.principal);
    const borrower = s.nodes.get(loan.borrower)!;
    const mint = PARAMS.SETTLE_MINT.mul(d0);
    const yieldEach = PARAMS.SPONSOR_YIELD.mul(d0);
    const sponsors = s.edges.filter((e) => e.to === loan.borrower).map((e) => e.from);

    loan.status = 'SETTLED';
    loan.closedDay = s.day;
    borrower.R = borrower.R.plus(mint);
    borrower.settledLoans += 1;
    if (borrower.status === 'RESTRICTED' && borrower.R.gt(0)) borrower.status = 'ACTIVE';
    for (const id of sponsors) {
      const sp = s.nodes.get(id)!;
      sp.R = sp.R.plus(yieldEach);
      if (sp.status === 'RESTRICTED' && sp.R.gt(0)) sp.status = 'ACTIVE';
    }
    for (const e of s.edges) if (e.lockedLoanId === loan.id) e.lockedLoanId = null;

    this.emit('LoanEscrow', 'Settled', `${loan.id} repaid in full · ₹${loan.principal.toString()}`, [loan.borrower], [{ node: loan.borrower, delta: mint.toString() }]);
    this.emit('VouchHub', 'YieldPaid', `Sponsors earn reputation yield; locked capacity released`, sponsors, sponsors.map((id) => ({ node: id, delta: yieldEach.toString() })));
    this.commit();
  }

  defaultLoan(loanId: string): void {
    this.applyDefault(loanId);
    this.commit();
  }

  /** A regional shock: several loans in one cluster default in the same cycle. */
  regionalShock(): void {
    for (const id of SHOCK_LOANS) this.applyDefault(id);
    this.commit();
  }

  restructure(clusterId: string): void {
    const s = this.state;
    const cluster = s.clusters.find((c) => c.id === clusterId);
    if (!cluster || !cluster.tripped) return;
    const waived = cluster.queued.length;
    for (const loanId of cluster.queued) {
      const loan = s.loans.find((l) => l.id === loanId);
      if (loan) loan.slashQueued = false;
    }
    cluster.queued = [];
    cluster.tripped = false;
    this.emit('CircuitBreaker', 'Restructured', `${cluster.name}: review closed, ${waived} queued slash${waived === 1 ? '' : 'es'} waived, loans rescheduled`, [], []);
    this.commit();
  }

  private applyDefault(loanId: string): void {
    const s = this.state;
    const loan = s.loans.find((l) => l.id === loanId);
    if (!loan || loan.status !== 'DISBURSED') return;
    const borrower = s.nodes.get(loan.borrower)!;
    const cluster = s.clusters.find((c) => c.id === borrower.seed.cluster)!;
    const members = [...s.nodes.values()].filter((n) => n.registered && n.seed.kind === 'person' && n.seed.cluster === cluster.id);
    const defaulted = members.filter((n) => n.status === 'DEFAULTED').length;
    const d0 = delta0For(loan.principal);

    loan.status = 'DEFAULTED';
    loan.closedDay = s.day;
    for (const e of s.edges) if (e.lockedLoanId === loan.id) e.lockedLoanId = null;

    if (cluster.tripped || breakerTrips(defaulted, members.length)) {
      loan.slashQueued = true;
      borrower.status = 'DEFAULTED';
      cluster.queued.push(loan.id);
      this.emit('LoanEscrow', 'Defaulted', `${loan.id} · grace period expired; slash queued for review`, [loan.borrower], []);
      if (!cluster.tripped) {
        cluster.tripped = true;
        this.emit('CircuitBreaker', 'Tripped', `${cluster.name}: ${defaulted} of ${members.length} members already defaulted (> ${PARAMS.THETA.mul(100).toString()}%). Automated slashing paused`, [], []);
      }
      s.lastCascade = { id: `C-${s.seq}`, loanId, defaulter: loan.borrower, penalties: [], queued: true, day: s.day };
      return;
    }

    const graphNodes = this.graphNodes();
    const weights = edgeWeights(graphNodes, s.edges);
    const penalties = cascade(loan.borrower, d0, s.edges, weights);
    // Apply every penalty together, then fix states: no intermediate state is ever published.
    const applied = penalties.map((p) => {
      const rec = s.nodes.get(p.node)!;
      const before = rec.R;
      rec.R = rec.R.minus(p.delta);
      return { node: p.node, k: p.k, delta: p.delta.toString(), before: before.toString(), after: rec.R.toString() };
    });
    for (const p of penalties) {
      const rec = s.nodes.get(p.node)!;
      if (p.k === 0) rec.status = 'DEFAULTED';
      else if (rec.status !== 'DEFAULTED') rec.status = rec.R.lt(0) ? 'RESTRICTED' : 'ACTIVE';
    }
    s.lastCascade = { id: `C-${s.seq}`, loanId, defaulter: loan.borrower, penalties: applied, queued: false, day: s.day };
    this.emit('LoanEscrow', 'Defaulted', `${loan.id} · grace period expired without repayment`, [loan.borrower], []);
    this.emit(
      'VouchHub',
      'Slashed',
      `Damped cascade: defaulter −${d0.toString()}, ${penalties.filter((p) => p.k === 1).length} sponsor(s), ${penalties.filter((p) => p.k === 2).length} ancestor(s); hop 3+ untouched`,
      penalties.map((p) => p.node),
      penalties.map<ApiDelta>((p) => ({ node: p.node, delta: p.delta.neg().toString(), k: p.k })),
    );
  }

  // ---------- what-if ----------

  simulate(req: SimulateRequest): SimulateResponse {
    const rec = this.state.nodes.get(req.nodeId);
    if (!rec) throw new Error('Unknown node');
    const base = rec.seed.profile;
    let profile: CashflowProfile | null = base;
    if (base && (req.monthlyIncome || req.obligations)) {
      const incomes = base.monthlyIncome.map(D);
      const meanIncome = incomes.reduce((a, b) => a.plus(b), D(0)).div(incomes.length);
      const scale = req.monthlyIncome ? D(req.monthlyIncome).div(meanIncome) : D(1);
      profile = {
        monthlyIncome: incomes.map((x) => x.mul(scale).toString()),
        netFlows: base.netFlows.map((x) => D(x).mul(scale).toString()),
        obligations: req.obligations ?? base.obligations,
      };
    }
    const sources = { aa: req.aa ?? rec.sources.aa, utility: req.utility ?? rec.sources.utility };
    const assessment = this.assess(req.nodeId, {
      profile,
      sources,
      principal: req.principal ? D(req.principal) : undefined,
    });
    const dscrHealthy = assessment.cashflow ? D(assessment.cashflow.dscr).gte('1.25') : false;
    return { assessment, dscrHealthy };
  }

  reset(): void {
    for (const t of this.timers) clearTimeout(t);
    this.timers = [];
    const nullifiers = new Map([...this.state.nodes.values()].map((n) => [n.seed.id, n.nullifier]));
    this.state = initialState();
    for (const rec of this.state.nodes.values()) {
      if (rec.registered) rec.nullifier = nullifiers.get(rec.seed.id) ?? null;
    }
    this.commit();
  }

  // ---------- internals ----------

  private emit(contract: Contract, name: string, summary: string, actors: string[], deltas: ApiDelta[]): void {
    const s = this.state;
    s.seq += 1;
    s.block += 1 + (s.seq % 3);
    const event: ApiEvent = {
      id: `E-${s.seq}`,
      seq: s.seq,
      contract,
      name,
      tx: txHash(`${contract}.${name}#${s.seq}@${s.day}`),
      block: s.block,
      day: s.day,
      status: 'pending',
      summary,
      actors,
      deltas,
    };
    s.events.unshift(event);
    const timer = setTimeout(() => {
      const target = this.state.events.find((e) => e.id === event.id);
      if (target) {
        target.status = 'confirmed';
        this.commit();
      }
    }, CONFIRM_MS);
    this.timers.push(timer);
  }

  private graphNodes(): GraphNode[] {
    return [...this.state.nodes.values()]
      .filter((n) => n.registered)
      .map((n) => ({ id: n.seed.id, kind: n.seed.kind, R: n.R }));
  }

  private assess(
    nodeId: string,
    override?: { profile: CashflowProfile | null; sources: DataSources; principal?: Decimal },
  ): ApiAssessment {
    const s = this.state;
    const rec = s.nodes.get(nodeId)!;
    const graphNodes = this.graphNodes();
    const weights = edgeWeights(graphNodes, s.edges);
    const g = rGraph(nodeId, graphNodes, s.edges, weights);
    const open = s.loans.find((l) => l.borrower === nodeId && l.status === 'APPLIED');
    const principal = override?.principal ?? open?.principal;
    const proposedEmi = principal ? demoEmi(principal) : D(0);
    const inDegree = s.edges.filter((e) => e.to === nodeId).length;
    const profile = override ? override.profile : rec.seed.profile;
    const sc = score({
      rGraph: g.total,
      profile,
      sources: override?.sources ?? rec.sources,
      nSettled: rec.settledLoans,
      inDegree,
      proposedEmi,
    });
    // A DEFAULTED identity cannot borrow, whatever its graph trust (zk-identity-stub state machine).
    const limit = rec.status === 'DEFAULTED' ? D(0) : sc.limit;
    return {
      nodeId,
      rGraph: g.total.toString(),
      paths: g.paths.map((p) => ({ nodes: p.nodes, trust: p.trust.toString() })),
      absorbed: g.absorbed,
      cashflow: sc.cashflow && profile
        ? {
            meanIncome: inr(sc.cashflow.meanIncome),
            obligations: inr(D(profile.obligations)),
            proposedEmi: inr(proposedEmi),
            debtService: inr(sc.cashflow.debtService),
            dscr: sc.cashflow.dscr.toString(),
            incomeCv: sc.cashflow.incomeCv.toString(),
            volatility: sc.cashflow.volatility.toString(),
            sCashflow: sc.cashflow.sCashflow.toString(),
          }
        : null,
      nSettled: rec.settledLoans,
      inDegree,
      nData: sc.nData,
      completeness: sc.completeness.toString(),
      mu: sc.mu.toString(),
      sigma2: sc.sigma2.toString(),
      sigma: sc.sigma.toString(),
      lcb: sc.lcb.toString(),
      bandLow: sc.bandLow.toString(),
      bandHigh: sc.bandHigh.toString(),
      limit: inr(limit),
      requested: principal ? inr(principal) : null,
    };
  }

  private story(): StoryStep {
    const s = this.state;
    const b = s.nodes.get(BORROWER_ID)!;
    if (!b.registered) return 'register';
    const loan = [...s.loans].reverse().find((l) => l.borrower === BORROWER_ID);
    if (loan?.status === 'SETTLED') return 'settled';
    if (loan?.status === 'DEFAULTED') return 'defaulted';
    if (loan?.status === 'DISBURSED') return s.day >= (loan.dueDay ?? 0) ? 'outcome' : 'advance';
    if (loan?.status === 'APPLIED') return 'approve';
    if (s.edges.some((e) => e.to === BORROWER_ID)) return 'apply';
    if (s.requests.some((r) => r.from === BORROWER_ID && r.status === 'PENDING')) return 'vouch';
    return 'request';
  }

  private build(): Snapshot {
    const s = this.state;
    this.version += 1;
    const graphNodes = this.graphNodes();
    const weights = edgeWeights(graphNodes, s.edges);
    const nodes: Record<string, ApiNode> = {};
    for (const rec of s.nodes.values()) {
      const inbound = s.edges.some((e) => e.to === rec.seed.id);
      nodes[rec.seed.id] = {
        id: rec.seed.id,
        kind: rec.seed.kind,
        name: rec.seed.name,
        role: rec.seed.role,
        place: rec.seed.place,
        cluster: rec.seed.cluster,
        R: rec.R.toString(),
        capacity: capacity(rec.R).toString(),
        status: rec.status,
        coldStart: rec.registered && rec.seed.kind === 'person' && rec.status === 'ACTIVE' && rec.R.isZero() && !inbound && rec.settledLoans === 0 && !rec.sources.aa && !rec.sources.utility,
        nullifier: rec.nullifier,
        joinedDay: rec.joinedDay,
        settledLoans: rec.settledLoans,
        sources: { ...rec.sources },
      };
    }
    const assessments: Record<string, ApiAssessment> = {};
    for (const rec of s.nodes.values()) {
      if (rec.registered && rec.seed.kind === 'person') assessments[rec.seed.id] = this.assess(rec.seed.id);
    }
    const members = (cid: string) =>
      [...s.nodes.values()].filter((n) => n.registered && n.seed.kind === 'person' && n.seed.cluster === cid);
    return {
      version: this.version,
      day: s.day,
      block: s.block,
      nodes,
      edges: s.edges
        .filter((e) => s.nodes.get(e.from)!.registered && s.nodes.get(e.to)!.registered)
        .map((e) => ({ ...e, weight: (weights.get(edgeKey(e.from, e.to)) ?? D(0)).toString() })),
      loans: s.loans.map((l) => ({
        id: l.id,
        borrower: l.borrower,
        principal: inr(l.principal),
        emi: inr(demoEmi(l.principal)),
        purpose: l.purpose,
        status: l.status,
        appliedDay: l.appliedDay,
        disbursedDay: l.disbursedDay,
        dueDay: l.dueDay,
        closedDay: l.closedDay,
        delta0: delta0For(l.principal).toString(),
        slashQueued: l.slashQueued,
      })),
      requests: s.requests.map((r) => ({ ...r })),
      events: s.events.map((e) => ({ ...e })),
      clusters: s.clusters.map((c) => ({
        id: c.id,
        name: c.name,
        members: members(c.id).map((n) => n.seed.id),
        defaulted: members(c.id).filter((n) => n.status === 'DEFAULTED').length,
        tripped: c.tripped,
        queued: [...c.queued],
      })),
      assessments,
      borrowerId: BORROWER_ID,
      voucherId: VOUCHER_ID,
      lenderId: LENDER_ID,
      story: this.story(),
      lastCascade: s.lastCascade,
    };
  }
}
