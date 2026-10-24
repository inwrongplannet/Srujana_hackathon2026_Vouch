"""Critical tests for Web-of-Trust graph engine and out-degree conservation.

Enforces Invariant 1 (Out-degree conservation) and Invariant 2 (Hop attenuation).
"""

from decimal import Decimal
import pytest
from veritrust.engine import TrustEngine
from veritrust.scoring import CreditScorer


def test_out_degree_conservation_law(empty_engine: TrustEngine):
    """Invariant 1: Out-degree conservation.

    Sum of outgoing weights must always be <= C_u = max(0, R_u).
    """
    engine = empty_engine
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("12.0"))
    engine.create_user("U1", "User 1", initial_reputation=Decimal("0.0"))
    engine.create_user("U2", "User 2", initial_reputation=Decimal("0.0"))
    engine.create_user("U3", "User 3", initial_reputation=Decimal("0.0"))
    engine.create_user("U4", "User 4", initial_reputation=Decimal("0.0"))

    # Add 4 outgoing vouches one by one
    targets = ["U1", "U2", "U3", "U4"]
    for i, target in enumerate(targets, start=1):
        engine.vouch("ALICE", target)
        expected_weight = Decimal("12.0") / Decimal(i)
        for t in targets[:i]:
            assert engine.graph["ALICE"][t]["weight"] == expected_weight
        assert engine.verify_conservation("ALICE")


def test_zero_reputation_node_cannot_vouch(empty_engine: TrustEngine):
    """Nodes with R <= 0 have C = 0 and cannot vouch for others."""
    engine = empty_engine
    engine.create_user("ZERO_NODE", "Zero Node", initial_reputation=Decimal("0.0"))
    engine.create_user("TARGET", "Target", initial_reputation=Decimal("0.0"))

    with pytest.raises(ValueError, match="has 0 capacity"):
        engine.vouch("ZERO_NODE", "TARGET")


def test_linear_chain_numerical_decay(linear_chain_engine: TrustEngine):
    """Invariant 2: Hop attenuation X = 0.5.

    Chain: ANCHOR (R=10) -> ALICE (R=6) -> BOB
    First hop (ANCHOR -> ALICE): weight = 10.0 (no decay, hop 0)
    Second hop (ALICE -> BOB): weight = 6.0, decayed by 0.5 -> 3.0
    Trust(P) = 10.0 * 3.0 = 30.0
    """
    engine = linear_chain_engine
    scorer = CreditScorer(engine)
    r_graph, paths = scorer.compute_r_graph("BOB")

    assert len(paths) == 1
    assert paths[0].path == ["ANCHOR", "ALICE", "BOB"]
    assert paths[0].path_trust == Decimal("30.0")
    assert r_graph == Decimal("30.0")


def test_multi_anchor_additive_aggregation(multi_anchor_diamond_engine: TrustEngine):
    """Trust contributions from distinct institutional anchors aggregate additively.

    Path 1: ANCHOR1(10) -> A(4) -> TARGET:  10.0 * (4.0 * 0.5) = 20.0
    Path 2: ANCHOR2(8)  -> B(6) -> TARGET:   8.0 * (6.0 * 0.5) = 24.0
    Total R_graph(TARGET) = 20.0 + 24.0 = 44.0
    """
    engine = multi_anchor_diamond_engine
    scorer = CreditScorer(engine)
    r_graph, paths = scorer.compute_r_graph("TARGET")

    assert len(paths) == 2
    path_trusts = {tuple(p.path): p.path_trust for p in paths}
    assert path_trusts[("ANCHOR1", "A", "TARGET")] == Decimal("20.0")
    assert path_trusts[("ANCHOR2", "B", "TARGET")] == Decimal("24.0")
    assert r_graph == Decimal("44.0")


def test_disconnected_node_receives_zero_trust(empty_engine: TrustEngine):
    """A node without any paths from anchors receives R_graph = 0."""
    engine = empty_engine
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("ISOLATED", "Isolated Node", initial_reputation=Decimal("0.0"))

    scorer = CreditScorer(engine)
    r_graph, paths = scorer.compute_r_graph("ISOLATED")

    assert r_graph == Decimal("0.0")
    assert len(paths) == 0


def test_unvouch_restores_capacity(empty_engine: TrustEngine):
    """Removing an edge redistributes capacity among remaining edges."""
    engine = empty_engine
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("10.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))
    engine.create_user("CHARLIE", "Charlie", initial_reputation=Decimal("0.0"))

    engine.vouch("ALICE", "BOB")
    engine.vouch("ALICE", "CHARLIE")
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("5.0")
    assert engine.graph["ALICE"]["CHARLIE"]["weight"] == Decimal("5.0")

    engine.unvouch("ALICE", "CHARLIE")
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("10.0")
    assert not engine.graph.has_edge("ALICE", "CHARLIE")

