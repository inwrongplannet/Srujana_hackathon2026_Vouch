/**
 * A visual fingerprint of a nullifier: a mirrored 7x7 grid drawn from the hash bytes, in neel.
 * Same hash, same glyph, so a re-registration is recognisable at a glance.
 */
export function IdentityGlyph({ hash, size = 56, className = '' }: { hash: string; size?: number; className?: string }) {
  const hex = hash.replace(/^0x/, '').padEnd(64, '0');
  const cells: { x: number; y: number; shade: number }[] = [];
  for (let y = 0; y < 7; y += 1) {
    for (let x = 0; x < 4; x += 1) {
      const nibble = parseInt(hex[(y * 4 + x) % 64]!, 16);
      if (nibble % 3 === 0) continue;
      const shade = nibble > 10 ? 0 : nibble > 5 ? 1 : 2;
      cells.push({ x, y, shade });
      if (x < 3) cells.push({ x: 6 - x, y, shade });
    }
  }
  const fills = ['#24368F', '#3D56C2', '#9AA8DC'];
  const cell = 10;
  return (
    <svg width={size} height={size} viewBox="-3 -3 76 76" className={className} aria-hidden>
      <rect x="-3" y="-3" width="76" height="76" rx="12" fill="#ECEEF7" />
      {cells.map((c, i) => (
        <rect key={i} x={c.x * cell + 1} y={c.y * cell + 1} width={cell - 2} height={cell - 2} rx="1.6" fill={fills[c.shade]} />
      ))}
    </svg>
  );
}
