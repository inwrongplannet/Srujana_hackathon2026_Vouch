import { useState } from 'react';
import { Link } from 'react-router';
import { useSnapshot } from '@/state/DemoProvider';
import { Logo } from '@/components/brand/Logo';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { IllustrativeNotice } from '@/components/ui/Notice';
import Threads from '@/components/bits/Threads';
import BlurText from '@/components/bits/BlurText';
import RubberSegment from '@/components/bits/RubberSegment';
import {
  IconArrowRight,
  IconBreaker,
  IconFingerprint,
  IconGraph,
  IconHatch,
  IconRipple,
  IconVouch,
} from '@/components/icons';
import { HeroCompare } from '@/features/landing/HeroCompare';
import { TrustFlow } from '@/features/landing/TrustFlow';
import { ScoreGauge } from '@/features/score/ScoreGauge';
import { PathList } from '@/features/graph/PathList';

const SAFEGUARDS = [
  {
    icon: <IconFingerprint size={20} />,
    attack: 'A defaulter abandons the wallet and signs up again',
    defence: 'The identity hash is deterministic: the same Aadhaar resolves to the same defaulted record.',
    term: 'Nullifier',
  },
  {
    icon: <IconGraph size={20} />,
    attack: 'Ten friends vouch for each other in a ring',
    defence: 'Trust only flows from institutional anchors, and a path that loops back is absorbed at zero.',
    term: 'Cycle absorption',
  },
  {
    icon: <IconVouch size={20} />,
    attack: 'A respected member sells vouches for cash',
    defence: 'Capacity is split across every vouch they give, so each extra one thins all the others.',
    term: 'Out-degree conservation',
  },
  {
    icon: <IconRipple size={20} />,
    attack: 'One default drags a whole street down',
    defence: 'The sponsor pays a damped share, their sponsor less, and nobody three hops away pays anything.',
    term: '2-hop horizon',
  },
  {
    icon: <IconBreaker size={20} />,
    attack: 'A drought hits a village and many default at once',
    defence: 'Above 30% of a cluster defaulting, automatic penalties pause for restructuring.',
    term: 'Circuit breaker',
  },
  {
    icon: <IconHatch size={20} />,
    attack: 'A new borrower is mistaken for a bad one',
    defence: 'No history is recorded as uncertainty (σ² = 1), never as a −1. Data narrows it.',
    term: 'Epistemic band',
  },
];

export function LandingPage() {
  const s = useSnapshot();
  const sample = ['p_anita', 'p_suresh', 'p_farida'] as const;
  const [pick, setPick] = useState<string>('p_anita');

  return (
    <div className="min-h-dvh">
      {/* ---------- HERO ---------- */}
      <section className="relative overflow-hidden border-b border-rule">
        <div className="pointer-events-none absolute inset-0 [mask-image:linear-gradient(to_bottom,transparent,black_30%,black_70%,transparent)]">
          <Threads
            color="#24368F"
            accentColor="#3D56C2"
            lineCount={36}
            amplitude={1.1}
            distance={0.25}
            thickness={0.5}
            speed={0.25}
            angle={8}
            brightness={1}
            opacity={0.22}
            enableMouseInteraction
            className="h-full w-full"
          />
        </div>

        <nav className="relative z-10 mx-auto flex h-20 max-w-[1240px] items-center justify-between px-4 sm:px-8">
          <Logo />
          <div className="hidden items-center gap-8 text-[14px] text-ink-2 md:flex">
            <a href="#how" className="hover:text-ink">How trust moves</a>
            <a href="#axes" className="hover:text-ink">Two axes</a>
            <a href="#safeguards" className="hover:text-ink">Safeguards</a>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/app/lender" className="hidden text-[14px] text-ink-2 hover:text-ink sm:block">
              Lender console
            </Link>
            <Link to="/login">
              <Button variant="ink" size="sm" trailingIcon={<IconArrowRight size={15} />}>
                Try the demo
              </Button>
            </Link>
          </div>
        </nav>

        <div className="relative z-10 mx-auto grid max-w-[1240px] items-center gap-14 px-4 pt-10 pb-24 sm:px-8 lg:grid-cols-[1.15fr_1fr] lg:pt-16 lg:pb-32">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-rule-2 bg-surface/70 px-3 py-1 text-[12.5px] text-ink-2 backdrop-blur">
              <span className="size-1.5 rounded-full bg-neel-500" /> Community-backed credit · working prototype
            </p>
            <h1 className="display mt-6 text-[clamp(52px,7.2vw,104px)] leading-[0.92] tracking-[-0.03em]">
              <BlurText text="Unknown is not" animateBy="words" delay={90} className="block" />
              <span className="block">
                <BlurText text="the same as" animateBy="words" delay={90} className="inline" />{' '}
                <span className="text-neel-700">
                  <BlurText text="risky." animateBy="words" delay={300} className="inline" />
                </span>
              </span>
            </h1>
            <p className="mt-7 max-w-[52ch] text-[18px] leading-relaxed text-ink-2">
              Bureaus score a missing file as a bad one. VeriTrust turns the people who know your work into credit you can trace: every
              point of a score is a path through a public graph of vouches, anchored by institutions that lend real money.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link to="/login">
                <Button size="lg" trailingIcon={<IconArrowRight size={17} />}>
                  Walk the demo as Lakshmi
                </Button>
              </Link>
              <Link to="/app/lender">
                <Button size="lg" variant="secondary">
                  Open the lender console
                </Button>
              </Link>
            </div>
          </div>
          <HeroCompare />
        </div>
      </section>

      {/* ---------- HOW ---------- */}
      <section id="how" className="mx-auto max-w-[1240px] px-4 py-24 sm:px-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr] lg:items-end">
          <h2 className="display text-[clamp(36px,4.4vw,56px)] leading-[1.02]">How trust moves.</h2>
          <p className="max-w-[60ch] text-[16px] text-ink-2">
            The kirana udhaar book was India’s first community credit score. We keep its logic, that people who know you vouch for you,
            and add what it lacked: a record anyone can audit, and rules that make vouching cost something.
          </p>
        </div>
        <div className="mt-16">
          <TrustFlow />
        </div>
      </section>

      {/* ---------- AXES ---------- */}
      <section id="axes" className="border-y border-rule bg-paper-2/60">
        <div className="mx-auto grid max-w-[1240px] gap-12 px-4 py-24 sm:px-8 lg:grid-cols-[0.9fr_1.4fr]">
          <div>
            <p className="eyebrow">Live from the scoring engine</p>
            <h2 className="display mt-3 text-[clamp(36px,4.4vw,56px)] leading-[1.02]">Two axes, never one number.</h2>
            <p className="mt-5 text-[16px] text-ink-2">
              Expected capacity μ says how much someone can carry. Uncertainty σ² says how sure we are. The lendable score is the lower
              bound, μ − √σ², so a thin file starts small and grows as evidence arrives, instead of being refused.
            </p>
            <div className="mt-8">
              <RubberSegment
                value={pick}
                onChange={setPick}
                items={sample.map((id) => ({ value: id, label: s.nodes[id]!.name.split(' ')[0] }))}
                trackColor="#E3DDCF"
                thumbColor="#FBFAF6"
                textColor="#6A6D76"
                activeTextColor="#16181F"
                radius={10}
                aria-label="Pick a member"
              />
              <p className="mt-3 text-[13px] text-ink-3">
                {pick === 'p_anita' ? 'New vendor, one vouch, no data.' : pick === 'p_suresh' ? 'One repaid loan, bank statements linked.' : 'Three repaid loans, full file.'}
              </p>
            </div>
          </div>
          <div className="card space-y-6 p-7 shadow-[var(--shadow-lift)]">
            <div className="flex items-center gap-3">
              <Avatar node={s.nodes[pick]!} size={38} />
              <div>
                <p className="font-medium">{s.nodes[pick]!.name}</p>
                <p className="text-[12.5px] text-ink-3">{s.nodes[pick]!.role}</p>
              </div>
            </div>
            <ScoreGauge a={s.assessments[pick]!} node={s.nodes[pick]!} compact />
            <div className="border-t border-rule pt-5">
              <PathList a={s.assessments[pick]!} s={s} />
            </div>
          </div>
        </div>
      </section>

      {/* ---------- SAFEGUARDS ---------- */}
      <section id="safeguards" className="mx-auto max-w-[1240px] px-4 py-24 sm:px-8">
        <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr] lg:items-end">
          <h2 className="display text-[clamp(36px,4.4vw,56px)] leading-[1.02]">Built to be gamed. It isn’t.</h2>
          <p className="max-w-[60ch] text-[16px] text-ink-2">
            Every rule below is enforced by the protocol and can be watched happening in the demo, not promised in a policy document.
          </p>
        </div>
        <div className="mt-12 border-t border-ink">
          {SAFEGUARDS.map((g) => (
            <div key={g.term} className="grid gap-3 border-b border-rule py-6 md:grid-cols-[44px_1fr_1.3fr_180px] md:items-baseline md:gap-8">
              <span className="text-neel-700">{g.icon}</span>
              <p className="text-[16px] font-medium">{g.attack}</p>
              <p className="text-[15px] text-ink-2">{g.defence}</p>
              <p className="font-mono text-[12px] tracking-wide text-neel-800 md:text-right">{g.term}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- SEATS ---------- */}
      <section className="bg-ink text-paper">
        <div className="mx-auto max-w-[1240px] px-4 py-20 sm:px-8">
          <div className="grid gap-10 lg:grid-cols-[1fr_1.6fr] lg:items-center">
            <div>
              <p className="font-mono text-[11px] tracking-[0.16em] text-neel-300">THE DEMO</p>
              <h2 className="display mt-3 text-[clamp(34px,4vw,52px)] leading-[1.02]">Three seats, one story.</h2>
              <p className="mt-4 text-[15px] text-paper/70">A presenter bar at the bottom of the app moves the clock, repays or defaults, and triggers a regional shock.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {[
                { to: '/login', node: s.nodes[s.borrowerId]!, seat: 'Borrower', line: 'Signs in, asks for a vouch, borrows' },
                { to: '/app/voucher', node: s.nodes[s.voucherId]!, seat: 'Voucher', line: 'Sees the price of saying yes' },
                { to: '/app/lender', node: s.nodes[s.lenderId]!, seat: 'Lender', line: 'Decides on both axes, watches the cascade' },
              ].map((x) => (
                <Link key={x.seat} to={x.to} className="group rounded-[14px] border border-paper/15 p-5 transition-colors hover:border-paper/40 hover:bg-paper/5">
                  <p className="font-mono text-[11px] tracking-[0.12em] text-paper/50">{x.seat.toUpperCase()}</p>
                  <p className="display mt-2 text-[24px] leading-tight">{x.node.name}</p>
                  <p className="mt-2 text-[13.5px] text-paper/65">{x.line}</p>
                  <IconArrowRight size={18} className="mt-5 text-neel-300 transition-transform group-hover:translate-x-1" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      <footer className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-4 px-4 py-8 sm:px-8">
        <Logo size={22} />
        <IllustrativeNotice />
        <p className="text-[12px] text-ink-3">Prototype · simulated chain · demo identities only</p>
      </footer>
    </div>
  );
}
