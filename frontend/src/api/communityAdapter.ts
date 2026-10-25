/**
 * Converts the live community API (`/api/v1/community`) into the shapes the community screens
 * already draw (`src/mocks/community.ts`), so the same components render demo or live data.
 *
 * The backend seeds the same cast with upper-case ids (`MEENA`, `FARIDA_ASK`); the screens and
 * routes use lower-case ids (`meena`). Ids are translated only here, in both directions.
 * Amounts, stakes and weights stay decimal strings until they become Decimal.
 */
import type { Ask } from '@/mocks/community';
import type { Member, Relationship, Vouch } from '@/mocks/engine/community';
import { D } from '@/mocks/engine/params';
import type { CommunityAsk, CommunityMember } from './backend';

export const toLocalId = (id: string) => id.toLowerCase();
export const toApiId = (id: string) => id.toUpperCase();

export function toMember(m: CommunityMember): Member {
  return {
    id: toLocalId(m.id),
    name: m.name,
    line: m.line,
    reputation: D(m.reputation),
    budget: D(m.budget),
    committed: D(m.committed),
    resolved: m.resolved,
    repaid: m.repaid,
  };
}

export function toAsk(a: CommunityAsk): Ask {
  const vouches: Vouch[] = a.vouches.map((v) => ({
    voucherId: toLocalId(v.voucher_id),
    kind: v.kind,
    stake: D(v.stake),
    relationship: (v.relationship ?? undefined) as Relationship | undefined,
    yearsKnown: v.years_known ?? undefined,
    utilisation: v.utilisation ? D(v.utilisation) : undefined,
  }));
  return {
    id: toLocalId(a.id),
    ownerId: toLocalId(a.owner_id),
    name: a.name,
    trade: a.trade,
    place: a.place,
    circle: a.circle,
    purpose: a.purpose,
    amountBand: a.amount_band,
    postedDays: a.posted_days,
    story: a.story,
    verified: a.verified,
    thinFile: a.thin_file,
    bureau: { status: a.bureau_status, trail: a.bureau_trail ?? null },
    expectedRepay: D(a.expected_repay),
    vouches,
    setback: a.setback
      ? {
          posted: a.setback.posted,
          text: a.setback.text,
          reported: true,
          responses: Object.fromEntries(Object.entries(a.setback.responses).map(([k, v]) => [toLocalId(k), v])),
        }
      : undefined,
    knownBy: a.known_by.map(toLocalId),
  };
}
