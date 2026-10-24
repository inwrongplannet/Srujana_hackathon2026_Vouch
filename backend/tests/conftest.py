"""Pytest fixtures for VeriTrust test suite."""

from decimal import Decimal
import pytest
from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer


@pytest.fixture
def empty_engine() -> TrustEngine:
    """Fixture providing an empty TrustEngine."""
    return TrustEngine()


@pytest.fixture
def linear_chain_engine() -> TrustEngine:
    """Fixture providing: ANCHOR (R=10) -> ALICE (R=6) -> BOB (R=0)."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("6.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))
    engine.vouch("ANCHOR", "ALICE")
    engine.vouch("ALICE", "BOB")
    return engine


@pytest.fixture
def multi_anchor_diamond_engine() -> TrustEngine:
    """Fixture providing a diamond graph with two anchors:

    ANCHOR1 (R=10) --> A (R=4) --> TARGET (R=0)
    ANCHOR2 (R=8)  --> B (R=6) --> TARGET (R=0)
    """
    engine = TrustEngine()
    engine.create_user("ANCHOR1", "Anchor 1", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("ANCHOR2", "Anchor 2", initial_reputation=Decimal("8.0"), is_anchor=True)
    engine.create_user("A", "Node A", initial_reputation=Decimal("4.0"))
    engine.create_user("B", "Node B", initial_reputation=Decimal("6.0"))
    engine.create_user("TARGET", "Target Borrower", initial_reputation=Decimal("0.0"))

    engine.vouch("ANCHOR1", "A")
    engine.vouch("ANCHOR2", "B")
    engine.vouch("A", "TARGET")
    engine.vouch("B", "TARGET")
    return engine


@pytest.fixture
def standard_lending_setup() -> tuple[TrustEngine, CreditScorer, LendingService]:
    """Fixture with institutional anchor, sponsor, and borrower with financial records."""
    engine = TrustEngine()
    engine.create_user("ROOT_ANCHOR", "Root Anchor", initial_reputation=Decimal("20.0"), is_anchor=True)
    engine.create_user("SPONSOR", "Sponsor", initial_reputation=Decimal("10.0"))
    engine.create_user(
        "BORROWER",
        "Borrower",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("40000.00"),
            monthly_debt=Decimal("6000.00"),
            net_operating_income=Decimal("24000.00"),
            debt_service=Decimal("6000.00"),
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

