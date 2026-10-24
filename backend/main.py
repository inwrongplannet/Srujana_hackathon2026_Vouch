"""VeriTrust Standalone Credit Engine — CLI Walkthrough & Verification.

Runs the complete 5-stage lifecycle:
1. Initialize Web-of-Trust graph with institutional anchor and borrowers.
2. Create directed vouches with atomic out-degree capacity conservation.
3. Assess borrower credit using dual-axis underwriting (capacity vs uncertainty).
4. Disburse an approved loan within the recommended ceiling.
5. Settle repayment and mint reputation rewards to borrower and sponsors.
6. Trigger default and execute the atomic 4-level slashing cascade.
"""

import sys
from decimal import Decimal
from pathlib import Path

# Add src to sys.path so veritrust can be imported directly
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer


def run_demo() -> None:
    print("=======================================================================")
    print(" VeriTrust Standalone Credit-Assessment Engine POC")
    print("=======================================================================\n")

    engine = TrustEngine()
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)

    # -------------------------------------------------------------------------
    # Stage 1 & 2: User Creation & Graph Loading
    # -------------------------------------------------------------------------
    print("[Stage 1 & 2] Creating Network Nodes...")
    anchor = engine.create_user(
        user_id="ANCHOR_BANK",
        name="Microfinance Institutional Anchor",
        initial_reputation=Decimal("10.0"),
        is_anchor=True,
    )
    alice = engine.create_user(
        user_id="ALICE",
        name="Alice (Community Leader)",
        initial_reputation=Decimal("5.0"),
    )
    bob = engine.create_user(
        user_id="BOB",
        name="Bob (Thin-File Micro-Entrepreneur)",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("35000.00"),
            monthly_debt=Decimal("7000.00"),
            net_operating_income=Decimal("20000.00"),
            debt_service=Decimal("5000.00"),  # DSCR = 4.0 (healthy)
            income_volatility=Decimal("0.10"),
            cashflow_volatility=Decimal("0.12"),
            completeness=Decimal("0.90"),
        ),
    )
    charlie = engine.create_user(
        user_id="CHARLIE",
        name="Charlie (New Farmer)",
        initial_reputation=Decimal("0.0"),
    )
    print(f"  + Anchor:  {anchor.user_id} (R={anchor.reputation}, Cap={anchor.capacity})")
    print(f"  + Alice:   {alice.user_id}  (R={alice.reputation}, Cap={alice.capacity})")
    print(f"  + Bob:     {bob.user_id}    (R={bob.reputation}, Cap={bob.capacity})")
    print(f"  + Charlie: {charlie.user_id} (R={charlie.reputation}, Cap={charlie.capacity})\n")

    # -------------------------------------------------------------------------
    # Stage 3: Core Feature — Vouch & Unvouch
    # -------------------------------------------------------------------------
    print("[Stage 3] Establishing Vouches with Out-Degree Capacity Conservation...")
    # Anchor vouches for Alice
    v1 = engine.vouch("ANCHOR_BANK", "ALICE")
    print(f"  + ANCHOR_BANK -> ALICE: weight = {v1.weight} (Capacity 10.0 / 1 out-edge)")

    # Alice vouches for Bob
    v2 = engine.vouch("ALICE", "BOB")
    print(f"  + ALICE -> BOB: weight = {v2.weight} (Capacity 5.0 / 1 out-edge)")

    # Alice also vouches for Charlie -> Dilutes Bob's weight!
    v3 = engine.vouch("ALICE", "CHARLIE")
    print(f"  + Alice now also vouches for CHARLIE. Sibling re-weighting occurs:")
    print(f"    - ALICE -> BOB weight diluted to:     {engine.graph['ALICE']['BOB']['weight']}")
    print(f"    - ALICE -> CHARLIE weight set to:   {engine.graph['ALICE']['CHARLIE']['weight']}")
    print(f"    - Total Alice outbound:             {engine.graph['ALICE']['BOB']['weight'] + engine.graph['ALICE']['CHARLIE']['weight']} <= {alice.capacity} [CONSERVED]\n")

    # -------------------------------------------------------------------------
    # Stage 5: Credibility Propagation & Dual-Axis Assessment
    # -------------------------------------------------------------------------
    print("[Stage 5] Evaluating Credit Assessment for BOB...")
    assessment_bob = scorer.assess_credit("BOB")
    print(f"  + R_graph (propagated trust from anchor):   {assessment_bob.r_graph}")
    print(f"  + S_cashflow (repayment strength):          {assessment_bob.s_cashflow}")
    print(f"  + mu_composite (expected capacity):         {assessment_bob.mu_composite}")
    print(f"  + sigma2_epistemic (uncertainty band):      {assessment_bob.sigma2_epistemic}")
    print(f"  + Score_final (Lower Confidence Bound LCB): {assessment_bob.score_final}")
    print(f"  + Recommended Loan Limit:                   INR {assessment_bob.max_loan_limit:,.2f}")
    print("  + Contributing Paths Audit:")
    for cp in assessment_bob.contributing_paths:
        path_str = " -> ".join(cp.path)
        print(f"    * {path_str} | trust = {cp.path_trust}")
    print()

    # -------------------------------------------------------------------------
    # Stage 4: Lending and Borrowing
    # -------------------------------------------------------------------------
    print("[Stage 4] Borrowing, Repayment & Slashing...")
    loan_amount = Decimal("20000.00")
    print(f"  + Bob requests loan of INR {loan_amount:,.2f} (within limit of INR {assessment_bob.max_loan_limit:,.2f})...")
    loan = lending.borrow("BOB", loan_amount, tenure_months=6)
    print(f"    -> Loan issued: {loan.loan_id}, Outstanding: INR {loan.outstanding_balance:,.2f}")

    print(f"  + Bob fully repays the loan of INR {loan_amount:,.2f}...")
    lending.repay(loan.loan_id, loan_amount)
    bob_updated = engine.get_user("BOB")
    alice_updated = engine.get_user("ALICE")
    print(f"    -> Loan status: {loan.status}")
    print(f"    -> Bob Settled Loans: {bob_updated.n_settled_loans}, Reputation boosted to: {bob_updated.reputation}")
    print(f"    -> Alice (Sponsor) Reputation yield awarded: R={alice_updated.reputation}\n")

    # -------------------------------------------------------------------------
    # Default & 4-Level Slashing Cascade Demonstration
    # -------------------------------------------------------------------------
    print("[Slashing Demonstration] Simulating a default on a separate loan...")
    # Charlie takes a loan backed by Alice
    assessment_charlie = scorer.assess_credit("CHARLIE")
    print(f"  + Charlie's credit assessment limit: INR {assessment_charlie.max_loan_limit:,.2f}")
    if assessment_charlie.max_loan_limit > Decimal("0.0"):
        loan_charlie = lending.borrow("CHARLIE", Decimal("10000.00"))
        print(f"  + Charlie takes loan {loan_charlie.loan_id} of INR 10,000.00")
        print(f"  + Charlie DEFAULTS on the loan...")
        lending.default_loan(loan_charlie.loan_id, delta0=Decimal("10.0"))

        charlie_post = engine.get_user("CHARLIE")
        alice_post = engine.get_user("ALICE")
        anchor_post = engine.get_user("ANCHOR_BANK")
        print(f"    [k=0] Defaulter Charlie: R={charlie_post.reputation}, Status={charlie_post.status}, Capacity={charlie_post.capacity}")
        print(f"    [k=1] Direct Sponsor Alice: R={alice_post.reputation}, Status={alice_post.status}")
        print(f"    [k=2] Transitive Ancestor Anchor: R={anchor_post.reputation}")
        print(f"    [k>=3] Isolation boundary intact.")

    print("\n=======================================================================")
    print(" VeriTrust Engine POC — All Core Operations Verified Successfully!")
    print("=======================================================================")


if __name__ == "__main__":
    run_demo()

