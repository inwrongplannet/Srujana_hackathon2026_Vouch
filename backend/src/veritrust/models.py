"""Domain models for the VeriTrust engine.

All financial amounts and reputation scores use Decimal end-to-end to prevent
floating-point drift from corrupting graph trust calculations.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class FinancialFeatures(BaseModel):
    """Borrower financial signals for cash-flow underwriting."""

    monthly_income: Decimal = Field(default=Decimal("0.0"), description="Gross monthly income in INR")
    monthly_debt: Decimal = Field(default=Decimal("0.0"), description="Existing recurring debt payments in INR")
    net_operating_income: Decimal = Field(
        default=Decimal("0.0"), description="Net operating income after operating expenses"
    )
    debt_service: Decimal = Field(default=Decimal("0.0"), description="Total monthly debt service obligations")
    income_volatility: Decimal = Field(
        default=Decimal("0.15"), description="Coefficient of variation of income (stddev / mean)"
    )
    cashflow_volatility: Decimal = Field(
        default=Decimal("0.15"), description="Volatility of net operating cash flows"
    )
    completeness: Decimal = Field(
        default=Decimal("1.0"),
        description="Data completeness fraction in [0.0, 1.0]. Lower values increase epistemic uncertainty.",
    )

    @field_validator(
        "monthly_income",
        "monthly_debt",
        "net_operating_income",
        "debt_service",
        "income_volatility",
        "cashflow_volatility",
        "completeness",
        mode="before",
    )
    @classmethod
    def parse_to_decimal(cls, value: object) -> Decimal:
        """Coerce raw numeric inputs to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class User(BaseModel):
    """Participant node in the VeriTrust web-of-trust graph."""

    user_id: str = Field(description="Unique protocol identifier for the node (e.g. 'U001')")
    name: str = Field(description="Display name or organizational label")
    reputation: Decimal = Field(default=Decimal("0.0"), description="Intrinsic credibility score R")
    capacity: Decimal = Field(
        default=Decimal("0.0"), description="Allocatable vouch capacity C_u = max(0, R_u)"
    )
    status: Literal["ACTIVE", "RESTRICTED", "DEFAULTED"] = Field(
        default="ACTIVE", description="Node protocol state"
    )
    is_anchor: bool = Field(
        default=False, description="True if this node is an institutional / seed trust root"
    )
    financial_features: Optional[FinancialFeatures] = Field(
        default=None, description="Optional financial health features"
    )
    n_settled_loans: int = Field(default=0, description="Count of successfully repaid loan contracts")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("reputation", "capacity", mode="before")
    @classmethod
    def parse_reputation_decimal(cls, value: object) -> Decimal:
        """Coerce reputation/capacity inputs to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    def update_capacity(self) -> None:
        """Synchronize allocatable capacity with current reputation score.

        C_u = max(0, R_u) if ACTIVE, else 0.
        """
        if self.status != "ACTIVE":
            self.capacity = Decimal("0.0")
        else:
            self.capacity = max(Decimal("0.0"), self.reputation)


class Transaction(BaseModel):
    """Monetary transaction record."""

    tx_id: str = Field(description="Unique transaction ID")
    user_id: str = Field(description="Target user ID")
    amount: Decimal = Field(description="Transaction amount (paise / Decimal)")
    currency: str = Field(default="INR", description="ISO 4217 currency code")
    tx_type: Literal["INCOME", "DEBT_SERVICE", "DISBURSEMENT", "REPAYMENT"] = Field(
        description="Type of financial transaction"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> Decimal:
        """Ensure amount is strictly Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class Vouch(BaseModel):
    """Directed trust endorsement between two nodes."""

    vouch_id: str = Field(description="Unique vouch ID (e.g. 'V_U001_U002')")
    source: str = Field(description="Source endorser user ID (u)")
    target: str = Field(description="Endorsed borrower user ID (v)")
    weight: Decimal = Field(
        default=Decimal("0.0"), description="Allocated vouch weight W_uv satisfying out-degree conservation"
    )
    active: bool = Field(default=True, description="Whether this endorsement is currently active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("weight", mode="before")
    @classmethod
    def parse_weight(cls, value: object) -> Decimal:
        """Ensure weight is strictly Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class Loan(BaseModel):
    """Borrowing contract record."""

    loan_id: str = Field(description="Unique loan ID")
    borrower_id: str = Field(description="Borrower user ID")
    lender_id: Optional[str] = Field(default=None, description="Lender user ID for peer-to-peer lending")
    principal: Decimal = Field(description="Principal loan amount in INR")
    outstanding_balance: Decimal = Field(description="Remaining balance to be settled in INR")
    interest_rate: Decimal = Field(
        default=Decimal("0.10"), description="Annual interest rate as a decimal fraction (e.g. 0.10 = 10%)"
    )
    tenure_months: int = Field(default=6, description="Tenure in months")
    status: Literal["PENDING", "ACTIVE", "REPAID", "DEFAULTED"] = Field(
        default="ACTIVE", description="Current contract status"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("principal", "outstanding_balance", "interest_rate", mode="before")
    @classmethod
    def parse_loan_decimals(cls, value: object) -> Decimal:
        """Ensure loan numeric fields are Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class ContributingPath(BaseModel):
    """Explainability record of a trust path from an anchor to a target node."""

    path: list[str] = Field(description="Sequence of node IDs [anchor, ..., target]")
    hop_weights: list[Decimal] = Field(description="Edge weights along each hop")
    path_trust: Decimal = Field(description="Total attenuated trust contribution of this path")


class CreditAssessment(BaseModel):
    """Dual-axis credit evaluation report."""

    user_id: str = Field(description="Evaluated borrower user ID")
    r_graph: Decimal = Field(description="Graph trust score propagated from institutional anchors")
    s_cashflow: Decimal = Field(description="Repayment capacity score derived from cash-flow signals")
    mu_composite: Decimal = Field(description="Expected repayment capacity (weighted blend)")
    sigma2_epistemic: Decimal = Field(
        description="Epistemic uncertainty [0.0, 1.0]. High uncertainty indicates thin file, not bad credit."
    )
    score_final: Decimal = Field(
        description="Lower Confidence Bound (LCB) decision score: mu - kappa * sqrt(sigma2)"
    )
    max_loan_limit: Decimal = Field(description="Maximum eligible borrowing limit in INR")
    currency: str = Field(default="INR", description="ISO 4217 currency code")
    contributing_paths: list[ContributingPath] = Field(
        default_factory=list, description="Audit list of paths backing this borrower"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    disclaimer: str = Field(
        default="Illustrative data — prototype recommendation, not validated financial advice."
    )


class Evidence(BaseModel):
    """Verifiable evidence backing a reputation mutation event."""

    evidence_id: str = Field(description="Unique identifier for the evidence")
    evidence_type: Literal[
        "COMMUNITY_VOUCH",
        "SETTLEMENT_RECEIPT",
        "BANK_STATEMENT",
        "DEFAULT_NOTICE",
        "GOVERNANCE_OVERRIDE",
        "IDENTITY_ANCHOR",
    ] = Field(default="COMMUNITY_VOUCH", description="Category of evidence")
    uri_or_hash: str = Field(default="", description="Content hash, DigiLocker URI, or receipt reference")
    description: str = Field(description="Human-readable explanation of the evidence")
    recorded_by: str = Field(description="Actor or authority who submitted this evidence")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LedgerEvent(BaseModel):
    """Immutable, cryptographically chained event in the VeriTrust Reputation Ledger."""

    event_id: str = Field(description="Unique event identifier (e.g. 'EVT_00001')")
    sequence: int = Field(default=0, description="Sequential index in the append-only ledger")
    event_type: Literal[
        "USER_REGISTERED",
        "VOUCH_CREATED",
        "VOUCH_REVOKED",
        "LOAN_DISBURSED",
        "LOAN_REPAID",
        "LOAN_DEFAULTED",
        "REPUTATION_SLASHED",
        "REPUTATION_MINTED",
    ] = Field(description="Specific lifecycle event type")
    actor_id: str = Field(description="Entity triggering this action (user, lender, or system)")
    subject_id: str = Field(description="Target node whose trust or standing is affected")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delta_reputation: Decimal = Field(
        default=Decimal("0.0"), description="Signed change in subject reputation from this event"
    )
    evidence: Optional[Evidence] = Field(default=None, description="Auditable evidence reference")
    payload: dict = Field(default_factory=dict, description="Event-specific metadata")
    prev_hash: str = Field(default="", description="SHA-256 hash of the immediately preceding event")
    event_hash: str = Field(default="", description="SHA-256 hash of this event's canonical fields")

    @field_validator("delta_reputation", mode="before")
    @classmethod
    def parse_delta(cls, value: object) -> Decimal:
        """Coerce delta_reputation to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    def compute_hash(self) -> str:
        """Compute deterministic SHA-256 hash for tamper detection."""
        import hashlib, json
        payload_canonical = json.dumps(self.payload, sort_keys=True, default=str)
        if self.evidence:
            evidence_str = json.dumps(self.evidence.model_dump(mode="json"), sort_keys=True, default=str)
        else:
            evidence_str = ""
        raw = (
            f"{self.prev_hash}|{self.event_id}|{self.sequence}|{self.event_type}|"
            f"{self.actor_id}|{self.subject_id}|{str(self.delta_reputation)}|"
            f"{self.timestamp.isoformat()}|{evidence_str}|{payload_canonical}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


