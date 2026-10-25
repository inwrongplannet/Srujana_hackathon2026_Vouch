/**
 * Shell for the community platform. The viewer is Meena (vouching) everywhere except "My ask",
 * which shows Lakshmi's side as the borrower.
 */
import { Link, NavLink, Outlet, useLocation } from 'react-router';
import { Logo } from '@/components/brand/Logo';
import { IllustrativeNotice } from '@/components/ui/Notice';
import { fmt } from '@/lib/format';
import { MEMBERS, VIEWER_ID } from '@/mocks/community';
import { useCommunity } from '@/state/communityStore';
import { PersonMark, recordLabel } from '@/features/community/parts';
import { ProductNav } from './ProductNav';

const tab = ({ isActive }: { isActive: boolean }) =>
  `relative px-1 py-3 text-[13.5px] transition-colors ${isActive ? 'text-ink after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:bg-ink' : 'text-ink-3 hover:text-ink-2'}`;

export function CommunityShell() {
  const { members } = useCommunity();
  const { pathname } = useLocation();
  const borrowerSide = pathname.startsWith('/community/me');
  const me = members[VIEWER_ID]!;
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-20 border-b border-rule bg-paper/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-[1240px] items-stretch justify-between gap-4 px-4 sm:px-8">
          <div className="flex min-w-0 items-stretch gap-5 sm:gap-8">
            <Link to="/" aria-label="Vouch home" className="flex items-center">
              <span className="sm:hidden">
                <Logo size={22} word="" />
              </span>
              <span className="hidden sm:inline">
                <Logo size={24} word="Vouch" />
              </span>
            </Link>
            <ProductNav />
          </div>
          <div className="hidden items-center gap-2.5 md:flex">
            {borrowerSide ? (
              <>
                <div className="text-right">
                  <p className="text-[13px] leading-tight font-medium">Lakshmi Naik</p>
                  <p className="text-[11.5px] text-ink-3">asking · borrower view</p>
                </div>
                <PersonMark name="Lakshmi Naik" size={30} />
              </>
            ) : (
              <>
                <div className="text-right">
                  <p className="text-[13px] leading-tight font-medium">{MEMBERS[VIEWER_ID]!.name}</p>
                  <p className="text-[11.5px] text-ink-3">
                    {fmt(me.budget.minus(me.committed).toString(), 0)} points free · {recordLabel(me)}
                  </p>
                </div>
                <PersonMark name={me.name} size={30} />
              </>
            )}
          </div>
        </div>
        <div className="border-t border-rule">
          <div className="mx-auto flex max-w-[1240px] items-center justify-between gap-6 px-4 sm:px-8">
            <nav aria-label="Community" className="flex gap-6">
              <NavLink to="/community" className={() => tab({ isActive: !borrowerSide })}>
                Discover
              </NavLink>
              <NavLink to="/community/me" className={tab}>
                My ask
              </NavLink>
            </nav>
            <p className="text-[12px] text-ink-3">
              Viewing as{' '}
              <span className="font-medium text-ink-2">
                {borrowerSide ? 'Lakshmi, asking' : `${MEMBERS[VIEWER_ID]!.name.split(' ')[0]}, vouching`}
              </span>
            </p>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1240px] px-4 pt-8 pb-16 sm:px-8">
        <Outlet />
        <IllustrativeNotice className="mt-12" />
      </main>
    </div>
  );
}
