import { useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import type { SimulateResponse, Snapshot } from '@/api/types';
import { Card, CardHead } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/StatusBadge';
import { InkDots } from '@/components/ui/InkDots';
import { IconBulb, IconCheck, IconSliders, IconStatement, IconAlert } from '@/components/icons';
import { fmt, formatMoney, geom, inr } from '@/lib/format';

/** Linked data sources narrow the band; the what-if shows cash flow, the axis goodwill can't cover. */
export function StrengthenPanel({ s }: { s: Snapshot }) {
  const me = s.borrowerId;
  const node = s.nodes[me]!;
  const a = s.assessments[me]!;
  const [preview, setPreview] = useState<{ aa: SimulateResponse | null; util: SimulateResponse | null }>({ aa: null, util: null });

  useEffect(() => {
    let alive = true;
    void Promise.all([api.simulate({ nodeId: me, aa: true }), api.simulate({ nodeId: me, aa: true, utility: true })]).then(([aa, util]) => {
      if (alive) setPreview({ aa, util });
    });
    return () => {
      alive = false;
    };
  }, [me, s.version]);

  return (
    <Card className="p-6">
      <CardHead eyebrow="Strengthen your file" title="Data narrows the band" />
      <p className="mt-2 max-w-[70ch] text-[14px] text-ink-2">
        Vouches say who trusts you. Cash flow says whether a repayment fits. Each verified source shrinks your uncertainty, so your
        lendable score moves up even if nothing else changes.
      </p>
      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="grid gap-4">
        <SourceCard
          icon={<IconStatement size={20} />}
          title="Bank and UPI statements"
          via="Account Aggregator · simulated"
          detail="6 months of income, obligations and net flow. Consent-based, read-only."
          linked={node.sources.aa}
          from={a.sigma2}
          to={preview.aa?.assessment.sigma2}
          limitTo={preview.aa ? formatMoney(preview.aa.assessment.limit) : null}
          onLink={() => api.linkSource(me, 'aa')}
        />
        <SourceCard
          icon={<IconBulb size={20} />}
          title="Utility payment cadence"
          via="Jyoti Power Co-op · simulated"
          detail="11 of the last 12 electricity bills paid on time."
          linked={node.sources.utility}
          from={node.sources.aa ? a.sigma2 : preview.aa?.assessment.sigma2}
          to={preview.util?.assessment.sigma2}
          limitTo={preview.util ? formatMoney(preview.util.assessment.limit) : null}
          disabled={!node.sources.aa}
          onLink={() => api.linkSource(me, 'utility')}
        />
        </div>
        <WhatIf nodeId={me} version={s.version} />
      </div>
    </Card>
  );
}

function SourceCard({
  icon,
  title,
  via,
  detail,
  linked,
  from,
  to,
  limitTo,
  disabled,
  onLink,
}: {
  icon: React.ReactNode;
  title: string;
  via: string;
  detail: string;
  linked: boolean;
  from?: string;
  to?: string;
  limitTo: string | null;
  disabled?: boolean;
  onLink: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <div className={`flex flex-col rounded-[12px] border p-5 ${linked ? 'border-active/30 bg-active-tint/40' : 'border-rule bg-paper/60'}`}>
      <div className="flex items-start gap-4">
        <span className={`grid size-10 shrink-0 place-items-center rounded-[10px] ${linked ? 'bg-active text-surface' : 'bg-neel-50 text-neel-700'}`}>{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-medium">{title}</p>
              <p className="text-[12px] text-ink-3">{via}</p>
            </div>
            {linked ? <Badge tone="active">Linked</Badge> : <Badge tone="plain">Not linked</Badge>}
          </div>
          <p className="mt-2 text-[13px] text-ink-2">{detail}</p>
        </div>
      </div>
      {!linked ? (
        <>
          {from && to ? (
            <p className="num mt-3 font-mono text-[12.5px] text-ink-2">
              σ² {fmt(from)} → <b className="text-neel-700">{fmt(to)}</b>
              {limitTo ? <span className="text-ink-3"> · limit {limitTo}</span> : null}
            </p>
          ) : null}
          <Button
            className="mt-3"
            variant="secondary"
            loading={busy}
            disabled={disabled}
            onClick={async () => {
              setBusy(true);
              await onLink();
              setBusy(false);
            }}
          >
            {disabled ? 'Link statements first' : 'Link (simulated)'}
          </Button>
        </>
      ) : (
        <p className="mt-3 inline-flex items-center gap-1.5 text-[13px] font-medium text-active">
          <IconCheck size={15} /> Counted in your assessment
        </p>
      )}
    </div>
  );
}

/** Sliders call POST /simulate (debounced 300ms); the browser never computes a score. */
function WhatIf({ nodeId, version }: { nodeId: string; version: number }) {
  const [income, setIncome] = useState(8150);
  const [emis, setEmis] = useState(3500);
  const [principal, setPrincipal] = useState(5000);
  const [res, setRes] = useState<SimulateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    setLoading(true);
    clearTimeout(timer.current);
    let alive = true;
    timer.current = setTimeout(() => {
      void api
        .simulate({ nodeId, aa: true, monthlyIncome: String(income), obligations: String(emis), principal: String(principal) })
        .then((r) => {
          if (!alive) return;
          setRes(r);
          setLoading(false);
        });
    }, 300);
    return () => {
      alive = false;
      clearTimeout(timer.current);
    };
  }, [income, emis, principal, nodeId, version]);

  const dscr = res?.assessment.cashflow ? geom(res.assessment.cashflow.dscr) : null;
  return (
    <div className="rounded-[12px] border border-rule bg-surface p-5">
      <div className="flex items-center justify-between">
        <p className="flex items-center gap-2 font-medium">
          <IconSliders size={18} className="text-neel-700" /> What if
        </p>
        {loading ? <InkDots className="text-neel-500" /> : <span className="font-mono text-[11px] text-ink-3">POST /simulate</span>}
      </div>
      <div className="mt-4 grid gap-4">
        <Slider label="Monthly income" value={income} min={4000} max={30000} step={250} onChange={setIncome} />
        <Slider label="Existing EMIs" value={emis} min={0} max={12000} step={250} onChange={setEmis} />
        <Slider label="Loan asked" value={principal} min={1000} max={60000} step={500} onChange={setPrincipal} />
      </div>
      {res ? (
        <div className="mt-5 border-t border-rule pt-4">
          <div className="flex items-baseline justify-between text-[13px]">
            <span className="text-ink-3">Debt service cover (DSCR)</span>
            <span className={`num font-mono font-medium ${res.dscrHealthy ? 'text-active' : 'text-defaulted'}`}>{dscr?.toFixed(2)}×</span>
          </div>
          <DscrBar value={dscr ?? 0} />
          {!res.dscrHealthy ? (
            <p className="mt-2 flex items-start gap-1.5 text-[12.5px] text-defaulted">
              <IconAlert size={14} className="mt-0.5 shrink-0" /> Below 1.25×: well-liked or not, the instalment doesn’t fit the cash flow.
            </p>
          ) : null}
          <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
            <Mini k="μ" v={fmt(res.assessment.mu)} />
            <Mini k="σ²" v={fmt(res.assessment.sigma2)} />
            <Mini k="Limit" v={formatMoney(res.assessment.limit)} />
          </dl>
          {res.emi ? <p className="mt-2 text-center text-[12px] text-ink-3">EMI {formatMoney(res.emi, 2)} on {formatMoney(inr(String(principal)))}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

function Slider({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <label className="block">
      <span className="flex justify-between text-[12.5px]">
        <span className="text-ink-2">{label}</span>
        <span className="num font-medium">{formatMoney(inr(String(value)))}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="vt-range mt-1.5 w-full"
        style={{ '--fill': `${pct}%` } as React.CSSProperties}
      />
    </label>
  );
}

function DscrBar({ value }: { value: number }) {
  const max = 3;
  const w = Math.min(100, (value / max) * 100);
  return (
    <div className="relative mt-2 h-2 rounded-full bg-paper-2">
      <div className={`h-full rounded-full transition-[width] duration-300 ${value >= 1.25 ? 'bg-active' : 'bg-defaulted'}`} style={{ width: `${w}%` }} />
      <span className="absolute -top-1 h-4 w-px bg-ink" style={{ left: `${(1.25 / max) * 100}%` }} />
      <span className="absolute top-3 -translate-x-1/2 font-mono text-[10px] text-ink-3" style={{ left: `${(1.25 / max) * 100}%` }}>
        1.25
      </span>
    </div>
  );
}

function Mini({ k, v }: { k: string; v: string }) {
  return (
    <div className="mt-3 rounded-[8px] bg-paper px-2 py-2">
      <dt className="font-mono text-[11px] text-ink-3">{k}</dt>
      <dd className="num text-[14px] font-medium">{v}</dd>
    </div>
  );
}
