import { useMemo } from 'react';
import { useNavigate } from 'react-router';
import Decimal from 'decimal.js';
import { useSnapshot } from '@/state/DemoProvider';
import type { ApiLoan } from '@/api/types';
import { Card, CardHead } from '@/components/ui/Card';
import { Avatar } from '@/components/ui/Avatar';
import { Badge, StatusBadge } from '@/components/ui/StatusBadge';
import { IconAnchor, IconChevronRight } from '@/components/icons';
import { dayDate, fmt, formatMoney, inr } from '@/lib/format';
import { BandChip } from '@/features/score/BandChip';
import { BreakerBanner } from '@/features/lender/BreakerBanner';
import { TrustGraph } from '@/features/graph/TrustGraph';
import { LiveBook } from '@/features/lender/LiveBook';
import { SourceBadge } from '@/components/ui/SourceBadge';
import { Explain } from '@/features/explain/Explain';
import type { FormulaId } from '@/features/explain/formulas';

const loanTone = { APPLIED: 'neel', DISBURSED: 'plain', SETTLED: 'active', DEFAULTED: 'defaulted', DECLINED: 'plain' } as const;
const HEADERS: [string, FormulaId | null][] = [
  ['Applicant', null],
  ['Asked', null],
  ['Lendable score · band', 'lcb'],
  ['Uncertainty σ²', 'sigma2'],
  ['Model limit', 'limit'],
  ['Vouches', null],
  ['', null],
];
const loanLabel = { APPLIED: 'Awaiting decision', DISBURSED: 'Disbursed', SETTLED: 'Repaid', DEFAULTED: 'Defaulted', DECLINED: 'Declined' };

export function LenderPage() {
  const s = useSnapshot();
  const navigate = useNavigate();
  const lender = s.nodes[s.lenderId]!;

  const applied = s.loans.filter((l) => l.status === 'APPLIED').sort((a, b) => b.appliedDay - a.appliedDay);
  const book = s.loans.filter((l) => l.status !== 'APPLIED' && l.status !== 'DECLINED').sort((a, b) => (b.closedDay ?? b.disbursedDay ?? 0) - (a.closedDay ?? a.disbursedDay ?? 0));
  const outstanding = s.loans.filter((l) => l.status === 'DISBURSED').reduce((sum, l) => sum.plus(l.principal.amount), new Decimal(0));
  const network = useMemo(() => [...Object.keys(s.assessments), ...Object.values(s.nodes).filter((n) => n.kind === 'anchor').map((n) => n.id)], [s.assessments, s.nodes]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="flex items-center gap-4">
          <Avatar node={lender} size={54} />
          <div>
            <p className="eyebrow">Lender console · institutional anchor</p>
            <h1 className="display mt-1 text-[38px] leading-none">{lender.name}</h1>
            <p className="mt-2 text-[13.5px] text-ink-2">
              Anchor credibility R {fmt(lender.R)} · trust in this network starts with institutions that put capital at risk
            </p>
          </div>
        </div>
        <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-[12px] border border-rule bg-rule">
          {[
            ['Applications', String(applied.length)],
            ['Outstanding', formatMoney(inr(outstanding.toString()))],
            ['Network', `${Object.keys(s.assessments).length} people`],
          ].map(([k, v]) => (
            <div key={k} className="min-w-[130px] bg-surface px-4 py-2.5">
              <dt className="text-[11.5px] text-ink-3">{k}</dt>
              <dd className="num text-[18px] font-medium">{v}</dd>
            </div>
          ))}
        </dl>
      </div>

      <LiveBook />

      <BreakerBanner s={s} />

      <Card className="overflow-hidden">
        <div className="px-6 pt-6">
          <CardHead eyebrow="Decide with both axes" title="Applications" />
        </div>
        <ul className="mt-4 border-t border-rule md:hidden">
          {applied.length === 0 ? (
            <li className="px-6 py-10 text-center text-ink-3">No open applications.</li>
          ) : (
            applied.map((l) => <ApplicationCard key={l.id} loan={l} onOpen={() => navigate(`/app/lender/${l.borrower}`)} />)
          )}
        </ul>
        <div className="mt-4 hidden overflow-x-auto md:block">
          <table className="w-full min-w-[860px] text-[13.5px]">
            <thead>
              <tr className="border-y border-rule bg-paper/60 text-left">
                {HEADERS.map(([h, id]) => (
                  <th key={h} className="eyebrow px-6 py-2.5 font-medium first:pl-6">
                    {id ? <Explain id={id}>{h}</Explain> : h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {applied.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-10 text-center text-ink-3">
                    No open applications.
                  </td>
                </tr>
              ) : (
                applied.map((l) => <ApplicationRow key={l.id} loan={l} onOpen={() => navigate(`/app/lender/${l.borrower}`)} />)
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-12">
        <Card className="p-6 lg:col-span-12">
          <CardHead
            eyebrow="Whole network"
            title="Who vouches for whom"
            aside={
              <span className="flex flex-wrap gap-2">
                <Badge tone="active">Active</Badge>
                <Badge tone="restricted">Restricted</Badge>
                <Badge tone="defaulted">Defaulted</Badge>
                <Badge tone="cold">Cold start</Badge>
              </span>
            }
          />
          <div className="mt-4">
            <TrustGraph s={s} nodeIds={network} cascade={s.lastCascade} maxHeight={640} onNodeClick={(id) => s.assessments[id] && navigate(`/app/lender/${id}`)} />
          </div>
          <p className="mt-2 flex items-center gap-2 text-[12.5px] text-ink-3">
            <IconAnchor size={14} /> Squares are institutional anchors. Edge labels are <Explain id="rGraph">vouch weights W = C / |Out|</Explain>. Click a
            person to open their file.
          </p>
        </Card>
        <Card className="p-6 lg:col-span-12">
          <CardHead eyebrow="Book" title="Loans" aside={<SourceBadge live={false} />} />
          <ul className="mt-3 grid gap-x-8 md:grid-cols-2 [&>li]:border-b [&>li]:border-rule">
            {book.map((l) => (
              <li key={l.id} className="flex items-center gap-3 py-3">
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13.5px] font-medium">{s.nodes[l.borrower]!.name}</span>
                  <span className="block font-mono text-[11.5px] text-ink-3">
                    {l.id} · {dayDate(l.closedDay ?? l.disbursedDay ?? l.appliedDay)}
                    {l.slashQueued ? ' · slash queued' : ''}
                  </span>
                </span>
                <span className="num text-[13px] font-medium">{formatMoney(l.principal)}</span>
                <Badge tone={loanTone[l.status]}>{loanLabel[l.status]}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

function ApplicationCard({ loan, onOpen }: { loan: ApiLoan; onOpen: () => void }) {
  const s = useSnapshot();
  const n = s.nodes[loan.borrower]!;
  const a = s.assessments[loan.borrower]!;
  const fits = new Decimal(a.limit.amount).gte(loan.principal.amount);
  return (
    <li className="border-b border-rule last:border-0">
      <button type="button" onClick={onOpen} className="w-full px-5 py-4 text-left transition-colors hover:bg-paper/70">
        <span className="flex items-center gap-3">
          <Avatar node={n} size={34} />
          <span className="min-w-0 flex-1">
            <span className="flex items-center gap-2 font-medium">
              {n.name} <StatusBadge node={n} />
            </span>
            <span className="block truncate text-[12px] text-ink-3">
              {n.role} · {loan.purpose}
            </span>
          </span>
          <IconChevronRight size={18} className="shrink-0 text-ink-3" />
        </span>
        <span className="mt-3 grid grid-cols-3 gap-3 text-[12px]">
          <span>
            <span className="eyebrow block">Asked</span>
            <span className="num mt-1 block text-[14px] font-medium">{formatMoney(loan.principal)}</span>
          </span>
          <span>
            <span className="eyebrow block">Limit</span>
            <span className={`num mt-1 block text-[14px] font-medium ${fits ? 'text-active' : 'text-restricted-ink'}`}>{formatMoney(a.limit)}</span>
          </span>
          <span>
            <span className="eyebrow block">Score · σ²</span>
            <span className="num mt-1 block font-mono text-[13px]">
              {fmt(a.lcb)} · {fmt(a.sigma2)}
            </span>
          </span>
        </span>
      </button>
    </li>
  );
}

function ApplicationRow({ loan, onOpen }: { loan: ApiLoan; onOpen: () => void }) {
  const s = useSnapshot();
  const n = s.nodes[loan.borrower]!;
  const a = s.assessments[loan.borrower]!;
  const fits = new Decimal(a.limit.amount).gte(loan.principal.amount);
  return (
    <tr onClick={onOpen} className="group cursor-pointer border-b border-rule transition-colors last:border-0 hover:bg-paper/70">
      <td className="px-6 py-3.5">
        <span className="flex items-center gap-3">
          <Avatar node={n} size={34} />
          <span>
            <span className="flex items-center gap-2 font-medium">
              {n.name} <StatusBadge node={n} />
            </span>
            <span className="block text-[12px] text-ink-3">
              {n.role} · {loan.purpose}
            </span>
          </span>
        </span>
      </td>
      <td className="num px-6 font-medium">{formatMoney(loan.principal)}</td>
      <td className="px-6">
        <BandChip a={a} />
      </td>
      <td className="num px-6 font-mono">{fmt(a.sigma2)}</td>
      <td className="px-6">
        <span className={`num font-medium ${fits ? 'text-active' : 'text-restricted-ink'}`}>{formatMoney(a.limit)}</span>
        <span className="block text-[11.5px] text-ink-3">{fits ? 'covers the ask' : 'below the ask'}</span>
      </td>
      <td className="num px-6">{a.inDegree}</td>
      <td className="px-6 text-right">
        <IconChevronRight size={18} className="text-ink-3 transition-transform group-hover:translate-x-0.5 group-hover:text-ink" />
      </td>
    </tr>
  );
}
