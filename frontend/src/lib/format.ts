/**
 * Presentation-only formatting. Amounts stay decimal strings until this point; rounding happens
 * here and nowhere else. Intl.NumberFormat formats decimal strings exactly (no float conversion).
 */
import Decimal from 'decimal.js';
import type { Money } from '@/api/types';

const nfCache = new Map<string, Intl.NumberFormat>();
function nf(currency: string, dp: number): Intl.NumberFormat {
  const key = `${currency}:${dp}`;
  if (!nfCache.has(key)) {
    nfCache.set(
      key,
      new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency,
        minimumFractionDigits: dp,
        maximumFractionDigits: dp,
      }),
    );
  }
  return nfCache.get(key)!;
}

/** "₹1,20,000" in Indian digit grouping; banker's rounding to `dp` places. */
export function formatMoney(m: Money, dp = 0): string {
  const fixed = new Decimal(m.amount).toFixed(dp, Decimal.ROUND_HALF_EVEN);
  // The runtime accepts decimal strings exactly; the cast only satisfies older lib typings.
  return nf(m.currency, dp).format(fixed as unknown as number);
}

export const inr = (amount: string): Money => ({ amount, currency: 'INR' });

/** A score or weight to `dp` places. */
export function fmt(value: string, dp = 2): string {
  return new Decimal(value).toFixed(dp, Decimal.ROUND_HALF_EVEN);
}

/** Signed with a true minus sign: "+0.50", "−0.35". */
export function fmtSigned(value: string, dp = 2): string {
  const d = new Decimal(value);
  const body = d.abs().toFixed(dp, Decimal.ROUND_HALF_EVEN);
  if (d.isZero()) return body;
  return `${d.isNegative() ? '−' : '+'}${body}`;
}

/** A fraction as a percentage string: "0.625" -> "63%". */
export function pct(value: string, dp = 0): string {
  return `${new Decimal(value).mul(100).toFixed(dp, Decimal.ROUND_HALF_EVEN)}%`;
}

/** Assessment confidence shown beside sigma2: 1 - sigma2 as a percentage. */
export function confidencePct(sigma2: string): string {
  return `${new Decimal(1).minus(sigma2).mul(100).toFixed(0, Decimal.ROUND_HALF_EVEN)}%`;
}

/**
 * Converts a decimal string to a JS number for drawing only (pixel positions, bar widths).
 * Never use the result for money or scoring.
 */
export const geom = (value: string): number => Number(value);

export function shortHash(hash: string, lead = 6, tail = 4): string {
  if (hash.length <= lead + tail + 2) return hash;
  return `${hash.slice(0, lead + 2)}…${hash.slice(-tail)}`;
}

/** Story clock: the demo starts on day 0, 24 Oct 2026. */
const EPOCH = Date.UTC(2026, 9, 24);
const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' });
export function dayDate(day: number): string {
  return dateFmt.format(new Date(EPOCH + day * 86_400_000));
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join('');
}
