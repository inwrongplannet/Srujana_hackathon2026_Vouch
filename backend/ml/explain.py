"""Turn model output into evidence-backed reasons.

Why this exists: the design document forbids a black box and forbids an LLM
inventing causes. Every sentence here comes from a column that exists, with the
observed value, its direction from the model, and whether the field is missing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# feature -> (reason code, human text, unit formatter)
REASON_CODES: dict[str, tuple[str, str, str]] = {
    "dti_est": ("DTI_ABOVE_CAP", "Debt-to-income after the new EMI", "ratio"),
    "amount_to_income": ("AMOUNT_TO_INCOME_HIGH", "Requested amount relative to income", "ratio"),
    "income_est_minor": ("INCOME_LEVEL", "Estimated monthly income", "money"),
    "bank_surplus_median_minor": ("MONTHLY_SURPLUS", "Median monthly surplus before EMIs", "money"),
    "bank_income_cv": ("INCOME_UNSTABLE", "Month-to-month income variation", "ratio"),
    "bank_zero_income_months": ("ZERO_INCOME_MONTHS", "Months with no income credit", "count"),
    "bank_worst3_to_median": ("WORST_MONTHS", "Three worst months versus the median", "ratio"),
    "bank_bounces_3m": ("EMI_BOUNCE", "Bounced auto-debits in the last 3 months", "count"),
    "bank_bounces": ("EMI_BOUNCE_HISTORY", "Bounced auto-debits in 12 months", "count"),
    "bank_low_balance_months": ("LOW_BUFFER", "Months ending with a near-empty balance", "count"),
    "bank_loan_disbursals_6m": ("NEW_LOANS_6M", "New loans credited in 6 months", "count"),
    "bank_last_month_spike": ("WINDOW_DRESSING_SUSPECT", "Last-month credits versus median", "ratio"),
    "bank_unreconciled_months": ("DUPLICATE_ROWS", "Months whose balance does not reconcile", "count"),
    "undeclared_emi_to_income": ("UNDECLARED_EMI", "EMIs in the statement but not on the form", "ratio"),
    "declared_to_bank_income": ("INCOME_INCONSISTENT", "Declared income versus bank credits", "ratio"),
    "bureau_max_dpd_24m": ("BUREAU_DELINQUENCY", "Worst days past due in 24 months", "days"),
    "bureau_months_30plus_24m": ("BUREAU_30PLUS", "Months 30+ days overdue in 24 months", "count"),
    "bureau_new_6m": ("BUREAU_NEW_CREDIT", "New credit lines in 6 months", "count"),
    "bureau_written_off": ("BUREAU_WRITE_OFF", "Written-off accounts", "count"),
    "bureau_outstanding_to_sanctioned": ("BUREAU_UTILISATION", "Outstanding to sanctioned share", "ratio"),
    "bureau_history_months": ("BUREAU_HISTORY", "Bureau history length", "months"),
    "completeness_tier": ("DATA_COMPLETENESS", "Independent verified sources", "count"),
    "gst_missed_filings": ("GST_MISSED", "Missed GST filings", "count"),
    "gst_to_bank_credits": ("GST_INCONSISTENT", "GST turnover versus bank credits", "ratio"),
    "vouch_count": ("VOUCH_PRESENT", "Community vouches", "count"),
    "vouch_mean_voucher_on_time": ("VOUCHER_QUALITY", "Vouchers' own on-time record", "ratio"),
    "hc_late_share_12m": ("LENDER_LATE", "Late instalments with this lender", "ratio"),
    "hc_max_days_late_12m": ("LENDER_DPD", "Worst days late with this lender", "days"),
    "occupation_tenure_months": ("TENURE", "Months in current occupation", "months"),
    "dependents": ("DEPENDENTS", "Dependents", "count"),
}

STATUS_GAPS = {
    "bank_statement_status": ("BANK_STATEMENT", {"NOT_PROVIDED", "PARTIAL"}),
    "bureau_status": ("BUREAU_FILE", {"NO_RECORD"}),
    "gst_status": ("GST", {"NOT_APPLICABLE", "PARTIAL"}),
    "declared_income_status": ("DECLARED_INCOME", {"WITHHELD"}),
    "occupation_tenure_status": ("OCCUPATION_TENURE", {"NOT_APPLICABLE", "NOT_PROVIDED"}),
}

GAP_TEXT = {
    "NO_RECORD": "does not exist",
    "NOT_PROVIDED": "exists but was not shared",
    "PARTIAL": "shared but incomplete",
    "NOT_APPLICABLE": "does not apply to this applicant",
    "WITHHELD": "left blank on purpose",
}


def _fmt(value: float, unit: str) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "missing"
    if unit == "money":
        return f"INR {value / 100:,.0f}"
    if unit == "ratio":
        return f"{value:.2f}"
    if unit == "days":
        return f"{value:.0f} days"
    if unit == "months":
        return f"{value:.0f} months"
    return f"{value:.0f}"


def missing_information(raw_row: pd.Series) -> list[dict]:
    """Fields whose status column says the evidence is absent, with the reason."""
    out = []
    for col, (label, gap_values) in STATUS_GAPS.items():
        if col not in raw_row:
            continue
        value = raw_row[col]
        if isinstance(value, str) and value in gap_values:
            out.append({
                "code": f"MISSING_{label}",
                "text": f"{label.replace('_', ' ').title()} {GAP_TEXT.get(value, value)}",
                "status": value,
            })
    return out


def local_reasons(
    contributions: np.ndarray,
    feature_names: list[str],
    raw_row: pd.Series,
    top_k: int = 6,
) -> dict:
    """Split EBM additive contributions into risk-up and risk-down factors.

    Contributions are in log-odds; positive pushes default probability up.
    """
    contrib = pd.Series(contributions[: len(feature_names)], index=feature_names)
    contrib = contrib[contrib.index.isin(REASON_CODES)]
    contrib = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(top_k)

    up, down = [], []
    for feat, value in contrib.items():
        code, text, unit = REASON_CODES[feat]
        observed = raw_row.get(feat)
        item = {
            "code": code,
            "text": f"{text}: {_fmt(observed, unit)}",
            "feature": feat,
            "observed": None if observed is None or (isinstance(observed, float) and np.isnan(observed)) else str(observed),
            "log_odds": round(float(value), 4),
            "direction": "raises_risk" if value > 0 else "lowers_risk",
        }
        (up if value > 0 else down).append(item)
    return {"risk_factors": up, "positive_factors": down}


def decision_from_sets(member: np.ndarray) -> str:
    """Map a conformal set to a review outcome; never an automatic rejection."""
    default_in, repay_in = bool(member[1]), bool(member[0])
    if default_in and repay_in:
        return "REVIEW"
    if repay_in:
        return "ELIGIBLE"
    if default_in:
        return "DECLINE_CANDIDATE"
    return "ABSTAIN"
