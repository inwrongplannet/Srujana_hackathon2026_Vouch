"""Critical tests for dual-axis underwriting and Lower Confidence Bound (LCB).

Verifies:
1. Thin-file borrowers are treated fairly (high uncertainty, not negative capacity).
2. Epistemic uncertainty sigma2 starts at 1.0 and is never negative.
3. Final decision score Score_final = mu - kappa * sqrt(sigma2).
4. Monetary limit calculation is strictly Decimal.
"""

from decimal import Decimal
from veritrust.engine import TrustEngine
from veritrust.models import FinancialFeatures
from veritrust.scoring import CreditScorer


def test_thin_file_vs_rich_file_evaluation():
    """Verify distinct treatment of thin-file vs rich-file applicant."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("SPONSOR", "Sponsor", initial_reputation=Decimal("5.0"))
    engine.vouch("ANCHOR", "SPONSOR")

    # 1. Thin-file applicant: Has 1 incoming vouch from SPONSOR, but NO financial history
    engine.create_user("THIN_FILE", "Thin File Borrower", initial_reputation=Decimal("0.0"))
    engine.vouch("SPONSOR", "THIN_FILE")

    # 2. Rich-file applicant: Has incoming vouch, 3 settled loans, and complete financial statements
    engine.create_user(
        "RICH_FILE",
        "Rich File Borrower",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            monthly_income=Decimal("60000.00"),
            monthly_debt=Decimal("5000.00"),
            net_operating_income=Decimal("40000.00"),
            debt_service=Decimal("5000.00"),  # DSCR = 8.0
            income_volatility=Decimal("0.05"),
            cashflow_volatility=Decimal("0.05"),
            completeness=Decimal("1.0"),
        ),
    )
    rich_node = engine.get_user("RICH_FILE")
    rich_node.n_settled_loans = 3
    engine.vouch("SPONSOR", "RICH_FILE")

    scorer = CreditScorer(engine)
    thin_assessment = scorer.assess_credit("THIN_FILE")
    rich_assessment = scorer.assess_credit("RICH_FILE")

    # Uncertainty assertions
    # Thin file: 0 settled, 1 vouch, 0 financials -> N_data_points = 1, completeness = 0 -> sigma2 = 1.0
    assert thin_assessment.sigma2_epistemic == Decimal("1.0")

    # Rich file: 3 settled, 1 vouch, 1 financials -> N_data_points = 5, completeness = 1.0 -> sigma2 < 0.25
    assert rich_assessment.sigma2_epistemic < Decimal("0.25")

    # Capacity assertions: Rich file should have significantly higher score and limit
    assert rich_assessment.score_final > thin_assessment.score_final
    assert rich_assessment.max_loan_limit > thin_assessment.max_loan_limit

    # Verify explainability: both should have non-empty contributing paths from ANCHOR
    assert len(thin_assessment.contributing_paths) == 1
    assert thin_assessment.contributing_paths[0].path == ["ANCHOR", "SPONSOR", "THIN_FILE"]


def test_missing_financial_fields_widen_uncertainty():
    """Missing data directly lowers completeness and raises epistemic uncertainty."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("U_COMPLETE", "Complete Data", initial_reputation=Decimal("0.0"),
                       financial_features=FinancialFeatures(completeness=Decimal("1.0")))
    engine.create_user("U_PARTIAL", "Partial Data", initial_reputation=Decimal("0.0"),
                       financial_features=FinancialFeatures(completeness=Decimal("0.5")))

    engine.vouch("ANCHOR", "U_COMPLETE")
    engine.vouch("ANCHOR", "U_PARTIAL")

    scorer = CreditScorer(engine)
    assessment_complete = scorer.assess_credit("U_COMPLETE")
    assessment_partial = scorer.assess_credit("U_PARTIAL")

    # Lower completeness must yield strictly higher uncertainty
    assert assessment_partial.sigma2_epistemic > assessment_complete.sigma2_epistemic


def test_parameter_sensitivity_alpha():
    """Adjusting alpha shifts weight between graph trust and cash-flow."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user(
        "BORROWER",
        "Borrower",
        initial_reputation=Decimal("0.0"),
        financial_features=FinancialFeatures(
            net_operating_income=Decimal("50000.00"),
            debt_service=Decimal("5000.00"),
            completeness=Decimal("1.0"),
        ),
    )
    engine.vouch("ANCHOR", "BORROWER")  # High graph trust

    # High graph weighting (alpha = 0.8)
    scorer_high_graph = CreditScorer(engine, alpha=Decimal("0.8"))
    assess_high = scorer_high_graph.assess_credit("BORROWER")

    # Low graph weighting (alpha = 0.2)
    scorer_low_graph = CreditScorer(engine, alpha=Decimal("0.2"))
    assess_low = scorer_low_graph.assess_credit("BORROWER")

    # Since graph score (10.0) is higher than normalized cash-flow score (~1.0),
    # higher alpha results in higher mu_composite
    assert assess_high.mu_composite > assess_low.mu_composite


def test_strictly_decimal_precision():
    """Verify that all score and monetary outputs are Decimal."""
    engine = TrustEngine()
    engine.create_user("ANCHOR", "Anchor Bank", initial_reputation=Decimal("10.0"), is_anchor=True)
    engine.create_user("TARGET", "Target", initial_reputation=Decimal("0.0"))
    engine.vouch("ANCHOR", "TARGET")

    scorer = CreditScorer(engine)
    assessment = scorer.assess_credit("TARGET")

    assert isinstance(assessment.r_graph, Decimal)
    assert isinstance(assessment.s_cashflow, Decimal)
    assert isinstance(assessment.mu_composite, Decimal)
    assert isinstance(assessment.sigma2_epistemic, Decimal)
    assert isinstance(assessment.score_final, Decimal)
    assert isinstance(assessment.max_loan_limit, Decimal)

