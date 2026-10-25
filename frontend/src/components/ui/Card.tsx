import type { ReactNode } from 'react';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function CardHead({ eyebrow, title, aside, className = '' }: { eyebrow?: ReactNode; title?: ReactNode; aside?: ReactNode; className?: string }) {
  return (
    <div className={`flex items-start justify-between gap-4 ${className}`}>
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        {title ? <h3 className="display mt-1.5 text-[22px] leading-tight">{title}</h3> : null}
      </div>
      {aside}
    </div>
  );
}
