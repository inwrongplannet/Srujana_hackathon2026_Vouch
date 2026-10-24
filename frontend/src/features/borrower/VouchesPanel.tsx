import { useState } from 'react';
import { api } from '@/api/client';
import type { Snapshot } from '@/api/types';
import { Card, CardHead } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/StatusBadge';
import { Modal } from '@/components/ui/Modal';
import { IconCopy, IconLock, IconVouch, IconCheck } from '@/components/icons';
import { dayDate, fmt } from '@/lib/format';
import { VOUCH_NOTE } from '@/mocks/seed';
import { QrCode } from './QrCode';

/** Incoming vouches, or the empty state that invites the first one. */
export function VouchesPanel({ s }: { s: Snapshot }) {
  const me = s.borrowerId;
  const [asking, setAsking] = useState(false);
  const incoming = s.edges.filter((e) => e.to === me);
  const pending = s.requests.filter((r) => r.from === me && r.status === 'PENDING');

  return (
    <Card className="flex flex-col p-6">
      <CardHead
        eyebrow="Who backs you"
        title={incoming.length ? `${incoming.length} vouch${incoming.length > 1 ? 'es' : ''}` : 'No vouches yet'}
        aside={
          <Button variant="secondary" size="sm" icon={<IconVouch size={15} />} onClick={() => setAsking(true)}>
            Ask for a vouch
          </Button>
        }
      />

      {incoming.length === 0 && pending.length === 0 ? (
        <div className="mt-4 grid flex-1 items-center gap-6 sm:grid-cols-[180px_1fr]">
          <EmptyNode />
          <div>
            <p className="text-[14px] text-ink-2">
              A vouch is someone with a good record putting part of theirs behind you. One is enough to open a first limit.
            </p>
            <Button className="mt-4" onClick={() => setAsking(true)} icon={<IconVouch size={16} />}>
              Ask someone who knows your work
            </Button>
          </div>
        </div>
      ) : (
        <ul className="ruled mt-4">
          {pending.map((r) => (
            <li key={r.id} className="flex items-center gap-3 py-3">
              <Avatar node={s.nodes[r.to]!} size={34} />
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-medium">{s.nodes[r.to]!.name}</p>
                <p className="text-[12.5px] text-ink-3">Request sent {dayDate(r.day)} · waiting for their decision</p>
              </div>
              <Badge tone="neel">Pending</Badge>
            </li>
          ))}
          {incoming.map((e) => (
            <li key={e.from} className="flex items-center gap-3 py-3">
              <Avatar node={s.nodes[e.from]!} size={34} />
              <div className="min-w-0 flex-1">
                <p className="text-[14px] font-medium">{s.nodes[e.from]!.name}</p>
                <p className="text-[12.5px] text-ink-3">
                  {s.nodes[e.from]!.role} · since {dayDate(e.createdDay)}
                </p>
              </div>
              <div className="text-right">
                <p className="num font-mono text-[14px]">W {fmt(e.weight)}</p>
                {e.lockedLoanId ? (
                  <p className="inline-flex items-center gap-1 text-[11.5px] text-ink-3">
                    <IconLock size={12} /> backing {e.lockedLoanId}
                  </p>
                ) : (
                  <p className="text-[11.5px] text-ink-3">edge weight</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <RequestDialog s={s} open={asking} onClose={() => setAsking(false)} />
    </Card>
  );
}

function RequestDialog({ s, open, onClose }: { s: Snapshot; open: boolean; onClose: () => void }) {
  const me = s.borrowerId;
  // People in the same community who have capacity to vouch, the one who knows her work first.
  const candidates = Object.values(s.nodes)
    .filter((n) => n.kind === 'person' && n.id !== me && n.cluster === s.nodes[me]!.cluster && Number(n.capacity) > 0)
    .sort((a, b) => (a.id === s.voucherId ? -1 : b.id === s.voucherId ? 1 : 0))
    .slice(0, 4);
  const [to, setTo] = useState(s.voucherId);
  const [note, setNote] = useState(VOUCH_NOTE);
  const [sent, setSent] = useState(false);
  const [copied, setCopied] = useState(false);
  const link = `https://veritrust.demo/vouch/${s.nodes[me]!.nullifier?.slice(2, 14) ?? 'pending'}`;

  async function send() {
    await api.requestVouch(me, to, note);
    setSent(true);
    setTimeout(() => {
      setSent(false);
      onClose();
    }, 900);
  }

  return (
    <Modal open={open} onClose={onClose} eyebrow="Vouch request" title="Who knows your work?" width={720}>
      <div className="grid gap-0 md:grid-cols-[1fr_230px]">
        <div className="p-6">
          <fieldset>
            <legend className="text-[13px] font-medium">Send to</legend>
            <div className="mt-2 grid gap-2">
              {candidates.map((n) => (
                <label
                  key={n.id}
                  className={`flex cursor-pointer items-center gap-3 rounded-[10px] border px-3 py-2.5 transition-colors ${
                    to === n.id ? 'border-neel-500 bg-neel-50' : 'border-rule hover:border-rule-2'
                  }`}
                >
                  <input type="radio" name="voucher" value={n.id} checked={to === n.id} onChange={() => setTo(n.id)} className="sr-only" />
                  <Avatar node={n} size={32} />
                  <span className="flex-1">
                    <span className="block text-[14px] font-medium">{n.name}</span>
                    <span className="block text-[12px] text-ink-3">
                      {n.role} · capacity {fmt(n.capacity)}
                    </span>
                  </span>
                  {to === n.id ? <IconCheck size={18} className="text-neel-700" /> : null}
                </label>
              ))}
            </div>
          </fieldset>
          <label htmlFor="note" className="mt-5 block text-[13px] font-medium">
            Why they can vouch for you
          </label>
          <textarea
            id="note"
            rows={3}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="mt-2 w-full resize-none rounded-[8px] border border-rule-2 bg-surface p-3 text-[14px] focus:border-neel-500 focus:ring-4 focus:ring-neel-100 focus:outline-none"
          />
          <p className="mt-2 text-[12.5px] text-ink-3">They’ll see exactly what they put at risk before they decide.</p>
          <Button className="mt-5 w-full" size="lg" onClick={() => void send()} disabled={sent} icon={sent ? <IconCheck size={17} /> : <IconVouch size={17} />}>
            {sent ? 'Request sent' : `Send to ${s.nodes[to]?.name.split(' ')[0]}`}
          </Button>
        </div>
        <aside className="flex flex-col items-center border-t border-rule bg-paper p-6 text-center md:border-t-0 md:border-l">
          <p className="eyebrow">Or share in person</p>
          <div className="mt-4 rounded-[12px] border border-rule bg-surface p-3">
            <QrCode value={link} size={150} />
          </div>
          <p className="mt-3 max-w-full truncate font-mono text-[11px] text-ink-3">{link.replace('https://', '')}</p>
          <button
            type="button"
            onClick={() => {
              void navigator.clipboard?.writeText(link);
              setCopied(true);
              setTimeout(() => setCopied(false), 1400);
            }}
            className="mt-2 inline-flex items-center gap-1.5 text-[12.5px] font-medium text-neel-700 hover:underline"
          >
            {copied ? <IconCheck size={14} /> : <IconCopy size={14} />} {copied ? 'Copied' : 'Copy link'}
          </button>
        </aside>
      </div>
    </Modal>
  );
}

/** A lone dashed node with faint possible edges: someone the graph has not met yet. */
function EmptyNode() {
  return (
    <svg viewBox="0 0 180 130" className="w-full max-w-[180px]" aria-hidden>
      <defs>
        <pattern id="empty-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
          <rect width="6" height="6" fill="#ECEEF7" />
          <rect width="1.4" height="6" fill="#C9D0EC" />
        </pattern>
      </defs>
      {[
        [28, 26],
        [152, 32],
        [150, 108],
        [24, 104],
      ].map(([x, y], i) => (
        <g key={i}>
          <line x1={x} y1={y} x2={90} y2={66} stroke="#C9C2B4" strokeDasharray="2 5" />
          <circle cx={x} cy={y} r={7} fill="#FBFAF6" stroke="#C9C2B4" strokeDasharray="2 3" />
        </g>
      ))}
      <circle cx={90} cy={66} r={22} fill="url(#empty-hatch)" stroke="#7C7F87" strokeWidth={1.6} strokeDasharray="4 4" />
      <text x={90} y={70} textAnchor="middle" fontSize="11" fontFamily="IBM Plex Sans" fontWeight={600} fill="#16181F">
        you
      </text>
    </svg>
  );
}
