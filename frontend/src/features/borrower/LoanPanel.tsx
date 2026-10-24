import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { Money, Snapshot } from '@/api/types';
import { Card, CardHead } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/StatusBadge';
import Counter from '@/components/bits/Counter';
import { IconRupee, IconSeal, IconAlert, IconClockForward } from '@/components/icons';
import { dayDate, formatMoney, geom, inr } from '@/lib/format';

const PURPOSE = 'Industrial sewing-machine motor';

/** The credit line: current limit, apply, then the loan's life on LoanEscrow. */
export function LoanPanel({ s }: { s: Snapshot }) {
  const me = s.borrowerId;
  const a = s.assessments[me]!;
  const node = s.nodes[me]!;
  const loan = [...s.loans].reverse().find((l) => l.borrower === me && l.status !== 'DECLINED');
  const limit = geom(a.limit.amount);
  const choices = ['2000', '5000', a.limit.amount].filter((v, i, arr) => geom(v) > 0 && geom(v) <= limit && arr.indexOf(v) === i);
  const [amount, setAmount] = useState('5000');
  const [emi, setEmi] = useState<Money | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    void api.simulate({ nodeId: me, principal: amount }).then((r) => alive && setEmi(r.emi));
    return () => {
      alive = false;
    };
  }, [amount, me]);

  return (
    <Card className="flex flex-col p-6">
      <CardHead eyebrow="Credit line" title="Available to borrow" aside={<IconRupee size={20} className="text-ink-3" />} />
      <div className="mt-3">
        <Counter
          value={limit}
          locale="en-IN"
          format={{ style: 'currency', currency: 'INR', maximumFractionDigits: 0 }}
          fontSize={44}
          fontWeight={600}
          textColor={limit > 0 ? '#16181F' : '#6A6D76'}
          tabular
          className="display"
          style={{ fontFamily: 'var(--font-display)', fontVariationSettings: "'wdth' 88" }}
        />
        <p className="mt-1 text-[12.5px] text-ink-3">Score × ₹10,000, rounded down to ₹500 · illustrative pricing 24% a.p.r.</p>
      </div>

      <div className="mt-5 flex-1 border-t border-rule pt-5">
        {node.status === 'DEFAULTED' ? (
          <Status tone="defaulted" icon={<IconAlert size={18} />} title="Borrowing blocked" text="This identity defaulted. The record follows the nullifier, not the wallet." />
        ) : !loan ? (
          limit > 0 ? (
            <div>
              <p className="text-[13px] font-medium">Amount</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {choices.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setAmount(c)}
                    className={`num h-9 rounded-[8px] border px-3.5 text-[14px] font-medium transition-colors ${
                      amount === c ? 'border-neel-700 bg-neel-700 text-surface' : 'border-rule-2 bg-surface hover:border-ink-3'
                    }`}
                  >
                    {formatMoney(inr(c))}
                  </button>
                ))}
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-y-1 text-[13px]">
                <dt className="text-ink-3">For</dt>
                <dd className="text-right">{PURPOSE}</dd>
                <dt className="text-ink-3">6 instalments of</dt>
                <dd className="num text-right font-medium">{emi ? formatMoney(emi, 2) : '…'}</dd>
              </dl>
              <Button
                className="mt-5 w-full"
                size="lg"
                loading={busy}
                onClick={async () => {
                  setBusy(true);
                  await api.applyLoan(me, amount, PURPOSE);
                  setBusy(false);
                }}
              >
                Apply for {formatMoney(inr(amount))}
              </Button>
            </div>
          ) : (
            <p className="text-[14px] text-ink-2">
              Your limit is ₹0 because nobody has vouched for you yet, not because of anything you did. One vouch changes that.
            </p>
          )
        ) : loan.status === 'APPLIED' ? (
          <Status tone="neel" title={`Applied for ${formatMoney(loan.principal)}`} text={`Sahyog Microfinance is reviewing ${loan.id}. They see your score path by path, not just a number.`} />
        ) : loan.status === 'DISBURSED' ? (
          <Status
            tone="neel"
            icon={<IconClockForward size={18} />}
            title={`${formatMoney(loan.principal)} received`}
            text={`${loan.id} · due ${dayDate(loan.dueDay!)} · ${formatMoney(loan.emi, 2)} a month. Meena’s vouch is locked behind it until it closes.`}
          />
        ) : loan.status === 'SETTLED' ? (
          <Status tone="active" icon={<IconSeal size={18} />} title="Repaid in full" text={`${loan.id} closed ${dayDate(loan.closedDay!)}. Credibility minted; you can now vouch for others.`} />
        ) : (
          <Status tone="defaulted" icon={<IconAlert size={18} />} title="Loan defaulted" text={`${loan.id} closed unpaid. Penalties reached your sponsors, damped, and stopped at two hops.`} />
        )}
      </div>
    </Card>
  );
}

function Status({ tone, title, text, icon }: { tone: 'neel' | 'active' | 'defaulted'; title: string; text: string; icon?: React.ReactNode }) {
  return (
    <div>
      <Badge tone={tone}>{tone === 'neel' ? 'In progress' : tone === 'active' ? 'Settled' : 'Defaulted'}</Badge>
      <p className="mt-3 flex items-center gap-2 text-[17px] font-medium">
        {icon}
        {title}
      </p>
      <p className="mt-1 text-[13.5px] text-ink-2">{text}</p>
    </div>
  );
}
