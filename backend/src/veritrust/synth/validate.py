"""Checks that the generated world is believable and does not leak its own answers.

python -m veritrust.synth.validate [--data ../data/synth]

Reports default rates, missingness by reason code, and three numbers that matter:
- observed AUC: a plain logistic regression on lender-visible features. Real credit models sit
  around 0.70-0.80; far above that means the label leaked into the features.
- oracle AUC: the same model on the hidden truth. Below 1.0 because future shocks are
  unknowable at application time; that gap is the irreducible uncertainty conformal must show.
- absence check: at the same true (oracle) risk, do people with no bureau file default more?
Stdlib only, so it runs anywhere the generator does.
"""

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

NUMERIC = [
    "requested_amount_minor", "tenure_months", "rate_annual", "new_emi_minor", "declared_income_minor",
    "declared_emi_minor", "occupation_tenure_months", "bank_statement_months", "income_est_minor",
    "existing_emi_est_minor", "dti_est", "amount_to_income", "declared_to_bank_income",
    "undeclared_emi_to_income", "gst_turnover_median_minor", "gst_missed_filings", "gst_to_bank_credits",
    "vouch_count", "vouch_mean_voucher_on_time", "completeness_tier", "bank_income_median_minor",
    "bank_income_cv", "bank_zero_income_months", "bank_worst3_to_median", "bank_emi_recent_minor",
    "bank_bounces", "bank_bounces_3m", "bank_low_balance_months", "bank_loan_disbursals_6m",
    "bank_last_month_spike", "bank_unreconciled_months", "bank_surplus_median_minor", "bureau_tradelines",
    "bureau_active", "bureau_history_months", "bureau_max_dpd_24m", "bureau_months_30plus_24m",
    "bureau_reporting_gaps", "bureau_new_6m", "bureau_written_off", "bureau_emi_minor",
    "bureau_outstanding_to_sanctioned", "dependents", "urban",
]
CATEGORICAL = ["occupation", "age_band", "product", "declared_income_status", "occupation_tenure_status",
               "bank_statement_status", "bureau_status", "gst_status", "vouch_status", "income_basis"]
ORACLE_NUMERIC = ["base_income_minor", "income_cv", "expense_ratio", "discipline", "save_rate",
                  "deposit_share", "true_dti_with_new", "stacker", "existing_emi_true_minor"]


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _num(value: str, money: bool) -> float:
    x = float(value)
    return math.log1p(max(0.0, x) / 100) if money else x


def encode(rows: list[dict], numeric: list[str], categorical: list[str]) -> tuple[list[list[float]], list[str]]:
    levels = {c: sorted({r[c] for r in rows}) for c in categorical}
    names: list[str] = []
    for c in numeric:
        names += [c, f"{c}__missing"]
    for c in categorical:
        names += [f"{c}={v}" for v in levels[c][1:]]
    matrix = []
    for r in rows:
        x: list[float] = []
        for c in numeric:
            if r[c] == "":
                x += [0.0, 1.0]
            else:
                x += [_num(r[c], c.endswith("_minor")), 0.0]
        for c in categorical:
            x += [1.0 if r[c] == v else 0.0 for v in levels[c][1:]]
        matrix.append(x)
    return matrix, names


def standardise(train: list[list[float]], test: list[list[float]]) -> None:
    for j in range(len(train[0])):
        column = [row[j] for row in train]
        mu = sum(column) / len(column)
        sd = math.sqrt(sum((v - mu) ** 2 for v in column) / len(column)) or 1.0
        for row in train:
            row[j] = (row[j] - mu) / sd
        for row in test:
            row[j] = (row[j] - mu) / sd


def logistic(train: list[list[float]], y: list[int], epochs: int = 12, lr: float = 0.05,
             l2: float = 1e-4) -> list[float]:
    """Plain SGD logistic regression; weights[0] is the intercept."""
    rng = random.Random(7)
    w = [0.0] * (len(train[0]) + 1)
    order = list(range(len(train)))
    for epoch in range(epochs):
        rng.shuffle(order)
        step = lr / (1 + epoch)
        for i in order:
            x = train[i]
            z = w[0] + sum(wj * xj for wj, xj in zip(w[1:], x))
            p = 1 / (1 + math.exp(-max(-30.0, min(30.0, z))))
            g = p - y[i]
            w[0] -= step * g
            for j, xj in enumerate(x, start=1):
                w[j] -= step * (g * xj + l2 * w[j])
    return w


def predict(w: list[float], rows: list[list[float]]) -> list[float]:
    return [1 / (1 + math.exp(-max(-30.0, min(30.0, w[0] + sum(a * b for a, b in zip(w[1:], x)))))) for x in rows]


def auc(scores: list[float], y: list[int]) -> float:
    """Rank-based ROC AUC (ties share the average rank)."""
    pairs = sorted(zip(scores, y))
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        for k in range(i, j + 1):
            ranks[k] = (i + j) / 2 + 1
        i = j + 1
    positives = sum(y)
    negatives = len(y) - positives
    if not positives or not negatives:
        return float("nan")
    rank_sum = sum(r for r, (_, label) in zip(ranks, pairs) if label)
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def fit_predict(rows: list[dict], labels: dict[str, int], numeric: list[str],
                categorical: list[str]) -> tuple[float, dict[str, float]]:
    """Train on ids ending 0-6, report test AUC on ids ending 7-9, and score every row."""
    train_rows = [r for r in rows if int(r["borrower_id"][1:]) % 10 < 7]
    test_rows = [r for r in rows if int(r["borrower_id"][1:]) % 10 >= 7]
    xall, _ = encode(rows, numeric, categorical)
    index = {r["borrower_id"]: i for i, r in enumerate(rows)}
    xtr = [list(xall[index[r["borrower_id"]]]) for r in train_rows]
    xev = [list(x) for x in xall]
    standardise(xtr, xev)
    w = logistic(xtr, [labels[r["borrower_id"]] for r in train_rows])
    scores = predict(w, xev)
    test_scores = [scores[index[r["borrower_id"]]] for r in test_rows]
    return auc(test_scores, [labels[r["borrower_id"]] for r in test_rows]),         {r["borrower_id"]: scores[index[r["borrower_id"]]] for r in rows}


def rate_by(rows: list[dict], key: str, labels: dict[str, int]) -> dict[str, dict]:
    groups: dict[str, list[int]] = defaultdict(list)
    for r in rows:
        groups[r[key]].append(labels[r["borrower_id"]])
    return {k: {"n": len(v), "default_rate": round(sum(v) / len(v), 4)} for k, v in sorted(groups.items())}


def report(data: Path) -> dict:
    features = read(data / "features.csv")
    truth = {r["borrower_id"]: r for r in read(data / "truth.csv")}
    labels = {r["borrower_id"]: int(r["default_12m"]) for r in read(data / "outcomes.csv")}
    n = len(features)

    oracle_rows = [{**truth[r["borrower_id"]], "occupation": r["occupation"]} for r in features]
    out = {
        "borrowers": n,
        "default_rate": round(sum(labels.values()) / n, 4),
        "by_occupation": rate_by(features, "occupation", labels),
        "by_completeness_tier": rate_by(features, "completeness_tier", labels),
        "by_bureau_status": rate_by(features, "bureau_status", labels),
        "by_bank_statement_status": rate_by(features, "bank_statement_status", labels),
        "by_application_month": rate_by(features, "application_month", labels),
        "missingness": {c: dict(sorted(_count(features, c).items()))
                        for c in ("declared_income_status", "occupation_tenure_status", "bank_statement_status",
                                  "bureau_status", "gst_status", "vouch_status")},
        "default_drivers": dict(sorted(_count([t for b, t in truth.items() if labels[b]], "default_driver").items())),
    }
    observed_auc, _ = fit_predict(features, labels, NUMERIC, CATEGORICAL)
    oracle_auc, oracle_pd = fit_predict(oracle_rows, labels, ORACLE_NUMERIC, ["occupation"])
    out["observed_auc"], out["oracle_auc"] = round(observed_auc, 4), round(oracle_auc, 4)

    # Absence vs inability: at the same true (oracle) risk, does having no bureau file add defaults?
    risk = sorted(oracle_pd.values())
    cuts = [risk[int(len(risk) * q)] for q in (0.2, 0.4, 0.6, 0.8)]
    buckets: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in features:
        value = oracle_pd[r["borrower_id"]]
        bucket = f"q{sum(value > c for c in cuts) + 1}"
        buckets[bucket][r["bureau_status"]].append(labels[r["borrower_id"]])
    out["absence_check"] = {
        b: {s: {"n": len(v), "default_rate": round(sum(v) / len(v), 4)} for s, v in sorted(groups.items())}
        for b, groups in sorted(buckets.items())
    }
    thin = [r for r in features if r["bureau_status"] == "NO_RECORD"]
    rejected = [r for r in thin if r["legacy_decision"] == "REJECT"]
    out["legacy_policy"] = {
        "approval_rate": round(sum(r["legacy_decision"] == "APPROVE" for r in features) / n, 4),
        "approved_default_rate": _rate([labels[r["borrower_id"]] for r in features if r["legacy_decision"] == "APPROVE"]),
        "no_bureau_applicants": len(thin),
        "no_bureau_rejected": len(rejected),
        "no_bureau_rejected_who_repaid": round(1 - (_rate([labels[r["borrower_id"]] for r in rejected]) or 0), 4),
    }
    out["leak_alarm"] = out["observed_auc"] > 0.90
    return out


def _count(rows: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r[key]] += 1
    return counts


def _rate(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a generated synthetic dataset.")
    parser.add_argument("--data", type=Path, default=Path("../data/synth"))
    args = parser.parse_args()
    result = report(args.data)
    (args.data / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("borrowers", "default_rate", "observed_auc", "oracle_auc",
                                              "leak_alarm", "legacy_policy")}, indent=2))
    print("by_occupation", json.dumps(result["by_occupation"]))
    print("by_tier", json.dumps(result["by_completeness_tier"]))
    print("by_bureau", json.dumps(result["by_bureau_status"]))
    print("drivers", json.dumps(result["default_drivers"]))
    print("absence_check", json.dumps(result["absence_check"]))


if __name__ == "__main__":
    main()
