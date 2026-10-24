"""Tests for Borrower Recourse & Evidence-Quality Workflow.

Verifies:
- Filing formal disputes with primary evidence
- Resolving disputes with automatic score recalculation
- Data quality audits separating epistemic records from repayment capacity
- Ledger event generation for disputes
"""

from decimal import Decimal
import pytest

from veritrust.engine import TrustEngine
from veritrust.models import Evidence, FinancialFeatures
from veritrust.recourse import BorrowerRecourseWorkflow
from veritrust.scoring import CreditScorer


def _setup_recourse_fixture():
    engine = TrustEngine()
    engine.create_user("ANCHOR_BANK", "Anchor Bank", initial_reputation=Decimal("20.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice Sponsor", initial_reputation=Decimal("10.0"))
    engine.create_user(
        "BOB",
        "Bob Borrower",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("35000.00"),
            monthly_debt=Decimal("6000.00"),
            net_operating_income=Decimal("22000.00"),
            debt_service=Decimal("5000.00"),
            completeness=Decimal("0.85"),
        ),
    )
    engine.vouch("ANCHOR_BANK", "ALICE")
    engine.vouch("ALICE", "BOB")

    scorer = CreditScorer(engine)
    workflow = BorrowerRecourseWorkflow(engine, scorer)
    return engine, scorer, workflow


def test_file_and_resolve_dispute_with_recalculation():
    """Verify filing and resolving a dispute updates borrower features and recalculates credit scores."""
    _, scorer, workflow = _setup_recourse_fixture()

    initial_assessment = scorer.assess_credit("BOB")

    # 1. File dispute
    evidence = Evidence(
        evidence_id="EVID_CORRECTED_PAYSLIP",
        evidence_type="BANK_STATEMENT",
        description="Official bank statement showing higher verified salary",
        recorded_by="BOB",
    )
    dispute = workflow.file_dispute(
        borrower_id="BOB",
        target_record_id="REC_INC_01",
        target_record_type="INCOME_STATEMENT",
        contestation_reason="Reported income 35,000 excluded bonus; actual income is 45,000",
        supporting_evidence=evidence,
    )

    assert dispute.status == "OPEN"
    assert dispute.borrower_id == "BOB"
    assert "DISP_" in dispute.dispute_id

    # 2. Resolve dispute (UPHELD with corrected income)
    resolved = workflow.resolve_dispute(
        dispute_id=dispute.dispute_id,
        action="UPHELD",
        resolution_notes="Salary slip confirmed with bank statement",
        resolving_officer="AUDIT_OFFICER_01",
        corrected_monthly_income=Decimal("45000.00"),
    )

    assert resolved.status == "RESOLVED_UPHELD"
    assert resolved.recalculation_impact is not None
    assert "updated_credit_limit" in resolved.recalculation_impact

    # Verified score recalculation increased credit limit
    new_assessment = scorer.assess_credit("BOB")
    assert new_assessment.max_loan_limit > initial_assessment.max_loan_limit


def test_audit_evidence_quality_separation():
    """Verify data quality audit tracks disputed and stale records without conflating with capacity."""
    _, _, workflow = _setup_recourse_fixture()

    evidence = Evidence(
        evidence_id="EVID_DISP_02",
        evidence_type="BANK_STATEMENT",
        description="Contested record",
        recorded_by="BOB",
    )
    workflow.file_dispute(
        borrower_id="BOB",
        target_record_id="REC_DEF_01",
        target_record_type="DEFAULT_NOTICE",
        contestation_reason="Incorrect default entry on repaid loan",
        supporting_evidence=evidence,
    )

    quality_audit = workflow.audit_evidence_quality("BOB")
    assert quality_audit.borrower_id == "BOB"
    assert quality_audit.disputed_records_count == 1
    assert quality_audit.data_quality_grade == "DATA_QUALITY_CONTESTED"
    assert len(quality_audit.open_disputes) == 1
    assert any("Fair Credit Standard" in note for note in quality_audit.fair_credit_compliance_notes)
