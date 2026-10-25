"""Unit tests for temporal uncertainty, evidence freshness decay, and recovery.

Tests:
1. Half-life confidence function matches known mathematical values.
2. Multi-horizon asymmetric decay (cash flows decay faster than vouches, vouches faster than repayments).
3. Epistemic uncertainty inflation over time (sigma2 -> 1.0 as delta_t -> inf).
4. Vouch Score graceful decay over elapsed months.
5. Lower Confidence Bound (LCB) loan limit reduction without reputation slashing.
6. Evidence rejuvenation: single bank statement refresh or vouch re-affirmation restores credit capacity.
7. Defaulted user isolation.
"""

from decimal import Decimal
import pytest

from veritrust.engine import TrustEngine
from veritrust.models import FinancialFeatures, User
from veritrust.scoring import CreditScorer
from veritrust.temporal import (
    assess_credit_temporal,
    compute_half_life_decay,
    compute_temporal_confidences,
    compute_temporal_epistemic_uncertainty,
    compute_temporal_vouch_score,
    simulate_rejuvenation_scenarios,
    simulate_temporal_trajectory,
)


def test_half_life_confidence_known_values():
    """Verify C(t) = 2^(-t / H) against known mathematical answers."""
    h = Decimal("24.0")  # 2-year half-life

    # Month 0: 2^0 = 1.0
    c_0 = compute_half_life_decay(Decimal("0.0"), h)
    assert c_0 == Decimal("1.0000")

    # Month 12 (1 year): 2^(-0.5) = 1 / sqrt(2) approx 0.7071
    c_12 = compute_half_life_decay(Decimal("12.0"), h)
    assert abs(c_12 - Decimal("0.7071")) <= Decimal("0.0002")

    # Month 24 (2 years = 1 half-life): 2^(-1) = 0.5000
    c_24 = compute_half_life_decay(Decimal("24.0"), h)
    assert c_24 == Decimal("0.5000")

    # Month 48 (4 years = 2 half-lives): 2^(-2) = 0.2500
    c_48 = compute_half_life_decay(Decimal("48.0"), h)
    assert c_48 == Decimal("0.2500")

    # Month 60 (5 years): 2^(-2.5) approx 0.1768 (matching the user's specification table)
    c_60 = compute_half_life_decay(Decimal("60.0"), h)
    assert abs(c_60 - Decimal("0.1768")) <= Decimal("0.0002")

    # Negative delta_t should clamp to 1.0
    assert compute_half_life_decay(Decimal("-5.0"), h) == Decimal("1.0")


def test_multi_horizon_asymmetric_decay():
    """Verify that cash flows decay faster than vouches, which decay faster than repayments."""
    m_12 = Decimal("12.0")  # 1 year elapsed
    conf = compute_temporal_confidences(m_12)

    # Cash flow half-life is 6 months -> at 12m, C_cf = 2^(-2) = 0.25
    assert conf.cashflow_confidence == Decimal("0.2500")

    # Vouch half-life is 24 months -> at 12m, C_v = 2^(-0.5) approx 0.7071
    assert abs(conf.vouch_confidence - Decimal("0.7071")) <= Decimal("0.0002")

    # Repayment half-life is 36 months -> at 12m, C_r = 2^(-1/3) approx 0.7937
    assert abs(conf.repayment_confidence - Decimal("0.7937")) <= Decimal("0.0002")

    # Hierarchy invariant: C_cashflow < C_vouch < C_repayment
    assert conf.cashflow_confidence < conf.vouch_confidence < conf.repayment_confidence


@pytest.fixture
def populated_engine():
    """Build a standard engine fixture with an anchor, voucher, and borrower."""
    engine = TrustEngine()
    engine.create_user(user_id="ANCHOR", name="State Bank", initial_reputation=Decimal("20.0"), is_anchor=True)
    engine.create_user(user_id="VOUCHER", name="Meena", initial_reputation=Decimal("10.0"), is_anchor=False)
    engine.create_user(
        user_id="BORROWER",
        name="Lakshmi",
        initial_reputation=Decimal("2.0"),
        is_anchor=False,
        financial_features=FinancialFeatures(
            monthly_income=Decimal("35000.00"),
            monthly_debt=Decimal("3000.00"),
            net_operating_income=Decimal("25000.00"),
            debt_service=Decimal("3000.00"),
            income_volatility=Decimal("0.10"),
            cashflow_volatility=Decimal("0.10"),
            completeness=Decimal("0.90"),
        ),
    )
    engine.vouch("ANCHOR", "VOUCHER")
    engine.vouch("VOUCHER", "BORROWER")
    return engine


def test_epistemic_uncertainty_inflation(populated_engine):
    """Verify that epistemic uncertainty sigma2 inflates monotonically as evidence ages."""
    scorer = CreditScorer(populated_engine)
    user = populated_engine.get_user("BORROWER")

    sigma_0 = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("0.0")).sigma2_temporal
    sigma_12 = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("12.0")).sigma2_temporal
    sigma_24 = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("24.0")).sigma2_temporal
    sigma_60 = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("60.0")).sigma2_temporal

    # Uncertainty increases monotonically with elapsed time
    assert sigma_0 < sigma_12 < sigma_24 < sigma_60

    # At 5 years without fresh data, uncertainty approaches 1.0 (cold-start baseline)
    assert sigma_60 > Decimal("0.90")


def test_vouch_score_temporal_decay(populated_engine):
    """Verify that the bounded Vouch Score (0-100) decreases gracefully over time."""
    scorer = CreditScorer(populated_engine)

    vs_0 = compute_temporal_vouch_score(scorer, "BORROWER", delta_months=Decimal("0.0"))
    vs_12 = compute_temporal_vouch_score(scorer, "BORROWER", delta_months=Decimal("12.0"))
    vs_24 = compute_temporal_vouch_score(scorer, "BORROWER", delta_months=Decimal("24.0"))
    vs_60 = compute_temporal_vouch_score(scorer, "BORROWER", delta_months=Decimal("60.0"))

    assert vs_0.vouch_score > vs_12.vouch_score > vs_24.vouch_score > vs_60.vouch_score
    assert vs_0.confidence in ("MEDIUM", "HIGH")
    assert vs_60.confidence in ("LOW", "MEDIUM")


def test_lcb_limit_graceful_reduction(populated_engine):
    """Verify that approved loan limit decreases without touching or slashing owned reputation."""
    scorer = CreditScorer(populated_engine)
    user_before = populated_engine.get_user("BORROWER")
    initial_reputation = user_before.reputation

    t_0 = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("0.0"))
    t_24 = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("24.0"))
    t_60 = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("60.0"))

    # Loan limit decreases over time
    assert t_0.max_loan_limit > t_24.max_loan_limit > t_60.max_loan_limit > Decimal("0.00")

    # Historical owned reputation R_u remains strictly unchanged (NO SLASHING)
    user_after = populated_engine.get_user("BORROWER")
    assert user_after.reputation == initial_reputation


def test_evidence_rejuvenation_recovery(populated_engine):
    """Verify that re-affirming endorsements or refreshing bank statements recovers credit capacity."""
    scorer = CreditScorer(populated_engine)
    rejuv = simulate_rejuvenation_scenarios(scorer, "BORROWER", stale_months=36)

    stale = rejuv["stale_baseline"]
    bank_only = rejuv["bank_statement_refreshed"]
    vouch_only = rejuv["vouch_reaffirmed"]
    both = rejuv["fully_rejuvenated"]

    # 1. Refreshing bank statement decreases uncertainty and increases limit
    assert bank_only.sigma2_temporal < stale.sigma2_temporal
    assert bank_only.max_loan_limit >= stale.max_loan_limit

    # 2. Re-affirming vouch recovers significant relational capacity
    assert vouch_only.max_loan_limit > stale.max_loan_limit

    # 3. Refreshing both yields the highest recovery
    assert both.max_loan_limit >= vouch_only.max_loan_limit
    assert both.max_loan_limit >= bank_only.max_loan_limit
    assert both.sigma2_temporal < stale.sigma2_temporal


def test_defaulted_user_temporal_isolation(populated_engine):
    """Verify that a defaulted user always receives zero limit regardless of temporal decay."""
    scorer = CreditScorer(populated_engine)
    borrower = populated_engine.get_user("BORROWER")
    borrower.status = "DEFAULTED"

    t_assess = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("0.0"))
    assert t_assess.max_loan_limit == Decimal("0.00")
    assert t_assess.score_final == Decimal("0.0")

    t_assess_aged = assess_credit_temporal(scorer, "BORROWER", delta_months=Decimal("24.0"))
    assert t_assess_aged.max_loan_limit == Decimal("0.00")
