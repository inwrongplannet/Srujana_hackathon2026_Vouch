"""Community platform endpoints: asks, KNOWN and EVIDENCE vouches, setbacks and consent.

State is in memory and reseeded on restart (`veritrust.community.CommunityStore`). There is no
login yet: the caller names the voucher or owner, as the demo does. Scores and weights are decimal
strings; stakes are reputation points, never money.
"""

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from veritrust.community import (
    Ask,
    CommunityScore,
    CommunityStore,
    Member,
    Vouch,
    community_score,
    track_record,
    weight,
)

router = APIRouter(prefix="/api/v1/community", tags=["Community"])
_store = CommunityStore()


def reset_community() -> CommunityStore:
    """Reseed the community (tests and demo resets)."""
    global _store
    _store = CommunityStore()
    return _store


def _q(value: Decimal | None, places: str = "0.0001") -> str | None:
    return None if value is None else str(value.quantize(Decimal(places)))


class MemberView(BaseModel):
    id: str
    name: str
    line: str
    reputation: str
    budget: str
    committed: str
    free: str
    resolved: int
    repaid: int
    track_record: str


class ScoreView(BaseModel):
    score: str | None = Field(description="0-100, or null when nobody has vouched (not zero)")
    known_weight: str
    evidence_weight: str
    evidence_counted: str
    total_weight: str


class VouchView(BaseModel):
    voucher_id: str
    kind: Literal["KNOWN", "EVIDENCE"]
    stake: str
    relationship: str | None = None
    years_known: int | None = None
    utilisation: str | None = None
    weight: str


class VerifiedView(BaseModel):
    key: str
    label: str
    detail: str
    tone: Literal["ok", "gap", "warn"]
    shown: bool


class SetbackView(BaseModel):
    posted: str
    text: str
    responses: dict[str, Literal["PENDING", "STAND_BY", "STEP_BACK"]]


class AskView(BaseModel):
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
    verified: list[VerifiedView] = Field(description="All items for the owner; only shown ones for anyone else")
    thin_file: bool
    bureau_status: Literal["NO_FILE", "AVAILABLE"]
    bureau_trail: list[int] | None = None
    expected_repay: str
    vouches: list[VouchView]
    score: ScoreView
    setback: SetbackView | None = None
    known_by: list[str]
    viewer_knows: bool = Field(description="True when the viewer is in this person's circle")


class VouchBody(BaseModel):
    voucher_id: str
    kind: Literal["KNOWN", "EVIDENCE"]
    stake: str = Field(description="Reputation points, a decimal string")
    relationship: Literal["FAMILY", "NEIGHBOUR", "COLLEAGUE", "TRADE", "COMMUNITY"] | None = None
    years_known: int | None = Field(default=None, ge=0, le=60)
    read_verified: bool = Field(default=False, description="EVIDENCE only: the voucher confirms they read the summary")


class PreviewView(BaseModel):
    weight: str
    utilisation: str
    score_before: str | None = None
    score_after: str
    gain_if_repaid: str
    loss_if_default: str


class SetbackBody(BaseModel):
    text: str


class RespondBody(BaseModel):
    voucher_id: str
    choice: Literal["STAND_BY", "STEP_BACK"]


class ShownBody(BaseModel):
    shown: bool


def _member_view(m: Member) -> MemberView:
    return MemberView(
        id=m.id, name=m.name, line=m.line, reputation=str(m.reputation), budget=str(m.budget),
        committed=str(m.committed), free=str(m.budget - m.committed), resolved=m.resolved, repaid=m.repaid,
        track_record=_q(track_record(m)),
    )


def _score_view(s: CommunityScore) -> ScoreView:
    return ScoreView(
        score=_q(s.score, "0.1"), known_weight=_q(s.known), evidence_weight=_q(s.evidence),
        evidence_counted=_q(s.evidence_counted), total_weight=_q(s.total),
    )


def _ask_view(a: Ask, viewer_id: str | None) -> AskView:
    members = _store.members
    owner = viewer_id == a.owner_id
    return AskView(
        id=a.id, owner_id=a.owner_id, name=a.name, trade=a.trade, place=a.place, circle=a.circle,
        purpose=a.purpose, amount_band=a.amount_band, posted_days=a.posted_days, story=a.story,
        verified=[VerifiedView(**vars(v)) for v in a.verified if owner or v.shown],
        thin_file=a.thin_file, bureau_status=a.bureau_status, bureau_trail=a.bureau_trail,
        expected_repay=str(a.expected_repay),
        vouches=[
            VouchView(
                voucher_id=v.voucher_id, kind=v.kind, stake=str(v.stake), relationship=v.relationship,
                years_known=v.years_known, utilisation=_q(v.utilisation), weight=_q(weight(members[v.voucher_id], v)),
            )
            for v in a.vouches
        ],
        score=_score_view(community_score(members, a.vouches)),
        setback=SetbackView(**vars(a.setback)) if a.setback else None,
        known_by=a.known_by,
        viewer_knows=viewer_id in a.known_by if viewer_id else False,
    )


def _vouch(body: VouchBody) -> Vouch:
    try:
        stake = Decimal(body.stake)
    except ArithmeticError:
        raise HTTPException(status_code=422, detail="stake must be a decimal string.")
    return Vouch(voucher_id=body.voucher_id, kind=body.kind, stake=stake,
                 relationship=body.relationship, years_known=body.years_known)


def _ask_or_404(ask_id: str) -> Ask:
    try:
        return _store.ask(ask_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Ask '{ask_id}' not found.")


@router.get("/members", response_model=list[MemberView])
def list_members():
    """Everyone who can vouch, with their budget and smoothed track record."""
    return [_member_view(m) for m in _store.members.values()]


@router.get("/asks", response_model=list[AskView])
def list_asks(viewer_id: str | None = Query(default=None)):
    """The feed. Strangers see only the verified items each borrower chose to show."""
    return [_ask_view(a, viewer_id) for a in _store.asks.values()]


@router.get("/asks/{ask_id}", response_model=AskView)
def get_ask(ask_id: str, viewer_id: str | None = Query(default=None)):
    """One ask, as `viewer_id` sees it."""
    return _ask_view(_ask_or_404(ask_id), viewer_id)


@router.post("/asks/{ask_id}/vouch-preview", response_model=PreviewView)
def preview_vouch(ask_id: str, body: VouchBody):
    """What a vouch would do before it is given: its weight, the score change and the reward at stake."""
    _ask_or_404(ask_id)
    try:
        p = _store.preview(ask_id, _vouch(body))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return PreviewView(
        weight=_q(p["weight"]), utilisation=_q(p["utilisation"]),
        score_before=_q(p["before"].score, "0.1"), score_after=_q(p["after"].score, "0.1"),
        gain_if_repaid=_q(p["gain"], "0.01"), loss_if_default=_q(p["loss"], "0.01"),
    )


@router.post("/asks/{ask_id}/vouches", response_model=AskView, status_code=status.HTTP_201_CREATED)
def vouch(ask_id: str, body: VouchBody):
    """Stake reputation on someone, as someone who knows them (KNOWN) or on their evidence (EVIDENCE)."""
    _ask_or_404(ask_id)
    if body.kind == "EVIDENCE" and not body.read_verified:
        raise HTTPException(status_code=400, detail="An evidence vouch needs read_verified: true.")
    try:
        ask = _store.vouch(ask_id, _vouch(body))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _ask_view(ask, body.voucher_id)


@router.post("/asks/{ask_id}/setback", response_model=AskView)
def post_setback(ask_id: str, body: SetbackBody):
    """The borrower reports a setback; each KNOWN voucher then stands by or steps back."""
    _ask_or_404(ask_id)
    try:
        ask = _store.post_setback(ask_id, body.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _ask_view(ask, ask.owner_id)


@router.post("/asks/{ask_id}/setback/respond", response_model=AskView)
def respond_setback(ask_id: str, body: RespondBody):
    """Stand by keeps the vouch; step back withdraws it and frees the stake."""
    _ask_or_404(ask_id)
    try:
        ask = _store.respond(ask_id, body.voucher_id, body.choice)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _ask_view(ask, body.voucher_id)


@router.post("/asks/{ask_id}/verified/{key}", response_model=AskView)
def set_shown(ask_id: str, key: str, body: ShownBody):
    """The borrower's consent: show or hide one verified item from strangers."""
    _ask_or_404(ask_id)
    try:
        ask = _store.set_shown(ask_id, key, body.shown)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _ask_view(ask, ask.owner_id)
