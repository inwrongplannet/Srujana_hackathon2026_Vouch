import Decimal from 'decimal.js';
import type { ReactNode } from 'react';
import type { AssessmentResult, CombinedAssessment, Factor } from '@/api/backend';
import { Card, CardHead } from '@/components/ui/Card';
import { Badge, type Tone } from '@/components/ui/StatusBadge';
import { formatMoney, inr } from '@/lib/format';

/** A backend decimal string in rupees, formatted; "—" when the backend sent none. */
export function rupees(amount: string | null | undefined, dp = 0): string {
  return amount === null || amount === undefined ? '—' : formatMoney(inr(amount), dp);
}

/** The backend sends some ratios as JSON numbers; format them without arithmetic on floats. */
function score(value: number | string, dp = 1): string {
  return new Decimal(String(value)).toFixed(dp, Decimal.ROUND_HALF_EVEN);
}

const words = (code: string) => code.toLowerCase().replaceAll('_', ' ');

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-ink-3">{label}</dt>
      <dd className="num text-right">{children}</dd>
    </>
  );
}

function Signal({ n, title, badge, children }: { n: number; title: string; badge: ReactNode; children: ReactNode }) {
  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="eyebrow">Signal {n}</p>
        {badge}
      </div>
      <h3 className="display mt-1.5 text-[20px] leading-tight">{title}</h3>
      <div className="mt-3 flex-1 text-[13px]">{children}</div>
    </Card>
  );
}

/** The four signals side by side, never blended into one number (Vouch documentation). */
export function Signals({ r, detail }: { r: AssessmentResult; detail: CombinedAssessment | null }) {
  const bureauTone: Tone = r.bureau_status === 'AVAILABLE' ? 'neel' : 'cold';
  const stress = r.stress_resilience;
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Signal n={1} title="Credit bureau" badge={<Badge tone={bureauTone}>{words(r.bureau_status)}</Badge>}>
        {r.bureau_score !== null ? (
          <p className="num display text-[34px] leading-none">{r.bureau_score}</p>
        ) : (
          <p className="text-ink-2">No bureau file. Recorded as <b>unknown</b>, not as a bad mark.</p>
        )}
      </Signal>

      <Signal
        n={2}
        title="Vouch Score"
        badge={detail ? <Badge tone="neel">{words(detail.vouch.confidence)} confidence</Badge> : null}
      >
        <p className="num display text-[34px] leading-none">
          {score(r.vouch_score)}
          <span className="text-[15px] text-ink-3"> / 100</span>
        </p>
        {detail ? (
          <dl className="mt-3 grid grid-cols-2 gap-y-1">
            <Row label="Endorsements counted">{detail.vouch.eligible_endorsements}</Row>
            <Row label="Standing">{words(detail.vouch.status)}</Row>
            <Row label="Outcome quality">{score(detail.vouch.quality_factor, 2)}</Row>
          </dl>
        ) : null}
        {r.vouch_score === 0 ? <p className="mt-2 text-ink-3">Nobody has vouched yet: that is missing evidence, not risk.</p> : null}
      </Signal>

      <Signal n={3} title="Affordability" badge={<Badge tone="plain">{words(r.affordability.status)}</Badge>}>
        <dl className="grid grid-cols-2 gap-y-1">
          <Row label="Disposable a month">{rupees(r.affordability.disposable_income)}</Row>
          <Row label="Largest safe EMI">{rupees(r.affordability.max_affordable_emi)}</Row>
          <Row label="Cash kept aside">{rupees(r.affordability.protected_cash_buffer)}</Row>
        </dl>
        {stress ? (
          <p className="mt-3 text-ink-2">
            Stress test: <b className="font-medium">{words(stress.rating)}</b>, shortfall in {score(new Decimal(String(stress.shortfall_probability)).mul(100).toString(), 1)}% of
            simulated futures; survives an income fall of {score(stress.income_shock_tolerance_percent, 1)}%.
          </p>
        ) : null}
      </Signal>

      <Signal
        n={4}
        title="Evidence"
        badge={detail ? <Badge tone={detail.data_quality === 'LOW' ? 'restricted' : 'active'}>{words(detail.data_quality)}</Badge> : null}
      >
        {r.missing_information.length ? (
          <ul className="space-y-1.5 text-ink-2">
            {r.missing_information.map((m) => (
              <li key={m}>Missing: {m}</li>
            ))}
          </ul>
        ) : (
          <p className="text-ink-2">Nothing the rules need is missing.</p>
        )}
        {r.review_flags.length ? (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {r.review_flags.map((f) => (
              <Badge key={f} tone="restricted">
                {words(f)}
              </Badge>
            ))}
          </div>
        ) : null}
      </Signal>
    </div>
  );
}

export function Plan({ r }: { r: AssessmentResult }) {
  const p = r.best_plan;
  return (
    <Card className="p-6">
      <CardHead
        eyebrow={`Assessment ${r.assessment_id}`}
        title={r.verdict === 'APPROVED' ? 'The request fits as asked' : p ? 'It fits as a different plan' : 'No plan fits yet'}
        aside={<Badge tone={r.verdict === 'APPROVED' ? 'active' : 'restricted'}>{words(r.verdict)}</Badge>}
      />
      {p ? (
        <dl className="mt-4 grid grid-cols-2 gap-y-1.5 text-[13.5px]">
          <Row label="Amount">{rupees(p.principal)}</Row>
          <Row label="Months">{p.term_months ?? '—'}</Row>
          <Row label="Monthly EMI">{rupees(p.monthly_emi, 2)}</Row>
          <Row label="Total interest">{rupees(p.total_interest, 2)}</Row>
        </dl>
      ) : (
        <p className="mt-3 text-[13.5px] text-ink-2">No amount and tenure passes the affordability rules within the limit.</p>
      )}
      <p className="mt-4 text-[12.5px] text-ink-3">Decision support only. A person decides.</p>
    </Card>
  );
}

function FactorList({ title, items, tone }: { title: string; items: Factor[]; tone: Tone }) {
  return (
    <div>
      <p className="eyebrow">{title}</p>
      {items.length ? (
        <ul className="mt-2 space-y-2.5">
          {items.map((f) => (
            <li key={f.code} className="text-[13.5px]">
              <Badge tone={tone} className="mr-2">
                {words(f.code)}
              </Badge>
              <span className="text-ink-2">{f.text}</span>
              <span className="ml-1 font-mono text-[11px] text-ink-3">· {words(f.source)}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-[13px] text-ink-3">None.</p>
      )}
    </div>
  );
}

export function Reasons({ r }: { r: AssessmentResult }) {
  return (
    <Card className="p-6">
      <CardHead eyebrow="Each reason cites its source" title="Why" />
      <div className="mt-4 grid gap-6 md:grid-cols-2">
        <FactorList title="In favour" items={r.positive_factors} tone="active" />
        <FactorList title="Against" items={r.risk_factors} tone="defaulted" />
      </div>
    </Card>
  );
}
