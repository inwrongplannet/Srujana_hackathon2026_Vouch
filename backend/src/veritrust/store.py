"""Flat-file persistence store for the VeriTrust engine.

Stores graph participants, endorsements, loans, transaction ledgers,
and active user sessions in human-readable JSON. Inspired by mitchellh/vouch
transparent flat-file model.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
from typing import Optional

from veritrust.engine import TrustEngine
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures, Loan, Transaction, User, Vouch
from veritrust.scoring import CreditScorer


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder supporting Decimal and datetime objects."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class StateStore:
    """Manages reading and writing engine state to disk."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        if data_dir is None:
            # Default to backend/data directory
            data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store_file = self.data_dir / "store.json"
        self.session_file = self.data_dir / "session.json"

    def get_current_user(self) -> Optional[str]:
        """Return currently logged-in user ID, if any."""
        if not self.session_file.is_file():
            return None
        try:
            data = json.loads(self.session_file.read_text(encoding="utf-8"))
            return data.get("current_user_id")
        except Exception:
            return None

    def set_current_user(self, user_id: Optional[str]) -> None:
        """Set or clear active user session."""
        payload = {"current_user_id": user_id}
        self.session_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save(self, engine: TrustEngine, lending: LendingService) -> None:
        """Serialize complete engine and lending state to store.json."""
        users_data = [user.model_dump(mode="json") for user in engine.list_users()]
        vouches_data = [vouch.model_dump(mode="json") for vouch in engine.vouches.values()]
        loans_data = [loan.model_dump(mode="json") for loan in lending.list_loans()]
        txs_data = [tx.model_dump(mode="json") for tx in lending.list_transactions()]

        payload = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "users": users_data,
            "vouches": vouches_data,
            "loans": loans_data,
            "transactions": txs_data,
        }
        self.store_file.write_text(json.dumps(payload, cls=DecimalEncoder, indent=2), encoding="utf-8")

    def load(self, engine: TrustEngine, lending: LendingService) -> bool:
        """Load state from store.json into engine and lending service.

        Returns True if loaded, False if file did not exist (seeded default).
        """
        if not self.store_file.is_file():
            self.seed_defaults(engine, lending)
            self.save(engine, lending)
            return False

        try:
            raw = json.loads(self.store_file.read_text(encoding="utf-8"))

            # Load users
            for u_data in raw.get("users", []):
                ff = None
                if u_data.get("financial_features"):
                    ff = FinancialFeatures(**u_data["financial_features"])
                user = User(
                    user_id=u_data["user_id"],
                    name=u_data["name"],
                    reputation=Decimal(str(u_data.get("reputation", "0.0"))),
                    capacity=Decimal(str(u_data.get("capacity", "0.0"))),
                    status=u_data.get("status", "ACTIVE"),
                    is_anchor=u_data.get("is_anchor", False),
                    financial_features=ff,
                    n_settled_loans=u_data.get("n_settled_loans", 0),
                )
                engine.users[user.user_id] = user
                engine._sync_node_to_graph(user)

            # Load vouches
            for v_data in raw.get("vouches", []):
                vouch = Vouch(
                    vouch_id=v_data["vouch_id"],
                    source=v_data["source"],
                    target=v_data["target"],
                    weight=Decimal(str(v_data.get("weight", "0.0"))),
                    active=v_data.get("active", True),
                )
                key = f"{vouch.source}_{vouch.target}"
                engine.vouches[key] = vouch
                if vouch.active:
                    engine.graph.add_edge(vouch.source, vouch.target, weight=vouch.weight)

            # Recompute weights to ensure conservation
            for user_id in engine.users:
                engine.recompute_weights(user_id)

            # Load loans
            for l_data in raw.get("loans", []):
                loan = Loan(
                    loan_id=l_data["loan_id"],
                    borrower_id=l_data["borrower_id"],
                    principal=Decimal(str(l_data["principal"])),
                    outstanding_balance=Decimal(str(l_data["outstanding_balance"])),
                    interest_rate=Decimal(str(l_data.get("interest_rate", "0.10"))),
                    tenure_months=l_data.get("tenure_months", 6),
                    status=l_data.get("status", "ACTIVE"),
                )
                lending.loans[loan.loan_id] = loan

            # Load transactions
            for t_data in raw.get("transactions", []):
                tx = Transaction(
                    tx_id=t_data["tx_id"],
                    user_id=t_data["user_id"],
                    amount=Decimal(str(t_data["amount"])),
                    currency=t_data.get("currency", "INR"),
                    tx_type=t_data["tx_type"],
                )
                lending.transactions.append(tx)

            # If ledger exists and is empty, bootstrap genesis events for audit continuity
            if getattr(engine, "ledger", None) is not None and engine.ledger.count() == 0:
                from veritrust.models import Evidence
                for u in engine.list_users():
                    engine.ledger.append_event(
                        event_type="USER_REGISTERED",
                        actor_id="GENESIS_ANCHOR" if u.is_anchor else u.user_id,
                        subject_id=u.user_id,
                        delta_reputation=u.reputation,
                        payload={
                            "name": u.name,
                            "is_anchor": u.is_anchor,
                            "financial_features": u.financial_features.model_dump(mode="json") if u.financial_features else None,
                        },
                        evidence=Evidence(
                            evidence_id=f"EVID_GENESIS_{u.user_id}",
                            evidence_type="IDENTITY_ANCHOR" if u.is_anchor else "COMMUNITY_VOUCH",
                            description=f"Genesis bootstrapping of node {u.user_id}",
                            recorded_by="SYSTEM_BOOTSTRAP",
                        ),
                    )
                for v in engine.vouches.values():
                    if v.active:
                        engine.ledger.append_event(
                            event_type="VOUCH_CREATED",
                            actor_id=v.source,
                            subject_id=v.target,
                            payload={"assigned_weight": str(v.weight)},
                            evidence=Evidence(
                                evidence_id=f"EVID_GENESIS_VOUCH_{v.source}_{v.target}",
                                evidence_type="COMMUNITY_VOUCH",
                                description=f"Genesis endorsement from {v.source} to {v.target}",
                                recorded_by="SYSTEM_BOOTSTRAP",
                            ),
                        )
                for l in lending.list_loans():
                    engine.ledger.append_event(
                        event_type="LOAN_DISBURSED",
                        actor_id=l.lender_id or l.borrower_id,
                        subject_id=l.borrower_id,
                        payload={"loan_id": l.loan_id, "principal": str(l.principal), "tenure_months": l.tenure_months},
                        evidence=Evidence(
                            evidence_id=f"EVID_GENESIS_LOAN_{l.loan_id}",
                            evidence_type="SETTLEMENT_RECEIPT",
                            description=f"Genesis loan contract {l.loan_id}",
                            recorded_by="SYSTEM_BOOTSTRAP",
                        ),
                    )

            return True
        except Exception:
            self.seed_defaults(engine, lending)
            self.save(engine, lending)
            return False

    def seed_defaults(self, engine: TrustEngine, lending: LendingService) -> None:
        """Seed initial demo graph network."""
        anchor = engine.create_user(
            user_id="ANCHOR_BANK",
            name="Microfinance Institutional Anchor",
            initial_reputation=Decimal("20.0"),
            is_anchor=True,
        )
        alice = engine.create_user(
            user_id="ALICE",
            name="Alice (Community Leader)",
            initial_reputation=Decimal("10.0"),
        )
        bob = engine.create_user(
            user_id="BOB",
            name="Bob (Micro-Business Owner)",
            initial_reputation=Decimal("0.0"),
            financial_features=FinancialFeatures(
                monthly_income=Decimal("35000.00"),
                monthly_debt=Decimal("6000.00"),
                net_operating_income=Decimal("22000.00"),
                debt_service=Decimal("5000.00"),
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

        engine.vouch("ANCHOR_BANK", "ALICE")
        engine.vouch("ALICE", "BOB")
