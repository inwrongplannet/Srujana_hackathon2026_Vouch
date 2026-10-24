import { graphlib, layout } from '@dagrejs/dagre';

export interface LaidNode {
  id: string;
  x: number;
  y: number;
}

export interface LaidEdge {
  from: string;
  to: string;
  points: { x: number; y: number }[];
}

/**
 * Layered, direction-aware layout (dagre): anchors on top, trust flowing down. A force layout
 * would ignore edge direction, which is the whole point of the graph.
 */
export function layoutDag(
  nodes: string[],
  edges: { from: string; to: string }[],
  opts: { nodeSize?: number; nodesep?: number; ranksep?: number } = {},
): { nodes: LaidNode[]; edges: LaidEdge[]; width: number; height: number } {
  const size = opts.nodeSize ?? 44;
  const g = new graphlib.Graph({ multigraph: false });
  g.setGraph({ rankdir: 'TB', nodesep: opts.nodesep ?? 56, ranksep: opts.ranksep ?? 78, marginx: 48, marginy: 34, ranker: 'network-simplex' });
  g.setDefaultEdgeLabel(() => ({}));
  for (const id of nodes) g.setNode(id, { width: size + 40, height: size + 18 });
  const keep = new Set(nodes);
  const laidEdges = edges.filter((e) => keep.has(e.from) && keep.has(e.to) && e.from !== e.to);
  for (const e of laidEdges) g.setEdge(e.from, e.to);
  layout(g);
  const graph = g.graph();
  return {
    nodes: nodes.map((id) => ({ id, x: g.node(id).x, y: g.node(id).y })),
    edges: laidEdges.map((e) => ({ ...e, points: g.edge({ v: e.from, w: e.to }).points ?? [] })),
    width: graph.width ?? 600,
    height: graph.height ?? 400,
  };
}

/**
 * Smooth path through dagre's control points, trimmed so arrows stop at the node rim. Downward
 * edges leave from below the node's label; `bend` pushes a two-way pair apart.
 */
export function edgePath(
  points: { x: number; y: number }[],
  from: { x: number; y: number },
  to: { x: number; y: number },
  rim = 22,
  bend = 0,
): string {
  let pts = [from, ...points.slice(1, -1), to];
  if (bend) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const len = Math.hypot(dx, dy) || 1;
    const off = { x: (-dy / len) * bend, y: (dx / len) * bend };
    pts = pts.map((p, i) => (i === 0 || i === pts.length - 1 ? p : { x: p.x + off.x, y: p.y + off.y }));
    if (pts.length === 2) pts = [from, { x: (from.x + to.x) / 2 + off.x * 2, y: (from.y + to.y) / 2 + off.y * 2 }, to];
  }
  const LABEL_DROP = rim + 34;
  if (pts[1]!.y > from.y + LABEL_DROP + 8) pts[0] = { x: from.x, y: from.y + LABEL_DROP - (rim - 4) };
  // Upward edges arrive under the target's label instead of through it.
  const last = pts.length - 1;
  if (pts[last - 1]!.y > to.y + LABEL_DROP + 8) pts[last] = { x: to.x, y: to.y + LABEL_DROP - (rim + 4) };
  const trim = (a: { x: number; y: number }, b: { x: number; y: number }, d: number) => {
    const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    return { x: b.x - ((b.x - a.x) / len) * d, y: b.y - ((b.y - a.y) / len) * d };
  };
  const start = trim(pts[1]!, pts[0]!, rim - 4);
  const end = trim(pts[pts.length - 2]!, pts[pts.length - 1]!, rim + 4);
  const all = [start, ...pts.slice(1, -1), end];
  if (all.length === 2) return `M${start.x} ${start.y} L${end.x} ${end.y}`;
  let d = `M${all[0]!.x} ${all[0]!.y}`;
  for (let i = 1; i < all.length - 1; i += 1) {
    const mid = { x: (all[i]!.x + all[i + 1]!.x) / 2, y: (all[i]!.y + all[i + 1]!.y) / 2 };
    d += ` Q${all[i]!.x} ${all[i]!.y} ${mid.x} ${mid.y}`;
  }
  d += ` L${end.x} ${end.y}`;
  return d;
}
