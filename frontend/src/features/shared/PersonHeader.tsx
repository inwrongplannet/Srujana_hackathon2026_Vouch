import type { ReactNode } from 'react';
import type { ApiNode } from '@/api/types';
import { Avatar } from '@/components/ui/Avatar';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { IdentityGlyph } from '@/components/ui/IdentityGlyph';
import { shortHash } from '@/lib/format';

/** Page header for a seat: who you are looking as, and their anchored identity. */
export function PersonHeader({ node, seat, aside }: { node: ApiNode; seat: string; aside?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-6">
      <div className="flex items-center gap-4">
        <Avatar node={node} size={54} />
        <div>
          <p className="eyebrow">{seat}</p>
          <h1 className="display mt-1 text-[38px] leading-none">{node.name}</h1>
          <p className="mt-2 flex flex-wrap items-center gap-2 text-[13.5px] text-ink-2">
            {node.role} · {node.place}
            <StatusBadge node={node} />
          </p>
        </div>
      </div>
      {aside ??
        (node.nullifier ? (
          <div className="flex items-center gap-3 rounded-[12px] border border-rule bg-surface py-2 pr-4 pl-2">
            <IdentityGlyph hash={node.nullifier} size={40} />
            <div>
              <p className="text-[11.5px] text-ink-3">Simulated identity anchor</p>
              <p className="font-mono text-[12.5px]">{shortHash(node.nullifier, 8, 6)}</p>
            </div>
          </div>
        ) : null)}
    </div>
  );
}
