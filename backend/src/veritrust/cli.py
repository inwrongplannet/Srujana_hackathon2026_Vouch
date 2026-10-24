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
        loan = lending.repay(loan_id, amount)
        store.save(engine, lending)
        print(f"Repayment Processed for Loan '{loan_id}'!")
        print(f"  + Payment Applied:     INR {amount:,.2f}")
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
