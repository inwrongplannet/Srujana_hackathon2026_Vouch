/**
 * In-memory store for the community demo: asks, vouches, setback responses and what each borrower
 * shows strangers. Session only (a reload restores the seed); every write makes a new snapshot so
 * React re-renders through useSyncExternalStore.
 */
import { useSyncExternalStore } from 'react';
import { ASKS, MEMBERS, VIEWER_ID, type Ask } from '@/mocks/community';
import { staked, type Member, type Vouch } from '@/mocks/engine/community';

export interface CommunityState {
  asks: Ask[];
  members: Record<string, Member>;
}

let state: CommunityState = { asks: ASKS, members: MEMBERS };
const listeners = new Set<() => void>();

function set(next: CommunityState) {
  state = next;
  listeners.forEach((l) => l());
}

function updateAsk(id: string, change: (ask: Ask) => Ask) {
  set({ ...state, asks: state.asks.map((a) => (a.id === id ? change(a) : a)) });
}

export const community = {
  /** The viewer vouches: the stake is committed against their budget and the vouch joins the ask. */
  vouch(askId: string, vouch: Vouch) {
    const me = state.members[vouch.voucherId]!;
    const fixed = staked(me, vouch);
    set({
      members: { ...state.members, [me.id]: { ...me, committed: me.committed.plus(vouch.stake) } },
      asks: state.asks.map((a) => (a.id === askId ? { ...a, vouches: [...a.vouches, fixed] } : a)),
    });
  },
  /** Stand by keeps the vouch (a renewal); step back withdraws it and releases the stake. */
  respond(askId: string, voucherId: string, choice: 'STAND_BY' | 'STEP_BACK') {
    const ask = state.asks.find((a) => a.id === askId)!;
    const gone = choice === 'STEP_BACK' ? ask.vouches.find((v) => v.voucherId === voucherId) : undefined;
    const me = state.members[voucherId]!;
    set({
      members: gone ? { ...state.members, [voucherId]: { ...me, committed: me.committed.minus(gone.stake) } } : state.members,
      asks: state.asks.map((a) =>
        a.id !== askId || !a.setback
          ? a
          : {
              ...a,
              vouches: gone ? a.vouches.filter((v) => v !== gone) : a.vouches,
              setback: { ...a.setback, responses: { ...a.setback.responses, [voucherId]: choice } },
            },
      ),
    });
  },
  setShown(askId: string, key: string, shown: boolean) {
    updateAsk(askId, (a) => ({ ...a, verified: a.verified.map((x) => (x.key === key ? { ...x, shown } : x)) }));
  },
  postSetback(askId: string, text: string) {
    updateAsk(askId, (a) => ({
      ...a,
      setback: {
        posted: 'just now', reported: true, text,
        responses: Object.fromEntries(a.vouches.filter((v) => v.kind === 'KNOWN').map((v) => [v.voucherId, 'PENDING' as const])),
      },
    }));
  },
};

export function useCommunity(): CommunityState {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => state,
  );
}

export const viewer = () => state.members[VIEWER_ID]!;
