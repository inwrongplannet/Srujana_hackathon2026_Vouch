"""Unit tests for vouching and out-degree capacity conservation."""

from decimal import Decimal
import pytest
from veritrust.engine import TrustEngine


def test_vouch_dilution_and_conservation():
    """Verify out-degree capacity conservation and atomic sibling re-weighting."""
    engine = TrustEngine()
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("9.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))
    engine.create_user("CHARLIE", "Charlie", initial_reputation=Decimal("0.0"))
    engine.create_user("DAVE", "Dave", initial_reputation=Decimal("0.0"))

    # 1. Alice vouches for Bob (1 outgoing edge)
    v1 = engine.vouch("ALICE", "BOB")
    assert v1.weight == Decimal("9.0")
    assert engine.verify_conservation("ALICE")

    # 2. Alice vouches for Charlie (2 outgoing edges) -> Dilutes Bob to 4.5
    v2 = engine.vouch("ALICE", "CHARLIE")
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("4.5")
    assert engine.graph["ALICE"]["CHARLIE"]["weight"] == Decimal("4.5")
    assert engine.verify_conservation("ALICE")

    # 3. Alice vouches for Dave (3 outgoing edges) -> Dilutes all to 3.0
    v3 = engine.vouch("ALICE", "DAVE")
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("3.0")
    assert engine.graph["ALICE"]["CHARLIE"]["weight"] == Decimal("3.0")
    assert engine.graph["ALICE"]["DAVE"]["weight"] == Decimal("3.0")
    assert engine.verify_conservation("ALICE")

    # 4. Unvouch Charlie -> Concentrates Bob and Dave back to 4.5
    engine.unvouch("ALICE", "CHARLIE")
    assert not engine.graph.has_edge("ALICE", "CHARLIE")
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("4.5")
    assert engine.graph["ALICE"]["DAVE"]["weight"] == Decimal("4.5")
    assert engine.verify_conservation("ALICE")


def test_vouch_guards():
    """Verify guards against self-vouching, zero capacity, and duplicate vouches."""
    engine = TrustEngine()
    engine.create_user("U1", "User 1", initial_reputation=Decimal("10.0"))
    engine.create_user("U2", "User 2", initial_reputation=Decimal("0.0"))

    # Self-vouching rejected
    with pytest.raises(ValueError, match="cannot vouch for themselves"):
        engine.vouch("U1", "U1")

    # Zero capacity cannot vouch
    with pytest.raises(ValueError, match="has 0 capacity"):
        engine.vouch("U2", "U1")

    # Duplicate vouch rejected
    engine.vouch("U1", "U2")
    with pytest.raises(ValueError, match="already exists"):
        engine.vouch("U1", "U2")


def test_bulk_dataset_ingestion():
    """Verify bulk dataset loading (Stage 2)."""
    engine = TrustEngine()
    users_data = [
        {"user_id": "BANK", "name": "Anchor Bank", "reputation": "50.0", "is_anchor": True},
        {"user_id": "ALICE", "name": "Alice", "reputation": "20.0"},
        {"user_id": "BOB", "name": "Bob", "reputation": "0.0"},
    ]
    vouches_data = [
        {"source": "BANK", "target": "ALICE"},
        {"source": "ALICE", "target": "BOB"},
    ]
    engine.load_dataset(users_data, vouches_data)

    assert len(engine.list_users()) == 3
    assert engine.graph.has_edge("BANK", "ALICE")
    assert engine.graph.has_edge("ALICE", "BOB")
    assert engine.graph["BANK"]["ALICE"]["weight"] == Decimal("50.0")
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("20.0")

