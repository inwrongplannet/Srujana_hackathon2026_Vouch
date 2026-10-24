import type { ApiNode } from '@/api/types';
import { initials } from '@/lib/format';
import { IconAnchor } from '@/components/icons';
import { nodeTone } from './StatusBadge';

const ring: Record<string, string> = {
  active: 'ring-active/70',
  restricted: 'ring-restricted',
  defaulted: 'ring-defaulted',
  cold: 'ring-cold ring-dashed',
};

/** People are circles, institutions are squares: the same grammar as the trust graph. */
export function Avatar({ node, size = 36 }: { node: ApiNode; size?: number }) {
  if (node.kind === 'anchor') {
    return (
      <span
        className="grid shrink-0 place-items-center rounded-[8px] bg-neel-700 text-surface"
        style={{ width: size, height: size }}
        aria-hidden
      >
        <IconAnchor size={size * 0.52} />
      </span>
    );
  }
  const tone = nodeTone(node);
  return (
    <span
      className={`grid shrink-0 place-items-center rounded-full bg-paper-2 font-medium text-ink ring-2 ring-offset-2 ring-offset-surface ${ring[tone]} ${tone === 'cold' ? 'outline outline-1 outline-dashed outline-cold ring-0' : ''}`}
      style={{ width: size, height: size, fontSize: size * 0.36 }}
      aria-hidden
    >
      {initials(node.name)}
    </span>
  );
}
