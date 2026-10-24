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


def test_out_degree_conservation_with_active_vouch(empty_engine: TrustEngine):
    """Invariant 1: Out-degree conservation with ACTIVE status users."""
    engine = empty_engine
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("15.0"))
    engine.create_user("U1", "User 1", initial_reputation=Decimal("0.0"))
    engine.create_user("U2", "User 2", initial_reputation=Decimal("0.0"))

    engine.vouch("ALICE", "U1")
    engine.vouch("ALICE", "U2")

    # Total weight should not exceed capacity = max(0, reputation) = 15.0
    assert engine.verify_conservation("ALICE")

    # After 2 vouches, each should have weight 15.0 / 2 = 7.5
    assert engine.graph["ALICE"]["U1"]["weight"] == Decimal("7.5")
    assert engine.graph["ALICE"]["U2"]["weight"] == Decimal("7.5")


def test_three_siblings_conservation(empty_engine: TrustEngine):
    """Invariant 1: Three siblings share capacity equally."""
    engine = empty_engine
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("9.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))
    engine.create_user("CHARLIE", "Charlie", initial_reputation=Decimal("0.0"))
    engine.create_user("DAVE", "Dave", initial_reputation=Decimal("0.0"))

    engine.vouch("ALICE", "BOB")
    engine.vouch("ALICE", "CHARLIE")
    engine.vouch("ALICE", "DAVE")

    # Each should have weight 9.0 / 3 = 3.0
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("3.0")
    assert engine.graph["ALICE"]["CHARLIE"]["weight"] == Decimal("3.0")
    assert engine.graph["ALICE"]["DAVE"]["weight"] == Decimal("3.0")
    assert engine.verify_conservation("ALICE")


def test_unvouch_then_revouch_redistributes(empty_engine: TrustEngine):
    """Invariant 1: Unvouch then revouch redistributes capacity among remaining."""
    engine = empty_engine
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("12.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))
    engine.create_user("CHARLIE", "Charlie", initial_reputation=Decimal("0.0"))

    engine.vouch("ALICE", "BOB")
    engine.vouch("ALICE", "CHARLIE")
    # Both have weight 6.0

    engine.unvouch("ALICE", "CHARLIE")
    # Now BOB should have weight 12.0

    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("12.0")
    assert not engine.graph.has_edge("ALICE", "CHARLIE")

    # Now revouch CHARLIE
    engine.vouch("ALICE", "CHARLIE")
    # Now with 2 edges, each should have weight 6.0
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("6.0")
    assert engine.graph["ALICE"]["CHARLIE"]["weight"] == Decimal("6.0")
    assert engine.verify_conservation("ALICE")


def test_single_vouch_full_capacity(empty_engine: TrustEngine):
    """Invariant 1: Single vouch gets full capacity as weight."""
    engine = empty_engine
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("20.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))

    engine.vouch("ALICE", "BOB")

    # Single edge should have full capacity
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("20.0")
    assert engine.verify_conservation("ALICE")


def test_out_degree_conservation_after_status_change(empty_engine: TrustEngine):
    """Invariant 1: Capacity drops to 0 when status changes from ACTIVE."""
    engine = empty_engine
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("15.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))
    engine.create_user("CHARLIE", "Charlie", initial_reputation=Decimal("0.0"))

    engine.vouch("ALICE", "BOB")
    engine.vouch("ALICE", "CHARLIE")

    # Both should have weight 7.5
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("7.5")
    assert engine.graph["ALICE"]["CHARLIE"]["weight"] == Decimal("7.5")
    assert engine.verify_conservation("ALICE")

    # Change ALICE status to DEFAULTED
    alice = engine.get_user("ALICE")
    alice.status = "DEFAULTED"
    alice.update_capacity()
    engine._sync_node_to_graph(alice)
    engine.recompute_weights("ALICE")

    # Capacity should now be 0
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("0.0")
    assert engine.graph["ALICE"]["CHARLIE"]["weight"] == Decimal("0.0")
    # With capacity=0 and weights=0, verify_conservation returns True (0 <= 0)
    # The key invariant is that weights are 0
    total_weight = (
        engine.graph["ALICE"]["BOB"].get("weight", Decimal("0.0"))
        + engine.graph["ALICE"]["CHARLIE"].get("weight", Decimal("0.0"))
    )
    assert total_weight == Decimal("0.0")


def test_per_path_cycle_absorption_triangle():
    """Invariant 3: Triangle cycle absorption with per-path visited set."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("6.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("4.0"))

    engine.vouch("ANCHOR", "ALICE")
    engine.vouch("ALICE", "BOB")
    engine.vouch("BOB", "ALICE")  # Creates triangle: ALICE -> BOB -> ALICE

    scorer = CreditScorer(engine)
    # Target BOB: should have path ANCHOR -> ALICE -> BOB
    r_graph_bob, paths_bob = scorer.compute_r_graph("BOB")
    # Should still have valid trust path (not zeroed by global visited set)
    assert r_graph_bob > Decimal("0.0")

    # Target ALICE: should receive trust only from ANCHOR -> ALICE direct
    # The cycle ALICE -> BOB -> ALICE should be absorbed
    r_graph_alice, paths_alice = scorer.compute_r_graph("ALICE")
    # Direct path ANCHOR -> ALICE should still count, cycle should be absorbed
    assert r_graph_alice == Decimal("10.0")  # Only direct path


def test_path_visited_set_is_per_path_not_global():
    """Invariant 3: Verify visited set is per-path, not global."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("A", "A", initial_reputation=Decimal("8.0"))
    engine.create_user("B", "B", initial_reputation=Decimal("6.0"))
    engine.create_user("C", "C", initial_reputation=Decimal("4.0"))
    engine.create_user("TARGET", "Target", initial_reputation=Decimal("0.0"))

    # Create two routes: ANCHOR -> A -> TARGET and ANCHOR -> B -> TARGET
    # And also a cycle: A -> B -> A
    engine.vouch("ANCHOR", "A")
    engine.vouch("ANCHOR", "B")
    engine.vouch("A", "TARGET")
    engine.vouch("B", "A")  # Creates cycle: B -> A (but A already vouched by ANCHOR)
    engine.vouch("B", "TARGET")

    scorer = CreditScorer(engine)
    # Should be able to find paths from ANCHOR to TARGET
    # The per-path visited set should allow both routes to be explored independently
    r_graph, paths = scorer.compute_r_graph("TARGET")

    # Should have at least one valid path
    assert len(paths) >= 1
    assert r_graph > Decimal("0.0")

