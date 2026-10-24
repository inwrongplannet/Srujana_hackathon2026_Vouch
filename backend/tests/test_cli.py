"""Unit tests for the CLI commands and state persistence."""

from decimal import Decimal
from pathlib import Path
import pytest
from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer
from veritrust.store import StateStore


def test_state_persistence_roundtrip(tmp_path: Path):
    """Verify that StateStore saves and restores graph, vouches, and loans accurately."""
    store = StateStore(data_dir=tmp_path)
    engine = TrustEngine()
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)

    # Seed data
    anchor = engine.create_user("A1", "Anchor 1", initial_reputation=Decimal("15.0"), is_anchor=True)
    borrower = engine.create_user(
        "B1",
        "Borrower 1",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(net_operating_income=Decimal("30000.00"), debt_service=Decimal("5000.00")),
    )
    engine.vouch("A1", "B1")

    # Issue loan
    assessment = scorer.assess_credit("B1")
    loan = lending.borrow("B1", Decimal("5000.00"))

    # Save to disk
    store.save(engine, lending)
    assert store.store_file.is_file()

    # Create new fresh instances and load state back
    engine_loaded = TrustEngine()
    scorer_loaded = CreditScorer(engine_loaded)
    lending_loaded = LendingService(engine_loaded, scorer_loaded)

    store.load(engine_loaded, lending_loaded)

    # Assert graph restored
    assert "A1" in engine_loaded.users
    assert "B1" in engine_loaded.users
    assert engine_loaded.users["A1"].reputation == Decimal("15.0")
    assert engine_loaded.graph.has_edge("A1", "B1")
    assert engine_loaded.graph["A1"]["B1"]["weight"] == Decimal("15.0")

    # Assert loan restored
    assert loan.loan_id in lending_loaded.loans
    assert lending_loaded.loans[loan.loan_id].principal == Decimal("5000.00")
    assert lending_loaded.loans[loan.loan_id].status == "ACTIVE"


def test_session_management(tmp_path: Path):
    """Verify user session login and logout persistence."""
    store = StateStore(data_dir=tmp_path)
    assert store.get_current_user() is None

    store.set_current_user("ALICE")
    assert store.get_current_user() == "ALICE"

    store.set_current_user(None)
    assert store.get_current_user() is None


def test_peer_to_peer_lending():
    """Verify peer-to-peer lending functionality."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor", initial_reputation=Decimal("20.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("10.0"))
    engine.create_user(
        "BOB",
        "Bob",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(net_operating_income=Decimal("20000.00"), debt_service=Decimal("5000.00")),
    )

    engine.vouch("ANCHOR", "ALICE")
    engine.vouch("ALICE", "BOB")

    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)

    # Alice lends to Bob
    loan = lending.lend(
        lender_id="ALICE",
        borrower_id="BOB",
        amount=Decimal("10000.00"),
        tenure_months=6,
    )

    assert loan.lender_id == "ALICE"
    assert loan.borrower_id == "BOB"
    assert loan.principal == Decimal("10000.00")
    assert loan.status == "ACTIVE"


def test_cli_subparser_registration():
    """Verify that ledger subcommands are properly registered in the parser."""
    from veritrust.cli import build_parser

    parser = build_parser()
    args_hist = parser.parse_args(["history", "BOB"])
    assert args_hist.subcommand == "history"
    assert args_hist.user_id == "BOB"

    args_audit = parser.parse_args(["audit"])
    assert args_audit.subcommand == "audit"

    args_replay = parser.parse_args(["replay", "--restore"])
    assert args_replay.subcommand == "replay"
    assert args_replay.restore is True


