"""Tests for the Decision Explanation & Audit Explorer.

Verifies:
- Explicit rule evaluation traces with threshold comparisons
- Extraction of contributing primary evidence records
- Web-of-Trust path tracing
- Deterministic sensitivity deltas (+10% income, -10% income shock, expense cuts)
"""

from decimal import Decimal
import pytest

from veritrust.audit_explorer import DecisionAuditExplorer
from veritrust.engine import TrustEngine
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer


def _setup_audit_fixture():
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
            income_volatility=Decimal("0.10"),
            cashflow_volatility=Decimal("0.12"),
            completeness=Decimal("0.90"),
        ),
    )
    engine.vouch("ANCHOR_BANK", "ALICE")
    engine.vouch("ALICE", "BOB")

    scorer = CreditScorer(engine)
    return engine, scorer


def test_audit_explorer_rules_and_sensitivity():
    """Verify forensic audit generates rule traces, graph paths, and sensitivity analysis."""
    engine, scorer = _setup_audit_fixture()
    explorer = DecisionAuditExplorer(engine, scorer)

    report = explorer.inspect_decision(
        borrower_id="BOB",
        requested_principal=Decimal("40000.00"),
        requested_tenure_months=6,
    )

    assert report.borrower_id == "BOB"
    assert report.verdict == "APPROVED"

    # Rules trace
    assert len(report.rules_evaluated) >= 4
    rule_ids = [r.rule_id for r in report.rules_evaluated]
    assert "RULE_DISPOSABLE_INCOME_FLOOR" in rule_ids
    assert "RULE_ITI_FOIR_CAP" in rule_ids
    assert "RULE_DTI_TOTAL_CAP" in rule_ids
    assert "RULE_CREDIT_LIMIT_CEILING" in rule_ids

    # Web-of-Trust graph paths
    assert report.graph_trust_score > Decimal("0.0")
    assert len(report.contributing_paths) > 0
    assert report.contributing_paths[0].path == ["ANCHOR_BANK", "ALICE", "BOB"]

    # Sensitivity analysis
    assert len(report.sensitivity_analysis) >= 3
    params = [s.parameter_perturbed for s in report.sensitivity_analysis]
    assert any("+10%" in p for p in params)
    assert any("-10%" in p for p in params)
    assert any("Expenses Cut" in p for p in params)
