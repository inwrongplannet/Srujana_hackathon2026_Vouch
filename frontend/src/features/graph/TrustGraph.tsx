import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import type { ApiCascade, ApiNode, Snapshot } from '@/api/types';
import { fmt, fmtSigned, geom, initials } from '@/lib/format';
import { edgePath, layoutDag, placeEdgeLabels } from './layout';

const STATE_FILL: Record<string, string> = {
  active: '#2E7A4D',
  restricted: '#B87A1A',
  defaulted: '#A8352A',
};
const R = 19;

function nodeState(n: ApiNode): 'active' | 'restricted' | 'defaulted' | 'cold' {
  if (n.status === 'DEFAULTED') return 'defaulted';
  if (n.status === 'RESTRICTED') return 'restricted';
  if (n.coldStart) return 'cold';
  return 'active';
}

/** Nodes worth drawing around `focus`: every trust path into it, one level of sponsors for context, and any cascade. */
export function neighbourhood(s: Snapshot, focus: string, cascade?: ApiCascade | null): string[] {
  const set = new Set<string>([focus]);
  for (const p of s.assessments[focus]?.paths ?? []) p.nodes.forEach((id) => set.add(id));
  const sponsorsOf = (id: string) => s.edges.filter((e) => e.to === id).map((e) => e.from);
  for (const id of [...set]) sponsorsOf(id).forEach((x) => set.add(x));
  if (cascade && cascade.defaulter === focus) {
    cascade.penalties.forEach((p) => set.add(p.node));
    cascade.penalties.filter((p) => p.k === 2).forEach((p) => sponsorsOf(p.node).forEach((x) => set.add(x)));
  }
  // Only nodes on the graph: anchors and registered people (who have an assessment).
  return [...set].filter((id) => s.nodes[id]?.kind === 'anchor' || !!s.assessments[id]);
}

export function TrustGraph({
  s,
  nodeIds,
  focus,
  highlight = [],
  cascade = null,
  maxHeight = 560,
  onNodeClick,
}: {
  s: Snapshot;
  nodeIds: string[];
  focus?: string;
  highlight?: string[][];
  cascade?: ApiCascade | null;
  maxHeight?: number;
  onNodeClick?: (id: string) => void;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const edges = useMemo(() => s.edges.filter((e) => nodeIds.includes(e.from) && nodeIds.includes(e.to)), [s.edges, nodeIds]);
  const lay = useMemo(() => layoutDag(nodeIds, edges), [nodeIds, edges]);
  const pos = useMemo(() => new Map(lay.nodes.map((n) => [n.id, n])), [lay]);
  const maxW = Math.max(0.01, ...edges.map((e) => geom(e.weight)));
  const labelAt = useMemo(() => {
    const twoWay = (a: string, b: string) => lay.edges.some((x) => x.from === b && x.to === a);
    const items = lay.edges
      .filter((e) => geom(edges.find((x) => x.from === e.from && x.to === e.to)!.weight) !== 0)
      .map((e) => {
        const from = pos.get(e.from)!;
        const to = pos.get(e.to)!;
        const len = Math.hypot(to.x - from.x, to.y - from.y) || 1;
        const bend = twoWay(e.from, e.to) ? (e.from < e.to ? 12 : -12) : 0;
        return {
          key: `${e.from}>${e.to}`,
          pts: [from, ...e.points.slice(1, -1), to],
          shift: { x: (-(to.y - from.y) / len) * bend * 1.6, y: ((to.x - from.x) / len) * bend * 1.6 },
        };
      });
    // A node blocks its circle and the name and R value printed under it.
    const nodes = lay.nodes.map((n) => ({ x: n.x, y: n.y + 7, w: 64, h: 2 * R + 30 }));
    return placeEdgeLabels(items, nodes);
  }, [lay, pos, edges]);

  const hot = new Set<string>();
  for (const path of highlight) for (let i = 0; i < path.length - 1; i += 1) hot.add(`${path[i]}>${path[i + 1]}`);

  const penalties = cascade && !cascade.queued ? cascade.penalties : [];
  const penalised = new Map(penalties.map((p) => [p.node, p]));
  const hop3 = cascade && !cascade.queued
    ? [...new Set(penalties.filter((p) => p.k === 2).flatMap((p) => s.edges.filter((e) => e.to === p.node).map((e) => e.from)))].filter((id) => !penalised.has(id) && pos.has(id))
    : [];

  return (
    <div className="relative w-full">
      <svg viewBox={`0 0 ${lay.width} ${lay.height}`} className="mx-auto block h-auto w-full" style={{ maxHeight }} role="img" aria-label="Directed trust graph">
        <defs>
          {[
            ['arr', '#B9B2A3'],
            ['arr-hot', '#3D56C2'],
            ['arr-bad', '#A8352A'],
          ].map(([id, c]) => (
            <marker key={id} id={id} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10 z" fill={c} />
            </marker>
          ))}
          <pattern id="tg-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
            <rect width="6" height="6" fill="#ECEEF7" />
            <rect width="1.4" height="6" fill="#C9D0EC" />
          </pattern>
          <style>{'@keyframes tgflow{to{stroke-dashoffset:-22}} .tg-flow{animation:tgflow 1.1s linear infinite}'}</style>
        </defs>

        {/* edges */}
        {lay.edges.map((e) => {
          const from = pos.get(e.from)!;
          const to = pos.get(e.to)!;
          const data = edges.find((x) => x.from === e.from && x.to === e.to)!;
          const w = geom(data.weight);
          const isHot = hot.has(`${e.from}>${e.to}`);
          const intoDefault = s.nodes[e.to]!.status === 'DEFAULTED';
          const twoWay = lay.edges.some((x) => x.from === e.to && x.to === e.from);
          const bend = twoWay ? (e.from < e.to ? 12 : -12) : 0;
          const d = edgePath(e.points, from, to, R + 2, bend);
          const dim = hover && hover !== e.from && hover !== e.to;
          return (
            <g key={`${e.from}>${e.to}`} opacity={dim ? 0.25 : 1} style={{ transition: 'opacity 160ms' }}>
              <path
                d={d}
                fill="none"
                stroke={isHot ? '#3D56C2' : intoDefault ? '#D9A9A2' : '#C9C2B4'}
                strokeWidth={1.1 + 2.4 * (w / maxW)}
                strokeLinecap="round"
                markerEnd={`url(#${isHot ? 'arr-hot' : intoDefault ? 'arr-bad' : 'arr'})`}
              />
              {isHot ? <path d={d} fill="none" stroke="#FBFAF6" strokeWidth={1.3} strokeDasharray="3 8" className="tg-flow" /> : null}
            </g>
          );
        })}

        {/* edge weights, drawn above every line so no edge crosses a label */}
        {lay.edges.map((e) => {
          const at = labelAt.get(`${e.from}>${e.to}`);
          if (!at) return null;
          const data = edges.find((x) => x.from === e.from && x.to === e.to)!;
          const isHot = hot.has(`${e.from}>${e.to}`);
          const dim = hover && hover !== e.from && hover !== e.to;
          return (
            <g key={`w-${e.from}>${e.to}`} transform={`translate(${at.x} ${at.y})`} opacity={dim ? 0.25 : 1} style={{ transition: 'opacity 160ms' }}>
              <rect x={-17} y={-8.5} width={34} height={17} rx={4} fill="#F4F1EA" stroke={isHot ? '#C9D0EC' : '#E3DDCF'} />
              <text textAnchor="middle" y={3.8} fontSize="10.5" fontFamily="IBM Plex Mono" fill={isHot ? '#24368F' : '#6A6D76'}>
                {fmt(data.weight)}
              </text>
            </g>
          );
        })}

        {/* hop-3 isolation markers */}
        {hop3.map((id) => {
          const p = pos.get(id)!;
          return (
            <motion.g key={`h3-${cascade!.id}-${id}`} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 1.45, duration: 0.4 }} style={{ originX: `${p.x}px`, originY: `${p.y}px` }}>
              <circle cx={p.x} cy={p.y} r={R + 10} fill="none" stroke="#3D56C2" strokeWidth={1.4} strokeDasharray="4 4" />
              <g transform={`translate(${p.x + R + 14} ${p.y - R - 4})`}>
                <rect x={0} y={-10} width={92} height={20} rx={10} fill="#ECEEF7" stroke="#C9D0EC" />
                <text x={46} y={4} textAnchor="middle" fontSize="10.5" fontFamily="IBM Plex Sans" fontWeight={500} fill="#24368F">
                  hop 3 · untouched
                </text>
              </g>
            </motion.g>
          );
        })}

        {/* nodes */}
        {lay.nodes.map(({ id, x, y }) => {
          const n = s.nodes[id]!;
          const st = nodeState(n);
          const pen = penalised.get(id);
          const isFocus = id === focus;
          const dim = hover && hover !== id && !edges.some((e) => (e.from === hover && e.to === id) || (e.to === hover && e.from === id));
          return (
            <motion.g
              key={id}
              initial={false}
              animate={{ x, y, opacity: dim ? 0.35 : 1 }}
              transition={{ type: 'spring', duration: 0.6, bounce: 0.1 }}
              onMouseEnter={() => setHover(id)}
              onMouseLeave={() => setHover(null)}
              onClick={() => onNodeClick?.(id)}
              style={{ cursor: onNodeClick ? 'pointer' : 'default' }}
            >
              {pen ? (
                <motion.circle
                  key={`rip-${cascade!.id}`}
                  r={R}
                  fill="none"
                  stroke={pen.k === 0 ? '#A8352A' : '#B87A1A'}
                  strokeWidth={2}
                  initial={{ r: R, opacity: 0.9 }}
                  animate={{ r: R + 30, opacity: 0 }}
                  transition={{ delay: pen.k * 0.45, duration: 1.1, repeat: 2, repeatDelay: 0.6 }}
                />
              ) : null}
              {isFocus ? <circle r={R + 7} fill="none" stroke="#3D56C2" strokeWidth={1.5} strokeDasharray="3 3" /> : null}
              {n.kind === 'anchor' ? (
                <g>
                  <rect x={-20} y={-20} width={40} height={40} rx={10} fill="#24368F" />
                  <path d="M-9 -3 0 -9 9 -3 M-6 -2v9 M-2 -2v9 M2 -2v9 M6 -2v9 M-10 9h20" stroke="#FBFAF6" strokeWidth={1.6} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                </g>
              ) : st === 'cold' ? (
                <g>
                  <circle r={R} fill="url(#tg-hatch)" stroke="#7C7F87" strokeWidth={1.6} strokeDasharray="4 3" />
                  <text textAnchor="middle" y={4.5} fontSize="12.5" fontWeight={600} fontFamily="IBM Plex Sans" fill="#16181F">
                    {initials(n.name)}
                  </text>
                </g>
              ) : (
                <g>
                  <circle r={R} fill={STATE_FILL[st]} />
                  <text textAnchor="middle" y={4.5} fontSize="12.5" fontWeight={600} fontFamily="IBM Plex Sans" fill="#FBFAF6">
                    {initials(n.name)}
                  </text>
                </g>
              )}
              <text textAnchor="middle" y={R + 16} fontSize="12" fontWeight={isFocus ? 600 : 500} fontFamily="IBM Plex Sans" fill="#16181F">
                {n.kind === 'anchor' ? n.name.split(' ')[0] : n.name.split(' ')[0]}
              </text>
              <text textAnchor="middle" y={R + 29} fontSize="10" fontFamily="IBM Plex Mono" fill="#6A6D76">
                {n.kind === 'anchor' ? 'anchor' : `R ${fmt(n.R)}`}
              </text>
              {pen ? (
                <motion.g key={`chip-${cascade!.id}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: pen.k * 0.45 + 0.15, duration: 0.35 }}>
                  <rect x={-24} y={-R - 26} width={48} height={18} rx={9} fill={pen.k === 0 ? '#A8352A' : '#F5EAD3'} />
                  <text textAnchor="middle" y={-R - 13} fontSize="11" fontFamily="IBM Plex Mono" fontWeight={500} fill={pen.k === 0 ? '#FBFAF6' : '#8A560A'}>
                    {fmtSigned(`-${pen.delta}`)}
                  </text>
                </motion.g>
              ) : null}
            </motion.g>
          );
        })}

        {/* hover card */}
        {hover && pos.get(hover) ? <HoverCard n={s.nodes[hover]!} x={pos.get(hover)!.x} y={pos.get(hover)!.y} w={lay.width} /> : null}
      </svg>
    </div>
  );
}

function HoverCard({ n, x, y, w }: { n: ApiNode; x: number; y: number; w: number }) {
  const left = x + 170 > w ? x - 186 : x + 30;
  const rows: [string, string][] =
    n.kind === 'anchor'
      ? [
          ['Type', n.role],
          ['R (assigned)', fmt(n.R)],
        ]
      : [
          ['Credibility R', fmt(n.R)],
          ['Capacity C', fmt(n.capacity)],
          ['Status', n.coldStart ? 'cold start' : n.status.toLowerCase()],
        ];
  return (
    <g transform={`translate(${left} ${y - 40})`} pointerEvents="none">
      <rect width={160} height={34 + rows.length * 17} rx={8} fill="#FBFAF6" stroke="#DDD7CB" filter="drop-shadow(0 6px 14px rgb(19 28 70 / 0.18))" />
      <text x={12} y={20} fontSize="12" fontWeight={600} fontFamily="IBM Plex Sans" fill="#16181F">
        {n.name}
      </text>
      {rows.map(([k, v], i) => (
        <g key={k}>
          <text x={12} y={40 + i * 17} fontSize="10.5" fontFamily="IBM Plex Sans" fill="#6A6D76">
            {k}
          </text>
          <text x={148} y={40 + i * 17} textAnchor="end" fontSize="10.5" fontFamily="IBM Plex Mono" fill="#16181F">
            {v}
          </text>
        </g>
      ))}
    </g>
  );
}
