import { AnimatePresence, motion } from 'motion/react';
import { IdentityGlyph } from '@/components/ui/IdentityGlyph';

/**
 * One illustration per onboarding step, drawn in the icon grammar: ink line, neel accents,
 * hatching for anything not yet known.
 */
export type ArtStep = 'aadhaar' | 'otp' | 'locker' | 'anchor';

const INK = '#16181F';
const NEEL = '#24368F';
const NEEL_500 = '#3D56C2';
const SURFACE = '#FBFAF6';
const PAPER3 = '#E3DDCF';

function Hatch({ id }: { id: string }) {
  return (
    <pattern id={id} width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
      <rect width="7" height="7" fill="#ECEEF7" />
      <rect width="1.6" height="7" fill="#C9D0EC" />
    </pattern>
  );
}

function IdCard() {
  return (
    <svg viewBox="0 0 360 280" className="h-full w-full" aria-hidden>
      <defs>
        <Hatch id="h-card" />
        <clipPath id="card-clip">
          <rect x="44" y="52" width="272" height="176" rx="16" />
        </clipPath>
      </defs>
      <rect x="52" y="62" width="272" height="176" rx="16" fill={PAPER3} />
      <rect x="44" y="52" width="272" height="176" rx="16" fill={SURFACE} stroke={INK} strokeWidth="1.6" />
      <g clipPath="url(#card-clip)">
        <rect x="44" y="52" width="272" height="38" fill="#ECEEF7" />
        <line x1="44" y1="90" x2="316" y2="90" stroke={INK} strokeWidth="1.2" />
        <text x="62" y="76" fontFamily="IBM Plex Mono" fontSize="11" letterSpacing="1.5" fill={NEEL}>
          IDENTITY · DEMO RECORD
        </text>
        <rect x="64" y="106" width="70" height="86" rx="9" fill="url(#h-card)" stroke={INK} strokeWidth="1.2" />
        <circle cx="99" cy="139" r="14" fill={SURFACE} stroke={INK} strokeWidth="1.4" />
        <path d="M76 190c3-16 12-24 23-24s20 8 23 24" fill={SURFACE} stroke={INK} strokeWidth="1.4" />
        <rect x="152" y="112" width="128" height="9" rx="4.5" fill={PAPER3} />
        <rect x="152" y="132" width="96" height="9" rx="4.5" fill={PAPER3} />
        <rect x="152" y="152" width="110" height="9" rx="4.5" fill={PAPER3} />
        <text x="152" y="194" fontFamily="IBM Plex Mono" fontSize="15" fill={INK} letterSpacing="1">
          XXXX XXXX 4821
        </text>
        <motion.g
          initial={{ y: 0 }}
          animate={{ y: [0, 150, 0] }}
          transition={{ duration: 3.6, repeat: Infinity, ease: 'easeInOut' }}
        >
          <rect x="44" y="92" width="272" height="2" fill={NEEL_500} opacity="0.7" />
          <rect x="44" y="94" width="272" height="16" fill={NEEL_500} opacity="0.06" />
        </motion.g>
      </g>
      <g transform="translate(286 34)">
        <circle r="17" fill={NEEL} />
        <path d="M-7 0.5 -2 5.5 7.5 -5" fill="none" stroke={SURFACE} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>
  );
}

function Phone() {
  return (
    <svg viewBox="0 0 360 280" className="h-full w-full" aria-hidden>
      <defs>
        <Hatch id="h-phone" />
      </defs>
      <path d="M86 92c-14 0-22 8-22 20M60 82c-24 0-36 14-36 32" fill="none" stroke={NEEL_500} strokeWidth="1.6" strokeLinecap="round" opacity="0.55" />
      <rect x="128" y="18" width="128" height="246" rx="22" fill={PAPER3} />
      <rect x="118" y="10" width="128" height="246" rx="22" fill={SURFACE} stroke={INK} strokeWidth="1.6" />
      <rect x="160" y="22" width="44" height="6" rx="3" fill={INK} />
      <rect x="132" y="40" width="100" height="196" rx="10" fill="url(#h-phone)" />
      <motion.g initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.4 }}>
        <rect x="140" y="104" width="86" height="76" rx="10" fill={SURFACE} stroke={INK} strokeWidth="1.3" />
        <text x="150" y="124" fontFamily="IBM Plex Sans" fontSize="9.5" fontWeight="600" fill={INK}>
          VeriTrust code
        </text>
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <motion.rect
            key={i}
            x={150 + i * 11.5}
            y={138}
            width="8.5"
            height="12"
            rx="2.5"
            fill={NEEL}
            initial={{ opacity: 0.15 }}
            animate={{ opacity: [0.15, 1, 1] }}
            transition={{ delay: 0.5 + i * 0.12, duration: 0.5 }}
          />
        ))}
        <text x="150" y="168" fontFamily="IBM Plex Sans" fontSize="8" fill="#6A6D76">
          Simulated · expires 2 min
        </text>
      </motion.g>
      <circle cx="182" cy="246" r="1" fill={INK} />
    </svg>
  );
}

function Locker() {
  return (
    <svg viewBox="0 0 360 280" className="h-full w-full" aria-hidden>
      <defs>
        <Hatch id="h-lock" />
      </defs>
      <rect x="62" y="96" width="78" height="96" rx="6" fill={SURFACE} stroke={INK} strokeWidth="1.2" transform="rotate(-8 100 140)" />
      <rect x="84" y="86" width="78" height="96" rx="6" fill={SURFACE} stroke={INK} strokeWidth="1.2" transform="rotate(4 120 130)" />
      <rect x="100" y="96" width="44" height="6" rx="3" fill={PAPER3} transform="rotate(4 120 130)" />
      <rect x="100" y="110" width="34" height="6" rx="3" fill={PAPER3} transform="rotate(4 120 130)" />
      <path d="M40 132a10 10 0 0 1 10-10h44l14 14h82a10 10 0 0 1 10 10v84a10 10 0 0 1-10 10H50a10 10 0 0 1-10-10Z" fill="url(#h-lock)" stroke={INK} strokeWidth="1.6" />
      <text x="62" y="214" fontFamily="IBM Plex Mono" fontSize="10.5" fill={NEEL} letterSpacing="1">
        DOCUMENTS STAY HERE
      </text>
      <motion.path
        d="M206 172 C236 172 248 150 272 150"
        fill="none"
        stroke={NEEL_500}
        strokeWidth="1.8"
        strokeDasharray="5 6"
        initial={{ strokeDashoffset: 22 }}
        animate={{ strokeDashoffset: 0 }}
        transition={{ duration: 1.1, repeat: Infinity, ease: 'linear' }}
      />
      <path d="m266 143 8 7-8 7" fill="none" stroke={NEEL_500} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <g transform="translate(300 150)">
        <circle r="30" fill={SURFACE} stroke={INK} strokeWidth="1.6" />
        <circle r="23" fill="none" stroke={NEEL} strokeWidth="1.2" strokeDasharray="2 3" />
        <path d="M-9 0.5-2.5 7 10-6" fill="none" stroke={NEEL} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      <text x="258" y="206" fontFamily="IBM Plex Mono" fontSize="10.5" fill={NEEL} letterSpacing="1">
        YES / NO ONLY
      </text>
    </svg>
  );
}

function Anchor({ hash }: { hash: string | null }) {
  return (
    <div className="relative flex h-full w-full items-center justify-center gap-5">
      <svg viewBox="0 0 220 200" className="h-[62%] w-auto" aria-hidden>
        <rect x="14" y="54" width="92" height="62" rx="8" fill={SURFACE} stroke={INK} strokeWidth="1.5" />
        <rect x="24" y="66" width="22" height="26" rx="4" fill={PAPER3} />
        <rect x="54" y="68" width="40" height="5" rx="2.5" fill={PAPER3} />
        <rect x="54" y="80" width="30" height="5" rx="2.5" fill={PAPER3} />
        <text x="24" y="108" fontFamily="IBM Plex Mono" fontSize="8" fill={INK}>XXXX 4821</text>
        <text x="20" y="140" fontFamily="IBM Plex Sans" fontSize="9.5" fill="#6A6D76">stays on device</text>
        <motion.path
          d="M112 85 H156"
          stroke={NEEL_500}
          strokeWidth="1.8"
          strokeDasharray="4 5"
          initial={{ strokeDashoffset: 18 }}
          animate={{ strokeDashoffset: 0 }}
          transition={{ duration: 0.9, repeat: Infinity, ease: 'linear' }}
        />
        <g transform="translate(176 85)">
          <rect x="-20" y="-20" width="40" height="40" rx="10" fill={NEEL} />
          <text x="0" y="6" textAnchor="middle" fontFamily="IBM Plex Mono" fontSize="17" fontWeight="500" fill={SURFACE}>
            H
          </text>
        </g>
        <text x="146" y="140" fontFamily="IBM Plex Sans" fontSize="9.5" fill="#6A6D76">one-way hash</text>
      </svg>
      <motion.div
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: hash ? 1 : 0.35, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.2, 0, 0, 1] }}
        className="flex flex-col items-center gap-3"
      >
        <IdentityGlyph hash={hash ?? '0'.repeat(64)} size={128} className={hash ? '' : 'grayscale'} />
        <span className="font-mono text-[11px] tracking-wide text-neel-800">{hash ? 'stored on chain' : 'computing…'}</span>
      </motion.div>
    </div>
  );
}

export function OnboardingArt({ step, hash }: { step: ArtStep; hash: string | null }) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={step}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        transition={{ duration: 0.32, ease: [0.2, 0, 0, 1] }}
        className="h-full w-full"
      >
        {step === 'aadhaar' && <IdCard />}
        {step === 'otp' && <Phone />}
        {step === 'locker' && <Locker />}
        {step === 'anchor' && <Anchor hash={hash} />}
      </motion.div>
    </AnimatePresence>
  );
}
