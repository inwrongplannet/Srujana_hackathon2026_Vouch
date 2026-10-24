"""Validate the anchored dataset: leakage, real absence facts, and detector answer keys.

python -m veritrust.anchor.validate [--data ../data/anchored]

- Leakage: AUC with real features only vs real + synthetic-statement features. The statements
  were generated from real behaviour, never from the label, so the gain should be small.
  A large jump would mean the synthetic layer smuggled in the answer.
- Absence (real data): default rates with and without a bureau file / lender history.
- Detectors: does the observed data reveal each injected test case (answer key: injections.csv)?
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from veritrust.synth.validate import fit_predict, rate_by, read

REAL_NUMERIC = [
    "requested_amount_minor", "tenure_months", "new_emi_minor", "declared_income_minor", "occupation_tenure_months",
    "dependents", "urban", "region_rating", "owns_realty", "bureau_enquiries_12m", "bureau_current_overdue_max",
    "bureau_tradelines", "bureau_active", "bureau_history_months", "bureau_max_dpd_24m", "bureau_months_30plus_24m",
    "bureau_reporting_gaps", "bureau_new_6m", "bureau_written_off", "bureau_emi_minor",
    "bureau_outstanding_to_sanctioned", "hc_prev_applications", "hc_prev_refused", "hc_instalments_12m",
    "hc_late_share_12m", "hc_short_share_12m", "hc_max_days_late_12m", "hc_late_share_all",
]
SYNTHETIC_NUMERIC = [
    "declared_emi_minor", "bank_statement_months", "income_est_minor", "existing_emi_est_minor", "dti_est",
    "amount_to_income", "declared_to_bank_income", "undeclared_emi_to_income", "gst_turnover_median_minor",
    "gst_missed_filings", "gst_to_bank_credits", "bank_income_median_minor", "bank_income_cv",
    "bank_zero_income_months", "bank_worst3_to_median", "bank_emi_recent_minor", "bank_bounces", "bank_bounces_3m",
    "bank_low_balance_months", "bank_last_month_spike", "bank_unreconciled_months", "bank_surplus_median_minor",
]
REAL_CATEGORICAL = ["occupation", "age_band", "product", "occupation_tenure_status", "bureau_status",
                    "hc_history_status"]
SYNTHETIC_CATEGORICAL = ["bank_statement_status", "gst_status", "income_basis"]


def _detector(rows: list[dict], flag, fired) -> dict:
    tp = sum(1 for r in rows if flag(r) and fired(r))
    fp = sum(1 for r in rows if not flag(r) and fired(r))
    fn = sum(1 for r in rows if flag(r) and not fired(r))
    return {"injected": tp + fn, "precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "recall": round(tp / (tp + fn), 4) if tp + fn else None}


def report(data: Path) -> dict:
    features = read(data / "features.csv")
    labels = {r["borrower_id"]: int(r["default_12m"]) for r in read(data / "outcomes.csv")}
    inject = {r["borrower_id"]: r for r in read(data / "injections.csv")}
    n = len(features)
    real_auc, _ = fit_predict(features, labels, REAL_NUMERIC, REAL_CATEGORICAL)
    all_auc, _ = fit_predict(features, labels, REAL_NUMERIC + SYNTHETIC_NUMERIC,
                             REAL_CATEGORICAL + SYNTHETIC_CATEGORICAL)
    with_bank = [r for r in features if r["bank_statement_months"] not in ("", "0")]

    def num(value: str) -> float:
        return float(value) if value != "" else 0.0

    joined = [{**r, **{f"inj_{k}": v for k, v in inject[r["borrower_id"]].items()}} for r in with_bank]
    out = {
        "borrowers": n,
        "default_rate": round(sum(labels.values()) / n, 4),
        "auc_real_features_only": round(real_auc, 4),
        "auc_real_plus_synthetic": round(all_auc, 4),
        "auc_gain_from_synthetic": round(all_auc - real_auc, 4),
        "leak_alarm": all_auc - real_auc > 0.03,
        "by_bureau_status": rate_by(features, "bureau_status", labels),
        "by_lender_history": rate_by(features, "hc_history_status", labels),
        "by_occupation": rate_by(features, "occupation", labels),
        "by_completeness_tier": rate_by(features, "completeness_tier", labels),
        "by_bank_statement_status": rate_by(features, "bank_statement_status", labels),
        "legacy_policy": {
            "approval_rate": round(sum(r["legacy_decision"] == "APPROVE" for r in features) / n, 4),
            "rejected_no_bureau": sum(r["legacy_reason"] == "NO_BUREAU_HISTORY" for r in features),
            "rejected_no_bureau_who_repaid": round(1 - sum(labels[r["borrower_id"]] for r in features
                                                           if r["legacy_reason"] == "NO_BUREAU_HISTORY")
                                                   / max(1, sum(r["legacy_reason"] == "NO_BUREAU_HISTORY" for r in features)), 4),
        },
        "detectors": {
            "hidden_loan (undeclared EMI > 1% of income)": _detector(
                joined, lambda r: r["inj_hidden_loan_emi_minor"] != "0" or r["inj_forgot_loan_emi_minor"] != "0",
                lambda r: num(r["undeclared_emi_to_income"]) > 0.01),
            "window_dressing (last month > 1.8x median)": _detector(
                joined, lambda r: r["inj_window_dressing"] == "1", lambda r: num(r["bank_last_month_spike"]) > 1.8),
            "duplicate_import (statement does not reconcile)": _detector(
                joined, lambda r: r["inj_duplicate_import"] == "1", lambda r: num(r["bank_unreconciled_months"]) > 0),
        },
    }
    missing: dict = defaultdict(dict)
    for column in ("bureau_status", "hc_history_status", "bank_statement_status", "occupation_tenure_status", "gst_status"):
        counts: dict = defaultdict(int)
        for r in features:
            counts[r[column]] += 1
        missing[column] = dict(sorted(counts.items()))
    out["missingness"] = missing
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the anchored dataset.")
    parser.add_argument("--data", type=Path, default=Path("../data/anchored"))
    args = parser.parse_args()
    result = report(args.data)
    (args.data / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
