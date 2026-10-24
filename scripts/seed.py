#!/usr/bin/env python3
"""Loads deterministic demo data so the demo is identical every run.

Writes data/accounts.json and data/transactions.csv. Same seed + same AS_OF date
=> byte-identical output. Never calls the network or uses the current time.
Adapt ACCOUNTS / the generators to the real schema in docs/API_CONTRACT.md.
"""
import csv
import json
import random
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

SEED = 42
AS_OF = date(2025, 1, 31)  # fixed "today" for the demo; never use date.today()
DAYS = 90
CURRENCY = "USD"  # ISO 4217; every amount carries a currency
CENT = Decimal("0.01")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

ACCOUNTS = [
    {"id": "acc_001", "name": "Everyday Checking", "type": "checking", "currency": CURRENCY},
    {"id": "acc_002", "name": "Rainy Day Savings", "type": "savings", "currency": CURRENCY},
]
CATEGORIES = {  # category: (merchants, typical amount)
    "groceries": (["Fresh Basket", "Green Grocer", "Market Hall"], Decimal("48")),
    "dining": (["Noodle Bar", "Cafe Aroma", "Taco Corner"], Decimal("22")),
    "transport": (["City Transit", "RideNow"], Decimal("14")),
    "entertainment": (["StreamBox", "Cinema 9"], Decimal("16")),
    "utilities": (["Power Co", "Water Works"], Decimal("85")),
}


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_EVEN)


def build_transactions(rng: random.Random) -> list[dict]:
    rows = []
    start = AS_OF - timedelta(days=DAYS - 1)
    for offset in range(DAYS):
        day = start + timedelta(days=offset)
        if day.day == 1:  # salary-like monthly inflow
            rows.append((day, "acc_001", "Acme Payroll", "income", money("3200")))
        if day.day == 15:  # bill
            rows.append((day, "acc_001", "Power Co", "utilities", -money("95")))
        weekday_bias = 2 if day.weekday() < 5 else 1
        for _ in range(rng.randint(0, weekday_bias)):
            category = rng.choice(list(CATEGORIES))
            merchants, typical = CATEGORIES[category]
            amount = money(typical * Decimal(str(round(rng.lognormvariate(0, 0.45), 4))))
            rows.append((day, "acc_001", rng.choice(merchants), category, -amount))
    rows.append((AS_OF - timedelta(days=3), "acc_001", "Fresh Basket", "groceries", money("12.50")))  # refund edge case
    rows.append((AS_OF - timedelta(days=1), "acc_001", "StreamBox", "entertainment", -money("16")))   # same-day
    rows.append((AS_OF - timedelta(days=1), "acc_001", "StreamBox", "entertainment", -money("16")))   # duplicate
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[4]))
    return [
        {"id": f"txn_{i:05d}", "date": d.isoformat(), "account_id": a, "merchant": m,
         "category": c, "amount": str(amt), "currency": CURRENCY}
        for i, (d, a, m, c, amt) in enumerate(rows, start=1)
    ]


def main() -> int:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(exist_ok=True)
    transactions = build_transactions(rng)
    with open(DATA_DIR / "accounts.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(ACCOUNTS, f, indent=2, sort_keys=True)
        f.write("\n")
    with open(DATA_DIR / "transactions.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(transactions[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(transactions)
    print(f"seeded {len(ACCOUNTS)} accounts, {len(transactions)} transactions into {DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
