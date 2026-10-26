/**
 * Store for the community screens. It starts on the built-in demo data (`src/mocks/community.ts`)
 * and switches to the live backend (`/api/v1/community`) once `/health` answers. Live, every
 * action is a backend call followed by a reload, so the screens show what the server holds. If the
 * backend stops answering, the store carries on with demo data and applies the action there, so
 * the demo never stops on an error; a refusal from the backend (say, too few points to stake) is
 * shown as the backend's own reason. Every write makes a new snapshot for useSyncExternalStore.
 */
import { useSyncExternalStore } from 'react';
import { backend } from '@/api/backend';
import { toApiId, toAsk, toMember } from '@/api/communityAdapter';
import { isRefusal } from '@/api/http';
import { ASKS, MEMBERS, VIEWER_ID, type Ask } from '@/mocks/community';
import { staked, type Member, type Vouch } from '@/mocks/engine/community';

export type CommunitySource = 'demo' | 'live';

export interface CommunityState {
  asks: Ask[];
  members: Record<string, Member>;
  source: CommunitySource;
  /** The backend's reason for refusing the last action, if it did; cleared by the next action. */
  notice: string | null;
}

let state: CommunityState = { asks: ASKS, members: MEMBERS, source: 'demo', notice: null };
const listeners = new Set<() => void>();

function set(next: CommunityState) {
  state = next;
  listeners.forEach((l) => l());
}

function updateAsk(id: string, change: (ask: Ask) => Ask) {
  set({ ...state, asks: state.asks.map((a) => (a.id === id ? change(a) : a)) });
}

/**
 * Loads members and asks from the backend. Each ask is read as its owner sees it, so the store
 * holds every verified item with its `shown` flag; the screens hide unshown items from strangers,
 * exactly as with the demo data.
 */
async function loadLive(): Promise<void> {
  const [members, list] = await Promise.all([backend.community.members(), backend.community.asks()]);
  const asks = await Promise.all(list.map((a) => backend.community.ask(a.id, a.owner_id)));
  set({
    asks: asks.map(toAsk),
    members: Object.fromEntries(members.map((m) => [m.id.toLowerCase(), toMember(m)])),
    source: 'live',
    notice: null,
  });
}

/** Live: call, then reload. Refused: say why. No answer: carry on with demo data and apply it locally. */
async function run(remote: () => Promise<unknown>, local: () => void): Promise<void> {
  if (state.source !== 'live') return local();
  try {
    await remote();
    await loadLive();
  } catch (e) {
    if (isRefusal(e)) {
      set({ ...state, notice: e.message });
      return;
    }
    set({ ...state, source: 'demo', notice: null });
    local();
  }
}

const local = {
  vouch(askId: string, vouch: Vouch) {
    const me = state.members[vouch.voucherId]!;
    const fixed = staked(me, vouch);
    set({
      ...state,
      members: { ...state.members, [me.id]: { ...me, committed: me.committed.plus(vouch.stake) } },
      asks: state.asks.map((a) => (a.id === askId ? { ...a, vouches: [...a.vouches, fixed] } : a)),
    });
  },
  respond(askId: string, voucherId: string, choice: 'STAND_BY' | 'STEP_BACK') {
    const ask = state.asks.find((a) => a.id === askId)!;
    const gone = choice === 'STEP_BACK' ? ask.vouches.find((v) => v.voucherId === voucherId) : undefined;
    const me = state.members[voucherId]!;
    set({
      ...state,
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

export const community = {
  /** Switch to live data; stays on demo data if the backend cannot be read. */
  async connect() {
    try {
      await loadLive();
    } catch {
      set({ ...state, source: 'demo', notice: null });
    }
  },
  /** The viewer vouches: the stake is committed against their budget and the vouch joins the ask. */
  vouch(askId: string, vouch: Vouch) {
    return run(
      () =>
        backend.community.vouch(toApiId(askId), {
          voucher_id: toApiId(vouch.voucherId),
          kind: vouch.kind,
          stake: vouch.stake.toString(),
          relationship: vouch.kind === 'KNOWN' ? vouch.relationship : undefined,
          years_known: vouch.kind === 'KNOWN' ? vouch.yearsKnown : undefined,
          read_verified: vouch.kind === 'EVIDENCE',
        }),
      () => local.vouch(askId, vouch),
    );
  },
  /** Stand by keeps the vouch (a renewal); step back withdraws it and releases the stake. */
  respond(askId: string, voucherId: string, choice: 'STAND_BY' | 'STEP_BACK') {
    return run(
      () => backend.community.respond(toApiId(askId), toApiId(voucherId), choice),
      () => local.respond(askId, voucherId, choice),
    );
  },
  setShown(askId: string, key: string, shown: boolean) {
    return run(
      () => backend.community.setShown(toApiId(askId), key, shown),
      () => local.setShown(askId, key, shown),
    );
  },
  postSetback(askId: string, text: string) {
    return run(
      () => backend.community.postSetback(toApiId(askId), text),
      () => local.postSetback(askId, text),
    );
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
