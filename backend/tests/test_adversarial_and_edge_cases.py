"""Adversarial, boundary, and genuine integration tests for VeriTrust.

Hammers the engine with absurd and extreme inputs to guarantee robustness:
1. Massive over-repayment (e.g. paying 1,500,000 on a 25,000 loan)
2. Negative and zero repayments
3. Consecutive lending spam (ID collision prevention and cumulative debt limit ceiling)
4. Counter synchronization across restarts
5. Absurd tenure requests (e.g. 67 months) and explainer narrative sanity
6. Giant principal requests violating both credit ceiling and repayment budget
7. Insolvent profiles with negative disposable income
8. Genuine multi-step partial repayments and settlement transitions
9. Attempting to repay defaulted loans or double-default
"""

from decimal import Decimal
import pytest

from veritrust.affordability import AffordabilityEngine, AffordabilityInput
from veritrust.engine import TrustEngine
from veritrust.explainer import ExplanationEngine
from veritrust.lending import LendingService
from veritrust.models import FinancialFeatures
from veritrust.optimizer import LoanOptimizer
from veritrust.scoring import CreditScorer
from veritrust.stress_tester import MonteCarloStressTester


def _build_test_network():
    """Build root anchor -> Alice -> Bob topology."""
    engine = TrustEngine()
    engine.create_user("ANCHOR_BANK", "Anchor Bank", initial_reputation=Decimal("20.0"), is_anchor=True)
    engine.create_user("ALICE", "Alice Leader", initial_reputation=Decimal("10.0"))
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
    lending = LendingService(engine, scorer)
    return engine, scorer, lending


def test_absurd_massive_overpayment_capped_to_debt():
    """An absurd payment (₹1,500,000 on a ₹25,000 loan) must cap payment, not go negative,
    and prevent inflated reputation minting.
    """
    engine, _, lending = _build_test_network()
    loan = lending.borrow("BOB", Decimal("25000.00"))
    assert loan.outstanding_balance == Decimal("25000.00")

    bob_before = engine.get_user("BOB")
    initial_rep = bob_before.reputation

    # Submit absurd repayment of 1.5 million
    repaid_loan = lending.repay(loan.loan_id, Decimal("1500000.00"))

    # Balance must be exactly 0.00, never negative
    assert repaid_loan.outstanding_balance == Decimal("0.00")
    assert repaid_loan.status == "REPAID"

    # Transaction log must record the capped actual payment (25,000), NOT 1.5 million
    last_tx = lending.transactions[-1]
    assert last_tx.amount == Decimal("25000.00")

    # Reputation reward must be awarded exactly once (standard reward of +2.0)
    bob_after = engine.get_user("BOB")
    assert bob_after.reputation == initial_rep + lending.borrower_reward
    assert bob_after.n_settled_loans == 1

    # Subsequent repayment attempt on the settled loan must fail
    with pytest.raises(ValueError, match="Cannot repay loan '.*' with status 'REPAID'"):
        lending.repay(loan.loan_id, Decimal("100.00"))


def test_absurd_zero_and_negative_repayments():
    """Zero or negative repayments must be rejected immediately."""
    _, _, lending = _build_test_network()
    loan = lending.borrow("BOB", Decimal("10000.00"))

    with pytest.raises(ValueError, match="Repayment amount must be positive"):
        lending.repay(loan.loan_id, Decimal("0.00"))

    with pytest.raises(ValueError, match="Repayment amount must be positive"):
        lending.repay(loan.loan_id, Decimal("-5000.00"))

    # Balance remains intact
    assert loan.outstanding_balance == Decimal("10000.00")
    assert loan.status == "ACTIVE"


def test_absurd_negative_or_zero_borrow_amount():
    """Borrowing zero or negative amounts must be rejected."""
    _, _, lending = _build_test_network()

    with pytest.raises(ValueError, match="Loan amount must be positive"):
        lending.borrow("BOB", Decimal("0.00"))

    with pytest.raises(ValueError, match="Loan amount must be positive"):
        lending.borrow("BOB", Decimal("-1000.00"))

    with pytest.raises(ValueError, match="Loan tenure must be positive"):
        lending.borrow("BOB", Decimal("5000.00"), tenure_months=0)


def test_lending_spam_unique_ids_and_cumulative_limit_exhaustion():
    """Calling lend/borrow repeatedly must generate unique sequential IDs
    and enforce cumulative debt limits across all active contracts.
    """
    engine, scorer, lending = _build_test_network()
    assessment = scorer.assess_credit("BOB")
    max_limit = assessment.max_loan_limit

    # Step 1: Issue three 5,000 INR loans
    loan1 = lending.lend("ALICE", "BOB", Decimal("5000.00"))
    loan2 = lending.lend("ALICE", "BOB", Decimal("5000.00"))
    loan3 = lending.lend("ALICE", "BOB", Decimal("5000.00"))

    # IDs must be strictly unique, no clobbering!
    assert loan1.loan_id == "LN_00001"
    assert loan2.loan_id == "LN_00002"
    assert loan3.loan_id == "LN_00003"
    assert len(lending.loans) == 3

    # Step 2: Cumulative active debt is 15,000 INR
    active_debt = sum(l.outstanding_balance for l in lending.loans.values() if l.status == "ACTIVE")
    assert active_debt == Decimal("15000.00")

    # Step 3: Try to borrow more than remaining credit limit
    excess = max_limit - active_debt + Decimal("1000.00")
    with pytest.raises(ValueError, match="exceeds approved credit limit"):
        lending.borrow("BOB", excess)


def test_counter_sync_after_persistence_reload():
    """Verify counters sync properly so reloaded instances never generate duplicate LN_ IDs."""
    engine, scorer, lending = _build_test_network()

    # Pre-populate loans
    lending.borrow("BOB", Decimal("2000.00"))
    lending.borrow("BOB", Decimal("3000.00"))
    assert "LN_00001" in lending.loans
    assert "LN_00002" in lending.loans

    # Create fresh service mimicking process restart
    fresh_lending = LendingService(engine, scorer)
    # Simulate loading from disk
    fresh_lending.loans = dict(lending.loans)
    fresh_lending.transactions = list(lending.transactions)
    fresh_lending.sync_counters()

    # Next generated ID must be LN_00003
    loan3 = fresh_lending.borrow("BOB", Decimal("1000.00"))
    assert loan3.loan_id == "LN_00003"
    assert len(fresh_lending.loans) == 3


def test_absurd_tenure_optimizer_and_explainer_sanity():
    """Verify optimizer and explainer handle unconventional requested tenures (e.g. 67 months)
    without producing negative budget excess or inverted directional verbs.
    """
    engine, scorer, _ = _build_test_network()
    afford_engine = AffordabilityEngine()
    optimizer = LoanOptimizer(afford_engine)
    tester = MonteCarloStressTester()
    explainer = ExplanationEngine()

    data = AffordabilityInput(
        monthly_income=Decimal("35000.00"),
        essential_expenses=Decimal("13000.00"),
        existing_debt_service=Decimal("6000.00"),
        data_completeness=Decimal("0.90"),
        is_verified=True,
    )
    afford_res = afford_engine.evaluate(data)

    # Bob requests 500,000 for 67 months, with credit limit capped at 329,338.90
    opt_res = optimizer.optimize(
        affordability_input=data,
        requested_principal=Decimal("500000.00"),
        requested_tenure_months=67,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("329338.90"),
        objective="MIN_COST",
    )

    plan = opt_res.best_feasible_alternative or opt_res.original_request
    stress_res = tester.stress_test(
        monthly_income=Decimal("35000.00"),
        essential_expenses=Decimal("19000.00"),
        monthly_emi=plan.monthly_emi,
        tenure_months=plan.tenure_months,
        initial_cash_buffer=afford_res.effective_buffer,
    )

    assessment = scorer.assess_credit("BOB")
    exp = explainer.explain(
        affordability=afford_res,
        optimization=opt_res,
        stress_test=stress_res,
        credit_assessment=assessment,
    )

    # Assert sanity of executive summary:
    summary = exp.narrative_summary
    # 1. Never produce negative excess "exceeds repayment budget by INR -"
    assert "INR -" not in summary
    # 2. Never say "Extending the tenure from 67 to 36" (67 to 36 is shortening!)
    assert "Extending the tenure from 67 to" not in summary
    # 3. Explainer correctly identified principal exceeded limit
    assert "exceeds the approved borrowing limit" in summary
    # 4. Financial capacity headline does not falsely claim "EXCEEDS_REPAYMENT_BUDGET" if EMI is affordable
    if opt_res.original_request.monthly_emi <= afford_res.max_affordable_emi:
        assert exp.dimension_financial_capacity.status == "WITHIN_INSTALMENT_BUDGET"


def test_absurd_giant_principal_optimizer_dual_infeasibility():
    """Borrower requesting an impossible principal (₹10,000,000 on ₹35,000 income)."""
    engine, scorer, _ = _build_test_network()
    afford_engine = AffordabilityEngine()
    optimizer = LoanOptimizer(afford_engine)
    explainer = ExplanationEngine()
    tester = MonteCarloStressTester()

    data = AffordabilityInput(
        monthly_income=Decimal("35000.00"),
        essential_expenses=Decimal("13000.00"),
        existing_debt_service=Decimal("6000.00"),
        data_completeness=Decimal("0.90"),
        is_verified=True,
    )
    afford_res = afford_engine.evaluate(data)

    opt_res = optimizer.optimize(
        affordability_input=data,
        requested_principal=Decimal("10000000.00"),
        requested_tenure_months=3,
        annual_rate=Decimal("0.10"),
        max_approved_credit_limit=Decimal("300000.00"),
        objective="MIN_COST",
    )

    assert opt_res.is_original_feasible is False
    assert len(opt_res.original_request.infeasibility_reasons) >= 2

    # Best alternative must scale down to approved limit (300,000) and affordable EMI
    best = opt_res.best_feasible_alternative
    assert best is not None
    assert best.principal <= Decimal("300000.00")
    assert best.monthly_emi <= afford_res.max_affordable_emi

    stress_res = tester.stress_test(
        monthly_income=Decimal("35000.00"),
        essential_expenses=Decimal("19000.00"),
        monthly_emi=best.monthly_emi,
        tenure_months=best.tenure_months,
    )

    exp = explainer.explain(
        affordability=afford_res,
        optimization=opt_res,
        stress_test=stress_res,
    )

    assert exp.verdict == "RESTRUCTURED_ALTERNATIVE"
    assert "exceeds the approved borrowing limit" in exp.narrative_summary
    assert "exceeds the repayment budget" in exp.narrative_summary


def test_absurd_negative_disposable_income_insolvency():
    """When expenses exceed income, disposable income D < 0. No loan may be granted."""
    afford_engine = AffordabilityEngine()
    optimizer = LoanOptimizer(afford_engine)
    tester = MonteCarloStressTester()
    explainer = ExplanationEngine()

    bankrupt_input = AffordabilityInput(
        monthly_income=Decimal("20000.00"),
        essential_expenses=Decimal("22000.00"),  # Expenses exceed income!
        existing_debt_service=Decimal("5000.00"),
        data_completeness=Decimal("1.00"),
        is_verified=True,
    )
    afford_res = afford_engine.evaluate(bankrupt_input)

    assert afford_res.is_affordable is False
    assert afford_res.max_affordable_emi == Decimal("0.00")
    assert afford_res.disposable_income < Decimal("0.00")

    opt_res = optimizer.optimize(
        affordability_input=bankrupt_input,
        requested_principal=Decimal("5000.00"),
        requested_tenure_months=6,
    )

    assert opt_res.is_original_feasible is False
    assert opt_res.best_feasible_alternative is None
    assert len(opt_res.feasible_options) == 0

    stress_res = tester.stress_test(
        monthly_income=Decimal("20000.00"),
        essential_expenses=Decimal("27000.00"),
        monthly_emi=Decimal("0.00"),
        tenure_months=6,
        initial_cash_buffer=Decimal("0.00"),
    )

    exp = explainer.explain(
        affordability=afford_res,
        optimization=opt_res,
        stress_test=stress_res,
    )

    assert exp.verdict == "REJECTED_UNAFFORDABLE"
    assert "unaffordable under current policy rules" in exp.narrative_summary


def test_genuine_multi_step_partial_repayments():
    """Genuine path: borrower makes 3 partial payments settling the debt incrementally."""
    engine, _, lending = _build_test_network()
    loan = lending.borrow("BOB", Decimal("20000.00"))
    bob = engine.get_user("BOB")
    init_rep = bob.reputation

    # Payment 1: 5,000
    lending.repay(loan.loan_id, Decimal("5000.00"))
    assert loan.outstanding_balance == Decimal("15000.00")
    assert loan.status == "ACTIVE"
    assert bob.reputation == init_rep

    # Payment 2: 5,000
    lending.repay(loan.loan_id, Decimal("5000.00"))
    assert loan.outstanding_balance == Decimal("10000.00")
    assert loan.status == "ACTIVE"

    # Payment 3: final 10,000 settling loan
    lending.repay(loan.loan_id, Decimal("10000.00"))
    assert loan.outstanding_balance == Decimal("0.00")
    assert loan.status == "REPAID"
    assert bob.reputation == init_rep + lending.borrower_reward
    assert bob.n_settled_loans == 1


def test_genuine_default_cannot_be_repaid_or_double_defaulted():
    """Defaulted loans are frozen: cannot be repaid and cannot be defaulted again."""
    _, _, lending = _build_test_network()
    loan = lending.borrow("BOB", Decimal("10000.00"))

    lending.default_loan(loan.loan_id)
    assert loan.status == "DEFAULTED"

    # Cannot repay defaulted loan
    with pytest.raises(ValueError, match="Cannot repay loan '.*' with status 'DEFAULTED'"):
        lending.repay(loan.loan_id, Decimal("5000.00"))

    # Cannot default again
    with pytest.raises(ValueError, match="Cannot default loan '.*' with status 'DEFAULTED'"):
        lending.default_loan(loan.loan_id)
