"""Tests for the rule-based affordability engine.

Verifies:
- Formula D = I - E - B
- Policy caps (FOIR/ITI <= 40%, DTI <= 50%)
- Precautionary buffers for unverified/thin-file data
- Strict separation between epistemic uncertainty and low economic capacity
- Loan plan feasibility checks and exact EMI calculations
"""

from decimal import Decimal
import pytest

from veritrust.affordability import (
    AffordabilityEngine,
    AffordabilityInput,
    AffordabilityResult,
    calculate_emi,
)


def test_calculate_emi_known_values():
    """Verify standard amortization formula with known financial benchmark."""
    # Principal: 100,000 INR, Rate: 12% p.a. (1% monthly), Tenure: 12 months
    p = Decimal("100000.00")
    r = Decimal("0.12")
    n = 12
    emi = calculate_emi(p, r, n)
    assert emi == Decimal("8884.88")

    # Zero interest edge case
    zero_emi = calculate_emi(p, Decimal("0.0"), 10)
    assert zero_emi == Decimal("10000.00")


def test_affordability_formula_disposable_income():
    """Verify D = I - E - B where B = I * buffer_pct."""
    engine = AffordabilityEngine()

    data = AffordabilityInput(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("20000.00"),
        existing_debt_service=Decimal("5000.00"),
        buffer_percentage=Decimal("0.15"),
        min_buffer_floor=Decimal("3000.00"),
        max_iti_foir=Decimal("0.50"),
        max_dti=Decimal("0.60"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )

    res = engine.evaluate(data)

    # I = 50,000
    # total non discretionary = 20,000 + 5,000 = 25,000
    # B = 50,000 * 0.15 = 7,500
    # D = 50,000 - 25,000 - 7,500 = 17,500
    assert res.monthly_income == Decimal("50000.00")
    assert res.effective_buffer == Decimal("7500.00")
    assert res.disposable_income == Decimal("17500.00")
    assert res.is_affordable is True
    assert res.data_reliability == "VERIFIED_COMPLETE"


def test_affordability_policy_caps_binding_dti():
    """Test that max affordable instalment is constrained by DTI cap."""
    engine = AffordabilityEngine()

    data = AffordabilityInput(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("15000.00"),
        existing_debt_service=Decimal("8000.00"),
        buffer_percentage=Decimal("0.10"),  # B = 5,000
        min_buffer_floor=Decimal("3000.00"),
        max_iti_foir=Decimal("0.40"),        # ITI cap = 20,000
        max_dti=Decimal("0.50"),             # DTI cap max total = 25,000; remaining after 8,000 debt = 17,000
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )

    res = engine.evaluate(data)

    # D = 50,000 - 23,000 - 5,000 = 22,000
    # ITI cap = 20,000
    # DTI allowed = 25,000 - 8,000 = 17,000
    # Min(22000, 20000, 17000) = 17000 (DTI_CAP)
    assert res.max_affordable_emi == Decimal("17000.00")
    assert res.binding_policy_rule == "DTI_CAP"


def test_separation_of_unreliable_data_from_low_affordability():
    """Verify that incomplete or unverified data does NOT artificially report zero economic capacity,
    but applies a transparent precautionary buffer and explicit flags.
    """
    engine = AffordabilityEngine()

    unverified_input = AffordabilityInput(
        monthly_income=Decimal("40000.00"),
        essential_expenses=Decimal("16000.00"),
        existing_debt_service=Decimal("0.00"),
        min_buffer_floor=Decimal("3000.00"),
        buffer_percentage=Decimal("0.15"),
        data_completeness=Decimal("0.40"),  # Thin file (< 0.50)
        is_verified=False,
    )

    res = engine.evaluate(unverified_input)

    assert res.data_reliability == "THIN_FILE_UNVERIFIED"
    assert len(res.unreliability_notes) >= 1
    # Base buffer: 15% of 40k = 6,000. Precautionary buffer (1.30x): 7,800.
    assert res.effective_buffer == Decimal("7800.00")
    # Economic capacity is still calculated explicitly:
    assert res.max_affordable_emi > Decimal("0.00")
    assert res.is_affordable is True


def test_insolvent_negative_disposable_income():
    """Verify that borrowers with non-discretionary expenses exceeding income are flagged as unaffordable."""
    engine = AffordabilityEngine()

    overburdened = AffordabilityInput(
        monthly_income=Decimal("20000.00"),
        essential_expenses=Decimal("18000.00"),
        existing_debt_service=Decimal("5000.00"),  # Total out = 23,000 > 20,000
        min_buffer_floor=Decimal("3000.00"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )

    res = engine.evaluate(overburdened)

    assert res.is_affordable is False
    assert res.max_affordable_emi == Decimal("0.00")
    assert res.disposable_income < Decimal("0.00")
    assert len(res.rejection_reasons) > 0


def test_validate_plan():
    """Verify validate_plan marks feasible vs infeasible plans and gives descriptive reasons."""
    engine = AffordabilityEngine()

    data = AffordabilityInput(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("20000.00"),
        existing_debt_service=Decimal("0.00"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )

    # Affordable loan: 50,000 over 12m at 10% -> EMI ~ 4,395.79 <= max_affordable_emi (20,000)
    is_valid, emi, res, violations = engine.validate_plan(
        inp=data,
        proposed_principal=Decimal("50000.00"),
        annual_rate=Decimal("0.10"),
        tenure_months=12,
    )
    assert is_valid is True
    assert len(violations) == 0
    assert emi == Decimal("4395.79")

    # Infeasible loan: 200,000 over 6m at 10% -> EMI ~ 34,312.28 > max_affordable_emi (20,000)
    bad_valid, bad_emi, bad_res, bad_violations = engine.validate_plan(
        inp=data,
        proposed_principal=Decimal("200000.00"),
        annual_rate=Decimal("0.10"),
        tenure_months=6,
    )
    assert bad_valid is False
    assert len(bad_violations) > 0
    assert "exceeds maximum affordable instalment" in bad_violations[0]
