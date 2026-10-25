"""Unit tests for VeriTrust domain models."""

from decimal import Decimal
import pytest
from veritrust.models import FinancialFeatures, Loan, Transaction, User, Vouch


def test_user_capacity_sync():
    """Verify capacity syncs with reputation and respects ACTIVE status."""
    user = User(user_id="U1", name="Test User", reputation=Decimal("15.5"))
    user.update_capacity()
    assert user.capacity == Decimal("15.5")

    # Negative reputation yields zero capacity
    user.reputation = Decimal("-5.0")
    user.update_capacity()
    assert user.capacity == Decimal("0.0")

    # Inactive status freezes capacity even if R > 0
    user.reputation = Decimal("10.0")
    user.status = "DEFAULTED"
    user.update_capacity()
    assert user.capacity == Decimal("0.0")


def test_decimal_coercion():
    """Verify that strings and integers are coerced strictly to Decimal."""
    ff = FinancialFeatures(
        monthly_income="25000",
        monthly_debt=5000,
        completeness="0.85",
    )
    assert isinstance(ff.monthly_income, Decimal)
    assert ff.monthly_income == Decimal("25000")
    assert isinstance(ff.monthly_debt, Decimal)
    assert ff.monthly_debt == Decimal("5000")
    assert isinstance(ff.completeness, Decimal)
    assert ff.completeness == Decimal("0.85")


def test_loan_and_transaction():
    """Verify Loan and Transaction validation and initial state."""
    loan = Loan(
        loan_id="L1",
        borrower_id="U1",
        principal=Decimal("50000.00"),
        outstanding_balance=Decimal("50000.00"),
        interest_rate=Decimal("0.12"),
    )
    assert loan.status == "ACTIVE"
    assert loan.principal == Decimal("50000.00")

    tx = Transaction(
        tx_id="TX1",
        user_id="U1",
        amount=Decimal("10000.00"),
        tx_type="DISBURSEMENT",
    )
    assert tx.currency == "INR"
    assert tx.amount == Decimal("10000.00")

