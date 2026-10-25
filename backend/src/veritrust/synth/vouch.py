"""Stage 1c: the vouch graph. Endorsements are time-stamped events; the score is a replay.

Why the vouch can carry information the bureau loses: endorsers know the borrower's latent
reliability (discipline) and community depth (support capacity). A shock moves the bureau score
through missed EMIs and new enquiries, but it tells endorsers nothing new about the person, so
reliable borrowers keep their endorsers and unreliable ones see them walk away. Endorsers also
help when cash runs short (simulate.py), which is the mechanism behind any difference in default.

Score (Vouch scoring proposal): w = R/100 * h * exp(-lambda * U) * g and S = 100 * (1 - exp(-W/tau)).
A reciprocal edge (the borrower endorses the endorser back, the ring pattern) keeps only
RING_PENALTY of its edge quality. Stakes are reputation points, never money. All weights Decimal.
"""

import random
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from . import params as P
from .model import Borrower, month_label
from .people import pick, poisson

W6 = Decimal("0.000001")
R4 = Decimal("0.0001")
STATE_CODES = sorted(P.STATES)


def q6(value: Decimal) -> str:
    return str(value.quantize(W6, rounding=ROUND_HALF_UP))


def q4(value: Decimal) -> str:
    return str(value.quantize(R4, rounding=ROUND_HALF_UP))


@dataclass
class Voucher:
    voucher_id: str
    kind: str                 # PERSON or INSTITUTION (an employer or SHG federation)
    reputation: Decimal       # R, 0..100
    reliability: Decimal      # h, 0..1
    budget: Decimal           # reputation points available to stake
    committed: Decimal = Decimal(0)
    cluster: str = ""


@dataclass
class Edge:
    vouch_id: str
    voucher: Voucher
    recipient_id: str
    relationship: str
    months_known: int
    stake: Decimal
    utilisation: Decimal      # U at the time of staking
    quality: Decimal          # g before any abuse penalty
    created: int
    expiries: list[int] = field(default_factory=list)   # each scheduled expiry; renewed unless last
    ended: int | None = None
    end_action: str = ""      # WITHDRAWN or EXPIRED
    reciprocal: bool = False

    def active(self, month: int) -> bool:
        return self.created <= month and (self.ended is None or month < self.ended)


class VoucherPool:
    """Endorsers shared by every borrower in one run.

    A voucher's attributes come from its own RNG, so it is the same person in every run. Staked
    points are a ledger across borrowers in id order: a stake that would exceed the voucher's
    budget is refused (proposal section 5), so no voucher is ever over-committed.
    """

    def __init__(self) -> None:
        self._vouchers: dict[str, Voucher] = {}

    def person(self, state: str, slot: int) -> Voucher:
        voucher_id = f"V{STATE_CODES.index(state):02d}{slot:05d}"
        if voucher_id not in self._vouchers:
            rng = random.Random(f"{P.SEED}:voucher:{voucher_id}")
            institution = rng.random() < P.P_INSTITUTION
            reputation = rng.uniform(80, 95) if institution else rng.triangular(45, 95, 78)
            reliability = rng.uniform(0.9, 1.0) if institution else min(1.0, max(0.5, rng.betavariate(8, 1.6)))
            self._vouchers[voucher_id] = Voucher(
                voucher_id=voucher_id, kind="INSTITUTION" if institution else "PERSON",
                reputation=Decimal(repr(round(reputation, 2))), reliability=Decimal(repr(round(reliability, 4))),
                budget=Decimal(rng.randint(*P.VOUCH_BUDGET)), cluster=voucher_id)
        return self._vouchers[voucher_id]

    def ring_account(self, borrower_id: str, n: int, rng: random.Random) -> Voucher:
        """A new account created to endorse one borrower; all share the borrower's ring cluster."""
        voucher = Voucher(
            voucher_id=f"R{borrower_id[1:]}{n:02d}", kind="PERSON",
            reputation=Decimal(repr(round(rng.uniform(40, 60), 2))),
            reliability=Decimal(repr(round(rng.uniform(0.4, 0.6), 4))),
            budget=Decimal(100), cluster=f"RING-{borrower_id}")
        self._vouchers[voucher.voucher_id] = voucher
        return voucher

    def stake(self, voucher: Voucher, points: Decimal) -> Decimal | None:
        """Commit points; returns the voucher's utilisation U after staking, or None if refused."""
        if voucher.committed + points > voucher.budget:
            return None
        voucher.committed += points
        return voucher.committed / voucher.budget


def _schedule(edge: Edge, horizon: int, rng: random.Random) -> list[int]:
    """Expiry months, renewing with P_RENEW each time, until one is not renewed or past horizon."""
    expiry = edge.created + rng.randint(*P.VOUCH_EXPIRY)
    expiries = [expiry]
    while expiry <= horizon and rng.random() < P.P_RENEW:
        expiry += rng.randint(*P.VOUCH_EXPIRY)
        expiries.append(expiry)
    return expiries


def plan_vouches(b: Borrower, pool: VoucherPool, rng: random.Random) -> tuple[list[Edge], list[Edge]]:
    """Endorsements received by `b` and, for ring cases, the edges `b` gives back.

    Count rises with support capacity and discipline (people vouch for those they trust). After a
    shock, each endorser walks away with probability P_WITHDRAW_AFTER_SHOCK * (1 - discipline)^2.
    """
    b.support_capacity = rng.betavariate(2.0, 2.0)
    horizon = b.app_month + P.PERFORMANCE_MONTHS
    received: list[Edge] = []
    given: list[Edge] = []

    def add_edge(voucher: Voucher, relationship: str, created: int, quality: float, reciprocal: bool = False) -> None:
        points = Decimal(rng.randint(*P.VOUCH_STAKE))
        utilisation = pool.stake(voucher, points)
        if utilisation is None:
            return
        edge = Edge(vouch_id=f"{b.borrower_id}-V{len(received) + 1:02d}", voucher=voucher,
                    recipient_id=b.borrower_id, relationship=relationship,
                    months_known=rng.randint(6, 240), stake=points, utilisation=utilisation,
                    quality=Decimal(repr(round(quality, 4))), created=created, reciprocal=reciprocal)
        edge.expiries = _schedule(edge, horizon, rng)
        received.append(edge)

    if rng.random() < P.VOUCH_COVERAGE[b.segment]:
        count = 1 + poisson(rng, 12.0 * b.support_capacity * (0.3 + 0.7 * b.discipline))
        for _ in range(count):
            voucher = pool.person(b.state, rng.randrange(P.VOUCHERS_PER_STATE))
            if voucher.kind == "INSTITUTION":
                relationship = "COLLEAGUE" if b.segment == "salaried_formal" else "COMMUNITY"
            else:
                relationship = pick(rng, {"FAMILY": 0.25, "NEIGHBOUR": 0.25, "COMMUNITY": 0.2,
                                          "TRADE": 0.15, "COLLEAGUE": 0.15})
            low, high = P.VOUCH_RELATIONSHIPS[relationship]
            created = b.app_month - rng.randint(*P.VOUCH_AGE)
            add_edge(voucher, relationship, created, rng.uniform(low, high))

    if b.discipline < 0.45 and rng.random() < P.P_RING:
        burst = b.app_month - rng.randint(1, 3)
        for n in range(rng.randint(*P.RING_SIZE)):
            account = pool.ring_account(b.borrower_id, n + 1, rng)
            add_edge(account, "COMMUNITY", burst, rng.uniform(0.75, 0.95), reciprocal=True)
            back = Edge(vouch_id=f"{b.borrower_id}-G{n + 1:02d}", voucher=Voucher(
                voucher_id=b.borrower_id, kind="PERSON", reputation=Decimal(0), reliability=Decimal(0),
                budget=Decimal(0)), recipient_id=account.voucher_id, relationship="COMMUNITY",
                months_known=rng.randint(0, 3), stake=Decimal(0), utilisation=Decimal(0),
                quality=Decimal(0), created=burst, reciprocal=True)
            back.expiries = [burst + 12]
            given.append(back)

    for edge in received:
        # Background churn, then the scheduled expiry if the endorsement was not renewed.
        for month in range(edge.created + 1, horizon + 1):
            if rng.random() < P.P_WITHDRAW_MONTHLY:
                edge.ended, edge.end_action = month, "WITHDRAWN"
                break
        last = edge.expiries[-1]
        if last <= horizon and (edge.ended is None or last < edge.ended):
            edge.ended, edge.end_action = last, "EXPIRED"

    plan = b.shock
    if plan:
        p_leave = P.P_WITHDRAW_AFTER_SHOCK * (1.0 - b.discipline) ** 2
        for edge in received:
            if edge.active(plan.start) and not edge.reciprocal and rng.random() < p_leave:
                month = plan.start + rng.randint(1, 3)
                if edge.ended is None or month < edge.ended:
                    edge.ended, edge.end_action = month, "WITHDRAWN"
    return received, given


def edge_weight(edge: Edge) -> Decimal:
    """w = R/100 * h * exp(-lambda * U) * g, with g cut to RING_PENALTY on a reciprocal edge."""
    quality = edge.quality * (P.RING_PENALTY if edge.reciprocal else 1)
    return (edge.voucher.reputation / 100 * edge.voucher.reliability
            * (-P.VOUCH_LAMBDA * edge.utilisation).exp() * quality)


def score_at(edges: list[Edge], month: int) -> dict:
    """The vouch score row for one month: replay of the events up to and including `month`."""
    eligible = [e for e in edges if e.active(month)]
    weights = [edge_weight(e) for e in eligible]
    total = sum(weights, Decimal(0))
    if not eligible:
        return {"vouch_score": "", "vouch_status": P.NO_RECORD, "eligible_incoming": 0,
                "total_weight": q6(Decimal(0)), "distinct_anchors": 0, "max_contributor_share": "",
                "reciprocal_edges": 0, "cluster_concentration": "", "mean_voucher_reliability": ""}
    score = (100 * (1 - (-total / P.VOUCH_TAU).exp())).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    by_cluster: dict[str, Decimal] = {}
    for edge, weight in zip(eligible, weights):
        by_cluster[edge.voucher.cluster] = by_cluster.get(edge.voucher.cluster, Decimal(0)) + weight
    established = len(eligible) >= 3 and min(e.created for e in eligible) <= month - 6
    return {
        "vouch_score": int(score),
        "vouch_status": "ESTABLISHED" if established else "PROVISIONAL",
        "eligible_incoming": len(eligible),
        "total_weight": q6(total),
        "distinct_anchors": sum(1 for e in eligible if e.voucher.kind == "INSTITUTION"),
        "max_contributor_share": q4(max(weights) / total) if total else "",
        "reciprocal_edges": sum(1 for e in eligible if e.reciprocal),
        "cluster_concentration": q4(max(by_cluster.values()) / total) if total else "",
        "mean_voucher_reliability": q4(sum(e.voucher.reliability for e in eligible) / len(eligible)),
    }


def weight_by_month(edges: list[Edge], months: range) -> dict[int, list[float]]:
    """Each active endorsement's weight per month, as plain numbers, used only for the support
    probability: each endorser can be hit by the same disaster as the borrower (simulate.py)."""
    return {m: [float(edge_weight(e)) for e in edges if e.active(m)] for m in months}


def event_rows(b: Borrower, received: list[Edge], given: list[Edge]) -> list[dict]:
    """CREATED, RENEWED, WITHDRAWN and EXPIRED events, oldest first."""
    rows = []
    for edge in received + given:
        base = {"borrower_id": b.borrower_id, "voucher_id": edge.voucher.voucher_id,
                "recipient_id": edge.recipient_id, "relationship": edge.relationship,
                "months_known": edge.months_known, "voucher_kind": edge.voucher.kind,
                "commitment_points": str(edge.stake), "voucher_budget_points": str(edge.voucher.budget),
                "utilisation_at_stake": q4(edge.utilisation),
                "consented": 1}
        stamps = [("CREATED", edge.created, edge.expiries[0])]
        stamps += [("RENEWED", edge.expiries[i], edge.expiries[i + 1]) for i in range(len(edge.expiries) - 1)
                   if edge.ended is None or edge.expiries[i] < edge.ended]
        if edge.ended is not None:
            stamps.append((edge.end_action, edge.ended, edge.ended))
        for action, month, expires in stamps:
            rows.append({"vouch_event_id": "", "vouch_id": edge.vouch_id, "action": action,
                         "event_month": month_label(month), "expires_month": month_label(expires), **base})
    rows.sort(key=lambda r: (r["event_month"], r["vouch_id"], r["action"]))
    for n, row in enumerate(rows, start=1):
        row["vouch_event_id"] = f"{b.borrower_id}-VE{n:03d}"
    return rows


def outcome_rows(b: Borrower, received: list[Edge], application_id: str, defaulted: bool,
                 settled: bool, default_month: str, rng: random.Random) -> list[dict]:
    """One row per endorsement active when the loan was taken, with the reputation update.

    delta = learning_rate * w * (y - p) * evidence_reliability (developer documentation). No
    update while an outcome is ongoing, disputed and open, or overturned on appeal.
    """
    rows = []
    for edge in received:
        if not edge.active(b.app_month) or edge.reciprocal:
            continue
        status = "DEFAULTED" if defaulted else "SETTLED" if settled else "ONGOING"
        dispute = "NONE"
        if defaulted and rng.random() < P.P_DISPUTE:
            dispute = rng.choice(("OPEN", "UPHELD", "REJECTED"))
        y = "" if status == "ONGOING" or dispute == "UPHELD" else (1 if status == "SETTLED" else 0)
        delta = Decimal(0)
        if y != "" and dispute != "OPEN":
            delta = P.VOUCH_LEARNING_RATE * edge_weight(edge) * (Decimal(y) - P.VOUCH_EXPECTED_REPAY)
        rows.append({
            "vouch_id": edge.vouch_id, "application_id": application_id, "borrower_id": b.borrower_id,
            "voucher_id": edge.voucher.voucher_id, "loan_status": status,
            "settled_month": default_month if defaulted else "", "y": y,
            "p_expected": str(P.VOUCH_EXPECTED_REPAY), "edge_weight": q6(edge_weight(edge)),
            "delta_reputation": q6(delta), "dispute_status": dispute,
        })
    return rows
