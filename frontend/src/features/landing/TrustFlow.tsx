/**
 * "How trust moves", drawn as one ledger line with four stations rather than four cards.
 */
const STATIONS = [
  {
    n: '01',
    title: 'Institutions seed trust',
    text: 'Only lenders, utilities and co-op banks that deploy real capital start with credibility. A ring of friends vouching for each other generates nothing.',
    art: (
      <svg viewBox="0 0 120 70" className="h-16 w-auto" aria-hidden>
        <rect x="44" y="8" width="32" height="32" rx="8" fill="#24368F" />
        <path d="M52 22 60 17l8 5M54 23v8M58 23v8M62 23v8M66 23v8M51 33h18" stroke="#FBFAF6" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        <path d="M60 42v14M60 42 34 60M60 42l26 18" stroke="#3D56C2" strokeWidth="1.6" strokeDasharray="3 4" />
        <circle cx="34" cy="62" r="5" fill="#2E7A4D" />
        <circle cx="60" cy="62" r="5" fill="#2E7A4D" />
        <circle cx="86" cy="62" r="5" fill="#2E7A4D" />
      </svg>
    ),
  },
  {
    n: '02',
    title: 'Members vouch, at a cost',
    text: 'Credibility is a fixed budget split across everyone you back. Each new vouch thins the others, so a vouch can’t be sold in bulk.',
    art: (
      <svg viewBox="0 0 120 70" className="h-16 w-auto" aria-hidden>
        <rect x="8" y="22" width="32" height="26" rx="5" fill="#24368F" />
        <rect x="43" y="22" width="32" height="26" rx="5" fill="#3D56C2" />
        <rect x="78" y="22" width="32" height="26" rx="5" fill="#ECEEF7" stroke="#3D56C2" strokeDasharray="3 3" />
        <path d="m82 48 22-26M86 48l18-21M92 48l12-14" stroke="#C9D0EC" strokeWidth="1.4" />
        <text x="60" y="64" textAnchor="middle" fontFamily="IBM Plex Mono" fontSize="9" fill="#6A6D76">W = C / |Out|</text>
      </svg>
    ),
  },
  {
    n: '03',
    title: 'Lenders read two axes',
    text: 'Expected capacity and uncertainty, never one opaque number. A thin file starts small because it is unknown, not because it is bad.',
    art: (
      <svg viewBox="0 0 120 70" className="h-16 w-auto" aria-hidden>
        <defs>
          <pattern id="tf-h" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
            <rect width="6" height="6" fill="#ECEEF7" />
            <rect width="1.4" height="6" fill="#C9D0EC" />
          </pattern>
        </defs>
        <rect x="8" y="30" width="104" height="6" rx="3" fill="#E3DDCF" />
        <rect x="30" y="22" width="58" height="22" rx="5" fill="url(#tf-h)" stroke="#C9D0EC" />
        <rect x="58" y="16" width="2" height="34" rx="1" fill="#16181F" />
        <rect x="25" y="28" width="10" height="10" rx="2" fill="#24368F" transform="rotate(45 30 33)" />
        <text x="30" y="62" textAnchor="middle" fontFamily="IBM Plex Mono" fontSize="9" fill="#24368F">lend here</text>
      </svg>
    ),
  },
  {
    n: '04',
    title: 'Outcomes flow back',
    text: 'Repayment mints credibility and pays sponsors a yield. A default slashes the sponsor, damps at the next hop, and stops dead at the third.',
    art: (
      <svg viewBox="0 0 120 70" className="h-16 w-auto" aria-hidden>
        <circle cx="20" cy="35" r="7" fill="#A8352A" />
        <circle cx="20" cy="35" r="14" fill="none" stroke="#A8352A" strokeOpacity="0.4" />
        <path d="M27 35h16" stroke="#C9C2B4" />
        <circle cx="50" cy="35" r="7" fill="#B87A1A" />
        <path d="M57 35h16" stroke="#C9C2B4" />
        <circle cx="80" cy="35" r="7" fill="#B87A1A" fillOpacity="0.6" />
        <path d="M87 35h9" stroke="#C9C2B4" />
        <circle cx="104" cy="35" r="7" fill="#2E7A4D" />
        <circle cx="104" cy="35" r="13" fill="none" stroke="#3D56C2" strokeDasharray="3 3" />
        <text x="104" y="62" textAnchor="middle" fontFamily="IBM Plex Mono" fontSize="9" fill="#24368F">hop 3</text>
      </svg>
    ),
  },
];

export function TrustFlow() {
  return (
    <div className="relative">
      <div className="absolute top-[38px] right-0 left-0 hidden border-t border-dashed border-rule-2 lg:block" aria-hidden />
      <ol className="grid gap-10 lg:grid-cols-4 lg:gap-8">
        {STATIONS.map((st) => (
          <li key={st.n} className="relative">
            <div className="flex items-center gap-3">
              <span className="relative z-10 grid size-[22px] place-items-center rounded-full bg-ink font-mono text-[10px] text-paper">{st.n}</span>
            </div>
            <div className="mt-6">{st.art}</div>
            <h3 className="display mt-4 text-[24px] leading-tight">{st.title}</h3>
            <p className="mt-2 text-[14.5px] text-ink-2">{st.text}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
