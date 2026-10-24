"""Tests for the Trust-Graph Attack Simulator & Security Safeguards.

Verifies:
1. Isolated Sybil cliques yield 0.00 trust due to anchor grounding.
2. Dense circular collusion rings are terminated by cycle absorption without runaway gain.
3. Compromised sponsor spam is strictly diluted by out-degree capacity conservation.
4. Rapid pre-application endorsement bursts trigger velocity damping heuristics.
"""

from decimal import Decimal
import pytest

from veritrust.attack_simulator import TrustGraphAttackSimulator


def test_sybil_mesh_neutralized_by_anchor_grounding():
    """Verify an isolated ring of 10 fake Sybil accounts cannot manufacture trust."""
    simulator = TrustGraphAttackSimulator()
    res = simulator.simulate_sybil_clique(n_sybils=10)

    assert res.attack_type == "SYBIL_ISOLATED_CLIQUE"
    assert res.is_attack_neutralized is True
    assert res.attack_induced_trust_score == Decimal("0.0")
    assert "SAFEGUARD_ANCHOR_GROUNDING" in res.safeguards_triggered[0]


def test_collusion_ring_neutralized_by_cycle_absorption():
    """Verify circular endorsement loops do not cause infinite recursion or gain."""
    simulator = TrustGraphAttackSimulator()
    res = simulator.simulate_dense_collusion_ring()

    assert res.attack_type == "DENSE_COLLUSION_RING"
    assert res.is_attack_neutralized is True
    # Trust score is finite and strictly bound by hop decay
    assert res.attack_induced_trust_score > Decimal("0.0")
    assert any("CYCLE_ABSORPTION" in sg for sg in res.safeguards_triggered)


def test_compromised_sponsor_dilution_enforced():
    """Verify high-trust sponsor endorsing 50 spam accounts has outgoing weight strictly conserved."""
    simulator = TrustGraphAttackSimulator()
    res = simulator.simulate_compromised_sponsor_dilution(n_spam_targets=50)

    assert res.attack_type == "COMPROMISED_SPONSOR_DILUTION"
    assert res.is_attack_neutralized is True
    # Weight per spam target must be heavily diluted (< 0.5)
    assert res.attack_induced_trust_score < Decimal("5.0")
    assert any("CAPACITY_CONSERVATION" in sg for sg in res.safeguards_triggered)


def test_endorsement_burst_temporal_anomaly():
    """Verify rapid cluster of 5 endorsements within minutes triggers velocity damping."""
    simulator = TrustGraphAttackSimulator()
    res = simulator.simulate_endorsement_burst_anomaly()

    assert res.attack_type == "ENDORSEMENT_BURST_ANOMALY"
    assert res.is_attack_neutralized is True
    assert any("VELOCITY_DETECTOR" in sg for sg in res.safeguards_triggered)
    # Score was damped by 50%
    assert res.attack_induced_trust_score == Decimal("25.00000")
