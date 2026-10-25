"""Domain models for the VeriTrust engine.

All financial amounts and reputation scores use Decimal end-to-end to prevent
floating-point drift from corrupting graph trust calculations.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


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
    """Monetary transaction record with platform fee cut tracking."""

    tx_id: str = Field(description="Unique transaction ID")
    user_id: str = Field(description="Target user ID")
    amount: Decimal = Field(description="Gross transaction amount in INR (paise / Decimal)")
    fee: Decimal = Field(default=Decimal("0.00"), description="Platform fee cut in INR (Decimal)")
    net_amount: Decimal = Field(default=Decimal("0.00"), description="Net transaction amount in INR (Decimal)")
    currency: str = Field(default="INR", description="ISO 4217 currency code")
    tx_type: Literal["INCOME", "DEBT_SERVICE", "DISBURSEMENT", "REPAYMENT", "PLATFORM_FEE"] = Field(
        description="Type of financial transaction"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("amount", "fee", "net_amount", mode="before")
    @classmethod
    def parse_amount(cls, value: object) -> Decimal:
        """Ensure monetary amounts are strictly Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @model_validator(mode="after")
    def populate_net_amount_default(self) -> "Transaction":
        """Default net_amount to amount if not explicitly set."""
        if self.net_amount == Decimal("0.00") and self.amount > Decimal("0.00"):
            self.net_amount = self.amount
        return self


class PlatformTreasury(BaseModel):
    """Platform treasury revenue and fee tracking."""

    treasury_id: str = Field(default="PLATFORM_TREASURY", description="Treasury account ID")
    total_fees_collected: Decimal = Field(default=Decimal("0.00"), description="Cumulative platform fee cut in INR")
    fee_rate: Decimal = Field(default=Decimal("0.01"), description="Active platform fee cut rate fraction (e.g. 0.01 = 1%)")
    transaction_count: int = Field(default=0, description="Total transactions processed through treasury")
    currency: str = Field(default="INR", description="ISO 4217 currency code")

    @field_validator("total_fees_collected", "fee_rate", mode="before")
    @classmethod
    def parse_treasury_decimals(cls, value: object) -> Decimal:
        """Ensure treasury numeric amounts are strictly Decimal."""
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
    rank: int = Field(
        default=1, description="Chronological rank r_uv among endorsements received by target (1-based, immutable)"
    )
    alpha: Decimal = Field(
        default=Decimal("1.0"), description="Chronological rank weight alpha_uv = 1 / 2^(r_uv - 1)"
    )
    active: bool = Field(default=True, description="Whether this endorsement is currently active")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("weight", "alpha", mode="before")
    @classmethod
    def parse_weight_decimals(cls, value: object) -> Decimal:
        """Ensure numeric fields are strictly Decimal."""
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
        "CONTESTED_RECORD",
        "DISPUTE_RESOLUTION",
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
        "DISPUTE_FILED",
        "DISPUTE_RESOLVED",
        "PLATFORM_FEE_COLLECTED",
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


# -----------------------------------------------------------------------------
# Master Documentation v2 Schemas (Section 5, 6, 8)
# -----------------------------------------------------------------------------

BureauStatus = Literal["AVAILABLE", "NO_FILE", "UNAVAILABLE", "NOT_AUTHORIZED"]


class BureauReport(BaseModel):
    """Credit bureau signal representation (Section 8 of Master Doc v2)."""

    status: BureauStatus = Field(default="NO_FILE", description="Bureau data availability status")
    score: Optional[int] = Field(default=None, description="Official credit score (300-900), or None if NO_FILE")
    source: Optional[str] = Field(default=None, description="Credit bureau authority (e.g. CIBIL, Experian)")
    as_of: Optional[datetime] = Field(default=None, description="Timestamp of bureau pull")


class VouchScoreReport(BaseModel):
    """Bounded Vouch Score (0-100) from Section 6.2 of Master Doc v2."""

    vouch_score: Decimal = Field(default=Decimal("0.0"), description="Bounded score in [0, 100]")
    status: Literal["PROVISIONAL", "ACTIVE", "RESTRICTED"] = Field(
        default="ACTIVE", description="Vouch score standing"
    )
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        default="MEDIUM", description="Confidence rating based on data depth"
    )
    eligible_endorsements: int = Field(default=0, description="Count of active contributing endorsements")
    raw_support: Decimal = Field(default=Decimal("0.0"), description="Diminishing returns support: 1 - exp(-W/tau)")
    quality_factor: Decimal = Field(default=Decimal("0.5"), description="Historical outcome quality: clamp(C, 0, 1)")

    @field_validator("vouch_score", "raw_support", "quality_factor", mode="before")
    @classmethod
    def parse_vouch_score_decimals(cls, value: object) -> Decimal:
        """Coerce numeric values to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class EndorsementItem(BaseModel):
    """Fine-grained endorsement with edge quality factors (Section 6.1 of Master Doc v2)."""

    endorsement_id: str = Field(description="Unique identifier for the endorsement")
    endorser_id: str = Field(description="User ID of the endorser (x)")
    recipient_id: str = Field(description="User ID of the recipient (y)")
    application_id: Optional[str] = Field(default=None, description="Optional loan application link")
    statement: str = Field(default="", description="Optional vouch statement or rationale")
    r_x: Decimal = Field(default=Decimal("1.0"), description="Endorser reputation factor in [0, 1]")
    q_x: Decimal = Field(default=Decimal("1.0"), description="Endorser verification / data quality factor in [0, 1]")
    e_xy: Decimal = Field(default=Decimal("1.0"), description="Edge strength after policy checks in [0, 1]")
    d_xy: Decimal = Field(default=Decimal("1.0"), description="Evidence relevance factor in [0, 1]")
    p_xy: Decimal = Field(default=Decimal("0.0"), description="Abuse and collusion penalty factor in [0, 1]")
    effective_weight: Decimal = Field(
        default=Decimal("0.0"), description="w_xy = clamp(r_x * q_x * e_xy * d_xy * (1 - p_xy), 0, 1)"
    )
    status: Literal["ACTIVE", "REVOKED", "EXPIRED", "DISPUTED"] = Field(
        default="ACTIVE", description="Lifecycle status of this endorsement"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiry: Optional[datetime] = Field(default=None, description="Optional expiry timestamp")

    @field_validator("r_x", "q_x", "e_xy", "d_xy", "p_xy", "effective_weight", mode="before")
    @classmethod
    def parse_endorsement_decimals(cls, value: object) -> Decimal:
        """Coerce numeric factors to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class LoanApplication(BaseModel):
    """Formal loan application record (Section 5 & 10 of Master Doc v2)."""

    application_id: str = Field(description="Unique application ID (e.g. 'APP_00001')")
    borrower_id: str = Field(description="Target applicant user ID")
    principal: Decimal = Field(description="Requested principal amount in INR")
    annual_rate: Decimal = Field(default=Decimal("0.12"), description="Annual interest rate (e.g. 0.12 = 12%)")
    term_months: int = Field(default=12, description="Requested tenure in months")
    purpose_category: str = Field(default="GENERAL", description="Loan purpose category")
    status: Literal["SUBMITTED", "UNDERWRITING", "APPROVED", "REJECTED", "FUNDED"] = Field(
        default="SUBMITTED", description="Current application status"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("principal", "annual_rate", mode="before")
    @classmethod
    def parse_app_decimals(cls, value: object) -> Decimal:
        """Coerce numeric values to Decimal."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))


class CombinedAssessment(BaseModel):
    """Side-by-side combined credit assessment (Section 8 of Master Doc v2)."""

    assessment_id: str = Field(description="Unique assessment snapshot identifier")
    application_id: Optional[str] = Field(default=None, description="Associated loan application ID")
    borrower_id: str = Field(description="Evaluated borrower user ID")
    bureau: BureauReport = Field(description="Conventional bureau signal (unblended)")
    vouch: VouchScoreReport = Field(description="Bounded Vouch score (0-100) and confidence")
    affordability: dict = Field(description="Cash-flow affordability and EMI capacity metrics")
    data_quality: Literal["HIGH_CONFIDENCE_VERIFIED", "MEDIUM", "LOW"] = Field(
        default="MEDIUM", description="Data completeness and verification grade"
    )
    positive_factors: list[dict] = Field(default_factory=list, description="Evidence-backed positive reason codes")
    risk_factors: list[dict] = Field(default_factory=list, description="Evidence-backed risk reason codes")
    missing_information: list[str] = Field(default_factory=list, description="Missing or unverified fields")
    review_flags: list[str] = Field(default_factory=list, description="Flags requiring human underwriter review")
    algorithm_version: str = Field(default="vouch-v2.0", description="Version of credit assessment rules")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PropagatedCredibilityReport(BaseModel):
    """Consolidated credibility propagated across the endorsement graph."""

    user_id: str
    g_raw: Decimal = Field(description="Uncapped propagated credibility G(u) = sum(p_u(s))")
    g_score: Decimal = Field(description="Scoring-capped propagated credibility G_score(u) = min(G(u), G_max)")
    source_contributions: dict[str, Decimal] = Field(
        default_factory=dict, description="Consolidated min-path contribution p_u(s) per distinct source s"
    )
    paths: list[ContributingPath] = Field(
        default_factory=list, description="All evaluated simple paths with individual T(P) values"
    )


class EndorserPenaltyDetail(BaseModel):
    """Detailed record of an endorser penalty resulting from a borrower default."""

    source_id: str
    contribution: Decimal = Field(description="Pre-default contribution p_D(u)")
    contribution_share: Decimal = Field(description="Contribution share a_u = p_D(u) / sum(p_D)")
    penalty_fraction: Decimal = Field(description="Endorser penalty fraction q_u = eta * q_D * a_u")
    delta_reputation: Decimal = Field(description="Owned reputation deducted Delta_u = R_u * q_u")
    pre_reputation: Decimal = Field(description="Pre-penalty owned reputation R_u")
    post_reputation: Decimal = Field(description="Post-penalty owned reputation R_u'")


class DefaultPenaltyReport(BaseModel):
    """Complete forensic record of an atomic snapshot-based default event."""

    loan_id: str
    defaulter_id: str
    outstanding_exposure: Decimal = Field(description="Exposure E_D = P_D + I_D")
    default_severity: Decimal = Field(description="Severity S_D = E_D * R_D / (R_D + G_D)")
    unpaid_fraction: Decimal = Field(description="Unpaid obligation fraction x_D = min(1, E_D / L_D)")
    normalized_overdue: Decimal = Field(description="Normalized overdue time tau_D = t_overdue / T_0")
    borrower_penalty_fraction: Decimal = Field(description="Borrower loss fraction q_D")
    borrower_delta: Decimal = Field(description="Borrower owned reputation deduction Delta_D")
    borrower_pre_reputation: Decimal
    borrower_post_reputation: Decimal
    borrower_pre_propagated_g: Decimal
    endorser_penalties: dict[str, EndorserPenaltyDetail] = Field(default_factory=dict)
    applied_atomically: bool = True




