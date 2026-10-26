import { useEffect, useState } from 'react';
import { backend, type AssessmentResult, type BackendUser, type BureauStatus, type CombinedAssessment, type PredictResponse, type ScenarioResult } from '@/api/backend';
import { checkBackend, useBackend } from '@/state/backendStatus';
import { Card, CardHead } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { SourceBadge } from '@/components/ui/SourceBadge';
import { TryAgain } from '@/layout/ProductNav';
import { Plan, Reasons, Signals, rupees } from '@/features/assess/parts';
import { WhatIf } from '@/features/assess/WhatIf';
import { ModelView } from '@/features/assess/Model';
import { Decide } from '@/features/assess/Decide';
import { RECORDED_INPUT, RECORDED_RUNS, RECORDED_USERS } from '@/mocks/deskRecorded';

const BUREAU: { value: BureauStatus; label: string }[] = [
  { value: 'NO_FILE', label: 'No file' },
  { value: 'AVAILABLE', label: 'Has a score' },
  { value: 'UNAVAILABLE', label: 'Bureau unavailable' },
  { value: 'NOT_AUTHORIZED', label: 'Not authorised' },
];
const TERMS = [6, 12, 18, 24, 36, 48];
const field = 'mt-1 h-10 w-full rounded-[7px] border border-rule-2 bg-surface px-2.5 text-[14px] text-ink';

type Source = 'live' | 'demo';

/**
 * Assessment desk. Live, every figure comes from the FastAPI backend; when the backend is down or
 * a call fails, the desk shows a recorded run of the same backend (`src/mocks/deskRecorded.ts`)
 * and says so, so the demo never stops on an error.
 */
export function AssessPage() {
  const b = useBackend();
  useEffect(() => {
    void checkBackend();
  }, []);
  // Only the first probe hides the desk; a later "Try again" keeps the current run on screen.
  const [settled, setSettled] = useState(b.status !== 'checking');
  if (!settled && b.status !== 'checking') setSettled(true);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Credit assessment</p>
          <h1 className="display mt-1 text-[34px] leading-tight">Assessment desk</h1>
          <p className="mt-1 max-w-[640px] text-[14px] text-ink-2">
            Bureau, Vouch Score, affordability and evidence, shown side by side, then the lender decides.
          </p>
        </div>
        {settled && b.status !== 'live' ? (
          <p className="flex flex-wrap items-center gap-3 text-[12.5px] text-ink-3">
            <SourceBadge live={false} />
            Backend not reachable, showing recorded runs.
            <TryAgain />
          </p>
        ) : null}
      </div>
      {settled ? <Desk live={b.status === 'live'} /> : <Card className="p-6 text-[14px] text-ink-3">Looking for the backend…</Card>}
    </div>
  );
}

type Run = {
  source: Source;
  applicationId: string;
  result: AssessmentResult;
  detail: CombinedAssessment | null;
  principal: number;
  term: number;
  /** Demo only: the recorded base what-if, since the sliders need the live backend. */
  scenario?: ScenarioResult;
};

const recorded = (borrower: string) => RECORDED_RUNS[borrower] ?? RECORDED_RUNS.LAKSHMI!;

function demoRun(borrower: string): Run {
  const r = recorded(borrower);
  return {
    source: 'demo',
    applicationId: r.applicationId,
    result: r.result,
    // The recorded detail is the backend's own response; see RecordedRun for why it is untyped.
    detail: r.detail as CombinedAssessment,
    principal: Number(RECORDED_INPUT.principal),
    term: RECORDED_INPUT.term,
    scenario: r.scenario,
  };
}

function Desk({ live }: { live: boolean }) {
  const [users, setUsers] = useState<BackendUser[] | null>(live ? null : RECORDED_USERS);
  const [borrower, setBorrower] = useState('LAKSHMI');
  // Opens on the story: Lakshmi asks for 1.5 lakh over 12 months (docs/DEMO.md).
  const [principal, setPrincipal] = useState('150000');
  const [term, setTerm] = useState(12);
  const [rate, setRate] = useState('24');
  const [bureau, setBureau] = useState<BureauStatus>('NO_FILE');
  const [bureauScore, setBureauScore] = useState('');
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [model, setModel] = useState<{ source: Source; m: PredictResponse } | null>(null);

  useEffect(() => {
    if (!live) return;
    let alive = true;
    backend
      .users()
      .then((list) => alive && setUsers(list.filter((u) => !u.is_anchor)))
      .catch(() => alive && setUsers(RECORDED_USERS));
    return () => {
      alive = false;
    };
  }, [live]);

  const scoreNeeded = bureau === 'AVAILABLE';
  const valid = borrower && /^\d+$/.test(principal) && Number(principal) > 0 && /^\d+(\.\d+)?$/.test(rate) && (!scoreNeeded || /^\d{3}$/.test(bureauScore));

  async function assess() {
    setBusy(true);
    if (!live) {
      setRun(demoRun(borrower));
      setModel({ source: 'demo', m: recorded(borrower).predict });
      setBusy(false);
      return;
    }
    // The rule-based assessment and the predictive model run side by side; either falls back alone.
    const prediction = backend
      .predict({
        borrower_id: borrower,
        requested_amount: `${principal}.00`,
        requested_tenure_months: term,
        annual_interest_rate: Number(rate) / 100,
        bureau_status: bureau,
        bureau_score: scoreNeeded ? Number(bureauScore) : null,
      })
      .then((m) => setModel({ source: 'live', m }))
      .catch(() => setModel({ source: 'demo', m: recorded(borrower).predict }));
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
      setRun({ source: 'live', applicationId: app.application_id, result, detail, principal: Number(principal), term });
    } catch {
      setRun(demoRun(borrower));
    } finally {
      await prediction;
      setBusy(false);
    }
  }

  if (!users) return <Card className="p-6 text-[14px] text-ink-3">Loading applicants…</Card>;

  const sameAsRecorded = principal === RECORDED_INPUT.principal && term === RECORDED_INPUT.term && rate === RECORDED_INPUT.rate && bureau === RECORDED_INPUT.bureau;

  return (
    <div className="space-y-5">
      <Card className="p-6">
        <CardHead eyebrow="Application" title="Who is asking, and for what" />
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
          <label className="text-[12.5px] text-ink-3 lg:col-span-2">
            Applicant
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
          {!live && !sameAsRecorded ? (
            <p className="text-[12.5px] text-ink-3">
              Demo data was recorded for {rupees(RECORDED_INPUT.principal)} over {RECORDED_INPUT.term} months at {RECORDED_INPUT.rate}% with no bureau file; other inputs need the live backend.
            </p>
          ) : null}
        </div>
      </Card>

      {run ? (
        <>
          <div className="flex flex-wrap items-center gap-3 text-[12.5px] text-ink-3">
            <SourceBadge live={run.source === 'live'} />
            {run.source === 'demo'
              ? `Recorded run: ${rupees(String(run.principal))} over ${run.term} months, the backend's own answer for this applicant.`
              : `Application ${run.applicationId}`}
          </div>
          <Signals r={run.result} detail={run.detail} />
          <div className="grid gap-5 lg:grid-cols-12">
            <div className="lg:col-span-5">
              <Plan r={run.result} />
            </div>
            <div className="lg:col-span-7">
              <Reasons r={run.result} />
            </div>
          </div>
          <WhatIf key={run.result.assessment_id} assessmentId={run.result.assessment_id} principal={run.principal} tenure={run.term} recorded={run.scenario} />
        </>
      ) : (
        <Card className="border-dashed p-6 text-[14px] text-ink-3">Run an assessment to see the four signals.</Card>
      )}
      {model ? <ModelView m={model.m} live={model.source === 'live'} /> : null}
      {run ? <Decide key={run.applicationId} applicationId={run.applicationId} live={run.source === 'live'} /> : null}
    </div>
  );
}
