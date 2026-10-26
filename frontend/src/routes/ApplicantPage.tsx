import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import Decimal from 'decimal.js';
import { api } from '@/api/client';
import { useSnapshot } from '@/state/DemoProvider';
import type { ApiCascade, Snapshot } from '@/api/types';
import { Card, CardHead } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/StatusBadge';
import { IconArrowLeft, IconCheck, IconClose, IconRipple, IconAlert, IconBreaker } from '@/components/icons';
import { dayDate, fmt, fmtSigned, formatMoney } from '@/lib/format';
import { Explain } from '@/features/explain/Explain';
import { PersonHeader } from '@/features/shared/PersonHeader';
import { ScoreGauge } from '@/features/score/ScoreGauge';
import { PathList } from '@/features/graph/PathList';
import { TrustGraph, neighbourhood } from '@/features/graph/TrustGraph';

export function ApplicantPage() {
  const { nodeId = '' } = useParams();
  const s = useSnapshot();
  const node = s.nodes[nodeId];
  const a = s.assessments[nodeId];
  const [hoverPath, setHoverPath] = useState<number | null>(null);
  const cascade = s.lastCascade && (s.lastCascade.defaulter === nodeId || s.lastCascade.penalties.some((p) => p.node === nodeId)) ? s.lastCascade : null;
  const ids = useMemo(() => (node ? neighbourhood(s, cascade?.defaulter ?? nodeId, cascade) : []), [s, nodeId, node, cascade]);

  if (!node || !a) {
    return (
      <div className="py-24 text-center">
        <p className="display text-[30px]">Not on the graph yet</p>
        <p className="mt-2 text-ink-2">This person hasn’t anchored an identity.</p>
        <Link to="/app/lender" className="mt-6 inline-block text-neel-700 underline">
          Back to applications
        </Link>
      </div>
    );
  }

  const live = a.paths.filter((p) => Number(p.trust) > 0);
  const highlight = hoverPath === null ? live.map((p) => p.nodes) : [live[hoverPath]!.nodes];
  const loan = [...s.loans].reverse().find((l) => l.borrower === nodeId);

  return (
    <div className="space-y-6">
      <Link to="/app/lender" className="inline-flex items-center gap-1.5 text-[13px] text-ink-3 hover:text-ink">
        <IconArrowLeft size={15} /> Applications
      </Link>
      <PersonHeader node={node} seat="Applicant file" />

      <div className="grid gap-5 xl:grid-cols-12 xl:items-start">
        <Card className={`p-6 xl:col-span-7 ${cascade ? '' : 'xl:sticky xl:top-[120px]'}`}>
          <CardHead
            eyebrow={cascade ? 'Default cascade' : 'Trust paths into this file'}
            title={cascade ? 'Penalties stop at two hops' : 'Where the trust comes from'}
            aside={<span className="font-mono text-[11.5px] text-ink-3">Trust(P) = W₀₁ · Π (W · 0.5)</span>}
          />
          <div className="mt-4">
            <TrustGraph s={s} nodeIds={ids} focus={nodeId} highlight={cascade ? [] : highlight} cascade={cascade} maxHeight={600} />
          </div>
          {cascade ? <CascadeTable s={s} c={cascade} /> : null}
        </Card>

        <div className="space-y-5 xl:col-span-5">
          <Card className="p-6">
            <ScoreGauge a={a} node={node} compact />
          </Card>
          <Card className="p-6">
            <CardHead eyebrow="Interpretable by construction" title="Why this score" />
            <div className="mt-3">
              <PathList a={a} s={s} onHover={setHoverPath} active={hoverPath} />
            </div>
            <CashflowRows s={s} nodeId={nodeId} />
          </Card>
          <DecisionCard s={s} nodeId={nodeId} loanId={loan?.id ?? null} />
        </div>
      </div>
    </div>
  );
}

function CashflowRows({ s, nodeId }: { s: Snapshot; nodeId: string }) {
  const a = s.assessments[nodeId]!;
  const cf = a.cashflow;
  return (
    <div className="mt-5 rounded-[10px] bg-paper p-4">
      <p className="eyebrow">Cash flow (Account Aggregator, simulated)</p>
      {cf ? (
        <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1.5 text-[13px]">
          <dt className="text-ink-3">Mean monthly income</dt>
          <dd className="num text-right">{formatMoney(cf.meanIncome)}</dd>
          <dt className="text-ink-3">Debt service incl. new EMI</dt>
          <dd className="num text-right">{formatMoney(cf.debtService)}</dd>
          <dt className="text-ink-3">DSCR</dt>
          <dd className={`num text-right font-mono ${Number(cf.dscr) >= 1.25 ? 'text-active' : 'text-defaulted'}`}>{fmt(cf.dscr)}×</dd>
          <dt className="text-ink-3">Income variation</dt>
          <dd className="num text-right font-mono">{fmt(cf.incomeCv)}</dd>
          <dt className="text-ink-3">
            <Explain id="cashflow">Cash-flow score</Explain>
          </dt>
          <dd className="num text-right font-mono">{fmt(cf.sCashflow)}</dd>
        </dl>
      ) : (
        <p className="mt-2 text-[13px] text-ink-2">
          Not linked. Missing data is <b>not</b> imputed: it stays as uncertainty (σ² {fmt(a.sigma2)}), never as a bad mark.
        </p>
      )}
      <p className="mt-3 font-mono text-[11px] text-ink-3">
        μ = (0.6·R_graph + 0.4·S_cf) · e^(0.1·({a.nSettled} settled + {a.inDegree} vouches)) · σ² = 1/(1 + {a.nData}·{fmt(a.completeness)})
      </p>
    </div>
  );
}

function DecisionCard({ s, nodeId, loanId }: { s: Snapshot; nodeId: string; loanId: string | null }) {
  const [busy, setBusy] = useState<string | null>(null);
  const a = s.assessments[nodeId]!;
  const node = s.nodes[nodeId]!;
  const loan = s.loans.find((l) => l.id === loanId);

  if (!loan) {
    return (
      <Card className="p-6">
        <CardHead eyebrow="Decision" title="No application on file" />
        <p className="mt-2 text-[13.5px] text-ink-2">Model limit today: {formatMoney(a.limit)}.</p>
      </Card>
    );
  }

  if (loan.status !== 'APPLIED') {
    const tone = loan.status === 'SETTLED' ? 'active' : loan.status === 'DEFAULTED' ? 'defaulted' : 'neel';
    return (
      <Card className="p-6">
        <CardHead eyebrow={`Decision · ${loan.id}`} title={`${formatMoney(loan.principal)} ${loan.status.toLowerCase()}`} aside={<Badge tone={tone}>{loan.status}</Badge>} />
        <p className="mt-2 text-[13.5px] text-ink-2">
          {loan.status === 'DISBURSED'
            ? `Released ${dayDate(loan.disbursedDay!)}, due ${dayDate(loan.dueDay!)}. Backing vouches are locked until it closes.`
            : loan.status === 'SETTLED'
              ? 'Repaid in full. The borrower earned credibility; sponsors earned yield.'
              : loan.slashQueued
                ? 'Defaulted while the cluster breaker was open: the slash is queued for review.'
                : 'Defaulted. The damped cascade has been applied; see the graph.'}
        </p>
      </Card>
    );
  }

  const fits = new Decimal(a.limit.amount).gte(loan.principal.amount);
  const canLend = new Decimal(a.limit.amount).gt(0) && node.status !== 'DEFAULTED';
  return (
    <Card className="border-neel-200 p-6 shadow-[var(--shadow-lift)]">
      <CardHead eyebrow={`Decision · ${loan.id}`} title={`${formatMoney(loan.principal)} for ${loan.purpose.toLowerCase()}`} />
      <dl className="mt-4 grid grid-cols-2 gap-y-1.5 text-[13.5px]">
        <dt className="text-ink-3">
          <Explain id="limit">Model limit</Explain>
        </dt>
        <dd className={`num text-right font-medium ${fits ? 'text-active' : 'text-restricted-ink'}`}>{formatMoney(a.limit)}</dd>
        <dt className="text-ink-3">
          <Explain id="emi">6 instalments of</Explain>
        </dt>
        <dd className="num text-right">{formatMoney(loan.emi, 2)}</dd>
        <dt className="text-ink-3">
          <Explain id="cascade">If it defaults, Δ₀</Explain>
        </dt>
        <dd className="num text-right font-mono">{fmtSigned(`-${loan.delta0}`)}</dd>
      </dl>
      <div className="mt-5 flex flex-wrap gap-3">
        {fits ? (
          <Button size="lg" className="flex-1" icon={<IconCheck size={17} />} loading={busy === 'ok'} onClick={async () => { setBusy('ok'); await api.decideLoan(loan.id, true); setBusy(null); }}>
            Approve {formatMoney(loan.principal)}
          </Button>
        ) : canLend ? (
          <Button size="lg" className="flex-1" icon={<IconCheck size={17} />} loading={busy === 'ok'} onClick={async () => { setBusy('ok'); await api.decideLoan(loan.id, true, a.limit.amount); setBusy(null); }}>
            Offer {formatMoney(a.limit)} instead
          </Button>
        ) : null}
        <Button size="lg" variant="secondary" icon={<IconClose size={16} />} loading={busy === 'no'} onClick={async () => { setBusy('no'); await api.decideLoan(loan.id, false); setBusy(null); }}>
          Decline
        </Button>
      </div>
      {!canLend ? (
        <p className="mt-3 flex items-start gap-1.5 text-[12.5px] text-ink-3">
          <IconAlert size={14} className="mt-0.5 shrink-0" /> The lower bound is below the lending floor. That is a reason to wait for a vouch or data, not a judgement of character.
        </p>
      ) : null}
    </Card>
  );
}

function CascadeTable({ s, c }: { s: Snapshot; c: ApiCascade }) {
  if (c.queued) {
    return (
      <div className="mt-4 flex items-start gap-3 rounded-[10px] bg-restricted-tint p-4 text-[13.5px]">
        <IconBreaker size={18} className="mt-0.5 shrink-0 text-restricted-ink" />
        Default recorded with the cluster breaker open. No penalties applied; the slash for {c.loanId} waits for review.
      </div>
    );
  }
  const label = ['Defaulter', 'Direct sponsor', 'Sponsor’s sponsor'];
  const rule = ['Δ₀', 'γ · W · Δ₀', 'γ² · Δ₀'];
  return (
    <div className="mt-4">
      <p className="eyebrow mb-2 flex items-center gap-1.5">
        <IconRipple size={14} /> Applied in one atomic step · {dayDate(c.day)}
      </p>
      <table className="w-full text-[13px]">
        <tbody>
          {c.penalties.map((p) => (
            <tr key={p.node} className="border-b border-rule">
              <td className="py-2">
                <span className="font-mono text-[11.5px] text-ink-3">k={p.k}</span> <b className="font-medium">{s.nodes[p.node]!.name}</b>
                <span className="text-ink-3"> · {label[p.k]}</span>
              </td>
              <td className="py-2 font-mono text-[11.5px] text-ink-3">{rule[p.k]}</td>
              <td className="num py-2 text-right font-mono text-defaulted">{fmtSigned(`-${p.delta}`)}</td>
              <td className="num py-2 text-right font-mono text-ink-2">
                {fmt(p.before)} → {fmt(p.after)}
              </td>
            </tr>
          ))}
          <tr>
            <td className="py-2 text-ink-3" colSpan={2}>
              <span className="font-mono text-[11.5px]">k≥3</span> everyone else
            </td>
            <td className="py-2 text-right font-mono text-neel-700" colSpan={2}>
              0.00 · isolated
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
