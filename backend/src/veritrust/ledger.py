"""Append-Only Reputation & Evidence Ledger for VeriTrust.

Every meaningful trust and credit state change becomes an immutable,
cryptographically chained event with verifiable evidence and reason.
Acts as the authoritative, tamper-evident source of truth for the protocol.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
from typing import Optional

from veritrust.models import Evidence, LedgerEvent


GENESIS_HASH = "0" * 64


class DuplicateEventError(ValueError):
    """Raised when an event with the same ID is processed more than once."""
    pass


class LedgerIntegrityError(Exception):
    """Raised when the hash chain verification detects tampering or corruption."""
    pass


class ReputationLedger:
    """ACID-compliant SQLite append-only event store with hash-chain auditability."""

    def __init__(self, db_path: Optional[Path] = None, jsonl_path: Optional[Path] = None) -> None:
        if db_path is None:
            data_dir = Path(__file__).resolve().parent.parent.parent / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = data_dir / "ledger.db"
            jsonl_path = data_dir / "events.jsonl"

        self.db_path = db_path
        self.jsonl_path = jsonl_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create ledger tables and indices if not already present."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ledger_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    actor_id TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    delta_reputation TEXT NOT NULL,
                    evidence_json TEXT,
                    payload_json TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_subject ON ledger_events(subject_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON ledger_events(event_type);")

    def get_latest_event(self) -> Optional[LedgerEvent]:
        """Fetch the most recent event at the head of the hash chain."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ledger_events ORDER BY sequence DESC LIMIT 1;")
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_event(row)

    def append_event(
        self,
        event_type: str,
        actor_id: str,
        subject_id: str,
        delta_reputation: Decimal = Decimal("0.0"),
        payload: Optional[dict] = None,
        evidence: Optional[Evidence] = None,
        event_id: Optional[str] = None,
    ) -> LedgerEvent:
        """Atomically append a new event to the ledger, computing cryptographic hash chain."""
        if payload is None:
            payload = {}

        now_utc = datetime.now(timezone.utc)
        if event_id is None:
            import uuid
            event_id = f"EVT_{now_utc.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        with self._get_connection() as conn:
            # Check for duplicate event_id to guarantee idempotency
            cur = conn.cursor()
            cur.execute("SELECT sequence FROM ledger_events WHERE event_id = ?;", (event_id,))
            if cur.fetchone() is not None:
                raise DuplicateEventError(f"Idempotency violation: Event '{event_id}' has already been processed.")

            # Get current head hash and sequence
            cur.execute("SELECT sequence, event_hash FROM ledger_events ORDER BY sequence DESC LIMIT 1;")
            last_row = cur.fetchone()
            if last_row:
                prev_hash = last_row["event_hash"]
                next_seq = last_row["sequence"] + 1
            else:
                prev_hash = GENESIS_HASH
                next_seq = 1

            # Build preliminary event
            event = LedgerEvent(
                event_id=event_id,
                sequence=next_seq,
                event_type=event_type,  # type: ignore
                actor_id=actor_id,
                subject_id=subject_id,
                timestamp=now_utc,
                delta_reputation=delta_reputation,
                evidence=evidence,
                payload=payload,
                prev_hash=prev_hash,
                event_hash="",
            )
            # Calculate cryptographic hash
            event.event_hash = event.compute_hash()

            # Insert into SQLite
            evidence_json = event.evidence.model_dump_json() if event.evidence else None
            payload_json = json.dumps(event.payload, sort_keys=True, default=str)
            conn.execute(
                """
                INSERT INTO ledger_events (
                    sequence, event_id, event_type, actor_id, subject_id,
                    timestamp, delta_reputation, evidence_json, payload_json,
                    prev_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event.sequence,
                    event.event_id,
                    event.event_type,
                    event.actor_id,
                    event.subject_id,
                    event.timestamp.isoformat(),
                    str(event.delta_reputation),
                    evidence_json,
                    payload_json,
                    event.prev_hash,
                    event.event_hash,
                ),
            )

        # Mirror append to JSONL for transparent text auditability
        if self.jsonl_path:
            try:
                with open(self.jsonl_path, "a", encoding="utf-8") as f:
                    f.write(event.model_dump_json() + "\n")
            except Exception:
                pass

        return event

    def get_history(self, subject_id: str) -> list[LedgerEvent]:
        """Fetch chronological history of all reputation events affecting subject_id."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM ledger_events WHERE subject_id = ? ORDER BY sequence ASC;",
                (subject_id,),
            )
            return [self._row_to_event(row) for row in cur.fetchall()]

    def list_all_events(self) -> list[LedgerEvent]:
        """Fetch all events ordered sequentially."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ledger_events ORDER BY sequence ASC;")
            return [self._row_to_event(row) for row in cur.fetchall()]

    def count(self) -> int:
        """Return total count of recorded events."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM ledger_events;")
            row = cur.fetchone()
            return row["cnt"] if row else 0

    def verify_integrity(self) -> tuple[bool, Optional[str]]:
        """Verify complete cryptographic hash chain from Genesis to Head.

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str]).
        """
        events = self.list_all_events()
        if not events:
            return True, None

        expected_prev_hash = GENESIS_HASH
        for event in events:
            # 1. Verify link to previous event
            if event.prev_hash != expected_prev_hash:
                return (
                    False,
                    f"Chain break at sequence {event.sequence} (Event ID: {event.event_id}): "
                    f"prev_hash '{event.prev_hash}' does not match expected '{expected_prev_hash}'.",
                )

            # 2. Verify event payload hash integrity
            calculated_hash = event.compute_hash()
            if event.event_hash != calculated_hash:
                return (
                    False,
                    f"Tamper detected at sequence {event.sequence} (Event ID: {event.event_id}): "
                    f"recorded hash '{event.event_hash}' does not match recomputed '{calculated_hash}'.",
                )

            expected_prev_hash = event.event_hash

        return True, None

    def _row_to_event(self, row: sqlite3.Row) -> LedgerEvent:
        evidence = None
        if row["evidence_json"]:
            evidence = Evidence(**json.loads(row["evidence_json"]))

        payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
        ts = datetime.fromisoformat(row["timestamp"])
        return LedgerEvent(
            event_id=row["event_id"],
            sequence=row["sequence"],
            event_type=row["event_type"],
            actor_id=row["actor_id"],
            subject_id=row["subject_id"],
            timestamp=ts,
            delta_reputation=Decimal(row["delta_reputation"]),
            evidence=evidence,
            payload=payload,
            prev_hash=row["prev_hash"],
            event_hash=row["event_hash"],
        )

    def reconstruct_state(self) -> tuple[object, object]:
        """Deterministically replay all events to reconstruct protocol state.

        Returns:
            Tuple of (reconstructed_engine: TrustEngine, reconstructed_lending: LendingService).

        Raises:
            LedgerIntegrityError: If cryptographic hash chain verification fails.
        """
        from veritrust.engine import TrustEngine
        from veritrust.scoring import CreditScorer
        from veritrust.lending import LendingService
        from veritrust.models import FinancialFeatures, Loan, Transaction

        is_valid, err = self.verify_integrity()
        if not is_valid:
            raise LedgerIntegrityError(f"Cannot replay corrupted ledger: {err}")

        # Engine with no ledger to prevent event duplication during replay
        replayed_engine = TrustEngine(ledger=None)
        replayed_scorer = CreditScorer(replayed_engine)
        replayed_lending = LendingService(replayed_engine, replayed_scorer)

        events = self.list_all_events()
        for evt in events:
            if evt.event_type == "USER_REGISTERED":
                ff_dict = evt.payload.get("financial_features")
                ff = FinancialFeatures(**ff_dict) if ff_dict else None
                replayed_engine.create_user(
                    user_id=evt.subject_id,
                    name=evt.payload.get("name", evt.subject_id),
                    initial_reputation=evt.delta_reputation,
                    is_anchor=evt.payload.get("is_anchor", False),
                    financial_features=ff,
                )
            elif evt.event_type == "VOUCH_CREATED":
                replayed_engine.vouch(source_id=evt.actor_id, target_id=evt.subject_id)
            elif evt.event_type == "VOUCH_REVOKED":
                replayed_engine.unvouch(source_id=evt.actor_id, target_id=evt.subject_id)
            elif evt.event_type == "LOAN_DISBURSED":
                loan_id = evt.payload["loan_id"]
                principal = Decimal(str(evt.payload["principal"]))
                tenure = int(evt.payload.get("tenure_months", 6))
                fee = Decimal(str(evt.payload.get("fee", "0.00")))
                net_amount = Decimal(str(evt.payload.get("net_amount", principal)))
                loan = Loan(
                    loan_id=loan_id,
                    borrower_id=evt.subject_id,
                    lender_id=evt.actor_id if evt.actor_id != evt.subject_id else None,
                    principal=principal,
                    outstanding_balance=principal,
                    tenure_months=tenure,
                    status="ACTIVE",
                )
                replayed_lending.loans[loan_id] = loan
                replayed_lending.total_platform_fees += fee
                replayed_lending.transactions.append(
                    Transaction(
                        tx_id=f"TX_DISB_{loan_id}",
                        user_id=evt.subject_id,
                        amount=principal,
                        fee=fee,
                        net_amount=net_amount,
                        tx_type="DISBURSEMENT",
                    )
                )
            elif evt.event_type == "LOAN_REPAID":
                loan_id = evt.payload["loan_id"]
                payment = Decimal(str(evt.payload["payment_amount"]))
                fee = Decimal(str(evt.payload.get("fee", "0.00")))
                net_amount = Decimal(str(evt.payload.get("net_amount", payment)))
                if loan_id in replayed_lending.loans:
                    loan = replayed_lending.loans[loan_id]
                    loan.outstanding_balance -= payment
                    if loan.outstanding_balance <= Decimal("0.0"):
                        loan.outstanding_balance = Decimal("0.0")
                        loan.status = "REPAID"
                    replayed_lending.total_platform_fees += fee
                    replayed_lending.transactions.append(
                        Transaction(
                            tx_id=f"TX_RP_{loan_id}_{evt.sequence}",
                            user_id=evt.subject_id,
                            amount=payment,
                            fee=fee,
                            net_amount=net_amount,
                            tx_type="REPAYMENT",
                        )
                    )
            elif evt.event_type == "REPUTATION_MINTED":
                user = replayed_engine.get_user(evt.subject_id)
                if user:
                    user.reputation += evt.delta_reputation
                    if evt.payload.get("reason") == "borrower_loan_settled":
                        user.n_settled_loans += 1
                    user.update_capacity()
                    replayed_engine._sync_node_to_graph(user)
                    replayed_engine.recompute_weights(user.user_id)
            elif evt.event_type == "LOAN_DEFAULTED":
                loan_id = evt.payload.get("loan_id")
                if loan_id and loan_id in replayed_lending.loans:
                    replayed_lending.loans[loan_id].status = "DEFAULTED"
            elif evt.event_type == "REPUTATION_SLASHED":
                user = replayed_engine.get_user(evt.subject_id)
                if user:
                    user.reputation += evt.delta_reputation
                    cascade_level = evt.payload.get("cascade_level", 0)
                    if cascade_level == 0:
                        user.status = "DEFAULTED"
                        user.capacity = Decimal("0.0")
                        for neighbor in list(replayed_engine.graph.successors(user.user_id)):
                            replayed_engine.graph[user.user_id][neighbor]["weight"] = Decimal("0.0")
                            key = f"{user.user_id}_{neighbor}"
                            if key in replayed_engine.vouches:
                                replayed_engine.vouches[key].weight = Decimal("0.0")
                    else:
                        if user.reputation < Decimal("0.0") and user.status == "ACTIVE":
                            user.status = "RESTRICTED"
                        user.update_capacity()
                        replayed_engine.recompute_weights(user.user_id)
                    replayed_engine._sync_node_to_graph(user)

        return replayed_engine, replayed_lending
