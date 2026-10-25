import { useCallback, useEffect, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';
import { useSnapshot } from '@/state/DemoProvider';
import { Logo } from '@/components/brand/Logo';
import RubberSegment from '@/components/bits/RubberSegment';
import { IconBlock, IconGauge } from '@/components/icons';
import { ChainDrawer } from '@/features/chain/ChainDrawer';
import { ChainToasts } from '@/features/chain/ChainToasts';
import { DirectorBar } from '@/features/demo/DirectorBar';
import { IllustrativeNotice } from '@/components/ui/Notice';
import { dayDate } from '@/lib/format';
import { checkBackend, useBackend } from '@/state/backendStatus';

const SEATS = ['borrower', 'voucher', 'lender'] as const;

export function AppShell() {
  const s = useSnapshot();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [ledgerOpen, setLedgerOpen] = useState(false);
  const openLedger = useCallback(() => setLedgerOpen(true), []);
  const closeLedger = useCallback(() => setLedgerOpen(false), []);

  const seat = SEATS.find((x) => pathname.startsWith(`/app/${x}`)) ?? 'borrower';
  // The Assessment desk runs on the live backend, outside the mock story's seats and director.
  const desk = pathname.startsWith('/app/assess');
  const pending = s.events.filter((e) => e.status === 'pending').length;
  const names = {
    borrower: s.nodes[s.borrowerId]!.name.split(' ')[0],
    voucher: s.nodes[s.voucherId]!.name.split(' ')[0],
    lender: s.nodes[s.lenderId]!.name.split(' ')[0],
  };

  return (
    <div className="min-h-dvh pb-40">
      <header className="sticky top-0 z-20 border-b border-rule bg-paper/85 backdrop-blur-md">
        <div className="mx-auto grid h-16 max-w-[1320px] grid-cols-[1fr_auto_1fr] items-center gap-4 px-4 sm:px-8">
          <div className="flex items-center gap-4">
            <Link to="/" aria-label="VeriTrust home">
              <Logo size={24} />
            </Link>
            <span className="hidden h-5 w-px bg-rule-2 lg:block" />
            <span className="hidden font-mono text-[11.5px] text-ink-3 lg:block">
              {dayDate(s.day)} · block {s.block.toLocaleString('en-IN')}
            </span>
          </div>

          {desk ? (
            <p className="hidden text-center text-[13px] font-medium text-ink-2 md:block">Assessment desk · live backend</p>
          ) : (
          <RubberSegment
            aria-label="Switch seat"
            value={seat}
            onChange={(v) => navigate(`/app/${v}`)}
            items={[
              { value: 'borrower', label: <SeatLabel role="Borrower" name={names.borrower} /> },
              { value: 'voucher', label: <SeatLabel role="Voucher" name={names.voucher} /> },
              { value: 'lender', label: <SeatLabel role="Lender" name={names.lender} /> },
            ]}
            trackColor="#EBE6DB"
            thumbColor="#FBFAF6"
            textColor="#6A6D76"
            activeTextColor="#16181F"
            size="md"
            radius={10}
            className="shadow-[inset_0_0_0_1px_#DDD7CB]"
          />
          )}

          <div className="flex items-center justify-end gap-2">
            <Link
              to="/app/assess"
              aria-label="Assessment desk"
              className="relative inline-flex h-9 items-center gap-2 rounded-[8px] border border-rule-2 bg-surface px-2.5 text-[13px] font-medium text-ink-2 transition-colors hover:border-ink-3 hover:text-ink sm:px-3"
            >
              <IconGauge size={16} />
              <span className="hidden sm:inline">Assess</span>
              <BackendDot />
            </Link>
            <Link
              to="/community"
              className="inline-flex h-9 items-center rounded-[8px] border border-rule-2 bg-surface px-3 text-[13px] font-medium text-ink-2 transition-colors hover:border-ink-3 hover:text-ink"
            >
              Community
            </Link>
            <button
              type="button"
              onClick={openLedger}
              className="group relative inline-flex h-9 items-center gap-2 rounded-[8px] border border-rule-2 bg-surface px-3 text-[13px] font-medium text-ink-2 transition-colors hover:border-ink-3 hover:text-ink"
            >
              <IconBlock size={16} />
              <span className="hidden sm:inline">Ledger</span>
              <span className="num rounded-full bg-paper-2 px-1.5 text-[11px] text-ink-3">{s.events.length}</span>
              {pending > 0 ? <span className="absolute -top-1 -right-1 size-2.5 rounded-full bg-neel-500 ring-2 ring-paper animate-pulse" /> : null}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1320px] px-4 pt-8 sm:px-8">
        <Outlet />
        <IllustrativeNotice className="mt-12" />
      </main>

      <ChainToasts onOpenLedger={openLedger} />
      <ChainDrawer open={ledgerOpen} onClose={closeLedger} />
      {desk ? null : <DirectorBar />}
    </div>
  );
}

function SeatLabel({ role, name }: { role: string; name: string }) {
  return (
    <span className="flex items-baseline gap-1.5 whitespace-nowrap">
      <span className="font-medium">{role}</span>
      <span className="hidden text-[12px] opacity-60 md:inline">{name}</span>
    </span>
  );
}

/** Green when the FastAPI backend answers /health, grey when the desk would be offline. */
function BackendDot() {
  const b = useBackend();
  useEffect(() => {
    void checkBackend();
  }, []);
  const label = b.status === 'live' ? 'Backend live' : b.status === 'offline' ? 'Backend offline' : 'Checking backend';
  const tone = b.status === 'live' ? 'bg-active' : b.status === 'offline' ? 'bg-cold' : 'bg-ink-3 animate-pulse';
  return <span role="img" aria-label={label} title={label} className={`absolute -top-1 -right-1 size-2.5 rounded-full ring-2 ring-paper ${tone}`} />;
}
