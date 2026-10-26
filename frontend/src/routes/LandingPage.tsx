import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { motion, useReducedMotion } from 'motion/react';
import { Logo } from '@/components/brand/Logo';
import { ButtonLink } from '@/components/ui/Button';
import { IllustrativeNotice } from '@/components/ui/Notice';
import { IconArrowRight, IconCommunity, IconGauge, IconPlay } from '@/components/icons';
import { AssessmentPanel } from '@/features/landing/AssessmentPanel';
import { HowItDecides } from '@/features/landing/HowItDecides';
import { Research } from '@/features/landing/Evidence';
import { Problem } from '@/features/landing/Problem';
import { HowFlow } from '@/features/landing/HowFlow';
import { Proof } from '@/features/landing/Proof';
import { BusinessModel } from '@/features/landing/BusinessModel';
import { Reveal, Section } from '@/features/landing/Story';
import { BackendDot } from '@/layout/ProductNav';
import { useBackend } from '@/state/backendStatus';

/** Ledger paper: faint blue rules with the red margin line of a bahi-khata page. */
const LEDGER = {
  backgroundImage:
    'linear-gradient(to right, transparent 39px, rgb(168 53 42 / 0.22) 39px 40px, transparent 40px), repeating-linear-gradient(to bottom, transparent 0 39px, rgb(36 54 143 / 0.06) 39px 40px)',
};

/**
 * In-page links scroll here directly: a hash change would reach the router as a navigation and
 * its scroll restoration would put the page back at the top.
 */
function jumpTo(e: React.MouseEvent<HTMLAnchorElement>, id: string) {
  const el = document.getElementById(id);
  if (!el) return;
  e.preventDefault();
  el.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}

const SECTIONS = [
  { id: 'problem', label: 'The problem' },
  { id: 'how', label: 'How it works' },
  { id: 'proof', label: 'Proof' },
  { id: 'evidence', label: 'Research' },
  { id: 'business', label: 'Business' },
  { id: 'try', label: 'Try it' },
];

/** Stays on top while reading; gains a rule and paper once the page scrolls under it. */
function TopNav() {
  const [scrolled, setScrolled] = useState(false);
  const [current, setCurrent] = useState<string | null>(null);
  useEffect(() => {
    const on = () => {
      setScrolled(window.scrollY > 8);
      // The section whose top has passed a third of the way down the screen is the one being read.
      const line = window.innerHeight / 3;
      const passed = SECTIONS.filter((x) => (document.getElementById(x.id)?.getBoundingClientRect().top ?? Infinity) <= line);
      setCurrent(passed.at(-1)?.id ?? null);
    };
    on();
    window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  }, []);
  return (
    <nav
      aria-label="Page"
      className={`sticky top-0 z-30 transition-[background-color,border-color] duration-200 ${
        scrolled ? 'border-b border-rule bg-paper/90 backdrop-blur-md' : 'border-b border-transparent'
      }`}
    >
      <div className="mx-auto flex h-16 w-full max-w-[1180px] items-center justify-between gap-6 px-4 sm:px-8">
        <Link to="/" aria-label="Vouch home">
          <Logo />
        </Link>
        <div className="hidden items-center gap-7 md:flex">
          {SECTIONS.map((x) => (
            <a
              key={x.id}
              href={`#${x.id}`}
              onClick={(e) => jumpTo(e, x.id)}
              aria-current={current === x.id ? 'location' : undefined}
              className={`text-[14px] transition-colors hover:text-ink ${current === x.id ? 'text-ink underline decoration-neel-500 decoration-2 underline-offset-[6px]' : 'text-ink-2'}`}
            >
              {x.label}
            </a>
          ))}
        </div>
        <ButtonLink to="/login" variant="ink" size="sm" trailingIcon={<IconArrowRight size={15} />}>
          Start the story
        </ButtonLink>
      </div>
    </nav>
  );
}

function Hero() {
  const reduce = useReducedMotion();
  const enter = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 14 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] as const },
  });
  return (
    <header className="relative -mt-16 flex min-h-dvh flex-col pt-16" style={LEDGER}>
      <div className="mx-auto grid w-full max-w-[1180px] flex-1 items-center gap-12 px-4 pt-4 pb-16 sm:px-8 lg:grid-cols-[1fr_1.05fr] lg:gap-14">
        <div>
          <motion.p {...enter(0)} className="font-mono text-[12px] tracking-[0.16em] text-ink-3">
            PEER-BACKED EVIDENCE FOR CREDIT DECISIONS
          </motion.p>
          <h1 className="display mt-6 text-[clamp(42px,5vw,68px)] leading-[0.98] tracking-[-0.03em] text-balance">
            <motion.span {...enter(0.1)} className="block">
              No score isn’t a bad score.
            </motion.span>
            <motion.span {...enter(0.5)} className="mt-2 block text-neel-700">
              A falling score isn’t the whole story.
            </motion.span>
          </h1>
          <motion.p {...enter(0.9)} className="mt-8 max-w-[46ch] text-[17px] leading-relaxed text-ink-2">
            Vouch sits beside the bureau. People who know a borrower stake their own reputation on them, the loan is checked against real cash
            flow, and every signal is shown on its own, with its evidence.
          </motion.p>
          <motion.div {...enter(1.1)} className="mt-9 flex flex-wrap items-center gap-3">
            <ButtonLink to="/login" size="lg" trailingIcon={<IconArrowRight size={17} />}>
              Start the guided story
            </ButtonLink>
            <ButtonLink to="/app/assess" size="lg" variant="secondary">
              Run a live assessment
            </ButtonLink>
          </motion.div>
          <motion.p {...enter(1.2)} className="mt-5 text-[13.5px] text-ink-3">
            Or{' '}
            <a href="#problem" onClick={(e) => jumpTo(e, 'problem')} className="text-ink-2 underline decoration-rule-2 underline-offset-4 hover:text-ink">
              read why it matters
            </a>
            , with the numbers and their sources.
          </motion.p>
        </div>
        <motion.div {...enter(0.3)}>
          <AssessmentPanel />
        </motion.div>
      </div>
    </header>
  );
}

const WAYS_IN = [
  {
    to: '/login',
    icon: <IconPlay size={20} />,
    title: 'Guided story',
    tag: 'Demo data · about 5 minutes',
    body: 'Follow Lakshmi from a blank file to her first loan: she anchors her identity, Meena vouches, Sahyog Microfinance decides, and a shock tests who stands by her.',
    cta: 'Start the story',
    live: false,
  },
  {
    to: '/community',
    icon: <IconCommunity size={20} />,
    title: 'Community',
    tag: 'Demo data',
    body: 'Browse people asking for a vouch as Meena. Read their files, and see what backing someone would cost your own reputation before you decide.',
    cta: 'Open the community',
    live: false,
  },
  {
    to: '/app/assess',
    icon: <IconGauge size={20} />,
    title: 'Assessment desk',
    tag: 'Live backend',
    body: 'Run the real assessment against the API: bureau, Vouch Score, affordability and evidence side by side, then move the what-if sliders.',
    cta: 'Run an assessment',
    live: true,
  },
];

function WayIn({ to, icon, title, tag, body, cta, live }: (typeof WAYS_IN)[number]) {
  const b = useBackend();
  return (
    <Link
      to={to}
      className="group flex h-full flex-col rounded-[var(--radius-card)] border border-paper/15 bg-paper/[0.04] p-6 transition-colors hover:border-paper/40 hover:bg-paper/[0.07]"
    >
      <div className="flex items-center justify-between">
        <span className="grid size-10 place-items-center rounded-[9px] bg-paper/10 text-paper">{icon}</span>
        <span className="inline-flex items-center gap-2 font-mono text-[11px] text-paper/60">
          {live ? <BackendDot /> : null}
          {live && b.status === 'offline' ? 'Backend offline' : tag}
        </span>
      </div>
      <p className="display mt-6 text-[26px] leading-tight">{title}</p>
      <p className="mt-2 text-[14px] leading-relaxed text-paper/70">{body}</p>
      <span className="mt-auto inline-flex items-center gap-2 pt-6 text-[14px] font-medium text-paper">
        {cta}
        <IconArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-dvh">
      <TopNav />
      <Hero />

      <Section id="problem" kicker="The problem" title="Three things a credit score alone cannot see.">
        <Problem />
      </Section>

      <Section id="how" kicker="How it works" title="Trust is useful evidence. But it needs to be earned.">
        <p className="mt-5 max-w-[66ch] text-[16px] leading-relaxed text-ink-2">
          Vouch is a complementary layer that combines accountable peer endorsements with consent-based financial evidence. It helps lenders see beyond a
          credit score without replacing the credit bureau or the lender’s judgment.
        </p>
        <HowFlow />
        <p className="mt-20 font-mono text-[11.5px] tracking-[0.16em] text-neel-700">SEE EACH STEP UP CLOSE</p>
        <HowItDecides />
        <IllustrativeNotice className="mt-8" />
      </Section>

      <Section id="proof" kicker="Does it work? We tested it" title="The vouch sees what the bureau misses.">
        <Proof />
      </Section>

      <Section id="evidence" kicker="What the research says" title="The signal is real. So is the trap.">
        <Research />
      </Section>

      <Section id="business" kicker="Business model" title="Lenders pay. Borrowers never do.">
        <BusinessModel />
      </Section>

      <section id="try" className="scroll-mt-16 bg-ink text-paper">
        <div className="mx-auto max-w-[1180px] px-4 py-20 sm:px-8 lg:py-24">
          <Reveal>
            <p className="font-mono text-[11.5px] tracking-[0.16em] text-neel-300">THREE WAYS IN</p>
            <p className="display mt-3 max-w-[18ch] text-[clamp(36px,5.4vw,72px)] leading-[0.95] tracking-[-0.03em] text-balance">
              Signals, not a verdict. A person decides.
            </p>
            <p className="mt-6 max-w-[62ch] text-[15px] leading-relaxed text-paper/75">
              Vouch tests whether accountable, outcome-weighted endorsements can improve assessment for thin-file and unusual-circumstance borrowers,
              while measuring default risk, fairness and manipulation resistance. See it from three sides:
            </p>
          </Reveal>
          <div className="mt-12 grid gap-4 lg:grid-cols-3">
            {WAYS_IN.map((w, n) => (
              <Reveal key={w.to} delay={n * 0.06} className="h-full">
                <WayIn {...w} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-rule">
        <div className="mx-auto grid max-w-[1180px] gap-8 px-4 py-12 sm:px-8 md:grid-cols-[1.2fr_1fr_1.4fr]">
          <div>
            <Logo size={22} />
            <p className="mt-3 max-w-[34ch] text-[13px] leading-relaxed text-ink-3">Peer-backed evidence beside the credit bureau. A hackathon prototype for F-04.</p>
          </div>
          <nav aria-label="Footer" className="flex flex-col gap-2 text-[13.5px]">
            <p className="eyebrow mb-1">Open</p>
            <Link to="/login" className="text-ink-2 hover:text-ink">
              Guided story
            </Link>
            <Link to="/community" className="text-ink-2 hover:text-ink">
              Community
            </Link>
            <Link to="/app/assess" className="text-ink-2 hover:text-ink">
              Assessment desk
            </Link>
          </nav>
          <div className="space-y-2 text-[12.5px] leading-relaxed text-ink-3">
            <p className="eyebrow mb-1">About the numbers</p>
            <IllustrativeNotice />
            <p>People, scores and cases are fictional demo data.</p>
            <p>Research figures link to their published sources. Dataset figures are documented in data/combined/README.md.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
