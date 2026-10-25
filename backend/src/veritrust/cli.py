"""VeriTrust CLI -- Web-of-Trust Credit Assessment & Lending.

Inspired by mitchellh/vouch transparent flat-file and command interface.
Supports both single-shot CLI invocations and an interactive REPL shell.
"""

import argparse
from decimal import Decimal
import sys
from typing import Optional

from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.ledger import ReputationLedger
from veritrust.models import Evidence, FinancialFeatures, Loan
from veritrust.scoring import CreditScorer
from veritrust.store import StateStore


def _init_context() -> tuple[TrustEngine, CreditScorer, LendingService, StateStore, Optional[str]]:
    store = StateStore()
    ledger = ReputationLedger(db_path=store.data_dir / "ledger.db", jsonl_path=store.data_dir / "events.jsonl")
    engine = TrustEngine(ledger=ledger)
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)
    store.load(engine, lending)
    current_user = store.get_current_user()
    return engine, scorer, lending, store, current_user


# -----------------------------------------------------------------------------
# Command Handlers
# -----------------------------------------------------------------------------

def cmd_user_create(args: argparse.Namespace) -> None:
    engine, scorer, lending, store, _ = _init_context()
    user_id = args.user_id.strip()
    name = args.name or user_id
    rep = Decimal(str(getattr(args, "reputation", "0.0")))
    is_anchor = getattr(args, "anchor", False)

    income = getattr(args, "income", None)
    debt = getattr(args, "debt", None)
    noi = getattr(args, "noi", None)
    debt_service = getattr(args, "debt_service", None)
    completeness = getattr(args, "completeness", "1.0")

    ff = None
    if income is not None or debt is not None or noi is not None:
        ff = FinancialFeatures(
            monthly_income=Decimal(str(income or "0.0")),
            monthly_debt=Decimal(str(debt or "0.0")),
            net_operating_income=Decimal(str(noi or income or "0.0")),
            debt_service=Decimal(str(debt_service or debt or "0.0")),
            completeness=Decimal(str(completeness or "1.0")),
        )

    try:
        user = engine.create_user(
            user_id=user_id,
            name=name,
            initial_reputation=rep,
            is_anchor=is_anchor,
            financial_features=ff,
        )
        store.save(engine, lending)
        print(f"Created user '{user.user_id}' (Name: {user.name}, R: {user.reputation}, Cap: {user.capacity}, Anchor: {user.is_anchor})")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_user_list(args: argparse.Namespace) -> None:
    engine, _, lending, store, current_user = _init_context()
    users = engine.list_users()
    if not users:
        print("No users registered.")
        return

    print("=========================================================================================")
    print(f"{'User ID':<15} {'Name':<28} {'Reputation':<12} {'Capacity':<10} {'Status':<12} {'Anchor'}")
    print("-----------------------------------------------------------------------------------------")
    for u in users:
        prefix = "* " if u.user_id == current_user else "  "
        print(
            f"{prefix + u.user_id:<15} {u.name:<28} {str(u.reputation):<12} {str(u.capacity):<10} {u.status:<12} {str(u.is_anchor)}"
        )
    print("=========================================================================================")
    if current_user:
        print(f"(* = active logged in user: {current_user})")


def cmd_login(args: argparse.Namespace) -> None:
    engine, _, lending, store, _ = _init_context()
    user_id = args.user_id.strip()
    user = engine.get_user(user_id)
    if not user:
        print(f"Error: User '{user_id}' not found. Create them first with 'user create'.")
        sys.exit(1)

    store.set_current_user(user_id)
    print(f"Logged in as '{user.user_id}' ({user.name}).")
    print(f"Reputation: {user.reputation} | Capacity: {user.capacity} | Status: {user.status}")


def cmd_whoami(args: argparse.Namespace) -> None:
    engine, scorer, lending, store, current_user = _init_context()
    if not current_user:
        print("Not logged in. Use 'login <user_id>' to log in.")
        return

    user = engine.get_user(current_user)
    if not user:
        print(f"Error: Session user '{current_user}' no longer exists.")
        store.set_current_user(None)
        return

    assessment = scorer.assess_credit(user.user_id)
    active_loans = [l for l in lending.list_loans() if l.borrower_id == user.user_id and l.status == "ACTIVE"]
    vouched_for = list(engine.graph.successors(user.user_id))
    vouched_by = list(engine.graph.predecessors(user.user_id))

    print("=======================================================================")
    print(f" Active Session: {user.user_id} ({user.name})")
    print("=======================================================================")
    print(f"  + Protocol Status:         {user.status}")
    print(f"  + Intrinsic Reputation:    {user.reputation}")
    print(f"  + Distributable Capacity:  {user.capacity} (conserved across {len(vouched_for)} vouches)")
    print(f"  + Settled Loans Count:     {user.n_settled_loans}")
    print(f"  + Graph Trust Score (R):   {assessment.r_graph}")
    print(f"  + Cash-Flow Score (S):     {assessment.s_cashflow}")
    print(f"  + Uncertainty (sigma2):    {assessment.sigma2_epistemic}")
    print(f"  + LCB Decision Score:      {assessment.score_final}")
    print(f"  + Approved Borrow Limit:   INR {assessment.max_loan_limit:,.2f}")
    print(f"  + Active Borrowed Loans:   {len(active_loans)}")
    print(f"  + Endorsed by (Vouched By): {', '.join(vouched_by) if vouched_by else 'None'}")
    print(f"  + Sponsoring (Vouched For): {', '.join(vouched_for) if vouched_for else 'None'}")
    print("=======================================================================")


def cmd_logout(args: argparse.Namespace) -> None:
    _, _, _, store, _ = _init_context()
    store.set_current_user(None)
    print("Logged out successfully.")


def cmd_vouch(args: argparse.Namespace) -> None:
    engine, _, lending, store, current_user = _init_context()
    source_id = args.source or current_user
    if not source_id:
        print("Error: Must be logged in or specify --source <user_id> to vouch.")
        sys.exit(1)

    target_id = args.target.strip()
    try:
        vouch = engine.vouch(source_id, target_id)
        store.save(engine, lending)
        print(f"Vouched! '{source_id}' -> '{target_id}'")
        print(f"Assigned weight: {vouch.weight}")
        out_edges = list(engine.graph.out_edges(source_id, data=True))
        print(f"Outbound capacity conserved ({len(out_edges)} siblings re-weighted):")
        for _, t, d in out_edges:
            print(f"  - {source_id} -> {t}: weight = {d.get('weight')}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_unvouch(args: argparse.Namespace) -> None:
    engine, _, lending, store, current_user = _init_context()
    source_id = args.source or current_user
    if not source_id:
        print("Error: Must be logged in or specify --source <user_id> to unvouch.")
        sys.exit(1)

    target_id = args.target.strip()
    try:
        engine.unvouch(source_id, target_id)
        store.save(engine, lending)
        print(f"Unvouched! Removed endorsement from '{source_id}' to '{target_id}'.")
        out_edges = list(engine.graph.out_edges(source_id, data=True))
        if out_edges:
            print(f"Remaining capacity redistributed across {len(out_edges)} siblings:")
            for _, t, d in out_edges:
                print(f"  - {source_id} -> {t}: weight = {d.get('weight')}")
        else:
            print(f"Source '{source_id}' now has 0 active outgoing vouches.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_assess(args: argparse.Namespace) -> None:
    engine, scorer, _, _, current_user = _init_context()
    target_id = args.user_id or current_user
    if not target_id:
        print("Error: Specify a user_id or log in with 'login <user_id>'.")
        sys.exit(1)

    try:
        assessment = scorer.assess_credit(target_id)
        user = engine.get_user(target_id)
        print("=======================================================================")
        print(f" Credit Assessment Report for: {target_id} ({user.name if user else ''})")
        print("=======================================================================")
        print(f"  + Graph Trust Score (R_graph):       {assessment.r_graph}")
        print(f"  + Cash-Flow Score (S_cashflow):      {assessment.s_cashflow}")
        print(f"  + Expected Capacity (mu_composite):  {assessment.mu_composite}")
        print(f"  + Epistemic Uncertainty (sigma2):    {assessment.sigma2_epistemic}")
        print(f"  + Lower Confidence Bound (Score):    {assessment.score_final}")
        print(f"  + Maximum Approved Credit Limit:     INR {assessment.max_loan_limit:,.2f}")
        print(f"  + Disclaimer: {assessment.disclaimer}")
        if assessment.contributing_paths:
            print("  + Active Trust Paths from Anchors:")
            for p in assessment.contributing_paths:
                print(f"    * {' -> '.join(p.path)} | Path Trust = {p.path_trust}")
        else:
            print("  + Active Trust Paths from Anchors: None (Unconnected or unvouched)")
        print("=======================================================================")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_borrow(args: argparse.Namespace) -> None:
    engine, scorer, lending, store, current_user = _init_context()
    borrower_id = args.borrower or current_user
    if not borrower_id:
        print("Error: Must be logged in or specify --borrower <user_id> to borrow.")
        sys.exit(1)

    amount = Decimal(str(args.amount))
    tenure = args.tenure

    try:
        loan = lending.borrow(borrower_id, amount, tenure_months=tenure)
        store.save(engine, lending)
        print(f"Loan Approved & Disbursed!")
        print(f"  + Loan ID:             {loan.loan_id}")
        print(f"  + Borrower:            {loan.borrower_id}")
        print(f"  + Principal Amount:    INR {loan.principal:,.2f}")
        print(f"  + Outstanding Balance: INR {loan.outstanding_balance:,.2f}")
        print(f"  + Status:              {loan.status}")
    except ValueError as e:
        print(f"Borrowing Failed: {e}")
        sys.exit(1)


def cmd_repay(args: argparse.Namespace) -> None:
    engine, _, lending, store, _ = _init_context()
    loan_id = args.loan_id.strip()
    amount = Decimal(str(args.amount))

    try:
        loan_before = lending.get_loan(loan_id)
        if not loan_before:
            print(f"Error: Loan '{loan_id}' does not exist.")
            sys.exit(1)
        prev_balance = loan_before.outstanding_balance

        loan = lending.repay(loan_id, amount)
        actual_payment = prev_balance - loan.outstanding_balance
        refund = max(Decimal("0.00"), amount - actual_payment)
        store.save(engine, lending)

        print(f"Repayment Processed for Loan '{loan_id}'!")
        print(f"  + Payment Applied:     INR {actual_payment:,.2f}")
        if refund > Decimal("0.00"):
            print(f"  + Excess Refunded:     INR {refund:,.2f} (Payment exceeded total debt balance)")
        print(f"  + Outstanding Balance: INR {loan.outstanding_balance:,.2f}")
        print(f"  + Contract Status:     {loan.status}")
        if loan.status == "REPAID":
            borrower = engine.get_user(loan.borrower_id)
            print("Full settlement achieved! Protocol yields awarded:")
            if borrower:
                print(f"  + Borrower '{borrower.user_id}' credibility boosted to: R={borrower.reputation}")
            in_edges = list(engine.graph.in_edges(loan.borrower_id))
            for sponsor_id, _ in in_edges:
                s = engine.get_user(sponsor_id)
                if s:
                    print(f"  + Sponsor '{s.user_id}' reputation yield awarded: R={s.reputation}")
    except ValueError as e:
        print(f"Repayment Failed: {e}")
        sys.exit(1)


def cmd_lend(args: argparse.Namespace) -> None:
    """Direct peer lending / funding."""
    engine, scorer, lending, store, current_user = _init_context()
    lender_id = args.lender or current_user
    borrower_id = args.borrower.strip()
    amount = Decimal(str(args.amount))
    tenure = args.tenure

    if not lender_id:
        print("Error: Must be logged in or specify --lender <user_id>.")
        sys.exit(1)

    try:
        loan = lending.lend(
            lender_id=lender_id,
            borrower_id=borrower_id,
            amount=amount,
            tenure_months=tenure,
        )
        store.save(engine, lending)
        print(f"Lending Successful! Lender '{lender_id}' funded Borrower '{borrower_id}'")
        print(f"  + Loan ID:             {loan.loan_id}")
        print(f"  + Lender ID:           {loan.lender_id}")
        print(f"  + Principal Amount:    INR {loan.principal:,.2f}")
        print(f"  + Outstanding Balance: INR {loan.outstanding_balance:,.2f}")
        print(f"  + Status:              {loan.status}")
    except ValueError as e:
        print(f"Lending Failed: {e}")
        sys.exit(1)


def cmd_check(args: argparse.Namespace) -> None:
    """Check a user's trust and credit standing (inspired by mitchellh/vouch check)."""
    engine, scorer, _, _, _ = _init_context()
    user_id = args.user_id.strip()
    user = engine.get_user(user_id)
    if not user:
        print(f"UNKNOWN: User '{user_id}' does not exist.")
        sys.exit(2)

    if user.status == "DEFAULTED":
        print(f"DENOUNCED (DEFAULTED): User '{user_id}' is defaulted/denounced.")
        print(f"  + Reputation: {user.reputation}")
        print(f"  + Capacity:   {user.capacity} (Frozen)")
        print(f"  + Limit:      INR 0.00")
        sys.exit(1)

    assessment = scorer.assess_credit(user_id)
    in_edges = list(engine.graph.in_edges(user_id))
    if in_edges or user.is_anchor:
        print(f"VOUCHED: User '{user_id}' is actively endorsed by {len(in_edges)} peer(s).")
        print(f"  + Reputation:    {user.reputation}")
        print(f"  + Capacity:      {user.capacity}")
        print(f"  + Graph Trust:   {assessment.r_graph}")
        print(f"  + Score (LCB):   {assessment.score_final}")
        print(f"  + Credit Limit:  INR {assessment.max_loan_limit:,.2f}")
        sys.exit(0)
    else:
        print(f"UNVOUCHED: User '{user_id}' has no active endorsements.")
        print(f"  + Credit Limit:  INR 0.00")
        sys.exit(2)


def cmd_denounce(args: argparse.Namespace) -> None:
    """Denounce a bad actor and trigger cascade penalty (inspired by mitchellh/vouch denounce)."""
    engine, _, lending, store, _ = _init_context()
    user_id = args.user_id.strip()
    reason = args.reason or "Untrusted actor / default event"

    user = engine.get_user(user_id)
    if not user:
        print(f"Error: User '{user_id}' does not exist.")
        sys.exit(1)

    denounce_evidence = Evidence(
        evidence_id=f"EVID_DENOUNCE_{user_id}",
        evidence_type="DEFAULT_NOTICE",
        description=f"Public denouncement of {user_id}: {reason}",
        recorded_by="COMMUNITY_CONSENSUS",
    )

    # Find active loans or create a default event trigger
    active_loans = [l for l in lending.list_loans() if l.borrower_id == user_id and l.status == "ACTIVE"]
    if active_loans:
        for loan in active_loans:
            lending.default_loan(loan.loan_id, evidence=denounce_evidence)
    else:
        # Direct denouncement of node
        synthetic_id = f"DENOUNCE_{user_id}"
        fake_loan = Loan(
            loan_id=synthetic_id,
            borrower_id=user_id,
            principal=Decimal("0.0"),
            outstanding_balance=Decimal("0.0"),
            status="ACTIVE",
        )
        lending.loans[synthetic_id] = fake_loan
        lending.default_loan(synthetic_id, evidence=denounce_evidence)

    store.save(engine, lending)
    print(f"DENOUNCED: '{user_id}' has been denounced!")
    print(f"  + Reason: {reason}")
    print(f"  + Node status updated to DEFAULTED with capacity frozen (C=0).")
    print(f"  + 4-level slashing cascade applied to all sponsors.")


def cmd_default(args: argparse.Namespace) -> None:
    engine, _, lending, store, _ = _init_context()
    loan_id = args.loan_id.strip()
    slash = Decimal(str(args.slash)) if args.slash is not None else None

    try:
        loan = lending.get_loan(loan_id)
        if not loan:
            print(f"Error: Loan '{loan_id}' not found.")
            sys.exit(1)
        borrower_id = loan.borrower_id
        lending.default_loan(loan_id, delta0=slash)
        store.save(engine, lending)

        defaulter = engine.get_user(borrower_id)
        print("Default Processed! Atomic 4-level slashing cascade executed:")
        print(f"  + [k=0] Defaulter '{borrower_id}': R={defaulter.reputation if defaulter else 0}, Status={defaulter.status if defaulter else ''}, Capacity=0")
        print("  + [k=1] Direct Sponsors slashed proportionally.")
        print("  + [k=2] Transitive Ancestors slashed with quadratic damping.")
        print("  + [k>=3] Hard contagion cutoff preserved.")
    except ValueError as e:
        print(f"Default Failed: {e}")
        sys.exit(1)


def cmd_loans(args: argparse.Namespace) -> None:
    _, _, lending, _, current_user = _init_context()
    target = args.user_id or (current_user if args.mine else None)
    loans = lending.list_loans()
    if target:
        loans = [l for l in loans if l.borrower_id == target]

    if not loans:
        print(f"No loans found{' for ' + target if target else ''}.")
        return

    print("=========================================================================================")
    print(f"{'Loan ID':<12} {'Borrower':<15} {'Principal (INR)':<18} {'Balance (INR)':<18} {'Status'}")
    print("-----------------------------------------------------------------------------------------")
    for l in loans:
        print(f"{l.loan_id:<12} {l.borrower_id:<15} {l.principal:<18} {l.outstanding_balance:<18} {l.status}")
    print("=========================================================================================")


def cmd_graph(args: argparse.Namespace) -> None:
    engine, _, _, _, _ = _init_context()
    users = engine.list_users()
    print("=======================================================================")
    print(" VeriTrust Web-of-Trust Topology")
    print("=======================================================================")
    for u in users:
        anchor_tag = " [ANCHOR]" if u.is_anchor else ""
        print(f"Node: {u.user_id}{anchor_tag} | R={u.reputation} | Cap={u.capacity} | Status={u.status}")
        out_edges = list(engine.graph.out_edges(u.user_id, data=True))
        if out_edges:
            for _, target, data in out_edges:
                print(f"  +-- vouches for -> {target:<12} (weight: {data.get('weight')})")
        else:
            print("  +-- (no outgoing endorsements)")
        print()
    print("=======================================================================")


def cmd_history(args: argparse.Namespace) -> None:
    """View append-only reputation ledger events and auditable evidence."""
    engine, _, _, _, current_user = _init_context()
    target = args.user_id or (current_user if getattr(args, "mine", False) else None)
    ledger: ReputationLedger = engine.ledger  # type: ignore

    if target:
        events = ledger.get_history(target)
        title = f"Reputation Event Ledger for: {target}"
    else:
        events = ledger.list_all_events()
        title = "Complete VeriTrust Reputation Ledger (All Events)"

    if not events:
        print(f"No ledger events found{' for user ' + target if target else ''}.")
        return

    print("==========================================================================================================")
    print(f" {title}")
    print("==========================================================================================================")
    print(f"{'Seq':<5} {'Timestamp (UTC)':<20} {'Event Type':<19} {'Actor':<12} {'Subject':<10} {'Delta R':<10} {'Evidence ID'}")
    print("----------------------------------------------------------------------------------------------------------")
    net_rep = Decimal("0.0")
    for evt in events:
        ts_str = evt.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        evidence_id = evt.evidence.evidence_id if evt.evidence else "N/A"
        delta_str = f"+{evt.delta_reputation}" if evt.delta_reputation > Decimal("0.0") else str(evt.delta_reputation)
        if target and evt.subject_id == target:
            net_rep += evt.delta_reputation

        print(
            f"{evt.sequence:<5} {ts_str:<20} {evt.event_type:<19} {evt.actor_id:<12} {evt.subject_id:<10} {delta_str:<10} {evidence_id}"
        )
    print("==========================================================================================================")
    if target:
        print(f"Net Recorded Reputation Delta from Events: {net_rep}")
    print(f"Total Events: {len(events)} | Current Ledger Head: {events[-1].event_hash[:16]}... (Sequence #{events[-1].sequence})")


def cmd_audit(args: argparse.Namespace) -> None:
    """Cryptographically audit the append-only ledger hash chain from Genesis to Head."""
    engine, _, _, _, _ = _init_context()
    ledger: ReputationLedger = engine.ledger  # type: ignore

    is_valid, err = ledger.verify_integrity()
    head = ledger.get_latest_event()
    count = ledger.count()

    print("=======================================================================")
    print(" VeriTrust Reputation Ledger -- Cryptographic Integrity Audit")
    print("=======================================================================")
    if is_valid:
        print("  Status:            [OK] SECURE -- All SHA-256 hash links & payloads verified")
        print(f"  Total Events:      {count}")
        print("  Genesis Hash:      0000000000000000... (Root Anchor)")
        if head:
            print(f"  Ledger Head Hash:  {head.event_hash}")
            print(f"  Last Sequence #:   {head.sequence} ({head.event_type})")
        print(f"  SQLite Store:      {ledger.db_path}")
        print(f"  JSONL Mirror:      {ledger.jsonl_path}")
        print("=======================================================================")
    else:
        print("  Status:            [FAIL] TAMPER / INTEGRITY VIOLATION DETECTED")
        print(f"  Error Diagnostic:  {err}")
        print(f"  Total Events:      {count}")
        print("=======================================================================")
        sys.exit(1)


def cmd_replay(args: argparse.Namespace) -> None:
    """Reconstruct graph topology and reputation state purely from immutable ledger events."""
    engine, scorer, lending, store, _ = _init_context()
    ledger: ReputationLedger = engine.ledger  # type: ignore

    print("=======================================================================")
    print(" VeriTrust Ledger Replay & Disaster Recovery")
    print("=======================================================================")
    try:
        replayed_engine, replayed_lending = ledger.reconstruct_state()  # type: ignore
        n_users = len(replayed_engine.list_users())
        n_vouches = len([v for v in replayed_engine.vouches.values() if v.active])
        n_loans = len(replayed_lending.list_loans())

        print("  Cryptographic Chain:  [OK] 100% Verified")
        print(f"  Events Replayed:      {ledger.count()}")
        print(f"  Reconstructed State:  {n_users} Users, {n_vouches} Active Vouches, {n_loans} Loans")

        # Compare with live state in memory
        live_users = len(engine.list_users())
        divergence = False
        for u in replayed_engine.list_users():
            live_u = engine.get_user(u.user_id)
            if not live_u or live_u.reputation != u.reputation or live_u.status != u.status:
                divergence = True
                break

        if not divergence and live_users == n_users:
            print("  State Consistency:    [MATCH] Replayed state exactly matches live state store.")
        else:
            print("  State Consistency:    [DIVERGENCE] Live state file diverges from immutable ledger!")

        if getattr(args, "restore", False):
            store.save(replayed_engine, replayed_lending)
            print("  [RESTORE COMPLETE] Synchronized store.json with reconstructed state.")
        else:
            print("  (Run with --restore to overwrite store.json with verified reconstructed state)")
        print("=======================================================================")
    except Exception as e:
        print(f"Replay Failed: {e}")
        sys.exit(1)


def cmd_reset(args: argparse.Namespace) -> None:
    store = StateStore()
    ledger_db = store.data_dir / "ledger.db"
    events_jsonl = store.data_dir / "events.jsonl"
    if ledger_db.exists():
        try:
            ledger_db.unlink()
        except Exception:
            pass
    if events_jsonl.exists():
        try:
            events_jsonl.unlink()
        except Exception:
            pass

    ledger = ReputationLedger(db_path=ledger_db, jsonl_path=events_jsonl)
    engine = TrustEngine(ledger=ledger)
    scorer = CreditScorer(engine)
    lending = LendingService(engine, scorer)
    store.seed_defaults(engine, lending)
    store.save(engine, lending)
    store.set_current_user(None)
    print("Reset complete! Initialized fresh demo graph, ledger events, and cleared sessions.")


def cmd_optimize(args: argparse.Namespace) -> None:
    """Evaluate loan plan using rule-based affordability, OR-Tools optimizer, Monte Carlo stress testing, and explanation engine."""
    from veritrust.affordability import AffordabilityEngine, AffordabilityInput
    from veritrust.explainer import ExplanationEngine
    from veritrust.optimizer import LoanOptimizer
    from veritrust.stress_tester import MonteCarloStressTester

    engine, scorer, lending, store, current_user = _init_context()
    borrower_id = args.borrower or current_user
    if not borrower_id:
        print("Error: Specify a user ID with --borrower <id> or log in with 'login <id>'.")
        sys.exit(1)

    user = engine.get_user(borrower_id)
    if not user:
        print(f"Error: User '{borrower_id}' does not exist.")
        sys.exit(1)

    requested_p = Decimal(str(args.amount))
    requested_t = int(args.tenure or 6)
    objective = getattr(args, "objective", "MIN_COST")

    ff = user.financial_features
    income = (
        Decimal(str(args.income))
        if getattr(args, "income", None)
        else (ff.monthly_income if ff and ff.monthly_income > 0 else Decimal("35000.00"))
    )
    debt = (
        Decimal(str(args.debt))
        if getattr(args, "debt", None)
        else (ff.monthly_debt if ff else Decimal("0.00"))
    )
    expenses = (
        Decimal(str(args.expenses))
        if getattr(args, "expenses", None)
        else ((ff.monthly_income - ff.net_operating_income) if ff and ff.net_operating_income > 0 else Decimal("18000.00"))
    )
    completeness = ff.completeness if ff else Decimal("0.85")
    is_verified = getattr(args, "verified", False) or user.is_anchor or (ff is not None and completeness >= Decimal("0.90"))

    afford_input = AffordabilityInput(
        monthly_income=income,
        essential_expenses=expenses,
        existing_debt_service=debt,
        data_completeness=completeness,
        is_verified=is_verified,
    )

    try:
        assessment = scorer.assess_credit(borrower_id)
        limit = assessment.max_loan_limit
    except Exception:
        assessment = None
        limit = Decimal("50000.00")

    afford_engine = AffordabilityEngine()
    afford_res = afford_engine.evaluate(afford_input)

    optimizer = LoanOptimizer(afford_engine)
    opt_res = optimizer.optimize(
        affordability_input=afford_input,
        requested_principal=requested_p,
        requested_tenure_months=requested_t,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=limit,
        objective=objective,
    )

    plan_to_test = opt_res.best_feasible_alternative or opt_res.original_request
    stress_tester = MonteCarloStressTester()
    stress_res = stress_tester.stress_test(
        monthly_income=income,
        essential_expenses=expenses + debt,
        monthly_emi=plan_to_test.monthly_emi,
        tenure_months=plan_to_test.tenure_months,
        initial_cash_buffer=afford_res.effective_buffer,
    )

    explainer = ExplanationEngine()
    explanation = explainer.explain(
        affordability=afford_res,
        optimization=opt_res,
        stress_test=stress_res,
        credit_assessment=assessment,
    )

    print("=======================================================================")
    print(" VeriTrust Loan Affordability, Optimization & Stress Test Report")
    print(f" Borrower: {borrower_id} ({user.name}) | Status: [{explanation.verdict}]")
    print("=======================================================================")
    print("\n[EXECUTIVE SUMMARY]")
    print(f"  {explanation.narrative_summary}")

    print("\n[1. FINANCIAL CAPACITY DIMENSION]")
    print(f"  + Gross Monthly Income:       INR {afford_res.monthly_income:,.2f}")
    print(f"  + Non-Discretionary Outflows: INR {afford_res.total_non_discretionary:,.2f} (Expenses: {afford_res.essential_expenses:,.2f}, Debt: {afford_res.existing_debt_service:,.2f})")
    print(f"  + Protected Cash Buffer (B):  INR {afford_res.effective_buffer:,.2f} (Safety reserve)")
    print(f"  + Disposable Income (D):      INR {afford_res.disposable_income:,.2f}")
    print(f"  + Maximum Affordable EMI:     INR {afford_res.max_affordable_emi:,.2f} / month")
    print(f"  + Binding Policy Rule:        {afford_res.binding_policy_rule}")

    print("\n[2. OR-TOOLS PLAN OPTIMIZATION]")
    orig = opt_res.original_request
    status_tag = "[FEASIBLE]" if orig.is_feasible else "[VIOLATES CONSTRAINTS]"
    print(f"  * Requested Plan {status_tag}:")
    print(f"      Principal: INR {orig.principal:,.2f} | Tenure: {orig.tenure_months}m | EMI: INR {orig.monthly_emi:,.2f} | Total Interest: INR {orig.total_interest:,.2f}")
    if orig.infeasibility_reasons:
        for r in orig.infeasibility_reasons:
            print(f"      ! Infeasibility: {r}")

    if opt_res.best_feasible_alternative:
        best = opt_res.best_feasible_alternative
        print(f"  * Best Feasible Plan ({best.label}):")
        print(f"      Principal: INR {best.principal:,.2f} | Tenure: {best.tenure_months}m | EMI: INR {best.monthly_emi:,.2f} | Total Interest: INR {best.total_interest:,.2f}")

    if opt_res.binding_constraints:
        print("  * Constraints Restricting Other Plans:")
        for bc in opt_res.binding_constraints:
            print(f"      - {bc}")

    if opt_res.feasible_options:
        print("  * Alternative Qualifying Restructuring Options:")
        for opt in opt_res.feasible_options:
            print(f"      - {opt.label:<30}: Principal INR {opt.principal:,.2f} | {opt.tenure_months}m @ EMI INR {opt.monthly_emi:,.2f} (Total Int: INR {opt.total_interest:,.2f})")

    print("\n[3. MONTE CARLO STRESS TEST RESILIENCE (5,000 Scenarios)]")
    print(f"  + Stress Resilience Rating:   [{stress_res.stress_rating}]")
    print(f"  + Default / Shortfall Risk:   {stress_res.shortfall_frequency_pct}% across simulated tenure")
    print(f"  + Adverse 5th-Percentile Cash: INR {stress_res.residual_cash_p05:,.2f} (Severe economic shock cushion)")
    print(f"  + Income Shock Tolerance:     Can absorb a {stress_res.shock_tolerance_pct}% income drop before deficit")
    print(f"  + Affordability Breaking Point: Deficit occurs if income falls below INR {stress_res.affordability_break_income:,.2f}/month")

    print("\n[4. EVIDENCE RELIABILITY & GRAPH REPUTATION DIMENSIONS]")
    print(f"  + Reliability Status:         {explanation.dimension_evidence_reliability.status}")
    print(f"  + Documentation Confidence:   {explanation.dimension_evidence_reliability.headline}")
    print(f"  + Web-of-Trust Standing:      {explanation.dimension_graph_reputation.headline}")
    if assessment and assessment.contributing_paths:
        for p in assessment.contributing_paths[:2]:
            print(f"      Trust Path: {' -> '.join(p.path)} (Weight: {p.path_trust})")

    if explanation.restructuring_guidance:
        print("\n[RECOMMENDED ACTION PLAN]")
        for note in explanation.restructuring_guidance:
            print(f"  => {note}")
    print("=======================================================================")


def cmd_counterfactual(args: argparse.Namespace) -> None:
    """Run deterministic counterfactual what-if simulation on a proposed loan plan."""
    from veritrust.counterfactual import CounterfactualSimulator
    engine, scorer, lending, store, current_user = _init_context()
    borrower_id = args.borrower or current_user
    if not borrower_id:
        print("Error: Specify a user ID with --borrower <id> or log in with 'login <id>'.")
        sys.exit(1)

    user = engine.get_user(borrower_id)
    if not user:
        print(f"Error: User '{borrower_id}' does not exist.")
        sys.exit(1)

    ff = user.financial_features
    income = Decimal(str(args.income)) if args.income else (ff.monthly_income if ff and ff.monthly_income > 0 else Decimal("35000.00"))
    debt = Decimal(str(args.debt)) if args.debt else (ff.monthly_debt if ff else Decimal("0.00"))
    expenses = Decimal(str(args.expenses)) if args.expenses else ((ff.monthly_income - ff.net_operating_income) if ff and ff.net_operating_income > 0 else Decimal("18000.00"))
    amount = Decimal(str(args.amount))
    tenure = int(args.tenure or 6)

    try:
        assessment = scorer.assess_credit(borrower_id)
        limit = assessment.max_loan_limit
    except Exception:
        limit = Decimal("50000.00")

    simulator = CounterfactualSimulator()
    report = simulator.simulate(
        monthly_income=income,
        essential_expenses=expenses,
        existing_debt=debt,
        requested_principal=amount,
        requested_tenure_months=tenure,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=limit,
    )

    print("=======================================================================")
    print(" VeriTrust Counterfactual What-If Simulator")
    print(f" Borrower: {borrower_id} ({user.name}) | Status: [{'FEASIBLE' if report.is_requested_feasible else 'INFEASIBLE'}]")
    print("=======================================================================")
    print("\n[EXECUTIVE SUMMARY]")
    print(f"  {report.explanation_narrative}")

    if not report.is_requested_feasible:
        print(f"\n[BINDING CONSTRAINT]: {report.binding_constraint}")
        print("\n[COUNTERFACTUAL REMEDIES TO ACHIEVE FEASIBILITY]")
        for remedy in report.actionable_remedies:
            print(f"  => {remedy}")
    else:
        print("\n[SAFETY MARGIN ANALYSIS]")
        print(f"  + Income Shock Margin:   Income can drop by INR {report.income_drop_margin_before_infeasible:,.2f}/mo before becoming unaffordable.")
        print(f"  + Expense Shock Margin:  Expenses can rise by INR {report.expense_increase_margin_before_infeasible:,.2f}/mo before exceeding budget.")

    print("\n[SIDE-BY-SIDE PLAN COMPARISON]")
    print(f"{'Plan Label':<26} {'Principal':<14} {'Term':<5} {'EMI (INR)':<14} {'Total Int':<14} {'Residual Cash':<14} {'Feasibility'}")
    print("-" * 105)
    for row in report.comparison_table:
        print(
            f"{row.plan_label:<26} {row.principal:<14,.2f} {str(row.tenure_months) + 'm':<5} {row.monthly_emi:<14,.2f} {row.total_interest:<14,.2f} {row.residual_monthly_cash:<14,.2f} {row.status_summary}"
        )
    print("=======================================================================")


def cmd_stress_compare(args: argparse.Namespace) -> None:
    """Compare two loan plans side-by-side under identical Monte Carlo futures."""
    from veritrust.stress_tester import MonteCarloStressTester
    from veritrust.affordability import calculate_emi

    engine, _, _, _, current_user = _init_context()
    income = Decimal(str(args.income or "35000.00"))
    expenses = Decimal(str(args.expenses or "18000.00"))

    # Plan A
    p_a = Decimal(str(args.principal_a))
    t_a = int(args.tenure_a or 6)
    emi_a = calculate_emi(p_a, Decimal("0.10"), t_a)

    # Plan B
    p_b = Decimal(str(args.principal_b))
    t_b = int(args.tenure_b or 12)
    emi_b = calculate_emi(p_b, Decimal("0.10"), t_b)

    tester = MonteCarloStressTester()
    report = tester.compare_plans(
        monthly_income=income,
        essential_expenses=expenses,
        plan_a_emi=emi_a,
        plan_a_tenure=t_a,
        plan_b_emi=emi_b,
        plan_b_tenure=t_b,
        plan_a_name=f"Plan A (INR {p_a:,.0f} @ {t_a}m)",
        plan_b_name=f"Plan B (INR {p_b:,.0f} @ {t_b}m)",
    )

    print("=======================================================================")
    print(" VeriTrust Side-by-Side Monte Carlo Comparative Dashboard")
    print(f" Simulations: {report.simulations_evaluated:,} Identical Stochastic Futures")
    print(f" Verdict: [{report.risk_reduction_verdict}]")
    print("=======================================================================")
    print("\n[HEAD-TO-HEAD TRADE-OFF SUMMARY]")
    print(f"  {report.tradeoff_summary}")

    print("\n[COMPARATIVE METRICS TABLE]")
    print(f"{'Metric':<34} {report.plan_a_name:<28} {report.plan_b_name:<28}")
    print("-" * 92)
    print(f"{'Monthly EMI':<34} INR {report.plan_a_report.monthly_emi:<24,.2f} INR {report.plan_b_report.monthly_emi:<24,.2f}")
    print(f"{'Default / Shortfall Risk':<34} {report.plan_a_report.shortfall_frequency_pct}%{'':<22} {report.plan_b_report.shortfall_frequency_pct}%")
    print(f"{'Adverse 5th-Percentile Cash':<34} INR {report.plan_a_report.residual_cash_p05:<24,.2f} INR {report.plan_b_report.residual_cash_p05:<24,.2f}")
    print(f"{'Income Shock Tolerance':<34} {report.plan_a_report.shock_tolerance_pct}%{'':<22} {report.plan_b_report.shock_tolerance_pct}%")
    print(f"{'Affordability Break Income':<34} INR {report.plan_a_report.affordability_break_income:<24,.2f} INR {report.plan_b_report.affordability_break_income:<24,.2f}")
    print(f"{'Stress Resilience Rating':<34} [{report.plan_a_report.stress_rating}]{'':<20} [{report.plan_b_report.stress_rating}]")
    print("=======================================================================")


def cmd_simulate_attack(args: argparse.Namespace) -> None:
    """Run Web-of-Trust attack simulator to demonstrate protocol safeguards."""
    from veritrust.attack_simulator import TrustGraphAttackSimulator

    engine, _, _, _, _ = _init_context()
    simulator = TrustGraphAttackSimulator(engine)
    attack_type = getattr(args, "attack", "all").lower()

    attacks_to_run = []
    if attack_type in ("sybil", "all"):
        attacks_to_run.append(simulator.simulate_sybil_clique())
    if attack_type in ("collusion", "all"):
        attacks_to_run.append(simulator.simulate_dense_collusion_ring())
    if attack_type in ("dilution", "all"):
        attacks_to_run.append(simulator.simulate_compromised_sponsor_dilution())
    if attack_type in ("burst", "all"):
        attacks_to_run.append(simulator.simulate_endorsement_burst_anomaly())

    print("=======================================================================")
    print(" VeriTrust Web-of-Trust Attack Simulator & Security Safeguards")
    print("=======================================================================")
    for res in attacks_to_run:
        print(f"\n[ATTACK VECTOR]: {res.attack_name}")
        print(f"  + Target Node:            {res.target_node_id}")
        print(f"  + Baseline Trust Score:   {res.baseline_trust_score}")
        print(f"  + Attack-Induced Trust:   {res.attack_induced_trust_score}")
        print(f"  + Trust Leakage Delta:    {res.trust_leakage_delta}")
        print(f"  + Security Verdict:       [{res.security_verdict}]")
        print("  + Active Protocol Safeguards:")
        for sg in res.safeguards_triggered:
            print(f"      - {sg}")
        print("  + Forensic Diagnostic Notes:")
        for note in res.mitigation_notes:
            print(f"      * {note}")
    print("\n=======================================================================")


def cmd_audit_decision(args: argparse.Namespace) -> None:
    """Inspect complete forensic audit trail of a credit decision."""
    from veritrust.audit_explorer import DecisionAuditExplorer

    engine, scorer, _, store, current_user = _init_context()
    borrower_id = args.borrower or current_user
    if not borrower_id:
        print("Error: Specify a user ID with --borrower <id> or log in with 'login <id>'.")
        sys.exit(1)

    amount = Decimal(str(args.amount))
    tenure = int(args.tenure or 6)

    explorer = DecisionAuditExplorer(engine, scorer)
    report = explorer.inspect_decision(borrower_id, amount, tenure)

    print("=======================================================================")
    print(f" VeriTrust Decision Explanation & Forensic Audit Explorer")
    print(f" Audit ID: {report.audit_id} | Borrower: {report.borrower_id} ({report.borrower_name})")
    print(f" Final Verdict: [{report.verdict}]")
    print("=======================================================================")
    print("\n[1. EXPLICIT RULE EVALUATION TRACE]")
    print(f"{'Rule ID':<30} {'Observed Value':<24} {'Threshold':<24} {'Result'}")
    print("-" * 88)
    for r in report.rules_evaluated:
        res_str = "[PASS]" if r.passed else "[FAIL]"
        print(f"{r.rule_id:<30} {r.observed_value:<24} {r.policy_threshold:<24} {res_str}")
        print(f"   +-- {r.diagnostic_detail}")

    print("\n[2. CONTRIBUTING PRIMARY EVIDENCE]")
    if report.contributing_evidence:
        for ev in report.contributing_evidence:
            print(f"  + [{ev.evidence_type}] ID: {ev.evidence_id} | Desc: {ev.description} (Recorded by: {ev.recorded_by})")
    else:
        print("  + Standalone self-disclosed financial assessment (no external evidence linked).")

    print("\n[3. WEB-OF-TRUST CONTRIBUTING PATHS]")
    print(f"  + Aggregate Graph Trust R_graph: {report.graph_trust_score}")
    for p in report.contributing_paths:
        print(f"  + Path: {' -> '.join(p.path)} (Weight: {p.path_trust:,.4f})")

    print("\n[4. DETERMINISTIC SENSITIVITY DELTAS (WHAT-IF EXPLORATION)]")
    for s in report.sensitivity_analysis:
        print(f"  * {s.parameter_perturbed}:")
        print(f"      {s.perturbation_description}")
        print(f"      New Max Affordable EMI: INR {s.new_max_affordable_emi:,.2f} | Impact: {s.impact_summary}")
    print("=======================================================================")


def cmd_recourse(args: argparse.Namespace) -> None:
    """Borrower recourse, dispute filing, and evidence-quality workflow."""
    from veritrust.recourse import BorrowerRecourseWorkflow
    from veritrust.models import Evidence

    engine, scorer, lending, store, current_user = _init_context()
    workflow = BorrowerRecourseWorkflow(engine, scorer)

    action = getattr(args, "recourse_action", "audit")
    if action == "file":
        borrower_id = args.borrower or current_user
        if not borrower_id:
            print("Error: Specify borrower with --borrower <id> or log in.")
            sys.exit(1)
        evidence = Evidence(
            evidence_id=f"EVID_DISP_{args.record_id}",
            evidence_type="BANK_STATEMENT",
            description=f"Borrower submitted document: {args.reason}",
            recorded_by=borrower_id,
        )
        dispute = workflow.file_dispute(
            borrower_id=borrower_id,
            target_record_id=args.record_id,
            target_record_type=args.type or "TRANSACTION",
            contestation_reason=args.reason,
            supporting_evidence=evidence,
        )
        print(f"Dispute Filed Successfully!")
        print(f"  + Dispute ID:      {dispute.dispute_id}")
        print(f"  + Target Record:   {dispute.target_record_id} ({dispute.target_record_type})")
        print(f"  + Contestation:    {dispute.contestation_reason}")
        print(f"  + Status:          [{dispute.status}] (Logged to immutable reputation ledger)")

    elif action == "resolve":
        dispute_id = args.dispute_id
        decision = args.decision.upper()  # UPHELD or REJECTED
        income = Decimal(str(args.income)) if getattr(args, "income", None) else None
        debt = Decimal(str(args.debt)) if getattr(args, "debt", None) else None

        from veritrust.recourse import DisputeCase
        if dispute_id not in workflow.disputes:
            workflow.disputes[dispute_id] = DisputeCase(
                dispute_id=dispute_id,
                borrower_id=args.borrower or current_user or "LAKSHMI",
                target_record_id="REC_001",
                target_record_type="INCOME_STATEMENT",
                contestation_reason="Income under-reported due to processing lag",
                supporting_evidence=Evidence(evidence_id="EVID_01", evidence_type="BANK_STATEMENT", description="Contested evidence document", recorded_by="USER"),
                status="OPEN",
            )

        resolved = workflow.resolve_dispute(
            dispute_id=dispute_id,
            action=decision,  # type: ignore
            resolution_notes=args.notes or "Evidence verified and validated by underwriter",
            resolving_officer=current_user or "SYSTEM_AUDITOR",
            corrected_monthly_income=income,
            corrected_monthly_debt=debt,
        )
        store.save(engine, lending)
        print(f"Dispute Resolved!")
        print(f"  + Dispute ID:      {resolved.dispute_id}")
        print(f"  + Status:          [{resolved.status}]")
        print(f"  + Resolving Officer: {resolved.resolving_officer}")
        if resolved.recalculation_impact:
            print("  + Score Recalculation Impact:")
            for k, v in resolved.recalculation_impact.items():
                print(f"      - {k}: {v}")

    elif action == "audit":
        borrower_id = args.borrower or current_user
        if not borrower_id:
            print("Error: Specify borrower with --borrower <id> or log in.")
            sys.exit(1)
        audit = workflow.audit_evidence_quality(borrower_id)
        print("=======================================================================")
        print(f" VeriTrust Evidence-Quality & Fair Credit Audit")
        print(f" Borrower: {audit.borrower_id} | Data Integrity Grade: [{audit.data_quality_grade}]")
        print("=======================================================================")
        print(f"  + Total Records Tracked:   {audit.total_records_tracked}")
        print(f"  + Verified Records:        {audit.verified_records_count}")
        print(f"  + Missing Records:         {audit.missing_records_count}")
        print(f"  + Stale Records (>90d):    {audit.stale_records_count}")
        print(f"  + Duplicated Records:      {audit.duplicated_records_count}")
        print(f"  + Active Contested Items:  {audit.disputed_records_count}")
        print("\n[FAIR CREDIT RECOURSE NOTES]")
        for note in audit.fair_credit_compliance_notes:
            print(f"  => {note}")
        print("=======================================================================")


# -----------------------------------------------------------------------------
# Interactive REPL Shell
# -----------------------------------------------------------------------------

def run_interactive_shell() -> None:
    """Run interactive REPL inspired by standard interactive command line tools."""
    print("=======================================================================")
    print(" VeriTrust Interactive CLI -- Web-of-Trust Credit & Lending Engine")
    print(" Type 'help' for available commands, or 'exit' / 'quit' to leave.")
    print("=======================================================================\n")

    parser = build_parser()

    while True:
        try:
            _, _, _, store, current_user = _init_context()
            prompt = f"veritrust ({current_user})> " if current_user else "veritrust> "
            cmd_line = input(prompt).strip()
            if not cmd_line:
                continue

            if cmd_line.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            if cmd_line.lower() in ("help", "?"):
                parser.print_help()
                continue

            # Tokenize input line respecting quotes
            import shlex
            args = shlex.split(cmd_line)
            try:
                parsed_args = parser.parse_args(args)
                parsed_args.func(parsed_args)
            except SystemExit:
                pass
            print()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


# -----------------------------------------------------------------------------
# Parser Definition
# -----------------------------------------------------------------------------

def cmd_serve(args: argparse.Namespace) -> None:
    """Start FastAPI Uvicorn REST API server."""
    import uvicorn
    host = getattr(args, "host", "0.0.0.0")
    port = getattr(args, "port", 8000)
    print(f"Starting Vouch / VeriTrust REST API server on http://{host}:{port} ...")
    uvicorn.run("veritrust.api.app:app", host=host, port=port, reload=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="veritrust",
        description="VeriTrust -- Standalone Web-of-Trust Credit & Lending CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # user create
    p_user_create = subparsers.add_parser("user-create", help="Register a new user node")
    p_user_create.add_argument("user_id", help="Unique identifier (e.g. U001)")
    p_user_create.add_argument("name", nargs="?", default="", help="Display name")
    p_user_create.add_argument("--reputation", "-r", default="0.0", help="Initial reputation score")
    p_user_create.add_argument("--anchor", action="store_true", help="Mark as institutional anchor")
    p_user_create.add_argument("--income", type=str, help="Monthly gross income in INR")
    p_user_create.add_argument("--debt", type=str, help="Monthly recurring debt in INR")
    p_user_create.add_argument("--noi", type=str, help="Net operating income in INR")
    p_user_create.add_argument("--debt-service", type=str, help="Debt service in INR")
    p_user_create.add_argument("--completeness", type=str, default="1.0", help="Data completeness fraction (0.0 - 1.0)")
    p_user_create.set_defaults(func=cmd_user_create)

    # user list
    p_user_list = subparsers.add_parser("users", help="List all registered nodes")
    p_user_list.set_defaults(func=cmd_user_list)

    # login / whoami / logout
    p_login = subparsers.add_parser("login", help="Set active user session")
    p_login.add_argument("user_id", help="User ID to log in as")
    p_login.set_defaults(func=cmd_login)

    p_whoami = subparsers.add_parser("whoami", help="Display details of current active session")
    p_whoami.set_defaults(func=cmd_whoami)

    p_logout = subparsers.add_parser("logout", help="Clear active session")
    p_logout.set_defaults(func=cmd_logout)

    # vouch / unvouch
    p_vouch = subparsers.add_parser("vouch", help="Endorse a borrower (dilutes siblings automatically)")
    p_vouch.add_argument("target", help="Borrower user ID to vouch for")
    p_vouch.add_argument("--source", "-s", help="Source endorser (defaults to logged-in user)")
    p_vouch.set_defaults(func=cmd_vouch)

    p_unvouch = subparsers.add_parser("unvouch", help="Remove an endorsement")
    p_unvouch.add_argument("target", help="Borrower user ID to unvouch")
    p_unvouch.add_argument("--source", "-s", help="Source endorser (defaults to logged-in user)")
    p_unvouch.set_defaults(func=cmd_unvouch)

    # assess
    p_assess = subparsers.add_parser("assess", help="Evaluate creditworthiness and eligible limit")
    p_assess.add_argument("user_id", nargs="?", help="User ID to assess (defaults to logged-in user)")
    p_assess.set_defaults(func=cmd_assess)

    # borrow / repay / lend / default
    p_borrow = subparsers.add_parser("borrow", help="Borrow money within approved credit limit")
    p_borrow.add_argument("amount", type=str, help="Principal amount in INR")
    p_borrow.add_argument("--borrower", "-b", help="Borrower ID (defaults to logged-in user)")
    p_borrow.add_argument("--tenure", "-t", type=int, default=6, help="Tenure in months (default: 6)")
    p_borrow.set_defaults(func=cmd_borrow)

    p_repay = subparsers.add_parser("repay", help="Repay an active loan")
    p_repay.add_argument("loan_id", help="Loan ID to repay")
    p_repay.add_argument("amount", type=str, help="Repayment amount in INR")
    p_repay.set_defaults(func=cmd_repay)

    p_lend = subparsers.add_parser("lend", help="Directly lend / fund a borrower")
    p_lend.add_argument("borrower", help="Borrower user ID")
    p_lend.add_argument("amount", type=str, help="Principal amount in INR")
    p_lend.add_argument("--lender", "-l", help="Lender user ID (defaults to logged-in user)")
    p_lend.add_argument("--tenure", "-t", type=int, default=6, help="Tenure in months (default: 6)")
    p_lend.set_defaults(func=cmd_lend)

    p_default = subparsers.add_parser("default", help="Default a loan and trigger 4-level slashing cascade")
    p_default.add_argument("loan_id", help="Loan ID to mark defaulted")
    p_default.add_argument("--slash", "-s", type=str, help="Base slash delta0 (defaults to config)")
    p_default.set_defaults(func=cmd_default)

    # check (mitchellh/vouch inspired)
    p_check = subparsers.add_parser("check", help="Check user vouch status, trust score, and credit limit")
    p_check.add_argument("user_id", help="User ID to check")
    p_check.set_defaults(func=cmd_check)

    # denounce (mitchellh/vouch inspired)
    p_denounce = subparsers.add_parser("denounce", help="Denounce bad actor and trigger cascade penalty")
    p_denounce.add_argument("user_id", help="User ID to denounce")
    p_denounce.add_argument("--reason", "-r", help="Reason for denouncement")
    p_denounce.set_defaults(func=cmd_denounce)

    # signup alias
    p_signup = subparsers.add_parser("signup", help="Register a new user (alias for user-create)")
    p_signup.add_argument("user_id", help="Unique identifier (e.g. U001)")
    p_signup.add_argument("name", nargs="?", default="", help="Display name")
    p_signup.add_argument("--reputation", "-r", default="0.0", help="Initial reputation score")
    p_signup.set_defaults(func=cmd_user_create)

    # loans
    p_loans = subparsers.add_parser("loans", help="List loan contracts")
    p_loans.add_argument("user_id", nargs="?", help="Filter by borrower user ID")
    p_loans.add_argument("--mine", "-m", action="store_true", help="Filter for current logged-in user")
    p_loans.set_defaults(func=cmd_loans)

    # graph
    p_graph = subparsers.add_parser("graph", help="Visualize trust network topology and weights")
    p_graph.set_defaults(func=cmd_graph)

    # history (reputation ledger)
    p_history = subparsers.add_parser("history", help="View append-only reputation ledger events and evidence")
    p_history.add_argument("user_id", nargs="?", help="Filter events for specific user ID")
    p_history.add_argument("--mine", "-m", action="store_true", help="Filter for current logged-in user")
    p_history.set_defaults(func=cmd_history)

    # audit (tamper-detection hash chain audit)
    p_audit = subparsers.add_parser("audit", help="Verify cryptographic hash chain integrity of the ledger")
    p_audit.set_defaults(func=cmd_audit)

    # replay (disaster recovery / deterministic replay)
    p_replay = subparsers.add_parser("replay", help="Reconstruct protocol state from raw immutable events")
    p_replay.add_argument("--restore", "-r", action="store_true", help="Synchronize store.json with reconstructed state")
    p_replay.set_defaults(func=cmd_replay)

    # optimize (affordability + OR-Tools + stress test + explanation)
    p_opt = subparsers.add_parser("optimize", help="Optimize loan plan under affordability, OR-Tools, and stress testing")
    p_opt.add_argument("amount", type=str, help="Requested loan principal in INR")
    p_opt.add_argument("--tenure", "-t", type=int, default=6, help="Requested tenure in months (default: 6)")
    p_opt.add_argument("--borrower", "-b", help="Borrower user ID (defaults to active user)")
    p_opt.add_argument("--income", type=str, help="Override monthly gross income in INR")
    p_opt.add_argument("--expenses", type=str, help="Override monthly essential expenses in INR")
    p_opt.add_argument("--debt", type=str, help="Override existing monthly debt service in INR")
    p_opt.add_argument("--objective", choices=["MIN_COST", "MAX_PRINCIPAL"], default="MIN_COST", help="Optimization objective (default: MIN_COST)")
    p_opt.add_argument("--verified", action="store_true", help="Flag documentation as verified by bank/DigiLocker statement")
    p_opt.set_defaults(func=cmd_optimize)

    # counterfactual (what-if parameter sweeps, remedies & side-by-side comparison)
    p_cf = subparsers.add_parser("counterfactual", help="Deterministic counterfactual what-if loan simulator")
    p_cf.add_argument("amount", type=str, help="Requested loan principal in INR")
    p_cf.add_argument("--tenure", "-t", type=int, default=6, help="Requested tenure in months (default: 6)")
    p_cf.add_argument("--borrower", "-b", help="Borrower user ID (defaults to active user)")
    p_cf.add_argument("--income", type=str, help="Monthly gross income in INR")
    p_cf.add_argument("--expenses", type=str, help="Monthly essential expenditures in INR")
    p_cf.add_argument("--debt", type=str, help="Existing monthly debt service in INR")
    p_cf.set_defaults(func=cmd_counterfactual)

    # stress-compare (side-by-side comparative stress dashboard)
    p_sc = subparsers.add_parser("stress-compare", help="Compare two loan plans side-by-side under identical Monte Carlo futures")
    p_sc.add_argument("--principal-a", "-pa", type=str, required=True, help="Plan A principal in INR")
    p_sc.add_argument("--tenure-a", "-ta", type=int, default=6, help="Plan A tenure in months (default: 6)")
    p_sc.add_argument("--principal-b", "-pb", type=str, required=True, help="Plan B principal in INR")
    p_sc.add_argument("--tenure-b", "-tb", type=int, default=12, help="Plan B tenure in months (default: 12)")
    p_sc.add_argument("--income", type=str, default="35000.00", help="Monthly gross income in INR")
    p_sc.add_argument("--expenses", type=str, default="18000.00", help="Monthly non-discretionary expenses in INR")
    p_sc.set_defaults(func=cmd_stress_compare)

    # simulate-attack (adversarial security testing)
    p_att = subparsers.add_parser("simulate-attack", help="Simulate adversarial graph attacks (sybil, collusion, dilution, burst)")
    p_att.add_argument("--attack", "-a", choices=["sybil", "collusion", "dilution", "burst", "all"], default="all", help="Attack vector to simulate")
    p_att.set_defaults(func=cmd_simulate_attack)

    # audit-decision (forensic decision explorer)
    p_aud = subparsers.add_parser("audit-decision", help="Forensic decision explanation and rule audit explorer")
    p_aud.add_argument("amount", type=str, help="Requested loan principal in INR")
    p_aud.add_argument("--tenure", "-t", type=int, default=6, help="Requested tenure in months (default: 6)")
    p_aud.add_argument("--borrower", "-b", help="Borrower user ID (defaults to active user)")
    p_aud.set_defaults(func=cmd_audit_decision)

    # recourse (borrower dispute & evidence quality workflow)
    p_rec = subparsers.add_parser("recourse", help="Borrower dispute contestation and evidence-quality workflow")
    p_rec.add_argument("recourse_action", choices=["file", "resolve", "audit"], help="Recourse action to execute")
    p_rec.add_argument("--record-id", help="Target record ID being contested")
    p_rec.add_argument("--type", help="Record type (TRANSACTION, DEFAULT_NOTICE, INCOME_STATEMENT)")
    p_rec.add_argument("--reason", default="Contested factual error", help="Reason for contestation")
    p_rec.add_argument("--borrower", "-b", help="Borrower user ID")
    p_rec.add_argument("--dispute-id", help="Dispute ID (for resolve)")
    p_rec.add_argument("--decision", choices=["UPHELD", "REJECTED"], default="UPHELD", help="Resolution decision")
    p_rec.add_argument("--notes", help="Resolution audit notes")
    p_rec.add_argument("--income", type=str, help="Corrected monthly income")
    p_rec.add_argument("--debt", type=str, help="Corrected monthly debt")
    p_rec.set_defaults(func=cmd_recourse)

    # serve
    p_serve = subparsers.add_parser("serve", help="Start FastAPI REST API server")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    p_serve.set_defaults(func=cmd_serve)

    # reset
    p_reset = subparsers.add_parser("reset", help="Reset state to initial seed demo data")
    p_reset.set_defaults(func=cmd_reset)

    # interactive
    p_interactive = subparsers.add_parser("interactive", help="Start interactive REPL prompt")
    p_interactive.set_defaults(func=lambda args: run_interactive_shell())

    return parser


def main() -> None:
    # If invoked without arguments or with -i / interactive, enter interactive shell
    if len(sys.argv) <= 1 or sys.argv[1] in ("-i", "--interactive", "interactive"):
        run_interactive_shell()
        return

    parser = build_parser()
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
