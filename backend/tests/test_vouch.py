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

