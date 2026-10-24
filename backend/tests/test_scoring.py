"""Unit tests for credibility propagation, hop decay, cycle absorption, and scoring."""

from decimal import Decimal
import pytest
from veritrust.engine import TrustEngine
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer


def test_linear_chain_hop_decay():
    """Verify geometric hop attenuation along a linear chain from an anchor.

    Chain: ANCHOR (R=10) -> ALICE (R=6) -> BOB
    First hop (ANCHOR -> ALICE): weight = 10.0 (no decay, hop 0)
    Second hop (ALICE -> BOB): weight = 6.0, decayed by X = 0.5 -> 3.0
    Expected path trust = 10.0 * 3.0 = 30.0
    """
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("6.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))

    engine.vouch("ANCHOR", "ALICE")
    engine.vouch("ALICE", "BOB")

    scorer = CreditScorer(engine)
    r_graph, paths = scorer.compute_r_graph("BOB")

    assert len(paths) == 1
    assert paths[0].path == ["ANCHOR", "ALICE", "BOB"]
    assert paths[0].path_trust == Decimal("30.0")
    assert r_graph == Decimal("30.0")


def test_cycle_absorption():
    """Verify that cycles (e.g. ANCHOR -> ALICE -> BOB -> ALICE) are absorbed at 0 trust."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("6.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("4.0"))

    engine.vouch("ANCHOR", "ALICE")
    engine.vouch("ALICE", "BOB")
    engine.vouch("BOB", "ALICE")  # Closes a cycle: ALICE -> BOB -> ALICE

    scorer = CreditScorer(engine)
    # Target ALICE: should receive trust only from direct ANCHOR -> ALICE, cycle from BOB -> ALICE absorbed
    r_graph_alice, paths_alice = scorer.compute_r_graph("ALICE")
    assert r_graph_alice == Decimal("10.0")

    # Target BOB: trust via ANCHOR -> ALICE -> BOB
    r_graph_bob, paths_bob = scorer.compute_r_graph("BOB")
    # Alice now has 1 out edge (BOB), so weight is 6.0
    # Bob path trust = 10.0 * (6.0 * 0.5) = 30.0
    assert r_graph_bob == Decimal("30.0")


def test_cold_start_vs_rich_file_uncertainty():
    """Verify that cold-start borrower has maximum uncertainty (sigma2=1.0) and lower LCB."""
    engine = TrustEngine()
    engine.create_user("COLD_START", "Cold Start User", initial_reputation=Decimal("0.0"))
    engine.create_user(
        "RICH_FILE",
        "Rich File User",
        initial_reputation=Decimal("5.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("50000.00"),
            monthly_debt=Decimal("5000.00"),
            net_operating_income=Decimal("35000.00"),
            debt_service=Decimal("5000.00"),
            income_volatility=Decimal("0.05"),
            cashflow_volatility=Decimal("0.05"),
            completeness=Decimal("1.0"),
        ),
    )
    rich_user = engine.get_user("RICH_FILE")
    rich_user.n_settled_loans = 3

    scorer = CreditScorer(engine)

    # Cold start assessment
    cold_assessment = scorer.assess_credit("COLD_START")
    assert cold_assessment.sigma2_epistemic == Decimal("1.0")
    assert cold_assessment.score_final <= Decimal("0.0")
    assert cold_assessment.max_loan_limit == Decimal("0.00")

    # Rich file assessment
    rich_assessment = scorer.assess_credit("RICH_FILE")
    assert rich_assessment.sigma2_epistemic < Decimal("0.3")
    assert rich_assessment.s_cashflow > Decimal("0.8")
    assert rich_assessment.score_final > Decimal("0.0")
    assert rich_assessment.max_loan_limit > Decimal("0.00")

