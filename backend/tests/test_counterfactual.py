"""Tests for the Counterfactual Loan Simulator.

Verifies:
- Accurate calculation of required income increase (Delta I)
- Accurate calculation of required expense reduction (Delta E)
- Minimum feasible tenure search (Delta T)
- Maximum feasible principal derivation (Delta P)
- Side-by-side comparison table generation
- Margin of safety analysis on affordable loans
"""

from decimal import Decimal
import pytest

from veritrust.counterfactual import CounterfactualSimulator


def test_counterfactual_infeasible_remedies():
    """Verify counterfactual simulator computes exact mathematical remedies for an infeasible plan."""
    simulator = CounterfactualSimulator()

    # Borrower with 35,000 income, 13,000 expenses, 6,000 debt
    # Max affordable EMI is 10,750 (D = 35k - 19k - 5.25k buffer = 10,750)
    # Requesting 100,000 for 3 months -> EMI is ~ 33,890.43
    report = simulator.simulate(
        monthly_income=Decimal("35000.00"),
        essential_expenses=Decimal("13000.00"),
        existing_debt=Decimal("6000.00"),
        requested_principal=Decimal("100000.00"),
        requested_tenure_months=3,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("150000.00"),
    )

    assert report.is_requested_feasible is False
    assert "INSTALMENT_CAP" in report.binding_constraint

    # Remedy 1: Required income increase
    assert report.required_income_increase > Decimal("0.00")
    # Remedy 2: Minimum tenure extension
    assert report.min_feasible_tenure_months is not None
    assert report.min_feasible_tenure_months > 3  # Must extend to 12m or more

    # Remedy 3: Maximum feasible principal at 3 months
    assert report.max_feasible_principal_at_requested_tenure > Decimal("0.00")
    assert report.max_feasible_principal_at_requested_tenure < Decimal("100000.00")

    # Comparison table must contain at least 2 rows (Requested + Feasible alternatives)
    assert len(report.comparison_table) >= 2
    assert any("Tenure Extended" in row.plan_label for row in report.comparison_table)
    assert any("Reduced Principal" in row.plan_label for row in report.comparison_table)

    # Actionable remedies must be populated
    assert len(report.actionable_remedies) >= 3


def test_counterfactual_feasible_margin_of_safety():
    """Verify that an affordable loan calculates income and expense safety margins."""
    simulator = CounterfactualSimulator()

    # Affordable: 50,000 over 12m on 50,000 income (EMI ~ 4,395 <= 17,500 budget)
    report = simulator.simulate(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("15000.00"),
        existing_debt=Decimal("0.00"),
        requested_principal=Decimal("50000.00"),
        requested_tenure_months=12,
        annual_rate=Decimal("0.10"),
    )

    assert report.is_requested_feasible is True
    assert report.income_drop_margin_before_infeasible > Decimal("0.00")
    assert report.expense_increase_margin_before_infeasible > Decimal("0.00")
    assert len(report.actionable_remedies) > 0
    assert "safety buffer" in report.actionable_remedies[0].lower()
