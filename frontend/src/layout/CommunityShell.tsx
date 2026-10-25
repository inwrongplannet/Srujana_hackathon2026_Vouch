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

const tab = ({ isActive }: { isActive: boolean }) =>
  `relative px-1 py-5 text-[14px] transition-colors ${isActive ? 'text-ink after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:bg-ink' : 'text-ink-3 hover:text-ink-2'}`;

export function CommunityShell() {
  const { members } = useCommunity();
  const { pathname } = useLocation();
  const borrowerSide = pathname.startsWith('/community/me');
  const me = members[VIEWER_ID]!;
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-20 border-b border-rule bg-paper/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-[1240px] items-center justify-between gap-6 px-4 sm:px-8">
          <div className="flex items-center gap-8">
            <Link to="/" aria-label="Vouch home">
              <Logo size={24} word="Vouch" />
            </Link>
            <nav className="hidden items-center gap-6 sm:flex">
              <NavLink to="/community" end className={tab}>
                Discover
              </NavLink>
              <NavLink to="/community/me" className={tab}>
                My ask
              </NavLink>
            </nav>
          </div>
          {borrowerSide ? (
            <div className="flex items-center gap-2.5">
              <PersonMark name="Lakshmi Naik" size={32} />
              <div className="hidden text-right sm:block">
                <p className="text-[13px] font-medium leading-tight">Lakshmi Naik</p>
                <p className="text-[11.5px] text-ink-3">asking · borrower view</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2.5">
              <div className="hidden text-right sm:block">
                <p className="text-[13px] font-medium leading-tight">{MEMBERS[VIEWER_ID]!.name}</p>
                <p className="text-[11.5px] text-ink-3">
                  {fmt(me.budget.minus(me.committed).toString(), 0)} points free · {recordLabel(me)}
                </p>
              </div>
              <PersonMark name={me.name} size={32} />
            </div>
          )}
        </div>
        <nav className="flex gap-6 border-t border-rule px-4 sm:hidden">
          <NavLink to="/community" end className={tab}>
            Discover
          </NavLink>
          <NavLink to="/community/me" className={tab}>
            My ask
          </NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-[1240px] px-4 pt-8 pb-16 sm:px-8">
        <Outlet />
        <IllustrativeNotice className="mt-12" />
      </main>
    </div>
  );
}
