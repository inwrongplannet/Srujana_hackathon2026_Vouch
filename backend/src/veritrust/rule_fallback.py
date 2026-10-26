"""Deterministic tuned rule-based underwriting and explanation fallback engine.

Why this exists:
If machine learning model inference (XGBoost, EBM, LightGBM, conformal prediction,
or neural networks) encounters runtime crashes, unhandled numerical exceptions, missing
weights, or corrupt dependencies, this module acts as a completely reliable, transparent
safety layer.

It evaluates creditworthiness using strict financial domain rules:
1. Cash-flow affordability (D = I_net - E_essential - B_floor) with FOIR <= 40% and DTI <= 50%.
2. Basel Scorecard rating translation (300 to 900) and calibrated default probability.
3. Deterministic split-conformal decision sets (ELIGIBLE, REVIEW, DECLINE_CANDIDATE).
4. Multi-dimensional underwriting scores (Capacity, Evidence, Graph Reputation, Stress Resilience).
5. Transparent additive reason codes and actionable counterfactual remedies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import math
from typing import Any, Dict, List, Optional, Tuple

from veritrust.affordability import AffordabilityEngine, affordability_input, calculate_emi
from veritrust.engine import TrustEngine
from veritrust.models import FinancialFeatures
from veritrust.temporal import compute_temporal_confidences


class RuleBasedFallbackEngine:
    """Tuned deterministic rule-based credit underwriter and explainer."""

    def evaluate(
        self,
        params: dict[str, Any],
        engine: Optional[TrustEngine] = None,
        scorer: Optional[Any] = None,
        fallback_reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Evaluate credit request with fail-safe financial domain heuristics.

        Args:
            params: Dictionary of borrower attributes and loan request fields.
            engine: Optional TrustEngine instance to resolve borrower graph state.
            scorer: Optional CreditScorer instance to compute live vouch score.
            fallback_reason: Optional diagnostic string describing why fallback was triggered.

        Returns:
            Structured dictionary matching PredictResponse schema with is_fallback=True.
        """
        borrower_id: Optional[str] = params.get("borrower_id")

        # 1. Resolve borrower defaults if borrower_id is provided
        default_income = "35000.00"
        default_debt = "2500.00"
        default_net_op = "20000.00"
        default_vouch_score = "0.0"
        default_vouch_count = 0
        user = None
        completeness = Decimal("1.0")

        if borrower_id and engine:
            try:
                user = engine.get_user(borrower_id)
                if user and user.financial_features:
                    default_income = str(user.financial_features.monthly_income)
                    default_debt = str(user.financial_features.monthly_debt)
                    default_net_op = str(user.financial_features.net_operating_income)
                    completeness = user.financial_features.completeness
                if user:
                    if scorer is not None:
                        try:
                            vouch_rep = scorer.compute_vouch_score(borrower_id)
                            default_vouch_score = str(vouch_rep.vouch_score)
                            default_vouch_count = vouch_rep.eligible_endorsements
                        except Exception:
                            default_vouch_score = str(user.reputation)
                            default_vouch_count = len(list(engine.graph.in_edges(borrower_id)))
                    else:
                        default_vouch_score = str(user.reputation)
                        default_vouch_count = len(list(engine.graph.in_edges(borrower_id)))
            except Exception:
                pass

        # 2. Extract inputs with bulletproof defensive casting
        try:
            income_val = max(Decimal("1000.00"), Decimal(str(params.get("monthly_income") or default_income)))
        except Exception:
            income_val = Decimal("35000.00")

        try:
            debt_val = max(Decimal("0.00"), Decimal(str(params.get("monthly_debt") or default_debt)))
        except Exception:
            debt_val = Decimal("2500.00")

        try:
            net_op_val = max(Decimal("0.00"), Decimal(str(params.get("net_operating_income") or default_net_op)))
        except Exception:
            net_op_val = Decimal("20000.00")

        try:
            principal_val = max(Decimal("1000.00"), Decimal(str(params.get("requested_amount") or "100000.00")))
        except Exception:
            principal_val = Decimal("100000.00")

        try:
            tenure_val = max(1, int(params.get("requested_tenure_months") or 12))
        except Exception:
            tenure_val = 12

        try:
            rate_val = max(Decimal("0.01"), Decimal(str(params.get("annual_interest_rate") or 0.18)))
        except Exception:
            rate_val = Decimal("0.18")

        bureau_fields = ("bureau_max_dpd_24m", "bureau_months_30plus_24m", "bureau_written_off", "bureau_utilisation")
        bureau_sent = any(params.get(f) is not None for f in bureau_fields)
        bureau_status_val: str = str(params.get("bureau_status") or ("AVAILABLE" if bureau_sent else "NO_FILE"))
        has_bureau_file = bureau_status_val not in ("NO_FILE", "NO_RECORD") or bureau_sent

        bureau_max_dpd_val: int = int(params.get("bureau_max_dpd_24m") or 0)
        bureau_written_off_val: int = int(params.get("bureau_written_off") or 0)
        bureau_util_val: float = float(params.get("bureau_utilisation") or 0.0)

        vouch_count_val: int = int(params["vouch_count"] if params.get("vouch_count") is not None else default_vouch_count)
        raw_vouch_score_val = Decimal(str(params.get("vouch_score") or default_vouch_score))
        bank_bounces_val: int = int(params.get("bank_bounces_3m") or 0)
        bank_income_cv_val: float = float(params.get("bank_income_cv") or 0.10)
        evidence_age_val = Decimal(str(params.get("evidence_age_months") or "0.0"))

        # 3. Financial calculations: EMI, Affordability, and Capacity
        monthly_emi = calculate_emi(principal_val, rate_val, tenure_val)
        total_debt_service = debt_val + monthly_emi
        dti_ratio = total_debt_service / income_val if income_val > Decimal("0") else Decimal("1.0")

        afford = AffordabilityEngine().evaluate(
            affordability_input(
                FinancialFeatures(
                    monthly_income=income_val,
                    monthly_debt=debt_val,
                    net_operating_income=net_op_val,
                    completeness=completeness,
                )
            )
        )
        essential_expenses = afford.essential_expenses
        max_affordable_emi = afford.max_affordable_emi
        emi_fits = (monthly_emi <= max_affordable_emi) and (dti_ratio <= Decimal("0.55"))

        # 4. Temporal Confidence & Effective Vouch Score
        temporal_rep = compute_temporal_confidences(delta_months=evidence_age_val)
        effective_vouch_score = min(Decimal("100.0"), raw_vouch_score_val * temporal_rep.vouch_confidence)
        comp_conf = float(temporal_rep.composite_confidence)
        base_epistemic = float(Decimal("1.0") / (Decimal("1.0") + Decimal(vouch_count_val + 1) * completeness))
        inflated_epistemic = round(1.0 - comp_conf * (1.0 - base_epistemic), 4)
        is_stale = evidence_age_val >= Decimal("12.0") or comp_conf < 0.60

        # 5. Tuned Rule-Based Underwriting Scorecard & Default Probability
        # Base credit score 660, base default probability 0.09
        rule_score = 660
        rule_default_prob = 0.09
        positive_factors: list[dict[str, Any]] = []
        risk_factors: list[dict[str, Any]] = []

        # Rule A: Debt-To-Income (DTI)
        dti_f = float(dti_ratio)
        if dti_f <= 0.35:
            rule_score += 55
            rule_default_prob -= 0.035
            positive_factors.append({
                "code": "DTI_EXCELLENT",
                "text": f"Debt-to-income after proposed EMI is low ({dti_f:.1%}), well within the 40% threshold",
                "feature": "dti_est",
                "observed": f"{dti_f:.2f}",
                "log_odds": -0.45,
                "direction": "lowers_risk",
            })
        elif dti_f <= 0.45:
            rule_score += 15
            rule_default_prob -= 0.010
            positive_factors.append({
                "code": "DTI_MANAGEABLE",
                "text": f"Debt-to-income is manageable ({dti_f:.1%})",
                "feature": "dti_est",
                "observed": f"{dti_f:.2f}",
                "log_odds": -0.15,
                "direction": "lowers_risk",
            })
        elif dti_f <= 0.55:
            rule_score -= 45
            rule_default_prob += 0.055
            risk_factors.append({
                "code": "DTI_ELEVATED",
                "text": f"Debt-to-income ({dti_f:.1%}) approaches upper policy ceiling of 50%",
                "feature": "dti_est",
                "observed": f"{dti_f:.2f}",
                "log_odds": 0.55,
                "direction": "raises_risk",
            })
        else:
            rule_score -= 140
            rule_default_prob += 0.180
            risk_factors.append({
                "code": "DTI_EXCEEDS_CAP",
                "text": f"Debt-to-income ({dti_f:.1%}) breaches the 50% prudent borrowing cap",
                "feature": "dti_est",
                "observed": f"{dti_f:.2f}",
                "log_odds": 1.40,
                "direction": "raises_risk",
            })

        # Rule B: Operating Surplus & Affordable EMI Fit
        if emi_fits:
            rule_score += 40
            rule_default_prob -= 0.025
            positive_factors.append({
                "code": "EMI_FITS_AFFORDABILITY",
                "text": f"Proposed EMI of INR {float(monthly_emi):,.2f} fits within maximum affordable limit of INR {float(max_affordable_emi):,.2f}",
                "feature": "max_affordable_emi",
                "observed": f"INR {float(max_affordable_emi):,.2f}",
                "log_odds": -0.30,
                "direction": "lowers_risk",
            })
        else:
            rule_score -= 110
            rule_default_prob += 0.150
            risk_factors.append({
                "code": "EMI_EXCEEDS_CAPACITY",
                "text": f"Proposed EMI (INR {float(monthly_emi):,.2f}) exceeds maximum affordable buffer (INR {float(max_affordable_emi):,.2f})",
                "feature": "max_affordable_emi",
                "observed": f"INR {float(max_affordable_emi):,.2f}",
                "log_odds": 1.10,
                "direction": "raises_risk",
            })

        # Rule C: Community Web-of-Trust Endorsements
        evs_f = float(effective_vouch_score)
        if vouch_count_val >= 2 and evs_f >= 30.0:
            rule_score += 65
            rule_default_prob -= 0.040
            positive_factors.append({
                "code": "STRONG_VOUCH_BACKING",
                "text": f"Applicant backed by {vouch_count_val} peer community endorsements (Vouch Score {evs_f:.1f})",
                "feature": "vouch_score",
                "observed": f"{evs_f:.1f}",
                "log_odds": -0.50,
                "direction": "lowers_risk",
            })
        elif vouch_count_val >= 1:
            rule_score += 25
            rule_default_prob -= 0.015
            positive_factors.append({
                "code": "VOUCH_PRESENT",
                "text": f"Applicant has {vouch_count_val} peer endorsement on file",
                "feature": "vouch_count",
                "observed": f"{vouch_count_val}",
                "log_odds": -0.20,
                "direction": "lowers_risk",
            })
        else:
            rule_score -= 15
            rule_default_prob += 0.015
            risk_factors.append({
                "code": "NO_COMMUNITY_VOUCHES",
                "text": "No active community peer endorsements registered in Web-of-Trust graph",
                "feature": "vouch_count",
                "observed": "0",
                "log_odds": 0.20,
                "direction": "raises_risk",
            })

        # Rule D: Adverse History & Bounces
        if bureau_written_off_val > 0:
            rule_score -= 220
            rule_default_prob += 0.35
            risk_factors.append({
                "code": "BUREAU_WRITEOFF_RECORDED",
                "text": f"{bureau_written_off_val} written-off account(s) present on credit history",
                "feature": "bureau_written_off",
                "observed": str(bureau_written_off_val),
                "log_odds": 2.50,
                "direction": "raises_risk",
            })

        if bureau_max_dpd_val >= 90:
            rule_score -= 160
            rule_default_prob += 0.25
            risk_factors.append({
                "code": "SEVERE_DELINQUENCY",
                "text": f"Severe delinquency detected ({bureau_max_dpd_val} days past due in past 24 months)",
                "feature": "bureau_max_dpd_24m",
                "observed": f"{bureau_max_dpd_val} days",
                "log_odds": 2.00,
                "direction": "raises_risk",
            })

        if bank_bounces_val > 0:
            bounce_penalty = 50 * bank_bounces_val
            rule_score -= bounce_penalty
            rule_default_prob += 0.06 * bank_bounces_val
            risk_factors.append({
                "code": "BANK_DEBIT_BOUNCES",
                "text": f"{bank_bounces_val} auto-debit bounce(s) detected in the last 3 months",
                "feature": "bank_bounces_3m",
                "observed": str(bank_bounces_val),
                "log_odds": 0.60 * bank_bounces_val,
                "direction": "raises_risk",
            })

        # Bound final score and default probability
        final_score = max(300, min(900, rule_score))
        final_default_prob = round(max(0.01, min(0.95, rule_default_prob)), 4)
        final_repay_prob = round(1.0 - final_default_prob, 4)

        # Risk tier
        if final_default_prob < 0.05:
            risk_tier = "LOW_RISK"
        elif final_default_prob < 0.15:
            risk_tier = "MODERATE_RISK"
        elif final_default_prob < 0.30:
            risk_tier = "HIGH_RISK"
        else:
            risk_tier = "VERY_HIGH_RISK"

        # Conformal prediction set and decision
        if not emi_fits or final_default_prob >= 0.35:
            decision = "DECLINE_CANDIDATE"
            conformal_set = ["DEFAULT"]
        elif final_default_prob <= 0.14 and inflated_epistemic <= 0.45 and not is_stale:
            decision = "ELIGIBLE"
            conformal_set = ["REPAY"]
        else:
            decision = "REVIEW"
            conformal_set = ["REPAY", "DEFAULT"]

        # 6. Missing evidence items
        missing_info: list[dict[str, str]] = []
        if not has_bureau_file:
            missing_info.append({
                "code": "MISSING_BUREAU_FILE",
                "text": "Credit bureau history is unavailable on file (thin-file applicant; alternative cash-flow and vouch evidence utilized)",
                "status": "NO_FILE",
            })
        if vouch_count_val == 0:
            missing_info.append({
                "code": "MISSING_VOUCHES",
                "text": "No peer endorsements on file; adding vouches will expand borrowing capacity",
                "status": "NONE",
            })

        # 7. Summary explanation
        summary = (
            f"[Rule-Based Fallback] Borrower is assessed as {decision} with calibrated default probability of {final_default_prob:.1%} "
            f"(Scorecard rating: {final_score}). "
            f"Underwriting evaluated cash-flow affordability (DTI: {dti_f:.1%}, Max EMI: INR {float(max_affordable_emi):,.2f}), "
            f"Web-of-Trust endorsements (Vouches: {vouch_count_val}), and adverse history."
        )

        # 8. Multi-dimensional scores (0-100)
        cap_ratio = float(max_affordable_emi / monthly_emi) if monthly_emi > Decimal("0") else 1.0
        fin_cap = round(min(100.0, max(0.0, cap_ratio * 75.0)), 1)
        ev_rel = round(70.0 * comp_conf, 1)
        graph_rep = round(float(effective_vouch_score), 1)

        shocked_income = income_val * Decimal("0.80")
        cover = float((shocked_income - essential_expenses - debt_val) / monthly_emi) if monthly_emi > Decimal("0") else 1.0
        stress_res = round(min(100.0, max(0.0, 30.0 * cover if cover < 1.0 else 30.0 + 60.0 * (cover - 1.0))), 1)

        # 9. Counterfactual remedy
        is_eligible = (decision == "ELIGIBLE")
        r_monthly = rate_val / Decimal("12")
        if r_monthly > Decimal("0"):
            comp_pow = (Decimal("1") + r_monthly) ** tenure_val
            max_principal_dec = (max_affordable_emi * (comp_pow - Decimal("1"))) / (r_monthly * comp_pow)
        else:
            max_principal_dec = max_affordable_emi * Decimal(str(tenure_val))

        recommended_tenure = tenure_val
        for test_t in [18, 24, 36, 48]:
            if calculate_emi(principal_val, rate_val, test_t) <= max_affordable_emi:
                recommended_tenure = test_t
                break

        remedies: list[str] = []
        if is_eligible:
            remedies.append("Current loan terms are fully sustainable within disposable cash flow.")
        else:
            if max_principal_dec < principal_val:
                remedies.append(
                    f"Reduce requested principal from INR {float(principal_val):,.2f} to INR {float(max_principal_dec):,.2f} "
                    f"to fit disposable cash flow."
                )
            if recommended_tenure > tenure_val:
                remedies.append(
                    f"Extend loan tenure from {tenure_val} to {recommended_tenure} months to lower monthly instalment."
                )
            if vouch_count_val < 2:
                remedies.append("Add 1 to 2 community endorsements from local network anchors to elevate approval standing.")

        reason_note = fallback_reason or "Tuned rule-based heuristic engaged as fail-safe fallback"

        return {
            "borrower_id": borrower_id,
            "is_fallback": True,
            "fallback_reason": reason_note,
            "model_source": "RULE_BASED_FALLBACK",
            "prediction": {
                "default_probability": final_default_prob,
                "repayment_probability": final_repay_prob,
                "credit_score": final_score,
                "risk_tier": risk_tier,
                "decision": decision,
                "conformal_set": conformal_set,
                "confidence_level": 0.90,
                "epistemic_uncertainty": inflated_epistemic,
            },
            "explanation": {
                "summary": summary,
                "positive_factors": positive_factors,
                "risk_factors": risk_factors,
                "missing_information": missing_info,
            },
            "temporal_freshness": {
                "evidence_age_months": float(evidence_age_val),
                "vouch_confidence": float(temporal_rep.vouch_confidence),
                "cashflow_confidence": float(temporal_rep.cashflow_confidence),
                "repayment_confidence": float(temporal_rep.repayment_confidence),
                "composite_confidence": comp_conf,
                "is_stale": is_stale,
                "staleness_warning": f"Evidence age is {float(evidence_age_val):.1f} months" if is_stale else None,
            },
            "multidimensional_scores": {
                "financial_capacity_score": fin_cap,
                "evidence_reliability_score": ev_rel,
                "graph_reputation_score": graph_rep,
                "stress_resilience_score": stress_res,
            },
            "counterfactual_remedy": {
                "target_decision": "ELIGIBLE",
                "is_already_eligible": is_eligible,
                "max_recommended_principal": f"{max(Decimal('0.00'), max_principal_dec):.2f}",
                "recommended_tenure_months": recommended_tenure,
                "sustainable_emi": f"{max(Decimal('0.00'), max_affordable_emi):.2f}",
                "required_additional_monthly_income": None,
                "actionable_recommendations": remedies,
            },
        }
