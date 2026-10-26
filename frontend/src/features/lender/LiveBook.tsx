/**
 * The lender's live book from the backend: every loan with repay and default actions, the
 * platform treasury (1% fee on disbursements and repayments) and the latest transactions. A default
 * shows the damped cascade the backend applied. Hidden when the backend is offline or cannot be
 * read, so the guided story's demo book below carries the screen; a failed refresh keeps the last
 * answer, and a refused action shows the backend's reason.
 */
import { useCallback, useEffect, useState } from 'react';
import { backend, type DefaultResult, type LoanSummary, type PlatformTreasury, type TransactionSummary } from '@/api/backend';
import { isRefusal } from '@/api/http';
import { Button } from '@/components/ui/Button';
import { Card, CardHead } from '@/components/ui/Card';
import { SourceBadge } from '@/components/ui/SourceBadge';
import { Explain } from '@/features/explain/Explain';
import { Badge, type Tone } from '@/components/ui/StatusBadge';
import { formatMoney, inr, pct } from '@/lib/format';
import { useBackend } from '@/state/backendStatus';
import { TryAgain } from '@/layout/ProductNav';

const TONE: Record<string, Tone> = { ACTIVE: 'neel', SETTLED: 'active', REPAID: 'active', DEFAULTED: 'defaulted' };
const money = (v: string) => formatMoney(inr(v));
const AMOUNT = /^\d+(\.\d{1,2})?$/;

type Book = { loans: LoanSummary[]; treasury: PlatformTreasury; txs: TransactionSummary[] };

function LoanRow({ loan, onDone }: { loan: LoanSummary; onDone: (cascade?: DefaultResult) => void }) {
  const [amount, setAmount] = useState('');
  const [arming, setArming] = useState(false);
  const [busy, setBusy] = useState<'repay' | 'default' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const active = loan.status === 'ACTIVE';

  async function act(kind: 'repay' | 'default') {
    setBusy(kind);
    setError(null);
    try {
      if (kind === 'repay') {
        await backend.repay(loan.loan_id, amount);
        setAmount('');
        onDone();
      } else {
        onDone(await backend.defaultLoan(loan.loan_id));
      }
    } catch (e) {
      setError(isRefusal(e) ? `Backend: ${e.message}` : 'The backend did not answer; nothing changed.');
    } finally {
      setBusy(null);
      setArming(false);
    }
  }

  return (
    <tr className="border-b border-rule align-top last:border-0">
      <td className="py-3 pr-4">
        <p className="font-mono text-[12.5px]">{loan.loan_id}</p>
        <p className="text-[13px] font-medium">{loan.borrower_id}</p>
      </td>
      <td className="num py-3 pr-4 text-right font-mono">{money(loan.principal)}</td>
      <td className="num py-3 pr-4 text-right font-mono">{money(loan.outstanding_balance)}</td>
      <td className="num py-3 pr-4 text-right font-mono text-ink-2">
        {pct(loan.interest_rate, 1)} · {loan.tenure_months}m
      </td>
      <td className="py-3 pr-4">
        <Badge tone={TONE[loan.status] ?? 'plain'}>{loan.status.toLowerCase()}</Badge>
      </td>
      <td className="py-3">
        {active ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            <input
              aria-label={`Repayment for ${loan.loan_id}, rupees`}
              inputMode="decimal"
              placeholder="₹ amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value.replace(/[^\d.]/g, ''))}
              className="num h-8 w-28 rounded-[6px] border border-rule-2 bg-surface px-2 font-mono text-[13px]"
            />
            <Button size="sm" variant="secondary" loading={busy === 'repay'} disabled={!AMOUNT.test(amount) || busy !== null} onClick={() => void act('repay')}>
              Repay
            </Button>
            <Button size="sm" variant="danger" loading={busy === 'default'} disabled={busy !== null} onClick={() => (arming ? void act('default') : setArming(true))}>
              {arming ? 'Confirm default' : 'Default'}
            </Button>
          </div>
        ) : null}
        {error ? <p className="mt-1 text-right text-[12px] text-ink-3">{error}</p> : null}
      </td>
    </tr>
  );
}

export function LiveBook() {
  const status = useBackend().status;
  const live = status === 'live';
  const [book, setBook] = useState<Book | null>(null);
  const [unreadable, setUnreadable] = useState(false);
  const [cascade, setCascade] = useState<DefaultResult | null>(null);

  const load = useCallback(async () => {
    try {
      const [loans, treasury, txs] = await Promise.all([backend.loans(), backend.treasury(), backend.transactions()]);
      setBook({ loans, treasury, txs });
      setUnreadable(false);
    } catch {
      // Keep the last good book; with none yet, the live book stays hidden.
      setUnreadable(true);
    }
  }, []);

  useEffect(() => {
    if (live) void load();
  }, [live, load]);

  if (status === 'checking' && !book) return null;
  if (!live || (unreadable && !book)) {
    return (
      <p className="flex flex-wrap items-center gap-3 rounded-[10px] border border-rule bg-surface px-4 py-2.5 text-[12.5px] text-ink-3">
        <SourceBadge live={false} />
        Live book hidden: the backend is not answering. The book below is the story&rsquo;s demo data.
        <TryAgain />
      </p>
    );
  }

  return (
    <Card className="p-6">
      <CardHead
        eyebrow="Live book"
        title="Loans on the backend"
        aside={
          <span className="flex items-center gap-3">
            <SourceBadge live />
            <Button size="sm" variant="ghost" onClick={() => void load()}>
              Refresh
            </Button>
          </span>
        }
      />
      {unreadable ? <p className="mt-3 text-[12.5px] text-ink-3">The backend did not answer the last refresh; showing the last book.</p> : null}
      {!book ? (
        <p className="mt-4 text-[13.5px] text-ink-3">Loading the book…</p>
      ) : (
        <>
          <dl className="mt-4 grid grid-cols-3 gap-px overflow-hidden rounded-[10px] border border-rule bg-rule">
            {[
              ['Platform fees collected', money(book.treasury.total_fees_collected)],
              ['Fee on each payment', pct(book.treasury.fee_rate, 0)],
              ['Fee-bearing payments', String(book.treasury.transaction_count)],
            ].map(([k, v]) => (
              <div key={k} className="bg-surface px-4 py-2.5">
                <dt className="text-[11.5px] text-ink-3">{k === 'Fee on each payment' ? <Explain id="fee">{k}</Explain> : k}</dt>
                <dd className="num text-[17px] font-medium">{v}</dd>
              </div>
            ))}
          </dl>

          {book.loans.length === 0 ? (
            <p className="mt-5 rounded-[10px] border border-dashed border-rule-2 p-4 text-[13.5px] text-ink-3">
              No loans yet. Approve an application on the Assessment desk and it appears here.
            </p>
          ) : (
            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-[13.5px]">
                <thead>
                  <tr className="border-b border-ink font-mono text-[11px] tracking-[0.06em] text-ink-3">
                    <th className="py-2 font-normal">LOAN</th>
                    <th className="py-2 pr-4 text-right font-normal">PRINCIPAL</th>
                    <th className="py-2 pr-4 text-right font-normal">OUTSTANDING</th>
                    <th className="py-2 pr-4 text-right font-normal">RATE · TERM</th>
                    <th className="py-2 font-normal">STATUS</th>
                    <th className="py-2 text-right font-normal">ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {book.loans.map((l) => (
                    <LoanRow
                      key={l.loan_id}
                      loan={l}
                      onDone={(c) => {
                        if (c) setCascade(c);
                        void load();
                      }}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {cascade ? (
            <div className="mt-5 rounded-[10px] border border-defaulted/30 bg-defaulted-tint/50 p-4">
              <p className="text-[13.5px] font-medium text-defaulted">
                {cascade.loan_id} defaulted · base penalty {cascade.delta0}. The cascade stops at two hops:
              </p>
              <ul className="mt-2 space-y-1 font-mono text-[12.5px]">
                {cascade.penalties.map((p) => (
                  <li key={`${p.user_id}-${p.level}`} className="flex flex-wrap gap-x-3">
                    <span className="w-16 text-ink-3">hop {p.level}</span>
                    <span className="w-24 font-medium">{p.user_id}</span>
                    <span>
                      {p.reputation_before} → {p.reputation_after}
                    </span>
                    <span className="text-ink-3">{p.status_after.toLowerCase()}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {book.txs.length ? (
            <div className="mt-5">
              <p className="eyebrow">Latest transactions</p>
              <ul className="mt-2 divide-y divide-rule">
                {book.txs.slice(-6).reverse().map((t) => (
                  <li key={t.tx_id} className="flex flex-wrap items-baseline justify-between gap-3 py-2 text-[13px]">
                    <span>
                      <span className="font-mono text-[12px] text-ink-3">{t.tx_type.toLowerCase()}</span> · {t.user_id}
                    </span>
                    <span className="num font-mono">
                      {money(t.amount)} <span className="text-ink-3">fee {money(t.fee)}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}
    </Card>
  );
}
