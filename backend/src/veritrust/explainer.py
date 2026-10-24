"""Traceable Explanation & Multi-Dimensional Evidence Engine for VeriTrust.

Generates auditable, human-readable explanations from the specific policy rules,
optimization alternatives, and stress tests that fired. Explains decisions across
four distinct, orthogonal dimensions:
1. Financial Capacity (Disposable income, cash buffer, EMI affordability)
2. Evidence Reliability (Documentation completeness, verified vs thin-file records)
3. Graph Reputation (Web-of-Trust endorsements, anchor distance, skin-in-the-game)
4. Stress-Test Resilience (Monte Carlo shock tolerance, shortfall risk under stress)
"""

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from veritrust.affordability import AffordabilityResult
from veritrust.models import CreditAssessment
from veritrust.optimizer import OptimizationResult
from veritrust.stress_tester import StressTestReport


class DimensionExplanation(BaseModel):
    """Breakdown of a single underwriting dimension."""

    dimension_name: str
    status: str
    headline: str
    score_or_metric: str
    key_findings: list[str]
    audit_trail_rules: list[str]


class RecommendationExplanation(BaseModel):
    """Unified explanation for credit decision and plan restructuring."""

    verdict: str
    narrative_summary: str
    dimension_financial_capacity: DimensionExplanation
    dimension_evidence_reliability: DimensionExplanation
    dimension_graph_reputation: DimensionExplanation
    dimension_stress_resilience: DimensionExplanation
    restructuring_guidance: list[str]
    traceable_rules_fired: list[str]


class ExplanationEngine:
    """Generates traceable, transparent explanations from rule execution traces."""

    def explain(
        self,
        affordability: AffordabilityResult,
        optimization: OptimizationResult,
        stress_test: StressTestReport,
        credit_assessment: Optional[CreditAssessment] = None,
    ) -> RecommendationExplanation:
        """Synthesize a complete multi-dimensional audit explanation."""
        orig = optimization.original_request
        best = optimization.best_feasible_alternative

        rules_fired_all: list[str] = list(affordability.rules_fired)
        restructuring_notes: list[str] = []

        # -------------------------------------------------------------
        # 1. Dimension: Financial Capacity
        # -------------------------------------------------------------
        if orig.is_feasible:
            cap_status = "APPROVED_WITHIN_BUDGET"
            cap_headline = "Requested loan instalment is fully affordable within disposable cash flow."
        else:
            cap_status = "EXCEEDS_REPAYMENT_BUDGET"
            diff = orig.monthly_emi - affordability.max_affordable_emi
            cap_headline = (
                f"Requested loan exceeds repayment budget by INR {diff:,.2f} per month "
                f"(EMI INR {orig.monthly_emi:,.2f} vs. budget INR {affordability.max_affordable_emi:,.2f})."
            )

        cap_findings = [
            f"Gross Monthly Income: INR {affordability.monthly_income:,.2f}",
            f"Non-Discretionary Obligations: INR {affordability.total_non_discretionary:,.2f} (Expenses: {affordability.essential_expenses:,.2f}, Debt: {affordability.existing_debt_service:,.2f})",
            f"Protected Cash Buffer: INR {affordability.effective_buffer:,.2f} (Reserved floor against emergencies)",
            f"Disposable Repayment Income (D = I - E - B): INR {affordability.disposable_income:,.2f}",
            f"Maximum Affordable Monthly Instalment: INR {affordability.max_affordable_emi:,.2f} (Constrained by {affordability.binding_policy_rule})",
        ]
        dim_capacity = DimensionExplanation(
            dimension_name="Financial Capacity",
            status=cap_status,
            headline=cap_headline,
            score_or_metric=f"Affordable EMI: INR {affordability.max_affordable_emi:,.2f} / month",
            key_findings=cap_findings,
            audit_trail_rules=affordability.rules_fired,
        )

        # -------------------------------------------------------------
        # 2. Dimension: Evidence Reliability
        # -------------------------------------------------------------
        rel_findings = []
        if affordability.data_reliability == "VERIFIED_COMPLETE":
            rel_status = "HIGH_CONFIDENCE_VERIFIED"
            rel_headline = "Financial capacity documented with verified statements."
            rel_findings.append("Documentation is verified via digital bank statement / DigiLocker data.")
            rel_findings.append("No precautionary uncertainty haircut applied.")
        elif affordability.data_reliability == "PARTIAL_ESTIMATE":
            rel_status = "PARTIAL_DISCLOSURE"
            rel_headline = "Partial financial disclosures; precautionary buffer applied."
            rel_findings.extend(affordability.unreliability_notes)
            rel_findings.append("Important: Information gap reflects epistemic uncertainty, not credit malpractice.")
        else:
            rel_status = "THIN_FILE_UNVERIFIED"
            rel_headline = "Thin-file borrower with unverified self-disclosed income."
            rel_findings.extend(affordability.unreliability_notes)
            rel_findings.append("Unverified records trigger conservative buffer floors rather than outright rejection.")

        dim_reliability = DimensionExplanation(
            dimension_name="Evidence Reliability",
            status=rel_status,
            headline=rel_headline,
            score_or_metric=f"Reliability: {affordability.data_reliability}",
            key_findings=rel_findings,
            audit_trail_rules=[r for r in affordability.rules_fired if "VERIF" in r or "THIN" in r or "UNCERTAIN" in r],
        )

        # -------------------------------------------------------------
        # 3. Dimension: Graph Reputation
        # -------------------------------------------------------------
        if credit_assessment:
            n_paths = len(credit_assessment.contributing_paths)
            graph_score = credit_assessment.r_graph
            max_limit = credit_assessment.max_loan_limit

            if credit_assessment.score_final > Decimal("0.0"):
                rep_status = "ENDORSED_CREDIBLE"
                rep_headline = f"Node endorsed by community with graph trust R={graph_score} across {n_paths} path(s)."
            else:
                rep_status = "UNCONNECTED_UNVOUCHED"
                rep_headline = "Node has zero active incoming endorsements from institutional anchors."

            rep_findings = [
                f"Graph Trust Score (R_graph): {graph_score}",
                f"Cash-Flow Capacity Score (S_cashflow): {credit_assessment.s_cashflow}",
                f"Lower Confidence Bound Score: {credit_assessment.score_final}",
                f"Approved Credit Limit: INR {max_limit:,.2f}",
                f"Active Anchor Paths: {n_paths}",
            ]
            for p in credit_assessment.contributing_paths[:2]:
                rep_findings.append(f"Trust Path: {' -> '.join(p.path)} (Weight: {p.path_trust})")
        else:
            rep_status = "NOT_EVALUATED"
            rep_headline = "Web-of-Trust graph assessment was not included in this evaluation."
            rep_findings = ["Standalone affordability calculation without graph propagation context."]

        dim_reputation = DimensionExplanation(
            dimension_name="Graph Reputation",
            status=rep_status,
            headline=rep_headline,
            score_or_metric=f"R_graph: {credit_assessment.r_graph if credit_assessment else 'N/A'}",
            key_findings=rep_findings,
            audit_trail_rules=["RULE_GRAPH_PROPAGATION: Hop decay lambda=0.5 with per-path cycle absorption"],
        )

        # -------------------------------------------------------------
        # 4. Dimension: Stress-Test Resilience
        # -------------------------------------------------------------
        res_findings = [
            f"Simulated Monte Carlo Paths: {stress_test.n_simulations:,} (Seed: {stress_test.reproducibility_seed})",
            f"Shortfall Probability under Stress: {stress_test.shortfall_frequency_pct}%",
            f"Worst-Case Adverse Cushion (5th Percentile): INR {stress_test.residual_cash_p05:,.2f}",
            f"Borrower Income Shock Absorption Tolerance: {stress_test.shock_tolerance_pct}%",
            f"Affordability Break Income Floor: INR {stress_test.affordability_break_income:,.2f} / month",
        ]
        dim_resilience = DimensionExplanation(
            dimension_name="Stress-Test Resilience",
            status=stress_test.stress_rating,
            headline=stress_test.resilience_summary,
            score_or_metric=f"Stress Rating: {stress_test.stress_rating} ({stress_test.shortfall_frequency_pct}% shortfall)",
            key_findings=res_findings,
            audit_trail_rules=[
                f"RULE_MONTE_CARLO: Evaluated {stress_test.n_simulations} iterations with income volatility and emergency expense shocks."
            ],
        )

        # -------------------------------------------------------------
        # Narrative Synthesis & Restructuring Guidance
        # -------------------------------------------------------------
        if orig.is_feasible:
            verdict = "APPROVED"
            narrative = (
                f"The requested loan of INR {orig.principal:,.2f} over {orig.tenure_months} months is approved. "
                f"The monthly instalment of INR {orig.monthly_emi:,.2f} fits within the disposable budget "
                f"of INR {affordability.max_affordable_emi:,.2f}, preserving the protected cash buffer of INR {affordability.effective_buffer:,.2f}. "
                f"Monte Carlo stress testing confirms {stress_test.stress_rating} resilience ({stress_test.shortfall_frequency_pct}% shortfall risk)."
            )
        elif best is not None:
            verdict = "RESTRUCTURED_ALTERNATIVE"
            diff = orig.monthly_emi - affordability.max_affordable_emi
            narrative = (
                f"The requested loan exceeds the repayment budget by INR {diff:,.2f} per month. "
                f"Extending the tenure from {orig.tenure_months} to {best.tenure_months} months reduces the monthly instalment "
                f"to INR {best.monthly_emi:,.2f}, satisfying all configured affordability rules while increasing total interest "
                f"from INR {orig.total_interest:,.2f} to INR {best.total_interest:,.2f}."
            )
            restructuring_notes.append(
                f"Option 1 (Recommended): Extend tenure to {best.tenure_months} months -> Monthly instalment drops to INR {best.monthly_emi:,.2f}."
            )
            if best.principal < orig.principal:
                restructuring_notes.append(
                    f"Option 2: Reduce principal from INR {orig.principal:,.2f} to INR {best.principal:,.2f} to maintain the original {orig.tenure_months}-month horizon."
                )
        else:
            verdict = "REJECTED_UNAFFORDABLE"
            narrative = (
                f"The requested loan is unaffordable under current policy rules. "
                f"Borrower's disposable income is INR {affordability.disposable_income:,.2f} after non-discretionary expenses "
                f"(INR {affordability.total_non_discretionary:,.2f}) and protected cash buffer (INR {affordability.effective_buffer:,.2f}). "
                "No feasible loan plan can be structured without violating minimum cash buffer or debt-to-income caps."
            )
            restructuring_notes.extend(affordability.rejection_reasons)

        return RecommendationExplanation(
            verdict=verdict,
            narrative_summary=narrative,
            dimension_financial_capacity=dim_capacity,
            dimension_evidence_reliability=dim_reliability,
            dimension_graph_reputation=dim_reputation,
            dimension_stress_resilience=dim_resilience,
            restructuring_guidance=restructuring_notes,
            traceable_rules_fired=rules_fired_all,
        )
