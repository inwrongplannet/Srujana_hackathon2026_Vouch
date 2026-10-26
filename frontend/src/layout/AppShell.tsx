import { useCallback, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router';
import { useSnapshot } from '@/state/DemoProvider';
import { Logo } from '@/components/brand/Logo';
import RubberSegment from '@/components/bits/RubberSegment';
import { IconBlock } from '@/components/icons';
import { ChainDrawer } from '@/features/chain/ChainDrawer';
import { ChainToasts } from '@/features/chain/ChainToasts';
import { DirectorBar } from '@/features/demo/DirectorBar';
import { IllustrativeNotice } from '@/components/ui/Notice';
import { dayDate } from '@/lib/format';
import { ProductNav } from './ProductNav';

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
        <div className="mx-auto flex h-14 max-w-[1320px] items-stretch justify-between gap-4 px-4 sm:px-8">
          <div className="flex min-w-0 items-stretch gap-5 sm:gap-8">
            <Link to="/" aria-label="Vouch home" className="flex items-center">
              <span className="sm:hidden">
                <Logo size={22} word="" />
              </span>
              <span className="hidden sm:inline">
                <Logo size={24} />
              </span>
            </Link>
            <ProductNav />
          </div>
          {desk ? null : (
            <div className="flex items-center">
              <button
                type="button"
                onClick={openLedger}
                aria-label={`Ledger, ${s.events.length} events`}
                className="group relative inline-flex h-9 items-center gap-2 rounded-[8px] border border-rule-2 bg-surface px-2.5 text-[13px] font-medium text-ink-2 transition-colors hover:border-ink-3 hover:text-ink sm:px-3"
              >
                <IconBlock size={16} />
                <span className="hidden sm:inline">Ledger</span>
                <span className="num rounded-full bg-paper-2 px-1.5 text-[11px] text-ink-3">{s.events.length}</span>
                {pending > 0 ? <span className="absolute -top-1 -right-1 size-2.5 rounded-full bg-neel-500 ring-2 ring-paper animate-pulse" /> : null}
              </button>
            </div>
          )}
        </div>

        {desk ? null : (
          <div className="border-t border-rule">
            <div className="mx-auto flex max-w-[1320px] items-center justify-between gap-4 px-4 py-2 sm:px-8">
              <div className="flex items-center gap-3">
                <span className="eyebrow hidden sm:inline">Viewing as</span>
                <RubberSegment
                  aria-label="Switch seat"
                  value={seat}
                  onChange={(v) => navigate(`/app/${v}`)}
                  items={[
                    {
                      value: 'borrower',
                      label: <SeatLabel role="Borrower" name={names.borrower} />,
                    },
                    {
                      value: 'voucher',
                      label: <SeatLabel role="Voucher" name={names.voucher} />,
                    },
                    {
                      value: 'lender',
                      label: <SeatLabel role="Lender" name={names.lender} />,
                    },
                  ]}
                  trackColor="#EBE6DB"
                  thumbColor="#FBFAF6"
                  textColor="#464955"
                  activeTextColor="#16181F"
                  size="sm"
                  radius={9}
                  className="shadow-[inset_0_0_0_1px_#DDD7CB]"
                />
              </div>
              <span className="hidden font-mono text-[11.5px] text-ink-3 md:block">
                {dayDate(s.day)} · block {s.block.toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        )}
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
      <span className="hidden text-[12px] opacity-60 sm:inline">{name}</span>
    </span>
  );
}
