"""Tests for the Master Mathematical Framework and Design Decisions (2026).

Verifies:
1. Equal outgoing endorsement allocation: sum(w_uv) = R_u.
2. Chronological rank-based diminishing returns: alpha_uv = 1 / 2^(r_uv - 1) and immutability.
3. Graph propagation known-answer test from Section 6:
   T(A -> B -> D) = 12 * (1/2) * (1/2) * 1 * 1 * 0.7 = 2.1.
4. Same-source consolidation using min-path: p_u(s) = min(T(P)).
5. Distinct-source aggregation: G(u) = sum(p_u(s)) and scoring cap G_score(u) = min(G, G_max).
6. Reputation minting with diminishing returns: M_k = M_0 * exp(-lambda * (k - 1)).
7. Default exposure, severity, and atomic snapshot penalties for borrower and contributing sources.
"""

from decimal import Decimal
import pytest

from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer


def test_equal_allocation_conservation_law():
    """Section 4: A user divides their owned reputation equally across active outgoing endorsements.

    sum_{v in N_u} w_uv = R_u.
    """
    engine = TrustEngine()
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("12.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))
    engine.create_user("CHARLIE", "Charlie", initial_reputation=Decimal("0.0"))
    engine.create_user("DAVID", "David", initial_reputation=Decimal("0.0"))

    # 1 outgoing: receives 12.0
    v1 = engine.vouch("ALICE", "BOB")
    assert v1.weight == Decimal("12.0")
    assert engine.verify_conservation("ALICE")

    # 2 outgoing: receives 6.0 each
    v2 = engine.vouch("ALICE", "CHARLIE")
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("6.0")
    assert v2.weight == Decimal("6.0")
    assert engine.verify_conservation("ALICE")

    # 3 outgoing: receives 4.0 each
    v3 = engine.vouch("ALICE", "DAVID")
    assert engine.graph["ALICE"]["BOB"]["weight"] == Decimal("4.0")
    assert engine.graph["ALICE"]["CHARLIE"]["weight"] == Decimal("4.0")
    assert v3.weight == Decimal("4.0")
    assert engine.verify_conservation("ALICE")


def test_chronological_rank_diminishing_weights():
    """Section 5: Chronological rank-based diminishing returns alpha_uv = 1 / 2^(r_uv - 1).

    First endorsement received gets weight 1, second 1/2, third 1/4, fourth 1/8.
    Rank is immutable.
    """
    engine = TrustEngine()
    engine.create_user("A", "User A", initial_reputation=Decimal("10.0"))
    engine.create_user("B", "User B", initial_reputation=Decimal("10.0"))
    engine.create_user("C", "User C", initial_reputation=Decimal("10.0"))
    engine.create_user("D", "User D", initial_reputation=Decimal("10.0"))
    engine.create_user("RECIPIENT", "Recipient", initial_reputation=Decimal("0.0"))

    # Endorsement 1 from A: rank 1, alpha = 1.0
    v1 = engine.vouch("A", "RECIPIENT")
    assert v1.rank == 1
    assert v1.alpha == Decimal("1.0")

    # Endorsement 2 from B: rank 2, alpha = 0.5
    v2 = engine.vouch("B", "RECIPIENT")
    assert v2.rank == 2
    assert v2.alpha == Decimal("0.5")

    # Endorsement 3 from C: rank 3, alpha = 0.25
    v3 = engine.vouch("C", "RECIPIENT")
    assert v3.rank == 3
    assert v3.alpha == Decimal("0.25")

    # Endorsement 4 from D: rank 4, alpha = 0.125
    v4 = engine.vouch("D", "RECIPIENT")
    assert v4.rank == 4
    assert v4.alpha == Decimal("0.125")

    # Immutability: revoking v1 does not change rank of v2 or v3
    engine.unvouch("A", "RECIPIENT")
    assert v2.rank == 2
    assert v3.rank == 3


def test_graph_propagation_known_answer_section_6():
    """Section 6 worked example from Master Framework:

    R_A = 12, d_A = 2, d_B = 2, both edges rank 1, delta = 0.7.
    Path A -> B -> D:
    T(A -> B -> D) = 12 * (1/2) * (1/2) * 1 * 1 * 0.7 = 2.1.
    If second edge had rank 2 (alpha = 1/2), T = 1.05.
    """
    engine = TrustEngine()
    # A has reputation 12, out-degree 2 (vouches for B and DUMMY_A)
    engine.create_user("A", "Node A", initial_reputation=Decimal("12.0"))
    engine.create_user("DUMMY_A", "Dummy A", initial_reputation=Decimal("0.0"))
    engine.vouch("A", "DUMMY_A")  # out-edge 1 from A

    # B has reputation 10, out-degree 2 (vouches for D and DUMMY_B)
    engine.create_user("B", "Node B", initial_reputation=Decimal("10.0"))
    engine.create_user("DUMMY_B", "Dummy B", initial_reputation=Decimal("0.0"))
    engine.vouch("B", "DUMMY_B")  # out-edge 1 from B

    # Target D
    engine.create_user("D", "Node D", initial_reputation=Decimal("0.0"))

    # Add edges in path: A -> B, and B -> D (both rank 1)
    engine.vouch("A", "B")  # out-edge 2 from A -> d_A = 2
    engine.vouch("B", "D")  # out-edge 2 from B -> d_B = 2

    scorer = CreditScorer(engine)
    report = scorer.compute_propagated_credibility("D", delta=Decimal("0.7"), sources_only=["A"])

    # Path A -> B -> D should transmit exactly 2.1
    assert len(report.paths) == 1
    path_record = report.paths[0]
    assert path_record.path == ["A", "B", "D"]
    assert path_record.path_trust == Decimal("2.1000")
    assert report.source_contributions["A"] == Decimal("2.1000")
    assert report.g_raw == Decimal("2.1000")


def test_same_source_min_path_consolidation_section_8():
    """Section 8: Multiple paths from the same source take the minimum contribution.

    p_u(s) = min_{P in P(s, u)} T(P).
    If source A contributes 2.1 through one path and 1.8 through another:
    p_D(A) = min(2.1, 1.8) = 1.8 (not 3.9).
    """
    engine = TrustEngine()
    engine.create_user("A", "Source A", initial_reputation=Decimal("10.0"))
    engine.create_user("B1", "Intermediary 1", initial_reputation=Decimal("5.0"))
    engine.create_user("B2", "Intermediary 2", initial_reputation=Decimal("5.0"))
    engine.create_user("D", "Target D", initial_reputation=Decimal("0.0"))

    # A vouches for B1 and B2 -> d_A = 2
    engine.vouch("A", "B1")
    engine.vouch("A", "B2")

    # B1 vouches for D (rank 1 at D)
    engine.vouch("B1", "D")

    # B2 vouches for D (rank 2 at D -> alpha = 0.5)
    engine.vouch("B2", "D")

    scorer = CreditScorer(engine)
    delta = Decimal("0.8")
    report = scorer.compute_propagated_credibility("D", delta=delta, sources_only=["A"])

    # Two paths from A:
    # Path 1 (A -> B1 -> D): 10 * (1/2) * (1/1) * 1.0 * 1.0 * 0.8 = 4.0
    # Path 2 (A -> B2 -> D): 10 * (1/2) * (1/1) * 1.0 * 0.5 * 0.8 = 2.0
    assert len(report.paths) == 2
    # p_D(A) = min(4.0, 2.0) = 2.0
    assert report.source_contributions["A"] == Decimal("2.0000")
    assert report.g_raw == Decimal("2.0000")


def test_distinct_source_aggregation_and_cap_section_9():
    """Section 9: G(u) = sum_{s != u} p_u(s), G_score(u) = min(G(u), G_max)."""
    engine = TrustEngine()
    engine.create_user("SOURCE_1", "Source 1", initial_reputation=Decimal("10.0"))
    engine.create_user("SOURCE_2", "Source 2", initial_reputation=Decimal("8.0"))
    engine.create_user("TARGET", "Target", initial_reputation=Decimal("0.0"))

    engine.vouch("SOURCE_1", "TARGET")  # rank 1: alpha = 1.0 -> 10.0 * 1.0 * 1.0 = 10.0
    engine.vouch("SOURCE_2", "TARGET")  # rank 2: alpha = 0.5 -> 8.0 * 1.0 * 0.5 = 4.0

    scorer = CreditScorer(engine)
    report = scorer.compute_propagated_credibility("TARGET", g_max=Decimal("12.0"))

    # G_raw = 10.0 + 4.0 = 14.0
    assert report.g_raw == Decimal("14.0000")
    # Capped at G_max = 12.0
    assert report.g_score == Decimal("12.0000")


def test_diminishing_reputation_minting_section_2():
    """Section 2 & 3: Diminishing returns on repeated transactions between a pair.

    M_k = M_0 * exp(-lambda * (k - 1)).
    With lambda = ln(2) = 0.693147, rewards halve: M_0, M_0/2, M_0/4, M_0/8...
    """
    engine = TrustEngine()
    engine.create_user("ALICE", "Alice", initial_reputation=Decimal("0.0"))
    engine.create_user("BOB", "Bob", initial_reputation=Decimal("0.0"))

    m0 = Decimal("2.0")
    lam = Decimal("0.693147")  # ln(2)

    # Transaction 1: k=1 -> M_1 = 2.0 * 1 = 2.0
    m1 = engine.mint_transaction_reputation("ALICE", "BOB", m0=m0, mint_lambda=lam)
    assert m1 == Decimal("2.0000")
    assert engine.get_user("ALICE").reputation == Decimal("2.0000")
    assert engine.get_user("BOB").reputation == Decimal("2.0000")

    # Transaction 2: k=2 -> M_2 = 2.0 / 2 = 1.0
    m2 = engine.mint_transaction_reputation("ALICE", "BOB", m0=m0, mint_lambda=lam)
    assert m2 == Decimal("1.0000")
    assert engine.get_user("ALICE").reputation == Decimal("3.0000")

    # Transaction 3: k=3 -> M_3 = 2.0 / 4 = 0.5
    m3 = engine.mint_transaction_reputation("ALICE", "BOB", m0=m0, mint_lambda=lam)
    assert m3 == Decimal("0.5000")
    assert engine.get_user("ALICE").reputation == Decimal("3.5000")

    # Transaction 4: k=4 -> M_4 = 2.0 / 8 = 0.25
    m4 = engine.mint_transaction_reputation("ALICE", "BOB", m0=m0, mint_lambda=lam)
    assert m4 == Decimal("0.2500")
    assert engine.get_user("ALICE").reputation == Decimal("3.7500")


def test_atomic_snapshot_default_penalty_sections_10_to_13():
    """Sections 10-13: Snapshot-based default severity, borrower loss, and endorser penalty."""
    engine = TrustEngine()
    engine.create_user("SPONSOR_1", "Sponsor 1", initial_reputation=Decimal("20.0"), is_anchor=True)
    engine.create_user("SPONSOR_2", "Sponsor 2", initial_reputation=Decimal("10.0"))
    engine.create_user(
        "BORROWER",
        "Borrower",
        initial_reputation=Decimal("10.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("50000.00"),
            net_operating_income=Decimal("30000.00"),
            debt_service=Decimal("5000.00"),
            completeness=Decimal("1.0"),
        ),
    )

    # Sponsors vouch for Borrower
    # Sponsor 1 -> Borrower (rank 1, alpha=1.0) -> contrib = 20.0
    # Sponsor 2 -> Borrower (rank 2, alpha=0.5) -> contrib = 5.0
    engine.vouch("SPONSOR_1", "BORROWER")
    engine.vouch("SPONSOR_2", "BORROWER")

    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)

    # Disburse loan to borrower
    loan = lending.borrow("BORROWER", amount=Decimal("10000.00"), tenure_months=6, interest_rate=Decimal("0.10"))

    # Execute default penalty under 30 days overdue (tau_D = 1.0)
    report = lending.apply_snapshot_default_penalty(
        loan_id=loan.loan_id,
        t_overdue_days=Decimal("30.0"),
        kappa=Decimal("1.5"),
        beta=Decimal("1.0"),
        t0_days=Decimal("30.0"),
        eta=Decimal("0.5"),
        q_max=Decimal("1.0"),
    )

    # 1. Exposure E_D = 10,000
    assert report.outstanding_exposure == Decimal("10000.00")

    # 2. Pre-default credibility: R_D = 10.0, G_D = 20.0 + 5.0 = 25.0
    # Severity S_D = 10,000 * (10 / (10 + 25)) = 10,000 * (10/35) = 2,857.14
    assert Decimal("2857.0") <= report.default_severity <= Decimal("2858.0")

    # 3. Borrower reputation is reduced
    assert report.borrower_post_reputation < report.borrower_pre_reputation
    assert report.borrower_penalty_fraction > Decimal("0.0")
    assert report.applied_atomically is True

    # 4. Endorsers penalized according to their contribution share
    # Total G = 25.0. Sponsor 1 gave 20.0 (80%), Sponsor 2 gave 5.0 (20%)
    assert "SPONSOR_1" in report.endorser_penalties
    assert "SPONSOR_2" in report.endorser_penalties
    detail_1 = report.endorser_penalties["SPONSOR_1"]
    detail_2 = report.endorser_penalties["SPONSOR_2"]

    assert detail_1.contribution_share == Decimal("0.8000")
    assert detail_2.contribution_share == Decimal("0.2000")
    # Sponsor 1 suffered a higher deduction than Sponsor 2 because of higher contribution share
    assert detail_1.delta_reputation > detail_2.delta_reputation
    # Node reputations updated in engine atomically
    assert engine.get_user("SPONSOR_1").reputation == detail_1.post_reputation
    assert engine.get_user("SPONSOR_2").reputation == detail_2.post_reputation


def test_model_simulator_calibration():
    """Verify ModelSimulator runs full parameter sweep across topologies and returns calibrated optima."""
    from veritrust.simulator import ModelSimulator

    sim = ModelSimulator()
    result = sim.calibrate_all()

    # Optimal calibrated parameters
    assert result.optimal_kappa == Decimal("1.50")
    assert result.optimal_lambda == Decimal("0.693147")
    assert result.optimal_delta == Decimal("0.70")
    assert result.optimal_beta == Decimal("1.00")
    assert result.optimal_eta == Decimal("0.50")

    # Swarm mitigation: 50 endorsers cannot exceed 2 * endorser_reputation (20.0)
    swarm_data = result.swarm_saturation_analysis["swarms"]
    assert any(s["swarm_size"] == 20 for s in swarm_data)
    for s in swarm_data:
        assert s["raw_propagated_g"] < 20.0

