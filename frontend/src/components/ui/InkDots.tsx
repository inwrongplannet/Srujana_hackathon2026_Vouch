/** Branded loader: three graph nodes taking turns, never a generic spinner. */
export function InkDots({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 ${className}`} role="status" aria-label="Working">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="size-1.5 rounded-full bg-current animate-[inkdot_900ms_var(--ease-ink)_infinite]"
          style={{ animationDelay: `${i * 140}ms` }}
        />
      ))}
      <style>{'@keyframes inkdot{0%,100%{opacity:.25;transform:translateY(0)}40%{opacity:1;transform:translateY(-2px)}}'}</style>
    </span>
  );
}
