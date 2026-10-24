"""Graph and Trust Engine for VeriTrust.

Manages participant nodes (users) and directed endorsements (vouches) on a NetworkX DiGraph.
Enforces the fundamental Invariant 1: Out-Degree Capacity Conservation.
"""

from decimal import Decimal
from typing import Optional
import networkx as nx

from veritrust.models import FinancialFeatures, User, Vouch


class TrustEngine:
    """Core Web-of-Trust graph engine maintaining participants and endorsements."""

    def __init__(self) -> None:
        """Initialize empty graph and registries."""
        self.graph: nx.DiGraph = nx.DiGraph()
        self.users: dict[str, User] = {}
        self.vouches: dict[str, Vouch] = {}  # key: f"{source}_{target}"

    def create_user(
        self,
        user_id: str,
        name: str,
        initial_reputation: Decimal = Decimal("0.0"),
        is_anchor: bool = False,
        financial_features: Optional[FinancialFeatures] = None,
    ) -> User:
        """Create and register a new user node in the system.

        Args:
            user_id: Unique identifier for the user.
            name: Display name.
            initial_reputation: Starting reputation score (anchors start > 0).
            is_anchor: True if this is an institutional seed anchor.
            financial_features: Optional cash-flow metrics.

        Returns:
            The created User instance.

        Raises:
            ValueError: If user_id already exists.
        """
        if user_id in self.users:
            raise ValueError(f"User with ID '{user_id}' already exists.")

        rep = Decimal(str(initial_reputation))
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

    def vouch(self, source_id: str, target_id: str) -> Vouch:
        """Establish a directed trust endorsement from source to target.

        Args:
            source_id: User ID of the endorser.
            target_id: User ID of the endorsed borrower.

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

        # Insert edge into graph
        self.graph.add_edge(source_id, target_id, weight=Decimal("0.0"))

        vouch_record = Vouch(
            vouch_id=f"V_{source_id}_{target_id}",
            source=source_id,
            target=target_id,
            weight=Decimal("0.0"),
            active=True,
        )
        self.vouches[f"{source_id}_{target_id}"] = vouch_record

        # Atomically reweight all siblings including this new edge
        self.recompute_weights(source_id)

        # Retrieve final conserved weight
        vouch_record.weight = self.graph[source_id][target_id]["weight"]
        return vouch_record

    def unvouch(self, source_id: str, target_id: str) -> None:
        """Remove an existing endorsement and reallocate capacity among remaining siblings.

        Args:
            source_id: User ID of endorser.
            target_id: User ID of endorsed borrower.

        Raises:
            ValueError: If no active vouch exists.
        """
        if not self.graph.has_edge(source_id, target_id):
            raise ValueError(f"No active vouch found from '{source_id}' to '{target_id}'.")

        # Remove edge from graph
        self.graph.remove_edge(source_id, target_id)

        # Update vouch record
        key = f"{source_id}_{target_id}"
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

