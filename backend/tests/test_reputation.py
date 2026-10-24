"""Critical tests for reputation updates, repayments, and the atomic 4-level slashing cascade.

Enforces:
1. Repayment awards settlement boost to borrower and sponsors.
2. Default cascade follows exact mathematical fractions:
   k=0 (Defaulter): -delta0, status DEFAULTED, capacity frozen (C=0), outbound weights zeroed.
   k=1 (Direct sponsor): -0.5 * W_AB * delta0. If R < 0 -> RESTRICTED.
   k=2 (Transitive ancestor): -0.25 * delta0.
   k>=3: delta = 0 (Hard boundary cutoff).
"""

from decimal import Decimal
import pytest
from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer


def test_repayment_reputation_minting(standard_lending_setup: tuple[TrustEngine, CreditScorer, LendingService]):
    """Successful settlement mints reputation to borrower and awards sponsor yield."""
    engine, scorer, lending = standard_lending_setup
    borrower = engine.get_user("BORROWER")
    sponsor = engine.get_user("SPONSOR")

    init_borrower_r = borrower.reputation
    init_sponsor_r = sponsor.reputation

    # Borrow half approved limit
    assessment = scorer.assess_credit("BORROWER")
    loan = lending.borrow("BORROWER", assessment.max_loan_limit / Decimal("2.0"))

    # Repay in full
    lending.repay(loan.loan_id, loan.outstanding_balance)

    assert loan.status == "REPAID"
    assert borrower.n_settled_loans == 1
    assert borrower.reputation == init_borrower_r + lending.borrower_reward
    assert sponsor.reputation == init_sponsor_r + lending.sponsor_reward


def test_4_level_slashing_cascade_exact_fractions():
    """Verify exact 4-level slashing cascade with k=3 cutoff.

    Topology:
      K3_NODE (R=30) -> K2_ANCESTOR (R=20) -> K1_SPONSOR (R=10) -> K0_DEFAULTER (R=0)
    All edges single outgoing, so edge weight = node capacity.
    """
    engine = TrustEngine()
    engine.create_user("K3_NODE", "Distance 3 Node", initial_reputation=Decimal("30.0"), is_anchor=True)
    engine.create_user("K2_ANCESTOR", "Distance 2 Ancestor", initial_reputation=Decimal("20.0"))
    engine.create_user("K1_SPONSOR", "Distance 1 Sponsor", initial_reputation=Decimal("10.0"))
    engine.create_user(
        "K0_DEFAULTER",
        "Borrower Defaulter",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            net_operating_income=Decimal("30000.00"),
            debt_service=Decimal("5000.00"),
            completeness=Decimal("1.0"),
        ),
    )

    # Establish linear chain
    engine.vouch("K3_NODE", "K2_ANCESTOR")
    engine.vouch("K2_ANCESTOR", "K1_SPONSOR")
    engine.vouch("K1_SPONSOR", "K0_DEFAULTER")

    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)

    # Issue loan
    assessment = scorer.assess_credit("K0_DEFAULTER")
    assert assessment.max_loan_limit > Decimal("0.0")
    loan = lending.borrow("K0_DEFAULTER", assessment.max_loan_limit / Decimal("2.0"))

    # Trigger default with delta0 = 10.0
    delta0 = Decimal("10.0")
    lending.default_loan(loan.loan_id, delta0=delta0)

    # Verify Level k = 0: Defaulter
    k0 = engine.get_user("K0_DEFAULTER")
    assert k0.status == "DEFAULTED"
    assert k0.capacity == Decimal("0.0")
    assert k0.reputation == Decimal("-10.0")

    # Verify Level k = 1: Sponsor
    # delta1 = 0.5 * W_K1_K0 * delta0
    # W_K1_K0 = 10.0 / 1 = 10.0 -> delta1 = 0.5 * 10.0 * 10.0 = 50.0
    # K1 reputation drops from 10.0 to 10.0 - 50.0 = -40.0 -> status RESTRICTED
    k1 = engine.get_user("K1_SPONSOR")
    assert k1.reputation == Decimal("10.0") - Decimal("50.0")
    assert k1.status == "RESTRICTED"
    assert k1.capacity == Decimal("0.0")

    # Verify Level k = 2: Ancestor
    # delta2 = 0.25 * delta0 = 0.25 * 10.0 = 2.5
    # K2 reputation drops from 20.0 to 20.0 - 2.5 = 17.5 -> status ACTIVE
    k2 = engine.get_user("K2_ANCESTOR")
    assert k2.reputation == Decimal("20.0") - Decimal("2.5")
    assert k2.status == "ACTIVE"

    # Verify Level k >= 3: Cutoff isolation
    # delta3 = 0.0 -> K3 reputation remains exactly 30.0
    k3 = engine.get_user("K3_NODE")
    assert k3.reputation == Decimal("30.0")
    assert k3.status == "ACTIVE"


def test_defaulted_node_cannot_vouch(standard_lending_setup: tuple[TrustEngine, CreditScorer, LendingService]):
    """A defaulted node is blocked from vouching."""
    engine, scorer, lending = standard_lending_setup
    assessment = scorer.assess_credit("BORROWER")
    loan = lending.borrow("BORROWER", assessment.max_loan_limit / Decimal("2.0"))
    lending.default_loan(loan.loan_id)

    engine.create_user("NEW_NODE", "New Node", initial_reputation=Decimal("0.0"))

    # Borrowed node is DEFAULTED and capacity is 0
    with pytest.raises(ValueError, match="cannot vouch"):
        engine.vouch("BORROWER", "NEW_NODE")

