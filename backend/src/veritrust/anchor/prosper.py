"""Real endorsements: Prosper peer-to-peer loans (US, 2005-2014), the only public data we found with
a credit score, social endorsements and a repayment outcome for the same borrower.

python -m veritrust.anchor.prosper [--raw ../data/external] [--out ../data/prosper]

Writes prosper_loans.csv (one row per loan, our own ids, no free text or Prosper keys) and
prints the real-data check: default by endorsement within credit-score bands, and how many real
loans combine a score drop with an endorsement. Endorsements here are cheap talk (no stake), so
they are a lower bound for a staked vouch. Money: US dollars as integer cents. Never commit rows.
"""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from veritrust.synth.generate import write_csv

SOURCE_FILE = "prosper/prosperLoanData.csv"
BAD = {"Chargedoff", "Defaulted", "Past Due (>120 days)"}
OPEN = {"Current", "Cancelled"}
BANDS = ((600, "<600"), (660, "600-659"), (720, "660-719"), (10_000, "720+"))


def _int(value: str) -> int | str:
    return "" if value in ("", "NA") else int(float(value))


def _cents(value: str) -> int | str:
    if value in ("", "NA"):
        return ""
    return int((Decimal(value) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _ratio(value: str) -> str:
    return "" if value in ("", "NA") else str(Decimal(value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def band(score: int) -> str:
    return next(name for ceiling, name in BANDS if score < ceiling)


def build(raw: Path, out: Path) -> dict:
    rows = []
    with (raw / SOURCE_FILE).open(encoding="utf-8") as handle:
        for n, r in enumerate(csv.DictReader(handle), start=1):
            status = r["LoanStatus"]
            resolved = status not in OPEN and not (status.startswith("Past Due") and status not in BAD)
            recommendations = _int(r["Recommendations"]) or 0
            friends = _int(r["InvestmentFromFriendsCount"]) or 0
            change = _int(r["ScorexChangeAtTimeOfListing"])
            rows.append({
                "borrower_id": f"P{n:06d}", "listing_month": r["ListingCreationDate"][:7],
                "term_months": _int(r["Term"]), "loan_amount_minor": _cents(r["LoanOriginalAmount"]), "currency": "USD",
                "credit_score_lower": _int(r["CreditScoreRangeLower"]),
                "credit_score_upper": _int(r["CreditScoreRangeUpper"]),
                "score_change_since_last_loan": change,
                "score_change_status": "OBSERVED" if change != "" else "NOT_APPLICABLE",
                "current_delinquencies": _int(r["CurrentDelinquencies"]),
                "delinquencies_last_7y": _int(r["DelinquenciesLast7Years"]),
                "bankcard_utilisation": _ratio(r["BankcardUtilization"]),
                "debt_to_income": _ratio(r["DebtToIncomeRatio"]),
                "stated_monthly_income_minor": _cents(r["StatedMonthlyIncome"]),
                "income_verifiable": 1 if r["IncomeVerifiable"] == "True" else 0,
                "employment_status": r["EmploymentStatus"],
                "prior_prosper_loans": _int(r["TotalProsperLoans"]),
                "prior_on_time_payments": _int(r["OnTimeProsperPayments"]),
                "recommendations": recommendations, "friends_invested_count": friends,
                "friends_invested_minor": _cents(r["InvestmentFromFriendsAmount"]) or 0,
                "in_group": 1 if r["CurrentlyInGroup"] == "True" else 0,
                "endorsed": int(recommendations > 0 or friends > 0),
                "loan_status": status, "resolved": int(resolved), "bad": int(status in BAD) if resolved else "",
            })
    out.mkdir(parents=True, exist_ok=True)
    path = out / "prosper_loans.csv"
    write_csv(path, rows)
    manifest = {
        "dataset": "prosper", "borrowers": len(rows), "currency": "USD", "money_unit": "integer cents",
        "label": "bad = charged off, defaulted or 120+ days past due, among resolved loans",
        "source": "Prosper loan data (113,937 loans, 2005-2014), public mirror pinned in download.py",
        "notice": "Real anonymised loans. Do not commit or share rows.",
        "files": {"prosper_loans.csv": {"rows": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def check(rows: list[dict]) -> dict:
    """Default by endorsement within credit-score bands, plus the score-drop cells (aggregates only)."""
    resolved = [r for r in rows if r["resolved"] == "1" and r["credit_score_lower"] != ""]

    def cell(subset):
        return {"n": len(subset), "default": round(sum(int(r["bad"]) for r in subset) / len(subset), 4) if subset else None}

    by_band = defaultdict(lambda: {"0": [], "1": []})
    for r in resolved:
        by_band[band(int(r["credit_score_lower"]))][r["endorsed"]].append(r)
    weighted = weight = 0.0
    for groups in by_band.values():
        t, c = groups["1"], groups["0"]
        if t and c:
            w = len(t) * len(c) / (len(t) + len(c))
            weighted += w * (sum(int(r["bad"]) for r in t) / len(t) - sum(int(r["bad"]) for r in c) / len(c))
            weight += w
    drops = {}
    for floor in (0, -20, -50):
        dropped = [r for r in resolved if r["score_change_since_last_loan"] != "" and int(r["score_change_since_last_loan"]) < floor]
        drops[f"score_change_below_{floor}"] = {"endorsed": cell([r for r in dropped if r["endorsed"] == "1"]),
                                                "not_endorsed": cell([r for r in dropped if r["endorsed"] == "0"])}
    troubled = [r for r in resolved if r["current_delinquencies"] not in ("", "0")]
    return {
        "resolved_loans": len(resolved), "endorsed": sum(1 for r in resolved if r["endorsed"] == "1"),
        "by_score_band": {b: {"endorsed": cell(g["1"]), "not_endorsed": cell(g["0"])} for b, g in sorted(by_band.items())},
        "band_adjusted_difference": round(weighted / weight, 4) if weight else None,
        "current_delinquency_at_listing": {"endorsed": cell([r for r in troubled if r["endorsed"] == "1"]),
                                           "not_endorsed": cell([r for r in troubled if r["endorsed"] == "0"])},
        "score_drop_cells": drops,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Prosper endorsement table and run the real-data check.")
    parser.add_argument("--raw", type=Path, default=Path("../data/external"))
    parser.add_argument("--out", type=Path, default=Path("../data/prosper"))
    args = parser.parse_args()
    manifest = build(args.raw, args.out)
    with (args.out / "prosper_loans.csv").open(encoding="utf-8") as handle:
        result = check(list(csv.DictReader(handle)))
    (args.out / "prosper_check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"prosper_loans.csv {manifest['borrowers']} rows")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
