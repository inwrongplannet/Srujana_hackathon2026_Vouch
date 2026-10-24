"""Tests for the Google OR-Tools Loan Optimizer.

Verifies:
- Feasible loan identification with CP-SAT solver
- Automatic restructuring when requested plan violates affordability caps
- Objective function behavior (MIN_COST vs MAX_PRINCIPAL)
- Extraction of binding constraints that disqualified other plans
- Exact calculation of EMI, total interest, and total repayment
"""

from decimal import Decimal
import pytest

from veritrust.affordability import AffordabilityEngine, AffordabilityInput
from veritrust.optimizer import LoanOptimizer


def test_optimizer_feasible_request_min_cost():
    """Verify that a feasible request is solved to OPTIMAL and selected as best plan."""
    engine = AffordabilityEngine()
    optimizer = LoanOptimizer(engine)

    afford_input = AffordabilityInput(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("15000.00"),
        existing_debt_service=Decimal("0.00"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )

    result = optimizer.optimize(
        affordability_input=afford_input,
        requested_principal=Decimal("30000.00"),
        requested_tenure_months=6,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("50000.00"),
        objective="MIN_COST",
    )

    assert result.is_original_feasible is True
    assert result.solver_status == "OPTIMAL"
    assert result.best_feasible_alternative is not None
    # With MIN_COST and requested 30k for 6m, shortest tenure that meets 30k could be 3m if affordable
    assert result.best_feasible_alternative.principal >= Decimal("30000.00")
    assert result.best_feasible_alternative.is_feasible is True
    assert result.best_feasible_alternative.monthly_emi <= result.affordability_summary.max_affordable_emi


def test_optimizer_restructures_infeasible_request():
    """When requested EMI violates disposable income, optimizer finds feasible alternative."""
    engine = AffordabilityEngine()
    optimizer = LoanOptimizer(engine)

    # Max affordable EMI will be ~ 10,750 (Income 35k, expenses 19k, buffer 5.25k)
    afford_input = AffordabilityInput(
        monthly_income=Decimal("35000.00"),
        essential_expenses=Decimal("13000.00"),
        existing_debt_service=Decimal("6000.00"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )

    # Requesting 100,000 for 3 months -> EMI is ~ 33,892, which massively exceeds 10,750
    result = optimizer.optimize(
        affordability_input=afford_input,
        requested_principal=Decimal("100000.00"),
        requested_tenure_months=3,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("100000.00"),
        objective="MIN_COST",
    )

    assert result.is_original_feasible is False
    assert len(result.original_request.infeasibility_reasons) > 0
    assert "exceeds maximum affordable instalment" in result.original_request.infeasibility_reasons[0]

    # Optimizer must have found a viable alternative with longer tenure (e.g. 12m or 18m)
    # where EMI <= max_affordable_emi
    best = result.best_feasible_alternative
    assert best is not None
    assert best.is_feasible is True
    assert best.monthly_emi <= result.affordability_summary.max_affordable_emi
    assert best.tenure_months > 3  # Extended tenure

    # Binding constraints must document the restriction
    assert len(result.binding_constraints) > 0
    assert any("Instalment cap" in bc for bc in result.binding_constraints)


def test_optimizer_max_principal_objective():
    """Verify MAX_PRINCIPAL searches the frontier for the largest sustainable borrowing capacity."""
    engine = AffordabilityEngine()
    optimizer = LoanOptimizer(engine)

    afford_input = AffordabilityInput(
        monthly_income=Decimal("40000.00"),
        essential_expenses=Decimal("15000.00"),
        existing_debt_service=Decimal("0.00"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )

    result = optimizer.optimize(
        affordability_input=afford_input,
        requested_principal=Decimal("20000.00"),
        requested_tenure_months=6,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("80000.00"),
        objective="MAX_PRINCIPAL",
    )

    assert result.solver_status == "OPTIMAL"
    assert result.best_feasible_alternative is not None
    # Max principal should push up to the credit limit ceiling of 80,000
    assert result.best_feasible_alternative.principal == Decimal("80000.00")
    assert result.best_feasible_alternative.monthly_emi <= result.affordability_summary.max_affordable_emi


def test_optimizer_total_cost_accounting():
    """Verify that total repayment equals principal + total interest."""
    engine = AffordabilityEngine()
    optimizer = LoanOptimizer(engine)

    afford_input = AffordabilityInput(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("15000.00"),
        existing_debt_service=Decimal("0.00"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )

    result = optimizer.optimize(
        affordability_input=afford_input,
        requested_principal=Decimal("50000.00"),
        requested_tenure_months=12,
        annual_rate=Decimal("0.12"),
    )

    orig = result.original_request
    assert orig.principal == Decimal("50000.00")
    # Total repayment = EMI * tenure
    expected_repayment = orig.monthly_emi * Decimal(12)
    assert abs(orig.total_repayment - expected_repayment) <= Decimal("0.05")
    # Total interest = Total repayment - principal
    assert orig.total_interest == orig.total_repayment - orig.principal
