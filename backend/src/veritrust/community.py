"""Hybrid community vouching: KNOWN (I know this person) and EVIDENCE (I don't, but I read their
verified summary and stake my reputation on it). A Decimal port of
`frontend/src/mocks/engine/community.ts`; its tests use the same known answers.

Both kinds use the Vouch proposal's edge weight, w = R/100 * h * exp(-lambda * U) * g, and score,
S = 100 * (1 - exp(-W / tau)), with tau = 3 and lambda = 1, but h and g mean different things:
- KNOWN: h is the voucher's smoothed track record; g comes from the relationship and the years
  known. It adds private knowledge no dataset has.
- EVIDENCE: the voucher adds judgement, not facts, so h is the track record shrunk to zero until
  JUDGE_MIN_RESOLVED outcomes exist, g is a flat EVIDENCE_QUALITY, and evidence weight is capped at
  EVIDENCE_ONLY_CAP plus EVIDENCE_TO_KNOWN of the known weight, so strangers cannot carry a score.
Stakes are reputation points, never money. Constants are demo values (docs/DECISIONS.md).
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Literal

VouchKind = Literal["KNOWN", "EVIDENCE"]
Relationship = Literal["FAMILY", "NEIGHBOUR", "COLLEAGUE", "TRADE", "COMMUNITY"]
Response = Literal["PENDING", "STAND_BY", "STEP_BACK"]

TAU = Decimal(3)
LAMBDA = Decimal(1)
RELATIONSHIP_QUALITY: dict[str, Decimal] = {
    "FAMILY": Decimal("0.65"),
    "NEIGHBOUR": Decimal("0.80"),
    "COLLEAGUE": Decimal("0.85"),
    "TRADE": Decimal("0.85"),
    "COMMUNITY": Decimal("0.80"),
}
EVIDENCE_QUALITY = Decimal("0.60")
JUDGE_MIN_RESOLVED = 5
EVIDENCE_ONLY_CAP = Decimal("0.60")
EVIDENCE_TO_KNOWN = Decimal(2) / Decimal(3)
LEARNING_RATE = Decimal("0.10")


@dataclass
class Member:
    """Someone who vouches. Reputation R is 0..100; budget and committed are points."""

    id: str
    name: str
    line: str
    reputation: Decimal
    budget: Decimal
    committed: Decimal
    resolved: int
    repaid: int


@dataclass
class Vouch:
    voucher_id: str
    kind: VouchKind
    stake: Decimal
    relationship: Relationship | None = None
    years_known: int | None = None
    # U fixed when the stake was made; later stakes by the same voucher do not reweight it.
    utilisation: Decimal | None = None


@dataclass
class Verified:
    """A platform-computed summary; `shown` is the borrower's consent for strangers to see it."""

    key: str
    label: str
    detail: str
    tone: Literal["ok", "gap", "warn"]
    shown: bool = True


@dataclass
class Setback:
    posted: str
    text: str
    responses: dict[str, Response]


@dataclass
class Ask:
    id: str
    owner_id: str
    name: str
    trade: str
    place: str
    circle: str
    purpose: str
    amount_band: str
    posted_days: int
    story: str
    verified: list[Verified]
    thin_file: bool
    bureau_status: Literal["NO_FILE", "AVAILABLE"]
    bureau_trail: list[int] | None
    expected_repay: Decimal  # expected repayment rate of comparable borrowers
    vouches: list[Vouch] = field(default_factory=list)
    setback: Setback | None = None
    known_by: list[str] = field(default_factory=list)


def track_record(m: Member) -> Decimal:
    """Smoothed share of past vouches that repaid: (repaid + 1) / (resolved + 2); 0.5 with none."""
    return Decimal(m.repaid + 1) / Decimal(m.resolved + 2)


def reliability(m: Member, kind: VouchKind) -> Decimal:
    """h for the vouch kind. Evidence counts only once the voucher has a record to judge them by."""
    record = track_record(m)
    if kind == "KNOWN":
        return record
    return record * min(Decimal(1), Decimal(m.resolved) / Decimal(JUDGE_MIN_RESOLVED))


def quality(v: Vouch) -> Decimal:
    """g: relationship quality, rising from 60% to 100% of it over the first ten years known."""
    if v.kind == "EVIDENCE":
        return EVIDENCE_QUALITY
    base = RELATIONSHIP_QUALITY[v.relationship or "COMMUNITY"]
    years = min(Decimal(10), Decimal(v.years_known or 0))
    return base * (Decimal("0.6") + years / Decimal(10) * Decimal("0.4"))


def utilisation(m: Member, stake: Decimal) -> Decimal | None:
    """U after staking, (committed + stake) / budget, or None when it would exceed the budget."""
    after = m.committed + stake
    return None if after > m.budget else after / m.budget


def staked(m: Member, v: Vouch) -> Vouch:
    """Fixes U at staking time, so the vouch keeps the weight it had when it was given."""
    return replace(v, utilisation=utilisation(m, v.stake) or Decimal(1))


def weight(m: Member, v: Vouch) -> Decimal:
    u = v.utilisation if v.utilisation is not None else (utilisation(m, v.stake) or Decimal(1))
    return m.reputation / Decimal(100) * reliability(m, v.kind) * (-LAMBDA * u).exp() * quality(v)


@dataclass
class CommunityScore:
    score: Decimal | None  # None: no vouches, "insufficient evidence", never 0
    known: Decimal
    evidence: Decimal  # raw evidence weight
    evidence_counted: Decimal  # after the cap
    total: Decimal


def community_score(members: dict[str, Member], vouches: list[Vouch]) -> CommunityScore:
    known = Decimal(0)
    evidence = Decimal(0)
    for v in vouches:
        w = weight(members[v.voucher_id], v)
        if v.kind == "KNOWN":
            known += w
        else:
            evidence += w
    cap = EVIDENCE_ONLY_CAP + known * EVIDENCE_TO_KNOWN
    counted = min(evidence, cap)
    total = known + counted
    score = Decimal(100) * (Decimal(1) - (-total / TAU).exp()) if vouches else None
    return CommunityScore(score=score, known=known, evidence=evidence, evidence_counted=counted, total=total)


def reward_preview(w: Decimal, expected_repay: Decimal) -> tuple[Decimal, Decimal]:
    """(gain if repaid, loss if defaulted) in points: 100 * lr * w * (1 - p) and 100 * lr * w * (0 - p).

    Backing someone everyone expects to repay earns little; backing an underrated borrower who
    repays earns the most.
    """
    scaled = Decimal(100) * LEARNING_RATE * w
    return scaled * (Decimal(1) - expected_repay), -(scaled * expected_repay)


def _v(voucher_id: str, kind: VouchKind, stake: int, relationship: Relationship | None = None,
       years: int | None = None) -> Vouch:
    return Vouch(voucher_id=voucher_id, kind=kind, stake=Decimal(stake), relationship=relationship, years_known=years)


def seed() -> tuple[dict[str, Member], list[Ask]]:
    """The fictional community from `frontend/src/mocks/community.ts`, ids upper-cased like the graph."""
    members = {
        m.id: m for m in (
            Member("MEENA", "Meena Patil", "Kirana store, Old Hubballi", Decimal(82), Decimal(100), Decimal(35), 7, 6),
            Member("RAMESH", "Ramesh Hegde", "Cloth wholesaler, Durgadbail", Decimal(74), Decimal(100), Decimal(40), 12, 11),
            Member("KAVYA", "Kavya Rao", "Tiffin service, Vidyanagar", Decimal(61), Decimal(80), Decimal(10), 1, 1),
            Member("ANAND", "Anand Kulkarni", "Retired bank officer · reads files", Decimal(70), Decimal(100), Decimal(45), 15, 13),
            Member("FARIDA", "Farida Shaikh", "Embroidery unit, Keshwapur", Decimal(68), Decimal(90), Decimal(20), 5, 5),
            Member("BASAVA", "Basavaraj Angadi", "Auto stand union, Gokul Road", Decimal(55), Decimal(80), Decimal(15), 0, 0),
        )
    }
    asks = [
        Ask(
            id="LAKSHMI", owner_id="LAKSHMI", name="Lakshmi Naik", trade="Tailoring unit", place="Hubballi",
            circle="Tailors' Association", purpose="Two industrial sewing machines", amount_band="₹1–2 lakh",
            posted_days=2,
            story="Wedding-season orders are more than two machines can stitch. A third and fourth would let me take school-uniform contracts too.",
            verified=[
                Verified("income", "Income steady for 24 months", "About ₹38,000 a month · bank statement", "ok"),
                Verified("rent", "Rent and chit fund paid 24 of 24 months", "Bank statement", "ok"),
                Verified("fit", "Loan fits her worst month at 24 months", "Stress-tested · EMI about ₹7,931", "ok"),
                Verified("bureau", "No credit bureau file", "Never borrowed formally · recorded as unknown, not bad", "gap"),
            ],
            thin_file=True, bureau_status="NO_FILE", bureau_trail=None, expected_repay=Decimal("0.80"),
            vouches=[_v("RAMESH", "KNOWN", 15, "TRADE", 6), _v("ANAND", "EVIDENCE", 10)],
            known_by=["MEENA", "RAMESH", "KAVYA"],
        ),
        Ask(
            id="SURESH", owner_id="SURESH", name="Suresh Kulkarni", trade="Auto-rickshaw driver", place="Gokul Road",
            circle="Auto stand union", purpose="Refinance a hospital bill into one EMI", amount_band="₹50,000–75,000",
            posted_days=9,
            story="Twelve years on the same stand. My father’s surgery in January took everything I had saved.",
            verified=[
                Verified("income", "Daily fares steady for 18 months", "About ₹32,000 a month · bank statement", "ok"),
                Verified("bureau", "Bureau score 745 → 668 in three months", "Utilisation up, one EMI 30 days late", "warn"),
                Verified("dsr", "Debt service 47% after the new EMI", "Borderline · review obligations", "warn"),
            ],
            thin_file=False, bureau_status="AVAILABLE", bureau_trail=[744, 746, 745, 731, 689, 668],
            expected_repay=Decimal("0.85"),
            vouches=[_v("MEENA", "KNOWN", 15, "NEIGHBOUR", 8), _v("RAMESH", "KNOWN", 10, "COMMUNITY", 5),
                     _v("BASAVA", "KNOWN", 10, "COLLEAGUE", 12), _v("FARIDA", "KNOWN", 10, "COMMUNITY", 4)],
            setback=Setback(
                posted="3 weeks ago",
                text="Hospital bill not covered by insurance. I was 30 days late on one EMI in February and have paid it since. Asking my vouchers to stand by while I refinance.",
                responses={"MEENA": "PENDING", "RAMESH": "STAND_BY", "BASAVA": "STAND_BY", "FARIDA": "STAND_BY"},
            ),
            known_by=["MEENA", "RAMESH", "BASAVA", "FARIDA"],
        ),
        Ask(
            id="FARIDA_ASK", owner_id="FARIDA", name="Farida Shaikh", trade="Embroidery unit", place="Keshwapur",
            circle="Women’s SHG federation", purpose="Working capital for the Eid season", amount_band="₹50,000–1 lakh",
            posted_days=4,
            story="Three repaid loans with the SHG. Bulk orders need thread and zari bought upfront.",
            verified=[
                Verified("income", "Income steady for 36 months", "About ₹41,000 a month", "ok"),
                Verified("bureau", "Bureau score 742, clean for 24 months", "Three closed loans, none late", "ok"),
            ],
            thin_file=False, bureau_status="AVAILABLE", bureau_trail=[728, 731, 735, 738, 740, 742],
            expected_repay=Decimal("0.95"),
            vouches=[_v("KAVYA", "KNOWN", 8, "COMMUNITY", 3)],
            known_by=["KAVYA"],
        ),
        Ask(
            id="IMRAN", owner_id="IMRAN", name="Imran Mulla", trade="Mobile repair stall", place="Old Hubballi",
            circle="Market association", purpose="Stock of spare screens and a soldering station",
            amount_band="₹25,000–50,000", posted_days=1,
            story="Two years at the stall, all cash and UPI. First time asking for a loan.",
            verified=[
                Verified("income", "UPI receipts for 9 months", "About ₹22,000 a month · partial statement", "ok"),
                Verified("bureau", "No credit bureau file", "Never borrowed formally", "gap"),
                Verified("expenses", "Living costs not shared", "Affordability unknown until shared", "gap"),
            ],
            thin_file=True, bureau_status="NO_FILE", bureau_trail=None, expected_repay=Decimal("0.78"),
        ),
    ]
    # Seed vouches keep the utilisation their voucher has today: commitments already include them.
    for ask in asks:
        ask.vouches = [replace(v, utilisation=members[v.voucher_id].committed / members[v.voucher_id].budget) for v in ask.vouches]
    return members, asks


class CommunityStore:
    """In-memory community state for the demo (reseeded on restart). Raises ValueError on a bad action."""

    def __init__(self) -> None:
        self.members, asks = seed()
        self.asks = {a.id: a for a in asks}

    def ask(self, ask_id: str) -> Ask:
        if ask_id not in self.asks:
            raise KeyError(ask_id)
        return self.asks[ask_id]

    def preview(self, ask_id: str, v: Vouch) -> dict:
        """What this vouch would do, without saving it: weight, score before and after, reward."""
        ask = self.ask(ask_id)
        me = self._voucher(ask, v)
        fixed = staked(me, v)
        w = weight(me, fixed)
        before = community_score(self.members, ask.vouches)
        after = community_score(self.members, ask.vouches + [fixed])
        gain, loss = reward_preview(w, ask.expected_repay)
        return {"weight": w, "utilisation": fixed.utilisation, "before": before, "after": after, "gain": gain, "loss": loss}

    def vouch(self, ask_id: str, v: Vouch) -> Ask:
        ask = self.ask(ask_id)
        me = self._voucher(ask, v)
        ask.vouches.append(staked(me, v))
        me.committed += v.stake
        return ask

    def respond(self, ask_id: str, voucher_id: str, choice: Literal["STAND_BY", "STEP_BACK"]) -> Ask:
        """Stand by keeps the vouch (a renewal); step back withdraws it and frees the stake."""
        ask = self.ask(ask_id)
        if not ask.setback or voucher_id not in ask.setback.responses:
            raise ValueError(f"'{voucher_id}' has no pending setback response on '{ask_id}'.")
        if choice == "STEP_BACK":
            gone = next((x for x in ask.vouches if x.voucher_id == voucher_id), None)
            if gone:
                ask.vouches.remove(gone)
                self.members[voucher_id].committed -= gone.stake
        ask.setback.responses[voucher_id] = choice
        return ask

    def post_setback(self, ask_id: str, text: str) -> Ask:
        """The borrower reports a setback; every KNOWN voucher is asked to stand by or step back."""
        ask = self.ask(ask_id)
        if not text.strip():
            raise ValueError("Say what happened: the setback text is empty.")
        ask.setback = Setback(
            posted="just now",
            text=text.strip(),
            responses={x.voucher_id: "PENDING" for x in ask.vouches if x.kind == "KNOWN"},
        )
        return ask

    def set_shown(self, ask_id: str, key: str, shown: bool) -> Ask:
        ask = self.ask(ask_id)
        item = next((x for x in ask.verified if x.key == key), None)
        if not item:
            raise ValueError(f"No verified item '{key}' on '{ask_id}'.")
        item.shown = shown
        return ask

    def _voucher(self, ask: Ask, v: Vouch) -> Member:
        me = self.members.get(v.voucher_id)
        if not me:
            raise ValueError(f"'{v.voucher_id}' is not a community member.")
        if v.voucher_id == ask.owner_id:
            raise ValueError("Nobody can vouch for their own ask.")
        if any(x.voucher_id == v.voucher_id for x in ask.vouches):
            raise ValueError(f"'{v.voucher_id}' already vouches for '{ask.id}'.")
        if v.kind == "KNOWN" and not v.relationship:
            raise ValueError("A KNOWN vouch names the relationship.")
        if v.kind == "EVIDENCE" and not any(x.shown for x in ask.verified):
            raise ValueError(f"'{ask.id}' shows strangers nothing verified yet, so there is no evidence to vouch on.")
        if v.stake <= 0 or utilisation(me, v.stake) is None:
            raise ValueError(f"Stake {v.stake} is outside '{v.voucher_id}''s free budget of {me.budget - me.committed} points.")
        return me
