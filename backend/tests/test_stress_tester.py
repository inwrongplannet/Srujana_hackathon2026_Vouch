"""Tests for the Monte Carlo Stress Tester.

Verifies:
- 100% deterministic reproducibility via seeded random generator (no ML)
- Computation of shortfall probability and adverse 5th-percentile cash
- Calculation of income shock tolerance percentage and analytical break income
- Stress rating classification (RESILIENT, MODERATE, FRAGILE)
"""

from decimal import Decimal
import pytest

from veritrust.stress_tester import MonteCarloStressTester, StressTestScenarioConfig


def test_stress_tester_reproducibility():
    """Verify that identical random seed produces bit-for-bit identical results."""
    tester = MonteCarloStressTester(StressTestScenarioConfig(n_simulations=1000, random_seed=42))

    run1 = tester.stress_test(
        monthly_income=Decimal("40000.00"),
        essential_expenses=Decimal("20000.00"),
        monthly_emi=Decimal("8000.00"),
        tenure_months=6,
        initial_cash_buffer=Decimal("5000.00"),
    )

    run2 = tester.stress_test(
        monthly_income=Decimal("40000.00"),
        essential_expenses=Decimal("20000.00"),
        monthly_emi=Decimal("8000.00"),
        tenure_months=6,
        initial_cash_buffer=Decimal("5000.00"),
    )

    assert run1.shortfall_probability == run2.shortfall_probability
    assert run1.shortfall_frequency_pct == run2.shortfall_frequency_pct
    assert run1.residual_cash_p05 == run2.residual_cash_p05
    assert run1.residual_cash_median == run2.residual_cash_median
    assert run1.worst_case_deficit == run2.worst_case_deficit
    assert run1.stress_rating == run2.stress_rating


def test_stress_tester_break_income_and_shock_tolerance():
    """Verify analytical breaking point and income shock tolerance percentage."""
    tester = MonteCarloStressTester(StressTestScenarioConfig(n_simulations=500, random_seed=42))

    # Income: 50,000, Expenses: 20,000, EMI: 10,000
    # Breaking point = 20,000 + 10,000 = 30,000
    # Cushion = 20,000 -> 20,000 / 50,000 = 40.00%
    report = tester.stress_test(
        monthly_income=Decimal("50000.00"),
        essential_expenses=Decimal("20000.00"),
        monthly_emi=Decimal("10000.00"),
        tenure_months=12,
        initial_cash_buffer=Decimal("7500.00"),
    )

    assert report.affordability_break_income == Decimal("30000.00")
    assert report.shock_tolerance_pct == Decimal("40.00")


def test_stress_tester_fragile_under_tight_cushion():
    """Verify that an aggressive EMI close to disposable income is flagged FRAGILE or MODERATE."""
    tester = MonteCarloStressTester(StressTestScenarioConfig(n_simulations=1000, random_seed=42))

    # Income: 30,000, Expenses: 22,000, EMI: 7,500 (Total out = 29,500 leaving only 500 buffer)
    report = tester.stress_test(
        monthly_income=Decimal("30000.00"),
        essential_expenses=Decimal("22000.00"),
        monthly_emi=Decimal("7500.00"),
        tenure_months=12,
        initial_cash_buffer=Decimal("1000.00"),
    )

    assert report.stress_rating in ("FRAGILE", "MODERATE")
    assert report.shortfall_frequency_pct > Decimal("10.00")
    # Residual cash at 5th percentile is negative (deficit)
    assert report.residual_cash_p05 < Decimal("0.00")


def test_stress_tester_resilient_under_healthy_buffer():
    """Verify that a modest EMI with ample buffer is flagged RESILIENT."""
    tester = MonteCarloStressTester(StressTestScenarioConfig(n_simulations=1000, random_seed=42))

    # Income: 60,000, Expenses: 15,000, EMI: 3,000, Buffer: 20,000
    report = tester.stress_test(
        monthly_income=Decimal("60000.00"),
        essential_expenses=Decimal("15000.00"),
        monthly_emi=Decimal("3000.00"),
        tenure_months=6,
        initial_cash_buffer=Decimal("20000.00"),
    )

    assert report.stress_rating == "RESILIENT"
    assert report.shortfall_probability <= Decimal("0.05")
    assert report.residual_cash_p05 > Decimal("0.00")


def test_compare_plans_under_identical_futures():
    """Verify side-by-side comparison of Plan A (tight tenure) vs Plan B (extended tenure)
    under the exact same stochastic macro realizations.
    """
    tester = MonteCarloStressTester(StressTestScenarioConfig(n_simulations=1000, random_seed=42))

    comparison = tester.compare_plans(
        monthly_income=Decimal("40000.00"),
        essential_expenses=Decimal("20000.00"),
        plan_a_emi=Decimal("15000.00"),  # Aggressive: leaves only 5k cushion
        plan_a_tenure=6,
        plan_b_emi=Decimal("7000.00"),   # Extended: leaves 13k cushion
        plan_b_tenure=12,
        plan_a_name="Plan A (6m)",
        plan_b_name="Plan B (12m)",
    )

    assert comparison.plan_a_name == "Plan A (6m)"
    assert comparison.plan_b_name == "Plan B (12m)"
    assert comparison.delta_shortfall_pct < Decimal("0.0")  # Plan B significantly reduces default risk
    assert comparison.delta_residual_cash_p05 > Decimal("0.0")  # Plan B retains more adverse cushion
    assert "SIGNIFICANTLY SAFER" in comparison.risk_reduction_verdict
    assert "Plan B (12m) reduces default shortfall risk" in comparison.tradeoff_summary
