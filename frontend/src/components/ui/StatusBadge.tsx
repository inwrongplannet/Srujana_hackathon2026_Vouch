import type { ApiNode } from '@/api/types';
import type { ReactNode } from 'react';

export type Tone = 'active' | 'restricted' | 'defaulted' | 'cold' | 'neel' | 'plain';

const tones: Record<Tone, string> = {
  active: 'bg-active-tint text-active',
  restricted: 'bg-restricted-tint text-restricted-ink',
  defaulted: 'bg-defaulted-tint text-defaulted',
  cold: 'bg-cold-tint text-[#55585f]',
  neel: 'bg-neel-50 text-neel-800',
  plain: 'border border-dashed border-rule-2 text-ink-2',
};

const dots: Record<Tone, string> = {
  active: 'bg-active',
  restricted: 'bg-restricted',
  defaulted: 'bg-defaulted',
  cold: 'border border-dashed border-cold bg-transparent',
  neel: 'bg-neel-500',
  plain: 'bg-ink-3',
};

export function Badge({ tone = 'plain', children, dot = true, className = '' }: { tone?: Tone; children: ReactNode; dot?: boolean; className?: string }) {
  return (
    <span className={`inline-flex h-6 items-center gap-1.5 rounded-full px-2.5 text-[12px] font-medium whitespace-nowrap ${tones[tone]} ${className}`}>
      {dot ? <span className={`size-1.5 shrink-0 rounded-full ${dots[tone]}`} /> : null}
      {children}
    </span>
  );
}

export function nodeTone(node: Pick<ApiNode, 'status' | 'coldStart'>): Tone {
  if (node.status === 'DEFAULTED') return 'defaulted';
  if (node.status === 'RESTRICTED') return 'restricted';
  if (node.coldStart) return 'cold';
  return 'active';
}

export function nodeLabel(node: Pick<ApiNode, 'status' | 'coldStart'>): string {
  if (node.status === 'DEFAULTED') return 'Defaulted';
  if (node.status === 'RESTRICTED') return 'Restricted';
  if (node.coldStart) return 'Cold start';
  return 'Active';
}

export function StatusBadge({ node }: { node: Pick<ApiNode, 'status' | 'coldStart'> }) {
  return <Badge tone={nodeTone(node)}>{nodeLabel(node)}</Badge>;
}
