"""FastAPI route handlers implementing the Vouch / VeriTrust REST API specification."""

from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from veritrust.affordability import AffordabilityEngine, AffordabilityInput
from veritrust.api.deps import get_services
from veritrust.counterfactual import CounterfactualSimulator
from veritrust.models import (
    BureauStatus,
    CombinedAssessment,
    Evidence,
    FinancialFeatures,
    LoanApplication,
    User,
)
from veritrust.optimizer import LoanOptimizer, OptimizationResult
from veritrust.recourse import BorrowerRecourseWorkflow, DisputeCase
from veritrust.stress_tester import MonteCarloStressTester

router = APIRouter()

# In-memory registry for loan applications and assessments
_applications: dict[str, LoanApplication] = {}
_assessments: dict[str, CombinedAssessment] = {}


# -----------------------------------------------------------------------------
# Request & Response Schemas
# -----------------------------------------------------------------------------

class CreateApplicationRequest(BaseModel):
    borrower_id: str
    principal: str
    annual_rate: float = 0.12
    term_months: int = 12
    purpose_category: str = "WORKING_CAPITAL"


class ApplicationResponse(BaseModel):
    application_id: str
    borrower_id: str
    principal: str
    term_months: int
    status: str
    created_at: str


class RegisterEvidenceRequest(BaseModel):
    evidence_type: str = "BANK_STATEMENT"
    source: str = "ACCOUNT_AGGREGATOR"
    uri_or_hash: str = ""
    confidence: float = 0.95
    description: str


class CreateEndorsementRequest(BaseModel):
    endorser_id: str
    recipient_id: str
    application_id: Optional[str] = None
    statement: str = ""
    verification_quality: float = 1.0
    edge_eligibility: float = 1.0
    relevance: float = 1.0
    abuse_penalty: float = 0.0


class EndorsementResponse(BaseModel):
    endorsement_id: str
    endorser_id: str
    recipient_id: str
    allocated_weight: str
    status: str
    created_at: str


class VouchSummaryResponse(BaseModel):
    user_id: str
    vouch_score: float
    confidence_rating: str
    eligible_endorsement_count: int
    reputation_capacity: str
    active_incoming_paths: int


class RunAssessmentRequest(BaseModel):
    objective: str = "MIN_COST"  # "MIN_COST" or "MAX_PRINCIPAL"
    enable_stress_test: bool = True
    simulation_scenarios: int = 5000
    bureau_score: Optional[int] = None
    bureau_status: BureauStatus = "NO_FILE"


class ScenarioSimRequest(BaseModel):
    simulated_income: Optional[str] = None
    simulated_expenses: Optional[str] = None
    simulated_principal: Optional[str] = None
    simulated_tenure: Optional[int] = None


class DisputeRequest(BaseModel):
    record_id: str
    record_type: str = "TRANSACTION"
    reason: str = "Contested factual error"
    borrower_id: Optional[str] = None


class CreateUserRequest(BaseModel):
    user_id: str
    name: str
    reputation: str = "0.0"
    is_anchor: bool = False
    monthly_income: Optional[str] = None
    monthly_debt: Optional[str] = None
    net_operating_income: Optional[str] = None
    debt_service: Optional[str] = None
    income_volatility: Optional[str] = None


class RepayLoanRequest(BaseModel):
    loan_id: str
    amount: str


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get("/health", tags=["System"])
def health_check():
    """Health check endpoint exposing no secrets or sensitive parameters."""
    return {
        "status": "OK",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/v1/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED, tags=["Applications"])
def create_application(req: CreateApplicationRequest):
    """Create loan application and validate amount, rate and term."""
    engine, _, _, _ = get_services()
    user = engine.get_user(req.borrower_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Borrower '{req.borrower_id}' does not exist.")

    app_id = f"APP_{uuid.uuid4().hex[:8].upper()}"
    app = LoanApplication(
        application_id=app_id,
        borrower_id=req.borrower_id,
        principal=Decimal(req.principal),
        annual_rate=Decimal(str(req.annual_rate)),
        term_months=req.term_months,
        purpose_category=req.purpose_category,
        status="SUBMITTED",
    )
    _applications[app_id] = app
    return ApplicationResponse(
        application_id=app.application_id,
        borrower_id=app.borrower_id,
        principal=str(app.principal),
        term_months=app.term_months,
        status=app.status,
        created_at=app.created_at.isoformat(),
    )


@router.post("/api/v1/applications/{app_id}/evidence", status_code=status.HTTP_201_CREATED, tags=["Applications"])
def register_evidence(app_id: str, req: RegisterEvidenceRequest):
    """Register consented evidence metadata linked to a loan application."""
    if app_id not in _applications:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")

    evid_id = f"EVID_{uuid.uuid4().hex[:8].upper()}"
    evidence = Evidence(
        evidence_id=evid_id,
        evidence_type=req.evidence_type,  # type: ignore
        uri_or_hash=req.uri_or_hash,
        description=req.description,
        recorded_by=_applications[app_id].borrower_id,
    )
    return {
        "evidence_id": evid_id,
        "application_id": app_id,
        "status": "REGISTERED",
        "verified_at": evidence.timestamp.isoformat(),
    }


@router.post("/api/v1/endorsements", response_model=EndorsementResponse, status_code=status.HTTP_201_CREATED, tags=["Endorsements"])
def create_endorsement(req: CreateEndorsementRequest):
    """Issue peer endorsement; enforce identity, consent, and exposure limits."""
    engine, _, lending, store = get_services()
    try:
        vouch = engine.vouch(
            source_id=req.endorser_id,
            target_id=req.recipient_id,
        )
        store.save(engine, lending)
        return EndorsementResponse(
            endorsement_id=vouch.vouch_id,
            endorser_id=vouch.source,
            recipient_id=vouch.target,
            allocated_weight=str(vouch.weight),
            status="ACTIVE",
            created_at=vouch.created_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/users/{user_id}/vouch-summary", response_model=VouchSummaryResponse, tags=["Endorsements"])
def get_vouch_summary(user_id: str):
    """Return score, confidence, and eligible incoming endorsements."""
    engine, scorer, _, _ = get_services()
    user = engine.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' does not exist.")

    vouch_report = scorer.compute_vouch_score(user_id)
    in_edges = list(engine.graph.in_edges(user_id))

    return VouchSummaryResponse(
        user_id=user_id,
        vouch_score=float(vouch_report.vouch_score),
        confidence_rating=vouch_report.confidence,
        eligible_endorsement_count=vouch_report.eligible_endorsements,
        reputation_capacity=str(user.capacity),
        active_incoming_paths=len(in_edges),
    )


@router.post("/api/v1/applications/{app_id}/assessments", tags=["Assessments"])
def run_assessment(app_id: str, req: RunAssessmentRequest):
    """Run affordability, OR-Tools restructuring, stress testing, and explainability."""
    engine, scorer, _, _ = get_services()
    app = _applications.get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")

    # 1. Combined side-by-side assessment
    combined = scorer.assess_combined(
        borrower_id=app.borrower_id,
        loan_app=app,
        bureau_score=req.bureau_score,
        bureau_status=req.bureau_status,
    )
    _assessments[combined.assessment_id] = combined

    # 2. Dual-axis credit score & limit
    dual_axis = scorer.assess_credit(app.borrower_id)

    # 3. Google OR-Tools optimization
    fin = engine.get_user(app.borrower_id).financial_features  # type: ignore
    monthly_income = fin.monthly_income if fin else Decimal("0.0")
    monthly_debt = fin.monthly_debt if fin else Decimal("0.0")
    essential_expenses = fin.net_operating_income if fin and fin.net_operating_income > 0 else Decimal("10000.00")

    aff_input = AffordabilityInput(
        monthly_income=monthly_income,
        essential_expenses=essential_expenses,
        existing_debt_service=monthly_debt,
    )
    aff_engine = AffordabilityEngine()
    aff_profile = aff_engine.evaluate(aff_input)

    optimizer = LoanOptimizer(affordability_engine=aff_engine)
    opt_result = optimizer.optimize(
        affordability_input=aff_input,
        requested_principal=app.principal,
        requested_tenure_months=app.term_months,
        annual_rate=app.annual_rate,
        max_approved_credit_limit=dual_axis.max_loan_limit,
        objective=req.objective,  # type: ignore
    )

    # 4. Monte Carlo stress test
    stress_report = None
    best_opt = opt_result.best_feasible_alternative or (opt_result.original_request if opt_result.is_original_feasible else None)
    if req.enable_stress_test:
        from veritrust.affordability import calculate_emi
        from veritrust.stress_tester import StressTestScenarioConfig
        tester = MonteCarloStressTester(
            config=StressTestScenarioConfig(n_simulations=req.simulation_scenarios, random_seed=42)
        )
        plan_emi = best_opt.monthly_emi if best_opt else calculate_emi(app.principal, app.annual_rate, app.term_months)
        plan_tenure = best_opt.tenure_months if best_opt else app.term_months
        stress_report = tester.stress_test(
            monthly_income=monthly_income,
            essential_expenses=essential_expenses + monthly_debt,
            monthly_emi=plan_emi,
            tenure_months=plan_tenure,
        )

    verdict = "APPROVED" if opt_result.is_original_feasible else "RESTRUCTURED_ALTERNATIVE"

    return {
        "assessment_id": combined.assessment_id,
        "application_id": app_id,
        "borrower_id": app.borrower_id,
        "verdict": verdict,
        "bureau_status": combined.bureau.status,
        "bureau_score": combined.bureau.score,
        "vouch_score": float(combined.vouch.vouch_score),
        "affordability": {
            "disposable_income": str(aff_profile.disposable_income),
            "max_affordable_emi": str(aff_profile.max_affordable_emi),
            "protected_cash_buffer": str(aff_profile.protected_buffer),
            "status": aff_profile.binding_policy_rule,
        },
        "best_plan": {
            "principal": str(best_opt.principal) if best_opt else None,
            "term_months": best_opt.tenure_months if best_opt else None,
            "monthly_emi": str(best_opt.monthly_emi) if best_opt else None,
            "total_interest": str(best_opt.total_interest) if best_opt else None,
        } if best_opt else None,
        "stress_resilience": {
            "rating": stress_report.stress_rating,
            "shortfall_probability": float(stress_report.shortfall_probability),
            "adverse_5th_percentile_cash": str(stress_report.residual_cash_p05),
            "income_shock_tolerance_percent": float(stress_report.shock_tolerance_pct),
        } if stress_report else None,
        "positive_factors": combined.positive_factors,
        "risk_factors": combined.risk_factors,
        "missing_information": combined.missing_information,
        "review_flags": combined.review_flags,
    }


@router.get("/api/v1/assessments/{asm_id}", tags=["Assessments"])
def get_assessment(asm_id: str):
    """Retrieve full combined assessment and audit explanation by ID."""
    if asm_id not in _assessments:
        raise HTTPException(status_code=404, detail=f"Assessment '{asm_id}' not found.")
    return _assessments[asm_id].model_dump(mode="json")


@router.post("/api/v1/assessments/{asm_id}/scenarios", tags=["Assessments"])
def run_scenario(asm_id: str, req: ScenarioSimRequest):
    """Run counterfactual simulation without modifying the base assessment."""
    if asm_id not in _assessments:
        raise HTTPException(status_code=404, detail=f"Assessment '{asm_id}' not found.")

    combined = _assessments[asm_id]
    engine, scorer, _, _ = get_services()
    user = engine.get_user(combined.borrower_id)
    if not user:
        raise HTTPException(status_code=404, detail="Borrower not found.")

    fin = user.financial_features
    income = Decimal(req.simulated_income) if req.simulated_income else (fin.monthly_income if fin else Decimal("35000.00"))
    expenses = Decimal(req.simulated_expenses) if req.simulated_expenses else Decimal("12000.00")
    debt = fin.monthly_debt if fin else Decimal("5000.00")
    principal = Decimal(req.simulated_principal) if req.simulated_principal else Decimal("50000.00")
    tenure = req.simulated_tenure if req.simulated_tenure else 12

    simulator = CounterfactualSimulator()
    report = simulator.simulate(
        monthly_income=income,
        essential_expenses=expenses,
        existing_debt=debt,
        requested_principal=principal,
        requested_tenure_months=tenure,
        max_approved_credit_limit=Decimal("500000.00"),
    )

    residual = report.comparison_table[0].residual_monthly_cash if report.comparison_table else Decimal("0.0")

    return {
        "base_assessment_id": asm_id,
        "is_feasible": report.is_requested_feasible,
        "monthly_emi": str(report.requested_plan.monthly_emi),
        "residual_cash": str(residual),
        "income_shock_margin": str(report.required_income_increase),
        "binding_constraint": report.binding_constraint,
        "summary": report.explanation_narrative,
    }


@router.post("/api/v1/endorsements/{endorsement_id}/dispute", tags=["Recourse"])
def dispute_endorsement(endorsement_id: str, req: DisputeRequest):
    """File a formal dispute against an endorsement or transaction."""
    engine, scorer, _, _ = get_services()
    workflow = BorrowerRecourseWorkflow(engine, scorer)
    borrower_id = req.borrower_id or "BOB"

    evidence = Evidence(
        evidence_id=f"EVID_DISP_{uuid.uuid4().hex[:8].upper()}",
        evidence_type="CONTESTED_RECORD",
        description=req.reason,
        recorded_by=borrower_id,
    )
    dispute = workflow.file_dispute(
        borrower_id=borrower_id,
        target_record_id=req.record_id,
        target_record_type=req.record_type,
        contestation_reason=req.reason,
        supporting_evidence=evidence,
    )

    return {
        "dispute_id": dispute.dispute_id,
        "target_record_id": dispute.target_record_id,
        "status": dispute.status,
        "created_at": dispute.created_at.isoformat(),
    }


# -----------------------------------------------------------------------------
# Additional Utility Routes for Frontend Integration
# -----------------------------------------------------------------------------

@router.get("/api/v1/users", tags=["Users"])
def list_users():
    """List all registered network nodes with reputation and capacity."""
    engine, _, _, _ = get_services()
    return [
        {
            "user_id": u.user_id,
            "name": u.name,
            "reputation": str(u.reputation),
            "capacity": str(u.capacity),
            "status": u.status,
            "is_anchor": u.is_anchor,
            "n_settled_loans": u.n_settled_loans,
        }
        for u in engine.list_users()
    ]


@router.post("/api/v1/users", status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(req: CreateUserRequest):
    """Register a new user node in the Web-of-Trust graph."""
    engine, _, lending, store = get_services()
    ff = None
    if req.monthly_income:
        ff = FinancialFeatures(
            monthly_income=Decimal(req.monthly_income),
            monthly_debt=Decimal(req.monthly_debt or "0.0"),
            net_operating_income=Decimal(req.net_operating_income or "0.0"),
            debt_service=Decimal(req.debt_service or "0.0"),
            income_volatility=Decimal(req.income_volatility or "0.15"),
        )
    user = engine.create_user(
        user_id=req.user_id,
        name=req.name,
        initial_reputation=Decimal(req.reputation),
        is_anchor=req.is_anchor,
        financial_features=ff,
    )
    store.save(engine, lending)
    return {
        "user_id": user.user_id,
        "name": user.name,
        "reputation": str(user.reputation),
        "capacity": str(user.capacity),
        "status": user.status,
    }


@router.get("/api/v1/loans", tags=["Loans"])
def list_loans():
    """List all active and historical loan contracts."""
    _, _, lending, _ = get_services()
    return [
        {
            "loan_id": l.loan_id,
            "borrower_id": l.borrower_id,
            "lender_id": l.lender_id,
            "principal": str(l.principal),
            "outstanding_balance": str(l.outstanding_balance),
            "interest_rate": str(l.interest_rate),
            "tenure_months": l.tenure_months,
            "status": l.status,
        }
        for l in lending.list_loans()
    ]


@router.post("/api/v1/loans/repay", tags=["Loans"])
def repay_loan(req: RepayLoanRequest):
    """Apply loan repayment and award reputation yield to borrower and sponsors."""
    engine, _, lending, store = get_services()
    try:
        loan = lending.repay(req.loan_id, Decimal(req.amount))
        store.save(engine, lending)
        return {
            "loan_id": loan.loan_id,
            "status": loan.status,
            "outstanding_balance": str(loan.outstanding_balance),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/v1/graph", tags=["Graph"])
def get_graph():
    """Return nodes and weighted edges for Web-of-Trust graph visualization."""
    engine, _, _, _ = get_services()
    nodes = [
        {
            "id": u.user_id,
            "name": u.name,
            "reputation": float(u.reputation),
            "capacity": float(u.capacity),
            "status": u.status,
            "is_anchor": u.is_anchor,
        }
        for u in engine.list_users()
    ]
    edges = [
        {
            "source": u,
            "target": v,
            "weight": float(data.get("weight", 0.0)),
        }
        for u, v, data in engine.graph.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}
