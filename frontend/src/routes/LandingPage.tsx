import { Link } from 'react-router';
import { motion, useReducedMotion } from 'motion/react';
import { Logo } from '@/components/brand/Logo';
import { Button } from '@/components/ui/Button';
import { IllustrativeNotice } from '@/components/ui/Notice';
import { IconArrowRight } from '@/components/icons';
import { AssessmentPanel } from '@/features/landing/AssessmentPanel';
import { Refused } from '@/features/landing/Refused';
import { HowItDecides } from '@/features/landing/HowItDecides';
import { Reveal, Section } from '@/features/landing/Story';

/** Ledger paper: faint blue rules with the red margin line of a bahi-khata page. */
const LEDGER = {
  backgroundImage:
    'linear-gradient(to right, transparent 39px, rgb(168 53 42 / 0.22) 39px 40px, transparent 40px), repeating-linear-gradient(to bottom, transparent 0 39px, rgb(36 54 143 / 0.06) 39px 40px)',
};

function Hero() {
  const reduce = useReducedMotion();
  const enter = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 14 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.8, delay, ease: [0.22, 1, 0.36, 1] as const },
  });
  return (
    <header className="relative flex min-h-dvh flex-col" style={LEDGER}>
      <nav className="mx-auto flex h-20 w-full max-w-[1180px] items-center justify-between px-4 sm:px-8">
        <Logo word="Vouch" />
        <div className="flex items-center gap-5">
          <Link to="/app/lender" className="hidden text-[14px] text-ink-2 hover:text-ink sm:block">
            Lender console
          </Link>
          <Link to="/login">
            <Button variant="ink" size="sm" trailingIcon={<IconArrowRight size={15} />}>
              Open the demo
            </Button>
          </Link>
        </div>
      </nav>

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
          <motion.div {...enter(1.1)} className="mt-9 flex flex-wrap gap-3">
            <Link to="/app/lender">
              <Button size="lg" trailingIcon={<IconArrowRight size={17} />}>
                Open the lender console
              </Button>
            </Link>
            <a href="#how">
              <Button size="lg" variant="secondary">
                See how it works
              </Button>
            </a>
          </motion.div>
        </div>
        <motion.div {...enter(0.3)}>
          <AssessmentPanel />
        </motion.div>
      </div>
    </header>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-dvh">
      <Hero />

      <Section kicker="The cost of a blank file" title="People without a file are not an edge case.">
        <Refused />
      </Section>

      <Section id="how" kicker="How it works" title="Evidence, not popularity.">
        <HowItDecides />
        <IllustrativeNotice className="mt-8" />
      </Section>

      <section className="bg-ink text-paper">
        <div className="mx-auto grid max-w-[1180px] gap-10 px-4 py-20 sm:px-8 lg:grid-cols-[1.4fr_1fr] lg:items-end lg:py-24">
          <Reveal>
            <p className="display max-w-[16ch] text-[clamp(36px,5.4vw,76px)] leading-[0.95] tracking-[-0.03em] text-balance">
              Signals, not a verdict. A person decides.
            </p>
          </Reveal>
          <Reveal delay={0.12} className="flex flex-wrap gap-3 lg:justify-end">
            <Link to="/app/lender">
              <Button size="lg" trailingIcon={<IconArrowRight size={17} />}>
                Open the lender console
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="secondary">
                Walk the demo
              </Button>
            </Link>
          </Reveal>
        </div>
      </section>

      <footer className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-4 px-4 py-8 sm:px-8">
        <Logo size={22} word="Vouch" />
        <IllustrativeNotice />
        <p className="text-[12px] text-ink-3">People, scores and cases are fictional demo data. Dataset figures: data/combined/README.md</p>
      </footer>
    </div>
  );
}
