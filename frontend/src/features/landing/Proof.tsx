/**
 * "Does it work?": three tests the reader can run, each animated from our dataset's own results.
 * 01 replays real Prosper loans band by band, 02 splits shocked borrowers the bureau cannot tell
 * apart, 03 lets the reader turn vouch strength up. Dots are people (or groups of ten); outcomes
 * are revealed in a fixed shuffled order so the counts end exactly on the reported rates.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { animate, LayoutGroup, motion, useInView, useReducedMotion } from 'motion/react';
import { IconArrowUpRight, IconReset } from '@/components/icons';
import { DOSE, REAL, SHOCK, dotsFor, gapPoints, pct1 } from './proofData';

/** Deterministic shuffle, so every visit (and every screenshot) reveals the same order. */
function shuffled(n: number, seed: number): number[] {
  let s = seed >>> 0;
  const rnd = () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 2 ** 32;
  const a = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i -= 1) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j]!, a[i]!];
  }
  return a;
}

/** 0 to 1 over `seconds` each time `run` changes while `on`; instant when motion is reduced. */
function useProgress(seconds: number, run: unknown, on: boolean) {
  const reduce = useReducedMotion();
  const [p, setP] = useState(0);
  useEffect(() => {
    if (!on) return;
    const c = animate(0, 1, { duration: reduce ? 0 : seconds, ease: 'linear', onUpdate: setP });
    return () => c.stop();
  }, [run, on, reduce, seconds]);
  return p;
}

type DotState = 'pending' | 'repaid' | 'defaulted';
const DOT: Record<DotState, string> = {
  pending: 'border border-rule-2 bg-transparent',
  repaid: 'bg-neel-700',
  defaulted: 'bg-defaulted',
};

/** Who defaults (the first `defaults` of one shuffle) and when each dot resolves (another shuffle). */
function useOutcomes(total: number, defaults: number, seed: number) {
  return useMemo(() => {
    const bad = new Set(shuffled(total, seed).slice(0, defaults));
    const when = new Array<number>(total);
    shuffled(total, seed * 7 + 3).forEach((dot, rank) => (when[dot] = rank));
    return { bad, when };
  }, [total, defaults, seed]);
}

function stateAt(i: number, p: number, total: number, o: { bad: Set<number>; when: number[] }): DotState {
  if (o.when[i]! >= Math.round(p * total)) return 'pending';
  return o.bad.has(i) ? 'defaulted' : 'repaid';
}

function Legend() {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1 font-mono text-[11px] text-ink-3">
      <span className="inline-flex items-center gap-2">
        <span className="size-2.5 rounded-full bg-neel-700" />
        repaid
      </span>
      <span className="inline-flex items-center gap-2">
        <span className="size-2.5 rounded-full bg-defaulted" />
        defaulted
      </span>
      <span className="inline-flex items-center gap-2">
        <span className="size-2.5 rounded-full border border-rule-2" />
        outcome not in yet
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ 01: real loans */

function Hundred({ title, n, rate, p, seed }: { title: string; n: number; rate: string; p: number; seed: number }) {
  const k = dotsFor(rate, 100);
  const o = useOutcomes(100, k, seed);
  const states = Array.from({ length: 100 }, (_, i) => stateAt(i, p, 100, o));
  const shownBad = states.filter((x) => x === 'defaulted').length;
  const done = p >= 1;
  // Once every outcome is in, the defaults slide together so the two groups can be counted.
  const ids = Array.from({ length: 100 }, (_, i) => i);
  const order = done ? [...ids.filter((i) => !o.bad.has(i)), ...ids.filter((i) => o.bad.has(i))] : ids;
  return (
    <div className="max-w-[340px]">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-[14.5px] font-medium">{title}</p>
        <p className="font-mono text-[11.5px] text-ink-3">{n.toLocaleString('en-IN')} loans</p>
      </div>
      <div className="mt-3 grid grid-cols-10 gap-1.5" role="img" aria-label={`${title}: ${pct1(rate)} defaulted, of ${n} loans`}>
        {order.map((i) => (
          <motion.span
            key={i}
            layout
            transition={{ layout: { type: 'spring', stiffness: 260, damping: 26, delay: 0.1 } }}
            className={`aspect-square rounded-full transition-colors duration-150 ${DOT[states[i]!]}`}
          />
        ))}
      </div>
      <p className="mt-3 flex items-baseline gap-2">
        <span className={`display num text-[34px] leading-none ${done ? 'text-defaulted' : 'text-ink'}`}>{done ? pct1(rate) : shownBad}</span>
        <span className="text-[13px] text-ink-3">{done ? 'defaulted' : 'of 100 defaulted so far'}</span>
      </p>
    </div>
  );
}

function RealLoans({ on }: { on: boolean }) {
  // Opens on borrowers whose score had already fallen: the case the bureau gets wrong.
  const [band, setBand] = useState(REAL.cells.length - 1);
  const [run, setRun] = useState(0);
  const cell = REAL.cells[band]!;
  const p = useProgress(1.2, `${band}-${run}`, on);
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2" role="radiogroup" aria-label="Credit score band">
        <span className="eyebrow mr-1">Credit score</span>
        {REAL.cells.map((c, i) => (
          <button
            key={c.key}
            type="button"
            role="radio"
            aria-checked={band === i}
            onClick={() => setBand(i)}
            className={`h-8 rounded-full border px-3 text-[13px] transition-colors ${band === i ? 'border-ink bg-ink text-paper' : 'border-rule-2 bg-surface text-ink-2 hover:border-ink-3'}`}
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="mt-8 grid gap-10 sm:grid-cols-2 lg:gap-16">
        <Hundred title="Endorsed by friends" n={cell.endorsed.n} rate={cell.endorsed.rate} p={p} seed={11 + band} />
        <Hundred title="Same score, no endorsement" n={cell.plain.n} rate={cell.plain.rate} p={p} seed={29 + band} />
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-rule pt-5">
        <motion.p key={`${band}-${p >= 1}`} initial={{ opacity: 0 }} animate={{ opacity: p >= 1 ? 1 : 0.35 }} className="max-w-[60ch] text-[15px] text-ink-2">
          <span className="font-medium text-ink">{gapPoints(cell.plain.rate, cell.endorsed.rate)} points less default</span> with an endorsement, at the same
          credit score. Across all {REAL.resolved.toLocaleString('en-IN')} resolved loans, band for band: {gapPoints(REAL.bandAdjustedGap, '0')} points.
        </motion.p>
        <Replay onClick={() => setRun((r) => r + 1)} />
      </div>
      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
        {REAL.links.map((l) => (
          <a
            key={l.url}
            href={l.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[12.5px] text-ink-2 underline decoration-rule-2 underline-offset-2 hover:text-ink"
          >
            {l.label}
            <IconArrowUpRight size={12} />
          </a>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ 02: after a shock */

const STAGES = [
  'A shock hits: illness, a lost job, a flood.',
  'Every one of them loses 50+ bureau points. To the bureau they look the same.',
  'The vouch sees three different groups.',
  'Twelve months later.',
];
const STAGE_MS = [800, 1300, 1100];

function AfterShock({ on }: { on: boolean }) {
  const reduce = useReducedMotion();
  const [stage, setStage] = useState(0);
  const [run, setRun] = useState(0);
  const groups = SHOCK.groups.map((g) => ({ ...g, dots: Math.round(g.n / SHOCK.perDot) }));
  const total = groups.reduce((a, g) => a + g.dots, 0);
  const starts = groups.map((_, i) => groups.slice(0, i).reduce((a, g) => a + g.dots, 0));
  // The cloud mixes the groups; dot ids stay fixed so each dot can travel to its group.
  const cloud = useMemo(() => shuffled(total, 5), [total]);
  const p = useProgress(1.1, run, on && stage === 3);

  useEffect(() => {
    if (!on) return;
    if (reduce) {
      setStage(3);
      return;
    }
    setStage(0);
    const timers = STAGE_MS.reduce<number[]>((acc, _, i) => {
      const at = STAGE_MS.slice(0, i + 1).reduce((a, b) => a + b, 0);
      return [...acc, window.setTimeout(() => setStage(i + 1), at)];
    }, []);
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [on, run, reduce]);

  const outcomes = groups.map((g, gi) => ({ g, o: shuffled(g.dots, 41 + gi), k: dotsFor(g.rate, g.dots), when: shuffled(g.dots, 97 + gi) }));
  const dotState = (gi: number, local: number): DotState => {
    if (stage < 3) return 'pending';
    const { o, k, when } = outcomes[gi]!;
    if (when.indexOf(local) >= Math.round(p * groups[gi]!.dots)) return 'pending';
    return o.indexOf(local) < k ? 'defaulted' : 'repaid';
  };
  // After the reveal each group's defaults slide to the end, so the three counts can be compared.
  const groupOrder = (gi: number, done: boolean) => {
    const ids = Array.from({ length: groups[gi]!.dots }, (_, i) => i);
    if (!done) return ids;
    const { o, k } = outcomes[gi]!;
    return [...ids.filter((i) => o.indexOf(i) >= k), ...ids.filter((i) => o.indexOf(i) < k)];
  };
  const tone = (gi: number, local: number) => {
    const st = dotState(gi, local);
    if (st !== 'pending') return DOT[st];
    return stage >= 1 ? 'bg-restricted/70' : 'bg-ink-3/50';
  };

  const dot = (id: number) => {
    const gi = starts.filter((s) => id >= s).length - 1;
    const local = id - starts[gi]!;
    return (
      <motion.span
        key={id}
        layoutId={`shock-${id}`}
        layout
        transition={{ type: 'spring', stiffness: 300, damping: 28 }}
        animate={stage === 1 && !reduce ? { y: [0, 3, -2, 0] } : { y: 0 }}
        className={`size-[12px] rounded-full transition-colors duration-200 ${tone(gi, local)}`}
      />
    );
  };

  return (
    <div>
      <ol className="flex flex-wrap gap-x-6 gap-y-2" aria-label="Steps">
        {STAGES.map((s, i) => (
          <li key={s} className={`flex items-center gap-2 text-[12.5px] transition-colors ${i <= stage ? 'text-ink' : 'text-ink-3'}`}>
            <span className={`grid size-5 place-items-center rounded-full font-mono text-[10.5px] ${i <= stage ? 'bg-ink text-paper' : 'border border-rule-2'}`}>{i + 1}</span>
            <span className="hidden md:inline">{['Shock', 'Bureau falls', 'Vouch splits', 'Outcome'][i]}</span>
          </li>
        ))}
      </ol>
      <motion.p key={stage} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="display mt-5 min-h-[2.4em] text-[clamp(20px,2.4vw,28px)] leading-tight">
        {STAGES[stage]}
      </motion.p>

      <LayoutGroup id={`shock-${run}`}>
        {stage < 2 ? (
          <div className="mt-6">
            <div className="flex max-w-[760px] flex-wrap gap-[6px]" role="img" aria-label={`${SHOCK.borrowers} shocked borrowers, one dot for ten`}>
              {cloud.map((id) => dot(id))}
            </div>
            <p className={`mt-4 font-mono text-[12px] transition-colors ${stage >= 1 ? 'text-restricted-ink' : 'text-ink-3'}`}>
              {stage >= 1 ? `Bureau: −50 points or worse for all ${SHOCK.borrowers.toLocaleString('en-IN')}` : `${SHOCK.borrowers.toLocaleString('en-IN')} borrowers · one dot = ${SHOCK.perDot}`}
            </p>
          </div>
        ) : (
          <div className="mt-6 grid gap-8 md:grid-cols-3">
            {groups.map((g, gi) => {
              const done = stage === 3 && p >= 1;
              return (
                <div key={g.key}>
                  <p className="text-[14.5px] font-medium">{g.label}</p>
                  <p className="text-[12px] text-ink-3">
                    {g.note} · {g.n.toLocaleString('en-IN')} borrowers
                  </p>
                  <div className="mt-3 flex flex-wrap gap-[6px]" role="img" aria-label={`${g.label}: ${pct1(g.rate)} defaulted`}>
                    {groupOrder(gi, done).map((local) => dot(starts[gi]! + local))}
                  </div>
                  <p className="mt-3 flex items-baseline gap-2">
                    <span className={`display num text-[34px] leading-none transition-colors ${done ? 'text-defaulted' : 'text-ink-3'}`}>{done ? pct1(g.rate) : '—'}</span>
                    <span className="text-[13px] text-ink-3">{done ? 'defaulted' : 'waiting'}</span>
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </LayoutGroup>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 border-t border-rule pt-5">
        <p className="max-w-[64ch] text-[15px] text-ink-2">
          <span className="font-medium text-ink">{SHOCK.stratifiedGap} points less default</span> when the vouch held, comparing borrowers with the same
          score before the shock and the same severity (95% interval {SHOCK.ci[0]} to {SHOCK.ci[1]}).
        </p>
        <Replay onClick={() => setRun((r) => r + 1)} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ 03: stronger vouch */

function Stronger({ on }: { on: boolean }) {
  const [level, setLevel] = useState(0);
  const touched = useRef(false);
  const reduce = useReducedMotion();
  // Walks up the levels once on first view, so the effect is visible before anyone drags.
  useEffect(() => {
    if (!on || touched.current || reduce) return;
    const timers = [1, 2, 3, 4].map((l) => window.setTimeout(() => !touched.current && setLevel(l), 350 * l));
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [on, reduce]);
  const d = DOSE[level]!;
  const k = dotsFor(d.rate, 100);
  const set = (l: number) => {
    touched.current = true;
    setLevel(l);
  };
  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:items-center">
      <div>
        <label htmlFor="dose" className="eyebrow">
          How strong the vouch is after the shock
        </label>
        <p className="display mt-2 text-[28px] leading-tight">
          {d.label}
          {d.floor !== null ? <span className="ml-2 text-[15px] text-ink-3">Vouch Score {d.floor}+</span> : null}
        </p>
        <input
          id="dose"
          type="range"
          min={0}
          max={DOSE.length - 1}
          step={1}
          value={level}
          onChange={(e) => set(Number(e.target.value))}
          className="vt-range mt-6 w-full"
          style={{ ['--fill' as string]: `${(level / (DOSE.length - 1)) * 100}%` }}
          aria-valuetext={`${d.label}: ${pct1(d.rate)} defaulted`}
        />
        <div className="mt-6 flex h-32 items-end gap-2" aria-hidden>
          {DOSE.map((x, i) => (
            <button key={x.label} type="button" tabIndex={-1} onClick={() => set(i)} className="group flex h-full flex-1 flex-col justify-end">
              <motion.span
                className={`w-full rounded-t-[4px] ${i === level ? 'bg-defaulted' : 'bg-defaulted/25 group-hover:bg-defaulted/45'}`}
                animate={{ height: `${dotsFor(x.rate, 100) * 2}%` }}
              />
              <span className={`mt-1.5 text-center font-mono text-[10.5px] ${i === level ? 'text-ink' : 'text-ink-3'}`}>{pct1(x.rate)}</span>
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="grid max-w-[360px] grid-cols-10 gap-1.5" role="img" aria-label={`${d.label}: ${pct1(d.rate)} defaulted`}>
          {Array.from({ length: 100 }, (_, i) => (
            <span key={i} className={`aspect-square rounded-full transition-colors duration-200 ${i >= 100 - k ? 'bg-defaulted' : 'bg-neel-700'}`} />
          ))}
        </div>
        <p className="mt-4 flex items-baseline gap-2">
          <span className="display num text-[44px] leading-none text-defaulted">{pct1(d.rate)}</span>
          <span className="text-[14px] text-ink-3">of these shocked borrowers defaulted</span>
        </p>
        <p className="mt-2 text-[13.5px] text-ink-2">The stronger the vouch that survives the shock, the fewer defaults: every step down, none up.</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ frame */

function Replay({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex h-9 items-center gap-2 rounded-[8px] border border-rule-2 bg-surface px-3.5 text-[13px] font-medium text-ink-2 hover:border-ink-3 hover:text-ink"
    >
      <IconReset size={15} /> Replay
    </button>
  );
}

const TESTS = [
  { key: 'real', n: '01', label: 'Real loans', tag: 'Real data · Prosper, US', source: REAL.source },
  { key: 'shock', n: '02', label: 'After a shock', tag: 'Simulated India', source: SHOCK.source },
  { key: 'dose', n: '03', label: 'Stronger vouch, safer loan', tag: 'Simulated India', source: SHOCK.source },
] as const;

export function Proof() {
  const [tab, setTab] = useState<(typeof TESTS)[number]['key']>('real');
  const stage = useRef<HTMLDivElement>(null);
  const seen = useInView(stage, { once: true, margin: '0px 0px -20% 0px' });
  const t = TESTS.find((x) => x.key === tab)!;
  return (
    <div className="mt-10">
      <div role="tablist" aria-label="Tests" className="grid grid-cols-3 border-b border-rule">
        {TESTS.map((x) => (
          <button
            key={x.key}
            type="button"
            role="tab"
            aria-selected={tab === x.key}
            onClick={() => setTab(x.key)}
            className={`relative pr-3 pb-4 text-left transition-colors ${tab === x.key ? 'text-ink' : 'text-ink-3 hover:text-ink-2'}`}
          >
            <span className="block font-mono text-[11px] text-neel-700">
              {x.n} · {x.tag}
            </span>
            <span className="display mt-1 block text-[clamp(16px,2vw,24px)] leading-tight">{x.label}</span>
            {tab === x.key ? <motion.span layoutId="proof-tab" className="absolute inset-x-0 -bottom-px h-[2px] bg-ink" /> : null}
          </button>
        ))}
      </div>

      <div ref={stage} role="tabpanel" className="card mt-8 p-6 sm:p-8">
        {tab === 'real' ? <RealLoans on={seen} /> : tab === 'shock' ? <AfterShock on={seen} /> : <Stronger on={seen} />}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <Legend />
          <p className="font-mono text-[11px] text-ink-3">{t.source}</p>
        </div>
      </div>

      <p className="mt-6 max-w-[80ch] text-[13px] leading-relaxed text-ink-3">
        What this shows: a vouch carries information the bureau score misses, most of all after a shock. What it does not show: that the effect is causal
        in the real world, or its size for Indian borrowers. Prosper endorsements carried no stake, so a staked vouch should do at least as well; across
        all applicants it adds little to a conventional model (AUC +0.003), because its value sits in the cases where the bureau is caught out.
      </p>
    </div>
  );
}
