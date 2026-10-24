"""In-memory lending and borrowing service for VeriTrust.

Manages loan contracts, disbursements, repayments, reputation settlement yields,
and atomic 4-level slashing cascades on default. No smart contracts.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from veritrust.config import get_settings
from veritrust.engine import TrustEngine
from veritrust.models import Loan, Transaction
from veritrust.scoring import CreditScorer


class LendingService:
    """Orchestrates lending operations and default cascades."""

    def __init__(
        self,
        engine: TrustEngine,
        scorer: CreditScorer,
        borrower_reward: Optional[Decimal] = None,
        sponsor_reward: Optional[Decimal] = None,
        default_base_slash: Optional[Decimal] = None,
        gamma: Optional[Decimal] = None,
    ) -> None:
        """Initialize the lending service.

        Args:
            engine: The Web-of-Trust graph engine.
            scorer: Dual-axis credit scorer for limit verification.
            borrower_reward: Credibility increment minted to borrower on full repayment.
            sponsor_reward: Credibility increment awarded to direct sponsors on repayment.
            default_base_slash: Primary default penalty delta0.
            gamma: Sponsor penalty fraction (delta1 = gamma * W_AB * delta0).
        """
        settings = get_settings()
        self.engine = engine
        self.scorer = scorer
        self.borrower_reward = borrower_reward if borrower_reward is not None else settings.borrower_reward
        self.sponsor_reward = sponsor_reward if sponsor_reward is not None else settings.sponsor_reward
        self.default_base_slash = (
            default_base_slash if default_base_slash is not None else settings.default_base_slash
        )
        self.gamma = gamma if gamma is not None else settings.gamma

        self.loans: dict[str, Loan] = {}
        self.transactions: list[Transaction] = []
        self._tx_counter: int = 0
        self._loan_counter: int = 0

    def _next_tx_id(self) -> str:
        self._tx_counter += 1
        return f"TX_{self._tx_counter:05d}"

    def _next_loan_id(self) -> str:
        self._loan_counter += 1
        return f"LN_{self._loan_counter:05d}"

    def borrow(
        self,
        borrower_id: str,
        amount: Decimal,
        tenure_months: int = 6,
        interest_rate: Decimal = Decimal("0.10"),
    ) -> Loan:
        """Issue a loan to borrower_id after verifying their credit assessment limit.

        Args:
            borrower_id: Target user ID.
            amount: Requested principal in INR.
            tenure_months: Loan tenure in months.
            interest_rate: Annual interest rate as a decimal fraction.

        Returns:
            The newly created and activated Loan record.

        Raises:
            ValueError: If user is not ACTIVE or requested amount exceeds approved limit.
        """
        borrower = self.engine.get_user(borrower_id)
        if not borrower:
            raise ValueError(f"Borrower '{borrower_id}' does not exist.")

        if borrower.status != "ACTIVE":
            raise ValueError(f"Borrower '{borrower_id}' is '{borrower.status}' and cannot take loans.")

        # Evaluate current credit capacity
        assessment = self.scorer.assess_credit(borrower_id)
        if amount > assessment.max_loan_limit:
            raise ValueError(
                f"Requested loan amount INR {amount:,.2f} exceeds approved credit limit "
                f"INR {assessment.max_loan_limit:,.2f} (Score: {assessment.score_final})."
            )

        loan_id = self._next_loan_id()
        loan = Loan(
            loan_id=loan_id,
            borrower_id=borrower_id,
            principal=amount,
            outstanding_balance=amount,
            interest_rate=interest_rate,
            tenure_months=tenure_months,
            status="ACTIVE",
        )
        self.loans[loan_id] = loan

        # Record disbursement transaction
        tx = Transaction(
            tx_id=self._next_tx_id(),
            user_id=borrower_id,
            amount=amount,
            tx_type="DISBURSEMENT",
        )
        self.transactions.append(tx)
        return loan

    def repay(self, loan_id: str, amount: Decimal) -> Loan:
        """Apply a repayment against an active loan.

        If the loan balance reaches zero, marks the loan REPAID, increments the
        borrower's settled loan count, and awards reputation yields to both the
        borrower and their direct sponsors.

        Args:
            loan_id: ID of the loan to repay.
            amount: Repayment amount in INR.

        Returns:
            The updated Loan record.

        Raises:
            ValueError: If loan does not exist or is not ACTIVE.
        """
        loan = self.loans.get(loan_id)
        if not loan:
            raise ValueError(f"Loan '{loan_id}' does not exist.")

        if loan.status != "ACTIVE":
            raise ValueError(f"Cannot repay loan '{loan_id}' with status '{loan.status}'.")

        # Cap payment to outstanding balance
        actual_payment = min(amount, loan.outstanding_balance)
        loan.outstanding_balance -= actual_payment

        # Record repayment transaction
        tx = Transaction(
            tx_id=self._next_tx_id(),
            user_id=loan.borrower_id,
            amount=actual_payment,
            tx_type="REPAYMENT",
        )
        self.transactions.append(tx)

        # Check for full settlement
        if loan.outstanding_balance == Decimal("0.0"):
            loan.status = "REPAID"
            borrower = self.engine.get_user(loan.borrower_id)
            if borrower:
                # Mint borrower credibility yield
                borrower.n_settled_loans += 1
                borrower.reputation += self.borrower_reward
                borrower.update_capacity()
                self.engine._sync_node_to_graph(borrower)
                self.engine.recompute_weights(borrower.user_id)

                # Award sponsor reputation yield to all incoming active vouchers
                in_edges = list(self.engine.graph.in_edges(borrower.user_id))
                for sponsor_id, _ in in_edges:
                    sponsor = self.engine.get_user(sponsor_id)
                    if sponsor and sponsor.status == "ACTIVE":
                        sponsor.reputation += self.sponsor_reward
                        sponsor.update_capacity()
                        self.engine._sync_node_to_graph(sponsor)
                        self.engine.recompute_weights(sponsor_id)

        return loan

    def default_loan(self, loan_id: str, delta0: Optional[Decimal] = None) -> None:
        """Trigger an atomic 4-level slashing cascade on loan default.

        Rules (Skill: slashing-cascade):
            k = 0 (Defaulter B): R_B <- R_B - delta0; status -> DEFAULTED; C_B = 0; W_B* = 0
            k = 1 (Direct sponsor A): delta_A = 0.5 * W_AB * delta0; if R_A < 0 -> RESTRICTED
            k = 2 (Transitive ancestor Z): delta_Z = 0.25 * delta0; if R_Z < 0 -> RESTRICTED
            k >= 3: delta = 0 (Hard boundary cutoff)

        All penalties and weight redistributions are applied atomically.
        """
        loan = self.loans.get(loan_id)
        if not loan:
            raise ValueError(f"Loan '{loan_id}' does not exist.")

        if loan.status != "ACTIVE":
            raise ValueError(f"Cannot default loan '{loan_id}' with status '{loan.status}'.")

        loan.status = "DEFAULTED"
        slash_amount = delta0 if delta0 is not None else self.default_base_slash
        defaulter_id = loan.borrower_id
        defaulter = self.engine.get_user(defaulter_id)

        if not defaulter:
            return

        # -------------------------------------------------------------
        # Level k = 0: Defaulter
        # -------------------------------------------------------------
        defaulter.reputation -= slash_amount
        defaulter.status = "DEFAULTED"
        defaulter.capacity = Decimal("0.0")
        self.engine._sync_node_to_graph(defaulter)

        # Freeze all outbound vouch weights to 0
        for _, neighbor in list(self.engine.graph.out_edges(defaulter_id)):
            self.engine.graph[defaulter_id][neighbor]["weight"] = Decimal("0.0")
            key = f"{defaulter_id}_{neighbor}"
            if key in self.engine.vouches:
                self.engine.vouches[key].weight = Decimal("0.0")

        # -------------------------------------------------------------
        # Level k = 1: Direct Sponsors (A vouched for B)
        # -------------------------------------------------------------
        direct_sponsors = list(self.engine.graph.predecessors(defaulter_id))
        k2_ancestors: set[str] = set()

        for sponsor_id in direct_sponsors:
            w_ab = self.engine.graph[sponsor_id][defaulter_id].get("weight", Decimal("0.0"))
            delta_1 = self.gamma * w_ab * slash_amount

            sponsor = self.engine.get_user(sponsor_id)
            if sponsor:
                sponsor.reputation -= delta_1
                if sponsor.reputation < Decimal("0.0") and sponsor.status == "ACTIVE":
                    sponsor.status = "RESTRICTED"
                sponsor.update_capacity()
                self.engine._sync_node_to_graph(sponsor)
                self.engine.recompute_weights(sponsor_id)

            # Collect k=2 ancestors (who vouched for this sponsor)
            for ancestor_id in self.engine.graph.predecessors(sponsor_id):
                if ancestor_id != defaulter_id and ancestor_id not in direct_sponsors:
                    k2_ancestors.add(ancestor_id)

        # -------------------------------------------------------------
        # Level k = 2: Transitive Ancestors (Z vouched for A)
        # -------------------------------------------------------------
        delta_2 = (self.gamma * self.gamma) * slash_amount
        for ancestor_id in k2_ancestors:
            ancestor = self.engine.get_user(ancestor_id)
            if ancestor:
                ancestor.reputation -= delta_2
                if ancestor.reputation < Decimal("0.0") and ancestor.status == "ACTIVE":
                    ancestor.status = "RESTRICTED"
                ancestor.update_capacity()
                self.engine._sync_node_to_graph(ancestor)
                self.engine.recompute_weights(ancestor_id)

        # Level k >= 3: delta = 0 (Hard isolation boundary)

    def get_loan(self, loan_id: str) -> Optional[Loan]:
        """Fetch loan by ID."""
        return self.loans.get(loan_id)

    def list_loans(self) -> list[Loan]:
        """Return all loan records."""
        return list(self.loans.values())

    def list_transactions(self) -> list[Transaction]:
        """Return all transaction ledger entries."""
        return list(self.transactions)

