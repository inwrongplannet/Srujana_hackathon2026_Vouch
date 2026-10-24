"""Tests for the VeriTrust Append-Only Reputation & Evidence Ledger.

Verifies:
- Append-only event sequencing and history queries
- Cryptographic hash chaining (Genesis to Head)
- Tamper detection on modified payload or broken hash chains
- Idempotency guarantees (duplicate event_id rejection)
- State reconstruction via deterministic replay
- Evidence audit trail persistence
"""

from decimal import Decimal
from pathlib import Path
import sqlite3
import pytest

from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.ledger import DuplicateEventError, LedgerIntegrityError, ReputationLedger, GENESIS_HASH
from veritrust.models import Evidence, FinancialFeatures
from veritrust.scoring import CreditScorer


@pytest.fixture
def temp_ledger(tmp_path: Path) -> ReputationLedger:
    """Fixture providing an isolated SQLite + JSONL ledger in a temporary folder."""
    db_path = tmp_path / "test_ledger.db"
    jsonl_path = tmp_path / "test_events.jsonl"
    return ReputationLedger(db_path=db_path, jsonl_path=jsonl_path)


def test_ledger_append_and_query_history(temp_ledger: ReputationLedger) -> None:
    """Test appending events and querying chronological history by subject."""
    assert temp_ledger.count() == 0

    evt1 = temp_ledger.append_event(
        event_type="USER_REGISTERED",
        actor_id="SYSTEM_ANCHOR",
        subject_id="U001",
        delta_reputation=Decimal("10.0"),
        payload={"name": "Alice"},
    )
    assert evt1.sequence == 1
    assert evt1.prev_hash == GENESIS_HASH
    assert len(evt1.event_hash) == 64
    assert temp_ledger.count() == 1

    evt2 = temp_ledger.append_event(
        event_type="USER_REGISTERED",
        actor_id="U002",
        subject_id="U002",
        delta_reputation=Decimal("0.0"),
        payload={"name": "Bob"},
    )
    assert evt2.sequence == 2
    assert evt2.prev_hash == evt1.event_hash

    # Query history for U001
    history_u1 = temp_ledger.get_history("U001")
    assert len(history_u1) == 1
    assert history_u1[0].event_id == evt1.event_id
    assert history_u1[0].delta_reputation == Decimal("10.0")

    # Latest event is evt2
    latest = temp_ledger.get_latest_event()
    assert latest is not None
    assert latest.event_id == evt2.event_id
    assert latest.sequence == 2


def test_cryptographic_hash_chain_verification(temp_ledger: ReputationLedger) -> None:
    """Test complete cryptographic hash chain validation from genesis to head."""
    prev_hash = GENESIS_HASH
    for i in range(1, 11):
        evt = temp_ledger.append_event(
            event_type="REPUTATION_MINTED",
            actor_id="SYSTEM",
            subject_id="U001",
            delta_reputation=Decimal(f"{i}.0"),
            payload={"iteration": i},
        )
        assert evt.prev_hash == prev_hash
        prev_hash = evt.event_hash

    assert temp_ledger.count() == 10
    is_valid, err = temp_ledger.verify_integrity()
    assert is_valid is True
    assert err is None


def test_tamper_detection_in_payload(temp_ledger: ReputationLedger) -> None:
    """Modifying event payload in SQLite directly must trigger integrity failure."""
    for i in range(1, 4):
        temp_ledger.append_event(
            event_type="REPUTATION_MINTED",
            actor_id="SYSTEM",
            subject_id="U001",
            delta_reputation=Decimal(f"{i}.0"),
        )

    # Validate before tampering
    assert temp_ledger.verify_integrity()[0] is True

    # Malicious actor secretly edits delta_reputation in SQLite row 2
    with sqlite3.connect(str(temp_ledger.db_path)) as conn:
        conn.execute("UPDATE ledger_events SET delta_reputation = '999.0' WHERE sequence = 2;")

    is_valid, err = temp_ledger.verify_integrity()
    assert is_valid is False
    assert err is not None
    assert "Tamper detected at sequence 2" in err


def test_tamper_detection_broken_chain(temp_ledger: ReputationLedger) -> None:
    """Altering prev_hash in an event row must trigger chain break detection."""
    for i in range(1, 4):
        temp_ledger.append_event(
            event_type="REPUTATION_MINTED",
            actor_id="SYSTEM",
            subject_id="U001",
            delta_reputation=Decimal(f"{i}.0"),
        )

    # Malicious actor attempts to forge previous hash link
    with sqlite3.connect(str(temp_ledger.db_path)) as conn:
        conn.execute("UPDATE ledger_events SET prev_hash = '0000deadbeef' WHERE sequence = 3;")

    is_valid, err = temp_ledger.verify_integrity()
    assert is_valid is False
    assert err is not None
    assert "Chain break at sequence 3" in err


def test_ledger_idempotency_enforcement(temp_ledger: ReputationLedger) -> None:
    """Processing duplicate event_id must raise DuplicateEventError without altering chain."""
    temp_ledger.append_event(
        event_type="USER_REGISTERED",
        actor_id="U001",
        subject_id="U001",
        event_id="EVT_IDEMPOTENT_100",
    )
    assert temp_ledger.count() == 1

    # Attempt second append with identical event_id
    with pytest.raises(DuplicateEventError) as exc_info:
        temp_ledger.append_event(
            event_type="USER_REGISTERED",
            actor_id="U001",
            subject_id="U001",
            event_id="EVT_IDEMPOTENT_100",
        )

    assert "Idempotency violation" in str(exc_info.value)
    assert temp_ledger.count() == 1
    assert temp_ledger.verify_integrity()[0] is True


def test_repayment_idempotency_prevents_duplicate_reputation(temp_ledger: ReputationLedger) -> None:
    """Duplicate repayment processing must be rejected and not award reputation twice."""
    engine = TrustEngine(ledger=temp_ledger)
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)

    engine.create_user("ANCHOR", "Bank Anchor", initial_reputation=Decimal("20.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("10.0"))
    engine.create_user(
        "BOB",
        "Bob",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("50000.00"),
            monthly_debt=Decimal("5000.00"),
            net_operating_income=Decimal("35000.00"),
            debt_service=Decimal("5000.00"),
        ),
    )
    engine.vouch("ANCHOR", "ALICE")
    engine.vouch("ALICE", "BOB")

    loan = lending.borrow("BOB", Decimal("5000.00"))
    assert loan.status == "ACTIVE"
    bob = engine.get_user("BOB")
    assert bob is not None
    assert bob.reputation == Decimal("0.0")

    # First partial repayment with unique transaction event ID
    payment_event_id = "PAY_BANK_TX_998877"
    lending.repay(loan.loan_id, Decimal("2000.00"), event_id=payment_event_id)
    assert loan.status == "ACTIVE"
    assert loan.outstanding_balance == Decimal("3000.00")

    # Duplicate call with identical event ID
    with pytest.raises(DuplicateEventError):
        lending.repay(loan.loan_id, Decimal("2000.00"), event_id=payment_event_id)

    # Outstanding balance must remain strictly 3000.00 (not decremented twice)
    assert loan.outstanding_balance == Decimal("3000.00")


def test_deterministic_replay_state_reconstruction(temp_ledger: ReputationLedger) -> None:
    """Full lifecycle must reconstruct identical engine and lending state on replay."""
    engine = TrustEngine(ledger=temp_ledger)
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)

    # 1. Setup participants
    anchor = engine.create_user("BANK", "Seed Bank", initial_reputation=Decimal("50.0"), is_anchor=True)
    alice = engine.create_user("ALICE", "Alice", initial_reputation=Decimal("20.0"))
    bob = engine.create_user(
        "BOB",
        "Bob",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("60000.00"),
            monthly_debt=Decimal("10000.00"),
            net_operating_income=Decimal("40000.00"),
            debt_service=Decimal("8000.00"),
            completeness=Decimal("0.95"),
        ),
    )
    mallory = engine.create_user("MALLORY", "Mallory", initial_reputation=Decimal("5.0"))

    # 2. Vouches
    engine.vouch("BANK", "ALICE")
    engine.vouch("ALICE", "BOB")
    engine.vouch("ALICE", "MALLORY")

    # 3. Bob takes loan and successfully repays
    loan_bob = lending.borrow("BOB", Decimal("5000.00"))
    lending.repay(loan_bob.loan_id, Decimal("5000.00"))
    assert loan_bob.status == "REPAID"

    # 4. Mallory takes loan and defaults -> triggers 4-level slashing cascade
    loan_mal = lending.borrow("MALLORY", Decimal("2000.00"))
    lending.default_loan(loan_mal.loan_id)
    assert loan_mal.status == "DEFAULTED"

    # Capture ground truth state before replay
    ground_truth_reps = {u.user_id: u.reputation for u in engine.list_users()}
    ground_truth_statuses = {u.user_id: u.status for u in engine.list_users()}
    ground_truth_capacities = {u.user_id: u.capacity for u in engine.list_users()}
    ground_truth_edges = {
        (u, v): d.get("weight") for u, v, d in engine.graph.edges(data=True)
    }

    # 5. Replay from raw ledger events
    replayed_engine, replayed_lending = temp_ledger.reconstruct_state()  # type: ignore

    # Verify users
    for user_id, expected_rep in ground_truth_reps.items():
        replayed_u = replayed_engine.get_user(user_id)
        assert replayed_u is not None, f"User {user_id} missing in replayed state"
        assert replayed_u.reputation == expected_rep, f"Reputation mismatch for {user_id}"
        assert replayed_u.status == ground_truth_statuses[user_id]
        assert replayed_u.capacity == ground_truth_capacities[user_id]

    # Verify graph edges and weights
    for (u, v), expected_weight in ground_truth_edges.items():
        assert replayed_engine.graph.has_edge(u, v), f"Edge ({u}, {v}) missing in replayed graph"
        actual_weight = replayed_engine.graph[u][v].get("weight")
        assert actual_weight == expected_weight, f"Edge weight mismatch for ({u}, {v})"

    # Verify loans
    for loan_id, original_loan in lending.loans.items():
        assert loan_id in replayed_lending.loans
        assert replayed_lending.loans[loan_id].status == original_loan.status
        assert replayed_lending.loans[loan_id].outstanding_balance == original_loan.outstanding_balance


def test_replay_fails_on_tampered_ledger(temp_ledger: ReputationLedger) -> None:
    """Replay must refuse to execute and raise LedgerIntegrityError if ledger has been tampered with."""
    temp_ledger.append_event(
        event_type="USER_REGISTERED",
        actor_id="SYS",
        subject_id="U001",
        delta_reputation=Decimal("10.0"),
    )
    temp_ledger.append_event(
        event_type="REPUTATION_MINTED",
        actor_id="SYS",
        subject_id="U001",
        delta_reputation=Decimal("5.0"),
    )

    # Maliciously alter sequence 1
    with sqlite3.connect(str(temp_ledger.db_path)) as conn:
        conn.execute("UPDATE ledger_events SET delta_reputation = '99.0' WHERE sequence = 1;")

    with pytest.raises(LedgerIntegrityError) as exc_info:
        temp_ledger.reconstruct_state()

    assert "Cannot replay corrupted ledger" in str(exc_info.value)


def test_evidence_audit_attachment(temp_ledger: ReputationLedger) -> None:
    """Verifiable evidence must be securely anchored and attached to ledger events."""
    evidence = Evidence(
        evidence_id="EVID_DIGILOCKER_001",
        evidence_type="BANK_STATEMENT",
        uri_or_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        description="DigiLocker verified income tax return & 12-month statement",
        recorded_by="DIGILOCKER_GATEWAY",
    )

    evt = temp_ledger.append_event(
        event_type="USER_REGISTERED",
        actor_id="U001",
        subject_id="U001",
        delta_reputation=Decimal("10.0"),
        evidence=evidence,
    )

    assert evt.evidence is not None
    assert evt.evidence.evidence_id == "EVID_DIGILOCKER_001"
    assert evt.evidence.evidence_type == "BANK_STATEMENT"
    assert evt.evidence.recorded_by == "DIGILOCKER_GATEWAY"

    # Query back from SQLite
    history = temp_ledger.get_history("U001")
    assert len(history) == 1
    assert history[0].evidence is not None
    assert history[0].evidence.evidence_id == "EVID_DIGILOCKER_001"
    assert history[0].evidence.uri_or_hash.startswith("sha256:")
