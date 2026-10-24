"""Calibrate cash-flow behaviour on real bank accounts (Berka / PKDD'99, Czech bank, 1993-98).

python -m veritrust.anchor.berka [--raw ../data/external/berka]

Writes berka_calibration.json next to this file: aggregate quantiles only, no rows, so it is safe
to commit. Accounts are grouped by income style, read from how their money arrives:
- transfer: most credits come from another bank (salary-like)
- pension:  old-age pension credits (k_symbol DUCHOD)
- cash:     most credits are cash deposits (informal or business income)
Also reports, respecting time (only transactions before each loan's date), how often good and bad
loans showed negative-balance penalties beforehand: real evidence that distress is visible early.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

QUANTILES = [round(q / 20, 2) for q in range(1, 20)]   # 0.05 .. 0.95
OUT = Path(__file__).with_name("berka_calibration.json")


def _monthly(trans: pd.DataFrame) -> pd.DataFrame:
    trans = trans.copy()
    trans["month"] = pd.to_datetime(trans["date"]).dt.to_period("M")
    credits = trans[(trans["type"] == "PRIJEM") & (trans["k_symbol"].fillna("") != "UROK")]
    monthly = credits.groupby(["account_id", "month"])["amount"].sum().rename("credits").reset_index()
    balance = trans.sort_values(["account_id", "date", "trans_id"]).groupby(["account_id", "month"])["balance"].last()
    penalty = trans[trans["k_symbol"].fillna("").str.startswith("SANKC")].groupby(["account_id", "month"]).size()
    frame = balance.rename("closing").reset_index()
    frame = frame.merge(monthly, on=["account_id", "month"], how="left").fillna({"credits": 0})
    frame["penalty"] = frame.set_index(["account_id", "month"]).index.map(penalty).fillna(0).astype(int).values > 0
    return frame


def _styles(trans: pd.DataFrame) -> pd.Series:
    credits = trans[(trans["type"] == "PRIJEM") & (trans["k_symbol"].fillna("") != "UROK")]
    total = credits.groupby("account_id")["amount"].sum()
    transfer = credits[credits["operation"] == "PREVOD Z UCTU"].groupby("account_id")["amount"].sum()
    pension = credits[credits["k_symbol"] == "DUCHOD"].groupby("account_id")["amount"].sum()
    share_t = (transfer / total).reindex(total.index).fillna(0)
    share_p = (pension / total).reindex(total.index).fillna(0)
    style = pd.Series("cash", index=total.index)
    style[share_t >= 0.5] = "transfer"
    style[share_p >= 0.5] = "pension"
    return style


def calibrate(raw: Path) -> dict:
    full = raw / "trans.csv"
    if full.exists():
        trans = pd.read_csv(full, low_memory=False)
    else:   # export still running: whole-account batches, so drop only the last account
        trans = pd.read_csv(raw / "trans.part", low_memory=False, on_bad_lines="skip")
        trans = trans[trans["account_id"] != trans["account_id"].iloc[-1]]
    loans = pd.read_csv(raw / "loan.csv")
    loans = loans[loans["account_id"].isin(set(trans["account_id"]))]
    monthly = _monthly(trans)
    style = _styles(trans)

    stats = monthly.groupby("account_id").agg(
        months=("credits", "size"), mean=("credits", "mean"), sd=("credits", "std"),
        median=("credits", "median"), zero=("credits", lambda s: float((s <= 0).mean())),
        penalty=("penalty", "mean"), closing=("closing", "median"))
    stats = stats[(stats["months"] >= 12) & (stats["mean"] > 0)]
    stats["cv"] = stats["sd"] / stats["mean"]
    stats["buffer"] = stats["closing"] / stats["median"].where(stats["median"] > 0)
    stats["style"] = style.reindex(stats.index)

    out: dict = {"source": "Berka / PKDD'99 financial dataset via CTU relational repository",
                 "accounts_used": int(len(stats)), "partial_export": not full.exists(), "styles": {}}
    for name, group in stats.groupby("style"):
        out["styles"][name] = {
            "accounts": int(len(group)),
            "income_cv_quantiles": [round(float(v), 4) for v in group["cv"].quantile(QUANTILES)],
            "buffer_months_quantiles": [round(float(v), 4) for v in group["buffer"].dropna().quantile(QUANTILES)],
            "zero_income_month_share": round(float(group["zero"].mean()), 4),
            "penalty_month_share": round(float(group["penalty"].mean()), 4),
        }
    out["quantile_levels"] = QUANTILES

    # Time-respecting early-warning check on the 682 real loans.
    loans["date"] = pd.to_datetime(loans["date"])
    monthly["start"] = monthly["month"].dt.to_timestamp()
    rows = []
    for loan in loans.itertuples():
        before = monthly[(monthly["account_id"] == loan.account_id) & (monthly["start"] < loan.date.replace(day=1))]
        before = before.tail(12)
        if before.empty:
            continue
        rows.append({"bad": loan.status in ("B", "D"), "penalty_months": int(before["penalty"].sum()),
                     "cv": float(before["credits"].std() / before["credits"].mean()) if before["credits"].mean() else None})
    early = pd.DataFrame(rows)
    out["loan_early_warning"] = {
        group: {"loans": int(len(g)),
                "share_with_penalty_before_loan": round(float((g["penalty_months"] > 0).mean()), 4),
                "median_income_cv_before_loan": round(float(g["cv"].median()), 4)}
        for group, g in early.groupby(early["bad"].map({True: "bad_loans_B_D", False: "good_loans_A_C"}))
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate cash-flow parameters on Berka accounts.")
    parser.add_argument("--raw", type=Path, default=Path("../data/external/berka"))
    args = parser.parse_args()
    result = calibrate(args.raw)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in result.items() if k != "styles"}, indent=2))
    for name, s in result["styles"].items():
        q = s["income_cv_quantiles"]
        print(name, s["accounts"], "cv p10/p50/p90:", q[1], q[9], q[17], "| penalty months:", s["penalty_month_share"])


if __name__ == "__main__":
    main()
