import { useEffect, useRef, useState } from 'react';
import { motion } from 'motion/react';
import type { ApiAssessment } from '@/api/types';
import { geom } from '@/lib/format';

const W = 300;
const H = 210;
const PAD = { l: 34, r: 12, t: 14, b: 30 };

/**
 * mu on x, sigma2 on y. The point should travel down (more certain) and right (more capacity).
 * Previous positions stay as a faint trail so the journey is visible.
 */
export function UncertaintyPlot({ a }: { a: ApiAssessment }) {
  const mu = geom(a.mu);
  const s2 = geom(a.sigma2);
  const xMax = Math.max(4, Math.ceil(mu + 0.5));
  const x = (v: number) => PAD.l + (Math.max(0, v) / xMax) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - v) * (H - PAD.t - PAD.b);

  const [trail, setTrail] = useState<{ mu: number; s2: number }[]>([]);
  const last = useRef<{ mu: number; s2: number } | null>(null);
  useEffect(() => {
    const prev = last.current;
    if (prev && (prev.mu !== mu || prev.s2 !== s2)) setTrail((t) => [...t, prev].slice(-6));
    last.current = { mu, s2 };
  }, [mu, s2]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={`Expected capacity ${mu.toFixed(2)} against uncertainty ${s2.toFixed(2)}`}>
      <defs>
        <pattern id="plot-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
          <rect width="6" height="6" fill="#ECEEF7" />
          <rect width="1.4" height="6" fill="#C9D0EC" />
        </pattern>
      </defs>
      <rect x={PAD.l} y={y(1)} width={W - PAD.l - PAD.r} height={y(0.5) - y(1)} fill="url(#plot-hatch)" />
      <text x={W - PAD.r - 6} y={y(1) + 14} textAnchor="end" fontSize="10.5" fill="#131C46" fontFamily="IBM Plex Sans">
        thin file
      </text>
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="#DDD7CB" strokeDasharray={t === 0 ? undefined : '2 4'} />
          <text x={PAD.l - 6} y={y(t) + 3.5} textAnchor="end" fontSize="10" fill="#6A6D76" fontFamily="IBM Plex Mono">
            {t === 0 ? '0' : t.toFixed(2).replace(/^0/, '')}
          </text>
        </g>
      ))}
      <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={y(0)} stroke="#C9C2B4" />
      {Array.from({ length: xMax + 1 }, (_, i) => (
        <text key={i} x={x(i)} y={H - 12} textAnchor="middle" fontSize="10" fill="#6A6D76" fontFamily="IBM Plex Mono">
          {i}
        </text>
      ))}
      <text x={W - PAD.r} y={H - 1} textAnchor="end" fontSize="10.5" fill="#6A6D76" fontFamily="IBM Plex Sans">
        expected capacity μ →
      </text>
      <text x={PAD.l + 6} y={y(0.5) + 14} fontSize="10.5" fill="#6A6D76" fontFamily="IBM Plex Sans">
        ↑ uncertainty σ²
      </text>

      {trail.map((p, i) => (
        <circle key={i} cx={x(p.mu)} cy={y(p.s2)} r={3} fill="#9AA8DC" opacity={0.25 + (i / trail.length) * 0.5} />
      ))}
      {trail.length > 0 ? (
        <motion.path
          d={[...trail, { mu, s2 }].map((p, i) => `${i ? 'L' : 'M'}${x(p.mu)} ${y(p.s2)}`).join(' ')}
          fill="none"
          stroke="#9AA8DC"
          strokeDasharray="3 4"
          initial={false}
        />
      ) : null}
      <motion.g initial={false} animate={{ x: x(mu), y: y(s2) }} transition={{ type: 'spring', duration: 0.8, bounce: 0.15 }}>
        <line x1={0} y1={0} x2={0} y2={y(0) - y(s2)} stroke="#3D56C2" strokeDasharray="2 3" />
        <circle r={9} fill="#24368F" opacity={0.12} />
        <circle r={5.5} fill="#24368F" stroke="#FBFAF6" strokeWidth={2} />
      </motion.g>
    </svg>
  );
}
