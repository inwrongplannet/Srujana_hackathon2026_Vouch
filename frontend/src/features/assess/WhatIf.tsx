import { useEffect, useState } from 'react';
import { backend, type ScenarioResult } from '@/api/backend';
import { ApiError } from '@/api/http';
import { Card, CardHead } from '@/components/ui/Card';
import { Badge } from '@/components/ui/StatusBadge';
import { rupees } from './parts';

const TENURES = [6, 12, 18, 24, 36, 48];

/**
 * Whole-rupee slider; the value goes to the backend as a decimal string. `null` means "not
 * overridden": the field is left out and the backend uses its own value (`unset` says which).
 */
function Slider({ id, label, value, min, max, step, unset, onChange }: { id: string; label: string; value: number | null; min: number; max: number; step: number; unset?: string; onChange: (v: number) => void }) {
  const at = value ?? min;
  return (
    <div>
      <label htmlFor={id} className="flex justify-between text-[12.5px] text-ink-3">
        {label}
        <span className="num font-mono text-ink">{value === null ? unset : rupees(String(value))}</span>
      </label>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={at}
        onChange={(e) => onChange(Number(e.target.value))}
        className="vt-range mt-1 w-full"
        style={{ ['--fill' as string]: `${value === null ? 0 : ((at - min) / (max - min)) * 100}%` }}
      />
    </div>
  );
}

/**
 * Counterfactuals from `POST /assessments/{id}/scenarios`, re-fetched 300 ms after the last
 * change (frontend/AGENTS.md): the maths stays on the backend.
 */
export function WhatIf({ assessmentId, principal, tenure }: { assessmentId: string; principal: number; tenure: number }) {
  const [income, setIncome] = useState<number | null>(null);
  const [expenses, setExpenses] = useState<number | null>(null);
  const [amount, setAmount] = useState(principal);
  const [months, setMonths] = useState(tenure);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    setBusy(true);
    const timer = setTimeout(() => {
      backend
        .scenario(assessmentId, {
          simulated_income: income === null ? undefined : String(income),
          simulated_expenses: expenses === null ? undefined : String(expenses),
          simulated_principal: String(amount),
          simulated_tenure: months,
        })
        .then((r) => {
          if (!alive) return;
          setResult(r);
          setError(null);
        })
        .catch((e: unknown) => alive && setError(e instanceof ApiError ? e.message : 'Scenario failed'))
        .finally(() => alive && setBusy(false));
    }, 300);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [assessmentId, income, expenses, amount, months]);

  return (
    <Card className="p-6">
      <CardHead eyebrow="What if" title="Move the numbers, the backend re-checks" aside={busy ? <span className="text-[12px] text-ink-3">checking…</span> : null} />
      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <div className="space-y-4">
          <Slider id="wi-income" label="Monthly income" value={income} min={5000} max={100000} step={500} unset="as on file" onChange={setIncome} />
          <Slider id="wi-expenses" label="Essential expenses a month" value={expenses} min={0} max={80000} step={500} unset="backend default" onChange={setExpenses} />
          <Slider id="wi-amount" label="Loan amount" value={amount} min={5000} max={500000} step={5000} onChange={setAmount} />
          <div>
            <p className="text-[12.5px] text-ink-3">Months</p>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {TENURES.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setMonths(t)}
                  className={`num h-9 rounded-[8px] border px-3.5 text-[14px] font-medium transition-colors ${
                    months === t ? 'border-neel-700 bg-neel-700 text-surface' : 'border-rule-2 bg-surface hover:border-ink-3'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-[10px] bg-paper p-4 text-[13.5px]">
          {error ? (
            <p className="text-defaulted">{error}</p>
          ) : result ? (
            <>
              <Badge tone={result.is_feasible ? 'active' : 'restricted'}>{result.is_feasible ? 'Fits' : 'Does not fit'}</Badge>
              <dl className="mt-3 grid grid-cols-2 gap-y-1.5">
                <dt className="text-ink-3">Monthly EMI</dt>
                <dd className="num text-right">{rupees(result.monthly_emi, 2)}</dd>
                <dt className="text-ink-3">Left each month</dt>
                <dd className="num text-right">{rupees(result.residual_cash, 2)}</dd>
                <dt className="text-ink-3">Income still needed</dt>
                <dd className="num text-right">{rupees(result.income_shock_margin, 2)}</dd>
                <dt className="text-ink-3">Binding rule</dt>
                <dd className="text-right">{result.binding_constraint.toLowerCase().replaceAll('_', ' ')}</dd>
              </dl>
              <p className="mt-3 text-ink-2">{result.summary}</p>
              <p className="mt-3 text-[12px] text-ink-3">
                The backend's scenario check does not take the application's interest rate yet, and assumes ₹12,000 of expenses unless you move that slider, so it can disagree with the assessment above.
              </p>
            </>
          ) : (
            <p className="text-ink-3">Checking…</p>
          )}
        </div>
      </div>
    </Card>
  );
}
