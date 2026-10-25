/** Says where a screen's figures come from: the live backend or the built-in demo data. */
export function SourceBadge({ live, className = '' }: { live: boolean; className?: string }) {
  return (
    <span
      title={live ? 'Figures come from the FastAPI backend' : 'Backend not reachable: showing the built-in demo data'}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10.5px] whitespace-nowrap ${
        live ? 'border-active/30 bg-active-tint text-active' : 'border-rule-2 bg-paper-2 text-ink-3'
      } ${className}`}
    >
      <span className={`size-1.5 rounded-full ${live ? 'bg-active' : 'bg-cold'}`} />
      {live ? 'live backend' : 'demo data'}
    </span>
  );
}
