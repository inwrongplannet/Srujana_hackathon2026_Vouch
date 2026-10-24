"""Loan Restructuring & Plan Optimizer using Google OR-Tools.

Searches the space of possible loan amounts and tenures subject to rule-based
affordability caps, credit assessment limits, and protected cash buffer constraints.
Supports optimization objectives:
1. MAX_PRINCIPAL: Maximize feasible loan amount borrower can sustainably service.
2. MIN_COST: Minimize total interest paid over the life of the loan.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Optional
from ortools.sat.python import cp_model
from pydantic import BaseModel, Field

from veritrust.affordability import AffordabilityEngine, AffordabilityInput, AffordabilityResult, calculate_emi, quantize_inr


class LoanPlanOption(BaseModel):
    """Specific loan restructuring option with terms and financial obligations."""

    principal: Decimal
    tenure_months: int
    annual_rate: Decimal
    monthly_emi: Decimal
    total_interest: Decimal
    total_repayment: Decimal
    label: str = ""
    is_feasible: bool = True
    infeasibility_reasons: list[str] = Field(default_factory=list)


class OptimizationResult(BaseModel):
    """Complete result of loan restructuring optimization."""

    objective: Literal["MAX_PRINCIPAL", "MIN_COST"]
    original_request: LoanPlanOption
    best_feasible_alternative: Optional[LoanPlanOption]
    is_original_feasible: bool
    binding_constraints: list[str]
    feasible_options: list[LoanPlanOption]
    candidate_plans_evaluated: int
    solver_status: str
    affordability_summary: AffordabilityResult
    currency: str = "INR"


class LoanOptimizer:
    """Google OR-Tools CP-SAT optimizer for credit plans and debt restructuring."""

    def __init__(self, affordability_engine: Optional[AffordabilityEngine] = None) -> None:
        self.affordability_engine = affordability_engine or AffordabilityEngine()

    def optimize(
        self,
        affordability_input: AffordabilityInput,
        requested_principal: Decimal,
        requested_tenure_months: int,
        annual_rate: Decimal = Decimal("0.10"),
        max_approved_credit_limit: Optional[Decimal] = None,
        objective: Literal["MAX_PRINCIPAL", "MIN_COST"] = "MIN_COST",
        tenure_candidates: Optional[list[int]] = None,
        principal_step: Decimal = Decimal("1000.00"),
    ) -> OptimizationResult:
        """Find the optimal loan plan matching borrower goals and policy constraints."""
        affordability = self.affordability_engine.evaluate(affordability_input)

        if tenure_candidates is None:
            tenure_candidates = [3, 6, 9, 12, 18, 24, 36, 48]

        # Credit ceiling is min of max_approved_credit_limit (if present) and disposable income projection
        limit_ceiling = (
            max_approved_credit_limit if max_approved_credit_limit is not None else requested_principal * Decimal("2.0")
        )

        # 1. Evaluate Original Request
        orig_emi = calculate_emi(requested_principal, annual_rate, requested_tenure_months)
        orig_total = orig_emi * Decimal(requested_tenure_months)
        orig_interest = max(Decimal("0.00"), orig_total - requested_principal)
        orig_violations: list[str] = []

        if not affordability.is_affordable:
            orig_violations.append("Borrower disposable income is zero or negative after essential expenses and buffer.")
        if orig_emi > affordability.max_affordable_emi:
            diff = orig_emi - affordability.max_affordable_emi
            orig_violations.append(
                f"Requested EMI of INR {orig_emi:,.2f} exceeds maximum affordable instalment of INR {affordability.max_affordable_emi:,.2f} by INR {diff:,.2f}."
            )
        if requested_principal > limit_ceiling:
            excess = requested_principal - limit_ceiling
            orig_violations.append(
                f"Requested principal of INR {requested_principal:,.2f} exceeds approved credit limit of INR {limit_ceiling:,.2f} by INR {excess:,.2f}."
            )

        is_orig_feasible = len(orig_violations) == 0
        original_plan = LoanPlanOption(
            principal=quantize_inr(requested_principal),
            tenure_months=requested_tenure_months,
            annual_rate=annual_rate,
            monthly_emi=orig_emi,
            total_interest=quantize_inr(orig_interest),
            total_repayment=quantize_inr(orig_total),
            label="Original Request",
            is_feasible=is_orig_feasible,
            infeasibility_reasons=orig_violations,
        )

        # 2. Build Discrete Grid of Candidate Plans
        # Principal range: from ₹5,000 up to min(requested * 1.5, limit_ceiling) in steps
        max_p_eval = max(requested_principal, limit_ceiling)
        min_p_eval = min(Decimal("5000.00"), requested_principal)

        principals: list[Decimal] = []
        curr_p = min_p_eval
        while curr_p <= max_p_eval:
            principals.append(curr_p)
            curr_p += principal_step
        if requested_principal not in principals:
            principals.append(requested_principal)
            principals.sort()

        # Generate candidates and filter feasibility
        candidates: list[LoanPlanOption] = []
        feasible_candidates: list[LoanPlanOption] = []
        binding_constraints_set: set[str] = set()

        for p in principals:
            for t in tenure_candidates:
                emi = calculate_emi(p, annual_rate, t)
                tot = emi * Decimal(t)
                intr = max(Decimal("0.00"), tot - p)
                reasons: list[str] = []

                if not affordability.is_affordable:
                    reasons.append("ZERO_DISPOSABLE_INCOME")
                if emi > affordability.max_affordable_emi:
                    reasons.append("EXCEEDS_AFFORDABLE_EMI")
                    binding_constraints_set.add(
                        f"Instalment cap: Max affordable EMI is INR {affordability.max_affordable_emi:,.2f} (Restricted by {affordability.binding_policy_rule})"
                    )
                if p > limit_ceiling:
                    reasons.append("EXCEEDS_CREDIT_LIMIT")
                    binding_constraints_set.add(f"Credit ceiling: Max eligible limit is INR {limit_ceiling:,.2f}")

                plan = LoanPlanOption(
                    principal=quantize_inr(p),
                    tenure_months=t,
                    annual_rate=annual_rate,
                    monthly_emi=emi,
                    total_interest=quantize_inr(intr),
                    total_repayment=quantize_inr(tot),
                    is_feasible=(len(reasons) == 0),
                    infeasibility_reasons=reasons,
                )
                candidates.append(plan)
                if plan.is_feasible:
                    feasible_candidates.append(plan)

        # 3. Solve with OR-Tools CP-SAT
        best_option: Optional[LoanPlanOption] = None
        solver_status_str = "NOT_SOLVED"

        if feasible_candidates:
            model = cp_model.CpModel()
            # Binary variable for each feasible candidate: x_i in {0, 1}
            x_vars = [model.NewBoolVar(f"plan_{i}") for i in range(len(feasible_candidates))]

            # Exactly one plan selected
            model.AddExactlyOne(x_vars)

            # Scaling factor for CP-SAT integer objectives (convert paise to int)
            # Objective formulation:
            if objective == "MAX_PRINCIPAL":
                # Maximize principal; tie-break with lower interest
                # Cost function: P * 10000 - Total_Interest
                obj_terms = [
                    int(feasible_candidates[i].principal * Decimal("100")) * 1000
                    - int(feasible_candidates[i].total_interest * Decimal("100"))
                    for i in range(len(feasible_candidates))
                ]
                model.Maximize(cp_model.LinearExpr.WeightedSum(x_vars, obj_terms))
            else:
                # MIN_COST: Prioritize matching or approaching requested principal, then minimize total interest
                # If plans exist with principal >= requested_principal, constrain to those
                meets_target = [c.principal >= requested_principal for c in feasible_candidates]
                if any(meets_target):
                    # Constrain to candidates that satisfy requested principal
                    for i, meets in enumerate(meets_target):
                        if not meets:
                            model.Add(x_vars[i] == 0)

                    # Minimize total interest
                    int_costs = [int(feasible_candidates[i].total_interest * Decimal("100")) for i in range(len(feasible_candidates))]
                    model.Minimize(cp_model.LinearExpr.WeightedSum(x_vars, int_costs))
                else:
                    # Could not satisfy requested principal -> maximize principal while minimizing cost
                    obj_terms = [
                        int(feasible_candidates[i].principal * Decimal("100")) * 1000
                        - int(feasible_candidates[i].total_interest * Decimal("100"))
                        for i in range(len(feasible_candidates))
                    ]
                    model.Maximize(cp_model.LinearExpr.WeightedSum(x_vars, obj_terms))

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 2.0
            status = solver.Solve(model)
            solver_status_str = solver.StatusName(status)

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                for i, x in enumerate(x_vars):
                    if solver.BooleanValue(x):
                        best_option = feasible_candidates[i]
                        best_option.label = (
                            "Best Alternative (Optimized)" if not is_orig_feasible else "Original Plan Optimal"
                        )
                        break

        # 4. Curate Diverse Feasible Alternatives (Lowest EMI, Shortest Tenure, Max Principal)
        curated_options: list[LoanPlanOption] = []
        if feasible_candidates:
            # Lowest EMI option
            lowest_emi = min(feasible_candidates, key=lambda c: (c.monthly_emi, c.total_interest))
            lowest_emi_copy = lowest_emi.model_copy()
            lowest_emi_copy.label = "Lowest Monthly Instalment"
            curated_options.append(lowest_emi_copy)

            # Shortest tenure option (Lowest Interest)
            shortest_t = min(feasible_candidates, key=lambda c: (c.tenure_months, c.total_interest))
            if shortest_t.tenure_months != lowest_emi.tenure_months or shortest_t.principal != lowest_emi.principal:
                shortest_t_copy = shortest_t.model_copy()
                shortest_t_copy.label = "Shortest Tenure (Lowest Interest)"
                curated_options.append(shortest_t_copy)

            # Maximum Principal option
            max_p = max(feasible_candidates, key=lambda c: (c.principal, -c.monthly_emi))
            if max_p.principal != lowest_emi.principal and max_p.principal != shortest_t.principal:
                max_p_copy = max_p.model_copy()
                max_p_copy.label = "Maximum Sustainable Principal"
                curated_options.append(max_p_copy)

        return OptimizationResult(
            objective=objective,
            original_request=original_plan,
            best_feasible_alternative=best_option,
            is_original_feasible=is_orig_feasible,
            binding_constraints=sorted(list(binding_constraints_set)),
            feasible_options=curated_options,
            candidate_plans_evaluated=len(candidates),
            solver_status=solver_status_str,
            affordability_summary=affordability,
        )
