"""Graph and Trust Engine for VeriTrust.

Manages participant nodes (users) and directed endorsements (vouches) on a NetworkX DiGraph.
Enforces the fundamental Invariant 1: Out-Degree Capacity Conservation.
"""

from decimal import Decimal
from typing import Optional
import networkx as nx

from veritrust.models import Evidence, FinancialFeatures, User, Vouch


class TrustEngine:
    """Core Web-of-Trust graph engine maintaining participants and endorsements."""

    def __init__(self, ledger: Optional[object] = None) -> None:
        """Initialize empty graph, registries, and optional reputation ledger."""
        self.graph: nx.DiGraph = nx.DiGraph()
        self.users: dict[str, User] = {}
        self.vouches: dict[str, Vouch] = {}  # key: f"{source}_{target}"
        self.target_endorsement_counters: dict[str, int] = {}
        self.pair_transaction_counters: dict[str, int] = {}
        self.ledger = ledger

    def create_user(
        self,
        user_id: str,
        name: str,
        initial_reputation: Decimal = Decimal("0.0"),
        is_anchor: bool = False,
        financial_features: Optional[FinancialFeatures] = None,
        evidence: Optional[Evidence] = None,
        event_id: Optional[str] = None,
    ) -> User:
        """Create and register a new user node in the system.

        Args:
            user_id: Unique identifier for the user.
            name: Display name.
            initial_reputation: Starting reputation score (anchors start > 0).
            is_anchor: True if this is an institutional seed anchor.
            financial_features: Optional cash-flow metrics.
            evidence: Optional verifiable evidence backing node creation.
            event_id: Optional unique event ID for idempotency control.

        Returns:
            The created User instance.

        Raises:
            ValueError: If user_id already exists.
        """
        if user_id in self.users:
            raise ValueError(f"User with ID '{user_id}' already exists.")

        rep = Decimal(str(initial_reputation))
        ff_payload = financial_features.model_dump(mode="json") if financial_features else None

        # Record immutable event in ledger first (Source of Truth)
        if self.ledger is not None:
            self.ledger.append_event(
                event_type="USER_REGISTERED",
                actor_id=user_id if not is_anchor else "SYSTEM_ANCHOR",
                subject_id=user_id,
                delta_reputation=rep,
                payload={"name": name, "is_anchor": is_anchor, "financial_features": ff_payload},
                evidence=evidence,
                event_id=event_id,
            )

        user = User(
            user_id=user_id,
            name=name,
            reputation=rep,
            is_anchor=is_anchor,
            financial_features=financial_features,
        )
        user.update_capacity()

        self.users[user_id] = user
        self._sync_node_to_graph(user)
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Fetch user by ID."""
        return self.users.get(user_id)

    def list_users(self) -> list[User]:
        """Return all registered users."""
        return list(self.users.values())

    def _sync_node_to_graph(self, user: User) -> None:
        """Add or update node attributes in the NetworkX directed graph."""
        self.graph.add_node(
            user.user_id,
            reputation=user.reputation,
            capacity=user.capacity,
            status=user.status,
            is_anchor=user.is_anchor,
            name=user.name,
        )

    def add_user_to_graph(self, user: User) -> None:
        """Stage 2 specification: add a user node to the NetworkX graph."""
        self._sync_node_to_graph(user)

    def load_dataset(self, users: list[dict], vouches: list[dict]) -> None:
        """Stage 2 specification: bulk load nodes and edges from dataset records."""
        for u in users:
            ff = None
            if u.get("financial_features"):
                ff = FinancialFeatures(**u["financial_features"])
            self.create_user(
                user_id=u["user_id"],
                name=u.get("name", u["user_id"]),
                initial_reputation=Decimal(str(u.get("reputation", "0.0"))),
                is_anchor=u.get("is_anchor", False),
                financial_features=ff,
            )
        for v in vouches:
            self.vouch(source_id=v["source"], target_id=v["target"])
    def recompute_weights(self, source_id: str) -> None:
        """Atomically recompute all outgoing edge weights from source_id.

        Enforces Out-Degree Conservation:
            C_u = max(0, R_u)
            W_uv = C_u / |Out(u)| for each v in Out(u)
            sum(W_uv) <= C_u

        Adding or removing a vouch proportionally dilutes or concentrates
        all sibling edges.
        """
        user = self.get_user(source_id)
        if not user:
            return

        user.update_capacity()
        out_edges = list(self.graph.out_edges(source_id))
        n_out = len(out_edges)

        if n_out == 0:
            return

        capacity = user.capacity
        if capacity <= Decimal("0.0") or user.status != "ACTIVE":
            weight = Decimal("0.0")
        else:
            weight = capacity / Decimal(n_out)

        # Atomically update all sibling edges in graph and vouch registry
        for _, target_id in out_edges:
            self.graph[source_id][target_id]["weight"] = weight
            key = f"{source_id}_{target_id}"
            if key in self.vouches:
                self.vouches[key].weight = weight

    def vouch(
        self,
        source_id: str,
        target_id: str,
        evidence: Optional[Evidence] = None,
        event_id: Optional[str] = None,
    ) -> Vouch:
        """Establish a directed trust endorsement from source to target.

        Args:
            source_id: User ID of the endorser.
            target_id: User ID of the endorsed borrower.
            evidence: Optional verifiable evidence backing the endorsement.
            event_id: Optional unique event ID for idempotency control.

        Returns:
            The created Vouch record with conserved weight.

        Raises:
            ValueError: If source/target invalid, self-vouching, insufficient capacity,
                        inactive status, or duplicate vouch.
        """
        if source_id == target_id:
            raise ValueError("Nodes cannot vouch for themselves.")

        source = self.get_user(source_id)
        if not source:
            raise ValueError(f"Source user '{source_id}' does not exist.")

        target = self.get_user(target_id)
        if not target:
            raise ValueError(f"Target user '{target_id}' does not exist.")

        if source.status != "ACTIVE":
            raise ValueError(f"Source user '{source_id}' has status '{source.status}' and cannot vouch.")

        if source.capacity <= Decimal("0.0"):
            raise ValueError(
                f"Source user '{source_id}' has 0 capacity (reputation: {source.reputation}) and cannot vouch."
            )

        if self.graph.has_edge(source_id, target_id):
            raise ValueError(f"Active vouch from '{source_id}' to '{target_id}' already exists.")

        # Compute conserved weight that will be assigned
        n_out = len(list(self.graph.out_edges(source_id))) + 1
        expected_weight = source.capacity / Decimal(n_out)

        # Record immutable event in ledger first (Source of Truth)
        if self.ledger is not None:
            self.ledger.append_event(
                event_type="VOUCH_CREATED",
                actor_id=source_id,
                subject_id=target_id,
                payload={"assigned_weight": str(expected_weight)},
                evidence=evidence,
                event_id=event_id,
            )

        # Determine fixed chronological rank r_uv among endorsements received by target
        current_rank = self.target_endorsement_counters.get(target_id, 0) + 1
        self.target_endorsement_counters[target_id] = current_rank
        rank_weight = Decimal("1.0") / Decimal(2 ** (current_rank - 1))

        # Insert edge into graph and register vouch with chronological rank weight
        self.graph.add_edge(
            source_id,
            target_id,
            weight=Decimal("0.0"),
            rank=current_rank,
            alpha=rank_weight,
        )

        vouch_record = Vouch(
            vouch_id=f"V_{source_id}_{target_id}",
            source=source_id,
            target=target_id,
            weight=Decimal("0.0"),
            rank=current_rank,
            alpha=rank_weight,
            active=True,
        )
        self.vouches[f"{source_id}_{target_id}"] = vouch_record

        # Atomically reweight all siblings including this new edge
        self.recompute_weights(source_id)

        # Retrieve final conserved weight
        vouch_record.weight = self.graph[source_id][target_id]["weight"]
        return vouch_record

    def unvouch(
        self,
        source_id: str,
        target_id: str,
        evidence: Optional[Evidence] = None,
        event_id: Optional[str] = None,
    ) -> None:
        """Remove an existing endorsement and reallocate capacity among remaining siblings.

        Args:
            source_id: User ID of endorser.
            target_id: User ID of endorsed borrower.
            evidence: Optional verifiable evidence explaining revocation.
            event_id: Optional unique event ID for idempotency control.

        Raises:
            ValueError: If no active vouch exists.
        """
        if not self.graph.has_edge(source_id, target_id):
            raise ValueError(f"No active vouch found from '{source_id}' to '{target_id}'.")

        key = f"{source_id}_{target_id}"

        # Record immutable event in ledger first (Source of Truth)
        if self.ledger is not None:
            self.ledger.append_event(
                event_type="VOUCH_REVOKED",
                actor_id=source_id,
                subject_id=target_id,
                payload={"revoked_vouch": key},
                evidence=evidence,
                event_id=event_id,
            )

        # Remove edge from graph
        self.graph.remove_edge(source_id, target_id)

        # Update vouch record
        if key in self.vouches:
            self.vouches[key].active = False
            self.vouches[key].weight = Decimal("0.0")

        # Atomically reallocate capacity across remaining siblings
        self.recompute_weights(source_id)

    def verify_conservation(self, user_id: str) -> bool:
        """Assert that total outgoing weights do not exceed user capacity."""
        user = self.get_user(user_id)
        if not user:
            return True

        out_edges = list(self.graph.out_edges(user_id, data=True))
        if not out_edges:
            return True

        total_weight = sum(edge_data.get("weight", Decimal("0.0")) for _, _, edge_data in out_edges)
        return total_weight <= user.capacity

    def mint_transaction_reputation(
        self,
        user_a: str,
        user_b: str,
        m0: Optional[Decimal] = None,
        mint_lambda: Optional[Decimal] = None,
        directional: bool = False,
        evidence: Optional[Evidence] = None,
        event_id: Optional[str] = None,
    ) -> Decimal:
        """Mint diminishing reputation rewards for repeated qualifying transactions between a pair.

        Formula (Section 2 & 3 of Master Model 2026):
            M_k = M_0 * exp(-lambda * (k - 1))
            R_u' = R_u + M_k
        """
        from veritrust.config import get_settings
        from veritrust.scoring import _decimal_exp

        settings = get_settings()
        base_m0 = m0 if m0 is not None else settings.m0
        lam = mint_lambda if mint_lambda is not None else settings.mint_lambda

        ua = self.get_user(user_a)
        ub = self.get_user(user_b)
        if not ua:
            raise ValueError(f"User '{user_a}' does not exist.")
        if not ub:
            raise ValueError(f"User '{user_b}' does not exist.")

        pair_key = f"{user_a}_{user_b}" if directional else f"{min(user_a, user_b)}_{max(user_a, user_b)}"
        current_k = self.pair_transaction_counters.get(pair_key, 0) + 1
        self.pair_transaction_counters[pair_key] = current_k

        # Compute M_k = M_0 * exp(-lambda * (k - 1))
        exponent = -lam * Decimal(current_k - 1)
        decay_factor = _decimal_exp(exponent)
        m_k = (base_m0 * decay_factor).quantize(Decimal("0.0001"))

        if m_k > Decimal("0.0"):
            # Update owned reputation for both users
            for u in (ua, ub):
                u.reputation += m_k
                u.update_capacity()
                self._sync_node_to_graph(u)
                self.recompute_weights(u.user_id)

                if self.ledger is not None:
                    self.ledger.append_event(
                        event_type="REPUTATION_MINTED",
                        actor_id="SYSTEM_TRANSACTION_ORACLE",
                        subject_id=u.user_id,
                        delta_reputation=m_k,
                        payload={
                            "reason": "qualifying_transaction_pair",
                            "partner_id": user_b if u == ua else user_a,
                            "k_counter": current_k,
                            "m0": str(base_m0),
                            "lambda": str(lam),
                        },
                        evidence=evidence,
                        event_id=event_id,
                    )

        return m_k


