/**
 * The three ways into Vouch, shown in every app header so a viewer can move between them without
 * going back to the landing page: the guided story (mock), the community (mock) and the
 * Assessment desk (live backend, with its status dot).
 */
import { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router';
import { checkBackend, useBackend } from '@/state/backendStatus';
import { Button } from '@/components/ui/Button';

const item = (active: boolean) =>
  `relative flex h-full items-center gap-1.5 whitespace-nowrap text-[13.5px] transition-colors ${
    active ? 'text-ink after:absolute after:inset-x-0 after:bottom-0 after:h-[2px] after:bg-ink' : 'text-ink-3 hover:text-ink-2'
  }`;

export function ProductNav() {
  const { pathname } = useLocation();
  const desk = pathname.startsWith('/app/assess');
  const story = pathname.startsWith('/app') && !desk;
  return (
    <nav aria-label="Vouch" className="flex h-full items-stretch gap-5 sm:gap-7">
      <NavLink to="/app" className={() => item(story)}>
        <span className="sm:hidden">Story</span>
        <span className="hidden sm:inline">Guided story</span>
      </NavLink>
      <NavLink to="/community" className={({ isActive }) => item(isActive)}>
        Community
      </NavLink>
      <NavLink to="/app/assess" className={() => item(desk)}>
        <span className="sm:hidden">Assess</span>
        <span className="hidden sm:inline">Assessment desk</span>
        <BackendDot />
      </NavLink>
    </nav>
  );
}

/** Green when the FastAPI backend answers /health, grey when the desk would be offline. */
export function BackendDot() {
  const b = useBackend();
  useEffect(() => {
    void checkBackend();
  }, []);
  const label = b.status === 'live' ? 'Backend live' : b.status === 'offline' ? 'Backend offline' : 'Checking backend';
  const tone = b.status === 'live' ? 'bg-active' : b.status === 'offline' ? 'bg-cold' : 'bg-ink-3 animate-pulse';
  return <span role="img" aria-label={label} title={label} className={`size-2 shrink-0 rounded-full ${tone}`} />;
}

/** Probes /health again without reloading the page; shown wherever a screen fell back to demo data. */
export function TryAgain() {
  const checking = useBackend().status === 'checking';
  return (
    <Button size="sm" variant="ghost" disabled={checking} onClick={() => void checkBackend()}>
      {checking ? 'Checking…' : 'Try again'}
    </Button>
  );
}
