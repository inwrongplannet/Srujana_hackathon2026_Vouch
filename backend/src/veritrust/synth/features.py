"""Stage 5: the model-ready row, computed only from what a lender can observe.

Why: the same function scores a training row and a demo persona, so the model never sees a
feature the live system could not compute. It never reads the truth table. Missing inputs stay
empty (never imputed) and every source keeps its reason code next to it.
DTI follows the finance-domain skill: monthly debt payments / monthly income (India's FOIR).
"""

from decimal import ROUND_HALF_UP, Decimal
from statistics import mean, median, pstdev

from . import params as P

RATIO = Decimal("0.0001")


def ratio(numerator: int | float | None, denominator: int | float | None) -> str:
    """Decimal ratio as a 4-dp string, or '' when it cannot be computed."""
    if numerator is None or denominator in (None, 0):
        return ""
    value = (Decimal(numerator) / Decimal(denominator)).quantize(RATIO, rounding=ROUND_HALF_UP)
    return str(value)


def _bank(months: list[dict]) -> dict:
    if not months:
        return {}
    incomes = [m["credits_minor"] - m["disbursal_credits_minor"] for m in months]
    mid = int(median(incomes))
    surplus = [m["credits_minor"] - m["disbursal_credits_minor"]
               - (m["debits_minor"] - m["emi_debits_minor"] - m["bounce_charges_minor"]) for m in months]
    out = {
        "bank_income_median_minor": mid,
        "bank_income_cv": ratio(pstdev(incomes), mean(incomes)) if mean(incomes) else "",
        "bank_zero_income_months": sum(1 for x in incomes if x < mid // 10),
        "bank_worst3_to_median": ratio(mean(sorted(incomes)[:3]), mid) if len(incomes) >= 3 else "",
        "bank_emi_recent_minor": int(median([m["emi_debits_minor"] for m in months[-3:]])),
        "bank_bounces": sum(m["emi_bounces"] for m in months),
        "bank_bounces_3m": sum(m["emi_bounces"] for m in months[-3:]),
        "bank_low_balance_months": sum(1 for m in months if m["closing_balance_minor"] < mid // 20),
        "bank_loan_disbursals_6m": sum(m["disbursal_count"] for m in months[-6:]),
        "bank_last_month_spike": ratio(incomes[-1], median(incomes[:-1])) if len(incomes) >= 2 else "",
        "bank_unreconciled_months": sum(
            1 for m in months
            if m["opening_balance_minor"] + m["credits_minor"] - m["debits_minor"] != m["closing_balance_minor"]),
        "bank_surplus_median_minor": int(median(surplus)),
    }
    return out


def _bureau(tradelines: list[dict], app_month: str) -> dict:
    if not tradelines:
        return {}
    year, month = int(app_month[:4]), int(app_month[5:])
    app_index = year * 12 + month - 1

    def index(label: str) -> int:
        return int(label[:4]) * 12 + int(label[5:]) - 1

    cells = [c for t in tradelines for c in t["dpd_grid"].split("|")]
    dpd = [int(c) for c in cells if c.isdigit()]
    active = [t for t in tradelines if t["status"] == "ACTIVE"]
    sanctioned = sum(t["sanctioned_minor"] for t in active)
    return {
        "bureau_tradelines": len(tradelines),
        "bureau_active": len(active),
        "bureau_history_months": app_index - min(index(t["opened_month"]) for t in tradelines),
        "bureau_max_dpd_24m": max(dpd) if dpd else 0,
        "bureau_months_30plus_24m": sum(1 for d in dpd if d >= 30),
        "bureau_reporting_gaps": sum(1 for c in cells if c == P.GRID_NOT_REPORTED),
        "bureau_new_6m": sum(1 for t in tradelines if app_index - index(t["opened_month"]) <= 6),
        "bureau_written_off": sum(1 for t in tradelines if t["status"] == "WRITTEN_OFF"),
        "bureau_emi_minor": sum(t["emi_minor"] for t in active),
        "bureau_outstanding_to_sanctioned": ratio(sum(t["outstanding_minor"] for t in active), sanctioned),
    }


def legacy_decision(app: dict, bureau: dict) -> tuple[str, str]:
    """A history-only policy: what a lender that trusts nothing but the bureau would decide."""
    if not bureau:
        return "REJECT", "NO_BUREAU_HISTORY"
    if bureau["bureau_max_dpd_24m"] >= 90:
        return "REJECT", "BUREAU_DELINQUENCY"
    income = app["declared_income_minor"]
    if income is None:
        return "REJECT", "INCOME_NOT_STATED"
    if Decimal(app["declared_emi_minor"] + app["new_emi_minor"]) / Decimal(income) > P.LEGACY_MAX_DTI:
        return "REJECT", "DTI_ABOVE_CAP"
    return "APPROVE", ""


def build_features(app: dict, months: list[dict], tradelines: list[dict], gst: list[dict],
                   vouches: list[dict]) -> dict:
    """One model row from the observed tables only."""
    bank = _bank(months)
    bureau = _bureau(tradelines, app["application_month"])
    declared_income = app["declared_income_minor"]
    bank_income = bank.get("bank_income_median_minor")

    if bank_income is not None and declared_income is not None:
        income_est, basis = min(bank_income, declared_income), "MIN_BANK_DECLARED"
    elif bank_income is not None:
        income_est, basis = bank_income, "BANK"
    elif declared_income is not None:
        income_est, basis = declared_income, "DECLARED"
    else:
        income_est, basis = None, "NONE"
    existing = max(app["declared_emi_minor"], bank.get("bank_emi_recent_minor", 0), bureau.get("bureau_emi_minor", 0))

    filed = [g["turnover_minor"] for g in gst if g["status"] == "FILED"]
    if not gst:
        gst_status = P.NOT_APPLICABLE
    elif len(filed) == len(gst):
        gst_status = P.OBSERVED
    else:
        gst_status = P.PARTIAL
    gst_median = int(median(filed)) if filed else None
    bank_credits_median = int(median([m["credits_minor"] for m in months])) if months else None

    tiers = [
        len(months) >= 6,
        bool(bureau) and bureau["bureau_history_months"] >= 6,
        gst_status in (P.OBSERVED, P.PARTIAL),
    ]
    on_time = [Decimal(v["voucher_on_time_share"]) for v in vouches]
    decision, reason = legacy_decision(app, bureau)

    row = {
        "borrower_id": app["borrower_id"],
        "application_month": app["application_month"],
        "occupation": app["occupation"], "state": app["state"], "urban": app["urban"],
        "age_band": app["age_band"], "dependents": app["dependents"], "product": app["product"],
        "requested_amount_minor": app["requested_amount_minor"], "tenure_months": app["tenure_months"],
        "rate_annual": app["rate_annual"], "new_emi_minor": app["new_emi_minor"],
        "declared_income_minor": "" if declared_income is None else declared_income,
        "declared_income_status": app["declared_income_status"],
        "declared_emi_minor": app["declared_emi_minor"],
        "occupation_tenure_months": "" if app["occupation_tenure_months"] is None else app["occupation_tenure_months"],
        "occupation_tenure_status": app["occupation_tenure_status"],
        "bank_statement_status": app["bank_statement_status"], "bank_statement_months": len(months),
        "bureau_status": P.OBSERVED if bureau else P.NO_RECORD,
        "gst_status": gst_status,
        "vouch_status": P.OBSERVED if vouches else P.NO_RECORD,
        "income_basis": basis,
        "income_est_minor": "" if income_est is None else income_est,
        "existing_emi_est_minor": existing,
        "dti_est": ratio(existing + app["new_emi_minor"], income_est),
        "amount_to_income": ratio(app["requested_amount_minor"], income_est),
        "declared_to_bank_income": ratio(declared_income, bank_income),
        "undeclared_emi_to_income": ratio(max(0, bank.get("bank_emi_recent_minor", 0) - app["declared_emi_minor"]), income_est)
        if bank else "",
        "gst_turnover_median_minor": "" if gst_median is None else gst_median,
        "gst_missed_filings": sum(1 for g in gst if g["status"] == "MISSED") if gst else "",
        "gst_to_bank_credits": ratio(gst_median, bank_credits_median) if gst_median is not None else "",
        "vouch_count": len(vouches),
        "vouch_mean_voucher_on_time": str((sum(on_time) / len(on_time)).quantize(Decimal("0.01"))) if on_time else "",
        "completeness_tier": sum(tiers),
        "legacy_decision": decision, "legacy_reason": reason,
    }
    for key in ("bank_income_median_minor", "bank_income_cv", "bank_zero_income_months",
                "bank_worst3_to_median", "bank_emi_recent_minor", "bank_bounces", "bank_bounces_3m",
                "bank_low_balance_months", "bank_loan_disbursals_6m", "bank_last_month_spike",
                "bank_unreconciled_months", "bank_surplus_median_minor"):
        row[key] = bank.get(key, "")
    for key in ("bureau_tradelines", "bureau_active", "bureau_history_months", "bureau_max_dpd_24m",
                "bureau_months_30plus_24m", "bureau_reporting_gaps", "bureau_new_6m",
                "bureau_written_off", "bureau_emi_minor", "bureau_outstanding_to_sanctioned"):
        row[key] = bureau.get(key, "")
    return row
