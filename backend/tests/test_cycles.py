"""Critical tests for Invariant 3: Cycle absorption and Sybil resistance.

Guarantees:
1. Visited-set is strictly PER-PATH, not global.
2. Loops terminate cleanly with 0 incremental trust without infinite recursion.
3. Collusion / Sybil rings cannot fabricate credibility.
"""

from decimal import Decimal
from veritrust.engine import TrustEngine
from veritrust.scoring import CreditScorer


def test_triangle_cycle_absorption():
    """Anchor -> A -> B -> Anchor.

    Evaluating target B:
    Valid path: Anchor -> A -> B.
    Cycle: Anchor -> A -> B -> Anchor -> ... must be absorbed on re-entry.
    No infinite loop.
    """
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("A", "Node A", initial_reputation=Decimal("6.0"))
    engine.create_user("B", "Node B", initial_reputation=Decimal("4.0"))

    engine.vouch("ANCHOR", "A")
    engine.vouch("A", "B")
    engine.vouch("B", "ANCHOR")  # Loop back to Anchor

    scorer = CreditScorer(engine)
    r_graph, paths = scorer.compute_r_graph("B")

    # Only one valid simple path should contribute
    assert len(paths) == 1
    assert paths[0].path == ["ANCHOR", "A", "B"]
    # Path trust: 10.0 * (6.0 * 0.5) = 30.0
    assert paths[0].path_trust == Decimal("30.0")
    assert r_graph == Decimal("30.0")


def test_per_path_visited_set_preserves_alternate_valid_routes():
    """CRITICAL: Visited set must be per-path, NOT shared globally.

    Topology:
      ANCHOR -> A -> B -> TARGET
      B -> A (cycle within branch 1)
      ANCHOR -> C -> TARGET (branch 2)

    If a buggy global visited set were used, exploring branch 1 might mark TARGET or A
    as visited and corrupt/cancel the completely valid alternate path via C.
    """
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("A", "Node A", initial_reputation=Decimal("6.0"))
    engine.create_user("B", "Node B", initial_reputation=Decimal("4.0"))
    engine.create_user("C", "Node C", initial_reputation=Decimal("8.0"))
    engine.create_user("TARGET", "Target", initial_reputation=Decimal("0.0"))

    # Branch 1
    engine.vouch("ANCHOR", "A")
    engine.vouch("A", "B")
    engine.vouch("B", "TARGET")
    engine.vouch("B", "A")  # Cycle loop back from B to A

    # Branch 2 (from same anchor to C)
    # Anchor now has 2 out edges: A and C -> W = 10 / 2 = 5.0 each
    engine.vouch("ANCHOR", "C")
    engine.vouch("C", "TARGET")

    scorer = CreditScorer(engine)
    r_graph, paths = scorer.compute_r_graph("TARGET")

    # Must find BOTH simple paths:
    # Path 1: ANCHOR -> A -> B -> TARGET
    # Path 2: ANCHOR -> C -> TARGET
    path_tuples = [tuple(p.path) for p in paths]
    assert ("ANCHOR", "A", "B", "TARGET") in path_tuples
    assert ("ANCHOR", "C", "TARGET") in path_tuples
    assert len(paths) == 2
    assert r_graph > Decimal("0.0")


def test_sybil_collusion_ring_zero_fabrication():
    """Sybil cluster without anchor backing cross-vouches to mutually inflate scores.

    Cluster: S1 -> S2 -> S3 -> S1 (all R=0, C=0).
    Expected: Zero capacity, zero weights, zero R_graph.
    """
    engine = TrustEngine()
    engine.create_user("S1", "Sybil 1", initial_reputation=Decimal("0.0"))
    engine.create_user("S2", "Sybil 2", initial_reputation=Decimal("0.0"))
    engine.create_user("S3", "Sybil 3", initial_reputation=Decimal("0.0"))

    # Because capacity is 0, vouching is rejected
    import pytest
    with pytest.raises(ValueError, match="has 0 capacity"):
        engine.vouch("S1", "S2")

    scorer = CreditScorer(engine)
    r_graph, paths = scorer.compute_r_graph("S1")
    assert r_graph == Decimal("0.0")
    assert len(paths) == 0

