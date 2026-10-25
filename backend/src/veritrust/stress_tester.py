"""Monte Carlo Stress Tester for VeriTrust Loan Portfolios.

Simulates thousands of stochastic financial scenarios using reproducible seeded
pseudo-random sampling (no machine learning required). Evaluates default probability,
worst-case residual cash under stress, and the exact income shock tolerance boundary.
"""

from decimal import Decimal, ROUND_HALF_UP
import random
from typing import Literal, Optional
from pydantic import BaseModel, Field

from veritrust.affordability import quantize_inr


class StressTestScenarioConfig(BaseModel):
    """Configurable assumptions for Monte Carlo stress testing."""

    n_simulations: int = Field(default=5000, description="Number of Monte Carlo paths to generate")
    income_volatility: Decimal = Field(
        default=Decimal("0.15"), description="Coefficient of variation of monthly income (stddev / mean)"
    )
    unexpected_expense_prob: Decimal = Field(
        default=Decimal("0.10"), description="Probability of an unexpected emergency expense per month"
    )
    unexpected_expense_mean: Decimal = Field(
        default=Decimal("4000.00"), description="Mean cost of an emergency expense event in INR"
    )
    unexpected_expense_std: Decimal = Field(
        default=Decimal("2000.00"), description="Standard deviation of emergency expense in INR"
    )
    income_delay_prob: Decimal = Field(
        default=Decimal("0.05"), description="Probability of client payment delay in informal/gig receivables"
    )
    random_seed: int = Field(default=42, description="Fixed seed ensuring 100% reproducible sampling")


class StressTestReport(BaseModel):
    """Synthesized results from Monte Carlo financial stress simulation."""

    n_simulations: int
    tenure_months: int
    monthly_emi: Decimal
    baseline_income: Decimal
    baseline_essential_expenses: Decimal
    initial_cash_buffer: Decimal
    shortfall_probability: Decimal  # Fraction of scenarios experiencing cash deficit
    shortfall_frequency_pct: Decimal  # e.g. 4.2%
    residual_cash_median: Decimal
    residual_cash_p05: Decimal  # 5th percentile (adverse scenario cushion)
    worst_case_deficit: Decimal
    shock_tolerance_pct: Decimal  # Max income percentage drop borrower can absorb
    affordability_break_income: Decimal  # Exact income floor where repayment becomes unaffordable
    stress_rating: Literal["RESILIENT", "MODERATE", "FRAGILE"]
    resilience_summary: str
    reproducibility_seed: int
    currency: str = "INR"


class MonteCarloStressTester:
    """Simulates monthly cash flows across thousands of stochastic shock realizations."""

    def __init__(self, config: Optional[StressTestScenarioConfig] = None) -> None:
        self.config = config or StressTestScenarioConfig()

    def stress_test(
        self,
        monthly_income: Decimal,
        essential_expenses: Decimal,
        monthly_emi: Decimal,
        tenure_months: int,
        initial_cash_buffer: Decimal = Decimal("3000.00"),
        override_config: Optional[StressTestScenarioConfig] = None,
    ) -> StressTestReport:
        """Run reproducible Monte Carlo simulations across the loan tenure."""
        cfg = override_config or self.config
        rng = random.Random(cfg.random_seed)

        income_f = float(monthly_income)
        expenses_f = float(essential_expenses)
        emi_f = float(monthly_emi)
        buffer_f = float(initial_cash_buffer)
        vol_f = float(cfg.income_volatility)
        shock_p = float(cfg.unexpected_expense_prob)
        shock_mean_f = float(cfg.unexpected_expense_mean)
        shock_std_f = float(cfg.unexpected_expense_std)
        delay_p = float(cfg.income_delay_prob)

        # Pre-calculate analytical breaking point
        # Affordability break point: monthly income where I - Expenses - EMI = 0
        break_income_f = expenses_f + emi_f
        affordability_break_income = quantize_inr(Decimal(str(max(0.0, break_income_f))))

        # Shock tolerance: percentage income drop borrower can absorb before monthly deficit
        if income_f > 0:
            cushion_f = income_f - expenses_f - emi_f
            tolerance_f = max(0.0, (cushion_f / income_f) * 100.0)
            shock_tolerance_pct = Decimal(str(round(tolerance_f, 2)))
        else:
            shock_tolerance_pct = Decimal("0.00")

        shortfall_count = 0
        min_residual_balances: list[float] = []

        for _ in range(cfg.n_simulations):
            curr_buffer = buffer_f
            min_bal = float("inf")
            had_shortfall = False
            carried_over_delay_income = 0.0

            for _month in range(tenure_months):
                # 1. Income shock (Gaussian truncated at 0)
                income_multiplier = max(0.0, rng.gauss(1.0, vol_f))
                realized_income = (income_f * income_multiplier) + carried_over_delay_income
                carried_over_delay_income = 0.0

                # 2. Payment delay shock (part of income delayed to next month)
                if rng.random() < delay_p:
                    delayed_amt = realized_income * 0.40
                    realized_income -= delayed_amt
                    carried_over_delay_income = delayed_amt

                # 3. Unexpected emergency expense shock
                unexpected_expense = 0.0
                if rng.random() < shock_p:
                    unexpected_expense = max(0.0, rng.gauss(shock_mean_f, shock_std_f))

                # 4. Monthly cash flow and residual balance
                total_liquid_cash = curr_buffer + realized_income - expenses_f - unexpected_expense

                if total_liquid_cash < emi_f:
                    had_shortfall = True
                    deficit = emi_f - total_liquid_cash
                    curr_buffer = 0.0
                    min_bal = min(min_bal, -deficit)
                else:
                    curr_buffer = total_liquid_cash - emi_f
                    min_bal = min(min_bal, curr_buffer)

            if had_shortfall:
                shortfall_count += 1
            min_residual_balances.append(min_bal)

        # Statistical Aggregations
        shortfall_prob_f = shortfall_count / float(cfg.n_simulations)
        shortfall_probability = Decimal(str(round(shortfall_prob_f, 4)))
        shortfall_frequency_pct = Decimal(str(round(shortfall_prob_f * 100.0, 2)))

        min_residual_balances.sort()
        idx_p05 = int(0.05 * len(min_residual_balances))
        idx_p50 = int(0.50 * len(min_residual_balances))

        p05_val = Decimal(str(round(min_residual_balances[idx_p05], 2)))
        median_val = Decimal(str(round(min_residual_balances[idx_p50], 2)))
        worst_val = Decimal(str(round(min_residual_balances[0], 2)))

        # Assign Stress Rating
        if shortfall_prob_f <= 0.05:
            stress_rating = "RESILIENT"
            summary = (
                f"Highly resilient loan plan. Across {cfg.n_simulations:,} Monte Carlo scenarios, "
                f"cash shortfall occurred in only {shortfall_frequency_pct}% of cases. "
                f"Borrower can absorb a {shock_tolerance_pct}% income drop before defaulting."
            )
        elif shortfall_prob_f <= 0.15:
            stress_rating = "MODERATE"
            summary = (
                f"Moderately sensitive loan plan with {shortfall_frequency_pct}% projected shortfall risk under adverse shocks. "
                f"Under the 5th percentile adverse scenario, cash buffer reaches INR {p05_val:,.2f}. "
                "Consider extending tenure to reduce monthly pressure."
            )
        else:
            stress_rating = "FRAGILE"
            summary = (
                f"Fragile loan plan under economic stress ({shortfall_frequency_pct}% shortfall probability). "
                f"Income volatility and emergency shocks deplete the cash buffer down to INR {p05_val:,.2f}. "
                f"Borrower has only {shock_tolerance_pct}% income shock cushion before repayment becomes unaffordable."
            )

        return StressTestReport(
            n_simulations=cfg.n_simulations,
            tenure_months=tenure_months,
            monthly_emi=quantize_inr(monthly_emi),
            baseline_income=quantize_inr(monthly_income),
            baseline_essential_expenses=quantize_inr(essential_expenses),
            initial_cash_buffer=quantize_inr(initial_cash_buffer),
            shortfall_probability=shortfall_probability,
            shortfall_frequency_pct=shortfall_frequency_pct,
            residual_cash_median=quantize_inr(median_val),
            residual_cash_p05=quantize_inr(p05_val),
            worst_case_deficit=quantize_inr(worst_val),
            shock_tolerance_pct=shock_tolerance_pct,
            affordability_break_income=affordability_break_income,
            stress_rating=stress_rating,
            resilience_summary=summary,
            reproducibility_seed=cfg.random_seed,
        )

    def compare_plans(
        self,
        monthly_income: Decimal,
        essential_expenses: Decimal,
        plan_a_emi: Decimal,
        plan_a_tenure: int,
        plan_b_emi: Decimal,
        plan_b_tenure: int,
        plan_a_name: str = "Plan A (Requested)",
        plan_b_name: str = "Plan B (Restructured)",
        initial_cash_buffer: Decimal = Decimal("3000.00"),
    ) -> "PlanComparativeStressReport":
        """Compare two loan plans under the EXACT same pseudo-random economic futures."""
        report_a = self.stress_test(
            monthly_income=monthly_income,
            essential_expenses=essential_expenses,
            monthly_emi=plan_a_emi,
            tenure_months=plan_a_tenure,
            initial_cash_buffer=initial_cash_buffer,
        )

        report_b = self.stress_test(
            monthly_income=monthly_income,
            essential_expenses=essential_expenses,
            monthly_emi=plan_b_emi,
            tenure_months=plan_b_tenure,
            initial_cash_buffer=initial_cash_buffer,
        )

        delta_shortfall = report_b.shortfall_frequency_pct - report_a.shortfall_frequency_pct
        delta_cash_p05 = report_b.residual_cash_p05 - report_a.residual_cash_p05

        if delta_shortfall < Decimal("0.0"):
            verdict = f"{plan_b_name} IS SIGNIFICANTLY SAFER"
            summary = (
                f"{plan_b_name} reduces default shortfall risk by {abs(delta_shortfall)}% "
                f"(from {report_a.shortfall_frequency_pct}% down to {report_b.shortfall_frequency_pct}%) "
                f"and improves the 5th-percentile adverse cash buffer by INR {delta_cash_p05:,.2f} "
                f"across {self.config.n_simulations:,} identical stochastic economic scenarios."
            )
        elif delta_shortfall > Decimal("0.0"):
            verdict = f"{plan_a_name} HAS LOWER DEFAULT RISK"
            summary = (
                f"{plan_a_name} exhibits lower shortfall risk ({report_a.shortfall_frequency_pct}% vs {report_b.shortfall_frequency_pct}%), "
                f"retaining INR {abs(delta_cash_p05):,.2f} more cash cushion in adverse scenarios."
            )
        else:
            verdict = "BOTH PLANS EXHIBIT EQUAL RESILIENCE"
            summary = (
                f"Both plans show identical {report_a.shortfall_frequency_pct}% shortfall probability under stress."
            )

        return PlanComparativeStressReport(
            plan_a_name=plan_a_name,
            plan_b_name=plan_b_name,
            plan_a_report=report_a,
            plan_b_report=report_b,
            delta_shortfall_pct=delta_shortfall,
            delta_residual_cash_p05=delta_cash_p05,
            risk_reduction_verdict=verdict,
            tradeoff_summary=summary,
            simulations_evaluated=self.config.n_simulations,
        )


class PlanComparativeStressReport(BaseModel):
    """Side-by-side comparative stress testing report for two loan plans under identical scenarios."""

    plan_a_name: str
    plan_b_name: str
    plan_a_report: StressTestReport
    plan_b_report: StressTestReport
    delta_shortfall_pct: Decimal  # Shortfall_B - Shortfall_A (negative means B is safer)
    delta_residual_cash_p05: Decimal  # Cash_B - Cash_A (positive means B has higher cushion)
    risk_reduction_verdict: str
    tradeoff_summary: str
    simulations_evaluated: int
