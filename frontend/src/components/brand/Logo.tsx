/** Mark: two vouches converging on one node. Wordmark set in Anek. */
export function LogoMark({ size = 28, tone = 'ink' }: { size?: number; tone?: 'ink' | 'paper' }) {
  const stroke = tone === 'ink' ? '#16181F' : '#F4F1EA';
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden>
      <path d="M5 5 L14 21 L23 5" fill="none" stroke={stroke} strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="5" cy="5" r="2.7" fill={stroke} />
      <circle cx="23" cy="5" r="2.7" fill={stroke} />
      <circle cx="14" cy="22" r="4.3" fill={tone === 'ink' ? '#24368F' : '#9AA8DC'} />
    </svg>
  );
}

export function Logo({ tone = 'ink', size = 26, word = 'Vouch' }: { tone?: 'ink' | 'paper'; size?: number; word?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${tone === 'ink' ? 'text-ink' : 'text-paper'}`}>
      <LogoMark size={size} tone={tone} />
      {word ? <span className="display text-[21px] leading-none tracking-[-0.01em]">{word}</span> : null}
    </span>
  );
}
