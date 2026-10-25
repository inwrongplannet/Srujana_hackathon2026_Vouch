"""Protocol actions the frontend's story needs: asking for a vouch, the lender's decision, and a
default with its slashing cascade. None of these import the OR-Tools optimizer.

Vouch requests live in memory like applications (lost on restart); endorsements, loans and
reputations are saved to the store. Money is a decimal string in INR.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from veritrust.api import registry
from veritrust.api.deps import get_services

router = APIRouter(prefix="/api/v1")

RequestStatus = Literal["PENDING", "ACCEPTED", "DECLINED"]


class CreateVouchRequest(BaseModel):
    requester_id: str
    voucher_id: str
    note: str = ""


class RespondVouchRequest(BaseModel):
    accept: bool


class VouchRequestResponse(BaseModel):
    request_id: str
    requester_id: str
    voucher_id: str
    note: str
    status: RequestStatus
    endorsement_id: str | None = None
    created_at: str


class DecisionRequest(BaseModel):
    # APPROVE_AT_LIMIT lends the smaller of the amount asked and the borrower's current limit.
    decision: Literal["APPROVE", "APPROVE_AT_LIMIT", "DECLINE"]


class LoanView(BaseModel):
    loan_id: str
    borrower_id: str
    principal: str
    outstanding_balance: str
    interest_rate: str
    tenure_months: int
    status: str


class DecisionResponse(BaseModel):
    application_id: str
    status: str  # APPROVED or REJECTED
    loan: LoanView | None = None


class DefaultRequest(BaseModel):
    delta0: str | None = None  # reputation slashed from the defaulter; config default when omitted


class Penalty(BaseModel):
    user_id: str
    level: int  # 0 defaulter, 1 direct sponsor, 2 sponsor's sponsor
    reputation_before: str
    reputation_after: str
    status_after: str


class DefaultResponse(BaseModel):
    loan_id: str
    status: str
    delta0: str
    penalties: list[Penalty]


_requests: dict[str, VouchRequestResponse] = {}


def _loan_view(loan) -> LoanView:
    return LoanView(
        loan_id=loan.loan_id,
        borrower_id=loan.borrower_id,
        principal=str(loan.principal),
        outstanding_balance=str(loan.outstanding_balance),
        interest_rate=str(loan.interest_rate),
        tenure_months=loan.tenure_months,
        status=loan.status,
    )


@router.post("/vouch-requests", response_model=VouchRequestResponse, status_code=status.HTTP_201_CREATED, tags=["Endorsements"])
def create_vouch_request(req: CreateVouchRequest):
    """Ask someone to vouch for you; they accept or decline later."""
    engine, _, _, _ = get_services()
    for user_id in (req.requester_id, req.voucher_id):
        if not engine.get_user(user_id):
            raise HTTPException(status_code=404, detail=f"User '{user_id}' does not exist.")
    if req.requester_id == req.voucher_id:
        raise HTTPException(status_code=400, detail="Nobody can vouch for themselves.")
    if engine.graph.has_edge(req.voucher_id, req.requester_id):
        raise HTTPException(status_code=409, detail=f"'{req.voucher_id}' already vouches for '{req.requester_id}'.")
    if any(r.status == "PENDING" and r.requester_id == req.requester_id and r.voucher_id == req.voucher_id for r in _requests.values()):
        raise HTTPException(status_code=409, detail="A request between these two is already pending.")
    record = VouchRequestResponse(
        request_id=f"VREQ_{uuid.uuid4().hex[:8].upper()}",
        requester_id=req.requester_id,
        voucher_id=req.voucher_id,
        note=req.note,
        status="PENDING",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    _requests[record.request_id] = record
    return record


@router.get("/vouch-requests", response_model=list[VouchRequestResponse], tags=["Endorsements"])
def list_vouch_requests(
    voucher_id: str | None = Query(default=None),
    requester_id: str | None = Query(default=None),
    request_status: Annotated[RequestStatus | None, Query(alias="status")] = None,
):
    """Requests filtered by who asked, who was asked, and status (all filters optional)."""
    return [
        r for r in _requests.values()
        if (voucher_id is None or r.voucher_id == voucher_id)
        and (requester_id is None or r.requester_id == requester_id)
        and (request_status is None or r.status == request_status)
    ]


@router.post("/vouch-requests/{request_id}/respond", response_model=VouchRequestResponse, tags=["Endorsements"])
def respond_vouch_request(request_id: str, req: RespondVouchRequest):
    """Accept (creates the endorsement, weights conserved) or decline a pending request."""
    record = _requests.get(request_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Vouch request '{request_id}' not found.")
    if record.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Vouch request '{request_id}' is already {record.status}.")
    if not req.accept:
        record.status = "DECLINED"
        return record
    engine, _, lending, store = get_services()
    try:
        vouch = engine.vouch(source_id=record.voucher_id, target_id=record.requester_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.save(engine, lending)
    record.status = "ACCEPTED"
    record.endorsement_id = vouch.vouch_id
    return record


@router.post("/applications/{app_id}/decision", response_model=DecisionResponse, tags=["Applications"])
def decide_application(app_id: str, req: DecisionRequest):
    """The lender approves (disbursing the loan within the borrower's limit) or declines."""
    app = registry.applications.get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    if app.status in ("APPROVED", "REJECTED", "FUNDED"):
        raise HTTPException(status_code=409, detail=f"Application '{app_id}' is already {app.status}.")
    if req.decision == "DECLINE":
        app.status = "REJECTED"
        return DecisionResponse(application_id=app_id, status=app.status)

    engine, scorer, lending, store = get_services()
    amount = app.principal
    if req.decision == "APPROVE_AT_LIMIT":
        amount = min(app.principal, scorer.assess_credit(app.borrower_id).max_loan_limit)
        if amount <= Decimal("0.00"):
            raise HTTPException(status_code=400, detail="The borrower's current limit is INR 0: nothing can be offered yet.")
    try:
        loan = lending.borrow(app.borrower_id, amount, tenure_months=app.term_months, interest_rate=app.annual_rate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.save(engine, lending)
    app.status = "APPROVED"
    return DecisionResponse(application_id=app_id, status=app.status, loan=_loan_view(loan))


@router.post("/loans/{loan_id}/default", response_model=DefaultResponse, tags=["Loans"])
def default_loan(loan_id: str, req: DefaultRequest):
    """Record a default and apply the damped slashing cascade (k = 0, 1, 2; nothing at k >= 3)."""
    engine, _, lending, store = get_services()
    loan = lending.get_loan(loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail=f"Loan '{loan_id}' does not exist.")
    try:
        delta0 = Decimal(req.delta0) if req.delta0 is not None else lending.default_base_slash
    except InvalidOperation:
        raise HTTPException(status_code=422, detail="delta0 must be a decimal string.")

    # Who sits at each level is read before the cascade, which zeroes the defaulter's out-edges.
    borrower = loan.borrower_id
    sponsors = list(engine.graph.predecessors(borrower))
    ancestors = {a for s in sponsors for a in engine.graph.predecessors(s) if a != borrower and a not in sponsors}
    levels = {borrower: 0, **{s: 1 for s in sponsors}, **{a: 2 for a in ancestors}}
    before = {uid: engine.get_user(uid).reputation for uid in levels}

    try:
        lending.default_loan(loan_id, delta0=delta0)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    store.save(engine, lending)

    penalties = []
    for uid, level in sorted(levels.items(), key=lambda kv: (kv[1], kv[0])):
        user = engine.get_user(uid)
        penalties.append(Penalty(
            user_id=uid,
            level=level,
            reputation_before=str(before[uid]),
            reputation_after=str(user.reputation),
            status_after=user.status,
        ))
    return DefaultResponse(loan_id=loan_id, status=loan.status, delta0=str(delta0), penalties=penalties)
