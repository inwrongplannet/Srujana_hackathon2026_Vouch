import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { AnimatePresence, motion } from 'motion/react';
import { api } from '@/api/client';
import type { DemoIdentity, RegisterResponse } from '@/api/types';
import { Logo } from '@/components/brand/Logo';
import { Button } from '@/components/ui/Button';
import { IllustrativeNotice } from '@/components/ui/Notice';
import { Badge } from '@/components/ui/StatusBadge';
import { IdentityGlyph } from '@/components/ui/IdentityGlyph';
import Noise from '@/components/bits/Noise';
import CodeSlots from '@/components/bits/CodeSlots';
import DecryptedText from '@/components/bits/DecryptedText';
import {
  IconAlert,
  IconArrowRight,
  IconCheck,
  IconLocker,
  IconShield,
  IconArrowLeft,
} from '@/components/icons';
import { OnboardingArt, type ArtStep } from '@/features/onboarding/OnboardingArt';
import { StepRail } from '@/features/onboarding/StepRail';

const STEPS: { key: ArtStep; label: string; title: string; copy: string }[] = [
  {
    key: 'aadhaar',
    label: 'Aadhaar',
    title: 'One person, one node.',
    copy: 'Your identity anchors you to the trust graph exactly once. Nobody can open a second account to escape a bad record.',
  },
  {
    key: 'otp',
    label: 'Verify',
    title: 'Prove the number is yours.',
    copy: 'A one-time code goes to the mobile linked to this identity. In the demo, any six digits work.',
  },
  {
    key: 'locker',
    label: 'DigiLocker',
    title: 'Attestations, not documents.',
    copy: 'DigiLocker answers yes or no on what we ask. Your documents never leave it and never reach us.',
  },
  {
    key: 'anchor',
    label: 'Anchor',
    title: 'Your number becomes a fingerprint.',
    copy: 'A one-way hash turns your identity into a nullifier. The same identity always gives the same fingerprint, and the number can’t be recovered from it.',
  },
];

const groupDigits = (d: string) => d.replace(/(\d{4})(?=\d)/g, '$1 ');
const fade = {
  initial: { opacity: 0, x: 16 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -12 },
  transition: { duration: 0.28, ease: [0.2, 0, 0, 1] as const },
};

export function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [digits, setDigits] = useState('');
  const [identity, setIdentity] = useState<DemoIdentity | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [otpStatus, setOtpStatus] = useState<'idle' | 'success'>('idle');
  const [result, setResult] = useState<RegisterResponse | null>(null);

  // The story's borrower first; the defaulter second, for the anti-churn demo.
  const demoIds = api
    .identities()
    .filter((i) => i.rawId !== '000000001102')
    .sort((a, b) => (a.rawId === '000000004821' ? -1 : b.rawId === '000000004821' ? 1 : 0));

  async function submitAadhaar() {
    setError(null);
    if (!/^0000\d{8}$/.test(digits)) {
      setError('Demo mode accepts test numbers starting 0000 only. Never enter a real Aadhaar.');
      return;
    }
    setBusy(true);
    const found = await api.lookupIdentity(digits);
    setBusy(false);
    if (!found) {
      setError('No demo identity with that number. Pick one below.');
      return;
    }
    setIdentity(found);
    setStep(1);
  }

  function otpComplete() {
    setOtpStatus('success');
    setTimeout(() => setStep(2), 750);
  }

  async function allowLocker() {
    setStep(3);
    setBusy(true);
    const res = await api.register(digits);
    // Leave the hash on screen long enough for the reveal to read as computation.
    setTimeout(() => {
      setResult(res);
      setBusy(false);
    }, 650);
  }

  const current = STEPS[step]!;

  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(420px,44%)_1fr]">
      {/* ------- Story panel ------- */}
      <aside className="relative hidden overflow-hidden border-r border-rule bg-paper-2 lg:flex lg:flex-col">
        <Noise opacity={0.035} fps={0} blendMode="multiply" dust={0} scratches={0} scanlines={0} flicker={0} />
        <div className="relative z-10 flex items-center justify-between px-10 pt-9">
          <Link to="/" aria-label="Vouch home">
            <Logo />
          </Link>
          <Badge tone="plain">Simulated identity anchor</Badge>
        </div>
        <div className="relative z-10 flex flex-1 items-center justify-center px-10">
          <div className="aspect-[9/7] w-full max-w-[460px]">
            <OnboardingArt step={current.key} hash={result?.nullifier ?? null} />
          </div>
        </div>
        <div className="relative z-10 px-10 pb-10">
          <AnimatePresence mode="wait">
            <motion.div key={current.key} {...fade}>
              <p className="eyebrow mb-3">
                Step {step + 1} of {STEPS.length}
              </p>
              <h2 className="display max-w-[16ch] text-[40px] leading-[1.02]">{current.title}</h2>
              <p className="mt-4 max-w-[46ch] text-[15px] text-ink-2">{current.copy}</p>
            </motion.div>
          </AnimatePresence>
          <IllustrativeNotice className="mt-8" />
        </div>
      </aside>

      {/* ------- Form panel ------- */}
      <main className="flex flex-col px-4 py-6 sm:px-10 lg:px-16 lg:py-9">
        <div className="flex items-center justify-between gap-4">
          <Link to="/" aria-label="Vouch home" className="lg:hidden">
            <Logo size={22} word="" />
          </Link>
          <StepRail steps={STEPS.map((s) => s.label)} current={step} />
          <button
            type="button"
            onClick={() => navigate('/app/lender')}
            className="hidden text-[13px] text-ink-3 underline-offset-4 hover:text-ink hover:underline md:block"
          >
            Skip to lender console
          </button>
        </div>

        <div className="flex flex-1 items-center">
          <div className="mx-auto w-full max-w-[440px] py-12">
            <AnimatePresence mode="wait">
              {step === 0 && (
                <motion.section key="aadhaar" {...fade}>
                  <h1 className="display text-[34px] leading-tight">Verify with Aadhaar</h1>
                  <p className="mt-2 text-ink-2">Sign in once. Your number is hashed on this device before anything is sent.</p>
                  <form
                    className="mt-8"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void submitAadhaar();
                    }}
                  >
                    <label htmlFor="aadhaar" className="text-[13px] font-medium">
                      Aadhaar number
                    </label>
                    <div className="relative mt-2">
                      <input
                        id="aadhaar"
                        inputMode="numeric"
                        autoComplete="off"
                        placeholder="0000 0000 0000"
                        value={groupDigits(digits)}
                        onChange={(e) => setDigits(e.target.value.replace(/\D/g, '').slice(0, 12))}
                        aria-invalid={!!error}
                        aria-describedby="aadhaar-help"
                        className="h-14 w-full rounded-[8px] border border-rule-2 bg-surface px-4 font-mono text-[20px] tracking-[0.12em] text-ink placeholder:text-rule-2 focus:border-neel-500 focus:outline-none focus:ring-4 focus:ring-neel-100"
                      />
                      <IconShield size={20} className="absolute top-1/2 right-4 -translate-y-1/2 text-ink-3" />
                    </div>
                    {error ? (
                      <p className="mt-2 flex items-start gap-1.5 text-[13px] text-defaulted" role="alert">
                        <IconAlert size={15} className="mt-0.5 shrink-0" />
                        {error}
                      </p>
                    ) : (
                      <p id="aadhaar-help" className="mt-2 text-[13px] text-ink-3">
                        Demo mode: test numbers start with 0000. Never enter a real Aadhaar.
                      </p>
                    )}
                    <Button type="submit" size="lg" className="mt-6 w-full" loading={busy} disabled={digits.length !== 12} trailingIcon={<IconArrowRight size={17} />}>
                      Send one-time code
                    </Button>
                  </form>

                  <div className="mt-10">
                    <p className="eyebrow mb-3">Demo identities</p>
                    <ul className="ruled overflow-hidden rounded-[10px] border border-rule bg-surface">
                      {demoIds.map((id) => (
                        <li key={id.rawId}>
                          <button
                            type="button"
                            onClick={() => {
                              setDigits(id.rawId);
                              setError(null);
                            }}
                            className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-paper"
                          >
                            <span>
                              <span className="block text-[14px] font-medium">{id.name}</span>
                              <span className="block text-[12.5px] text-ink-3">
                                {id.occupation}
                                {id.rawId === '000000000007' ? ' · defaulted last year, tries again' : ' · new to credit'}
                              </span>
                            </span>
                            <span className="font-mono text-[12.5px] text-ink-2 group-hover:text-neel-700">{groupDigits(id.rawId)}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                </motion.section>
              )}

              {step === 1 && identity && (
                <motion.section key="otp" {...fade}>
                  <BackLink onClick={() => setStep(0)} />
                  <h1 className="display text-[34px] leading-tight">Enter the code</h1>
                  <p className="mt-2 text-ink-2">
                    Sent to the mobile linked with <span className="font-mono text-ink">XXXX XXXX {digits.slice(-4)}</span> (simulated).
                  </p>
                  <div className="mt-8">
                    <CodeSlots
                      length={6}
                      autoFocus
                      status={otpStatus}
                      onComplete={otpComplete}
                      accentColor="#24368F"
                      inkColor="#16181F"
                      slotColor="#EBE6DB"
                      digitColor="#FBFAF6"
                      dangerColor="#A8352A"
                      slotSize={56}
                      gap={10}
                      radius={10}
                      ariaLabel="One-time code"
                    />
                  </div>
                  <p className="mt-5 text-[13px] text-ink-3">Any six digits work in the demo. Paste works too.</p>
                </motion.section>
              )}

              {step === 2 && identity && (
                <motion.section key="locker" {...fade}>
                  <BackLink onClick={() => setStep(1)} />
                  <div className="flex items-center gap-3">
                    <span className="grid size-11 place-items-center rounded-[10px] bg-neel-50 text-neel-700">
                      <IconLocker size={22} />
                    </span>
                    <div>
                      <p className="eyebrow">DigiLocker · simulated consent</p>
                      <h1 className="display text-[30px] leading-tight">Vouch is asking for</h1>
                    </div>
                  </div>
                  <ul className="ruled mt-7 rounded-[10px] border border-rule bg-surface">
                    {[
                      ['Aadhaar e-KYC', `Name ${identity.name}, born ${identity.yearOfBirth}, ${identity.district}`],
                      ['PAN', 'Verified or not. The number is not shared'],
                      ['Nothing else', 'No bank statements, no photos, no address history'],
                    ].map(([title, detail]) => (
                      <li key={title} className="flex gap-3 px-4 py-3.5">
                        <IconCheck size={18} className="mt-0.5 shrink-0 text-active" />
                        <span>
                          <span className="block text-[14px] font-medium">{title}</span>
                          <span className="block text-[13px] text-ink-3">{detail}</span>
                        </span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-4 text-[13px] text-ink-3">Consent lasts for this sign-in only. You can withdraw it from DigiLocker at any time.</p>
                  <div className="mt-7 flex gap-3">
                    <Button size="lg" className="flex-1" onClick={() => void allowLocker()}>
                      Allow
                    </Button>
                    <Button size="lg" variant="secondary" onClick={() => setStep(0)}>
                      Deny
                    </Button>
                  </div>
                </motion.section>
              )}

              {step === 3 && (
                <motion.section key="anchor" {...fade}>
                  <AnchorStep result={result} busy={busy} onContinue={(path) => navigate(path)} />
                </motion.section>
              )}
            </AnimatePresence>
          </div>
        </div>
        <IllustrativeNotice className="lg:hidden" />
      </main>
    </div>
  );
}

function BackLink({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="mb-6 inline-flex items-center gap-1.5 text-[13px] text-ink-3 hover:text-ink">
      <IconArrowLeft size={15} /> Back
    </button>
  );
}

function AnchorStep({
  result,
  busy,
  onContinue,
}: {
  result: RegisterResponse | null;
  busy: boolean;
  onContinue: (path: string) => void;
}) {
  if (busy || !result) {
    return (
      <div>
        <p className="eyebrow">Hashing on this device</p>
        <h1 className="display mt-2 text-[34px] leading-tight">Anchoring your identity</h1>
        <div className="mt-8 rounded-[10px] border border-rule bg-surface p-5 font-mono text-[13px] leading-6 text-ink-2">
          <p>sk&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= H(aadhaar, your salt)</p>
          <p>nullifier = H(sk, protocol salt)</p>
        </div>
      </div>
    );
  }

  const blocked = result.existing && result.node.status === 'DEFAULTED';
  return (
    <div>
      <p className="eyebrow">{result.existing ? 'Already anchored' : 'Identity anchored'}</p>
      <h1 className="display mt-2 text-[34px] leading-tight">
        {blocked ? 'Same identity, same record.' : result.existing ? 'Welcome back.' : `Welcome, ${result.node.name.split(' ')[0]}.`}
      </h1>
      <div className="mt-7 flex items-center gap-5 rounded-[12px] border border-rule bg-surface p-5">
        <IdentityGlyph hash={result.nullifier} size={76} />
        <div className="min-w-0">
          <p className="text-[12px] text-ink-3">Nullifier · simulated identity anchor</p>
          <DecryptedText
            text={`${result.nullifier.slice(0, 18)}…${result.nullifier.slice(-8)}`}
            animateOn="view"
            sequential
            revealDirection="start"
            speed={28}
            characters="0123456789abcdef"
            className="font-mono text-[14px] text-ink"
            encryptedClassName="font-mono text-[14px] text-neel-500"
            parentClassName="mt-1 block truncate"
          />
          <p className="mt-2 text-[12px] text-ink-3">Your Aadhaar number was not sent. Only this fingerprint is stored.</p>
        </div>
      </div>

      {blocked ? (
        <div className="mt-5 rounded-[12px] border border-defaulted/30 bg-defaulted-tint p-5">
          <p className="flex items-center gap-2 font-medium text-defaulted">
            <IconAlert size={17} /> This identity defaulted earlier
          </p>
          <p className="mt-1.5 text-[14px] text-ink-2">
            Re-registering produced the identical nullifier, so the protocol resolved it to the existing <b>DEFAULTED</b> record. A fresh wallet cannot shed a past default.
          </p>
          <Button className="mt-4" variant="secondary" onClick={() => onContinue('/app/lender')} trailingIcon={<IconArrowRight size={16} />}>
            See it in the lender console
          </Button>
        </div>
      ) : (
        <>
          <dl className="mt-5 grid grid-cols-3 gap-px overflow-hidden rounded-[12px] border border-rule bg-rule">
            {[
              ['Credibility', '0.00'],
              ['Uncertainty σ²', '1.00'],
              ['Status', 'Cold start'],
            ].map(([k, v]) => (
              <div key={k} className="bg-surface px-4 py-3">
                <dt className="text-[12px] text-ink-3">{k}</dt>
                <dd className="num mt-0.5 text-[17px] font-medium">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-[14px] text-ink-2">
            No history yet, so we treat you as <b>unknown, not risky</b>. One vouch from someone who knows your work opens your first limit.
          </p>
          <Button size="lg" className="mt-7 w-full" onClick={() => onContinue('/app/borrower')} trailingIcon={<IconArrowRight size={17} />}>
            Open my dashboard
          </Button>
        </>
      )}
    </div>
  );
}
