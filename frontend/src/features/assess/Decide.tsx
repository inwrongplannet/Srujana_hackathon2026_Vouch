/**
 * The lender's decision on the assessed application (POST /api/v1/applications/{id}/decision).
 * The signals inform it; a person makes it. Live, an approval creates a real loan that appears in
 * the lender console's live book; on demo data, or if the backend does not answer, the decision is
 * shown but not saved.
 */
import { useState } from 'react';
import { Link } from 'react-router';
import { backend, type Decision, type DecisionResult } from '@/api/backend';
import { isRefusal } from '@/api/http';
import { Button } from '@/components/ui/Button';
import { Card, CardHead } from '@/components/ui/Card';
import { Badge } from '@/components/ui/StatusBadge';
import { IconArrowRight } from '@/components/icons';
import { rupees } from './parts';

const CHOICES: { decision: Decision; label: string; variant: 'primary' | 'secondary' | 'danger' }[] = [
  { decision: 'APPROVE', label: 'Approve as asked', variant: 'primary' },
  { decision: 'APPROVE_AT_LIMIT', label: 'Approve up to the limit', variant: 'secondary' },
  { decision: 'DECLINE', label: 'Decline', variant: 'danger' },
];

const DEMO_STATUS: Record<Decision, string> = { APPROVE: 'APPROVED', APPROVE_AT_LIMIT: 'APPROVED', DECLINE: 'REJECTED' };

export function Decide({ applicationId, live }: { applicationId: string; live: boolean }) {
  const [busy, setBusy] = useState<Decision | null>(null);
  const [done, setDone] = useState<DecisionResult | null>(null);
  const [saved, setSaved] = useState(true);
  const [refused, setRefused] = useState<string | null>(null);

  async function decide(d: Decision) {
    setBusy(d);
    setRefused(null);
    try {
      if (!live) throw new Error('demo data');
      setDone(await backend.decide(applicationId, d));
      setSaved(true);
    } catch (e) {
      // The backend said no (over the limit, already decided): show why. Demo data or no answer:
      // show the decision without a loan, and say it was not saved.
      if (isRefusal(e)) {
        setRefused(e.message);
      } else {
        setDone({ application_id: applicationId, status: DEMO_STATUS[d], loan: null });
        setSaved(false);
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="p-6">
      <CardHead eyebrow="Your decision" title="Signals, not a verdict. You decide." />
      {done ? (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
          <p className="flex flex-wrap items-center gap-2 text-[14px]">
            <Badge tone={done.loan ? 'active' : 'plain'}>{done.status.toLowerCase()}</Badge>
            {!saved ? (
              <span className="text-ink-2">Shown on demo data; nothing was saved to the backend.</span>
            ) : done.loan ? (
              <span className="text-ink-2">
                Loan <span className="font-mono text-ink">{done.loan.loan_id}</span> for {rupees(done.loan.principal)} over {done.loan.tenure_months} months is
                now on the book.
              </span>
            ) : (
              <span className="text-ink-2">No loan was made.</span>
            )}
          </p>
          {done.loan ? (
            <Link to="/app/lender" className="inline-flex items-center gap-1.5 text-[13.5px] font-medium text-neel-700 hover:underline">
              Open the live book <IconArrowRight size={15} />
            </Link>
          ) : null}
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {CHOICES.map((c) => (
            <Button key={c.decision} variant={c.variant} loading={busy === c.decision} disabled={busy !== null} onClick={() => void decide(c.decision)}>
              {c.label}
            </Button>
          ))}
          {refused ? <p className="text-[13px] text-ink-2">Backend: {refused}</p> : null}
        </div>
      )}
    </Card>
  );
}
