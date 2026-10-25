"""Unit tests for Master Developer Documentation v2 scoring formulas.

Verifies:
1. Endorsement edge weighting w_xy = clamp(r_x * q_x * e_xy * d_xy * (1 - p_xy), 0, 1).
2. Diminishing returns bounded Vouch Score in [0, 100].
3. Outcome-conditioned reputation learning updates.
4. Combined side-by-side assessment generation without conflating bureau and vouch signals.
"""

from decimal import Decimal
import pytest

from veritrust.engine import TrustEngine
from veritrust.models import FinancialFeatures, LoanApplication
from veritrust.scoring import CreditScorer


@pytest.fixture
def test_setup():
    engine = TrustEngine()
    engine.create_user("ANCHOR_BANK", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("8.0"))
    engine.create_user(
        "BOB",
        "Bob",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("35000.00"),
            monthly_debt=Decimal("6000.00"),
            net_operating_income=Decimal("15000.00"),
            debt_service=Decimal("5000.00"),
            income_volatility=Decimal("0.10"),
            completeness=Decimal("1.0"),
        ),
    )
    engine.create_user("CHARLIE", "Charlie", initial_reputation=Decimal("0.0"))
    engine.vouch("ANCHOR_BANK", "ALICE")
    engine.vouch("ALICE", "BOB")
    scorer = CreditScorer(engine)
    return engine, scorer


def test_endorsement_edge_weight_formula():
    """Verify w_xy = clamp(r_x * q_x * e_xy * d_xy * (1 - p_xy), 0, 1)."""
    # Standard healthy vouch
    w1 = CreditScorer.compute_endorsement_weight(
        r_x=Decimal("0.8"),
        q_x=Decimal("1.0"),
        e_xy=Decimal("1.0"),
        d_xy=Decimal("1.0"),
        p_xy=Decimal("0.0"),
    )
    assert w1 == Decimal("0.8")

    # High penalty p_xy = 0.5 reduces weight by half
    w2 = CreditScorer.compute_endorsement_weight(
        r_x=Decimal("0.8"),
        q_x=Decimal("1.0"),
        e_xy=Decimal("1.0"),
        d_xy=Decimal("1.0"),
        p_xy=Decimal("0.5"),
    )
    assert w2 == Decimal("0.40")

    # Clamping boundaries [0, 1]
    w_over = CreditScorer.compute_endorsement_weight(r_x=Decimal("1.5"))
    assert w_over == Decimal("1.0")

    w_neg = CreditScorer.compute_endorsement_weight(r_x=Decimal("-0.5"))
    assert w_neg == Decimal("0.0")


def test_vouch_score_cold_start_vs_endorsed(test_setup):
    """Verify cold-start node receives 0 vouch score while endorsed node receives bounded score."""
    engine, scorer = test_setup

    # Charlie has 0 incoming endorsements
    vouch_charlie = scorer.compute_vouch_score("CHARLIE")
    assert vouch_charlie.vouch_score == Decimal("0")
    assert vouch_charlie.eligible_endorsements == 0
    assert vouch_charlie.status == "PROVISIONAL"

    # Bob has endorsement from Alice
    vouch_bob = scorer.compute_vouch_score("BOB")
    assert vouch_bob.vouch_score > Decimal("0")
    assert vouch_bob.vouch_score <= Decimal("100")
    assert vouch_bob.eligible_endorsements == 1
    assert vouch_bob.confidence in ("MEDIUM", "HIGH")


def test_reputation_update_formula():
    """Verify outcome-conditioned reputation delta: delta = eta * w * (y - p) * rho."""
    old_rep = Decimal("5.0")

    # Successful repayment: y = 1, expected p = 0.90 -> error = +0.10
    updated_success = CreditScorer.compute_reputation_update(
        old_reputation=old_rep,
        outcome_y=1,
        expected_p=Decimal("0.90"),
        learning_rate=Decimal("0.10"),
    )
    assert updated_success > old_rep

    # Default event: y = 0, expected p = 0.90 -> error = -0.90
    updated_default = CreditScorer.compute_reputation_update(
        old_reputation=old_rep,
        outcome_y=0,
        expected_p=Decimal("0.90"),
        learning_rate=Decimal("0.10"),
    )
    assert updated_default < old_rep


def test_combined_assessment_unblended_signals(test_setup):
    """Verify combined assessment presents bureau, vouch, and affordability as separate signals."""
    engine, scorer = test_setup

    app = LoanApplication(
        application_id="APP_TEST_001",
        borrower_id="BOB",
        principal=Decimal("40000.00"),
        annual_rate=Decimal("0.12"),
        term_months=12,
    )

    combined = scorer.assess_combined(
        borrower_id="BOB",
        loan_app=app,
        bureau_status="NO_FILE",
        bureau_score=None,
    )

    # 1. Bureau status is NO_FILE and score is None (not zeroed!)
    assert combined.bureau.status == "NO_FILE"
    assert combined.bureau.score is None

    # 2. Vouch score is present and distinct
    assert combined.vouch.vouch_score > Decimal("0")

    # 3. Affordability evaluated
    assert combined.affordability["status"] in ("SUFFICIENT", "BORDERLINE")

    # 4. Reason codes include positive factors
    pos_codes = [f["code"] for f in combined.positive_factors]
    assert "INCOME_PRESENT" in pos_codes
    assert "COMMUNITY_VOUCH_ACTIVE" in pos_codes

    # 5. Missing info lists thin-file status
    assert any("thin-file" in m or "bureau" in m for m in combined.missing_information)
