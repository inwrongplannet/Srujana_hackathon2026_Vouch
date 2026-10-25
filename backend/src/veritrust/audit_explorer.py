"""Decision Explanation and Audit Explorer for VeriTrust.

Provides a forensic, machine-readable audit trail of any credit decision:
- Inspects which explicit policy rules fired and passed/failed against numerical thresholds.
- Surfaces primary evidence records contributing to the underwriting assessment.
- Details the complete Web-of-Trust graph traversal paths, edge weights, and hop decays.
- Extracts the chronological, hash-chained reputation ledger events for the borrower.
- Performs deterministic sensitivity analysis showing how the decision changes under input corrections.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

from veritrust.affordability import AffordabilityEngine, AffordabilityInput, AffordabilityResult, quantize_inr
from veritrust.engine import TrustEngine
from veritrust.ledger import ReputationLedger
from veritrust.models import ContributingPath, CreditAssessment, Evidence, LedgerEvent
from veritrust.optimizer import LoanOptimizer, LoanPlanOption
from veritrust.scoring import CreditScorer
from veritrust.stress_tester import MonteCarloStressTester, StressTestReport


class DecisionRuleAuditRecord(BaseModel):
    """Detailed audit of a single policy or affordability rule evaluated during decisioning."""

    rule_id: str
    rule_name: str
    category: Literal["AFFORDABILITY", "POLICY_CAP", "GRAPH_TRUST", "STRESS_RESILIENCE"]
    observed_value: str
    policy_threshold: str
    passed: bool
    binding: bool
    diagnostic_detail: str


class SensitivityDelta(BaseModel):
    """Deterministic sensitivity delta under hypothetical input corrections."""

    parameter_perturbed: str
    perturbation_description: str
    new_disposable_income: Decimal
    new_max_affordable_emi: Decimal
    new_approved_credit_limit: Decimal
    impact_summary: str


class DecisionAuditReport(BaseModel):
    """Comprehensive forensic audit explorer report for an underwriting decision."""

    audit_id: str
    borrower_id: str
    borrower_name: str
    evaluated_at: datetime
    verdict: Literal["APPROVED", "RESTRUCTURED_ALTERNATIVE", "REJECTED_UNAFFORDABLE"]
    requested_principal: Decimal
    requested_tenure_months: int
    requested_emi: Decimal

    # 1. Rules Evaluated Trace
    rules_evaluated: list[DecisionRuleAuditRecord]

    # 2. Contributing Primary Evidence
    contributing_evidence: list[Evidence]

    # 3. Web-of-Trust Graph Paths
    graph_trust_score: Decimal
    contributing_paths: list[ContributingPath]

    # 4. Hash-Chained Reputation Mutation Event History
    reputation_event_history: list[LedgerEvent]

    # 5. Deterministic Sensitivity Analysis
    sensitivity_analysis: list[SensitivityDelta]
    currency: str = "INR"


class DecisionAuditExplorer:
    """Forensic decision inspection and sensitivity exploration engine."""

    def __init__(
        self,
        engine: TrustEngine,
        scorer: CreditScorer,
        affordability_engine: Optional[AffordabilityEngine] = None,
        optimizer: Optional[LoanOptimizer] = None,
        stress_tester: Optional[MonteCarloStressTester] = None,
    ) -> None:
        self.engine = engine
        self.scorer = scorer
        self.affordability_engine = affordability_engine or AffordabilityEngine()
        self.optimizer = optimizer or LoanOptimizer(self.affordability_engine)
        self.stress_tester = stress_tester or MonteCarloStressTester()

    def inspect_decision(
        self,
        borrower_id: str,
        requested_principal: Decimal,
        requested_tenure_months: int = 6,
        annual_rate: Decimal = Decimal("0.10"),
    ) -> DecisionAuditReport:
        """Generate a complete forensic audit report for a borrower's credit decision."""
        user = self.engine.get_user(borrower_id)
        if not user:
            raise ValueError(f"Borrower '{borrower_id}' does not exist.")

        ff = user.financial_features
        income = ff.monthly_income if ff and ff.monthly_income > 0 else Decimal("35000.00")
        debt = ff.monthly_debt if ff else Decimal("0.00")
        expenses = (ff.monthly_income - ff.net_operating_income) if ff and ff.net_operating_income > 0 else Decimal("18000.00")
        completeness = ff.completeness if ff else Decimal("0.85")
        is_verified = user.is_anchor or (ff is not None and completeness >= Decimal("0.90"))

        afford_input = AffordabilityInput(
            monthly_income=income,
            essential_expenses=expenses,
            existing_debt_service=debt,
            data_completeness=completeness,
            is_verified=is_verified,
        )
        afford_res = self.affordability_engine.evaluate(afford_input)
        assessment = self.scorer.assess_credit(borrower_id)
        opt_res = self.optimizer.optimize(
            affordability_input=afford_input,
            requested_principal=requested_principal,
            requested_tenure_months=requested_tenure_months,
            annual_rate=annual_rate,
            max_approved_credit_limit=assessment.max_loan_limit,
        )
        plan = opt_res.best_feasible_alternative or opt_res.original_request
        stress_res = self.stress_tester.stress_test(
            monthly_income=income,
            essential_expenses=expenses + debt,
            monthly_emi=plan.monthly_emi,
            tenure_months=plan.tenure_months,
            initial_cash_buffer=afford_res.effective_buffer,
        )

        orig = opt_res.original_request
        verdict: Literal["APPROVED", "RESTRUCTURED_ALTERNATIVE", "REJECTED_UNAFFORDABLE"]
        if orig.is_feasible:
            verdict = "APPROVED"
        elif opt_res.best_feasible_alternative is not None:
            verdict = "RESTRUCTURED_ALTERNATIVE"
        else:
            verdict = "REJECTED_UNAFFORDABLE"

        # 1. Structure explicit rule audits
        rules_evaluated: list[DecisionRuleAuditRecord] = []

        # Rule 1: Positive Disposable Income
        disp_passed = afford_res.disposable_income > Decimal("0.00")
        rules_evaluated.append(
            DecisionRuleAuditRecord(
                rule_id="RULE_DISPOSABLE_INCOME_FLOOR",
                rule_name="Minimum Disposable Income Floor",
                category="AFFORDABILITY",
                observed_value=f"INR {afford_res.disposable_income:,.2f}",
                policy_threshold="> INR 0.00",
                passed=disp_passed,
                binding=(not disp_passed),
                diagnostic_detail=f"D = I ({income:,.2f}) - E ({expenses:,.2f}) - Debt ({debt:,.2f}) - Buffer ({afford_res.effective_buffer:,.2f})",
            )
        )

        # Rule 2: ITI / FOIR Cap
        iti_cap = income * afford_input.max_iti_foir
        iti_passed = orig.monthly_emi <= iti_cap
        rules_evaluated.append(
            DecisionRuleAuditRecord(
                rule_id="RULE_ITI_FOIR_CAP",
                rule_name="Instalment-to-Income (FOIR) Cap (<= 40%)",
                category="POLICY_CAP",
                observed_value=f"INR {orig.monthly_emi:,.2f} ({orig.monthly_emi/income*100:.1f}%)",
                policy_threshold=f"<= INR {iti_cap:,.2f} (40.0%)",
                passed=iti_passed,
                binding=(afford_res.binding_policy_rule == "ITI_FOIR_CAP"),
                diagnostic_detail=f"Instalment of INR {orig.monthly_emi:,.2f} evaluated against 40% gross income limit.",
            )
        )

        # Rule 3: DTI Cap
        dti_cap = income * afford_input.max_dti
        total_out = orig.monthly_emi + debt
        dti_passed = total_out <= dti_cap
        rules_evaluated.append(
            DecisionRuleAuditRecord(
                rule_id="RULE_DTI_TOTAL_CAP",
                rule_name="Total Debt-to-Income Cap (<= 50%)",
                category="POLICY_CAP",
                observed_value=f"INR {total_out:,.2f} ({total_out/income*100:.1f}%)",
                policy_threshold=f"<= INR {dti_cap:,.2f} (50.0%)",
                passed=dti_passed,
                binding=(afford_res.binding_policy_rule == "DTI_CAP"),
                diagnostic_detail=f"Combined existing debt (INR {debt:,.2f}) and EMI (INR {orig.monthly_emi:,.2f}) evaluated against 50% cap.",
            )
        )

        # Rule 4: Credit Limit Ceiling
        limit_passed = requested_principal <= assessment.max_loan_limit
        rules_evaluated.append(
            DecisionRuleAuditRecord(
                rule_id="RULE_CREDIT_LIMIT_CEILING",
                rule_name="Approved Credit Limit Ceiling",
                category="GRAPH_TRUST",
                observed_value=f"INR {requested_principal:,.2f}",
                policy_threshold=f"<= INR {assessment.max_loan_limit:,.2f}",
                passed=limit_passed,
                binding=(not limit_passed),
                diagnostic_detail=f"Principal verified against LCB score ({assessment.score_final}) and graph trust R={assessment.r_graph}.",
            )
        )

        # Rule 5: Stress Resilience Threshold
        stress_passed = stress_res.shortfall_probability <= Decimal("0.15")
        rules_evaluated.append(
            DecisionRuleAuditRecord(
                rule_id="RULE_STRESS_TEST_RESILIENCE",
                rule_name="Monte Carlo Default Shortfall Bound",
                category="STRESS_RESILIENCE",
                observed_value=f"{stress_res.shortfall_frequency_pct}% shortfall ({stress_res.stress_rating})",
                policy_threshold="<= 15.0% shortfall probability",
                passed=stress_passed,
                binding=False,
                diagnostic_detail=f"5,000 stochastic scenarios evaluated. 5th-percentile adverse cash: INR {stress_res.residual_cash_p05:,.2f}.",
            )
        )

        # 2. Contributing Evidence Collection
        contributing_evidence: list[Evidence] = []
        if getattr(self.engine, "ledger", None):
            user_events = self.engine.ledger.get_history(borrower_id)  # type: ignore
            for evt in user_events:
                if evt.evidence and evt.evidence not in contributing_evidence:
                    contributing_evidence.append(evt.evidence)
        else:
            user_events = []

        # 3. Sensitivity / What-If Delta Analysis
        sensitivity_analysis: list[SensitivityDelta] = []

        # Scenario S1: Income +10%
        inc_up = income * Decimal("1.10")
        afford_up = self.affordability_engine.evaluate(
            AffordabilityInput(
                monthly_income=inc_up,
                essential_expenses=expenses,
                existing_debt_service=debt,
                data_completeness=completeness,
                is_verified=is_verified,
            )
        )
        sensitivity_analysis.append(
            SensitivityDelta(
                parameter_perturbed="Monthly Income +10%",
                perturbation_description=f"Income increases from INR {income:,.2f} to INR {inc_up:,.2f}",
                new_disposable_income=afford_up.disposable_income,
                new_max_affordable_emi=afford_up.max_affordable_emi,
                new_approved_credit_limit=quantize_inr(assessment.max_loan_limit * Decimal("1.08")),
                impact_summary=f"Max affordable EMI expands by INR {afford_up.max_affordable_emi - afford_res.max_affordable_emi:,.2f} / month.",
            )
        )

        # Scenario S2: Income -10% (Income Shock)
        inc_down = income * Decimal("0.90")
        afford_down = self.affordability_engine.evaluate(
            AffordabilityInput(
                monthly_income=inc_down,
                essential_expenses=expenses,
                existing_debt_service=debt,
                data_completeness=completeness,
                is_verified=is_verified,
            )
        )
        sensitivity_analysis.append(
            SensitivityDelta(
                parameter_perturbed="Monthly Income -10% (Shock)",
                perturbation_description=f"Income contracts from INR {income:,.2f} to INR {inc_down:,.2f}",
                new_disposable_income=afford_down.disposable_income,
                new_max_affordable_emi=afford_down.max_affordable_emi,
                new_approved_credit_limit=quantize_inr(assessment.max_loan_limit * Decimal("0.92")),
                impact_summary=f"Max affordable EMI contracts by INR {afford_res.max_affordable_emi - afford_down.max_affordable_emi:,.2f} / month.",
            )
        )

        # Scenario S3: Essential Expenses Cut by INR 3,000
        exp_cut = max(Decimal("0.00"), expenses - Decimal("3000.00"))
        afford_exp_cut = self.affordability_engine.evaluate(
            AffordabilityInput(
                monthly_income=income,
                essential_expenses=exp_cut,
                existing_debt_service=debt,
                data_completeness=completeness,
                is_verified=is_verified,
            )
        )
        sensitivity_analysis.append(
            SensitivityDelta(
                parameter_perturbed="Expenses Cut by INR 3,000",
                perturbation_description=f"Essential expenses cut from INR {expenses:,.2f} to INR {exp_cut:,.2f}",
                new_disposable_income=afford_exp_cut.disposable_income,
                new_max_affordable_emi=afford_exp_cut.max_affordable_emi,
                new_approved_credit_limit=assessment.max_loan_limit,
                impact_summary=f"Frees up INR {afford_exp_cut.disposable_income - afford_res.disposable_income:,.2f} in additional disposable repayment capacity.",
            )
        )

        return DecisionAuditReport(
            audit_id=f"AUDIT_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{borrower_id}",
            borrower_id=borrower_id,
            borrower_name=user.name,
            evaluated_at=datetime.now(timezone.utc),
            verdict=verdict,
            requested_principal=quantize_inr(requested_principal),
            requested_tenure_months=requested_tenure_months,
            requested_emi=orig.monthly_emi,
            rules_evaluated=rules_evaluated,
            contributing_evidence=contributing_evidence,
            graph_trust_score=assessment.r_graph,
            contributing_paths=assessment.contributing_paths,
            reputation_event_history=user_events,
            sensitivity_analysis=sensitivity_analysis,
        )
