"""Counterfactual loan simulator for VeriTrust.

Enables borrowers and underwriters to perform deterministic sensitivity analysis:
- Test counterfactual adjustments across principal, tenure, income, and expenses.
- Compare requested loan with feasible alternatives.
- Display monthly instalment, total interest, and residual disposable income.
- Identify the exact binding constraint causing a plan to fail.
- Explain precisely what financial changes (Delta I, Delta E, Delta T, Delta P)
  would restore feasibility without relying on machine learning.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from pydantic import BaseModel, Field

from veritrust.affordability import (
    AffordabilityEngine,
    AffordabilityInput,
    AffordabilityResult,
    calculate_emi,
    quantize_inr,
)
from veritrust.optimizer import LoanOptimizer, LoanPlanOption, OptimizationResult


class CounterfactualComparisonRow(BaseModel):
    """Side-by-side comparison row for loan counterfactuals."""

    plan_label: str
    principal: Decimal
    tenure_months: int
    monthly_emi: Decimal
    total_interest: Decimal
    total_repayment: Decimal
    residual_monthly_cash: Decimal  # Income - NonDiscretionary - EMI
    is_feasible: bool
    status_summary: str


class CounterfactualReport(BaseModel):
    """Detailed counterfactual report explaining what changes would make a plan feasible."""

    is_requested_feasible: bool
    requested_plan: LoanPlanOption
    binding_constraint: str

    # Required adjustments to achieve feasibility
    required_income_increase: Decimal
    required_expense_reduction: Decimal
    min_feasible_tenure_months: Optional[int]
    max_feasible_principal_at_requested_tenure: Decimal

    # Margin of safety (if already feasible)
    income_drop_margin_before_infeasible: Decimal
    expense_increase_margin_before_infeasible: Decimal

    # Side-by-side comparisons
    comparison_table: list[CounterfactualComparisonRow]

    # Deterministic natural language explanation
    explanation_narrative: str
    actionable_remedies: list[str]
    currency: str = "INR"


class CounterfactualSimulator:
    """Deterministic simulation engine for credit counterfactuals and what-if exploration."""

    def __init__(
        self,
        affordability_engine: Optional[AffordabilityEngine] = None,
        optimizer: Optional[LoanOptimizer] = None,
    ) -> None:
        self.affordability_engine = affordability_engine or AffordabilityEngine()
        self.optimizer = optimizer or LoanOptimizer(self.affordability_engine)

    def simulate(
        self,
        monthly_income: Decimal,
        essential_expenses: Decimal,
        existing_debt: Decimal = Decimal("0.00"),
        requested_principal: Decimal = Decimal("50000.00"),
        requested_tenure_months: int = 6,
        annual_rate: Decimal = Decimal("0.10"),
        max_approved_credit_limit: Optional[Decimal] = None,
        data_completeness: Decimal = Decimal("1.0"),
        is_verified: bool = True,
    ) -> CounterfactualReport:
        """Run deterministic counterfactual analysis for a proposed loan request."""
        afford_input = AffordabilityInput(
            monthly_income=monthly_income,
            essential_expenses=essential_expenses,
            existing_debt_service=existing_debt,
            data_completeness=data_completeness,
            is_verified=is_verified,
        )
        afford_res = self.affordability_engine.evaluate(afford_input)

        limit_ceiling = (
            max_approved_credit_limit
            if max_approved_credit_limit is not None
            else requested_principal * Decimal("2.0")
        )

        # 1. Evaluate Requested Plan
        orig_emi = calculate_emi(requested_principal, annual_rate, requested_tenure_months)
        orig_total = orig_emi * Decimal(requested_tenure_months)
        orig_interest = max(Decimal("0.00"), orig_total - requested_principal)
        residual_cash = monthly_income - (essential_expenses + existing_debt) - orig_emi

        violations: list[str] = []
        binding_constraint = "NONE"

        if not afford_res.is_affordable:
            violations.append("DISPOSABLE_INCOME_DEFICIT")
            binding_constraint = "INSOLVENT_DISPOSABLE_INCOME"
        elif orig_emi > afford_res.max_affordable_emi:
            violations.append("EXCEEDS_AFFORDABLE_EMI")
            binding_constraint = f"INSTALMENT_CAP_{afford_res.binding_policy_rule}"
        elif requested_principal > limit_ceiling:
            violations.append("EXCEEDS_CREDIT_CEILING")
            binding_constraint = "CREDIT_CEILING_LIMIT"

        is_feasible = len(violations) == 0

        requested_plan = LoanPlanOption(
            principal=quantize_inr(requested_principal),
            tenure_months=requested_tenure_months,
            annual_rate=annual_rate,
            monthly_emi=orig_emi,
            total_interest=quantize_inr(orig_interest),
            total_repayment=quantize_inr(orig_total),
            label="Requested Proposal",
            is_feasible=is_feasible,
            infeasibility_reasons=violations,
        )

        # 2. Counterfactual Gap Calculations (What changes make it feasible?)
        # Required Income Increase:
        # Disposable income equation: (I * (1 - buffer_pct)) - E - debt >= EMI
        # (1 - 0.15) * I >= E + debt + EMI => I >= (E + debt + EMI) / 0.85
        buffer_factor = Decimal("1.0") - afford_input.buffer_percentage
        target_income_disposable = (essential_expenses + existing_debt + orig_emi) / buffer_factor
        # ITI cap equation: I * max_iti >= EMI => I >= EMI / max_iti
        target_income_iti = orig_emi / afford_input.max_iti_foir
        target_income_needed = max(target_income_disposable, target_income_iti)
        required_income_inc = quantize_inr(max(Decimal("0.00"), target_income_needed - monthly_income))

        # Required Expense Reduction:
        max_allowed_outflow = monthly_income - afford_res.effective_buffer - orig_emi
        max_allowed_expenses = max_allowed_outflow - existing_debt
        required_expense_cut = quantize_inr(max(Decimal("0.00"), essential_expenses - max_allowed_expenses))

        # Minimum Feasible Tenure:
        # Search candidate tenures up to 72 months to find where EMI <= max_affordable_emi
        min_feasible_t: Optional[int] = None
        for candidate_t in [3, 6, 9, 12, 18, 24, 36, 48, 60, 72]:
            c_emi = calculate_emi(min(requested_principal, limit_ceiling), annual_rate, candidate_t)
            if c_emi <= afford_res.max_affordable_emi and candidate_t >= requested_tenure_months:
                min_feasible_t = candidate_t
                break

        # Maximum Feasible Principal at Requested Tenure:
        # Binary search / stepping for principal where EMI(P, requested_tenure) <= max_affordable_emi and P <= limit_ceiling
        max_feasible_p = Decimal("0.00")
        if afford_res.max_affordable_emi > Decimal("0.00"):
            # Approximate inversion: P ~ EMI / [r_m * (1+r_m)^T / ((1+r_m)^T - 1)]
            r_m = annual_rate / Decimal("12.0")
            if r_m > Decimal("0.0"):
                factor = (Decimal("1.0") + r_m) ** Decimal(str(requested_tenure_months))
                annuity_factor = (r_m * factor) / (factor - Decimal("1.0"))
                raw_p = afford_res.max_affordable_emi / annuity_factor
                max_feasible_p = quantize_inr(min(raw_p, limit_ceiling))
            else:
                max_feasible_p = quantize_inr(
                    min(afford_res.max_affordable_emi * Decimal(requested_tenure_months), limit_ceiling)
                )

        # 3. Margin of Safety (if plan is already feasible)
        income_drop_margin = Decimal("0.00")
        expense_increase_margin = Decimal("0.00")
        if is_feasible:
            # How much can income drop before D = EMI?
            # 0.85 * I_break = E + debt + EMI
            break_income = (essential_expenses + existing_debt + orig_emi) / buffer_factor
            income_drop_margin = quantize_inr(max(Decimal("0.00"), monthly_income - break_income))
            expense_increase_margin = quantize_inr(
                max(Decimal("0.00"), afford_res.max_affordable_emi - orig_emi)
            )

        # 4. Build Side-by-Side Comparison Table
        comparison_table: list[CounterfactualComparisonRow] = []

        # Row 1: Requested Plan
        req_status = "FEASIBLE" if is_feasible else f"FAILS ({binding_constraint})"
        comparison_table.append(
            CounterfactualComparisonRow(
                plan_label="Requested Proposal",
                principal=quantize_inr(requested_principal),
                tenure_months=requested_tenure_months,
                monthly_emi=orig_emi,
                total_interest=quantize_inr(orig_interest),
                total_repayment=quantize_inr(orig_total),
                residual_monthly_cash=quantize_inr(residual_cash),
                is_feasible=is_feasible,
                status_summary=req_status,
            )
        )

        # Row 2: Feasible Alternative with Extended Tenure (if needed)
        if not is_feasible and min_feasible_t and min_feasible_t != requested_tenure_months:
            eff_p = min(requested_principal, limit_ceiling)
            alt_emi = calculate_emi(eff_p, annual_rate, min_feasible_t)
            alt_tot = alt_emi * Decimal(min_feasible_t)
            alt_int = alt_tot - eff_p
            comparison_table.append(
                CounterfactualComparisonRow(
                    plan_label=f"Tenure Extended ({min_feasible_t}m)",
                    principal=eff_p,
                    tenure_months=min_feasible_t,
                    monthly_emi=alt_emi,
                    total_interest=quantize_inr(alt_int),
                    total_repayment=quantize_inr(alt_tot),
                    residual_monthly_cash=quantize_inr(monthly_income - (essential_expenses + existing_debt) - alt_emi),
                    is_feasible=True,
                    status_summary="FEASIBLE (Tenure Extended)",
                )
            )

        # Row 3: Feasible Alternative with Reduced Principal (at requested tenure)
        if not is_feasible and max_feasible_p > Decimal("0.00") and max_feasible_p < requested_principal:
            p_emi = calculate_emi(max_feasible_p, annual_rate, requested_tenure_months)
            p_tot = p_emi * Decimal(requested_tenure_months)
            p_int = p_tot - max_feasible_p
            comparison_table.append(
                CounterfactualComparisonRow(
                    plan_label="Reduced Principal",
                    principal=max_feasible_p,
                    tenure_months=requested_tenure_months,
                    monthly_emi=p_emi,
                    total_interest=quantize_inr(p_int),
                    total_repayment=quantize_inr(p_tot),
                    residual_monthly_cash=quantize_inr(monthly_income - (essential_expenses + existing_debt) - p_emi),
                    is_feasible=True,
                    status_summary="FEASIBLE (Principal Reduced)",
                )
            )

        # 5. Narrative Explanation & Concrete Actionable Remedies
        actionable_remedies: list[str] = []
        if is_feasible:
            explanation_narrative = (
                f"The requested plan of INR {requested_principal:,.2f} over {requested_tenure_months} months is affordable. "
                f"Monthly instalment of INR {orig_emi:,.2f} leaves a monthly residual cash cushion of INR {residual_cash:,.2f} "
                f"after non-discretionary expenses and the protected safety buffer of INR {afford_res.effective_buffer:,.2f}. "
                f"Your plan has a safety margin: gross income could fall by up to INR {income_drop_margin:,.2f}/month before becoming unaffordable."
            )
            actionable_remedies.append(
                f"Maintain current budget: You have an income shock safety buffer of INR {income_drop_margin:,.2f}/month."
            )
        else:
            narrative_clauses = []
            if orig_emi > afford_res.max_affordable_emi:
                diff = orig_emi - afford_res.max_affordable_emi
                narrative_clauses.append(
                    f"Requested monthly instalment of INR {orig_emi:,.2f} exceeds your maximum affordable instalment of INR {afford_res.max_affordable_emi:,.2f} by INR {diff:,.2f}."
                )
            if requested_principal > limit_ceiling:
                p_diff = requested_principal - limit_ceiling
                narrative_clauses.append(
                    f"Requested principal of INR {requested_principal:,.2f} exceeds your approved credit ceiling of INR {limit_ceiling:,.2f} by INR {p_diff:,.2f}."
                )

            explanation_narrative = " ".join(narrative_clauses)

            # Generate exact quantitative counterfactual remedies
            if required_income_inc > Decimal("0.00"):
                actionable_remedies.append(
                    f"Income Remedy: Increasing verified monthly income by INR {required_income_inc:,.2f} (from INR {monthly_income:,.2f} to INR {monthly_income + required_income_inc:,.2f}) makes the requested loan feasible."
                )
            if required_expense_cut > Decimal("0.00") and required_expense_cut <= essential_expenses:
                actionable_remedies.append(
                    f"Expense Remedy: Reducing non-discretionary monthly expenditures by INR {required_expense_cut:,.2f} (from INR {essential_expenses:,.2f} to INR {essential_expenses - required_expense_cut:,.2f}) satisfies affordability."
                )
            if min_feasible_t and min_feasible_t > requested_tenure_months:
                actionable_remedies.append(
                    f"Tenure Remedy: Extending the loan term from {requested_tenure_months} to {min_feasible_t} months reduces the instalment within budget."
                )
            if max_feasible_p > Decimal("0.00") and max_feasible_p < requested_principal:
                actionable_remedies.append(
                    f"Principal Remedy: Borrowing a reduced principal of INR {max_feasible_p:,.2f} at your requested {requested_tenure_months}-month horizon satisfies all policy constraints."
                )

        return CounterfactualReport(
            is_requested_feasible=is_feasible,
            requested_plan=requested_plan,
            binding_constraint=binding_constraint,
            required_income_increase=required_income_inc,
            required_expense_reduction=required_expense_cut,
            min_feasible_tenure_months=min_feasible_t,
            max_feasible_principal_at_requested_tenure=max_feasible_p,
            income_drop_margin_before_infeasible=income_drop_margin,
            expense_increase_margin_before_infeasible=expense_increase_margin,
            comparison_table=comparison_table,
            explanation_narrative=explanation_narrative,
            actionable_remedies=actionable_remedies,
        )
