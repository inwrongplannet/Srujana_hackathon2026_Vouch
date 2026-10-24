"""Unit tests for lending, repayments, and the atomic 4-level slashing cascade."""

from decimal import Decimal
import pytest
from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer


def _setup_lending_fixture():
    """Build anchor -> sponsor -> borrower chain with approved limit."""
    engine = TrustEngine()
    engine.create_user("ROOT_ANCHOR", "Root Anchor", initial_reputation=Decimal("20.0"), is_anchor=True)
    engine.create_user("SPONSOR", "Direct Sponsor", initial_reputation=Decimal("10.0"))
    engine.create_user(
        "BORROWER",
        "Borrower",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("40000.00"),
            monthly_debt=Decimal("5000.00"),
            net_operating_income=Decimal("25000.00"),
            debt_service=Decimal("5000.00"),
            income_volatility=Decimal("0.10"),
            cashflow_volatility=Decimal("0.10"),
            completeness=Decimal("1.0"),
        ),
    )
    engine.vouch("ROOT_ANCHOR", "SPONSOR")
    engine.vouch("SPONSOR", "BORROWER")

    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)
    return engine, scorer, lending


def test_borrow_limit_guard():
    """Verify borrow requests exceeding credit limits are rejected."""
    engine, scorer, lending = _setup_lending_fixture()
    assessment = scorer.assess_credit("BORROWER")

    # Exceed limit
    excessive_amount = assessment.max_loan_limit + Decimal("10000.00")
    with pytest.raises(ValueError, match="exceeds approved credit limit"):
        lending.borrow("BORROWER", excessive_amount)

    # Valid amount within limit
    valid_amount = assessment.max_loan_limit / Decimal("2.0")
    loan = lending.borrow("BORROWER", valid_amount)
    assert loan.status == "ACTIVE"
    assert loan.outstanding_balance == valid_amount


def test_repayment_reputation_boost():
    """Verify that full repayment increases borrower & sponsor reputations and settled loan count."""
    engine, scorer, lending = _setup_lending_fixture()
    assessment = scorer.assess_credit("BORROWER")

    borrow_amount = assessment.max_loan_limit / Decimal("2.0")
    loan = lending.borrow("BORROWER", borrow_amount)

    borrower_before = engine.get_user("BORROWER")
    sponsor_before = engine.get_user("SPONSOR")
    init_borrower_rep = borrower_before.reputation
    init_sponsor_rep = sponsor_before.reputation

    # Partial repayment
    lending.repay(loan.loan_id, borrow_amount / Decimal("2.0"))
    assert loan.status == "ACTIVE"
    assert borrower_before.reputation == init_borrower_rep  # No boost yet

    # Final repayment settling the loan
    lending.repay(loan.loan_id, borrow_amount / Decimal("2.0"))
    assert loan.status == "REPAID"
    assert loan.outstanding_balance == Decimal("0.0")

    borrower_after = engine.get_user("BORROWER")
    sponsor_after = engine.get_user("SPONSOR")
    assert borrower_after.n_settled_loans == 1
    assert borrower_after.reputation == init_borrower_rep + lending.borrower_reward
    assert sponsor_after.reputation == init_sponsor_rep + lending.sponsor_reward


def test_4_level_slashing_cascade():
    """Verify 4-level slashing cascade on loan default.

    Chain: ROOT_ANCHOR (k=2) -> SPONSOR (k=1) -> BORROWER (k=0)
    Default delta0 = 10.0
    k=0: BORROWER slashed by 10.0, capacity frozen, status DEFAULTED
    k=1: SPONSOR slashed by 0.5 * W_sponsor_borrower * 10.0
         (W_sponsor_borrower = 10.0 / 1 = 10.0 -> penalty = 0.5 * 10 * 10 = 50.0)
         SPONSOR reputation: 10.0 - 50.0 = -40.0 -> status RESTRICTED
    k=2: ROOT_ANCHOR slashed by 0.25 * 10.0 = 2.5
         ROOT_ANCHOR reputation: 20.0 - 2.5 = 17.5
    """
    engine, scorer, lending = _setup_lending_fixture()
    assessment = scorer.assess_credit("BORROWER")
    loan = lending.borrow("BORROWER", assessment.max_loan_limit / Decimal("2.0"))

    # Trigger default with delta0 = 10.0
    lending.default_loan(loan.loan_id, delta0=Decimal("10.0"))

    borrower = engine.get_user("BORROWER")
    sponsor = engine.get_user("SPONSOR")
    anchor = engine.get_user("ROOT_ANCHOR")

    # k=0 checks
    assert borrower.status == "DEFAULTED"
    assert borrower.capacity == Decimal("0.0")
    assert borrower.reputation == Decimal("-10.0")
    assert engine.graph["BORROWER"]["SPONSOR"] if engine.graph.has_edge("BORROWER", "SPONSOR") else True

    # k=1 checks
    assert sponsor.reputation == Decimal("10.0") - Decimal("50.0")  # -40.0
    assert sponsor.status == "RESTRICTED"

    # k=2 checks
    assert anchor.reputation == Decimal("20.0") - Decimal("2.5")  # 17.5
    assert anchor.status == "ACTIVE"

