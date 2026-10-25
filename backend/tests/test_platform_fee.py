"""Unit tests for platform transaction fee cut, treasury accumulation, and audit trail.

Verifies:
1. Exact Decimal calculations with known answers (no float drift).
2. Loan disbursement transaction fee recording and treasury accumulation.
3. Loan repayment transaction fee recording and treasury accumulation.
4. Append-only ledger cryptographic replay preserves platform fees.
5. Store persistence (save/load) preserves platform treasury balances.
6. REST API routes GET /api/v1/transactions and GET /api/v1/platform/treasury.
"""

from decimal import Decimal
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from veritrust.api.app import app
from veritrust.engine import TrustEngine
from veritrust.ledger import ReputationLedger
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures, PlatformTreasury, Transaction
from veritrust.scoring import CreditScorer
from veritrust.store import StateStore


def _setup_service(fee_rate: Decimal = Decimal("0.01")) -> tuple[TrustEngine, LendingService]:
    """Helper to set up engine and lending service with custom platform fee rate."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("50.0"), is_anchor=True)
    engine.create_user("SPONSOR", "Direct Sponsor", initial_reputation=Decimal("20.0"))
    engine.create_user(
        "BORROWER",
        "Borrower",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("50000.00"),
            monthly_debt=Decimal("5000.00"),
            net_operating_income=Decimal("35000.00"),
            debt_service=Decimal("5000.00"),
            completeness=Decimal("1.0"),
        ),
    )
    engine.vouch("ANCHOR", "SPONSOR")
    engine.vouch("SPONSOR", "BORROWER")
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer, platform_fee_rate=fee_rate)
    return engine, lending


def test_fee_calculation_known_answers():
    """Verify fee calculation matches known mathematical answers using Decimal."""
    _, lending = _setup_service(fee_rate=Decimal("0.01"))

    # 1.0% on INR 10,000.00 = INR 100.00
    assert lending.compute_platform_fee(Decimal("10000.00")) == Decimal("100.00")

    # 1.0% on INR 50,000.00 = INR 500.00
    assert lending.compute_platform_fee(Decimal("50000.00")) == Decimal("500.00")

    # 1.0% on INR 123.45 = INR 1.23 (1.2345 -> 1.23)
    assert lending.compute_platform_fee(Decimal("123.45")) == Decimal("1.23")

    # 1.0% on INR 123.50 = INR 1.24 (1.2350 -> 1.24 with ROUND_HALF_UP)
    assert lending.compute_platform_fee(Decimal("123.50")) == Decimal("1.24")

    # Zero fee if rate is zero
    lending.platform_fee_rate = Decimal("0.00")
    assert lending.compute_platform_fee(Decimal("10000.00")) == Decimal("0.00")


def test_disbursement_fee_and_treasury_accumulation():
    """Verify that loan disbursement creates a transaction fee and increments treasury."""
    _, lending = _setup_service(fee_rate=Decimal("0.01"))

    loan = lending.borrow("BORROWER", Decimal("20000.00"))
    assert loan.principal == Decimal("20000.00")
    assert loan.outstanding_balance == Decimal("20000.00")

    # Verify transaction record
    assert len(lending.transactions) == 1
    tx = lending.transactions[0]
    assert tx.tx_type == "DISBURSEMENT"
    assert tx.amount == Decimal("20000.00")
    assert tx.fee == Decimal("200.00")  # 1% of 20,000
    assert tx.net_amount == Decimal("20000.00")
    assert tx.currency == "INR"

    # Verify cumulative treasury
    assert lending.total_platform_fees == Decimal("200.00")
    treasury = lending.get_treasury_summary()
    assert treasury.total_fees_collected == Decimal("200.00")
    assert treasury.fee_rate == Decimal("0.01")
    assert treasury.transaction_count == 1
    assert treasury.currency == "INR"


def test_repayment_fee_and_cumulative_treasury():
    """Verify that repayment operations charge platform cut and accumulate revenue."""
    _, lending = _setup_service(fee_rate=Decimal("0.01"))

    loan = lending.borrow("BORROWER", Decimal("10000.00"))
    assert lending.total_platform_fees == Decimal("100.00")

    # Partial repayment of INR 4,000
    lending.repay(loan.loan_id, Decimal("4000.00"))
    assert loan.outstanding_balance == Decimal("6000.00")
    assert lending.total_platform_fees == Decimal("140.00")  # 100 + 40

    repay_tx = lending.transactions[-1]
    assert repay_tx.tx_type == "REPAYMENT"
    assert repay_tx.amount == Decimal("4000.00")
    assert repay_tx.fee == Decimal("40.00")
    assert repay_tx.net_amount == Decimal("4000.00")

    # Final settlement of remaining INR 6,000
    lending.repay(loan.loan_id, Decimal("6000.00"))
    assert loan.status == "REPAID"
    assert loan.outstanding_balance == Decimal("0.00")
    assert lending.total_platform_fees == Decimal("200.00")  # 140 + 60

    final_tx = lending.transactions[-1]
    assert final_tx.fee == Decimal("60.00")


def test_deterministic_replay_preserves_platform_fees(tmp_path: Path):
    """Verify that ledger replay reconstructs identical platform fee cuts and treasury totals."""
    ledger_db = tmp_path / "ledger.db"
    events_jsonl = tmp_path / "events.jsonl"
    ledger = ReputationLedger(db_path=ledger_db, jsonl_path=events_jsonl)

    engine = TrustEngine(ledger=ledger)
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("50.0"), is_anchor=True)
    engine.create_user("SPONSOR", "Direct Sponsor", initial_reputation=Decimal("20.0"))
    engine.create_user(
        "BORROWER",
        "Borrower",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("50000.00"),
            monthly_debt=Decimal("5000.00"),
            net_operating_income=Decimal("35000.00"),
            debt_service=Decimal("5000.00"),
            completeness=Decimal("1.0"),
        ),
    )
    engine.vouch("ANCHOR", "SPONSOR")
    engine.vouch("SPONSOR", "BORROWER")
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer, platform_fee_rate=Decimal("0.01"))

    loan = lending.borrow("BORROWER", Decimal("10000.00"))
    lending.repay(loan.loan_id, Decimal("5000.00"))
    assert lending.total_platform_fees == Decimal("150.00")

    # Reconstruct state from immutable events
    _, replayed_lending = ledger.reconstruct_state()  # type: ignore
    assert replayed_lending.total_platform_fees == Decimal("150.00")
    assert len(replayed_lending.transactions) == 2
    assert replayed_lending.transactions[0].fee == Decimal("100.00")
    assert replayed_lending.transactions[1].fee == Decimal("50.00")


def test_store_persistence_preserves_treasury(tmp_path: Path):
    """Verify that saving and loading state from store.json preserves total platform fees."""
    engine, lending = _setup_service(fee_rate=Decimal("0.01"))
    loan = lending.borrow("BORROWER", Decimal("10000.00"))
    lending.repay(loan.loan_id, Decimal("5000.00"))
    assert lending.total_platform_fees == Decimal("150.00")

    store = StateStore(data_dir=tmp_path)
    store.save(engine, lending)

    # Load into fresh instances
    fresh_engine = TrustEngine()
    fresh_scorer = CreditScorer(fresh_engine)
    fresh_lending = LendingService(fresh_engine, fresh_scorer)
    loaded = store.load(fresh_engine, fresh_lending)
    assert loaded is True
    assert fresh_lending.total_platform_fees == Decimal("150.00")
    assert len(fresh_lending.transactions) == 2
    assert fresh_lending.transactions[0].fee == Decimal("100.00")
    assert fresh_lending.transactions[1].fee == Decimal("50.00")


def test_api_platform_endpoints():
    """Verify GET /api/v1/platform/treasury and GET /api/v1/transactions REST endpoints."""
    client = TestClient(app)

    # 1. Treasury status
    res_treasury = client.get("/api/v1/platform/treasury")
    assert res_treasury.status_code == 200
    data_treasury = res_treasury.json()
    assert "total_fees_collected" in data_treasury
    assert "fee_rate" in data_treasury
    assert data_treasury["currency"] == "INR"
    assert data_treasury["treasury_id"] == "PLATFORM_TREASURY"

    # 2. Transactions list
    res_txs = client.get("/api/v1/transactions")
    assert res_txs.status_code == 200
    data_txs = res_txs.json()
    assert isinstance(data_txs, list)
    for tx in data_txs:
        assert "tx_id" in tx
        assert "amount" in tx
        assert "fee" in tx
        assert "net_amount" in tx
        assert tx["currency"] == "INR"

