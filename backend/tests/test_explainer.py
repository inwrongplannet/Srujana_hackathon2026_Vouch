"""Tests for the Explanation and Evidence Engine.

Verifies:
- Traceable explanations generated from rules that fired
- Coverage of all 4 orthogonal dimensions:
  1. Financial Capacity
  2. Evidence Reliability
  3. Graph Reputation
  4. Stress-Test Resilience
- Synthesis of narrative restructuring guidance ("exceeds repayment budget by ₹X per month...")
- Correct verdict states (APPROVED, RESTRUCTURED_ALTERNATIVE, REJECTED_UNAFFORDABLE)
"""

from decimal import Decimal
import pytest

from veritrust.affordability import AffordabilityEngine, AffordabilityInput
from veritrust.explainer import ExplanationEngine
from veritrust.models import CreditAssessment, ContributingPath
from veritrust.optimizer import LoanOptimizer
from veritrust.stress_tester import MonteCarloStressTester


def test_explainer_approved_loan():
    """Verify explanation output for an approved loan within financial capacity."""
    engine = AffordabilityEngine()
    optimizer = LoanOptimizer(engine)
    tester = MonteCarloStressTester()
    explainer = ExplanationEngine()

    data = AffordabilityInput(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("15000.00"),
        existing_debt_service=Decimal("0.00"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )
    afford_res = engine.evaluate(data)

    opt_res = optimizer.optimize(
        affordability_input=data,
        requested_principal=Decimal("40000.00"),
        requested_tenure_months=6,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("80000.00"),
        objective="MIN_COST",
    )

    stress_res = tester.stress_test(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("15000.00"),
        monthly_emi=opt_res.original_request.monthly_emi,
        tenure_months=6,
        initial_cash_buffer=afford_res.effective_buffer,
    )

    assessment = CreditAssessment(
        user_id="ALICE",
        r_graph=Decimal("100.00000"),
        s_cashflow=Decimal("50000.00"),
        mu_composite=Decimal("75000.00"),
        sigma2_epistemic=Decimal("0.05"),
        score_final=Decimal("95.00000"),
        max_loan_limit=Decimal("80000.00"),
        contributing_paths=[
            ContributingPath(path=["ANCHOR_BANK", "ALICE"], hop_weights=[Decimal("1.0")], path_trust=Decimal("100.00000"))
        ],
    )

    explanation = explainer.explain(
        affordability=afford_res,
        optimization=opt_res,
        stress_test=stress_res,
        credit_assessment=assessment,
    )

    assert explanation.verdict == "APPROVED"
    assert "approved" in explanation.narrative_summary.lower()

    # Dimension 1: Financial Capacity
    assert explanation.dimension_financial_capacity.status == "APPROVED_WITHIN_BUDGET"
    assert len(explanation.dimension_financial_capacity.key_findings) > 0

    # Dimension 2: Evidence Reliability
    assert explanation.dimension_evidence_reliability.status == "HIGH_CONFIDENCE_VERIFIED"

    # Dimension 3: Graph Reputation
    assert explanation.dimension_graph_reputation.status == "ENDORSED_CREDIBLE"
    assert "ANCHOR_BANK -> ALICE" in explanation.dimension_graph_reputation.key_findings[-1]

    # Dimension 4: Stress-Test Resilience
    assert explanation.dimension_stress_resilience.status in ("RESILIENT", "MODERATE")


def test_explainer_restructured_alternative_narrative():
    """Verify narrative matches user requirement when loan exceeds budget."""
    engine = AffordabilityEngine()
    optimizer = LoanOptimizer(engine)
    tester = MonteCarloStressTester()
    explainer = ExplanationEngine()

    # Borrower with limited disposable income (max affordable EMI ~ 10,750)
    data = AffordabilityInput(
        monthly_income=Decimal("35000.00"),
        essential_expenses=Decimal("13000.00"),
        existing_debt_service=Decimal("6000.00"),
        data_completeness=Decimal("0.85"),
        is_verified=True,
    )
    afford_res = engine.evaluate(data)

    # Request 80,000 for 3 months -> EMI is ~ 27,113 > 10,750
    opt_res = optimizer.optimize(
        affordability_input=data,
        requested_principal=Decimal("80000.00"),
        requested_tenure_months=3,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("100000.00"),
        objective="MIN_COST",
    )

    stress_res = tester.stress_test(
        monthly_income=Decimal("35000.00"),
        essential_expenses=Decimal("19000.00"),
        monthly_emi=opt_res.best_feasible_alternative.monthly_emi,  # type: ignore
        tenure_months=opt_res.best_feasible_alternative.tenure_months,  # type: ignore
        initial_cash_buffer=afford_res.effective_buffer,
    )

    explanation = explainer.explain(
        affordability=afford_res,
        optimization=opt_res,
        stress_test=stress_res,
    )

    assert explanation.verdict == "RESTRUCTURED_ALTERNATIVE"
    # Check exact wording pattern
    assert "The requested loan exceeds the repayment budget by INR" in explanation.narrative_summary
    assert "Extending the tenure" in explanation.narrative_summary
    assert "reduces the monthly instalment" in explanation.narrative_summary
    assert "increasing total interest" in explanation.narrative_summary

    # Actionable restructuring options
    assert len(explanation.restructuring_guidance) > 0
    assert "Extend tenure" in explanation.restructuring_guidance[0]


def test_explainer_thin_file_epistemic_separation():
    """Verify that thin-file documentation is flagged under Evidence Reliability
    without corrupting the financial capacity or rejecting outright.
    """
    engine = AffordabilityEngine()
    optimizer = LoanOptimizer(engine)
    tester = MonteCarloStressTester()
    explainer = ExplanationEngine()

    data = AffordabilityInput(
        monthly_income=Decimal("40000.00"),
        essential_expenses=Decimal("15000.00"),
        existing_debt_service=Decimal("0.00"),
        data_completeness=Decimal("0.40"),  # Thin file
        is_verified=False,
    )
    afford_res = engine.evaluate(data)

    opt_res = optimizer.optimize(
        affordability_input=data,
        requested_principal=Decimal("20000.00"),
        requested_tenure_months=6,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("50000.00"),
        objective="MIN_COST",
    )

    stress_res = tester.stress_test(
        monthly_income=Decimal("40000.00"),
        essential_expenses=Decimal("15000.00"),
        monthly_emi=opt_res.original_request.monthly_emi,
        tenure_months=6,
        initial_cash_buffer=afford_res.effective_buffer,
    )

    explanation = explainer.explain(
        affordability=afford_res,
        optimization=opt_res,
        stress_test=stress_res,
    )

    # Evidence reliability dimension captures the uncertainty
    assert explanation.dimension_evidence_reliability.status == "THIN_FILE_UNVERIFIED"
    assert "Thin-file borrower" in explanation.dimension_evidence_reliability.headline
    # Financial capacity still correctly approves feasible 20k loan
    assert explanation.verdict == "APPROVED"
