"""Rule-based affordability engine for VeriTrust.

Calculates disposable income, existing debt obligations, protected minimum cash buffers,
and maximum affordable loan instalments (EMI) based on explicit, traceable policy rules.
Strictly separates missing or unverified financial information from low affordability.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import TYPE_CHECKING, Literal, Optional
from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from veritrust.models import FinancialFeatures


def quantize_inr(value: Decimal) -> Decimal:
    """Round to 2 decimal places (paise precision) using bankers/half-up rounding."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_emi(principal: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
    """Calculate monthly loan instalment (EMI) with Decimal precision.

    Formula:
        r_m = annual_rate / 12
        EMI = P * r_m * (1 + r_m)^T / ((1 + r_m)^T - 1)
    """
    if tenure_months <= 0:
        raise ValueError(f"Tenure must be positive, got {tenure_months}")
    if principal <= Decimal("0.0"):
        return Decimal("0.00")
    if annual_rate <= Decimal("0.0"):
        return quantize_inr(principal / Decimal(tenure_months))

    r_m = annual_rate / Decimal("12.0")
    # Compute factor (1 + r_m)^T
    one_plus_r = Decimal("1.0") + r_m
    factor = one_plus_r ** Decimal(str(tenure_months))
    numerator = principal * r_m * factor
    denominator = factor - Decimal("1.0")
    return quantize_inr(numerator / denominator)


class AffordabilityInput(BaseModel):
    """Borrower financial inputs for rule-based affordability assessment."""

    monthly_income: Decimal = Field(description="Gross regular monthly income in INR")
    essential_expenses: Decimal = Field(
        default=Decimal("0.0"), description="Essential living expenditures (housing, food, utilities) in INR"
    )
    existing_debt_service: Decimal = Field(
        default=Decimal("0.0"), description="Existing recurring monthly debt obligations in INR"
    )
    buffer_percentage: Decimal = Field(
        default=Decimal("0.15"), description="Protected cash buffer as a fraction of monthly income (default: 15%)"
    )
    min_buffer_floor: Decimal = Field(
        default=Decimal("3000.00"), description="Absolute minimum protected cash buffer floor in INR"
    )
    max_iti_foir: Decimal = Field(
        default=Decimal("0.40"),
        description="Maximum Instalment-to-Income / Fixed Obligation to Income Ratio cap (default: 40%)",
    )
    max_dti: Decimal = Field(
        default=Decimal("0.50"),
        description="Maximum Total Debt-to-Income cap including new loan and existing debt (default: 50%)",
    )
    data_completeness: Decimal = Field(
        default=Decimal("1.0"),
        description="Financial data completeness fraction in [0.0, 1.0]. Lower values indicate thin-file records.",
    )
    is_verified: bool = Field(
        default=False, description="True if supported by verified bank statements or DigiLocker data"
    )

    @field_validator(
        "monthly_income",
        "essential_expenses",
        "existing_debt_service",
        "buffer_percentage",
        "min_buffer_floor",
        "max_iti_foir",
        "max_dti",
        "data_completeness",
        mode="before",
    )
    @classmethod
    def parse_to_decimal(cls, value: object) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


# Used only when a borrower shared income but no operating costs: a conservative stand-in, flagged
# as missing information by the assessment, so a blank never reads as "no expenses".
UNDOCUMENTED_EXPENSES = Decimal("10000.00")


def affordability_input(fin: Optional["FinancialFeatures"]) -> AffordabilityInput:
    """One affordability basis for every route, so an assessment and its what-if agree.

    Essential expenses are income minus net operating income (`FinancialFeatures` defines NOI as
    income after operating expenses), the same reading `cli.py` and `audit_explorer.py` use.
    No financial data means zero income, zero expenses and zero completeness: unknown, never imputed.
    Nothing on file is bank-verified yet, so `is_verified` stays False. Amounts are INR Decimals.
    """
    if fin is None:
        return AffordabilityInput(monthly_income=Decimal("0.00"), data_completeness=Decimal("0.0"))
    if fin.net_operating_income > Decimal("0.0"):
        expenses = max(Decimal("0.00"), fin.monthly_income - fin.net_operating_income)
    else:
        expenses = UNDOCUMENTED_EXPENSES
    return AffordabilityInput(
        monthly_income=fin.monthly_income,
        essential_expenses=expenses,
        existing_debt_service=fin.monthly_debt,
        data_completeness=fin.completeness,
    )


def affordability_status(disposable_income: Decimal) -> str:
    """SUFFICIENT, BORDERLINE (under INR 3,000 a month to spare) or INSUFFICIENT."""
    if disposable_income <= Decimal("0.0"):
        return "INSUFFICIENT"
    if disposable_income < Decimal("3000.00"):
        return "BORDERLINE"
    return "SUFFICIENT"


class AffordabilityResult(BaseModel):
    """Detailed output of rule-based affordability evaluation."""

    monthly_income: Decimal
    essential_expenses: Decimal
    existing_debt_service: Decimal
    total_non_discretionary: Decimal
    protected_buffer: Decimal
    effective_buffer: Decimal
    disposable_income: Decimal  # D = I - E - B
    max_affordable_emi: Decimal
    is_affordable: bool
    data_reliability: Literal["VERIFIED_COMPLETE", "PARTIAL_ESTIMATE", "THIN_FILE_UNVERIFIED"]
    rules_fired: list[str]
    binding_policy_rule: str
    rejection_reasons: list[str]
    unreliability_notes: list[str]
    currency: str = "INR"


class AffordabilityEngine:
    """Rule-based engine for evaluating consumer repayment capacity and protected reserves."""

    def evaluate(self, inp: AffordabilityInput) -> AffordabilityResult:
        """Run explicit policy rules to calculate disposable income and affordable instalment."""
        income = inp.monthly_income
        expenses = inp.essential_expenses
        debt = inp.existing_debt_service
        total_non_discretionary = expenses + debt

        rules_fired: list[str] = []
        rejection_reasons: list[str] = []
        unreliability_notes: list[str] = []

        # 1. Protected Cash Buffer Calculation: B = max(floor, pct * I)
        base_buffer = max(inp.min_buffer_floor, quantize_inr(income * inp.buffer_percentage))
        rules_fired.append(
            f"RULE_BUFFER_FLOOR: Computed base cash buffer of INR {base_buffer:,.2f} "
            f"(max of floor INR {inp.min_buffer_floor:,.2f} or {inp.buffer_percentage*100:.0f}% of income)"
        )

        # 2. Epistemic Data Completeness & Verification Handling
        # Missing or unverified data is treated separately from low financial affordability
        completeness = inp.data_completeness
        if inp.is_verified and completeness >= Decimal("0.85"):
            reliability = "VERIFIED_COMPLETE"
            effective_buffer = base_buffer
            rules_fired.append("RULE_VERIFIED_DATA: Financial documentation verified via reliable primary evidence.")
        elif completeness >= Decimal("0.50"):
            reliability = "PARTIAL_ESTIMATE"
            # Apply a prudent 15% buffer buffer margin for incomplete disclosures
            effective_buffer = quantize_inr(base_buffer * Decimal("1.15"))
            unreliability_notes.append(
                f"Data completeness is {completeness*100:.0f}%. Applied a 15% precautionary reserve buffer. "
                "This reflects information uncertainty, not adverse credit behavior."
            )
            rules_fired.append("RULE_UNCERTAINTY_BUFFER: Elevated protected buffer due to partial disclosures.")
        else:
            reliability = "THIN_FILE_UNVERIFIED"
            effective_buffer = quantize_inr(base_buffer * Decimal("1.30"))
            unreliability_notes.append(
                f"Thin-file borrower with {completeness*100:.0f}% verification. Applied a 30% precautionary reserve buffer. "
                "Borrower qualifies for micro-credit, but requires conservative instalment bounds pending repayment track record."
            )
            rules_fired.append("RULE_THIN_FILE_HAIRCUT: Expanded safety reserve for unverified file.")

        # 3. Disposable Income: D = I - E - B_effective
        disposable_income = income - total_non_discretionary - effective_buffer
        rules_fired.append(
            f"RULE_DISPOSABLE_INCOME: Calculated disposable income D = I ({income:,.2f}) "
            f"- Essential Expenses ({total_non_discretionary:,.2f}) - Buffer ({effective_buffer:,.2f}) = INR {disposable_income:,.2f}"
        )

        # 4. Instalment-to-Income (ITI / FOIR) Cap: EMI <= max_iti * I
        iti_cap = quantize_inr(income * inp.max_iti_foir)
        rules_fired.append(
            f"RULE_ITI_CAP: Instalment-to-Income cap set at {inp.max_iti_foir*100:.0f}% of income = INR {iti_cap:,.2f}"
        )

        # 5. Debt-to-Income (DTI) Cap: (existing_debt + EMI) <= max_dti * I => EMI <= max_dti * I - existing_debt
        dti_cap_max_total = quantize_inr(income * inp.max_dti)
        dti_allowed_emi = max(Decimal("0.00"), dti_cap_max_total - debt)
        rules_fired.append(
            f"RULE_DTI_CAP: Total debt cap set at {inp.max_dti*100:.0f}% of income (INR {dti_cap_max_total:,.2f}). "
            f"After existing debt of INR {debt:,.2f}, remaining debt allowance = INR {dti_allowed_emi:,.2f}"
        )

        # 6. Maximum Affordable Instalment: min(Disposable Income, ITI Cap, DTI Allowed EMI)
        candidates = {
            "DISPOSABLE_INCOME": disposable_income,
            "ITI_FOIR_CAP": iti_cap,
            "DTI_CAP": dti_allowed_emi,
        }
        binding_policy_rule = min(candidates, key=candidates.get)  # type: ignore
        raw_max_emi = candidates[binding_policy_rule]

        if raw_max_emi <= Decimal("0.00") or disposable_income <= Decimal("0.00"):
            max_affordable_emi = Decimal("0.00")
            is_affordable = False
            if disposable_income <= Decimal("0.00"):
                rejection_reasons.append(
                    f"Non-discretionary expenses (INR {total_non_discretionary:,.2f}) and protected buffer "
                    f"(INR {effective_buffer:,.2f}) exceed gross monthly income (INR {income:,.2f}). "
                    f"Disposable income is negative (INR {disposable_income:,.2f})."
                )
            if dti_allowed_emi <= Decimal("0.00"):
                rejection_reasons.append(
                    f"Existing debt service of INR {debt:,.2f} already exhausts the maximum "
                    f"Debt-to-Income limit of {inp.max_dti*100:.0f}% (INR {dti_cap_max_total:,.2f})."
                )
        else:
            max_affordable_emi = quantize_inr(raw_max_emi)
            is_affordable = True

        rules_fired.append(
            f"RULE_FINAL_AFFORDABLE_EMI: Binding constraint is '{binding_policy_rule}' "
            f"resulting in maximum affordable monthly instalment of INR {max_affordable_emi:,.2f}"
        )

        return AffordabilityResult(
            monthly_income=quantize_inr(income),
            essential_expenses=quantize_inr(expenses),
            existing_debt_service=quantize_inr(debt),
            total_non_discretionary=quantize_inr(total_non_discretionary),
            protected_buffer=quantize_inr(base_buffer),
            effective_buffer=quantize_inr(effective_buffer),
            disposable_income=quantize_inr(disposable_income),
            max_affordable_emi=max_affordable_emi,
            is_affordable=is_affordable,
            data_reliability=reliability,
            rules_fired=rules_fired,
            binding_policy_rule=binding_policy_rule,
            rejection_reasons=rejection_reasons,
            unreliability_notes=unreliability_notes,
        )

    def validate_plan(
        self,
        inp: AffordabilityInput,
        proposed_principal: Decimal,
        annual_rate: Decimal,
        tenure_months: int,
    ) -> tuple[bool, Decimal, AffordabilityResult, list[str]]:
        """Check if a specific loan proposal is affordable under policy rules.

        Returns:
            Tuple of (is_valid: bool, emi: Decimal, result: AffordabilityResult, violations: list[str]).
        """
        result = self.evaluate(inp)
        proposed_emi = calculate_emi(proposed_principal, annual_rate, tenure_months)
        violations: list[str] = []

        if not result.is_affordable:
            violations.append("Borrower has zero or negative disposable income after protected buffer.")
            return False, proposed_emi, result, violations

        if proposed_emi > result.max_affordable_emi:
            excess = proposed_emi - result.max_affordable_emi
            violations.append(
                f"Proposed instalment of INR {proposed_emi:,.2f} exceeds maximum affordable instalment "
                f"of INR {result.max_affordable_emi:,.2f} by INR {excess:,.2f} (Constrained by {result.binding_policy_rule})."
            )

        # Check remaining cash buffer if this EMI is serviced
        residual_after_emi = result.monthly_income - result.total_non_discretionary - proposed_emi
        if residual_after_emi < result.effective_buffer:
            violations.append(
                f"Servicing proposed EMI leaves residual buffer of INR {residual_after_emi:,.2f}, "
                f"violating minimum protected cash buffer floor of INR {result.effective_buffer:,.2f}."
            )

        return len(violations) == 0, proposed_emi, result, violations
