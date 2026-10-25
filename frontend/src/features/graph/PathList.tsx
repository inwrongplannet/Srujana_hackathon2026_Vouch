import { Fragment } from 'react';
import type { ApiAssessment, Snapshot } from '@/api/types';
import { fmt, geom } from '@/lib/format';
import { IconAnchor } from '@/components/icons';

/**
 * "Why this score", one ledger line per trust path. Hovering a row highlights the path in the
 * graph when `onHover` is wired.
 */
export function PathList({
  a,
  s,
  self = false,
  onHover,
  active,
}: {
  a: ApiAssessment;
  s: Snapshot;
  self?: boolean;
  onHover?: (i: number | null) => void;
  active?: number | null;
}) {
  const total = geom(a.rGraph);
  const paths = a.paths.filter((p) => geom(p.trust) > 0);
  if (paths.length === 0) {
    return <p className="py-4 text-[14px] text-ink-3">No trust path reaches this node from an institutional anchor yet.</p>;
  }
  return (
    <table className="w-full text-[13.5px]">
      <thead>
        <tr className="border-b border-ink text-left">
          <th className="eyebrow pb-2 font-medium">Path from an anchor</th>
          <th className="eyebrow w-16 pb-2 pl-4 text-right font-medium">Hops</th>
          <th className="eyebrow w-24 pb-2 pl-4 text-right font-medium">Trust</th>
        </tr>
      </thead>
      <tbody>
        {paths.map((p, i) => {
          const share = total > 0 ? (geom(p.trust) / total) * 100 : 0;
          return (
            <tr
              key={p.nodes.join('>')}
              onMouseEnter={() => onHover?.(i)}
              onMouseLeave={() => onHover?.(null)}
              className={`border-b border-rule transition-colors ${active === i ? 'bg-neel-50' : onHover ? 'hover:bg-paper' : ''}`}
            >
              <td className="py-3 pr-3">
                <span className="flex flex-wrap items-center gap-1.5">
                  {p.nodes.map((id, j) => {
                    const n = s.nodes[id]!;
                    const isTarget = j === p.nodes.length - 1;
                    return (
                      <Fragment key={id}>
                        {j > 0 ? <span className="text-ink-3">→</span> : null}
                        {n.kind === 'anchor' ? (
                          <span className="inline-flex items-center gap-1 rounded-[5px] bg-neel-700 px-1.5 py-0.5 text-[12px] font-medium text-surface">
                            <IconAnchor size={12} /> {n.name.split(' ')[0]}
                          </span>
                        ) : (
                          <span className={isTarget ? 'font-semibold' : ''}>{isTarget && self ? 'You' : n.name.split(' ')[0]}</span>
                        )}
                      </Fragment>
                    );
                  })}
                </span>
                <span className="mt-1.5 block h-1 w-full max-w-[220px] rounded-full bg-paper-2">
                  <span className="block h-full rounded-full bg-neel-500" style={{ width: `${share}%` }} />
                </span>
              </td>
              <td className="num py-3 pl-4 text-right text-ink-2">{p.nodes.length - 1}</td>
              <td className="num py-3 pl-4 text-right font-mono">+{fmt(p.trust)}</td>
            </tr>
          );
        })}
        {a.absorbed > 0 ? (
          <tr className="border-b border-rule text-ink-3">
            <td className="py-3 pr-3">
              {a.absorbed} loop{a.absorbed > 1 ? 's' : ''} re-entered a node already on the path and {a.absorbed > 1 ? 'were' : 'was'} absorbed
            </td>
            <td className="py-3 pl-4 text-right">—</td>
            <td className="num py-3 pl-4 text-right font-mono">0.00</td>
          </tr>
        ) : null}
      </tbody>
      <tfoot>
        <tr className="border-t border-ink">
          <td className="pt-2.5 font-medium">
            Graph trust R<sub>graph</sub>
          </td>
          <td />
          <td className="num pt-2.5 text-right font-mono font-semibold">{fmt(a.rGraph)}</td>
        </tr>
      </tfoot>
    </table>
  );
}
