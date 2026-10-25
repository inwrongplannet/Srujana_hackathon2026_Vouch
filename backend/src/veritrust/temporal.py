"""Temporal uncertainty and evidence freshness decay engine.

Implements:
1. Multi-horizon confidence decay functions (exponential and half-life parameterized).
2. Asymmetric temporal horizons for cash flows (fast), vouches (medium), and repayment track records (slow).
3. Freshness-weighted effective credibility G_effective(u, t) and cash-flow capacity S_D(t).
4. Temporal epistemic uncertainty inflation: sigma2(t) -> 1.0 as evidence ages.
5. Freshness-adjusted Lower Confidence Bound (LCB) loan limit derivations.
6. Longitudinal decay trajectory simulations and re-affirmation recovery modeling.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from veritrust.config import get_settings
from veritrust.engine import TrustEngine
from veritrust.models import (
    CreditAssessment,
    TemporalConfidenceReport,
    TemporalCreditAssessment,
    TemporalSimulationSnapshot,
    User,
    VouchScoreReport,
)
from veritrust.scoring import CreditScorer, _decimal_exp

# High-precision natural logarithm of 2 for exact Decimal half-life decay
_LN2 = Decimal("0.6931471805599453094172321215")


def compute_half_life_decay(delta_months: Decimal, half_life_months: Decimal) -> Decimal:
    """Calculate confidence factor C(t) = 2^(-delta_t / H) using strict Decimal math.

    Formula:
        2^(-x) = exp(-x * ln(2)) where x = delta_t / H

    Args:
        delta_months: Elapsed time in months since evidence was observed or refreshed.
        half_life_months: Duration in months after which confidence halves.

    Returns:
        Confidence factor in [0.0, 1.0] as Decimal.
    """
    if delta_months <= Decimal("0.0"):
        return Decimal("1.0")
    if half_life_months <= Decimal("0.0"):
        return Decimal("0.0")

    ratio = delta_months / half_life_months
    exponent = -ratio * _LN2
    raw = _decimal_exp(exponent)
    return min(Decimal("1.0"), max(Decimal("0.0"), raw.quantize(Decimal("0.0001"))))


def compute_exponential_decay(delta_months: Decimal, gamma: Decimal) -> Decimal:
    """Calculate confidence factor C(t) = exp(-gamma * delta_t) using Decimal math.

    Args:
        delta_months: Elapsed time in months.
        gamma: Decay rate per month.

    Returns:
        Confidence factor in [0.0, 1.0].
    """
    if delta_months <= Decimal("0.0"):
        return Decimal("1.0")
    if gamma <= Decimal("0.0"):
        return Decimal("1.0")

    raw = _decimal_exp(-gamma * delta_months)
    return min(Decimal("1.0"), max(Decimal("0.0"), raw.quantize(Decimal("0.0001"))))


def compute_temporal_confidences(
    delta_months: Decimal,
    vouch_age: Optional[Decimal] = None,
    cashflow_age: Optional[Decimal] = None,
    repay_age: Optional[Decimal] = None,
    vouch_half_life: Optional[Decimal] = None,
    cashflow_half_life: Optional[Decimal] = None,
    repay_half_life: Optional[Decimal] = None,
) -> TemporalConfidenceReport:
    """Compute multi-source evidence freshness confidence factors across distinct horizons.

    Args:
        delta_months: General elapsed time in months since last activity.
        vouch_age: Specific age of peer endorsements in months (defaults to delta_months).
        cashflow_age: Specific age of income/statement evidence (defaults to delta_months).
        repay_age: Specific age of last settled loan (defaults to delta_months).
        vouch_half_life: Half-life for peer endorsements (defaults to config: 24 months).
        cashflow_half_life: Half-life for cash flows (defaults to config: 6 months).
        repay_half_life: Half-life for repayment record (defaults to config: 36 months).

    Returns:
        TemporalConfidenceReport containing breakdown of confidence factors.
    """
    settings = get_settings()
    h_v = vouch_half_life if vouch_half_life is not None else settings.vouch_half_life_months
    h_cf = cashflow_half_life if cashflow_half_life is not None else settings.cashflow_half_life_months
    h_r = repay_half_life if repay_half_life is not None else settings.repayment_half_life_months

    t_v = vouch_age if vouch_age is not None else delta_months
    t_cf = cashflow_age if cashflow_age is not None else delta_months
    t_r = repay_age if repay_age is not None else delta_months

    c_vouch = compute_half_life_decay(t_v, h_v)
    c_cashflow = compute_half_life_decay(t_cf, h_cf)
    c_repay = compute_half_life_decay(t_r, h_r)

    # Composite confidence blends primary underwriting signals (60% vouch, 40% cash flow)
    c_composite = (Decimal("0.6") * c_vouch + Decimal("0.4") * c_cashflow).quantize(Decimal("0.0001"))

    return TemporalConfidenceReport(
        vouch_confidence=c_vouch,
        cashflow_confidence=c_cashflow,
        repayment_confidence=c_repay,
        composite_confidence=c_composite,
        delta_months=delta_months,
        half_lives={
            "vouch_months": h_v,
            "cashflow_months": h_cf,
            "repayment_months": h_r,
        },
    )


def compute_temporal_epistemic_uncertainty(
    user: User,
    completeness: Decimal,
    in_degree: int,
    confidence_report: TemporalConfidenceReport,
) -> Decimal:
    """Calculate temporally-inflated epistemic uncertainty sigma2 in [0.0, 1.0].

    As evidence ages, effective observations decay toward zero, causing
    epistemic uncertainty to gracefully inflate toward cold-start level 1.0:

        N_eff = (N_settled * C_repay + in_degree * C_vouch + N_financials * C_cashflow)
        sigma2 = 1.0 / (1.0 + N_eff * completeness * C_composite)

    Args:
        user: Target borrower user node.
        completeness: Profile data completeness fraction.
        in_degree: Count of incoming endorsements.
        confidence_report: Calculated freshness confidences.

    Returns:
        sigma2 in [0.0, 1.0] as Decimal.
    """
    effective_n = (
        (Decimal(user.n_settled_loans) * confidence_report.repayment_confidence)
        + (Decimal(in_degree) * confidence_report.vouch_confidence)
    )
    if user.financial_features is not None:
        effective_n += Decimal("1.0") * confidence_report.cashflow_confidence

    denominator = Decimal("1.0") + (effective_n * completeness * confidence_report.composite_confidence)
    if denominator <= Decimal("0.0"):
        return Decimal("1.0")

    sigma2 = (Decimal("1.0") / denominator).quantize(Decimal("0.0001"))
    return min(Decimal("1.0"), max(Decimal("0.0"), sigma2))


def assess_credit_temporal(
    scorer: CreditScorer,
    user_id: str,
    delta_months: Decimal = Decimal("0.0"),
    vouch_age: Optional[Decimal] = None,
    cashflow_age: Optional[Decimal] = None,
    repay_age: Optional[Decimal] = None,
) -> TemporalCreditAssessment:
    """Produce a temporal freshness-adjusted dual-axis credit assessment.

    Retains historical reputation and evidence intact, while discounting its
    predictive currency in present underwriting via temporal confidence and
    epistemic uncertainty inflation.

    Args:
        scorer: CreditScorer instance.
        user_id: Target borrower user ID.
        delta_months: Elapsed months since observation/activity.
        vouch_age: Optional specific vouch age override.
        cashflow_age: Optional specific cash flow age override.
        repay_age: Optional specific repayment age override.

    Returns:
        TemporalCreditAssessment with unattenuated base and freshness-adjusted outputs.
    """
    user = scorer.engine.get_user(user_id)
    if not user:
        raise ValueError(f"User '{user_id}' does not exist.")

    # 1. Obtain baseline unattenuated assessment
    base = scorer.assess_credit(user_id)

    # 2. Compute multi-source freshness confidences
    conf = compute_temporal_confidences(
        delta_months=delta_months,
        vouch_age=vouch_age,
        cashflow_age=cashflow_age,
        repay_age=repay_age,
    )

    # If defaulted or zero baseline, return zero assessment
    if user.status == "DEFAULTED" or base.score_final <= Decimal("0.0"):
        return TemporalCreditAssessment(
            user_id=user_id,
            base_assessment=base,
            temporal_confidence=conf,
            effective_r_graph=Decimal("0.0"),
            effective_s_cashflow=Decimal("0.0"),
            mu_effective=Decimal("0.0"),
            sigma2_temporal=Decimal("1.0"),
            score_final=Decimal("0.0"),
            max_loan_limit=Decimal("0.00"),
            is_stale=delta_months >= Decimal("12.0"),
        )

    # 3. Apply freshness discount to capacity components
    effective_r_graph = (base.r_graph * conf.vouch_confidence).quantize(Decimal("0.0001"))
    effective_s_cashflow = (base.s_cashflow * conf.cashflow_confidence).quantize(Decimal("0.0001"))

    # 4. Compute freshness-weighted composite capacity mu_effective
    in_edges = list(scorer.engine.graph.in_edges(user_id))
    in_degree = len(in_edges)
    effective_boost_exp = scorer.beta * (
        (Decimal(user.n_settled_loans) * conf.repayment_confidence)
        + (Decimal(in_degree) * conf.vouch_confidence)
    )
    boost_multiplier = _decimal_exp(effective_boost_exp)

    base_cap = (scorer.alpha * effective_r_graph) + ((Decimal("1.0") - scorer.alpha) * effective_s_cashflow)
    mu_effective = (base_cap * boost_multiplier).quantize(Decimal("0.0001"))

    # 5. Compute temporal epistemic uncertainty
    completeness = (
        user.financial_features.completeness if user.financial_features else Decimal("0.0")
    )
    sigma2_temporal = compute_temporal_epistemic_uncertainty(user, completeness, in_degree, conf)

    # 6. Freshness-adjusted Lower Confidence Bound (LCB)
    sigma = sigma2_temporal.sqrt()
    score_final = (mu_effective - (scorer.kappa * sigma)).quantize(Decimal("0.0001"))

    # 7. Approved loan limit
    if score_final > Decimal("0.0"):
        max_loan_limit = (score_final * scorer.base_unit_inr).quantize(Decimal("1.00"))
    else:
        max_loan_limit = Decimal("0.00")

    is_stale = conf.composite_confidence < Decimal("0.50")

    return TemporalCreditAssessment(
        user_id=user_id,
        base_assessment=base,
        temporal_confidence=conf,
        effective_r_graph=effective_r_graph,
        effective_s_cashflow=effective_s_cashflow,
        mu_effective=mu_effective,
        sigma2_temporal=sigma2_temporal,
        score_final=score_final,
        max_loan_limit=max_loan_limit,
        is_stale=is_stale,
    )


def compute_temporal_vouch_score(
    scorer: CreditScorer,
    target_id: str,
    delta_months: Decimal = Decimal("0.0"),
    tau: Decimal = Decimal("3.0"),
) -> VouchScoreReport:
    """Calculate bounded Vouch Score in [0, 100] with temporal edge decay.

    As endorsements age without re-affirmation, effective incoming weights W(t)
    decay by 2^(-delta_t / H_vouch), naturally reducing the Vouch Score.

    Args:
        scorer: CreditScorer instance.
        target_id: Borrower user ID.
        delta_months: Elapsed months since vouch creation or re-affirmation.
        tau: Saturation parameter for diminishing returns (default 3.0).

    Returns:
        VouchScoreReport reflecting freshness-adjusted relational trust.
    """
    user = scorer.engine.get_user(target_id)
    if not user:
        return VouchScoreReport()

    settings = get_settings()
    c_vouch = compute_half_life_decay(delta_months, settings.vouch_half_life_months)
    c_repay = compute_half_life_decay(delta_months, settings.repayment_half_life_months)

    in_edges = list(scorer.engine.graph.in_edges(target_id))
    total_w = Decimal("0.0")
    total_settled = 0
    total_defaults = 0

    for source_id, _ in in_edges:
        edge_data = scorer.engine.graph[source_id][target_id]
        edge_weight = edge_data.get("weight", Decimal("0.0"))
        edge_alpha = edge_data.get("alpha", Decimal("1.0"))
        source_user = scorer.engine.get_user(source_id)
        if not source_user:
            continue

        r_x = min(Decimal("1.0"), max(Decimal("0.0"), source_user.reputation / Decimal("10.0")))
        q_x = Decimal("1.0") if source_user.is_anchor else Decimal("0.85")
        e_xy = Decimal("1.0") if source_user.status == "ACTIVE" else Decimal("0.0")
        d_xy = Decimal("1.0")
        p_xy = Decimal("0.0")

        w_xy = scorer.compute_endorsement_weight(r_x, q_x, e_xy, d_xy, p_xy)
        # Scale incoming edge by temporal freshness confidence C_vouch
        total_w += edge_weight * edge_alpha * w_xy * c_vouch

        total_settled += source_user.n_settled_loans
        if source_user.status == "DEFAULTED":
            total_defaults += 1

    # Laplace smoothing quality factor C tempered by repayment confidence
    c_denom = Decimal(total_settled + total_defaults + 2)
    c_factor = (Decimal(total_settled + 1) / c_denom) * c_repay
    quality = min(Decimal("1.0"), max(Decimal("0.0"), c_factor))

    # Support with diminishing returns: 1 - exp(-W(t) / tau)
    if total_w > Decimal("0.0") and tau > Decimal("0.0"):
        neg_exponent = -(total_w / tau)
        support = Decimal("1.0") - _decimal_exp(neg_exponent)
        support = min(Decimal("1.0"), max(Decimal("0.0"), support))
    else:
        support = Decimal("0.0")

    raw_vouch_score = Decimal("100.0") * support * (Decimal("0.35") + (Decimal("0.65") * quality))
    vouch_score = int(raw_vouch_score.quantize(Decimal("1")))

    # Confidence rating considers both raw count and temporal freshness
    if len(in_edges) >= 3 and total_w >= Decimal("2.0") and c_vouch >= Decimal("0.50"):
        confidence = "HIGH"
    elif len(in_edges) >= 1 and c_vouch >= Decimal("0.25"):
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    status = "PROVISIONAL" if user.n_settled_loans == 0 and not in_edges else "ACTIVE"

    return VouchScoreReport(
        vouch_score=vouch_score,
        status=status,
        confidence=confidence,
        eligible_endorsements=len(in_edges),
        raw_support=support.quantize(Decimal("0.0001")),
        quality_factor=quality.quantize(Decimal("0.0001")),
    )


def simulate_temporal_trajectory(
    scorer: CreditScorer,
    user_id: str,
    months: Optional[list[int]] = None,
) -> list[TemporalSimulationSnapshot]:
    """Simulate the longitudinal trajectory of a borrower over elapsed months.

    Demonstrates how credit limits, uncertainty, and Vouch Scores evolve as
    evidence ages from Month 0 to Month 60 (5 years) without refreshed data.

    Args:
        scorer: CreditScorer instance.
        user_id: Target borrower user ID.
        months: List of month offsets to evaluate (defaults to [0, 6, 12, 18, 24, 36, 48, 60]).

    Returns:
        List of TemporalSimulationSnapshot objects across the time horizon.
    """
    if months is None:
        months = [0, 6, 12, 18, 24, 36, 48, 60]

    trajectory: list[TemporalSimulationSnapshot] = []
    for m in months:
        t_assess = assess_credit_temporal(scorer, user_id, delta_months=Decimal(str(m)))
        v_report = compute_temporal_vouch_score(scorer, target_id=user_id, delta_months=Decimal(str(m)))

        conf_rating = v_report.confidence
        if t_assess.temporal_confidence.composite_confidence < Decimal("0.10"):
            conf_rating = "EXPIRED"

        trajectory.append(
            TemporalSimulationSnapshot(
                month=m,
                vouch_confidence=t_assess.temporal_confidence.vouch_confidence,
                cashflow_confidence=t_assess.temporal_confidence.cashflow_confidence,
                repayment_confidence=t_assess.temporal_confidence.repayment_confidence,
                mu_effective=t_assess.mu_effective,
                sigma2_temporal=t_assess.sigma2_temporal,
                score_final=t_assess.score_final,
                max_loan_limit=t_assess.max_loan_limit,
                vouch_score=v_report.vouch_score,
                confidence_rating=conf_rating,
            )
        )

    return trajectory


def simulate_rejuvenation_scenarios(
    scorer: CreditScorer,
    user_id: str,
    stale_months: int = 36,
) -> dict[str, TemporalCreditAssessment]:
    """Simulate recovery and evidence rejuvenation for a borrower after a multi-year gap.

    Evaluates:
    1. 'stale_baseline': 36 months inactive across all signals.
    2. 'bank_statement_refreshed': Only cash flow refreshed (cashflow_age = 0).
    3. 'vouch_reaffirmed': Only peer endorsements re-affirmed (vouch_age = 0).
    4. 'fully_rejuvenated': Both bank statement and vouch re-affirmed (all ages = 0).

    Args:
        scorer: CreditScorer instance.
        user_id: Target borrower user ID.
        stale_months: Inactivity duration in months (default 36 / 3 years).

    Returns:
        Dictionary mapping scenario names to TemporalCreditAssessment results.
    """
    m_stale = Decimal(str(stale_months))

    stale_base = assess_credit_temporal(
        scorer, user_id, delta_months=m_stale
    )

    bank_refreshed = assess_credit_temporal(
        scorer,
        user_id,
        delta_months=m_stale,
        cashflow_age=Decimal("0.0"),
        vouch_age=m_stale,
        repay_age=m_stale,
    )

    vouch_reaffirmed = assess_credit_temporal(
        scorer,
        user_id,
        delta_months=m_stale,
        cashflow_age=m_stale,
        vouch_age=Decimal("0.0"),
        repay_age=m_stale,
    )

    fully_rejuvenated = assess_credit_temporal(
        scorer,
        user_id,
        delta_months=m_stale,
        cashflow_age=Decimal("0.0"),
        vouch_age=Decimal("0.0"),
        repay_age=m_stale,
    )

    return {
        "stale_baseline": stale_base,
        "bank_statement_refreshed": bank_refreshed,
        "vouch_reaffirmed": vouch_reaffirmed,
        "fully_rejuvenated": fully_rejuvenated,
    }
