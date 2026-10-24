"""Synthetic dataset generator: known-answer money maths, determinism and self-consistency."""

from decimal import Decimal

import pytest

from veritrust.synth import params as P
from veritrust.synth.generate import generate_one
from veritrust.synth.money import emi, outstanding, principal_for_emi, scale
from veritrust.synth.transactions import extract_months

RUPEE = 100


def test_emi_known_answer():
    # ₹1,00,000 at 12% a year for 12 months: EMI ₹8,884.88 (standard amortization table).
    assert emi(100_000 * RUPEE, Decimal("0.12"), 12) == 888_488


def test_emi_zero_rate_is_straight_line():
    assert emi(120_000 * RUPEE, Decimal("0"), 12) == 10_000 * RUPEE


def test_outstanding_known_answer():
    # Same loan after 6 payments: ₹51,492.11 by a period-by-period table; the schedule uses the
    # EMI already rounded to ₹8,884.88, which leaves ₹51,492.10.
    assert outstanding(100_000 * RUPEE, Decimal("0.12"), 12, 6) == 5_149_210
    assert outstanding(100_000 * RUPEE, Decimal("0.12"), 12, 0) == 100_000 * RUPEE
    assert outstanding(100_000 * RUPEE, Decimal("0.12"), 12, 12) == 0


def test_principal_for_emi_inverts_emi():
    principal = principal_for_emi(888_488, Decimal("0.12"), 12)
    assert abs(principal - 100_000 * RUPEE) <= 1


def test_scale_quantizes_to_paise_and_never_goes_negative():
    assert scale(1_001, 0.5) == 501          # half-up
    assert scale(10_000, -0.3) == 0


@pytest.fixture(scope="module")
def borrowers():
    return [generate_one(i, with_transactions=True) for i in range(1, 61)]


def test_generation_is_deterministic(borrowers):
    assert generate_one(7, with_transactions=True) == borrowers[6]


def test_money_columns_are_integers(borrowers):
    for rows in borrowers:
        for table in ("applications", "monthly_cashflow", "bureau_tradelines", "transactions"):
            for row in rows[table]:
                for key, value in row.items():
                    if key.endswith("_minor") and value is not None:
                        assert isinstance(value, int), (table, key, value)


def test_every_gap_has_a_reason_code(borrowers):
    for rows in borrowers:
        app = rows["applications"][0]
        for key in ("declared_income_status", "occupation_tenure_status", "bank_statement_status"):
            assert app[key] in P.STATUSES
        if app["declared_income_status"] == P.WITHHELD:
            assert app["declared_income_minor"] is None
        feat = rows["features"][0]
        assert feat["bureau_status"] in P.STATUSES and feat["gst_status"] in P.STATUSES


def test_extractor_reproduces_monthly_table(borrowers):
    checked = 0
    for rows in borrowers:
        if not rows["transactions"]:
            continue
        extracted = extract_months(rows["transactions"])
        for month in rows["monthly_cashflow"]:
            got = extracted[month["month"]]
            for key, value in got.items():
                assert value == month[key], (month["borrower_id"], month["month"], key)
            checked += 1
    assert checked > 50


def test_statement_balance_never_negative_and_closes_true(borrowers):
    for rows in borrowers:
        for txn in rows["transactions"]:
            assert txn["balance_minor"] >= 0
        closing = {m["month"]: m["closing_balance_minor"] for m in rows["monthly_cashflow"]}
        last = {}
        for txn in rows["transactions"]:
            last[txn["date"][:7]] = txn["balance_minor"]
        for month, value in last.items():
            assert value == closing[month]


def test_bureau_grid_covers_24_months(borrowers):
    for rows in borrowers:
        for t in rows["bureau_tradelines"]:
            assert len(t["dpd_grid"].split("|")) == P.HISTORY_MONTHS


def test_default_falls_after_the_application(borrowers):
    for rows in borrowers:
        outcome, app = rows["outcomes"][0], rows["applications"][0]
        if outcome["default_12m"]:
            assert outcome["default_month"] > app["application_month"]
            assert outcome["max_dpd_12m"] >= P.DEFAULT_ARREARS * 30


def test_features_never_read_the_truth_table(borrowers):
    truth_only = {"discipline", "stacker", "inflator", "true_dti_with_new", "default_driver", "expense_ratio"}
    for rows in borrowers:
        assert not truth_only & set(rows["features"][0])
