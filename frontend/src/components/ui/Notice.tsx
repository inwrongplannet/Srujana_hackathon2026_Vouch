import { IconInfo } from '@/components/icons';

/** Required on every screen that shows figures from seed data (frontend/AGENTS.md). */
export function IllustrativeNotice({ className = '' }: { className?: string }) {
  return (
    <p className={`inline-flex items-center gap-2 text-[12px] text-ink-3 ${className}`}>
      <IconInfo size={14} />
      Illustrative data — not financial advice.
    </p>
  );
}
