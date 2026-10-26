/**
 * Business model, from the team's business model (frontend/Vouch_Business_Model.md): who pays whom
 * under each deployment, drawn as a live flow beside that model's prices. Prices are planning
 * assumptions and come from the mock engine.
 */
import { useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import { PRICES, type Model } from '@/mocks/engine/business';
import { formatMoney, inr } from '@/lib/format';

const MODELS: { key: Model; label: string; line: string; data: string; best: string; fees: [string, string][] }[] = [
  {
    key: 'owned',
    label: 'A · Institution-owned',
    line: 'The lender licenses Vouch and runs it inside its own systems.',
    data: 'Borrower data stays inside the lender. Vouch receives fees, not files.',
    best: 'Lenders that need dedicated control or a custom integration.',
    fees: [
      ['Implementation, once', formatMoney(inr(PRICES.owned.setup.toString()))],
      ['Licence, per year', formatMoney(inr(PRICES.owned.recurringPerYear.toString()))],
      ['Per assessment', formatMoney(inr(PRICES.owned.perAssessment.toString()))],
    ],
  },
  {
    key: 'platform',
    label: 'B · Vouch platform',
    line: 'Many lenders call one Vouch API, each under its own contract.',
    data: 'Lenders send permitted requests and get signals back; every decision stays theirs.',
    best: 'Repeatable service across many lenders.',
    fees: [
      ['Onboarding, once', formatMoney(inr(PRICES.platform.setup.toString()))],
      ['Subscription, per month', formatMoney(inr(PRICES.platform.recurringPerYear.div(12).toString()))],
      ['Per assessment', formatMoney(inr(PRICES.platform.perAssessment.toString()))],
    ],
  },
];

/* ------------------------------------------------------------------ who pays whom */

const W = 760;
const H = 340;
const BORROWER = { x: 92, y: 160 };
const VOUCH = { x: 660, y: 160 };
const LENDERS: Record<Model, { x: number; y: number; on: boolean }[]> = {
  owned: [
    { x: 372, y: 160, on: true },
    { x: 372, y: 160, on: false },
    { x: 372, y: 160, on: false },
  ],
  platform: [
    { x: 372, y: 160, on: true },
    { x: 372, y: 58, on: true },
    { x: 372, y: 262, on: true },
  ],
};
const SPRING = { type: 'spring', stiffness: 120, damping: 20 } as const;

/** Something travelling along a line, forever: a data packet, a signal coming back, or money. */
function Packet({ a, b, kind, delay }: { a: { x: number; y: number }; b: { x: number; y: number }; kind: 'data' | 'signal' | 'money'; delay: number }) {
  return (
    <motion.g
      initial={{ x: a.x, y: a.y, opacity: 0 }}
      animate={{ x: [a.x, b.x], y: [a.y, b.y], opacity: [0, 1, 1, 0] }}
      transition={{ duration: 2.2, delay, repeat: Infinity, repeatDelay: 0.8, ease: 'easeInOut', times: [0, 0.15, 0.85, 1] }}
    >
      {kind === 'money' ? (
        <>
          <circle r={9} fill="#16181F" />
          <text textAnchor="middle" y={4} fontSize="11" fontWeight={600} fontFamily="IBM Plex Sans" fill="#F4F1EA">
            ₹
          </text>
        </>
      ) : (
        <circle r={4.5} fill={kind === 'data' ? '#3D56C2' : '#9AA8DC'} />
      )}
    </motion.g>
  );
}

function Flow({ model }: { model: Model }) {
  const reduce = useReducedMotion();
  const lenders = LENDERS[model];
  const owned = model === 'owned';
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label={owned ? 'Borrowers apply to one lender running Vouch inside its own systems; the lender pays Vouch fees; borrowers pay Vouch nothing' : 'Borrowers apply to three lenders; each lender sends requests to the Vouch platform, gets signals back and pays fees; borrowers pay Vouch nothing'}>
      {/* borrowers never pay Vouch */}
      <path d={`M${BORROWER.x} ${BORROWER.y + 34} C ${BORROWER.x + 40} ${H - 8}, ${VOUCH.x - 40} ${H - 8}, ${VOUCH.x} ${VOUCH.y + 40}`} fill="none" stroke="#A8352A" strokeWidth={1.4} strokeDasharray="5 6" opacity={0.55} />
      <g transform={`translate(${(BORROWER.x + VOUCH.x) / 2} ${H - 30})`}>
        <rect x={-104} y={-14} width={208} height={28} rx={14} fill="#F3DEDA" />
        <path d="M-90 -5 l10 10 M-80 -5 l-10 10" stroke="#A8352A" strokeWidth={1.8} strokeLinecap="round" />
        <text x={-70} y={4.5} fontSize="12" fontFamily="IBM Plex Sans" fontWeight={500} fill="#A8352A">
          no fees from borrowers
        </text>
      </g>

      {/* lines */}
      {lenders.map((l, i) => (
        <g key={`lines-${i}`}>
          <motion.line initial={false} animate={{ x1: BORROWER.x + 54, y1: BORROWER.y, x2: l.x - 92, y2: l.y, opacity: l.on ? 1 : 0 }} transition={SPRING} stroke="#C9C2B4" strokeWidth={1.5} />
          <motion.line initial={false} animate={{ x1: l.x + 92, y1: l.y, x2: VOUCH.x - 70, y2: VOUCH.y, opacity: l.on ? 1 : 0 }} transition={SPRING} stroke={owned ? '#16181F' : '#C9C2B4'} strokeWidth={1.5} strokeDasharray={owned ? '2 5' : undefined} />
        </g>
      ))}

      {/* moving packets */}
      {reduce
        ? null
        : lenders.map((l, i) =>
            l.on ? (
              <g key={`p-${model}-${i}`}>
                <Packet a={{ x: BORROWER.x + 54, y: BORROWER.y }} b={{ x: l.x - 92, y: l.y }} kind="data" delay={i * 0.5} />
                {owned ? null : (
                  <>
                    <Packet a={{ x: l.x + 92, y: l.y }} b={{ x: VOUCH.x - 70, y: VOUCH.y }} kind="data" delay={0.9 + i * 0.5} />
                    <Packet a={{ x: VOUCH.x - 70, y: VOUCH.y }} b={{ x: l.x + 92, y: l.y }} kind="signal" delay={1.9 + i * 0.5} />
                  </>
                )}
                <Packet a={{ x: l.x + 92, y: l.y }} b={{ x: VOUCH.x - 70, y: VOUCH.y }} kind="money" delay={owned ? 1.2 : 2.6 + i * 0.5} />
              </g>
            ) : null,
          )}

      {/* borrowers */}
      <g transform={`translate(${BORROWER.x} ${BORROWER.y})`}>
        <rect x={-54} y={-32} width={108} height={64} rx={12} fill="#FBFAF6" stroke="#DDD7CB" />
        <text textAnchor="middle" y={-2} fontSize="15" fontWeight={600} fontFamily="IBM Plex Sans" fill="#16181F">
          Borrowers
        </text>
        <text textAnchor="middle" y={14} fontSize="12" fontFamily="IBM Plex Sans" fill="#6A6D76">
          apply for loans
        </text>
      </g>

      {/* lenders */}
      {owned ? (
        <motion.rect initial={{ opacity: 0 }} animate={{ opacity: 1 }} x={372 - 116} y={160 - 80} width={232} height={160} rx={16} fill="none" stroke="#9AA8DC" strokeDasharray="5 5" />
      ) : null}
      {owned ? (
        <text x={372} y={160 - 88} textAnchor="middle" fontSize="12" fontFamily="IBM Plex Mono" fill="#24368F">
          THE LENDER’S OWN SYSTEMS
        </text>
      ) : null}
      {lenders.map((l, i) => (
        <motion.g key={`l-${i}`} initial={false} animate={{ x: l.x, y: l.y, opacity: l.on ? 1 : 0 }} transition={SPRING}>
          <rect x={-92} y={-31} width={184} height={62} rx={12} fill="#FBFAF6" stroke="#16181F" strokeWidth={1.2} />
          <text textAnchor="middle" y={-4} fontSize="15" fontWeight={600} fontFamily="IBM Plex Sans" fill="#16181F">
            {['Lender', 'Lender 2', 'Lender 3'][i]}
          </text>
          <text textAnchor="middle" y={13} fontSize="12" fontFamily="IBM Plex Sans" fill="#6A6D76">
            bank · NBFC · MFI · decides
          </text>
        </motion.g>
      ))}
      {owned ? (
        <motion.g initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <rect x={372 - 72} y={160 + 40} width={144} height={28} rx={13} fill="#24368F" />
          <text x={372} y={160 + 59} textAnchor="middle" fontSize="13" fontWeight={600} fontFamily="IBM Plex Sans" fill="#FBFAF6">
            Vouch, installed
          </text>
        </motion.g>
      ) : null}

      {/* Vouch */}
      <g transform={`translate(${VOUCH.x} ${VOUCH.y})`}>
        <rect x={-70} y={-40} width={140} height={80} rx={14} fill="#24368F" />
        <text textAnchor="middle" y={-6} fontSize="16" fontWeight={600} fontFamily="IBM Plex Sans" fill="#FBFAF6">
          Vouch
        </text>
        <text textAnchor="middle" y={12} fontSize="12" fontFamily="IBM Plex Sans" fill="#C9D0EC">
          {owned ? 'vendor: fees only' : 'platform API'}
        </text>
        <text textAnchor="middle" y={26} fontSize="12" fontFamily="IBM Plex Sans" fill="#C9D0EC">
          not a lender
        </text>
      </g>
    </svg>
  );
}

function FlowLegend() {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 font-mono text-[11px] text-ink-3">
      <span className="inline-flex items-center gap-2">
        <span className="size-2.5 rounded-full bg-neel-500" /> application or request
      </span>
      <span className="inline-flex items-center gap-2">
        <span className="size-2.5 rounded-full bg-neel-300" /> signals back to the lender
      </span>
      <span className="inline-flex items-center gap-2">
        <span className="grid size-4 place-items-center rounded-full bg-ink text-[9px] font-semibold text-paper">₹</span> fees to Vouch
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ section */

export function BusinessModel() {
  const [model, setModel] = useState<Model>('platform');
  const m = MODELS.find((x) => x.key === model)!;
  return (
    <div className="mt-10">
      <div role="radiogroup" aria-label="Deployment model" className="inline-flex rounded-[10px] bg-paper-2 p-1 shadow-[inset_0_0_0_1px_#DDD7CB]">
        {MODELS.map((x) => (
          <button
            key={x.key}
            type="button"
            role="radio"
            aria-checked={model === x.key}
            onClick={() => setModel(x.key)}
            className={`relative h-10 rounded-[8px] px-4 text-[14px] font-medium transition-colors ${model === x.key ? 'text-ink' : 'text-ink-2 hover:text-ink'}`}
          >
            {model === x.key ? <motion.span layoutId="biz-model" className="absolute inset-0 rounded-[8px] bg-surface shadow-[0_1px_2px_rgb(22_24_31/0.12)]" /> : null}
            <span className="relative">{x.label}</span>
          </button>
        ))}
      </div>

      <div className="card mt-6 grid gap-8 p-6 sm:p-8 lg:grid-cols-[1.6fr_1fr]">
        <div>
          <Flow model={model} />
          <div className="mt-3">
            <FlowLegend />
          </div>
        </div>
        <motion.div key={model} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}>
          <p className="display text-[24px] leading-tight">{m.line}</p>
          <p className="mt-3 text-[14px] leading-relaxed text-ink-2">{m.data}</p>
          <dl className="mt-6 divide-y divide-rule border-y border-rule">
            {m.fees.map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between gap-4 py-2.5">
                <dt className="text-[13.5px] text-ink-2">{k}</dt>
                <dd className="num font-mono text-[14px] font-medium">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-2 text-[11.5px] text-ink-3">Planning assumptions for modelling, not market prices or customer commitments.</p>
          <p className="mt-5 text-[13px] text-ink-2">
            <span className="font-medium text-ink">Best for: </span>
            {m.best}
          </p>
        </motion.div>
      </div>

      <p className="mt-6 max-w-[80ch] text-[13px] leading-relaxed text-ink-3">
        Vouch sells credit-assessment software to lenders; it does not lend, does not replace CIBIL or the lender’s policy, and never charges borrowers. Its
        exact role under RBI’s Digital Lending Directions, 2025 depends on each contract and needs legal review before launch. Higher prices are earned
        only after a pilot shows value beyond the lender’s current process.
      </p>
    </div>
  );
}
