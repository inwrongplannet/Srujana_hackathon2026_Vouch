import { describe, expect, it } from 'vitest';
import { MockServer } from './server';
import { BORROWER_ID } from './seed';

async function vouchedWorld() {
  const s = new MockServer('test-salt');
  await s.ready;
  await s.register('000000004821');
  s.requestVouch(BORROWER_ID, 'p_meena', 'note');
  s.respondVouch(s.getSnapshot().requests[0].id, true);
  return s;
}

describe('demo story on the mock server', () => {
  it('a cold-start registration has sigma2 1 and no limit', async () => {
    const s = new MockServer('test-salt');
    await s.ready;
    await s.register('000000004821');
    const a = s.getSnapshot().assessments[BORROWER_ID];
    expect(a.sigma2).toBe('1');
    expect(a.limit.amount).toBe('0');
    expect(s.getSnapshot().nodes[BORROWER_ID].coldStart).toBe(true);
  });

  it("Meena's vouch dilutes her edges to 0.7 and gives R_graph 2.45 and a INR 6,000 limit", async () => {
    const s = await vouchedWorld();
    const snap = s.getSnapshot();
    expect(snap.edges.filter((e) => e.from === 'p_meena').map((e) => e.weight)).toEqual(['0.7', '0.7', '0.7', '0.7']);
    // sahyog -> ramesh -> meena -> lakshmi: 4 * 1 * 0.35 = 1.4; jyoti -> meena -> lakshmi: 3 * 0.35 = 1.05.
    expect(snap.assessments[BORROWER_ID].rGraph).toBe('2.45');
    expect(snap.assessments[BORROWER_ID].limit.amount).toBe('6000');
  });

  it('re-registering the same demo ID resolves to the same record (anti-churn)', async () => {
    const s = new MockServer('test-salt');
    await s.ready;
    const res = await s.register('000000000007');
    expect(res.existing).toBe(true);
    expect(res.node.status).toBe('DEFAULTED');
  });

  it('a default cascades to hop 2 and stops: sponsor -0.35, ancestors -0.25, hop 3 untouched', async () => {
    const s = await vouchedWorld();
    s.applyLoan(BORROWER_ID, '5000', 'Motor');
    const loan = s.getSnapshot().loans.find((l) => l.borrower === BORROWER_ID)!;
    s.decideLoan(loan.id, true);
    s.advance(30);
    s.defaultLoan(loan.id);
    const n = s.getSnapshot().nodes;
    expect(n[BORROWER_ID].R).toBe('-1');
    expect(n[BORROWER_ID].status).toBe('DEFAULTED');
    expect(n.p_meena.R).toBe('2.45');
    expect(n.p_ramesh.R).toBe('3.75');
    expect(n.a_jyoti.R).toBe('5.75');
    expect(n.p_anita.R).toBe('0.15');
    expect(n.a_sahyog.R).toBe('8');
  });

  it('repayment mints credibility to the borrower and yield to the sponsor', async () => {
    const s = await vouchedWorld();
    s.applyLoan(BORROWER_ID, '5000', 'Motor');
    const loan = s.getSnapshot().loans.find((l) => l.borrower === BORROWER_ID)!;
    s.decideLoan(loan.id, true);
    s.settle(loan.id);
    const n = s.getSnapshot().nodes;
    expect(n[BORROWER_ID].R).toBe('0.5');
    expect(n.p_meena.R).toBe('2.9');
  });

  it('a regional shock trips the breaker and queues the third slash', async () => {
    const s = new MockServer('test-salt');
    await s.ready;
    s.regionalShock();
    const snap = s.getSnapshot();
    const gadag = snap.clusters.find((c) => c.id === 'gadag')!;
    expect(gadag.tripped).toBe(true);
    expect(gadag.queued).toEqual(['L-1990']);
    expect(snap.nodes.p_girija.R).toBe('1');
  });
});

describe('vouch preview', () => {
  it("prices Meena's exposure on Lakshmi: W 0.7, default -0.35, yield +0.1, limit 0 -> 6,000", async () => {
    const s = new MockServer('test-salt');
    await s.ready;
    await s.register('000000004821');
    const p = s.previewVouch('p_meena', BORROWER_ID);
    expect(p.weightBefore).toBe('0.9333333333333333333333333333333333333333');
    expect(p.weightAfter).toBe('0.7');
    expect(p.penaltyIfDefault).toBe('0.35');
    expect(p.yieldIfRepaid).toBe('0.1');
    expect(p.requesterBefore.limit.amount).toBe('0');
    expect(p.requesterAfter.limit.amount).toBe('6000');
    // Preview never commits.
    expect(s.getSnapshot().edges.some((e) => e.to === BORROWER_ID)).toBe(false);
  });
});
