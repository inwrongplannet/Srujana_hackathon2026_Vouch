import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router';
import { InkDots } from './InkDots';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'ink';
type Size = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  trailingIcon?: ReactNode;
}

const variants: Record<Variant, string> = {
  primary:
    'bg-neel-700 text-surface hover:bg-neel-800 active:bg-neel-900 shadow-[inset_0_1px_0_rgb(255_255_255/0.12),0_1px_2px_rgb(19_28_70/0.3)] disabled:bg-paper-3 disabled:text-ink-3 disabled:shadow-none',
  ink: 'bg-ink text-paper hover:bg-neel-950 active:bg-black disabled:bg-paper-3 disabled:text-ink-3',
  secondary: 'bg-surface text-ink border border-rule-2 hover:border-ink-3 hover:bg-white active:bg-paper-2 disabled:text-ink-3 disabled:border-rule',
  ghost: 'text-ink-2 hover:text-ink hover:bg-paper-2 active:bg-paper-3 disabled:text-ink-3',
  danger:
    'bg-surface text-defaulted border border-defaulted/40 hover:bg-defaulted-tint active:bg-defaulted-tint disabled:text-ink-3 disabled:border-rule',
};

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-[13px] gap-1.5 rounded-[6px]',
  md: 'h-10 px-4 text-[14px] gap-2 rounded-[7px]',
  lg: 'h-12 px-5 text-[15px] gap-2.5 rounded-[8px]',
};

const BASE =
  'relative inline-flex select-none items-center justify-center font-medium whitespace-nowrap transition-[background-color,border-color,color,transform] duration-150 ease-[var(--ease-ink)] active:translate-y-px';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', loading, icon, trailingIcon, className = '', children, disabled, ...rest },
  ref,
) {
  return (
    <button ref={ref} disabled={disabled || loading} className={`${BASE} ${variants[variant]} ${sizes[size]} ${className}`} {...rest}>
      <span className={`inline-flex items-center gap-[inherit] ${loading ? 'opacity-0' : ''}`}>
        {icon}
        {children}
        {trailingIcon}
      </span>
      {loading ? (
        <span className="absolute inset-0 grid place-items-center">
          <InkDots />
        </span>
      ) : null}
    </button>
  );
});

/** A navigation link styled as a button: one interactive element, never a button inside a link. */
export function ButtonLink({
  variant = 'primary',
  size = 'md',
  icon,
  trailingIcon,
  className = '',
  children,
  ...rest
}: LinkProps & { variant?: Variant; size?: Size; icon?: ReactNode; trailingIcon?: ReactNode }) {
  return (
    <Link className={`${BASE} ${variants[variant]} ${sizes[size]} ${className}`} {...rest}>
      {icon}
      {children}
      {trailingIcon}
    </Link>
  );
}
