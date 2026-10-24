/**
 * VeriTrust icon set. One grammar for every glyph: 24px grid, 1.5px round stroke, no fills except
 * a solid "node" dot where an icon touches the trust graph. Never emoji.
 */
import type { ReactNode, SVGProps } from 'react';

export type IconProps = SVGProps<SVGSVGElement> & { size?: number; title?: string };

function Icon({ size = 18, title, children, ...rest }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      {children}
    </svg>
  );
}

const Node = ({ cx, cy, r = 1.6 }: { cx: number; cy: number; r?: number }) => (
  <circle cx={cx} cy={cy} r={r} fill="currentColor" stroke="none" />
);

export const IconAnchor = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3.5 9.5 12 4.5l8.5 5" />
    <path d="M6 10.5v7M10 10.5v7M14 10.5v7M18 10.5v7" />
    <path d="M3.5 19.5h17" />
    <Node cx={12} cy={4.5} />
  </Icon>
);

export const IconPerson = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="8.5" r="3.5" />
    <path d="M5 19.5c.6-3.6 3.4-5.5 7-5.5s6.4 1.9 7 5.5" />
  </Icon>
);

export const IconCommunity = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="8.5" cy="9" r="2.8" />
    <circle cx="16.5" cy="10" r="2.3" />
    <path d="M3.5 19c.5-3 2.4-4.6 5-4.6s4.5 1.6 5 4.6" />
    <path d="M14.5 14.6c2.6-.3 4.5 1 5.2 3.9" />
  </Icon>
);

export const IconVouch = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="5.5" cy="12" r="2.5" />
    <path d="M8.5 12h8" />
    <path d="m14.5 9.5 2.5 2.5-2.5 2.5" />
    <Node cx={19} cy={12} r={2} />
  </Icon>
);

export const IconGraph = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 5.5 6 17.5M12 5.5l6 12M7.8 18.5h8.4" />
    <Node cx={12} cy={5} r={2} />
    <Node cx={5.5} cy={18.5} r={2} />
    <Node cx={18.5} cy={18.5} r={2} />
  </Icon>
);

export const IconLedger = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6.5 3.5h11a1.5 1.5 0 0 1 1.5 1.5v14.5H8a2.5 2.5 0 0 1-2.5-2.5V4.5a1 1 0 0 1 1-1Z" />
    <path d="M5.5 17a2.5 2.5 0 0 1 2.5-2.5h11" />
    <path d="M9.5 7.5h6M9.5 10.5h4" />
  </Icon>
);

export const IconShield = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 3.5 19 6v5.5c0 4.2-2.9 7.6-7 9-4.1-1.4-7-4.8-7-9V6l7-2.5Z" />
    <Node cx={12} cy={11.5} r={1.9} />
  </Icon>
);

export const IconFingerprint = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7.5 18.5c-.8-1.8-1.2-3.7-1.2-5.8a5.7 5.7 0 0 1 11.4 0c0 1.1-.1 2.2-.3 3.2" />
    <path d="M10.2 19.8c-.8-2-1.1-4.2-1.1-6.8a2.9 2.9 0 0 1 5.8 0c0 2.6-.4 4.9-1.2 6.9" />
    <path d="M12 13v3.5" />
    <path d="M4.7 9.2A8.4 8.4 0 0 1 12 4.3a8.4 8.4 0 0 1 7.3 4.3" />
  </Icon>
);

export const IconPhone = (p: IconProps) => (
  <Icon {...p}>
    <rect x="6.5" y="3" width="11" height="18" rx="2.5" />
    <path d="M10.5 18h3" />
    <Node cx={9.8} cy={10.5} r={0.9} />
    <Node cx={12} cy={10.5} r={0.9} />
    <Node cx={14.2} cy={10.5} r={0.9} />
  </Icon>
);

export const IconLocker = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v8.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2V7.5Z" />
    <path d="m9.5 13.5 2 2 3.5-4" />
  </Icon>
);

export const IconStatement = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6.5 3.5h7.5l4 4v12a1 1 0 0 1-1 1h-10.5a1 1 0 0 1-1-1v-15a1 1 0 0 1 1-1Z" />
    <path d="M14 3.5v4h4" />
    <path d="m8.5 16 2.5-3 2 1.8 2.5-3.3" />
  </Icon>
);

export const IconBulb = (p: IconProps) => (
  <Icon {...p}>
    <path d="M9 17.5h6M10 20.5h4" />
    <path d="M12 3.5a5.5 5.5 0 0 0-3.2 10c.7.5 1.2 1.3 1.2 2.2v1.8h4v-1.8c0-.9.5-1.7 1.2-2.2A5.5 5.5 0 0 0 12 3.5Z" />
  </Icon>
);

export const IconClockForward = (p: IconProps) => (
  <Icon {...p}>
    <path d="M20 12a8 8 0 1 1-2.3-5.7" />
    <path d="M20 4.5v3.5h-3.5" />
    <path d="M12 8v4.2l2.8 1.8" />
  </Icon>
);

export const IconCheck = (p: IconProps) => (
  <Icon {...p}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </Icon>
);

export const IconClose = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />
  </Icon>
);

export const IconArrowRight = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4.5 12h15M13.5 6l6 6-6 6" />
  </Icon>
);

export const IconArrowLeft = (p: IconProps) => (
  <Icon {...p}>
    <path d="M19.5 12h-15M10.5 6l-6 6 6 6" />
  </Icon>
);

export const IconArrowUpRight = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7 17 17 7M8.5 7H17v8.5" />
  </Icon>
);

export const IconChevronDown = (p: IconProps) => (
  <Icon {...p}>
    <path d="m6.5 9.5 5.5 5.5 5.5-5.5" />
  </Icon>
);

export const IconChevronRight = (p: IconProps) => (
  <Icon {...p}>
    <path d="m9.5 6.5 5.5 5.5-5.5 5.5" />
  </Icon>
);

export const IconPlus = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);

export const IconAlert = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10.3 4.6 3 17.6a2 2 0 0 0 1.7 2.9h14.6a2 2 0 0 0 1.7-2.9l-7.3-13a2 2 0 0 0-3.4 0Z" />
    <path d="M12 9.5v4" />
    <Node cx={12} cy={16.8} r={1} />
  </Icon>
);

export const IconInfo = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 11v5" />
    <Node cx={12} cy={8} r={1} />
  </Icon>
);

/** A circuit-breaker switch: two terminals, lever thrown open. */
export const IconBreaker = (p: IconProps) => (
  <Icon {...p}>
    <path d="M3 15.5h4.5M16.5 15.5H21" />
    <circle cx="8.8" cy="15.5" r="1.4" />
    <circle cx="15.2" cy="15.5" r="1.4" />
    <path d="m9.8 14.5 5.4-6" />
  </Icon>
);

/** A chain block: the simulated ledger. */
export const IconBlock = (p: IconProps) => (
  <Icon {...p}>
    <path d="m12 3.5 7.5 4.2v8.6L12 20.5l-7.5-4.2V7.7L12 3.5Z" />
    <path d="M4.5 7.7 12 12l7.5-4.3M12 12v8.5" />
  </Icon>
);

export const IconCopy = (p: IconProps) => (
  <Icon {...p}>
    <rect x="8.5" y="8.5" width="11" height="11" rx="2" />
    <path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5" />
  </Icon>
);

export const IconQr = (p: IconProps) => (
  <Icon {...p}>
    <rect x="4" y="4" width="6" height="6" rx="1" />
    <rect x="14" y="4" width="6" height="6" rx="1" />
    <rect x="4" y="14" width="6" height="6" rx="1" />
    <path d="M14 14h2.5v2.5H14zM18.5 18.5H20V20M14 20h1.5M20 14v2" />
  </Icon>
);

export const IconSliders = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4.5 7.5h9M17.5 7.5h2M4.5 16.5h3M11.5 16.5h8" />
    <circle cx="15.5" cy="7.5" r="2" />
    <circle cx="9.5" cy="16.5" r="2" />
  </Icon>
);

export const IconLock = (p: IconProps) => (
  <Icon {...p}>
    <rect x="5" y="10.5" width="14" height="10" rx="2" />
    <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" />
    <Node cx={12} cy={15.5} r={1.2} />
  </Icon>
);

export const IconRupee = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7 4.5h10M7 9h10" />
    <path d="M7 4.5h3.5a4.25 4.25 0 0 1 0 8.5H7l7.5 7" />
  </Icon>
);

export const IconReset = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 12a8 8 0 1 0 2.3-5.7" />
    <path d="M4 4.5V8h3.5" />
  </Icon>
);

export const IconRipple = (p: IconProps) => (
  <Icon {...p}>
    <Node cx={12} cy={12} r={2} />
    <circle cx="12" cy="12" r="5.5" strokeDasharray="2 2.4" />
    <circle cx="12" cy="12" r="9" strokeDasharray="1.2 3.2" />
  </Icon>
);

export const IconSeal = (p: IconProps) => (
  <Icon {...p}>
    <path d="m12 3 2.1 1.6 2.6-.2.8 2.5 2.2 1.4-.8 2.5.8 2.5-2.2 1.4-.8 2.5-2.6-.2L12 18.6l-2.1-1.6-2.6.2-.8-2.5-2.2-1.4.8-2.5-.8-2.5 2.2-1.4.8-2.5 2.6.2L12 3Z" />
    <path d="m9.2 11 1.9 1.9 3.7-3.8" />
  </Icon>
);

export const IconEye = (p: IconProps) => (
  <Icon {...p}>
    <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
    <circle cx="12" cy="12" r="2.8" />
  </Icon>
);

export const IconLogout = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14 4.5H6.5a1 1 0 0 0-1 1v13a1 1 0 0 0 1 1H14" />
    <path d="M10 12h10M16.5 8.5 20 12l-3.5 3.5" />
  </Icon>
);

export const IconPlay = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7.5 5.5v13l11-6.5-11-6.5Z" />
  </Icon>
);

export const IconHatch = (p: IconProps) => (
  <Icon {...p}>
    <rect x="4" y="6" width="16" height="12" rx="2" />
    <path d="M8 18 16 6M4.5 13.5 10 6M14 18l6-8" />
  </Icon>
);

export const IconStorm = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7 15.5a4.5 4.5 0 0 1-.4-9 5.5 5.5 0 0 1 10.6 1.6A3.7 3.7 0 0 1 17.5 15.5" />
    <path d="m12.5 12.5-2 4h3l-2 4" />
  </Icon>
);

export const IconGauge = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 17a8 8 0 1 1 16 0" />
    <path d="m12 17 4-5.5" />
    <Node cx={12} cy={17} r={1.6} />
  </Icon>
);
