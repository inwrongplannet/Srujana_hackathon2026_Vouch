import { useEffect, useState } from 'react';
import { backend, type AssessmentResult, type BackendUser, type BureauStatus, type CombinedAssessment } from '@/api/backend';
import { ApiError } from '@/api/http';
import { checkBackend, useBackend } from '@/state/backendStatus';
import { Card, CardHead } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/StatusBadge';
import { IconAlert, IconReset } from '@/components/icons';
import { Plan, Reasons, Signals } from '@/features/assess/parts';
import { WhatIf } from '@/features/assess/WhatIf';

const BUREAU: { value: BureauStatus; label: string }[] = [
  { value: 'NO_FILE', label: 'No file' },
  { value: 'AVAILABLE', label: 'Has a score' },
  { value: 'UNAVAILABLE', label: 'Bureau unavailable' },
  { value: 'NOT_AUTHORIZED', label: 'Not authorised' },
];
const TERMS = [6, 12, 18, 24, 36, 48];
const field = 'mt-1 h-10 w-full rounded-[7px] border border-rule-2 bg-surface px-2.5 text-[14px] text-ink';

/** Assessment desk: the one screen that runs on the real FastAPI backend (option C wiring). */
export function AssessPage() {
  const b = useBackend();
  useEffect(() => {
    void checkBackend();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Live backend</p>
          <h1 className="display mt-1 text-[34px] leading-tight">Assessment desk</h1>
          <p className="mt-1 max-w-[640px] text-[14px] text-ink-2">
            Runs the real assessment on the backend: bureau, Vouch Score, affordability and evidence, shown side by side.
          </p>
        </div>
      </div>
      {b.status === 'checking' ? (
        <Card className="p-6 text-[14px] text-ink-3">Looking for the backend…</Card>
      ) : b.status === 'offline' ? (
        <Offline message={b.message} />
      ) : (
        <Desk />
      )}
    </div>
  );
}

function Offline({ message }: { message: string }) {
  return (
    <Card className="p-6">
      <CardHead eyebrow="Backend offline" title="Start the API to use this desk" aside={<Badge tone="restricted">offline</Badge>} />
      <p className="mt-3 text-[14px] text-ink-2">{message}</p>
      <pre className="mt-4 overflow-x-auto rounded-[8px] bg-ink p-4 font-mono text-[12.5px] text-paper">cd backend{'\n'}python main.py serve --port 8000</pre>
      <p className="mt-3 text-[13px] text-ink-3">The rest of the demo keeps working on the built-in mock while the backend is down.</p>
      <Button className="mt-5" variant="secondary" icon={<IconReset size={15} />} onClick={() => void checkBackend()}>
        Try again
      </Button>
    </Card>
  );
}

type Run = { result: AssessmentResult; detail: CombinedAssessment | null; principal: number; term: number };

function Desk() {
  const [users, setUsers] = useState<BackendUser[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [borrower, setBorrower] = useState('');
  const [principal, setPrincipal] = useState('50000');
  const [term, setTerm] = useState(12);
  const [rate, setRate] = useState('24');
  const [bureau, setBureau] = useState<BureauStatus>('NO_FILE');
  const [bureauScore, setBureauScore] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null);

  useEffect(() => {
    let alive = true;
    backend
      .users()
      .then((list) => {
        if (!alive) return;
        const people = list.filter((u) => !u.is_anchor);
        setUsers(people);
        setBorrower((current) => current || people[0]?.user_id || '');
      })
      .catch((e: unknown) => alive && setLoadError(e instanceof ApiError ? e.message : 'Could not load applicants'));
    return () => {
      alive = false;
    };
  }, []);

  const scoreNeeded = bureau === 'AVAILABLE';
  const valid = borrower && /^\d+$/.test(principal) && Number(principal) > 0 && /^\d+(\.\d+)?$/.test(rate) && (!scoreNeeded || /^\d{3}$/.test(bureauScore));

  async function assess() {
    setBusy(true);
    setError(null);
    try {
      const app = await backend.createApplication({
        borrower_id: borrower,
        principal,
        // A rate, not money: the backend takes an annual fraction (24% -> 0.24).
        annual_rate: Number(rate) / 100,
        term_months: term,
        purpose_category: 'WORKING_CAPITAL',
      });
      const result = await backend.runAssessment(app.application_id, {
        objective: 'MIN_COST',
        enable_stress_test: true,
        simulation_scenarios: 2000,
        bureau_status: bureau,
        bureau_score: scoreNeeded ? Number(bureauScore) : null,
      });
      const detail = await backend.assessment(result.assessment_id).catch(() => null);
      setRun({ result, detail, principal: Number(principal), term });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'The assessment failed');
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <Card className="p-6 text-[14px] text-defaulted">
        <IconAlert size={16} className="mr-1.5 inline" />
        {loadError}
      </Card>
    );
  }
  if (!users) return <Card className="p-6 text-[14px] text-ink-3">Loading applicants…</Card>;
  if (!users.length) return <Card className="p-6 text-[14px] text-ink-2">The backend has no applicants yet. Seed it, then reload.</Card>;

  return (
    <div className="space-y-5">
      <Card className="p-6">
        <CardHead eyebrow="Application" title="Who is asking, and for what" />
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
          <label className="text-[12.5px] text-ink-3 lg:col-span-2">
            Applicant (from the backend)
            <select value={borrower} onChange={(e) => setBorrower(e.target.value)} className={field}>
              {users.map((u) => (
                <option key={u.user_id} value={u.user_id}>
                  {u.name} · {u.user_id}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[12.5px] text-ink-3">
            Amount (₹)
            <input inputMode="numeric" value={principal} onChange={(e) => setPrincipal(e.target.value.replace(/\D/g, ''))} className={`${field} num`} />
          </label>
          <label className="text-[12.5px] text-ink-3">
            Months
            <select value={term} onChange={(e) => setTerm(Number(e.target.value))} className={field}>
              {TERMS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[12.5px] text-ink-3">
            Rate (% a year)
            <input inputMode="decimal" value={rate} onChange={(e) => setRate(e.target.value.replace(/[^\d.]/g, ''))} className={`${field} num`} />
          </label>
          <label className="text-[12.5px] text-ink-3">
            Bureau
            <select value={bureau} onChange={(e) => setBureau(e.target.value as BureauStatus)} className={field}>
              {BUREAU.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          {scoreNeeded ? (
            <label className="text-[12.5px] text-ink-3">
              Bureau score (300-900)
              <input inputMode="numeric" value={bureauScore} onChange={(e) => setBureauScore(e.target.value.replace(/\D/g, '').slice(0, 3))} className={`${field} num`} />
            </label>
          ) : null}
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <Button size="lg" loading={busy} disabled={!valid} onClick={() => void assess()}>
            Run assessment
          </Button>
          {error ? (
            <p className="flex items-center gap-1.5 text-[13px] text-defaulted">
              <IconAlert size={15} /> {error}
            </p>
          ) : null}
        </div>
      </Card>

      {run ? (
        <>
          <Signals r={run.result} detail={run.detail} />
          <div className="grid gap-5 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <Plan r={run.result} />
            </div>
            <div className="lg:col-span-7">
              <Reasons r={run.result} />
            </div>
          </div>
          <WhatIf key={run.result.assessment_id} assessmentId={run.result.assessment_id} principal={run.principal} tenure={run.term} />
        </>
      ) : (
        <Card className="border-dashed p-6 text-[14px] text-ink-3">Run an assessment to see the four signals.</Card>
      )}
    </div>
  );
}
