"""Borrower Recourse & Evidence-Quality Workflow for VeriTrust.

Provides a fair creditworthiness recourse protocol:
- Allows borrowers to contest erroneous transactions, dispute defaults, and provide corrected evidence.
- Categorizes data quality across: VERIFIED, MISSING, STALE, DUPLICATED, and DISPUTED.
- Strictly separates data-quality classification from underlying economic repayment capacity.
- Records all dispute filings, evidence corrections, and score recalculations on the append-only ledger.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

from veritrust.affordability import AffordabilityEngine, AffordabilityInput
from veritrust.engine import TrustEngine
from veritrust.ledger import ReputationLedger
from veritrust.models import CreditAssessment, Evidence, FinancialFeatures, LedgerEvent
from veritrust.scoring import CreditScorer


RecordQualityStatus = Literal["VERIFIED", "MISSING", "STALE", "DUPLICATED", "DISPUTED"]
DisputeStatus = Literal["OPEN", "UNDER_REVIEW", "RESOLVED_UPHELD", "RESOLVED_REJECTED"]


class QualityFlaggedRecord(BaseModel):
    """An auditable record tagged with its evidence-quality classification."""

    record_id: str
    record_type: Literal["TRANSACTION", "INCOME_STATEMENT", "DEBT_SERVICE", "DEFAULT_NOTICE", "COMMUNITY_VOUCH"]
    quality_status: RecordQualityStatus
    claimed_value: str
    flagged_reason: str
    evidence_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DisputeCase(BaseModel):
    """Formal borrower contestation against a recorded transaction or negative credit event."""

    dispute_id: str
    borrower_id: str
    target_record_id: str
    target_record_type: str
    contestation_reason: str
    supporting_evidence: Evidence
    status: DisputeStatus = "OPEN"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolving_officer: Optional[str] = None
    resolution_summary: Optional[str] = None
    recalculation_impact: Optional[dict[str, str]] = None


class EvidenceQualityAudit(BaseModel):
    """Independent evidence-quality audit separating epistemic quality from credit capacity."""

    borrower_id: str
    total_records_tracked: int
    verified_records_count: int
    missing_records_count: int
    stale_records_count: int
    duplicated_records_count: int
    disputed_records_count: int
    data_quality_grade: Literal["HIGH_INTEGRITY", "PARTIAL_DISCLOSURE", "DATA_QUALITY_CONTESTED", "CRITICAL_DEFICIT"]
    flagged_records: list[QualityFlaggedRecord]
    open_disputes: list[DisputeCase]
    resolved_disputes: list[DisputeCase]
    fair_credit_compliance_notes: list[str]


class BorrowerRecourseWorkflow:
    """Manages borrower dispute resolution, evidence quality tracking, and recalculation audit."""

    def __init__(
        self,
        engine: TrustEngine,
        scorer: CreditScorer,
        affordability_engine: Optional[AffordabilityEngine] = None,
    ) -> None:
        self.engine = engine
        self.scorer = scorer
        self.affordability_engine = affordability_engine or AffordabilityEngine()
        self.disputes: dict[str, DisputeCase] = {}
        self.quality_records: dict[str, list[QualityFlaggedRecord]] = {}
        self._dispute_counter: int = 0

    def _next_dispute_id(self) -> str:
        self._dispute_counter += 1
        return f"DISP_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{self._dispute_counter:04d}"

    def file_dispute(
        self,
        borrower_id: str,
        target_record_id: str,
        target_record_type: str,
        contestation_reason: str,
        supporting_evidence: Evidence,
    ) -> DisputeCase:
        """File a formal contestation against an inaccurate record with supporting primary evidence."""
        borrower = self.engine.get_user(borrower_id)
        if not borrower:
            raise ValueError(f"Borrower '{borrower_id}' does not exist.")

        dispute_id = self._next_dispute_id()
        dispute = DisputeCase(
            dispute_id=dispute_id,
            borrower_id=borrower_id,
            target_record_id=target_record_id,
            target_record_type=target_record_type,
            contestation_reason=contestation_reason,
            supporting_evidence=supporting_evidence,
            status="OPEN",
        )
        self.disputes[dispute_id] = dispute

        # Record in data quality registry
        flagged = QualityFlaggedRecord(
            record_id=target_record_id,
            record_type="TRANSACTION" if "TX" in target_record_type else "DEFAULT_NOTICE",
            quality_status="DISPUTED",
            claimed_value="Contested by borrower",
            flagged_reason=contestation_reason,
            evidence_id=supporting_evidence.evidence_id,
        )
        self.quality_records.setdefault(borrower_id, []).append(flagged)

        # Append immutable audit event to ledger
        if getattr(self.engine, "ledger", None) is not None:
            self.engine.ledger.append_event(
                event_type="DISPUTE_FILED",
                actor_id=borrower_id,
                subject_id=borrower_id,
                delta_reputation=Decimal("0.0"),
                payload={
                    "dispute_id": dispute_id,
                    "target_record_id": target_record_id,
                    "target_record_type": target_record_type,
                    "reason": contestation_reason,
                },
                evidence=supporting_evidence,
            )

        return dispute

    def resolve_dispute(
        self,
        dispute_id: str,
        action: Literal["UPHELD", "REJECTED"],
        resolution_notes: str,
        resolving_officer: str,
        corrected_monthly_income: Optional[Decimal] = None,
        corrected_monthly_debt: Optional[Decimal] = None,
    ) -> DisputeCase:
        """Resolve a borrower dispute, update records, recompute scores, and commit ledger audit."""
        dispute = self.disputes.get(dispute_id)
        if not dispute:
            raise ValueError(f"Dispute '{dispute_id}' does not exist.")

        if dispute.status in ("RESOLVED_UPHELD", "RESOLVED_REJECTED"):
            raise ValueError(f"Dispute '{dispute_id}' is already closed with status '{dispute.status}'.")

        borrower = self.engine.get_user(dispute.borrower_id)
        if not borrower:
            raise ValueError(f"Borrower '{dispute.borrower_id}' does not exist.")

        # Snapshot baseline assessment
        baseline_assessment = self.scorer.assess_credit(dispute.borrower_id)
        recalc_impact: dict[str, str] = {}

        if action == "UPHELD":
            dispute.status = "RESOLVED_UPHELD"
            # Apply corrections to financial features
            ff = borrower.financial_features or FinancialFeatures(
                monthly_income=Decimal("35000.00"),
                monthly_debt=Decimal("0.00"),
                net_operating_income=Decimal("20000.00"),
                debt_service=Decimal("0.00"),
                completeness=Decimal("1.0"),
            )
            if corrected_monthly_income is not None:
                ff.monthly_income = corrected_monthly_income
                ff.net_operating_income = corrected_monthly_income * Decimal("0.65")
            if corrected_monthly_debt is not None:
                ff.monthly_debt = corrected_monthly_debt
                ff.debt_service = corrected_monthly_debt
            ff.completeness = Decimal("1.0")
            borrower.financial_features = ff

            # If user had been incorrectly DEFAULTED by this contested notice, reinstate to ACTIVE
            if borrower.status == "DEFAULTED" and "DEFAULT" in dispute.target_record_type:
                borrower.status = "ACTIVE"
                borrower.reputation = max(Decimal("0.0"), borrower.reputation + Decimal("10.0"))
                borrower.update_capacity()
                self.engine._sync_node_to_graph(borrower)

            # Recompute updated assessment
            new_assessment = self.scorer.assess_credit(dispute.borrower_id)
            recalc_impact = {
                "prior_credit_limit": f"INR {baseline_assessment.max_loan_limit:,.2f}",
                "updated_credit_limit": f"INR {new_assessment.max_loan_limit:,.2f}",
                "delta_limit": f"INR {new_assessment.max_loan_limit - baseline_assessment.max_loan_limit:,.2f}",
                "prior_lcb_score": str(baseline_assessment.score_final),
                "updated_lcb_score": str(new_assessment.score_final),
                "correction_applied": f"Income: {ff.monthly_income}, Debt: {ff.monthly_debt}",
            }
        else:
            dispute.status = "RESOLVED_REJECTED"
            recalc_impact = {"status": "Contestation rejected; no change to credit parameters."}

        dispute.resolved_at = datetime.now(timezone.utc)
        dispute.resolving_officer = resolving_officer
        dispute.resolution_summary = resolution_notes
        dispute.recalculation_impact = recalc_impact

        # Update quality records
        user_records = self.quality_records.get(dispute.borrower_id, [])
        for rec in user_records:
            if rec.record_id == dispute.target_record_id:
                rec.quality_status = "VERIFIED" if action == "UPHELD" else "DISPUTED"

        # Record resolution on append-only ledger
        if getattr(self.engine, "ledger", None) is not None:
            self.engine.ledger.append_event(
                event_type="DISPUTE_RESOLVED",
                actor_id=resolving_officer,
                subject_id=dispute.borrower_id,
                delta_reputation=Decimal("0.0"),
                payload={
                    "dispute_id": dispute_id,
                    "action": action,
                    "resolution_summary": resolution_notes,
                    "recalculation_impact": recalc_impact,
                },
                evidence=dispute.supporting_evidence,
            )

        return dispute

    def audit_evidence_quality(self, borrower_id: str) -> EvidenceQualityAudit:
        """Audit data quality tracking separately from economic credit capacity."""
        borrower = self.engine.get_user(borrower_id)
        if not borrower:
            raise ValueError(f"Borrower '{borrower_id}' does not exist.")

        user_disputes = [d for d in self.disputes.values() if d.borrower_id == borrower_id]
        open_disps = [d for d in user_disputes if d.status in ("OPEN", "UNDER_REVIEW")]
        resolved_disps = [d for d in user_disputes if d.status in ("RESOLVED_UPHELD", "RESOLVED_REJECTED")]

        user_flags = self.quality_records.get(borrower_id, [])
        n_stale = len([r for r in user_flags if r.quality_status == "STALE"])
        n_dup = len([r for r in user_flags if r.quality_status == "DUPLICATED"])
        n_missing = len([r for r in user_flags if r.quality_status == "MISSING"])
        n_disputed = len(open_disps)

        # Grade data quality
        if n_disputed > 0:
            grade = "DATA_QUALITY_CONTESTED"
        elif n_missing > 2:
            grade = "CRITICAL_DEFICIT"
        elif n_stale > 0 or n_missing > 0:
            grade = "PARTIAL_DISCLOSURE"
        else:
            grade = "HIGH_INTEGRITY"

        compliance_notes = [
            "Fair Credit Standard: Data quality flags strictly isolate epistemic documentation uncertainty from ability to pay.",
            "Recourse Guarantee: Borrowers retain active recourse rights with immutable recalculation audit trails.",
        ]
        if open_disps:
            compliance_notes.append(
                f"Active Recourse: {len(open_disps)} active contestation(s) currently open under audit."
            )

        return EvidenceQualityAudit(
            borrower_id=borrower_id,
            total_records_tracked=len(user_flags),
            verified_records_count=len([r for r in user_flags if r.quality_status == "VERIFIED"]),
            missing_records_count=n_missing,
            stale_records_count=n_stale,
            duplicated_records_count=n_dup,
            disputed_records_count=n_disputed,
            data_quality_grade=grade,
            flagged_records=user_flags,
            open_disputes=open_disps,
            resolved_disputes=resolved_disps,
            fair_credit_compliance_notes=compliance_notes,
        )
